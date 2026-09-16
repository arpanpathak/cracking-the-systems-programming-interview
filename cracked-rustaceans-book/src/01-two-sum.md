# 1. Two Sum {#two-sum}

*Source file: [`src/problems/two_sum.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/two_sum.rs). Test it with `cargo test two_sum`.*

## Problem Statement

Given a slice of integers and a target value, return the indices of two positions
whose values sum to the target, or report that no such pair exists. The inputs this
function handles contain at most one such pair. The two positions may hold the same
value provided the positions differ.

Comparing every element with every element after it costs `n(n - 1) / 2`
comparisons for a slice of length `n`, which is `O(n²)`. One million elements is
about five hundred billion comparisons.

## Designing a Solution

For an element `x` and a target `t`, the value that completes the pair is `t - x`.
It follows from `x` and `t` alone, so finding it requires no search.

The direct method asks whether `t - x` occurs anywhere in the remainder of the
slice, and every answer costs a scan. Recording each element as it is passed
replaces the scan with a hash-table lookup: when the cursor reaches the second
element of a pair, the first element is already in the table.

```text
x        the element under the cursor
t - x    the only value that would complete a pair with x
```

The table maps a value to the position where it was found, because the answer is a
pair of indices. It is keyed by the element's own value rather than by the
complement, because one element can be the second half of one pair and the first
half of another.

## Implementation

```rust
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
```

The return type is `Option<(usize, usize)>`. Absence is part of the answer, and a
caller cannot read index zero as a failure because the indices exist only inside
`Some`. Both are `usize`, which is what `enumerate` produces and what indexes a
slice.

`HashMap::with_capacity(nums.len())` bounds the number of entries the loop can
insert. Without the hint the table rehashes as it grows, and the hint removes that
work.

`nums.iter()` yields `&i32`, `enumerate` pairs each reference with its position, and
the pattern `(idx, &num)` destructures that pair, copying the integer out of the
reference.

`seen.get(&(target - num))` computes the complement and looks it up in one
expression; `get` takes a reference to the key. The borrow that `get` returns ends
with the `match`, which is what allows the `None` arm to insert into the same map.

`Some(&prev)` copies the stored index out of the returned reference. `Some(prev)`
would move a `usize` out of a map the function does not own.

## Intuition

The first trace uses the slice from the test suite. The pair completes on the
second element.

```text
nums = [2, 7, 11, 15]      target = 9

step  idx  num   complement 9-num   present in the map?   map after the step
 1     0    2         7              no                   {2: 0}
 2     1    7         2              yes, at index 0      return Some((0, 1))
```

The second trace has two positions holding the same value. The positions differ,
which the answer requires; the values are equal, which the input permits.

```text
nums = [3, 3]              target = 6

step  idx  num   complement 6-num   present in the map?   map after the step
 1     0    3         3              no                   {3: 0}
 2     1    3         3              yes, at index 0      return Some((0, 1))
```

With `nums = [1, 2, 3]` and `target = 100`, every complement is negative, no lookup
succeeds, and the loop ends with three entries in the map. The map is released when
the function returns, so the memory used follows the input rather than whether a
pair exists.

## Time and Space Complexity

| Resource | Cost | Condition |
|---|---|---|
| Time | `O(n)` expected | the hash function distributes keys evenly |
| Space | `O(n)` | one entry per element, when every element is distinct |

The time bound is expected rather than guaranteed. A hash table hashes the key,
selects a bucket from part of the hash, and probes from there. Evenly distributed
keys give a small constant number of probes per operation. Keys that collide
systematically turn every operation in a colliding group into a scan, and `n`
insertions cost `O(n²)` in total.

The standard library's default hasher is SipHash-1-3 with a key chosen at random for
each map, so which keys collide depends on a seed the program cannot observe. A
program that installs its own hasher, as programs that hash integers do for speed,
gives up that property, and the expected bound becomes a claim its input can break.

Space is `O(n)` because the table holds one entry per distinct value visited, and an
input with no pair keeps every element distinct. For a slice of integers the table
is larger than the input: a million `i32` values occupy four megabytes, while a map
of a million entries stores a key, a value, and the table's bookkeeping for each.

## Limitations

The subtraction `target - num` can overflow. `two_sum(&[i32::MIN], 0)` evaluates
`0 - i32::MIN`, and no `i32` holds that value. A debug build panics with an
arithmetic overflow. A release build wraps, the wrapped value matches no element,
and the function returns `None`. The two profiles therefore disagree on the same
input, and a program tested in debug and shipped in release can change behaviour on
a value read from a file or a socket. `checked_sub` reports the case instead:

```rust
let complement = match target.checked_sub(num) {
    Some(value) => value,
    None => {
        seen.insert(num, idx);
        continue;
    }
};
```

The element that has no complement is still recorded, because a later element may
need to find it.

`insert` overwrites the index of a repeated value, so the map keeps the most recent
position. A pair completed by the second occurrence returns the index the first
occurrence recorded, which is the answer the function promises. A caller that needs
the pair with the smallest first index, or every pair, requires information this
function discards.

The function returns as soon as it reaches the second element of any pair, so on an
input with several valid pairs the answer depends on the order of the elements.
Reporting every pair requires the loop to continue and the map to hold every index
for each value. Reporting the pair with the earliest first index requires
`seen.entry(num).or_insert(idx)` in place of `insert`.

The element type is `i32` and the index type is `usize`. The algorithm depends on
neither choice, but the signature fixes both, so a slice of `i64`, or of a type that
is not `Copy`, cannot be passed without changing the declaration.

## References

- Standard library, [`HashMap`](https://doc.rust-lang.org/std/collections/struct.HashMap.html), on the default hasher and its random seed.
- Standard library, [`HashMap::with_capacity`](https://doc.rust-lang.org/std/collections/struct.HashMap.html#method.with_capacity).
- Standard library, [`i32::checked_sub`](https://doc.rust-lang.org/std/primitive.i32.html#method.checked_sub), and [`HashMap::entry`](https://doc.rust-lang.org/std/collections/struct.HashMap.html#method.entry) for the variant that keeps the earliest index.
- The Rust Reference, [Arithmetic overflow](https://doc.rust-lang.org/reference/expressions/operator-expr.html#overflow), on the difference between debug and release builds.
