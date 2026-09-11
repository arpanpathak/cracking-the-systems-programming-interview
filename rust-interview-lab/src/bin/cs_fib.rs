//! Three ways to compute Fibonacci: naive recursion, iteration, and memoization.
//! The first shows why exponential blowup happens; the other two fix it.
//!
//! Run with: cargo run --bin cs_fib

use std::time::{Duration, Instant};

/// Exponential: fib(n) recomputes fib(n - 1) and fib(n - 2) from scratch.
fn recursive(n: u64) -> u64 {
    if n < 2 {
        n
    } else {
        recursive(n - 1) + recursive(n - 2)
    }
}

/// Linear time, constant space.
fn iterative(n: u64) -> u64 {
    let (mut previous, mut current) = (0u64, 1u64);
    for _ in 0..n {
        (previous, current) = (current, previous + current);
    }
    previous
}

/// Linear time, linear space: recursion plus a cache of subproblem answers.
fn memoized(n: u64) -> u64 {
    fn go(n: u64, cache: &mut [u64]) -> u64 {
        if n < 2 {
            return n;
        }
        let index = n as usize;
        if cache[index] == 0 {
            cache[index] = go(n - 1, cache) + go(n - 2, cache);
        }
        cache[index]
    }

    let mut cache = vec![0u64; n as usize + 1];
    go(n, &mut cache)
}

fn timed(label: &str, n: u64, operation: impl Fn(u64) -> u64) {
    let start = Instant::now();
    let value = operation(n);
    report(label, n, value, start.elapsed());
}

fn report(label: &str, n: u64, value: u64, elapsed: Duration) {
    println!("  {label:<10} fib({n:>2}) = {value:<20} in {elapsed:?}");
}

fn main() {
    println!("small input, all three should agree");
    timed("recursive", 20, recursive);
    timed("iterative", 20, iterative);
    timed("memoized", 20, memoized);

    println!("\nrecursive cost grows quickly");
    timed("recursive", 30, recursive);
    timed("iterative", 30, iterative);

    println!("\nlarge input: recursion alone would not finish");
    timed("iterative", 90, iterative);
    timed("memoized", 90, memoized);

    for n in 0..20 {
        assert_eq!(recursive(n), iterative(n));
        assert_eq!(memoized(n), iterative(n));
    }
    assert_eq!(iterative(30), 832_040);
    assert_eq!(iterative(90), 2_880_067_194_370_816_120);

    println!("\nall checks passed");
}
