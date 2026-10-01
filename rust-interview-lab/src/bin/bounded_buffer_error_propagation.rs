use std::{
    collections::VecDeque,
    error::Error,
    sync::{Arc, Condvar, Mutex},
    thread,
    time::Duration,
};

type RuntimeError = Box<dyn Error + Send + Sync>;

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

    fn push(&self, item: T) -> Result<(), RuntimeError> {
        let mut guard = self
            .inner
            .lock()
            .map_err(|e| e.to_string())?;

        while guard.len() == self.capacity {
            guard = self
                .not_full
                .wait(guard)
                .map_err(|e| e.to_string())?;
        }

        guard.push_back(item);
        drop(guard);
        self.not_empty.notify_one();
        Ok(())
    }

    fn pop(&self) -> Result<T, RuntimeError> {
        let mut guard = self
            .inner
            .lock()
            .map_err(|e| e.to_string())?;

        while guard.is_empty() {
            guard = self
                .not_empty
                .wait(guard)
                .map_err(|e| e.to_string())?;
        }

        let item = match guard.pop_front() {
            Some(item) => item,
            None => return Err("deque is non-empty by loop invariant".into()),
        };

        drop(guard);
        self.not_full.notify_one();
        Ok(item)
    }
}

fn main() -> Result<(), RuntimeError> {
    let queue = Arc::new(BoundedQueue::new(3));

    let producers = (0..2).map(|p| {
        let q = Arc::clone(&queue);
        thread::spawn(move || -> Result<(), RuntimeError> {
            for i in 0..5 {
                let item = format!("p{}:item{}", p, i);
                println!("  [producer {}] pushing {}", p, item);
                q.push(item)?;
                thread::sleep(Duration::from_millis(30));
            }
            Ok(())
        })
    });

    let consumers = (0..2).map(|c| {
        let q = Arc::clone(&queue);
        thread::spawn(move || -> Result<(), RuntimeError> {
            for _ in 0..5 {
                let item = q.pop()?;
                println!("[consumer {}] got {}", c, item);
                thread::sleep(Duration::from_millis(60));
            }
            Ok(())
        })
    });

    let handles: Vec<_> = producers.chain(consumers).collect();

    for h in handles {
        match h.join() {
            Ok(r) => println!("Thread joined : {:#?}", r),
            Err(e) => eprintln!("Error occured : {:#?}", e),
        }
    }

    println!("done");
    Ok(())
}
