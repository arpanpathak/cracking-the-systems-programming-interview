# 13. I/O Multiplexing and the Event Loop

The central engineering problem of high-concurrency network servers is sustaining tens of thousands, or even millions, of simultaneous client connections when almost all of those connections sit idle waiting for network packets at any given instant. Historically framed as the **C10K problem** in 1999 (handling 10,000 concurrent connections on a single commodity server) and later pushed to the **C10M problem** (handling 10,000,000 concurrent connections), this workload exposes a sharp tension between programming simplicity and operating-system overhead. How can a server monitor massive numbers of sockets simultaneously without exhausting physical memory, thrashing processor caches, or spending more cycles in the kernel scheduler than in application logic?

Answering this question requires examining how operating systems schedule threads, how sockets interact with kernel wait queues, and how **Input/Output (`I/O`)** multiplexing interfaces evolved from linear descriptor scans to stateful kernel event queues and shared-memory completion rings.

## 13.1 The C10K and C10M Crux: Why Thread-Per-Connection Breaks

The most direct way to serve multiple **Transmission Control Protocol (`TCP`)** clients is the **thread-per-connection** model: a listening thread calls `accept()`, spawns a dedicated operating-system thread for the returned client socket, and lets that thread run straightforward blocking `read()` and `write()` calls until the peer closes the connection. Listing 13-5 at the end of this chapter implements this pattern in Rust. For an internal service handling fifty concurrent clients, the model is clear, debuggable, and completely adequate.

When concurrency scales to 10,000 or 100,000 connections, however, the thread-per-connection model collides with three hardware and kernel ceilings: memory exhaustion, scheduler and cache locality collapse, and lock contention on shared state.

### 13.1.1 Memory Exhaustion at Scale

Every operating-system thread requires both user-space and kernel-space memory before it processes a single application byte. On Linux x86-64, the default user-space stack reservation via `pthread_create()` is 8 MiB of virtual address space (commonly tuned down to 1 or 2 MiB in server configurations). Demand paging avoids committing all 8 MiB to physical **Dynamic Random-Access Memory (`DRAM`)** immediately, yet touching local buffers, protocol parsers, and **Transport Layer Security (`TLS`)** handshake frames rapidly faults in 32 to 64 KiB of resident stack pages per thread. Inside Ring 0, the kernel allocates a non-swappable kernel stack (typically 16 KiB on x86-64 Linux) plus a `task_struct` descriptor, scheduler entities, and **Floating-Point Unit (`FPU`)** / **Single Instruction, Multiple Data (`SIMD`)** register-save areas totaling roughly 8 to 12 KiB.

Consider a concrete budget for 50,000 simultaneous connections, each backed by one thread. Assuming a modest 64 KiB of resident user stack plus 24 KiB of pinned kernel stack and thread metadata, each thread consumes 88 KiB of physical memory:

```text
50,000 threads * 88 KiB/thread = 4,400,000 KiB (~4.20 GiB)
```

Over 4 GiB of physical memory is consumed purely by thread stacks and kernel scheduling structures, before allocating a single socket buffer or application session record. Scaling the same calculation to the C10M regime (10,000,000 connections) would demand roughly 840 GiB of physical memory for idle stacks alone, alongside 80 TiB of virtual stack reservations. By contrast, an event-driven server represents an idle connection with a compact heap structure (typically 512 bytes to 4 KiB), allowing 50,000 connections to occupy 25 to 200 MiB total.

### 13.1.2 Scheduler Overhead and Cache Locality Collapse

Memory consumption is only half of the pathology. Suppose 50,000 clients each send one small heartbeat or chat message per second, producing 50,000 wakeups per second across an 8-core server (6,250 wakeups per core per second). Under thread-per-connection, every arriving packet wakes a different sleeping thread. The kernel scheduler must enqueue the thread onto a run queue, preempt or switch away from the currently executing thread, save general-purpose and vector registers, switch kernel stacks, and resume the woken thread.

