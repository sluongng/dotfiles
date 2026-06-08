---
name: codex-local-audit
description: Audit local Codex thread, session, token, and automation state on this machine. Use when Codex needs exact recent thread counts, token rankings, session titles, local automation recency, or Codex Desktop versus remote-control process evidence from ~/.codex.
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
3. Use `${CODEX_HOME:-$HOME/.codex}/automations` for automation definitions and
   memory recency.
4. Use live process evidence when asked whether Codex Desktop, app-server,
   remote-control, or automation launchers are running.

Do not infer exact counts from session filenames alone. Report plainly when the
data set is too small to fill a requested top-N list.

## Setup

```bash
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
DB="$CODEX_HOME/state_5.sqlite"
SESSIONS="$CODEX_HOME/sessions"
AUTOMATIONS="$CODEX_HOME/automations"
```

If excluding the active audit thread matters, identify the likely current
session from recent JSONL files and read its `session_meta` id:

```bash
current_session="$(find "$SESSIONS" -type f -mtime -1 | sort | tail -n 1)"
current_id=""
if [ -n "$current_session" ]; then
  current_id="$(
    jq -r 'select(.type=="session_meta") | .payload.id // empty' \
      "$current_session" 2>/dev/null | head -n 1
  )"
fi
```

## Thread And Token Queries

Recent threads in a time window:

```bash
sqlite3 -header -column "$DB" "
select id,
       datetime(updated_at, 'unixepoch', 'localtime') as updated,
       tokens_used,
       cwd,
       title
from threads
where updated_at >= strftime('%s','now','-14 days')
order by updated_at;
"
```

Top token consumers:

```bash
sqlite3 -header -column "$DB" "
select id,
       datetime(updated_at, 'unixepoch', 'localtime') as updated,
       tokens_used,
       cwd,
       title
from threads
where updated_at >= strftime('%s','now','-14 days')
  and ('$current_id' = '' or id != '$current_id')
order by tokens_used desc
limit 5;
"
```

If the active audit thread is included and dominates the result, say so and
also provide the ranking with it excluded.

## Session Evidence

Inventory recent session files:

```bash
find "$SESSIONS" -type f -mtime -14 | sort
```

Extract user-facing message summaries:

```bash
jq -r '
  select(.type=="response_item" and .payload.type=="message") |
  [.payload.role,
   ((.payload.content // [])
    | map(.text? // .input_text? // .output_text? // empty)
    | join(" ")
    | gsub("\n"; " ")
    | .[0:300])]
  | @tsv
' $(find "$SESSIONS" -type f -mtime -14 | sort)
```

Extract concrete tool failures:

```bash
jq -r '
  select(.type=="response_item" and .payload.type=="function_call_output") |
  select((.payload.output // "") |
    test("Process exited with code [1-9]|No such file|not found|failed|error|unsupported|ModuleNotFound|Permission denied|timeout|timed out"; "i")) |
  (.payload.output
    | split("\n")
    | map(select(test("Process exited with code [1-9]|No such file|not found|failed|error|unsupported|ModuleNotFound|Permission denied|timeout|timed out"; "i")))
    | .[0:8]
    | join("\n")) + "\n---"
' $(find "$SESSIONS" -type f -mtime -14 | sort)
```

Treat expected non-zero exits used for existence checks separately from real
failures.

## Automation Recency And Health

List configured automations:

```bash
find "$AUTOMATIONS" -maxdepth 2 -name automation.toml | sort
```

Find recent automation-like threads:

```bash
sqlite3 -header -column "$DB" "
select datetime(updated_at,'unixepoch','localtime') as updated,
       tokens_used,
       cwd,
       title
from threads
where title like '%PR Coach%'
   or title like '%Weekly%'
   or title like '%Dependency%'
   or title like '%AGENTS%'
   or title like '%skills%'
   or title like '%Buck2%'
   or title like '%automation%'
order by updated_at desc
limit 40;
"
```

Inspect recent job errors when automation or memory health is in question:

```bash
sqlite3 -header -column "$DB" "
select kind,
       job_key,
       status,
       datetime(started_at,'unixepoch','localtime') as started,
       datetime(finished_at,'unixepoch','localtime') as finished,
       retry_remaining,
       last_error
from jobs
order by rowid desc
limit 20;
"
```

For live process checks:

```bash
ps aux | rg -i 'Codex|codex' | rg -v 'rg -i|exec_command|zsh -lc'
```

On this machine, `codex remote-control` plus `caffeinate` proves remote-control
is alive. It does not prove Codex Desktop automations are healthy. For Desktop
automation health, look for the installed `Codex.app` process and its
`codex app-server` companion, then pair process evidence with recent automation
threads or job errors.

## Reporting

Include:

- the exact time window and data source used
- exact counts and token totals
- whether the active audit thread was excluded
- recent automation health signals when relevant
- any gaps, such as no recent automation-created threads or missing session
  files

Keep runtime/auth/history/log/memory/SQLite state local. Do not move it into
dotfiles or shared plugin files.
