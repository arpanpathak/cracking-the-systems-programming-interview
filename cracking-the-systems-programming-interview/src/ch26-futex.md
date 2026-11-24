<img class="plate" src="art/ch26.png" alt="Latch, the robot who is the keeper of the sleeping queue, beside a gate latch on a single brass word, with a bench of sleeping robots behind it under a lamp">

# Futexes and memory ordering

<div class="covers" markdown="1">

This chapter covers

- The Linux futex: a kernel wait queue keyed by the virtual or physical address of a user-space atomic word
- A three-state sleeping mutex whose uncontended fast path executes entirely in user space without system calls
- Atomic value verification inside `futex_wait` and elimination of the lost-wakeup race
- Empirical system-call and throughput comparison against `std::sync::Mutex` under single- and multi-threaded contention
- Hardware store buffers and store-load memory reordering under x86 total store order (TSO)
- Million-iteration litmus tests for store buffering and message passing across `Relaxed`, `Release`/`Acquire`, and `SeqCst`

</div>

A user-space spin lock (Chapter 16) minimizes latency for nanosecond-scale critical sections, but wastes CPU cycles and degrades scheduling throughput whenever a lock is held across blocking I/O or preempted by the scheduler. Scalable mutual exclusion requires a hybrid design: an uncontended user-space fast path that acquires and releases the lock via single atomic instructions, paired with a kernel-assisted slow path that deschedules contending threads onto a wait queue until release. On Linux, this boundary is implemented by the **futex** (fast user-space mutex) system call, whose correctness rests directly on the underlying hardware memory model.

Two reference programs examine both layers of synchronization. `futex_mutex` constructs a three-state sleeping mutex over raw `SYS_futex` calls, counting exact `futex_wait` and `futex_wake` invocations against `std::sync::Mutex`. `litmus` executes one million synchronized rounds each of the store-buffering and message-passing litmus tests, measuring hardware memory reordering rates across atomic orderings.

## 26.1 Sleeping on a word

A **futex** is a kernel wait queue hashed by the address of a 32-bit atomic word residing in user-space memory. The kernel assigns no semantic meaning to the integer's value; user space defines the state machine, while the kernel provides two wait-queue primitives:

- **`futex_wait(addr, expected)`**: atomically verifies that the 32-bit word at `addr` still equals `expected`; if so, it enqueues the calling thread on the kernel wait queue for `addr` and deschedules it. If the word holds any other value, the call returns immediately with `EAGAIN`.
- **`futex_wake(addr, n)`**: dequeues and wakes up to `n` threads currently sleeping on the wait queue associated with `addr`.

Because the lock state word resides in user space (Figure 26.1), acquiring an uncontended lock requires a single atomic compare-and-swap instruction with zero kernel transitions. A thread invokes `futex_wait` only upon contention, and `unlock` invokes `futex_wake` only when the state word indicates that sleeping waiters may exist.

<figure>
<img src="figures/ch26-futex.svg" alt="In user space, thread A holds the lock and the state word holds 2, locked with waiters. Thread B's swap(2) returned 1, so B calls futex_wait(&state, 2) and sleeps on the kernel's queue for that address. A unlocks with swap(0), which returns 2, so A calls futex_wake(&state, 1).">
<figcaption><b>Figure 26.1</b> The lock word lives in the program. The kernel keeps only the queue of threads asleep on its address.</figcaption>
</figure>

### 26.1.1 Why the kernel checks the word

`futex_wait` performs the comparison `*addr == expected` and wait-queue insertion under the kernel's internal hash-bucket spinlock. Without that atomic verification, the following interleaving produces a permanent deadlock:

1. Thread B reads the lock word, observes it held, and decides to sleep.
2. Thread A releases the lock, updates the word to unlocked, and invokes `futex_wake`. Because Thread B has not yet entered the wait queue, `futex_wake` wakes zero threads.
3. Thread B enters the kernel wait queue and sleeps indefinitely with no future waker.

