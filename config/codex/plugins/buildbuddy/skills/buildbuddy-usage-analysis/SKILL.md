---
name: buildbuddy-usage-analysis
description: Analyze BuildBuddy usage, target and action performance across invocations, trends, drilldowns, and cost anomalies.
metadata:
  short-description: Analyze BuildBuddy usage and target performance.
---

# BuildBuddy Usage Analysis

## Overview

Choose the matching BuildBuddyService analytics API, store responses in a temp
directory, and analyze performance or usage across invocations. Keep API keys
private and time windows bounded. Use the [API index](../../references/api-reference.md)
when choosing between target results, execution metrics, and test history.

## Quick start

1) Use the [shared API setup](../../references/api-common.md#shell-setup).
2) Choose only the data needed for the question:
   - Billing: `GetUsage` and `GetTrend` for aligned periods.
   - Target Performance: `GetTargetTrends` to rank targets across invocations.
   - One target's action history: `GetExecutionTimeline`.
   - Invocation counts/time grouped by user, repo, branch, or commit: `GetInvocationStat`.
   - Distribution and breakdowns: `GetStatHeatmap` / `GetStatDrilldown`, then
     `SearchExecution` for execution rows or `SearchInvocation` for build rows.
3) Load the matching section of `references/requests.md`; do not fetch billing
   data for a target-performance-only question.
4) Analyze the saved results, preserving aggregation and sampling limits.

## Preconditions and access

- Verify API key presence without printing it: `git config --local buildbuddy.api-key | wc -c`.
- If `GetUser` returns `NotFound` (common with org API keys), use `GetGroup` with `urlIdentifier` to resolve `GROUP_ID`.
- `GetUsage` is admin-only. If you get `PermissionDenied`, report the missing access; use another authorized credential only when its group and scope are established.

## Fetch data (usage + trends)

Use the request templates in `references/requests.md`:

- `GetUsage` for the current month and the prior month (billing comparisons).
- `GetTrend` for the same window (time-series context and cache hit rates).
- `GetTargetTrends` for per-target RBE metric aggregates (substring label filter,
  actual pagination, not a full target inventory).
- `GetExecutionTimeline` for one exact target's summaries, buckets, and bounded
  execution samples; use `SearchExecution` for paginated row retrieval.
- `GetInvocationStat` for grouped invocation counts and durations.
- If drilling down: `GetStatHeatmap`, `GetStatDrilldown`, then `SearchInvocation`
  or `SearchExecution` for example rows. For target clicks, use
  `query.dimensionFilter`, not the invocation command `pattern`.

Notes:
- Keep windows small (days/weeks) to reduce payload size.
- JSON fields are lowerCamelCase (e.g., `dailyUsage`, `actionCacheHits`).

For links to the matching trends or drilldown view, load
[references/requests.md](references/requests.md#ui-quick-links-visuals). It includes URL parameters
and metric enum mappings; verify those against current source if they differ.

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

- [API index](../../references/api-reference.md): cross-skill API selection and source map.
- [Shared request conventions](../../references/api-common.md): auth, JSON, and caching.
- `references/requests.md`: focused analytics examples, limits, and UI URLs.
- `scripts/analyze_usage_trends.py`: anomaly detector for usage/trends JSON.
