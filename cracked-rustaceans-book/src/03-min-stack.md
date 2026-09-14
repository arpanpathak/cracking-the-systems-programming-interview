# 3. Min Stack {#min-stack}

*Source file: [`src/problems/min_stack.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/min_stack.rs). Test it with `cargo test min_stack`.*

## Problem Statement

Support four operations on a stack, `push`, `pop`, `top`, and `get_min`, with
each of them in constant time. The first three are what a stack always provides.
The fourth is the whole problem: the smallest value currently in the stack, also in
constant time.

A single vector of values cannot do it. The minimum of the stack is easy to track
while values are only added: keep a running smallest value and update it on each
push. Popping destroys it. When the smallest value leaves the stack, the next
smallest is whatever the second smallest was at that moment, and that value was
overwritten by the running minimum when the smaller one arrived. The information
needed to answer the question after a pop is information the running minimum
discarded.

## Designing a Solution

The fix is to stop tracking one minimum and start recording the minimum at every
depth. Keep a second vector, the same length as the first, in which entry `i` holds
the smallest value among the first `i + 1` entries of the stack.

```text
values          3   1   4   1   5
mins            3   1   1   1   1
                ^   ^
                |   the smallest of 3, 1
                the smallest of 3
```

The invariant is the sentence

> `mins[i]` is the minimum of `values[0..=i]`.

Two facts follow from it, and between them they explain the whole implementation.
The answer to `get_min` is the last entry of `mins`, because the last index covers
the whole stack. And `pop` can remove the last entry of each vector and remain
consistent, because after removing index `i` from both, the invariant still holds
for every remaining index. Nothing has to be recomputed, because what was recorded
at each depth happens to be exactly what is needed at that depth.

Push does not compute a minimum; it records the decision that was made at the new
depth. The value appended to `mins` is either the incoming value, if it is smaller
than everything already there, or the previous minimum, if it is not. Both are
available in constant time, which is where the constant time bound comes from.

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
implementation cannot drift apart. The derive provides `Default`, and `new` is the
name callers expect.

`push` matches on the last entry of `mins` with a guard. `Some(&min) if min <= val`
handles the case where the stack is non-empty and the incoming value is not
smaller, in which case the previous minimum is repeated. The underscore arm covers
both remaining cases at once: the stack is empty, so there is no previous minimum,
or the incoming value is strictly smaller, so it becomes the new minimum. In both,
the value pushed is `val`.

The comparison is `<=` rather than `<`. With `<` the two arms would still be
correct for the minimum, because equal values give the same answer. The choice
matters for the variant that stores counts, where equality against the current
minimum is what increments the count instead of appending an entry.

`pop` discards the last entry of each vector and returns the value from the first.
Both vectors lose exactly one element per call, so the equal-length invariant is
maintained by construction, and the discarded entry of `mins` is never read.

`top` and `get_min` use `copied`, which turns `Option<&i32>` into `Option<i32>` by
copying the value out of the reference. Without it the returned `&i32` would borrow
the stack, and a caller could not push while holding the result, a restriction
that a four-line accessor should not impose.

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

The sequence in the test suite exercises the case the running-minimum design would
fail: after `-3` is popped, `get_min` reports `-2`, the value that was second
smallest. A single tracked minimum would still report `-3`, a value no longer in
the stack.

The second test covers equality. Two equal values are pushed and one is popped; the
minimum after the pop is still that value, because the surviving entry also records
it. Both vectors held two entries and one remains, so the derivation of the
invariant is unaffected by the repetition.

## Time and Space Complexity

| Operation | Time | Space |
|---|---|---|
| `push` | `O(1)` amortised | one `i32` in each vector |
| `pop` | `O(1)` | releases one `i32` from each vector |
| `top` | `O(1)` | none |
| `get_min` | `O(1)` | none |

Push is amortised rather than constant because a `Vec` occasionally reallocates and
moves its elements. The event is rare and the capacity doubles, so `n` pushes
perform `O(n)` total movement, which is the amortised `O(1)` the caller receives.

The structure stores two integers per element to hold one. For a stack of a million
entries that is eight megabytes instead of four. The overhead is the price of the
constant time minimum, and it is the measurement to give when someone asks what the
approach costs. The alternative is described under failure modes: it stores a pair
per *run* of equal minimum values rather than a value per element, which is smaller
when the minimum repeats and equal to or larger than this design when it does not.

## Limitations

The memory overhead is proportional to the number of elements rather than to the
number of distinct minimum values. A stack whose minimum changes on every push,
which is what an increasing sequence produces, records the incoming value every
time, and both vectors hold distinct entries. A stack whose minimum never changes
records the same value repeatedly, and the second vector is redundant. A design that
stores `(value, repeat_count)` pairs, appending an entry only when the minimum
strictly decreases and incrementing the count when it is repeated, holds fewer
entries on inputs with repeated minima and never more than one entry per element.
That variant is not implemented here, and the gain appears only on inputs where the
minimum repeats.

Pop on an empty stack returns `None` and changes nothing: `Option::pop` on an empty
`Vec` returns `None` without panicking, and both vectors are left empty. `top` and
`get_min` also return `None` on an empty stack, so an empty stack reports no minimum
rather than a minimum of zero, which is the distinction that a sentinel value would
lose.

The structure has no `len` and no `is_empty`. A caller cannot ask how many entries
the stack holds, and the two fields are private, so the depth is not observable from
outside the module. A caller can push, pop, read the top and read the minimum, and
nothing else; an application that needs the depth has to track it alongside the
structure, or wait for the accessor to be added.

The value type is `i32`. Making the structure generic over a type `T` with the
`Ord` bound requires a type parameter on the struct, the implementation, and the two
vectors, and the comparison in `push` is the only operation that needs the bound.
Nothing in the algorithm depends on the values being integers, and nothing in it
depends on `Copy` either: the second vector stores cloned values, which would need a
`Clone` bound on the same type parameter.

The order of the two pushes in `push`, `mins` first, then `values`, is an aspect
of the invariant that the type system does not enforce. The code appends to `mins`
before it appends to `values`, so if the second append could fail, the vectors would
differ in length and the invariant would be broken. In Rust an allocation failure
aborts the process rather than returning an error, so the case is not reachable
through this function. The invariant holds because of the order of two adjacent
statements rather than because of anything the compiler checks, and a reader
verifying the structure should know that.

## Summary

- The invariant is that `mins[i]` is the minimum of `values[0..=i]`. Every question
  about the design follows from it.
- A single tracked minimum is not sufficient: the value that the running minimum
  overwrites is the value needed after the pop, which is the problem the parallel
  vector solves.
- The cost is constant amortised time and two integers per element. The time bound
  alone does not decide whether the structure is usable for a large stack.
- The `(value, count)` pair is an alternative that occupies less memory when
  consecutive values repeat, and the shape of the input decides between the two
  designs. Only the bound changes if the variant is requested.

## References

- Standard library, [`Vec::last`](https://doc.rust-lang.org/std/vec/struct.Vec.html#method.last).
- Standard library, [`Option::copied`](https://doc.rust-lang.org/std/option/enum.Option.html#method.copied), on the conversion from a borrowed to an owned value.
- Standard library, [`Vec::push`](https://doc.rust-lang.org/std/vec/struct.Vec.html#method.push), on the amortised cost of growth.
