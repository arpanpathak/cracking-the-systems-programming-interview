# 30. A Bounded Buffer {#bounded-buffer}

*Source file: [`src/bin/bounded_buffer.rs`](../../rust-interview-lab/src/bin/bounded_buffer.rs). Run it with
`cargo run --bin bounded_buffer`.*

## Problem Statement

Build a queue with a fixed capacity that several threads share: producers must
wait while the queue is full, and consumers must wait while it is empty. No thread
may spin on a flag, and no item may be lost or handed out twice.

## Designing a Solution

A `Mutex<VecDeque<T>>` makes the deque safe to share, but a lock alone cannot
express waiting. A consumer that finds the queue empty has to release the lock
and sleep, and it has to be woken when an item arrives. That is what a condition
variable is for.

The queue uses two condition variables. `not_empty` is the one consumers wait on
and producers signal after a push; `not_full` is the one producers wait on and
consumers signal after a pop. With a single variable, every waiter would be woken
by every change, and the threads of the wrong kind would find their own condition
still false and go back to sleep.

`Condvar::wait` takes the guard by value. It releases the lock, parks the thread,
and returns a new guard once the lock has been reacquired. That reacquisition is
why the condition has to be checked in a `while` loop rather than an `if`: the
thread can wake without a signal, and another thread can take the slot between
the wake-up and the reacquisition. The `while` re-checks the condition with the
lock held, so the thread only proceeds when the state is what it observed.

`notify_one` is used rather than `notify_all`. Each signal follows exactly one
state change, one item added or one slot freed, so exactly one waiter can make
progress. Waking every waiter would produce a crowd that immediately re-checks
the condition and sleeps again.

## Implementation

```rust
use std::collections::VecDeque;
use std::sync::{Arc, Condvar, Mutex};
use std::thread;
use std::time::Duration;

// A thread-safe bounded buffer (a "shelf" that holds at most `capacity` items).
//
// Three fields do all the work:
//   - `inner`     : the actual VecDeque, wrapped in a Mutex so only one thread
//                   touches it at a time.
//   - `not_empty` : waiting room for CONSUMERS. A consumer sleeps here when the
//                   shelf is empty. Producers ring this bell after pushing.
//   - `not_full`  : waiting room for PRODUCERS. A producer sleeps here when the
//                   shelf is full. Consumers ring this bell after popping.
//
// Two separate condvars so we always wake the RIGHT kind of thread.
// One shared condvar would cause livelock: consumers waking consumers,
// producers waking producers, everyone re-checking and going back to sleep.
struct BoundedQueue<T> {
    inner: Mutex<VecDeque<T>>,
    capacity: usize,
    not_empty: Condvar,
    not_full: Condvar,
}

impl<T> BoundedQueue<T> {
    fn new(capacity: usize) -> Self {
        // Capacity 0 makes no sense: no producer could ever push,
        // and every pop would block forever.
        assert!(capacity > 0, "capacity must be > 0");

        Self {
            inner: Mutex::new(VecDeque::with_capacity(capacity)),
            capacity,
            not_empty: Condvar::new(),
            not_full: Condvar::new(),
        }
    }

    fn push(&self, item: T) {
        // Acquire the shelf lock. `guard` is our exclusive handle to the deque.
        let mut guard = self.inner.lock().unwrap();

        // Wait while the shelf is full.
        //
        // Why `while` and not `if`:
        //   1. Condvars are allowed to wake up for no reason (spurious wakeup).
        //   2. Even on a real wakeup, another producer may have raced us and
        //      taken the free slot before we reacquired the lock.
        // So we must re-check the condition every time we wake.
        //
        // Why `guard = ...wait(guard)`:
        //   `wait` consumes the guard (it releases the lock on our behalf),
        //   puts us to sleep, then re-locks and hands us a NEW guard.
        //   The reassignment just means "here's my fresh key to the shelf."
        //   The VecDeque inside is the same one — we're not replacing the queue.
        while guard.len() == self.capacity {
            guard = self.not_full.wait(guard).unwrap();
        }

        // We have room. Add the item to the back of the deque.
        guard.push_back(item);

        // Release the lock BEFORE ringing the bell.
        // This is an optimization, not a correctness requirement.
        // If we notify while still holding the lock, the thread we wake will
        // immediately block on `lock()` until we release it — a wasted wakeup.
        drop(guard);

        // Ring the "not empty" bell: one consumer can now make progress.
        // `notify_one` (not `notify_all`) because exactly ONE item was added,
        // so only ONE consumer can succeed. Waking all of them = stampede.
        self.not_empty.notify_one();
    }

    fn pop(&self) -> T {
        // Acquire the shelf lock.
        let mut guard = self.inner.lock().unwrap();

        // Wait while the shelf is empty.
        // Same `while` reasoning as push: spurious wakeups + races with other
        // consumers who may have grabbed the item before we reacquired the lock.
        while guard.is_empty() {
            guard = self.not_empty.wait(guard).unwrap();
        }

        // Safe to unwrap: the `while` loop guarantees the deque is non-empty,
        // and we hold the lock so nobody can change that between the check
        // and this line.
        let item = guard.pop_front().unwrap();

        // Release before notifying (same optimization as in push).
        drop(guard);

        // Ring the "not full" bell: one producer can now make progress.
        // Exactly one slot opened, so wake exactly one producer.
        self.not_full.notify_one();

        item
    }
}

fn main() {
    // Small capacity (3) so that with two slow consumers you can actually
    // SEE producers block: the queue fills up and push() sleeps in `not_full`.
    let queue = Arc::new(BoundedQueue::new(3));

    let mut handles = vec![];

    // ---- Producers ----
    // Two producers, each pushes 5 items. `Arc::clone` bumps the refcount so
    // each thread shares the same queue; ownership of the clone moves in.
    for p in 0..2 {
        let q = Arc::clone(&queue);
        handles.push(thread::spawn(move || {
            for i in 0..5 {
                let item = format!("p{}:item{}", p, i);
                println!("  [producer {}] pushing {}", p, item);
                q.push(item);
                // Slow down so we don't blast through the whole buffer instantly.
                thread::sleep(Duration::from_millis(30));
            }
        }));
    }

    // ---- Consumers ----
    // Two consumers, each pops 5 items. Consumers are SLOWER than producers
    // here (60ms vs 30ms), so the queue fills up and you'll see producers
    // stall on `not_full.wait(...)`.
    for c in 0..2 {
        let q = Arc::clone(&queue);
        handles.push(thread::spawn(move || {
            for _ in 0..5 {
                let item = q.pop();
                println!("[consumer {}] got {}", c, item);
                thread::sleep(Duration::from_millis(60));
            }
        }));
    }

    // Join everything. If our synchronization is wrong, this is where you'd
    // hang (a thread sleeping forever) or panic (unwrap on empty / on a
    // poisoned mutex after another thread panicked while holding it).
    for h in handles {
        h.join().unwrap();
    }
    println!("done");
}
```

