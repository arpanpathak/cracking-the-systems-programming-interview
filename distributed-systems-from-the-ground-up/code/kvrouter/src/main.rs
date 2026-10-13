//! Command kvrouter sends each request to the shard that owns its key, and
//! within that shard to the member that leads. Clients talk to the router
//! and need to know nothing about shards or leaders.
//!
//! Run it from code/ with:
//!
//!     cargo run -p kvrouter -- --listen 127.0.0.1:7000 --ring ring.json

// ANCHOR: imports
use std::collections::HashMap;
use std::error::Error;
use std::fs;
use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::Arc;
use std::sync::atomic::{AtomicUsize, Ordering};
use std::time::Duration;

use axum::body::Bytes;
use axum::extract::{Path, State};
use axum::http::header::{CONTENT_TYPE, ETAG, IF_MATCH, IF_NONE_MATCH};
use axum::http::{HeaderMap, Method, StatusCode};
use axum::response::{IntoResponse, Response};
use axum::routing::get;
use axum::{Json, Router};
use clap::Parser;
use kvd::api::{ApiError, valid_key};
use ring::Ring;
use serde::{Deserialize, Serialize};
use tokio::net::TcpListener;
use tokio::time::sleep;
// ANCHOR_END: imports

// ANCHOR: config
#[derive(Parser)]
struct Options {
    #[arg(long, default_value = "127.0.0.1:7000")]
    listen: SocketAddr,

    /// A JSON file that lists the shards and the addresses of their members.
    #[arg(long)]
    ring: PathBuf,
}

/// The contents of the ring file.
#[derive(Deserialize)]
struct Config {
    virtual_nodes: u32,
    shards: Vec<ShardConfig>,
}

#[derive(Deserialize)]
struct ShardConfig {
    name: String,
    /// The HTTP address of each member, in the order of their ids: member 1 first.
    members: Vec<String>,
}

/// A shard, as the router knows it.
struct Shard {
    members: Vec<String>,
    /// The position in `members` of the member that led when the router last asked.
    leader: AtomicUsize,
}

struct Routes {
    ring: Ring,
    shards: HashMap<String, Shard>,
    client: reqwest::Client,
}
// ANCHOR_END: config

// ANCHOR: load
impl Routes {
    /// Builds the ring from the file: every shard receives its tokens.
    fn load(config: Config) -> Routes {
        let mut ring = Ring::new(config.virtual_nodes);
        let mut shards = HashMap::new();

        for shard in config.shards {
            ring.add(&shard.name);
            shards.insert(
                shard.name,
                Shard {
                    members: shard.members,
                    leader: AtomicUsize::new(0),
                },
            );
        }

        Routes {
            ring,
            shards,
            client: reqwest::Client::new(),
        }
    }

    /// The shard that owns a key.
    fn shard_of(&self, key: &str) -> Option<&Shard> {
        self.shards
            .get(self.ring.owner(key)?)
    }
}
// ANCHOR_END: load

// ANCHOR: attempt
/// What a member said about a request it did not serve.
#[derive(Deserialize)]
struct Problem {
    #[serde(rename = "type")]
    kind: String,
    #[serde(default)]
    detail: String,
}

impl Problem {
    /// The position of the leader in the shard's list of members, when the
    /// member named it, as in "the leader is member 3".
    fn named_leader(&self) -> Option<usize> {
        let id: usize = self
            .detail
            .rsplit(' ')
            .next()?
            .parse()
            .ok()?;

        id.checked_sub(1)
    }
}

/// The result of asking one member.
enum Attempt {
    /// The member served the request. This is its response.
    Served(Response),
    /// The member changed nothing. It may have named the leader.
    Refused(Option<usize>),
    /// The request may or may not have taken effect.
    Unknown(String),
}
// ANCHOR_END: attempt

// ANCHOR: ask
const NO_LEADER: &str = "/problems/no-leader";

