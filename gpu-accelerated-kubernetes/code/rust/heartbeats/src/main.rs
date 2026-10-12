//! Models how a control plane tracks which machines in a fleet are alive.
//! Every host sends a heartbeat once a second. The registry keeps each host's
//! last heartbeat in memory, runs a sweep once a second, and records a durable
//! write only when a host changes state: Up, Suspect, or Dead.
//!
//! The program simulates 10,000 hosts for 60 seconds without real time
//! passing. Host 42 crashes at second 20, and host 7 misses four heartbeats
//! from second 30 to second 33. It prints how many heartbeats the registry
//! handled, how many durable writes it made, and each write.
//!
//! Run it from `code/rust` with `cargo run -p heartbeats`.

// ANCHOR: types
/// Seconds without a heartbeat before a host is Suspect.
const SUSPECT_AFTER: u32 = 3;
/// Seconds without a heartbeat before a host is Dead.
const DEAD_AFTER: u32 = 10;
/// Hosts in the fleet.
const HOST_COUNT: usize = 10_000;
/// Seconds simulated.
const DURATION: u32 = 60;

/// What the registry believes about a host.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
enum State {
    /// Heartbeats are arriving.
    #[default]
    Up,
    /// Heartbeats stopped recently; the host may be slow.
    Suspect,
    /// Heartbeats stopped long enough to give up on the host.
    Dead,
}

/// The registry's in-memory record of one host.
#[derive(Clone, Copy, Default)]
struct Entry {
    /// The second of the host's most recent heartbeat.
    last_seen: u32,
    /// The host's current state.
    state: State,
}

/// One durable write: a host entering a new state.
struct Transition {
    /// The second at which the sweep or heartbeat noticed the change.
    at: u32,
    /// The host's number.
    host: usize,
    /// The state the host entered.
    state: State,
}

/// Holds the liveness of every host.
struct Registry {
    /// Indexed by host number.
    hosts: Vec<Entry>,
    /// Counts the heartbeats handled in memory.
    heartbeats: usize,
    /// The durable writes, in order.
    writes: Vec<Transition>,
}
// ANCHOR_END: types

// ANCHOR: registry
impl Registry {
    /// Returns a registry in which every host is Up, as it would be after the
    /// hosts registered.
    fn new(n: usize) -> Self {
        Self {
            hosts: vec![Entry::default(); n],
            heartbeats: 0,
            writes: Vec::new(),
        }
    }

    /// Records a heartbeat from `host` at second `now`. Only a host that was
    /// not Up costs a durable write.
    fn heartbeat(&mut self, now: u32, host: usize) {
        self.heartbeats += 1;
        let entry = &mut self.hosts[host];
        entry.last_seen = now;
        if entry.state != State::Up {
            entry.state = State::Up;
            self.writes.push(Transition {
                at: now,
                host,
                state: State::Up,
            });
        }
    }

    /// Re-evaluates every host at second `now` and records each change of state.
    fn sweep(&mut self, now: u32) {
        for (host, entry) in self.hosts.iter_mut().enumerate() {
            let next = state_after(now - entry.last_seen);
            if next != entry.state {
                entry.state = next;
                self.writes.push(Transition {
                    at: now,
                    host,
                    state: next,
                });
            }
        }
    }
}

/// Returns the state of a host that has been silent for `silent` seconds.
fn state_after(silent: u32) -> State {
    match silent {
        s if s >= DEAD_AFTER => State::Dead,
        s if s >= SUSPECT_AFTER => State::Suspect,
        _ => State::Up,
    }
}
// ANCHOR_END: registry

// ANCHOR: main
/// Reports whether `host` sends a heartbeat at second `now` in the simulation.
fn sends_heartbeat(host: usize, now: u32) -> bool {
    match host {
        42 => now < 20,                // crashes at second 20
        7 => !(30..34).contains(&now), // silent from second 30 to 33
        _ => true,
    }
}

/// Runs the simulation and prints the registry's work.
fn main() {
    let mut registry = Registry::new(HOST_COUNT);
    for now in 0..DURATION {
        for host in 0..HOST_COUNT {
            if sends_heartbeat(host, now) {
                registry.heartbeat(now, host);
            }
        }
        registry.sweep(now);
    }
    println!("heartbeats handled in memory: {}", registry.heartbeats);
    println!("durable writes:               {}", registry.writes.len());
    for w in &registry.writes {
        println!("  second {:2}  host {:2} -> {:?}", w.at, w.host, w.state);
    }
}
// ANCHOR_END: main
