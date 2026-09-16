use std::cmp::Ordering::{Equal, Greater, Less};

#[derive(Debug)]
struct Edge { u: usize, v: usize, w: u32 }

struct DisjointSet { parent: Vec<usize>, rank: Vec<usize> }

impl DisjointSet  {
    fn new(n: usize) -> Self {
        Self {
            parent: (0..n).collect(),
            rank: vec![0; n]
        }
    }

    fn find(&mut self, elem: usize) -> usize{
        if self.parent[elem] != elem {
            self.parent[elem] = self.find(self.parent[elem]);
        }

        self.parent[elem]
    }

    fn union(&mut self, x: usize, y: usize) -> bool {
        let (x, y) = (self.find(x), self.find(y));

        if x == y { return false;}
 
        // Note for self : Comparator requires a reference
        match self.rank[x].cmp(&self.rank[y]) {
            Less => self.parent[x] = y,
            Greater => self.parent[y] = x,
            Equal => {
                self.parent[x] = y;
                self.rank[y] += 1;
            } 
        }

        true
    }
}

fn kruskals(n: usize, mut edges: Vec<Edge>) -> Vec<Edge> {
    // Greedy algorothm, sort the edges by weight
    edges.sort_by_key(|e| e.w);

    let mut uf = DisjointSet::new(n);
    let mut mst = Vec::new();

    for edge in edges {
        if uf.union(edge.u, edge.v) {
            mst.push(edge);
        }
    }

    mst

}

fn main() {
     let edges = vec![
        Edge { u: 0, v: 1, w: 4 },
        Edge { u: 0, v: 2, w: 3 },
        Edge { u: 1, v: 2, w: 1 },
        Edge { u: 1, v: 3, w: 2 },
        Edge { u: 2, v: 3, w: 4 },
        Edge { u: 3, v: 4, w: 2 },
    ];

    let mst = kruskals(5, edges);
    let total: u32 = mst.iter().map(|e| e.w).sum();

    for e in &mst {
        println!("{} - {} ({})", e.u, e.v, e.w);
    }
    println!("total: {total}");
}
