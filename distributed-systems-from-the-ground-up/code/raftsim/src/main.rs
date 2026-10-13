//! Command raftsim runs 3 members in one process and decides itself when
//! each clock ticks, which message arrives, which is lost, and which member
//! crashes. It first walks through an election and the repair of a log,
//! and then makes 200 runs of 600 random steps, checking after every step
//! that no 2 members lead the same term and that no acknowledged write is
//! missing.
//!
//! Run it from code/ with:
//!
//!     cargo run --release -p raftsim

// ANCHOR: imports
use std::collections::BTreeMap;
use std::env;
use std::error::Error;
use std::fs;
use std::path::{Path, PathBuf};
use std::process;

use kv::{Change, Condition};
use raft::{Member, NodeId, Outgoing, Role};
// ANCHOR_END: imports

// ANCHOR: random
/// A generator of pseudo-random numbers. The same seed gives the same
/// numbers, so a run that fails can be repeated exactly.
struct Random(u64);

impl Random {
    fn next(&mut self) -> u64 {
        self.0 ^= self.0 << 13;
        self.0 ^= self.0 >> 7;
        self.0 ^= self.0 << 17;

        self.0
    }

    /// A number below `bound`.
    fn below(&mut self, bound: usize) -> usize {
        (self.next() % bound as u64) as usize
    }
}
// ANCHOR_END: random

// ANCHOR: cluster
const MEMBERS: [NodeId; 3] = [1, 2, 3];

/// A write that a leader has accepted and not yet committed.
struct Pending {
    leader: NodeId,
    term: u64,
    sequence: u64,
    key: String,
}

struct Cluster {
    root: PathBuf,
    /// The members that are running. A crashed member is absent.
    up: BTreeMap<NodeId, Member>,
    /// The messages that are on their way.
    network: Vec<Outgoing>,
    pending: Vec<Pending>,
    /// The sequence and the key of every acknowledged write.
    acknowledged: Vec<(u64, String)>,
    /// The leader that was seen in each term.
    leaders: BTreeMap<u64, NodeId>,
    discarded: u64,
    writes: u64,
}

impl Cluster {
    fn open(root: &Path) -> Result<Cluster, Box<dyn Error>> {
        let mut cluster = Cluster {
            root: root.to_owned(),
            up: BTreeMap::new(),
            network: Vec::new(),
            pending: Vec::new(),
            acknowledged: Vec::new(),
            leaders: BTreeMap::new(),
            discarded: 0,
            writes: 0,
        };

        for id in MEMBERS {
            cluster.start(id)?;
        }

        Ok(cluster)
    }

    fn start(&mut self, id: NodeId) -> Result<(), Box<dyn Error>> {
        let peers = MEMBERS
            .iter()
            .copied()
            .filter(|&peer| peer != id)
            .collect();
        let member = Member::open(
            &self
                .root
                .join(format!("member-{id}")),
            id,
            peers,
            false,
        )?;
        self.up.insert(id, member);

        Ok(())
    }

    /// Stops a member. Its files remain, and its memory is lost.
    fn crash(&mut self, id: NodeId) {
        if let Some(member) = self.up.remove(&id) {
            self.discarded += member.discarded();
        }
    }

    fn tick(&mut self, id: NodeId) -> Result<(), Box<dyn Error>> {
        if let Some(member) = self.up.get_mut(&id) {
            self.network.extend(member.tick()?);
        }

        self.check()
    }

    /// Delivers the message at `index`. A message for a member that is
    /// down is lost.
    fn deliver(&mut self, index: usize) -> Result<(), Box<dyn Error>> {
        let Outgoing { to, message } = self.network.remove(index);

        if let Some(member) = self.up.get_mut(&to) {
            self.network
                .extend(member.handle(message)?);
        }

        self.check()
    }

    /// Delivers one of the messages that are on their way, chosen at random.
    fn deliver_any(&mut self, random: &mut Random) -> Result<(), Box<dyn Error>> {
        if self.network.is_empty() {
            return Ok(());
        }

        self.deliver(random.below(self.network.len()))
    }

    /// Loses one of the messages that are on their way.
    fn lose_any(&mut self, random: &mut Random) {
        if !self.network.is_empty() {
            self.network
                .remove(random.below(self.network.len()));
        }
    }

    /// Starts a member that is down.
    fn restart(&mut self, id: NodeId) -> Result<(), Box<dyn Error>> {
        if self.up.contains_key(&id) {
            return Ok(());
        }

        self.start(id)
    }

