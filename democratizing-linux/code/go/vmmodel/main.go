// Command vmmodel models an address space: a list of mappings, a page table
// that is filled on demand by page faults, a shared zero page, and
// copy-on-write after fork.
//
// Run it from code/go with:
//
//	go run ./vmmodel
package main

// ANCHOR: imports
import (
	"errors"
	"fmt"
)

// ANCHOR_END: imports

// ANCHOR: types
const pageSize = 4096

// errSegv is the result of an access that no mapping allows. The kernel
// sends the process the signal SIGSEGV.
var errSegv = errors.New("SIGSEGV")

// A frame is a page of physical memory. refs counts the page table entries
// that refer to it.
type frame struct {
	data [pageSize]byte
	refs int
}

// memory is the physical memory shared by all address spaces: the number of
// frames allocated, and the frame of zeros that every read of an untouched
// page maps.
type memory struct {
	frames int
	zero   *frame
}

func (m *memory) allocate() *frame {
	m.frames++

	return &frame{refs: 1}
}

// A mapping is a range of virtual pages and the access it permits.
type mapping struct {
	start, pages int
	writable     bool
}

// An entry is a page table entry: the frame behind a virtual page, and
// whether the processor may write to it without a fault.
type entry struct {
	frame    *frame
	writable bool
}

// A space is the address space of a process.
type space struct {
	memory   *memory
	mappings []mapping
	table    map[int]entry
	faults   int
	nextPage int
}

func newSpace() *space {
	return &space{
		memory:   &memory{zero: &frame{refs: 1}},
		table:    map[int]entry{},
		nextPage: 16,
	}
}

// ANCHOR_END: types

// ANCHOR: mmap
// mmap records a new mapping and returns its address. It allocates no frame
// and writes no page table entry.
func (s *space) mmap(pages int, writable bool) int {
	start := s.nextPage
	s.mappings = append(s.mappings, mapping{start: start, pages: pages, writable: writable})
	s.nextPage += pages + 1

	return start * pageSize
}

// find returns the mapping that contains a page.
func (s *space) find(page int) (mapping, bool) {
	for _, m := range s.mappings {
		if page >= m.start && page < m.start+m.pages {
			return m, true
		}
	}

	return mapping{}, false
}

// ANCHOR_END: mmap

// ANCHOR: access
// read returns the byte at an address. The processor uses the page table
// entry when one exists, and faults when none does.
func (s *space) read(address int) (byte, error) {
	page, offset := address/pageSize, address%pageSize

	if _, present := s.table[page]; !present {
		if err := s.fault(page, false); err != nil {
			return 0, err
		}
	}

	return s.table[page].frame.data[offset], nil
}

// write stores a byte at an address. It faults when the page has no entry or
// the entry does not permit writing.
func (s *space) write(address int, value byte) error {
	page, offset := address/pageSize, address%pageSize

	if !s.table[page].writable {
		if err := s.fault(page, true); err != nil {
			return err
		}
	}

	s.table[page].frame.data[offset] = value

	return nil
}

// ANCHOR_END: access

// ANCHOR: fault
// fault is the kernel's page fault handler. It checks the access against
// the mappings and then repairs the page table entry so that the access can
// be repeated.
func (s *space) fault(page int, write bool) error {
	m, ok := s.find(page)

	if !ok || write && !m.writable {
		return errSegv
	}

	s.faults++
	e, present := s.table[page]

	switch {
	case !write:
		// A read of an untouched page maps the shared zero frame.
		s.memory.zero.refs++
		s.table[page] = entry{frame: s.memory.zero}

	case !present:
		// A write to an untouched page gets a new frame of zeros.
		s.table[page] = entry{frame: s.memory.allocate(), writable: true}

	case e.frame.refs == 1:
		// The frame has no other user. Writing is enabled in place.
		s.table[page] = entry{frame: e.frame, writable: true}

	default:
		// The frame is shared. The writer gets a private copy.
		private := s.memory.allocate()
		private.data = e.frame.data
		e.frame.refs--
		s.table[page] = entry{frame: private, writable: true}
	}

	return nil
}

// ANCHOR_END: fault

// ANCHOR: fork
// fork returns a child with the same mappings and a page table that refers
// to the same frames. Every entry is made read-only in the parent and in the
// child, so that the first write by either causes a fault.
func (s *space) fork() *space {
	child := &space{
		memory:   s.memory,
		mappings: append([]mapping(nil), s.mappings...),
		table:    map[int]entry{},
		nextPage: s.nextPage,
	}

	for page, e := range s.table {
		e.frame.refs++
		e.writable = false
		s.table[page], child.table[page] = e, e
	}

	return child
}

// ANCHOR_END: fork

// ANCHOR: trace
// report prints a step with the fault count of a space and the number of
// frames allocated.
func (s *space) report(step string) {
	fmt.Printf("%-34s faults %d, frames %d\n", step, s.faults, s.memory.frames)
}

func run() error {
	parent := newSpace()
	base := parent.mmap(4, true)
	parent.report("mmap of 4 pages:")

	if err := parent.write(base, 'a'); err != nil {
		return err
	}

	parent.report("write to page 0:")

	value, err := parent.read(base + pageSize)

	if err != nil {
		return err
	}

	parent.report(fmt.Sprintf("read of page 1, value %d:", value))

	if err := parent.write(base+pageSize, 'x'); err != nil {
		return err
	}

	parent.report("write to page 1:")

	child := parent.fork()
	child.report("fork, in the child:")

	if err := child.write(base, 'b'); err != nil {
		return err
	}

	child.report("child writes page 0:")

	if err := parent.write(base, 'c'); err != nil {
		return err
	}

	parent.report("parent writes page 0:")

	inParent, err := parent.read(base)

	if err != nil {
		return err
	}

	inChild, err := child.read(base)

	if err != nil {
		return err
	}

	fmt.Printf("page 0 holds %q in the parent and %q in the child\n", inParent, inChild)

	fmt.Printf("write outside every mapping: %v\n", parent.write(base+100*pageSize, 1))

	readOnly := parent.mmap(1, false)
	fmt.Printf("write to a read-only mapping: %v\n", parent.write(readOnly, 1))

	return nil
}

func main() {
	if err := run(); err != nil {
		fmt.Println(err)
	}
}

// ANCHOR_END: trace
