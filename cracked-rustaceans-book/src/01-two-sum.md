# 1. Two Sum {#two-sum}

*Source file: [`src/problems/two_sum.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/two_sum.rs). Test it with `cargo test two_sum`.*

## Problem Statement

Given a slice of integers and a target value, return the indices of two positions
whose values sum to the target, or report that no such pair exists. The usual
statement of the problem guarantees that at most one answer exists, and permits
the two positions to hold the same value as long as they are different positions.

The straightforward solution compares every element with every element after it.
For a slice of length `n`, that is `n(n-1)/2` comparisons, which is `O(n²)`. The
cost is easy to underestimate because the code is short. A slice of a million
elements, an ordinary size for a batch job, would need about five hundred billion
comparisons; at one comparison per nanosecond that is more than six days. The rest
of this chapter reduces that to a single pass.

## Designing a Solution

The useful observation is that for a given element `x` the value of its complement is
not unknown. If the pair sums to a target `t`, then the complement of `x` is exactly
`t - x`. That value is determined by `x` and `t` before any search takes place.

This changes the shape of the work. The naive solution asks a *search* question,
"is there an element equal to `t - x` somewhere in the rest of the slice?", and
every answer costs a scan of what remains. The reformulated solution asks a
*membership* question, "have I already seen `t - x`?", and membership is the
question a hash table answers in constant expected time.

```text
x        the element under the cursor
t - x    the only value that would complete a pair with x
```

Walking the slice once and recording each element as it is passed therefore
suffices. When the cursor reaches the second element of a pair, the first element
is already in the table and the pair can be reported. Nothing earlier in the walk
could have reported that pair, because at that point only one of its two halves had
been seen.

Two decisions in the representation follow from the problem statement. The table
maps a value to the *position* where that value was found, because the answer is a
pair of indices and not a pair of values. And the table is keyed by the element's
own value rather than by its complement, because the role an element plays depends
on what comes after it: the same element may be the second half of one pair and the
first half of another, so it has to be findable by its own value when a later
element arrives.

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

The signature returns `Option<(usize, usize)>`, so the absence of a pair is part of
the answer. A caller cannot mistake an index of zero for a failure, because the
indices exist only inside `Some`. Both are `usize`, which is what `enumerate`
produces and what a slice accepts.

The map is created with `HashMap::with_capacity(nums.len())`. Without the hint the
table rehashes as it fills, moving every entry each time it grows, and the number
of such movements is logarithmic in the final size. The hint is an upper bound on
the entries the loop can insert, so with it the table allocates once.

The loop header, `for (idx, &num) in nums.iter().enumerate()`, reads from the
inside out. `nums.iter()` yields `&i32`. `enumerate` pairs each element with its
position, yielding `(usize, &i32)`. The pattern in the loop header destructures
that pair, and the `&` in `&num` copies the integer out of the reference, so the
body works with `num: i32` rather than with a borrow. Copying an `i32` is a load
from the slice that the loop needed anyway.

The lookup `seen.get(&(target - num))` computes the complement and searches for it
in one expression. `get` takes a reference to the key, which is why the complement
is written inside `&(...)`. An intermediate binding would be equally clear, and
would name a value used once. The borrow of `seen` that `get` returns ends with the
`match`, and that is what allows the `None` arm to take a mutable borrow of the same
map.

The pattern `Some(&prev)` copies the stored index out of the reference that `get`
returned. Writing `Some(prev)` would attempt to move a `usize` out of a map the
caller does not own, and the borrow checker refuses it.

## Intuition

The first trace uses the slice from the test suite, where the pair is completed on
the second element.

```text
nums = [2, 7, 11, 15]      target = 9

step  idx  num   complement 9-num   present in the map?   map after the step
 1     0    2         7              no                   {2: 0}
 2     1    7         2              yes, at index 0      return Some((0, 1))
```

The second trace covers the case the problem statement is written to permit: two
positions holding the same value.

```text
nums = [3, 3]              target = 6

step  idx  num   complement 6-num   present in the map?   map after the step
 1     0    3         3              no                   {3: 0}
 2     1    3         3              yes, at index 0      return Some((0, 1))

The two positions are distinct, which the answer requires; the two values are
equal, which the problem statement allows.
```

A third case is worth following for what it does not do. With `nums = [1, 2, 3]`
and `target = 100`, every complement is negative, no lookup succeeds, and the loop
runs to the end with three entries in the map. The function then returns `None`,
and the map is released when the function returns. The memory used by the search
therefore depends on the input, and not on whether an answer exists.

## Time and Space Complexity

| Resource | Cost | Condition |
|---|---|---|
| Time | `O(n)` expected | the hash function distributes keys evenly |
| Space | `O(n)` | one entry per element, when every element is distinct |

The time bound is expected rather than guaranteed. A hash table computes a hash of
the key, uses part of it to select a bucket, and probes from there. When keys
distribute evenly the average number of probes per operation is a small constant,
close to one in the standard library's implementation. When keys collide
systematically, every operation inside a colliding group degenerates into a scan,
and `n` insertions cost `O(n²)` in total.

The standard library's default hasher is SipHash-1-3 with a key chosen at random
for each map. That is what keeps the worst case out of reach of an attacker who
supplies the input: which keys collide depends on a seed the attacker cannot
observe. A program that installs its own hasher, as programs that hash integers do
for speed, gives up that protection, and the expected bound then becomes a claim
the program's own input can break.

Space is `O(n)` because the table holds an entry per distinct value visited, and in
the worst case every element is distinct and no pair exists. For a slice of
integers the table is larger than the input. A million `i32` values occupy four
megabytes, while a map of a million entries carries a key, a value, and the table's
own bookkeeping for each one. The memory cost of the faster algorithm is the price
of the membership test, and it is paid in full when the answer is absent.

## Limitations

The subtraction `target - num` is arithmetic on `i32`, and it can overflow. The
case is reachable with a single element: `two_sum(&[i32::MIN], 0)` evaluates
`0 - i32::MIN`, and `i32::MIN` has no counterpart of the opposite sign that fits in
an `i32`. In a debug build that expression panics with an arithmetic overflow. In a
release build the same expression wraps, the wrapped value is a number no element
can hold, and the function returns `None`. The two build profiles therefore
disagree about the same input, which means a program tested in debug and shipped in
release can change behaviour on a value that arrived from a file or a network. The
remedy is one call:

```rust
let complement = match target.checked_sub(num) {
    Some(value) => value,
    None => {
        seen.insert(num, idx);
        continue;
    }
};
```

`checked_sub` reports the impossible case instead of overflowing, and the element
that has no complement is still recorded, because a later element may need to
find it.

The map keeps the most recent index for a repeated value, since the `None` arm
writes with `insert` and an existing key is overwritten. When a pair is completed
by the second occurrence of a value, the index returned is the one the first
occurrence recorded, so the answer is correct. The detail matters only if the
contract changes: a caller that asks for the pair whose first index is smallest, or
for every pair, needs evidence that this function discards.

Only one pair is reported. The function returns as soon as the second element of
any pair is reached, so on an input containing several valid pairs the answer
depends on the order of the elements rather than on a property of the pairs. Two
related problems look like this one and need different code. Reporting every pair
requires the loop to continue and the map to hold every index for each value.
Reporting the pair closest to the front of the slice requires the earliest index to
be kept, which turns the `None` arm into `seen.entry(num).or_insert(idx)`.

The element type is fixed at `i32` and the index type at `usize`. Nothing in the
algorithm depends on either choice, but the signature fixes both, so a slice of
`i64`, or of a type that is not `Copy`, cannot be passed without changing the
declaration.

## Summary

- The complement of an element is determined by the target, so the search for a
  complement becomes a membership test among the elements already seen. That
  reformulation is what makes the one-pass loop possible.
- The cost is expected `O(n)` rather than guaranteed `O(n)`, and the assumption
  behind the bound is that the hash function distributes keys evenly. The worst
  case is `O(n²)` with a hasher that collides.
- `target - num` overflows on adversarial input. The expression passes every test
  written with small positive numbers and fails on the first input near `i32::MIN`.
  Chapter 9 makes the same point about the midpoint of a range.

## References

- Standard library, [`HashMap`](https://doc.rust-lang.org/std/collections/struct.HashMap.html), on the default hasher and its random seed.
- Standard library, [`HashMap::with_capacity`](https://doc.rust-lang.org/std/collections/struct.HashMap.html#method.with_capacity).
- Standard library, [`i32::checked_sub`](https://doc.rust-lang.org/std/primitive.i32.html#method.checked_sub), and [`HashMap::entry`](https://doc.rust-lang.org/std/collections/struct.HashMap.html#method.entry) for the variant that keeps the earliest index.
- The Rust Reference, [Arithmetic overflow](https://doc.rust-lang.org/reference/expressions/operator-expr.html#overflow), on the difference between debug and release builds.
