//! The write-ahead log: a file that only grows, to which every change is
//! appended before it is applied.

// ANCHOR: imports
use std::fs::{self, File, OpenOptions};
use std::io::{self, Read, Write};
use std::path::Path;

use crate::record::{Change, Decoded, Record};
// ANCHOR_END: imports

// ANCHOR: types
/// The name of the log inside the data directory.
pub const FILE_NAME: &str = "kv.log";

/// An open log, positioned at its end.
pub struct Log {
    file: File,
    /// Whether `append` waits for the disk before it returns.
    sync: bool,
    /// The sequence number of the next record.
    next: u64,
    /// Set by a failed write. A failed log accepts no more records.
    failed: bool,
}

/// What `Log::open` found in the file.
pub struct Recovery {
    /// The complete records, in the order they were written.
    pub records: Vec<Record>,
    /// The bytes after the last complete record, which were removed.
    pub discarded: u64,
}
// ANCHOR_END: types

// ANCHOR: scan
/// Reads records from the front of `bytes` until one is incomplete or
/// corrupt. It returns the records and the number of bytes they occupy.
fn scan(bytes: &[u8]) -> (Vec<Record>, usize) {
    let mut records = Vec::new();
    let mut valid = 0;

    while let Decoded::Record { record, length } = Record::decode(&bytes[valid..]) {
        records.push(record);
        valid += length;
    }

    (records, valid)
}
// ANCHOR_END: scan

// ANCHOR: open
impl Log {
    /// Opens the log in `directory`, creating both if they do not exist.
    /// Anything after the last complete record is cut off.
    pub fn open(directory: &Path, sync: bool) -> io::Result<(Log, Recovery)> {
        fs::create_dir_all(directory)?;

        let mut file = OpenOptions::new()
            .read(true)
            .append(true)
            .create(true)
            .open(directory.join(FILE_NAME))?;
        let mut bytes = Vec::new();
        file.read_to_end(&mut bytes)?;

        let (records, valid) = scan(&bytes);
        let discarded = (bytes.len() - valid) as u64;

        if discarded > 0 {
            file.set_len(valid as u64)?;
        }

        if sync {
            // The file's length is part of the file. Its name is part of the directory.
            file.sync_all()?;
            File::open(directory)?.sync_all()?;
        }

        let next = records
            .last()
            .map_or(1, |record| record.sequence + 1);

        Ok((
            Log {
                file,
                sync,
                next,
                failed: false,
            },
            Recovery { records, discarded },
        ))
    }
}
// ANCHOR_END: open

// ANCHOR: append
impl Log {
    /// Appends a change and returns the record that holds it. When the log
    /// was opened with `sync`, the record is on the disk when this returns.
    pub fn append(&mut self, change: Change) -> io::Result<Record> {
        if self.failed {
            return Err(io::Error::other(
                "the log failed on an earlier write and is closed",
            ));
        }

        let record = Record {
            sequence: self.next,
            change,
        };

        if let Err(error) = self.write(&record.encode()) {
            self.failed = true;

            return Err(error);
        }

        self.next += 1;

        Ok(record)
    }

    fn write(&mut self, bytes: &[u8]) -> io::Result<()> {
        self.file.write_all(bytes)?;

        if self.sync {
            self.file.sync_data()?;
        }

        Ok(())
    }

    /// The sequence number of the last record, or 0 for an empty log.
    pub fn last_sequence(&self) -> u64 {
        self.next - 1
    }
}
// ANCHOR_END: append

// ANCHOR: replicate
impl Log {
    /// Appends records that another node numbered, in one write and with one
    /// wait for the disk. The first record must follow the last record of
    /// this log.
    pub fn append_records(&mut self, records: &[Record]) -> io::Result<()> {
        if self.failed {
            return Err(io::Error::other(
                "the log failed on an earlier write and is closed",
            ));
        }

        let misplaced = (self.next..)
            .zip(records)
            .find(|(expected, record)| record.sequence != *expected);

        if let Some((expected, record)) = misplaced {
            return Err(io::Error::other(format!(
                "record {} cannot follow record {}",
                record.sequence,
                expected - 1
            )));
        }

        let bytes: Vec<u8> = records
            .iter()
            .flat_map(Record::encode)
            .collect();

        if let Err(error) = self.write(&bytes) {
            self.failed = true;

            return Err(error);
        }

        self.next += records.len() as u64;

        Ok(())
    }
}
// ANCHOR_END: replicate

// ANCHOR: truncate
impl Log {
    /// Removes the records after record `keep`, which ends at byte `length`
    /// of the file. A follower uses this to discard records that were never
    /// committed and that differ from the leader's.
    pub fn truncate(&mut self, keep: u64, length: u64) -> io::Result<()> {
        self.file.set_len(length)?;

        if self.sync {
            self.file.sync_all()?;
        }

        self.next = keep + 1;

        Ok(())
    }
}
// ANCHOR_END: truncate
