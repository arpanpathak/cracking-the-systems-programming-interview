# 1. What an Operating System Is

An operating system is the software that runs in privileged mode and owns the
hardware. Every other program — browser, compiler, server — runs in a
restricted mode and asks the operating system for what it needs. This chapter
explains why that arrangement exists, what the operating system does with the
privilege, and how your programs talk to it.

<div class="callout glance">
<span class="label">At a glance</span>

- Three jobs: present abstractions, isolate programs from one another, and
  manage shared resources.
- The kernel is the privileged core; everything else runs in user mode.
- System calls are the only door between the two.

</div>

## 1.1 The machine without an operating system

Start with the hardware from Chapter 2 and imagine no operating system at
all. A program then runs directly on the CPU, with every instruction of the
instruction set available to it. Three problems follow immediately.

**One program at a time.** The CPU has one program counter. Running two
programs means deciding which one owns the CPU now, saving the state of the
one being interrupted, and restoring the state of the one being resumed.
Without software to perform that save and restore, the machine runs one
program until it finishes.

**No safe sharing.** A program that can execute every instruction can
reprogram the memory-management hardware, stop the timer, and read any byte
of memory. One faulty or hostile program can corrupt another program's data
or take the machine down. Protection is not a policy choice at this level;
it is a property of which instructions are allowed, and something must
enforce that property.

**Every device is raw.** Reading a sector from a disk means programming the
disk controller's registers, waiting for an interrupt, and checking status
bits. Reading a packet means the same against the network controller. Every
program would carry its own copy of that logic, written against one
particular controller, and two programs talking to the same device at once
would corrupt each other's transfers.

Each problem has the same shape: the hardware is capable, but nobody is
standing between the programs and the capability. That standing-between is
the operating system's existence.

<div class="callout keyidea">
<span class="label">Key idea</span>

The operating system exists because the hardware provides no mediation. It
converts raw capability into services, and exclusivity into scheduling.

</div>

## 1.2 The three jobs

Everything an operating system does reduces to three jobs, and the book is
organized around them.

**Abstraction.** The operating system replaces raw hardware with objects a
programmer can reason about. A running program becomes a **process** with its
own address space. A region of storage becomes a **file** with a name and a
position. A network endpoint becomes a **socket**. Each abstraction hides the
physical detail and presents a stable interface instead: processes do not
need to know which frames of RAM they occupy, and files do not need to know
which sectors hold them. Chapters 3, 7, and 12 build these abstractions.

**Isolation.** Each process believes it has the machine to itself. It cannot
write another process's memory, exhaust another process's file descriptors,
or read another process's packets. Isolation is enforced by the hardware
(page tables and privilege levels) under the operating system's direction,
and it is what lets one machine run an editor and a database server
simultaneously without either trusting the other. Chapters 2, 7, and 16
develop the enforcement machinery.

**Resource management.** The machine has one CPU, one memory system, and one
of each device; the workload has many processes. The operating system
decides who runs next, which pages stay in memory, and in what order disk
requests are issued. These decisions are scheduling, and they appear
everywhere: the CPU scheduler in Chapter 5, the memory manager in Chapter 7,
the I/O stack in Chapter 13.

<figure>
<img src="diagrams/ch01_layers.svg" alt="Four layers: applications, system libraries, kernel, hardware, with requests flowing down and interrupts flowing up"/>
</figure>

The diagram has four layers. Applications call library functions. The
libraries translate those calls into system calls. The kernel executes the
system calls in privileged mode. The hardware executes instructions and
raises interrupts when a device needs attention. Notice what sits directly
on the hardware: the kernel, and nothing else.

## 1.3 The kernel and user mode

The word **kernel** names the part of the operating system that runs in
privileged mode. The rest of the operating system — libraries, tools,
services — runs in user mode like any other program. The distinction is
about privilege, not about importance.

Chapter 2 defines the two modes precisely. For this chapter, two facts
matter. First, privileged instructions — those that change page tables,
mask interrupts, or write device registers — execute only in kernel mode.
Second, the kernel's code and data are mapped into every process's address
space, so that when a program makes a system call the CPU can enter kernel
code without switching address spaces. The kernel is therefore present in
every process but reachable only through controlled entry points. Figure
2-2 draws this arrangement.

That one arrangement produces the three jobs. Abstraction lives in the
kernel because only kernel code can build page tables and device
transfers. Isolation lives in the kernel because only kernel code can
decide which pages a process may touch. Management lives in the kernel
because only kernel code runs at the moment resources change hands.

## 1.4 System calls: the only door

A program in user mode cannot touch the kernel's memory and cannot execute
privileged instructions. It can ask for services through one mechanism: the
**system call**. A system call is a controlled transfer into the kernel at a
fixed entry point, with a number selecting the service and registers
carrying the arguments. Chapter 9 walks the transfer step by step and
measures what it costs.

The POSIX interface that this book uses is a set of system calls with
documented behavior. The ones you will meet in later chapters:

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

A library call and a system call are different things. `fwrite` is a library
function that buffers in your process and issues `write` system calls when
its buffer fills. `printf` formats first, then writes. Chapter 9 measures
the difference, and the measurement is not small: a system call crosses the
privilege boundary, and the boundary is expensive.

## 1.5 What this book does not cover

Three omissions keep the book honest. It does not cover the internals of one
particular kernel; the page table walk in Chapter 7 describes x86-64 and
arm64 at the level a systems engineer needs, not the data structures a
kernel developer maintains. It does not cover graphical interfaces; nothing
in the later chapters depends on one. It does not cover kernel development
itself — writing a scheduler or a file system — except through the
simulations in Chapters 5 and 8, which reproduce the decisions a kernel
makes, in user mode, where you can watch them run.

<div class="callout summary">
<span class="label">Summary</span>

- An operating system is privileged software that owns the hardware and
  mediates all access to it.
- Its three jobs are abstraction, isolation, and resource management; every
  later chapter serves one or more of them.
- The kernel is the privileged core. Programs run in user mode and enter the
  kernel only through system calls.
- The machine model behind all of this — registers, caches, devices,
  interrupts, privilege levels — is Chapter 2.

</div>
