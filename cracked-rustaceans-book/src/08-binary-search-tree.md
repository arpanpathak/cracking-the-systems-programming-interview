# 8. Binary Search Tree {#binary-search-tree}

*Source file: [`src/bin/bst_clean.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/bst_clean.rs). Run it with `cargo run --bin bst_clean`.*

## Problem Statement

Implement a binary search tree with four operations: `insert`, `contains`, `remove`,
and `range`, which returns the values in a closed interval. Removal has a case the
others do not: a node with two children cannot be unlinked without a replacement that
preserves the ordering.

## Designing a Solution

The ordering invariant defines the structure:

```text
for every node:  every value in the left subtree  <  the node's value
                 every value in the right subtree >  the node's value
```

A lookup follows one path from the root and discards a subtree at each comparison. An
in-order traversal reads the values in ascending order, which is the usual way to test
that the invariant holds.

Removal has three shapes:

```text
delete a leaf                the link becomes Empty

delete a node with one child the child takes its place

delete a node with two       the smallest value of the right subtree takes its
children                     place; it is the next value in order, so the
                             ordering holds on both sides

example: remove 10 from
            10
           /  \
          5    15

  the right subtree is 15, whose smallest value is 15, so 15 takes the place of 10
```

```text
               10
              /  \
             5    15
            / \   / \
           3   7 12  18

remove 5  -> its only child 7 moves up
remove 10 -> 12, the successor, moves up
```

## Implementation

<p class="listing"><span class="listing-label">Listing 8.1</span> The complete program. <code>src/bin/bst_clean.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/bst_clean.rs">read the file on GitHub</a></p>

The type is its own node. `BST<T>` is either `Empty` or a node with two boxed
subtrees, so `Box<BST<T>>` is the link type and there is no separate wrapper struct.
The `Default` derive with `#[default]` on `Empty` gives `BST::default()` as an empty
tree.

`match val.cmp(value)` produces one arm per comparison result. Using `cmp` rather than
a pair of comparisons decides the ordering once per node, and the `Ordering::Equal` arm
is explicit at every call site.

`remove` handles the two-children case by moving the smallest value out of the right
subtree into the node being deleted. `right.remove_min()` returns that value, and the
`unwrap` is safe because the branch is reached only when the right subtree is
non-empty. Values move; links stay.

`std::mem::take(right)` replaces the right subtree with `Empty` and returns the old
one. `*self = *std::mem::take(right)` then moves the subtree into the node, which
detaches it from its old position in one assignment.

`range_helper` prunes: a subtree entirely below `low` is searched on its right only,
and one entirely above `high` on its left only. The lifetime parameter `'a` ties the
references in `acc` to the tree that `self` borrows, which is what allows the returned
vector to outlive the call.

## Intuition

```text
bst_clean output, with the tree built by main:

insert 10, 5, 15, 3, 7, 12, 18

                10
              /    \
             5      15
            / \    /  \
           3   7  12   18

in order      : 3 5 7 10 12 15 18
range (4, 16) : 5 7 10 12 15

remove(&5)   -> true    5 has one child, so 7 moves up
remove(&10)  -> true    10 has two children, so 12 moves up
remove(&99)  -> false   the descent ends at Empty
```

## Time and Space Complexity

| Operation | Time | Space |
|---|---|---|
| `insert` | `O(h)` | `O(h)` stack frames |
| `contains` | `O(h)` | `O(h)` stack frames |
| `remove` | `O(h)` | `O(h)` stack frames, plus one descent to the successor |
| `range` | `O(h + k)` | `O(k)` for the output, `O(h)` stack frames |

`h` is the height. The tree does not balance, so `h` is `O(log n)` only when the input
arrives in an order that produces a balanced shape, and `O(n)` when it arrives sorted.

## Limitations

**The file has no tests.** `src/bin/bst_clean.rs` contains no `#[cfg(test)]` module, and
`main` prints values without asserting anything, so a break in the ordering invariant
appears as terminal output rather than as a failing test. The behaviour to pin down is
the ordering invariant and the three removal shapes; a test that inserts a known
sequence, removes a leaf, a one-child node and a two-child node, and asserts the
in-order traversal after each step covers all of it.

**The tree does not balance.** Inserting 1 to 1000 in ascending order produces a chain
of height 1000, and every operation becomes linear. A production ordered collection
uses a red-black tree or a B-tree; the standard library's `BTreeMap` is the one to
reach for.

**Removal by successor does not balance either.** Repeated deletions under this rule
can leave a tree taller than the input would suggest.

**`remove_min` contains an `unreachable!()` arm.** The branch is genuinely unreachable:
the guard `left.is_empty()` and the pattern `Self::Node` together guarantee that the
taken node is a node. The arm exists because the compiler cannot see that, and
`unreachable!()` records the guarantee, but it is a panic path in a function whose
caller does not expect one.

**`remove` panics if the invariant is broken.** The two-child branch calls
`right.remove_min().unwrap()`, and `remove_min` returns `None` only for an empty
subtree. The `unwrap` cannot fail while the tree is ordered; it is a second panic path.

**The value type needs `Ord`.** A caller with a type that is only `PartialOrd`, such as
a floating-point number, cannot use the tree at all, because `insert` matches on
`Ordering` and `f64` does not implement `Ord`.

## Summary

- The ordering invariant is the whole structure: every value left of a node is smaller
  and every value right of it is larger, so one comparison discards a subtree.
- Removal has three shapes, and only the two-child case needs a second descent: the
  smallest value of the right subtree is the next value in order, so putting it in
  place keeps the invariant on both sides.
- Every bound is stated in the height rather than the count, because nothing here
  balances. Sorted input produces a chain, and the height becomes the count.
- An in-order traversal reads the values in ascending order, which is the test that the
  invariant still holds after a sequence of removals.

## References

- Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, and Clifford Stein,
  *Introduction to Algorithms*, 4th edition, MIT Press, 2022, Chapter 12, "Binary
  Search Trees".
- Standard library, [`std::cmp::Ordering`](https://doc.rust-lang.org/std/cmp/enum.Ordering.html).
- Standard library, [`std::mem::take`](https://doc.rust-lang.org/std/mem/fn.take.html).
- Standard library, [`BTreeMap`](https://doc.rust-lang.org/std/collections/struct.BTreeMap.html).
