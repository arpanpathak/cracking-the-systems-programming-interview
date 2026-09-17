use std::cmp::Reverse;
use std::collections::{BinaryHeap, HashMap};
use std::hash::Hash;

#[derive(Debug)]
struct Edge<Node> {
    to: Node,
    weight: u64,
}

type AdjMap<Node> = HashMap<Node, Vec<Edge<Node>>>;

fn dijkstra_ssmd_shortest<'a, Node>(graph: &'a AdjMap<Node>, start: &'a Node) -> HashMap<&'a Node, u64>
where
    Node: Hash + Ord,
{
    let mut dist = HashMap::from([(start, 0u64)]);
    let mut heap = BinaryHeap::from([Reverse((0u64, start))]);

    while let Some(Reverse((cost, node))) = heap.pop() {
        if cost > dist[node] {
            continue; // stale entry
        }
        let Some(edges) = graph.get(node) else { continue };

        for edge in edges {
            let Some(new_cost) = cost.checked_add(edge.weight) else { continue };
            if dist.get(&edge.to).is_none_or(|&d| new_cost < d) {
                dist.insert(&edge.to, new_cost);
                heap.push(Reverse((new_cost, &edge.to)));
            }
        }
    }
    dist
}

fn main() {
    let graph: AdjMap<String> = HashMap::from([
        ("A".into(), vec![Edge { to: "B".into(), weight: 4 }, Edge { to: "C".into(), weight: 1 }]),
        ("B".into(), vec![Edge { to: "D".into(), weight: 1 }]),
        ("C".into(), vec![Edge { to: "B".into(), weight: 2 }, Edge { to: "D".into(), weight: 5 }]),
    ]);

    println!("Graph => {:#?}", graph);

    let start = "A".into();
    println!("Shortest path {:#?}", dijkstra_ssmd_shortest(&graph, &start)); // A:0, C:1, B:3, D:4
}
