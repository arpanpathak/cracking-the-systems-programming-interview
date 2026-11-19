// ch15/daemon.rs: the same lifecycle in Rust: double fork, setsid, pidfile,
// and signal-driven shutdown through libc.
use std::fs::OpenOptions;
use std::io::Write;
use std::sync::atomic::{AtomicBool, Ordering};
use std::thread;
use std::time::Duration;

static RELOAD: AtomicBool = AtomicBool::new(false);
static STOP: AtomicBool = AtomicBool::new(false);

extern "C" fn on_hup(_: libc::c_int) {
    RELOAD.store(true, Ordering::Relaxed);
}

extern "C" fn on_term(_: libc::c_int) {
    STOP.store(true, Ordering::Relaxed);
}

fn main() -> std::io::Result<()> {
    // SAFETY: Classic UNIX Daemonization Invariants:
    // 1. First `fork()`: Creates an asynchronous background child and terminates the parent,
    //    guaranteeing the child is not a process group leader.
    // 2. `setsid()`: Creates a new session and process group with no controlling terminal (tty).
    // 3. Second `fork()`: Exits the session leader, ensuring the grandchild daemon can never
    //    subsequently acquire a controlling terminal, even if it opens a tty device.
    // 4. `umask(0o027)`: Restricts default file creation modes (no permissions for other, no write for group).
    // 5. `chdir("/")`: Unmounts the current working directory, preventing the daemon from pinning a mounted filesystem.
    unsafe {
        let pid = libc::fork();
        if pid < 0 {
            std::process::exit(1);
        }
        if pid > 0 {
            libc::_exit(0);        // first parent exits
        }

        libc::setsid();            // new session: no controlling terminal

        let pid = libc::fork();
        if pid > 0 {
            libc::_exit(0);        // session leader exits; terminal cannot return
        }

        libc::umask(0o027);
        libc::chdir(b"/\0".as_ptr() as *const libc::c_char);
    }

    let pidfile = "/tmp/osbook_daemon_rs.pid";
    let logfile = "/tmp/osbook_daemon_rs.log";

    {
        let mut pf = OpenOptions::new()
            .create(true)
            .write(true)
            .truncate(true)
            .open(pidfile)?;
        writeln!(pf, "{}", std::process::id())?;
    }

    let mut log = OpenOptions::new().create(true).append(true).open(logfile)?;

    // SAFETY: Registers signal handlers `on_hup` and `on_term` which strictly store to `AtomicBool`
    // flags with `Ordering::Relaxed`. Atomic stores compile to single store instructions on x86/ARM,
    // fulfilling the strict POSIX async-signal-safety specification.
    unsafe {
        let mut sa: libc::sigaction = std::mem::zeroed();
        sa.sa_sigaction = on_hup as *const () as usize;
        libc::sigemptyset(&mut sa.sa_mask);
        libc::sigaction(libc::SIGHUP, &sa, std::ptr::null_mut());

        sa.sa_sigaction = on_term as *const () as usize;
        libc::sigaction(libc::SIGTERM, &sa, std::ptr::null_mut());
    }

    writeln!(log, "daemon {} started", std::process::id())?;
    log.flush()?;

    let mut ticks = 0;
    while !STOP.load(Ordering::Relaxed) {
        thread::sleep(Duration::from_secs(1));
        ticks += 1;

        writeln!(log, "tick {ticks}")?;
        log.flush()?;

        if RELOAD.swap(false, Ordering::Relaxed) {
            writeln!(log, "reload requested")?;
            log.flush()?;
        }
    }

    writeln!(log, "stopping after {ticks} ticks")?;
    std::fs::remove_file(pidfile)?;
    Ok(())
}
