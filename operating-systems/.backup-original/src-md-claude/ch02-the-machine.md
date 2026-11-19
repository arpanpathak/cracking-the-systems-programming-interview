# 2. The Architectural Substrate and Execution Constraints

The design and operational behavior of an operating system are
fundamentally dictated by the invariant properties of the underlying
hardware. These properties define the limits of execution, the necessity
of memory management, and the mechanisms for enforcing system integrity.

<div class="callout glance">
<span class="label">This chapter covers</span>

- the execution model, the program counter, and the stack pointer
- why an increment is not atomic
- the memory hierarchy, locality, and the 64-byte cache line
- privilege levels and privileged instructions
- traps and interrupts
- the boot sequence, from firmware to the first process

</div>

## 2.1 The Execution Model and the Atomicity Gap

A processor core operates via a continuous fetch-decode-execute cycle,
where the architectural state of a program is encapsulated by its
registers, most critically the Program Counter (PC) and the Stack Pointer
(SP). While the cycle ensures that individual instructions are processed
sequentially, it does not guarantee the atomicity of high-level
operations.

The fundamental discrepancy between high-level language abstractions and
machine-level execution introduces significant concurrency risks. An
ostensibly indivisible operation, such as a variable increment, typically
decomposes into a sequence of discrete instructions: a load, an arithmetic
update, and a store.

```asm
load  r1, [0x1000]    ; r1 = counter
add   r1, r1, 1       ; r1 = r1 + 1
store [0x1000], r1    ; counter = r1
```

In multi-core environments, the interleaving of these instructions across
different cores can result in lost updates, where the intermediate state
of one core is overwritten by another before completion. With the counter
at 42, two cores that both load before either stores each compute 43 and
each store 43, so two increments advance the counter by one. This lack of
inherent atomicity necessitates the implementation of synchronization
primitives and atomic hardware instructions to ensure state consistency.
Chapter 4 reproduces the lost update with real threads, and Chapter 6
introduces the instructions that render the three steps indivisible.

<figure>
<img src="figures/ch02_machine.svg" alt="Block diagram of a CPU core with registers, ALU, control unit, MMU, caches, DRAM, PCIe devices, timer, and interrupt controller"/>
</figure>

Figure 2-1 fixes the machine model assumed throughout this book. Beyond
the core and its caches, three components recur in later chapters. The
memory management unit (MMU) translates every address the core issues
into a physical location, consulting the tables of Chapter 7. The
interrupt controller aggregates device signals and presents them to the
core as interrupts, on which Chapters 10 and 13 depend. The timer raises
an interrupt at a fixed interval, and that interrupt is the means by which
the scheduler of Chapter 5 reclaims the CPU from a running program.

## 2.2 Memory Hierarchy and Locality Dynamics

The memory subsystem is defined by a tiered hierarchy that manages the
inherent tension between capacity and latency. This hierarchy ranges from
low-latency, low-capacity registers and multiple levels of cache (L1, L2,
L3) to high-capacity, high-latency DRAM.

The magnitudes involved span two orders. An L1 cache of 32 to 64 KiB
answers in about 4 cycles, an L2 cache of 256 KiB to 1 MiB in about 10,
and an L3 cache of 4 to 32 MiB in about 40, whereas a DRAM access costs on
the order of 100 ns and storage devices are slower again by several orders
of magnitude. Figure 18-1 presents the complete hierarchy.

The performance efficacy of this hierarchy is entirely contingent upon the
principle of locality:

- **Temporal Locality:** The reuse of recently accessed memory locations.
- **Spatial Locality:** The access of memory addresses in close proximity
  to one another.

Programs that exhibit high locality maximize cache hits, whereas irregular
access patterns induce frequent misses, forcing the processor to stall
while awaiting data from DRAM. Furthermore, the hardware's management of
data in 64-byte cache lines introduces the phenomenon of false sharing.
This occurs when multiple cores contend for exclusive ownership of the
same cache line to update logically independent data, resulting in
significant, unintended synchronization overhead due to constant cache
line movement between cores.

Chapter 18 quantifies the cost of poor locality by sweeping over buffer
sizes, Chapter 7 extends the hierarchy with page tables and the TLB, and
Chapter 17 measures false sharing and eliminates it.

<div class="callout keyidea">
<span class="label">Key idea</span>

The running time of a loop depends on the order in which it accesses
memory as much as on the number of instructions it executes. Two loops
with equal instruction counts can differ in speed by a factor of 10 when
one finds its data in cache and the other does not.

</div>

## 2.3 Privilege Domains and Boundary Enforcement

