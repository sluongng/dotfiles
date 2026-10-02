# Autonomous Codex chat retrospective

Aton and the systemd user timer `codex-automaton@codex-improve.timer` run this
retrospective daily at **09:00 Europe/Amsterdam**, using **GPT-6.1 Sol/high**.
The job may autonomously improve AGENTS.md and skills. It does not stop at
proposals and has no per-file approval list. External account, publishing,
transaction, service-activation, and memory boundaries remain unchanged.

## Input and completion

`retrospective.py prepare` snapshots **every changed root chat since the previous
completed retrospective**, using the authoritative Codex SQLite index and its
rollout paths. The initial migration uses the last validated legacy retrospective completion;
without host completion history it conservatively defaults to seven days. A
successful model process alone is not proof of a completed retrospective.

Default transcripts contain user/assistant chat messages, including commentary,
with timestamps, cwd, and source record locators. Injected instruction wrappers,
subagent threads, excluded private roots, forks with unverified copied-history
boundaries, and this meta-job are omitted. Forks are skipped entirely, including
their new messages, so inherited private text cannot enter the review. Tool
calls, tool output, and reasoning are not part of the default review. The agent
may inspect specific original records when a concrete uncertainty needs tool
evidence. Plain and compressed rollouts are supported.

There is **no event queue, priority heuristic, sampling quota, or three-candidate
cap**. Large transcripts can be read in chunks, but the run must cover all
captured chats. The two-hour service ceiling bounds execution, not coverage:
failure, partial coverage, or timeout retains the snapshot and leaves the last
completed bookmark unchanged. A retry resumes that same captured window; activity
after its capture belongs to the next window. The completion receipt checks the
exact chat IDs, records changed-file hashes and validation, and only then
advances the bookmark. This verifies reported coverage, not every model reading.

The reviewer actively looks for instruction gaps. An explicit durable user
correction can suffice; inferred lessons need independent supporting tasks.
Already-covered decisions compare exact clauses, not matching topics. It edits
canonical sources, preserves unrelated dirty work, validates the affected assets,
and installs only the relevant managed updates when necessary. Honest no-change
outcomes remain valid, with reasons recorded. Changed-file counts are not proof
of behavioral improvement; subsequent chats provide recurrence evidence.

## State and inspection

Private captured chats, manifests, receipts, and the bookmark live under
`~/.local/state/codex-improve/retrospective/`. Aton keeps execution history under
`~/.local/state/codex-automaton/codex-improve/`. Neither belongs in Git.
`~/.local/state/codex-improve/latest.md` is the readable last completed report.
Desktop notices report applied changes or failures; no-change runs stay quiet.

```sh
codex-improve status
systemctl --user list-timers 'codex-automaton@codex-improve.timer'
journalctl --user -u codex-automaton@codex-improve.service
```

The old `codex-observe.timer` is disabled on installation. Its event files,
bookmarks, candidates, and review history are preserved for inspection, but do
not feed the new run or define a backlog. The legacy `pipeline.py` and scratch
check unit remain available for old candidate receipts.

## Install and validate

Requires Python 3.14+, Git, an installed Aton executable, and the validation
commands required by any skills actually edited. Installation refuses to run
while either the old collector or retrospective service is executing, backs up
changed destinations, and does not restart the shared Codex daemon.

```sh
python3 -m unittest discover -s automation/codex/improve -p 'test_*.py'
python3 automation/codex/improve/install.py --enable
```

Installation enables this timer only and disables the legacy collector timer.
`Persistent=false` prevents a schedule change or wake-up from triggering a missed
09:00 run immediately. The next scheduled run still covers the entire elapsed
chat window. Installation does not start an immediate model run or restore unrelated automations.
An explicitly requested immediate run uses:

```sh
systemctl --user start codex-automaton@codex-improve.service
```

To pause future runs, disable the timer; a currently executing run is unaffected:

```sh
systemctl --user disable --now codex-automaton@codex-improve.timer
```

Private exclusions may be added using `install.py --exclude-root THREAD_ID`.
Existing exclusions are preserved. Do not put private chat identities in Git.
