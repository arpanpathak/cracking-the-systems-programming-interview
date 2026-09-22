use std::sync::{mpsc, Arc, Mutex};
use std::thread::{self, JoinHandle};

type Job = Box<dyn FnOnce() + Send + 'static>;

pub struct ThreadPool {
    workers: Vec<JoinHandle<()>>,
    job_sender: Option<mpsc::Sender<Job>>,
}

impl ThreadPool {
    pub fn new(size: usize) -> Self {
        assert!(size > 0, "pool size must be > 0");
        let (job_sender, job_receiver) = mpsc::channel();
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
            job_sender.send(Box::new(task)).unwrap();
        }
    }
}

impl Drop for ThreadPool {
    fn drop(&mut self) {
        self.job_sender = None; // close channel so workers stop
        for worker in self.workers.drain(..) {
            worker.join().unwrap(); // Wait for workers to finish... This will ensure gracefull shutdown..
        }
    }
}

fn main() {
    let pool = ThreadPool::new(4);
    for i in 0..8 {
        pool.execute(move || println!("task {i} on {:?}", thread::current().id()));
    }
}