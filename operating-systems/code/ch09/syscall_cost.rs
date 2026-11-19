// ch09/syscall_cost.rs: the same comparison in Rust.
use std::hint::black_box;
use std::time::Instant;

#[inline(never)]
fn plain_fn(x: i32) -> i32 {
    x + 1
}

fn main() {
    const N: u64 = 5_000_000;

    // Plain function calls: nothing leaves user mode.
    let mut acc: u64 = 0;
    let t0 = Instant::now();
    for _ in 0..N {
        acc += plain_fn(black_box((acc & 0xff) as i32)) as u64;
    }

    let fn_ns = t0.elapsed().as_nanos() as f64 / N as f64;

    // System calls: each one traps into the kernel and back. We use getppid(),
    // not getpid(): on macOS libc caches getpid() after the first call, so a
    // getpid() loop would measure a library lookup, not a trap.
    let mut ppid: libc::pid_t = 0;
    let t1 = Instant::now();
    for _ in 0..N {
        // SAFETY: POSIX `getppid()` executes a pure user-to-kernel mode switch (ring 3 -> ring 0).
        // It requires no memory pointers and cannot fail or corrupt process state.
        // We measure `getppid()` rather than `getpid()` because modern macOS libSystem caches
        // `getpid()` in user-space TLS after the initial call, which would measure a simple
        // memory load rather than a full CPU hardware trap and context transition.
        ppid = unsafe { libc::getppid() };
    }

    let sys_ns = t1.elapsed().as_nanos() as f64 / N as f64;

    println!("plain function call  : {fn_ns:7.1} ns");
    println!("getppid() system call: {sys_ns:7.1} ns");
    println!("ratio                : {:7.1}x", sys_ns / fn_ns);
    println!("(parent pid {ppid}, checksum {acc})");
}
