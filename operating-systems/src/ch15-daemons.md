# 15. Daemon Lifecycle and Service Supervision

A daemon is a specialized process designed for long-running background execution, decoupled from any interactive terminal. While traditional daemons implement complex detachment rituals to ensure they are truly independent, modern operating systems have evolved toward a supervision-based model where central init systems—such as `launchd` on macOS and Darwin, or `systemd` on Linux—manage the lifecycle, socket activation, resource boundaries, and fault recovery of background services.

## 15.1 The Ritual of Detachment

To transition from a terminal-bound process to a fully independent daemon in a standalone environment, a program must undergo a sequence of operations designed to sever all ties to the controlling session and its parent terminal. This "daemonization" process involves four critical stages:

1. **Session Decoupling (First Fork):** The process calls `fork`, allowing the parent to exit and returning control to the shell. This places the child in the background.
2. **Session Leadership (setsid):** The child invokes `setsid` to establish a new session. This creates a new session with the child as its leader and, crucially, detaches the process from its original controlling terminal.
3. **Terminal Prevention (Second Fork):** A second `fork` is performed to ensure the resulting grandchild is not a session leader. This prevents the process from inadvertently acquiring a new controlling terminal should it subsequently open a terminal device.
4. **Environment Sanitization:** The process redirects its standard input, output, and error streams to `/dev/null` or a log file, changes its working directory to the root (`/`) to avoid pinning a mounted filesystem, and sets its `umask` to ensure predictable file permissions. Finally, it records its Process ID (PID) in a **pidfile** to facilitate external management.

<figure>
<img src="figures/ch15_daemonize.svg" alt="The four daemonization steps: fork, setsid, fork again, redirect stdio and write the pidfile"/>
</figure>

## 15.2 Signal-Driven Management and the Lifecycle Interface

The primary interface for interacting with a standalone daemon is through signals and its associated pidfile. Standardized signals allow for controlled lifecycle transitions:
- **`SIGHUP` (Signal Hangup):** Conventionally repurposed to instruct the daemon to reload its configuration files and re-open log handles without dropping active connections.
- **`SIGTERM` (Signal Terminate):** Requests a graceful shutdown. The daemon finishes in-flight requests, flushes persistent state, unlinks its pidfile, and terminates cleanly.
- **`SIGKILL` (Uncatchable Kill):** Forcibly destroys the process image immediately, used by supervisors when a daemon fails to respond to `SIGTERM` within a specified grace period.

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

In modern production environments—particularly cloud server operating systems and Apple platforms—the manual detachment ritual is replaced by centralized **service supervision**. Central supervisors, such as Apple's `launchd` and Linux's `systemd`, operate as PID 1, managing daemons as managed child processes.

### 15.3.1 The Foreground Daemon Model

Supervised services must run in the **foreground**:
- The daemon does not invoke `fork()` or `setsid()`.
- The daemon does not manage its own pidfile or redirect standard I/O to `/dev/null`.
- The supervisor starts the binary directly as an immediate child.

If a daemon double-forks under a supervisor, it intentionally severs parentage, causing the supervisor to believe the process has terminated prematurely. By retaining parentage, the supervisor tracks the true PID directly, monitors exit status codes, bounds memory and CPU utilization via cgroups or task policies, and aggregates log streams written to `stdout`/`stderr`.

### 15.3.2 Socket-Based On-Demand Activation

A major architectural innovation pioneered by Apple’s `launchd` (and subsequently adopted by `systemd`) is **socket activation**. Traditional init scripts enforce complex boot-order dependencies: a logging daemon must start before a database daemon, which must start before an application server. If one daemon delays or crashes, the entire dependency tree blocks.

Under socket activation, `launchd` creates and binds the listening sockets (IPC Unix domain sockets or network TCP ports) *before* the daemon is ever launched:
1. `launchd` parses the service descriptor (`.plist` on Darwin) and binds listening sockets on designated ports or Mach port endpoints.
2. When a client process issues a connection request, the kernel buffers the connection.
3. `launchd` detects readiness on the socket, spawns the daemon process, and passes the pre-allocated listening socket directly as an open file descriptor (typically file descriptor 3, or retrieved via `launch_activate_socket()`).
4. The daemon calls `accept()` immediately without needing initialization races.

