//! The file descriptor table: how a process numbers its open files, what a
//! child inherits across `fork` and `exec`, and how a shell joins two programs
//! with a pipe.
//!
//! Run with: cargo run --bin fd_table

use std::{
    ffi::CString,
    fs::{self, File},
    io::{self, Read, Write},
    os::fd::{AsRawFd, FromRawFd, OwnedFd, RawFd},
    path::Path,
    thread,
    time::Duration,
};

/// The descriptors open in this process, read from `/dev/fd`.
///
/// Reading the directory opens one more descriptor, which is in the list.
fn open_fds() -> io::Result<Vec<RawFd>> {
    let mut fds: Vec<RawFd> = fs::read_dir("/dev/fd")?
        .filter_map(Result::ok)
        .filter_map(|entry| entry.file_name().to_str()?.parse().ok())
        .collect();
    fds.sort_unstable();
    Ok(fds)
}

/// Turn a C return value into an `io::Result`: -1 means `errno` holds the error.
fn check(result: libc::c_int) -> io::Result<libc::c_int> {
    if result == -1 {
        Err(io::Error::last_os_error())
    } else {
        Ok(result)
    }
}

/// Set close-on-exec on `fd`, so a program started with `exec` does not get it.
fn set_cloexec(fd: RawFd) -> io::Result<()> {
    // SAFETY: F_SETFD changes only the descriptor's flags.
    check(unsafe { libc::fcntl(fd, libc::F_SETFD, libc::FD_CLOEXEC) })?;
    Ok(())
}

/// A pipe as (read end, write end). Both ends are close-on-exec.
fn pipe() -> io::Result<(OwnedFd, OwnedFd)> {
    let mut ends = [0; 2];
    // SAFETY: `pipe` writes two new descriptors into the array.
    check(unsafe { libc::pipe(ends.as_mut_ptr()) })?;
    // SAFETY: both descriptors were just created, and nothing else owns them.
    let (read_end, write_end) =
        unsafe { (OwnedFd::from_raw_fd(ends[0]), OwnedFd::from_raw_fd(ends[1])) };
    set_cloexec(read_end.as_raw_fd())?;
    set_cloexec(write_end.as_raw_fd())?;
    Ok((read_end, write_end))
}

/// A copy of `file`'s descriptor, numbered 100 or above, with or without
/// close-on-exec.
fn duplicate(file: &File, cloexec: bool) -> io::Result<OwnedFd> {
    let command = if cloexec {
        libc::F_DUPFD_CLOEXEC
    } else {
        libc::F_DUPFD
    };
    // SAFETY: F_DUPFD and F_DUPFD_CLOEXEC create a new descriptor and nothing else.
    let fd = check(unsafe { libc::fcntl(file.as_raw_fd(), command, 100) })?;
    // SAFETY: `fcntl` just created this descriptor, and nothing else owns it.
    Ok(unsafe { OwnedFd::from_raw_fd(fd) })
}

/// A program name and its arguments, as C strings.
struct Program(Vec<CString>);

impl Program {
    fn new(args: &[&str]) -> Self {
        Self(
            args.iter()
                .map(|arg| CString::new(*arg).expect("no NUL byte in an argument"))
                .collect(),
        )
    }

    /// The null-terminated pointer array `execvp` takes. It borrows `self`.
    fn argv(&self) -> Vec<*const libc::c_char> {
        self.0
            .iter()
            .map(|arg| arg.as_ptr())
            .chain(std::iter::once(std::ptr::null()))
            .collect()
    }
}

/// Start `program` in a child process. `stdin` and `stdout`, when given,
/// become the child's descriptors 0 and 1. Returns the child's process id.
fn spawn(
    program: &Program,
    stdin: Option<RawFd>,
    stdout: Option<RawFd>,
) -> io::Result<libc::pid_t> {
    // Allocate before `fork`: the child may only make async-signal-safe calls.
    let argv = program.argv();

    // SAFETY: the child below calls only dup2, execvp, and _exit.
    let pid = check(unsafe { libc::fork() })?;
    if pid > 0 {
        return Ok(pid);
    }

    // SAFETY: this is the child, a copy of the parent with one thread. dup2 copies
    // a descriptor without its close-on-exec flag; execvp replaces the program.
    unsafe {
        if let Some(fd) = stdin {
            libc::dup2(fd, 0);
        }
        if let Some(fd) = stdout {
            libc::dup2(fd, 1);
        }
        libc::execvp(argv[0], argv.as_ptr());
        libc::_exit(127)
    }
}

/// Wait for the child `pid` to exit, and return its exit status.
fn wait(pid: libc::pid_t) -> io::Result<i32> {
    let mut status = 0;
    // SAFETY: `waitpid` writes the status into the integer it is given.
    check(unsafe { libc::waitpid(pid, &mut status, 0) })?;
    Ok(libc::WEXITSTATUS(status))
}

