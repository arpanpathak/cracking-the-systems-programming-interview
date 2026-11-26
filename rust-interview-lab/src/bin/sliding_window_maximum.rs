//! Maximum of every window of `k` consecutive values, with a monotonic deque.
//!
//! The deque holds indexes whose values decrease from front to back, so the front is
//! always the current window's maximum. Each index enters and leaves once: O(n).

use std::collections::VecDeque;

// 0,1,2,3,4,5
fn sliding_window_max(s: &[i32], k: usize) -> Vec<i32> {
    let mut dq = VecDeque::new();
    let mut out = vec![];

    if k == 0 {
        return out; // no window has zero width
    }

    for (i, &x) in s.iter().enumerate() {
        // Slide out of the invalid or we could say that f <= i - k, because Window starts from (i - k, i]
        if dq.front().is_some_and(|&f| f + k <= i) {
            dq.pop_front();
        }

        while dq
            .back()
            .is_some_and(|&back_idx| s[back_idx] <= x)
        {
            dq.pop_back();
        }
        dq.push_back(i);

        if i + 1 >= k {
            out.push(s[dq[0]]);
        }
    }

    out
}

fn main() {
    let values = [1, 3, -1, -3, 5, 3, 6, 7];

    println!("values = {values:?}, k = 3");
    println!("window maximums = {:?}", sliding_window_max(&values, 3));
}

#[cfg(test)]
mod tests {
    use super::*;

    /// The slow answer to compare against: scan every window.
    fn brute_force(s: &[i32], k: usize) -> Vec<i32> {
        if k == 0 {
            return vec![];
        }

        s.windows(k)
            .filter_map(|window| window.iter().max().copied())
            .collect()
    }

    #[test]
    fn matches_brute_force() {
        let values = [1, 3, -1, -3, 5, 3, 6, 7, 7, 2, 9, -4, 0];

        for k in 0..=values.len() + 1 {
            assert_eq!(
                sliding_window_max(&values, k),
                brute_force(&values, k),
                "k = {k}"
            );
        }
    }

    #[test]
    fn leetcode_example() {
        assert_eq!(
            sliding_window_max(&[1, 3, -1, -3, 5, 3, 6, 7], 3),
            [3, 3, 5, 5, 6, 7]
        );
    }
}
