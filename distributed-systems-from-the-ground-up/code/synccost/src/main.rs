//! Command synccost measures what it costs to wait for the disk. It appends
//! the same records to 2 logs, one that calls fsync after each record and
//! one that does not, and prints the time per record.
//!
//! Run it from code/ with:
//!
//!     cargo run --release -p synccost -- /var/tmp/synccost

// ANCHOR: imports
use std::env;
use std::error::Error;
use std::fs;
use std::path::Path;
use std::time::{Duration, Instant};

use kv::{Change, Log};
// ANCHOR_END: imports

// ANCHOR: measure
const RECORDS: u32 = 500;

/// Appends `RECORDS` records of 100 bytes and returns the time it took.
fn measure(directory: &Path, sync: bool) -> Result<Duration, Box<dyn Error>> {
    let mut log = Log::open(directory, sync)?.0;
    let started = Instant::now();

    for number in 0..RECORDS {
        log.append(Change::Put {
            key: format!("key-{number:06}"),
            value: vec![b'v'; 100],
        })?;
    }

    Ok(started.elapsed())
}

fn main() -> Result<(), Box<dyn Error>> {
    let root = env::args()
        .nth(1)
        .ok_or("usage: synccost <directory>")?;

    for (name, sync) in [("without fsync", false), ("with fsync", true)] {
        let directory = Path::new(&root).join(name.replace(' ', "-"));
        let elapsed = measure(&directory, sync)?;
        let each = elapsed.as_secs_f64() * 1000.0 / f64::from(RECORDS);

        println!(
            "{name:13}: {RECORDS} records in {:8.1} ms, {each:.3} ms per record, {:6.0} records per second",
            elapsed.as_secs_f64() * 1000.0,
            1000.0 / each
        );

        fs::remove_dir_all(&directory)?;
    }

    Ok(())
}
// ANCHOR_END: measure
