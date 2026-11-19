# 18. Performance Analysis and Observability

Systems performance optimization is an empirical engineering discipline. Intuition about why a program is slow is routinely wrong on modern out-of-order superscalar processors with multi-level caches, hardware prefetchers, and complex kernel I/O stacks. Rigorous diagnosis follows a closed scientific loop: characterize which physical resource bounds throughput or latency (CPU pipeline, memory hierarchy, lock contention, storage, or network), instrument the live system with low-overhead observability tools, hypothesize a single structural change, and verify the improvement under controlled statistical measurements.

## 18.1 The Empirical Method and the Memory Latency Hierarchy

Performance triage begins by classifying whether a workload is **on-CPU** (compute-bound or stalled on cache/TLB misses while holding a core) or **off-CPU** (blocked in kernel wait queues awaiting disk I/O, network packets, or contended mutexes).

When a workload runs on-CPU, the dominant performance cliff on modern hardware is the three-order-of-magnitude latency gap across the memory hierarchy (Figure 18-1):
- **CPU Registers (~0.3 ns, 1 cycle):** Private operand storage inside the execution pipeline.
- **L1 Cache (32 to 64 KiB per core, ~1 ns, 3 to 4 cycles):** Split instruction and data caches; accessed virtually in parallel with the L1 TLB.
- **L2 Cache (256 KiB to 4 MiB per core, ~3 to 5 ns, 10 to 14 cycles):** Unified per-core cache absorbing L1 capacity misses.
- **L3 / System-Level Cache (8 to 128 MiB shared, ~12 to 20 ns, 35 to 55 cycles):** Shared across cores; last stop before crossing the memory controller to off-chip DRAM.
- **Main DRAM (~60 to 100 ns, 200 to 300 cycles):** Hundreds of execution slots can stall inside the core's Reorder Buffer while a single pointer-chasing load waits for DRAM.

Sequential scans mask much of DRAM latency because the CPU's **hardware stride prefetcher** detects regular address increments and fetches future 64-byte cache lines into L1/L2 ahead of the instruction stream. Listings 18-1 and 18-2 isolate raw cache-level capacity cliffs by striding through progressively larger working sets (from 4 KiB up to 64 MiB) in 64-byte steps: as soon as the working set exceeds L1, L2, and then L3 capacity, measured nanoseconds per access climb sharply in visible plateaus.

<figure>
<img src="figures/ch18_pyramid.svg" alt="The memory hierarchy pyramid: registers and caches at the top, DRAM, SSD, and network below"/>
</figure>

**Listing 18-1. Reading a buffer with a stride of 64 bytes (C++20).**

```cpp
{{#include ../code/ch18/cache_bench.cpp}}
```

**Output 18-1. One run on the verification machine.**

```text
{{#include ../code/out/ch18_cache_bench.out}}
```

**Listing 18-2. The same program in Rust.**

```rust
{{#include ../code/ch18/cache_bench.rs}}
```

**Output 18-2.**

```text
{{#include ../code/out/ch18_cache_bench_rs.out}}
```

## 18.2 Observability: Hardware PMU Counters, Profilers, Tracers, and Flame Graphs

Understanding *how* observability tools collect data prevents misinterpreting their output or distorting the system under measurement.

### 18.2.1 The Hardware Performance Monitoring Unit (PMU)

Every modern x86-64 and ARM64 core contains a dedicated **Performance Monitoring Unit (PMU)**: a set of silicon hardware event counters that increment in parallel with execution at zero software cost. Tools such as Linux `perf stat` program these counters to measure exact microarchitectural events:
- **`cycles` and `instructions` (IPC = Instructions Per Cycle):** A modern superscalar core can retire 4 to 8 instructions per cycle. Observing an IPC of `0.3` on a supposedly CPU-bound loop immediately reveals that the core is not computing, but rather stalling on L3 cache misses, branch mispredictions, or atomic lock bus traffic.
- **`LLC-load-misses` and `dTLB-load-misses`:** Quantify whether stalls stem from working-set overflow out of the Last-Level Cache or TLB reach exhaustion (addressable with 2 MiB huge pages, Chapter 7).

### 18.2.2 Sampling Profilers versus Event Tracers

- **Sampling Profilers (`perf record`, macOS `sample` / Instruments):** Program the core's PMU counter to overflow every `N` cycles (or every 1 ms via a timer) and raise a Non-Maskable Interrupt (NMI). Inside the interrupt handler, the kernel records the interrupted instruction pointer (`RIP`/`PC`) and walks the Frame Pointer chain (`RBP`/`x29`, Chapter 2) to capture the full call stack. Because sampling wakes only ~1,000 times per second, runtime overhead stays below 1 to 2%, making sampling safe in live production clusters.
- **Event Tracers (`strace`, `dtrace`, `eBPF` / `bpftrace`):** Record *every* discrete occurrence of a selected event (such as every `open`, `read`, or `futex` system call with exact arguments, return value, and duration). Legacy `strace` attaches via `ptrace(2)`, pausing the traced process twice per system call (on entry and exit) and imposing 10x to 100x slowdowns on syscall-heavy servers. Modern **eBPF** avoids user-space context switches by running verified bytecode directly inside Ring 0 tracepoints and aggregating latency histograms in kernel maps, cutting tracing overhead to a few percent.
- **Flame Graphs:** Aggregate thousands of profiler stack samples into a single visual hierarchy. Two reading rules are critical:
  1. **The Y-axis is call-stack depth** (entry point `main()` at the bottom, active leaf function on-CPU at the top).
  2. **The X-axis is alphabetical proportion of total samples, NOT chronological time.** A wide plateau at the top of a flame graph indicates a leaf function consuming a large fraction of total CPU cycles; narrow spikes indicate brief functions.

## 18.3 Statistical Rigor and Measurement Pitfalls

Reporting a single arithmetic mean hides the exact latency spikes that break production service-level objectives (SLOs). Consider a web gateway that fans out one user request to 100 backend shards in parallel and waits for the slowest shard to respond. Even if each individual shard responds in 2 ms on average and has a **p99** (99th percentile) latency of 50 ms (meaning 99% of calls are fast), the probability that *at least one* of the 100 parallel shard calls hits the slow 1% tail is `1 - 0.99^100 = 63.4%`. In distributed fan-out architectures, **tail latency (`p99` and `p99.9`) becomes the common case**.

Reliable systems benchmarking must therefore report full latency distributions (`p50`, `p95`, `p99`, `p99.9`) and guard against four classic measurement traps:
1. **Unoptimized builds and dead-code elimination:** Benchmarking debug binaries measures compiler boilerplate rather than hardware limits; conversely, under `-O2`/`-O3`, compilers delete loops whose results are never observed unless outputs are consumed (as in Listing 18-1's checksum print) or fenced with `std::hint::black_box`.
2. **Cold-start bias:** The first iteration of a benchmark suffers minor page faults, cold instruction/data caches, cold TLBs, and low CPU turbo clocks. Always separate warm-up iterations from measured trials.
3. **Coordinated omission:** When a single-threaded load generator waits for one slow response before sending the next request, it pauses during server stalls and fails to record the queuing delay that real open-loop users experience.
4. **Power-management and frequency scaling noise:** Modern laptops and servers dynamically throttle CPU frequency (`Turbo Boost`, thermal throttling) and migrate threads across performance (P) and efficiency (E) cores. Pin benchmark threads when isolating microarchitectural costs, and run multiple independent trials to verify low variance.
