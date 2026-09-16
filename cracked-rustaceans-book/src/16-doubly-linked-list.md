# 16. Doubly Linked List {#doubly-linked-list}

*Source file: [`src/bin/ll.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/ll.rs). Run it with `cargo run --bin ll`.*

## Problem Statement

Build a list with constant time insertion and removal at both ends. A singly linked list
cannot remove from the back in constant time, because reaching the penultimate node
requires a walk. Something has to point backwards, and that something cannot own what it
points at.

## Designing a Solution

```text
  head                                    tail
   |                                        |
   v                                        v
 +------+   next (Rc, strong)   +------+   next   +------+
 | 10   | --------------------> | 20   | -------> | 30   |
 |      | <-------------------- |      | <------- |      |
 +------+   prev (Weak)         +------+   prev   +------+
```

If both directions owned their target, the reference count of a two-node list would
never reach zero and the nodes would leak: each node would be kept alive by the other.
The resolution is to let the forward links own and the backward links observe:

| Link | Type | Keeps the node alive | Fails how |
|---|---|---|---|
| `next` | `Rc<RefCell<Node<T>>>` | yes | the list outlives the value |
| `prev` | `Weak<RefCell<Node<T>>>` | no | `upgrade()` returns `None` |

A `Weak` pointer observes a value without keeping it alive. When the last strong
reference goes away, the node is freed and every weak pointer to it starts returning
`None` from `upgrade`.

The `RefCell` is the second half of the design. `Rc` alone gives shared ownership but no
mutation; `RefCell` adds mutation with the borrow checked at run time rather than at
compile time.

```text
after pop_front on the list above

(node 10 is freed: nothing strong refers to it)

              head                          tail
               |                             |
               v                             v
            +------+      next   +------+
            | 20   | ----------> | 30   |
            |      | <---------- |      |
            +------+      prev   +------+
               ^
               |
            the tail's weak pointer upgrades to this node, so pop_back
            reaches the new last node in constant time
```

## Implementation

<p class="listing"><span class="listing-label">Listing 16.1</span> The complete program, with its tests. <code>src/bin/ll.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/ll.rs">read the file on GitHub</a></p>

Four details carry the implementation.

`Rc::downgrade(&new_node)` is stored in the *old* head's `prev`, not the new node's. The
new node already owns the old head through `next`, and a second strong reference would
keep the old head alive after the list forgot it.

`self.tail.as_ref().map(Rc::downgrade)` in `push_back` converts `Option<&NodeRef<T>>`
into `Option<WeakNodeRef<T>>` without a `match`. When the list is empty the tail is
`None` and the new node's `prev` is `None`.

`old_tail.borrow_mut().prev.take().and_then(|w| w.upgrade())` in `pop_back` does three
things in one expression: takes the weak pointer out of the node, leaving `None` behind;
attempts to upgrade it to a strong reference; and yields `None` if the node has been
freed. The `take` is what allows the removed node to be freed afterwards.

`Rc::try_unwrap(old_head).ok().unwrap().into_inner()` moves the node out of the `Rc` and
the data out of the `RefCell`. It succeeds because the node has been unlinked and no
other strong reference exists. `into_inner` on a `RefCell` consumes the cell, so it
cannot fail and needs no borrow check.

## Intuition

```text
call                  head   tail   len   effect
new()                 -      -      0
push_front(10)        10     10     1     the first node becomes both ends
push_front(20)        20     10     2     10.prev is a weak pointer to 20
push_back(30)         20     30     3     10.next is 30; 30.prev is weak to 10
push_back(40)         20     40     4     30.next is 40; 40.prev is weak to 30

peek_front()          the guard dereferences to 20
peek_back()           the guard dereferences to 40

pop_front()           20     40     3     returns Some(20)
                                          10's predecessor link is cleared, so
                                          nothing strong refers to 20 and it is
                                          freed by the unwrap
pop_back()            10     30     2     returns Some(40)
                                          30.next is cleared
```

## Time and Space Complexity

| Operation | Time | Space |
|---|---|---|
| `push_front`, `push_back` | `O(1)` | one allocation, plus one reference-count update |
| `pop_front`, `pop_back` | `O(1)` | frees one allocation |
| `peek_front`, `peek_back` | `O(1)` | none |
| `len`, `is_empty` | `O(1)` | the length is stored |

## Limitations

**`Rc::try_unwrap(...).ok().unwrap()` is a panic path that the type system does not
close.** It succeeds while the invariants hold: the removed node has been unlinked and
the new end's link to it has been cleared, so the list holds the only strong reference.
Nothing in the signature says so, and a future change to `push_back` that keeps an extra
strong reference would turn the `unwrap` into a run-time panic rather than a compile
error. An `.expect("...")` with the reason would document the assumption; a `match` that
recovers the node from the `Err` arm would make the code total.

**The list is neither `Send` nor `Sync`.** `Rc` and `RefCell` are both single-threaded,
so a `LinkedList` cannot be moved to another thread or shared between threads. The
compiler rejects both, which puts the limitation at the call site. A concurrent list
uses `Arc<Mutex<Node<T>>>` and pays for it with lock contention and the possibility of
poison.

**`RefCell` borrows are checked at run time.** `borrow_mut()` panics if a borrow is
already active. Holding the guard that `peek_front` returns while calling `pop_front` on
the same list is a run-time panic, where the `Box`-based list of Chapter 14 would have
made it a compile error.

**Dropping a long list is recursive.** Each node holds a strong reference to the next, so
releasing the head releases the next node, which releases the next, one stack frame per
node. The `RefCell` does not change that; it adds a borrow flag to each node, two more
machine words per element.

**The demonstration's comment about `pop_front` returning 20 is the only place the
expected value is written.** `main` prints values and asserts nothing, and the tests
cover the same behaviour.

## Summary

- Forward links own and backward links observe: `next` is an `Rc` and `prev` a `Weak`,
  so a two-node list is not kept alive by itself.
- `RefCell` moves the borrow check to run time, which is what allows two links to point
  at a node that is being modified. The price is a panic rather than a compile error
  when two borrows overlap.
- Every operation at either end is constant time, and the length is stored rather than
  counted.
- `Rc` and `RefCell` are single-threaded types, so the list is neither `Send` nor
  `Sync`. Chapter 18 answers the same problem with indices into a vector, which is
  cheaper and carries no reference counts at all.

## References

- The Rust Book, [`Rc<T>`, the reference-counted smart pointer](https://doc.rust-lang.org/book/ch15-04-rc.html).
- The Rust Book, [`RefCell<T>` and the interior mutability pattern](https://doc.rust-lang.org/book/ch15-05-interior-mutability.html).
- Standard library, [`Rc::downgrade`](https://doc.rust-lang.org/std/rc/struct.Rc.html#method.downgrade).
- Standard library, [`Weak::upgrade`](https://doc.rust-lang.org/std/rc/struct.Weak.html#method.upgrade).
- Standard library, [`Ref::map`](https://doc.rust-lang.org/std/cell/struct.Ref.html#method.map).
