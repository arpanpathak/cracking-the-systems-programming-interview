# 45. A Counting Semaphore {#semaphore}

*Source file: [`src/problems/semaphore.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/semaphore.rs). Test it with `cargo test semaphore`.*

## Problem Statement

Implement `Semaphore::new(permits)` with:

- `acquire_guard`, which blocks until a permit is free, takes it, and returns a guard
  that gives it back when dropped;
- `try_acquire`, which takes a permit only if one is free now;
- `try_acquire_timeout`, which waits at most a given duration;
- `available_permits`, for metrics.

At no time may more guards be alive than the semaphore has permits.

## Designing a Solution

The state is one integer, `available`, in a `Mutex`. Taking a permit decrements it and
releasing one increments it. A thread that finds `available == 0` waits on a
`Condvar`, `released`, and every release signals that condition variable once.

```text
acquire_guard                           release (in SemaphoreGuard::drop)
lock state                              lock state
while available == 0:                   available += 1
    state = released.wait(state)        released.notify_one()
available -= 1
return SemaphoreGuard
```

`notify_one` is enough, because a release frees exactly one permit, so exactly one
waiter can proceed. The `while` loop re-checks the count after every wake-up, because a
wake-up can be spurious and another thread can take the permit between the signal and
the moment the woken thread reacquires the lock.

The guard is what makes the permit count trustworthy. Code written as "acquire, work,
release" leaks a permit whenever the work returns early or panics. With a guard, the
release runs in `Drop` on every path.

## Implementation

```rust
//! Counting semaphore built from `Mutex` + `Condvar`.
//!
//! A semaphore bounds how many callers may proceed at once without protecting any
//! data. It is the primitive behind connection pools, per-account GPU slot limits,
//! and bounded fan-out in an SDK or CLI.
//!
//! The RAII guard returns the permit on drop, so a panicking worker cannot leak a
//! permit and slowly deadlock the pool.

use std::sync::{Condvar, Mutex};
use std::time::Duration;

struct State {
    available: usize,
}

/// A counting semaphore. Cloning is not provided; share one behind `Arc`.
pub struct Semaphore {
    state: Mutex<State>,
    released: Condvar,
}

impl Semaphore {
    /// Create a semaphore with `permits` permits available.
    pub fn new(permits: usize) -> Self {
        Self {
            state: Mutex::new(State { available: permits }),
            released: Condvar::new(),
        }
    }

    /// Block until a permit is available.
    pub fn acquire(&self) {
        let _guard = self.acquire_guard();
    }

    /// Block until a permit is available, returning a guard that releases it.
    pub fn acquire_guard(&self) -> SemaphoreGuard<'_> {
        let mut state = self.state.lock().expect("semaphore mutex poisoned");
        while state.available == 0 {
            state = self.released.wait(state).expect("semaphore mutex poisoned");
        }
        state.available -= 1;
        SemaphoreGuard { semaphore: self }
    }

    /// Take a permit only if one is free right now.
    pub fn try_acquire(&self) -> Option<SemaphoreGuard<'_>> {
        let mut state = self.state.lock().expect("semaphore mutex poisoned");
        if state.available == 0 {
            None
        } else {
            state.available -= 1;
            Some(SemaphoreGuard { semaphore: self })
        }
    }

    /// Take a permit, waiting at most `timeout`.
    pub fn try_acquire_timeout(&self, timeout: Duration) -> Option<SemaphoreGuard<'_>> {
        let mut state = self.state.lock().expect("semaphore mutex poisoned");
        if state.available > 0 {
            state.available -= 1;
            return Some(SemaphoreGuard { semaphore: self });
        }

        let (mut state, _timed_out) = self
            .released
            .wait_timeout(state, timeout)
            .expect("semaphore mutex poisoned");

        if state.available == 0 {
            None
        } else {
            state.available -= 1;
            Some(SemaphoreGuard { semaphore: self })
        }
    }

    /// Permits currently free. Useful for metrics, not for control flow.
    pub fn available_permits(&self) -> usize {
        self.state
            .lock()
            .expect("semaphore mutex poisoned")
            .available
    }

    fn release(&self) {
        let mut state = self.state.lock().expect("semaphore mutex poisoned");
        state.available += 1;
        self.released.notify_one();
    }
}

/// Releases one permit when dropped.
pub struct SemaphoreGuard<'a> {
    semaphore: &'a Semaphore,
}

impl Drop for SemaphoreGuard<'_> {
    fn drop(&mut self) {
        self.semaphore.release();
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::thread;

    #[test]
    fn never_exceeds_the_permit_count() {
        let permits = 4;
        let semaphore = Arc::new(Semaphore::new(permits));
        let active = Arc::new(AtomicUsize::new(0));
        let peak = Arc::new(AtomicUsize::new(0));

        let mut handles = Vec::new();
        for _ in 0..32 {
            let semaphore = Arc::clone(&semaphore);
            let active = Arc::clone(&active);
            let peak = Arc::clone(&peak);
            handles.push(thread::spawn(move || {
                let _guard = semaphore.acquire_guard();
                let now = active.fetch_add(1, Ordering::SeqCst) + 1;
                peak.fetch_max(now, Ordering::SeqCst);
                thread::sleep(Duration::from_millis(1));
                active.fetch_sub(1, Ordering::SeqCst);
            }));
        }
        for handle in handles {
            handle.join().expect("worker panicked");
        }

        assert!(peak.load(Ordering::SeqCst) <= permits);
        assert_eq!(semaphore.available_permits(), permits);
    }

    #[test]
    fn guard_returns_the_permit_on_drop() {
        let semaphore = Semaphore::new(1);
        {
            let _guard = semaphore.acquire_guard();
            assert_eq!(semaphore.available_permits(), 0);
        }
        assert_eq!(semaphore.available_permits(), 1);
    }

    #[test]
    fn try_acquire_reports_contention() {
        let semaphore = Semaphore::new(1);
        let first = semaphore.try_acquire().expect("first permit is free");
        assert!(semaphore.try_acquire().is_none());
        drop(first);
        assert!(semaphore.try_acquire().is_some());
    }

    #[test]
    fn timeout_gives_up_when_no_permit_arrives() {
        let semaphore = Semaphore::new(0);
        assert!(
            semaphore
                .try_acquire_timeout(Duration::from_millis(5))
                .is_none()
        );
    }
}
```

`State` is a struct with a single field rather than a bare `usize`. The indirection
costs nothing and leaves room for more state, such as a closed flag, without changing
every lock site.

`acquire_guard` returns `SemaphoreGuard<'_>`, whose lifetime borrows the semaphore. The
guard cannot outlive the semaphore, and code that shares the semaphore between threads
must therefore share it by reference, through `Arc` or a scope.

