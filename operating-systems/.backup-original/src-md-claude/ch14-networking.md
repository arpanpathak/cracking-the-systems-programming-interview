# 14. Sockets and the Network Stack

A **socket** is a file descriptor that represents one end of a network
connection. The echo servers of Chapter 13 already used sockets, but we
did not yet explain what the kernel does when a program reads from one or
writes to one.

In this chapter, we describe the two most common kinds of sockets. A TCP
socket provides a reliable stream of bytes between two programs. A UDP
socket sends and receives separate messages, with no guarantee of
delivery. We also show how a program translates a host name into network
addresses.

<div class="callout glance">
<span class="label">This chapter covers</span>

- what TCP guarantees, and how a connection is opened and closed
- `bind`, `listen`, `accept`, and `connect`
- sequence numbers, and why TCP needs message framing
- UDP datagrams, `sendto`, and `recvfrom`
- when to choose TCP and when UDP
- name resolution with `getaddrinfo`

</div>

## 14.1 TCP

The **Transmission Control Protocol** (TCP) provides a connection between
two programs that carries a stream of bytes in each direction. The
network underneath can lose packets, duplicate them, and deliver them out
of order, and the TCP implementation in the kernel corrects all three
problems. It assigns a number to every byte. The receiver acknowledges the
bytes it has received, and the sender transmits again any bytes that are
not acknowledged in time. The receiver uses the numbers to put the bytes
in order and to discard duplicates. As a result, the bytes that one
program writes arrive at the other program completely, in order, and
once. If that becomes impossible, for example because the network path
fails, the connection ends with an error.

Before any data can flow, the two sides exchange three segments, called
the **three-way handshake**. When the connection is no longer needed,
further segments close it. Figure 14-1 shows a connection from handshake
to close.

<figure>
<img src="figures/ch14_tcp.svg" alt="The TCP handshake, data exchange with sequence numbers, and FIN teardown"/>
</figure>

The system calls of a program correspond to parts of this figure.

- A server calls `bind` to attach its socket to an address and a port, and
  `listen` to declare that it accepts connections on that socket.
- A client calls `connect`. The kernel of the client sends the SYN segment
  and completes the handshake with the kernel of the server before
  `connect` returns.
- The server calls `accept`, which returns a new descriptor for a
  connection whose handshake has completed.
- Both sides then call `read` and `write`.
- Either side calls `close`, and its kernel sends a FIN segment. A `read`
  on the other side then returns 0, which signals the end of the stream,
  as it does for a pipe in Chapter 11.

The sequence numbers in Figure 14-1 count bytes, not `write` calls. TCP
does not preserve the boundaries between writes. If a sender calls `write`
with 100 bytes and then with 50 bytes, the receiver may obtain all 150
bytes from one `read`, or it may obtain 60, 20, and 70 bytes from three.
A protocol on top of TCP must therefore add its own framing, as we
discussed for pipes in Chapter 11.

## 14.2 UDP

The **User Datagram Protocol** (UDP) is much simpler. A program sends a
**datagram**, a single message with a destination address, and the kernel
transmits it once. UDP has no handshake, no acknowledgments, and no
retransmission. A datagram may be lost, may arrive twice, or may arrive
after a datagram that was sent later. A datagram that does arrive is
complete, however, so UDP preserves message boundaries. One `sendto` call
on the sender corresponds to one `recvfrom` call on the receiver.

Listing 14-1 creates a UDP socket and binds it to the loopback address
127.0.0.1. It then sends one datagram to its own address and prints what
it receives.

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

The choice between the two protocols depends on what an application needs.
TCP suits applications that need every byte to arrive in order, such as
file transfer, web pages, and database connections. UDP suits applications
in which late data has no value. In a voice call, for example, playing the
next sound sample on time is more useful than waiting for a
retransmission of a lost one. UDP is also used for short exchanges such
as DNS queries, in which a handshake would take longer than the exchange
itself. Many systems use both protocols.

<div class="callout keyidea">
<span class="label">Key idea</span>

TCP delivers a byte stream completely and in order, at the cost of a
handshake and retransmissions. UDP delivers separate datagrams with less
delay and no guarantees. A program uses both through socket descriptors.

</div>

## 14.3 From names to addresses

Programs usually identify a host by a name, such as `example.com`, whereas
the network requires a numeric address. The translation is called *name
resolution*. In C and C++, the function `getaddrinfo` performs it and
returns a list of addresses.

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

On the verification machine, the name `localhost` resolves to two
addresses: the IPv6 address `::1` and the IPv4 address `127.0.0.1`. The
name of a large service can resolve to many more. A client should try the
addresses in the order returned and use the first one to which `connect`
succeeds. A client that tries only the first address fails on a machine
that cannot reach that address family, even when another address in the
list would have worked.

<div class="callout caution">
<span class="label">Watch out</span>

Three properties of sockets are often overlooked.

- A `write` may accept fewer bytes than the program passed. The program
  must write the rest in a loop.
- A `read` may return only part of a message. The program must apply the
  framing of its protocol to find where the message ends.
- If the other host crashes or loses its network connection, no FIN
  arrives, and a `read` can block forever. A connection that stays open
  for a long time needs a timeout, and often periodic keepalive messages
  as well.

</div>

<div class="callout summary">
<span class="label">Summary</span>

- TCP provides a reliable byte stream. A connection opens with a
  three-way handshake and closes with FIN segments.
- TCP sequence numbers count bytes. TCP does not preserve message
  boundaries, so a protocol must frame its messages.
- UDP sends separate datagrams with no handshake and no guarantee of
  delivery or order. Each datagram arrives whole or not at all.
- Name resolution returns a list of addresses, and a client should try
  each of them.

In Chapter 15, we write a daemon, a program that runs in the background
without a terminal.

</div>
