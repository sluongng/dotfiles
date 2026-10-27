---
name: buildbuddy-log-root-cause
description: Diagnose BuildBuddy or bb CLI logs and reported symptoms when no specific invocation is available.
---

# BuildBuddy Log Root Cause

Use this for BuildBuddy reports that start from pasted logs, screenshots, vague
customer symptoms, or source-backed questions instead of a single invocation URL.
If the request is clearly internal, admin, or needs sensitive local data, prefer
the local-only BuildBuddy Dev plugin.

## Workflow

1. Normalize the symptom:
   - exact log lines and timestamps
   - Bazel, `bb` CLI, sidecar, executor, cache proxy, UI, or server component
   - whether an invocation URL, group, host, or executor id is available

2. Route when a focused skill fits:
   - invocation URL or target failure: `$buildbuddy-invocation-troubleshoot`
   - two invocations or cache invalidation comparison: `$buildbuddy-invocation-compare`
   - one action replay: `$buildbuddy-action-reproduce`
   - flaky target ranking: `$buildbuddy-flaky-tests`

3. If no focused skill fits, inspect source and logs directly:
   - Prefer `rg` in the local BuildBuddy checkout, usually
     `${BUILDBUDDY_CHECKOUT:-$HOME/work/buildbuddy-io/buildbuddy}`, when it is
     available.
   - Trace frontend gates and backend authorization separately for UI access
     questions.
   - Trace Bazel client, sidecar, BuildBuddy server, executor, and proxy layers
     separately before merging symptoms into one root cause.
   - For a source-backed support packet with missing runtime evidence, use
     `$ask-buddy` and its bounded support-preparation workflow.

## Known Diagnostic Shapes

- FastCDC warning with `bb`: check whether sidecar `GetCapabilities` failed its
  upstream call and returned default capabilities before blaming server support.
- BES upload failure: analyze `publishBuildEvents`, proxy stream `Recv`, ACKs,
  retries, and `bes_upload_mode` separately from cache capability warnings.
- Invocation id mismatch: distinguish request id, REAPI
  `RequestMetadata.tool_invocation_id`, and the BES stream invocation id.
- Executor page or role access: trace the frontend route gate and backend
  `allowed_rpc` or capability checks rather than inferring from role names.
- Cache proxy behavior: trace `FindMissing`, `BatchUpdateBlobs`, bytestream
  writes, remote downloader paths, and request metadata forwarding explicitly.
- Filecache or OCI reports: separate local executor state, OS behavior, isolation
  flags, and server-visible cache request data.
- Slow input preparation with high file-cache hit rates: trace the timer boundary
  in the affected executor version before interpreting it as network-transfer
  time. Separate input-tree metadata RPCs, directory/symlink creation, setup-limit
  waits, local link/copy operations, and cache-miss transfers where the timer
  includes them. Compare downloaded bytes/files and total input-tree size for
  representative slow actions with executor setup/file-cache latency and app RPC
  latency from the same workload window. A high hit rate alone rules out neither
  expensive local materialization nor large misses; near-zero transferred bytes
  warrant inspecting local setup, without proving a filesystem bottleneck.

## Output

Return the established root cause, or conditional triage when the evidence does
not establish one. Include source references, confidence level, symptoms that
are separate, the smallest decisive next checks, and whether a focused
BuildBuddy skill should take over. Do not label a source-supported possibility
as an observed cause.
