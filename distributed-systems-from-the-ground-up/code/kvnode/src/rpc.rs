//! The replication service: the generated gRPC types, the conversion between
//! them and the types of the `repl` crate, and the server side that a
//! follower runs.

// ANCHOR: imports
use std::sync::Arc;

use kv::{Change, Record};
use repl::{Append, Appended};
use tokio::task;
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

pub use proto::replication_client::ReplicationClient;
pub use proto::replication_server::{Replication, ReplicationServer};
// ANCHOR_END: generated

// ANCHOR: convert
impl From<&Record> for proto::Record {
    fn from(record: &Record) -> Self {
        let change = match record.change.clone() {
            Change::Put { key, value } => proto::record::Change::Put(proto::Put { key, value }),
            Change::Delete { key } => proto::record::Change::Delete(proto::Delete { key }),
        };

        proto::Record {
            sequence: record.sequence,
            change: Some(change),
        }
    }
}

impl TryFrom<proto::Record> for Record {
    type Error = Status;

    fn try_from(record: proto::Record) -> Result<Self, Status> {
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
}

impl From<Append> for proto::AppendRequest {
    fn from(message: Append) -> Self {
        proto::AppendRequest {
            shard: 0,
            term: message.term,
            previous_sequence: message.previous_sequence,
            records: message
                .records
                .iter()
                .map(proto::Record::from)
                .collect(),
            committed_sequence: message.committed_sequence,
            // The fields that leader election added are not used by this program.
            previous_term: 0,
            leader: 0,
        }
    }
}

impl From<proto::AppendResponse> for Appended {
    fn from(answer: proto::AppendResponse) -> Self {
        Appended {
            term: answer.term,
            appended: answer.appended,
            last_sequence: answer.last_sequence,
        }
    }
}
// ANCHOR_END: convert

// ANCHOR: service
/// The server side of `Append`, which a follower runs.
pub struct Follower {
    pub node: Arc<Node>,
}

#[tonic::async_trait]
impl Replication for Follower {
    async fn append(
        &self,
        request: Request<proto::AppendRequest>,
    ) -> Result<Response<proto::AppendResponse>, Status> {
        let request = request.into_inner();
        let records = request
            .records
            .into_iter()
            .map(Record::try_from)
            .collect::<Result<Vec<_>, _>>()?;

        let message = Append {
            term: request.term,
            previous_sequence: request.previous_sequence,
            records,
            committed_sequence: request.committed_sequence,
        };

        // Appending waits for the disk, so it runs where blocking is allowed.
        let answer = task::block_in_place(|| {
            self.node
                .replica
                .lock()
                .handle_append(message)
        })
        .map_err(|error| Status::unavailable(error.to_string()))?;

        Ok(Response::new(proto::AppendResponse {
            term: answer.term,
            appended: answer.appended,
            last_sequence: answer.last_sequence,
        }))
    }
}
// ANCHOR_END: service
