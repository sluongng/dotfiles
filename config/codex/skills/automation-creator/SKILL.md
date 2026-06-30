---
name: automation-creator
description: Create, inspect, update, pause, resume, delete, migrate, or troubleshoot Codex automations across backends. Use when Codex needs to manage reminders, recurring jobs, repo monitors, thread follow-ups, local codex-automaton/Aton jobs, systemd user timers, Codex App automations, automation TOML, automation threads, journals, or the localhost Automaton WebUI. On Linux, default to the local codex-automaton Aton/systemd backend; on macOS, default to the Codex App automation backend.
---

# Automation Creator

## Overview

Use this skill when the user wants a Codex automation created, inspected, updated, paused, resumed, deleted, migrated, or debugged. Choose the backend first, then follow the matching workflow.

Backend selection:

- Use local Aton/systemd on Linux unless the user explicitly asks for Codex App.
- Use Codex App on macOS unless the user explicitly asks for local Aton and the tooling exists.
- Honor an explicit backend request when it is available.
- If the selected backend tool is unavailable, report that clearly and do not fake state.

## Core Workflow

1. Classify the request as create, inspect, update, pause, resume, delete, run, troubleshoot, migrate, thread lookup, or WebUI management.
2. Resolve the backend from OS, user wording, and available tools.
3. Inspect existing automations first. Match by id, name, prompt, workspace, schedule, and kind so you update the closest existing automation instead of creating duplicates.
4. Shape prompts so they describe the task itself, source of truth, guardrails, and expected output. Keep schedule, backend, and workspace metadata outside the prompt unless the future run needs that context to act safely.
5. Validate before enabling or running. Use dry-run paths when available.
6. Report the backend, automation id, cadence, scope, status, validation, and any follow-up needed.

## Linux: Aton/Systemd Backend

Use the installed `codex-automaton` CLI. It stores installed automation TOML under `${XDG_CONFIG_HOME:-$HOME/.config}/codex-automaton`, run state under `${XDG_STATE_HOME:-$HOME/.local/state}/codex-automaton`, and schedules through `systemd --user`.

Start every Linux workflow with:

```bash
command -v codex-automaton
codex-automaton --json doctor
codex-automaton --json automation list
```

Prefer `--json` for analysis and scripting. Use human output only for quick inspection.

Common Linux actions:

```bash
codex-automaton --json automation get <id>
codex-automaton --json automation run --id <id> --dry-run
codex-automaton automation update <id> --on-calendar '*-*-* 09:00:00'
codex-automaton automation update <id> --model gpt-5.5 --reasoning-effort xhigh --speed fast
codex-automaton automation update <id> --prompt-file /tmp/new-prompt.md
codex-automaton --json threads list --automation <id> --limit 10
```

On Linux, run packaged `codex` directly for Aton jobs; do not shadow it with a wrapper or require custom Codex CLI flags. Aton categorizes completed automation sessions by updating local rollout metadata and the Codex thread index, so new Aton-created threads should appear in plain `codex resume`; use `codex resume --all --include-non-interactive <session_id>` only for legacy automation threads that were created before this categorization existed.

For new local automations, create or update a TOML file, validate it, then install:

```bash
systemd-analyze calendar '<calendar expression>'
codex-automaton --json automation install path/to/automation.toml --dry-run
codex-automaton --json automation install path/to/automation.toml
systemctl --user status 'codex-automaton@<id>.timer' --no-pager
systemctl --user list-timers 'codex-automaton@*.timer' --all --no-pager
```

Use `--no-enable` when importing or staging an automation that must not start yet.

Troubleshoot Linux automations with:

```bash
systemctl --user status 'codex-automaton@<id>.service' --no-pager --full
systemctl --user show 'codex-automaton@<id>.service' -p ActiveState -p SubState -p Result -p ExecMainStatus
journalctl --user -u 'codex-automaton@<id>.service' -n 240 --no-pager
systemctl --user list-timers 'codex-automaton@*.timer' --all --no-pager
systemctl --user --failed --no-pager --plain
```

