# Claude Code config

This directory tracks non-sensitive Claude Code configuration shared via
dotfiles. `config/codex` is the source of truth for skills and plugins; this
directory holds only Claude-specific settings, forks, and wrappers.

Deploy it with:

```sh
./automation/claude/install-claude.sh
```

The deploy script manages these paths under `~/.claude` (or `$CLAUDE_CONFIG_DIR`):

- merges the tracked `settings.json` baseline into `~/.claude/settings.json`,
  preserving keys written at runtime such as hooks and theme
- symlinks the tracked global `CLAUDE.md`, and `AGENTS.md` from `config/codex`
- symlinks skills into `skills/` (see below)
- registers the `sluongng-dotfiles` marketplace from `config/codex` and
  installs every plugin the baseline enables

## Instructions

Claude Code reads a project's `AGENTS.md` natively but ignores
`~/.claude/AGENTS.md`. The global `CLAUDE.md` therefore imports it with
`@AGENTS.md`, then lists the few rules that differ for Claude Code. Edit shared
guidance in `config/codex/AGENTS.md`.

## Mode

The baseline matches the Codex `approval_policy = "never"` and
`sandbox_mode = "danger-full-access"` setup: `bypassPermissions` by default, no
bypass warning, sandbox off, high effort, and telemetry off.

## Skills

Every skill under `config/codex/skills` is linked into `~/.claude/skills`
except those listed in `codex-only-skills.txt`, which drive Codex-only runtime
surfaces. A directory under `skills/` here is a Claude fork. It replaces the
same-named Codex skill, or adds a Claude-only skill such as `chrome-devtools`
or `playwright`.

Edit shared skills in `config/codex/skills`; both tools pick up the change.

## Plugins

`config/codex/.claude-plugin/marketplace.json` exposes the Codex plugin
directories to Claude Code as `strict: false` plugins, so Claude reads the same
`skills/` trees without a second manifest. Desired enabled state lives in
`enabledPlugins` in `settings.json`, mirroring `[plugins.*]` in the Codex
config. `etoro-api` is untracked; the installer adds it only when its source
exists locally.

Validate after editing:

```sh
claude plugin validate config/codex
```

## Machine-local state

The script leaves `~/.claude/.credentials.json`, histories, sessions,
projects/memory, and other Claude-managed runtime state as local machine state.
Machine-specific permissions belong in `~/.claude/settings.local.json`, which is
not tracked. The `local-gerrit` skill is linked from its local checkout and
stays machine-local.

Do not commit secrets or API keys.
