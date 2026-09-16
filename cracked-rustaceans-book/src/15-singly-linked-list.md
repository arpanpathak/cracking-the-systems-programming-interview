# 15. Singly Linked List {#singly-linked-list}

*Source file: [`src/bin/singly_linked_list.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/singly_linked_list.rs). Run it with
`cargo run --bin singly_linked_list`.*

## Problem Statement

Build a list whose node set is described by an algebraic data type, with constant time
insertion and removal at the front.

## Designing a Solution

```text
List<T> = Empty
        | Node { value: T, next: Box<List<T>> }
```

The layout is the same as `Option<Box<ListNode>>` from Chapter 14, with the empty case
named in the type rather than expressed by `None`. The end of the list is
`List::Empty`, and an empty list is `List::Empty` as well, so there is no separate
sentinel and no nullable field.

```text
list = Node { value: 0, next: Box<Node { value: 1, next: Box<Empty> }> }

  list
   |
   v
 +---------------+     +---------------+     +--------+
 | value: 0      | --> | value: 1      | --> | Empty  |
 | next: Box --- |     | next: Box --- |     +--------+
 +---------------+     +---------------+
```

`push_front` and `pop_front` both take the whole list out of `self` with
`std::mem::replace`, decide what to do with it, and write the result back. That is what
lets the code move a list value without cloning it and without holding a borrow of
`self` across the move.

```text
push_front(0) on [1, 2]

before:  self = Node { 1, next: [2] }

replace(self, Empty) returns the old list [1, 2] and leaves self = Empty
then:    self = Node { 0, next: Box::new([1, 2]) }

pop_front() on [0, 1, 2]

replace(self, Empty) returns [0, 1, 2] and leaves self = Empty
the node is destructured into value = 0 and next = Box([1, 2])
then:    self = *next = [1, 2]
returns: Some(0)
```

## Implementation

<p class="listing"><span class="listing-label">Listing 15.1</span> The complete program, with its tests. <code>src/bin/singly_linked_list.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/singly_linked_list.rs">read the file on GitHub</a></p>

`push_front` moves the old list into a new `Box`. The old value comes from
`std::mem::replace(self, List::Empty)`, which leaves `self` in a valid state that the
following assignment overwrites. There is no moment at which `self` is uninitialised,
and the code needs neither `unsafe` nor `Option`.

`pop_front` destructures the taken value. `*self = *next` moves the inner list out of
its box and into `self`; the box itself is freed, so the popped node is released rather
than remembered.

`Link::new(old)` is `Box::new(old)` written through the type alias, which reads as
"a new link holding the old list".

The two functions carry `/// O(1)` doc comments and nothing else. They are the only
documentation in the file beyond the module header and the type sketch.

## Intuition

```text
push_front(2)   self = Node { 2, next: Empty }
push_front(1)   self = Node { 1, next: Node { 2, next: Empty } }
push_front(0)   self = Node { 0, next: Node { 1, next: Node { 2, next: Empty } } }

len()           three recursive calls plus the empty base case, returning 3

pop_front()     replace returns the node holding 0
                value = 0, next = Box(Node { 1, ... })
                self = Node { 1, next: Node { 2, next: Empty } }
                returns Some(0)

pop_front()     returns Some(1), self = Node { 2, next: Empty }
pop_front()     returns Some(2), self = Empty
pop_front()     replace returns Empty, so the match yields None
```

## Time and Space Complexity

| Operation | Time | Space |
|---|---|---|
| `push_front` | `O(1)` | one allocation |
| `pop_front` | `O(1)` | frees one allocation |
| `is_empty` | `O(1)` | none |
| `len` | `O(n)` | `O(n)` stack frames |

## Limitations

**`List::new` has no `Default` implementation.** Clippy's `new_without_default` lint
fires on this pattern, and the reason it exists is that a caller writing a generic
function over many types expects `Default` to work. An `impl<T> Default for List<T>`
with a two-line body fixes it.

**`len` is recursive.** It walks the list with one stack frame per node, so a list long
enough to matter cannot be measured. An iterative version keeps a `&List<T>` cursor and
counts in a `while let` loop.

**Dropping the list is recursive.** The derived destructor for `List<T>` follows the
`next` links, one frame per node, and a long list aborts the process when it goes out of
scope. This is the hazard described in Chapter 14, and the same fix applies: a manual
`Drop` implementation that unlinks nodes into a loop.

**`pop_front` is `O(1)` at any length, but the drop that follows is not.** For a list of
a million nodes, the operation the API advertises is cheap and the work the program does
when the list is released is `O(n)`. The two have to be considered together.

**There is no `Clone`, no `Debug`, and no iterator.** A caller cannot print the list,
cannot copy it, and cannot write `for value in &list`.

## Summary

- The layout is the one of Chapter 14 with the empty case named in the type: `Empty`
  ends the list and is also the empty list, so there is no sentinel and no nullable
  field.
- `push_front` and `pop_front` are constant time because both work at the head, where
  ownership of the rest of the list can be moved in one step.
- `len` and the derived destructor are recursive, so the length of the list is bounded
  by the stack rather than by the heap.
- Naming the empty case costs nothing at run time here, and it buys a `match` that the
  compiler checks for exhaustiveness at every use.

## References

- The Rust Book, [Defining an enum](https://doc.rust-lang.org/book/ch06-01-defining-an-enum.html).
- Standard library, [`std::mem::replace`](https://doc.rust-lang.org/std/mem/fn.replace.html).
- Clippy, [`new_without_default`](https://rust-lang.github.io/rust-clippy/master/index.html#new_without_default).
