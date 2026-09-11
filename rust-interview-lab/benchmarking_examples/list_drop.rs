//! Demo of the iterative `Drop` in `lists::boxed_drop`.
//!
//! The same program against `lists::boxed` aborts with a stack overflow at this
//! size, because that variant frees its chain recursively.
//!
//! Run with: cargo run --release --bin list_drop

use nvidia_rust_interview_lab::lists::SinglyList;
use nvidia_rust_interview_lab::lists::boxed_drop::LinkedList;

fn main() {
    const N: u64 = 5_000_000;

    let mut list = LinkedList::new();
    for value in 0..N {
        list.push_front(value);
    }
    println!("built a list of {N} nodes");

    list.pop_front();
    println!("dropping the remaining {} nodes", N - 1);

    drop(list);
    println!("dropped without recursing");
}
