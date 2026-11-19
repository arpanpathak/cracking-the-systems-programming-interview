// ch18/cache_bench.rs: the same memory-hierarchy walk in Rust.
use std::time::Instant;

fn ns_per_access(bytes: usize) {
    const ACCESSES: u64 = 16_000_000;
    let mut v = vec![0u8; bytes];

    // Touch every 64th byte once so page faults do not dominate the timing.
    for i in (0..bytes).step_by(64) {
        v[i] = 1;
    }

    let mut sum: u64 = 0;
    let mut i = 0usize;
    let t0 = Instant::now();
    for _ in 0..ACCESSES {
        sum += v[i] as u64;
        i += 64;
        if i >= bytes {
            i = 0;
        }
    }

    let ns = t0.elapsed().as_nanos() as f64 / ACCESSES as f64;
    println!("  {bytes:9} bytes  {ns:7.1} ns per access  (checksum {sum})");
}

fn main() {
    println!("stride 64 bytes, 16,000,000 accesses per size\n");

    let mut s = 16 * 1024usize;
    while s <= 256 * 1024 * 1024 {
        ns_per_access(s);
        s *= 4;
    }
}
