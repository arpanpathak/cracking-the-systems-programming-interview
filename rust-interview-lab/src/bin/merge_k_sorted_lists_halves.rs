use std::mem;

#[derive(Debug)]
struct ListNode {
    val: i32,
    next: Option<Box<ListNode>>,
}

type List = Option<Box<ListNode>>;

fn merge(a: List, b: List) -> List {
    match (a, b) {
        (None, rest) | (rest, None) => rest,
        (Some(mut left), Some(mut right)) => {
            if left.val > right.val {
                mem::swap(&mut left, &mut right);
            }
            left.next = merge(left.next.take(), Some(right));
            Some(left)
        }
    }
}

fn merge_k_slice(lists: &mut [List]) -> List {
    match lists.len() {
        0 => None,
        1 => lists[0].take(),
        _ => {
            let mid = lists.len() / 2;
            let (left_half, right_half) = lists.split_at_mut(mid);
            merge(merge_k_slice(left_half), merge_k_slice(right_half))
        }
    }
}

fn create_list(arr: &[i32]) -> List {
    let mut head = None;
    let mut tail = &mut head;

    for &val in arr {
        *tail = Some(Box::new(ListNode { val, next: None }));
        if let Some(node) = tail {
            tail = &mut node.next;
        }
    }

    head
}

fn print_list(mut list: &List) {
    let mut elements = Vec::new();
    while let Some(node) = list {
        elements.push(node.val.to_string());
        list = &node.next;
    }
    println!("[{}]", elements.join(" -> "));
}

fn main() {
    let mut lists = vec![
        create_list(&[1, 4, 5]),
        create_list(&[1, 3, 4]),
        create_list(&[2, 6]),
    ];

    println!("Input lists:");
    for list in &lists {
        print_list(list);
    }

    let merged = merge_k_slice(&mut lists);

    println!("\nMerged list:");
    print_list(&merged);
}
