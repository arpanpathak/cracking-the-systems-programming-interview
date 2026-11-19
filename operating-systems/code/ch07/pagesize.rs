// ch07/pagesize.rs: Queries hardware page size, maps three contiguous virtual pages,
// and strips permissions from the middle guard page via mprotect(PROT_NONE).
use std::process::exit;
use std::ptr;

fn main() {
    // SAFETY: `_SC_PAGESIZE` is a read-only POSIX configuration constant returning
    // the CPU MMU's native page granularity (4,096 B on x86-64; 16,384 B on Apple Silicon).
    let page_size = unsafe { libc::sysconf(libc::_SC_PAGESIZE) as usize };
    println!("page size: {page_size} bytes");

    // SAFETY: Anonymous private mapping (`MAP_PRIVATE | MAP_ANON`) of `3 * page_size` bytes.
    // Checking `mapped_region != MAP_FAILED` guarantees a valid page-aligned virtual range.
    let mapped_region = unsafe {
        libc::mmap(
            ptr::null_mut(),
            3 * page_size,
            libc::PROT_READ | libc::PROT_WRITE,
            libc::MAP_PRIVATE | libc::MAP_ANON,
            -1,
            0,
        )
    };
    if mapped_region == libc::MAP_FAILED {
        eprintln!("mmap failed");
        exit(1);
    }

    println!("region:    {mapped_region:p} (page-aligned by construction)");

    unsafe {
        // SAFETY: `mapped_region` spans 3 writable pages starting at a page-aligned address.
        // Writing to offsets 0, `page_size`, and `2 * page_size` touches Page 0, Page 1, and Page 2.
        ptr::write(mapped_region.cast::<u8>(), b'a');
        ptr::write(mapped_region.cast::<u8>().add(page_size), b'b');
        ptr::write(mapped_region.cast::<u8>().add(2 * page_size), b'c');

        // Convert Page 1 (middle page) into a guard page by setting PTE permissions to PROT_NONE.
        // SAFETY: `mapped_region + page_size` is page-aligned and lies strictly within the mapping.
        let mprotect_status = libc::mprotect(
            mapped_region.cast::<u8>().add(page_size) as *mut libc::c_void,
            page_size,
            libc::PROT_NONE,
        );
        println!("mprotect(middle page, PROT_NONE): status={mprotect_status}");

        // SAFETY: Unmaps the exact base address and length returned by `mmap`.
        libc::munmap(mapped_region, 3 * page_size);
    }
}
