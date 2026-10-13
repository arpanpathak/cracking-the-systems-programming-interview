//! Command replsim runs a leader and 2 followers in one process and carries
//! the messages between them by hand, so that it can lose any message it
//! chooses. It first walks through the cases of the chapter, and then tries
//! every combination of lost requests and lost answers over 3 writes and
//! checks what the replicas hold after each.
//!
//! Run it from code/ with:
//!
//!     cargo run --release -p replsim

// ANCHOR: imports
use std::env;
use std::error::Error;
use std::fs;
use std::path::{Path, PathBuf};
use std::process;

use kv::{Change, Condition};
use repl::{Replica, majority_sequence};
// ANCHOR_END: imports

// ANCHOR: cluster
/// What happens to one exchange between the leader and a follower.
#[derive(Clone, Copy, PartialEq, Eq)]
enum Fate {
    Delivered,
    /// The follower does not receive the message.
    RequestLost,
    /// The follower processes the message, and its answer does not arrive.
    AnswerLost,
}

/// A leader, 2 followers, and what the leader knows about each follower.
struct Cluster {
    leader: Replica,
    followers: Vec<Replica>,
    /// The last sequence each follower has reported.
    reported: Vec<u64>,
}

impl Cluster {
    fn open(root: &Path) -> Result<Cluster, Box<dyn Error>> {
        let open = |name: &str| Replica::open(&root.join(name), false, 1);

        Ok(Cluster {
            leader: open("leader")?,
            followers: vec![open("follower-1")?, open("follower-2")?],
            reported: vec![0, 0],
        })
    }

    /// One exchange with a follower: the leader sends what the follower
    /// lacks, as far as it knows, and commits what a majority now holds.
    fn exchange(&mut self, follower: usize, fate: Fate) -> Result<(), Box<dyn Error>> {
        let message = self
            .leader
            .append_for(self.reported[follower]);

        if fate == Fate::RequestLost {
            return Ok(());
        }

        let answer = self.followers[follower].handle_append(message)?;

        if fate == Fate::AnswerLost {
            return Ok(());
        }

        self.reported[follower] = answer.last_sequence;

        let stored = vec![
            self.leader.last_sequence(),
            self.reported[0],
            self.reported[1],
        ];
        self.leader
            .commit(majority_sequence(stored));

        Ok(())
    }

    /// A write: the leader appends the record and makes one exchange with
    /// each follower. It returns whether the write was acknowledged, or
    /// `None` when the leader could not accept it.
    fn write(
        &mut self,
        key: &str,
        value: &str,
        fates: [Fate; 2],
    ) -> Result<Option<bool>, Box<dyn Error>> {
        if !self.leader.is_settled() {
            return Ok(None);
        }

        let change = Change::Put {
            key: key.into(),
            value: value.into(),
        };
        let sequence = self
            .leader
            .propose(change, Condition::Always)?;

        self.exchange(0, fates[0])?;
        self.exchange(1, fates[1])?;

        Ok(Some(self.leader.committed() >= sequence))
    }

    /// The last sequence of the leader and of each follower.
    fn lasts(&self) -> [u64; 3] {
        [
            self.leader.last_sequence(),
            self.followers[0].last_sequence(),
            self.followers[1].last_sequence(),
        ]
    }
}
// ANCHOR_END: cluster

// ANCHOR: cases
const BOTH: [Fate; 2] = [Fate::Delivered, Fate::Delivered];

