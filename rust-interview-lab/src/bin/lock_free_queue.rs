//! A bounded lock-free queue for many producers and many consumers (Dmitry Vyukov's design).
//!
//! Every slot carries a sequence number that says whose turn the slot is:
//!
//! - `seq == pos`: empty and ready for the producer that claims position `pos`.
//! - `seq == pos + 1`: full and ready for the consumer that claims position `pos`.
//!
//! A thread claims a position by moving `tail` (producers) or `head` (consumers) forward
//! with a compare-and-swap, then owns that slot alone until it publishes the new `seq`.
//! The `Release` store of `seq` and the `Acquire` load pair up, so the value written into
//! the slot is visible before anyone reads it.

use std::{
    cell::UnsafeCell,
    mem::MaybeUninit,
    sync::atomic::{
        AtomicU64,
        AtomicUsize,
        Ordering::{Acquire, Relaxed, Release},
    },
    thread,
};

struct Slot<T> {
    /// Whose turn the slot is; see the module comment.
    seq: AtomicUsize,
    /// The value, written by exactly one producer and read by exactly one consumer.
    data: UnsafeCell<MaybeUninit<T>>,
}

pub struct LockFreeQueue<T> {
    buf: Box<[Slot<T>]>,
    /// `capacity - 1`: `pos & mask` is `pos % capacity` for a power-of-two capacity.
    mask: usize,
    /// The next position to pop.
    head: AtomicUsize,
    /// The next position to push.
    tail: AtomicUsize,
}

// The slot protocol gives each value to one thread at a time, so sharing the queue only
// needs the values themselves to be `Send`.
unsafe impl<T: Send> Sync for LockFreeQueue<T> {}

unsafe impl<T: Send> Send for LockFreeQueue<T> {}

impl<T> LockFreeQueue<T> {
    fn new(capacity: usize) -> Self {
        // With one slot, "full at lap n" and "empty at lap n + 1" share a sequence number.
        assert!(capacity >= 2 && capacity.is_power_of_two());

        let buf = (0..capacity)
            .map(|i| Slot {
                seq: AtomicUsize::new(i),
                data: UnsafeCell::new(MaybeUninit::uninit()),
            })
            .collect();

        Self {
            buf,
            mask: capacity - 1,
            head: AtomicUsize::new(0),
            tail: AtomicUsize::new(0),
        }
    }

    /// Adds `value`, or hands it back when the queue is full.
    fn push(&self, value: T) -> Result<(), T> {
        let mut tail = self.tail.load(Relaxed);

        loop {
            let seq = self.buf[tail & self.mask]
                .seq
                .load(Acquire);

            if seq < tail {
                return Err(value); // full: the slot still holds last lap's value
            }

            if seq > tail {
                tail = self.tail.load(Relaxed); // another producer took this position
                continue;
            }

            match self
                .tail
                .compare_exchange_weak(tail, tail + 1, Relaxed, Relaxed)
            {
                Ok(_) => break,
                Err(current) => tail = current,
            }
        }

        // Position `tail` is ours: no other thread touches this slot until we publish.
        let slot = &self.buf[tail & self.mask];
        unsafe { (*slot.data.get()).write(value) };

        slot.seq.store(tail + 1, Release);

        Ok(())
    }

    /// Removes the oldest value, or returns `None` when the queue is empty.
    fn pop(&self) -> Option<T> {
        let mut head = self.head.load(Relaxed);

        loop {
            let seq = self.buf[head & self.mask]
                .seq
                .load(Acquire);

            if seq < head + 1 {
                return None; // empty: no producer has filled this slot yet
            }

            if seq > head + 1 {
                head = self.head.load(Relaxed); // another consumer took this position
                continue;
            }

            match self
                .head
                .compare_exchange_weak(head, head + 1, Relaxed, Relaxed)
            {
                Ok(_) => break,
                Err(current) => head = current,
            }
        }

        // Position `head` is ours, and its producer published the value with `Release`.
        let slot = &self.buf[head & self.mask];
        let value = unsafe { (*slot.data.get()).assume_init_read() };

        // Free the slot for the producer one lap later.
        slot.seq
            .store(head + self.mask + 1, Release);

        Some(value)
    }
}

impl<T> Drop for LockFreeQueue<T> {
    /// Drops the values still queued; `MaybeUninit` never drops them on its own.
    fn drop(&mut self) {
        while self.pop().is_some() {}
    }
}

const PRODUCERS: u64 = 4;
const CONSUMERS: usize = 4;
const PER_PRODUCER: u64 = 100_000;

fn main() {
    let queue = LockFreeQueue::<u64>::new(64);
    let total = PRODUCERS * PER_PRODUCER;
    let popped = AtomicU64::new(0);
    let sum = AtomicU64::new(0);

    thread::scope(|scope| {
        for _ in 0..PRODUCERS {
            scope.spawn(|| {
                for value in 1..=PER_PRODUCER {
                    while queue.push(value).is_err() {
                        thread::yield_now(); // full: let a consumer run
                    }
                }
            });
        }

        for _ in 0..CONSUMERS {
            scope.spawn(|| {
                while popped.load(Relaxed) < total {
                    let Some(value) = queue.pop() else {
                        thread::yield_now(); // empty: let a producer run
                        continue;
                    };

                    sum.fetch_add(value, Relaxed);
                    popped.fetch_add(1, Relaxed);
                }
            });
        }
    });

    let expected = PRODUCERS * PER_PRODUCER * (PER_PRODUCER + 1) / 2;

    println!("popped {} values", popped.load(Relaxed));
    println!("sum = {}, expected {expected}", sum.load(Relaxed));
}

#[cfg(test)]
mod tests {
    use std::sync::Arc;

    use super::*;

    #[test]
    fn fifo_and_full() {
        let queue = LockFreeQueue::new(4);

        for value in 1..=4 {
            assert_eq!(queue.push(value), Ok(()));
        }

        assert_eq!(queue.push(5), Err(5));
        assert_eq!(queue.pop(), Some(1));
        assert_eq!(queue.push(5), Ok(()));

        let rest: Vec<i32> = std::iter::from_fn(|| queue.pop()).collect();
        assert_eq!(rest, [2, 3, 4, 5]);
        assert_eq!(queue.pop(), None);
    }

    #[test]
    fn drop_frees_values_still_queued() {
        let value = Arc::new(7);
        let queue = LockFreeQueue::new(8);

        for _ in 0..3 {
            assert!(queue.push(Arc::clone(&value)).is_ok());
        }
        assert_eq!(Arc::strong_count(&value), 4);

        drop(queue);
        assert_eq!(Arc::strong_count(&value), 1);
    }
}