A direct context switch between two threads in the same address space costs roughly 1 to 3 microseconds on modern x86-64 processors, yet the indirect cost of cache pollution dominates. Each core has a small private **Level 1 (`L1`)** data cache (32 to 48 KiB) and **Level 2 (`L2`)** cache (256 KiB to 1 MiB). Switching among thousands of distinct thread stacks evicts the previous thread's stack frames and working set on every wakeup, causing a burst of L1 and L2 cache misses as well as **Translation Lookaside Buffer (`TLB`)** misses as the processor walks page tables for disparate stack pages. Even when threads share a process page table, their scattered stack addresses rapidly exhaust the 64-entry L1 data `TLB`.

### 13.1.3 Lock Contention Across Thousands of Threads

Network servers rarely process connections in complete isolation. Chat brokers route messages between peers, reverse proxies maintain shared upstream connection pools, and telemetry collectors update global histograms. When 10,000 threads concurrently acquire mutexes guarding a shared routing table, cache lines holding the lock word bounce across processor cores via cache-coherency invalidations, and waiting threads sleep in kernel `futex` queues. A single-threaded event loop (or a **shared-nothing** architecture running one pinned event loop per **Central Processing Unit (`CPU`)** core) eliminates lock contention on per-core connection state because only one thread ever mutates that core's connection table.

## 13.2 Event-Driven Architecture and `I/O` Multiplexing

An **event-driven server** decouples connection count from thread count by running a single thread (or one thread per core) inside an **event loop** driven by an `I/O` multiplexing system call (`select`, `poll`, Linux `epoll`, or **Berkeley Software Distribution (`BSD`)** and Darwin `kqueue`). Instead of parking a dedicated thread on each blocking `read()`, the application places every active socket into a monitored set and invokes one kernel call that sleeps until *any* descriptor in the set becomes ready (Figure 13-1).

Every iteration of the event loop executes three sequential phases. During the **wait phase**, the loop invokes `poll()`, `epoll_wait()`, or `kevent()`, suspending the thread in the kernel until at least one monitored descriptor transitions to a ready state (an incoming `TCP` connection queued on the listening socket, readable bytes in a client receive buffer, writable space in a send buffer, or an error or hangup condition) or a caller-supplied timeout expires. During the **dispatch phase**, the loop inspects the ready descriptors returned by the kernel and routes each event to the corresponding connection state machine. During the **non-blocking execution phase**, each handler consumes available bytes, updates per-connection state, emits any immediately writable response bytes, and returns promptly to the loop.

Because one thread multiplexes every connection assigned to that core, handler execution time directly determines tail latency for all sibling clients. If a handler invokes a synchronous disk read that takes 15 ms, executes a blocking **Domain Name System (`DNS`)** query, or runs an unchunked cryptographic computation, every other socket in the loop waits 15 ms before its ready event is dispatched. Production event-driven servers therefore keep handlers strictly non-blocking and offload unavoidable blocking work to a bounded background thread pool, notifying the event loop upon completion through a pipe or `eventfd`.

<figure>
<img src="figures/ch13_event_loop.svg" alt="An event loop asking the kernel which descriptors are ready, then dispatching each"/>
</figure>

### 13.2.1 Socket Setup, `struct sockaddr_in`, and the `poll(2)` System Call Interface

Listings 13-1 through 13-4 implement a complete single-threaded `TCP` echo server and client using the `BSD` socket **Application Programming Interface (`API`)** paired with `poll(2)`. Before examining the code, review the exact data structures and system call contracts crossing the user-kernel boundary:

