//! Measures the life cycle of a process: who its parent is, how its
//! termination is reported, what exec keeps, what remains of a child that has
//! exited and has not been waited for, and who becomes the parent of an
//! orphan.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p procfacts
//! ```

// ANCHOR: imports
use std::fs;
use std::io;
use std::os::unix::process::ExitStatusExt;
use std::path::Path;
use std::process::{self, Command};
use std::thread;
use std::time::Duration;

use nix::sys::signal::{Signal, kill};
use nix::unistd::Pid;
// ANCHOR_END: imports

// ANCHOR: proc
/// Returns one field of `/proc/<pid>/stat`, counted from 1. The second field,
/// the command name, is in parentheses and may contain spaces, so the fields
/// after it are counted from the closing parenthesis.
fn field(pid: u32, n: usize) -> io::Result<String> {
    let stat = fs::read_to_string(format!("/proc/{pid}/stat"))?;
    let rest = stat.rsplit_once(')').map_or("", |(_, rest)| rest);

    rest.split_whitespace()
        .nth(n - 3)
        .map(str::to_owned)
        .ok_or_else(|| io::ErrorKind::InvalidData.into())
}

/// Runs a shell command and returns what it printed, without the final
/// newline.
fn output(script: &str) -> io::Result<String> {
    let output = Command::new("sh").args(["-c", script]).output()?;

    Ok(String::from_utf8_lossy(&output.stdout).trim().to_owned())
}
// ANCHOR_END: proc

// ANCHOR: parent
/// Asks a child for the number of its parent process.
fn parent() -> io::Result<()> {
    let text = output("echo $PPID")?;

    println!(
        "the child's parent is this process: {}",
        text == process::id().to_string()
    );

    Ok(())
}
// ANCHOR_END: parent

// ANCHOR: status
/// Runs a script and reports how it terminated.
fn status(script: &str) -> io::Result<()> {
    let status = Command::new("sh").args(["-c", script]).status()?;

    match (status.signal(), status.code()) {
        (Some(signal), _) => println!("{script}: killed by signal {signal}"),
        (None, Some(code)) => println!("{script}: exited with status {code}"),
        (None, None) => println!("{script}: {status}"),
    }

    Ok(())
}
// ANCHOR_END: status

// ANCHOR: exec
/// Prints the process number of a shell before and after the shell replaces
/// its program with exec.
fn exec_keeps_pid() -> io::Result<()> {
    let text = output("echo $$; exec sh -c 'echo $$'")?;
    let pids: Vec<&str> = text.split_whitespace().collect();

    println!(
        "pid before and after exec: equal {}",
        pids.len() == 2 && pids[0] == pids[1]
    );

    Ok(())
}
// ANCHOR_END: exec

// ANCHOR: zombie
/// Starts a child that exits at once, and reads its state before and after
/// waiting for it.
fn zombie() -> io::Result<()> {
    let mut child = Command::new("true").spawn()?;
    let pid = child.id();

    let mut state = field(pid, 3)?;

    while state != "Z" {
        thread::sleep(Duration::from_millis(1));
        state = field(pid, 3)?;
    }

    child.wait()?;

    let present = Path::new(&format!("/proc/{pid}")).exists();
    println!("exited child: state {state} before wait, /proc entry present after wait: {present}");

    Ok(())
}
// ANCHOR_END: zombie

// ANCHOR: orphan
/// Starts a shell that starts a background sleep and exits. The sleep
/// outlives its parent, and the kernel gives it a new one.
fn orphan() -> io::Result<()> {
    let text = output("sleep 30 >/dev/null 2>&1 & echo $!")?;

    let pid: u32 = text
        .parse()
        .map_err(|_| io::Error::from(io::ErrorKind::InvalidData))?;

    let adopter = field(pid, 4);
    kill(Pid::from_raw(pid as i32), Signal::SIGKILL)?;

    let name = fs::read_to_string(format!("/proc/{}/comm", adopter?))?;
    println!("orphan adopted by: {}", name.trim());

    Ok(())
}
// ANCHOR_END: orphan

fn main() -> io::Result<()> {
    parent()?;
    status("exit 7")?;
    status("exit 300")?;
    status("kill -TERM $$")?;
    exec_keeps_pid()?;
    zombie()?;
    orphan()
}
