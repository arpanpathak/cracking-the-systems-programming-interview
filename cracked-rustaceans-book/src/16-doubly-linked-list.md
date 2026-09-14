# 16. Doubly Linked List {#doubly-linked-list}

*Source file: [`src/bin/ll.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/ll.rs). Run it with `cargo run --bin ll`.*

## Problem Statement

Build a list with constant time insertion and removal at both ends. A singly
linked list cannot remove from the back in constant time, because reaching the
penultimate node requires a walk. Something has to point backwards, and that
something cannot own what it points at.

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

If both directions owned their target, the reference count of a two-node list
would never reach zero and the nodes would leak: each node would be kept alive by
the other. The resolution is to let the forward links own and the backward links
observe:

| Link | Type | Keeps the node alive | Fails how |
|---|---|---|---|
| `next` | `Rc<RefCell<Node<T>>>` | yes | the list outlives the value |
| `prev` | `Weak<RefCell<Node<T>>>` | no | `upgrade()` returns `None` |

A `Weak` pointer observes a value without keeping it alive. When the last strong
reference goes away, the node is freed and every weak pointer to it starts
returning `None` from `upgrade`. That is the mechanism that makes the structure
agree with the ownership rules instead of working around them.

The `RefCell` is the second half of the design. `Rc` alone gives shared ownership
but not mutation; `RefCell` adds mutation with the borrow checked at run time
rather than at compile time.

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

```rust
// ============================================================================
// Type aliases for clarity.
// ============================================================================
use std::cell::{Ref, RefCell}; // Ref is needed for peek return types
use std::rc::{Rc, Weak};

type NodeRef<T> = Rc<RefCell<Node<T>>>;
type WeakNodeRef<T> = Weak<RefCell<Node<T>>>;
type OptNodeRef<T> = Option<NodeRef<T>>;
type OptWeakNodeRef<T> = Option<WeakNodeRef<T>>;

// ============================================================================
// Node and LinkedList definitions.
// ============================================================================
struct Node<T> {
    data: T,
    next: OptNodeRef<T>,
    prev: OptWeakNodeRef<T>,
}

pub struct LinkedList<T> {
    head: OptNodeRef<T>,
    tail: OptNodeRef<T>,
    len: usize,
}

impl<T> LinkedList<T> {
    /// Creates an empty list.
    pub fn new() -> Self {
        LinkedList {
            head: None,
            tail: None,
            len: 0,
        }
    }

    pub fn len(&self) -> usize {
        self.len
    }
    pub fn is_empty(&self) -> bool {
        self.len == 0
    }

    // --------------------------------------------------------------------
    // push_front
    // --------------------------------------------------------------------
    pub fn push_front(&mut self, data: T) {
        let new_node = Rc::new(RefCell::new(Node {
            data,
            next: None,
            prev: None,
        }));

        // take() moves the old head out of the Option, leaving None.
        match self.head.take() {
            Some(old_head) => {
                // Link old head back to new node (weakly).
                old_head.borrow_mut().prev = Some(Rc::downgrade(&new_node));
                // Link new node forward to old head.
                new_node.borrow_mut().next = Some(old_head);
            }
            None => {
                // List was empty: new node is also the tail.
                self.tail = Some(new_node.clone());
            }
        }
        self.head = Some(new_node);
        self.len += 1;
    }

    // --------------------------------------------------------------------
    // push_back
    // --------------------------------------------------------------------
    pub fn push_back(&mut self, data: T) {
        let new_node = Rc::new(RefCell::new(Node {
            data,
            next: None,
            // self.tail.as_ref() gives Option<&NodeRef<T>>,
            // map(Rc::downgrade) turns it into Option<WeakNodeRef<T>>.
            prev: self.tail.as_ref().map(Rc::downgrade),
        }));

        match self.tail.take() {
            Some(old_tail) => {
                old_tail.borrow_mut().next = Some(new_node.clone());
            }
            None => {
                self.head = Some(new_node.clone());
            }
        }
        self.tail = Some(new_node);
        self.len += 1;
    }

    // --------------------------------------------------------------------
    // pop_front
    // --------------------------------------------------------------------
    pub fn pop_front(&mut self) -> Option<T> {
        self.head.take().and_then(|old_head| {
            // Take ownership of the next node (if any).
            let next = old_head.borrow_mut().next.take();

            match next {
                Some(next_node) => {
                    // Disconnect the new head's prev pointer.
                    next_node.borrow_mut().prev = None;
                    self.head = Some(next_node);
                }
                None => {
                    self.tail = None; // list becomes empty
                }
            }

            self.len -= 1;

            // Safely extract the data. At this point, old_head is the only
            // strong reference (because we removed it from the list and the
            // new head's prev doesn't point to it).
            let node = Rc::try_unwrap(old_head).ok().unwrap().into_inner();
            Some(node.data)
        })
    }

    // --------------------------------------------------------------------
    // pop_back
    // --------------------------------------------------------------------
    pub fn pop_back(&mut self) -> Option<T> {
        self.tail.take().and_then(|old_tail| {
            // Get the previous node (upgrade the weak reference).
            let prev = old_tail.borrow_mut().prev.take().and_then(|w| w.upgrade());

            match prev {
                Some(prev_node) => {
                    prev_node.borrow_mut().next = None;
                    self.tail = Some(prev_node);
                }
                None => {
                    self.head = None; // list becomes empty
                }
            }

            self.len -= 1;

            let node = Rc::try_unwrap(old_tail).ok().unwrap().into_inner();
            Some(node.data)
        })
    }

    // --------------------------------------------------------------------
    // peek_front: returns a guarded reference to the front data.
    // The returned Ref<'_, T> holds the borrow of the RefCell until it goes
    // out of scope, ensuring the reference stays valid.
    // --------------------------------------------------------------------
    pub fn peek_front(&self) -> Option<Ref<'_, T>> {
        // self.head.as_ref() -> Option<&NodeRef<T>>
        self.head.as_ref().map(|node| {
            // node.borrow() returns Ref<'_, Node<T>>.
            // Ref::map projects that to a Ref<'_, T> pointing to the data field.
            Ref::map(node.borrow(), |n| &n.data)
        })
    }

    // --------------------------------------------------------------------
    // peek_back: similar to peek_front.
    // --------------------------------------------------------------------
    pub fn peek_back(&self) -> Option<Ref<'_, T>> {
        self.tail
            .as_ref()
            .map(|node| Ref::map(node.borrow(), |n| &n.data))
    }
}

