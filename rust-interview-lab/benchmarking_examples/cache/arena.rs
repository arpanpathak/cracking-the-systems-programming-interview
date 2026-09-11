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
