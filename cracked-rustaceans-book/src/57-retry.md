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

<p class="listing"><span class="listing-label">Listing 57.1</span> <code>Retryable</code>, <code>is_retryable</code>, and <code>retry_after</code>. <code>src/problems/retry.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/retry.rs">read the file on GitHub</a></p>

`retry_after` has a default body returning `None`, so an error type that has no
server-provided delay implements only `is_retryable`.

`impl Retryable for ApiError` calls `ApiError::is_retryable(self)`, the inherent method
from chapter 19, which has the same name as the trait method being defined. Method-call
syntax would reach the same function, because inherent methods take priority over trait
methods, but a reader would have to know that rule to see that `self.is_retryable()`
does not recurse. The path form states the target directly.

<p class="listing"><span class="listing-label">Listing 57.2</span> <code>Jitter</code>, <code>RetryPolicy</code>, and <code>new</code>. <code>src/problems/retry.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/retry.rs">read the file on GitHub</a></p>

`exponential_delay` computes `2^attempt` as `1u32 << attempt.min(31)`. The `min` keeps
the shift below 32, where shifting a `u32` would overflow. `Duration::saturating_mul`
returns `Duration::MAX` instead of panicking when the product is too large, and `.min`
then applies the cap. Attempt 50 therefore produces `max_delay`, as the test checks.

`delay_for` clamps `unit_random` to `[0.0, 1.0]` before `Duration::mul_f64`, which
panics on a negative or non-finite factor. A faulty random source cannot crash the retry
loop.

`RetryPolicy::new` asserts `max_attempts > 0`. The fields are also `pub`, so a caller can
build a policy with a struct literal and bypass the assertion.

<p class="listing"><span class="listing-label">Listing 57.3</span> <code>retry</code>. <code>src/problems/retry.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/retry.rs">read the file on GitHub</a></p>

The operation is `FnMut(u32) -> Result<T, E>`. `FnMut` allows it to update state between
calls, such as a counter in a test, and the `u32` argument tells it which attempt it is
running, which is useful for logging.

`attempt + 1 >= policy.max_attempts` checks whether the attempt that just failed was the
last one. With `max_attempts = 3`, attempts 0, 1, and 2 run, and the error from attempt 2
is returned without a final sleep.

`error.retry_after().map_or(backoff, |hint| hint.max(backoff))` returns the backoff when
there is no hint and the larger of the two when there is.

<p class="listing"><span class="listing-label">Listing 57.4</span> The tests for the module. <code>src/problems/retry.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/retry.rs">read the file on GitHub</a></p>

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
