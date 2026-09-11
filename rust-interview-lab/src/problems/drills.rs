//! Short answers to the common prompts, sized for a live round.
//!
//! Each item is a standalone implementation of roughly the length you would write
//! in an interview. The modules next to this one are reference versions with the
//! long explanations and full test suites; this file is what you type.

use std::cell::UnsafeCell;
use std::collections::VecDeque;
use std::collections::hash_map::DefaultHasher;
use std::hash::Hasher;
use std::ops::{Deref, DerefMut};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Condvar, Mutex, mpsc};
use std::thread::{self, JoinHandle};
use std::time::Duration;

// --- Thread-safe counter (Arc + Mutex) ---

pub fn count_parallel(threads: usize, per_thread: usize) -> usize {
    let counter = Arc::new(Mutex::new(0usize));
    let handles: Vec<_> = (0..threads)
        .map(|_| {
            let counter = Arc::clone(&counter);
            thread::spawn(move || {
                for _ in 0..per_thread {
                    *counter.lock().expect("poisoned") += 1;
                }
            })
        })
        .collect();

    for handle in handles {
        handle.join().expect("worker panicked");
    }
    *counter.lock().expect("poisoned")
}

// --- Scoped threads (borrow instead of Arc) ---

pub fn parallel_sum(values: &[i32]) -> i64 {
    let chunk_size = values.len().div_ceil(4).max(1);
    thread::scope(|scope| {
        values
            .chunks(chunk_size)
            .map(|chunk| {
                scope.spawn(move || chunk.iter().map(|value| i64::from(*value)).sum::<i64>())
            })
            .map(|handle| handle.join().expect("worker panicked"))
            .sum()
    })
}

// --- Spin lock from an atomic ---

pub struct SpinLock<T> {
    locked: AtomicBool,
    value: UnsafeCell<T>,
}

unsafe impl<T: Send> Sync for SpinLock<T> {}

impl<T> SpinLock<T> {
    pub const fn new(value: T) -> Self {
        Self {
            locked: AtomicBool::new(false),
            value: UnsafeCell::new(value),
        }
    }

    pub fn lock(&self) -> SpinGuard<'_, T> {
        while self.locked.swap(true, Ordering::Acquire) {
            std::hint::spin_loop();
        }
        SpinGuard { lock: self }
    }
}

pub struct SpinGuard<'a, T> {
    lock: &'a SpinLock<T>,
}

impl<T> Drop for SpinGuard<'_, T> {
    fn drop(&mut self) {
        self.lock.locked.store(false, Ordering::Release);
    }
}

impl<T> Deref for SpinGuard<'_, T> {
    type Target = T;
    fn deref(&self) -> &T {
        unsafe { &*self.lock.value.get() }
    }
}

impl<T> DerefMut for SpinGuard<'_, T> {
    fn deref_mut(&mut self) -> &mut T {
        unsafe { &mut *self.lock.value.get() }
    }
}

// --- Semaphore (acquire blocks) ---

pub struct Semaphore {
    permits: Mutex<usize>,
    released: Condvar,
}

impl Semaphore {
    pub fn new(permits: usize) -> Self {
        Self {
            permits: Mutex::new(permits),
            released: Condvar::new(),
        }
    }

    pub fn acquire(&self) {
        let mut permits = self.permits.lock().expect("poisoned");
        while *permits == 0 {
            permits = self.released.wait(permits).expect("poisoned");
        }
        *permits -= 1;
    }

    pub fn try_acquire(&self) -> bool {
        let mut permits = self.permits.lock().expect("poisoned");
        if *permits == 0 {
            false
        } else {
            *permits -= 1;
            true
        }
    }

    pub fn release(&self) {
        *self.permits.lock().expect("poisoned") += 1;
        self.released.notify_one();
    }
}

// --- Bounded blocking queue (backpressure + close) ---

pub struct BlockingQueue<T> {
    inner: Mutex<Inner<T>>,
    not_empty: Condvar,
    not_full: Condvar,
}

struct Inner<T> {
    items: VecDeque<T>,
    capacity: usize,
    closed: bool,
}

impl<T> BlockingQueue<T> {
    pub fn new(capacity: usize) -> Self {
        Self {
            inner: Mutex::new(Inner {
                items: VecDeque::new(),
                capacity,
                closed: false,
            }),
            not_empty: Condvar::new(),
            not_full: Condvar::new(),
        }
    }

