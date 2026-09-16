# 42. Consistent Hashing {#consistent-hashing}

*Source file: [`src/problems/consistent_hash.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/consistent_hash.rs). Test it with `cargo test consistent_hash`.*

## Problem Statement

Map string keys to node names so that:

- the same key maps to the same node while the set of nodes is unchanged;
- adding a node moves only keys that the new node takes over;
- removing a node moves only the keys that node owned;
- keys spread roughly evenly across nodes.

## Designing a Solution

Consider `N = 3` backends and placement by `hash(key) % 3`. Adding a fourth backend
changes the divisor, and a key keeps its backend only when `hash % 3 == hash % 4`,
which holds for about one key in four. Three quarters of the cache misses at once.

A hash ring avoids the divisor. Every node is hashed to a point on the circle of
64-bit values, and every key is hashed to a point on the same circle. A key belongs to
the first node point clockwise from it. Adding a node inserts new points, and only the
keys between each new point and its predecessor change owner, all of them moving to
the new node.

One point per node gives uneven arcs. The implementation places each node at
`replicas` points, called virtual nodes, by hashing the node name together with the
replica number. With 128 replicas the arcs average out, and each node owns close to
its share of the circle.

The diagram below shows a ring with two nodes and two replicas each.

```text
0                                                                    2^64
|-----b#1------k------a#0------------a#1-------------b#0-------------|
               |       ^
               +-------+   k belongs to the first point after it: a#0, node a

a key after b#0 wraps around to the start and belongs to b#1, node b
```

The ring is stored as a vector of `(hash, node)` pairs sorted by hash. Lookup is a
binary search for the first point greater than the key's hash, wrapping to index 0
when the key's hash is beyond the last point.

## Implementation

<p class="listing"><span class="listing-label">Listing 42.1</span> <code>ConsistentHash</code>, <code>new</code>, and <code>add_node</code>. <code>src/problems/consistent_hash.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/consistent_hash.rs">read the file on GitHub</a></p>

The node name is stored as `Arc<str>`. With 128 replicas, a `String` per virtual node
would allocate 128 copies of the name. `Arc::from(node)` allocates once, and each
`Arc::clone` increments a count. `Arc<str>` is two words wide, a pointer and a length,
the same as `&str`.

`add_node` checks for an existing node with a linear scan over the ring, pushes
`replicas` new points, and re-sorts the vector. `sort_by_key` is a stable sort that
performs well on input that is already mostly sorted, which is the state after pushing
new points onto the end of a sorted vector.

`get` uses `partition_point(|(point, _)| *point <= hash)`, which returns the index of
the first element for which the predicate is false: the first point strictly greater
than the key's hash. When every point is less than or equal to the hash, the result is
`ring.len()`, and the next line wraps it to 0.

`virtual_node_hash` feeds the node name and the replica number into one hasher rather
than hashing a formatted string such as `"node-a#17"`. This avoids an allocation per
virtual node and produces a well-mixed hash of both values.

`DefaultHasher::new()` creates a hasher with fixed keys, unlike `RandomState`. The ring
therefore places nodes at the same points in every process, which is required when
several clients must agree on placement. The standard library does not promise that
`DefaultHasher` produces the same values across Rust releases, so clients built with
different compiler versions could disagree.

<p class="listing"><span class="listing-label">Listing 42.2</span> The tests for the module. <code>src/problems/consistent_hash.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/consistent_hash.rs">read the file on GitHub</a></p>

`adding_a_node_only_moves_keys_to_the_new_node` records the owner of 2,000 keys on a
two-node ring, adds a third node, and checks every key: either its owner is unchanged
or its new owner is `node-c`. That is the defining property of consistent hashing,
tested directly.

`keys_spread_across_nodes` requires each of three nodes to own more than 300 of 3,000
keys, a loose bound that catches a ring whose virtual nodes are not being used.

## Intuition

**Lookup on a small ring, with hashes shortened to two digits for readability**

| ring after sorting | key | key hash | `partition_point` result | owner |
|---|---|---|---|---|
| `[(12, b), (40, a), (71, b), (93, a)]` | `job-1` | 55 | 2, the first point > 55 is 71 | `b` |
| same | `job-2` | 12 | 1, the first point > 12 is 40 | `a` |
| same | `job-3` | 97 | 4 = `len`, wraps to 0 | `b` |

Adding node `c` with points `(60, c)` and `(20, c)` changes the ring to
`[(12, b), (20, c), (40, a), (60, c), (71, b), (93, a)]`. `job-1` at 55 now finds 60
and moves to `c`. `job-2` at 12 now finds 20 and moves to `c`. `job-3` at 97 still
wraps to `b`. No key moved from `a` to `b` or from `b` to `a`.

## Time and Space Complexity

`N` is the number of physical nodes, `R` the number of replicas, and `V = N · R` the
length of the ring.

| Operation | Time | Space |
|---|---|---|
| `add_node` | `O(V)` scan plus `O(V log V)` sort | `R` new entries |
| `remove_node` | `O(V)` | none |
| `get` | `O(log V)` for the search, plus hashing the key | none |
| `node_count` | `O(V)`, and it allocates a `HashSet` | `O(N)` |
| memory | `O(V)` entries of 24 bytes each, plus one name per node | |

When a node joins a ring of `N` nodes, about `1/(N + 1)` of the keys move.

## Limitations

**`DefaultHasher` is not a stable hash.** Its algorithm is unspecified and may change
between Rust releases. Two services that must agree on placement should use a hash
function with a published, fixed definition.

**No weights.** Every node receives the same number of virtual nodes. A backend with
twice the capacity needs twice the replicas, which the API cannot express.

**`add_node` is quadratic over many additions.** Adding `N` nodes one at a time sorts
the ring `N` times. Building the ring from a list of nodes and sorting once would be
`O(V log V)` in total.

**Hash collisions between virtual nodes are not handled.** If two virtual nodes hash to
the same point, `partition_point` always lands after both of them, so the one that
sorts first can never own a key. The effect is a slightly smaller share for its node.
With 64-bit hashes and a few thousand points the probability is negligible.

**`node_count` builds a `HashSet` on every call.** A field that counts physical nodes,
updated in `add_node` and `remove_node`, would make it `O(1)`.

## Summary

- Modulo placement moves most keys when the node count changes. A hash ring moves only
  the keys between a new node's points and their predecessors.
- Each physical node appears at `replicas` virtual points, which evens out the share of
  keys each node owns.
- A sorted `Vec<(u64, Arc<str>)>` with `partition_point` gives `O(log V)` lookup and
  wraps to index 0 past the last point.
- `Arc<str>` stores one copy of each node name, shared by all its virtual nodes.
- Placement must be computed with a hash whose definition is stable across processes
  and releases, which `DefaultHasher` does not guarantee.

## References

- David Karger, Eric Lehman, Tom Leighton, Matthew Levine, Daniel Lewin, and Rahul
  Panigrahy, "Consistent hashing and random trees", *Proceedings of the 29th ACM
  Symposium on Theory of Computing*, 1997.
- Giuseppe DeCandia et al., "Dynamo: Amazon's highly available key-value store",
  *Proceedings of the 21st ACM Symposium on Operating Systems Principles*, 2007.
- Standard library, [`slice::partition_point`](https://doc.rust-lang.org/std/primitive.slice.html#method.partition_point).
- Standard library, [`DefaultHasher`](https://doc.rust-lang.org/std/hash/struct.DefaultHasher.html), on its unspecified algorithm.
