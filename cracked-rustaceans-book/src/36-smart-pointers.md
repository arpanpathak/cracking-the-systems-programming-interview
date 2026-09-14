# 36. Smart Pointers and Interior Mutability {#smart-pointers}

*Source file: [`src/problems/smart_pointers.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/smart_pointers.rs). Test it with `cargo test smart_pointers`.*

## Problem Statement

Five situations recur in systems code:

1. A type contains itself, such as an expression tree.
2. Two parts of one thread need to change the same value.
3. A child needs to reach its parent without keeping the parent alive.
4. Several threads need to change the same value.
5. A function usually returns its input unchanged and occasionally needs a modified copy.

Each has a type designed for it, and choosing the wrong one produces either a compile
error or a run-time failure. The module documentation summarises the choices in a
table, reproduced here.

**What each pointer type provides**

| Type | Ownership | Mutation | Across threads |
|---|---|---|---|
| `Box<T>` | single | through `&mut` | if `T: Send` |
| `Rc<T>` | shared, non-atomic count | no | no |
| `Arc<T>` | shared, atomic count | no | if `T: Send + Sync` |
| `RefCell<T>` | single | checked at run time | no |
| `Mutex<T>` | single | blocking lock | yes |
| `Weak<T>` | non-owning | no | as `Rc` or `Arc` |
| `Cow<'a, T>` | borrowed or owned | no | as the borrow |

## Designing a Solution

The types combine along two axes. The first axis is ownership: `Box` has one owner,
`Rc` and `Arc` have many, and `Weak` has none. The second is mutation through a shared
reference, which Rust forbids by default and permits only through a cell: `RefCell`
checks borrows at run time on one thread, and `Mutex` enforces exclusion with a lock
across threads.

The common pairings follow from those axes:

- `Rc<RefCell<T>>` for shared, mutable state inside one thread, such as the doubly
  linked list in chapter 16.
- `Arc<Mutex<T>>` for shared, mutable state between threads, such as the counters and
  queues in chapters 21, 22, and 30.
- `Rc` forward and `Weak` backward whenever two objects refer to each other, so that
  the reference counts can reach zero.

`Cow` is on a different axis. It is not about sharing; it lets a function defer the
decision to allocate until it knows whether an allocation is needed.

## Implementation

The module contains five short examples and a test for each. The file begins with the
table from the Problem Statement in its documentation comment and the imports, shown
below.

```rust
//! Smart pointers and interior mutability.
//!
//! Each pointer type answers a different ownership question, and picking the
//! wrong one shows up as either a compile error or a runtime bug.
//!
//! | Type | Ownership | Mutation | Across threads |
//! |---|---|---|---|
//! | `Box<T>` | single | through `&mut` | if `T: Send` |
//! | `Rc<T>` | shared, non-atomic count | no | no |
//! | `Arc<T>` | shared, atomic count | no | if `T: Send + Sync` |
//! | `RefCell<T>` | single | runtime checked | no |
//! | `Mutex<T>` | single | blocking lock | yes |
//! | `Weak<T>` | non-owning | no | as `Arc` |
//! | `Cow<'a, T>` | borrow or own | no | as the borrow |
//!
//! Two rules cover most decisions. `Rc`/`RefCell` is for graphs and caches inside
//! one thread; `Arc`/`Mutex` is for state shared between threads. `Weak` exists to
//! break reference cycles, because two strong references in a cycle never reach a
//! count of zero and the memory is never freed.

use std::borrow::Cow;
use std::cell::RefCell;
use std::rc::{Rc, Weak};
use std::sync::{Arc, Mutex};
use std::thread;
```

### `Box` for a recursive type

A type that contains itself by value would have infinite size. `Box<Expr>` is one
pointer wide whatever the expression contains, so `Expr` has a finite size.

```rust
/// A recursive type needs indirection, because `Expr` cannot contain itself by
/// value. `Box` provides the fixed-size indirection.
#[derive(Debug, PartialEq, Eq)]
pub enum Expr {
    Lit(i64),
    Add(Box<Expr>, Box<Expr>),
}

/// Evaluate an expression tree.
pub fn eval(expr: &Expr) -> i64 {
    match expr {
        Expr::Lit(value) => *value,
        Expr::Add(left, right) => eval(left) + eval(right),
    }
}
```

`eval(left)` receives a `&Box<Expr>`, and deref coercion turns it into the `&Expr` the
function expects, so the recursive calls need no explicit dereference.

### `Rc<RefCell<T>>` inside one thread

```rust
/// Shared mutation inside one thread, with `Rc` for aliasing and `RefCell` for
/// the runtime borrow check.
pub fn shared_counter_with_rc_refcell() -> i32 {
    let counter = Rc::new(RefCell::new(0));
    let alias = Rc::clone(&counter);

    *alias.borrow_mut() += 1;
    *counter.borrow_mut() += 10;

    *counter.borrow()
}
```

`Rc::clone(&counter)` increments a reference count and returns a second handle to the
same allocation; it does not copy the integer. `borrow_mut` returns a `RefMut` guard
that dereferences to `&mut i32`. Each guard is a temporary that ends with its
statement, so the two mutable borrows never overlap and neither panics. The function
returns 11.

If the two guards were alive at the same time, for example
`let a = alias.borrow_mut(); let b = counter.borrow_mut();`, the second call would
panic with `already borrowed`. The compiler cannot see the conflict because both
handles are shared references; `RefCell` checks it at run time instead.

### `Weak` for a back-reference

```rust
/// A node whose parent link is weak, so a child does not keep its parent alive.
pub struct TreeNode {
    pub value: i32,
    parent: RefCell<Weak<TreeNode>>,
}

impl TreeNode {
    /// A node with no parent.
    pub fn root(value: i32) -> Rc<Self> {
        Rc::new(Self {
            value,
            parent: RefCell::new(Weak::new()),
        })
    }

    /// A node that points back weakly at `parent`.
    pub fn child_of(parent: &Rc<Self>, value: i32) -> Rc<Self> {
        Rc::new(Self {
            value,
            parent: RefCell::new(Rc::downgrade(parent)),
        })
    }

    /// The parent's value, or `None` once the parent has been dropped.
    pub fn parent_value(&self) -> Option<i32> {
        self.parent.borrow().upgrade().map(|parent| parent.value)
    }
}
```

`Rc::downgrade(parent)` creates a `Weak` that does not contribute to the strong count.
When the last `Rc` to the parent is dropped, the parent is freed even though the child
still holds the `Weak`. `upgrade` then returns `None`, and `parent_value` reports
absence rather than reading freed memory.

The `parent` field is a `RefCell<Weak<TreeNode>>`. This module only reads the cell,
but the cell is what would let a parent be attached or replaced after the child is
created, through a shared `Rc<TreeNode>`.

### `Arc<Mutex<T>>` across threads

```rust
/// Shared mutation across threads, with `Arc` for ownership and `Mutex` for
/// exclusive access.
pub fn total_with_arc_mutex(threads: usize, per_thread: usize) -> usize {
    let total = Arc::new(Mutex::new(0usize));
    let mut handles = Vec::with_capacity(threads);

    for _ in 0..threads {
        let total = Arc::clone(&total);
        handles.push(thread::spawn(move || {
            for _ in 0..per_thread {
                let mut guard = total.lock().expect("mutex poisoned");
                *guard += 1;
            }
        }));
    }

    for handle in handles {
        handle.join().expect("worker panicked");
    }

    *total.lock().expect("mutex poisoned")
}
```

`Arc` is the thread-safe version of `Rc`: its reference count is updated with atomic
operations, so handles can be cloned and dropped on different threads. `Mutex`
provides the exclusive access that `RefCell` provides on one thread, and it blocks
rather than panics when the value is already borrowed.

The lock is taken once per increment. That is correct and slow: each increment pays
for a lock acquisition. Chapter 43 replaces the mutex with an `AtomicUsize` for this
exact workload.

### `Cow` to allocate only when necessary

```rust
/// Borrow when no change is needed, allocate only when there is one.
///
/// `Cow` is the idiomatic return type for a function that usually passes its
/// input through unchanged.
pub fn normalize(input: &str, uppercase: bool) -> Cow<'_, str> {
    if uppercase && input.bytes().any(|byte| byte.is_ascii_lowercase()) {
        Cow::Owned(input.to_uppercase())
    } else {
        Cow::Borrowed(input)
    }
}
```

The function scans the bytes once. If uppercasing is not requested, or the input has
no lowercase ASCII letter, it returns `Cow::Borrowed(input)` and allocates nothing.
Otherwise it allocates the uppercased `String`. A caller treats both cases the same way,
because `Cow<str>` dereferences to `&str`, and a caller that needs ownership calls
`into_owned`.

The lifetime in `Cow<'_, str>` is elided to the lifetime of `input`, which is what ties
a borrowed result to the argument it came from.

