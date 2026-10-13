//! Measures how the kernel fills an address space: when a mapped page
//! receives physical memory, what an untouched page contains, how a mapping's
//! permissions appear in `/proc/self/maps`, and where a write through a
//! private or a shared file mapping ends up.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p vmfacts
//! ```

// ANCHOR: imports
use std::fs::{self, File, OpenOptions};
use std::io;
use std::os::unix::fs::FileExt;
use std::path::Path;

use memmap2::{MmapMut, MmapOptions};
// ANCHOR_END: imports

// ANCHOR: resident
const PAGE_SIZE: usize = 4096;

/// Counts the pages of a mapping that have physical memory. The kernel
/// publishes 8 bytes per virtual page in `/proc/self/pagemap`, and bit 63 of
/// an entry is set when the page is present in memory.
fn resident(mapping: &[u8]) -> io::Result<usize> {
    let pagemap = File::open("/proc/self/pagemap")?;
    let mut entries = vec![0u8; 8 * mapping.len() / PAGE_SIZE];
    let offset = mapping.as_ptr() as usize / PAGE_SIZE * 8;

    pagemap.read_exact_at(&mut entries, offset as u64)?;

    let (entries, _) = entries.as_chunks::<8>();
    let count = entries.iter().filter(|entry| entry[7] >> 7 == 1).count();

    Ok(count)
}
// ANCHOR_END: resident

// ANCHOR: demand
/// Maps 64 pages of anonymous memory, writes to 10 of them, reads 1 more, and
/// counts the resident pages after each step.
fn demand() -> io::Result<()> {
    let mut mapping = MmapMut::map_anon(64 * PAGE_SIZE)?;

    let before = resident(&mapping)?;

    for page in 0..10 {
        mapping[page * PAGE_SIZE] = 1;
    }

    let written = resident(&mapping)?;

    let value = mapping[20 * PAGE_SIZE];
    let read = resident(&mapping)?;

    println!("64 pages mapped: {before} resident");
    println!("after writing to 10 pages: {written} resident");
    println!("after reading 1 more page: {read} resident, the byte read is {value}");

    Ok(())
}
// ANCHOR_END: demand

// ANCHOR: protect
/// Returns the permission column of the line in `/proc/self/maps` that starts
/// at the address of a mapping.
fn permissions(mapping: &[u8]) -> io::Result<String> {
    let start = format!("{:x}-", mapping.as_ptr() as usize);

    fs::read_to_string("/proc/self/maps")?
        .lines()
        .filter(|line| line.starts_with(&start))
        .find_map(|line| line.split_whitespace().nth(1))
        .map(str::to_owned)
        .ok_or_else(|| io::ErrorKind::NotFound.into())
}

/// Reads the permissions of a mapping before and after mprotect removes the
/// permission to write.
fn protect() -> io::Result<()> {
    let mapping = MmapMut::map_anon(PAGE_SIZE)?;
    let before = permissions(&mapping)?;

    let mapping = mapping.make_read_only()?;
    let after = permissions(&mapping)?;

    println!("permissions of the mapping: {before}, after mprotect: {after}");

    Ok(())
}
// ANCHOR_END: protect

// ANCHOR: file
/// Maps a file that holds "hello", writes "HELLO" through the mapping, unmaps
/// it, and returns the contents of the file.
fn through_mapping(path: &Path, shared: bool) -> io::Result<String> {
    fs::write(path, "hello")?;

    let file = OpenOptions::new().read(true).write(true).open(path)?;
    let options = MmapOptions::new();

    // SAFETY: mapping a file is unsafe in Rust because another process could
    // change the file while the slice exists. This file is in a directory the
    // program has just created, and nothing else opens it.
    let mut mapping = unsafe {
        if shared {
            options.map_mut(&file)?
        } else {
            options.map_copy(&file)?
        }
    };

    mapping.copy_from_slice(b"HELLO");
    drop(mapping);

    fs::read_to_string(path)
}

/// Compares a private file mapping with a shared one.
fn files() -> io::Result<()> {
    let dir = std::env::temp_dir().join(format!("vmfacts-{}", std::process::id()));
    let path = dir.join("file");

    fs::create_dir_all(&dir)?;

    for (name, shared) in [("private", false), ("shared", true)] {
        let text = through_mapping(&path, shared)?;
        println!("HELLO written through a {name} file mapping: the file holds {text:?}");
    }

    fs::remove_dir_all(&dir)
}
// ANCHOR_END: file

fn main() -> io::Result<()> {
    demand()?;
    protect()?;
    files()
}
