# 02: Linux Concepts: A Deep Dive

Understanding Linux systems in the context of container orchestration requires examining node-level operations, such as Pod scheduling, device visibility, and node troubleshooting. These behaviors are governed by kernel objects, system calls, data structures, and command-line utilities detailed in this chapter.

## How to read this chapter

Each mechanism is presented in four steps:

1. **The Problem:** The issue that arises without the mechanism.
2. **The Mechanism:** The kernel data structure or algorithm that resolves the issue.
3. **Implementation:** A concise C program demonstrating the concept, occasionally accompanied by a Rust equivalent using the `libc` crate.
4. **Output:** The program's output alongside corresponding external command outputs.

All code listings were compiled and executed on an NVIDIA Jetson (aarch64, Linux 5.15) using gcc 11.4.0 and rustc 1.96 nightly. The outputs provided are exact reproductions. Note that on aarch64, the system call instruction is `svc` (rather than `syscall`), and memory addresses are 48-bit. While specific numerical values differ on x86-64 architectures, the underlying mechanisms remain identical.

```bash
gcc -O2 -Wall -Wextra -o fork_cow fork_cow.c   # the C programs
cargo run --release --bin syscall_cost         # the Rust ones, libc is already a dependency
```

## Further reading

The following texts provide comprehensive background and serve as the foundational references for the concepts discussed in this chapter.

| Source | Utility |
|---|---|
| Arpaci-Dusseau, *Operating Systems: Three Easy Pieces* (free at `ostep.org`) | Provides a clear introduction to virtual memory, scheduling, and concurrency. Recommended as an initial resource for foundational terminology. |
| Bryant & O'Hallaron, *Computer Systems: A Programmer's Perspective* | Connects C code to machine code and the memory hierarchy. Chapters 8 and 9 detail the mechanics of page faults. |
| Tanenbaum & Bos, *Modern Operating Systems* | A canonical survey that compares Linux with other kernel architectures. |
| Silberschatz, Galvin & Gagne, *Operating System Concepts* | Standard academic textbook. Useful for precise definitions of concepts such as working set, thrashing, and demand paging. |
| Kerrisk, *The Linux Programming Interface* | Serves as an exhaustive reference for the system call boundary, detailing calls, errors, and edge cases. Best utilized as a reference dictionary. |
| Stevens & Rago, *Advanced Programming in the UNIX Environment* | A foundational text on signals, process control, and I/O idioms. |
| Love, *Linux Kernel Development* | An overview of the kernel's internal data structures, authored by a former scheduler maintainer. |
| Bovet & Cesati, *Understanding the Linux Kernel* | Provides deep technical insights into page-table and VFS internals. |
| Corbet, Rubini & Kroah-Hartman, *Linux Device Drivers* | Details how drivers interface with the kernel, which is relevant for GPU driver integration. |
| Drepper, "What Every Programmer Should Know About Memory" (2007) | A comprehensive, freely available account of caches, TLBs, and NUMA architectures. |
| Ritchie & Thompson, "The UNIX Time-Sharing System" (CACM, 1974) | The foundational paper explaining the design of UNIX process and file abstractions. |
| Saltzer & Kaashoek, *Principles of Computer System Design* | Covers naming, layering, and fault containment, explaining the architectural rationale behind system abstractions. |

The quotations from Linus Torvalds included below are historical, attributed, and dated. They are provided to illustrate the design philosophies that inform the surrounding technical sections.

---

## 1. Process and thread model

### 1.1 The kernel's unit of execution is a task

On Linux, both processes and threads are represented by the same kernel structure: `task_struct`. What is conventionally referred to as a process is typically a **thread group**: one or more tasks sharing the same Thread Group ID (`TGID`). In user space:

- `getpid()` returns the TGID of the calling task (the "process ID").
- `gettid()` returns the kernel task ID (`PID` in `/proc/<pid>/status`, representing `Tgid` vs `Pid`).
- `ps -Lf` and `top -H` display individual tasks and threads.

In `ps -eo pid,tid,ppid,comm`, the `pid` column represents the process ID and `tid` represents the thread ID. For a single-threaded process, these values are identical.

Utilizing a unified structure extends beyond convenience. Maintaining separate process and thread tables would require every scheduling decision, signal delivery, and credential check to first determine the appropriate table context. By utilizing a single `task_struct` with a `tgid` field, a "thread" is defined as a relationship between tasks rather than a distinct object type. This design allows `kill(2)` to address either a specific thread or an entire thread group depending on the ID format, and explains why `/proc/<tgid>/task/<tid>` exists as a directory rather than a separate filesystem.

Regarding the importance of data structures over code implementation, Linus Torvalds noted (git mailing list, 27 July 2006):

> I will, in fact, claim that the difference between a bad programmer and a good one is whether he considers his code or his data structures more important. Bad programmers worry about the code. Good programmers worry about data structures and their relationships.

The scheduler, signal handling, cgroup accounting, and the `/proc` filesystem are all views onto this single object. Consequently, analyzing process behavior generally involves determining which field of the `task_struct` was modified and by which subsystem.

### 1.2 `fork()`, `vfork()`, and `clone()`

- `fork()` creates a child task by duplicating the parent's address space, file-descriptor table, signal handlers, and most other process state. The duplication is virtualized through **copy-on-write (COW)**: both parent and child initially reference the same physical pages, which are marked read-only. When either process attempts a write, the kernel duplicates the specific page. This mechanism makes `fork()` highly efficient for small processes and dictates that memory usage (`PSS`) should not be calculated simply as `RSS(parent) + RSS(child)`.
- `vfork()` originally suspended the parent until the child called `exec()` or `exit()`. It is rarely required in modern systems because COW already renders `fork()` highly efficient.
- `clone()` is the low-level system call utilized by pthreads and container runtimes. Flags dictate which resources are shared with the child. `clone(CLONE_THREAD)` creates a thread, while `clone(CLONE_NEWPID|CLONE_NEWNS|...)` creates a process within new namespaces, which is the mechanism `runc` uses to initialize a container.

**In the Linux kernel, threads are implemented as processes that share an address space, file descriptors, and signal handlers, rather than as a distinct kernel abstraction.**

#### Copy-on-write mechanics

`fork()` performs no physical memory copying at the moment of the call. It marks the parent's writable pages as read-only in *both* page tables. The first process to attempt a write triggers a protection fault, prompting the kernel to duplicate that specific page and provide a writable mapping. The following program demonstrates this: the parent and child print the *same* virtual address holding *different* values. This is possible because the printed address is virtual, while the underlying physical frame was duplicated upon the first write.

