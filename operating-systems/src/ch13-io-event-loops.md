# 13. I/O Multiplexing and the Event Loop

The central engineering challenge of high-concurrency network servers is sustaining tens of thousands of simultaneous client connections when the vast majority remain idle waiting for network packets at any given instant. Choosing between a thread-per-connection architecture and an event-driven I/O multiplexing loop directly governs memory consumption, cache locality, and scheduler overhead.

## 13.1 The Scalability Limits of Thread-Per-Connection

Assigning one operating-system thread to every accepted TCP connection allows handlers to be written as straightforward sequential blocking code (`read()`, process, `write()`). While intuitive for low-concurrency services, this model encounters three scaling ceilings as connection counts grow into the tens of thousands:
- **Per-thread stack footprint:** Each OS thread reserves a dedicated user-space stack (commonly 1 to 8 MiB of virtual space and tens of kilobytes of resident pages) plus a kernel stack (8 to 16 KiB) and scheduling metadata.
- **Context-switch and TLB overhead:** Waking thousands of threads across bursts of short packets triggers frequent kernel scheduler invocations, register-state saves, and L1/L2 cache eviction.
- **Lock contention:** Sharing mutable session tables or metrics across thousands of concurrent threads introduces heavy synchronization overhead.

## 13.2 Event-Driven Architecture and I/O Multiplexing

An **event-driven server** decouples connection count from thread count by running a single-threaded (or one-thread-per-core) **event loop** over an **I/O multiplexing** system call (`poll`, Linux `epoll`, or BSD/Darwin `kqueue`). Rather than blocking a dedicated thread on one socket, the loop registers every active file descriptor with the kernel and sleeps once until *any* descriptor becomes ready:

1. **Wait (Observation):** The loop invokes `poll()` (or `epoll_wait()` / `kevent()`), suspending the thread until one or more monitored sockets transition to a ready state (an incoming TCP connection waiting on the listening socket, readable bytes in a client receive buffer, or an error/hangup) or a timeout expires.
2. **Dispatch:** The loop inspects the ready descriptors reported by the kernel and routes each event to its connection state machine.
3. **Non-blocking Execution:** Each handler consumes or emits available bytes and returns promptly to the loop. Because one thread services all connections, a blocking disk read or expensive CPU computation inside a handler stalls every other client until it returns; production event loops offload blocking work to dedicated thread pools.

<figure>
<img src="figures/ch13_event_loop.svg" alt="An event loop asking the kernel which descriptors are ready, then dispatching each"/>
</figure>

### 13.2.1 Socket Setup, `struct sockaddr_in`, and the `poll(2)` System Call Interface

Listings 13-1 through 13-4 build a complete single-threaded TCP echo server and client using the BSD socket API paired with `poll(2)`. Understanding the exact data structures, byte-order conversions, and return contracts makes every line transparent:

