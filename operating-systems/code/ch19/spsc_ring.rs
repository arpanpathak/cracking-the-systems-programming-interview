// ch19/spsc_ring.rs: a lock-free ring buffer for one producer and one consumer.
use std::sync::Arc;
use std::sync::atomic::{AtomicU64, AtomicUsize, Ordering};
use std::thread;

const CAPACITY: usize = 1024;

/// A ring buffer that one thread writes and one other thread reads, without locks.
/// Head and tail indices are isolated on separate 64-byte cache lines to eliminate
/// false sharing between producer and consumer CPU cores.
#[repr(C, align(64))]
struct SpscRing {
    head: AtomicUsize, // written only by the consumer
    _pad: [u8; 56],    // 8 bytes head + 56 bytes padding = 64-byte cache line

    tail: AtomicUsize, // written only by the producer
    slots: Vec<AtomicU64>,
}

impl SpscRing {
    fn new() -> Self {
        SpscRing {
            head: AtomicUsize::new(0),
            _pad: [0; 56],
            tail: AtomicUsize::new(0),
            slots: (0..CAPACITY)
                .map(|_| AtomicU64::new(0))
                .collect(),
        }
    }

    /// Stores a value. Returns false when the ring is full.
    fn try_push(&self, value: u64) -> bool {
        // Memory Ordering Proof (Producer):
        // 1. `self.tail` is owned and mutated exclusively by the producer thread; reading our own
        //    latest write requires only `Ordering::Relaxed`.
        // 2. `self.head` is mutated by the consumer thread. Loading `head` with `Ordering::Acquire`
        //    synchronizes-with the consumer's `Ordering::Release` store in `try_pop()`, establishing
        //    a happens-before edge that proves the consumer has finished reading `slots[tail % CAPACITY]`
        //    before we overwrite it.
        // 3. Storing `tail + 1` with `Ordering::Release` prevents the compiler and out-of-order CPU
        //    store buffer from reordering the payload store (`slots[tail % CAPACITY]`) after the index
        //    publication, guaranteeing the consumer never observes an incremented `tail` with stale slot data.
        let tail = self.tail.load(Ordering::Relaxed);
        let head = self.head.load(Ordering::Acquire);

        if tail - head == CAPACITY {
            return false;
        }

        self.slots[tail % CAPACITY].store(value, Ordering::Relaxed);
        self.tail.store(tail + 1, Ordering::Release);
        true
    }

    /// Takes the oldest value. Returns None when the ring is empty.
    fn try_pop(&self) -> Option<u64> {
        // Memory Ordering Proof (Consumer):
        // 1. `self.head` is mutated exclusively by this consumer thread (`Ordering::Relaxed` load).
        // 2. Loading `self.tail` with `Ordering::Acquire` pairs with the producer's `Ordering::Release`
        //    store in `try_push()`, guaranteeing that the producer's payload write to `slots[head % CAPACITY]`
        //    is globally visible in L1/L2 cache before we read the slot.
        // 3. Publishing `head + 1` with `Ordering::Release` guarantees our read of `slots[head % CAPACITY]`
        //    completes before the producer can observe the freed capacity and reuse the slot.
        let head = self.head.load(Ordering::Relaxed);
        let tail = self.tail.load(Ordering::Acquire);

        if head == tail {
            return None;
        }

        let value = self.slots[head % CAPACITY].load(Ordering::Relaxed);
        self.head.store(head + 1, Ordering::Release);
        Some(value)
    }
}

fn main() -> Result<(), &'static str> {
    const ITEMS: u64 = 1_000_000;
    let ring = Arc::new(SpscRing::new());

    let producer_ring = Arc::clone(&ring);
    let producer = thread::spawn(move || {
        for value in 1..=ITEMS {
            while !producer_ring.try_push(value) {
                thread::yield_now();
            }
        }
    });

    let consumer_ring = Arc::clone(&ring);
    let consumer = thread::spawn(move || {
        let mut consumed_sum = 0;
        let mut taken = 0;

        while taken < ITEMS {
            let Some(value) = consumer_ring.try_pop() else {
                thread::yield_now();
                continue;
            };

            consumed_sum += value;
            taken += 1;
        }

        consumed_sum
    });

    producer
        .join()
        .map_err(|_| "the producer thread panicked")?;

    let consumed_sum = consumer
        .join()
        .map_err(|_| "the consumer thread panicked")?;

    let expected = ITEMS * (ITEMS + 1) / 2;
    let verdict = if expected == consumed_sum { "yes" } else { "NO" };

    println!("expected sum {expected}");
    println!("consumed sum {consumed_sum}");
    println!("match        {verdict}");

    Ok(())
}