fn cases(root: &Path) -> Result<(), Box<dyn Error>> {
    let mut cluster = Cluster::open(root)?;
    let show = |cluster: &Cluster| {
        format!(
            "logs end at {:?}, committed {}",
            cluster.lasts(),
            cluster.leader.committed()
        )
    };

    for key in ["a", "b", "c"] {
        cluster.write(key, "1", BOTH)?;
    }

    println!("3 writes, every message delivered: {}", show(&cluster));

    for key in ["d", "e", "f"] {
        cluster.write(key, "1", [Fate::RequestLost, Fate::Delivered])?;
    }

    println!(
        "3 writes while follower 1 is unreachable: {}",
        show(&cluster)
    );

    cluster.exchange(0, Fate::Delivered)?;
    println!("follower 1 returns, 1 exchange: {}", show(&cluster));

    for key in ["g", "h", "i"] {
        cluster.write(key, "1", [Fate::AnswerLost, Fate::Delivered])?;
    }

    println!(
        "3 writes while the answers of follower 1 are lost: {}",
        show(&cluster)
    );
    println!(
        "  the leader believes that the log of follower 1 ends at {}",
        cluster.reported[0]
    );

    cluster.exchange(0, Fate::Delivered)?;
    println!(
        "  next exchange: the leader sends records 7 to 9, follower 1 refuses and reports {}",
        cluster.reported[0]
    );

    cluster.exchange(0, Fate::Delivered)?;
    println!("  the exchange after it: {}", show(&cluster));

    let acknowledged =
        cluster.write("j", "1", [Fate::RequestLost, Fate::RequestLost])? == Some(true);
    println!(
        "1 write while both followers are unreachable: acknowledged {acknowledged}, {}",
        show(&cluster)
    );
    println!(
        "  the leader reads j as {:?}",
        cluster
            .leader
            .get("j")
            .map(|entry| entry.version)
    );

    let accepted = cluster
        .write("k", "1", [Fate::RequestLost, Fate::RequestLost])?
        .is_some();
    println!("  the leader accepts another write: {accepted}");

    cluster.exchange(1, Fate::Delivered)?;
    println!("follower 2 returns: {}", show(&cluster));
    println!(
        "  the leader reads j as {:?}",
        cluster
            .leader
            .get("j")
            .map(|entry| entry.version)
    );

    let mut newer = Replica::open(&root.join("newer"), false, 2)?;
    let answer = newer.handle_append(cluster.leader.append_for(0))?;
    println!(
        "a replica at term 2 receives a message of term 1: appended {}, its term {}",
        answer.appended, answer.term
    );

    Ok(())
}
// ANCHOR_END: cases

// ANCHOR: exhaustive
const WRITES: usize = 3;

/// The fate of exchange number `index` under a pattern: 2 bits for each.
fn fate(pattern: u32, index: usize) -> Fate {
    match (pattern >> (2 * index)) & 3 {
        0 | 1 => Fate::Delivered,
        2 => Fate::RequestLost,
        3.. => Fate::AnswerLost,
    }
}

/// Runs 3 writes under one pattern of losses and checks the replicas. It
/// returns the number of writes that were acknowledged.
fn run(root: &Path, pattern: u32) -> Result<usize, Box<dyn Error>> {
    let mut cluster = Cluster::open(root)?;
    let mut acknowledged = Vec::new();

    for number in 0..WRITES {
        let fates = [fate(pattern, 2 * number), fate(pattern, 2 * number + 1)];

        if cluster.write(&format!("key-{number}"), "1", fates)? == Some(true) {
            acknowledged.push(cluster.leader.last_sequence());
        }
    }

    for &sequence in &acknowledged {
        let holders = cluster
            .lasts()
            .iter()
            .filter(|&&last| last >= sequence)
            .count();

        if holders < 2 {
            return Err(format!(
                "pattern {pattern}: record {sequence} was acknowledged and is in {holders} log"
            )
            .into());
        }
    }

    for follower in &cluster.followers {
        if !cluster
            .leader
            .records()
            .starts_with(follower.records())
        {
            return Err(format!(
                "pattern {pattern}: a follower's log is not the beginning of the leader's"
            )
            .into());
        }
    }

    for _ in 0..2 {
        cluster.exchange(0, Fate::Delivered)?;
        cluster.exchange(1, Fate::Delivered)?;
    }

    let [leader, first, second] = cluster.lasts();

    if first != leader || second != leader || !cluster.leader.is_settled() {
        return Err(format!(
            "pattern {pattern}: the logs differ after every message was delivered"
        )
        .into());
    }

    Ok(acknowledged.len())
}

fn exhaustive(root: &Path) -> Result<(), Box<dyn Error>> {
    let patterns = 1u32 << (4 * WRITES);
    let mut by_acknowledged = [0; WRITES + 1];

    for pattern in 0..patterns {
        let directory = root.join(format!("pattern-{pattern}"));
        by_acknowledged[run(&directory, pattern)?] += 1;
        fs::remove_dir_all(&directory)?;
    }

    println!("{patterns} patterns of lost messages over {WRITES} writes:");
    println!("  every acknowledged record was in at least 2 of the 3 logs");
    println!("  every follower's log was the beginning of the leader's log");
    println!("  after the losses stopped, the 3 logs were equal and every record was committed");

    for (count, patterns) in by_acknowledged.iter().enumerate() {
        println!("  {count} of {WRITES} writes acknowledged: {patterns} patterns");
    }

    Ok(())
}
// ANCHOR_END: exhaustive

// ANCHOR: main
fn directory() -> PathBuf {
    env::temp_dir().join(format!("replsim-{}", process::id()))
}

fn main() -> Result<(), Box<dyn Error>> {
    let root = directory();
    let result = cases(&root.join("cases")).and_then(|()| exhaustive(&root));

    fs::remove_dir_all(&root)?;

    result
}
// ANCHOR_END: main
