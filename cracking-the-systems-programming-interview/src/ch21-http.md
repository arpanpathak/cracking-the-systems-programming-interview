<img class="plate" src="art/ch21.png" alt="Courier, the robot who reads every header before opening the parcel, beside a pneumatic tube carrying a request capsule into a sorting office">

# Parsing and serving HTTP/1.1

<div class="covers" markdown="1">

This chapter covers

- Parsing an HTTP/1.1 request from bytes: request line, headers, and body framing
- Why `Content-Length` plus `Transfer-Encoding` must be rejected, and what request smuggling is
- Decoding chunked bodies, enforcing size limits, and reporting "incomplete" as a normal result
- A small REST server: a pure routing function, keep-alive, and status codes
- Reading the server against the RFC, and the three things it gets wrong

</div>

HTTP/1.1 looks like text with line breaks, and treating it as text causes bugs. It is a
byte stream, and the headers decide where one message ends and the next begins. The security bugs in real
servers come from two programs disagreeing about that boundary. This chapter builds a parser around that one
question. It then builds a server that keeps protocol handling apart from routing, so each part can be tested alone.

## 21.1 The parser

A parser answers four questions about the bytes it has, in order:

1. Has the whole head arrived? The head ends at the first blank line, `\r\n\r\n`.
2. What does the request line say: which method, which target, which version?
3. What are the headers?
4. Where does the body end?

The fourth question is the one with security consequences. Figure 21.1 shows the order of the checks, and
the sections below take them one at a time. The complete file is listing 21.1 in section 21.3.

<figure>
<img src="figures/ch21-framing.svg" alt="Flowchart: find the end of the head, parse the request line, parse headers, require exactly one Host for HTTP/1.1, then choose body framing: both headers is an error, Transfer-Encoding decodes chunked, Content-Length takes that many bytes, neither means no body">
<figcaption><b>Figure 21.1</b> The order of checks in <code>parse_request</code> and <code>parse_body</code>.</figcaption>
</figure>

### 21.1.1 Types first

The file starts with its vocabulary, so each later function can say exactly what it found. `Method` is an
enum with a `parse` that returns `None` for an unknown token:

```rust
{{#include ../../rust-interview-lab/src/problems/http_request.rs:10:45}}
```

The two predicates come from RFC 9110. `is_safe` is true for GET, HEAD, and OPTIONS, which do not change
state. `is_idempotent` adds PUT and DELETE, whose effect is the same if they run twice. Chapter 19's retry
loop is the consumer that needs `is_idempotent`.

`Version` has two variants because the parser accepts two versions. `Limits` carries the caps on header
and body size, 16 KiB and 8 MiB by default:

```rust
{{#include ../../rust-interview-lab/src/problems/http_request.rs:47:66}}
```

A parsed `Request` owns its method, target, version, headers, and body:

```rust
{{#include ../../rust-interview-lab/src/problems/http_request.rs:68:100}}
```

`header` finds a header case-insensitively, because header names are case-insensitive.
`should_keep_alive` encodes the one rule that differs by version. HTTP/1.1 keeps the connection open unless
the client sends `Connection: close`. HTTP/1.0 closes it unless the client sends `Connection: keep-alive`.
The `has` closure splits the header on commas, because `Connection` carries a list.

`ParseError` names each case a server must treat differently:

```rust
{{#include ../../rust-interview-lab/src/problems/http_request.rs:102:112}}
```

`Incomplete` is not a failure. It means "read more bytes and try again", and the server's loop in section
21.2 depends on it. `PayloadTooLarge` maps to status 413, and `MissingHost` and `Malformed` to 400.

### 21.1.2 The head of the request

`parse_request` works on `&[u8]`, not `&str`, because an HTTP body is arbitrary bytes and only the head is
text. Its first job is to find the blank line that ends the head:

```rust
{{#include ../../rust-interview-lab/src/problems/http_request.rs:134:151}}
    // ...
}
```

`windows(4).position(...)` slides a four-byte window along the input until it sees `\r\n\r\n`. If the
blank line is missing, the request is `Incomplete`. The exception is a buffer already larger than
`max_header_bytes`: that client is sending an endless header, and it gets `PayloadTooLarge`. The check
stops a slow client from holding memory with a header that never ends.

