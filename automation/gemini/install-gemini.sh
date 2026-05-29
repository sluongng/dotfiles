#!/usr/bin/env bash

set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="${DOTFILES_DIR}/config/gemini"
TARGET_DIR="${HOME}/.gemini/config"
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

prune_stale_links() {
  local parent_dir="$1"
  local source_parent="$2"
  local target_path=""
  local current_target=""

  if [ ! -d "${parent_dir}" ]; then
    return 0
  fi

  while IFS= read -r target_path; do
    current_target="$(readlink "${target_path}")"
    if [[ "${current_target}" == "${source_parent}/"* ]] && [ ! -e "${current_target}" ]; then
      rm "${target_path}"
      echo "Removed stale link ${target_path}"
    fi
  done < <(find "${parent_dir}" -mindepth 1 -maxdepth 1 -type l | sort)
}

main() {
  if [ ! -d "${SOURCE_DIR}" ]; then
    echo "Missing source directory: ${SOURCE_DIR}" >&2
    exit 1
  fi

  mkdir -p "${TARGET_DIR}" "${TARGET_DIR}/skills" "${TARGET_DIR}/plugins"

  # Link config files
  if [ -f "${SOURCE_DIR}/config.json" ]; then
    ensure_symlink "${SOURCE_DIR}/config.json" "${TARGET_DIR}/config.json"
  fi
  if [ -f "${SOURCE_DIR}/mcp_config.json" ]; then
    ensure_symlink "${SOURCE_DIR}/mcp_config.json" "${TARGET_DIR}/mcp_config.json"
  fi

  # Link custom skills
  if [ -d "${SOURCE_DIR}/skills" ]; then
    while IFS= read -r source_path; do
      local skill_name
      skill_name="$(basename "${source_path}")"
      ensure_symlink "${source_path}" "${TARGET_DIR}/skills/${skill_name}"
    done < <(find "${SOURCE_DIR}/skills" -mindepth 1 -maxdepth 1 -type d | sort)
  fi

  # Link custom plugins
  if [ -d "${SOURCE_DIR}/plugins" ]; then
    while IFS= read -r source_path; do
      local plugin_name
      plugin_name="$(basename "${source_path}")"
      ensure_symlink "${source_path}" "${TARGET_DIR}/plugins/${plugin_name}"
    done < <(find "${SOURCE_DIR}/plugins" -mindepth 1 -maxdepth 1 -type d | sort)
  fi

  # Prune stale links
  prune_stale_links "${TARGET_DIR}/skills" "${SOURCE_DIR}/skills"
  prune_stale_links "${TARGET_DIR}/plugins" "${SOURCE_DIR}/plugins"
}

main "$@"
