# 60. Graph Traversal: BFS and DFS {#graph-traversal}

*Source files: [`src/problems/graph_bfs.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/graph_bfs.rs) and [`src/problems/graph_dfs.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/graph_dfs.rs). Test them with `cargo test graph_bfs` and `cargo test graph_dfs`.*

## Problem Statement

Given a directed graph and a start node, return the nodes reachable from the start in
the order a traversal visits them, once in breadth-first order and once in depth-first
order. Each node must appear at most once, and the traversal must terminate on graphs
with cycles.

Each algorithm is written twice. The vector variant numbers the nodes `0..n` and stores
the graph as `Vec<Vec<(usize, u32)>>`. The map variant accepts any node type that is
`Copy + Eq + Hash`, such as `&str`, and stores the graph as a `HashMap` from a node to a
slice of `(neighbor, weight)` edges. The weights are unused by the traversals and are
kept so that the same graph can be passed to Dijkstra's algorithm in chapter 61.

## Designing a Solution

Both traversals keep a frontier of nodes still to explore and a visited set. They
differ only in the frontier.

```text
BFS: frontier is a queue (VecDeque)     DFS: frontier is a stack (Vec)
     pop_front, push_back                    pop, push

     explores all nodes at distance 1,       follows one path as deep as it goes,
     then all at distance 2, ...             then backtracks
```

The sample graph used in the tests:

```text
A --1--> B --5--> D
|        |        ^
4        2        |
v        v        |
C ------------1---+
(B -> C with weight 2, C -> D with weight 1)

vector variant: A = 0, B = 1, C = 2, D = 3
```

**When a node is marked visited differs between the two.** BFS marks a node when it is
enqueued. Every node enters the queue once, and the queue never holds a duplicate. The
iterative DFS marks a node when it is popped. A node can be pushed several times, once
by each neighbor that reaches it before it is explored, and the later copies are
skipped when they are popped. Marking on pop is what makes the order depth-first: a
node pushed recently is explored before an older copy of the same node.

**The vector variant is the one to write first.** With nodes as indices, the visited
set is a `Vec<bool>` indexed directly, with no hashing, and `graph[node]` is a bounds-
checked index into a vector. The map variant is the same algorithm with `HashSet`
membership and `HashMap` lookup, which is what a problem with named nodes needs.

## Implementation

```rust
//! Breadth-first search.
//!
//! Two variants of the same algorithm:
//!
//! - `bfs_vec`: nodes are `usize` indices and the graph is `Vec<Vec<(usize, u32)>>`,
//!   so `visited` is a plain `Vec<bool>`. This is the version to write first.
//! - `bfs`: nodes are any `Copy + Eq + Hash` type and the graph is a `HashMap`
//!   from a node to a slice of `(neighbor, weight)` edges.

use std::collections::{HashMap, HashSet, VecDeque};
use std::hash::Hash;

/// Adjacency list keyed by node: each node maps to its `(neighbor, weight)` edges.
pub type GraphAdjList<'a, Node> = HashMap<Node, &'a [(Node, u32)]>;

/// BFS over an index-based adjacency list. Returns nodes in visiting order.
pub fn bfs_vec(graph: &[Vec<(usize, u32)>], start_node: usize) -> Vec<usize> {
    let mut visited = vec![false; graph.len()];
    let mut queue = VecDeque::from([start_node]);
    let mut result = vec![];

    visited[start_node] = true;

    while let Some(current_node) = queue.pop_front() {
        result.push(current_node);
        for &(neighbor, _) in &graph[current_node] {
            if !visited[neighbor] {
                visited[neighbor] = true;
                queue.push_back(neighbor);
            }
        }
    }
    result
}

/// BFS over a `HashMap` adjacency list. Returns nodes in visiting order.
pub fn bfs<Node>(graph: &GraphAdjList<Node>, start_node: Node) -> Vec<Node>
where
    Node: Copy + Eq + Hash,
{
    let mut visited = HashSet::new();
    let mut queue = VecDeque::from([start_node]);
    let mut result = vec![];

    visited.insert(start_node);

    while let Some(current_node) = queue.pop_front() {
        result.push(current_node);
        // slice iter yields &(Node, u32); `&` destructures it
        for &(neighbor, _) in graph[&current_node] {
            if visited.insert(neighbor) {
                queue.push_back(neighbor);
            }
        }
    }
    result
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
    fn vec_variant_visits_level_by_level() {
        assert_eq!(bfs_vec(&sample_vec(), 0), vec![0, 1, 2, 3]);
    }

    #[test]
    fn vec_variant_skips_unreachable_nodes() {
        let graph = vec![vec![(1, 1)], vec![], vec![(0, 1)]];
        assert_eq!(bfs_vec(&graph, 0), vec![0, 1]);
    }

    #[test]
    fn vec_variant_handles_cycles() {
        let graph = vec![vec![(1, 1)], vec![(0, 1)]];
        assert_eq!(bfs_vec(&graph, 0), vec![0, 1]);
    }

    #[test]
    fn map_variant_visits_level_by_level() {
        assert_eq!(bfs(&sample_map(), "A"), vec!["A", "B", "C", "D"]);
    }

    #[test]
    fn both_variants_agree() {
        let names = ["A", "B", "C", "D"];
        let from_vec: Vec<&str> = bfs_vec(&sample_vec(), 0)
            .into_iter()
            .map(|index| names[index])
            .collect();
        assert_eq!(from_vec, bfs(&sample_map(), "A"));
    }
}
```

