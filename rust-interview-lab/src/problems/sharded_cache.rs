//! Sharded concurrent map to reduce lock contention.
//!
//! A single `Mutex<HashMap>` serializes every access. Splitting the map into N
//! shards, each with its own lock, lets independent keys proceed in parallel. The
//! cost is that `len` and `clear` must visit every shard, and there is no global
//! atomic snapshot.
//!
//! This is a common SDK/CLI cache shape: per-account token caches, node metadata
//! caches, and request de-duplication tables.

use std::collections::HashMap;
use std::collections::hash_map::RandomState;
use std::hash::{BuildHasher, Hash, Hasher};
use std::sync::Mutex;

/// A fixed-size map split across independently locked shards.
///
/// The shard count is rounded up to a power of two so the index is a mask instead
/// of a modulo.
pub struct ShardedCache<K, V> {
    shards: Vec<Mutex<HashMap<K, V>>>,
    hasher: RandomState,
    mask: usize,
}

impl<K, V> ShardedCache<K, V>
where
    K: Hash + Eq,
{
    /// Create a cache with at least `shard_count` shards (rounded to a power of two).
    pub fn new(shard_count: usize) -> Self {
        let shard_count = shard_count.max(1).next_power_of_two();
        
        let shards = (0..shard_count)
            .map(|_| Mutex::new(HashMap::new()))
            .collect();
        Self {
            shards,
            hasher: RandomState::new(),
            mask: shard_count - 1,
        }
    }

    fn shard(&self, key: &K) -> &Mutex<HashMap<K, V>> {
        let mut hasher = self.hasher.build_hasher();
        key.hash(&mut hasher);
        let index = (hasher.finish() as usize) & self.mask;
        &self.shards[index]
    }

    /// Insert a value, returning the previous one if the key was present.
    pub fn insert(&self, key: K, value: V) -> Option<V> {
        self.shard(&key)
            .lock()
            .expect("shard mutex poisoned")
            .insert(key, value)
    }

    /// Read a value by cloning it out of the shard.
    pub fn get(&self, key: &K) -> Option<V>
    where
        V: Clone,
    {
        self.shard(key)
            .lock()
            .expect("shard mutex poisoned")
            .get(key)
            .cloned()
    }

    /// Run `inspect` against the value under the shard lock, without cloning.
    ///
    /// Use this for read-modify-write on a single key; the closure holds the lock
    /// for its duration, so keep it short and do not call back into the cache.
    pub fn with<R>(&self, key: &K, inspect: impl FnOnce(Option<&V>) -> R) -> R {
        let guard = self.shard(key).lock().expect("shard mutex poisoned");
        inspect(guard.get(key))
    }

    pub fn remove(&self, key: &K) -> Option<V> {
        self.shard(key)
            .lock()
            .expect("shard mutex poisoned")
            .remove(key)
    }

    pub fn contains_key(&self, key: &K) -> bool {
        self.shard(key)
            .lock()
            .expect("shard mutex poisoned")
            .contains_key(key)
    }

    pub fn len(&self) -> usize {
        self.shards
            .iter()
            .map(|shard| shard.lock().expect("shard mutex poisoned").len())
            .sum()
    }

    pub fn is_empty(&self) -> bool {
        self.len() == 0
    }

    pub fn clear(&self) {
        for shard in &self.shards {
            shard.lock().expect("shard mutex poisoned").clear();
        }
    }

    pub fn shard_count(&self) -> usize {
        self.shards.len()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;
    use std::thread;

    #[test]
    fn insert_get_remove() {
        let cache: ShardedCache<String, u32> = ShardedCache::new(4);
        assert_eq!(cache.insert("gpu-a100".into(), 8), None);
        assert_eq!(cache.get(&"gpu-a100".into()), Some(8));
        assert_eq!(cache.insert("gpu-a100".into(), 16), Some(8));
        assert_eq!(cache.get(&"gpu-a100".into()), Some(16));
        assert_eq!(cache.remove(&"gpu-a100".into()), Some(16));
        assert!(!cache.contains_key(&"gpu-a100".into()));
        assert!(cache.is_empty());
    }

    #[test]
    fn with_exposes_the_value_without_cloning() {
        let cache: ShardedCache<&str, String> = ShardedCache::new(2);
        cache.insert("node", "A100".to_string());
        let observed = cache.with(&"node", |value| value.map(|v| v.len()));
        assert_eq!(observed, Some(4));
    }

    #[test]
    fn concurrent_writers_all_land() {
        let cache = Arc::new(ShardedCache::new(16));
        let mut handles = Vec::new();

        for writer in 0..8 {
            let cache = Arc::clone(&cache);
            handles.push(thread::spawn(move || {
                for key in 0..500 {
                    cache.insert(format!("{writer}-{key}"), key);
                }
            }));
        }
        for handle in handles {
            handle.join().expect("writer panicked");
        }

        assert_eq!(cache.len(), 8 * 500);
    }

    #[test]
    fn keys_spread_across_shards() {
        let cache: ShardedCache<u32, u32> = ShardedCache::new(8);
        for key in 0..4_096 {
            cache.insert(key, key);
        }
        // Every shard should hold roughly 1/8 of the keys; assert none is starved.
        let smallest = cache
            .shards
            .iter()
            .map(|shard| shard.lock().expect("shard mutex poisoned").len())
            .min()
            .expect("at least one shard");
        assert!(smallest > 0, "at least one shard was empty");
    }
}
