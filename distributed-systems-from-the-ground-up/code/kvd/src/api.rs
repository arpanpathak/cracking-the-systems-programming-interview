//! The parts of the HTTP API that do not depend on how a node stores its
//! data: the errors and their responses, and the reading of keys and
//! conditional headers.

// ANCHOR: imports
use axum::Json;
use axum::http::header::{CONTENT_TYPE, IF_MATCH, IF_NONE_MATCH};
use axum::http::{HeaderMap, HeaderName, StatusCode};
use axum::response::{IntoResponse, Response};
use kv::{Condition, StoreError};
use serde::Serialize;
// ANCHOR_END: imports

/// The largest value a key may hold.
pub const MAX_VALUE: usize = 1 << 20;

pub const MAX_KEY: usize = 256;

// ANCHOR: errors
/// The ways a request can fail. Each one is a status code and a sentence.
pub enum ApiError {
    InvalidKey,
    InvalidHeader(HeaderName),
    NotFound,
    ConditionFailed(Option<u64>),
    Unavailable(String),
    /// The request reached a node that does not serve it. The text names the reason.
    Misdirected(String),
    /// The shard has no leader at the moment. Nothing was changed.
    NoLeader,
}

/// The body of an error response, in the format of RFC 9457.
#[derive(Serialize)]
struct Problem {
    #[serde(rename = "type")]
    kind: &'static str,
    title: &'static str,
    status: u16,
    #[serde(skip_serializing_if = "String::is_empty")]
    detail: String,
}

impl IntoResponse for ApiError {
    fn into_response(self) -> Response {
        let (status, kind, title, detail) = match self {
            ApiError::InvalidKey => (
                StatusCode::BAD_REQUEST,
                "/problems/invalid-key",
                "The key is not valid",
                format!("a key is 1 to {MAX_KEY} characters from A-Z, a-z, 0-9, '.', '_' and '-'"),
            ),
            ApiError::InvalidHeader(name) => (
                StatusCode::BAD_REQUEST,
                "/problems/invalid-header",
                "A request header is not valid",
                format!("{name} must be a version in double quotes, or * where that is allowed"),
            ),
            ApiError::NotFound => (
                StatusCode::NOT_FOUND,
                "/problems/key-not-found",
                "The key does not exist",
                String::new(),
            ),
            ApiError::ConditionFailed(current) => (
                StatusCode::PRECONDITION_FAILED,
                "/problems/condition-failed",
                "The condition on the key's version does not hold",
                current.map_or("the key does not exist".into(), |version| {
                    format!("the key is at version {version}")
                }),
            ),
            ApiError::Misdirected(detail) => (
                StatusCode::MISDIRECTED_REQUEST,
                "/problems/not-leader",
                "This node is not the leader",
                detail,
            ),
            ApiError::NoLeader => (
                StatusCode::SERVICE_UNAVAILABLE,
                "/problems/no-leader",
                "The shard has no leader at the moment",
                String::new(),
            ),
            ApiError::Unavailable(detail) => (
                StatusCode::SERVICE_UNAVAILABLE,
                "/problems/store-unavailable",
                "The node cannot serve the request",
                detail,
            ),
        };

        let problem = Problem {
            kind,
            title,
            status: status.as_u16(),
            detail,
        };

        (
            status,
            [(CONTENT_TYPE, "application/problem+json")],
            Json(problem),
        )
            .into_response()
    }
}

impl From<StoreError> for ApiError {
    fn from(error: StoreError) -> Self {
        match error {
            StoreError::NotFound => ApiError::NotFound,
            StoreError::ConditionFailed { current } => ApiError::ConditionFailed(current),
            StoreError::Log(error) => ApiError::Unavailable(error.to_string()),
        }
    }
}
// ANCHOR_END: errors

// ANCHOR: headers
/// A version as it appears in `ETag`, `If-Match` and `If-None-Match`.
pub fn etag(version: u64) -> String {
    format!("\"{version}\"")
}

pub fn valid_key(key: &str) -> Result<(), ApiError> {
    let allowed = |c: char| c.is_ascii_alphanumeric() || matches!(c, '.' | '_' | '-');

    let valid = (1..=MAX_KEY).contains(&key.len()) && key.chars().all(allowed);

    valid
        .then_some(())
        .ok_or(ApiError::InvalidKey)
}

/// Reads a header that holds a quoted version or `*`.
pub fn version_header(
    headers: &HeaderMap,
    name: HeaderName,
) -> Result<Option<Condition>, ApiError> {
    let Some(value) = headers.get(&name) else {
        return Ok(None);
    };

    let Ok(text) = value.to_str() else {
        return Err(ApiError::InvalidHeader(name));
    };

    if text == "*" {
        return Ok(Some(Condition::Absent));
    }

    let version = text
        .strip_prefix("\"")
        .and_then(|rest| rest.strip_suffix("\""))
        .and_then(|digits| digits.parse().ok());

    version
        .map(Condition::Version)
        .map(Some)
        .ok_or(ApiError::InvalidHeader(name))
}

/// The condition a write carries: `If-Match: "7"` requires version 7, and
/// `If-None-Match: *` requires that the key does not exist.
pub fn write_condition(headers: &HeaderMap) -> Result<Condition, ApiError> {
    match (
        version_header(headers, IF_MATCH)?,
        version_header(headers, IF_NONE_MATCH)?,
    ) {
        (Some(Condition::Version(version)), None) => Ok(Condition::Version(version)),
        (None, Some(Condition::Absent)) => Ok(Condition::Absent),
        (None, None) => Ok(Condition::Always),
        (Some(..), ..) => Err(ApiError::InvalidHeader(IF_MATCH)),
        (None, Some(..)) => Err(ApiError::InvalidHeader(IF_NONE_MATCH)),
    }
}
// ANCHOR_END: headers
