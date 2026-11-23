// ch15/kqueue_supervisor.rs: process fault monitoring using kqueue in Rust.
use std::mem;
use std::process::{Command, Stdio};
use std::ptr;

fn main() {
    // SAFETY: Kernel Event Loop Supervision Invariants:
    // 1. Descriptor Allocation: `kqueue()` allocates a kernel event notification queue and returns
    //    a file descriptor into the calling process's file descriptor table. We assert `kq >= 0`
    //    to guarantee descriptor validity before registering filters.
    // 2. Filter Registration (`EVFILT_PROC`): `&change` is a valid, stack-allocated, properly
    //    aligned `libc::kevent` struct referencing the live child `pid` spawned via `Command::spawn()`.
    //    Passing `nchanges = 1` and `nevents = 0` registers the `NOTE_EXIT` kernel hook synchronously
    //    without harvesting events. Because `EVFILT_PROC` attaches directly to the kernel `proc`
    //    structure before or even as the child exits, it avoids the signal-coalescing and
    //    async-signal-safety hazards of `SIGCHLD`.
    // 3. Blocking Event Harvest: `event` is a stack-allocated `libc::kevent` initialized via
    //    `std::mem::zeroed()` (all integer and pointer fields in `kevent` admit zero as a valid
    //    bit representation). Passing `&mut event` with `nevents = 1` and a null timeout pointer
    //    parks the supervisor thread in the kernel wait queue until the child process terminates.
    // 4. Resource Teardown: `child.wait()` reaps the terminated zombie PCB via `waitpid`, and
    //    `libc::close(kq)` releases the kqueue file descriptor back to the kernel.
    unsafe {
        let kq = libc::kqueue();
        assert!(kq >= 0, "failed to create kqueue");

        // Spawn a child process to supervise
        let mut child = Command::new("sleep")
            .arg("0.05")
            .stdout(Stdio::null())
            .spawn()
            .expect("failed to spawn child");

        let pid = child.id() as libc::pid_t;

        // Register EVFILT_PROC to observe process termination
        let change = libc::kevent {
            ident: pid as usize,
            filter: libc::EVFILT_PROC,
            flags: libc::EV_ADD | libc::EV_ENABLE,
            fflags: libc::NOTE_EXIT,
            data: 0,
            udata: ptr::null_mut(),
        };

        let ret = libc::kevent(kq, &change, 1, ptr::null_mut(), 0, ptr::null());
        assert!(ret >= 0, "failed to register kevent");

        // Block on the event queue until the process exits
        let mut event = mem::zeroed();
        let nev = libc::kevent(kq, ptr::null(), 0, &mut event, 1, ptr::null());
        assert!(nev > 0, "kevent wait failed");

        let status = child.wait().expect("failed to wait on child");
        println!("supervisor detected child {} termination, success: {}", pid, status.success());

        libc::close(kq);
    }
}
