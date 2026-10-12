struct TreeNode<T> {
    data: T,
    children: Vec<TreeNode<T>>,
}

struct TreeIter<'a, T> {
    stack: Vec<&'a TreeNode<T>>,
}

impl<'a, T> Iterator for TreeIter<'a, T> {
    type Item = &'a T;

    fn next(&mut self) -> Option<Self::Item> {
        let node = self.stack.pop()?;
        self.stack.extend(node.children.iter().rev());
        Some(&node.data)
    }
}

impl<'a, T> TreeNode<T> {
    /// TODO: Study WTF is this syntax TreeIter<'_, T> why is life time using underscore, ?? Using
    /// lifetime of 'a throws compliation error. 
    fn iter(&self) -> TreeIter<'_, T> {
        TreeIter { stack: vec![self] }
    }
}

fn main() {
    let tree = TreeNode {
        data: 1,
        children: vec![
            TreeNode {
                data: 2,
                children: vec![
                    TreeNode { data: 4, children: vec![] },
                    TreeNode { data: 5, children: vec![] },
                ],
            },
            TreeNode {
                data: 3,
                children: vec![TreeNode { data: 6, children: vec![] }],
            },
        ],
    };

    let doubled: Vec<_> = tree.iter()
        .map(|value| value * 2)
        .collect();
    println!("{:?}", doubled);
}
