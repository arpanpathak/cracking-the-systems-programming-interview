<img class="plate" src="art/ch29.png" alt="Dock, the robot who is the harbormaster of the connection pool, beside a rack of numbered moorings, some with boats tied up and one empty, and a tide clock">

# A client connection pool

<div class="covers" markdown="1">

This chapter covers

- Amortizing per-connection overhead (TCP/TLS handshakes, congestion-window slow start, and `TIME_WAIT` port consumption) via persistent reuse
- Bounded concurrency control: enforcing a hard cap on open sockets and a wait deadline for saturated callers
- RAII borrowing via a guard type that returns healthy sockets on drop and discards broken sockets after I/O errors
- LIFO idle-stack reuse and idle-timeout eviction to shrink pool footprint under light load
- Detecting half-closed stale connections via non-blocking `peek` before lending
- Empirical comparison of 2,000 concurrent requests with and without pooling

</div>

Establishing a new TCP connection for every outbound RPC imposes four compounding costs: a TCP three-way handshake (plus a TLS handshake when encrypted), TCP congestion-window slow start, server-side `accept` and descriptor allocation overhead, and a 60-second `TIME_WAIT` entry that rapidly exhausts client ephemeral ports (Chapter 27). A **bounded client connection pool** amortizes these setup and teardown costs by maintaining a capped set of persistent connections, lending them exclusively to calling threads via RAII guards, and reclaiming or evicting them deterministically.

The reference program `conn_pool` implements a thread-safe bounded pool using only the Rust standard library (`Mutex`, `Condvar`, and `Drop`), then benchmarks 2,000 multithreaded requests and verifies capacity limits, idle eviction, and stale-connection detection against a local line-oriented server.

## 29.1 What a new connection costs

Each freshly dialed connection incurs four distinct performance and resource penalties:

- **Handshake latency:** one round trip for the TCP three-way handshake, plus a second round trip for TLS 1.3 (Chapter 28).
- **TCP slow start:** a new connection begins with a minimal initial congestion window and requires multiple round trips to probe link capacity (Section 20.2), whereas a warm persistent connection retains its expanded window.
- **Server-side setup overhead:** `accept`, descriptor allocation, and per-connection worker dispatch.
- **`TIME_WAIT` port pinning:** active closure pins an ephemeral client port for 60 seconds (Section 27.2.1).

Across a 50 ms RTT link, connection handshakes alone add 100 ms to an RPC whose actual application latency is 5 ms.

Unbounded connection retention introduces an opposing hazard: every open socket consumes file descriptors and kernel socket buffers on both client and server, risking `EMFILE` or server overload. A production connection pool therefore enforces four invariants (Figure 29.1):

1. **Bounded capacity:** total open sockets (in-use plus idle) never exceed `max`.
2. **Deterministic return:** dropping a borrowed guard returns the socket to the idle pool unless explicitly marked broken via `discard`.
3. **LIFO reuse:** the most recently returned idle socket is lent first, allowing surplus sockets to age out under low load.
4. **Staleness eviction:** sockets idle beyond `idle_timeout` or closed asynchronously by the server are destroyed rather than lent.

<figure>
<img src="figures/ch29-pool.svg" alt="pool.get() pops the idle stack, newest on top. If that connection is fresh and open it becomes a Pooled guard; if not it is closed as evicted or stale, and the next one is tried. When the stack is empty, if open is below max the pool reserves a slot and connects outside the lock; otherwise the caller waits on a Condvar until a return or the deadline, which gives Err(TimedOut). The guard derefs to TcpStream; dropping it puts the connection back on the idle stack, and discard() after an error closes it and frees the slot.">
<figcaption><b>Figure 29.1</b> One call to <code>get</code>. A caller gets an idle connection, a new one, or waits for a return until its deadline.</figcaption>
</figure>

## 29.2 The pool's state

`Config` specifies the pool's operational bounds, and `Stats` tracks cumulative connects, reuses, evictions, and stale discards:

```rust
{{#include ../../rust-interview-lab/src/bin/conn_pool.rs:8:42}}
```

Idle sockets reside in a `Vec` operated as a LIFO stack, paired with their return timestamps. The `open` counter tracks the total number of sockets currently owned by the pool (both idle and checked out):

```rust
{{#include ../../rust-interview-lab/src/bin/conn_pool.rs:44:68}}
```

The pool maintains the structural invariant `open == idle.len() + checked_out`. Because every mutation of `open` occurs while holding the internal `Mutex`, `get` can decide atomically whether capacity permits dialing a new connection.

