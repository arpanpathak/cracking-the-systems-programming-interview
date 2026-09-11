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
