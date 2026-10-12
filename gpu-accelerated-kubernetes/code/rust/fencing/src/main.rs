//! Shows why a checkpoint store has to check who is writing.
//!
//! A training job runs on thor-1. The Thor loses its network link and keeps
//! training. The control plane sees silence, declares thor-1 dead, and starts
//! the job again on thor-2 from the last checkpoint. For a while two copies of
//! the job run, and both write checkpoints to the same store.
//!
//! The program plays that sequence twice: against a store that accepts every
//! write, and against a store that remembers the highest epoch it has seen
//! and refuses writes that carry an older one.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p fencing
//! ```

use std::fmt;

// ANCHOR: store
/// What a worker saves: the training step it reached and the epoch of the
/// assignment under which it was running.
#[derive(Clone, Copy, Default)]
struct Checkpoint {
    /// The training step the checkpoint holds.
    step: u32,
    /// The assignment number the writer was given.
    epoch: u32,
    /// The host that wrote the checkpoint.
    writer: &'static str,
}

/// Returned to a writer whose epoch is older than one the store has already
/// accepted.
struct Fenced;

impl fmt::Display for Fenced {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str("fenced: a newer assignment has written")
    }
}

/// Holds the latest checkpoint of one job.
#[derive(Default)]
struct Store {
    /// Turns the epoch check on.
    fencing: bool,
    /// The stored checkpoint.
    latest: Checkpoint,
}

impl Store {
    /// Stores a checkpoint. With fencing on, a checkpoint whose epoch is lower
    /// than the stored one is refused.
    fn write(&mut self, c: Checkpoint) -> Result<(), Fenced> {
        if self.fencing && c.epoch < self.latest.epoch {
            return Err(Fenced);
        }

        self.latest = c;

        Ok(())
    }
}
// ANCHOR_END: store

// ANCHOR: assign
/// Hands out assignments of one job. Each assignment gets the next epoch, so a
/// later assignment always carries a higher number.
#[derive(Default)]
struct ControlPlane {
    epoch: u32,
}

impl ControlPlane {
    /// Gives the job to a host and returns the epoch of the assignment.
    fn assign(&mut self, host: &str) -> u32 {
        self.epoch += 1;
        println!(
            "  control plane: job assigned to {host} with epoch {}",
            self.epoch
        );

        self.epoch
    }
}
// ANCHOR_END: assign

// ANCHOR: run
/// Writes one checkpoint and prints what the store answered.
fn save(store: &mut Store, writer: &'static str, epoch: u32, step: u32) {
    match store.write(Checkpoint {
        step,
        epoch,
        writer,
    }) {
        Ok(()) => println!("  {writer} writes step {step} with epoch {epoch}: stored"),
        Err(e) => println!("  {writer} writes step {step} with epoch {epoch}: refused, {e}"),
    }
}

/// Plays the sequence against one store.
fn run(mut store: Store) {
    let mut plane = ControlPlane::default();
    let first = plane.assign("thor-1");
    save(&mut store, "thor-1", first, 1000);
    println!("  thor-1 loses its link and keeps training; its Lease expires");
    let second = plane.assign("thor-2");
    println!("  thor-2 resumes from step {}", store.latest.step);
    save(&mut store, "thor-2", second, 2000);
    println!("  thor-1's link returns; it still holds epoch 1");
    save(&mut store, "thor-1", first, 1500);
    println!(
        "  a restart now resumes from step {}, written by {}",
        store.latest.step, store.latest.writer
    );
}

fn main() {
    println!("a store that accepts every write:");
    run(Store::default());
    println!("a store that checks the epoch:");
    run(Store {
        fencing: true,
        ..Store::default()
    });
}
// ANCHOR_END: run
