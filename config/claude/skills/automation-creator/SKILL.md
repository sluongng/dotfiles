---
name: automation-creator
description: Create, inspect, update, pause, resume, or delete Claude Code automations for reminders, recurring jobs, repo monitors, and thread follow-ups. Use when Claude needs to turn a natural-language task plus a schedule into a scheduled or recurring automation, avoid creating a duplicate automation, or adjust an existing automation's prompt, cadence, status, or workspace.
---

# Automation Creator

## Overview

Use this skill when the user wants a Claude automation created or maintained.
The execution surface is Claude Code's built-in scheduling tools:

- `CronCreate` / `CronList` / `CronDelete` for cron-style jobs and one-shot
  reminders.
- `ScheduleWakeup` for self-paced, in-session follow-ups (the `/loop` dynamic
  mode).

Do not hand-write systemd timers, shell `sleep` loops, or external cron entries
when these tools fit.

## Workflow

1. Classify the request.
   - Use a **follow-up** (`ScheduleWakeup`, or a one-shot `CronCreate` with
     `recurring: false`) for requests attached to the current thread, like
     "remind me later", "check back in 30 minutes", or "continue this tomorrow".
   - Use a **recurring** `CronCreate` (`recurring: true`, the default) for
     detached recurring jobs.
   - If the user asks to view, pause, resume, edit, or delete an automation,
     inspect existing jobs first with `CronList` and update those instead of
     creating a duplicate.

2. Resolve the automation target.
   - List current session jobs with `CronList`. For durable jobs, inspect
     `./.claude/scheduled_tasks.json` (or `${CLAUDE_PROJECT_DIR}/.claude/`).
   - Match by prompt intent, workspace, and cadence when possible.
   - Prefer deleting + recreating the closest existing job over stacking a
     second job with overlapping behavior. (There is no in-place update tool;
     `CronDelete` then `CronCreate` is the update path.)

3. Shape the automation prompt.
   - Describe only the task itself; make it self-sufficient and include the
     expected output format when useful.
   - Do not bake schedule, thread, or workspace details into the prompt text.
   - Do not ask the automation to write files or suppress output unless the
     user explicitly wants that.

4. Choose schedule and execution details.
   - Use a standard 5-field cron expression in the user's local timezone:
     `minute hour day-of-month month day-of-week`. No timezone math needed —
     `0 9 * * *` is 9am local.
   - When the requested time is approximate, avoid the `:00` and `:30` marks so
     fleet-wide jobs don't all fire on the same instant: prefer `57 8 * * *` or
     `3 9 * * *` over `0 9 * * *`, and `7 * * * *` over `0 * * * *`. Use exact
     minutes only when the user clearly means a precise time.
   - For one-shot reminders, set `recurring: false` and pin minute/hour/
     day-of-month/month to the target instant.
   - Default to session-scoped jobs. Set `durable: true` only when the user
     wants the automation to survive across Claude sessions (it persists to
     `.claude/scheduled_tasks.json`).

5. Execute with the tool.
   - `CronCreate` when there is no matching job and the user wants it now.
   - `CronDelete` + `CronCreate` to change a job's prompt, schedule, or scope.
   - `CronDelete` alone to remove a job the user clearly wants gone.
   - `ScheduleWakeup` for self-paced in-session loops where you decide the next
     check-in time.

6. Report back in plain language.
   - Confirm whether the automation was created, updated, paused, resumed, or
     deleted, and summarize cadence, scope, and status.
   - State the relevant lifetime limits: session jobs vanish when Claude exits;
     recurring jobs auto-expire after 7 days (one final fire, then deleted);
     `durable: true` survives restarts.
   - If you updated/recreated an existing job to avoid duplication, say so.

## Prompt Writing Rules

- State the task, the source of truth, and the expected output.
- For reports, specify grouping, ranking, and evidence expectations.
- For monitors, state what condition should trigger action and what the
  follow-up should include. For watching live state (a log, a process, command
  output) prefer the `Monitor` tool over polling on a cron schedule.
- Keep the prompt stable enough that later schedule changes don't require
  rewriting the task intent.

## Decision Hints

- "Remind me in 20 minutes to check CI" -> one-shot `CronCreate` (`recurring:
  false`) or `ScheduleWakeup`.
- "Every weekday at 9 AM, review open PRs in this repo" -> recurring
  `CronCreate` `3 9 * * 1-5`.
- "Pause my daily summary" -> `CronDelete` the matching job; recreate when
  resuming.
- "Make my daily summary survive restarts" -> recreate it with `durable: true`.

## Constraints

- Never spin up a workaround `sleep` loop or external cron entry when a built-in
  schedule fits.
- Never invent job ids; resolve them from `CronList` output.
- Keep automation descriptions short and human-readable.
- If task, schedule, or workspace scope is materially ambiguous, clarify the
  missing piece before creating the automation.
