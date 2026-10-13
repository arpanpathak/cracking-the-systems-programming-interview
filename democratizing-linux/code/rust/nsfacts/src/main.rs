//! Measures namespaces. It compares the namespaces of a process with those of
//! an ordinary child, and then starts a child in new user, UTS and PID
//! namespaces and reports what that child sees.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p nsfacts
//! ```

// ANCHOR: imports
use std::collections::HashMap;
use std::env;
use std::fs;
use std::io;
use std::process::{self, Command};

use nix::sched::{CloneFlags, unshare};
use nix::unistd::{getgid, gethostname, getpid, getuid, sethostname};
// ANCHOR_END: imports

// ANCHOR: identity
/// The namespace types of Linux 5.15, as named under `/proc/<pid>/ns`.
const KINDS: [&str; 8] = ["cgroup", "ipc", "mnt", "net", "pid", "time", "user", "uts"];

/// Returns the identity of each namespace of a process. The kernel shows it
/// as the target of a symbolic link, such as `uts:[4026531838]`.
/// Processes are in the same namespace when the targets are equal.
fn namespaces(pid: &str) -> io::Result<HashMap<&'static str, String>> {
    KINDS
        .iter()
        .map(|&kind| {
            let id = fs::read_link(format!("/proc/{pid}/ns/{kind}"))?;

            Ok((kind, id.to_string_lossy().into_owned()))
        })
        .collect()
}

fn hostname() -> io::Result<String> {
    Ok(gethostname()?.to_string_lossy().into_owned())
}
// ANCHOR_END: identity

// ANCHOR: inside
/// Runs in the child. It tries to change the host name, and prints what it
/// sees as key=value lines for the parent to read.
fn inside() -> io::Result<()> {
    let outcome = match sethostname("box") {
        Ok(()) => "succeeds".to_owned(),
        Err(error) => format!("fails with {error:?}"),
    };

    let ids = namespaces("self")?;
    let uid_map = fs::read_to_string("/proc/self/uid_map")?;
    let uid_map: Vec<&str> = uid_map.split_whitespace().collect();

    println!("sethostname={outcome}");
    println!("hostname={}", hostname()?);
    println!("pid={}", getpid());
    println!("uid={}", getuid());
    println!("map={}", uid_map.join(" "));
    println!("uts={}", ids["uts"]);
    println!("pidns={}", ids["pid"]);

    Ok(())
}
// ANCHOR_END: inside

// ANCHOR: start
/// Moves this process into new user and UTS namespaces, maps user 0 inside to
/// the current user, and runs the program again as a child. A new PID
/// namespace applies to the children of the process that asks for it, so the
/// child is the first process of that namespace.
fn isolated() -> io::Result<()> {
    let (uid, gid) = (getuid(), getgid());

    unshare(CloneFlags::CLONE_NEWUSER | CloneFlags::CLONE_NEWUTS | CloneFlags::CLONE_NEWPID)?;

    fs::write("/proc/self/setgroups", "deny")?;
    fs::write("/proc/self/uid_map", format!("0 {uid} 1"))?;
    fs::write("/proc/self/gid_map", format!("0 {gid} 1"))?;

    let status = Command::new("/proc/self/exe").arg("inside").status()?;

    process::exit(if status.success() { 0 } else { 1 });
}

/// Runs this program again as a child and returns the lines the child prints,
/// as a map. With `isolate` set, the child is created in new namespaces.
fn report(isolate: bool) -> io::Result<HashMap<String, String>> {
    let mode = if isolate { "isolated" } else { "inside" };
    let output = Command::new("/proc/self/exe").arg(mode).output()?;

    let seen = String::from_utf8_lossy(&output.stdout)
        .lines()
        .filter_map(|line| line.split_once('='))
        .map(|(key, value)| (key.to_owned(), value.to_owned()))
        .collect();

    Ok(seen)
}
// ANCHOR_END: start

// ANCHOR: compare
fn run() -> io::Result<()> {
    let mine = namespaces("self")?;
    let name = hostname()?;

    for isolate in [false, true] {
        let seen = report(isolate)?;
        let get = |key: &str| seen.get(key).map_or("", String::as_str);

        println!("child in new user, UTS and PID namespaces: {isolate}");
        println!(
            "  same UTS namespace as the parent {}, same PID namespace {}",
            get("uts") == mine["uts"],
            get("pidns") == mine["pid"]
        );
        println!(
            "  sethostname {}; host name inside is \"box\" {}, outside unchanged {}",
            get("sethostname"),
            get("hostname") == "box",
            hostname()? == name
        );
        println!(
            "  pid inside is 1 {}; uid inside is 0 {}",
            get("pid") == "1",
            get("uid") == "0"
        );

        let map: Vec<&str> = get("map").split_whitespace().collect();

        if let (true, [_, outside, _]) = (isolate, map.as_slice()) {
            println!("  uid map: user 0 inside is user {outside} outside");
        }
    }

    Ok(())
}
// ANCHOR_END: compare

fn main() -> io::Result<()> {
    match env::args().nth(1).as_deref() {
        Some("inside") => inside(),
        Some("isolated") => isolated(),
        _ => run(),
    }
}