impl Routes {
    /// Sends the request to one member and classifies what comes back.
    async fn ask(
        &self,
        member: &str,
        method: Method,
        key: &str,
        headers: &HeaderMap,
        body: Bytes,
    ) -> Attempt {
        let conditions = [IF_MATCH, IF_NONE_MATCH]
            .into_iter()
            .filter_map(|name| {
                headers
                    .get(&name)
                    .map(|value| (name, value))
            });
        let request = self
            .client
            .request(method, format!("{member}/v1/keys/{key}"))
            .body(body);
        let request = conditions.fold(request, |request, (name, value)| {
            request.header(name, value)
        });

        let response = match request.send().await {
            Ok(response) => response,
            Err(error) if error.is_connect() => return Attempt::Refused(None),
            Err(error) => return Attempt::Unknown(error.to_string()),
        };

        let status = response.status();
        let redirected = status == StatusCode::MISDIRECTED_REQUEST;

        if !redirected && status != StatusCode::SERVICE_UNAVAILABLE {
            return Attempt::Served(relay(response).await);
        }

        match response.json::<Problem>().await {
            Ok(problem) if redirected || problem.kind == NO_LEADER => {
                Attempt::Refused(problem.named_leader())
            }
            Ok(problem) => Attempt::Unknown(problem.detail),
            Err(error) => Attempt::Unknown(error.to_string()),
        }
    }
}

/// Passes a member's response on to the client: status, version and body.
async fn relay(response: reqwest::Response) -> Response {
    let status = response.status();
    let headers: HeaderMap = [ETAG, CONTENT_TYPE]
        .into_iter()
        .filter_map(|name| {
            response
                .headers()
                .get(&name)
                .map(|value| (name, value.clone()))
        })
        .collect();

    match response.bytes().await {
        Ok(body) => (status, headers, body).into_response(),
        Err(error) => ApiError::Unavailable(error.to_string()).into_response(),
    }
}
// ANCHOR_END: ask

// ANCHOR: forward
/// How many times the router asks a member before it gives up.
const ATTEMPTS: usize = 12;

/// How long the router waits before it asks again, once every member of a
/// shard has refused.
const PAUSE: Duration = Duration::from_millis(150);

impl Routes {
    /// Sends a request to the leader of the key's shard. A member that
    /// refuses has changed nothing, so the router asks another.
    async fn forward(
        &self,
        method: Method,
        key: &str,
        headers: &HeaderMap,
        body: Bytes,
    ) -> Result<Response, ApiError> {
        valid_key(key)?;

        let shard = self
            .shard_of(key)
            .ok_or(ApiError::NoLeader)?;

        for attempt in 1..=ATTEMPTS {
            let tried = shard.leader.load(Ordering::Relaxed);
            let member = &shard.members[tried];

            let named = match self
                .ask(member, method.clone(), key, headers, body.clone())
                .await
            {
                Attempt::Served(response) => return Ok(response),
                Attempt::Unknown(detail) => return Err(ApiError::Unavailable(detail)),
                Attempt::Refused(named) => named,
            };

            let next = named
                .filter(|&position| position < shard.members.len())
                .unwrap_or((tried + 1) % shard.members.len());

            shard
                .leader
                .store(next, Ordering::Relaxed);

            // Every member has refused once: the shard is electing a leader.
            if attempt >= shard.members.len() {
                sleep(PAUSE).await;
            }
        }

        Err(ApiError::NoLeader)
    }
}
// ANCHOR_END: forward

// ANCHOR: handlers
async fn key(
    State(routes): State<Arc<Routes>>,
    method: Method,
    Path(key): Path<String>,
    headers: HeaderMap,
    body: Bytes,
) -> Result<Response, ApiError> {
    routes
        .forward(method, &key, &headers, body)
        .await
}

#[derive(Serialize)]
struct ShardHealth<'a> {
    name: &'a str,
    /// The address the router currently sends this shard's requests to.
    leader: &'a str,
}

async fn health(State(routes): State<Arc<Routes>>) -> Json<serde_json::Value> {
    let mut shards: Vec<ShardHealth> = routes
        .shards
        .iter()
        .map(|(name, shard)| ShardHealth {
            name,
            leader: &shard.members[shard.leader.load(Ordering::Relaxed)],
        })
        .collect();
    shards.sort_by_key(|shard| shard.name);

    Json(serde_json::json!({ "status": "ok", "shards": shards }))
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let options = Options::parse();
    let config: Config = serde_json::from_str(&fs::read_to_string(&options.ring)?)?;
    let routes = Arc::new(Routes::load(config));

    println!("routing to {} shards", routes.shards.len());

    let app = Router::new()
        .route("/v1/keys/{key}", get(key).put(key).delete(key))
        .route("/healthz", get(health))
        .with_state(routes);

    let listener = TcpListener::bind(options.listen).await?;
    println!("listening on {}", listener.local_addr()?);

    axum::serve(listener, app).await?;

    Ok(())
}
// ANCHOR_END: handlers
