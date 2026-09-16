# 44. A Spin Lock {#spin-lock}

*Source file: [`src/problems/spin_lock.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/spin_lock.rs). Test it with `cargo test spin_lock`.*

## Problem Statement

Implement `SpinLock<T>` with `lock`, which waits until the lock is free and returns a
guard, and `try_lock`, which returns `None` immediately if the lock is held. The guard
must give `&T` and `&mut T` access to the value and release the lock when it is
dropped. The lock must be shareable between threads through `Arc` or a scoped borrow.

## Designing a Solution

**State.** The lock is an `AtomicBool`, `false` when free, and the value is an
`UnsafeCell<T>`. `UnsafeCell` is the only legal way in Rust to obtain a mutable
pointer to data reachable through a shared reference; every interior-mutability type,
including `Mutex` and `RefCell`, is built on it.

**Acquire.** `compare_exchange(false, true)` stores `true` only if the current value is
`false`, and reports whether it did. Exactly one of several competing threads succeeds.
The losers wait for the flag to become `false` and try again.

**Release.** The guard's `Drop` stores `false`. Because release happens in a destructor,
it happens on every path out of the critical section, including a panic that unwinds
through it.

**Soundness.** The guard dereferences to `&mut T` using the `UnsafeCell`. That is sound
only while the guard is the only way to reach the value, which the flag guarantees:
while one guard exists, no other thread can create a second one.

```text
thread A                                 thread B
compare_exchange(false, true) -> Ok       compare_exchange(false, true) -> Err
guard A: exclusive access to the value    while locked.load() { spin_loop() }
*guard += 1                               ...
drop(guard A): locked.store(false)        load() sees false, loop exits
                                          compare_exchange(false, true) -> Ok
                                          guard B: exclusive access
```

## Implementation

<p class="listing"><span class="listing-label">Listing 44.1</span> The complete module, with its tests. <code>src/problems/spin_lock.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/spin_lock.rs">read the file on GitHub</a></p>

### The acquire loop

`lock` has two nested loops. The outer loop attempts the exchange with
`compare_exchange_weak`, which is allowed to fail spuriously even when the value is
`false`. On some architectures, including ARM, the weak version maps directly to a
load-link/store-conditional instruction pair and avoids an internal retry loop, and
the outer loop already handles failure.

When the exchange fails, the inner loop waits with plain `load` calls until the flag
reads `false`. A failed `compare_exchange` still requests exclusive ownership of the
cache line holding the flag, while a `load` can proceed from a shared copy. Spinning on
`load` keeps contending threads from bouncing the cache line between cores.
`std::hint::spin_loop` emits the processor's pause instruction, which reduces power
use and lets the processor schedule the waiting loop efficiently.

### The orderings

The success ordering of the exchange is `Acquire` and the release uses `Release`. For a
lock built on one atomic, these names document intent: `Acquire` for the operation that
takes the lock and `Release` for the one that gives it up. The protected data does not
depend on the ordering argument. It is synchronized by mutual exclusion: a write made
under the lock happens before the release, and the next holder cannot start before it
observes that release. The failure ordering `Relaxed` applies to the load performed
when the exchange fails, where no guarantee beyond the atomic's own is needed.

### The trait implementations

`unsafe impl<T: Send> Sync for SpinLock<T> {}` tells the compiler that `&SpinLock<T>`
may be shared between threads. The bound is `T: Send`, not `T: Sync`, and it matches
`std::sync::Mutex`. Through the lock, only one thread at a time can reach the value,
so the value never needs to be accessed concurrently; it only needs to be movable
between threads, because one thread may write it and another read it later.

`SpinLock<T>` is automatically `Send` when `T: Send`, because `AtomicBool` and
`UnsafeCell<T>` are.

### The guard

`SpinGuard` holds `&'a SpinLock<T>`, and the lifetime ties it to the lock, so a guard
cannot outlive its lock. `Deref` and `DerefMut` each contain one `unsafe` block that
turns the `UnsafeCell`'s raw pointer into a reference. The `SAFETY` comments state the
invariant that justifies both: holding a guard means this thread has exclusive access.

## Intuition

**`try_lock_reports_contention`**

| step | `locked` | result |
|---|---|---|
| `SpinLock::new(1u32)` | `false` | |
| `let guard = lock.lock()` | `true` | exchange succeeds |
| `lock.try_lock()` | `true` | exchange fails, returns `None` |
| `lock.is_locked()` | `true` | returns `true` |
| `drop(guard)` | `false` | `Drop` stores `false` |
| `lock.try_lock()` | `true` for the temporary guard, then `false` when it is dropped at the end of the statement | returns `Some` |
| `lock.is_locked()` | `false` | returns `false` |

In `serializes_concurrent_increments`, eight threads each perform 1,000 increments of
`*lock.lock() += 1`. Every increment reads and writes the counter under the lock, so
the final value is exactly 8,000. Without the lock, lost updates would make it
smaller.

## Time and Space Complexity

| Operation | Time | Space |
|---|---|---|
| `lock`, uncontended | one compare-and-swap | none |
| `lock`, contended | unbounded busy-waiting; the thread uses a full core while it waits | none |
| `try_lock` | one compare-and-swap | none |
| guard drop | one store | none |
| memory | | `size_of::<T>()` plus one byte, rounded up to `T`'s alignment |

## Limitations

**The guard is `Sync` for any `T: Send`, which is unsound.** `SpinGuard` has no explicit
trait implementations, so the compiler derives them from its one field,
`&'a SpinLock<T>`. That reference is `Sync` whenever `SpinLock<T>` is, which is
whenever `T: Send`. The guard therefore becomes `Sync` for a type such as
`Cell<i32>`, which is `Send` but not `Sync`. Sharing `&SpinGuard<Cell<i32>>` between
two scoped threads lets both call `Cell::set` through `Deref` at the same time, a data
race in safe code. The following program compiles against this lock:

```rust
let lock = SpinLock::new(Cell::new(0));
let guard = lock.lock();
std::thread::scope(|s| {
    s.spawn(|| guard.set(1));
    guard.set(2);
});
```

`std::sync::MutexGuard` avoids this with an explicit `unsafe impl<T: ?Sized + Sync>
Sync for MutexGuard<'_, T>`. The smallest fix for `SpinGuard` is a marker field that
makes the guard's automatic `Sync` implementation require `T: Sync`:

```rust
use std::marker::PhantomData;

pub struct SpinGuard<'a, T> {
    lock: &'a SpinLock<T>,
    // `&mut T` is `Sync` only if `T: Sync`, so the guard is too.
    _not_sync_unless_t_is: PhantomData<&'a mut T>,
}
```

Each place that constructs a guard then writes
`SpinGuard { lock: self, _not_sync_unless_t_is: PhantomData }`. The same issue appears
in the short spin lock in `drills.rs`, described in chapter 59.

**Spinning wastes a core.** A thread that cannot acquire the lock keeps running. If the
holder is descheduled, or the critical section is long, waiting threads burn CPU time
without progress. On a machine with more runnable threads than cores this can be much
slower than a mutex that parks the thread. Spin locks suit very short critical
sections on dedicated cores; `std::sync::Mutex` spins briefly and then parks, and is
the right default.

**No fairness.** A thread that has waited a long time has no advantage over one that
arrived a moment ago. Under steady contention, a thread can wait indefinitely.

**No poisoning.** A panic while the guard is held releases the lock through `Drop`, and
the next thread sees whatever partial update the panicking thread left. Chapter 22
explains why `Mutex` records that event.

**Not reentrant.** Calling `lock` twice on one thread without dropping the first guard
spins forever.

## Summary

- A spin lock is an `AtomicBool` guarding an `UnsafeCell<T>`; `compare_exchange` lets
  exactly one thread set the flag.
- `compare_exchange_weak` in a loop, with a `load`-and-`spin_loop` wait on failure, is
  the conventional acquire path.
- The guard releases the lock in `Drop`, so every exit from the critical section,
  including unwinding, unlocks it.
- `unsafe impl<T: Send> Sync for SpinLock<T>` matches `Mutex` and is justified by
  mutual exclusion.
- The guard's automatically derived `Sync` is too permissive; a `PhantomData<&mut T>`
  field, or an explicit implementation bounded by `T: Sync`, closes the hole.

## References

- Mara Bos, *Rust Atomics and Locks*, O'Reilly Media, 2023, Chapter 4, "Building Our
  Own Spin Lock".
- Standard library, [`AtomicBool::compare_exchange_weak`](https://doc.rust-lang.org/std/sync/atomic/struct.AtomicBool.html#method.compare_exchange_weak).
- Standard library, [`std::cell::UnsafeCell`](https://doc.rust-lang.org/std/cell/struct.UnsafeCell.html) and [`std::hint::spin_loop`](https://doc.rust-lang.org/std/hint/fn.spin_loop.html).
- Standard library, [`MutexGuard`](https://doc.rust-lang.org/std/sync/struct.MutexGuard.html), for its `Send` and `Sync` implementations.
- The Rustonomicon, [Send and Sync](https://doc.rust-lang.org/nomicon/send-and-sync.html).
