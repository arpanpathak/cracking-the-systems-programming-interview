# 10. Signals and Interrupts

A **signal** is a notification that the kernel delivers to a process. The
kernel sends a signal when a child process exits, when a timer expires,
when a terminal is closed, or when a program performs an invalid operation
such as a division by zero. A process can also send a signal to itself or
to another process, if it has permission to do so. A signal is to a
process what an interrupt is to a CPU. It can arrive at any time, and it
causes a handler to run before the interrupted code continues.

In this chapter, we follow a signal through three stages: it is generated,
it remains pending, and it is delivered. We then block a signal and
observe that its delivery is postponed. Finally, we use the signal
`SIGCHLD` to collect the exit status of child processes.

<div class="callout glance">
<span class="label">This chapter covers</span>

- the three stages of a signal
- the pending set and the signal mask
- what a signal handler may safely do
- blocking and unblocking a signal with `sigprocmask`
- reaping children with `SIGCHLD` and `waitpid`
- the `SA_RESTART` flag

</div>

## 10.1 Generated, pending, delivered

Figure 10-1 shows the three stages of a signal.

<figure>
<img src="figures/ch10_signal_lifecycle.svg" alt="A signal is generated, held in a pending bitmask, and delivered by running the handler"/>
</figure>

A signal is **generated** when some event produces it. The process may
call `raise`, another process may call `kill`, or the hardware may report
a condition such as a protection fault. When a signal is generated, the
kernel sets one bit in the **pending set** of the receiving process. The
pending set is a bitmask with one bit for each signal number. At this
point, the process has not yet been affected.

A signal is **delivered** the next time the kernel is about to return its
target process to user mode. Before doing so, the kernel compares the
pending set with that process's **signal mask**, which lists all signals
that the process has *blocked*. A blocked signal stays pending. For a
signal that is not blocked, the kernel looks up which action the process
has chosen for it. This choice is called a *disposition*. It is either a
default action, which terminates the process, stops it, or ignores the
signal, depending on which signal it is, or it is a **handler**, a
function that the program installed with `sigaction`.

A handler runs in user mode, on the stack of the thread that receives the
signal. It runs between two instructions of the program, wherever the
program happened to be. The interrupted code may be in the middle of
updating a data structure or may hold a lock. A handler must therefore do
very little, and it may call only functions that POSIX lists as
*async-signal-safe*.

<div class="callout keyidea">
<span class="label">Key idea</span>

The pending set has one bit per signal and does not count. If `SIGUSR1` is
generated ten times before it is delivered, the handler runs once. A
standard signal carries no data other than its number.

</div>

## 10.2 Blocking and delivering a signal

Listing 10-1 shows the three stages in a running program. The program
blocks `SIGUSR1`, sends that signal to itself, and prints a flag that the
handler would have set. It then unblocks the signal and prints the flag
again. Finally, it sends `SIGINT`, which is not blocked.

**Listing 10-1. Blocking, sending, and unblocking a signal (C++20).**

```cpp
{{#include ../code/ch10/signals.cpp}}
```

**Output 10-1. The handler runs only after the signal is unblocked.**

```text
{{#include ../code/out/ch10_signals.out}}
```

After the first `raise`, our flag is still 0. `SIGUSR1` is pending, but
its delivery is blocked. Once the program unblocks `SIGUSR1`, the flag is
1, which shows that its handler has run. `SIGINT`, sent last, is delivered
at once.

The handler in Listing 10-1 does nothing except set a flag of type
`volatile sig_atomic_t`. This type is the only kind of variable that the C
and C++ standards allow a handler to share with the rest of the program.
A handler that calls `printf`, locks a mutex, or allocates memory can
deadlock, because the interrupted code may already hold the lock that the
function needs. A common design is therefore to set a flag in the handler
and to test the flag in the main loop of the program. A program that
needs more information can have the handler write one byte to a pipe, or
it can use `signalfd` on Linux, which delivers signals through a file
descriptor.

**Listing 10-2. The same steps in Rust, using the libc crate.**

```rust
{{#include ../code/ch10/signals.rs}}
```

**Output 10-2.**

```text
{{#include ../code/out/ch10_signals_rs.out}}
```

The Rust handler stores `true` in an `AtomicBool` with relaxed ordering.
An atomic store is safe inside a signal handler, whereas locking a mutex
or allocating memory is not.

<div class="callout note">
<span class="label">Why a process blocks signals</span>

A signal can arrive between any two instructions, including a moment at
which a data structure is only partly updated. A program can block the
signal before such an update and unblock it afterward. A signal that is
generated in between stays pending and is delivered after the unblock.

</div>

## 10.3 Reaping children with SIGCHLD

In Chapter 3, we saw that a child that has exited remains a zombie until
its parent calls `waitpid`. A parent with nothing else to do can call
`waitpid` and block. A server, however, has other work, and it should not
block while its children run. For this case, the kernel sends the signal
`SIGCHLD` to a parent whenever one of its children exits or stops. The
parent can then call `waitpid` in the handler of that signal.

Listing 10-3 creates two children. It collects the first with an ordinary
`waitpid` call and the second in a `SIGCHLD` handler.

**Listing 10-3. Reaping one child directly and one child in a handler (C++20).**

```cpp
{{#include ../code/ch10/sigchld.cpp}}
```

**Output 10-3. The second child has already been reaped when the main program calls waitpid.**

```text
{{#include ../code/out/ch10_sigchld.out}}
```

As the last line shows, `waitpid` returned -1 in the main program. No
child was left to wait for, because our handler had already reaped child
number two.

The handler calls `waitpid(-1, &status, WNOHANG)` in a loop until no
exited child remains. A single call would not be enough. Since the pending
set does not count, several children can exit while one `SIGCHLD` is
pending, and the handler then runs only once. The option `WNOHANG` makes
`waitpid` return at once when no child has exited, so the loop ends
without blocking.

Listing 10-3 also sets the flag `SA_RESTART` when it installs the handler.
A signal can arrive while the process is blocked in a system call such as
`read`. Without `SA_RESTART`, that call fails with the error `EINTR` after
the handler returns, and the program must repeat the call. With
`SA_RESTART`, the kernel restarts the call automatically. A server that
neither sets this flag nor handles `EINTR` reports false errors whenever a
child exits during a `read`.

<div class="callout caution">
<span class="label">Watch out</span>

Three mistakes with signals are common.

- Calling a function in a handler that is not async-signal-safe. The
  interrupted code may hold a lock that the function needs.
- Sharing a flag with a handler without `volatile` or an atomic type. The
  compiler may keep the flag in a register, and the main loop then never
  sees the value that the handler stored.
- Calling `waitpid` only once for each `SIGCHLD`. Several children may
  have exited.

</div>

<div class="callout summary">
<span class="label">Summary</span>

- A signal is generated, stays pending, and is delivered. The pending set
  holds one bit per signal and does not count occurrences.
- A handler runs between two instructions of the program. It should set a
  `sig_atomic_t` flag or an atomic variable and return.
- A blocked signal stays pending until the process unblocks it.
- A `SIGCHLD` handler reaps children with `waitpid` and `WNOHANG` in a
  loop. `SA_RESTART` restarts system calls that the signal interrupted.

Signals carry almost no data. In Chapter 11, we study the mechanisms with
which processes exchange data: pipes, shared memory, and socket pairs.

</div>
