# 6. Synchronization

Chapter 4 measured the failure mode: shared state, concurrent threads, lost
updates. This chapter supplies the repairs, in the order a systems
engineer reaches for them: the mutex for mutual exclusion, the condition
variable for waiting on a condition, and the discipline that keeps both
from deadlocking. The chapter closes with the ordering rules that atomics
add on top of atomicity.

<div class="callout glance">
<span class="label">At a glance</span>

- A mutex admits one thread into a critical section; everyone else waits.
- A condition variable releases the mutex while a thread waits for a
  predicate to become true, then reacquires it.
- Deadlock needs four conditions; breaking any one prevents it.
- Atomics provide atomicity by instruction and ordering by memory order.

</div>

## 6.1 The mutex

A **mutex** is a lock with two states and one rule: at most one thread
holds it at a time. A thread that calls `lock` on a free mutex takes it
and proceeds; a thread that calls `lock` on a held mutex blocks until the
holder releases it. The code between lock and unlock is a **critical
section**, and the mutex's guarantee is that critical sections guarded by
the same mutex never overlap.

Figure 6-1 draws the arrangement: an owner, a queue of waiters, and the
protected region.

<figure>
<img src="diagrams/ch06_mutex.svg" alt="A mutex with an owner, a wait queue, and the critical section it protects"/>
</figure>

The counter experiment from Chapter 4, guarded this time.

**Listing 6-1. The lost-update counter, protected by a mutex (C++20).**

```cpp
{{#include ../code/ch06/mutex_counter.cpp}}
```

**Output 6-1. Exact, every run — at a cost the listing does not hide.**

```text
{{#include ../code/out/ch06_mutex.out}}
```

The cost is real. The atomic version in Chapter 4 completed each
increment with one locked instruction. This version locks a mutex, which
is itself built from atomics, for every increment, and contended mutexes
add the further cost of putting waiters to sleep and waking them. When
the critical section is one instruction, the atomic wins. When the
critical section is a data structure — a queue, a table, a cache — the
mutex is the right tool, and its overhead is noise against the section's
length.

**Listing 6-2. The same guarded counter in Rust.**

```rust
{{#include ../code/ch06/mutex_counter.rs}}
```

**Output 6-2.**

```text
{{#include ../code/out/ch06_mutex_rs.out}}
```

Rust's `Mutex` differs from C++'s in one instructive way: the mutex owns
the value. `Arc<Mutex<u64>>` is a shared reference-counted mutex holding
the counter, and `lock()` returns a guard through which the counter is
the only way to reach it. The compiler rejects touching the counter
without holding the lock, because the counter is not reachable any other
way. C++'s mutex protects by convention; Rust's protects by
construction.

## 6.2 Condition variables: waiting for a condition

A mutex answers "can I enter?" A condition variable answers "may I
proceed?", and the two questions differ. The classic problem is the
**bounded buffer**: producers add items to a fixed-size queue, consumers
remove them. A producer with a full queue must wait for space; a consumer
with an empty queue must wait for items.

A naive solution spins: lock, check, unlock, repeat. Spinning wastes the
core and delays the other side. The correct mechanism is the **condition
variable**, which does something a mutex alone cannot: it releases the
mutex while the thread waits, and reacquires it before the thread wakes.
The wait is written against a **predicate** — `count < capacity` or
`count > 0` — and the rule is always: wait inside a loop, because the
wakeup only promises that the predicate *may* be true.

**Listing 6-3. A bounded buffer shared by two producers and two consumers (C++20).**

```cpp
{{#include ../code/ch06/prodcons.cpp}}
```

**Output 6-3. The sums prove the accounting: nothing lost, nothing duplicated.**

```text
{{#include ../code/out/ch06_prodcons.out}}
```

The verification deserves one sentence of its own. Two producers generate
the values 1 through 200,000 and sum them as they produce. Two consumers
sum what they remove. If an item were lost, the consumed sum would fall
short of the expected 20,000,100,000. If an item were duplicated, it
would overshoot. The equality of three independently computed numbers is
the proof that the synchronization is correct, not merely fast.

**Listing 6-4. The same buffer with `Mutex` + `Condvar` (Rust).**

```rust
{{#include ../code/ch06/prodcons.rs}}
```

**Output 6-4.**

```text
{{#include ../code/out/ch06_prodcons_rs.out}}
```

The two listings are structurally identical — lock, loop-while-predicate,
act, notify — and that structure is the contract. `notify_one` wakes one
waiter; a broadcast would wake all, which is correct but noisier. The
predicate lives in the program, not in the condition variable; the
variable only provides the sleep and the wakeup.

