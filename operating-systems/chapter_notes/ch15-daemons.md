# Chapter 15: Daemon Lifecycle and Service Supervision

A daemon is a specialized process designed for long-running background execution, decoupled from any interactive terminal. While traditional daemons implement complex detachment rituals to ensure they are truly independent, modern systems have evolved toward a supervision-based model where service managers handle the lifecycle and environmental isolation of background services.

## 15.1 The Ritual of Detachment

To transition from a terminal-bound process to a fully independent daemon, a program must undergo a sequence of operations designed to sever all ties to the controlling session and its parent terminal. This "daemonization" process typically involves four critical stages:

1. **Session Decoupling (First Fork):** The process calls `fork`, allowing the parent to exit and returning control to the shell. This places the child in the background.
2. **Session Leadership (setsid):** The child invokes `setsid` to establish a new session. This creates a new session with the child as its leader and, crucially, detaches the process from its original controlling terminal.
3. **Terminal Prevention (Second Fork):** A second `fork` is performed to ensure the resulting grandchild is not a session leader. This prevents the process from inadvertently acquiring a new controlling terminal if it happens to open a terminal device.
4. **Environment Sanitization:** The process redirects its standard input, output, and error streams to `/dev/null` or a log file, changes its working directory to the root (`/`) to avoid pinning a filesystem, and sets its `umask` to ensure predictable file permissions. Finally, it records its Process ID (PID) in a **pidfile** to facilitate external management.

## 15.2 Signal-Driven Management and Supervision

The primary interface for interacting with a running daemon is through signals and its associated pidfile. Standardized signals allow for controlled lifecycle transitions: `SIGHUP` is conventionally used to request a configuration reload, while `SIGTERM` initiates a graceful shutdown.

In contemporary environments, the manual detachment ritual is often superseded by service managers such as `systemd` (Linux) or `launchd` (macOS). These supervisors adopt a "foreground daemon" model: the service is started directly as a child of the supervisor without manual `fork` or `setsid` calls. This allows the supervisor to maintain direct control over the process's PID, monitor its health, and manage its resource limits.

When using a supervisor, the daemon must still respect the signal-driven lifecycle. Upon receiving `SIGTERM`, the daemon must conclude its current tasks and exit within a predefined grace period; failure to do so results in the supervisor forcibly terminating the process via `SIGKILL`, which prevents any cleanup logic from executing.
