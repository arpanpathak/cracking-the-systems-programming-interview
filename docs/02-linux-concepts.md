# 02: Linux Concepts, Deep Dive

Linux systems questions concern what happens on a node when a Pod is scheduled,
why a container can or cannot see a device, and how a misbehaving node is found.
The answers are in the kernel objects, syscalls, data structures, and commands
below.

## How to read this chapter

Each mechanism is presented in four steps.

1. **The problem.** What goes wrong without the mechanism.
2. **The mechanism.** The kernel data structure or algorithm that solves it.
3. **A program.** A short C program, and in some sections the same thing in Rust
   through the `libc` crate.
4. **Output.** What the program prints, next to the command that shows the same
   thing from outside the process.

Every listing was compiled and run; the outputs are copied, not invented. The
machine was a Jetson (aarch64, Linux 5.15), gcc 11.4.0, rustc 1.96 nightly. On
aarch64 the system call instruction is `svc`, not `syscall`, and the addresses
printed below are 48-bit. On x86-64 the numbers differ; the mechanisms do not.

```bash
gcc -O2 -Wall -Wextra -o fork_cow fork_cow.c   # the C programs
cargo run --release --bin syscall_cost         # the Rust ones, libc is already a dependency
```

## Further reading

Nothing here is a substitute for these. They are the source for the full argument
behind any section below.

| Source | What it is good for |
|---|---|
| Arpaci-Dusseau, *Operating Systems: Three Easy Pieces* (free at `ostep.org`) | The clearest first pass on virtual memory, scheduling and concurrency. Read this first if the rest reads like vocabulary. |
| Bryant & O'Hallaron, *Computer Systems: A Programmer's Perspective* | Ties C code to machine code and the memory hierarchy. Chapters 8 and 9 are what a page fault actually does. |
| Tanenbaum & Bos, *Modern Operating Systems* | The canonical survey, and the one that compares Linux with other kernels rather than assuming it. |
| Silberschatz, Galvin & Gagne, *Operating System Concepts* | The course textbook. Use it to get definitions exact: working set, thrashing, demand paging. |
| Kerrisk, *The Linux Programming Interface* | The reference for the syscall boundary: every call, every error, every edge case. A dictionary, not a read-through. |
| Stevens & Rago, *Advanced Programming in the UNIX Environment* | Older, still unmatched on signals, process control and I/O idioms. |
| Love, *Linux Kernel Development* | A short tour of the kernel's own data structures by a former scheduler maintainer. |
| Bovet & Cesati, *Understanding the Linux Kernel* | Dated but deep. Where to go for page-table and VFS internals. |
| Corbet, Rubini & Kroah-Hartman, *Linux Device Drivers* | How drivers attach to the kernel, which is where the GPU driver lives. |
| Drepper, "What Every Programmer Should Know About Memory" (2007) | Still the best free account of caches, TLBs and NUMA. |
| Ritchie & Thompson, "The UNIX Time-Sharing System" (CACM, 1974) | Six pages that explain why the process and file abstractions look like this. |
| Saltzer & Kaashoek, *Principles of Computer System Design* | Naming, layering and fault containment: the "why" behind the abstractions. |

The quotations from Linus Torvalds below are short, attributed and dated. They are
here because each one states a position the surrounding section then argues from.

---

## 1. Process and thread model

### 1.1 The kernel's unit of execution is a task

On Linux, both processes and threads are represented by the same kernel
structure: `task_struct`. What we call a process is usually a **thread group**:
one or more tasks sharing the same Thread Group ID (`TGID`). In user space:

- `getpid()` returns the TGID of the calling task (the "process ID").
- `gettid()` returns the kernel task ID (`PID` in `/proc/<pid>/status`, i.e. `Tgid` vs `Pid`).
- `ps -Lf` and `top -H` show individual tasks/threads.

In `ps -eo pid,tid,ppid,comm`, the `pid` column is the process ID and `tid` is the
thread ID. For a single-threaded process they are the same number.

A single structure matters beyond convenience: separate process and thread tables
would force every scheduling decision, signal delivery and credential check to ask
which table it is looking at. With one `task_struct` and a `tgid` field, "thread"
becomes a relationship between tasks rather than a second kind of object. It is also
why `kill(2)` can address a thread or a whole thread group depending on how the id
is formed, and why `/proc/<tgid>/task/<tid>` exists as a directory rather than a
separate filesystem.

Linus Torvalds, on why the shape of the data matters more than the shape of the code
(git mailing list, 27 July 2006):

> I will, in fact, claim that the difference between a bad programmer and a good one
> is whether he considers his code or his data structures more important. Bad
> programmers worry about the code. Good programmers worry about data structures and
> their relationships.

The scheduler, the signal code, the accounting in cgroups and the `/proc` tree are all
views onto this one object, so questions about process behaviour are usually questions
about which field of it changed and who changed it.

### 1.2 `fork()`, `vfork()`, and `clone()`

- `fork()` creates a child task by copying the parent's address space,
  file-descriptor table, signal handlers, and most other process state. The
  copy is virtualized through **copy-on-write (COW)**: both parent and child
  initially point at the same physical pages marked read-only. When either one
  writes, the kernel duplicates the page. This is why `fork()` is cheap for
  small children and why memory usage (`PSS`) should not be computed as
  `RSS(parent) + RSS(child)`.
- `vfork()` originally suspended the parent until the child called `exec()`
  or `exit()`; it is rarely needed today because COW already makes `fork()`
  cheap.
- `clone()` is the low-level syscall used by pthreads and container runtimes.
  Flags select what is shared with the child. `clone(CLONE_THREAD)` creates a
  thread; `clone(CLONE_NEWPID|CLONE_NEWNS|...)` creates a process in new
  namespaces, which is what `runc` does to start a container.

**Threads are processes that share an address space, file descriptors, and signal
handlers; they are not a separate kernel concept.**

#### What copy-on-write does

`fork()` copies nothing at the moment of the call. It marks the parent's writable
pages read-only in *both* page tables; the first writer among the two takes a
protection fault, and the kernel duplicates that one page and hands out a writable
mapping. The program below makes the consequence visible: parent and child print the
*same* address holding *different* values, which is only possible because the address
printed is virtual and the physical frame behind it was duplicated on the first write.

```c
/* fork_cow.c: the child gets a private copy of the parent's memory. */
#include <stdio.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void)
{
    int value = 42;                     /* on the parent's stack */
    pid_t pid = fork();

    if (pid < 0) {
        perror("fork");
        return 1;
    }

    if (pid == 0) {
        value = 99;                     /* writes to a private copy */
        printf("child : pid=%d value=%d address=%p\n",
               (int)getpid(), value, (void *)&value);
        fflush(stdout);                 /* flush before _exit, or this line is lost */
        _exit(0);                       /* exit() would flush too, and run atexit handlers */
    }

    waitpid(pid, NULL, 0);
    printf("parent: pid=%d value=%d address=%p\n",
           (int)getpid(), value, (void *)&value);
    return 0;
}
```

