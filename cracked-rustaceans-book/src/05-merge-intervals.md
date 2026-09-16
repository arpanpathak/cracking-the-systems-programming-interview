# 5. Merge Intervals {#merge-intervals}

*Source file: [`src/problems/merge_intervals.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/merge_intervals.rs). Test it with
`cargo test merge_intervals`.*

## Problem Statement

Given a list of closed intervals `[start, end]`, return the list of maximal intervals
covering exactly the same points. Overlapping intervals are merged, and so are
intervals that only touch: `(1, 4)` and `(4, 5)` become `(1, 5)`, because `4` belongs
to both. Half-open intervals would not merge.

## Designing a Solution

Sorting by start removes the need to compare intervals with each other. After the
sort, an interval can only overlap the most recent one in the output, so each interval
costs one comparison.

```text
input   (1, 3) (2, 6) (8, 10) (15, 18)     already sorted here

interval   merged so far         decision
(1, 3)     [(1, 3)]              the first interval is always pushed
(2, 6)     [(1, 6)]              2 <= 3, so extend the end to max(3, 6)
(8, 10)    [(1, 6), (8, 10)]     8 > 6, a gap, so push
(15, 18)   [..., (15, 18)]       15 > 10, a gap, so push
```

The end of the merged interval is the `max` of the two ends. With `(1, 10)` followed by
`(2, 3)`, assigning the incoming end would shrink the interval.

## Implementation

The file contains two functions. The first consumes the vector it is given; the second
borrows it.

<p class="listing"><span class="listing-label">Listing 5.1</span> <code>merge_intervals</code>, <code>merge_intervals2</code>, and <code>merges_overlapping_and_adjacent</code>, with their tests. <code>src/problems/merge_intervals.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/merge_intervals.rs">read the file on GitHub</a></p>

`sort_unstable_by_key` sorts by the start value and does not preserve the relative order
of intervals with equal starts. Intervals with equal starts are merged into one, so
their order cannot matter.

`for (start, end) in intervals` consumes the vector, which moves each pair out rather
than borrowing it. `for &(start, end) in &intervals` copies each pair out of the
borrowed vector. Since `(i32, i32)` is `Copy`, both loops work, and the difference is
only whether the caller keeps the vector.

`match merged.last_mut()` with a guard keeps the three cases flat: an overlap, an empty
output, and a gap. The last two share an arm because they share an action.

## Intuition

```text
input: [(15, 18), (2, 3), (1, 10), (1, 10)]

sorted by start: [(1, 10), (1, 10), (2, 3), (15, 18)]

interval   merged before   overlap?          merged after
(1, 10)    []              output is empty   [(1, 10)]
(1, 10)    [(1, 10)]       1 <= 10           [(1, 10)]          end stays max(10, 10)
(2, 3)     [(1, 10)]       2 <= 10           [(1, 10)]          end stays max(10, 3)
(15, 18)   [(1, 10)]       15 > 10           [(1, 10), (15, 18)]
```

## Time and Space Complexity

| Resource | Cost | Condition |
|---|---|---|
| Time | `O(n log n)` | the sort dominates; the sweep is `O(n)` |
| Space | `O(n)` | the output holds at most one interval per input |

The input vector is taken by value, so its allocation is available to the function; the
code still allocates a second vector for the output rather than sorting and merging in
place.

## Limitations

**The second function is unreferenced.** `merge_intervals2` is not exported from
`lib.rs`, and no test in the file calls it. Its only difference from
`merge_intervals` is the loop, which borrows the vector instead of consuming it. An
unused `pub fn` in a library is not a compiler warning, so the two functions coexist
without a signal that one of them is unused.

**There is no test for the borrow-based variant.** Even if the function is kept,
nothing checks that it agrees with the other one. The assertion
`assert_eq!(merge_intervals2(v.clone()), merge_intervals(v))` would cover it.

**The element type is `i32`.** The end of a merged interval is
`previous.1.max(end)`, so the function performs no arithmetic and cannot overflow. The
bound matters only in that a caller with larger times cannot use the function.

## Summary

- Sorting by start removes the need to compare intervals with one another: afterwards
  an interval can overlap only the most recent interval of the output, so the sweep
  costs one comparison per interval.
- The end of a merged interval is the `max` of the two ends. Assigning the incoming end
  would shrink an interval that contains the next one.
- The sort dominates the cost, `O(n log n)`, and the output holds at most one interval
  per input.
- The same sort-then-sweep shape answers the neighbouring questions, such as the
  largest gap and the maximum overlap, without a second pass.

## References

- Standard library, [`slice::sort_unstable_by_key`](https://doc.rust-lang.org/std/primitive.slice.html#method.sort_unstable_by_key).
- Standard library, [`Vec::last_mut`](https://doc.rust-lang.org/std/vec/struct.Vec.html#method.last_mut).
- Standard library, [`Ord::max`](https://doc.rust-lang.org/std/cmp/trait.Ord.html#method.max).
