//! Merge k sorted lists by moving owned nodes.
//!
//! `merge_two` keeps one rule: `a` is the list whose front node comes next. It
//! moves that node onto a pile, swaps the two lists when `b` is now ahead, and
//! reverses the pile at the end. No node is copied or allocated, and nothing
//! holds a `&mut` into a list. `merge_k` merges the lists in place, in rounds
//! that double the gap between partners.

type Link = Option<Box<Node>>;

struct Node {
    val: i32,
    next: Link,
}

/// Whether list `x` should give the next node before list `y`.
fn goes_first(x: &Link, y: &Link) -> bool {
    match (x, y) {
        (Some(x), Some(y)) => x.val < y.val,
        (Some(_), None) => true,
        _ => false,
    }
}

/// Merge two sorted lists. O(n) time, O(1) extra memory.
fn merge_two(mut a: Link, mut b: Link) -> Link {
    let mut pile = None; // merged nodes so far, largest on top
    loop {
        if goes_first(&b, &a) {
            (a, b) = (b, a);
        }
        let Some(mut node) = a else { break };
        a = node.next; // a keeps the rest of its list
        node.next = pile; // the node goes on top of the pile
        pile = Some(node);
    }
    reverse(pile)
}

/// Reverse a list, as in chapter 9.
fn reverse(mut list: Link) -> Link {
    let mut reversed = None;
    while let Some(mut node) = list {
        list = node.next;
        node.next = reversed;
        reversed = Some(node);
    }
    reversed
}

/// Merge k sorted lists in place. Round 1 merges lists 1 apart, round 2 lists
/// 2 apart, and so on: O(N log k) time, O(1) extra memory.
fn merge_k(mut lists: Vec<Link>) -> Link {
    let mut gap = 1;
    while gap < lists.len() {
        for i in (0..lists.len() - gap).step_by(2 * gap) {
            lists[i] = merge_two(lists[i].take(), lists[i + gap].take());
        }
        gap *= 2;
    }
    lists.into_iter().next().flatten()
}

fn build(values: &[i32]) -> Link {
    let mut head = None;
    for &val in values.iter().rev() {
        head = Some(Box::new(Node { val, next: head }));
    }
    head
}

fn to_vec(mut current: Link) -> Vec<i32> {
    let mut out = Vec::new();
    while let Some(node) = current {
        out.push(node.val);
        current = node.next;
    }
    out
}

fn main() {
    let lists = vec![
        build(&[1, 4, 7]),
        build(&[2, 5, 8]),
        build(&[0, 3, 6, 9]),
        None,
    ];
    println!("{:?}", to_vec(merge_k(lists))); // [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    println!(
        "{:?}",
        to_vec(merge_k(vec![build(&[1, 1, 5]), build(&[1, 3])]))
    ); // [1, 1, 1, 3, 5]
    println!("{:?}", to_vec(merge_k(vec![]))); // []
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn merges_two_lists_keeping_duplicates() {
        let merged = merge_two(build(&[1, 1, 5]), build(&[1, 3]));
        assert_eq!(to_vec(merged), vec![1, 1, 1, 3, 5]);
    }

    #[test]
    fn merges_with_empty_lists() {
        assert_eq!(to_vec(merge_two(None, build(&[2, 4]))), vec![2, 4]);
        assert_eq!(to_vec(merge_two(build(&[2, 4]), None)), vec![2, 4]);
        assert!(merge_two(None, None).is_none());
        assert!(merge_k(vec![]).is_none());
        assert!(merge_k(vec![None, None]).is_none());
    }

    #[test]
    fn merges_an_odd_number_of_lists() {
        let five = vec![
            build(&[9]),
            build(&[1, 5]),
            build(&[3]),
            build(&[2, 8]),
            build(&[4]),
        ];
        assert_eq!(to_vec(merge_k(five)), vec![1, 2, 3, 4, 5, 8, 9]);
    }

    #[test]
    fn merges_many_long_lists() {
        let lists: Vec<Link> = (0..7)
            .map(|k| {
                build(
                    &(0..100)
                        .map(|i| i * 7 + k)
                        .collect::<Vec<_>>(),
                )
            })
            .collect();
        let expected: Vec<i32> = (0..700).collect();
        assert_eq!(to_vec(merge_k(lists)), expected);
    }
}
