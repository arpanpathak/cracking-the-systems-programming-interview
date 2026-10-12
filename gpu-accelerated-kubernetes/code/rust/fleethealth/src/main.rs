//! Models the part of a control plane that keeps a fleet of GPU machines
//! healthy. It reads failure signals, decides whether each one blames a job, a
//! machine, or the network between machines, and moves each machine through a
//! lifecycle: cordon, drain, repair, validate, and return.
//!
//! The fleet is eight machines: five Jetson AGX Thor developer kits on one
//! 25 GbE switch, two DGX Sparks joined by a 200 GbE cable, and one Jetson
//! Orin NX. The program replays a scripted list of signals without real time
//! passing and prints every decision it makes.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p fleethealth
//! ```

use std::collections::{BTreeMap, BTreeSet};
use std::fmt;

// ANCHOR: fleet
/// One machine in the fleet.
struct Node {
    /// The machine's host name.
    name: &'static str,
    /// The product the machine is.
    model: &'static str,
    /// The switch or cable that connects the machine to its peers.
    link: &'static str,
}

/// The machines, in the order the program reports them.
const FLEET: [Node; 8] = [
    Node {
        name: "thor-1",
        model: "Jetson AGX Thor",
        link: "switch-25g",
    },
    Node {
        name: "thor-2",
        model: "Jetson AGX Thor",
        link: "switch-25g",
    },
    Node {
        name: "thor-3",
        model: "Jetson AGX Thor",
        link: "switch-25g",
    },
    Node {
        name: "thor-4",
        model: "Jetson AGX Thor",
        link: "switch-25g",
    },
    Node {
        name: "thor-5",
        model: "Jetson AGX Thor",
        link: "switch-25g",
    },
    Node {
        name: "spark-1",
        model: "DGX Spark",
        link: "cable-200g",
    },
    Node {
        name: "spark-2",
        model: "DGX Spark",
        link: "cable-200g",
    },
    Node {
        name: "orin-nx-1",
        model: "Jetson Orin NX",
        link: "bench",
    },
];
// ANCHOR_END: fleet

// ANCHOR: signal
/// The class of a failure signal.
#[derive(Clone, Copy)]
enum Kind {
    /// The GPU rejected work from one program.
    AppFault,
    /// An uncorrectable memory error on the GPU.
    MemoryEcc,
    /// The GPU stopped answering the driver.
    OffBus,
    /// The machine's network link went down and up.
    LinkFlap,
}

impl fmt::Display for Kind {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(match self {
            Kind::AppFault => "application fault",
            Kind::MemoryEcc => "uncorrectable ECC",
            Kind::OffBus => "GPU off the bus",
            Kind::LinkFlap => "link flap",
        })
    }
}

/// One failure report from a machine.
struct Signal {
    /// The second at which the signal arrived.
    at: u32,
    /// The machine that reported it.
    node: &'static str,
    /// The job that was using the GPU, or "" for a signal with no job.
    job: &'static str,
    /// The signal's class.
    kind: Kind,
}
// ANCHOR_END: signal

// ANCHOR: state
/// A machine's place in the repair lifecycle, in the order a failing machine
/// passes through it.
#[derive(Clone, Copy, Debug, PartialEq, PartialOrd)]
enum State {
    /// Schedulable.
    Healthy,
    /// No new work; waiting for the disruption budget.
    Cordoned,
    /// Jobs are checkpointing and leaving.
    Draining,
    /// A repair action is running.
    Remediating,
    /// A burn-in test is running.
    Validating,
    /// Every repair failed; a person has to look.
    Quarantined,
}

impl fmt::Display for State {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        // `pad` honours the width given in a format string such as `{:<11}`.
        f.pad(&format!("{self:?}"))
    }
}

/// The repair actions, from the cheapest to the most thorough.
const LADDER: [&str; 3] = ["reset the GPU", "reboot", "reimage"];
// ANCHOR_END: state

/// Distinct jobs (or nodes) before an application fault blames a node (or a job).
const BLAME_AFTER: usize = 3;
/// Machines on one link that must flap together to blame the link.
const FABRIC_AFTER: usize = 3;
/// How close in time those flaps have to be, in seconds.
const FABRIC_WINDOW: u32 = 5;
/// Machines that may be out of service at once.
const BUDGET: usize = 2;
/// Seconds a job gets to write a checkpoint and leave.
const DRAIN_TIME: u32 = 4;
/// Seconds one repair action takes.
const REPAIR_TIME: u32 = 3;
/// Seconds the burn-in test takes.
const BURN_IN_TIME: u32 = 3;
/// Seconds simulated.
const DURATION: u32 = 110;

