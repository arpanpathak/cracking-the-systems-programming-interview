<img class="plate" src="art/ch27.png" alt="Taper, the robot who is the closer of the line, beside two telegraph poles whose wire is being lowered, with a sixty-second hourglass hanging from it">

# Closing TCP connections

<div class="covers" markdown="1">

This chapter covers

- Independent full-duplex teardown via TCP's four-way `FIN`/`ACK` handshake
- Kernel state transitions for active close (`FIN_WAIT1`, `FIN_WAIT2`, `TIME_WAIT`) and passive close (`CLOSE_WAIT`, `LAST_ACK`), inspected via `/proc/net/tcp`
- `TIME_WAIT` protocol invariants, the 60-second Linux 2 MSL duration, and ephemeral port exhaustion on high-rate clients
- `SO_REUSEADDR` semantics for rebinding a listening port occupied by `TIME_WAIT` entries
- `CLOSE_WAIT` descriptor accumulation caused by servers that fail to close peer-terminated sockets
- Abrupt termination via TCP `RST` when closing a socket with unread receive-buffer data or `SO_LINGER`

</div>

A TCP connection is a full-duplex byte stream whose teardown is asymmetric and outlives user-space descriptor closure. When an application calls `shutdown` or `close`, the kernel transitions the underlying transmission control block (TCB) through a deterministic state machine that can persist for 60 seconds after the process drops the socket (`TIME_WAIT`), or indefinitely if a server neglects to close a peer-terminated descriptor (`CLOSE_WAIT`). Failing to account for these kernel states manifests in production as ephemeral port exhaustion (`EADDRNOTAVAIL`), restart failures (`EADDRINUSE`), descriptor exhaustion (`EMFILE`), and unexpected connection resets (`ECONNRESET`).

The reference program `tcp_close` exercises these kernel transitions directly inside a Linux container by parsing `/proc/net/tcp` after each protocol step, reproducing `CLOSE_WAIT` leaks, `TIME_WAIT` bind conflicts, and unread-buffer resets.

## 27.1 Two directions, two `FIN`s

Because TCP carries two independent, full-duplex byte streams, each direction terminates separately. An endpoint with no further payload to transmit emits a **`FIN`** segment, which the peer acknowledges with an **`ACK`**; data may continue flowing in the reverse direction (a **half-closed** connection) until the peer transmits its own `FIN` and receives the final `ACK`. Orderly teardown therefore requires four segments: `FIN`, `ACK`, `FIN`, `ACK`.

The endpoint transmitting the first `FIN` executes the **active close**; its peer executes the **passive close**. The two endpoints traverse disjoint subsets of the TCP state machine (Figure 27.1):

| Side | State | Waiting for |
|---|---|---|
| active | `FIN_WAIT1` | the `ACK` of its `FIN` |
| active | `FIN_WAIT2` | the peer's `FIN` |
| active | `TIME_WAIT` | a fixed time, 60 seconds on Linux, before the connection is forgotten |
| passive | `CLOSE_WAIT` | its own program to close the socket |
| passive | `LAST_ACK` | the `ACK` of its `FIN` |

<figure>
<img src="figures/ch27-close.svg" alt="The client, closing first, goes from ESTABLISHED to FIN_WAIT1 and sends FIN. The server moves to CLOSE_WAIT until its program closes, and sends ACK; the client moves to FIN_WAIT2. The server moves to LAST_ACK and sends FIN; the client moves to TIME_WAIT, 60 seconds on Linux, and sends ACK; the server is CLOSED. After TIME_WAIT the client is CLOSED too.">
<figcaption><b>Figure 27.1</b> The four segments of a close, and the state each side is in between them.</figcaption>
</figure>

Two of these states depend on local events rather than network arrivals: `CLOSE_WAIT` persists until the local application closes its socket descriptor, and `TIME_WAIT` persists until a kernel timer expires. Sections 27.2 and 27.3 analyze both states and their operational failure modes.

### 27.1.1 Reading the states

Linux exposes active IPv4 TCP control blocks through `/proc/net/tcp`, emitting one line per socket. The second and third columns encode the local and remote endpoints in hexadecimal (for example, `0100007F:1F90` for `127.0.0.1:8080`), and the fourth column encodes the TCP state as a hexadecimal enumeration from `01` (`ESTABLISHED`) through `0B` (`CLOSING`).

The parser helpers extract endpoint port pairs and map hexadecimal state codes to canonical TCP state names:

```rust
{{#include ../../rust-interview-lab/src/bin/tcp_close.rs:8:70}}
    // ...
}
```

