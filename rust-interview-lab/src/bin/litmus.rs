//! Memory-ordering litmus tests, run many times on real hardware.
//!
//! A litmus test is two short threads and a question: can this combination
//! of results happen? Each test runs a million rounds and counts the rounds
//! that ended with the result in question.
//!
//! Run with: cargo run --release --bin litmus

use std::{
    sync::atomic::{
        AtomicU32,
        AtomicUsize,
        Ordering::{self, Acquire, Relaxed, Release, SeqCst},
    },
    thread,
};

const ROUNDS: usize = 1_000_000;

/// A fresh, zeroed atomic for every round, so no round needs a reset.
fn zeroed(rounds: usize) -> Vec<AtomicU32> {
    (0..rounds).map(|_| AtomicU32::new(0)).collect()
}

/// Wait until both threads have reached `round`. Keeps the two threads on the
/// same round, so their operations overlap in time.
fn meet(arrived: &AtomicUsize, round: usize) {
    arrived.fetch_add(1, SeqCst);
    while arrived.load(SeqCst) < 2 * (round + 1) {
        std::hint::spin_loop();
    }
}

/// Store buffering. Thread 1 stores x and loads y; thread 2 stores y and loads
/// x. Returns the rounds in which both loads read 0.
fn store_buffering(store: Ordering, load: Ordering) -> usize {
    let (x, y) = (zeroed(ROUNDS), zeroed(ROUNDS));
    let (r1, r2) = (zeroed(ROUNDS), zeroed(ROUNDS));
    let arrived = AtomicUsize::new(0);

    thread::scope(|scope| {
        scope.spawn(|| {
            for i in 0..ROUNDS {
                meet(&arrived, i);
                x[i].store(1, store);
                r1[i].store(y[i].load(load), Relaxed);
            }
        });
        scope.spawn(|| {
            for i in 0..ROUNDS {
                meet(&arrived, i);
                y[i].store(1, store);
                r2[i].store(x[i].load(load), Relaxed);
            }
        });
    });

    (0..ROUNDS)
        .filter(|&i| r1[i].load(Relaxed) == 0 && r2[i].load(Relaxed) == 0)
        .count()
}

/// Message passing. Thread 1 writes data, then sets a flag; thread 2 reads the
/// flag, then the data. Returns the rounds in which thread 2 saw the flag set
/// but the data still 0.
fn message_passing(store: Ordering, load: Ordering) -> usize {
    let (data, flag) = (zeroed(ROUNDS), zeroed(ROUNDS));
    let (seen_flag, seen_data) = (zeroed(ROUNDS), zeroed(ROUNDS));
    let arrived = AtomicUsize::new(0);

    thread::scope(|scope| {
        scope.spawn(|| {
            for i in 0..ROUNDS {
                meet(&arrived, i);
                data[i].store(42, Relaxed);
                flag[i].store(1, store);
            }
        });
        scope.spawn(|| {
            for i in 0..ROUNDS {
                meet(&arrived, i);
                seen_flag[i].store(flag[i].load(load), Relaxed);
                seen_data[i].store(data[i].load(Relaxed), Relaxed);
            }
        });
    });

    (0..ROUNDS)
        .filter(|&i| seen_flag[i].load(Relaxed) == 1 && seen_data[i].load(Relaxed) == 0)
        .count()
}

fn main() {
    let orderings = [
        ("Relaxed", Relaxed, Relaxed),
        ("Release / Acquire", Release, Acquire),
        ("SeqCst", SeqCst, SeqCst),
    ];

    println!("store buffering, {ROUNDS} rounds: both loads read 0");
    for (name, store, load) in orderings {
        println!("  {name:<18} {:>8}", store_buffering(store, load));
    }

    println!("\nmessage passing, {ROUNDS} rounds: flag read as 1, data read as 0");
    for (name, store, load) in orderings {
        println!("  {name:<18} {:>8}", message_passing(store, load));
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn seq_cst_forbids_both_loads_reading_zero() {
        assert_eq!(store_buffering(SeqCst, SeqCst), 0);
    }

    #[test]
    fn release_acquire_forbids_a_flag_without_its_data() {
        assert_eq!(message_passing(Release, Acquire), 0);
    }
}
