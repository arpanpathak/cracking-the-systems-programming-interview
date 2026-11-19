# 4. Threaded Execution and Concurrency Hazards

While a process provides a fundamental unit of isolation, it is often
insufficient for expressing fine-grained parallelism. To achieve
concurrency within a single execution context, a process employs threads,
independent sequences of instructions that operate within the same
administrative boundaries.

<div class="callout glance">
<span class="label">This chapter covers</span>

- the private and shared state of a thread
- a data race on a shared counter, with measured loss
- the limited role of `volatile`
- atomic instructions and `fetch_add`
- atomicity as distinct from memory ordering
- thread creation, joining, and language-level safety

</div>

## 4.1 Shared Address Space and the Loss of Intra-Process Isolation

A thread is characterized by a dual nature: it possesses a private
architectural state, including a unique program counter, register set, and
stack, yet it operates within the shared address space of its parent
process. This architecture allows threads to communicate via shared
memory, allowing one thread to observe the updates of another via ordinary
loads and stores, without the overhead of inter-process communication
(IPC) or expensive system calls.

<figure>
<img src="figures/ch04_threads.svg" alt="A single-threaded process versus a process with three threads sharing text, data, and heap"/>
</figure>

Figure 4-1 contrasts a single-threaded process with one that hosts three
threads. Code, global variables, heap, and file descriptors are common to
all three, whereas each retains a stack and a register set of its own.

However, this efficiency comes at a significant cost to safety. While
hardware and the kernel provide robust isolation between distinct
processes via page tables, no such mechanism exists to isolate threads
within a single process. Consequently, the shared memory model exposes the
program to data races: conditions where the correctness of a program
depends on the non-deterministic interleaving of instructions across
multiple threads. When multiple threads concurrently access and modify the
same memory location without proper synchronization, the integrity of the
data is compromised by the atomicity gaps inherent in the CPU's execution
cycle.

<div class="callout keyidea">
<span class="label">Key idea</span>

The hardware isolates processes from one another, but it does not isolate
threads within a process. A program that shares a variable between threads
must coordinate their access to it.

</div>

## 4.2 Atomicity and the Resolution of Data Races

The most fundamental concurrency hazard arises from the decomposition of
high-level operations into discrete machine instructions. An operation
that appears indivisible in a high-level language, such as an integer
increment, typically translates to a sequence of load, modify, and store
instructions. In a multi-core environment, if two threads interleave these
steps, one thread's intermediate state may be overwritten by another,
resulting in a "lost update."

```asm
load  r1, [counter]   ; read
add   r1, r1, 1       ; modify
store [counter], r1   ; write
```

<figure>
<img src="figures/ch04_race_timeline.svg" alt="Timeline showing two threads loading 42, adding 1, and storing 43, losing one increment"/>
</figure>

Figure 4-2 traces one such interleaving. Both threads load 42 before
either stores a result, both compute 43, and both store 43, so the counter
holds 43 where 44 was required. Listing 4-1 subjects the hazard to
measurement: eight threads each increment one shared counter 20,000,000
times, for an expected total of 160,000,000.

**Listing 4-1. Eight threads increment one counter without synchronization (C++20).**

```cpp
{{#include ../code/ch04/race.cpp}}
```

**Output 4-1. One run. The observed value differs from run to run.**

```text
{{#include ../code/out/ch04_race.out}}
```

The counter terminated at 45,704,287, which corresponds to a loss of
roughly 71 percent of the increments. The `volatile` qualifier on the
counter neither confers atomicity nor synchronizes threads. It merely
obliges the compiler to perform every read and write in memory, without
which the counter could reside in a register for the duration of the loop
and the race would elude observation. Its presence serves the experiment
and nothing else.

Rust ordinarily rejects unsynchronized writes from several threads at
compile time. Reproducing the race therefore requires a `static mut`
accessed through raw pointers in `unsafe` blocks, each annotated with a
`SAFETY` comment conceding that the required invariant is deliberately
violated.

**Listing 4-2. The same race in Rust, written with `unsafe`.**

```rust
{{#include ../code/ch04/race.rs}}
```

**Output 4-2.**

