# 3. Processes

A program is a sequence of instructions stored in a file. A process is that
program in execution: the instructions, the data they operate on, the stack
they call through, and the kernel's record of all of it. One program can
run as many processes at once — every shell you open runs the same shell
program, and each is a separate process with a separate address space. This
chapter makes the distinction visible, then splits one process into two
with `fork`.

<div class="callout glance">
<span class="label">At a glance</span>

- A process owns an address space, a set of open files, and at least one
  thread; the kernel records these in a process control block.
- The address space has a fixed shape: text, data, BSS, heap, stack —
  observable from inside the program.
- `fork` copies the calling process; the parent and child differ only in
  the return value and PID.

</div>

## 3.1 What a process owns

The kernel keeps one record per process — the **process control block**,
PCB for short. It holds the process ID (PID), the parent's PID, the state
(running, ready, blocked), the saved register values when the process is
not running, the page table that defines its address space, the table of
open file descriptors, the current directory, and the signal state that
Chapter 10 will use. When the scheduler switches from one process to
another, it saves the CPU registers into the outgoing PCB and loads them
from the incoming one; the address space switches by changing one register
that points to the page table.

The address space is the process's private view of memory. Figure 3-1 is
its canonical shape, the picture to keep in mind whenever a later chapter
talks about the heap or the stack.

<figure>
<img src="diagrams/ch03_address_space.svg" alt="Process address space: text, data, BSS, heap growing up, stack growing down, kernel at the top"/>
</figure>

From low addresses upward:

- **text** holds the machine code. It is read-only, so two processes
  running the same program can share the same physical pages.
- **data** holds initialized globals; **BSS** holds uninitialized globals,
  which the kernel zero-fills without storing them in the file.
- **heap** holds memory obtained from `malloc` / `new` / `Box`. It grows
  upward as the allocator asks the kernel for more pages; Chapter 8 opens
  the allocator itself.
- **stack** holds call frames: return addresses, saved registers, local
  variables. It grows downward, one frame per call.
- **kernel** occupies the top of every process's space, mapped but
  unreachable from user mode, exactly as Chapter 2 described.

The exact addresses differ between Linux and macOS — macOS keeps the heap
in a separate region near `0x6000...`, and Linux places shared libraries
between heap and stack — but the order and the growth directions are the
same on both.

## 3.2 The address space, observed

The shape in Figure 3-1 is not a convention; it is measurable from inside
any process. The next listing prints the addresses of one object from each
region.

**Listing 3-1. Where the pieces of a process live (C++20).**

```cpp
{{#include ../code/ch03/layout.cpp}}
```

**Output 3-1. One run on the verification machine.**

```text
{{#include ../code/out/ch03_layout.out}}
```

Read the addresses against Figure 3-1. The function pointer is lowest, in
the text segment around `0x102c...`. The two globals sit adjacent in the
data segment — `0x...5000` and `0x...5004`, four bytes apart, exactly one
`int`. The heap pointer starts with `0x6000...`, far from the rest, in
macOS's heap region. The stack pointer starts with `0x7ff7...`, at the top
of the user range. High addresses at the top, low at the bottom, growth
directions as drawn.

The Rust version reports the same regions.

**Listing 3-2. The same observation in Rust (2024 edition).**

```rust
{{#include ../code/ch03/layout.rs}}
```

**Output 3-2.**

```text
{{#include ../code/out/ch03_layout_rs.out}}
```

Two details deserve comment. The Rust global is an `AtomicI32` because
Rust's `static` requires thread-safe types, and the uninitialized global is
a `static mut`, whose address the program takes through `addr_of!` rather
than a reference. Both restrictions exist so that shared mutable state is
always explicit — a theme Chapter 6 returns to.

<div class="callout experiment">
<span class="label">Experiment</span>

Add a second `new` call after the first and print both pointers. The second
address is higher than the first: the heap grows up. Then declare a local
variable inside a function called from `main` and print its address: it is
lower than `main`'s local, because the stack grows down.

</div>

## 3.3 fork: one program, two processes

