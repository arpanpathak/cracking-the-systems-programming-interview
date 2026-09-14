# 53. An epoll Echo Server {#epoll-echo-server}

*Source file: [`src/bin/epoll_echo.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/epoll_echo.rs). It runs on Linux only. Run it with `cargo run --bin epoll_echo`, optionally followed by a port number, and connect with `nc 127.0.0.1 9000`.*

## Problem Statement

Serve any number of echo clients from a single thread. No call may block on one client
while others are waiting. A client that sends faster than the server can write back to
it must not stall the rest.

## Designing a Solution

**Non-blocking sockets.** A socket opened with `SOCK_NONBLOCK` never waits. A read with
no data available fails with `EAGAIN` instead of sleeping, and so does a write when the
send buffer is full.

**Readiness notification.** An `epoll` instance holds a set of file descriptors and the
events of interest for each. `epoll_wait` sleeps until at least one registered
descriptor is ready, then reports which ones, and the loop handles only those.

**Level-triggered events.** Without the `EPOLLET` flag, `epoll` reports a descriptor as
readable for as long as unread data remains. A loop that does not drain a socket in one
pass is reminded on the next `epoll_wait`, which makes the code harder to get wrong than
the edge-triggered mode.

**Per-connection output buffers.** When a write accepts only part of the reply, the rest
is stored in the connection's buffer and the loop registers interest in `EPOLLOUT`. When
the socket becomes writable, the loop writes the remainder and removes the interest, so
`epoll` does not wake the loop continuously for a socket that has nothing to send.

The diagram below shows one iteration of the loop.

```text
epoll_wait(epfd, events, 64, 100 ms)
    |
    +-- listening socket readable ---> accept4 until EAGAIN, register each client for EPOLLIN
    |
    +-- client readable -------------> read until EAGAIN into connection.out, then flush
    |                                   read returns 0 -> close the connection
    |
    +-- client writable -------------> flush the rest of connection.out
    |
    +-- after either ----------------> EPOLLIN | EPOLLOUT if output is pending, else EPOLLIN
```

## Implementation

The file keeps its Linux code in a module compiled only on Linux, with a fallback `main`
for other platforms. The listings follow the file from top to bottom.

### Connection state and the listening socket

```rust
//! epoll echo server: one thread, many non-blocking sockets.
//!
//! Reads run until `EAGAIN`, and a reply that does not fit the socket buffer is
//! queued and finished under `EPOLLOUT`, so one slow client cannot stall the loop.
//! Linux only; kqueue and IOCP are the portable equivalents.

#[cfg(target_os = "linux")]
mod linux {
    use std::collections::HashMap;
    use std::io;
    use std::sync::atomic::{AtomicBool, Ordering};

    const MAX_EVENTS: usize = 64;
    const EPOLL_TIMEOUT_MS: i32 = 100;

    /// Per-connection state. `out`/`out_pos` form a write buffer that survives a
    /// partial write.
    #[derive(Default)]
    struct Connection {
        out: Vec<u8>,
        out_pos: usize,
    }

    impl Connection {
        fn has_pending_output(&self) -> bool {
            self.out_pos < self.out.len()
        }
    }

    /// Bind a non-blocking listener on `127.0.0.1:port`; port 0 asks the kernel for
    /// a free port, which is returned alongside the fd.
    pub fn bind_listener(port: u16) -> io::Result<(i32, u16)> {
        // SAFETY: all pointers are to stack values that outlive the call.
        unsafe {
            let fd = libc::socket(libc::AF_INET, libc::SOCK_STREAM | libc::SOCK_NONBLOCK, 0);
            if fd < 0 {
                return Err(io::Error::last_os_error());
            }

            let enable: libc::c_int = 1;
            if libc::setsockopt(
                fd,
                libc::SOL_SOCKET,
                libc::SO_REUSEADDR,
                &enable as *const _ as *const libc::c_void,
                std::mem::size_of::<libc::c_int>() as libc::socklen_t,
            ) < 0
            {
                let error = io::Error::last_os_error();
                libc::close(fd);
                return Err(error);
            }

            let mut address: libc::sockaddr_in = std::mem::zeroed();
            address.sin_family = libc::AF_INET as libc::sa_family_t;
            address.sin_port = port.to_be();
            address.sin_addr.s_addr = libc::INADDR_LOOPBACK.to_be();

            if libc::bind(
                fd,
                &address as *const _ as *const libc::sockaddr,
                std::mem::size_of::<libc::sockaddr_in>() as libc::socklen_t,
            ) < 0
            {
                let error = io::Error::last_os_error();
                libc::close(fd);
                return Err(error);
            }

            if libc::listen(fd, 128) < 0 {
                let error = io::Error::last_os_error();
                libc::close(fd);
                return Err(error);
            }

            let mut bound: libc::sockaddr_in = std::mem::zeroed();
            let mut length = std::mem::size_of::<libc::sockaddr_in>() as libc::socklen_t;
            if libc::getsockname(fd, &mut bound as *mut _ as *mut libc::sockaddr, &mut length) < 0 {
                let error = io::Error::last_os_error();
                libc::close(fd);
                return Err(error);
            }

            Ok((fd, u16::from_be(bound.sin_port)))
        }
    }

```

`Connection` holds `out`, the bytes waiting to be written, and `out_pos`, how many of
them have already been written. Advancing `out_pos` instead of removing written bytes
from the front of the vector avoids moving the remaining bytes after every partial
write.

`bind_listener` wraps its whole body in one `unsafe` block, with a comment explaining
that every pointer passed to the C functions refers to a stack value that outlives the
call. Each step checks the return value, closes the socket on failure, and returns
`io::Error::last_os_error()`, which reads `errno`. `address.sin_port = port.to_be()`
converts the port to network byte order, as chapter 51 described.

Binding to port 0 and reading the result back with `getsockname` gives the test a free
port without guessing.

### The event loop

```rust
    pub fn event_loop(epfd: i32, listen_fd: i32, shutdown: &AtomicBool) -> io::Result<()> {
        epoll_add(epfd, listen_fd, libc::EPOLLIN as u32)?;

        let mut connections: HashMap<i32, Connection> = HashMap::new();
        let mut events = vec![libc::epoll_event { events: 0, u64: 0 }; MAX_EVENTS];

        while !shutdown.load(Ordering::Relaxed) {
            // SAFETY: `events` is a valid, writable buffer of MAX_EVENTS entries.
            let ready = unsafe {
                libc::epoll_wait(
                    epfd,
                    events.as_mut_ptr(),
                    events.len() as i32,
                    EPOLL_TIMEOUT_MS,
                )
            };

            if ready < 0 {
                let error = io::Error::last_os_error();
                if error.raw_os_error() == Some(libc::EINTR) {
                    continue;
                }
                return Err(error);
            }

            for event in &events[..ready as usize] {
                let fd = event.u64 as i32;
                if fd == listen_fd {
                    accept_ready(epfd, listen_fd, &mut connections)?;
                    continue;
                }

                let readable = event.events & (libc::EPOLLIN as u32) != 0;
                let writable = event.events & (libc::EPOLLOUT as u32) != 0;

                if readable && !read_into(fd, &mut connections)? {
                    continue; // connection closed
                }
                if writable && connections.contains_key(&fd) {
                    flush(fd, &mut connections)?;
                }
                if connections.contains_key(&fd) {
                    update_interest(epfd, fd, &mut connections)?;
                }
            }
        }

        Ok(())
    }

```

The loop registers the listener for `EPOLLIN`, allocates an event array of 64 entries
once, and waits with a timeout of 100 ms so that it can check the shutdown flag
regularly. `EINTR`, a wait interrupted by a signal, is not an error, so the loop retries.

Each event carries the file descriptor in its `u64` field, stored there when the
descriptor was registered. The loop dispatches on whether it is the listener, then
handles readability and writability for client sockets. `read_into` returns `false`
when it has closed the connection, and the `continue` skips the remaining steps for a
descriptor that no longer exists.

### Accepting and reading

```rust
    /// `SOCK_NONBLOCK` means a client socket can never block the loop.
    fn accept_ready(
        epfd: i32,
        listen_fd: i32,
        connections: &mut HashMap<i32, Connection>,
    ) -> io::Result<()> {
        loop {
            // SAFETY: a null sockaddr is explicitly allowed for accept.
            let client = unsafe {
                libc::accept4(
                    listen_fd,
                    std::ptr::null_mut(),
                    std::ptr::null_mut(),
                    libc::SOCK_NONBLOCK,
                )
            };

            if client < 0 {
                if would_block() {
                    return Ok(());
                }
                return Err(io::Error::last_os_error());
            }

            epoll_add(epfd, client, libc::EPOLLIN as u32)?;
            connections.insert(client, Connection::default());
        }
    }

    /// Drain readable bytes into the connection's output buffer.
    ///
    /// Returns `false` when the peer closed the connection.
    fn read_into(fd: i32, connections: &mut HashMap<i32, Connection>) -> io::Result<bool> {
        let mut buffer = [0u8; 4096];
        loop {
            // SAFETY: `buffer` is a valid writable region of `buffer.len()` bytes.
            let read =
                unsafe { libc::read(fd, buffer.as_mut_ptr() as *mut libc::c_void, buffer.len()) };

            if read == 0 {
                close_connection(fd, connections);
                return Ok(false);
            }
            if read < 0 {
                if would_block() {
                    break;
                }
                close_connection(fd, connections);
                return Err(io::Error::last_os_error());
            }

            if let Some(connection) = connections.get_mut(&fd) {
                connection.out.extend_from_slice(&buffer[..read as usize]);
            }
        }

        flush(fd, connections)?;
        Ok(true)
    }

```

`accept_ready` accepts in a loop until `EAGAIN`, because one readiness notification can
stand for several queued connections. `accept4` with `SOCK_NONBLOCK` creates each client
socket already non-blocking, which avoids a separate `fcntl` call and the window in
which the socket would still be blocking.

`read_into` also loops until `EAGAIN`, appending each chunk to the connection's output
buffer, and then calls `flush` to echo as much as the socket will accept immediately.

### Writing and updating interest

```rust
    /// Write as much of the buffered reply as the socket accepts.
    fn flush(fd: i32, connections: &mut HashMap<i32, Connection>) -> io::Result<()> {
        let Some(connection) = connections.get_mut(&fd) else {
            return Ok(());
        };

        while connection.has_pending_output() {
            let remaining = connection.out.len() - connection.out_pos;
            // SAFETY: the slice is valid for `remaining` bytes.
            let written = unsafe {
                libc::write(
                    fd,
                    connection.out[connection.out_pos..].as_ptr() as *const libc::c_void,
                    remaining,
                )
            };

            if written < 0 {
                if would_block() {
                    // Keep the rest buffered; EPOLLOUT will drive the next attempt.
                    return Ok(());
                }
                return Err(io::Error::last_os_error());
            }
            connection.out_pos += written as usize;
        }

        connection.out.clear();
        connection.out_pos = 0;
        Ok(())
    }

    /// Ask for `EPOLLOUT` only while a reply is still buffered.
    fn update_interest(
        epfd: i32,
        fd: i32,
        connections: &mut HashMap<i32, Connection>,
    ) -> io::Result<()> {
        let pending = connections
            .get(&fd)
            .is_some_and(Connection::has_pending_output);
        let events = if pending {
            (libc::EPOLLIN | libc::EPOLLOUT) as u32
        } else {
            libc::EPOLLIN as u32
        };
        epoll_modify(epfd, fd, events)
    }

    fn close_connection(fd: i32, connections: &mut HashMap<i32, Connection>) {
        connections.remove(&fd);
        // SAFETY: `fd` is owned by us and open at this point.
        unsafe {
            libc::close(fd);
        }
    }

    fn epoll_add(epfd: i32, fd: i32, events: u32) -> io::Result<()> {
        let mut event = libc::epoll_event {
            events,
            u64: fd as u64,
        };
        // SAFETY: `event` outlives the call.
        if unsafe { libc::epoll_ctl(epfd, libc::EPOLL_CTL_ADD, fd, &mut event) } < 0 {
            Err(io::Error::last_os_error())
        } else {
            Ok(())
        }
    }

    fn epoll_modify(epfd: i32, fd: i32, events: u32) -> io::Result<()> {
        let mut event = libc::epoll_event {
            events,
            u64: fd as u64,
        };
        // SAFETY: `event` outlives the call.
        if unsafe { libc::epoll_ctl(epfd, libc::EPOLL_CTL_MOD, fd, &mut event) } < 0 {
            Err(io::Error::last_os_error())
        } else {
            Ok(())
        }
    }

    fn would_block() -> bool {
        matches!(
            io::Error::last_os_error().raw_os_error(),
            Some(libc::EAGAIN)
        )
    }
}
```

`flush` writes from `out_pos` until the buffer is empty or the socket returns `EAGAIN`.
On `EAGAIN` it returns `Ok(())` with the remainder still buffered. When everything has
been written it clears the vector, which keeps its capacity for the next reply.

`update_interest` computes the event mask from `has_pending_output` and calls
`EPOLL_CTL_MOD`. Asking for `EPOLLOUT` only while output is pending is the difference
between a loop that sleeps and a loop that spins: an idle socket is almost always
writable, and a level-triggered `EPOLLOUT` on it would wake `epoll_wait` immediately,
forever.

`would_block` compares `errno` with `EAGAIN`. On Linux, `EWOULDBLOCK` has the same value.

### Startup and the test

```rust
#[cfg(target_os = "linux")]
fn main() {
    use std::sync::atomic::AtomicBool;

    let port: u16 = std::env::args()
        .nth(1)
        .and_then(|argument| argument.parse().ok())
        .unwrap_or(9000);

    let (listen_fd, bound_port) = linux::bind_listener(port).expect("failed to bind");
    // SAFETY: epoll_create1 takes flags and returns an fd or -1.
    let epfd = unsafe { libc::epoll_create1(0) };
    assert!(epfd >= 0, "epoll_create1 failed");

    // A write to a peer that vanished raises SIGPIPE, which by default kills the
    // process. Servers ignore it and handle EPIPE from write instead.
    // SAFETY: installing SIG_IGN is a single-threaded startup action.
    unsafe {
        libc::signal(libc::SIGPIPE, libc::SIG_IGN);
    }

    println!("epoll echo server listening on 127.0.0.1:{bound_port} (Ctrl-C to stop)");

    let shutdown = AtomicBool::new(false);
    let result = linux::event_loop(epfd, listen_fd, &shutdown);
    // SAFETY: both fds are owned by this process.
    unsafe {
        libc::close(epfd);
        libc::close(listen_fd);
    }

    if let Err(error) = result {
        eprintln!("event loop error: {error}");
        std::process::exit(1);
    }
}

#[cfg(not(target_os = "linux"))]
fn main() {
    eprintln!("epoll_echo requires Linux; use kqueue or IOCP on this platform.");
}

#[cfg(all(test, target_os = "linux"))]
mod tests {
    use super::linux;
    use std::io::{Read, Write};
    use std::net::TcpStream;
    use std::sync::Arc;
    use std::sync::atomic::{AtomicBool, Ordering};
    use std::thread;

    #[test]
    fn echoes_a_message_through_the_event_loop() {
        let (listen_fd, port) = linux::bind_listener(0).expect("bind");
        // SAFETY: epoll_create1 takes flags and returns an fd or -1.
        let epfd = unsafe { libc::epoll_create1(0) };
        assert!(epfd >= 0, "epoll_create1 failed");

        let shutdown = Arc::new(AtomicBool::new(false));
        let server_shutdown = Arc::clone(&shutdown);
        let server = thread::spawn(move || {
            let result = linux::event_loop(epfd, listen_fd, &server_shutdown);
            // SAFETY: the test owns both fds.
            unsafe {
                libc::close(epfd);
                libc::close(listen_fd);
            }
            result
        });

        let mut client = TcpStream::connect(("127.0.0.1", port)).expect("connect");
        client.write_all(b"epoll echo").expect("write");
        let mut echoed = [0u8; 10];
        client.read_exact(&mut echoed).expect("read echo");
        assert_eq!(&echoed, b"epoll echo");

        shutdown.store(true, Ordering::Relaxed);
        drop(client);
        let result = server.join().expect("server thread panicked");
        assert!(result.is_ok(), "event loop returned {result:?}");
    }
}
```

`main` ignores `SIGPIPE`. By default, writing to a socket whose peer has closed delivers
`SIGPIPE`, which terminates the process. With the signal ignored, the write fails with
`EPIPE` instead, which the program can handle.

The test runs the event loop on a thread, connects a standard `TcpStream` client, and
checks that ten bytes come back. It then sets the shutdown flag, and the loop exits at
its next 100 ms timeout. The two descriptors are closed on the server thread, and the
loop's result is checked.

## Intuition

**Events for one client that sends `epoll echo`**

| `epoll_wait` result | handler | effect |
|---|---|---|
| listener readable | `accept_ready` | `accept4` returns client fd 5, registered for `EPOLLIN`; second `accept4` returns `EAGAIN` |
| fd 5 readable | `read_into` | `read` returns 10 bytes into `out`; next `read` returns `EAGAIN`; `flush` writes 10 bytes and clears `out` |
| | `update_interest` | no pending output, so interest stays `EPOLLIN` |
| timeout, no events | | shutdown flag checked, still `false` |
| fd 5 readable | `read_into` | `read` returns 0 after the test drops the client; the connection is closed |

If the client stopped reading and the socket's send buffer filled, `flush` would get
`EAGAIN` with bytes left in `out`, `update_interest` would add `EPOLLOUT`, and the next
writable event would call `flush` again.

## Time and Space Complexity

| Resource | Cost |
|---|---|
| Per `epoll_wait` | `O(ready descriptors)`, independent of the number of idle connections |
| Per connection | one `Connection` in a `HashMap` and one kernel socket; no thread |
| Per event | a `read` or `write` system call per chunk, plus one `epoll_ctl` per event |
| Memory for output | proportional to bytes received but not yet written |

## Limitations

**One client's error stops the server.** `read_into` and `flush` return `Err` for any
failure other than `EAGAIN`, and `event_loop` propagates it with `?`. A client that
resets its connection, which makes `write` fail with `ECONNRESET` or `EPIPE`, therefore
ends the loop for every client. Errors on a client socket should close that connection
and let the loop continue; only errors on the listener or on `epoll` itself are fatal.

**No backpressure.** `read_into` reads until `EAGAIN` and appends everything to `out`,
even when `flush` could not write the previous reply. A client that sends continuously
and never reads makes the server's memory grow without bound. The loop should stop
reading from a connection, by removing `EPOLLIN`, while its output buffer is above a
limit.

**Raw descriptors have no owner.** File descriptors are plain `i32` values. When
`event_loop` returns an error, the client descriptors in `connections` are never closed.
`std::os::fd::OwnedFd` closes its descriptor on drop, and storing one in `Connection`
would make the cleanup automatic.

**An `epoll_ctl` call per event.** `update_interest` issues `EPOLL_CTL_MOD` after every
event even when the mask has not changed. Tracking the registered mask in `Connection`
and calling `epoll_ctl` only when it changes removes one system call per event.

**`EINTR` is handled only for `epoll_wait`.** A `read` or `write` interrupted by a signal
also fails with `EINTR`, and the code treats that as a fatal error.

**`errno` is read after `close`.** In `read_into`, the error path calls
`close_connection` before `io::Error::last_os_error()`. If `close` changed `errno`, the
reported error would describe the wrong call. Reading the error first avoids the
question.

**Linux only.** macOS and the BSDs provide `kqueue` and Windows provides I/O completion
ports. The `mio` crate abstracts over all three, and Tokio is built on it.

## Summary

- Non-blocking sockets fail with `EAGAIN` instead of waiting, and `epoll_wait` reports
  which sockets are ready, so one thread can serve many connections.
- Level-triggered readiness keeps reporting a socket until it is drained, which tolerates
  handlers that do not read everything at once.
- A per-connection output buffer with a position index survives partial writes, and
  `EPOLLOUT` should be registered only while output is pending.
- Each `unsafe` call into `libc` states why its pointers are valid, and every return value
  is checked against `-1` and converted with `io::Error::last_os_error`.
- Production event loops close only the failing connection, apply backpressure, own
  their descriptors with `OwnedFd`, and are usually built on `mio`.

## References

- Linux manual pages [`epoll(7)`](https://man7.org/linux/man-pages/man7/epoll.7.html), [`accept4(2)`](https://man7.org/linux/man-pages/man2/accept4.2.html), and [`socket(7)`](https://man7.org/linux/man-pages/man7/socket.7.html).
- Michael Kerrisk, *The Linux Programming Interface*, No Starch Press, 2010, Chapter 63,
  "Alternative I/O Models".
- Standard library, [`std::os::fd::OwnedFd`](https://doc.rust-lang.org/std/os/fd/struct.OwnedFd.html).
- The `mio` crate, [documentation](https://docs.rs/mio/latest/mio/).
