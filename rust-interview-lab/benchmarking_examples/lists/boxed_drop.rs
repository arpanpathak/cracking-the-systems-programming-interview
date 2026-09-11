//! `Option<Box<Node<T>>>` with an iterative `Drop`.
//!
//! Push and pop are identical to [`boxed`](super::boxed); only freeing changes.
//! Dropping a node would otherwise drop its `next` and recurse once per element,
//! so the list is unlinked in a loop before any node is freed.

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
            next: self.head.take(),
        }));
    }

    fn pop_front(&mut self) -> Option<T> {
        self.head.take().map(|node| {
            self.head = node.next;
            node.value
        })
    }

    fn is_empty(&self) -> bool {
        self.head.is_none()
    }

    fn variant() -> &'static str {
        "box+drop"
    }
}

impl<T> Drop for LinkedList<T> {
    fn drop(&mut self) {
        // Walk the chain and unlink each node before it is freed, so no node's
        // drop has to carry the rest of the list on the stack.
        let mut current = self.head.take();
        while let Some(mut node) = current {
            current = node.next.take();
        }
    }
}
