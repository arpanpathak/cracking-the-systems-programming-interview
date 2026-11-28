<img class="plate" src="art/ch31.png" alt="Dispatcher, the robot who picks the next job by rank, beside a rack of job tickets sorted by rank that feeds two worker bots">

# Scheduling jobs by policy

<div class="covers" markdown="1">

This chapter covers

- Separating scheduling policy from dispatch mechanics by projecting policies onto a single min-heap sort key
- Quantum-bounded preemption and how round-robin and SRTF emerge from re-queuing timestamps
- Evaluating mean turnaround time across FCFS, SJF/SRTF, and priority policies
- Extending the priority heap to concurrent OS worker threads under `thread::scope`
- Replacing panic-on-poison `.unwrap()` calls with value-based error propagation and analyzing handle-dropping semantics

</div>

Whenever the number of runnable tasks exceeds the available processor cores, a **scheduler** must arbitrate access
to compute resources by deciding which job executes next and for how long. Section 15.6 examined round-robin
time-slicing, which allocates equal processor shares to every runnable task. Real systems also schedule by intrinsic
job attributes such as estimated service time or static urgency.

Rather than writing a separate queue structure for every discipline, production dispatchers isolate **mechanism**
(an ordered runqueue supporting logarithmic extraction of the minimum key) from **policy** (a ranking function that
maps job metadata to an ordering key). This chapter formalizes that separation over Rust's `BinaryHeap` (chapter 5),
first on a single simulated CPU with a discrete quantum and then across concurrent worker threads sharing a
mutex-protected priority queue.

## 31.1 Scheduling policies on one CPU

**Problem formulation.** Consider a single processor servicing a static batch of *n* jobs arriving simultaneously at
logical clock `t = 0`. Each job *j* carries an identifier, a total CPU burst duration `time`, and a static integer
`priority` (where smaller integers denote higher urgency). Execution proceeds in bounded slices of at most one
**quantum** *q*: once a job consumes *q* clock units without finishing, the dispatcher preempts it and returns it to
the ready set. We evaluate three classical arbitration policies:

- **First come, first served (FCFS):** selects the job that has resided longest in the ready set.
- **Shortest job first (SJF):** selects the job with the smallest remaining CPU burst.
- **Priority scheduling:** selects the job with the smallest priority number.

Applied to the four-job workload `a` (burst 5, priority 2), `b` (burst 2, priority 3), `c` (burst 3, priority 1),
and `d` (burst 4, priority 1) under quantum `q = 2`, FCFS and SJF both complete the jobs in order `b, c, d, a`,
whereas priority scheduling completes them in order `c, d, a, b`.

**Baseline complexity.** Storing runnable jobs in an unsorted `Vec` and performing a linear scan prior to each
dispatch requires O(*n*) comparisons per slice. Over a schedule spanning *s* total slices, dispatch overhead scales
as O(*s* × *n*).

**Unified heap architecture.** Projecting every policy onto a scalar **rank** allows a single binary min-heap of
4-tuples `(rank, queued_at, index, time_left)` to serve all three disciplines. Because Rust compares tuples
lexicographically from left to right (section 5.3.1), the heap enforces a strict total order: `rank` governs primary
selection, `queued_at` (the logical clock instant at which the entry entered the heap) breaks ties in FIFO order so
longer-waiting jobs run first, and the immutable input `index` breaks any residual tie deterministically. On each
dispatch step, the scheduler extracts the minimum tuple in O(log *n*) time, advances the logical clock by
`min(time_left, q)`, and reinserts unfinished jobs with an updated rank and `queued_at = clock`.

### 31.1.1 Unifying three policies through a single rank

The `Policy::rank` method translates each discipline into an integer key computed from remaining burst and static
priority:

- **FCFS as round-robin (`Policy::Fcfs => 0`).** Assigning every job the constant rank `0` collapses primary key
  ordering and delegates selection entirely to `(queued_at, index)`. When a job exhausts its quantum and re-enters
  the heap stamped with the current clock, its timestamp strictly exceeds that of every waiting entry, placing it
  at the tail of the ready order. Combining a constant rank with quantum preemption therefore reproduces
  **round-robin** rotation (section 15.6) without a dedicated ring queue.
- **Preemptive SJF as SRTF (`Policy::Sjf => remaining`).** Because the dispatcher recomputes `rank` on every
  reinsertion using the decremented `time_left`, a partially executed job competes with its remaining burst rather
  than its original length. This preemptive refinement is **shortest remaining time first (SRTF)**.
