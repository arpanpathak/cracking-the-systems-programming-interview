# 15. Daemon Lifecycle and Service Supervision

A daemon is a specialized process designed for long-running background execution, decoupled from any interactive terminal. While traditional daemons implement explicit detachment rituals to sever ties with their launching shell, modern operating systems have evolved toward a supervision-based model where central init systems (such as `launchd` on macOS and Darwin, or `systemd` on Linux) manage the lifecycle, socket activation, resource boundaries, and fault recovery of background services.

## 15.1 The Ritual of Detachment

To transition from a terminal-bound process to a fully independent daemon in a standalone environment, a program undergoes four ordered stages designed to sever every kernel linkage to the launching session and controlling terminal:

1. **Session Decoupling (First Fork):** The process invokes `fork()`, and the parent immediately calls `_exit(0)`, returning control to the launching shell. The child is reparented to PID 1 and is guaranteed **not** to be a process group leader (its new PID differs from its inherited PGID).
2. **Session Leadership (`setsid`):** The child invokes `setsid()` to create a brand-new session and process group with itself as leader, detaching completely from its original controlling terminal so terminal signals (`SIGHUP` on logout, `SIGINT` on Ctrl-C) can never reach it.
3. **Terminal Prevention (Second Fork):** Because POSIX allows a session leader without a controlling terminal to inadvertently acquire one if it ever calls `open()` on a tty device (without `O_NOCTTY`), a second `fork()` exits the session leader so the grandchild daemon is never a session leader and can never acquire a controlling terminal.
4. **Environment Sanitization:** The grandchild restricts default file permissions via `umask()`, moves its working directory to `/` via `chdir("/")` so it cannot pin a mounted volume against unmounting, redirects descriptors `0`, `1`, and `2` (`stdin`, `stdout`, `stderr`) to `/dev/null` or a log file via `dup2()`, and writes its PID into a **pidfile**.

<figure>
<img src="figures/ch15_daemonize.svg" alt="The four daemonization steps: fork, setsid, fork again, redirect stdio and write the pidfile"/>
</figure>

### 15.1.1 The Detachment System Call Interface (`setsid`, `umask`, `chdir`, `dup2`)

Listings 15-1 and 15-2 invoke four specialized environment-control system calls alongside `fork()`, `open()`, and `sigaction()`:

```text
pid_t  setsid(void);
mode_t umask(mode_t mask);
int    chdir(const char *path);
int    dup2(int oldfd, int newfd);
```

- **`setsid()`:** Takes no parameters. If the calling process is not already a process group leader, the kernel creates a new session and a new process group whose IDs both equal the caller's PID, strips any controlling terminal association, and returns the new session ID (`pid_t > 0`). If the caller *is* already a process group leader, `setsid()` fails and returns `(pid_t)-1` with `errno = EPERM`, which is precisely why the first `fork()` must precede `setsid()`.
- **`umask(mask)`:** Sets the process's file-mode creation mask to `mask` and returns the previous mask (this call never fails). Whenever the daemon subsequently creates a file with `open(..., mode)` or `fopen()`, the kernel clears every bit set in `umask` (`effective_permissions = mode & ~umask`). Passing octal **`0027`** (`0o027` in Rust) clears group-write (`2`) and all permissions for others (`7`), ensuring newly created log files and pidfiles are readable/writable by the owner, at most readable by the group, and completely inaccessible to unprivileged users.
- **`chdir(path)`:** Changes the process's current working directory to `path`, returning `0` on success or `-1` on error (`ENOENT`, `EACCES`). Because the kernel keeps the working directory's mount point pinned as busy while any process sits inside it, moving to `"/"` prevents a long-running daemon from blocking administrative `umount` operations.
- **`dup2(oldfd, newfd)`:** Atomically closes `newfd` (if currently open) and duplicates `oldfd` onto slot `newfd` in the process's file descriptor table so both slots point to the identical kernel open file description. In Listing 15-1, opening `logfile` and calling `dup2(fd, STDOUT_FILENO)` (`1`) and `dup2(fd, STDERR_FILENO)` (`2`) followed by `close(fd)` redirects all subsequent `printf()` and error writes directly into the log file without leaking an extra descriptor; similarly, `dup2(devnull, STDIN_FILENO)` (`0`) ensures any library read from `stdin` receives immediate EOF. Returns `newfd` on success or `-1` on error (`EBADF`, `EMFILE`).

