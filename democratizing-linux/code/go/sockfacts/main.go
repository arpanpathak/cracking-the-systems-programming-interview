// Command sockfacts measures TCP sockets on the loopback interface: when a
// connection is established, what identifies it, how written bytes arrive,
// what stops a writer whose peer does not read, and how each side learns
// that the other has closed.
//
// Run it from code/go with:
//
//	go run ./sockfacts
package main

// ANCHOR: imports
import (
	"errors"
	"fmt"
	"log"

	"golang.org/x/sys/unix"
)

// ANCHOR_END: imports

// ANCHOR: pair
// listen returns a TCP socket that listens on a free port of 127.0.0.1, and
// its address.
func listen() (int, *unix.SockaddrInet4, error) {
	listener, err := unix.Socket(unix.AF_INET, unix.SOCK_STREAM|unix.SOCK_CLOEXEC, 0)

	if err != nil {
		return 0, nil, err
	}

	if err := unix.Bind(listener, &unix.SockaddrInet4{Addr: [4]byte{127, 0, 0, 1}}); err != nil {
		return 0, nil, err
	}

	if err := unix.Listen(listener, 16); err != nil {
		return 0, nil, err
	}

	address, err := unix.Getsockname(listener)

	if err != nil {
		return 0, nil, err
	}

	return listener, address.(*unix.SockaddrInet4), nil
}

// connect returns a TCP socket connected to an address.
func connect(address *unix.SockaddrInet4) (int, error) {
	client, err := unix.Socket(unix.AF_INET, unix.SOCK_STREAM|unix.SOCK_CLOEXEC, 0)

	if err != nil {
		return 0, err
	}

	return client, unix.Connect(client, address)
}

// name returns the symbolic name of a system call error, such as EPIPE.
func name(err error) string {
	var errno unix.Errno

	if errors.As(err, &errno) {
		return unix.ErrnoName(errno)
	}

	return fmt.Sprint(err)
}

// port returns the port of an address.
func port(address unix.Sockaddr, err error) int {
	if inet, ok := address.(*unix.SockaddrInet4); ok && err == nil {
		return inet.Port
	}

	return 0
}

// ANCHOR_END: pair

// ANCHOR: establish
// establish connects before the server calls accept, and compares the
// addresses of both ends.
func establish() error {
	listener, address, err := listen()

	if err != nil {
		return err
	}

	defer unix.Close(listener)

	client, err := connect(address)
	fmt.Printf("connect before the server calls accept: succeeded %v\n", err == nil)

	if err != nil {
		return err
	}

	defer unix.Close(client)

	server, _, err := unix.Accept(listener)

	if err != nil {
		return err
	}

	defer unix.Close(server)

	fmt.Printf("accept returns a new descriptor: %v, on the listener's port: %v\n",
		server != listener, port(unix.Getsockname(server)) == address.Port)
	fmt.Printf("the client's local port is the server's peer port: %v\n",
		port(unix.Getsockname(client)) == port(unix.Getpeername(server)))

	return stream(client, server)
}

// ANCHOR_END: establish

// ANCHOR: stream
// readFull reads until buf is full.
func readFull(fd int, buf []byte) error {
	for filled := 0; filled < len(buf); {
		n, err := unix.Read(fd, buf[filled:])

		if err != nil {
			return err
		}

		if n == 0 {
			return errors.New("the stream ended early")
		}

		filled += n
	}

	return nil
}

// stream writes "ab" and "cd" with 2 calls and reads 3 bytes and then 1.
// Then the client closes, and the server reads and writes again.
func stream(client, server int) error {
	for _, part := range []string{"ab", "cd"} {
		if _, err := unix.Write(client, []byte(part)); err != nil {
			return err
		}
	}

	first, second := make([]byte, 3), make([]byte, 1)

	if err := readFull(server, first); err != nil {
		return err
	}

	if err := readFull(server, second); err != nil {
		return err
	}

	fmt.Printf("writes of \"ab\" and \"cd\", reads of 3 bytes and 1 byte: %q and %q\n", first, second)

	unix.Close(client)

	n, err := unix.Read(server, first)

	if err != nil {
		return err
	}

	fmt.Printf("the client closed: read returns %d\n", n)

	for err == nil {
		_, err = unix.Write(server, []byte("x"))
	}

	fmt.Printf("writes to the closed peer: the first is accepted, a later one fails with %s\n", name(err))

	return nil
}

// ANCHOR_END: stream

// ANCHOR: flow
// fill writes blocks to a non-blocking socket until the kernel refuses one
// and returns the number of bytes accepted.
func fill(fd int) (int, error) {
	block := make([]byte, 1024)
	total := 0

	for {
		n, err := unix.Write(fd, block)

		if errors.Is(err, unix.EAGAIN) {
			return total, nil
		}

		if err != nil {
			return total, err
		}

		total += n
	}
}

// flow gives a connection small buffers, fills it while the server does not
// read, lets the server read everything, and fills it again.
func flow() error {
	listener, address, err := listen()

	if err != nil {
		return err
	}

	defer unix.Close(listener)

	if err := unix.SetsockoptInt(listener, unix.SOL_SOCKET, unix.SO_RCVBUF, 4096); err != nil {
		return err
	}

	client, err := connect(address)

	if err != nil {
		return err
	}

	defer unix.Close(client)

	if err := unix.SetsockoptInt(client, unix.SOL_SOCKET, unix.SO_SNDBUF, 4096); err != nil {
		return err
	}

	server, _, err := unix.Accept(listener)

	if err != nil {
		return err
	}

	defer unix.Close(server)

	if err := unix.SetNonblock(client, true); err != nil {
		return err
	}

	sent, err := fill(client)

	if err != nil {
		return err
	}

	fmt.Printf("the server does not read: the client is stopped after %d bytes\n", sent)

	if err := readFull(server, make([]byte, sent)); err != nil {
		return err
	}

	again, err := fill(client)

	if err != nil {
		return err
	}

	fmt.Printf("the server has read everything: the client can write again: %v\n", again > 0)

	return nil
}

// ANCHOR_END: flow

func main() {
	for _, experiment := range []func() error{establish, flow} {
		if err := experiment(); err != nil {
			log.Fatal(err)
		}
	}
}