The request line comes next. It must be exactly three parts separated by spaces:

```rust
pub fn parse_request(input: &[u8], limits: Limits) -> Result<Request, ParseError> {
    // ...
{{#include ../../rust-interview-lab/src/problems/http_request.rs:153:180}}
    // ...
}
```

The three parts are a known method, a non-empty target, and `HTTP/1.1` or `HTTP/1.0`. A fourth part is an
error.

Each remaining line of the head is one header, split at its first colon:

```rust
pub fn parse_request(input: &[u8], limits: Limits) -> Result<Request, ParseError> {
    // ...
{{#include ../../rust-interview-lab/src/problems/http_request.rs:182:206}}
    // ...
}
```

A name with whitespace is rejected, because RFC 9112 forbids whitespace between the name and the colon. A
line that starts with a space or tab is *obsolete line folding*, a continuation syntax the RFC deprecates.
Different servers interpret it differently, so the parser rejects it.

HTTP/1.1 requires exactly one `Host` header:

```rust
pub fn parse_request(input: &[u8], limits: Limits) -> Result<Request, ParseError> {
    // ...
{{#include ../../rust-interview-lab/src/problems/http_request.rs:208:216}}
    // ...
}
```

`filter(...).count() != 1` rejects both zero and two.

### 21.1.3 Body framing and request smuggling

The head says how long the body is, in one of two ways. `Content-Length: 5` gives a byte count.
`Transfer-Encoding: chunked` says the body arrives in pieces, each with its own size, and ends at a piece
of size zero. A request that uses both is the setup for an attack called request smuggling (figure 21.2).

A front-end proxy may frame a request by `Content-Length`, while the back-end server frames the same bytes
by `Transfer-Encoding: chunked`. The two then disagree about where the request ends. The attacker places a
second request in the part the back-end treats as "after the body". The back-end runs it as though it
arrived on its own, past whatever checks the proxy applied.

<figure>
<img src="figures/ch21-smuggling.svg" alt="One message with both Content-Length and Transfer-Encoding; the proxy reads one request, the back-end ends the POST at the zero chunk and reads GET /admin as a new request; the parser rejects the message instead">
<figcaption><b>Figure 21.2</b> A CL.TE desynchronization. The parser answers such a request with 400 and closes the connection.</figcaption>
</figure>

<figure class="anim">
<video class="motion" src="figures/ch21-http-framing.mp4" autoplay loop muted playsinline preload="metadata" aria-label="A request's bytes stream into a buffer. The parser slides a window until it finds the blank line that ends the head, then splits the request line and headers into fields. With Content-Length: 5, a ruler counts five body bytes. With Transfer-Encoding: chunked, the parser reads a size line, takes that many bytes, and stops at the zero-size chunk. Last, one message carries both headers: a proxy frames it by Content-Length and sees one request, a back-end frames it by chunks and finds a hidden GET /admin after the body. The parser refuses the message with 400 and closes the connection." data-chapters="[[0.0, &quot;the head&quot;], [14.82, &quot;Content-Length&quot;], [26.22, &quot;chunked&quot;], [42.6, &quot;both&quot;]]"><video class="motion" src="figures/ch21-http-framing.mp4" autoplay loop muted playsinline preload="metadata" aria-label="A request's bytes stream into a buffer. The parser slides a window until it finds the blank line that ends the head, then splits the request line and headers into fields. With Content-Length: 5, a ruler counts five body bytes. With Transfer-Encoding: chunked, the parser reads a size line, takes that many bytes, and stops at the zero-size chunk. Last, one message carries both headers: a proxy frames it by Content-Length and sees one request, a back-end frames it by chunks and finds a hidden GET /admin after the body. The parser refuses the message with 400 and closes the connection." data-chapters="[[0.0, &quot;the head&quot;], [14.82, &quot;Content-Length&quot;], [26.22, &quot;chunked&quot;], [42.6, &quot;both&quot;]]"><img src="figures/ch21-http-framing.gif" alt="A request's bytes stream into a buffer. The parser slides a window until it finds the blank line that ends the head, then splits the request line and headers into fields. With Content-Length: 5, a ruler counts five body bytes. With Transfer-Encoding: chunked, the parser reads a size line, takes that many bytes, and stops at the zero-size chunk. Last, one message carries both headers: a proxy frames it by Content-Length and sees one request, a back-end frames it by chunks and finds a hidden GET /admin after the body. The parser refuses the message with 400 and closes the connection."></video></video>
<figcaption><b>Animation 21.1</b> How the head decides where the body ends, and what goes wrong when two programs decide differently.</figcaption>
</figure>

