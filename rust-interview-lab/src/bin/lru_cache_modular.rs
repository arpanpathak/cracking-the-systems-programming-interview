//! A fixed-capacity LRU (Least Recently Used) cache.
//!
//! ## Design
//!
//! Two structures cooperate to give O(1) `get` and `put`:
//!
//! * `lookup_table: HashMap<i32, usize>` — key → index into the arena.
//! * `nodes: Vec<Node>` — an **arena** of nodes; indices play the role
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

/// A single cache entry, linked into the recency list by index.
struct Node {
    /// Retained so we can delete the corresponding map entry when evicting.
    key: i32,
    value: i32,
    /// Neighbour closer to the MRU end (or `None` if this is `head`).
    prev: Option<usize>,
    /// Neighbour closer to the LRU end (or `None` if this is `tail`).
    next: Option<usize>,
}

/// Fixed-capacity LRU cache.
pub struct LruCache {
    /// Maximum number of entries; `>= 1` (enforced by `new`).
    cap: usize,
    /// Key → arena index. The single source of truth for "is this key cached?".
    lookup_table: HashMap<i32, usize>,
    /// Arena of nodes; indices are the "pointers" of the linked list.
    nodes: Vec<Node>,
    /// Arena index of the most recently used entry.
    head: Option<usize>,
    /// Arena index of the least recently used entry (next to be evicted).
    tail: Option<usize>,
}

impl LruCache {
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

    /// Unlink node `i` from the list. `i` must currently be linked.
    fn detach(&mut self, i: usize) {
        let (prev, next) = (self.nodes[i].prev, self.nodes[i].next);
        match prev {
            Some(p) => self.nodes[p].next = next,
            None => self.head = next,
        }
        match next {
            Some(n) => self.nodes[n].prev = prev,
            None => self.tail = prev,
        }
    }

    /// Link node `i` in at the MRU end. `i` must currently be unlinked.
    fn push_front(&mut self, i: usize) {
        self.nodes[i].prev = None;
        self.nodes[i].next = self.head;
        match self.head {
            Some(h) => self.nodes[h].prev = Some(i),
            None => self.tail = Some(i), // list was empty
        }
        self.head = Some(i);
    }

    /// Promote an already-linked node to MRU.
    fn promote_to_front(&mut self, i: usize) {
        if self.head == Some(i) {
            return; // already MRU
        }
        self.detach(i);
        self.push_front(i);
    }

    /// Look up `key`, promoting it to MRU on a hit.
    ///
    /// Returns `None` if the key is not cached.
    pub fn get(&mut self, key: i32) -> Option<i32> {
        let i = *self.lookup_table.get(&key)?;
        self.promote_to_front(i);
        Some(self.nodes[i].value)
    }

    /// Insert or update `key`. Promotes it to MRU. Evicts the LRU entry if
    /// the cache is full.
    pub fn put(&mut self, key: i32, value: i32) {
        // Case 1: key already present → update value, promote.
        if let Some(&i) = self.lookup_table.get(&key) {
            self.nodes[i].value = value;
            self.promote_to_front(i);
            return;
        }

        // Case 2: room to grow → append a fresh (unlinked) node.
        if self.nodes.len() < self.cap {
            let i = self.nodes.len();
            self.nodes.push(Node {
                key,
                value,
                prev: None,
                next: None,
            });
            self.lookup_table.insert(key, i);
            self.push_front(i);
            return;
        }

        // Case 3: at capacity → reuse the LRU slot.
        // `tail` is guaranteed to be `Some` here because `cap >= 1` and the
        // arena is full, but we still handle `None` gracefully.
        if let Some(i) = self.tail {
            // Swap the new key into the node and hand back the old one it held.
            let old_key = std::mem::replace(&mut self.nodes[i].key, key);
            self.nodes[i].value = value;
            self.lookup_table.remove(&old_key);
            self.lookup_table.insert(key, i);
            self.promote_to_front(i);
        }
    }
}

fn main() {
    let mut cache = LruCache::new(2);

    cache.put(1, 10);
    cache.put(2, 20);
    println!("get 1 = {:?}", cache.get(1)); // Some(10), 1 now MRU

    cache.put(3, 30); // evicts 2 (LRU)

    println!("get 2 = {:?}", cache.get(2)); // None
    println!("get 1 = {:?}", cache.get(1)); // Some(10)
    println!("get 3 = {:?}", cache.get(3)); // Some(30)

    cache.put(1, 99);
    println!("get 1 = {:?}", cache.get(1)); // Some(99)
}

#[cfg(test)]
mod tests_for_lru {
    use super::*;

    #[test]
    fn basic_eviction() {
        let mut c = LruCache::new(2);
        c.put(1, 10);
        c.put(2, 20);

        assert_eq!(c.get(1), Some(10)); // 1 is now MRU
        c.put(3, 30); // evicts 2

        assert_eq!(c.get(2), None);
        assert_eq!(c.get(1), Some(10));
        assert_eq!(c.get(3), Some(30));
    }

    #[test]
    fn updating_existing_key_keeps_it() {
        let mut c = LruCache::new(2);
        c.put(1, 10);
        c.put(2, 20);

        c.put(1, 100); // update 1, 1 becomes MRU
        c.put(3, 30);  // evicts 2

        assert_eq!(c.get(1), Some(100));
        assert_eq!(c.get(2), None);
        assert_eq!(c.get(3), Some(30));
    }

    #[test]
    fn get_refreshes_recency() {
        let mut c = LruCache::new(2);
        c.put(1, 10);
        c.put(2, 20);

        assert_eq!(c.get(1), Some(10)); // 1 refreshed
        c.put(3, 30);                   // evicts 2

        assert_eq!(c.get(2), None);
        assert_eq!(c.get(1), Some(10));
    }

    #[test]
    fn capacity_one() {
        let mut c = LruCache::new(1);
        c.put(1, 10);
        c.put(2, 20); // evicts 1

        assert_eq!(c.get(1), None);
        assert_eq!(c.get(2), Some(20));
    }

    #[test]
    fn missing_key_returns_none() {
        let mut c = LruCache::new(2);
        assert_eq!(c.get(42), None);
    }

    #[test]
    #[should_panic(expected = "capacity must be > 0")]
    fn zero_capacity_panics() {
        let _ = LruCache::new(0);
    }
}
