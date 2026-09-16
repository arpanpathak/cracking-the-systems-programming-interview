# 37. Fibonacci Three Ways {#fibonacci}

*Source file: [`src/bin/cs_fib.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/cs_fib.rs). Run it with `cargo run --release --bin cs_fib`.*

## Problem Statement

Compute the `n`-th Fibonacci number, where `fib(0) = 0`, `fib(1) = 1`, and
`fib(n) = fib(n - 1) + fib(n - 2)` for `n >= 2`. The result type is `u64`.

## Designing a Solution

The recurrence can be transcribed directly into a recursive function. The difficulty
is visible in its call tree, shown below: `fib(5)` computes `fib(3)` twice
and `fib(2)` three times, and the duplication doubles at every level.

```text
                          fib(5)
                 /                      \
             fib(4)                    fib(3)
            /      \                  /      \
        fib(3)    fib(2)          fib(2)    fib(1)
        /    \    /    \          /    \
    fib(2) fib(1) fib(1) fib(0) fib(1) fib(0)
    /    \
fib(1) fib(0)
```

The number of calls made by `recursive(n)` is `2 * fib(n + 1) - 1`, which grows by a
factor of about 1.618 for every increment of `n`. For `n = 30` that is 2,692,537 calls
to produce one number.

Two changes remove the duplication.

**Memoization** keeps the recursion and stores each answer the first time it is
computed. Every later request for the same subproblem is a table read, so each of the
`n + 1` subproblems is computed once.

**Iteration** reverses the direction. It starts from `fib(0)` and `fib(1)` and
advances a pair of accumulators `n` times. It needs only the previous two values, so
it uses constant space.

## Implementation

The first listing shows the three functions.

<p class="listing"><span class="listing-label">Listing 37.1</span> <code>recursive</code>, <code>iterative</code>, and <code>memoized</code>. <code>src/bin/cs_fib.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/cs_fib.rs">read the file on GitHub</a></p>

`recursive` is the recurrence written as an `if` expression. Nothing in it is wrong
except its cost.

`iterative` keeps `(previous, current)` equal to `(fib(i), fib(i + 1))` at the start of
iteration `i`. The statement `(previous, current) = (current, previous + current)` is a
destructuring assignment, stable since Rust 1.59. The right side is evaluated in full
before either variable is written, so no temporary is needed. After `n` iterations,
`previous` holds `fib(n)`.

`memoized` declares a nested function `go` that receives the cache as `&mut [u64]`. A
nested `fn` cannot capture variables from the enclosing function, so the cache is
passed explicitly, as in chapter 13. A cache slot holding `0` means "not yet
computed". That sentinel is safe because `fib(n)` is zero only for `n = 0`, and
`n < 2` is handled before the cache is consulted.

The second listing shows the timing helper and `main`.

<p class="listing"><span class="listing-label">Listing 37.2</span> <code>timed</code> and <code>report</code>. <code>src/bin/cs_fib.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/cs_fib.rs">read the file on GitHub</a></p>

`timed` accepts the function as `impl Fn(u64) -> u64`. Each of the three function
items has its own zero-sized type, so each call to `timed` is monomorphised for that
function, and the call inside `timed` is a direct call.

The assertions at the end of `main` compare the three versions for `n` below 20 and
pin two known values. The program prints `all checks passed` only when they hold.

## Intuition

`iterative(5)` runs five iterations:

```text
iteration   previous   current   after (previous, current) = (current, previous + current)
start           0          1
1               1          1
2               1          2
3               2          3
4               3          5
5               5          8
return previous = 5
```

A release build on an NVIDIA Jetson board with an 8-core Cortex-A78AE
printed the following:

```text
small input, all three should agree
  recursive  fib(20) = 6765                 in 39.489µs
  iterative  fib(20) = 6765                 in 64ns
  memoized   fib(20) = 6765                 in 928ns

recursive cost grows quickly
  recursive  fib(30) = 832040               in 4.508408ms
  iterative  fib(30) = 832040               in 64ns

large input: recursion alone would not finish
  iterative  fib(90) = 2880067194370816120  in 96ns
  memoized   fib(90) = 2880067194370816120  in 7.681µs

all checks passed
```

Going from `n = 20` to `n = 30` multiplies the recursive time by about 114, close to
`1.618^10 ≈ 123`. At that rate `recursive(90)` would take about 1.5 × 10^10
seconds, several centuries. The memoized version is slower than the iterative one because it allocates
a vector of `n + 1` entries and makes `2n - 1` function calls. A single timed run of a
function this short is dominated by measurement noise, so the nanosecond figures
indicate order of magnitude only.

## Time and Space Complexity

| Version | Time | Space |
|---|---|---|
| `recursive` | `O(φ^n)`, where `φ ≈ 1.618` | `O(n)` stack frames |
| `memoized` | `O(n)` | `O(n)` for the cache and `O(n)` stack frames |
| `iterative` | `O(n)` | `O(1)` |

## Limitations

**`u64` overflows early.** `fib(93)` is the largest Fibonacci number that fits in a
`u64`. `iterative` computes one term ahead, so `iterative(93)` evaluates `fib(94)` in
its last iteration and panics with an arithmetic overflow in a debug build, even
though the value it returns would fit. In a release build the addition wraps silently.
`checked_add` would turn both into an explicit error, and `u128` extends the range to
`fib(186)`.

**`memoized` recurses to depth `n`.** Each level uses one stack frame. With a `u64`
result the value overflows at `n = 94`, long before the depth matters, but a version
widened to an arbitrary-precision integer would reach the stack limit for large `n`.
The iterative version has no such limit.

**`memoized` uses `0` as a sentinel.** The choice is correct for this sequence and
would be wrong for a recurrence whose answers can be zero. `Option<u64>` in the cache,
or a separate `computed` bitmap, removes the dependency on the values.

**`n as usize` assumes a 64-bit target.** On a 32-bit target a `u64` larger than
`u32::MAX` truncates when cast. The values of `n` that can produce a `u64` result are
far below that limit, so the cast is safe in practice and not in general.

**The timings are single runs.** Chapter 24 and chapter 40 describe the warm-up and
repetition a measurement needs before its figures can be quoted.

## Summary

- Direct recursion on the Fibonacci recurrence makes `2 · fib(n + 1) - 1` calls, which
  is exponential in `n`.
- Memoization stores each subproblem's answer on first computation, reducing the work
  to `O(n)` while keeping the recursive structure.
- Iteration computes the same values bottom-up with two accumulators in `O(1)` space;
  tuple assignment updates both without a temporary.
- `fib(93)` is the largest value that fits in `u64`, and the iterative loop overflows
  one step earlier because it computes one term ahead.

## References

- Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, and Clifford Stein,
  *Introduction to Algorithms*, 4th edition, MIT Press, 2022, Chapter 7, "Dynamic
  Programming".
- The Rust Reference, [Destructuring assignments](https://doc.rust-lang.org/reference/expressions/operator-expr.html#destructuring-assignments).
- Standard library, [`u64::checked_add`](https://doc.rust-lang.org/std/primitive.u64.html#method.checked_add).
