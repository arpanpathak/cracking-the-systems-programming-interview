# 1. Processes and the Kernel's View of a Task {#processes-and-tasks}

A Kubernetes Pod, a `docker run`, and a shell pipeline all come down to the same
kernel object: a `task_struct`. Linux has no separate "container process" type
and no separate "thread" type. What the rest of this book calls a process, a
thread, or a container is one task, or several tasks that share some state and
not other state. This chapter is about that one data structure, because every
later mechanism, namespaces, cgroups, signals, the scheduler, is a view onto
it.

## The kernel's unit of execution is a task

On Linux, both processes and threads are represented by the same kernel
structure: `task_struct`. What is usually called a process is a **thread
group**: one or more tasks sharing the same Thread Group ID (`TGID`). In user
space:

- `getpid()` returns the TGID of the calling task (the "process ID").
- `gettid()` returns the kernel task ID (`PID` in `/proc/<pid>/status`, i.e.
  `Tgid` vs `Pid`).
- `ps -Lf` and `top -H` show individual tasks and threads.

In `ps -eo pid,tid,ppid,comm`, the `pid` column is the process ID and `tid` is
the thread ID. For a single-threaded process they are the same number.

There is a real payoff to a single structure, beyond convenience: separate
process and thread tables would force every scheduling decision, signal
delivery, and credential check to ask which table it is looking at. With one
`task_struct` and a `tgid` field, "thread" becomes a relationship between
tasks rather than a second kind of object. `kill(2)` addresses a thread or a
whole thread group depending on how the ID is formed, and
`/proc/<tgid>/task/<tid>` exists as a directory rather than a separate
filesystem, both for the same reason.

Linus Torvalds, on why the shape of the data matters more than the shape of the
code (git mailing list, 27 July 2006):

> I will, in fact, claim that the difference between a bad programmer and a good
> one is whether he considers his code or his data structures more important.
> Bad programmers worry about the code. Good programmers worry about data
> structures and their relationships.

The scheduler, the signal code, the accounting in cgroups, and the `/proc` tree
are all views onto this one object, so questions about process behavior are
usually questions about which field of it changed and who changed it.

## `fork()`, `vfork()`, and `clone()`

`fork()` creates a child task by copying the parent's address space,
file-descriptor table, signal handlers, and most other process state. The copy
is virtualized through **copy-on-write (COW)**: both parent and child initially
point at the same physical pages, marked read-only. When either one writes, the
kernel duplicates the page. This is why `fork()` is cheap for small children,
and why memory usage (`PSS`) should not be computed as
`RSS(parent) + RSS(child)`.

`vfork()` originally suspended the parent until the child called `exec()` or
`exit()`; it is rarely needed today because COW already makes `fork()` cheap.

`clone()` is the low-level syscall used by pthreads and container runtimes.
Flags select what is shared with the child. `clone(CLONE_THREAD)` creates a
thread; `clone(CLONE_NEWPID|CLONE_NEWNS|...)` creates a process in new
namespaces, which is what `runc` does to start a container. Chapter 3 covers
those flags in detail.

Threads are processes that share an address space, file descriptors, and
signal handlers; they are not a separate kernel concept.

### What copy-on-write does

`fork()` copies nothing at the moment of the call. It marks the parent's
writable pages read-only in *both* page tables; the first writer among the two
takes a protection fault, and the kernel duplicates that one page and hands out
a writable mapping. The program below makes the consequence visible: parent and
child print the *same* address holding *different* values, which is only
possible because the address printed is virtual and the physical frame behind
it was duplicated on the first write.

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

Two processes, one address, two values. `cat /proc/<pid>/smaps` shows the
copied page as a dirty anonymous page charged to each process separately,
which is exactly what `PSS` accounts for and `RSS` does not.

The trap in that listing is the `fflush`. Stdout to a pipe is block-buffered,
and `_exit(2)` does not run the stdio flush. A program that prints in the child
and then calls `_exit` loses the output with no error to explain it:

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

This is the same class of bug as writing to a forked child while a lock on the
stdio buffer is held: the buffer was duplicated by the fork, so the data is
either lost or printed twice.

Rust reaches `fork(2)` through the `libc` crate. The constraint is on what the
child may do afterward: POSIX permits only async-signal-safe functions between
`fork()` and `exec()`. That excludes nearly everything in `std::io`, because
those functions may take locks and touch buffers that the fork duplicated. The
listing below writes with `write(2)` directly for that reason.

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
`posix_spawn` or `fork` plus `exec`, so the child never runs arbitrary Rust
between the two.

## `exec()` replaces the process image

`execve(path, argv, envp)` does not create a new PID. It destroys the current
process's address space and loads the new program, then starts execution at
its entry point. The file descriptor table survives unless `FD_CLOEXEC` is set
on a descriptor; that flag causes the descriptor to close automatically during
`exec`. Servers therefore set `O_CLOEXEC` on sockets and files.

```text
bash
 └─ fork()              # child bash process
     └─ execve("curl")  # child keeps PID but becomes curl
```

## What happens during a system call

A userspace program cannot touch hardware or kernel memory directly. A
function such as `read()` goes through the C library, or a raw `syscall`
instruction, and:

1. Places the syscall number and arguments in registers.
2. Executes `syscall` (x86-64) or `svc` (AArch64).
3. The CPU traps into kernel mode.
4. The kernel validates arguments, copies data from user pointers, executes the
   operation on the current task's kernel stack, and copies results back.
5. Control returns to user mode with a result in a register.

The kernel may sleep the task if the syscall blocks, such as waiting for
network data. When that happens, the scheduler runs another runnable task.
`strace` intercepts these syscalls and can show why a program is slow or why
it fails.

What makes the crossing expensive is that it is a privilege transition: the
CPU saves the user context, switches to the kernel stack, runs the entry path,
and switches back. That cost is paid before the operation itself does any
work, so even a call that does almost nothing is measurable.

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

That number belongs to one machine, one kernel, one frequency governor. The
same call on the same host, measured again at a different moment, reports
207.6 ns. A ten percent spread on a fixed instruction is the honest answer to
"how fast is a syscall," and it is the reason a measured figure should always
be printed beside the machine that produced it.

A server that issues one `read()` per 8 bytes pays more for crossings than for
copying. Batching (`sendmmsg`, `recvmmsg`, `io_uring`), mapping instead of
reading (`mmap`), and user-space networking (DPDK) all buy back the same
transition. `strace -c` counts the crossings the kernel actually handled, which
is why it is the first tool to reach for on a syscall-bound program.

The syscall number, the argument layout, and the error convention, `-1` plus
`errno`, are fixed for the architecture and constitute a published interface.
Binaries compiled years ago against a kernel that no longer exists still run
because of it. Linus Torvalds, on a proposed change that would have broken
that interface (LKML, 23 December 2012):

> WE DO NOT BREAK USERSPACE!
>
> Seriously. We've been doing this for decades. The fact that you don't
> understand why is not an excuse.

Extending a public API means adding rather than modifying, and giving a
version to anything that cannot be added. Kubernetes' own API versioning,
covered in Chapter 10, follows the same rule at a different scale.

## Process states, zombies, and orphans

The `STAT` column in `ps` is the state:

| State | Meaning |
|---|---|
| `R` | Running or runnable |
| `S` | Interruptible sleep (waiting for I/O or an event) |
| `D` | Uninterruptible sleep (usually waiting on kernel I/O) |
| `T` | Stopped (`SIGSTOP`) |
| `Z` | Zombie: exited but not yet reaped by the parent |
| `I` | Idle kernel thread |

A **zombie** is a task that has exited but whose `task_struct` is kept until
the parent calls `wait()`. The kernel must preserve the exit status for the
parent. If a parent never calls `wait()`, the child remains a zombie. If the
parent dies, the child is reparented to `init`/`systemd` (PID 1), which reaps
it.

A **D-state** process cannot be killed until the kernel I/O completes. Storage
and network hangs produce D-state processes, and the fix is the underlying
device rather than `kill -9`, which cannot interrupt uninterruptible sleep.

Field 3 of `/proc/<pid>/stat` is a single character, and it is the same
character `ps` prints in its `STAT` column. The program below forks a child,
deliberately does not reap it, and reads that field.

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

The child has no code left to run, yet it still occupies a slot in the process
table; that is what `Z` reports. `waitpid(2)` collects the exit status and the
kernel finally releases the `task_struct`. Without the `sleep`, the first read
often shows `R` or `S` instead, because the parent can reach the read before
the child has been scheduled; that race is why a zombie is confirmed by
re-reading rather than by reading once.

A container whose PID 1 never reaps orphans accumulates zombies until the
process-table limit, `/proc/sys/kernel/pid_max`, is reached. That is a bug in
the container's init handling, not a sign the kernel is misbehaving, and a
zombie itself holds a PID rather than any meaningful amount of memory.

## Signals and process control

Signals are software interrupts. The ones that come up most:

- `SIGTERM` (15): ask the process to exit; the process can clean up.
- `SIGKILL` (9): cannot be caught or blocked; the kernel destroys the task.
- `SIGSTOP` (19) / `SIGCONT` (18): stop and continue.
- `SIGHUP` (1): often means the terminal closed, or a request to reload
  configuration.
- `SIGCHLD`: sent to a parent when a child stops or exits.

Container runtimes use signals to stop containers: Kubernetes first sends
`SIGTERM` to PID 1 in the Pod, waits `terminationGracePeriodSeconds`, then
sends `SIGKILL`. Chapter 12 covers the rest of that sequence, including how a
sidecar container changes the order.

```bash
ps -eo pid,tid,ppid,stat,comm --sort=-%cpu | head
pstree -ap
pgrep -a python
kill -TERM 1234
kill -KILL 1234
renice -n -5 -p 1234
```

## References

- Kerrisk, *The Linux Programming Interface*, Chapter 24, "Process Creation."
- Arpaci-Dusseau, *Operating Systems: Three Easy Pieces*, Chapter 4, "The
  Abstraction: The Process," and Chapter 5, "Interlude: Process API."
- Love, *Linux Kernel Development*, on `task_struct`.
- The man pages for `fork(2)`, `clone(2)`, `execve(2)`, and `wait(2)`.
