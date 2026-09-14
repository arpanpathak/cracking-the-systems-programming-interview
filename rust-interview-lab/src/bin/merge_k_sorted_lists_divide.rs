struct MergeKSorted { }

#[derive(Default)]
struct ListNode {
    data: u32,
    next: Option<Box<ListNode>>
}
impl ListNode {
    fn new(data: u32) -> Self { 
        Self {
            data,
            next: None
        }
    }
}

type OptionalLink<T> = Option<Box<T>>;

impl MergeKSorted {
    pub fn merge_k_lists(mut lists: Vec<OptionalLink<ListNode>>) -> OptionalLink<ListNode> {
        if lists.is_empty() { return None; }

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

    fn merge_two(a: &mut OptionalLink<ListNode>, b: &mut OptionalLink<ListNode>) -> OptionalLink<ListNode> {
        let mut dummy = Box::new(ListNode::new(0));
        let mut tail = &mut dummy;

        while let (Some(na), Some(nb)) = (a.as_ref(), b.as_ref()) {
            let pick = if na.data < nb.data { &mut *a } else { &mut *b };
            let mut node = pick.take().unwrap();
            *pick = node.next.take();
            tail.next = Some(node);
            tail = tail.next.as_mut().unwrap();
        }

        tail.next = a.take().or(b.take());
        dummy.next
    }
}

/// Build a list from a slice, front to back.
fn from_slice(values: &[u32]) -> OptionalLink<ListNode> {
    let mut head = None;
    for &value in values.iter().rev() {
        let mut node = Box::new(ListNode::new(value));
        node.next = head;
        head = Some(node);
    }
    head
}

/// Collect a list's values into a vector.
fn to_vec(mut list: &OptionalLink<ListNode>) -> Vec<u32> {
    let mut values = Vec::new();
    while let Some(node) = list {
        values.push(node.data);
        list = &node.next;
    }
    values
}

fn main() {
    let lists = vec![from_slice(&[1, 4, 5]), from_slice(&[1, 3, 4]), from_slice(&[2, 6])];
    let merged = MergeKSorted::merge_k_lists(lists);
    println!("{:?}", to_vec(&merged));
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn merges_three_lists() {
        let lists = vec![from_slice(&[1, 4, 5]), from_slice(&[1, 3, 4]), from_slice(&[2, 6])];
        let merged = MergeKSorted::merge_k_lists(lists);
        assert_eq!(to_vec(&merged), vec![1, 1, 2, 3, 4, 4, 5, 6]);
    }

    #[test]
    fn handles_empty_input_and_empty_lists() {
        assert!(MergeKSorted::merge_k_lists(vec![]).is_none());
        let merged = MergeKSorted::merge_k_lists(vec![None, from_slice(&[2]), None]);
        assert_eq!(to_vec(&merged), vec![2]);
    }

    #[test]
    fn handles_an_odd_number_of_lists() {
        let lists: Vec<_> = (0..5).map(|i| from_slice(&[i, i + 10])).collect();
        let merged = MergeKSorted::merge_k_lists(lists);
        assert_eq!(to_vec(&merged), vec![0, 1, 2, 3, 4, 10, 11, 12, 13, 14]);
    }
}