```text
$ gcc -O2 -o fork_cow fork_cow.c && ./fork_cow
child : pid=1939075 value=99 address=0xffffeb225404
parent: pid=1939074 value=42 address=0xffffeb225404
```

Two processes, one address, two values. `cat /proc/<pid>/smaps` shows the copied page
as a dirty anonymous page charged to each process separately, which is exactly what
`PSS` accounts for and `RSS` does not.

**The trap in that listing is the `fflush`.** Stdout to a pipe is block-buffered, and
`_exit(2)` does not run the stdio flush. A program that prints in the child and then
calls `_exit` loses the output with no error to explain it:

```c
/* lost.c: the child's output disappears. */
#include <stdio.h>
#include <unistd.h>

int main(void)
{
    printf("child\n");   /* sits in the buffer */
    _exit(0);            /* does not flush it */
}
```

```text
$ gcc -O2 -o lost lost.c && echo "captured: [$(./lost)]"
captured: []
```

This is the same class of bug as writing to a forked child while a lock on the stdio
buffer is held: the buffer was duplicated by the fork, so the data is either lost or
printed twice.

#### The same thing in Rust

Rust reaches `fork(2)` through the `libc` crate. The constraint is on what the child
may do afterwards: POSIX permits only async-signal-safe functions between `fork()`
and `exec()`. That excludes nearly everything in `std::io`, because those functions
may take locks and touch buffers that the fork duplicated. The listing therefore
writes with `write(2)` directly.

```rust
//! fork_cow.rs
use libc::{fork, getpid, waitpid};

/// `write(2)` directly: after `fork()` only async-signal-safe calls belong in the
/// child. `println!` is not one of them.
fn raw_print(text: &str) {
    // SAFETY: `text` is valid for `text.len()` bytes for the duration of the call.
    unsafe { libc::write(1, text.as_ptr() as *const libc::c_void, text.len()) };
}

fn main() {
    let mut value: i32 = 42; // on the parent's stack

    // SAFETY: single-threaded, and the child performs one write() then _exit().
    let pid = unsafe { fork() };

    if pid < 0 {
        eprintln!("fork failed");
        std::process::exit(1);
    }

    if pid == 0 {
        value = 99; // writes into the child's private copy of the page
        raw_print(&format!(
            "child : pid={} value={} address={:p}\n",
            unsafe { getpid() },
            value,
            &value as *const i32
        ));
        // SAFETY: _exit skips destructors and the stdio flush, which is the point.
        unsafe { libc::_exit(0) };
    }

    // SAFETY: `pid` is the child created above.
    unsafe { waitpid(pid, std::ptr::null_mut(), 0) };
    println!(
        "parent: pid={} value={} address={:p}",
        unsafe { getpid() },
        value,
        &value as *const i32
    );
}
```

```text
$ cargo run --release --bin fork_cow
child : pid=1938714 value=99 address=0xffffd94eee74
parent: pid=1938713 value=42 address=0xffffd94eee74
```

Calling `fork` from a process that already has other threads is dangerous, and
`std::process::Command` exists so that this is rarely written by hand: it uses
`posix_spawn` or `fork` plus `exec`, so the child never runs arbitrary Rust between
the two.

### 1.3 `exec()` replaces the process image

`execve(path, argv, envp)` does not create a new PID. It destroys the current
process's address space and loads the new program, then starts execution at its
entry point. The file descriptor table survives unless `FD_CLOEXEC` is set on a
descriptor; that flag causes the descriptor to close automatically during
`exec`. Servers therefore set `O_CLOEXEC` on sockets and files.

Typical shell sequence:

```text
bash
 └─ fork()              # child bash process
     └─ execve("curl")  # child keeps PID but becomes curl
```

### 1.4 What happens during a system call

A userspace program cannot touch hardware or kernel memory directly. A function
such as `read()` goes through the C library (or raw `syscall` instruction) and:

1. Places the syscall number and arguments in registers.
2. Executes `syscall` (x86-64) or `svc` (AArch64).
3. The CPU traps into kernel mode.
4. The kernel validates arguments, copies data from user pointers, executes the
   operation on the current task's kernel stack, copies results back.
5. Control returns to user mode with a result in a register.

The kernel may sleep the task if the syscall blocks (e.g. waiting for network
data). When that happens, the scheduler runs another runnable task.

`strace` is a tracer that intercepts these syscalls and can reveal why a program is
slow or why it fails.

#### What the crossing costs

The steps above are the whole mechanism. What makes it expensive is that it is a
privilege transition: the CPU saves the user context, switches to the kernel stack,
runs the entry path, and switches back. That cost is paid before the operation itself
does any work, which is why even a call that does almost nothing is measurable.

```rust
//! syscall_cost.rs
use std::hint::black_box;
use std::time::Instant;

const ITERATIONS: u32 = 1_000_000;

fn main() {
    // Warm up: the first calls pay for page faults and lazy symbol resolution.
    for _ in 0..10_000 {
        black_box(unsafe { libc::getpid() });
    }

    let start = Instant::now();
    for _ in 0..ITERATIONS {
        // SAFETY: getpid takes no arguments and cannot fail.
        black_box(unsafe { libc::getpid() });
    }
    let elapsed = start.elapsed();

    println!("{} getpid() calls in {:?}", ITERATIONS, elapsed);
    println!(
        "{:.1} ns per call",
        elapsed.as_nanos() as f64 / f64::from(ITERATIONS)
    );
}
```

```text
$ cargo run --release --bin syscall_cost
1000000 getpid() calls in 229.03379ms
229.0 ns per call
```

That number belongs to one machine, one kernel, one frequency governor. This
repository's own `src/bin/syscall_overhead.rs` reports 207.6 ns for the same call on
the same host at a different moment. A ten percent spread on a fixed instruction is
the answer to how fast a syscall is, which is why every measured figure here is
printed beside the machine that produced it.

The practical consequences: a server that issues one `read()` per 8 bytes pays more for
crossings than for copying. Batching (`sendmmsg`, `recvmmsg`, `io_uring`), mapping
instead of reading (`mmap`), and user-space networking (DPDK) all buy back the same
transition. `strace -c` counts the crossings the kernel actually handled, which is why
it is the first tool for "why is this syscall-bound".

#### Why this interface cannot change

The syscall number, the argument layout and the error convention (`-1` plus `errno`)
are fixed for the architecture, and they are a published interface. Binaries compiled
years ago against a kernel that no longer exists still run because of it.

Linus Torvalds, on a proposed change that would have broken that interface (LKML,
23 December 2012):

> WE DO NOT BREAK USERSPACE!
>
> Seriously. We've been doing this for decades. The fact that you don't understand why
> is not an excuse.

The transferable rule: extending a public API means adding rather than modifying,
and giving a version to anything that cannot be added. That is the same decision at
a much smaller scale.

### 1.5 Process states, zombies, and orphans

The `STAT` column in `ps` is the state:

| State | Meaning |
|---|---|
| `R` | Running or runnable |
| `S` | Interruptible sleep (waiting for I/O/event) |
| `D` | Uninterruptible sleep (usually waiting on kernel I/O) |
| `T` | Stopped (`SIGSTOP`) |
| `Z` | Zombie: exited but not yet reaped by parent |
| `I` | Idle kernel thread |

A **zombie** is a task that has exited but whose `task_struct` is kept until the
parent calls `wait()`. The kernel must preserve the exit status for the parent.
If a parent never calls `wait()`, the child remains a zombie. If the parent
dies, the child is reparented to `init`/`systemd` (PID 1), which reaps it.

A **D-state** process cannot be killed until the kernel I/O completes. Storage and
network hangs produce D-state processes, and the fix is the underlying device
rather than `kill -9`.

#### Watching the state field change

Field 3 of `/proc/<pid>/stat` is a single character, and it is the same character `ps`
prints in its `STAT` column. The program below forks a child, deliberately does *not*
reap it, and reads that field.

```c
/* zombie.c: an exited child stays in the process table until it is reaped. */
#include <stdio.h>
#include <sys/wait.h>
#include <unistd.h>

static void show_state(const char *label, pid_t pid)
{
    char path[64];
    FILE *f;
    int first;
    char comm[64];
    char state;

    snprintf(path, sizeof path, "/proc/%d/stat", (int)pid);
    f = fopen(path, "r");
    if (f == NULL) {
        printf("%s: /proc/%d/stat is gone\n", label, (int)pid);
        return;
    }
    /* field 1 is the pid, field 2 the command in parentheses, field 3 the state */
    if (fscanf(f, "%d %63s %c", &first, comm, &state) == 3)
        printf("%s: state '%c'\n", label, state);
    fclose(f);
}

int main(void)
{
    pid_t pid = fork();

    if (pid < 0) {
        perror("fork");
        return 1;
    }

    if (pid == 0)
        _exit(0);                       /* the child is gone in microseconds */

    printf("parent %d, child %d has exited\n", (int)getpid(), (int)pid);
    sleep(1);                           /* let the child exit first */
    show_state("exited, not reaped", pid);
    show_state("still not reaped", pid);

    waitpid(pid, NULL, 0);              /* only now is the child reaped */
    show_state("after waitpid", pid);
    return 0;
}
```

```text
$ gcc -O2 -o zombie zombie.c && ./zombie
parent 1939371, child 1939372 has exited
exited, not reaped: state 'Z'
still not reaped: state 'Z'
after waitpid: /proc/1939372/stat is gone
```

The child has no code left to run, yet it still occupies a slot in the process table;
that is what `Z` reports. `waitpid(2)` collects the exit status and the kernel finally
releases the `task_struct`. Without the `sleep`, the first read often shows `R` or `S`
instead, because the parent can reach the read before the child has been scheduled.
That race is why "is it a zombie" is answered by re-reading rather than by reading once.

Two consequences. A container whose PID 1 does not reap orphans
accumulates zombies until the process-table limit is reached; that is a container bug,
not a kernel one. And a zombie costs almost no memory but does hold a PID, which is
finite (`/proc/sys/kernel/pid_max`).

### 1.6 Signals and process control

Signals are software interrupts. Key signals:

- `SIGTERM` (15): ask the process to exit; the process can clean up.
- `SIGKILL` (9): cannot be caught or blocked; kernel destroys the task.
- `SIGSTOP` (19) / `SIGCONT` (18): stop/continue.
- `SIGHUP` (1): often means terminal closed or daemon reload.
- `SIGCHLD`: sent to parent when a child stops or exits.

Container runtimes use signals to stop containers: Kubernetes first sends
`SIGTERM` to PID 1 in the pod, waits `terminationGracePeriodSeconds`, then sends
`SIGKILL`.

Commands to try:

```bash
ps -eo pid,tid,ppid,stat,comm --sort=-%cpu | head
pstree -ap
pgrep -a python
kill -TERM 1234
kill -KILL 1234
renice -n -5 -p 1234
```

---

## 2. Memory model

### 2.1 Virtual memory

Every process has its own virtual address space described by `mm_struct` and
page tables. The CPU translates virtual addresses to physical addresses through
the page tables, with a TLB caching recent translations. This gives:

