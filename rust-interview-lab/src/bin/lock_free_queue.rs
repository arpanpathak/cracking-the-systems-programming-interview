use std::{
    cell::UnsafeCell,
    mem::MaybeUninit,
    sync::atomic::{
        AtomicU64, AtomicUsize,
        Ordering::{Acquire, Relaxed, Release},
    },
    thread,
};

struct Slot<T> {
    seq: AtomicUsize,
    data: UnsafeCell<MaybeUninit<T>>,
}

pub struct LockFreeQueue<T> {
    buf: Box<[Slot<T>]>,
    mask: usize,
    head: AtomicUsize,
    tail: AtomicUsize,
}

unsafe impl<T: Send> Sync for LockFreeQueue<T> {}

unsafe impl<T: Send> Send for LockFreeQueue<T> {}

impl<T> LockFreeQueue<T> {
    fn new(capacity: usize) -> Self {
        // One slot is not enough: "full" and "empty one lap later" share a seq.
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

    fn push(&self, value: T) -> Result<(), T> {
        let mut tail = self.tail.load(Relaxed);

        loop {
            let seq = self.buf[tail & self.mask].seq.load(Acquire);

            if seq < tail {
                return Err(value); // full
            }

            if seq > tail {
                tail = self.tail.load(Relaxed); // another producer took it
                continue;
            }

            match self.tail.compare_exchange_weak(tail, tail + 1, Relaxed, Relaxed) {
                Ok(_) => break,
                Err(current) => tail = current,
            }
        }

        let slot = &self.buf[tail & self.mask];
        unsafe { (*slot.data.get()).write(value) };
        slot.seq.store(tail + 1, Release); // full, ready for a consumer

        Ok(())
    }

    fn pop(&self) -> Option<T> {
        let mut head = self.head.load(Relaxed);

        loop {
            let seq = self.buf[head & self.mask].seq.load(Acquire);

            if seq < head + 1 {
                return None; // empty
            }

            if seq > head + 1 {
                head = self.head.load(Relaxed); // another consumer took it
                continue;
            }

            match self.head.compare_exchange_weak(head, head + 1, Relaxed, Relaxed) {
                Ok(_) => break,
                Err(current) => head = current,
            }
        }

        let slot = &self.buf[head & self.mask];
        let value = unsafe { (*slot.data.get()).assume_init_read() };
        slot.seq.store(head + self.mask + 1, Release); // empty, ready for the next lap

        Some(value)
    }
}

impl<T> Drop for LockFreeQueue<T> {
    fn drop(&mut self) {
        while self.pop().is_some() {}
    }
}

fn main() {
    let queue = LockFreeQueue::<u64>::new(64);
    let sum = AtomicU64::new(0);

    thread::scope(|scope| {
        for _ in 0..2 {
            scope.spawn(|| {
                for value in 1..=1000 {
                    while queue.push(value).is_err() {
                        thread::yield_now();
                    }
                }
            });
        }

        for _ in 0..2 {
            scope.spawn(|| {
                for _ in 0..1000 {
                    let value = loop {
                        if let Some(value) = queue.pop() {
                            break value;
                        }
                        thread::yield_now();
                    };

                    sum.fetch_add(value, Relaxed);
                }
            });
        }
    });

    println!("sum = {}", sum.load(Relaxed)); // 2 * (1 + 2 + ... + 1000) = 1001000
}
