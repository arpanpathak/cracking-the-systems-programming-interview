//! Thread-safe token bucket rate limiter.

use std::sync::Mutex;
use std::time::Instant;

pub struct TokenBucket {
    /// Max tokens.
    capacity: f64,
    /// Tokens per second.
    rate: f64,
    state: Mutex<BucketState>,
}

struct BucketState {
    tokens: f64,
    last_refill: Instant,
}

impl TokenBucket {
    pub fn new(capacity: usize, rate_per_sec: f64) -> Self {
        assert!(capacity > 0);
        assert!(rate_per_sec > 0.0);
        Self {
            capacity: capacity as f64,
            rate: rate_per_sec,
            state: Mutex::new(BucketState {
                tokens: capacity as f64, // Start full
                last_refill: Instant::now(),
            }),
        }
    }

    pub fn try_acquire(&self) -> bool {
        let mut s = self.state.lock().unwrap();
        let now = Instant::now();

        // Refill tokens based on elapsed time
        let elapsed = now - s.last_refill;
        let new_tokens = elapsed.as_secs_f64() * self.rate;
        s.tokens = (s.tokens + new_tokens).min(self.capacity);
        s.last_refill = now;

        // Try to take one
        if s.tokens >= 1.0 {
            s.tokens -= 1.0;
            true
        } else {
            false
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::thread;
    use std::time::Duration;

    #[test]
    fn it_works() {
        let bucket = TokenBucket::new(5, 1.0); // 5 tokens, refill 1 per sec

        // Use all 5
        for _ in 0..5 {
            assert!(bucket.try_acquire());
        }
        // 6th fails
        assert!(!bucket.try_acquire());

        // Wait 1 second
        thread::sleep(Duration::from_secs(1));
        // Should have 1 token back
        assert!(bucket.try_acquire());
        // And none left
        assert!(!bucket.try_acquire());
    }
}
