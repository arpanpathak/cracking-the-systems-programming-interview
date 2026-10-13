//! Command kvraft is a storage node whose shard elects its own leader.
//! Every node is started the same way, with its id and the replication
//! addresses of the other members.
//!
//! Run 3 nodes from code/ with:
//!
//!     cargo run -p kvraft -- --id 1 --listen 127.0.0.1:7001 --replication 127.0.0.1:7101 --data /var/tmp/m1 \
//!         --peer 2=http://127.0.0.1:7102 --peer 3=http://127.0.0.1:7103
//!
//! and the same for ids 2 and 3, each with its own ports and the other 2 as peers.

mod node;
mod rpc;

// ANCHOR: imports
use std::collections::BTreeMap;
use std::error::Error;
use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::Arc;

use axum::body::Bytes;
use axum::extract::{DefaultBodyLimit, Path, State};
use axum::http::header::{CONTENT_TYPE, ETAG, IF_NONE_MATCH};
use axum::http::{HeaderMap, StatusCode};
use axum::response::{IntoResponse, Response};
use axum::routing::get;
use axum::{Json, Router};
use clap::Parser;
use kv::{Change, Condition};
use kvd::api::{ApiError, MAX_VALUE, etag, valid_key, version_header, write_condition};
use raft::{Member, NodeId, Role};
use serde::Serialize;
use tokio::net::TcpListener;
use tonic::transport::Server;

use crate::node::Node;
use crate::rpc::{ElectionServer, ReplicationServer, Service};
// ANCHOR_END: imports

// ANCHOR: options
/// Reads `2=http://127.0.0.1:7102` as member 2 at that address.
fn parse_peer(text: &str) -> Result<(NodeId, String), String> {
    let (id, address) = text
        .split_once('=')
        .ok_or("a peer is written as id=address")?;
    let Ok(id) = id.parse() else {
        return Err("the id of a peer is a number".to_owned());
    };

    Ok((id, address.to_owned()))
}

#[derive(Parser)]
struct Options {
    /// The id of this member, a number that no other member has.
    #[arg(long)]
    id: NodeId,

    /// The address of the HTTP API.
    #[arg(long, default_value = "127.0.0.1:7001")]
    listen: SocketAddr,

    /// The address on which this member accepts messages from the others.
    #[arg(long, default_value = "127.0.0.1:7101")]
    replication: SocketAddr,

    /// Another member and its replication address, as id=address.
    #[arg(long = "peer", value_parser = parse_peer)]
    peers: Vec<(NodeId, String)>,

    #[arg(long, default_value = "data")]
    data: PathBuf,

    /// Respond without waiting for the disk.
    #[arg(long)]
    no_sync: bool,
}
// ANCHOR_END: options

// ANCHOR: handlers
async fn put_key(
    State(node): State<Arc<Node>>,
    Path(key): Path<String>,
    headers: HeaderMap,
    body: Bytes,
) -> Result<Response, ApiError> {
    valid_key(&key)?;
    let condition = write_condition(&headers)?;

    let written = node
        .write(
            Change::Put {
                key,
                value: body.to_vec(),
            },
            condition,
        )
        .await?;
    let status = if written.created {
        StatusCode::CREATED
    } else {
        StatusCode::NO_CONTENT
    };

    Ok((status, [(ETAG, etag(written.version))]).into_response())
}

async fn delete_key(
    State(node): State<Arc<Node>>,
    Path(key): Path<String>,
    headers: HeaderMap,
) -> Result<StatusCode, ApiError> {
    valid_key(&key)?;
    let condition = write_condition(&headers)?;

    node.write(Change::Delete { key }, condition)
        .await?;

    Ok(StatusCode::NO_CONTENT)
}

async fn get_key(
    State(node): State<Arc<Node>>,
    Path(key): Path<String>,
    headers: HeaderMap,
) -> Result<Response, ApiError> {
    valid_key(&key)?;
    let cached = version_header(&headers, IF_NONE_MATCH)?;
    let entry = node.get(&key)?;
    let tag = [(ETAG, etag(entry.version))];

    if cached == Some(Condition::Version(entry.version)) {
        return Ok((StatusCode::NOT_MODIFIED, tag).into_response());
    }

    Ok((
        tag,
        [(CONTENT_TYPE, "application/octet-stream")],
        entry.value,
    )
        .into_response())
}

#[derive(Serialize)]
struct Health {
    id: NodeId,
    role: &'static str,
    term: u64,
    /// The leader of the term, when this member knows it.
    leader: Option<NodeId>,
    last_sequence: u64,
    committed: u64,
}

async fn health(State(node): State<Arc<Node>>) -> Json<Health> {
    let member = node.member.lock();

    let role = match member.role() {
        Role::Leader => "leader",
        Role::Candidate => "candidate",
        Role::Follower => "follower",
    };

    Json(Health {
        id: member.id(),
        role,
        term: member.term(),
        leader: member.leader(),
        last_sequence: member.last_sequence(),
        committed: member.committed(),
    })
}
// ANCHOR_END: handlers

// ANCHOR: main
#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let options = Options::parse();
    let peers: BTreeMap<NodeId, String> = options.peers.into_iter().collect();
    let member = Member::open(
        &options.data,
        options.id,
        peers.keys().copied().collect(),
        !options.no_sync,
    )?;

    println!(
        "member {}, term {}, log ends at {}",
        member.id(),
        member.term(),
        member.last_sequence()
    );

    let node = Node::new(member, peers)?;

    let replication = ReplicationServer::new(Service {
        node: Arc::clone(&node),
    });
    let election = ElectionServer::new(Service {
        node: Arc::clone(&node),
    });

    tokio::spawn(
        Server::builder()
            .add_service(replication)
            .add_service(election)
            .serve(options.replication),
    );
    tokio::spawn(Arc::clone(&node).run_clock());

    let routes = Router::new()
        .route(
            "/v1/keys/{key}",
            get(get_key)
                .put(put_key)
                .delete(delete_key),
        )
        .route("/healthz", get(health))
        .layer(DefaultBodyLimit::max(MAX_VALUE))
        .with_state(node);

    let listener = TcpListener::bind(options.listen).await?;
    println!("listening on {}", listener.local_addr()?);

    axum::serve(listener, routes).await?;

    Ok(())
}
// ANCHOR_END: main
