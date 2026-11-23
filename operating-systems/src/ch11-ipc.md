# 11. Inter-Process Communication (IPC)

While threads within a single process share an address space and coordinate directly through memory and synchronization primitives, processes are isolated by hardware page tables. **Inter-Process Communication (`IPC`)** provides controlled kernel-mediated channels through which isolated processes exchange data and synchronize execution without surrendering memory protection.

This isolation creates a core systems trade-off: how can two mutually untrusted or fault-isolated processes exchange gigabytes of data per second while maintaining clean lifecycle semantics, backpressure, and crash safety? Routing bytes through kernel buffers guarantees automatic flow control and crisp failure notification when a peer exits, at the cost of copying every byte twice across the privilege boundary. Aliasing physical memory frames across address tables eliminates every kernel copy, yet forces user space to solve cross-process synchronization, memory ordering, and peer-crash recovery directly. Understanding the internal mechanics of pipes, shared memory, and Unix domain sockets allows systems engineers to choose the right channel for each control plane or data plane.

## 11.1 Unidirectional Byte Streams: Pipes

A **pipe** is a unidirectional, kernel-resident ring buffer exposed to user space as a pair of ordinary file descriptors. Because open file descriptors are inherited across `fork()`, a parent process can create a pipe before forking and establish an immediate communication channel with its child (Figure 11-1).

Internally, a Linux pipe is implemented as an array of `struct pipe_buffer` descriptors referencing 16 physical 4 KiB pages (a 64 KiB ring buffer by default, resizable per pipe via `fcntl(fd, F_SETPIPE_SZ, bytes)` up to `/proc/sys/fs/pipe-max-size`; macOS dynamically scales pipe buffers between 16 KiB and 64 KiB). The kernel maintains a producer index (`head`) and a consumer index (`tail`) protected by a per-pipe spinlock or mutex, together with two wait queues: one for readers sleeping on an empty pipe and one for writers sleeping on a full pipe. When a fast producer outruns a slow consumer and fills all 64 KiB, the kernel puts the producer to sleep on the writer wait queue until the consumer drains space. This built-in **backpressure** prevents unbounded memory consumption without requiring any application-level flow-control protocol.

### 11.1.1 `PIPE_BUF` Atomicity and `SIGPIPE` / `EPIPE` Teardown Semantics

Two kernel invariants govern concurrent access and teardown on every pipe: **`PIPE_BUF` write atomicity** and **broken-pipe signaling**.

The **Portable Operating System Interface (`POSIX`)** standard guarantees that any `write()` to a pipe of at most `PIPE_BUF` bytes (at least 512 bytes by standard; 4,096 bytes on both Linux and macOS) is **atomic**: the kernel copies all bytes of that write into the ring buffer contiguously without interleaving bytes from another concurrent writer. Consider two worker processes sharing an inherited log pipe. If each worker emits 120-byte structured log records (`120 <= 4,096`), every record arrives intact at the log collector even with zero user-space locks. If those workers instead emit 8,192-byte records (`8,192 > 4,096`), the kernel may fit the first 4,096 bytes into the remaining ring buffer, sleep the first writer while the pipe is full, accept 4,096 bytes from the second writer once space opens, and deliver an interleaved, corrupted stream to the reader. Any multi-writer protocol exceeding `PIPE_BUF` must serialize writes externally or give each producer a dedicated pipe.

Teardown semantics operate asymmetrically in the two directions. Every open descriptor referencing the read end increments the pipe's `readers` reference count; every open descriptor referencing the write end increments its `writers` reference count. When `writers` drops to zero, a reader drains any remaining buffered bytes and then receives `0` from `read()`, signaling clean **End-of-File (`EOF`)**. Conversely, when `readers` drops to zero while a writer still attempts to write (for example, in the shell pipeline `yes | head -n 5` after `head` reads five lines and exits), the kernel refuses to buffer bytes that no process can ever consume. Instead, the kernel delivers **Broken Pipe (`SIGPIPE`)** to the writing thread. Because the default disposition of `SIGPIPE` terminates the process, `yes` exits immediately instead of spinning forever. Long-lived daemons and network servers, however, cannot allow a disconnected client or worker to kill the entire server process; they set `SIGPIPE` to `SIG_IGN` at startup (or pass `MSG_NOSIGNAL` on sockets) so the failed `write()` returns `-1` with `errno = EPIPE`, allowing orderly connection cleanup.

### 11.1.2 The `pipe` System Call Interface and Stream Semantics

```c
int     pipe(int pipefd[2]);
ssize_t read(int fd, void *buf, size_t count);
ssize_t write(int fd, const void *buf, size_t count);
int     close(int fd);
```