/// Whether the child `pid` has exited, without waiting for it.
fn has_exited(pid: libc::pid_t) -> io::Result<bool> {
    let mut status = 0;
    // SAFETY: as in `wait`; WNOHANG returns 0 at once if the child is running.
    let result = check(unsafe { libc::waitpid(pid, &mut status, libc::WNOHANG) })?;
    Ok(result == pid)
}

/// Run `program` with its standard output on a pipe, and return what it wrote.
fn output(program: &Program) -> io::Result<String> {
    let (read_end, write_end) = pipe()?;
    let child = spawn(program, None, Some(write_end.as_raw_fd()))?;
    drop(write_end);

    let mut text = String::new();
    File::from(read_end).read_to_string(&mut text)?;
    wait(child)?;
    Ok(text)
}

/// `ls dir | wc -l`, built the way a shell builds it. `wc` writes to this
/// process's standard output.
fn ls_wc(dir: &Path) -> io::Result<()> {
    let ls = Program::new(&["ls", dir.to_str().expect("UTF-8 path")]);
    let wc = Program::new(&["wc", "-l"]);

    let (read_end, write_end) = pipe()?;
    let writer = spawn(&ls, None, Some(write_end.as_raw_fd()))?;
    let reader = spawn(&wc, Some(read_end.as_raw_fd()), None)?;
    drop(read_end);
    drop(write_end);

    wait(writer)?;
    wait(reader)?;
    Ok(())
}

/// Start `wc -l` on a pipe, write two lines into it, and keep the write end
/// open for `hold`. Returns whether `wc` was still running when `hold` ended.
fn reader_waits_for_the_write_end(hold: Duration) -> io::Result<bool> {
    let wc = Program::new(&["wc", "-l"]);
    let (read_end, write_end) = pipe()?;
    let reader = spawn(&wc, Some(read_end.as_raw_fd()), None)?;
    drop(read_end);

    let mut writer = File::from(write_end);
    writer.write_all(b"one\ntwo\n")?;
    thread::sleep(hold);
    let still_running = !has_exited(reader)?;

    drop(writer);
    wait(reader)?;
    Ok(still_running)
}

/// Whether a child started with `exec` has descriptor `fd` open.
fn child_has(fd: &OwnedFd) -> io::Result<bool> {
    let listing = output(&Program::new(&["ls", "/dev/fd"]))?;
    let number = fd.as_raw_fd().to_string();
    Ok(listing
        .split_whitespace()
        .any(|name| name == number))
}

fn main() -> io::Result<()> {
    let dir = std::env::temp_dir().join("fd_table_demo");
    fs::create_dir_all(&dir)?;
    for name in ["a.txt", "b.txt", "c.txt"] {
        fs::write(dir.join(name), name)?;
    }
    let path = dir.join("a.txt");

    println!("open at start: {:?}", open_fds()?);
    let first = File::open(&path)?;
    let second = File::open(&path)?;
    println!(
        "opened two files: fd {} and fd {}",
        first.as_raw_fd(),
        second.as_raw_fd()
    );
    let freed = first.as_raw_fd();
    drop(first);
    let third = File::open(&path)?;
    println!(
        "closed fd {freed}, opened another: fd {}\n",
        third.as_raw_fd()
    );

    println!("ls fd_table_demo | wc -l");
    ls_wc(&dir)?;

    println!("\nparent writes two lines to wc -l and holds the write end for 1 s:");
    let still_running = reader_waits_for_the_write_end(Duration::from_secs(1))?;
    println!("wc still running after 1 s: {still_running}\n");

    let leaked = duplicate(&third, false)?;
    let kept = duplicate(&third, true)?;
    println!(
        "fd {} without close-on-exec, open in the child: {}",
        leaked.as_raw_fd(),
        child_has(&leaked)?
    );
    println!(
        "fd {} with close-on-exec,    open in the child: {}",
        kept.as_raw_fd(),
        child_has(&kept)?
    );

    fs::remove_dir_all(&dir)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_child_writes_through_a_pipe() {
        let text = output(&Program::new(&["echo", "through the pipe"])).expect("run echo");
        assert_eq!(text, "through the pipe\n");
    }

    #[test]
    fn close_on_exec_decides_what_a_child_inherits() {
        let file = File::open("/dev/null").expect("open /dev/null");
        let leaked = duplicate(&file, false).expect("dup");
        let kept = duplicate(&file, true).expect("dup");
        assert!(child_has(&leaked).expect("ls"));
        assert!(!child_has(&kept).expect("ls"));
    }

    #[test]
    fn a_reader_waits_while_any_write_end_is_open() {
        let still_running = reader_waits_for_the_write_end(Duration::from_millis(200)).expect("wc");
        assert!(still_running);
    }
}
