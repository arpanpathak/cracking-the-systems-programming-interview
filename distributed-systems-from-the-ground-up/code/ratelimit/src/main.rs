//! Command ratelimit gives the same traffic to 5 rate limiting algorithms
//! and prints what each of them forwards. Every algorithm enforces the same
//! limit: 5 requests per second for 1 client.
//!
//! Run it from code/ with:
//!
//!     cargo run -p ratelimit

// ANCHOR: imports
use std::collections::VecDeque;
// ANCHOR_END: imports

// ANCHOR: limit
/// The limit: `LIMIT` requests in every `WINDOW` milliseconds.
const LIMIT: u64 = 5;
const WINDOW: u64 = 1000;

/// The gap between 2 requests of a client that sends exactly at the limit.
const INTERVAL: u64 = WINDOW / LIMIT;

/// A rate limiter for 1 client. `admit` decides a request that arrives at
/// `now`, in milliseconds. It returns the time at which the request is
/// forwarded, or `None` when the request is refused.
trait Limiter {
    fn admit(&mut self, now: u64) -> Option<u64>;
}
// ANCHOR_END: limit

// ANCHOR: fixed
/// Counts the requests of the current window. The count starts again from 0
/// when the clock enters the next window.
#[derive(Default)]
struct FixedWindow {
    window: u64,
    count: u64,
}

impl Limiter for FixedWindow {
    fn admit(&mut self, now: u64) -> Option<u64> {
        let window = now / WINDOW;

        if window != self.window {
            *self = FixedWindow { window, count: 0 };
        }

        if self.count == LIMIT {
            return None;
        }

        self.count += 1;

        Some(now)
    }
}
// ANCHOR_END: fixed

// ANCHOR: log
/// Keeps the arrival time of every request it forwarded during the last
/// `WINDOW` milliseconds.
#[derive(Default)]
struct SlidingLog {
    forwarded: VecDeque<u64>,
}

impl Limiter for SlidingLog {
    fn admit(&mut self, now: u64) -> Option<u64> {
        let recent = self
            .forwarded
            .partition_point(|&time| time + WINDOW <= now);

        self.forwarded.drain(..recent);

        if self.forwarded.len() as u64 == LIMIT {
            return None;
        }

        self.forwarded.push_back(now);

        Some(now)
    }
}
// ANCHOR_END: log

// ANCHOR: counter
/// Keeps 2 counts, for the current window and the one before it, and
/// estimates from them how many requests the last `WINDOW` milliseconds held.
#[derive(Default)]
struct SlidingCounter {
    window: u64,
    current: u64,
    previous: u64,
}

impl Limiter for SlidingCounter {
    fn admit(&mut self, now: u64) -> Option<u64> {
        let window = now / WINDOW;

        (self.previous, self.current) = match window - self.window {
            0 => (self.previous, self.current),
            1 => (self.current, 0),
            2.. => (0, 0),
        };
        self.window = window;

        // The part of the previous window that the last WINDOW milliseconds
        // still cover. Both sides of the comparison are multiplied by WINDOW,
        // so the estimate needs no fractions.
        let overlap = WINDOW - now % WINDOW;
        let estimate = self.previous * overlap + self.current * WINDOW;

        if estimate + WINDOW > LIMIT * WINDOW {
            return None;
        }

        self.current += 1;

        Some(now)
    }
}
// ANCHOR_END: counter

// ANCHOR: token
/// Holds up to `LIMIT` tokens and gains `LIMIT` tokens per second. A request
/// is forwarded when it can take 1 token.
struct TokenBucket {
    tokens: f64,
    updated: u64,
}

impl Limiter for TokenBucket {
    fn admit(&mut self, now: u64) -> Option<u64> {
        let gained = (now - self.updated) as f64 / INTERVAL as f64;

        self.tokens = (self.tokens + gained).min(LIMIT as f64);
        self.updated = now;

        if self.tokens < 1.0 {
            return None;
        }

        self.tokens -= 1.0;

        Some(now)
    }
}
// ANCHOR_END: token

// ANCHOR: leaky
/// A queue of up to `LIMIT` waiting requests that lets 1 request out every
/// `INTERVAL` milliseconds. The queue is not stored: `free_at`, the time of
/// the next free place in the outgoing schedule, describes it completely.
#[derive(Default)]
struct LeakyBucket {
    free_at: u64,
}

impl Limiter for LeakyBucket {
    fn admit(&mut self, now: u64) -> Option<u64> {
        let leaves = now.max(self.free_at);

        if leaves - now >= LIMIT * INTERVAL {
            return None;
        }

        self.free_at = leaves + INTERVAL;

        Some(leaves)
    }
}
// ANCHOR_END: leaky

// ANCHOR: main
/// The largest number of requests forwarded within any span of `WINDOW`
/// milliseconds.
fn busiest_second(forwarded: &[u64]) -> usize {
    forwarded
        .iter()
        .map(|&start| {
            forwarded
                .iter()
                .filter(|&&time| (start..start + WINDOW).contains(&time))
                .count()
        })
        .max()
        .unwrap_or_default()
}

/// Gives the same arrivals to every algorithm and prints what each forwards.
fn compare(title: &str, arrivals: &[u64]) {
    let limiters: [(&str, Box<dyn Limiter>); 5] = [
        ("fixed window", Box::new(FixedWindow::default())),
        ("sliding window log", Box::new(SlidingLog::default())),
        (
            "sliding window counter",
            Box::new(SlidingCounter::default()),
        ),
        (
            "token bucket",
            Box::new(TokenBucket {
                tokens: LIMIT as f64,
                updated: 0,
            }),
        ),
        ("leaky bucket", Box::new(LeakyBucket::default())),
    ];

    println!("\n{title}: {} requests", arrivals.len());
    println!(
        "  {:24}{:>9}  {:>18}  first 5 forwarded at (ms)",
        "algorithm", "forwarded", "most in any second"
    );

    for (name, mut limiter) in limiters {
        let forwarded: Vec<u64> = arrivals
            .iter()
            .filter_map(|&now| limiter.admit(now))
            .collect();
        let first: Vec<String> = forwarded
            .iter()
            .take(5)
            .map(u64::to_string)
            .collect();

        println!(
            "  {name:24}{:>9}  {:>18}  {}",
            forwarded.len(),
            busiest_second(&forwarded),
            first.join(" ")
        );
    }
}

fn main() {
    println!("the limit for every algorithm: {LIMIT} requests per second");

    let burst = [0; 20];
    let boundary: Vec<u64> = (900..1100).step_by(20).collect();
    let steady: Vec<u64> = (0..3000).step_by(100).collect();

    compare("20 requests in the same instant", &burst);
    compare(
        "5 requests before the 1 second mark and 5 after it",
        &boundary,
    );
    compare("10 requests per second for 3 seconds", &steady);
}
// ANCHOR_END: main
