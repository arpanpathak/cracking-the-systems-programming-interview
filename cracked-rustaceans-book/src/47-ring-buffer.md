# 47. A Lock-Free Ring Buffer {#ring-buffer}

*Source file: [`src/problems/ring_buffer.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/ring_buffer.rs). Test it with `cargo test ring_buffer`.*

## Problem Statement

Implement `SpscRing<T, N>` with capacity `N`:

- `push(value) -> Result<(), T>` returns the value when the ring is full;
- `pop() -> Option<T>` returns `None` when the ring is empty;
- one thread may push while another pops, with no lock;
- items still in the ring when it is dropped must be dropped too.

## Designing a Solution

**Two indices, two owners.** `tail` is the index of the next slot to write, and only the
producer changes it. `head` is the index of the next slot to read, and only the consumer
changes it. Neither side ever writes the other's index, so no compare-and-swap is
needed; each side reads the other's index to decide whether it may proceed.

**Indices that only grow.** The indices count total pushes and total pops, and the slot
used is `index % N`. The number of queued items is `tail - head`, computed with
wrapping subtraction. Keeping full and empty distinct needs no spare slot: empty is
`head == tail`, and full is `tail - head == N`.

**Publish after the write.** The producer writes the value into the slot first and
stores the new `tail` second. Until that store, the consumer's view of `tail` does not
include the slot, so it cannot read a slot that is still being written. The consumer
does the mirror image: it reads the value out, then stores the new `head`, which is
when the producer may reuse the slot.

```text
a ring of four slots after six pushes and three pops

tail = 6, head = 3, len = tail - head = 3

slot index:   0        1        2        3
            [ v4 ]  [ v5 ]  [ free ] [ v3 ]
                              ^         ^
                   tail % 4 = 2         head % 4 = 3
                   next write           next read
```

**Uninitialized storage.** Slots that do not hold a value must not be dropped or read.
Each slot is `UnsafeCell<MaybeUninit<T>>`: `MaybeUninit` allows a slot to be
uninitialized, and `UnsafeCell` allows the two threads to write slots through a shared
reference.

## Implementation

```rust
//! Lock-free single-producer / single-consumer (SPSC) ring buffer.
//!
//! The classic producer/consumer exercise, but with no mutex: the producer owns
//! the `tail` index and the consumer owns the `head` index, and each publishes its
//! write with a release store so the other side sees the slot only after it is
//! initialized. This is the shape inside channel implementations, log shippers,
//! and kernel ring buffers.
//!
//! Two rules keep this sound:
//!
//! - exactly one thread calls [`SpscRing::push`] and exactly one calls
//!   [`SpscRing::pop`];
//! - a slot is written before `tail` is published, and read only after `head`
//!   reaches it.
//!
//! If you need many producers or consumers, use a mutex-backed queue such as
//! [`crate::problems::bounded_queue::BoundedQueue`].

use std::cell::UnsafeCell;
use std::mem::MaybeUninit;
use std::sync::atomic::{AtomicUsize, Ordering};

/// Ring buffer with capacity `N` (the maximum number of queued items).
pub struct SpscRing<T, const N: usize> {
    slots: [UnsafeCell<MaybeUninit<T>>; N],
    /// Next index to read. Written only by the consumer.
    head: AtomicUsize,
    /// Next index to write. Written only by the producer.
    tail: AtomicUsize,
}

// SAFETY: at most one thread mutates `head` and one mutates `tail`. A slot is
// initialized before `tail` is published with a release store, and the consumer
// performs an acquire load of `tail` before reading that slot, so there is no
// data race and no read of uninitialized memory under the SPSC discipline.
unsafe impl<T: Send, const N: usize> Sync for SpscRing<T, N> {}

impl<T, const N: usize> SpscRing<T, N> {
    /// Create an empty ring. Panics if `N` is zero.
    pub fn new() -> Self {
        assert!(N > 0, "ring capacity must be > 0");
        Self {
            slots: std::array::from_fn(|_| UnsafeCell::new(MaybeUninit::uninit())),
            head: AtomicUsize::new(0),
            tail: AtomicUsize::new(0),
        }
    }

    /// Maximum number of items the ring can hold.
    pub const fn capacity(&self) -> usize {
        N
    }

    /// Number of queued items. Only meaningful to the owning side in a race.
    pub fn len(&self) -> usize {
        self.tail
            .load(Ordering::Acquire)
            .wrapping_sub(self.head.load(Ordering::Acquire))
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }

    pub fn is_full(&self) -> bool {
        self.len() >= N
    }

    /// Enqueue a value, returning `Err(value)` when the ring is full.
    pub fn push(&self, value: T) -> Result<(), T> {
        let tail = self.tail.load(Ordering::Relaxed);
        let head = self.head.load(Ordering::Acquire);
        if tail.wrapping_sub(head) >= N {
            return Err(value);
        }

        let index = tail % N;
        // SAFETY: the slot at `index` is free because the ring is not full, and
        // only the producer writes it.
        unsafe { (*self.slots[index].get()).write(value) };

        // Publish the slot to the consumer.
        self.tail.store(tail.wrapping_add(1), Ordering::Release);
        Ok(())
    }

    /// Dequeue a value, or `None` when the ring is empty.
    pub fn pop(&self) -> Option<T> {
        let head = self.head.load(Ordering::Relaxed);
        let tail = self.tail.load(Ordering::Acquire);
        if head == tail {
            return None;
        }

        let index = head % N;
        // SAFETY: `head != tail`, so the producer has published this slot and
        // only the consumer reads it.
        let value = unsafe { (*self.slots[index].get()).assume_init_read() };

        // Publish the freed slot to the producer.
        self.head.store(head.wrapping_add(1), Ordering::Release);
        Some(value)
    }
}

impl<T, const N: usize> Default for SpscRing<T, N> {
    fn default() -> Self {
        Self::new()
    }
}

impl<T, const N: usize> Drop for SpscRing<T, N> {
    fn drop(&mut self) {
        // Drop any items that were never popped.
        while self.pop().is_some() {}
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;
    use std::sync::atomic::AtomicUsize;
    use std::thread;

    #[test]
    fn is_fifo_within_capacity() {
        let ring = SpscRing::<u32, 4>::new();
        assert!(ring.push(1).is_ok());
        assert!(ring.push(2).is_ok());
        assert!(ring.push(3).is_ok());
        assert_eq!(ring.pop(), Some(1));
        assert_eq!(ring.pop(), Some(2));
        assert_eq!(ring.pop(), Some(3));
        assert_eq!(ring.pop(), None);
    }

    #[test]
    fn full_ring_returns_the_value() {
        let ring = SpscRing::<u32, 2>::new();
        assert!(ring.push(1).is_ok());
        assert!(ring.push(2).is_ok());
        assert!(ring.is_full());
        assert_eq!(ring.push(3), Err(3));
    }

    #[test]
    fn producer_and_consumer_run_concurrently_in_order() {
        const ITEMS: u64 = 50_000;
        const SENTINEL: u64 = u64::MAX;

        let ring = Arc::new(SpscRing::<u64, 256>::new());

        let producer = {
            let ring = Arc::clone(&ring);
            thread::spawn(move || {
                for value in 0..ITEMS {
                    let mut pending = value;
                    loop {
                        match ring.push(pending) {
                            Ok(()) => break,
                            Err(returned) => {
                                pending = returned;
                                thread::yield_now();
                            }
                        }
                    }
                }
                let mut pending = SENTINEL;
                loop {
                    match ring.push(pending) {
                        Ok(()) => break,
                        Err(returned) => {
                            pending = returned;
                            thread::yield_now();
                        }
                    }
                }
            })
        };

        let consumer = {
            let ring = Arc::clone(&ring);
            thread::spawn(move || {
                let mut received = Vec::with_capacity(ITEMS as usize);
                loop {
                    match ring.pop() {
                        Some(SENTINEL) => break,
                        Some(value) => received.push(value),
                        None => thread::yield_now(),
                    }
                }
                received
            })
        };

        producer.join().expect("producer panicked");
        let received = consumer.join().expect("consumer panicked");

        assert_eq!(received, (0..ITEMS).collect::<Vec<_>>());
    }

    #[test]
    fn dropped_ring_drops_queued_items() {
        struct Tracker(Arc<AtomicUsize>);
        impl Drop for Tracker {
            fn drop(&mut self) {
                self.0.fetch_add(1, Ordering::SeqCst);
            }
        }

        let dropped = Arc::new(AtomicUsize::new(0));
        {
            let ring = SpscRing::<Tracker, 4>::new();
            assert!(ring.push(Tracker(Arc::clone(&dropped))).is_ok());
            assert!(ring.push(Tracker(Arc::clone(&dropped))).is_ok());
            assert!(ring.push(Tracker(Arc::clone(&dropped))).is_ok());
        }
        assert_eq!(dropped.load(Ordering::SeqCst), 3);
    }
}
```

### Storage

`slots: [UnsafeCell<MaybeUninit<T>>; N]` is an array whose length is the const generic
parameter, so the ring stores its items inline with no heap allocation. `new` builds it
with `std::array::from_fn`, which calls the closure once per element. The obvious
`[UnsafeCell::new(MaybeUninit::uninit()); N]` does not compile, because array repeat
expressions require the element to be `Copy` or a constant.

`assert!(N > 0)` runs at construction. A zero-capacity ring would make `tail % N` a
division by zero.

### The producer's side

`push` loads its own `tail` with `Relaxed`, because no other thread writes it, and loads
the consumer's `head` with `Acquire`, because it must see the consumer's latest
published value. If the ring is full, the value is returned to the caller in `Err`.

The `unsafe` block writes into the slot with `MaybeUninit::write`, which does not drop
the previous contents. That is required: the slot either was never initialized or was
moved out of by `pop`, and dropping it would be a double free or a read of
uninitialized memory. The `SAFETY` comment names the two facts that justify the write:
the slot is free because the ring is not full, and only the producer writes slots.

`self.tail.store(tail.wrapping_add(1), Ordering::Release)` publishes the new item.

### The consumer's side

`pop` is the mirror of `push`. `assume_init_read` copies the value out of the slot by
bitwise read and leaves the slot logically uninitialized. The `SAFETY` comment rests
on `head != tail`, which means the producer has published this slot.

### Dropping remaining items

`Drop` calls `pop` until the ring is empty, which moves each remaining value out and
drops it. `drop` receives `&mut self`, so no other thread can be using the ring, and the
atomic operations are merely unnecessary rather than incorrect.

### The `Sync` implementation

`unsafe impl<T: Send, const N: usize> Sync for SpscRing<T, N> {}` lets `&SpscRing` be
shared between threads. The `SAFETY` comment conditions it on "at most one thread
mutates `head` and one mutates `tail`". The Limitations section examines what happens
when that condition is not met.

`producer_and_consumer_run_concurrently_in_order` pushes 50,000 values and a sentinel
from one thread and pops on another, retrying with `yield_now` when the ring is full or
empty. It requires the consumer to receive every value in order.

`dropped_ring_drops_queued_items` pushes three `Tracker` values that increment a shared
counter when dropped, lets the ring go out of scope, and checks that the counter reads
three. It would fail if `Drop` were missing, because `MaybeUninit` never drops its
contents by itself.

## Intuition

**`is_fifo_within_capacity` on `SpscRing::<u32, 4>`**

| call | `tail` before | `head` before | slot | `tail` after | `head` after | result |
|---|---|---|---|---|---|---|
| `push(1)` | 0 | 0 | write 0 | 1 | 0 | `Ok(())` |
| `push(2)` | 1 | 0 | write 1 | 2 | 0 | `Ok(())` |
| `push(3)` | 2 | 0 | write 2 | 3 | 0 | `Ok(())` |
| `pop()` | 3 | 0 | read 0 | 3 | 1 | `Some(1)` |
| `pop()` | 3 | 1 | read 1 | 3 | 2 | `Some(2)` |
| `pop()` | 3 | 2 | read 2 | 3 | 3 | `Some(3)` |
| `pop()` | 3 | 3 | none | 3 | 3 | `None` |

## Time and Space Complexity

| Operation | Time | Space |
|---|---|---|
| `push`, `pop` | `O(1)`: two atomic loads, one store, one slot move | none |
| `len`, `is_empty`, `is_full` | `O(1)` | none |
| drop | `O(len)` | none |
| memory | | `N` slots of `size_of::<T>()` plus two `usize` indices, inline |

The ring never blocks and never allocates after construction. The producer and consumer
still share the cache lines holding `head` and `tail`, so heavy traffic on both sides
causes the false sharing described in chapter 48; production rings pad the two indices
onto separate cache lines.

## Limitations

**The single-producer, single-consumer rule is not enforced, so the safe API admits
undefined behaviour.** `push` and `pop` take `&self`, and `SpscRing` is `Sync`. Nothing
stops two threads holding an `Arc<SpscRing<T, N>>` from both calling `push`. Both can
load the same `tail`, write the same slot concurrently, and store the same new `tail`,
so one value is lost and the slot write is a data race. That is undefined behaviour
reachable from safe code, which means the `unsafe impl Sync` is unsound as written.

The idiomatic repair is to encode the rule in types. A `split` method hands out one
`Producer` with `push` and one `Consumer` with `pop`. Each handle is `Send`, so it can be
moved to its thread, and neither is `Clone` or `Sync`, so there can be only one of each
and neither can be shared:

```rust
pub struct Producer<'a, T, const N: usize> {
    ring: &'a SpscRing<T, N>,
    _not_sync: PhantomData<Cell<()>>,
}

pub struct Consumer<'a, T, const N: usize> {
    ring: &'a SpscRing<T, N>,
    _not_sync: PhantomData<Cell<()>>,
}

