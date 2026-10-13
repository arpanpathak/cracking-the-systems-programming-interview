//! A member of a shard that elects its own leader.
//!
//! A `Member` is a replica with a role. It follows the Raft algorithm: a
//! follower that hears nothing from a leader stands for election, a
//! candidate that receives the votes of a majority becomes the leader, and
//! a leader replicates its log. The type does no I/O on the network and
//! reads no clock. The caller delivers messages to `handle`, calls `tick`
//! at a fixed interval, and sends the messages that both return.

// ANCHOR: imports
use std::collections::BTreeMap;
use std::fs::{self, File};
use std::io::{self, Write};
use std::path::{Path, PathBuf};

use kv::{Change, Condition, Entry, Log, Record, StoreError, apply, check};
// ANCHOR_END: imports

// ANCHOR: messages
pub type NodeId = u32;

/// Sent by a leader to a follower.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AppendRequest {
    pub term: u64,
    pub leader: NodeId,
    /// The sequence of the record that precedes `records`, and its term.
    pub previous_sequence: u64,
    pub previous_term: u64,
    pub records: Vec<Record>,
    pub committed_sequence: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct AppendAnswer {
    pub term: u64,
    pub from: NodeId,
    pub appended: bool,
    /// When appended: the last sequence that is known to match the leader's
    /// log. When refused: the sequence the leader should continue from.
    pub last_sequence: u64,
}

/// Sent by a candidate to every other member.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct VoteRequest {
    pub term: u64,
    pub candidate: NodeId,
    /// The end of the candidate's log, and the term of its last record.
    pub last_sequence: u64,
    pub last_term: u64,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct VoteAnswer {
    pub term: u64,
    pub from: NodeId,
    pub granted: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Message {
    Append(AppendRequest),
    Appended(AppendAnswer),
    Vote(VoteRequest),
    Voted(VoteAnswer),
}

/// A message and the member it is addressed to.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Outgoing {
    pub to: NodeId,
    pub message: Message,
}
// ANCHOR_END: messages

// ANCHOR: member
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Role {
    Follower,
    Candidate,
    Leader,
}

/// The ticks a follower waits for a leader before it stands for election:
/// 10 to 19, different for each member and each term, so that 2 members
/// seldom stand at the same moment. A tick is 100 ms in the node.
fn election_timeout(id: NodeId, term: u64) -> u64 {
    10 + (u64::from(id) * 7 + term * 3) % 10
}

/// What the leader knows about one follower.
#[derive(Debug, Clone, Copy, Default)]
struct Progress {
    /// The sequence after which the next message to the follower begins.
    next: u64,
    /// The last sequence the follower has confirmed to match.
    matched: u64,
    /// The tick at which the follower last answered.
    heard: u64,
}

pub struct Member {
    id: NodeId,
    peers: Vec<NodeId>,
    directory: PathBuf,
    sync: bool,

    log: Log,
    /// Every record of the log. Record `n` is at index `n - 1`.
    records: Vec<Record>,
    /// The term in which each record was written.
    terms: Vec<u64>,
    entries: BTreeMap<String, Entry>,
    committed: u64,

    /// The current term, and the member this one voted for in it. Both are
    /// stored on disk before any answer that depends on them is sent.
    term: u64,
    voted_for: Option<NodeId>,

    role: Role,
    /// The leader of the current term, when this member knows it.
    leader: Option<NodeId>,
    votes: usize,
    progress: BTreeMap<NodeId, Progress>,
    /// Ticks since the member started, and the tick of the last message
    /// from a leader or the last vote granted.
    now: u64,
    quiet_since: u64,
    /// The records this member has removed from its log because they
    /// differed from a leader's.
    discarded: u64,
}
// ANCHOR_END: member

// ANCHOR: terms
/// The key of a term marker. A client cannot write the empty key, so the
/// log can use it for a record of its own: the first record a new leader
/// appends, whose value is the leader's term.
const MARKER: &str = "";