`parse_body` makes the decision. It collects both framing headers, and refuses a request that has both:

```rust
{{#include ../../rust-interview-lab/src/problems/http_request.rs:229:248}}
    // ...
}
```

Refusing ambiguous framing outright, and closing the connection, removes the disagreement.

A chunked body is accepted only in one shape:

```rust
fn parse_body(
    input: &[u8],
    body_start: usize,
    headers: &[(String, String)],
    limits: Limits,
) -> Result<Vec<u8>, ParseError> {
    // ...
{{#include ../../rust-interview-lab/src/problems/http_request.rs:250:268}}
    // ...
}
```

`Transfer-Encoding` values from every such header are joined and split into codings. The parser supports
only `chunked`, and requires it to be last, because a body whose final coding is not `chunked` has no
defined end. Anything else is `UnsupportedTransferEncoding`.

Otherwise the body is `Content-Length` bytes long, or empty:

```rust
fn parse_body(
    input: &[u8],
    body_start: usize,
    headers: &[(String, String)],
    limits: Limits,
) -> Result<Vec<u8>, ParseError> {
    // ...
{{#include ../../rust-interview-lab/src/problems/http_request.rs:270:291}}
}
```

Multiple `Content-Length` headers are allowed only if they all agree. The check compares with
`lengths.any(|length| length != Ok(first))`, comparing `Result`s directly. A length above `max_body_bytes`
is rejected *before* the server waits for the bytes. A client cannot claim a huge body and make the
server buffer it. If fewer bytes than the length have arrived, the result is `Incomplete`.

### 21.1.4 Chunked bodies

A chunked body is a list of records, `size-in-hex CRLF data CRLF`, that ends with a size of 0.
`decode_chunked` walks a cursor through them. Each record starts with its size line:

```rust
{{#include ../../rust-interview-lab/src/problems/http_request.rs:294:311}}
    // ...
}
}
```

Chunk extensions after a `;` are ignored, as the RFC permits. A size of zero ends the body, after optional
trailer lines up to an empty line:

```rust
fn decode_chunked(data: &[u8], max_body: usize) -> Result<Vec<u8>, ParseError> {
    // ...
    loop {
        // ...
{{#include ../../rust-interview-lab/src/problems/http_request.rs:313:323}}
        // ...
    }
}
```

Any other size is a chunk of data, checked against the limit and against what has arrived:

```rust
fn decode_chunked(data: &[u8], max_body: usize) -> Result<Vec<u8>, ParseError> {
    // ...
    loop {
        // ...
{{#include ../../rust-interview-lab/src/problems/http_request.rs:325:338}}
    }
}
```

The chunk's end is computed with `checked_add`. The result is `Incomplete` if the data has not all arrived,
and the CRLF after the data is required. The helper that finds each line end returns `None` for a cursor
past the end, rather than panicking:

```rust
{{#include ../../rust-interview-lab/src/problems/http_request.rs:342:347}}
```

One arithmetic detail needs tightening. `body.len() + size > max_body` runs before the `checked_add`, and a
chunk size near `usize::MAX` overflows that addition. `from_str_radix` will parse such a size from sixteen
`f`s. The form `size > max_body - body.len()` cannot overflow.

`parse_request` returns the request but not how many bytes it consumed. A caller therefore cannot find the
start of a second, pipelined request in the same buffer. The server below accepts that limitation and says
so.

## 21.2 A small REST server

The server is a loop around the parser. It reads bytes, asks the parser what it has, and answers. The
decision about *what* to answer lives in one function that never touches a socket. The complete file is
listing 21.2 in section 21.3.

### 21.2.1 Routing as a pure function

`route` takes a parsed request and returns the status, the content type, and the body. It starts with the
health check:

```rust
{{#include ../../rust-interview-lab/src/bin/http_server.rs:36:47}}
    // ...
}
```

