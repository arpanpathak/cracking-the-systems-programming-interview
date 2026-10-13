//! Command cachesim measures how often a cache that keeps the most recently
//! used keys can answer, for several cache sizes, when a few keys are asked
//! for far more often than the rest.
//!
//! Run it from code/ with:
//!
//!     cargo run --release -p cachesim

// ANCHOR: imports
use std::collections::{BTreeMap, HashMap};
use std::iter;
// ANCHOR_END: imports

// ANCHOR: lru
/// A cache that holds at most `capacity` keys. When it is full, it removes
/// the key that was used longest ago.
struct Cache {
    capacity: usize,
    /// The time each key was last used.
    used: HashMap<u64, u64>,
    /// The same keys, ordered by the time they were last used.
    order: BTreeMap<u64, u64>,
    clock: u64,
}

impl Cache {
    fn new(capacity: usize) -> Cache {
        Cache {
            capacity,
            used: HashMap::new(),
            order: BTreeMap::new(),
            clock: 0,
        }
    }

    /// Looks up a key and returns whether the cache held it. Either way the
    /// key is the most recently used one afterwards.
    fn get(&mut self, key: u64) -> bool {
        self.clock += 1;

        let hit = match self.used.insert(key, self.clock) {
            Some(before) => self.order.remove(&before).is_some(),
            None => false,
        };

        self.order.insert(self.clock, key);

        if self.used.len() > self.capacity
            && let Some(oldest) = self.order.pop_first()
        {
            self.used.remove(&oldest.1);
        }

        hit
    }
}
// ANCHOR_END: lru

// ANCHOR: workload
/// A repeatable source of pseudo-random numbers.
struct Random(u64);

impl Random {
    fn next(&mut self) -> u64 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;

        self.0
    }

    /// A key from 0 to `keys`, where small numbers are far more likely:
    /// the product of 2 random fractions falls near 0 most of the time.
    fn popular_key(&mut self, keys: u64) -> u64 {
        let fraction = |random: &mut Random| (random.next() % 10_000) as f64 / 10_000.0;
        let skewed = fraction(self) * fraction(self) * fraction(self);

        (skewed * keys as f64) as u64
    }
}

fn main() {
    let (keys, requests) = (100_000u64, 1_000_000u64);

    println!("{requests} requests for {keys} keys, a few of them popular");

    for percent in [1, 5, 10, 25] {
        let mut cache = Cache::new((keys * percent / 100) as usize);
        let mut random = Random(42);

        let hits = iter::repeat_with(|| cache.get(random.popular_key(keys)))
            .take(requests as usize)
            .filter(|&hit| hit)
            .count();

        println!(
            "  cache holds {percent:2}% of the keys: {:4.1}% of requests answered from the cache",
            100.0 * hits as f64 / requests as f64
        );
    }
}
// ANCHOR_END: workload
