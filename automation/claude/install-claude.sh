#!/usr/bin/env bash

set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="${DOTFILES_DIR}/config/claude"
CODEX_SOURCE_DIR="${DOTFILES_DIR}/config/codex"
CODEX_ONLY_SKILLS_FILE="${SOURCE_DIR}/codex-only-skills.txt"
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
  local skill_name=""

  [ -d "${TARGET_DIR}/skills" ] || return 0

  while IFS= read -r target_path; do
    current_target="$(readlink "${target_path}")"
    skill_name="$(basename "${target_path}")"
    if [[ "${current_target}" == "${SOURCE_DIR}/skills/"* ]] && [ ! -e "${current_target}" ]; then
      rm "${target_path}"
      echo "Removed stale skill link ${target_path}"
    elif [[ "${current_target}" == "${CODEX_SOURCE_DIR}/skills/"* ]] &&
      { [ ! -e "${current_target}" ] || is_codex_only_skill "${skill_name}"; }; then
      rm "${target_path}"
      echo "Removed stale skill link ${target_path}"
    fi
  done < <(find "${TARGET_DIR}/skills" -mindepth 1 -maxdepth 1 -type l | sort)
}

is_codex_only_skill() {
  grep -qxF "$1" <(sed -e 's/#.*//' -e 's/[[:space:]]*$//' "${CODEX_ONLY_SKILLS_FILE}")
}

link_skills() {
  local source_path=""
  local skill_name=""

  # Claude forks first; they take precedence over same-named Codex skills.
  while IFS= read -r source_path; do
    ensure_symlink "$(dirname "${source_path}")" "${TARGET_DIR}/skills/$(basename "$(dirname "${source_path}")")"
  done < <(find "${SOURCE_DIR}/skills" -mindepth 2 -maxdepth 2 -name SKILL.md | sort)

  # Shared skills come straight from the Codex sources.
  while IFS= read -r source_path; do
    source_path="$(dirname "${source_path}")"
    skill_name="$(basename "${source_path}")"
    if [ -e "${SOURCE_DIR}/skills/${skill_name}/SKILL.md" ] || is_codex_only_skill "${skill_name}"; then
      continue
    fi
    ensure_symlink "${source_path}" "${TARGET_DIR}/skills/${skill_name}"
  done < <(find "${CODEX_SOURCE_DIR}/skills" -mindepth 2 -maxdepth 2 -name SKILL.md | sort)
}

register_marketplace() {
  local plugin=""

  if ! command -v claude >/dev/null 2>&1; then
    echo "claude CLI not found; skipping marketplace registration."
    echo "  Register it later with: claude plugin marketplace add \"${CODEX_SOURCE_DIR}\""
    return 0
  fi

  # The marketplace shares the Codex plugin sources. Re-register it when an
  # older install still points at another directory.
  if claude plugin marketplace list 2>/dev/null | grep -q "${MARKETPLACE_NAME}"; then
    if claude plugin marketplace list 2>/dev/null | grep -qF "${CODEX_SOURCE_DIR}"; then
      echo "Marketplace '${MARKETPLACE_NAME}' already registered; updating."
      claude plugin marketplace update "${MARKETPLACE_NAME}" >/dev/null 2>&1 || true
    else
      claude plugin marketplace remove "${MARKETPLACE_NAME}" >/dev/null 2>&1 || true
    fi
  fi
  if ! claude plugin marketplace list 2>/dev/null | grep -q "${MARKETPLACE_NAME}"; then
    if claude plugin marketplace add "${CODEX_SOURCE_DIR}" >/dev/null 2>&1; then
      echo "Registered marketplace '${MARKETPLACE_NAME}' from ${CODEX_SOURCE_DIR}"
    else
      echo "Could not auto-register the marketplace. Add it manually with:"
      echo "  claude plugin marketplace add \"${CODEX_SOURCE_DIR}\""
      return 0
    fi
  fi

  # Install every plugin the tracked baseline enables, plus the machine-local
  # etoro-api plugin when its untracked source exists.
  while IFS= read -r plugin; do
    if claude plugin install "${plugin}" >/dev/null 2>&1; then
      echo "Installed plugin ${plugin}"
    else
      echo "Could not install plugin ${plugin}; run: claude plugin install ${plugin}"
    fi
  done < <(
    python3 - "${SOURCE_DIR}/settings.json" <<'PY'
import json
import sys

enabled = json.load(open(sys.argv[1])).get("enabledPlugins", {})
for name, on in enabled.items():
    if on:
        print(name)
PY
    if [ -d "${CODEX_SOURCE_DIR}/plugins/etoro-api/skills" ]; then
      echo "etoro-api@${MARKETPLACE_NAME}"
    fi
  )
}

main() {
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

  # Global user instructions. CLAUDE.md imports the shared Codex AGENTS.md,
  # which Claude Code does not read from ~/.claude on its own.
  if [ -f "${SOURCE_DIR}/CLAUDE.md" ]; then
    ensure_symlink "${SOURCE_DIR}/CLAUDE.md" "${TARGET_DIR}/CLAUDE.md"
  fi
  ensure_symlink "${CODEX_SOURCE_DIR}/AGENTS.md" "${TARGET_DIR}/AGENTS.md"

  # Personal skills: Claude forks plus the shared Codex skills.
  link_skills

  prune_stale_skill_links

  # Local plugin marketplace.
  register_marketplace
}

main "$@"
