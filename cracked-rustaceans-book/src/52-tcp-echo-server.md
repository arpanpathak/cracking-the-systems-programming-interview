# 52. A Thread-per-Connection Echo Server {#tcp-echo-server}

*Source file: [`src/bin/tcp_echo_server.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/tcp_echo_server.rs). Run it with `cargo run --bin tcp_echo_server`, then connect with `nc 127.0.0.1 <port>`.*

## Problem Statement

Listen on a TCP address. For every client that connects, send back every byte the client
sends, until the client closes its side of the connection. Several clients must be
served at the same time, and an error on one connection must not stop the server.

## Designing a Solution

The server's lifecycle has a fixed order:

```text
bind      reserve a local address and port
listen    ask the kernel to queue incoming connections (TcpListener::bind does both)
accept    take one queued connection, which yields a new TcpStream
read      block until the client sends bytes, or returns 0 when the client closes
write     send the bytes back
close     drop the TcpStream
```

`accept` returns a separate socket for each client, while the listening socket keeps
accepting. Handling each accepted socket on a new thread lets a slow client block only
its own thread. Reads and writes use ordinary blocking calls, and the code reads as a
simple loop.

TCP delivers a byte stream, not messages. One `write` from the client can arrive as
several `read`s at the server, and several writes can arrive as one read. An echo server
does not care about message boundaries, which is what makes it a clean first exercise.

A `read` that returns `Ok(0)` means the peer has shut down its sending direction, which
happens when it closes the socket. It is not an error, and the server should finish
the connection normally.

## Implementation

````rust
//! TCP echo server: the canonical socket exercise.
//!
//! Demonstrates the server side of the TCP lifecycle: `bind` -> `listen` ->
//! `accept` -> read/write loop -> peer `close` (a `read` of 0). It uses a
//! thread-per-connection model, which is the right default for bounded concurrency
//! and blocking handlers; the event-loop alternative is `src/bin/epoll_echo.rs`.
//!
//! `TCP_NODELAY` is set because an echo server must not sit on Nagle's algorithm
//! waiting to coalesce a reply that will never be followed by more data.
//!
//! ```bash
//! cargo run --bin tcp_echo_server            # binds 127.0.0.1:0, prints the port
//! cargo run --bin tcp_echo_server 0.0.0.0:9000
//! ```

use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::thread;

/// Accept connections forever, handling each on its own thread.
pub fn serve(listener: TcpListener) {
    for incoming in listener.incoming() {
        match incoming {
            Ok(stream) => {
                thread::spawn(move || {
                    if let Err(error) = handle_connection(stream) {
                        eprintln!("connection error: {error}");
                    }
                });
            }
            Err(error) => eprintln!("accept error: {error}"),
        }
    }
}

/// Echo every byte back until the peer closes the connection.
fn handle_connection(mut stream: TcpStream) -> std::io::Result<()> {
    stream.set_nodelay(true)?;
    if let Ok(peer) = stream.peer_addr() {
        println!("connection from {peer}");
    }

    let mut buffer = [0u8; 4096];
    loop {
        let read = stream.read(&mut buffer)?;
        if read == 0 {
            // A zero-byte read is the peer's FIN: an orderly close.
            return Ok(());
        }
        stream.write_all(&buffer[..read])?;
    }
}

fn main() {
    let address = std::env::args()
        .nth(1)
        .unwrap_or_else(|| "127.0.0.1:0".to_string());

    let listener = TcpListener::bind(&address).expect("failed to bind");
    let local = listener.local_addr().expect("failed to read local address");
    println!("tcp echo server listening on {local}");

    serve(listener);
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::net::Shutdown;

    #[test]
    fn echoes_bytes_until_the_client_closes() {
        let listener = TcpListener::bind("127.0.0.1:0").expect("bind ephemeral port");
        let address = listener.local_addr().expect("local address");

        // Accept exactly one connection, echo it, then return so the test can join.
        let server = thread::spawn(move || {
            let (stream, _) = listener.accept().expect("accept one connection");
            handle_connection(stream).expect("echo");
        });

        let mut client = TcpStream::connect(address).expect("connect");
        client.write_all(b"hello gpu").expect("write");
        client.shutdown(Shutdown::Write).expect("half close");

        let mut echoed = Vec::new();
        client.read_to_end(&mut echoed).expect("read echo");

        server.join().expect("server thread panicked");
        assert_eq!(echoed, b"hello gpu");
    }
}
````

`serve` iterates over `listener.incoming()`, which calls `accept` in a loop and yields
`io::Result<TcpStream>`. An `accept` error, such as running out of file descriptors, is
printed and the loop continues. The listener is not closed on a transient error.

`thread::spawn(move || ...)` moves the `TcpStream` into the new thread. The closure
reports a connection error to standard error and returns, and the thread ends. The
`JoinHandle` is dropped, which detaches the thread.

`handle_connection` returns `std::io::Result<()>`, so every fallible call inside it uses
`?`. `stream.set_nodelay(true)?` disables Nagle's algorithm. Nagle's algorithm delays a
small write while earlier data is unacknowledged, hoping to combine it with the next
write. An echo server writes one reply per read, so the delay would add latency without
saving packets.

`write_all(&buffer[..read])` writes exactly the bytes received. `write` alone may send
fewer bytes than requested, and `write_all` repeats it until every byte is sent or an
error occurs.

`main` binds to `127.0.0.1:0` by default. Port 0 asks the kernel to choose a free port,
and `listener.local_addr()` reports which one it chose.

The test binds its own listener on port 0, accepts exactly one connection on a helper
thread, and calls `handle_connection` directly, so it needs neither a fixed port nor a
separate process. The client calls `shutdown(Shutdown::Write)` after writing. That sends
a FIN, which makes the server's next `read` return 0, and the client's `read_to_end` then
receives the echoed bytes followed by the server's own close.

## Intuition

**The test `echoes_bytes_until_the_client_closes`**

| step | client | server thread |
|---|---|---|
| 1 | | `TcpListener::bind("127.0.0.1:0")`, `accept` blocks |
| 2 | `TcpStream::connect(address)` | `accept` returns a stream |
| 3 | `write_all(b"hello gpu")` | `read` returns 9 |
| 4 | `shutdown(Write)` sends FIN | `write_all` sends 9 bytes back |
| 5 | `read_to_end` receives 9 bytes | `read` returns 0, `handle_connection` returns `Ok(())` |
| 6 | `read_to_end` sees the server's close and returns | the stream is dropped, closing the socket |
| 7 | `server.join()` succeeds; `echoed == b"hello gpu"` | |

## Time and Space Complexity

| Resource | Cost |
|---|---|
| Per connection | one thread, with its own stack (2 MiB by default for spawned threads) and one 4 KiB buffer |
| Per byte | one copy into the buffer and one copy out, plus system calls for `read` and `write` |
| Concurrency | limited by the number of threads the process and the kernel allow |

Threads are cheap to write and expensive to have many of. A server with ten thousand
idle connections holds ten thousand threads, most of them blocked in `read`.

## Limitations

**The number of threads is unbounded.** Every connection spawns a thread with no limit,
so a burst of connections can exhaust memory or the process's thread limit. A worker
pool, or a semaphore around `accept` as in chapter 45, bounds the work.

**No timeouts.** A client that connects and never sends anything holds a thread
forever. `set_read_timeout` and `set_write_timeout` on the stream give each connection
an idle limit.

**A slow reader stalls its own thread.** `write_all` blocks when the client does not
read and the socket's send buffer fills. With one thread per connection that affects
only that client, which is the main advantage of this design over a naive
single-threaded loop.

**Detached threads are not shut down.** `serve` never returns, and the spawned threads
are not tracked. A server that must stop cleanly needs a shutdown signal and a way to
join or cancel connection threads.

**`serve` is public in a binary crate.** The `pub` keyword has no effect in a binary,
which has no downstream users. It is harmless and suggests the function was meant to
live in the library.

## Summary

- `TcpListener::bind` performs `bind` and `listen`, and `incoming` yields one
  `TcpStream` per accepted connection.
- One thread per connection keeps each handler a simple blocking loop and isolates slow
  clients from each other.
- A `read` of zero bytes is the peer's orderly close, not an error.
- `write_all` handles partial writes, and `set_nodelay(true)` removes Nagle's delay for
  request-reply traffic.
- Binding to port 0 and calling the handler directly lets a server be tested in-process
  with no fixed port.

## References

- W. Richard Stevens, Bill Fenner, and Andrew M. Rudoff, *UNIX Network Programming,
  Volume 1*, 3rd edition, Addison-Wesley, 2003, Chapters 19 and 36.
- RFC 896, *Congestion Control in IP/TCP Internetworks*, 1984, which describes Nagle's
  algorithm.
- Standard library, [`std::net::TcpListener`](https://doc.rust-lang.org/std/net/struct.TcpListener.html) and [`TcpStream::set_nodelay`](https://doc.rust-lang.org/std/net/struct.TcpStream.html#method.set_nodelay).
- Standard library, [`Write::write_all`](https://doc.rust-lang.org/std/io/trait.Write.html#method.write_all).
