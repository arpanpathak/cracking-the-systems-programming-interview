# 11. Inter-Process Communication (IPC)

While threads within a single process share an address space and coordinate directly through memory and synchronization primitives, processes are isolated by hardware page tables. Inter-process communication (IPC) provides controlled kernel-mediated channels through which isolated processes exchange data and synchronize execution without sacrificing memory protection.

## 11.1 Unidirectional Byte Streams: Pipes

A **pipe** is a unidirectional, kernel-resident ring buffer (typically 64 KiB on Linux and 16 to 64 KiB on macOS) exposed to user space as a pair of ordinary file descriptors. Because file descriptors are inherited across `fork()`, a parent process can create a pipe before forking and establish an immediate communication channel with its child.

### 11.1.1 The `pipe` System Call Interface and Stream Semantics

```text
int     pipe(int pipefd[2]);
ssize_t read(int fd, void *buf, size_t count);
ssize_t write(int fd, const void *buf, size_t count);
int     close(int fd);
```

- **`pipe(pipefd)`:** Allocates a single kernel pipe buffer and populates the caller's two-element integer array `pipefd` with two newly opened file descriptors:
  - **`pipefd[0]`:** The **read end** of the pipe (analogous to `stdin`, descriptor `0`). Attempting to `write()` to `pipefd[0]` fails with `EBADF`.
  - **`pipefd[1]`:** The **write end** of the pipe (analogous to `stdout`, descriptor `1`). Attempting to `read()` from `pipefd[1]` fails with `EBADF`.
  - **Return value:** `0` on success, or `-1` on failure with `errno` set (`EMFILE` if the process descriptor table is full, `ENFILE` if the system-wide open-file limit is reached, or `EFAULT` if `pipefd` is not writable).
- **`read(fd, buf, count)` on a pipe:** Copies up to `count` available bytes from the kernel ring buffer into `buf`.
  - If the buffer contains data, `read()` returns the positive byte count transferred (`1 <= n <= count`) immediately, even if fewer than `count` bytes are present.
  - If the buffer is empty and **at least one process still holds an open write descriptor** for the pipe, `read()` blocks the calling thread until data arrives or all write descriptors close.
  - If the buffer is empty and **zero open write descriptors remain across the entire system**, `read()` returns `0`, signaling **End-of-File (EOF)**.
  - Returns `-1` on error (`EINTR`, `EAGAIN` if `O_NONBLOCK` is set on an empty pipe).
- **`write(fd, buf, count)` on a pipe:** Copies bytes from `buf` into the kernel ring buffer.
  - If the buffer is full, `write()` blocks until a reader drains space. POSIX guarantees that writes of at most `PIPE_BUF` bytes (minimum 512 bytes by standard, 4,096 bytes on Linux and macOS) are **atomic**: concurrent writers will not interleave their bytes mid-write.
  - If **zero open read descriptors remain**, the kernel refuses the write, delivers **`SIGPIPE`** to the writing thread (whose default disposition terminates the process), and, if `SIGPIPE` is caught or ignored, returns `-1` with `errno = EPIPE`.

Effective pipe engineering therefore enforces three operational invariants:
- **Closing unused ends immediately after `fork()`:** Because `fork()` duplicates both `pipefd[0]` and `pipefd[1]` into the child, the kernel reference count on each end becomes `2`. If the parent forgets to close its unused write end `pipefd[1]`, the pipe's writer reference count never drops to zero even after the child exits, causing the parent's `read()` to block forever instead of observing EOF.
- **Handling partial transfers:** Because pipes are raw byte streams, `read()` and `write()` in multi-kilobyte workloads must loop until the expected byte count is transferred or EOF is reached.
- **Explicit message framing:** Pipes preserve byte order (FIFO) but do not preserve write boundaries: two consecutive 10-byte `write()` calls may be returned by a single 20-byte `read()`. Applications exchanging structured records must layer a framing protocol such as a fixed-width length prefix or newline delimiter.

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

Every byte transmitted through a pipe or socket traverses the kernel twice: once via `copy_from_user` into the kernel ring buffer during `write()`, and a second time via `copy_to_user` into the receiver's buffer during `read()`. For high-throughput workloads such as database buffer pools, video pipelines, and telemetry rings, **shared memory** eliminates both copies by mapping the exact same physical RAM frames into the page tables of multiple processes simultaneously. Once mapped, stores executed by one process become visible to peer processes at hardware cache-coherence speeds with zero system calls.

### 11.2.1 `MAP_SHARED` Mappings and Process-Shared Mutex Attributes

Removing kernel buffering shifts synchronization responsibility entirely onto the application: concurrent processes mutating a shared region face the exact same read-modify-write atomicity gap as threads (Chapter 4). Listings 11-3 and 11-4 place both a `pthread_mutex_t` and a 64-bit counter inside one shared virtual page using two coordinated interfaces:

```text
void *mmap(void *addr, size_t length, int prot, int flags, int fd, off_t offset);
int   pthread_mutexattr_init(pthread_mutexattr_t *attr);
int   pthread_mutexattr_setpshared(pthread_mutexattr_t *attr, int pshared);
int   pthread_mutex_init(pthread_mutex_t *mutex, const pthread_mutexattr_t *attr);
int   pthread_mutex_destroy(pthread_mutex_t *mutex);
```

