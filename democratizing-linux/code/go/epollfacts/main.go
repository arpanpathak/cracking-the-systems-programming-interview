// Command epollfacts measures epoll with pipes: which descriptors a wait
// reports, how level-triggered and edge-triggered registrations differ, how
// a closed peer is reported, and how many events a wait returns when 1000
// descriptors are registered and 1 is ready.
//
// Run it from code/go with:
//
//	go run ./epollfacts
package main

// ANCHOR: imports
import (
	"fmt"
	"log"

	"golang.org/x/sys/unix"
)

// ANCHOR_END: imports

// ANCHOR: setup
// A pipe is the pair of descriptors of one pipe.
type pipe struct {
	reader, writer int
}

// watch creates an epoll instance and n pipes, and registers the read end of
// every pipe for readability with the given extra flags. The number of the
// pipe is stored in the registration and comes back with each event.
func watch(n int, flags uint32) (int, []pipe, error) {
	epoll, err := unix.EpollCreate1(unix.EPOLL_CLOEXEC)

	if err != nil {
		return 0, nil, err
	}

	pipes := make([]pipe, n)

	for i := range pipes {
		var fds [2]int

		if err := unix.Pipe2(fds[:], unix.O_CLOEXEC); err != nil {
			return 0, nil, err
		}

		pipes[i] = pipe{reader: fds[0], writer: fds[1]}
		event := unix.EpollEvent{Events: unix.EPOLLIN | flags, Fd: int32(i)}

		if err := unix.EpollCtl(epoll, unix.EPOLL_CTL_ADD, fds[0], &event); err != nil {
			return 0, nil, err
		}
	}

	return epoll, pipes, nil
}

// ready returns the events that are ready now. A timeout of 0 makes the
// wait return at once.
func ready(epoll int) ([]unix.EpollEvent, error) {
	events := make([]unix.EpollEvent, 16)
	n, err := unix.EpollWait(epoll, events, 0)

	if err != nil {
		return nil, err
	}

	return events[:n], nil
}

// release closes an epoll instance and its pipes.
func release(epoll int, pipes []pipe) {
	unix.Close(epoll)

	for _, p := range pipes {
		unix.Close(p.reader)
		unix.Close(p.writer)
	}
}

// ANCHOR_END: setup

// ANCHOR: level
// level registers 3 pipes level-triggered and waits before a write, after a
// write, again without reading, and after reading.
func level() error {
	epoll, pipes, err := watch(3, 0)

	if err != nil {
		return err
	}

	defer release(epoll, pipes)

	events, err := ready(epoll)

	if err != nil {
		return err
	}

	fmt.Printf("3 pipes registered, none written: %d event(s)\n", len(events))

	if _, err := unix.Write(pipes[1].writer, []byte("hello")); err != nil {
		return err
	}

	events, err = ready(epoll)

	if err != nil || len(events) != 1 {
		return fmt.Errorf("wait after a write: %d events, %v", len(events), err)
	}

	fmt.Printf("write to pipe 1: 1 event, for pipe %d\n", events[0].Fd)

	events, err = ready(epoll)

	if err != nil {
		return err
	}

	fmt.Printf("level-triggered, data not read, wait again: %d event(s)\n", len(events))

	if _, err := unix.Read(pipes[1].reader, make([]byte, 16)); err != nil {
		return err
	}

	events, err = ready(epoll)

	if err != nil {
		return err
	}

	fmt.Printf("after reading the data: %d event(s)\n", len(events))

	unix.Close(pipes[1].writer)
	events, err = ready(epoll)

	if err != nil || len(events) != 1 {
		return fmt.Errorf("wait after a close: %d events, %v", len(events), err)
	}

	fmt.Printf("write end of pipe 1 closed: event has EPOLLHUP %v\n", events[0].Events&unix.EPOLLHUP != 0)

	return nil
}

// ANCHOR_END: level

// ANCHOR: edge
// edge registers a pipe edge-triggered and waits 2 times after one write,
// and once more after a second write.
func edge() error {
	epoll, pipes, err := watch(1, unix.EPOLLET)

	if err != nil {
		return err
	}

	defer release(epoll, pipes)

	var counts [3]int

	for i := range counts {
		if i != 1 {
			if _, err := unix.Write(pipes[0].writer, []byte("hello")); err != nil {
				return err
			}
		}

		events, err := ready(epoll)

		if err != nil {
			return err
		}

		counts[i] = len(events)
	}

	fmt.Printf("edge-triggered, data not read: wait %d event(s), wait again %d event(s)\n", counts[0], counts[1])
	fmt.Printf("edge-triggered, after another write: %d event(s)\n", counts[2])

	return nil
}

// ANCHOR_END: edge

// ANCHOR: many
// many registers 1000 pipes and writes to 1 of them.
func many() error {
	epoll, pipes, err := watch(1000, 0)

	if err != nil {
		return err
	}

	defer release(epoll, pipes)

	if _, err := unix.Write(pipes[700].writer, []byte("hello")); err != nil {
		return err
	}

	events, err := ready(epoll)

	if err != nil || len(events) != 1 {
		return fmt.Errorf("wait with 1000 pipes: %d events, %v", len(events), err)
	}

	fmt.Printf("1000 pipes registered, pipe 700 written: 1 event, for pipe %d\n", events[0].Fd)

	return nil
}

// ANCHOR_END: many

func main() {
	for _, experiment := range []func() error{level, edge, many} {
		if err := experiment(); err != nil {
			log.Fatal(err)
		}
	}
}
