#!/usr/bin/env bash

set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="${DOTFILES_DIR}/config/codex"
TARGET_DIR="${HOME}/.codex"
TIMESTAMP="$(date +%Y%m%d%H%M%S)"

backup_path() {
  local path="$1"
  local backup_path="${path}.bak.${TIMESTAMP}"

  if [ ! -e "${path}" ] && [ ! -L "${path}" ]; then
    return 0
  fi

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
  local relative_path=""
  local skill_name=""
  local source_path=""

  if [ ! -d "${SOURCE_DIR}" ]; then
    echo "Missing source directory: ${SOURCE_DIR}" >&2
    exit 1
  fi

  mkdir -p "${TARGET_DIR}" "${TARGET_DIR}/agents" "${TARGET_DIR}/skills"

  ensure_symlink "${SOURCE_DIR}/config.toml" "${TARGET_DIR}/config.toml"

  while IFS= read -r source_path; do
    relative_path="${source_path#"${SOURCE_DIR}/"}"
    ensure_symlink "${source_path}" "${TARGET_DIR}/${relative_path}"
  done < <(find "${SOURCE_DIR}/agents" -type f | sort)

  while IFS= read -r source_path; do
    skill_name="$(basename "${source_path}")"
    ensure_symlink "${source_path}" "${TARGET_DIR}/skills/${skill_name}"
  done < <(find "${SOURCE_DIR}/skills" -mindepth 1 -maxdepth 1 -type d ! -name '.system' | sort)
}

main "$@"
