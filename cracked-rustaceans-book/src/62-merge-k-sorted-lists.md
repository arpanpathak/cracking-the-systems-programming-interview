# 62. Merge K Sorted Lists {#merge-k-sorted-lists}

*Source file: [`src/bin/merge_k_sorted_lists_divide.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/merge_k_sorted_lists_divide.rs). Run it with `cargo run --bin merge_k_sorted_lists_divide`, and test it with `cargo test --bin merge_k_sorted_lists_divide`.*

## Problem Statement

Given `k` singly linked lists, each sorted in ascending order, merge them into one sorted
list. The nodes must be relinked rather than copied, and the result must contain every
node of every input list.

## Designing a Solution

Merging two sorted lists is the building block: compare the heads, move the smaller node
to the output, and repeat. Merging `k` lists one after another into a growing result is
simple and slow, because the result is walked again for every list, which costs
`O(kN)` for `N` nodes in total.

Divide and conquer merges the lists in pairs, like the merge step of merge sort. In the
first round, list 0 is merged with list 1, list 2 with list 3, and so on. In the next
round, the survivors are merged in pairs again, until one list remains. Each node takes
part in one merge per round, and there are `log k` rounds, so the total is `O(N log k)`.

The implementation merges in place inside the input vector. `interval` is the distance
between the two lists being merged, and it doubles every round:

```text
lists: [L0, L1, L2, L3, L4]        n = 5

interval 1:  L0 = merge(L0, L1)   L2 = merge(L2, L3)   L4 untouched
interval 2:  L0 = merge(L0, L2)                        L4 untouched
interval 4:  L0 = merge(L0, L4)
interval 8:  8 >= 5, stop; the answer is lists[0]
```

`merge_two` uses a dummy head node, so appending the first node of the result needs no
special case, and a `tail` reference that always points at the last node of the output.

## Implementation

```rust
struct MergeKSorted { }

#[derive(Default)]
struct ListNode {
    data: u32,
    next: Option<Box<ListNode>>
}
impl ListNode {
    fn new(data: u32) -> Self { 
        Self {
            data,
            next: None
        }
    }
}

type OptionalLink<T> = Option<Box<T>>;

impl MergeKSorted {
    pub fn merge_k_lists(mut lists: Vec<OptionalLink<ListNode>>) -> OptionalLink<ListNode> {
        if lists.is_empty() { return None; }

        let (n, mut interval) = (lists.len(), 1);
        while interval < n {
            let mut i = 0;
            while i + interval < n {
                let (left, right) = lists.split_at_mut(i + interval);
                left[i] = Self::merge_two(&mut left[i], &mut right[0]);
                i += interval * 2;
            }
            interval *= 2;
        }

        lists[0].take()
    }

    fn merge_two(a: &mut OptionalLink<ListNode>, b: &mut OptionalLink<ListNode>) -> OptionalLink<ListNode> {
        let mut dummy = Box::new(ListNode::new(0));
        let mut tail = &mut dummy;

        while let (Some(na), Some(nb)) = (a.as_ref(), b.as_ref()) {
            let pick = if na.data < nb.data { &mut *a } else { &mut *b };
            let mut node = pick.take().unwrap();
            *pick = node.next.take();
            tail.next = Some(node);
            tail = tail.next.as_mut().unwrap();
        }

        tail.next = a.take().or(b.take());
        dummy.next
    }
}

/// Build a list from a slice, front to back.
fn from_slice(values: &[u32]) -> OptionalLink<ListNode> {
    let mut head = None;
    for &value in values.iter().rev() {
        let mut node = Box::new(ListNode::new(value));
        node.next = head;
        head = Some(node);
    }
    head
}

/// Collect a list's values into a vector.
fn to_vec(mut list: &OptionalLink<ListNode>) -> Vec<u32> {
    let mut values = Vec::new();
    while let Some(node) = list {
        values.push(node.data);
        list = &node.next;
    }
    values
}

fn main() {
    let lists = vec![from_slice(&[1, 4, 5]), from_slice(&[1, 3, 4]), from_slice(&[2, 6])];
    let merged = MergeKSorted::merge_k_lists(lists);
    println!("{:?}", to_vec(&merged));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn merges_three_lists() {
        let lists = vec![from_slice(&[1, 4, 5]), from_slice(&[1, 3, 4]), from_slice(&[2, 6])];
        let merged = MergeKSorted::merge_k_lists(lists);
        assert_eq!(to_vec(&merged), vec![1, 1, 2, 3, 4, 4, 5, 6]);
    }

    #[test]
    fn handles_empty_input_and_empty_lists() {
        assert!(MergeKSorted::merge_k_lists(vec![]).is_none());
        let merged = MergeKSorted::merge_k_lists(vec![None, from_slice(&[2]), None]);
        assert_eq!(to_vec(&merged), vec![2]);
    }

    #[test]
    fn handles_an_odd_number_of_lists() {
        let lists: Vec<_> = (0..5).map(|i| from_slice(&[i, i + 10])).collect();
        let merged = MergeKSorted::merge_k_lists(lists);
        assert_eq!(to_vec(&merged), vec![0, 1, 2, 3, 4, 10, 11, 12, 13, 14]);
    }
}
```

`lists.split_at_mut(i + interval)` is the step that makes the in-place merge legal. The
merge needs mutable access to two different elements of the same vector, `lists[i]` and
`lists[i + interval]`, and the borrow checker does not allow two `&mut` borrows of one
vector at the same time. `split_at_mut` divides the vector into two non-overlapping
mutable slices, so `left[i]` and `right[0]` are two separate borrows.

`merge_two` takes both lists as `&mut OptionalLink<ListNode>` and consumes them with
`take`. The loop condition `while let (Some(na), Some(nb)) = (a.as_ref(), b.as_ref())`
peeks at both heads without moving them. Inside the loop, `pick` is a mutable reference to
whichever list has the smaller head, `pick.take().unwrap()` detaches that node, and
`*pick = node.next.take()` advances the list past it.

`tail` is `&mut Box<ListNode>`. After `tail.next = Some(node)`, the statement
`tail = tail.next.as_mut().unwrap()` moves the reference to the node just appended. When
either input runs out, `tail.next = a.take().or(b.take())` attaches the rest of the other
list in one step, with no further comparisons.

`dummy.next` is the merged list. The dummy node itself is freed when the function returns.

The helpers `from_slice` and `to_vec` build lists from slices and read them back, so
`main` and the tests can express lists as arrays. The tests cover three lists, an empty
input and empty lists mixed with non-empty ones, and an odd number of lists, where the
last list waits until the final round.

## Intuition

```text
merge_two([1, 4, 5], [1, 3, 4])

a head   b head   pick   output so far
  1        1       b     [1]              1 < 1 is false, so b is picked on ties
  1        3       a     [1, 1]
  4        3       b     [1, 1, 3]
  4        4       b     [1, 1, 3, 4]
  4        -             loop ends: b is empty
                         tail.next = rest of a = [4, 5]
result: [1, 1, 3, 4, 4, 5]
```

For the three lists in `main`, the first round merges `[1, 4, 5]` with `[1, 3, 4]`, and the
second round merges the result with `[2, 6]`. The program prints:

```text
[1, 1, 2, 3, 4, 4, 5, 6]
```

## Time and Space Complexity

| Resource | Cost | Condition |
|---|---|---|
| Time | `O(N log k)` | `N` nodes in total; each of the `log k` rounds touches every node at most once |
| Space | `O(1)` extra | nodes are relinked in place; one dummy node per merge |
| Allocations | one per `merge_two` call | the dummy head is boxed |

A min-heap of the `k` current heads is the other common solution. It also costs
`O(N log k)`, and it needs `O(k)` extra space for the heap.

## Limitations

**Ties take the node from the second list.** The comparison is `na.data < nb.data`, so
equal values come from `b` first. The merge is correct, but it is not stable: equal
elements do not keep the order of their input lists. Using `<=` would keep elements from
the first list ahead on ties.

**The dummy node allocates.** `Box::new(ListNode::new(0))` allocates for every merge,
`k - 1` allocations in total. A local, unboxed dummy avoids the allocation, at the cost of
a slightly different type for `tail`.

**`MergeKSorted` is an empty struct used as a namespace.** `merge_k_lists` and `merge_two`
could be free functions; the struct groups them the way many online judges expect, and
it carries no state.

**The derived `Default` is unused.** `ListNode` derives `Default`, and nothing calls it.

**Dropping a very long result list is recursive.** As chapters 14 and 38 showed, the
default destructor of `Option<Box<ListNode>>` frees one node per stack frame, so a merged
list of a few hundred thousand nodes can overflow the stack when it is dropped.

**The values are `u32`.** The algorithm needs only `Ord`; a generic `ListNode<T: Ord>`
would merge any ordered type.

## Summary

- Merging `k` sorted lists in pairs, doubling the interval each round, costs
  `O(N log k)` and relinks nodes without copying.
- `split_at_mut` provides two mutable borrows of different vector elements at once.
- A dummy head and a `tail` reference remove the special case for the first node, and
  `a.take().or(b.take())` attaches the remainder in one step.
- The merge is not stable on ties, and each merge allocates one dummy node.

## References

- Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, and Clifford Stein,
  *Introduction to Algorithms*, 4th edition, MIT Press, 2022, Section 2.3, on merging.
- Standard library, [`slice::split_at_mut`](https://doc.rust-lang.org/std/primitive.slice.html#method.split_at_mut).
- Standard library, [`Option::take`](https://doc.rust-lang.org/std/option/enum.Option.html#method.take).
