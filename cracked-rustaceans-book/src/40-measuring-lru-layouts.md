# 40. Measuring Two LRU Layouts {#measuring-lru-layouts}

*Source files: [`benchmarking_examples/cache/`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/benchmarking_examples/cache/) and [`benchmarking_examples/benchmark.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/benchmarking_examples/benchmark.rs). Run it with `cargo run --release --bin benchmark cache`.*

## Problem Statement

Implement a fixed-capacity LRU cache twice with identical behaviour:

- **arena**: nodes in a `Vec`, linked by `Option<usize>`;
- **rc_list**: one `Rc<RefCell<Node>>` per entry, linked forward by `Rc` and backward
  by `Weak`.

Drive both with the same request stream, check that they produce the same hits, and
report the time per request.

## Designing a Solution

**A shared trait.** Both caches implement `Cache<K, V>`, with `new`, `get`, `put`,
`len`, and `variant`. The benchmark is a generic function over `C: Cache<u64, u64>`,
so the only difference between the two measured loops is the cache type.

**Values that are `Copy`.** The trait requires `V: Copy`, and `get` returns `Option<V>`
rather than a reference. This lets the `Rc<RefCell>` version return a value without
holding a `Ref` guard past the end of the method, and keeps the two signatures
identical.

**A realistic request stream.** A uniform stream over the key space would make every
cache miss most of the time. The benchmark instead draws four requests in five from a
hot set of 1 percent of the keys and the rest from the whole space. The stream comes
from a linear congruential generator seeded with a constant, so both caches see the
same sequence and the hit counts can be compared.

**Where the two designs differ.** On a hit, both look up the key in a `HashMap` and
move the entry to the front. The arena writes a few integers in one vector. The list
clones an `Rc`, upgrades a `Weak`, takes `RefCell` borrows on up to three nodes, and
follows pointers to separate heap blocks. On a miss at capacity, the arena overwrites
the evicted slot, while the list frees the evicted node and allocates a new one.

## Implementation

### The contract

```rust
//! Two LRU caches of the same design, stored differently, so one benchmark loop
//! can cover both.
//!
//! [`arena`] keeps nodes in a `Vec` and links them by `usize` index.
//! [`rc_list`] allocates an `Rc<RefCell<_>>` per node and links them by pointer.

pub mod arena;
pub mod rc_list;

use std::hash::Hash;

/// The operations every cache supports.
pub trait Cache<K, V>
where
    K: Hash + Eq + Clone,
    V: Copy,
{
    /// A cache that holds at most `capacity` entries.
    ///
    /// # Panics
    /// Panics if `capacity == 0`, since a zero-capacity cache cannot store
    /// anything.
    fn new(capacity: usize) -> Self;

    /// Looks up `key`, promoting it to most recently used on a hit.
    fn get(&mut self, key: &K) -> Option<V>;

    /// Inserts or updates `key`, evicting the least recently used entry when
    /// the cache is full.
    fn put(&mut self, key: K, value: V);

    /// How many entries are cached.
    fn len(&self) -> usize;

    /// The variant's name, for benchmark output.
    fn variant() -> &'static str;
}
```

### The arena

The arena version is the cache from chapter 18 with its public methods moved into the
trait implementation. The first listing shows the types and `touch`, and the second the
trait implementation.

````rust
//! Fixed-capacity LRU cache backed by an arena.
//!
//! ## Design
//!
//! Two structures cooperate to give O(1) `get` and `put`:
//!
//! * `lookup_table: HashMap<K, usize>` — key to index into the arena.
//! * `nodes: Vec<Node<K, V>>` — an **arena** of nodes; indices play the role of
//!   pointers, sidestepping `Rc<RefCell<...>>` and its borrow-checker pain.
//!
//! The arena is stitched into a doubly linked list through `head`/`tail`:
//!
//! ```text
//!   MRU  ->  head -> ... -> tail  ->  LRU
//! ```
//!
//! On eviction the tail slot is **reused** instead of removed, so no node is
//! deallocated mid-life and the arena stays dense and index-stable.

use std::collections::HashMap;
use std::hash::Hash;

use super::Cache;

/// A single cache entry, linked into the recency list by index.
struct Node<K, V> {
    /// Retained so the corresponding map entry can be removed when evicting.
    key: K,
    value: V,
    /// Neighbour closer to the MRU end (`None` if this is `head`).
    prev: Option<usize>,
    /// Neighbour closer to the LRU end (`None` if this is `tail`).
    next: Option<usize>,
}

pub struct LruCache<K, V> {
    /// Maximum number of entries; `>= 1`.
    cap: usize,
    /// Key to arena index. The single source of truth for "is this cached?".
    lookup_table: HashMap<K, usize>,
    /// Arena of nodes; indices are the "pointers" of the linked list.
    nodes: Vec<Node<K, V>>,
    /// Arena index of the most recently used entry.
    head: Option<usize>,
    /// Arena index of the least recently used entry (next to evict).
    tail: Option<usize>,
}

impl<K, V> LruCache<K, V>
where
    K: Hash + Eq + Clone,
    V: Copy,
{
    /// Promotes node `i` to `head` (MRU).
    ///
    /// Handles both cases in one pass:
    /// * **Already linked** — detach from its current neighbours first.
    /// * **Brand new** — the node has `prev = next = None` and is not yet
    ///   referenced by `head`/`tail`, so the detach step is skipped.
    fn touch(&mut self, i: usize) {
        let (prev, next) = (self.nodes[i].prev, self.nodes[i].next);

        // A node is "linked" if any of its four references exist.
        let linked =
            prev.is_some() || next.is_some() || self.head == Some(i) || self.tail == Some(i);

        if linked {
            // Splice `i` out of the list.
            match prev {
                Some(p) => self.nodes[p].next = next,
                None => self.head = next,
            }
            match next {
                Some(n) => self.nodes[n].prev = prev,
                None => self.tail = prev,
            }
        }

        // Splice `i` in at the front.
        self.nodes[i].prev = None;
        self.nodes[i].next = self.head;
        if let Some(h) = self.head {
            self.nodes[h].prev = Some(i);
        }
        self.head = Some(i);
        if self.tail.is_none() {
            self.tail = Some(i);
        }
    }
}
````

```rust
impl<K, V> Cache<K, V> for LruCache<K, V>
where
    K: Hash + Eq + Clone,
    V: Copy,
{
    fn new(capacity: usize) -> Self {
        assert!(capacity > 0, "capacity must be > 0");
        Self {
            cap: capacity,
            lookup_table: HashMap::new(),
            nodes: Vec::new(),
            head: None,
            tail: None,
        }
    }

    fn get(&mut self, key: &K) -> Option<V> {
        let i = *self.lookup_table.get(key)?;
        self.touch(i);
        Some(self.nodes[i].value)
    }

    fn put(&mut self, key: K, value: V) {
        // Case 1: key already present, update the value and promote.
        if let Some(&i) = self.lookup_table.get(&key) {
            self.nodes[i].value = value;
            self.touch(i);
            return;
        }

        // Case 2: room to grow, append a fresh node.
        if self.nodes.len() < self.cap {
            let i = self.nodes.len();
            self.nodes.push(Node {
                key: key.clone(),
                value,
                prev: None,
                next: None,
            });
            self.lookup_table.insert(key, i);
            self.touch(i);
            return;
        }

        // Case 3: at capacity, reuse the LRU slot. `tail` is `Some` here because
        // `cap >= 1` and the arena is full, but handle `None` anyway.
        if let Some(i) = self.tail {
            let old_key = std::mem::replace(&mut self.nodes[i].key, key);
            self.nodes[i].value = value;
            self.lookup_table.remove(&old_key);
            self.lookup_table.insert(self.nodes[i].key.clone(), i);
            self.touch(i);
        }
    }

    fn len(&self) -> usize {
        self.lookup_table.len()
    }

    fn variant() -> &'static str {
        "arena (Vec + indices)"
    }
}
```

`get` returns `Some(self.nodes[i].value)`, a copy, because the trait bound is
`V: Copy`. Chapter 18's version returned `Option<&V>`.

### The reference-counted list

```rust
//! LRU cache built from an `Rc<RefCell<_>>` doubly linked list.
//!
//! The textbook version: `Rc` forward, `Weak` back, and a `HashMap` from key to
//! node. Every node is its own heap allocation, and every move to the front
//! clones an `Rc`, upgrades a `Weak`, and borrows the `RefCell`.
//!
//! The default drop would free a node, which frees its `next`, one stack frame
//! per element, so `Drop` is written to unlink iteratively.

use std::cell::RefCell;
use std::collections::HashMap;
use std::hash::Hash;
use std::rc::{Rc, Weak};

use super::Cache;

type Link<K, V> = Option<Rc<RefCell<Node<K, V>>>>;

struct Node<K, V> {
    key: K,
    value: V,
    prev: Weak<RefCell<Node<K, V>>>,
    next: Link<K, V>,
}

pub struct LruCache<K, V> {
    cap: usize,
    map: HashMap<K, Rc<RefCell<Node<K, V>>>>,
    head: Link<K, V>,
    tail: Link<K, V>,
}
```

`Link<K, V>` is the type alias for an owning, optional forward link. The backward link
`prev` is a `Weak`, so two neighbours do not keep each other alive. The cache holds
three kinds of strong reference to a node: the map entry, the previous node's `next`
(or `head`), and, for the last node, `tail`.

```rust
impl<K, V> LruCache<K, V>
where
    K: Hash + Eq + Clone,
    V: Copy,
{
    fn detach(&mut self, node: &Rc<RefCell<Node<K, V>>>) {
        let (prev, next) = {
            let entry = node.borrow();
            (entry.prev.clone(), entry.next.clone())
        };

        match prev.upgrade() {
            Some(previous) => previous.borrow_mut().next = next.clone(),
            None => self.head = next.clone(),
        }
        match &next {
            Some(following) => following.borrow_mut().prev = prev,
            None => self.tail = prev.upgrade(),
        }
    }

    fn push_front(&mut self, node: Rc<RefCell<Node<K, V>>>) {
        let head = self.head.clone();
        {
            let mut entry = node.borrow_mut();
            entry.prev = Weak::new();
            entry.next = head.clone();
        }
        match &head {
            Some(previous) => previous.borrow_mut().prev = Rc::downgrade(&node),
            None => self.tail = Some(node.clone()),
        }
        self.head = Some(node);
    }
}
```

`detach` first clones both links out of the node inside a block, so the `Ref` guard
from `node.borrow()` ends before any `borrow_mut` runs. `RefCell` checks borrows at
run time, and a guard that lives longer than it needs to is the usual cause of an
`already borrowed` panic. The block rules that out by construction, at the cost of one
`Weak` clone and one `Rc` clone.

`prev.upgrade()` turns the weak back-link into a strong one for the duration of the
statement. When it returns `None`, the node was the head, and `head` is moved to the
successor. When `next` is `None`, the node was the tail, and `tail` becomes the
upgraded predecessor.

`push_front` clears the node's `prev`, points its `next` at the old head, and makes
the old head's `prev` a `Weak` to the node. If the list was empty, the node becomes
the tail as well.

```rust
impl<K, V> Cache<K, V> for LruCache<K, V>
where
    K: Hash + Eq + Clone,
    V: Copy,
{
    fn new(capacity: usize) -> Self {
        assert!(capacity > 0, "capacity must be > 0");
        Self {
            cap: capacity,
            map: HashMap::new(),
            head: None,
            tail: None,
        }
    }

    fn get(&mut self, key: &K) -> Option<V> {
        let node = self.map.get(key)?.clone();
        self.detach(&node);
        self.push_front(node.clone());
        Some(node.borrow().value)
    }

    fn put(&mut self, key: K, value: V) {
        if let Some(node) = self.map.get(&key).cloned() {
            node.borrow_mut().value = value;
            self.detach(&node);
            self.push_front(node);
            return;
        }

        if self.map.len() >= self.cap {
            if let Some(victim) = self.tail.clone() {
                let old_key = victim.borrow().key.clone();
                self.map.remove(&old_key);
                self.detach(&victim);
            }
        }

        let node = Rc::new(RefCell::new(Node {
            key: key.clone(),
            value,
            prev: Weak::new(),
            next: None,
        }));
        self.map.insert(key, node.clone());
        self.push_front(node);
    }

    fn len(&self) -> usize {
        self.map.len()
    }

    fn variant() -> &'static str {
        "Rc<RefCell> list"
    }
}

impl<K, V> Drop for LruCache<K, V> {
    fn drop(&mut self) {
        // Unlink iteratively: dropping a million-node chain recursively overflows
        // the stack.
        let mut current = self.head.take();
        while let Some(node) = current {
            let next = node.borrow_mut().next.take();
            node.borrow_mut().prev = Weak::new();
            current = next;
        }
    }
}
```

`get` clones the `Rc` out of the map before calling `detach`, because `detach` takes
`&mut self` and the map entry borrows `self`. The clone is a reference-count
increment. Each hit therefore performs several count updates, a `Weak` upgrade, and
four or more `RefCell` borrow checks, none of which the arena needs.

The `Drop` implementation unlinks the chain iteratively for the reason chapter 38
measured: the default destructor would free a 65,536-node chain recursively.

### The benchmark

```rust
// ---------------------------------------------------------------------------
// Cache: arena vs Rc<RefCell> linked list
// ---------------------------------------------------------------------------

/// Request stream with realistic locality: four requests in five come from a hot
/// set of 1% of the keys, the rest from the whole space.
fn key_at(state: u64) -> u64 {
    let mixed = state >> 17;
    if (state >> 33) % 100 < 80 {
        mixed % (KEY_SPACE / 100)
    } else {
        mixed % KEY_SPACE
    }
}

/// The fastest of `CACHE_RUNS` timed passes, with the hit count and final size
/// from the last one. Each pass starts from an empty cache, so the stream is the
/// same every time.
fn best_cache_run<C: Cache<u64, u64>>() -> (Duration, u64, usize) {
    let mut best = Duration::MAX;
    let mut hits = 0;
    let mut len = 0;

    for _ in 0..CACHE_RUNS {
        let mut cache = C::new(CACHE_CAPACITY);
        let (elapsed, run_hits) = cache_workload(&mut cache);
        best = best.min(elapsed);
        hits = run_hits;
        len = cache.len();
    }
    (best, hits, len)
}

/// The same request stream against any cache.
fn cache_workload<C: Cache<u64, u64>>(cache: &mut C) -> (Duration, u64) {
    let mut state = 0x9e37_79b9_7f4a_7c15u64;
    let mut hits = 0u64;

    let start = Instant::now();
    for _ in 0..OPERATIONS {
        state = state
            .wrapping_mul(6_364_136_223_846_793_005)
            .wrapping_add(1_442_695_040_888_963_407);
        let key = key_at(state);

        match cache.get(&key) {
            Some(value) => {
                hits += 1;
                black_box(value);
            }
            None => cache.put(key, key.rotate_left(17)),
        }
    }
    (start.elapsed(), hits)
}

fn cache_benchmark() {
    println!(
        "LRU cache: {} entries, {} requests over {} keys",
        with_thousands(CACHE_CAPACITY as u64),
        with_thousands(OPERATIONS),
        with_thousands(KEY_SPACE)
    );
    println!("A miss inserts and evicts the least recently used entry.");
    println!("Best of {CACHE_RUNS} runs per cache.\n");

    let (arena_time, arena_hits, arena_len) = best_cache_run::<ArenaCache<u64, u64>>();
    let (list_time, list_hits, list_len) = best_cache_run::<RcCache<u64, u64>>();

    // Same population and same hit count, or this compares nothing.
    assert_eq!(arena_len, list_len);
    assert_eq!(
        arena_hits, list_hits,
        "the two runs saw different request streams"
    );

    println!(
        "  hit rate: {:.1}%  ({} hits, {} inserts)\n",
        arena_hits as f64 * 100.0 / OPERATIONS as f64,
        with_thousands(arena_hits),
        with_thousands(OPERATIONS - arena_hits)
    );

    let per_request = |elapsed: Duration| elapsed.as_nanos() as f64 / OPERATIONS as f64;

    // `{:.2?}` uses Duration's own Debug format, rounded to two decimals.
    println!("  {:<22} {:>12} {:>13}", "storage", "total", "per request");
    println!("  {}", "-".repeat(48));
    for (name, elapsed) in [
        (
            <ArenaCache<u64, u64> as Cache<u64, u64>>::variant(),
            arena_time,
        ),
        (<RcCache<u64, u64> as Cache<u64, u64>>::variant(), list_time),
    ] {
        println!(
            "  {name:<22} {elapsed:>12.2?} {:>8.0} ns",
            per_request(elapsed)
        );
    }

    let speedup = list_time.as_secs_f64() / arena_time.as_secs_f64();
    println!(
        "\n  the arena is {speedup:.2}x faster on the same requests: {arena_time:.2?} against {list_time:.2?}"
    );
    println!("  the arena reuses the evicted slot; the list frees a node and allocates another");
}
```

`key_at` uses two different ranges of bits from the generator state: bits above 33
choose between the hot set and the whole space, and bits above 17 choose the key. The
low bits of a linear congruential generator have short periods, so both shifts
discard them.

The two assertions after the runs are the benchmark's correctness check. If the two
caches had different eviction behaviour, the same stream would produce different hit
counts and the program would stop before printing a time.

`<ArenaCache<u64, u64> as Cache<u64, u64>>::variant()` is fully qualified syntax. It is
needed because `variant` is an associated function with no `self`, and the type has
no inherent function of that name to fall back on.

### The arena cache as a standalone program

The repository also holds the arena cache as a runnable program,
[`src/bin/lru_cache_arena.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/lru_cache_arena.rs). Its `Node`, `LruCache`,
`touch`, `get`, `put`, and tests are the same as `src/problems/lru_cache_easy.rs`, which
chapter 18 prints in full; its test module is named `tests_for_lru`. It adds a `main`
that runs the eviction sequence traced in chapter 18. Run it with
`cargo run --bin lru_cache_arena`.

```rust
fn main() {
    let mut cache = LruCache::new(2);

    cache.put("A", 10);
    cache.put("B", 20);
    println!("get A = {:?}", cache.get(&"A")); // Some(10), A now MRU

    cache.put("C", 30); // evicts B (LRU)

    println!("get B = {:?}", cache.get(&"B")); // None
    println!("get A = {:?}", cache.get(&"A")); // Some(10)
    println!("get C = {:?}", cache.get(&"C")); // Some(30)

    cache.put("A", 99);
    println!("get A = {:?}", cache.get(&"A")); // Some(99)
}
```

The program prints:

```text
get A = Some(10)
get B = None
get A = Some(10)
get C = Some(30)
get A = Some(99)
```

## Intuition

The recorded result from `BENCHMARKS.md`, release build, on an NVIDIA Jetson board
with an 8-core Cortex-A78AE:

```text
LRU cache: 65,536 entries, 10,000,000 requests over 131,072 keys
A miss inserts and evicts the least recently used entry.
Best of 3 runs per cache.

  hit rate: 89.8%  (8,979,314 hits, 1,020,686 inserts)

  storage                       total   per request
  ------------------------------------------------
  arena (Vec + indices)         1.03s      103 ns
  Rc<RefCell> list              1.86s      186 ns

  the arena is 1.81x faster on the same requests: 1.03s against 1.86s
  the arena reuses the evicted slot; the list frees a node and allocates another
```

Both caches pay for the same `HashMap` lookup on every request, and that lookup is a
large part of the 103 ns the arena spends. The ratio between the two designs is
therefore bounded by the share of each request spent on list maintenance. The
repository's report measured the ratio across several access patterns: it ranged from
1.1 to 1.9, reaching 1.83 for a stream of hits only and falling to 1.30 for a stream
that never repeats a key.

## Time and Space Complexity

| Operation | arena | rc_list |
|---|---|---|
| `get` hit | `O(1)` expected; integer writes in one `Vec` | `O(1)` expected; count updates, a `Weak` upgrade, several borrow checks |
| `put` miss at capacity | `O(1)` expected; no allocation | `O(1)` expected; one deallocation and one allocation |
| memory per entry | key, value, two `Option<usize>`, map entry | key, value, `Rc` counts, `RefCell` flag, `Weak`, `Option<Rc>`, map entry, allocator header |
| drop | one `Vec` deallocation | one deallocation per entry |

## Limitations

**One workload, one machine.** The 1.81 ratio holds for this stream, this capacity,
and this processor. The report's range of 1.1 to 1.9 shows how much the answer depends
on the access pattern.

**Single-threaded only.** Neither cache is shared between threads. A concurrent
version would add a lock or sharding, as in chapter 41, and the lock would likely
dominate both figures.

**`V: Copy` narrows the contract.** A cache of `String` values cannot use this trait.
The restriction keeps the two implementations comparable and hides the cost that a
`Clone` on every hit would add.

**Clippy findings.** The trait has `len` without `is_empty` (`len_without_is_empty`),
and the eviction block in `rc_list::put` nests an `if let` inside an `if` that can be
collapsed into one condition (`collapsible_if`). Neither affects the measurement.

## Summary

- A shared trait and generic benchmark functions make two implementations comparable
  with identical measurement code.
- The `Rc<RefCell>` list pays for reference-count updates, `Weak` upgrades, run-time
  borrow checks, and an allocation per eviction; the arena pays for integer writes in
  one vector.
- A deterministic generator with locality gives both caches the same request stream,
  and comparing hit counts verifies that they behave identically.
- On ten million requests the arena was 1.81 times faster. The shared hash-map lookup
  bounds the ratio, which ranged from 1.1 to 1.9 across access patterns.

## References

- The repository's `BENCHMARKS.md` and `benchmarking_examples/benchmarking-report.pdf`,
  for the full procedure and the threats to validity.
- Standard library, [`std::rc::Weak`](https://doc.rust-lang.org/std/rc/struct.Weak.html) and [`std::cell::RefCell`](https://doc.rust-lang.org/std/cell/struct.RefCell.html).
- Donald E. Knuth, *The Art of Computer Programming*, Volume 2, 3rd edition,
  Addison-Wesley, 1997, Section 3.2.1, on linear congruential generators.
