//! HTTP/1.1 request parsing: request line, headers, and body framing.
//!
//! The framing checks are the point. `Content-Length` together with
//! `Transfer-Encoding` is rejected as ambiguous (request smuggling), as are
//! obsolete line folding and a missing `Host`. Header and body sizes are bounded
//! so a slow client cannot hold a connection open.

use std::fmt;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum Method {
    Get,
    Head,
    Post,
    Put,
    Patch,
    Delete,
    Options,
}

impl Method {
    pub fn parse(token: &str) -> Option<Self> {
        Some(match token {
            "GET" => Self::Get,
            "HEAD" => Self::Head,
            "POST" => Self::Post,
            "PUT" => Self::Put,
            "PATCH" => Self::Patch,
            "DELETE" => Self::Delete,
            "OPTIONS" => Self::Options,
            _ => return None,
        })
    }

    pub fn is_safe(self) -> bool {
        matches!(self, Self::Get | Self::Head | Self::Options)
    }

    pub fn is_idempotent(self) -> bool {
        matches!(
            self,
            Self::Get | Self::Head | Self::Options | Self::Put | Self::Delete
        )
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Version {
    Http10,
    Http11,
}

#[derive(Debug, Clone, Copy)]
pub struct Limits {
    pub max_header_bytes: usize,
    pub max_body_bytes: usize,
}

impl Default for Limits {
    fn default() -> Self {
        Self {
            max_header_bytes: 16 * 1024,
            max_body_bytes: 8 * 1024 * 1024,
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Request {
    pub method: Method,
    pub target: String,
    pub version: Version,
    pub headers: Vec<(String, String)>,
    pub body: Vec<u8>,
}

impl Request {
    /// First header value matching `name`, case-insensitively.
    pub fn header(&self, name: &str) -> Option<&str> {
        self.headers
            .iter()
            .find(|(key, _)| key.eq_ignore_ascii_case(name))
            .map(|(_, value)| value.as_str())
    }

    /// HTTP/1.1 reuses the connection unless `Connection: close`; HTTP/1.0 only
    /// reuses it with `Connection: keep-alive`.
    pub fn should_keep_alive(&self) -> bool {
        let connection = self.header("connection").unwrap_or("");
        let has = |token: &str| {
            connection
                .split(',')
                .any(|part| part.trim().eq_ignore_ascii_case(token))
        };
        match self.version {
            Version::Http11 => !has("close"),
            Version::Http10 => has("keep-alive"),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ParseError {
    /// Not a complete request yet; read more and retry.
    Incomplete,
    Malformed(&'static str),
    MissingHost,
    /// `Content-Length` and `Transfer-Encoding` were both present.
    AmbiguousBodyLength,
    UnsupportedTransferEncoding,
    PayloadTooLarge,
}

impl fmt::Display for ParseError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            Self::Incomplete => write!(f, "incomplete request"),
            Self::Malformed(reason) => write!(f, "malformed request: {reason}"),
            Self::MissingHost => write!(f, "HTTP/1.1 requires exactly one Host header"),
            Self::AmbiguousBodyLength => {
                write!(
                    f,
                    "Content-Length and Transfer-Encoding are mutually exclusive"
                )
            }
            Self::UnsupportedTransferEncoding => write!(f, "unsupported Transfer-Encoding"),
            Self::PayloadTooLarge => write!(f, "request exceeds configured limits"),
        }
    }
}

impl std::error::Error for ParseError {}

/// Parse one request from the start of `input`.
pub fn parse_request(input: &[u8], limits: Limits) -> Result<Request, ParseError> {
    let Some(header_end) = input.windows(4).position(|window| window == b"\r\n\r\n") else {
        return Err(if input.len() > limits.max_header_bytes {
            ParseError::PayloadTooLarge
        } else {
            ParseError::Incomplete
        });
    };
    if header_end + 4 > limits.max_header_bytes {
        return Err(ParseError::PayloadTooLarge);
    }

    let head = &input[..header_end];
    let body_start = header_end + 4;

    let mut lines = head
        .split(|byte| *byte == b'\n')
        .map(|line| line.strip_suffix(b"\r").unwrap_or(line));

    let request_line = std::str::from_utf8(lines.next().ok_or(ParseError::Malformed("empty"))?)
        .map_err(|_| ParseError::Malformed("request line"))?;
    let mut parts = request_line.split(' ');
    let method = Method::parse(parts.next().ok_or(ParseError::Malformed("method"))?)
        .ok_or(ParseError::Malformed("unknown method"))?;
    let target = parts.next().ok_or(ParseError::Malformed("target"))?;
    let version = match parts.next() {
        Some("HTTP/1.1") => Version::Http11,
        Some("HTTP/1.0") => Version::Http10,
        _ => return Err(ParseError::Malformed("version")),
    };
    if parts.next().is_some() || target.is_empty() {
        return Err(ParseError::Malformed("request line"));
    }

    let mut headers = Vec::new();
    for line in lines {
        if line.is_empty() {
            continue;
        }
        if matches!(line.first(), Some(b' ') | Some(b'\t')) {
            return Err(ParseError::Malformed("obsolete line folding"));
        }
        let colon = line
            .iter()
            .position(|byte| *byte == b':')
            .ok_or(ParseError::Malformed("header without colon"))?;
        let name = std::str::from_utf8(&line[..colon])
            .map_err(|_| ParseError::Malformed("header name"))?;
        if name.is_empty() || name.bytes().any(|byte| byte.is_ascii_whitespace()) {
            return Err(ParseError::Malformed("invalid header name"));
        }
        let value = std::str::from_utf8(&line[colon + 1..])
            .map_err(|_| ParseError::Malformed("header value"))?;
        headers.push((name.to_string(), value.trim().to_string()));
    }

    if version == Version::Http11
        && headers
            .iter()
            .filter(|(name, _)| name.eq_ignore_ascii_case("host"))
            .count()
            != 1
    {
        return Err(ParseError::MissingHost);
    }

    let body = parse_body(input, body_start, &headers, limits)?;

    Ok(Request {
        method,
        target: target.to_string(),
        version,
        headers,
        body,
    })
}

fn parse_body(
    input: &[u8],
    body_start: usize,
    headers: &[(String, String)],
    limits: Limits,
) -> Result<Vec<u8>, ParseError> {
    let collect = |name: &str| -> Vec<&str> {
        headers
            .iter()
            .filter(|(key, _)| key.eq_ignore_ascii_case(name))
            .map(|(_, value)| value.as_str())
            .collect()
    };
    let transfer_encoding = collect("transfer-encoding");
    let content_length = collect("content-length");

    // Two framing headers is the classic request-smuggling setup.
    if !transfer_encoding.is_empty() && !content_length.is_empty() {
        return Err(ParseError::AmbiguousBodyLength);
    }

    if !transfer_encoding.is_empty() {
        let joined = transfer_encoding.join(",");
        let codings: Vec<&str> = joined
            .split(',')
            .map(str::trim)
            .filter(|token| !token.is_empty())
            .collect();
        let all_chunked = codings
            .iter()
            .all(|token| token.eq_ignore_ascii_case("chunked"));
        if !all_chunked
            || !codings
                .last()
                .is_some_and(|t| t.eq_ignore_ascii_case("chunked"))
        {
            return Err(ParseError::UnsupportedTransferEncoding);
        }
        return decode_chunked(&input[body_start..], limits.max_body_bytes);
    }

    if content_length.is_empty() {
        return Ok(Vec::new());
    }

    let mut lengths = content_length.iter().map(|value| {
        value
            .trim()
            .parse::<usize>()
            .map_err(|_| ParseError::Malformed("invalid Content-Length"))
    });
    let first = lengths.next().expect("non-empty")?;
    if lengths.any(|length| length != Ok(first)) {
        return Err(ParseError::Malformed("conflicting Content-Length"));
    }
    if first > limits.max_body_bytes {
        return Err(ParseError::PayloadTooLarge);
    }
    let end = body_start + first;
    if input.len() < end {
        return Err(ParseError::Incomplete);
    }
    Ok(input[body_start..end].to_vec())
}

fn decode_chunked(data: &[u8], max_body: usize) -> Result<Vec<u8>, ParseError> {
    let mut cursor = 0;
    let mut body = Vec::new();

    loop {
        let line_end = find_crlf(data, cursor).ok_or(ParseError::Incomplete)?;
        let size_token = data[cursor..line_end]
            .split(|byte| *byte == b';')
            .next()
            .unwrap_or(&[]);
        let size = usize::from_str_radix(
            std::str::from_utf8(size_token)
                .map_err(|_| ParseError::Malformed("chunk size"))?
                .trim(),
            16,
        )
        .map_err(|_| ParseError::Malformed("chunk size"))?;
        cursor = line_end + 2;

        if size == 0 {
            // Consume trailers up to the final empty line.
            loop {
                let trailer_end = find_crlf(data, cursor).ok_or(ParseError::Incomplete)?;
                let is_empty = trailer_end == cursor;
                cursor = trailer_end + 2;
                if is_empty {
                    return Ok(body);
                }
            }
        }

        if body.len() + size > max_body {
            return Err(ParseError::PayloadTooLarge);
        }
        let chunk_end = cursor
            .checked_add(size)
            .ok_or(ParseError::Malformed("chunk overflow"))?;
        if chunk_end + 2 > data.len() {
            return Err(ParseError::Incomplete);
        }
        body.extend_from_slice(&data[cursor..chunk_end]);
        if &data[chunk_end..chunk_end + 2] != b"\r\n" {
            return Err(ParseError::Malformed("chunk not CRLF-terminated"));
        }
        cursor = chunk_end + 2;
    }
}

fn find_crlf(data: &[u8], from: usize) -> Option<usize> {
    data.get(from..)?
        .windows(2)
        .position(|window| window == b"\r\n")
        .map(|offset| offset + from)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn parse(raw: &[u8]) -> Result<Request, ParseError> {
        parse_request(raw, Limits::default())
    }

    #[test]
    fn parses_a_get_and_a_post_with_content_length() {
        let get = parse(b"GET /v1/gpu-workloads HTTP/1.1\r\nHost: api\r\nAccept: */*\r\n\r\n")
            .expect("valid");
        assert_eq!(get.method, Method::Get);
        assert_eq!(get.header("HOST"), Some("api"));
        assert!(get.body.is_empty());
        assert!(get.should_keep_alive());

        let post = parse(b"POST / HTTP/1.1\r\nHost: api\r\nContent-Length: 5\r\n\r\nhello")
            .expect("valid");
        assert_eq!(post.body, b"hello");
        assert!(!post.method.is_idempotent());
    }

    #[test]
    fn decodes_chunked_bodies() {
        let raw = b"POST /u HTTP/1.1\r\nHost: api\r\nTransfer-Encoding: chunked\r\n\r\n5\r\nhello\r\n6\r\n world\r\n0\r\n\r\n";
        assert_eq!(parse(raw).expect("valid").body, b"hello world");
    }

    #[test]
    fn rejects_ambiguous_framing_and_bad_framing() {
        let smuggling = b"POST / HTTP/1.1\r\nHost: api\r\nContent-Length: 5\r\nTransfer-Encoding: chunked\r\n\r\nhello";
        assert_eq!(parse(smuggling), Err(ParseError::AmbiguousBodyLength));

        let gzip = b"POST / HTTP/1.1\r\nHost: api\r\nTransfer-Encoding: gzip\r\n\r\n";
        assert_eq!(parse(gzip), Err(ParseError::UnsupportedTransferEncoding));
    }

    #[test]
    fn rejects_missing_host_and_line_folding() {
        assert_eq!(
            parse(b"GET / HTTP/1.1\r\nAccept: */*\r\n\r\n"),
            Err(ParseError::MissingHost)
        );
        let folded = b"GET / HTTP/1.1\r\nHost: api\r\nX-A: 1\r\n continued\r\n\r\n";
        assert!(matches!(parse(folded), Err(ParseError::Malformed(_))));
    }

    #[test]
    fn reports_incomplete_and_enforces_limits() {
        assert_eq!(
            parse(b"GET / HTTP/1.1\r\nHost: api\r\n"),
            Err(ParseError::Incomplete)
        );
        let limits = Limits {
            max_header_bytes: 1024,
            max_body_bytes: 10,
        };
        let raw = b"POST / HTTP/1.1\r\nHost: api\r\nContent-Length: 999\r\n\r\n";
        assert_eq!(parse_request(raw, limits), Err(ParseError::PayloadTooLarge));
    }

    #[test]
    fn http_1_0_needs_keep_alive_opt_in() {
        let raw = b"GET / HTTP/1.0\r\n\r\n";
        assert!(!parse(raw).expect("valid").should_keep_alive());
        let raw = b"GET / HTTP/1.0\r\nConnection: keep-alive\r\n\r\n";
        assert!(parse(raw).expect("valid").should_keep_alive());
    }
}
