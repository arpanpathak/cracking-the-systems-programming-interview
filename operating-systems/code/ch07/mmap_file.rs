// ch07/mmap_file.rs: Compares counting bytes via read(2) (kernel-to-user copy)
// against reading directly through an mmap(2) virtual memory mapping.
extern crate libc;

use std::ptr;
use std::slice;

const FILE_BYTES: usize = 4 * 1024 * 1024;  // 4 MiB test file
const LINE_BYTES: usize = 64;               // 63 'a' characters + '\n'

fn main() {
    let file_path = b"/tmp/osbook_mmap_demo_rs.txt\0";

    // SAFETY: `file_path` is a NUL-terminated path; mode 0o644 creates a readable/writable file.
    let file_fd = unsafe {
        libc::open(
            file_path.as_ptr() as *const libc::c_char,
            libc::O_CREAT | libc::O_RDWR | libc::O_TRUNC,
            0o644 as libc::c_uint,
        )
    };
    assert!(file_fd >= 0, "open failed");

    let mut line_buffer = [b'a'; LINE_BYTES];
    line_buffer[LINE_BYTES - 1] = b'\n';

    for _ in (0..FILE_BYTES).step_by(LINE_BYTES) {
        // SAFETY: `file_fd` is open for writing and `line_buffer` provides `LINE_BYTES` valid bytes.
        let bytes_written = unsafe {
            libc::write(file_fd, line_buffer.as_ptr() as *const libc::c_void, LINE_BYTES)
        };
        assert_eq!(bytes_written, LINE_BYTES as isize);
    }

    // SAFETY: `file_fd` is an open file descriptor; sync data and rewind offset to byte 0.
    unsafe {
        libc::fsync(file_fd);
        libc::lseek(file_fd, 0, libc::SEEK_SET);
    }

    // Step 2: Count 'a' bytes via read(2) (copies from kernel page cache into user buffer).
    let mut count_via_read: usize = 0;
    let mut read_buffer = [0_u8; 8192];
    loop {
        // SAFETY: `file_fd` is readable and `read_buffer` provides 8,192 writable bytes.
        let bytes_read = unsafe {
            libc::read(
                file_fd,
                read_buffer.as_mut_ptr() as *mut libc::c_void,
                read_buffer.len(),
            )
        };
        if bytes_read <= 0 {
            break;
        }
        count_via_read += read_buffer[..bytes_read as usize]
            .iter()
            .filter(|&&byte| byte == b'a')
            .count();
    }

    // Step 3: Map the file directly into virtual memory (no explicit user-buffer copy).
    // SAFETY: Read-only private mapping of `FILE_BYTES` backed by `file_fd`.
    let mapped_ptr = unsafe {
        libc::mmap(
            ptr::null_mut(),
            FILE_BYTES,
            libc::PROT_READ,
            libc::MAP_PRIVATE,
            file_fd,
            0,
        )
    };
    assert_ne!(mapped_ptr, libc::MAP_FAILED, "mmap failed");

    // SAFETY: `mapped_ptr` is verified valid and remains read-only and mapped until `munmap`.
    let mapped_slice = unsafe { slice::from_raw_parts(mapped_ptr as *const u8, FILE_BYTES) };
    let count_via_mmap = mapped_slice.iter().filter(|&&byte| byte == b'a').count();

    println!("file size   : {FILE_BYTES} bytes");
    println!("read(2)     : {count_via_read} 'a' characters");
    println!("mmap        : {count_via_mmap} 'a' characters");
    println!(
        "match       : {}",
        if count_via_read == count_via_mmap { "yes" } else { "NO" }
    );

    // SAFETY: Unmaps the exact mapping, closes `file_fd`, and removes the temporary file.
    unsafe {
        libc::munmap(mapped_ptr, FILE_BYTES);
        libc::close(file_fd);
        libc::unlink(file_path.as_ptr() as *const libc::c_char);
    }
}
