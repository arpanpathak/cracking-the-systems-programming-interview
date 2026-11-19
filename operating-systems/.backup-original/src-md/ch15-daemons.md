# 15. Daemons and Service Lifecycle

A daemon is a process with no terminal, no parent to speak of, and one
job that runs until the machine stops. Everything distinctive about it
comes from detaching cleanly: the double fork, the new session, the
redirected standard streams, the pidfile, and the signal discipline
that lets a supervisor stop it gracefully. This chapter builds one in
both languages, runs it under a harness, and shows it shut down on
command.

<div class="callout glance">
<span class="label">At a glance</span>

- Detachment is mechanical: fork, setsid, fork again, redirect stdio,
  record the PID.
- The pidfile is the supervisor's handle; removing it on exit is the
  shutdown handshake.
- `SIGHUP` means reload configuration; `SIGTERM` means stop cleanly.
- systemd and launchd supervise daemons that stay in the foreground;
  the daemonize dance belongs to programs they do not manage.

</div>

## 15.1 Why detachment is mechanical

A process started from a shell belongs to the shell's session, reads
and writes the terminal, and dies when the terminal closes — via
`SIGHUP`, the hangup signal. A daemon must survive all three. Each
step of the traditional dance undoes one attachment, and Figure 15-1
lays them out.

<figure>
<img src="diagrams/ch15_daemonize.svg" alt="The four daemonization steps: fork, setsid, fork again, redirect stdio and write the pidfile"/>
</figure>

**First fork.** The daemon runs in the child; the parent exits, so the
shell's job — and its terminal's notion of a foreground process — is
finished.

**setsid.** The child becomes leader of a new session with no
controlling terminal. A session is the kernel's grouping of processes
around a terminal; leaving it is what makes the daemon immune to the
terminal's hangup.

**Second fork.** The session leader exits. This step is historical
insurance: on systems where a session leader can reacquire a terminal
by opening one, the grandchild — not a leader — cannot. Modern
systems no longer need it, but the dance is retained because
supervisors and scripts expect it.

**Redirect, record, handle.** Standard input from `/dev/null`, output
to a log, working directory to `/` (so the daemon never pins a
filesystem), a restrictive umask, the PID written to a pidfile, and
signal handlers installed.

The result is a process that the shell no longer owns, and that
nothing on the machine can find except through its pidfile and its
log. That indirection is the point: the pidfile is the interface.

## 15.2 The daemon, built and run

**Listing 15-1. A complete daemon lifecycle (C++20).**

```cpp
{{#include ../code/ch15/daemon.cpp}}
```

**Listing 15-2. The same lifecycle in Rust.**

```rust
{{#include ../code/ch15/daemon.rs}}
```

The harness starts each binary, waits for its pidfile, verifies the
process is alive, sends `SIGHUP` and then `SIGTERM`, and confirms the
pidfile disappears.

**Output 15-1. Start, reload, stop — the C++ daemon's log as the harness saw it.**

```text
{{#include ../code/out/ch15_daemon.out}}
```

**Output 15-2. The Rust daemon's run.**

```text
{{#include ../code/out/ch15_daemon_rs.out}}
```

Read the logs as the lifecycle in miniature. `started` after the
pidfile write. `tick 1`, then `reload requested` — the `SIGHUP` flag,
checked in the main loop rather than handled inline, which is
Chapter 10's minimal-handler discipline. `stopping after N ticks` —
the `SIGTERM` flag ends the loop, the pidfile is removed, and the
process exits with its affairs in order. The tick counts differ
between the two runs; everything else is deterministic.

<div class="callout keyidea">
<span class="label">Key idea</span>

A daemon's interface is three artifacts: a pidfile that names it, a
log that records it, and signal handlers that steer it. The double
fork is scenery; the interface is the contract.

</div>

## 15.3 Supervisors: systemd and launchd

Modern systems supervise daemons instead of merely starting them. The
supervisor — `systemd` on Linux, `launchd` on macOS — starts services
at boot, restarts them when they fail, collects their logs, and
enforces their resource limits. Two consequences follow for how
daemons are written.

First, a supervised daemon stays in the **foreground**: no double
fork, no `setsid`, no pidfile. The supervisor already detached it, and
a daemon that daemonizes again defeats the supervisor's accounting —
it cannot watch a process it did not start, and a pidfile is a
guess at what the supervisor knows exactly. The traditional dance in
Section 15.1 remains correct for programs that must run standalone;
the modern rule is to know which world the program lives in and
choose one, not both.

Second, the signals keep their meanings but gain a sender. `SIGHUP`
still means reload; systemd sends it on `systemctl reload`. `SIGTERM`
still means stop; the supervisor sends it, waits a grace period, and
escalates to `SIGKILL` — which no handler can catch — if the process
lingers. A daemon therefore has one job on `SIGTERM`: become
finished before the grace period ends. The loop-and-flag pattern in
the listings is exactly that job, and the graceful shutdown it
performs — finish the current tick, flush, remove the pidfile — is
the difference between a clean restart and a supervisor-forced kill.

<div class="callout caution">
<span class="label">Watch out</span>

Three daemon failures, in one sentence each. Double-daemonizing under
a supervisor — the supervisor watches the wrong process and restarts
nothing. Removing the pidfile in a crash path but not on `SIGKILL` —
a stale pidfile then names a PID that has been reused by an unrelated
process. And handling `SIGTERM` with cleanup that blocks on a network
peer — the grace period expires, `SIGKILL` lands, and the cleanup
never runs.

</div>

<div class="callout summary">
<span class="label">Summary</span>

- Detachment is four mechanical steps; the pidfile, log, and signal
  handlers are the resulting interface.
- Handlers set flags; the main loop checks them — the minimal
  pattern from Chapter 10, at daemon scale.
- Supervised daemons stay in the foreground and let systemd or
  launchd own detachment, restart, and logs.
- `SIGTERM` means "finish before the grace period"; clean shutdown is
  a deadline, not a courtesy.
- Chapter 16 scales the process model outward: many daemons, many
  machines, and the virtualization layers between them.

</div>