System integrity is maintained through the hardware-enforced bifurcation
of execution into User Mode and Kernel Mode. This distinction restricts
access to privileged instructions, such as those modifying page tables,
configuring device controllers, or altering interrupt masks, to the
kernel. Any attempt by user-mode code to execute these instructions
triggers a hardware-level fault, transferring control to the kernel for
remediation.

To optimize the performance of mode transitions, the kernel is typically
mapped into the address space of every process. While this shared mapping
allows for low-latency entry via system calls without requiring a change
of page tables, it imposes a critical security requirement: the kernel
must rigorously validate every pointer provided by a user-mode process.
Failure to do so could allow a program to exploit the kernel's elevated
privileges to access or modify protected memory.

<figure>
<img src="figures/ch02_privilege.svg" alt="User mode and kernel mode separated by a privilege boundary, with system call and return arrows crossing it"/>
</figure>

Figure 2-2 depicts this shared address space, with the privilege boundary
separating the two domains and the system call and return paths crossing
it.

<div class="callout note">
<span class="label">Other privilege levels</span>

x86 defines 4 rings, and arm64 defines 4 exception levels. Linux and macOS
use one level for the kernel (ring 0 on x86) and one for all user programs
(ring 3). The remaining levels host hypervisors and firmware, which
Chapter 16 addresses.

</div>

## 2.4 Synchronous and Asynchronous Control Transfers

The transition from user-mode execution to kernel-mode service is mediated
by two distinct classes of control transfers, categorized by their
relationship to the instruction stream:

- **Traps (Synchronous):** These are events triggered directly by the
  execution of a specific instruction, such as a system call, a page
  fault, or an arithmetic exception. Because they are synchronous, they
  are deterministic and tied to a specific point in the program's
  execution.
- **Interrupts (Asynchronous):** These are signals generated by external
  hardware peripherals (e.g., timers, network controllers) that occur
  independently of the current instruction stream. Interrupts allow the
  kernel to respond to real-world events and implement preemptive
  scheduling, enabling the system to handle concurrent hardware events
  without continuous polling.

Both mechanisms utilize a standardized hardware sequence: the CPU saves
the current architectural state, elevates the privilege level, and jumps
to a predefined kernel entry point to handle the event. Kernel code at
that entry point preserves the remaining registers, services the event,
restores the saved state, and returns. The context switch of Chapter 5
follows the identical sequence, except that the kernel restores the
registers of a different program. An interrupt may likewise end with a
different program running, since the event may have terminated that
program's wait: a thread blocked in `poll`, for instance, becomes runnable
when a packet arrives, a behavior on which Chapter 13 relies.

## 2.5 The Boot Sequence

The boot sequence exercises every part of the machine described so far,
which makes it a common interview question.

1. When power is applied, the CPU begins executing **firmware** stored on
   the motherboard. The firmware initializes memory and devices and
   searches for a disk that contains a bootloader.
2. The firmware loads the **bootloader** into memory and jumps to it. The
   bootloader loads the kernel and jumps to the kernel.
3. The kernel builds its page tables and its table of processes, and it
   initializes the device drivers.
4. The kernel creates the first process. On Linux, this process runs
   `init` (on most distributions, `systemd`). On macOS, it runs `launchd`.
5. The first process starts system services, one of which eventually
   starts a shell.
6. When we type a command, the shell calls `fork` to create a new process
   and `execve` to load our program into it. We follow these two calls in
   Chapter 3.

Step 4 cannot happen until the kernel has working page tables, a memory
allocator, and a scheduler that can select a process. These are the
subjects of Chapters 7, 8, and 5.

<div class="callout summary">
<span class="label">Summary</span>

- A core repeats fetch, decode, and execute, and the program counter holds
  the address of the next instruction.
- An increment of a variable in memory takes three instructions. Because
  another core can run between them, concurrent increments can lose
  updates.
- Memory forms a hierarchy of registers, three cache levels, and DRAM.
  Programs with good locality find most of their data in cache.
- Caches hold 64-byte lines, and a core must own a line to write to it.
  Two threads that write to one line slow each other down even when they
  write to different bytes.
- Privileged operations execute only in kernel mode. The kernel is mapped
  into every process but is inaccessible from user mode, and it must check
  every pointer that a program passes to it.
- A trap is caused by the running instruction and an interrupt by a
  device. Both enter the kernel at a fixed address.
- A computer boots in the order firmware, bootloader, kernel, first
  process.

With this model of the machine in place, Chapter 3 turns to the first
abstraction that an operating system provides, the process.

</div>
