//! Measures signal handling from outside a process. It starts shell scripts
//! that set signal dispositions, sends them signals, and reads their signal
//! masks from `/proc/<pid>/status`.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p sigfacts
//! ```

// ANCHOR: imports
use std::fs;
use std::io::{self, Read};
use std::os::unix::process::ExitStatusExt;
use std::process::{Child, Command, Stdio};
use std::thread;
use std::time::Duration;

use nix::sys::signal::{Signal, kill};
use nix::unistd::Pid;
// ANCHOR_END: imports

// ANCHOR: proc
/// Returns one of the signal masks in `/proc/<pid>/status`: `ShdPnd`
/// (pending), `SigBlk` (blocked), `SigIgn` (ignored) or `SigCgt` (caught).
fn mask(pid: Pid, name: &str) -> io::Result<u64> {
    let status = fs::read_to_string(format!("/proc/{pid}/status"))?;

    status
        .lines()
        .find_map(|line| line.strip_prefix(name)?.strip_prefix(':'))
        .and_then(|value| u64::from_str_radix(value.trim(), 16).ok())
        .ok_or_else(|| io::ErrorKind::InvalidData.into())
}

/// Reports whether a mask contains a signal. Signal `n` is bit `n - 1`.
fn has(mask: u64, signal: Signal) -> bool {
    mask & (1 << (signal as i32 - 1)) != 0
}

/// Polls `/proc/<pid>/stat` until the process has the given command name and
/// state. State `T` is "stopped" and `S` is "sleeping".
fn wait_for(pid: Pid, command: &str, state: char) -> io::Result<()> {
    let want = format!("({command}) {state}");

    while !fs::read_to_string(format!("/proc/{pid}/stat"))?.contains(&want) {
        thread::sleep(Duration::from_millis(1));
    }

    Ok(())
}

/// Starts a shell script and returns the child with its process number.
fn shell(script: &str, stdout: Stdio) -> io::Result<(Child, Pid)> {
    let child = Command::new("sh")
        .args(["-c", script])
        .stdout(stdout)
        .spawn()?;
    let pid = Pid::from_raw(child.id() as i32);

    Ok((child, pid))
}
// ANCHOR_END: proc

// ANCHOR: pending
/// Sends `SIGUSR1` 3 times to a stopped process that has a handler for it,
/// reads the pending mask, and counts how often the handler runs after the
/// process continues.
fn pending() -> io::Result<()> {
    let script = "trap 'echo caught' USR1; kill -STOP $$; echo done";
    let (mut child, pid) = shell(script, Stdio::piped())?;

    wait_for(pid, "sh", 'T')?;

    for _ in 0..3 {
        kill(pid, Signal::SIGUSR1)?;
    }

    let waiting = mask(pid, "ShdPnd")?;

    kill(pid, Signal::SIGCONT)?;

    let mut text = String::new();

    if let Some(stdout) = child.stdout.as_mut() {
        stdout.read_to_string(&mut text)?;
    }

    child.wait()?;

    println!("SIGUSR1 sent 3 times to a stopped process: pending mask {waiting:#x}");
    println!(
        "after SIGCONT the handler ran {} time(s)",
        text.matches("caught").count()
    );

    Ok(())
}
// ANCHOR_END: pending

// ANCHOR: dispositions
/// Reads the ignored and caught masks of a shell that ignores `SIGINT` and
/// handles `SIGUSR1`.
fn dispositions() -> io::Result<()> {
    let script = "trap '' INT; trap 'echo caught' USR1; kill -STOP $$";
    let (mut child, pid) = shell(script, Stdio::inherit())?;

    wait_for(pid, "sh", 'T')?;

    let ignored = mask(pid, "SigIgn")?;
    let caught = mask(pid, "SigCgt")?;

    child.kill()?;
    child.wait()?;

    println!(
        "shell with 2 traps: SIGINT ignored {}, SIGUSR1 caught {}, SIGTERM ignored {}",
        has(ignored, Signal::SIGINT),
        has(caught, Signal::SIGUSR1),
        has(ignored, Signal::SIGTERM)
    );

    Ok(())
}
// ANCHOR_END: dispositions

// ANCHOR: exec
/// Reads the masks of a process after exec, sends it a signal it ignores, and
/// then `SIGKILL`.
fn across_exec() -> io::Result<()> {
    let script = "trap '' TERM; trap 'echo caught' USR1; exec sleep 30";
    let (mut child, pid) = shell(script, Stdio::inherit())?;

    wait_for(pid, "sleep", 'S')?;

    let ignored = mask(pid, "SigIgn")?;
    let caught = mask(pid, "SigCgt")?;

    println!(
        "after exec: SIGTERM ignored {}, SIGUSR1 caught {}",
        has(ignored, Signal::SIGTERM),
        has(caught, Signal::SIGUSR1)
    );

    kill(pid, Signal::SIGTERM)?;
    kill(pid, Signal::SIGKILL)?;

    if let Some(signal) = child.wait()?.signal() {
        println!("SIGTERM, then SIGKILL: killed by signal {signal}");
    }

    Ok(())
}
// ANCHOR_END: exec

fn main() -> io::Result<()> {
    pending()?;
    dispositions()?;
    across_exec()
}
