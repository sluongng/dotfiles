---
name: timed-self-wake
description: Schedule, inspect, or cancel one-time future wake-ups for Claude, especially when Claude must re-evaluate time-sensitive state in the future, preserve prior context or approvals, or install a guarded future action. Use for "check back at 4pm", "wake up at market open", or pausing a task until a deadline or release window instead of holding a long sleeping shell.
---

# Timed Self Wake

Use this skill when a task should pause until a future clock time, market open,
deadline, release window, or scheduled review. Prefer a built-in one-time
schedule over a long sleeping shell.

Two mechanisms, pick by horizon:

- `ScheduleWakeup` — self-paced, within the current session. Best when you are
  actively looping on something and want to wake yourself after a chosen delay
  (e.g. polling CI). Picks a delay in seconds; the session stays alive.
- `CronCreate` with `recurring: false` — a one-shot fire pinned to a wall-clock
  instant. Best for "at 4pm do X". Add `durable: true` when the wake-up must
  survive Claude restarting before it fires.

## Safety Boundary

- Treat inherited conversation as context, not permission to execute future
  writes. Put exact user approvals and guardrails in the wake-up prompt itself.
- Cancel any existing sleeping shell, stale `ScheduleWakeup`, or duplicate cron
  job (`CronList` -> `CronDelete`) before installing a new one for the same
  action.
- For broker, calendar, GitHub, production, or file mutations, include explicit
  skip conditions and post-write verification in the future prompt.
- Never put secrets or raw private payloads in the prompt. Store private outputs
  under the task repo's private/raw data path and have the future run read them.

## Workflow

1. Confirm local time and timezone with `date -Is`, plus the target market or
   event timezone when relevant. Cron expressions are interpreted in local time.
2. Inspect existing schedules with `CronList` so you don't stack duplicates.
3. Decide the mechanism:
   - In-session loop you are actively driving -> `ScheduleWakeup` with a delay
     matched to how fast the watched state changes. Keep delays under ~270s to
     stay in cache when polling; jump to 1200s+ for genuinely idle waits.
   - Detached one-shot at a specific clock time -> `CronCreate`
     (`recurring: false`) with minute/hour/day-of-month/month pinned to the
     target instant. Avoid the `:00`/`:30` marks unless the user means an exact
     time.
4. Write a self-contained wake-up prompt (see checklist). Distill the necessary
   context into it so the future run does not depend on this conversation.
5. Create the schedule, then read back `CronList` to confirm the trigger.
6. Report the job id (if cron), the exact trigger time in local and event
   timezones, and the future-action guardrails.

## Prompt Checklist

Every future prompt should include:

- The user's exact active instruction or approval, if any.
- Absolute date/time and timezone, plus a late-window skip rule.
- The working directory and relevant private output directory.
- Fresh-state reads required before any action.
- Duplicate-action checks.
- Guardrails for execute vs skip.
- Exact command shape for any approved write, including a confirmation token
  when applicable.
- Verification after any write; a write response alone is not proof.
- Concise final-report requirements.

## Useful Calls

- `date -Is` — current local time and offset.
- `CronList` — see scheduled jobs and their ids.
- `CronCreate` `{cron: "30 16 14 6 *", recurring: false, prompt: "..."}` — fire
  once at 4:30pm on Jun 14 local.
- `CronCreate` with `durable: true` — survive a Claude restart before firing.
- `CronDelete` `{id}` — cancel a scheduled job.
- `ScheduleWakeup` `{delaySeconds, reason, prompt}` — self-paced in-session wake.
