//! A consistent hash ring with virtual nodes.
//!
//! Positions on the ring are 64-bit hashes. Every node owns several
//! positions, called tokens, and a key belongs to the node that owns the
//! first token at or after the key's own position, going round to the
//! lowest token after the highest.

// ANCHOR: imports
use std::collections::{BTreeMap, BTreeSet};

use xxhash_rust::xxh3::xxh3_64;
// ANCHOR_END: imports

// ANCHOR: types
/// A position on the ring.
pub type Token = u64;

/// The ring: every token, in order, with the name of the node that owns it.
#[derive(Debug, Clone, Default)]
pub struct Ring {
    tokens: BTreeMap<Token, String>,
    /// The number of tokens each node receives.
    virtual_nodes: u32,
}

/// The position of a key on the ring.
pub fn position(key: &str) -> Token {
    xxh3_64(key.as_bytes())
}
// ANCHOR_END: types

// ANCHOR: membership
impl Ring {
    pub fn new(virtual_nodes: u32) -> Ring {
        Ring {
            tokens: BTreeMap::new(),
            virtual_nodes,
        }
    }

    /// Adds a node. Its tokens are the hashes of its name followed by a
    /// number, so every program that knows the name computes the same ring.
    pub fn add(&mut self, node: &str) {
        for number in 0..self.virtual_nodes {
            self.tokens
                .insert(position(&format!("{node}#{number}")), node.to_owned());
        }
    }

    /// Removes a node and all of its tokens.
    pub fn remove(&mut self, node: &str) {
        self.tokens
            .retain(|_, owner| owner != node);
    }
}
// ANCHOR_END: membership

// ANCHOR: lookup
impl Ring {
    /// The tokens from the key's position onward, continuing from the start
    /// of the ring after its end.
    fn clockwise(&self, key: &str) -> impl Iterator<Item = &String> {
        let from = position(key);

        self.tokens
            .range(from..)
            .chain(self.tokens.range(..from))
            .map(|token| token.1)
    }

    /// The node that owns a key.
    pub fn owner(&self, key: &str) -> Option<&str> {
        self.clockwise(key)
            .next()
            .map(String::as_str)
    }

    /// The first `count` different nodes clockwise from a key: the nodes
    /// that hold its replicas.
    pub fn replicas(&self, key: &str, count: usize) -> Vec<&str> {
        // Several tokens in a row can belong to 1 node, and a node is taken
        // only the first time it is met.
        let mut met = BTreeSet::new();

        self.clockwise(key)
            .map(String::as_str)
            .filter(|node| met.insert(*node))
            .take(count)
            .collect()
    }
}
// ANCHOR_END: lookup