fn marker(term: u64) -> Change {
    Change::Put {
        key: MARKER.to_owned(),
        value: term.to_le_bytes().to_vec(),
    }
}

/// The term a record starts, if it is a term marker.
fn marked_term(record: &Record) -> Option<u64> {
    let Change::Put { key, value } = &record.change else {
        return None;
    };

    if key != MARKER {
        return None;
    }

    let term: [u8; 8] = value.as_slice().try_into().ok()?;

    Some(u64::from_le_bytes(term))
}

/// The term of each record: the term of the last marker at or before it.
fn terms_of(records: &[Record], mut term: u64) -> Vec<u64> {
    let mut terms = Vec::with_capacity(records.len());

    for record in records {
        term = marked_term(record).unwrap_or(term);
        terms.push(term);
    }

    terms
}
// ANCHOR_END: terms

// ANCHOR: open
impl Member {
    /// Opens the member in `directory`. It starts as a follower, with
    /// nothing applied, in the term it had reached before it stopped.
    pub fn open(
        directory: &Path,
        id: NodeId,
        peers: Vec<NodeId>,
        sync: bool,
    ) -> io::Result<Member> {
        let (log, recovery) = Log::open(directory, sync)?;
        let (term, voted_for) = read_state(directory)?;
        let terms = terms_of(&recovery.records, 0);

        Ok(Member {
            id,
            peers,
            directory: directory.to_owned(),
            sync,
            log,
            records: recovery.records,
            terms,
            entries: BTreeMap::new(),
            committed: 0,
            term,
            voted_for,
            role: Role::Follower,
            leader: None,
            votes: 0,
            progress: BTreeMap::new(),
            now: 0,
            quiet_since: 0,
            discarded: 0,
        })
    }

    pub fn id(&self) -> NodeId {
        self.id
    }

    pub fn role(&self) -> Role {
        self.role
    }

    pub fn term(&self) -> u64 {
        self.term
    }

    pub fn leader(&self) -> Option<NodeId> {
        self.leader
    }

    pub fn last_sequence(&self) -> u64 {
        self.records.len() as u64
    }

    pub fn committed(&self) -> u64 {
        self.committed
    }

    pub fn records(&self) -> &[Record] {
        &self.records
    }

    pub fn discarded(&self) -> u64 {
        self.discarded
    }

    fn last_term(&self) -> u64 {
        self.terms
            .last()
            .copied()
            .unwrap_or(0)
    }

    /// The term of record `sequence`, or 0 for the position before the log.
    fn term_at(&self, sequence: u64) -> u64 {
        if sequence == 0 {
            0
        } else {
            self.terms[sequence as usize - 1]
        }
    }

    fn majority(&self) -> usize {
        let members = self.peers.len() + 1;

        members / 2 + 1
    }
}

// ANCHOR_END: open

// ANCHOR: state
const STATE_FILE: &str = "state";

/// Reads the term and the vote. A member that has no state file has not
/// voted and is in term 0.
fn read_state(directory: &Path) -> io::Result<(u64, Option<NodeId>)> {
    let text = match fs::read_to_string(directory.join(STATE_FILE)) {
        Ok(text) => text,
        Err(error) if error.kind() == io::ErrorKind::NotFound => return Ok((0, None)),
        Err(error) => return Err(error),
    };

    let mut fields = text
        .split_whitespace()
        .map(str::parse::<u64>);
    let invalid = || io::Error::new(io::ErrorKind::InvalidData, "the state file is malformed");
    let term = fields
        .next()
        .and_then(Result::ok)
        .ok_or_else(invalid)?;
    let voted_for = fields
        .next()
        .and_then(Result::ok)
        .map(|id| id as NodeId);

    Ok((term, voted_for))
}

