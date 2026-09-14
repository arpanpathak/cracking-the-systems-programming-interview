# 38. Four List Layouts and the Recursive Drop {#list-layouts}

*Source files: [`benchmarking_examples/lists/`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/benchmarking_examples/lists/), the three demonstration programs [`benchmarking_examples/list_box.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/benchmarking_examples/list_box.rs), [`benchmarking_examples/list_enum.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/benchmarking_examples/list_enum.rs), and [`benchmarking_examples/list_drop.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/benchmarking_examples/list_drop.rs), and the benchmark in [`benchmarking_examples/benchmark.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/benchmarking_examples/benchmark.rs). Run the benchmark with `cargo run --release --bin benchmark list`.*

## Problem Statement

Implement a stack-shaped singly linked list with `push_front`, `pop_front`, and
`is_empty`, in each of four variants:

| variant | node layout | deallocation |
|---|---|---|
| `box` | `Option<Box<Node<T>>>` | compiler-generated |
| `enum` | `enum ListNode<T> { Empty, Next(T, Box<ListNode<T>>) }` | compiler-generated |
| `box+drop` | `Option<Box<Node<T>>>` | a hand-written iterative `Drop` |
| `enum+drop` | `enum ListNode<T>` | a hand-written iterative `Drop` |

Measure the time to push and to drop a list in each variant, find the largest list
the recursive variants can free, and check that the iterative variants can free a
much larger one.

## Designing a Solution

**One trait, four implementations.** A trait with the operations every variant
supports lets the benchmark be written once as a generic function. Each call is
monomorphised for its variant, so the trait adds no dispatch cost to the measurement.

**Why the default drop recurses.** When a `Box<Node<T>>` is dropped, the compiler
drops the node's fields, and one of those fields is the next `Box`. Dropping it drops
its node, whose `next` is dropped in turn. Each step is a nested call, so freeing a
list of `n` nodes needs `n` stack frames at once. The diagram below shows the stack at the
deepest point.

```text
drop(head: Option<Box<Node>>)        frame 1, node 1 not yet freed
  drop(node1.next)                   frame 2, node 2 not yet freed
    drop(node2.next)                 frame 3, node 3 not yet freed
      drop(node3.next = None)        frame 4, returns
    free node 3
  free node 2
free node 1
```

**The iterative fix.** A hand-written `Drop` moves each node's `next` out before the
node is freed. When the node is then dropped, its `next` is already `None`, so the
drop does not descend, and the loop moves to the detached tail. The stack depth is
constant.

## Implementation

### The trait

```rust
//! Singly linked lists in four variants, so one benchmark loop can cover all of
//! them.
//!
//! The variants differ only in how a node is stored and in how the list frees
//! itself. `boxed` and `enum_node` free a chain of boxes recursively, which
//! overflows the stack past roughly 265,000 nodes. `boxed_drop` and `enum_drop`
//! unlink iteratively and scale.

pub mod boxed;
pub mod boxed_drop;
pub mod enum_drop;
pub mod enum_node;

/// The operations every variant supports, so the benchmark can be written once.
pub trait SinglyList<T>: Sized {
    /// A new, empty list.
    fn new() -> Self;

    /// Adds `value` to the front of the list.
    fn push_front(&mut self, value: T);

    /// Removes and returns the front value, if there is one.
    fn pop_front(&mut self) -> Option<T>;

    /// Whether the list holds nothing.
    fn is_empty(&self) -> bool;

    /// The variant's name, for benchmark output and error messages.
    fn variant() -> &'static str;
}
```

`fn new() -> Self` in a trait requires `Self: Sized`, which the bound `SinglyList<T>:
Sized` states for every method at once. `variant` is an associated function rather
than a method, so the benchmark can print a name without constructing a list.

### The boxed layout

