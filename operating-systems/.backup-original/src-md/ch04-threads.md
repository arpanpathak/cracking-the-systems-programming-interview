# 4. Threads

A process can do one thing at a time, unless it is given more threads. A
**thread** is a schedulable stream of instructions: its own program
counter, its own registers, its own stack — and the process's everything
else. One process, several threads, several things happening at once. This
chapter creates threads, measures what goes wrong when they share a
variable, and shows the instruction that makes sharing safe.

<div class="callout glance">
<span class="label">At a glance</span>

- Threads share the address space; each keeps its own stack and registers.
- An unsynchronized increment is three machine operations, and the
  interleaving loses updates — measurably.
- The atomic increment collapses the three operations into one
  read-modify-write at the hardware level.

</div>

## 4.1 One address space, several stacks

Figure 4-1 states the contract precisely.

<figure>
<img src="diagrams/ch04_threads.svg" alt="A single-threaded process versus a process with three threads sharing text, data, and heap"/>
</figure>

What is shared: the code, the globals, the heap, the file descriptors.
What is private: the stack and the registers. Two consequences follow.

The good one: threads communicate by writing shared memory. No copying, no
kernel round trip — a producer thread stores a value, a consumer thread
loads it. Chapter 6 builds its synchronization machinery on exactly this
property.

The bad one: nothing separates two threads touching the same variable at
the same time. The address space is shared by design, so the hardware's
usual isolation between processes does not exist between threads. Every
shared variable is a potential race, and the compiler, the caches, and the
scheduler all conspire to make the race real.

<div class="callout keyidea">
<span class="label">Key idea</span>

Threads share memory by construction, so synchronization is the
programmer's responsibility, not the hardware's. A process's isolation is
enforced for it; a thread's is not.

</div>

## 4.2 The race, observed

Chapter 2 reduced an increment to three instructions:

```asm
load  r1, [counter]   ; read
add   r1, r1, 1       ; modify
store [counter], r1   ; write
```

Two threads executing this sequence against one `counter` can interleave
their three steps. The losing interleaving is Figure 4-2: both threads
load the same old value, both add one, both store — one increment is lost.
The window is wide, and in a tight loop over millions of iterations it is
hit constantly.

<figure>
<img src="diagrams/ch04_race_timeline.svg" alt="Timeline showing two threads loading 42, adding 1, and storing 43, losing one increment"/>
</figure>

The next listing runs eight threads, each incrementing one shared counter
twenty million times. The expected result is 160,000,000.

**Listing 4-1. Eight threads, one counter, no synchronization (C++20).**

```cpp
{{#include ../code/ch04/race.cpp}}
```

**Output 4-1. The observed value varies from run to run; it is never 160,000,000.**

```text
{{#include ../code/out/ch04_race.out}}
```

The counter is declared `volatile`, and that deserves a precise comment.
`volatile` does not make the increment atomic and does not synchronize
threads. It forces each read and each write to reach memory instead of
being optimized away, which widens the race window and makes the loss
reliably visible. Production code must not treat `volatile` as a
concurrency primitive.

The Rust listing constructs the same race deliberately. Because Rust
forbids shared mutable state through its type system, the program reaches
for the escape hatch: a `static mut` and `unsafe` blocks, with volatile
reads and writes through raw pointers.

**Listing 4-2. The same race, through Rust's escape hatch.**

```rust
{{#include ../code/ch04/race.rs}}
```

**Output 4-2.**

```text
{{#include ../code/out/ch04_race_rs.out}}
```

Both outputs lose about seventy percent of the increments. The exact number
depends on scheduling and cache traffic, which is the honest signature of
a data race: nondeterministic, run-dependent, and wrong.

## 4.3 The atomic increment

The fix is to make the read-modify-write one operation. Processors provide
exactly such instructions — `lock xadd` on x86, `ldaddal` on arm64 — which
perform the load, the arithmetic, and the store atomically with respect to
every other core's memory operations. C++ and Rust both expose them
through **atomic types**.

**Listing 4-3. The same counter with `std::atomic` (C++20).**

```cpp
{{#include ../code/ch04/race_atomic.cpp}}
```

**Output 4-3. Exact, every run.**

```text
{{#include ../code/out/ch04_race_atomic.out}}
```

**Listing 4-4. The atomic counter in Rust.**

```rust
{{#include ../code/ch04/race_atomic.rs}}
```

**Output 4-4.**

```text
{{#include ../code/out/ch04_race_atomic_rs.out}}
```

The `fetch_add` call compiles to the locked instruction. The
`std::memory_order_relaxed` argument — `Ordering::Relaxed` in Rust — asks
for atomicity of the increment itself and nothing more; it does not order
the increment against any other variable. Chapter 6 explains when more
ordering is needed. For a standalone counter, relaxed is correct and
fastest.

<div class="callout note">
<span class="label">Atomicity versus ordering</span>

Atomicity answers one question: can another thread observe this operation
half-done? Ordering answers another: in what order do operations on
different variables become visible? `fetch_add` with relaxed ordering
provides only the first. Both languages make the distinction explicit,
and Chapter 6 builds mutexes and condition variables on top of it.

</div>

## 4.4 Creating and joining threads

The remaining mechanics are small. A thread is created by handing a
function to the threading facility; it is joined by waiting for that
function to return. The next pair of listings runs four threads that each
print one line.

**Listing 4-5. Four threads, one process (C++20).**

```cpp
{{#include ../code/ch04/threads.cpp}}
```

**Output 4-5. The order varies; the lines stay intact.**

```text
{{#include ../code/out/ch04_threads.out}}
```

Each `operator<<` on `std::cout` locks independently, so without the
mutex the fragments of different threads could interleave mid-line — the
output might read `thread thread 01 running running`. The mutex in the
listing makes the whole line one unit. The mutex itself is Chapter 6's
subject; here it only protects the printer.

**Listing 4-6. The same four threads in Rust.**

```rust
{{#include ../code/ch04/threads.rs}}
```

**Output 4-6.**

```text
{{#include ../code/out/ch04_threads_rs.out}}
```

Rust's `println!` locks the standard output for the whole call, so no
mutex is needed for intact lines. The pattern is otherwise identical:
spawn, then join. `join` waits for the thread's function to finish and
propagates its result or its panic; a thread that is neither joined nor
detached triggers a run-time error on process exit, because its stack
would be abandoned mid-frame.

One practical contrast closes the chapter. Threads share the heap, so a
C++ lambda can capture shared state by reference, as Listing 4-1 does, and
nothing stops it. Rust's `thread::spawn` requires the closure to own its
data or share it through a reference-counted, synchronized wrapper like
`Arc` — the type system refuses to compile Listing 4-2's pattern without
`unsafe`. Chapter 6 shows the safe version of shared state in both
languages.

<div class="callout summary">
<span class="label">Summary</span>

- Threads share everything except stack and registers; that sharing is
  their speed and their danger.
- An increment is load–add–store; interleaved across threads it loses
  updates. The loss is measurable and run-dependent.
- `volatile` widens the window but fixes nothing; atomic `fetch_add`
  compiles to a locked read-modify-write and fixes everything.
- Spawn to start a thread, join to wait for it; protect multi-fragment
  output with a mutex (C++) or rely on `println!`'s internal lock (Rust).
- Scheduling decides the interleaving; Chapter 5 explains the scheduler,
  and Chapter 6 the synchronization primitives.

</div>
