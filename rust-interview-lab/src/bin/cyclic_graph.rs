use std::collections::VecDeque;

type NodeId = usize;

struct Graph<T> {
    nodes: Vec<T>,
    adj: Vec<Vec<NodeId>>, // adj[i] = nodes that i points to
}

#[derive(Clone, Copy)]
enum State { Unvisited, Visiting, Done }

impl<T> Graph<T> {
    fn new() -> Self { 
        Self { nodes: Vec::new(), adj: Vec::new() }
    }

    fn add_node(&mut self, data: T) -> NodeId {
        self.nodes.push(data);
        self.adj.push(Vec::new());
        self.nodes.len() - 1
    }

    fn add_edge(&mut self, from: NodeId, to: NodeId) {
        self.adj[from].push(to);
    }

    fn neighbors(&self, id: NodeId) -> impl Iterator<Item = NodeId> + '_ {
        self.adj[id].iter().copied()
    }

    fn bfs(&self, start: NodeId) -> Vec<NodeId> {
        let mut visited = vec![false; self.nodes.len()];
        let mut queue = VecDeque::from([start]);
        let mut order = Vec::new();
        visited[start] = true;

        while let Some(node) = queue.pop_front() {
            order.push(node);
            for next in self.neighbors(node) {
                if !visited[next] {
                    visited[next] = true;
                    queue.push_back(next);
                }
            }
        }
        order
    }

    fn dfs(&self, start: NodeId) -> Vec<NodeId> {
        let mut visited = vec![false; self.nodes.len()];
        let mut stack = vec![start];
        let mut order = Vec::new();

        while let Some(node) = stack.pop() {
            if visited[node] {
                continue;
            }
            visited[node] = true;
            order.push(node);
            stack.extend(self.neighbors(node).filter(|&n| !visited[n]));
        }
        order
    }

    fn has_cycle(&self) -> bool {
        let mut state = vec![State::Unvisited; self.nodes.len()];
        (0..self.nodes.len()).any(|n| self.visit(n, &mut state))
    }

    fn visit(&self, node: NodeId, state: &mut [State]) -> bool {
        match state[node] {
            State::Visiting => true, // back edge: cycle found
            State::Done => false,
            State::Unvisited => {
                state[node] = State::Visiting;
                let found = self.adj[node].iter().any(|&n| self.visit(n, state));
                state[node] = State::Done;
                found
            }
        }
    }
}

fn main() {
    let mut g = Graph::new();
    let a = g.add_node("A");
    let b = g.add_node("B");
    let c = g.add_node("C");

    g.add_edge(a, b);
    g.add_edge(b, c);
    g.add_edge(c, a); // closes the cycle

    let names = |ids: Vec<NodeId>| -> Vec<&str> {
        ids.into_iter().map(|i| g.nodes[i]).collect()
    };

    println!("BFS:   {:?}", names(g.bfs(a)));   // ["A", "B", "C"]
    println!("DFS:   {:?}", names(g.dfs(a)));   // ["A", "B", "C"]
    println!("Cycle: {}", g.has_cycle());       // true
}