With the atomic check in place, step 3 detects that `*addr != expected`, aborts the sleep, and returns immediately so Thread B can retry acquisition. This race is the classic **lost wake-up** hazard, identical in structure to the reason POSIX condition variables (`Condvar`, Chapter 16) require an associated mutex.

## 26.2 A mutex with three states

A minimal sleeping mutex encodes three states in its 32-bit atomic word (Figure 26.2):

- **0 (`UNLOCKED`)**: the lock is free.
- **1 (`LOCKED`)**: the lock is held, with no known contending waiters.
- **2 (`CONTENDED`)**: the lock is held, and one or more threads may be sleeping in `futex_wait`.

Distinguishing states 1 and 2 enables `unlock` to elide `futex_wake` on the uncontended path: transitioning from 1 to 0 requires a single atomic instruction, whereas transitioning from 2 to 0 additionally invokes `futex_wake`.

<figure>
<img src="figures/ch26-states.svg" alt="State 0, unlocked, goes to 1, locked, by compare_exchange(0, 1) with no system call. 1 goes back to 0 by swap(0) returning 1, with no system call. A second thread moves 1 to 2 with swap(2) and then futex_wait. Unlock from 2 is swap(0) returning 2, then futex_wake. A woken thread's swap(2) returning 0 takes the lock in state 2.">
<figcaption><b>Figure 26.2</b> The three states. The two transitions between 0 and 1 are the uncontended path, and make no system call.</figcaption>
</figure>

### 26.2.1 The system calls

Because `libc` exposes no typed wrapper for `futex`, the program invokes `SYS_futex` through the generic variadic `syscall` interface:

```rust
unsafe extern "C" {
    fn syscall(number: c_long, ...) -> c_long;
}

// The futex call, as the kernel defines its arguments:
// syscall(SYS_futex, uaddr: *const u32, op: c_int, val: u32, timeout: *const timespec)
//   FUTEX_WAIT: sleep if *uaddr == val, until woken or until the timeout (null: none)
//   FUTEX_WAKE: wake up to val threads sleeping on uaddr; timeout is unused
```

The wait and wake wrappers encapsulate the raw system calls:

```rust
{{#include ../../rust-interview-lab/src/bin/futex_mutex.rs:10:53}}
    // ...
}
```

Passing `FUTEX_PRIVATE_FLAG` informs the kernel that the futex word is not shared across process address spaces, allowing the kernel to hash the wait queue by virtual address without inspecting shared-memory page tables. `AtomicU32::as_ptr` yields the stable address of the underlying 32-bit word. `futex_wait` ignores its return code because callers must already tolerate spurious wakeups (such as `EINTR` from signal delivery) by re-evaluating the lock word in a loop.

### 26.2.2 `lock` and `unlock`

`FutexMutex<T>` bundles the 32-bit state word, atomic telemetry counters for wait and wake system calls, and the `UnsafeCell<T>` holding the protected payload:

```rust
mod linux {
    // ...
{{#include ../../rust-interview-lab/src/bin/futex_mutex.rs:55:75}}
        // ...
}
```

As with the spin lock in Chapter 16, `unsafe impl Sync` upholds the soundness invariant that at most one thread holds a mutable reference to `value` at any instant. `lock` returns an RAII `Guard` that releases the mutex on drop. Acquisition attempts the uncontended fast path before falling back to `lock_contended`:

```rust
mod linux {
    // ...
    impl<T> FutexMutex<T> {
        // ...
{{#include ../../rust-interview-lab/src/bin/futex_mutex.rs:77:101}}
        // ...
    }
    // ...
}
```

`compare_exchange(UNLOCKED, LOCKED, Acquire, Relaxed)` claims an uncontended lock in one atomic instruction. On failure, `lock_contended` executes `swap(CONTENDED, Acquire)`: if the previous state was `UNLOCKED` (0), the caller has acquired the lock; otherwise, the caller sleeps via `futex_wait(CONTENDED)` and loops upon wakeup.

