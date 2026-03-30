# Codex config

This directory only tracks non-sensitive Codex configuration that should be shared
via dotfiles.

Deploy it with:

```sh
./automation/codex/install-codex.sh
```

The deploy script manages these paths under `~/.codex`:

- renders `config.toml` from the tracked shared config plus local overlays
- tracked files under `agents/`
- tracked custom skill directories under `skills/`

It intentionally leaves `~/.codex/auth.json`, histories, logs, memories,
SQLite state, and Codex-managed system skills as local machine state.

Do not edit `~/.codex/config.toml` directly. Update the tracked shared config in
this directory, or use one of these machine-local files instead:

- `~/.codex/config.local.toml` for additive local-only settings
- `~/.codex/projects.local.toml` for local trust entries (`[projects]`)

Do not commit secrets or API keys here.
