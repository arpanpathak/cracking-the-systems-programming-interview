//! Single flight: concurrent calls with the same key share one execution.
//!
//! The first caller marks the key in progress and runs the work without
//! holding the lock. Later callers with that key wait for its result, while
//! calls with other keys run in parallel. A result is kept, so a retry after
//! success gets the stored result. A failure is not kept, so a retry runs the
//! work again. A panic in the work clears the mark, so waiters are not stranded.
//!
//! Run with: cargo run --bin single_flight

use std::{
    collections::HashMap,
    hash::Hash,
    panic::{self, AssertUnwindSafe},
    sync::{
        Barrier,
        Condvar,
        Mutex,
        MutexGuard,
        atomic::{AtomicUsize, Ordering::Relaxed},
    },
    thread,
    time::{Duration, Instant},
};

type Error = Box<dyn std::error::Error + Send + Sync>;

/// The state of one key.
enum Slot<V> {
    InProgress,
    Done(V),
}

/// Results by key, with at most one execution in flight per key.
pub struct SingleFlight<K, V> {
    slots: Mutex<HashMap<K, Slot<V>>>,
    finished: Condvar,
}

/// The claim of the caller that is running the work for `key`. If it is
/// dropped while it still holds the key, after an error or a panic, it clears
/// the `InProgress` mark and wakes the waiters, so one of them can run the work.
struct Claim<'a, K: Eq + Hash, V> {
    flight: &'a SingleFlight<K, V>,
    key: Option<K>,
}

impl<K: Eq + Hash, V> Drop for Claim<'_, K, V> {
    fn drop(&mut self) {
        if let Some(key) = self.key.take() {
            self.flight.lock().remove(&key);
            self.flight.finished.notify_all();
        }
    }
}

impl<K: Eq + Hash, V> SingleFlight<K, V> {
    /// The map, even if a thread panicked while holding the lock: every
    /// update leaves the map consistent, so its contents are still valid.
    fn lock(&self) -> MutexGuard<'_, HashMap<K, Slot<V>>> {
        self.slots
            .lock()
            .unwrap_or_else(|poisoned| poisoned.into_inner())
    }
}

impl<K, V> SingleFlight<K, V>
where
    K: Eq + Hash + Clone,
    V: Clone,
{
    pub fn new() -> Self {
        Self {
            slots: Mutex::new(HashMap::new()),
            finished: Condvar::new(),
        }
    }

    /// Return the stored result for `key`, wait for the execution in flight,
    /// or run `work` if neither exists.
    pub fn execute<F>(&self, key: K, work: F) -> Result<V, Error>
    where
        F: FnOnce() -> Result<V, Error>,
    {
        let mut slots = self.lock();
        loop {
            match slots.get(&key) {
                Some(Slot::Done(value)) => return Ok(value.clone()),
                Some(Slot::InProgress) => {
                    slots = self
                        .finished
                        .wait(slots)
                        .unwrap_or_else(|poisoned| poisoned.into_inner());
                }
                None => break,
            }
        }
        slots.insert(key.clone(), Slot::InProgress);
        drop(slots);

        let mut claim = Claim {
            flight: self,
            key: Some(key),
        };
        let value = work()?;

        let key = claim.key.take().expect("claim holds its key");
        self.lock().insert(key, Slot::Done(value.clone()));
        self.finished.notify_all();
        Ok(value)
    }
}

/// Run `call` on `threads` threads that start together. Returns the results
/// and the time from the start to the last return.
fn together<T: Send>(threads: usize, call: impl Fn(usize) -> T + Sync) -> (Vec<T>, Duration) {
    let start_line = Barrier::new(threads);
    let start = Instant::now();
    let results = thread::scope(|scope| {
        let handles: Vec<_> = (0..threads)
            .map(|i| {
                let (start_line, call) = (&start_line, &call);
                scope.spawn(move || {
                    start_line.wait();
                    call(i)
                })
            })
            .collect();
        handles
            .into_iter()
            .map(|handle| handle.join().expect("caller thread"))
            .collect()
    });
    (results, start.elapsed())
}

fn main() -> Result<(), Error> {
    let charges = AtomicUsize::new(0);
    let charge = |order: &str| -> Result<String, Error> {
        charges.fetch_add(1, Relaxed);
        thread::sleep(Duration::from_millis(100));
        Ok(format!("txn-{order}"))
    };

    println!("1. Eight concurrent calls with one key");
    let flight = SingleFlight::new();
    let (results, elapsed) = together(8, |_| flight.execute("order-1", || charge("order-1")));
    let agreed = results
        .iter()
        .all(|result| matches!(result, Ok(txn) if txn == "txn-order-1"));
    println!(
        "  executions {}, all got txn-order-1: {agreed}, {:.0} ms",
        charges.swap(0, Relaxed),
        elapsed.as_secs_f64() * 1000.0
    );

    println!("\n2. Four concurrent calls with four keys");
    let orders = ["order-1", "order-2", "order-3", "order-4"];
    let flight = SingleFlight::new();
    let (_, elapsed) = together(4, |i| flight.execute(orders[i], || charge(orders[i])));
    println!(
        "  executions {}, {:.0} ms",
        charges.swap(0, Relaxed),
        elapsed.as_secs_f64() * 1000.0
    );

    println!("\n3. A failure is not stored");
    let flight = SingleFlight::new();
    let declined = flight.execute("order-5", || Err("card declined".into()));
    let retried = flight.execute("order-5", || charge("order-5"));
    println!(
        "  first: {declined:?}, retry: {retried:?}, executions {}",
        charges.swap(0, Relaxed)
    );

    println!("\n4. The work panics while another caller waits");
    let flight = SingleFlight::new();
    let (results, _) = together(2, |i| {
        if i == 1 {
            thread::sleep(Duration::from_millis(20));
        }
        panic::catch_unwind(AssertUnwindSafe(|| {
            flight.execute("order-6", || {
                if i == 0 {
                    thread::sleep(Duration::from_millis(50));
                    panic!("payment provider crashed");
                }
                charge("order-6")
            })
        }))
        .map_err(|_| "panicked")
    });
    for (i, result) in results.iter().enumerate() {
        println!("  caller {i}: {result:?}");
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn concurrent_calls_with_one_key_run_once() {
        let runs = AtomicUsize::new(0);
        let flight = SingleFlight::new();
        let (results, _) = together(8, |_| {
            flight.execute("k", || {
                runs.fetch_add(1, Relaxed);
                thread::sleep(Duration::from_millis(30));
                Ok(7)
            })
        });
        assert_eq!(runs.load(Relaxed), 1);
        assert!(
            results
                .iter()
                .all(|result| matches!(result, Ok(7)))
        );
    }

    #[test]
    fn a_failure_lets_the_next_call_run() {
        let flight = SingleFlight::new();
        assert!(flight.execute("k", || Err("no".into())).is_err());
        assert_eq!(flight.execute("k", || Ok(1)).unwrap(), 1);
        assert_eq!(flight.execute("k", || Ok(2)).unwrap(), 1);
    }
}
