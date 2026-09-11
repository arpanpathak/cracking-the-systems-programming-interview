// ============================================================================
// Type aliases for clarity.
// ============================================================================
use std::cell::{Ref, RefCell}; // Ref is needed for peek return types
use std::rc::{Rc, Weak};

type NodeRef<T> = Rc<RefCell<Node<T>>>;
type WeakNodeRef<T> = Weak<RefCell<Node<T>>>;
type OptNodeRef<T> = Option<NodeRef<T>>;
type OptWeakNodeRef<T> = Option<WeakNodeRef<T>>;

// ============================================================================
// Node and LinkedList definitions.
// ============================================================================
struct Node<T> {
    data: T,
    next: OptNodeRef<T>,
    prev: OptWeakNodeRef<T>,
}

pub struct LinkedList<T> {
    head: OptNodeRef<T>,
    tail: OptNodeRef<T>,
    len: usize,
}

impl<T> LinkedList<T> {
    /// Creates an empty list.
    pub fn new() -> Self {
        LinkedList {
            head: None,
            tail: None,
            len: 0,
        }
    }

    pub fn len(&self) -> usize {
        self.len
    }
    pub fn is_empty(&self) -> bool {
        self.len == 0
    }

    // --------------------------------------------------------------------
    // push_front
    // --------------------------------------------------------------------
    pub fn push_front(&mut self, data: T) {
        let new_node = Rc::new(RefCell::new(Node {
            data,
            next: None,
            prev: None,
        }));

        // take() moves the old head out of the Option, leaving None.
        match self.head.take() {
            Some(old_head) => {
                // Link old head back to new node (weakly).
                old_head.borrow_mut().prev = Some(Rc::downgrade(&new_node));
                // Link new node forward to old head.
                new_node.borrow_mut().next = Some(old_head);
            }
            None => {
                // List was empty: new node is also the tail.
                self.tail = Some(new_node.clone());
            }
        }
        self.head = Some(new_node);
        self.len += 1;
    }

    // --------------------------------------------------------------------
    // push_back
    // --------------------------------------------------------------------
    pub fn push_back(&mut self, data: T) {
        let new_node = Rc::new(RefCell::new(Node {
            data,
            next: None,
            // self.tail.as_ref() gives Option<&NodeRef<T>>,
            // map(Rc::downgrade) turns it into Option<WeakNodeRef<T>>.
            prev: self.tail.as_ref().map(Rc::downgrade),
        }));

        match self.tail.take() {
            Some(old_tail) => {
                old_tail.borrow_mut().next = Some(new_node.clone());
            }
            None => {
                self.head = Some(new_node.clone());
            }
        }
        self.tail = Some(new_node);
        self.len += 1;
    }

    // --------------------------------------------------------------------
    // pop_front
    // --------------------------------------------------------------------
    pub fn pop_front(&mut self) -> Option<T> {
        self.head.take().and_then(|old_head| {
            // Take ownership of the next node (if any).
            let next = old_head.borrow_mut().next.take();

            match next {
                Some(next_node) => {
                    // Disconnect the new head's prev pointer.
                    next_node.borrow_mut().prev = None;
                    self.head = Some(next_node);
                }
                None => {
                    self.tail = None; // list becomes empty
                }
            }

            self.len -= 1;

            // Safely extract the data. At this point, old_head is the only
            // strong reference (because we removed it from the list and the
            // new head's prev doesn't point to it).
            let node = Rc::try_unwrap(old_head).ok().unwrap().into_inner();
            Some(node.data)
        })
    }

    // --------------------------------------------------------------------
    // pop_back
    // --------------------------------------------------------------------
    pub fn pop_back(&mut self) -> Option<T> {
        self.tail.take().and_then(|old_tail| {
            // Get the previous node (upgrade the weak reference).
            let prev = old_tail.borrow_mut().prev.take().and_then(|w| w.upgrade());

            match prev {
                Some(prev_node) => {
                    prev_node.borrow_mut().next = None;
                    self.tail = Some(prev_node);
                }
                None => {
                    self.head = None; // list becomes empty
                }
            }

            self.len -= 1;

            let node = Rc::try_unwrap(old_tail).ok().unwrap().into_inner();
            Some(node.data)
        })
    }

