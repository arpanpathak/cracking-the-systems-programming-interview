# 10. Signals and Interrupts

A signal is an asynchronous notification delivered to a process. The
kernel sends one when a child exits, a timer expires, a terminal is
closed, or a program divides by zero — and a process can send one to
itself or to another process it is permitted to signal. This chapter
follows a signal through its three stages — generated, pending,
delivered — and shows the two patterns that matter in production: the
handler that reaps children, and the mask that defers delivery.

<div class="callout glance">
<span class="label">At a glance</span>

- A signal is generated, waits in a per-process pending set, and is
  delivered when the kernel next schedules the process.
- Delivery runs a handler between two of the process's instructions;
  handlers must be minimal.
- Blocking a signal defers delivery until the mask is cleared.
- `SIGCHLD` plus `waitpid` is the standard way to reap children.

</div>

## 10.1 Generated, pending, delivered

Figure 10-1 is the entire lifecycle.

<figure>
<img src="diagrams/ch10_signal_lifecycle.svg" alt="A signal is generated, held in a pending bitmask, and delivered by running the handler"/>
</figure>

Generation is an event: `raise` from the process itself, `kill` from
another process, or a hardware condition such as a protection fault.
Generation sets one bit in the receiving process's **pending set** — a
bitmask with one bit per signal number. That is all generation does;
the signal is not delivered yet.

Delivery is the kernel's next scheduling decision involving that
process. The kernel checks the pending set against the process's
**signal mask**; a blocked signal stays pending. For a deliverable
signal, the kernel consults the disposition: the default action
(terminate, ignore, stop), or a handler the program installed with
`sigaction`. A handler runs in user mode, on the process's own stack,
between two of its instructions — which is why the handler must do as
little as possible and touch only async-signal-safe state.

<div class="callout keyidea">
<span class="label">Key idea</span>

Pending is a bit, not a queue. Ten `SIGUSR1`s generated before
delivery collapse into one delivery — signals carry no payload beyond
their number, and count is not preserved.

</div>

## 10.2 Blocking and delivering, observed

The next listing demonstrates the stages directly: block `SIGUSR1`,
send it to yourself, observe that nothing ran; unblock, observe the
handler run; then send `SIGINT` and watch it deliver immediately.

**Listing 10-1. Block, send, observe, unblock (C++20).**

```cpp
{{#include ../code/ch10/signals.cpp}}
```

**Output 10-1. Delivery waits for the unblock, exactly as Figure 10-1 predicts.**

```text
{{#include ../code/out/ch10_signals.out}}
```

The handler writes a `volatile sig_atomic_t` flag, and that type choice
is the contract: between the handler and the rest of the program, the
only state that is safe to share is a sig_atomic integer. A handler
that calls `printf`, locks a mutex, or allocates memory can deadlock
against the very instruction it interrupted. The production pattern is
a flag like this one, checked by the main loop, plus one of the
kernel's own mechanisms — a pipe, or `signalfd` on Linux — for anything
more.

**Listing 10-2. The same stages through Rust's libc bindings.**

```rust
{{#include ../code/ch10/signals.rs}}
```

**Output 10-2.**

```text
{{#include ../code/out/ch10_signals_rs.out}}
```

Rust's handler writes an `AtomicBool` with relaxed ordering — a store
that is safe in a signal handler, unlike a mutex or an allocation. The
rest of the program polls the flag, which is the same minimal pattern
as the C++ listing, with the type system stating the guarantee instead
of a convention.

<div class="callout note">
<span class="label">Why masks exist</span>

A signal can arrive between any two instructions, including inside a
critical section. The mask lets a program defer delivery across a
fragile interval — say, while a data structure is half-updated — and
then unblock, at which point the pending signal delivers. Blocking is
the signal world's mutex.

</div>

## 10.3 SIGCHLD: reaping by signal

Chapter 3 left a loose end: a child that exits without being waited on
remains a zombie. Waiting in the main loop works when the parent has
nothing else to do; a server with live work needs the kernel to say
when a child has exited. The saying is `SIGCHLD`, delivered to the
parent when any child changes state.

**Listing 10-3. Reaping by hand, then reaping by handler (C++20).**

```cpp
{{#include ../code/ch10/sigchld.cpp}}
```

**Output 10-3. The first child waits for a manual waitpid; the second is reaped by the handler.**

```text
{{#include ../code/out/ch10_sigchld.out}}
```

The handler loops on `waitpid(-1, WNOHANG)` rather than waiting once,
because several children can exit before the handler runs, and because
pending is a bit: one `SIGCHLD` may stand for several exits. The
nonblocking reap drains all of them. `SA_RESTART` asks the kernel to
resume interrupted system calls instead of failing them with `EINTR` —
without it, a `read` interrupted by the handler's delivery returns an
error the program must retry, and servers that miss this fail under
exactly the load that generates many children.

The same pattern, in production form, appears in every daemon and
server: install `SIGCHLD` early, reap with a loop, restart syscalls.
Chapter 15's daemon installs the same discipline for its own shutdown
signals.

<div class="callout caution">
<span class="label">Watch out</span>

Three classic signal bugs, in one sentence each. Calling non-safe
functions in a handler — the interrupted code may hold the very lock
the function needs. Checking a flag without `volatile`/atomics — the
compiler may keep the flag in a register and never see the handler's
store. Using `waitpid` once per `SIGCHLD` — several children may have
exited behind one bit.

</div>

<div class="callout summary">
<span class="label">Summary</span>

- Generated, pending, delivered: one bit per signal, one delivery per
  bit, no counting.
- Handlers run between instructions; share only sig_atomic flags or
  atomic stores, and keep the work to a minimum.
- Masks defer delivery across fragile intervals; unblocking releases
  the pending signal.
- `SIGCHLD` + a `waitpid` loop is the standard reaping pattern;
  `SA_RESTART` keeps interrupted system calls transparent.
- Signals are the kernel's asynchronous edge; Chapter 11 turns to the
  data plane — pipes, shared memory, and sockets between processes.

</div>
