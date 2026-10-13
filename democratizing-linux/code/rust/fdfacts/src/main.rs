//! Measures how the kernel hands out file descriptors and what a pair of
//! descriptors shares: the number an open returns, the file offset, the
//! status flags, and the close-on-exec flag. It ends with the redirection
//! `> file 2>&1`, done once with a shared open file description and once with
//! separate ones.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p fdfacts
//! ```

// ANCHOR: imports
use std::fs::{self, File, OpenOptions};
use std::io::{self, Read};
use std::os::fd::{AsFd, AsRawFd};
use std::os::unix::fs::MetadataExt;
use std::path::Path;
use std::process::Command;

use nix::fcntl::{FcntlArg, FdFlag, OFlag, fcntl, open};
use nix::sys::resource::{Resource, getrlimit, setrlimit};
use nix::sys::stat::Mode;
use nix::unistd::{Whence, close, dup, lseek, write};
// ANCHOR_END: imports

// ANCHOR: numbers
/// Closes descriptor 0, the standard input, and opens a file. The kernel
/// gives an open the lowest number that is free.
fn numbers(path: &Path) -> io::Result<()> {
    close(0)?;

    let fd = open(path, OFlag::O_RDONLY, Mode::empty())?;
    println!(
        "descriptor 0 closed: the next open returns {}",
        fd.as_raw_fd()
    );

    Ok(())
}
// ANCHOR_END: numbers

// ANCHOR: limit
/// Lowers the limit on open descriptors to 32 and opens a file until the
/// kernel refuses.
fn limit(path: &Path) -> io::Result<()> {
    let (soft, hard) = getrlimit(Resource::RLIMIT_NOFILE)?;

    setrlimit(Resource::RLIMIT_NOFILE, 32, hard)?;

    let mut opened = Vec::new();

    let error = loop {
        match open(path, OFlag::O_RDONLY, Mode::empty()) {
            Ok(fd) => opened.push(fd),
            Err(error) => break error,
        }
    };

    let highest = opened.iter().map(AsRawFd::as_raw_fd).fold(-1, i32::max);

    println!(
        "limit of 32 descriptors: the highest number obtained is {highest}, the next open fails with {error:?}"
    );

    drop(opened);
    setrlimit(Resource::RLIMIT_NOFILE, soft, hard)?;

    Ok(())
}
// ANCHOR_END: limit

// ANCHOR: offsets
/// Returns the file offset that a descriptor refers to.
fn offset(fd: impl AsFd) -> nix::Result<i64> {
    lseek(fd, 0, Whence::SeekCur)
}

/// Writes through one descriptor and reads the offset through a duplicate of
/// it and through a second open of the same file.
fn offsets(path: &Path) -> io::Result<()> {
    let first = open(path, OFlag::O_WRONLY, Mode::empty())?;
    let duplicate = dup(&first)?;
    let second = open(path, OFlag::O_WRONLY, Mode::empty())?;

    write(&first, b"hello")?;

    let shared = offset(&duplicate)?;
    let separate = offset(&second)?;

    println!(
        "after a write of 5 bytes: offset through the duplicate {shared}, through a second open {separate}"
    );

    Ok(())
}
// ANCHOR_END: offsets

// ANCHOR: flags
/// Sets `O_APPEND` and close-on-exec through a duplicate and reads both
/// through the original descriptor.
fn flags(path: &Path) -> io::Result<()> {
    let first = open(path, OFlag::O_WRONLY, Mode::empty())?;
    let duplicate = dup(&first)?;

    fcntl(&duplicate, FcntlArg::F_SETFL(OFlag::O_APPEND))?;
    fcntl(&duplicate, FcntlArg::F_SETFD(FdFlag::FD_CLOEXEC))?;

    let status = OFlag::from_bits_truncate(fcntl(&first, FcntlArg::F_GETFL)?);
    let descriptor = FdFlag::from_bits_truncate(fcntl(&first, FcntlArg::F_GETFD)?);

    println!(
        "set on the duplicate, read on the original: O_APPEND {}, close-on-exec {}",
        status.contains(OFlag::O_APPEND),
        descriptor.contains(FdFlag::FD_CLOEXEC)
    );

    Ok(())
}
// ANCHOR_END: flags

// ANCHOR: names
/// Gives a file a second name and compares the inodes behind the names.
fn names(path: &Path) -> io::Result<()> {
    let (first, second) = (path.with_extension("first"), path.with_extension("second"));

    fs::write(&first, "hello")?;
    fs::hard_link(&first, &second)?;

    let (a, b) = (fs::metadata(&first)?, fs::metadata(&second)?);

    println!(
        "a second name for the file: same inode {}, link count {}",
        a.ino() == b.ino(),
        b.nlink()
    );

    fs::remove_file(&first)?;
    fs::remove_file(&second)
}
// ANCHOR_END: names

// ANCHOR: unlinked
/// Opens a file, removes its only name, and reads through the descriptor.
fn unlinked(path: &Path) -> io::Result<()> {
    let name = path.with_extension("unlinked");

    fs::write(&name, "hello")?;

    let mut file = File::open(&name)?;

    fs::remove_file(&name)?;

    let links = file.metadata()?.nlink();
    let mut text = String::new();

    file.read_to_string(&mut text)?;

    println!(
        "the name removed, the file still open: link count {links}, read through the descriptor returns {text:?}"
    );

    Ok(())
}
// ANCHOR_END: unlinked

// ANCHOR: redirect
/// Runs a command that writes "out" to descriptor 1 and then "err" to
/// descriptor 2, with both descriptors on the same file, and returns the
/// file's contents.
fn redirect(path: &Path, stdout: File, stderr: File) -> io::Result<String> {
    Command::new("sh")
        .args(["-c", "echo out; echo err >&2"])
        .stdout(stdout)
        .stderr(stderr)
        .status()?;

    let text = fs::read_to_string(path)?;
    let words: Vec<&str> = text.split_whitespace().collect();

    Ok(words.join(" "))
}

/// Compares `> file 2>&1`, where descriptor 2 is a duplicate of descriptor 1,
/// with `> file 2> file`, where the file is opened once for each.
fn redirections(path: &Path) -> io::Result<()> {
    let stdout = File::create(path)?;
    let stderr = stdout.try_clone()?;

    let text = redirect(path, stdout, stderr)?;
    println!("> file 2>&1: the file holds {text:?}");

    let first = File::create(path)?;
    let second = OpenOptions::new().write(true).open(path)?;

    let text = redirect(path, first, second)?;
    println!("> file 2> file: the file holds {text:?}");

    Ok(())
}
// ANCHOR_END: redirect

fn main() -> io::Result<()> {
    let dir = std::env::temp_dir().join(format!("fdfacts-{}", std::process::id()));
    let path = dir.join("file");

    fs::create_dir_all(&dir)?;
    fs::write(&path, "")?;

    let result = numbers(&path)
        .and_then(|()| limit(&path))
        .and_then(|()| offsets(&path))
        .and_then(|()| flags(&path))
        .and_then(|()| names(&path))
        .and_then(|()| unlinked(&path))
        .and_then(|()| redirections(&path));

    fs::remove_dir_all(&dir)?;

    result
}