`try_acquire` returns `Option<SemaphoreGuard<'_>>`, so the caller either holds a permit
or knows it does not, and cannot forget to release one it took.

`try_acquire_timeout` checks the count, and if no permit is free, waits once with
`wait_timeout`. After the wait it checks the count again and returns `None` if it is
still zero. The boolean that reports whether the wait timed out is ignored, because the
count is the authoritative answer.

`release` is private. The only way to return a permit is to drop a guard, which rules
out releasing a permit that was never taken.

`never_exceeds_the_permit_count` runs 32 threads against four permits. Each thread
increments an `active` counter after acquiring, records the maximum with `fetch_max`,
sleeps for a millisecond, and decrements. The test requires the recorded peak to be at
most four and all permits to be back at the end.

## Intuition

**Three threads contending for a semaphore with two permits**

| time | thread | action | `available` after |
|---|---|---|---|
| 1 | A | `acquire_guard`: count is 2, take one | 1 |
| 2 | B | `acquire_guard`: count is 1, take one | 0 |
| 3 | C | `acquire_guard`: count is 0, `wait` releases the lock and parks | 0 |
| 4 | A | guard dropped: `release` increments and calls `notify_one` | 1 |
| 5 | C | wakes, reacquires the lock, loop sees 1, takes it | 0 |
| 6 | B | guard dropped | 1 |
| 7 | C | guard dropped | 2 |

## Time and Space Complexity

| Operation | Time | Space |
|---|---|---|
| `acquire_guard`, permit free | one lock acquisition | none |
| `acquire_guard`, no permit | blocks until a release; one context switch to wake | the parked thread's stack |
| `try_acquire` | one lock acquisition | none |
| guard drop | one lock acquisition and one notification | none |
| memory | | one `Mutex<usize>` and one `Condvar` |

## Limitations

**`acquire` does not hold a permit.** Its body is `let _guard = self.acquire_guard();`.
The guard is bound to `_guard` and dropped at the end of the function, so `acquire`
waits until a permit is free, takes it, and returns it before the caller runs any code.
A caller that writes `semaphore.acquire(); do_work();` has no concurrency limit at all.
The method should either be removed or return the guard. The tests do not call it.

**The timeout is not a deadline.** `try_acquire_timeout` waits once. A spurious
wake-up, or a notification whose permit is taken by another thread first, makes it
return `None` before the timeout has elapsed. `Condvar::wait_timeout_while` re-checks
the condition and continues waiting for the remaining time, and it is the idiomatic
replacement:

```rust
pub fn try_acquire_timeout(&self, timeout: Duration) -> Option<SemaphoreGuard<'_>> {
    let state = self.state.lock().expect("semaphore mutex poisoned");
    let (mut state, result) = self
        .released
        .wait_timeout_while(state, timeout, |state| state.available == 0)
        .expect("semaphore mutex poisoned");
    if result.timed_out() {
        return None;
    }
    state.available -= 1;
    Some(SemaphoreGuard { semaphore: self })
}
```

`wait_timeout_while` returns immediately without waiting when a permit is already
free, so the separate fast path is no longer needed.

**No fairness.** A thread that arrives just as a permit is released can take it ahead
of one that has waited longer.

**No way to change the permit count.** A pool that grows or shrinks at run time needs
an `add_permits` method, and a shutdown path needs a way to wake all waiters with an
error.

**`available_permits` is stale on return.** The documentation comment says so: the
count can change before the caller reads it, so it is suitable for metrics and not for
deciding whether to acquire.

## Summary

- A counting semaphore is a count under a `Mutex` plus a `Condvar` that waiters park on;
  each release notifies one waiter.
- The condition is re-checked in a `while` loop after every wake-up.
- A guard that releases in `Drop` makes it impossible to leak a permit on an early
  return or a panic, and a private `release` makes it impossible to release one twice.
- `acquire` drops its guard before returning, so it does not limit concurrency.
- `wait_timeout_while` implements a time-limited wait that tolerates spurious wake-ups.

## References

- Edsger W. Dijkstra, "Cooperating sequential processes", technical report EWD-123,
  1965, which introduced semaphores.
- Standard library, [`Condvar::wait_timeout_while`](https://doc.rust-lang.org/std/sync/struct.Condvar.html#method.wait_timeout_while).
- Tokio, [`tokio::sync::Semaphore`](https://docs.rs/tokio/latest/tokio/sync/struct.Semaphore.html), the asynchronous equivalent with owned permits.
