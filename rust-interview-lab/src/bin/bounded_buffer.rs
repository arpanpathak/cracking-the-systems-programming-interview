use std::collections::VecDeque;
use std::sync::{Arc, Condvar, Mutex};
use std::thread;
use std::time::Duration;

// A thread-safe bounded buffer (a "shelf" that holds at most `capacity` items).
//
// Three fields do all the work:
//   - `inner`     : the actual VecDeque, wrapped in a Mutex so only one thread
//                   touches it at a time.
//   - `not_empty` : waiting room for CONSUMERS. A consumer sleeps here when the
//                   shelf is empty. Producers ring this bell after pushing.
//   - `not_full`  : waiting room for PRODUCERS. A producer sleeps here when the
//                   shelf is full. Consumers ring this bell after popping.
//
// Two separate condvars so we always wake the RIGHT kind of thread.
// One shared condvar would cause livelock: consumers waking consumers,
// producers waking producers, everyone re-checking and going back to sleep.
struct BoundedQueue<T> {
    inner: Mutex<VecDeque<T>>,
    capacity: usize,
    not_empty: Condvar,
    not_full: Condvar,
}

impl<T> BoundedQueue<T> {
    fn new(capacity: usize) -> Self {
        // Capacity 0 makes no sense: no producer could ever push,
        // and every pop would block forever.
        assert!(capacity > 0, "capacity must be > 0");

        Self {
            inner: Mutex::new(VecDeque::with_capacity(capacity)),
            capacity,
            not_empty: Condvar::new(),
            not_full: Condvar::new(),
        }
    }

    fn push(&self, item: T) {
        // Acquire the shelf lock. `guard` is our exclusive handle to the deque.
        let mut guard = self.inner.lock().unwrap();

        // Wait while the shelf is full.
        //
        // Why `while` and not `if`:
        //   1. Condvars are allowed to wake up for no reason (spurious wakeup).
        //   2. Even on a real wakeup, another producer may have raced us and
        //      taken the free slot before we reacquired the lock.
        // So we must re-check the condition every time we wake.
        //
        // Why `guard = ...wait(guard)`:
        //   `wait` consumes the guard (it releases the lock on our behalf),
        //   puts us to sleep, then re-locks and hands us a NEW guard.
        //   The reassignment just means "here's my fresh key to the shelf."
        //   The VecDeque inside is the same one — we're not replacing the queue.
        while guard.len() == self.capacity {
            guard = self.not_full.wait(guard).unwrap();
        }

        // We have room. Add the item to the back of the deque.
        guard.push_back(item);

        // Release the lock BEFORE ringing the bell.
        // This is an optimization, not a correctness requirement.
        // If we notify while still holding the lock, the thread we wake will
        // immediately block on `lock()` until we release it — a wasted wakeup.
        drop(guard);

        // Ring the "not empty" bell: one consumer can now make progress.
        // `notify_one` (not `notify_all`) because exactly ONE item was added,
        // so only ONE consumer can succeed. Waking all of them = stampede.
        self.not_empty.notify_one();
    }

    fn pop(&self) -> T {
        // Acquire the shelf lock.
        let mut guard = self.inner.lock().unwrap();

        // Wait while the shelf is empty.
        // Same `while` reasoning as push: spurious wakeups + races with other
        // consumers who may have grabbed the item before we reacquired the lock.
        while guard.is_empty() {
            guard = self.not_empty.wait(guard).unwrap();
        }

        // Safe to unwrap: the `while` loop guarantees the deque is non-empty,
        // and we hold the lock so nobody can change that between the check
        // and this line.
        let item = guard.pop_front().unwrap();

        // Release before notifying (same optimization as in push).
        drop(guard);

        // Ring the "not full" bell: one producer can now make progress.
        // Exactly one slot opened, so wake exactly one producer.
        self.not_full.notify_one();

        item
    }
}

fn main() {
    // Small capacity (3) so that with two slow consumers you can actually
    // SEE producers block: the queue fills up and push() sleeps in `not_full`.
    let queue = Arc::new(BoundedQueue::new(3));

    let mut handles = vec![];

    // ---- Producers ----
    // Two producers, each pushes 5 items. `Arc::clone` bumps the refcount so
    // each thread shares the same queue; ownership of the clone moves in.
    for p in 0..2 {
        let q = Arc::clone(&queue);
        handles.push(thread::spawn(move || {
            for i in 0..5 {
                let item = format!("p{}:item{}", p, i);
                println!("  [producer {}] pushing {}", p, item);
                q.push(item);
                // Slow down so we don't blast through the whole buffer instantly.
                thread::sleep(Duration::from_millis(30));
            }
        }));
    }

    // ---- Consumers ----
    // Two consumers, each pops 5 items. Consumers are SLOWER than producers
    // here (60ms vs 30ms), so the queue fills up and you'll see producers
    // stall on `not_full.wait(...)`.
    for c in 0..2 {
        let q = Arc::clone(&queue);
        handles.push(thread::spawn(move || {
            for _ in 0..5 {
                let item = q.pop();
                println!("[consumer {}] got {}", c, item);
                thread::sleep(Duration::from_millis(60));
            }
        }));
    }

    // Join everything. If our synchronization is wrong, this is where you'd
    // hang (a thread sleeping forever) or panic (unwrap on empty / on a
    // poisoned mutex after another thread panicked while holding it).
    for h in handles {
        h.join().unwrap();
    }
    println!("done");
}