# BuildBuddy Invocation Troubleshooting: Request Templates

Use these as copy/paste starting points. Replace placeholders and keep API keys redacted in logs.

## Common shell setup

```bash
BASE_URL=${BASE_URL:-https://app.buildbuddy.io}
API_KEY=$(git config --local buildbuddy.api-key)
GROUP_ID=<GROUP_ID>
INVOCATION_ID=<INVOCATION_ID>
TZ_OFFSET_MINUTES=-60
```

If `API_KEY` is empty, run `bb login` first.

## SearchInvocation (find recent invocations)

```bash
curl "$BASE_URL/rpc/BuildBuddyService/SearchInvocation" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data '{
    "requestContext": {"groupId": "'"$GROUP_ID"'", "timezoneOffsetMinutes": '"$TZ_OFFSET_MINUTES"'},
    "query": {
      "groupId": "'"$GROUP_ID"'",
      "updatedAfter": "2023-06-25T23:00:00.00Z",
      "updatedBefore": "2023-06-26T23:00:00.00Z"
    },
    "sort": {"sortField": "UPDATED_AT_USEC_SORT_FIELD", "ascending": false},
    "count": 100
  }' | jq -r '.invocation[].invocationId'
```

## GetInvocation (metadata + console buffer)

```bash
curl "$BASE_URL/rpc/BuildBuddyService/GetInvocation" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data '{
    "requestContext": {"groupId": "'"$GROUP_ID"'", "timezoneOffsetMinutes": '"$TZ_OFFSET_MINUTES"'},
    "lookup": {"invocationId": "'"$INVOCATION_ID"'", "fetchChildInvocations": true}
  }'
```

## GetTarget (failed targets + stdout/stderr)

```bash
curl "$BASE_URL/rpc/BuildBuddyService/GetTarget" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data '{
    "requestContext": {"groupId": "'"$GROUP_ID"'"},
    "invocationId": "'"$INVOCATION_ID"'",
    "status": "FAILED"
  }'
```

Look for `actionEvents[].actionExecuted.stdout` / `stderr` (files may have `uri` or inline `contents`).

## GetExecution (RBE executions for an invocation)

```bash
curl "$BASE_URL/rpc/BuildBuddyService/GetExecution" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data '{
    "requestContext": {"groupId": "'"$GROUP_ID"'"},
    "executionLookup": {"invocationId": "'"$INVOCATION_ID"'"},
    "inlineExecuteResponse": true
  }'
```

## SearchExecution (filter by repo/branch/time window)

```bash
curl "$BASE_URL/rpc/BuildBuddyService/SearchExecution" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data '{
    "requestContext": {"groupId": "'"$GROUP_ID"'"},
    "query": {
      "repoUrl": "https://github.com/buildbuddy-io/buildbuddy",
      "updatedAfter": "2023-06-25T23:00:00.00Z",
      "updatedBefore": "2023-06-26T23:00:00.00Z",
      "invocationStatus": ["FAILED"]
    },
    "count": 100
  }'
```

## GetCacheScoreCard (server-side cache request logs)

```bash
curl "$BASE_URL/rpc/BuildBuddyService/GetCacheScoreCard" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data '{
    "requestContext": {"groupId": "'"$GROUP_ID"'"},
    "invocationId": "'"$INVOCATION_ID"'",
    "orderBy": "ORDER_BY_DURATION",
    "descending": true
  }'
```

## GetEventLogChunk (build log text)

```bash
curl "$BASE_URL/rpc/BuildBuddyService/GetEventLogChunk" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data '{
    "requestContext": {"groupId": "'"$GROUP_ID"'"},
    "invocationId": "'"$INVOCATION_ID"'",
    "minLines": 500
  }'
```

## Download artifacts via /file/download

Raw build events:

```bash
curl -L "$BASE_URL/file/download?artifact=raw_json&invocation_id=$INVOCATION_ID" -o "${INVOCATION_ID}_raw.json"
curl -L "$BASE_URL/file/download?artifact=raw_proto&invocation_id=$INVOCATION_ID" -o "${INVOCATION_ID}_raw.proto"
```

Build log (requires attempt number, usually `invocation.attempt`):

```bash
curl -L "$BASE_URL/file/download?artifact=buildlog&invocation_id=$INVOCATION_ID&attempt=1" -o "${INVOCATION_ID}.log"
```

Execution profile (RBE only, needs execution_id from GetExecution):

```bash
EXECUTION_ID=<EXECUTION_ID>
curl -L "$BASE_URL/file/download?artifact=execution_profile&invocation_id=$INVOCATION_ID&execution_id=$EXECUTION_ID" -o "${EXECUTION_ID}.pb.gz"
```

Bytestream file download (from File.uri):

```bash
BYTESTREAM_URL='<BYTESTREAM_URL>'
curl -L "$BASE_URL/file/download?invocation_id=$INVOCATION_ID&bytestream_url=$(python3 -c 'import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1]))' "$BYTESTREAM_URL")" -o output.bin
```

## gRPC alternative (grpcurl)

```bash
grpcurl \
  -H "x-buildbuddy-api-key: $API_KEY" \
  -d '{"requestContext":{"groupId":"'"$GROUP_ID"'"},"lookup":{"invocationId":"'"$INVOCATION_ID"'"}}' \
  app.buildbuddy.io:443 buildbuddy.service.BuildBuddyService/GetInvocation
```
