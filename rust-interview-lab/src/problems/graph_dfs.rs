//! Iterative depth-first search with an explicit stack.
//!
//! Two variants of the same algorithm:
//!
//! - `dfs_vec`: nodes are `usize` indices and the graph is `Vec<Vec<(usize, u32)>>`.
//! - `dfs`: nodes are any `Copy + Eq + Hash` type and the graph is a `HashMap`.
//!
//! A node is marked visited when it is popped, not when it is pushed, so it may
//! sit on the stack more than once. Neighbors are pushed in order, which means the
//! last neighbor is explored first.

use crate::problems::graph_bfs::GraphAdjList;
use std::collections::HashSet;
use std::hash::Hash;

/// DFS over an index-based adjacency list. Returns nodes in visiting order.
pub fn dfs_vec(graph: &[Vec<(usize, u32)>], start_node: usize) -> Vec<usize> {
    let mut visited = vec![false; graph.len()];
    let mut stack = vec![start_node];
    let mut result = vec![];

    while let Some(current_node) = stack.pop() {
        if visited[current_node] {
            continue;
        }
        visited[current_node] = true;
        result.push(current_node);
        for &(neighbor, _) in &graph[current_node] {
            stack.push(neighbor);
        }
    }
    result
}

/// DFS over a `HashMap` adjacency list. Returns nodes in visiting order.
pub fn dfs<Node>(graph: &GraphAdjList<Node>, start_node: Node) -> Vec<Node>
where
    Node: Copy + Eq + Hash,
{
    let mut visited = HashSet::new();
    let mut stack = vec![start_node];
    let mut result = vec![];

    while let Some(current_node) = stack.pop() {
        if !visited.insert(current_node) {
            continue;
        }
        result.push(current_node);
        for &(neighbor, _) in graph[&current_node] {
            stack.push(neighbor);
        }
    }
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;

    /// A -> B (1), A -> C (4), B -> C (2), B -> D (5), C -> D (1)
    fn sample_vec() -> Vec<Vec<(usize, u32)>> {
        vec![
            vec![(1, 1), (2, 4)],
            vec![(2, 2), (3, 5)],
            vec![(3, 1)],
            vec![],
        ]
    }

    fn sample_map() -> HashMap<&'static str, &'static [(&'static str, u32)]> {
        HashMap::from([
            ("A", &[("B", 1), ("C", 4)][..]),
            ("B", &[("C", 2), ("D", 5)][..]),
            ("C", &[("D", 1)][..]),
            ("D", &[][..]),
        ])
    }

    #[test]
    fn vec_variant_explores_the_last_neighbor_first() {
        // Pop 0, push 1 and 2; pop 2, push 3; pop 3; pop 1.
        assert_eq!(dfs_vec(&sample_vec(), 0), vec![0, 2, 3, 1]);
    }

    #[test]
    fn vec_variant_handles_cycles() {
        let graph = vec![vec![(1, 1)], vec![(2, 1)], vec![(0, 1)]];
        assert_eq!(dfs_vec(&graph, 0), vec![0, 1, 2]);
    }

    #[test]
    fn map_variant_explores_the_last_neighbor_first() {
        assert_eq!(dfs(&sample_map(), "A"), vec!["A", "C", "D", "B"]);
    }

    #[test]
    fn both_variants_agree() {
        let names = ["A", "B", "C", "D"];
        let from_vec: Vec<&str> = dfs_vec(&sample_vec(), 0)
            .into_iter()
            .map(|index| names[index])
            .collect();
        assert_eq!(from_vec, dfs(&sample_map(), "A"));
    }
}
