# 63. Three Sum {#three-sum}

*Source file: [`src/problems/three_sum.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/three_sum.rs). Test it with `cargo test three_sum`.*

## Problem Statement

Given a list of integers and a target, return every unique triplet of values that adds
up to the target. Two triplets with the same three values count once, whatever positions
they came from, and the triplets are returned with their values in ascending order.

Checking every triple of positions costs `n(n - 1)(n - 2) / 6` sums, which is `O(n³)`,
and removing duplicate triplets afterwards needs extra storage.

## Designing a Solution

Sort the values first. Sorting makes two things cheap: duplicates sit next to each other,
and for a fixed first value the remaining pair can be found with two pointers instead of
a nested loop.

For each position `i`, the pair must add up to `target - numbers[i]` among the values to
the right of `i`. Start `left` just after `i` and `right` at the end:

```text
sum < target   the smallest candidate is too small: move left one step right
sum > target   the largest candidate is too large: move right one step left
sum == target  record the triplet, skip equal neighbors on both sides, move both
```

Each step discards one candidate that can no longer be part of a triplet with
`numbers[i]`, so the inner loop is linear and the whole algorithm is `O(n²)`.

The three-way decision maps directly onto `Ord::cmp`, which returns `Ordering::Less`,
`Greater`, or `Equal`. Importing the variants with
`use std::cmp::Ordering::{Equal, Greater, Less};` lets the `match` name them without the
`Ordering::` prefix, and the compiler checks that all three cases are handled.

Duplicates are skipped in two places. A first value equal to the previous one is
skipped, because it would find the same pairs again. After a match, `left` and `right`
step past values equal to the ones just used, so the same pair is not recorded twice for
this first value.

## Implementation

<p class="listing"><span class="listing-label">Listing 63.1</span> The complete module, with its tests. <code>src/problems/three_sum.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/three_sum.rs">read the file on GitHub</a></p>

`three_sum` takes `numbers: &mut [i32]` and sorts it in place with `sort_unstable`. A
mutable slice is enough: sorting only rearranges elements, so the function needs neither
ownership nor a copy, and it accepts a `Vec`, an array, or part of either. The `&mut` at
the call site, `three_sum(&mut values, 0)`, shows that the caller's data comes back
sorted. `sort_unstable` is faster than `sort` and allocates nothing; stability does not
matter for integers.

`numbers.len().saturating_sub(1)` gives the last index without underflowing when the
slice is empty. For every `i`, `left` starts at `i + 1`, so for the last two positions
`left >= right` and the inner loop does not run.

The sum is computed in `i64`. Three `i32` values can add up to about three times
`i32::MAX`, which overflows an `i32`: a debug build would panic and a release build would
wrap to a wrong answer. `i64::from` widens each value losslessly, and the target is
widened once before the loop.

Inside the `Equal` arm, `results.push((numbers[i], numbers[left], numbers[right]))`
records the values. The two `while` loops check `left < right` before indexing
`left + 1` and `right - 1`, so neither can step past the other or read outside the pair's
range. The final `left += 1; right -= 1;` moves both pointers off the values just used.

The tests cover the standard example, inputs that are all duplicates, a non-zero target,
inputs with no answer or fewer than three values, and extreme values whose sum would
overflow `i32`.

## Intuition

```text
three_sum(&mut [-1, 0, 1, 2, -1, -4], 0)

sorted: [-4, -1, -1, 0, 1, 2]
index:    0   1   2  3  4  5

i  first  left right  sum   cmp      action
0   -4     1    5     -3    Less     left = 2
0   -4     2    5     -3    Less     left = 3
0   -4     3    5     -2    Less     left = 4
0   -4     4    5     -1    Less     left = 5, loop ends
1   -1     2    5      0    Equal    push (-1, -1, 2); no equal neighbors; left = 3, right = 4
1   -1     3    4      0    Equal    push (-1, 0, 1); left = 4, right = 3, loop ends
2   -1                               same as numbers[1], skip
3    0     4    5      3    Greater  right = 4, loop ends
4    1     5    5                    left == right, loop does not run
5    2     6    5                    left > right, loop does not run

result: [(-1, -1, 2), (-1, 0, 1)]
```

## Time and Space Complexity

| Resource | Cost | Condition |
|---|---|---|
| Time | `O(n²)` | the sort is `O(n log n)`; each of the `n` first values runs a linear two-pointer scan |
| Space | `O(1)` extra | the slice is sorted in place; the result holds one tuple per unique triplet |

`sort_unstable` sorts in place without allocating, so the only allocation is the result.

## Limitations

**The caller's order is lost.** The slice comes back sorted. A caller that needs the
original order must clone the data before the call.

**Values, not indices, are returned.** After sorting, positions no longer refer to the
caller's data, so the function returns the values. A problem that asks for the original
indices needs the positions carried through the sort, for example by sorting
`(value, index)` pairs.

**`O(n²)` is the expected bound for this problem.** A hash-set approach has the same
asymptotic cost and more overhead, and makes duplicate handling harder. For very large
inputs with a small value range, counting values can do better.

**The skip loops are subtle.** Removing the `left < right` guard lets `left + 1` or
`right - 1` read past the pair's range and, in an input such as `[0, 0, 0]`, index out of
bounds. The guard must come before the comparison, which `&&` guarantees by evaluating
left to right.

## Summary

- Sorting turns Three Sum into `n` two-pointer scans, for `O(n²)` time.
- `match current_sum.cmp(&target)` with `Less`, `Greater`, and `Equal` imported into scope
  states the three moves directly, and the match is checked for exhaustiveness.
- Skipping an equal first value, and equal neighbors after a match, keeps each triplet
  unique without a set.
- Taking `&mut [i32]` and sorting it in place avoids a copy and ownership; widening to
  `i64` keeps the sum from overflowing.

## References

- Standard library, [`Ord::cmp`](https://doc.rust-lang.org/std/cmp/trait.Ord.html#tymethod.cmp) and [`std::cmp::Ordering`](https://doc.rust-lang.org/std/cmp/enum.Ordering.html).
- Standard library, [`slice::sort_unstable`](https://doc.rust-lang.org/std/primitive.slice.html#method.sort_unstable).
- Standard library, [`usize::saturating_sub`](https://doc.rust-lang.org/std/primitive.usize.html#method.saturating_sub).
