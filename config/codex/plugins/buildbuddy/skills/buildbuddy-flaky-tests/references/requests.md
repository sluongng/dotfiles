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

Use the [shared API setup](../../../references/api-common.md#shell-setup) for
HTTP auth and the selected group, then choose the repo and time window below.

```bash
REPO_URL=https://github.com/buildbuddy-io/buildbuddy
BRANCH=master
STARTED_AFTER=2026-04-28T00:00:00Z
STARTED_BEFORE=2026-05-05T00:00:00Z
```

## GetTargetStats

```bash
curl --fail-with-body --silent --show-error "$BASE_URL/rpc/BuildBuddyService/GetTargetStats" \
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
curl --fail-with-body --silent --show-error "$BASE_URL/rpc/BuildBuddyService/GetDailyTargetStats" \
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
curl --fail-with-body --silent --show-error "$BASE_URL/rpc/BuildBuddyService/GetTargetFlakeSamples" \
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

## GetTargetHistory

Use this for Test Grid-style histories across invocations/commits, not for a
complete repository inventory or the execution-performance page.

`POST /rpc/BuildBuddyService/GetTargetHistory`:

```json
{
  "requestContext": {"groupId": "GROUP_ID"},
  "query": {"repoUrl": "https://github.com/example/project"},
  "serverSidePagination": true
}
```

The response contains `invocationTargets[]` with per-label target histories and
`nextPageToken`. Copy the token to `pageToken` with the same query to continue.
The current page window is 40 distinct commits, not 40 individual targets.
There is no arbitrary label-list or recursive-pattern selector.
Do not assume that every field declared in `TargetQuery` is effective: the
schema warns that only repo applies in server-side pagination mode; the current
OLAP path additionally uses branch. Check the selected backend before relying
on other query fields or date bounds.

History depends on enabled target tracking and eligible CI `test`/`coverage`
invocations, authentication, event availability, and retention. A missing row
is not proof that a label did not run or does not exist.
See `proto/target.proto`, `server/target/target.go:GetTargetHistory`, and
`server/build_event_protocol/target_tracker/target_tracker.go` for the exact gates.

## Collection and pagination limits

The flake-statistics RPCs above require OLAP-backed test status reads and
operate on recorded uncached test data in the authorized group.
GetTargetStats is an evidence-filtered, bounded list (currently at most 500),
not every test in a repository. Daily stats likewise omit dates without the
relevant evidence. Although GetDailyTargetStats declares `pageToken`, its
current handler does not consume that token or return a continuation token.
GetTargetFlakeSamples does paginate (currently five candidates per page), but
only candidates with suitable recorded test output artifacts produce samples.
Follow actual tokens; do not infer completeness from the response array length.

Source scope and the distinction from performance analytics are in the
[API index](../../../references/api-reference.md).
