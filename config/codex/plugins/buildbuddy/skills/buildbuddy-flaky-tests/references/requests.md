# BuildBuddy Flaky-Test RPCs

The flakes UI in `enterprise/app/tap/flakes.tsx` uses these BuildBuddyService
RPCs:

- `GetTargetStats`: list flaky targets for a repo, branch, and time window.
- `GetDailyTargetStats`: daily aggregate counts for the same filters.
- `GetTargetFlakeSamples`: sample flaky invocations for one target label.

The RPC definitions are in `proto/buildbuddy_service.proto`; request/response
messages are in `proto/target.proto`.

## JSON Field Mapping

Use lowerCamelCase JSON fields for protolet HTTP JSON:

- `requestContext.groupId`
- `requestContext.timezoneOffsetMinutes`
- `requestContext.timezone`
- `labels`
- `repo`
- `branchName`
- `startedAfter`
- `startedBefore`
- `pageToken`

`startedAfter` and `startedBefore` are `google.protobuf.Timestamp` values and
can be sent as RFC3339 strings such as `2026-05-01T00:00:00Z`.

## Common Setup

```bash
BASE_URL=${BASE_URL:-https://app.buildbuddy.io}
API_KEY=$(git config --local buildbuddy.api-key)
GROUP_ID=<GROUP_ID>
REPO_URL=https://github.com/buildbuddy-io/buildbuddy
BRANCH=master
STARTED_AFTER=2026-04-28T00:00:00Z
STARTED_BEFORE=2026-05-05T00:00:00Z
```

If `API_KEY` is empty, run `bb login` in the repo or set
`BUILDBUDDY_API_KEY`.

## GetTargetStats

```bash
curl "$BASE_URL/rpc/BuildBuddyService/GetTargetStats" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data '{
    "requestContext": {
      "groupId": "'"$GROUP_ID"'",
      "timezoneOffsetMinutes": 0
    },
    "repo": "'"$REPO_URL"'",
    "branchName": "'"$BRANCH"'",
    "startedAfter": "'"$STARTED_AFTER"'",
    "startedBefore": "'"$STARTED_BEFORE"'"
  }'
```

`stats[]` contains `label` and `data` with `totalRuns`, `flakyRuns`,
`likelyFlakyRuns`, `failedRuns`, and `totalFlakeRuntimeUsec`.

## GetDailyTargetStats

```bash
curl "$BASE_URL/rpc/BuildBuddyService/GetDailyTargetStats" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data '{
    "requestContext": {
      "groupId": "'"$GROUP_ID"'",
      "timezoneOffsetMinutes": 0
    },
    "repo": "'"$REPO_URL"'",
    "branchName": "'"$BRANCH"'",
    "startedAfter": "'"$STARTED_AFTER"'",
    "startedBefore": "'"$STARTED_BEFORE"'"
  }'
```

The response has `stats[]` entries with `date` and `data`.

## GetTargetFlakeSamples

```bash
LABEL=//server/foo:foo_test
curl "$BASE_URL/rpc/BuildBuddyService/GetTargetFlakeSamples" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data '{
    "requestContext": {
      "groupId": "'"$GROUP_ID"'",
      "timezoneOffsetMinutes": 0
    },
    "label": "'"$LABEL"'",
    "repo": "'"$REPO_URL"'",
    "branchName": "'"$BRANCH"'",
    "startedAfter": "'"$STARTED_AFTER"'",
    "startedBefore": "'"$STARTED_BEFORE"'"
  }'
```

Each sample includes `invocationId`, `invocationStartTimeUsec`, `status`, and a
Build Event `testResult`. Test logs are usually available through
`testResult.testActionOutput[]` entries named `test.xml` or `test.log`.
