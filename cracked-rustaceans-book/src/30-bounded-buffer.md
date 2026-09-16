# 30. A Bounded Buffer {#bounded-buffer}

*Source file: [`src/bin/bounded_buffer.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/bounded_buffer.rs). Run it with
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

### The variant that returns an error instead of panicking

Two of the limitations above are the same limitation seen from different sides. A thread
that panics while holding the lock poisons the mutex, every later `lock()` returns `Err`,
and the `unwrap` turns that into a second panic that takes down a thread which did nothing
wrong. A queue meant to be used by other people has to hand the failure back to its caller
instead. The version below does that, and it carries the tests that prove it.

*Source file: [`src/bin/bounded_buffer_with_error_handling.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/bounded_buffer_with_error_handling.rs). Run it with
`cargo run --bin bounded_buffer_with_error_handling`, and test it with
`cargo test --bin bounded_buffer_with_error_handling`.*

```rust
use std::collections::VecDeque;
use std::fmt;
use std::sync::{Arc, Condvar, Mutex, PoisonError};
use std::thread;
use std::time::Duration;

#[derive(Debug)]
pub struct QueuePoisonedError;

impl fmt::Display for QueuePoisonedError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "The queue's internal mutex was poisoned by a panicking thread")
    }
}

impl std::error::Error for QueuePoisonedError {}

trait PoisonMap<T> {
    fn map_poison(self) -> Result<T, QueuePoisonedError>;
}

impl<T> PoisonMap<T> for Result<T, PoisonError<T>> {
    fn map_poison(self) -> Result<T, QueuePoisonedError> {
        self.map_err(|_| QueuePoisonedError)
    }
}

struct BoundedQueue<T> {
    inner: Mutex<VecDeque<T>>,
    capacity: usize,
    not_empty: Condvar,
    not_full: Condvar,
}

impl<T> BoundedQueue<T> {
    fn new(capacity: usize) -> Self {
        assert!(capacity > 0, "capacity must be > 0");
        Self {
            inner: Mutex::new(VecDeque::with_capacity(capacity)),
            capacity,
            not_empty: Condvar::new(),
            not_full: Condvar::new(),
        }
    }

    fn push(&self, item: T) -> Result<(), QueuePoisonedError> {
        let mut guard = self.inner.lock().map_poison()?;
        while guard.len() == self.capacity {
            guard = self.not_full.wait(guard).map_poison()?;
        }
        guard.push_back(item);
        drop(guard);
        self.not_empty.notify_one();
        Ok(())
    }

    fn pop(&self) -> Result<T, QueuePoisonedError> {
        let mut guard = self.inner.lock().map_poison()?;
        while guard.is_empty() {
            guard = self.not_empty.wait(guard).map_poison()?;
        }
        let item = guard.pop_front().unwrap();
        drop(guard);
        self.not_full.notify_one();
        Ok(item)
    }
}

fn main() {
    let queue = Arc::new(BoundedQueue::new(3));
    let mut handles = vec![];

    // ---- Producers ----
    for p in 0..2 {
        let q = Arc::clone(&queue);
        handles.push(thread::spawn(move || {
            for i in 0..5 {
                let item = format!("p{}:item{}", p, i);
                println!("  [producer {}] pushing {}", p, item);
                
                // Uses match, avoids naming an error variable, uses dbg!
                match q.push(item) {
                    Ok(_) => {}
                    Err(err) => {
                        dbg!(err);
                        break;
                    }
                }
                thread::sleep(Duration::from_millis(30));
            }
        }));
    }

    // ---- Consumers ----
    for c in 0..2 {
        let q = Arc::clone(&queue);
        handles.push(thread::spawn(move || {
            for _ in 0..5 {
                // Uses match, avoids naming an error variable, uses dbg!
                match q.pop() {
                    Ok(item) => {
                        println!("[consumer {}] got {}", c, item);
                    }
                    Err(err) => {
                        dbg!(err);
                        break;
                    }
                }
                thread::sleep(Duration::from_millis(60));
            }
        }));
    }

    // Join everything.
    for h in handles {
        match h.join() {
            Ok(_) => {}
            Err(err) => {
                dbg!(err);
            }
        }
    }
    println!("done");
}

#[cfg(test)]
mod tests {
    use super::*;

    // 1. Mark the test as one that MUST panic to pass
    // 2. Optional: use 'expected' to verify it panics with the correct error message
    #[test]
    #[should_panic(expected = "capacity must be > 0")]
    fn test_zero_capacity_panics() {
        // This line invokes the assert!(capacity > 0) inside new()
        let _queue: BoundedQueue<i32> = BoundedQueue::new(0);
    }

    #[test]
    fn test_queue_poisoning_on_thread_panic() {
        // 1. Create a queue shared via Arc so multiple threads can touch it
        let queue = Arc::new(BoundedQueue::new(5));
        let queue_clone = Arc::clone(&queue);

        // 2. Spawn a thread designed to crash while holding the internal lock
        let handle = thread::spawn(move || {
            // Manually lock the inner mutex so this thread owns the lock guard
            let _guard = queue_clone.inner.lock().unwrap();
            
            // Trigger a serious runtime panic while holding the lock guard!
            panic!("Intentional worker thread crash!");
        });

        // 3. Wait for the thread to die. It will return an Err because it panicked.
        let join_result = handle.join();
        assert!(join_result.is_err(), "The thread was supposed to panic");

        // 4. Now try to interact with the queue. 
        // Because the thread panicked while holding the guard, the Mutex is poisoned.
        // Our push and pop methods should cleanly catch this and return our custom error.
        match queue.push("test_item") {
            Err(QueuePoisonedError) => {
                // Success! The queue correctly caught the poisoned state 
                // instead of panicking the main thread.
            }
            Ok(_) => {
                panic!("Expected QueuePoisonedError, but push succeeded!");
            }
        }

        // Verify pop behaves the same way
        match queue.pop() {
            Err(QueuePoisonedError) => {}
            Ok(_) => panic!("Expected QueuePoisonedError, but pop succeeded!"),
        }
    }
}
```

