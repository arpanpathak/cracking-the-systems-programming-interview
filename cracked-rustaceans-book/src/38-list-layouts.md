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

<p class="listing"><span class="listing-label">Listing 38.1</span> The trait. <code>benchmarking_examples/lists/mod.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/benchmarking_examples/lists/mod.rs">read the file on GitHub</a></p>

`fn new() -> Self` in a trait requires `Self: Sized`, which the bound `SinglyList<T>:
Sized` states for every method at once. `variant` is an associated function rather
than a method, so the benchmark can print a name without constructing a list.

### The boxed layout

<p class="listing"><span class="listing-label">Listing 38.2</span> The boxed layout. <code>benchmarking_examples/lists/boxed.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/benchmarking_examples/lists/boxed.rs">read the file on GitHub</a></p>

`self.head.take()` moves the old head out and leaves `None` in the field, so the new
node can own it without an intermediate state in which the list has two owners.
`pop_front` uses `map` on the taken head: the closure moves `node.next` back into the
list and returns `node.value`, and the `Box` holding the node is freed when the closure
returns.

### The enumeration layout

<p class="listing"><span class="listing-label">Listing 38.3</span> The enumeration layout. <code>benchmarking_examples/lists/enum_node.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/benchmarking_examples/lists/enum_node.rs">read the file on GitHub</a></p>

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

<p class="listing"><span class="listing-label">Listing 38.4</span> The iterative destructors. <code>benchmarking_examples/lists/boxed_drop.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/benchmarking_examples/lists/boxed_drop.rs">read the file on GitHub</a></p>

`while let Some(mut node) = current` takes ownership of one node per iteration.
`current = node.next.take()` detaches the rest of the list before `node` goes out of
scope at the end of the loop body. The node is then freed with `next == None`, so its
destructor has nothing to recurse into.

<p class="listing"><span class="listing-label">Listing 38.5</span> The iterative destructors. <code>benchmarking_examples/lists/enum_drop.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/benchmarking_examples/lists/enum_drop.rs">read the file on GitHub</a></p>

`while let ListNode::Next(_, next) = current` destructures the current node, binding
the boxed tail and dropping the value. `current = *next` moves the tail out of its box.
The assignment drops the previous value of `current`, which at that point has already
been moved out of by the pattern, so nothing recursive happens.

### The demonstration programs

<p class="listing"><span class="listing-label">Listing 38.6</span> The demonstration programs. <code>benchmarking_examples/list_box.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/benchmarking_examples/list_box.rs">read the file on GitHub</a></p>

<p class="listing"><span class="listing-label">Listing 38.7</span> The demonstration programs. <code>benchmarking_examples/list_enum.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/benchmarking_examples/list_enum.rs">read the file on GitHub</a></p>

<p class="listing"><span class="listing-label">Listing 38.8</span> The demonstration programs. <code>benchmarking_examples/list_drop.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/benchmarking_examples/list_drop.rs">read the file on GitHub</a></p>

The programs import both the trait and the concrete type. Without `use
nvidia_rust_interview_lab::lists::SinglyList`, the calls to `LinkedList::new` and
`push_front` would not resolve, because trait methods are in scope only when the trait
is.

### The benchmark loop

Listing 38.9 is `main`, which dispatches between the cache benchmark of chapter 40 and
the list benchmark, and Listing 38.10 is the list benchmark itself.

<p class="listing"><span class="listing-label">Listing 38.9</span> The dispatcher, <code>main</code>. <code>benchmarking_examples/benchmark.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/benchmarking_examples/benchmark.rs">read the file on GitHub</a></p>

<p class="listing"><span class="listing-label">Listing 38.10</span> The list benchmark itself. <code>benchmarking_examples/benchmark.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/benchmarking_examples/benchmark.rs">read the file on GitHub</a></p>

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
