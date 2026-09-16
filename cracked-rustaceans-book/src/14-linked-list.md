# 14. Reverse a Linked List {#reverse-linked-list}

*Source file: [`src/problems/linked_list.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/linked_list.rs). Test it with
`cargo test linked_list`.*

## Problem Statement

Reverse a singly linked list in place and return its new head. In place means no extra
node allocations: the nodes are re-linked, not copied.

## Designing a Solution

```text
head: Option<Box<ListNode>>

  head
   |
   v
 +--------+     +--------+     +--------+
 | 1 next | --> | 2 next | --> | 3 next | --> None
 +--------+     +--------+     +--------+
  heap           heap           heap
```

Three properties follow from `Option<Box<ListNode>>`.

`None` is the end of the list, so an empty list is the value `None` rather than a node
with a flag, and there is no sentinel to keep consistent.

The list owns its nodes. Handing over the head hands over the whole list, so there is no
way to hold a list whose nodes have been freed and no separate deallocation call.

A link is one pointer wide. The compiler stores `None` in the null pointer, which is
never a valid address for a `Box`, so no discriminant byte is added.

Reversal is one loop over three bindings. In a language with unrestricted pointers it is
three assignments per node; in Rust the same algorithm is written by taking ownership of
one node at a time, which is what makes it checkable.

```text
initial   previous = None            current = Some(1 -> 2 -> 3 -> None)

step 1    current = node.next.take()   current  = Some(2 -> 3 -> None)
          node.next = previous         node     = Some(1 -> None)
          previous = Some(node)        previous = Some(1 -> None)

step 2    current = Some(3 -> None)    previous = Some(2 -> 1 -> None)
step 3    current = None               previous = Some(3 -> 2 -> 1 -> None)

the loop ends because current is None, and the answer is previous
```

`Option::take` is the operation that makes this work. It moves the successor out of
`node.next` and leaves `None` behind, so the node under the loop's cursor stands alone
while the rest of the list is held in a separate binding. Without `take`, the assignment
`node.next = previous` would have to write through a reference that `current` still
holds, which the borrow checker rejects.

## Implementation

<p class="listing"><span class="listing-label">Listing 14.1</span> The complete module, with its tests. <code>src/problems/linked_list.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/linked_list.rs">read the file on GitHub</a></p>

`from_slice` builds the list backwards, from the last value to the first, so each new
node takes the list built so far as its successor. Building forwards would need a
mutable reference to the tail.

`to_vec` takes the list by value, which lets each node be dropped as the traversal
proceeds: the value is copied out and the successor moves into `current`, so the node
that was just read is freed at the end of the iteration. A version that took
`&Option<Box<ListNode>>` would leave the list alive and would need the caller to drop it
afterwards.

`while let Some(mut node) = current` binds the node by value, and the `mut` is required
because the body assigns to `node.next`. The three statements in the body are the
algorithm: detach the successor, point backwards, advance `previous`.

## Intuition

```text
input: 1 -> 2 -> 3 -> None

iteration   node   current after take   node.next after assignment   previous
start       -      Some(1 -> 2 -> 3)    -                            None
1           1      Some(2 -> 3)         None                         Some(1)
2           2      Some(3)              Some(1)                      Some(2 -> 1)
3           3      None                 Some(2 -> 1)                 Some(3 -> 2 -> 1)

current is None, so the loop ends and previous is returned.
```

## Time and Space Complexity

| Operation | Time | Space |
|---|---|---|
| `reverse_list` | `O(n)` | `O(1)`; no allocation, only pointer writes |
| `from_slice` | `O(n)` | `O(n)`, one allocation per node |
| `to_vec` | `O(n)` | `O(n)` for the result, and it frees the nodes |

## Limitations

**A long list is dropped recursively.** The compiler's derived destructor for
`Option<Box<ListNode>>` follows the `next` links, one stack frame per node. A list of a
few hundred thousand nodes overflows the thread stack when it is dropped, and a stack
overflow aborts the process rather than unwinding. This affects every caller, including
one that only reverses a list built elsewhere, because the destructor runs when the last
owner goes out of scope.

**`to_vec` consumes the list.** A caller that wants both the reversed list and its values
has to clone one of them, and `ListNode` does not implement `Clone`.

**`from_slice` allocates one box per element.** For a long slice that is a long chain of
small allocations, each with its own allocator overhead. An array-based representation
holds the same data in one allocation, at the cost of not being a linked list.

**The value type is fixed at `i32`.** Nothing in the algorithm depends on the value type,
and the declaration is not generic.

## Summary

- `Option<Box<ListNode>>` states three things in the type: `None` is the end of the
  list, the list owns its nodes, and a link is one pointer wide because `None` is
  stored in the null address.
- The reversal is a sequence of ownership moves rather than pointer edits: each node is
  taken out of the old list, its `next` replaced, and the node pushed onto the new
  head. Nothing is allocated.
- Because each node is moved once, the reversal is `O(n)` time and `O(1)` space.
- The derived destructor is recursive, so a list long enough to reverse in constant
  space can still exhaust the stack when it is dropped. Chapter 38 measures that and
  writes the iterative destructor.

## References

- The Rust Book, [Enabling recursive types with boxes](https://doc.rust-lang.org/book/ch15-01-box.html).
- Standard library, [`Option::take`](https://doc.rust-lang.org/std/option/enum.Option.html#method.take).
- Standard library, [`Box`](https://doc.rust-lang.org/std/boxed/struct.Box.html).
