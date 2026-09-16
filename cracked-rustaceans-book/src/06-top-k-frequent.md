# 6. Top K Frequent Elements {#top-k-frequent}

*Source file: [`src/problems/top_k_frequent.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/top_k_frequent.rs). Test it with
`cargo test top_k_frequent`.*

## Problem Statement

Given a slice of integers and a number `k`, return the `k` values that occur most
often. The result order is defined only if the function states how ties are broken.
This implementation keys the heap on `(count, value)`, compared lexicographically, so
a larger value wins a tie.

## Designing a Solution

Two passes. The first counts occurrences in a hash map. The second moves every
`(count, value)` pair into a `BinaryHeap` and pops the largest keys.

`BinaryHeap` in Rust is a max-heap, so the pairs come out in descending count and, for
equal counts, in descending value. The alternative, a min-heap holding at most `k`
entries, costs `O(m log k)` time and `O(k)` space and is not implemented here. The
cost table states what the simpler choice costs.

## Implementation

<p class="listing"><span class="listing-label">Listing 6.1</span> The complete module, with its tests. <code>src/problems/top_k_frequent.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/top_k_frequent.rs">read the file on GitHub</a></p>

`*counts.entry(num).or_insert(0) += 1` looks up the count or inserts zero, then
increments through the returned `&mut usize`. The map is searched once per element
rather than twice.

`counts.into_iter()` consumes the map and yields owned pairs, so the heap is built
without borrowing the map. `map(|(num, count)| (count, num))` reverses each pair so
that the count is the first component of the key, which is the tie-break rule.

`while result.len() < k` with `None => break` handles a `k` larger than the number of
distinct values: the heap empties, the loop stops, and the result is shorter than `k`.

## Intuition

```text
nums = [1, 1, 1, 2, 2, 3]     k = 2

pass 1: counts = {1: 3, 2: 2, 3: 1}

pass 2: heap after collecting the pairs (count, value):
        pop order is (3, 1), (2, 2), (1, 3)

pop 1 -> push value 1     result = [1]
pop 2 -> push value 2     result = [1, 2]      length is k, stop

The heap still holds (1, 3), which is not popped.
```

## Time and Space Complexity

| Resource | Cost | Condition |
|---|---|---|
| Time | `O(n + m log m)` expected | `m` distinct values; the first pass is `O(n)`, the heap operations are `O(m log m)` |
| Space | `O(m)` | the map and the heap each hold one entry per distinct value |

The heap holds one entry per distinct value rather than `k` entries. For a slice of a
million elements with half a million distinct values and `k = 10`, the program builds a
heap of half a million entries to return ten. A min-heap bounded at `k` entries, which
discards each element smaller than its root, costs `O(m log k)` time and `O(k)` space.
The file does not implement it.

## Limitations

**The heap is unbounded in the number of distinct values.** Every distinct value
counted becomes an entry, so the structure holds `m` entries at its largest, where `m`
is the number of distinct values in the input.

**The result order is fixed by the heap comparison and nothing else.** The pair
ordering makes it deterministic, and the first test sorts the result before asserting,
so the file never pins the order. A caller that prints the result directly sees
descending count and then descending value.

**A `k` of zero returns an empty vector.** `Vec::with_capacity(0)` allocates nothing
and the loop does not run, so the answer is empty rather than a panic. The file has no
test for it.

**The tie-break rule is not documented.** A reader has to derive it from `(count, num)`
and from the fact that `BinaryHeap` is a max-heap. Two sentences in the module
documentation would make it part of the contract rather than a consequence of the
implementation.

## Summary

- Two passes: a hash map counts occurrences, and a `BinaryHeap` of `(count, value)`
  pairs yields the `k` largest counts.
- `BinaryHeap` is a max-heap and orders pairs by the first field, so putting the count
  first is what makes the heap answer the question asked.
- The heap holds one entry per distinct value, which is `O(m log m)` time and `O(m)`
  space. A min-heap of at most `k` entries would cost `O(m log k)` and `O(k)`.
- Ties are broken by the value, because that is how a pair compares, rather than by a
  documented rule. A caller that needs a stated order must impose it.

## References

- Standard library, [`BinaryHeap`](https://doc.rust-lang.org/std/collections/struct.BinaryHeap.html), which documents that the heap is a max-heap.
- Standard library, [`cmp::Reverse`](https://doc.rust-lang.org/std/cmp/struct.Reverse.html), the wrapper that turns a max-heap into a min-heap.
- Standard library, [`HashMap::entry`](https://doc.rust-lang.org/std/collections/struct.HashMap.html#method.entry).
