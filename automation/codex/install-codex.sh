#!/usr/bin/env bash

set -euo pipefail

DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SOURCE_DIR="${DOTFILES_DIR}/config/codex"
SOURCE_SCRIPTS_DIR="${DOTFILES_DIR}/config/scripts"
TARGET_DIR="${CODEX_HOME:-${HOME}/.codex}"
TARGET_BIN_DIR="${CODEX_BIN_HOME:-${HOME}/.local/bin}"
TIMESTAMP="$(date +%Y%m%d%H%M%S)"
BACKUP_DIR="${TARGET_DIR}/backups/install-codex-${TIMESTAMP}"
RENDER_CONFIG_SCRIPT="${DOTFILES_DIR}/automation/codex/render-config.py"
MARKETPLACE_NAME="sluongng-dotfiles"

backup_path() {
  local path="$1"
  local relative_path=""
  local backup_path=""

  if [ ! -e "${path}" ] && [ ! -L "${path}" ]; then
    return 0
  fi

  if [[ "${path}" == "${TARGET_DIR}/"* ]]; then
    relative_path="${path#"${TARGET_DIR}/"}"
  elif [[ "${path}" == "${TARGET_BIN_DIR}/"* ]]; then
    relative_path="user-bin/${path#"${TARGET_BIN_DIR}/"}"
  elif [[ "${path}" == "${HOME}/"* ]]; then
    relative_path="home/${path#"${HOME}/"}"
  else
    echo "Refusing to back up path outside configured user paths: ${path}" >&2
    return 1
  fi
  backup_path="${BACKUP_DIR}/${relative_path}"

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

ensure_regular_file() {
  # Role loading uses the sensitive-file reader, which does not follow symlinks.
  # Stage beside the destination and replace its directory entry atomically so
  # upgrading an old role symlink never writes through it into tracked source.
  python3 - "$1" "$2" "${TARGET_DIR}" "${BACKUP_DIR}" <<'PY'
import filecmp
import os
from pathlib import Path
import shutil
import sys
import tempfile

source, target, target_root, backup_root = map(Path, sys.argv[1:])
relative = target.relative_to(target_root)
if target.parent.is_symlink():
    raise SystemExit(f"Refusing role deployment through symlink directory: {target.parent}")
target.parent.mkdir(parents=True, exist_ok=True)
if target.exists() and not target.is_symlink() and not target.is_file():
    raise SystemExit(f"Refusing to replace non-file role destination: {target}")
if target.is_file() and not target.is_symlink() and filecmp.cmp(source, target, shallow=False):
    print(f"Already copied {target}")
    raise SystemExit(0)

fd, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
os.close(fd)
temporary = Path(temporary_name)
try:
    shutil.copy2(source, temporary)
    if os.path.lexists(target):
        backup = backup_root / relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        suffix = 0
        while os.path.lexists(backup):
            suffix += 1
            backup = (backup_root / relative).with_name(f"{target.name}.{suffix}")
        shutil.copy2(target, backup, follow_symlinks=False)
        print(f"Backed up {target} to {backup}")
    os.replace(temporary, target)
finally:
    temporary.unlink(missing_ok=True)
print(f"Copied {source} -> {target}")
PY
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

detect_nested_feature_tables() {
  local override="${CODEX_NESTED_FEATURE_TABLES:-}"
  local probe_home=""

  case "${override}" in
    true | false)
      printf '%s\n' "${override}"
      return 0
      ;;
    "") ;;
    *)
      echo "CODEX_NESTED_FEATURE_TABLES must be true or false" >&2
      exit 1
      ;;
  esac

  if ! command -v codex >/dev/null 2>&1; then
    printf '%s\n' false
    return 0
  fi

  probe_home="$(mktemp -d "${TMPDIR:-/tmp}/codex-config-probe.XXXXXX")"
  mkdir -p "${probe_home}"
  cat > "${probe_home}/config.toml" <<'EOF'
[features.current_time_reminder]
enabled = true
clock_source = "system"
delivery_mode = "after_user_or_tool_output"
sleep_tool = true

[features.multi_agent_v2]
enabled = true

[agents]
max_concurrent_threads_per_session = 12
max_depth = 2
EOF
  if CODEX_HOME="${probe_home}" codex features list >/dev/null 2>&1; then
    printf '%s\n' true
  else
    printf '%s\n' false
  fi
  rm -rf "${probe_home}"
}

