use std::sync::mpsc::{self, Receiver, SendError, SyncSender};
use std::sync::{Arc, Mutex};
use std::thread::{self, JoinHandle};

type Job = Box<dyn FnOnce() + Send + 'static>;
type SharedLockedChannel = Arc<Mutex<Receiver<Job>>>;

pub struct ThreadPool {
    tx: Option<SyncSender<Job>>,
    workers: Vec<JoinHandle<()>>,
}

impl ThreadPool {
    pub fn new(num_workers: usize, queue_size: usize) -> Self {
        let (tx, rx) = mpsc::sync_channel::<Job>(queue_size);
        let rx = SharedLockedChannel::new(Mutex::new(rx));

        let workers = (0..num_workers)
            .map(|_| Self::spawn_worker(Arc::clone(&rx)))
            .collect();

        Self { tx: Some(tx), workers }
    }

    fn spawn_worker(rx: SharedLockedChannel) -> JoinHandle<()> {
        thread::spawn(move || loop {
            let Ok(receiver) = rx.lock() else { break }; // mutex poisoned
            let Ok(job) = receiver.recv() else { break }; // channel closed
            drop(receiver); // release lock before running the job
            job();
        })
    }

    pub fn execute<F>(&self, f: F) -> Result<(), SendError<Job>>
    where
        F: FnOnce() + Send + 'static,
    {
        let job: Job = Box::new(f);
        match &self.tx {
            Some(tx) => tx.send(job), // blocks when queue is full
            None => Err(SendError(job)),
        }
    }

    pub fn join_all<I>(&self, handles: I)
    where
        I: IntoIterator<Item = JoinHandle<()>>,
    {
        for handle in handles {
            let _ = handle.join();
        }
    }
}

impl Drop for ThreadPool {
    fn drop(&mut self) {
        drop(self.tx.take()); // close channel so workers exit
        for worker in self.workers.drain(..) {
            let _ = worker.join();
        }
    }
}

fn main() {
    let pool = Arc::new(ThreadPool::new(4, 16));

    let producers: Vec<_> = (0..3)
        .map(|p| {
            let pool = Arc::clone(&pool);
            thread::spawn(move || {
                for i in 0..5 {
                    let _ = pool.execute(move || println!("producer {p}, job {i}"));
                }
            })
        })
        .collect();

    pool.join_all(producers);
} // last Arc dropped here: Drop waits for all queued jobs