/// What the control plane remembers about one machine.
struct Record {
    node: &'static Node,
    state: State,
    /// The second at which the machine entered its state.
    since: u32,
    /// The index of the next action on the ladder.
    step: usize,
    /// The distinct jobs that have faulted on this machine.
    fault_jobs: BTreeSet<&'static str>,
    /// The second of the machine's latest link flap.
    last_flap: Option<u32>,
}

/// The control plane's state: one record per machine, the nodes each job has
/// faulted on, and a scripted answer for each burn-in test.
struct Plane {
    records: Vec<Record>,
    /// For each job, the distinct nodes it has faulted on.
    job_nodes: BTreeMap<&'static str, BTreeSet<&'static str>>,
    /// The jobs and links already reported, so each is reported once.
    blamed: BTreeSet<&'static str>,
    /// How many burn-in tests a machine fails before one passes.
    burn_in: BTreeMap<&'static str, usize>,
}

impl Plane {
    /// Returns a plane in which every machine is Healthy.
    fn new(burn_in: BTreeMap<&'static str, usize>) -> Self {
        let records = FLEET
            .iter()
            .map(|node| Record {
                node,
                state: State::Healthy,
                since: 0,
                step: 0,
                fault_jobs: BTreeSet::new(),
                last_flap: None,
            })
            .collect();
        Plane {
            records,
            job_nodes: BTreeMap::new(),
            blamed: BTreeSet::new(),
            burn_in,
        }
    }

    /// Returns the index of the named machine's record.
    fn find(&self, name: &str) -> usize {
        self.records
            .iter()
            .position(|r| r.node.name == name)
            .expect("unknown node")
    }

    /// Puts a machine in a new state and logs the transition with its reason.
    fn transition(&mut self, now: u32, index: usize, to: State, why: &str) {
        let r = &mut self.records[index];
        println!(
            "{now:4}s  {:<10} {:<11} -> {:<11} {why}",
            r.node.name, r.state, to
        );
        r.state = to;
        r.since = now;
    }
}

// ANCHOR: triage
impl Plane {
    /// Takes one signal and decides what it blames. A hardware signal blames
    /// the machine. An application fault blames the job once the job has
    /// faulted on three machines, and blames the machine once three jobs have
    /// faulted on it. Link flaps blame the link when three machines on it flap
    /// within five seconds of each other.
    fn observe(&mut self, s: &Signal) {
        let index = self.find(s.node);
        match s.kind {
            Kind::MemoryEcc | Kind::OffBus => self.condemn(s.at, index, &s.kind.to_string()),
            Kind::AppFault => {
                self.records[index].fault_jobs.insert(s.job);
                let nodes = self.job_nodes.entry(s.job).or_default();
                nodes.insert(s.node);
                let (machines, jobs) = (nodes.len(), self.records[index].fault_jobs.len());
                if machines >= BLAME_AFTER && self.blamed.insert(s.job) {
                    println!(
                        "{:4}s  job {} faulted on {machines} machines: the job is at fault, no machine is drained",
                        s.at, s.job
                    );
                } else if machines < BLAME_AFTER && jobs >= BLAME_AFTER {
                    self.condemn(s.at, index, &format!("{jobs} different jobs faulted here"));
                }
            }
            Kind::LinkFlap => {
                self.records[index].last_flap = Some(s.at);
                let link = self.records[index].node.link;
                let together = self
                    .records
                    .iter()
                    .filter(|r| r.node.link == link)
                    .filter(|r| r.last_flap.is_some_and(|at| s.at - at <= FABRIC_WINDOW))
                    .count();
                if together >= FABRIC_AFTER && self.blamed.insert(link) {
                    println!(
                        "{:4}s  {together} machines on {link} flapped together: the link is at fault, no machine is drained",
                        s.at
                    );
                }
            }
        }
    }
}
// ANCHOR_END: triage

impl Plane {
    /// Cordons a Healthy machine. A machine already under repair stays where
    /// it is.
    fn condemn(&mut self, now: u32, index: usize, why: &str) {
        if self.records[index].state == State::Healthy {
            self.records[index].step = 0;
            self.transition(now, index, State::Cordoned, why);
        }
    }
}

// ANCHOR: budget
impl Plane {
    /// Counts the machines that hold a slot of the disruption budget: every
    /// machine that is draining, under repair, in burn-in, or quarantined.
    fn out_of_service(&self) -> usize {
        self.records
            .iter()
            .filter(|r| r.state >= State::Draining)
            .count()
    }
}
// ANCHOR_END: budget

