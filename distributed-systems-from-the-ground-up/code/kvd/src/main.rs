//! Command kvd serves a key-value store over HTTP. Every write is in the log
//! on disk before the response is sent.
//!
//! Run it from code/ with:
//!
//!     cargo run -p kvd -- --listen 0.0.0.0:7001 --data /var/tmp/kvd

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
use clap::Parser;
use kv::{Condition, Store, StoreError, Summary};
use kvd::api::{ApiError, MAX_VALUE, etag, valid_key, version_header, write_condition};
use parking_lot::Mutex;
use serde::{Deserialize, Serialize};
use tokio::net::TcpListener;
use tokio::task;
// ANCHOR_END: imports

// ANCHOR: options
#[derive(Parser)]
struct Options {
    /// The address to accept connections on.
    #[arg(long, default_value = "127.0.0.1:7001")]
    listen: SocketAddr,

    /// The directory that holds the log.
    #[arg(long, default_value = "data")]
    data: PathBuf,

    /// Respond to a write without waiting for the disk.
    #[arg(long)]
    no_sync: bool,
}

/// The store, shared by every request.
type Shared = Arc<Mutex<Store>>;

// ANCHOR_END: options

// ANCHOR: blocking
/// Runs a write on a thread that may block. A write waits for the disk, and
/// a thread that waits must not be one of the threads that serve requests.
async fn write<T, F>(store: Shared, work: F) -> Result<T, ApiError>
where
    F: FnOnce(&mut Store) -> Result<T, StoreError> + Send + 'static,
    T: Send + 'static,
{
    let result = task::spawn_blocking(move || work(&mut store.lock()))
        .await
        .map_err(|error| ApiError::Unavailable(error.to_string()))?;

    Ok(result?)
}
// ANCHOR_END: blocking

// ANCHOR: put
async fn put_key(
    State(store): State<Shared>,
    Path(key): Path<String>,
    headers: HeaderMap,
    body: Bytes,
) -> Result<Response, ApiError> {
    valid_key(&key)?;
    let condition = write_condition(&headers)?;

    let written = write(store, move |store| store.put(key, body.to_vec(), condition)).await?;
    let status = if written.created {
        StatusCode::CREATED
    } else {
        StatusCode::NO_CONTENT
    };

    Ok((status, [(ETAG, etag(written.version))]).into_response())
}

async fn delete_key(
    State(store): State<Shared>,
    Path(key): Path<String>,
    headers: HeaderMap,
) -> Result<StatusCode, ApiError> {
    valid_key(&key)?;
    let condition = write_condition(&headers)?;

    write(store, move |store| store.delete(&key, condition)).await?;

    Ok(StatusCode::NO_CONTENT)
}
// ANCHOR_END: put

// ANCHOR: get
async fn get_key(
    State(store): State<Shared>,
    Path(key): Path<String>,
    headers: HeaderMap,
) -> Result<Response, ApiError> {
    valid_key(&key)?;
    let cached = version_header(&headers, IF_NONE_MATCH)?;
    let entry = store
        .lock()
        .get(&key)
        .cloned()
        .ok_or(ApiError::NotFound)?;
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
// ANCHOR_END: get

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
    /// The value of `after` that returns the next page, when there is one.
    next_after: Option<String>,
}

async fn list_keys(State(store): State<Shared>, Query(query): Query<ListQuery>) -> Json<Page> {
    let limit = query
        .limit
        .unwrap_or(100)
        .clamp(1, 1000);
    let (page, more) = store
        .lock()
        .list(&query.prefix, query.after.as_deref(), limit);
    let next_after = page
        .last()
        .filter(|_last| more)
        .map(|last| last.key.clone());
    let keys = page
        .into_iter()
        .map(|Summary { key, version, size }| Item { key, version, size })
        .collect();

    Json(Page { keys, next_after })
}

#[derive(Serialize)]
struct Health {
    status: &'static str,
    keys: usize,
    last_sequence: u64,
}

async fn health(State(store): State<Shared>) -> Json<Health> {
    let store = store.lock();

    Json(Health {
        status: "ok",
        keys: store.len(),
        last_sequence: store.last_sequence(),
    })
}
// ANCHOR_END: list

// ANCHOR: main
#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let options = Options::parse();
    let (store, applied, discarded) = Store::open(&options.data, !options.no_sync)?;

    println!(
        "recovered {} keys from {applied} records, cut {discarded} bytes from the end of the log",
        store.len()
    );

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
        .with_state(Arc::new(Mutex::new(store)));

    let listener = TcpListener::bind(options.listen).await?;
    println!("listening on {}", listener.local_addr()?);

    axum::serve(listener, routes).await?;

    Ok(())
}
// ANCHOR_END: main
