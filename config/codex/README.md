# Codex config

This directory only tracks non-sensitive Codex configuration that should be shared
via dotfiles.

Deploy it with:

```sh
./automation/codex/install-codex.sh
```

The deploy script symlinks these repo-managed paths into `~/.codex`:

- `config.toml`
- tracked files under `agents/`
- tracked custom skill directories under `skills/`

It intentionally leaves `~/.codex/auth.json`, histories, logs, memories,
SQLite state, and Codex-managed system skills as local machine state.

Do not commit secrets or API keys here. Keep machine-specific or sensitive
overrides in ignored paths such as `~/.codex/local/` or `~/.codex/*.local.toml`.
