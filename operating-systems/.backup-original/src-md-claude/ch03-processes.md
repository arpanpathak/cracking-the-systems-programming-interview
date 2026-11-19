# 3. Process Abstraction and Lifecycle

A program is a static sequence of instructions; it becomes a process only
when the operating system instantiates it into an active execution
environment. A process is defined by its execution state, its resource
ownership, and its isolated address space.

<div class="callout glance">
<span class="label">This chapter covers</span>

- the process control block and the topology of an address space
- empirical confirmation of that topology from inside a process
- `fork`, its two return values, and copy-on-write
- inheritance of user-mode buffers across `fork`
- `execve`, `exit`, `waitpid`, and zombie processes
- the states running, ready, and blocked

</div>

## 3.1 The Process Control Block and Address Space Topology

To manage multiple concurrent executions, the kernel maintains a Process
Control Block (PCB) for every active process. The PCB serves as the
primary vehicle for context switching, storing the process's unique
identifier (PID), its lineage, its current execution state (running,
ready, or blocked), and the precise architectural state, including
registers and the program counter, required to resume execution. Beyond
execution state, the PCB tracks the process's environmental resources,
including its page tables for memory isolation, its file descriptor table,
and its signal configuration.

A context switch is consequently an exchange between two PCBs. The kernel
deposits the CPU registers in the PCB of the outgoing process, loads them
from that of the incoming one, and writes a different page table address
into a single register, an operation that replaces the entire address
space at once.

The process's memory is organized into a structured address space, which
provides a consistent view of memory regardless of the underlying physical
allocation. This topology typically includes:

- **Text Segment:** The read-only machine code of the program, which can
  be shared across multiple processes to conserve physical memory.
- **Data and BSS Segments:** Regions for initialized and uninitialized
  global variables, respectively.
- **Heap:** A dynamically expanding region for runtime memory allocation,
  growing toward higher addresses.
- **Stack:** A region that manages function activation records, growing
  toward lower addresses.
- **Kernel Space:** A protected region at the apex of the address space,
  mapped into every process but inaccessible in user mode, facilitating
  efficient system calls.

<figure>
<img src="figures/ch03_address_space.svg" alt="Process address space: text, data, BSS, heap growing up, stack growing down, kernel at the top"/>
</figure>

Figure 3-1 renders this topology. The executable file stores no bytes for
BSS, since the kernel zero-fills that region at program start. Absolute
addresses are platform-specific: macOS confines the heap to a separate
region near `0x6000...`, whereas Linux interposes shared libraries between
heap and stack. The relative order of the regions and their directions of
growth are nevertheless invariant across both.

## 3.2 Empirical Verification of the Address Space

Because the topology is common to every process, it can be verified from
within any one of them. Listing 3-1 defines a function, an initialized
global, an uninitialized global, a heap object, and a local variable, and
emits the address of each.

**Listing 3-1. Printing one address from each region (C++20).**

```cpp
{{#include ../code/ch03/layout.cpp}}
```

**Output 3-1. One run on the verification machine.**

```text
{{#include ../code/out/ch03_layout.out}}
```

The five addresses emerge in the order that Figure 3-1 prescribes. The
function occupies the lowest, `10EC385E0`, in the text segment. The two
globals follow at `10EC3A000` and `10EC3A004`, separated by 4 bytes, the
size of one `int`, which confirms the adjacency of data and BSS. The heap
object resides far above them at `600001EB0040`, within the macOS heap
region, and the local variable holds the highest address, `7FF7B12C67AC`,
near the upper limit of the user range.

**Listing 3-2. The same program in Rust (2024 edition).**

```rust
{{#include ../code/ch03/layout.rs}}
```

**Output 3-2.**

```text
{{#include ../code/out/ch03_layout_rs.out}}
```

The Rust variant reports the same five regions under stricter
declarations. A `static` must possess a type that is safe to share between
threads, which necessitates an `AtomicI32` for the initialized global. The
uninitialized global is a `static mut`, whose address is obtained through
`addr_of!`, because references to a `static mut` are prohibited. Both
constraints enforce a single invariant: shared mutable state must be
explicit in the source. Chapter 6 returns to that invariant.

<div class="callout experiment">
<span class="label">Experiment</span>

Add a second `new` after the first one and print both pointers. The second
address is higher, because the heap grows upward. Then declare a local
variable in a function that `main` calls and print its address. It is
lower than the address of the local in `main`, because the stack grows
downward.

</div>

## 3.3 Process Creation and the Mechanics of `fork`

On Unix-like systems, process creation is facilitated through the `fork`
system call, which implements a "copy-on-write" (COW) paradigm. Rather
than performing an immediate, computationally expensive duplication of the
parent's entire address space, the kernel initially permits the parent and
child to share the same physical pages, marking them as read-only. A
private copy is only instantiated when one of the processes attempts a
write operation. This mechanism ensures that `fork` remains highly
efficient, particularly when the child intends to immediately replace its
image using `execve`.

