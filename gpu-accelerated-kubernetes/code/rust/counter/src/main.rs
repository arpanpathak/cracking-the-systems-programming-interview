//! Shows how replicas of a service that cannot always reach each other can
//! keep one count.
//!
//! Three replicas of a usage service run beside the three groups of machines
//! in our fleet: the shelf, the desk, and the bench. Each records the GPU time
//! that jobs near it report. The program counts in four ways: with one number
//! per replica, with a grow-only counter, with a counter that also goes down,
//! and with a quota divided into allowances.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p counter
//! ```

/// The number of replicas.
const REPLICAS: usize = 3;
/// The replicas, by index.
const SHELF: usize = 0;
const DESK: usize = 1;
const BENCH: usize = 2;
/// The replicas' names, in index order.
const NAMES: [&str; REPLICAS] = ["shelf", "desk", "bench"];

/// Formats a row of numbers as Go prints an array: `[1 2 3]`.
fn row(values: [i64; REPLICAS]) -> String {
    format!("[{}]", values.map(|v| v.to_string()).join(" "))
}

// ANCHOR: gcounter
/// A count that only grows. It keeps one entry per replica, and each replica
/// adds only to its own entry.
#[derive(Clone, Copy, Default)]
struct GCounter([i64; REPLICAS]);

impl GCounter {
    /// Records n more at the given replica.
    fn add(&mut self, replica: usize, n: i64) {
        self.0[replica] += n;
    }

    /// Takes, entry by entry, the larger of this counter's value and the
    /// other's. Merging is safe to repeat and to do in any order.
    fn merge(&mut self, other: GCounter) {
        for (mine, theirs) in self.0.iter_mut().zip(other.0) {
            *mine = (*mine).max(theirs);
        }
    }

    /// The count: the sum of every replica's entry.
    fn value(self) -> i64 {
        self.0.iter().sum()
    }
}
// ANCHOR_END: gcounter

// ANCHOR: pncounter
/// A count that goes up and down, built from two counters that only grow: one
/// for the increments and one for the decrements.
#[derive(Clone, Copy, Default)]
struct PnCounter {
    up: GCounter,
    down: GCounter,
}

impl PnCounter {
    /// Records a change of n, which may be negative, at the given replica.
    fn add(&mut self, replica: usize, n: i64) {
        if n >= 0 {
            self.up.add(replica, n);
        } else {
            self.down.add(replica, -n);
        }
    }

    /// Merges both halves.
    fn merge(&mut self, other: PnCounter) {
        self.up.merge(other.up);
        self.down.merge(other.down);
    }

    /// The increments minus the decrements.
    fn value(self) -> i64 {
        self.up.value() - self.down.value()
    }
}
// ANCHOR_END: pncounter

// ANCHOR: naive
/// Counts with a single number per replica and synchronises by keeping the
/// larger of two numbers.
fn one_number() {
    let adds = [300, 120, 40];
    for (name, n) in NAMES.iter().zip(adds) {
        println!("  {name:<5} records {n} GPU-seconds");
    }
    let largest = adds.iter().max().expect("three replicas");
    let sum: i64 = adds.iter().sum();
    println!("  after synchronising, every replica says {largest}; the jobs used {sum}");
}
// ANCHOR_END: naive

/// Prints one replica's counter and its value.
fn show(replica: usize, c: GCounter) {
    println!("  {:<5} holds {} = {}", NAMES[replica], row(c.0), c.value());
}

