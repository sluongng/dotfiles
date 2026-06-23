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

- renders `config.toml` from the tracked shared config plus local overlays
- tracked global `AGENTS.md`
- tracked files under `agents/`
- tracked custom skill directories under `skills/`

Tracked plugin marketplaces can live in this directory as:

- `.agents/plugins/marketplace.json`
- `plugins/<plugin-name>/`

Enable those marketplaces from `${CODEX_HOME:-~/.codex}/config.local.toml`
with a local absolute `source` path. Keep development-only plugins under
`${CODEX_HOME:-~/.codex}/local` so they stay outside dotfiles git.

Codex materializes enabled marketplace plugins into
`${CODEX_HOME:-~/.codex}/plugins/cache`; bump the plugin manifest version when
changing tracked plugin contents, or clear the matching cache entry to force a
local refresh.

It intentionally leaves `auth.json`, histories, logs, memories, SQLite state,
and Codex-managed system skills as local machine state inside the selected
Codex home.

Do not edit the rendered `config.toml` directly. Update the tracked shared
config in this directory, or use one of these machine-local files instead:

- `${CODEX_HOME:-~/.codex}/config.local.toml` for additive local-only settings
- `${CODEX_HOME:-~/.codex}/projects.local.toml` for local trust entries (`[projects]`)

Do not commit secrets or API keys here.