The last listing shows the tests, one per example.

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn boxed_expression_evaluates() {
        let expr = Expr::Add(Box::new(Expr::Lit(1)), Box::new(Expr::Lit(2)));
        assert_eq!(eval(&expr), 3);
    }

    #[test]
    fn rc_refcell_shares_mutation_within_a_thread() {
        assert_eq!(shared_counter_with_rc_refcell(), 11);
    }

    #[test]
    fn weak_parent_link_does_not_keep_the_parent_alive() {
        let root = TreeNode::root(1);
        let child = TreeNode::child_of(&root, 2);

        assert_eq!(child.parent_value(), Some(1));
        drop(root);
        assert_eq!(child.parent_value(), None);
    }

    #[test]
    fn arc_mutex_sums_concurrent_updates() {
        assert_eq!(total_with_arc_mutex(8, 250), 2_000);
    }

    #[test]
    fn cow_borrows_and_owns_as_needed() {
        assert!(matches!(normalize("A100", true), Cow::Borrowed(_)));
        assert!(matches!(normalize("a100", true), Cow::Owned(_)));
        assert_eq!(normalize("a100", true), "A100");
        assert_eq!(normalize("a100", false), "a100");
    }
}
```

## Intuition

The weak-parent test is the one that shows a pointer type changing state over time.
The table below records the reference counts at each step.

**Counts during `weak_parent_link_does_not_keep_the_parent_alive`**

| step | strong count of `root` | weak count of `root` | `child.parent_value()` |
|---|---|---|---|
| `let root = TreeNode::root(1)` | 1 | 0 | not called |
| `let child = TreeNode::child_of(&root, 2)` | 1 | 1 | `Some(1)` |
| `drop(root)` | 0, the node is dropped | 1, the allocation remains until the `Weak` is gone | `None` |

The allocation that held the parent's control block is released when the child, and
with it the last `Weak`, is dropped at the end of the test. The `TreeNode` value
itself was dropped at `drop(root)`.

The `Cow` test produces the following results:

```text
normalize("A100", true)   no lowercase byte      Cow::Borrowed("A100")
normalize("a100", true)   'a' is lowercase       Cow::Owned("A100")
normalize("a100", false)  uppercase not wanted   Cow::Borrowed("a100")
```

## Time and Space Complexity

| Operation | Time | Space |
|---|---|---|
| `Box::new` | one allocation | the value plus nothing |
| `Rc::clone`, `Rc` drop | one non-atomic increment or decrement | two counts per allocation |
| `Arc::clone`, `Arc` drop | one atomic increment or decrement | two counts per allocation |
| `RefCell::borrow_mut` | one flag check and write | one `isize` flag per cell |
| `Mutex::lock` | uncontended: one atomic operation; contended: a system call | a few bytes of lock state |
| `Weak::upgrade` | one count check and increment | none |
| `normalize` | `O(n)` scan, plus `O(n)` copy when owned | zero or one allocation |

## Limitations

**`Rc<RefCell<T>>` moves errors from compile time to run time.** A borrow conflict in
the `Rc<RefCell<T>>` example is a panic, not a compile error. Code that can be written with plain
ownership and `&mut` should be, and the arena in chapter 18 shows a design that avoids
`RefCell` altogether.

**`Arc<Mutex<T>>` serializes the work it protects.** In the `Arc<Mutex<T>>` example, eight threads
spend most of their time waiting for one lock. The type makes sharing safe; it does
not make it fast.

**`Weak` does not prevent cycles on its own.** It is a tool for breaking them, and the
program has to choose which link is weak. Two `Rc` links in a cycle leak both values,
and no warning is issued.

**`normalize` looks only for ASCII lowercase letters.** An input such as `"straße"` has
lowercase letters, and so is converted, but an input consisting only of non-ASCII
lowercase letters such as `"é"` is returned borrowed and unchanged even though
`to_uppercase` would change it. The check and the conversion disagree on what
"lowercase" means.

## Summary

- `Box` gives a recursive type a finite size and has a single owner.
- `Rc` shares ownership within a thread, and `Arc` shares it across threads with
  atomic counts.
- `RefCell` and `Mutex` allow mutation through a shared handle; `RefCell` panics on a
  conflicting borrow, and `Mutex` blocks.
- `Weak` observes without owning, which lets back-references coexist with reference
  counting; `upgrade` returns `None` after the target is dropped.
- `Cow` returns a borrow when no change is needed and allocates only when one is.

## References

- The Rust Book, [Smart pointers](https://doc.rust-lang.org/book/ch15-00-smart-pointers.html).
- The Rust Book, [Reference cycles can leak memory](https://doc.rust-lang.org/book/ch15-06-reference-cycles.html).
- Standard library, [`std::rc`](https://doc.rust-lang.org/std/rc/index.html), [`std::cell`](https://doc.rust-lang.org/std/cell/index.html), and [`std::sync::Arc`](https://doc.rust-lang.org/std/sync/struct.Arc.html).
- Standard library, [`std::borrow::Cow`](https://doc.rust-lang.org/std/borrow/enum.Cow.html).
