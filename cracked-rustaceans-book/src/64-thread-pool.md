# 64. Thread Pool - Workers of the Pool Assemble {#thread-pool}

*Source files: [`src/bin/thread_pool.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/thread_pool.rs), [`src/problems/thread_pool_v2.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/thread_pool_v2.rs), [`src/problems/thread_pool_v3.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/thread_pool_v3.rs), and [`src/problems/thread_pool_v4.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/thread_pool_v4.rs). Run the first with `cargo run --bin thread_pool`, and test the others with `cargo test thread_pool`.*

## Problem Statement

Build a pool of worker threads that runs submitted closures. A caller creates the pool
with a fixed number of workers, submits jobs with `execute`, and eventually shuts the pool
down, at which point every job already submitted must still run.

This chapter builds the pool four times. The first version is short enough to write in
a few minutes. Each later version fixes one problem with the one before it, and adds the
tests that prove the fix:

| Version | What it adds |
|---|---|
| 1 | a working pool in under fifty lines |
| 2 | jobs that really run in parallel, and closures without `Box::new` |
| 3 | errors instead of panics, and shutdown when the pool is dropped |
| 4 | workers that survive panicking jobs, named threads, spawn errors, and a report |

## Designing a Solution

All four versions share one design. A channel carries jobs from the pool to the workers,
and each job is a boxed closure:

```text
type Job = Box<dyn FnOnce() + Send + 'static>;

caller --execute--> Sender<Job> ===channel===> Receiver<Job>
                                                   |
                                        Arc<Mutex<Receiver<Job>>>
                                     /        |          |        \
                               worker 0   worker 1   worker 2   worker 3
                               loop: take a job, run it
```

`FnOnce` lets a job consume what it captures. `Send` lets it move to a worker thread.
`'static` means it borrows nothing from the caller's stack, because the worker may run it
after the caller's function has returned.

An `mpsc::Receiver` has a single owner, so the workers share it through
`Arc<Mutex<Receiver<Job>>>`: `Arc` gives each worker a handle, and the `Mutex` lets one
worker at a time wait in `recv`.

Shutdown uses the channel itself. When the last `Sender` is dropped, `recv` returns
`Err` once the queue is empty, and each worker's loop ends. Joining the workers then waits
until every queued job has run.

## Implementation

### Version 1: the pool in a few lines

<p class="listing"><span class="listing-label">Listing 64.1</span> Version 1: the pool in a few lines. <code>src/bin/thread_pool.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/thread_pool.rs">read the file on GitHub</a></p>

`new` creates the channel, wraps the receiver, and spawns `size` workers with an iterator
that collects their `JoinHandle`s. Each worker loops with `while let Ok(job) =
rx.lock().unwrap().recv()` and runs the job. `execute` sends a boxed job. `join` takes
`self` by value, drops the sender to close the channel, and joins every worker.

The program queues 100 jobs that print their number, and prints all 100 lines before it
exits.

The version works, and it has one surprising property: **the jobs run one at a time.**
The condition of a `while let` is a single expression, and temporaries created in it live
until the end of the loop body. The `MutexGuard` returned by `rx.lock().unwrap()` is such
a temporary, so the worker keeps the receiver locked while `job()` runs. Every other
worker waits for that lock, and four workers behave like one.

A measurement makes it visible. Submitting eight jobs that each sleep for 100 ms to a pool
of four workers should take about 200 ms. With version 1 it took **801 ms** on the NVIDIA
Jetson board used for this book, which is eight jobs in sequence.

The other issues are smaller:

- `ThreadPool::new(0)` creates a pool that accepts jobs and never runs them.
- Callers must write `Box::new` around every closure.
- `execute` and every worker call `unwrap`, so a failure becomes a panic.
- A panicking job kills its worker, and the pool silently shrinks.
- If the caller forgets `join`, the program can exit before queued jobs run.

### Version 2: parallel workers

<p class="listing"><span class="listing-label">Listing 64.2</span> Version 2: parallel workers. <code>src/problems/thread_pool_v2.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/thread_pool_v2.rs">read the file on GitHub</a></p>

