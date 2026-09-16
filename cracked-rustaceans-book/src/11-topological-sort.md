# 11. Topological Sort {#topological-sort}

*Source file: [`src/problems/graph_topology.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/graph_topology.rs). Test it with
`cargo test graph_topology`.*

## Problem Statement

Given a directed graph, produce an ordering of its vertices in which every edge points
forward. If the graph contains a cycle, no such ordering exists and the function
reports that instead.

```text
edges:  0 -> 1, 0 -> 2, 1 -> 3, 2 -> 3

  0 -----> 1
  |        |
  v        v
  2 -----> 3

valid orders: [0, 1, 2, 3], [0, 2, 1, 3]
```

## Designing a Solution

Kahn's algorithm. A vertex can be placed as soon as every vertex that must precede it
has been placed, so counting the number of unplaced predecessors, the in-degree, is
enough to decide when a vertex becomes available.

```text
in-degree of each vertex: 0:0   1:1   2:1   3:2
ready queue: [0]

take 0  ->  order [0]        in-degree 1:0, 2:0       queue [1, 2]
take 1  ->  order [0, 1]     in-degree 3:1            queue [2]
take 2  ->  order [0, 1, 2]  in-degree 3:0            queue [3]
take 3  ->  order [0, 1, 2, 3]                        queue []
```

Four vertices were placed out of four, so the graph is acyclic. If the loop ends with
fewer vertices placed than the graph holds, the unplaced vertices are exactly those on
or after a cycle: each vertex of a cycle waits for another vertex of the same cycle, so
none of them reaches in-degree zero. The cycle test is therefore one comparison at the
end, with no separate traversal.

## Implementation

<p class="listing"><span class="listing-label">Listing 11.1</span> The complete module, with its tests. <code>src/problems/graph_topology.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/graph_topology.rs">read the file on GitHub</a></p>

`vec![Vec::new(); num_nodes]` builds the adjacency list with one vector per vertex. The
inner vectors grow as edges are added, so the total allocation is proportional to the
edge count.

`queue` is seeded with every vertex whose in-degree is already zero. A `VecDeque` is
used because vertices arrive at the back and leave from the front: `pop_front` and
`push_back` are both constant time, and removing from the front of a `Vec` is linear.

`indegree[next] -= 1` runs once per edge leaving `node`, so the total work of the inner
loop across the whole algorithm is the edge count. That is what makes the cost
`O(V + E)`.

`(order.len() == num_nodes).then_some(order)` consumes `order` only when the comparison
is true. If the graph has a cycle, the partial order is dropped and the caller receives
`None`, so no caller can schedule a partial order by accident.

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

**An edge naming a vertex outside `0..num_nodes` panics.** `graph[from].push(to)` and
`indegree[to] += 1` index directly, so `topological_sort(2, &[(5, 0)])` panics with an
index-out-of-bounds whose message names a vector index rather than the offending edge.
A caller that reads a graph from a file must validate the vertex numbers first.

**`None` does not say which cycle was found.** A caller that wants to report the cycle
must run a depth-first search over the unplaced vertices. The information is available
inside the algorithm, since the unplaced vertices are exactly the ones the loop never
reached, but the return type discards it.

**The choice among valid orders is unspecified.** For the diamond graph both
`[0, 1, 2, 3]` and `[0, 2, 1, 3]` are correct, and which one is produced depends on the
order of the edges in the input and on the vertex numbering. The tests assert only the
properties that must hold, and a caller must not depend on a particular order.

**Duplicate edges are tolerated but not detected.** Two copies of `(0, 1)` add two to
the in-degree of vertex 1, and the same edge is relaxed twice, so the counts stay
consistent and the result is unaffected. Nothing reports the duplication.

## Summary

- A vertex can be placed as soon as every vertex that must precede it has been placed,
  so counting unplaced predecessors, the in-degree, is enough to decide when a vertex
  becomes available.
- The queue is a `VecDeque` because vertices arrive at the back and leave from the
  front, and each edge is relaxed exactly once, which is what gives `O(V + E)`.
- The cycle test is one comparison at the end. A vertex on or after a cycle never
  reaches in-degree zero, so a short order is proof that no order exists.
- `then_some` consumes the partial order when the graph has a cycle, so a caller
  cannot schedule a prefix by accident. Chapter 65 keeps the same algorithm with
  vertices named by string, and returns an empty vector instead.

## References

- Arthur B. Kahn, "Topological sorting of large networks", *Communications of the
  ACM* 5(11), 1962, pages 558–562.
- Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, and Clifford Stein,
  *Introduction to Algorithms*, 4th edition, MIT Press, 2022, Section 20.4,
  "Topological sort".
- Standard library, [`VecDeque`](https://doc.rust-lang.org/std/collections/struct.VecDeque.html).
- Standard library, [`bool::then_some`](https://doc.rust-lang.org/std/primitive.bool.html#method.then_some).
