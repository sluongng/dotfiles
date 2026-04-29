# BuildBuddy Usage/Trends: Request Templates

Use these as copy/paste starting points. Keep API keys out of logs and outputs.

## Common shell setup

```bash
BASE_URL=${BASE_URL:-https://app.buildbuddy.io}
API_KEY=$(git config --local buildbuddy.api-key)
GROUP_ID=<GROUP_ID>
TZ_OFFSET_MINUTES=${TZ_OFFSET_MINUTES:-0}
OUT_DIR=${OUT_DIR:-$(mktemp -d -t bb-usage.XXXX)}
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
If `GetUser` returns `NotFound` (common with org API keys), resolve the group ID via `GetGroup` using `urlIdentifier`.
`GetUsage` is admin-only; a developer key will return `PermissionDenied`.

## GetGroup (resolve group ID from org slug)

```bash
URL_IDENTIFIER=<org-slug>
bb_json get_group curl "$BASE_URL/rpc/BuildBuddyService/GetGroup" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data '{
    "requestContext": {},
    "urlIdentifier": "'"$URL_IDENTIFIER"'"
  }'
```

## GetUsage (monthly usage)

```bash
USAGE_PERIOD=<YYYY-MM> # empty for current
bb_json get_usage curl "$BASE_URL/rpc/BuildBuddyService/GetUsage" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data '{
    "requestContext": {"groupId": "'"$GROUP_ID"'"},
    "usagePeriod": "'"$USAGE_PERIOD"'"
  }'
```

## GetTrend (time series aggregates)

```bash
UPDATED_AFTER=2025-12-01T00:00:00.00Z
UPDATED_BEFORE=2025-12-31T23:59:59.00Z
bb_json get_trend curl "$BASE_URL/rpc/BuildBuddyService/GetTrend" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data '{
    "requestContext": {"groupId": "'"$GROUP_ID"'", "timezoneOffsetMinutes": '"$TZ_OFFSET_MINUTES"'},
    "query": {
      "updatedAfter": "'"$UPDATED_AFTER"'",
      "updatedBefore": "'"$UPDATED_BEFORE"'",
      "role": ["CI"]
    }
  }'
```

## GetStatHeatmap (distribution over time)

```bash
bb_json get_stat_heatmap curl "$BASE_URL/rpc/BuildBuddyService/GetStatHeatmap" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data '{
    "requestContext": {"groupId": "'"$GROUP_ID"'"},
    "metric": {"invocation": "DURATION_USEC_INVOCATION_METRIC"},
    "query": {
      "updatedAfter": "'"$UPDATED_AFTER"'",
      "updatedBefore": "'"$UPDATED_BEFORE"'",
      "role": ["CI"]
    }
  }'
```

## GetStatDrilldown (drill into a selected bucket)

```bash
bb_json get_stat_drilldown curl "$BASE_URL/rpc/BuildBuddyService/GetStatDrilldown" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data '{
    "requestContext": {"groupId": "'"$GROUP_ID"'"},
    "drilldownMetric": {"invocation": "DURATION_USEC_INVOCATION_METRIC"},
    "query": {
      "updatedAfter": "'"$UPDATED_AFTER"'",
      "updatedBefore": "'"$UPDATED_BEFORE"'",
      "role": ["CI"]
    },
    "filter": [
      {"metric": {"invocation": "DURATION_USEC_INVOCATION_METRIC"}, "min": 60000000, "max": 120000000}
    ]
  }'
```

## SearchInvocation (get sample invocations for a drilldown)

```bash
bb_json search_invocation curl "$BASE_URL/rpc/BuildBuddyService/SearchInvocation" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data '{
    "requestContext": {"groupId": "'"$GROUP_ID"'", "timezoneOffsetMinutes": '"$TZ_OFFSET_MINUTES"'},
    "query": {
      "groupId": "'"$GROUP_ID"'",
      "updatedAfter": "'"$UPDATED_AFTER"'",
      "updatedBefore": "'"$UPDATED_BEFORE"'"
    },
    "sort": {"sortField": "UPDATED_AT_USEC_SORT_FIELD", "ascending": false},
    "count": 25
  }'
```

## SearchExecution (execution-level drilldown events)

```bash
bb_json search_execution curl "$BASE_URL/rpc/BuildBuddyService/SearchExecution" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data '{
    "requestContext": {"groupId": "'"$GROUP_ID"'"},
    "query": {
      "updatedAfter": "'"$UPDATED_AFTER"'",
      "updatedBefore": "'"$UPDATED_BEFORE"'",
      "invocationStatus": ["FAILED"]
    },
    "count": 25
  }'
```

## Notes

- Use small time windows to keep responses light.
- `timezoneOffsetMinutes` controls bucketing for trend charts and should match the user's locale when comparing UI output.
- For projections, use the last date present in `dailyUsage` rather than the count of entries (arrays may not start on day 1).

## UI quick links (visuals)

Use the org base URL from `GetGroup` (field `url`).

```text
<ORG_URL>/trends/?start=YYYY-MM-DD&end=YYYY-MM-DD#builds
<ORG_URL>/trends/?start=YYYY-MM-DD&end=YYYY-MM-DD#cache
<ORG_URL>/trends/?start=YYYY-MM-DD&end=YYYY-MM-DD#cas
<ORG_URL>/trends/?start=YYYY-MM-DD&end=YYYY-MM-DD#savings
<ORG_URL>/trends/?start=YYYY-MM-DD&end=YYYY-MM-DD#drilldown&ddMetric=i<INVOCATION_METRIC_ENUM>
```

`ddMetric` uses `i<invocationEnum>` or `e<executionEnum>`; use metric enum values from your API docs.

Example:

```text
<ORG_URL>/trends/?start=2026-01-01&end=2026-01-31#builds
<ORG_URL>/trends/?start=2026-01-01&end=2026-01-31#cache
<ORG_URL>/trends/?start=2026-01-01&end=2026-01-31#cas
<ORG_URL>/trends/?start=2026-01-01&end=2026-01-31#savings
<ORG_URL>/trends/?start=2026-01-01&end=2026-01-31#drilldown&ddMetric=i1
<ORG_URL>/trends/?start=2026-01-01&end=2026-01-31#drilldown&ddMetric=i4
<ORG_URL>/trends/?start=2026-01-01&end=2026-01-31#drilldown&ddMetric=e7
<ORG_URL>/trends/?start=2026-01-01&end=2026-01-31#drilldown&ddMetric=e9
```

Example ddMetric labels:
- `i1` = invocation duration (total build duration)
- `i4` = invocation cache download size (CAS download bytes)
- `e7` = execution input download size (RBE cache download bytes)
- `e9` = execution wall time (total execution time)

All ddMetric values:

Invocation metrics (`i*`)
- `i1` duration (total build duration)
- `i2` CAS cache misses
- `i3` updated at (timestamp)
- `i4` CAS cache download size (bytes)
- `i5` CAS cache download speed (bytes/sec)
- `i6` CAS cache upload size (bytes)
- `i7` CAS cache upload speed (bytes/sec)
- `i8` action cache misses
- `i9` time saved (cached execution time)

Execution metrics (`e*`)
- `e1` queue time
- `e2` updated at (timestamp)
- `e3` input download time
- `e4` real execution time
- `e5` output upload time
- `e6` peak memory
- `e7` input download size
- `e8` output upload size
- `e9` execution wall time
- `e10` execution CPU nanos
- `e11` execution average millicores
