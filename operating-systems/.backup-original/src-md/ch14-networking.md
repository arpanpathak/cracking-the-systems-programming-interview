# 14. Sockets and the Network Stack

A socket is a descriptor that reaches another machine. Everything
Chapter 13 waited on — data arriving, peers closing — becomes, on a
socket, the arrival of packets and the end of a TCP connection. This
chapter builds the two socket types from their system calls: the
connection-oriented stream over TCP, with its handshake and byte
ordering, and the connectionless datagram over UDP, with neither.

<div class="callout glance">
<span class="label">At a glance</span>

- TCP is a byte stream with a handshake, ordering, retransmission, and
  four-segment teardown; sockets expose it as read and write.
- UDP is a datagram with no handshake and no guarantees; sockets
  expose it as send and receive.
- Names resolve to addresses through the resolver; IPv4 and IPv6 both
  arrive, and the program tries them in order.

</div>

## 14.1 TCP: a stream with a contract

Chapter 13's echo server already used TCP sockets; this chapter names
the contract the kernel was keeping. A TCP connection is a byte stream
between two endpoints. The kernel numbers every byte, retransmits what
the peer did not acknowledge, reorders what arrived out of order, and
drops nothing silently. What the program writes arrives, in order,
once — or the connection breaks with an error.

The contract is bought with a handshake and a teardown, drawn in
Figure 14-1.

<figure>
<img src="diagrams/ch14_tcp.svg" alt="The TCP handshake, data exchange with sequence numbers, and FIN teardown"/>
</figure>

The system calls map onto the figure one for one. The server calls
`bind` to name its address, `listen` to declare willingness, `accept`
to receive a connection — the SYN from a client wakes the accept.
The client calls `connect`, which performs the three segments of the
handshake before returning. Both sides then `read` and `write` byte
streams. `close` performs the FIN exchange; either side can close
first, and the other's `read` then returns zero — the same
end-of-stream Chapter 11's pipe produced, now from a remote peer.

The sequence numbers in the figure deserve one precise sentence:
they count bytes, not messages. A `write` of 100 bytes followed by a
`write` of 50 may arrive at the reader as one `read` of 150, three
`read`s of 60, 20, and 70, or any other partition — TCP promises
order and completeness, never chunking. Every TCP protocol therefore
carries its own message framing, exactly as the pipe warning in
Chapter 11 prescribed.

## 14.2 UDP: a datagram, no contract

UDP is the alternative. A datagram is a single packet's worth of
bytes, addressed and sent; the kernel attempts delivery and promises
nothing further. No handshake, no ordering, no retransmission — a
datagram arrives whole or not at all. The socket interface matches:
`sendto` and `recvfrom` carry the peer's address on every call, and
one send is one receive, boundaries preserved.

**Listing 14-1. A datagram sent to the loopback address and read back (C++20).**

```cpp
{{#include ../code/ch14/udp.cpp}}
```

**Output 14-1. Eight bytes in, eight bytes out, one datagram.**

```text
{{#include ../code/out/ch14_udp.out}}
```

**Listing 14-2. The same round trip with `std::net::UdpSocket` (Rust).**

```rust
{{#include ../code/ch14/udp.rs}}
```

**Output 14-2.**

```text
{{#include ../code/out/ch14_udp_rs.out}}
```

The honest division of labor: UDP is for workloads that prefer the
application to own retransmission and ordering — real-time media,
service discovery, telemetry where a lost sample is cheaper than a
stalled stream. TCP is for workloads that want the kernel to own
them — everything else. The two are not competitors; production
systems commonly run both, TCP for control, UDP for data.

<div class="callout keyidea">
<span class="label">Key idea</span>

TCP trades latency for guarantees: handshake before data,
acknowledgments after, retransmission on loss. UDP trades guarantees
for latency: send and hope. The socket interface exposes both as the
same object — a descriptor — with different calls and different
promises.

</div>

## 14.3 Names to addresses

Programs name hosts; the network names addresses. The resolver is the
translation, and the correct pattern is to iterate everything it
returns.

**Listing 14-3. What the resolver returns for "localhost" (C++20).**

```cpp
{{#include ../code/ch14/getaddrinfo.cpp}}
```

**Output 14-3. IPv6 first on this machine; IPv4 second.**

```text
{{#include ../code/out/ch14_getaddrinfo.out}}
```

**Listing 14-4. The Rust equivalent in one line of interface.**

```rust
{{#include ../code/ch14/to_socket_addrs.rs}}
```

**Output 14-4.**

```text
{{#include ../code/out/ch14_to_socket_addrs_rs.out}}
```

A name can resolve to several addresses — both families here, many
addresses for large services. The connect pattern is therefore a
loop: resolve once, try each address in order, keep the first that
connects. Programs that take the first address and give up fail on
machines where only one family is reachable — the most common
networking bug in deployed clients, and the reason both languages
make the full list the return value.

<div class="callout caution">
<span class="label">Watch out</span>

Three socket behaviors that surprise in production. A `write` may
accept fewer bytes than given — the loop from Chapter 11 applies to
sockets too. A `read` may return fewer bytes than a message — framing
is the protocol's job. And a peer that disappears without closing
leaves the connection half-open until a keepalive or a timeout
notices; every long-lived connection needs both a deadline and a
heartbeat.

</div>

<div class="callout summary">
<span class="label">Summary</span>

- TCP is a byte stream with a three-segment handshake, per-byte
  acknowledgments, and a FIN teardown; the socket interface is
  read/write plus the connection calls.
- UDP is a datagram with boundaries and no guarantees; one send is one
  receive.
- Sequence numbers count bytes; message framing always belongs to the
  protocol.
- Resolution returns a list; connect tries every address in it.
- The socket is the event loop's input in Chapter 13, and the
  daemon's control channel in the next chapter — the descriptor
  abstraction, extended to the network.

</div>
