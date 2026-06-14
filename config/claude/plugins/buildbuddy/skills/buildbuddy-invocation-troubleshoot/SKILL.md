---
name: buildbuddy-invocation-troubleshoot
description: Troubleshoot BuildBuddy invocations via BuildBuddyService (HTTP JSON or gRPC). Use when asked to debug a BuildBuddy invocation, find failed targets and stdout/stderr, inspect remote cache vs RBE metadata, retrieve execution details/profiles/logs, download raw build events or Bazel profiles, or fetch cache scorecard data.
metadata:
  short-description: Troubleshoot a BuildBuddy invocation and fetch logs/artifacts.
---

# BuildBuddy Invocation Troubleshoot

## Overview

Use this skill to investigate a BuildBuddy invocation end-to-end: locate the invocation, identify failing targets, collect stdout/stderr, determine whether RBE or remote cache was involved, and download build artifacts (raw BES, build logs, execution profiles, cache scorecard).

## Workflow (recommended)

### 0) Preflight: auth + base URL

- Avoid accessing the API key value directly. Check presence by piping to `wc` and treating any non-empty value as valid, e.g. `git config --local buildbuddy.api-key | wc -c`.
- If the API key is missing (empty output), ask the user to run `bb login` and retry.
- Confirm the base URL (default `https://app.buildbuddy.io` unless self-hosted).
- Collect `group_id` and (if already known) `invocation_id`.
- Create a temp working directory (per investigation) and store **all** downloaded artifacts and API responses there. Reuse cached files to avoid re-calling the API; delete a cached file or set a force flag when you want a fresh response.

Reference request templates live in `references/requests.md`.

### 1) Find the invocation ID

- Use `SearchInvocation` with a time window (`updated_after` / `updated_before`), group ID, and optional filters (repo, branch, user, status, command).
- Sort by `UPDATED_AT_USEC_SORT_FIELD` descending to find the latest runs.
- If the user already has an invocation URL, extract the `invocation_id` from it and skip search.

### 2) Fetch invocation metadata

- Call `GetInvocation` with `invocation_id` to retrieve:
  - `console_buffer` (fastest way to see the failure banner)
  - `remote_execution_enabled`, `upload_local_results_enabled`, `download_outputs_option`
  - `cache_stats` and `score_card` (if remote cache was used)
  - `structured_command_line` to detect flags (remote executor, BES, etc.)
  - `invocation_status` to confirm completeness
- Note and report the git commit hash, branch name, OS, and hostname from the invocation metadata. If these match the local environment, reproduction may be feasible.

If `invocation_status` is not complete, expect partial logs and missing artifacts.

### 3) Identify failing targets + stdout/stderr

- Use `GetTarget` for the invocation.
  - Filter by `status=FAILED` or `filter` to narrow labels.
  - Focus on `root_cause` targets when present.
- For each failing target, inspect `action_events` (ActionExecuted) for:
  - `stdout` / `stderr` file descriptors
  - `exit_code`, `command_line`, `failure_detail`
- Download target logs using the file `uri` (if present) or by passing the `bytestream_url` to `/file/download`.

### 4) If RBE is involved, drill into executions

- When `remote_execution_enabled=true`, use `GetExecution` (by `invocation_id`) or `SearchExecution` to locate the execution.
- For execution details:
  - `execute_response` (use `inline_execute_response=true`) contains ActionResult and stdout/stderr digests.
  - `executed_action_metadata` provides queue/execute timestamps.
  - `execution_id`, `target_label`, `action_mnemonic`, and `command_snippet` help correlate to the failing target.
- If multiple executions failed but later retries succeeded, filter `SearchExecution` by the exact failing target label (from `GetTarget`) or by `primary_output` to avoid unrelated transient failures. A single target label can map to many actions, so `primary_output` is often the best discriminator.
- Download the execution profile (if enabled) via `/file/download?artifact=execution_profile&invocation_id=...&execution_id=...`.

### 5) Download build events / build log / Bazel profile

- Raw BES JSON/Proto:
  - `/file/download?artifact=raw_json&invocation_id=...`
  - `/file/download?artifact=raw_proto&invocation_id=...`
- Build log (BES text chunks):
  - `/file/download?artifact=buildlog&invocation_id=...&attempt=...`
- Bazel profile:
  - Usually attached as an artifact file in BES. Find it from invocation/target files, then download via `/file/download` with its bytestream URL or direct `uri`.

### 6) Cache scorecard (server-side cache requests)

- Use `GetCacheScoreCard` with `invocation_id`.
- Apply filters for request/response type and search for a specific target/action mnemonic.
- Use `order_by` to surface slow or large transfers.

## Tips and safety

- Avoid printing API keys in outputs. Redact before sharing.
- When making requests, use shell expansion like `$(git config --local buildbuddy.api-key)` instead of pasting the API key directly.
- Prefer smaller time windows in searches to avoid large result sets.
- For JSON mapping, proto fields are lowerCamelCase (e.g., `requestContext`, `groupId`).
- When unsure about fields, check these protos:
  - `proto/buildbuddy_service.proto`
  - `proto/invocation.proto`
  - `proto/target.proto`
  - `proto/build_event_stream.proto`
  - `proto/execution_stats.proto`
  - `proto/cache.proto`
  - `proto/eventlog.proto`
