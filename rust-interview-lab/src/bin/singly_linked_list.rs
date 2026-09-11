// Singly linked list using an algebraic data type.
//
//    List<T> = Empty
//            | Node { value: T, next: Link<T> }
//
// `Empty` is the end of the list.

type Link<T> = Box<List<T>>;

pub enum List<T> {
    Empty,
    Node { value: T, next: Link<T> },
}

impl<T> List<T> {
    pub fn new() -> Self {
        List::Empty
    }

    pub fn is_empty(&self) -> bool {
        matches!(self, List::Empty)
    }

    pub fn len(&self) -> usize {
        match self {
            List::Empty => 0,
            List::Node { next, .. } => 1 + next.len(),
        }
    }

    /// O(1)
    pub fn push_front(&mut self, value: T) {
        let old = std::mem::replace(self, List::Empty);
        *self = List::Node {
            value,
            next: Link::new(old),
        };
    }

    /// O(1)
    pub fn pop_front(&mut self) -> Option<T> {
        match std::mem::replace(self, List::Empty) {
            List::Empty => None,
            List::Node { value, next } => {
                *self = *next;
                Some(value)
            }
        }
    }

}

fn main() {
    let mut list = List::new();
    list.push_front(2);
    list.push_front(1);
    list.push_front(0);

    assert_eq!(list.len(), 3);
    assert_eq!(list.pop_front(), Some(0));
    assert_eq!(list.pop_front(), Some(1));
    assert_eq!(list.pop_front(), Some(2));
    println!("ok");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn push_pop_works() {
        let mut list = List::new();
        list.push_front(1);
        list.push_front(2);
        assert_eq!(list.pop_front(), Some(2));
        assert_eq!(list.pop_front(), Some(1));
        assert_eq!(list.pop_front(), None);
    }

    #[test]
    fn len_works() {
        let mut list = List::new();
        assert_eq!(list.len(), 0);
        list.push_front(1);
        list.push_front(2);
        assert_eq!(list.len(), 2);
    }
}
