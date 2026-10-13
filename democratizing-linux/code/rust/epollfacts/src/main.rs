//! Measures epoll with pipes: which descriptors a wait reports, how
//! level-triggered and edge-triggered registrations differ, how a closed peer
//! is reported, and how many events a wait returns when 1000 descriptors are
//! registered and 1 is ready.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p epollfacts
//! ```

// ANCHOR: imports
use std::os::fd::OwnedFd;

use nix::fcntl::OFlag;
use nix::sys::epoll::{Epoll, EpollCreateFlags, EpollEvent, EpollFlags, EpollTimeout};
use nix::unistd::{pipe2, read, write};
// ANCHOR_END: imports

// ANCHOR: setup
/// The pair of descriptors of one pipe. The write end is an `Option` so that
/// an experiment can close it.
struct Pipe {
    reader: OwnedFd,
    writer: Option<OwnedFd>,
}

/// Creates an epoll instance and `n` pipes, and registers the read end of
/// every pipe for readability with the given extra flags. The number of the
/// pipe is stored in the registration and comes back with each event.
fn watch(n: usize, flags: EpollFlags) -> nix::Result<(Epoll, Vec<Pipe>)> {
    let epoll = Epoll::new(EpollCreateFlags::EPOLL_CLOEXEC)?;
    let mut pipes = Vec::with_capacity(n);

    for i in 0..n {
        let (reader, writer) = pipe2(OFlag::O_CLOEXEC)?;

        epoll.add(
            &reader,
            EpollEvent::new(EpollFlags::EPOLLIN | flags, i as u64),
        )?;

        pipes.push(Pipe {
            reader,
            writer: Some(writer),
        });
    }

    Ok((epoll, pipes))
}

/// Returns the events that are ready now. A timeout of 0 makes the wait
/// return at once.
fn ready(epoll: &Epoll) -> nix::Result<Vec<EpollEvent>> {
    let mut events = [EpollEvent::empty(); 16];
    let n = epoll.wait(&mut events, EpollTimeout::ZERO)?;

    Ok(events[..n].to_vec())
}

/// Writes "hello" to a pipe whose write end is open.
fn send(pipe: &Pipe) -> nix::Result<()> {
    if let Some(writer) = &pipe.writer {
        write(writer, b"hello")?;
    }

    Ok(())
}
// ANCHOR_END: setup

// ANCHOR: level
/// Registers 3 pipes level-triggered and waits before a write, after a write,
/// again without reading, and after reading.
fn level() -> nix::Result<()> {
    let (epoll, mut pipes) = watch(3, EpollFlags::empty())?;

    println!(
        "3 pipes registered, none written: {} event(s)",
        ready(&epoll)?.len()
    );

    send(&pipes[1])?;

    if let [event] = ready(&epoll)?.as_slice() {
        println!("write to pipe 1: 1 event, for pipe {}", event.data());
    }

    println!(
        "level-triggered, data not read, wait again: {} event(s)",
        ready(&epoll)?.len()
    );

    read(&pipes[1].reader, &mut [0u8; 16])?;
    println!("after reading the data: {} event(s)", ready(&epoll)?.len());

    pipes[1].writer = None;

    if let [event] = ready(&epoll)?.as_slice() {
        println!(
            "write end of pipe 1 closed: event has EPOLLHUP {}",
            event.events().contains(EpollFlags::EPOLLHUP)
        );
    }

    Ok(())
}
// ANCHOR_END: level

// ANCHOR: edge
/// Registers a pipe edge-triggered and waits 2 times after one write, and
/// once more after a second write.
fn edge() -> nix::Result<()> {
    let (epoll, pipes) = watch(1, EpollFlags::EPOLLET)?;
    let mut counts = [0; 3];

    for (i, count) in counts.iter_mut().enumerate() {
        if i != 1 {
            send(&pipes[0])?;
        }

        *count = ready(&epoll)?.len();
    }

    println!(
        "edge-triggered, data not read: wait {} event(s), wait again {} event(s)",
        counts[0], counts[1]
    );
    println!(
        "edge-triggered, after another write: {} event(s)",
        counts[2]
    );

    Ok(())
}
// ANCHOR_END: edge

// ANCHOR: many
/// Registers 1000 pipes and writes to 1 of them.
fn many() -> nix::Result<()> {
    let (epoll, pipes) = watch(1000, EpollFlags::empty())?;

    send(&pipes[700])?;

    if let [event] = ready(&epoll)?.as_slice() {
        println!(
            "1000 pipes registered, pipe 700 written: 1 event, for pipe {}",
            event.data()
        );
    }

    Ok(())
}
// ANCHOR_END: many

fn main() -> nix::Result<()> {
    level()?;
    edge()?;
    many()
}
