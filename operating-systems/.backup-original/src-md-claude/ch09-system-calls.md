# 9. System Calls and the Kernel Boundary

In Chapter 1, we introduced the system call as the way a user-mode program
requests a service from the kernel. Every file operation, every process
operation, and every network operation of a program is carried out
through system calls, so their cost affects the speed of almost every
program.

In this chapter, we follow one system call, `getppid`, from the program
into the kernel and back. We then measure the time of a system call and
compare it with the time of an ordinary function call. Finally, we show
how a buffer inside the program reduces the number of system calls needed
to write a given amount of data.

<div class="callout glance">
<span class="label">This chapter covers</span>

- the six steps of a system call
- why the kernel checks every argument
- the measured cost of a system call and of a function call
- why `getpid` is unsuitable for this measurement on some systems
- buffered output with `fwrite` and `BufWriter`
- what buffering does not guarantee

</div>

## 9.1 The path of a system call

Figure 9-1 shows one system call step by step. We use `getppid`, which
returns the parent's PID, because it takes no arguments and does very
little work in the kernel.

<figure>
<img src="figures/ch09_trap.svg" alt="Six numbered steps of a system call from user mode to the kernel and back"/>
</figure>

1. A program calls `getppid()`, a short function in the C library that is
   often called a *stub*.
2. This stub places a number that identifies the requested system call in
   a register. For calls that take arguments, it places those in registers
   as well. It then executes a trap instruction.
3. The CPU saves the program's registers, switches to kernel mode, and
   jumps to the kernel's entry point.
4. The kernel uses that number as an index into its *system call table*
   and calls the handler stored there. On Linux for x86-64, `getppid` has
   number 110.
5. This handler reads the parent's PID from the process table and places
   it in the register that carries return values.
6. The CPU restores the program's registers and switches back to user
   mode. Execution continues after the trap instruction, with a result in
   a register.

Three aspects of this sequence deserve attention. First, the kernel runs
on behalf of the calling process. Address space and page table stay as
they were, and only the privilege level changes. Second, the kernel checks
every value that it receives from a program, including the call number,
each pointer, and each length. A program can pass any value, and an
unchecked pointer would allow it to read or overwrite kernel memory.
Third, most of the time goes to steps 3 and 6, in which the CPU saves and
restores registers and changes its privilege level. After such a switch,
caches also hold little of the code and data that the kernel needs. A
handler itself is often short.

<div class="callout keyidea">
<span class="label">Key idea</span>

A system call runs kernel code inside the calling process. For a simple
call, most of the cost is the transition between user mode and kernel
mode. A program therefore runs faster when it does more work in each
system call and makes fewer calls.

</div>

## 9.2 Measuring the cost

Listing 9-1 measures this cost. It calls an ordinary function 5,000,000
times, then calls `getppid` 5,000,000 times, and prints the average time
of each.

**Listing 9-1. A system call compared with a function call (C++20).**

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

On this machine, a function call takes about 2 ns, and a system call takes
about 600 ns. The ratio is 277 in the C++ run and 242 in the Rust run. A
program that makes one system call for each small unit of work therefore
spends nearly all of its time on transitions.

We measure `getppid` and not the more familiar `getpid` for a reason. On
macOS, the C library stores the PID in memory after the first call to
`getpid` and returns the stored value on later calls. Older versions of
glibc on Linux did the same until version 2.25. On such a system, a loop
of `getpid` calls measures a memory read and no system call at all. The
library cannot store the result of `getppid` in this way, because the
parent of a process can change, so each call enters the kernel.

## 9.3 Buffering

Since each system call costs about 600 ns, a program should transfer as
much data as possible in each call. The usual technique is **buffering**.
The program appends its output to an array in its own memory, called a
*buffer*, and it calls `write` once when the buffer is full. The functions
`fwrite` in C and `BufWriter` in Rust work in this way. Figure 9-2
compares unbuffered and buffered output.

<figure>
<img src="figures/ch09_buffering.svg" alt="Unbuffered writes cross into the kernel per call; a 64 KiB user buffer crosses only when full"/>
</figure>

Listing 9-3 writes 200,000 records of 17 bytes each to `/dev/null`. It
first writes each record with a separate `write` call, and it then writes
the same records through `fwrite` with a buffer of 64 KiB.

**Listing 9-3. 200,000 small writes, unbuffered and buffered (C++20).**

```cpp
{{#include ../code/ch09/write_buffered.cpp}}
```

**Output 9-3.**

```text
{{#include ../code/out/ch09_write_buffered.out}}
```

**Listing 9-4. The same comparison in Rust, with write(2) and BufWriter.**

```rust
{{#include ../code/ch09/write_buffered.rs}}
```

**Output 9-4.**

```text
{{#include ../code/out/ch09_write_buffered_rs.out}}
```

The unbuffered loop makes 200,000 system calls and takes 284 ms, which is
about 1.4 µs per call. The buffered versions write the same 3,400,000
bytes. With a buffer of 65,536 bytes, they need only 3,400,000 / 65,536 ≈
52 calls to `write`, and they finish in 12.6 ms and 0.5 ms.

The two buffered times differ by a factor of about 25, although both
programs make the same number of system calls. This difference comes from
the two libraries. Each call to `fwrite` locks its stream and updates some
bookkeeping, whereas the Rust compiler inlines `BufWriter` code into the
loop. Once most system calls are gone, library overhead becomes
visible.

Buffering has two drawbacks. First, data in a buffer has not yet reached
the kernel. If the program crashes, that data is lost, and a call to
`fsync` does not help, because `fsync` affects only data that the kernel
has already received. Second, when a program mixes buffered and
unbuffered output on one descriptor, the output can appear out of order
unless the program flushes the buffer at the right moments. The duplicated
line in Chapter 3 was a consequence of unflushed buffered data.

<div class="callout caution">
<span class="label">Watch out</span>

Output that must survive a crash, such as a log record, needs two steps.
The program first flushes its buffer with `fflush` or `flush`, which
passes the data to the kernel. It then calls `fsync` or `sync_all`, which
asks the kernel to write the data to the storage device. We return to this
topic in Chapter 12.

</div>

<div class="callout summary">
<span class="label">Summary</span>

- In a system call, a stub places a call number in a register and
  executes a trap instruction. The kernel selects a handler from its
  system call table and checks every argument.
- On the verification machine, a system call takes about 600 ns, and a
  function call takes about 2 ns.
- Some library functions, such as `getpid` on macOS, return a stored value
  and make no system call.
- Buffering collects many small writes into a few large ones. In our
  test, it reduced 200,000 system calls to about 52.
- Buffered data is lost if the program crashes before it flushes.

In Chapter 10, we study signals, with which the kernel notifies a process
of an event.

</div>
