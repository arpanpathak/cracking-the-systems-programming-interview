//! Breadth-first search.
//!
//! Two variants of the same algorithm:
//!
//! - `bfs_vec`: nodes are `usize` indices and the graph is `Vec<Vec<(usize, u32)>>`,
//!   so `visited` is a plain `Vec<bool>`. This is the version to write first.
//! - `bfs`: nodes are any `Copy + Eq + Hash` type and the graph is a `HashMap`
//!   from a node to a slice of `(neighbor, weight)` edges.

use std::collections::{HashMap, HashSet, VecDeque};
use std::hash::Hash;

/// Adjacency list keyed by node: each node maps to its `(neighbor, weight)` edges.
pub type GraphAdjList<'a, Node> = HashMap<Node, &'a [(Node, u32)]>;

/// BFS over an index-based adjacency list. Returns nodes in visiting order.
pub fn bfs_vec(graph: &[Vec<(usize, u32)>], start_node: usize) -> Vec<usize> {
    let mut visited = vec![false; graph.len()];
    let mut queue = VecDeque::from([start_node]);
    let mut result = vec![];

    visited[start_node] = true;

    while let Some(current_node) = queue.pop_front() {
        result.push(current_node);
        for &(neighbor, _) in &graph[current_node] {
            if !visited[neighbor] {
                visited[neighbor] = true;
                queue.push_back(neighbor);
            }
        }
    }
    result
}

/// BFS over a `HashMap` adjacency list. Returns nodes in visiting order.
pub fn bfs<Node>(graph: &GraphAdjList<Node>, start_node: Node) -> Vec<Node>
where
    Node: Copy + Eq + Hash,
{
    let mut visited = HashSet::new();
    let mut queue = VecDeque::from([start_node]);
    let mut result = vec![];

    visited.insert(start_node);

    while let Some(current_node) = queue.pop_front() {
        result.push(current_node);
        // slice iter yields &(Node, u32); `&` destructures it
        for &(neighbor, _) in graph[&current_node] {
            if visited.insert(neighbor) {
                queue.push_back(neighbor);
            }
        }
    }
    result
}

#[cfg(test)]
mod tests {
    use super::*;

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
    fn vec_variant_visits_level_by_level() {
        assert_eq!(bfs_vec(&sample_vec(), 0), vec![0, 1, 2, 3]);
    }

    #[test]
    fn vec_variant_skips_unreachable_nodes() {
        let graph = vec![vec![(1, 1)], vec![], vec![(0, 1)]];
        assert_eq!(bfs_vec(&graph, 0), vec![0, 1]);
    }

    #[test]
    fn vec_variant_handles_cycles() {
        let graph = vec![vec![(1, 1)], vec![(0, 1)]];
        assert_eq!(bfs_vec(&graph, 0), vec![0, 1]);
    }

    #[test]
    fn map_variant_visits_level_by_level() {
        assert_eq!(bfs(&sample_map(), "A"), vec!["A", "B", "C", "D"]);
    }

    #[test]
    fn both_variants_agree() {
        let names = ["A", "B", "C", "D"];
        let from_vec: Vec<&str> = bfs_vec(&sample_vec(), 0)
            .into_iter()
            .map(|index| names[index])
            .collect();
        assert_eq!(from_vec, bfs(&sample_map(), "A"));
    }
}
