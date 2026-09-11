//! Top K Frequent Elements.
//!
//! Count occurrences with a HashMap, then use a max-heap (`BinaryHeap`) to pull
//! out the top k elements. O(n log n) worst case; acceptable and readable.

use std::collections::{BinaryHeap, HashMap};

pub fn top_k_frequent(nums: &[i32], k: usize) -> Vec<i32> {
    let mut counts: HashMap<i32, usize> = HashMap::with_capacity(nums.len());
    for &num in nums.iter() {
        *counts.entry(num).or_insert(0) += 1;
    }

    // BinaryHeap is a max-heap in Rust, so (count, num) keeps highest counts first.
    let mut heap: BinaryHeap<(usize, i32)> = counts
        .into_iter()
        .map(|(num, count)| (count, num))
        .collect();

    let mut result = Vec::with_capacity(k);
    while result.len() < k {
        match heap.pop() {
            Some((_, num)) => result.push(num),
            None => break,
        }
    }
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn returns_top_two() {
        let nums = [1, 1, 1, 2, 2, 3];
        let mut result = top_k_frequent(&nums, 2);
        result.sort_unstable();
        assert_eq!(result, vec![1, 2]);
    }

    #[test]
    fn k_larger_than_unique_values_returns_all() {
        let result = top_k_frequent(&[1, 2, 3], 10);
        assert_eq!(result.len(), 3);
    }
}
