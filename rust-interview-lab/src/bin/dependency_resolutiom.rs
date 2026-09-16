use std::collections::{HashMap, VecDeque};

#[derive(Clone)]
struct Course {
    name: String,
    depends_on: Vec<String>,
}

fn topo_sort(courses: &[Course]) -> Vec<String> {
    let mut adj: HashMap<String, Vec<String>> = HashMap::new();
    let mut indegree: HashMap<String, usize> = HashMap::new();

    for Course { name, depends_on } in courses {
        indegree.insert(name.clone(), depends_on.len());
        adj.entry(name.clone()).or_default();
        for dep in depends_on {
            adj.entry(dep.clone()).or_default().push(name.clone());
            indegree.entry(dep.clone()).or_insert(0);
        }
    }

    let mut queue: VecDeque<_> = indegree
        .iter()
        .filter(|&(_, deg)| *deg == 0)
        .map(|(name, _)| name.clone())
        .collect();

    let mut order = Vec::new();
    while let Some(node) = queue.pop_front() {
        for next in &adj[&node] {
            let d = indegree.get_mut(next).unwrap();
            *d -= 1;
            if *d == 0 {
                queue.push_back(next.clone());
            }
        }
        order.push(node);
    }
    
    if order.len() == indegree.len() { order } else { Vec::new() }
}

fn main() {
    let courses = vec![
        Course { name: "algos".into(), depends_on: vec!["datastructs".into()] },
        Course { name: "compilers".into(), depends_on: vec!["algos".into(), "os".into()] },
        Course { name: "os".into(), depends_on: vec!["datastructs".into()] },
    ];


    let coned2 = courses.clone();

    println!("{:?}", topo_sort(&courses));
}