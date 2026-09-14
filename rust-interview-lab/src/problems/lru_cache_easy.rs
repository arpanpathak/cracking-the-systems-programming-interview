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

#[cfg(test)]
mod tests_for_lru {
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
