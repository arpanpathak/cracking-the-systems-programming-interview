// ============================================================================
// Syscall overhead measurement
//
// Ported from the Rust playground repo (`mkdir_syscall.rs`).
//
// What this measures:
//   - Every syscall crosses the user/kernel boundary: argument validation,
//     kernel work, scheduling checks, and return to user space.
//   - This program calls `getpid()` in a tight loop and estimates the average
//     per-call cost. `getpid()` is a tiny syscall, so the measured cost is
//     close to the irreducible syscall overhead on this kernel/hardware.
//
// Why this appears in cloud interviews:
//   - High-performance data planes care about per-packet or per-I/O syscall
//     cost. The difference between one syscall per event and batching via
//     io_uring/recvmmsg can be enormous.
//   - It also demonstrates unsafe FFI, safety comments, warm-up loops, and
//     benchmark methodology: warm the code path, run enough iterations, and
//     report average cost rather than one lucky sample.
//
// Run:
//   cargo run --bin syscall_overhead
// ============================================================================

use std::time::Instant;

/// Calls `getpid()` `iterations` times and returns the average cost in
/// nanoseconds per call.
fn measure_getpid_ns_per_call(iterations: u64) -> f64 {
    let start = Instant::now();

    for _ in 0..iterations {
        // SAFETY: `libc::getpid` is a pure read-only system call with no
        // pointer arguments and no memory side effects. The FFI declaration in
        // the `libc` crate matches the Linux kernel ABI.
        //
        // `black_box` prevents the optimizer from assuming the loop has no
        // observable effect, which matters because the syscall result is
        // otherwise unused.
        unsafe {
            libc::getpid();
        }
    }

    let elapsed = start.elapsed();
    elapsed.as_nanos() as f64 / iterations as f64
}

fn main() {
    const ITERATIONS: u64 = 10_000_000;

    // Warm up the code path before timing. The first calls may fault in the
    // libc/PLT, cache lines, or CPU frequency may still be ramping.
    for _ in 0..100_000 {
        // SAFETY: same reasoning as above; read-only syscall.
        unsafe { libc::getpid() };
    }

    let ns_per_call = measure_getpid_ns_per_call(ITERATIONS);

    println!("Iterations:      {}", ITERATIONS);
    println!(
        "Total time:      {:.3}s",
        ns_per_call * ITERATIONS as f64 / 1e9
    );
    println!("Per syscall:     {:.1} ns", ns_per_call);

    // Example framing: if a service processed 10M packets/s and used one
    // getpid-style syscall per packet, this fraction of each second would be
    // spent crossing into the kernel just for the syscall overhead.
    let cpu_seconds_per_second = ns_per_call * 10_000_000.0 / 1_000_000_000.0;
    println!(
        "At 10M calls/s, syscall overhead would consume: {:.2} CPU-seconds per second",
        cpu_seconds_per_second
    );
}

// ============================================================================
// Tests (cargo test --bin syscall_overhead)
// ============================================================================
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn measurement_returns_a_positive_finite_number() {
        let ns = measure_getpid_ns_per_call(10_000);
        assert!(ns.is_finite(), "nanoseconds per call must be finite");
        assert!(ns > 0.0, "a syscall cannot cost zero time");
        // On any real kernel this is microseconds or tens/hundreds of ns, not
        // seconds per call.
        assert!(
            ns < 1_000_000.0,
            "suspiciously slow syscall measurement: {ns} ns"
        );
    }

    #[test]
    fn getpid_returns_nonzero_pid() {
        // SAFETY: read-only syscall, no pointers, no side effects.
        let pid = unsafe { libc::getpid() };
        assert!(pid > 0);
    }
}
