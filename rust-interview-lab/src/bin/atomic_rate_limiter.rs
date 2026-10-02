use std::{
    sync::atomic::{AtomicI64, AtomicU64, Ordering::Relaxed},
    thread,
    time::{Duration, Instant},
};

pub struct RateLimiter {
    tokens: AtomicI64,
    rate_per_secs: i32,
    last_refilled_at: AtomicI64,
    created_at: Instant,
}

impl RateLimiter {
    fn new(rate_per_secs: i32) -> Self {
        Self {
            last_refilled_at: AtomicI64::new(Instant::now()),
            tokens: rate_per_secs,
        }
    }
}

fn main() {}