- **Strict priority with fair intra-level rotation (`Policy::Priority => priority`).** Ranking by static priority
  dispatches urgent jobs ahead of lower-priority work. Jobs sharing the same priority value tie on the first tuple
  component and fall back to `queued_at`, cycling in round-robin fashion within their priority band. In our
  workload, jobs `c` and `d` (both priority 1) alternate slices until both retire.

### 31.1.2 Quantum preemption and turnaround analysis

Upon popping `(.., index, left)` from the min-heap, the dispatcher compares `left` against `quantum` via
`left.cmp(&quantum)` and branches across two exhaustive cases:

1. **`Ordering::Greater` (preemption):** More than one quantum of work remains. The dispatcher advances `clock` by
   `quantum`, decrements `left` by `quantum`, recomputes `policy.rank(left, job.priority)`, and pushes the updated
   entry back onto the heap stamped with the new `clock`.
2. **`Ordering::Less | Ordering::Equal` (completion):** The job finishes within the current slice. The dispatcher
   advances `clock` by `left` and invokes `(jobs[index].run)()` to record its output.

Tracing the eight heap extractions under `Policy::Sjf` demonstrates how recomputing the rank upon preemption keeps
nearly finished jobs at the root of the heap:

| Pop | Entry popped | Job | Clock after the slice | Entry pushed back |
|---|---|---|---|---|
| 1 | `(2, 0, 1, 2)` | b | 2 | b completes |
| 2 | `(3, 0, 2, 3)` | c | 4 | `(1, 4, 2, 1)` |
| 3 | `(1, 4, 2, 1)` | c | 5 | c completes |
| 4 | `(4, 0, 3, 4)` | d | 7 | `(2, 7, 3, 2)` |
| 5 | `(2, 7, 3, 2)` | d | 9 | d completes |
| 6 | `(5, 0, 0, 5)` | a | 11 | `(3, 11, 0, 3)` |
| 7 | `(3, 11, 0, 3)` | a | 13 | `(1, 13, 0, 1)` |
| 8 | `(1, 13, 0, 1)` | a | 14 | a completes |

At pop 3, `c` re-emerges ahead of `d`'s `(4, 0, 3, 4)` because its remaining work has dropped to 1, lowering its
rank below `d`'s initial burst of 4. Figure 31.1 contrasts the resulting Gantt timelines across all three policies.

<figure>
<img src="figures/ch31-quantum-schedule.svg" alt="Three timelines from clock 0 to 14, one per policy. Policy::Fcfs runs a, b, c, d, a, c, d, a, and the jobs finish as b at 4, c at 11, d at 13 and a at 14. Policy::Sjf runs b, c, c, d, d, a, a, a, and the jobs finish as b at 2, c at 5, d at 9 and a at 14. Policy::Priority runs c, d, c, d, a, a, a, b, and the jobs finish as c at 5, d at 7, a at 12 and b at 14.">
<figcaption><b>Figure 31.1</b> The slices executed under each policy with a quantum of 2. Under <code>Policy::Fcfs</code>, the jobs take turns in round-robin order.</figcaption>
</figure>

A standard metric for batch scheduling efficiency is **turnaround time**, defined as
`T_turnaround = T_completion - T_arrival`. Because every job in this static workload arrives at `t = 0`, each job's
completion clock equals its turnaround time:

| Policy | Completion times | Mean turnaround time |
|---|---|---|
| FCFS | b 4, c 11, d 13, a 14 | (4 + 11 + 13 + 14) / 4 = 10.5 |
| SJF | b 2, c 5, d 9, a 14 | (2 + 5 + 9 + 14) / 4 = 7.5 |
| Priority | c 5, d 7, a 12, b 14 | (5 + 7 + 12 + 14) / 4 = 9.5 |

SJF attains the minimal mean turnaround time (7.5), illustrating a classical theorem of scheduling theory: for any
static job set arriving simultaneously, servicing jobs in non-decreasing order of processing time minimizes average
turnaround time because every short job retires early rather than accumulating wait latency behind longer jobs.
Round-robin yields the highest mean (10.5) because interleaving partial progress across all four jobs defers three
of the four completions past clock 11, trading throughput efficiency for bounded interactive response time.

### 31.1.3 The program

<p class="listing"><b>Listing 31.1</b> A scheduler with 3 policies and a quantum, on 1 heap. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/shortest_job_first_scheduling.rs">src/bin/shortest_job_first_scheduling.rs</a></p>

