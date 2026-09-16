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
