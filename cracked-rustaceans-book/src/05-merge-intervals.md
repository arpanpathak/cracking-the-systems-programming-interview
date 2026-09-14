# 5. Merge Intervals {#merge-intervals}

*Source file: [`src/problems/merge_intervals.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/merge_intervals.rs). Test it with
`cargo test merge_intervals`.*

## Problem Statement

Given a list of closed intervals `[start, end]`, return the list of maximal
intervals covering exactly the same points. Overlapping intervals are merged, and
so are intervals that only touch: `(1, 4)` and `(4, 5)` become `(1, 5)`, because
`4` belongs to both. Whether touching intervals merge is the first property to
fix, since half-open intervals would not merge.

## Designing a Solution

Sorting by start removes the need to compare intervals with each other. After the
sort, an interval can only overlap the most recent one in the output, so each
interval costs one comparison.

```text
input   (1, 3) (2, 6) (8, 10) (15, 18)     already sorted here

interval   merged so far         decision
(1, 3)     [(1, 3)]              the first interval is always pushed
(2, 6)     [(1, 6)]              2 <= 3, so extend the end to max(3, 6)
(8, 10)    [(1, 6), (8, 10)]     8 > 6, a gap, so push
(15, 18)   [..., (15, 18)]       15 > 10, a gap, so push
```

The comparison uses `max` for the end. With `(1, 10)` followed by `(2, 3)`, the
incoming end is smaller than the end already recorded, and assigning it would
shrink the interval.

## Implementation

The file contains two functions. The first consumes the vector it is given; the
second borrows it.

```rust
//! Merge Intervals: sort by start, then merge overlapping intervals in one pass.
//!
//! The `match out.last_mut()` pattern is intentionally clean: no deep nesting,
//! no confusing boolean flags.

pub fn merge_intervals(mut intervals: Vec<(i32, i32)>) -> Vec<(i32, i32)> {
    if intervals.is_empty() {
        return intervals;
    }

    intervals.sort_unstable_by_key(|(start, _)| *start);

    let mut merged: Vec<(i32, i32)> = Vec::with_capacity(intervals.len());
    for (start, end) in intervals {
        match merged.last_mut() {
            Some(previous) if start <= previous.1 => {
                previous.1 = previous.1.max(end);
            }
            _ => merged.push((start, end)),
        }
    }
    merged
}

pub fn merge_intervals2(mut intervals: Vec<(i32, i32)>) -> Vec<(i32, i32)> {
    if intervals.is_empty() {
        return intervals;
    }

    intervals.sort_unstable_by_key(|(start, _)| *start);

    let mut merged: Vec<(i32, i32)> = Vec::with_capacity(intervals.len());

    for &(start, end) in &intervals {
        match merged.last_mut() {
            Some(previous) if start <= previous.1 => {
                previous.1 = previous.1.max(end);
            }
            _ => merged.push((start, end)),
        }
    }
    merged
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn merges_overlapping_and_adjacent() {
        let intervals = vec![(1, 3), (2, 6), (8, 10), (15, 18)];
        assert_eq!(merge_intervals(intervals), vec![(1, 6), (8, 10), (15, 18)]);
    }

    #[test]
    fn handles_empty_and_disjoint() {
        assert_eq!(merge_intervals(vec![]), vec![]);
        assert_eq!(merge_intervals(vec![(1, 2), (3, 4)]), vec![(1, 2), (3, 4)]);
    }
}
```

`sort_unstable_by_key` sorts by the start value and does not preserve the relative
order of intervals with equal starts. That is correct here: intervals with equal
starts are merged into one, so their order cannot matter.

`for (start, end) in intervals` consumes the vector, which moves each pair out
rather than borrowing it. `for &(start, end) in &intervals` in the second function
copies each pair out of the borrowed vector. Since `(i32, i32)` is `Copy`, both
loops work, and the difference is only whether the caller keeps the vector.

`match merged.last_mut()` with a guard keeps the three cases flat: an overlap, an
empty output, and a gap. The last two share an arm because they share an action.

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

The input vector is taken by value, so its allocation is available to the
function; the code still allocates a second vector for the output rather than
sorting and merging in place.

## Limitations

**The second function is unreferenced.** `merge_intervals2` is not exported from
`lib.rs`, no test in the file calls it, and no integration test calls it. Its only
difference from `merge_intervals` is the loop, which borrows the vector instead of
consuming it. An unused `pub fn` in a library is not a compiler warning, so the two
functions coexist without a signal that one of them is unused.

**There is no test for the borrow-based variant.** Even if the function is kept,
nothing checks that it agrees with the other one. A one-line assertion,
`assert_eq!(merge_intervals2(v.clone()), merge_intervals(v))`, would cover it.

**`i32` bounds silently overflow in the merged output.** The end of a merged
interval is `previous.1.max(end)`, so no arithmetic is performed and no overflow
is possible. The bound of `i32` matters only in the sense that a caller with
larger times cannot use the function.

## Summary

- Whether intervals that touch are merged is a specification decision rather than
  a detail of the implementation. It changes one comparison from `<` to `<=`, and
  the two choices give different answers for `[1, 2]` followed by `[2, 3]`.
- The `O(n log n)` bound comes from the sort. The sweep that follows is linear, so
  the sort determines the cost of the function.
- After sorting by start, one comparison per interval is sufficient. Merging
  extends the last interval to the largest end seen, so that interval is the only
  one a new interval can overlap.

## References

- Standard library, [`slice::sort_unstable_by_key`](https://doc.rust-lang.org/std/primitive.slice.html#method.sort_unstable_by_key).
- Standard library, [`Vec::last_mut`](https://doc.rust-lang.org/std/vec/struct.Vec.html#method.last_mut).
- Standard library, [`Ord::max`](https://doc.rust-lang.org/std/cmp/trait.Ord.html#method.max).
