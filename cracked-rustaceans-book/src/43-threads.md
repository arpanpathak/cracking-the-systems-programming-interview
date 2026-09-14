# 43. Threads, Send, and Sync {#threads}

*Source file: [`src/problems/threads.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/threads.rs). Test it with `cargo test threads`.*

## Problem Statement

Write the basic concurrent building blocks a systems interview expects:

- sum a slice on several threads without copying it or wrapping it in `Arc`;
- count events from several threads without a lock;
- initialize a process-wide value exactly once, even if several threads ask for it at
  the same time;
- make a thread-safety assumption about a type fail the build when it is false.

## Designing a Solution

**Send and Sync.** A type is `Send` when a value of it may be moved to another thread,
and `Sync` when a shared reference `&T` may be used from several threads at once.
Equivalently, `T: Sync` exactly when `&T: Send`. Both are auto traits: the compiler
implements them for a type whose fields all implement them. `Rc<T>` is neither, because
its reference count is updated without synchronization, and `RefCell<T>` is `Send` but
not `Sync`, because its borrow flag is not synchronized. Passing either where the
other thread could touch it is a compile error.

**Three ways to run work on threads**, in increasing order of ceremony:

1. `thread::scope` for work that borrows local data and finishes before the scope ends.
   The closures may capture references, because the scope guarantees they are joined
   before the borrowed data can be dropped.
2. `thread::spawn` for work that owns its data and may outlive the caller. The closure
   must be `'static` and `Send`, so shared data travels in an `Arc`.
3. A thread pool when there are many small jobs and threads should be reused, which
   chapter 21 builds.

**Atomics instead of locks.** When the shared state is a single integer, an
`AtomicUsize` updates it with one processor instruction such as `lock xadd` on x86 or
an exclusive-load and exclusive-store pair on ARM. No thread blocks, and no guard
exists that could be held across a panic.

## Implementation

```rust
//! Threads and fearless concurrency.
//!
//! Rust's claim about concurrency is narrow and checkable: safe code cannot
//! produce a data race, because `Send` and `Sync` describe what may cross a
//! thread boundary and the compiler refuses programs that violate the rules.
//!
//! - `Send` means a value may be moved to another thread.
//! - `Sync` means `&T` may be shared across threads.
//!
//! Both are auto traits: a type is `Send`/`Sync` when its fields are. `Rc` and
//! `RefCell` are the standard counter-examples, which is precisely why sharing
//! them across threads does not compile. The compile error is the feature, not an
//! obstacle.
//!
//! Three ways to get work onto other threads, in increasing order of ceremony:
//!
//! 1. `thread::scope` for work that borrows local data and finishes with the
//!    scope. No `'static`, no `Arc`.
//! 2. `thread::spawn` for work that must own its data and outlive the caller.
//! 3. A thread pool when the number of units of work is large and threads should
//!    be reused.

use std::sync::OnceLock;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::thread;

/// Number of hardware threads the runtime can use, defaulting to 1.
pub fn available_workers() -> usize {
    thread::available_parallelism()
        .map(|count| count.get())
        .unwrap_or(1)
}

/// Sum a slice by splitting it into chunks that run on scoped threads.
///
/// `thread::scope` is what makes this ergonomic: the workers borrow `values`
/// directly, so there is no `Arc` and no `'static` bound. The scope waits for
/// every thread, which removes the forgotten-join bug.
pub fn parallel_sum(values: &[i32]) -> i64 {
    if values.is_empty() {
        return 0;
    }

    let workers = available_workers().min(values.len());
    let chunk_size = values.len().div_ceil(workers);

    thread::scope(|scope| {
        let handles: Vec<_> = values
            .chunks(chunk_size)
            .map(|chunk| {
                scope.spawn(move || chunk.iter().map(|value| i64::from(*value)).sum::<i64>())
            })
            .collect();

        handles
            .into_iter()
            .map(|handle| handle.join().expect("worker panicked"))
            .sum()
    })
}
```

`thread::available_parallelism` returns `io::Result<NonZeroUsize>`. It can fail, for
example inside a restricted container, and the function falls back to 1 rather than
propagating the error, which is a reasonable default for sizing a pool.

`parallel_sum` returns early for an empty slice. Without that check, `workers` would be
0 and `values.len().div_ceil(0)` would panic with a division by zero.

`values.chunks(chunk_size)` yields at most `workers` sub-slices. The closure passed to
`scope.spawn` is `move`, so it captures `chunk`, a `&[i32]`, by value. The reference
borrows from `values`, and `thread::scope` is what makes that borrow legal: the scope
does not return until every spawned thread has finished.

The handles are collected into a `Vec` before any is joined. Joining inside the same
iterator chain that spawns would make the chain lazy and sequential: each thread would
be spawned and joined before the next was spawned.

```rust
/// A counter that several threads may increment without a lock.
///
/// `Relaxed` is correct here because the counter is the only value being
/// communicated; there is no other data whose visibility depends on it.
#[derive(Default)]
pub struct AtomicCounter {
    value: AtomicUsize,
}

impl AtomicCounter {
    pub const fn new() -> Self {
        Self {
            value: AtomicUsize::new(0),
        }
    }

    /// Increment and return the new value.
    pub fn increment(&self) -> usize {
        self.value.fetch_add(1, Ordering::Relaxed) + 1
    }

    pub fn get(&self) -> usize {
        self.value.load(Ordering::Relaxed)
    }
}

/// Increment a counter from several scoped threads that share it by reference.
pub fn scoped_increment(counter: &AtomicCounter, threads: usize, per_thread: usize) {
    thread::scope(|scope| {
        for _ in 0..threads {
            scope.spawn(|| {
                for _ in 0..per_thread {
                    counter.increment();
                }
            });
        }
    });
}
```

`increment` takes `&self`, not `&mut self`. The atomic provides interior mutability
that is safe across threads, so `AtomicCounter` is `Sync` and can be shared by
reference.

`fetch_add(1, Ordering::Relaxed)` returns the previous value, and the method adds one
to return the new value. The `Ordering` argument does not control the addition, which
is always atomic. It describes the guarantees about when other atomic operations
observe the result. For a single counter with no relationship to other variables,
`Relaxed` is sufficient. `SeqCst` would be required only if the program's correctness
depended on a particular interleaving of this counter with other atomic variables.

`scoped_increment` spawns closures that capture `counter: &AtomicCounter` without
`move`. Each closure borrows the reference, and all the borrows are shared, which is
legal because `AtomicCounter: Sync`.

`AtomicCounter::new` is a `const fn`, so a counter can be a `static` initialized at
compile time: `static REQUESTS: AtomicCounter = AtomicCounter::new();`.

```rust
/// A value initialized once and shared by every caller.
///
/// `OnceLock` is the primitive behind lazy process-wide configuration, and it is
/// safe because initialization happens at most once even under concurrent calls.
pub fn build_channel() -> &'static str {
    static CHANNEL: OnceLock<&'static str> = OnceLock::new();
    CHANNEL.get_or_init(|| "stable")
}

