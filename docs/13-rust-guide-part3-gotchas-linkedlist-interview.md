# 13: Rust Senior Interview Guide, Part 3: Gotchas, Full Doubly Linked List, Interview Tactics

Part 3 covers the traps that catch Rust candidates, the doubly linked list lab,
and how to behave in a phone screen.

---

## 11. Rust gotchas

### 11.1 "cannot borrow as mutable more than once"

```rust,ignore
let mut values = vec![1, 2, 3];
let first = &values[0];
values.push(4); // ERROR: cannot borrow `values` as mutable because it is also borrowed as immutable
println!("{first}");
```

Solution: the immutable borrow ends before the mutation, or an index is copied:

```rust
let mut values = vec![1, 2, 3];
let first_copy = values[0];
values.push(4);
println!("{first_copy} {values:?}");
```

Explanation: Rust forbids aliasing with mutation. Shared mutation requires
`RefCell` or `Mutex`, which move the check to run time.

### 11.2 "temporary value dropped while borrowed"

```rust,ignore
let name = String::from("A100").as_str(); // ERROR: temporary dropped
```

Solution: the owner is bound first:

```rust
let owned = String::from("A100");
let name = owned.as_str();
```

### 11.3 "moving out of borrowed content"

```rust,ignore
struct Config { name: String }
fn bad(config: &Config) -> String {
    config.name // cannot move out of borrowed content
}
```

Solutions: `config.name.clone()`, `config.name.as_str()`, or taking ownership by
value.

### 11.4 Avoiding explicit lifetimes

Explicit lifetimes are needed when a return value borrows from one of several
inputs:

```rust
fn longest<'a>(a: &'a str, b: &'a str) -> &'a str {
    if a.len() >= b.len() { a } else { b }
}
```

Lifetime proliferation is avoided by:

- returning owned types (`String`, `Vec<T>`),
- using `Cow<'a, str>` for borrowed-or-owned strings,
- designing structs to own data (e.g., `struct Client { base_url: String }`
  rather than `&'a str`).

### 11.5 Iterator invalidation

Rust generally prevents it at compile time:

```rust,ignore
let mut items = vec![1, 2, 3];
for item in &items {
    items.push(4); // ERROR: cannot borrow as mutable while immutable borrow active
}
```

Solution:

```rust
let mut items = vec![1, 2, 3];
let to_add: Vec<i32> = items.iter().map(|x| x + 1).collect();
items.extend(to_add);
```

### 11.6 `as_ref`, `&`, and `take`

- `&x` creates a reference to `x`.
- `.as_ref()` converts `Option<T>`/`Result<T,E>`/smart pointer to a reference.
- `.take()` replaces `Option<T>` with `None` and returns the owned value.

```rust
let mut opt = Some(String::from("gpu"));
let borrowed: Option<&String> = opt.as_ref();
let owned: String = opt.take().unwrap();
```

### 11.7 `unwrap` vs `expect` vs `?`

- `unwrap()`: panic on error; only in tests/examples.
- `expect("message")`: panic with an invariant explanation; appropriate when a
  failure is logically impossible.
- `?`: propagate error; used in production fallible functions.

```rust
fn read_first_line(path: &str) -> std::io::Result<String> {
    let content = std::fs::read_to_string(path)?;
    Ok(content.lines().next().unwrap_or_default().to_string())
}
```

### 11.8 Deadlocks with `Mutex`

Deadlock patterns:

- Lock A then lock B in one thread; lock B then lock A in another.
- Locking the same non-reentrant mutex twice in one thread.

Prevention:

- A global lock order is defined.
- Locks are held briefly.
- `try_lock()` with timeout/backoff covers the cases where blocking is
  unacceptable.
- User code and `.await` are never called while holding `std::sync::MutexGuard`.
- For async, `tokio::sync::Mutex` is preferred, and it is not held across
  `.await` where the data can be copied out first.

### 11.9 Async pitfalls

- Blocking in async starves the executor thread.
- `std::sync::MutexGuard` is not `Send`, so holding it across `.await` fails.
- Non-`Send` futures cannot be spawned with `tokio::spawn`.
- `tokio::task::spawn_blocking` covers blocking I/O and CPU work.