Calling `pipe(pipefd)` allocates a single kernel pipe buffer and populates `pipefd` with two newly opened file descriptors: `pipefd[0]` is the **read end** (writing to it fails with `EBADF`), and `pipefd[1]` is the **write end** (reading from it fails with `EBADF`). It returns `0` on success or `-1` on failure (`EMFILE`, `ENFILE`, or `EFAULT`). On Linux, `pipe2(pipefd, O_CLOEXEC | O_NONBLOCK)` sets close-on-exec and non-blocking flags atomically at creation time, closing the multi-threaded `fork`/`exec` descriptor-leak window.

On the read end, `read(fd, buf, count)` copies up to `count` available bytes from the kernel ring buffer into `buf`, returning immediately with `1 <= n <= count` whenever data is present. If the buffer is empty and at least one open write descriptor still exists, `read()` blocks until data arrives or all writers close; once zero open write descriptors remain system-wide, `read()` returns `0` (`EOF`). On the write end, `write(fd, buf, count)` copies bytes into the ring buffer, blocking when the buffer is full.

Three operational invariants prevent classic pipe bugs. First, both parent and child must **close their unused ends immediately after `fork()`**: because `fork()` duplicates both descriptors, the reference count on each end becomes `2`. If the parent forgets to close `pipefd[1]`, the writer reference count never drops to zero even after the child exits, causing the parent's `read()` to block forever instead of observing `EOF`. Second, multi-kilobyte workloads must loop over partial `read()` and `write()` transfers. Third, because pipes are **First-In, First-Out (`FIFO`)** raw byte streams that do not preserve write boundaries (two consecutive 10-byte writes may be returned by one 20-byte `read()`), structured protocols must layer explicit message framing such as a length prefix or newline delimiter.

<figure>
<img src="figures/ch11_pipe.svg" alt="A kernel-buffered byte stream between a writing child and a reading parent"/>
</figure>

**Listing 11-1. One pipe, one fork, and one message (C++20).**

```cpp
{{#include ../code/ch11/pipe.cpp}}
```

**Output 11-1.**

```text
{{#include ../code/out/ch11_pipe.out}}
```

**Listing 11-2. The same program in Rust.**

```rust
{{#include ../code/ch11/pipe.rs}}
```

**Output 11-2.**

```text
{{#include ../code/out/ch11_pipe_rs.out}}
```

## 11.2 Zero-Copy Communication: Shared Memory

Every byte transmitted through a pipe or socket traverses the kernel twice: once via `copy_from_user` into the kernel ring buffer during `write()`, and a second time via `copy_to_user` into the receiver's buffer during `read()`. For high-throughput workloads such as database buffer pools, video pipelines, and telemetry rings, **shared memory** eliminates both copies by mapping the exact same physical **Random-Access Memory (`RAM`)** frames into the page tables of multiple processes simultaneously (Figure 11-2). Once mapped, stores executed by one process become visible to peer processes at hardware cache-coherency speeds with zero system calls.

An explicit bandwidth calculation illustrates why high-throughput data planes abandon pipes in favor of shared memory. Suppose a producer transfers `1 GiB` (`1,073,741,824` bytes) to a consumer. Over a 64 KiB pipe, the transfer requires `1,073,741,824 / 65,536 = 16,384` `write()` calls and `16,384` `read()` calls (`32,768` privilege transitions in total). More significantly, `write()` reads `1 GiB` from sender `RAM` and writes `1 GiB` into the kernel ring buffer (`2 GiB` of memory-bus traffic), and `read()` reads `1 GiB` from the ring buffer and writes `1 GiB` into receiver `RAM` (`2 GiB` more), generating `4 GiB` of total memory-bus traffic and polluting the **Level 3 (`L3`)** cache with intermediate kernel copies. Over a `MAP_SHARED` ring buffer, the producer writes `1 GiB` once into the shared physical frames and the consumer reads `1 GiB` directly from those identical frames (`2 GiB` total bus traffic, a 50% reduction), with zero system calls in the uncontended steady state.

### 11.2.1 Named Shared Memory (`shm_open`), Cache Coherency, and `memfd` Sealing

Anonymous `MAP_SHARED | MAP_ANON` mappings work cleanly between a parent and children created via `fork()`, as in Listings 11-3 and 11-4, because the child inherits the parent's virtual memory mappings directly. Unrelated processes lacking a common ancestor instead rendezvous through `POSIX` named shared memory:

```c
int shm_open(const char *name, int oflag, mode_t mode);
int ftruncate(int fd, off_t length);
int shm_unlink(const char *name);
```

