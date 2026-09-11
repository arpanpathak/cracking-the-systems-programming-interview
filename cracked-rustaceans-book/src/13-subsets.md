# 13. Subsets {#subsets}

*Source file: [`src/problems/backtracking.rs`](../../rust-interview-lab/src/problems/backtracking.rs). Test it with
`cargo test backtracking`.*

## Problem Statement

Given a list of distinct values, return every subset. A list of `n` values has
`2^n` subsets, because each value is independently either present or absent, and
the empty subset and the whole list are both included.

## Designing a Solution

Backtracking walks a sequence of decisions. At each step the algorithm holds a
partial selection and a position, records the selection, and then tries every
value from that position onward as the next member. After each trial it undoes the
choice, which is what allows the next trial to start from the same state.

```text
values = [1, 2, 3]

                       []                       record []
         +--------------+---------------+
         |              |               |
       [1]             [2]             [3]      record each
    +----+----+         |
    |         |         |
  [1,2]     [1,3]     [2,3]                     record each
    |
 [1,2,3]                                        record it

8 records: [], [1], [2], [3], [1,2], [1,3], [2,3], [1,2,3]
```

The invariant that makes the undo step correct is: on entry to the recursive call,
`selection` holds a prefix of a decision sequence; on exit it holds exactly what it
held on entry. Every branch therefore starts from a state that the branches before
it did not disturb.

The restriction that each recursive call may only choose a value at or after
`start` is what prevents `[1, 2]` and `[2, 1]` from both appearing. The output is
ordered by index, not by value.

## Implementation

```rust
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
```

`fn backtrack(...)` is a nested function inside `subsets`. A nested `fn` does not
capture its environment, so the values it needs are passed as parameters:
`nums`, `start`, `path`, and `result`. That is why the signature is longer than the
body: the parameters replace the closure capture that a nested `fn` cannot have.

`result.push(path.clone())` records the current selection. The clone is required
because `path` is reused for the rest of the search; all `2^n` recorded subsets are
independent vectors.

`backtrack(&nums, idx + 1, path, result)` passes `idx + 1`, not `start + 1`. Each
chosen value advances the lower bound past itself, so a value cannot be chosen
twice and the indices in a subset always increase.

`path.pop()` after the recursive call restores the invariant. Removing that line
makes the selection grow for the remainder of the search, and the output would
contain subsets that were never selected.

## Intuition

```text
subsets(vec![1, 2, 3])

call                     path       recorded        loop
backtrack(nums, 0)       []         []              idx 0, 1, 2
  push nums[0] = 1       [1]
  backtrack(nums, 1)     [1]        [1]             idx 1, 2
    push nums[1] = 2     [1, 2]
    backtrack(nums, 2)   [1, 2]     [1, 2]          idx 2
      push nums[2] = 3   [1, 2, 3]
      backtrack(nums, 3) [1, 2, 3]  [1, 2, 3]       loop does not run
      pop                [1, 2]
    pop                  [1]
    push nums[2] = 3     [1, 3]
    backtrack(nums, 3)   [1, 3]     [1, 3]          loop does not run
    pop                  [1]
  pop                    []
  push nums[1] = 2       [2]
  backtrack(nums, 2)     [2]        [2]             idx 2
    push nums[2] = 3     [2, 3]
    backtrack(nums, 3)   [2, 3]     [2, 3]
    pop                  [2]
  pop                    []
  push nums[2] = 3       [3]
  backtrack(nums, 3)     [3]        [3]
  pop                    []

recorded, in order: [], [1], [1,2], [1,2,3], [1,3], [2], [2,3], [3]
```

## Time and Space Complexity

| Resource | Cost | Condition |
|---|---|---|
| Time | `O(2^n × n)` | one clone of the selection per recorded subset, of length up to `n` |
| Space | `O(2^n × n)` | the output dominates; the stack is `O(n)` |

The clone is the reason for the extra factor of `n`. A caller that only needs to
visit each subset can pass a closure instead of collecting them, which removes the
factor.

## Limitations

**The capacity hint overflows for large inputs.** `Vec::with_capacity(1 <<
nums.len())` evaluates `1 << nums.len()` as a `usize`. For a list of 64 or more
values on a 64-bit target, the shift is not representable and panics in a debug
build. The panic happens on an input the function is otherwise able to accept: the
recursion itself has no such limit, and the allocation would fail long before the
work finished. The hint is a promise the code cannot keep.

**A list of 40 values cannot be enumerated at all.** `2^40` subsets is about a
trillion vectors, and the output alone would exceed any machine's memory. The
function has no bound on the input size and no way to report that the work is
impossible, so the caller has to know.

**Duplicate values produce duplicate-looking subsets.** The function takes a list
and treats every position as distinct, so `subsets(vec![1, 1, 1])` returns eight
subsets (five of them empty-looking). The documentation says "distinct integers",
which is a precondition the type does not enforce.

**The output order is an implementation detail, and one test depends on it.**
`empty_input_has_one_subset` compares the whole output, which is safe for one
element. The other test sorts before comparing, which is the right pattern;
`generates_all_subsets` follows it.

**There is no way to stop the search early or to stream the results.** A caller
that wants the first `k` subsets, or wants to search for a subset with a property,
must collect all of them first.

## Summary

- The recording happens at the start of each call, before the loop. That is what
  produces the empty subset and what makes every node of the recursion tree
  correspond to one output.
- The output is `2^n` subsets, and cloning the working path into each one adds a
  factor of `n`. Replacing the collected vectors with a visitor closure removes the
  factor, which is a change of interface rather than a micro-optimisation.
- The `push` and `pop` pair is a single operation. The `pop` is what makes the next
  branch independent, not cleanup after the current one.
- The input size is unbounded. A list of 40 values produces about a trillion
  subsets, and the capacity hint `1 << nums.len()` overflows for 64 values on a
  64-bit target.
- The documentation states "distinct integers" as a precondition the type does not
  enforce, so repeated values produce repeated-looking subsets.

## References

- Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, and Clifford Stein,
  *Introduction to Algorithms*, 4th edition, MIT Press, 2022, Section 5.3, on
  recurrences, and Chapter 14 on the same recursive-search structure.
- Standard library, [`Vec::clone`](https://doc.rust-lang.org/std/vec/struct.Vec.html#method.clone).
- Standard library, [`Vec::with_capacity`](https://doc.rust-lang.org/std/vec/struct.Vec.html#method.with_capacity).
