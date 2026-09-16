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

Three sweeps follow, and they differ only in what they own. The first consumes the vector
it is given, the second borrows it, and the third merges inside the vector and allocates
no output at all.

```rust
//! Merge Intervals: sort by start, then merge overlapping intervals in one pass.
//!
//! The `match out.last_mut()` pattern is intentionally clean: no deep nesting,
//! no confusing boolean flags.

#[derive(Debug, PartialEq, Clone, Copy)]
pub struct Interval {
    start: i32,
    end: i32
}
pub fn merge_intervals(mut intervals: Vec<Interval>) -> Vec<Interval> {
    if intervals.is_empty() {
        return intervals;
    }

    intervals.sort_unstable_by_key(|interval| interval.start);

    let mut merged: Vec<Interval> = Vec::with_capacity(intervals.len());
    for Interval { start, end } in intervals {
        match merged.last_mut() {
            Some(previous) if start <= previous.end => {
                previous.end = previous.end.max(end);
            }
            _ => merged.push(Interval{start, end}),
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

/// In place: `last` is the last merged interval at the front of the vector.
/// O(1) extra space.
pub fn merge_intervals_in_place(intervals: &mut Vec<Interval>) {
    if intervals.is_empty() {
        return;
    }

    intervals.sort_unstable_by_key(|interval| interval.start);

    let mut last = 0;
    for i in 1..intervals.len() {
        match (intervals[last], intervals[i]) {
            (previous, current) if current.start <= previous.end => {
                intervals[last].end = previous.end.max(current.end);
            }
            (_, current) => {
                last += 1;
                intervals[last] = current;
            }
        }
    }
    intervals.truncate(last + 1);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn merges_overlapping_and_adjacent() {
        let input = [(1, 3), (2, 6), (8, 10), (15, 18)].map(|(start, end)| Interval { start, end });
        let expected = [(1, 6), (8, 10), (15, 18)].map(|(start, end)| Interval { start, end });
        assert_eq!(merge_intervals(input.into()), expected);
    }

    #[test]
    fn handles_empty_and_disjoint() {
        assert_eq!(merge_intervals(vec![]), vec![]);
        let input = [(1, 2), (3, 4)].map(|(start, end)| Interval { start, end });
        let expected = [(1, 2), (3, 4)].map(|(start, end)| Interval { start, end });
        assert_eq!(merge_intervals(input.into()), expected);
    }

    #[test]
    fn merges_in_place() {
        let mut intervals: Vec<Interval> = [(8, 10), (1, 3), (15, 18), (2, 6)]
            .map(|(start, end)| Interval { start, end })
            .into();
        merge_intervals_in_place(&mut intervals);
        let expected = [(1, 6), (8, 10), (15, 18)].map(|(start, end)| Interval { start, end });
        assert_eq!(intervals, expected);

        let mut empty = vec![];
        merge_intervals_in_place(&mut empty);
        assert!(empty.is_empty());
    }
}
```

`sort_unstable_by_key` sorts by the start value and does not preserve the relative order
of intervals with equal starts. Intervals with equal starts are merged into one, so
their order cannot matter.

Destructuring in the loop header is what keeps the body short.
`for Interval { start, end } in intervals` consumes the vector and moves each interval
out; `for &(start, end) in &intervals`, in the older tuple-based `merge_intervals2`,
copies each pair out of a vector the caller keeps. Both `Interval` and `(i32, i32)`
derive `Copy`, so either loop compiles, and the choice says only whether the input
survives the call.

A named struct earns its place here beyond taste. `previous.1 = previous.1.max(end)` and
`previous.end = previous.end.max(end)` compile to the same instructions, and only the
second one says which field is being extended.

`match merged.last_mut()` with a guard keeps the three cases flat: an overlap, an empty
output, and a gap. The last two share an arm because they share an action.

### The variant that merges in place

Both sweeps above allocate a second vector, and the output can never be longer than the
input, so the allocation is avoidable. Writing the merged intervals over the front of the
same vector and truncating at the end brings the extra space down to `O(1)`.

```rust
/// In place: `last` is the last merged interval at the front of the vector.
/// O(1) extra space.
pub fn merge_intervals_in_place(intervals: &mut Vec<Interval>) {
    if intervals.is_empty() {
        return;
    }

    intervals.sort_unstable_by_key(|interval| interval.start);

    let mut last = 0;
    for i in 1..intervals.len() {
        match (intervals[last], intervals[i]) {
            (previous, current) if current.start <= previous.end => {
                intervals[last].end = previous.end.max(current.end);
            }
            (_, current) => {
                last += 1;
                intervals[last] = current;
            }
        }
    }
    intervals.truncate(last + 1);
}
```

Two indices walk the vector. `i` reads, `last` marks the end of the merged prefix, and
`last` never overtakes `i`, so the write at `intervals[last] = current` can only land on a
slot that has already been read. That is the invariant the whole sweep rests on, and it is
the reason nothing is lost when the prefix and the remainder share one allocation.

`match (intervals[last], intervals[i])` copies both intervals out before the arms run.
The copy is what makes the borrow checker accept the assignment inside the first arm:
`intervals[last].end = previous.end.max(current.end)` needs a mutable borrow of the
vector, which would clash with a borrow still held by the scrutinee. Copying two structs
of eight bytes is cheaper than the borrow-splitting the alternative would require, and
`Interval` derives `Copy` for exactly this.

`truncate(last + 1)` drops the tail that the sweep has already absorbed. The vector keeps
its capacity, so the merged result sits in the allocation the caller passed in, and the
function returns nothing.

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
first two versions still allocate a second vector for the output.
`merge_intervals_in_place` does not, and its space cost is the two indices, which is
`O(1)`. All three are dominated by the sort, so the in-place version buys memory rather
than time.

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

## References

- Standard library, [`slice::sort_unstable_by_key`](https://doc.rust-lang.org/std/primitive.slice.html#method.sort_unstable_by_key).
- Standard library, [`Vec::last_mut`](https://doc.rust-lang.org/std/vec/struct.Vec.html#method.last_mut).
- Standard library, [`Ord::max`](https://doc.rust-lang.org/std/cmp/trait.Ord.html#method.max).
