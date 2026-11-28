<img class="plate" src="art/ch31.png" alt="Dispatcher, the robot who picks the next job by rank, beside a rack of job tickets sorted by rank that feeds two worker bots">

# Scheduling jobs by policy

<div class="covers" markdown="1">

This chapter covers

- Reducing FCFS, shortest job first, and priority scheduling to 1 rank in a min-heap
- Preempting a job at the end of a time quantum, and how round robin and SRTF arise from the rank
- Mean turnaround time under each policy, computed from a trace
- Workers in `thread::scope` that pop a fixed set of jobs from a `Mutex<BinaryHeap<_>>`
- A first version with `unwrap`, and a second version in which errors are returned as values

</div>

When more jobs are ready than processors are available, the next job to run must be selected, and this selection is called **scheduling**. Recall from section 15.6 that under round robin, every runnable task is given the same turn on the CPU. Under other policies, the next job is selected by a property of the job itself, such as its remaining time or its urgency. In this chapter, we express each policy as 1 number per job and keep the ready jobs in a heap from chapter 5. The jobs are executed first on 1 simulated CPU and then on real worker threads.

## 31.1 Scheduling policies on one CPU

**The problem.** A single CPU executes a set of jobs. Each job has a name, a running time in clock units, and a priority, where a smaller priority number corresponds to a more urgent job. The CPU executes 1 job at a time, for at most 1 **quantum**, a fixed slice of clock time. The job that is given the next slice is determined by a **scheduling policy**. 3 classical policies are compared:

- Under **first come, first served (FCFS)**, the CPU is given to the job that has waited longest.
- Under **shortest job first (SJF)**, the CPU is given to the job with the least remaining time.
- Under **priority scheduling**, the CPU is given to the job with the smallest priority number.

The 4 jobs a (time 5, priority 2), b (time 2, priority 3), c (time 3, priority 1) and d (time 4, priority 1) are scheduled with a quantum of 2. The jobs are completed in the order `b, c, d, a` under FCFS and SJF, and in the order `c, d, a, b` under priority scheduling.

**The baseline approach.** The ready jobs can be kept in a `Vec`, and the vector can be scanned for the best job before every slice. Each selection then costs O(n), and a schedule of s slices costs O(s × n).

**The heap approach.** Every policy is reduced to 1 number per job, the **rank**, and the ready jobs are kept in a min-heap of tuples `(rank, queued at, index, time left)`. The second field, the queued-at time, is the clock value at which the job was inserted into the heap. When 2 jobs have the same rank, the entry of the job that has waited longer is therefore the smaller tuple, and that job is run first. The smallest tuple is popped repeatedly, and its job is run for 1 quantum or less. If time remains, the job is pushed back with a new rank and a new queued-at time. Each selection costs O(log n).

### 31.1.1 A single rank for 3 policies

The rank is computed by `Policy::rank` from the remaining time and the priority of a job:

- For `Policy::Fcfs`, the rank is 0 for every job. All entries are equal in rank, and the order is decided by the queued-at time and then by index. A preempted job is pushed back with the current clock as its queued-at time, so it is placed behind every job that is already waiting. With a quantum, FCFS is therefore equivalent to **round-robin** scheduling, the policy of section 15.6.
- For `Policy::Sjf`, the rank is the remaining time. The rank is recomputed on every push, so a partially executed job is ranked by its remaining time instead of its original time. This variant of SJF is called **shortest remaining time first (SRTF)**.
- For `Policy::Priority`, the rank is the priority. Jobs of equal priority are ordered by their queued-at times, so they are run in round-robin order within their priority level. In this way, the CPU is shared by the jobs c and d, both of priority 1, until both are completed.

### 31.1.2 Preemption at the end of a quantum

After each pop, the remaining time `left` is compared with the quantum in a `match` with 2 arms:

