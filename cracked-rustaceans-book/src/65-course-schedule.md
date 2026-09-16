# 65. Course Schedule and Dependency Resolution {#course-schedule}

*Source file: [`src/bin/dependency_resolutiom.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/dependency_resolutiom.rs). Run it with
`cargo run --bin dependency_resolutiom`.*

## Problem Statement

Given a set of courses, each with the names of the courses it depends on, produce an
order in which every course is taken after the courses it depends on. If the
dependencies contain a cycle, no such order exists.

The input differs from the one in Chapter 11 in two ways. A course is named by a
string rather than by an index, and the edges are given as the dependencies of each
course rather than as a list of pairs. A course may be named only as a dependency and
never declared on its own.

```text
courses:
  algos      depends on  datastructs
  compilers  depends on  algos, os
  os         depends on  datastructs

  datastructs ---> algos ------> compilers
        |                          ^
        +--------> os -------------+

a valid order: [datastructs, algos, os, compilers]
```

`datastructs` is declared nowhere in the list. It appears only on the right-hand side
of the other three, and the order still has to contain it.

## Designing a Solution

The algorithm is Kahn's, as in Chapter 11, and the difference is the keying. Instead of
two vectors indexed by vertex number, the program keeps two maps: `adj`, from a course
to the courses that depend on it, and `indegree`, from a course to the number of its
dependencies still unplaced.

Two entries are written for every declaration. A course that declares dependencies
receives `indegree` equal to the number of them. Each dependency receives an `adj`
entry naming the declaring course, and an `indegree` of zero if it has not been seen
before. The zero is written with `or_insert`, so a course that is later declared with
dependencies of its own overwrites it, and the result does not depend on the order in
which the declarations arrive.

The map keyed by name also decides what the program can return. A vertex number has a
natural range to compare against, while a name does not, so the count of placed
courses is compared with the number of distinct names the maps have seen, which is
`indegree.len()` rather than the length of the input.

## Implementation

<p class="listing"><span class="listing-label">Listing 65.1</span> The complete program. <code>src/bin/dependency_resolutiom.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/dependency_resolutiom.rs">read the file on GitHub</a></p>

`for Course { name, depends_on } in courses` destructures in the pattern position, so
the body works with the two fields directly and never mentions the binding for the
whole structure. The fields are borrowed, which is why each use of a name that has to
outlive the loop is written `name.clone()`.

`adj.entry(dep.clone()).or_default().push(name.clone())` is the line that inverts the
input. The declaration says that `name` depends on `dep`; the map records that `dep`
has `name` among its dependents, which is the direction the traversal needs.
`or_default` creates the empty vector on first use, so a dependency that has not been
seen becomes a key of `adj` at the moment it is first named.

`adj.entry(name.clone()).or_default()` is the line that keeps the traversal total. A
course with no dependents would otherwise never become a key of `adj`, and `&adj[&node]`
in the loop would panic on it. With the entry created at declaration time, every name
that can reach the queue is a key of both maps.

`indegree.entry(dep.clone()).or_insert(0)` records a dependency that is never declared,
which is how `datastructs` enters the maps at all. It is `or_insert` and not `insert`
so that a course already declared with its own dependencies keeps the count it was
given.

The queue is seeded by iterating `indegree` and collecting the names whose count is
zero. `indegree.get_mut(next).unwrap()` then decrements the count of each dependent as
its dependency is placed, and a count that reaches zero pushes the name onto the queue.
The `unwrap` is sound for the reason given above: a name in `adj[&node]` was written
into `indegree` by the same pass that wrote the edge.

`if order.len() == indegree.len() { order } else { Vec::new() }` is the cycle test. The
comparison is against the number of distinct names rather than the number of
declarations, because the maps hold the courses that were declared and the courses
that were only depended on.

## Intuition

```text
courses: algos <- datastructs
         compilers <- algos, os
         os <- datastructs

after the first pass:

  adj        datastructs -> [algos, os]   algos -> [compilers]
             os -> [compilers]            compilers -> []
  indegree   algos 1   compilers 2   os 1   datastructs 0

step  pop          order                                  indegree after
 1    datastructs  [datastructs]                          algos 0, os 0
 2    algos        [datastructs, algos]                   compilers 1
 3    os           [datastructs, algos, os]               compilers 0
 4    compilers    [datastructs, algos, os, compilers]    -

order.len() == 4 == indegree.len(), so the order is returned.

A cycle: a depends on b, b depends on a

  indegree   a 1   b 1

no name has a count of zero, the queue is seeded empty, the loop body never
runs, and order.len() == 0 != 2, so the result is the empty vector.
```

## Time and Space Complexity

| Resource | Cost |
|---|---|
| Time | `O((V + E) · L)`, where `L` bounds the length of a name: each vertex and each edge is handled once, and each handling hashes or clones a name |
| Space | `O((V + E) · L)`, the two maps, the queue, and the order, each holding owned names |

The bound of Chapter 11 is `O(V + E)` with no factor for the key, because an index is
compared in one instruction and copied in one word. Naming the vertices is what adds
the factor, and it buys an input that needs no numbering pass before it can be used.

## Limitations

**The empty vector is overloaded.** It is returned for a cycle and it is also the
correct answer for an empty input, so a caller cannot distinguish "no order exists"
from "nothing to order" without checking the input as well. Chapter 11 returns
`Option<Vec<usize>>` and does not have this ambiguity. `Option` or a dedicated error
would separate the two cases here at no cost to the algorithm.

**The order among ready courses is not reproducible.** The queue is seeded by iterating
a `HashMap`, whose iteration order depends on the hash seed chosen for the process, so
two runs on the same input can produce different valid orders. Chapter 11 seeds from a
range and is deterministic. A caller that needs a stable order must sort the ready set,
for example by collecting the zero-count names and sorting them before the loop.

**Every name is cloned several times.** A name is cloned once as a key of `indegree`,
once as a key of `adj`, once for each edge that mentions it, and once more when it is
pushed onto the queue. For short course names this is not measurable. For a build
graph with thousands of long target names, the same algorithm over a vector of indices
with one table from name to index avoids the copies, and the index-based form is
Chapter 11.

**A duplicate declaration silently replaces the first.** `indegree.insert` overwrites,
so a course declared twice keeps the count from the later declaration while the edges
from the earlier one remain in `adj`. The counts and the edges then disagree, and the
course may be left out of the order. Nothing reports the duplication.

## Summary

The algorithm of Chapter 11 does not change when the vertices are named: the in-degree
count, the ready queue and the comparison at the end are the same. What changes is the
cost of a vertex, which is a hash and a clone rather than an index, and what a caller
can be told when the graph does not admit an order. The index form is the one to reach
for when the vertices are already numbered, and this form is the one to reach for when
the input arrives as names, which is how dependency and prerequisite problems are
usually posed in an interview.

## References

- Arthur B. Kahn, "Topological sorting of large networks", *Communications of the
  ACM* 5(11), 1962, pages 558–562.
- Standard library, [`HashMap::entry`](https://doc.rust-lang.org/std/collections/struct.HashMap.html#method.entry)
  and [`Entry::or_insert`](https://doc.rust-lang.org/std/collections/hash_map/enum.Entry.html#method.or_insert).
- Standard library, [`VecDeque`](https://doc.rust-lang.org/std/collections/struct.VecDeque.html).