- isolation (one process cannot read another process's memory),
- lazy allocation,
- shared file pages,
- copy-on-write,
- overcommit.

Typical 64-bit user address space (not to scale):

```text
0x0000_0000_0000_0000
├── text (executable code)
├── data / BSS
├── heap (grows up via brk)
├── mmap region (shared libs, mmap files, threads, arenas)
├── stack (grows down)
└── vsyscall / vvar / ... (kernel-exported pages)
```

#### How a virtual address becomes a physical one

On a 64-bit machine the hardware uses 48 bits of an address (the upper bits are sign
extension), and those 48 bits are split into five fields: four 9-bit table indices and
a 12-bit page offset. The 12-bit offset is why a page is 4 KiB.

```text
47      39 38      30 29      21 20      12 11        0
+-----------+-----------+-----------+-----------+-----------+
| PGD   9b  | PUD   9b  | PMD   9b  | PTE   9b  | offset 12b|
+-----------+-----------+-----------+-----------+-----------+
```

Translation walks the levels in order: the PGD entry names a PUD table, the PUD entry a
PMD table, the PMD entry a PTE table, and the PTE holds the physical frame number. The
offset is copied through untranslated. That is up to four dependent memory reads per
translation, which is why the TLB exists and why a TLB miss is the expensive
event measured by tools like `perf stat -e dTLB-load-misses`.

Two numbers make the structure concrete. Nine bits per level means one PTE table
describes 512 pages, and 512 × 4 KiB is 2 MiB of address space per table. Each table is
itself exactly one page, because 512 entries × 8 bytes = 4096 bytes. Empty branches are
never allocated, so a process that touches a few megabytes never materialises the
tables for the rest, which is what makes a 128 TiB address space affordable.

The payoff is that every item in the list above is the same mechanism seen from a
different angle. Isolation, lazy allocation, shared libraries and copy-on-write are all
answers to one question: which physical frame does this entry point at, and who else's
entry points at the same frame?

### 2.2 Pages, page faults, and RSS

Memory is managed in pages (usually 4 KiB; also 2 MiB/1 GiB huge pages). When a
program calls `malloc(1 GiB)`, the kernel usually does not allocate physical
memory immediately. It records virtual address space. The first write to a page
triggers a **page fault**; the kernel allocates a physical page and maps it.

Page fault types:

- **Minor fault**: the page is already in memory (e.g. file page in page cache,
  COW page) and only needs a new PTE.
- **Major fault**: the kernel must read the page from disk/network.
- **Protection fault**: could be COW, read-only mapping, or a bug.
- **Segmentation fault**: access to a virtual address with no valid mapping.

Measurements:

- **VSZ** (virtual size): entire mapped virtual address space, including
  libraries and mappings not resident.
- **RSS** (resident set size): physical pages currently mapped to the process.
- **PSS** (proportional set size): RSS divided among processes sharing a page
  (`/proc/<pid>/smaps_rollup`).
- Page cache: file-backed pages cached by the kernel; it is normal for `free`
  to show most memory "used" by cache. The cache is reclaimed under pressure.

Commands:

```bash
cat /proc/self/status
cat /proc/self/smaps_rollup
grep -E 'VmSize|VmRSS|RssAnon|RssFile|ShmemPmdMapped' /proc/self/status
free -h
vmstat 1 5
```

#### Counting the faults yourself

The kernel keeps per-process counters, so the fault behaviour described above can be
measured rather than asserted. `getrusage(RUSAGE_SELF)` returns `ru_minflt` and
`ru_majflt`; `ps -o min_flt,maj_flt` and `/proc/<pid>/stat` fields 10 and 12 read the
same numbers. The program maps 64 MiB of anonymous memory and writes to all of it
twice.

```c
/* faults.c: the kernel counts the page faults a process takes. */
#define _GNU_SOURCE
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/resource.h>

static void delta(const char *label, struct rusage *before, struct rusage *after)
{
    printf("%-13s minor +%ld major +%ld\n", label,
           after->ru_minflt - before->ru_minflt,
           after->ru_majflt - before->ru_majflt);
}

int main(void)
{
    const size_t len = 64u * 1024 * 1024;   /* 64 MiB */
    struct rusage before, after;
    char *p;

    p = mmap(NULL, len, PROT_READ | PROT_WRITE,
             MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (p == MAP_FAILED) {
        perror("mmap");
        return 1;
    }

    getrusage(RUSAGE_SELF, &before);
    memset(p, 1, len);                      /* first touch of every page */
    getrusage(RUSAGE_SELF, &after);
    delta("first touch", &before, &after);

    getrusage(RUSAGE_SELF, &before);
    memset(p, 2, len);                      /* already resident */
    getrusage(RUSAGE_SELF, &after);
    delta("second write", &before, &after);

    printf("mapped %zu bytes = %zu pages of %d\n", len, len / 4096, 4096);
    munmap(p, len);
    return 0;
}
```

```text
$ gcc -O2 -o faults faults.c && ./faults
first touch   minor +16384 major +0
second write  minor +0 major +0
mapped 67108864 bytes = 16384 pages of 4096
```

The arithmetic checks out exactly: 64 MiB ÷ 4 KiB = 16384 pages, and the first touch
took exactly one minor fault per page. The second pass over the same range took none,
because the pages were already resident and the PTEs already existed. The count of
`major` faults is zero for anonymous memory, which is the expected result: nothing had
to be read from a backing store.

That is also the correct way to think about `mmap` of a *file*. There the first touch
is a minor fault if the page is already in the page cache and a major fault if it is
not, so the same program run against a file will move the count between the two columns
depending on cache state. That is what makes `majflt` a useful signal in production:
sustained major faults mean the working set no longer fits in RAM.

#### The same counters in Rust

```rust
//! faults.rs
use libc::{getrusage, mmap, rusage, MAP_ANONYMOUS, MAP_FAILED, MAP_PRIVATE, PROT_READ, PROT_WRITE, RUSAGE_SELF};

const LEN: usize = 64 * 1024 * 1024; // 64 MiB

fn usage() -> rusage {
    let mut u: rusage = unsafe { std::mem::zeroed() };
    // SAFETY: RUSAGE_SELF writes a rusage into a valid stack slot.
    unsafe { getrusage(RUSAGE_SELF, &mut u) };
    u
}

fn main() {
    // SAFETY: an anonymous private mapping; the result is checked below.
    let base = unsafe {
        mmap(
            std::ptr::null_mut(),
            LEN,
            PROT_READ | PROT_WRITE,
            MAP_PRIVATE | MAP_ANONYMOUS,
            -1,
            0,
        )
    };
    if base == MAP_FAILED {
        eprintln!("mmap failed");
        std::process::exit(1);
    }

    let before = usage();
    // SAFETY: the mapping is LEN bytes and writable.
    unsafe { std::ptr::write_bytes(base as *mut u8, 1, LEN) };
    let after = usage();
    println!(
        "first touch : minor +{} major +{}",
        after.ru_minflt - before.ru_minflt,
        after.ru_majflt - before.ru_majflt
    );

    let before = usage();
    // SAFETY: same mapping, already resident.
    unsafe { std::ptr::write_bytes(base as *mut u8, 2, LEN) };
    let after = usage();
    println!(
        "second write: minor +{} major +{}",
        after.ru_minflt - before.ru_minflt,
        after.ru_majflt - before.ru_majflt
    );
    println!("bytes: {} = {} pages", LEN, LEN / 4096);
}
```

```text
$ cargo run --release --bin faults
first touch : minor +16384 major +0
second write: minor +0 major +0
bytes: 67108864 = 16384 pages
```

That program never asks the allocator for memory. `mmap` is the syscall underneath
`malloc`, and going straight to it removes the allocator from the measurement.
Reasoning about a heap problem requires `malloc` in the picture; reasoning about the
kernel's accounting does not.

### 2.3 `malloc`, `brk`, and `mmap`

Glibc `malloc` manages heap **arenas**. Small allocations come from arenas that
grow with `brk`/`mmap`; large allocations use `mmap` directly and are unmapped
on `free`. Because memory is virtual until touched, allocating a huge buffer is
cheap, but touching all of it can cause the OOM killer to act if cgroup/host
limits are exceeded.

Consequences for cloud services:

- Allocate memory lazily or via explicit pools if latency spikes matter.
- Watch `RssAnon` (anonymous memory) for actual process memory.
- A memory leak in one container may not be visible in `top` RSS immediately if
  the pages are never touched again.

#### Where the bytes come from

`brk` and `mmap` are two different places to obtain memory, and glibc chooses between
them. Its threshold, `M_MMAP_THRESHOLD`, is 128 KiB by default: a larger request is
served by `mmap` and released on `free`, a smaller one comes from the heap that `brk`
extends. The program below prints the program break and the number of mappings in
`/proc/self/maps` around one small and one large allocation.

```c
/* heap.c: glibc grows the brk area for small blocks and calls mmap for large ones. */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

static int mappings(void)
{
    FILE *f = fopen("/proc/self/maps", "r");
    int lines = 0;
    char buf[512];

    if (f == NULL)
        return -1;
    while (fgets(buf, sizeof buf, f) != NULL)
        lines++;
    fclose(f);
    return lines;
}

int main(void)
{
    void *small;
    void *large;

    printf("start    brk=%p mappings=%d\n", sbrk(0), mappings());

    small = malloc(64 * 1024);
    printf("64 KiB   %p brk=%p mappings=%d\n", small, sbrk(0), mappings());

    large = malloc(8 * 1024 * 1024);
    printf("8 MiB    %p brk=%p mappings=%d\n", large, sbrk(0), mappings());

    free(large);
    free(small);
    printf("freed    brk=%p mappings=%d\n", sbrk(0), mappings());
    return 0;
}
```

```text
$ gcc -O2 -o heap heap.c && ./heap
start    brk=0xaaaaef254000 mappings=16
64 KiB   0xaaaaef2558a0 brk=0xaaaaef275000 mappings=16
8 MiB    0xffff8143f010 brk=0xaaaaef275000 mappings=17
freed    brk=0xaaaaef275000 mappings=16
```

Three things are visible in that output. The 64 KiB block came from the heap: `brk`
moved, and the mapping count did not change. The 8 MiB block did the opposite: `brk` is
identical before and after, the mapping count went from 16 to 17, and the address sits
far away in the high part of the address space, which is where `mmap` places mappings.
After `free`, the large mapping is gone but `brk` has not moved, because glibc keeps the
heap it has already grown in order to reuse it.

That last point is the one that matters in production. A process that repeatedly
allocates and frees large buffers holds a stable mapping count rather than returning
memory between calls. A process that allocates many small objects keeps both the pages
and the `brk` address for its lifetime. Neither is a leak in the "lost pointer" sense,
and neither shows up as growing `RSS` unless the memory was actually touched. It is also
why "`RSS` is flat but the container was OOM-killed" is normally a cgroup limit set
below the peak *touched* set rather than a leak.

### 2.4 Overcommit and OOM killer

The Linux kernel can allow `malloc` to succeed even when there is not enough
physical RAM (mode `0` heuristic overcommit, `1` always overcommit, `2` never
overcommit). When memory runs out, the kernel invokes the OOM killer, which
scores processes and kills one to free memory.

In containers, memory limits are enforced by **cgroup v2**. When a cgroup
exceeds `memory.max`, the kernel reclaims pages inside that cgroup, then invokes
the cgroup OOM killer for that cgroup. A container does not necessarily take
down the whole node. `dmesg` shows messages like
`Memory cgroup out of memory: Killed process ...`.

#### Why Linux overcommits

Overcommit is where the kernel's model and the textbook model diverge. A textbook
allocator refuses when the resource is exhausted. Linux hands out address space it may
not be able to back, for two reasons: a `fork`-heavy workload would fail constantly if
every child had to be fully fundable, and most programs reserve far more than they
touch. The mode is selected by `vm.overcommit_memory` (`0` heuristic, `1` always, `2`
never), and the default is the heuristic.

The consequence is that a non-NULL return from `malloc` is not a promise. The failure
arrives later, as an OOM kill, and the process chosen to die is selected by `oom_score`
rather than by whoever requested the memory. That is why production systems set a
`memory.max` on the cgroup: it confines the kill to the container that overspent instead
of letting the heuristic choose among every process on the node.

Linus Torvalds, on why the deployed behaviour wins even when the theory is cleaner
(*The Linux Edge*, in *Open Sources*, O'Reilly, 1999):

> Theory and practice sometimes clash. Theory loses. Every single time.

The model and the deviation both matter. Overcommit, `oom_score`, and the gap between
`VmSize` and `VmRSS` follow from the design above.

### 2.5 Huge pages and NUMA

- **Huge pages** reduce TLB misses and page-table overhead for large memory
  regions (important for some HPC/database workloads). Kubernetes supports
  `hugepages-2Mi`/`hugepages-1Gi` as resources.
- **NUMA** means memory attached to one CPU socket is faster for CPUs on that
  socket. GPU servers are strongly NUMA: PCIe/NVLink topology and GPU memory
  locality affect data transfer. `numactl --hardware` shows nodes and distances.

GPU-related memory points:

- CUDA pinned (page-locked) host memory allows DMA without bounce buffers; it
  is deliberately non-swappable.
- GPUs have their own HBM memory; `nvidia-smi` shows used/free memory, but that
  is not host RSS.
- GPUDirect Storage can DMA from storage to GPU memory,
  bypassing host memory.

---

## 3. Namespaces, cgroups, and containers

### 3.1 What a namespace isolates

Namespaces give processes a different view of system resources. `clone()` and
`unshare()` accept namespace flags; `setns()` joins an existing namespace. A
container is, at minimum, a set of processes in new namespaces plus cgroup
limits.

| Namespace | Flag | Isolates |
|---|---|---|
| Mount | `CLONE_NEWNS` | Mount points and filesystem view |
| PID | `CLONE_NEWPID` | Process IDs; PID 1 inside is not host PID 1 |
| Network | `CLONE_NEWNET` | Network interfaces, routes, firewall, sockets |
| UTS | `CLONE_NEWUTS` | Hostname and NIS domain |
| IPC | `CLONE_NEWIPC` | System V IPC and POSIX message queues |
| User | `CLONE_NEWUSER` | User and group IDs (unprivileged namespaces) |
| Cgroup | `CLONE_NEWCGROUP` | View of cgroup hierarchy root |
| Time | `CLONE_NEWTIME` | Clock offsets |

PID namespace nuance: a process inside a new PID namespace sees itself as PID 1,
but the host sees it with another PID. `ps` inside a container only shows
processes in that PID namespace by default.

#### A namespace is a pointer, not a copy

The mechanism is smaller than the vocabulary suggests. The kernel keeps one namespace
object per type (a `struct uts_namespace`, a `struct pid_namespace`, and so on) and each
task holds a pointer to one of them. Every system call that resolves a name, whether
`gethostname`, `kill`, `mount` or `socket`, resolves it through the namespace the calling
task points at. Creating a namespace allocates a fresh object and repoints one task.
Nothing is copied, and nothing is isolated behind a hypervisor boundary. That is why a
container starts in milliseconds, and also why a kernel bug reachable through a
namespace is a host bug rather than a guest bug.

UTS is the smallest namespace to demonstrate, because it holds a single field. The
program below asks for its own copy of that field.

```c
/* ns.c: the UTS namespace holds the hostname, so a process can have its own. */
#define _GNU_SOURCE
#include <errno.h>
#include <sched.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int main(void)
{
    char before[256];
    char after[256];

    if (gethostname(before, sizeof before) != 0) {
        perror("gethostname");
        return 1;
    }

    if (unshare(CLONE_NEWUTS) != 0) {
        printf("unshare(CLONE_NEWUTS) = -1 errno=%d (%s)\n", errno, strerror(errno));
        printf("this needs CAP_SYS_ADMIN, so try:\n");
        printf("  unshare --user --map-root-user --uts ./ns\n");
        return 1;
    }

    if (sethostname("in-a-namespace", 14) != 0) {
        perror("sethostname");
        return 1;
    }
    gethostname(after, sizeof after);

    printf("hostname before: %s\n", before);
    printf("hostname after : %s\n", after);
    return 0;
}
```

Run as an ordinary user it fails:

```text
$ gcc -O2 -o ns ns.c && ./ns
unshare(CLONE_NEWUTS) = -1 errno=1 (Operation not permitted)
this needs CAP_SYS_ADMIN, so try:
  unshare --user --map-root-user --uts ./ns
```

Creating a namespace is privileged, because namespaces are what confinement is built
from. The route available to an unprivileged user is the user namespace: it can be
created without privilege, and inside it the user's uid is mapped to root, which
grants the capability needed to create the rest.

```text
$ unshare --user --map-root-user --uts ./ns
hostname before: yahboom
hostname after : in-a-namespace
```

That pair of results explains how `docker run` works for an ordinary user, and why
rootless containers exist. The runtime does not perform a privileged operation on
the user's behalf; the user namespace grants the privileges it needs inside a scope
it cannot escape.

### 3.2 cgroups v2: accounting and limiting

cgroup v2 (`/sys/fs/cgroup`) organizes processes into a tree. Key controllers:

- `cpu.max`: `$MAX_PERIOD $PERIOD`, e.g. `50000 100000` = 50% of one CPU.
- `memory.max`: hard memory limit; `memory.current`, `memory.events` show
  pressure/oom counts.
- `memory.high`: throttle above threshold before hard limit.
- `io.max`: I/O bandwidth/IOPS limits.
- `pids.max`: max tasks/threads.
- `cpuset.cpus` / `cpuset.mems`: CPU/memory affinity.
- `misc.max`: miscellaneous resources charged through the misc controller.

cgroup v2 rules:

- The no-internal-processes rule: a cgroup that has child cgroups cannot also hold
  processes. `cgroup.subtree_control` delegates a controller to the children.
- The kernel charges a process to the cgroup that contains it; when a process
  forks, the child stays in the parent's cgroup unless moved.
- `memory.events` contains `oom_kill`, `max`, `high` counters.

Commands:

```bash
cat /proc/self/cgroup
cat /sys/fs/cgroup/memory.max
cat /sys/fs/cgroup/memory.current
cat /sys/fs/cgroup/memory.events
cat /sys/fs/cgroup/cpu.max
cat /sys/fs/cgroup/pids.max
systemd-cgls
```

### 3.3 From container image to running container

When Kubernetes schedules a Pod, the kubelet asks the CRI runtime (containerd)
to start a sandbox (pause container) and then containers. High-level flow:

1. `containerd` receives the CRI request.
2. It creates an OCI bundle from the image: rootfs from image layers, config
   with mounts, env, command, namespaces, cgroup path, devices.
3. `containerd` invokes `runc` (or another OCI runtime) via `runc create`.
4. `runc` creates the namespaces with `clone()`/`unshare()`, sets cgroup
   membership, applies mounts and `pivot_root` into the container rootfs.
5. `runc` starts the container process via `exec`.
6. The process runs with a restricted view; PID 1 inside the container is
   normally the application or a tiny init process.

The pause/sandbox container holds the network namespace and other shared
infrastructure so the app containers in a Pod can share localhost and volumes.

### 3.4 Container runtime specifics

A container by default has no access to `/dev/nvidia*` and no CUDA driver
user-space libraries. The GPU
Operator and container toolkit automate it. At a low level,
`nvidia-container-cli` performs:

1. Detect the host driver version and CUDA compatibility.
2. Mount the driver's user-space libraries (`libcuda.so`, `libnvidia-ml.so`,
   etc.) into the container.
3. Create/bind-mount the GPU device nodes (`/dev/nvidia0`, `/dev/nvidiactl`,
   `/dev/nvidia-uvm`, `/dev/nvidia-modeset`, MIG devices) into the container.
4. Set environment variables (`NVIDIA_VISIBLE_DEVICES`, `NVIDIA_DRIVER_CAPABILITIES`).
5. For MIG, expose the requested compute instance device node.

The container still runs on the host kernel; the driver's kernel module lives
on the host. The container gets the same kernel driver plus user-space libraries
that match it. This is why the driver version inside containers and the CUDA
version must be compatible.

The device plugin, not the runtime, decides which GPUs are assigned. The kubelet
calls the plugin's `Allocate` RPC after scheduling; the plugin returns device
IDs and environment variables; the runtime uses them to inject devices.

---

## 4. Filesystem and I/O

### 4.1 VFS and core objects

The Linux VFS abstracts filesystems. Core objects:

- `super_block`: represents a mounted filesystem.
- `inode`: metadata for a file (owner, mode, size, block pointers).
- `dentry`: directory entry mapping a name to an inode; cached by VFS.
- `file`: open file description with current offset, flags, and methods.

`stat` reads inode metadata; `df` reports filesystem usage; `lsof` shows open
files.

#### What those four objects are

They nest. A `super_block` owns a set of `inode`s. An `inode` has no name. A `dentry` is
what gives an inode a name inside a directory. A `file` is a per-open-descriptor view
with its own offset. That structure explains three things that otherwise look like
trivia: two processes can hold the same file open at different offsets (two `file`
objects, one `inode`), renaming a file does not change the inode it refers to (the name
moved, the inode did not), and a hard link is a second `dentry` pointing at the same
`inode`, which is why hard links cannot cross filesystems.

At the syscall boundary this becomes an error convention: failure is `-1` with `errno`
set, and `errno` is thread-local, which is what makes it usable from a threaded program.

```c
/* errno.c: the syscall boundary reports failure with -1 plus errno. */
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

static void try_open(const char *path)
{
    char buf[64];
    ssize_t n;
    int fd = open(path, O_RDONLY);

    if (fd < 0) {
        printf("open(\"%s\") = -1 errno=%d (%s)\n", path, errno, strerror(errno));
        return;
    }
    printf("open(\"%s\") = %d\n", path, fd);

    n = read(fd, buf, sizeof buf - 1);      /* may return fewer bytes than asked */
    if (n > 0) {
        buf[n] = '\0';
        if (buf[n - 1] == '\n')
            buf[n - 1] = '\0';
        printf("  read() returned %zd byte(s): \"%s\"\n", n, buf);
    }
    close(fd);
}

int main(void)
{
    try_open("/definitely/not/here");
    try_open("/etc/hostname");
    try_open("/etc/shadow");                /* exists, but not readable by this uid */
    return 0;
}
```

```text
$ gcc -O2 -o errno errno.c && ./errno
open("/definitely/not/here") = -1 errno=2 (No such file or directory)
open("/etc/hostname") = 3
  read() returned 8 byte(s): "yahboom"
open("/etc/shadow") = -1 errno=13 (Permission denied)
```

Three distinct failures appear in those four lines. `ENOENT` (2) and `EACCES` (13) are
different conditions that a caller must be able to distinguish, which is the reason `errno`
exists instead of a single "it failed" return. The descriptor is 3 rather than 1 because
0, 1 and 2 are already stdin, stdout and stderr: the descriptor table is a small integer
namespace per process, and exhausting it is a failure mode (`EMFILE`) in servers.
And `read` returned 8 bytes; it is permitted to return fewer bytes than requested at any
time, so a correct reader loops. Treating a short read as an error, or as end-of-file, is
one of the most common bugs in systems code.

### 4.2 Filesystems relevant to Kubernetes

- **ext4/xfs**: local disk filesystems.
- **tmpfs**: RAM-backed, used for emptyDir with `medium: Memory` and `/dev/shm`.
- **overlayfs**: combines lower image layers and an upper writable layer; used
  by containerd/Docker for image rootfs.
- **FUSE**: user-space filesystems (e.g. some CSI drivers, gcsfuse).
- **Network filesystems**: NFS, and cloud CSI volumes (EBS/EFS/PVC).

Overlayfs copy-up: when a container modifies a file that exists in a lower
image layer, the kernel copies it to the upper layer before the write. Deleting
a lower file creates a whiteout in the upper layer. This is why writing to a
large lower-layer file inside a container can be expensive on first touch.

### 4.3 Mount propagation

Mounts can propagate between mount namespaces (`shared`, `slave`, `private`,
`unbindable`). Kubernetes uses this for hostPath volumes and for the container
runtime to inject devices/libraries. `mount --make-rshared /` is common on nodes
so that mounts created in containers are visible where needed. Misconfigured
propagation causes "device or resource busy" and invisible mounts.

Commands:

```bash
mount | grep -E 'overlay|nvidia|/var/lib/kubelet'
cat /proc/self/mountinfo
findmnt -R /var/lib/kubelet | head -50
```

### 4.4 I/O stack and pressure

I/O path: process syscall → VFS → filesystem → block layer → device driver.
Page cache absorbs reads/writes; dirty pages are written back later by per-device
writeback threads. Storage performance:

- `iostat -x 1` shows `%util`, await, svctm.
- `pidstat -d 1` shows per-process I/O.
- `/proc/pressure/io`, `/proc/pressure/memory`, `/proc/pressure/cpu` expose PSI
  (Pressure Stall Information), which is more meaningful than raw utilization.
- `iotop` shows per-process I/O in real time.

---

## 5. Networking deep dive

### 5.1 Sockets and TCP

A socket is an endpoint identified by IP:port. `socket()` creates it,
`bind()` assigns an address, `listen()` marks it passive, `accept()` returns a
new connected socket, and `connect()` initiates an outbound connection. `ss`
is the modern way to inspect sockets:

```bash
ss -tulpn
ss -tan state established
ss -tnp | grep :443
```

TCP state machine for server-side connections:
`LISTEN → SYN_RECV → ESTABLISHED → FIN_WAIT/CLOSE_WAIT → ...`.

TCP details:

- `CLOSE_WAIT` sockets mean the remote side closed but the local application has
  not closed its socket; a leak usually indicates the app forgot to close.
- `TIME_WAIT` is normal after active close; it allows delayed packets to die.
  Large TIME_WAIT counts are not automatically a problem unless sockets or
  ephemeral ports are exhausted.
- `somaxconn`/backlog limits how many pending connections the kernel queues.

### 5.2 Packet path through a Linux host

Application → socket buffer → TCP/IP stack → routing → netfilter
(`iptables`/`nftables`) → neighbor/ARP → NIC driver → wire.

For incoming packets, the NIC DMA's into ring buffers, raises an interrupt (or
NAPI polls), the kernel parses headers, runs netfilter/prerouting, forwards or
delivers to a socket.

