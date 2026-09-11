//! Two Sum: find the pair of indices whose values add up to a target.
//!
//! Use a `HashMap` for one pass: O(n) time, O(n) space.

use std::collections::HashMap;

pub fn two_sum(nums: &[i32], target: i32) -> Option<(usize, usize)> {
    let mut seen = HashMap::with_capacity(nums.len());
    for (idx, &num) in nums.iter().enumerate() {
        match seen.get(&(target - num)) {
            Some(&prev) => return Some((prev, idx)),
            None => {
                seen.insert(num, idx);
            }
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn finds_pair() {
        let nums = [2, 7, 11, 15];
        assert_eq!(two_sum(&nums, 9), Some((0, 1)));
    }

    #[test]
    fn returns_none_when_missing() {
        assert_eq!(two_sum(&[1, 2, 3], 100), None);
    }
}