A thread acquiring the lock via `lock_contended` deliberately leaves the state word at `CONTENDED` (2) even if no other threads remain asleep. Because user space cannot observe the kernel wait queue's length atomically, preserving state 2 prevents a lost wakeup at the cost of an occasional redundant `futex_wake` on an empty queue.

`unlock` executes `swap(UNLOCKED, Release)`, establishing a happens-before relationship that publishes all critical-section writes to the next acquiring thread (Section 16.4.3). If the prior state was `CONTENDED`, `unlock` invokes `futex_wake(&self.state, 1)` to wake a single waiter.

The `Guard` implementation provides `Deref`, `DerefMut`, and automatic unlock in `Drop`:

```rust
mod linux {
    // ...
{{#include ../../rust-interview-lab/src/bin/futex_mutex.rs:113:138}}
}
```

Animation 26.1 traces two threads across all three states and illustrates the lost-wakeup deadlock when the atomic word check is omitted.

<figure class="anim">
<video class="motion" src="figures/ch26-futex.mp4" autoplay loop muted playsinline preload="metadata" aria-label="Two thread robots, A and B, beside the lock word, with the kernel's wait queue for the word's address below. A's compare_exchange changes 0 to 1 without entering the kernel. B's compare_exchange fails; B swaps in 2, sees 1, and calls futex_wait(&state, 2). The kernel checks that the word holds 2, and B sleeps on the queue. A unlocks: swap(0) returns 2, so A calls futex_wake and B wakes. B's swap(2) returns 0, so B holds the lock, with the word at 2. B's unlock returns 2 and calls futex_wake, which finds nobody. In a last run the kernel does not check the word: B sees the lock held, A unlocks and wakes an empty queue, then B joins the queue and sleeps forever." data-chapters="[[0.0, &quot;fast path&quot;], [7.14, &quot;B waits&quot;], [26.78, &quot;wake&quot;], [52.06, &quot;no check&quot;]]"><img src="figures/ch26-futex.gif" alt="Two thread robots, A and B, beside the lock word, with the kernel's wait queue for the word's address below. A's compare_exchange changes 0 to 1 without entering the kernel. B's compare_exchange fails; B swaps in 2, sees 1, and calls futex_wait(&state, 2). The kernel checks that the word holds 2, and B sleeps on the queue. A unlocks: swap(0) returns 2, so A calls futex_wake and B wakes. B's swap(2) returns 0, so B holds the lock, with the word at 2. B's unlock returns 2 and calls futex_wake, which finds nobody. In a last run the kernel does not check the word: B sees the lock held, A unlocks and wakes an empty queue, then B joins the queue and sleeps forever."></video>
<figcaption><b>Animation 26.1</b> The uncontended path stays in user space. A waiter sleeps in the kernel, and the check of the word inside <code>futex_wait</code> keeps a wake-up from being lost.</figcaption>
</figure>

### 26.2.3 Measured

`main` executes one million counter increments under both `FutexMutex` and `std::sync::Mutex`, partitioned across 1, 2, and 4 threads inside a two-vCPU Linux container:

```text
$ cargo run --release --bin futex_mutex
threads     total    waits    wakes     futex ms       std ms
      1   1000000        0        0         30.8         25.1
      2   1000000    23712    59752         64.4         56.2
      4   1000000    28006    71826         71.0         56.1
```

At one thread, one million lock-unlock cycles executed with zero kernel transitions, averaging approximately 30 ns per cycle. At two threads, roughly 2.4% of acquisitions entered `futex_wait`, while `futex_wake` executed 2.5 times as frequently as `futex_wait` due to the conservative `CONTENDED` state preservation in `lock_contended`.