A known path with an unsupported method returns 405. The collection path answers GET with a list and POST
with the created item:

```rust
pub fn route(request: &Request) -> (u16, &'static str, Vec<u8>) {
    // ...
{{#include ../../rust-interview-lab/src/bin/http_server.rs:49:63}}
    // ...
}
```

A path with an id uses `strip_prefix` to take the id. An empty id, or one containing `/`, is a 404, and so
is any path the function does not know:

```rust
pub fn route(request: &Request) -> (u16, &'static str, Vec<u8>) {
    // ...
{{#include ../../rust-interview-lab/src/bin/http_server.rs:65:80}}
}
```

Because `route` is pure, the tests at the bottom of the file exercise every route by building a `Request`
value directly, with no socket.

`build_response` turns the result into bytes:

```rust
{{#include ../../rust-interview-lab/src/bin/http_server.rs:100:116}}
```

It writes the status line, `Content-Length`, an optional `Content-Type`, and a `Connection` header that
tells the client what the server will do next.

### 21.2.2 The connection loop

`handle_connection` keeps one growing buffer of bytes, and asks the parser about it again after every read
(figure 21.3). TCP delivers bytes, not messages, so a request can arrive in several reads.

<figure>
<img src="figures/ch21-connection.svg" alt="State loop: parse; on Ok route and respond, then clear the buffer and loop if keep-alive or close; on Incomplete read more and parse again; on other errors send 400 and close">
<figcaption><b>Figure 21.3</b> The keep-alive loop in <code>handle_connection</code>.</figcaption>
</figure>

On `Ok`, the loop routes, writes the response, and either closes or clears the buffer for the next request:

```rust
{{#include ../../rust-interview-lab/src/bin/http_server.rs:134:152}}
    // ...
}
}
}
```

On `Incomplete`, it reads more. A read of 0 means the client left in the middle of a request. Any other
error gets a 400 whose body is the error's `Display` text, and the connection closes:

```rust
fn handle_connection(mut stream: TcpStream) -> std::io::Result<()> {
    // ...
    loop {
        match parse_request(&buffer, limits) {
            // ...
{{#include ../../rust-interview-lab/src/bin/http_server.rs:153:166}}
        }
    }
}
```

After a framing error the server cannot know where the next request starts, so closing is the only safe
answer.

<figure class="anim">
<video class="motion" src="figures/ch21-keep-alive.mp4" autoplay loop muted playsinline preload="metadata" aria-label="A client and the server's connection loop. The first request arrives in two reads: the first read leaves the parser with Incomplete, so the loop reads again, and the second read completes the head. The parser returns Ok, route answers 200, the response goes back with Connection: keep-alive, and the buffer is cleared. A second request on the same connection is routed the same way. Last, a request with both Content-Length and Transfer-Encoding gets 400 and the connection closes." data-chapters="[[0.0, &quot;two reads&quot;], [20.46, &quot;route&quot;], [31.02, &quot;keep-alive&quot;], [39.54, &quot;framing error&quot;]]"><video class="motion" src="figures/ch21-keep-alive.mp4" autoplay loop muted playsinline preload="metadata" aria-label="A client and the server's connection loop. The first request arrives in two reads: the first read leaves the parser with Incomplete, so the loop reads again, and the second read completes the head. The parser returns Ok, route answers 200, the response goes back with Connection: keep-alive, and the buffer is cleared. A second request on the same connection is routed the same way. Last, a request with both Content-Length and Transfer-Encoding gets 400 and the connection closes." data-chapters="[[0.0, &quot;two reads&quot;], [20.46, &quot;route&quot;], [31.02, &quot;keep-alive&quot;], [39.54, &quot;framing error&quot;]]"><img src="figures/ch21-keep-alive.gif" alt="A client and the server's connection loop. The first request arrives in two reads: the first read leaves the parser with Incomplete, so the loop reads again, and the second read completes the head. The parser returns Ok, route answers 200, the response goes back with Connection: keep-alive, and the buffer is cleared. A second request on the same connection is routed the same way. Last, a request with both Content-Length and Transfer-Encoding gets 400 and the connection closes."></video></video>
<figcaption><b>Animation 21.2</b> One connection, three requests: one that arrives in pieces, one that reuses the connection, and one that ends it.</figcaption>
</figure>

