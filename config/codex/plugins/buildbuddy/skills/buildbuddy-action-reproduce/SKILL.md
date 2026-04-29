---
name: buildbuddy-action-reproduce
description: Reproduce a specific Bazel remote action from a BuildBuddy invocation and generate a customizable `bb execute` replay command. Use when a user provides an invocation URL/ID and wants to re-run one action, modify command args/env/exec properties, or pin execution to a specific executor using scheduler debug properties.
---

# BuildBuddy Action Reproduce

## Overview

Use this skill to go from invocation identifier to a concrete, reproducible action replay.
Use BuildBuddy API calls to identify the action and `bb execute` to replay and customize it.

Quick-start helper:

```bash
scripts/generate_bb_execute.py \
  --invocation 'https://app.buildbuddy.io/invocation/<INVOCATION_ID>' \
  --group-id <GROUP_ID> \
  --action-digest-hash <ACTION_DIGEST_HASH>
```

## Choose API vs CLI

Use a hybrid approach by default:

- Use BuildBuddy API (`GetInvocation`, `GetExecution`, `GetExecutionNodes`) to discover and narrow actions.
- Use `bb execute` to replay and customize the action.
- Prefer the UI "Copy as bb-execute" when a fully formed action page link is available.

Do not use `bb execute` alone for action discovery; it needs action details up front.

## Source Files To Trust

- `app/invocation/invocation_action_card.tsx`
  - Defines the "Copy as bb-execute" command format and which fields are carried over.
- `cli/execute/execute.go`
  - Defines replay flags (`--input_root_digest`, `--action_env`, `--exec_properties`, etc.).
- `enterprise/server/scheduling/scheduler_server/scheduler_server.go`
  - Defines scheduler pinning behavior for `debug-executor-id`.
- `proto/buildbuddy_service.proto`
  - Defines BuildBuddyService RPCs used for invocation/execution discovery.
- `proto/remote_execution.proto`
  - Defines `Action`, `Command`, `ExecuteRequest`, `ExecuteResponse`, `RequestMetadata`.

## Workflow

### 1) Preflight

- Confirm auth without printing secrets.
  - Check key presence using `git config --local buildbuddy.api-key | wc -c`.
  - If empty, ask the user to run `bb login`.
- Set base URL and gRPC target.
  - HTTP API default: `https://app.buildbuddy.io`
  - gRPC target default: `remote.buildbuddy.io`
- Create a temp output directory and cache JSON responses there.
- Accept invocation input as either UUID or URL.
  - Extract `invocation_id` from `/invocation/<uuid>`.
  - Keep optional query params if present: `actionDigest`, `executeResponseDigest`, `executionId`.

### 2) Identify the action candidate

- If action digest or execution ID is already provided, use it directly.
- Otherwise call:
  - `GetInvocation` for invocation metadata and command-line options.
  - `GetExecution` with `execution_lookup.invocation_id` to list candidate actions.
- If there are many matches, narrow in this order:
  1. `action_digest_hash`
  2. `execution_id`
  3. `(target_label, action_mnemonic, primary_output_path)` together
  4. fallback to failed actions or latest worker timestamp

### 3) Ask clarifying questions when action is ambiguous

When no unique action is identified, ask focused questions.

If `request_user_input` is available, ask one question at a time and prefer these identifiers:

1. action digest hash
2. execution ID
3. target label + mnemonic + primary output path

If `request_user_input` is unavailable in the current mode, ask the same questions directly in chat.

### 4) Build baseline replay command

- Preferred path:
  - Construct action page URL:
    - `/invocation/<invocation_id>?executionId=<execution_id>&actionDigest=<hash/size>[&executeResponseDigest=<hash/size>]#action`
  - Instruct user to click "Copy as bb-execute" in the action card.
- Fallback path:
  - Download `Action` and `Command` digests and compose `bb execute` manually.
- Always preserve:
  - `--remote_executor`
  - `--digest_function`
  - `--remote_instance_name`
  - `--input_root_digest`
  - `--remote_timeout` (if set)
  - `--action_env=*`
  - `--exec_properties=*`
  - `--output_path=*`
  - command arguments after `--`

### 5) Apply customization safely

- Command args: edit everything after the `--` separator.
- Env vars: add/edit/remove `--action_env=NAME=VALUE`.
- Exec properties: add/edit/remove `--exec_properties=NAME=VALUE`.
- Keep input root unchanged unless user explicitly wants different inputs.

### 6) Pin to a specific executor

Use this exec property:

```bash
--exec_properties=debug-executor-id=<executor_id>
```

Important distinctions:

- `debug-executor-id` expects `ExecutionNode.executor_id`, not `executor_host_id`.
- `Execution.executed_action_metadata.worker` may be a host identifier; map it via `GetExecutionNodes` when needed.
- If no connected executor matches, scheduler returns requested-executor-not-found behavior.

### 7) Verify reproduction

- Include `--invocation_id=<new_uuid>` for the replay run.
- Compare outcome to original action:
  - gRPC status
  - exit code
  - stdout/stderr
  - output digests if needed
- If the replay diverges, check differences in:
  - command args
  - env vars
  - exec properties
  - remote instance / digest function

## References

Run `scripts/generate_bb_execute.py` to auto-generate the replay command.
Load `references/requests.md` for copy/paste request templates and jq filters.
