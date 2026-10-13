//! Command clicksim counts clicks on an advertisement in windows of 10
//! seconds. Clicks arrive late, out of order and sometimes twice. It counts
//! them once by the time they arrived and once by the time they happened,
//! with a watermark that decides when a window is finished.
//!
//! Run it from code/ with:
//!
//!     cargo run -p clicksim

// ANCHOR: imports
use std::collections::{BTreeMap, BTreeSet};
// ANCHOR_END: imports

// ANCHOR: counting
/// The length of a window, and how long after the newest click the counter
/// still waits for older ones, in seconds.
const WINDOW: u64 = 10;
const LATENESS: u64 = 5;

/// A click: its id, the second in which it happened, and the second in
/// which it reached the counter.
#[derive(Clone, Copy)]
struct Click {
    id: u32,
    happened: u64,
    arrived: u64,
}

/// Counts by the time of the event. A window is finished once the
/// watermark, the newest event time minus `LATENESS`, has passed its end.
#[derive(Default)]
struct Counter {
    seen: BTreeSet<u32>,
    open: BTreeMap<u64, u32>,
    finished: BTreeMap<u64, u32>,
    watermark: u64,
    repeats: u32,
    too_late: u32,
}

impl Counter {
    fn add(&mut self, click: Click) {
        if !self.seen.insert(click.id) {
            self.repeats += 1;

            return;
        }

        let window = click.happened / WINDOW;

        if (window + 1) * WINDOW <= self.watermark {
            self.too_late += 1;

            return;
        }

        *self.open.entry(window).or_default() += 1;
        self.watermark = self.watermark.max(
            click
                .happened
                .saturating_sub(LATENESS),
        );

        // Every open window that the watermark has passed is finished.
        let still_open = self
            .open
            .split_off(&(self.watermark / WINDOW));

        self.finished.append(&mut self.open);
        self.open = still_open;
    }
}
// ANCHOR_END: counting

// ANCHOR: main
fn show(counts: &BTreeMap<u64, u32>) -> String {
    counts
        .iter()
        .map(|(window, count)| format!("{}-{} s: {count}", window * WINDOW, (window + 1) * WINDOW))
        .collect::<Vec<String>>()
        .join(", ")
}

fn main() {
    // 8 clicks happen in the first 10 seconds and 4 in the next 10. Click 7
    // is held up on a phone for 6 seconds, click 3 is sent twice, and click
    // 2 arrives a minute late.
    let clicks = [
        (1, 1, 1),
        (3, 3, 3),
        (4, 4, 4),
        (3, 3, 5),
        (5, 6, 6),
        (6, 8, 8),
        (8, 9, 9),
        (9, 11, 11),
        (7, 7, 13),
        (10, 14, 14),
        (11, 16, 16),
        (12, 19, 19),
        (13, 26, 26),
        (2, 2, 62),
    ]
    .map(|(id, happened, arrived)| Click {
        id,
        happened,
        arrived,
    });

    let mut by_arrival: BTreeMap<u64, u32> = BTreeMap::new();
    let mut counter = Counter::default();

    for click in clicks {
        *by_arrival
            .entry(click.arrived / WINDOW)
            .or_default() += 1;
        counter.add(click);
    }

    println!("what happened:              0-10 s: 8, 10-20 s: 4, 20-30 s: 1");
    println!("counted by arrival time:    {}", show(&by_arrival));
    println!("counted by event time:      {}", show(&counter.finished));
    println!("still open:                 {}", show(&counter.open));
    println!(
        "clicks received twice: {}, clicks too late for their window: {}",
        counter.repeats, counter.too_late
    );
}
// ANCHOR_END: main
