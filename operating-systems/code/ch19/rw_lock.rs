// ch19/rw_lock.rs: a reader-writer lock built from a mutex and a condition variable.
use std::sync::atomic::{AtomicI64, AtomicU64, Ordering};
use std::sync::{Arc, Condvar, Mutex};
use std::thread;

type LockResult<T> = Result<T, &'static str>;

const POISONED: &str = "a thread panicked while it held the state mutex";
const PANICKED: &str = "a worker thread panicked";

/// Who is inside the lock, and who is waiting to write.
#[derive(Default)]
struct LockState {
    readers_active: u32,
    writers_waiting: u32,
    writer_active: bool,
}

impl LockState {
    /// A reader waits for an active writer, and also lets waiting writers go first.
    fn reader_must_wait(&self) -> bool {
        self.writer_active || self.writers_waiting > 0
    }

    /// A writer waits until nobody else is inside.
    fn writer_must_wait(&self) -> bool {
        self.writer_active || self.readers_active > 0
    }
}

/// Many readers may hold the lock together. A writer holds it alone.
#[derive(Default)]
struct ReaderWriterLock {
    state: Mutex<LockState>,
    changed: Condvar,
}

impl ReaderWriterLock {
    fn lock_shared(&self) -> LockResult<()> {
        let state = self
            .state
            .lock()
            .map_err(|_| POISONED)?;

        let mut state = self
            .changed
            .wait_while(state, |state| state.reader_must_wait())
            .map_err(|_| POISONED)?;

        state.readers_active += 1;

        Ok(())
    }

    fn unlock_shared(&self) -> LockResult<()> {
        let mut state = self
            .state
            .lock()
            .map_err(|_| POISONED)?;

        state.readers_active -= 1;

        if state.readers_active == 0 {
            self.changed.notify_all();
        }

        Ok(())
    }

    fn lock_exclusive(&self) -> LockResult<()> {
        let mut state = self
            .state
            .lock()
            .map_err(|_| POISONED)?;

        state.writers_waiting += 1; // new readers now queue behind this writer

        let mut state = self
            .changed
            .wait_while(state, |state| state.writer_must_wait())
            .map_err(|_| POISONED)?;

        state.writers_waiting -= 1;
        state.writer_active = true;

        Ok(())
    }

    fn unlock_exclusive(&self) -> LockResult<()> {
        let mut state = self
            .state
            .lock()
            .map_err(|_| POISONED)?;

        state.writer_active = false;
        self.changed.notify_all();

        Ok(())
    }
}

/// Two balances whose sum must stay 1000. Atomics make the fields shareable, and
/// the reader-writer lock is what keeps the pair consistent.
struct Accounts {
    lock: ReaderWriterLock,
    balance_a: AtomicI64,
    balance_b: AtomicI64,
    broken_reads: AtomicU64,
}

impl Accounts {
    /// Moves one unit from A to B while holding the lock exclusively.
    fn transfer_one(&self) -> LockResult<()> {
        self.lock.lock_exclusive()?;

        self.balance_a.fetch_sub(1, Ordering::Relaxed);
        self.balance_b.fetch_add(1, Ordering::Relaxed);

        self.lock.unlock_exclusive()
    }

    /// Reads both balances while holding the lock shared, and returns their sum.
    fn read_sum(&self) -> LockResult<i64> {
        self.lock.lock_shared()?;

        let balance_a = self.balance_a.load(Ordering::Relaxed);
        let balance_b = self.balance_b.load(Ordering::Relaxed);

        self.lock.unlock_shared()?;

        Ok(balance_a + balance_b)
    }
}

fn main() -> LockResult<()> {
    const WRITERS: usize = 2;
    const READERS: usize = 4;
    const ROUNDS: usize = 20_000;

    let accounts = Arc::new(Accounts {
        lock: ReaderWriterLock::default(),
        balance_a: AtomicI64::new(1000),
        balance_b: AtomicI64::new(0),
        broken_reads: AtomicU64::new(0),
    });

    let mut threads = Vec::new();

    for _ in 0..WRITERS {
        let accounts = Arc::clone(&accounts);

        threads.push(thread::spawn(move || -> LockResult<()> {
            for _ in 0..ROUNDS {
                accounts.transfer_one()?;
            }

            Ok(())
        }));
    }

    for _ in 0..READERS {
        let accounts = Arc::clone(&accounts);

        threads.push(thread::spawn(move || -> LockResult<()> {
            for _ in 0..ROUNDS {
                if accounts.read_sum()? != 1000 {
                    accounts.broken_reads.fetch_add(1, Ordering::Relaxed);
                }
            }

            Ok(())
        }));
    }

    for handle in threads {
        let finished = handle
            .join()
            .map_err(|_| PANICKED)?;

        finished?;
    }

    let transfers = accounts.balance_b.load(Ordering::Relaxed);
    let broken_reads = accounts.broken_reads.load(Ordering::Relaxed);

    println!("transfers    {transfers}");
    println!("broken reads {broken_reads}");

    Ok(())
}
