//! Bounded blocking queue with backpressure.
//!
//! Unbounded queues are a classic production failure: a fast producer and a slow
//! consumer turn into an OOM kill instead of a slow response. A bounded queue makes
//! the producer wait, which is backpressure, and it is the first thing a senior
//! systems interviewer looks for.
//!
//! This is an MPMC queue (many producers, many consumers) built from one `Mutex`
//! and two condition variables: `not_empty` for waiting consumers and `not_full`
//! for waiting producers. `close` unblocks everyone so shutdown cannot hang.

use std::collections::VecDeque;
use std::sync::{Condvar, Mutex};

struct State<T> {
    items: VecDeque<T>,
    capacity: usize,
    closed: bool,
}

/// A bounded MPMC queue. Share it behind `Arc`; all methods take `&self`.
pub struct BoundedQueue<T> {
    state: Mutex<State<T>>,
    not_empty: Condvar,
    not_full: Condvar,
}

impl<T> BoundedQueue<T> {
    /// Create a queue that holds at most `capacity` items.
    ///
    /// Panics if `capacity` is zero, because a zero-capacity queue can never make
    /// progress.
    pub fn new(capacity: usize) -> Self {
        assert!(capacity > 0, "capacity must be > 0");
        Self {
            state: Mutex::new(State {
                items: VecDeque::with_capacity(capacity),
                capacity,
                closed: false,
            }),
            not_empty: Condvar::new(),
            not_full: Condvar::new(),
        }
    }

    /// Push an item, blocking while the queue is full.
    ///
    /// Returns `Err(item)` if the queue is closed, so the caller keeps ownership
    /// instead of losing the value.
    pub fn push(&self, item: T) -> Result<(), T> {
        let mut state = self.state.lock().expect("queue mutex poisoned");
        loop {
            if state.closed {
                return Err(item);
            }
            if state.items.len() < state.capacity {
                state.items.push_back(item);
                self.not_empty.notify_one();
                return Ok(());
            }
            state = self.not_full.wait(state).expect("queue mutex poisoned");
        }
    }

    /// Pop an item, blocking while the queue is empty.
    ///
    /// Returns `None` once the queue is closed and drained, which is how a
    /// consumer loop terminates cleanly.
    pub fn pop(&self) -> Option<T> {
        let mut state = self.state.lock().expect("queue mutex poisoned");
        loop {
            if let Some(item) = state.items.pop_front() {
                self.not_full.notify_one();
                return Some(item);
            }
            if state.closed {
                return None;
            }
            state = self.not_empty.wait(state).expect("queue mutex poisoned");
        }
    }

    /// Pop without blocking.
    pub fn try_pop(&self) -> Option<T> {
        let mut state = self.state.lock().expect("queue mutex poisoned");
        let item = state.items.pop_front();
        if item.is_some() {
            self.not_full.notify_one();
        }
        item
    }

    /// Close the queue.
    ///
    /// Pending and future `pop` calls return `None` after the queue drains, and
    /// future `push` calls fail. Idempotent.
    pub fn close(&self) {
        let mut state = self.state.lock().expect("queue mutex poisoned");
        state.closed = true;
        drop(state);
        self.not_empty.notify_all();
        self.not_full.notify_all();
    }

    pub fn is_closed(&self) -> bool {
        self.state.lock().expect("queue mutex poisoned").closed
    }

    pub fn capacity(&self) -> usize {
        self.state.lock().expect("queue mutex poisoned").capacity
    }

    pub fn len(&self) -> usize {
        self.state.lock().expect("queue mutex poisoned").items.len()
    }

    pub fn is_empty(&self) -> bool {
        self.state
            .lock()
            .expect("queue mutex poisoned")
            .items
            .is_empty()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::thread;
    use std::time::Duration;

    #[test]
    fn preserves_order_across_threads() {
        let queue = Arc::new(BoundedQueue::new(8));
        let producer = {
            let queue = Arc::clone(&queue);
            thread::spawn(move || {
                for value in 0..1_000 {
                    queue.push(value).expect("queue stays open");
                }
                queue.close();
            })
        };

        let mut received = Vec::new();
        while let Some(value) = queue.pop() {
            received.push(value);
        }
        producer.join().expect("producer panicked");

        assert_eq!(received, (0..1_000).collect::<Vec<_>>());
    }

    #[test]
    fn never_exceeds_capacity() {
        let queue = Arc::new(BoundedQueue::new(4));
        let observed_peak = Arc::new(AtomicUsize::new(0));
        let producer = {
            let queue = Arc::clone(&queue);
            let observed_peak = Arc::clone(&observed_peak);
            thread::spawn(move || {
                for value in 0..200u32 {
                    queue.push(value).expect("queue stays open");
                    observed_peak.fetch_max(queue.len(), Ordering::SeqCst);
                }
                queue.close();
            })
        };

        while queue.pop().is_some() {
            thread::sleep(Duration::from_micros(50));
        }
        producer.join().expect("producer panicked");

        assert!(observed_peak.load(Ordering::SeqCst) <= 4);
    }

    #[test]
    fn close_wakes_a_blocked_consumer() {
        let queue = Arc::new(BoundedQueue::<u32>::new(1));
        let consumer = {
            let queue = Arc::clone(&queue);
            thread::spawn(move || queue.pop())
        };

        thread::sleep(Duration::from_millis(20));
        queue.close();

        assert_eq!(consumer.join().expect("consumer panicked"), None);
    }

    #[test]
    fn push_after_close_returns_the_item() {
        let queue = BoundedQueue::new(1);
        queue.close();
        assert_eq!(
            queue.push("workload".to_string()),
            Err("workload".to_string())
        );
    }
}
