---
name: buildbuddy-usage-analysis
description: Analyze BuildBuddy billing usage and trends data, fetch GetUsage/GetTrend/GetStatHeatmap/GetStatDrilldown/SearchInvocation/SearchExecution data, compare periods, spot anomalies, and recommend cost-saving actions while protecting API keys.
metadata:
  short-description: Analyze BuildBuddy usage trends and cost anomalies.
---

# BuildBuddy Usage Analysis

## Overview

Fetch usage + trends data from BuildBuddyService, store responses in a temp dir, analyze for spikes/drops, and recommend cost savings. Prioritize API key safety and small time windows.

## Quick start

1) Use `references/requests.md` to set `BASE_URL`, `API_KEY`, `GROUP_ID`, and `OUT_DIR`.
2) Call `GetUsage` for current and prior months.
3) Call `GetTrend` for a time window aligned with the usage comparison.
4) Use the analyzer script or ad‑hoc math to compare and project.

## Preconditions and access

- Verify API key presence without printing it: `git config --local buildbuddy.api-key | wc -c`.
- If `GetUser` returns `NotFound` (common with org API keys), use `GetGroup` with `urlIdentifier` to resolve `GROUP_ID`.
- `GetUsage` is admin-only. If you get `PermissionDenied`, switch to an org admin key or admin user for the group.

## Fetch data (usage + trends)

Use the request templates in `references/requests.md`:

- `GetUsage` for the current month and the prior month (billing comparisons).
- `GetTrend` for the same window (time-series context and cache hit rates).
- If drilling down: `GetStatHeatmap`, `GetStatDrilldown`, then `SearchInvocation` or `SearchExecution` for sample events.

Notes:
- Keep windows small (days/weeks) to reduce payload size.
- JSON fields are lowerCamelCase (e.g., `dailyUsage`, `actionCacheHits`).

## Visual URLs (trends + drilldown)

Use the org base URL from `GetGroup` (field `url`).

Trends charts:

```
<ORG_URL>/trends/?start=YYYY-MM-DD&end=YYYY-MM-DD#builds
<ORG_URL>/trends/?start=YYYY-MM-DD&end=YYYY-MM-DD#cache
<ORG_URL>/trends/?start=YYYY-MM-DD&end=YYYY-MM-DD#cas
<ORG_URL>/trends/?start=YYYY-MM-DD&end=YYYY-MM-DD#savings
```

Drilldown view:

```
<ORG_URL>/trends/?start=YYYY-MM-DD&end=YYYY-MM-DD#drilldown&ddMetric=i<INVOCATION_METRIC_ENUM>
```

Common query params: `start`, `end`, `days`, `user`, `repo`, `branch`, `commit`, `host`, `command`, `pattern`, `tag`, `status`, `role`.

`ddMetric` format is `i<invocationEnum>` or `e<executionEnum>` (use the stat_filter metric enums from your API docs). Drilldown selections can be pinned via `ddSelection` or `ddZoom` (heatmap selection encoding: `start|end|bucketStart|bucketEnd|eventsSelected`).

Example URLs (agent can adapt as-is):

```
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

All ddMetric values (agent can use directly):

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

## Analyze for anomalies

Use quick ad-hoc analysis (jq / python) or the script:

- `scripts/analyze_usage_trends.py --usage usage.json --trend trend.json`

Look for:
- Spikes in `totalDownloadSizeBytes` or `totalUploadSizeBytes`.
- Drops in `actionCacheHits` or `casCacheHits`.
- Drops in action cache hit rate: `actionCacheHits / (actionCacheHits + actionCacheMisses)` from trend stats.
- Large changes in execution time or CPU nanos (`cloudCpuNanos`, `cloudRbeCpuNanos`).

## Project month-to-date usage

- Use `dailyUsage` to find the latest reported day (the array may not start on day 1).
- Project full-month totals by scaling `usage` totals by `full_days / last_reported_day`.
- Call out the projection method and the last reported date explicitly.

## Recommendations

When anomalies are found, prioritize cost-saving advice:

- Action Cache: reduce non-determinism, align toolchains, enable remote cache for CI.
- Download egress: avoid downloading large outputs, prefer minimal downloads, limit artifact retention.
- Drill down: use `GetStatDrilldown` to identify top users/repos/targets, then inspect sample invocations.
- For a specific invocation investigation, use `buildbuddy-invocation-troubleshoot`.

## Resources

- `references/requests.md`: request templates with safe API key handling and UI URLs.
- `scripts/analyze_usage_trends.py`: anomaly detector for usage/trends JSON.
