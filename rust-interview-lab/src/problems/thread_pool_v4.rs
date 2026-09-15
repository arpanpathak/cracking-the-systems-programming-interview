//! Thread pool, version 4: survives panicking jobs and reports what happened.
//!
//! - Workers are named threads created with `thread::Builder`, and a failure to
//!   spawn one is returned as `PoolError::Spawn` after the already started workers
//!   are shut down.
//! - Each job runs inside `catch_unwind`, so a panicking job no longer kills its
//!   worker and silently shrinks the pool.
//! - `shutdown` consumes the pool and returns a `Report` with the number of jobs
//!   that completed and the number that panicked.

use std::fmt;
use std::io;
use std::panic::{self, AssertUnwindSafe};
use std::sync::atomic::{AtomicUsize, Ordering};
use std::sync::{Arc, Mutex, mpsc};
use std::thread;

type Job = Box<dyn FnOnce() + Send + 'static>;

/// Why the pool could not be created or refused a job.
#[derive(Debug)]
pub enum PoolError {
    NoWorkers,
    Spawn(io::Error),
    ShutDown,
}

impl fmt::Display for PoolError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::NoWorkers => write!(f, "a thread pool needs at least one worker"),
            Self::Spawn(error) => write!(f, "failed to spawn a worker thread: {error}"),
            Self::ShutDown => write!(f, "the thread pool has shut down"),
        }
    }
}

impl std::error::Error for PoolError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            Self::Spawn(error) => Some(error),
            _ => None,
        }
    }
}

/// What the pool did over its lifetime.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Report {
    pub completed: usize,
    pub panicked: usize,
}

#[derive(Default)]
struct Counters {
    completed: AtomicUsize,
    panicked: AtomicUsize,
}

pub struct ThreadPool {
    sender: Option<mpsc::Sender<Job>>,
    workers: Vec<thread::JoinHandle<()>>,
    counters: Arc<Counters>,
}

impl ThreadPool {
    /// Start `size` named workers.
    pub fn new(size: usize) -> Result<Self, PoolError> {
        if size == 0 {
            return Err(PoolError::NoWorkers);
        }

        let (sender, receiver) = mpsc::channel::<Job>();
        let receiver = Arc::new(Mutex::new(receiver));
        let counters = Arc::new(Counters::default());

        let mut pool = Self {
            sender: Some(sender),
            workers: Vec::with_capacity(size),
            counters,
        };

        for id in 0..size {
            let receiver = Arc::clone(&receiver);
            let counters = Arc::clone(&pool.counters);
            let spawned = thread::Builder::new()
                .name(format!("pool-worker-{id}"))
                .spawn(move || worker_loop(&receiver, &counters));

            match spawned {
                Ok(handle) => pool.workers.push(handle),
                // Dropping `pool` here closes the queue and joins the workers
                // that did start, so none of them is leaked.
                Err(error) => return Err(PoolError::Spawn(error)),
            }
        }

        Ok(pool)
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

    /// Close the queue, wait for every queued job, and report the outcome.
    pub fn shutdown(mut self) -> Report {
        self.close_and_join();
        Report {
            completed: self.counters.completed.load(Ordering::Relaxed),
            panicked: self.counters.panicked.load(Ordering::Relaxed),
        }
    }

    fn close_and_join(&mut self) {
        drop(self.sender.take());
        for worker in self.workers.drain(..) {
            // Jobs cannot unwind out of `worker_loop`, so a join error would mean
            // a bug in the loop itself; there is nothing further to clean up.
            let _ = worker.join();
        }
    }
}

impl Drop for ThreadPool {
    fn drop(&mut self) {
        self.close_and_join();
    }
}

fn worker_loop(receiver: &Mutex<mpsc::Receiver<Job>>, counters: &Counters) {
    loop {
        let Ok(guard) = receiver.lock() else { return };
        let job = guard.recv();
        drop(guard);

        let Ok(job) = job else { return };

        // `AssertUnwindSafe` is sound here: the job owns everything it touches,
        // and a panicking job's partial state is never observed by this loop.
        match panic::catch_unwind(AssertUnwindSafe(job)) {
            Ok(()) => counters.completed.fetch_add(1, Ordering::Relaxed),
            Err(_) => counters.panicked.fetch_add(1, Ordering::Relaxed),
        };
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::error::Error;
    use std::sync::mpsc::channel;
    use std::time::Duration;

    #[test]
    fn reports_completed_jobs() {
        let pool = ThreadPool::new(4).unwrap();
        for _ in 0..20 {
            pool.execute(|| {}).unwrap();
        }
        assert_eq!(
            pool.shutdown(),
            Report {
                completed: 20,
                panicked: 0
            }
        );
    }

    #[test]
    fn a_panicking_job_does_not_kill_its_worker() {
        // One worker: if the panic killed it, the second job would never run.
        let pool = ThreadPool::new(1).unwrap();
        let (done_tx, done_rx) = channel();

        pool.execute(|| panic!("job failed on purpose")).unwrap();
        pool.execute(move || done_tx.send(()).unwrap()).unwrap();

        done_rx
            .recv_timeout(Duration::from_secs(5))
            .expect("the worker died with the panicking job");
        assert_eq!(
            pool.shutdown(),
            Report {
                completed: 1,
                panicked: 1
            }
        );
    }

    #[test]
    fn workers_are_named() {
        let pool = ThreadPool::new(1).unwrap();
        let (name_tx, name_rx) = channel();
        pool.execute(move || {
            let name = thread::current().name().map(str::to_string);
            name_tx.send(name).unwrap();
        })
        .unwrap();
        assert_eq!(name_rx.recv().unwrap().as_deref(), Some("pool-worker-0"));
    }

    #[test]
    fn zero_workers_is_an_error() {
        assert!(matches!(ThreadPool::new(0), Err(PoolError::NoWorkers)));
    }

    #[test]
    fn spawn_errors_expose_their_source() {
        let error = PoolError::Spawn(io::Error::other("no threads left"));
        assert!(error.to_string().contains("no threads left"));
        assert!(error.source().is_some());
        assert!(PoolError::ShutDown.source().is_none());
    }
}
