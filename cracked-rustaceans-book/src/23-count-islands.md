# 23. Counting Islands {#counting-islands}

*Source file: [`src/bin/count_islands.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/count_islands.rs). Run it with
`cargo run --bin count_islands`.*

## Problem Statement

Given a rectangular grid of cells, count the connected regions of a chosen value.
Two cells are connected when they share an edge, so a cell touches at most four
neighbours. The function is generic over the cell type, so the caller decides
whether land is `'1'`, `true`, `1u8`, or something else.

## Designing a Solution

Scan the grid and flood-fill each unvisited land cell. Counting the number of
flood-fills is the answer, because a flood-fill visits exactly one connected
region.

```text
grid                    count
1 1 0 0 0
1 1 0 0 0               scan finds (0,0), fills the four cells of the top-left block
0 0 1 0 0               scan finds (2,2), fills that single cell
0 0 0 1 1               scan finds (3,3), fills (3,3) and (3,4)
                        answer: 3

the fill order for the first region, breadth first
queue: [(0,0)]
pop (0,0), push (0,1) and (1,0)
pop (0,1), push (1,1)
pop (1,0), neighbours already visited
pop (1,1), neighbours already visited
```

A cell is marked when it enters the queue rather than when it leaves. Marking on
entry is what keeps a cell from being enqueued twice: two neighbours of the same
cell can both see it as unvisited if the mark happens later, and the queue then
holds duplicates and the work grows.

## Implementation

<p class="listing"><span class="listing-label">Listing 23.1</span> The complete program, with its tests. <code>src/bin/count_islands.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/count_islands.rs">read the file on GitHub</a></p>

The grid type is `&[&[T]]`: a slice of row slices. This accepts a fixed-size
array of slices (`&['1', '1', '0'][..]`) and a vector of vectors, and it requires
every row to have the same length. The code reads `grid[0].len()` as the column
count and assumes the rest of the rows match.

`count_islands<T: PartialEq>(grid: &[&[T]], land: T)` takes `land` by value. The
comparison `grid[r][c] == land` therefore needs `PartialEq<T>` for `T`, which the
single bound provides. The bound is minimal: nothing else about the cell type is
required.

The bounds test casts to `i32` before adding the delta:

```rust
let nr = cr as i32 + dr;
let nc = cc as i32 + dc;

if (0..rows as i32).contains(&nr) && (0..cols as i32).contains(&nc) {
```

A `usize` cannot represent `-1`, so a neighbour above or to the left of the origin
would wrap to a very large index rather than failing a range check. Signed
arithmetic makes the range test correct for all four directions in one expression.

The `bfs` closure takes `visited` as a parameter rather than capturing it mutably.
A closure that captured `visited` would hold a mutable borrow across the whole
outer loop, and the loop also reads `visited`. Passing the reference in makes the
borrow begin and end at the call.

The demonstration prints two lines, and the tests exercise the same two grids plus
four boundary cases.

## Intuition

```text
grid
row 0: 1 1 0 0 0
row 1: 1 1 0 0 0
row 2: 0 0 1 0 0
row 3: 0 0 0 1 1

scan reach  cell   is land  visited?  action
(0,0)       yes    no        count = 1, fill from (0,0)
                             visit (0,0), (1,0), (0,1), (1,1)
(0,1)       yes    yes       skip
(0,2)       no     -         skip
(0,3)       no     -         skip
(0,4)       no     -         skip
(1,0)       yes    yes       skip
(1,1)       yes    yes       skip
(2,2)       yes    no        count = 2, fill from (2,2), visiting one cell
(3,3)       yes    no        count = 3, fill from (3,3), visiting (3,3) and (3,4)

the run prints:  Islands: 3
                 Boolean islands: 2
```

## Time and Space Complexity

| Resource | Cost |
|---|---|
| Time | `O(rows × cols)`, each cell is visited once and each visit examines four neighbours |
| Space | `O(rows × cols)` for the visited set and the queue |

## Limitations

**The visited set is a hash set of coordinate pairs.** Each entry holds two
`usize` values plus the hash table's overhead: control bytes, a bucket array that
may be twice the entry count, and a random seed per set. A bitmap of one bit per
cell answers the same question in `rows × cols / 8` bytes and one shift per lookup.
For a 4096 × 4096 grid the hash set holds up to sixteen million entries, while the
bitmap holds two megabytes. That factor, roughly fifty to a hundred, depending on
load factor, is the difference between a large allocation and a small one, and the
file's own comment says only "O(rows * cols) for the visited set".

**The rows are assumed to be the same length.** `cols` is read from the first row
and used to bound every row. A ragged input does not panic on the bound check for
the shorter rows; it panics on `grid[ur][uc]` when a shorter row is indexed at a
column the first row had. A ragged grid is a malformed input, and the failure mode
is an index panic deep inside the fill.

**A very large connected region is held in the queue.** The BFS queue can hold a
frontier proportional to the region's size, so memory is bounded by the input area
in the worst case. A depth-first fill with an explicit stack has the same bound.

**The function is private to the binary.** `count_islands` is in `src/bin/`, so it
is not part of the library's API, and a second binary that wants it must copy it.
Moving it into `src/problems/` would export it with the rest of the problems.

**The cell type must be `PartialEq` and the land value is taken by value.** So
`count_islands` cannot accept a predicate, which would let a caller count something
other than strict equality, for example, a region of cells above a threshold. The
predicate version is the same code with `land` replaced by a closure.

## Summary

- A flood fill visits exactly one connected component, so the number of fills is
  the number of components.
- A cell is marked when it is enqueued rather than when it is dequeued. Without
  that, several neighbours can enqueue the same cell and the queue holds it more
  than once.
- The neighbour offsets use signed arithmetic, which is what prevents the fill from
  wrapping around the edge of the grid.
- The visited set is a hash set of coordinate pairs, so each entry holds two
  `usize` values plus the table's overhead. A bitmap of one bit per cell answers the
  same question in `rows × cols / 8` bytes: for a 4096 × 4096 grid the hash set
  holds up to sixteen million entries against two megabytes for the bitmap.
- The rows are assumed to be of equal length. A ragged grid does not fail the bound
  check on a short row; it panics on `grid[ur][uc]` when a short row is indexed at a
  column the first row had.
- The BFS queue holds a frontier proportional to the region being filled, so memory
  is bounded by the area of the input in the worst case. A depth-first fill with an
  explicit stack has the same bound.
- The function is private to its binary, and the cell type must be `PartialEq`,
  because the land value is taken by value and no predicate is accepted.

## References

- Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, and Clifford Stein,
  *Introduction to Algorithms*, 4th edition, MIT Press, 2022, Section 20.2,
  "Breadth-first search".
- Standard library, [`VecDeque`](https://doc.rust-lang.org/std/collections/struct.VecDeque.html).
- Standard library, [`std::ops::Range::contains`](https://doc.rust-lang.org/std/ops/struct.Range.html#method.contains).
