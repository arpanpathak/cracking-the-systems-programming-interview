use std::collections::{HashMap, HashSet, VecDeque};
use std::hash::Hash;

#[derive(Clone, Copy)]
enum State { Visiting, Done }

#[derive(Default)]
struct Graph<T> {
    adj: HashMap<T, Vec<T>>,
}

impl<T: Copy + Eq + Hash> Graph<T> {
    fn add_edge(&mut self, u: T, v: T) {
        self.adj.entry(v).or_default();
        self.adj.entry(u).or_default().push(v);
    }

    fn bfs(&self, start: T) -> Vec<T> {
        let mut seen = HashSet::from([start]);
        let mut queue = VecDeque::from([start]);
        let mut order = vec![];

        while let Some(u) = queue.pop_front() {
            order.push(u);
            for &v in &self.adj[&u] {
                if seen.insert(v) {
                    queue.push_back(v);
                }
            }
        }
        order
    }

    fn has_cycle(&self) -> bool {
        fn dfs<T: Copy + Eq + Hash>(g: &Graph<T>, u: T, state: &mut HashMap<T, State>) -> bool {
            match state.get(&u) {
                Some(State::Visiting) => return true,
                Some(State::Done) => return false,
                None => {}
            }

            state.insert(u, State::Visiting);
            let found = g.adj[&u].iter().any(|&v| dfs(g, v, state));
            state.insert(u, State::Done);
            found
        }

        let mut state = HashMap::new();
        self.adj.keys().any(|&u| dfs(self, u, &mut state))
    }
}

fn main() {
    let mut g = Graph::default();
    g.add_edge("A", "B");
    g.add_edge("B", "C");
    g.add_edge("C", "A");

    println!("{:?}", g.bfs("A"));
    println!("{}", g.has_cycle()); // true
}
