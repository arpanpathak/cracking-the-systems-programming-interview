# 17. LRU Cache {#lru-cache}

*Source file: [`src/problems/lru_cache.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/lru_cache.rs). Test it with `cargo test lru_cache::`.*

## Problem Statement

A cache with a fixed capacity that evicts the least recently used entry. `get` and `put`
must be in expected `O(1)`, and a `get` must count as a use.

## Designing a Solution

The recency order is kept as a log of events. Every access appends `(key, generation)` to
a queue, where the generation counter increases on every access. A second map holds the
generation of each key's most recent access.

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

The first event whose generation matches its key's entry belongs to the least recently
used key. The queue is ordered by generation, and every live key's most recent event
appears exactly once, so the earliest match is the minimum.

An event whose generation does not match records an earlier access to a key that has
been used since. It carries no information about the current recency order and is
discarded.

## Implementation

<p class="listing"><span class="listing-label">Listing 17.1</span> The complete module, with its tests. <code>src/problems/lru_cache.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/lru_cache.rs">read the file on GitHub</a></p>

`get` clones the value out of the map, increments the generation, appends an event, and
writes the entry back with the new generation. The write-back is what keeps the map in
agreement with the log; without it, the event just appended would look stale.

`put` inserts first and evicts only when the key was new. An update cannot take the cache
over its capacity, so the eviction loop would be wasted work in that case.

`evict_if_needed` pops events until one matches. The `break` after a successful removal
ends the loop. `put` adds at most one entry, so the loop removes at most one.

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

**The event queue is not bounded by the capacity.** Every `get` and every `put` appends
one entry to `recency`, and entries are removed only during eviction. A cache that is
read far more often than it is written grows its queue without bound: with a capacity of
two and a million reads of one key, the queue holds a million events, and nothing in the
API releases them. The queue is proportional to the number of operations rather than to
the number of entries, so a long-lived read-heavy cache will exhaust memory. Chapter 18
shows a design whose storage is bounded by the capacity.

**`get` clones the value on every hit.** The signature returns `Option<V>` rather than
`Option<&V>`, so a cached value is copied out on every access. For a small integer that
is free; for a cached response body it is a memcpy per hit, and it also forces the
`V: Clone` bound on the type.

**`capacity == 0` panics.** `new` asserts `capacity > 0`, so a cache cannot be disabled by
configuration. A caller that receives a capacity from a file must validate it or accept
the panic.

**The `break` in the eviction loop is correct only because `put` adds at most one
entry.** If the function were reused where several entries could be over capacity, it
would leave some of them in place.

**A generation counter of `u64` wraps after 2^64 accesses.** The wrap is unreachable in
practice, about 584 years at a billion accesses per second, and its consequence would be
a misidentified stale event rather than memory unsafety.

## Summary

- Recency is kept as a log of `(key, generation)` events rather than as a list that is
  spliced on every access, and a map holds the current generation of each key.
- An event is stale when the map disagrees with it, so eviction pops events from the
  front until it finds one that is current. Each event is created once and removed
  once, which is what makes the amortised cost constant.
- The design trades memory for simplicity: the queue grows with the number of accesses
  since the last eviction, not with the number of entries.
- Chapters 18 and 40 answer the same problem with bounded memory, one by indices into a
  vector and the other by measurement of the two layouts.

## References

- Standard library, [`VecDeque`](https://doc.rust-lang.org/std/collections/struct.VecDeque.html).
- Standard library, [`HashMap`](https://doc.rust-lang.org/std/collections/struct.HashMap.html).
- Standard library, [`u64`](https://doc.rust-lang.org/std/primitive.u64.html).