impl<T: Send, const N: usize> SpscRing<T, N> {
    /// Borrowing `self` mutably guarantees this is the only split.
    pub fn split(&mut self) -> (Producer<'_, T, N>, Consumer<'_, T, N>) {
        let ring: &Self = self;
        (
            Producer { ring, _not_sync: PhantomData },
            Consumer { ring, _not_sync: PhantomData },
        )
    }
}
```

`push` and `pop` then move to `Producer` and `Consumer`, and become private on the ring.
`PhantomData<Cell<()>>` removes the automatic `Sync` implementation while keeping
`Send`.

**Index continuity assumes a power-of-two capacity after wrap-around.** When `tail`
wraps from `usize::MAX` to 0, the slot index jumps from `usize::MAX % N` to 0, which is
the next slot only when `N` divides `2^64`. With any other `N`, the ring would misplace
items after 2^64 operations. The limit is unreachable in practice, and restricting `N`
to powers of two would also let `% N` become a mask.

**Busy retrying is the caller's job.** A full or empty ring returns immediately. The
tests retry with `yield_now`, which uses a core while waiting. A blocking wrapper needs
a way to park and wake the other side, such as a futex or a condition variable, which
reintroduces some of the cost the design removes.

**The array is inline.** A ring of 4,096 `u64` values is 32 KiB inside the struct, and
constructing it on the stack before moving it into an `Arc` can overflow a small
thread stack. Large rings are better allocated on the heap.

## Summary

- An SPSC ring gives the tail index to the producer and the head index to the consumer,
  so each side writes only its own atomic and no lock or compare-and-swap is needed.
- Writing the slot before publishing `tail`, and reading it before publishing `head`,
  guarantees that neither side sees a slot the other is still using.
- `UnsafeCell<MaybeUninit<T>>` slots in a const-generic array hold values without heap
  allocation; `MaybeUninit::write` and `assume_init_read` move values in and out
  without dropping uninitialized memory.
- A `Drop` implementation must drain the ring, because `MaybeUninit` never drops its
  contents.
- Because `push` and `pop` take `&self` on a `Sync` type, two producers can race; split
  handles that are `Send` and not `Sync` enforce the single-producer rule in the types.

## References

- Mara Bos, *Rust Atomics and Locks*, O'Reilly Media, 2023, Chapter 5, "Building Our
  Own Channels".
- Standard library, [`std::mem::MaybeUninit`](https://doc.rust-lang.org/std/mem/union.MaybeUninit.html) and [`std::array::from_fn`](https://doc.rust-lang.org/std/array/fn.from_fn.html).
- The Rust Reference, [Const generics](https://doc.rust-lang.org/reference/items/generics.html#const-generics).
- The `crossbeam` project, [`ArrayQueue`](https://docs.rs/crossbeam/latest/crossbeam/queue/struct.ArrayQueue.html), a bounded lock-free MPMC queue.
