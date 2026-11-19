# 18. Performance and Observability

Improving the performance of a system begins with measurement. An engineer
who changes code without first measuring often speeds up a part of the
system that was not slow. The usual method is to find the resource that
limits the system, confirm this with an observation, change one thing, and
measure again.

In this chapter, we describe that method. We then run an experiment that
shows the levels of the memory hierarchy as differences in access time.
Finally, we introduce profilers, tracers, and flame graphs, and we explain
why a measurement should report percentiles as well as an average.

<div class="callout glance">
<span class="label">This chapter covers</span>

- a method for finding a bottleneck
- the memory hierarchy, from registers to storage
- access time as a function of buffer size
- sampling profilers and tracers
- flame graphs
- averages, distributions, and percentiles

</div>

## 18.1 The method

A program uses four kinds of resources: CPU time, memory, storage, and
network. The first step of an investigation is to find out which of them
limits the program. If the CPU is fully used, the program is
*compute-bound*. If the CPU is mostly idle while requests wait, the
program is blocked on something else, such as a disk, a network peer, or a
lock. Two measurements separate these cases: the utilization of each
resource and the latency of requests.

For a compute-bound program, the next question is where the time goes. The
arithmetic itself is seldom the limit. More often, the program waits for
data to arrive from memory. Figure 18-1 shows the levels of the memory
hierarchy with their approximate access times. A read that is served by
the L1 cache takes about 1 ns, and a read from DRAM takes 60 to 100 ns.
Cache misses, page table walks, accesses to remote NUMA memory, and
contention for cache lines all increase the time of memory operations.

<figure>
<img src="figures/ch18_pyramid.svg" alt="The memory hierarchy pyramid: registers and caches at the top, DRAM, SSD, and network below"/>
</figure>

<div class="callout keyidea">
<span class="label">Key idea</span>

Before changing a program, we need to know where it spends its time and
why. A profile answers the first question by naming the function, and a
count of events such as cache misses helps to answer the second.

</div>

## 18.2 Measuring the hierarchy

Listing 18-1 makes the memory hierarchy visible. The program allocates a
buffer and reads one byte from every 64th position, so that each access
uses a different cache line. When it reaches the end of the buffer, it
starts again from the beginning, until it has performed 16,000,000
accesses. It prints the average time of one access and repeats the
measurement for buffers from 16 KiB to 256 MiB.

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

The access times fall into three groups. For buffers up to 256 KiB, one
access takes about 0.8 ns, because the whole buffer fits in the L1 and L2
caches. For 1 MiB and 4 MiB, the time roughly doubles to between 1.6 and
1.8 ns, since most of the buffer now lies in the L3 cache. From 16 MiB
upward, the buffer is larger than all caches, and one access takes about
4 ns.

A time of 4 ns is far below the 60 to 100 ns of a single DRAM access. It
is so low because our program reads its buffer in order. A processor
detects such a regular pattern and loads subsequent lines from DRAM before
the program asks for them. This mechanism is called *hardware
prefetching*, and with it a program reads from DRAM at close to the rate
at which DRAM can deliver data. Other machines produce different numbers,
but on each of them access time increases in steps at that machine's cache
sizes.

Two details of Listing 18-1 keep its measurement valid, and both apply to
benchmarks in general. First, our program writes to every cache line of
its buffer before it starts the clock. During these writes, the kernel
allocates all pages of that buffer, so page faults, as described in
Chapter 7, do not occur inside the timed loop. Second, the program adds up
every byte that it reads and prints their sum. If nothing used the loop's
result, an optimizing compiler could remove the loop, and we would measure
nothing.

<div class="callout experiment">
<span class="label">Experiment</span>

Replace the regular stride with a random position for each access. A
prefetcher can no longer predict which address comes next, and for a
buffer of 256 MiB each access then takes nearly as long as one DRAM
access. Comparing both runs shows how much a sequential read gains from
prefetching.

</div>

## 18.3 Tools: profilers, tracers, and flame graphs

Three kinds of tools show what a running program does.

A **sampling profiler** interrupts the program at regular intervals, for
example 1,000 times per second, and records which function is executing
at each interrupt. A function that accounts for 30 percent of the samples
uses about 30 percent of the CPU time. Sampling slows the program only
slightly. Two examples are `perf` on Linux and Instruments on macOS. Both
can also count hardware events such as cache misses and attribute them to
functions. A profile shows where the time is spent, but it does not by
itself show the cause.

A **tracer** records individual events with their arguments and results.
`strace` on Linux and `dtruss` on macOS record every system call that a
program makes. A trace shows exactly what a program requests from the
kernel and in which order. Tracing slows a program considerably, so the
times in a trace are not representative. In short, a tracer shows what a
program does, and a profiler shows how long it takes.

A **flame graph** is a picture of the samples of a profiler. Each function
is drawn as a rectangle whose width is proportional to its share of the
samples, and a called function is drawn above its caller. A wide rectangle
near the top of the graph marks a function in which the program spends
much of its time.

Whatever the tool, a measurement should report a distribution and not only
an average. Consider a service whose requests take 2 ms on average but
whose slowest 1 percent take 900 ms. The average suggests a fast service,
yet one request in a hundred takes almost a second. The value below which
99 percent of the measurements fall is called the *99th percentile*, and
in this example it is 900 ms. Reports on the latency of a service
therefore state percentiles, typically the 50th, 99th, and 99.9th.

<div class="callout caution">
<span class="label">Watch out</span>

Two mistakes invalidate many performance measurements.

- Measuring a build without optimization, or measuring the first run. The
  first run includes one-time costs such as page faults and empty caches.
- Using a profile that was recorded under a different load. The
  bottleneck of a system depends on its workload, so a profile describes
  only the conditions under which it was recorded.

</div>

<div class="callout summary">
<span class="label">Summary</span>

- An investigation starts by finding the resource that limits the
  program: CPU, memory, storage, or network.
- In our measurement, one access took 0.8 ns in the L1 and L2 caches,
  about 1.7 ns in the L3 cache, and about 4 ns in DRAM with prefetching.
- A sampling profiler shows where a program spends its time. A tracer
  shows which events occur. A flame graph displays the samples of a
  profiler by call path.
- Latency should be reported with percentiles, because an average hides
  the slowest requests.

The method of this chapter applies to every topic of this book: state a
hypothesis, observe, change one thing, and measure again.

</div>