For worktree-backed jobs, verify the branch guard before resetting failures:

```bash
git -C "${XDG_STATE_HOME:-$HOME/.local/state}/codex-automaton/<id>/worktree" status --short --branch
codex-automaton --json automation run --id <id> --dry-run
systemctl --user reset-failed 'codex-automaton@<id>.service'
```

Manage the local WebUI with:

```bash
codex-automaton server install-systemd --host 127.0.0.1 --port 8767
systemctl --user status codex-automaton-server.service --no-pager
journalctl --user -u codex-automaton-server.service -f
```

Open `http://codex-automaton.localhost:8767/` or `http://127.0.0.1:8767/`.

## macOS: Codex App Backend

Use the built-in `codex_app.automation_update` tool when it is available. Do not hand-write raw automation directives for the Codex App backend.

Classify app automations:

- Use `heartbeat` for follow-ups attached to the current thread, especially reminders like "check back in 30 minutes" or "continue this thread tomorrow".
- Use `cron` for detached recurring jobs tied to one or more workspaces.
- For heartbeat automations on the current conversation, use `destination=thread`.
- For cron automations, set `cwds` to the relevant workspace paths and choose `local` or `worktree` only when that distinction matters.

Resolve existing app automations defensively:

```bash
AUTOMATION_BASE="${CODEX_HOME:-$HOME/.codex}/automations"
find "$AUTOMATION_BASE" -maxdepth 2 -name automation.toml | sort
```

Read the matched file before app `update`, `view`, or `delete` so the automation id and current fields are resolved from source. Use `create` only when no matching automation exists. Use `suggested_create` or `suggested_update` only when the user asks to review before applying.

For memory-backed app jobs, include the defensive path pattern `${CODEX_HOME:-$HOME/.codex}/automations/<automation_id>/memory.md` in the prompt and tell the run to read it first and record the outcome before returning.

## Prompt Writing Rules

- State the task, the source of truth, and the expected output.
- For reports, specify grouping, ranking, and evidence expectations.
- For monitors, state what condition should trigger action and what the follow-up should include.
- Do not ask an automation to suppress output unless the user explicitly wants that behavior.
- Do not put secrets, raw private payloads, or credentials in prompts.
- For memory-backed recurring jobs, spell out the backend's fallback memory path and stable automation id.
- Keep the prompt stable enough that later schedule changes do not require rewriting the task intent.

## Safety Rules

- Do not enable an imported local Aton timer while the original Codex App automation is still active unless the user explicitly wants both schedulers running.
- Use dry-run validation before manual local runs, especially for prompts that can edit repositories, create PRs, or call external write APIs.
- Do not run `systemctl --user start codex-automaton@<id>.service` unless the user asked for a live run.
- Prefer `codex-automaton automation update`, `automation install`, or the WebUI over direct installed TOML edits so systemd timers stay refreshed.
- Preserve unrelated dirty worktree files. If a local automation worktree has tracked changes at the start of a task, stop before a live run unless the user explicitly tells you to continue.
- Default new automations to active unless the user asks to start paused, but stage imports with `--no-enable` when duplicate scheduling is possible.
- Delete automations only when the user clearly asks to remove them.

## Useful Paths

- Local project source: `${CODEX_AUTOMATON_REPO:-$HOME/work/misc/codex-automaton}`
- Local installed binary: `~/.local/bin/codex-automaton`
- Local server unit: `${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/codex-automaton-server.service`
- Local service template: `${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/codex-automaton@.service`
- Local installed automations: `${XDG_CONFIG_HOME:-$HOME/.config}/codex-automaton/automations`
- Local run state: `${XDG_STATE_HOME:-$HOME/.local/state}/codex-automaton`
- Codex App automations: `${CODEX_HOME:-$HOME/.codex}/automations`
