# 1. The Ontological Necessity of the Operating System

The requirement for an operating system is fundamentally predicated on the
inherent architectural limitations of bare-metal execution. In a primitive
hardware environment, a single processor core is constrained by a solitary
program counter, which effectively precludes multi-program concurrency by
capturing the instruction stream. Furthermore, the absence of a
supervisory layer leaves the system without mechanisms for memory
protection or instruction restriction, rendering any program capable of
unmitigated interference with the hardware or other co-resident software.
Finally, the lack of unified device drivers necessitates that every
application manage its own hardware-specific communication, a process that
is both inefficient and prone to catastrophic resource contention.

<div class="callout glance">
<span class="label">This chapter covers</span>

- what a program cannot do on a machine with no operating system
- how batch monitors, time sharing, and Unix led to today's systems
- abstraction, isolation, and resource management, and why each
  necessitates the next
- mechanism and policy
- kernel mode, user mode, and the cost of each kernel structure
- the path of a system call, its error convention, and its cost
- the POSIX calls used in later chapters

</div>

## 1.1 Execution on Bare Hardware

Load a single program into the memory of the machine described in Chapter
2 and start the CPU at its first instruction. The program has the entire
instruction set at its disposal and runs correctly, yet the same freedom
that lets it run precludes three things.

**Concurrency is precluded by the single program counter.** A core holds
one program counter, the register that addresses the next instruction, so
it can follow only one instruction stream. Sharing the core between two
programs requires code that belongs to neither: code that stops one
stream, preserves its register values, installs those of the other, and
resumes there. In the absence of such code, the first program occupies
the core until it ends.

**Protection is precluded by unrestricted instructions.** Since the
program may execute any instruction, it can read or write every byte of
memory, silence the timer, and reprogram the hardware that translates
addresses. A second program loaded beside it would therefore be exposed to
every bug in the first, and no check written in software could change
that, because the first program could overwrite the check itself.

**Device independence is precluded by the absence of shared drivers.**
Obtaining 512 bytes from a disk means writing a command to the controller,
awaiting its interrupt, and inspecting its status bits, and a network
packet demands the same from a different controller. This logic is
specific to one controller model, so every program would have to embed a
copy, and two programs commanding the same controller at once would
corrupt each other's transfers.

Each deficiency calls for code that stands above individual programs: a
switcher for the CPU, limits that the hardware enforces on every program,
and one set of drivers that all programs share. That code is the
operating system.

## 1.2 Historical Derivation

These remedies were not designed together. Each was introduced when its
absence became too costly, and the order of their introduction still
determines how systems are layered.

The computers of the early 1950s were precisely the machine of Section
1.1. Because an hour of machine time cost far more than an hour of its
operator's time, the minutes lost between one job and the next were the
first inefficiency to be attacked. The remedy was the *batch monitor*, a
small resident program that loaded each job as soon as its predecessor
ended. GM-NAA I/O, written in 1956 for the IBM 704, is generally regarded
as the first.

A batch monitor removed idle time between jobs but not within them, since
a job waiting for a tape still held the processor. *Multiprogramming*
recovered that time by keeping several jobs in memory and switching away
from any job that waited for a device. Switching, however, imposed two
requirements on hardware. Regaining the processor from a job that never
waits necessitates a timer interrupt, and protecting the monitor from a
faulty job necessitates a privileged mode. The Atlas computer, completed
in Manchester in 1962, provided both, together with an early form of
virtual memory.

*Time sharing* applied the same switching at intervals short enough for
people to work interactively at terminals. MIT demonstrated CTSS, the
Compatible Time-Sharing System, in 1961, and its successor Multics, begun
in 1965, contributed much of the vocabulary still in use. Unix followed in
1969, when Ken Thompson and Dennis Ritchie at Bell Labs built a far
smaller system around a few ideas: processes created by `fork`, a
hierarchy of files, and devices that are read and written as though they
were files. Its interface was standardized as POSIX, first published as
IEEE Standard 1003.1 in 1988. Linux and macOS both implement that
interface, and it underpins every listing in this book.

## 1.3 Abstraction, Isolation, and Resource Management

To resolve these deficiencies, the operating system implements three
critical roles: abstraction, isolation, and resource management. Through
abstraction, the OS mediates between complex hardware interfaces and
simplified software objects, such as processes, files, and sockets,
thereby decoupling program logic from physical device geometry. This
abstraction, however, necessitates isolation; once multiple processes
coexist within a managed environment, the OS must enforce strict
boundaries to prevent cross-process interference. This enforcement is
delegated to the hardware through privilege levels and page tables,
ensuring that memory and resource access remain confined to authorized
domains. The resulting contention for finite hardware necessitates
resource management, where the OS acts as a central arbiter, orchestrating
the distribution of CPU time, memory capacity, and I/O bandwidth according
to evolving workload policies.

