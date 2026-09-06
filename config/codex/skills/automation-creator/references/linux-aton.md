# Linux Aton Backend

Use the installed `codex-automaton` CLI (`aton` is its primary binary name).
Check `--help` when a requested operation differs from these examples; there is
no `automation create` subcommand. Create a TOML definition and install it.

## Resolve current paths and identity

```bash
codex-automaton --json doctor
codex-automaton --json automation list
codex-automaton --json automation get <id>
systemctl --user list-timers 'codex-automaton@*.timer' --all --no-pager
```

`doctor` reports the effective paths. CLI `--config-home`, `--state-home`, and
`--systemd-user-dir` override environment/default roots; keep the same roots
for inspection, preview, and mutation. Defaults are:

- Definitions: `${CODEX_AUTOMATON_CONFIG_HOME:-${XDG_CONFIG_HOME:-$HOME/.config}/codex-automaton}/automations/<id>.toml`
- State: `${CODEX_AUTOMATON_STATE_HOME:-${XDG_STATE_HOME:-$HOME/.local/state}/codex-automaton}/<id>/`
- Units: `${CODEX_AUTOMATON_SYSTEMD_USER_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user}/`

Use `<state>/<id>/memory.md` for concise run memory. Aton writes `last-message.md`
when `output.last_message=true`; `last-run.json` and `attempts.jsonl` are runtime
records. Inspect their timestamps and outcomes when diagnosing run health.
Do not infer workload success from `doctor.ok`, a running daemon, or an old final
message. Do not edit Aton's lifecycle records to bypass a blocked run.

## Definition shape

Choose the actual name, cwd, timezone, prompt, and permissions for the job. The
following is a paused example; it is not a mandate to create this workload:

```toml
version = 1
id = "daily-repo-report"
name = "Daily repository report"
cwd = "/absolute/repository/path"
on_calendar = "*-*-* 09:00:00 Europe/Amsterdam"
persistent = true
status = "PAUSED"
prompt = """
Inspect the requested repository state and report actionable changes.
This is an Aton run. Read the job's memory.md under the effective Aton state
root first; append the outcome there before returning. Return a concise report.
"""

[codex]
bin = "codex"
# Omit model/effort to inherit the shared config, or pin the user's choice.
# Choose sandbox/approval settings appropriate to this job's authorized work.

[worktree]
enabled = false

[output]
last_message = true
json = false
```

For an isolated coding job, set `[worktree].enabled=true` and explicitly set
`branch="sluongng/automation/<id>"`; Aton's built-in `aton/<id>` default does
not match the user's branch convention. Use `$prepare-worktree` for required
local context. Use the main checkout for a read-only report when appropriate.

For clock-sensitive one-shot work, use `$timed-self-wake`: absolute date/time,
`one_shot=true`, and normally `persistent=false`. For recurring work, decide
whether catch-up after sleep/offline is wanted rather than copying a default.

## Preview and apply

```bash
systemd-analyze calendar '<OnCalendar expression>'
codex-automaton --json automation render /absolute/path/job.toml
codex-automaton --json automation install /absolute/path/job.toml --dry-run
codex-automaton --json automation install /absolute/path/job.toml
```

`ACTIVE` is enabled by install; `PAUSED` and `DISABLED` remain disabled. Use
`--no-enable` only when intentionally staging installation, and verify actual
timer state separately. Keep private task definitions outside shared repos.

Update the existing job through the CLI so generation/lifecycle safeguards and
timer state remain synchronized:

```bash
codex-automaton --json automation update <id> --on-calendar '<expression>' --dry-run
codex-automaton --json automation update <id> --on-calendar '<expression>'
codex-automaton --json automation update <id> --prompt-file /absolute/path/prompt.txt
codex-automaton --json automation update <id> --status PAUSED
codex-automaton --json automation update <id> --status ACTIVE
```

After changing a schedule or status:

```bash
codex-automaton --json automation get <id>
systemctl --user status 'codex-automaton@<id>.timer' --no-pager
systemctl --user list-timers 'codex-automaton@<id>.timer' --all --no-pager
```

Inactive timer status can return nonzero for an intentionally paused job; check
its state rather than treating that as a workload failure. For an explicitly
requested immediate run, first preview `automation run --id <id> --dry-run`,
then use `automation run --id <id>` within the job's actual authorization.
Scheduling alone does not request that immediate run.

The CLI has no delete subcommand. If deletion is explicitly requested, pause
the exact job first and verify it has no active attempt. Remove only its
installed definition and instance timer, then reload user units. Preserve run
history and any linked worktree unless deletion of those is also requested;
never remove the shared `codex-automaton@.service` template for a single job.
