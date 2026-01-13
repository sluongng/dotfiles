# BuildBuddy Invocation Compare: Request Templates

Use these as copy/paste starting points. Replace placeholders and keep API keys redacted in logs.

## Common shell setup

```bash
BASE_URL=${BASE_URL:-https://app.buildbuddy.io}
API_KEY=$(git config --local buildbuddy.api-key)
GROUP_ID=<GROUP_ID>
INVOCATION_OLD=<INVOCATION_ID_OLD>
INVOCATION_NEW=<INVOCATION_ID_NEW>
TZ_OFFSET_MINUTES=-60
OUT_DIR=${OUT_DIR:-$(mktemp -d -t bb-compare.XXXX)}
mkdir -p "$OUT_DIR"

# Cache API responses to avoid repeated calls. Set BB_FORCE=1 to refresh.
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

If `API_KEY` is empty, run `bb login` first.

## GetInvocation (metadata + structured command line)

```bash
bb_json get_invocation_old curl "$BASE_URL/rpc/BuildBuddyService/GetInvocation" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data '{
    "requestContext": {"groupId": "'"$GROUP_ID"'", "timezoneOffsetMinutes": '"$TZ_OFFSET_MINUTES"'},
    "lookup": {"invocationId": "'"$INVOCATION_OLD"'", "fetchChildInvocations": true}
  }'

bb_json get_invocation_new curl "$BASE_URL/rpc/BuildBuddyService/GetInvocation" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data '{
    "requestContext": {"groupId": "'"$GROUP_ID"'", "timezoneOffsetMinutes": '"$TZ_OFFSET_MINUTES"'},
    "lookup": {"invocationId": "'"$INVOCATION_NEW"'", "fetchChildInvocations": true}
  }'
```

## Extract canonical flags (sorted)

```bash
jq -r '
  .invocation[0].structuredCommandLine[]
  | select(.commandLineLabel != null)
  | select(.commandLineLabel | test("canonical"; "i"))
  | .sections[]
  | select(.sectionLabel | test("startup|command"; "i"))
  | .optionList.option[]
  | "--" + .optionName + (if .optionValue == "" then "" else "=" + .optionValue end)
' "$OUT_DIR/get_invocation_old.json" | sort -u > "$OUT_DIR/old.flags"

jq -r '
  .invocation[0].structuredCommandLine[]
  | select(.commandLineLabel != null)
  | select(.commandLineLabel | test("canonical"; "i"))
  | .sections[]
  | select(.sectionLabel | test("startup|command"; "i"))
  | .optionList.option[]
  | "--" + .optionName + (if .optionValue == "" then "" else "=" + .optionValue end)
' "$OUT_DIR/get_invocation_new.json" | sort -u > "$OUT_DIR/new.flags"

diff -u "$OUT_DIR/old.flags" "$OUT_DIR/new.flags"
```

If no canonical command line is present, fall back to the only `structuredCommandLine` entry and note the limitation.

## GetCacheScoreCard (AC read misses ordered by start time)

```bash
bb_json cache_scorecard_old curl "$BASE_URL/rpc/BuildBuddyService/GetCacheScoreCard" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data '{
    "requestContext": {"groupId": "'"$GROUP_ID"'"},
    "invocationId": "'"$INVOCATION_OLD"'",
    "filter": {
      "mask": {"paths": ["request_type", "response_type", "cache_type"]},
      "requestType": "READ",
      "responseType": "NOT_FOUND",
      "cacheType": "AC"
    },
    "orderBy": "ORDER_BY_START_TIME",
    "descending": false
  }'

bb_json cache_scorecard_new curl "$BASE_URL/rpc/BuildBuddyService/GetCacheScoreCard" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data '{
    "requestContext": {"groupId": "'"$GROUP_ID"'"},
    "invocationId": "'"$INVOCATION_NEW"'",
    "filter": {
      "mask": {"paths": ["request_type", "response_type", "cache_type"]},
      "requestType": "READ",
      "responseType": "NOT_FOUND",
      "cacheType": "AC"
    },
    "orderBy": "ORDER_BY_START_TIME",
    "descending": false
  }'
```

To identify the first shared AC miss (target + mnemonic), use:

```bash
python3 scripts/find_first_shared_ac_miss.py \
  "$OUT_DIR/cache_scorecard_old.json" \
  "$OUT_DIR/cache_scorecard_new.json"