```text
{{#include ../code/out/ch04_race_rs.out}}
```

The Rust program forfeits a comparable share. In both cases the precise
count is governed by scheduler interleaving and by the transfer of the
counter's cache line between cores, and it consequently varies between
runs.

To mitigate this, modern processor architectures provide atomic
instructions, such as `lock xadd` on x86 or `ldaddal` on arm64, which
guarantee that a sequence of operations is perceived by the rest of the
system as a single, indivisible unit. These instructions ensure that no
other core can observe or intervene in the memory location during the
operation.

**Listing 4-3. The counter as a `std::atomic` (C++20).**

```cpp
{{#include ../code/ch04/race_atomic.cpp}}
```

**Output 4-3. The observed value equals the expected value in every run.**

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

With eight threads and 5,000,000 increments each, the expected value is
40,000,000, and both programs report exactly that. Each `fetch_add`
compiles to a single atomic instruction.

It is critical to distinguish between **atomicity** and **memory
ordering**. Atomicity refers to the indivisibility of a single operation,
ensuring no partial states are observable. Ordering, conversely, governs
the visibility and sequence of effects on *different* memory locations
across threads. An operation can be atomic without being ordered, a
distinction that is central to the design of high-performance concurrent
algorithms and the use of relaxed memory models. The argument
`std::memory_order_relaxed`, or `Ordering::Relaxed` in Rust, requests
atomicity alone, which suffices for a counter independent of all other
data and is the least costly option. Chapter 6 examines the stronger
orderings.

## 4.3 Thread Lifecycle and Language-Level Safety

Thread management involves the creation of new execution contexts and the
eventual synchronization of their completion, typically through a "join"
operation. The abstraction of thread creation allows a program to spawn
multiple tasks that run concurrently, with the scheduler determining their
interleaving on available cores.

**Listing 4-5. Four threads in one process (C++20).**

```cpp
{{#include ../code/ch04/threads.cpp}}
```

**Output 4-5. The order of the lines differs from run to run.**

```text
{{#include ../code/out/ch04_threads.out}}
```

Listing 4-5 encloses its print statement in a mutex. A single statement
comprises several `<<` operations, each of which `std::cout` treats as a
separate write, so that two unsynchronized threads could interleave their
fragments into `thread thread 01 running running`. The mutex, examined in
Chapter 6, renders the whole line one unit. C++ further requires every
`std::thread` to be joined or detached before destruction, failing which
the program invokes `std::terminate`.

**Listing 4-6. The same four threads in Rust.**

```rust
{{#include ../code/ch04/threads.rs}}
```

**Output 4-6.**

```text
{{#include ../code/out/ch04_threads_rs.out}}
```

The Rust version dispenses with the mutex, since `println!` locks standard
output for the duration of one call. Its `join` additionally propagates
the result of the thread's function, or an error if that function
panicked.

Different programming languages approach the inherent risks of threading
through varying degrees of strictness. C++ provides flexible but
inherently unsafe mechanisms, allowing threads to capture local variables
by reference without built-in protection against lifetime or
synchronization issues. Rust, by contrast, leverages its ownership and
type systems to enforce thread safety at compile time. By requiring that
data shared between threads be wrapped in synchronized types (such as
`Arc` for shared ownership) or managed through strict ownership transfers,
Rust eliminates entire classes of data races, forcing the developer to
explicitly acknowledge and handle the complexities of shared mutable
state.

<div class="callout summary">
<span class="label">Summary</span>

- Threads share code, globals, heap, and descriptors, and each retains a
  private stack and register set. No hardware boundary separates them.
- An increment decomposes into load, modify, and store. Interleaving
  across threads lost 71 percent of 160,000,000 increments in our run.
- `volatile` forces memory access but confers neither atomicity nor
  synchronization.
- An atomic `fetch_add` executes as one indivisible instruction and
  yields the exact count.
- Atomicity concerns one operation, whereas ordering concerns the
  visibility of effects on different locations.
- Rust rejects unsynchronized sharing at compile time, and C++ leaves it
  to the programmer.

Which thread occupies a core at each instant is determined by the
scheduler, the subject of Chapter 5.

</div>
