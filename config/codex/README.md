# Codex config

This directory only tracks non-sensitive Codex configuration that should be shared
via dotfiles.

Deploy it with:

```sh
./automation/codex/install-codex.sh
```

Set `CODEX_HOME` to render the same tracked config into another Codex home,
for example:

```sh
CODEX_HOME="$HOME/.codexp" ./automation/codex/install-codex.sh
```

The deploy script manages these paths under `${CODEX_HOME:-~/.codex}`:

- preserves App-managed desktop, bundled plugin, and `node_repl` tables in
  `runtime.local.toml`, then renders `config.toml` from the tracked shared
  config plus local overlays
- tracked global `AGENTS.md`
- tracked files under `agents/`
- tracked custom skill directories under `skills/`
- tracked local plugins under `plugins/`, synced into Codex's plugin cache by
  plugin manifest name and version

Tracked plugin marketplaces can live in this directory as:

- `.agents/plugins/marketplace.json`
- `plugins/<plugin-name>/`

Enable those marketplaces from `${CODEX_HOME:-~/.codex}/config.local.toml`
with a local absolute `source` path. Keep development-only plugins under
`${CODEX_HOME:-~/.codex}/local` so they stay outside dotfiles git.

Keep desired `[plugins."<name>@<marketplace>"]` enabled state for tracked
personal plugins in `config.toml`. The marketplace location is machine-local,
but the desired plugin state must be part of the rendered source of truth so a
later deploy does not silently discard an install made by `codex plugin add`.

The deploy script materializes tracked local marketplace plugins into
`${CODEX_HOME:-~/.codex}/plugins/cache` by plugin manifest name and version.
Bump the plugin manifest version when changing tracked plugin contents so fresh
Codex sessions pick up the new cache entry, or clear the matching cache entry
to force a local refresh.

The rendered config is platform-aware:

- forked-zsh backends stay disabled on both macOS and Linux because the CLI and
  Desktop share config but may ship different resource layouts;
- it probes whether the installed CLI accepts nested feature configuration and
  emits the compatible legacy boolean form for older Codex releases;
- it disables the Linux Chrome Bridge-only `chatgpt-threads` plugin on macOS;
- it generates the tracked marketplace source from this checkout when a
  machine-local marketplace entry is not already present;
- redundant local plugin tables that exactly match tracked desired state are
  ignored, while conflicting overrides fail before replacing the live config.

It intentionally leaves `auth.json`, histories, logs, memories, SQLite state,
and Codex-managed system skills as local machine state inside the selected
Codex home.

Do not edit the rendered `config.toml` directly. Update the tracked shared
config in this directory, or use one of these machine-local files instead:

- `${CODEX_HOME:-~/.codex}/config.local.toml` for additive local-only settings
- `${CODEX_HOME:-~/.codex}/projects.local.toml` for local trust entries (`[projects]`)
- `${CODEX_HOME:-~/.codex}/runtime.local.toml` for App-managed desktop,
  bundled plugin, and `node_repl` state; the deploy script updates this file
  automatically

Do not commit secrets or API keys here.
