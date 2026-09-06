#!/usr/bin/env bash
set -euo pipefail

version="1.0.1"
asset="voxtype-${version}-linux-x86_64-avx512"
checksum="77d49275ae4c3a6d93671014278b0dabd69ba52e65d2ee6ab3ec1bff0af34d55"
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(git -C "$script_dir" rev-parse --show-toplevel)"
binary_dir="${HOME}/.local/bin"
config_home="${XDG_CONFIG_HOME:-${HOME}/.config}"
systemd_user_dir="${config_home}/systemd/user"
download_dir="$(mktemp -d)"

cleanup() {
  rm -f -- "${download_dir}/${asset}"
  rmdir -- "$download_dir"
}
trap cleanup EXIT

link_tracked_file() {
  local source="$1"
  local target="$2"

  mkdir -p -- "$(dirname -- "$target")"
  if [[ -L "$target" && "$(readlink -f -- "$target")" == "$source" ]]; then
    return 0
  fi
  if [[ -e "$target" || -L "$target" ]]; then
    printf 'Refusing to replace existing path: %s\n' "$target" >&2
    exit 1
  fi
  ln -s -- "$source" "$target"
}

if [[ "$(uname -m)" != "x86_64" ]] || ! grep -qw avx512f /proc/cpuinfo; then
  printf 'This installer requires an x86_64 CPU with AVX-512 support.\n' >&2
  exit 1
fi

# Preflight both destinations before changing the installed binary or links.
for relative in voxtype/config.toml systemd/user/voxtype.service; do
  target="${config_home}/${relative}"
  source="${repo_root}/config/${relative}"
  if [[ -L "$target" && "$(readlink -f -- "$target")" == "$source" ]]; then
    continue
  fi
  if [[ -e "$target" || -L "$target" ]]; then
    printf 'Refusing to replace existing path: %s\n' "$target" >&2
    exit 1
  fi
done

curl -fL \
  "https://github.com/peteonrails/voxtype/releases/download/v${version}/${asset}" \
  -o "${download_dir}/${asset}"
printf '%s  %s\n' "$checksum" "$asset" | (cd "$download_dir" && sha256sum -c -)

mkdir -p -- "$binary_dir"
install -m 0755 -- "${download_dir}/${asset}" "${binary_dir}/voxtype"
link_tracked_file \
  "${repo_root}/config/voxtype/config.toml" \
  "${config_home}/voxtype/config.toml"
link_tracked_file \
  "${repo_root}/config/systemd/user/voxtype.service" \
  "${systemd_user_dir}/voxtype.service"

# The tracked config already selects whisper/base.en. --activate would write
# through that source symlink (or replace it), so download without activation.
"${binary_dir}/voxtype" setup \
  --download \
  --model base.en \
  --no-post-install
systemctl --user daemon-reload
systemctl --user enable --now voxtype.service
