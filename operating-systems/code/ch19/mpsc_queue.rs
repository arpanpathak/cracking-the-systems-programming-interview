// ch19/mpsc_queue.rs: wait-free multi-producer, single-consumer queue (Vyukov).
use std::cell::UnsafeCell;
use std::ptr;
use std::sync::atomic::{AtomicPtr, Ordering};
use std::thread;

struct Node<T> {
    data: UnsafeCell<Option<T>>,
    next: AtomicPtr<Node<T>>,
}

impl<T> Node<T> {
    fn new(data: Option<T>) -> *mut Self {
        Box::into_raw(Box::new(Self {
            data: UnsafeCell::new(data),
            next: AtomicPtr::new(ptr::null_mut()),
        }))
    }
}

/// Unbounded lock-free MPSC queue using a stub-node linked list.
/// Multiple threads may call `push` concurrently; only one thread may call `pop`.
/// `head` and `tail` are isolated on separate 64-byte cache lines to prevent false sharing.
#[repr(C, align(64))]
struct MpscQueue<T> {
    head: AtomicPtr<Node<T>>, // shared by all producers (wait-free swap)
    _pad: [u8; 56],           // 8 bytes head + 56 bytes padding = 64-byte cache line
    tail: AtomicPtr<Node<T>>, // owned exclusively by the single consumer
}

// SAFETY: Ownership of `T` transfers cleanly across threads via Release-Acquire edges.
unsafe impl<T: Send> Send for MpscQueue<T> {}
// SAFETY: Producers synchronize on `head` via atomic swap; caller contract limits `pop` to one thread.
unsafe impl<T: Send> Sync for MpscQueue<T> {}

impl<T> MpscQueue<T> {
    fn new() -> Self {
        let stub = Node::new(None);
        Self {
            head: AtomicPtr::new(stub),
            _pad: [0; 56],
            tail: AtomicPtr::new(stub),
        }
    }

    /// Wait-free enqueue: atomically swap `head`, then link the previous node.
    fn push(&self, value: T) {
        let node = Node::new(Some(value));
        let prev = self.head.swap(node, Ordering::AcqRel);

        // SAFETY: `prev` is a live heap node detached from `head` by our swap.
        // The consumer cannot free `prev` until this Release store makes `prev.next` non-null.
        unsafe { (*prev).next.store(node, Ordering::Release) };
    }

    /// Single-consumer dequeue: advance stub to `next`, reclaim old stub, return payload.
    fn pop(&self) -> Option<T> {
        let tail = self.tail.load(Ordering::Relaxed);

        // SAFETY: `tail` is always a valid allocated stub owned exclusively by the single consumer.
        let next = unsafe { (*tail).next.load(Ordering::Acquire) };
        if next.is_null() {
            return None;
        }

        self.tail.store(next, Ordering::Relaxed);

        // SAFETY: `tail.next` is non-null, proving the producer finished storing `tail.next`
        // and no thread retains a pointer to `tail`.
        unsafe { drop(Box::from_raw(tail)) };

        // SAFETY: The Acquire load of `next` synchronizes-with the producer's Release store.
        // Only the consumer accesses `next.data`; concurrent producers touch only `next.next`.
        unsafe { (*(*next).data.get()).take() }
    }
}

impl<T> Drop for MpscQueue<T> {
    fn drop(&mut self) {
        let mut curr = *self.tail.get_mut();
        while !curr.is_null() {
            // SAFETY: `&mut self` guarantees exclusive access; every node in the chain was
            // allocated with `Box::into_raw` and has not yet been reclaimed.
            let node = unsafe { Box::from_raw(curr) };
            curr = node.next.into_inner();
        }
    }
}

fn main() {
    const PRODUCERS: u64 = 4;
    const PER_PRODUCER: u64 = 25_000;
    const TOTAL: u64 = PRODUCERS * PER_PRODUCER;

    let queue = &MpscQueue::<u64>::new();
    let mut consumed_sum = 0;

    thread::scope(|scope| {
        for p in 0..PRODUCERS {
            scope.spawn(move || {
                let base = p * PER_PRODUCER;
                for i in 1..=PER_PRODUCER {
                    queue.push(base + i);
                }
            });
        }

        let mut taken = 0;
        while taken < TOTAL {
            let Some(value) = queue.pop() else {
                thread::yield_now();
                continue;
            };

            consumed_sum += value;
            taken += 1;
        }
    });

    let expected = TOTAL * (TOTAL + 1) / 2;
    let verdict = if expected == consumed_sum { "yes" } else { "NO" };

    println!("producers    {PRODUCERS}");
    println!("expected sum {expected}");
    println!("consumed sum {consumed_sum}");
    println!("match        {verdict}");
}
