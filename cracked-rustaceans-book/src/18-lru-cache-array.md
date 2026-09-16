# 18. LRU Cache, Array-Backed {#lru-cache-array}

*Source file: [`src/problems/lru_cache_easy.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/lru_cache_easy.rs). Test it with
`cargo test lru_cache_easy`.*

## Problem Statement

The same problem as the previous chapter, solved a second way: a fixed-capacity cache
that evicts the least recently used entry, with `get` and `put` in constant time.

## Designing a Solution

Keep the entries in a `Vec` and use the index as the pointer. The map goes from key to
index, and the arena is stitched into a doubly linked list by two fields on each node,
`prev` and `next`, with `head` at the most recently used end and `tail` at the least
recently used one.

```text
lookup_table: "A" -> 1, "C" -> 0
nodes:  index 0              index 1
        +--------------+     +--------------+
        | key "C"      |     | key "A"      |
        | value  30    |     | value  10    |
        | prev: None   |     | prev: Some(0)|
        | next: Some(1)|     | next: None   |
        +--------------+     +--------------+
           ^                     ^
         head                  tail
         most recently used    least recently used
```

An index needs no reference count and no borrow flag, so a node costs two integers more
than the entry itself and nothing else. The arena is dense and index-stable: when the
cache is full, the slot at the tail is overwritten rather than freed, so no node is
deallocated while the cache lives.

One method moves a node to the front, and it handles both cases in a single pass. A node
that is already linked is spliced out of its current position first; a brand new node has
no neighbours and is spliced in directly. That is what `touch` does.

## Implementation

````rust
//! A fixed-capacity LRU (Least Recently Used) cache.
//!
//! ## Design
//!
//! Two structures cooperate to give O(1) `get` and `put`:
//!
//! * `map: HashMap<K, usize>` — key → index into the arena.
//! * `nodes: Vec<Node<K, V>>` — an **arena** of nodes; indices play the role
//!   of pointers, sidestepping `Rc<RefCell<…>>` and its borrow-checker pain.
//!
//! The arena is stitched into a doubly linked list through `head`/`tail`:
//!
//! ```text
//!   MRU  →  head → … → tail  →  LRU
//! ```
//!
//! On eviction we **reuse the tail slot** instead of removing it, so no node
//! is ever deallocated mid-life. That keeps the arena dense and index-stable.

use std::collections::HashMap;
use std::hash::Hash;

/// A single cache entry, linked into the recency list by index.
struct Node<K, V> {
    /// Retained so we can delete the corresponding map entry when evicting.
    key: K,
    value: V,
    /// Neighbour closer to the MRU end (or `None` if this is `head`).
    prev: Option<usize>,
    /// Neighbour closer to the LRU end (or `None` if this is `tail`).
    next: Option<usize>,
}

/// Fixed-capacity LRU cache.
pub struct LruCache<K, V> {
    /// Maximum number of entries; `>= 1` (enforced by `new`).
    cap: usize,
    /// Key → arena index. The single source of truth for "is this key cached?".
    lookup_table: HashMap<K, usize>,
    /// Arena of nodes; indices are the "pointers" of the linked list.
    nodes: Vec<Node<K, V>>,
    /// Arena index of the most recently used entry.
    head: Option<usize>,
    /// Arena index of the least recently used entry (next to be evicted).
    tail: Option<usize>,
}

impl<K, V> LruCache<K, V>
where
    K: Hash + Eq + Clone,
{
    /// Create a cache holding at most `cap` entries.
    ///
    /// # Panics
    /// Panics if `cap == 0`, since a zero-capacity cache cannot store anything.
    pub fn new(cap: usize) -> Self {
        assert!(cap > 0, "capacity must be > 0");
        Self {
            cap,
            lookup_table: HashMap::new(),
            nodes: Vec::new(),
            head: None,
            tail: None,
        }
    }

    /// Promote node `i` to `head` (MRU).
    ///
    /// Handles both cases in one pass:
    /// * **Already linked** — detach from its current neighbours first.
    /// * **Brand new** — the node has `prev = next = None` and is not yet
    ///   referenced by `head`/`tail`, so the detach step is skipped.
    fn touch(&mut self, i: usize) {
        let (prev, next) = (self.nodes[i].prev, self.nodes[i].next);

        // A node is "linked" if any of its four references exist.
        let linked = prev.is_some()
            || next.is_some()
            || self.head == Some(i)
            || self.tail == Some(i);

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

    /// Look up `key`, promoting it to MRU on a hit.
    ///
    /// Returns `None` if the key is not cached.
    pub fn get(&mut self, key: &K) -> Option<&V> {
        let i = *self.lookup_table.get(key)?;
        self.touch(i);
        Some(&self.nodes[i].value)
    }

    /// Insert or update `key`. Promotes it to MRU. Evicts the LRU entry if
    /// the cache is full.
    pub fn put(&mut self, key: K, value: V) {
        // Case 1: key already present → update value, promote.
        if let Some(&i) = self.lookup_table.get(&key) {
            self.nodes[i].value = value;
            self.touch(i);
            return;
        }

        // Case 2: room to grow → append a fresh node.
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

        // Case 3: at capacity → reuse the LRU slot.
        // `tail` is guaranteed to be `Some` here because `cap >= 1` and the
        // arena is full, but we still handle `None` gracefully.
        if let Some(i) = self.tail {
            let old_key = std::mem::replace(&mut self.nodes[i].key, key);
            self.nodes[i].value = value;
            self.lookup_table.remove(&old_key);
            self.lookup_table.insert(self.nodes[i].key.clone(), i);
            self.touch(i);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn basic_eviction() {
        let mut c = LruCache::new(2);
        c.put("A", 1);
        c.put("B", 2);

        assert_eq!(c.get(&"A"), Some(&1)); // A is now MRU
        c.put("C", 3); // evicts B

        assert_eq!(c.get(&"B"), None);
        assert_eq!(c.get(&"A"), Some(&1));
        assert_eq!(c.get(&"C"), Some(&3));
    }

    #[test]
    fn updating_existing_key_keeps_it() {
        let mut c = LruCache::new(2);
        c.put("A", 1);
        c.put("B", 2);

        c.put("A", 100); // update A, A becomes MRU
        c.put("C", 3);   // evicts B

        assert_eq!(c.get(&"A"), Some(&100));
        assert_eq!(c.get(&"B"), None);
        assert_eq!(c.get(&"C"), Some(&3));
    }

    #[test]
    fn get_refreshes_recency() {
        let mut c = LruCache::new(2);
        c.put("A", 1);
        c.put("B", 2);

        assert_eq!(c.get(&"A"), Some(&1)); // A refreshed
        c.put("C", 3);                     // evicts B

        assert_eq!(c.get(&"B"), None);
        assert_eq!(c.get(&"A"), Some(&1));
    }

    #[test]
    fn capacity_one() {
        let mut c = LruCache::new(1);
        c.put("A", 1);
        c.put("B", 2); // evicts A

        assert_eq!(c.get(&"A"), None);
        assert_eq!(c.get(&"B"), Some(&2));
    }

    #[test]
    fn missing_key_returns_none() {
        let mut c: LruCache<&str, i32> = LruCache::new(2);
        assert_eq!(c.get(&"nope"), None);
    }

    #[test]
    #[should_panic(expected = "capacity must be > 0")]
    fn zero_capacity_panics() {
        let _: LruCache<&str, i32> = LruCache::new(0);
    }
}
````

`touch` reads the node's two links, decides whether the node is linked at all, and acts.
The `linked` test is what lets one method serve both callers. Without it, a brand new
node would be spliced out of a list it is not in, and `head` and `tail` would be
overwritten with `None`.

`get` takes `&mut self` because a hit reorders the list. The index comes from the lookup
table, `touch` promotes it, and the reference returned is into the arena.

`put` has three cases in order. An existing key takes the update path, which writes the
new value and promotes the slot. A key that is not present and a cache below capacity
appends a node. A full cache overwrites the tail slot, which removes the old key from the
lookup table in the same step. The `assert!` in `new` is what makes the third case safe
to write with `tail` assumed to be present.

The key is cloned once per insertion because it lives in two places: the node keeps it for
eviction, and the lookup table keeps it for search. The map cannot be keyed on a reference
into the arena, so one of the two copies has to be made.

## Intuition

```text
capacity 2, keys A B C

call              nodes                       lookup_table   head   tail
new(2)            []                          {}             None   None
put("A", 10)      [(A,10,-,-)]                {A:0}          0      0
put("B", 20)      [(A,10,-,1), (B,20,0,-)]    {A:0,B:1}      1      0
get(&"A")         touch 0: detach 0, attach 0
                  [(A,10,-,1), (B,20,0,-)]    {A:0,B:1}      0      1
put("C", 30)      at capacity, so the tail slot 1 is reused
                  detach 1, remove B from the table
                  nodes[1] = (C,30,-,-)
                  attach 1: nodes[1].next = 0, nodes[0].prev = Some(1)
                  [(A,10,1,-), (C,30,-,0)]    {A:0,C:1}      1      0
get(&"B")         the table has no entry for B             None
get(&"A")         touch 0                                   Some(10)
get(&"C")         touch 1                                   Some(30)
put("A", 99)      case 1: nodes[0].value = 99, touch 0
get(&"A")                                                  Some(99)
```

## Time and Space Complexity

| Operation | Time | Space |
|---|---|---|
| `get` | `O(1)` expected | none |
| `put` of an existing key | `O(1)` expected | none |
| `put` of a new key | `O(1)` expected | one slot, reused when the cache is full |
| memory | `O(capacity)` | one node per slot, never more |

`touch` performs a constant number of assignments in every case. There is no allocation,
no copying of values, and no recursion.

## Limitations

**The arena never shrinks.** Slots are reused, so the cache holds one `K` and one `V` per
slot for its whole life, including after those values have been replaced. That is what
bounds the memory, and it also means a cache created with a large capacity keeps that
memory after it becomes empty.

**A capacity of zero panics at construction.** `new` asserts `cap > 0`, so the panic
happens before any use and names the capacity, which is better than failing on the first
`put`. A caller that receives a capacity from a file still has to validate it or accept
the panic; a `Result` would report it as a value.

**`get` borrows the cache mutably, so the returned reference cannot be held across another
call.** `let v = cache.get(&k)` keeps `cache` borrowed while `v` is live, and `put` cannot
be called until `v` goes out of scope. A caller that needs to read a value and then store
something has to copy the value out first.

**There is no `len`, no `is_empty`, and no iteration.** The lookup table's length is the
entry count, and a caller outside the module cannot read it. A two-line accessor would
close the gap.

**The indexes are not checked.** Every method indexes `self.nodes[i]` directly. The
indexes come from the lookup table or from `head` and `tail`, which this module maintains,
so they are valid while the invariants hold. A mistake in `touch` would be an index panic
rather than a wrong answer.

**The tests do not exercise growth past the capacity with distinct keys.** They cover
eviction, update, refresh, capacity one, a missing key and a zero capacity. A test that
fills a cache of capacity three, evicts one entry, and then reads the other two would
check that the reused slot and the surviving links agree.

## Summary

- The nodes live in a `Vec` and the links are indices, so the cache holds one
  allocation rather than one per entry, and a node carries no reference count and no
  borrow flag.
- `attach` and `detach` maintain the list; every operation is a constant number of
  index writes, and a slot freed by eviction is reused rather than returned.
- Memory is bounded by the capacity, which is the property Chapter 17 does not have.
- The cost of the index representation is that nothing checks it: a stale index is a
  wrong entry rather than a compile error or a panic, so the invariants live in the
  code that maintains the links.

## References

- Standard library, [`Vec`](https://doc.rust-lang.org/std/vec/struct.Vec.html).
- Standard library, [`HashMap`](https://doc.rust-lang.org/std/collections/struct.HashMap.html).
- Standard library, [`std::mem::replace`](https://doc.rust-lang.org/std/mem/fn.replace.html).
- Standard library, [`Option::get_or_insert`](https://doc.rust-lang.org/std/option/enum.Option.html#method.get_or_insert).
