# 61. Dijkstra's Shortest Paths {#dijkstra}

*Source file: [`src/problems/graph_dijkstra.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/graph_dijkstra.rs). Test it with `cargo test graph_dijkstra`.*

## Problem Statement

Given a directed graph with non-negative edge weights and a start node, return the
length of the shortest path from the start to every node. A node that cannot be reached
has no distance.

As in chapter 60, the algorithm is written twice. The vector variant numbers the nodes
`0..n` and returns `Vec<Option<u32>>`, with `None` for an unreachable node. The map
variant accepts any node type that is `Copy + Eq + Hash + Ord` and returns a `HashMap`
that contains only the reachable nodes.

## Designing a Solution

BFS finds shortest paths when every edge has the same length, because it settles nodes
in order of hop count. Dijkstra's algorithm generalizes that order to weighted edges:
it always expands the unexpanded node with the smallest known distance. With
non-negative weights, no later path can make that node's distance smaller, so its
distance is final once it is expanded.

A priority queue supplies the smallest known distance in `O(log n)`. Rust's `BinaryHeap`
is a max-heap, so each entry is wrapped in `std::cmp::Reverse`, which inverts the
ordering and makes the smallest `(cost, node)` pair come out first.

`BinaryHeap` has no operation to lower the priority of an entry already in the heap.
Instead, a shorter distance pushes a second entry for the same node. The older entry
stays in the heap and is recognised as stale when it is popped, because its cost is
larger than the distance recorded for the node.

```text
the sample graph from chapter 60

A --1--> B --5--> D
|        |        ^
4        2        |
v        v        |
C ------------1---+

shortest distances from A: A 0, B 1, C 3 (via B), D 4 (via B and C)
```

## Implementation

```rust
//! Dijkstra's shortest paths with a binary min-heap.
//!
//! Two variants of the same algorithm:
//!
//! - `dijkstra_vec`: nodes are `usize` indices and distances are a
//!   `Vec<Option<u32>>`, where `None` means unreachable.
//! - `dijkstra`: nodes are any `Copy + Eq + Hash + Ord` type and distances are a
//!   `HashMap` containing only the reachable nodes.
//!
//! Edge weights must be non-negative, which `u32` guarantees. `BinaryHeap` is a
//! max-heap, so entries are wrapped in `Reverse` to pop the smallest cost first.
//! A node can be in the heap several times; an entry whose cost is larger than the
//! recorded distance is stale and skipped.

use crate::problems::graph_bfs::GraphAdjList;
use std::cmp::Reverse;
use std::collections::{BinaryHeap, HashMap};
use std::hash::Hash;

/// Shortest distances from `start_node` over an index-based adjacency list.
pub fn dijkstra_vec(graph: &[Vec<(usize, u32)>], start_node: usize) -> Vec<Option<u32>> {
    let mut distances = vec![None; graph.len()];
    let mut min_heap = BinaryHeap::from([Reverse((0, start_node))]);

    distances[start_node] = Some(0);

    while let Some(Reverse((current_cost, current_node))) = min_heap.pop() {
        // stale heap entry, a shorter path was already recorded
        if distances[current_node].is_some_and(|best| current_cost > best) {
            continue;
        }
        for &(neighbor, weight) in &graph[current_node] {
            let new_distance = current_cost + weight;
            if distances[neighbor].is_none_or(|best| new_distance < best) {
                distances[neighbor] = Some(new_distance);
                min_heap.push(Reverse((new_distance, neighbor)));
            }
        }
    }
    distances
}

/// Shortest distances from `start_node` over a `HashMap` adjacency list.
pub fn dijkstra<Node>(graph: &GraphAdjList<Node>, start_node: Node) -> HashMap<Node, u32>
where
    Node: Copy + Eq + Hash + Ord,
{
    let mut distances = HashMap::from([(start_node, 0)]);
    let mut min_heap = BinaryHeap::from([Reverse((0, start_node))]);

    while let Some(Reverse((current_cost, current_node))) = min_heap.pop() {
        // stale heap entry, a shorter path was already recorded
        if current_cost > distances[&current_node] {
            continue;
        }
        for &(neighbor, weight) in graph[&current_node] {
            let new_distance = current_cost + weight;
            if new_distance < *distances.get(&neighbor).unwrap_or(&u32::MAX) {
                distances.insert(neighbor, new_distance);
                min_heap.push(Reverse((new_distance, neighbor)));
            }
        }
    }
    distances
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A -> B (1), A -> C (4), B -> C (2), B -> D (5), C -> D (1)
    fn sample_vec() -> Vec<Vec<(usize, u32)>> {
        vec![
            vec![(1, 1), (2, 4)],
            vec![(2, 2), (3, 5)],
            vec![(3, 1)],
            vec![],
        ]
    }

    fn sample_map() -> HashMap<&'static str, &'static [(&'static str, u32)]> {
        HashMap::from([
            ("A", &[("B", 1), ("C", 4)][..]),
            ("B", &[("C", 2), ("D", 5)][..]),
            ("C", &[("D", 1)][..]),
            ("D", &[][..]),
        ])
    }

    #[test]
    fn vec_variant_finds_shorter_multi_hop_paths() {
        // A -> C directly costs 4, A -> B -> C costs 3; D is reached via C for 4.
        assert_eq!(
            dijkstra_vec(&sample_vec(), 0),
            vec![Some(0), Some(1), Some(3), Some(4)]
        );
    }

    #[test]
    fn vec_variant_marks_unreachable_nodes() {
        let graph = vec![vec![(1, 7)], vec![], vec![(0, 1)]];
        assert_eq!(dijkstra_vec(&graph, 0), vec![Some(0), Some(7), None]);
    }

    #[test]
    fn map_variant_finds_shorter_multi_hop_paths() {
        let distances = dijkstra(&sample_map(), "A");
        assert_eq!(
            distances,
            HashMap::from([("A", 0), ("B", 1), ("C", 3), ("D", 4)])
        );
    }

    #[test]
    fn map_variant_omits_unreachable_nodes() {
        let graph: HashMap<u8, &[(u8, u32)]> =
            HashMap::from([(0, &[(1, 2)][..]), (1, &[][..]), (2, &[(0, 1)][..])]);
        assert_eq!(dijkstra(&graph, 0), HashMap::from([(0, 0), (1, 2)]));
    }
}
```

`dijkstra_vec` stores distances as `Vec<Option<u32>>`, so "not reached yet" is `None`
rather than a sentinel. The relaxation test
`distances[neighbor].is_none_or(|best| new_distance < best)` accepts an edge when the
neighbor has no distance yet or when the new path is shorter. `Option::is_none_or` was
stabilised in Rust 1.82. The stale-entry test
`distances[current_node].is_some_and(|best| current_cost > best)` skips an entry whose
cost is larger than the distance already recorded.

The map variant, `dijkstra`, keeps the same logic with a `HashMap`. It uses
`*distances.get(&neighbor).unwrap_or(&u32::MAX)` as the current best, so a node without
an entry compares as infinitely far. `distances[&current_node]` cannot panic in the
stale-entry test, because a node is pushed onto the heap only after its distance is
inserted.

`Node: Ord` is required by the map variant because the heap orders `(cost, node)` tuples,
and tuples compare element by element: when two costs are equal, the nodes decide the
order. The vector variant gets that ordering for free from `usize`.

The tests cover the multi-hop case, where the direct edge `A -> C` of weight 4 loses to
`A -> B -> C` of weight 3, and a graph with an unreachable node in each variant.

## Intuition

```text
dijkstra_vec(sample, start = 0)

pop (cost, node)   stale?   relaxations                         distances [A, B, C, D]   heap after
 -                                                              [0, -, -, -]             [(0,0)]
(0, 0)             no       B: 1 < none, push; C: 4 < none, push [0, 1, 4, -]             [(1,1), (4,2)]
(1, 1)             no       C: 3 < 4, push; D: 6 < none, push    [0, 1, 3, 6]             [(3,2), (4,2), (6,3)]
(3, 2)             no       D: 4 < 6, push                       [0, 1, 3, 4]             [(4,2), (4,3), (6,3)]
(4, 2)             yes, 4 > 3, skip                              [0, 1, 3, 4]             [(4,3), (6,3)]
(4, 3)             no       D has no edges                       [0, 1, 3, 4]             [(6,3)]
(6, 3)             yes, 6 > 4, skip                              [0, 1, 3, 4]             []
```

The result is `[Some(0), Some(1), Some(3), Some(4)]`. Two of the six pops were stale
entries, one for `C` and one for `D`.

## Time and Space Complexity

| Resource | Cost | Condition |
|---|---|---|
| Time | `O((V + E) log E)` | each edge can push one heap entry, and each push and pop costs `O(log E)` |
| Space | `O(V + E)` | the distance table holds one entry per node, and the heap up to one entry per edge |
| Map variant | the same bounds, expected | `HashMap` operations are expected constant time |

Since `E` is at most `V²`, `log E` is at most `2 log V`, and the bound is usually written
`O((V + E) log V)`.

## Limitations

**Negative weights are not supported.** The algorithm relies on a node's distance being
final when it is expanded. The `u32` weight type rules out negative edges. A graph with
negative weights needs the Bellman-Ford algorithm.

**Distances can overflow.** `current_cost + weight` is a `u32` addition. A path whose
total exceeds `u32::MAX` panics in a debug build and wraps in a release build, which
could make a long path look short. `checked_add`, or `u64` distances, removes the risk.

**Paths are not returned.** The functions return distances only. Recording the
predecessor of each node when its distance improves, in a `Vec<Option<usize>>` or a
`HashMap<Node, Node>`, allows the path to be rebuilt by walking back from the target.

**The whole reachable graph is explored.** A search for one target can stop as soon as
that target is popped, because its distance is final at that point. Neither function
takes a target.

**A missing node panics.** As in chapter 60, an edge to an index outside the vector, or
to a node without its own map entry, panics on indexing.

## Summary

- Dijkstra's algorithm expands nodes in order of distance, which is final on expansion
  when every weight is non-negative.
- `BinaryHeap` is a max-heap; `Reverse((cost, node))` turns it into a min-heap.
- Instead of decreasing a key, the algorithm pushes a new entry and skips stale entries
  whose cost exceeds the recorded distance.
- The vector variant represents "unreachable" as `None` and uses `is_none_or` and
  `is_some_and` for the two tests; the map variant omits unreachable nodes.
- The cost is `O((V + E) log V)` time and `O(V + E)` space.

## References

- Edsger W. Dijkstra, "A note on two problems in connexion with graphs", *Numerische
  Mathematik* 1, 1959, pages 269–271.
- Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, and Clifford Stein,
  *Introduction to Algorithms*, 4th edition, MIT Press, 2022, Section 22.3,
  "Dijkstra's algorithm".
- Standard library, [`BinaryHeap`](https://doc.rust-lang.org/std/collections/struct.BinaryHeap.html), on using `Reverse` for a min-heap.
- Standard library, [`Option::is_none_or`](https://doc.rust-lang.org/std/option/enum.Option.html#method.is_none_or).