## 15.2 Signal-Driven Management and the Lifecycle Interface

The primary administrative interface for a standalone daemon consists of signals paired with its pidfile:
- **`SIGHUP` (Signal Hangup):** Conventionally repurposed to instruct the daemon to reload configuration files and rotate log handles without dropping active connections.
- **`SIGTERM` (Signal Terminate):** Requests a graceful shutdown. The handler sets an atomic stop flag (`g_stop = 1` / `STOP.store(true, Ordering::Relaxed)`), allowing the main loop to finish in-flight work, flush logs, call `unlink(pidfile)`, and exit cleanly.
- **`SIGKILL` (Uncatchable Kill):** Forcibly terminates the process immediately in kernel mode when a daemon fails to exit within the supervisor's grace period after `SIGTERM`.

**Listing 15-1. A daemon from start to shutdown (C++20).**

```cpp
{{#include ../code/ch15/daemon.cpp}}
```

**Output 15-1. The C++ daemon.**

```text
{{#include ../code/out/ch15_daemon.out}}
```

**Listing 15-2. The same daemon in Rust.**

```rust
{{#include ../code/ch15/daemon.rs}}
```

**Output 15-2. The Rust daemon.**

```text
{{#include ../code/out/ch15_daemon_rs.out}}
```

<div class="callout keyidea">
<span class="label">Key idea</span>

A daemon's interface is three artifacts: a pidfile that names it, a log that records it, and signal handlers that steer it. In standalone systems, the double-fork ritual is merely plumbing; the signal-driven lifecycle is the true contract.

</div>

## 15.3 Service Supervision and On-Demand Activation: `launchd` and `systemd`

In modern production environments (particularly cloud server operating systems and Apple platforms), the manual detachment ritual is replaced by centralized **service supervision**. Central supervisors, such as Apple's `launchd` and Linux's `systemd`, operate as PID 1, managing daemons as direct child processes.

### 15.3.1 The Foreground Daemon Model

Supervised services must run in the **foreground**:
- The daemon does not invoke `fork()` or `setsid()`.
- The daemon does not manage its own pidfile or redirect standard I/O to `/dev/null`.
- The supervisor starts the binary directly as an immediate child.

If a daemon double-forks under a supervisor, it severs parentage, causing the supervisor to believe the service terminated prematurely. By retaining direct parentage, the supervisor tracks the true PID reliably, observes exact exit codes, enforces memory and CPU limits via cgroups or task policies, and aggregates log streams written directly to `stdout`/`stderr`.

### 15.3.2 Socket-Based On-Demand Activation

A major architectural innovation pioneered by Apple's `launchd` (and subsequently adopted by `systemd`) is **socket activation**. Traditional init scripts enforce fragile boot-order dependency chains: a logging daemon must start before a database daemon, which must start before an application server. If one daemon stalls, downstream services time out.

Under socket activation, the supervisor creates and binds the listening sockets (Unix domain sockets or TCP ports) *before* the daemon ever launches:
1. `launchd` parses the service descriptor (`.plist` on Darwin) and binds listening sockets on designated ports or Mach endpoints.
2. When a client connects, the kernel queues the incoming connection on the bound socket.
3. `launchd` detects socket readiness, spawns the daemon process on demand, and passes the pre-bound listening descriptor directly to the child (typically file descriptor 3, or retrieved via `launch_activate_socket()`).
4. The daemon invokes `accept()` immediately with zero startup race conditions.

## 15.4 Asynchronous Fault Detection and Process Monitoring via `kqueue`

In distributed infrastructure and cloud platforms, daemons frequently act as local supervisors that manage worker processes, telemetry sidecars, and hardware accelerators. A supervisor must detect worker crashes and hardware faults instantaneously.

### 15.4.1 The Limits of Signal-Based Monitoring (`SIGCHLD`)

