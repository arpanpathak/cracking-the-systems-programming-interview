# 14. Network Protocols and the Socket Interface

Network communication is abstracted through the BSD socket interface, which exposes transport protocols through ordinary file descriptors while letting applications select between fundamentally different delivery contracts: reliable, ordered byte streams (TCP) and connectionless, boundary-preserving datagrams (UDP).

## 14.1 The Transmission Control Protocol (TCP): Reliable Byte Streams

The **Transmission Control Protocol (TCP)** provides a connection-oriented, reliable, full-duplex byte stream over an inherently unreliable packet-switched IP network that can drop, duplicate, reorder, or corrupt packets. TCP enforces reliability through cumulative byte **sequence numbers**, receiver **acknowledgments (ACKs)**, retransmission timers, sliding-window **flow control** (preventing a fast sender from overflowing a slow receiver's kernel buffer), and **congestion control** (adapting transmission rate to network path capacity).

Every TCP connection traverses two control phases around its data transfer:
- **Three-Way Handshake (Establishment):** The client transmits `SYN` with an initial sequence number; the server responds with `SYN-ACK`; the client replies with `ACK`. Only after this round trip completes do `connect()` and `accept()` succeed.
- **Graceful Teardown:** Each direction closes independently via `FIN` and `ACK` segments (half-close), allowing buffered in-flight data to drain cleanly before the endpoint enters `TIME_WAIT` and releases the port.

Because TCP treats transmitted data as an unstructured sequence of bytes, it does **not** preserve `write()` boundaries: three 10-byte writes may arrive as a single 30-byte `read()` or thirty 1-byte reads. Every application protocol layered over TCP (HTTP, TLS, gRPC, PostgreSQL wire protocol) must therefore define explicit framing, such as length prefixes or delimiters.

<figure>
<img src="figures/ch14_tcp.svg" alt="The TCP handshake, data exchange with sequence numbers, and FIN teardown"/>
</figure>

## 14.2 The User Datagram Protocol (UDP): Unreliable Message Delivery

The **User Datagram Protocol (UDP)** strips away connection state, handshakes, retransmissions, and ordering guarantees, adding only 8 bytes of header (source port, destination port, length, and checksum) atop raw IP packets. Each UDP datagram is routed independently and may arrive out of order, arrive duplicated, or vanish silently in transit.

This minimal contract yields two major engineering properties:
- **Zero handshake latency and no head-of-line blocking:** Sending the first payload incurs zero setup round trips, and losing one packet never stalls subsequent packets waiting behind it. Real-time voice/video pipelines, DNS resolvers, telemetry collectors, and modern QUIC (HTTP/3) transports build directly on UDP.
- **Strict message-boundary preservation:** Unlike TCP streams, one `sendto()` call produces exactly one discrete datagram delivered atomically by one `recvfrom()` call.

### 14.2.1 The Connectionless Datagram System Call Interface (`sendto`, `recvfrom`)

Because a UDP socket (`socket(AF_INET, SOCK_DGRAM, 0)`) does not maintain a fixed peer connection, each transmission and reception carries its own endpoint address explicitly:

```text
ssize_t sendto(int sockfd, const void *buf, size_t len, int flags,
               const struct sockaddr *dest_addr, socklen_t addrlen);

ssize_t recvfrom(int sockfd, void *buf, size_t len, int flags,
                 struct sockaddr *src_addr, socklen_t *addrlen);
```

- **`sockfd`:** A `SOCK_DGRAM` file descriptor. Calling `bind()` assigns a local port (such as `45680` in Listing 14-1) so peers know where to address datagrams; an unbound socket sending via `sendto()` receives an ephemeral port automatically from the kernel.
- **`buf` and `len`:** User-space payload buffer and its byte length.
- **`flags`:** Per-operation bitmask (`0` for standard blocking transfer; `MSG_DONTWAIT` for non-blocking single-call I/O; `MSG_PEEK` to inspect a queued datagram without removing it from the receive buffer).
- **`dest_addr` and `addrlen` (in `sendto`):** Pointer to the destination `struct sockaddr_in` (or `sockaddr_in6`) and its exact byte size passed **by value** (`sizeof addr`).
- **`src_addr` and `addrlen` (in `recvfrom`):** Output parameters allowing the kernel to populate the sender's IP address and port. Notice that **`addrlen` is passed by pointer (`socklen_t *`)** as a value-result argument: the caller initializes `*addrlen` to the buffer capacity (for example, `sizeof(struct sockaddr_storage)`) before the call, and the kernel overwrites `*addrlen` with the actual address length written. Passing `nullptr, nullptr` (as in Listing 14-1) tells the kernel the caller does not need the sender's address.
- **Return values and truncation hazard:** Both functions return the signed number of bytes sent or received (`ssize_t >= 0`), or `-1` on error (`EMSGSIZE` if a datagram exceeds the link MTU/limit, `EAGAIN` on non-blocking empty receive, `EINTR`). Crucially, if an arriving UDP datagram is larger than the `len` buffer supplied to `recvfrom()`, the kernel copies the first `len` bytes and **silently discards the remaining tail of the datagram** (unlike TCP `read()`, which leaves unread bytes queued for the next call).

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

Applications operate on human-readable hostnames (`"localhost"`, `"api.example.com"`) and service names (`"https"`, `"443"`), whereas `connect()` and `bind()` require binary IPv4 (`sockaddr_in`) or IPv6 (`sockaddr_in6`) structures. Modern POSIX software replaces legacy IPv4-only functions (`gethostbyname`) with the re-entrant, protocol-independent resolver **`getaddrinfo(3)`**.

### 14.3.1 Protocol-Independent Resolution (`struct addrinfo`, `getaddrinfo`, `freeaddrinfo`, `inet_ntop`)

```text
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

- **Filtering via `hints`:** Callers zero-initialize a `struct addrinfo hints{}` and populate only the constraint fields they care about: setting **`ai_family = AF_UNSPEC`** accepts both IPv4 and IPv6 addresses, while **`ai_socktype = SOCK_STREAM`** restricts results to stream (TCP) endpoints so each IP address is not duplicated for both TCP and UDP. For server `bind()` lookups, setting `ai_flags = AI_PASSIVE` with `node = nullptr` produces wildcard listen addresses (`0.0.0.0` / `::`).
- **`getaddrinfo(node, service, hints, res)`:** Queries `/etc/hosts` and configured DNS resolvers for hostname `node` (e.g., `"localhost"`) and optional port/service string `service` (`nullptr` when inspecting addresses without a port). On success it allocates a linked list of `struct addrinfo` nodes on the heap, writes the head pointer into `*res`, and returns **`0`**.
  - **Dedicated error codes (`gai_strerror`):** Unlike raw system calls, `getaddrinfo()` does **not** return `-1` with `errno`. On failure it returns a specific non-zero resolver code (`EAI_NONAME`, `EAI_AGAIN`, `EAI_MEMORY`), which callers must translate via **`gai_strerror(rc)`** rather than `perror()`.
- **Traversing and freeing (`ai_next` and `freeaddrinfo`):** Because a hostname commonly resolves to both IPv6 (`::1`) and IPv4 (`127.0.0.1`) endpoints, callers iterate `for (addrinfo *ai = list; ai != nullptr; ai = ai->ai_next)`, inspecting `ai->ai_family` to safely cast `ai->ai_addr` to either `sockaddr_in *` or `sockaddr_in6 *`. Once finished, the caller **must** invoke **`freeaddrinfo(list)`** to release the entire heap-allocated linked list.
- **`inet_ntop(af, src, dst, size)` ("network to presentation"):** Converts a binary network-order address pointer (`&sin_addr` for `AF_INET`, or `&sin6_addr` for `AF_INET6`) into a null-terminated text string inside `dst`. Sizing `dst` to **`INET6_ADDRSTRLEN`** (46 bytes) guarantees sufficient capacity for both IPv4 dotted-quad (`127.0.0.1`) and full IPv6 colon-hex (`::1`) representations. Returns `dst` on success or `nullptr` on error (`EAFNOSUPPORT`, `ENOSPC`).

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
