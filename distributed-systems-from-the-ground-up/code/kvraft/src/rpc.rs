//! The gRPC services of a member: the generated types, their conversion to
//! the messages of the `raft` crate, and the server side of both calls.

// ANCHOR: imports
use std::sync::Arc;

use kv::{Change, Record};
use raft::{AppendAnswer, AppendRequest, Message, NodeId, VoteAnswer, VoteRequest};
use tonic::{Request, Response, Status};

use crate::node::Node;
// ANCHOR_END: imports

// ANCHOR: generated
/// The types that `build.rs` generates from `proto/store.proto`. The schema
/// also defines the ring, which this program does not use.
#[allow(dead_code)]
pub mod proto {
    tonic::include_proto!("store.v1");
}

pub use proto::election_client::ElectionClient;
pub use proto::election_server::{Election, ElectionServer};
pub use proto::replication_client::ReplicationClient;
pub use proto::replication_server::{Replication, ReplicationServer};
// ANCHOR_END: generated

// ANCHOR: convert
fn record_to_proto(record: &Record) -> proto::Record {
    let change = match record.change.clone() {
        Change::Put { key, value } => proto::record::Change::Put(proto::Put { key, value }),
        Change::Delete { key } => proto::record::Change::Delete(proto::Delete { key }),
    };

    proto::Record {
        sequence: record.sequence,
        change: Some(change),
    }
}

fn record_from_proto(record: proto::Record) -> Result<Record, Status> {
    let change = match record.change {
        Some(proto::record::Change::Put(put)) => Change::Put {
            key: put.key,
            value: put.value,
        },
        Some(proto::record::Change::Delete(delete)) => Change::Delete { key: delete.key },
        None => return Err(Status::invalid_argument("a record without a change")),
    };

    Ok(Record {
        sequence: record.sequence,
        change,
    })
}

impl From<AppendRequest> for proto::AppendRequest {
    fn from(request: AppendRequest) -> Self {
        proto::AppendRequest {
            shard: 0,
            term: request.term,
            previous_sequence: request.previous_sequence,
            records: request
                .records
                .iter()
                .map(record_to_proto)
                .collect(),
            committed_sequence: request.committed_sequence,
            previous_term: request.previous_term,
            leader: request.leader,
        }
    }
}

impl TryFrom<proto::AppendRequest> for AppendRequest {
    type Error = Status;

    fn try_from(request: proto::AppendRequest) -> Result<Self, Status> {
        Ok(AppendRequest {
            term: request.term,
            leader: request.leader,
            previous_sequence: request.previous_sequence,
            previous_term: request.previous_term,
            records: request
                .records
                .into_iter()
                .map(record_from_proto)
                .collect::<Result<_, _>>()?,
            committed_sequence: request.committed_sequence,
        })
    }
}

impl From<VoteRequest> for proto::VoteRequest {
    fn from(request: VoteRequest) -> Self {
        proto::VoteRequest {
            term: request.term,
            candidate: request.candidate,
            last_sequence: request.last_sequence,
            last_term: request.last_term,
        }
    }
}

/// The answer of member `from` to an `Append` call, as a message.
pub fn appended(from: NodeId, answer: proto::AppendResponse) -> Message {
    Message::Appended(AppendAnswer {
        term: answer.term,
        from,
        appended: answer.appended,
        last_sequence: answer.last_sequence,
    })
}

/// The answer of member `from` to a `RequestVote` call, as a message.
pub fn voted(from: NodeId, answer: proto::VoteResponse) -> Message {
    Message::Voted(VoteAnswer {
        term: answer.term,
        from,
        granted: answer.granted,
    })
}
// ANCHOR_END: convert

// ANCHOR: service
/// The server side of both services. Each call is one message for the
/// member, and the member's answer is the response of the call.
pub struct Service {
    pub node: Arc<Node>,
}

#[tonic::async_trait]
impl Replication for Service {
    async fn append(
        &self,
        request: Request<proto::AppendRequest>,
    ) -> Result<Response<proto::AppendResponse>, Status> {
        let request = AppendRequest::try_from(request.into_inner())?;

        let answer = self
            .node
            .answer(Message::Append(request))
            .map_err(|error| Status::unavailable(error.to_string()))?;

        let Message::Appended(answer) = answer else {
            return Err(Status::internal(
                "the member answered with another kind of message",
            ));
        };

        Ok(Response::new(proto::AppendResponse {
            term: answer.term,
            appended: answer.appended,
            last_sequence: answer.last_sequence,
        }))
    }
}

#[tonic::async_trait]
impl Election for Service {
    async fn request_vote(
        &self,
        request: Request<proto::VoteRequest>,
    ) -> Result<Response<proto::VoteResponse>, Status> {
        let request = request.into_inner();
        let request = VoteRequest {
            term: request.term,
            candidate: request.candidate,
            last_sequence: request.last_sequence,
            last_term: request.last_term,
        };

        let answer = self
            .node
            .answer(Message::Vote(request))
            .map_err(|error| Status::unavailable(error.to_string()))?;

        let Message::Voted(answer) = answer else {
            return Err(Status::internal(
                "the member answered with another kind of message",
            ));
        };

        Ok(Response::new(proto::VoteResponse {
            term: answer.term,
            granted: answer.granted,
        }))
    }
}
// ANCHOR_END: service
