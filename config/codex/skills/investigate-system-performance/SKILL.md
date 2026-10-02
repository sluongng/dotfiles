---
name: investigate-system-performance
description: "Diagnose performance regressions, interpret profiles, review benchmarks, or validate latency, throughput, and resource optimizations with representative measurements."
---

# Investigate System Performance

## Goal

Find the dominant cost, explain its mechanism, make the highest-leverage safe
change, and prove the outcome on a representative workload.

Base the workflow on Abseil's [Performance
Hints](https://abseil.io/fast/hints.html). Read
[`references/abseil-performance-playbook.md`](references/abseil-performance-playbook.md)
when selecting optimization techniques, diagnosing a flat profile, or designing
a microbenchmark.

## Core rules

- Define the performance objective and workload before optimizing.
- Prefer observed evidence over code-shape intuition. Use intuition to form a
  testable hypothesis, not to declare a cause.
- Compare the same release, build mode, configuration, input, and environment.
- Change one meaningful factor at a time when establishing causality.
- Treat a microbenchmark as a fast hypothesis tool, not a production forecast.
- Preserve correctness. Include correctness checks in every benchmark or load
  test when practical.
- Keep performance changes behind an encapsulation boundary when possible.
- Weigh runtime, memory, code size, readability, API stability, portability,
  operability, and maintenance together.
- Separate **measured effect**, **correlation**, **estimate**, **hypothesis**, and
  **remaining uncertainty** in reports.
- Do not claim a win when work merely moves to another resource, phase, process,
  or downstream service.

## Workflow

Match the depth to the request. Interpreting an existing profile or reviewing a
benchmark does not automatically require implementation, a new benchmark suite,
or production experiments. Use the stages below that resolve the question;
collect more evidence when it could change the conclusion.

### 1. Frame the question

Record:

- the user-visible objective: latency, tail latency, throughput, CPU time,
  memory, cost, startup time, build time, or scalability
- the exact workload and input distribution
- the affected scope and suspected regression window
- the target environment, concurrency, cache state, and data size
- correctness, API, complexity, memory, and rollout constraints
- the success threshold or budget

Distinguish setup or cold-path work from per-request or per-item hot-path work.
Treat reusable library code as higher leverage because many callers may pay its
cost.

If diagnosing a regression, first identify the narrowest reproducible baseline
and candidate. Prefer a same-release or otherwise controlled A/B that isolates
the feature or change under test.

### 2. Build a cost model

Estimate before instrumenting deeply:

1. Count expensive operations: bytes moved, allocations, comparisons, cache
   misses, lock acquisitions, syscalls, disk operations, RPCs, retries, or
   serialization steps.
2. Multiply by measured local costs when available; otherwise use explicitly
   labeled rough assumptions.
3. Separate total resource work from critical-path latency. Account for overlap,
   fan-out, queueing, concurrency, and variance.
4. Identify the likely dominant term and a plausible lower bound.

Calibrate rough operation costs on the actual hardware and environment before
using them for a decision. Do not copy historical latency tables as current
facts.

### 3. Establish a trustworthy baseline

Use the highest-fidelity repeatable workload available. Capture:

- source revision and exact command
- optimized production-equivalent build flags with usable symbols
- machine or worker type, CPU topology, memory, storage, and relevant limits
- inputs, request mix, concurrency, duration, warmup, cache state, and seed
- primary metric plus resource and correctness guardrails
- sample count, distribution or variance, and raw artifact paths

Prefer a ladder of increasing fidelity:

1. microbenchmark for iteration speed
2. component or single-task load test
3. end-to-end or cluster test
4. production observation when authorized

If two levels disagree, investigate the benchmark model. Do not average away
the disagreement.

For Bazel build/test comparisons, read
[`references/bazel-build-benchmarks.md`](references/bazel-build-benchmarks.md)
before starting the matrix or diagnosing a regression. It covers cache-phase
pilots, timing boundaries, existing invocation evidence, and failed attempts.

### 4. Profile broad to narrow

Start with whole-program evidence, then add the profile that tests the leading
hypothesis:

- CPU or wall-clock call graph and flame graph
- off-CPU or scheduler time
- allocation count, retained memory, heap growth, or GC
- lock contention and critical-section duration
- I/O, syscall, network, queue, retry, and backpressure data
- cache misses, branch misses, memory bandwidth, instruction footprint, and
  context switches

Use `pprof` for supported runtimes and `perf` for Linux CPU and hardware-counter
detail, but follow the repository's established profiler first. Verify that
symbols, sampling frequency, build mode, and workload make the profile useful.

For a distributed system, also map time and work across stages, queues, fan-out,
retries, serialization, payload sizes, and remote dependencies. Abseil's source
page mainly covers a single binary, so do not force a local CPU explanation onto
a distributed latency problem.

When the CPU profile is flat, use the flat-profile playbook in the reference.

### 5. State and rank hypotheses

Write each candidate in this form:

```text
Observation -> suspected mechanism -> proposed change -> predicted metric or
counter movement -> correctness and tradeoff risks -> validation experiment
```

Rank candidates by expected system impact, confidence, implementation cost, and
reversibility. Prefer, roughly:

1. eliminate work or improve the algorithm
2. batch work or change a boundary/API
3. improve representation and locality
4. reduce allocations, copies, parsing, and conversions
5. shorten or remove synchronization and I/O from hot paths
6. specialize common cases, defer, precompute, reuse, or cache
7. reduce code footprint and help the compiler
8. apply low-level SIMD, alignment, prefetch, or lock-free techniques only with
   profile and counter support

### 6. Implement narrowly

Make one coherent change that tests the hypothesis. Preserve unrelated work.
Keep fallbacks and uncommon cases correct. Avoid exposing a new public API or
configuration knob unless the measured benefit cannot be achieved within the
existing abstraction.

Add or retain a benchmark when it represents a stable property worth guarding.
Do not bake machine-specific timing thresholds into ordinary tests unless the
project has a controlled performance-test environment.

### 7. Validate causality and system impact

Run baseline and candidate under matched conditions. Check:

- the primary metric and uncertainty
- the predicted profile or counter movement
- correctness and output equivalence
- CPU, memory, allocations, I/O, and code-size guardrails
- multiple data sizes and relevant concurrency levels
- both common and adverse cases
- a higher-fidelity workload than the microbenchmark

Inspect generated code only for hot routines where the hypothesis depends on
compiler behavior. Re-run enough samples to distinguish the effect from noise,
alignment changes, thermal behavior, frequency scaling, or shared-host load.

If the candidate loses or the mechanism does not move as predicted, revise the
hypothesis or benchmark. Do not rationalize the result after the fact.

### 8. Report and operationalize

Report:

| Field | Required content |
| --- | --- |
| Objective | Metric, workload, and success threshold |
| Baseline | Revision, command, environment, sample count, and result |
| Evidence | Profile, trace, counters, or cost model with artifact paths |
| Mechanism | Why the observed cost occurs |
| Change | Narrow implementation and correctness implications |
| Result | Matched A/B effect with variance or confidence |
| Fidelity | Micro, component, end-to-end, or production level reached |
| Tradeoffs | CPU, memory, code size, API, complexity, and portability |
| Confidence | Proven facts, inferences, limitations, and next validation |

State negative results and unchanged metrics. Keep benchmark and profile
artifacts local or untracked unless the user asks to publish them.