// ============================================================================
// Demonstration with main().
// ============================================================================
fn main() {
    let mut list = LinkedList::new();

    list.push_front(10);
    list.push_front(20);
    list.push_back(30);
    list.push_back(40);

    println!("Length: {}", list.len());

    // Peek returns a Ref; we can dereference it with *.
    if let Some(front) = list.peek_front() {
        println!("Front: {}", *front);
    }
    if let Some(back) = list.peek_back() {
        println!("Back: {}", *back);
    }

    println!("Pop front: {:?}", list.pop_front()); // 20
    println!("Pop back:  {:?}", list.pop_back()); // 40

    // Drain the list.
    while let Some(val) = list.pop_front() {
        println!("Popped: {}", val);
    }
    println!("Empty? {}", list.is_empty());
}

// ============================================================================
// Tests (cargo test --bin ll)
// ============================================================================
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn new_list_is_empty() {
        let list: LinkedList<i32> = LinkedList::new();
        assert!(list.is_empty());
        assert_eq!(list.len(), 0);
        assert!(list.peek_front().is_none());
        assert!(list.peek_back().is_none());
    }

    #[test]
    fn push_front_back_and_len() {
        let mut list = LinkedList::new();
        list.push_back(1);
        list.push_back(2);
        list.push_front(0);

        assert_eq!(list.len(), 3);
        assert_eq!(*list.peek_front().unwrap(), 0);
        assert_eq!(*list.peek_back().unwrap(), 2);
    }

    #[test]
    fn pop_front_and_back_work_in_order() {
        let mut list = LinkedList::new();
        list.push_back(10);
        list.push_back(20);
        list.push_back(30);

        assert_eq!(list.pop_front(), Some(10));
        assert_eq!(list.pop_back(), Some(30));
        assert_eq!(list.pop_front(), Some(20));
        assert_eq!(list.pop_front(), None);
        assert_eq!(list.pop_back(), None);
        assert!(list.is_empty());
    }

    #[test]
    fn popping_last_item_empties_the_list() {
        let mut list = LinkedList::new();
        list.push_back(42);
        assert_eq!(list.peek_front().map(|x| *x), Some(42));
        assert_eq!(list.pop_back(), Some(42));
        assert!(list.is_empty());
    }

    #[test]
    fn alternating_push_pop_keeps_invariants() {
        let mut list = LinkedList::new();
        for i in 0..100 {
            list.push_back(i);
            list.push_front(-i);
        }
        assert_eq!(list.len(), 200);
        for i in (0..100).rev() {
            assert_eq!(list.pop_front(), Some(-i));
            assert_eq!(list.pop_back(), Some(i));
        }
        assert!(list.is_empty());
    }
}

