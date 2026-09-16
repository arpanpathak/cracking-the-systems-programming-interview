# 65. Kruskal's Minimum Spanning Tree {#kruskal}

*Source file: [`src/bin/kruskals_algorithm.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/kruskals_algorithm.rs). Run it with
`cargo run --bin kruskals_algorithm`.*

## Problem Statement

Given an undirected graph on `n` vertices, presented as a list of weighted edges, return a
set of edges that connects every vertex and whose total weight is as small as possible.
The graph may contain edges in any order, and the answer has `n - 1` edges when the graph
is connected.

## Designing a Solution

The greedy rule is short enough to state in one line: sort the edges by weight and keep
each one that joins two vertices not already connected. The rule is correct because of the
cut property. For any way of splitting the vertices into two groups, the lightest edge
crossing the split belongs to some minimum spanning tree, and an edge rejected by the rule
is one whose endpoints already sit on the same side of every split made so far.

What the rule needs is a fast answer to one question: are these two vertices already
connected? A disjoint set, also called union-find, answers it. Each component is a tree of
vertices, each vertex points at a parent, and the root of the tree is the name of the
component. Two vertices are connected when they reach the same root.

Two refinements keep those trees flat. Path compression makes every vertex visited during
a lookup point straight at the root, so the next lookup on that path is one step. Union by
rank hangs the shorter tree under the taller one, so the height grows only when two trees
of equal height meet. Together they bring the amortised cost of a lookup down to the
inverse Ackermann function of `n`, which is below five for any graph that fits in memory.

`union` returns a `bool`, and that return value is what drives the main loop. It answers
"were these two vertices in different components", which is the question the greedy rule
asks, and it performs the merge in the same call, so the algorithm never has to ask twice.

## Implementation

```rust
use std::cmp::Ordering::{Equal, Greater, Less};

#[derive(Debug)]
struct Edge { u: usize, v: usize, w: u32 }

struct DisjointSet { parent: Vec<usize>, rank: Vec<usize> }

impl DisjointSet  {
    fn new(n: usize) -> Self {
        Self {
            parent: (0..n).collect(),
            rank: vec![0; n]
        }
    }

    fn find(&mut self, elem: usize) -> usize{
        if self.parent[elem] != elem {
            self.parent[elem] = self.find(self.parent[elem]);
        }

        self.parent[elem]
    }

    fn union(&mut self, x: usize, y: usize) -> bool {
        let (x, y) = (self.find(x), self.find(y));

        if x == y { return false;}
 
        // Note for self : Comparator requires a reference
        match self.rank[x].cmp(&self.rank[y]) {
            Less => self.parent[x] = y,
            Greater => self.parent[y] = x,
            Equal => {
                self.parent[x] = y;
                self.rank[y] += 1;
            } 
        }

        true
    }
}

fn kruskals(n: usize, mut edges: Vec<Edge>) -> Vec<Edge> {
    // Greedy algorothm, sort the edges by weight
    edges.sort_by_key(|e| e.w);

    let mut uf = DisjointSet::new(n);
    let mut mst = Vec::new();

    for edge in edges {
        if uf.union(edge.u, edge.v) {
            mst.push(edge);
        }
    }

    mst

}

fn main() {
     let edges = vec![
        Edge { u: 0, v: 1, w: 4 },
        Edge { u: 0, v: 2, w: 3 },
        Edge { u: 1, v: 2, w: 1 },
        Edge { u: 1, v: 3, w: 2 },
        Edge { u: 2, v: 3, w: 4 },
        Edge { u: 3, v: 4, w: 2 },
    ];

    let mst = kruskals(5, edges);
    let total: u32 = mst.iter().map(|e| e.w).sum();

    for e in &mst {
        println!("{} - {} ({})", e.u, e.v, e.w);
    }
    println!("total: {total}");
}
```

`DisjointSet::new` starts with every vertex as its own component. `(0..n).collect()` fills
`parent` so that vertex `i` is its own parent, and every rank starts at zero.

`find` walks to the root and rewrites the path on the way back out. The recursive call
returns the root, and the assignment `self.parent[elem] = self.find(self.parent[elem])`
stores it directly in the vertex being visited, so a chain of any length collapses into a
set of direct links to the root in a single traversal. Writing the compression as a loop
takes two passes, one to find the root and one to rewrite; the recursion gets both from the
way the call stack unwinds.

`union` looks up both roots first, and an equal pair means the edge would close a cycle, so
it returns `false` without touching anything. Otherwise the ranks decide the direction.
`self.rank[x].cmp(&self.rank[y])` compares them, and the comparison needs a reference
because `Ord::cmp` takes `&self` and `&Self`. The taller tree becomes the parent in the
`Less` and `Greater` arms, and neither rank changes, because hanging a shorter tree under a
taller one cannot make it taller. Only the `Equal` arm increments a rank, which is the one
case where the height genuinely grows.

`kruskals` sorts, then folds the edge list into the answer. `edges.sort_by_key(|e| e.w)` is
a stable sort, so edges of equal weight stay in the order they were given, and the tree
this function returns is reproducible for a given input rather than merely minimal. The
loop consumes `edges`, which is what allows `mst.push(edge)` to move the edge into the
result without cloning it.

## Intuition

The graph in `main` has five vertices and six edges. Sorted by weight, and with the state
of the disjoint set after each decision:

```text
edge        weight   roots        decision   components after
1 - 2         1      1, 2         keep       {0} {1,2} {3} {4}
1 - 3         2      2, 3         keep       {0} {1,2,3} {4}
3 - 4         2      2, 4         keep       {0} {1,2,3,4}
0 - 2         3      0, 2         keep       {0,1,2,3,4}
0 - 1         4      2, 2         skip       already connected
2 - 3         4      2, 2         skip       already connected
```

The two edges of weight 2 are considered in the order they appear in the input, which the
stable sort preserves. The program prints the four kept edges and their total:

```text
1 - 2 (1)
1 - 3 (2)
3 - 4 (2)
0 - 2 (3)
total: 8
```

Four edges for five vertices is the expected count. Each kept edge reduces the number of
components by exactly one, from `n` to one, so a connected graph always yields `n - 1`.

## Time and Space Complexity

| Resource | Cost | Condition |
|---|---|---|
| Sort | `O(E log E)` | dominates the whole algorithm |
| `find`, `union` | `O(α(n))` amortised | path compression and union by rank together; `α(n) < 5` in practice |
| Total time | `O(E log E)` | equivalently `O(E log V)`, since `E < V²` |
| Space | `O(V + E)` | two vectors of length `V`, plus the edge list and the result |
| Allocation | one per `Vec` | `sort_by_key` sorts in place and allocates only for large inputs |

Prim's algorithm is the other standard answer, and it costs `O(E log V)` with a binary
heap. Kruskal suits an edge list and a sparse graph; Prim suits an adjacency list and a
dense one.

## Limitations

**A disconnected graph returns a forest, and says nothing about it.** The loop keeps every
edge that joins two components, and when the graph falls into several pieces the result is
a minimum spanning forest with fewer than `n - 1` edges. Nothing in the signature reports
this, and a caller that needs a spanning tree has to check `mst.len() == n - 1` itself.

**Vertex indices are not validated.** `union(edge.u, edge.v)` indexes `parent` directly, so
an edge naming a vertex at or beyond `n` panics with an out-of-bounds access rather than
returning an error. A function taking untrusted input would check the bounds while sorting.

**`find` is recursive.** The depth is the height of the tree, which path compression and
union by rank hold at `O(log n)`, so the stack is safe for any realistic graph. It is still
recursion on data supplied by the caller, and an iterative two-pass version removes the
question entirely.

**The total can overflow.** Weights are `u32` and `main` sums them into a `u32`. A graph
with many heavy edges overflows, and in release mode that wraps silently. Summing into a
`u64` costs nothing here.

**There are no tests.** The example in `main` is checked by reading the output. A test that
asserts the total weight, and a second one on a disconnected graph, would pin both the
result and the forest behaviour described above.

## Summary

- Sorting the edges by weight and keeping each edge that joins two components yields a
  minimum spanning tree, by the cut property.
- A disjoint set answers "are these connected" in near-constant amortised time when it
  uses both path compression and union by rank.
- Returning `bool` from `union` merges the membership test and the merge into one call,
  which is exactly the question the greedy rule asks.
- The sort dominates the cost at `O(E log E)`; the disjoint set is effectively free.
- A disconnected graph yields a forest, and the function does not distinguish that case
  from a spanning tree.

## References

- Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, and Clifford Stein,
  *Introduction to Algorithms*, 4th edition, MIT Press, 2022, Chapter 21, on disjoint
  sets, and Section 23.2, on Kruskal's and Prim's algorithms.
- Robert E. Tarjan, "Efficiency of a Good But Not Linear Set Union Algorithm",
  *Journal of the ACM*, 22(2), 1975, for the inverse Ackermann bound.
- Standard library, [`Ord::cmp`](https://doc.rust-lang.org/std/cmp/trait.Ord.html#tymethod.cmp).
- Standard library, [`slice::sort_by_key`](https://doc.rust-lang.org/std/primitive.slice.html#method.sort_by_key).
