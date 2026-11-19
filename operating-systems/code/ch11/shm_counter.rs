// ch11/shm_counter.rs: a counter in shared memory, guarded by a
// process-shared mutex. Parent and child each add half a million.
extern crate libc;

use std::mem::{MaybeUninit, size_of};
use std::ptr;

#[repr(C)]
struct Shared {
    mu: libc::pthread_mutex_t,
    counter: u64,
}

fn main() {
    const ITERS: u64 = 500_000;

    // SAFETY: `MAP_SHARED | MAP_ANON` allocates page-aligned shared physical memory
    // inherited across `fork()`. Checked against `MAP_FAILED` before dereferencing.
    let raw = unsafe {
        libc::mmap(
            ptr::null_mut(),
            size_of::<Shared>(),
            libc::PROT_READ | libc::PROT_WRITE,
            libc::MAP_SHARED | libc::MAP_ANON,
            -1,
            0,
        )
    };
    assert_ne!(raw, libc::MAP_FAILED, "mmap failed");
    let s = raw as *mut Shared;

    // SAFETY: `s` points to writable page-aligned memory of at least `size_of::<Shared>()`.
    // Configuring `PTHREAD_PROCESS_SHARED` permits synchronization across forked processes.
    unsafe {
        let mut attr = MaybeUninit::<libc::pthread_mutexattr_t>::zeroed().assume_init();
        libc::pthread_mutexattr_init(&mut attr);
        libc::pthread_mutexattr_setpshared(&mut attr, libc::PTHREAD_PROCESS_SHARED);
        libc::pthread_mutex_init(ptr::addr_of_mut!((*s).mu), &attr);
        libc::pthread_mutexattr_destroy(&mut attr);
        ptr::addr_of_mut!((*s).counter).write(0);
    }

    // SAFETY: Shared mutex and counter are initialized before `fork()`.
    let pid = unsafe { libc::fork() };
    assert!(pid >= 0, "fork failed");

    if pid == 0 {
        // SAFETY: All accesses to `(*s).counter` occur while holding the process-shared
        // pthread mutex `(*s).mu`, preventing data races between parent and child.
        unsafe {
            for _ in 0..ITERS {
                libc::pthread_mutex_lock(ptr::addr_of_mut!((*s).mu));
                let cur = ptr::addr_of!((*s).counter).read();
                ptr::addr_of_mut!((*s).counter).write(cur + 1);
                libc::pthread_mutex_unlock(ptr::addr_of_mut!((*s).mu));
            }
            libc::_exit(0);
        }
    }

    // SAFETY: Parent increments `(*s).counter` under the same process-shared mutex,
    // waits for child termination via `waitpid`, and then cleans up the shared mapping.
    unsafe {
        for _ in 0..ITERS {
            libc::pthread_mutex_lock(ptr::addr_of_mut!((*s).mu));
            let cur = ptr::addr_of!((*s).counter).read();
            ptr::addr_of_mut!((*s).counter).write(cur + 1);
            libc::pthread_mutex_unlock(ptr::addr_of_mut!((*s).mu));
        }
        libc::waitpid(pid, ptr::null_mut(), 0);

        let observed = ptr::addr_of!((*s).counter).read();
        println!("expected {}, observed {observed}", 2 * ITERS);

        libc::pthread_mutex_destroy(ptr::addr_of_mut!((*s).mu));
        libc::munmap(raw, size_of::<Shared>());
    }
}
