# 6. Top K Frequent Elements {#top-k-frequent}

*Source file: [`src/problems/top_k_frequent.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/top_k_frequent.rs). Test it with
`cargo test top_k_frequent`.*

## Problem Statement

Given a slice of integers and a number `k`, return the `k` values that occur most
often. The result order is defined only if the function states how ties are broken.
This implementation keys the heap on `(count, value)`, compared lexicographically, so
a larger value wins a tie.

## Designing a Solution

Two passes. The first counts occurrences in a hash map. The second moves every
`(count, value)` pair into a `BinaryHeap` and pops the largest keys.

`BinaryHeap` in Rust is a max-heap, so the pairs come out in descending count and, for
equal counts, in descending value. The alternative, a min-heap holding at most `k`
entries, costs `O(m log k)` time and `O(k)` space and is not implemented here. The
cost table states what the simpler choice costs.

## Implementation

```rust
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
```

`*counts.entry(num).or_insert(0) += 1` looks up the count or inserts zero, then
increments through the returned `&mut usize`. The map is searched once per element
rather than twice.

`counts.into_iter()` consumes the map and yields owned pairs, so the heap is built
without borrowing the map. `map(|(num, count)| (count, num))` reverses each pair so
that the count is the first component of the key, which is the tie-break rule.

`while result.len() < k` with `None => break` handles a `k` larger than the number of
distinct values: the heap empties, the loop stops, and the result is shorter than `k`.

## Intuition

```text
nums = [1, 1, 1, 2, 2, 3]     k = 2

pass 1: counts = {1: 3, 2: 2, 3: 1}

pass 2: heap after collecting the pairs (count, value):
        pop order is (3, 1), (2, 2), (1, 3)

pop 1 -> push value 1     result = [1]
pop 2 -> push value 2     result = [1, 2]      length is k, stop

The heap still holds (1, 3), which is not popped.
```

## Time and Space Complexity

| Resource | Cost | Condition |
|---|---|---|
| Time | `O(n + m log m)` expected | `m` distinct values; the first pass is `O(n)`, the heap operations are `O(m log m)` |
| Space | `O(m)` | the map and the heap each hold one entry per distinct value |

The heap holds one entry per distinct value rather than `k` entries. For a slice of a
million elements with half a million distinct values and `k = 10`, the program builds a
heap of half a million entries to return ten. A min-heap bounded at `k` entries, which
discards each element smaller than its root, costs `O(m log k)` time and `O(k)` space.
The file does not implement it.

## Limitations

**The heap is unbounded in the number of distinct values.** Every distinct value
counted becomes an entry, so the structure holds `m` entries at its largest, where `m`
is the number of distinct values in the input.

**The result order is fixed by the heap comparison and nothing else.** The pair
ordering makes it deterministic, and the first test sorts the result before asserting,
so the file never pins the order. A caller that prints the result directly sees
descending count and then descending value.

**A `k` of zero returns an empty vector.** `Vec::with_capacity(0)` allocates nothing
and the loop does not run, so the answer is empty rather than a panic. The file has no
test for it.

**The tie-break rule is not documented.** A reader has to derive it from `(count, num)`
and from the fact that `BinaryHeap` is a max-heap. Two sentences in the module
documentation would make it part of the contract rather than a consequence of the
implementation.

## References

- Standard library, [`BinaryHeap`](https://doc.rust-lang.org/std/collections/struct.BinaryHeap.html), which documents that the heap is a max-heap.
- Standard library, [`cmp::Reverse`](https://doc.rust-lang.org/std/cmp/struct.Reverse.html), the wrapper that turns a max-heap into a min-heap.
- Standard library, [`HashMap::entry`](https://doc.rust-lang.org/std/collections/struct.HashMap.html#method.entry).