```rust
//! `Option<Box<Node<T>>>`: one heap allocation per node.
//!
//! Pushing takes the old head and boxes it inside the new node. Freeing the head
//! frees its `next`, which frees its `next`, so the drop recurses once per
//! element and overflows the stack on a long list.

use super::SinglyList;

struct Node<T> {
    value: T,
    next: Option<Box<Node<T>>>,
}

pub struct LinkedList<T> {
    head: Option<Box<Node<T>>>,
}

impl<T> SinglyList<T> for LinkedList<T> {
    fn new() -> Self {
        Self { head: None }
    }

    fn push_front(&mut self, value: T) {
        self.head = Some(Box::new(Node {
            value,
            // .take() leaves None in its place and extracts the old head
            next: self.head.take(),
        }));
    }

    fn pop_front(&mut self) -> Option<T> {
        self.head.take().map(|node| {
            // Point the list head to the next node in line
            self.head = node.next;
            // Return the unboxed value
            node.value
        })
    }

    fn is_empty(&self) -> bool {
        self.head.is_none()
    }

    fn variant() -> &'static str {
        "box"
    }
}
```

`self.head.take()` moves the old head out and leaves `None` in the field, so the new
node can own it without an intermediate state in which the list has two owners.
`pop_front` uses `map` on the taken head: the closure moves `node.next` back into the
list and returns `node.value`, and the `Box` holding the node is freed when the closure
returns.

### The enumeration layout

```rust
//! `enum ListNode<T> { Empty, Next(T, Box<ListNode<T>>) }`.
//!
//! Same shape as the boxed variant, written with an enum instead of an
//! `Option`. The enum cannot contain itself by value, so the recursive arm holds
//! a `Box`. The drop is recursive for the same reason.

use super::SinglyList;

enum ListNode<T> {
    Empty,
    Next(T, Box<ListNode<T>>),
}

pub struct LinkedList<T> {
    head: ListNode<T>,
}

impl<T> SinglyList<T> for LinkedList<T> {
    fn new() -> Self {
        Self {
            head: ListNode::Empty,
        }
    }

    fn push_front(&mut self, value: T) {
        // Extract the old head and leave Empty in its place
        let old_head = std::mem::replace(&mut self.head, ListNode::Empty);

        // Wrap the old head inside a Box behind the new value
        self.head = ListNode::Next(value, Box::new(old_head));
    }

    fn pop_front(&mut self) -> Option<T> {
        let old_head = std::mem::replace(&mut self.head, ListNode::Empty);

        match old_head {
            ListNode::Empty => None,
            ListNode::Next(value, next_node) => {
                // Point the list head to the next node in the sequence
                self.head = *next_node;
                Some(value)
            }
        }
    }

    fn is_empty(&self) -> bool {
        matches!(self.head, ListNode::Empty)
    }

    fn variant() -> &'static str {
        "enum"
    }
}
```

The enumeration cannot use `take`, which exists only on `Option`, so it uses
`std::mem::replace(&mut self.head, ListNode::Empty)` to the same effect. `self.head =
*next_node` moves the boxed tail out of its box into the list head and frees the box.

The two layouts differ in what the list head holds. `Option<Box<Node<u64>>>` is 8
bytes, one pointer, because the null pointer encodes `None`. `ListNode<u64>` is 16
bytes: a `u64` and a `Box`. It needs no separate discriminant, because `Box` is never
null and the compiler uses the null pattern to encode `Empty`. The heap nodes are 16
bytes in both layouts. The difference is in the moves: the boxed variant's push moves
an 8-byte pointer out of the head, while the enumeration variant's push moves a
16-byte `ListNode` out of the head and into a new box.

### The iterative destructors

The two `+drop` variants repeat the push and pop code of their counterparts
unchanged and add a `Drop` implementation.