`entries` skips the header row, tokenizes each record on whitespace, and extracts the three target columns; the `?` operator inside `filter_map` discards malformed lines. Because all test traffic traverses `127.0.0.1`, the `(local_port, remote_port)` pair uniquely identifies each socket endpoint.

`state` queries a single endpoint's state, and `census` aggregates state counts across all sockets associated with a server port:

```rust
mod linux {
    // ...
{{#include ../../rust-interview-lab/src/bin/tcp_close.rs:72:98}}
    // ...
}
```

Once the kernel reclaims a TCB, its entry disappears from `/proc/net/tcp` and `state` reports `gone`. `connected` returns both ends of a loopback TCP pair so a single process can drive and inspect both endpoints deterministically.

### 27.1.2 A close, step by step

The first scenario executes an orderly half-close sequence: the client closes its write half via `shutdown(Write)`, the server drains until EOF and transmits a reply, and both endpoints drop their descriptors. A 50 ms delay after each step ensures loopback segment delivery completes before `/proc/net/tcp` is sampled:

```text
1. An orderly close, client first, with a half-close

  step                                   client       server
  connected                              ESTABLISHED  ESTABLISHED
  client shutdown(Write): FIN sent       FIN_WAIT2    CLOSE_WAIT
  server read to end, wrote a reply      FIN_WAIT2    CLOSE_WAIT
  server dropped its socket: FIN sent    TIME_WAIT    gone
  client read the reply, dropped         TIME_WAIT    gone
```

`FIN_WAIT1` is transient on loopback because the peer's `ACK` arrives within microseconds, advancing the client TCB directly into `FIN_WAIT2` before the poll executes; over a wide-area link with non-trivial round-trip latency, `FIN_WAIT1` is directly observable.

Row three demonstrates half-closed duplex operation: the client's transmit direction is closed while the server's remains open to deliver the response. When the server drops its socket, the server TCB transmits `FIN`, transitions through `LAST_ACK`, and is reclaimed upon receiving the client's final `ACK`. The client TCB enters `TIME_WAIT` and persists in kernel memory even after the client drops its descriptor, demonstrating that `TIME_WAIT` is owned strictly by the kernel network stack rather than the application process.

Animation 27.1 traces this orderly teardown followed by a server that leaks descriptors in `CLOSE_WAIT`.

<figure class="anim">
<video class="motion" src="figures/ch27-close.mp4" autoplay loop muted playsinline preload="metadata" aria-label="A client robot and a server robot joined by a wire, each with its TCP state above it. The client's shutdown sends FIN; the server's kernel acknowledges it, and the states become FIN_WAIT2 and CLOSE_WAIT. The server's read returns 0, it writes a reply that crosses to the client, and it drops its socket, which sends FIN. The server goes through LAST_ACK to gone, and the client acknowledges and enters TIME_WAIT, where a 60-second clock runs after the client drops its socket. In a second run the server never drops its sockets: five clients connect and close, each leaves a FIN_WAIT2 on the client side and a CLOSE_WAIT on the server, and the server's count of open descriptors climbs toward its limit." data-chapters="[[0.0, &quot;FIN&quot;], [15.42, &quot;reply&quot;], [23.42, &quot;second FIN&quot;], [42.42, &quot;leak&quot;]]"><img src="figures/ch27-close.gif" alt="A client robot and a server robot joined by a wire, each with its TCP state above it. The client's shutdown sends FIN; the server's kernel acknowledges it, and the states become FIN_WAIT2 and CLOSE_WAIT. The server's read returns 0, it writes a reply that crosses to the client, and it drops its socket, which sends FIN. The server goes through LAST_ACK to gone, and the client acknowledges and enters TIME_WAIT, where a 60-second clock runs after the client drops its socket. In a second run the server never drops its sockets: five clients connect and close, each leaves a FIN_WAIT2 on the client side and a CLOSE_WAIT on the server, and the server's count of open descriptors climbs toward its limit."></video>
<figcaption><b>Animation 27.1</b> Each side's <code>FIN</code> closes one direction. A server that never closes leaves every connection in <code>CLOSE_WAIT</code>, holding a descriptor.</figcaption>
</figure>

## 27.2 `TIME_WAIT`

The active-closing endpoint retains its TCB in `TIME_WAIT` before releasing the connection's four-tuple. This mandatory holding interval enforces two transport-layer safety invariants:

