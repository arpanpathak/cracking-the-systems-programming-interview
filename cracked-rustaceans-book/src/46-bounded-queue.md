# 46. A Closable Bounded Queue {#bounded-queue}

*Source file: [`src/problems/bounded_queue.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/bounded_queue.rs). Test it with `cargo test bounded_queue`.*

## Problem Statement

Chapter 30's bounded buffer runs a fixed number of pushes and pops, so every consumer
knows when to stop. A service does not have that knowledge. Its consumers loop until the
producers are finished, and something has to tell a consumer that is parked waiting for
an item that no item will ever arrive. Build a bounded queue shared by many producers and
many consumers that:

- makes producers wait while the queue is full, and consumers wait while it is empty;
- can be closed, after which `push` fails and returns the item to the caller;
- lets consumers drain items pushed before the close, and then report that no more work
  exists.

## Designing a Solution

The queue uses the same structure as chapter 30: a `Mutex` around a `VecDeque`, a
`not_empty` condition variable for consumers, and a `not_full` condition variable for
producers. It adds three behaviours.

**A `closed` flag inside the protected state.** It lives in the same `Mutex` as the
items, so a thread reads it and the item count under one lock acquisition and cannot
observe one without the other.

**`push` returns `Err(item)` after `close`.** The caller gets its value back instead of
losing it, which matters when the item is a request that must be answered.

**`pop` returns `Option<T>`.** It returns `Some` while items remain, including items
pushed before `close`, and `None` only when the queue is both closed and drained. A
consumer can therefore be written as `while let Some(item) = queue.pop()`.

```text
push                                    pop
lock state                              lock state
loop:                                   loop:
    closed?        -> Err(item)             item available? -> notify not_full, Some(item)
    room?          -> push, notify          closed?          -> None
                      not_empty, Ok         wait on not_empty
    wait on not_full

close: lock, closed = true, unlock, notify_all on both condition variables
```

## Implementation

```rust
//! Bounded blocking queue with backpressure.
//!
//! Unbounded queues are a classic production failure: a fast producer and a slow
//! consumer turn into an OOM kill instead of a slow response. A bounded queue makes
//! the producer wait, which is backpressure, and it is the first thing a senior
//! systems interviewer looks for.
//!
//! This is an MPMC queue (many producers, many consumers) built from one `Mutex`
//! and two condition variables: `not_empty` for waiting consumers and `not_full`
//! for waiting producers. `close` unblocks everyone so shutdown cannot hang.

use std::collections::VecDeque;
use std::sync::{Condvar, Mutex};

struct State<T> {
    items: VecDeque<T>,
    capacity: usize,
    closed: bool,
}

/// A bounded MPMC queue. Share it behind `Arc`; all methods take `&self`.
pub struct BoundedQueue<T> {
    state: Mutex<State<T>>,
    not_empty: Condvar,
    not_full: Condvar,
}

impl<T> BoundedQueue<T> {
    /// Create a queue that holds at most `capacity` items.
    ///
    /// Panics if `capacity` is zero, because a zero-capacity queue can never make
    /// progress.
    pub fn new(capacity: usize) -> Self {
        assert!(capacity > 0, "capacity must be > 0");
        Self {
            state: Mutex::new(State {
                items: VecDeque::with_capacity(capacity),
                capacity,
                closed: false,
            }),
            not_empty: Condvar::new(),
            not_full: Condvar::new(),
        }
    }

    /// Push an item, blocking while the queue is full.
    ///
    /// Returns `Err(item)` if the queue is closed, so the caller keeps ownership
    /// instead of losing the value.
    pub fn push(&self, item: T) -> Result<(), T> {
        let mut state = self.state.lock().expect("queue mutex poisoned");
        loop {
            if state.closed {
                return Err(item);
            }
            if state.items.len() < state.capacity {
                state.items.push_back(item);
                self.not_empty.notify_one();
                return Ok(());
            }
            state = self.not_full.wait(state).expect("queue mutex poisoned");
        }
    }

    /// Pop an item, blocking while the queue is empty.
    ///
    /// Returns `None` once the queue is closed and drained, which is how a
    /// consumer loop terminates cleanly.
    pub fn pop(&self) -> Option<T> {
        let mut state = self.state.lock().expect("queue mutex poisoned");
        loop {
            if let Some(item) = state.items.pop_front() {
                self.not_full.notify_one();
                return Some(item);
            }
            if state.closed {
                return None;
            }
            state = self.not_empty.wait(state).expect("queue mutex poisoned");
        }
    }

    /// Pop without blocking.
    pub fn try_pop(&self) -> Option<T> {
        let mut state = self.state.lock().expect("queue mutex poisoned");
        let item = state.items.pop_front();
        if item.is_some() {
            self.not_full.notify_one();
        }
        item
    }

    /// Close the queue.
    ///
    /// Pending and future `pop` calls return `None` after the queue drains, and
    /// future `push` calls fail. Idempotent.
    pub fn close(&self) {
        let mut state = self.state.lock().expect("queue mutex poisoned");
        state.closed = true;
        drop(state);
        self.not_empty.notify_all();
        self.not_full.notify_all();
    }

    pub fn is_closed(&self) -> bool {
        self.state.lock().expect("queue mutex poisoned").closed
    }

    pub fn capacity(&self) -> usize {
        self.state.lock().expect("queue mutex poisoned").capacity
    }

    pub fn len(&self) -> usize {
        self.state.lock().expect("queue mutex poisoned").items.len()
    }

    pub fn is_empty(&self) -> bool {
        self.state
            .lock()
            .expect("queue mutex poisoned")
            .items
            .is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::thread;
    use std::time::Duration;

    #[test]
    fn preserves_order_across_threads() {
        let queue = Arc::new(BoundedQueue::new(8));
        let producer = {
            let queue = Arc::clone(&queue);
            thread::spawn(move || {
                for value in 0..1_000 {
                    queue.push(value).expect("queue stays open");
                }
                queue.close();
            })
        };

        let mut received = Vec::new();
        while let Some(value) = queue.pop() {
            received.push(value);
        }
        producer.join().expect("producer panicked");

        assert_eq!(received, (0..1_000).collect::<Vec<_>>());
    }

    #[test]
    fn never_exceeds_capacity() {
        let queue = Arc::new(BoundedQueue::new(4));
        let observed_peak = Arc::new(AtomicUsize::new(0));
        let producer = {
            let queue = Arc::clone(&queue);
            let observed_peak = Arc::clone(&observed_peak);
            thread::spawn(move || {
                for value in 0..200u32 {
                    queue.push(value).expect("queue stays open");
                    observed_peak.fetch_max(queue.len(), Ordering::SeqCst);
                }
                queue.close();
            })
        };

        while queue.pop().is_some() {
            thread::sleep(Duration::from_micros(50));
        }
        producer.join().expect("producer panicked");

        assert!(observed_peak.load(Ordering::SeqCst) <= 4);
    }

    #[test]
    fn close_wakes_a_blocked_consumer() {
        let queue = Arc::new(BoundedQueue::<u32>::new(1));
        let consumer = {
            let queue = Arc::clone(&queue);
            thread::spawn(move || queue.pop())
        };

        thread::sleep(Duration::from_millis(20));
        queue.close();

        assert_eq!(consumer.join().expect("consumer panicked"), None);
    }

    #[test]
    fn push_after_close_returns_the_item() {
        let queue = BoundedQueue::new(1);
        queue.close();
        assert_eq!(
            queue.push("workload".to_string()),
            Err("workload".to_string())
        );
    }
}
```

The loops in `push` and `pop` test the closed flag on every iteration, not only before
the first wait. A thread parked on a condition variable may be woken by `close` rather
than by a state change it was waiting for, and the re-check is what turns that wake-up
into a return.

`close` sets the flag, releases the lock, and calls `notify_all` on both condition
variables. `notify_one` would be wrong here. Closing is a change that every waiter must
observe, because every parked producer must fail and every parked consumer must either
take a remaining item or return `None`. The method is idempotent: a second call sets a
flag that is already set.

`pop` checks for an item before it checks the flag. That order is what drains the queue
after `close`: items pushed before shutdown are still delivered, and `None` means that
there is no more work, not that shutdown has been requested.

`try_pop` never waits, and it still signals `not_full` when it removes an item, so a
producer parked on a full queue is not stranded by a consumer that polls.

`new` asserts that the capacity is positive, because a queue of capacity zero could never
accept an item.

The four tests are concurrency tests rather than single-threaded checks.
`preserves_order_across_threads` pushes a thousand values from one thread and pops them
on another. `never_exceeds_capacity` records the largest length a producer observes
while a slow consumer drains. `close_wakes_a_blocked_consumer` parks a consumer on an
empty queue and requires `close` to release it with `None`, which is the test that fails
if `pop` checks the flag only before waiting. `push_after_close_returns_the_item` checks
that the value comes back to the caller.

The `len`, `is_empty`, and `is_closed` accessors each take the lock and return a
snapshot. By the time the caller reads the value, another thread may have changed it, so
they are useful for metrics and tests and not for deciding whether to call `pop`.

## Intuition

**`close_wakes_a_blocked_consumer` with capacity 1**

| step | consumer thread | main thread | state |
|---|---|---|---|
| 1 | `pop` locks; no item; not closed; waits on `not_empty` | | `[]`, open |
| 2 | parked, lock released | sleeps 20 ms | `[]`, open |
| 3 | | `close`: sets `closed`, unlocks, `notify_all` | `[]`, closed |
| 4 | wakes, reacquires lock; no item; closed, returns `None` | | `[]`, closed |
| 5 | thread ends | `join` returns `None` | |

## Time and Space Complexity

| Operation | Cost |
|---|---|
| `push`, `pop`, `try_pop` | `O(1)` amortised under the lock, plus waiting time when full or empty |
| `close` | `O(1)` plus waking every parked thread |
| accessors | one lock acquisition each |
| memory | `capacity` slots allocated at construction |

## Limitations

**Poisoning panics every caller.** Each method uses `expect("queue mutex poisoned")`. A
panic in one thread while it holds the lock makes every later call panic as well.
Chapter 22 describes the alternatives.

**No fairness.** A producer that arrives just as a slot frees can take it ahead of one
that has waited longer.

**No timeouts.** `push` and `pop` wait indefinitely. A service that must give up after a
deadline needs `Condvar::wait_timeout_while` and a result that distinguishes a timeout
from a close.

**`notify_all` on close wakes every waiter at once.** For a queue with thousands of parked
threads, closing causes a burst of wake-ups that each take the lock in turn. This is the
correct behaviour for shutdown, and it is a cost worth knowing about.

## Summary

- A closable queue keeps a `closed` flag under the same lock as the items, so waiters see
  a consistent state.
- `push` returns the rejected item after close, and `pop` drains remaining items before
  it reports `None`.
- The closed flag is re-checked inside the wait loops, and `close` uses `notify_all`,
  because every waiter must observe shutdown.
- `try_pop` must signal `not_full` like `pop`, or a polling consumer can strand producers.

## References

- Standard library, [`std::sync::Condvar`](https://doc.rust-lang.org/std/sync/struct.Condvar.html), on `notify_all` and spurious wake-ups.
- The `crossbeam-channel` crate, [`bounded`](https://docs.rs/crossbeam-channel/latest/crossbeam_channel/fn.bounded.html), a production bounded MPMC channel.