```c
struct sockaddr_in {
    sa_family_t    sin_family; // Address family: AF_INET (IPv4)
    in_port_t      sin_port;   // 16-bit TCP/UDP port in network byte order (htons)
    struct in_addr sin_addr;   // 32-bit IPv4 address in network byte order (htonl)
    unsigned char  sin_zero[8];// Zero padding to match generic struct sockaddr size
};

struct pollfd {
    int   fd;       // File descriptor to monitor (negative entries are ignored)
    short events;   // Input bitmask: events the application asks the kernel to watch
    short revents;  // Output bitmask: events the kernel detected on return
};

int socket(int domain, int type, int protocol);
int setsockopt(int sockfd, int level, int optname, const void *optval, socklen_t optlen);
int bind(int sockfd, const struct sockaddr *addr, socklen_t addrlen);
int listen(int sockfd, int backlog);
int accept(int sockfd, struct sockaddr *addr, socklen_t *addrlen);
int connect(int sockfd, const struct sockaddr *addr, socklen_t addrlen);
int poll(struct pollfd *fds, nfds_t nfds, int timeout);
```

Internet protocols transmit multi-byte integers in **big-endian** network byte order, whereas x86-64 and ARM64 processors store integers in little-endian order. Calling `htons(45678)` ("host to network short", 16-bit) and `htonl(INADDR_LOOPBACK)` ("host to network long", 32-bit, converting `127.0.0.1` = `0x7F000001`) converts fields inside `struct sockaddr_in` into wire order before passing the structure to the kernel. Because `bind()`, `connect()`, and `accept()` serve **Internet Protocol Version 4 (`IPv4`, `sockaddr_in`)**, **Internet Protocol Version 6 (`IPv6`, `sockaddr_in6`)**, and Unix domain (`sockaddr_un`) addresses through a single C interface, callers cast the concrete pointer to `struct sockaddr *` and pass its exact byte length in `addrlen`.

To establish a listening server, `socket(AF_INET, SOCK_STREAM, 0)` allocates an unbound `IPv4` `TCP` endpoint and returns a file descriptor (`fd >= 0`, or `-1` with `errno` set to `EMFILE`, `ENFILE`, or `EAFNOSUPPORT`). Calling `setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one)` allows immediate server restarts even when prior connections linger in `TCP` `TIME_WAIT` state, preventing `EADDRINUSE` during rapid redeployment. Next, `bind(ls, addr, addrlen)` attaches the local **Internet Protocol (`IP`)** address and port, and `listen(ls, backlog)` converts `ls` into a passive listener whose completed-connection queue is bounded by `backlog` (`8` in Listing 13-1). Each call to `accept(ls, addr, addrlen)` dequeues one completed client connection and returns a **new, distinct connected file descriptor** (`c >= 0`), leaving `ls` open for future clients. On the client side (Listing 13-2), `connect(fd, addr, addrlen)` initiates the `TCP` three-way handshake (**Synchronize (`SYN`)**, **Synchronize-Acknowledge (`SYN-ACK`)**, **Acknowledge (`ACK`)**), returning `0` once established or `-1` (`ECONNREFUSED`, `ETIMEDOUT`).

The `poll(fds, nfds, timeout)` system call monitors an array of `nfds` `struct pollfd` entries simultaneously. Before each call, the application populates `fds[i].fd` and `fds[i].events` (typically `POLLIN` to detect readable client bytes, peer **End-of-File (`EOF`)**, or a queued connection on `ls`). The `timeout` parameter specifies the maximum wait in milliseconds (`1000` ms in Listing 13-1; `-1` blocks indefinitely; `0` returns immediately without sleeping). On return, the kernel overwrites `fds[i].revents` with observed flags (`POLLIN`, `POLLOUT`, and output-only `POLLHUP`, `POLLERR`, or `POLLNVAL`) and returns the count of ready entries (`> 0`), `0` on timeout, or `-1` on error (`EINTR`, `ENOMEM`). When `POLLIN` fires on a client socket and `read()` returns `0`, the peer has closed its write half (`TCP` **Finish (`FIN`)**), so the server closes the descriptor and removes it from `fds`.

### 13.2.2 Connecting the Echo Server Listings to Production Invariants