The fix for the lock is one line moved into its own statement:

```rust
let job = receiver.lock().unwrap().recv();
match job {
    Ok(job) => job(),
    Err(_) => break,
}
```

Temporaries in a `let` statement are dropped at the end of that statement, so the guard is
released as soon as `recv` returns, before `job()` runs. The same eight 100 ms jobs now take
**201 ms**, four times faster, with no other change to the design.

`execute` is now generic over `F: FnOnce() + Send + 'static` and boxes the closure itself,
so callers write `pool.execute(move || ...)`. `new` asserts that `size` is positive.

The test `jobs_run_at_the_same_time` proves parallelism without timing. Four jobs wait on a
`Barrier` for four parties, which only opens when all four are waiting at once. With version
2 they pass the barrier and report back; with version 1 the first job would wait forever,
so the test uses `recv_timeout` to fail instead of hanging.

### Version 3: errors and shutdown on drop

<p class="listing"><span class="listing-label">Listing 64.3</span> Version 3: errors and shutdown on drop. <code>src/problems/thread_pool_v3.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/thread_pool_v3.rs">read the file on GitHub</a></p>

**Errors are values.** `PoolError` has two variants. `new` returns `Err(NoWorkers)` for a
size of zero, and `execute` returns `Err(ShutDown)` when the pool no longer accepts work. The
type implements `Display` and `std::error::Error`, so a caller can use `?` and print a
readable message.

**The sender is an `Option`.** `shutdown` takes the sender out with `self.sender.take()` and
drops it, then drains and joins the workers. Because the field is `None` afterwards,
calling `shutdown` again does nothing, and `execute` reports `ShutDown` through
`self.sender.as_ref().ok_or(PoolError::ShutDown)?`.

**Dropping the pool shuts it down.** `impl Drop for ThreadPool` calls `shutdown`. A pool that
goes out of scope, including during an early return or a panic in the caller, still closes
its queue and waits for the jobs it was given. The test
`dropping_the_pool_finishes_queued_jobs` submits fifty jobs inside a block and checks the
counter after the block ends.

**The worker loop has no `unwrap`.** `let Ok(guard) = receiver.lock() else { return };` ends the
worker if the lock is poisoned instead of panicking again, and `drop(guard)` releases the
lock explicitly before the job runs, which states the fix from version 2 in code rather than
relying on the temporary rule.

### Version 4: survive panics and report the outcome

<p class="listing"><span class="listing-label">Listing 64.4</span> Version 4: survive panics and report the outcome. <code>src/problems/thread_pool_v4.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/thread_pool_v4.rs">read the file on GitHub</a></p>

**A panicking job no longer kills its worker.** The worker runs each job inside
`panic::catch_unwind(AssertUnwindSafe(job))`. A panic unwinds only to that call, which returns
`Err`, and the worker continues with the next job. `AssertUnwindSafe` tells the compiler that
observing state after a panic is acceptable; here the job owns what it captured and the loop
never looks at it. The test `a_panicking_job_does_not_kill_its_worker` uses a single worker, so
the job after the panic can only run if that worker survived.

**Outcomes are counted.** A shared `Counters` struct holds two `AtomicUsize` values that the
workers increment after each job. `shutdown(self)` consumes the pool, joins every worker, and
returns a `Report { completed, panicked }`. Because `shutdown` takes the pool by value,
calling `execute` after it is a compile error rather than a run-time `ShutDown`.

**Workers are named, and spawn failures are errors.** `thread::Builder::new().name(...)`
names each worker `pool-worker-N`, which appears in panic messages and debuggers.
`Builder::spawn` returns `io::Result`, unlike `thread::spawn`, which panics. When a spawn
fails, `new` returns `Err(PoolError::Spawn(error))`. The partially built `pool` is dropped on
that `return`, and its `Drop` implementation closes the queue and joins the workers that did
start, so none of them leaks. `Error::source` exposes the underlying `io::Error`.

## Intuition

**Version 1 against version 2: eight jobs of 100 ms on four workers**

