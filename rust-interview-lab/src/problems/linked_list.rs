//! Reverse a singly linked list, and remove nodes from it.
//!
//! Uses `Option<Box<ListNode>>` and a `while let` loop to move pointers in a
//! borrow-safe way. Removal walks a cursor: a mutable borrow of one link.

#[derive(Debug, PartialEq, Eq)]
pub struct ListNode {
    pub val: i32,
    pub next: Option<Box<ListNode>>,
}

impl ListNode {
    pub fn from_slice(values: &[i32]) -> Option<Box<ListNode>> {
        let mut head = None;
        for &value in values.iter().rev() {
            head = Some(Box::new(ListNode {
                val: value,
                next: head,
            }));
        }
        head
    }

    pub fn to_vec(head: Option<Box<ListNode>>) -> Vec<i32> {
        let mut result = Vec::new();
        let mut current = head;
        while let Some(node) = current {
            result.push(node.val);
            current = node.next;
        }
        result
    }
}

pub fn reverse_list(head: Option<Box<ListNode>>) -> Option<Box<ListNode>> {
    let mut previous = None;
    let mut current = head;

    while let Some(mut node) = current {
        current = node.next.take();
        node.next = previous;
        previous = Some(node);
    }

    previous
}

/// Remove every node whose value is `target`, in one pass.
///
/// `cursor` is a mutable borrow of a link: first `head`, then the `next` of
/// each node that stays. A matching node is unlinked by moving its `next` into
/// the link that pointed at it. The cursor does not move after a removal,
/// because the link it holds now points at a node not yet checked.
pub fn remove_all(mut head: Option<Box<ListNode>>, target: i32) -> Option<Box<ListNode>> {
    let mut cursor = &mut head;
    while cursor.is_some() {
        let node = cursor
            .as_mut()
            .expect("checked by is_some");
        if node.val == target {
            let next = node.next.take();
            *cursor = next;
        } else {
            cursor = &mut cursor
                .as_mut()
                .expect("checked by is_some")
                .next;
        }
    }
    head
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reverses_list() {
        let head = ListNode::from_slice(&[1, 2, 3, 4]);
        assert_eq!(ListNode::to_vec(reverse_list(head)), vec![4, 3, 2, 1]);
    }

    #[test]
    fn removes_head_middle_and_consecutive_matches() {
        let head = ListNode::from_slice(&[2, 1, 2, 2, 3, 2]);
        assert_eq!(ListNode::to_vec(remove_all(head, 2)), vec![1, 3]);
    }

    #[test]
    fn remove_all_edge_cases() {
        let absent = ListNode::from_slice(&[1, 3]);
        assert_eq!(ListNode::to_vec(remove_all(absent, 2)), vec![1, 3]);
        let every = ListNode::from_slice(&[7, 7, 7]);
        assert_eq!(remove_all(every, 7), None);
        assert_eq!(remove_all(None, 7), None);
    }

    #[test]
    fn handles_empty_and_single() {
        assert_eq!(reverse_list(None), None);
        assert_eq!(
            ListNode::to_vec(reverse_list(ListNode::from_slice(&[42]))),
            vec![42]
        );
    }
}
