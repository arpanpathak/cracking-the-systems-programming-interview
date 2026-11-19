// ch07/tlb.rs: Measures per-access latency while sweeping the working set upward,
// stepping by one full hardware page per access so latency cliffs reveal TLB capacity.
extern crate libc;

use std::ptr;
use std::slice;
use std::time::Instant;

fn measure_ns_per_access(working_set_bytes: usize, total_accesses: u64) {
    // SAFETY: `_SC_PAGESIZE` queries the read-only OS hardware page granularity.
    let page_size = unsafe { libc::sysconf(libc::_SC_PAGESIZE) } as usize;

    // SAFETY: Anonymous private mapping of `working_set_bytes`; validated against `MAP_FAILED`.
    let region_ptr = unsafe {
        libc::mmap(
            ptr::null_mut(),
            working_set_bytes,
            libc::PROT_READ | libc::PROT_WRITE,
            libc::MAP_PRIVATE | libc::MAP_ANON,
            -1,
            0,
        )
    };
    assert_ne!(region_ptr, libc::MAP_FAILED, "mmap failed");

    // SAFETY: `region_ptr` is an exclusively owned, zero-initialized mapping valid until `munmap`.
    let mapped_bytes =
        unsafe { slice::from_raw_parts_mut(region_ptr as *mut u8, working_set_bytes) };
    let page_count = working_set_bytes / page_size;

    // Pre-fault every page once so page-allocation traps do not distort TLB timings.
    for page_index in 0..page_count {
        mapped_bytes[page_index * page_size] = 1;
    }

    let mut checksum: u64 = 0;
    let mut page_index: usize = 0;
    let start_time = Instant::now();
    for _ in 0..total_accesses {
        checksum += u64::from(mapped_bytes[page_index * page_size]);
        page_index += 1;
        if page_index == page_count {
            page_index = 0;
        }
    }
    let ns_per_access = start_time.elapsed().as_nanos() as f64 / total_accesses as f64;

    println!(
        "  {working_set_bytes:9} bytes  {page_count:7} pages  {ns_per_access:6.1} ns per access  (checksum {checksum})"
    );

    // SAFETY: `mapped_bytes` is no longer referenced; unmaps the exact mapping from `mmap`.
    unsafe {
        libc::munmap(region_ptr, working_set_bytes);
    }
}

fn main() {
    const TOTAL_ACCESSES: u64 = 4_000_000;
    println!("one access per page, {TOTAL_ACCESSES} accesses per working-set size\n");

    for &working_set_bytes in &[
        4 * 1024,
        64 * 1024,
        256 * 1024,
        1 << 20,
        4 << 20,
        16 << 20,
        64 << 20,
        256 << 20,
    ] {
        measure_ns_per_access(working_set_bytes, TOTAL_ACCESSES);
    }
}
