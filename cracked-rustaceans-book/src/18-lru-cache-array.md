# 18. LRU Cache, Array-Backed {#lru-cache-array}

*Source file: [`src/problems/lru_cache_easy.rs`](../../rust-interview-lab/src/problems/lru_cache_easy.rs). Test it with
`cargo test lru_cache_easy`.*

## Problem Statement

The same problem as the previous chapter, solved a second way: a fixed-capacity
cache that evicts the least recently used entry, with `get` and `put` in constant
time.

## Designing a Solution

Store the nodes in a `Vec` and link them by index. The recency order is a doubly
linked list of indices, with the most recently used node at one end. Because the
links are integers rather than pointers, the list can be rearranged while the
nodes stay where they are.

```text
map: "a" -> 2, "c" -> 0

nodes:  index 0              index 1              index 2
        +--------------+     +--------------+     +--------------+
        | key "c"      |     | key ""       |     | key "a"      |
        | val ...      |     | val ...      |     | val ...      |
        | prev: None   |     |              |     | prev: Some(0)|
        | next: Some(2)|     |              |     | next: None   |
        +--------------+     +--------------+     +--------------+
           ^                                          ^
         tail                                       head
         least recently used                        most recently used

get("a") moves node 2 to the front:

  detach 2   tail 0's next becomes None            the list is just node 0
  attach 2   node 2's prev becomes None
             node 2's next becomes the old head, 0
             node 0's prev becomes Some(2)
             head becomes 2
```

`detach` and `attach` are five assignments each and never touch the `nodes`
vector's layout, so `get` performs no allocation and no copying of values.

## Implementation

```rust
use std::collections::HashMap;
use std::hash::Hash;

struct Node<K, V> {
    key: K,
    val: V,
    prev: Option<usize>,
    next: Option<usize>,
}

pub struct LruCache<K, V> {
    nodes: Vec<Node<K, V>>,
    map: HashMap<K, usize>,
    head: Option<usize>, // MRU
    tail: Option<usize>, // LRU
    cap: usize,
}

impl<K: Hash + Eq + Clone, V> LruCache<K, V> {
    pub fn new(cap: usize) -> Self {
        Self { nodes: Vec::new(), map: HashMap::new(), head: None, tail: None, cap }
    }

    pub fn get(&mut self, key: &K) -> Option<&V> {
        let &i = self.map.get(key)?;
        self.bump(i);
        Some(&self.nodes[i].val)
    }

    pub fn put(&mut self, key: K, val: V) {
        if let Some(&i) = self.map.get(&key) {
            self.nodes[i].val = val;
            self.bump(i);
            return;
        }
        let node = Node { key: key.clone(), val, prev: None, next: None };
        let i = if self.map.len() == self.cap {
            let i = self.tail.unwrap();
            self.detach(i);
            self.map.remove(&self.nodes[i].key);
            self.nodes[i] = node;
            i
        } else {
            self.nodes.push(node);
            self.nodes.len() - 1
        };
        self.map.insert(key, i);
        self.attach(i);
    }

    fn bump(&mut self, i: usize) {
        self.detach(i);
        self.attach(i);
    }

    fn detach(&mut self, i: usize) {
        let (p, n) = (self.nodes[i].prev, self.nodes[i].next);
        match p {
            Some(p) => self.nodes[p].next = n,
            None => self.head = n,
        }
        match n {
            Some(n) => self.nodes[n].prev = p,
            None => self.tail = p,
        }
    }

    fn attach(&mut self, i: usize) {
        self.nodes[i].prev = None;
        self.nodes[i].next = self.head;
        if let Some(h) = self.head {
            self.nodes[h].prev = Some(i);
        }
        self.head = Some(i);
        self.tail.get_or_insert(i);
    }
}

fn main() {
    let mut c = LruCache::new(2);
    c.put(1, "a");
    c.put(2, "b");
    assert_eq!(c.get(&1), Some(&"a"));
    c.put(3, "c"); // evicts 2
    assert_eq!(c.get(&2), None);
    assert_eq!(c.get(&1), Some(&"a"));
    assert_eq!(c.get(&3), Some(&"c"));
    c.put(3, "cc"); // update existing key
    assert_eq!(c.get(&3), Some(&"cc"));
    println!("ok");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn lru_cache_evicts_the_least_recently_used_key() {
        let mut cache = LruCache::new(2);

        cache.put("a", 1);
        cache.put("b", 2);
        assert_eq!(cache.get(&"a"), Some(&1));

        cache.put("c", 3);

        assert_eq!(cache.get(&"b"), None, "b was the least recently used entry");
        assert_eq!(cache.get(&"a"), Some(&1));
        assert_eq!(cache.get(&"c"), Some(&3));
    }

    #[test]
    fn updating_a_key_does_not_evict_anything() {
        let mut cache = LruCache::new(2);

        cache.put("a", 1);
        cache.put("b", 2);
        cache.put("a", 10);

        assert_eq!(cache.get(&"a"), Some(&10));
        assert_eq!(cache.get(&"b"), Some(&2));
        assert_eq!(cache.map.len(), 2);
    }
}
```

