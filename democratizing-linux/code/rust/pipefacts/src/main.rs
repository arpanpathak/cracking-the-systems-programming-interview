//! Measures a kernel pipe: its capacity, the unit in which
//! a read frees space, how a reader observes the end of the stream, and the
//! result of a write when no reader exists.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p pipefacts
//! ```

// ANCHOR: imports
use std::os::fd::OwnedFd;

use nix::errno::Errno;
use nix::fcntl::{FcntlArg, OFlag, fcntl};
use nix::unistd::{pipe2, read, write};
// ANCHOR_END: imports

// ANCHOR: pipe
/// The size of every write the program attempts: one page.
const BLOCK: usize = 4096;

/// Creates a pipe in non-blocking mode: a read or a write that cannot proceed
/// returns `EAGAIN` where it would otherwise suspend the caller. The read end
/// is first.
fn new_pipe() -> nix::Result<(OwnedFd, OwnedFd)> {
    pipe2(OFlag::O_NONBLOCK | OFlag::O_CLOEXEC)
}
// ANCHOR_END: pipe

// ANCHOR: fill
/// Writes whole blocks until the kernel refuses one and returns the number of
/// bytes accepted.
fn fill(writer: &OwnedFd) -> nix::Result<usize> {
    let data = [0u8; BLOCK];
    let mut total = 0;

    loop {
        match write(writer, &data) {
            Ok(n) => total += n,
            Err(Errno::EAGAIN) => return Ok(total),
            Err(error) => return Err(error),
        }
    }
}

/// Reads and discards up to `n` bytes.
fn drain(reader: &OwnedFd, n: usize) -> nix::Result<usize> {
    read(reader, &mut vec![0u8; n])
}
// ANCHOR_END: fill

// ANCHOR: capacity
/// Fills a pipe when it is new, after 1 byte has been read, and after 4096
/// bytes have been read. Each fill reports the free space.
fn capacity() -> nix::Result<()> {
    let (reader, writer) = new_pipe()?;

    let steps = [
        (0, "new pipe"),
        (1, "after reading 1 byte"),
        (BLOCK - 1, "after reading 4096 bytes in total"),
    ];

    for (count, label) in steps {
        drain(&reader, count)?;

        let accepted = fill(&writer)?;
        println!("{label}: {accepted} bytes accepted");
    }

    Ok(())
}
// ANCHOR_END: capacity

// ANCHOR: resize
/// Changes the capacity of a pipe with fcntl and measures it after each
/// change.
fn resize() -> nix::Result<()> {
    let (reader, writer) = new_pipe()?;

    for request in [4 * BLOCK, 5000, 1 << 20] {
        let granted = fcntl(&writer, FcntlArg::F_SETPIPE_SZ(request as i32))?;
        let accepted = fill(&writer)?;

        println!(
            "capacity of {request} bytes requested: {granted} granted, {accepted} bytes accepted"
        );

        drain(&reader, accepted)?;
    }

    Ok(())
}
// ANCHOR_END: resize

// ANCHOR: eof
/// Reads an empty pipe while a write end is open, and again after the write
/// end has been closed.
fn end_of_stream() -> nix::Result<()> {
    let (reader, writer) = new_pipe()?;
    let mut buf = [0u8; BLOCK];

    if let Err(error) = read(&reader, &mut buf) {
        println!("empty pipe, write end open: read fails with {error:?}");
    }

    drop(writer);

    let n = read(&reader, &mut buf)?;
    println!("empty pipe, write end closed: read returns {n}");

    Ok(())
}
// ANCHOR_END: eof

// ANCHOR: broken
/// Writes to a pipe whose read end has been closed.
fn broken_pipe() -> nix::Result<()> {
    let (reader, writer) = new_pipe()?;

    drop(reader);

    if let Err(error) = write(&writer, b"hello") {
        println!("read end closed: write fails with {error:?}");
    }

    Ok(())
}
// ANCHOR_END: broken

fn main() -> nix::Result<()> {
    capacity()?;
    resize()?;
    end_of_stream()?;
    broken_pipe()
}
