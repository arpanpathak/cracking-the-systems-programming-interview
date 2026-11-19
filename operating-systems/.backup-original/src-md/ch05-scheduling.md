# 5. Scheduling

The machine has a few cores and many threads. The scheduler is the part
of the kernel that decides which thread runs on which core next, and the
decision repeats every few milliseconds, all day, across every machine.
The policy choices behind that decision — who goes first, who waits, and
what "fair" means — are this chapter's subject, computed by hand and then
by a simulation you can run.

<div class="callout glance">
<span class="label">At a glance</span>

- Metrics: turnaround (completion minus arrival) and wait (time spent
  ready but not running); they trade against each other.
- FCFS runs jobs in arrival order; SJF runs the shortest first; RR gives
  every job a fixed time slice in rotation.
- Real schedulers combine the ideas with priorities and multiple queues.

</div>

## 5.1 What the scheduler decides

A running thread occupies a core until one of three events: it finishes,
it blocks waiting for I/O or a lock, or a timer interrupt fires and its
time slice expires. On each event the scheduler consults the **ready
queue** — the set of threads that want a core — and dispatches one.
Figure 5-1 draws the three places a thread can be.

<figure>
<img src="diagrams/ch05_queues.svg" alt="The scheduler moves jobs between the ready queue, the CPU, and the wait queue"/>
</figure>

The mechanism is fixed; the policy is a choice. To compare policies,
measure three quantities for each job: **turnaround** — the time from
arrival to completion, which is what a user waiting for a result feels;
**wait** — the time spent ready but not running; and **response** — the
time from arrival to first running, which is what a user typing at a
terminal feels. No policy wins all three; each trades them differently.

## 5.2 Three policies

**First-Come, First-Served (FCFS)** runs jobs in arrival order, each to
completion. It is the simplest policy and the fairest in one narrow
sense: nobody overtakes anybody. Its flaw is the convoy: one long job
blocks every short job behind it, and average turnaround suffers.

**Shortest Job First (SJF)** runs the shortest job to completion first.
For a fixed set of jobs it minimizes average turnaround — a result worth
sitting with, because it says the optimal order is exactly the
counterintuitive one: let the small jobs cut the line. Its flaw is
practical: the scheduler must know each job's length in advance, which
real workloads do not announce.

**Round-Robin (RR)** gives every job the same time slice, or **quantum**,
in rotation; a job that does not finish returns to the back of the queue.
RR optimizes response — every job gets a turn within one full rotation —
at the cost of turnaround, because long jobs are repeatedly interrupted.
The quantum is the tuning knob: too large and RR degenerates toward FCFS;
too small and the machine spends its time switching.

Figure 5-2 runs all three policies on the same three jobs, A = 10, B = 5,
C = 5, all arriving at time 0.

<figure>
<img src="diagrams/ch05_gantt.svg" alt="Gantt charts for FCFS, SJF, and round-robin on jobs of length 10, 5, and 5"/>
</figure>

FCFS completes them at 10, 15, 20 — average turnaround 15. SJF completes
them at 5, 10, 20 — average turnaround 11.7. RR with quantum 5 completes
them at 20, 10, 15 — average turnaround 15 again, but every job first ran
within 5, and B and C finished while A was still working. The same three
jobs, three different answers, each defending a different metric.

## 5.3 The policies, simulated

The arithmetic is simple enough to check by hand, and the next listing
does exactly that in code. Three functions implement the three policies
against a small job table, and `main` prints the resulting schedules.

**Listing 5-1. FCFS, SJF, and RR computed inside a simulator (C++20).**

```cpp
{{#include ../code/ch05/sched_sim.cpp}}
```

**Output 5-1. The numbers match Figure 5-2.**

```text
{{#include ../code/out/ch05_sched.out}}
```

**Listing 5-2. The same simulator in Rust.**

```rust
{{#include ../code/ch05/sched_sim.rs}}
```

**Output 5-2.**

```text
{{#include ../code/out/ch05_sched_rs.out}}
```

Three implementation details are the whole art of the simulation. FCFS is
one loop over the arrival order. SJF is the same loop over a
burst-sorted copy of the jobs. RR is a queue with a remainder counter per
job: run `min(quantum, remaining)`, and push the job back if anything is
left. Every real scheduler's data structure is a variation of that queue.

<div class="callout experiment">
<span class="label">Experiment</span>

Change the quantum to 1 and to 15, and watch the RR averages. At 1, the
short jobs finish earlier but A's turnaround grows with every switch. At
15, RR's schedule equals FCFS's. The quantum is a trade, not a
correctness setting.

</div>

## 5.4 What real schedulers add

Production schedulers — the completely fair scheduler in Linux, the
multi-queue scheduler in macOS — add four ideas to the three policies.

**Priorities.** Some threads matter more: the audio thread over the
indexer. Priorities weight the queue, so high-priority work runs sooner
without starving the rest, which a fair share per priority band
prevents.

**Multiple queues with feedback.** A thread that uses its whole slice is
CPU-bound and lands in a lower-priority queue; a thread that blocks
early is interactive and stays high. The scheduler learns behavior from
history, which solves SJF's problem of not knowing job lengths: past
behavior stands in for future length.

**Preemption.** A timer interrupt every few milliseconds guarantees the
scheduler gets to run, which is what makes RR possible at all. Without
the timer, a CPU-bound thread would hold the core forever.

**Affinity and topology.** A thread runs best on the core whose caches
hold its data. Schedulers prefer the last core a thread used, and on
NUMA machines, the cores near the thread's memory; Chapter 17 returns to
this with a diagram.

One honest boundary: the kernel's scheduler is a deep subject in itself,
and this chapter stops at its interface. The policies here — FCFS, SJF,
RR, priorities, feedback — are the vocabulary every deeper account uses,
and the simulation is the correct mental model at the resolution a
systems engineer usually needs.

<div class="callout summary">
<span class="label">Summary</span>

- The scheduler dispatches from the ready queue on finish, block, or
  timer expiry; policy lives entirely in that choice.
- Turnaround measures completion; response measures first running; the
  two pull in opposite directions.
- FCFS is fair in order, SJF optimal for known lengths, RR responsive at
  the cost of turnaround.
- Real schedulers add priorities, feedback queues, preemption timers,
  and cache-aware placement to the three policies.
- The ready queue is the shared data structure; Chapter 6 is about what
  happens when threads queue on a lock instead of a core.

</div>
