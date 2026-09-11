//! Reverse a singly linked list.
//!
//! Uses `Option<Box<ListNode>>` and a `while let` loop to move pointers in a
//! borrow-safe way.

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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn reverses_list() {
        let head = ListNode::from_slice(&[1, 2, 3, 4]);
        assert_eq!(ListNode::to_vec(reverse_list(head)), vec![4, 3, 2, 1]);
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
