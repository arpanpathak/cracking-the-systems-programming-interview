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