`Pooled<'a>` wraps a checked-out `TcpStream` inside an `Option` alongside a shared reference `&'a Pool`. The lifetime parameter `'a` prevents any borrowed handle from outliving the pool at compile time, while `Option` allows `Drop` to move ownership of the stream back into the idle stack.

## 29.3 Borrowing a connection

`get` executes a lock-protected state-machine loop until it acquires a usable socket or exhausts its deadline:

```rust
{{#include ../../rust-interview-lab/src/bin/conn_pool.rs:83:122}}
    // ...
}
```

Each iteration evaluates three branches in priority order:

- **Reuse an idle socket:** `take_idle` pops the most recent healthy socket from the idle stack, or returns `None`.
- **Dial a new socket outside the lock:** if `open < max`, `get` reserves a capacity slot by incrementing `open` under the mutex, releases the mutex immediately, and performs `TcpStream::connect` without holding the lock. Performing blocking network I/O while holding the mutex would serialize all pool operations, preventing concurrent threads from returning healthy sockets. Pre-incrementing `open` guarantees that concurrent callers never violate the `max` bound.
- **Wait with a bounded deadline:** when `open == max`, the caller blocks on `Condvar::wait_timeout` until another thread returns or discards a socket, or until the deadline expires. Because `wait_timeout` atomically releases the mutex while sleeping (Section 16.5) and may return spuriously, the enclosing `loop` re-evaluates pool state on every wakeup.

If the deadline expires before a slot opens, `get` returns `io::ErrorKind::TimedOut`. Bounding wait time transforms downstream saturation into explicit backpressure rather than unbounded thread starvation (Chapter 17).

If `TcpStream::connect` fails after reserving a slot, `connect` decrements `open` under the mutex and notifies one waiting thread so the reserved capacity is not leaked:

```rust
impl Pool {
    // ...
{{#include ../../rust-interview-lab/src/bin/conn_pool.rs:141:164}}
    // ...
}
```

## 29.4 Giving it back

Implementing `Drop` on `Pooled` guarantees that every borrowed connection returns to the pool automatically across normal returns, early `?` propagation, and stack unwinding:

```rust
impl Pool {
    // ...
{{#include ../../rust-interview-lab/src/bin/conn_pool.rs:166:192}}
}
```

```rust
{{#include ../../rust-interview-lab/src/bin/conn_pool.rs:195:226}}
```

`give_back` pushes the socket onto the idle stack with `Instant::now()` and invokes `notify_one` on the `Condvar`. Calling `discard` marks the guard as broken so that `Drop` closes the socket, decrements `open`, and wakes a waiter instead of returning it to the idle stack. Discarding after any I/O error is mandatory: an aborted request may leave partial response bytes in the kernel receive buffer, which would corrupt framing for the next borrower.

`ask` composes borrowing, request-response execution, error-triggered discard, and automatic return into a single helper:

```rust
{{#include ../../rust-interview-lab/src/bin/conn_pool.rs:228:250}}
```

## 29.5 Stale connections

Operating the idle collection as a **LIFO stack** concentrates traffic onto a small working set of warm sockets during low load. Surplus sockets sink to the bottom of the stack, age past `idle_timeout`, and are closed on subsequent sweeps. A **FIFO queue**, by contrast, rotates every socket evenly across requests, resetting every idle timestamp and preventing the pool from shrinking after a traffic spike.

Even within `idle_timeout`, servers enforce their own idle connection timeouts (commonly 5 seconds to several minutes) by transmitting a TCP `FIN`. While the socket sits idle in the pool, no thread reads that `FIN`; without a liveness probe, the next borrower writes a request into the half-closed socket and fails with `UnexpectedEof` or `ECONNRESET` (Figure 29.2).

<figure>
<img src="figures/ch29-stale.svg" alt="At t = 0 a request finishes and the connection is returned to the pool. At 50 ms the server's idle timeout fires and it sends FIN, which sits unread in the pooled socket. At 100 ms get lends the connection. Without the check, the write goes out and the read returns 0, so the request fails. With check_alive, a peek sees the FIN first, and the pool closes the connection and connects again.">
<figcaption><b>Figure 29.2</b> A connection goes stale while it sits in the pool. A check before lending it catches the server's <code>FIN</code>.</figcaption>
</figure>

`take_idle` enforces both idle-timeout eviction and server-close detection before lending a socket:

```rust
{{#include ../../rust-interview-lab/src/bin/conn_pool.rs:70:81}}
```

```rust
impl Pool {
    // ...
{{#include ../../rust-interview-lab/src/bin/conn_pool.rs:124:139}}
    // ...
}
```

