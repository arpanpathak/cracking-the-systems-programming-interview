//! `Option<Box<Node<T>>>`: one heap allocation per node.
//!
//! Pushing takes the old head and boxes it inside the new node. Freeing the head
//! frees its `next`, which frees its `next`, so the drop recurses once per
//! element and overflows the stack on a long list.

use super::SinglyList;

struct Node<T> {
    value: T,
    next: Option<Box<Node<T>>>,
}

pub struct LinkedList<T> {
    head: Option<Box<Node<T>>>,
}

impl<T> SinglyList<T> for LinkedList<T> {
    fn new() -> Self {
        Self { head: None }
    }

    fn push_front(&mut self, value: T) {
        self.head = Some(Box::new(Node {
            value,
            // .take() leaves None in its place and extracts the old head
            next: self.head.take(),
        }));
    }

    fn pop_front(&mut self) -> Option<T> {
        self.head.take().map(|node| {
            // Point the list head to the next node in line
            self.head = node.next;
            // Return the unboxed value
            node.value
        })
    }

    fn is_empty(&self) -> bool {
        self.head.is_none()
    }

    fn variant() -> &'static str {
        "box"
    }
}
