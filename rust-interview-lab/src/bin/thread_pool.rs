use std::sync::{mpsc, Arc, Mutex};
use std::thread;

type Job = Box<dyn FnOnce() + Send + 'static>;

pub struct ThreadPool {
    sender: mpsc::Sender<Job>,
    workers: Vec<thread::JoinHandle<()>>,
}

impl ThreadPool {
    pub fn new(size: usize) -> Self {
        let (sender, receiver) = mpsc::channel::<Job>();
        let receiver = Arc::new(Mutex::new(receiver));

        let workers = (0..size)
            .map(|_| {
                let rx = Arc::clone(&receiver);
                thread::spawn(move || {
                    while let Ok(job) = rx.lock().unwrap().recv() {
                        job();
                    }
                })
            })
            .collect();

        Self { sender, workers }
    }

    pub fn execute(&self, job: Job) {
        self.sender.send(job).unwrap();
    }

    pub fn join(self) {
        drop(self.sender);
        for w in self.workers {
            let _ = w.join();
        }
    }
}

fn main() {
    let pool = ThreadPool::new(4);
    for i in 0..10_000 {
        pool.execute(Box::new(move || println!("task {i}")));
    }

    pool.join();
}
