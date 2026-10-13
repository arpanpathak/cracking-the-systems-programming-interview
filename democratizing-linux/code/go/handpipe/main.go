// Command handpipe builds a pipe by hand, with the same parts the kernel
// uses: a ring of pages for the bytes, a lock, a place for a reader to sleep
// and a place for a writer to sleep, and a count of the open ends.
//
// It traces a small ring call by call, repeats the capacity measurement of
// pipefacts on a ring of the kernel's size, and sends 1048576 bytes from a
// writer goroutine to a reader.
//
// Run it from code/go with:
//
//	go run ./handpipe
package main

// ANCHOR: imports
import (
	"errors"
	"fmt"
	"strings"
	"sync"
)

// ANCHOR_END: imports

// ANCHOR: page
// A page is one slot of the ring: a block of memory, and the position and
// length of the bytes in it that have not been read yet.
type page struct {
	data   []byte
	offset int
	length int
}

// A ring is the storage of a pipe. head counts the pages ever put into use
// and tail counts the pages ever emptied, so head-tail pages are in use, and
// a counter's remainder after division by the number of slots is its slot.
type ring struct {
	pages []page
	head  uint
	tail  uint
}

func newRing(slots, pageSize int) *ring {
	pages := make([]page, slots)

	for i := range pages {
		pages[i].data = make([]byte, pageSize)
	}

	return &ring{pages: pages}
}

func (r *ring) empty() bool {
	return r.head == r.tail
}

func (r *ring) full() bool {
	return r.head-r.tail == uint(len(r.pages))
}

// slot returns the page that a counter refers to.
func (r *ring) slot(counter uint) *page {
	return &r.pages[counter%uint(len(r.pages))]
}

// ANCHOR_END: page

// ANCHOR: put
// put copies as much of data as the ring has room for and returns the number
// of bytes it copied. The bytes go first into the unused end of the newest
// page, then into free slots, one page each.
func (r *ring) put(data []byte) int {
	copied := 0

	if !r.empty() {
		newest := r.slot(r.head - 1)
		end := newest.offset + newest.length

		n := copy(newest.data[end:], data)
		newest.length += n
		copied += n
	}

	for copied < len(data) && !r.full() {
		next := r.slot(r.head)
		next.offset = 0
		next.length = copy(next.data, data[copied:])

		copied += next.length
		r.head++
	}

	return copied
}

// ANCHOR_END: put

// ANCHOR: take
// take moves up to len(buf) of the oldest bytes into buf and returns the
// number it moved. A slot becomes free when the last byte of its page has
// been taken.
func (r *ring) take(buf []byte) int {
	moved := 0

	for moved < len(buf) && !r.empty() {
		oldest := r.slot(r.tail)

		n := copy(buf[moved:], oldest.data[oldest.offset:oldest.offset+oldest.length])
		oldest.offset += n
		oldest.length -= n
		moved += n

		if oldest.length == 0 {
			r.tail++
		}
	}

	return moved
}

// ANCHOR_END: take

// ANCHOR: pipe
// errBrokenPipe is what a write returns when no reader is left.
var errBrokenPipe = errors.New("EPIPE")

// A pipe is a ring shared by a reader and a writer goroutine. readable is where a reader
// sleeps while the ring is empty, and writable is where a writer sleeps while
// the ring is full. readers and writers count the open ends.
type pipe struct {
	mu       sync.Mutex
	readable *sync.Cond
	writable *sync.Cond
	ring     *ring
	readers  int
	writers  int
}

func newPipe(slots, pageSize int) *pipe {
	p := &pipe{ring: newRing(slots, pageSize), readers: 1, writers: 1}
	p.readable = sync.NewCond(&p.mu)
	p.writable = sync.NewCond(&p.mu)

	return p
}

// ANCHOR_END: pipe

// ANCHOR: write
// write returns when every byte of data is in the ring, or when no reader is
// left. While the ring is full it sleeps on writable.
func (p *pipe) write(data []byte) (int, error) {
	p.mu.Lock()
	defer p.mu.Unlock()

	written := 0

	for written < len(data) {
		if p.readers == 0 {
			return written, errBrokenPipe
		}

		n := p.ring.put(data[written:])
		written += n

		if n == 0 {
			p.writable.Wait()
			continue
		}

		p.readable.Broadcast()
	}

	return written, nil
}

// ANCHOR_END: write

