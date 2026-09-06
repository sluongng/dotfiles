---
name: buildbuddy-usage-analysis
description: Analyze BuildBuddy billing usage and trends, compare periods, investigate anomalies, and estimate cost savings.
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
- `GetUsage` is admin-only. If you get `PermissionDenied`, report the missing access; use another authorized credential only when its group and scope are established.

## Fetch data (usage + trends)

Use the request templates in `references/requests.md`:

- `GetUsage` for the current month and the prior month (billing comparisons).
- `GetTrend` for the same window (time-series context and cache hit rates).
- If drilling down: `GetStatHeatmap`, `GetStatDrilldown`, then `SearchInvocation` or `SearchExecution` for sample events.

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

- `references/requests.md`: request templates with safe API key handling and UI URLs.
- `scripts/analyze_usage_trends.py`: anomaly detector for usage/trends JSON.
