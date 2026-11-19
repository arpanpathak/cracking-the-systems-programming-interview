# 9. System Calls and the Kernel Boundary

A system call is the only door between a program and the kernel. Every
file operation, every process operation, every millisecond of I/O passes
through it. This chapter follows one call through the door, measures the
cost of crossing it, and shows the buffering discipline that makes the
cost affordable.

<div class="callout glance">
<span class="label">At a glance</span>

- A system call traps into the kernel with a number and arguments in
  registers; the kernel dispatches, executes, and returns.
- A trap costs hundreds of nanoseconds — hundreds of times a plain
  function call.
- Buffering in the library turns many small system calls into few large
  ones; that is the entire purpose of stdio and `BufWriter`.

</div>

## 9.1 The path of a system call

Chapter 2 drew the boundary; Figure 9-1 now walks one call across it,
step by step, with `getppid()` as the example.

<figure>
<img src="diagrams/ch09_trap.svg" alt="Six numbered steps of a system call from user mode to the kernel and back"/>
</figure>

The program calls `getppid()`, a library function. The library's stub
places the call's number and arguments in registers and executes the
trap instruction. The CPU saves the program's registers, switches to
kernel mode, and jumps to a fixed entry point. The kernel consults its
system call table — number 110 is `getppid` — and runs the handler. The
handler reads the parent PID from the process table and places it in
the return register. The CPU restores the program's registers, switches
back to user mode, and resumes the program after the trap.

Three properties of the path deserve emphasis. First, the kernel runs
*in the calling process's context*: same address space, same page
table, only the privilege level changes. Second, the kernel validates
everything the program passed — the call number, the pointers, the
lengths — because those values come from the untrusted side of the
boundary. Third, the expensive parts are the register save, the ring
switch, and the cold caches after the switch; the handler itself is
usually short.

<div class="callout keyidea">
<span class="label">Key idea</span>

A system call is a controlled context switch into kernel code inside
the same process. Its cost is the boundary crossing, not the work —
which is why batching work per crossing dominates I/O performance.

</div>

## 9.2 The cost, measured

The next listing measures the boundary directly: five million plain
function calls, five million system calls, one comparison.

**Listing 9-1. A system call against a plain function call (C++20).**

```cpp
{{#include ../code/ch09/syscall_cost.cpp}}
```

**Output 9-1. One run on the verification machine.**

```text
{{#include ../code/out/ch09_syscall_cost.out}}
```

**Listing 9-2. The same comparison in Rust.**

```rust
{{#include ../code/ch09/syscall_cost.rs}}
```

**Output 9-2.**

```text
{{#include ../code/out/ch09_syscall_cost_rs.out}}
```

Two numbers, one lesson. The function call costs about two nanoseconds.
The system call costs about six hundred — a factor of nearly three hundred. Any code that issues a system call per small unit of work is
spending three hundred times the necessary cost on the door.

A detail in the listings is itself worth an interview answer. The
experiment uses `getppid`, not `getpid`, because libc on macOS **caches
`getpid`** after the first call: a loop of `getpid()` would measure a
library lookup, not a trap. On Linux, glibc does the same. The honest
measurement requires a call the library cannot cache, and `getppid`
qualifies, because the parent can change. Knowing which calls are
library and which are syscalls is part of reading an I/O profile.

## 9.3 Buffering: fewer crossings, same bytes

If one crossing costs six hundred nanoseconds, the discipline is
obvious: accumulate work in the program, cross rarely, carry much. That
is the entire function of stdio's `fwrite` and Rust's `BufWriter`, and
Figure 9-2 draws the two paths.

<figure>
<img src="diagrams/ch09_buffering.svg" alt="Unbuffered writes cross into the kernel per call; a 64 KiB user buffer crosses only when full"/>
</figure>

**Listing 9-3. Two hundred thousand small writes, buffered and unbuffered (C++20).**

```cpp
{{#include ../code/ch09/write_buffered.cpp}}
```

**Output 9-3.**

```text
{{#include ../code/out/ch09_write_buffered.out}}
```

**Listing 9-4. The same comparison with raw write(2) and BufWriter (Rust).**

```rust
{{#include ../code/ch09/write_buffered.rs}}
```

**Output 9-4.**

```text
{{#include ../code/out/ch09_write_buffered_rs.out}}
```

The unbuffered loop pays one trap per 17 bytes: roughly 300 ms of
boundary crossings. The buffered loops pay one trap per full 64 KiB
buffer — a few dozen crossings — and finish in milliseconds. The
remaining difference between `fwrite` (13 ms) and `BufWriter` (0.6 ms)
is not the kernel; both crossed about as often. It is per-call overhead
in stdio's locking and bookkeeping versus a fully inlined Rust loop —
a library cost, visible only because the kernel cost has been removed.
This is the correct reading of an I/O profile: the kernel is one cost,
the library is another, and buffering removes the first.

Buffering has two prices, and both are the subject of classic bugs.
Data in the buffer has not reached the kernel: a crash loses it, and
`fsync` guarantees nothing about it. And output ordering between
buffered and unbuffered writes on the same descriptor is undefined
unless the program flushes deliberately — the fork duplication in
Chapter 3 was this price, paid in duplicated lines.

<div class="callout caution">
<span class="label">Watch out</span>

Buffered data is uncommitted data. Logs that must survive a crash need
`fflush`/`flush` plus `fsync`/`sync_all` on the descriptor, and even
then the disk's own write cache is a separate question Chapter 12
returns to. The buffer's convenience is bought with a delay in
visibility.

</div>

<div class="callout summary">
<span class="label">Summary</span>

- A system call traps into kernel code inside the same process; the
  kernel dispatches by number and validates every argument.
- The boundary costs hundreds of nanoseconds; a plain call costs a few.
- Library caching hides some calls entirely — `getpid` is a lookup, not
  a trap, on both Linux and macOS.
- Buffering converts many small crossings into few large ones; stdio
  and `BufWriter` exist for exactly this.
- Chapter 10 covers the asynchronous cousin of the trap: the signal,
  which enters the same boundary from the other direction.

</div>
