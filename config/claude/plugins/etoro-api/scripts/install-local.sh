#!/usr/bin/env bash
set -euo pipefail

plugin_dir="$(cd "$(dirname "$0")/.." && pwd)"
bin_dir="$HOME/.local/bin"
mkdir -p "$bin_dir"
chmod +x "$plugin_dir/scripts/etoro_api.py"
ln -sfn "$plugin_dir/scripts/etoro_api.py" "$bin_dir/etoro-api"
printf 'Installed %s\n' "$bin_dir/etoro-api"