```rust
//! Iterative depth-first search with an explicit stack.
//!
//! Two variants of the same algorithm:
//!
//! - `dfs_vec`: nodes are `usize` indices and the graph is `Vec<Vec<(usize, u32)>>`.
//! - `dfs`: nodes are any `Copy + Eq + Hash` type and the graph is a `HashMap`.
//!
//! A node is marked visited when it is popped, not when it is pushed, so it may
//! sit on the stack more than once. Neighbors are pushed in order, which means the
//! last neighbor is explored first.

use crate::problems::graph_bfs::GraphAdjList;
use std::collections::HashSet;
use std::hash::Hash;

/// DFS over an index-based adjacency list. Returns nodes in visiting order.
pub fn dfs_vec(graph: &[Vec<(usize, u32)>], start_node: usize) -> Vec<usize> {
    let mut visited = vec![false; graph.len()];
    let mut stack = vec![start_node];
    let mut result = vec![];

    while let Some(current_node) = stack.pop() {
        if visited[current_node] {
            continue;
        }
        visited[current_node] = true;
        result.push(current_node);
        for &(neighbor, _) in &graph[current_node] {
            stack.push(neighbor);
        }
    }
    result
}

/// DFS over a `HashMap` adjacency list. Returns nodes in visiting order.
pub fn dfs<Node>(graph: &GraphAdjList<Node>, start_node: Node) -> Vec<Node>
where
    Node: Copy + Eq + Hash,
{
    let mut visited = HashSet::new();
    let mut stack = vec![start_node];
    let mut result = vec![];

    while let Some(current_node) = stack.pop() {
        if !visited.insert(current_node) {
            continue;
        }
        result.push(current_node);
        for &(neighbor, _) in graph[&current_node] {
            stack.push(neighbor);
        }
    }
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;

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
    fn vec_variant_explores_the_last_neighbor_first() {
        // Pop 0, push 1 and 2; pop 2, push 3; pop 3; pop 1.
        assert_eq!(dfs_vec(&sample_vec(), 0), vec![0, 2, 3, 1]);
    }

    #[test]
    fn vec_variant_handles_cycles() {
        let graph = vec![vec![(1, 1)], vec![(2, 1)], vec![(0, 1)]];
        assert_eq!(dfs_vec(&graph, 0), vec![0, 1, 2]);
    }

    #[test]
    fn map_variant_explores_the_last_neighbor_first() {
        assert_eq!(dfs(&sample_map(), "A"), vec!["A", "C", "D", "B"]);
    }

    #[test]
    fn both_variants_agree() {
        let names = ["A", "B", "C", "D"];
        let from_vec: Vec<&str> = dfs_vec(&sample_vec(), 0)
            .into_iter()
            .map(|index| names[index])
            .collect();
        assert_eq!(from_vec, dfs(&sample_map(), "A"));
    }
}
```

`bfs_vec` sets `visited[start_node] = true` before the loop and marks each neighbor as it
is enqueued, so the check `!visited[neighbor]` and the mark happen together. The map
variant does the same in one call: `visited.insert(neighbor)` returns `true` only when
the node was not already present, so the condition both tests and records membership.

`for &(neighbor, _) in &graph[current_node]` iterates over `&(usize, u32)` values, and the
pattern `&(neighbor, _)` copies the neighbor out and ignores the weight. In the map
variant, `graph[&current_node]` already yields a slice reference, `&[(Node, u32)]`, so
the loop iterates over it without another `&`.

