# 17. Multiprocessor Systems and Accelerators

So far, we have treated the cores of a machine as equal and its memory as
one uniform pool. Large servers do not fit this model. They contain
several processor packages, each with memory of its own, and many of them
also contain accelerators such as GPUs, which compute alongside the CPU.

In this chapter, we first describe machines in which the time of a memory
access depends on the location of the memory. We then measure false
sharing, the cache-line effect that we introduced in Chapter 2, and remove
it with padding. Finally, we outline what an operating system does for an
accelerator.

<div class="callout glance">
<span class="label">This chapter covers</span>

- sockets and non-uniform memory access (NUMA)
- affinity and first-touch page placement
- cache coherence
- false sharing, with a measurement and a fix
- scheduling, data transfer, and isolation for accelerators

</div>

## 17.1 Sockets, NUMA, and distance

A large server has several **sockets**. A socket holds one processor
package, which contains a number of cores and a memory controller that is
connected to its own DRAM. Any core can access any memory of the machine,
but access times differ. A core reaches the memory of its own socket
directly. To reach the memory of another socket, the request must travel
over an *interconnect* between the sockets, which takes longer. This
arrangement is called **non-uniform memory access** (NUMA). Figure 17-1
shows a machine with two sockets.

<figure>
<img src="figures/ch17_numa.svg" alt="Two sockets, each with cores and local DRAM, connected by an interconnect"/>
</figure>

An operating system uses two techniques to keep memory accesses local.
First, the scheduler prefers to run a thread on a core of the socket that
holds the memory of the thread. This extends the affinity of Chapter 5.
Second, when a thread writes to a new page for the first time, the kernel
allocates the frame from the socket on which the thread is running. This
policy is called **first-touch placement**. Under it, a thread that
allocates and initializes its own data receives that data in local memory.
In contrast, if one thread initializes a large array and other threads on
another socket use it later, all of their accesses are remote.

The hardware, for its part, ensures that all cores see a consistent
content of memory, although each core has its own caches. This property is
called **cache coherence**. To maintain it, the hardware transfers cache
lines between the caches of different cores. When a core writes to a line,
it first obtains exclusive ownership of the line, and the copies in other
caches become invalid. These transfers take time, and they cause the
effect that we measure in Section 17.2.

<div class="callout keyidea">
<span class="label">Key idea</span>

On a NUMA machine, the location of data affects the speed of a program.
The kernel places a page on the socket of the thread that first writes to
it, and the scheduler keeps threads close to their memory.

</div>

## 17.2 Measuring false sharing

Suppose that two threads each increment a counter of their own. The
threads share no data, so we would expect them to run at full speed. If
both counters lie in the same 64-byte cache line, however, they do not.
Each write by one thread makes the copy of the line in the cache of the
other core invalid, and the line travels back and forth between the two
cores. This effect is called **false sharing**, because the threads share
a cache line without sharing data. Figure 17-2 shows the two layouts that
we compare.

<figure>
<img src="figures/ch17_false_sharing.svg" alt="Two counters in one cache line bouncing between cores, versus two padded counters in separate lines"/>
</figure>

Listing 17-1 runs two threads that increment two counters. It measures
the running time once with the counters next to each other and once with
each counter aligned to a 64-byte boundary.

**Listing 17-1. Two counters in one cache line and in two (C++20).**

```cpp
{{#include ../code/ch17/false_sharing.cpp}}
```

**Output 17-1. One run on the verification machine.**

```text
{{#include ../code/out/ch17_false_sharing.out}}
```

**Listing 17-2. The same experiment in Rust, with atomic counters.**

```rust
{{#include ../code/ch17/false_sharing.rs}}
```

**Output 17-2.**

```text
{{#include ../code/out/ch17_false_sharing_rs.out}}
```

With the counters in one line, the C++ program takes 1,620 ms. With the
counters in separate lines, it takes 346 ms, so the first layout is 4.68
times slower. The Rust program shows a ratio of 4.63. Both layouts perform
the same 80,000,000 increments, and only the placement of the second
counter differs.

The remedy is to give each variable that is written often by one thread a
cache line of its own. In C++, we request this with `alignas(64)`, and in
Rust with `#[repr(C, align(64))]`. Programs that need high throughput apply
this technique to per-thread counters, to locks, and to the head and tail
indices of queues.

## 17.3 Accelerators

An **accelerator** is a second processor that is specialized for one kind
of computation. Graphics processing units (GPUs) and chips designed for
machine learning are examples. In the machine model of Figure 2-1, an
accelerator is a device on the PCIe bus. Unlike a disk or a network card,
it executes programs, and it has memory of its own. The operating system
and the driver of the accelerator have three tasks.

**Scheduling.** An accelerator can run one workload or a small number of
workloads at a time. The driver and its user-space runtime keep a queue of
waiting workloads and switch between long-running ones where the hardware
allows it. This task is the scheduling problem of Chapter 5, applied to a
device.

**Data transfer.** The memory of an accelerator is separate from main
memory. Before a computation, its input must be copied to the accelerator,
and afterward the results must be copied back. These transfers use DMA
over PCIe, or over a faster link such as NVLink. Since a transfer takes
time, a program usually starts one, continues with other work, and is
notified by an interrupt when the transfer has completed.

**Isolation.** Several processes may use one accelerator. The driver must
keep the memory of each process on the device separate from that of the
others, and it must report a fault on the device to the process that
caused it. These are the protection tasks of Chapters 1 and 7. They need a
separate implementation, because an accelerator does not use the page
tables of the CPU.

How to write programs for accelerators is a subject of its own. We
recommend *Programming Massively Parallel Processors* by Kirk, Hwu, and
El Hajj for it.

<div class="callout caution">
<span class="label">Watch out</span>

Two mistakes often limit the performance of programs that use
accelerators.

- Transferring data in many small pieces. Every transfer has a fixed cost
  of microseconds, so data should be sent in large batches, for the same
  reason that Chapter 9 gave for system calls.
- Transferring from memory that is not pinned. A device reads physical
  addresses, so the kernel must not move or page out a buffer during a
  transfer. A buffer that is not *pinned*, that is, locked at its physical
  location, must first be copied into one that is, which costs additional
  time.

</div>

<div class="callout summary">
<span class="label">Summary</span>

- On a NUMA machine, each socket has its own memory, and an access to the
  memory of another socket is slower. First-touch placement and affinity
  keep data and threads on the same socket.
- Cache coherence transfers cache lines between cores. Two threads that
  write to one line slow each other down.
- In our measurement, false sharing made a program 4.7 times slower.
  Aligning each counter to 64 bytes removed the effect.
- For an accelerator, the operating system schedules workloads, transfers
  data, and isolates the processes that use the device.

In Chapter 18, we describe a method for measuring performance and repeat
the measurement of the memory hierarchy.

</div>
