//! Merge k sorted lists: the gap loop, with a short iterative merge.
//!
//! `merge_two` keeps both lists in one tuple. Each pass moves the smaller front
//! node to the end of the output and puts the two remaining lists back.

type Link = Option<Box<Node>>;

struct Node {
    val: i32,
    next: Link,
}

/// Merge two sorted lists. O(n) time, O(1) extra memory.
fn merge_two(left: Link, right: Link) -> Link {
    let mut head = None;
    let mut tail = &mut head;
    let mut lists = (left, right);
    while let (Some(left), Some(right)) = lists {
        let (mut smaller, larger) = if left.val <= right.val {
            (left, right)
        } else {
            (right, left)
        };
        lists = (smaller.next.take(), Some(larger));
        tail = &mut tail.insert(smaller).next;
    }
    *tail = lists.0.or(lists.1);
    head
}

/// Merge k sorted lists in place: round 1 merges lists 1 apart, round 2 lists
/// 2 apart, and so on. O(N log k) time, O(1) extra memory.
fn merge_k(mut lists: Vec<Link>) -> Link {
    if lists.is_empty() {
        return None;
    }

    let size = lists.len();
    let mut gap = 1;
    while gap < size {
        let mut i = 0;
        while i + gap < size {
            lists[i] = merge_two(lists[i].take(), lists[i + gap].take());
            i += gap * 2;
        }
        gap *= 2;
    }
    lists[0].take()
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