`QueuePoisonedError` is a unit struct with a `Display` implementation and an empty
`std::error::Error` implementation, which is the minimum a type needs to travel inside a
`Box<dyn Error>` or to be printed by a caller that knows nothing about the queue. It
carries no data, because there is nothing useful to say beyond the fact that the queue can
no longer be trusted.

The conversion from the standard library's error is done by an extension trait rather than
by a free function. Both `Mutex::lock` and `Condvar::wait` fail with a
`PoisonError<T>`, but `T` differs between them: `lock` gives back a `MutexGuard`, and
`wait` gives back the guard it was handed. Writing `map_poison` as a method on
`Result<T, PoisonError<T>>` covers both call sites with one implementation, and leaves
`?` usable at the end of each line.

Discarding the `PoisonError` is a decision worth naming. It holds the guard, so a caller
that wanted to could reach through it with `into_inner` and use the data the panicking
thread left behind. Dropping it says that this queue treats poisoning as permanent: the
contents may be half-updated, and no caller should act on them.

The panicking thread no longer costs the whole program. `push` and `pop` return
`Result`, the producers and consumers match on it, and a poisoned queue ends each of
their loops with a `break` rather than an abort. What the variant does not fix is the
third limitation: there is still no way to close the queue, so a consumer that outlives
the producers still waits forever. Chapter 46 adds that.

The tests cover the two failures the original had no way to express.
`#[should_panic(expected = "capacity must be > 0")]` pins the assertion in `new`, and the
expected string means the test fails if the code panics for some other reason. The second
test poisons the queue on purpose: a thread locks the inner mutex, panics while holding
the guard, and after `join` reports the panic, both `push` and `pop` are checked for the
error. Matching `Err(QueuePoisonedError)` as a pattern works because the error is a unit
struct, so its name is both the type and its only value.

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
- Returning a `Result` from `push` and `pop` keeps a panicking producer from taking
  down the threads that were using the queue correctly.
- An extension trait on `Result<T, PoisonError<T>>` converts both the `lock` and the
  `wait` failure with one implementation.

## References

- Standard library, [`std::sync::Condvar`](https://doc.rust-lang.org/std/sync/struct.Condvar.html).
- Standard library, [`Condvar::wait`](https://doc.rust-lang.org/std/sync/struct.Condvar.html#method.wait).
- Standard library, [`std::sync::Mutex`](https://doc.rust-lang.org/std/sync/struct.Mutex.html).
- The Rust Book, [Shared-state concurrency](https://doc.rust-lang.org/book/ch16-03-shared-state.html).
