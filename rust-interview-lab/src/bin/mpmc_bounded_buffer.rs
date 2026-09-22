use std::thread;

use std::collections::VecDeque;
use std::sync::{Condvar, Mutex};

pub struct BoundedBuffer<T> {
    queue: Mutex<VecDeque<T>>,
    capacity: usize,
    not_empty: Condvar,
    not_full: Condvar,
}

impl<T> BoundedBuffer<T> {
    pub fn new(capacity: usize) -> Self {
        assert!(capacity > 0, "capacity must be > 0");

        Self {
            queue: Mutex::new(VecDeque::with_capacity(capacity)),
            capacity,
            not_empty: Condvar::new(),
            not_full: Condvar::new(),
        }
    }

    /// Blocks while the buffer is full.
    pub fn push(&self, item: T) {
        let cap = self.capacity;

        let mut queue = self.queue.lock().unwrap();
        queue = self
            .not_full
            .wait_while(queue, |q| q.len() >= cap)
            .unwrap();

        queue.push_back(item);
        drop(queue);

        self.not_empty.notify_one();
    }

    /// Blocks while the buffer is empty.
    pub fn pop(&self) -> T {
        let mut queue = self.queue.lock().unwrap();
        queue = self
            .not_empty
            .wait_while(queue, |q| q.is_empty())
            .unwrap();

        let item = queue.pop_front().unwrap();
        self.not_full.notify_one();
        item
    }
}

fn main() {
    let buffer = BoundedBuffer::<(usize, usize)>::new(8);
    let buffer = &buffer;

    const PRODUCERS: usize = 4;
    const CONSUMERS: usize = 2;
    const PER_PRODUCER: usize = 10;
    const PER_CONSUMER: usize = PRODUCERS * PER_PRODUCER / CONSUMERS;

    thread::scope(|s| {
        for p in 0..PRODUCERS {
            s.spawn(move || {
                for i in 0..PER_PRODUCER {
                    buffer.push((p, i));
                }
            });
        }

        for c in 0..CONSUMERS {
            s.spawn(move || {
                for _ in 0..PER_CONSUMER {
                    let item = buffer.pop();
                    println!("consumer {c}: {item:?}");
                }
            });
        }
    });
}

