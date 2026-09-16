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
