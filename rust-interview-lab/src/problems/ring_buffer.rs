//! Lock-free single-producer / single-consumer (SPSC) ring buffer.
//!
//! The classic producer/consumer exercise, but with no mutex: the producer owns
//! the `tail` index and the consumer owns the `head` index, and each publishes its
//! write with a release store so the other side sees the slot only after it is
//! initialized. This is the shape inside channel implementations, log shippers,
//! and kernel ring buffers.
//!
//! Two rules keep this sound:
//!
//! - exactly one thread calls [`SpscRing::push`] and exactly one calls
//!   [`SpscRing::pop`];
//! - a slot is written before `tail` is published, and read only after `head`
//!   reaches it.
//!
//! If you need many producers or consumers, use a mutex-backed queue such as
//! [`crate::problems::bounded_queue::BoundedQueue`].

use std::cell::UnsafeCell;
use std::mem::MaybeUninit;
use std::sync::atomic::{AtomicUsize, Ordering};

/// Ring buffer with capacity `N` (the maximum number of queued items).
pub struct SpscRing<T, const N: usize> {
    slots: [UnsafeCell<MaybeUninit<T>>; N],
    /// Next index to read. Written only by the consumer.
    head: AtomicUsize,
    /// Next index to write. Written only by the producer.
    tail: AtomicUsize,
}

// SAFETY: at most one thread mutates `head` and one mutates `tail`. A slot is
// initialized before `tail` is published with a release store, and the consumer
// performs an acquire load of `tail` before reading that slot, so there is no
// data race and no read of uninitialized memory under the SPSC discipline.
unsafe impl<T: Send, const N: usize> Sync for SpscRing<T, N> {}

impl<T, const N: usize> SpscRing<T, N> {
    /// Create an empty ring. Panics if `N` is zero.
    pub fn new() -> Self {
        assert!(N > 0, "ring capacity must be > 0");
        Self {
            slots: std::array::from_fn(|_| UnsafeCell::new(MaybeUninit::uninit())),
            head: AtomicUsize::new(0),
            tail: AtomicUsize::new(0),
        }
    }

    /// Maximum number of items the ring can hold.
    pub const fn capacity(&self) -> usize {
        N
    }

    /// Number of queued items. Only meaningful to the owning side in a race.
    pub fn len(&self) -> usize {
        self.tail
            .load(Ordering::Acquire)
            .wrapping_sub(self.head.load(Ordering::Acquire))
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }

    pub fn is_full(&self) -> bool {
        self.len() >= N
    }

    /// Enqueue a value, returning `Err(value)` when the ring is full.
    pub fn push(&self, value: T) -> Result<(), T> {
        let tail = self.tail.load(Ordering::Relaxed);
        let head = self.head.load(Ordering::Acquire);
        if tail.wrapping_sub(head) >= N {
            return Err(value);
        }

        let index = tail % N;
        // SAFETY: the slot at `index` is free because the ring is not full, and
        // only the producer writes it.
        unsafe { (*self.slots[index].get()).write(value) };

        // Publish the slot to the consumer.
        self.tail.store(tail.wrapping_add(1), Ordering::Release);
        Ok(())
    }

    /// Dequeue a value, or `None` when the ring is empty.
    pub fn pop(&self) -> Option<T> {
        let head = self.head.load(Ordering::Relaxed);
        let tail = self.tail.load(Ordering::Acquire);
        if head == tail {
            return None;
        }

        let index = head % N;
        // SAFETY: `head != tail`, so the producer has published this slot and
        // only the consumer reads it.
        let value = unsafe { (*self.slots[index].get()).assume_init_read() };

        // Publish the freed slot to the producer.
        self.head.store(head.wrapping_add(1), Ordering::Release);
        Some(value)
    }
}

impl<T, const N: usize> Default for SpscRing<T, N> {
    fn default() -> Self {
        Self::new()
    }
}

impl<T, const N: usize> Drop for SpscRing<T, N> {
    fn drop(&mut self) {
        // Drop any items that were never popped.
        while self.pop().is_some() {}
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;
    use std::sync::atomic::AtomicUsize;
    use std::thread;

    #[test]
    fn is_fifo_within_capacity() {
        let ring = SpscRing::<u32, 4>::new();
        assert!(ring.push(1).is_ok());
        assert!(ring.push(2).is_ok());
        assert!(ring.push(3).is_ok());
        assert_eq!(ring.pop(), Some(1));
        assert_eq!(ring.pop(), Some(2));
        assert_eq!(ring.pop(), Some(3));
        assert_eq!(ring.pop(), None);
    }

    #[test]
    fn full_ring_returns_the_value() {
        let ring = SpscRing::<u32, 2>::new();
        assert!(ring.push(1).is_ok());
        assert!(ring.push(2).is_ok());
        assert!(ring.is_full());
        assert_eq!(ring.push(3), Err(3));
    }

    #[test]
    fn producer_and_consumer_run_concurrently_in_order() {
        const ITEMS: u64 = 50_000;
        const SENTINEL: u64 = u64::MAX;

        let ring = Arc::new(SpscRing::<u64, 256>::new());

        let producer = {
            let ring = Arc::clone(&ring);
            thread::spawn(move || {
                for value in 0..ITEMS {
                    let mut pending = value;
                    loop {
                        match ring.push(pending) {
                            Ok(()) => break,
                            Err(returned) => {
                                pending = returned;
                                thread::yield_now();
                            }
                        }
                    }
                }
                let mut pending = SENTINEL;
                loop {
                    match ring.push(pending) {
                        Ok(()) => break,
                        Err(returned) => {
                            pending = returned;
                            thread::yield_now();
                        }
                    }
                }
            })
        };

        let consumer = {
            let ring = Arc::clone(&ring);
            thread::spawn(move || {
                let mut received = Vec::with_capacity(ITEMS as usize);
                loop {
                    match ring.pop() {
                        Some(SENTINEL) => break,
                        Some(value) => received.push(value),
                        None => thread::yield_now(),
                    }
                }
                received
            })
        };

        producer.join().expect("producer panicked");
        let received = consumer.join().expect("consumer panicked");

        assert_eq!(received, (0..ITEMS).collect::<Vec<_>>());
    }

    #[test]
    fn dropped_ring_drops_queued_items() {
        struct Tracker(Arc<AtomicUsize>);
        impl Drop for Tracker {
            fn drop(&mut self) {
                self.0.fetch_add(1, Ordering::SeqCst);
            }
        }

        let dropped = Arc::new(AtomicUsize::new(0));
        {
            let ring = SpscRing::<Tracker, 4>::new();
            assert!(ring.push(Tracker(Arc::clone(&dropped))).is_ok());
            assert!(ring.push(Tracker(Arc::clone(&dropped))).is_ok());
            assert!(ring.push(Tracker(Arc::clone(&dropped))).is_ok());
        }
        assert_eq!(dropped.load(Ordering::SeqCst), 3);
    }
}