impl Member {
    /// Stores the term and the vote. The new file replaces the old one in a
    /// single step, so a crash leaves one of the 2 and not a mixture.
    fn save_state(&self) -> io::Result<()> {
        let temporary = self.directory.join("state.new");
        let vote = self
            .voted_for
            .map_or(String::new(), |id| id.to_string());
        let mut file = File::create(&temporary)?;

        file.write_all(format!("{} {vote}\n", self.term).as_bytes())?;

        if self.sync {
            file.sync_all()?;
        }

        fs::rename(&temporary, self.directory.join(STATE_FILE))?;

        if self.sync {
            File::open(&self.directory)?.sync_all()?;
        }

        Ok(())
    }
}
// ANCHOR_END: state

// ANCHOR: commit
impl Member {
    /// Applies the records up to `sequence` that are not applied yet. Term
    /// markers are records of the log and are not entries.
    fn commit(&mut self, sequence: u64) {
        let until = sequence.min(self.last_sequence());

        // A record that marks the start of a term changes no key.
        let changes: Vec<Record> = (self.committed..until)
            .map(|index| self.records[index as usize].clone())
            .filter(|record| marked_term(record).is_none())
            .collect();

        for record in changes {
            apply(&mut self.entries, record);
        }

        self.committed = self.committed.max(until);
    }

    /// The leader's commit rule. A record of an earlier term is not counted
    /// on its own: it becomes committed together with the first record of
    /// the leader's own term that a majority has stored.
    fn advance(&mut self) {
        let mut stored: Vec<u64> = self
            .progress
            .values()
            .map(|progress| progress.matched)
            .collect();
        stored.push(self.last_sequence());
        stored.sort_unstable_by(|a, b| b.cmp(a));

        let on_majority = stored[self.majority() - 1];

        if on_majority > self.committed && self.term_at(on_majority) == self.term {
            self.commit(on_majority);
        }
    }
}
// ANCHOR_END: commit

// ANCHOR: step_down
impl Member {
    /// Moves to a newer term as a follower. The vote of the old term does
    /// not carry over.
    fn step_down(&mut self, term: u64) -> io::Result<()> {
        if term > self.term {
            self.term = term;
            self.voted_for = None;
            self.save_state()?;
        }

        self.role = Role::Follower;
        self.leader = None;
        self.progress.clear();

        Ok(())
    }
}
// ANCHOR_END: step_down

// ANCHOR: stand
impl Member {
    /// Stands for election in the next term.
    fn stand(&mut self) -> io::Result<Vec<Outgoing>> {
        self.term += 1;
        self.voted_for = Some(self.id);
        self.save_state()?;

        self.role = Role::Candidate;
        self.leader = None;
        self.votes = 1;
        self.quiet_since = self.now;

        let request = VoteRequest {
            term: self.term,
            candidate: self.id,
            last_sequence: self.last_sequence(),
            last_term: self.last_term(),
        };

        Ok(self
            .peers
            .iter()
            .map(|&to| Outgoing {
                to,
                message: Message::Vote(request),
            })
            .collect())
    }
}
// ANCHOR_END: stand

// ANCHOR: lead
impl Member {
    /// Becomes the leader of the current term. The first record of the term
    /// is its marker. When a majority has stored the marker, every earlier
    /// record is committed with it.
    fn lead(&mut self) -> io::Result<Vec<Outgoing>> {
        self.role = Role::Leader;
        self.leader = Some(self.id);

        let next = self.last_sequence();
        self.progress = self
            .peers
            .iter()
            .map(|&peer| {
                (
                    peer,
                    Progress {
                        next,
                        matched: 0,
                        heard: self.now,
                    },
                )
            })
            .collect();

        let record = self.log.append(marker(self.term))?;
        self.records.push(record);
        self.terms.push(self.term);

        Ok(self.replicate())
    }
}
// ANCHOR_END: lead

// ANCHOR: tick
impl Member {
    /// Advances the member's clock by one tick. A leader sends every
    /// follower a message. A follower or a candidate that has waited for
    /// its election timeout stands for election.
    pub fn tick(&mut self) -> io::Result<Vec<Outgoing>> {
        self.now += 1;

        if self.role == Role::Leader {
            return Ok(self.replicate());
        }

        if self.now - self.quiet_since >= election_timeout(self.id, self.term) {
            return self.stand();
        }

        Ok(Vec::new())
    }

