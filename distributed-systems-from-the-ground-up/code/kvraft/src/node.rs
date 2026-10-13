//! A node: a member, its clock, and the connections that carry its
//! messages to the other members.

// ANCHOR: imports
use std::collections::BTreeMap;
use std::io;
use std::sync::Arc;
use std::time::Duration;

use kv::{Change, Condition, Entry, Written};
use kvd::api::ApiError;
use parking_lot::Mutex;
use raft::{Member, Message, NodeId, Outgoing, Role};
use tokio::sync::watch;
use tokio::task;
use tokio::time::{interval, timeout};
use tonic::transport::{Channel, Endpoint};

use crate::rpc::{ElectionClient, ReplicationClient, appended, proto, voted};
// ANCHOR_END: imports

// ANCHOR: types
/// The length of a tick of the member's clock.
pub const TICK: Duration = Duration::from_millis(100);

/// How long a member waits for the answer to one message.
const ANSWER: Duration = Duration::from_millis(500);

/// How long a write waits for its record to be committed.
const COMMIT: Duration = Duration::from_secs(1);

pub struct Node {
    pub member: Mutex<Member>,
    /// A connection to each of the other members.
    peers: BTreeMap<NodeId, Channel>,
    /// Held by the write that is in progress.
    turn: tokio::sync::Mutex<()>,
    /// The committed sequence, for writes that wait for it to advance.
    committed: watch::Sender<u64>,
}

impl Node {
    pub fn new(
        member: Member,
        addresses: BTreeMap<NodeId, String>,
    ) -> Result<Arc<Node>, tonic::transport::Error> {
        let mut peers = BTreeMap::new();

        for (id, address) in addresses {
            peers.insert(
                id,
                Endpoint::from_shared(address)?
                    .connect_timeout(ANSWER)
                    .connect_lazy(),
            );
        }

        Ok(Arc::new(Node {
            member: Mutex::new(member),
            peers,
            turn: tokio::sync::Mutex::new(()),
            committed: watch::Sender::new(0),
        }))
    }
}
// ANCHOR_END: types

// ANCHOR: with_member
impl Node {
    /// Runs one operation on the member and publishes the committed
    /// sequence. The member waits for the disk, so the operation runs where
    /// blocking is allowed.
    fn with_member<T>(&self, operation: impl FnOnce(&mut Member) -> T) -> T {
        task::block_in_place(|| {
            let mut member = self.member.lock();
            let result = operation(&mut member);
            self.committed
                .send_replace(member.committed());

            result
        })
    }
}
// ANCHOR_END: with_member

// ANCHOR: send
impl Node {
    /// Sends each message in a task of its own, so that a member that does
    /// not answer delays nothing else.
    fn dispatch(self: &Arc<Node>, messages: Vec<Outgoing>) {
        for message in messages {
            tokio::spawn(Arc::clone(self).send(message));
        }
    }

    /// Carries one request to a member and gives the answer to this member.
    async fn send(self: Arc<Node>, outgoing: Outgoing) {
        let Some(channel) = self
            .peers
            .get(&outgoing.to)
            .cloned()
        else {
            return;
        };

        let answer = match outgoing.message {
            Message::Append(request) => {
                let call = async move {
                    ReplicationClient::new(channel)
                        .append(proto::AppendRequest::from(request))
                        .await
                };

                timeout(ANSWER, call)
                    .await
                    .ok()
                    .and_then(Result::ok)
                    .map(|answer| appended(outgoing.to, answer.into_inner()))
            }
            Message::Vote(request) => {
                let call = async move {
                    ElectionClient::new(channel)
                        .request_vote(proto::VoteRequest::from(request))
                        .await
                };

                timeout(ANSWER, call)
                    .await
                    .ok()
                    .and_then(Result::ok)
                    .map(|answer| voted(outgoing.to, answer.into_inner()))
            }
            // An answer travels as the response of the call that asked.
            Message::Appended(..) | Message::Voted(..) => None,
        };

        if let Some(answer) = answer {
            self.deliver(answer);
        }
    }

    /// Gives the member a message and sends what the member returns.
    fn deliver(self: &Arc<Node>, message: Message) {
        match self.with_member(|member| member.handle(message)) {
            Ok(messages) => self.dispatch(messages),
            Err(error) => eprintln!("the member could not process a message: {error}"),
        }
    }
}
// ANCHOR_END: send

// ANCHOR: clock
impl Node {
    /// The member's answer to a request that arrived over gRPC.
    pub fn answer(&self, request: Message) -> io::Result<Message> {
        let mut messages = self.with_member(|member| member.handle(request))?;

        messages
            .pop()
            .map(|outgoing| outgoing.message)
            .ok_or_else(|| io::Error::other("the member gave no answer"))
    }

    /// Advances the member's clock, for as long as the node runs.
    pub async fn run_clock(self: Arc<Node>) {
        let mut ticks = interval(TICK);

        loop {
            ticks.tick().await;

            match self.with_member(Member::tick) {
                Ok(messages) => self.dispatch(messages),
                Err(error) => eprintln!("the member could not advance its clock: {error}"),
            }
        }
    }
}
// ANCHOR_END: clock

// ANCHOR: write
impl Node {
    fn not_leader(member: &Member) -> ApiError {
        match member.leader() {
            Some(leader) => ApiError::Misdirected(format!("the leader is member {leader}")),
            None => ApiError::NoLeader,
        }
    }

    /// A write on the leader. It is acknowledged when its record is
    /// committed and this member has led the same term throughout.
    pub async fn write(
        self: &Arc<Node>,
        change: Change,
        condition: Condition,
    ) -> Result<Written, ApiError> {
        let turn = self.turn.lock().await;

        let last = {
            let member = self.member.lock();

            if member.role() != Role::Leader {
                return Err(Node::not_leader(&member));
            }

            member.last_sequence()
        };

        self.wait_for(last).await?;

        let (written, term, messages) = self.with_member(|member| {
            if !member.is_settled() {
                return Err(Node::not_leader(member));
            }

            let created = match &change {
                Change::Put { key, .. } | Change::Delete { key } => member.get(key).is_none(),
            };
            let version = member.propose(change, condition)?;

            Ok((
                Written { version, created },
                member.term(),
                member.replicate(),
            ))
        })?;

        self.dispatch(messages);
        self.wait_for(written.version)
            .await?;
        drop(turn);

        // A member that lost the leadership while it waited may hold another
        // leader's record at this sequence.
        let member = self.member.lock();

        if member.role() == Role::Leader && member.term() == term {
            Ok(written)
        } else {
            Err(ApiError::Unavailable(
                "the leadership changed before the record was committed".into(),
            ))
        }
    }

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
                "record {sequence} is not on a majority of the members"
            )))
        }
    }

    pub fn get(&self, key: &str) -> Result<Entry, ApiError> {
        let member = self.member.lock();

        if member.role() != Role::Leader {
            return Err(Node::not_leader(&member));
        }

        if !member.can_read() {
            return Err(ApiError::Unavailable(
                "this leader cannot confirm that it still leads".into(),
            ));
        }

        member
            .get(key)
            .cloned()
            .ok_or(ApiError::NotFound)
    }
}
// ANCHOR_END: write
