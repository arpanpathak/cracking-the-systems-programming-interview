//! Thread pool, version 3: errors instead of panics, and shutdown on drop.
//!
//! - `new` returns `Err(PoolError::NoWorkers)` for a size of zero.
//! - `execute` returns `Err(PoolError::ShutDown)` once the pool no longer accepts work.
//! - Dropping the pool closes the queue and joins every worker, so a pool that goes
//!   out of scope still finishes the jobs it was given.

use std::fmt;
use std::sync::{Arc, Mutex, mpsc};
use std::thread;

type Job = Box<dyn FnOnce() + Send + 'static>;

/// Why the pool refused a request.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PoolError {
    NoWorkers,
    ShutDown,
}

impl fmt::Display for PoolError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::NoWorkers => write!(f, "a thread pool needs at least one worker"),
            Self::ShutDown => write!(f, "the thread pool has shut down"),
        }
    }
}

impl std::error::Error for PoolError {}

pub struct ThreadPool {
    // `None` after shutdown: dropping the sender is what tells workers to stop.
    sender: Option<mpsc::Sender<Job>>,
    workers: Vec<thread::JoinHandle<()>>,
}

impl ThreadPool {
    /// Start `size` workers.
    pub fn new(size: usize) -> Result<Self, PoolError> {
        if size == 0 {
            return Err(PoolError::NoWorkers);
        }

        let (sender, receiver) = mpsc::channel::<Job>();
        let receiver = Arc::new(Mutex::new(receiver));

        let workers = (0..size)
            .map(|_| {
                let receiver = Arc::clone(&receiver);
                thread::spawn(move || worker_loop(&receiver))
            })
            .collect();

        Ok(Self {
            sender: Some(sender),
            workers,
        })
    }

    /// Queue a closure to run on the next free worker.
    pub fn execute<F>(&self, job: F) -> Result<(), PoolError>
    where
        F: FnOnce() + Send + 'static,
    {
        self.sender
            .as_ref()
            .ok_or(PoolError::ShutDown)?
            .send(Box::new(job))
            .map_err(|_| PoolError::ShutDown)
    }

    /// Stop accepting jobs, drain the queue, and wait for every worker.
    /// Calling it again does nothing.
    pub fn shutdown(&mut self) {
        drop(self.sender.take());
        for worker in self.workers.drain(..) {
            let _ = worker.join();
        }
    }
}

impl Drop for ThreadPool {
    fn drop(&mut self) {
        self.shutdown();
    }
}

fn worker_loop(receiver: &Mutex<mpsc::Receiver<Job>>) {
    loop {
        // A poisoned lock means another worker panicked while holding it;
        // stop this worker instead of panicking a second time.
        let Ok(guard) = receiver.lock() else { return };
        let job = guard.recv();
        drop(guard);

        match job {
            Ok(job) => job(),
            Err(_) => return,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::{AtomicUsize, Ordering};

    #[test]
    fn zero_workers_is_an_error() {
        assert_eq!(ThreadPool::new(0).err(), Some(PoolError::NoWorkers));
    }

    #[test]
    fn dropping_the_pool_finishes_queued_jobs() {
        let counter = Arc::new(AtomicUsize::new(0));
        {
            let pool = ThreadPool::new(2).unwrap();
            for _ in 0..50 {
                let counter = Arc::clone(&counter);
                pool.execute(move || {
                    counter.fetch_add(1, Ordering::Relaxed);
                })
                .unwrap();
            }
        } // drop: close the queue and join
        assert_eq!(counter.load(Ordering::Relaxed), 50);
    }

    #[test]
    fn execute_after_shutdown_is_an_error() {
        let mut pool = ThreadPool::new(1).unwrap();
        pool.shutdown();
        assert_eq!(pool.execute(|| {}), Err(PoolError::ShutDown));
        pool.shutdown(); // idempotent
    }

    #[test]
    fn errors_render_a_message() {
        assert_eq!(
            PoolError::NoWorkers.to_string(),
            "a thread pool needs at least one worker"
        );
        assert_eq!(
            PoolError::ShutDown.to_string(),
            "the thread pool has shut down"
        );
    }
}
