---
name: buildbuddy-invocation-compare
description: Compare two BuildBuddy invocation URLs or IDs to troubleshoot hermeticity/reproducibility and cache invalidation. Use when asked to diff canonical Bazel flags, find the first shared action-cache misses, inspect Action/ActionResult differences (inputs/command/env/platform/outputs), or analyze compact execution logs with `bb explain`.
metadata:
  short-description: Compare two BuildBuddy invocations and pinpoint cache/action differences.
---

# BuildBuddy Invocation Compare

## Overview

Compare two invocations end-to-end to isolate the earliest shared action-cache miss and pinpoint why actions are rebuilt or produce divergent outputs.

## Workflow

### 0) Preflight: auth + inputs

- Extract invocation IDs from the URLs.
- Confirm API base URL and API key presence without printing the key.
- Create a temp working directory and cache API responses there.
- Use the request templates in `references/requests.md`.

### 1) Diff canonical flags

- Call `GetInvocation` for both IDs.
- Extract the canonical command line (`structuredCommandLine.commandLineLabel` matching `canonical`).
- Sort flags and diff; highlight any differences in startup or command options.
- If canonical is missing, fall back to the only structured command line and note the limitation.
- Some entries may have `commandLineLabel=null`; filter them out to avoid jq errors.

### 2) Find the first shared AC miss

- Call `GetCacheScoreCard` for both invocations filtered to:
  - `cache_type=AC`, `request_type=READ`, `response_type=NOT_FOUND`
  - ordered by `start_time` ascending
- Use `scripts/find_first_shared_ac_miss.py` to identify the earliest shared `{target, mnemonic}` with AC misses on both sides.
- Record `target_id`, `action_mnemonic`, and `action_id` from each side for the next step.

### 3) Locate the rerun action(s)

- Call `GetExecution` with `inline_execute_response=true` for each invocation.
- Filter executions by target label, mnemonic, and primary output path (if known) to disambiguate actions.
- Capture:
  - `action_digest` (Action proto in CAS)
  - `action_result_digest` or `execute_response.result` (ActionResult)
  - `execute_response.result` (stdout/stderr/output digests)
  - `primary_output_path` to ensure you are comparing the correct action

### 4) Diff Action and ActionResult

Fetch protos via `bazel run //tools/cas` and compare with `diff -u` or `jq`.

Focus on these common divergence points:

- **Input root tree**: Compare `Action.input_root_digest`; if it differs, fetch both trees and identify differing file paths/digests. If only a few files differ, download and diff them.
- **Command args / outputs**: Compare `Command.arguments`, `Command.output_files`, and `Command.output_directories`. Expect platform or toolchain mismatches to surface here.
- **Env / platform properties**: Compare `Command.environment_variables` and `Action.platform.properties`. Treat differences as evidence of non-strict env or platform drift.
- **Output digests**: Compare `ActionResult.output_files` and `output_directories`; if digests differ with identical inputs/commands, suspect non-determinism.

Prefer `bb explain` when input roots differ and compact execution logs are available to pinpoint exact input changes.

### 5) Compact execution logs (optional)

- If `execution_log.binpb.zst` appears in the build tool logs, download both logs and diff with `bb explain`.
- Alternatively, pass invocation IDs directly to `bb explain` when the logs are available in BES.

## Response requirements

- Summarize the root cause clearly and tie it to the earliest shared AC miss.
- Call out which of the divergence categories applies (inputs, command/outputs, env/platform, output digest).
- Include a pointer to the compare UI sources: `app/compare/compare_actions.tsx` or `app/compare/compare_invocations.tsx` for deeper inspection.

## Resources

- `references/requests.md` for API + jq templates.
- `scripts/find_first_shared_ac_miss.py` to identify the earliest shared AC miss.
