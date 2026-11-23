# 14. Network Protocols and the Socket Interface

Network communication is abstracted through the **Berkeley Software Distribution (`BSD`)** socket interface, which exposes transport protocols through ordinary file descriptors while letting applications choose between fundamentally different delivery contracts: reliable, ordered byte streams (**Transmission Control Protocol (`TCP`)**) and connectionless, boundary-preserving datagrams (**User Datagram Protocol (`UDP`)**).

## 14.1 The Transmission Control Protocol (`TCP`): Reliable Byte Streams

`TCP` provides a connection-oriented, reliable, full-duplex byte stream over an inherently unreliable packet-switched **Internet Protocol (`IP`)** network that can drop, duplicate, reorder, or corrupt packets. `TCP` enforces reliability through cumulative byte **sequence numbers**, receiver **Acknowledgments (`ACK`s)**, retransmission timers, sliding-window **flow control** (preventing a fast sender from overflowing a slow receiver's kernel buffer), and **congestion control** (adapting transmission rate to bottleneck link capacity).

Every `TCP` connection traverses two control phases around its data transfer (Figure 14-1). During the **Three-Way Handshake**, the client transmits a **Synchronize (`SYN`)** segment carrying an initial sequence number, the server replies with **`SYN-ACK`**, and the client returns **`ACK`**; only after this round trip completes do `connect()` and `accept()` succeed. During **Graceful Teardown**, each direction closes independently via **Finish (`FIN`)** and `ACK` segments (half-close), allowing in-flight data to drain cleanly. The endpoint performing the active close then enters **`TIME_WAIT`** for twice the maximum segment lifetime (typically 30 to 120 seconds) for two subtle reasons: to ensure its final `ACK` can be retransmitted if lost, and to prevent delayed duplicate packets from an old connection from being misinterpreted by a newly opened connection reusing the same `(IP, port)` four-tuple.

Because `TCP` treats transmitted data as an unstructured sequence of bytes, it never preserves `write()` boundaries: three 10-byte writes may arrive as a single 30-byte `read()` or thirty 1-byte reads. Every application protocol layered over `TCP` (including **Hypertext Transfer Protocol (`HTTP`)**, **Transport Layer Security (`TLS`)**, **gRPC Remote Procedure Calls (`gRPC`)**, and the PostgreSQL wire protocol) must therefore define explicit framing such as length prefixes or delimiters.

<figure>
<img src="figures/ch14_tcp.svg" alt="The TCP handshake, data exchange with sequence numbers, and FIN teardown"/>
</figure>

## 14.2 The User Datagram Protocol (`UDP`): Unreliable Message Delivery

`UDP` strips away connection state, handshakes, retransmissions, and ordering guarantees, adding only an 8-byte header (source port, destination port, length, and checksum) atop raw `IP` packets. Each `UDP` datagram is routed independently and may arrive out of order, arrive duplicated, or vanish in transit without notification.

This minimal contract yields two defining engineering properties. First, it eliminates handshake latency and head-of-line blocking: transmitting the first payload incurs zero setup round trips, and losing one packet never stalls subsequent packets waiting behind it. Real-time voice and video pipelines, **Domain Name System (`DNS`)** resolvers, telemetry collectors, and modern **Quick UDP Internet Connections (`QUIC`)** transports (powering `HTTP/3`) build directly on `UDP`. Second, `UDP` enforces strict message-boundary preservation: one `sendto()` call produces one discrete datagram delivered atomically by one `recvfrom()` call.

### 14.2.1 The Connectionless Datagram System Call Interface (`sendto`, `recvfrom`)

Because a `UDP` socket (`socket(AF_INET, SOCK_DGRAM, 0)`) maintains no fixed peer connection, every transmission and reception carries its endpoint address explicitly:

```c
ssize_t sendto(int sockfd, const void *buf, size_t len, int flags,
               const struct sockaddr *dest_addr, socklen_t addrlen);

ssize_t recvfrom(int sockfd, void *buf, size_t len, int flags,
                 struct sockaddr *src_addr, socklen_t *addrlen);
```

In both calls, `sockfd` is a `SOCK_DGRAM` descriptor (calling `bind()` assigns a fixed local port such as `45680` in Listing 14-1, whereas an unbound sender automatically receives an ephemeral port), `buf` and `len` specify the payload buffer, and `flags` controls per-call behavior (`0` for standard blocking **Input/Output (`I/O`)**, `MSG_DONTWAIT` for non-blocking execution, or `MSG_PEEK` to inspect a queued datagram without dequeuing it). In `sendto()`, `dest_addr` points to the target `struct sockaddr_in` (or `sockaddr_in6`) and `addrlen` is passed **by value** (`sizeof addr`). In `recvfrom()`, `src_addr` and `addrlen` are output parameters receiving the sender's address, so `addrlen` is passed **by pointer (`socklen_t *`)** as a value-result argument: the caller initializes `*addrlen` to the buffer capacity before the call, and the kernel overwrites it with the actual length written (passing `nullptr, nullptr` discards the sender's address).

