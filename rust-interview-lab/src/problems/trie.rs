//! Trie / prefix tree.
//!
//! Relevant to NVIDIA-style SDK/CLI/codegen work: autocomplete, filtering GPU
//! SKUs, command completion, and prefix matching.

use std::collections::HashMap;

#[derive(Default)]
pub struct Trie {
    root: Node,
}

#[derive(Default)]
struct Node {
    children: HashMap<char, Node>,
    terminal: bool,
}

impl Trie {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn insert(&mut self, word: &str) {
        let mut node = &mut self.root;
        for ch in word.chars() {
            node = node.children.entry(ch).or_default();
        }
        node.terminal = true;
    }

    pub fn search(&self, word: &str) -> bool {
        self.find_node(word).is_some_and(|node| node.terminal)
    }

    pub fn starts_with(&self, prefix: &str) -> bool {
        self.find_node(prefix).is_some()
    }

    fn find_node(&self, word: &str) -> Option<&Node> {
        let mut node = &self.root;
        for ch in word.chars() {
            node = node.children.get(&ch)?;
        }
        Some(node)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn trie_insert_search_and_prefix() {
        let mut trie = Trie::new();
        trie.insert("gpu");
        trie.insert("gpucloud");

        assert!(trie.search("gpu"));
        assert!(trie.search("gpucloud"));
        assert!(!trie.search("gp"));
        assert!(!trie.search("gpucloudapi"));

        assert!(trie.starts_with("gp"));
        assert!(trie.starts_with("gpucloud"));
        assert!(!trie.starts_with("h100"));
    }
}
