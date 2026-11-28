use std::iter;

pub struct Node<T> {
    pub value: T,
    pub children: Vec<usize>,
}

pub struct Tree<T> {
    pub arena: Vec<Node<T>>,
    pub root: Option<usize>,
}

impl<T> Tree<T> {
    pub fn dfs_iter(&self) -> impl Iterator<Item = &Node<T>> {
        // Automatically copies the Option<usize> out of &self
        let mut stack: Vec<usize> = self.root.into_iter().collect();

        iter::from_fn(move || {
            let current_idx = stack.pop()?;
            let node = &self.arena[current_idx];

            // Reversing the reference iterator and extending the stack directly.
            // Rust automatically handles the dereferencing here during extension.
            stack.extend(node.children.iter().rev());

            Some(node)
        })
    }
}

fn main() {
    // Setting up a flat-vector arena tree:
    //      0
    //     / \
    //    1   2
    let tree = Tree {
        arena: vec![
            Node {
                value: "Root",
                children: vec![1, 2],
            },
            Node {
                value: "Left Child",
                children: vec![],
            },
            Node {
                value: "Right Child",
                children: vec![],
            },
        ],
        root: Some(0),
    };

    // Collect values via the zero-boilerplate iterator loop
    let visited: Vec<&str> = tree
        .dfs_iter()
        .map(|node| node.value)
        .collect();

    assert_eq!(visited, vec!["Root", "Left Child", "Right Child"]);
    println!("{visited:?}");
}