### 5.3 Netfilter, conntrack, iptables/nftables

Netfilter hooks are points in the kernel where packet filtering/NAT happens.
`iptables` manages tables (`filter`, `nat`, `mangle`, `raw`) and chains.
`conntrack` tracks connection state so `-m conntrack --ctstate ESTABLISHED,RELATED`
works.

In Kubernetes:

- Services can use iptables (kube-proxy): DNAT to a selected Pod IP.
- `ClusterIP` traffic is NATed; replies are un-NATed via conntrack.
- NetworkPolicy is often implemented by Calico/Cilium in iptables/eBPF.
- Cilium can bypass iptables and use eBPF for service load balancing and policy.

Commands:

```bash
iptables -L -n -v
iptables -t nat -L -n -v
conntrack -L | head
nft list ruleset | head
```

### 5.4 Network namespaces, veth, bridges, CNI

Each Kubernetes Pod usually has its own network namespace. The CNI plugin:

1. Creates a veth pair.
2. Puts one end in the Pod's network namespace.
3. Attaches the other end to a bridge/OVS or a virtual routing/encap device.
4. Assigns an IP address (usually from the node's pod CIDR).
5. Adds routes and maybe policy.
6. Reports the interface/IP to the kubelet.

The layout:

```text
Pod netns                    Host netns
┌─────────────┐ veth         ┌─────────────────────────┐
│ eth0        ├─────────────►│ vethXXX ──► cni0/bridge │
│ 10.244.1.5  │              │           │             │
└─────────────┘              │         eth0            │
                             └─────────────────────────┘
```

`localhost` inside a pod is the pod network namespace only, not the node.

### 5.5 DNS

Pods use CoreDNS (or another DNS service). DNS resolution inside a pod first
consults `/etc/resolv.conf`, which points to the cluster DNS. Search domains
allow short service names. Common problem: pod DNS works but host networking
does not use the cluster DNS, or `ndots:5` causes extra DNS queries for every
name.

---

## 6. Debugging a sick Linux node

### 6.1 Systematic triage order

The order is layered, from the node down to the GPU:

1. **Node availability**: `kubectl get node`, `kubectl describe node`.
2. **Load/resource basics**: `uptime`, `free -h`, `df -h`, `top`.
3. **Kernel/device messages**: `dmesg -T | tail`.
4. **Runtime**: `crictl ps -a`, `journalctl -u containerd`.
5. **Kubelet**: `journalctl -u kubelet`, `/var/lib/kubelet`.
6. **Application logs**: `kubectl logs`, `kubectl describe pod`.
7. **GPU-specific**: `nvidia-smi`, device plugin logs, allocatable resources,
   Xid errors, ECC errors.

### 6.2 Scenario: Pods stuck in `Pending`

Pending means the scheduler has not placed the Pod. Common causes:

- No node has enough CPU/memory/GPU.
- No node matches `nodeSelector`, affinity, or tolerations.
- `nvidia.com/gpu` is not in node allocatable.
- ResourceQuota/LimitRange in namespace blocks admission.
- PVC is unbound, causing scheduling failure after node filtering.
- The node is tainted `NoSchedule` and the pod lacks toleration.
- The scheduler itself is down or unschedulable.

Commands that reveal the reason:

```bash
kubectl describe pod <pod>
kubectl get nodes -o wide
kubectl describe node <node>
kubectl get events -A --sort-by=.lastTimestamp
kubectl get pvc
```

### 6.3 Scenario: Pod scheduled but `ContainerCreating`

The kubelet is involved at this stage:

- Image pull errors: `kubectl describe pod`.
- Storage mount failures: events, `journalctl -u kubelet`.
- Runtime start failures: `crictl ps -a`, `journalctl -u containerd`.
- Device plugin allocation failure: `kubectl describe pod` may show
  `Failed to create pod sandbox` or `Allocate failed`.

### 6.4 Scenario: Pod `CrashLoopBackOff`

- `kubectl logs <pod> --previous` shows the crash reason from the previous
  container.
- Exit code 137 is SIGKILL (often OOM or a liveness kill); 143 is SIGTERM.
- If exit code 137 with OOMKilled in status, inspect memory limit and
  `memory.events`.
- If liveness probe fails, `kubectl describe pod` shows probe failures.

### 6.5 Scenario: GPU node cannot allocate GPUs

The order of checks:

1. **Driver visible on host?**
   ```bash
   nvidia-smi
   ```
   If not, driver module not loaded or node needs reboot after driver install.

2. **Device plugin running?**
   ```bash
   kubectl get pods -n gpu-operator -l app=nvidia-device-plugin-daemonset
   kubectl logs -n gpu-operator -l app=nvidia-device-plugin-daemonset
   ```

3. **Node resource advertised?**
   ```bash
   kubectl describe node | grep -A5 'nvidia.com/gpu'
   ```
   If `Allocatable` is missing, plugin registration did not complete.

4. **Pod request matches allocatable?** `nvidia.com/gpu` is an extended
   resource: it must be in `limits`, and Kubernetes requires `limits == requests`
   for extended resources.

5. **Runtime injection works?**
   ```bash
   kubectl exec <pod> -- nvidia-smi
   ```
   If the binary is missing, the container toolkit/GPU Operator did not
   install runtime hooking correctly.

6. **Hardware/kernel errors?**
   ```bash
   dmesg | grep -i xid
   dmesg | grep -i nvidia
   nvidia-smi -q -d ECC
   nvidia-smi -q -d PAGE_RETIREMENT
   nvidia-smi --query-gpu=timestamp,name,pci.bus_id,utilization.gpu,memory.used,temperature.gpu,power.draw --format=csv
   ```

Xid errors are GPU error messages emitted by the driver; different Xid numbers
have different meanings. The presence of Xid errors plus ECC errors is a strong
signal of a hardware or driver fault, not a Kubernetes configuration problem.

### 6.6 Scenario: high CPU but no obvious process

Commands:

```bash
top -b -n1 -H | head -20
pidstat 1
perf top
cat /proc/loadavg
ps -eo pid,stat,wchan:30,comm
```

`wchan` shows the kernel function a task is blocked in. A process in
`R` with high CPU may be spinning; sample with `perf top` or capture a
stack:

```bash
perf record -F 99 -g -p <pid> -- sleep 10
perf report
```

---

## 7. Performance tools and observability

| Layer | Tool | What to look for |
|---|---|---|
| CPU | `top`, `pidstat -u`, `perf top` | %usr vs %sys, context switches, runnable threads |
| CPU scheduler | `/proc/pressure/cpu`, `cat /sys/fs/cgroup/cpu.stat` | runnable pressure, throttling |
| Memory | `free`, `/proc/pressure/memory`, `valgrind massif` | PSI, anon vs file, swap, OOM events |
| Disk | `iostat -x`, `pidstat -d`, `/proc/pressure/io` | await, %util, per-process IO |
| Network | `sar -n DEV`, `ss`, `tcpdump`, `ethtool -S` | drops, retransmits, queue full |
| Syscalls | `strace -f -tt`, `ltrace` | blocked calls, EAGAIN loops |
| Tracing | `perf trace`, `bpftrace`, `ftrace` | kernel-level explanations |
| Containers | `crictl stats`, `systemd-cgtop` | per-pod/per-container usage |

### ftrace/bpftrace examples

```bash
# Trace process creation
bpftrace -e 'tracepoint:sched:sched_process_exec { printf("%s %s\n", comm, args->filename); }'

# Trace openat syscalls
bpftrace -e 'tracepoint:syscalls:sys_enter_openat { printf("%s %s\n", comm, str(args->filename)); }'

# Show cgroup OOM events
grep oom_kill /sys/fs/cgroup/memory.events
```

### When to use `perf`

- High CPU with unknown owner: `perf top`.
- Looking for lock contention: `perf lock`.
- Hardware counters: `perf stat`.
- Flame graphs from `perf record` output.

---

## 8. Container/VM differences in one picture

| Aspect | Container | VM |
|---|---|---|
| Isolation boundary | kernel namespaces/cgroups/seccomp | hardware virtualisation (KVM) |
| Kernel | shared host kernel | separate guest kernel |
| Boot time | milliseconds (process start) | seconds (kernel boot) |
| Device access | mediated by runtime/device cgroup | virtual devices/passthrough |
| Attack surface | syscalls filtered by seccomp/apparmor | full kernel interface |
| GPU options | device plugin + container runtime | vGPU, MIG, PCIe passthrough |

GPU cloud products span both models: Kubernetes pods with device
plugins/MIG for container workloads, and GPU instances/VMs for customers who
need full control.

---

## 9. Questions with answer sketches

### `docker run`, step by step

1. Docker client talks to dockerd/containerd.
2. Image is pulled and unpacked into an OCI rootfs (overlayfs).
3. Runtime creates namespaces/cgroup, prepares mounts/devices.
4. `runc` starts the process as PID 1 in the new namespaces.
5. The process has a restricted view of processes, network, mounts, and
   resources.

### How a cgroup memory limit kills a container

The kernel charges anonymous and page-cache pages to the cgroup. When
`memory.current` exceeds `memory.max`, the kernel reclaims, and if it cannot
bring usage below the limit it performs a cgroup OOM kill. The container exits,
often with code 137. `kubectl describe pod` shows `OOMKilled`.

### Shared kernel, separate PID namespace

It shares the host kernel (so `uname` matches), but it is in a new PID namespace,
so `ps` only sees PIDs inside that namespace. Without a PID namespace, it could
see host processes; Kubernetes normally isolates PID namespaces for pods.

### Why `free` reports little free memory

Linux uses free RAM for page cache and reclaims it on demand. "Free" memory is
not a useful health metric; check available memory, PSI, and cgroup usage
instead.

### Containers and VMs

Containers are processes with kernel-enforced isolation; VMs run separate
kernels on virtual hardware. Containers share the host kernel and are lighter;
VMs provide stronger isolation and can run different OS kernels.

### Zombies and reaping

A zombie is an exited task whose parent has not called `wait()`. `init`/PID 1
adopts orphaned children and reaps them. A container with a broken init process
can leak zombies inside its PID namespace.

### Debugging a GPU node that cannot allocate GPUs

The order: host `nvidia-smi`, driver module, device plugin pods and logs,
`nvidia.com/gpu` allocatable on the node, Pod resource limits, container runtime
toolkit/GPU Operator state, then Xid/ECC hardware errors.

### The page cache

The page cache caches file contents in RAM. Reads hit it and avoid disk; writes
are buffered in it and written back later. Dropping it is rarely a performance
fix; it discards useful cache, and the read costs are paid again.

### conntrack

Conntrack tracks connection state for NAT/firewall. kube-proxy's iptables mode
uses it to reverse DNAT replies. If conntrack table fills, new connections fail
or are dropped; monitor `nf_conntrack_count` vs `nf_conntrack_max`.
