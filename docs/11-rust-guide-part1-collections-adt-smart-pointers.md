# 11: Rust Senior Interview Guide, Part 1: Collections, Idioms, ADTs, Smart Pointers

The theme is **idiomatic Rust: types that make invalid states unrepresentable,
pattern matching in place of `if-else` chains, and owned or borrowed data designed
from the start.** The code is written to be reproduced from memory.

---

## 1. Standard collections: internal representation, complexity, and when to use each

### 1.1 `Vec<T>`, contiguous growable array

Internal representation:

```text
ptr ─────► [ T | T | T | ... unused capacity ]
len = used elements
capacity = allocated slots
```

- `push`/`pop`: amortized O(1)
- `insert`/`remove` at index `i`: O(n)
- Indexing by position: O(1)
- Iteration: O(n)
- Memory: 3 words + capacity * size_of::<T>()

When to use: the default sequential collection. `LinkedList` is almost never the
better choice.

Runnable example:

```rust
fn main() {
    let mut gpus = Vec::with_capacity(4);
    gpus.push("A100");
    gpus.push("H100");
    gpus.push("L40S");

    assert_eq!(gpus[0], "A100");
    assert_eq!(gpus.get(10), None); // safe lookup

    if let Some(last) = gpus.pop() {
        println!("popped {last}");
    }

    gpus.insert(1, "B200");
    gpus.remove(0);

    for (i, gpu) in gpus.iter().enumerate() {
        println!("gpus[{i}] = {gpu}");
    }
}
```

Gotchas:

- `Vec` may reallocate when `len == capacity`; `with_capacity` avoids that when
  the size is known.
- Iterating while removing by index is easy to get wrong; `retain`, `drain`, or
  `collect` avoid it.
- `v[i]` panics on out-of-bounds; `v.get(i)` returns `Option<&T>`.
- `Vec` of `bool`/small ints is not bit-packed; `bitvec` packs them when that
  matters.

### 1.2 `VecDeque<T>`, ring buffer

Internal representation: one or two contiguous buffers managed as a circular
buffer.

- `push_front`/`pop_front`: O(1)
- `push_back`/`pop_back`: O(1)
- index access: O(1), but not guaranteed to be contiguous
- `make_contiguous()` can move elements

When to use: queue/worker pool, sliding window, BFS, retry queues.

Runnable example:

```rust
use std::collections::VecDeque;

fn main() {
    let mut queue = VecDeque::new();
    queue.push_back("job-a");
    queue.push_back("job-b");
    queue.push_front("urgent-job");

    assert_eq!(queue.pop_front(), Some("urgent-job"));
    assert_eq!(queue.pop_front(), Some("job-a"));
    queue.push_back("job-c");

    // Rotate to simulate round-robin scheduling.
    if let Some(job) = queue.pop_front() {
        queue.push_back(job);
    }

    println!("queue: {queue:?}");
}
```

Gotchas:

- `VecDeque` is not `Vec`, so `sort` is not available directly (drain into `Vec`).
- A "ring buffer" still stores all elements; capacity does not shrink unless
  `shrink_to_fit` is called.

### 1.3 `LinkedList<T>`, doubly linked list

Internal representation: individually heap-allocated nodes with `prev`/`next`
pointers. In `std`, a `LinkedList` is doubly linked and supports O(1)
push/pop at both ends.

- push/pop front/back: O(1)
- access by index: O(n)
- split/append: O(1)

When to use: **almost never** in normal code. `VecDeque` is faster and more
cache-friendly. Exceptions are rare algorithms that need guaranteed O(1)
splice/merge without copying or stable node identity.

`Vec` wins because of cache locality. A linked list is a red flag in most designs,
and appears here only as a way to test ownership.

Runnable example:

```rust
use std::collections::LinkedList;

fn main() {
    let mut list = LinkedList::new();
    list.push_back(2);
    list.push_back(3);
    list.push_front(1);

    let mut rest = list.split_off(1); // list=[1], rest=[2,3]
    list.append(&mut rest);

    while let Some(value) = list.pop_front() {
        print!("{value} ");
    }
    println!();
}
```

Gotchas:

- Poor cache locality; pointer chasing.
- No indexing (`list[0]` does not compile).
- `split_off` is O(n) for index positions because it must walk the list.

### 1.4 `HashMap<K, V>`, hash table

Internal representation: hash table with open addressing or hashbrown/SwissTable
in modern Rust. Uses a randomly seeded SipHash by default to resist HashDoS.

- `get`/`insert`/`remove`: O(1) average
- iteration order: unspecified and randomized per process
- `entry` API is the idiomatic way to insert-or-update

