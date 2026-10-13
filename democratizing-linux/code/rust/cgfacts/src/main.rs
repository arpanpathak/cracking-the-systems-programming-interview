//! Measures control groups. It creates a group below the one it runs in,
//! starts shell commands inside the new group, and observes the kernel
//! counting their processes, refusing a fork beyond `pids.max`, and ending a
//! process that exceeds `memory.max`.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p cgfacts
//! ```

// ANCHOR: imports
use std::fs;
use std::io;
use std::os::unix::process::ExitStatusExt;
use std::path::{Path, PathBuf};
use std::process::{self, Command};
use std::thread;
use std::time::Duration;
// ANCHOR_END: imports

// ANCHOR: files
/// The directory of a control group under `/sys/fs/cgroup`.
struct Group(PathBuf);

impl Group {
    /// Writes a value to one of the group's control files.
    fn set(&self, file: &str, value: &str) -> io::Result<()> {
        fs::write(self.0.join(file), value)
    }

    /// Reads one of the group's control files.
    fn get(&self, file: &str) -> io::Result<String> {
        Ok(fs::read_to_string(self.0.join(file))?.trim().to_owned())
    }

    /// Returns the counter with the given key from a file of "key value"
    /// lines, such as `pids.events` and `memory.events`.
    fn event(&self, file: &str, key: &str) -> io::Result<String> {
        self.get(file)?
            .lines()
            .filter_map(|line| line.split_once(' '))
            .find(|(name, _)| *name == key)
            .map(|(_, value)| value.to_owned())
            .ok_or_else(|| io::ErrorKind::NotFound.into())
    }
}
// ANCHOR_END: files

// ANCHOR: create
impl Group {
    /// Makes a new group. It goes up from the group of this process to the
    /// nearest group that distributes the memory and pids controllers to its
    /// children, and creates a directory there.
    fn create() -> io::Result<Group> {
        let line = fs::read_to_string("/proc/self/cgroup")?;
        let path = line.trim().split_once("::").map_or("", |(_, path)| path);
        let root = Path::new("/sys/fs/cgroup");
        let own = root.join(path.trim_start_matches('/'));

        for dir in own.ancestors().take_while(|dir| *dir != root) {
            let Ok(enabled) = fs::read_to_string(dir.join("cgroup.subtree_control")) else {
                continue;
            };

            if enabled.contains("memory") && enabled.contains("pids") {
                let created = dir.join(format!("cgfacts-{}", process::id()));

                fs::create_dir(&created)?;

                return Ok(Group(created));
            }
        }

        Err(io::Error::other(
            "no parent group delegates the memory and pids controllers",
        ))
    }

    /// Returns a shell script that will run in the group. The shell first
    /// moves itself into the group by writing its own process number to
    /// `cgroup.procs`, and every process it starts afterwards is created
    /// there.
    fn command(&self, script: &str) -> Command {
        let mut command = Command::new("sh");

        command
            .arg("-c")
            .arg(format!(r#"echo $$ > "$0/cgroup.procs" && {script}"#))
            .arg(&self.0);

        command
    }

    /// Ends every process left in the group, waits until the group is empty,
    /// and deletes it.
    fn remove(&self) -> io::Result<()> {
        self.set("cgroup.kill", "1")?;

        while self.get("pids.current")? != "0" {
            thread::sleep(Duration::from_millis(1));
        }

        fs::remove_dir(&self.0)
    }
}
// ANCHOR_END: create

// ANCHOR: count
/// Starts a process in the group and reads the group's process count.
fn count(group: &Group) -> io::Result<()> {
    let mut child = group.command("exec sleep 30").spawn()?;

    while group.get("pids.current")? != "1" {
        thread::sleep(Duration::from_millis(1));
    }

    child.kill()?;
    child.wait()?;

    println!("a process moved into the new group: pids.current 1");

    Ok(())
}
// ANCHOR_END: count

// ANCHOR: pids
/// Sets `pids.max` to 4 and runs a shell that tries to start 6 background
/// commands and prints a line for each one it started.
fn limit_pids(group: &Group) -> io::Result<()> {
    group.set("pids.max", "4")?;

    let script = "for i in 1 2 3 4 5 6; do sleep 1 & echo started; done 2>/dev/null";
    let output = group.command(script).output()?;
    let started = String::from_utf8_lossy(&output.stdout)
        .matches("started")
        .count();

    println!(
        "pids.max 4, a shell starts background commands: started {started}, forks refused {}",
        group.event("pids.events", "max")?
    );

    group.set("pids.max", "max")
}
// ANCHOR_END: pids

// ANCHOR: memory
/// Sets `memory.max` to 32 MiB with no swap and runs a command whose memory
/// grows without bound.
fn limit_memory(group: &Group) -> io::Result<()> {
    group.set("memory.max", "33554432")?;
    group.set("memory.swap.max", "0")?;

    let status = group.command("exec tail /dev/zero").status()?;
    let kills = group.event("memory.events", "oom_kill")?;

    if let Some(signal) = status.signal() {
        println!(
            "memory.max 32 MiB, a command that grows without bound: killed by signal {signal}, oom_kill {kills}"
        );
    }

    Ok(())
}
// ANCHOR_END: memory

fn main() -> io::Result<()> {
    let group = Group::create()?;

    let result = count(&group)
        .and_then(|()| limit_pids(&group))
        .and_then(|()| limit_memory(&group));

    group.remove()?;

    result
}
