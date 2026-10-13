//! Command kvgroup is the storage node of chapter 2 with group commit: one
//! thread writes the log, and it stores every write that is waiting with a
//! single wait for the disk.
//!
//! Run it from code/ with:
//!
//!     cargo run --release -p kvgroup -- --listen 127.0.0.1:7001 --data /var/tmp/kvgroup

// ANCHOR: imports
use std::error::Error;
use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::mpsc::{self, Receiver, Sender};
use std::thread;

use axum::Router;
use axum::body::Bytes;
use axum::extract::{DefaultBodyLimit, Path, State};
use axum::http::header::ETAG;
use axum::http::{HeaderMap, StatusCode};
use axum::response::{IntoResponse, Response};
use axum::routing::put;
use clap::Parser;
use kv::{Change, Store, StoreError, Write, Written};
use kvd::api::{ApiError, MAX_VALUE, etag, valid_key, write_condition};
use tokio::net::TcpListener;
use tokio::sync::oneshot;
// ANCHOR_END: imports

// ANCHOR: options
#[derive(Parser)]
struct Options {
    #[arg(long, default_value = "127.0.0.1:7001")]
    listen: SocketAddr,

    #[arg(long, default_value = "data")]
    data: PathBuf,

    /// The largest number of writes stored with one wait for the disk.
    #[arg(long, default_value_t = 256)]
    batch: usize,
}

/// A write on its way to the committer, with the channel for its result.
struct Request {
    write: Write,
    reply: oneshot::Sender<Result<Written, StoreError>>,
}
// ANCHOR_END: options

// ANCHOR: committer
/// The committer: the one thread that owns the store. It takes the write
/// that has waited longest, adds every write that arrived meanwhile, and
/// stores them together.
fn run_committer(mut store: Store, requests: Receiver<Request>, limit: usize) {
    let (mut batches, mut writes) = (0u64, 0u64);

    while let Ok(first) = requests.recv() {
        // The first request, and whatever else is already waiting.
        let mut batch = vec![first];

        batch.extend(requests.try_iter().take(limit - 1));

        let (changes, replies): (Vec<Write>, Vec<_>) = batch
            .into_iter()
            .map(|request| (request.write, request.reply))
            .unzip();

        batches += 1;
        writes += changes.len() as u64;

        // A handler that has gone away no longer wants its result.
        store
            .commit(changes)
            .into_iter()
            .zip(replies)
            .for_each(|(result, reply)| drop(reply.send(result)));

        if batches.is_multiple_of(200) {
            let average = writes as f64 / batches as f64;
            println!("{writes} writes in {batches} batches, {average:.1} writes per batch");
        }
    }
}
// ANCHOR_END: committer

// ANCHOR: handlers
/// Hands a write to the committer and waits for its result.
async fn submit(committer: &Sender<Request>, write: Write) -> Result<Written, ApiError> {
    let (reply, result) = oneshot::channel();
    let stopped = || ApiError::Unavailable("the committer has stopped".into());

    if committer
        .send(Request { write, reply })
        .is_err()
    {
        return Err(stopped());
    }

    let Ok(outcome) = result.await else {
        return Err(stopped());
    };

    Ok(outcome?)
}

async fn put_key(
    State(committer): State<Sender<Request>>,
    Path(key): Path<String>,
    headers: HeaderMap,
    body: Bytes,
) -> Result<Response, ApiError> {
    valid_key(&key)?;

    let write = Write {
        change: Change::Put {
            key,
            value: body.to_vec(),
        },
        condition: write_condition(&headers)?,
    };

    let written = submit(&committer, write).await?;
    let status = if written.created {
        StatusCode::CREATED
    } else {
        StatusCode::NO_CONTENT
    };

    Ok((status, [(ETAG, etag(written.version))]).into_response())
}

async fn delete_key(
    State(committer): State<Sender<Request>>,
    Path(key): Path<String>,
    headers: HeaderMap,
) -> Result<StatusCode, ApiError> {
    valid_key(&key)?;

    let write = Write {
        change: Change::Delete { key },
        condition: write_condition(&headers)?,
    };

    submit(&committer, write).await?;

    Ok(StatusCode::NO_CONTENT)
}
// ANCHOR_END: handlers

// ANCHOR: main
#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let options = Options::parse();
    let (store, applied, discarded) = Store::open(&options.data, true)?;

    println!("recovered {applied} records, cut {discarded} bytes from the end of the log");

    let (committer, requests) = mpsc::channel();
    thread::spawn(move || run_committer(store, requests, options.batch));

    let routes = Router::new()
        .route("/v1/keys/{key}", put(put_key).delete(delete_key))
        .layer(DefaultBodyLimit::max(MAX_VALUE))
        .with_state(committer);

    let listener = TcpListener::bind(options.listen).await?;
    println!("listening on {}", listener.local_addr()?);

    axum::serve(listener, routes).await?;

    Ok(())
}
// ANCHOR_END: main
