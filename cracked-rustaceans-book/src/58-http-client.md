# 58. An HTTP Client with Retries and Caching {#http-client}

*Source files: [`src/bin/fun_network_call.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/fun_network_call.rs) and [`src/bin/reqwest_and_tokio.rs`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/reqwest_and_tokio.rs). Both send a request to `httpbin.org` and need network access. Run them with `cargo run --bin fun_network_call` and `cargo run --bin reqwest_and_tokio`.*

## Problem Statement

Create an item on a REST API with `POST /post` and a JSON body. The client must:

- retry a failed attempt with exponential backoff, up to three attempts;
- return the stored response, without sending the request again, when the same
  idempotency key is used a second time;
- report a final failure to the caller.

The chapter reads two versions of the same client. The first uses only the standard
library and writes the HTTP request by hand. The second uses `reqwest` on the `tokio`
runtime. Reading them side by side shows which concerns a library absorbs and which
remain the caller's responsibility.

## Designing a Solution

Both clients layer the same three functions:

```text
execute(key, request)
    |
    +-- cache: return the stored body if key was seen
    |
    +-- retry: call send up to max_attempts times with growing delays
            |
            +-- send: one HTTP exchange
```

The order of the layers is a design decision. The cache is outside the retry loop, so a
successful response is stored once, however many attempts it took, and a cached key
never reaches the network.

A client-side cache protects against the caller repeating a call. It cannot protect
against the case chapter 34 began with, where the server performed the work and the
response was lost, because the client never received a response to cache. That case
needs the server's help: the client sends the key in an `Idempotency-Key` header, and the
server stores the result under that key. The `reqwest` version sends the header; the
standard-library version does not.

## Implementation

### The standard-library client

```rust
use std::collections::HashMap;
use std::io::{Read, Write};
use std::net::TcpStream;
use std::sync::Mutex;
use std::time::Duration;

type RuntimeError = Box<dyn std::error::Error>;

enum RequestType {
    GET    { path: String, headers: Vec<(String, String)> },
    OPTION { path: String, headers: Vec<(String, String)> },
    POST   { path: String, headers: Vec<(String, String)>, body: String },
    PUT    { path: String, headers: Vec<(String, String)>, body: String },
}

struct IdemCache {
    store: Mutex<HashMap<String, String>>,
}

impl IdemCache {
    fn new() -> Self {
        Self { store: Mutex::new(HashMap::new()) }
    }

    fn get_or_insert<F>(&self, key: &str, f: F) -> Result<String, RuntimeError>
    where
        F: FnOnce() -> Result<String, RuntimeError>,
    {
        let mut store = self.store.lock().map_err(|_| "lock poisoned")?;
        if let Some(v) = store.get(key) {
            return Ok(v.clone());
        }
        let v = f()?;
        store.insert(key.to_string(), v.clone());
        Ok(v)
    }
}

struct RetryPolicy {
    max_attempts: u32,
    base_delay: Duration,
    max_delay: Duration,
}

impl RetryPolicy {
    fn new() -> Self {
        Self {
            max_attempts: 3,
            base_delay: Duration::from_millis(100),
            max_delay: Duration::from_secs(5),
        }
    }

    fn execute<F, T>(&self, mut f: F) -> Result<T, RuntimeError>
    where
        F: FnMut() -> Result<T, RuntimeError>,
    {
        let mut attempt = 0;
        loop {
            attempt += 1;
            match f() {
                Ok(v) => return Ok(v),
                Err(e) if attempt >= self.max_attempts => return Err(e),
                Err(_) => {
                    let delay = (self.base_delay * 2u32.pow(attempt - 1)).min(self.max_delay);
                    std::thread::sleep(delay);
                }
            }
        }
    }
}

/// -- Build a HTTP client with those strategies

struct HttpClient {
    host: String,
    port: u16,
    cache: IdemCache,
    retry: RetryPolicy,
}

impl HttpClient {
    fn new(host: &str, port: u16) -> Self {
        Self {
            host: host.to_string(),
            port,
            cache: IdemCache::new(),
            retry: RetryPolicy::new(),
        }
    }

    fn execute(&self, key: &str, req: &RequestType) -> Result<String, RuntimeError> {
        self.cache.get_or_insert(key, || self.retry.execute(|| self.send(req)))
    }

    fn send(&self, req: &RequestType) -> Result<String, RuntimeError> {
        let (method, path, headers, body) = match req {
            RequestType::GET    { path, headers }       => ("GET",     path, headers, None),
            RequestType::OPTION { path, headers }       => ("OPTIONS", path, headers, None),
            RequestType::POST   { path, headers, body } => ("POST",    path, headers, Some(body)),
            RequestType::PUT    { path, headers, body } => ("PUT",     path, headers, Some(body)),
        };

        let mut raw = format!(
            "{method} {path} HTTP/1.1\r\nHost: {}\r\nConnection: close\r\n",
            self.host
        );
        for (k, v) in headers { raw += &format!("{k}: {v}\r\n"); }
        if let Some(b) = body { raw += &format!("Content-Length: {}\r\n", b.len()); }
        raw += "\r\n";
        if let Some(b) = body { raw += b; }

        let mut stream = TcpStream::connect((self.host.as_str(), self.port))?;
        stream.write_all(raw.as_bytes())?;
        let mut resp = String::new();
        stream.read_to_string(&mut resp)?;
        Ok(resp.split_once("\r\n\r\n").map(|(_, b)| b).unwrap_or("").to_string())
    }
}

// --- The actual REST call ---

fn create_item(client: &HttpClient, item_name: &str) -> Result<String, RuntimeError> {
    client.execute("create-demo-001", &RequestType::POST {
        path: "/post".into(),
        headers: vec![
            ("Content-Type".into(), "application/json".into()),
            ("Accept".into(), "application/json".into()),
        ],
        body: format!(r#"{{"name":"{item_name}"}}"#),
    })
}

fn main() -> Result<(), RuntimeError> {
    let client = HttpClient::new("httpbin.org", 80);
    println!("created:\n{}", create_item(&client, "demo")?);
    Ok(())
}
```

`RuntimeError` is `Box<dyn std::error::Error>`, the conventional error type for a
program's top level. Any error type, and any `&str` or `String`, converts into it with
`?`, which is how `map_err(|_| "lock poisoned")?` turns a poisoned lock into an error.

`IdemCache::get_or_insert` holds the mutex for its whole body, including the call to
`f`. The same design and the same trade-off appear in chapter 34: a second caller with
the same key waits and then sees the stored value, and every caller, whatever its key,
waits while one request is in flight.

`RetryPolicy::execute` retries every error. The guard `Err(e) if attempt >=
self.max_attempts` returns the last error, and the final arm sleeps for
`base_delay × 2^(attempt - 1)`, capped at `max_delay`.

`execute` composes the layers in one expression:
`self.cache.get_or_insert(key, || self.retry.execute(|| self.send(req)))`.

`send` destructures the request enum into a method string, a path, headers, and an
optional body with a single `match`. It writes the request line, a `Host` header, and
`Connection: close`, which tells the server to close the connection after the response.
That lets the client read the whole response with `read_to_string`, which returns when
the server closes, instead of parsing `Content-Length` or chunked framing. The body
follows the empty line, with a `Content-Length` header computed from its byte length.

`resp.split_once("\r\n\r\n")` separates the response head from the body, and the client
returns the body.

### The `reqwest` and `tokio` client

```rust
use std::{collections::HashMap, sync::Mutex, time::Duration};
use reqwest::{Client, Method, StatusCode};
use serde_json::Value;

type Error = Box<dyn std::error::Error + Send + Sync>;

const RETRY: [StatusCode; 5] = [
    StatusCode::TOO_MANY_REQUESTS,
    StatusCode::INTERNAL_SERVER_ERROR,
    StatusCode::BAD_GATEWAY,
    StatusCode::SERVICE_UNAVAILABLE,
    StatusCode::GATEWAY_TIMEOUT,
];

struct Config {
    base: String,
    max_attempts: u32,
    base_delay: Duration,
    max_delay: Duration,
    timeout: Duration,
}

struct Api {
    http: Client,
    cache: Mutex<HashMap<String, String>>,
    cfg: Config,
}

impl Api {
    fn new(cfg: Config) -> Result<Self, Error> {
        Ok(Self {
            http: Client::builder().timeout(cfg.timeout).build()?,
            cache: Mutex::new(HashMap::new()),
            cfg,
        })
    }

    fn cached(&self, key: &str) -> Option<String> {
        self.cache
            .lock()
            .unwrap_or_else(|e| e.into_inner())
            .get(key)
            .cloned()
    }

    fn store(&self, key: &str, text: &str) {
        self.cache
            .lock()
            .unwrap_or_else(|e| e.into_inner())
            .insert(key.into(), text.into());
    }

    async fn call(
        &self,
        key: &str,
        method: Method,
        path: &str,
        body: Option<&Value>,
    ) -> Result<String, Error> {
        match self.cached(key) {
            Some(hit) => return Ok(hit),
            None => {}
        }

        let url = format!("{}{}", self.cfg.base, path);
        let mut delay = self.cfg.base_delay;
        let mut attempt = 0;

        loop {
            attempt += 1;

            let req = self
                .http
                .request(method.clone(), &url)
                .header("Idempotency-Key", key)
                .header("Accept", "application/json");
            let req = match body {
                Some(b) => req.json(b),
                None => req,
            };

            let resp = req.send().await?;
            let status = resp.status();
            let text = resp.text().await?;

            match status {
                s if s.is_success() => {
                    self.store(key, &text);
                    return Ok(text);
                }
                s if RETRY.contains(&s) && attempt < self.cfg.max_attempts => {
                    tokio::time::sleep(delay).await;
                    delay = (delay * 2).min(self.cfg.max_delay);
                }
                s => return Err(format!("HTTP {s} after {attempt} attempts: {text}").into()),
            }
        }
    }
}

#[tokio::main]
async fn main() -> Result<(), Error> {
    let api = Api::new(Config {
        base: "https://httpbin.org".into(),
        max_attempts: 3,
        base_delay: Duration::from_millis(100),
        max_delay: Duration::from_secs(5),
        timeout: Duration::from_secs(15),
    })?;

    let body = serde_json::json!({ "name": "demo" });
    let out = api
        .call("create-demo-001", Method::POST, "/post", Some(&body))
        .await?;
    println!("created:\n{out}");
    Ok(())
}
```

`Error` is `Box<dyn std::error::Error + Send + Sync>`. The additional bounds let the error
cross threads, which `tokio`'s multi-threaded runtime can require of values held across
an `.await`.

`Client::builder().timeout(cfg.timeout).build()?` sets a total timeout for each request.
Building one `Client` and reusing it keeps a connection pool, so repeated calls to the
same host reuse TCP and TLS connections.

The cache uses `std::sync::Mutex` in async code. That is correct here, because `cached`
and `store` take and release the lock without awaiting in between. A standard mutex held
across an `.await` would block the executor thread. `lock().unwrap_or_else(|e|
e.into_inner())` recovers the guard from a poisoned lock, which is reasonable for a cache
whose entries are independent strings.

The retry loop sends the `Idempotency-Key` header on every attempt, so a server that
supports idempotency keys recognises a retried request after a lost response. It reads
the status and body, returns and caches a success, sleeps and doubles the delay for a
status in `RETRY` while attempts remain, and otherwise returns an error that includes
the status, the attempt count, and the response text. `tokio::time::sleep(delay).await`
yields to the runtime rather than blocking a thread.

`#[tokio::main]` wraps `main` in a runtime, and `serde_json::json!` builds the body from
JSON-like syntax with correct escaping.

## Intuition

**`create_item` in the standard-library client, when the first attempt fails to connect**

| layer | action |
|---|---|
| `execute("create-demo-001", ..)` | locks the cache; key not present |
| `retry.execute`, attempt 1 | `send` fails in `TcpStream::connect`; attempt 1 < 3, sleep 100 ms |
| `retry.execute`, attempt 2 | `send` connects, writes the request, reads to close; returns the body |
| cache | stores the body under `create-demo-001`, releases the lock |
| second `execute` with the same key | returns the stored body without connecting |

**`Api::call` in the `reqwest` client, for a 503 followed by a 200**

| attempt | status | action |
|---|---|---|
| 1 | 503 | in `RETRY`, 1 < 3: sleep 100 ms, delay becomes 200 ms |
| 2 | 200 | success: store the text under the key and return it |

## Time and Space Complexity

| Operation | Cost |
|---|---|
| cache hit | one lock acquisition and one `String` clone |
| cache miss | up to three HTTP exchanges plus up to 100 ms + 200 ms of backoff |
| memory | one stored body per distinct key, never evicted |

## Limitations

**The standard-library client treats every HTTP response as success.** `send` returns the
body of any response, including `500 Internal Server Error`. A server error therefore
reaches the caller as `Ok`, is never retried, and is stored in the cache, so every later
call with the same key returns the error page. Checking the status line before returning
closes the gap:

```rust
let (head, body) = resp.split_once("\r\n\r\n").ok_or("malformed response")?;
let status: u16 = head
    .split(' ')
    .nth(1)
    .and_then(|code| code.parse().ok())
    .ok_or("malformed status line")?;
if !(200..300).contains(&status) {
    return Err(format!("HTTP {status}: {body}").into());
}
Ok(body.to_string())
```

**The `reqwest` client does not retry transport failures.** `req.send().await?` returns
at once when the connection fails or the request times out, which are the failures a
retry is most likely to fix. Only HTTP status codes in `RETRY` are retried. Matching on
the send result retries timeouts and connection errors as well:

```rust
let resp = match req.send().await {
    Ok(resp) => resp,
    Err(error)
        if (error.is_timeout() || error.is_connect()) && attempt < self.cfg.max_attempts =>
    {
        tokio::time::sleep(delay).await;
        delay = (delay * 2).min(self.cfg.max_delay);
        continue;
    }
    Err(error) => return Err(error.into()),
};
```

**Neither client adds jitter or honours `Retry-After`.** Both double a fixed delay, so
many clients that fail together retry together, and a `429` response's `Retry-After`
header is ignored. Chapter 57's policy provides both.

**The standard-library client retries non-idempotent requests without a server-side
key.** A `POST` whose response is lost is sent again with nothing that lets the server
recognise it, which can create a duplicate item. The `reqwest` client's
`Idempotency-Key` header addresses this when the server supports it.

**The cache check and the request are not atomic in the async client.** Two concurrent
calls with the same key can both miss the cache and both send the request. The
standard-library client avoids this by holding its lock across the request, at the cost
of serializing every request.

**No timeouts in the standard-library client.** `TcpStream::connect`, `write_all`, and
`read_to_string` can each block indefinitely. `TcpStream::connect_timeout`,
`set_read_timeout`, and `set_write_timeout` bound them.

**The JSON body is built with `format!`.** In `create_item`, a name containing `"` or `\`
produces invalid JSON. The `reqwest` version's `json!` macro escapes correctly.

**Compiler and Clippy warnings.** The variants `GET`, `OPTION`, and `PUT` are never
constructed, and variant names in all capitals trigger Clippy's `upper_case_acronyms`;
the idiomatic names are `Get`, `Options`, `Post`, and `Put`. In the async client,
`match self.cached(key) { Some(hit) => return Ok(hit), None => {} }` is clearer as
`if let Some(hit) = self.cached(key) { return Ok(hit); }`, as Clippy's `single_match`
lint suggests.

**No response framing.** Reading until close works only because the request asks for
`Connection: close`. The client cannot reuse connections, and it would return the raw
chunk-size lines of a chunked response as part of the body.

## Summary

- A client composes a cache, a retry policy, and a single-exchange function; placing the
  cache outside the retry loop stores each result once.
- A hand-written HTTP/1.1 client writes the request line, `Host`, framing headers, an
  empty line, and the body, and `Connection: close` lets it read the response to the end
  of the stream.
- A client-side cache handles repeated calls; only a server-side idempotency key handles a
  response that was lost after the server did the work.
- `reqwest` provides connection pooling, timeouts, TLS, and JSON encoding; the caller
  still decides which statuses and transport errors to retry.
- A client must check the status before caching or returning a body, and must retry the
  transport failures that retries exist for.

## References

- The `reqwest` crate, [`Client`](https://docs.rs/reqwest/latest/reqwest/struct.Client.html) and [`Error`](https://docs.rs/reqwest/latest/reqwest/struct.Error.html).
- The Tokio tutorial, [Shared state](https://tokio.rs/tokio/tutorial/shared-state), on using `std::sync::Mutex` in async code.
- IETF HTTPAPI working group, *The Idempotency-Key HTTP Header Field*, Internet-Draft.
- RFC 9112, *HTTP/1.1*, 2022, Section 9.6, on `Connection: close`.