    /// Delivers messages until none is on its way.
    fn deliver_all(&mut self) -> Result<(), Box<dyn Error>> {
        while !self.network.is_empty() {
            self.deliver(0)?;
        }

        Ok(())
    }

    /// Sends a write to a leader that can accept one, if there is one.
    fn write(&mut self) -> Result<bool, Box<dyn Error>> {
        let Some(leader) = self
            .up
            .values_mut()
            .find(|member| member.is_settled())
        else {
            return Ok(false);
        };

        self.writes += 1;
        let key = format!("key-{}", self.writes);
        let change = Change::Put {
            key: key.clone(),
            value: b"1".to_vec(),
        };
        let sequence = leader.propose(change, Condition::Always)?;

        self.pending.push(Pending {
            leader: leader.id(),
            term: leader.term(),
            sequence,
            key,
        });
        self.network
            .extend(leader.replicate());

        Ok(true)
    }

    fn leader(&self) -> Option<&Member> {
        self.up
            .values()
            .filter(|member| member.role() == Role::Leader)
            .max_by_key(|member| member.term())
    }
}
// ANCHOR_END: cluster

// ANCHOR: check
impl Cluster {
    /// The properties that must hold after every step.
    fn check(&mut self) -> Result<(), Box<dyn Error>> {
        // No 2 members lead the same term.
        for member in self
            .up
            .values()
            .filter(|member| member.role() == Role::Leader)
        {
            let first = *self
                .leaders
                .entry(member.term())
                .or_insert(member.id());

            if first != member.id() {
                return Err(format!(
                    "members {first} and {} both lead term {}",
                    member.id(),
                    member.term()
                )
                .into());
            }
        }

        // A write is acknowledged when the leader that accepted it, still
        // leading the same term, has committed its record.
        let up = &self.up;
        let committed = |write: &Pending| {
            up.get(&write.leader)
                .is_some_and(|leader| {
                    leader.role() == Role::Leader
                        && leader.term() == write.term
                        && leader.committed() >= write.sequence
                })
        };
        let (done, waiting): (Vec<Pending>, Vec<Pending>) = self
            .pending
            .drain(..)
            .partition(committed);

        self.acknowledged.extend(
            done.into_iter()
                .map(|write| (write.sequence, write.key)),
        );
        self.pending = waiting;

        // Every member that has committed the sequence of an acknowledged
        // write holds that write at that sequence.
        for (sequence, key) in &self.acknowledged {
            for member in self
                .up
                .values()
                .filter(|member| member.committed() >= *sequence)
            {
                let holds = matches!(&member.records()[*sequence as usize - 1].change, Change::Put { key: held, .. } if held == key);

                if !holds {
                    return Err(format!(
                        "member {} lost the acknowledged write of {key}",
                        member.id()
                    )
                    .into());
                }
            }
        }

        Ok(())
    }
}
// ANCHOR_END: check

// ANCHOR: cases
fn show(cluster: &Cluster) -> String {
    let describe = |id: &NodeId| match cluster.up.get(id) {
        Some(member) => format!(
            "{id}: {:?} term {} log {}",
            member.role(),
            member.term(),
            member.last_sequence()
        ),
        None => format!("{id}: down"),
    };

    MEMBERS
        .iter()
        .map(describe)
        .collect::<Vec<_>>()
        .join(" | ")
}

/// Ticks every running member, delivering all messages after each tick,
/// until a member leads. It returns the number of ticks.
fn elect(cluster: &mut Cluster) -> Result<u64, Box<dyn Error>> {
    let mut ticks = 0;

    while cluster
        .up
        .values()
        .all(|member| !member.is_settled())
    {
        ticks += 1;

        for id in MEMBERS {
            cluster.tick(id)?;
        }

        cluster.deliver_all()?;
    }

    Ok(ticks)
}

