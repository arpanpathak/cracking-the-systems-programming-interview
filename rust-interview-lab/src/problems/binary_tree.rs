//! Binary tree as an algebraic data type.
//!
//! ```text
//! Tree = Empty
//!      | Node { value, left: Box<Tree>, right: Box<Tree> }
//! ```

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Tree {
    Empty,
    Node {
        value: i32,
        left: Box<Tree>,
        right: Box<Tree>,
    },
}

impl Tree {
    pub fn max_depth(&self) -> usize {
        match self {
            Tree::Empty => 0,
            Tree::Node { left, right, .. } => 1 + left.max_depth().max(right.max_depth()),
        }
    }

    pub fn invert(&mut self) {
        match self {
            Tree::Empty => {}
            Tree::Node { left, right, .. } => {
                left.invert();
                right.invert();
                std::mem::swap(left, right);
            }
        }
    }

    pub fn preorder(&self) -> Vec<i32> {
        let mut out = Vec::new();
        self.collect_preorder(&mut out);
        out
    }

    pub fn inorder(&self) -> Vec<i32> {
        let mut out = Vec::new();
        self.collect_inorder(&mut out);
        out
    }

    pub fn postorder(&self) -> Vec<i32> {
        let mut out = Vec::new();
        self.collect_postorder(&mut out);
        out
    }

    fn collect_preorder(&self, out: &mut Vec<i32>) {
        match self {
            Tree::Empty => {}
            Tree::Node { value, left, right } => {
                out.push(*value);
                left.collect_preorder(out);
                right.collect_preorder(out);
            }
        }
    }

    fn collect_inorder(&self, out: &mut Vec<i32>) {
        match self {
            Tree::Empty => {}
            Tree::Node { value, left, right } => {
                left.collect_inorder(out);
                out.push(*value);
                right.collect_inorder(out);
            }
        }
    }

    fn collect_postorder(&self, out: &mut Vec<i32>) {
        match self {
            Tree::Empty => {}
            Tree::Node { value, left, right } => {
                left.collect_postorder(out);
                right.collect_postorder(out);
                out.push(*value);
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn leaf(value: i32) -> Tree {
        Tree::Node {
            value,
            left: Box::new(Tree::Empty),
            right: Box::new(Tree::Empty),
        }
    }

    fn node(value: i32, left: Tree, right: Tree) -> Tree {
        Tree::Node {
            value,
            left: Box::new(left),
            right: Box::new(right),
        }
    }

    fn sample() -> Tree {
        node(3, leaf(9), node(20, leaf(15), leaf(7)))
    }

    #[test]
    fn max_depth_works() {
        assert_eq!(Tree::Empty.max_depth(), 0);
        assert_eq!(leaf(1).max_depth(), 1);
        assert_eq!(sample().max_depth(), 3);
    }

    #[test]
    fn invert_swaps_subtrees() {
        let mut tree = sample();
        tree.invert();

        match &tree {
            Tree::Node { left, right, .. } => {
                match left.as_ref() {
                    Tree::Node { value, .. } => assert_eq!(*value, 20),
                    _ => panic!("expected left node"),
                }
                match right.as_ref() {
                    Tree::Node { value, .. } => assert_eq!(*value, 9),
                    _ => panic!("expected right node"),
                }
            }
            _ => panic!("expected node"),
        }
    }

    #[test]
    fn traversals_work() {
        let tree = sample();
        assert_eq!(tree.preorder(), vec![3, 9, 20, 15, 7]);
        assert_eq!(tree.inorder(), vec![9, 3, 15, 20, 7]);
        assert_eq!(tree.postorder(), vec![9, 15, 7, 20, 3]);
    }
}
