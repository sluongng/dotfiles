# Abseil Performance Playbook

Use this reference after establishing a baseline and profile. It distills the
technique families in Abseil's [Performance
Hints](https://abseil.io/fast/hints.html), last updated there on 2025-12-16,
into a language-neutral checklist. The source focuses on a single binary and
uses many C++ examples; translate the mechanisms rather than copying types or
container choices mechanically.

## Contents

- [Technique selection](#technique-selection)
- [Flat-profile playbook](#flat-profile-playbook)
- [Microbenchmark integrity](#microbenchmark-integrity)
- [Profiles and counters](#profiles-and-counters)
- [Technique-specific cautions](#technique-specific-cautions)
- [Source map](#source-map)

## Technique selection

### Algorithm and structure

Check first for:

- asymptotic improvements and performance cliffs
- repeated incremental work that can be replaced by bulk construction
- top-level loops that invoke checks or setup once per item
- overly general operations where a simpler operation matches the requirement
- representations that cause unnecessary traversal or indirection

Prefer structural wins because they often dominate local instruction changes.

### API and boundary design

Consider:

- bulk operations that amortize locking, calls, parsing, validation, or setup
- view or slice arguments when ownership is not transferred
- caller-owned scratch storage or precomputed arguments
- validating malformed input once at the module boundary
- narrow, deep modules that permit internal representation changes
- externally synchronized types when universal internal synchronization would
  make every caller pay; use internal synchronization when most callers need it
  and the implementation may later be sharded

Do not add API complexity until callers and profiles show the boundary is
material.

### Representation and locality

Inspect cache and memory footprint, not only nominal operation count:

- reorder fields to reduce padding and cluster fields used together
- separate cold data and hot mutable data from hot read-only data
- use the smallest safe scalar or index representation
- replace pointer-rich nodes with indices into contiguous storage
- store elements in flat, batched, chunked, or inlined layouts
- use arenas for related lifetimes and locality, with a measured initial size
- replace small-domain maps and sets with arrays, vectors, or bitsets
- challenge nested maps; either a compound key or a two-level layout can win
  depending on key duplication and access locality

Measure packing and alignment changes. Smaller is not automatically faster if
access becomes expensive or false sharing grows.

### Allocations and copies

Look for:

- heap allocation in per-item or per-request paths
- default-constructed objects overwritten immediately
- container growth without `reserve` or an equivalent capacity plan
- `push` loops where one resize plus indexed fill is safe
- values passed, returned, or captured by copy when a view, move, or reference
  is valid
- temporary buffers and objects that can be reused across iterations
- serialization objects recreated inside loops

Track both allocation bytes and allocation count. Reducing allocations may also
reduce cache misses and GC work.

### Avoid unnecessary work

Consider:

- fast paths for common, simple cases
- precomputing invariant properties once
- moving invariant work outside loops
- deferring work until its result is needed
- computing rarely requested stats on demand
- specialized implementations for proven hot call sites
- caching repeated expensive work when keys, invalidation, lifetime, and memory
  bounds are correct
- removing or sampling hot-path stats and logging
- avoiding repeated parsing, formatting, validation, conversions, and virtual
  calls

Account for cache invalidation, memory growth, and correctness before adding a
cache. Prefer work elimination over making unnecessary work faster.

### Compiler and code footprint

Large generated code can increase compile and link time, binary size, memory,
instruction-cache pressure, and branch-predictor pressure. Check:

- slow paths or error formatting duplicated by inlining
- large functions in headers
- template parameters that can be runtime arguments
- code duplicated across template instantiations
- repeated container operations that expand into large code sequences
- abstractions that block vectorization or force conservative alias analysis

Inspect annotated disassembly for a measured hot routine. Do not lower
abstraction merely because the compiler might do better.

### Parallelism and synchronization

Consider:

- batching before parallel dispatch
- whether spare CPU, memory bandwidth, and downstream capacity exist
- amortizing lock acquisition without lengthening contention
- moving RPCs, files, allocation, formatting, and expensive destruction outside
  critical sections
- sharding only when no cross-shard invariant is required
- isolating independently mutated fields to address measured false sharing
- buffering pipeline channels where rendezvous is not the goal
- processing tiny work inline to avoid dispatch and context-switch overhead
- SIMD for repeated independent operations
- high-level lock-free abstractions for read-heavy cases only after conventional
  locking is shown to be the cost

Measure throughput, latency, CPU, fairness, contention, and saturation together.
Parallelism can reduce latency while increasing total resource use or making a
memory-bound workload slower.

### Serialization and domain types

Do not use a wire or persistence representation as the default hot in-memory
representation. For Protocol Buffers and analogous formats, consider:

- native compact structures for computation-heavy inner loops
- reserving repeated fields
- parsing only required fields
- avoiding text validation when the schema and semantics permit bytes
- reusing message objects across iterations
- separating transport/storage types from compute types when conversion cost is
  lower than repeated indirect access

Use language-specific container substitutions only after verifying semantic
requirements such as ordering, pointer stability, iteration behavior, and
memory lifetime.

## Flat-profile playbook

When no single CPU leaf dominates:

1. Inspect loops and control flow high in flame graphs.
2. Look for structural work repeated across many small callees.
3. Replace overly general operations with requirement-specific ones.
4. Collect allocation-count and retained-memory profiles.
5. Collect lock-contention, off-CPU, cache-miss, branch-miss, and bandwidth data.
6. Check whether contention suppresses CPU utilization.
7. Accumulate independently verified small improvements only when the benchmark
   is stable enough to resolve them.

Do not conclude that a flat profile has no opportunity. It may indicate broadly
distributed overhead or that the wrong resource is being profiled.

## Microbenchmark integrity

Use microbenchmarks to answer a narrow question quickly. Validate the answer at
increasing fidelity. Abseil's [microbenchmark pitfalls
guide](https://abseil.io/fast/39) and [construction
guide](https://abseil.io/fast/75) motivate these checks:

- prevent dead-code elimination and constant folding without distorting the hot
  loop excessively
- verify results for correctness
- keep setup, random generation, logging, and fixture construction outside the
  timed region when they are not part of the real operation
- report items and bytes correctly for batched iterations
- distinguish throughput from dependency-chain latency
- use representative sizes, distributions, paths, cache states, and working
  sets
- test meaningful boundaries such as cache-hit and cache-miss behavior
- include steady-state and dynamic or bursty behavior when production has both
- use fixed, recorded seeds for reproduction, but do not let one seed define the
  whole conclusion
- inspect disassembly when compiler elimination, speculation, aliasing, or
  vectorization determines the result
- repeat runs and watch for code, branch, stack, and data alignment sensitivity
- control or record frequency scaling, thermal state, SMT, preemption, NUMA, and
  shared-resource interference
- check instruction footprint and downstream application performance; a faster
  isolated routine can make a larger program slower

When a microbenchmark win disappears in a component test, repair the benchmark
or causal model before proceeding.

## Profiles and counters

Match the measurement to the hypothesis:

| Hypothesis | Evidence to collect |
| --- | --- |
| CPU computation | CPU profile, annotated source/disassembly, cycles |
| Waiting or queueing | Wall/off-CPU profile, scheduler trace, queue depth |
| Allocation or GC | Allocation count/bytes, heap, GC pause and CPU |
| Locking | Contention profile, wait/hold time, blocked threads |
| Poor locality | Cache/TLB misses, bandwidth, working-set and layout data |
| Branch-heavy code | Branch misses and annotated hot instructions |
| Code footprint | Binary/symbol size, instruction misses, frontend stalls |
| I/O or RPC | Syscalls, bytes, latency distributions, fan-out and retries |
| False sharing | Cache-coherency evidence plus layout-sensitive A/B |

Use hardware counters as supporting evidence, not portable universal facts.
Counter names and semantics vary across CPUs. Abseil's [hardware counter
guide](https://abseil.io/fast/53) provides C++ benchmark context.

## Technique-specific cautions

- Bulk work can increase latency or memory for small requests.
- Inlined storage bloats every instance when the element or inline capacity is
  large.
- Arenas retain memory until arena reset and can mix incompatible lifetimes.
- Caches require bounded growth, correct keys, invalidation, and concurrency.
- Field packing can add decoding cost or unsafe under-alignment.
- Larger critical sections amortize lock calls but may increase contention.
- Sharding adds coordination and is invalid when operations need global state.
- False-sharing padding can materially enlarge objects.
- Lock-free code increases correctness and reclamation risk.
- Logging and stats removal reduces observability; measure and preserve the
  signals that justify their cost.
- Excessive inlining and specialization can trade local speed for instruction
  cache pressure and binary growth.

## Source map

- [Estimation](https://abseil.io/fast/hints.html#estimation)
- [Measurement](https://abseil.io/fast/hints.html#measurement)
- [API considerations](https://abseil.io/fast/hints.html#api-considerations)
- [Algorithmic improvements](https://abseil.io/fast/hints.html#algorithmic-improvements)
- [Better memory representation](https://abseil.io/fast/hints.html#better-memory-representation)
- [Reduce allocations](https://abseil.io/fast/hints.html#reduce-allocations)
- [Avoid unnecessary work](https://abseil.io/fast/hints.html#avoid-unnecessary-work)
- [Code size considerations](https://abseil.io/fast/hints.html#code-size-considerations)
- [Parallelization and synchronization](https://abseil.io/fast/hints.html#parallelization-and-synchronization)
- [Protocol Buffer advice](https://abseil.io/fast/hints.html#protocol-buffer-advice)
- [C++-specific advice](https://abseil.io/fast/hints.html#c-specific-advice)
