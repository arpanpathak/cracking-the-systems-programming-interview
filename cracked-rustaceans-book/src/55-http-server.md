# 55. A Small HTTP Server {#http-server}

*Source file: [`src/bin/http_server.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/http_server.rs). Run it with `cargo run --bin http_server`, then `curl -i http://127.0.0.1:8080/healthz`.*

## Problem Statement

Serve the following routes over HTTP/1.1:

| Method | Path | Response |
|---|---|---|
| `GET` | `/healthz` | `200` plain text |
| `GET` | `/v1/gpu-workloads` | `200` JSON list |
| `POST` | `/v1/gpu-workloads` | `201` created |
| `GET` | `/v1/gpu-workloads/{id}` | `200` one workload |
| `DELETE` | `/v1/gpu-workloads/{id}` | `204` no content |

A known path with an unsupported method returns `405 Method Not Allowed`, an unknown path
returns `404 Not Found`, and a request the parser rejects returns `400 Bad Request`. A
connection stays open for further requests unless the client asks to close it.

## Designing a Solution

**Separate the protocol from the application.** `route` takes a parsed `Request` and
returns `(status, content_type, body)`. It knows nothing about sockets or bytes on the
wire, so its behaviour can be tested with constructed requests. `build_response` turns
that triple into bytes, and `handle_connection` owns the socket.

**Read until a request parses.** `handle_connection` keeps a growing buffer. It asks the
parser from chapter 54 for a request, and on `Incomplete` reads more bytes and tries
again. Any other error ends the connection with a 400. After a response, the loop either
returns, when the connection should close, or clears the buffer and waits for the next
request.

```text
loop:
    match parse_request(buffer):
        Ok(request)      -> route, write response, close or clear buffer
        Err(Incomplete)  -> read more bytes; a read of 0 means the client left
        Err(other)       -> write 400 with Connection: close, return
```

**404 or 405.** The status tells the client what to change. A 404 says the resource does
not exist, so a different method will not help; a 405 says the resource exists and the
method is wrong. The router therefore matches the path first and the method second.

## Implementation

````rust
//! Minimal HTTP/1.1 server with REST-style routes.
//!
//! This is the "write a web server" exercise an SDK/CLI interview often starts
//! with. It uses only `std::net` plus the request parser in
//! [`nvidia_rust_interview_lab::problems::http_request`], so the interesting parts
//! stay visible: the accept loop, the keep-alive loop, status codes, and the
//! routing decision.
//!
//! Routes:
//!
//! | Method | Path | Response |
//! |---|---|---|
//! | `GET` | `/healthz` | `200` plain text |
//! | `GET` | `/v1/gpu-workloads` | `200` JSON list |
//! | `POST` | `/v1/gpu-workloads` | `201` created |
//! | `GET` | `/v1/gpu-workloads/{id}` | `200` one workload |
//! | `DELETE` | `/v1/gpu-workloads/{id}` | `204` no content |
//!
//! A known path with the wrong method returns `405`, and an unknown path returns
//! `404`. Pipelined requests are not supported: the loop handles one request per
//! read buffer, which matches how most servers treat pipelining in practice.
//!
//! ```bash
//! cargo run --bin http_server            # binds 127.0.0.1:8080
//! curl -i http://127.0.0.1:8080/healthz
//! curl -i -X POST -d '{"gpuCount":1}' http://127.0.0.1:8080/v1/gpu-workloads
//! ```

use nvidia_rust_interview_lab::problems::http_request::{
    Limits, Method, ParseError, Request, parse_request,
};
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::thread;

/// Map a request to `(status, content_type, body)`.
///
/// Pure, so the routing rules are unit-testable without a socket.
pub fn route(request: &Request) -> (u16, &'static str, Vec<u8>) {
    let target = request.target.as_str();

    if target == "/healthz" {
        return match request.method {
            Method::Get | Method::Head => (200, "text/plain", b"ok\n".to_vec()),
            _ => method_not_allowed(),
        };
    }

    if target == "/v1/gpu-workloads" {
        return match request.method {
            Method::Get | Method::Head => (
                200,
                "application/json",
                br#"[{"id":"wl-a100-1","gpuCount":1,"state":"Running"}]"#.to_vec(),
            ),
            Method::Post => (
                201,
                "application/json",
                br#"{"id":"wl-a100-2","gpuCount":1,"state":"Pending"}"#.to_vec(),
            ),
            _ => method_not_allowed(),
        };
    }

    if let Some(id) = target.strip_prefix("/v1/gpu-workloads/") {
        if id.is_empty() || id.contains('/') {
            return (404, "text/plain", b"not found\n".to_vec());
        }
        return match request.method {
            Method::Get | Method::Head => (
                200,
                "application/json",
                format!(r#"{{"id":"{id}","state":"Running"}}"#).into_bytes(),
            ),
            Method::Delete => (204, "", Vec::new()),
            _ => method_not_allowed(),
        };
    }

    (404, "text/plain", b"not found\n".to_vec())
}

fn method_not_allowed() -> (u16, &'static str, Vec<u8>) {
    (405, "text/plain", b"method not allowed\n".to_vec())
}

fn status_reason(status: u16) -> &'static str {
    match status {
        200 => "OK",
        201 => "Created",
        204 => "No Content",
        400 => "Bad Request",
        404 => "Not Found",
        405 => "Method Not Allowed",
        413 => "Payload Too Large",
        _ => "Internal Server Error",
    }
}

fn build_response(status: u16, content_type: &str, body: &[u8], keep_alive: bool) -> Vec<u8> {
    let mut response = format!("HTTP/1.1 {} {}\r\n", status, status_reason(status));
    response.push_str(&format!("Content-Length: {}\r\n", body.len()));
    if !content_type.is_empty() {
        response.push_str(&format!("Content-Type: {content_type}\r\n"));
    }
    response.push_str(if keep_alive {
        "Connection: keep-alive\r\n"
    } else {
        "Connection: close\r\n"
    });
    response.push_str("\r\n");

    let mut bytes = response.into_bytes();
    bytes.extend_from_slice(body);
    bytes
}

/// Serve connections forever, one thread per connection.
pub fn serve(listener: TcpListener) {
    for incoming in listener.incoming() {
        match incoming {
            Ok(stream) => {
                thread::spawn(move || {
                    if let Err(error) = handle_connection(stream) {
                        eprintln!("connection error: {error}");
                    }
                });
            }
            Err(error) => eprintln!("accept error: {error}"),
        }
    }
}

fn handle_connection(mut stream: TcpStream) -> std::io::Result<()> {
    stream.set_nodelay(true)?;
    let limits = Limits::default();
    let mut buffer = Vec::new();
    let mut chunk = [0u8; 4096];

    loop {
        match parse_request(&buffer, limits) {
            Ok(request) => {
                let keep_alive = request.should_keep_alive();
                let (status, content_type, body) = route(&request);
                let response = build_response(status, content_type, &body, keep_alive);
                stream.write_all(&response)?;

                if !keep_alive {
                    return Ok(());
                }
                buffer.clear();
            }
            Err(ParseError::Incomplete) => {
                let read = stream.read(&mut chunk)?;
                if read == 0 {
                    // Peer closed mid-request.
                    return Ok(());
                }
                buffer.extend_from_slice(&chunk[..read]);
            }
            Err(error) => {
                let response =
                    build_response(400, "text/plain", error.to_string().as_bytes(), false);
                stream.write_all(&response)?;
                return Ok(());
            }
        }
    }
}

fn main() {
    let address = std::env::args()
        .nth(1)
        .unwrap_or_else(|| "127.0.0.1:8080".to_string());

    let listener = TcpListener::bind(&address).expect("failed to bind");
    let local = listener.local_addr().expect("failed to read local address");
    println!("http server listening on http://{local}");

    serve(listener);
}

#[cfg(test)]
mod tests {
    use super::*;
    use nvidia_rust_interview_lab::problems::http_request::Version;

    fn request(method: Method, target: &str) -> Request {
        Request {
            method,
            target: target.to_string(),
            version: Version::Http11,
            headers: vec![("host".to_string(), "localhost".to_string())],
            body: Vec::new(),
        }
    }

    #[test]
    fn healthz_is_ok() {
        let (status, content_type, body) = route(&request(Method::Get, "/healthz"));
        assert_eq!(status, 200);
        assert_eq!(content_type, "text/plain");
        assert_eq!(body, b"ok\n");
    }

    #[test]
    fn lists_and_creates_workloads() {
        let (status, _, _) = route(&request(Method::Get, "/v1/gpu-workloads"));
        assert_eq!(status, 200);

        let (status, content_type, body) = route(&request(Method::Post, "/v1/gpu-workloads"));
        assert_eq!(status, 201);
        assert_eq!(content_type, "application/json");
        assert!(String::from_utf8(body).expect("json").contains("Pending"));
    }

    #[test]
    fn gets_and_deletes_one_workload() {
        let (status, _, body) = route(&request(Method::Get, "/v1/gpu-workloads/wl-7"));
        assert_eq!(status, 200);
        assert!(String::from_utf8(body).expect("json").contains("wl-7"));

        let (status, _, body) = route(&request(Method::Delete, "/v1/gpu-workloads/wl-7"));
        assert_eq!(status, 204);
        assert!(body.is_empty());
    }

    #[test]
    fn wrong_method_on_known_path_is_405() {
        let (status, _, _) = route(&request(Method::Put, "/healthz"));
        assert_eq!(status, 405);
        let (status, _, _) = route(&request(Method::Put, "/v1/gpu-workloads"));
        assert_eq!(status, 405);
    }

    #[test]
    fn unknown_path_is_404() {
        let (status, _, _) = route(&request(Method::Get, "/nope"));
        assert_eq!(status, 404);
    }
}
````

### Routing

`route` matches three kinds of path in order: the exact `/healthz`, the exact collection
path, and the collection path followed by an identifier. `target.strip_prefix(...)`
returns the remainder only when the prefix matches, so `if let Some(id)` both tests and
extracts. An empty identifier, or one containing `/`, returns 404, which rejects paths
such as `/v1/gpu-workloads/` and `/v1/gpu-workloads/a/b`.

The return type `(u16, &'static str, Vec<u8>)` uses a static string for the content type,
because every content type the server sends is a literal, and a `Vec<u8>` for the body,
because one route formats its body at run time.

`br#"..."#` is a raw byte string literal. The `r#` form allows the JSON's double quotes
without escaping, and the `b` prefix makes the literal a `&[u8; N]`.

### Responses and connections

`build_response` writes the status line, `Content-Length`, an optional `Content-Type`,
and a `Connection` header, followed by an empty line and the body. `Content-Length` is
what lets a keep-alive client find the end of the response without waiting for the
connection to close.

`handle_connection` computes `keep_alive` from the request before routing, writes the
response with `write_all`, and returns when the connection should close. On a parse
error it writes the error's `Display` text as a 400 body and closes the connection,
because after a malformed request the server cannot know where the next request would
begin.

`main` accepts an optional address argument and defaults to `127.0.0.1:8080`.

The test helper `request` builds a `Request` value directly. Because `route` is pure, the
tests check status codes, content types, and bodies without binding a port.

## Intuition

A session with `curl` against the running server:

```text
$ curl -i http://127.0.0.1:8080/v1/gpu-workloads/wl-7
HTTP/1.1 200 OK
Content-Length: 31
Content-Type: application/json
Connection: keep-alive

{"id":"wl-7","state":"Running"}

$ curl -i -X DELETE http://127.0.0.1:8080/v1/gpu-workloads/wl-7
HTTP/1.1 204 No Content
Content-Length: 0
Connection: keep-alive
```

**How `route` answers several requests**

| request | path branch | method arm | response |
|---|---|---|---|
| `GET /healthz` | exact `/healthz` | `Get` | `200`, `ok\n` |
| `PUT /healthz` | exact `/healthz` | `_` | `405` |
| `POST /v1/gpu-workloads` | exact collection | `Post` | `201`, JSON |
| `DELETE /v1/gpu-workloads/wl-7` | prefix, `id = "wl-7"` | `Delete` | `204`, empty body |
| `GET /v1/gpu-workloads/` | prefix, `id = ""` | not reached | `404` |
| `GET /nope` | none | not reached | `404` |

## Time and Space Complexity

| Stage | Cost |
|---|---|
| per request | one parse of the buffered bytes, one route match, one response allocation |
| per connection | one thread and one growing buffer, bounded by the parser's limits |
| routing | `O(path length)` for the prefix comparisons |

## Limitations

**Responses to `HEAD` include a body.** `route` returns the same body for `HEAD` as for
`GET`, and `build_response` always appends it. RFC 9110 requires that a response to
`HEAD` carry the headers of the `GET` response and no body. A client that sends `HEAD`
and then a second request on the same connection will read the unexpected body as the
start of the next response.

**`204` responses carry `Content-Length: 0`.** RFC 9110 says a server must not send
`Content-Length` in a `204` response. Most clients tolerate it, and it is still a
protocol violation that a strict client or proxy may reject.

**The identifier is inserted into JSON without escaping.**
`format!(r#"{{"id":"{id}","state":"Running"}}"#)` places the path segment inside a JSON
string as it arrived. A request for `/v1/gpu-workloads/a"b` produces invalid JSON, and a
crafted identifier can add fields to the object. Serializing with `serde_json`, or at
least escaping `"` and `\`, prevents both.

**All parse errors become 400.** `status_reason` includes `413 Payload Too Large`, but
`handle_connection` sends 400 for every error, including `ParseError::PayloadTooLarge`.
Mapping that variant to 413 gives the client the correct reason.

**Pipelined requests are discarded.** After a request is handled, `buffer.clear()` drops
any bytes that arrived after it in the same read. A client that pipelines two requests
receives one response and then waits. The module documentation states this, and fixing
it requires the parser to report how many bytes it consumed.

**Unbounded threads and no timeouts.** The limitations of chapter 52 apply unchanged: a
thread per connection, no limit on connections, and no idle timeout.

**String building allocates repeatedly.** `build_response` calls `format!` for each header
and appends the result with `push_str`. `std::fmt::Write` allows `write!(response,
"Content-Length: {}\r\n", body.len())` directly into the `String`, which avoids the
temporary allocations.

## Summary

- Keeping `route` pure, from `Request` to `(status, content_type, body)`, makes the
  application logic testable without a socket.
- The connection loop parses what it has, reads more on `Incomplete`, and closes after a
  malformed request because it cannot find the next request boundary.
- Match the path before the method, so a wrong method on an existing path returns 405
  and an unknown path returns 404.
- `Content-Length` lets keep-alive clients find the end of each response.
- A conforming server sends no body for `HEAD`, no `Content-Length` for `204`, escapes
  data it places in JSON, and maps each parse failure to its own status.

## References

- RFC 9110, *HTTP Semantics*, 2022, Sections 9.3.2 (`HEAD`), 15.3.5 (`204`), and 15.5.6
  (`405`).
- RFC 9112, *HTTP/1.1*, 2022, Section 9, on persistent connections.
- The `serde_json` crate, [`json!` macro](https://docs.rs/serde_json/latest/serde_json/macro.json.html).
- Standard library, [`str::strip_prefix`](https://doc.rust-lang.org/std/primitive.str.html#method.strip_prefix) and [`std::fmt::Write`](https://doc.rust-lang.org/std/fmt/trait.Write.html).