Calling `shm_open("/telemetry_ring", O_CREAT | O_RDWR, 0600)` creates or opens a named shared-memory object (backed by an in-memory `tmpfs` mount at `/dev/shm` on Linux) and returns an ordinary file descriptor. A freshly created shared-memory object has a size of `0` bytes; the creator must call `ftruncate(fd, size)` before mapping it with `mmap(nullptr, size, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0)`. Accessing a mapped address beyond the underlying object's truncated length triggers a hardware **Bus Error (`SIGBUS`)** rather than allocating pages. Once all peers have mapped the descriptor, calling `shm_unlink("/telemetry_ring")` removes the name from the namespace while keeping the physical frames alive until the last mapping is unmapped and the last descriptor is closed.

Because hardware page tables translate two distinct virtual addresses in Process A and Process B to the identical physical address, processor **cache-coherency protocols** (such as **MESI** or **MOESI**) automatically maintain coherence across **Central Processing Unit (`CPU`)** cores without kernel intervention. Atomic operations (`std::atomic` with `memory_order_release` / `memory_order_acquire`, or Rust `AtomicU64`) and lock-free single-producer/single-consumer ring buffers therefore function identically across process boundaries as long as the shared data structure avoids raw pointers (using integer byte offsets instead, because the two processes may map the shared region at different virtual base addresses).

Sharing memory between mutually untrusted processes (such as a display server and an untrusted graphical application) introduces a subtle denial-of-service hazard known as the **`SIGBUS` truncation attack**. If an untrusted client opens a `shm_open` file, passes the file descriptor to the server, waits for the server to `mmap()` it, and then calls `ftruncate(fd, 0)`, the server immediately crashes with `SIGBUS` the next time it dereferences a byte inside the mapped buffer. Linux eliminates this hazard via **`memfd_create(2)`** combined with **file sealing**: the sender allocates an anonymous in-memory file with `memfd_create("frame", MFD_ALLOW_SEALING)`, writes its payload, and applies `fcntl(fd, F_ADD_SEALS, F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_WRITE | F_SEAL_SEAL)`. Before mapping the buffer, the receiver queries `fcntl(fd, F_GET_SEALS)` to verify that `F_SEAL_SHRINK` and `F_SEAL_SEAL` are present. Once sealed, the kernel rejects any subsequent `ftruncate()` or write mutation on that descriptor, guaranteeing that the receiver can read the shared pages safely without risking `SIGBUS` or time-of-check-to-time-of-use (**`TOCTOU`**) modification.

### 11.2.2 `MAP_SHARED` Mappings and Process-Shared Mutex Attributes

Removing kernel buffering shifts synchronization and failure-recovery responsibility entirely onto the application: concurrent processes mutating a shared region face the exact same read-modify-write atomicity gap as threads (as seen in Chapter 4). Listings 11-3 and 11-4 place both a `pthread_mutex_t` and a 64-bit counter inside one shared virtual page:

```c
void *mmap(void *addr, size_t length, int prot, int flags, int fd, off_t offset);
int   pthread_mutexattr_init(pthread_mutexattr_t *attr);
int   pthread_mutexattr_setpshared(pthread_mutexattr_t *attr, int pshared);
int   pthread_mutex_init(pthread_mutex_t *mutex, const pthread_mutexattr_t *attr);
int   pthread_mutex_destroy(pthread_mutex_t *mutex);
```

Both `MAP_SHARED | MAP_ANON` and `MAP_PRIVATE | MAP_ANON` allocate zero-initialized anonymous memory (`fd = -1`, `offset = 0`, `prot = PROT_READ | PROT_WRITE`), but they diverge across `fork()`. Under `MAP_PRIVATE`, the kernel marks both parent and child **Page Table Entries (`PTE`s)** read-only and performs **Copy-on-Write (`COW`)** on the first store, splitting them onto isolated frames. Under `MAP_SHARED`, both processes' `PTE`s continue pointing to the identical writable physical frame, establishing true zero-copy shared memory.

By default, a `pthread_mutex_t` initialized with `nullptr` attributes uses `PTHREAD_PROCESS_PRIVATE`, allowing the runtime to key its futex wait queue strictly on the calling process's virtual address (`FUTEX_PRIVATE_FLAG` on Linux). Locking a private mutex across distinct processes produces undefined behavior because their wait queues do not match. Calling `pthread_mutexattr_init(&attr)` followed by `pthread_mutexattr_setpshared(&attr, PTHREAD_PROCESS_SHARED)` configures `pthread_mutex_init(&s->mu, &attr)` to hash futex wait queues on the underlying physical memory object. Each `pthread_*` function returns `0` on success or a positive `POSIX` error code directly (without setting `errno`).

