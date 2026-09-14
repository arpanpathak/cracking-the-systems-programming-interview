# 57. Retry with Backoff and Jitter {#retry}

*Source file: [`src/problems/retry.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/retry.rs). Test it with `cargo test retry`.*

## Problem Statement

Write `retry(policy, operation, unit_random)` that calls `operation` until one of the
following happens:

- it succeeds, and the value is returned;
- it fails with an error that retrying cannot fix, and the error is returned at once;
- the policy's maximum number of attempts is reached, and the last error is returned.

Between attempts, wait for a delay that grows exponentially up to a cap, is randomised
according to the policy, and is never shorter than a delay the server requested.

## Designing a Solution

**Classify errors by type.** A `Retryable` trait with `is_retryable` and an optional
`retry_after` lets the loop ask each error what to do. `ApiError` implements it: rate
limiting and 5xx server errors are retryable, while `NotFound`, `Unauthorized`, and
`InvalidRequest` are not, because waiting does not change the outcome.

**Exponential backoff with a cap.** The delay before retry `k`, counting from zero, is
`base × 2^k`, limited to `max_delay`:

```text
base = 100 ms, max = 1 s

retry k    base × 2^k    capped
0          100 ms        100 ms
1          200 ms        200 ms
2          400 ms        400 ms
3          800 ms        800 ms
4          1600 ms       1000 ms
```

**Full jitter.** With no randomness, clients that failed at the same moment retry at the
same moments. Full jitter chooses the delay uniformly between zero and the capped
backoff, which spreads retries across the whole interval. Analysis published by AWS
found that full jitter completed the same work with fewer calls than equal jitter or no
jitter.

**Inject the random source.** The loop takes `unit_random: impl FnMut() -> f64`. Tests
pass `|| 0.0` and get deterministic delays; production code passes a real generator.
The crate has no dependency on a random-number library.

**`Retry-After` is a floor.** When a server sends `429 Too Many Requests` with a
`Retry-After` value, retrying sooner only earns another 429. The loop waits for the larger
of the server's value and its own backoff.

## Implementation

```rust
//! Retry with exponential backoff, full jitter, and `Retry-After`.
//!
//! Every cloud SDK retries. Done badly it makes an outage worse: synchronized
//! retries from thousands of clients form a thundering herd, and retrying a
//! non-idempotent `POST` can create duplicate workloads. This module models the
//! policy explicitly.
//!
//! Two details that interviews probe:
//!
//! - **Jitter.** Full jitter picks a random delay in `[0, capped_backoff]` so
//!   clients spread out instead of retrying in lockstep.
//! - **`Retry-After`.** When the server tells you when to come back, wait at
//!   least that long; never retry sooner than the server asked.
//!
//! The random source is injected as a closure so the delay math is deterministic
//! under test.

use crate::problems::state_machine::ApiError;
use std::time::Duration;

/// An error that knows whether retrying could help.
pub trait Retryable {
    /// `true` if the operation is worth retrying.
    fn is_retryable(&self) -> bool;

    /// A server-provided minimum delay, such as HTTP `Retry-After`.
    fn retry_after(&self) -> Option<Duration> {
        None
    }
}

impl Retryable for ApiError {
    fn is_retryable(&self) -> bool {
        ApiError::is_retryable(self)
    }

    fn retry_after(&self) -> Option<Duration> {
        match self {
            ApiError::RateLimited { retry_after } => Some(*retry_after),
            _ => None,
        }
    }
}
```

`retry_after` has a default body returning `None`, so an error type that has no
server-provided delay implements only `is_retryable`.

`impl Retryable for ApiError` calls `ApiError::is_retryable(self)`, the inherent method
from chapter 19, which has the same name as the trait method being defined. Method-call
syntax would reach the same function, because inherent methods take priority over trait
methods, but a reader would have to know that rule to see that `self.is_retryable()`
does not recurse. The path form states the target directly.

```rust
/// How randomness is applied to the backoff.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Jitter {
    /// Delay is exactly the capped exponential backoff.
    None,
    /// Delay is `unit_random * capped_backoff` (AWS "full jitter").
    Full,
}

/// Backoff configuration.
#[derive(Debug, Clone, Copy)]
pub struct RetryPolicy {
    /// Total attempts, including the first one. Must be at least 1.
    pub max_attempts: u32,
    /// Delay before the first retry.
    pub base_delay: Duration,
    /// Upper bound on a single delay.
    pub max_delay: Duration,
    pub jitter: Jitter,
}

impl RetryPolicy {
    pub fn new(
        max_attempts: u32,
        base_delay: Duration,
        max_delay: Duration,
        jitter: Jitter,
    ) -> Self {
        assert!(max_attempts > 0, "max_attempts must be > 0");
        Self {
            max_attempts,
            base_delay,
            max_delay,
            jitter,
        }
    }

    /// Capped exponential backoff for a zero-based retry attempt:
    /// `min(base * 2^attempt, max_delay)`.
    pub fn exponential_delay(&self, attempt: u32) -> Duration {
        let shift = attempt.min(31);
        let factor = 1u32 << shift;
        self.base_delay.saturating_mul(factor).min(self.max_delay)
    }

