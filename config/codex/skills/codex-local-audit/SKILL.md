---
name: codex-local-audit
description: "Audit local Codex thread counts, token usage, session evidence, automation recency, and live Desktop or app-server process state."
---

# Codex Local Audit

Use this skill for machine-local Codex audits where exact local state matters:
recent thread counts, token usage, session titles, automation run recency,
tool-failure evidence, or Codex process health.

## Source Priority

1. Use `~/.codex/state_5.sqlite` as the primary source for thread ids, titles,
   cwd, timestamps, and token totals.
2. Use `~/.codex/sessions/**/*.jsonl` for user prompts, assistant summaries,
   tool calls, tool failures, and current-session exclusion.
3. Resolve the automation's actual scheduler before checking definitions or
   run history. On Linux inspect Aton/systemd; inspect Codex App records as a
   separate backend when relevant. Old App records do not prove current ownership.
4. Use live process evidence when asked whether Codex Desktop, app-server,
   remote-control, or automation launchers are running.

Do not infer exact counts from session filenames alone. Report plainly when the
data set is too small to fill a requested top-N list.

## Setup

```bash
AUDIT_CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
DB="$AUDIT_CODEX_HOME/state_5.sqlite"
SESSIONS="$AUDIT_CODEX_HOME/sessions"
APP_AUTOMATIONS="$AUDIT_CODEX_HOME/automations"
```

Use the active thread ID supplied by the runtime when available. Otherwise
identify it from matching session metadata and current task evidence; the newest
filename alone does not prove which thread is active. Leave `current_id` empty
and report that exclusion is unavailable if it cannot be established reliably.

Set `current_id` to that verified ID before using the ranking example.

## Select the evidence needed

Read [references/audit-queries.md](references/audit-queries.md) for thread/token
rankings, session message or tool-failure extraction, and automation/job queries.
Run only the queries relevant to the request. Check the installed database schema
before relying on version-specific fields.

Keep audit operations read-only. Use SQLite's `-readonly` mode and scheduler
inspection commands; do not trigger runs, repair lifecycle files, or change
definitions, timers, or services merely to establish their health.

Distinguish root threads from descendants and inherited transcript context when
reporting counts or token usage. `tokens_used` can include inherited cumulative
usage; do not sum it across related threads as incremental work or billed cost.

For runtime health, inspect the relevant live process tree, user service, and
socket state. Identify Desktop, app-server, remote-control, and automation
launchers separately. A running remote-control or app-server process alone does
not prove Desktop is attached or that scheduled jobs execute successfully; pair
process evidence with recent task or job outcomes. Do not assume macOS process
names or `caffeinate` on Linux.

## Reporting

Include:

- the exact time window and data source used
- counts and recorded token metrics with their accounting limitations
- whether the active audit thread was excluded
- recent automation health signals when relevant
- any gaps, such as no recent automation-created threads or missing session
  files

Keep runtime/auth/history/log/memory/SQLite state local. Do not move it into
dotfiles or shared plugin files.
