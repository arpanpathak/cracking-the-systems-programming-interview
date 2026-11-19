// ch19/linked_list.rs: reverse a list, merge two sorted lists, detect a cycle.

struct Node {
    value: i32,
    next: Option<Box<Node>>,
}

type List = Option<Box<Node>>;

/// Builds a list from a slice, last element first, so that order is preserved.
fn from_slice(values: &[i32]) -> List {
    values
        .iter()
        .rev()
        .fold(None, |next, &value| Some(Box::new(Node { value, next })))
}

/// Reverses the list by moving each node to the front of a new list.
fn reverse(mut head: List) -> List {
    let mut reversed = None;

    while let Some(mut node) = head {
        head = node.next.take();
        node.next = reversed;
        reversed = Some(node);
    }

    reversed
}

/// Merges two ascending lists into one ascending list, reusing the nodes.
fn merge_sorted(mut left: List, mut right: List) -> List {
    let mut merged = None;
    let mut tail = &mut merged;

    // While both chains contain nodes, detach the smaller head.
    while let (Some(l), Some(r)) = (&left, &right) {
        let take_left = l.value <= r.value;
        let source = if take_left { &mut left } else { &mut right };

        if let Some(mut node) = source.take() {
            *source = node.next.take();
            tail = &mut tail.insert(node).next;
        }
    }

    // O(1) splice: directly attach whichever chain still has nodes.
    *tail = left.or(right);

    merged
}

/// Floyd's algorithm on index links. A `Box` list cannot contain a cycle, because
/// each node has exactly one owner, so the cyclic case uses an array of next indices.
fn has_cycle(next: &[Option<usize>], head: usize) -> bool {
    let step = |position: Option<usize>| position.and_then(|index| next[index]);
    let mut slow = Some(head);
    let mut fast = Some(head);

    loop {
        slow = step(slow);
        fast = step(step(fast));

        if fast.is_none() {
            return false;
        }

        if slow == fast {
            return true;
        }
    }
}

fn print_list(label: &str, mut head: &List) {
    print!("{label}");

    while let Some(node) = head {
        print!(" {}", node.value);
        head = &node.next;
    }

    println!();
}

fn main() {
    let merged = merge_sorted(from_slice(&[1, 3, 5]), from_slice(&[2, 4, 6]));
    print_list("merged  :", &merged);

    let reversed = reverse(merged);
    print_list("reversed:", &reversed);

    let straight = [Some(1), Some(2), Some(3), None];
    let looped = [Some(1), Some(2), Some(3), Some(1)];

    let before = if has_cycle(&straight, 0) { "yes" } else { "no" };
    let after = if has_cycle(&looped, 0) { "yes" } else { "no" };

    println!("cycle before: {before}");
    println!("cycle after : {after}");
}
