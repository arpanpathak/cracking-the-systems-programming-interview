// ch19/thread_pool.rs: a fixed set of worker threads that run queued tasks.
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::mpsc::{self, Receiver, Sender};
use std::sync::{Arc, Mutex};
use std::thread::{self, JoinHandle};

type Task = Box<dyn FnOnce() + Send + 'static>;

/// Runs submitted tasks on a fixed number of threads. Dropping the pool finishes
/// all queued tasks and then joins the workers.
struct ThreadPool {
    sender: Option<Sender<Task>>,
    workers: Vec<JoinHandle<()>>,
}

impl ThreadPool {
    fn new(worker_count: usize) -> Self {
        let (sender, receiver) = mpsc::channel::<Task>();
        let receiver = Arc::new(Mutex::new(receiver));

        let workers = (0..worker_count)
            .map(|_| {
                let receiver = Arc::clone(&receiver);
                thread::spawn(move || run_worker(&receiver))
            })
            .collect();

        ThreadPool {
            sender: Some(sender),
            workers,
        }
    }

    /// Queues one task. A worker that is blocked in `recv` wakes up and runs it.
    fn submit(&self, task: impl FnOnce() + Send + 'static) {
        let Some(sender) = &self.sender else {
            return;
        };

        let sent = sender.send(Box::new(task));

        if sent.is_err() {
            eprintln!("thread pool: all workers have exited");
        }
    }
}

/// Waits for the next task. Returns None when the channel is closed and empty.
/// The mutex guard is dropped on return, so the caller runs the task unlocked.
fn next_task(receiver: &Mutex<Receiver<Task>>) -> Option<Task> {
    let receiver = receiver
        .lock()
        .ok()?;

    receiver
        .recv()
        .ok()
}

/// Runs tasks until none remain and the pool has closed the channel.
fn run_worker(receiver: &Mutex<Receiver<Task>>) {
    while let Some(task) = next_task(receiver) {
        task();
    }
}

impl Drop for ThreadPool {
    fn drop(&mut self) {
        self.sender.take(); // closing the channel makes `recv` fail once it is empty

        for worker in self.workers.drain(..) {
            let joined = worker.join();

            if joined.is_err() {
                eprintln!("thread pool: a worker panicked");
            }
        }
    }
}

fn main() {
    const TASKS: u64 = 1000;
    let total = Arc::new(AtomicU64::new(0));

    {
        let pool = ThreadPool::new(4);

        for task in 1..=TASKS {
            let total = Arc::clone(&total);
            pool.submit(move || {
                total.fetch_add(task, Ordering::Relaxed);
            });
        }
    } // dropping the pool waits for every task here

    let expected = TASKS * (TASKS + 1) / 2;
    let total = total.load(Ordering::Relaxed);

    println!("expected {expected}");
    println!("total    {total}");
}
