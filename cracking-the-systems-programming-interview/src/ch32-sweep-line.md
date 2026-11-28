<img class="plate" src="art/ch32.png" alt="Sweeper, the robot who reads the city one edge at a time, beside a vertical sweep line passing over a row of buildings">

# Sweep-line algorithms

<div class="covers" markdown="1">

This chapter covers

- Reducing a geometric problem to a sequence of events sorted by coordinate
- Keeping the active set in a `BTreeMap` used as an ordered multiset, when a `BinaryHeap` cannot remove an arbitrary element
- Ordering events at the same coordinate so that no false key point is emitted
- The skyline problem, traced event by event, in O(n log n) time

</div>

In many problems about intervals, rectangles and segments, 1 question is posed at every point of a line. Examples are which intervals cover a coordinate, which rectangle is tallest there, and which segments cross. In a direct solution, the question is evaluated at every coordinate of interest against every object, at a cost of O(n²) for n objects. With a **sweep line**, this cost is reduced. An imaginary vertical line is moved from left to right and stopped only where the answer can change. Each stop is called an **event**, and the objects crossed by the line between 2 events form the **active set**.

Michael Shamos and Dan Hoey applied the technique to the detection of intersecting line segments in 1976, and Jon Bentley and Thomas Ottmann extended it to report every intersection in 1979. It has been a standard method of computational geometry since then. In this chapter, we develop a sweep line for the skyline problem, and we choose the data structure for the active set from the operations required by the sweep.

## 32.1 The skyline problem

**The problem.** A city is described by rectangular buildings that stand on a common ground line. Each building is given as `[left, right, height]`, with `left < right` and `height > 0`. The **skyline** is the outline that the buildings form when the city is viewed from a distance. It is reported as a list of **key points** `[x, height]`. A key point is emitted at every x-coordinate where the height of the outline changes. For the 5 buildings `[2, 9, 10]`, `[3, 7, 15]`, `[5, 12, 12]`, `[15, 20, 10]` and `[19, 24, 8]`, the skyline consists of 7 key points: `[2, 10]`, `[3, 15]`, `[7, 12]`, `[12, 0]`, `[15, 10]`, `[20, 8]` and `[24, 0]` (figure 32.1).

<figure>
<img src="figures/ch32-skyline.svg" alt="Five shaded buildings on an x axis from 0 to 25: [2, 9, 10], [3, 7, 15], [5, 12, 12], [15, 20, 10] and [19, 24, 8]. A thick outline follows the tallest building at every x. Seven key points are marked on the outline: [2, 10], [3, 15], [7, 12], [12, 0], [15, 10], [20, 8] and [24, 0].">
<figcaption><b>Figure 32.1</b> 5 buildings and their skyline. A key point marks every change in the height of the outline.</figcaption>
</figure>

**The baseline approach.** At a coordinate `x`, the outline's height equals the maximum height among all buildings that cover `x`. In a direct method, this maximum is evaluated at each of the 2n building edges by a scan over all n buildings. Each evaluation costs O(n), and the whole computation costs O(n²).

**The sweep-line approach.** The height of the outline can change only at a building edge, so the 2n edges are the events of the sweep. At a left edge, 1 height is added to the active set, and at a right edge, 1 height is removed. After each edge, the maximum of the active set is the outline's height to the right of that edge. A key point is emitted only when this maximum differs from its previous value.

## 32.2 An ordered multiset of active heights

3 operations on the active set are required: insertion of a height, removal of 1 specific height, and retrieval of the maximum. Insertion and retrieval of the maximum are supported by `BinaryHeap` from chapter 5, but no operation for the removal of an arbitrary element is provided. The active set is therefore stored in a `BTreeMap<i32, i32>` used as a **multiset**, a set in which an element can occur more than once. Each key is a height, and its value is the number of active buildings of that height. The counts are required because 2 active buildings can have equal heights. At the right edge of 1 of these buildings, the other must remain in the set.

In a `BTreeMap`, keys are stored in sorted order in a B-tree. Insertion and removal take O(log n) time, and the largest key is obtained with `keys().next_back()` in O(log n) time. The map is initialized with the entry `(0, 1)`, which represents the ground. This entry is never removed, so the map is never empty, and the outline's height is 0 after the right edge of the last building in a group.

## 32.3 Events at the same coordinate

2 events are created for each building, `(left, Event::Start(Reverse(height)))` and `(right, Event::End(height))`, and the events are sorted as tuples. Events at different coordinates are ordered by `x`. Ties at the same coordinate are decided by the derived `Ord` implementation of `Event`. Under 3 of its rules, no key point outside the skyline is emitted:

