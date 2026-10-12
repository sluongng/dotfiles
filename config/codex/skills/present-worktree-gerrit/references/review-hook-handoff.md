# Gerrit review bridge: installed runtime

The bridge is implemented in `/home/nb/work/cli/local-gerrit/runtime/` and enabled
as `local-gerrit-review.service`. Gerrit has the source-built `hooks` plugin and
a `hooks/comment-added` script. Verify live service/plugin status before claiming
it is active; this document is not a health check.

## Operations

Read the **Review-to-session bridge** section of
[`OPERATIONS.md`](/home/nb/work/cli/local-gerrit/OPERATIONS.md) for installation,
registration, completion and recovery. Relevant files:

- `runtime/review-bridge.py`: durable binding, reconciliation, session dispatch
  and verified threaded replies.
- `runtime/install-review-bridge.py`: isolated dependencies, hook installation,
  plugin hot-load and user service setup without Gerrit/Codex restart.
- `runtime/test_review_bridge.py`: review lifecycle and failure-path tests.
- Private state: `~/.local/state/local-gerrit/review-bridge/state.json`.

```sh
systemctl --user is-active local-gerrit-review.service
local-gerrit --json request GET /plugins/
local-gerrit-review status
journalctl --user -u local-gerrit-review.service -n 30 --no-pager
```

Review state contains private feedback; do not dump it into public logs or PRs.
The shared Codex Unix control socket uses **WebSocket framing**, not line-delimited
JSON. Never start another app-server to resume the original session.

## Binding and recovery invariants

First binding baselines existing Gerrit messages; it does not replay old reviews.
Bind only the exact originating persistent user thread and task worktree. Never
bind an ephemeral side conversation or a subagent. Preserve stack order, source
branch, base and Change-Ids. Gerrit's synthetic IDs depend on commit position when
source commits lack explicit IDs; insertion/reordering requires care and renewed
verification, not assumptions about identity.

Only published reviews from the pinned human account trigger work. Message IDs
provide deduplication, and inline comments are linked to their specific review
message. Active sessions receive guarded steering; idle sessions resume with
existing settings. Later reviews wait behind the current event.

Delivery acknowledgement is not completion. The session must assess feedback,
validate, verify uploads, and call the event-specific completion helper. That
helper verifies current revisions, source trees and parent chain, posts original-
patchset threaded replies plus a current-patchset summary, and marks completion.
Replies are authored by `codex`, tagged as automation, and use `notify: NONE`.

Uncertain delivery is reconciled against the event marker in thread history.
Do not blindly retry or infer successful completion from final prose. Inspect
blocked events and their turn before an explicit retry. Completed REST writes
whose responses were lost are reconciled using reply markers. No upstream
publication, external notifications, submission or merging is authorized.

To disable future dispatch without interrupting an existing review turn:

```sh
systemctl --user disable --now local-gerrit-review.service
```