    // --------------------------------------------------------------------
    // peek_front: returns a guarded reference to the front data.
    // The returned Ref<'_, T> holds the borrow of the RefCell until it goes
    // out of scope, ensuring the reference stays valid.
    // --------------------------------------------------------------------
    pub fn peek_front(&self) -> Option<Ref<'_, T>> {
        // self.head.as_ref() -> Option<&NodeRef<T>>
        self.head.as_ref().map(|node| {
            // node.borrow() returns Ref<'_, Node<T>>.
            // Ref::map projects that to a Ref<'_, T> pointing to the data field.
            Ref::map(node.borrow(), |n| &n.data)
        })
    }

    // --------------------------------------------------------------------
    // peek_back: similar to peek_front.
    // --------------------------------------------------------------------
    pub fn peek_back(&self) -> Option<Ref<'_, T>> {
        self.tail
            .as_ref()
            .map(|node| Ref::map(node.borrow(), |n| &n.data))
    }
}

// ============================================================================
// Demonstration with main().
// ============================================================================
fn main() {
    let mut list = LinkedList::new();

    list.push_front(10);
    list.push_front(20);
    list.push_back(30);
    list.push_back(40);

    println!("Length: {}", list.len());

    // Peek returns a Ref; we can dereference it with *.
    if let Some(front) = list.peek_front() {
        println!("Front: {}", *front);
    }
    if let Some(back) = list.peek_back() {
        println!("Back: {}", *back);
    }

    println!("Pop front: {:?}", list.pop_front()); // 20
    println!("Pop back:  {:?}", list.pop_back()); // 40

    // Drain the list.
    while let Some(val) = list.pop_front() {
        println!("Popped: {}", val);
    }
    println!("Empty? {}", list.is_empty());
}

// ============================================================================
// Tests (cargo test --bin ll)
// ============================================================================
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn new_list_is_empty() {
        let list: LinkedList<i32> = LinkedList::new();
        assert!(list.is_empty());
        assert_eq!(list.len(), 0);
        assert!(list.peek_front().is_none());
        assert!(list.peek_back().is_none());
    }

    #[test]
    fn push_front_back_and_len() {
        let mut list = LinkedList::new();
        list.push_back(1);
        list.push_back(2);
        list.push_front(0);

        assert_eq!(list.len(), 3);
        assert_eq!(*list.peek_front().unwrap(), 0);
        assert_eq!(*list.peek_back().unwrap(), 2);
    }

    #[test]
    fn pop_front_and_back_work_in_order() {
        let mut list = LinkedList::new();
        list.push_back(10);
        list.push_back(20);
        list.push_back(30);

        assert_eq!(list.pop_front(), Some(10));
        assert_eq!(list.pop_back(), Some(30));
        assert_eq!(list.pop_front(), Some(20));
        assert_eq!(list.pop_front(), None);
        assert_eq!(list.pop_back(), None);
        assert!(list.is_empty());
    }

    #[test]
    fn popping_last_item_empties_the_list() {
        let mut list = LinkedList::new();
        list.push_back(42);
        assert_eq!(list.peek_front().map(|x| *x), Some(42));
        assert_eq!(list.pop_back(), Some(42));
        assert!(list.is_empty());
    }

    #[test]
    fn alternating_push_pop_keeps_invariants() {
        let mut list = LinkedList::new();
        for i in 0..100 {
            list.push_back(i);
            list.push_front(-i);
        }
        assert_eq!(list.len(), 200);
        for i in (0..100).rev() {
            assert_eq!(list.pop_front(), Some(-i));
            assert_eq!(list.pop_back(), Some(i));
        }
        assert!(list.is_empty());
    }
}

// ============================================================================
// Explanation of key methods used:
//
// - Rc::new / RefCell::new        : create a reference-counted, mutable cell.
// - borrow() / borrow_mut()       : borrow the RefCell's contents (immutably/mutably).
// - Rc::downgrade()               : turn an Rc into a Weak (no ownership).
// - Weak::upgrade()               : attempt to get an Rc from a Weak (returns Option).
// - Option::take()                : take the value out of an Option, leaving None.
// - Option::as_ref()              : convert Option<T> to Option<&T> without moving.
// - Option::map()                 : apply a function to the inner value if Some.
// - Option::and_then()            : like map but returns an Option (for chaining).
// - Rc::try_unwrap()              : move the value out of the Rc if it's the only strong ref.
// - Ref::map()                    : project a Ref to a subfield, keeping the borrow alive.
// ============================================================================
