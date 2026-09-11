//! Smart pointers and interior mutability.
//!
//! Each pointer type answers a different ownership question, and picking the
//! wrong one shows up as either a compile error or a runtime bug.
//!
//! | Type | Ownership | Mutation | Across threads |
//! |---|---|---|---|
//! | `Box<T>` | single | through `&mut` | if `T: Send` |
//! | `Rc<T>` | shared, non-atomic count | no | no |
//! | `Arc<T>` | shared, atomic count | no | if `T: Send + Sync` |
//! | `RefCell<T>` | single | runtime checked | no |
//! | `Mutex<T>` | single | blocking lock | yes |
//! | `Weak<T>` | non-owning | no | as `Arc` |
//! | `Cow<'a, T>` | borrow or own | no | as the borrow |
//!
//! Two rules cover most decisions. `Rc`/`RefCell` is for graphs and caches inside
//! one thread; `Arc`/`Mutex` is for state shared between threads. `Weak` exists to
//! break reference cycles, because two strong references in a cycle never reach a
//! count of zero and the memory is never freed.

use std::borrow::Cow;
use std::cell::RefCell;
use std::rc::{Rc, Weak};
use std::sync::{Arc, Mutex};
use std::thread;

/// A recursive type needs indirection, because `Expr` cannot contain itself by
/// value. `Box` provides the fixed-size indirection.
#[derive(Debug, PartialEq, Eq)]
pub enum Expr {
    Lit(i64),
    Add(Box<Expr>, Box<Expr>),
}

/// Evaluate an expression tree.
pub fn eval(expr: &Expr) -> i64 {
    match expr {
        Expr::Lit(value) => *value,
        Expr::Add(left, right) => eval(left) + eval(right),
    }
}

/// Shared mutation inside one thread, with `Rc` for aliasing and `RefCell` for
/// the runtime borrow check.
pub fn shared_counter_with_rc_refcell() -> i32 {
    let counter = Rc::new(RefCell::new(0));
    let alias = Rc::clone(&counter);

    *alias.borrow_mut() += 1;
    *counter.borrow_mut() += 10;

    *counter.borrow()
}

/// A node whose parent link is weak, so a child does not keep its parent alive.
pub struct TreeNode {
    pub value: i32,
    parent: RefCell<Weak<TreeNode>>,
}

impl TreeNode {
    /// A node with no parent.
    pub fn root(value: i32) -> Rc<Self> {
        Rc::new(Self {
            value,
            parent: RefCell::new(Weak::new()),
        })
    }

    /// A node that points back weakly at `parent`.
    pub fn child_of(parent: &Rc<Self>, value: i32) -> Rc<Self> {
        Rc::new(Self {
            value,
            parent: RefCell::new(Rc::downgrade(parent)),
        })
    }

    /// The parent's value, or `None` once the parent has been dropped.
    pub fn parent_value(&self) -> Option<i32> {
        self.parent.borrow().upgrade().map(|parent| parent.value)
    }
}

/// Shared mutation across threads, with `Arc` for ownership and `Mutex` for
/// exclusive access.
pub fn total_with_arc_mutex(threads: usize, per_thread: usize) -> usize {
    let total = Arc::new(Mutex::new(0usize));
    let mut handles = Vec::with_capacity(threads);

    for _ in 0..threads {
        let total = Arc::clone(&total);
        handles.push(thread::spawn(move || {
            for _ in 0..per_thread {
                let mut guard = total.lock().expect("mutex poisoned");
                *guard += 1;
            }
        }));
    }

    for handle in handles {
        handle.join().expect("worker panicked");
    }

    *total.lock().expect("mutex poisoned")
}

/// Borrow when no change is needed, allocate only when there is one.
///
/// `Cow` is the idiomatic return type for a function that usually passes its
/// input through unchanged.
pub fn normalize(input: &str, uppercase: bool) -> Cow<'_, str> {
    if uppercase && input.bytes().any(|byte| byte.is_ascii_lowercase()) {
        Cow::Owned(input.to_uppercase())
    } else {
        Cow::Borrowed(input)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn boxed_expression_evaluates() {
        let expr = Expr::Add(Box::new(Expr::Lit(1)), Box::new(Expr::Lit(2)));
        assert_eq!(eval(&expr), 3);
    }

    #[test]
    fn rc_refcell_shares_mutation_within_a_thread() {
        assert_eq!(shared_counter_with_rc_refcell(), 11);
    }

    #[test]
    fn weak_parent_link_does_not_keep_the_parent_alive() {
        let root = TreeNode::root(1);
        let child = TreeNode::child_of(&root, 2);

        assert_eq!(child.parent_value(), Some(1));
        drop(root);
        assert_eq!(child.parent_value(), None);
    }

    #[test]
    fn arc_mutex_sums_concurrent_updates() {
        assert_eq!(total_with_arc_mutex(8, 250), 2_000);
    }

    #[test]
    fn cow_borrows_and_owns_as_needed() {
        assert!(matches!(normalize("A100", true), Cow::Borrowed(_)));
        assert!(matches!(normalize("a100", true), Cow::Owned(_)));
        assert_eq!(normalize("a100", true), "A100");
        assert_eq!(normalize("a100", false), "a100");
    }
}