```rust
//! `Option<Box<Node<T>>>` with an iterative `Drop`.
//!
//! Push and pop are identical to [`boxed`](super::boxed); only freeing changes.
//! Dropping a node would otherwise drop its `next` and recurse once per element,
//! so the list is unlinked in a loop before any node is freed.

use super::SinglyList;

struct Node<T> {
    value: T,
    next: Option<Box<Node<T>>>,
}

pub struct LinkedList<T> {
    head: Option<Box<Node<T>>>,
}

impl<T> SinglyList<T> for LinkedList<T> {
    fn new() -> Self {
        Self { head: None }
    }

    fn push_front(&mut self, value: T) {
        self.head = Some(Box::new(Node {
            value,
            next: self.head.take(),
        }));
    }

    fn pop_front(&mut self) -> Option<T> {
        self.head.take().map(|node| {
            self.head = node.next;
            node.value
        })
    }

    fn is_empty(&self) -> bool {
        self.head.is_none()
    }

    fn variant() -> &'static str {
        "box+drop"
    }
}

impl<T> Drop for LinkedList<T> {
    fn drop(&mut self) {
        // Walk the chain and unlink each node before it is freed, so no node's
        // drop has to carry the rest of the list on the stack.
        let mut current = self.head.take();
        while let Some(mut node) = current {
            current = node.next.take();
        }
    }
}
```

`while let Some(mut node) = current` takes ownership of one node per iteration.
`current = node.next.take()` detaches the rest of the list before `node` goes out of
scope at the end of the loop body. The node is then freed with `next == None`, so its
destructor has nothing to recurse into.

```rust
//! `enum ListNode<T>` with an iterative `Drop`.
//!
//! Push and pop are identical to [`enum_node`](super::enum_node); only freeing
//! changes. The recursive arm holds a `Box`, so the default drop walks the chain
//! on the stack. This one replaces the head with `Empty`, then takes the box out
//! of each node in turn.

use super::SinglyList;

enum ListNode<T> {
    Empty,
    Next(T, Box<ListNode<T>>),
}

pub struct LinkedList<T> {
    head: ListNode<T>,
}

impl<T> SinglyList<T> for LinkedList<T> {
    fn new() -> Self {
        Self {
            head: ListNode::Empty,
        }
    }

    fn push_front(&mut self, value: T) {
        let old_head = std::mem::replace(&mut self.head, ListNode::Empty);
        self.head = ListNode::Next(value, Box::new(old_head));
    }

    fn pop_front(&mut self) -> Option<T> {
        let old_head = std::mem::replace(&mut self.head, ListNode::Empty);

        match old_head {
            ListNode::Empty => None,
            ListNode::Next(value, next_node) => {
                self.head = *next_node;
                Some(value)
            }
        }
    }

    fn is_empty(&self) -> bool {
        matches!(self.head, ListNode::Empty)
    }

    fn variant() -> &'static str {
        "enum+drop"
    }
}

impl<T> Drop for LinkedList<T> {
    fn drop(&mut self) {
        // Take the chain out of the list first, then step it forward one node at
        // a time. Each node has already lost its `next` by the time it is freed,
        // so the drop stays on the heap.
        let mut current = std::mem::replace(&mut self.head, ListNode::Empty);
        while let ListNode::Next(_, next) = current {
            current = *next;
        }
    }
}
```

`while let ListNode::Next(_, next) = current` destructures the current node, binding
the boxed tail and dropping the value. `current = *next` moves the tail out of its box.
The assignment drops the previous value of `current`, which at that point has already
been moved out of by the pattern, so nothing recursive happens.

### The demonstration programs

```rust
//! Demo of the `Option<Box<Node<T>>>` list in `lists::boxed`.
//!
//! Run with: cargo run --bin list_box

use nvidia_rust_interview_lab::lists::SinglyList;
use nvidia_rust_interview_lab::lists::boxed::LinkedList;

fn main() {
    let mut list = LinkedList::new();

    list.push_front(10);
    list.push_front(20);
    list.push_front(30);

    assert_eq!(list.pop_front(), Some(30));
    assert_eq!(list.pop_front(), Some(20));
    assert_eq!(list.pop_front(), Some(10));
    assert_eq!(list.pop_front(), None);
    assert!(list.is_empty());

    println!("All tests passed successfully!");
}
```