/// A compile-time assertion that `T` may cross thread boundaries.
///
/// Calling `assert_send_sync::<Client>()` fails to compile if `Client` is not
/// thread-safe, which turns a concurrency assumption into a build error.
pub fn assert_send_sync<T: Send + Sync>() {}
```

`OnceLock::get_or_init` runs the closure at most once, even when several threads call
it concurrently. The other callers block until the first finishes and then receive a
reference to the same value. The `static` is local to the function, so the value is
private to it and still lives for the whole process.

`assert_send_sync::<T>()` has an empty body and a bound. Calling it with a type that is
not `Send + Sync` is a compile error, which turns an assumption such as "our client can
be shared between threads" into a check that runs on every build.

```rust
#[cfg(test)]
mod tests {
    use super::*;
    use std::thread;

    #[test]
    fn parallel_sum_matches_the_sequential_sum() {
        let values: Vec<i32> = (1..=10_000).collect();
        let expected: i64 = values.iter().map(|value| i64::from(*value)).sum();
        assert_eq!(parallel_sum(&values), expected);
    }

    #[test]
    fn parallel_sum_handles_small_and_empty_inputs() {
        assert_eq!(parallel_sum(&[]), 0);
        assert_eq!(parallel_sum(&[7]), 7);
        assert_eq!(parallel_sum(&[-1, 1, -2, 2]), 0);
    }

    #[test]
    fn scoped_threads_share_a_counter_without_arc() {
        let counter = AtomicCounter::new();
        scoped_increment(&counter, 8, 500);
        assert_eq!(counter.get(), 4_000);
    }