`is_alive` temporarily switches the socket to non-blocking mode and executes `peek(&mut [0u8; 1])`. Because a healthy idle request-response socket should contain zero unread bytes, `WouldBlock` confirms that the connection remains open and clean. Returning `Ok(0)` indicates a pending server `FIN`, and returning `Ok(n > 0)` indicates unexpected stray bytes; in either case, the pool closes the socket and decrements `open`.

A pre-lend `peek` narrows the stale-connection race window but cannot eliminate it completely, because the server's `FIN` can arrive in flight between `peek` and the client's `write`. Production clients close the remaining window with two complementary defenses:

- Configure the pool's `idle_timeout` strictly shorter than the server's keep-alive timeout so the client initiates eviction before the server closes.
- Retry idempotent requests once on a fresh connection when a reused socket fails with a transport error (Chapter 19).

Animation 29.1 visualizes the complete pool lifecycle across borrowing, capacity blocking, idle eviction, and stale-socket detection.

<figure class="anim">
<video class="motion" src="figures/ch29-pool.mp4" autoplay loop muted playsinline preload="metadata" aria-label="Three caller robots on the left, the pool in the middle with two slots and an idle shelf, and the server on the right. Caller A gets a connection: the shelf is empty and open is 0 of 2, so the pool connects. A sends a request, gets a reply, and drops the guard; the connection goes onto the idle shelf with an age clock. Caller B gets it from the shelf, a reuse. A and B now hold both connections, and caller C's get finds open at 2 of 2 and sleeps on the Condvar. B drops its guard, C wakes and takes the returned connection. Later a connection on the shelf ages past idle_timeout and is closed. In a last run the server closes an idle connection, its FIN lands on the shelf unread, and a pool without the liveness check lends it: the caller writes, read returns 0, and the request fails." data-chapters="[[0.0, &quot;connect&quot;], [13.1, &quot;reuse&quot;], [19.7, &quot;limit&quot;], [39.98, &quot;eviction&quot;], [55.18, &quot;stale&quot;]]"><img src="figures/ch29-pool.gif" alt="Three caller robots on the left, the pool in the middle with two slots and an idle shelf, and the server on the right. Caller A gets a connection: the shelf is empty and open is 0 of 2, so the pool connects. A sends a request, gets a reply, and drops the guard; the connection goes onto the idle shelf with an age clock. Caller B gets it from the shelf, a reuse. A and B now hold both connections, and caller C's get finds open at 2 of 2 and sleeps on the Condvar. B drops its guard, C wakes and takes the returned connection. Later a connection on the shelf ages past idle_timeout and is closed. In a last run the server closes an idle connection, its FIN lands on the shelf unread, and a pool without the liveness check lends it: the caller writes, read returns 0, and the request fails."></video>
<figcaption><b>Animation 29.1</b> The pool lends, takes back, makes a caller wait at its limit, and closes an idle connection. Without the liveness check, it lends a connection the server has already closed.</figcaption>
</figure>

## 29.6 Measured

`main` executes four scenarios against a local line-oriented server. Scenario 1 dispatches 2,000 requests across eight worker threads, comparing unpooled connections against a 4-connection pool:

```text
1. 2000 requests from 8 threads
  a new connection each:   2000 connections,  169.8 ms
  a pool of 4:                4 connections,   80.4 ms, 1996 reuses
```

Even on loopback where TCP handshakes execute in microseconds, pooling halved elapsed wall-clock latency while eliminating 1,996 handshakes. Without pooling, the run generated 2,000 `TIME_WAIT` sockets in 0.17 seconds, a rate that exhausts Linux's 28,232-port ephemeral range in under 3 seconds (Section 27.2.1). Over a real network with TLS, unpooled requests would additionally incur 2 RTT per call.

Scenarios 2 through 4 verify capacity enforcement, idle eviction, and stale-connection detection:

```text
2. The bound: 2 connections, both lent out
  third get after 103 ms: Err(Custom { kind: TimedOut, error: "pool exhausted" })
  after one is returned: Ok(()), sizes (open, idle) = (2, 1)

3. Idle eviction: idle_timeout 100 ms
  connects 2, evicted 1

4. A server that closes idle connections after 50 ms
  check_alive false: Err(Custom { kind: UnexpectedEof, error: "server closed the connection" }), stale discarded 0
  check_alive true : Ok("ok second"), stale discarded 1
```

When both slots were occupied, the third `get` waited its 100 ms deadline and returned `TimedOut`; returning one guard immediately unblocked the next acquisition. Sleeping 150 ms past a 100 ms `idle_timeout` triggered eviction and a fresh dial. Against a server enforcing a 50 ms idle close, disabling `check_alive` lent a half-closed socket and failed with `UnexpectedEof`, whereas enabling `check_alive` detected the pending `FIN`, discarded the stale socket, and redialed transparently.

