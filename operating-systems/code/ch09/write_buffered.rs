// ch09/write_buffered.rs: the same comparison with raw write(2) and BufWriter.
use std::fs::File;
use std::io::{BufWriter, Write};
use std::time::Instant;

const N: usize = 200_000;
const MSG: &[u8] = b"0123456789abcdef\n";   // 17 bytes

fn main() -> std::io::Result<()> {
    // SAFETY: The path string literal is static, null-terminated, and safely cast
    // to a C-compatible pointer. `O_WRONLY` is a valid POSIX file flag.
    let fd = unsafe {
        libc::open(b"/dev/null\0".as_ptr() as *const libc::c_char, libc::O_WRONLY)
    };
    if fd < 0 {
        eprintln!("open failed");
        std::process::exit(1);
    }

    // Unbuffered: one write(2) system call per iteration.
    let t0 = Instant::now();
    for _ in 0..N {
        let mut written = 0usize;
        while written < MSG.len() {
            // SAFETY:
            // 1. `fd` is verified valid and open for writing.
            // 2. `MSG[written..]` references initialized, static read-only memory.
            // 3. Length `MSG.len() - written` accurately describes the remaining slice,
            //    preventing out-of-bounds kernel memory reads.
            let n = unsafe {
                libc::write(
                    fd,
                    MSG[written..].as_ptr() as *const libc::c_void,
                    MSG.len() - written,
                )
            };
            if n <= 0 {
                break;
            }

            written += n as usize;
        }
    }

    let raw_ms = t0.elapsed().as_secs_f64() * 1000.0;

    // Buffered: BufWriter accumulates in a 64 KiB buffer, then flushes once.
    let f = File::create("/dev/null")?;
    let mut w = BufWriter::with_capacity(64 * 1024, f);

    let t1 = Instant::now();
    for _ in 0..N {
        w.write_all(MSG)?;
    }
    w.flush()?;

    let buf_ms = t1.elapsed().as_secs_f64() * 1000.0;

    println!("write(2) into /dev/null, {N} x 17 bytes : {raw_ms:7.1} ms");
    println!("BufWriter,     {N} x 17 bytes         : {buf_ms:7.1} ms");

    // SAFETY: `fd` is a valid open file descriptor returned by `open()`. Closing it releases
    // the kernel file description ref-count and frees the file descriptor table entry.
    unsafe { libc::close(fd) };
    Ok(())
}
