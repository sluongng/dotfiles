---
name: codex-automaton
description: Manage local Codex CLI automations backed by systemd user timers. Use when Codex needs to inspect, import, run, update, install, or troubleshoot local `codex-automaton` automations, migrate Codex App automations into CLI-managed timers, view recent automation threads, or manage the localhost Automaton WebUI service.
---

# Codex Automaton

## Overview

Use the installed `codex-automaton` CLI for local Codex automations. It stores automation TOML under `${XDG_CONFIG_HOME:-$HOME/.config}/codex-automaton`, run state under `${XDG_STATE_HOME:-$HOME/.local/state}/codex-automaton`, and schedules runs through `systemd --user`.

## Start Here

Verify the command and local setup first:

```bash
command -v codex-automaton
codex-automaton --json doctor
```

Then list installed automations:

```bash
codex-automaton --json automation list
```

Prefer `--json` for analysis and scripting. Use human output only for quick terminal inspection.

## Common Workflows

Import Codex App automations without enabling duplicate timers:

```bash
codex-automaton automation import-codex-app --out automations --force
codex-automaton automation install automations/buildbuddy-flaky-test-fixer.toml --no-enable
```

Inspect or dry-run an automation before allowing it to execute:

```bash
codex-automaton --json automation get buildbuddy-flaky-test-fixer
codex-automaton --json automation run --id buildbuddy-flaky-test-fixer --dry-run
```

Update schedule, model, thinking, tier, or prompt:

```bash
codex-automaton automation update buildbuddy-flaky-test-fixer --on-calendar '*-*-* 09:00:00'
codex-automaton automation update buildbuddy-flaky-test-fixer --model gpt-5.5 --reasoning-effort xhigh --speed fast
codex-automaton automation update buildbuddy-flaky-test-fixer --prompt-file /tmp/new-prompt.md
```

Find recent local sessions that mention an automation:

```bash
codex-automaton --json threads list --automation buildbuddy-flaky-test-fixer --limit 10
```

Manage the localhost WebUI:

```bash
codex-automaton server install-systemd --host 127.0.0.1 --port 8767
systemctl --user status codex-automaton-server.service
journalctl --user -u codex-automaton-server.service -f
```

Open the UI at `http://codex-automaton.localhost:8767/` or `http://127.0.0.1:8767/`.

## Safety Rules

- Do not enable an imported automaton timer while the original Codex App automation is still active unless the user explicitly wants both schedulers running.
- Use `automation run --dry-run` before manual runs, especially for prompts that can edit repositories or create PRs.
- Do not run `systemctl --user start codex-automaton@<id>.service` unless the user asked for a live run.
- Prefer updating installed TOML through `codex-automaton automation update` or the WebUI so the timer unit is refreshed consistently.
- Keep secrets out of prompts and command output. `doctor --json` reports only presence/paths, not tokens.

## Useful Files

- Project source: `${CODEX_AUTOMATON_REPO:-$HOME/work/misc/codex-automaton}`
- Installed binary: `~/.local/bin/codex-automaton`
- Server unit:
  `${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/codex-automaton-server.service`
- Automation service template:
  `${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/codex-automaton@.service`
- Installed automations:
  `${XDG_CONFIG_HOME:-$HOME/.config}/codex-automaton/automations`
- Run state: `${XDG_STATE_HOME:-$HOME/.local/state}/codex-automaton`
