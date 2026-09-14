# 56. A Minimal Async Runtime {#async-runtime}

*Source files: [`src/problems/async_mini.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/async_mini.rs) and [`src/bin/async_demo.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/async_demo.rs). Run the tests with `cargo test async_mini` and the demonstration with `cargo run --bin async_demo`.*

## Problem Statement

Using only the standard library:

1. Implement `block_on(future)`, which runs a future on the current thread and returns
   its output, without spinning while the future is waiting.
2. Implement two futures by hand: one that yields a given number of times before it
   completes, and one that completes after a wall-clock delay.
3. Implement an executor that runs several spawned tasks, each polled again only after
   it has been woken.

## Designing a Solution

**The contract.** A future has one method:

```text
fn poll(self: Pin<&mut Self>, cx: &mut Context<'_>) -> Poll<Self::Output>
```

`Poll::Ready(value)` means the future is finished. `Poll::Pending` means it cannot make
progress now, and it carries an obligation: before returning `Pending`, the future must
arrange for `cx.waker()` to be called when progress becomes possible. A runtime that
receives `Pending` does not poll that future again until its waker is called.

**Pinning.** An `async` block that holds a reference to one of its own local variables
across an `.await` becomes a self-referential struct. Moving it would invalidate the
reference. `Pin<&mut Self>` promises the future that it will not be moved again, which
is why `poll` receives a pinned reference and why runtimes pin futures, typically with
`Box::pin`, before polling them.

**A waker for a thread.** `block_on` has one future and one thread. Its waker can simply
unpark that thread. The loop polls, and on `Pending` parks the thread until the waker
unparks it.

**A waker for a task.** An executor with many tasks keeps a queue of tasks ready to be
polled. A task's waker pushes the task back onto that queue. The executor pops a task,
polls it, and moves on; a task that returned `Pending` is not in the queue until
something wakes it.

The diagram below shows the executor's cycle.

```text
spawn(future) ---> queue: [task]
                      |
                      v
run: pop task ---> poll(future, Context with waker = task)
                      |
          +-----------+------------------+
          v                              v
   Poll::Ready                     Poll::Pending
   mark completed                  the future stored or called the waker
                                         |
                           waker.wake() pushes the task back onto the queue
```

## Implementation

### `block_on`

```rust
//! A minimal async runtime, built from `Future`, `Waker`, and `Pin`.
//!
//! `.await` is not magic. A `Future` is a state machine with one method, `poll`,
//! that returns `Ready(value)` or `Pending`; when it returns `Pending` it must
//! arrange for the `Waker` in its `Context` to be called later. An executor is a
//! loop that polls tasks and parks until a waker fires.
//!
//! This module implements that loop twice, from scratch and without a runtime
//! dependency:
//!
//! - [`block_on`] drives one future on the current thread, parking on `Pending`;
//! - [`MiniExecutor`] queues independent tasks and re-enqueues them when woken.
//!
//! It is deliberately small. What it makes concrete is the part interviewers ask
//! about: why `poll` takes `Pin<&mut Self>`, what `Pending` promises, and where
//! `Send` matters for a multi-threaded runtime.

use std::collections::VecDeque;
use std::future::Future;
use std::pin::Pin;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Mutex};
use std::task::{Context, Poll, Wake, Waker};
use std::thread;
use std::time::Duration;

/// Block the current thread until `future` completes.
///
/// The future is pinned on the heap so its address is stable across `await`
/// points, and the thread parks whenever the future reports `Pending`. The waker
/// unparks it, so the loop polls again only when there is a reason to.
pub fn block_on<F: Future>(future: F) -> F::Output {
    let mut future = Box::pin(future);
    let waker = Waker::from(Arc::new(ThreadWaker(thread::current())));
    let mut context = Context::from_waker(&waker);

    loop {
        match future.as_mut().poll(&mut context) {
            Poll::Ready(value) => return value,
            // `park` may return spuriously, so the loop re-polls either way.
            Poll::Pending => thread::park(),
        }
    }
}

/// Waker that unparks the thread which is driving the future.
struct ThreadWaker(thread::Thread);

impl Wake for ThreadWaker {
    fn wake(self: Arc<Self>) {
        self.0.unpark();
    }

    fn wake_by_ref(self: &Arc<Self>) {
        self.0.unpark();
    }
}
```

