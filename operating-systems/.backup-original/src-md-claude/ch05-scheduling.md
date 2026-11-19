# 5. Scheduling Theory and Policy

The scheduler is the kernel component responsible for the multiplexing of
processing resources, deciding which threads occupy available CPU cores at
any given moment. This decision-making process is governed by specific
policies that attempt to optimize various performance metrics, each
representing a different set of user or system requirements.

<div class="callout glance">
<span class="label">This chapter covers</span>

- the events that invoke a scheduler, and the ready queue
- turnaround time, wait time, and response time
- First-Come, First-Served, Shortest Job First, and Round-Robin
- a simulator for the three policies, in C++ and Rust
- priorities, feedback queues, preemption, and affinity

</div>

## 5.1 Scheduling Dynamics and Performance Metrics

A scheduler operates by transitioning threads between various execution
states. When a thread terminates, blocks on an event (such as I/O or
synchronization), or exhausts its allotted time slice, the kernel invokes
the scheduler to select a new thread from the **ready queue** and dispatch
it to a core. The efficiency of these policies is evaluated using three
primary metrics:

- **Turnaround Time:** The interval from a job's initial arrival to its
  ultimate completion, a metric critical for batch-oriented workloads.
- **Wait Time:** The cumulative duration a job resides in the ready queue.
- **Response Time:** The latency between a job's arrival and its initial
  execution, which is the primary metric for interactive and
  time-sensitive applications.

<figure>
<img src="figures/ch05_queues.svg" alt="The scheduler moves jobs between the ready queue, the CPU, and the wait queue"/>
</figure>

Figure 5-1 locates these transitions among the ready queue, the CPU, and
the wait queue. The transitions themselves are mechanism and are common to
every scheduler. What distinguishes one scheduler from another is policy,
the rule by which the next thread is selected.

Optimization of these metrics is often a zero-sum game; policies that
minimize turnaround time frequently do so at the expense of response time,
and vice versa.

## 5.2 Fundamental Scheduling Policies

The theoretical foundation of scheduling rests on three classic policies:

1. **First-Come, First-Served (FCFS):** A non-preemptive policy where jobs
   are processed in strict arrival order. While computationally trivial,
   FCFS is susceptible to the "convoy effect," where a single long-running
   task obstructs the progress of numerous subsequent short tasks,
   drastically increasing average turnaround time.
2. **Shortest Job First (SJF):** An optimal policy for minimizing average
   turnaround time, which prioritizes tasks with the smallest predicted
   execution bursts. However, its practical implementation is limited by
   the inherent difficulty of accurately predicting future execution
   requirements.
3. **Round-Robin (RR):** A preemptive policy that distributes CPU time via
   fixed-duration increments known as **quanta**. RR excels at providing
   low response times by ensuring that every job receives a portion of the
   CPU within a single pass of the ready queue. However, the overhead of
   frequent context switching and the potential for increased turnaround
   time must be managed by carefully selecting the quantum size.

Figure 5-2 subjects all three policies to one workload: job A requires 10
time units, jobs B and C require 5 each, and all arrive at time 0.

<figure>
<img src="figures/ch05_gantt.svg" alt="Gantt charts for FCFS, SJF, and round-robin on jobs of length 10, 5, and 5"/>
</figure>

Under FCFS, the jobs complete at 10, 15, and 20. Since every job arrived
at time 0, these values are also the turnaround times, and their mean is
(10 + 15 + 20) / 3 = 15. SJF reorders execution to B, C, A, yielding
completions at 5, 10, and 20 and a mean of 35 / 3 = 11.7. RR with a
quantum of 5 executes A, B, C, A, so that A completes at 20, B at 10, and
C at 15, and the mean returns to 15. RR thus confers no advantage in
turnaround on this workload, yet every job commences within 10 time units,
and B and C conclude before A.

## 5.3 A Simulator for the Three Policies

Listing 5-1 mechanizes the same arithmetic. It provides one function per
policy and a `report` function that tabulates completion, turnaround, and
wait times.

**Listing 5-1. A simulator for FCFS, SJF, and RR (C++20).**

```cpp
{{#include ../code/ch05/sched_sim.cpp}}
```

**Output 5-1. The completion times agree with Figure 5-2.**

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

The brevity of the implementation reflects the simplicity of the policies.
`fcfs` reduces to one loop that accumulates bursts on a running clock. SJF
requires only that `shortest_first` order a copy of the jobs by burst
length before `fcfs` processes them. `rr` maintains a queue of job indices
together with the residual demand of each job: it dequeues the head, runs
it for the lesser of the quantum and its residual demand, and re-enqueues
it if demand remains.

<div class="callout experiment">
<span class="label">Experiment</span>

Change the quantum from 5 to 1, and then to 15. With a quantum of 1, B and
C complete at times 14 and 15, and A still completes at 20. With a quantum
of 15, every job finishes within its first slice, and the RR schedule is
identical to the FCFS schedule.

</div>

## 5.4 Advanced Heuristics in Production Schedulers

Modern production kernels, such as Linux and macOS, extend these
fundamental policies through sophisticated heuristics designed to handle
diverse and unpredictable workloads.

- **Priority-Based Scheduling:** Assigns varying levels of importance to
  threads, allowing latency-sensitive tasks (e.g., audio processing) to
  preempt background tasks.
- **Multi-Level Feedback Queues:** Employs past behavior as a proxy for
  future requirements. Threads that exhaust their full quantum are
  categorized as compute-bound and relegated to lower-priority queues,
  whereas threads that block frequently are identified as interactive and
  maintained at higher priorities.
- **Preemption:** Utilizes hardware timer interrupts to enforce
  time-slicing, ensuring that no single thread can monopolize a core
  indefinitely.
- **Processor Affinity and Topology Awareness:** Leverages cache locality
  and hardware topology to prefer scheduling threads on cores where their
  data is already resident or on cores that are topologically close to
  their memory, minimizing data transfer latencies.

Feedback queues thereby approximate the foreknowledge that SJF demands,
substituting observed history for the unknowable future. Linux relied on
the Completely Fair Scheduler for many years and superseded it with EEVDF
in version 6.6, a change of policy that left the context-switch mechanism
intact. Topology awareness recurs in Chapter 17.

<div class="callout summary">
<span class="label">Summary</span>

- The scheduler selects from the ready queue whenever a thread
  terminates, blocks, or exhausts its time slice.
- Turnaround, wait, and response time cannot all be minimized at once.
- FCFS preserves arrival order and suffers the convoy effect. SJF
  minimizes mean turnaround but presupposes known burst lengths. RR
  minimizes response time at the cost of additional context switches.
- On jobs of 10, 5, and 5 units, the mean turnaround is 15 under FCFS,
  11.7 under SJF, and 15 under RR with a quantum of 5.
- Production schedulers add priorities, feedback queues, timer-driven
  preemption, and affinity.

Threads also queue for locks rather than cores, which is the concern of
Chapter 6.

</div>