When to use: lookup by key, counts, caches, indexes.

Runnable example:

```rust
use std::collections::HashMap;

fn main() {
    let mut quotas: HashMap<String, u32> = HashMap::new();

    quotas.insert("team-a".into(), 8);
    *quotas.entry("team-b".into()).or_insert(4) += 1;

    match quotas.get("team-a") {
        Some(q) => println!("team-a quota {q}"),
        None => println!("team-a has no quota"),
    }

    let old = quotas.remove("team-b");
    println!("removed: {old:?}");
}
```

Gotchas:

- Iteration order is nondeterministic, and code that depends on it is broken.
- `HashMap` default hasher is slower than a custom `FxHash` for performance
  workloads, but switching only pays off when profiling says it matters.
- Borrowing conflicts between `get` and `insert` are resolved with `entry` or by
  cloning keys.

### 1.5 `BTreeMap<K, V>`, sorted map

Internal representation: B-tree.

- get/insert/remove: O(log n)
- iteration: sorted by key
- supports range queries: `range`, `range_mut`

When to use: ordered iteration, prefix/range scans, deterministic behavior,
small n (BTreeMap can beat HashMap at tiny sizes due to no hashing).

Runnable example:

```rust
use std::collections::BTreeMap;

fn main() {
    let mut nodes = BTreeMap::new();
    nodes.insert("node-3", 3);
    nodes.insert("node-1", 1);
    nodes.insert("node-2", 2);

    for (name, id) in &nodes {
        println!("{name}: {id}");
    }

    // Keys are sorted, so range scans are natural.
    for (name, id) in nodes.range("node-2"..) {
        println!("range >= node-2: {name}: {id}");
    }
}
```

Gotchas:

- Keys must implement `Ord`.
- No average O(1) lookup; still excellent in practice for many workloads.

### 1.6 `HashSet<T>`, hash set

Internal representation: `HashMap<T, ()>`.

- insert/remove/contains: O(1) average
- iteration: unordered
- `is_subset`, `union`, `intersection`, `difference` available

When to use: deduplication, membership tests, visited sets in graph search.

Runnable example:

```rust
use std::collections::HashSet;

fn main() {
    let mut allowed: HashSet<&str> = HashSet::new();
    allowed.insert("a100");
    allowed.insert("h100");

    println!("contains h100? {}", allowed.contains("h100"));
    allowed.remove("a100");

    for product in allowed {
        println!("allowed: {product}");
    }
}
```

Gotchas:

- Iteration order is random.
- Sorted membership uses `BTreeSet`.
- Borrowing: `HashSet<&str>` and `HashSet<String>` have different ergonomics.

### 1.7 `BTreeSet<T>`, sorted set

Internal representation: `BTreeMap<T, ()>`.

- insert/remove/contains: O(log n)
- iteration sorted
- range queries

When to use: sorted unique values or range scans.

Runnable example:

```rust
use std::collections::BTreeSet;

fn main() {
    let mut zones = BTreeSet::new();
    zones.insert("us-east-1");
    zones.insert("us-west-2");
    zones.insert("eu-central-1");

    assert!(zones.contains("us-west-2"));

    for zone in zones.range("eu".."us") {
        println!("{zone}");
    }
}
```

### 1.8 `BinaryHeap<T>`, priority queue

Internal representation: implicit binary heap in a `Vec`.

- `push`: O(log n) amortized
- `pop` (max): O(log n)
- `peek`: O(1)
- max-heap by default; min-heap with `Reverse<T>`

When to use: top-k, scheduling, Dijkstra.

Runnable example:

```rust
use std::cmp::Reverse;
use std::collections::BinaryHeap;

fn main() {
    let mut max_heap = BinaryHeap::new();
    max_heap.push(3);
    max_heap.push(1);
    max_heap.push(4);
    assert_eq!(max_heap.pop(), Some(4));

    let mut min_heap = BinaryHeap::new();
    min_heap.push(Reverse(3));
    min_heap.push(Reverse(1));
    min_heap.push(Reverse(4));
    assert_eq!(min_heap.pop(), Some(Reverse(1)));
}
```

Gotchas:

- `BinaryHeap` does not provide arbitrary removal/update efficiently.
- A min-heap needs `Reverse`.
- To avoid allocating a new `Reverse` each time, store `Reverse<MyType>`.

### 1.9 Collection cheat sheet