Although `std::sync::Mutex` on Linux implements the identical three-state futex protocol, it achieved lower wall-clock latency under contention by performing a brief adaptive spin (up to 100 iterations of relaxed loads) before invoking `futex_wait`. When critical sections last only a few nanoseconds, short-duration spinning absorbs transient contention without incurring two system calls and a context switch. Because container scheduling introduces 10% or greater variance in wall-clock duration across runs (one four-thread `std::sync::Mutex` run measured 214 ms), the deterministic `waits` and `wakes` counters provide the primary behavioral signal.

## 26.3 What the hardware reorders

Section 16.2.3 defined the Rust/C++ memory model contracts: `Relaxed` enforces atomicity without ordering constraints on surrounding memory accesses, `Release`/`Acquire` establishes pairwise happens-before edges, and `SeqCst` enforces a single total modification order across all sequentially consistent operations. Those abstract rules exist because physical processors reorder memory operations to hide cache-coherence latency.

### 26.3.1 Store buffers

Committing a store directly to a coherent L1 cache stalls the pipeline whenever the target cache line resides exclusively in another core's cache. To mask this coherence latency, modern superscalar cores enqueue outgoing stores in a private FIFO **store buffer** and immediately retire subsequent instructions while the store drains asynchronously to cache. A core's own loads perform **store-to-load forwarding** from its local store buffer (preserving single-thread program semantics), whereas remote cores observe a store only after it drains into the coherent cache hierarchy.

Consequently, a load to address $y$ that follows a store to address $x$ in program order can execute and read from cache before the earlier store to $x$ becomes globally visible. Figure 26.3 depicts two cores executing this symmetric pattern concurrently: both loads observe the stale value `0` from memory while both stores remain queued in their private store buffers.

<figure>
<img src="figures/ch26-store-buffer.svg" alt="Core 1 stores x = 1 and core 2 stores y = 1; both stores wait in their cores' store buffers. Core 1 loads y and core 2 loads x from cache and memory, where x and y are still 0. Both loads read 0. The buffers drain later.">
<figcaption><b>Figure 26.3</b> Both stores wait in store buffers while both loads read memory. Each thread's load completes before its own store is visible.</figcaption>
</figure>

Animation 26.2 contrasts one round of store-buffer reordering under `Relaxed` against the drained serialization enforced by `SeqCst`.

<figure class="anim">
<video class="motion" src="figures/ch26-store-buffer.mp4" autoplay loop muted playsinline preload="metadata" aria-label="Two thread robots on cores 1 and 2, each with a store buffer below, and cache and memory between them holding x = 0 and y = 0. With Relaxed, thread 1's store x = 1 goes into its buffer, and thread 2's store y = 1 into its own. Thread 1 loads y from memory and reads 0; thread 2 loads x and reads 0. Only then do the buffers drain, and memory holds x = 1 and y = 1, with r1 = 0 and r2 = 0. With SeqCst, thread 1's store waits for its buffer to drain before the core continues, so x = 1 is in memory before thread 1 loads y and reads 0. Thread 2 stores y the same way and then loads x, which reads 1." data-chapters="[[0.0, &quot;Relaxed&quot;], [32.99, &quot;SeqCst&quot;]]"><img src="figures/ch26-store-buffer.gif" alt="Two thread robots on cores 1 and 2, each with a store buffer below, and cache and memory between them holding x = 0 and y = 0. With Relaxed, thread 1's store x = 1 goes into its buffer, and thread 2's store y = 1 into its own. Thread 1 loads y from memory and reads 0; thread 2 loads x and reads 0. Only then do the buffers drain, and memory holds x = 1 and y = 1, with r1 = 0 and r2 = 0. With SeqCst, thread 1's store waits for its buffer to drain before the core continues, so x = 1 is in memory before thread 1 loads y and reads 0. Thread 2 stores y the same way and then loads x, which reads 1."></video>
<figcaption><b>Animation 26.2</b> With <code>Relaxed</code>, both loads run while both stores are still buffered. A <code>SeqCst</code> store drains the buffer first, so the later load of the other thread sees it.</figcaption>
</figure>

