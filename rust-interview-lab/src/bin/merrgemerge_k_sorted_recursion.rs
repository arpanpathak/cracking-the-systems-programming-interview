#[derive(Debug)]
struct ListNode {
    val: i32,
    next: Option<Box<ListNode>>,
}

type List = Option<Box<ListNode>>;

// Merge two sorted lists
fn merge(a: List, b: List) -> List {
    match (a, b) {
        (None, rest) | (rest, None) => rest,
        (Some(mut a), Some(mut b)) => {
            if a.val > b.val {
                std::mem::swap(&mut a, &mut b); // a is now the smaller head
            }
            a.next = merge(a.next.take(), Some(b));
            Some(a)
        }
    }
}

// Merge k sorted lists using divide and conquer
fn merge_k(mut lists: Vec<List>) -> List {
    match lists.len() {
        0 => None,
        1 => lists.pop().unwrap(),
        n => {
            let right = lists.split_off(n / 2); // lists = left half
            merge(merge_k(lists), merge_k(right))
        }
    }
}

// Merge k sorted lists using divide and conquer without heap allocation
fn merge_k_slice(lists: &mut [List]) -> List {
    match lists.len() {
        0 => None,
        1 => lists[0].take(),
        _ => {
            let mid = lists.len() / 2;
            let (left, right) = lists.split_at_mut(mid);
            merge(merge_k_slice(left), merge_k_slice(right))
        }
    }
}

// Helper: build a list from a Vec
// fn from_vec(v: Vec<i32>) -> List {
//     let mut head = None;
//     for val in v.into_iter().rev() {
//         head = Some(Box::new(ListNode { val, next: head }));
//     }
//     head
// }

fn from_vec(v: Vec<i32>) -> List {
    let mut head = None;
    let mut tail = &mut head; // points to the empty slot at the end

    for val in v {
        let node = Box::new(ListNode { val, next: None });
        tail = &mut tail.insert(node).next; // fill the slot, move to the new node's next
    }

    head
}

// Helper: turn a list back into a Vec for printing
fn to_vec(mut cur: &List) -> Vec<i32> {
    let mut out = Vec::new();
    while let Some(node) = cur {
        out.push(node.val);
        cur = &node.next;
    }
    out
}

fn main() {
    let lists = vec![
        from_vec(vec![1, 4, 5]),
        from_vec(vec![1, 3, 4]),
        from_vec(vec![2, 6]),
    ];
    let merged = merge_k(lists);
    println!("{:?}", to_vec(&merged)); // [1, 1, 2, 3, 4, 4, 5, 6]

    // Edge cases
    println!("{:?}", to_vec(&merge_k(vec![])));           // []
    println!("{:?}", to_vec(&merge_k(vec![None, None]))); // []
    println!("{:?}", to_vec(&merge_k(vec![from_vec(vec![7])]))); // [7]

    let v = [1,2,3,4,5];

    match v {
        [1, .. ] => println!("it starts with one thing...."),
        [_,..] => println!("I dunno why!"),
    }
}
