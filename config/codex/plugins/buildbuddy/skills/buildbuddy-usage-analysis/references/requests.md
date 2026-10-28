# BuildBuddy Usage/Trends: Request Templates

Use these as copy/paste starting points. Keep API keys out of logs and outputs.

## Common shell setup

Use the [shared API setup](../../../references/api-common.md#shell-setup) for
`BASE_URL`, `API_KEY`, `GROUP_ID`, `TZ_OFFSET_MINUTES`, `OUT_DIR`, and `bb_json`.
Choose the authorized deployment and group, then set the task inputs below.
Use distinct cache names when invocation IDs, filters, or dates change.

```bash
UPDATED_AFTER='2026-10-01T00:00:00Z'
UPDATED_BEFORE='2026-10-08T00:00:00Z'
```

## GetGroup (resolve group ID from org slug)

```bash
URL_IDENTIFIER=<org-slug>
bb_json get_group curl --fail-with-body --silent --show-error "$BASE_URL/rpc/BuildBuddyService/GetGroup" \
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
bb_json get_usage curl --fail-with-body --silent --show-error "$BASE_URL/rpc/BuildBuddyService/GetUsage" \
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
bb_json get_trend curl --fail-with-body --silent --show-error "$BASE_URL/rpc/BuildBuddyService/GetTrend" \
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
bb_json get_stat_heatmap curl --fail-with-body --silent --show-error "$BASE_URL/rpc/BuildBuddyService/GetStatHeatmap" \
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
bb_json get_stat_drilldown curl --fail-with-body --silent --show-error "$BASE_URL/rpc/BuildBuddyService/GetStatDrilldown" \
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
bb_json search_invocation curl --fail-with-body --silent --show-error "$BASE_URL/rpc/BuildBuddyService/SearchInvocation" \
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
bb_json search_execution curl --fail-with-body --silent --show-error "$BASE_URL/rpc/BuildBuddyService/SearchExecution" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data '{
    "requestContext": {"groupId": "'"$GROUP_ID"'"},
    "query": {
      "updatedAfter": "'"$UPDATED_AFTER"'",
      "updatedBefore": "'"$UPDATED_BEFORE"'",
      "invocationStatus": ["FAILURE"]
    },
    "count": 25
  }'
```

## GetTargetTrends

Use this for the Target Performance page's **per-target remote execution metric
aggregates across invocations**, not target/test-result enumeration.
It requires the feature to be enabled, an OLAP database, and stats access to the
selected group.

`POST /rpc/BuildBuddyService/GetTargetTrends` — save this body as
`$OUT_DIR/target-trends.request.json`, replacing the group and choosing a time window:

```json
{
  "requestContext": {"groupId": "GROUP_ID"},
  "query": {
    "updatedAfter": "2026-10-01T00:00:00Z",
    "updatedBefore": "2026-10-08T00:00:00Z"
  },
  "metric": "EXECUTION_CPU_NANOS_EXECUTION_METRIC",
  "agg": "SUM_TARGET_AGGREGATION",
  "targetLabelFilter": "//pkg/"
}
```

```bash
bb_json target_trends curl --fail-with-body --silent --show-error \
  "$BASE_URL/rpc/BuildBuddyService/GetTargetTrends" \
  -H 'Content-Type: application/json' \
  -H "x-buildbuddy-api-key: $API_KEY" \
  --data-binary @"$OUT_DIR/target-trends.request.json"
```

- `query` is a `TrendQuery`: repo/branch/commit/time, invocation attributes,
  execution dimensions, and generic filters. Without a start time, the current
  implementation defaults to seven days.
- `metric` is a scalar `ExecutionMetricType` enum, **not** the `{execution: ...}`
  `Metric` wrapper used by heatmap and drilldown. Use the pinned
  `proto/stat_filter.proto` for metric names and units.
- `agg` supports sum (default), average, min, max, P50, P90, and P99 over matching
  execution measurements after deduplication, not averages of whole build durations.
- `targetLabelFilter` is one case-insensitive substring; wildcard characters
  are literal. `//pkg/...` is not expanded. Omit it to rank all observed labels.
- Results are `targetStats[]` with `target` and `value`, sorted by value descending
  with label tie-breaking. The current page size is 50. Copy `nextPageToken` to
  `pageToken` in an otherwise unchanged request, using a different cache name
  for each page, until no token remains.
- Only recorded remote executions with nonempty labels and `cached_result = false`
  contribute. The query excludes merged invocation links and deduplicates by
  target label and execution UUID; an original link outside the selection can
  therefore leave logical uses uncounted. This is not all local/cached work or
  a complete target inventory, nor per-invocation status records.

Sources: `proto/stats.proto:GetTargetTrendsRequest`,
`enterprise/server/invocation_stat_service/invocation_stat_service.go:GetTargetTrends`,
and `enterprise/app/targets/targets.tsx:fetchTargetTrends`.
See the [API index](../../../references/api-reference.md) for source/version scope.

## GetExecutionTimeline

Use this for one target's action-performance history across invocations, as used
by the newer single-target detail page. The older target-click route instead
opens the [drilldown APIs](#target-filtered-drilldown).

`POST /rpc/BuildBuddyService/GetExecutionTimeline`:

```json
{
  "requestContext": {"groupId": "GROUP_ID", "timezone": "UTC"},
  "target": "//pkg:target1",
  "query": {
    "updatedAfter": "2026-10-01T00:00:00Z",
    "updatedBefore": "2026-10-08T00:00:00Z"
  }
}
```

`target` is mandatory and exact, not a pattern. `query` is `ExecutionQuery`
(the same type as SearchExecution). This RPC needs OLAP and authorized stats
access; UI availability also depends on its feature configuration.
`timelines[]` groups measurements by normalized output path, mnemonic, OS, and
architecture, with `summary`, time-bucketed `aggregatedStats`, and
`executionSamples` containing invocation IDs. Only rows with worker start/end
and an output path qualify. The individual events are a bounded random sample
(currently at most 1,000 across all timelines), **not** an exhaustive export.
There is no continuation token. Use [SearchExecution](#searchexecution-execution-level-drilldown-events)
for paginated execution rows instead.

Sources: `proto/execution_stats.proto:GetExecutionTimelineRequest` and
`enterprise/server/execution_search_service/execution_search_service.go:GetExecutionTimeline`.

## GetInvocationStat

Use this for invocation-level aggregates grouped by repositories, users, branches,
or commits, rather than target execution metrics.

`POST /rpc/BuildBuddyService/GetInvocationStat`:

```json
{
  "requestContext": {"groupId": "GROUP_ID"},
  "aggregationType": "REPO_URL_AGGREGATION_TYPE",
  "limit": 100,
  "query": {
    "updatedAfter": "2026-10-01T00:00:00Z",
    "updatedBefore": "2026-10-08T00:00:00Z"
  }
}
```

An aggregation type is required. Other types include user, host, group, commit,
date, branch, and recorded command pattern. The response's `invocationStat[]`
contains entity `name`, build counts, total build time, and latest build times.
The default limit is 100; explicit limits must be 1–1,000. This is a bounded
aggregate list ordered by latest build activity, not a metric-ranked top-N or
a paginated invocation search. Locally sorting a limited response does not establish
a global ranking. It uses `InvocationStatQuery`,
not `TrendQuery`, and tag filtering requires OLAP. Stats access to the group
is required.

Sources: `proto/invocation.proto:GetInvocationStatRequest` and
`enterprise/server/invocation_stat_service/invocation_stat_service.go:GetInvocationStat`.

## Target-filtered drilldown

Clicking a target in the older Target Performance flow selects an execution
metric and adds this exact-label filter inside `query` for `GetStatHeatmap`,
`GetStatDrilldown`, and `SearchExecution`:

```json
{
  "dimensionFilter": [
    {
      "dimension": {"execution": "TARGET_LABEL_EXECUTION_DIMENSION"},
      "value": "//pkg:target1"
    }
  ]
}
```

The SQL predicate is `target_label = ?`, not substring or Bazel pattern matching.
Use `metric: {"execution": "EXECUTION_CPU_NANOS_EXECUTION_METRIC"}` for heatmap,
or `drilldownMetric` with that wrapper for drilldown charts. In GetStatDrilldown,
`query.dimensionFilter` restricts the whole population; top-level `filter` and
`dimensionFilter` define the selected subset compared with the base population.
SearchExecution returns execution rows with `invocationMetadata` and
`nextPageToken`; the page requests 25 examples, not a complete target inventory.
Follow returned tokens for an export and keep query/group/time fixed.

Do not put the target in `query.pattern`: that field matches the invocation's
recorded command-pattern string exactly. Multiple dimension filters are ANDed,
so appending two target-label filters does not express a label-set union.

Sources: `enterprise/app/trends/drilldown_page.tsx`,
`enterprise/app/trends/common.ts:encodeTargetLabelUrlParam`, and
`server/util/filter/filter.go:GenerateDimensionFilterStringAndArgs`.

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
Common filters include `user`, `repo`, `branch`, `commit`, `host`, `command`, `pattern`,
`tag`, `status`, and `role`. Drilldown selections use `ddSelection` or `ddZoom`
with `start|end|bucketStart|bucketEnd|eventsSelected` encoding.

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
