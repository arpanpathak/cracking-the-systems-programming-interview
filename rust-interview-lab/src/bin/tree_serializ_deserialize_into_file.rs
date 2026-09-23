use std::collections::VecDeque;
use std::fs;
use std::io;
use std::str::FromStr;

#[derive(Debug)]
struct TreeNode<T> {
    value: T,
    children: Vec<TreeNode<T>>,
}

impl<T> TreeNode<T> {
    fn level_order(&self) -> Vec<Vec<&T>> {
        let mut result = Vec::new();
        let mut queue = VecDeque::from([self]);

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

    fn serialize(&self) -> Vec<String>
    where
        T: ToString,
    {
        let mut serialized = Vec::new();
        let mut stack = vec![self];

        while let Some(node) = stack.pop() {
            serialized.push(node.value.to_string());
            serialized.push(node.children.len().to_string());

            for child in node.children.iter().rev() {
                stack.push(child);
            }
        }

        serialized
    }

    fn deserialize(serialized: &[String], pos: &mut usize) -> Option<Self>
    where
        T: FromStr,
    {
        let value = serialized.get(*pos)?.parse().ok()?;
        let child_count: usize = serialized.get(*pos + 1)?.parse().ok()?;
        *pos += 2;

        let mut children = Vec::new();
        for _ in 0..child_count {
            children.push(Self::deserialize(serialized, pos)?);
        }

        Some(TreeNode { value, children })
    }

    fn save(&self, path: &str) -> io::Result<()>
    where
        T: ToString,
    {
        fs::write(path, self.serialize().join("\n"))
    }

    fn load(path: &str) -> Option<Self>
    where
        T: FromStr,
    {
        let text = fs::read_to_string(path).ok()?;
        let serialized: Vec<String> = text.lines().map(String::from).collect();
        Self::deserialize(&serialized, &mut 0)
    }
}

fn main() -> io::Result<()> {
    let root = TreeNode {
        value: "root".to_string(),
        children: vec![
            TreeNode {
                value: "a".to_string(),
                children: vec![
                    TreeNode { value: "a1".to_string(), children: vec![] },
                    TreeNode { value: "a2".to_string(), children: vec![] },
                ],
            },
            TreeNode {
                value: "b".to_string(),
                children: vec![TreeNode { value: "b1".to_string(), children: vec![] }],
            },
        ],
    };

    root.save("tree.bin")?;

    let Some(loaded) = TreeNode::<String>::load("tree.bin") else {
        println!("invalid tree file");
        return Ok(());
    };

    for level in loaded.level_order() {
        println!("{:?}", level);
    }

    Ok(())
}
