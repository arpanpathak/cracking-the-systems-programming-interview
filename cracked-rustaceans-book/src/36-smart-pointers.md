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

<p class="listing"><span class="listing-label">Listing 36.1</span> An excerpt of the module. <code>src/problems/smart_pointers.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/smart_pointers.rs">read the file on GitHub</a></p>

### `Box` for a recursive type

A type that contains itself by value would have infinite size. `Box<Expr>` is one
pointer wide whatever the expression contains, so `Expr` has a finite size.

<p class="listing"><span class="listing-label">Listing 36.2</span> <code>Box</code> for a recursive type. <code>src/problems/smart_pointers.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/smart_pointers.rs">read the file on GitHub</a></p>

`eval(left)` receives a `&Box<Expr>`, and deref coercion turns it into the `&Expr` the
function expects, so the recursive calls need no explicit dereference.

### `Rc<RefCell<T>>` inside one thread

<p class="listing"><span class="listing-label">Listing 36.3</span> <code>Rc&lt;RefCell&lt;T&gt;&gt;</code> inside one thread. <code>src/problems/smart_pointers.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/smart_pointers.rs">read the file on GitHub</a></p>

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

<p class="listing"><span class="listing-label">Listing 36.4</span> <code>Weak</code> for a back-reference. <code>src/problems/smart_pointers.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/smart_pointers.rs">read the file on GitHub</a></p>

`Rc::downgrade(parent)` creates a `Weak` that does not contribute to the strong count.
When the last `Rc` to the parent is dropped, the parent is freed even though the child
still holds the `Weak`. `upgrade` then returns `None`, and `parent_value` reports
absence rather than reading freed memory.

The `parent` field is a `RefCell<Weak<TreeNode>>`. This module only reads the cell,
but the cell is what would let a parent be attached or replaced after the child is
created, through a shared `Rc<TreeNode>`.

### `Arc<Mutex<T>>` across threads

<p class="listing"><span class="listing-label">Listing 36.5</span> <code>Arc&lt;Mutex&lt;T&gt;&gt;</code> across threads. <code>src/problems/smart_pointers.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/smart_pointers.rs">read the file on GitHub</a></p>

`Arc` is the thread-safe version of `Rc`: its reference count is updated with atomic
operations, so handles can be cloned and dropped on different threads. `Mutex`
provides the exclusive access that `RefCell` provides on one thread, and it blocks
rather than panics when the value is already borrowed.

The lock is taken once per increment. That is correct and slow: each increment pays
for a lock acquisition. Chapter 43 replaces the mutex with an `AtomicUsize` for this
exact workload.

### `Cow` to allocate only when necessary

<p class="listing"><span class="listing-label">Listing 36.6</span> <code>Cow</code> to allocate only when necessary. <code>src/problems/smart_pointers.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/smart_pointers.rs">read the file on GitHub</a></p>

The function scans the bytes once. If uppercasing is not requested, or the input has
no lowercase ASCII letter, it returns `Cow::Borrowed(input)` and allocates nothing.
Otherwise it allocates the uppercased `String`. A caller treats both cases the same way,
because `Cow<str>` dereferences to `&str`, and a caller that needs ownership calls
`into_owned`.

The lifetime in `Cow<'_, str>` is elided to the lifetime of `input`, which is what ties
a borrowed result to the argument it came from.

The last listing shows the tests, one per example.

<p class="listing"><span class="listing-label">Listing 36.7</span> <code>Cow</code> to allocate only when necessary, continued. <code>src/problems/smart_pointers.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/smart_pointers.rs">read the file on GitHub</a></p>

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