1. Variants are compared in declaration order, so every `Start` precedes every `End` at the same `x`. When the right edge of 1 building coincides with the left edge of another building of equal height, the start is processed first. The maximum is never reduced, and no key point `[x, 0]` is emitted between the 2 buildings.
2. 2 `Start` events are compared by their `Reverse(height)` values, so the taller building is processed first. The taller height is the maximum from the first start onward, the maximum is unchanged by the shorter start, and 1 key point is emitted where 2 would be emitted otherwise.
3. 2 `End` events are compared by plain heights, so the shorter building is removed first. The maximum is changed only by the removal of the taller building, and again 1 key point is emitted.

The result for the buildings `[0, 5, 10]` and `[5, 8, 10]` depends on rule 1. If the end at `x = 5` were processed first, the maximum would be reduced to 0 and raised back to 10, and the false key points `[5, 0]` and `[5, 10]` would be emitted between 2 buildings that form 1 flat roof.

## 32.4 A trace

The 10 events of the 5 buildings in figure 32.1 are processed in the order below. After each event, the active heights are listed in sorted order, and a key point is emitted whenever the maximum changes.

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

At `x = 5`, the building of height 12 becomes active, but the building of height 15 still covers that coordinate, so no key point is emitted. From `x = 7`, the right edge of the building of height 15, the outline's height is 12.

## 32.5 The program

<p class="listing"><b>Listing 32.1</b> The skyline with a sweep line and an ordered multiset. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/skyline_problem.rs">src/bin/skyline_problem.rs</a></p>

```rust
{{#include ../../rust-interview-lab/src/bin/skyline_problem.rs}}
```

```text
$ cargo run --bin skyline_problem
[[2, 10], [3, 15], [7, 12], [12, 0], [15, 10], [20, 8], [24, 0]]
```

Key details of the implementation:

- In `flat_map`, each building is expanded into an array of 2 events, so `events` holds exactly 2n entries.
- `sort_unstable` is sufficient, although equal elements may be reordered by it. 2 events that compare equal have the same coordinate, variant and height, so the result does not depend on their relative order.
- In the `End` arm, a mutable reference to the count of `h` is obtained with `entry(h).or_default()`, and the count is decremented. When the count reaches 0, the key is removed, so the height of an ended building is never returned by `next_back`. An equivalent formulation with `get_mut` and `is_some_and` is given in the commented block.
- The condition `if let Some(&curr_max) = active.keys().next_back() && curr_max != prev_max` is a **let chain**, stabilized in Rust 1.88 for the 2024 edition. The comparison is evaluated only when the pattern matches, and the binding `curr_max` is in scope for it.

**Complexity.** The 2n events are sorted in O(n log n) time. For each event, 1 update of the B-tree and 1 lookup of the maximum are then performed, each in O(log n) time. The total running time is O(n log n), and the events and the map occupy O(n) space.

<div class="summary" markdown="1">

## Summary

- A sweep line is moved across the plane and stopped only at events, the coordinates where the answer can change. Between 2 events, the active set is constant.
- For the skyline, the events are the 2n building edges. The outline's height after an event is the maximum of the active heights, and a key point is emitted only when that maximum changes.
- The removal of a specific height is required for the active set and is not available in `BinaryHeap`. In a `BTreeMap` of height counts, insertion, removal and retrieval of the maximum take O(log n) time, and because of the ground entry `(0, 1)`, the map is never empty.
- Ties at 1 coordinate are ordered by the derived `Ord` of `Event`: starts before ends, taller starts first, shorter ends first. Under each rule, 1 kind of false key point is avoided.
- The running time of the whole sweep is O(n log n), and its space is O(n).

</div>

## Exercises

1. Replace the `BTreeMap` in `get_skyline` with a `BinaryHeap<i32>` and lazy deletion: record each ended height in a `HashMap<i32, i32>`, and pop the heap while its top is recorded there. Check that the 7 key points of section 32.4 are unchanged.
2. Reverse the declaration order of `Start` and `End` in `Event`, and run the program on the buildings `[0, 5, 10]` and `[5, 8, 10]`. Explain each false key point that appears.
3. Use a sweep line to compute the maximum number of meetings that overlap at any moment, given each meeting as `[start, end)`. Decide whether an end at `x` must be processed before or after a start at the same `x`.
4. Compute the total area covered by the buildings of figure 32.1, counting overlapping parts once, by summing the outline's height times the width between consecutive key points.
