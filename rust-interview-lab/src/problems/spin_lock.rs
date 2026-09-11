//! A spin lock built from a single `AtomicBool`.
//!
//! This is the primitive to write when an interviewer asks for a lock from
//! scratch. The interesting part is not the loop; it is the memory ordering and
//! the ownership argument that make the unsafe block sound.
//!
//! - `lock`/`try_lock` use a compare-exchange with `Acquire` ordering, so the
//!   critical section observes every write the previous holder made before it
//!   released.
//! - `unlock` uses a `Release` store, so writes inside the critical section are
//!   visible to whoever acquires next.
//! - The guard derefs to `&T`/`&mut T`. Mutual exclusion is what makes handing out
//!   `&mut T` sound, and that is exactly what the lock guarantees.
//!
//! A spin lock is the wrong choice when the critical section can block or is
//! long: every waiting thread burns a core. Use it for very short sections on
//! dedicated cores, and prefer `std::sync::Mutex` (which parks the thread) in
//! general code.

use std::cell::UnsafeCell;
use std::hint::spin_loop;
use std::ops::{Deref, DerefMut};
use std::sync::atomic::{AtomicBool, Ordering};

/// A mutual-exclusion lock that busy-waits instead of parking.
pub struct SpinLock<T> {
    locked: AtomicBool,
    value: UnsafeCell<T>,
}

// SAFETY: `value` is only accessed while `locked` is held, and the acquire/release
// ordering on `locked` makes a hand-off between threads well defined. Sharing
// `&SpinLock` across threads therefore only requires the protected value to be
// `Send`, which lets one thread move data in and another move it out.
unsafe impl<T: Send> Sync for SpinLock<T> {}

/// Grants access to the protected value and releases the lock when dropped.
pub struct SpinGuard<'a, T> {
    lock: &'a SpinLock<T>,
}

impl<T> SpinLock<T> {
    /// Create an unlocked spin lock.
    pub const fn new(value: T) -> Self {
        Self {
            locked: AtomicBool::new(false),
            value: UnsafeCell::new(value),
        }
    }

    /// Acquire the lock, spinning until it is free.
    pub fn lock(&self) -> SpinGuard<'_, T> {
        loop {
            if self
                .locked
                .compare_exchange_weak(false, true, Ordering::Acquire, Ordering::Relaxed)
                .is_ok()
            {
                return SpinGuard { lock: self };
            }

            // Spin on a relaxed load so the contention loop does not keep
            // bouncing the cache line with exclusive accesses.
            while self.locked.load(Ordering::Relaxed) {
                spin_loop();
            }
        }
    }

    /// Acquire the lock only if it is free right now.
    pub fn try_lock(&self) -> Option<SpinGuard<'_, T>> {
        self.locked
            .compare_exchange(false, true, Ordering::Acquire, Ordering::Relaxed)
            .ok()
            .map(|_| SpinGuard { lock: self })
    }

    /// Whether the lock is currently held.
    pub fn is_locked(&self) -> bool {
        self.locked.load(Ordering::Relaxed)
    }

    fn unlock(&self) {
        self.locked.store(false, Ordering::Release);
    }
}

impl<T: Default> Default for SpinLock<T> {
    fn default() -> Self {
        Self::new(T::default())
    }
}

impl<T> Drop for SpinGuard<'_, T> {
    fn drop(&mut self) {
        self.lock.unlock();
    }
}

impl<T> Deref for SpinGuard<'_, T> {
    type Target = T;

    fn deref(&self) -> &T {
        // SAFETY: holding the guard means this thread has exclusive access.
        unsafe { &*self.lock.value.get() }
    }
}

impl<T> DerefMut for SpinGuard<'_, T> {
    fn deref_mut(&mut self) -> &mut T {
        // SAFETY: holding the guard means this thread has exclusive access.
        unsafe { &mut *self.lock.value.get() }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;
    use std::thread;

    #[test]
    fn serializes_concurrent_increments() {
        let lock = Arc::new(SpinLock::new(0usize));
        let mut handles = Vec::new();

        for _ in 0..8 {
            let lock = Arc::clone(&lock);
            handles.push(thread::spawn(move || {
                for _ in 0..1_000 {
                    *lock.lock() += 1;
                }
            }));
        }
        for handle in handles {
            handle.join().expect("worker panicked");
        }

        assert_eq!(*lock.lock(), 8_000);
    }

    #[test]
    fn try_lock_reports_contention() {
        let lock = SpinLock::new(1u32);
        let guard = lock.lock();
        assert!(lock.try_lock().is_none());
        assert!(lock.is_locked());
        drop(guard);
        assert!(lock.try_lock().is_some());
        assert!(!lock.is_locked());
    }

    #[test]
    fn guard_gives_mutable_access() {
        let lock = SpinLock::new(vec![1, 2, 3]);
        {
            let mut guard = lock.lock();
            guard.push(4);
        }
        assert_eq!(*lock.lock(), vec![1, 2, 3, 4]);
    }
}