fn cases(root: &Path) -> Result<(), Box<dyn Error>> {
    let mut cluster = Cluster::open(root)?;

    println!("start:            {}", show(&cluster));

    let ticks = elect(&mut cluster)?;
    println!("after {ticks:2} ticks:   {}", show(&cluster));

    for _ in 0..3 {
        cluster.write()?;
        cluster.deliver_all()?;
    }

    println!(
        "after 3 writes:   {}, {} acknowledged",
        show(&cluster),
        cluster.acknowledged.len()
    );

    // The leader accepts a write and crashes before it sends the record.
    let old = cluster
        .leader()
        .map(Member::id)
        .ok_or("no leader")?;
    cluster.write()?;
    cluster.network.clear();
    cluster.crash(old);
    println!(
        "leader {old} appends record 5 and crashes: {}",
        show(&cluster)
    );

    let ticks = elect(&mut cluster)?;
    println!("after {ticks:2} ticks:   {}", show(&cluster));

    cluster.write()?;
    cluster.deliver_all()?;
    println!(
        "after 1 write:    {}, {} acknowledged",
        show(&cluster),
        cluster.acknowledged.len()
    );

    cluster.start(old)?;
    println!("member {old} returns: {}", show(&cluster));

    for _ in 0..2 {
        for id in MEMBERS {
            cluster.tick(id)?;
        }

        cluster.deliver_all()?;
    }

    let discarded = cluster
        .up
        .get(&old)
        .map_or(0, Member::discarded);
    println!("after 2 ticks:    {}", show(&cluster));
    println!(
        "member {old} discarded {discarded} record that was never committed, and holds the leader's records in its place"
    );

    Ok(())
}
// ANCHOR_END: cases

// ANCHOR: runs
const RUNS: u64 = 200;
const STEPS: usize = 600;

/// One run: random ticks, deliveries, losses, crashes, restarts and writes.
fn run(root: &Path, seed: u64) -> Result<Cluster, Box<dyn Error>> {
    let mut cluster = Cluster::open(root)?;
    let mut random = Random(seed);

    for _ in 0..STEPS {
        let id = MEMBERS[random.below(MEMBERS.len())];

        match random.below(100) {
            0..40 => cluster.tick(id)?,
            40..82 => cluster.deliver_any(&mut random)?,
            82..87 => cluster.lose_any(&mut random),
            87..90 => cluster.crash(id),
            90..94 => cluster.restart(id)?,
            94.. => cluster.write().map(drop)?,
        }
    }

    recover(&mut cluster)?;

    Ok(cluster)
}

/// Ends the faults: every member runs and every message arrives. The
/// members must then agree on a leader and on a log that holds every
/// acknowledged write.
fn recover(cluster: &mut Cluster) -> Result<(), Box<dyn Error>> {
    for id in MEMBERS {
        if !cluster.up.contains_key(&id) {
            cluster.start(id)?;
        }
    }

    let agreed = |cluster: &Cluster| {
        cluster
            .leader()
            .is_some_and(|leader| {
                leader.is_settled()
                    && cluster
                        .up
                        .values()
                        .all(|member| member.records() == leader.records())
            })
    };

    for _ in 0..200 {
        if agreed(cluster) {
            break;
        }

        for id in MEMBERS {
            cluster.tick(id)?;
        }

        cluster.deliver_all()?;
    }

    if !agreed(cluster) {
        return Err("the members did not agree after the faults ended".into());
    }

    let leader = cluster
        .leader()
        .ok_or("the members have no leader after the faults ended")?;

    for (sequence, key) in &cluster.acknowledged {
        if leader
            .get(key)
            .is_none_or(|entry| entry.version != *sequence)
        {
            return Err(
                format!("the acknowledged write of {key} is missing after recovery").into(),
            );
        }
    }

    Ok(())
}

fn runs(root: &Path) -> Result<(), Box<dyn Error>> {
    let (mut leaders, mut acknowledged, mut discarded, mut most_terms) = (0, 0, 0, 0);

    for seed in 1..=RUNS {
        let directory = root.join(format!("run-{seed}"));
        let mut cluster = run(&directory, seed)?;

        for id in MEMBERS {
            cluster.crash(id);
        }

        leaders += cluster.leaders.len();
        acknowledged += cluster.acknowledged.len();
        discarded += cluster.discarded;
        most_terms = most_terms.max(
            cluster
                .leaders
                .keys()
                .next_back()
                .copied()
                .unwrap_or(0),
        );

        fs::remove_dir_all(&directory)?;
    }

    println!("{RUNS} runs of {STEPS} random steps:");
    println!("  {leaders} leaders were elected, and no term had 2 leaders");
    println!("  {acknowledged} writes were acknowledged, and every one was present after recovery");
    println!(
        "  {discarded} uncommitted records were discarded by members whose log differed from a leader's"
    );
    println!("  the highest term reached in a run was {most_terms}");

    Ok(())
}
// ANCHOR_END: runs

// ANCHOR: main
fn main() -> Result<(), Box<dyn Error>> {
    let root = env::temp_dir().join(format!("raftsim-{}", process::id()));
    let result = cases(&root.join("cases")).and_then(|()| runs(&root));

    fs::remove_dir_all(&root)?;

    result
}
// ANCHOR_END: main