```c
/* fork_cow.c: the child receives a private copy of the parent's memory. */
#include <stdio.h>
#include <sys/wait.h>
#include <unistd.h>

int main(void)
{
    int value = 42;                     /* located on the parent's stack */
    pid_t pid = fork();

    if (pid < 0) {
        perror("fork");
        return 1;
    }

    if (pid == 0) {
        value = 99;                     /* writes to the private copy */
        printf("child : pid=%d value=%d address=%p\n",
               (int)getpid(), value, (void *)&value);
        fflush(stdout);                 /* flush before _exit, otherwise output is lost */
        _exit(0);                       /* exit() would also flush and run atexit handlers */
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

Two processes share one virtual address but hold two distinct values. Examining `cat /proc/<pid>/smaps` reveals the copied page as a dirty anonymous page charged to each process independently, which is precisely what `PSS` accounts for and `RSS` does not.

**A critical detail in this listing is the `fflush` call.** Standard output directed to a pipe is block-buffered, and `_exit(2)` bypasses the standard I/O flush. Consequently, a program that prints in the child process and subsequently calls `_exit` will lose the buffered output without generating an error:

```c
/* lost.c: the child's output is lost due to missing flush. */
#include <stdio.h>
#include <unistd.h>

int main(void)
{
    printf("child\n");   /* remains in the buffer */
    _exit(0);            /* does not flush the buffer */
}
```

```text
$ gcc -O2 -o lost lost.c && echo "captured: [$(./lost)]"
captured: []
```

This relates to a common class of bugs involving stdio buffer locks during a fork: because the buffer was duplicated by the fork, the data may be lost or printed multiple times depending on lock states.

#### Rust implementation

Rust accesses `fork(2)` via the `libc` crate. A strict constraint applies to the child process post-fork: POSIX permits only async-signal-safe functions between `fork()` and `exec()`. This excludes most of `std::io`, as those functions may acquire locks and modify buffers that were duplicated during the fork. The following implementation utilizes `write(2)` directly to comply with this constraint.

```rust
//! fork_cow.rs
use libc::{fork, getpid, waitpid};

/// Use `write(2)` directly: after `fork()`, only async-signal-safe calls are permitted in
/// the child. `println!` does not meet this requirement.
fn raw_print(text: &str) {
    // SAFETY: `text` is valid for `text.len()` bytes for the duration of the call.
    unsafe { libc::write(1, text.as_ptr() as *const libc::c_void, text.len()) };
}

fn main() {
    let mut value: i32 = 42; // located on the parent's stack

    // SAFETY: single-threaded execution; the child performs one write() then _exit().
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
        // SAFETY: _exit skips destructors and the stdio flush.
        unsafe { libc::_exit(0) };
    }

    // SAFETY: `pid` corresponds to the child created above.
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

Invoking `fork` from a multithreaded process carries significant risks. The `std::process::Command` API exists to abstract this complexity, utilizing `posix_spawn` or a managed `fork` and `exec` sequence to ensure the child never executes arbitrary Rust code between the two system calls.

### 1.3 `exec()` replaces the process image

`execve(path, argv, envp)` does not allocate a new PID. It destroys the current process's address space, loads the new program, and begins execution at the entry point. The file descriptor table persists unless `FD_CLOEXEC` is set on a descriptor; this flag ensures the descriptor is closed automatically during the `exec` call. Server applications typically set `O_CLOEXEC` on sockets and files to prevent descriptor leaks.

Typical shell execution sequence:

```text
bash
 └─ fork()              # child bash process created
     └─ execve("curl")  # child retains PID but replaces image with curl
```

### 1.4 System call mechanics

User-space programs cannot access hardware or kernel memory directly. A function such as `read()` transitions through the C library (or a raw `syscall` instruction) via the following steps:

1. The syscall number and arguments are placed in registers.
2. The `syscall` (x86-64) or `svc` (AArch64) instruction is executed.
3. The CPU traps into kernel mode.
4. The kernel validates arguments, copies data from user pointers, executes the operation on the current task's kernel stack, and copies results back.
5. Control returns to user mode with the result in a register.

If a system call blocks (e.g., waiting for network data), the kernel transitions the task to a sleep state, allowing the scheduler to execute another runnable task.

`strace` is a diagnostic tracer that intercepts these system calls, useful for identifying performance bottlenecks or failure causes.

#### Context switch overhead

The aforementioned steps constitute the complete system call mechanism. The performance overhead arises from the privilege level transition: the CPU saves the user context, switches to the kernel stack, executes the entry path, and restores the user context. This transition cost is incurred before the actual operation begins, rendering even minimal system calls measurable in terms of latency.

```rust
//! syscall_cost.rs
use std::hint::black_box;
use std::time::Instant;

const ITERATIONS: u32 = 1_000_000;

fn main() {
    // Warm up: initial calls incur costs for page faults and lazy symbol resolution.
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

This measurement is specific to the hardware, kernel version, and CPU frequency governor of the test machine. Minor variations (e.g., a 10% spread) are normal for fixed instructions, which is why empirical measurements must always be accompanied by the environmental context.

Practical implications include the high relative cost of crossing the kernel boundary for small payloads. A server issuing one `read()` per 8 bytes spends more time on context transitions than on memory copying. Techniques such as batching (`sendmmsg`, `recvmmsg`, `io_uring`), memory mapping (`mmap`), and user-space networking (DPDK) are designed to amortize this transition cost. The `strace -c` utility aggregates these transitions, making it a primary tool for diagnosing syscall-bound applications.

#### API stability

The system call numbers, argument layouts, and error conventions (`-1` alongside `errno`) are fixed per architecture and constitute a published, stable interface. Binaries compiled against older kernel versions continue to function because of this strict backward compatibility.

Regarding the strict maintenance of backward compatibility in the user-space API, Linus Torvalds stated (LKML, 23 December 2012):

> WE DO NOT BREAK USERSPACE!
>
> Seriously. We've been doing this for decades. The fact that you don't understand why is not an excuse.

The architectural principle is clear: extending a public API requires additive changes rather than modifications, and versioning must be applied to any interface that cannot be safely extended.

### 1.5 Process states, zombies, and orphans

The `STAT` column in `ps` indicates the current process state:

| State | Meaning |
|---|---|
| `R` | Running or runnable |
| `S` | Interruptible sleep (waiting for I/O or an event) |
| `D` | Uninterruptible sleep (typically waiting on kernel I/O) |
| `T` | Stopped (via `SIGSTOP`) |
| `Z` | Zombie: exited but not yet reaped by the parent |
| `I` | Idle kernel thread |

A **zombie** is a task that has terminated, but its `task_struct` is retained until the parent invokes `wait()`. The kernel preserves the exit status for the parent to collect. If a parent never calls `wait()`, the child remains a zombie. If the parent terminates first, the child is reparented to `init` or `systemd` (PID 1), which subsequently reaps it.

A process in **D-state** cannot be terminated until the underlying kernel I/O operation completes. Storage or network failures frequently result in D-state processes; resolving the issue requires addressing the underlying device rather than sending `kill -9`.

#### Monitoring state transitions

Field 3 of `/proc/<pid>/stat` contains a single character representing the state, identical to the `STAT` column in `ps`. The following program forks a child, deliberately omits the reaping step, and reads the state field to demonstrate zombie persistence.

```c
/* zombie.c: an exited child remains in the process table until reaped. */
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
        _exit(0);                       /* child terminates immediately */

    printf("parent %d, child %d has exited\n", (int)getpid(), (int)pid);
    sleep(1);                           /* allow child to exit first */
    show_state("exited, not reaped", pid);
    show_state("still not reaped", pid);

    waitpid(pid, NULL, 0);              /* child is reaped here */
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