```

## GetExecution (all actions for an invocation, inline ExecuteResponse)

```bash
bb_json get_execution_old curl "$BASE_URL/rpc/BuildBuddyService/GetExecution" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data '{
    "requestContext": {"groupId": "'"$GROUP_ID"'"},
    "executionLookup": {"invocationId": "'"$INVOCATION_OLD"'"},
    "inlineExecuteResponse": true
  }'

bb_json get_execution_new curl "$BASE_URL/rpc/BuildBuddyService/GetExecution" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data '{
    "requestContext": {"groupId": "'"$GROUP_ID"'"},
    "executionLookup": {"invocationId": "'"$INVOCATION_NEW"'"},
    "inlineExecuteResponse": true
  }'
```

Filter executions for the target+mnemonic (and optionally primary output) to locate the rerun action:

```bash
TARGET='//path:label'
MNEMONIC='CppCompile'
PRIMARY_OUTPUT='bazel-out/.../file.o'

jq -c --arg t "$TARGET" --arg m "$MNEMONIC" --arg p "$PRIMARY_OUTPUT" '
  .execution[]
  | select(.targetLabel == $t)
  | select(.actionMnemonic == $m)
  | (if $p == "" then . else select(.primaryOutputPath == $p) end)
' "$OUT_DIR/get_execution_old.json" > "$OUT_DIR/old.exec.json"

jq -c --arg t "$TARGET" --arg m "$MNEMONIC" --arg p "$PRIMARY_OUTPUT" '
  .execution[]
  | select(.targetLabel == $t)
  | select(.actionMnemonic == $m)
  | (if $p == "" then . else select(.primaryOutputPath == $p) end)
' "$OUT_DIR/get_execution_new.json" > "$OUT_DIR/new.exec.json"
```

## Download Action / ActionResult / Tree via tools/cas

Use `bazel run //tools/cas` to fetch REAPI protos from CAS/AC.

```bash
CACHE_TARGET=grpcs://remote.buildbuddy.io
API_KEY=$(git config --local buildbuddy.api-key)

# Action digest (CAS)
ACTION_HASH=<HASH>
ACTION_SIZE=<SIZE_BYTES>

bazel run //tools/cas -- \
  -target="$CACHE_TARGET" \
  -api_key="$API_KEY" \
  -resource="/blobs/$ACTION_HASH/$ACTION_SIZE" \
  -type=Action > "$OUT_DIR/action.json"

# ActionResult digest (AC)
AR_HASH=<HASH>
AR_SIZE=<SIZE_BYTES>

bazel run //tools/cas -- \
  -target="$CACHE_TARGET" \
  -api_key="$API_KEY" \
  -resource="/blobs/ac/$AR_HASH/$AR_SIZE" \
  -type=ActionResult > "$OUT_DIR/action_result.json"

# Input root tree (CAS)
TREE_HASH=<HASH>
TREE_SIZE=<SIZE_BYTES>

bazel run //tools/cas -- \
  -target="$CACHE_TARGET" \
  -api_key="$API_KEY" \
  -resource="/blobs/$TREE_HASH/$TREE_SIZE" \
  -type=Tree > "$OUT_DIR/input_tree.json"
```

## Download compact execution logs

When `execution_log.binpb.zst` appears in build tool logs, download via bytestream:

```bash
BYTESTREAM_URL='bytestream://remote.buildbuddy.io/blobs/blake3/<HASH>/<SIZE>'

curl -L "$BASE_URL/file/download?invocation_id=$INVOCATION_OLD&bytestream_url=$(python3 -c 'import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))' "$BYTESTREAM_URL")" \
  -o "$OUT_DIR/$INVOCATION_OLD.execution_log.binpb.zst"
```

Then compare logs:

```bash
bb explain --old "$OUT_DIR/$INVOCATION_OLD.execution_log.binpb.zst" \
  --new "$OUT_DIR/$INVOCATION_NEW.execution_log.binpb.zst"
```

Alternatively, pass invocation IDs directly to `bb explain` when the logs are available in BES:

```bash
bb explain --old "$INVOCATION_OLD" --new "$INVOCATION_NEW"
```