detect_context_management_table() {
  # Older runtimes can support other nested feature tables while still parsing
  # context_management as an unknown boolean flag. Probe it independently.
  # Force false when sharing this config with a less capable App runtime.
  local override="${CODEX_CONTEXT_MANAGEMENT_TABLE:-}"
  local probe_home=""
  case "${override}" in
    true | false)
      printf '%s\n' "${override}"
      return 0
      ;;
    "") ;;
    *)
      echo "CODEX_CONTEXT_MANAGEMENT_TABLE must be true or false" >&2
      return 1
      ;;
  esac
  if ! command -v codex >/dev/null 2>&1; then
    printf '%s\n' false
    return 0
  fi
  probe_home="$(mktemp -d "${TMPDIR:-/tmp}/codex-context-probe.XXXXXX")"
  cat > "${probe_home}/config.toml" <<'EOF'
[features.context_management]
experimental_mode = true
EOF
  if CODEX_HOME="${probe_home}" codex features list >/dev/null 2>&1; then
    printf '%s\n' true
  else
    printf '%s\n' false
  fi
  rm -rf "${probe_home}"
}

main() {
  local relative_path=""
  local skill_name=""
  local source_path=""
  local target_config_path="${TARGET_DIR}/config.toml"
  local local_config_path="${TARGET_DIR}/config.local.toml"
  local projects_local_path="${TARGET_DIR}/projects.local.toml"
  local runtime_local_path="${TARGET_DIR}/runtime.local.toml"
  local platform=""
  local nested_feature_tables=""
  local context_management_table=""

  if [ ! -d "${SOURCE_DIR}" ]; then
    echo "Missing source directory: ${SOURCE_DIR}" >&2
    exit 1
  fi

  if [ ! -f "${RENDER_CONFIG_SCRIPT}" ]; then
    echo "Missing render script: ${RENDER_CONFIG_SCRIPT}" >&2
    exit 1
  fi

  mkdir -p "${TARGET_DIR}" "${TARGET_DIR}/agents" "${TARGET_DIR}/skills" "${TARGET_BIN_DIR}"

  platform="${CODEX_CONFIG_PLATFORM:-$(uname -s)}"
  case "${platform}" in
    Darwin | Linux) ;;
    *)
      echo "Unsupported Codex config platform: ${platform}" >&2
      exit 1
      ;;
  esac
  nested_feature_tables="$(detect_nested_feature_tables)"
  context_management_table="$(detect_context_management_table)"

  python3 "${RENDER_CONFIG_SCRIPT}" \
    --shared "${SOURCE_DIR}/config.toml" \
    --local "${local_config_path}" \
    --projects "${projects_local_path}" \
    --runtime "${runtime_local_path}" \
    --target "${target_config_path}" \
    --platform "${platform}" \
    --nested-feature-tables "${nested_feature_tables}" \
    --context-management-table "${context_management_table}" \
    --marketplace-name "${MARKETPLACE_NAME}" \
    --marketplace-source "${SOURCE_DIR}"

  echo "Codex packaged zsh fork backends disabled (${platform})"
  echo "Codex nested feature tables supported: ${nested_feature_tables}"
  echo "Codex context management table supported: ${context_management_table}"

  if [ -f "${SOURCE_DIR}/AGENTS.md" ]; then
    ensure_symlink "${SOURCE_DIR}/AGENTS.md" "${TARGET_DIR}/AGENTS.md"
  fi

  if [ -d "${SOURCE_DIR}/agents" ]; then
    while IFS= read -r source_path; do
      relative_path="${source_path#"${SOURCE_DIR}/"}"
      ensure_regular_file "${source_path}" "${TARGET_DIR}/${relative_path}"
    done < <(find "${SOURCE_DIR}/agents" -type f | sort)
  fi

  # Current CLI profiles are full config layers next to the generated config.
  if [ -d "${SOURCE_DIR}/profiles" ]; then
    while IFS= read -r source_path; do
      ensure_regular_file "${source_path}" "${TARGET_DIR}/$(basename "${source_path}")"
    done < <(find "${SOURCE_DIR}/profiles" -maxdepth 1 -type f -name '*.config.toml' | sort)
  fi

  while IFS= read -r source_path; do
    skill_name="$(basename "${source_path}")"
    if [ ! -f "${source_path}/SKILL.md" ]; then
      continue
    fi
    ensure_symlink "${source_path}" "${TARGET_DIR}/skills/${skill_name}"
  done < <(find "${SOURCE_DIR}/skills" -mindepth 1 -maxdepth 1 -type d ! -name '.system' | sort)

  if [ -d "${SOURCE_SCRIPTS_DIR}" ]; then
    while IFS= read -r source_path; do
      ensure_symlink "${source_path}" "${TARGET_BIN_DIR}/$(basename "${source_path}")"
    done < <(find "${SOURCE_SCRIPTS_DIR}" -mindepth 1 -maxdepth 1 -type f -perm -u+x | sort)
  fi

  prune_stale_skill_links
  sync_tracked_plugin_caches
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  main "$@"
fi
