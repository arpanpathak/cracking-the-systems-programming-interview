# 11. Topological Sort {#topological-sort}

*Source files: [`src/problems/graph_topology.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/graph_topology.rs),
tested with `cargo test graph_topology`, and
[`src/bin/dependency_resolutiom.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/dependency_resolutiom.rs), run with
`cargo run --bin dependency_resolutiom`.*

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

### The variant that names vertices with strings

Dependency graphs rarely arrive as integers. A build system is handed package names, a
course catalogue is handed course codes, and a scheduler is handed job identifiers. Kahn's
algorithm does not change, but every vector indexed by a vertex becomes a hash map keyed by
a name, and that substitution has a price worth seeing in full.

*Source file: [`src/bin/dependency_resolutiom.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/dependency_resolutiom.rs). Run it with
`cargo run --bin dependency_resolutiom`.*

```rust
use std::collections::{HashMap, VecDeque};

#[derive(Clone)]
struct Course {
    name: String,
    depends_on: Vec<String>,
}

fn topo_sort(courses: &[Course]) -> Vec<String> {
    let mut adj: HashMap<String, Vec<String>> = HashMap::new();
    let mut indegree: HashMap<String, usize> = HashMap::new();

    for Course { name, depends_on } in courses {
        indegree.insert(name.clone(), depends_on.len());
        adj.entry(name.clone()).or_default();
        for dep in depends_on {
            adj.entry(dep.clone()).or_default().push(name.clone());
            indegree.entry(dep.clone()).or_insert(0);
        }
    }

    let mut queue: VecDeque<_> = indegree
        .iter()
        .filter(|&(_, deg)| *deg == 0)
        .map(|(name, _)| name.clone())
        .collect();

    let mut order = Vec::new();
    while let Some(node) = queue.pop_front() {
        for next in &adj[&node] {
            let d = indegree.get_mut(next).unwrap();
            *d -= 1;
            if *d == 0 {
                queue.push_back(next.clone());
            }
        }
        order.push(node);
    }
    
    if order.len() == indegree.len() { order } else { Vec::new() }
}

fn main() {
    let courses = vec![
        Course { name: "algos".into(), depends_on: vec!["datastructs".into()] },
        Course { name: "compilers".into(), depends_on: vec!["algos".into(), "os".into()] },
        Course { name: "os".into(), depends_on: vec!["datastructs".into()] },
    ];


    let coned2 = courses.clone();

    println!("{:?}", topo_sort(&courses));
}
```

The input is declared in the direction a person would write it. A `Course` names what it
depends on, so `depends_on.len()` is already the in-degree of that course and can be
inserted directly, where the index version increments a counter once per edge. The edges
themselves point the other way: `adj.entry(dep).or_default().push(name)` records that
finishing `dep` unblocks `name`, which is the direction the traversal needs.

Three calls in the build loop exist only to make sure no vertex is missing.
`adj.entry(name).or_default()` gives every course an adjacency entry, so the later
`&adj[&node]` cannot panic on a course with no dependents.
`indegree.entry(dep).or_insert(0)` registers a name that appears only as a dependency and
never as a `Course` of its own. In the example that name is `datastructs`, and without the
`or_insert` it would never appear in the in-degree map, never enter the queue, and nothing
would start. `or_insert` rather than `insert` is what keeps it from overwriting a count
already computed for a course that happens to be listed later.

The completeness test at the end compares against `indegree.len()` rather than
`courses.len()`, and the difference is exactly those dependency-only names. The map holds
every vertex the graph mentions; the slice holds only the ones somebody declared.

What the rewrite costs is visible in the number of `clone` calls. Every name is cloned into
the adjacency map, again into the in-degree map, again into the queue, and a `String` clone
is a heap allocation and a copy. A resolver that runs on a large graph interns the names
once, into a `HashMap<String, usize>` built at the edge of the system, and then runs the
index-based version printed above, where a vertex is a `usize` and a lookup is a bounds
check.

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

The string-keyed variant has the same asymptotic cost and a much larger constant. Each of
the `O(V + E)` steps hashes a `String` rather than indexing a vector, and the names are
cloned into the maps and the queue, so the allocation count grows with the graph instead of
staying at two vectors.

## Limitations

**The order changes between runs.** The initial queue is built by iterating `indegree`,
and a `HashMap` iterates in an order that depends on a seed randomised for each process. A
graph with a single root, like the one in `main`, hides this, because there is only one
vertex to start from. Adding a second independent course makes it visible:

```text
["datastructs", "ethics", "algos", "os", "compilers"]
["datastructs", "ethics", "algos", "os", "compilers"]
["ethics", "datastructs", "algos", "os", "compilers"]
["datastructs", "ethics", "algos", "os", "compilers"]
["ethics", "datastructs", "algos", "os", "compilers"]
```

Every one of those is a correct topological order, and a build system that printed a
different plan on each invocation would still be trusted less for it. Collecting the roots
into a vector and sorting them before the traversal makes the output reproducible, at a
cost of `O(V log V)`.

**A cycle and an empty graph give the same answer.** `topo_sort` returns `Vec::new()` when
the order is short, and an input with no courses also returns an empty vector, so the
caller cannot tell a refused graph from an empty one. The index-based version says it
properly with `Option`, and `(order.len() == indegree.len()).then_some(order)` is the same
change here.

**The unused clone in `main`.** `let coned2 = courses.clone();` duplicates the whole course
list and is never read, which the compiler reports as an unused variable. Removing it
removes an allocation per course.

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

## References

- Arthur B. Kahn, "Topological sorting of large networks", *Communications of the
  ACM* 5(11), 1962, pages 558–562.
- Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, and Clifford Stein,
  *Introduction to Algorithms*, 4th edition, MIT Press, 2022, Section 20.4,
  "Topological sort".
- Standard library, [`VecDeque`](https://doc.rust-lang.org/std/collections/struct.VecDeque.html).
- Standard library, [`bool::then_some`](https://doc.rust-lang.org/std/primitive.bool.html#method.then_some).
