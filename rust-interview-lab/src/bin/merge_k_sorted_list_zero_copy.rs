type NodeLink = Option<Box<Node>>;

struct Node {
    val: i32,
    next: NodeLink,
}

fn merge_two(mut left: NodeLink, mut right: NodeLink) -> NodeLink {
    let mut dummy = Box::new(Node { val: 0, next: None });
    let mut tail = &mut dummy;

    while let (Some(left_head), Some(right_head)) = (&left, &right) {
        let smaller = if left_head.val <= right_head.val {
            &mut left
        } else {
            &mut right
        };
        let mut node = smaller.take().unwrap(); // safe: checked by while let
        *smaller = node.next.take();
        tail = tail.next.insert(node);
    }

    tail.next = if left.is_some() { left } else { right };
    dummy.next
}

fn merge_k(mut lists: Vec<NodeLink>) -> NodeLink {
    if lists.is_empty() {
        return None;
    }

    let list_count = lists.len();
    let mut gap = 1;
    while gap < list_count {
        let mut index = 0;
        while index + gap < list_count {
            let left = lists[index].take();
            let right = lists[index + gap].take();
            lists[index] = merge_two(left, right);
            index += gap * 2;
        }
        gap *= 2;
    }
    lists[0].take()
}

fn build(values: &[i32]) -> NodeLink {
    let mut head = None;
    for &val in values.iter().rev() {
        head = Some(Box::new(Node { val, next: head }));
    }
    head
}

fn print(mut current: &NodeLink) {
    while let Some(node) = current {
        print!("{} ", node.val);
        current = &node.next;
    }
    println!();
}

fn main() {
    let lists = vec![
        build(&[1, 4, 7]),
        build(&[2, 5, 8]),
        build(&[0, 3, 6, 9]),
        None,
    ];
    print(&merge_k(lists)); // 0 1 2 3 4 5 6 7 8 9

    print(&merge_k(vec![build(&[1, 1, 5]), build(&[1, 3])])); // 1 1 1 3 5
    print(&merge_k(vec![])); // (empty line)

    let five = vec![
        build(&[9]),
        build(&[1, 5]),
        build(&[3]),
        build(&[2, 8]),
        build(&[4]),
    ];
    print(&merge_k(five)); // 1 2 3 4 5 8 9
}
