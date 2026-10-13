//! Measures TCP sockets on the loopback interface: when a connection is
//! established, what identifies it, how written bytes arrive, what stops a
//! writer whose peer does not read, and how each side learns that the other
//! has closed.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p sockfacts
//! ```

// ANCHOR: imports
use std::io::{self, Read, Write};
use std::net::{TcpListener, TcpStream};
use std::os::fd::AsRawFd;

use nix::errno::Errno;
use nix::sys::socket::{setsockopt, sockopt};
// ANCHOR_END: imports

// ANCHOR: pair
/// Returns a TCP socket that listens on a free port of 127.0.0.1.
fn listen() -> io::Result<TcpListener> {
    TcpListener::bind("127.0.0.1:0")
}

/// Returns a TCP socket connected to the address of a listener.
fn connect(listener: &TcpListener) -> io::Result<TcpStream> {
    TcpStream::connect(listener.local_addr()?)
}

/// Returns the symbolic name of a system call error, such as `EPIPE`.
fn name(error: &io::Error) -> String {
    match error.raw_os_error() {
        Some(code) => format!("{:?}", Errno::from_raw(code)),
        None => error.to_string(),
    }
}
// ANCHOR_END: pair

// ANCHOR: establish
/// Connects before the server calls accept, and compares the addresses of
/// both ends.
fn establish() -> io::Result<()> {
    let listener = listen()?;

    let client = connect(&listener);
    println!(
        "connect before the server calls accept: succeeded {}",
        client.is_ok()
    );

    let client = client?;
    let (server, _) = listener.accept()?;

    println!(
        "accept returns a new descriptor: {}, on the listener's port: {}",
        server.as_raw_fd() != listener.as_raw_fd(),
        server.local_addr()?.port() == listener.local_addr()?.port()
    );
    println!(
        "the client's local port is the server's peer port: {}",
        client.local_addr()?.port() == server.peer_addr()?.port()
    );

    stream(client, server)
}
// ANCHOR_END: establish

// ANCHOR: stream
/// Writes "ab" and "cd" with 2 calls and reads 3 bytes and then 1. Then the
/// client closes, and the server reads and writes again.
fn stream(mut client: TcpStream, mut server: TcpStream) -> io::Result<()> {
    for part in ["ab", "cd"] {
        client.write_all(part.as_bytes())?;
    }

    let (mut first, mut second) = ([0u8; 3], [0u8; 1]);

    server.read_exact(&mut first)?;
    server.read_exact(&mut second)?;

    println!(
        "writes of \"ab\" and \"cd\", reads of 3 bytes and 1 byte: {:?} and {:?}",
        String::from_utf8_lossy(&first),
        String::from_utf8_lossy(&second)
    );

    drop(client);

    let n = server.read(&mut first)?;
    println!("the client closed: read returns {n}");

    let error = loop {
        if let Err(error) = server.write(b"x") {
            break error;
        }
    };

    println!(
        "writes to the closed peer: the first is accepted, a later one fails with {}",
        name(&error)
    );

    Ok(())
}
// ANCHOR_END: stream

// ANCHOR: flow
/// Writes blocks to a non-blocking socket until the kernel refuses one and
/// returns the number of bytes accepted.
fn fill(mut stream: &TcpStream) -> io::Result<usize> {
    let block = [0u8; 1024];
    let mut total = 0;

    loop {
        match stream.write(&block) {
            Ok(n) => total += n,
            Err(error) if error.kind() == io::ErrorKind::WouldBlock => return Ok(total),
            Err(error) => return Err(error),
        }
    }
}

/// Gives a connection small buffers, fills it while the server does not read,
/// lets the server read everything, and fills it again.
fn flow() -> io::Result<()> {
    let listener = listen()?;
    setsockopt(&listener, sockopt::RcvBuf, &4096)?;

    let client = connect(&listener)?;
    setsockopt(&client, sockopt::SndBuf, &4096)?;

    let (mut server, _) = listener.accept()?;

    client.set_nonblocking(true)?;

    let sent = fill(&client)?;
    println!("the server does not read: the client is stopped after {sent} bytes");

    server.read_exact(&mut vec![0u8; sent])?;

    let again = fill(&client)?;
    println!(
        "the server has read everything: the client can write again: {}",
        again > 0
    );

    Ok(())
}
// ANCHOR_END: flow

fn main() -> io::Result<()> {
    establish()?;
    flow()
}