## 29.7 The complete program

<p class="listing"><b>Listing 29.1</b> A bounded connection pool with automatic return, idle eviction, and a liveness check. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/conn_pool.rs">src/bin/conn_pool.rs</a></p>

```rust
{{#include ../../rust-interview-lab/src/bin/conn_pool.rs}}
```

```text
$ cargo run --release --bin conn_pool
1. 2000 requests from 8 threads
  a new connection each:   2000 connections,  169.8 ms
  a pool of 4:                4 connections,   80.4 ms, 1996 reuses

2. The bound: 2 connections, both lent out
  third get after 103 ms: Err(Custom { kind: TimedOut, error: "pool exhausted" })
  after one is returned: Ok(()), sizes (open, idle) = (2, 1)

3. Idle eviction: idle_timeout 100 ms
  connects 2, evicted 1

4. A server that closes idle connections after 50 ms
  check_alive false: Err(Custom { kind: UnexpectedEof, error: "server closed the connection" }), stale discarded 0
  check_alive true : Ok("ok second"), stale discarded 1
```

## 29.8 Questions that come up

**"How large should the pool be?"**
By Little's Law, the steady-state concurrency required is L = \lambda W (peak request rate multiplied by average connection hold duration). At 2,000 requests per second and 5 ms per request, L = 10 concurrent connections. Because each client instance multiplies load on the server, the upper bound per client is the server's maximum connection budget divided by the fleet size.

**"Why not one pool shared by every server address?"**
A TCP socket is bound to a single remote endpoint. HTTP clients therefore maintain a map of per-origin `(host, port)` pools, enforcing both a per-host concurrency cap and a global descriptor cap.

**"What does HTTP/2 change?"**
HTTP/2 multiplexes concurrent request-response streams over a single TCP connection. Clients require only one (or a small fixed number of) TCP connections per origin, shifting pooling from connection checkout to concurrent stream-quota management.

**"What happens when the server restarts?"**
The server closes all idle pooled sockets simultaneously via `FIN` or `RST`. Pre-lend liveness probes discard idle sockets before reuse, while in-flight requests fail and idempotent operations retry on freshly dialed connections.

**"Is a `Mutex` too slow for a pool?"**
Because `TcpStream::connect` and all network I/O execute outside the critical section, the mutex protects only nanosecond-scale vector pushes, pops, and integer increments. Under extreme contention (hundreds of thousands of acquisitions per second), partitioning the pool into independent shards eliminates single-lock contention, mirroring the sharded map architecture of Chapter 14.

<div class="summary" markdown="1">

## Summary

- Connection pooling amortizes TCP/TLS handshakes, congestion-window slow start, server accept overhead, and client-side `TIME_WAIT` port consumption across many requests.
- Enforcing `open <= max` under a single mutex while dialing new sockets outside the lock prevents both capacity violations and mutex serialization during slow connects.
- Blocking saturated callers on `Condvar::wait_timeout` converts downstream overload into bounded `TimedOut` errors instead of indefinite hangs.
- RAII guards return healthy connections automatically in `Drop`; calling `discard` after an I/O error closes the socket so corrupted framing cannot leak to subsequent borrowers.
- LIFO idle-stack reuse concentrates traffic on warm sockets and enables surplus connections to expire under `idle_timeout`.
- Non-blocking `peek` detects server-closed sockets before lending; setting `idle_timeout` below the server's timeout and retrying idempotent requests once closes the remaining race window.
- Across 2,000 concurrent loopback requests, a 4-connection pool reduced elapsed time from 169.8 ms (2,000 connections) to 80.4 ms (4 connections, 1,996 reuses).

</div>

## Exercises

1. Add a `max_lifetime` field to `Config` that closes any connection older than its creation deadline even under continuous reuse. Explain why production pools enforce `max_lifetime` when upstream backends rotate IP addresses behind DNS or load balancers.
2. Enforce FIFO wakeup fairness in `get` so waiting callers acquire connections in arrival order. Explain why `Condvar::notify_one` does not guarantee FIFO ordering and specify the synchronization data structure required.
3. Extend `ask` to retry an idempotent request once on a fresh connection when a reused connection fails with an I/O error, while refusing to retry non-idempotent requests.
4. Benchmark scenario 1 with `max` set to 1, 2, 4, 8, and 16, plotting elapsed time against pool size. Identify where throughput plateaus and explain why.
5. Wrap the pool's `TcpStream` connections in `rustls` TLS streams (Chapter 28) and re-measure scenario 1 with and without pooling.
