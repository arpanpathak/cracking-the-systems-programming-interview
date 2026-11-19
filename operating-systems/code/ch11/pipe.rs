// ch11/pipe.rs: the same pipe between parent and child in Rust.
use std::process::exit;

fn main() {
    let mut fds = [0; 2];
    // SAFETY:
    // 1. `pipe(2)` receives a valid mutable pointer to an array of two `c_int`s.
    // 2. Concurrency Safety: Process is single-threaded at `fork()`, ensuring child inherits
    //    an uncorrupted address space.
    // 3. Pipe Lifecycle Proof: The pipe inode ref-count is incremented upon `fork()`.
    //    The child closes its unused read end (`fds[0]`), while the parent closes its unused write
    //    end (`fds[1]`). When the child terminates, its write end is closed, reducing the writer
    //    ref-count to zero. This allows the parent's `read(2)` to encounter EOF (0 bytes) rather
    //    than hanging forever in an unblocked sleep.
    unsafe {
        if libc::pipe(fds.as_mut_ptr()) != 0 {
            eprintln!("pipe failed");
            exit(1);
        }

        let pid = libc::fork();
        if pid == 0 {
            libc::close(fds[0]);              // child keeps the write end
            let msg = b"hello from child";
            libc::write(fds[1], msg.as_ptr() as *const libc::c_void, msg.len());
            libc::close(fds[1]);
            libc::_exit(0);
        }

        libc::close(fds[1]);                  // parent keeps the read end

        let mut buf = [0u8; 64];
        let n = libc::read(fds[0], buf.as_mut_ptr() as *mut libc::c_void, buf.len() - 1);
        libc::waitpid(pid, std::ptr::null_mut(), 0);

        let s = std::str::from_utf8(&buf[..n as usize]).unwrap();
        println!("parent read {n} bytes: \"{s}\"");
    }
}
