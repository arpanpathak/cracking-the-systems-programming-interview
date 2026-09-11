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
