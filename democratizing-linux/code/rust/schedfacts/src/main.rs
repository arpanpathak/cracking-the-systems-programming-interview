//! Measures how the scheduler divides a CPU between busy processes of
//! different nice values. It starts the processes on the same CPU, lets them
//! compete, and reads the CPU time each one received.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p schedfacts
//! ```

// ANCHOR: imports
use std::fs;
use std::io;
use std::process::{Child, Command};
use std::thread;
use std::time::Duration;
// ANCHOR_END: imports

// ANCHOR: spin
/// Starts a busy shell loop, restricted to CPU 0 and with the
/// given nice value.
fn spin(nice: i32) -> io::Result<Child> {
    Command::new("taskset")
        .args(["-c", "0", "nice", "-n", &nice.to_string()])
        .args(["sh", "-c", "while :; do :; done"])
        .spawn()
}

/// Returns the CPU time a process has used, in clock ticks: fields 14 and 15
/// of `/proc/<pid>/stat`, the time in user mode and in kernel mode.
fn cpu_time(pid: u32) -> io::Result<u64> {
    let stat = fs::read_to_string(format!("/proc/{pid}/stat"))?;
    let rest = stat.rsplit_once(')').map_or("", |(_, rest)| rest);

    let ticks: Vec<u64> = rest
        .split_whitespace()
        .skip(11)
        .take(2)
        .filter_map(|field| field.parse().ok())
        .collect();

    match ticks.as_slice() {
        [user, kernel] => Ok(user + kernel),
        _ => Err(io::ErrorKind::InvalidData.into()),
    }
}
// ANCHOR_END: spin

// ANCHOR: share
/// Ends a busy process and collects it.
fn stop(mut child: Child) -> io::Result<()> {
    child.kill()?;
    child.wait()?;

    Ok(())
}

/// Lets a process of nice 0 and a process of the given nice value compete for
/// CPU 0 for 2 seconds and prints the share of CPU time each received,
/// rounded to the nearest 5%.
fn share(nice: i32) -> io::Result<()> {
    let first = spin(0)?;
    let second = spin(nice)?;

    thread::sleep(Duration::from_secs(2));

    let times = cpu_time(first.id()).and_then(|a| Ok((a, cpu_time(second.id())?)));

    stop(first)?;
    stop(second)?;

    let (a, b) = times?;
    let percent = (200 * a / (a + b) + 5) / 10 * 5;

    println!(
        "nice 0 and nice {nice} on 1 CPU: {percent}% and {}%",
        100 - percent
    );

    Ok(())
}
// ANCHOR_END: share

fn main() -> io::Result<()> {
    for nice in [0, 5, 10] {
        share(nice)?;
    }

    Ok(())
}
