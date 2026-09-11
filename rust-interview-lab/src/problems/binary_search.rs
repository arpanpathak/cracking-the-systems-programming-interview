//! Binary search on a rotated sorted array.
//!
//! Classic O(log n) interview problem. The code uses explicit range bounds and
//! sorted-half checks; no recursion or nested `if` chains are required.

pub fn search_rotated(nums: &[i32], target: i32) -> Option<usize> {
    let mut low = 0usize;
    let mut high = nums.len();

    while low < high {
        let mid = low + (high - low) / 2;
        if nums[mid] == target {
            return Some(mid);
        }

        // 6,7, 1,2,3,4,5
        // start = 0 , end = 6, 0 + (6-0)/2 = 3
        
        // 4,5,6,1,2,3
        let left_is_sorted = nums[low] <= nums[mid];
        if left_is_sorted {
            if nums[low] <= target && target < nums[mid] {
                high = mid;
            } else {
                low = mid + 1;
            }
        } else if nums[mid] < target && target <= nums[high - 1] {
            low = mid + 1;
        } else {
            high = mid;
        }
    }

    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn finds_target_in_rotated_array() {
        let nums = [4, 5, 6, 7, 0, 1, 2];
        assert_eq!(search_rotated(&nums, 0), Some(4));
        assert_eq!(search_rotated(&nums, 3), None);
        assert_eq!(search_rotated(&nums, 5), Some(1));
    }

    #[test]
    fn handles_unrotated_and_single() {
        assert_eq!(search_rotated(&[1, 2, 3, 4], 3), Some(2));
        assert_eq!(search_rotated(&[1], 1), Some(0));
        assert_eq!(search_rotated(&[1], 2), None);
    }
}
