<img class="plate" src="art/ch32.png" alt="Sweeper, the robot who reads the city one edge at a time, beside a vertical sweep line passing over a row of buildings">

# Sweep-line algorithms

<div class="covers" markdown="1">

This chapter covers

- Transforming 2D geometric envelope queries into a 1D sorted event stream
- Deriving the active-set data structure (`BTreeMap` multiset) when `BinaryHeap` cannot delete arbitrary elements
- Encoding tie-breaking invariants via derived `Ord` to prevent degenerate skyline key points
- Implementing and tracing the skyline algorithm in O(n log n) time and O(n) space

</div>

Numerous problems in computational geometry ask for an aggregate property across every coordinate along an axis:
which intervals cover a timestamp, which overlapping rectangle defines the upper contour at coordinate *x*, or
which pairs of line segments intersect. Evaluating that property by testing all *n* geometric primitives at every
candidate coordinate yields an O(*n*²) quadratic algorithm. A **sweep-line** algorithm eliminates redundant work by
advancing an imaginary vertical line *x = t* monotonically from left to right and halting exclusively at discrete
**event points** where the combinatorial structure can change. Between consecutive events, the subset of primitives
intersecting the sweep line, termed the **active set** (or sweep-line status), remains invariant.

Michael Shamos and Dan Hoey introduced the plane-sweep method in 1976 to detect segment intersections in O(*n* log *n*)
time, and Jon Bentley and Thomas Ottmann generalized it in 1979 to report all *k* intersections in
O((*n* + *k*) log *n*) time. Since then, plane sweeping has served as a foundational algorithmic framework across
VLSI design-rule verification, graphics rasterization, and spatial indexing. This chapter develops a sweep-line
solution for the classical skyline problem, deriving both its active-set representation and its event-ordering
invariants directly from the geometry of the output.

## 32.1 The skyline problem

**Problem formulation.** Given *n* axis-aligned rectangular buildings resting on a common baseline `y = 0`, each
specified by a triple `[left, right, height]` with `left < right` and `height > 0`, compute the **skyline**: the
upper envelope of the union of all rectangles. Formally, the skyline defines a right-continuous, piecewise-constant
step function:

```text
H(x) = max({0} ∪ { h_i : left_i <= x < right_i })
```

Because *H*(*x*) is constant between discontinuities, the output encodes the silhouette minimally as an ordered
sequence of **key points** `[x, H(x)]`, emitting one point at every abscissa *x* where *H*(*x*) jumps to a new
value (with no two consecutive key points sharing the same height). For the five buildings `[2, 9, 10]`,
`[3, 7, 15]`, `[5, 12, 12]`, `[15, 20, 10]`, and `[19, 24, 8]`, the upper envelope consists of seven key points:
`[2, 10]`, `[3, 15]`, `[7, 12]`, `[12, 0]`, `[15, 10]`, `[20, 8]`, and `[24, 0]` (Figure 32.1).

<figure>
<img src="figures/ch32-skyline.svg" alt="Five shaded buildings on an x axis from 0 to 25: [2, 9, 10], [3, 7, 15], [5, 12, 12], [15, 20, 10] and [19, 24, 8]. A thick outline follows the tallest building at every x. Seven key points are marked on the outline: [2, 10], [3, 15], [7, 12], [12, 0], [15, 10], [20, 8] and [24, 0].">
<figcaption><b>Figure 32.1</b> 5 buildings and their skyline. A key point marks every change in the height of the outline.</figcaption>
</figure>

**Quadratic baseline.** Because *H*(*x*) can change only at a building's vertical boundary, evaluating *H*(*x*) by
scanning all *n* buildings at each of the `2n` distinct boundary coordinates produces the exact silhouette, but at
O(*n*) cost per boundary and O(*n*²) overall time.

**Sweep-line reduction.** Decomposing each rectangle `[left, right, height]` into two boundary events transforms
the 2D spatial problem into a 1D chronological scan over `2n` events sorted by coordinate: a left edge inserts
`height` into the active set, and a right edge deletes `height`. Immediately after processing each event at
coordinate *x*, the maximum element of the active set equals *H*(*x*). Comparing that maximum against the previous
emitted height `prev_max` detects every true discontinuity of *H*(*x*) in a single pass.

