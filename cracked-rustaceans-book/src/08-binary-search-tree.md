# 8. Binary Search Tree {#binary-search-tree}

*Source file: [`src/bin/bst_clean.rs`](../../rust-interview-lab/src/bin/bst_clean.rs). Run it with `cargo run --bin bst_clean`.*

## Problem Statement

Build an ordered tree, a binary search tree, supporting insertion, membership,
removal, and a range query. Removal is the interesting one, because a node with
two children cannot simply be unlinked: something has to take its place without
breaking the ordering.

## Designing a Solution

The ordering invariant is the whole structure:

```text
for every node:  every value in the left subtree  <  the node's value
                 every value in the right subtree >  the node's value
```

A lookup follows one path from the root, discarding a subtree at each comparison.
An in-order traversal reads the values in ascending order, which is the standard
way to test that the invariant holds.

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

```rust
use std::cmp::Ordering;

type TreeLink<T> = Box<BST<T>>;

#[derive(Debug, Clone, Default)]
pub enum BST<T> {
    #[default]
    Empty,
    Node {
        value: T,
        left: TreeLink<T>,
        right: TreeLink<T>,
    },
}

impl<T: Ord> BST<T> {
    pub fn new() -> Self {
        Self::Empty
    }

    pub fn insert(&mut self, val: T) {
        match self {
            Self::Empty => {
                *self = Self::Node {
                    value: val,
                    left: Box::new(Self::Empty),
                    right: Box::new(Self::Empty),
                };
            }
            Self::Node { value, left, right } => match val.cmp(value) {
                Ordering::Less => left.insert(val),
                Ordering::Greater => right.insert(val),
                Ordering::Equal => {}
            },
        }
    }

    pub fn contains(&self, val: &T) -> bool {
        match self {
            Self::Empty => false,
            Self::Node { value, left, right } => match val.cmp(value) {
                Ordering::Less => left.contains(val),
                Ordering::Greater => right.contains(val),
                Ordering::Equal => true,
            },
        }
    }

    pub fn remove(&mut self, val: &T) -> bool {
        match self {
            Self::Empty => false,
            Self::Node { value, left, right } => match val.cmp(value) {
                Ordering::Less => left.remove(val),
                Ordering::Greater => right.remove(val),
                Ordering::Equal => {
                    if left.is_empty() && right.is_empty() {
                        *self = Self::Empty;
                        return true;
                    }
                    if left.is_empty() {
                        *self = *std::mem::take(right);
                        return true;
                    }
                    if right.is_empty() {
                        *self = *std::mem::take(left);
                        return true;
                    }
                    let min_val = right.remove_min().unwrap();
                    *value = min_val;
                    true
                }
            },
        }
    }

    fn remove_min(&mut self) -> Option<T> {
        match self {
            Self::Empty => None,
            Self::Node { left, .. } if left.is_empty() => {
                let node = std::mem::take(self);
                if let Self::Node { value, right, .. } = node {
                    *self = *right;
                    Some(value)
                } else {
                    unreachable!()
                }
            }
            Self::Node { left, .. } => left.remove_min(),
        }
    }

    pub fn range(&self, low: &T, high: &T) -> Vec<&T> {
        let mut result = Vec::new();
        self.range_helper(low, high, &mut result);
        result
    }

    // Explicit lifetime 'a ties the references in the vector to the lifetime of &self.
    fn range_helper<'a>(&'a self, low: &T, high: &T, acc: &mut Vec<&'a T>) {
        match self {
            Self::Empty => {}
            Self::Node { value, left, right } => {
                if value < low {
                    right.range_helper(low, high, acc);
                } else if value > high {
                    left.range_helper(low, high, acc);
                } else {
                    left.range_helper(low, high, acc);
                    acc.push(value);
                    right.range_helper(low, high, acc);
                }
            }
        }
    }

    fn is_empty(&self) -> bool {
        matches!(self, Self::Empty)
    }
}

fn main() {
    let mut bst = BST::new();
    bst.insert(10);
    bst.insert(5);
    bst.insert(15);
    bst.insert(3);
    bst.insert(7);
    bst.insert(12);
    bst.insert(18);

    println!("Contains 7: {}", bst.contains(&7));
    println!("Contains 12: {}", bst.contains(&12));

    let range = bst.range(&4, &16);
    println!("Values in [4, 16]: {:?}", range);

    println!("Remove 5: {}", bst.remove(&5));
    println!("Remove 10: {}", bst.remove(&10));
    println!("Remove 99: {}", bst.remove(&99));

    println!("After removals: {:#?}", bst);
}
```