// ANCHOR: grow
/// Counts the same usage with a `GCounter` at each replica, through a
/// partition that cuts the bench off from the other two.
fn grow_only() {
    let mut at = [GCounter::default(); REPLICAS];
    for (r, n) in [300, 120, 40].into_iter().enumerate() {
        at[r].add(r, n);
    }
    println!("  the bench is cut off; shelf and desk exchange counters");
    at[SHELF].merge(at[DESK]);
    at[DESK].merge(at[SHELF]);
    at[SHELF].add(SHELF, 60);
    at[BENCH].add(BENCH, 25);
    for (r, c) in at.into_iter().enumerate() {
        show(r, c);
    }
    println!("  the network heals; counters are exchanged in no particular order, some twice");
    at[DESK].merge(at[BENCH]);
    at[SHELF].merge(at[DESK]);
    at[BENCH].merge(at[SHELF]);
    at[DESK].merge(at[SHELF]);
    at[DESK].merge(at[SHELF]);
    for (r, c) in at.into_iter().enumerate() {
        show(r, c);
    }
}
// ANCHOR_END: grow

// ANCHOR: updown
/// Counts GPUs in use. A job's start and its end may be recorded at different
/// replicas.
fn up_and_down() {
    let mut at = [PnCounter::default(); REPLICAS];
    at[SHELF].add(SHELF, 3); // three jobs start on the Thors
    at[DESK].add(DESK, 2); // two start on the Sparks
    at[SHELF].add(SHELF, -1); // one Thor job ends
    at[BENCH].add(BENCH, -1); // the bench replica hears that a Spark job ended
    for r in 0..REPLICAS {
        for other in 0..REPLICAS {
            let theirs = at[other];
            at[r].merge(theirs);
        }
    }
    let c = at[BENCH];
    println!("  started {}, ended {}: {} GPUs in use", row(c.up.0), row(c.down.0), c.value());
}
// ANCHOR_END: updown

// ANCHOR: quota
/// The number of GPUs one team may use at once.
const QUOTA: i64 = 6;

/// Lets each replica admit a job whenever its own view of the count leaves
/// room under the quota.
fn shared_limit() {
    let mut at = [PnCounter::default(); REPLICAS];
    at[SHELF].add(SHELF, 3);
    at[DESK].add(DESK, 1);
    let (shelf, desk) = (at[SHELF], at[DESK]);
    at[SHELF].merge(desk);
    at[DESK].merge(shelf);
    println!("  both replicas see {} of {QUOTA} in use; then they lose contact", at[SHELF].value());
    for r in [SHELF, DESK] {
        if at[r].value() + 2 <= QUOTA {
            at[r].add(r, 2);
            println!("  {:<5} admits a 2-GPU job: by its count, {} of {QUOTA} are in use", NAMES[r], at[r].value());
        }
    }
    let desk = at[DESK];
    at[SHELF].merge(desk);
    println!("  after they merge: {} of {QUOTA} in use", at[SHELF].value());
}

/// Gives each replica a share of the quota. A replica admits a job only from
/// its own share, and shares move between replicas when they can reach each
/// other.
fn allowances() {
    let mut share = [4, 2, 0];
    let mut used = [3, 1, 0];
    println!("  shares {}, in use {}; then the replicas lose contact", row(share), row(used));
    let admit = |share: &[i64; REPLICAS], used: &mut [i64; REPLICAS], r: usize, gpus: i64| {
        let left = share[r] - used[r];
        if left < gpus {
            println!("  {:<5} refuses a {gpus}-GPU job: its share has {left} left", NAMES[r]);
            return;
        }
        used[r] += gpus;
        println!("  {:<5} admits a {gpus}-GPU job", NAMES[r]);
    };
    admit(&share, &mut used, SHELF, 2);
    admit(&share, &mut used, DESK, 2);
    println!("  contact returns; desk gives its unused GPU to shelf");
    share[DESK] -= 1;
    share[SHELF] += 1;
    admit(&share, &mut used, SHELF, 2);
    println!("  shares {}, in use {}: {} of {QUOTA}", row(share), row(used), used.iter().sum::<i64>());
}
// ANCHOR_END: quota

fn main() {
    println!("one number per replica:");
    one_number();
    println!("one entry per replica, merged by taking the larger:");
    grow_only();
    println!("a count that goes down as well:");
    up_and_down();
    println!("a quota checked against each replica's own count:");
    shared_limit();
    println!("a quota divided into shares:");
    allowances();
}