Each role is developed in later chapters: the abstractions of process,
memory, and file in Chapters 3, 7, and 12, the enforcement of isolation in
Chapters 2, 7, and 16, and the arbitration of CPU time, memory, and I/O in
Chapters 5, 7, and 13.

<figure>
<img src="figures/ch01_layers.svg" alt="Four layers: applications, system libraries, kernel, hardware, with requests flowing down and interrupts flowing up"/>
</figure>

Figure 1-1 arranges a running system in four layers. Requests descend: an
application calls a library function such as `printf`, the library
converts that call into one or more system calls, and the kernel carries
those out with instructions that only it may execute. Events ascend: a
device raises an interrupt when it has completed a transfer or holds new
data, and the kernel passes the result to the waiting program.

## 1.4 Mechanism and Policy

The implementation of these roles relies on the distinction between
mechanism and policy. Mechanisms, the low-level primitives provided by the
hardware, such as context switching or page table walks, remain constant
across architectural iterations, while policies, the logic governing which
process to schedule or which page to evict, are tuned to specific system
requirements.

Keeping the two apart lets each change at its own rate. Mechanisms persist
for as long as the processor architecture does, while policies are revised
whenever workloads shift. Linux, for example, replaced its scheduling
policy in version 6.6 without altering the code that switches between
processes. Later chapters follow the same division, presenting a
mechanism first and then the policies that operate it.

## 1.5 Privilege Modes and Kernel Structure

Isolation demands that some code be able to do what ordinary programs
cannot, and processors supply that asymmetry through two execution modes.
**Kernel mode** permits every instruction. **User mode** withholds a small
set of *privileged instructions*, namely those that change page tables,
mask interrupts, or write to device registers. An attempt to execute one
of them in user mode does not succeed silently or fail silently. It
raises a fault, and control passes to the operating system.

The portion of the operating system that executes in kernel mode is the
**kernel**. Everything else, including the C library, the shell, and
system services, executes in user mode exactly as applications do. Only
the kernel can therefore switch processes, edit page tables, and address
devices, which is why all three roles of Section 1.3 are discharged there.

How much code to place in kernel mode is governed by a tension between
speed and fault containment. A *monolithic* kernel, such as Linux, places
scheduling, memory management, file systems, network protocols, and device
drivers in one program. Its parts communicate by ordinary function calls,
which is fast, but a fault in any driver can bring down the whole system,
and the Linux kernel has grown beyond 30 million lines of source code,
most of them drivers. A *microkernel* retains only address spaces,
threads, and message passing in kernel mode and runs file systems and
drivers as user-mode processes. A faulty driver can then be restarted like
any other process, at the price of a message exchange wherever a
monolithic kernel makes a function call. XNU, the kernel of macOS,
occupies a middle position: it combines the Mach microkernel with
components from BSD Unix, but runs both in kernel mode within one address
space.

A further design decision keeps entry into the kernel cheap. Although
user-mode code cannot access kernel memory, that memory is mapped into the
address space of every process, with its pages marked inaccessible from
user mode. Entering the kernel therefore requires no change of page
tables. The CPU raises its privilege level and jumps to a fixed kernel
address, as Figure 2-2 in the next chapter shows.

## 1.6 The System Call Interface

The boundary between the kernel (which executes in a privileged mode with
unrestricted instruction access) and user-mode applications is mediated
through the system call interface. A system call provides a
hardware-supervised, deterministic transfer of control, allowing a program
to request kernel services without compromising the integrity of the
kernel's own address space. This transition, while computationally
expensive compared to standard function calls, serves as the essential
gatekeeper for system security and stability.

The transfer itself follows a fixed protocol. A program deposits a number
identifying the requested service in one register and the arguments in
others, and then executes a dedicated instruction (`syscall` on x86-64,
`svc` on arm64). The CPU elevates to kernel mode and resumes at an address
that the kernel registered during boot. Because the program cannot
influence that address, entry into the kernel is confined to points that
the kernel itself designates.

Consider a program on Linux for x86-64 that writes the six bytes `hello\n`
to its terminal.

```cpp
write(1, "hello\n", 6);
```

