//! A node of a replicated shard: a replica, and for a leader the tasks that
//! keep its followers up to date.

// ANCHOR: imports
use std::sync::Arc;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::time::{Duration, Instant};

use kv::{Change, Condition, Entry, Summary, Written};
use kvd::api::ApiError;
use parking_lot::Mutex;
use repl::{Appended, Replica, majority_sequence};
use tokio::sync::{Notify, watch};
use tokio::task;
use tokio::time::{sleep, timeout};
use tonic::transport::{Channel, Endpoint};

use crate::rpc::{ReplicationClient, proto};
// ANCHOR_END: imports

// ANCHOR: types
/// How often a leader sends a message to a follower that has nothing new to receive.
const HEARTBEAT: Duration = Duration::from_millis(100);

/// How long a leader waits for the answer to one message.
const ANSWER: Duration = Duration::from_millis(500);

/// How long a write waits for its record to reach a majority.
const COMMIT: Duration = Duration::from_secs(1);

/// What the leader knows about one follower.
pub struct Peer {
    pub address: String,
    /// The last sequence the follower has reported.
    reported: AtomicU64,
    /// When the follower last answered.
    heard: Mutex<Option<Instant>>,
}

pub struct Node {
    pub replica: Mutex<Replica>,
    pub leader: bool,
    pub peers: Vec<Peer>,
    /// The sequence the log ended at when the node started. A leader serves
    /// reads once this much is committed.
    ready: u64,
    /// Held by the write that is in progress, so that writes take turns.
    turn: tokio::sync::Mutex<()>,
    /// The committed sequence, for writes that wait for it to advance.
    committed: watch::Sender<u64>,
    /// Signalled when the leader has appended a record.
    appended: Notify,
    /// Set when a follower answers with a newer term: another leader exists.
    deposed: AtomicBool,
}

impl Node {
    pub fn new(replica: Replica, leader: bool, followers: Vec<String>) -> Arc<Node> {
        let peer = |address| Peer {
            address,
            reported: AtomicU64::new(0),
            heard: Mutex::new(None),
        };

        Arc::new(Node {
            ready: replica.last_sequence(),
            replica: Mutex::new(replica),
            leader,
            peers: followers
                .into_iter()
                .map(peer)
                .collect(),
            turn: tokio::sync::Mutex::new(()),
            committed: watch::Sender::new(0),
            appended: Notify::new(),
            deposed: AtomicBool::new(false),
        })
    }
}
// ANCHOR_END: types

// ANCHOR: follow
impl Node {
    /// Starts one task for each follower. A task sends the follower what it
    /// lacks, again and again, for as long as the node runs.
    pub fn lead(self: &Arc<Node>) -> Result<(), tonic::transport::Error> {
        for index in 0..self.peers.len() {
            let channel = Endpoint::from_shared(self.peers[index].address.clone())?
                .connect_timeout(ANSWER)
                .connect_lazy();

            tokio::spawn(Arc::clone(self).follow(index, ReplicationClient::new(channel)));
        }

        Ok(())
    }

    async fn follow(self: Arc<Node>, index: usize, mut client: ReplicationClient<Channel>) {
        let peer = &self.peers[index];

        loop {
            let message = self.replica.lock().append_for(
                peer.reported
                    .load(Ordering::Relaxed),
            );
            let request = proto::AppendRequest::from(message);

            let answer = timeout(ANSWER, client.append(request)).await;

            // An answer that did not come counts as a peer that is up to date:
            // the next round is a heartbeat, which finds out more.
            let behind = answer
                .ok()
                .and_then(Result::ok)
                .is_some_and(|answer| self.record(peer, answer.into_inner().into()));

            if !behind {
                // Wait for a new record, or send a heartbeat when none comes.
                tokio::select! {
                    () = self.appended.notified() => {}
                    () = sleep(HEARTBEAT) => {}
                }
            }
        }
    }
}
// ANCHOR_END: follow