    /// A message for every follower: the records it lacks, or a heartbeat.
    pub fn replicate(&self) -> Vec<Outgoing> {
        self.peers
            .iter()
            .filter_map(|&peer| self.append_for(peer))
            .collect()
    }

    fn append_for(&self, peer: NodeId) -> Option<Outgoing> {
        let from = self
            .progress
            .get(&peer)?
            .next
            .min(self.last_sequence());

        let request = AppendRequest {
            term: self.term,
            leader: self.id,
            previous_sequence: from,
            previous_term: self.term_at(from),
            records: self.records[from as usize..].to_vec(),
            committed_sequence: self.committed,
        };

        Some(Outgoing {
            to: peer,
            message: Message::Append(request),
        })
    }
}
// ANCHOR_END: tick

// ANCHOR: handle
impl Member {
    /// Processes a message and returns the messages to send in response.
    pub fn handle(&mut self, message: Message) -> io::Result<Vec<Outgoing>> {
        match message {
            Message::Append(request) => {
                let to = request.leader;
                let answer = self.on_append(request)?;

                Ok(vec![Outgoing {
                    to,
                    message: Message::Appended(answer),
                }])
            }
            Message::Vote(request) => {
                let to = request.candidate;
                let answer = self.on_vote(request)?;

                Ok(vec![Outgoing {
                    to,
                    message: Message::Voted(answer),
                }])
            }
            Message::Appended(answer) => self.on_appended(answer),
            Message::Voted(answer) => self.on_voted(answer),
        }
    }
}
// ANCHOR_END: handle

// ANCHOR: vote
impl Member {
    /// A member grants its vote once in a term, and only to a candidate
    /// whose log is at least as complete as its own.
    fn on_vote(&mut self, request: VoteRequest) -> io::Result<VoteAnswer> {
        if request.term > self.term {
            self.step_down(request.term)?;
        }

        let complete =
            (request.last_term, request.last_sequence) >= (self.last_term(), self.last_sequence());
        let free = self
            .voted_for
            .is_none_or(|id| id == request.candidate);
        let granted = request.term == self.term && complete && free;

        if granted {
            self.voted_for = Some(request.candidate);
            self.save_state()?;
            self.quiet_since = self.now;
        }

        Ok(VoteAnswer {
            term: self.term,
            from: self.id,
            granted,
        })
    }

    fn on_voted(&mut self, answer: VoteAnswer) -> io::Result<Vec<Outgoing>> {
        if answer.term > self.term {
            self.step_down(answer.term)?;

            return Ok(Vec::new());
        }

        if self.role != Role::Candidate || answer.term != self.term || !answer.granted {
            return Ok(Vec::new());
        }

        self.votes += 1;

        if self.votes >= self.majority() {
            self.lead()
        } else {
            Ok(Vec::new())
        }
    }
}
// ANCHOR_END: vote

// ANCHOR: on_append
impl Member {
    fn on_append(&mut self, request: AppendRequest) -> io::Result<AppendAnswer> {
        let refuse = |member: &Member, last_sequence| AppendAnswer {
            term: member.term,
            from: member.id,
            appended: false,
            last_sequence,
        };

        if request.term < self.term {
            return Ok(refuse(self, self.last_sequence()));
        }

        // A message of the current term or a newer one comes from the leader.
        self.step_down(request.term)?;
        self.leader = Some(request.leader);
        self.quiet_since = self.now;

        if request.previous_sequence > self.last_sequence() {
            return Ok(refuse(self, self.last_sequence()));
        }

        if self.term_at(request.previous_sequence) != request.previous_term {
            return Ok(refuse(self, request.previous_sequence - 1));
        }

        let matched = request.previous_sequence + request.records.len() as u64;
        self.store(
            request.previous_sequence,
            request.previous_term,
            request.records,
        )?;
        self.commit(
            request
                .committed_sequence
                .min(matched),
        );

        Ok(AppendAnswer {
            term: self.term,
            from: self.id,
            appended: true,
            last_sequence: matched,
        })
    }
}
// ANCHOR_END: on_append

