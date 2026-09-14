use std::sync::atomic::{AtomicU64, Ordering};
use std::thread;
use std::time::{Duration, Instant};

const ITERS: u64 = 20_000_000;

/// Both counters are guaranteed to live inside one 64-byte cache line.
#[repr(align(64))]
struct SameLine {
    a: AtomicU64,
    b: AtomicU64,
}

/// Each of these occupies its own 64-byte block.
#[repr(align(64))]
struct Padded(AtomicU64);

fn time<F: FnOnce()>(f: F) -> Duration {
    let t = Instant::now();
    f();
    t.elapsed()
}

fn main() {
    // ---- 1. False sharing: two counters on the same cache line ----
    let same = SameLine { a: AtomicU64::new(0), b: AtomicU64::new(0) };

    let d1 = time(|| {
        thread::scope(|s| {
            s.spawn(|| for _ in 0..ITERS { same.a.fetch_add(1, Ordering::Relaxed); });
            s.spawn(|| for _ in 0..ITERS { same.b.fetch_add(1, Ordering::Relaxed); });
        });
    });

    // ---- 2. Padded: same work, but counters are on separate cache lines ----
    let p0 = Padded(AtomicU64::new(0));
    let p1 = Padded(AtomicU64::new(0));

    let d2 = time(|| {
        thread::scope(|s| {
            s.spawn(|| for _ in 0..ITERS { p0.0.fetch_add(1, Ordering::Relaxed); });
            s.spawn(|| for _ in 0..ITERS { p1.0.fetch_add(1, Ordering::Relaxed); });
        });
    });

    println!("same cache line (false sharing): {:?}", d1);
    println!("padded (separate lines):         {:?}", d2);
}