Since parent and child resume at the same instruction with identical
state, the return value of `fork` is the sole means of distinguishing
them. A single invocation returns twice: the parent receives the PID of
the child, and the child receives 0. Every call site must therefore branch
on that value. Figure 3-2 depicts both processes after the call.

<figure>
<img src="figures/ch03_fork.svg" alt="fork copies the process; parent receives the child PID, child receives 0"/>
</figure>

**Listing 3-3. fork, waitpid, and the exit status (C++20).**

```cpp
{{#include ../code/ch03/fork.cpp}}
```

**Output 3-3. The first line is printed twice.**

```text
{{#include ../code/out/ch03_fork.out}}
```

A critical nuance of `fork` involves the inheritance of process state,
specifically the buffers within standard I/O libraries. Because `fork`
duplicates the process's memory, including any unwritten data in user-mode
buffers, a child process may inadvertently re-output data that was
buffered by the parent prior to the fork. This necessitates explicit
synchronization, such as calling `fflush` before a `fork` operation, to
maintain output integrity.

Output 3-3 exhibits precisely this effect. With standard output directed
to a file, as it is under the capturing script, the C library defers
writing until its buffer fills or the program exits. At the instant of the
`fork`, the buffer still holds `before fork: pid=46627`, and the child
inherits a copy of it. The child appends its own line and invokes
`fflush`, which emits both. The parent subsequently exits and emits its
own copy, which likewise begins with `before fork`.

<div class="callout caution">
<span class="label">Watch out</span>

A process can end with `exit` or with `_exit`. `exit` runs the functions
registered with `atexit` and writes out stdio buffers, whereas `_exit`
does neither. If a child created by `fork` calls `exit`, it writes any
buffered output that it inherited from its parent, and that output then
appears twice. To avoid the duplicate, call `fflush` before `fork`, or
end the child with `_exit`.

</div>

**Listing 3-4. The same sequence in Rust, using the libc crate.**

```rust
{{#include ../code/ch03/fork.rs}}
```

**Output 3-4.**

```text
{{#include ../code/out/ch03_fork_rs.out}}
```

The Rust standard library exposes no `fork`, so Listing 3-4 reaches the
operating system through the `libc` crate. Each call is confined to an
`unsafe` block, since its correctness lies beyond the compiler's analysis,
and a `SAFETY` comment above each block records the justification. Here
`before fork` appears only once, because `println!` writes through a
line-buffered handle and the line had left its buffer before the `fork`.
The child nevertheless invokes `flush` before `_exit`, for the reason that
governs the `fflush` in the C++ listing.

## 3.4 Lifecycle Management and Termination

The lifecycle of a process is governed by a sequence of fundamental
transitions: `fork` for creation, `execve` for program replacement, `exit`
for termination, and `waitpid` for status collection. `execve` is
particularly vital as it allows a process to discard its current address
space and load a new program image while retaining its existing process
identity (PID) and inherited file descriptors.

The separation of creation from program loading is deliberate. Between the
return of `fork` and the invocation of `execve`, the child still executes
the parent's code and can close descriptors, open files, or alter its
working directory, so that the new program begins in an environment
already prepared for it. Shells implement redirection within this
interval, and the daemon of Chapter 15 is constructed from it.

Proper lifecycle management is required to prevent the accumulation of
"zombie" processes. When a process terminates via `exit`, the kernel
preserves its PCB and exit status until the parent process acknowledges
the termination through a `waitpid` call. If a parent fails to reap its
children, these defunct processes remain in the system as zombies,
consuming entries in the process table and potentially exhausting system
resources. In Output 3-3, `waitpid` returns the status 7 that the child
passed to `_exit`. Chapter 10 delegates this reaping to a signal handler.

The operational state of a process is categorized into three primary
modes: **Running** (actively executing on a core), **Ready** (eligible for
execution but awaiting a CPU), and **Blocked** (waiting for an external
event or resource). The scheduler's role is to manage transitions between
these states, ensuring efficient CPU utilization and responsiveness.

<div class="callout summary">
<span class="label">Summary</span>

- The PCB holds the identity, execution state, saved registers, and
  resource tables of a process, and a context switch exchanges two PCBs.
- An address space comprises text, data, BSS, heap, and stack, with the
  heap growing upward and the stack downward.
- `fork` returns the child's PID to the parent and 0 to the child. Pages
  are shared read-only until a write forces a private copy.
- User-mode buffers are duplicated by `fork`, which necessitates `fflush`
  beforehand.
- `execve` replaces the program image, `exit` terminates the process, and
  `waitpid` collects its status. An unreaped child persists as a zombie.

A process as characterized here executes a single instruction stream.
Chapter 4 introduces several such streams within one address space.

</div>
