# 3. Min Stack {#min-stack}

*Source file: [`src/problems/min_stack.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/min_stack.rs). Test it with `cargo test min_stack`.*

## Problem Statement

Implement a stack with four operations: `push`, `pop`, `top`, and `get_min`. Each
runs in `O(1)` time. The first three are the standard stack operations. `get_min`
returns the smallest value currently on the stack.

A `Vec<i32>` together with a variable holding the current minimum does not satisfy
the bound. The variable is correct while values are pushed. A `pop` that removes the
current minimum leaves the previous minimum unavailable, because the variable was
overwritten when the smaller value was pushed.

## Designing a Solution

Store the minimum at every depth. A second vector, the same length as the first,
records at index `i` the smallest value among `values[0..=i]`.

```text
values          3   1   4   1   5
mins            3   1   1   1   1
                ^   ^
                |   the smallest of 3, 1
                the smallest of 3
```

The invariant is `mins[i] == min(values[0..=i])`. Two consequences cover the
implementation. `get_min` returns the last entry of `mins`, because the last index
covers the whole stack. `pop` removes the last entry from both vectors, and the
invariant still holds for every remaining index, so nothing is recomputed.

`push` appends to `mins` either the incoming value, when it is smaller than the
current minimum, or the current minimum otherwise. Both are available in constant
time, which is where the bound comes from.

## Implementation

```rust
//! Min Stack: O(1) push, pop, top, and get_min.
//!
//! We keep a parallel `mins` stack. Each push stores the current minimum at that
//! point in history, so pop is symmetric.

#[derive(Debug, Default)]
pub struct MinStack {
    values: Vec<i32>,
    mins: Vec<i32>,
}

impl MinStack {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn push(&mut self, val: i32) {
        match self.mins.last() {
            Some(&min) if min <= val => self.mins.push(min),
            _ => self.mins.push(val),
        }
        self.values.push(val);
    }

    pub fn pop(&mut self) -> Option<i32> {
        self.mins.pop();
        self.values.pop()
    }

    pub fn top(&self) -> Option<i32> {
        self.values.last().copied()
    }

    pub fn get_min(&self) -> Option<i32> {
        self.mins.last().copied()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn stack_tracks_minimum() {
        let mut stack = MinStack::new();
        stack.push(-2);
        stack.push(0);
        stack.push(-3);
        assert_eq!(stack.get_min(), Some(-3));
        assert_eq!(stack.pop(), Some(-3));
        assert_eq!(stack.top(), Some(0));
        assert_eq!(stack.get_min(), Some(-2));
    }

    #[test]
    fn handles_duplicates() {
        let mut stack = MinStack::new();
        stack.push(1);
        stack.push(1);
        stack.pop();
        assert_eq!(stack.get_min(), Some(1));
    }
}
```

`MinStack::new` returns `Self::default()`, so the constructor and the `Default`
implementation cannot disagree.

`push` matches on the last entry of `mins` with a guard. `Some(&min) if min <= val`
handles a non-empty stack whose incoming value is not smaller, and repeats the
previous minimum. The underscore arm covers the empty stack and the strictly smaller
value; in both, the value pushed is `val`.

The comparison is `<=` rather than `<`. With `<` the arms remain correct for the
minimum, because equal values give the same answer. The choice matters for the
variant that stores counts, where equality with the current minimum increments the
count instead of appending an entry.

`pop` removes the last entry of each vector and returns the value from the first.
Both vectors lose one element per call, so the equal-length invariant holds by
construction, and the discarded entry of `mins` is never read.

`top` and `get_min` use `copied`, which turns `Option<&i32>` into `Option<i32>`.
Without it the returned reference would borrow the stack and prevent a push while
the result is held.

## Intuition

```text
call              values          mins              returns
push(-2)          [-2]            [-2]              -
push(0)           [-2, 0]         [-2, -2]          -
push(-3)          [-2, 0, -3]     [-2, -2, -3]      -
get_min()         [-2, 0, -3]     [-2, -2, -3]      Some(-3)
pop()             [-2, 0]         [-2, -2]          Some(-3)
top()             [-2, 0]         [-2, -2]          Some(0)
get_min()         [-2, 0]         [-2, -2]          Some(-2)
pop()             [-2]            [-2]              Some(0)
pop()             []              []                Some(-2)
get_min()         []              []                None
```

The trace exercises the case a single tracked minimum would fail. After `-3` is
popped, `get_min` reports `-2`, which was the second smallest value. A single
tracked minimum would report `-3`, a value no longer on the stack.

The second test pushes two equal values and pops one. The minimum after the pop is
still that value, because the surviving entry records it.

## Time and Space Complexity

| Operation | Time | Space |
|---|---|---|
| `push` | `O(1)` amortised | one `i32` in each vector |
| `pop` | `O(1)` | releases one `i32` from each vector |
| `top` | `O(1)` | none |
| `get_min` | `O(1)` | none |

Push is amortised rather than constant because a `Vec` occasionally reallocates and
moves its elements. The capacity doubles, so `n` pushes perform `O(n)` total
movement.

The structure stores two integers per element to hold one. A stack of one million
entries occupies eight megabytes instead of four. The alternative under Limitations
stores a pair per run of equal minima, which uses less space when the minimum
repeats and no more when it does not.

## Limitations

The memory overhead is proportional to the number of elements, not to the number of
distinct minimum values. An increasing sequence changes the minimum on every push
and records a distinct value each time. A sequence whose minimum never changes
records the same value repeatedly, and the second vector is redundant. A design that
stores `(value, repeat_count)` pairs, appending only when the minimum strictly
decreases and incrementing the count when it repeats, holds fewer entries on inputs
with repeated minima and never more than one entry per element. That variant is not
implemented here.

`pop` on an empty stack returns `None` and changes nothing. `top` and `get_min` also
return `None` on an empty stack, so an empty stack reports no minimum rather than a
minimum of zero.

The structure has no `len` and no `is_empty`, and both fields are private, so the
depth is not observable outside the module. A caller can push, pop, read the top and
read the minimum, and nothing else. An application that needs the depth has to track
it separately.

The value type is `i32`. Making the structure generic over a type `T: Ord` requires
a type parameter on the struct, the implementation, and both vectors; the comparison
in `push` is the only operation that needs the bound. The second vector stores cloned
values, which would also require `Clone`.

`push` appends to `mins` before `values`. If the second append could fail, the
vectors would differ in length and the invariant would break. Rust aborts the process
on allocation failure, so the case is unreachable through this function. The
invariant holds because of the order of two adjacent statements, which the compiler
does not check.

## References

- Standard library, [`Vec::last`](https://doc.rust-lang.org/std/vec/struct.Vec.html#method.last).
- Standard library, [`Option::copied`](https://doc.rust-lang.org/std/option/enum.Option.html#method.copied), on the conversion from a borrowed to an owned value.
- Standard library, [`Vec::push`](https://doc.rust-lang.org/std/vec/struct.Vec.html#method.push), on the amortised cost of growth.