In Listing 13-1 (`poll_echo_server.cpp`) and Listing 13-3 (`poll_echo_server.rs`), both servers keep the code minimal to isolate the mechanics of `poll()`. Inspecting the loop reveals two pedagogical simplifications that production event loops must harden. First, neither listing sets `O_NONBLOCK` on the listening socket `ls` or the accepted client descriptors `c`. On a blocking client socket, a single `write()` inside the event loop can suspend the entire server thread if a slow client's `TCP` receive window fills and the kernel's send buffer becomes full. Production servers set `O_NONBLOCK` via `accept4(..., SOCK_NONBLOCK)` or `fcntl(fd, F_SETFL, O_NONBLOCK)`. When a non-blocking `write()` returns fewer bytes than requested or fails with `EAGAIN` / `EWOULDBLOCK`, the server appends the unsent tail to a per-connection outbound buffer and adds `POLLOUT` to `fds[i].events`, clearing `POLLOUT` once the outbound buffer drains to avoid busy-spinning on permanently writable sockets.

Second, Listing 13-1 reads into a fixed 256-byte stack buffer (`char buf[256]`) and writes directly back to the socket. If a client sends 4,096 bytes in one burst, `read()` returns 256 bytes, leaving 3,840 bytes in the kernel socket receive buffer. Because `poll()` is **level-triggered**, the next iteration immediately reports `POLLIN` again until all 4,096 bytes are drained. Under edge-triggered `epoll`, failing to drain the buffer completely would introduce a subtle deadlock, examined in Section 13.4.

**Listing 13-1. An echo server with one thread and `poll` (C++20).**

```cpp
{{#include ../code/ch13/poll_echo_server.cpp}}
```

**Listing 13-2. The C++20 echo client.**

```cpp
{{#include ../code/ch13/echo_client.cpp}}
```

**Output 13-1. The log of the C++20 server.**

```text
{{#include ../code/out/ch13_poll_echo_server.out}}
```

**Output 13-2. The first C++20 client run. The second run prints the same lines.**

```text
{{#include ../code/out/ch13_echo_client_1.out}}
```

**Listing 13-3. The same single-threaded `poll` echo server in Rust.**

```rust
{{#include ../code/ch13/poll_echo_server.rs}}
```

**Listing 13-4. The Rust echo client.**

```rust
{{#include ../code/ch13/echo_client.rs}}
```

**Output 13-3. The log of the Rust `poll` server.**

```text
{{#include ../code/out/ch13_poll_echo_server_rs.out}}
```

**Output 13-4. The first Rust client run.**

```text
{{#include ../code/out/ch13_echo_client_1_rs.out}}
```

## 13.3 Complexity and Evolution of Multiplexing Primitives (`select`, `poll`, `epoll`, `kqueue`)

The scalability ceiling of an event loop depends directly on how the kernel maintains the monitored descriptor set across calls (Figure 13-2). Table 13-1 compares the four foundational readiness-based multiplexing primitives across descriptor limits, asymptotic complexity, and kernel data structures.

| Primitive | Platform | Descriptor Limit | Per-Wait Complexity | Kernel Registration Model |
| :--- | :--- | :--- | :--- | :--- |
| **`select`** | **Portable Operating System Interface (`POSIX`)** | Fixed `FD_SETSIZE` (typically 1024) | O(max_fd) | Stateless; copies full bitmasks on every call |
| **`poll`** | `POSIX` | Unbounded (dynamic `pollfd[]`) | O(N) | Stateless; copies and scans full `fds` array on every call |
| **`epoll`** | Linux | Unbounded | O(K) ready events | Stateful kernel red-black tree (`epoll_ctl`) + O(1) ready list (`epoll_wait`) |
| **`kqueue`** | macOS / `BSD` | Unbounded | O(K) ready events | Stateful kernel event table (`kevent`) unifying sockets, timers, files, and processes |

### 13.3.1 The O(N) Kernel-Copy Overhead of `select` and `poll`