Traditional Unix process monitoring relies on `SIGCHLD` and `waitpid()`. However, signal-based monitoring exhibits two architectural constraints in complex event-driven supervisors:
- **Signal Coalescence:** Standard POSIX signals do not queue. If multiple children exit simultaneously, the kernel coalesces multiple `SIGCHLD` deliveries into one pending bit, forcing non-blocking `waitpid(-1, &status, WNOHANG)` drain loops.
- **Async-Signal Safety Restrictions:** Inside a `SIGCHLD` handler, a supervisor cannot allocate memory, lock standard mutexes, or update complex in-memory worker tables without risking self-deadlock, typically requiring a self-pipe wakeup trick to hand off notification to the main loop.

### 15.4.2 Event-Driven Supervision with `EVFILT_PROC` and the `struct kevent` Interface

On Apple Darwin and BSD-derived kernels, **`kqueue`** unifies socket readiness, timers, filesystem changes, and process lifecycle monitoring inside one stateful kernel event queue. Rather than installing a signal handler, a supervisor registers an `EVFILT_PROC` filter directly on a child PID and receives termination notifications synchronously inside its main event loop.

```text
struct kevent {
    uintptr_t ident;  // Identifier for this event (e.g., fd, signal number, or child PID)
    int16_t   filter; // Kernel event subsystem (EVFILT_READ, EVFILT_TIMER, EVFILT_PROC)
    uint16_t  flags;  // Registration action flags (EV_ADD, EV_ENABLE, EV_DELETE, EV_ONESHOT)
    uint32_t  fflags; // Filter-specific sub-flags (for EVFILT_PROC: NOTE_EXIT, NOTE_FORK)
    intptr_t  data;   // Filter-specific payload (readable bytes, or exit status metadata)
    void     *udata;  // Opaque user-space context pointer returned untouched by the kernel
};

int  kqueue(void);
void EV_SET(struct kevent *kev, uintptr_t ident, int16_t filter, uint16_t flags,
            uint32_t fflags, intptr_t data, void *udata);
int  kevent(int kq, const struct kevent *changelist, int nchanges,
            struct kevent *eventlist, int nevents, const struct timespec *timeout);
```

Each primitive and structure field serves a distinct role in Listings 15-3 and 15-4:
- **`kqueue()`:** Allocates a new empty kernel event queue and returns a file descriptor (`kq >= 0`), or `-1` on error (`EMFILE`, `ENOMEM`). Unlike regular descriptors, a `kqueue` descriptor is not inherited across `fork()` and must be closed via `close(kq)` when finished.
- **`EV_SET(&change, pid, EVFILT_PROC, EV_ADD | EV_ENABLE, NOTE_EXIT, 0, nullptr)`:** Helper macro that initializes every field of a `struct kevent` cleanly:
  - **`ident = pid`:** The target child process ID to monitor.
  - **`filter = EVFILT_PROC`:** Attaches the event to the kernel's process-lifecycle monitor.
  - **`flags = EV_ADD | EV_ENABLE`:** Inserts the filter into `kq` (`EV_ADD`) and marks it active for delivery (`EV_ENABLE`).
  - **`fflags = NOTE_EXIT`:** Requests notification the instant the child terminates (additional `EVFILT_PROC` flags include `NOTE_EXITSTATUS`, `NOTE_FORK`, and `NOTE_EXEC`).
  - **`data = 0`, `udata = nullptr`:** Unused on input registration; `udata` can carry a pointer to a supervisor's internal worker struct so event dispatch executes in O(1) without a hash lookup.
- **`kevent(kq, changelist, nchanges, eventlist, nevents, timeout)`:** Performs registration and waiting through a single unified system call:
  - **Registration phase (`changelist`, `nchanges`):** Applies `nchanges` modifications from `changelist` to `kq`. Passing `eventlist = nullptr, nevents = 0` (the first `kevent()` call in Listing 15-3) registers the `EVFILT_PROC` interest and returns `0` immediately without blocking.
  - **Retrieval phase (`eventlist`, `nevents`, `timeout`):** Waits until up to `nevents` registered events fire or `timeout` elapses (`nullptr` blocks indefinitely; `timespec{0, 0}` polls without blocking). Passing `changelist = nullptr, nchanges = 0` (the second `kevent()` call in Listing 15-3) blocks until the child exits and fills `event`.
  - **Return value:** Returns the number of ready events written into `eventlist` (`> 0`), `0` if `timeout` expired, or `-1` on error (`EBADF`, `EINTR`, `ESRCH` if `pid` already exited before registration). Once `event.fflags & NOTE_EXIT` fires, the supervisor calls `waitpid(pid, &status, WNOHANG)` to reap the zombie PCB and extract `WEXITSTATUS(status)`.

