# 11. Interprocess Communication

Threads share memory by construction; processes do not. Two processes
that need to cooperate — a shell and the program it runs, a server and
its workers — must use a channel the kernel provides. This chapter
builds the three classic channels: the pipe for byte streams, shared
memory for direct access with a process-shared lock, and the socketpair
for a bidirectional channel.

<div class="callout glance">
<span class="label">At a glance</span>

- A pipe is a kernel-buffered byte stream with a read end and a write
  end; `fork` inherits both, and each side closes the end it does not
  use.
- Shared memory maps one physical frame into two page tables; the
  processes synchronize with a process-shared mutex.
- A socketpair is a bidirectional pipe; both descriptors both read and
  write.

</div>

## 11.1 The pipe

`pipe` creates two descriptors: `fds[0]` reads, `fds[1]` writes. The
bytes travel through a bounded kernel buffer, first in, first out,
with no message boundaries — a stream, not a sequence of packets.
A reader blocks when the buffer is empty; a writer blocks when it is
full. The descriptors are ordinary file descriptors, so they are
inherited across `fork` exactly like any other, which is what makes
the pipe the shell's plumbing: `ls | wc` is a pipe with the two
programs at its ends.

Figure 11-1 draws one pipe between a parent and its child, with the
ends closed that neither side uses.

<figure>
<img src="diagrams/ch11_pipe.svg" alt="A kernel-buffered byte stream between a writing child and a reading parent"/>
</figure>

**Listing 11-1. One pipe, one fork, one message (C++20).**

```cpp
{{#include ../code/ch11/pipe.cpp}}
```

**Output 11-1.**

```text
{{#include ../code/out/ch11_pipe.out}}
```

**Listing 11-2. The same pipe in Rust.**

```rust
{{#include ../code/ch11/pipe.rs}}
```

**Output 11-2.**

```text
{{#include ../code/out/ch11_pipe_rs.out}}
```

The discipline is three rules. Close the end you do not use — a reader
sees end-of-file only when every write end is closed, and a forgotten
write end in the reading process means the reader waits forever after
the real writer exits. Read in a loop — a `read` may return fewer bytes
than requested, and the stream has no boundaries to tell you a message
ended. Treat `write` as possibly partial — the same loop, on the other
end.

<div class="callout caution">
<span class="label">Watch out</span>

A pipe carries bytes, not messages. If the protocol needs messages,
the program adds framing — a length prefix, a delimiter — at both
ends. `write` 10 bytes and `read` 10 bytes can return 3; the stream
guarantees order, never chunking.

</div>

## 11.2 Shared memory

A pipe copies: program to kernel, kernel to program. Shared memory
copies nothing — two page tables point at one physical frame, and both
processes load and store the bytes directly, as Figure 11-2 draws.

<figure>
<img src="diagrams/ch11_shm.svg" alt="Two page tables mapping one physical frame into two processes"/>
</figure>

The speed comes with the Chapter 4 problem in a new setting: two
processes, one counter, no isolation. The fix is the same idea with a
wider lock — a mutex whose **process-shared** attribute lets processes,
not just threads, take turns. The next listing places the mutex and the
counter in the shared frame, forks, and has parent and child each add
half a million.

**Listing 11-3. A counter in shared memory, guarded by a process-shared mutex (C++20).**

```cpp
{{#include ../code/ch11/shm_counter.cpp}}
```

**Output 11-3. Exact — across processes this time.**

```text
{{#include ../code/out/ch11_shm_counter.out}}
```

Two details carry the whole mechanism. `MAP_SHARED` makes the mapping
visible across the fork — the default `MAP_PRIVATE` would give each
process a private copy on first write, which is Chapter 3's
copy-on-write. And `PTHREAD_PROCESS_SHARED` extends the mutex's
ownership from a thread to a process, so the lock itself lives in the
shared frame and both processes contend on the same bytes.

<div class="callout keyidea">
<span class="label">Key idea</span>

The channel and the lock are separate choices. Pipes deliver data;
shared memory shares it. Either can carry the synchronization problem,
and a process-shared mutex placed in the shared region is the standard
solution.

</div>

## 11.3 The socketpair

A pipe is one-directional; a socketpair is the same buffer with both
directions. `socketpair` returns two descriptors, and each can both
read and write. The pair is how a parent and child maintain a private
two-way conversation — a control channel alongside a one-way data
pipe.

**Listing 11-4. A bidirectional channel: ping and pong (C++20).**

```cpp
{{#include ../code/ch11/socketpair.cpp}}
```

**Output 11-4. Each side writes one message and reads the other's.**

```text
{{#include ../code/out/ch11_socketpair.out}}
```

The output order deserves a glance: the child's line prints before the
parent's, because the parent's `printf` sat in its stdio buffer while
the child flushed and exited — Chapter 3's lesson, recurring. The data
itself is what matters: both directions, one pair of descriptors.

The three channels form the toolbox. A pipe moves bytes one way with
kernel buffering and blocking built in. Shared memory moves bytes not
at all, and the program brings its own synchronization. A socketpair
adds the second direction. Every larger IPC mechanism — message queues,
domain sockets, `signalfd`, event loops — is one of these three ideas
with a different interface. Chapter 14 generalizes the socketpair into
sockets that reach across machines; Chapter 13 gives the event loop
that serves many channels at once.

<div class="callout summary">
<span class="label">Summary</span>

- Pipes are kernel-buffered byte streams; close unused ends, loop on
  partial reads and writes, and frame messages yourself.
- Shared memory is one frame in two page tables; `MAP_SHARED` plus a
  process-shared mutex makes it safe.
- Socketpairs are bidirectional pipes — the standard control channel
  between related processes.
- The choice is copies versus synchronization: pipes pay copies and
  give order; shared memory pays a lock and gives speed.
- Chapter 12 turns to the durable side of data: files, inodes, and
  what `fsync` actually promises.

</div>