Cross-process locks also introduce a failure mode absent from single-process threads: if Process A acquires a shared mutex and is terminated abruptly by `SIGKILL`, the mutex stays locked forever and Process B hangs indefinitely. Production shared-memory services mitigate this by setting `pthread_mutexattr_setrobust(&attr, PTHREAD_MUTEX_ROBUST)`. When a holder dies while owning a robust mutex, the kernel wakes the next waiter and returns `EOWNERDEAD` from `pthread_mutex_lock()`, allowing the survivor to repair any partially updated shared invariants and call `pthread_mutex_consistent()` before unlocking. Once `waitpid()` confirms the child has exited, the parent invokes `pthread_mutex_destroy(&s->mu)` and `munmap(s, sizeof(Shared))`.

<figure>
<img src="figures/ch11_shm.svg" alt="Two page tables mapping one physical frame into two processes"/>
</figure>

**Listing 11-3. A counter in shared memory, protected by a process-shared mutex (C++20).**

```cpp
{{#include ../code/ch11/shm_counter.cpp}}
```

**Output 11-3. The counter reaches exactly 1,000,000.**

```text
{{#include ../code/out/ch11_shm_counter.out}}
```

**Listing 11-4. The same process-shared mutex counter in Rust.**

```rust
{{#include ../code/ch11/shm_counter.rs}}
```

**Output 11-4.**

```text
{{#include ../code/out/ch11_shm_counter_rs.out}}
```

## 11.3 Bidirectional Channels: Unix Domain Sockets and `SCM_RIGHTS`

A pipe supports data flow in only one direction; implementing request-response communication with pipes requires two separate pipes and careful descriptor management to avoid deadlock. A **Unix domain socket** (`AF_UNIX` or `AF_LOCAL`) provides a single **full-duplex** (bidirectional) local channel backed by two independent kernel send/receive buffers so both peers can transmit and receive simultaneously. Unlike network sockets, `AF_UNIX` routes traffic strictly through local kernel memory without **Internet Protocol (`IP`)** headers, checksums, or network-interface serialization.

Unix domain sockets support three distinct communication models. `SOCK_STREAM` delivers a reliable, ordered byte stream analogous to a **Transmission Control Protocol (`TCP`)** connection without message boundaries. `SOCK_DGRAM` delivers discrete datagrams with preserved boundaries (and unlike network **User Datagram Protocol (`UDP`)**, local `AF_UNIX` datagrams are reliable and delivered in order on Linux and macOS). `SOCK_SEQPACKET` combines connection-oriented lifecycle management with strict message-boundary preservation, making it well suited for local **Remote Procedure Call (`RPC`)** framing.

### 11.3.1 File-Descriptor Passing (`SCM_RIGHTS`) and Peer Credentials

Beyond ordinary byte payloads, `AF_UNIX` sockets provide a kernel capability unavailable to pipes or shared memory: **passing live open file descriptors across process boundaries**. Sending an integer such as `fd = 5` as raw bytes over a pipe is useless because file descriptor tables are private to each process; slot `5` in the receiver either is closed or points to a completely unrelated file.

Using `sendmsg(2)` and `recvmsg(2)` with an ancillary control message (`struct cmsghdr`) of level `SOL_SOCKET` and type **`SCM_RIGHTS`**, a sender asks the kernel to transfer the underlying *open file description* referenced by `fd = 5`. Inside the kernel, `sendmsg()` looks up the sender's kernel `struct file` pointer, increments its reference count, and attaches it to the socket's receive queue alongside the message bytes. When the receiver invokes `recvmsg()`, the kernel allocates the lowest unused descriptor slot in the receiver's descriptor table (for example, `fd = 9`), points slot `9` at the transferred `struct file`, and writes `9` into the receiver's ancillary buffer. Both processes now share the exact same open file description (including its file offset and access mode), even if they are completely unrelated processes with no `fork()` lineage.

This capability underpins modern **privilege-separated architectures** such as web browsers, container runtimes, and `systemd` socket activation. An untrusted renderer or sandboxed worker process can drop all filesystem privileges via `seccomp` and `chroot`, retaining only a single `AF_UNIX` socket connected to a small, audited broker process. When the sandboxed worker needs to read a user-selected document or map a `memfd` buffer, the broker validates the policy, opens the file, and transfers the live descriptor over `SCM_RIGHTS`. Complementary control messages (`SO_PEERCRED` on Linux; `getpeereid` on macOS/`BSD`) allow the broker to inspect the kernel-verified **Process Identifier (`PID`)**, **User Identifier (`UID`)**, and **Group Identifier (`GID`)** of the remote socket peer, which a malicious client cannot forge.