```text
version 1, lock held while the job runs

time (ms)   0    100   200   300   400   500   600   700   800
worker 0    [job][job]
worker 1              [job][job]
worker 2                          [job][job]
worker 3                                      [job][job]
            each worker waits for the lock the previous one holds    total 801 ms

version 2, lock released before the job runs

time (ms)   0    100   200
worker 0    [job][job]
worker 1    [job][job]
worker 2    [job][job]
worker 3    [job][job]
                                                                     total 201 ms
```

The exact assignment of jobs to workers varies between runs; the totals do not.

**Version 4: one worker, a panicking job followed by a normal one**

| step | worker | counters |
|---|---|---|
| `execute(panicking job)` | receives it, `catch_unwind` returns `Err` | panicked = 1 |
| `execute(send on channel)` | receives it, runs it, returns `Ok` | completed = 1 |
| `shutdown()` | `recv` returns `Err`, loop ends, thread joined | `Report { completed: 1, panicked: 1 }` |

## Time and Space Complexity

| Operation | Cost | Condition |
|---|---|---|
| `new` | `O(n)` thread creations | `n` workers |
| `execute` | `O(1)`: one allocation for the box and one channel send | |
| per job | one lock acquisition and one `recv` on the worker side | version 2 onwards: the lock is not held while the job runs |
| shutdown | waits for every queued job, then `O(n)` joins | |
| memory | one stack per worker, one box per queued job | the queue is unbounded |

## Limitations

**The queue is unbounded.** `mpsc::channel` never blocks the sender, so a producer faster than
the workers grows the queue without limit. `mpsc::sync_channel(bound)`, or the bounded queue of
chapter 46, makes `execute` wait instead.

**Workers contend on one lock.** Every worker takes the same `Mutex` to receive. For short jobs
at high rates this lock becomes the bottleneck. A multi-consumer channel such as
`crossbeam-channel`, or a work-stealing pool such as `rayon`, avoids it.

**Jobs return nothing.** A caller that needs a result must send it back itself, as the tests
do with channels. A pool that returns a handle per job, similar to `JoinHandle<T>`, would
carry the result and the panic.

**`catch_unwind` does not catch everything.** A job that aborts the process, overflows its
stack, or panics while `panic = "abort"` is configured still ends the program. Version 4
protects the pool from ordinary panics only.

**Shutdown waits for every job.** None of the versions can cancel queued jobs or interrupt a
running one. A pool that must stop quickly needs a separate stop flag that jobs check.

**Version 1 is kept as written.** Its serial behaviour is the most useful thing to learn from
it, and the later versions exist to explain it.

## Summary

- A thread pool is a channel of boxed `FnOnce() + Send + 'static` jobs and workers that share
  the receiver through `Arc<Mutex<Receiver<Job>>>`.
- Temporaries in a `while let` condition live for the whole loop body. Holding the
  `MutexGuard` there made version 1 run jobs one at a time; taking the job in a separate `let`
  statement made the same work four times faster.
- Returning `Result` from `new` and `execute`, and shutting down in `Drop`, turns panics into
  values and makes a dropped pool finish its work.
- `catch_unwind` keeps a panicking job from killing its worker, `thread::Builder` names workers
  and reports spawn failures, and a consuming `shutdown` can return what happened.
- A `Barrier` tests parallelism without timing, and a single-worker pool tests survival after
  a panic.

## References

- The Rust Programming Language, [Final Project: Building a Multithreaded Web Server](https://doc.rust-lang.org/book/ch21-00-final-project-a-web-server.html), which builds a similar pool and discusses the `while let` lock issue.
- The Rust Reference, [Temporary scopes](https://doc.rust-lang.org/reference/destructors.html#temporary-scopes).
- Standard library, [`std::sync::mpsc`](https://doc.rust-lang.org/std/sync/mpsc/index.html), [`std::sync::Barrier`](https://doc.rust-lang.org/std/sync/struct.Barrier.html), and [`std::thread::Builder`](https://doc.rust-lang.org/std/thread/struct.Builder.html).
- Standard library, [`std::panic::catch_unwind`](https://doc.rust-lang.org/std/panic/fn.catch_unwind.html).