x86-64 processors implement **total store order (TSO)**: hardware preserves store-store, load-load, and load-store order, permitting only store-load reordering via store buffers. Weakly ordered architectures such as ARM64 (Apple Silicon, AWS Graviton) permit store-store and load-load reordering as well. Independently of hardware strength, optimizing compilers may freely reorder `Relaxed` memory accesses on any target architecture.

### 26.3.2 The litmus tests

A **litmus test** is a minimal two-thread concurrent program designed to detect whether a specific non-sequentially-consistent outcome occurs on target hardware. Each harness allocates fresh atomic variables per round to eliminate reset synchronization and aligns both threads at a spin barrier before every iteration so their memory instructions overlap in time:

```rust
{{#include ../../rust-interview-lab/src/bin/litmus.rs:9:34}}
```

`meet` implements a single-counter spin barrier: each thread increments the shared counter and spins until the count reaches the threshold for the current round.

The **store-buffering (SB)** litmus test implements Figure 26.3 directly, counting rounds in which both threads observe `0`:

```rust
{{#include ../../rust-interview-lab/src/bin/litmus.rs:36:63}}
```

The **message-passing (MP)** litmus test publishes a payload word followed by a readiness flag, counting rounds in which the consumer observes the flag set (`1`) alongside stale payload data (`0`):

```rust
{{#include ../../rust-interview-lab/src/bin/litmus.rs:65:93}}
```

Message passing is the foundational synchronization idiom behind locks, channels, and publication queues, relying on a `Release` store paired with an `Acquire` load (Section 16.4.3).

Executed on an Intel x86-64 processor:

```text
$ cargo run --release --bin litmus
store buffering, 1000000 rounds: both loads read 0
  Relaxed               14472
  Release / Acquire     15019
  SeqCst                    0

message passing, 1000000 rounds: flag read as 1, data read as 0
  Relaxed                   0
  Release / Acquire         0
  SeqCst                    0
```

A Linux container on the same host recorded 6,342 and 5,045 store-buffering reorderings, with zero anomalies elsewhere. These measurements confirm three architectural properties:

- **Store-load reordering is empirically frequent.** Approximately 1.5% of rounds observed `r1 == 0 && r2 == 0` under `Relaxed`. Upgrading to `Release`/`Acquire` produced the same reordering rate: `Release` prevents prior accesses from moving after a store and `Acquire` prevents subsequent accesses from moving before a load, but neither prevents a subsequent load from bypassing a prior store.
- **`SeqCst` eliminates store-load reordering.** On x86-64, a `SeqCst` store compiles to a locked instruction (`xchg`) or `mov` followed by `mfence`, draining the core's store buffer before subsequent loads issue. Every `SeqCst` access then participates in a global total order, guaranteeing that at least one store precedes the opposing load.
- **Passing tests on x86-64 do not prove memory-ordering soundness.** Message passing recorded zero failures under `Relaxed` solely because x86-64 TSO forbids hardware store-store and load-load reordering. The `Relaxed` implementation remains formally incorrect: it fails empirically on ARM64 hardware and permits compiler reordering on all architectures.

## 26.4 The complete programs

<p class="listing"><b>Listing 26.1</b> A mutex on the futex system call. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/futex_mutex.rs">src/bin/futex_mutex.rs</a></p>

```rust
{{#include ../../rust-interview-lab/src/bin/futex_mutex.rs}}
```

<p class="listing"><b>Listing 26.2</b> Store buffering and message passing, a million rounds each. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/litmus.rs">src/bin/litmus.rs</a></p>

```rust
{{#include ../../rust-interview-lab/src/bin/litmus.rs}}
```

## 26.5 Questions that come up