- **Reliable delivery of the final `ACK`.** If the final `ACK` is lost in transit, the passive peer remains in `LAST_ACK` and retransmits its `FIN`. An active endpoint still in `TIME_WAIT` recognizes the retransmitted `FIN` and re-emits the `ACK`. Had it purged the TCB immediately, it would reply with `RST`, causing the peer to observe an error on an orderly close.
- **Isolation from delayed duplicate segments.** Packets delayed in the network can arrive after connection teardown. If a new connection immediately reused the identical four-tuple `(local IP, local port, remote IP, remote port)`, stale segments from the previous incarnation could pass sequence checks and corrupt the new byte stream. `TIME_WAIT` quarantines the four-tuple until delayed segments expire.

RFC 9293 specifies `TIME_WAIT` as twice the maximum segment lifetime (`2 MSL`); Linux hardcodes `TCP_TIMEWAIT_LEN` to 60 seconds.

### 27.2.1 The cost: ports on a busy client

A `TIME_WAIT` control block occupies only a few hundred bytes of kernel memory. The constraining resource is four-tuple cardinality. For every outbound connection to a fixed `(remote IP, remote port)`, the client kernel selects a local port from the **ephemeral port range** (`net.ipv4.ip_local_port_range`, defaulting to 32,768 through 60,999 on Linux, yielding 28,232 ports). When the client performs the active close, each port remains pinned in `TIME_WAIT` for 60 seconds, bounding sustained connection churn to roughly 28,232 / 60 ≈ 470 new connections per second per destination endpoint (Figure 27.2). Exceeding this rate exhausts the ephemeral pool and causes `connect` to fail with `EADDRNOTAVAIL`.

<figure>
<img src="figures/ch27-ports.svg" alt="A client at 10.0.0.5 with ephemeral ports 32768 to 60999, 28,232 ports, has connections from ports 40001 and 40002 to the server 10.0.0.9:443, each in TIME_WAIT with about 60 seconds left. With 28,232 such four-tuples held at once, the next connect fails with EADDRNOTAVAIL. The server uses its one port for every connection.">
<figcaption><b>Figure 27.2</b> Each closed connection holds its four values for 60 seconds. On the client, the free values run out with the ephemeral ports.</figcaption>
</figure>

Three architectural mitigations address client-side ephemeral port exhaustion:

- **Connection reuse.** Persistent HTTP keep-alive connections or a bounded client connection pool (Chapter 29) amortize connection setup and eliminate per-request `TIME_WAIT` churn.
- **Server-initiated active close.** Shifting active close onto the server places `TIME_WAIT` entries on the server side, where all connections share a single listening port and are distinguished by distinct client endpoints.
- **`net.ipv4.tcp_tw_reuse`.** Enabling this Linux sysctl permits outbound `connect` calls to reclaim a `TIME_WAIT` four-tuple safely after one second when TCP timestamps (`RFC 7323`) guarantee monotonically increasing timestamps relative to the closed incarnation.

### 27.2.2 Binding a port with connections in `TIME_WAIT`

When a server initiates active close and subsequently restarts within 60 seconds, residual `TIME_WAIT` entries still occupy its listening port. By default, `bind` rejects a new listening socket on that port with `EADDRINUSE`. Setting **`SO_REUSEADDR`** instructs the kernel to permit `bind` whenever no active `LISTEN` socket holds the identical `(IP, port)` pair. Because Rust's `TcpListener::bind` enables `SO_REUSEADDR` automatically on Unix, `tcp_close` invokes raw `libc` socket primitives to contrast both configurations:

```rust
unsafe extern "C" {
    fn socket(domain: c_int, ty: c_int, protocol: c_int) -> c_int; // AF_INET, SOCK_STREAM, 0
    fn setsockopt(
        fd: c_int,
        level: c_int,          // SOL_SOCKET
        name: c_int,           // SO_REUSEADDR
        value: *const c_void,  // points at the option's value, a c_int here
        len: socklen_t,        // its size in bytes
    ) -> c_int;
    fn bind(fd: c_int, addr: *const sockaddr, len: socklen_t) -> c_int;
}
```

`sockaddr` serves as the polymorphic C address header; an IPv4 endpoint is populated in `sockaddr_in` and passed as a `*const sockaddr` pointer alongside its byte length:

```rust
mod linux {
    // ...
{{#include ../../rust-interview-lab/src/bin/tcp_close.rs:100:141}}
    // ...
}
```

The third scenario closes a connection server-first, drops the listener, and attempts to rebind the port with `SO_REUSEADDR` disabled and enabled:

