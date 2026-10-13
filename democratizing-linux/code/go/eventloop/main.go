// Command eventloop models epoll: an interest list of registered pipes, a
// ready list that a write fills, and a wait that examines only the ready
// list. It repeats the measurements of epollfacts on the model and then runs
// a small event loop on it.
//
// Run it from code/go with:
//
//	go run ./eventloop
package main

// ANCHOR: imports
import "fmt"

// ANCHOR_END: imports

// ANCHOR: types
// A pipe is the read end of a pipe as epoll sees it: the bytes waiting to be
// read, and its registration. queued is set while the pipe is on the ready
// list.
type pipe struct {
	buffered   int
	registered bool
	edge       bool
	queued     bool
}

// A kernel holds the pipes and one epoll instance. The registered pipes are
// the interest list. ready is the ready list, in the order in which the
// pipes became ready. examined counts the registrations that waits and scans
// have looked at.
type kernel struct {
	pipes    []pipe
	ready    []int
	examined int
}

func newKernel(pipes int) *kernel {
	return &kernel{pipes: make([]pipe, pipes)}
}

// ANCHOR_END: types

// ANCHOR: wake
// register adds a pipe to the interest list. A pipe that is already
// readable goes on the ready list at once.
func (k *kernel) register(index int, edge bool) {
	p := &k.pipes[index]
	p.registered, p.edge = true, edge

	if p.buffered > 0 {
		k.enqueue(index)
	}
}

// enqueue puts a pipe on the ready list unless it is already there.
func (k *kernel) enqueue(index int) {
	if p := &k.pipes[index]; !p.queued {
		p.queued = true
		k.ready = append(k.ready, index)
	}
}

// write adds bytes to a pipe. This is the moment the pipe becomes ready, and
// the writer puts it on the ready list.
func (k *kernel) write(index, n int) {
	k.pipes[index].buffered += n

	if k.pipes[index].registered {
		k.enqueue(index)
	}
}

// read removes up to n bytes from a pipe and returns the number removed.
func (k *kernel) read(index, n int) int {
	n = min(n, k.pipes[index].buffered)
	k.pipes[index].buffered -= n

	return n
}

// ANCHOR_END: wake

// ANCHOR: wait
// wait empties the ready list and returns the pipes on it that are still
// readable. A level-triggered pipe that is reported goes back on the list,
// so the next wait checks it again. An edge-triggered pipe does not, and is
// reported again only after another write.
func (k *kernel) wait() []int {
	queued := k.ready
	k.ready = nil

	var events []int

	for _, index := range queued {
		p := &k.pipes[index]
		p.queued = false
		k.examined++

		if p.buffered == 0 {
			continue
		}

		events = append(events, index)

		if !p.edge {
			k.enqueue(index)
		}
	}

	return events
}

// scan is the method of select and poll: it examines every registered pipe
// on every call.
func (k *kernel) scan() []int {
	var events []int

	for index, p := range k.pipes {
		if !p.registered {
			continue
		}

		k.examined++

		if p.buffered > 0 {
			events = append(events, index)
		}
	}

	return events
}

// ANCHOR_END: wait

// ANCHOR: measure
// level repeats the level-triggered measurement of epollfacts.
func level() {
	k := newKernel(3)

	for index := range k.pipes {
		k.register(index, false)
	}

	fmt.Printf("3 pipes registered, none written: %d event(s)\n", len(k.wait()))

	k.write(1, 5)

	if events := k.wait(); len(events) == 1 {
		fmt.Printf("write to pipe 1: 1 event, for pipe %d\n", events[0])
	}

	fmt.Printf("level-triggered, data not read, wait again: %d event(s)\n", len(k.wait()))

	k.read(1, 16)
	fmt.Printf("after reading the data: %d event(s)\n", len(k.wait()))
}

// edge repeats the edge-triggered measurement.
func edge() {
	k := newKernel(1)
	k.register(0, true)

	k.write(0, 5)
	first, second := len(k.wait()), len(k.wait())
	fmt.Printf("edge-triggered, data not read: wait %d event(s), wait again %d event(s)\n", first, second)

	k.write(0, 5)
	fmt.Printf("edge-triggered, after another write: %d event(s)\n", len(k.wait()))
}

// many compares the work of a wait with the work of a scan when 1000 pipes
// are registered and 1 is ready.
func many() {
	k := newKernel(1000)

	for index := range k.pipes {
		k.register(index, false)
	}

	k.write(700, 5)

	if events := k.wait(); len(events) == 1 {
		fmt.Printf("1000 pipes registered, pipe 700 written: 1 event, for pipe %d\n", events[0])
	}

	byWait := k.examined
	k.scan()
	fmt.Printf("registrations examined: %d by the wait, %d by a scan\n", byWait, k.examined-byWait)
}

// ANCHOR_END: measure

// ANCHOR: event_loop
// turn is one iteration of an event loop: wait for ready pipes, then run the
// handler for each. It returns the pipes it handled.
func (k *kernel) turn(handle func(k *kernel, index int)) []int {
	events := k.wait()

	for _, index := range events {
		handle(k, index)
	}

	return events
}

// loop registers 4 pipes, writes to 2 of them, and runs an event loop whose
// handler reads at most 4 bytes for each event.
func loop() {
	k := newKernel(4)

	for index := range k.pipes {
		k.register(index, false)
	}

	k.write(2, 5)
	k.write(0, 3)

	handle := func(k *kernel, index int) { k.read(index, 4) }

	fmt.Printf("event loop: turn 1 handles %v, turn 2 handles %v, turn 3 handles %v\n",
		k.turn(handle), k.turn(handle), k.turn(handle))
}

// ANCHOR_END: event_loop

func main() {
	level()
	edge()
	many()
	loop()
}
