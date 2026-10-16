use std::cmp::Reverse;
use std::collections::{BinaryHeap, HashMap};
use std::hash::Hash;

/// Eq and Ord trait is required by heap to compare. Clone us for imutability. For larger graph, use
/// reference. Node key must be hashable, in order to store in a HashMap.
fn dijkstra<Node>(
    graph: &HashMap<Node, &[(Node, u32)]>,
    start: Node,
) -> HashMap<Node, u32>
where 
    Node: Eq + Hash + Clone + Ord {

    let mut dist = HashMap::from([(start.clone(), 0)]);
    let mut heap = BinaryHeap::from([Reverse((0, &start))]);

    while let Some(Reverse((d, u))) = heap.pop() {
        if d > dist[&u] { continue }
        let Some(neighbors) = graph.get(&u) else { continue };

        for (v, w) in *neighbors {
            let nd = d + w;
            if dist.get(v).is_none_or(|&old| nd < old) {
                dist.insert(v.clone(), nd);
                heap.push(Reverse((nd, v)));
            }
        }
    }
    dist
}

fn main() {
    let graph = HashMap::from([
        ("A", &[("B", 1), ("D", 4)][..]),
        ("B", &[("A", 1), ("C", 2), ("E", 1)][..]),
        ("C", &[("B", 2), ("F", 1)][..]),
        ("D", &[("A", 4), ("E", 1)][..]),
        ("E", &[("B", 1), ("D", 1), ("F", 3)][..]),
        ("F", &[("C", 1), ("E", 3)][..]),
    ]);
    println!("{:?}", dijkstra(&graph, "A"));
}
