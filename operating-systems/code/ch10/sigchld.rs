// ch10/sigchld.rs: reaping by hand versus reaping by a SIGCHLD handler.
extern crate libc;

use std::io::{self, Write};
use std::mem::MaybeUninit;
use std::ptr;

extern "C" fn on_sigchld(_sig: libc::c_int) {
    let mut status: libc::c_int = 0;
    // SAFETY: `waitpid` with `WNOHANG` is async-signal-safe per POSIX.1-2008.
    while unsafe { libc::waitpid(-1, &mut status, libc::WNOHANG) } > 0 {}
}

fn main() {
    let _ = io::stdout().flush();
    // SAFETY: Flushing stdio before `fork()` avoids duplicate user-space buffer flushes.
    let c1 = unsafe { libc::fork() };
    assert!(c1 >= 0, "fork failed");

    if c1 == 0 {
        // SAFETY: `getpid()` and `_exit(0)` are safe in the child process.
        unsafe {
            println!("child {}: exiting", libc::getpid());
            let _ = io::stdout().flush();
            libc::_exit(0);
        }
    }

    // SAFETY: `sleep` and `waitpid` synchronize with child `c1`.
    unsafe {
        libc::sleep(1);
        let mut status: libc::c_int = 0;
        let reaped = libc::waitpid(c1, &mut status, 0);
        let code = (status >> 8) & 0xff;
        println!("parent reaped child {reaped} by hand, status {code}");
        let _ = io::stdout().flush();
    }

    // Install async-signal-safe SIGCHLD handler.
    // SAFETY: `sigaction` struct is zero-initialized and populated with a valid
    // `extern "C"` handler function pointer and empty signal mask.
    unsafe {
        let mut sa = MaybeUninit::<libc::sigaction>::zeroed().assume_init();
        sa.sa_sigaction = on_sigchld as *const () as usize;
        libc::sigemptyset(&mut sa.sa_mask);
        sa.sa_flags = libc::SA_RESTART;
        libc::sigaction(libc::SIGCHLD, &sa, ptr::null_mut());
    }

    // SAFETY: Stdio is flushed; child exits immediately via `_exit(0)`.
    let c2 = unsafe { libc::fork() };
    assert!(c2 >= 0, "fork failed");

    if c2 == 0 {
        // SAFETY: Child prints its PID, flushes stdout, and terminates immediately.
        unsafe {
            println!("child {}: exiting", libc::getpid());
            let _ = io::stdout().flush();
            libc::_exit(0);
        }
    }

    // SAFETY: `sleep(1)` is interrupted/resumed once SIGCHLD arrives; subsequent
    // non-blocking `waitpid` confirms the handler already reaped `c2`.
    unsafe {
        libc::sleep(1);
        let mut status: libc::c_int = 0;
        let r = libc::waitpid(c2, &mut status, libc::WNOHANG);
        println!("after handler: waitpid(WNOHANG) -> {r} (-1 = already reaped)");
    }
}
