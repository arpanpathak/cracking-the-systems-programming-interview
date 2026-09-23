use std::collections::VecDeque;

#[derive(Debug)]
struct TreeNode<T> {
    value: T,
    children: Vec<TreeNode<T>>,
}


fn level_order<T>(root: &TreeNode<T>) -> Vec<Vec<&T>> {
    let mut result = Vec::new();
    let mut level = vec![root];
    while !level.is_empty() {
        result.push(level.iter().map(|n| &n.value).collect());
        level = level.iter().flat_map(|n| &n.children).collect();
    }
    result
}

fn level_order_readable<T>(root: &TreeNode<T>) -> Vec<Vec<&T>> {
    let mut result = Vec::new();
    let mut queue = VecDeque::from([(root)]);

    while !queue.is_empty() {
        let current_size = queue.len();
        let mut level = Vec::with_capacity(current_size);

        for _ in 1..=current_size {
            let Some(node) = queue.pop_front() else { break };

            level.push(&node.value);
            queue.extend(&node.children);
        }

        result.push(level);

    }
    result
}


fn main() {
    let root: TreeNode<String> = TreeNode {
        value: "root".into(),
        children: vec![
            TreeNode {
                value: "branch_a".into(),
                children: vec![
                    TreeNode { value: "leaf_1".into(), children: vec![] },
                    TreeNode { value: "leaf_2".into(), children: vec![] },
                ],
            },
            TreeNode {
                value: "branch_b".into(),
                children: vec![
                    TreeNode { value: "leaf_3".into(), children: vec![] },
                ],
            },
        ],
    };

    let levels = level_order(&root);
    println!("Tree\n {:#?}", root);

    for level in levels {
        println!("{:?}", level);
    }
}

