//! Runs a shell script in a container built by hand: new user, mount, UTS,
//! PID, IPC and network namespaces, a root file system of its own, and a control group
//! with a limit on the number of processes.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p box
//! ```

// ANCHOR: imports
use std::env;
use std::fs;
use std::io;
use std::os::unix::fs::symlink;
use std::os::unix::process::CommandExt;
use std::path::{Path, PathBuf};
use std::process::{self, Command};
use std::thread;
use std::time::Duration;

use nix::mount::{MntFlags, MsFlags, mount, umount2};
use nix::sched::{CloneFlags, unshare};
use nix::unistd::{chdir, getgid, gethostname, getuid, pivot_root, sethostname};
// ANCHOR_END: imports

// ANCHOR: group
/// Makes a control group for the container below the nearest group that
/// passes the pids controller to its children, and sets `pids.max`.
fn create_group(pids_max: u32) -> io::Result<PathBuf> {
    let line = fs::read_to_string("/proc/self/cgroup")?;
    let path = line.trim().split_once("::").map_or("", |(_, path)| path);

    let root = Path::new("/sys/fs/cgroup");
    let own = root.join(path.trim_start_matches('/'));

    for dir in own.ancestors().take_while(|dir| *dir != root) {
        let Ok(enabled) = fs::read_to_string(dir.join("cgroup.subtree_control")) else {
            continue;
        };

        if enabled.contains("pids") {
            let group = dir.join(format!("box-{}", process::id()));

            fs::create_dir(&group)?;
            fs::write(group.join("pids.max"), pids_max.to_string())?;

            return Ok(group);
        }
    }

    Err(io::Error::other(
        "no parent group passes on the pids controller",
    ))
}

/// Returns the number of forks the group has refused.
fn refused(group: &Path) -> io::Result<String> {
    fs::read_to_string(group.join("pids.events"))?
        .lines()
        .find_map(|line| line.strip_prefix("max "))
        .map(str::to_owned)
        .ok_or_else(|| io::Error::other("pids.events has no line max"))
}

/// Waits until the group is empty and deletes it.
fn remove_group(group: &Path) -> io::Result<()> {
    while fs::read_to_string(group.join("pids.current"))?.trim() != "0" {
        thread::sleep(Duration::from_millis(1));
    }

    fs::remove_dir(group)
}
// ANCHOR_END: group

// ANCHOR: launch
/// Runs in a helper process. It moves itself into new namespaces, maps the
/// current user to user 0 inside, and starts the first process of the
/// container. The new PID namespace takes effect for that child.
fn enter(group: &str, root: &str, script: &str) -> io::Result<()> {
    let (uid, gid) = (getuid(), getgid());

    unshare(
        CloneFlags::CLONE_NEWUSER
            | CloneFlags::CLONE_NEWNS
            | CloneFlags::CLONE_NEWUTS
            | CloneFlags::CLONE_NEWPID
            | CloneFlags::CLONE_NEWIPC
            | CloneFlags::CLONE_NEWNET,
    )?;

    fs::write("/proc/self/setgroups", "deny")?;
    fs::write("/proc/self/uid_map", format!("0 {uid} 1"))?;
    fs::write("/proc/self/gid_map", format!("0 {gid} 1"))?;

    let status = Command::new("/proc/self/exe")
        .args(["init", group, root, script])
        .status()?;

    let Some(code) = status.code() else {
        process::exit(1);
    };

    process::exit(code);
}
// ANCHOR_END: launch

// ANCHOR: root
/// The directories of the host that the container can see.
const SHARED: [&str; 4] = ["bin", "sbin", "lib", "usr"];

/// No source, file system type or options, for the calls to `mount` that
/// need none.
const NONE: Option<&str> = None;

