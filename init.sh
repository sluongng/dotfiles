#!/usr/bin/env bash

set -euo pipefail

# Bootstrap the shared dotfiles on macOS or Linux. Package installation is
# intentionally opt-in; the default operation only links tracked config and
# installs the tracked Codex surface.

DEFAULT_DOTFILES_DIR="${HOME}/.dotfiles"
SCRIPT_SOURCE="${BASH_SOURCE[0]:-}"
SCRIPT_DIR=""
REPO_ROOT=""

if [ -n "${SCRIPT_SOURCE}" ] && [ -f "${SCRIPT_SOURCE}" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${SCRIPT_SOURCE}")" && pwd)"
  REPO_ROOT="$(git -C "${SCRIPT_DIR}" rev-parse --show-toplevel 2>/dev/null || true)"
fi

DOTFILES_DIR="${DOTFILES_DIR:-${REPO_ROOT:-${DEFAULT_DOTFILES_DIR}}}"
CONFIG_HOME="${XDG_CONFIG_HOME:-${HOME}/.config}"
PLATFORM="${DOTFILES_PLATFORM:-$(uname -s)}"
TIMESTAMP="$(date +%Y%m%d%H%M%S)"
BACKUP_DIR="${DOTFILES_BACKUP_DIR:-${HOME}/.dotfiles-backups/${TIMESTAMP}}"

case "${PLATFORM}" in
  Darwin | Linux) ;;
  *)
    echo "Unsupported platform: ${PLATFORM}. Expected Darwin or Linux." >&2
    exit 1
    ;;
esac

if [ ! -d "${DOTFILES_DIR}/.git" ]; then
  if [ -e "${DOTFILES_DIR}" ]; then
    echo "${DOTFILES_DIR} exists but is not a Git checkout." >&2
    exit 1
  fi
  git clone https://github.com/sluongng/dotfiles.git "${DOTFILES_DIR}"
elif [ "${DOTFILES_UPDATE:-0}" = "1" ]; then
  git -C "${DOTFILES_DIR}" pull --ff-only
else
  echo "Using existing checkout ${DOTFILES_DIR} (set DOTFILES_UPDATE=1 to pull)."
fi

git -C "${DOTFILES_DIR}" config core.hooksPath .githooks

backup_path() {
  local target_path="$1"
  local relative_path="${target_path#"${HOME}/"}"
  local backup_path="${BACKUP_DIR}/${relative_path}"

  if [ ! -e "${target_path}" ] && [ ! -L "${target_path}" ]; then
    return 0
  fi

  mkdir -p "$(dirname "${backup_path}")"
  mv "${target_path}" "${backup_path}"
  echo "Backed up ${target_path} to ${backup_path}"
}

ensure_symlink() {
  local source_path="$1"
  local target_path="$2"
  local current_target=""

  if [ ! -e "${source_path}" ]; then
    echo "Missing tracked source: ${source_path}" >&2
    exit 1
  fi

  mkdir -p "$(dirname "${target_path}")"
  if [ -L "${target_path}" ]; then
    current_target="$(readlink "${target_path}")"
    if [ "${current_target}" = "${source_path}" ]; then
      return 0
    fi
    backup_path "${target_path}"
  elif [ -e "${target_path}" ]; then
    backup_path "${target_path}"
  fi

  ln -s "${source_path}" "${target_path}"
  echo "Linked ${target_path} -> ${source_path}"
}

link_config_tree() {
  local source_root="$1"
  local target_root="$2"
  local source_path=""
  local relative_path=""

  [ -d "${source_root}" ] || return 0
  while IFS= read -r source_path; do
    relative_path="${source_path#"${source_root}/"}"
    ensure_symlink "${source_path}" "${target_root}/${relative_path}"
  done < <(find "${source_root}" -type f | sort)
}

for relative_path in .zshrc .zprofile .ideavimrc .tmux.conf; do
  ensure_symlink "${DOTFILES_DIR}/${relative_path}" "${HOME}/${relative_path}"
done
ensure_symlink "${DOTFILES_DIR}/wezterm.lua" "${HOME}/.wezterm.lua"

for config_name in nvim alacritty kitty bat git ghostty herdr metals voxtype; do
  link_config_tree \
    "${DOTFILES_DIR}/config/${config_name}" \
    "${CONFIG_HOME}/${config_name}"
done

if [ "${PLATFORM}" = "Darwin" ]; then
  link_config_tree \
    "${DOTFILES_DIR}/config/karabiner" \
    "${CONFIG_HOME}/karabiner"
  ensure_symlink \
    "${DOTFILES_DIR}/config/ghostty/config.macos" \
    "${HOME}/Library/Application Support/com.mitchellh.ghostty/config"
else
  ensure_symlink \
    "${DOTFILES_DIR}/config/libinput-gestures.conf" \
    "${CONFIG_HOME}/libinput-gestures.conf"
  for config_name in hypr mako waybar systemd; do
    link_config_tree \
      "${DOTFILES_DIR}/config/${config_name}" \
      "${CONFIG_HOME}/${config_name}"
  done
fi

"${DOTFILES_DIR}/automation/codex/install-codex.sh"

if [ "${DOTFILES_INSTALL_MAIL:-0}" = "1" ]; then
  "${DOTFILES_DIR}/automation/mail/install-mail.sh"
fi

if [ "${DOTFILES_INSTALL_PACKAGES:-0}" = "1" ]; then
  if [ "${PLATFORM}" = "Darwin" ]; then
    if ! command -v brew >/dev/null 2>&1; then
      echo "Homebrew is required for DOTFILES_INSTALL_PACKAGES=1 on macOS." >&2
      exit 1
    fi
    brew bundle install --file "${DOTFILES_DIR}/Brewfile"
  else
    echo "Linux package installation is intentionally host-managed; config is installed." >&2
  fi
fi

if command -v herdr >/dev/null 2>&1; then
  herdr integration install codex
  if [ -d "${HOME}/.gemini/config" ]; then
    herdr integration install antigravity-cli
  fi
fi

echo "Dotfiles installed for ${PLATFORM} from ${DOTFILES_DIR}."
