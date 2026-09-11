//! LRU cache that is actually writable in an interview.
//!
//! Design: `HashMap<K, (V, generation)>` + `VecDeque<(K, generation)>`.
//!
//! Each access pushes a new `(key, generation)` event to the back. On eviction
//! we pop old events until we find the newest generation for a key, then remove
//! it. Stale events are skipped. This keeps amortized O(1) operations while
//! preserving true LRU semantics.

use std::collections::{HashMap, VecDeque};
use std::hash::Hash;

pub struct LruCache<K, V>
where
    K: Eq + Hash + Clone,
    V: Clone,
{
    capacity: usize,
    map: HashMap<K, (V, u64)>,
    recency: VecDeque<(K, u64)>,
    generation: u64,
}

impl<K, V> LruCache<K, V>
where
    K: Eq + Hash + Clone,
    V: Clone,
{
    pub fn new(capacity: usize) -> Self {
        assert!(capacity > 0, "LRU cache capacity must be > 0");
        Self {
            capacity,
            map: HashMap::new(),
            recency: VecDeque::new(),
            generation: 0,
        }
    }

    pub fn len(&self) -> usize {
        self.map.len()
    }

    pub fn is_empty(&self) -> bool {
        self.map.is_empty()
    }

    pub fn get(&mut self, key: &K) -> Option<V> {
        let (value, _) = self.map.get(key)?.clone();
        self.generation += 1;
        self.recency.push_back((key.clone(), self.generation));
        self.map
            .insert(key.clone(), (value.clone(), self.generation));
        Some(value)
    }

    pub fn put(&mut self, key: K, value: V) {
        self.generation += 1;
        let is_new = self
            .map
            .insert(key.clone(), (value, self.generation))
            .is_none();
        self.recency.push_back((key, self.generation));

        if is_new {
            self.evict_if_needed();
        }
    }

    fn evict_if_needed(&mut self) {
        while self.map.len() > self.capacity {
            let Some((key, generation)) = self.recency.pop_front() else {
                break;
            };

            match self.map.get(&key) {
                Some((_, current)) if *current == generation => {
                    self.map.remove(&key);
                    break;
                }
                _ => {}
            }
        }
    }
}



#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn put_get_and_len() {
        let mut cache = LruCache::new(2);
        cache.put("a".to_string(), 1);
        cache.put("b".to_string(), 2);

        assert_eq!(cache.len(), 2);
        assert_eq!(cache.get(&"a".to_string()), Some(1));
        assert_eq!(cache.get(&"missing".to_string()), None);
    }

    #[test]
    fn evicts_least_recently_used() {
        let mut cache = LruCache::new(2);
        cache.put("a".to_string(), 1);
        cache.put("b".to_string(), 2);
        cache.put("c".to_string(), 3);

        assert_eq!(cache.get(&"a".to_string()), None);
        assert_eq!(cache.get(&"b".to_string()), Some(2));
        assert_eq!(cache.get(&"c".to_string()), Some(3));
    }

    #[test]
    fn get_updates_recency() {
        let mut cache = LruCache::new(2);
        cache.put("a".to_string(), 1);
        cache.put("b".to_string(), 2);

        // Access "a" so it becomes most recently used.
        assert_eq!(cache.get(&"a".to_string()), Some(1));

        cache.put("c".to_string(), 3); // evicts "b"
        assert_eq!(cache.get(&"b".to_string()), None);
        assert_eq!(cache.get(&"a".to_string()), Some(1));
        assert_eq!(cache.get(&"c".to_string()), Some(3));
    }

    #[test]
    fn updating_existing_key_moves_it_to_mru() {
        let mut cache = LruCache::new(2);
        cache.put("a".to_string(), 1);
        cache.put("b".to_string(), 2);

        // Update "a"; it becomes MRU, so "b" should be evicted next.
        cache.put("a".to_string(), 10);
        cache.put("c".to_string(), 3);

        assert_eq!(cache.get(&"a".to_string()), Some(10));
        assert_eq!(cache.get(&"b".to_string()), None);
        assert_eq!(cache.get(&"c".to_string()), Some(3));
    }
}
