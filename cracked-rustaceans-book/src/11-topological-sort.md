# 11. Topological Sort {#topological-sort}

*Source file: [`src/problems/graph_topology.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/graph_topology.rs). Test it with
`cargo test graph_topology`.*

## Problem Statement

Given a directed graph, produce an ordering of its vertices in which every edge
points forward. If the graph contains a cycle, no such ordering exists and the
function reports that instead.

```text
edges:  0 -> 1, 0 -> 2, 1 -> 3, 2 -> 3

  0 -----> 1
  |        |
  v        v
  2 -----> 3

valid orders: [0, 1, 2, 3], [0, 2, 1, 3]
```

## Designing a Solution

Kahn's algorithm. A vertex can be placed as soon as every vertex that must precede
it has been placed, so counting the number of unplaced predecessors, the
in-degree, is enough to decide when a vertex becomes available.

```text
in-degree of each vertex: 0:0   1:1   2:1   3:2
ready queue: [0]

take 0  ->  order [0]        in-degree 1:0, 2:0       queue [1, 2]
take 1  ->  order [0, 1]     in-degree 3:1            queue [2]
take 2  ->  order [0, 1, 2]  in-degree 3:0            queue [3]
take 3  ->  order [0, 1, 2, 3]                        queue []
```

Four vertices were placed out of four, so the graph is acyclic. If the loop ends
with fewer vertices placed than the graph holds, the vertices left in the queue
are empty and the unplaced vertices are exactly those that lie on or after a
cycle: each vertex of a cycle waits for another vertex of the same cycle, so none
of them ever reaches in-degree zero.

The check is therefore one comparison at the end, and the algorithm detects cycles
without a separate traversal.

## Implementation

```rust
//! Topological sort (Kahn's algorithm).
//!
//! Common in NVIDIA-style scheduling questions: prerequisite graphs, pipeline
//! stages, dependency ordering of GPU jobs.

use std::collections::VecDeque;

pub fn topological_sort(num_nodes: usize, edges: &[(usize, usize)]) -> Option<Vec<usize>> {
    let mut graph = vec![Vec::new(); num_nodes];
    let mut indegree = vec![0usize; num_nodes];

    for &(from, to) in edges {
        graph[from].push(to);
        indegree[to] += 1;
    }

    let mut queue: VecDeque<usize> = (0..num_nodes).filter(|&n| indegree[n] == 0).collect();
    let mut order = Vec::with_capacity(num_nodes);

    while let Some(node) = queue.pop_front() {
        order.push(node);

        for &next in &graph[node] {
            indegree[next] -= 1;
            if indegree[next] == 0 {
                queue.push_back(next);
            }
        }
    }

    (order.len() == num_nodes).then_some(order)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn returns_order_for_dag() {
        // 0 -> 1, 0 -> 2, 1 -> 3, 2 -> 3
        let edges = [(0, 1), (0, 2), (1, 3), (2, 3)];
        let order = topological_sort(4, &edges).expect("DAG has an order");
        assert_eq!(order.len(), 4);
        assert!(
            order.iter().position(|&n| n == 0).unwrap()
                < order.iter().position(|&n| n == 1).unwrap()
        );
        assert!(
            order.iter().position(|&n| n == 1).unwrap()
                < order.iter().position(|&n| n == 3).unwrap()
        );
    }

    #[test]
    fn detects_cycle() {
        // 0 -> 1 -> 0 is a cycle.
        let edges = [(0, 1), (1, 0)];
        assert_eq!(topological_sort(2, &edges), None);
    }

    #[test]
    fn disconnected_nodes_are_included() {
        let edges = [(0, 1)];
        let order = topological_sort(3, &edges).expect("DAG has an order");
        assert_eq!(order.len(), 3);
    }
}
```

`vec![Vec::new(); num_nodes]` builds the adjacency list with one vector per
vertex. The inner vectors grow as edges are added, so the total allocation is
proportional to the edge count.

`queue` is seeded with every vertex whose in-degree is already zero. A
`VecDeque` is used because vertices arrive at the back and leave from the front:
`pop_front` and `push_back` are both constant time, and a `Vec` removing from the
front would be linear.

`indegree[next] -= 1` runs once per edge leaving `node`, so the total work of the
inner loop across the whole algorithm is the edge count. That is what makes the
cost `O(V + E)` rather than something quadratic.

`(order.len() == num_nodes).then_some(order)` consumes `order` only when the
comparison is true. If the graph has a cycle, the partially built order is dropped
and the caller receives `None`, so no caller can accidentally schedule a partial
order.

## Intuition

```text
num_nodes = 4, edges = [(0, 1), (0, 2), (1, 3), (2, 3)]

adjacency: 0 -> [1, 2]     1 -> [3]     2 -> [3]     3 -> []
indegree: [0, 1, 1, 2]

step  queue      pop   order            in-degree after          queue after
 1    [0]        0     [0]              1:0, 2:0                 [1, 2]
 2    [1, 2]     1     [0, 1]           3:1                      [2]
 3    [2]        2     [0, 1, 2]        3:0                      [3]
 4    [3]        3     [0, 1, 2, 3]     -                        []

order.len() == 4 == num_nodes, so the result is Some(order).

A cycle: num_nodes = 2, edges = [(0, 1), (1, 0)]

indegree: [1, 1]
the queue is seeded empty, the loop body never runs, order has length 0,
and 0 != 2, so the result is None.
```

## Time and Space Complexity

| Resource | Cost |
|---|---|
| Time | `O(V + E)`, each vertex enters the queue once and each edge is relaxed once |
| Space | `O(V + E)`, the adjacency list and the two auxiliary vectors |

## Limitations

**An edge naming a vertex outside `0..num_nodes` panics.** `graph[from].push(to)`
and `indegree[to] += 1` index directly, so `topological_sort(2, &[(5, 0)])` panics
with an index-out-of-bounds, and the panic message names a vector index rather
than the offending edge. A caller that reads a graph from a file must validate the
vertex numbers first; the function gives it no help.

**`None` does not say which cycle was found.** A caller that wants to report the
cycle must run a depth-first search over the unplaced vertices to find one. The
information is available inside the algorithm, the unplaced vertices are exactly
the ones the loop never reached, but the return type discards it.

**The choice among valid orders is unspecified.** For the diamond graph both
`[0, 1, 2, 3]` and `[0, 2, 1, 3]` are correct, and which one comes out depends on
the order of the edges in the input and on the vertex numbering. The tests assert
only the properties that must hold, which is the correct way to test this
function, and a caller must not depend on a particular order.

**Duplicate edges are tolerated but not detected.** Two copies of `(0, 1)` add two
to the in-degree of vertex 1 and the same edge is relaxed twice, so the counts
stay consistent and the result is unaffected. Nothing reports the duplication,
which a caller might want to know about.

## Summary

- The invariant is that the in-degree array counts the unplaced predecessors of
  each vertex. The remainder of the algorithm follows from it.
- A short result is the cycle test. The unplaced vertices are exactly those the
  main loop never reached, so a count below `num_nodes` means those vertices
  carry a cycle.
- The cost is `O(V + E)`. The `E` term comes from the relaxation loop, which
  examines each edge once, rather than from a repeated scan of the edge list.
- An edge whose endpoints fall outside `0..num_nodes` panics with an
  index-out-of-bounds whose message names the vector index rather than the edge. A
  caller reading a graph from a file must validate the vertex numbers before
  calling the function.

## References

- Arthur B. Kahn, "Topological sorting of large networks", *Communications of the
  ACM* 5(11), 1962, pages 558–562.
- Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, and Clifford Stein,
  *Introduction to Algorithms*, 4th edition, MIT Press, 2022, Section 20.4,
  "Topological sort".
- Standard library, [`VecDeque`](https://doc.rust-lang.org/std/collections/struct.VecDeque.html).
- Standard library, [`bool::then_some`](https://doc.rust-lang.org/std/primitive.bool.html#method.then_some).
