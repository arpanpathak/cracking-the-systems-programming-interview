// ch10/signals.rs: the same block-then-deliver sequence in Rust.
use std::sync::atomic::{AtomicBool, Ordering};

static GOT_USR1: AtomicBool = AtomicBool::new(false);
static GOT_INT: AtomicBool = AtomicBool::new(false);

extern "C" fn on_usr1(_: libc::c_int) {
    GOT_USR1.store(true, Ordering::Relaxed);
}

extern "C" fn on_int(_: libc::c_int) {
    GOT_INT.store(true, Ordering::Relaxed);
}

fn main() {
    // SAFETY:
    // 1. Asynchronous Execution Safety: Signal handlers preempt execution on the same thread stack.
    //    Our signal callbacks (`on_usr1`, `on_int`) strictly perform atomic store operations
    //    (`AtomicBool::store`), which compile to lock-free instructions and are POSIX async-signal-safe.
    // 2. Struct Validity: `sa` is zero-initialized and configured with an empty signal mask.
    // 3. Mask Consistency: `sigprocmask` safely alternates the thread's signal disposition
    //    between blocked and unblocked states using valid stack-allocated `sigset_t` bitmasks.
    unsafe {
        let mut sa: libc::sigaction = std::mem::zeroed();
        sa.sa_sigaction = on_usr1 as *const () as usize;
        libc::sigemptyset(&mut sa.sa_mask);
        libc::sigaction(libc::SIGUSR1, &sa, std::ptr::null_mut());

        sa.sa_sigaction = on_int as *const () as usize;
        libc::sigaction(libc::SIGINT, &sa, std::ptr::null_mut());

        // Block SIGUSR1, send it to ourselves, and observe that it stays pending.
        let mut set: libc::sigset_t = std::mem::zeroed();
        let mut oldset: libc::sigset_t = std::mem::zeroed();
        libc::sigemptyset(&mut set);
        libc::sigaddset(&mut set, libc::SIGUSR1);
        libc::sigprocmask(libc::SIG_BLOCK, &set, &mut oldset);

        libc::raise(libc::SIGUSR1);   // queued, not delivered
        println!(
            "after raise while blocked: handled={}",
            GOT_USR1.load(Ordering::Relaxed)
        );

        libc::sigprocmask(libc::SIG_UNBLOCK, &set, std::ptr::null_mut()); // delivery here
        println!("after unblock: handled={}", GOT_USR1.load(Ordering::Relaxed));

        libc::raise(libc::SIGINT);    // delivered immediately
        println!("after SIGINT: handled={}", GOT_INT.load(Ordering::Relaxed));

        libc::sigprocmask(libc::SIG_SETMASK, &oldset, std::ptr::null_mut());
    }
}