Both `select` and `poll` are **stateless** interfaces: the kernel retains zero memory of which descriptors the application monitored during the previous iteration. `select(nfds, readfds, writefds, exceptfds, timeout)` represents descriptor sets as fixed-size bitmaps (`fd_set`), capping the maximum descriptor value at `FD_SETSIZE` (1024 on Linux and macOS). Because the kernel mutates the bitmaps in place to return ready descriptors, the application must rebuild the input bitmaps before every single invocation, and the kernel must scan every bit from `0` up to `max_fd`.

`poll()` removes the 1024-descriptor limit by accepting a contiguous user-space array of `struct pollfd` entries (8 bytes each), yet preserves the exact same O(N) per-call cost. Trace what occurs on a server managing `N = 50,000` mostly idle connections where only `K = 10` sockets receive packets during a 1-millisecond tick. First, `poll()` copies all 50,000 `struct pollfd` entries (`50,000 * 8 bytes = 400 KiB`) from user memory into kernel memory via `copy_from_user()`. Second, the kernel iterates over all 50,000 descriptors, resolves each file descriptor number to its `struct file` in the process descriptor table, checks its current readiness via the file's `f_op->poll()` method, and registers a temporary wait-queue callback on each socket's wait queue. Third, when packets arrive on 10 sockets, the thread wakes, walks all 50,000 wait-queue entries to detach every temporary callback, and copies the entire 400 KiB array back to user space via `copy_to_user()`. Fourth, the application linearly scans all 50,000 elements of `fds[]` to locate the 10 entries whose `revents` field is non-zero.

At 1,000 loop iterations per second, copying 400 KiB in and 400 KiB out moves 800 MiB/s across the user-kernel boundary and performs 50,000,000 descriptor checks per second to dispatch 10,000 active events. CPU utilization saturates on bookkeeping while actual packet throughput collapses.

### 13.3.2 Stateful O(K) Multiplexing: `epoll` and `kqueue`

Linux `epoll` and `BSD`/Darwin `kqueue` eliminate the O(N) scan by moving the interest set permanently into kernel memory. In `epoll`, the application creates an epoll instance once via `epoll_create1(EPOLL_CLOEXEC)` and mutates its interest set incrementally via `epoll_ctl(epfd, op, fd, &event)` when connections open (`EPOLL_CTL_ADD`), change direction (`EPOLL_CTL_MOD`), or close (`EPOLL_CTL_DEL`).

Internally, the Linux kernel backs each `struct eventpoll` with two distinct data structures: a **red-black tree (`rbr`)** storing every registered descriptor (keyed by file pointer and descriptor number, giving O(log N) insertion, lookup, and deletion) and a doubly-linked **ready list (`rdllist`)**. When `epoll_ctl(EPOLL_CTL_ADD)` registers a socket, the kernel attaches a persistent callback (`ep_poll_callback`) to that socket's wait queue *once*. Whenever the **Network Interface Card (`NIC`)** delivers a packet and the `TCP` stack appends data to the socket's receive queue, the interrupt/softirq path invokes `ep_poll_callback`, which links the socket's `epitem` onto `rdllist` in **O(1)** time and wakes any thread blocked in `epoll_wait()`.

When the event loop invokes `epoll_wait(epfd, events, maxevents, timeout)`, the kernel does not walk the 50,000-node red-black tree. It inspects `rdllist`, copies only the `K = 10` ready `struct epoll_event` entries (`10 * 12 bytes = 120 bytes`) to user space, and returns `10`. Both kernel work and user-space dispatch drop from **O(N)** to **O(K)**, scaling smoothly from 10,000 to millions of idle connections.

