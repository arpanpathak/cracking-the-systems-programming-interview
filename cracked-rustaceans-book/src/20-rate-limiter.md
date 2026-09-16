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

<p class="listing"><span class="listing-label">Listing 20.1</span> The complete module, with its tests. <code>src/problems/rate_limiter.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/rate_limiter.rs">read the file on GitHub</a></p>

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

## Summary

- A bucket of at most `capacity` tokens refilled at `rate` per second admits a burst of
  `capacity` and then holds the sustained rate, which is the behaviour a fixed window
  cannot express.
- The refill is computed from the elapsed time on each call rather than by a timer
  thread, so the bucket costs no thread and its state does not depend on how the
  scheduler ran one.
- The refill is capped at the capacity, which is what keeps an idle bucket from
  accumulating an unbounded burst.
- Each call is constant time behind one uncontended mutex acquisition, and the state is
  three machine words.

## References

- Standard library, [`Mutex`](https://doc.rust-lang.org/std/sync/struct.Mutex.html).
- Standard library, [`Instant`](https://doc.rust-lang.org/std/time/struct.Instant.html).
- Standard library, [`f64::min`](https://doc.rust-lang.org/std/primitive.f64.html#method.min).
