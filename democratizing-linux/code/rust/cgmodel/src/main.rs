//! Models the control group hierarchy: every group counts the processes and
//! the memory of its whole subtree, a fork is refused when any group above
//! it is at its limit, and a group that exceeds its memory limit loses the
//! largest process in its subtree.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p cgmodel
//! ```

// ANCHOR: imports
use std::fmt;
// ANCHOR_END: imports

// ANCHOR: types
/// The value of a limit that is written "max" in a control file.
const UNLIMITED: usize = usize::MAX;

#[derive(Debug)]
struct Again;

impl fmt::Display for Again {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("EAGAIN")
    }
}

/// One node of the hierarchy. `pids` and `memory` are the usage of the group
/// and of every group below it. `refused` and `oom_kills` are the counters
/// the kernel publishes in `pids.events` and `memory.events`.
struct Group {
    parent: Option<usize>,
    pids_max: usize,
    memory_max: usize,
    pids: usize,
    memory: usize,
    refused: usize,
    oom_kills: usize,
}

/// A process belongs to one group and holds an amount of memory.
struct Process {
    name: &'static str,
    home: usize,
    memory: usize,
    alive: bool,
}

/// The hierarchy: groups and processes, referred to by index.
#[derive(Default)]
struct Hierarchy {
    groups: Vec<Group>,
    processes: Vec<Process>,
}

impl Hierarchy {
    /// Adds a group below `parent` and returns its index.
    fn group(&mut self, parent: Option<usize>, pids_max: usize, memory_max: usize) -> usize {
        self.groups.push(Group {
            parent,
            pids_max,
            memory_max,
            pids: 0,
            memory: 0,
            refused: 0,
            oom_kills: 0,
        });

        self.groups.len() - 1
    }

    /// The group itself and every group above it, nearest first.
    fn upward(&self, group: usize) -> Vec<usize> {
        let mut path = vec![group];

        while let Some(parent) = self.groups[path[path.len() - 1]].parent {
            path.push(parent);
        }

        path
    }
}
// ANCHOR_END: types

// ANCHOR: pids
impl Hierarchy {
    /// Starts a process in a group and returns its index. The process is
    /// counted in the group and in every group above it, so it is refused
    /// when any of them is at its limit.
    fn spawn(&mut self, group: usize, name: &'static str) -> Result<usize, Again> {
        let path = self.upward(group);

        for &up in &path {
            if self.groups[up].pids == self.groups[up].pids_max {
                self.groups[up].refused += 1;

                return Err(Again);
            }
        }

        for &up in &path {
            self.groups[up].pids += 1;
        }

        self.processes.push(Process {
            name,
            home: group,
            memory: 0,
            alive: true,
        });

        Ok(self.processes.len() - 1)
    }
}
// ANCHOR_END: pids

// ANCHOR: memory
impl Hierarchy {
    /// Gives a process more memory. While a group above the process is over
    /// its limit, the largest process in that group's subtree is killed.
    /// Returns the names of the processes killed.
    fn allocate(&mut self, process: usize, amount: usize) -> Vec<&'static str> {
        let path = self.upward(self.processes[process].home);

        self.processes[process].memory += amount;

        for &up in &path {
            self.groups[up].memory += amount;
        }

        let mut killed = Vec::new();

        for &up in &path {
            while self.groups[up].memory > self.groups[up].memory_max {
                let Some(victim) = self.largest(up) else {
                    break;
                };

                self.groups[up].oom_kills += 1;
                killed.push(self.processes[victim].name);
                self.kill(victim);
            }
        }

        killed
    }

    /// Returns the living process with the most memory in the subtree of a
    /// group.
    fn largest(&self, group: usize) -> Option<usize> {
        (0..self.processes.len())
            .filter(|&p| self.processes[p].alive)
            .filter(|&p| self.upward(self.processes[p].home).contains(&group))
            .max_by_key(|&p| self.processes[p].memory)
    }

    /// Ends a process and returns its memory and its place in the process
    /// count.
    fn kill(&mut self, process: usize) {
        let memory = self.processes[process].memory;

        for up in self.upward(self.processes[process].home) {
            self.groups[up].memory -= memory;
            self.groups[up].pids -= 1;
        }

        self.processes[process].alive = false;
    }
}
// ANCHOR_END: memory

// ANCHOR: trace
fn main() -> Result<(), Again> {
    let mut tree = Hierarchy::default();

    let team = tree.group(None, 4, 100);
    let job_a = tree.group(Some(team), UNLIMITED, UNLIMITED);
    let job_b = tree.group(Some(team), UNLIMITED, UNLIMITED);

    let a1 = tree.spawn(job_a, "a1")?;
    tree.spawn(job_a, "a2")?;
    tree.spawn(job_a, "a3")?;
    let b1 = tree.spawn(job_b, "b1")?;

    println!(
        "3 processes in job-a and 1 in job-b: pids.current job-a {}, job-b {}, team {}",
        tree.groups[job_a].pids, tree.groups[job_b].pids, tree.groups[team].pids
    );

    if let Err(error) = tree.spawn(job_b, "b2") {
        println!(
            "another process in job-b, team at pids.max 4: {error}, pids.events max of team {}",
            tree.groups[team].refused
        );
    }

    tree.allocate(a1, 60);
    println!(
        "a1 allocates 60: memory.current job-a {}, job-b {}, team {}",
        tree.groups[job_a].memory, tree.groups[job_b].memory, tree.groups[team].memory
    );

    let killed = tree.allocate(b1, 50);
    println!(
        "b1 allocates 50, team at memory.max 100: killed [{}], oom_kill of team {}",
        killed.join(" "),
        tree.groups[team].oom_kills
    );
    println!(
        "afterwards: memory.current job-a {}, job-b {}, team {}, pids.current team {}",
        tree.groups[job_a].memory,
        tree.groups[job_b].memory,
        tree.groups[team].memory,
        tree.groups[team].pids
    );

    Ok(())
}
// ANCHOR_END: trace
