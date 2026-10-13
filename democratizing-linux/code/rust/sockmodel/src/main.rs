//! Models the receiving side of TCP in the kernel: a table of connections
//! keyed by addresses and ports, listeners with an accept queue of limited
//! length, and a receive buffer whose free space is the window offered to the
//! sender.
//!
//! Run it from code/rust with:
//!
//! ```text
//! cargo run -p sockmodel
//! ```

// ANCHOR: imports
use std::collections::{HashMap, VecDeque};
use std::fmt;
// ANCHOR_END: imports

// ANCHOR: types
/// An IP address and a port.
#[derive(Clone, Copy, PartialEq, Eq, Hash)]
struct Endpoint {
    address: &'static str,
    port: u16,
}

impl fmt::Display for Endpoint {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}:{}", self.address, self.port)
    }
}

/// One established connection: the bytes received and not yet read, the size
/// of the receive buffer, and whether the sender has finished.
struct Socket {
    received: VecDeque<u8>,
    capacity: usize,
    finished: bool,
}

impl Socket {
    /// The free space of the receive buffer: the number of bytes the sender
    /// may still send.
    fn window(&self) -> usize {
        self.capacity - self.received.len()
    }
}

/// Identifies a connection on this machine: the remote endpoint and the local
/// port. With the local address, which the model leaves out, it forms the 4
/// values that identify a TCP connection.
#[derive(Clone, Copy, PartialEq, Eq, Hash)]
struct Key {
    remote: Endpoint,
    port: u16,
}

/// Accepts connections on a port. `queue` holds the connections that are
/// established and have not been returned by accept.
struct Listener {
    backlog: usize,
    queue: VecDeque<Key>,
}

/// The TCP state of a machine.
struct Stack {
    listeners: HashMap<u16, Listener>,
    connections: HashMap<Key, Socket>,
    buffer_size: usize,
}

/// A packet of TCP. `syn` opens a connection and `fin` ends the sender's
/// stream.
#[derive(Default)]
struct Segment {
    syn: bool,
    fin: bool,
    data: &'static str,
}
// ANCHOR_END: types

// ANCHOR: receive
impl Stack {
    /// Handles a segment that arrives from `from` for local port `port`, and
    /// describes the result. A segment belongs to the connection with its
    /// remote endpoint and local port. Only when no such connection exists,
    /// and the segment is a SYN, is the listener on the port consulted.
    fn receive(&mut self, from: Endpoint, port: u16, segment: &Segment) -> String {
        let id = Key { remote: from, port };

        if let Some(socket) = self.connections.get_mut(&id) {
            return socket.deliver(segment);
        }

        if !segment.syn {
            return "reset, no connection".into();
        }

        let Some(listener) = self.listeners.get_mut(&port) else {
            return "reset, no listener on the port".into();
        };

        if listener.queue.len() == listener.backlog {
            return "dropped, the accept queue is full".into();
        }

        let socket = Socket {
            received: VecDeque::new(),
            capacity: self.buffer_size,
            finished: false,
        };

        self.connections.insert(id, socket);
        listener.queue.push_back(id);

        format!("established, accept queue {}", listener.queue.len())
    }
}

impl Socket {
    /// Puts the data of a segment into the receive buffer, up to the window,
    /// and records a FIN.
    fn deliver(&mut self, segment: &Segment) -> String {
        if segment.fin {
            self.finished = true;

            return "the sender's stream has ended".into();
        }

        let accepted = segment.data.len().min(self.window());
        self.received.extend(&segment.data.as_bytes()[..accepted]);

        format!("accepted {accepted}, window {}", self.window())
    }
}
// ANCHOR_END: receive

// ANCHOR: calls
impl Stack {
    /// Removes the oldest connection from the accept queue of a port.
    fn accept(&mut self, port: u16) -> Option<Key> {
        self.listeners.get_mut(&port)?.queue.pop_front()
    }
}

impl Socket {
    /// Removes up to `n` bytes from the receive buffer. It returns 0 bytes
    /// with the second value set when the buffer is empty and a FIN has
    /// arrived.
    fn read(&mut self, n: usize) -> (String, bool) {
        let n = n.min(self.received.len());
        let data: Vec<u8> = self.received.drain(..n).collect();

        (
            String::from_utf8_lossy(&data).into_owned(),
            n == 0 && self.finished,
        )
    }
}
// ANCHOR_END: calls

// ANCHOR: trace
fn endpoint(address: &'static str) -> Endpoint {
    Endpoint {
        address,
        port: 5000,
    }
}

fn main() {
    let listener = Listener {
        backlog: 2,
        queue: VecDeque::new(),
    };

    let mut stack = Stack {
        listeners: HashMap::from([(80, listener)]),
        connections: HashMap::new(),
        buffer_size: 8,
    };

    let (a, b, c) = (
        endpoint("10.0.0.1"),
        endpoint("10.0.0.2"),
        endpoint("10.0.0.3"),
    );

    let syn = Segment {
        syn: true,
        ..Segment::default()
    };

    for (from, port) in [(a, 80), (b, 80), (c, 80), (c, 81)] {
        let result = stack.receive(from, port, &syn);
        println!("SYN from {from} to port {port}: {result}");
    }

    if let Some(id) = stack.accept(80) {
        println!("accept on port 80: the connection from {}", id.remote);
    }

    let hello = Segment {
        data: "hello",
        ..Segment::default()
    };

    for from in [b, a, b, c] {
        let result = stack.receive(from, 80, &hello);
        println!("5 bytes from {from} to port 80: {result}");
    }

    let id = Key {
        remote: b,
        port: 80,
    };

    if let Some(socket) = stack.connections.get_mut(&id) {
        let (data, _) = socket.read(4);
        println!(
            "read of 4 bytes on the connection from {b}: {data:?}, window {}",
            socket.window()
        );
    }

    let fin = Segment {
        fin: true,
        ..Segment::default()
    };

    println!("FIN from {b}: {}", stack.receive(b, 80, &fin));

    if let Some(socket) = stack.connections.get_mut(&id) {
        for _ in 0..2 {
            let (data, ended) = socket.read(16);
            println!("read: {data:?}, stream ended {ended}");
        }
    }
}
// ANCHOR_END: trace