- **`MAP_SHARED | MAP_ANON` versus `MAP_PRIVATE | MAP_ANON`:** Both allocate zero-initialized anonymous RAM unbacked by any disk file (`fd = -1`, `offset = 0`, `prot = PROT_READ | PROT_WRITE`). Their critical divergence occurs across `fork()`:
  - With **`MAP_PRIVATE`**, the kernel marks both parent and child Page Table Entries read-only and performs **Copy-on-Write (COW)** on the first store, splitting parent and child onto isolated physical frames so neither observes the other's writes.
  - With **`MAP_SHARED`**, both parent and child PTEs continue pointing to the identical writable physical frame after `fork()`, establishing true zero-copy shared memory. (For unrelated processes that do not share a `fork()` ancestor, POSIX provides `shm_open()` plus `ftruncate()` to obtain a shared file descriptor passed as `fd` to `mmap(..., MAP_SHARED, fd, 0)`.)
- **Process-shared mutex configuration (`pthread_mutexattr_t`):**
  - By default, a `pthread_mutex_t` initialized with `nullptr` attributes uses `PTHREAD_PROCESS_PRIVATE`, allowing the runtime to optimize futex wait-queue keys using only the calling process's virtual address space (`FUTEX_PRIVATE_FLAG` on Linux). Locking a private-attribute mutex from two distinct processes yields undefined behavior because their futex wait queues do not match.
  - Calling `pthread_mutexattr_init(&attr)` initializes an attribute descriptor, and **`pthread_mutexattr_setpshared(&attr, PTHREAD_PROCESS_SHARED)`** instructs `pthread_mutex_init(&s->mu, &attr)` to configure the mutex for cross-process futex hashing keyed on the underlying physical memory object. Each of these `pthread_*` functions returns `0` on success and a positive POSIX error code directly (without setting `errno`) on failure.
  - After `waitpid()` guarantees the child has exited and no process holds the lock, the parent calls `pthread_mutex_destroy(&s->mu)` followed by `munmap(s, sizeof(Shared))` to release the lock state and unmap the virtual page.

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

## 11.3 Bidirectional Channels: Socket Pairs

A pipe supports data flow in only one direction; implementing request-response communication with pipes requires creating two separate pipes and managing four descriptors carefully to avoid deadlock. A **socket pair** provides a single **full-duplex** (bidirectional) local channel between related processes, backed by two independent kernel send/receive buffers so both peers can transmit and receive simultaneously.

### 11.3.1 The `socketpair` System Call Interface

```text
int socketpair(int domain, int type, int protocol, int sv[2]);
```

Each argument configures the local channel before `fork()`:
- **`domain`:** Protocol family. On POSIX systems, `socketpair()` supports **`AF_UNIX`** (also aliased as `AF_LOCAL`), which routes data exclusively through local kernel memory without touching IP headers, checksums, or network interfaces.
- **`type`:** Communication semantics. **`SOCK_STREAM`** provides a reliable, ordered, full-duplex byte stream (identical in framing semantics to a bidirectional pipe or TCP connection); `SOCK_DGRAM` and `SOCK_SEQPACKET` preserve explicit message boundaries.
- **`protocol`:** Selects a specific protocol within the domain; passing **`0`** instructs the kernel to choose the default protocol for `(AF_UNIX, SOCK_STREAM)`.
- **`sv[2]`:** Output array populated with two symmetric, pre-connected file descriptors (`sv[0]` and `sv[1]`). Unlike `pipe()`, neither endpoint is restricted to reading or writing: bytes written to `sv[1]` are read from `sv[0]`, and bytes written to `sv[0]` are read from `sv[1]`. After `fork()`, the child closes `sv[0]` and retains `sv[1]`, while the parent closes `sv[1]` and retains `sv[0]`.
- **Return value:** Returns `0` on success, or `-1` on failure with `errno` set (`EAFNOSUPPORT`, `EOPNOTSUPP`, `EMFILE`, or `EFAULT`). Beyond byte streams, `AF_UNIX` socket pairs also support passing open file descriptors between isolated processes via `sendmsg()`/`recvmsg()` with `SCM_RIGHTS` ancillary control messages, a cornerstone of privilege-separated browser and sandbox architectures.

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

## 11.4 Comparative Analysis of IPC Mechanisms

The selection of an IPC mechanism involves a fundamental trade-off between kernel-managed synchronization simplicity and zero-copy throughput:

| Mechanism | Directionality | Data Copying | Synchronization | Typical Use Case |
| :--- | :--- | :--- | :--- | :--- |
| **Pipe (`pipe`)** | Unidirectional | Two copies per transfer | Kernel-managed (blocking and FIFO ordering) | Shell pipelines, streaming parent/child stdout redirection |
| **Shared Memory (`mmap(MAP_SHARED)`)** | Bidirectional | Zero copies (shared physical frames) | Application-managed (`PTHREAD_PROCESS_SHARED` mutexes or atomics) | High-throughput ring buffers, database buffer pools, telemetry |
| **Socket Pair (`socketpair(AF_UNIX)`)** | Full-duplex bidirectional | Two copies per transfer | Kernel-managed (blocking, ordering, `SCM_RIGHTS` fd passing) | Worker RPC channels, privilege-separated sandboxes |

Pipes and socket pairs are preferred whenever kernel-managed blocking, EOF detection, and poll/kqueue readiness integration simplify system architecture. Shared memory is reserved for latency-critical or bandwidth-bound data planes where eliminating kernel copies justifies explicit cross-process locking and memory-ordering discipline.
