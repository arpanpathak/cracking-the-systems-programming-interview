//! Thread pool, version 2: workers really run in parallel.
//!
//! Version 1 (`src/bin/thread_pool.rs`) holds the receiver's lock while a job runs,
//! because the `MutexGuard` in `while let Ok(job) = rx.lock().unwrap().recv()` lives
//! until the end of the loop body. This version takes the job in its own `let`
//! statement, so the guard is dropped before the job starts.
//!
//! It also accepts any closure in `execute`, so callers no longer write `Box::new`.

use std::sync::{Arc, Mutex, mpsc};
use std::thread;

type Job = Box<dyn FnOnce() + Send + 'static>;

pub struct ThreadPool {
    sender: mpsc::Sender<Job>,
    workers: Vec<thread::JoinHandle<()>>,
}

impl ThreadPool {
    /// Start `size` workers. Panics if `size` is zero.
    pub fn new(size: usize) -> Self {
        assert!(size > 0, "a thread pool needs at least one worker");

        let (sender, receiver) = mpsc::channel::<Job>();
        let receiver = Arc::new(Mutex::new(receiver));

        let workers = (0..size)
            .map(|_| {
                let receiver = Arc::clone(&receiver);
                thread::spawn(move || {
                    loop {
                        // The guard is a temporary of this `let` statement, so the
                        // lock is released here, before the job runs.
                        let job = receiver.lock().unwrap().recv();
                        match job {
                            Ok(job) => job(),
                            Err(_) => break, // every sender is gone: shut down
                        }
                    }
                })
            })
            .collect();

        Self { sender, workers }
    }

    /// Queue a closure to run on the next free worker.
    pub fn execute<F>(&self, job: F)
    where
        F: FnOnce() + Send + 'static,
    {
        self.sender.send(Box::new(job)).unwrap();
    }

    /// Stop accepting jobs, let the workers drain the queue, and wait for them.
    pub fn join(self) {
        drop(self.sender);
        for worker in self.workers {
            let _ = worker.join();
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Barrier;
    use std::sync::atomic::{AtomicUsize, Ordering};
    use std::time::Duration;

    #[test]
    fn runs_every_job() {
        let pool = ThreadPool::new(4);
        let counter = Arc::new(AtomicUsize::new(0));
        for _ in 0..100 {
            let counter = Arc::clone(&counter);
            pool.execute(move || {
                counter.fetch_add(1, Ordering::Relaxed);
            });
        }
        pool.join();
        assert_eq!(counter.load(Ordering::Relaxed), 100);
    }

    #[test]
    fn jobs_run_at_the_same_time() {
        // Four jobs wait on a barrier for four parties. They can only all get
        // through if four workers run them at once; version 1 would never finish.
        let pool = ThreadPool::new(4);
        let barrier = Arc::new(Barrier::new(4));
        let (done_tx, done_rx) = mpsc::channel();

        for _ in 0..4 {
            let barrier = Arc::clone(&barrier);
            let done_tx = done_tx.clone();
            pool.execute(move || {
                barrier.wait();
                done_tx.send(()).unwrap();
            });
        }

        for _ in 0..4 {
            done_rx
                .recv_timeout(Duration::from_secs(5))
                .expect("jobs did not run in parallel");
        }
        pool.join();
    }

    #[test]
    #[should_panic(expected = "at least one worker")]
    fn zero_workers_is_rejected() {
        let _ = ThreadPool::new(0);
    }
}
