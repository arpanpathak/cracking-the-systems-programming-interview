// ch04/race.rs: the unsynchronized counter in Rust. Reading or writing a
// `static mut` requires an unsafe block; the data race itself is real.
// read_volatile/write_volatile keep each iteration's read and write in memory.
use std::ptr::{addr_of, addr_of_mut, read_volatile, write_volatile};
use std::thread;

static mut COUNTER: u64 = 0;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    const THREADS: usize = 8;
    const ITERS: u64 = 20_000_000;

    let mut handles = Vec::new();
    for _ in 0..THREADS {
        handles.push(thread::spawn(|| {
            let p = addr_of_mut!(COUNTER);

            for _ in 0..ITERS {
                // Microarchitectural Dynamics:
                // An unsynchronized read-modify-write on shared mutable memory (`COUNTER`) violates
                // the fundamental atomicity requirement. At the hardware level, this decompiles into
                // three distinct micro-operations:
                //   1. LOAD [p] -> register
                //   2. ADD register, 1
                //   3. STORE register -> [p]
                // When 8 cores execute this concurrently, core store buffers and cache coherency
                // invalidations (MESI/MOESI) interleave unpredictably. Between Step 1 and Step 3,
                // another core overwrites [p], leading to lost updates. In Rust, this unsynchronized
                // concurrent mutation of a static variable is undefined behavior by definition.
                let v = unsafe { read_volatile(p) };
                unsafe { write_volatile(p, v + 1) };
            }
        }));
    }

    for h in handles {
        h.join().map_err(|_| "worker thread panicked")?;
    }

    // SAFETY: Synchronization Barrier Proof:
    // Calling `join()` on all 8 thread handles establishes a strict "happens-before" edge
    // between worker thread completion and the parent thread. Because all worker threads
    // have fully terminated, no concurrent writers exist, allowing safe inspection of the
    // final counter value.
    let observed = unsafe { read_volatile(addr_of!(COUNTER)) };
    println!("expected {}, observed {observed}", THREADS as u64 * ITERS);
    Ok(())
}
