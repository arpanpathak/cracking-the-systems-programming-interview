use std::collections::{HashMap, HashSet, VecDeque};

#[derive(Default)]
struct Graph {
    ids: HashMap<String, usize>,
    adj: Vec<Vec<usize>>,
}

impl Graph {
    fn id(&mut self, name: &str) -> usize {
        *self
            .ids
            .entry(name.to_owned())
            .or_insert_with(|| {
                self.adj.push(vec![]);
                self.adj.len() - 1
            })
    }

    fn add_edge(&mut self, from: &str, to: &str) {
        let (u, v) = (self.id(from), self.id(to));
        self.adj[u].push(v);
    }

    fn bfs(&self, start: &str) -> Vec<usize> {
        let mut visited = HashSet::new();
        let mut queue = VecDeque::from([self.ids[start]]);
        let mut order = Vec::new();

        while let Some(node) = queue.pop_front() {
            if !visited.insert(node) {
                continue;
            }
            order.push(node);
            queue.extend(self.adj[node].iter());
        }
        order
    }
}

fn main() {
    let mut g = Graph::default();
    g.add_edge("A", "B");
    g.add_edge("A", "C");
    g.add_edge("B", "D");
    g.add_edge("C", "E");
    g.add_edge("D", "F");

    println!("{:?}", g.bfs("A")); // [0, 1, 2, 3, 4, 5]
}
