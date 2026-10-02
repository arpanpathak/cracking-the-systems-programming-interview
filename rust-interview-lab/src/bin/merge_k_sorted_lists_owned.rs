//! Merge k sorted lists with owned values only.
//!
//! Every step moves a whole `Box<Node>` from one owner to another, so no node is
//! copied or allocated. There is no `&mut` cursor into a list and no `as_ref`:
//! the merge pushes each smaller front node onto the front of the result, which
//! leaves the result reversed, and one pass of `reverse` puts it in order.
//! The k lists are merged in place, in rounds that double the gap.

type Link = Option<Box<Node>>;

struct Node {
    val: i32,
    next: Link,
}

/// Merge two sorted lists into one, moving their nodes.
fn merge_two(mut left: Link, mut right: Link) -> Link {
    // The merged nodes so far, largest first. Each new node goes on the front.
    let mut reversed: Link = None;
    loop {
        // Take the smaller front node, and hand back both remaining lists.
        let mut node;
        (node, left, right) = match (left, right) {
            (Some(mut l), Some(r)) if l.val <= r.val => {
                let rest = l.next.take();
                (l, rest, Some(r))
            }
            (l, Some(mut r)) => {
                let rest = r.next.take();
                (r, l, rest)
            }
            (Some(mut l), None) => {
                let rest = l.next.take();
                (l, rest, None)
            }
            (None, None) => break,
        };
        node.next = reversed;
        reversed = Some(node);
    }
    reverse(reversed)
}

/// Reverse a list in place, as in chapter 9.
fn reverse(mut current: Link) -> Link {
    let mut previous = None;
    while let Some(mut node) = current {
        current = node.next.take();
        node.next = previous;
        previous = Some(node);
    }
    previous
}

/// Merge k sorted lists. Round 1 merges neighbours 1 apart, round 2 lists 2
/// apart, and so on, so every node moves about log2(k) times.
fn merge_k(mut lists: Vec<Link>) -> Link {
    let mut gap = 1;
    while gap < lists.len() {
        for i in (0..lists.len() - gap).step_by(gap * 2) {
            let left = lists[i].take();
            let right = lists[i + gap].take();
            lists[i] = merge_two(left, right);
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
