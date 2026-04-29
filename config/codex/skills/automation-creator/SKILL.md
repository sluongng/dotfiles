---
name: automation-creator
description: Create, inspect, update, pause, resume, or delete Codex automations for reminders, recurring jobs, repo monitors, and thread follow-ups. Use when Codex needs to turn a natural-language task plus schedule into a heartbeat or cron automation, avoid creating a duplicate automation, or adjust an existing automation's prompt, cadence, status, or workspace.
---

# Automation Creator

## Overview

Use this skill when the user wants a Codex automation created or maintained. The execution surface is the built-in `codex_app.automation_update` tool; do not hand-write raw automation directives.

## Workflow

1. Classify the request.
- Use `heartbeat` for follow-ups attached to the current thread, especially requests like "remind me later", "check back in 30 minutes", or "continue this thread tomorrow".
- Use `cron` for detached recurring jobs tied to one or more workspaces.
- If the user asks to view, pause, resume, edit, or delete an automation, inspect the existing automation first and update it instead of creating a duplicate.

2. Resolve the automation target.
- For existing automations, inspect local `automation.toml` files under `${CODEX_HOME:-$HOME/.codex}/automations`.
- Match by automation name, prompt, workspace, and kind when possible.
- Prefer updating the closest existing automation over creating a second automation with overlapping behavior.

3. Shape the automation prompt.
- Describe only the task itself.
- Make the prompt self-sufficient and include the expected output format when useful.
- Do not include schedule, thread, or workspace details in the prompt.
- Do not ask the automation to write files or to suppress output unless the user explicitly wants that behavior.
- If the task should use automation memory, include the defensive path pattern
  `${CODEX_HOME:-$HOME/.codex}/automations/<automation_id>/memory.md`
  and tell the run to read it first and record the outcome before returning.
  Avoid raw `$CODEX_HOME/automations/...` paths because `CODEX_HOME` may be
  unset in cron runs.

4. Choose schedule and execution details.
- Interpret times in the user's locale.
- For heartbeat automations on the current conversation, use `destination=thread`.
- For cron automations, set `cwds` to the relevant workspace paths and choose `local` or `worktree` only when the request makes that distinction important.
- Default status to `ACTIVE` unless the user asks to start paused.

5. Execute with the tool.
- Use `create` when there is no matching automation and the user wants it created now.
- Use `suggested_create` or `suggested_update` only when the user asks to review before applying.
- Use `update` for prompt, schedule, status, cwd, or model changes, preserving fields the user did not ask to change.
- Use `delete` only when the user clearly asks to remove the automation.

6. Report back in plain language.
- Confirm whether the automation was created, updated, paused, resumed, or deleted.
- Summarize cadence, scope, and status without exposing raw RRULE strings unless the user explicitly asks for them.
- If you updated an existing automation to avoid duplication, say so.

## Existing Automation Discovery

Use a defensive `CODEX_HOME` fallback when reading local automation files:

```bash
AUTOMATION_BASE="${CODEX_HOME:-$HOME/.codex}/automations"
find "$AUTOMATION_BASE" -maxdepth 2 -name automation.toml | sort
```

Read the matched file before calling `update`, `view`, or `delete` so the automation id and current fields are resolved from source.

## Prompt Writing Rules

- State the task, the source of truth, and the expected output.
- For reports, specify grouping, ranking, and evidence expectations.
- For monitors, state what condition should trigger action and what the follow-up should include.
- For memory-backed recurring jobs, spell out the fallback memory path with
  `${CODEX_HOME:-$HOME/.codex}` and the stable automation id.
- Keep the prompt stable enough that later schedule changes do not require rewriting the task intent.

## Decision Hints

- "Remind me in 20 minutes to check CI" -> `heartbeat`
- "Every weekday at 9 AM, review open PRs in this repo" -> `cron`
- "Pause my daily summary" -> update the existing automation status
- "Delete the reminder about the invoice follow-up" -> resolve the matching automation id, then delete it

## Constraints

- Never create a workaround cron automation when a same-thread heartbeat fits.
- Never invent automation ids; resolve them from local files or tool output.
- Never assume `CODEX_HOME` is set when reading local automations.
- Keep automation names short and human-readable.
- If task, schedule, or workspace scope is materially ambiguous, clarify the missing piece before creating the automation.