1. `write` is a short function in the C library. It loads 1, the number of
   the `write` service, into register `rax`, and the three arguments into
   `rdi`, `rsi`, and `rdx`. It then executes `syscall`.
2. The `syscall` instruction saves the address of the next instruction in
   `rcx` and the flags in `r11`, switches the CPU to kernel mode, and
   loads the program counter from a register that only kernel-mode code
   can set.
3. The kernel's entry code saves the remaining registers, verifies that
   `rax` holds a valid number, and calls the function that the system call
   table lists for it.
4. That function looks up descriptor 1 in the process's table of open
   files and finds the terminal there. It confirms that the 6 bytes at the
   address in `rsi` lie in memory that the process may read, copies them,
   and passes them to the terminal driver.
5. The kernel stores 6, the number of bytes written, in `rax`, restores
   the saved registers, and returns to user mode, where the program
   continues after the call.

Step 4 contains a check that the boundary makes mandatory. The address in
`rsi` comes from an untrusted program, and kernel-mode code is permitted
to read any memory, so an unverified pointer would let a program read the
kernel's own data through the kernel.

Failure is reported through a convention with two layers. On Linux, the
kernel returns a negative error number in `rax`. Were descriptor 1 closed,
for instance, `rax` would hold -9, the negation of `EBADF`. The C library
converts this value before the program sees it, storing 9 in the variable
`errno` and returning -1. A program must therefore test the result of
every system call, and `errno` is meaningful only after a call has
returned -1.

The crossing is also expensive. The five steps above take a few hundred
nanoseconds, over two hundred times as long as an ordinary function call,
as Chapter 9 measures. Two techniques contain that cost. Libraries avoid
crossings where they can: both `fwrite` and `printf` accumulate output in
a buffer inside the process and call `write` only when the buffer fills or
the program flushes it, so a thousand calls to `printf` may produce a
single `write`. The kernel, for its part, serves a few frequent requests
with no crossing at all. Linux maps a small shared library, the *vDSO*,
into every process, through which functions such as `clock_gettime` read
the current time from a page that the kernel keeps up to date.

The system calls used in this book belong to POSIX. Table 1-1 lists those
that appear in later chapters.

**Table 1-1. POSIX calls in this book.**

| Call | What it does | Chapter |
|---|---|---|
| `open` / `read` / `write` / `close` | access files through descriptors | 12, 13 |
| `fork` / `waitpid` / `execve` | create, reap, and replace processes | 3 |
| `mmap` / `mprotect` / `munmap` | map memory and change its protection | 7, 11 |
| `pipe` / `socketpair` | create communication channels | 11 |
| `poll` / `kqueue` / `epoll` | wait for readiness on many descriptors | 13 |
| `sigaction` / `sigprocmask` | install and mask signal handlers | 10 |
| `bind` / `listen` / `accept` / `connect` | establish network connections | 14 |
| `setsid` / `umask` / `chdir` | detach a daemon from its terminal | 15 |

## 1.7 Scope

The internals of a particular kernel lie outside this book. Chapter 7, for
example, presents the page table walk on x86-64 and arm64, but not the
structures in which Linux records the memory regions of a process.
Graphical interfaces are likewise excluded, as is kernel code itself. In
its place, Chapters 5 and 8 implement a scheduler and two allocators as
ordinary user-mode programs, where every decision they make can be
printed.

<div class="callout summary">
<span class="label">Summary</span>

- A single program counter precludes concurrency, unrestricted
  instructions preclude protection, and the absence of shared drivers
  ties every program to particular devices.
- Batch monitors, multiprogramming, and time sharing supplied the
  remedies between 1956 and the 1960s. Multiprogramming necessitated the
  timer interrupt and the privileged mode. Unix, from 1969, is the origin
  of the POSIX interface.
- Abstraction necessitates isolation, and isolation leaves contention for
  hardware that resource management must resolve. Isolation depends on
  the CPU, because a software check can be overwritten.
- Mechanisms are dictated by hardware and policies by workloads, so the
  two are kept apart.
- The kernel is the code that runs in kernel mode. Monolithic kernels buy
  speed at the cost of fault containment, and microkernels make the
  opposite trade.
- A system call enters the kernel at an address that the kernel chose,
  and the kernel verifies every pointer it receives. On failure, the C
  library returns -1 and sets `errno`.
- A crossing costs a few hundred nanoseconds, which buffering in
  libraries and the vDSO reduce.

Chapter 2 describes the hardware on which this design rests, from
registers and caches to privilege levels and interrupts.

</div>
