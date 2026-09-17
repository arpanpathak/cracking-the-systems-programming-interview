use std::cmp::Reverse;
use std::collections::{BinaryHeap, HashMap};
use std::hash::Hash;

struct Edge<Node> {
    to: Node,
    weight: u64,
}

type AdjMap<Node> = HashMap<Node, Vec<Edge<Node>>>;

fn dijkstra_ssmd_shortest<Node>(graph: &AdjMap<Node>, start: Node) -> HashMap<Node, u64>
where
    Node: Clone + Hash + Ord,
{
    let mut dist = HashMap::from([(start.clone(), 0)]);
    let mut heap = BinaryHeap::from([Reverse((0u64, start))]);

    while let Some(Reverse((cost, node))) = heap.pop() {
        if cost > dist[&node] {
            continue; // stale entry
        }
        let Some(edges) = graph.get(&node) else { continue }; // node with no outgoing edges

        for edge in edges {
            let Some(new_cost) = cost.checked_add(edge.weight) else { continue }; // overflow
            if dist.get(&edge.to).is_none_or(|&d| new_cost < d) {
                dist.insert(edge.to.clone(), new_cost);
                heap.push(Reverse((new_cost, edge.to.clone())));
            }
        }
    }
    dist
}

fn main() {
    let graph: AdjMap<&str> = HashMap::from([
        ("A", vec![Edge { to: "B", weight: 4 }, Edge { to: "C", weight: 1 }]),
        ("B", vec![Edge { to: "D", weight: 1 }]),
        ("C", vec![Edge { to: "B", weight: 2 }, Edge { to: "D", weight: 5 }]),
    ]); // "D" has no entry now, and it no longer panics

    println!("{:?}", dijkstra_ssmd_shortest(&graph, "A"));
}
