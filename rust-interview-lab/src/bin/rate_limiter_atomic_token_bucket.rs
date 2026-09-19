use std::sync::atomic::{AtomicI64, AtomicU64, Ordering::Relaxed};
use std::time::{Instant, Duration};
use std::thread;

#[repr(align(64))]
pub struct RateLimiter {
    tokens: AtomicI64,
    last_refilled_at: AtomicU64, // secs since created_at
    capacity: i64,
    tokens_per_sec: i64,
    created_at: Instant,
}

impl RateLimiter {
    pub fn new(capacity: i64, tokens_per_sec: i64) -> Self {
        Self {
            tokens: AtomicI64::new(capacity),
            last_refilled_at: AtomicU64::new(0),
            capacity,
            tokens_per_sec,
            created_at: Instant::now(),
        }
    }

    pub fn try_acquire(&self) -> bool {
        let now = self.created_at.elapsed().as_secs();
        let last = self.last_refilled_at.fetch_max(now, Relaxed);
        if now > last {
            self.tokens.fetch_add((now - last) as i64 * self.tokens_per_sec, Relaxed);
            self.tokens.fetch_min(self.capacity, Relaxed);
        }

        if self.tokens.load(Relaxed) <= 0 {
            return false;
        }
        self.tokens.fetch_sub(1, Relaxed) > 0
    }
}


fn main() {
    let limiter = RateLimiter::new(5, 5);

    for i in 1..=6 {
        println!("request {i}: {}", limiter.try_acquire());
    }

    thread::sleep(Duration::from_secs(1));

    for i in 1..=6 {
        println!("request {i}: {}", limiter.try_acquire());
    }
}
