// ch19/ring_buffer.rs: Hand-rolled fixed-capacity ring buffer (without VecDeque)
// paired with a Mutex and dual Condvars for thread-safe bounded queuing.
use std::sync::{Arc, Condvar, Mutex};
use std::thread;

type QueueResult<T> = Result<T, &'static str>;

const POISONED: &str = "a thread panicked while holding the ring mutex";
const PANICKED: &str = "a worker thread panicked";

/// Fixed-capacity circular buffer backed by Vec<Option<T>>.
/// Tracking (head, len) instead of (head, tail) avoids the classic ambiguity
/// where head == tail could mean either completely empty or completely full.
struct Ring<T> {
    buf: Vec<Option<T>>, // Fixed length after construction; never reallocates
    head: usize,         // Index of the oldest live element
    len: usize,          // Count of live elements currently stored
}

impl<T> Ring<T> {
    fn new(capacity: usize) -> Self {
        let cap = capacity.max(1);
        Self {
            buf: (0..cap).map(|_| None).collect(),
            head: 0,
            len: 0,
        }
    }

    fn is_full(&self) -> bool {
        self.len == self.buf.len()
    }

    fn is_empty(&self) -> bool {
        self.len == 0
    }

    /// Inserts an item at the logical tail in O(1) time.
    /// Caller guarantees `!self.is_full()`.
    fn push_back(&mut self, item: T) {
        let tail = (self.head + self.len) % self.buf.len();
        self.buf[tail] = Some(item);
        self.len += 1;
    }

    /// Removes and returns the oldest item at `head` in O(1) time.
    /// `Option::take()` moves ownership of any non-Copy `T` out safely and leaves `None`.
    fn pop_front(&mut self) -> Option<T> {
        let item = self.buf[self.head].take()?;
        self.head = (self.head + 1) % self.buf.len();
        self.len -= 1;
        Some(item)
    }
}

struct BoundedRingQueue<T> {
    ring: Mutex<Ring<T>>,
    not_full: Condvar,
    not_empty: Condvar,
}

impl<T> BoundedRingQueue<T> {
    fn new(capacity: usize) -> Self {
        Self {
            ring: Mutex::new(Ring::new(capacity)),
            not_full: Condvar::new(),
            not_empty: Condvar::new(),
        }
    }

    fn push(&self, item: T) -> QueueResult<()> {
        let guard = self.ring.lock().map_err(|_| POISONED)?;
        let mut ring = self
            .not_full
            .wait_while(guard, |r| r.is_full())
            .map_err(|_| POISONED)?;

        ring.push_back(item);
        drop(ring); // Release lock before waking so the consumer does not immediately re-block
        self.not_empty.notify_one();
        Ok(())
    }

    fn pop(&self) -> QueueResult<T> {
        let guard = self.ring.lock().map_err(|_| POISONED)?;
        let mut ring = self
            .not_empty
            .wait_while(guard, |r| r.is_empty())
            .map_err(|_| POISONED)?;

        let item = ring
            .pop_front()
            .ok_or("ring was empty after wait_while")?;
        drop(ring);
        self.not_full.notify_one();
        Ok(item)
    }
}

fn main() -> QueueResult<()> {
    // Use non-Copy String values to verify ownership transfer via Option::take()
    // across many wrap-around cycles on a 4-slot ring buffer.
    const TOTAL: usize = 200;
    let queue = Arc::new(BoundedRingQueue::<String>::new(4));

    let producer = {
        let q = Arc::clone(&queue);
        thread::spawn(move || -> QueueResult<()> {
            for i in 0..TOTAL {
                q.push(format!("msg-{i}"))?;
            }
            Ok(())
        })
    };

    for expected in 0..TOTAL {
        let received = queue.pop()?;
        assert_eq!(received, format!("msg-{expected}"));
    }

    producer.join().map_err(|_| PANICKED)??;
    println!("hand-rolled ring queue: {TOTAL} String messages transferred in strict FIFO order (verified)");
    Ok(())
}