**Listing 15-3. Process supervision via `kqueue` (C++20).**

```cpp
{{#include ../code/ch15/kqueue_supervisor.cpp}}
```

**Output 15-3. The C++ supervisor output.**

```text
{{#include ../code/out/ch15_kqueue_supervisor.out}}
```

**Listing 15-4. The same supervisor in Rust.**

```rust
{{#include ../code/ch15/kqueue_supervisor.rs}}
```

**Output 15-4. The Rust supervisor output.**

```text
{{#include ../code/out/ch15_kqueue_supervisor_rs.out}}
```

## 15.5 Fault Recovery Policies and Health Checks

Detecting a failure is only the first half of high-availability systems software; the second half is executing a deterministic recovery policy.

### 15.5.1 Crash Loops and Exponential Backoff

When a daemon crashes due to an unrecoverable condition (such as corrupted persistent state, a missing configuration file, or dead hardware), an unconstrained supervisor will repeatedly restart the process in an infinite tight loop. This "crash-loop" consumes 100% CPU capacity and fills storage disks with repetitive panic dumps.

Production supervisors implement **restart rate limiting**:
- **`launchd` `ThrottleInterval`:** Enforces a minimum delay (defaulting to 10 seconds) between successive restarts of an exiting job.
- **Exponential Backoff:** Each consecutive failure doubles the restart delay (1s → 2s → 4s → 8s...) up to a maximum threshold. If the service achieves steady-state operation for a configured duration, the failure counter resets.

### 15.5.2 Watchdog Timers and Liveness Probing

A process failure does not always manifest as an abrupt crash. Daemons frequently succumb to deadlocks, infinite spin loops, or hung network I/O, where the process remains alive in the process table but stops serving requests.

Supervisors resolve hung processes via **watchdogs**:
- **Software Watchdogs:** The daemon must periodically ping the supervisor (for example, via an IPC keepalive message or updating a shared memory timestamp) within a negotiated interval (such as every 5 seconds). If the daemon misses two consecutive heartbeats, the supervisor assumes a deadlock, collects a diagnostic backtrace, and issues `SIGABRT` or `SIGKILL`.
- **Hardware Watchdogs:** For bare-metal hypervisors and low-level system controllers, the supervisor itself resets a hardware watchdog timer (`/dev/watchdog` or a microcontroller PMU register). If the entire kernel or root supervisor deadlocks, the hardware timer expires, triggering a physical machine reset.

<div class="callout caution">
<span class="label">Watch out</span>

Three common daemon failure modes:
1. **Double-daemonizing under a supervisor:** Invoking `fork()` and `setsid()` inside a `launchd` or `systemd` unit causes the supervisor to track the short-lived parent, leaving the actual worker orphaned and unmanaged.
2. **Blocking during `SIGTERM` cleanup:** Handling `SIGTERM` by initiating network requests that block on remote services. When the supervisor's grace period expires, `SIGKILL` forcibly kills the process, leaving intermediate state half-written.
3. **Stale pidfiles:** Relying on pidfiles without verifying process identity. If a crashed daemon leaves a stale pidfile, another unrelated process may later spawn with that reused PID, causing administrative scripts to kill innocent services.

</div>

<div class="callout summary">
<span class="label">Summary</span>

- Standalone daemons isolate themselves via a 4-step detachment ritual (`fork`, `setsid`, `fork`, `umask`/`chdir`/`dup2`), pidfiles, and signal handlers.
- Modern cloud and Apple OS architectures supervise daemons in the foreground, delegating process tracking, logging, and sandboxing to `launchd` or `systemd`.
- Socket activation decouples service boot ordering, allowing daemons to start lazily on demand.
- Event-driven monitoring via `kqueue` (`EVFILT_PROC` and `struct kevent`) delivers deterministic child exit notifications on the supervisor's main event loop, bypassing the fragility of `SIGCHLD`.
- High-availability recovery relies on exponential backoff restart limits and watchdog heartbeats to resolve deadlocks.

</div>
