//! Models the kernel's process table: process numbers handed out in a cycle,
//! a parent for every process, a zombie state between exit and wait, and a
//! new parent for orphans. It applies a sequence of calls and prints the
//! table after each.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p proctable
//! ```

// ANCHOR: imports
use std::collections::BTreeMap;
use std::fmt;
// ANCHOR_END: imports

// ANCHOR: table
/// The errors carry the names of the kernel's error codes for the same cases.
#[derive(Debug)]
enum Error {
    Again,
    NoChild,
    Search,
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(match self {
            Error::Again => "EAGAIN: no process number is free",
            Error::NoChild => "ECHILD: the caller has no child to wait for",
            Error::Search => "ESRCH: no such process",
        })
    }
}

impl std::error::Error for Error {}

/// The process that adopts orphans.
const INIT_PID: u32 = 1;

#[derive(Clone, Copy, PartialEq)]
enum State {
    Running,
    Zombie,
}

/// One entry of the table.
struct Process {
    parent: u32,
    state: State,
    status: i32,
}

/// Maps process numbers to entries. `last` is the number given out most
/// recently, and `pid_max` is the largest number allowed.
struct Table {
    procs: BTreeMap<u32, Process>,
    last: u32,
    pid_max: u32,
}

impl Table {
    fn new(pid_max: u32) -> Table {
        let init = Process {
            parent: 0,
            state: State::Running,
            status: 0,
        };

        Table {
            procs: BTreeMap::from([(INIT_PID, init)]),
            last: INIT_PID,
            pid_max,
        }
    }
}
// ANCHOR_END: table

// ANCHOR: fork
impl Table {
    /// Returns the first free number after `last`, wrapping around from
    /// `pid_max` to the number after `INIT_PID`.
    fn allocate(&mut self) -> Result<u32, Error> {
        let mut pid = self.last;

        for _ in 0..self.pid_max {
            pid += 1;

            if pid > self.pid_max {
                pid = INIT_PID + 1;
            }

            if !self.procs.contains_key(&pid) {
                self.last = pid;

                return Ok(pid);
            }
        }

        Err(Error::Again)
    }

    /// Creates a child of `parent` and returns the child's number.
    fn fork(&mut self, parent: u32) -> Result<u32, Error> {
        if !self.procs.contains_key(&parent) {
            return Err(Error::Search);
        }

        let pid = self.allocate()?;

        let child = Process {
            parent,
            state: State::Running,
            status: 0,
        };

        self.procs.insert(pid, child);

        Ok(pid)
    }
}
// ANCHOR_END: fork

// ANCHOR: exit
impl Table {
    /// Ends a process. The entry stays in the table as a zombie that holds
    /// the exit status, and the children of the process become children of
    /// init.
    fn exit(&mut self, pid: u32, status: i32) -> Result<(), Error> {
        let process = self.procs.get_mut(&pid).ok_or(Error::Search)?;

        process.state = State::Zombie;
        process.status = status;

        for child in self.procs.values_mut() {
            if child.parent == pid {
                child.parent = INIT_PID;
            }
        }

        Ok(())
    }
}
// ANCHOR_END: exit

// ANCHOR: wait
impl Table {
    /// Removes a zombie child of `parent` from the table and returns its
    /// number and exit status. The result is `None` when `parent` has
    /// children and none of them has exited, the case in which the kernel
    /// suspends the caller.
    fn wait(&mut self, parent: u32) -> Result<Option<(u32, i32)>, Error> {
        let mut children = self
            .procs
            .iter()
            .filter(|(_, child)| child.parent == parent)
            .peekable();

        if children.peek().is_none() {
            return Err(Error::NoChild);
        }

        let Some((&pid, child)) = children.find(|(_, child)| child.state == State::Zombie) else {
            return Ok(None);
        };

        let status = child.status;
        self.procs.remove(&pid);

        Ok(Some((pid, status)))
    }
}
// ANCHOR_END: wait

// ANCHOR: trace
/// Renders the table as pid(parent)state for each entry.
impl fmt::Display for Table {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let cells: Vec<String> = self
            .procs
            .iter()
            .map(|(pid, process)| {
                let state = match process.state {
                    State::Running => 'R',
                    State::Zombie => 'Z',
                };

                format!("{pid}({}){state}", process.parent)
            })
            .collect();

        f.write_str(&cells.join(" "))
    }
}

/// One step of the trace.
enum Call {
    Fork(u32),
    Exit(u32, i32),
    Wait(u32),
}

impl Table {
    /// Performs a call and describes its result.
    fn apply(&mut self, call: &Call) -> Result<String, Error> {
        match *call {
            Call::Fork(parent) => {
                let child = self.fork(parent)?;

                Ok(format!("fork by {parent}: pid {child}"))
            }
            Call::Exit(pid, status) => {
                self.exit(pid, status)?;

                Ok(format!("exit of {pid}, status {status}"))
            }
            Call::Wait(parent) => match self.wait(parent)? {
                Some((child, status)) => {
                    Ok(format!("wait by {parent}: pid {child}, status {status}"))
                }
                None => Ok(format!("wait by {parent}: would block")),
            },
        }
    }
}

fn main() -> Result<(), Error> {
    let mut table = Table::new(6);

    let calls = [
        Call::Fork(1),
        Call::Fork(2),
        Call::Fork(3),
        Call::Wait(2),
        Call::Exit(3, 0),
        Call::Wait(2),
        Call::Fork(2),
        Call::Exit(4, 7),
        Call::Wait(1),
        Call::Fork(2),
        Call::Fork(2),
    ];

    println!("{:<30} {table}", "start");

    for call in &calls {
        let result = table.apply(call)?;
        println!("{result:<30} {table}");
    }

    Ok(())
}
// ANCHOR_END: trace
