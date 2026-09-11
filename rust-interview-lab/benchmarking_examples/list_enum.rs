//! Demo of the `enum ListNode<T>` list in `lists::enum_node`.
//!
//! Run with: cargo run --bin list_enum

use nvidia_rust_interview_lab::lists::SinglyList;
use nvidia_rust_interview_lab::lists::enum_node::LinkedList;

fn main() {
    let mut list = LinkedList::new();
    list.push_front(42);
    list.push_front(100);

    assert_eq!(list.pop_front(), Some(100));
    assert_eq!(list.pop_front(), Some(42));
    assert_eq!(list.pop_front(), None);
    assert!(list.is_empty());
}
