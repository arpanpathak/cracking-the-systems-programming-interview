//! Command ringsim measures a consistent hash ring. It places 100000 keys on
//! rings of 24 nodes with different numbers of virtual nodes and prints how
//! evenly the keys are spread. Then it adds a 25th node and counts the keys
//! whose owner changed, on the ring and under `hash mod N`.
//!
//! Run it from code/ with:
//!
//!     cargo run --release -p ringsim

// ANCHOR: imports
use std::collections::HashMap;

use ring::{Ring, position};
// ANCHOR_END: imports

// ANCHOR: setup
const NODES: usize = 24;
const KEYS: usize = 100_000;

fn node_name(number: usize) -> String {
    format!("node-{number}")
}

fn keys() -> impl Iterator<Item = String> {
    (0..KEYS).map(|number| format!("key-{number}"))
}

fn ring_of(nodes: usize, virtual_nodes: u32) -> Ring {
    let mut ring = Ring::new(virtual_nodes);

    for number in 1..=nodes {
        ring.add(&node_name(number));
    }

    ring
}
// ANCHOR_END: setup

// ANCHOR: spread
/// Prints the smallest and the largest share of the keys that a node owns.
fn spread(virtual_nodes: u32) {
    let ring = ring_of(NODES, virtual_nodes);
    let mut counts: HashMap<&str, usize> = HashMap::new();

    for key in keys() {
        if let Some(node) = ring.owner(&key) {
            *counts.entry(node).or_default() += 1;
        }
    }

    let share = |count: usize| 100.0 * count as f64 / KEYS as f64;
    let smallest = (1..=NODES)
        .map(|n| {
            counts
                .get(node_name(n).as_str())
                .copied()
                .unwrap_or(0)
        })
        .min()
        .unwrap_or(0);
    let largest = counts
        .values()
        .copied()
        .max()
        .unwrap_or(0);

    println!(
        "  {virtual_nodes:4} tokens per node: smallest share {:5.2}%, largest share {:5.2}%",
        share(smallest),
        share(largest)
    );
}
// ANCHOR_END: spread

// ANCHOR: growth
/// Adds a 25th node and counts the keys whose owner changed.
fn growth(virtual_nodes: u32) {
    let before = ring_of(NODES, virtual_nodes);
    let mut after = before.clone();
    let added = node_name(NODES + 1);
    after.add(&added);

    let moved: Vec<String> = keys()
        .filter(|key| before.owner(key) != after.owner(key))
        .collect();
    let to_new = moved
        .iter()
        .filter(|key| after.owner(key) == Some(added.as_str()))
        .count();
    let by_modulo = keys()
        .filter(|key| position(key) % NODES as u64 != position(key) % (NODES as u64 + 1))
        .count();
    let percent = |count: usize| 100.0 * count as f64 / KEYS as f64;

    println!(
        "  on the ring: {} keys changed owner ({:.2}%), {} of them to the new node",
        moved.len(),
        percent(moved.len()),
        to_new
    );
    println!(
        "  hash mod N : {by_modulo} keys changed owner ({:.2}%)",
        percent(by_modulo)
    );
}
// ANCHOR_END: growth

// ANCHOR: main
fn main() {
    println!(
        "{KEYS} keys on {NODES} nodes, ideal share {:.2}%",
        100.0 / NODES as f64
    );

    for virtual_nodes in [1, 8, 64, 256] {
        spread(virtual_nodes);
    }

    println!(
        "adding node 25 to a ring with 256 tokens per node, ideal movement {:.2}%",
        100.0 / (NODES as f64 + 1.0)
    );
    growth(256);

    let ring = ring_of(NODES, 256);
    println!(
        "replicas of user-1: {}",
        ring.replicas("user-1", 3)
            .join(", ")
    );
    println!("position of user-1: {:#018x}", position("user-1"));
}
// ANCHOR_END: main