## 32.2 An ordered multiset of active heights

The sweep-line status structure must satisfy three operational contracts:

1. **Insert** a building's height upon crossing its left boundary.
2. **Delete** one specific height upon crossing its right boundary.
3. **Query the maximum** among all currently active heights.

Rust's `BinaryHeap` (chapter 5) satisfies insertion in O(log *n*) time and maximum inspection in O(1) time, but its
implicit heap array provides no O(log *n*) deletion of an arbitrary interior value. To support arbitrary deletion
cleanly, we represent the active set as a **multiset** backed by `BTreeMap<i32, i32>`, mapping each active height
key to its multiplicity (the count of currently spanning buildings of that height). Multiplicity tracking preserves
correctness when two overlapping buildings share the same elevation: retiring one building decrements the count
without erasing the height still sustained by the surviving building.

Because `BTreeMap` maintains keys in sorted order inside a cache-friendly B-tree, insertion, deletion, and extremum
retrieval (`keys().next_back()`) all execute in O(log *n*) time. Seeding the map with the sentinel `(0, 1)` models
the infinite ground plane at `y = 0`. Since no `End` event ever removes height `0`, the map remains strictly
non-empty throughout the sweep, and the maximum automatically returns to `0` whenever the last active building in a
contiguous cluster terminates.

## 32.3 Events at the same coordinate

Each building contributes two tuples, `(left, Event::Start(Reverse(height)))` and `(right, Event::End(height))`.
Sorting these `2n` tuples orders events primarily by coordinate *x*. When multiple edges coincide at the same
abscissa *x*, however, processing them in arbitrary order corrupts the right-continuous step function *H*(*x*) by
introducing transient, zero-width spikes or redundant steps.

Rust's `#[derive(Eq, PartialEq, Ord, PartialOrd)]` on `Event` resolves coincident edges deterministically through
three lexicographical ordering invariants:

1. **Starts precede ends (`Start` declared before `End`).** Derived `Ord` ranks enum variants in declaration order,
   so every entering building at *x* enters the active set before any departing building at *x* leaves it. When two
   buildings of equal height abut along a shared wall (for example, `[0, 5, 10]` and `[5, 8, 10]`), inserting the
   second height-10 building first increments the count from 1 to 2 before the first building decrements it back to
   1. The maximum stays continuously at 10, preventing a spurious drop to `[5, 0]` followed by a false climb back
   to `[5, 10]`.
2. **Tallest starts first (`Start(Reverse(height))`).** Wrapping the start height in `Reverse` sorts taller
   entering buildings ahead of shorter ones at the same *x*. The tallest building elevates the active maximum
   immediately on the first event, emitting one upward transition; subsequent shorter starts at *x* leave the
   maximum unchanged and emit nothing. Without `Reverse`, ascending heights would emit a staircase of false
   intermediate key points at the same abscissa *x*.
3. **Shortest ends first (`End(height)`).** Comparing departure heights in natural ascending order removes shorter
   buildings before taller ones at the same *x*. While the tallest departing building remains in the active set,
   removing shorter buildings leaves the maximum unchanged; only removing the final tallest building lowers the
   maximum and emits the single true downward transition.

Together, these three rules guarantee that processing events one by one produces the exact canonical silhouette
without requiring a post-processing pass to deduplicate coincident *x*-coordinates.

## 32.4 A trace

The table below traces all 10 sorted events for the five buildings in Figure 32.1, recording the sorted multiset of
active heights, the resulting maximum *H*(*x*), and each emitted key point:

| `x` | Event | Active heights | Maximum | Key point |
|---|---|---|---|---|
| 2 | `Start(Reverse(10))` | 0, 10 | 10 | `[2, 10]` |
| 3 | `Start(Reverse(15))` | 0, 10, 15 | 15 | `[3, 15]` |
| 5 | `Start(Reverse(12))` | 0, 10, 12, 15 | 15 | |
| 7 | `End(15)` | 0, 10, 12 | 12 | `[7, 12]` |
| 9 | `End(10)` | 0, 12 | 12 | |
| 12 | `End(12)` | 0 | 0 | `[12, 0]` |
| 15 | `Start(Reverse(10))` | 0, 10 | 10 | `[15, 10]` |
| 19 | `Start(Reverse(8))` | 0, 8, 10 | 10 | |
| 20 | `End(10)` | 0, 8 | 8 | `[20, 8]` |
| 24 | `End(8)` | 0 | 0 | `[24, 0]` |

