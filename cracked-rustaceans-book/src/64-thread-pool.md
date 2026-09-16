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

```rust
use std::sync::{mpsc, Arc, Mutex};
use std::thread;

type Job = Box<dyn FnOnce() + Send + 'static>;

pub struct ThreadPool {
    sender: mpsc::Sender<Job>,
    workers: Vec<thread::JoinHandle<()>>,
}

impl ThreadPool {
    pub fn new(size: usize) -> Self {
        let (sender, receiver) = mpsc::channel::<Job>();
        let receiver = Arc::new(Mutex::new(receiver));

        let workers = (0..size)
            .map(|_| {
                let rx = Arc::clone(&receiver);
                thread::spawn(move || {
                    while let Ok(job) = rx.lock().unwrap().recv() {
                        job();
                    }
                })
            })
            .collect();

        Self { sender, workers }
    }

    pub fn execute(&self, job: Job) {
        self.sender.send(job).unwrap();
    }

    pub fn join(self) {
        drop(self.sender);
        for w in self.workers {
            let _ = w.join();
        }
    }
}

fn main() {
    let pool = ThreadPool::new(4);
    for i in 0..100 {
        pool.execute(Box::new(move || println!("task {i}")));
    }

    pool.join();
}
```

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

```rust
//! Thread pool, version 2: workers really run in parallel.
//!
//! Version 1 (`src/bin/thread_pool.rs`) holds the receiver's lock while a job runs,
//! because the `MutexGuard` in `while let Ok(job) = rx.lock().unwrap().recv()` lives
//! until the end of the loop body. This version takes the job in its own `let`
//! statement, so the guard is dropped before the job starts.
//!
//! It also accepts any closure in `execute`, so callers no longer write `Box::new`.

use std::sync::{Arc, Mutex, mpsc};
use std::thread;

type Job = Box<dyn FnOnce() + Send + 'static>;

pub struct ThreadPool {
    sender: mpsc::Sender<Job>,
    workers: Vec<thread::JoinHandle<()>>,
}

impl ThreadPool {
    /// Start `size` workers. Panics if `size` is zero.
    pub fn new(size: usize) -> Self {
        assert!(size > 0, "a thread pool needs at least one worker");

        let (sender, receiver) = mpsc::channel::<Job>();
        let receiver = Arc::new(Mutex::new(receiver));

        let workers = (0..size)
            .map(|_| {
                let receiver = Arc::clone(&receiver);
                thread::spawn(move || {
                    loop {
                        // The guard is a temporary of this `let` statement, so the
                        // lock is released here, before the job runs.
                        let job = receiver.lock().unwrap().recv();
                        match job {
                            Ok(job) => job(),
                            Err(_) => break, // every sender is gone: shut down
                        }
                    }
                })
            })
            .collect();

        Self { sender, workers }
    }

    /// Queue a closure to run on the next free worker.
    pub fn execute<F>(&self, job: F)
    where
        F: FnOnce() + Send + 'static,
    {
        self.sender.send(Box::new(job)).unwrap();
    }

    /// Stop accepting jobs, let the workers drain the queue, and wait for them.
    pub fn join(self) {
        drop(self.sender);
        for worker in self.workers {
            let _ = worker.join();
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Barrier;
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::time::Duration;

    #[test]
    fn runs_every_job() {
        let pool = ThreadPool::new(4);
        let counter = Arc::new(AtomicUsize::new(0));
        for _ in 0..100 {
            let counter = Arc::clone(&counter);
            pool.execute(move || {
                counter.fetch_add(1, Ordering::Relaxed);
            });
        }
        pool.join();
        assert_eq!(counter.load(Ordering::Relaxed), 100);
    }

    #[test]
    fn jobs_run_at_the_same_time() {
        // Four jobs wait on a barrier for four parties. They can only all get
        // through if four workers run them at once; version 1 would never finish.
        let pool = ThreadPool::new(4);
        let barrier = Arc::new(Barrier::new(4));
        let (done_tx, done_rx) = mpsc::channel();

        for _ in 0..4 {
            let barrier = Arc::clone(&barrier);
            let done_tx = done_tx.clone();
            pool.execute(move || {
                barrier.wait();
                done_tx.send(()).unwrap();
            });
        }

        for _ in 0..4 {
            done_rx
                .recv_timeout(Duration::from_secs(5))
                .expect("jobs did not run in parallel");
        }
        pool.join();
    }

    #[test]
    #[should_panic(expected = "at least one worker")]
    fn zero_workers_is_rejected() {
        let _ = ThreadPool::new(0);
    }
}
```

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

