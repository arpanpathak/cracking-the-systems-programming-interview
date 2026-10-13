//! Command crashsim checks what the log recovers after a crash in the middle
//! of a write. It writes a log of 5 records, then damages a copy of it in
//! every way a crash or a bad disk can: it cuts the copy at every length,
//! and it flips 1 bit in every byte. After each, it opens the copy and
//! compares the records that come back with the records that were complete.
//!
//! Run it from code/ with:
//!
//!     cargo run -p crashsim

// ANCHOR: imports
use std::env;
use std::error::Error;
use std::fs;
use std::path::Path;
use std::process;

use kv::log::FILE_NAME;
use kv::{Change, Log, Record};
// ANCHOR_END: imports

// ANCHOR: build
/// The changes of the test log.
fn changes() -> Vec<Change> {
    let put = |key: &str, value: &str| Change::Put {
        key: key.into(),
        value: value.into(),
    };

    vec![
        put("user-1", "ada"),
        put("user-2", "grace"),
        put("user-1", "ada lovelace"),
        Change::Delete {
            key: "user-2".into(),
        },
        put("user-3", "barbara"),
    ]
}

/// Writes the changes to a log in `directory`. It returns the bytes of the
/// log and the offset at which each record ends.
fn build(directory: &Path) -> Result<(Vec<u8>, Vec<usize>), Box<dyn Error>> {
    let mut log = Log::open(directory, false)?.0;
    let mut ends = Vec::new();

    for change in changes() {
        let record = log.append(change)?;
        ends.push(ends.last().copied().unwrap_or(0) + record.encode().len());
    }

    Ok((fs::read(directory.join(FILE_NAME))?, ends))
}
// ANCHOR_END: build

// ANCHOR: recover
/// Replaces the log in `directory` with `bytes` and opens it.
fn recover(directory: &Path, bytes: &[u8]) -> Result<Vec<Record>, Box<dyn Error>> {
    fs::write(directory.join(FILE_NAME), bytes)?;
    let recovery = Log::open(directory, false)?.1;

    Ok(recovery.records)
}

/// Whether `records` are exactly the first `count` changes, in order.
fn is_prefix(records: &[Record], count: usize) -> bool {
    let expected = changes();

    records.len() == count
        && records
            .iter()
            .zip(&expected)
            .enumerate()
            .all(|(index, (record, change))| {
                record.sequence == index as u64 + 1 && &record.change == change
            })
}
// ANCHOR_END: recover

// ANCHOR: cuts
/// Cuts the log at every length and checks that recovery returns the records
/// that end at or before the cut.
fn cuts(directory: &Path, log: &[u8], ends: &[usize]) -> Result<(), Box<dyn Error>> {
    for length in 0..=log.len() {
        let complete = ends
            .iter()
            .filter(|&&end| end <= length)
            .count();
        let records = recover(directory, &log[..length])?;

        if !is_prefix(&records, complete) {
            return Err(format!(
                "cut at {length}: expected {complete} records, recovered {}",
                records.len()
            )
            .into());
        }
    }

    println!(
        "cut at every length from 0 to {}: each recovery returned the complete records",
        log.len()
    );

    let mut first = 0;

    for (count, &end) in ends.iter().enumerate() {
        println!("  lengths {first:3} to {:3}: {count} records", end - 1);
        first = end;
    }

    println!("  length  {first:3}       : {} records", ends.len());

    Ok(())
}
// ANCHOR_END: cuts

// ANCHOR: flips
/// Flips 1 bit in each byte in turn and checks that recovery returns the
/// records before the damaged one.
fn flips(directory: &Path, log: &[u8], ends: &[usize]) -> Result<(), Box<dyn Error>> {
    for position in 0..log.len() {
        let mut damaged = log.to_vec();
        damaged[position] ^= 0x10;

        let before = ends
            .iter()
            .filter(|&&end| end <= position)
            .count();
        let records = recover(directory, &damaged)?;

        if !is_prefix(&records, before) {
            return Err(format!(
                "flip at {position}: expected {before} records, recovered {}",
                records.len()
            )
            .into());
        }
    }

    println!(
        "1 bit flipped in each of {} bytes: each recovery returned the records before the damage",
        log.len()
    );

    Ok(())
}
// ANCHOR_END: flips

// ANCHOR: main
fn run(directory: &Path) -> Result<(), Box<dyn Error>> {
    let (log, ends) = build(directory)?;
    let boundaries: Vec<String> = ends
        .iter()
        .map(usize::to_string)
        .collect();

    println!(
        "a log of {} records and {} bytes, with records ending at {}",
        ends.len(),
        log.len(),
        boundaries.join(", ")
    );

    cuts(directory, &log, &ends)?;
    flips(directory, &log, &ends)?;

    let records = recover(directory, &log[..ends[1] + 5])?;
    let mut reopened = Log::open(directory, false)?.0;
    let next = reopened.append(Change::Delete {
        key: "user-1".into(),
    })?;

    println!(
        "after a cut at {}: {} records recovered, and the next record has sequence {}",
        ends[1] + 5,
        records.len(),
        next.sequence
    );

    Ok(())
}

fn main() -> Result<(), Box<dyn Error>> {
    let directory = env::temp_dir().join(format!("crashsim-{}", process::id()));
    let result = run(&directory);

    fs::remove_dir_all(&directory)?;

    result
}
// ANCHOR_END: main