### 11.3.2 The `socketpair` System Call Interface

```c
int socketpair(int domain, int type, int protocol, int sv[2]);
```

Calling `socketpair(AF_UNIX, SOCK_STREAM, 0, sv)` creates a pre-connected pair of symmetric local descriptors in `sv[0]` and `sv[1]`, returning `0` on success or `-1` on error (`EAFNOSUPPORT`, `EOPNOTSUPP`, `EMFILE`, `EFAULT`). Passing `protocol = 0` selects the domain default. Unlike `pipe()`, either endpoint can both read and write: after `fork()`, the child closes `sv[0]` and keeps `sv[1]`, while the parent closes `sv[1]` and keeps `sv[0]`. For unrelated processes, a server instead calls `socket(AF_UNIX, ...)`, `bind()` to a filesystem path (such as `/run/app.sock`), and `listen()`, while clients call `connect()` to that path.

**Listing 11-5. A two-way channel between parent and child (C++20).**

```cpp
{{#include ../code/ch11/socketpair.cpp}}
```

**Output 11-5. Each process sends one message and receives the other.**

```text
{{#include ../code/out/ch11_socketpair.out}}
```

**Listing 11-6. The same bidirectional socketpair in Rust.**

```rust
{{#include ../code/ch11/socketpair.rs}}
```

**Output 11-6.**

```text
{{#include ../code/out/ch11_socketpair_rs.out}}
```

## 11.4 Comparative Analysis of `IPC` Mechanisms

Selecting an `IPC` mechanism balances kernel-managed synchronization, backpressure, and security capabilities against zero-copy throughput:

| Mechanism | Directionality | Data Copying | Message Boundaries | Synchronization & Capabilities | Typical Use Case |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Pipe (`pipe`)** | Unidirectional | Two copies per transfer | Byte stream (`PIPE_BUF` atomic writes) | Kernel-managed blocking, `EOF`, `SIGPIPE` | Shell pipelines, parent/child `stdout` redirection |
| **Shared Memory (`mmap` / `shm_open` / `memfd`)** | Bidirectional | Zero copies (shared physical frames) | Application-defined | Application-managed (`PTHREAD_PROCESS_SHARED`, `PTHREAD_MUTEX_ROBUST`, `memfd` seals) | High-throughput ring buffers, database buffer pools, video frames |
| **Unix Domain Socket (`AF_UNIX`)** | Full-duplex bidirectional | Two copies per transfer | Stream (`SOCK_STREAM`) or messages (`SOCK_DGRAM` / `SOCK_SEQPACKET`) | Kernel-managed blocking, `SCM_RIGHTS` fd passing, `SO_PEERCRED` auth | Worker `RPC` channels, privilege-separated sandboxes, local daemons |

Pipes and Unix domain sockets are preferred whenever kernel-managed blocking, `EOF` detection, `poll`/`kqueue` readiness integration, or capability transfer via `SCM_RIGHTS` simplify system architecture. Shared memory is reserved for latency-critical or bandwidth-bound data planes where eliminating kernel copies justifies explicit cross-process locking, memory-ordering discipline, and robust crash recovery. Many high-performance systems combine both: an `AF_UNIX` control channel passes sealed `memfd` descriptors and wake notifications while the mapped shared memory carries bulk payloads at zero-copy speed.

<div class="callout keyidea">
<span class="label">Key idea</span>

Pipes and Unix domain sockets trade two kernel buffer copies per transfer for built-in backpressure, `EOF` lifecycle signaling, `SCM_RIGHTS` capability passing, and `poll`/`kqueue` integration. `MAP_SHARED` shared memory eliminates every kernel copy by aliasing physical frames across page tables, shifting synchronization and crash recovery onto user space.

</div>

<div class="callout experiment">
<span class="label">Experiment</span>

In Listing 11-1 (`code/ch11/pipe.cpp`), comment out `close(fds[1])` in the parent process and run the binary. Observe that the parent's `read()` blocks indefinitely even after the child exits because the parent itself still holds an open write reference, preventing `EOF`.

</div>

<div class="callout caution">
<span class="label">Common Pitfall</span>

Placing a default-initialized `pthread_mutex_t` (without `PTHREAD_PROCESS_SHARED`) inside `MAP_SHARED` memory. Default mutexes use process-private futex keys (`FUTEX_PRIVATE_FLAG`), causing cross-process lock acquisitions to hash into separate wait queues and produce undefined behavior.

</div>