`Box::pin(future)` moves the future to the heap and returns `Pin<Box<F>>`. After that
the future's address does not change, so `poll` may be called on it repeatedly.
`future.as_mut()` produces the `Pin<&mut F>` that `poll` requires, without moving the box.

`Waker::from(Arc::new(ThreadWaker(thread::current())))` builds a waker from any type that
implements the `Wake` trait, stable since Rust 1.51. Before `Wake`, building a waker
required a hand-written virtual function table and `unsafe` code.

`thread::park` is safe against a lost wake-up. If the waker calls `unpark` before the
thread parks, the thread receives a token, and the next `park` returns immediately.
`park` may also return spuriously, which the loop tolerates because it simply polls again.

### A future that yields

```rust
/// A future that yields to the executor `times` times before completing.
///
/// Completes with the number of times it yielded, which makes it easy to assert
/// that a runtime actually suspended and resumed a task.
pub struct YieldTimes {
    remaining: usize,
    yielded: usize,
}

impl YieldTimes {
    pub fn new(times: usize) -> Self {
        Self {
            remaining: times,
            yielded: 0,
        }
    }
}

impl Future for YieldTimes {
    type Output = usize;

    fn poll(self: Pin<&mut Self>, context: &mut Context<'_>) -> Poll<usize> {
        // `YieldTimes` is `Unpin`, so a mutable reference is safe to take.
        let this = self.get_mut();
        if this.remaining == 0 {
            return Poll::Ready(this.yielded);
        }

        this.remaining -= 1;
        this.yielded += 1;
        // Ask to be polled again; an executor that ignores this hangs.
        context.waker().wake_by_ref();
        Poll::Pending
    }
}
```

`YieldTimes` contains only two `usize` fields, so it implements `Unpin`, and
`self.get_mut()` can turn `Pin<&mut Self>` back into `&mut Self` without `unsafe` code.

Each `Pending` result is preceded by `context.waker().wake_by_ref()`. The future asks to be
polled again immediately. Returning `Pending` without arranging a wake-up would leave the
future suspended forever, which is the most common bug in hand-written futures.

### A future that waits for time

```rust
struct DelayState {
    ready: bool,
    waker: Option<Waker>,
}

/// A future that completes after a wall-clock duration.
///
/// A background thread sleeps and then wakes the task. Storing and waking the
/// [`Waker`] — rather than spinning in `poll` — is the whole point: `poll` never
/// blocks the executor thread.
pub struct Delay {
    state: Arc<Mutex<DelayState>>,
}

impl Delay {
    pub fn new(duration: Duration) -> Self {
        let state = Arc::new(Mutex::new(DelayState {
            ready: false,
            waker: None,
        }));

        let thread_state = Arc::clone(&state);
        thread::spawn(move || {
            thread::sleep(duration);
            let waker = {
                let mut guard = thread_state.lock().expect("delay mutex poisoned");
                guard.ready = true;
                guard.waker.take()
            };
            if let Some(waker) = waker {
                waker.wake();
            }
        });

        Self { state }
    }
}

impl Future for Delay {
    type Output = ();

    fn poll(self: Pin<&mut Self>, context: &mut Context<'_>) -> Poll<()> {
        let mut guard = self.state.lock().expect("delay mutex poisoned");
        if guard.ready {
            Poll::Ready(())
        } else {
            guard.waker = Some(context.waker().clone());
            Poll::Pending
        }
    }
}
```