// ============================================================================
// Explanation of key methods used:
//
// - Rc::new / RefCell::new        : create a reference-counted, mutable cell.
// - borrow() / borrow_mut()       : borrow the RefCell's contents (immutably/mutably).
// - Rc::downgrade()               : turn an Rc into a Weak (no ownership).
// - Weak::upgrade()               : attempt to get an Rc from a Weak (returns Option).
// - Option::take()                : take the value out of an Option, leaving None.
// - Option::as_ref()              : convert Option<T> to Option<&T> without moving.
// - Option::map()                 : apply a function to the inner value if Some.
// - Option::and_then()            : like map but returns an Option (for chaining).
// - Rc::try_unwrap()              : move the value out of the Rc if it's the only strong ref.
// - Ref::map()                    : project a Ref to a subfield, keeping the borrow alive.
// ============================================================================
```

Four details carry the implementation.

`Rc::downgrade(&new_node)` is stored in the *old* head's `prev`, not the new
node's. The new node already owns the old head through `next`, and a second strong
reference would keep the old head alive after the list forgot it.

`self.tail.as_ref().map(Rc::downgrade)` in `push_back` converts
`Option<&NodeRef<T>>` into `Option<WeakNodeRef<T>>` without a `match`. When the
list is empty the tail is `None` and the new node's `prev` is `None`.

`old_tail.borrow_mut().prev.take().and_then(|w| w.upgrade())` in `pop_back` does
three things in one expression: takes the weak pointer out of the node (leaving
`None` behind), attempts to upgrade it to a strong reference, and yields `None` if
the node has been freed. The `take` is what allows the removed node to be freed
afterwards.

`Rc::try_unwrap(old_head).ok().unwrap().into_inner()` moves the node out of the
`Rc` and the data out of the `RefCell`. It succeeds because the node has been
unlinked and no other strong reference exists. `into_inner` on a `RefCell`
consumes the cell, so it cannot fail and needs no borrow check.

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
close.** It succeeds while the invariants hold: the removed node has been unlinked
and the new end's link to it has been cleared, so the list holds the only strong
reference. Nothing in the signature says so, and a future change to `push_back`
that keeps an extra strong reference would turn the `unwrap` into a panic at run
time rather than a compile error. `.expect("...")` with the reason would document
the assumption; a `match` that recovers the node from the `Err` arm would make the
code total.

**The list is neither `Send` nor `Sync`.** `Rc` and `RefCell` are both
single-threaded, so a `LinkedList` cannot be moved to another thread or shared
between threads. The compiler rejects both, which means the limitation appears at
the call site. A concurrent list uses `Arc<Mutex<Node<T>>>` and pays for it with
lock contention and the possibility of poison.

**`RefCell` borrows are checked at run time.** `borrow_mut()` panics if a borrow is
already active. Holding the guard that `peek_front` returns while calling
`pop_front` on the same list is a run-time panic, where the `Box`-based list of
Chapter 14 would have made it a compile error.

**Dropping a long list is recursive.** Each node holds a strong reference to the
next, so releasing the head releases the next node, which releases the next, one
stack frame per node. The `RefCell` does not change that; it only adds a borrow
flag to each node, which is two more machine words per element.

**The demonstration's comment about `pop_front` returning 20 is the only place the
expected value is written.** `main` prints values and asserts nothing, and the
tests cover the same behaviour. The two comments in `main` are documentation rather
than checks.

## Summary

- One direction of the link has to be weak. Two strong links between a pair of
  nodes would keep the pair alive after the list released it, so `prev` is a
  `Weak`.
- `RefCell` adds a borrow counter to each node, two machine words per element, and
  turns a conflicting borrow into a run-time panic where the `Box`-based list of
  Chapter 14 makes it a compile error. What it provides is mutation through shared
  ownership, which is what `pop_back` requires.
- `Rc::try_unwrap(...).ok().unwrap()` is a panic path that the type system does not
  close. It succeeds while the invariants hold, because the removed node has been
  unlinked and the list holds the only strong reference, and nothing in the
  signature states that. An `.expect` with the reason would record the assumption,
  and a `match` on the `Err` arm would make the function total.
- The list is neither `Send` nor `Sync`, because `Rc` and `RefCell` are
  single-threaded. A concurrent list would use `Arc<Mutex<Node<T>>>` and pay for it
  with lock contention and the possibility of poison.
- Dropping a long list recurses, one stack frame per node, since each node holds a
  strong reference to the next.

## References

- The Rust Book, [`Rc<T>`, the reference-counted smart pointer](https://doc.rust-lang.org/book/ch15-04-rc.html).
- The Rust Book, [`RefCell<T>` and the interior mutability pattern](https://doc.rust-lang.org/book/ch15-05-interior-mutability.html).
- Standard library, [`Rc::downgrade`](https://doc.rust-lang.org/std/rc/struct.Rc.html#method.downgrade).
- Standard library, [`Weak::upgrade`](https://doc.rust-lang.org/std/rc/struct.Weak.html#method.upgrade).
- Standard library, [`Ref::map`](https://doc.rust-lang.org/std/cell/struct.Ref.html#method.map).
