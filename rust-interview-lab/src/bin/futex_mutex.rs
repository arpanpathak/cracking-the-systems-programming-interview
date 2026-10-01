//! A mutex built on the futex system call.
//!
//! The lock is one 32-bit word with three states: 0 unlocked, 1 locked, and
//! 2 locked with threads that may be asleep waiting for it. Taking a free lock
//! and releasing a lock nobody waits for are single atomic instructions. Only a
//! thread that has to wait, and an unlock that has to wake it, enter the kernel.
//!
//! Linux only. Run with: cargo run --release --bin futex_mutex

#[cfg(target_os = "linux")]
mod linux {
    use std::{
        cell::UnsafeCell,
        ops::{Deref, DerefMut},
        sync::atomic::{
            AtomicU32,
            AtomicU64,
            Ordering::{Acquire, Relaxed, Release},
        },
    };

    const UNLOCKED: u32 = 0;
    const LOCKED: u32 = 1;
    const CONTENDED: u32 = 2;

    /// Sleep while `word` holds `expected`. The kernel checks the value and
    /// queues the thread as one step, so a wake that happens first is not lost.
    fn futex_wait(word: &AtomicU32, expected: u32) {
        // SAFETY: `word` is a valid, aligned u32 for the whole call, and a null
        // timeout means wait without a time limit.
        unsafe {
            libc::syscall(
                libc::SYS_futex,
                word.as_ptr(),
                libc::FUTEX_WAIT | libc::FUTEX_PRIVATE_FLAG,
                expected,
                std::ptr::null::<libc::timespec>(),
            );
        }
    }

    /// Wake one thread sleeping on `word`, if there is one.
    fn futex_wake_one(word: &AtomicU32) {
        // SAFETY: `word` is a valid, aligned u32 for the whole call.
        unsafe {
            libc::syscall(
                libc::SYS_futex,
                word.as_ptr(),
                libc::FUTEX_WAKE | libc::FUTEX_PRIVATE_FLAG,
                1,
            );
        }
    }

    /// A mutual-exclusion lock that sleeps in the kernel while it waits.
    pub struct FutexMutex<T> {
        state: AtomicU32,
        waits: AtomicU64,
        wakes: AtomicU64,
        value: UnsafeCell<T>,
    }

    // SAFETY: the lock gives one thread at a time access to `value`, so sharing
    // the mutex is safe whenever `T` may move between threads.
    unsafe impl<T: Send> Sync for FutexMutex<T> {}

    impl<T> FutexMutex<T> {
        pub const fn new(value: T) -> Self {
            Self {
                state: AtomicU32::new(UNLOCKED),
                waits: AtomicU64::new(0),
                wakes: AtomicU64::new(0),
                value: UnsafeCell::new(value),
            }
        }

        pub fn lock(&self) -> Guard<'_, T> {
            if self
                .state
                .compare_exchange(UNLOCKED, LOCKED, Acquire, Relaxed)
                .is_err()
            {
                self.lock_contended();
            }
            Guard { mutex: self }
        }

        /// The slow path: mark the lock contended, and sleep until it is free.
        fn lock_contended(&self) {
            while self.state.swap(CONTENDED, Acquire) != UNLOCKED {
                self.waits.fetch_add(1, Relaxed);
                futex_wait(&self.state, CONTENDED);
            }
        }

        fn unlock(&self) {
            if self.state.swap(UNLOCKED, Release) == CONTENDED {
                self.wakes.fetch_add(1, Relaxed);
                futex_wake_one(&self.state);
            }
        }

        /// The number of `futex` wait and wake calls this mutex has made.
        pub fn syscalls(&self) -> (u64, u64) {
            (self.waits.load(Relaxed), self.wakes.load(Relaxed))
        }

        pub fn into_inner(self) -> T {
            self.value.into_inner()
        }
    }

    /// Access to the value while the lock is held. Unlocks when dropped.
    pub struct Guard<'a, T> {
        mutex: &'a FutexMutex<T>,
    }

    impl<T> Deref for Guard<'_, T> {
        type Target = T;

        fn deref(&self) -> &T {
            // SAFETY: the guard exists only while this thread holds the lock.
            unsafe { &*self.mutex.value.get() }
        }
    }

    impl<T> DerefMut for Guard<'_, T> {
        fn deref_mut(&mut self) -> &mut T {
            // SAFETY: as in `deref`, and `&mut self` makes this the only borrow.
            unsafe { &mut *self.mutex.value.get() }
        }
    }

    impl<T> Drop for Guard<'_, T> {
        fn drop(&mut self) {
            self.mutex.unlock();
        }
    }
}

#[cfg(target_os = "linux")]
fn main() {
    use std::{
        sync::Mutex,
        thread,
        time::{Duration, Instant},
    };

    use linux::FutexMutex;

    const INCREMENTS: u64 = 1_000_000;

    /// Run `add` INCREMENTS times in total, split across `threads`.
    fn timed(threads: u64, add: &(dyn Fn() + Sync)) -> Duration {
        let start = Instant::now();
        thread::scope(|scope| {
            for _ in 0..threads {
                scope.spawn(|| (0..INCREMENTS / threads).for_each(|_| add()));
            }
        });
        start.elapsed()
    }

    // One untimed pass of each, so neither pays for a cold start in the table.
    let warm = FutexMutex::new(0u64);
    timed(1, &|| *warm.lock() += 1);
    let warm = Mutex::new(0u64);
    timed(1, &|| *warm.lock().unwrap() += 1);

    println!(
        "{:>7} {:>9} {:>8} {:>8} {:>12} {:>12}",
        "threads", "total", "waits", "wakes", "futex ms", "std ms"
    );
    for threads in [1, 2, 4] {
        let futex = FutexMutex::new(0u64);
        let futex_time = timed(threads, &|| *futex.lock() += 1);
        let (waits, wakes) = futex.syscalls();

        let std = Mutex::new(0u64);
        let std_time = timed(threads, &|| *std.lock().unwrap() += 1);
        assert_eq!(std.into_inner().unwrap(), INCREMENTS);

        println!(
            "{threads:>7} {:>9} {waits:>8} {wakes:>8} {:>12.1} {:>12.1}",
            futex.into_inner(),
            futex_time.as_secs_f64() * 1000.0,
            std_time.as_secs_f64() * 1000.0
        );
    }
}

#[cfg(not(target_os = "linux"))]
fn main() {
    eprintln!("futex_mutex uses the Linux futex system call; run it on Linux");
}

#[cfg(all(test, target_os = "linux"))]
mod tests {
    use std::thread;

    use super::linux::FutexMutex;

    #[test]
    fn an_uncontended_lock_makes_no_system_calls() {
        let mutex = FutexMutex::new(0);
        for _ in 0..1000 {
            *mutex.lock() += 1;
        }
        assert_eq!(mutex.syscalls(), (0, 0));
        assert_eq!(mutex.into_inner(), 1000);
    }

    #[test]
    fn contended_increments_are_not_lost() {
        let mutex = FutexMutex::new(0);
        thread::scope(|scope| {
            for _ in 0..8 {
                scope.spawn(|| {
                    for _ in 0..10_000 {
                        *mutex.lock() += 1;
                    }
                });
            }
        });
        assert_eq!(mutex.into_inner(), 80_000);
    }
}