`Delay::new` starts a thread that sleeps and then sets `ready` and takes the stored waker,
both under the mutex. `poll` checks `ready` and stores a clone of the current waker, also
under the mutex. Because both sides hold the lock while they read or write the shared
state, there is no moment at which the timer thread can see "no waker yet" after `poll`
has decided to return `Pending`. Without the lock, a wake-up could be lost.

`poll` replaces the stored waker on every call. A future may be polled with a different
waker each time, for example after being moved to another task, and it must wake the most
recent one.

The timer thread calls `waker.wake()` after releasing the lock. Calling a waker while
holding a lock the woken task might also need is a common source of deadlock.

### The executor

```rust
struct Task {
    future: Mutex<Pin<Box<dyn Future<Output = ()> + Send>>>,
    queue: Arc<Mutex<VecDeque<Arc<Task>>>>,
    completed: AtomicBool,
}

impl Wake for Task {
    fn wake(self: Arc<Self>) {
        // Re-enqueue the task. Cloning the `Arc` is a refcount bump, not a deep copy.
        self.queue
            .lock()
            .expect("executor queue poisoned")
            .push_back(Arc::clone(&self));
    }

    fn wake_by_ref(self: &Arc<Self>) {
        self.queue
            .lock()
            .expect("executor queue poisoned")
            .push_back(Arc::clone(self));
    }
}

/// A single-threaded, `Send`-only executor.
///
/// Real runtimes add work stealing, timers, and I/O readiness. This keeps only the
/// part that matters for explaining how `.await` makes progress: a queue of tasks
/// where waking a task puts it back on the queue.
#[derive(Default)]
pub struct MiniExecutor {
    queue: Arc<Mutex<VecDeque<Arc<Task>>>>,
}

impl MiniExecutor {
    pub fn new() -> Self {
        Self::default()
    }

    /// Add a task to the executor.
    pub fn spawn<F>(&self, future: F)
    where
        F: Future<Output = ()> + Send + 'static,
    {
        let task = Arc::new(Task {
            future: Mutex::new(Box::pin(future)),
            queue: Arc::clone(&self.queue),
            completed: AtomicBool::new(false),
        });
        self.queue
            .lock()
            .expect("executor queue poisoned")
            .push_back(task);
    }

    /// Run until the queue is empty.
    ///
    /// A task that returns `Pending` without waking stays suspended, which is why
    /// this returns rather than blocks: a runtime with timers or I/O would also
    /// park on an event source.
    pub fn run(&self) {
        loop {
            let Some(task) = self
                .queue
                .lock()
                .expect("executor queue poisoned")
                .pop_front()
            else {
                return;
            };

            if task.completed.load(Ordering::Acquire) {
                continue;
            }

            let waker = Waker::from(Arc::clone(&task));
            let mut context = Context::from_waker(&waker);
            let mut future = task.future.lock().expect("task mutex poisoned");
            if future.as_mut().poll(&mut context).is_ready() {
                task.completed.store(true, Ordering::Release);
            }
        }
    }
}
```

A `Task` holds its future as `Mutex<Pin<Box<dyn Future<Output = ()> + Send>>>`. The
`Wake` trait requires `Arc<Task>` to be `Send` and `Sync`, because a waker may be called
from any thread. The `Mutex` makes the task `Sync`; the `Send` bound on the future makes it
safe to poll the future from whichever thread holds the lock.

`spawn` requires `F: Future<Output = ()> + Send + 'static`. The future is stored in the
task and outlives the call to `spawn`, so it cannot borrow from the caller, and it may be
polled after a wake from another thread, so it must be `Send`. These are the same bounds
that `tokio::spawn` imposes, for the same reasons.

`run` pops tasks until the queue is empty. `let Some(task) = ... else { return; }` takes
the queue lock only for the `pop_front`, because the temporary guard is dropped at the end
of the `let` statement. The lock must not be held while polling, because a future that
wakes itself during `poll`, as `YieldTimes` does, pushes onto the same queue.