1. `Greater`: more than 1 quantum of work remains for the job. The clock is advanced by 1 quantum, and the remaining time is reduced by 1 quantum. The job is then pushed back with a recomputed rank and the current clock as its queued-at time.
2. `Less | Equal`: the job is completed within this slice. The clock is advanced by the remaining time, and the closure `run` of the job is invoked to produce its result.

Under SJF, the 8 pops are listed below. In the pushed entries, the rank of a partially executed job decreases with its remaining time.

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

At pop 3, the entry of c is popped ahead of `(4, 0, 3, 4)` for d, because 1 unit of c remains and its rank has fallen to 1. The schedules of all 3 policies are drawn as timelines in figure 31.1.

<figure>
<img src="figures/ch31-quantum-schedule.svg" alt="Three timelines from clock 0 to 14, one per policy. Policy::Fcfs runs a, b, c, d, a, c, d, a, and the jobs finish as b at 4, c at 11, d at 13 and a at 14. Policy::Sjf runs b, c, c, d, d, a, a, a, and the jobs finish as b at 2, c at 5, d at 9 and a at 14. Policy::Priority runs c, d, c, d, a, a, a, b, and the jobs finish as c at 5, d at 7, a at 12 and b at 14.">
<figcaption><b>Figure 31.1</b> The slices executed under each policy with a quantum of 2. Under <code>Policy::Fcfs</code>, the jobs take turns in round-robin order.</figcaption>
</figure>

Since all 4 jobs are ready at clock 0, the completion time of a job is also its **turnaround time**, the interval between its arrival and its completion. The mean turnaround times of the 3 schedules in figure 31.1 are computed below.

| Policy | Completion times | Mean turnaround time |
|---|---|---|
| FCFS | b 4, c 11, d 13, a 14 | (4 + 11 + 13 + 14) / 4 = 10.5 |
| SJF | b 2, c 5, d 9, a 14 | (2 + 5 + 9 + 14) / 4 = 7.5 |
| Priority | c 5, d 7, a 12, b 14 | (5 + 7 + 12 + 14) / 4 = 9.5 |

The smallest mean is obtained under SJF, in agreement with the classical result that the mean turnaround time is minimized by running the shortest jobs first when all jobs are ready together.

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

Key details of the implementation:

- The 4-tuple is wrapped in `Reverse`, so the smallest tuple is popped first from `BinaryHeap`, a max-heap (section 5.3.2).
- Every initial entry is queued at clock 0, so ties among the first entries are broken by index, the order of the input.
- In `while let Some(Reverse((.., index, left))) = heap.pop()`, the rank and the queued-at time are skipped with the rest pattern `..`, because they are not needed after the pop.
- Time is measured on a logical clock, and no thread sleeps. The closure of a job is invoked once, in the slice in which the job is completed. In section 31.2, the same policies are applied to jobs executed on real threads.
- In this program, all jobs are ready at clock 0. If short or urgent jobs arrived continually, a long job under SJF or a low-priority job under priority scheduling could remain unscheduled indefinitely. This condition is called **starvation**.

**Complexity.** A job with running time t is popped ⌈t / q⌉ times for a quantum q. For a schedule of s slices in total, the running time is O(s log n), and at most n entries are in the heap.

## 31.2 Workers that pop from a priority heap

In section 31.1, 3 scheduling policies were simulated on 1 CPU with a logical clock. In this section, the same `Policy` type and the same rank are applied to jobs executed on real threads. All jobs are placed in a `BinaryHeap` behind a `Mutex` before any worker starts. A fixed number of workers then repeatedly pop the job of smallest rank and execute it. 2 versions are developed, the first with `unwrap` and the second with errors returned as values.

**The problem.** The 4 jobs a, b, c and d of section 31.1 are executed by 2 worker threads. In each job, the calling thread sleeps for 50, 20, 30 or 40 ms, and the job's name is then returned. The `time` (5, 2, 3 or 4) and the `priority` (2, 3, 1 or 1) of every job are unchanged. The results are to be collected in the order in which the jobs are completed.

