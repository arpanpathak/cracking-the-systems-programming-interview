//! Cache locality: the same data is much faster to walk in order than to jump
//! around, because memory moves in cache lines and the prefetcher helps only the
//! sequential case.
//!
//! Run with: cargo run --bin cs_locality

use std::time::{Duration, Instant};

/// A power of two, so a stride must be odd to visit every index.
const ELEMENTS: usize = 4 * 1024 * 1024;

/// Odd, and therefore coprime with `ELEMENTS`: the walk visits every slot once.
const STRIDE: usize = 1_000_003;

fn sequential_sum(data: &[u64]) -> (u64, Duration) {
    let start = Instant::now();
    let sum = data.iter().sum();
    (sum, start.elapsed())
}

fn strided_sum(data: &[u64]) -> (u64, Duration) {
    let start = Instant::now();
    let mut index = 0usize;
    let mut sum = 0u64;
    for _ in 0..data.len() {
        index = (index + STRIDE) % data.len();
        sum = sum.wrapping_add(data[index]);
    }
    (sum, start.elapsed())
}

fn main() {
    let data: Vec<u64> = (0..ELEMENTS as u64).collect();
    println!(
        "{} elements, {} MiB",
        data.len(),
        data.len() * 8 / (1024 * 1024)
    );

    let (sequential, sequential_time) = sequential_sum(&data);
    let (strided, strided_time) = strided_sum(&data);

    println!("\n  sequential: {sequential} in {sequential_time:?}");
    println!("  strided:    {strided} in {strided_time:?}");

    // Both touch every element exactly once, so the sums must match; only the
    // access pattern differs.
    assert_eq!(sequential, strided);
    assert_eq!(sequential, ELEMENTS as u64 * (ELEMENTS as u64 - 1) / 2);

    println!("\nequal work, different pattern; timings vary by machine");
}
