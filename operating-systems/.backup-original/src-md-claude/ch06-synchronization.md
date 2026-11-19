# 6. Synchronization and Memory Ordering

While atomic instructions suffice for single-word updates, most concurrent
operations involve complex, multi-instruction transformations of data
structures. To preserve system integrity, threads must coordinate their
access to these critical sections using higher-level synchronization
primitives.

<div class="callout glance">
<span class="label">This chapter covers</span>

- mutexes and critical sections
- condition variables, predicates, and the bounded buffer
- the four necessary conditions for deadlock, and their removal
- relaxed, acquire/release, and sequentially consistent ordering

</div>

## 6.1 Mutual Exclusion and Critical Sections

A **mutex** (mutual exclusion) is a synchronization primitive that grants
exclusive access to a critical section of code to a single thread at a
time. When a thread attempts to acquire a mutex already held by another,
the kernel may suspend the thread, placing it in a wait queue to prevent
wasteful "spinning."

<figure>
<img src="figures/ch06_mutex.svg" alt="A mutex with an owner, a wait queue, and the critical section it protects"/>
</figure>

Figure 6-1 depicts a mutex with its owner, a suspended contender, and the
critical section it guards. Listing 6-1 repeats the counter experiment of
Chapter 4 with the increment enclosed in such a section.

**Listing 6-1. The shared counter, protected by a mutex (C++20).**

```cpp
{{#include ../code/ch06/mutex_counter.cpp}}
```

**Output 6-1. The observed value equals the expected value in every run.**

```text
{{#include ../code/out/ch06_mutex.out}}
```

The choice between atomic instructions and mutexes is primarily a matter
of granularity and overhead. Atomic operations are highly efficient for
single-word updates, as they are implemented directly in hardware.
However, when a critical section encompasses complex data structures, such
as queues or trees, the overhead of a mutex is negligible compared to the
work performed within the section. In languages like Rust, the `Mutex`
type enforces safety by wrapping the data it protects, ensuring that the
data can only be accessed through a lock guard, thereby preventing
accidental unprotected access at compile time.

**Listing 6-2. The same counter in Rust.**

```rust
{{#include ../code/ch06/mutex_counter.rs}}
```

**Output 6-2.**

```text
{{#include ../code/out/ch06_mutex_rs.out}}
```

In Listing 6-2, the type `Arc<Mutex<u64>>` denotes a reference-counted
pointer to a mutex that contains the counter. Invoking `lock()` yields the
guard through which the counter is reached, and code that bypasses the
lock is rejected by the compiler. C++ offers no equivalent coupling: mutex
and data are separate objects, and their association exists only by
convention.

## 6.2 Condition Variables and Predicate-Based Synchronization

Mutexes provide exclusion, but they lack the ability to facilitate
coordination based on state changes. **Condition variables** bridge this
gap by allowing threads to sleep until a specific logical condition, or
**predicate**, is satisfied.

The canonical instance is the *bounded buffer*, a queue of fixed capacity
shared by producer threads that insert items and consumer threads that
remove them. A producer must wait while the buffer is full, on the
predicate `count < capacity`, and a consumer must wait while it is empty,
on the predicate `count > 0`.

The standard pattern for using a condition variable is implemented through
a `wait` operation that atomically releases the associated mutex and
suspends the thread. When another thread modifies the state and invokes
`notify`, the sleeping thread is awakened and must re-acquire the mutex
before the `wait` returns. Because of potential race conditions and
"spurious wakeups" (where a thread is awakened without the predicate being
met), the `wait` operation must always be encapsulated within a loop that
repeatedly tests the predicate. This ensures that the thread only proceeds
when the condition is truly satisfied.

**Listing 6-3. A bounded buffer with two producers and two consumers (C++20).**

```cpp
{{#include ../code/ch06/prodcons.cpp}}
```

**Output 6-3. The three sums are equal.**

```text
{{#include ../code/out/ch06_prodcons.out}}
```

Listing 6-3 certifies its own correctness. The two producers jointly
insert the values 1 through 200,000 and accumulate what they insert, while
each consumer accumulates what it removes. The sum of 1 through 200,000 is
200,000 × 200,001 / 2 = 20,000,100,000. A lost item would depress the
consumed sum below this figure, and a duplicated item would raise it
above. All three printed sums coincide. The two-argument form of `wait`
used in the listing accepts the predicate as a lambda and incorporates the
required loop.

**Listing 6-4. The same buffer in Rust, with `Mutex` and `Condvar`.**

```rust
{{#include ../code/ch06/prodcons.rs}}
```

**Output 6-4.**

```text
{{#include ../code/out/ch06_prodcons_rs.out}}
```

<div class="callout caution">
<span class="label">Watch out</span>

A thread that returns from `wait` cannot assume that its predicate is
true. Another consumer may have removed the item first, and some systems
also wake threads for no reason (a *spurious wakeup*). Testing the
predicate with `if` instead of `while` is a common bug. It is hard to find
by testing, because it fails only under rare timing.

