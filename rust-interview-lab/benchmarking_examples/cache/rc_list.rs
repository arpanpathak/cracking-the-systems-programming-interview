//! LRU cache built from an `Rc<RefCell<_>>` doubly linked list.
//!
//! The textbook version: `Rc` forward, `Weak` back, and a `HashMap` from key to
//! node. Every node is its own heap allocation, and every move to the front
//! clones an `Rc`, upgrades a `Weak`, and borrows the `RefCell`.
//!
//! The default drop would free a node, which frees its `next`, one stack frame
//! per element, so `Drop` is written to unlink iteratively.

use std::cell::RefCell;
use std::collections::HashMap;
use std::hash::Hash;
use std::rc::{Rc, Weak};

use super::Cache;

type Link<K, V> = Option<Rc<RefCell<Node<K, V>>>>;

struct Node<K, V> {
    key: K,
    value: V,
    prev: Weak<RefCell<Node<K, V>>>,
    next: Link<K, V>,
}

pub struct LruCache<K, V> {
    cap: usize,
    map: HashMap<K, Rc<RefCell<Node<K, V>>>>,
    head: Link<K, V>,
    tail: Link<K, V>,
}

impl<K, V> LruCache<K, V>
where
    K: Hash + Eq + Clone,
    V: Copy,
{
    fn detach(&mut self, node: &Rc<RefCell<Node<K, V>>>) {
        let (prev, next) = {
            let entry = node.borrow();
            (entry.prev.clone(), entry.next.clone())
        };

        match prev.upgrade() {
            Some(previous) => previous.borrow_mut().next = next.clone(),
            None => self.head = next.clone(),
        }
        match &next {
            Some(following) => following.borrow_mut().prev = prev,
            None => self.tail = prev.upgrade(),
        }
    }

    fn push_front(&mut self, node: Rc<RefCell<Node<K, V>>>) {
        let head = self.head.clone();
        {
            let mut entry = node.borrow_mut();
            entry.prev = Weak::new();
            entry.next = head.clone();
        }
        match &head {
            Some(previous) => previous.borrow_mut().prev = Rc::downgrade(&node),
            None => self.tail = Some(node.clone()),
        }
        self.head = Some(node);
    }
}

impl<K, V> Cache<K, V> for LruCache<K, V>
where
    K: Hash + Eq + Clone,
    V: Copy,
{
    fn new(capacity: usize) -> Self {
        assert!(capacity > 0, "capacity must be > 0");
        Self {
            cap: capacity,
            map: HashMap::new(),
            head: None,
            tail: None,
        }
    }

    fn get(&mut self, key: &K) -> Option<V> {
        let node = self.map.get(key)?.clone();
        self.detach(&node);
        self.push_front(node.clone());
        Some(node.borrow().value)
    }

    fn put(&mut self, key: K, value: V) {
        if let Some(node) = self.map.get(&key).cloned() {
            node.borrow_mut().value = value;
            self.detach(&node);
            self.push_front(node);
            return;
        }

        if self.map.len() >= self.cap {
            if let Some(victim) = self.tail.clone() {
                let old_key = victim.borrow().key.clone();
                self.map.remove(&old_key);
                self.detach(&victim);
            }
        }

        let node = Rc::new(RefCell::new(Node {
            key: key.clone(),
            value,
            prev: Weak::new(),
            next: None,
        }));
        self.map.insert(key, node.clone());
        self.push_front(node);
    }

    fn len(&self) -> usize {
        self.map.len()
    }

    fn variant() -> &'static str {
        "Rc<RefCell> list"
    }
}

impl<K, V> Drop for LruCache<K, V> {
    fn drop(&mut self) {
        // Unlink iteratively: dropping a million-node chain recursively overflows
        // the stack.
        let mut current = self.head.take();
        while let Some(node) = current {
            let next = node.borrow_mut().next.take();
            node.borrow_mut().prev = Weak::new();
            current = next;
        }
    }
}
