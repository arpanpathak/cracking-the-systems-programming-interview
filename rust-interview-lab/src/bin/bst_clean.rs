use std::cmp::Ordering;

type TreeLink<T> = Box<BST<T>>;

#[derive(Debug, Clone, Default)]
pub enum BST<T> {
    #[default]
    Empty,
    Node {
        value: T,
        left: TreeLink<T>,
        right: TreeLink<T>,
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
                Ordering::Less => left.insert(val),
                Ordering::Greater => right.insert(val),
                Ordering::Equal => {}
            },
        }
    }

    pub fn contains(&self, val: &T) -> bool {
        match self {
            Self::Empty => false,
            Self::Node { value, left, right } => match val.cmp(value) {
                Ordering::Less => left.contains(val),
                Ordering::Greater => right.contains(val),
                Ordering::Equal => true,
            },
        }
    }

    pub fn remove(&mut self, val: &T) -> bool {
        match self {
            Self::Empty => false,
            Self::Node { value, left, right } => match val.cmp(value) {
                Ordering::Less => left.remove(val),
                Ordering::Greater => right.remove(val),
                Ordering::Equal => {
                    if left.is_empty() && right.is_empty() {
                        *self = Self::Empty;
                        return true;
                    }
                    if left.is_empty() {
                        *self = *std::mem::take(right);
                        return true;
                    }
                    if right.is_empty() {
                        *self = *std::mem::take(left);
                        return true;
                    }
                    let min_val = right.remove_min().unwrap();
                    *value = min_val;
                    true
                }
            },
        }
    }

    fn remove_min(&mut self) -> Option<T> {
        match self {
            Self::Empty => None,
            Self::Node { left, .. } if left.is_empty() => {
                let node = std::mem::take(self);
                if let Self::Node { value, right, .. } = node {
                    *self = *right;
                    Some(value)
                } else {
                    unreachable!()
                }
            }
            Self::Node { left, .. } => left.remove_min(),
        }
    }

    pub fn range(&self, low: &T, high: &T) -> Vec<&T> {
        let mut result = Vec::new();
        self.range_helper(low, high, &mut result);
        result
    }

    // Explicit lifetime 'a ties the references in the vector to the lifetime of &self.
    fn range_helper<'a>(&'a self, low: &T, high: &T, acc: &mut Vec<&'a T>) {
        match self {
            Self::Empty => {}
            Self::Node { value, left, right } => {
                if value < low {
                    right.range_helper(low, high, acc);
                } else if value > high {
                    left.range_helper(low, high, acc);
                } else {
                    left.range_helper(low, high, acc);
                    acc.push(value);
                    right.range_helper(low, high, acc);
                }
            }
        }
    }

    fn is_empty(&self) -> bool {
        matches!(self, Self::Empty)
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
    bst.insert(18);

    println!("Contains 7: {}", bst.contains(&7));
    println!("Contains 12: {}", bst.contains(&12));

    let range = bst.range(&4, &16);
    println!("Values in [4, 16]: {:?}", range);

    println!("Remove 5: {}", bst.remove(&5));
    println!("Remove 10: {}", bst.remove(&10));
    println!("Remove 99: {}", bst.remove(&99));

    println!("After removals: {:#?}", bst);
}