// ANCHOR: store
impl Member {
    /// Makes the log equal to the leader's from `previous` onward: records
    /// the member already has are skipped, a record that differs is removed
    /// together with everything after it, and the rest is appended.
    fn store(&mut self, previous: u64, previous_term: u64, records: Vec<Record>) -> io::Result<()> {
        let terms = terms_of(&records, previous_term);
        let mut fresh = 0;

        for (index, record) in records.iter().enumerate() {
            let sequence = previous + index as u64 + 1;

            if sequence > self.last_sequence() {
                break;
            }

            if self.term_at(sequence) != terms[index]
                || &self.records[sequence as usize - 1] != record
            {
                self.truncate(sequence - 1)?;

                break;
            }

            fresh = index + 1;
        }

        if fresh < records.len() {
            self.log
                .append_records(&records[fresh..])?;
            self.records
                .extend_from_slice(&records[fresh..]);
            self.terms
                .extend_from_slice(&terms[fresh..]);
        }

        Ok(())
    }
}
// ANCHOR_END: store

// ANCHOR: truncate
impl Member {
    /// Removes the records after `keep`. Only records that are not
    /// committed can differ from the leader's, so none of them is applied.
    fn truncate(&mut self, keep: u64) -> io::Result<()> {
        if keep < self.committed {
            return Err(io::Error::other(format!(
                "record {} is committed and differs from the leader's",
                keep + 1
            )));
        }

        let length: usize = self.records[..keep as usize]
            .iter()
            .map(|record| record.encode().len())
            .sum();

        self.discarded += self.last_sequence() - keep;
        self.log
            .truncate(keep, length as u64)?;
        self.records.truncate(keep as usize);
        self.terms.truncate(keep as usize);

        Ok(())
    }
}
// ANCHOR_END: truncate

// ANCHOR: on_appended
impl Member {
    fn on_appended(&mut self, answer: AppendAnswer) -> io::Result<Vec<Outgoing>> {
        if answer.term > self.term {
            self.step_down(answer.term)?;

            return Ok(Vec::new());
        }

        if self.role != Role::Leader || answer.term != self.term {
            return Ok(Vec::new());
        }

        let now = self.now;
        let Some(progress) = self.progress.get_mut(&answer.from) else {
            return Ok(Vec::new());
        };

        progress.heard = now;
        progress.next = answer.last_sequence;

        if answer.appended {
            progress.matched = progress
                .matched
                .max(answer.last_sequence);
        }

        let behind = !answer.appended || answer.last_sequence < self.last_sequence();
        self.advance();

        Ok(if behind {
            self.append_for(answer.from)
                .into_iter()
                .collect()
        } else {
            Vec::new()
        })
    }
}
// ANCHOR_END: on_appended

// ANCHOR: client
impl Member {
    /// Whether this member is the leader and every record of its log is
    /// committed, so that it can accept a write.
    pub fn is_settled(&self) -> bool {
        self.role == Role::Leader && self.committed == self.last_sequence()
    }

    /// Checks the condition of a write and appends its record to the log.
    /// The caller sends the messages of `replicate` afterwards.
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
        self.terms.push(self.term);

        Ok(sequence)
    }

    /// Whether this member may answer a read: it is the leader, the marker
    /// of its term is committed, and a majority of the members, itself
    /// included, has answered within the last 10 ticks.
    pub fn can_read(&self) -> bool {
        let recent = self
            .progress
            .values()
            .filter(|progress| self.now - progress.heard < 10)
            .count();

        self.role == Role::Leader
            && self.term_at(self.committed) == self.term
            && recent + 1 >= self.majority()
    }

    pub fn get(&self, key: &str) -> Option<&Entry> {
        self.entries.get(key)
    }
}
// ANCHOR_END: client
