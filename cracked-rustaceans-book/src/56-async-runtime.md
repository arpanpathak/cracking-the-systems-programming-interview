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

<p class="listing"><span class="listing-label">Listing 56.1</span> <code>block_on</code>. <code>src/problems/async_mini.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/async_mini.rs">read the file on GitHub</a></p>

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

<p class="listing"><span class="listing-label">Listing 56.2</span> A future that yields. <code>src/problems/async_mini.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/async_mini.rs">read the file on GitHub</a></p>

`YieldTimes` contains only two `usize` fields, so it implements `Unpin`, and
`self.get_mut()` can turn `Pin<&mut Self>` back into `&mut Self` without `unsafe` code.

Each `Pending` result is preceded by `context.waker().wake_by_ref()`. The future asks to be
polled again immediately. Returning `Pending` without arranging a wake-up would leave the
future suspended forever, which is the most common bug in hand-written futures.

### A future that waits for time

<p class="listing"><span class="listing-label">Listing 56.3</span> A future that waits for time. <code>src/problems/async_mini.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/async_mini.rs">read the file on GitHub</a></p>

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

<p class="listing"><span class="listing-label">Listing 56.4</span> The executor. <code>src/problems/async_mini.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/async_mini.rs">read the file on GitHub</a></p>

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

<p class="listing"><span class="listing-label">Listing 56.5</span> The executor, continued. <code>src/problems/async_mini.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/async_mini.rs">read the file on GitHub</a></p>

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
