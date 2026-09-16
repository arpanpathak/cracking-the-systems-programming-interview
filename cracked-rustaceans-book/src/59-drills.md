# 59. Interview Drills {#drills}

*Source file: [`src/problems/drills.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/drills.rs). Test it with `cargo test drills`.*

## Problem Statement

The other chapters read complete, tested modules. In an interview there is time for
perhaps forty lines. The file `drills.rs` collects the version of ten exercises that
fits that budget, written to be typed from memory:

| Drill | Full treatment |
|---|---|
| Thread-safe counter with `Arc<Mutex>` | Chapters 36 and 43 |
| Scoped parallel sum | Chapters 31 and 43 |
| Spin lock | Chapter 44 |
| Semaphore | Chapter 45 |
| Bounded blocking queue with close | Chapters 30 and 46 |
| Thread pool | Chapter 21 |
| Retry with exponential backoff | Chapter 57 |
| Consistent hashing ring | Chapter 42 |
| HTTP request head parser | Chapter 54 |
| Newtype and routing enumeration | Chapters 35 and 55 |

## Designing a Solution

Each drill should be written in 30 to 45 minutes without looking at the file, and then
compared with it. After writing it, state the failure modes and how you would test them.
The short versions keep the core mechanism of each design and drop everything a caller
could live without in an interview: accessors, timeouts, typed errors, and most
documentation.

## Implementation

<p class="listing"><span class="listing-label">Listing 59.1</span> The complete module, with its tests. <code>src/problems/drills.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/drills.rs">read the file on GitHub</a></p>

### Counter and parallel sum

`count_parallel` is the `Arc<Mutex<usize>>` counter from chapter 36, with the lock taken
once per increment. The final `*counter.lock().expect("poisoned")` reads the total after
every thread has been joined.

`parallel_sum` is shorter than chapter 43's version, and it is not parallel. The iterator
chain `.map(|chunk| scope.spawn(...)).map(|handle| handle.join()...).sum()` is lazy:
`sum` pulls the first element, which spawns the first thread and immediately joins it,
and only then pulls the second. The four chunks are summed one after another on four
threads. The result is correct and the test passes, so the problem is easy to miss.
Collecting the handles into a `Vec` before joining, as chapter 43's version does, starts
every thread before waiting for any.

### Spin lock and semaphore

The spin lock uses `swap(true, Ordering::Acquire)` in a loop rather than
`compare_exchange_weak`. `swap` stores `true` whether or not the lock was free and
returns the previous value, so the loop exits when the previous value was `false`. It is
shorter to write and performs a write on every attempt, which chapter 44's version
avoids while waiting. The `unsafe` blocks have no `SAFETY` comments, and `SpinGuard` has
the same automatically derived `Sync` implementation that chapter 44 shows to be
unsound.

The semaphore has no guard. `acquire` and `release` are separate calls, so a caller that
returns early between them leaks a permit. Chapter 45's version returns a guard.

### Queue and thread pool

`BlockingQueue` is chapter 46's closable queue without its accessors. `new` does not check
the capacity, so `BlockingQueue::new(0)` produces a queue on which every `push` waits
forever.

`ThreadPool` sends boxed closures, `Box<dyn FnOnce() + Send + 'static>`, over one channel.
Each worker runs `let Ok(job) = receiver.lock().expect("poisoned").recv() else { return; };`.
The temporary `MutexGuard` in that statement is dropped at the end of the `let`
statement, before `job()` runs, so workers execute jobs in parallel. `Drop` for the pool
takes the sender out of its `Option` and drops it, which makes every worker's `recv` fail
and its loop end, and then joins the workers. A job that panics ends its worker thread,
and `let _ = worker.join()` discards the panic.

### Retry, hash ring, HTTP head, and small types

`retry` takes the retryability test as a closure instead of a trait, doubles a delay that
starts at 25 ms, and caps it at one second. It has no jitter.

`HashRing::get` computes the owner index as `partition_point(...) % self.points.len()`,
which wraps an index equal to the length to zero in one expression. Keys are hashed with
the same function as virtual nodes, using replica number 0.

`parse_request_head` returns `Option`, so a caller cannot tell why a head was rejected.
It lowercases header names on the way in, which makes later lookups case-insensitive
without `eq_ignore_ascii_case`.

`Port::new` accepts any non-zero `u16`. The standard library's `NonZeroU16` expresses the
same invariant with no custom type, and `NonZeroU16::new(value)` returns `Option`.
`Route::parse` combines exact matches with `strip_prefix` in the catch-all arm.

The tests are grouped three to a function. `retry_ring_http_and_adt` checks the hash ring
with the same property as chapter 42: after adding node `c`, a key either keeps its owner
or moves to `c`.

## Intuition

**`parallel_sum(&[1, 2, 3, 4])` as the lazy chain runs it**

| `sum` pulls | action | threads alive |
|---|---|---|
| element 1 | spawn a thread for `[1]`, then join it: 1 | 0 |
| element 2 | spawn a thread for `[2]`, then join it: 2 | 0 |
| element 3 | spawn a thread for `[3]`, then join it: 3 | 0 |
| element 4 | spawn a thread for `[4]`, then join it: 4 | 0 |
| end | return 10 | 0 |

No two threads are ever alive at the same time.

## Time and Space Complexity

Each drill has the same asymptotic cost as its full version; the chapters listed in the
table in the Problem Statement give the details. `parallel_sum` costs `O(n)` work as intended, but
its wall-clock time is that of a sequential sum plus four thread creations.

## Limitations

**What the short versions leave out**

| Drill | Omitted, compared with the full version |
|---|---|
| `count_parallel` | nothing essential |
| `parallel_sum` | the lazy chain joins each thread before spawning the next |
| `SpinLock` | `try_lock`, `SAFETY` comments; the guard is `Sync` for `T: Send` |
| `Semaphore` | RAII guard, timeout |
| `BlockingQueue` | capacity check, `try_pop`, accessors |
| `ThreadPool` | reporting of panicked jobs |
| `retry` | jitter, `Retry-After` |
| `HashRing` | removal, duplicate detection, shared name storage |
| `parse_request_head` | body framing, limits, typed errors |
| `Port`, `Route` | typed errors; `NonZeroU16` would suffice for `Port` |

## Summary

- A drill is the version of an exercise that fits an interview's time budget; the full
  chapters show what a production version adds.
- Iterator chains are lazy. Spawning and joining threads in one chain runs them
  sequentially, and the result is still correct, so only timing reveals it.
- Shortened `unsafe` code keeps the soundness obligations of the full version, including
  the `Send` and `Sync` implementations of guard types.
- Guards that release in `Drop` are worth their few extra lines, even in a drill.

## References

- Standard library, [`Iterator`](https://doc.rust-lang.org/std/iter/trait.Iterator.html#laziness), on laziness.
- Standard library, [`std::num::NonZeroU16`](https://doc.rust-lang.org/std/num/type.NonZeroU16.html).
