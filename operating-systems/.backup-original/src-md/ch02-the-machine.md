# 2. The Machine Underneath

Every operating system mechanism in this book is an answer to a property of
the machine: the instruction cycle, the memory hierarchy, the privilege
levels, and the interrupt path. This chapter fixes those four properties
with enough precision that later chapters can refer to them by name. It
contains no listings; it contains the model the listings run on.

<div class="callout glance">
<span class="label">At a glance</span>

- The CPU repeats fetch–decode–execute; the program counter says which
  instruction is next.
- Memory is a hierarchy, not a single store: registers, caches, DRAM.
- The CPU has at least two privilege levels; privileged instructions run
  only in the higher one.
- Interrupts and traps are the two ways the CPU leaves its current
  instruction stream.

</div>

## 2.1 The processor: fetch, decode, execute

A CPU core is a machine for repeating three steps. It fetches the
instruction at the address in the **program counter** (PC). It decodes the
instruction to learn which operation and which operands. It executes the
operation, updating registers or memory, and advances the PC to the next
instruction. Then it repeats.

Consider three instructions operating on a counter at address `0x1000`:

```asm
load  r1, [0x1000]    ; r1 = counter
add   r1, r1, 1       ; r1 = r1 + 1
store [0x1000], r1    ; counter = r1
```

One core executes these in order, and `counter` ends one larger. The
interesting property appears with two cores: if both execute this sequence
against the same address, each loads, adds, and stores independently, and
one of the two increments can be lost. The read–modify–write sequence is
not one operation; it is three. Chapter 4 turns this into a measured
experiment, and Chapter 6 shows the instructions that make it one
operation.

Two registers deserve names now. The **program counter** says which
instruction is next; saving and restoring it is the core of a context
switch, and Chapter 5 depends on that. The **stack pointer** (SP) marks the
top of the current call stack; every function call pushes a frame, and
every thread and every process has a stack of its own, which Chapters 3 and
4 draw in memory.

<figure>
<img src="diagrams/ch02_machine.svg" alt="Block diagram of a CPU core with registers, ALU, control unit, MMU, caches, DRAM, PCIe devices, timer, and interrupt controller"/>
</figure>

The diagram is the reference model for the whole book. Note the parts that
later chapters name:

- The **MMU** translates every address the core issues. Chapter 7 is about
  what the MMU consults to do that.
- The **interrupt controller** collects device signals and delivers them to
  the core as interrupts. Chapters 10 and 13 build on it.
- The **timer** raises an interrupt on a schedule, which is how the
  scheduler in Chapter 5 takes the CPU away from a running program.

## 2.2 The memory hierarchy

Memory is not one thing. The core has registers, small and immediate. Below
them sit cache levels of increasing size and latency, then DRAM, then
devices that behave like memory but are slower by orders of magnitude.
Figure 18-1 draws the full pyramid; this section establishes the principle.

Every access the core makes goes through the hierarchy. When the core reads
an address, the hardware checks the L1 cache first. A hit returns in a few
cycles. A miss checks L2, then L3, then DRAM, each step several times
slower than the one above it. The hardware does this automatically; the
program's only influence is the pattern of addresses it touches.

The pattern that matters is **locality**. A program that reuses recently
touched addresses (temporal locality) and touches addresses near the ones
it just used (spatial locality) keeps its working set in the fast levels.
A program that jumps randomly through a large region does not. Chapter 18
measures the difference with a sweep across buffer sizes; Chapter 7 adds
the page table and the TLB to the same picture, and Chapter 17 adds the
complication that on large machines some memory is closer to a core than
other memory is.

One more property matters for concurrency: **the cache line**. Caches move
memory in aligned blocks of 64 bytes, not in individual bytes. Two threads
incrementing two independent counters that happen to sit in the same line
contend for that line's ownership, and the line bounces between cores.
Chapter 17 measures the slowdown and the fix.

<div class="callout keyidea">
<span class="label">Key idea</span>

Performance follows the access pattern, not the instruction count. Two
loops can execute the same number of instructions and differ by a factor of
ten because one keeps its data in caches and the other does not.

