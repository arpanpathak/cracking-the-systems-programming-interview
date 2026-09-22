use std::sync::{mpsc, Arc, Mutex};
use std::thread::{self, JoinHandle};

type Job = Box<dyn FnOnce() + Send + 'static>;

pub struct ThreadPool {
    workers: Vec<JoinHandle<()>>,
    job_sender: Option<mpsc::SyncSender<Job>>, // changed: bounded sender
}

impl ThreadPool {
    pub fn new(size: usize, queue_size: usize) -> Self { // changed: queue_size
        assert!(size > 0, "pool size must be > 0");
        let (job_sender, job_receiver) = mpsc::sync_channel(queue_size); // changed: bounded queue
        let job_receiver = Arc::new(Mutex::new(job_receiver));

        let workers = (0..size)
            .map(|_| Self::spawn_worker(Arc::clone(&job_receiver)))
            .collect();

        Self { workers, job_sender: Some(job_sender) }
    }

    fn spawn_worker(job_receiver: Arc<Mutex<mpsc::Receiver<Job>>>) -> JoinHandle<()> {
        thread::spawn(move || loop {
            let message = job_receiver.lock().unwrap().recv();
            match message {
                Ok(job) => job(),
                Err(_) => break,
            }
        })
    }

    pub fn execute(&self, task: impl FnOnce() + Send + 'static) {
        if let Some(job_sender) = &self.job_sender {
            job_sender.send(Box::new(task)).unwrap(); // blocks when queue is full
        }
    }

    // new: run a task and get its result back
    pub fn submit<T: Send + 'static>(
        &self,
        task: impl FnOnce() -> T + Send + 'static,
    ) -> mpsc::Receiver<T> {
        let (result_sender, result_receiver) = mpsc::channel();
        self.execute(move || {
            let _ = result_sender.send(task());
        });
        result_receiver
    }
}

impl Drop for ThreadPool {
    fn drop(&mut self) {
        self.job_sender = None;
        for worker in self.workers.drain(..) {
            let _ = worker.join();
        }
    }
}

fn main() {
    let pool = ThreadPool::new(4, 10); // 4 workers, at most 10 jobs waiting

    let results: Vec<_> = (0..8).map(|i| pool.submit(move || i * i)).collect();

    for r in results {
        println!("{}", r.recv().unwrap());
    }
}