The `completed` flag handles a task that is woken after it has finished. Its waker may
still exist, held by a timer or a clone, and pushing it onto the queue must not poll a
completed future again.

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::AtomicUsize;
    use std::time::Instant;

    #[test]
    fn block_on_drives_a_hand_written_future() {
        assert_eq!(block_on(YieldTimes::new(3)), 3);
    }

    #[test]
    fn block_on_polls_an_async_block() {
        let total = block_on(async {
            let a = YieldTimes::new(1).await;
            let b = YieldTimes::new(2).await;
            a + b
        });
        assert_eq!(total, 3);
    }

    #[test]
    fn block_on_waits_for_a_delay() {
        let start = Instant::now();
        block_on(Delay::new(Duration::from_millis(30)));
        assert!(start.elapsed() >= Duration::from_millis(20));
    }

    #[test]
    fn executor_runs_spawned_tasks_to_completion() {
        let executor = MiniExecutor::new();
        let counter = Arc::new(AtomicUsize::new(0));

        for _ in 0..4 {
            let counter = Arc::clone(&counter);
            executor.spawn(async move {
                YieldTimes::new(2).await;
                counter.fetch_add(1, Ordering::SeqCst);
            });
        }

        executor.run();
        assert_eq!(counter.load(Ordering::SeqCst), 4);
    }

    #[test]
    fn executor_polls_an_immediately_ready_task() {
        let executor = MiniExecutor::new();
        let flag = Arc::new(AtomicBool::new(false));

        let task_flag = Arc::clone(&flag);
        executor.spawn(async move {
            task_flag.store(true, Ordering::SeqCst);
        });

        executor.run();
        assert!(flag.load(Ordering::SeqCst));
    }
}
```

````rust
//! Runs the hand-written async runtime in [`nvidia_rust_interview_lab::problems::async_mini`].
//!
//! There is no Tokio here on purpose: the point is to show that `Future`, `Waker`,
//! `Poll`, and `Pin` are enough to build an executor, and that `.await` is just
//! sugar over a state machine that is polled.
//!
//! ```bash
//! cargo run --bin async_demo
//! ```

use nvidia_rust_interview_lab::problems::async_mini::{Delay, MiniExecutor, YieldTimes, block_on};
use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::{Duration, Instant};

fn main() {
    println!("== block_on drives a hand-written future ==");
    let yields = block_on(YieldTimes::new(3));
    println!("YieldTimes suspended and resumed {yields} time(s)");

    println!("\n== block_on drives an async block ==");
    let total = block_on(async {
        let first = YieldTimes::new(1).await;
        let second = YieldTimes::new(2).await;
        first + second
    });
    println!("async block finished with {total}");

    println!("\n== block_on parks the thread until the waker fires ==");
    let start = Instant::now();
    block_on(Delay::new(Duration::from_millis(50)));
    println!("Delay completed after {:?}", start.elapsed());

    println!("\n== MiniExecutor runs independent tasks ==");
    let executor = MiniExecutor::new();
    let completed = Arc::new(AtomicUsize::new(0));

    for id in 1..=3 {
        let completed = Arc::clone(&completed);
        executor.spawn(async move {
            YieldTimes::new(id).await;
            completed.fetch_add(1, Ordering::SeqCst);
            println!("task {id} completed after {id} yield(s)");
        });
    }

    executor.run();
    println!("{} task(s) completed", completed.load(Ordering::SeqCst));
}
````

## Intuition

The demonstration program printed:

```text
== block_on drives a hand-written future ==
YieldTimes suspended and resumed 3 time(s)

== block_on drives an async block ==
async block finished with 3

== block_on parks the thread until the waker fires ==
Delay completed after 50.291507ms

== MiniExecutor runs independent tasks ==
task 1 completed after 1 yield(s)
task 2 completed after 2 yield(s)
task 3 completed after 3 yield(s)
3 task(s) completed
```

**The executor queue while running the three tasks**

