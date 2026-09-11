//! False sharing: two independent counters that land on the same cache line make
//! each other slow, because every write moves the line between cores.
//!
//! Run with: cargo run --bin concurrency_false_sharing

use std::mem::size_of;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::thread;
use std::time::{Duration, Instant};

const THREADS: usize = 4;
const ITERATIONS: usize = 2_000_000;

/// Packed by default: consecutive counters share a cache line.
struct Unpadded(AtomicUsize);

impl Unpadded {
    fn new() -> Self {
        Self(AtomicUsize::new(0))
    }

    fn increment(&self) {
        self.0.fetch_add(1, Ordering::Relaxed);
    }
}

/// Padded to a cache line, so no two counters share one.
#[repr(align(64))]
struct Padded(AtomicUsize);

impl Padded {
    fn new() -> Self {
        Self(AtomicUsize::new(0))
    }

    fn increment(&self) {
        self.0.fetch_add(1, Ordering::Relaxed);
    }
}

/// Scoped threads borrow the vector directly, so there is no `Arc` and no clone.
fn run_unpadded() -> Duration {
    let counters: Vec<Unpadded> = (0..THREADS).map(|_| Unpadded::new()).collect();
    let start = Instant::now();
    thread::scope(|scope| {
        for counter in &counters {
            scope.spawn(move || {
                for _ in 0..ITERATIONS {
                    counter.increment();
                }
            });
        }
    });
    start.elapsed()
}

fn run_padded() -> Duration {
    let counters: Vec<Padded> = (0..THREADS).map(|_| Padded::new()).collect();
    let start = Instant::now();
    thread::scope(|scope| {
        for counter in &counters {
            scope.spawn(move || {
                for _ in 0..ITERATIONS {
                    counter.increment();
                }
            });
        }
    });
    start.elapsed()
}

fn main() {
    println!("atomic:   {} bytes", size_of::<AtomicUsize>());
    println!(
        "unpadded: {} bytes (several counters per 64 byte line)",
        size_of::<Unpadded>()
    );
    println!(
        "padded:   {} bytes (one counter per 64 byte line)",
        size_of::<Padded>()
    );

    let unpadded = run_unpadded();
    let padded = run_padded();

    println!("\n{THREADS} threads x {ITERATIONS} increments, each on its own counter");
    println!("  unpadded (shared lines): {unpadded:?}");
    println!("  padded   (own line):     {padded:?}");

    assert!(size_of::<Padded>() >= 64, "padding must fill a cache line");
    assert!(unpadded.as_nanos() > 0 && padded.as_nanos() > 0);

    println!("\ntimings vary by machine; the padded run is normally the faster one");
}