```rust
//! Demo of the `enum ListNode<T>` list in `lists::enum_node`.
//!
//! Run with: cargo run --bin list_enum

use nvidia_rust_interview_lab::lists::SinglyList;
use nvidia_rust_interview_lab::lists::enum_node::LinkedList;

fn main() {
    let mut list = LinkedList::new();
    list.push_front(42);
    list.push_front(100);

    assert_eq!(list.pop_front(), Some(100));
    assert_eq!(list.pop_front(), Some(42));
    assert_eq!(list.pop_front(), None);
    assert!(list.is_empty());
}
```

```rust
//! Demo of the iterative `Drop` in `lists::boxed_drop`.
//!
//! The same program against `lists::boxed` aborts with a stack overflow at this
//! size, because that variant frees its chain recursively.
//!
//! Run with: cargo run --release --bin list_drop

use nvidia_rust_interview_lab::lists::SinglyList;
use nvidia_rust_interview_lab::lists::boxed_drop::LinkedList;

fn main() {
    const N: u64 = 5_000_000;

    let mut list = LinkedList::new();
    for value in 0..N {
        list.push_front(value);
    }
    println!("built a list of {N} nodes");

    list.pop_front();
    println!("dropping the remaining {} nodes", N - 1);

    drop(list);
    println!("dropped without recursing");
}
```

The programs import both the trait and the concrete type. Without `use
nvidia_rust_interview_lab::lists::SinglyList`, the calls to `LinkedList::new` and
`push_front` would not resolve, because trait methods are in scope only when the trait
is.

### The benchmark loop

The first listing below shows `main`, which dispatches between the cache benchmark of
chapter 40 and the list benchmark, and the second shows the list benchmark itself.

```rust
//! One main for every benchmark in the lab.
//!
//! Usage:
//!   cargo run --release --bin benchmark                    # cache, then lists
//!   cargo run --release --bin benchmark cache              # cache only
//!   cargo run --release --bin benchmark list               # all four variants
//!   cargo run --release --bin benchmark list enum 500000   # one variant, one size
//!
//! The recursive list variants abort with a stack overflow past roughly 265,000
//! nodes, so run them below that size or on their own.

use std::hint::black_box;
use std::time::{Duration, Instant};

use nvidia_rust_interview_lab::cache::Cache;
use nvidia_rust_interview_lab::cache::arena::LruCache as ArenaCache;
use nvidia_rust_interview_lab::cache::rc_list::LruCache as RcCache;
use nvidia_rust_interview_lab::lists::SinglyList;
use nvidia_rust_interview_lab::lists::{boxed, boxed_drop, enum_drop, enum_node};

const CACHE_CAPACITY: usize = 65_536;
const KEY_SPACE: u64 = 131_072;
const OPERATIONS: u64 = 10_000_000;
const DEFAULT_LIST_ELEMENTS: usize = 200_000;
/// Timed passes per cache; the fastest is reported, since a slow pass is noise.
const CACHE_RUNS: usize = 3;
/// Timed passes per list variant.
const LIST_RUNS: usize = 3;

fn main() {
    let arguments: Vec<String> = std::env::args().skip(1).collect();

    match arguments.first().map(String::as_str) {
        Some("cache") => cache_benchmark(),
        Some("list") => {
            let variant = arguments.get(1).map(String::as_str);
            let elements = arguments
                .get(2)
                .and_then(|value| value.parse().ok())
                .unwrap_or(DEFAULT_LIST_ELEMENTS);
            list_benchmark(variant, elements);
        }
        _ => {
            cache_benchmark();
            println!();
            list_benchmark(None, DEFAULT_LIST_ELEMENTS);
        }
    }
}
```

