//! Measures the page cache for one file: how many of the file's pages are
//! held in memory after a write, after the cache is told to drop them, and
//! after reads of different kinds.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p cachefacts
//! ```

// ANCHOR: imports
use std::fs::{self, File, OpenOptions};
use std::io::{self, Write};
use std::os::unix::fs::FileExt;
use std::path::Path;
use std::process::Command;

use nix::fcntl::{PosixFadviseAdvice, posix_fadvise};
// ANCHOR_END: imports

// ANCHOR: cached
const PAGE_SIZE: usize = 4096;

/// Returns the number of pages of a file that are in the page cache, as
/// reported by the fincore utility.
fn cached(path: &Path) -> io::Result<usize> {
    let output = Command::new("fincore")
        .args(["--noheadings", "--output", "PAGES"])
        .arg(path)
        .output()?;

    String::from_utf8_lossy(&output.stdout)
        .trim()
        .parse()
        .map_err(|_| io::ErrorKind::InvalidData.into())
}

/// Prints a step and the number of cached pages after it.
fn report(step: &str, path: &Path) -> io::Result<()> {
    let pages = cached(path)?;
    println!("{:<38} cached pages: {pages}", format!("{step}:"));

    Ok(())
}

/// Writes the file's dirty pages to disk and asks the kernel to remove the
/// file's pages from the cache.
fn drop_pages(file: &File) -> io::Result<()> {
    file.sync_all()?;
    posix_fadvise(file, 0, 0, PosixFadviseAdvice::POSIX_FADV_DONTNEED)?;

    Ok(())
}
// ANCHOR_END: cached

// ANCHOR: steps
/// Writes a file of 64 pages and reads it in 3 ways, dropping the cached
/// pages between the steps.
fn run(path: &Path) -> io::Result<()> {
    let mut file = OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .truncate(true)
        .open(path)?;

    file.write_all(&vec![0u8; 64 * PAGE_SIZE])?;
    report("write of 64 pages", path)?;

    drop_pages(&file)?;
    report("fsync, then FADV_DONTNEED", path)?;

    let mut one = [0u8; 1];

    file.read_exact_at(&mut one, 0)?;
    report("read of 1 byte at offset 0", path)?;

    let mut whole = vec![0u8; 64 * PAGE_SIZE];

    file.read_exact_at(&mut whole, 0)?;
    report("read of the whole file", path)?;

    drop_pages(&file)?;
    posix_fadvise(&file, 0, 0, PosixFadviseAdvice::POSIX_FADV_RANDOM)?;

    file.read_exact_at(&mut one, 0)?;
    report("dropped, FADV_RANDOM, read of 1 byte", path)
}
// ANCHOR_END: steps

fn main() -> io::Result<()> {
    let dir = std::env::temp_dir().join(format!("cachefacts-{}", std::process::id()));

    fs::create_dir_all(&dir)?;

    let result = run(&dir.join("file"));

    fs::remove_dir_all(&dir)?;

    result
}
