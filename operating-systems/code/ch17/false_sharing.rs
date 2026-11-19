// ch17/false_sharing.rs: the same experiment with atomic counters.
use std::sync::atomic::{AtomicU64, Ordering};
use std::thread;
use std::time::Instant;

#[repr(C, align(64))]
struct Unpadded {
    a: AtomicU64,
    b: AtomicU64,   // shares a's cache line
}

#[repr(C, align(64))]
struct Padded {
    a: AtomicU64,
    pad: [u64; 7],
    b: AtomicU64,   // 64 bytes after a: its own line
}

fn bench(a: &AtomicU64, b: &AtomicU64) -> f64 {
    const ITERS: u64 = 40_000_000;

    let t0 = Instant::now();
    thread::scope(|s| {
        s.spawn(|| {
            for _ in 0..ITERS {
                a.fetch_add(1, Ordering::Relaxed);
            }
        });

        s.spawn(|| {
            for _ in 0..ITERS {
                b.fetch_add(1, Ordering::Relaxed);
            }
        });
    });

    t0.elapsed().as_secs_f64() * 1000.0
}

fn main() {
    let u = Unpadded { a: AtomicU64::new(0), b: AtomicU64::new(0) };
    let p = Padded { a: AtomicU64::new(0), pad: [0; 7], b: AtomicU64::new(0) };

    bench(&u.a, &u.b);            // warmup
    bench(&p.a, &p.b);

    let tu = bench(&u.a, &u.b);
    let tp = bench(&p.a, &p.b);

    println!("unpadded (shared line): {tu:7.1} ms");
    println!("padded   (separate)   : {tp:7.1} ms");
    println!("ratio                 : {:5.2}x", tu / tp);
    println!(
        "(unpadded {}, padded {})",
        u.a.load(Ordering::Relaxed),
        p.a.load(Ordering::Relaxed)
    );
}