| Need | Collection | Complexity | Note |
|---|---|---|---|
| Default sequential | `Vec<T>` | O(1) push/pop amortized | cache-friendly |
| Queue/deque/BFS | `VecDeque<T>` | O(1) ends | ring buffer |
| Ordered key-value | `BTreeMap<K,V>` | O(log n) | range queries |
| Unordered key-value | `HashMap<K,V>` | O(1) avg | random order |
| Dedup membership | `HashSet<T>` | O(1) avg | random order |
| Sorted membership | `BTreeSet<T>` | O(log n) | range queries |
| Priority queue | `BinaryHeap<T>` | O(log n) push/pop | max heap |
| Insertion at both ends | `LinkedList<T>` | O(1) ends, O(n) access | avoid in practice |

---

## 2. Idiomatic Rust coding standards (Rust API Guidelines)

### 2.1 Naming

- `snake_case`: functions, methods, variables, modules
- `CamelCase`: types, enum variants, traits
- `SCREAMING_SNAKE_CASE`: constants and statics
- `&self` methods read only; `&mut self` mutates; `self` consumes
- Boolean-like methods: `is_empty()`, `contains()`, `has_...`
- Conversion names: `as_` (cheap, borrowed), `to_` (expensive, owned), `into_`
  (consuming, owned)

```rust
const DEFAULT_GPU_COUNT: u32 = 1;

pub struct GpuWorkload {
    image: String,
    gpu_count: u32,
}

impl GpuWorkload {
    pub fn new(image: impl Into<String>) -> Self { ... }

    pub fn image(&self) -> &str { &self.image }
    pub fn gpu_count(&self) -> u32 { self.gpu_count }
    pub fn with_gpu_count(mut self, count: u32) -> Self { ... }
}
```

### 2.2 Documentation

- `///` documents the item after it.
- `//!` documents the module or crate.
- A doc-test example belongs on any non-trivial API.

```rust
/// Returns the number of complete GPU jobs of size `requested` that fit in
/// `available`.
///
/// ```
/// use mylib::jobs_that_fit;
/// assert_eq!(jobs_that_fit(4, 10), 2);
/// ```
pub fn jobs_that_fit(requested: u32, available: u32) -> u32 {
    available / requested
}
```

### 2.3 Derive common traits

```rust
#[derive(Debug, Clone, PartialEq, Eq, Hash, Default)]
pub struct SchedulerConfig {
    pub max_gpus: u32,
    pub region: String,
}

impl SchedulerConfig {
    pub fn with_capacity(&mut self, n: usize) -> &mut Self { ... }
}
```

Which derives apply:

- `Debug` almost always.
- `Clone` when cheap or API callers need copies.
- `PartialEq`/`Eq` when equality is meaningful.
- `Hash` if used in `HashSet`/`HashMap`.
- `Default` when zero-value config is valid.

### 2.4 Constructors

- `new()` for primary constructor.
- `with_capacity()` for collections/config where capacity is known.
- `from_...` for conversions.
- `Default` for zero-value configurations.
- Builder for many optional fields.

### 2.5 Errors

- Library: custom error `enum` with `thiserror`.
- Binary/application: `anyhow`.
- Public API: return `Result<T, Self::Error>` with a typed error.
- Never `unwrap()` in production unless the invariant is locally proven. Where
  that is unavoidable, `expect("message with invariant")` records the reason.

### 2.6 Builder pattern

```rust
#[derive(Debug, Clone)]
pub struct WorkloadSpec {
    image: String,
    gpu_count: u32,
    runtime_class: Option<String>,
}

#[derive(Default)]
pub struct WorkloadSpecBuilder {
    image: Option<String>,
    gpu_count: u32,
    runtime_class: Option<String>,
}

impl WorkloadSpecBuilder {
    pub fn image(mut self, image: impl Into<String>) -> Self {
        self.image = Some(image.into());
        self
    }

    pub fn gpu_count(mut self, count: u32) -> Self {
        self.gpu_count = count;
        self
    }

    pub fn runtime_class(mut self, name: impl Into<String>) -> Self {
        self.runtime_class = Some(name.into());
        self
    }

    pub fn build(self) -> Result<WorkloadSpec, String> {
        Ok(WorkloadSpec {
            image: self.image.ok_or("image is required")?,
            gpu_count: self.gpu_count,
            runtime_class: self.runtime_class,
        })
    }
}

fn main() -> Result<(), String> {
    let spec = WorkloadSpecBuilder::default()
        .image("nvcr.io/nvidia/tritonserver:24.05-py3")
        .gpu_count(1)
        .runtime_class("nvidia")
        .build()?;
    println!("{spec:?}");
    Ok(())
}
```

---

## 3. Algebraic data types and pattern matching

Rust structs are product types: they combine fields. Enums are sum types: a
value is exactly one variant. Together they form ADTs, which model domains
without illegal states.

### 3.1 Typed state with `enum`

```rust
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum WorkloadState {
    Pending,
    Provisioning,
    Running,
    Terminating,
    Terminated,
    Failed { reason: String },
}

