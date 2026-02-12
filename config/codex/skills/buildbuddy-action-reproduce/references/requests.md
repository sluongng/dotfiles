# BuildBuddy Action Reproduction Request Templates

Use these templates to identify a single action in an invocation and replay it with `bb execute`.

## Quick start with helper script

```bash
SKILL_DIR=/home/nb/.dotfiles/config/codex/skills/buildbuddy-action-reproduce

"$SKILL_DIR/scripts/generate_bb_execute.py" \
  --invocation 'https://app.buildbuddy.io/invocation/<INVOCATION_ID>' \
  --group-id <GROUP_ID> \
  --action-digest-hash <ACTION_DIGEST_HASH> \
  --pin-to-original-worker
```

Use selectors based on what you know:
- `--execution-id <id>`
- `--action-digest-hash <hash>`
- `--target-label <label> --mnemonic <mnemonic> --primary-output <path>`

## Common setup

```bash
BASE_URL=${BASE_URL:-https://app.buildbuddy.io}
GRPC_TARGET=${GRPC_TARGET:-remote.buildbuddy.io}
API_KEY=$(git config --local buildbuddy.api-key)
GROUP_ID=<GROUP_ID>
INVOCATION_INPUT='<INVOCATION_ID_OR_URL>'
OUT_DIR=${OUT_DIR:-$(mktemp -d -t bb-action-repro.XXXX)}
mkdir -p "$OUT_DIR"

if [[ -z "$API_KEY" ]]; then
  echo "Missing BuildBuddy API key. Run: bb login" >&2
  return 1
fi

extract_invocation_id() {
  local in="$1"
  if [[ "$in" =~ ^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$ ]]; then
    echo "${in,,}"
    return 0
  fi
  local id
  id=$(sed -nE 's#.*\/invocation\/([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}).*#\1#p' <<<"$in" | head -n1)
  [[ -n "$id" ]] || return 1
  echo "${id,,}"
}

INVOCATION_ID=$(extract_invocation_id "$INVOCATION_INPUT") || {
  echo "Could not parse invocation ID from: $INVOCATION_INPUT" >&2
  return 1
}

bb_json() {
  local name="$1"; shift
  local path="$OUT_DIR/$name.json"
  if [[ -s "$path" && -z "${BB_FORCE:-}" ]]; then
    cat "$path"
  else
    "$@" | tee "$path"
  fi
}
```

## Get invocation metadata

```bash
bb_json get_invocation curl "$BASE_URL/rpc/BuildBuddyService/GetInvocation" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data '{
    "requestContext": {"groupId": "'"$GROUP_ID"'"},
    "lookup": {"invocationId": "'"$INVOCATION_ID"'"}
  }'
```

Extract replay defaults from canonical structured command line:

```bash
canon_opt() {
  local name="$1"
  jq -r --arg name "$name" '
    (.invocation[0].structuredCommandLine // [])
    | (map(select(.commandLineLabel == "canonical"))[0] // .[0] // {})
    | .sections[]?.optionList?.option[]?
    | select(.optionName == $name)
    | .optionValue
  ' "$OUT_DIR/get_invocation.json" | tail -n1
}

REMOTE_EXECUTOR=$(canon_opt remote_executor)
if [[ -z "$REMOTE_EXECUTOR" ]]; then
  REMOTE_EXECUTOR=$(canon_opt remote_cache)
fi
REMOTE_INSTANCE=$(canon_opt remote_instance_name)
DIGEST_FUNCTION=$(canon_opt digest_function)
if [[ -z "$DIGEST_FUNCTION" ]]; then
  DIGEST_FUNCTION=sha256
fi

# Optional: infer gRPC target from remote_executor URL.
if [[ -n "$REMOTE_EXECUTOR" ]]; then
  GRPC_TARGET=$(sed -E 's#^[a-z]+://##; s#/.*$##' <<<"$REMOTE_EXECUTOR")
fi
```

## Get executions for the invocation

```bash
bb_json get_execution curl "$BASE_URL/rpc/BuildBuddyService/GetExecution" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data '{
    "requestContext": {"groupId": "'"$GROUP_ID"'"},
    "executionLookup": {"invocationId": "'"$INVOCATION_ID"'"},
    "inlineExecuteResponse": true
  }'
```

List candidate actions:

```bash
jq -r '
  .execution[]? |
  [
    .executionId,
    (.actionDigest.hash + "/" + (.actionDigest.sizeBytes|tostring)),
    .targetLabel,
    .actionMnemonic,
    .primaryOutputPath,
    ((.status.code // 0)|tostring),
    (.exitCode|tostring),
    (.executedActionMetadata.worker // ""),
    (if .executeResponseDigest.hash then (.executeResponseDigest.hash + "/" + (.executeResponseDigest.sizeBytes|tostring)) else "" end)
  ] | @tsv
' "$OUT_DIR/get_execution.json"
```

## Narrow down to one execution

By action digest hash:

```bash
ACTION_DIGEST_HASH=<ACTION_DIGEST_HASH>
jq --arg h "$ACTION_DIGEST_HASH" '
  first(.execution[]? | select(.actionDigest.hash == $h))
' "$OUT_DIR/get_execution.json" > "$OUT_DIR/selected_execution.json"
```

By target + mnemonic + primary output:

```bash
TARGET_LABEL='//path/to:target'
MNEMONIC='CppCompile'
PRIMARY_OUTPUT='bazel-out/.../foo.o'
jq --arg t "$TARGET_LABEL" --arg m "$MNEMONIC" --arg p "$PRIMARY_OUTPUT" '
  first(.execution[]? | select(.targetLabel == $t and .actionMnemonic == $m and .primaryOutputPath == $p))
' "$OUT_DIR/get_execution.json" > "$OUT_DIR/selected_execution.json"
```

By execution ID:

```bash
EXECUTION_ID=<EXECUTION_ID>
jq --arg e "$EXECUTION_ID" '
  first(.execution[]? | select(.executionId == $e))
' "$OUT_DIR/get_execution.json" > "$OUT_DIR/selected_execution.json"
```

Extract selected digests:

```bash
ACTION_DIGEST=$(jq -r '.actionDigest.hash + "/" + (.actionDigest.sizeBytes|tostring)' "$OUT_DIR/selected_execution.json")
EXECUTION_ID=$(jq -r '.executionId' "$OUT_DIR/selected_execution.json")
EXECUTE_RESPONSE_DIGEST=$(jq -r 'if .executeResponseDigest.hash then (.executeResponseDigest.hash + "/" + (.executeResponseDigest.sizeBytes|tostring)) else "" end' "$OUT_DIR/selected_execution.json")
```

## Build action page URL for "Copy as bb-execute"

```bash
ACTION_URL="$BASE_URL/invocation/$INVOCATION_ID?executionId=$EXECUTION_ID&actionDigest=$ACTION_DIGEST"
if [[ -n "$EXECUTE_RESPONSE_DIGEST" ]]; then
  ACTION_URL="${ACTION_URL}&executeResponseDigest=$EXECUTE_RESPONSE_DIGEST"
fi
ACTION_URL="${ACTION_URL}#action"
echo "$ACTION_URL"
```

Open that URL and use the action card button "Copy as bb-execute".

## Map host ID to executor ID for pinning

`debug-executor-id` expects `ExecutionNode.executor_id`.
If you only have host ID (`executedActionMetadata.worker`), map it first:

```bash
WORKER_HOST_ID=$(jq -r '.executedActionMetadata.worker // ""' "$OUT_DIR/selected_execution.json")

bb_json get_execution_nodes curl "$BASE_URL/rpc/BuildBuddyService/GetExecutionNodes" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data '{
    "requestContext": {"groupId": "'"$GROUP_ID"'"}
  }'

jq -r --arg host "$WORKER_HOST_ID" '
  .executor[]?
  | select(.node.executorHostId == $host)
  | [.node.executorId, .node.executorHostId, .node.host, .node.pool, .node.osFamily, .node.arch]
  | @tsv
' "$OUT_DIR/get_execution_nodes.json"
```

Pin replay to one executor:

```bash
PIN_EXECUTOR_ID=<EXECUTOR_ID>
# Add this flag to the copied bb execute command:
# --exec_properties=debug-executor-id=<EXECUTOR_ID>
```

## Optional fallback: download Action and Command protos

Use this when you cannot use the UI copy button.

```bash
cas_resource() {
  local digest="$1" # hash/size
  local hash="${digest%/*}"
  local size="${digest#*/}"
  local fn="${DIGEST_FUNCTION,,}"
  local prefix="${REMOTE_INSTANCE:+${REMOTE_INSTANCE}/}blobs"
  if [[ "$fn" != "sha256" ]]; then
    prefix="$prefix/$fn"
  fi
  echo "$prefix/$hash/$size"
}

ACTION_RESOURCE=$(cas_resource "$ACTION_DIGEST")
bb download "$ACTION_RESOURCE" \
  --type=Action \
  --target="$GRPC_TARGET" \
  --remote_header="x-buildbuddy-api-key=$API_KEY" \
  > "$OUT_DIR/action.json"

COMMAND_DIGEST=$(jq -r '.commandDigest.hash + "/" + (.commandDigest.sizeBytes|tostring)' "$OUT_DIR/action.json")
COMMAND_RESOURCE=$(cas_resource "$COMMAND_DIGEST")
bb download "$COMMAND_RESOURCE" \
  --type=Command \
  --target="$GRPC_TARGET" \
  --remote_header="x-buildbuddy-api-key=$API_KEY" \
  > "$OUT_DIR/command.json"
```

From `action.json` + `command.json`, reconstruct:
- args from `arguments[]`
- env from `environmentVariables[]`
- exec properties from `platform.properties[]`
- outputs from `outputPaths[]` (or `outputFiles[]` and `outputDirectories[]`)
- timeout from `action.timeout`
- input root from `action.inputRootDigest`
