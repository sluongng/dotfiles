# Bazel Build and Test Benchmarks

Use this alongside the performance skill's matched-workload and causality rules.
It applies to local, remote-cache, and remote-execution build/test comparisons,
not to ordinary correctness checks.

## Validate the cache protocol before the expensive matrix

Define the intended cache phases and prove them with a narrow representative
target before running the full workload. Verify the selected Bazel version's
flag semantics for cache reads, writes, and test-result reuse independently;
do not infer write behavior from a flag's name. Check remote-cache/execution
access and build-event service (BES) access separately without printing secrets.

Keep these measurements distinct:

| Phase | What to verify |
| --- | --- |
| Forced execution / population | Intended actions or tests execute; result writes remain enabled if the next phase depends on them. |
| Remote reuse after clean local outputs | The intended remote action/test results are reused; record any remaining executions. |
| Mixed-hit reuse | Record the actual hit and execution counts rather than labeling it fully cached. |
| Local no-op | Existing local outputs or test results are reused; do not label this remote-cache performance. |

Use invocation data, build-event protocol (BEP) results, profiles, or logs to
verify the transitions. Record the cleaning/reset procedure and separate local
outputs, local test results, disk cache, remote action cache, remote blob store,
and executor-local state. Clean local outputs or disabled action-cache reads do
not establish that every remote cache or worker is cold.

Record source revision, Bazel/JDK versions, effective flags, execution strategy,
jobs/concurrency, download policy, targets, and fixtures for each comparison.
Compare matched concurrency separately from higher-concurrency experiments.
Count test targets, shards, attempts, cached results, and new executions
separately when they differ. A cache-enabled speedup with fewer executing tests
is not a pure transfer-speed improvement.

For warm incremental comparisons, verify Bazel server/JVM continuity within
each arm and record the actual runtime, not just the Java compilation target.
Use separate persistent servers when comparing rebuilt Bazel binaries. Prime
each measured source state and execution path before timing; an already-warm
JVM can still encounter a path's first-use cost. Compare selected actions and
input-tree shapes across arms, not cache-hit percentages alone: skipped actions
or reused aggregate subtrees can remove the work being optimized. Keep local
no-op, remote action-cache reuse, and remote execution with warm CAS distinct,
and verify the workload's required output equivalence.

## Reconcile timing boundaries before assigning a cause

For CI latency, align check registration, parent-pipeline start, downstream
worker start, Bazel command intervals, and check completion. A check marked
`RUNNING` can include queueing or provisioning before a worker starts; inspect
the pipeline's reporting boundary instead of attributing that whole interval
to remote execution. Separate pre-parent waiting, pre-worker waiting, and actual
command time. Name capacity exhaustion or slow provisioning as the cause only
when queue or agent evidence distinguishes them. If invocation access is denied,
CI logs can still establish commands, invocation IDs, and timing, but do not
claim server-side execution or cache analysis from those logs alone.

Preserve full client command wall time, exit status, invocation URLs, profiles,
and client/server logs. Inspect the existing artifacts before starting follow-up
runs; use the invocation-troubleshooting workflow when BuildBuddy evidence is
available. Run a new experiment when the preserved evidence leaves a material
question unresolved, not merely because another run is possible.

Do not equate Bazel's reported build interval, the remote invocation duration,
or finalized server cache statistics with client command completion. Uploads,
downloads, event reporting, and shutdown can extend beyond a reporting boundary.
If command wall time regresses while reported build time stays flat, align the
timestamps and identify the outstanding client wait before blaming compilation
or a particular server operation. Use a focused profile, log, or thread dump
when needed; missing work in finalized statistics is not proof it never happened.

Target results or a "Build completed" line do not establish successful command
completion. Wait for the process exit and preserve post-build failures. Report
build-interval and end-to-end results with their respective boundaries. Do not
sum overlapping remote-action or shard durations as client elapsed time.

## Keep failed attempts and scope visible

Preserve failed or protocol-invalid attempts separately from valid measurements
and disclose exclusions and their reasons. Report command failures separately
from failed test executions: replaying a cached failure is not a new execution.
If a replacement measurement is warranted within the requested run budget,
repeat the whole affected cell with the same source, workload, flags, concurrency,
cache protocol, and timing definition. Do not filter failing tests or enlarge
timeouts to obtain a favorable benchmark. Stop and report an incomplete cell
when repeated failures prevent a trustworthy result.

If the protocol changes, identify which measurements became invalid; keep
unaffected valid results instead of rerunning the entire matrix. If the candidate
changes, preserve the old results and identify the new revision in its rerun.
Report failed-attempt counts alongside the successful sample distribution, and
do not imply that a median of successful runs measures reliability.

A before/after commit-stack comparison measures the bundle, not an individual
flag's effect. Attribute a feature only with a matched same-revision ablation,
and keep uncertainty about the underlying mechanism explicit.
