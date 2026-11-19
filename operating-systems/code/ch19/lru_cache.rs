// ch19/lru_cache.rs: a fixed-capacity, generic LRU (Least Recently Used) cache.
//!
//! ## Design
//!
//! Two structures cooperate to give O(1) `get` and `put`:
//!
//! * `lookup_table: HashMap<K, usize>` — key → index into the arena.
//! * `nodes: Vec<Node<K, V>>` — an **arena** of nodes; indices play the role
//!   of pointers, sidestepping `Rc<RefCell<…>>` and its borrow-checker overhead.
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
use std::fmt::Display;
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

impl<K: Hash + Eq + Clone, V> LruCache<K, V> {
    /// Create a cache holding at most `cap` entries.
    ///
    /// # Panics
    /// Panics if `cap == 0`, since a zero-capacity cache cannot store anything.
    pub fn new(cap: usize) -> Self {
        assert!(cap > 0, "capacity must be > 0");
        Self {
            cap,
            lookup_table: HashMap::with_capacity(cap),
            nodes: Vec::with_capacity(cap),
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
    pub fn get(&mut self, key: &K) -> Option<&V> {
        let i = *self.lookup_table.get(key)?;
        self.promote_to_front(i);
        Some(&self.nodes[i].value)
    }

    /// Insert or update `key`. Promotes it to MRU. Evicts the LRU entry if
    /// the cache is full.
    pub fn put(&mut self, key: K, value: V) {
        // Case 1: key already present → update value, promote.
        if let Some(&i) = self.lookup_table.get(&key) {
            self.nodes[i].value = value;
            self.promote_to_front(i);
            return;
        }

        // Case 2: room to grow → append a fresh (unlinked) node.
        if self.nodes.len() < self.cap {
            let i = self.nodes.len();
            self.lookup_table.insert(key.clone(), i);
            self.nodes.push(Node {
                key,
                value,
                prev: None,
                next: None,
            });
            self.push_front(i);
            return;
        }

        // Case 3: at capacity → reuse the LRU slot.
        // `tail` is guaranteed to be `Some` here because `cap >= 1` and the
        // arena is full, but we still handle `None` gracefully.
        if let Some(i) = self.tail {
            // Drop the evicted key from the map while the node still holds it.
            self.lookup_table.remove(&self.nodes[i].key);
            // Unlink the slot, overwrite it with a fresh node, relink at MRU.
            self.detach(i);
            self.nodes[i] = Node {
                key: key.clone(),
                value,
                prev: None,
                next: None,
            };
            self.lookup_table.insert(key, i);
            self.push_front(i);
        }
    }
}

fn show<V: Display>(label: &str, value: Option<&V>) {
    match value {
        Some(found) => println!("{label}{found}"),
        None => println!("{label}miss"),
    }
}

fn main() {
    let mut cache = LruCache::new(2);

    cache.put(1, 10);
    cache.put(2, 20);
    show("get 1 -> ", cache.get(&1)); // 1 becomes most recent

    cache.put(3, 30); // evicts 2, the least recent
    show("get 2 -> ", cache.get(&2));
    show("get 3 -> ", cache.get(&3));

    cache.put(4, 40); // evicts 1
    show("get 1 -> ", cache.get(&1));
    show("get 4 -> ", cache.get(&4));

    // Works with any hashable key and any value type.
    let mut names: LruCache<String, Vec<u8>> = LruCache::new(1);
    names.put("a".to_string(), vec![1, 2, 3]);
    names.put("b".to_string(), vec![4]); // evicts "a"
    assert!(names.get(&"a".to_string()).is_none());
    assert_eq!(names.get(&"b".to_string()), Some(&vec![4]));
}

#[cfg(test)]
mod tests_for_lru {
    use super::*;

    #[test]
    fn basic_eviction() {
        let mut c = LruCache::new(2);
        c.put(1, 10);
        c.put(2, 20);

        assert_eq!(c.get(&1), Some(&10)); // 1 is now MRU
        c.put(3, 30); // evicts 2

        assert_eq!(c.get(&2), None);
        assert_eq!(c.get(&1), Some(&10));
        assert_eq!(c.get(&3), Some(&30));
    }

    #[test]
    fn updating_existing_key_keeps_it() {
        let mut c = LruCache::new(2);
        c.put(1, 10);
        c.put(2, 20);

        c.put(1, 100); // update 1, 1 becomes MRU
        c.put(3, 30); // evicts 2

        assert_eq!(c.get(&1), Some(&100));
        assert_eq!(c.get(&2), None);
        assert_eq!(c.get(&3), Some(&30));
    }

    #[test]
    fn get_refreshes_recency() {
        let mut c = LruCache::new(2);
        c.put(1, 10);
        c.put(2, 20);

        assert_eq!(c.get(&1), Some(&10)); // 1 refreshed
        c.put(3, 30); // evicts 2

        assert_eq!(c.get(&2), None);
        assert_eq!(c.get(&1), Some(&10));
    }

    #[test]
    fn capacity_one() {
        let mut c = LruCache::new(1);
        c.put(1, 10);
        c.put(2, 20); // evicts 1

        assert_eq!(c.get(&1), None);
        assert_eq!(c.get(&2), Some(&20));
    }

    #[test]
    fn missing_key_returns_none() {
        let mut c: LruCache<i32, i32> = LruCache::new(2);
        assert_eq!(c.get(&42), None);
    }

    #[test]
    fn non_copy_key_and_value() {
        let mut c: LruCache<String, String> = LruCache::new(2);
        c.put("a".into(), "alpha".into());
        c.put("b".into(), "beta".into());
        c.put("c".into(), "gamma".into()); // evicts "a"

        assert_eq!(c.get(&"a".to_string()), None);
        assert_eq!(c.get(&"b".to_string()).map(String::as_str), Some("beta"));
        assert_eq!(c.get(&"c".to_string()).map(String::as_str), Some("gamma"));
    }

    #[test]
    #[should_panic(expected = "capacity must be > 0")]
    fn zero_capacity_panics() {
        let _ = LruCache::<i32, i32>::new(0);
    }
}
