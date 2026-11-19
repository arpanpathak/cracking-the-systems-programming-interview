# 11. Interprocess Communication

Threads of one process share memory, so they can exchange data through
ordinary variables. Two processes have separate address spaces and cannot
do so. When processes need to cooperate, as a shell does with the programs
it starts or a server with its worker processes, they exchange data
through a channel that the kernel provides. Such channels are known as
**interprocess communication**, or IPC.

In this chapter, we use three kinds of channels. A pipe carries a stream
of bytes in one direction. Shared memory lets two processes read and write
the same bytes, and we protect it with a mutex that works across
processes. A socket pair carries bytes in both directions.

<div class="callout glance">
<span class="label">This chapter covers</span>

- pipes, their two ends, and end-of-file
- partial reads and writes, and message framing
- shared memory with `mmap` and `MAP_SHARED`
- a mutex shared between processes
- `socketpair`
- how to choose among the three

</div>

## 11.1 The pipe

A **pipe** is a buffer inside the kernel with two file descriptors. The
call `pipe(fds)` creates one and stores the descriptor for reading in
`fds[0]` and the descriptor for writing in `fds[1]`. Bytes written to
`fds[1]` can be read from `fds[0]` in the same order. The buffer has a
fixed capacity. A `read` blocks while the buffer is empty, and a `write`
blocks while it is full.

A pipe carries a *stream* of bytes. It does not preserve the boundaries
between separate `write` calls. For example, if a writer makes two calls
of 5 bytes each, a reader may receive all 10 bytes from one `read`.

Pipe descriptors are ordinary file descriptors, so a child created by
`fork` inherits them. A typical use is therefore to create a pipe, call
`fork`, and let one process write while the other reads. A shell runs
`ls | wc` in this way, with `ls` writing to a pipe and `wc` reading from
it. Figure 11-1 shows a pipe between a child that writes and a parent that
reads.

<figure>
<img src="figures/ch11_pipe.svg" alt="A kernel-buffered byte stream between a writing child and a reading parent"/>
</figure>

**Listing 11-1. One pipe, one fork, and one message (C++20).**

```cpp
{{#include ../code/ch11/pipe.cpp}}
```

**Output 11-1.**

```text
{{#include ../code/out/ch11_pipe.out}}
```

**Listing 11-2. The same program in Rust.**

```rust
{{#include ../code/ch11/pipe.rs}}
```

**Output 11-2.**

```text
{{#include ../code/out/ch11_pipe_rs.out}}
```

A program that uses a pipe should follow three rules.

1. **Close the end that the process does not use.** A reader receives
   end-of-file only when every descriptor for the write end has been
   closed. After `fork`, both processes hold both descriptors. If the
   reading process keeps its copy of the write end open, its `read` never
   returns end-of-file, even after the writer has exited.
2. **Call `read` in a loop.** A `read` may return fewer bytes than the
   program requested, so the program must continue until it has all the
   bytes it expects.
3. **Call `write` in a loop.** A `write` may also transfer fewer bytes
   than requested.

<div class="callout caution">
<span class="label">Watch out</span>

A pipe delivers bytes in order, but it does not mark where one message
ends and the next begins. A protocol that needs messages must add
*framing*. Common choices are a length field before each message or a
delimiter byte after it.

</div>

## 11.2 Shared memory

A pipe copies data twice, from the writer into the kernel buffer and from
that buffer into the reader. **Shared memory** avoids both copies. The
kernel maps the same physical frame into the address spaces of two
processes, as Figure 11-2 shows. A byte that one process stores in the
shared page can be loaded by the other with no system call.

<figure>
<img src="figures/ch11_shm.svg" alt="Two page tables mapping one physical frame into two processes"/>
</figure>

With shared memory, two processes can now write to the same variable,
which is the data race of Chapter 4 in a new form. We solve it in the same
way, with a mutex, but an ordinary mutex works only among the threads of
one process. POSIX mutexes have an attribute, `PTHREAD_PROCESS_SHARED`,
that allows threads of different processes to lock the same mutex. Such a
mutex must itself be stored in the shared memory.

Listing 11-3 maps one shared page and places a process-shared mutex and a
counter in it. After a `fork`, the parent and the child each increment the
counter 500,000 times.

**Listing 11-3. A counter in shared memory, protected by a process-shared mutex (C++20).**

```cpp
{{#include ../code/ch11/shm_counter.cpp}}
```

**Output 11-3. The counter reaches exactly 1,000,000.**

```text
{{#include ../code/out/ch11_shm_counter.out}}
```

Two flags are essential in this listing. The first is `MAP_SHARED` in the
call to `mmap`. With the alternative, `MAP_PRIVATE`, the kernel would
apply copy-on-write after the `fork`, and each process would increment a
private copy of the counter. The second is `PTHREAD_PROCESS_SHARED` in the
attributes of the mutex, as described above.

<div class="callout keyidea">
<span class="label">Key idea</span>

Shared memory transfers data without copying, but it does not coordinate
the processes that use it. A program that shares memory must also share a
lock, and a process-shared mutex stored in the shared region serves that
purpose.

</div>

## 11.3 The socket pair

A pipe carries data in one direction only. The call `socketpair` creates
two connected descriptors that carry data in both directions. Bytes
written to one descriptor can be read from the other, and each descriptor
can be used for both reading and writing. A parent and a child often use a
socket pair as a private two-way channel, for example to exchange
commands and replies.

**Listing 11-4. A two-way channel between parent and child (C++20).**

```cpp
{{#include ../code/ch11/socketpair.cpp}}
```

**Output 11-4. Each process sends one message and receives the other.**

```text
{{#include ../code/out/ch11_socketpair.out}}
```

The child sends `ping from child` and receives `pong from parent`. The
line of the child appears first in the output, because the child exits,
and thereby flushes its stdio buffer, before the parent does.

Table 11-1 compares the three channels.

**Table 11-1. Three IPC channels.**

| Channel | Direction | Copies | Blocking and order |
|---|---|---|---|
| pipe | one way | two per transfer | provided by the kernel |
| shared memory | both | none | the program must synchronize |
| socket pair | both | two per transfer | provided by the kernel |

A pipe or a socket pair is the simpler choice, because the kernel blocks
readers and writers as needed and delivers bytes in order. Shared memory
is faster for large amounts of data, but the program must supply its own
locking. In Chapter 14, we extend the socket pair to sockets that connect
processes on different machines. In Chapter 13, we handle many channels
in one thread.

<div class="callout summary">
<span class="label">Summary</span>

- A pipe is a kernel buffer that carries a byte stream in one direction.
  Each process closes the end it does not use, and both sides call `read`
  and `write` in loops.
- A pipe does not preserve message boundaries. A protocol adds framing
  when it needs messages.
- Shared memory maps one frame into two processes. It requires
  `MAP_SHARED` and a mutex with `PTHREAD_PROCESS_SHARED`.
- A socket pair is a channel in both directions between related
  processes.

Data in a pipe or in shared memory disappears when the processes exit. In
Chapter 12, we study files, which keep data on a storage device.

</div>
