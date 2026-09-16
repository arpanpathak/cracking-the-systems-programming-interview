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

<p class="listing"><span class="listing-label">Listing 53.1</span> Connection state and the listening socket. <code>src/bin/epoll_echo.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/epoll_echo.rs">read the file on GitHub</a></p>

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

<p class="listing"><span class="listing-label">Listing 53.2</span> The event loop. <code>src/bin/epoll_echo.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/epoll_echo.rs">read the file on GitHub</a></p>

The loop registers the listener for `EPOLLIN`, allocates an event array of 64 entries
once, and waits with a timeout of 100 ms so that it can check the shutdown flag
regularly. `EINTR`, a wait interrupted by a signal, is not an error, so the loop retries.

Each event carries the file descriptor in its `u64` field, stored there when the
descriptor was registered. The loop dispatches on whether it is the listener, then
handles readability and writability for client sockets. `read_into` returns `false`
when it has closed the connection, and the `continue` skips the remaining steps for a
descriptor that no longer exists.

### Accepting and reading

<p class="listing"><span class="listing-label">Listing 53.3</span> Accepting and reading. <code>src/bin/epoll_echo.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/epoll_echo.rs">read the file on GitHub</a></p>

`accept_ready` accepts in a loop until `EAGAIN`, because one readiness notification can
stand for several queued connections. `accept4` with `SOCK_NONBLOCK` creates each client
socket already non-blocking, which avoids a separate `fcntl` call and the window in
which the socket would still be blocking.

`read_into` also loops until `EAGAIN`, appending each chunk to the connection's output
buffer, and then calls `flush` to echo as much as the socket will accept immediately.

### Writing and updating interest

<p class="listing"><span class="listing-label">Listing 53.4</span> Writing and updating interest. <code>src/bin/epoll_echo.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/epoll_echo.rs">read the file on GitHub</a></p>

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

<p class="listing"><span class="listing-label">Listing 53.5</span> Startup and the test. <code>src/bin/epoll_echo.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/epoll_echo.rs">read the file on GitHub</a></p>

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
