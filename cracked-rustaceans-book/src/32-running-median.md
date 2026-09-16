# 32. Running Median {#running-median}

*Source file: [`src/bin/median_finder.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/median_finder.rs). Run it with
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

<p class="listing"><span class="listing-label">Listing 32.1</span> The complete program, with its tests. <code>src/bin/median_finder.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/median_finder.rs">read the file on GitHub</a></p>

The listing is the whole file. Taken in order:

- `add_num` pushes onto `low` before rebalancing. That order means the new value is
  considered for the lower half first, and the move of `low`'s maximum to `high`
  then restores the ordering if the value belongs above the median. The second `if`
  runs only when `high` became longer, which moves one value back so `low` is never
  the shorter heap.
- `find_median` returns `Option<f64>`. `self.low.peek()?` returns `None` for an
  empty finder, so `find_median` reports absence rather than dividing by zero. When
  `low` is longer, `low`'s maximum is the median; otherwise the two tops are
  averaged.
- The median is returned as `f64` even when it is a whole number, because the two
  middle values can be a half-integer. Casting `i32` to `f64` is exact for every
  `i32`, so no precision is lost on the way in.
- `main` drives the type with the `SAMPLE` stream and prints the median after each
  insertion, which is the behaviour the chapter claims in one run.
- The tests check the empty case, one value, an even count, the ordered sequence, a
  repeated value, and the whole `SAMPLE` stream against a sort of the values seen so
  far. That last test is a differential check: it computes the median a second,
  slower way and requires the heaps to agree with it on every step. A further test
  asserts the balancing invariant itself, that the two lengths never differ by more
  than one.

## Intuition

Insert the values `1`, then `2`, then `3`:

```text
step            low (max-heap)   high (min-heap)   median
start           []               []                None
add_num(1)      [1]              []                1.0
add_num(2)      [1]              [2]               1.5
add_num(3)      [2, 1]           [3]               2.0
```

The third step in detail. `3` goes onto `low`, so `low` is `[3, 1]`. Its maximum,
`3`, moves to `high`, which becomes `[2, 3]` read as a min-heap: the top is `2`.
`high` is now longer than `low`, so its minimum, `2`, moves back and `low` becomes
`[2, 1]`. The median is `low`'s top, `2.0`.

The `SAMPLE` stream in the program produces:

```text
after  6: median 6
after 10: median 8
after  2: median 6
after  6: median 6
after  5: median 6
after  0: median 5.5
after  6: median 6
after  3: median 5.5
after  1: median 5
after  0: median 4
after  0: median 3
```

Each insertion moves at most two values between the heaps, so the two lengths never
differ by more than one and the median is always one or two heap tops away.

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

**A median is returned as `f64`, which changes the type of the answer.** For
`i32` inputs the conversion and the average are exact, but a caller that needs an
exact fraction of two integers has to compute it from the two tops rather than
from the returned value.

**There is no removal.** The structure answers the median of everything seen.
A sliding-window median needs a structure that can remove the oldest value, which
the two heaps cannot do without locating that value in one of them.

**The tests cover one stream in depth and a few cases by hand.** `SAMPLE` is
eleven values. The differential test compares against a sort, so it catches a
rebalancing error on those eleven steps, but a random or exhaustive stream would
cover more of the state space than a fixed array does.

## Summary

- Two heaps hold the lower and upper halves, and `Reverse` turns the second into
  a min-heap.
- The three-step insertion keeps the halves ordered and balanced, which is what
  makes the median a constant-time query.
- `Option<f64>` states that an empty finder has no median, instead of returning a
  sentinel.
- The program prints the median after every value of a sample stream, and the tests
  check the result against a sort of the values seen so far.

## References

- Standard library, [`BinaryHeap`](https://doc.rust-lang.org/std/collections/struct.BinaryHeap.html).
- Standard library, [`std::cmp::Reverse`](https://doc.rust-lang.org/std/cmp/struct.Reverse.html).
- Standard library, [`Option`](https://doc.rust-lang.org/std/option/enum.Option.html).
