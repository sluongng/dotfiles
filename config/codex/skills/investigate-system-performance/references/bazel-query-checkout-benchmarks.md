# Bazel Query and Checkout Benchmarks

Use this for native-checkout versus lazy-filesystem or prefetch comparisons.
Use the build/test reference as well only when measuring builds or execution.

## Match the source and transport

Pin both arms to the same commit, Bazel version, query, and effective repository
configuration. Pilot a successful native query before the matrix; do not disable
workspace rc files when they supply required settings. Verify equivalent target
sets, not just successful exits.

When the question is about GitHub or another hosted origin, measure that actual
transport. Local file transport and warm loopback proxies answer different
questions. Name the state of the proxy/mirror, Git objects, OS caches, Bazel
server/output base, and external dependencies rather than calling all of them
"cold." Keep any one-time external-dependency warmup explicit.

Probe required metadata capabilities before timing. Distinguish advertised
support, a successful direct request, and the product client's end-to-end path.
If the stock path fails, preserve that result. A benchmark-only REST importer or
protocol adapter can measure a conditional path, but label it separately, count
its request/import time, and do not claim the product supports that workflow.
Do not borrow local object contents or size tables in a remote-origin comparison
unless that reuse is an explicit part of the workload.

## Measure the whole workflow

For clone-to-first-query latency, use one continuous timer from clone start to
successful query process exit. Include required size discovery, cache import,
prefetch, mount readiness, and handoffs. Also retain phase timings and raw total
samples. A sum of phase medians is not the median end-to-end wall time; label
differences of medians separately from paired-trial differences.

Report first-query and same-server repeat-query results separately. Keep traced
diagnostic runs out of the timing samples when tracing changes the workload.
For storage-engine comparisons, match durability and inspect the actual I/O
path: an open/read/close loop may read memory and measure close-triggered syncs,
not database retrieval. Use counters or syscall traces to test that distinction.

## Account for hydration by phase

Record newly fetched object IDs and bytes separately for metadata warming,
prefetch, query, and later Git-status or inspection commands. Separate unique
objects from path aliases, logical content bytes from allocated disk, and source
repository storage from Bazel outputs and external dependencies.

For unexpected query fetches, inspect Git modes and access evidence before
calling them unnecessary. Symlink blobs hold target strings, not target file
contents. Queries can also read patches, requirements, downloader configuration,
and other module/rc-referenced inputs beyond Starlark. Distinguish a heuristic's
over-prefetch from files the timed command actually demand-fetched under its
flags. When batching is under evaluation, record actual request counts as well
as bytes; one selection command need not mean one network request.

## Validate the command's actual scope

Query checks package loading; `aquery` adds action analysis, but its `ActionKey`
is not an execution-input content digest. Use a real build/cache workflow with
output-equivalence and hydration checks to validate digest shortcuts.

For `--watchfs`, compare matched arms and validate mounted edits, package
additions, and removals, not only unchanged repeats. A watcher improvement does
not identify the individual costs of the default scan. Keep the mount alive
between commands; re-establish watches after remounting, using a fresh Bazel
server when needed. Treat Git fsmonitor and Bazel's filesystem watches as
separate mechanisms.
