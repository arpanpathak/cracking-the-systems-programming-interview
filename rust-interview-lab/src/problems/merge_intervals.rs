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
