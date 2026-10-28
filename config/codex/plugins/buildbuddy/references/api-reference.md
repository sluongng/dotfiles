# BuildBuddy API reference index

Start here when choosing an API or finding its request examples.
Read [common request conventions](api-common.md) once, then load only the reference for the workflow you need.
Keep task-specific filtering, `jq`, replay, and comparison procedures with their skills rather than copying every request into this index.

## API surfaces

| Surface | Address | Contract and use |
| --- | --- | --- |
| Public API, `api.v1.ApiService` | `POST /api/v1/<Method>` | [Public retrieval examples](public-api.md); the documented external API. |
| UI RPCs, `buildbuddy.service.BuildBuddyService` | `POST /rpc/BuildBuddyService/<Method>` | The richer queries used by the UI and these skills; not interchangeable with similarly named public API methods. |
| Official MCP server | Organization `/mcp` endpoint | [MCP configuration](buildbuddy-mcp.md); use exposed tools when sufficient, but do not assume it exposes every RPC below. |

The same method name does not imply the same request schema or result semantics.
For example, public `GetTarget` uses `selector.invocationId` and an optional exact `selector.label`; UI `GetTarget` uses `invocationId`, `targetLabel`, status, and a substring filter.

## Invocation and execution investigation

| API | Use | Request reference | Schema |
| --- | --- | --- | --- |
| `GetInvocation` | One invocation's metadata, command line, and collected events | [Troubleshooting](../skills/buildbuddy-invocation-troubleshoot/references/requests.md#getinvocation-metadata--console-buffer) | `proto/invocation.proto` |
| `SearchInvocation` | Find invocations by metadata and time range | [Troubleshooting](../skills/buildbuddy-invocation-troubleshoot/references/requests.md#searchinvocation-find-recent-invocations) | `proto/invocation.proto` |
| `GetTarget` | Targets and associated events in one invocation | [Troubleshooting](../skills/buildbuddy-invocation-troubleshoot/references/requests.md#gettarget-failed-targets--stdoutstderr) | `proto/target.proto` |
| `GetExecution` | Invocation-scoped execution/action details | [Troubleshooting](../skills/buildbuddy-invocation-troubleshoot/references/requests.md#getexecution-rbe-executions-for-an-invocation) | `proto/execution_stats.proto` |
| `SearchExecution` | Filtered execution records across invocations | [Troubleshooting](../skills/buildbuddy-invocation-troubleshoot/references/requests.md#searchexecution-filter-by-repobranchtime-window) | `proto/execution_stats.proto` |
| `GetExecutionTimeline` | One target's action-performance timelines and bounded samples | [Usage and performance](../skills/buildbuddy-usage-analysis/references/requests.md#getexecutiontimeline) | `proto/execution_stats.proto` |
| `GetExecutionNodes` | Map an observed worker host ID to an executor for replay | [Action replay](../skills/buildbuddy-action-reproduce/references/requests.md#map-host-id-to-executor-id-for-pinning) | `proto/scheduler.proto` |
| `GetCacheScoreCard` | Cache request logs for one invocation | [Troubleshooting](../skills/buildbuddy-invocation-troubleshoot/references/requests.md#getcachescorecard-server-side-cache-request-logs) | `proto/cache.proto` |
| `GetEventLogChunk` | Invocation build-log text chunks | [Troubleshooting](../skills/buildbuddy-invocation-troubleshoot/references/requests.md#geteventlogchunk-build-log-text) | `proto/eventlog.proto` |

For paired invocation requests and response comparisons, use [invocation comparison](../skills/buildbuddy-invocation-compare/references/requests.md).
For replay selection and command construction, use [action reproduction](../skills/buildbuddy-action-reproduce/references/requests.md).

## Usage, trends, and target analytics

| API | Use | Request reference | Schema |
| --- | --- | --- | --- |
| `GetGroup` | Resolve an authorized organization slug to its group context | [Group lookup](../skills/buildbuddy-usage-analysis/references/requests.md#getgroup-resolve-group-id-from-org-slug) | `proto/grp.proto` |
| `GetUsage` | Monthly billing-usage counters; admin access required | [Usage](../skills/buildbuddy-usage-analysis/references/requests.md#getusage-monthly-usage) | `proto/usage.proto` |
| `GetTrend` | Time-series invocation and execution aggregates | [Trends](../skills/buildbuddy-usage-analysis/references/requests.md#gettrend-time-series-aggregates) | `proto/stats.proto` |
| `GetStatHeatmap` | Metric distribution over time | [Heatmaps](../skills/buildbuddy-usage-analysis/references/requests.md#getstatheatmap-distribution-over-time) | `proto/stats.proto` |
| `GetStatDrilldown` | Breakdown charts comparing a selection with its base population | [Drilldowns](../skills/buildbuddy-usage-analysis/references/requests.md#getstatdrilldown-drill-into-a-selected-bucket) | `proto/stats.proto` |
| `GetTargetTrends` | Remote execution metrics aggregated by target across invocations | [Target Performance](../skills/buildbuddy-usage-analysis/references/requests.md#gettargettrends) | `proto/stats.proto` |
| `GetInvocationStat` | Invocation aggregates grouped by user, repo, commit, or another dimension | [Invocation aggregates](../skills/buildbuddy-usage-analysis/references/requests.md#getinvocationstat) | `proto/invocation.proto` |
| `GetTargetHistory` | Tracked CI test-target status history across commits | [Test history](../skills/buildbuddy-flaky-tests/references/requests.md#gettargethistory) | `proto/target.proto` |
| `GetTargetStats` | Flaky, likely-flaky, and nearly-timeout target statistics | [Flaky targets](../skills/buildbuddy-flaky-tests/references/requests.md#gettargetstats) | `proto/target.proto` |
| `GetDailyTargetStats` | Daily test-statistics aggregates | [Daily statistics](../skills/buildbuddy-flaky-tests/references/requests.md#getdailytargetstats) | `proto/target.proto` |
| `GetTargetFlakeSamples` | Example test results for one target | [Flake samples](../skills/buildbuddy-flaky-tests/references/requests.md#gettargetflakesamples) | `proto/target.proto` |

Choose by the data required, not just by a method name containing “target.”
`GetTargetTrends` measures recorded remote work; `GetTargetHistory` and flake APIs read tracked test statuses; public `GetTarget` lists label-level data from one invocation's build events.
None is a general Bazel target-pattern expansion service.

## Source map and scope

This index was checked against BuildBuddy revision `017562c412cbabe1a7aecb70334a90dca28cfce3`.
It covers retrieval and analytics relevant to this plugin's workflows, not every service or message under `proto/`.
Administrative writes, account/security configuration, scheduler internals, distributed-cache internals, VM services, and protocol mirrors are outside this reference.
Documentation does not authorize an API call or imply that a feature is enabled in a particular deployment.

- [Public service](https://github.com/buildbuddy-io/buildbuddy/blob/017562c412cbabe1a7aecb70334a90dca28cfce3/proto/api/v1/service.proto) and [public handler](https://github.com/buildbuddy-io/buildbuddy/blob/017562c412cbabe1a7aecb70334a90dca28cfce3/enterprise/server/api/api_server.go).
- [UI service](https://github.com/buildbuddy-io/buildbuddy/blob/017562c412cbabe1a7aecb70334a90dca28cfce3/proto/buildbuddy_service.proto) and [RPC routing](https://github.com/buildbuddy-io/buildbuddy/blob/017562c412cbabe1a7aecb70334a90dca28cfce3/server/buildbuddy_server/buildbuddy_server.go).
- Analytics implementations: `enterprise/server/invocation_stat_service/invocation_stat_service.go`, `enterprise/server/execution_search_service/execution_search_service.go`, and `server/target/target.go`.
- For a new or changed method, trace its proto through routing to the implementation and a representative test or UI caller before adding examples.
  Declared fields, especially pagination fields, do not alone establish implemented behavior.