    /// Backoff for `attempt` with `unit_random` in `[0, 1)` applied when jitter
    /// is enabled.
    pub fn delay_for(&self, attempt: u32, unit_random: f64) -> Duration {
        let capped = self.exponential_delay(attempt);
        match self.jitter {
            Jitter::None => capped,
            Jitter::Full => capped.mul_f64(unit_random.clamp(0.0, 1.0)),
        }
    }
}
```

`exponential_delay` computes `2^attempt` as `1u32 << attempt.min(31)`. The `min` keeps
the shift below 32, where shifting a `u32` would overflow. `Duration::saturating_mul`
returns `Duration::MAX` instead of panicking when the product is too large, and `.min`
then applies the cap. Attempt 50 therefore produces `max_delay`, as the test checks.

`delay_for` clamps `unit_random` to `[0.0, 1.0]` before `Duration::mul_f64`, which
panics on a negative or non-finite factor. A faulty random source cannot crash the retry
loop.

`RetryPolicy::new` asserts `max_attempts > 0`. The fields are also `pub`, so a caller can
build a policy with a struct literal and bypass the assertion.

```rust
/// Retry `operation` until it succeeds, fails permanently, or the policy is
/// exhausted.
///
/// `unit_random` must return values in `[0, 1)`; pass `|| 0.0` for deterministic
/// tests or a real RNG in production.
pub fn retry<T, E, F, R>(policy: &RetryPolicy, mut operation: F, mut unit_random: R) -> Result<T, E>
where
    F: FnMut(u32) -> Result<T, E>,
    E: Retryable,
    R: FnMut() -> f64,
{
    let mut attempt = 0;
    loop {
        match operation(attempt) {
            Ok(value) => return Ok(value),
            Err(error) => {
                let exhausted = attempt + 1 >= policy.max_attempts;
                if exhausted || !error.is_retryable() {
                    return Err(error);
                }

                let backoff = policy.delay_for(attempt, unit_random());
                // Honor the server's hint, but never retry sooner than our own
                // backoff says is healthy.
                let delay = error
                    .retry_after()
                    .map_or(backoff, |hint| hint.max(backoff));

                std::thread::sleep(delay);
                attempt += 1;
            }
        }
    }
}
```

The operation is `FnMut(u32) -> Result<T, E>`. `FnMut` allows it to update state between
calls, such as a counter in a test, and the `u32` argument tells it which attempt it is
running, which is useful for logging.

`attempt + 1 >= policy.max_attempts` checks whether the attempt that just failed was the
last one. With `max_attempts = 3`, attempts 0, 1, and 2 run, and the error from attempt 2
is returned without a final sleep.

`error.retry_after().map_or(backoff, |hint| hint.max(backoff))` returns the backoff when
there is no hint and the larger of the two when there is.

```rust
#[cfg(test)]
mod tests {
    use super::*;

    fn policy(max_attempts: u32, jitter: Jitter) -> RetryPolicy {
        RetryPolicy::new(
            max_attempts,
            Duration::from_millis(100),
            Duration::from_millis(1_000),
            jitter,
        )
    }

    #[test]
    fn exponential_backoff_doubles_until_capped() {
        let policy = policy(6, Jitter::None);
        assert_eq!(policy.exponential_delay(0), Duration::from_millis(100));
        assert_eq!(policy.exponential_delay(1), Duration::from_millis(200));
        assert_eq!(policy.exponential_delay(2), Duration::from_millis(400));
        assert_eq!(policy.exponential_delay(3), Duration::from_millis(800));
        // Capped from here on.
        assert_eq!(policy.exponential_delay(4), Duration::from_millis(1_000));
        assert_eq!(policy.exponential_delay(50), Duration::from_millis(1_000));
    }

    #[test]
    fn full_jitter_scales_the_delay() {
        let policy = policy(6, Jitter::Full);
        assert_eq!(policy.delay_for(2, 0.0), Duration::ZERO);
        assert_eq!(policy.delay_for(2, 0.5), Duration::from_millis(200));
        // Values above 1.0 are clamped rather than overflowing.
        assert_eq!(policy.delay_for(2, 9.9), Duration::from_millis(400));
    }

    #[test]
    fn retries_then_succeeds() {
        let policy = RetryPolicy::new(5, Duration::ZERO, Duration::ZERO, Jitter::None);
        let mut attempts = 0;
        let result: Result<u32, ApiError> = retry(
            &policy,
            |_| {
                attempts += 1;
                if attempts < 3 {
                    Err(ApiError::Server {
                        status: 503,
                        message: "temporarily unavailable".into(),
                    })
                } else {
                    Ok(42)
                }
            },
            || 0.0,
        );

        assert_eq!(result, Ok(42));
        assert_eq!(attempts, 3);
    }

