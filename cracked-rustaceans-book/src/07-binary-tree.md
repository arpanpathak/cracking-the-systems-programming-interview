# 7. Binary Tree {#binary-tree}

*Source file: [`src/problems/binary_tree.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/binary_tree.rs). Test it with
`cargo test binary_tree`.*

## Problem Statement

Represent a binary tree of integers, compute its depth, mirror it in place, and
produce its three depth-first traversals.

## Designing a Solution

The type is an algebraic data type with two variants:

```text
Tree = Empty
     | Node { value: i32, left: Box<Tree>, right: Box<Tree> }
```

Two properties follow from this representation rather than from nullable pointers.

**A node always has both children.** There is no state in which the left child is
absent and the right one is present, because the `Node` variant has no optional
fields. Every function that matches on `Tree::Node` binds `left` and `right` without
testing them.

**The recursion is in the type.** A `Node` owns its children, and each child is boxed,
so the size of a `Tree` value does not depend on how many nodes exist:

```text
stack                              heap
+---------------------+
| Tree::Node          |            +---------------------------+
|   value: 3          |            | Tree::Node                |
|   left  ------------|-----+      |   value: 9                |
|   right ------------|--+         |   left  -> Tree::Empty    |
+---------------------+  |         |   right -> Tree::Empty    |
                         |         +---------------------------+
                         |         +---------------------------+
                         +-------->| Tree::Node                |
                                   |   value: 20               |
                                   |   left  -> Node(15)       |
                                   |   right -> Node(7)        |
                                   +---------------------------+
```

Each arrow is one eight-byte ownership pointer. The `Empty` variant is a discriminant
with no payload, so it occupies no heap space.

## Implementation

<p class="listing"><span class="listing-label">Listing 7.1</span> The complete module, with its tests. <code>src/problems/binary_tree.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/binary_tree.rs">read the file on GitHub</a></p>

`max_depth` uses `..` in the pattern to ignore `value`, and computes
`1 + left.max_depth().max(right.max_depth())` without a binding for the child depths.
`Ord::max` on two `usize` values is a single instruction.

`invert` swaps the two children after recursing into both. `std::mem::swap(left, right)`
exchanges the two `Box` values, which swaps two pointers per node and moves no subtree.
Swapping before recursing would also be correct; the two subtrees are independent.

The three collection helpers take `&mut Vec<i32>`. Returning a new vector from each
recursive call would copy the whole output at every level of the tree, which turns a
linear traversal into a quadratic one.

The test helpers `leaf` and `node` exist because building a tree means writing
`Box::new` at every level, and the constructors keep the shape of the sample tree
readable. They are in the test module, so they are not part of the library's API.

## Intuition

```text
sample tree
         3
        / \
       9   20
          /  \
         15   7

preorder   value, left, right    3  9  20  15  7
inorder    left, value, right    9  3  15  20  7
postorder  left, right, value    9  15  7  20  3

max_depth  1 + max(depth of 9, depth of the 20 subtree)
           depth of 9  = 1
           depth of 20 = 1 + max(1, 1) = 2
           result      = 1 + max(1, 2) = 3

invert     left and right exchanged at every node
         3
        / \
       20  9
      /  \
     7   15
```

## Time and Space Complexity

| Operation | Time | Space |
|---|---|---|
| `max_depth` | `O(n)` | `O(h)` stack frames |
| `invert` | `O(n)` | `O(h)` stack frames, no allocation |
| each traversal | `O(n)` | `O(n)` for the output, `O(h)` stack frames |

`h` is the height of the tree: `O(log n)` when the tree is balanced and `O(n)` when it
is a chain.

## Limitations

**A deep tree exhausts the stack.** All five methods recurse, so each uses one stack
frame per level. A left-leaning tree of a few hundred thousand nodes overflowing the
default thread stack aborts the process, because a stack overflow is not a panic that
unwinds. The traversals cannot be reformulated iteratively without an explicit work
list, and `#[derive(Clone)]` has the same problem: the derived `clone` recurses as
well.

**The derived destructor recurses too.** Dropping a deep tree follows the boxes, one
frame per level, for the same reason. Freeing the memory is therefore as unsafe for a
deep tree as cloning it.

**The value type is fixed at `i32`.** Every method works for any type, and making the
declaration generic is one change to the `enum` and one to each signature, but the file
as written is not generic.

**`Tree` has no `PartialOrd`, no iteration, and no `len`.** A caller that needs the node
count writes a recursive helper or a loop with a work list.

**The test for `invert` inspects two values and not the shape.** It checks that the
roots of the two subtrees were exchanged, which catches an `invert` that does nothing
and not one that swaps the children of the root only. Asserting `tree.preorder()`
against the mirrored sequence would test the whole tree in one line.

## Summary

- The tree is an algebraic data type with an `Empty` variant and a `Node` variant that
  owns both children, so a half-present node is not representable and no function tests
  for one.
- Boxing the children puts the recursion in the type: a `Tree` value has a fixed size
  however many nodes exist.
- Every operation visits each node once, `O(n)`, and the stack cost is the height, so
  the shape of the tree, not its size, decides how much stack is needed.
- The derived destructor recurses as well, which is why a degenerate tree can exhaust
  the stack while being dropped rather than while being read. Chapter 38 measures that
  case and replaces the destructor.

## References

- The Rust Book, [Defining an enum](https://doc.rust-lang.org/book/ch06-01-defining-an-enum.html).
- The Rust Book, [Enabling recursive types with boxes](https://doc.rust-lang.org/book/ch15-01-box.html#enabling-recursive-types-with-boxes).
- Standard library, [`std::mem::swap`](https://doc.rust-lang.org/std/mem/fn.swap.html).