**The design.** In the pools of sections 18.2 to 18.7, jobs are received through a channel while the workers run. In this design, the set of jobs is fixed in advance. The queue is therefore a `Mutex<BinaryHeap<JobState>>` filled once, and a worker exits when the heap is empty. Each heap entry is `Reverse((rank, time queued, index))`. The second field is the time elapsed since `start`, measured with `Instant`, a monotonic clock whose readings never decrease. The entries are created in index order, so jobs of equal rank are popped in input order. The workers are started with `thread::scope` (Section 16.1.3), so `jobs`, `heap` and `results` can be borrowed by the workers without `Arc`, since every worker is joined at the end of the scope.

### 31.2.1 Version 1, with `unwrap`

The complete first version is shown in Listing 31.2.

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

A worker executes 3 steps in each iteration of its loop:

1. The worker locks the heap and pops the smallest entry in the statement `let next = heap.lock().unwrap().pop();`. The `MutexGuard` is a temporary of that `let` statement, so it is dropped at the semicolon, and the lock is released before the job is run (Section 18.3).
2. If the heap was empty, the loop is left with `break` in the `else` branch of `let ... else`, and the worker thread ends.
3. Otherwise, the worker invokes the closure of job `index` without holding any lock, then locks `results` and pushes the value. The order of `results` is therefore the order of completion.

The order of pops is determined by the policy. The order of completion also depends on job durations and on the number of workers (figure 31.2). Under `Policy::Priority`, worker 1 pops c and worker 2 pops d. At 30 ms, worker 1 completes c and pops a, the job of the next smaller rank. At 40 ms, worker 2 completes d and pops b, and b is completed at 60 ms, 20 ms before a. A job of lower priority can therefore be completed earlier, because only the starting moment of a job depends on its priority.

<figure>
<img src="figures/ch31-heap-workers.svg" alt="Three timelines from 0 to 90 ms, each with 2 worker lanes. Policy::Fcfs pops a, b, c, d: worker 1 runs a from 0 to 50 and d from 50 to 90, worker 2 runs b from 0 to 20 and c from 20 to 50, and a and c both end at 50 ms. Policy::Sjf pops b, c, d, a: worker 1 runs b from 0 to 20 and d from 20 to 60, worker 2 runs c from 0 to 30 and a from 30 to 80, so the results are b, c, d, a. Policy::Priority pops c, d, a, b: worker 1 runs c from 0 to 30 and a from 30 to 80, worker 2 runs d from 0 to 40 and b from 40 to 60, so the results are c, d, b, a.">
<figcaption><b>Figure 31.2</b> 2 workers and 4 jobs under each policy. The pop order follows the rank; the order of the results follows the completion times.</figcaption>
</figure>

Under `Policy::Fcfs`, the jobs a and c are both completed at about 50 ms, a on worker 1 and c on worker 2. The worker that first acquires the lock on `results` pushes its value first. In 30 consecutive runs of the program, the result was `["b", "a", "c", "d"]` 27 times and `["b", "c", "a", "d"]` 3 times. Under the other 2 policies, the same result was printed in all 30 runs, because no 2 of their jobs are completed within the same few milliseconds.

Key details of the implementation:

- The bound `F: Fn() -> T + Sync` is required because every worker calls the closures through the shared reference `&jobs`. A shared reference to a value can be sent to another thread only if the value is `Sync` (Section 16.1.4).
- The bound `T: Send` is required because each result is produced on a worker thread and returned to the caller's thread.
- After the scope, every worker has been joined, so the vector is taken out of the mutex with `results.into_inner()` without locking it.
- If a mutex is poisoned, the thread that calls `unwrap` on its lock result panics. A mutex is poisoned only when a thread panics while it holds the guard (Section 16.6).

### 31.2.2 Version 2: errors as values

