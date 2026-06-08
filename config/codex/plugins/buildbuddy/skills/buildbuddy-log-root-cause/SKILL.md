---
name: buildbuddy-log-root-cause
description: Diagnose BuildBuddy or bb CLI log snippets and customer reports when there is no clean invocation URL, especially FastCDC capability warnings, BES upload failures, confusing invocation IDs, cache proxy behavior, executor UI questions, and source-backed root-cause analysis.
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
   - Prefer `rg` in `/home/nb/work/buildbuddy-io/buildbuddy` when the checkout is
     available.
   - Trace frontend gates and backend authorization separately for UI access
     questions.
   - Trace Bazel client, sidecar, BuildBuddy server, executor, and proxy layers
     separately before merging symptoms into one root cause.

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

## Output

Return a concise root cause with source references, confidence level, symptoms
that are separate, recommended next checks, and whether a focused BuildBuddy
skill should take over.
