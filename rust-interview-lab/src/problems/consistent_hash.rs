//! Consistent hashing ring.
//!
//! When a distributed gateway shards work across N backends, a plain
//! `hash(key) % N` remaps nearly every key the moment N changes. Consistent
//! hashing places each node at several points on a hash ring, so adding or
//! removing one node only moves the keys that node owns. That property is the
//! reason it shows up in caches, sharded queues, and load balancers.
//!
//! Each physical node is placed at `replicas` points (virtual nodes) to smooth the
//! key distribution; more replicas means a less lumpy ring.

use std::collections::HashSet;
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};
use std::sync::Arc;

/// A hash ring mapping keys to node names.
pub struct ConsistentHash {
    replicas: usize,
    /// Sorted `(hash, node)` pairs. The node name is an `Arc<str>` so that the
    /// many virtual nodes for one physical node share a single allocation.
    ring: Vec<(u64, Arc<str>)>,
}

impl ConsistentHash {
    /// Create an empty ring with `replicas` virtual nodes per physical node.
    /// Panics if `replicas` is zero.
    pub fn new(replicas: usize) -> Self {
        assert!(replicas > 0, "replicas must be > 0");
        Self {
            replicas,
            ring: Vec::new(),
        }
    }

    /// Add a node and its virtual nodes. Adding a node that already exists is a
    /// no-op.
    pub fn add_node(&mut self, node: &str) {
        if self.ring.iter().any(|(_, name)| name.as_ref() == node) {
            return;
        }

        // One allocation for the name, then a refcount bump per virtual node.
        let name: Arc<str> = Arc::from(node);
        for replica in 0..self.replicas {
            let hash = virtual_node_hash(node, replica);
            self.ring.push((hash, Arc::clone(&name)));
        }
        self.ring.sort_by_key(|(hash, _)| *hash);
    }

    /// Remove a node and all of its virtual nodes.
    pub fn remove_node(&mut self, node: &str) {
        self.ring.retain(|(_, name)| name.as_ref() != node);
    }

    /// Return the node responsible for `key`, or `None` when the ring is empty.
    pub fn get(&self, key: &str) -> Option<&str> {
        if self.ring.is_empty() {
            return None;
        }

        let hash = hash_of(key);
        // First virtual node strictly clockwise from the key.
        let index = self.ring.partition_point(|(point, _)| *point <= hash);
        let index = if index == self.ring.len() { 0 } else { index };
        Some(self.ring[index].1.as_ref())
    }

    /// Number of distinct physical nodes.
    pub fn node_count(&self) -> usize {
        self.ring
            .iter()
            .map(|(_, name)| name.as_ref())
            .collect::<HashSet<_>>()
            .len()
    }

    /// Number of virtual nodes on the ring.
    pub fn ring_len(&self) -> usize {
        self.ring.len()
    }
}

fn hash_of(input: &str) -> u64 {
    let mut hasher = DefaultHasher::new();
    input.hash(&mut hasher);
    hasher.finish()
}

/// Hash of the `replica`-th virtual node for `node`.
///
/// Hashing the two fields separately avoids allocating a `"{node}#{replica}"`
/// string for every virtual node on the ring.
fn virtual_node_hash(node: &str, replica: usize) -> u64 {
    let mut hasher = DefaultHasher::new();
    node.hash(&mut hasher);
    replica.hash(&mut hasher);
    hasher.finish()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn empty_ring_has_no_owner() {
        let ring = ConsistentHash::new(64);
        assert_eq!(ring.get("workload-1"), None);
        assert_eq!(ring.node_count(), 0);
    }

    #[test]
    fn lookup_is_stable_for_a_fixed_ring() {
        let mut ring = ConsistentHash::new(64);
        ring.add_node("node-a");
        ring.add_node("node-b");

        let first = ring.get("gpu-job-42").map(str::to_string);
        for _ in 0..100 {
            assert_eq!(ring.get("gpu-job-42").map(str::to_string), first);
        }
        assert!(first.is_some());
    }

    #[test]
    fn keys_spread_across_nodes() {
        let mut ring = ConsistentHash::new(128);
        for node in ["node-a", "node-b", "node-c"] {
            ring.add_node(node);
        }

        let mut counts = std::collections::HashMap::new();
        for key in 0..3_000 {
            let owner = ring.get(&format!("key-{key}")).expect("ring is populated");
            *counts.entry(owner.to_string()).or_insert(0) += 1;
        }

        assert_eq!(counts.len(), 3, "every node should own some keys");
        let smallest = *counts.values().min().expect("non-empty");
        assert!(smallest > 300, "distribution is too lumpy: {counts:?}");
    }

    #[test]
    fn adding_a_node_only_moves_keys_to_the_new_node() {
        let keys: Vec<String> = (0..2_000).map(|i| format!("workload-{i}")).collect();

        let mut ring = ConsistentHash::new(128);
        ring.add_node("node-a");
        ring.add_node("node-b");
        let before: Vec<String> = keys
            .iter()
            .map(|key| ring.get(key).expect("ring is populated").to_string())
            .collect();

        ring.add_node("node-c");
        let after: Vec<String> = keys
            .iter()
            .map(|key| ring.get(key).expect("ring is populated").to_string())
            .collect();

        for (old, new) in before.iter().zip(after.iter()) {
            assert!(
                old == new || new == "node-c",
                "adding a node moved a key from {old} to {new}"
            );
        }
    }

    #[test]
    fn removing_a_node_drops_it_from_the_ring() {
        let mut ring = ConsistentHash::new(32);
        ring.add_node("node-a");
        ring.add_node("node-b");
        assert_eq!(ring.node_count(), 2);
        assert_eq!(ring.ring_len(), 64);

        ring.remove_node("node-a");
        assert_eq!(ring.node_count(), 1);
        for _ in 0..500 {
            assert!(matches!(ring.get("any-key"), Some("node-b")));
        }
    }
}
