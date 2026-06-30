---
name: timed-self-wake
description: Create, inspect, or cancel one-time Codex wake-up automations backed by systemd user timers, especially when Codex must re-evaluate time-sensitive state in the future, preserve prior context or approvals, resume a known thread, or install a guarded future action through local codex-automaton.
---

# Timed Self Wake

Use this skill when a task should pause until a future clock time, market open,
deadline, release window, or scheduled review. Prefer a one-time
codex-automaton timer over a long sleeping shell.

## Safety Boundary

- Treat inherited conversation as context, not permission to execute future
  writes. Put exact user approvals and guardrails in the automation prompt.
- Cancel any existing sleeping shell, old timer, or duplicate automation before
  installing a new one for the same action.
- For broker, calendar, GitHub, production, or file mutations, include explicit
  skip conditions and post-write verification in the future prompt.
- Use Persistent=false for clock-sensitive one-shot actions unless the user
  explicitly wants catch-up execution after the machine was asleep or offline.
- Never put secrets or raw private payloads in the prompt. Store private outputs
  under the task repo's private/raw data path.

## Workflow

1. Read $automation-creator if available. Use its Linux Aton/systemd backend
   with the installed codex-automaton CLI and systemd user timers; do not
   hand-roll unit files unless the CLI is unavailable.
2. Confirm local time and timezone with date -Is, plus the target market or
   event timezone when relevant.
3. Inspect existing state with codex-automaton --json doctor,
   codex-automaton --json automation list, and systemctl --user list-timers
   'codex-automaton@*.timer' --all.
4. Decide whether the wake-up should start a new automation run or resume a
   specific thread:
   - Use a normal codex-automaton prompt for most future actions. Distill the
     necessary context into the prompt so the future run is self-contained.
   - Use a thread id only when the user specifically wants the same thread
     reopened. See references/thread-resume.md.
5. Write a one-time automation TOML. Prefer scripts/render_one_time_automation.py
   with --id, --name, --cwd, --on-calendar, --prompt-file, and --out.
6. Validate before enabling with systemd-analyze calendar, codex-automaton
   automation install --dry-run, and codex-automaton automation render.
7. Install and verify with codex-automaton automation install, then systemctl
   --user status codex-automaton@<id>.timer --no-pager and systemctl --user
   list-timers 'codex-automaton@<id>.timer' --all --no-pager.
8. Return the timer id, exact trigger time in local and event timezones, TOML
   path, and the future action guardrails.

## Prompt Checklist

Every future prompt should include:

- The user's exact active instruction or approval, if any.
- Absolute date/time and timezone, plus a late-window skip rule.
- The working directory and relevant private output directory.
- Fresh-state reads required before any action.
- Duplicate-action checks.
- Guardrails for execute vs skip.
- Exact command shape for any approved write, including confirmation token when
  applicable.
- Verification after any write; write response alone is not proof.
- Concise final report requirements.

## Useful Commands

- PATH="$HOME/.local/bin:$PATH"
- codex-automaton --json doctor
- codex-automaton --json automation list
- codex-automaton --json automation install path/to/automation.toml --dry-run
- codex-automaton --json automation install path/to/automation.toml
- systemctl --user list-timers 'codex-automaton@<id>.timer' --all --no-pager
- systemctl --user disable --now 'codex-automaton@<id>.timer'
- systemctl --user reset-failed 'codex-automaton@<id>.service'