    #[test]
    fn spawn_returns_a_join_handle_that_carries_the_result() {
        let handle = thread::spawn(|| 6 * 7);
        assert_eq!(handle.join().expect("worker panicked"), 42);
    }

    #[test]
    fn once_lock_initializes_a_single_value() {
        assert_eq!(build_channel(), "stable");
        assert_eq!(build_channel(), build_channel());
    }

    #[test]
    fn counter_is_thread_safe_by_construction() {
        assert_send_sync::<AtomicCounter>();
        assert!(available_workers() >= 1);
    }
}
```

`spawn_returns_a_join_handle_that_carries_the_result` shows the owned alternative to
scoped threads: `thread::spawn(|| 6 * 7)` returns a `JoinHandle<i32>`, and `join`
returns `Result<i32, Box<dyn Any + Send>>`, whose error case carries the panic payload
if the thread panicked.

## Intuition

**`parallel_sum(&[1, 2, 3, 4, 5, 6, 7])` on a machine with eight hardware threads**

| step | value |
|---|---|
| `available_workers()` | 8 |
| `workers = 8.min(7)` | 7 |
| `chunk_size = 7.div_ceil(7)` | 1 |
| `values.chunks(1)` | seven slices of one element |
| threads spawned | 7, each summing one element |
| joined results | `1, 2, 3, 4, 5, 6, 7` |
| return | 28 |

For a slice of 10,000 values on the same machine, `workers` is 8, `chunk_size` is
1,250, and eight threads each sum 1,250 values. The test compares the result with a
sequential sum.

## Time and Space Complexity

| Operation | Time | Space |
|---|---|---|
| `parallel_sum` | `O(n)` total work, spread over up to `available_parallelism` threads, plus thread creation | one stack per thread and one handle per chunk |
| `AtomicCounter::increment` | `O(1)`, one atomic instruction | none |
| `build_channel` | `O(1)` after the first call | one `&'static str` |
| `assert_send_sync` | compile time only | none |

Creating a thread costs tens of microseconds and a stack reservation. For a slice of a
few thousand integers the sequential loop is faster than any parallel version, and the
parallel version pays off only when the per-chunk work dominates the cost of starting
threads.

## Limitations

**`parallel_sum` spawns threads on every call.** A program that calls it in a loop pays
thread creation each time. A pool, or a library such as `rayon`, reuses threads.

**Contention on a shared atomic.** Every `fetch_add` from every thread writes to the same
cache line, so eight threads incrementing one counter scale poorly. Chapter 48 measures
the related effect of false sharing between separate counters.

**`Relaxed` is correct here, and easy to misuse elsewhere.** The justification in the
documentation comment applies to an isolated counter. Code that reads one atomic to
decide how to update another needs an argument about ordering, and usually needs a
lock or a compare-and-swap loop.

**`build_channel` is a demonstration.** Its initializer returns a constant, which a plain
`const` would express without `OnceLock`. The pattern pays off when initialization reads
the environment or a file.

## Summary

- `Send` permits moving a value to another thread and `Sync` permits sharing `&T`
  between threads; the compiler derives both from a type's fields.
- `thread::scope` lets threads borrow local data because it joins them before
  returning, which removes the need for `Arc` and `'static`.
- Collect spawned handles before joining them, or the threads run one after another.
- An `AtomicUsize` counts from many threads without a lock; `Relaxed` ordering suffices
  for a value with no relationship to other atomics.
- `OnceLock` initializes a shared value exactly once, and a generic function with a
  `Send + Sync` bound turns a thread-safety assumption into a compile-time check.

## References

- The Rust Book, [Fearless concurrency](https://doc.rust-lang.org/book/ch16-00-concurrency.html).
- The Rustonomicon, [Send and Sync](https://doc.rust-lang.org/nomicon/send-and-sync.html).
- Mara Bos, *Rust Atomics and Locks*, O'Reilly Media, 2023, Chapters 1 to 35.
- Standard library, [`std::thread::scope`](https://doc.rust-lang.org/std/thread/fn.scope.html), [`std::sync::atomic::Ordering`](https://doc.rust-lang.org/std/sync/atomic/enum.Ordering.html), and [`std::sync::OnceLock`](https://doc.rust-lang.org/std/sync/struct.OnceLock.html).
