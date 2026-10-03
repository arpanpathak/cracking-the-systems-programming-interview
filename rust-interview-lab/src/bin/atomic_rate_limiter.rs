use std::{sync::atomic::AtomicI64, time::Instant};

pub struct RateLimiter {
    tokens: AtomicI64,
    rate_per_secs: i32,
    last_refilled_at: AtomicI64,
    created_at: Instant,
}

impl RateLimiter {
    fn new(rate_per_secs: i32) -> Self {
        Self {
            tokens: AtomicI64::new(rate_per_secs as i64),
            rate_per_secs,
            last_refilled_at: AtomicI64::new(0),
            created_at: Instant::now(),
        }
    }
}

fn main() {}