### 11.10 `Rc` cycles and memory leaks

If `Rc` objects point to each other, reference counts never reach zero. `Weak`
covers parent/back edges; owned indices or an arena are the alternative.

### 11.11 `RefCell` double-borrow panic

```rust,ignore
let cell = std::cell::RefCell::new(0);
let a = cell.borrow();
let b = cell.borrow_mut(); // panics: already borrowed
```

Solutions:

- A `Ref` is not held while calling `borrow_mut`.
- Borrows are scoped narrowly.
- `try_borrow`/`try_borrow_mut` handle failure gracefully.

---

## 12. Full doubly linked list lab

The repo already contains a runnable `Rc<RefCell<Node<T>>>` + `Weak` doubly
linked list at:

```text
rust-interview-lab/src/bin/ll.rs
```

It demonstrates:

- `new`, `push_front`, `push_back`, `pop_front`, `pop_back`
- `peek_front`, `peek_back`
- `len`, `is_empty`
- safe extraction with `Rc::try_unwrap`
- `Weak` back pointers to avoid reference cycles
- unit tests added for invariants

Commands:

```bash
cd rust-interview-lab
cargo run --bin ll
cargo test --bin ll
```

### 12.1 The core structure

```rust
use std::cell::RefCell;
use std::rc::{Rc, Weak};

type NodeRef<T> = Rc<RefCell<Node<T>>>;
type WeakNodeRef<T> = Weak<RefCell<Node<T>>>;

struct Node<T> {
    data: T,
    next: Option<NodeRef<T>>,
    prev: Option<WeakNodeRef<T>>, // weak to avoid cycles
}

pub struct LinkedList<T> {
    head: Option<NodeRef<T>>,
    tail: Option<NodeRef<T>>,
    len: usize,
}
```

Why `Weak` for `prev`? If every node strongly referenced its previous node,
the chain would still be acyclic (head does not point back strongly from prev
of head? Actually `prev` of second points weak to first, fine; if prev were
`Rc`, there would be two strong paths to a node? Node2's next -> Node3 and
Node3's prev -> Node2, creating a cycle between adjacent nodes? Let's think:
Node1 -> Node2 strong, Node2.prev weak currently. If Node2.prev strong to
Node1, Node1 -> Node2 and Node2 -> Node1 creates cycle -> leak. So weak is
correct.)

### 12.2 The complete core implementation pattern

```rust
impl<T> LinkedList<T> {
    pub fn new() -> Self {
        LinkedList { head: None, tail: None, len: 0 }
    }

    pub fn len(&self) -> usize { self.len }
    pub fn is_empty(&self) -> bool { self.len == 0 }

    pub fn push_front(&mut self, data: T) {
        let new_node = Rc::new(RefCell::new(Node {
            data,
            next: None,
            prev: None,
        }));

        match self.head.take() {
            Some(old_head) => {
                old_head.borrow_mut().prev = Some(Rc::downgrade(&new_node));
                new_node.borrow_mut().next = Some(old_head);
            }
            None => {
                self.tail = Some(new_node.clone());
            }
        }
        self.head = Some(new_node);
        self.len += 1;
    }

    pub fn push_back(&mut self, data: T) {
        let new_node = Rc::new(RefCell::new(Node {
            data,
            next: None,
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

    pub fn pop_front(&mut self) -> Option<T> {
        self.head.take().and_then(|old_head| {
            let next = old_head.borrow_mut().next.take();
            match next {
                Some(next_node) => {
                    next_node.borrow_mut().prev = None;
                    self.head = Some(next_node);
                }
                None => {
                    self.tail = None;
                }
            }
            self.len -= 1;
            let node = Rc::try_unwrap(old_head).ok().unwrap().into_inner();
            Some(node.data)
        })
    }

    pub fn pop_back(&mut self) -> Option<T> {
        self.tail.take().and_then(|old_tail| {
            let prev = old_tail
                .borrow_mut()
                .prev
                .take()
                .and_then(|weak| weak.upgrade());
            match prev {
                Some(prev_node) => {
                    prev_node.borrow_mut().next = None;
                    self.tail = Some(prev_node);
                }
                None => {
                    self.head = None;
                }
            }
            self.len -= 1;
            let node = Rc::try_unwrap(old_tail).ok().unwrap().into_inner();
            Some(node.data)
        })
    }

    pub fn peek_front(&self) -> Option<std::cell::Ref<'_, T>> {
        self.head.as_ref().map(|node| {
            std::cell::Ref::map(node.borrow(), |node| &node.data)
        })
    }

    pub fn peek_back(&self) -> Option<std::cell::Ref<'_, T>> {
        self.tail.as_ref().map(|node| {
            std::cell::Ref::map(node.borrow(), |node| &node.data)
        })
    }
}
```

