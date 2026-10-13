// Command pipefacts measures a kernel pipe: its capacity,
// the unit in which a read frees space, how a reader observes the end of the
// stream, and the result of a write when no reader exists.
//
// Run it from code/go with:
//
//	go run ./pipefacts
package main

// ANCHOR: imports
import (
	"errors"
	"fmt"
	"log"

	"golang.org/x/sys/unix"
)

// ANCHOR_END: imports

// ANCHOR: pipe
// block is the size of every write the program attempts: one page.
const block = 4096

// newPipe creates a pipe in non-blocking mode: a read or a write that cannot
// proceed returns EAGAIN where it would otherwise suspend the caller.
func newPipe() (reader, writer int, err error) {
	var fds [2]int

	if err := unix.Pipe2(fds[:], unix.O_NONBLOCK|unix.O_CLOEXEC); err != nil {
		return 0, 0, fmt.Errorf("pipe2: %w", err)
	}

	return fds[0], fds[1], nil
}

// ANCHOR_END: pipe

// ANCHOR: fill
// fill writes whole blocks until the kernel refuses one and returns the
// number of bytes accepted.
func fill(writer int) (int, error) {
	data := make([]byte, block)
	total := 0

	for {
		n, err := unix.Write(writer, data)

		if errors.Is(err, unix.EAGAIN) {
			return total, nil
		}

		if err != nil {
			return total, fmt.Errorf("write: %w", err)
		}

		total += n
	}
}

// drain reads and discards up to n bytes.
func drain(reader, n int) error {
	_, err := unix.Read(reader, make([]byte, n))

	return err
}

// ANCHOR_END: fill

// ANCHOR: capacity
// capacity fills a pipe when it is new, after 1 byte has been read, and
// after 4096 bytes have been read. Each fill reports the free space.
func capacity() error {
	reader, writer, err := newPipe()

	if err != nil {
		return err
	}

	defer unix.Close(reader)
	defer unix.Close(writer)

	steps := []struct {
		read   int
		report string
	}{
		{0, "new pipe: %d bytes accepted\n"},
		{1, "after reading 1 byte: %d bytes accepted\n"},
		{block - 1, "after reading 4096 bytes in total: %d bytes accepted\n"},
	}

	for _, step := range steps {
		if err := drain(reader, step.read); err != nil {
			return err
		}

		accepted, err := fill(writer)

		if err != nil {
			return err
		}

		fmt.Printf(step.report, accepted)
	}

	return nil
}

// ANCHOR_END: capacity

// ANCHOR: resize
// resize changes the capacity of a pipe with fcntl and measures it after
// each change.
func resize() error {
	reader, writer, err := newPipe()

	if err != nil {
		return err
	}

	defer unix.Close(reader)
	defer unix.Close(writer)

	for _, request := range []int{4 * block, 5000, 1 << 20} {
		granted, err := unix.FcntlInt(uintptr(writer), unix.F_SETPIPE_SZ, request)

		if err != nil {
			return fmt.Errorf("F_SETPIPE_SZ: %w", err)
		}

		accepted, err := fill(writer)

		if err != nil {
			return err
		}

		fmt.Printf("capacity of %d bytes requested: %d granted, %d bytes accepted\n", request, granted, accepted)

		if err := drain(reader, accepted); err != nil {
			return err
		}
	}

	return nil
}

// ANCHOR_END: resize

// ANCHOR: eof
// endOfStream reads an empty pipe while a write end is open, and again after
// the write end has been closed.
func endOfStream() error {
	reader, writer, err := newPipe()

	if err != nil {
		return err
	}

	defer unix.Close(reader)

	buf := make([]byte, block)

	_, err = unix.Read(reader, buf)
	fmt.Printf("empty pipe, write end open: read fails with %s\n", name(err))

	unix.Close(writer)

	n, err := unix.Read(reader, buf)

	if err != nil {
		return fmt.Errorf("read: %w", err)
	}

	fmt.Printf("empty pipe, write end closed: read returns %d\n", n)

	return nil
}

// ANCHOR_END: eof

// ANCHOR: broken
// brokenPipe writes to a pipe whose read end has been closed.
func brokenPipe() error {
	reader, writer, err := newPipe()

	if err != nil {
		return err
	}

	defer unix.Close(writer)

	unix.Close(reader)

	_, err = unix.Write(writer, []byte("hello"))
	fmt.Printf("read end closed: write fails with %s\n", name(err))

	return nil
}

// name returns the symbolic name of a system call error, such as EAGAIN.
func name(err error) string {
	var errno unix.Errno

	if errors.As(err, &errno) {
		return unix.ErrnoName(errno)
	}

	return fmt.Sprint(err)
}

// ANCHOR_END: broken

func main() {
	for _, experiment := range []func() error{capacity, resize, endOfStream, brokenPipe} {
		if err := experiment(); err != nil {
			log.Fatal(err)
		}
	}
}