**"Why not always spin, or always sleep?"**
Pure spinning burns CPU cycles for the entire duration of a hold and starves other runnable threads when a lock holder is preempted. Pure sleeping incurs two system calls and a context switch (microseconds) even when the lock is released nanoseconds later. Adaptive hybrid locks (brief user-space spinning followed by a `futex_wait` sleep, as implemented in `std::sync::Mutex`) optimize for both regimes.

**"What is priority inversion, and does a futex help?"**
Priority inversion occurs when a high-priority thread blocks on a lock held by a low-priority thread while a medium-priority thread preempts the low-priority holder indefinitely. Linux provides priority-inheritance futexes (`FUTEX_LOCK_PI`), which temporarily elevate the lock holder's scheduling priority to match the highest-priority waiter until release.

**"Can a futex be shared between processes?"**
Yes. Placing the atomic 32-bit word in a shared memory region (such as a `MAP_SHARED` mapping from Section 23.2) and omitting `FUTEX_PRIVATE_FLAG` instructs the kernel to key the wait queue by physical page and offset rather than process-local virtual address.

**"When is `Relaxed` correct?"**
`Relaxed` is sound when no other memory access depends on the ordering of the atomic operation (for example, monotonic telemetry counters or unique identifier generation via `fetch_add`). Whenever an atomic value signals that accompanying memory is initialized or ready, `Release`/`Acquire` synchronization is mandatory.

**"When is `SeqCst` needed?"**
`SeqCst` is required when correctness depends on a single global total order across distinct atomic variables, as in Dekker's mutual-exclusion algorithm or work-stealing deque synchronization (the store-buffering pattern). Code structured around mutexes, channels, and pairwise `Release`/`Acquire` publication rarely requires `SeqCst`.

<div class="summary" markdown="1">

## Summary

- A futex is a kernel wait queue keyed by the address of a 32-bit user-space atomic word. `futex_wait` atomically verifies the word's value before descheduling the caller, preventing lost wake-ups.
- A three-state mutex (`UNLOCKED`, `LOCKED`, `CONTENDED`) executes uncontended acquisition and release with a single atomic instruction each, entering the kernel only to block or wake waiters.
- One million single-threaded increments incurred zero system calls; under contention, conservative retention of the `CONTENDED` state produced more `futex_wake` calls than `futex_wait` calls.
- `std::sync::Mutex` reduces contention overhead relative to a purely sleeping futex by spinning briefly before entering the kernel.
- Processor store buffers allow a subsequent load to execute before an earlier store drains to coherent cache; x86-64 TSO permits this single reordering, whereas ARM64 permits store-store and load-load reordering as well.
- Store buffering observed both loads reading `0` in roughly 1.5% of a million rounds under `Relaxed` and `Release`/`Acquire`, and zero times under `SeqCst`. Message passing recorded zero failures on x86-64 due to TSO, which does not make `Relaxed` sound.

</div>

## Exercises

1. Add an adaptive spin loop to `lock_contended` (up to 100 `Relaxed` loads terminating early upon observing `UNLOCKED`) before executing the first `swap`. Compare the resulting `waits`, `wakes`, and wall-clock timings against the table in Section 26.2.3.
2. Insert a 50-microsecond busy loop inside the critical section and execute four threads. Compare `FutexMutex` against the Chapter 16 spin lock in both wall-clock duration and total CPU time (`/usr/bin/time -v`).
3. Defeat the `expected` verification by passing a constant mismatch value (such as `7`) to `futex_wait`. Explain why CPU utilization spikes to 100% per thread.
4. Change the message-passing test to `Relaxed` for both threads and execute it on an `aarch64` processor. Record the number of reordered rounds.
5. Implement the **load-buffering (LB)** litmus test: Thread 1 loads `x` then stores `y = 1`, while Thread 2 loads `y` then stores `x = 1`. Determine whether `r1 == 1 && r2 == 1` is possible under `Relaxed` on x86-64 and justify the observed result.
