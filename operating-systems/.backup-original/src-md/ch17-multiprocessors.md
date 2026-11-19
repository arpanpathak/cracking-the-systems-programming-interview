# 17. Multiprocessor Systems and Accelerators

Every mechanism so far assumed, for simplicity, a machine with one
kind of core and one pool of memory. Data center machines break both
assumptions: many cores in several sockets, memory with a distance,
and accelerators — GPUs and machine-learning silicon — that compute
beside the CPU rather than under it. This chapter corrects the
assumptions, measures the cache-line effect that survives at every
scale, and describes how the operating system orchestrates the
heterogeneous whole.

<div class="callout glance">
<span class="label">At a glance</span>

- Sockets hold cores and their own memory; local access is fast,
  remote access crosses an interconnect.
- Cache coherence makes shared memory correct; false sharing makes
  it slow — measurably, and fixably with padding.
- Accelerators are peer devices with their own memory and execution;
  the operating system's job is scheduling, memory movement, and
  fault isolation between them.

</div>

## 17.1 Sockets, NUMA, and distance

A large server is not one processor; it is several **sockets**, each
a package of cores with its own memory controller and its own DRAM.
A core can address all of the machine's memory, but not at one
speed: its own socket's memory answers directly, while the other
socket's memory answers across an interconnect, slower by a factor
that grows with the machine. The architecture is **NUMA** —
non-uniform memory access — and Figure 17-1 draws it.

<figure>
<img src="diagrams/ch17_numa.svg" alt="Two sockets, each with cores and local DRAM, connected by an interconnect"/>
</figure>

Two operating system mechanisms respond to the distance. The
scheduler prefers to run a thread on cores near its memory — the
affinity hints of Chapter 5, now with a distance attached. The
allocator places pages near the core that first writes them —
first-touch placement, so a thread that allocates and initializes
its own working set keeps that set local. Both mechanisms are
heuristics with the same goal: make the common access local.

The hardware's side of the bargain is **cache coherence**: all
cores, in all sockets, observe one consistent order of reads and
writes to each address. The protocol moves cache lines between
cores' caches on demand — which is why Chapter 2's 64-byte line
still governs performance, and why the next section's measurement
applies unchanged on the largest machines.

<div class="callout keyidea">
<span class="label">Key idea</span>

NUMA turns memory placement into a scheduling problem. First touch
and affinity keep data near its core; coherence keeps the sharing
correct; the cache line remains the unit whose movement costs
everything.

</div>

## 17.2 False sharing, measured

Two threads, two independent counters, one cache line. Each thread
increments its own counter, so no logical sharing exists — yet every
write invalidates the other core's copy of the *line*, the line
bounces between caches, and both threads run far below their speed.
The effect has a name, **false sharing**, and a diagram, Figure 17-2.

<figure>
<img src="diagrams/ch17_false_sharing.svg" alt="Two counters in one cache line bouncing between cores, versus two padded counters in separate lines"/>
</figure>

**Listing 17-1. One line versus two, measured (C++20).**

```cpp
{{#include ../code/ch17/false_sharing.cpp}}
```

**Output 17-1. Nearly five times slower, from layout alone.**

```text
{{#include ../code/out/ch17_false_sharing.out}}
```

**Listing 17-2. The same experiment with Rust's atomics.**

```rust
{{#include ../code/ch17/false_sharing.rs}}
```

**Output 17-2.**

```text
{{#include ../code/out/ch17_false_sharing_rs.out}}
```

The experiment changes nothing logical — the same increments, the
same totals — only the placement of the second counter, 64 bytes
away. The four-to-five-fold gap is the price of the line bouncing.
The fix generalizes: any hot, independently written field belongs in
its own line, and the languages make the intent expressible —
`alignas(64)` in C++, `#[repr(C, align(64))]` in Rust. The pattern
recurs in every high-throughput system: per-thread counters padded,
lock fields separated from the data they guard, queue heads and
tails in different lines.

## 17.3 Accelerators beside the CPU

An accelerator — a GPU, a machine-learning ASIC — is a peer
processor with its own memory, its own execution model, and its own
place in the machine of Figure 2-1: on the PCIe bus, like any
device, but executing programs rather than moving data. Three
responsibilities follow for the operating system.

**Scheduling.** The accelerator runs one workload at a time or a
few concurrently; the kernel and its user-space runtime queue
workloads, time-slice long ones, and preempt where the hardware
allows — the scheduler of Chapter 5, with a device as the resource.

**Memory movement.** CPU and accelerator memories are separate
address spaces. Data crosses the PCIe bus — or a faster link, such
as CXL or NVLink — under the kernel's DMA machinery from Chapter 2,
and the runtime decides what to move, when, and whether to overlap
the transfer with computation. The discipline is the event loop's:
launch a transfer, do other work, be woken by the completion
interrupt.

**Isolation and faults.** Several tenants share one accelerator. The
operating system fences each tenant's memory, translates the
accelerator's faults back into the owning process's signals, and
resets the device's state between tenants — the protection work of
Chapters 1 and 7, replayed against a device that does not share the
CPU's page tables by default.

The programming model on top is a chapter of its own, and the
reference book this one draws on — Kirk, Hwu, and El Hajj's
*Programming Massively Parallel Processors* — develops it
completely. The systems-engineer level is the three
responsibilities above: the accelerator is a scheduled resource with
distant memory and faults to translate, and everything this book
said about scheduling, DMA, and isolation applies to it with new
latency numbers.

<div class="callout caution">
<span class="label">Watch out</span>

Two placement errors dominate accelerator performance, and both are
invisible in the code's logic. Copying data across the bus per small
operation instead of per batch — the Chapter 9 lesson, with
microseconds instead of nanoseconds. And pinning memory that the
kernel may page out mid-transfer — accelerator transfers read
physical addresses, so movable memory must be pinned or copied, or
the transfer faults on a page that is no longer there.

</div>

<div class="callout summary">
<span class="label">Summary</span>

- NUMA makes memory distance a scheduling input: first-touch
  placement and affinity keep data local.
- False sharing costs a four-to-five-fold slowdown with no logical
  change; padding hot fields is the fix.
- Accelerators are scheduled peer processors with separate memory;
  the kernel moves data, fences tenants, and translates faults.
- Batching transfers and pinning pages are the two habits that
  separate working accelerator paths from demos.
- Chapter 18 supplies the measurement discipline for all of this:
  what to observe, what the numbers mean, and how to read a
  profile.

</div>