```rust
// ---------------------------------------------------------------------------
// Lists: four variants, one loop
// ---------------------------------------------------------------------------

fn list_benchmark(variant: Option<&str>, elements: usize) {
    println!(
        "Singly linked list: push {} values, pop them back in order, then drop a full list",
        with_thousands(elements as u64)
    );
    println!("Best of {LIST_RUNS} runs per variant, allocator warmed up.\n");
    println!(
        "  {:<10} {:>12} {:>13} {:>13}",
        "variant", "elements", "push", "drop"
    );
    println!("  {}", "-".repeat(52));

    match variant {
        Some("box") => run_list::<boxed::LinkedList<u64>>(elements),
        Some("enum") => run_list::<enum_node::LinkedList<u64>>(elements),
        Some("box+drop") => run_list::<boxed_drop::LinkedList<u64>>(elements),
        Some("enum+drop") => run_list::<enum_drop::LinkedList<u64>>(elements),
        _ => {
            run_list::<boxed::LinkedList<u64>>(elements);
            run_list::<enum_node::LinkedList<u64>>(elements);
            run_list::<boxed_drop::LinkedList<u64>>(elements);
            run_list::<enum_drop::LinkedList<u64>>(elements);
        }
    }
}

fn run_list<L: SinglyList<u64>>(elements: usize) {
    // Warm the allocator first: without this the first variant in a process pays
    // for fresh heap pages and looks several times slower than an identical one.
    let mut warm_up = L::new();
    for value in 0..elements as u64 {
        warm_up.push_front(value);
    }
    drop(warm_up);

    let mut best_push = Duration::MAX;
    let mut best_drop = Duration::MAX;

    for _ in 0..LIST_RUNS {
        let mut list = L::new();

        let start = Instant::now();
        for value in 0..elements as u64 {
            list.push_front(value);
        }
        best_push = best_push.min(start.elapsed());

        // Pop every value back and check the order, so a broken list cannot post
        // a fast time.
        let mut expected = elements as u64;
        while let Some(value) = list.pop_front() {
            expected -= 1;
            assert_eq!(value, expected, "{} lost LIFO order", L::variant());
        }
        assert_eq!(expected, 0);
        black_box(expected);

        // Rebuild, then time the drop of a full list. This is where the
        // recursive variants overflow the stack.
        for value in 0..elements as u64 {
            list.push_front(value);
        }
        let start = Instant::now();
        drop(list);
        best_drop = best_drop.min(start.elapsed());
    }

    println!(
        "  {:<10} {:>12} {best_push:>13.2?} {best_drop:>13.2?}",
        L::variant(),
        with_thousands(elements as u64)
    );
}

fn with_thousands(value: u64) -> String {
    let digits = value.to_string();
    let mut out = String::with_capacity(digits.len() + digits.len() / 3);
    for (index, digit) in digits.chars().enumerate() {
        if index > 0 && (digits.len() - index) % 3 == 0 {
            out.push(',');
        }
        out.push(digit);
    }
    out
}
```

`run_list::<boxed::LinkedList<u64>>(elements)` names the variant with a turbofish. The
generic function calls `L::new()`, `push_front`, and `pop_front` through the trait,
and each instantiation compiles to direct calls on its variant.

Four measurement decisions are visible in `run_list`:

- **A warm-up pass.** The first list built in a process pays for fresh heap pages.
  Building and dropping one list before timing removes that cost from the first
  variant measured.
- **Best of three.** Each timed pass records its duration, and the minimum is
  reported, because interference from the rest of the system only ever adds time.
- **A correctness check inside the timed program.** Every value is popped back and
  compared with the expected LIFO order, so a broken variant fails instead of
  posting a fast time.
- **`black_box`.** `std::hint::black_box(expected)` tells the optimiser to treat the
  value as used, so the check cannot be removed as dead code.

`with_thousands` formats counts with separators for the report.

## Intuition

The benchmark was run in release mode on an NVIDIA Jetson board,
an 8-core Cortex-A78AE with an 8 MiB main-thread stack. The recorded results are in
`BENCHMARKS.md` in the repository.

**The largest list each variant can free**

