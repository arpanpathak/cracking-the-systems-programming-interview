# 13. Input/Output and Event Loops

A network server may hold thousands of connections at once, and at any
moment most of them are idle. The server must wait for data on all of
them and respond promptly to whichever one becomes active. How a server
waits has a large effect on the memory and CPU time that it needs.

In this chapter, we compare two designs. In the first, each connection has
its own thread, which blocks in `read` until data arrives. In the second,
a single thread asks the kernel which connections have data and serves
only those. We write an echo server in each design.

<div class="callout glance">
<span class="label">This chapter covers</span>

- blocking I/O and the cost of one thread per connection
- readiness, and the `poll` system call
- the event loop
- an echo server with `poll` in C++
- epoll on Linux and kqueue on macOS
- an echo server with one thread per connection in Rust
- when to use each design

</div>

## 13.1 Blocking I/O and its cost

When a thread calls `read` on a socket that has no data, the call
*blocks*. The kernel places the thread on a wait queue that belongs to the
socket and runs other threads. When a packet arrives for the socket, the
network device raises an interrupt, as described in Chapter 2. The kernel
then copies the data into the buffer of the socket and makes the waiting
thread ready to run.

With blocking calls, the simplest server design is **one thread per
connection**. Each thread reads a request, processes it, writes the reply,
and blocks in `read` again. The code for one connection is a
straightforward loop, and this design works well when a server has few
connections or when each request needs a lot of computation. A database
that executes long queries is an example.

The cost of this design grows with the number of connections. Every thread
needs a stack and an entry in the tables of the scheduler, whether or not
its connection is active. A server with 10,000 idle connections keeps
10,000 threads that do nothing but wait. With hundreds of thousands of
connections, the memory for stacks and the time spent switching between
threads become prohibitive.

<div class="callout keyidea">
<span class="label">Key idea</span>

A thread that blocks in `read` is waiting to learn that one descriptor has
data. The kernel can report this for many descriptors in a single system
call, so one thread can wait on behalf of all connections.

</div>

## 13.2 Waiting for readiness with poll

A descriptor is **ready** for reading when a `read` on it would return at
once, either with data or with end-of-file. The system call `poll` takes
an array of descriptors, each with the events that the program is
interested in, such as "readable" or "writable". It blocks until at least
one descriptor is ready or until a timeout expires, and it marks the ready
descriptors in the array.

A server built on `poll` repeats four steps, which Figure 13-1 shows. This
structure is called an **event loop**.

1. Call `poll` with all descriptors.
2. For each descriptor that `poll` marked as ready, determine what to do:
   accept a new connection, read data, or write data.
3. Perform that action.
4. Return to step 1.

<figure>
<img src="figures/ch13_event_loop.svg" alt="An event loop asking the kernel which descriptors are ready, then dispatching each"/>
</figure>

An event loop has one firm rule. The thread must not block anywhere except
in `poll`. If the thread blocks while it serves one connection, all other
connections wait. Work that may block, such as a long computation or a
read from a slow disk, must be passed to another thread.

Listing 13-1 is an echo server with one thread. It sends back every byte
that a client sends, and it exits after two clients have disconnected.
Listing 13-2 is the client. Our script starts the server and then runs the
client twice.

**Listing 13-1. An echo server with one thread and `poll` (C++20).**

```cpp
{{#include ../code/ch13/poll_echo_server.cpp}}
```

**Listing 13-2. The client.**

```cpp
{{#include ../code/ch13/echo_client.cpp}}
```

**Output 13-1. The log of the server.**

```text
{{#include ../code/out/ch13_poll_echo_server.out}}
```

**Output 13-2. The first client run. The second run prints the same lines.**

```text
{{#include ../code/out/ch13_echo_client_1.out}}
```

Let us follow the log of the server. At first, the array passed to `poll`
contains only the listening socket. When the first client connects, the
listening socket becomes readable. The server calls `accept`, receives
descriptor 4, and adds it to the array. The client then sends `one`,
`two`, and `three`. Each message makes descriptor 4 readable, and the
server reads and echoes 3, 3, and 5 bytes. When the client closes its
socket, `read` returns 0, and the server closes descriptor 4 and removes
it from the array. The second client receives descriptor 4 as well,
because the kernel assigns the lowest free descriptor number.

`poll` becomes slow when the array is large. On every call, the kernel
examines every descriptor in the array, and after the call the program
examines every entry to find those that are ready. Both steps take time
proportional to the number of connections, even if only one connection is
active. Two newer interfaces remove this cost. With **epoll** on Linux and
**kqueue** on macOS and the BSD systems, the program registers its
descriptors with the kernel once, and each wait returns only the ready
ones. The four steps of the event loop are the same with all three
interfaces. We use `poll` in this chapter because it is available on both
Linux and macOS.

## 13.3 One thread per connection in Rust

For comparison, Listing 13-3 implements the echo server with one thread
per connection. To keep the example in one file, the same program also
runs two clients, one after the other. It uses only the Rust standard
library.

**Listing 13-3. An echo server with one thread per connection, and its client (Rust).**

```rust
{{#include ../code/ch13/thread_echo.rs}}
```

**Output 13-3.**

```text
{{#include ../code/out/ch13_thread_echo_rs.out}}
```

The server starts a new thread for each accepted connection, and that
thread echoes `alpha`, `beta`, and `gamma` back to its client.

The number of connections determines which design is appropriate. With a
few dozen connections, one thread per connection is simpler to write and
to debug. With thousands of connections, an event loop needs much less
memory and causes fewer context switches. Servers and frameworks that are
designed for very large numbers of connections, such as nginx, Node.js,
and Tokio, are built around event loops.

<div class="callout caution">
<span class="label">Watch out</span>

The most common fault in an event loop is a handler that blocks. A single
`read` on a descriptor that is not ready stops service for every
connection. To guard against this fault, set descriptors to non-blocking
mode with `O_NONBLOCK`, give every wait a timeout, and keep long
computations out of handlers.

</div>

<div class="callout summary">
<span class="label">Summary</span>

- A blocking `read` suspends the calling thread until data arrives. One
  thread per connection is simple but needs a stack for every connection.
- `poll` reports which descriptors of a set are ready. An event loop
  calls `poll`, serves the ready descriptors, and repeats.
- A thread that runs an event loop must not block outside `poll`.
- epoll and kqueue keep the set of descriptors in the kernel and return
  only the ready ones.

In Chapter 14, we examine sockets in more detail and follow a TCP
connection from its handshake to its close.

</div>
