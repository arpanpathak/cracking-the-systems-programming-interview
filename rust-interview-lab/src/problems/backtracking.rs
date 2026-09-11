//! Subsets: enumerate every subset of a set of distinct integers.
//!
//! Backtracking with clean `path.push(...)` + recursive exploration + `pop`.
//! `Vec<Vec<i32>>` is sorted in the tests to avoid order-dependent assertions.

pub fn subsets(nums: Vec<i32>) -> Vec<Vec<i32>> {
    let mut result = Vec::with_capacity(1 << nums.len());
    let mut path = Vec::new();

    fn backtrack(nums: &[i32], start: usize, path: &mut Vec<i32>, result: &mut Vec<Vec<i32>>) {
        result.push(path.clone());
        for idx in start..nums.len() {
            path.push(nums[idx]);
            backtrack(nums, idx + 1, path, result);
            path.pop();
        }
    }

    backtrack(&nums, 0, &mut path, &mut result);
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn generates_all_subsets() {
        let mut subsets = subsets(vec![1, 2, 3]);
        subsets.sort_unstable();
        assert_eq!(subsets.len(), 8);
        assert!(subsets.contains(&vec![]));
        assert!(subsets.contains(&vec![1, 2, 3]));
    }

    #[test]
    fn empty_input_has_one_subset() {
        assert_eq!(subsets(vec![]), vec![vec![]]);
    }
}