    pub fn push(&self, item: T) -> Result<(), T> {
        let mut inner = self.inner.lock().expect("poisoned");
        loop {
            if inner.closed {
                return Err(item);
            }
            if inner.items.len() < inner.capacity {
                inner.items.push_back(item);
                self.not_empty.notify_one();
                return Ok(());
            }
            inner = self.not_full.wait(inner).expect("poisoned");
        }
    }

    pub fn pop(&self) -> Option<T> {
        let mut inner = self.inner.lock().expect("poisoned");
        loop {
            if let Some(item) = inner.items.pop_front() {
                self.not_full.notify_one();
                return Some(item);
            }
            if inner.closed {
                return None;
            }
            inner = self.not_empty.wait(inner).expect("poisoned");
        }
    }

    pub fn close(&self) {
        let mut inner = self.inner.lock().expect("poisoned");
        inner.closed = true;
        drop(inner);
        self.not_empty.notify_all();
        self.not_full.notify_all();
    }
}

// --- Thread pool (fixed workers + channel) ---

pub struct ThreadPool {
    sender: Option<mpsc::Sender<Box<dyn FnOnce() + Send + 'static>>>,
    workers: Vec<JoinHandle<()>>,
}

impl ThreadPool {
    pub fn new(size: usize) -> Self {
        let (sender, receiver) = mpsc::channel::<Box<dyn FnOnce() + Send + 'static>>();
        let receiver = Arc::new(Mutex::new(receiver));
        let workers = (0..size)
            .map(|_| {
                let receiver = Arc::clone(&receiver);
                thread::spawn(move || {
                    loop {
                        let Ok(job) = receiver.lock().expect("poisoned").recv() else {
                            return;
                        };
                        job();
                    }
                })
            })
            .collect();
        Self {
            sender: Some(sender),
            workers,
        }
    }

    pub fn execute(&self, job: impl FnOnce() + Send + 'static) {
        self.sender
            .as_ref()
            .expect("pool dropped")
            .send(Box::new(job))
            .expect("worker gone");
    }
}

impl Drop for ThreadPool {
    fn drop(&mut self) {
        drop(self.sender.take());
        for worker in self.workers.drain(..) {
            let _ = worker.join();
        }
    }
}

// --- Retry with exponential backoff ---

pub fn retry<T, E>(
    max_attempts: u32,
    mut operation: impl FnMut() -> Result<T, E>,
    retryable: impl Fn(&E) -> bool,
) -> Result<T, E> {
    let mut delay = Duration::from_millis(25);
    let mut attempt = 0;
    loop {
        match operation() {
            Ok(value) => return Ok(value),
            Err(error) => {
                attempt += 1;
                if attempt >= max_attempts || !retryable(&error) {
                    return Err(error);
                }
                thread::sleep(delay);
                delay = (delay * 2).min(Duration::from_secs(1));
            }
        }
    }
}

// --- Consistent hashing ring ---

#[derive(Default)]
pub struct HashRing {
    points: Vec<(u64, String)>,
}

impl HashRing {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn add(&mut self, node: &str, replicas: usize) {
        for replica in 0..replicas {
            self.points.push((hash(node, replica), node.to_string()));
        }
        self.points.sort_unstable_by_key(|(point, _)| *point);
    }

    pub fn get(&self, key: &str) -> Option<&str> {
        if self.points.is_empty() {
            return None;
        }
        let hash = hash(key, 0);
        let index = self.points.partition_point(|(point, _)| *point <= hash) % self.points.len();
        Some(self.points[index].1.as_str())
    }
}

fn hash(input: &str, replica: usize) -> u64 {
    let mut hasher = DefaultHasher::new();
    hasher.write(input.as_bytes());
    hasher.write_usize(replica);
    hasher.finish()
}

// --- HTTP request head ---

pub struct RequestHead {
    pub method: String,
    pub target: String,
    pub headers: Vec<(String, String)>,
}

