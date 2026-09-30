use std::{
    sync::{
        Arc,
        Mutex,
        mpsc::{self, Receiver, SendError, SyncSender},
    },
    thread::{self, JoinHandle},
};

/// Define your necessary data types....
type Job = Box<dyn FnOnce() + Send + 'static>;
type SharedSyncReceiver = Arc<Mutex<Receiver<Job>>>;

pub struct ThreadPool {
    // Transmission channel for senders to send jobs...
    tx: Option<SyncSender<Job>>,
    workers: Vec<JoinHandle<()>>,
}

impl ThreadPool {
    pub fn new(num_workers: usize, queue_size: usize) -> Self {
        let (tx, rx) = mpsc::sync_channel::<Job>(queue_size);
        let rx = SharedSyncReceiver::new(Mutex::new(rx));

        let workers = (1..=num_workers)
            .map(|_| Self::span_worker(Arc::clone(&rx)))
            .collect();

        Self {
            tx: Some(tx),
            workers,
        }
    }

    fn span_worker(rx: SharedSyncReceiver) -> JoinHandle<()> {
        thread::spawn(move || {
            loop {
                let Ok(receiver) = rx.lock() else { break }; // Mutex poisoned
                let Ok(job) = receiver.recv() else { break }; // Chapter is closed, just move on!

                // Small resource optimization, you don't need to hold the lock, just like move to the
                // right lane after passing...
                drop(receiver);

                // It's just a foking function call, innit ?
                job();
            }
        })
    }

    // TODO: Define Algebric sum type for enums...
    pub fn execute<F>(&self, f: F) -> Result<(), SendError<Job>>
    where
        F: FnOnce() + Send + 'static,
    {
        let job = Box::new(f);
        match &self.tx {
            Some(tx) => tx.send(job),
            None => Err(SendError(job)),
        }
    }
}

fn main() {
    let collection = vec![1, 2, 3, 4, 5];
}
