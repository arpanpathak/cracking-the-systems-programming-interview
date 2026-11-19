// ch07/tlb.rs: one access per page, sweeping the working set upward.
extern crate libc;

use std::ptr;
use std::slice;
use std::time::Instant;

fn ns_per_access(bytes: usize, touches: u64) {
    // SAFETY: `sysconf(_SC_PAGESIZE)` queries a read-only kernel constant.
    let ps = unsafe { libc::sysconf(libc::_SC_PAGESIZE) } as usize;

    // SAFETY: Anonymous private mapping of `bytes` length requires no file descriptor.
    // Verified against `MAP_FAILED` before forming a Rust slice.
    let region = unsafe {
        libc::mmap(
            ptr::null_mut(),
            bytes,
            libc::PROT_READ | libc::PROT_WRITE,
            libc::MAP_PRIVATE | libc::MAP_ANON,
            -1,
            0,
        )
    };
    assert_ne!(region, libc::MAP_FAILED, "mmap failed");

    // SAFETY: `region` is a valid, exclusively owned mapping of `bytes` initialized
    // by the kernel to zero; valid until `munmap` at the end of this function.
    let mem = unsafe { slice::from_raw_parts_mut(region as *mut u8, bytes) };
    let pages = bytes / ps;

    // Pre-fault every page so page-allocation traps do not pollute TLB timings.
    for p in 0..pages {
        mem[p * ps] = 1;
    }

    let mut sum: u64 = 0;
    let mut p: usize = 0;
    let start = Instant::now();
    for _ in 0..touches {
        sum += u64::from(mem[p * ps]);
        p += 1;
        if p == pages {
            p = 0;
        }
    }
    let ns = start.elapsed().as_nanos() as f64 / touches as f64;

    println!("  {bytes:8} bytes  {pages:8} pages  {ns:8.1} ns per access  (checksum {sum})");

    // SAFETY: `mem` is no longer referenced; unmaps the exact region returned by `mmap`.
    unsafe {
        libc::munmap(region, bytes);
    }
}

fn main() {
    const TOUCHES: u64 = 4_000_000;
    println!("one access per page, {TOUCHES} accesses per size\n");

    for &bytes in &[
        4 * 1024,
        64 * 1024,
        256 * 1024,
        1 << 20,
        4 << 20,
        16 << 20,
        64 << 20,
        256 << 20,
    ] {
        ns_per_access(bytes, TOUCHES);
    }
}
