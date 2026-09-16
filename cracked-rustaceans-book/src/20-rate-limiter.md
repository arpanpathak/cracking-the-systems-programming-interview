# 20. Token Bucket Rate Limiter {#rate-limiter}

*Source file: [`src/problems/rate_limiter.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/rate_limiter.rs). Test it with
`cargo test rate_limiter`.*

## Problem Statement

Limit how often a caller may do something, allow a burst, and do it safely from several
threads. The interface is one question: may I do it now?

## Designing a Solution

A token bucket holds at most `capacity` tokens and refills at `rate` tokens per second.
Each accepted request removes one token; a request that arrives with fewer than one token
available is refused. The bucket therefore admits a burst of up to `capacity` requests
and then holds the sustained rate at `rate`.

```text
tokens = 3.0, capacity = 5.0, rate = 1.0/s, last_refill = t

t + 0.0s   try_acquire   tokens 3.0 >= 1.0   true    tokens = 2.0
t + 0.0s   try_acquire   tokens 2.0 >= 1.0   true    tokens = 1.0
t + 0.0s   try_acquire   tokens 1.0 >= 1.0   true    tokens = 0.0
t + 0.0s   try_acquire   tokens 0.0 <  1.0   false   tokens = 0.0
t + 0.5s   try_acquire   refill adds 0.5, so 0.5 < 1.0   false
t + 1.5s   try_acquire   refill adds 1.5, so 1.5 >= 1.0  true, tokens = 0.5
t + 10.0s  try_acquire   refill is capped at capacity, so the result is 5.0
```

The refill is computed from the elapsed time rather than by a timer thread. A timer
thread would cost one thread per bucket and would make the bucket's state depend on how
the scheduler ran that thread.

## Implementation

```rust
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
```

`try_acquire` takes `&self` rather than `&mut self`. That is what allows one bucket to be
shared by reference across threads; the mutation happens behind the `Mutex`.

The four statements inside the lock are the whole algorithm: read the clock, add the
tokens that time has earned, cap at the capacity, and take one if there is one.
`last_refill` is updated on every call, so no interval is counted twice.

The lock is held across a clock read and a floating-point multiply, which is the shortest
critical section this design permits.

## Intuition

```text
new(5, 1.0)
  state = { tokens: 5.0, last_refill: t0 }

five calls to try_acquire, all at t0:
  call 1  elapsed 0, tokens 5.0, 5.0 >= 1.0  -> true,  tokens 4.0
  call 2  elapsed 0, tokens 4.0, 4.0 >= 1.0  -> true,  tokens 3.0
  call 3  elapsed 0, tokens 3.0, 3.0 >= 1.0  -> true,  tokens 2.0
  call 4  elapsed 0, tokens 2.0, 2.0 >= 1.0  -> true,  tokens 1.0
  call 5  elapsed 0, tokens 1.0, 1.0 >= 1.0  -> true,  tokens 0.0

call 6 at t0:
  elapsed 0, tokens 0.0, 0.0 < 1.0           -> false, tokens 0.0

thread::sleep(1s), then call 7 at t0 + 1s:
  elapsed 1.0s, new_tokens = 1.0 * 1.0 = 1.0
  tokens = min(0.0 + 1.0, 5.0) = 1.0
  1.0 >= 1.0                                 -> true,  tokens 0.0

call 8 at t0 + 1s:
  elapsed ~0, tokens 0.0                     -> false
```

## Time and Space Complexity

| Operation | Time | Space |
|---|---|---|
| `try_acquire` | `O(1)` plus one uncontended mutex acquisition | three machine words of state |
| `new` | `O(1)` | one allocation-free struct |

## Limitations

**`new` panics on an invalid configuration.** `capacity == 0` and `rate_per_sec <= 0.0`
both assert, and a rate read from a configuration file is external input. The rate test
also rejects `f64::NAN`, because every comparison with `NAN` is false, so the assertion
fires. `f64::INFINITY` passes the same test and makes every request succeed, because the
refill is capped at the capacity on the first call and the bucket then stays full. The
validation is therefore incomplete and the failure is a panic rather than a value.

**`self.state.lock().unwrap()` panics if a thread panicked while holding the lock.** One
failed request handler would then take down every later caller that touches this bucket.
Chapter 22 describes the recovery pattern that avoids this.

**There is no blocking acquisition.** A caller that is refused must sleep and try again,
and the bucket offers no way to learn how long to sleep, so the retry policy lives in the
caller and every caller invents one.

**`try_acquire` reads the clock on every call.** `Instant::now()` is cheap, and on some
platforms it goes through the vDSO rather than a system call. A bucket that is called
millions of times per second spends a measurable fraction of its time in the clock.

**The bucket is per-process.** Two processes sharing a limit need a shared store, and
nothing in this design provides one.

**The test sleeps for a second.** That makes the test suite slower and makes the result
depend on how the operating system scheduled the test thread. On a loaded machine the
sleep may return later than requested, which only makes the assertion more likely to pass,
so a bucket whose rate were too high would not be caught.

## References

- Standard library, [`Mutex`](https://doc.rust-lang.org/std/sync/struct.Mutex.html).
- Standard library, [`Instant`](https://doc.rust-lang.org/std/time/struct.Instant.html).
- Standard library, [`f64::min`](https://doc.rust-lang.org/std/primitive.f64.html#method.min).