```rust
{{#include ../../rust-interview-lab/src/bin/shortest_job_first_scheduling.rs}}
```

```text
$ cargo run --bin shortest_job_first_scheduling
fcfs     ["b done", "c done", "d done", "a done"]
sjf      ["b done", "c done", "d done", "a done"]
priority ["c done", "d done", "a done", "b done"]
```

Notable structural properties of Listing 31.1:

- **Min-heap inversion.** `std::collections::BinaryHeap` implements a max-heap; wrapping each 4-tuple in
  `std::cmp::Reverse` reverses its `Ord` relation at zero runtime cost so `pop()` always yields the minimal tuple
  (section 5.3.2).
- **Deterministic initial ordering.** Seeding every entry with `queued_at = 0` ensures that ties among initial
  entries break strictly by input `index`.
- **Irrelevant-field elision.** Destructuring `while let Some(Reverse((.., index, left))) = heap.pop()` discards
  the sort keys (`rank` and `queued_at`) via the `..` rest pattern once extraction has already used them.
- **Logical-clock simulation.** The loop advances a virtual counter without blocking any OS thread, deferring
  invocation of each job closure until its terminal slice. Section 31.2 transitions from simulated time to real
  concurrent execution.
- **Starvation under dynamic arrivals.** Because Listing 31.1 processes a closed static batch, every job eventually
  terminates. In an open system receiving a steady stream of short or high-priority tasks, SJF and strict priority
  scheduling can delay long or low-priority work indefinitely, a liveness failure known as **starvation**.

**Complexity.** A job of duration *t* undergoes `⌈t / q⌉` dispatches. Across *s* total slices and *n* jobs, the
heap performs *s* removals and at most *s* insertions, requiring O(*s* log *n*) time and O(*n*) auxiliary space.

## 31.2 Workers that pop from a priority heap

Replacing the simulated processor of section 31.1 with multiple OS worker threads shifts the problem from logical
time-slicing to concurrent dispatch synchronization. Before spawning workers, the scheduler constructs a single
`Mutex<BinaryHeap<JobState>>` populated with the entire batch. A fixed cohort of worker threads then loops,
acquiring the heap mutex solely to extract the lowest-ranked job before executing that job concurrently without
holding any lock. Two implementations follow: version 1 panics on poisoned mutexes via `.unwrap()`, while version 2
surfaces lock failures through `Result` and `?`.

**Problem formulation.** Two worker threads execute the four jobs `a`, `b`, `c`, and `d` from section 31.1. Each
closure now simulates real compute latency by sleeping for 50, 20, 30, or 40 ms before returning its identifier,
while retaining its static metadata (`time` of 5, 2, 3, or 4 and `priority` of 2, 3, 1, or 1). The scheduler returns
results in the chronological order in which workers complete them.

**Concurrency architecture.** Whereas the general-purpose thread pools of sections 18.2 through 18.7 ingest
unbounded work streams over channels and block idle workers on condition variables, a fixed-batch scheduler knows
its entire workload before startup. Consequently, an empty heap signals permanent termination rather than transient
idleness. Each queue entry has type `Reverse((u32, Duration, usize))`, pairing `rank` with the elapsed duration
since `start` measured via `std::time::Instant`, a monotonic clock immune to wall-clock adjustments. Populating
entries in slice order establishes non-decreasing timestamps that preserve input order on rank ties. Launching
workers inside `std::thread::scope` (section 16.1.3) establishes a lexical join barrier: because the scope blocks
until every worker exits, workers borrow `jobs`, `heap`, and `results` directly from `schedule`'s stack frame
without reference-counted `Arc` wrappers.

### 31.2.1 Version 1, with `unwrap`

Listing 31.2 presents the initial scoped-thread implementation using `.unwrap()`.

<p class="listing"><b>Listing 31.2</b> 2 workers that pop jobs from a priority heap. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/multi_thread_job_scheduling.rs">src/bin/multi_thread_job_scheduling.rs</a></p>

```rust
{{#include ../../rust-interview-lab/src/bin/multi_thread_job_scheduling.rs}}
```

```text
$ cargo run --bin multi_thread_job_scheduling
fcfs     ["b", "a", "c", "d"]
sjf      ["b", "c", "d", "a"]
priority ["c", "d", "b", "a"]
```

Each iteration of a worker loop executes three strictly separated phases:

1. **Bounded critical section for extraction.** The statement `let next = heap.lock().unwrap().pop();` acquires the
   heap mutex, removes the highest-priority entry, and drops the temporary `MutexGuard` at the terminating
   semicolon. Releasing the lock before executing the job preserves parallelism across workers, avoiding the
   lock-serialization defect diagnosed in section 18.3.
2. **Termination check.** When `next` is `None`, the `let ... else` statement exits the loop via `break`,
   terminating the worker thread cleanly.
3. **Lock-free execution and synchronized collection.** The worker invokes `(jobs[index].run)()` outside every
   critical section, then briefly acquires `results` to push the return value. Because workers append upon
   completion rather than dispatch, `results` records empirical completion order.

Dispatch order and completion order decouple immediately once multiple workers execute variable-duration tasks in
parallel (Figure 31.2). Under `Policy::Priority`, the two workers claim `c` (priority 1, 30 ms) and `d`
(priority 1, 40 ms) at `t = 0`. At 30 ms, worker 1 retires `c` and dispatches `a` (priority 2, 50 ms), running it
until 80 ms. At 40 ms, worker 2 retires `d` and dispatches `b` (priority 3, 20 ms), which finishes at 60 ms, 20 ms
before the higher-priority job `a`. Static priority constrains admission order, not retirement order.

<figure>
<img src="figures/ch31-heap-workers.svg" alt="Three timelines from 0 to 90 ms, each with 2 worker lanes. Policy::Fcfs pops a, b, c, d: worker 1 runs a from 0 to 50 and d from 50 to 90, worker 2 runs b from 0 to 20 and c from 20 to 50, and a and c both end at 50 ms. Policy::Sjf pops b, c, d, a: worker 1 runs b from 0 to 20 and d from 20 to 60, worker 2 runs c from 0 to 30 and a from 30 to 80, so the results are b, c, d, a. Policy::Priority pops c, d, a, b: worker 1 runs c from 0 to 30 and a from 30 to 80, worker 2 runs d from 0 to 40 and b from 40 to 60, so the results are c, d, b, a.">
<figcaption><b>Figure 31.2</b> 2 workers and 4 jobs under each policy. The pop order follows the rank; the order of the results follows the completion times.</figcaption>
</figure>

Parallel completion times also introduce timing-dependent nondeterminism. Under `Policy::Fcfs`, worker 1 finishes
`a` at roughly 50 ms while worker 2 finishes `b` (20 ms) followed by `c` (30 ms), arriving at the same 50 ms
boundary. Whichever thread wins the `results` mutex appends first: across 30 consecutive runs, the binary produced
`["b", "a", "c", "d"]` 27 times and `["b", "c", "a", "d"]` 3 times. Under SJF and priority scheduling, all
completion timestamps are separated by at least 10 ms, yielding identical outputs across all 30 runs.

Type-system and synchronization invariants in Listing 31.2:

- **`F: Fn() -> T + Sync`.** Every worker invokes job closures through the shared immutable slice `&jobs`. Sending
  a shared reference `&[Job<F>]` across thread boundaries requires `Job<F>: Sync`, which in turn requires `F: Sync`
  (section 16.1.4).
- **`T: Send`.** Each worker constructs a `T` on its own thread and moves it into the shared `results` vector that
  the calling thread later consumes, requiring ownership transfer across threads.
- **Zero-cost lock unwrapping.** Once `thread::scope` returns, static borrow rules guarantee no concurrent handle to
  `results` survives. Calling `results.into_inner()` consumes the `Mutex` by value and retrieves the underlying
  `Vec<T>` without invoking a lock syscall.
- **Mutex poisoning.** Calling `.unwrap()` on `lock()` or `into_inner()` panics if the mutex is poisoned, a state
  entered only when another thread panics while holding the guard (section 16.6).

### 31.2.2 Version 2: errors as values

Library code should report synchronization failures to callers rather than aborting through `.unwrap()`. Version 2
introduces the alias `type ScheduledJob<T, E> = Result<Vec<T>, E>`, updates `schedule` to return
`ScheduledJob<T, String>`, and changes `main` to return `Result<(), String>`. All domain types, job definitions, and
console output stay unchanged; only `schedule` changes (Listing 31.3).

<p class="listing"><b>Listing 31.3</b> <code>schedule</code> with errors returned as values (lines 35 to 76). <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/job_scheduling_worker_with_error_propagation.rs">src/bin/job_scheduling_worker_with_error_propagation.rs</a></p>

```rust
{{#include ../../rust-interview-lab/src/bin/job_scheduling_worker_with_error_propagation.rs:35:76}}
```