| pop | task | poll result | wake | queue after |
|---|---|---|---|---|
| 1 | task 1 | `Pending`, no yields remain | re-enqueue 1 | `[2, 3, 1]` |
| 2 | task 2 | `Pending` | re-enqueue 2 | `[3, 1, 2]` |
| 3 | task 3 | `Pending` | re-enqueue 3 | `[1, 2, 3]` |
| 4 | task 1 | `Ready`, prints | none | `[2, 3]` |
| 5 | task 2 | `Pending` | re-enqueue 2 | `[3, 2]` |
| 6 | task 3 | `Pending` | re-enqueue 3 | `[2, 3]` |
| 7 | task 2 | `Ready`, prints | none | `[3]` |
| 8 | task 3 | `Pending` | re-enqueue 3 | `[3]` |
| 9 | task 3 | `Ready`, prints | none | `[]` |

The round-robin order in the table explains why task 1 finishes first even though all
three started together.

## Time and Space Complexity

| Operation | Cost |
|---|---|
| `block_on` | one poll per wake-up; the thread sleeps between them |
| `YieldTimes` | `times + 1` polls |
| `Delay::new` | one operating-system thread per delay |
| `MiniExecutor::run` | one poll and two queue lock acquisitions per wake-up |
| memory per task | one `Arc<Task>` holding the boxed future, a mutex, and a flag |

## Limitations

**`MiniExecutor::run` returns while tasks are still waiting.** If a spawned task awaits a
`Delay`, its first poll returns `Pending` and the queue empties before the timer fires, so
`run` returns and the task never completes. `block_on` parks instead, and the `Delay`
test therefore uses `block_on`. A complete executor parks on an event source when the queue
is empty and has live tasks.

**One thread per timer.** `Delay` costs an operating-system thread, which defeats the
purpose of an async runtime. Real runtimes keep one timer structure, such as a hashed
wheel, and fire wakers from the event loop.

**A reference cycle can leak tasks.** Each `Task` holds an `Arc` of the queue, and the
queue holds `Arc<Task>` values. If a `MiniExecutor` is dropped while tasks are still
queued, the queue and those tasks keep each other alive and are never freed. Storing a
`Weak` reference to the queue in each task breaks the cycle.

**No `JoinHandle` and no cancellation.** Spawned tasks return `()`, and the caller cannot
wait for one or cancel it. Results must be communicated through shared state, as the
tests do with atomics.

**Single-threaded execution.** `run` polls on the calling thread. The `Send` bounds are in
place for a multi-threaded version, which would need several threads popping from the
queue and, for good performance, per-thread queues with work stealing.

## Summary

- A future returns `Poll::Ready` when done or `Poll::Pending` after arranging for its
  waker to be called; a runtime polls it again only after that call.
- `Pin` guarantees a future will not move, which self-referential `async` state machines
  require, and `Box::pin` provides it.
- `block_on` pairs a poll loop with a waker that unparks the thread, and `thread::park`
  cannot lose an early wake-up.
- A hand-written future that returns `Pending` must store or call the waker, under the
  same lock that the waking side uses.
- An executor is a queue of tasks whose wakers re-enqueue them; `Send + 'static` bounds on
  `spawn` follow from storing tasks and waking them from other threads.

## References

- The Rust Async Book, [Under the hood: executing futures and tasks](https://rust-lang.github.io/async-book/02_execution/01_chapter.html).
- Standard library, [`std::future::Future`](https://doc.rust-lang.org/std/future/trait.Future.html), [`std::task::Wake`](https://doc.rust-lang.org/std/task/trait.Wake.html), and [`std::pin`](https://doc.rust-lang.org/std/pin/index.html).
- Standard library, [`std::thread::park`](https://doc.rust-lang.org/std/thread/fn.park.html), on the unpark token.
- Mara Bos, *Rust Atomics and Locks*, O'Reilly Media, 2023, Chapter 1, on thread parking.
