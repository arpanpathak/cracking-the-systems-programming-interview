use std::ptr;

#[derive(Debug)]
struct Node<'a, T> {
    val: T,
    left: Link<'a, T>,
    right: Link<'a, T>,
}

type Link<'a, T> = Option<&'a Node<'a, T>>;

fn lowest_common_ancestor<'a, T>(root: Link<'a, T>, p: &Node<T>, q: &Node<T>) -> Link<'a, T> {
    let node = root?;

    if ptr::eq(node, p) || ptr::eq(node, q) {
        return Some(node);
    }

    match (
        lowest_common_ancestor(node.left, p, q),
        lowest_common_ancestor(node.right, p, q),
    ) {
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
    let root = Some(&Node {
        val: 1,
        left: Some(&Node {
            val: 2,
            left: Some(&Node { val: 4, left: None, right: None }),
            right: Some(&Node {
                val: 5,
                left: Some(&Node { val: 8, left: None, right: None }),
                right: Some(&Node { val: 9, left: None, right: None }),
            }),
        }),
        right: Some(&Node {
            val: 3,
            left: Some(&Node { val: 6, left: None, right: None }),
            right: Some(&Node { val: 7, left: None, right: None }),
        }),
    });

    // SAFETY: the tree is built by hand above, so these nodes are known to exist.
    let n1 = root.unwrap();
    let n2 = n1.left.unwrap();
    let n3 = n1.right.unwrap();
    let n4 = n2.left.unwrap();
    let n5 = n2.right.unwrap();
    let n7 = n3.right.unwrap();
    let n8 = n5.left.unwrap();
    let n9 = n5.right.unwrap();

    // SAFETY: p and q are both in the tree, so an LCA always exists.
    println!("LCA(8, 9) = {}", lowest_common_ancestor(root, n8, n9).unwrap().val);
    println!("LCA(4, 9) = {}", lowest_common_ancestor(root, n4, n9).unwrap().val);
    println!("LCA(8, 7) = {}", lowest_common_ancestor(root, n8, n7).unwrap().val);
    println!("LCA(2, 8) = {}", lowest_common_ancestor(root, n2, n8).unwrap().val);
}