Darwin and `BSD` kernels achieve the same O(K) scaling through **`kqueue`**, which additionally generalizes readiness beyond file descriptors into a unified filter framework (`EVFILT_READ`, `EVFILT_WRITE`, `EVFILT_TIMER`, `EVFILT_SIGNAL`, and `EVFILT_PROC` for process lifecycle monitoring, covered in Chapter 15). Moreover, `kevent()` accepts both a `changelist` (registration updates) and an `eventlist` (ready outputs) in a single system call, allowing an application to batch dozens of descriptor registrations and retrieve ready events in one user-kernel transition. Production runtimes including Nginx, Envoy, Node.js (`libuv`), and Rust's Tokio are built directly atop `epoll` and `kqueue`.

<figure>
<img src="figures/ch13_poll_vs_epoll.svg" alt="Stateless poll O(N) full-array copy and scan versus stateful epoll/kqueue O(K) kernel red-black tree and ready queue"/>
</figure>

## 13.4 Level-Triggered vs. Edge-Triggered Readiness

Stateful multiplexers introduce a critical semantic choice in how readiness notifications fire: **Level-Triggered (`LT`)** mode (the default in `poll`, `epoll`, and `kqueue`) versus **Edge-Triggered (`ET`)** mode (`EPOLLET` in `epoll`, `EV_CLEAR` in `kqueue`).

In **level-triggered** mode, the kernel reports a descriptor as ready on every `epoll_wait()` call for as long as the underlying condition remains true (unread bytes exist in the socket receive buffer, or free space exists in the send buffer). In **edge-triggered** mode, the kernel reports the descriptor *once* when its state transitions from not-ready to ready (for example, when new bytes arrive on a previously empty socket buffer).

### 13.4.1 The Partial-Read Stall Bug Under Edge-Triggered Mode

Edge-triggered mode reduces redundant wakeups, especially when multiple worker threads share an `epoll` instance, yet it introduces a classic liveness bug if the handler fails to drain the socket completely. Trace a concrete counterexample using the 256-byte buffer from Listing 13-1 under `EPOLLET`. Suppose a client transmits a 1,000-byte request in a single `TCP` segment, transitioning the socket's receive buffer from 0 bytes to 1,000 bytes. `epoll_wait()` detects this rising edge and returns `EPOLLIN` for the client socket. The server calls `read(fd, buf, 256)`, consuming 256 bytes and leaving 744 bytes unread in the kernel buffer, and then returns to `epoll_wait()` without looping to read the remainder. Because the client is waiting for the server's reply before sending additional bytes, no new packets arrive; and because `EPOLLET` triggers only on *new* state transitions, `epoll_wait()` sleeps indefinitely even though 744 bytes sit ready in kernel memory, deadlocking both endpoints until a timeout fires.

To prevent partial-read stalls under `EPOLLET`, every descriptor must be configured with `O_NONBLOCK`, and every read handler must loop calling `read()` until it returns `-1` with `errno == EAGAIN` (or `0` on `EOF`). Similarly, `accept()` on an edge-triggered listening socket must loop until `EAGAIN`, because two clients may complete their three-way handshakes simultaneously before a single `EPOLLET` notification is delivered.

### 13.4.2 Connection Starvation and `EPOLLONESHOT`

Draining until `EAGAIN` introduces the opposite hazard: **connection starvation**. Suppose Client A streams a 100 MiB upload over a 10 Gbps local link while Client B waits for a 64-byte authentication reply on the same event loop. Under an unbounded `while ((n = read(...)) > 0)` drain loop, new packets from Client A refill the receive buffer faster than the handler empties it, so `read()` never returns `EAGAIN`. Client A monopolizes the event loop thread for tens of milliseconds while Client B's latency spikes.

Production event loops resolve this tension by capping each handler invocation to a fixed per-turn byte budget (for example, 64 KiB per tick). If the socket still has data after reaching the budget, the loop stops draining Client A, services Client B and other ready sockets, and reschedules Client A on a user-space continuation queue (since `EPOLLET` will not re-notify on the unread remainder). When multiple threads call `epoll_wait()` on a shared `epfd`, handlers also register sockets with **`EPOLLONESHOT`**, which automatically disables the descriptor after delivering one event to one thread so two threads never concurrently read out-of-order chunks from the same `TCP` stream; the owning thread re-arms the descriptor via `epoll_ctl(EPOLL_CTL_MOD)` once processing finishes.

