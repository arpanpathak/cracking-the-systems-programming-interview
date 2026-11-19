// ch04/race_atomic.rs: the same counter with an atomic increment.
use std::sync::atomic::{AtomicU64, Ordering};
use std::thread;

static COUNTER: AtomicU64 = AtomicU64::new(0);

fn main() {
    const THREADS: usize = 8;
    const ITERS: u64 = 5_000_000;

    let mut handles = Vec::new();
    for _ in 0..THREADS {
        handles.push(thread::spawn(|| {
            for _ in 0..ITERS {
                // Memory Ordering Proof:
                // `Ordering::Relaxed` guarantees hardware-level indivisibility of the Read-Modify-Write
                // (`lock xadd` on x86-64; `ldadd` on ARM64) on the single `COUNTER` cache line,
                // ensuring total modification order without paying the pipeline-stall cost of memory
                // fences (`SeqCst` / `AcqRel`). Because no other memory locations depend on the
                // intermediate value of `COUNTER`, relaxed ordering is both necessary and sufficient.
                COUNTER.fetch_add(1, Ordering::Relaxed);
            }
        }));
    }

    for h in handles {
        h.join().unwrap();
    }

    // Synchronization Proof: `JoinHandle::join()` provides an acquire-release synchronization barrier
    // with each thread's termination, guaranteeing all relaxed `fetch_add` stores are visible here.
    println!(
        "expected {}, observed {}",
        THREADS as u64 * ITERS,
        COUNTER.load(Ordering::Relaxed)
    );
}