The test module in the repository stores one entry and asserts nothing, so
`cargo test` reports a pass that checks no behaviour. This edition prints the two
tests above in its place. They cover the two behaviours the demonstration in
`main` relies on, and the second one reads the cache's private map, which a test
inside the module is allowed to do.

`put` overwrites the slot of the evicted node rather than pushing a new one:

```rust
let i = if self.map.len() == self.cap {
    let i = self.tail.unwrap();
    self.detach(i);
    self.map.remove(&self.nodes[i].key);
    self.nodes[i] = node;
    i
} else {
    self.nodes.push(node);
    self.nodes.len() - 1
};
```

When the cache is full, the tail index is reused: the node is unlinked, its key is
removed from the map (read out of the vector before the overwrite), and the new
node takes the slot. The vector never exceeds the capacity, so the cache's storage
is bounded by `capacity`, which is the property the previous chapter's design does
not have.

`get` returns `Option<&V>`, a reference into the vector, when the value is present.

`attach` uses `self.tail.get_or_insert(i)` to set the tail only when the list is
empty, which handles the first insertion without a separate branch.

## Intuition

```text
capacity 2

call              nodes                       map            head   tail
new               []                          {}             None   None
put(1, "a")       [(1,"a",-, -)]              {1:0}          Some(0) Some(0)
put(2, "b")       [(1,"a",-,1), (2,"b",0,-)]  {1:0,2:1}      Some(1) Some(0)
get(&1)           detach 0, attach 0
                  [(1,"a",-,1), (2,"b",0,-)]  {1:0,2:1}      Some(0) Some(1)
put(3, "c")       the map holds 2 entries and cap is 2, so the tail (1) is reused
                  detach 1
                  map.remove(&nodes[1].key) -> removes 2
                  nodes[1] = (3,"c",-, -)
                  attach 1: nodes[1].next = head = 0, nodes[0].prev = Some(1)
                  [(1,"a",1,-), (3,"c",-,0)]  {1:0,3:1}      Some(1) Some(0)
get(&2)           the map has no entry for 2            None
get(&1)           detach 0, attach 0
get(&3)           detach 1, attach 1
```

## Time and Space Complexity

| Operation | Time | Space |
|---|---|---|
| `get` | `O(1)` expected | none |
| `put` of an existing key | `O(1)` expected | none |
| `put` of a new key | `O(1)` expected | one slot, reused when the cache is full |
| memory | `O(capacity)` | one node per slot, never more |

The four `match` arms of `detach` and the four assignments of `attach` are the
whole of the list maintenance. No allocation, no copying of values, and no
recursion.

## Limitations

**`capacity == 0` panics on the first `put`.** The full case tests `self.map.len()
== self.cap`, which is true for an empty cache of capacity zero, and the next line
is `self.tail.unwrap()` on a `None`. The panic message names an `Option` rather
than the capacity. A guard in `new`, or a `Result`, would report what the caller
passed.

**`prev` and `next` fields are left stale after `detach`.** `detach` updates the
neighbours but not the removed node's own links. `attach` overwrites both, so the
stale values are never read on the paths that exist today. A future method that
detaches without re-attaching would read them.

**The nodes are never freed as the cache is used.** Reusing a slot is what bounds
the memory, and it also means the cache holds one `K` and one `V` per slot for the
lifetime of the cache, even when those values have been replaced. An evicted key
is dropped when the slot is overwritten, which is correct, and the slot itself
stays allocated.

**There is no `len`, no `is_empty`, and no iteration.** A caller that needs the
entry count reads the private map, which the tests do and outside code cannot.

**The indexes are not checked.** Every method indexes `self.nodes[i]` directly.
The indexes come from the map or from `head` and `tail`, which this module
maintains, so they are valid while the invariants hold. A mistake in the list
maintenance would be an index panic rather than a wrong answer, which is at least
loud.

**No test pins the recency order after a sequence of several operations.** The two
tests cover one eviction and one update. The invariant that the list is consistent
with its ends is not checked anywhere.

## Summary

- The two cache designs differ in what bounds them. This one bounds storage by the
  capacity and returns references; the design in Chapter 17 bounds storage by the
  number of accesses and clones values on every read.
- The links are indices because the nodes never move, and an index requires no
  reference count. That costs two words per node and makes an index meaningless
  without the vector that owns it.
- A capacity of zero panics on the first `put`, where the full case tests
  `map.len() == cap` and then unwraps a `None` `tail`. The panic message names an
  `Option` rather than the capacity.
- `detach` updates the neighbours but not the removed node's own links. `attach`
  overwrites both, so the stale values are not read on the paths that exist today.
- The nodes are never freed while the cache is in use. Reusing a slot bounds the
  memory, and it also holds one `K` and one `V` per slot for the lifetime of the
  cache, including after those values have been replaced.
- No test pins the recency order after a sequence of several operations; the two
  tests cover one eviction and one update.

## References

- Standard library, [`Vec`](https://doc.rust-lang.org/std/vec/struct.Vec.html).
- Standard library, [`Option::get_or_insert`](https://doc.rust-lang.org/std/option/enum.Option.html#method.get_or_insert).
- Standard library, [`HashMap::remove`](https://doc.rust-lang.org/std/collections/struct.HashMap.html#method.remove).
