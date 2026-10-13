//! Replication of a log from a leader to its followers.
//!
//! A `Replica` is one copy of a shard: a log, and the entries that result
//! from the records that are known to be on a majority of the copies. The
//! same type serves as leader and as follower. This module does no I/O on
//! the network. It builds the messages and processes them, and the caller
//! carries them between replicas.

// ANCHOR: imports
use std::collections::BTreeMap;
use std::io;
use std::path::Path;

use kv::{Change, Condition, Entry, Log, Record, StoreError, Summary, apply, check, page};
// ANCHOR_END: imports

// ANCHOR: messages
/// The message a leader sends to a follower.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Append {
    /// The term of the sender.
    pub term: u64,
    /// The sequence of the record that precedes `records` in the leader's log.
    pub previous_sequence: u64,
    pub records: Vec<Record>,
    /// Every record up to this sequence is on a majority of the replicas.
    pub committed_sequence: u64,
}

/// The follower's answer.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Appended {
    pub term: u64,
    /// False when the follower's log does not end at `previous_sequence`,
    /// or when the sender's term is older than the follower's.
    pub appended: bool,
    /// The sequence of the last record in the follower's log.
    pub last_sequence: u64,
}
// ANCHOR_END: messages

// ANCHOR: replica
pub struct Replica {
    log: Log,
    /// Every record of the log, in order. Record `n` is at index `n - 1`.
    records: Vec<Record>,
    /// The result of applying the records up to `committed`.
    entries: BTreeMap<String, Entry>,
    /// The sequence of the last record that is applied to `entries`.
    committed: u64,
    term: u64,
}

impl Replica {
    /// Opens the replica in `directory`. Nothing is applied yet: a replica
    /// that has restarted does not know which of its records are committed.
    pub fn open(directory: &Path, sync: bool, term: u64) -> io::Result<Replica> {
        let (log, recovery) = Log::open(directory, sync)?;

        Ok(Replica {
            log,
            records: recovery.records,
            entries: BTreeMap::new(),
            committed: 0,
            term,
        })
    }

    pub fn term(&self) -> u64 {
        self.term
    }

    pub fn last_sequence(&self) -> u64 {
        self.records.len() as u64
    }

    pub fn committed(&self) -> u64 {
        self.committed
    }

    /// One page of the committed keys.
    pub fn list(&self, prefix: &str, after: Option<&str>, limit: usize) -> (Vec<Summary>, bool) {
        page(&self.entries, prefix, after, limit)
    }

    /// Every record of the log, in order.
    pub fn records(&self) -> &[Record] {
        &self.records
    }

    /// The committed value of a key.
    pub fn get(&self, key: &str) -> Option<&Entry> {
        self.entries.get(key)
    }

    /// Applies the records up to `sequence` that are not applied yet.
    pub fn commit(&mut self, sequence: u64) {
        let until = sequence.min(self.last_sequence());

        while self.committed < until {
            apply(
                &mut self.entries,
                self.records[self.committed as usize].clone(),
            );
            self.committed += 1;
        }
    }
}
// ANCHOR_END: replica

// ANCHOR: propose
impl Replica {
    /// Whether every record of the log is committed. A leader accepts a new
    /// write only in this state, so that the condition of the write is
    /// checked against the result of all earlier writes.
    pub fn is_settled(&self) -> bool {
        self.committed == self.last_sequence()
    }

    /// Checks the condition of a write and appends its record to the
    /// leader's log. The record is not applied: it is not committed yet.
    pub fn propose(&mut self, change: Change, condition: Condition) -> Result<u64, StoreError> {
        let key = match &change {
            Change::Put { key, .. } | Change::Delete { key } => key,
        };
        let current = self
            .entries
            .get(key)
            .map(|entry| entry.version);

        if matches!(change, Change::Delete { .. }) && current.is_none() {
            return Err(StoreError::NotFound);
        }

        check(condition, current)?;

        let record = self.log.append(change)?;
        let sequence = record.sequence;
        self.records.push(record);

        Ok(sequence)
    }
}
// ANCHOR_END: propose

// ANCHOR: append_for
impl Replica {
    /// The message that brings a follower whose log ends at `follower_last`
    /// up to the end of this log. With nothing to send it is a heartbeat.
    pub fn append_for(&self, follower_last: u64) -> Append {
        let from = follower_last.min(self.last_sequence()) as usize;

        Append {
            term: self.term,
            previous_sequence: from as u64,
            records: self.records[from..].to_vec(),
            committed_sequence: self.committed,
        }
    }
}

// ANCHOR_END: append_for

// ANCHOR: majority
/// The highest sequence that is stored on a majority, given the last
/// sequence of every replica, the leader included.
pub fn majority_sequence(mut last_sequences: Vec<u64>) -> u64 {
    last_sequences.sort_unstable_by(|a, b| b.cmp(a));

    last_sequences
        .get(last_sequences.len() / 2)
        .copied()
        .unwrap_or(0)
}
// ANCHOR_END: majority

// ANCHOR: follower
impl Replica {
    /// Processes a message from a leader.
    pub fn handle_append(&mut self, request: Append) -> io::Result<Appended> {
        let refuse = |replica: &Replica| Appended {
            term: replica.term,
            appended: false,
            last_sequence: replica.last_sequence(),
        };

        if request.term < self.term {
            return Ok(refuse(self));
        }

        self.term = request.term;

        if request.previous_sequence != self.last_sequence() {
            return Ok(refuse(self));
        }

        if !request.records.is_empty() {
            self.log
                .append_records(&request.records)?;
            self.records.extend(request.records);
        }

        self.commit(request.committed_sequence);

        Ok(Appended {
            term: self.term,
            appended: true,
            last_sequence: self.last_sequence(),
        })
    }
}
// ANCHOR_END: follower
