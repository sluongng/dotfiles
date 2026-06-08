---
name: automation-runner
description: Execute recurring Codex automations, reminders, monitors, and scheduled follow-up runs when a prompt includes an Automation ID, Automation memory path, Last run timestamp, or asks Codex to run an automation. Use before task-specific skills to read and update automation memory safely, avoid raw CODEX_HOME path misses, and return the required inbox item.
---

# Automation Runner

Use this skill when you are executing an automation run. For creating,
editing, pausing, or deleting automation definitions, use `automation-creator`
instead.

## Startup

Resolve automation memory defensively before task-specific work. This should be
the first shell command that touches automation memory:

```bash
AUTOMATION_ID="<automation_id>"
AUTOMATION_BASE="${CODEX_HOME:-$HOME/.codex}/automations"
MEMORY_PATH="$AUTOMATION_BASE/$AUTOMATION_ID/memory.md"
mkdir -p "$(dirname "$MEMORY_PATH")"
if [ -f "$MEMORY_PATH" ]; then
  sed -n '1,240p' "$MEMORY_PATH"
fi
```

Do not run a preliminary probe like
`if [ -f "$CODEX_HOME/automations/<id>/memory.md" ]`; it is still a raw
`$CODEX_HOME` lookup even when followed by a fallback. If `CODEX_HOME` is unset,
that expands to `/automations/...` and silently skips the real memory file.
Construct `MEMORY_PATH` with `${CODEX_HOME:-$HOME/.codex}` first, then only read
or write through `"$MEMORY_PATH"`.

## Running The Task

- Apply the task-specific skill after startup when one matches the automation
  body.
- Exclude the current automation's in-progress session files from evidence.
- Treat expected non-zero exits used as existence checks separately from real
  failures.
- Keep the automation's normal output contract, but avoid inventing work when
  the scan is a no-op.

## Finish

Before returning, append a concise run record to `$MEMORY_PATH` with:

- current run time
- what was scanned or changed
- whether the run was a no-op
- validation or install commands, if files changed

End the final response with exactly one `::inbox-item{...}` directive, using a
short title and a concrete next-step summary.