// ANCHOR: record
impl Node {
    /// Takes note of a follower's answer and commits what a majority now
    /// holds. It returns whether the follower still lacks records.
    fn record(&self, peer: &Peer, answer: Appended) -> bool {
        let mut replica = self.replica.lock();

        if answer.term > replica.term() {
            self.deposed
                .store(true, Ordering::Relaxed);

            return false;
        }

        peer.reported
            .store(answer.last_sequence, Ordering::Relaxed);
        *peer.heard.lock() = Some(Instant::now());

        let mut stored: Vec<u64> = self
            .peers
            .iter()
            .map(|peer| {
                peer.reported
                    .load(Ordering::Relaxed)
            })
            .collect();
        stored.push(replica.last_sequence());

        replica.commit(majority_sequence(stored));
        self.committed
            .send_replace(replica.committed());

        answer.last_sequence < replica.last_sequence()
    }
}
// ANCHOR_END: record

// ANCHOR: write
impl Node {
    /// A write on the leader: wait for a turn, append the record, and wait
    /// until a majority of the replicas hold it.
    pub async fn write(&self, change: Change, condition: Condition) -> Result<Written, ApiError> {
        self.must_lead()?;

        let turn = self.turn.lock().await;
        let last = self.replica.lock().last_sequence();
        self.wait_for(last).await?;

        let proposed = task::block_in_place(|| {
            let mut replica = self.replica.lock();
            let created = match &change {
                Change::Put { key, .. } | Change::Delete { key } => replica.get(key).is_none(),
            };

            replica
                .propose(change, condition)
                .map(|version| Written { version, created })
        })?;

        self.appended.notify_waiters();
        self.wait_for(proposed.version)
            .await?;
        drop(turn);

        Ok(proposed)
    }

    /// Waits until the record with this sequence is committed.
    async fn wait_for(&self, sequence: u64) -> Result<(), ApiError> {
        let mut committed = self.committed.subscribe();

        let reached = committed.wait_for(|&committed| committed >= sequence);
        let in_time = timeout(COMMIT, reached)
            .await
            .is_ok_and(|reached| reached.is_ok());

        if in_time {
            Ok(())
        } else {
            Err(ApiError::Unavailable(format!(
                "record {sequence} is not on a majority of the replicas"
            )))
        }
    }

    fn must_lead(&self) -> Result<(), ApiError> {
        if !self.leader {
            return Err(ApiError::Misdirected("this node is a follower".into()));
        }

        if self.deposed.load(Ordering::Relaxed) {
            return Err(ApiError::Misdirected(
                "a leader of a newer term exists".into(),
            ));
        }

        Ok(())
    }
}
// ANCHOR_END: write

// ANCHOR: read
impl Node {
    /// A leader serves reads while a majority of the replicas, itself
    /// included, has answered within the last second, and once everything
    /// its log held at start is committed.
    fn must_serve_reads(&self) -> Result<(), ApiError> {
        self.must_lead()?;

        let recently = |peer: &&Peer| {
            peer.heard
                .lock()
                .is_some_and(|at| at.elapsed() < COMMIT)
        };
        let reachable = 1 + self
            .peers
            .iter()
            .filter(recently)
            .count();

        if 2 * reachable <= self.peers.len() + 1 {
            return Err(ApiError::Unavailable(
                "this leader cannot reach a majority of the replicas".into(),
            ));
        }

        if self.replica.lock().committed() < self.ready {
            return Err(ApiError::Unavailable(
                "the records from before the restart are not committed yet".into(),
            ));
        }

        Ok(())
    }

    pub fn get(&self, key: &str) -> Result<Entry, ApiError> {
        self.must_serve_reads()?;

        self.replica
            .lock()
            .get(key)
            .cloned()
            .ok_or(ApiError::NotFound)
    }

    pub fn list(
        &self,
        prefix: &str,
        after: Option<&str>,
        limit: usize,
    ) -> Result<(Vec<Summary>, bool), ApiError> {
        self.must_serve_reads()?;

        Ok(self
            .replica
            .lock()
            .list(prefix, after, limit))
    }

    /// The last sequence each follower has reported.
    pub fn reported(&self) -> Vec<u64> {
        self.peers
            .iter()
            .map(|peer| {
                peer.reported
                    .load(Ordering::Relaxed)
            })
            .collect()
    }
}
// ANCHOR_END: read
