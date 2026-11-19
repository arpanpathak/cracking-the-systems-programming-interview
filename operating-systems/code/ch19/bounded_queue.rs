// ch19/bounded_queue.rs: a blocking queue of fixed capacity.
use std::collections::VecDeque;
use std::sync::{Arc, Condvar, Mutex};
use std::thread;

type QueueResult<T> = Result<T, &'static str>;

const POISONED: &str = "a thread panicked while it held the queue mutex";
const PANICKED: &str = "a worker thread panicked";

/// A queue that blocks producers while it is full and consumers while it is empty.
struct BoundedQueue<T> {
    capacity: usize,
    items: Mutex<VecDeque<T>>,
    is_full: Condvar,  // producers sleep here while the queue is full
    is_empty: Condvar, // consumers sleep here while the queue is empty
}

impl<T> BoundedQueue<T> {
    fn new(capacity: usize) -> Self {
        // A capacity of 0 would block every push forever, so the minimum is 1.
        BoundedQueue {
            capacity: capacity.max(1),
            items: Mutex::new(VecDeque::new()),
            is_full: Condvar::new(),
            is_empty: Condvar::new(),
        }
    }

    /// Appends one item. Waits while the queue is full.
    fn push(&self, item: T) -> QueueResult<()> {
        let items = self.items.lock().map_err(|_| POISONED)?;

        let mut items = self
            .is_full
            .wait_while(items, |q| q.len() == self.capacity)
            .map_err(|_| POISONED)?;

        items.push_back(item);
        self.is_empty.notify_one();

        Ok(())
    }

    /// Removes the oldest item. Waits while the queue is empty.
    fn pop(&self) -> QueueResult<T> {
        let items = self.items.lock().map_err(|_| POISONED)?;

        let mut items = self
            .is_empty
            .wait_while(items, |q| q.is_empty())
            .map_err(|_| POISONED)?;

        let item = items
            .pop_front()
            .ok_or("the queue was empty after the wait")?;

        self.is_full.notify_one();

        Ok(item)
    }
}

fn main() -> QueueResult<()> {
    const ITEMS_PER_THREAD: u64 = 50_000;
    const THREAD_PAIRS: u64 = 2;

    let queue = Arc::new(BoundedQueue::new(8));
    let mut producers = Vec::new();
    let mut consumers = Vec::new();

    for producer in 0..THREAD_PAIRS {
        let queue = Arc::clone(&queue);

        producers.push(thread::spawn(move || -> QueueResult<()> {
            let first = producer * ITEMS_PER_THREAD + 1;

            for value in first..first + ITEMS_PER_THREAD {
                queue.push(value)?;
            }

            Ok(())
        }));
    }

    for _ in 0..THREAD_PAIRS {
        let queue = Arc::clone(&queue);

        consumers.push(thread::spawn(move || -> QueueResult<u64> {
            let mut sum = 0;

            for _ in 0..ITEMS_PER_THREAD {
                sum += queue.pop()?;
            }

            Ok(sum)
        }));
    }

    for producer in producers {
        let pushed = producer
            .join()
            .map_err(|_| PANICKED)?;

        pushed?;
    }

    let mut consumed = 0;

    for consumer in consumers {
        let sum = consumer
            .join()
            .map_err(|_| PANICKED)?;

        consumed += sum?;
    }

    let item_count = THREAD_PAIRS * ITEMS_PER_THREAD;
    let expected = item_count * (item_count + 1) / 2;
    let verdict = if expected == consumed { "yes" } else { "NO" };

    println!("expected sum {expected}");
    println!("consumed sum {consumed}");
    println!("match        {verdict}");

    Ok(())
}
