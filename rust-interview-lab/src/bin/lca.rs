type Link<T> = Option<Box<TreeNode<T>>>;

#[derive(Default, PartialEq)]
struct TreeNode<T> {
    data: T,
    left: Link<T>,
    right: Link<T>,
}

impl<T: PartialEq + Clone> TreeNode<T> {
    fn get_lca(root: &Link<T>, p: &Link<T>, q: &Link<T>) -> Option<T> {
        let Some(node) = root else { return None };

        if root == p || root == q {
            return Some(node.data.clone());
        }

        match (Self::get_lca(&node.left, p, q), Self::get_lca(&node.right, p, q)) {
            (Some(_), Some(_)) => Some(node.data.clone()),
            (left, right) => left.or(right),
        }
    }
}

fn main() {
    let tree = Link::Some(Box::new(TreeNode {
        data: 1,
        left: Some(Box::new(TreeNode {
            data: 2,
            left: Some(Box::new(TreeNode { data: 4, left: None, right: None })),
            right: Some(Box::new(TreeNode { data: 5, left: None, right: None })),
        })),
        right: Some(Box::new(TreeNode { data: 3, left: None, right: None })),
    }));

    let p = Link::Some(Box::new(TreeNode { data: 4, left: None, right: None }));
    let q = Link::Some(Box::new(TreeNode { data: 5, left: None, right: None }));

    match TreeNode::get_lca(&tree, &p, &q) {
        Some(data) => println!("LCA is {}", data),
        _ => println!("Not found"),
    }
}