impl WorkloadState {
    pub fn summary(&self) -> String {
        match self {
            WorkloadState::Pending => "waiting for resources".into(),
            WorkloadState::Provisioning => "allocating GPU".into(),
            WorkloadState::Running => "running".into(),
            WorkloadState::Terminating => "cleaning up".into(),
            WorkloadState::Terminated => "stopped".into(),
            WorkloadState::Failed { reason } => format!("failed: {reason}"),
        }
    }

    pub fn can_transition_to(&self, next: &Self) -> bool {
        matches!(
            (self, next),
            (WorkloadState::Pending, WorkloadState::Provisioning)
                | (WorkloadState::Provisioning, WorkloadState::Running)
                | (WorkloadState::Running, WorkloadState::Terminating)
                | (WorkloadState::Terminating, WorkloadState::Terminated)
                | (WorkloadState::Failed { .. }, WorkloadState::Pending)
        )
    }
}
```

### 3.2 `match` over `if-else`

```rust
fn classify(status_code: u16) -> &'static str {
    match status_code {
        200..=299 => "success",
        400..=499 => "client error",
        500..=599 => "server error",
        _ => "unknown",
    }
}

fn main() {
    println!("{}", classify(429));
}
```

### 3.3 `if let` and `while let`

`if let` fits when only one variant matters and the `else` arm is trivial:

```rust
let mut queue = std::collections::VecDeque::from([1, 2, 3]);

while let Some(job) = queue.pop_front() {
    println!("processing {job}");
}

if let Some(value) = queue.pop_front() {
    println!("unexpected: {value}");
} else {
    println!("queue is empty");
}
```

### 3.4 Matching on data-carrying variants

```rust
#[derive(Debug)]
pub enum ApiError {
    Invalid { field: String, message: String },
    RateLimited { retry_after_secs: u64 },
    NotFound { resource: String },
}

fn message(error: &ApiError) -> String {
    match error {
        ApiError::Invalid { field, message } => format!("{field}: {message}"),
        ApiError::RateLimited { retry_after_secs } => {
            format!("retry after {retry_after_secs}s")
        }
        ApiError::NotFound { resource } => format!("{resource} not found"),
    }
}
```

### 3.5 Guards

```rust
fn error_severity(err: &ApiError) -> &'static str {
    match err {
        ApiError::RateLimited { retry_after_secs } if *retry_after_secs < 2 => "mild",
        ApiError::RateLimited { .. } => "severe",
        ApiError::NotFound { .. } => "actionable",
        ApiError::Invalid { .. } => "programming error",
    }
}
```

---

## 4. Smart pointers and interior mutability

### 4.1 Mental model

| Type | Ownership | Mutability | Thread-safe | Use |
|---|---|---|---|---|
| `Box<T>` | single owner | mutable if owner is `mut` | yes if `T: Send` | heap allocation, recursive types, trait objects |
| `Rc<T>` | shared owner, non-atomic count | immutable | **no** | same-thread sharing |
| `Arc<T>` | shared owner, atomic count | immutable | yes | multi-thread sharing |
| `RefCell<T>` | single owner | runtime checked | **no** | interior mutability in one thread |
| `Mutex<T>` | single owner | blocking lock | yes | shared mutable state |
| `RwLock<T>` | single owner | read/write locks | yes | many readers, rare writer |
| `Weak<T>` | non-owning reference | n/a | n/a | break cycles |

### 4.2 `Box<T>`

`Box` allocates on the heap. It is needed for:

- recursive types (tree/list)
- trait objects (`Box<dyn Error>`)
- moving large data while keeping stack small

```rust
#[derive(Debug)]
enum Expr {
    Lit(i64),
    Add(Box<Expr>, Box<Expr>),
}

fn eval(expr: &Expr) -> i64 {
    match expr {
        Expr::Lit(n) => *n,
        Expr::Add(l, r) => eval(l) + eval(r),
    }
}

fn main() {
    let expr = Expr::Add(Box::new(Expr::Lit(1)), Box::new(Expr::Lit(2)));
    println!("{}", eval(&expr));
}
```

### 4.3 `Rc<T>` and `RefCell<T>`

`Rc` gives shared ownership but no mutation. `RefCell` adds runtime borrow
checking. The combination `Rc<RefCell<T>>` is the classic graph/list building
block inside one thread.

```rust
use std::cell::RefCell;
use std::rc::Rc;