## 13.5 Why Regular Disk Files Always Report Ready Under `epoll`

Engineers porting network event loops to storage-heavy servers frequently attempt to register regular disk file descriptors (opened on `ext4`, `XFS`, or `APFS`) with `epoll` or `poll`, expecting the kernel to notify the loop when disk blocks finish reading from **Solid-State Drive (`SSD`)** storage. On Linux, `epoll_ctl(epfd, EPOLL_CTL_ADD, disk_fd, &ev)` fails immediately with **`EPERM`**, and `poll()` / `select()` always return `POLLIN` and `POLLOUT` immediately for regular files regardless of whether the requested block resides in the **Page Cache** or on spinning media.

This behavior stems from a fundamental difference between network sockets and block-backed files in the Unix **Virtual File System (`VFS`)** model. A network socket has an intrinsic, asynchronous arrival stream: bytes are either currently present in the socket's receive queue or absent until a remote peer transmits them. A regular file has no remote producer; its bytes already exist on disk at known offsets. Under `POSIX` buffered `I/O`, the kernel assumes a file is always readable up to `EOF`, and the actual disk read is only initiated *inside* the synchronous `read()` or `pread()` system call when a page-cache miss occurs. Because `poll()` and `epoll` have no mechanism to specify *which file offset and byte length* the caller intends to read, the kernel cannot prefetch the block asynchronously in advance.

Consequently, invoking `read()` on a regular file descriptor inside a single-threaded event loop blocks the entire thread for the duration of a page-cache miss (tens of microseconds on **Non-Volatile Memory Express (`NVMe`)**, several milliseconds on rotational disks or network filesystems), even if the file descriptor was opened with `O_NONBLOCK` (which `POSIX` ignores for regular files). Traditional event-driven runtimes such as `libuv` (Node.js) and Tokio work around this limitation by dispatching regular-file operations to a dedicated background thread pool, paying thread-wakeup and context-switch overhead on every disk request.

## 13.6 Completion-Based `I/O`: Linux `io_uring`

Readiness-based interfaces (`poll`, `epoll`, `kqueue`) implement the **reactor pattern**: the kernel tells user space *when* a descriptor is ready, and user space still issues a separate system call (`read`, `write`, `accept`) to perform the data transfer. On modern hardware where a single `NVMe` drive delivers over 1,000,000 **Input/Output Operations Per Second (`IOPS`)** and Spectre/Meltdown mitigations have raised user-kernel transition costs, issuing two or more system calls per operation (plus failing to handle regular disk files asynchronously) becomes a primary bottleneck.

Introduced in Linux 5.1, **`io_uring`** shifts the operating system to a true **proactor (completion-based) model** that unifies network sockets, regular disk files (both buffered and `O_DIRECT`), timers, and filesystem metadata operations under one asynchronous interface.

### 13.6.1 Shared Submission and Completion Ring Buffers

When an application calls `io_uring_setup(entries, &params)`, the kernel allocates two lock-free, single-producer/single-consumer ring buffers in memory shared between user space and Ring 0 via `mmap()`. In the **Submission Queue (`SQ`)**, user space writes 64-byte **Submission Queue Entries (`SQE`s)** describing desired operations (an opcode such as `IORING_OP_READ`, `IORING_OP_WRITE`, `IORING_OP_ACCEPT`, or `IORING_OP_RECV`, a target file descriptor, a buffer address, a byte length, and an opaque 64-bit `user_data` tag) and advances the `SQ` tail pointer with a store-release memory barrier. In the **Completion Queue (`CQ`)**, once the kernel completes an operation asynchronously (via `NVMe` interrupt, `NIC` softirq, or internal worker thread), it writes a 16-byte **Completion Queue Entry (`CQE`)** containing the original `user_data` tag and the signed result (`res`, matching the return value or negated `-errno` of the equivalent syscall) and advances the `CQ` tail pointer.

