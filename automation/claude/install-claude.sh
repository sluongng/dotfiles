#!/usr/bin/env bash

set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="${DOTFILES_DIR}/config/claude"
TARGET_DIR="${CLAUDE_CONFIG_DIR:-${HOME}/.claude}"
TIMESTAMP="$(date +%Y%m%d%H%M%S)"
BACKUP_DIR="${TARGET_DIR}/backups/install-claude-${TIMESTAMP}"
MERGE_SETTINGS_SCRIPT="${DOTFILES_DIR}/automation/claude/merge-settings.py"
MARKETPLACE_NAME="sluongng-dotfiles"

backup_path() {
  local path="$1"
  local relative_path="${path#"${TARGET_DIR}/"}"
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

prune_stale_skill_links() {
  local target_path=""
  local current_target=""

  [ -d "${TARGET_DIR}/skills" ] || return 0

  while IFS= read -r target_path; do
    current_target="$(readlink "${target_path}")"
    if [[ "${current_target}" == "${SOURCE_DIR}/skills/"* ]] && [ ! -e "${current_target}" ]; then
      rm "${target_path}"
      echo "Removed stale skill link ${target_path}"
    fi
  done < <(find "${TARGET_DIR}/skills" -mindepth 1 -maxdepth 1 -type l | sort)
}

register_marketplace() {
  if ! command -v claude >/dev/null 2>&1; then
    echo "claude CLI not found; skipping marketplace registration."
    echo "  Register it later with: claude plugin marketplace add \"${SOURCE_DIR}\""
    return 0
  fi

  if claude plugin marketplace list 2>/dev/null | grep -q "${MARKETPLACE_NAME}"; then
    echo "Marketplace '${MARKETPLACE_NAME}' already registered; updating."
    claude plugin marketplace update "${MARKETPLACE_NAME}" >/dev/null 2>&1 || true
  else
    if claude plugin marketplace add "${SOURCE_DIR}" >/dev/null 2>&1; then
      echo "Registered marketplace '${MARKETPLACE_NAME}' from ${SOURCE_DIR}"
    else
      echo "Could not auto-register the marketplace. Add it manually with:"
      echo "  claude plugin marketplace add \"${SOURCE_DIR}\""
    fi
  fi

  echo "Install plugins from it with, e.g.:"
  echo "  claude plugin install buildbuddy@${MARKETPLACE_NAME}"
  echo "  claude plugin install buck2@${MARKETPLACE_NAME}"
  echo "  claude plugin install tinytree-dev@${MARKETPLACE_NAME}"
  echo "  claude plugin install etoro-api@${MARKETPLACE_NAME}"
}

main() {
  local relative_path=""
  local skill_name=""
  local source_path=""

  if [ ! -d "${SOURCE_DIR}" ]; then
    echo "Missing source directory: ${SOURCE_DIR}" >&2
    exit 1
  fi

  if [ ! -f "${MERGE_SETTINGS_SCRIPT}" ]; then
    echo "Missing merge script: ${MERGE_SETTINGS_SCRIPT}" >&2
    exit 1
  fi

  mkdir -p "${TARGET_DIR}" "${TARGET_DIR}/skills"

  # Merge the tracked settings baseline (preserves Claude-managed keys).
  python3 "${MERGE_SETTINGS_SCRIPT}" \
    --baseline "${SOURCE_DIR}/settings.json" \
    --target "${TARGET_DIR}/settings.json"

  # Global user instructions.
  if [ -f "${SOURCE_DIR}/CLAUDE.md" ]; then
    ensure_symlink "${SOURCE_DIR}/CLAUDE.md" "${TARGET_DIR}/CLAUDE.md"
  fi

  # Personal skills: one symlink per tracked skill directory.
  while IFS= read -r source_path; do
    skill_name="$(basename "${source_path}")"
    ensure_symlink "${source_path}" "${TARGET_DIR}/skills/${skill_name}"
  done < <(find "${SOURCE_DIR}/skills" -mindepth 1 -maxdepth 1 -type d | sort)

  prune_stale_skill_links

  # Local plugin marketplace.
  register_marketplace
}

main "$@"
