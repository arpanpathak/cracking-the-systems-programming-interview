//! `enum ListNode<T> { Empty, Next(T, Box<ListNode<T>>) }`.
//!
//! Same shape as the boxed variant, written with an enum instead of an
//! `Option`. The enum cannot contain itself by value, so the recursive arm holds
//! a `Box`. The drop is recursive for the same reason.

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
        // Extract the old head and leave Empty in its place
        let old_head = std::mem::replace(&mut self.head, ListNode::Empty);

        // Wrap the old head inside a Box behind the new value
        self.head = ListNode::Next(value, Box::new(old_head));
    }

    fn pop_front(&mut self) -> Option<T> {
        let old_head = std::mem::replace(&mut self.head, ListNode::Empty);

        match old_head {
            ListNode::Empty => None,
            ListNode::Next(value, next_node) => {
                // Point the list head to the next node in the sequence
                self.head = *next_node;
                Some(value)
            }
        }
    }

    fn is_empty(&self) -> bool {
        matches!(self.head, ListNode::Empty)
    }

    fn variant() -> &'static str {
        "enum"
    }
}