pub fn parse_request_head(input: &str) -> Option<RequestHead> {
    let mut lines = input.split("\r\n");
    let mut request_line = lines.next()?.split(' ');
    let method = request_line.next()?.to_string();
    let target = request_line.next()?.to_string();
    if request_line.next()? != "HTTP/1.1" {
        return None;
    }

    let mut headers = Vec::new();
    for line in lines {
        if line.is_empty() {
            break;
        }
        let (name, value) = line.split_once(':')?;
        headers.push((name.trim().to_ascii_lowercase(), value.trim().to_string()));
    }
    Some(RequestHead {
        method,
        target,
        headers,
    })
}

// --- Newtype and enum ADT ---

pub struct Port(u16);

impl Port {
    pub fn new(value: u16) -> Result<Self, &'static str> {
        (1..=u16::MAX)
            .contains(&value)
            .then_some(Self(value))
            .ok_or("port must be non-zero")
    }

    pub fn get(self) -> u16 {
        self.0
    }
}

pub enum Route {
    Health,
    List,
    ById(String),
}

impl Route {
    pub fn parse(path: &str) -> Option<Self> {
        match path {
            "/healthz" => Some(Self::Health),
            "/v1/gpu-workloads" => Some(Self::List),
            _ => path
                .strip_prefix("/v1/gpu-workloads/")
                .map(|id| Self::ById(id.to_string())),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::atomic::AtomicUsize;

    #[test]
    fn counter_scoped_sum_and_spin_lock() {
        assert_eq!(count_parallel(4, 100), 400);
        assert_eq!(parallel_sum(&[1, 2, 3, 4]), 10);

        let lock = Arc::new(SpinLock::new(0usize));
        let handles: Vec<_> = (0..4)
            .map(|_| {
                let lock = Arc::clone(&lock);
                thread::spawn(move || {
                    for _ in 0..100 {
                        *lock.lock() += 1;
                    }
                })
            })
            .collect();
        for handle in handles {
            handle.join().expect("worker panicked");
        }
        assert_eq!(*lock.lock(), 400);
    }

    #[test]
    fn semaphore_queue_and_pool() {
        let semaphore = Semaphore::new(1);
        assert!(semaphore.try_acquire());
        assert!(!semaphore.try_acquire());
        semaphore.release();
        assert!(semaphore.try_acquire());

        let queue = BlockingQueue::new(1);
        assert_eq!(queue.push(1), Ok(()));
        queue.close();
        assert_eq!(queue.pop(), Some(1));
        assert_eq!(queue.pop(), None);
        assert_eq!(queue.push(2), Err(2));

        let pool = ThreadPool::new(3);
        let counter = Arc::new(AtomicUsize::new(0));
        for _ in 0..100 {
            let counter = Arc::clone(&counter);
            pool.execute(move || {
                counter.fetch_add(1, Ordering::SeqCst);
            });
        }
        drop(pool);
        assert_eq!(counter.load(Ordering::SeqCst), 100);
    }

    #[test]
    fn retry_ring_http_and_adt() {
        let mut attempts = 0;
        let ok = retry(
            3,
            || {
                attempts += 1;
                if attempts < 3 { Err("transient") } else { Ok(7) }
            },
            |_| true,
        );
        assert_eq!(ok, Ok(7));

        let mut attempts = 0;
        let bad: Result<(), &str> = retry(
            3,
            || {
                attempts += 1;
                Err("permanent")
            },
            |_| false,
        );
        assert!(bad.is_err());
        assert_eq!(attempts, 1);

        let mut ring = HashRing::new();
        ring.add("a", 64);
        ring.add("b", 64);
        let before = ring.get("job-1").map(str::to_string);
        ring.add("c", 64);
        let after = ring.get("job-1").map(str::to_string);
        assert!(after == before || after.as_deref() == Some("c"));

        let head =
            parse_request_head("GET /v1/gpu-workloads HTTP/1.1\r\nHost: api\r\n\r\n").expect("valid");
        assert_eq!(
            (head.method.as_str(), head.target.as_str()),
            ("GET", "/v1/gpu-workloads")
        );
        assert_eq!(head.headers[0], ("host".to_string(), "api".to_string()));
        assert!(parse_request_head("GET / HTTP/2\r\n\r\n").is_none());

        assert!(Port::new(8080).is_ok());
        assert!(Port::new(0).is_err());
        assert!(matches!(Route::parse("/healthz"), Some(Route::Health)));
        assert!(matches!(
            Route::parse("/v1/gpu-workloads/wl-1"),
            Some(Route::ById(id)) if id == "wl-1"
        ));
    }
}
