# 54. Parsing HTTP/1.1 Requests {#http-request-parsing}

*Source file: [`src/problems/http_request.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/http_request.rs). Test it with `cargo test http_request`.*

## Problem Statement

Given a byte slice that begins at the start of a request, return a `Request` containing
the method, target, version, headers, and body, or an error that says why no request
could be produced. The parser must:

- return `Incomplete` when the bytes so far are a valid prefix of a request;
- reject a request line with a missing, extra, or unknown part;
- require exactly one `Host` header for HTTP/1.1;
- reject obsolete header line folding;
- reject a request with both `Content-Length` and `Transfer-Encoding`;
- decode chunked bodies, and bound header and body sizes.

## Designing a Solution

An HTTP/1.1 request has three parts:

```text
POST /v1/gpu-workloads HTTP/1.1\r\n          request line
Host: api.example.com\r\n                    header lines
Content-Length: 13\r\n
\r\n                                         empty line ends the head
{"gpuCount":1}                               body, framed by the headers
```

**Find the end of the head first.** The head ends at the first `\r\n\r\n`. Until those
four bytes arrive, the request is incomplete, unless the bytes already exceed the header
limit, in which case the request is too large. Everything before that point is split into
lines.

**Parse the head as text only where the grammar is text.** The request line and header
names and values are converted to `&str` with `from_utf8`, and invalid UTF-8 is a
malformed request. The body stays as bytes.

**Decide the body length from exactly one source.** The body is framed either by
`Content-Length`, a decimal byte count, or by `Transfer-Encoding: chunked`, a sequence of
hexadecimal-length chunks ending with a zero-length chunk. RFC 9112 requires a server to
treat a request carrying both as an error, because a proxy that honours one and a server
that honours the other would split the same bytes into different requests. That
disagreement is the basis of request smuggling.

**Bound everything.** A header section larger than 16 KiB, or a body larger than 8 MiB,
is rejected before the parser allocates for it.

## Implementation

```rust
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
```

### Methods, versions, and the request type

`Method::parse` uses `Some(match token { ... _ => return None })`. Every arm except the
last produces a `Method`, and the last returns from the function, so the `match`
expression has type `Method` and the whole body fits in one expression.

`is_safe` and `is_idempotent` encode RFC 9110's definitions. `PUT` and `DELETE` are
idempotent but not safe, and `POST` and `PATCH` are neither. Chapter 57 uses the same
distinction to decide which requests may be retried.

`Request::header` compares names with `eq_ignore_ascii_case`, because HTTP header names
are case-insensitive, and returns the first match.

`should_keep_alive` splits the `Connection` header on commas, because the header is a
list, and applies the default for each version: HTTP/1.1 keeps connections open unless
told to close, and HTTP/1.0 closes them unless told to keep them alive.

### Errors

`ParseError` is `Copy`. `Malformed` carries a `&'static str` reason rather than a
`String`, so constructing an error never allocates. A client can make the parser fail
on purpose, and failing should cost as little as possible.

### The request line and headers

`let Some(header_end) = ... else { ... }` handles the missing terminator first, choosing
between `PayloadTooLarge` and `Incomplete` by the input length.

The head is split on `\n` with each line's trailing `\r` removed by `strip_suffix`. The
request line is split on single spaces into exactly three parts. `parts.next().is_some()`
after the version rejects a fourth part, and `target.is_empty()` rejects the empty target
that two consecutive spaces produce.

Header lines beginning with a space or tab are obsolete line folding, which RFC 9112
says a server must reject or replace; this parser rejects them. A header name must be
non-empty and free of whitespace, which rejects `Host : api`, a form some servers accept
and others do not.

The `Host` check counts matching headers and requires exactly one, for HTTP/1.1 only.

### Body framing

`collect` is a closure that returns every value of a header. Collecting all values rather
than the first is required for framing: two `Content-Length` headers with different
values are rejected as `conflicting Content-Length`, while two with the same value are
accepted, as RFC 9112 permits.

For `Transfer-Encoding`, all values are joined and split on commas. The only coding the
parser supports is `chunked`, and it must be the final coding. Anything else is
`UnsupportedTransferEncoding`.

`lengths.next().expect("non-empty")?` combines two operations. `expect` documents that
the iterator cannot be empty, because the function returned earlier for an empty list,
and `?` propagates a parse failure of the first value.

### Chunked decoding

Each chunk begins with a hexadecimal size, optionally followed by `;` and chunk
extensions, which the parser ignores. A size of zero ends the body; the loop then skips
trailer lines until an empty line. For a non-zero size, the parser checks the body limit,
checks that the chunk and its trailing `\r\n` are fully present, copies the chunk, and
verifies the `\r\n`.

`find_crlf` uses `data.get(from..)?`, which returns `None` rather than panicking when
`from` is past the end of the data.

## Intuition

**Parsing a chunked `POST` from the test `decodes_chunked_bodies`**

| stage | input examined | result |
|---|---|---|
| find head end | up to the first `\r\n\r\n` | `header_end` found |
| request line | `POST /u HTTP/1.1` | `Method::Post`, target `/u`, `Http11` |
| headers | `Host: api`, `Transfer-Encoding: chunked` | two headers; exactly one `Host` |
| framing | `transfer-encoding` present, no `content-length` | chunked |
| chunk 1 | `5\r\nhello\r\n` | size 5, body `hello` |
| chunk 2 | `6\r\n world\r\n` | size 6, body `hello world` |
| last chunk | `0\r\n\r\n` | size 0; empty trailer line ends the body |
| result | | `Ok(Request { body: b"hello world", .. })` |

For the smuggling test, both `Content-Length: 5` and `Transfer-Encoding: chunked` are
present, and `parse_body` returns `AmbiguousBodyLength` before looking at the body.

## Time and Space Complexity

| Stage | Time | Space |
|---|---|---|
| finding the head | `O(n)` over the bytes received | none |
| request line and headers | `O(head length)` | one `String` pair per header |
| `Content-Length` body | `O(body length)` | one copy of the body |
| chunked body | `O(body length)` plus `O(chunks)` line searches | one growing `Vec<u8>` |

## Limitations

**A chunk size near `usize::MAX` panics in a debug build.** In `decode_chunked`, the check
`body.len() + size > max_body` adds before comparing. A client that sends one valid chunk
and then a chunk size of `ffffffffffffffff` makes the addition overflow. With overflow
checks enabled, as in a debug build, the parser panics; the following request triggers
it:

```text
POST / HTTP/1.1\r\nHost: a\r\nTransfer-Encoding: chunked\r\n\r\n5\r\nhello\r\nffffffffffffffff\r\n
```

In a release build the sum wraps, passes the size check, and the later `checked_add`
reports `Malformed`, so the outcome depends on the build profile. Comparing without
adding removes the problem:

```rust
if size > max_body - body.len() {
    return Err(ParseError::PayloadTooLarge);
}
```

`body.len()` never exceeds `max_body`, so the subtraction cannot underflow.

**The head is searched again on every call.** A server that calls `parse_request` after
each read rescans all the bytes received so far for `\r\n\r\n`. For a client that sends
a 16 KiB head one byte at a time, that is quadratic work bounded by the header limit. A
parser that remembers where it stopped avoids it.

**Header names are not validated as tokens.** RFC 9110 restricts header names to a set
of token characters. The parser rejects only empty names and names containing
whitespace, so names such as `X(Y)` are accepted.

**`Transfer-Encoding` is accepted for HTTP/1.0.** The chunked coding was introduced in
HTTP/1.1, and RFC 9112 advises treating its presence in a 1.0 request as a framing
error.

**One request per call.** The parser does not report how many bytes it consumed, so a
caller cannot find the start of a pipelined second request in the same buffer. Returning
the consumed length alongside the `Request` would allow it.

## Summary

- Parse the head only after the terminating empty line has arrived; report `Incomplete`
  until then and `PayloadTooLarge` if the limit is exceeded first.
- Convert only the textual parts of a request to `&str`, and keep the body as bytes.
- Reject a request that carries both `Content-Length` and `Transfer-Encoding`, and
  reject conflicting `Content-Length` values, to close the ambiguities behind request
  smuggling.
- Bound header and body sizes before allocating, and use allocation-free error values
  in code that untrusted input can drive to failure.
- Size arithmetic on untrusted numbers must not overflow; compare against the remaining
  budget instead of adding to the amount used.

## References

- RFC 9110, *HTTP Semantics*, 2022, Sections 5.1 and 9.2.
- RFC 9112, *HTTP/1.1*, 2022, Sections 6 and 7, on message body length and chunked
  transfer coding.
- James Kettle, "HTTP Desync Attacks: Request Smuggling Reborn", PortSwigger Research,
  2019.
- The `httparse` crate, [documentation](https://docs.rs/httparse/latest/httparse/), a
  zero-copy incremental parser.
