// Command sockmodel models the receiving side of TCP in the kernel: a table
// of connections keyed by addresses and ports, listeners with an accept
// queue of limited length, and a receive buffer whose free space is the
// window offered to the sender.
//
// Run it from code/go with:
//
//	go run ./sockmodel
package main

// ANCHOR: imports
import "fmt"

// ANCHOR_END: imports

// ANCHOR: types
// An endpoint is an IP address and a port.
type endpoint struct {
	address string
	port    int
}

func (e endpoint) String() string {
	return fmt.Sprintf("%s:%d", e.address, e.port)
}

// A socket is one established connection: the bytes received and not yet
// read, the size of the receive buffer, and whether the sender has finished.
type socket struct {
	received []byte
	capacity int
	finished bool
}

// window is the free space of the receive buffer: the number of bytes the
// sender may still send.
func (s *socket) window() int {
	return s.capacity - len(s.received)
}

// A key identifies a connection on this machine: the remote endpoint and the
// local port. With the local address, which the model leaves out, it forms
// the 4 values that identify a TCP connection.
type key struct {
	remote endpoint
	port   int
}

// A listener accepts connections on a port. queue holds the connections that
// are established and have not been returned by accept.
type listener struct {
	backlog int
	queue   []key
}

// A stack is the TCP state of a machine.
type stack struct {
	listeners   map[int]*listener
	connections map[key]*socket
	bufferSize  int
}

// A segment is a packet of TCP. syn opens a connection and fin ends the
// sender's stream.
type segment struct {
	from     endpoint
	port     int
	syn, fin bool
	data     string
}

// ANCHOR_END: types

// ANCHOR: receive
// receive handles an arriving segment and describes the result. A segment
// belongs to the connection with its remote endpoint and local port. Only
// when no such connection exists, and the segment is a SYN, is the listener
// on the port consulted.
func (st *stack) receive(seg segment) string {
	id := key{remote: seg.from, port: seg.port}

	if s, ok := st.connections[id]; ok {
		return s.deliver(seg)
	}

	if !seg.syn {
		return "reset, no connection"
	}

	l, ok := st.listeners[seg.port]

	if !ok {
		return "reset, no listener on the port"
	}

	if len(l.queue) == l.backlog {
		return "dropped, the accept queue is full"
	}

	st.connections[id] = &socket{capacity: st.bufferSize}
	l.queue = append(l.queue, id)

	return fmt.Sprintf("established, accept queue %d", len(l.queue))
}

// deliver puts the data of a segment into the receive buffer, up to the
// window, and records a FIN.
func (s *socket) deliver(seg segment) string {
	if seg.fin {
		s.finished = true

		return "the sender's stream has ended"
	}

	accepted := min(len(seg.data), s.window())
	s.received = append(s.received, seg.data[:accepted]...)

	return fmt.Sprintf("accepted %d, window %d", accepted, s.window())
}

// ANCHOR_END: receive

// ANCHOR: calls
// accept removes the oldest connection from the accept queue of a port.
func (st *stack) accept(port int) (key, bool) {
	l, ok := st.listeners[port]

	if !ok || len(l.queue) == 0 {
		return key{}, false
	}

	id := l.queue[0]
	l.queue = l.queue[1:]

	return id, true
}

// read removes up to n bytes from the receive buffer. It returns 0 bytes
// with ended set when the buffer is empty and a FIN has arrived.
func (s *socket) read(n int) (data string, ended bool) {
	n = min(n, len(s.received))
	data, s.received = string(s.received[:n]), s.received[n:]

	return data, n == 0 && s.finished
}

// ANCHOR_END: calls

// ANCHOR: trace
func main() {
	st := &stack{
		listeners:   map[int]*listener{80: {backlog: 2}},
		connections: map[key]*socket{},
		bufferSize:  8,
	}

	a, b, c := endpoint{"10.0.0.1", 5000}, endpoint{"10.0.0.2", 5000}, endpoint{"10.0.0.3", 5000}

	for _, seg := range []segment{{from: a, port: 80, syn: true}, {from: b, port: 80, syn: true},
		{from: c, port: 80, syn: true}, {from: c, port: 81, syn: true}} {
		fmt.Printf("SYN from %s to port %d: %s\n", seg.from, seg.port, st.receive(seg))
	}

	if id, ok := st.accept(80); ok {
		fmt.Printf("accept on port 80: the connection from %s\n", id.remote)
	}

	for _, from := range []endpoint{b, a, b, c} {
		fmt.Printf("5 bytes from %s to port 80: %s\n", from, st.receive(segment{from: from, port: 80, data: "hello"}))
	}

	conn, ok := st.connections[key{remote: b, port: 80}]

	if !ok {
		return
	}

	data, ended := conn.read(4)
	fmt.Printf("read of 4 bytes on the connection from %s: %q, window %d\n", b, data, conn.window())

	fmt.Printf("FIN from %s: %s\n", b, st.receive(segment{from: b, port: 80, fin: true}))

	data, ended = conn.read(16)
	fmt.Printf("read: %q, stream ended %v\n", data, ended)

	data, ended = conn.read(16)
	fmt.Printf("read: %q, stream ended %v\n", data, ended)
}

// ANCHOR_END: trace