At `x = 5`, inserting height 12 into `{0, 10, 15}` leaves the maximum unchanged at 15, so the building remains
occluded behind the taller tower until `x = 7`, when `End(15)` removes 15 from the active set and exposes height
12 as the new silhouette boundary `[7, 12]`.

## 32.5 The program

<p class="listing"><b>Listing 32.1</b> The skyline with a sweep line and an ordered multiset. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/skyline_problem.rs">src/bin/skyline_problem.rs</a></p>

```rust
{{#include ../../rust-interview-lab/src/bin/skyline_problem.rs}}
```

```text
$ cargo run --bin skyline_problem
[[2, 10], [3, 15], [7, 12], [12, 0], [15, 10], [20, 8], [24, 0]]
```

Key implementation details in Listing 32.1:

- **Event expansion.** `flat_map` projects each `[left, right, height]` input slice into a stack-allocated
  two-element event array, collecting exactly `2n` entries into `events`.
- **Unstable sorting.** Calling `sort_unstable()` avoids auxiliary merge buffers without sacrificing correctness:
  two events compare equal only when they have identical `(x, variant, height)` triples, so permuting equal events
  produces identical multiset updates.
- **Multiplicity eviction.** In the `End(h)` branch, `active.entry(h).or_default()` yields `&mut i32` to the count
  of height `h`. Once decrementing brings the count to `0`, `active.remove(&h)` purges the key so `next_back()`
  never observes an expired elevation. The commented alternative expresses the same update through `get_mut` and
  `is_some_and`, avoiding an extra entry lookup when the key is guaranteed present.
- **Let-chain guard.** The condition `if let Some(&curr_max) = active.keys().next_back() && curr_max != prev_max`
  employs a **let chain** (stabilized in Rust 1.88 under the 2024 edition), evaluating the inequality predicate
  strictly when pattern matching succeeds and keeping `curr_max` bound in the same guard expression.

**Complexity.** Sorting `2n` event tuples takes O(*n* log *n*) time. During the sweep, each event executes one
B-tree insertion or deletion and one maximum lookup, each costing O(log *n*) time. Total runtime is therefore
O(*n* log *n*), with O(*n*) auxiliary memory for the event vector and active multiset.

<div class="summary" markdown="1">

## Summary

- A sweep-line algorithm reduces 2D spatial queries to a 1D scan over sorted event points where the active set can
  change; between adjacent events, the sweep-line status stays constant.
- Modeling the skyline as the upper envelope of *n* rectangles turns the `2n` vertical edges into start and end
  events, emitting a key point whenever the active maximum changes.
- Because `BinaryHeap` lacks O(log *n*) arbitrary deletion, a reference-counted `BTreeMap<i32, i32>` provides the
  required ordered multiset operations in O(log *n*) time, anchored by the permanent ground sentinel `(0, 1)`.
- Encoding start-before-end, descending start height, and ascending end height into `Event`'s derived `Ord`
  guarantees canonical key points at coincident *x*-coordinates without post-processing.
- The algorithm executes in O(*n* log *n*) time and O(*n*) space.

</div>

## Exercises

1. Reimplement `get_skyline` using a `BinaryHeap<i32>` paired with lazy deletion: maintain a `HashMap<i32, i32>` of
   pending retired heights and discard stale entries from the top of the heap before reading the maximum. Verify
   that the seven key points of section 32.4 match exactly, and compare worst-case space against the `BTreeMap`
   design.
2. Swap the declaration order of `Start` and `End` in `Event` and execute the binary on the abutting roofs
   `[0, 5, 10]` and `[5, 8, 10]`. Trace how the active set evolves at `x = 5` and explain each spurious key point
   emitted.
3. Apply the sweep-line method to compute the peak concurrency of a set of half-open meeting intervals
   `[start, end)`. Prove whether an `End` event at coordinate `x` must sort before or after a `Start` event at the
   same coordinate `x`.
4. Extend Listing 32.1 to compute the total union area of the buildings in Figure 32.1 by integrating the
   piecewise-constant skyline `H(x)` across consecutive key points.
