//! Topological sort (Kahn's algorithm).
//!
//! Common in NVIDIA-style scheduling questions: prerequisite graphs, pipeline
//! stages, dependency ordering of GPU jobs.

use std::collections::VecDeque;

pub fn topological_sort(num_nodes: usize, edges: &[(usize, usize)]) -> Option<Vec<usize>> {
    let mut graph = vec![Vec::new(); num_nodes];
    let mut indegree = vec![0usize; num_nodes];

    for &(from, to) in edges {
        graph[from].push(to);
        indegree[to] += 1;
    }

    let mut queue: VecDeque<usize> = (0..num_nodes).filter(|&n| indegree[n] == 0).collect();
    let mut order = Vec::with_capacity(num_nodes);

    while let Some(node) = queue.pop_front() {
        order.push(node);

        for &next in &graph[node] {
            indegree[next] -= 1;
            if indegree[next] == 0 {
                queue.push_back(next);
            }
        }
    }

    (order.len() == num_nodes).then_some(order)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn returns_order_for_dag() {
        // 0 -> 1, 0 -> 2, 1 -> 3, 2 -> 3
        let edges = [(0, 1), (0, 2), (1, 3), (2, 3)];
        let order = topological_sort(4, &edges).expect("DAG has an order");
        assert_eq!(order.len(), 4);
        assert!(
            order.iter().position(|&n| n == 0).unwrap()
                < order.iter().position(|&n| n == 1).unwrap()
        );
        assert!(
            order.iter().position(|&n| n == 1).unwrap()
                < order.iter().position(|&n| n == 3).unwrap()
        );
    }

    #[test]
    fn detects_cycle() {
        // 0 -> 1 -> 0 is a cycle.
        let edges = [(0, 1), (1, 0)];
        assert_eq!(topological_sort(2, &edges), None);
    }

    #[test]
    fn disconnected_nodes_are_included() {
        let edges = [(0, 1)];
        let order = topological_sort(3, &edges).expect("DAG has an order");
        assert_eq!(order.len(), 3);
    }
}
