//! Dijkstra's shortest paths with a binary min-heap.
//!
//! Two variants of the same algorithm:
//!
//! - `dijkstra_vec`: nodes are `usize` indices and distances are a
//!   `Vec<Option<u32>>`, where `None` means unreachable.
//! - `dijkstra`: nodes are any `Copy + Eq + Hash + Ord` type and distances are a
//!   `HashMap` containing only the reachable nodes.
//!
//! Edge weights must be non-negative, which `u32` guarantees. `BinaryHeap` is a
//! max-heap, so entries are wrapped in `Reverse` to pop the smallest cost first.
//! A node can be in the heap several times; an entry whose cost is larger than the
//! recorded distance is stale and skipped.

use crate::problems::graph_bfs::GraphAdjList;
use std::cmp::Reverse;
use std::collections::{BinaryHeap, HashMap};
use std::hash::Hash;

/// Shortest distances from `start_node` over an index-based adjacency list.
pub fn dijkstra_vec(graph: &[Vec<(usize, u32)>], start_node: usize) -> Vec<Option<u32>> {
    let mut distances = vec![None; graph.len()];
    let mut min_heap = BinaryHeap::from([Reverse((0, start_node))]);

    distances[start_node] = Some(0);

    while let Some(Reverse((current_cost, current_node))) = min_heap.pop() {
        // stale heap entry, a shorter path was already recorded
        if distances[current_node].is_some_and(|best| current_cost > best) {
            continue;
        }
        for &(neighbor, weight) in &graph[current_node] {
            let new_distance = current_cost + weight;
            if distances[neighbor].is_none_or(|best| new_distance < best) {
                distances[neighbor] = Some(new_distance);
                min_heap.push(Reverse((new_distance, neighbor)));
            }
        }
    }
    distances
}

/// Shortest distances from `start_node` over a `HashMap` adjacency list.
pub fn dijkstra<Node>(graph: &GraphAdjList<Node>, start_node: Node) -> HashMap<Node, u32>
where
    Node: Copy + Eq + Hash + Ord,
{
    let mut distances = HashMap::from([(start_node, 0)]);
    let mut min_heap = BinaryHeap::from([Reverse((0, start_node))]);

    while let Some(Reverse((current_cost, current_node))) = min_heap.pop() {
        // stale heap entry, a shorter path was already recorded
        if current_cost > distances[&current_node] {
            continue;
        }
        for &(neighbor, weight) in graph[&current_node] {
            let new_distance = current_cost + weight;

            if new_distance < *distances.get(&neighbor).unwrap_or(&u32::MAX) {
                distances.insert(neighbor, new_distance);
                min_heap.push(Reverse((new_distance, neighbor)));
            }
        }
    }
    distances
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
    fn vec_variant_finds_shorter_multi_hop_paths() {
        // A -> C directly costs 4, A -> B -> C costs 3; D is reached via C for 4.
        assert_eq!(
            dijkstra_vec(&sample_vec(), 0),
            vec![Some(0), Some(1), Some(3), Some(4)]
        );
    }

    #[test]
    fn vec_variant_marks_unreachable_nodes() {
        let graph = vec![vec![(1, 7)], vec![], vec![(0, 1)]];
        assert_eq!(dijkstra_vec(&graph, 0), vec![Some(0), Some(7), None]);
    }

    #[test]
    fn map_variant_finds_shorter_multi_hop_paths() {
        let distances = dijkstra(&sample_map(), "A");
        assert_eq!(
            distances,
            HashMap::from([("A", 0), ("B", 1), ("C", 3), ("D", 4)])
        );
    }

    #[test]
    fn map_variant_omits_unreachable_nodes() {
        let graph: HashMap<u8, &[(u8, u32)]> =
            HashMap::from([(0, &[(1, 2)][..]), (1, &[][..]), (2, &[(0, 1)][..])]);
        assert_eq!(dijkstra(&graph, 0), HashMap::from([(0, 0), (1, 2)]));
    }
}
