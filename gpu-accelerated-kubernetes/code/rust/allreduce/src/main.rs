//! Runs one step of distributed training's communication: five workers each
//! hold a gradient, and every worker has to end the step holding the sum of
//! all five.
//!
//! The workers are threads connected in a ring by channels, and they run the
//! ring all-reduce algorithm. The program runs the step three ways: with every
//! worker healthy, with one worker failing part of the way through, and then
//! as arithmetic, to find how often a job of a given size should save a
//! checkpoint.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p allreduce
//! ```

use std::sync::mpsc::{self, Receiver, Sender};
use std::thread;
use std::time::Duration;

// ANCHOR: worker
/// Carries one chunk of a gradient from a worker to its right-hand neighbour.
struct Message {
    /// The index of the chunk within the gradient.
    chunk: usize,
    /// The chunk's contents: one number stands for the whole chunk.
    value: i64,
}

/// One machine's part in the step.
struct Worker {
    /// The worker's position in the ring, from 0.
    id: usize,
    /// One value per chunk. It starts as this worker's own gradient and ends
    /// as the sum over all workers.
    gradient: Vec<i64>,
    /// Receives from the left-hand neighbour.
    inbox: Receiver<Message>,
    /// Sends to the right-hand neighbour.
    out: Sender<Message>,
    /// The number of messages the worker exchanges before it fails, if the
    /// run makes it fail.
    fail_after: Option<usize>,
}

/// How long a worker waits for its neighbour before giving up.
const PATIENCE: Duration = Duration::from_millis(100);
// ANCHOR_END: worker

/// Returns the host name of the worker at a ring position.
fn name(id: usize) -> String {
    format!("thor-{}", id + 1)
}

// ANCHOR: run
impl Worker {
    /// Performs the worker's 2(n-1) exchanges. In each one it sends a chunk to
    /// the right and receives a chunk from the left. During the first n-1
    /// exchanges it adds what it receives to its own chunk. During the last
    /// n-1 the chunks it receives are finished sums, and it stores them.
    /// Returns the worker with the number of exchanges completed and the
    /// reason it stopped early, if any.
    fn run(mut self, n: usize) -> (Self, usize, Option<String>) {
        for step in 0..2 * (n - 1) {
            if self.fail_after == Some(step) {
                return (self, step, Some("failed".to_owned()));
            }

            // The chunk to send moves one place back around the gradient each
            // step, so after the first step it is the chunk just received.
            // Adding 2n keeps the subtraction from going below zero.
            let chunk = (self.id + 2 * n - step) % n;
            // The right-hand neighbour may have stopped; its channel still accepts.
            let _ = self.out.send(Message {
                chunk,
                value: self.gradient[chunk],
            });
            let reducing = step < n - 1;

            match self.inbox.recv_timeout(PATIENCE) {
                Ok(m) if reducing => self.gradient[m.chunk] += m.value,
                Ok(m) => self.gradient[m.chunk] = m.value,
                Err(_) => {
                    let why = format!(
                        "no chunk from {} within {PATIENCE:?}",
                        name((self.id + n - 1) % n)
                    );

                    return (self, step, Some(why));
                }
            }
        }

        (self, 2 * (n - 1), None)
    }
}
// ANCHOR_END: run

// ANCHOR: ring
/// Connects n workers in a circle, runs them all at once, and returns each
/// worker with its result. The worker named in `failing` stops after that
/// many exchanges.
fn ring(n: usize, failing: Option<(usize, usize)>) -> Vec<(Worker, usize, Option<String>)> {
    // One channel per link. `senders[i]` leads to worker i.
    let (senders, receivers): (Vec<_>, Vec<_>) = (0..n).map(|_| mpsc::channel()).unzip();
    let workers: Vec<Worker> = receivers
        .into_iter()
        .enumerate()
        .map(|(id, inbox)| Worker {
            id,
            gradient: own_gradient(id, n),
            inbox,
            out: senders[(id + 1) % n].clone(),
            fail_after: failing
                .filter(|(who, _)| *who == id)
                .map(|(_, after)| after),
        })
        .collect();

    let handles: Vec<_> = workers
        .into_iter()
        .map(|w| thread::spawn(move || w.run(n)))
        .collect();

    handles
        .into_iter()
        .map(|h| h.join().expect("a worker panicked"))
        .collect()
}
// ANCHOR_END: ring

/// Returns the gradient a worker starts with: a different value in each chunk.
fn own_gradient(id: usize, n: usize) -> Vec<i64> {
    (0..n).map(|chunk| (id + 1 + 10 * chunk) as i64).collect()
}

/// Formats a gradient as its values separated by spaces.
fn show(gradient: &[i64]) -> String {
    gradient
        .iter()
        .map(i64::to_string)
        .collect::<Vec<_>>()
        .join(" ")
}

// ANCHOR: checkpoint
/// The time one checkpoint takes to write, in seconds.
const CHECKPOINT_COST: f64 = 50.0;
/// The mean time between failures of one machine, in seconds: 30 days.
const MACHINE_MTBF: f64 = 30.0 * 24.0 * 3600.0;

/// Returns the time between checkpoints that loses the least work, by Young's
/// formula: the square root of twice the checkpoint cost times the job's mean
/// time between failures.
fn interval(job_mtbf: f64) -> f64 {
    (2.0 * CHECKPOINT_COST * job_mtbf).sqrt()
}
// ANCHOR_END: checkpoint

// ANCHOR: main
fn main() {
    const N: usize = 5;

    println!("ring all-reduce over {N} workers, {N} chunks each:");

    for (worker, _, _) in ring(N, None) {
        println!(
            "  {} starts with {:<17} and ends with {}",
            name(worker.id),
            show(&own_gradient(worker.id, N)),
            show(&worker.gradient)
        );
    }

    let sent = 2 * (N - 1);
    println!(
        "  each worker sent {sent} chunks, {:.1} times its gradient; {} messages in all",
        sent as f64 / N as f64,
        sent * N
    );

    println!(
        "the same step, with {} failing after 2 of its {sent} exchanges:",
        name(2)
    );

    for (worker, steps, why) in ring(N, Some((2, 2))) {
        let why = why.unwrap_or_else(|| "finished".to_owned());
        println!(
            "  {} stopped after {steps} of {sent}: {why}",
            name(worker.id)
        );
    }

    println!(
        "checkpoint interval, for a 50 s checkpoint and one failure per machine every 30 days:"
    );
    println!("  machines  job fails every  checkpoint every  time lost");

    for machines in [1, 5, 64, 512] {
        let job_mtbf = MACHINE_MTBF / f64::from(machines);
        let every = interval(job_mtbf);
        let lost = CHECKPOINT_COST / every + every / (2.0 * job_mtbf);
        println!(
            "  {machines:8}  {:10.1} hours  {:9.0} minutes  {:8.1}%",
            job_mtbf / 3600.0,
            every / 60.0,
            lost * 100.0
        );
    }
}
// ANCHOR_END: main
