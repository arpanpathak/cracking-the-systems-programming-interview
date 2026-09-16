# 9. Binary Search on a Rotated Array {#binary-search}

*Source file: [`src/problems/binary_search.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/binary_search.rs). Test it with
`cargo test binary_search`.*

## Problem Statement

A sorted slice of distinct values has been rotated by an unknown amount. Find the index
of a target value in `O(log n)`, or report that it is absent.

```text
[4, 5, 6, 7, 0, 1, 2]        a rotation of [0, 1, 2, 4, 5, 6, 7]
     sorted      sorted
```

## Designing a Solution

The loop keeps a half-open range `[low, high)` and the invariant

> the target, if it is present, lies in `nums[low..high]`.

In a rotated array, at least one half of any range is sorted. Testing
`nums[low] <= nums[mid]` says which half. If the left half is sorted, one range test
decides whether the target can be in it; if it cannot, the target is in the right half.
That test is one comparison, which is what keeps the loop logarithmic.

```text
nums = [4, 5, 6, 7, 0, 1, 2]        target = 0

low  high  mid  nums[mid]  left sorted?  decision
 0    7     3      7       yes, 4 <= 7   target not in [4, 7)  -> low = 4
 4    7     5      1       no, 0 <= 1    target not in (1, 2]  -> high = 5
 4    5     4      0       found                              -> Some(4)
```

## Implementation

<p class="listing"><span class="listing-label">Listing 9.1</span> The complete module, with its tests. <code>src/problems/binary_search.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/binary_search.rs">read the file on GitHub</a></p>

`high` starts at `nums.len()`, not at `nums.len() - 1`, because the range is half-open.
That choice removes the special case for an empty slice: `low == high == 0` and the
loop does not run.

`let mid = low + (high - low) / 2` avoids the overflow that `(low + high) / 2` would
have in a debug build for a slice near the maximum length. The midpoint satisfies
`low <= mid < high`, so `nums[mid]` and `nums[high - 1]` are both in bounds.

`nums[low] <= target && target < nums[mid]` is a half-open interval test: the lower
bound is inclusive and the upper bound exclusive, matching the convention used by the
loop range.

## Intuition

```text
nums = [4, 5, 6, 7, 0, 1, 2]        target = 3, absent

low  high  mid  nums[mid]  left sorted?  test                              next
 0    7     3      7       yes, 4 <= 7   4 <= 3? no                     low = 4
 4    7     5      1       no, 0 <= 1    1 < 3 and 3 <= nums[6]=2? no   high = 5
 4    5     4      0       found? no     left sorted? 0 <= 0 yes
                                         0 <= 3 and 3 < 0? no           low = 5
 5    5     -      -       low == high, loop ends                       None
```

## Time and Space Complexity

| Resource | Cost |
|---|---|
| Time | `O(log n)`, the range halves on every iteration |
| Space | `O(1)`, three indices and no recursion |

## Limitations

**Repeated values break the sorted-half test.** With duplicates, `nums[low] <= nums[mid]`
can hold for both halves, so the code can discard the half holding the target. On
`[1, 1, 1, 0, 1]` the search for `0` fails. The function is correct only for strictly
increasing inputs, which the problem statement guarantees and the documentation does
not mention.

**The returned index is not the first or the last match.** With duplicates, any index
holding the target satisfies the problem as stated. A caller that needs a boundary
needs a different function.

**The slice must be a rotation of one sorted array, not two ascending runs.** The runs
have to be the tail and the head of a single sorted sequence, which is what makes the
range tests meaningful.

**There is no test for a two-element rotation.** `[2, 1]` is the smallest input where
`nums[low] == nums[mid]` is false and the sorted-half test has to choose correctly.

## Summary

- The loop keeps the half-open range `[low, high)` and the invariant that the target,
  if present, lies inside it.
- In a rotated array at least one half of any range is sorted, and `nums[low] <=
  nums[mid]` says which. One range test then decides whether the target can lie in the
  sorted half, and the range halves either way.
- That single comparison is what keeps the search logarithmic in an array that is not
  sorted as a whole.
- The sorted-half test rests on distinct values. With repeats, `nums[low] ==
  nums[mid]` no longer identifies the sorted half, and the worst case becomes linear.

## References

- Standard library, [`slice::binary_search`](https://doc.rust-lang.org/std/primitive.slice.html#method.binary_search), the unrotated case.
- Standard library, [`usize`](https://doc.rust-lang.org/std/primitive.usize.html), whose arithmetic the midpoint formula is written to avoid overflowing.
