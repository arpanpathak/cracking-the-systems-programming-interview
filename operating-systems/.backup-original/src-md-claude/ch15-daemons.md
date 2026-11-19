# 15. Daemons and Service Lifecycle

A **daemon** is a process that runs in the background and is not attached
to a terminal. Web servers, database servers, and the logging service of a
system are daemons. A daemon usually starts when the machine boots and
runs until the machine shuts down.

In this chapter, we examine the steps by which a process detaches itself
from the terminal that started it. We then write a daemon in C++ and in
Rust, start it, ask it to reload its configuration, and stop it. Finally,
we describe how the service managers systemd and launchd have changed the
way daemons are written.

<div class="callout glance">
<span class="label">This chapter covers</span>

- sessions and the controlling terminal
- the four steps of detachment: `fork`, `setsid`, a second `fork`, and
  redirection
- the pidfile
- `SIGHUP` for reloading and `SIGTERM` for stopping
- a complete daemon in C++ and Rust
- daemons under systemd and launchd

</div>

## 15.1 Detaching from the terminal

A process that we start from a shell is connected to that shell in three
ways. It belongs to the **session** of the shell, which is a group of
processes that share one *controlling terminal*. Its standard input,
output, and error refer to that terminal. And when the terminal closes,
the kernel sends the signal `SIGHUP` (hangup) to the processes of the
session, which terminates them by default. A daemon must remove all three
connections. Figure 15-1 shows the steps that it takes.

<figure>
<img src="figures/ch15_daemonize.svg" alt="The four daemonization steps: fork, setsid, fork again, redirect stdio and write the pidfile"/>
</figure>

1. **First fork.** The program calls `fork`, and the parent exits. The
   shell sees that its command has finished and prints a new prompt. The
   child continues in the background.
2. **setsid.** The child calls `setsid`, which creates a new session with
   the child as its leader. The new session has no controlling terminal,
   so the child no longer receives `SIGHUP` when the old terminal closes.
3. **Second fork.** The child calls `fork` again and exits. On some Unix
   systems, a session leader acquires a controlling terminal when it opens
   a terminal device. The grandchild is not a session leader, so it cannot
   acquire one by accident.
4. **Redirection and bookkeeping.** The grandchild, which is now the
   daemon, connects its standard input to `/dev/null` and its standard
   output and error to a log file. It changes its working directory to
   `/`, so that it does not keep some other file system in use, and it
   sets its umask. It writes its PID to a file, called the **pidfile**,
   and installs its signal handlers.

After these steps, the daemon has no connection to the shell that started
it. Its parent has exited, so the kernel has assigned it a new parent,
which is the first process of the system. Other programs find the daemon
through its pidfile and learn what it does from its log.

## 15.2 A complete daemon

Listings 15-1 and 15-2 implement these steps. After detaching, the daemon
enters a loop in which it writes a line to its log once per interval,
which we call a *tick*. Its handlers for `SIGHUP` and `SIGTERM` only set
flags, as recommended in Chapter 10, and the loop tests those flags.

**Listing 15-1. A daemon from start to shutdown (C++20).**

```cpp
{{#include ../code/ch15/daemon.cpp}}
```

**Listing 15-2. The same daemon in Rust.**

```rust
{{#include ../code/ch15/daemon.rs}}
```

Our script starts each daemon and waits until a pidfile exists. It checks
that a process with that PID is alive, sends `SIGHUP` and then `SIGTERM`,
and finally checks that the pidfile has been removed. Each output below
shows messages from our script, followed by the daemon's log.

**Output 15-1. The C++ daemon.**

```text
{{#include ../code/out/ch15_daemon.out}}
```

**Output 15-2. The Rust daemon.**

```text
{{#include ../code/out/ch15_daemon_rs.out}}
```

Each log records every stage. A daemon writes `started` after it has
created its pidfile. During tick 1, `SIGHUP` arrives, and when the loop
next tests its flag, the daemon writes `reload requested`. A real daemon
would read its configuration file again at this point. When `SIGTERM`
arrives, the loop ends, and the daemon writes `stopping`, removes its
pidfile, and exits. Our C++ daemon completed three ticks and our Rust
daemon two, because signals arrived at slightly different times in these
two runs.

<div class="callout keyidea">
<span class="label">Key idea</span>

Other programs interact with a daemon through three things: a pidfile that
contains its PID, a log that records its activity, and signals that
request a reload or a shutdown.

</div>

## 15.3 Supervisors: systemd and launchd

On current systems, a **supervisor** starts and monitors daemons. Linux
distributions use `systemd` for this purpose, and macOS uses `launchd`. A
supervisor starts services when the machine boots, restarts a service that
has crashed, collects its output in a log, and applies limits to the
resources it may use. Supervision changes the way a daemon is written in
two respects.

First, a supervised daemon runs in the *foreground*. It does not call
`fork` or `setsid`, and it does not write a pidfile. The supervisor
starts the daemon as its own child, with no terminal attached, and it
knows the PID because it created the process. If such a daemon detaches
itself anyway, the process that the supervisor started exits, and the
supervisor concludes that the service has stopped. The steps of Section
15.1 are still appropriate for a program that runs without a supervisor.
A program should use one of the two approaches, but not both.

Second, the signals keep their meaning, and the supervisor sends them.
`systemctl reload` sends `SIGHUP` to a service whose unit file configures
that signal as its reload action. To stop a service, the supervisor sends
`SIGTERM` and waits for a grace period, 90 seconds by default in systemd.
If the process is still running after that time, the supervisor sends
`SIGKILL`, which cannot be caught and ends the process at once. A daemon
must therefore finish its current work and exit within the grace period
after it receives `SIGTERM`. The flag and loop of our listings do exactly
that.

<div class="callout caution">
<span class="label">Watch out</span>

Three mistakes are common in daemons.

- Detaching under a supervisor. The supervisor then monitors a process
  that has already exited.
- Trusting a stale pidfile. A daemon that is ended by `SIGKILL` cannot
  remove its pidfile, and the kernel may later give the recorded PID to an
  unrelated process.
- Blocking during shutdown. If the `SIGTERM` cleanup waits for a network
  peer that never answers, the grace period expires, and `SIGKILL` ends
  the daemon before the cleanup has finished.

</div>

<div class="callout summary">
<span class="label">Summary</span>

- A daemon detaches with `fork`, `setsid`, a second `fork`, and the
  redirection of its standard streams. It records its PID in a pidfile.
- Signal handlers set flags, and the main loop of the daemon acts on
  them. `SIGHUP` requests a reload, and `SIGTERM` requests a shutdown.
- A daemon that runs under systemd or launchd stays in the foreground and
  does not detach.
- After `SIGTERM`, a daemon must exit within the grace period, or the
  supervisor ends it with `SIGKILL`.

In Chapter 16, we study virtual machines and containers, which run groups
of processes in isolation from the rest of a machine.

</div>