Socket activation eliminates boot-time startup ordering issues: client connections simply buffer in the kernel while the receiving daemon initializes on demand.

## 15.4 Asynchronous Fault Detection and Process Monitoring via `kqueue`

In distributed infrastructure and cloud platforms, daemons frequently act as local supervisors—managing worker processes, telemetry sidecars, and hardware accelerators. A supervisor must detect worker crashes and hardware faults instantaneously.

### 15.4.1 The Limits of Signal-Based Monitoring (`SIGCHLD`)

Traditional Unix process monitoring relies on the `SIGCHLD` signal and `waitpid()`. However, signal-based monitoring exhibits severe architectural flaws:
- **Signal Coalescence:** POSIX signals do not queue. If multiple child processes terminate simultaneously, the kernel coalesces multiple `SIGCHLD` instances into a single signal, requiring non-blocking `waitpid(-1, &status, WNOHANG)` loops to reap all children.
- **Async-Signal Safety Restrictions:** Inside a signal handler, a process can only execute async-signal-safe functions. Allocating memory, acquiring standard mutexes, or writing to high-level logging libraries inside a `SIGCHLD` handler invokes undefined behavior.

### 15.4.2 Event-Driven Supervision with `EVFILT_PROC`

On Apple Darwin and BSD-derived kernels, the **`kqueue`** subsystem provides a robust, event-driven mechanism for process monitoring. Using the `EVFILT_PROC` filter, a supervisor registers an interest in specific process events directly with the kernel:
- **`NOTE_EXIT`:** Notifies the supervisor immediately when the monitored PID terminates.
- **`NOTE_EXITSTATUS`:** Delivers the child's exit status code directly inside the `kevent` structure (`data` field).
- **`NOTE_FORK` / `NOTE_EXEC`:** Tracks child process forks and binary replacements.

Crucially, `kqueue` delivers process termination events on the **same asynchronous event loop** used for network sockets, timers, and IPC descriptors. The supervisor handles child crashes synchronously in its main event dispatch loop without invoking signal handlers.

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
- **Software Watchdogs:** The daemon must periodically ping the supervisor (e.g., via an IPC keepalive message or updating a shared memory timestamp) within a negotiated interval (e.g., every 5 seconds). If the daemon misses two consecutive heartbeats, the supervisor assumes a deadlock, collects a diagnostic backtrace, and issues `SIGABRT` or `SIGKILL`.
- **Hardware Watchdogs:** For bare-metal hypervisors and low-level system controllers, the supervisor itself pets a hardware watchdog timer (`/dev/watchdog` or a microcontroller PMU register). If the entire kernel or root supervisor deadlocks, the hardware timer expires, triggering a physical machine reset.

<div class="callout caution">
<span class="label">Watch out</span>

Three common daemon failure modes:
1. **Double-daemonizing under a supervisor:** Invoking `fork()` and `setsid()` inside a `launchd` or `systemd` unit causes the supervisor to track the short-lived parent, leaving the actual worker orphaned and unmanaged.
2. **Blocking during `SIGTERM` cleanup:** Handling `SIGTERM` by initiating network requests that block on remote services. When the supervisor's grace period expires, `SIGKILL` forcibly kills the process, leaving intermediate state half-written.
3. **Stale pidfiles:** Relying on pidfiles without verifying process identity. If a crashed daemon leaves a stale pidfile, another unrelated process may later spawn with that reused PID, causing administrative scripts to kill innocent services.

</div>

<div class="callout summary">
<span class="label">Summary</span>

- Standalone daemons isolate themselves via a 4-step detachment ritual, pidfiles, and signal handlers.
- Modern cloud and Apple OS architectures supervise daemons in the foreground, delegating process tracking, logging, and sandboxing to `launchd` or `systemd`.
- Socket activation decouples service boot ordering, allowing daemons to start lazily on demand.
- Event-driven monitoring via `kqueue` (`EVFILT_PROC`) delivers deterministic child exit notifications on the supervisor's main event loop, bypassing the fragility of `SIGCHLD`.
- High-availability recovery relies on exponential backoff restart limits and watchdog heartbeats to resolve deadlocks.

</div>
