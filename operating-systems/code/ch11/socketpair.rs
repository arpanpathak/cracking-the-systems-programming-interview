// ch11/socketpair.rs: a socketpair: one bidirectional channel, two directions.
extern crate libc;

use std::io::{self, Write};
use std::ptr;

fn main() {
    let mut sv = [0 as libc::c_int; 2];
    // SAFETY: `sv` is a valid 2-element `c_int` array populated by `socketpair`.
    let rc = unsafe { libc::socketpair(libc::AF_UNIX, libc::SOCK_STREAM, 0, sv.as_mut_ptr()) };
    assert_eq!(rc, 0, "socketpair failed");

    let _ = io::stdout().flush();
    // SAFETY: Stdio is flushed prior to `fork()`.
    let pid = unsafe { libc::fork() };
    assert!(pid >= 0, "fork failed");

    if pid == 0 {
        // SAFETY: Child closes parent descriptor `sv[0]`, exchanges messages on `sv[1]`,
        // flushes output, and terminates via `_exit(0)`.
        unsafe {
            libc::close(sv[0]);
            let msg = b"ping from child";
            libc::write(sv[1], msg.as_ptr() as *const libc::c_void, msg.len());

            let mut buf = [0_u8; 64];
            let n = libc::read(sv[1], buf.as_mut_ptr() as *mut libc::c_void, buf.len() - 1);
            let text = std::str::from_utf8(&buf[..n.max(0) as usize]).unwrap_or("");
            println!("child  received: \"{text}\"");
            let _ = io::stdout().flush();
            libc::close(sv[1]);
            libc::_exit(0);
        }
    }

    // SAFETY: Parent closes child descriptor `sv[1]`, reads request from `sv[0]`,
    // writes reply, and reaps the child process.
    unsafe {
        libc::close(sv[1]);
        let mut buf = [0_u8; 64];
        let n = libc::read(sv[0], buf.as_mut_ptr() as *mut libc::c_void, buf.len() - 1);
        let text = std::str::from_utf8(&buf[..n.max(0) as usize]).unwrap_or("");
        println!("parent received: \"{text}\"");

        let reply = b"pong from parent";
        libc::write(sv[0], reply.as_ptr() as *const libc::c_void, reply.len());
        libc::close(sv[0]);
        libc::waitpid(pid, ptr::null_mut(), 0);
    }
}
