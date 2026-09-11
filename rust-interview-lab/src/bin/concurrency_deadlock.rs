//! Deadlock detection: a deadlock exists exactly when the wait-for graph has a
//! cycle. Each edge `(waiter, holder)` means the first task is blocked on the
//! second.
//!
//! Run with: cargo run --bin concurrency_deadlock

/// Iterative-friendly depth-first search over a small adjacency list.
fn has_deadlock(waits_for: &[(usize, usize)]) -> bool {
    let Some(highest) = waits_for.iter().flat_map(|(a, b)| [*a, *b]).max() else {
        return false;
    };

    let mut edges = vec![Vec::new(); highest + 1];
    for (waiter, holder) in waits_for {
        edges[*waiter].push(*holder);
    }

    // 1 = on the current path, 2 = fully explored.
    fn visit(node: usize, edges: &[Vec<usize>], state: &mut [u8]) -> bool {
        match state[node] {
            1 => return true,
            2 => return false,
            _ => state[node] = 1,
        }
        for &next in &edges[node] {
            if visit(next, edges, state) {
                return true;
            }
        }
        state[node] = 2;
        false
    }

    let mut state = vec![0u8; edges.len()];
    (0..edges.len()).any(|node| visit(node, &edges, &mut state))
}

fn main() {
    let acyclic = [(0, 1), (1, 2), (0, 2)];
    let cycle = [(0, 1), (1, 2), (2, 0)];
    let self_wait = [(0, 0)];

    for (label, graph) in [
        ("0->1, 1->2, 0->2", &acyclic[..]),
        ("0->1, 1->2, 2->0", &cycle[..]),
        ("0->0", &self_wait[..]),
    ] {
        println!("{label:<20} deadlock: {}", has_deadlock(graph));
    }

    // The four Coffman conditions must all hold for a deadlock; removing any one
    // of them prevents it.
    println!("\nCoffman conditions:");
    for condition in [
        "mutual exclusion",
        "hold and wait",
        "no preemption",
        "circular wait",
    ] {
        println!("  - {condition}");
    }

    assert!(!has_deadlock(&acyclic));
    assert!(has_deadlock(&cycle));
    assert!(has_deadlock(&self_wait));
    assert!(!has_deadlock(&[]));

    println!("\nall checks passed");
}