| variant | 260,000 nodes | 270,000 nodes | 5,000,000 nodes |
|---|---|---|---|
| `box` | completed | aborted | not attempted |
| `enum` | completed | aborted | not attempted |
| `box+drop` | completed | completed | completed |
| `enum+drop` | completed | completed | completed |

The recursive variants abort between 260,000 and 270,000 nodes with:

```text
thread 'main' has overflowed its stack
fatal runtime error: stack overflow, aborting
```

An 8 MiB stack divided by roughly 265,000 frames is about 32 bytes per frame.

The timed results, as best of three passes:

```text
  variant        elements          push          drop
  ----------------------------------------------------
  box             200,000        2.40ms        3.23ms
  enum            200,000        3.42ms        3.20ms
  box+drop        200,000        2.32ms        2.91ms
  enum+drop       200,000        3.62ms        2.52ms

  box+drop      5,000,000       58.11ms       72.32ms
  enum+drop     5,000,000       90.98ms       67.51ms
```

Two conclusions follow. First, the enumeration layout pushes more slowly, about
17 ns per element against 12 ns, which is consistent with each push moving a 16-byte
node value rather than an 8-byte pointer. Second, the iterative destructor is not
meaningfully slower than the recursive one; at 200,000 nodes it is slightly faster.
Its value is that it removes the size limit.

`box` and `box+drop` share the same push code, and their push times of 2.40 ms and
2.32 ms agree within run-to-run variation. That agreement is a check on the
measurement itself.

## Time and Space Complexity

| Operation | Time | Stack space | Heap |
|---|---|---|---|
| `push_front` | `O(1)` | `O(1)` | one allocation |
| `pop_front` | `O(1)` | `O(1)` | one deallocation |
| default drop of `n` nodes | `O(n)` | `O(n)` frames | `n` deallocations |
| iterative drop of `n` nodes | `O(n)` | `O(1)` | `n` deallocations |

## Limitations

**The limit depends on the stack size.** 265,000 nodes is the figure for an 8 MiB
main-thread stack. A spawned thread has a 2 MiB stack by default, so the same program
on a worker thread fails at roughly a quarter of that length. The iterative variants
have no such dependency.

**The `+drop` variants duplicate code.** Push and pop are copied from their
counterparts so that each file is complete. A shared inner type with the `Drop`
added in a wrapper would remove the duplication, at the cost of one more type.

**The enumeration layout stores a boxed `Empty`.** The first push boxes the initial
`Empty` head, so the last heap node of every non-empty list holds no value. The
allocation count is still one per push, because the most recent value lives inline in
the list head, but one of the `n` heap blocks carries no data.

**The measurement covers one allocator and one machine.** The ratios are the figures
intended to carry over. The absolute times depend on the system allocator, the
compiler version, and the processor.

## Summary

- A trait with a `Sized` bound lets one generic benchmark exercise several
  implementations with no dispatch overhead.
- A compiler-generated destructor for a chain of boxes recurses once per node, and an
  8 MiB stack is exhausted at roughly 265,000 nodes.
- An iterative `Drop` that detaches each node's successor before freeing it runs in
  constant stack space and frees five million nodes without difficulty.
- The iterative destructor is not slower. Its benefit is the removal of the size
  limit.
- A benchmark needs a warm-up pass, several repetitions reported as the minimum, and
  a correctness check that the optimiser cannot remove.

## References

- The Rust Book, [Running code on cleanup with the `Drop` trait](https://doc.rust-lang.org/book/ch15-03-drop.html).
- Aria Beingessner and contributors, *Learning Rust With Entirely Too Many Linked
  Lists*, [Drop](https://rust-unofficial.github.io/too-many-lists/first-drop.html).
- Standard library, [`std::hint::black_box`](https://doc.rust-lang.org/std/hint/fn.black_box.html).
- Standard library, [`std::thread`](https://doc.rust-lang.org/std/thread/index.html#stack-size), on the default stack size of spawned threads.