The type is its own node. `BST<T>` is either `Empty` or a node with two boxed
subtrees, so `Box<BST<T>>` is the link type and there is no separate wrapper
struct. The `Default` derive with `#[default]` on `Empty` gives `BST::default()`
as an empty tree.

`match val.cmp(value)` produces three arms for the three comparison results. Using
`cmp` rather than a pair of comparisons means the ordering is decided once per
node, and the `Ordering::Equal` arm is explicit at every call site.

`remove` handles the two-children case by moving the smallest value out of the
right subtree into the node being deleted. `right.remove_min()` returns that
value, and the `unwrap` is safe because the branch is only reached when the right
subtree is non-empty. The node structure is untouched: values move, links stay.

`std::mem::take(right)` replaces the right subtree with `Empty` and returns the
old one. `*self = *std::mem::take(right)` then moves the subtree into the node,
which detaches the whole subtree from its old position in one assignment.

`range_helper` prunes: a subtree entirely below `low` is only searched on its
right, and one entirely above `high` is only searched on its left. The lifetime
parameter is written `'a` and ties the references in `acc` to the tree that
`self` borrows, which is what allows the returned vector to outlive the call.

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

`h` is the height. The tree does not balance, so `h` is `O(log n)` only when the
input arrives in an order that produces a balanced shape, and `O(n)` when it
arrives sorted.

## Limitations

**The file has no tests.** `src/bin/bst_clean.rs` contains no `#[cfg(test)]`
module, and `main` prints values without asserting anything, so a break in the
ordering invariant shows up as output on the terminal rather than as a failing
test. `cargo test` reports no test for this file. The behaviour to pin down is the
ordering invariant and the three removal shapes; a test that inserts a known
sequence, removes a leaf, a one-child node, and a two-child node, and asserts the
in-order traversal after each step covers all of it.

**The tree does not balance.** Inserting 1 to 1000 in ascending order produces a
chain of height 1000, and every operation becomes linear. A production ordered
collection uses a red-black tree or a B-tree; the standard library's `BTreeMap`
is the one to reach for.

**Removal by successor does not balance either.** Repeated deletions under this
rule can leave a tree taller than the input would suggest, and the effect is
measurable over a long sequence of insertions and deletions.

**`remove_min` contains an `unreachable!()` arm.** The branch is genuinely
unreachable: the guard `left.is_empty()` and the pattern `Self::Node` together
guarantee that the taken node is a node. The arm exists because the compiler
cannot see that, and `unreachable!()` records that guarantee, but it is a
panic path in a function whose caller does not expect one.

**`remove` panics if the tree has a node whose left child is empty and whose right
child is not `Node`.** The two-child branch calls `right.remove_min().unwrap()`,
and `remove_min` returns `None` only for an empty subtree. The `unwrap` cannot
fail while the invariant holds; it is a second panic path.

**The value type needs `Ord`, and the range query needs `PartialOrd`.** Those are
the correct bounds. A caller with a type that is only `PartialOrd`, such as a
floating-point number, cannot use the tree at all, because `insert` matches on
`Ordering` and `f64` does not implement `Ord`.

## Summary

- Removal has three shapes. Removing a leaf and removing a node with one child are
  bookkeeping; removing a node with two children is the case the ordering
  invariant makes interesting.
- The replacement value is the next value in order, which is also the minimum of
  the right subtree. The first description states why the invariant survives the
  substitution.
- The tree does not balance. A sorted input produces a chain, so `O(h)` becomes
  `O(n)`, and `BTreeMap` is the standard library structure that keeps the
  `O(log n)` bound under any insertion order.
- The file has no tests. `main` prints values without asserting them, so a fault
  in the ordering invariant appears as output on the terminal rather than as a
  failing test.

## References

- Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, and Clifford Stein,
  *Introduction to Algorithms*, 4th edition, MIT Press, 2022, Chapter 12, "Binary
  Search Trees".
- Standard library, [`std::cmp::Ordering`](https://doc.rust-lang.org/std/cmp/enum.Ordering.html).
- Standard library, [`std::mem::take`](https://doc.rust-lang.org/std/mem/fn.take.html).
- Standard library, [`BTreeMap`](https://doc.rust-lang.org/std/collections/struct.BTreeMap.html).