```text
$ cargo run --bin job_scheduling_worker_with_error_propagation
fcfs     ["b", "a", "c", "d"]
sjf      ["b", "c", "d", "a"]
priority ["c", "d", "b", "a"]
```

Annotating each worker closure with `-> Result<(), String>` enables fallible `?` propagation across the loop body,
yielding two distinct exit paths:

1. **Poisoned mutex.** `heap.lock()` or `results.lock()` returns `Err(PoisonError)`. Chaining
   `.map_err(|e| e.to_string())?` translates the lock error into an owned `String` and aborts the worker loop.
2. **Exhausted queue.** `pop()` yields `None`, which `.ok_or("worker polled an empty queue")` promotes to
   `Err(&str)`. The `?` operator converts `&str` into `String` through `From` and exits the closure cleanly,
   eliminating the need for an explicit `break`.

Notice a subtle interaction with `std::thread::scope`. Every call to `s.spawn` returns a `ScopedJoinHandle<Result<(), String>>`,
which Listing 31.3 drops immediately. Although `thread::scope` guarantees that every spawned thread joins before the
scope exits, dropping the handles discards each closure's `Result`. Inside the scope, a worker that terminates due
to a poisoned mutex is therefore indistinguishable from one that drains an empty queue. Error reporting to the
caller of `schedule` instead relies on the post-scope `heap.into_inner()` and `results.into_inner()` checks, which
inspect both mutexes for poison and propagate any `Err` through `?`.

Neither version intercepts panics originating inside a user job closure. When a scoped worker panics and its
`ScopedJoinHandle` is not manually joined, `thread::scope` waits for all sibling workers to finish and then resumes
the panic on the calling thread.

**Complexity.** Building the binary heap via `collect` takes O(*n*) time using Floyd's linear-time heapification,
and each of the *n* extractions costs O(log *n*) under the heap lock. Given *w* workers and uniform job duration
*d*, wall-clock completion time approaches `⌈n / w⌉ × d`, bounded by lock contention when *d* approaches the cost
of mutex acquisition.

## 31.3 The complete files

Listing 31.4 reproduces version 2 in full, including `main` and the four-job benchmark workload.

<p class="listing"><b>Listing 31.4</b> Version 2, with errors returned as values. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/job_scheduling_worker_with_error_propagation.rs">src/bin/job_scheduling_worker_with_error_propagation.rs</a></p>

```rust
{{#include ../../rust-interview-lab/src/bin/job_scheduling_worker_with_error_propagation.rs}}
```

<div class="summary" markdown="1">

## Summary

- Projecting scheduling policies onto a scalar rank unifies FCFS, SJF/SRTF, and priority scheduling over a single
  binary min-heap of `(rank, queued_at, index, time_left)` tuples.
- Under quantum-bounded preemption, stamping reinserted jobs with the current logical clock places them behind
  every waiting entry of equal rank, deriving round-robin rotation directly from FCFS.
- For a static simultaneous arrival set, servicing the shortest remaining burst first minimizes mean turnaround
  time (7.5 versus 9.5 for priority scheduling and 10.5 for round-robin on the section 31.1 workload).
- Scoped worker threads can share a `Mutex<BinaryHeap<_>>` concurrently when each worker confines its critical
  section to the pop statement; policy dictates dispatch order, while job durations and worker count dictate
  completion order.
- Dropping a `ScopedJoinHandle` inside `thread::scope` discards the worker closure's `Result`; reporting
  individual worker errors requires collecting and joining every handle explicitly.

</div>

## Exercises

1. Extend `Job` in Listing 31.1 with an explicit arrival timestamp so jobs enter the min-heap only once the logical
   clock reaches their arrival time. Compute each job's turnaround time (`completion - arrival`) and compare mean
   turnaround across all three policies.
2. Construct an arrival stream that injects a unit-length job (`time = 1`) on every slice and demonstrate
   indefinite starvation of a length-8 job under `Policy::Sjf`. Implement **aging** by subtracting accrued waiting
   time from each job's rank, and verify that the length-8 job completes.
3. Run Listing 31.2 with `workers` set to 1, 2, and 4 under all three policies. Record the completion sequences and
   sketch the corresponding multi-lane execution timelines modeled on Figure 31.2.
4. Collect every `ScopedJoinHandle` returned by `s.spawn` in Listing 31.3, return `Ok(())` on an empty heap so
   normal worker exit is distinct from failure, and join all handles so `schedule` propagates the first worker
   error directly.
