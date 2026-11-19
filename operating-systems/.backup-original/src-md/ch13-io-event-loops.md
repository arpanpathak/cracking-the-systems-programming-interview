# 13. Input/Output and Event Loops

A server holds thousands of connections. Each one spends most of its
life idle, and the server's core problem is waiting: waiting on many
descriptors without one thread per descriptor and without burning a
core in a spin. This chapter measures the two classical answers —
blocking calls, one thread per connection — then builds the answer
modern servers use: one thread, many descriptors, and a readiness call
that wakes it when any of them has work.

<div class="callout glance">
<span class="label">At a glance</span>

- Blocking I/O parks a thread in the kernel per connection; simple,
  correct, and expensive at scale.
- `poll` takes a set of descriptors and returns the ready subset; the
  program then handles events without ever blocking.
- epoll and kqueue are the scalable descendants of the same pattern,
  built into Linux and macOS.

</div>

## 13.1 Blocking I/O and its cost

A `read` on a socket with no data blocks: the thread is parked inside
the kernel, on that socket's wait queue, until a packet arrives or the
peer closes. The mechanism is elegant — one queue per descriptor,
woken by the network interrupt from Chapter 2 — and the cost is a
thread per connection. Ten thousand idle connections mean ten thousand
parked threads, each with a stack and a scheduling presence, most of
them waiting.

The classical answer is a pool: a fixed set of threads, each serving
one connection at a time. The pattern is simple, correct under load,
and still the right choice when connections are few or each
connection's work is heavy — a database worker computing a query
should own its thread. The Rust listing in Section 13.3 demonstrates
the pattern.

The weakness is structural. A thread costs memory and scheduling
time; ten thousand threads is real overhead, a hundred thousand is
infeasible, and a million — the connection count of a large edge
service — is out of the question. The fix is to notice what a blocked
thread actually does: it waits for *readiness*, a question the kernel
can answer for many descriptors at once.

<div class="callout keyidea">
<span class="label">Key idea</span>

A blocked thread is an expensive way to ask one question: "is this
descriptor ready?" The event loop asks the question about every
descriptor in a single call, and spends its one thread only on the
ready ones.

</div>

## 13.2 The readiness call

`poll` takes an array of descriptors and the events each is waiting
for — readable, writable — and blocks until at least one is ready or a
timeout passes. It returns the ready subset. The program then handles
each ready descriptor: accept new connections, read available data,
write what fits. Then it calls `poll` again. Figure 13-1 is the
pattern.

<figure>
<img src="diagrams/ch13_event_loop.svg" alt="An event loop asking the kernel which descriptors are ready, then dispatching each"/>
</figure>

The discipline is strict and short: after `poll` returns, the program
must never block. A blocking call on one descriptor stalls every other
descriptor behind it. Work that can block — a long computation, a disk
read — moves to a worker thread or a second event loop. The event
loop's one thread is for readiness and dispatch, nothing else.

**Listing 13-1. One thread, two clients, `poll` (C++20).**

```cpp
{{#include ../code/ch13/poll_echo_server.cpp}}
```

The server accepts connections, echoes everything they send, and
exits after serving two clients. The harness starts it, runs the
client twice, and collects both outputs.

**Listing 13-2. The client that exercises it.**

```cpp
{{#include ../code/ch13/echo_client.cpp}}
```

**Output 13-1. The server's log: one thread handled both clients' events in order.**

```text
{{#include ../code/out/ch13_poll_echo_server.out}}
```

**Output 13-2. One of the two client runs; the other is identical.**

```text
{{#include ../code/out/ch13_echo_client_1.out}}
```

Read the server log against Figure 13-1. One descriptor set starts
with just the listening socket. `poll` returns when a client
connects; the loop accepts and adds the new descriptor. Subsequent
polls return when that descriptor has data; the loop reads and
echoes. When the client closes, `read` returns zero, the loop removes
the descriptor, and the next client repeats the cycle. One thread,
six events, no blocking anywhere except inside `poll` itself.

The pattern scales to thousands of descriptors; `poll`'s interface is
the limit, because the kernel must scan the array the program passes
in full, and the program must scan it again to find the ready ones.
The two system-specific descendants fix the rescanning. **epoll** on
Linux keeps the interest set inside the kernel and returns only the
ready descriptors. **kqueue** on macOS and the BSDs does the same with
a more general event model. The shape of the loop — wait, dispatch,
handle, repeat — is identical across all three; the listings in this
chapter compile and run on both systems because `poll` is the portable
common denominator.

## 13.3 Thread per connection, in Rust

The contrast, for calibration. The next listing is the same echo
server with one thread per connection — server and client in one
process, using only the Rust standard library.

**Listing 13-3. A thread-per-connection echo server plus its client (Rust).**

```rust
{{#include ../code/ch13/thread_echo.rs}}
```

**Output 13-3. Correct and simple; the cost is one stack per connection.**

```text
{{#include ../code/out/ch13_thread_echo_rs.out}}
```

The choice between the two patterns is a count, not a preference. At
dozens of connections, threads are simpler — each connection is
straight-line code. At thousands, the event loop wins on memory and
scheduling. At millions, the event loop is the only option, which is
why every production server framework — nginx, node, tokio — is an
event loop underneath, whatever its interface says.

<div class="callout caution">
<span class="label">Watch out</span>

The event loop's failure mode is a blocking call hiding in a handler:
one overlooked `read` on a slow peer stalls every connection. The
defenses are nonblocking descriptors, timeouts on every wait, and a
hard rule that handlers dispatch, not compute. Reviewing handlers for
blocking calls is the single highest-value audit for this pattern.

</div>

<div class="callout summary">
<span class="label">Summary</span>

- Blocking I/O parks a thread per connection; simple and correct, and
  expensive in stacks and scheduling.
- `poll` answers "which descriptors are ready" for a whole set; the
  loop then dispatches without blocking.
- epoll and kqueue keep the interest set in the kernel and return
  only ready events; the loop shape is unchanged.
- The rule of the pattern: after the readiness call, never block.
- Chapter 14 supplies the network half of the picture — how a socket
  becomes ready, and what TCP's handshake guarantees underneath.

</div>
