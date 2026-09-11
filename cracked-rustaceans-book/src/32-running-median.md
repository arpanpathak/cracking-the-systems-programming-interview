# 32. Running Median {#running-median}

*Source file: [`src/bin/median_finder.rs`](../../rust-interview-lab/src/bin/median_finder.rs). Run it with
`cargo run --bin median_finder`.*

## Problem Statement

Accept a stream of numbers one at a time and report the median of everything seen
so far after each insertion. The median is the middle value when the count is odd
and the average of the two middle values when it is even. Resorting the values on
every query is the obvious answer and the wrong one; the type has to maintain the
median as the stream arrives.

## Designing a Solution

Two heaps split the values into a lower half and an upper half. `low` is a
`BinaryHeap<i32>`, which is a max-heap, so its top is the largest value in the
lower half. `high` is a `BinaryHeap<Reverse<i32>>`, and `Reverse` flips the
ordering, so its top is the smallest value in the upper half. `BinaryHeap` is
already a priority queue; `Reverse` is the wrapper that gives the second one the
opposite ordering.

Two invariants keep the halves together:

- every value in `low` is less than or equal to every value in `high`;
- `low.len()` equals `high.len()`, or exceeds it by one.

If both hold, the median is `low.peek()` when `low` is longer, and the average of
the two tops otherwise. The insertion maintains them in three steps: push onto
`low`, move `low`'s maximum to `high` so the halves stay ordered, and move `high`'s
minimum back if `high` has grown too large.

## Implementation

```rust
use std::cmp::Reverse;
use std::collections::BinaryHeap;

#[derive(Default)]
pub struct MedianFinder {
    low: BinaryHeap<i32>,
    high: BinaryHeap<Reverse<i32>>,
}

impl MedianFinder {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn add_num(&mut self, num: i32) {
        self.low.push(num);

        if let Some(val) = self.low.pop() {
            self.high.push(Reverse(val));
        }

        if self.high.len() > self.low.len() {
            if let Some(Reverse(val)) = self.high.pop() {
                self.low.push(val);
            }
        }
    }

    pub fn find_median(&self) -> Option<f64> {
        let max_low = *self.low.peek()?;

        if self.low.len() > self.high.len() {
            Some(max_low as f64)
        } else {
            let Reverse(min_high) = *self.high.peek()?;
            Some((max_low as f64 + min_high as f64) / 2.0)
        }
    }
}

fn main() {
    todo!("TODO TODO")
}
```

The file's `main` is a placeholder, so the listing ends at the implementation.
The type is exercised through `add_num` and `find_median`.

`add_num` pushes onto `low` before rebalancing. That order means the new value is
considered for the lower half first, and the move of `low`'s maximum to `high`
then restores the ordering if the value belongs above the median. The second
`if` runs only when `high` became longer, which moves one value back so `low` is
never the shorter heap.

`find_median` returns `Option<f64>`. `self.low.peek()?` returns `None` for an
empty finder, so `find_median` reports absence rather than dividing by zero. When
`low` is longer, `low`'s maximum is the median; otherwise the two tops are
averaged.

The median is returned as `f64` even when it is a whole number, because the two
middle values can be a half-integer. Casting `i32` to `f64` is exact for every
`i32`, so no precision is lost on the way in; the average of two integers is the
only value that can be fractional, and it is exact as well for `i32` inputs.

## Intuition

Insert the values `1`, then `2`, then `3`:

```text
step            low (max-heap)   high (min-heap)   median
start           []               []                None
add_num(1)      [1]              []                1.0
add_num(2)      [1]              [2]               1.5
add_num(3)      [2, 1]           [3]               2.0

add_num(1)      push 1 onto low        low = [1]
                move the maximum       low = [], high = [1]
                high not longer        low = [], high = [1]
                low is empty, so find_median returns None
```

Insert `2` next from that state:

```text
add_num(2)      push 2 onto low        low = [2]
                move the maximum       low = [], high = [1, 2]
                high is longer         pop 1 back to low
                                       low = [1], high = [2]   median = 1.5
```

Each insertion moves at most two values between the heaps, so the two lengths
never differ by more than one.

## Time and Space Complexity

| Operation | Cost | Condition |
|---|---|---|
| `add_num` | `O(log n)` | two heap pushes and at most two pops |
| `find_median` | `O(1)` | the median is one or two heap tops |
| memory | `O(n)` | every value is stored once |

The alternative, keeping a sorted `Vec` and re-sorting on each query, costs
`O(n log n)` per insertion. Sorting once per query and caching the result trades
that for `O(1)` queries but still pays `O(n log n)` when the stream continues.

## Limitations

**The type is fixed to `i32`.** The heaps are `BinaryHeap<i32>`, so the caller
cannot use `i64` or `f64`. Making the type generic needs an ordering bound plus a
way to average two values, which is more than `Ord` provides.

**The file's `main` is a placeholder.** Nothing runs when the program starts, so
the type is only reachable from a test or from another program. `cargo run --bin
median_finder` exits without output.

**The file has no tests.** The invariant that the two heaps stay balanced is the
part worth testing, and it is not asserted anywhere in the file. A test that adds
a sequence and checks the median after each step would catch a rebalancing error
that a single query does not.

**A median is returned as `f64`, which changes the type of the answer.** For
`i32` inputs the conversion and the average are exact, but a caller that needs an
exact fraction of two integers has to compute it from the two tops rather than
from the returned value.

**There is no removal.** The structure answers the median of everything seen.
A sliding-window median needs a structure that can remove the oldest value, which
the two heaps cannot do without locating that value in one of them.

## Summary

- Two heaps hold the lower and upper halves, and `Reverse` turns the second into
  a min-heap.
- The three-step insertion keeps the halves ordered and balanced, which is what
  makes the median a constant-time query.
- `Option<f64>` states that an empty finder has no median, instead of returning a
  sentinel.
- The type is concrete rather than generic, and its `main` and tests are absent.

## References

- Standard library, [`BinaryHeap`](https://doc.rust-lang.org/std/collections/struct.BinaryHeap.html).
- Standard library, [`std::cmp::Reverse`](https://doc.rust-lang.org/std/cmp/struct.Reverse.html).
- Standard library, [`Option`](https://doc.rust-lang.org/std/option/enum.Option.html).
