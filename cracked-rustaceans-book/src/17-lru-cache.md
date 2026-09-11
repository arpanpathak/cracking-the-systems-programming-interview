# 17. LRU Cache {#lru-cache}

*Source file: [`src/problems/lru_cache.rs`](../../rust-interview-lab/src/problems/lru_cache.rs). Test it with `cargo test lru_cache::`.*

## Problem Statement

A cache with a fixed capacity that evicts the least recently used entry. `get` and
`put` must be in expected `O(1)`, and a `get` must count as a use.

## Designing a Solution

The recency order is kept as a log of events. Every access appends `(key,
generation)` to a queue, where the generation counter increases on every access. A
second map holds the generation of each key's *most recent* access.

```text
access order: a, b, a, c          generation counter after each step: 1, 2, 3, 4

event queue             generations map      values map
+--------------+        +--------+           +--------+
| (a, 1) front |        | a -> 3 |           | a -> v |
| (b, 2)       |        | b -> 2 |           | b -> v |
| (a, 3)       |        | c -> 4 |           | c -> v |
| (c, 4) back  |        +--------+           +--------+
+--------------+

Which entry is least recently used? Scan the queue from the front:

  (a, 1)   stale: the map says a's generation is 3, not 1
  (b, 2)   current: the map says b's generation is 2, so b is the candidate
```

The first event whose generation matches its key's entry belongs to the least
recently used key. The queue is ordered by generation, and every live key's most
recent event appears exactly once, so the earliest match is the minimum.

An event whose generation does not match is a record of an earlier access to a key
that has been used since. It carries no information about the current recency order
and is discarded.

## Implementation

```rust
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
```

`get` clones the value out of the map, increments the generation, appends an event,
and writes the entry back with the new generation. The write-back is what makes
the generation map agree with the log; without it, the event just appended would
look stale.

`put` inserts first and then evicts only when the key was new. An update cannot
take the cache over its capacity, so the eviction loop would be wasted work in that
case.

`evict_if_needed` pops events until one matches. The `break` after a successful
removal ends the loop. Since `put` adds at most one entry, the loop removes at most
one, which is the reason the `break` is safe.

## Intuition

```text
capacity 2

call                    generation   map after                   queue after
new()                   0            {}                          []
put("a", 1)             1            {a: (1, 1)}                 [(a,1)]
put("b", 2)             2            {a: (1,1), b: (2,2)}        [(a,1), (b,2)]
get(&"a")               3            {a: (1,3), b: (2,2)}        [(a,1), (b,2), (a,3)]
put("c", 3)             4            {a: (1,3), b: (2,2),
                                      c: (3,4)}                   [(a,1), (b,2),
                                                                   (a,3), (c,4)]

eviction, because the map holds 3 entries and the capacity is 2:
  pop (a, 1)   the map says a's generation is 3, so this event is stale
  pop (b, 2)   the map says b's generation is 2, so b is the least recently used
               remove b, and the loop ends

result: {a: (1,3), c: (3,4)}
```

## Time and Space Complexity

| Resource | Cost | Condition |
|---|---|---|
| `get` | expected `O(1)`, plus one clone of the value | the hash function distributes keys evenly |
| `put` | expected `O(1)` amortised | the eviction scan pops events, each of which is removed once |
| Space | `O(entries)` for the map, and `O(accesses since the last eviction)` for the queue | see below |

## Limitations

**The event queue is not bounded by the capacity.** Every `get` and every `put`
appends one entry to `recency`, and entries are only removed during eviction. A
cache that is read far more often than it is written grows its queue without
bound: with a capacity of two and a million reads of one key, the queue holds a
million events, and nothing in the API releases them. The queue is therefore
proportional to the number of operations rather than to the number of entries, and
a long-lived read-heavy cache will exhaust memory. Chapter 18 shows a design whose
storage is bounded by the capacity.

**`get` clones the value on every hit.** The signature returns `Option<V>` rather
than `Option<&V>`, so a cached value is copied out on every access. For a small
integer that is free; for a cached response body it is a memcpy per hit, and it
also forces the `V: Clone` bound on the type.

**`capacity == 0` panics.** `new` asserts `capacity > 0`, so a cache cannot be
disabled by configuration. A caller that receives a capacity from a file must
either validate it or accept the panic.

**The `break` in the eviction loop makes the function correct only because `put`
adds at most one entry.** If the function were reused in a context where several
entries could be over capacity, it would leave some of them in place.

**A generation counter of `u64` wraps after 2^64 accesses.** The wrap is
unreachable in practice, at a billion accesses per second it takes about 584 years
, and the consequence of reaching it would be a misidentified stale event rather
than memory unsafety.

## Summary

- Two structures hold the state. The map holds values and the current generation
  of each key; the queue holds access events.
- The generation check identifies stale events. An event whose generation does not
  match the key's current entry records an access that a later operation has
  superseded.
- The queue is proportional to the number of operations rather than to the
  capacity. With a capacity of two and a million reads of one key, the queue holds
  a million events and nothing in the API releases them. Chapter 18 describes a
  design whose storage is bounded by the capacity.
- `get` returns `Option<V>` and therefore clones on every hit, which copies a
  cached value out of the map and forces the `V: Clone` bound. A signature of
  `Option<&V>` would avoid the copy and change what `get` can do with the map.
- A capacity of zero panics, because `new` asserts `capacity > 0`.

## References

- Standard library, [`VecDeque`](https://doc.rust-lang.org/std/collections/struct.VecDeque.html).
- Standard library, [`HashMap`](https://doc.rust-lang.org/std/collections/struct.HashMap.html).
- Standard library, [`u64`](https://doc.rust-lang.org/std/primitive.u64.html).
