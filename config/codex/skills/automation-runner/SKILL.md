---
name: automation-runner
description: Run an existing Codex automation or scheduled monitor, using its actual scheduler's memory and output contract. Use when the prompt identifies an automation run.
---

# Automation Runner

Use this skill for an already-triggered run. For creating, updating, pausing,
or resuming a schedule, use `$automation-creator`. Linux scheduling is owned by
Aton/systemd; do not create an App task or another timer merely to run the task.

## Resolve the run's backend and memory

An `Aton automation ID:` prompt comes from `codex-automaton`. Use its actual
state root, not the Codex App automation directory. A supplied state-root CLI
override or explicit job-memory path takes precedence over defaults; generated
Aton services export `CODEX_AUTOMATON_STATE_HOME` for the effective root.

For an Aton run with its resolved ID:

```bash
AUTOMATION_ID="<automation_id>"
AUTOMATION_STATE_ROOT="${CODEX_AUTOMATON_STATE_HOME:-${XDG_STATE_HOME:-$HOME/.local/state}/codex-automaton}"
MEMORY_PATH="$AUTOMATION_STATE_ROOT/$AUTOMATION_ID/memory.md"
```

For a confirmed Codex App run, use its supplied memory path, or:

```bash
AUTOMATION_ID="<automation_id>"
APP_AUTOMATION_ROOT="${CODEX_HOME:-$HOME/.codex}/automations"
MEMORY_PATH="$APP_AUTOMATION_ROOT/$AUTOMATION_ID/memory.md"
```

Do not infer the backend from the words “Automation ID” alone when records
conflict. Check the run prompt, effective environment, and installed job via
`codex-automaton --json automation get <id>` or the App runtime. The mere
presence of old App records on Linux does not make them the current owner.
Never probe raw `$CODEX_HOME/automations/...` before resolving its fallback.

Read existing memory before task-specific work; create its directory only when
recording a run outcome is part of the job:

```bash
if [ -f "$MEMORY_PATH" ]; then
  sed -n '1,240p' "$MEMORY_PATH"
fi
```

## Execute the requested task

- Apply the relevant task skill without expanding the automation's authority.
- Exclude this in-progress run from historical evidence and counts.
- Keep prior memory as context, not proof of current external state. Refresh
  facts needed for the next action, not an unrelated full inventory.
- Respect the job's existing write boundaries, duplicate checks, and stopping
  conditions. Report an expected no-op or precondition block without inventing
  work or starting another scheduler.
- Do not manually write Aton's `last-run.json`, `attempts.jsonl`, terminal locks,
  or lifecycle records. The runner owns those; their state is not a bypassable
  task precondition.

## Finish using the actual output contract

When the job uses run memory, append a concise record through `$MEMORY_PATH`:
current time, result or no-op reason, changes made, relevant validation, and the
next actionable check. Keep secrets and raw private payloads out of it.

For Aton, return the requested plain report. With `output.last_message=true`,
Aton captures it in `<state-root>/<id>/last-message.md` and records terminal
status separately. Emit `ATON_SEMANTIC_OUTCOME=...` only when the job explicitly
requires that structured contract; do not invent broker/job fields. An App
`::inbox-item{...}` directive is not required for Aton.

For an App run, follow the App runtime's required inbox/notification contract,
including exactly one inbox-item directive when requested there. A saved final
message proves what the agent reported, not that an external write succeeded;
state any actual verification or remaining limitation.
