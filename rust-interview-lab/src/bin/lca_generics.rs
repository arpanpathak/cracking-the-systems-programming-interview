use std::ptr;

#[derive(Debug)]
struct Node<T> {
    val: T,
    left: Link<T>,
    right: Link<T>,
}

type Link<T> = Option<Box<Node<T>>>;

fn lowest_common_ancestor<'a, T>(root: &'a Link<T>, p: &Link<T>, q: &Link<T>) -> Option<&'a Node<T>> {
    let node: &Node<T> = root.as_ref()?;

    if ptr::eq(root, p) || ptr::eq(root, q) {
        return Some(node);
    }

    match (
        lowest_common_ancestor(&node.left, p, q),
        lowest_common_ancestor(&node.right, p, q),
    ) {
        // When the node p and q is found on both side of the root node, it mean root is the lowest
        // common ancestor.
        (Some(_), Some(_)) => Some(node),
        (left, right) => left.or(right),
    }
}

fn main() {
    //             1
    //           /   \
    //          2     3
    //         / \   / \
    //        4   5 6   7
    //           / \
    //          8   9
    let root = Some(Box::new(Node {
        val: 1,
        left: Some(Box::new(Node {
            val: 2,
            left: Some(Box::new(Node { val: 4, left: None, right: None })),
            right: Some(Box::new(Node {
                val: 5,
                left: Some(Box::new(Node { val: 8, left: None, right: None })),
                right: Some(Box::new(Node { val: 9, left: None, right: None })),
            })),
        })),
        right: Some(Box::new(Node {
            val: 3,
            left: Some(Box::new(Node { val: 6, left: None, right: None })),
            right: Some(Box::new(Node { val: 7, left: None, right: None })),
        })),
    }));

    // SAFETY: the tree is built by hand above, so these nodes are known to exist.
    let n1 = root.as_ref().unwrap();
    let n2 = n1.left.as_ref().unwrap();
    let n3 = n1.right.as_ref().unwrap();
    let n5 = n2.right.as_ref().unwrap();

    // SAFETY: p and q are both in the tree, so an LCA always exists.
    println!("LCA(8, 9) = {}", lowest_common_ancestor(&root, &n5.left, &n5.right).unwrap().val);
    println!("LCA(4, 9) = {}", lowest_common_ancestor(&root, &n2.left, &n5.right).unwrap().val);
    println!("LCA(8, 7) = {}", lowest_common_ancestor(&root, &n5.left, &n3.right).unwrap().val);
    println!("LCA(2, 8) = {}", lowest_common_ancestor(&root, &n1.left, &n5.left).unwrap().val);
}