```text
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

- **Network Byte Order (`htons` / `htonl`):** Internet protocols transmit multi-byte integers in **big-endian** (most significant byte first) network byte order, whereas x86-64 and ARM64 processors are little-endian. Calling **`htons(45678)`** ("host to network short", 16-bit) and **`htonl(INADDR_LOOPBACK)`** ("host to network long", 32-bit, converting `127.0.0.1` = `0x7F000001`) converts fields inside `struct sockaddr_in` into canonical wire order before passing the struct to the kernel.
- **Polymorphic `struct sockaddr *` casts:** Because `bind()`, `connect()`, and `accept()` serve IPv4 (`sockaddr_in`), IPv6 (`sockaddr_in6`), and Unix domain (`sockaddr_un`) addresses through one C interface, callers cast the concrete address pointer to `struct sockaddr *` and pass its exact byte size (`sizeof addr`) in `addrlen`.
- **`socket(domain, type, protocol)`:** Creates an unbound kernel socket endpoint and returns a file descriptor (`>= 0`), or `-1` on error (`EMFILE`, `EAFNOSUPPORT`). Passing `(AF_INET, SOCK_STREAM, 0)` selects IPv4 (`AF_INET`), reliable connection-oriented byte stream (`SOCK_STREAM`), and the default stream protocol (TCP, `0`).
- **`setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one)`:** Configures socket-layer options (`SOL_SOCKET`). When a TCP server exits with active connections, the kernel holds the old `(IP, port)` tuple in TCP **`TIME_WAIT`** state for 30 to 120 seconds to absorb delayed network packets. Without **`SO_REUSEADDR`** set to non-zero (`one = 1`), immediately restarting the server on port `45678` fails inside `bind()` with `EADDRINUSE`. Returns `0` on success or `-1` on error.
- **`bind(ls, addr, addrlen)`:** Associates the local IP address and port in `addr` with socket `ls`. Returns `0` on success or `-1` (`EADDRINUSE`, `EACCES` for privileged ports `< 1024`).
- **`listen(ls, backlog)`:** Marks `ls` as a passive listening socket capable of accepting incoming TCP handshakes. The **`backlog`** parameter (`8` in Listing 13-1) bounds the length of the kernel's completed-connection queue awaiting `accept()`. Returns `0` on success or `-1`.
- **`accept(ls, addr, addrlen)`:** Dequeues one completed client connection from `ls`'s accept queue and allocates a **new, distinct connected file descriptor** (`c >= 0`) dedicated to that client, leaving `ls` open and listening for future clients. Passing `nullptr, nullptr` for `(addr, addrlen)` discards the peer's IP/port metadata. Returns `-1` on error (`EINTR`, `EAGAIN`, `EMFILE`).
- **`connect(fd, addr, addrlen)`:** Used by the client (Listing 13-2) to initiate the TCP three-way handshake (`SYN`, `SYN-ACK`, `ACK`) toward the server address in `addr`. Returns `0` once established, or `-1` (`ECONNREFUSED` if no server is listening, `ETIMEDOUT` on network timeout).
- **`poll(fds, nfds, timeout)`:** Monitors the array `fds` of `nfds` `struct pollfd` entries simultaneously.
  - Before calling `poll()`, the application sets `fds[i].fd` and `fds[i].events` (typically **`POLLIN`** to detect readable client bytes, peer EOF, or a newly queued connection ready for `accept()` on the listening socket `ls`).
  - **`timeout`** specifies the maximum blocking interval in milliseconds (`1000` ms in Listing 13-1; `-1` blocks indefinitely; `0` returns immediately without blocking).
  - On return, the kernel overwrites **`fds[i].revents`** for every entry (leaving `events` untouched) with the subset of conditions actually observed: **`POLLIN`** (data or EOF ready to read), **`POLLOUT`** (send buffer writable), and output-only flags **`POLLHUP`** (peer closed connection), **`POLLERR`** (asynchronous socket error), or **`POLLNVAL`** (descriptor is not open).
  - **Return value:** Returns the count (`> 0`) of entries with non-zero `revents`, `0` if `timeout` elapsed with zero ready descriptors, or `-1` on error (`EINTR` if interrupted by a signal, `ENOMEM`). When `fds[i].revents & POLLIN` fires on a client socket and `read()` returns `0`, the client has closed its write half cleanly (TCP `FIN`), so the server closes the descriptor and erases it from `fds`.

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

The scalability of an event loop depends directly on how the kernel tracks the monitored descriptor set across calls:

| Primitive | Platform | Descriptor Limit | Per-Wait Complexity | Kernel Registration Model |
| :--- | :--- | :--- | :--- | :--- |
| **`select`** | POSIX | Fixed `FD_SETSIZE` (typically 1024) | O(max_fd) | Stateless; copies full bitmasks on every call |
| **`poll`** | POSIX | Unbounded (dynamic `pollfd[]`) | O(N) | Stateless; copies and scans full `fds` array on every call |
| **`epoll`** | Linux | Unbounded | O(K) ready events | Stateful kernel red-black tree (`epoll_ctl`) + O(1) ready list (`epoll_wait`) |
| **`kqueue`** | macOS / BSD | Unbounded | O(K) ready events | Stateful kernel event table (`kevent`) unifying sockets, timers, files, and processes |

Both `select` and `poll` are **stateless**: on every iteration of the event loop, user space copies the entire array of `N` descriptors into Ring 0, the kernel walks all `N` descriptors to register wait-queue callbacks, and user space scans all `N` entries again on return to locate the `K` active sockets. When `N = 50,000` connections and only `K = 10` are active, O(N) scanning dominates CPU time.

Modern kernels eliminate this scan via stateful interest sets (`epoll` on Linux, `kqueue` on Darwin/BSD, and completion-based `io_uring` on Linux 5.1+). The application registers each socket once upon `accept()`; when packets arrive, the network interrupt handler appends that socket directly onto a kernel ready queue, reducing event retrieval from O(N) to **O(K)** where `K` is the number of ready sockets. Production runtimes including Nginx, Envoy, Node.js (`libuv`), and Rust's Tokio are built atop these O(K) interfaces.

**Listing 13-5. Contrast: a thread-per-connection echo server and client (Rust).**

```rust
{{#include ../code/ch13/thread_echo.rs}}
```

**Output 13-5.**

```text
{{#include ../code/out/ch13_thread_echo_rs.out}}
```
