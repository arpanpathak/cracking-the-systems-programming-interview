//! Singly linked lists in four variants, so one benchmark loop can cover all of
//! them.
//!
//! The variants differ only in how a node is stored and in how the list frees
//! itself. `boxed` and `enum_node` free a chain of boxes recursively, which
//! overflows the stack past roughly 265,000 nodes. `boxed_drop` and `enum_drop`
//! unlink iteratively and scale.

pub mod boxed;
pub mod boxed_drop;
pub mod enum_drop;
pub mod enum_node;

/// The operations every variant supports, so the benchmark can be written once.
pub trait SinglyList<T>: Sized {
    /// A new, empty list.
    fn new() -> Self;

    /// Adds `value` to the front of the list.
    fn push_front(&mut self, value: T);

    /// Removes and returns the front value, if there is one.
    fn pop_front(&mut self) -> Option<T>;

    /// Whether the list holds nothing.
    fn is_empty(&self) -> bool;

    /// The variant's name, for benchmark output and error messages.
    fn variant() -> &'static str;
}