Although the child has no remaining code to execute, it continues to occupy a slot in the process table, which the `Z` state indicates. `waitpid(2)` collects the exit status, allowing the kernel to finally release the `task_struct`. Omitting the `sleep` often results in the first read showing `R` or `S`, as the parent may execute the read before the child is scheduled to exit. Due to this race condition, verifying a zombie state requires polling the status rather than relying on a single read.

Two operational consequences arise from this behavior. First, a container whose PID 1 fails to reap orphans will accumulate zombies until the process-table limit is reached; this constitutes an application defect rather than a kernel issue. Second, while a zombie consumes negligible memory, it holds a PID, which is a finite resource governed by `/proc/sys/kernel/pid_max`.

### 1.6 Signals and process control

Signals function as software interrupts. Key signals include:

- `SIGTERM` (15): Requests graceful termination, allowing the process to clean up resources.
- `SIGKILL` (9): Forces immediate termination; cannot be caught or blocked.
- `SIGSTOP` (19) / `SIGCONT` (18): Suspends and resumes execution.
- `SIGHUP` (1): Indicates terminal closure or requests a daemon configuration reload.
- `SIGCHLD`: Sent to a parent when a child stops or exits.

Container runtimes utilize signals for lifecycle management. For instance, Kubernetes sends `SIGTERM` to PID 1 in a pod, waits for the `terminationGracePeriodSeconds` duration, and then issues `SIGKILL` if the process has not exited.

Relevant diagnostic commands:

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

Every process operates within its own virtual address space, defined by `mm_struct` and page tables. The CPU translates virtual addresses to physical addresses via page tables, utilizing a Translation Lookaside Buffer (TLB) to cache recent translations. This architecture provides:

- Isolation (preventing processes from accessing each other's memory).
- Lazy allocation.
- Shared file pages.
- Copy-on-write semantics.
- Memory overcommit capabilities.

Typical 64-bit user address space layout (not to scale):

```text
0x0000_0000_0000_0000
├── text (executable code)
├── data / BSS
├── heap (grows upward via brk)
├── mmap region (shared libraries, mapped files, thread stacks, arenas)
├── stack (grows downward)
└── vsyscall / vvar / ... (kernel-exported pages)
```

#### Address translation mechanics

On 64-bit architectures, the hardware utilizes 48 bits of an address (with upper bits serving as sign extension). These 48 bits are divided into five fields: four 9-bit table indices and a 12-bit page offset. The 12-bit offset dictates the standard 4 KiB page size.

```text
47      39 38      30 29      21 20      12 11        0
+-----------+-----------+-----------+-----------+-----------+
| PGD   9b  | PUD   9b  | PMD   9b  | PTE   9b  | offset 12b|
+-----------+-----------+-----------+-----------+-----------+
```

Translation traverses the hierarchy sequentially: the PGD entry points to a PUD table, the PUD entry to a PMD table, the PMD entry to a PTE table, and the PTE contains the physical frame number. The offset is passed through untranslated. This process requires up to four dependent memory reads per translation, underscoring the necessity of the TLB and explaining why TLB misses are expensive events tracked by tools like `perf stat -e dTLB-load-misses`.

To contextualize the structure: nine bits per level means a single PTE table describes 512 pages. Multiplying 512 by 4 KiB yields 2 MiB of address space per table. Each table occupies exactly one page (512 entries × 8 bytes = 4096 bytes). Empty branches are not allocated, meaning a process accessing only a few megabytes of memory does not materialize page tables for the rest of the address space, rendering a 128 TiB virtual address space economically viable.

Consequently, the features listed above are all manifestations of the same underlying mechanism. Isolation, lazy allocation, shared libraries, and copy-on-write semantics all depend on resolving a single question: which physical frame a page table entry references, and whether multiple entries reference the same frame.

### 2.2 Pages, page faults, and RSS

Memory is managed in discrete pages (typically 4 KiB, alongside 2 MiB or 1 GiB huge pages). When a program requests memory via `malloc(1 GiB)`, the kernel generally records the virtual address space allocation without immediately assigning physical memory. The first write to a page triggers a **page fault**, prompting the kernel to allocate and map a physical page.

Page fault classifications:

- **Minor fault**: The page is already resident in memory (e.g., in the page cache or as a COW page) and only requires a new PTE.
- **Major fault**: The kernel must retrieve the page from a backing store (disk or network).
- **Protection fault**: Triggered by COW operations, read-only mappings, or access violations.
- **Segmentation fault**: Attempted access to a virtual address lacking a valid mapping.

Relevant memory metrics:

- **VSZ** (Virtual Size): The total mapped virtual address space, including non-resident libraries and mappings.
- **RSS** (Resident Set Size): The physical pages currently mapped to the process.
- **PSS** (Proportional Set Size): RSS divided proportionally among processes sharing a page (available in `/proc/<pid>/smaps_rollup`).
- **Page cache**: File-backed pages cached by the kernel. It is standard for `free` to report most memory as "used" by the cache, which is reclaimed automatically under memory pressure.

Diagnostic commands:

```bash
cat /proc/self/status
cat /proc/self/smaps_rollup
grep -E 'VmSize|VmRSS|RssAnon|RssFile|ShmemPmdMapped' /proc/self/status
free -h
vmstat 1 5
```

#### Measuring page faults

The kernel maintains per-process fault counters, allowing empirical measurement of paging behavior. `getrusage(RUSAGE_SELF)` returns `ru_minflt` and `ru_majflt`; these values correspond to fields 10 and 12 in `/proc/<pid>/stat` and the output of `ps -o min_flt,maj_flt`. The following program maps 64 MiB of anonymous memory and writes to the entire region twice.

```c
/* faults.c: measuring kernel page fault counters. */
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
    memset(p, 1, len);                      /* initial touch of every page */
    getrusage(RUSAGE_SELF, &after);
    delta("first touch", &before, &after);

    getrusage(RUSAGE_SELF, &before);
    memset(p, 2, len);                      /* pages are already resident */
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

The arithmetic aligns precisely: 64 MiB ÷ 4 KiB equals 16,384 pages, and the initial memory access triggered exactly one minor fault per page. The second pass over the identical range generated zero faults because the pages were already resident and the PTEs were established. The `major` fault count remains zero for anonymous memory, confirming that no data was read from a backing store.

This principle also applies to the `mmap` of a *file*. In that scenario, the initial touch results in a minor fault if the page is present in the page cache, or a major fault if it must be read from disk. Monitoring `majflt` is highly valuable in production environments, as sustained major faults indicate that the application's working set exceeds available RAM.

#### Rust implementation of fault counters

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

This program bypasses the user-space allocator. Because `mmap` is the underlying system call for `malloc`, invoking it directly removes allocator overhead from the measurement. Diagnosing heap issues requires the allocator to be active, whereas analyzing kernel accounting does not.

### 2.3 `malloc`, `brk`, and `mmap`

The glibc `malloc` implementation manages heap **arenas**. Small allocations are drawn from arenas that expand via `brk` or `mmap`, whereas large allocations utilize `mmap` directly and are unmapped immediately upon `free`. Because memory remains virtual until accessed, allocating massive buffers is inexpensive, but touching the entirety of the buffer can trigger the OOM killer if cgroup or host limits are breached.

Operational considerations for cloud services:

- Allocate memory lazily or utilize explicit memory pools if latency spikes are unacceptable.
- Monitor `RssAnon` (anonymous memory) to track actual process memory consumption.
- A memory leak in a container may not immediately reflect in `top` RSS if the leaked pages are never subsequently accessed.

#### Allocation strategies

`brk` and `mmap` represent distinct memory acquisition methods, and glibc dynamically selects between them. The default threshold (`M_MMAP_THRESHOLD`) is 128 KiB: requests exceeding this size are served by `mmap` and released upon `free`, while smaller requests are drawn from the heap extended by `brk`. The following program outputs the program break and the mapping count in `/proc/self/maps` surrounding small and large allocations.

```c
/* heap.c: glibc utilizes brk for small blocks and mmap for large allocations. */
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

Three behaviors are evident in the output. The 64 KiB block was allocated from the heap: `brk` advanced, and the mapping count remained static. The 8 MiB block exhibited the opposite behavior: `brk` remained unchanged, the mapping count increased from 16 to 17, and the address was placed in the high region of the address space, which is characteristic of `mmap`. Following `free`, the large mapping was removed, but `brk` did not retract, as glibc retains the expanded heap for future reuse.

This memory retention behavior is particularly significant in production environments. A process that repeatedly allocates and frees large buffers maintains a stable mapping count rather than returning memory to the OS between calls. Similarly, a process allocating numerous small objects retains both the pages and the `brk` address for its lifecycle. Neither behavior constitutes a traditional "lost pointer" memory leak, and neither manifests as growing `RSS` unless the memory is actively touched. This explains scenarios where `RSS` appears stable, yet a container is OOM-killed; the termination is typically caused by a cgroup limit set below the peak *touched* memory set, rather than a leak.

### 2.4 Overcommit and the OOM killer

The Linux kernel permits `malloc` to succeed even when physical RAM is insufficient. This is governed by the overcommit mode (`0` for heuristic, `1` for always overcommit, `2` for never overcommit). When physical memory is exhausted, the kernel invokes the Out-Of-Memory (OOM) killer, which evaluates process scores and terminates a task to reclaim memory.

In containerized environments, memory limits are enforced via **cgroup v2**. When a cgroup exceeds `memory.max`, the kernel first attempts to reclaim pages within that specific cgroup. If reclamation fails, the cgroup OOM killer is invoked. Consequently, a container exceeding its limit does not necessarily compromise the entire node. Relevant kernel messages in `dmesg` appear as `Memory cgroup out of memory: Killed process ...`.

#### The rationale for memory overcommit

Memory overcommit represents a divergence between the Linux kernel's memory model and traditional textbook models. While a conventional allocator denies requests when resources are exhausted, Linux allocates virtual address space that may exceed available physical backing. This design accommodates `fork`-heavy workloads (which would otherwise fail constantly if every child required full physical backing) and reflects the reality that most programs reserve significantly more memory than they actively touch. The mode is configured via `vm.overcommit_memory` (defaulting to `0`, heuristic).

A critical implication is that a non-NULL return from `malloc` does not guarantee physical memory availability. Failure manifests later as an OOM kill, with the victim selected by `oom_score` rather than the process that requested the memory. To prevent the heuristic from terminating critical host processes, production systems apply a `memory.max` limit to the cgroup, confining OOM kills to the specific container that exceeded its allocation.

On the divergence between theoretical models and practical implementation, Linus Torvalds noted (*The Linux Edge*, in *Open Sources*, O'Reilly, 1999):

> Theory and practice sometimes clash. Theory loses. Every single time.

Both the design and its deviations are operationally significant. Overcommit mechanics, `oom_score` calculations, and the delta between `VmSize` and `VmRSS` are direct consequences of this architecture.

### 2.5 Huge pages and NUMA

- **Huge pages** reduce TLB misses and page-table overhead for large memory regions, which is critical for specific HPC and database workloads. Kubernetes natively supports `hugepages-2Mi` and `hugepages-1Gi` as schedulable resources.
- **NUMA** (Non-Uniform Memory Access) architectures dictate that memory attached to a specific CPU socket is accessed faster by CPUs on that same socket. GPU servers exhibit strong NUMA characteristics; PCIe/NVLink topology and GPU memory locality heavily influence data transfer performance. The `numactl --hardware` command maps nodes and access distances.

GPU-specific memory considerations:

- CUDA pinned (page-locked) host memory facilitates DMA without bounce buffers and is explicitly configured as non-swappable.
- GPUs utilize dedicated HBM memory. While `nvidia-smi` reports used and free GPU memory, this is distinct from host RSS.
- GPUDirect Storage enables DMA transfers directly from storage to GPU memory, bypassing host memory entirely.

---

## 3. Namespaces, cgroups, and containers

### 3.1 Namespace isolation mechanics

Namespaces provide processes with isolated views of system resources. The `clone()` and `unshare()` system calls accept namespace flags, while `setns()` attaches a process to an existing namespace. Fundamentally, a container comprises a set of processes operating within new namespaces, constrained by cgroup limits.

| Namespace | Flag | Isolates |
|---|---|---|
| Mount | `CLONE_NEWNS` | Mount points and filesystem hierarchy |
| PID | `CLONE_NEWPID` | Process IDs (PID 1 inside is distinct from host PID 1) |
| Network | `CLONE_NEWNET` | Network interfaces, routing tables, firewalls, and sockets |
| UTS | `CLONE_NEWUTS` | Hostname and NIS domain name |
| IPC | `CLONE_NEWIPC` | System V IPC and POSIX message queues |
| User | `CLONE_NEWUSER` | User and group IDs (enabling unprivileged namespaces) |
| Cgroup | `CLONE_NEWCGROUP` | View of the cgroup hierarchy root |
| Time | `CLONE_NEWTIME` | Clock offsets |

PID namespace nuance: A process within a new PID namespace perceives itself as PID 1, while the host kernel tracks it under a different PID. By default, `ps` executed inside a container only enumerates processes within that specific PID namespace.

#### Implementation details of namespaces

The underlying mechanism is more streamlined than the associated terminology might imply. The kernel maintains a single namespace object per type (e.g., `struct uts_namespace`, `struct pid_namespace`), and each task holds a pointer to its respective objects. System calls that resolve names—such as `gethostname`, `kill`, `mount`, or `socket`—resolve them through the namespace referenced by the calling task. Creating a namespace allocates a fresh object and updates the task's pointer. No data is copied, and isolation does not rely on a hypervisor boundary. This architectural choice allows containers to initialize in milliseconds, but it also means that a kernel vulnerability accessible via a namespace affects the host directly, rather than being contained within a guest environment.

The UTS namespace is the most straightforward to demonstrate, as it primarily manages a single field (the hostname). The following program requests an isolated copy of this field.

```c
/* ns.c: the UTS namespace manages the hostname, allowing process-level isolation. */
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
        printf("this requires CAP_SYS_ADMIN. Alternative execution:\n");
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

Execution as an unprivileged user yields a permission error:

```text
$ gcc -O2 -o ns ns.c && ./ns
unshare(CLONE_NEWUTS) = -1 errno=1 (Operation not permitted)
this requires CAP_SYS_ADMIN. Alternative execution:
  unshare --user --map-root-user --uts ./ns
```

Namespace creation is a privileged operation because namespaces form the foundation of process confinement. Unprivileged users can bypass this restriction utilizing the user namespace, which can be created without elevated privileges. Inside the user namespace, the user's UID is mapped to root, granting the capabilities required to create the remaining namespaces.

```text
$ unshare --user --map-root-user --uts ./ns
hostname before: yahboom
hostname after : in-a-namespace
```

This sequence illustrates the mechanics of `docker run` for unprivileged users and the foundation of rootless containers. The runtime does not execute privileged operations on the user's behalf; rather, the user namespace grants the necessary privileges within a strictly confined scope.

### 3.2 cgroups v2: accounting and limiting

cgroup v2 (`/sys/fs/cgroup`) organizes processes into a hierarchical tree. Primary controllers include:

- `cpu.max`: Defined as `$MAX_PERIOD $PERIOD` (e.g., `50000 100000` allocates 50% of one CPU).
- `memory.max`: Hard memory limit. `memory.current` and `memory.events` report usage and OOM counts.
- `memory.high`: Throttling threshold applied before the hard limit is reached.
- `io.max`: I/O bandwidth and IOPS limitations.
- `pids.max`: Maximum allowed tasks and threads.
- `cpuset.cpus` / `cpuset.mems`: CPU and memory affinity constraints.
- `misc.max`: Miscellaneous resources managed via the misc controller.

cgroup v2 operational rules:

- **No internal processes rule**: A cgroup containing child cgroups cannot simultaneously hold processes. `cgroup.subtree_control` is used to delegate controllers to child cgroups.
- The kernel attributes process resource usage to the cgroup containing it. Upon fork, the child inherits the parent's cgroup membership unless explicitly migrated.
- `memory.events` tracks `oom_kill`, `max`, and `high` threshold counters.

Diagnostic commands:

```bash
cat /proc/self/cgroup
cat /sys/fs/cgroup/memory.max
cat /sys/fs/cgroup/memory.current
cat /sys/fs/cgroup/memory.events
cat /sys/fs/cgroup/cpu.max
cat /sys/fs/cgroup/pids.max
systemd-cgls
```

### 3.3 Container lifecycle: Image to execution

When Kubernetes schedules a Pod, the kubelet instructs the Container Runtime Interface (CRI) daemon (e.g., containerd) to initialize a sandbox (pause container) and subsequent application containers. The high-level execution flow is as follows:

1. `containerd` receives the CRI request.
2. It constructs an OCI bundle from the image: assembling the rootfs from image layers and generating a configuration file detailing mounts, environment variables, commands, namespaces, cgroup paths, and device access.
3. `containerd` invokes the OCI runtime (e.g., `runc`) via `runc create`.
4. `runc` establishes namespaces using `clone()`/`unshare()`, configures cgroup membership, applies mounts, and executes `pivot_root` into the container rootfs.
5. `runc` initiates the container process via `exec`.
6. The process executes with a restricted system view. PID 1 inside the container is typically the primary application or a minimal init process.

The pause (sandbox) container retains the network namespace and shared infrastructure, enabling application containers within the same Pod to share localhost networking and volumes.

### 3.4 Container runtime device injection

By default, a container lacks access to `/dev/nvidia*` devices and CUDA user-space libraries. The GPU Operator and NVIDIA Container Toolkit automate this integration. At a foundational level, `nvidia-container-cli` executes the following steps:

1. Detects the host driver version and verifies CUDA compatibility.
2. Mounts the driver's user-space libraries (`libcuda.so`, `libnvidia-ml.so`, etc.) into the container filesystem.
3. Creates and bind-mounts GPU device nodes (`/dev/nvidia0`, `/dev/nvidiactl`, `/dev/nvidia-uvm`, `/dev/nvidia-modeset`, and MIG devices) into the container.
4. Injects required environment variables (`NVIDIA_VISIBLE_DEVICES`, `NVIDIA_DRIVER_CAPABILITIES`).
5. For MIG configurations, exposes the requested compute instance device node.

The container continues to execute on the host kernel; the driver's kernel module resides exclusively on the host. The container receives access to the identical kernel driver alongside matching user-space libraries. This architecture necessitates strict compatibility between the host driver version and the CUDA version utilized within the container.

The Kubernetes device plugin, rather than the container runtime, dictates GPU assignment. The kubelet invokes the plugin's `Allocate` RPC post-scheduling; the plugin returns device IDs and environment variables, which the runtime subsequently utilizes to inject the devices.

---

## 4. Filesystem and I/O

### 4.1 VFS and core objects

The Linux Virtual File System (VFS) abstracts underlying filesystem implementations. Core objects include:

- `super_block`: Represents a mounted filesystem.
- `inode`: Stores file metadata (owner, permissions, size, block pointers).
- `dentry`: Directory entry mapping a string name to an inode; heavily cached by the VFS.
- `file`: Represents an open file description, maintaining the current offset, flags, and operation methods.

`stat` retrieves inode metadata; `df` reports filesystem utilization; `lsof` enumerates open files.

#### Object relationships and nesting

These objects operate in a nested hierarchy. A `super_block` owns a collection of `inode`s. An `inode` lacks an inherent name. A `dentry` assigns a name to an inode within a specific directory. A `file` provides a per-open-descriptor view, maintaining an independent offset.

This nested structure clarifies several fundamental filesystem behaviors: two processes can hold the same file open at different offsets (resulting in two `file` objects referencing one `inode`); renaming a file alters the `dentry` but leaves the underlying `inode` unchanged; and a hard link is simply a secondary `dentry` pointing to an existing `inode`, which inherently prevents hard links from crossing filesystem boundaries.

At the system call boundary, failures are reported using a standard convention: a return value of `-1` accompanied by a thread-local `errno` variable. This thread-local storage ensures `errno` remains safe for use in multithreaded applications.

```c
/* errno.c: the system call boundary reports failure via -1 and errno. */
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

    n = read(fd, buf, sizeof buf - 1);      /* may return fewer bytes than requested */
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
    try_open("/etc/shadow");                /* exists, but lacks read permissions for this uid */
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

The output demonstrates three distinct failure modes. `ENOENT` (2) and `EACCES` (13) represent different conditions that a caller must distinguish, which is the primary rationale for the existence of `errno` rather than a generic failure code. The assigned descriptor is 3 rather than 1 because 0, 1, and 2 are reserved for standard input, output, and error. The descriptor table functions as a small integer namespace per process, and exhausting it (`EMFILE`) is a common failure mode in server applications. Finally, `read` returned 8 bytes; the system call is permitted to return fewer bytes than requested. A robust reader must implement a loop to handle partial reads. Incorrectly handling short reads—either by treating them as fatal errors or as the end-of-file—is a frequent source of bugs in systems programming.

### 4.2 Filesystems relevant to Kubernetes

- **ext4/xfs**: Standard local disk filesystems.
- **tmpfs**: RAM-backed filesystem, utilized for `emptyDir` volumes with `medium: Memory` and `/dev/shm`.
- **overlayfs**: Combines lower read-only image layers with an upper writable layer; the standard rootfs implementation for containerd and Docker.
- **FUSE**: User-space filesystems (utilized by certain CSI drivers and tools like gcsfuse).
- **Network filesystems**: NFS and cloud-native CSI volumes (e.g., EBS, EFS, PVCs).

**Overlayfs copy-up behavior**: When a container modifies a file present in a lower image layer, the kernel copies the file to the upper layer prior to executing the write. Deleting a file from a lower layer generates a "whiteout" file in the upper layer. Consequently, the initial write to a large file residing in a lower layer incurs significant I/O overhead.

### 4.3 Mount propagation

Mount events can propagate between mount namespaces, categorized as `shared`, `slave`, `private`, or `unbindable`. Kubernetes relies on this mechanism for `hostPath` volumes and for the container runtime to inject devices and libraries. Executing `mount --make-rshared /` is standard practice on nodes to ensure mounts created within containers remain visible to required host subsystems. Misconfigured propagation frequently results in "device or resource busy" errors or invisible mounts.

Diagnostic commands:

```bash
mount | grep -E 'overlay|nvidia|/var/lib/kubelet'
cat /proc/self/mountinfo
findmnt -R /var/lib/kubelet | head -50
```

### 4.4 I/O stack and pressure

The I/O path traverses: process system call → VFS → filesystem → block layer → device driver. The page cache absorbs read and write operations; dirty pages are asynchronously flushed by per-device writeback threads. Storage performance metrics include:

- `iostat -x 1`: Reports `%util`, `await`, and `svctm`.
- `pidstat -d 1`: Reports per-process I/O statistics.
- `/proc/pressure/io`, `/proc/pressure/memory`, `/proc/pressure/cpu`: Expose Pressure Stall Information (PSI), providing more actionable metrics than raw utilization percentages.
- `iotop`: Displays real-time, per-process I/O consumption.

---

## 5. Networking deep dive

### 5.1 Sockets and TCP

A socket represents a network endpoint identified by an IP address and port. `socket()` creates the endpoint, `bind()` assigns an address, `listen()` marks it as passive, `accept()` returns a newly connected socket, and `connect()` initiates an outbound connection. `ss` is the standard utility for socket inspection:

```bash
ss -tulpn
ss -tan state established
ss -tnp | grep :443
```

The TCP state machine for server-side connections follows the sequence:
`LISTEN → SYN_RECV → ESTABLISHED → FIN_WAIT/CLOSE_WAIT → ...`.

Critical TCP states:

- `CLOSE_WAIT`: Indicates the remote side closed the connection, but the local application has not yet closed its socket. A high count typically indicates an application-level resource leak.
- `TIME_WAIT`: A normal state following an active close, designed to allow delayed packets to expire. High `TIME_WAIT` counts are generally benign unless ephemeral ports or socket descriptors are exhausted.
- `somaxconn` / backlog: Dictates the maximum number of pending connections the kernel will queue.

### 5.2 Packet path through a Linux host

Outbound path: Application → socket buffer → TCP/IP stack → routing → netfilter (`iptables`/`nftables`) → neighbor/ARP → NIC driver → physical wire.

Inbound path: The NIC DMAs packets into ring buffers and raises an interrupt (or relies on NAPI polling). The kernel parses headers, executes netfilter/prerouting rules, and either forwards the packet or delivers it to the target socket.

### 5.3 Netfilter, conntrack, iptables/nftables

Netfilter hooks are kernel interception points for packet filtering and Network Address Translation (NAT). `iptables` manages tables (`filter`, `nat`, `mangle`, `raw`) and chains. `conntrack` maintains connection state, enabling rules such as `-m conntrack --ctstate ESTABLISHED,RELATED`.

Kubernetes networking implementations:

- Services utilizing `kube-proxy` in iptables mode perform DNAT to selected Pod IPs.
- `ClusterIP` traffic is NATed; return traffic is un-NATed via conntrack.
- NetworkPolicy is frequently implemented by CNI plugins (Calico/Cilium) using iptables or eBPF.
- Cilium can bypass iptables entirely, utilizing eBPF for service load balancing and policy enforcement.

Diagnostic commands:

```bash
iptables -L -n -v
iptables -t nat -L -n -v
conntrack -L | head
nft list ruleset | head
```

### 5.4 Network namespaces, veth, bridges, and CNI

Each Kubernetes Pod is typically assigned a dedicated network namespace. The Container Network Interface (CNI) plugin executes the following sequence:

1. Creates a virtual ethernet (veth) pair.
2. Places one end of the veth pair into the Pod's network namespace.
3. Attaches the host end to a bridge, Open vSwitch (OVS), or virtual routing/encapsulation device.
4. Assigns an IP address (typically drawn from the node's Pod CIDR).
5. Configures routing tables and applies network policies.
6. Reports the interface and IP configuration back to the kubelet.

Network topology layout:

```text
Pod netns                    Host netns
┌─────────────┐ veth         ┌─────────────────────────┐
│ eth0        ├─────────────►│ vethXXX ──► cni0/bridge │
│ 10.244.1.5  │              │           │             │
└─────────────┘              │         eth0            │
                             └─────────────────────────┘
```

The `localhost` interface inside a pod resolves exclusively to the pod's network namespace, not the underlying host node.

### 5.5 DNS resolution

Pods utilize CoreDNS (or an equivalent cluster DNS service). DNS resolution inside a pod initially consults `/etc/resolv.conf`, which points to the cluster DNS endpoint. Search domains enable the use of short service names. A common configuration issue arises when `ndots:5` is set, generating excessive DNS queries for external names, or when host networking bypasses the cluster DNS configuration.

---

## 6. Debugging a sick Linux node

### 6.1 Systematic triage order

Diagnostic procedures should follow a layered approach, from the node infrastructure down to specific hardware accelerators:

1. **Node availability**: `kubectl get node`, `kubectl describe node`.
2. **Load and resource baselines**: `uptime`, `free -h`, `df -h`, `top`.
3. **Kernel and device logs**: `dmesg -T | tail`.
4. **Container runtime**: `crictl ps -a`, `journalctl -u containerd`.
5. **Kubelet status**: `journalctl -u kubelet`, inspect `/var/lib/kubelet`.
6. **Application logs**: `kubectl logs`, `kubectl describe pod`.
7. **GPU-specific diagnostics**: `nvidia-smi`, device plugin logs, allocatable resources, Xid errors, and ECC errors.

### 6.2 Scenario: Pods stuck in `Pending`

A `Pending` state indicates the scheduler has failed to place the Pod. Common causes include:

- Insufficient CPU, memory, or GPU resources across all available nodes.
- No node satisfies `nodeSelector`, node affinity, or toleration requirements.
- `nvidia.com/gpu` is missing from the node's allocatable resources.
- Namespace `ResourceQuota` or `LimitRange` restrictions block admission.
- An unbound PersistentVolumeClaim (PVC) causes scheduling failure post-node filtering.
- The node is tainted with `NoSchedule`, and the pod lacks the corresponding toleration.
- The `kube-scheduler` pod is down or marked unschedulable.

Diagnostic commands:

```bash
kubectl describe pod <pod>
kubectl get nodes -o wide
kubectl describe node <node>
kubectl get events -A --sort-by=.lastTimestamp
kubectl get pvc
```

### 6.3 Scenario: Pod scheduled but stuck in `ContainerCreating`

This state indicates the kubelet is actively processing the pod but encountering friction:

- **Image pull errors**: Review `kubectl describe pod` events.
- **Storage mount failures**: Check events and `journalctl -u kubelet`.
- **Runtime start failures**: Inspect `crictl ps -a` and `journalctl -u containerd`.
- **Device plugin allocation failure**: `kubectl describe pod` may report `Failed to create pod sandbox` or `Allocate failed`.

### 6.4 Scenario: Pod in `CrashLoopBackOff`

- `kubectl logs <pod> --previous` retrieves the logs from the terminated container instance.
- Exit code 137 indicates `SIGKILL` (frequently caused by OOM kills or failed liveness probes); exit code 143 indicates `SIGTERM`.
- If exit code 137 is accompanied by `OOMKilled` in the pod status, inspect the memory limits and `memory.events`.
- If liveness probes are failing, `kubectl describe pod` will detail the probe failure reasons.

### 6.5 Scenario: GPU node cannot allocate GPUs

Execute the following diagnostic sequence:

1. **Verify host driver visibility:**
   ```bash
   nvidia-smi
   ```
   If absent, the driver module is unloaded or the node requires a reboot post-installation.

2. **Verify device plugin status:**
   ```bash
   kubectl get pods -n gpu-operator -l app=nvidia-device-plugin-daemonset
   kubectl logs -n gpu-operator -l app=nvidia-device-plugin-daemonset
   ```

3. **Verify node resource advertisement:**
   ```bash
   kubectl describe node | grep -A5 'nvidia.com/gpu'
   ```
   If `Allocatable` is missing, plugin registration failed to complete.

4. **Verify Pod request alignment:** `nvidia.com/gpu` is an extended resource. It must be defined in `limits`, and Kubernetes mandates `limits == requests` for extended resources.

5. **Verify runtime injection:**
   ```bash
   kubectl exec <pod> -- nvidia-smi
   ```
   If the binary is missing, the container toolkit or GPU Operator failed to configure runtime hooking.

6. **Check for hardware or kernel errors:**
   ```bash
   dmesg | grep -i xid
   dmesg | grep -i nvidia
   nvidia-smi -q -d ECC
   nvidia-smi -q -d PAGE_RETIREMENT
   nvidia-smi --query-gpu=timestamp,name,pci.bus_id,utilization.gpu,memory.used,temperature.gpu,power.draw --format=csv
   ```

Xid errors are diagnostic messages emitted by the NVIDIA driver; specific Xid numbers correspond to distinct hardware or software faults. The concurrent presence of Xid and ECC errors strongly indicates a hardware or driver fault, effectively ruling out a Kubernetes configuration issue.

### 6.6 Scenario: High CPU utilization with no obvious process

Diagnostic commands:

```bash
top -b -n1 -H | head -20
pidstat 1
perf top
cat /proc/loadavg
ps -eo pid,stat,wchan:30,comm
```

The `wchan` column indicates the kernel function in which a task is currently blocked. A process in state `R` exhibiting high CPU usage may be spinning in user space or kernel space. Utilize `perf top` for sampling, or capture a stack trace:

```bash
perf record -F 99 -g -p <pid> -- sleep 10
perf report
```

---

## 7. Performance tools and observability

| Layer | Tool | Metrics to monitor |
|---|---|---|
| CPU | `top`, `pidstat -u`, `perf top` | %usr vs %sys, context switches, runnable threads |
| CPU scheduler | `/proc/pressure/cpu`, `cat /sys/fs/cgroup/cpu.stat` | Runnable pressure, throttling events |
| Memory | `free`, `/proc/pressure/memory`, `valgrind massif` | PSI, anonymous vs file-backed memory, swap usage, OOM events |
| Disk | `iostat -x`, `pidstat -d`, `/proc/pressure/io` | I/O await, %util, per-process I/O volume |
| Network | `sar -n DEV`, `ss`, `tcpdump`, `ethtool -S` | Packet drops, TCP retransmits, queue saturation |
| Syscalls | `strace -f -tt`, `ltrace` | Blocked calls, `EAGAIN` spin loops |
| Tracing | `perf trace`, `bpftrace`, `ftrace` | Kernel-level execution paths |
| Containers | `crictl stats`, `systemd-cgtop` | Per-pod and per-container resource consumption |

### ftrace and bpftrace examples

```bash
# Trace process execution
bpftrace -e 'tracepoint:sched:sched_process_exec { printf("%s %s\n", comm, args->filename); }'

# Trace openat system calls
bpftrace -e 'tracepoint:syscalls:sys_enter_openat { printf("%s %s\n", comm, str(args->filename)); }'

# Query cgroup OOM events
grep oom_kill /sys/fs/cgroup/memory.events
```

### Appropriate use cases for `perf`

- High CPU utilization with an unknown owner: `perf top`.
- Diagnosing lock contention: `perf lock`.
- Querying hardware performance counters: `perf stat`.
- Generating flame graphs from `perf record` output.

---

## 8. Container vs. VM architecturalural differences

| Aspect | Container | Virtual Machine (VM) |
|---|---|---|
| Isolation boundary | Kernel namespaces, cgroups, seccomp | Hardware virtualization (e.g., KVM) |
| Kernel architecture | Shared host kernel | Dedicated guest kernel |
| Boot latency | Milliseconds (process initialization) | Seconds (full kernel boot) |
| Device access | Mediated by runtime and device cgroups | Virtual devices or PCIe passthrough |
| Attack surface | System calls filtered by seccomp/AppArmor | Full kernel interface exposed to guest |
| GPU integration | Device plugin + container runtime hooks | vGPU, MIG, or PCIe passthrough |

GPU cloud infrastructure spans both models: Kubernetes pods utilizing device plugins and MIG for containerized workloads, alongside dedicated GPU instances and VMs for tenants requiring absolute hardware control.

---

## 9. Technical summaries and operational concepts

### `docker run` execution sequence

1. The Docker client communicates with dockerd/containerd.
2. The image is pulled and unpacked into an OCI rootfs (utilizing overlayfs).
3. The runtime establishes namespaces and cgroups, and prepares mounts and device nodes.
4. `runc` initiates the primary process as PID 1 within the new namespaces.
5. The process operates with a restricted view of host processes, network interfaces, mounts, and hardware resources.

### Cgroup memory limit enforcement

The kernel attributes anonymous and page-cache memory to the respective cgroup. When `memory.current` exceeds `memory.max`, the kernel initiates memory reclamation. If reclamation fails to reduce usage below the threshold, the cgroup OOM killer terminates a process. The container exits (frequently with code 137), and `kubectl describe pod` will report `OOMKilled`.

### Shared kernel with isolated PID namespace

A container shares the host kernel (hence `uname` outputs match the host), but operates within a distinct PID namespace. Consequently, `ps` enumerates only the PIDs resident within that specific namespace. Without a PID namespace, the container would have visibility into host processes; Kubernetes defaults to isolating PID namespaces for pods to prevent cross-pod interference.

### Linux memory reporting (`free`)

Linux utilizes available RAM for the page cache and reclaims it dynamically under memory pressure. Therefore, "free" memory is not an accurate indicator of system health. Operational monitoring should prioritize available memory, Pressure Stall Information (PSI), and cgroup utilization metrics.

### Containers versus Virtual Machines

Containers are standard Linux processes constrained by kernel-enforced isolation mechanisms (namespaces and cgroups). VMs execute distinct operating system kernels atop virtualized hardware. Containers share the host kernel, resulting in lower overhead, whereas VMs provide stricter isolation boundaries and the ability to run heterogeneous operating systems.

### Zombie processes and reaping

A zombie is a terminated task whose parent has failed to invoke `wait()`. The `init` process (PID 1) adopts orphaned children and reaps them. A container utilizing a defective init process may accumulate zombies within its isolated PID namespace, eventually exhausting the namespace's PID limit.

### Debugging GPU allocation failures

The standard diagnostic sequence involves verifying: host `nvidia-smi` output, driver module status, device plugin pod health and logs, `nvidia.com/gpu` allocatable resources on the node, Pod resource limit definitions, container runtime toolkit/GPU Operator state, and finally, hardware-level Xid/ECC errors.

### The Page Cache

The page cache stores file contents in RAM. Read operations hit the cache, bypassing disk I/O; write operations are buffered in the cache and flushed asynchronously. Manually dropping the page cache is rarely a valid performance optimization, as it discards highly utilized cached data, forcing subsequent reads to incur disk latency penalties.

### Connection Tracking (conntrack)

Conntrack maintains connection state to facilitate NAT and firewall operations. The `kube-proxy` iptables mode relies on conntrack to reverse DNAT operations on return traffic. If the conntrack table reaches capacity (`nf_conntrack_max`), new connections will fail or be dropped. Monitoring `nf_conntrack_count` relative to the maximum limit is critical for high-throughput nodes.