### 12.3 Keep iterators out of the phone-screen implementation

`IntoIterator`, `DoubleEndedIterator`, `iter_mut`, and a custom `Drop` add a lot of
code to this linked list and are not the point of the exercise. The parts that
matter:

- `Rc<RefCell<Node<T>>>` ownership,
- `Weak` back pointers to avoid cycles,
- correct push/pop with `Option::take()`,
- safe value extraction with `Rc::try_unwrap`.

The question of iteration has a one-sentence trade-off:

> "With `RefCell`, I cannot return normal `&T` references because borrows are
> runtime-checked. I could return `Ref<'_, T>`, or I could provide an owned
> iterator that pops from the list, but that is more machinery than this
> question needs."

The trade-off is stated rather than solved, which is the right amount of machinery
for the question.

---

## 13. The phone screen

### 13.1 Thinking aloud

- Constraints and examples come first.
- Complexity is stated before code is written.
- The intended approach is stated before it is started.

Example script:

> "I'll use a `VecDeque` for BFS because I need O(1) pop from the front and
> push to the back. I'll track visited in a `HashSet`. Time is O(n), space is
> O(n)."

### 13.2 Clarifying questions

- What are valid inputs? Empty? Negative numbers? Huge strings?
- Do I need to preserve order?
- Is this single-threaded or multithreaded?
- Is the API caller a library consumer or a CLI user?

### 13.3 The compiler and the tests

- The signature comes first.
- `assert_eq!` tests are added before or after the implementation.
- Borrow-checker errors are followed and explained.
- `cargo test` runs locally; in an online IDE, small `#[test]` modules are
  written and run.

### 13.4 Trade-offs

- `Vec` vs `LinkedList`: cache locality.
- `HashMap` vs `BTreeMap`: order/range vs average O(1).
- `Arc<Mutex>` vs `RwLock`: read/write ratio.
- `Rc<RefCell>` vs arena indices: borrow complexity.
- `reqwest` blocking vs async: simplicity vs scalability.

### 13.5 The online IDE

- Autocomplete supplies method names.
- Compiler diagnostics drive the iteration.
- Functions stay small and testable.
- Clever one-liners are avoided unless they are clearly idiomatic.

### 13.6 Common phone-screen problems

- Two sum with `HashMap`
- Valid parentheses with `VecDeque`/`Vec` stack
- LRU cache with `HashMap` + linked structure
- Rate limiter with timestamp deque or token bucket
- Worker pool with `mpsc` and `Arc<Mutex<Receiver>>`
- Number of islands with BFS/DFS
- Merge intervals with sorting + `match last_mut()`
- Trie for autocomplete/SDK command completion
- Topological sort for dependency graph
- Binary heap for top-k GPU jobs

The `rust-interview-lab` repo has all of these as library modules with tests,
plus runnable binaries for islands, syscall overhead, mutex poisoning,
shadowing, singly/doubly linked lists.

---

## 14. Using this guide with the rest of the repo

1. **Part 1** covers collections, ADTs, and smart pointers.
2. **Part 2** covers errors, async, and the SDK/CLI.
3. **Part 3** covers the gotchas and the linked list.
4. **Runnable examples** live in `rust-interview-lab`:

```bash
cd rust-interview-lab
cargo test
cargo run --bin ll
cargo run --bin count_islands
cargo run --bin mutex_poisoning
cargo run --bin singly_linked_list
cargo run --bin syscall_overhead
cargo run --bin shadowing
```

5. The full job description is mapped to this material in
   `docs/01-role-map-and-study-plan.md` and the operator/GPU docs (`04`, `05`,
   `10`).
