// ch19/mini_pipeline.rs: what a shell does for `echo hello | tr a-z A-Z`.
use std::ffi::CString;
use std::io::Write;

/// Forks a child whose stdin and stdout are replaced by the given descriptors,
/// then replaces the child with `words[0]`. Returns the child's PID to the parent.
fn spawn(
    words: &[&str],
    input_fd: i32,
    output_fd: i32,
    unused_fd: i32,
) -> libc::pid_t {
    let owned: Vec<CString> = words
        .iter()
        .filter_map(|word| CString::new(*word).ok())
        .collect();

    let mut argv: Vec<*const libc::c_char> = owned
        .iter()
        .map(|word| word.as_ptr())
        .collect();

    argv.push(std::ptr::null());

    // SAFETY: Process is single-threaded at `fork()`, ensuring no inherited mutex locks are deadlocked in the child.
    let pid = unsafe { libc::fork() };
    if pid != 0 {
        return pid; // parent, or fork failed (-1)
    }

    // SAFETY: Pipeline Redirection Proof:
    // 1. `dup2` duplicates `input_fd` to STDIN and `output_fd` to STDOUT.
    // 2. Crucial Cleanup Invariant: `input_fd` and `output_fd` are immediately closed once duplicated,
    //    and `unused_fd` (the opposing pipe end) is closed. Failing to close `unused_fd` would leave
    //    an unclosed writer open in the reader child, preventing the reader from ever detecting EOF.
    // 3. `execvp`: `argv[0]` and `argv` are valid, null-terminated arrays of C-strings from `owned`.
    unsafe {
        if input_fd != libc::STDIN_FILENO {
            libc::dup2(input_fd, libc::STDIN_FILENO);
            libc::close(input_fd);
        }
        if output_fd != libc::STDOUT_FILENO {
            libc::dup2(output_fd, libc::STDOUT_FILENO);
            libc::close(output_fd);
        }

        libc::close(unused_fd); // the pipe end this child does not use

        libc::execvp(argv[0], argv.as_ptr());
        libc::_exit(127) // reached only if exec failed
    }
}

fn main() {
    let mut pipe_fds = [0; 2];

    // SAFETY: `pipe_fds` is a stack array with capacity for two `c_int` descriptors.
    if unsafe { libc::pipe(pipe_fds.as_mut_ptr()) } != 0 {
        eprintln!("pipe failed");
        return;
    }

    // Nothing buffered may be copied into the children.
    let flushed = std::io::stdout().flush();

    if flushed.is_err() {
        eprintln!("flush failed");
    }

    let [read_end, write_end] = pipe_fds;

    let writer = spawn(&["echo", "hello"], libc::STDIN_FILENO, write_end, read_end);
    let reader = spawn(&["tr", "a-z", "A-Z"], read_end, libc::STDOUT_FILENO, write_end);

    let mut writer_status = 0;
    let mut reader_status = 0;

    // SAFETY: Parent Pipeline Lifecycle Proof:
    // The parent must close both `read_end` and `write_end` of the pipe. If the parent leaves
    // `write_end` open, the kernel keeps the pipe's writer reference count > 0 even after `echo`
    // exits. Consequently, `tr` would block indefinitely in `read(2)` waiting for more input.
    // Closing both descriptors in the parent allows `tr` to cleanly receive EOF and exit.
    unsafe {
        libc::close(read_end);
        libc::close(write_end);

        libc::waitpid(writer, &mut writer_status, 0);
        libc::waitpid(reader, &mut reader_status, 0);
    }

    println!(
        "echo exited with {}, tr exited with {}",
        libc::WEXITSTATUS(writer_status),
        libc::WEXITSTATUS(reader_status)
    );
}
