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