`dfs_vec` pushes every neighbor, visited or not, and filters at pop time with
`if visited[current_node] { continue; }`. The map variant writes the same test as
`if !visited.insert(current_node) { continue; }`.

`GraphAdjList<'a, Node>` is `HashMap<Node, &'a [(Node, u32)]>`. The lifetime says the map
borrows its edge slices rather than owning them, which is why the tests build the graph
from slice literals such as `&[("B", 1), ("C", 4)][..]`. The `[..]` turns an array
reference into a slice reference, so every entry of the map has the same type. The alias
is defined in `graph_bfs.rs` and imported by the other two graph modules.

The `both_variants_agree` tests map the indices from the vector variant to names and
compare the result with the map variant, so the two implementations cannot drift apart.

## Intuition

```text
bfs_vec(sample, start = 0)

pop   queue after pushes        visited              result
 -    [0]                       {0}                  []
 0    [1, 2]                    {0, 1, 2}            [0]
 1    [2, 3]                    {0, 1, 2, 3}         [0, 1]      2 already visited
 2    [3]                       {0, 1, 2, 3}         [0, 1, 2]   3 already visited
 3    []                        {0, 1, 2, 3}         [0, 1, 2, 3]
```

```text
dfs_vec(sample, start = 0)

pop   visited before?   stack after pushes     result
 0    no                [1, 2]                 [0]
 2    no                [1, 3]                 [0, 2]
 3    no                [1]                    [0, 2, 3]
 1    no                [2, 3]                 [0, 2, 3, 1]
 3    yes, skip         [2]
 2    yes, skip         []
```

The tests `vec_variant_visits_level_by_level` and
`vec_variant_explores_the_last_neighbor_first` assert exactly these two orders, and the
map variants return `["A", "B", "C", "D"]` and `["A", "C", "D", "B"]`.

## Time and Space Complexity

| Resource | Cost | Condition |
|---|---|---|
| Time | `O(V + E)` | every reachable node is expanded once and each of its edges is examined once |
| Space, BFS | `O(V)` | the queue and the visited set each hold at most one entry per node |
| Space, DFS | `O(V + E)` | a node can be pushed once per incoming edge before it is popped |
| Map variant | the same bounds, expected | `HashSet` and `HashMap` operations are expected constant time |

The vector variant allocates `visited` for every node in the graph, reachable or not. The
map variant grows its set only as nodes are visited.

## Limitations

**A missing node panics.** `graph[current_node]` in the vector variant panics when an
edge names an index outside the vector, and `graph[&current_node]` in the map variant
panics when a neighbor has no entry of its own, even an empty one. The tests give every
node an entry. A graph read from input should be validated first, or the loop should use
`graph.get(node)` and treat a missing entry as a node with no edges.

**The DFS order is not the recursive order.** A recursive DFS visits the first neighbor
first. This iterative version pushes neighbors in order and pops the last one first, so
it visits `C` before `B`. Both are valid depth-first orders. Pushing the neighbors in
reverse, `for &(neighbor, _) in graph[node].iter().rev()`, reproduces the recursive order.

**The DFS stack can grow beyond `V`.** Marking on pop allows duplicates on the stack, up
to one entry per edge. Marking on push keeps the stack at `V` entries but no longer
produces a depth-first order in all cases.

**Only reachable nodes are returned.** To traverse a graph with several components, call
the function from every node that has not been visited yet, as chapter 23 does for grid
islands.

**The weights are carried but unused.** A traversal that only needs connectivity can
store `Vec<Vec<usize>>`, which halves the memory per edge.

## Summary

- BFS and DFS share one loop and differ only in the frontier: a `VecDeque` used as a queue
  or a `Vec` used as a stack.
- BFS marks a node when it enters the queue; this iterative DFS marks a node when it is
  popped, which allows duplicates on the stack and gives a depth-first order.
- The vector variant uses indices and a `Vec<bool>`; the map variant uses a `HashSet`,
  whose `insert` returns whether the node was new.
- Both run in `O(V + E)` time, and tests that compare the two variants keep them
  consistent.

## References

- Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, and Clifford Stein,
  *Introduction to Algorithms*, 4th edition, MIT Press, 2022, Sections 20.2,
  "Breadth-first search", and 20.3, "Depth-first search".
- Standard library, [`VecDeque`](https://doc.rust-lang.org/std/collections/struct.VecDeque.html).
- Standard library, [`HashSet::insert`](https://doc.rust-lang.org/std/collections/struct.HashSet.html#method.insert), on its return value.