<div class="callout caution">
<span class="label">Watch out</span>

A wakeup is a hint, not a guarantee. The predicate may still be false
when the thread wakes — another consumer may have taken the item first.
Checking the predicate once, with `if` instead of `while`, is the
single most common synchronization bug, and it survives testing because
it fires only under timing that tests rarely produce.

</div>

## 6.3 Deadlock

Two threads, two mutexes, opposite order. Worker 1 locks A, then wants B.
Worker 2 locks B, then wants A. Each holds what the other wants, and
neither releases what it holds: the two are **deadlocked**. Figure 6-2
draws the cycle.

<figure>
<img src="diagrams/ch06_deadlock.svg" alt="Two workers each holding one resource and waiting for the other, forming a cycle"/>
</figure>

The next listing deadlocks on purpose. The harness starts it, observes
after one second that it has not finished, and kills it — the captured
output records the verdict.

**Listing 6-5. The deadlock, deliberately constructed (C++20).**

```cpp
{{#include ../code/ch06/deadlock.cpp}}
```

**Output 6-5. Both workers announce their first lock; neither reaches the second.**

```text
{{#include ../code/out/ch06_deadlock.out}}
```

Deadlock requires four conditions, and the four suggest four fixes.
**Mutual exclusion** — a resource held by one thread at a time. Break it
with lock-free structures, rarely practical. **Hold and wait** — a thread
holds one lock while requesting another. Break it by acquiring all locks
at once, as C++'s `std::scoped_lock` and Rust's multiple `lock` calls
do, or by `try_lock` with release-and-retry. **No preemption** — locks
cannot be taken away. Break it with `try_lock` timeouts. **Circular
wait** — a cycle in who waits for whom. Break it with a global lock
order: every thread acquires A before B, always.

The next listing breaks hold-and-wait. Worker 2 takes B, *tries* A, and
on failure releases B and retries after a short sleep. No thread ever
blocks while holding a lock it cannot complete with.

**Listing 6-6. try_lock: back off instead of blocking (C++20).**

```cpp
{{#include ../code/ch06/trylock.cpp}}
```

**Output 6-6. Retries, then success — no deadlock, no hang.**

```text
{{#include ../code/out/ch06_trylock.out}}
```

<div class="callout keyidea">
<span class="label">Key idea</span>

The practical rule: acquire locks in one global order, or never hold one
lock while waiting for another. Both rules make the cycle of Figure 6-2
unrepresentable.

</div>

## 6.4 Atomics and memory ordering

Chapter 4 used `fetch_add` with **relaxed** ordering: atomic, but ordered
against nothing. Two stronger orders complete the vocabulary, and the
names describe the guarantees precisely.

**Acquire–release** comes in pairs. A **release store** publishes a value
and everything written before it; an **acquire load** that reads that
value also sees everything the store published. The pattern is
message-passing through memory: a producer writes a payload, then
release-stores a ready flag; the consumer acquire-loads the flag and may
then read the payload without a mutex. Rust's `Mutex` and C++'s `mutex`
are built on exactly this pair.

**Sequential consistency** is the strongest default: every operation
appears in one global order shared by all threads. It is the easiest to
reason about and the most expensive, which is why both languages let a
programmer choose a weaker order where the algorithm allows.

The table is the whole interface:

| Need | C++ | Rust |
|---|---|---|
| atomic increment, nothing else | `fetch_add(1, memory_order_relaxed)` | `fetch_add(1, Ordering::Relaxed)` |
| publish, then signal | `store(v, memory_order_release)` | `store(v, Ordering::Release)` |
| observe the signal, read the payload | `load(memory_order_acquire)` | `load(Ordering::Acquire)` |
| strongest, simplest | default (`memory_order_seq_cst`) | `Ordering::SeqCst` |

The deeper theory — happens-before, coherence, fences — fills a book of
its own. The systems-engineer level is the table above plus one habit:
when a mutex fits, use the mutex; reach for explicit ordering only when
the critical section has been reduced to a flag.

<div class="callout summary">
<span class="label">Summary</span>

- Mutexes serialize critical sections; they protect regions, not values,
  and cost a lock per region.
- Condition variables wait on predicates while releasing the mutex;
  always re-check the predicate in a loop.
- Deadlock is a cycle of hold-and-wait; a global lock order or
  try-and-back-off breaks it.
- Atomics are the building blocks: relaxed for isolated counters,
  acquire–release for publish–observe, sequential consistency as the
  readable default.
- All of this runs in one address space; Chapter 11 takes
  synchronization across processes, where the tools are the same but
  the kernel mediates.

</div>