    #[test]
    fn non_retryable_errors_return_immediately() {
        let policy = RetryPolicy::new(5, Duration::ZERO, Duration::ZERO, Jitter::None);
        let mut attempts = 0;
        let result: Result<(), ApiError> = retry(
            &policy,
            |_| {
                attempts += 1;
                Err(ApiError::NotFound {
                    resource_id: "gpu-0".into(),
                })
            },
            || 0.0,
        );

        assert!(result.is_err());
        assert_eq!(attempts, 1);
    }

    #[test]
    fn exhausted_policy_returns_the_last_error() {
        let policy = RetryPolicy::new(3, Duration::ZERO, Duration::ZERO, Jitter::None);
        let mut attempts = 0;
        let result: Result<(), ApiError> = retry(
            &policy,
            |_| {
                attempts += 1;
                Err(ApiError::Server {
                    status: 500,
                    message: "boom".into(),
                })
            },
            || 0.0,
        );

        assert!(result.is_err());
        assert_eq!(attempts, 3);
    }

    #[test]
    fn retry_after_is_honored_as_a_floor() {
        let policy = policy(2, Jitter::None);
        let error = ApiError::RateLimited {
            retry_after: Duration::from_secs(5),
        };
        let backoff = policy.delay_for(0, 0.0);
        let chosen = error
            .retry_after()
            .map_or(backoff, |hint| hint.max(backoff));
        assert_eq!(chosen, Duration::from_secs(5));
    }
}
```

The loop tests use a policy with zero delays, so they run without sleeping.

## Intuition

**`retries_then_succeeds` with `max_attempts = 5` and zero delays**

| attempt | operation result | exhausted? | retryable? | action |
|---|---|---|---|---|
| 0 | `Err(Server { status: 503, .. })` | `1 >= 5` is false | yes | sleep 0, attempt = 1 |
| 1 | `Err(Server { status: 503, .. })` | `2 >= 5` is false | yes | sleep 0, attempt = 2 |
| 2 | `Ok(42)` | | | return `Ok(42)` |

**Delays for a policy of base 100 ms and cap 1 s with full jitter**

| attempt | capped backoff | `unit_random` | delay | server `Retry-After` | chosen |
|---|---|---|---|---|---|
| 0 | 100 ms | 0.37 | 37 ms | none | 37 ms |
| 1 | 200 ms | 0.90 | 180 ms | none | 180 ms |
| 2 | 400 ms | 0.10 | 40 ms | 5 s | 5 s |

## Time and Space Complexity

| Operation | Cost |
|---|---|
| `exponential_delay`, `delay_for` | `O(1)` |
| `retry` | at most `max_attempts` calls to `operation`, and the sum of the chosen delays in wall-clock time |
| memory | none beyond what `operation` uses |

With full jitter the expected total delay is half the sum of the capped backoffs.

## Limitations

**`retry` blocks the thread.** The loop calls `std::thread::sleep`. In an async program
that would stall an executor thread; an async version awaits a timer such as
`tokio::time::sleep` instead, as chapter 58 does.

**The `Retry-After` test does not call `retry`.** `retry_after_is_honored_as_a_floor`
repeats the expression from the loop and checks its value, because calling `retry` with
a five-second hint would make the test sleep for five seconds. The loop's use of the hint
is therefore untested. Injecting the sleep function, as the random source already is,
would let a test record the requested delays without waiting.

**`Retry-After` is not capped.** A server that answers `Retry-After: 3600` makes the loop
sleep for an hour. A client usually caps the hint, or gives up and reports it to the
caller, rather than blocking that long.

**Retryability ignores the request.** A 503 is retryable for a `GET` and dangerous for a
`POST` that may already have created a resource on the server. The policy knows only
the error. Chapter 54's `Method::is_idempotent`, or an idempotency key as in chapter 34,
supplies the missing information.

**No overall deadline.** A caller that needs an answer within two seconds cannot say so;
the policy bounds the number of attempts, not the elapsed time.

## Summary

- A `Retryable` trait lets the loop ask each error whether waiting can help and whether
  the server requested a delay.
- Capped exponential backoff is `min(base × 2^attempt, max)`; `saturating_mul` and a
  bounded shift keep the arithmetic from overflowing.
- Full jitter chooses a delay uniformly in `[0, capped]`, which spreads retries from
  many clients across time.
- Injecting the random source makes the delay arithmetic deterministic under test; the
  sleep function deserves the same treatment.
- A server's `Retry-After` is a lower bound, and retries of non-idempotent requests need
  information the error type does not carry.

## References

- Marc Brooker, "Exponential Backoff And Jitter", AWS Architecture Blog, 2015.
- RFC 9110, *HTTP Semantics*, 2022, Section 10.2.3, `Retry-After`.
- Google Cloud, "Retry strategy", Cloud Storage documentation, on truncated exponential
  backoff.
- Standard library, [`Duration::saturating_mul`](https://doc.rust-lang.org/std/time/struct.Duration.html#method.saturating_mul) and [`Duration::mul_f64`](https://doc.rust-lang.org/std/time/struct.Duration.html#method.mul_f64).