</div>

## 2.3 Privilege levels

The CPU executes at one of several **privilege levels**, called rings on
x86 and exception levels on arm64. This book needs two: **user mode**, the
restricted level where programs run, and **kernel mode**, the level where
the operating system runs. The hardware enforces the difference at every
instruction.

Three classes of operations are privileged. Changing the page table base
register — which decides what memory a program can address at all — is
privileged. Writing device controller registers is privileged. Changing
the interrupt mask is privileged. A program that attempts any of these in
user mode faults, and the kernel decides what happens next, which is
usually termination of the program.

The arrangement has one consequence drawn in Figure 2-2: the kernel's code
and data are mapped into every process's address space at the same
addresses, but marked so that user mode cannot touch them. When a process
enters the kernel, the CPU raises the privilege level in place; no address
space switch is needed. This is why system calls are cheap enough to use
pervasively — and why the kernel must never trust a pointer a program
passes in.

<figure>
<img src="diagrams/ch02_privilege.svg" alt="User mode and kernel mode separated by a privilege boundary, with system call and return arrows crossing it"/>
</figure>

<div class="callout note">
<span class="label">Why two levels suffice</span>

Real processors have more rings and more exception levels. The operating
systems in this book collapse them to two: everything below the kernel
behaves like user mode from the kernel's point of view. The additional
levels host hypervisors and firmware, which Chapter 16 touches.

</div>

## 2.4 Traps and interrupts

A CPU executes its instruction stream until something pulls it elsewhere.
The two pulling mechanisms are **traps** and **interrupts**, and they are
the same in mechanism and different in cause.

A **trap** is caused by the running program: a system call instruction, a
divide by zero, a page fault. It is synchronous with the instruction
stream — it happens at a specific instruction, and after handling it the
kernel returns to that program. A **system call** is a trap a program
performs on purpose; Chapter 9 follows one through the boundary and
measures it.

An **interrupt** is caused by hardware: a timer expiry, a completed disk
transfer, an arriving packet. It is asynchronous — it lands between two
arbitrary instructions of whatever program happens to be running. After
handling it, the kernel returns to that program, or, because the interrupt
may have made some blocked work runnable, to a different one. Chapter 10
uses the timer interrupt as the scheduler's clock, and Chapter 13 uses
device interrupts as the reason a blocked `poll` returns.

Both paths start the same way: the hardware saves a minimal state, switches
to kernel mode, and jumps to a fixed entry point. The kernel then saves the
rest of the registers, handles the cause, and restores. The path is the
**context switch** in miniature; Chapter 5 shows the full version between
two programs.

## 2.5 From power-on to your program

One path ties the whole machine together, and interviewers ask about it
because it touches every layer. When the machine powers on, the CPU starts
executing firmware. The firmware initializes memory and devices, finds a
bootable disk, and loads the **bootloader**. The bootloader loads the
kernel into memory and jumps to it. The kernel initializes its data
structures — the page tables, the process table, the device drivers — and
starts the first process, `init` on Linux and `launchd` on macOS. That
first process starts the services the system needs, one of which starts
your shell. When you run a program, the shell calls `fork` to create a
process and `execve` to replace it with your program; Chapter 3 follows
exactly those two calls.

Notice what the kernel must have before any of this works: a working page
table, a way to allocate memory, and a scheduler that can choose a process.
Those are Chapters 7, 8, and 5, in that dependency order.

<div class="callout summary">
<span class="label">Summary</span>

- Fetch–decode–execute, driven by the program counter, is the loop every
  mechanism in this book eventually serves or interrupts.
- Memory is a hierarchy of caches above DRAM; locality decides which level
  answers most accesses; 64-byte lines decide contention.
- User mode and kernel mode are enforced by hardware at every privileged
  instruction; the kernel is mapped into every process but walled off.
- Traps are synchronous and caused by the program; interrupts are
  asynchronous and caused by hardware; both enter the kernel at a fixed
  entry point.
- The boot path — firmware, bootloader, kernel, first process — is the
  same sequence on every machine this book considers.

</div>