```rust
//! Thread pool, version 3: errors instead of panics, and shutdown on drop.
//!
//! - `new` returns `Err(PoolError::NoWorkers)` for a size of zero.
//! - `execute` returns `Err(PoolError::ShutDown)` once the pool no longer accepts work.
//! - Dropping the pool closes the queue and joins every worker, so a pool that goes
//!   out of scope still finishes the jobs it was given.

use std::fmt;
use std::sync::{Arc, Mutex, mpsc};
use std::thread;

type Job = Box<dyn FnOnce() + Send + 'static>;

/// Why the pool refused a request.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PoolError {
    NoWorkers,
    ShutDown,
}

impl fmt::Display for PoolError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::NoWorkers => write!(f, "a thread pool needs at least one worker"),
            Self::ShutDown => write!(f, "the thread pool has shut down"),
        }
    }
}

impl std::error::Error for PoolError {}

pub struct ThreadPool {
    // `None` after shutdown: dropping the sender is what tells workers to stop.
    sender: Option<mpsc::Sender<Job>>,
    workers: Vec<thread::JoinHandle<()>>,
}

impl ThreadPool {
    /// Start `size` workers.
    pub fn new(size: usize) -> Result<Self, PoolError> {
        if size == 0 {
            return Err(PoolError::NoWorkers);
        }

        let (sender, receiver) = mpsc::channel::<Job>();
        let receiver = Arc::new(Mutex::new(receiver));

        let workers = (0..size)
            .map(|_| {
                let receiver = Arc::clone(&receiver);
                thread::spawn(move || worker_loop(&receiver))
            })
            .collect();

        Ok(Self {
            sender: Some(sender),
            workers,
        })
    }

    /// Queue a closure to run on the next free worker.
    pub fn execute<F>(&self, job: F) -> Result<(), PoolError>
    where
        F: FnOnce() + Send + 'static,
    {
        self.sender
            .as_ref()
            .ok_or(PoolError::ShutDown)?
            .send(Box::new(job))
            .map_err(|_| PoolError::ShutDown)
    }

    /// Stop accepting jobs, drain the queue, and wait for every worker.
    /// Calling it again does nothing.
    pub fn shutdown(&mut self) {
        drop(self.sender.take());
        for worker in self.workers.drain(..) {
            let _ = worker.join();
        }
    }
}

impl Drop for ThreadPool {
    fn drop(&mut self) {
        self.shutdown();
    }
}

fn worker_loop(receiver: &Mutex<mpsc::Receiver<Job>>) {
    loop {
        // A poisoned lock means another worker panicked while holding it;
        // stop this worker instead of panicking a second time.
        let Ok(guard) = receiver.lock() else { return };
        let job = guard.recv();
        drop(guard);

        match job {
            Ok(job) => job(),
            Err(_) => return,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    #[test]
    fn zero_workers_is_an_error() {
        assert_eq!(ThreadPool::new(0).err(), Some(PoolError::NoWorkers));
    }

    #[test]
    fn dropping_the_pool_finishes_queued_jobs() {
        let counter = Arc::new(AtomicUsize::new(0));
        {
            let pool = ThreadPool::new(2).unwrap();
            for _ in 0..50 {
                let counter = Arc::clone(&counter);
                pool.execute(move || {
                    counter.fetch_add(1, Ordering::Relaxed);
                })
                .unwrap();
            }
        } // drop: close the queue and join
        assert_eq!(counter.load(Ordering::Relaxed), 50);
    }

    #[test]
    fn execute_after_shutdown_is_an_error() {
        let mut pool = ThreadPool::new(1).unwrap();
        pool.shutdown();
        assert_eq!(pool.execute(|| {}), Err(PoolError::ShutDown));
        pool.shutdown(); // idempotent
    }

    #[test]
    fn errors_render_a_message() {
        assert_eq!(
            PoolError::NoWorkers.to_string(),
            "a thread pool needs at least one worker"
        );
        assert_eq!(
            PoolError::ShutDown.to_string(),
            "the thread pool has shut down"
        );
    }
}
```

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

