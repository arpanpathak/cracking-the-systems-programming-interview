//! Command idgen makes unique 64-bit ids on several nodes without any
//! coordination between them, and checks that no id is made twice.
//!
//! Run it from code/ with:
//!
//!     cargo run --release -p idgen

// ANCHOR: imports
use std::collections::HashSet;
use std::iter;
// ANCHOR_END: imports

// ANCHOR: generator
/// The bits of an id, from the top: 41 of time in milliseconds, 10 for the
/// node, 12 for a counter within the millisecond.
const NODE_BITS: u64 = 10;
const COUNTER_BITS: u64 = 12;
const COUNTER_MAX: u64 = (1 << COUNTER_BITS) - 1;

struct Generator {
    node: u64,
    /// The millisecond of the last id, and the counter within it.
    last: u64,
    counter: u64,
}

impl Generator {
    fn new(node: u64) -> Generator {
        Generator {
            node,
            last: 0,
            counter: 0,
        }
    }

    /// Makes the next id at time `now`, or `None` when the node must wait:
    /// the counter of this millisecond is used up, or the clock went back.
    fn next(&mut self, now: u64) -> Option<u64> {
        if now < self.last {
            return None;
        }

        let counter = if now == self.last {
            self.counter + 1
        } else {
            0
        };

        if counter > COUNTER_MAX {
            return None;
        }

        self.last = now;
        self.counter = counter;

        Some(now << (NODE_BITS + COUNTER_BITS) | self.node << COUNTER_BITS | counter)
    }
}
// ANCHOR_END: generator

// ANCHOR: main
/// The number of ids that every node is asked for in every millisecond.
const ASKED: usize = 5000;

fn main() {
    let mut nodes: Vec<Generator> = (1..=3)
        .map(Generator::new)
        .collect();
    let mut seen = HashSet::new();
    let mut made = 0;

    // Every node is asked in every one of 100 milliseconds.
    let turns = (1000..1100).flat_map(|now| (0..3).map(move |node| (now, node)));

    for (now, node) in turns {
        let ids: Vec<u64> = iter::repeat_with(|| nodes[node].next(now))
            .take(ASKED)
            .flatten()
            .collect();

        made += ids.len();
        seen.extend(ids);
    }

    let refused = 3 * 100 * ASKED - made;

    println!("ids made: {made}, different ids: {}", seen.len());
    println!("requests refused because a millisecond was full: {refused}");

    let mut node = Generator::new(7);
    let first = node.next(2000);
    let second = node.next(2000);
    let later = node.next(2001);
    let back = node.next(1999);

    println!("node 7 at time 2000: {first:?}, then {second:?}");
    println!("node 7 at time 2001: {later:?}");
    println!("node 7 at time 1999, after its clock went back: {back:?}");
    println!("ids sort by time: {}", first < second && second < later);
}
// ANCHOR_END: main
