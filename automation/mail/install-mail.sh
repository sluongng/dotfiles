#!/usr/bin/env bash

set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="${DOTFILES_DIR}/config/mail"
CONFIG_HOME="${XDG_CONFIG_HOME:-${HOME}/.config}"
BIN_HOME="${HOME}/.local/bin"
TIMESTAMP="$(date +%Y%m%d%H%M%S)"
BACKUP_DIR="${CONFIG_HOME}/mail-dotfiles-backups/${TIMESTAMP}"

backup_path() {
  local path="$1"
  local relative_path="${path#"${HOME}/"}"
  local backup_path="${BACKUP_DIR}/${relative_path}"

  if [ ! -e "${path}" ] && [ ! -L "${path}" ]; then
    return 0
  fi

  mkdir -p "$(dirname "${backup_path}")"
  mv "${path}" "${backup_path}"
  echo "Backed up ${path} to ${backup_path}"
}

ensure_symlink() {
  local source_path="$1"
  local target_path="$2"
  local current_target=""

  mkdir -p "$(dirname "${target_path}")"

  if [ -L "${target_path}" ]; then
    current_target="$(readlink "${target_path}")"
    if [ "${current_target}" = "${source_path}" ]; then
      echo "Already linked ${target_path}"
      return 0
    fi
    rm "${target_path}"
  elif [ -e "${target_path}" ]; then
    backup_path "${target_path}"
  fi

  ln -s "${source_path}" "${target_path}"
  echo "Linked ${target_path} -> ${source_path}"
}

main() {
  local local_path=""
  local relative_path=""

  if [ ! -d "${SOURCE_DIR}" ]; then
    echo "Missing source directory: ${SOURCE_DIR}" >&2
    exit 1
  fi

  mkdir -p \
    "${CONFIG_HOME}/aerc" \
    "${CONFIG_HOME}/isync" \
    "${CONFIG_HOME}/msmtp" \
    "${CONFIG_HOME}/notmuch/personal/hooks" \
    "${CONFIG_HOME}/notmuch/work/hooks" \
    "${CONFIG_HOME}/oama" \
    "${BIN_HOME}"

  chmod 700 \
    "${CONFIG_HOME}/aerc" \
    "${CONFIG_HOME}/isync" \
    "${CONFIG_HOME}/msmtp" \
    "${CONFIG_HOME}/notmuch" \
    "${CONFIG_HOME}/notmuch/personal" \
    "${CONFIG_HOME}/notmuch/work" \
    "${CONFIG_HOME}/oama"

  for relative_path in \
    aerc/aerc.conf \
    aerc/accounts.conf.example \
    aerc/query-map-personal \
    aerc/query-map-work \
    isync/mbsyncrc.example \
    msmtp/config.example \
    notmuch/personal/config.example \
    notmuch/personal/hooks/post-new \
    notmuch/work/config.example \
    notmuch/work/hooks/post-new \
    oama/config.yaml.example; do
    ensure_symlink \
      "${SOURCE_DIR}/${relative_path}" \
      "${CONFIG_HOME}/${relative_path}"
  done

  for relative_path in \
    mail-send-disabled \
    mail-sync-personal \
    mail-sync-work; do
    ensure_symlink \
      "${SOURCE_DIR}/bin/${relative_path}" \
      "${BIN_HOME}/${relative_path}"
  done

  for local_path in \
    "${CONFIG_HOME}/aerc/accounts.conf" \
    "${CONFIG_HOME}/isync/mbsyncrc" \
    "${CONFIG_HOME}/msmtp/config" \
    "${CONFIG_HOME}/notmuch/personal/config" \
    "${CONFIG_HOME}/notmuch/work/config" \
    "${CONFIG_HOME}/oama/config.yaml"; do
    if [ -f "${local_path}" ]; then
      chmod 600 "${local_path}"
    fi
  done

  echo
  echo "Local account files were preserved. See ${SOURCE_DIR}/README.md"
  echo "for the files that must be created from the tracked examples."
}

main "$@"
