# 18. Performance and Observability

Performance work is measurement with a method: find the resource that
limits the system, confirm it with an observation, change one thing,
and measure again. This chapter closes the book with the method, the
one experiment that makes the memory hierarchy tangible, and the
tools that turn a running system into observations.

<div class="callout glance">
<span class="label">At a glance</span>

- The method: hypothesize the bottleneck, observe it, change one
  variable, re-measure.
- The memory hierarchy is the first hypothesis for CPU-bound work;
  one sweep across buffer sizes shows its cliffs.
- Profilers sample; tracers record; the two answer different
  questions.
- A performance number without its distribution is a guess.

</div>

## 18.1 The method

Begin with the utilization of the four resources: CPU, memory
bandwidth, storage, network. If the CPU is saturated, the program is
compute-bound; if the CPU is idle while requests wait, it is blocked
on something else. The distinction decides everything downstream, and
it is made with two numbers: utilization and latency.

Compute-bound work then meets the hierarchy of Figure 18-1: the
processor's arithmetic is rarely the limit; the distance to the data
is. Cache misses, page walks, remote NUMA accesses, and the
synchronization of Chapters 6 and 17 each leave a signature in the
latency of memory operations, and the next section measures the
simplest one directly.

<figure>
<img src="diagrams/ch18_pyramid.svg" alt="The memory hierarchy pyramid: registers and caches at the top, DRAM, SSD, and network below"/>
</figure>

<div class="callout keyidea">
<span class="label">Key idea</span>

Optimize the bottleneck, not the symptom. A profile that shows 90
percent of time in one function tells you where; a measurement of
cache misses tells you why. The two questions are different, and
both need answers before any change.

</div>

## 18.2 The hierarchy, measured

One program makes the whole pyramid visible. It allocates a buffer,
then walks it with a fixed stride, touching one cache line's worth of
bytes per access, and reports nanoseconds per access. Each doubling
of the buffer pushes the working set past one more level — L1, L2,
L3, DRAM — and each crossing appears as a step.

**Listing 18-1. Stride 64, sixteen million accesses per size (C++20).**

```cpp
{{#include ../code/ch18/cache_bench.cpp}}
```

**Output 18-1. Four distinct plateaus; the machine's hierarchy, in numbers.**

```text
{{#include ../code/out/ch18_cache_bench.out}}
```

**Listing 18-2. The same walk in Rust.**

```rust
{{#include ../code/ch18/cache_bench.rs}}
```

**Output 18-2.**

```text
{{#include ../code/out/ch18_cache_bench_rs.out}}
```

The shape is the result, not the specific numbers. Below 256 KiB,
every access hits L1 or L2: under one nanosecond. At 4 MiB the
working set exceeds the fast caches and each access pays several
times more; beyond 16 MiB it lives in DRAM and the cost flattens
near four nanoseconds. Another machine prints different numbers on
the same steps; a machine without the steps is not a different
machine — it is a different stride or a broken measurement.

Two refinements make the experiment honest, and both generalize.
The warm-up pass touches every line once before timing, so page
faults from Chapter 7 do not contaminate the measurement. The
checksum is printed and, in the C++ version, accumulated — without
it, an optimizing compiler may delete the loop whose timing is the
entire point.

<div class="callout experiment">
<span class="label">Experiment</span>

Change the stride from 64 to one byte. The steps largely disappear:
sequential access lets the hardware prefetcher hide DRAM latency.
Then change it to a large prime. The steps return, steeper. The
stride is the difference between a program the hardware can predict
and one it cannot — which is the entire subject of cache-aware
engineering.

</div>

## 18.3 Tools: sample, trace, attribute

Three tool classes convert a running system into evidence.

**Sampling profilers** interrupt the process at a fixed frequency
and record the instruction pointer each time. Time spent in a
function is proportional to the samples that land in it. Sampling is
cheap, honest about where time goes, and blind to why — two
functions can have identical sample counts for opposite reasons.
Linux's `perf` and macOS's Instruments are the standard tools; both
can attribute samples to *cache misses* and *stalls* rather than
instructions, which is the measurement the previous section made by
hand.

**Tracers** record events as they happen — system calls, signals,
context switches, page faults — with arguments and return values.
Linux's `strace` and macOS's `dtruss` trace system calls; they
answer "what is this program asking the kernel for" precisely, at a
cost that distorts timing. Use a tracer for behavior, a profiler for
time.

**Flame graphs** render a profiler's samples as stacked rectangles:
each function's width is its share of time, its height its position
in the call stack. One glance localizes the bottleneck to a path;
the figure is a profiler's output, rearranged for the human visual
system, and it is the standard artifact attached to a performance
investigation.

One discipline underlies all three: measure the **distribution**,
not the average. A service whose requests average 2 ms and whose
99th percentile is 900 ms is a 900 ms service for one request in a
hundred — and in a data center, that tail is the experience. Every
serious measurement reports percentiles; every serious optimization
moves the tail, not the mean.

<div class="callout caution">
<span class="label">Watch out</span>

Two measurement errors invalidate more performance work than any
algorithm choice. Measuring with debug builds or without warm-up —
the first run pays every one-time cost and reports it as steady
state. And optimizing from a profile taken under a different load —
the bottleneck moves with the workload, and last month's profile
describes last month's system.

</div>

<div class="callout summary">
<span class="label">Summary</span>

- Find the saturated resource first; CPU-bound and I/O-bound lead
  to different investigations.
- One stride-64 sweep reveals the machine's cache and DRAM
  plateaus; the shape, not the numbers, is the lesson.
- Samplers measure time, tracers record behavior, flame graphs
  localize paths.
- Report distributions and percentiles; the tail is the system's
  observable behavior.
- The method applies to every chapter in this book: hypothesize,
  observe, change one variable, measure again.

</div>
