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

<p class="listing"><span class="listing-label">Listing 54.1</span> The complete module, with its tests. <code>src/problems/http_request.rs</code> &middot; <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/rust-interview-lab/src/problems/http_request.rs">read the file on GitHub</a></p>

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