```text
3. TIME_WAIT on the server's port, and binding it again

  server closed first, then the client: {"TIME_WAIT": 1}
  bind port again, SO_REUSEADDR false: Address already in use (os error 98)
  bind port again, SO_REUSEADDR true : bound
```

A single residual `TIME_WAIT` entry suffices to block an unconfigured `bind` call.

## 27.3 `CLOSE_WAIT`

Upon receiving a peer's `FIN`, the passive endpoint transitions to `CLOSE_WAIT` and remains there indefinitely until its owning process invokes `close` (or `shutdown(Write)`). The kernel cannot unilaterally exit `CLOSE_WAIT`, because only the application knows whether it still intends to transmit response bytes before closing its half of the stream.

A server that neglects to drop accepted sockets after clients disconnect accumulates `CLOSE_WAIT` sockets for the lifetime of the process, pinning one file descriptor per leaked connection. Common root causes include read handlers that ignore a `0`-byte EOF return, connection maps that omit eviction on error paths, and reference-counting cycles (`Rc`/`Arc`) that retain socket owners indefinitely.

`leaky_server` reproduces this pathology by retaining five accepted sockets in a `Vec` while all five clients connect and immediately close:

```rust
mod linux {
    // ...
{{#include ../../rust-interview-lab/src/bin/tcp_close.rs:143:157}}
    // ...
}
```

```text
2. A server that never closes what clients closed

  while the server keeps 5 sockets: {"CLOSE_WAIT": 5, "FIN_WAIT2": 5}
  after the server drops them:      {"TIME_WAIT": 5}
```

All five connections stalled mid-teardown: the clients remained in `FIN_WAIT2` awaiting the server's `FIN`, while the server held five sockets in `CLOSE_WAIT`. Dropping the server's `Vec` transmitted five `FIN` segments and transitioned the client endpoints into `TIME_WAIT`. Because the clients had already closed their local descriptors, Linux would otherwise bound such orphaned `FIN_WAIT2` sockets with `net.ipv4.tcp_fin_timeout` (defaulting to 60 seconds) before reclaiming them.

In production diagnostics, `ss -tan state close-wait` enumerates all `CLOSE_WAIT` sockets across the host. A monotonically increasing `CLOSE_WAIT` count indicates a descriptor leak in the owning server process that will eventually terminate new connections with `EMFILE` (Section 24.1).

## 27.4 Reset instead of `FIN`

When a process closes a TCP socket whose kernel receive buffer still holds unread bytes, the kernel aborts orderly teardown and transmits a **reset (`RST`)** segment instead of a `FIN`, signaling data loss to the peer. The peer's subsequent `read` fails with `ECONNRESET` ("Connection reset by peer"), and any unread bytes queued in the peer's receive buffer are discarded:

```rust
mod linux {
    // ...
{{#include ../../rust-interview-lab/src/bin/tcp_close.rs:159:169}}
}
```

```text
4. Closing with unread data

  client read failed: Connection reset by peer (os error 104)
```

This mechanism causes a subtle failure mode in HTTP servers. If a server rejects an oversized request by writing an HTTP `413` response and immediately calling `close` while unread request-body bytes remain in the kernel receive buffer, the resulting `RST` can overtake or flush the response on the client, causing the client to report `ECONNRESET` instead of reading the HTTP error status. Production servers prevent this race via a **lingering close**: after writing the error response, the server invokes `shutdown(Write)` to transmit `FIN`, drains and discards incoming request bytes for a bounded interval, and only then closes the descriptor.

An application can also trigger an immediate `RST` explicitly by enabling `SO_LINGER` with `l_onoff = 1` and `l_linger = 0` before closing. This bypasses `TIME_WAIT` and forces `ECONNRESET` on the peer; although edge proxies occasionally use it to shed abusive connections rapidly, it discards unsent data in the send buffer and violates orderly transport semantics.

## 27.5 The complete program

<p class="listing"><b>Listing 27.1</b> The states of a closing connection, read from <code>/proc/net/tcp</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/tcp_close.rs">src/bin/tcp_close.rs</a></p>

```rust
{{#include ../../rust-interview-lab/src/bin/tcp_close.rs}}
```