/// Assembles the root file system of the container in an empty directory: a
/// tmpfs, the host's program directories, the null device, and a new /proc.
fn build_root(root: &Path) -> io::Result<()> {
    // Mount changes made from here on stay in this mount namespace.
    mount(NONE, "/", NONE, MsFlags::MS_REC | MsFlags::MS_PRIVATE, NONE)?;
    mount(Some("tmpfs"), root, Some("tmpfs"), MsFlags::empty(), NONE)?;

    for name in SHARED {
        let (source, target) = (Path::new("/").join(name), root.join(name));

        // On this system /bin, /sbin and /lib are symbolic links into /usr.
        if let Ok(link) = fs::read_link(&source) {
            symlink(link, target)?;

            continue;
        }

        fs::create_dir(&target)?;
        mount(
            Some(&source),
            &target,
            NONE,
            MsFlags::MS_BIND | MsFlags::MS_REC,
            NONE,
        )?;
    }

    // The container gets a /dev with the null device and nothing else.
    let null = root.join("dev/null");

    fs::create_dir(root.join("dev"))?;
    fs::write(&null, "")?;
    mount(Some("/dev/null"), &null, NONE, MsFlags::MS_BIND, NONE)?;

    let proc = root.join("proc");

    fs::create_dir(&proc)?;
    mount(Some("proc"), &proc, Some("proc"), MsFlags::empty(), NONE)?;

    Ok(())
}

/// Makes `root` the root directory of the mount namespace and detaches the
/// host's file system from it.
fn enter_root(root: &Path) -> io::Result<()> {
    let old = root.join("old");

    fs::create_dir(&old)?;
    pivot_root(root, &old)?;
    chdir("/")?;
    umount2("/old", MntFlags::MNT_DETACH)?;

    fs::remove_dir("/old")
}
// ANCHOR_END: root

// ANCHOR: init
/// Runs as process 1 of the container. It moves itself into the control
/// group, where writing 0 to `cgroup.procs` means "the writing process".
/// Then it builds and enters the root file system, sets the host name, and
/// replaces itself with a shell that runs the script.
fn initialize(group: &Path, root: &Path, script: &str) -> io::Result<()> {
    fs::write(group.join("cgroup.procs"), "0")?;

    build_root(root)?;
    enter_root(root)?;
    sethostname("box")?;

    let error = Command::new("/bin/sh")
        .args(["-c", script])
        .env_clear()
        .env("PATH", "/usr/sbin:/usr/bin:/sbin:/bin")
        .exec();

    Err(error)
}
// ANCHOR_END: init

// ANCHOR: run
/// What the container runs.
const SCRIPT: &str = r#"echo "host name: $(hostname)"
echo "process number of the shell: $$"
echo "user number: $(id -u)"
echo "processes under /proc:" /proc/[0-9]*
echo "root directory:" /*
while read device directory type rest; do echo "mounted: $directory ($type)"; done < /proc/mounts
echo "network interfaces:" $(tail -n +3 /proc/net/dev | cut -d: -f1)
echo "effective capabilities:" $(grep CapEff /proc/self/status | cut -f2)
for i in 1 2 3 4 5 6; do sleep 1 & echo "started a background command"; done 2>/dev/null"#;

fn hostname() -> io::Result<String> {
    Ok(gethostname()?.to_string_lossy().into_owned())
}

fn run() -> io::Result<()> {
    let group = create_group(5)?;
    let root = env::temp_dir().join(format!("box-root-{}", process::id()));

    fs::create_dir(&root)?;

    let before = hostname()?;

    let status = Command::new("/proc/self/exe")
        .arg("enter")
        .args([&group, &root])
        .arg(SCRIPT)
        .status()?;

    let Some(code) = status.code() else {
        return Err(io::Error::other("the container was ended by a signal"));
    };

    let count = refused(&group)?;

    remove_group(&group)?;
    fs::remove_dir(&root)?;

    println!("the container ended with status {code}; forks refused by its group: {count}");
    println!("host name outside unchanged: {}", before == hostname()?);

    Ok(())
}

fn main() -> io::Result<()> {
    let args: Vec<String> = env::args().collect();
    let args: Vec<&str> = args.iter().map(String::as_str).collect();

    match args.as_slice() {
        [_, "enter", group, root, script] => enter(group, root, script),
        [_, "init", group, root, script] => initialize(Path::new(group), Path::new(root), script),
        _ => run(),
    }
}
// ANCHOR_END: run
