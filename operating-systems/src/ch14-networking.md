# 14. Network Protocols and the Socket Interface

Network communication is abstracted through the socket interface, which provides a standardized mechanism for processes to exchange data across local or remote hosts. While the underlying network may be unreliable, the socket API allows applications to choose between different transport protocols, primarily TCP and UDP, depending on their requirements for reliability, ordering, and latency.

## 14.1 The Transmission Control Protocol (TCP): Reliable Byte Streams

The Transmission Control Protocol (TCP) provides a robust, connection-oriented abstraction that presents the network as a reliable, ordered stream of bytes. To overcome the inherent unreliability of the underlying network (such as packet loss, duplication, or out-of-order delivery), TCP employs sequence numbers and acknowledgment mechanisms. By tracking the exact byte offset of every transmitted segment, the protocol can reassemble data in the correct order, discard duplicates, and retransmit lost segments, ensuring that the application perceives a seamless and continuous stream.

Establishing and terminating a TCP connection involves a structured exchange of control segments:
- **Connection Establishment:** A three-way handshake (SYN, SYN-ACK, ACK) synchronizes sequence numbers and establishes the connection state.
- **Connection Teardown:** The termination process utilizes FIN segments to signal the end of the stream, allowing both sides to gracefully conclude communication.

From a programming perspective, TCP operations are managed through a specific sequence of system calls: `bind` and `listen` prepare a server to accept connections; `connect` initiates a client-side handshake; and `accept` generates a new file descriptor for an established connection. A critical implementation detail is that TCP, being a stream-oriented protocol, does not preserve application-level message boundaries. Consequently, any protocol layered atop TCP must implement its own framing mechanism, such as length-prefixing or delimiters, to reconstruct discrete messages from the continuous byte stream.

<figure>
<img src="figures/ch14_tcp.svg" alt="The TCP handshake, data exchange with sequence numbers, and FIN teardown"/>
</figure>

## 14.2 The User Datagram Protocol (UDP): Unreliable Message Delivery

In contrast to the complexity of TCP, the User Datagram Protocol (UDP) provides a minimalist, connectionless service. Communication via UDP is centered around discrete datagrams, each of which is sent independently with its own destination address. Unlike TCP, UDP provides no guarantees regarding delivery, ordering, or integrity; a datagram may be lost, duplicated, or arrive out of sequence.

The primary advantage of UDP is its low latency and reduced overhead, as it avoids the handshake and acknowledgment cycles required by TCP. This makes it ideal for real-time applications (such as voice or video streaming) where late data is useless, or for short, transactional exchanges (such as DNS queries) where the cost of a handshake would exceed the cost of the data transfer itself. Furthermore, UDP preserves message boundaries: a single `sendto` call corresponds to exactly one `recvfrom` call, simplifying the application-level framing requirements.

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

While network communication occurs via numeric IP addresses, practical applications utilize human-readable hostnames. Name resolution is the process of translating these names into a list of compatible network addresses (typically encompassing both IPv4 and IPv6). Using standardized interfaces like `getaddrinfo`, applications can iterate through the returned address list to attempt connection to the first available endpoint, ensuring compatibility across diverse network environments.

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
