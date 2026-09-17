use std::cmp::Ordering::{Equal, Greater, Less};
use std::mem;

#[derive(Debug, Clone)]
pub enum BST<T> {
    Empty,
    Node {
        value: T,
        left: Box<BST<T>>,
        right: Box<BST<T>>,
    },
}

impl<T: Ord> BST<T> {
    pub fn new() -> Self {
        Self::Empty
    }

    pub fn insert(&mut self, val: T) {
        match self {
            Self::Empty => {
                *self = Self::Node {
                    value: val,
                    left: Box::new(Self::Empty),
                    right: Box::new(Self::Empty),
                };
            }
            Self::Node { value, left, right } => match val.cmp(value) {
                Less => left.insert(val),
                Greater => right.insert(val),
                Equal => {}
            },
        }
    }

    pub fn contains(&self, val: &T) -> bool {
        match self {
            Self::Empty => false,
            Self::Node { value, left, right } => match val.cmp(value) {
                Less => left.contains(val),
                Greater => right.contains(val),
                Equal => true,
            },
        }
    }

    pub fn remove(&mut self, val: &T) {
        match self {
            Self::Empty => {}
            Self::Node { value, left, right } => match val.cmp(value) {
                Less => left.remove(val),
                Greater => right.remove(val),
                Equal => {
                    if left.is_empty() {
                        *self = right.take();
                    } else if right.is_empty() {
                        *self = left.take();
                    } else {
                        *value = right.pop_min().unwrap();
                    }
                }
            },
        }
    }

    pub fn pop_min(&mut self) -> Option<T> {
        let mut node = self;

        while node.has_left() {
            if let Self::Node { left, .. } = node {
                node = left;
            }
        }

        match node.take() {
            Self::Empty => None,
            Self::Node { value, right, .. } => {
                *node = *right;
                Some(value)
            }
        }
    }

    pub fn range(&self, from: &T, to: &T) -> Vec<&T> {
        let mut result = Vec::new();

        if let Self::Node { value, left, right } = self {
            if from < value {
                result.extend(left.range(from, to));
            }
            if from <= value && value <= to {
                result.push(value);
            }
            if value < to {
                result.extend(right.range(from, to));
            }
        }

        result
    }

    fn is_empty(&self) -> bool {
        match self {
            Self::Empty => true,
            Self::Node { .. } => false,
        }
    }

    fn has_left(&self) -> bool {
        match self {
            Self::Empty => false,
            Self::Node { left, .. } => !left.is_empty(),
        }
    }

    fn take(&mut self) -> Self {
        mem::replace(self, Self::Empty)
    }
}

fn main() {
    let mut bst = BST::new();

    bst.insert(10);
    bst.insert(5);
    bst.insert(15);
    bst.insert(3);
    bst.insert(7);
    bst.insert(12);

    println!("Contains 7: {}", bst.contains(&7));
    println!("Range 4 to 12: {:?}", bst.range(&4, &12));

    bst.remove(&10);
    println!("After removing 10: {:?}", bst.range(&0, &100));

    println!("Pop min: {:?}", bst.pop_min());
    println!("{:#?}", bst);
}
