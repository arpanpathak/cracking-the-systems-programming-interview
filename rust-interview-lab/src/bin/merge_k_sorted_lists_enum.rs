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
