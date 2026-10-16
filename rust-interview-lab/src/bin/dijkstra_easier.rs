use std::cmp::Reverse as Rev;
use std::collections::{BinaryHeap, HashMap};
use std::hash::Hash;

fn dijkstra<N: Eq + Hash + Clone + Ord>(
    graph: &HashMap<N, Vec<(N, u32)>>,
    start: N,
) -> HashMap<N, u32> {
    let mut dist = HashMap::from([(start.clone(), 0)]);
    let mut heap = BinaryHeap::from([Rev((0, start))]);

    while let Some(Rev((d, u))) = heap.pop() {
        if d > dist[&u] { continue }
        let Some(neighbors) = graph.get(&u) else { continue };

        for (v, w) in neighbors {
            let nd = d + w;
            if dist.get(v).is_none_or(|&old| nd < old) {
                dist.insert(v.clone(), nd);
                heap.push(Rev((nd, v.clone())));
            }
        }
    }
    dist
}

fn main() {
    let graph = HashMap::from([
        ("A", vec![("B", 1), ("D", 4)]),
        ("B", vec![("A", 1), ("C", 2), ("E", 1)]),
        ("C", vec![("B", 2), ("F", 1)]),
        ("D", vec![("A", 4), ("E", 1)]),
        ("E", vec![("B", 1), ("D", 1), ("F", 3)]),
        ("F", vec![("C", 1), ("E", 3)]),
    ]);
    println!("{:?}", dijkstra(&graph, "A"));
}
