# 41. A Sharded Concurrent Cache {#sharded-cache}

*Source file: [`src/problems/sharded_cache.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/sharded_cache.rs). Test it with `cargo test sharded_cache`.*

## Problem Statement

Build a map from `K` to `V` that many threads can read and write concurrently. Two
operations on different keys should usually not block each other. The map needs
`insert`, `get`, `remove`, `contains_key`, `len`, `is_empty`, `clear`, and a way to
inspect a value without cloning it.

## Designing a Solution

Allocate `N` independent `Mutex<HashMap<K, V>>` values. To find a key's shard, hash the
key and take the hash modulo `N`. Operations on keys in different shards take
different locks and proceed in parallel. The diagram below shows the layout for four shards.

```text
                    hash(key) & mask
                           |
        +----------+-------+--+----------+
        v          v          v          v
   +---------+ +---------+ +---------+ +---------+
   | Mutex   | | Mutex   | | Mutex   | | Mutex   |
   | HashMap | | HashMap | | HashMap | | HashMap |
   +---------+ +---------+ +---------+ +---------+
    shard 0     shard 1     shard 2     shard 3
```

If `N` is a power of two, `hash % N` equals `hash & (N - 1)`, and the mask is cheaper
than a division. The constructor therefore rounds the requested shard count up to a
power of two and stores the mask.

The hash that selects a shard must be the same for a key every time. The cache keeps
one `RandomState`, created once, and builds a hasher from it for each lookup. A
`RandomState` holds random keys chosen at construction, so shard selection is stable
for the life of the cache and unpredictable to an outside party, which prevents a
client from choosing keys that all land in one shard.

Operations that touch one key lock one shard. Operations that touch every key, `len`
and `clear`, lock each shard in turn. They do not hold all the locks at once, so they
do not observe a single consistent state of the whole map.

## Implementation

```rust
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
```

`new` builds the shard vector with an iterator, `(0..shard_count).map(...).collect()`.
`Mutex<HashMap<K, V>>` is not `Clone`, so `vec![Mutex::new(HashMap::new()); n]` would
not compile; the iterator constructs each shard separately.

`shard` returns `&Mutex<HashMap<K, V>>` borrowed from `self`. The caller locks it, and
the guard lives only for the expression that uses it, so each public method holds its
lock for exactly one map operation.

`get` requires `V: Clone` through a `where` clause on the method rather than on the
`impl` block. A cache of values that are not `Clone` can still use every other method,
including `with`.

`with` takes a closure `FnOnce(Option<&V>) -> R` and calls it with a reference into the
map while the shard lock is held. The caller can read a large value, or compute
something small from it, without copying the value out. The documentation comment
states the two rules that make this safe to use: keep the closure short, because it
holds the lock, and do not call back into the cache from inside it, because a second
lock of the same shard on the same thread deadlocks.

`len` sums the shard lengths with an iterator. Each shard is locked, measured, and
unlocked before the next is locked.

```rust
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
```

`concurrent_writers_all_land` runs eight threads that insert 500 distinct keys each and
checks that the total is 4,000. A lost update would show as a smaller count.

`keys_spread_across_shards` inserts 4,096 keys into eight shards and asserts that no
shard is empty. The test module can read the private `shards` field because it is a
child module.

## Intuition

**Shard selection for a cache created with `new(6)`**

| step | value |
|---|---|
| `shard_count.max(1)` | 6 |
| `.next_power_of_two()` | 8 |
| `mask` | `8 - 1 = 7`, binary `0b111` |
| `hasher.finish()` for some key | for example `0x9f3a_52c1_0b7e_44d5` |
| `as usize & mask` | the low three bits, `0b101`, so shard 5 |

Two threads inserting `"gpu-a100"` and `"node-17"` lock shard 5 and, say, shard 2. The
two inserts do not wait for each other. Two threads inserting keys that both hash to
shard 5 serialize on that shard's lock, exactly as they would on a single global map.

## Time and Space Complexity

| Operation | Time | Locks taken |
|---|---|---|
| `insert`, `get`, `remove`, `contains_key`, `with` | `O(1)` expected, plus hashing the key | one shard |
| `len`, `is_empty` | `O(shards)` | every shard, one at a time |
| `clear` | `O(entries)` | every shard, one at a time |
| memory | `O(entries + shards)` | one `Mutex` and one `HashMap` header per shard |

With `S` shards and keys spread evenly, the chance that two concurrent single-key
operations need the same lock is about `1/S`.

## Limitations

**No cross-shard atomicity.** `len` can return a value the map never held, if one
thread inserts into shard 0 after `len` has counted it and another removes from shard
7 before `len` reaches it. A read-modify-write over two keys, such as moving a value
from one key to another, cannot be done atomically with this API.

**`get` then `insert` is not atomic either.** Two threads that both call `get`, see
`None`, and then `insert` will both insert. An `entry`-style method that performs the
check and the insert under one shard lock is the idiomatic addition.

**No eviction.** Despite its name, this is a concurrent map with no capacity. A
long-running process that caches without bound will grow without bound.

**`with` can deadlock its caller.** Calling any method of the same cache inside the
closure, for a key in the same shard, locks a `std::sync::Mutex` twice on one thread.
The standard mutex does not detect this, and the thread waits forever.

**Hot keys defeat sharding.** If most traffic targets one key, that key's shard is a
single global lock. Sharding spreads keys, not load.

**Hashing is written out by hand.** `shard` creates a hasher, feeds the key, and calls
`finish`. Since Rust 1.71, `BuildHasher::hash_one` does the same in one call,
`self.hasher.hash_one(key)`, and Clippy suggests it through `manual_hash_one`. The
constructor also contains a line with trailing whitespace after `let shard_count`,
which `rustfmt` removes.

**A poisoned shard panics every caller.** Each method uses `expect("shard mutex
poisoned")`. One panic while a shard is locked makes every later access to any key in
that shard panic as well. Chapter 22 describes the alternatives.

## Summary

- Splitting a map into `N` independently locked shards lets operations on different
  keys run in parallel while keeping the simplicity of a `Mutex`.
- Rounding `N` to a power of two turns `hash % N` into `hash & (N - 1)`.
- A single `RandomState` gives stable, unpredictable shard selection for the life of
  the cache.
- `with` exposes a reference under the lock without cloning, and must not call back
  into the cache.
- Whole-map operations visit shards one at a time and do not see a consistent
  snapshot, and check-then-insert sequences need an atomic `entry`-style method.

## References

- Standard library, [`std::collections::hash_map::RandomState`](https://doc.rust-lang.org/std/collections/hash_map/struct.RandomState.html).
- Standard library, [`BuildHasher::hash_one`](https://doc.rust-lang.org/std/hash/trait.BuildHasher.html#method.hash_one).
- The `dashmap` crate, [documentation](https://docs.rs/dashmap/latest/dashmap/), a production sharded map.
- Maurice Herlihy and Nir Shavit, *The Art of Multiprocessor Programming*, 2nd
  edition, Morgan Kaufmann, 2020, Chapter 32, "Concurrent Hashing and Natural
  Parallelism".
