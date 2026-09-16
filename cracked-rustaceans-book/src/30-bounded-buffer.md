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

<p class="listing"><span class="listing-label">Listing 30.1</span> The complete program. <code>src/bin/bounded_buffer.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/bounded_buffer.rs">read the file on GitHub</a></p>

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
