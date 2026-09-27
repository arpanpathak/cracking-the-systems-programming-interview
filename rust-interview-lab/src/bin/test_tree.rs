use std::collections::VecDeque;

struct TreeNode<T> {
    value: T,
    children: Vec<TreeNode<T>>, // Owned children directly inline
}

impl<T> TreeNode<T> 
where 
    T: Clone + std::fmt::Display
{
    
    /// Recursive DFS (Pre-order) - No callbacks
    pub fn dfs(&self) {
        println!("{}", self.value);
        for child in self.children.iter() {
            child.dfs();
        }
    }

    /// Level Order BFS - Idiomatic VecDeque::from([self])
    pub fn bfs(&self) {
        let mut queue = VecDeque::from([self]); // Idiomatic initialization

        while let Some(node) = queue.pop_front() {
            println!("{}", node.value);
            
            for child in &node.children {
                queue.push_back(child);
            }
        }
    }
}

fn main() {
    // --- Inline Construction (No variables, no push) ---
    
    let root = TreeNode {
        value: 1,
        children: vec![
            TreeNode {
                value: 2,
                children: vec![
                    TreeNode { value: 4, children: vec![] },
                    TreeNode { value: 5, children: Vec::new() },
                ],
            },
            TreeNode {
                value: 3,
                children: vec![TreeNode { value: 6, children: Vec::new() }],
            },
        ],
    };

    println!("=== DFS ===");
    root.dfs(); 
    // Output: 1, 2, 4, 5, 3, 6

    println!("\n=== BFS ===");
    root.bfs();
    // Output: 1, 2, 3, 4, 5, 6
}

