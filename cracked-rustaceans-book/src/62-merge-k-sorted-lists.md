# 62. Merge K Sorted Lists {#merge-k-sorted-lists}

*Source files, all under `src/bin/`: [`merge_k_sorted_lists_divide.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/merge_k_sorted_lists_divide.rs), [`merge_k_sorted_lists_swap.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/merge_k_sorted_lists_swap.rs), [`merge_k_sorted_lists_simple.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/merge_k_sorted_lists_simple.rs), [`merge_k_sorted_lists_pairs.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/merge_k_sorted_lists_pairs.rs), [`merge_k_sorted_lists_heap.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/merge_k_sorted_lists_heap.rs), [`merge_k_sorted_lists_enum.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/merge_k_sorted_lists_enum.rs), and [`merge_k_sorted_list_easy.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/merge_k_sorted_list_easy.rs). Run any of them with
`cargo run --bin <name>`, and test the two that carry tests with
`cargo test --bin merge_k_sorted_lists_divide` and `cargo test --bin merge_k_sorted_lists_simple`.*

## Problem Statement

Given `k` singly linked lists, each sorted in ascending order, merge them into one sorted
list. The nodes must be relinked rather than copied, and the result must contain every
node of every input list.

The chapter solves the problem seven times. The divide-and-conquer version comes first and
is read in full; the six that follow change one decision each and are read against it:

| Version | What it changes |
|---|---|
| divide | merges in place inside the input vector, using `split_at_mut` for two borrows |
| swap | takes one list out of the vector first, so only one borrow is needed |
| simple | passes lists by value and appends through a `&mut Link`, with no dummy node |
| pairs | merges the front two lists of a `VecDeque` and pushes the result on the back |
| heap | keeps the head of every list in a `BinaryHeap` and pops the smallest |
| enum | replaces `Option<Box<ListNode>>` with an enum carrying an `Empty` variant |
| easy | merges two lists recursively, and builds lists through `From<Vec<i32>>` |

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

    fn merge_two(left: &mut OptionalLink<ListNode>, right: &mut OptionalLink<ListNode>) -> OptionalLink<ListNode> {
        let mut dummy = Box::new(ListNode::new(0));
        let mut tail = &mut dummy;

        while let (Some(l), Some(r)) = (left.as_ref(), right.as_ref()) {
            let smaller = if l.data < r.data { &mut *left } else { &mut *right };
            let mut head = smaller.take().unwrap();
            *smaller = head.next.take();
            tail.next = Some(head);
            tail = tail.next.as_mut().unwrap();
        }

        tail.next = left.take().or(right.take());
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
`take`. The loop condition `while let (Some(l), Some(r)) = (left.as_ref(), right.as_ref())`
peeks at both heads without moving them. Inside the loop, `smaller` is a mutable reference
to whichever list has the smaller head, `smaller.take().unwrap()` detaches that node, and
`*smaller = head.next.take()` advances the list past it.

`tail` is `&mut Box<ListNode>`. After `tail.next = Some(head)`, the statement
`tail = tail.next.as_mut().unwrap()` moves the reference to the node just appended. When
either input runs out, `tail.next = left.take().or(right.take())` attaches the rest of the other
list in one step, with no further comparisons.

`dummy.next` is the merged list. The dummy node itself is freed when the function returns.

The helpers `from_slice` and `to_vec` build lists from slices and read them back, so
`main` and the tests can express lists as arrays. The tests cover three lists, an empty
input and empty lists mixed with non-empty ones, and an odd number of lists, where the
last list waits until the final round.

### The variant that swaps instead of splitting

The two mutable borrows can be avoided rather than legalised. Taking
`lists[i + interval]` out of the vector with `take` leaves `None` behind at that index
and hands the caller an owned list, so the merge that follows borrows only `lists[i]`,
and a single borrow needs no help from `split_at_mut`.

*Source file: [`src/bin/merge_k_sorted_lists_swap.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/merge_k_sorted_lists_swap.rs). Run it with
`cargo run --bin merge_k_sorted_lists_swap`.*

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
                let mut right = lists[i + interval].take();
                lists[i] = Self::merge_two(&mut lists[i], &mut right);
                i += interval * 2;
            }
            interval *= 2;
        }

        lists[0].take()
    }

    fn merge_two(left: &mut OptionalLink<ListNode>, right: &mut OptionalLink<ListNode>) -> OptionalLink<ListNode> {
        let mut dummy = Box::new(ListNode::new(0));
        let mut tail = &mut dummy;

        while let (Some(l), Some(r)) = (&left, &right) {
            if r.data < l.data {
                std::mem::swap(left, right);
            }
            let mut smallest = left.take().unwrap();
            *left = smallest.next.take();
            tail.next = Some(smallest);
            tail = tail.next.as_mut().unwrap();
        }

        tail.next = left.take().or(right.take());
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

The merge changes shape as well. Instead of choosing a reference to whichever list has
the smaller head, it swaps the two lists whenever the right head is the smaller one, so
after the swap `left` always names the list the next node comes from. Everything below
the swap then has one path through it: detach the head of `left`, advance `left` past it,
append the node to the tail.

The comparison is `r.data < l.data`, and a tie leaves the two lists as they are, so the
node comes from `left`. This version is therefore stable where the divide-and-conquer
version above is not.

### The variant that moves the lists by value

References are not needed at all if the merge owns what it merges. Taking both lists by
value and returning the merged list makes the ownership of every node explicit in the
signature, and the caller puts the result back into the vector itself.

*Source file: [`src/bin/merge_k_sorted_lists_simple.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/merge_k_sorted_lists_simple.rs). Run it with
`cargo run --bin merge_k_sorted_lists_simple`.*

```rust
struct ListNode {
    data: u32,
    next: Link,
}

type Link = Option<Box<ListNode>>;

fn merge_k_lists(mut lists: Vec<Link>) -> Link {
    if lists.is_empty() { return None; }

    let (n, mut interval) = (lists.len(), 1);
    while interval < n {
        let mut i = 0;
        while i + interval < n {
            let left = lists[i].take();
            let right = lists[i + interval].take();
            lists[i] = merge_two(left, right);
            i += interval * 2;
        }
        interval *= 2;
    }

    lists[0].take()
}

fn merge_two(mut left: Link, mut right: Link) -> Link {
    let mut merged = None;
    let mut tail = &mut merged;

    while let (Some(l), Some(r)) = (&left, &right) {
        if r.data < l.data {
            std::mem::swap(&mut left, &mut right);
        }
        *tail = left;                              // hang left list on the tail
        tail = &mut tail.as_mut().unwrap().next;   // step past its first node
        left = tail.take();                        // cut the rest off again
    }

    *tail = left.or(right);
    merged
}

fn from_slice(values: &[u32]) -> Link {
    let mut head = None;
    for &data in values.iter().rev() {
        head = Some(Box::new(ListNode { data, next: head }));
    }
    head
}

fn to_vec(mut list: &Link) -> Vec<u32> {
    let mut values = Vec::new();
    while let Some(node) = list {
        values.push(node.data);
        list = &node.next;
    }
    values
}

fn main() {
    let lists = vec![from_slice(&[1, 4, 5]), from_slice(&[1, 3, 4]), from_slice(&[2, 6])];
    println!("{:?}", to_vec(&merge_k_lists(lists)));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn merges_three_lists() {
        let lists = vec![from_slice(&[1, 4, 5]), from_slice(&[1, 3, 4]), from_slice(&[2, 6])];
        assert_eq!(to_vec(&merge_k_lists(lists)), vec![1, 1, 2, 3, 4, 4, 5, 6]);
    }

    #[test]
    fn handles_empty_input_and_empty_lists() {
        assert!(merge_k_lists(vec![]).is_none());
        let merged = merge_k_lists(vec![None, from_slice(&[2]), None]);
        assert_eq!(to_vec(&merged), vec![2]);
    }

    #[test]
    fn handles_an_odd_number_of_lists() {
        let lists: Vec<_> = (0..5).map(|i| from_slice(&[i, i + 10])).collect();
        assert_eq!(to_vec(&merge_k_lists(lists)), vec![0, 1, 2, 3, 4, 10, 11, 12, 13, 14]);
    }
}
```

The output is built without a dummy node. `tail` is a `&mut Link`, a mutable reference to
the empty `Option` that sits at the end of the merged list, and writing through it appends.
At the start it points at `merged` itself, which is why the first node needs no special
case.

Three statements do the appending, and they are worth reading slowly. `*tail = left`
hangs the whole of the left list on the tail rather than one node.
`tail = &mut tail.as_mut().unwrap().next` steps the tail reference past the node that has
just been attached. `left = tail.take()` then cuts everything after that node off again
and gives it back to `left`. The net effect is the same as moving one node, and no `Box`
is allocated to hold a dummy.

### The variant that pairs the lists in a queue

Doubling an `interval` is bookkeeping in service of a simple idea: merge the lists two at
a time until one is left. A queue expresses the idea directly. Two lists come off the
front, their merge goes on the back, and the rounds appear on their own without being
counted.

*Source file: [`src/bin/merge_k_sorted_lists_pairs.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/merge_k_sorted_lists_pairs.rs). Run it with
`cargo run --bin merge_k_sorted_lists_pairs`.*

```rust
use std::collections::VecDeque;

struct ListNode {
    data: u32,
    next: Option<Box<ListNode>>,
}

type Link = Option<Box<ListNode>>;

fn merge_k_lists(lists: Vec<Link>) -> Link {
    let mut queue: VecDeque<Link> = lists.into();
    while queue.len() > 1 {
        let a = queue.pop_front().unwrap();
        let b = queue.pop_front().unwrap();
        queue.push_back(merge_two(a, b));
    }
    queue.pop_front().flatten()
}

fn merge_two(mut a: Link, mut b: Link) -> Link {
    let mut dummy = Box::new(ListNode { data: 0, next: None });
    let mut tail = &mut dummy;

    while let (Some(x), Some(y)) = (&a, &b) {
        let pick = if x.data <= y.data { &mut a } else { &mut b };
        let mut node = pick.take().unwrap();
        *pick = node.next.take();
        tail = tail.next.insert(node);
    }
    tail.next = a.or(b);
    dummy.next
}

fn main() {
    let mut lists = Vec::new();
    for values in [vec![1, 4, 5], vec![1, 3, 4], vec![2, 6]] {
        let mut head = None;
        for data in values.into_iter().rev() {
            head = Some(Box::new(ListNode { data, next: head }));
        }
        lists.push(head);
    }

    let mut cur = merge_k_lists(lists);
    while let Some(node) = cur {
        print!("{} ", node.data);
        cur = node.next;
    }
    println!();
}
```

Each pass over the queue halves the number of lists it holds, so a list takes part in
`log k` merges and the total is `O(N log k)`, the same as the interval version. The cost
is one `VecDeque` of `k` links, against the `O(1)` extra space of merging inside the input
vector.

`tail.next.insert(node)` replaces the `tail.next = Some(node)` and
`tail = tail.next.as_mut().unwrap()` pair used earlier. `Option::insert` stores the value
and returns a mutable reference to it, which is exactly the two steps in one.
`queue.pop_front().flatten()` turns the `Option<Link>` returned by the last pop into a
`Link`, since a queue of one list and an empty queue must both answer `None`.

### The variant that keeps the heads in a heap

The complexity table above names a min-heap as the other standard solution, and it is
worth writing out. Rather than merging lists against each other, keep the current head of
every list in a heap and repeatedly move the smallest one to the output.

*Source file: [`src/bin/merge_k_sorted_lists_heap.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/merge_k_sorted_lists_heap.rs). Run it with
`cargo run --bin merge_k_sorted_lists_heap`.*

```rust
use std::cmp::Reverse;
use std::collections::BinaryHeap;

struct ListNode {
    data: u32,
    next: Option<Box<ListNode>>,
}

type Link = Option<Box<ListNode>>;

fn merge_k_lists(mut lists: Vec<Link>) -> Link {
    let mut heap = BinaryHeap::new();
    for (i, list) in lists.iter().enumerate() {
        if let Some(node) = list {
            heap.push(Reverse((node.data, i)));
        }
    }

    let mut dummy = Box::new(ListNode { data: 0, next: None });
    let mut tail = &mut dummy;

    while let Some(Reverse((_, i))) = heap.pop() {
        let mut node = lists[i].take().unwrap();
        lists[i] = node.next.take();
        if let Some(next) = &lists[i] {
            heap.push(Reverse((next.data, i)));
        }
        tail = tail.next.insert(node);
    }
    dummy.next
}

fn main() {
    let mut lists = Vec::new();
    for values in [vec![1, 4, 5], vec![1, 3, 4], vec![2, 6]] {
        let mut head = None;
        for data in values.into_iter().rev() {
            head = Some(Box::new(ListNode { data, next: head }));
        }
        lists.push(head);
    }

    let mut cur = merge_k_lists(lists);
    while let Some(node) = cur {
        print!("{} ", node.data);
        cur = node.next;
    }
    println!();
}
```

`BinaryHeap` is a max-heap, so `Reverse` inverts every comparison and turns it into a
min-heap. What the heap stores is a `(data, index)` pair rather than a node: the node
itself stays in `lists[i]`, and only its value and the list it came from are needed to
decide what to pop next. Storing nodes in the heap would mean moving them out of the
lists and back, which is the fight with ownership this arrangement avoids entirely.

Each pop names the list holding the smallest head. That node is taken out of `lists[i]`,
the list is advanced past it, and the list's new head, if there is one, goes back into the
heap. The heap therefore holds at most `k` entries at any moment, one per non-empty list,
and each of the `N` nodes is pushed and popped once, for `O(N log k)` time and `O(k)`
space.

Ties are broken by the second field of the pair, the list index, so equal values leave the
lists in index order. The merge is stable.

### The variant that carries emptiness in the node

`Option<Box<ListNode>>` makes emptiness a property of the link. An enum with an `Empty`
variant makes it a property of the node, which is the shape a reader coming from a
functional language expects, and the shape an interviewer sometimes asks for by name.

*Source file: [`src/bin/merge_k_sorted_lists_enum.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/merge_k_sorted_lists_enum.rs). Run it with
`cargo run --bin merge_k_sorted_lists_enum`.*

```rust
use ListNode::{Empty, Node};

type LinkTo<T> = Box<T>;

enum ListNode {
    Node { data: u32, next: LinkTo<ListNode> },
    Empty,
}

impl ListNode {
    fn take(&mut self) -> ListNode {
        std::mem::replace(self, Empty)
    }
}

struct MergeKSorted {}

impl MergeKSorted {
    pub fn merge_k_lists(mut lists: Vec<ListNode>) -> ListNode {
        if lists.is_empty() { return Empty; }

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

    fn merge_two(left: &mut ListNode, right: &mut ListNode) -> ListNode {
        let mut left = left.take();
        let mut right = right.take();
        let mut merged = Empty;
        let mut tail = &mut merged;

        loop {
            let smaller = match (&left, &right) {
                (Empty, _) => { *tail = right; break; }
                (_, Empty) => { *tail = left; break; }
                (Node { data: l, .. }, Node { data: r, .. }) => {
                    if l <= r { &mut left } else { &mut right }
                }
            };

            if let Node { data, next } = smaller.take() {
                *smaller = *next;
                *tail = Node { data, next: LinkTo::new(Empty) };
                if let Node { next, .. } = tail {
                    tail = next;
                }
            }
        }

        merged
    }
}

fn main() {
    let mut lists = Vec::new();
    for values in [vec![1, 4, 5], vec![1, 3, 4], vec![2, 6]] {
        let mut head = Empty;
        for data in values.into_iter().rev() {
            head = Node { data, next: LinkTo::new(head) };
        }
        lists.push(head);
    }

    let merged = MergeKSorted::merge_k_lists(lists);

    let mut current = &merged;
    while let Node { data, next } = current {
        print!("{data} ");
        current = next;
    }
    println!();
}
```

`ListNode::take` is the enum's own version of `Option::take`. `mem::replace(self, Empty)`
moves the node out and leaves an empty one in its place, which is what makes it legal to
take a node out of a list that is still borrowed.

There is a cost to the change, and it is visible in `*tail = Node { data, next:
LinkTo::new(Empty) }`. Every appended node allocates a box to hold the `Empty` that
terminates the list, where `Option<Box<ListNode>>` stores the same information as a null
pointer inside the box's niche and allocates nothing. The enum form is one allocation per
node more expensive than the form printed at the head of this chapter.

The loop is a `loop` rather than a `while let`, because the two exhausted cases now have
to be matched explicitly. `(Empty, _)` and `(_, Empty)` attach the remaining list to the
tail and break; the third arm takes a mutable reference to whichever list has the smaller
head and falls through to the move below it.

### The variant that merges recursively

The merge of two sorted lists has a two-line recursive definition: the smaller head,
followed by the merge of what remains. Writing it that way removes the tail pointer and
the dummy node together.

*Source file: [`src/bin/merge_k_sorted_list_easy.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/merge_k_sorted_list_easy.rs). Run it with
`cargo run --bin merge_k_sorted_list_easy`.*

```rust
pub type NodeLink = Box<ListNode>;

#[derive(Debug, PartialEq, Eq, Default)]
pub enum ListNode {
    #[default]
    Empty,
    Node(i32, NodeLink),
}

impl From<Vec<i32>> for NodeLink {
    fn from(vec: Vec<i32>) -> Self {
        vec.into_iter().rev().fold(NodeLink::default(), |acc, v| NodeLink::new(ListNode::Node(v, acc)))
    }
}

impl From<Vec<i32>> for ListNode {
    fn from(vec: Vec<i32>) -> Self {
        *NodeLink::from(vec)
    }
}

impl ListNode {
    pub fn merge_k_lists(mut lists: Vec<NodeLink>) -> NodeLink {
        if lists.is_empty() {
            return NodeLink::default();
        }
        let mut interval = 1;
        while interval < lists.len() {
            for i in (0..lists.len()).step_by(interval * 2) {
                if i + interval < lists.len() {
                    let right = std::mem::take(&mut lists[i + interval]);
                    let left = std::mem::take(&mut lists[i]);
                    lists[i] = Self::merge(left, right);
                }
            }
            interval *= 2;
        }
        lists.swap_remove(0)
    }

    fn merge(l1: NodeLink, l2: NodeLink) -> NodeLink {
        match (*l1, *l2) {
            (ListNode::Empty, l) | (l, ListNode::Empty) => NodeLink::new(l),
            (ListNode::Node(v1, n1), ListNode::Node(v2, n2)) => {
                if v1 <= v2 {
                    NodeLink::new(ListNode::Node(v1, Self::merge(n1, NodeLink::new(ListNode::Node(v2, n2)))))
                } else {
                    NodeLink::new(ListNode::Node(v2, Self::merge(NodeLink::new(ListNode::Node(v1, n1)), n2)))
                }
            }
        }
    }
}

fn main() {
    let lists: Vec<NodeLink> = vec![
        vec![1, 4, 5].into(),
        vec![1, 3, 4].into(),
        vec![2, 6].into(),
    ];

    let merged = ListNode::merge_k_lists(lists);

    println!("{:#?}", merged);
}
```

`From<Vec<i32>>` is what lets `main` write `vec![1, 4, 5].into()`. The fold walks the
values backwards and hangs each one in front of the list built so far, starting from
`NodeLink::default()`, which the `#[default]` attribute on `Empty` defines as the empty
list.

`match (*l1, *l2)` dereferences both boxes, which moves the nodes out of them, so each arm
owns the data it matched and can rebuild a list from it without cloning. The first arm
uses an or-pattern: whichever side is empty, the other is the answer.

The recursion costs a stack frame per node of the merged list, which is the limitation
this version trades for its brevity. A merge of a few hundred thousand nodes overflows the
stack, as chapters 14 and 38 describe for the recursive destructor. `v1 <= v2` keeps the
node from the first list ahead on ties, so this merge is stable.

## Intuition

```text
merge_two([1, 4, 5], [1, 3, 4])

left    right    taken   output so far
  1        1      right   [1]              1 < 1 is false, so right is taken on ties
  1        3      left    [1, 1]
  4        3      right   [1, 1, 3]
  4        4      right   [1, 1, 3, 4]
  4        -              loop ends: right is empty
                          tail.next = rest of left = [4, 5]
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

**Ties take the node from the second list.** The comparison is `l.data < r.data`, so
equal values come from `right` first. The merge is correct, but it is not stable: equal
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
  `left.take().or(right.take())` attaches the remainder in one step.
- The merge is not stable on ties, and each merge allocates one dummy node. The swap,
  by-value, queue, heap and recursive versions are all stable, because each of them
  takes the node from the earlier list when two values are equal.
- The queue and the heap reach the same `O(N log k)` by different routes: the queue
  halves the number of lists on every pass, and the heap holds one entry per list and
  pops `N` times.
- An enum with an `Empty` variant reads well and allocates one box per node more than
  `Option<Box<ListNode>>`, which keeps its terminator in the pointer's niche.

## References

- Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, and Clifford Stein,
  *Introduction to Algorithms*, 4th edition, MIT Press, 2022, Section 2.3, on merging.
- Standard library, [`slice::split_at_mut`](https://doc.rust-lang.org/std/primitive.slice.html#method.split_at_mut).
- Standard library, [`Option::take`](https://doc.rust-lang.org/std/option/enum.Option.html#method.take).
