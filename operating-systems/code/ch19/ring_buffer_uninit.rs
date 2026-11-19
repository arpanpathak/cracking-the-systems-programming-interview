// ch19/ring_buffer_uninit.rs: Zero-overhead fixed-capacity ring buffer backed by
// Box<[MaybeUninit<T>]>, eliminating Option<T>'s discriminant + padding overhead.
use std::mem::{self, MaybeUninit};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Condvar, Mutex};
use std::thread;

type QueueResult<T> = Result<T, &'static str>;

const POISONED: &str = "a thread panicked while holding the raw ring mutex";
const PANICKED: &str = "a worker thread panicked";

/// Fixed-capacity ring storing raw MaybeUninit<T> slots with zero tag overhead.
/// Invariant: slots at `(head + k) % buf.len()` for `0 <= k < len` are initialized;
/// all remaining slots are uninitialized and must never be read or dropped.
struct RawRing<T> {
    buf: Box<[MaybeUninit<T>]>,
    head: usize,
    len: usize,
}

impl<T> RawRing<T> {
    fn new(capacity: usize) -> Self {
        let cap = capacity.max(1);
        let buf = (0..cap).map(|_| MaybeUninit::uninit()).collect();
        Self {
            buf,
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

    /// Writes `item` into the uninitialized tail slot in O(1) time.
    /// Caller guarantees `!self.is_full()`.
    fn push_back(&mut self, item: T) {
        let tail = (self.head + self.len) % self.buf.len();
        self.buf[tail].write(item);
        self.len += 1;
    }

    /// Moves the oldest initialized element out of `buf[head]` in O(1) time.
    fn pop_front(&mut self) -> Option<T> {
        if self.len == 0 {
            return None;
        }
        // SAFETY: `self.len > 0` guarantees `self.buf[self.head]` was initialized by
        // `push_back`. Advancing `head` and decrementing `len` immediately marks this
        // slot uninitialized so it can never be read or dropped a second time.
        let item = unsafe { self.buf[self.head].assume_init_read() };
        self.head = (self.head + 1) % self.buf.len();
        self.len -= 1;
        Some(item)
    }
}

impl<T> Drop for RawRing<T> {
    fn drop(&mut self) {
        // MaybeUninit<T> does NOT run T's destructor automatically.
        // Pop and drop every remaining live slot; uninitialized slots are untouched.
        while self.pop_front().is_some() {}
    }
}

struct BoundedRawQueue<T> {
    ring: Mutex<RawRing<T>>,
    not_full: Condvar,
    not_empty: Condvar,
}

impl<T> BoundedRawQueue<T> {
    fn new(capacity: usize) -> Self {
        Self {
            ring: Mutex::new(RawRing::new(capacity)),
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
        drop(ring);
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
            .ok_or("raw ring was empty after wait_while")?;
        drop(ring);
        self.not_full.notify_one();
        Ok(item)
    }
}

struct DropTracker(Arc<AtomicUsize>);
impl Drop for DropTracker {
    fn drop(&mut self) {
        self.0.fetch_add(1, Ordering::Relaxed);
    }
}

fn main() -> QueueResult<()> {
    // 1. Verify memory layouts directly at runtime.
    println!(
        "layouts (bytes): u64={}, Option<u64>={}, MaybeUninit<u64>={}, Option<Box<u64>>={} (niche), Option<String>={} (niche)",
        mem::size_of::<u64>(),
        mem::size_of::<Option<u64>>(),
        mem::size_of::<MaybeUninit<u64>>(),
        mem::size_of::<Option<Box<u64>>>(),
        mem::size_of::<Option<String>>(),
    );
    assert_eq!(mem::size_of::<Option<u64>>(), 16);
    assert_eq!(mem::size_of::<MaybeUninit<u64>>(), 8);
    assert_eq!(mem::size_of::<Option<Box<u64>>>(), 8);

    // 2. Verify multi-threaded FIFO wrap-around with heap-owning String values.
    const TOTAL: usize = 200;
    let queue = Arc::new(BoundedRawQueue::<String>::new(4));
    let producer = {
        let q = Arc::clone(&queue);
        thread::spawn(move || -> QueueResult<()> {
            for i in 0..TOTAL {
                q.push(format!("raw-{i}"))?;
            }
            Ok(())
        })
    };
    for expected in 0..TOTAL {
        assert_eq!(queue.pop()?, format!("raw-{expected}"));
    }
    producer.join().map_err(|_| PANICKED)??;

    // 3. Verify manual Drop destroys ONLY the 3 live items in an 8-slot ring (not the 5 uninit slots).
    let drops = Arc::new(AtomicUsize::new(0));
    {
        let mut ring = RawRing::new(8);
        for _ in 0..3 {
            ring.push_back(DropTracker(Arc::clone(&drops)));
        }
    }
    assert_eq!(drops.load(Ordering::Relaxed), 3);
    println!("MaybeUninit ring: {TOTAL} Strings transferred + partial-ring Drop destroyed 3/3 live items (verified)");
    Ok(())
}
