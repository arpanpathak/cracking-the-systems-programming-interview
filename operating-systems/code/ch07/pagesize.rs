// ch07/pagesize.rs: page size and page alignment through Rust's libc bindings.
use std::process::exit;
use std::ptr;

fn main() {
    let ps = unsafe {
        // SAFETY: `_SC_PAGESIZE` is a POSIX-standard sysconf parameter with no memory
        // preconditions. It queries the architectural hardware translation granularity
        // established by the CPU MMU (typically 4096 bytes on x86_64, 16384 on Apple Silicon).
        libc::sysconf(libc::_SC_PAGESIZE) as usize
    };
    println!("page size: {ps} bytes");

    let region = unsafe {
        // SAFETY: Anonymous, private mapping (`MAP_ANON | MAP_PRIVATE`) with a null hint
        // requests the kernel to allocate an arbitrary, unmapped region in the process's
        // address space. The requested length `3 * ps` is an exact multiple of the page size,
        // ensuring clean page-boundary alignment by construction. The descriptor is -1 and
        // offset is 0 per POSIX specifications for anonymous allocations.
        libc::mmap(
            ptr::null_mut(),
            3 * ps,
            libc::PROT_READ | libc::PROT_WRITE,
            libc::MAP_PRIVATE | libc::MAP_ANON,
            -1,
            0,
        )
    };
    if region == libc::MAP_FAILED {
        eprintln!("mmap failed");
        exit(1);
    }

    println!("region:    {region:p} (page-aligned by construction)");

    unsafe {
        // SAFETY:
        // 1. Validity: `region` was verified != MAP_FAILED, guaranteeing a valid 3-page
        //    contiguous virtual address reservation in the page table.
        // 2. Alignment: Offsets 0, `ps`, and `2 * ps` are exact multiples of the hardware page
        //    granularity. Because `region` is page-aligned, each offset addresses the base of a distinct page.
        // 3. Protection: The mapping was created with `PROT_READ | PROT_WRITE`. Writing here triggers
        //    a minor page fault on each page, prompting the kernel to allocate a physical frame
        //    and install the PTE with dirty and accessed bits set.
        ptr::write(region.cast::<u8>(), b'a');
        ptr::write(region.cast::<u8>().add(ps), b'b');
        ptr::write(region.cast::<u8>().add(2 * ps), b'c');

        // Turn the middle page into a guard page: any access faults.
        // SAFETY: `mprotect` requires a page-aligned address and valid length.
        // `region.add(ps)` points exactly to the second page boundary, and `ps` spans
        // precisely one page. Stripping permissions (`PROT_NONE`) modifies the PTE
        // protection bits, causing any subsequent load/store to that 4 KiB/16 KiB range
        // to immediately trigger an unrecoverable hardware trap (SIGSEGV / EXC_BAD_ACCESS).
        let rc = libc::mprotect(
            region.cast::<u8>().add(ps) as *mut libc::c_void,
            ps,
            libc::PROT_NONE,
        );
        println!("mprotect(middle page, PROT_NONE): rc={rc}");

        // SAFETY: `munmap` releases the virtual memory range back to the OS. `region` is the exact
        // base pointer returned by `mmap`, and `3 * ps` is the exact mapped size. No subsequent
        // references to this virtual address range occur.
        libc::munmap(region, 3 * ps);
    }
}
