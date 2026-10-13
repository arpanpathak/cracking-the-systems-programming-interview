//! Command kvnode is a storage node that replicates its log. One node of a
//! shard is started as the leader, with the addresses of its followers, and
//! the others as followers. The leader serves the HTTP API and acknowledges
//! a write when a majority of the nodes hold its record.
//!
//! Run 3 nodes from code/ with:
//!
//!     cargo run -p kvnode -- --role follower --listen 127.0.0.1:7002 --replication 127.0.0.1:7102 --data /var/tmp/n2
//!     cargo run -p kvnode -- --role follower --listen 127.0.0.1:7003 --replication 127.0.0.1:7103 --data /var/tmp/n3
//!     cargo run -p kvnode -- --role leader --listen 127.0.0.1:7001 --data /var/tmp/n1 \
//!         --follower http://127.0.0.1:7102 --follower http://127.0.0.1:7103

mod node;
mod rpc;

// ANCHOR: imports
use std::error::Error;
use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::Arc;

use axum::body::Bytes;
use axum::extract::{DefaultBodyLimit, Path, Query, State};
use axum::http::header::{CONTENT_TYPE, ETAG, IF_NONE_MATCH};
use axum::http::{HeaderMap, StatusCode};
use axum::response::{IntoResponse, Response};
use axum::routing::get;
use axum::{Json, Router};
use clap::{Parser, ValueEnum};
use kv::{Change, Condition};
use kvd::api::{ApiError, MAX_VALUE, etag, valid_key, version_header, write_condition};
use repl::Replica;
use serde::{Deserialize, Serialize};
use tokio::net::TcpListener;
use tonic::transport::Server;

use crate::node::Node;
use crate::rpc::{Follower, ReplicationServer};
// ANCHOR_END: imports

// ANCHOR: options
#[derive(Clone, Copy, PartialEq, Eq, ValueEnum)]
enum Role {
    Leader,
    Follower,
}

#[derive(Parser)]
struct Options {
    #[arg(long, value_enum)]
    role: Role,

    /// The address of the HTTP API.
    #[arg(long, default_value = "127.0.0.1:7001")]
    listen: SocketAddr,

    /// The address on which a follower accepts records from the leader.
    #[arg(long, default_value = "127.0.0.1:7101")]
    replication: SocketAddr,

    /// The replication address of a follower, such as http://127.0.0.1:7102.
    /// Given once for each follower, to the leader.
    #[arg(long = "follower")]
    followers: Vec<String>,

    /// The term this node starts in. A new leader is given a higher term
    /// than the leader it replaces.
    #[arg(long, default_value_t = 1)]
    term: u64,

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
// ANCHOR_END: handlers

// ANCHOR: list
#[derive(Deserialize)]
struct ListQuery {
    #[serde(default)]
    prefix: String,
    after: Option<String>,
    limit: Option<usize>,
}

#[derive(Serialize)]
struct Item {
    key: String,
    version: u64,
    size: usize,
}

#[derive(Serialize)]
struct Page {
    keys: Vec<Item>,
    next_after: Option<String>,
}

async fn list_keys(
    State(node): State<Arc<Node>>,
    Query(query): Query<ListQuery>,
) -> Result<Json<Page>, ApiError> {
    let limit = query
        .limit
        .unwrap_or(100)
        .clamp(1, 1000);
    let (page, more) = node.list(&query.prefix, query.after.as_deref(), limit)?;
    let next_after = if more {
        page.last()
            .map(|last| last.key.clone())
    } else {
        None
    };
    let keys = page
        .into_iter()
        .map(|item| Item {
            key: item.key,
            version: item.version,
            size: item.size,
        })
        .collect();

    Ok(Json(Page { keys, next_after }))
}

#[derive(Serialize)]
struct Health {
    role: &'static str,
    term: u64,
    last_sequence: u64,
    committed: u64,
    /// The last sequence each follower has reported to this leader.
    followers: Vec<u64>,
}

async fn health(State(node): State<Arc<Node>>) -> Json<Health> {
    let replica = node.replica.lock();

    Json(Health {
        role: if node.leader { "leader" } else { "follower" },
        term: replica.term(),
        last_sequence: replica.last_sequence(),
        committed: replica.committed(),
        followers: node.reported(),
    })
}
// ANCHOR_END: list

// ANCHOR: main
#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let options = Options::parse();
    let replica = Replica::open(&options.data, !options.no_sync, options.term)?;

    println!(
        "term {}, log ends at {}",
        replica.term(),
        replica.last_sequence()
    );

    let node = Node::new(replica, options.role == Role::Leader, options.followers);

    match options.role {
        Role::Leader => node.lead()?,
        Role::Follower => {
            let service = ReplicationServer::new(Follower {
                node: Arc::clone(&node),
            });

            tokio::spawn(
                Server::builder()
                    .add_service(service)
                    .serve(options.replication),
            );
            println!("accepting records on {}", options.replication);
        }
    }

    let routes = Router::new()
        .route("/v1/keys", get(list_keys))
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
