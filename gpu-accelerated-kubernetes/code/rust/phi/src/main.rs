//! Compares two ways of deciding that a host has failed: a fixed timeout, and
//! the phi accrual failure detector, which learns how regular each host's
//! heartbeats are and reports how unlikely the current silence is.
//!
//! Two simulated hosts both send a heartbeat about once a second. One is
//! steady; the other sits on a congested network and its heartbeats arrive
//! between 0.4 and 2.4 seconds apart. For each host, the program prints the
//! detector's suspicion level, phi, after different lengths of silence, next
//! to the verdict of a 2-second timeout.
//!
//! Run it from `code/rust` with `cargo run -p phi`.

use std::collections::VecDeque;

// ANCHOR: detector
/// The fixed timeout that the program compares against, in seconds.
const TIMEOUT: f64 = 2.0;

/// The smallest standard deviation the detector assumes, in seconds. Without
/// it, a perfectly regular host would make any delay look infinitely
/// suspicious.
const MIN_STD_DEV: f64 = 0.2;

/// A phi accrual failure detector for one host.
struct Detector {
    /// The most recent gaps between heartbeats, in seconds.
    intervals: VecDeque<f64>,
    /// The number of gaps the detector remembers.
    window: usize,
    /// The time of the most recent heartbeat, in seconds.
    last: f64,
}

impl Detector {
    /// Returns a detector that remembers `window` gaps and has seen a first
    /// heartbeat at time `first`.
    fn new(window: usize, first: f64) -> Self {
        Self {
            intervals: VecDeque::new(),
            window,
            last: first,
        }
    }

    /// Records a heartbeat that arrived at time `now`.
    fn heartbeat(&mut self, now: f64) {
        self.intervals.push_back(now - self.last);
        if self.intervals.len() > self.window {
            self.intervals.pop_front();
        }
        self.last = now;
    }
}
// ANCHOR_END: detector

// ANCHOR: phi
impl Detector {
    /// Returns the suspicion level at time `now`: minus the base-10 logarithm
    /// of the probability that a heartbeat would still arrive after this much
    /// silence, given the gaps seen so far. Phi 1 means a 10% chance the host
    /// is fine, phi 2 means 1%, and phi 3 means 0.1%.
    #[allow(clippy::cast_precision_loss)] // the window holds at most 100 gaps
    fn phi(&self, now: f64) -> f64 {
        let n = self.intervals.len() as f64;
        let mean = self.intervals.iter().sum::<f64>() / n;
        let variance = self
            .intervals
            .iter()
            .map(|gap| (gap - mean).powi(2))
            .sum::<f64>()
            / n;
        let std_dev = variance.sqrt().max(MIN_STD_DEV);

        // The probability that a gap is longer than the current silence, from
        // a logistic approximation of the normal distribution.
        let silence = now - self.last;
        let y = (silence - mean) / std_dev;
        let e = (-y * (1.5976 + 0.070_566 * y * y)).exp();
        let p_later = if silence > mean {
            e / (1.0 + e)
        } else {
            1.0 - 1.0 / (1.0 + e)
        };
        -p_later.log10()
    }
}
// ANCHOR_END: phi

// ANCHOR: main
/// The simulated hosts and the gaps between their heartbeats.
const HOSTS: [(&str, [f64; 10]); 2] = [
    (
        "steady",
        [1.0, 1.02, 0.98, 1.01, 0.99, 1.0, 1.03, 0.97, 1.0, 1.0],
    ),
    (
        "jittery",
        [0.4, 1.9, 0.6, 1.7, 0.5, 1.8, 0.7, 1.6, 0.4, 2.4],
    ),
];

/// Feeds each host's heartbeats to a detector and prints phi after increasing
/// lengths of silence.
fn main() {
    for (name, gaps) in HOSTS {
        let mut detector = Detector::new(100, 0.0);
        let mut now = 0.0;
        for gap in gaps {
            now += gap;
            detector.heartbeat(now);
        }
        println!("{name} host, silent for:");
        for silence in [1.0, 1.5, 2.0, 2.5, 3.0, 4.0] {
            let verdict = if silence > TIMEOUT { "dead" } else { "alive" };
            println!(
                "  {silence:.1}s  phi = {:6.2}   {TIMEOUT:.0}s timeout says {verdict}",
                detector.phi(now + silence)
            );
        }
    }
}
// ANCHOR_END: main
