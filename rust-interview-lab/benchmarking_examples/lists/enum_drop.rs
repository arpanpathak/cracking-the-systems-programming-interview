//! `enum ListNode<T>` with an iterative `Drop`.
//!
//! Push and pop are identical to [`enum_node`](super::enum_node); only freeing
//! changes. The recursive arm holds a `Box`, so the default drop walks the chain
//! on the stack. This one replaces the head with `Empty`, then takes the box out
//! of each node in turn.

use super::SinglyList;

enum ListNode<T> {
    Empty,
    Next(T, Box<ListNode<T>>),
}

pub struct LinkedList<T> {
    head: ListNode<T>,
}

impl<T> SinglyList<T> for LinkedList<T> {
    fn new() -> Self {
        Self {
            head: ListNode::Empty,
        }
    }

    fn push_front(&mut self, value: T) {
        let old_head = std::mem::replace(&mut self.head, ListNode::Empty);
        self.head = ListNode::Next(value, Box::new(old_head));
    }

    fn pop_front(&mut self) -> Option<T> {
        let old_head = std::mem::replace(&mut self.head, ListNode::Empty);

        match old_head {
            ListNode::Empty => None,
            ListNode::Next(value, next_node) => {
                self.head = *next_node;
                Some(value)
            }
        }
    }

    fn is_empty(&self) -> bool {
        matches!(self.head, ListNode::Empty)
    }

    fn variant() -> &'static str {
        "enum+drop"
    }
}

impl<T> Drop for LinkedList<T> {
    fn drop(&mut self) {
        // Take the chain out of the list first, then step it forward one node at
        // a time. Each node has already lost its `next` by the time it is freed,
        // so the drop stays on the heap.
        let mut current = std::mem::replace(&mut self.head, ListNode::Empty);
        while let ListNode::Next(_, next) = current {
            current = *next;
        }
    }
}