// ANCHOR: step
impl Plane {
    /// Advances every machine by one second. A Cordoned machine starts to
    /// drain when the budget has a free slot. The other states each last a
    /// fixed time and then move on.
    fn step(&mut self, now: u32) {
        for index in 0..self.records.len() {
            let (state, step, name) = {
                let r = &self.records[index];
                (r.state, r.step, r.node.name)
            };
            let waited = now - self.records[index].since;
            match state {
                State::Cordoned if self.out_of_service() < BUDGET => {
                    self.transition(now, index, State::Draining, "jobs told to checkpoint");
                }
                State::Cordoned if waited == 1 => {
                    println!(
                        "{now:4}s  {name:<10} blocked: {BUDGET} machines are already out of service"
                    );
                }
                State::Draining if waited >= DRAIN_TIME => {
                    self.transition(now, index, State::Remediating, LADDER[step]);
                }
                State::Remediating if waited >= REPAIR_TIME => {
                    let why = format!("burn-in after {}", LADDER[step]);
                    self.transition(now, index, State::Validating, &why);
                }
                State::Validating if waited >= BURN_IN_TIME => self.finish_burn_in(now, index),
                _ => {}
            }
        }
    }

    /// Acts on the result of a burn-in test. A pass returns the machine to
    /// service. A failure sends it back for the next action on the ladder, and
    /// a machine with no actions left is quarantined.
    fn finish_burn_in(&mut self, now: u32, index: usize) {
        let name = self.records[index].node.name;
        let failures = self.burn_in.entry(name).or_default();
        if *failures == 0 {
            self.records[index].fault_jobs.clear();
            self.transition(now, index, State::Healthy, "burn-in passed");
            return;
        }
        *failures -= 1;
        if self.records[index].step + 1 == LADDER.len() {
            let why = "burn-in failed after every action; ticket opened";
            self.transition(now, index, State::Quarantined, why);
            return;
        }
        self.records[index].step += 1;
        let why = format!("burn-in failed; {}", LADDER[self.records[index].step]);
        self.transition(now, index, State::Remediating, &why);
    }
}
// ANCHOR_END: step

// ANCHOR: main
/// The run: the signals in the order they arrive.
const SCRIPT: [Signal; 11] = [
    // One job faults on three different Thors.
    Signal {
        at: 5,
        node: "thor-1",
        job: "finetune-7b",
        kind: Kind::AppFault,
    },
    Signal {
        at: 9,
        node: "thor-2",
        job: "finetune-7b",
        kind: Kind::AppFault,
    },
    Signal {
        at: 14,
        node: "thor-3",
        job: "finetune-7b",
        kind: Kind::AppFault,
    },
    // A memory error on a Spark, which one GPU reset repairs.
    Signal {
        at: 20,
        node: "spark-1",
        job: "",
        kind: Kind::MemoryEcc,
    },
    // A Thor whose GPU stops answering, and which no action repairs.
    Signal {
        at: 40,
        node: "thor-4",
        job: "",
        kind: Kind::OffBus,
    },
    // The 25 GbE switch restarts: four Thors lose their link together.
    Signal {
        at: 60,
        node: "thor-1",
        job: "",
        kind: Kind::LinkFlap,
    },
    Signal {
        at: 61,
        node: "thor-2",
        job: "",
        kind: Kind::LinkFlap,
    },
    Signal {
        at: 61,
        node: "thor-3",
        job: "",
        kind: Kind::LinkFlap,
    },
    Signal {
        at: 62,
        node: "thor-5",
        job: "",
        kind: Kind::LinkFlap,
    },
    // Two machines fail in the same second while thor-4 is quarantined.
    Signal {
        at: 80,
        node: "spark-2",
        job: "",
        kind: Kind::OffBus,
    },
    Signal {
        at: 80,
        node: "orin-nx-1",
        job: "",
        kind: Kind::MemoryEcc,
    },
];

fn main() {
    // thor-4 fails every burn-in; every other machine passes its first.
    let mut plane = Plane::new(BTreeMap::from([("thor-4", LADDER.len())]));
    let mut signals = SCRIPT.iter().peekable();
    for now in 0..=DURATION {
        while let Some(signal) = signals.next_if(|s| s.at == now) {
            plane.observe(signal);
        }
        plane.step(now);
    }
    println!("final states:");
    for r in &plane.records {
        println!("  {:<10} {:<16} {}", r.node.name, r.node.model, r.state);
    }
}
// ANCHOR_END: main
