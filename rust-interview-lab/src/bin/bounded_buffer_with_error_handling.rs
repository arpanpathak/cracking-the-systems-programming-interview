use std::collections::VecDeque;
use std::fmt;
use std::sync::{Arc, Condvar, Mutex, PoisonError};
use std::thread;
use std::time::Duration;

#[derive(Debug)]
pub struct QueuePoisonedError;

impl fmt::Display for QueuePoisonedError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "The queue's internal mutex was poisoned by a panicking thread")
    }
}

impl std::error::Error for QueuePoisonedError {}

trait PoisonMap<T> {
    fn map_poison(self) -> Result<T, QueuePoisonedError>;
}

impl<T> PoisonMap<T> for Result<T, PoisonError<T>> {
    fn map_poison(self) -> Result<T, QueuePoisonedError> {
        self.map_err(|_| QueuePoisonedError)
    }
}

struct BoundedQueue<T> {
    inner: Mutex<VecDeque<T>>,
    capacity: usize,
    not_empty: Condvar,
    not_full: Condvar,
}

impl<T> BoundedQueue<T> {
    fn new(capacity: usize) -> Self {
        assert!(capacity > 0, "capacity must be > 0");
        Self {
            inner: Mutex::new(VecDeque::with_capacity(capacity)),
            capacity,
            not_empty: Condvar::new(),
            not_full: Condvar::new(),
        }
    }

    fn push(&self, item: T) -> Result<(), QueuePoisonedError> {
        let mut guard = self.inner.lock().map_poison()?;
        while guard.len() == self.capacity {
            guard = self.not_full.wait(guard).map_poison()?;
        }
        guard.push_back(item);
        drop(guard);
        self.not_empty.notify_one();
        Ok(())
    }

    fn pop(&self) -> Result<T, QueuePoisonedError> {
        let mut guard = self.inner.lock().map_poison()?;
        while guard.is_empty() {
            guard = self.not_empty.wait(guard).map_poison()?;
        }
        let item = guard.pop_front().unwrap();
        drop(guard);
        self.not_full.notify_one();
        Ok(item)
    }
}

fn main() {
    let queue = Arc::new(BoundedQueue::new(3));
    let mut handles = vec![];

    // ---- Producers ----
    for p in 0..2 {
        let q = Arc::clone(&queue);
        handles.push(thread::spawn(move || {
            for i in 0..5 {
                let item = format!("p{}:item{}", p, i);
                println!("  [producer {}] pushing {}", p, item);
                
                // Uses match, avoids naming an error variable, uses dbg!
                match q.push(item) {
                    Ok(_) => {}
                    Err(err) => {
                        dbg!(err);
                        break;
                    }
                }
                thread::sleep(Duration::from_millis(30));
            }
        }));
    }

    // ---- Consumers ----
    for c in 0..2 {
        let q = Arc::clone(&queue);
        handles.push(thread::spawn(move || {
            for _ in 0..5 {
                // Uses match, avoids naming an error variable, uses dbg!
                match q.pop() {
                    Ok(item) => {
                        println!("[consumer {}] got {}", c, item);
                    }
                    Err(err) => {
                        dbg!(err);
                        break;
                    }
                }
                thread::sleep(Duration::from_millis(60));
            }
        }));
    }

    // Join everything.
    for h in handles {
        match h.join() {
            Ok(_) => {}
            Err(err) => {
                dbg!(err);
            }
        }
    }
    println!("done");
}

#[cfg(test)]
mod tests {
    use super::*;

    // 1. Mark the test as one that MUST panic to pass
    // 2. Optional: use 'expected' to verify it panics with the correct error message
    #[test]
    #[should_panic(expected = "capacity must be > 0")]
    fn test_zero_capacity_panics() {
        // This line invokes the assert!(capacity > 0) inside new()
        let _queue: BoundedQueue<i32> = BoundedQueue::new(0);
    }

    #[test]
    fn test_queue_poisoning_on_thread_panic() {
        // 1. Create a queue shared via Arc so multiple threads can touch it
        let queue = Arc::new(BoundedQueue::new(5));
        let queue_clone = Arc::clone(&queue);

        // 2. Spawn a thread designed to crash while holding the internal lock
        let handle = thread::spawn(move || {
            // Manually lock the inner mutex so this thread owns the lock guard
            let _guard = queue_clone.inner.lock().unwrap();
            
            // Trigger a serious runtime panic while holding the lock guard!
            panic!("Intentional worker thread crash!");
        });

        // 3. Wait for the thread to die. It will return an Err because it panicked.
        let join_result = handle.join();
        assert!(join_result.is_err(), "The thread was supposed to panic");

        // 4. Now try to interact with the queue. 
        // Because the thread panicked while holding the guard, the Mutex is poisoned.
        // Our push and pop methods should cleanly catch this and return our custom error.
        match queue.push("test_item") {
            Err(QueuePoisonedError) => {
                // Success! The queue correctly caught the poisoned state 
                // instead of panicking the main thread.
            }
            Ok(_) => {
                panic!("Expected QueuePoisonedError, but push succeeded!");
            }
        }

        // Verify pop behaves the same way
        match queue.pop() {
            Err(QueuePoisonedError) => {}
            Ok(_) => panic!("Expected QueuePoisonedError, but pop succeeded!"),
        }
    }
}