# Claude Code config

This directory tracks non-sensitive Claude Code configuration shared via
dotfiles. It is the Claude-side counterpart to `config/codex`.

Deploy it with:

```sh
./automation/claude/install-claude.sh
```

The deploy script manages these paths under `~/.claude` (or `$CLAUDE_CONFIG_DIR`):

- merges the tracked `settings.json` baseline into `~/.claude/settings.json`
  (preserving Claude-managed keys such as `enabledPlugins` and theme)
- symlinks the tracked global `CLAUDE.md`
- symlinks each tracked personal skill directory under `skills/`
- registers the local plugin marketplace from this directory

## Skills

Personal skills live under `skills/<name>/SKILL.md` and are symlinked into
`~/.claude/skills/`. Each skill may bundle `scripts/`, `references/`, and
`assets/` subdirectories. The skill `description` is what Claude uses to decide
when to load the skill, so keep it specific and trigger-oriented.

A few skills carry caveats:

- `hatch-pet` targets the **Codex** pet asset format and an `imagegen`
  image-generation skill that Claude Code does not ship. It is kept for
  portability; substitute an available image generator.
- `buck2` (plugin) `buildbuddy-stack-maintainer` includes a browser-linking
  helper script that drove the Codex Chrome native host. Under Claude, use the
  `chrome-devtools` skill (Chrome DevTools MCP) instead.

## Plugins and the marketplace

Tracked plugins live under `plugins/<plugin-name>/` with a
`.claude-plugin/plugin.json`, and `.claude-plugin/marketplace.json` lists them.

The installer registers the marketplace; install plugins explicitly:

```sh
claude plugin marketplace add ~/.dotfiles/config/claude   # done by installer
claude plugin install buildbuddy@sluongng-dotfiles
claude plugin install buck2@sluongng-dotfiles
claude plugin install tinytree-dev@sluongng-dotfiles
claude plugin install etoro-api@sluongng-dotfiles
```

Validate the manifests after editing:

```sh
claude plugin validate config/claude --strict
```

Keep development-only plugins (for example `buildbuddy-dev`) and other local
state outside dotfiles git — they are not tracked here.

## Machine-local state

The script intentionally leaves `~/.claude/.credentials.json`, histories, logs,
sessions, todos, projects/memory, and other Claude-managed runtime state as
local machine state. Machine-specific permissions belong in
`~/.claude/settings.local.json`, which is not tracked here.

Do not commit secrets or API keys.
