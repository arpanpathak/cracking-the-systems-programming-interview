//! Demo of the `Option<Box<Node<T>>>` list in `lists::boxed`.
//!
//! Run with: cargo run --bin list_box

use nvidia_rust_interview_lab::lists::SinglyList;
use nvidia_rust_interview_lab::lists::boxed::LinkedList;

fn main() {
    let mut list = LinkedList::new();

    list.push_front(10);
    list.push_front(20);
    list.push_front(30);

    assert_eq!(list.pop_front(), Some(30));
    assert_eq!(list.pop_front(), Some(20));
    assert_eq!(list.pop_front(), Some(10));
    assert_eq!(list.pop_front(), None);
    assert!(list.is_empty());

    println!("All tests passed successfully!");
}
