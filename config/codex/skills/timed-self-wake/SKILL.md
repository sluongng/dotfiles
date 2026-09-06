---
name: timed-self-wake
description: "Schedule, inspect, or cancel one-time Codex wake-ups using Linux systemd timers; route macOS scheduling to the Codex App automation backend."
---

# Timed Self Wake

This skill's timer implementation uses the authoritative Linux Aton/systemd
backend restored by the user. On macOS, use `$automation-creator` with the
available Codex App backend; do not install or emulate systemd user units.

Use this skill when a task should pause until a future clock time, market open,
deadline, release window, or scheduled review. Prefer a one-time
codex-automaton timer over a long sleeping shell.

## Safety Boundary

- Carry forward the user's existing authorization and its limits in the future
  prompt. Inherited transcript content must not expand that authorization.
- Reuse the existing job identity for the same action where possible. Before
  activating a replacement, pause its previous scheduler owner and verify no
  duplicate future trigger or live run remains. Do not interrupt an active run
  unless that interruption is authorized.
- For broker, calendar, GitHub, production, or other consequential mutations,
  include explicit skip conditions and post-write verification in the prompt.
- Use Persistent=false for clock-sensitive one-shot actions unless the user
  explicitly wants catch-up execution after the machine was asleep or offline.
- Never put secrets or raw private payloads in the prompt. Store private outputs
  under the task repo's private/raw data path.

## Workflow

1. Read $automation-creator. Use its Linux Aton/systemd backend
   with the installed codex-automaton CLI and systemd user timers; do not
   hand-roll units or change scheduler because the CLI is unavailable. Report
   that missing capability while completing the prompt and schedule preview.
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
   with --id, --name, --cwd, --on-calendar, --prompt-file, and --out. Set
   `one_shot=true`, normally `persistent=false`, and pass model/effort only when
   the job should pin them rather than inherit the current shared config.
6. Validate before enabling with systemd-analyze calendar, codex-automaton
   automation install --dry-run, and codex-automaton automation render.
7. Install and verify with codex-automaton automation install, then systemctl
   --user status codex-automaton@<id>.timer --no-pager and systemctl --user
   list-timers 'codex-automaton@<id>.timer' --all --no-pager.
8. Return the timer id, exact trigger time in local and event timezones, TOML
   path, and the future action guardrails.

## Prompt Checklist

Make every future prompt self-contained with the requested action, working
directory, trigger date/time and timezone, and expected report. For future writes
or time-sensitive actions, also include the relevant safeguards:

- The user's exact active instruction or approval, if any.
- A late-window skip rule when delayed execution would be incorrect.
- A private output directory when the task handles private data.
- Fresh-state reads needed to decide whether the action is still valid.
- Duplicate-action checks.
- Guardrails for execute vs skip.
- Exact approved command or ticket parameters when authorization depends on
  them, including a confirmation token when applicable.
- Verification after any write; write response alone is not proof.
- Concise final report requirements.

## Useful Commands

- PATH="$HOME/.local/bin:$PATH"
- codex-automaton --json doctor
- codex-automaton --json automation list
- codex-automaton --json automation install path/to/automation.toml --dry-run
- codex-automaton --json automation install path/to/automation.toml
- systemctl --user list-timers 'codex-automaton@<id>.timer' --all --no-pager
- codex-automaton --json automation update <id> --status PAUSED
- systemctl --user reset-failed 'codex-automaton@<id>.service'