The lock is released with `drop(guard)` before `notify_one`. Holding the lock
while signalling does not lose the wake-up, but the thread that is woken
immediately blocks on `lock` until the signaller releases it, so the signal
costs a context switch that accomplishes nothing.

`Arc` is what lets two threads own the same queue. The clone is passed to the
thread and the original stays in `main`; the queue is freed when the last handle
is dropped.

## Intuition

With `BoundedQueue::new(1)` and one producer and one consumer, the state after
each operation is:

```text
step                queue   producer        consumer
push(1)             [1]     running
pop()               []      running         takes 1
push(2)             [2]     running
pop()               []      running         takes 2

if the consumer starts first:
pop()               []      -               waits on not_empty
push(1)             [1]     running         wakes, takes 1
```

The consumer that finds the queue empty parks on `not_empty` and holds no lock
while parked, so the producer can take the lock and push.

## Time and Space Complexity

| Operation | Cost | Condition |
|---|---|---|
| `push`, `pop` | `O(1)` | one lock, at most one signal |
| block and wake | one context switch | the lock is released while the thread is parked |
| memory | one deque at `capacity`, plus one word per blocked thread | the blocked threads are in the kernel, not in the queue |
| memory | `O(n)` per `VecDeque` | the buffer is sized at construction and does not grow |

The mutex is held for the length of the critical section, which is a deque
operation and a length check. No work that can block is performed under the lock,
which is what keeps the queue from serialising its callers.

## Limitations

**There is no way to close the queue.** A consumer that calls `pop` after the
producers have finished waits forever, and with no `close` method there is no
state that would release it. A production queue needs a shutdown flag, checked
inside the same loop, and a `notify_all` when it is set.

**Poisoning is handled with `unwrap`.** A thread that panics while holding the
lock marks the mutex poisoned, and every later `lock()` returns `Err`. The
`unwrap` turns that into a second panic rather than a recoverable error, which is
acceptable for a demonstration and not for a library.

**There is no fairness guarantee.** `notify_one` may wake any waiter, so a
pushed item can be taken by a later arrival while an earlier consumer is still
parked. A fair queue needs an ordered wait list, which this one does not provide.

**The program's output is interleaved.** The print statements run outside the
lock, so the two producers can print in either order and the lines from different
threads can be adjacent. The set of lines is fixed; the order is not.

**The file has no tests.** Correctness here is a property of the interleaving,
and the tests that would catch a missing `while` are the ones that run a producer
and a consumer concurrently rather than the ones that assert on a single-threaded
push and pop.

## Summary

- A mutex makes the deque shared; condition variables make waiting possible.
- The condition is re-checked in a `while` loop, because a wake-up does not
  prove the condition is true.
- Two condition variables keep each signal directed at a thread that can act on
  it; `notify_one` follows each single state change.
- The queue has no shutdown path, and a consumer that outlives the producers
  waits indefinitely.

## References

- Standard library, [`std::sync::Condvar`](https://doc.rust-lang.org/std/sync/struct.Condvar.html).
- Standard library, [`Condvar::wait`](https://doc.rust-lang.org/std/sync/struct.Condvar.html#method.wait).
- Standard library, [`std::sync::Mutex`](https://doc.rust-lang.org/std/sync/struct.Mutex.html).
- The Rust Book, [Shared-state concurrency](https://doc.rust-lang.org/book/ch16-03-shared-state.html).