Because both rings live in shared memory, an application can enqueue 64 network sends and 32 disk reads into the `SQ`, then issue a *single* `io_uring_enter()` system call to submit all 96 operations and optionally wait for completions. Reaping completed `CQE`s requires zero system calls: user space reads directly from the `CQ` ring and advances the `CQ` head pointer.

### 13.6.2 Zero-Syscall Polling (`SQPOLL`) and Registered Resources

For ultra-low-latency storage engines and network proxies, `io_uring` supports **Submission Queue Polling (`IORING_SETUP_SQPOLL`)**. When enabled, the kernel spawns a dedicated kernel thread (`io_uring-sq`) that continuously polls the shared `SQ` tail pointer in memory. As soon as user space writes an `SQE` and updates the tail index, the kernel thread submits the operation to the storage or network driver immediately, achieving **zero system calls** on the steady-state data path (falling back to sleeping after an idle timeout `sq_thread_idle` to conserve `CPU` when traffic pauses).

`io_uring` also eliminates per-operation kernel lookup overhead through resource registration. Calling `io_uring_register()` with `IORING_REGISTER_FILES` installs a fixed table of file descriptors so the kernel skips atomic reference-count increments and decrements (`fget`/`fput`) on every `I/O` request. Similarly, `IORING_REGISTER_BUFFERS` pins user-space buffers in physical `DRAM` once at startup, eliminating repeated page-table walks and `get_user_pages()` pinning on high-throughput `O_DIRECT` disk and network transfers.

## 13.7 Contrast: Thread-Per-Connection in Rust

Listing 13-5 contrasts the single-threaded `poll` servers from Listings 13-1 and 13-3 with a thread-per-connection echo server written using only the Rust standard library. Every accepted `TcpStream` moves into a newly spawned operating-system thread (`thread::spawn(move || handle(s, id))`), allowing `handle()` to execute straightforward blocking `read()` and `write_all()` calls without maintaining an explicit state machine or readiness loop. For small client populations or CPU-bound request handlers, this simplicity is attractive; once connection counts enter the tens of thousands, the stack memory, cache eviction, and scheduling overhead quantified in Section 13.1 motivate moving to an `epoll`, `kqueue`, or `io_uring` event loop.

**Listing 13-5. Contrast: a thread-per-connection echo server and client (Rust).**

```rust
{{#include ../code/ch13/thread_echo.rs}}
```

**Output 13-5.**

```text
{{#include ../code/out/ch13_thread_echo_rs.out}}
```

<div class="callout keyidea">
<span class="label">Key idea</span>

Event-driven servers scale to tens of thousands of idle connections by replacing per-connection thread stacks with one kernel readiness queue. Stateful `epoll` and `kqueue` reduce wait complexity from O(*N*) total connections (`poll`) to O(*K*) active connections, while `io_uring` extends asynchronous execution to regular disk files and zero-syscall submission rings.

</div>

<div class="callout experiment">
<span class="label">Experiment</span>

In Listing 13-1 (`code/ch13/poll_echo_server.cpp`), comment out the `setsockopt(..., SO_REUSEADDR, ...)` call, connect a client, terminate the server with Ctrl-C, and immediately restart it. Observe `bind()` failing with `EADDRINUSE` while the prior socket lingers in `TCP` `TIME_WAIT`.

</div>

<div class="callout caution">
<span class="label">Common Pitfall</span>

Executing a blocking disk read, synchronous `DNS` lookup, or heavy `CPU` loop inside a single-threaded event-loop callback. Because one thread multiplexes every socket, a 50 ms blocking call stalls tail latency across all sibling connections simultaneously; offload blocking work to a worker pool or use `io_uring`.

</div>
