#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
data_dir="${STREAMCONTROLLER_DATA_DIR:-${HOME}/.var/app/com.core447.StreamController/data}"
page_dir="${data_dir}/pages"
target="${page_dir}/first.json"
backup_dir="${page_dir}/backups"

if [[ ! -d "$page_dir" ]]; then
  printf 'StreamController page directory does not exist: %s\n' "$page_dir" >&2
  exit 1
fi

unit="app-StreamController@autostart.service"
was_active=false
stopped=false
staged="$(mktemp "${page_dir}/.first.XXXXXXXX.json")"
restore_service() {
  local result=$?
  rm -f -- "$staged"
  if [[ "$stopped" == true && "$was_active" == true ]]; then
    systemctl --user start "$unit" || result=1
  fi
  return "$result"
}
trap restore_service EXIT
# Finish the copy before stopping the application. A failed write cannot leave
# either a truncated live page or an unnecessarily stopped controller.
install -m 0644 -- "$script_dir/page.json" "$staged"
if systemctl --user is-active --quiet "$unit"; then
  was_active=true
fi
systemctl --user stop "$unit"
stopped=true

if [[ -f "$target" ]]; then
  mkdir -p -- "$backup_dir"
  cp --reflink=auto -- "$target" "$backup_dir/first-$(date +%Y%m%dT%H%M%S%N).json"
fi

mv -f -- "$staged" "$target"
if [[ "$was_active" == false ]]; then
  systemctl --user start "$unit"
fi
