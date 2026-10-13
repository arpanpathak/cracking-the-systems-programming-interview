//! The store: the current value of every key in memory, and the log that
//! rebuilds it.

// ANCHOR: imports
use std::collections::BTreeMap;
use std::io;
use std::ops::Bound;
use std::path::Path;

use thiserror::Error;

use crate::log::Log;
use crate::record::{Change, Record};
// ANCHOR_END: imports

// ANCHOR: types
/// The value of a key and the sequence number of the record that wrote it.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Entry {
    pub value: Vec<u8>,
    pub version: u64,
}

/// What a write requires of the key's current state.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Condition {
    /// The write is unconditional.
    Always,
    /// The key must not exist.
    Absent,
    /// The key must exist at this version.
    Version(u64),
}

/// The result of a `put`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Written {
    pub version: u64,
    /// Whether the key did not exist before.
    pub created: bool,
}

/// One line of a listing.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Summary {
    pub key: String,
    pub version: u64,
    pub size: usize,
}

#[derive(Debug, Error)]
pub enum StoreError {
    #[error("the key does not exist")]
    NotFound,
    #[error("the condition on the key's version does not hold")]
    ConditionFailed { current: Option<u64> },
    #[error("the log could not be written: {0}")]
    Log(#[from] io::Error),
}

pub struct Store {
    entries: BTreeMap<String, Entry>,
    log: Log,
}
// ANCHOR_END: types

// ANCHOR: open
impl Store {
    /// Opens the store in `directory` and applies every record of its log.
    /// It returns the store, the number of records applied, and the number
    /// of bytes that were cut from the end of the log.
    pub fn open(directory: &Path, sync: bool) -> io::Result<(Store, usize, u64)> {
        let (log, recovery) = Log::open(directory, sync)?;
        let applied = recovery.records.len();
        let mut entries = BTreeMap::new();

        for record in recovery.records {
            apply(&mut entries, record);
        }

        Ok((Store { entries, log }, applied, recovery.discarded))
    }
}

/// Makes the change of one record in the map. Recovery and the write path
/// both go through this function, so they cannot disagree.
pub fn apply(entries: &mut BTreeMap<String, Entry>, record: Record) {
    match record.change {
        Change::Put { key, value } => {
            entries.insert(
                key,
                Entry {
                    value,
                    version: record.sequence,
                },
            );
        }
        Change::Delete { key } => {
            entries.remove(&key);
        }
    }
}
// ANCHOR_END: open

// ANCHOR: write
impl Store {
    /// Sets the value of a key. The change is in the log before it is in
    /// the map.
    pub fn put(
        &mut self,
        key: String,
        value: Vec<u8>,
        condition: Condition,
    ) -> Result<Written, StoreError> {
        let current = self.version(&key);
        check(condition, current)?;

        let record = self
            .log
            .append(Change::Put { key, value })?;
        let version = record.sequence;
        apply(&mut self.entries, record);

        Ok(Written {
            version,
            created: current.is_none(),
        })
    }

    /// Removes a key.
    pub fn delete(&mut self, key: &str, condition: Condition) -> Result<(), StoreError> {
        let current = self.version(key);

        if current.is_none() {
            return Err(StoreError::NotFound);
        }

        check(condition, current)?;

        let record = self.log.append(Change::Delete {
            key: key.to_owned(),
        })?;
        apply(&mut self.entries, record);

        Ok(())
    }

    fn version(&self, key: &str) -> Option<u64> {
        self.entries
            .get(key)
            .map(|entry| entry.version)
    }
}

pub fn check(condition: Condition, current: Option<u64>) -> Result<(), StoreError> {
    let holds = match condition {
        Condition::Always => true,
        Condition::Absent => current.is_none(),
        Condition::Version(version) => current == Some(version),
    };

    holds
        .then_some(())
        .ok_or(StoreError::ConditionFailed { current })
}
// ANCHOR_END: write

// ANCHOR: batch
/// One write of a batch: the change, and the condition it carries.
pub struct Write {
    pub change: Change,
    pub condition: Condition,
}

impl Store {
    /// Performs several writes with a single wait for the disk. Each write
    /// is checked as if the writes before it in the batch had already
    /// happened. The result of each is returned in the same order.
    pub fn commit(&mut self, writes: Vec<Write>) -> Vec<Result<Written, StoreError>> {
        // The versions that keys will have once the accepted writes of this
        // batch are applied. `None` is a key that a write of the batch deletes.
        let mut pending: BTreeMap<String, Option<u64>> = BTreeMap::new();
        let mut records = Vec::new();
        let mut results = Vec::new();
        let first = self.log.last_sequence() + 1;

        for write in writes {
            let key = match &write.change {
                Change::Put { key, .. } | Change::Delete { key } => key.clone(),
            };
            let current = match pending.get(&key) {
                Some(version) => *version,
                None => self.version(&key),
            };
            let deletes = matches!(write.change, Change::Delete { .. });

            let checked = if deletes && current.is_none() {
                Err(StoreError::NotFound)
            } else {
                check(write.condition, current)
            };

            if let Err(error) = checked {
                results.push(Err(error));

                continue;
            }

            let sequence = first + records.len() as u64;
            let version = if deletes { None } else { Some(sequence) };

            pending.insert(key, version);
            results.push(Ok(Written {
                version: sequence,
                created: current.is_none(),
            }));
            records.push(Record {
                sequence,
                change: write.change,
            });
        }

        // One write and one wait for the disk, for the whole batch.
        if let Err(error) = self.log.append_records(&records) {
            let failure = error.to_string();

            return results
                .into_iter()
                .map(|result| result.and(Err(StoreError::Log(io::Error::other(failure.clone())))))
                .collect();
        }

        for record in records {
            apply(&mut self.entries, record);
        }

        results
    }
}
// ANCHOR_END: batch

// ANCHOR: read
impl Store {
    pub fn get(&self, key: &str) -> Option<&Entry> {
        self.entries.get(key)
    }

    /// Returns up to `limit` keys that start with `prefix` and sort after
    /// `after`, in order, and whether more keys follow them.
    pub fn list(&self, prefix: &str, after: Option<&str>, limit: usize) -> (Vec<Summary>, bool) {
        page(&self.entries, prefix, after, limit)
    }

    pub fn len(&self) -> usize {
        self.entries.len()
    }

    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    /// The sequence number of the last record in the log.
    pub fn last_sequence(&self) -> u64 {
        self.log.last_sequence()
    }
}

/// One page of a listing over a map of entries.
pub fn page(
    entries: &BTreeMap<String, Entry>,
    prefix: &str,
    after: Option<&str>,
    limit: usize,
) -> (Vec<Summary>, bool) {
    let start = match after {
        Some(key) => Bound::Excluded(key),
        None => Bound::Included(prefix),
    };

    let mut matching = entries
        .range::<str, _>((start, Bound::Unbounded))
        .take_while(|entry| entry.0.starts_with(prefix))
        .map(|(key, entry)| Summary {
            key: key.clone(),
            version: entry.version,
            size: entry.value.len(),
        });

    let page: Vec<Summary> = matching
        .by_ref()
        .take(limit)
        .collect();
    let more = matching.next().is_some();

    (page, more)
}
// ANCHOR_END: read