</div>

## 6.3 Deadlock: Causes and Prevention

A **deadlock** occurs when a group of threads enters a state of permanent
suspension, where each thread is waiting for a resource held by another
thread in the cycle. For a deadlock to manifest, four necessary conditions
must hold simultaneously:

1. **Mutual Exclusion:** The resource is held by exactly one thread.
2. **Hold and Wait:** A thread holds one resource while requesting
   another.
3. **No Preemption:** A resource cannot be forcibly taken from its holder.
4. **Circular Wait:** A closed chain of dependencies exists among the
   waiting threads.

<figure>
<img src="figures/ch06_deadlock.svg" alt="Two workers each holding one resource and waiting for the other, forming a cycle"/>
</figure>

Figure 6-2 shows the minimal cycle: worker 1 holds A and requests B, while
worker 2 holds B and requests A. Listing 6-5 constructs it deliberately.
Each worker sleeps for 50 ms after its first acquisition, which guarantees
that the other completes its own. The capturing script finds the process
still alive after 1 second and terminates it.

**Listing 6-5. A deliberate deadlock (C++20).**

```cpp
{{#include ../code/ch06/deadlock.cpp}}
```

**Output 6-5. Each worker acquires its first mutex and never acquires the second.**

```text
{{#include ../code/out/ch06_deadlock.out}}
```

Deadlock prevention strategies focus on breaking one of these conditions.
One effective method is to enforce a strict, global acquisition order for
all locks, which eliminates the possibility of a circular wait.
Alternatively, threads can employ a "try-and-back-off" strategy using
`try_lock` operations; if a thread fails to acquire a secondary resource,
it releases its held resources and retries, thereby breaking the "hold and
wait" condition.

**Listing 6-6. Using try_lock to release and retry (C++20).**

```cpp
{{#include ../code/ch06/trylock.cpp}}
```

**Output 6-6. Worker 2 retries several times, and both workers finish.**

```text
{{#include ../code/out/ch06_trylock.out}}
```

In this run, the first nine attempts of worker 2 failed. Because it
relinquished B after each failure, worker 1 obtained both mutexes and
completed, whereupon the tenth attempt of worker 2 succeeded. C++ also
provides `std::scoped_lock`, which acquires several mutexes in one
operation and removes hold and wait by construction.

<div class="callout keyidea">
<span class="label">Key idea</span>

To prevent deadlock, acquire locks in the same order in every thread, or
never block while holding a lock. With either rule, the cycle of Figure
6-2 cannot form.

</div>

## 6.4 Memory Ordering and Visibility

In a concurrent system, the visibility of memory operations is not
guaranteed by atomicity alone. Memory ordering models define how different
threads perceive the sequence of reads and writes performed by others.

- **Relaxed Ordering:** Guarantees only that the operation itself is
  atomic. It provides no guarantees regarding the order in which
  subsequent or preceding memory operations become visible to other
  threads.
- **Acquire/Release Semantics:** Provides a mechanism for transitive
  visibility. A `release` operation on a variable ensures that all prior
  memory writes by the thread are made visible to any thread that
  subsequently performs an `acquire` operation on that same variable. This
  is the fundamental pattern for publishing data safely between threads.
- **Sequential Consistency:** The strongest ordering model, providing a
  single, global total order of all operations that is consistent with all
  threads' views. While the easiest to reason about, it incurs significant
  performance penalties on modern hardware due to the requirement for
  strict synchronization across cores.

**Table 6-1. Memory orderings in C++ and Rust.**

| Need | C++ | Rust |
|---|---|---|
| atomic increment only | `fetch_add(1, memory_order_relaxed)` | `fetch_add(1, Ordering::Relaxed)` |
| publish data, then set a flag | `store(v, memory_order_release)` | `store(v, Ordering::Release)` |
| read the flag, then read the data | `load(memory_order_acquire)` | `load(Ordering::Acquire)` |
| one common order for all threads | default (`memory_order_seq_cst`) | `Ordering::SeqCst` |

Sequential consistency is the default in C++. Explicit weaker orderings
are warranted only where shared state has been reduced to a flag or a
counter, and a mutex remains the appropriate instrument wherever a
critical section spans more than that.

<div class="callout summary">
<span class="label">Summary</span>

- A mutex admits one thread at a time to a critical section. Its overhead
  is justified when the section updates a multi-word structure.
- A condition variable suspends a thread until a predicate holds. `wait`
  releases the mutex atomically, and the predicate must be retested in a
  loop after every wakeup.
- Deadlock requires mutual exclusion, hold and wait, no preemption, and
  circular wait. A global lock order removes the cycle, and `try_lock`
  with back-off removes hold and wait.
- Relaxed ordering guarantees atomicity alone, acquire/release publishes
  prior writes, and sequential consistency imposes one global order.

Every thread in this chapter shares one address space. Chapter 11 extends
synchronization across separate processes.

</div>