`fork` is the only way a process creates another process. It copies the
calling process — same code, same data, same open files, same position in
the program — and returns twice: once in the parent, once in the new child.
The two processes are independent from that moment; writes in one do not
appear in the other.

Figure 3-2 shows the mechanics. The memory copy is lazy: both processes
initially point at the same physical pages, and the kernel makes a private
copy of a page only when one of them writes it. The technique is
copy-on-write, and it makes `fork` cheap even for large processes, because
the common case — fork followed immediately by `exec` — never copies
anything.

<figure>
<img src="diagrams/ch03_fork.svg" alt="fork copies the process; parent receives the child PID, child receives 0"/>
</figure>

The only reliable difference the program can observe is the return value:
the parent receives the child's PID, the child receives 0. Every `fork`
call site is therefore an `if` on that value, as in the next listing.

**Listing 3-3. fork, wait, and the exit status (C++20).**

```cpp
{{#include ../code/ch03/fork.cpp}}
```

**Output 3-3. The duplicated line is not a mistake; it is the point.**

```text
{{#include ../code/out/ch03_fork.out}}
```

The first line appears twice. The mechanism: `printf` writes into a buffer
in the process's memory and only flushes the buffer to the terminal when it
fills or when the program exits. At the moment of `fork`, the buffer still
holds `before fork: pid=...`. The child inherits that buffer, adds its own
line, and `_exit`s — the `fflush` before `_exit` writes both lines. The
parent later flushes its own copy, printing the first line again.

<div class="callout caution">
<span class="label">Watch out</span>

Two exits exist. `exit` runs cleanup registered with `atexit` and flushes
stdio buffers; `_exit` does neither. In a `fork`ed child, `exit` can flush
buffers the child inherited from the parent and print them twice — the
duplication in Output 3-3. Production code flushes before forking, or uses
`_exit` in children that must not run the parent's cleanup.

</div>

The parent waits with `waitpid`, which blocks until the child exits and
returns the exit status. Waiting is not politeness: an exited child whose
parent has not waited remains in the process table as a **zombie**, holding
its PID and exit status. Chapter 10 shows a zombie being reaped by a
signal handler.

**Listing 3-4. The same sequence through Rust's libc bindings.**

```rust
{{#include ../code/ch03/fork.rs}}
```

**Output 3-4.**

```text
{{#include ../code/out/ch03_fork_rs.out}}
```

Rust's standard library does not expose `fork`; the listing calls the
operating system directly through the `libc` crate, in `unsafe` blocks that
mark the calls whose correctness the compiler cannot check. The explicit
`flush` before `_exit` plays the same role as the C++ listing's `fflush`.

## 3.4 Life cycle: fork, exec, exit, wait

Four calls carry a process from birth to death. `fork` creates a copy.
`execve` replaces a process's entire address space with a new program —
same PID, same open files, new code and data. The shell's `ls` is a
fork followed by an exec in the child. `exit` ends the process and
produces a status. `wait` lets the parent collect that status and release
the PCB.

The separation of fork from exec is what makes shells, daemons, and
containers possible: between the two calls, the child can close
descriptors, open files, and set up its environment, all before the new
program runs. Chapter 15 builds a daemon entirely out of that interval.

Process states follow from the same four calls. A process is **running** on
a core, **ready** when it wants a core and none is free, or **blocked**
when it waits for an event such as a read from a pipe or a child's exit.
The scheduler moves processes between ready and running; the events
Chapter 13 waits on move them between blocked and ready.

<div class="callout summary">
<span class="label">Summary</span>

- A process is a program in execution: address space, file table, and at
  least one thread, recorded in the kernel's process control block.
- The address space's regions — text, data, BSS, heap, stack — are
  observable and follow the growth directions of Figure 3-1.
- `fork` returns twice: the child's PID in the parent, 0 in the child. The
  memory copy is lazy (copy-on-write).
- Buffered output is inherited across `fork`; flush before forking or
  accept the duplication.
- `execve` replaces the program; `exit` ends it; `wait` collects it. A
  child that exits without being waited on is a zombie.

</div>