A session with `curl` and `nc` against the server, started with
`cargo run --bin http_server 127.0.0.1:18080`:

```text
$ curl -si http://127.0.0.1:18080/healthz
HTTP/1.1 200 OK
Content-Length: 3
Content-Type: text/plain
Connection: keep-alive

ok
$ curl -si -X POST -d '{"gpuCount":1}' http://127.0.0.1:18080/v1/gpu-workloads
HTTP/1.1 201 Created
Content-Length: 49
Content-Type: application/json
Connection: keep-alive

{"id":"wl-a100-2","gpuCount":1,"state":"Pending"}
$ printf 'POST / HTTP/1.1\r\nHost: x\r\nContent-Length: 5\r\nTransfer-Encoding: chunked\r\n\r\nhello' | nc 127.0.0.1 18080
HTTP/1.1 400 Bad Request
Content-Length: 59
Content-Type: text/plain
Connection: close

Content-Length and Transfer-Encoding are mutually exclusive
```

### 21.2.3 Reading the server against the RFC

The same session shows three places where the server departs from RFC 9110. None of them is hard to fix,
and finding them is good practice.

```text
$ curl -si -X DELETE http://127.0.0.1:18080/v1/gpu-workloads/wl-7
HTTP/1.1 204 No Content
Content-Length: 0
Connection: keep-alive

$ printf 'HEAD /healthz HTTP/1.1\r\nHost: x\r\nConnection: close\r\n\r\n' | nc 127.0.0.1 18080
HTTP/1.1 200 OK
Content-Length: 3
Content-Type: text/plain
Connection: close

ok
```

- **HEAD must not carry a body.** A HEAD response repeats the GET headers, including the
  `Content-Length` of a body it does not send. The server sends `ok`. A client that
  trusts the spec reads those three bytes as the start of the *next* response. The fix is one line in
  `handle_connection`: skip `body` when `request.method == Method::Head`.
- **204 must not carry `Content-Length`.** `build_response` always writes it. Skipping it for 204 (and
  1xx) fixes that.
- **Errors all become 400.** `PayloadTooLarge` deserves 413, and `status_reason` already has its text.
  Mapping `ParseError` to a status in one `match` fixes it. A 405 should also carry an `Allow` header
  listing the methods that path supports.

Two more points concern safety rather than the RFC. The id is interpolated into JSON with `format!`, so an
id containing `"` produces invalid JSON; a real server serializes with `serde_json`. And `buffer.clear()`
after each request discards any pipelined bytes that arrived with it, which the module comment
acknowledges.

## 21.3 The complete programs

The parser and the server, each as one file.

<p class="listing"><b>Listing 21.1</b> An HTTP/1.1 request parser with framing checks and limits. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/http_request.rs">src/problems/http_request.rs</a></p>

```rust
{{#include ../../rust-interview-lab/src/problems/http_request.rs}}
```

<p class="listing"><b>Listing 21.2</b> Routes, responses, and a keep-alive loop over <code>std::net</code>. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/bin/http_server.rs">src/bin/http_server.rs</a></p>

```rust
{{#include ../../rust-interview-lab/src/bin/http_server.rs}}
```

## 21.4 Questions that come up

**"How does a server know where an HTTP/1.1 request body ends?"**
`Transfer-Encoding: chunked` means read chunks until a zero-size chunk. Else `Content-Length` gives the
count. With neither header there is no body. For responses, closing the connection can also end the body.

**"What is request smuggling, and how do you prevent it?"**
Two servers frame the same bytes differently, so each sees a different message.
Reject requests with both framing headers. Reject conflicting `Content-Length`s. Close the
connection after any framing error.

**"How do you stop a client from exhausting your server's memory?"**
Limit header size and body size. Check the declared length before reading the body. Time out idle
and slow connections.

**"Why is routing a separate pure function?"**
So the rules are testable without sockets. The protocol code (framing, keep-alive) can then be changed
without touching the application logic.

**"What does HTTP/2 change?"**
Binary framing with explicit lengths, many concurrent streams on one connection, and header compression.
Framing ambiguity of the HTTP/1.1 kind disappears inside HTTP/2, although it can return where a proxy
downgrades to HTTP/1.1.