```rust
//! Thread pool, version 4: survives panicking jobs and reports what happened.
//!
//! - Workers are named threads created with `thread::Builder`, and a failure to
//!   spawn one is returned as `PoolError::Spawn` after the already started workers
//!   are shut down.
//! - Each job runs inside `catch_unwind`, so a panicking job no longer kills its
//!   worker and silently shrinks the pool.
//! - `shutdown` consumes the pool and returns a `Report` with the number of jobs
//!   that completed and the number that panicked.

use std::fmt;
use std::io;
use std::panic::{self, AssertUnwindSafe};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex, mpsc};
use std::thread;

type Job = Box<dyn FnOnce() + Send + 'static>;

/// Why the pool could not be created or refused a job.
#[derive(Debug)]
pub enum PoolError {
    NoWorkers,
    Spawn(io::Error),
    ShutDown,
}

impl fmt::Display for PoolError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::NoWorkers => write!(f, "a thread pool needs at least one worker"),
            Self::Spawn(error) => write!(f, "failed to spawn a worker thread: {error}"),
            Self::ShutDown => write!(f, "the thread pool has shut down"),
        }
    }
}

impl std::error::Error for PoolError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Spawn(error) => Some(error),
            _ => None,
        }
    }
}

/// What the pool did over its lifetime.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Report {
    pub completed: usize,
    pub panicked: usize,
}

#[derive(Default)]
struct Counters {
    completed: AtomicUsize,
    panicked: AtomicUsize,
}

pub struct ThreadPool {
    sender: Option<mpsc::Sender<Job>>,
    workers: Vec<thread::JoinHandle<()>>,
    counters: Arc<Counters>,
}

impl ThreadPool {
    /// Start `size` named workers.
    pub fn new(size: usize) -> Result<Self, PoolError> {
        if size == 0 {
            return Err(PoolError::NoWorkers);
        }

        let (sender, receiver) = mpsc::channel::<Job>();
        let receiver = Arc::new(Mutex::new(receiver));
        let counters = Arc::new(Counters::default());

        let mut pool = Self {
            sender: Some(sender),
            workers: Vec::with_capacity(size),
            counters,
        };

        for id in 0..size {
            let receiver = Arc::clone(&receiver);
            let counters = Arc::clone(&pool.counters);
            let spawned = thread::Builder::new()
                .name(format!("pool-worker-{id}"))
                .spawn(move || worker_loop(&receiver, &counters));

            match spawned {
                Ok(handle) => pool.workers.push(handle),
                // Dropping `pool` here closes the queue and joins the workers
                // that did start, so none of them is leaked.
                Err(error) => return Err(PoolError::Spawn(error)),
            }
        }

        Ok(pool)
    }

    /// Queue a closure to run on the next free worker.
    pub fn execute<F>(&self, job: F) -> Result<(), PoolError>
    where
        F: FnOnce() + Send + 'static,
    {
        self.sender
            .as_ref()
            .ok_or(PoolError::ShutDown)?
            .send(Box::new(job))
            .map_err(|_| PoolError::ShutDown)
    }

    /// Close the queue, wait for every queued job, and report the outcome.
    pub fn shutdown(mut self) -> Report {
        self.close_and_join();
        Report {
            completed: self.counters.completed.load(Ordering::Relaxed),
            panicked: self.counters.panicked.load(Ordering::Relaxed),
        }
    }

    fn close_and_join(&mut self) {
        drop(self.sender.take());
        for worker in self.workers.drain(..) {
            // Jobs cannot unwind out of `worker_loop`, so a join error would mean
            // a bug in the loop itself; there is nothing further to clean up.
            let _ = worker.join();
        }
    }
}

impl Drop for ThreadPool {
    fn drop(&mut self) {
        self.close_and_join();
    }
}

fn worker_loop(receiver: &Mutex<mpsc::Receiver<Job>>, counters: &Counters) {
    loop {
        let Ok(guard) = receiver.lock() else { return };
        let job = guard.recv();
        drop(guard);

        let Ok(job) = job else { return };

        // `AssertUnwindSafe` is sound here: the job owns everything it touches,
        // and a panicking job's partial state is never observed by this loop.
        match panic::catch_unwind(AssertUnwindSafe(job)) {
            Ok(()) => counters.completed.fetch_add(1, Ordering::Relaxed),
            Err(_) => counters.panicked.fetch_add(1, Ordering::Relaxed),
        };
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::error::Error;
    use std::sync::mpsc::channel;
    use std::time::Duration;

    #[test]
    fn reports_completed_jobs() {
        let pool = ThreadPool::new(4).unwrap();
        for _ in 0..20 {
            pool.execute(|| {}).unwrap();
        }
        assert_eq!(
            pool.shutdown(),
            Report {
                completed: 20,
                panicked: 0
            }
        );
    }

    #[test]
    fn a_panicking_job_does_not_kill_its_worker() {
        // One worker: if the panic killed it, the second job would never run.
        let pool = ThreadPool::new(1).unwrap();
        let (done_tx, done_rx) = channel();

        pool.execute(|| panic!("job failed on purpose")).unwrap();
        pool.execute(move || done_tx.send(()).unwrap()).unwrap();

        done_rx
            .recv_timeout(Duration::from_secs(5))
            .expect("the worker died with the panicking job");
        assert_eq!(
            pool.shutdown(),
            Report {
                completed: 1,
                panicked: 1
            }
        );
    }

    #[test]
    fn workers_are_named() {
        let pool = ThreadPool::new(1).unwrap();
        let (name_tx, name_rx) = channel();
        pool.execute(move || {
            let name = thread::current().name().map(str::to_string);
            name_tx.send(name).unwrap();
        })
        .unwrap();
        assert_eq!(name_rx.recv().unwrap().as_deref(), Some("pool-worker-0"));
    }

    #[test]
    fn zero_workers_is_an_error() {
        assert!(matches!(ThreadPool::new(0), Err(PoolError::NoWorkers)));
    }

    #[test]
    fn spawn_errors_expose_their_source() {
        let error = PoolError::Spawn(io::Error::other("no threads left"));
        assert!(error.to_string().contains("no threads left"));
        assert!(error.source().is_some());
        assert!(PoolError::ShutDown.source().is_none());
    }
}
```

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
