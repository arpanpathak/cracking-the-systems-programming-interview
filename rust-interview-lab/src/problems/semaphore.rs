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
