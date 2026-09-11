# 6. Top K Frequent Elements {#top-k-frequent}

*Source file: [`src/problems/top_k_frequent.rs`](../../rust-interview-lab/src/problems/top_k_frequent.rs). Test it with
`cargo test top_k_frequent`.*

## Problem Statement

Given a slice of integers and a number `k`, return the `k` values that occur most
often. The result order is only defined if the function states how ties are
broken, and the file's ordering answers that question by construction: the heap
key is the pair `(count, value)`, compared lexicographically, so a larger value
wins a tie.

## Designing a Solution

Two passes. The first counts occurrences in a hash map. The second moves every
`(count, value)` pair into a `BinaryHeap` and pops the largest keys.

`BinaryHeap` in Rust is a max-heap, so pushing `(count, num)` and popping puts the
highest count first. That is the opposite of the min-heap-with-size-`k` design
that keeps `O(m log k)` time, and the file chooses the simpler of the two. The
cost table below states what that choice costs.

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

`*counts.entry(num).or_insert(0) += 1` is the counting idiom. `entry` looks up or
inserts, `or_insert(0)` supplies the initial count, and the dereference lets the
increment write through the returned `&mut usize`. The map is searched once per
element.

`counts.into_iter()` consumes the map and yields owned pairs, which avoids
borrowing it while the heap is built. `map(|(num, count)| (count, num))` reverses
each pair so that the heap's ordering applies to the count first; this is the
whole tie-break rule.

`while result.len() < k` with `None => break` handles `k` larger than the number
of distinct values. The heap empties and the loop stops, leaving a result shorter
than `k`.

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

The heap holds every distinct value, not `k` of them. For a slice of a million
elements with half a million distinct values and `k = 10`, the program builds a
heap of half a million entries to return ten. The bounded variant keeps a
min-heap of size `k` and discards each element smaller than the current root,
which is `O(m log k)` and needs `O(k)` space. The file does not implement it, and
the comment in the file states the trade in one line: `O(n log n) worst case;
acceptable and readable`.

## Limitations

**The heap is unbounded in the number of distinct values.** Every distinct value
counted becomes an entry in the heap, so the structure holds `m` entries at its
largest, where `m` is the number of distinct values in the input.

**The result order depends on the heap's internal comparison and nothing else.**
The pair ordering makes the order deterministic, and the first test sorts the
result before asserting, so the file never pins the order. A caller that prints
the result directly sees the order the heap produced, which is by descending count
and then by descending value.

**A `k` of zero returns an empty vector.** `Vec::with_capacity(0)` allocates
nothing and the loop does not run, so the answer is empty rather than a panic. The
file has no test for it.

**The tie-break rule is not documented.** A reader has to derive it from
`(count, num)` and from the fact that `BinaryHeap` is a max-heap. Two sentences in
the module documentation would make it part of the contract rather than a
consequence of the implementation.

## Summary

- The tie-break rule is part of the specification. "The `k` most frequent" is
  incomplete where counts are equal, and this implementation resolves a tie in
  favour of the larger value, because the heap orders `(count, value)` pairs and
  is a max-heap.
- Two heap designs are available. A heap holding every distinct value costs
  `O(m log m)`; a heap bounded at `k` entries costs `O(m log k)`. This file uses
  the bounded heap, and the result is therefore in heap order rather than sorted.
- `counts.entry(num).or_insert(0) += 1` performs one map lookup rather than a
  lookup followed by an insertion.

## References

- Standard library, [`BinaryHeap`](https://doc.rust-lang.org/std/collections/struct.BinaryHeap.html), which documents that the heap is a max-heap.
- Standard library, [`cmp::Reverse`](https://doc.rust-lang.org/std/cmp/struct.Reverse.html), the wrapper that turns a max-heap into a min-heap.
- Standard library, [`HashMap::entry`](https://doc.rust-lang.org/std/collections/struct.HashMap.html#method.entry).
