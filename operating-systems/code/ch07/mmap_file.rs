// ch07/mmap_file.rs: read a file with read(2), then map it and read it again.
extern crate libc;

use std::ptr;
use std::slice;

const SIZE: usize = 4 * 1024 * 1024; // 4 MiB
const LINE: usize = 64;              // 63 'a' + newline

fn main() {
    let path = b"/tmp/osbook_mmap_demo_rs.txt\0";

    // SAFETY: `path` is a valid NUL-terminated byte array; opening with O_CREAT
    // passes mode 0o644 and returns a valid descriptor or -1 on error.
    let fd = unsafe {
        libc::open(
            path.as_ptr() as *const libc::c_char,
            libc::O_CREAT | libc::O_RDWR | libc::O_TRUNC,
            0o644 as libc::c_uint,
        )
    };
    assert!(fd >= 0, "open failed");

    let mut line = [b'a'; LINE];
    line[LINE - 1] = b'\n';

    for _ in (0..SIZE).step_by(LINE) {
        // SAFETY: `fd` is an open writable file descriptor and `line` is a valid
        // 64-byte stack buffer for the duration of the `write` system call.
        let written = unsafe { libc::write(fd, line.as_ptr() as *const libc::c_void, LINE) };
        assert_eq!(written, LINE as isize);
    }

    // SAFETY: `fd` is a valid open file descriptor.
    unsafe {
        libc::fsync(fd);
        libc::lseek(fd, 0, libc::SEEK_SET);
    }

    let mut via_read: usize = 0;
    let mut buf = [0_u8; 8192];
    loop {
        // SAFETY: `fd` is readable and `buf` provides 8,192 writable bytes.
        let n = unsafe { libc::read(fd, buf.as_mut_ptr() as *mut libc::c_void, buf.len()) };
        if n <= 0 {
            break;
        }
        via_read += buf[..n as usize].iter().filter(|&&b| b == b'a').count();
    }

    // SAFETY: We request a read-only private mapping of `SIZE` bytes backed by `fd`.
    // Checking against `MAP_FAILED` ensures the returned pointer is valid and mapped.
    let map = unsafe {
        libc::mmap(
            ptr::null_mut(),
            SIZE,
            libc::PROT_READ,
            libc::MAP_PRIVATE,
            fd,
            0,
        )
    };
    assert_ne!(map, libc::MAP_FAILED, "mmap failed");

    // SAFETY: `map` points to a valid read-only page-aligned mapping of `SIZE` bytes
    // that remains immutable and mapped until `munmap` below.
    let mapped_bytes = unsafe { slice::from_raw_parts(map as *const u8, SIZE) };
    let via_mmap = mapped_bytes.iter().filter(|&&b| b == b'a').count();

    println!("file size   : {SIZE} bytes");
    println!("read(2)     : {via_read} 'a' characters");
    println!("mmap        : {via_mmap} 'a' characters");
    println!("match       : {}", if via_read == via_mmap { "yes" } else { "NO" });

    // SAFETY: `map` was returned by `mmap` with length `SIZE`, `fd` is open,
    // and `path` is NUL-terminated.
    unsafe {
        libc::munmap(map, SIZE);
        libc::close(fd);
        libc::unlink(path.as_ptr() as *const libc::c_char);
    }
}
