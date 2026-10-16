//! A fixed-capacity LFU (Least Frequently Used) cache.
//!
//! ## Design
//!
//! Same arena idea as the LRU, but with one recency list per frequency:
//!
//! * `lookup_table: HashMap<K, usize>` — key → index into the arena.
//! * `nodes: Vec<Node>` — an **arena** of nodes; indices play the role of pointers.
//! * `buckets: HashMap<usize, Bucket>` — frequency → its own `head`/`tail` list.
//!
//! ```text
//!   freq 1:  head → … → tail
//!   freq 2:  head → … → tail
//!   ...
//! ```
//!
//! On eviction we take the `tail` of the `min_freq` bucket (least frequent,
//! then least recent) and **reuse its slot**, exactly like the LRU.

use std::collections::HashMap;
use std::hash::Hash;

/// A single cache entry, linked into its frequency bucket by index.
struct Node<K, V> {
    /// Retained so we can delete the corresponding map entry when evicting.
    key: K,
    value: V,
    /// How many times this entry has been accessed.
    freq: usize,
    /// Neighbour closer to the MRU end of the bucket.
    prev: Option<usize>,
    /// Neighbour closer to the LRU end of the bucket.
    next: Option<usize>,
}

/// The recency list for one frequency.
#[derive(Default)]
struct Bucket {
    head: Option<usize>,
    tail: Option<usize>,
}

/// Fixed-capacity LFU cache.
pub struct LfuCache<K, V> {
    /// Maximum number of entries; `>= 1` (enforced by `new`).
    cap: usize,
    /// Key → arena index.
    lookup_table: HashMap<K, usize>,
    /// Arena of nodes; indices are the "pointers" of the linked lists.
    nodes: Vec<Node<K, V>>,
    /// Frequency → recency list of nodes with that frequency.
    buckets: HashMap<usize, Bucket>,
    /// Lowest frequency currently present; its bucket's tail is evicted next.
    min_freq: usize,
}

impl<K: Hash + Eq + Clone, V> LfuCache<K, V> {
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
            buckets: HashMap::new(),
            min_freq: 0,
        }
    }

    /// Unlink node `i` from its bucket, dropping the bucket if it becomes empty.
    fn detach(&mut self, i: usize) {
        let Node { freq, prev, next, .. } = self.nodes[i];
        let Some(bucket) = self.buckets.get_mut(&freq) else {
            return;
        };

        match prev {
            Some(p) => self.nodes[p].next = next,
            None => bucket.head = next,
        }
        match next {
            Some(n) => self.nodes[n].prev = prev,
            None => bucket.tail = prev,
        }

        if bucket.head.is_none() {
            self.buckets.remove(&freq);
        }
    }

    /// Link node `i` in at the MRU end of its bucket. `i` must be unlinked.
    fn push_front(&mut self, i: usize) {
        let bucket = self.buckets.entry(self.nodes[i].freq).or_default();

        self.nodes[i].prev = None;
        self.nodes[i].next = bucket.head;
        match bucket.head {
            Some(h) => self.nodes[h].prev = Some(i),
            None => bucket.tail = Some(i), // bucket was empty
        }
        bucket.head = Some(i);
    }

    /// Move node `i` up to the next frequency bucket.
    fn bump(&mut self, i: usize) {
        let freq = self.nodes[i].freq;
        self.detach(i);

        // The lowest bucket just emptied, so the minimum moves up with this node.
        if self.min_freq == freq && !self.buckets.contains_key(&freq) {
            self.min_freq += 1;
        }

        self.nodes[i].freq += 1;
        self.push_front(i);
    }

    /// Look up `key`, bumping its frequency on a hit.
    ///
    /// Returns `None` if the key is not cached.
    pub fn get(&mut self, key: &K) -> Option<&V> {
        let i = *self.lookup_table.get(key)?;
        self.bump(i);
        Some(&self.nodes[i].value)
    }

    /// Insert or update `key`. Evicts the least frequently used entry
    /// (least recently used among ties) if the cache is full.
    pub fn put(&mut self, key: K, value: V) {
        // Case 1: key already present → update value, bump frequency.
        if let Some(&i) = self.lookup_table.get(&key) {
            self.nodes[i].value = value;
            self.bump(i);
            return;
        }

        let node = Node { key: key.clone(), value, freq: 1, prev: None, next: None };

        // Case 2: room to grow → append the fresh node.
        if self.nodes.len() < self.cap {
            let i = self.nodes.len();
            self.nodes.push(node);
            self.lookup_table.insert(key, i);
            self.push_front(i);
            self.min_freq = 1;
            return;
        }

        // Case 3: at capacity → reuse the LRU slot of the lowest-frequency bucket.
        if let Some(i) = self.buckets.get(&self.min_freq).and_then(|b| b.tail) {
            self.detach(i);
            let evicted = std::mem::replace(&mut self.nodes[i], node);
            self.lookup_table.remove(&evicted.key);
            self.lookup_table.insert(key, i);
            self.push_front(i);
            self.min_freq = 1;
        }
    }
}

fn main() {
    let mut cache = LfuCache::new(2);

    cache.put("a", 1);
    cache.put("b", 2);
    cache.get(&"a"); // a: freq 2
    cache.put("c", 3); // evicts b (lowest freq)
    cache.get(&"c"); // c: freq 2
    cache.put("d", 4); // a, c tie -> evicts a (least recent)

    assert_eq!(cache.get(&"a"), None);
    assert_eq!(cache.get(&"b"), None);
    assert_eq!(cache.get(&"c"), Some(&3));
    assert_eq!(cache.get(&"d"), Some(&4));

    cache.put("c", 30);
    println!("c = {:?}", cache.get(&"c")); // Some(30)
}