Both functions return the signed byte count transferred (`ssize_t >= 0`), or `-1` on error (`EMSGSIZE` if a datagram exceeds the link's **Maximum Transmission Unit (`MTU`)** limit, `EAGAIN` on non-blocking empty receive, or `EINTR`). Unlike `TCP` `read()`, which leaves unread bytes queued for the next call, if an arriving `UDP` datagram exceeds the `len` buffer supplied to `recvfrom()`, the kernel copies the first `len` bytes and **discards the remaining tail without signaling an error**.

**Listing 14-1. Sending and receiving one datagram (C++20).**

```cpp
{{#include ../code/ch14/udp.cpp}}
```

**Output 14-1. One datagram of 8 bytes.**

```text
{{#include ../code/out/ch14_udp.out}}
```

**Listing 14-2. The same exchange with `std::net::UdpSocket` (Rust).**

```rust
{{#include ../code/ch14/udp.rs}}
```

**Output 14-2.**

```text
{{#include ../code/out/ch14_udp_rs.out}}
```

## 14.3 Name Resolution and Addressing

Applications operate on human-readable hostnames (`"localhost"`, `"api.example.com"`) and service names (`"https"`, `"443"`), whereas `connect()` and `bind()` require binary **Internet Protocol Version 4 (`IPv4`, `sockaddr_in`)** or **Internet Protocol Version 6 (`IPv6`, `sockaddr_in6`)** structures. Modern **Portable Operating System Interface (`POSIX`)** software replaces legacy `IPv4`-only functions (`gethostbyname`) with the re-entrant, protocol-independent resolver **`getaddrinfo(3)`**.

### 14.3.1 Protocol-Independent Resolution (`getaddrinfo`, `freeaddrinfo`, `inet_ntop`)

```c
struct addrinfo {
    int              ai_flags;     // Input options (e.g., AI_PASSIVE, AI_NUMERICHOST)
    int              ai_family;    // AF_UNSPEC (IPv4 or IPv6), AF_INET, or AF_INET6
    int              ai_socktype;  // SOCK_STREAM (TCP), SOCK_DGRAM (UDP), or 0 (any)
    int              ai_protocol;  // Protocol number or 0 (any matching protocol)
    socklen_t        ai_addrlen;   // Byte length of the socket address in ai_addr
    struct sockaddr *ai_addr;      // Pointer to populated sockaddr_in or sockaddr_in6
    char            *ai_canonname; // Canonical hostname (when AI_CANONNAME requested)
    struct addrinfo *ai_next;      // Next candidate in the singly-linked result list
};

int         getaddrinfo(const char *node, const char *service,
                        const struct addrinfo *hints, struct addrinfo **res);
void        freeaddrinfo(struct addrinfo *res);
const char *gai_strerror(int errcode);
const char *inet_ntop(int af, const void *src, char *dst, socklen_t size);
```

Callers zero-initialize a `struct addrinfo hints{}` and populate only the constraints they require: `ai_family = AF_UNSPEC` accepts both `IPv4` and `IPv6`, `ai_socktype = SOCK_STREAM` restricts results to `TCP` endpoints so each address is not duplicated for `UDP`, and `ai_flags = AI_PASSIVE` with `node = nullptr` yields wildcard server listen addresses (`0.0.0.0` and `::`). Calling `getaddrinfo(node, service, hints, res)` queries `/etc/hosts` and configured `DNS` resolvers, allocates a heap-resident singly-linked list of candidate `struct addrinfo` nodes in `*res`, and returns `0` on success. Unlike raw system calls, failures return a dedicated non-zero resolver code (`EAI_NONAME`, `EAI_AGAIN`, `EAI_MEMORY`) that callers decode with `gai_strerror(rc)` rather than `perror()`.

Because a hostname commonly resolves to both `IPv6` (`::1`) and `IPv4` (`127.0.0.1`) endpoints, callers traverse the linked list via `ai->ai_next`, inspect `ai->ai_family` to cast `ai->ai_addr` safely to `sockaddr_in *` or `sockaddr_in6 *`, and release the entire list with `freeaddrinfo(list)`. To format a binary network-order address into text, `inet_ntop(af, src, dst, size)` ("network to presentation") writes a null-terminated string into `dst`; sizing `dst` to `INET6_ADDRSTRLEN` (46 bytes) guarantees sufficient capacity for both `IPv4` dotted-quad and full `IPv6` colon-hex strings.

**Listing 14-3. The addresses that `getaddrinfo` returns for "localhost" (C++20).**

```cpp
{{#include ../code/ch14/getaddrinfo.cpp}}
```

**Output 14-3. One IPv6 address and one IPv4 address.**

```text
{{#include ../code/out/ch14_getaddrinfo.out}}
```

**Listing 14-4. The same lookup in Rust, with `to_socket_addrs`.**

```rust
{{#include ../code/ch14/to_socket_addrs.rs}}
```

**Output 14-4.**

```text
{{#include ../code/out/ch14_to_socket_addrs_rs.out}}
```

<div class="callout keyidea">
<span class="label">Key idea</span>

`TCP` delivers a reliable, ordered byte stream with zero message-boundary preservation; `UDP` delivers discrete, boundary-preserving datagrams with zero reliability or ordering guarantees. Every protocol above `TCP` must therefore frame its own messages, while protocols above `UDP` (such as `QUIC`) implement custom reliability without head-of-line blocking.

</div>

<div class="callout experiment">
<span class="label">Experiment</span>

In Listing 14-1 (`code/ch14/udp.cpp`), shrink the receiver buffer `char buf[4]` while sending the 8-byte `"ping-udp"` payload. Observe `recvfrom()` returning `4` bytes and discarding the remaining 4 bytes without returning an error, contrasting sharply with `TCP` stream buffering.

</div>

<div class="callout caution">
<span class="label">Common Pitfall</span>

Assuming a single `read()` on a `TCP` socket returns one complete application message or forgetting to call `freeaddrinfo()` after `getaddrinfo()`. Under network fragmentation or kernel coalescing, a single `TCP` `read()` may return half a header or three concatenated messages.

</div>
