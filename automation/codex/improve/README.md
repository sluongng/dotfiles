# Incremental Codex improvement

This Linux workflow uses systemd user timers and Aton. It does not require the
ChatGPT App. Deterministic collection precedes a bounded weekly model review;
candidate patches are validated in scratch files and never applied to live
instructions automatically.

## Jobs

| Unit | Schedule | Work |
| --- | --- | --- |
| `codex-observe.timer` | Daily 06:45 Europe/Amsterdam, up to two minutes jitter | New local evidence and configuration health; no model |
| `codex-automaton@codex-improve.timer` | Sunday 09:00 Europe/Amsterdam | Astra/high review when evidence is pending; 20-minute deadline |
| `codex-improvement-check@<candidate>.service` | On demand | Scratch application and allowlisted syntax validation; five-minute deadline |

Private evidence, bookmarks, batches, proposals, and validation receipts live in
`~/.local/state/codex-improve/`. Aton retains its own execution history under
`~/.local/state/codex-automaton/codex-improve/`. Neither belongs in Git.
`latest.md` is the readable weekly result. New candidates and failed reviews
produce a local desktop notification when `notify-send` is available; unchanged
reviews remain quiet. `codex-improve status` includes the pending evidence count
so a bounded review never silently implies it covered the whole backlog.

The collector excludes configured private thread IDs and meta-automation roots
from learning, resolves compressed rollouts, and identifies ordinary automation
outcomes separately from human messages. Native history that cannot be proven
for a fork is conservatively excluded and reported. The initial window is seven
days; later passes use durable per-thread bookmarks and stable event IDs.
Stored message text is capped at 16,000 characters, with explicit truncation and
original-length fields. A relevant missing tail can be inspected through the
original JSONL path and logical line locator, including a later `.zst` copy;
the reviewer must report missing source rather than assume the prefix is complete.
Collection is bounded, so large backlogs may require more than one pass. Do not
delete bookmarks merely to force a new proposal.

## Install

From the dotfiles root, after the Python tests pass:

Requires Linux, Python 3.14 or newer (including `compression.zstd`), Git,
PyYAML for skill frontmatter validation, and an installed Aton executable.

```sh
python3 automation/codex/improve/install.py
systemctl --user start codex-observe.service
systemctl --user start codex-automaton@codex-improve.service
python3 automation/codex/improve/install.py --enable
```

The initial installation stages active job metadata with its timer unenabled,
backs up existing destinations, and verifies the units. `--enable` activates
only these two timers; it does not restart the shared Codex daemon or restore
unrelated paused automations. Do not reinstall while either service is running.
The weekly service's new-evidence condition precedes attempt creation. Failures
and timeouts retain the batch for a later retry; only a validated result
acknowledges its included events.

The managed Codex configuration and regular role files are installed separately:

```sh
./automation/codex/install-codex.sh
```

## Inspect and review

```sh
codex-improve status
systemctl --user list-timers 'codex-observe.timer' 'codex-automaton@codex-improve.timer'
journalctl --user -u codex-observe.service -u codex-automaton@codex-improve.service
codex-improve check CANDIDATE_ID
systemctl --user start codex-improvement-check@CANDIDATE_ID.service
codex-improve decision CANDIDATE_ID --status rejected
```

`finish` validates each candidate automatically. The explicit check commands
are useful after review or to inspect a previous failure. A syntax-valid patch
is not proof of behavioral improvement: the candidate records the expected
behavior, evidence, and remaining semantic assessment.

Accepting a candidate records a decision, not a live edit. Apply an accepted
patch through an authorized normal editing session, then record `--status
applied`; that decision succeeds only when the current target matches the
validated patched bytes. Applied/rejected history accompanies future reviews so
they can assess recurrence and avoid repeatedly proposing the same change.
The loop does not write Codex memories, publish, enable other jobs, or change its
own model, execution permissions, or schedule.

## Validation

```sh
python3 -m unittest discover -s automation/codex/improve -p 'test_*.py'
```

Tests use isolated state and source fixtures. They cover incrementality,
compressed replay, exclusion of inherited/meta evidence, failure recovery,
bounded manifests, schema/evidence validation, target/path restrictions, and
scratch-only patch application. Live smoke runs are separate from fixture tests.

## Pause

```sh
systemctl --user disable --now codex-observe.timer codex-automaton@codex-improve.timer
```

Disabling timers does not stop an already running service. Inspect the service
before deciding whether to stop it. Preserve the private state when pausing so
restoration continues from the same evidence and proposal decisions.

To exclude a setup or audit thread, pass `--exclude-root THREAD_ID` to the
installer. It merges exclusions into private `excluded-roots.json` in the
state directory; subsequent installs preserve them. The collector also accepts
`--exclude-root` for an individual run. Keep actual thread IDs out of Git.