fn main() {
    let shared = Rc::new(RefCell::new(0i32));
    let a = Rc::clone(&shared);
    let b = Rc::clone(&shared);

    *a.borrow_mut() += 1;
    *b.borrow_mut() += 10;

    println!("value = {}", shared.borrow()); // 11
}
```

Gotcha: `borrow()` panics if a mutable borrow is already active, so holding a
`Ref`/`RefMut` across another call that borrows the same `RefCell` panics.

### 4.4 `Arc<T>` and `Mutex<T>`

```rust
use std::sync::{Arc, Mutex};
use std::thread;

fn main() {
    let counter = Arc::new(Mutex::new(0u32));
    let mut handles = Vec::new();

    for _ in 0..4 {
        let counter = Arc::clone(&counter);
        handles.push(thread::spawn(move || {
            for _ in 0..1_000 {
                let mut guard = counter.lock().unwrap();
                *guard += 1;
            }
        }));
    }

    for handle in handles {
        handle.join().unwrap();
    }

    println!("counter = {}", *counter.lock().unwrap());
}
```

Gotchas:

- A mutex guard should be held as briefly as possible.
- Unknown or async code should not be called while holding a guard.
- `try_lock()` where blocking is not acceptable.
- Poisoning: if a thread panics while holding the guard, later `lock()` returns
  `Err(PoisonError)`. Recovery is `into_inner()`, or the error can be propagated.

### 4.5 `RwLock<T>`

Many readers, occasional writer. `RwLock` suits workloads where reads dominate
and the critical section is short.

```rust
use std::sync::{Arc, RwLock};

fn main() {
    let config = Arc::new(RwLock::new(vec!["a100".to_string()]));

    // Reader
    let config = Arc::clone(&config);
    let reader = std::thread::spawn(move || {
        let gpus = config.read().unwrap();
        println!("readers: {gpus:?}");
    });

    // Writer
    let config = Arc::clone(&config);
    let writer = std::thread::spawn(move || {
        config.write().unwrap().push("h100".to_string());
    });

    reader.join().unwrap();
    writer.join().unwrap();
}
```

Gotcha: writer starvation is possible under heavy read load, so read sections
should be short.

### 4.6 `Weak<T>` breaks cycles

If `A` owns `B` and `B` owns `A` via `Rc`, neither is ever freed, so back-edges
use `Weak`. This is why the doubly linked list in this repo stores `Weak` for
`prev`.

```rust
use std::cell::RefCell;
use std::rc::{Rc, Weak};

#[derive(Debug)]
struct Node {
    value: i32,
    parent: RefCell<Weak<Node>>,
}

fn main() {
    let parent = Rc::new(Node {
        value: 1,
        parent: RefCell::new(Weak::new()),
    });
    let child = Rc::new(Node {
        value: 2,
        parent: RefCell::new(Rc::downgrade(&parent)),
    });

    // Child -> parent is weak, so dropping child does not keep parent alive.
    let upgraded = child.parent.borrow().upgrade();
    println!("parent value: {:?}", upgraded.map(|p| p.value));
}
```

### 4.7 `Send` and `Sync`

- `Send`: type can be moved to another thread.
- `Sync`: type can be shared by reference across threads (`&T` is `Send`).

Implications:

- `Rc<T>` is neither `Send` nor `Sync`.
- `Arc<T>` is `Send + Sync` if `T: Send + Sync`.
- `RefCell<T>` is `Send` only if `T: Send`, but not `Sync`.
- `Mutex<T>` is `Sync` if `T: Send`.
- Raw pointers are neither by default; unsafe wrapper types must document safety.

A custom type is `Send + Sync` when it only composes `Send + Sync` fields. A
compile-time assertion checks that:

```rust
fn assert_send_sync<T: Send + Sync>() {}

struct Scheduler {
    client: std::sync::Arc<tokio::sync::Mutex<()>>,
}

#[test]
fn scheduler_is_send_sync() {
    assert_send_sync::<Scheduler>();
}
```

---

## 5. Summary

- Internal representation is what explains the complexity of `Vec`, `VecDeque`,
  `HashMap`, `BTreeMap`, and `BinaryHeap`.
- `entry()` is the idiom for hash-map insert-or-update.
- State and errors are modelled with `enum` + `match`.
- `Rc<RefCell<T>>` covers single-thread graphs and lists; `Arc<Mutex<T>>` covers
  shared multithread state; `Weak` breaks cycles.
- Cache locality is why `Vec`/`VecDeque` usually beat `LinkedList`.
