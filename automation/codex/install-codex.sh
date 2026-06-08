#!/usr/bin/env bash

set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="${DOTFILES_DIR}/config/codex"
TARGET_DIR="${CODEX_HOME:-${HOME}/.codex}"
TIMESTAMP="$(date +%Y%m%d%H%M%S)"
BACKUP_DIR="${TARGET_DIR}/backups/install-codex-${TIMESTAMP}"
RENDER_CONFIG_SCRIPT="${DOTFILES_DIR}/automation/codex/render-config.py"

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

  while IFS= read -r target_path; do
    current_target="$(readlink "${target_path}")"
    if [[ "${current_target}" != "${SOURCE_DIR}/skills/"* ]]; then
      continue
    fi

    if [ ! -e "${current_target}" ]; then
      rm "${target_path}"
      echo "Removed stale skill link ${target_path}"
    elif [ ! -f "${current_target}/SKILL.md" ]; then
      rm "${target_path}"
      echo "Removed non-skill link ${target_path}"
    fi
  done < <(find "${TARGET_DIR}/skills" -mindepth 1 -maxdepth 1 -type l | sort)
}

sync_tracked_plugin_caches() {
  local marketplace_manifest="${SOURCE_DIR}/.agents/plugins/marketplace.json"
  local marketplace_name=""
  local manifest_path=""
  local plugin_dir=""
  local metadata=""
  local plugin_name=""
  local plugin_version=""
  local cache_dir=""
  local tmp_dir=""

  if [ ! -d "${SOURCE_DIR}/plugins" ]; then
    return 0
  fi
  if [ ! -f "${marketplace_manifest}" ]; then
    echo "Missing plugin marketplace manifest: ${marketplace_manifest}" >&2
    exit 1
  fi

  marketplace_name="$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["name"])' "${marketplace_manifest}")"
  if [ -z "${marketplace_name}" ]; then
    echo "Invalid plugin marketplace metadata: ${marketplace_manifest}" >&2
    exit 1
  fi

  while IFS= read -r manifest_path; do
    plugin_dir="$(cd "$(dirname "${manifest_path}")/.." && pwd)"
    metadata="$(python3 -c 'import json, sys; data = json.load(open(sys.argv[1])); print(data["name"] + "\t" + data["version"])' "${manifest_path}")"
    IFS=$'\t' read -r plugin_name plugin_version <<< "${metadata}"

    if [ -z "${plugin_name}" ] || [ -z "${plugin_version}" ]; then
      echo "Invalid plugin manifest metadata: ${manifest_path}" >&2
      exit 1
    fi

    cache_dir="${TARGET_DIR}/plugins/cache/${marketplace_name}/${plugin_name}/${plugin_version}"
    tmp_dir="${cache_dir}.tmp.${TIMESTAMP}"

    rm -rf "${tmp_dir}"
    mkdir -p "$(dirname "${cache_dir}")" "${tmp_dir}"
    (
      cd "${plugin_dir}"
      tar -cf - .
    ) | (
      cd "${tmp_dir}"
      tar -xf -
    )
    rm -rf "${cache_dir}"
    mv "${tmp_dir}" "${cache_dir}"
    echo "Synced plugin cache ${cache_dir}"
  done < <(find "${SOURCE_DIR}/plugins" -mindepth 3 -maxdepth 3 -path '*/.codex-plugin/plugin.json' -type f | sort)
}

main() {
  local relative_path=""
  local skill_name=""
  local source_path=""
  local target_config_path="${TARGET_DIR}/config.toml"
  local local_config_path="${TARGET_DIR}/config.local.toml"
  local projects_local_path="${TARGET_DIR}/projects.local.toml"

  if [ ! -d "${SOURCE_DIR}" ]; then
    echo "Missing source directory: ${SOURCE_DIR}" >&2
    exit 1
  fi

  if [ ! -f "${RENDER_CONFIG_SCRIPT}" ]; then
    echo "Missing render script: ${RENDER_CONFIG_SCRIPT}" >&2
    exit 1
  fi

  mkdir -p "${TARGET_DIR}" "${TARGET_DIR}/agents" "${TARGET_DIR}/skills"

  python3 "${RENDER_CONFIG_SCRIPT}" \
    --shared "${SOURCE_DIR}/config.toml" \
    --local "${local_config_path}" \
    --projects "${projects_local_path}" \
    --target "${target_config_path}"

  if [ -f "${SOURCE_DIR}/AGENTS.md" ]; then
    ensure_symlink "${SOURCE_DIR}/AGENTS.md" "${TARGET_DIR}/AGENTS.md"
  fi

  if [ -d "${SOURCE_DIR}/agents" ]; then
    while IFS= read -r source_path; do
      relative_path="${source_path#"${SOURCE_DIR}/"}"
      ensure_symlink "${source_path}" "${TARGET_DIR}/${relative_path}"
    done < <(find "${SOURCE_DIR}/agents" -type f | sort)
  fi

  while IFS= read -r source_path; do
    skill_name="$(basename "${source_path}")"
    if [ ! -f "${source_path}/SKILL.md" ]; then
      continue
    fi
    ensure_symlink "${source_path}" "${TARGET_DIR}/skills/${skill_name}"
  done < <(find "${SOURCE_DIR}/skills" -mindepth 1 -maxdepth 1 -type d ! -name '.system' | sort)

  prune_stale_skill_links
  sync_tracked_plugin_caches
}

main "$@"
