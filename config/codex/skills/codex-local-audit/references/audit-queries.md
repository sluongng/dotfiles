# Local Audit Query Examples

Use the path variables from SKILL.md and adapt the time window to the request.
Check the live SQLite schema before relying on version-specific table columns.

## Thread And Token Queries

Recent threads in a time window:

```bash
sqlite3 -readonly -header -column "$DB" "
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
sqlite3 -readonly -header -column "$DB" "
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

On Linux, inspect Aton definitions and actual systemd timer state:

```bash
codex-automaton --json doctor
codex-automaton --json automation list
systemctl --user list-timers 'codex-automaton@*.timer' --all --no-pager
```

Use the effective roots reported by `doctor`, including any supplied
`--config-home`, `--state-home`, or `--systemd-user-dir` overrides. Defaults are
`${CODEX_AUTOMATON_CONFIG_HOME:-${XDG_CONFIG_HOME:-$HOME/.config}/codex-automaton}`
for configuration and
`${CODEX_AUTOMATON_STATE_HOME:-${XDG_STATE_HOME:-$HOME/.local/state}/codex-automaton}`
for state. Keep the same overrides on subsequent CLI inspection commands.

For a selected job, read its installed definition with
`codex-automaton --json automation get <id>`, inspect
`systemctl --user status 'codex-automaton@<id>.timer' --no-pager`, and correlate
the relevant service journal with `<state-root>/<id>/attempts.jsonl`,
`last-run.json`, and `last-message.md` when present. Report timer enablement,
the next trigger, and recent run outcome separately. An intentionally paused
timer may return nonzero status. Do not edit lifecycle records or run the job.

Inspect App definitions separately when auditing that backend or comparing old
and current scheduler ownership:

```bash
find "$APP_AUTOMATIONS" -maxdepth 2 -name automation.toml | sort
```

A missing App directory or old paused records do not imply Aton jobs are absent
or unhealthy. If the Aton CLI is unavailable, inspect the relevant existing
files and user units and report that limitation without installing anything.

Find recent automation-like threads:

```bash
sqlite3 -readonly -header -column "$DB" "
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

Inspect recent Codex internal job errors when relevant. This table is not
Aton's run ledger and does not establish Aton workload health:

```bash
sqlite3 -readonly -header -column "$DB" "
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