// ANCHOR: read
// read returns as soon as it has moved at least one byte into buf. While the
// ring is empty and a writer exists it sleeps on readable. It returns 0 when
// the ring is empty and no writer is left: the end of the stream.
func (p *pipe) read(buf []byte) int {
	p.mu.Lock()
	defer p.mu.Unlock()

	for p.ring.empty() && p.writers > 0 {
		p.readable.Wait()
	}

	n := p.ring.take(buf)

	if n > 0 {
		p.writable.Broadcast()
	}

	return n
}

// ANCHOR_END: read

// ANCHOR: close
// closeWriter gives up a write end. A reader asleep on an empty ring wakes
// and finds that no writer is left.
func (p *pipe) closeWriter() {
	p.mu.Lock()
	defer p.mu.Unlock()

	p.writers--
	p.readable.Broadcast()
}

// closeReader gives up a read end. A writer asleep on a full ring wakes and
// finds that no reader is left.
func (p *pipe) closeReader() {
	p.mu.Lock()
	defer p.mu.Unlock()

	p.readers--
	p.writable.Broadcast()
}

// ANCHOR_END: close

// ANCHOR: trace
// picture renders the ring as one cell per slot: the number of unread bytes
// in its page, or a dot when the slot is free.
func (r *ring) picture() string {
	cells := make([]string, len(r.pages))

	for i := range cells {
		cells[i] = "."
	}

	for counter := r.tail; counter != r.head; counter++ {
		cells[counter%uint(len(r.pages))] = fmt.Sprint(r.slot(counter).length)
	}

	return "[" + strings.Join(cells, " ") + "]"
}

// smallRing applies the calls of the trace to a ring of 4 pages of 8 bytes
// and prints the ring after each.
func smallRing() {
	r := newRing(4, 8)
	buf := make([]byte, 32)

	calls := []struct {
		op string
		n  int
	}{{"put", 12}, {"take", 3}, {"put", 30}, {"take", 5}, {"put", 30}}

	fmt.Println("ring of 4 pages of 8 bytes")

	for _, call := range calls {
		var done int

		switch call.op {
		case "put":
			done = r.put(buf[:call.n])
		case "take":
			done = r.take(buf[:call.n])
		}

		fmt.Printf("%-4s %2d: %2d bytes   head %d  tail %d   %s\n", call.op, call.n, done, r.head, r.tail, r.picture())
	}
}

// ANCHOR_END: trace

// ANCHOR: kernelsize
// fill puts whole blocks into the ring until it accepts none and returns the
// number of bytes accepted.
func fill(r *ring, block []byte) int {
	total := 0

	for {
		n := r.put(block)

		if n == 0 {
			return total
		}

		total += n
	}
}

// kernelSize repeats the capacity measurement of pipefacts on a ring with
// the kernel's dimensions: 16 pages of 4096 bytes.
func kernelSize() {
	const pageSize = 4096

	r := newRing(16, pageSize)
	block := make([]byte, pageSize)

	steps := []struct {
		read   int
		report string
	}{
		{0, "new pipe: %d bytes accepted\n"},
		{1, "after reading 1 byte: %d bytes accepted\n"},
		{pageSize - 1, "after reading 4096 bytes in total: %d bytes accepted\n"},
	}

	for _, step := range steps {
		r.take(block[:step.read])
		fmt.Printf(step.report, fill(r, block))
	}
}

// ANCHOR_END: kernelsize

// ANCHOR: transfer
// transfer sends one megabyte through a pipe of the kernel's size. Byte i of
// the stream has the value i mod 256, which lets the reader verify the order.
func transfer() {
	const total = 1 << 20

	p := newPipe(16, 4096)

	go func() {
		defer p.closeWriter()

		chunk := make([]byte, 100_000)

		for sent := 0; sent < total; sent += len(chunk) {
			chunk = chunk[:min(len(chunk), total-sent)]

			for i := range chunk {
				chunk[i] = byte(sent + i)
			}

			if _, err := p.write(chunk); err != nil {
				return
			}
		}
	}()

	buf := make([]byte, 30_000)
	received, inOrder := 0, true

	for n := p.read(buf); n > 0; n = p.read(buf) {
		for i, b := range buf[:n] {
			inOrder = inOrder && b == byte(received+i)
		}

		received += n
	}

	fmt.Printf("1048576 bytes written: %d bytes read, in order: %v\n", received, inOrder)
	fmt.Printf("write end closed: read returns %d\n", p.read(buf))

	p.closeReader()

	_, err := p.write([]byte("hello"))
	fmt.Printf("read end closed: write fails with %v\n", err)
}

// ANCHOR_END: transfer

func main() {
	smallRing()
	fmt.Println()
	kernelSize()
	fmt.Println()
	transfer()
}
