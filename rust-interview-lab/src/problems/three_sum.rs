//! Three Sum: every unique triplet of values that adds up to a target.
//!
//! Sort, fix the first value, then close in on the other two with two pointers.
//! Takes the vector by value and sorts it in place: O(n^2) time, no extra space
//! beyond the result.

// Import the variants directly into scope
use std::cmp::Ordering::{Equal, Greater, Less};

pub fn three_sum(mut numbers: Vec<i32>, target: i32) -> Vec<(i32, i32, i32)> {
    numbers.sort_unstable();

    let mut results = Vec::new();
    let target = i64::from(target);

    for i in 0..numbers.len() {
        // Skip a first value that was already used, so triplets stay unique.
        if i > 0 && numbers[i] == numbers[i - 1] {
            continue;
        }

        let (mut left, mut right) = (i + 1, numbers.len().saturating_sub(1));
        while left < right {
            // Widen to i64 so the sum of three i32 values cannot overflow.
            let current_sum =
                numbers[i] as i64 + numbers[left] as i64 + numbers[right] as i64;

            match current_sum.cmp(&target) {
                Less => left += 1,
                Greater => right -= 1,
                Equal => {
                    results.push((numbers[i], numbers[left], numbers[right]));

                    while left < right && numbers[left] == numbers[left + 1] {
                        left += 1;
                    }
                    while left < right && numbers[right] == numbers[right - 1] {
                        right -= 1;
                    }

                    left += 1;
                    right -= 1;
                }
            }
        }
    }

    results
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn finds_all_unique_triplets() {
        let result = three_sum(vec![-1, 0, 1, 2, -1, -4], 0);
        assert_eq!(result, vec![(-1, -1, 2), (-1, 0, 1)]);
    }

    #[test]
    fn skips_duplicates_on_every_position() {
        assert_eq!(three_sum(vec![0, 0, 0, 0], 0), vec![(0, 0, 0)]);
        assert_eq!(three_sum(vec![-2, 0, 0, 2, 2], 0), vec![(-2, 0, 2)]);
    }

    #[test]
    fn supports_a_non_zero_target() {
        assert_eq!(
            three_sum(vec![1, 2, 3, 4, 5], 9),
            vec![(1, 3, 5), (2, 3, 4)]
        );
    }

    #[test]
    fn returns_nothing_when_no_triplet_exists() {
        assert!(three_sum(vec![1, 2, 3], 100).is_empty());
        assert!(three_sum(vec![1, 2], 3).is_empty());
        assert!(three_sum(vec![], 0).is_empty());
    }

    #[test]
    fn does_not_overflow_on_extreme_values() {
        assert_eq!(
            three_sum(vec![i32::MAX, i32::MAX, i32::MIN], i32::MAX - 1),
            vec![(i32::MIN, i32::MAX, i32::MAX)]
        );
    }
}
