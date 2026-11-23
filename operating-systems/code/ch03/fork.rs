// ch03/fork.rs: the same fork/wait sequence through Rust's libc bindings.
use std::io::{self, Write};
use std::process::exit;

fn main() {
    // SAFETY: POSIX `getpid()` reads the process ID cached or stored in the PCB.
    // It requires no memory pointers and is guaranteed by the kernel never to fail.
    let pid_before = unsafe { libc::getpid() };
    println!("before fork: pid={pid_before}");

    // SAFETY: `fork(2)` duplicates the calling process, cloning page table entries
    // with Copy-On-Write (COW) protections.
    // Crucial Concurrency Invariant: In multi-threaded programs, POSIX `fork()` duplicates
    // only the calling thread, leaving any mutex held by sibling threads permanently locked
    // in the child (causing immediate deadlock on any subsequent malloc or libc lock acquisition).
    // Because this runtime has executed exactly one thread, no internal mutexes are held,
    // ensuring the child enters a completely quiescent, safe address space.
    let pid = unsafe { libc::fork() };
    if pid < 0 {
        eprintln!("fork failed");
        exit(1);
    }

    if pid == 0 {
        // Child: fork() returned 0 here.
        // SAFETY: Direct kernel queries for process identification requiring no memory contracts.
        let me = unsafe { libc::getpid() };
        let parent = unsafe { libc::getppid() };
        println!("child : pid={me} parent={parent}");
        let _ = io::stdout().flush(); // _exit() skips stdio flushing
        // SAFETY: `_exit(2)` immediately terminates execution without running user-space `atexit`
        // handlers or flushing C stdio buffers. This prevents double-flushing data buffers that
        // were duplicated across the fork boundary into the child's address space.
        unsafe { libc::_exit(7) };
    }

    // Parent: fork() returned the child's pid here.
    let mut status: libc::c_int = 0;
    // SAFETY: `status` is a valid, aligned mutable pointer to a stack-allocated integer.
    // Passing our child PID guarantees we wait on an existing direct descendant process.
    let waited = unsafe { libc::waitpid(pid, &mut status, 0) };

    let code = if libc::WIFEXITED(status) {
        libc::WEXITSTATUS(status)
    } else {
        -1
    };

    println!("parent: child {waited} exited with status {code}");
}