In the second version, each `unwrap` is replaced by `?`, and the return type of `schedule` is `ScheduledJob<T, String>`, an alias for `Result<Vec<T>, String>`. The return type of `main` is `Result<(), String>`, and `?` is applied to every call of `schedule`. The types, the job list and the printed results are identical to version 1, and only `schedule` is changed (Listing 31.3).

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

The closure of each worker is declared as `|| -> Result<(), String>`, so the operator `?` can be applied inside it. A worker now ends under 2 conditions:

1. A poisoned mutex. `Err(PoisonError)` is returned by `lock()`, converted to its message with `map_err(|e| e.to_string())`, and returned from the closure with `?`.
2. An empty heap. `None` is returned by `pop()`, converted to `Err` with `ok_or("worker polled an empty queue")`, and returned from the closure with `?`. Through the `From` implementation of `String`, the `&str` is converted into a `String`. In this version, the empty heap is the normal exit from the loop, and the loop contains no `break`.

For each worker, a `ScopedJoinHandle` is returned by `s.spawn`, and in this version, the handles are dropped without being joined. Every worker is still joined at the end of the scope, but the `Result` of each closure is discarded. A worker that ends because of a poisoned lock is therefore indistinguishable from a worker that ends because the heap is empty. After the scope, `Err` is returned by `heap.into_inner()` if the heap mutex was poisoned, and with the `?` that follows, the error is passed to the caller. The same check is made for the result vector with `results.into_inner()`.

A job that panics is not converted to an error by either version. If a scoped thread panics and its handle is not joined manually, the calling thread panics at the end of `thread::scope`, after all workers have been joined.

**Complexity.** For n jobs, the heap is built by `collect` in O(n) time, and each of the n pops costs O(log n). The lock on the heap is held only for the pop. With w workers and jobs of equal duration d, the n jobs are completed in about ⌈n / w⌉ × d.

## 31.3 The complete files

Version 2 of the worker scheduler is reproduced in full in Listing 31.4, including the job list in `main`.

<p class="listing"><b>Listing 31.4</b> Version 2, with errors returned as values. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/job_scheduling_worker_with_error_propagation.rs">src/bin/job_scheduling_worker_with_error_propagation.rs</a></p>

```rust
{{#include ../../rust-interview-lab/src/bin/job_scheduling_worker_with_error_propagation.rs}}
```

<div class="summary" markdown="1">

## Summary

- A scheduling policy can be reduced to a rank in a min-heap of `(rank, queued at, index, time left)` tuples. With a quantum, round robin corresponds to a rank of 0, shortest remaining time first to the remaining time, and priority scheduling to the priority.
- A preempted job is pushed back with the current clock as its queued-at time, so it is placed behind every waiting job of equal rank.
- When all jobs are ready together, the smallest mean turnaround time is obtained by running the shortest jobs first: 7.5 for the 4 jobs of section 31.1, against 10.5 for round robin and 9.5 for priority scheduling.
- Workers in `thread::scope` can share a `Mutex<BinaryHeap<_>>` when the lock is held only for the pop. The order of the pops is fixed by the policy, and the order of completion depends on the job durations and the number of workers.
- Errors returned from a scoped worker's closure are discarded unless its `ScopedJoinHandle` is joined explicitly.

</div>

## Exercises

1. Add arrival times to the jobs of Listing 31.1, so that a job is inserted into the heap only when the clock reaches its arrival time. Print the turnaround time of every job under each policy.
2. Add a new job of time 1 at every slice, and show that a job of time 8 never completes under `Policy::Sjf`. Then add **aging**: subtract the time a job has waited from its rank, and show that the job of time 8 now completes.
3. Run Listing 31.2 with 1, 2, and 4 workers, and record the order of the results under each policy. Explain each order with a timeline like figure 31.2.
4. Keep the `ScopedJoinHandle` of every worker in Listing 31.3 and join each one, so that `schedule` returns the first error of any worker. Return `Ok(())` from a worker when the heap is empty, so that an empty heap is no longer reported as an error.