```text
$ cargo run --bin tcp_close
1. An orderly close, client first, with a half-close

  step                                   client       server
  connected                              ESTABLISHED  ESTABLISHED
  client shutdown(Write): FIN sent       FIN_WAIT2    CLOSE_WAIT
  server read to end, wrote a reply      FIN_WAIT2    CLOSE_WAIT
  server dropped its socket: FIN sent    TIME_WAIT    gone
  client read the reply, dropped         TIME_WAIT    gone

2. A server that never closes what clients closed

  while the server keeps 5 sockets: {"CLOSE_WAIT": 5, "FIN_WAIT2": 5}
  after the server drops them:      {"TIME_WAIT": 5}

3. TIME_WAIT on the server's port, and binding it again

  server closed first, then the client: {"TIME_WAIT": 1}
  bind port again, SO_REUSEADDR false: Address already in use (os error 98)
  bind port again, SO_REUSEADDR true : bound

4. Closing with unread data

  client read failed: Connection reset by peer (os error 104)
```

## 27.6 Questions that come up

**"A server has 30,000 sockets in `TIME_WAIT`. Is that a problem?"**
Rarely on a server. Each `TIME_WAIT` entry occupies a few hundred bytes of kernel memory and all share the server's listening port without consuming ephemeral ports. The same count on a client targeting a single upstream endpoint exhausts the 28,232-port ephemeral range and causes `EADDRNOTAVAIL`.

**"A server has 3,000 sockets in `CLOSE_WAIT` and the number keeps rising. What happened?"**
Remote peers closed their write directions, and the server process failed to close its descriptors. Audit read loops for ignored `0`-byte EOF returns, connection registries that omit cleanup on error paths, and reference cycles retaining `TcpStream` instances.

**"Why not shorten `TIME_WAIT`?"**
Linux fixes `TCP_TIMEWAIT_LEN` at 60 seconds as a compile-time kernel constant to uphold RFC 9293's 2 MSL guarantee. Eliminating client-side `TIME_WAIT` churn is properly addressed through persistent connection pooling or `net.ipv4.tcp_tw_reuse` with TCP timestamps enabled.

**"What is the difference between `shutdown(Write)` and `close`?"**
`shutdown(Write)` transmits a `FIN` to close the outbound byte stream while keeping the descriptor open for reading (and affects all duplicated descriptors referencing that socket). `close` removes a single descriptor table entry; the kernel transmits `FIN` (or `RST` if unread data remains) only when the open file description's reference count reaches zero.

**"Both sides send `FIN` at the same moment. What happens?"**
Both endpoints transition from `FIN_WAIT1` into the simultaneous-close state `CLOSING` upon receiving the peer's `FIN`, and then into `TIME_WAIT` upon receiving the peer's `ACK`.

<div class="summary" markdown="1">

## Summary

- Each direction of a full-duplex TCP connection terminates independently via `FIN` and `ACK`, requiring four segments for complete teardown.
- Active close traverses `FIN_WAIT1`, `FIN_WAIT2`, and `TIME_WAIT`; passive close traverses `CLOSE_WAIT` and `LAST_ACK`.
- `TIME_WAIT` lasts 60 seconds on Linux (`2 MSL`) to retransmit lost final `ACK`s and prevent delayed duplicate segments from corrupting a reused four-tuple.
- On a high-rate client, `TIME_WAIT` pins ephemeral ports, capping throughput at roughly 470 new connections per second per destination unless connections are reused.
- `SO_REUSEADDR` permits a restarting server to bind a port still referenced by `TIME_WAIT` entries; `TcpListener::bind` enables it automatically on Unix.
- `CLOSE_WAIT` persists until the local application closes the socket; unbounded `CLOSE_WAIT` growth signals a descriptor leak culminating in `EMFILE`.
- Closing a socket with unread receive-buffer bytes (or `SO_LINGER` with a zero timeout) transmits `RST` instead of `FIN`, surfacing as `ECONNRESET` on the peer.

</div>

## Exercises

1. Insert `thread::sleep(Duration::from_secs(61))` at the end of scenario 1 and re-query the client's `/proc/net/tcp` state. Confirm that the `TIME_WAIT` entry has been reclaimed.
2. Invert `leaky_server` so the server performs active close while clients retain their descriptors open. Identify which side enters `FIN_WAIT2`, which enters `CLOSE_WAIT`, and which transitions to `TIME_WAIT` upon client drop.
3. Open and close 1,000 loopback connections sequentially from the client side and print `census`; repeat with the server closing first and compare the resulting state distributions.
4. In `close_with_unread_data`, drain the client's bytes on the server prior to dropping the server socket. Record the new return value of the client's `read`.
5. Configure `SO_LINGER` with `{ l_onoff: 1, l_linger: 0 }` via `libc::setsockopt` on the server socket in scenario 1 before dropping it. Identify which TCP states vanish and what error the client's `read` reports.
