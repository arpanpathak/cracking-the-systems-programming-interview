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

<p class="listing"><span class="listing-label">Listing 41.1</span> <code>ShardedCache</code>, <code>new</code>, and <code>shard</code>. <code>src/problems/sharded_cache.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/sharded_cache.rs">read the file on GitHub</a></p>

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

<p class="listing"><span class="listing-label">Listing 41.2</span> The tests for the module. <code>src/problems/sharded_cache.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/sharded_cache.rs">read the file on GitHub</a></p>

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
