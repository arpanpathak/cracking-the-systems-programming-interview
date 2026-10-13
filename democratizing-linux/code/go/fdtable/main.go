// Command fdtable models the kernel's file tables in user space: names that
// refer to inodes, open file descriptions that refer to an inode and hold an
// offset, and a descriptor table for each process. Every object counts the
// references to it and is released when the count reaches 0. The program
// repeats the experiments of fdfacts on the model and prints the same lines.
//
// Run it from code/go with:
//
//	go run ./fdtable
package main

// ANCHOR: imports
import (
	"errors"
	"fmt"
	"log"
	"strings"
)

// ANCHOR_END: imports

// ANCHOR: inode
// The errors carry the names of the kernel's error codes for the same cases.
var (
	errBadDescriptor = errors.New("EBADF")
	errTooManyFiles  = errors.New("EMFILE")
	errNoEntry       = errors.New("ENOENT")
)

// An inode is a file: its number, its contents, and 2 reference counts.
// links counts the names that refer to it, and opens counts the open file
// descriptions that refer to it.
type inode struct {
	number int
	data   []byte
	links  int
	opens  int
}

// A filesystem holds the inodes and a single directory, which maps names to
// inodes.
type filesystem struct {
	names  map[string]*inode
	inodes map[int]*inode
	next   int
}

func newFilesystem() *filesystem {
	return &filesystem{names: map[string]*inode{}, inodes: map[int]*inode{}, next: 1}
}

// allocate returns a new inode with no name.
func (fs *filesystem) allocate() *inode {
	file := &inode{number: fs.next}
	fs.inodes[file.number] = file
	fs.next++

	return file
}

// ANCHOR_END: inode

// ANCHOR: names
// create makes an empty file with one name.
func (fs *filesystem) create(name string) *inode {
	file := fs.allocate()
	file.links = 1
	fs.names[name] = file

	return file
}

// link adds a second name for an existing file.
func (fs *filesystem) link(existing, added string) error {
	file, ok := fs.names[existing]

	if !ok {
		return errNoEntry
	}

	file.links++
	fs.names[added] = file

	return nil
}

// unlink removes a name. The file itself is removed only when release finds
// no other reference to it.
func (fs *filesystem) unlink(name string) error {
	file, ok := fs.names[name]

	if !ok {
		return errNoEntry
	}

	delete(fs.names, name)
	file.links--
	fs.release(file)

	return nil
}

// release frees an inode that has no name and is not open.
func (fs *filesystem) release(file *inode) {
	if file.links == 0 && file.opens == 0 {
		delete(fs.inodes, file.number)
	}
}

// ANCHOR_END: names

// ANCHOR: tables
// A description is an open file description: the state created by one open.
// refs counts the descriptors, in all processes, that refer to it.
type description struct {
	file       *inode
	offset     int
	appendMode bool
	refs       int
}

// A descriptor is one entry of a process's table. The close-on-exec flag
// belongs to the entry.
type descriptor struct {
	open    *description
	cloexec bool
}

// A process is its descriptor table. The index of an entry is the file
// descriptor, a nil entry is a free number, and limit is the number of
// entries the process may use.
type process struct {
	fs    *filesystem
	table []*descriptor
	limit int
}

// newProcess returns a process with descriptors 0, 1 and 2 open on a
// terminal, which is a file without a name.
func newProcess(fs *filesystem) *process {
	p := &process{fs: fs, limit: 1024}
	terminal := &description{file: fs.allocate()}
	terminal.file.opens = 1

	for range 3 {
		p.install(terminal)
	}

	return p
}

// ANCHOR_END: tables

// ANCHOR: install
// install puts a description in the lowest free entry, counts the new
// reference, and returns the number of the entry.
func (p *process) install(open *description) (int, error) {
	fd := 0

	for fd < len(p.table) && p.table[fd] != nil {
		fd++
	}

	if fd >= p.limit {
		return 0, errTooManyFiles
	}

	if fd == len(p.table) {
		p.table = append(p.table, nil)
	}

	open.refs++
	p.table[fd] = &descriptor{open: open}

	return fd, nil
}

// lookup returns the entry of a descriptor.
func (p *process) lookup(fd int) (*descriptor, error) {
	if fd < 0 || fd >= len(p.table) || p.table[fd] == nil {
		return nil, errBadDescriptor
	}

	return p.table[fd], nil
}

// open finds the inode behind a name and creates a description for it, with
// offset 0.
func (p *process) open(name string) (int, error) {
	file, ok := p.fs.names[name]

	if !ok {
		return 0, errNoEntry
	}

	fd, err := p.install(&description{file: file})

	if err == nil {
		file.opens++
	}

	return fd, err
}

// dup makes a second descriptor for an existing description.
func (p *process) dup(fd int) (int, error) {
	entry, err := p.lookup(fd)

	if err != nil {
		return 0, err
	}

	return p.install(entry.open)
}

// ANCHOR_END: install

// ANCHOR: close
// close frees an entry and drops its reference to the description. The last
// reference closes the description, which drops its reference to the inode.
func (p *process) close(fd int) error {
	entry, err := p.lookup(fd)

	if err != nil {
		return err
	}

	p.table[fd] = nil
	entry.open.refs--

	if entry.open.refs == 0 {
		entry.open.file.opens--
		p.fs.release(entry.open.file)
	}

	return nil
}

// dup2 makes descriptor to refer to the description of descriptor from,
// closing whatever to referred to before.
func (p *process) dup2(from, to int) error {
	entry, err := p.lookup(from)

	if err != nil {
		return err
	}

	if from == to {
		return nil
	}

	if _, err := p.lookup(to); err == nil {
		p.close(to)
	}

	for len(p.table) <= to {
		p.table = append(p.table, nil)
	}

	entry.open.refs++
	p.table[to] = &descriptor{open: entry.open}

	return nil
}

// ANCHOR_END: close

// ANCHOR: io
// write copies data into the file at the description's offset and advances
// the offset. In append mode the offset first moves to the end of the file.
func (p *process) write(fd int, data string) error {
	entry, err := p.lookup(fd)

	if err != nil {
		return err
	}

	open, file := entry.open, entry.open.file

	if open.appendMode {
		open.offset = len(file.data)
	}

	end := open.offset + len(data)

	if end > len(file.data) {
		file.data = append(file.data, make([]byte, end-len(file.data))...)
	}

	copy(file.data[open.offset:], data)
	open.offset = end

	return nil
}

// read returns up to n bytes from the description's offset and advances the
// offset.
func (p *process) read(fd, n int) (string, error) {
	entry, err := p.lookup(fd)

	if err != nil {
		return "", err
	}

	open := entry.open
	end := min(open.offset+n, len(open.file.data))
	data := string(open.file.data[open.offset:end])
	open.offset = end

	return data, nil
}

// ANCHOR_END: io

// ANCHOR: fork
// fork returns a child whose table has a copy of every entry. The copies
// refer to the parent's descriptions, and each copy is counted.
func (p *process) fork() *process {
	child := &process{fs: p.fs, limit: p.limit, table: make([]*descriptor, len(p.table))}

	for fd, entry := range p.table {
		if entry != nil {
			entry.open.refs++
			child.table[fd] = &descriptor{open: entry.open, cloexec: entry.cloexec}
		}
	}

	return child
}

// exec closes every descriptor that has the close-on-exec flag.
func (p *process) exec() {
	for fd, entry := range p.table {
		if entry != nil && entry.cloexec {
			p.close(fd)
		}
	}
}

// ANCHOR_END: fork

// ANCHOR: experiments
func numbers(fs *filesystem) error {
	p := newProcess(fs)

	if err := p.close(0); err != nil {
		return err
	}

	fd, err := p.open("file")
	fmt.Printf("descriptor 0 closed: the next open returns %d\n", fd)

	return err
}

func limit(fs *filesystem) error {
	p := newProcess(fs)
	p.limit = 32
	highest := -1

	for {
		fd, err := p.open("file")

		if err != nil {
			fmt.Printf("limit of 32 descriptors: the highest number obtained is %d, the next open fails with %v\n", highest, err)

			return nil
		}

		highest = max(highest, fd)
	}
}

func offsets(fs *filesystem) error {
	p := newProcess(fs)
	first, err := p.open("file")

	if err != nil {
		return err
	}

	duplicate, err := p.dup(first)

	if err != nil {
		return err
	}

	second, err := p.open("file")

	if err != nil {
		return err
	}

	if err := p.write(first, "hello"); err != nil {
		return err
	}

	fmt.Printf("after a write of 5 bytes: offset through the duplicate %d, through a second open %d\n",
		p.table[duplicate].open.offset, p.table[second].open.offset)

	return nil
}

func flags(fs *filesystem) error {
	p := newProcess(fs)
	first, err := p.open("file")

	if err != nil {
		return err
	}

	duplicate, err := p.dup(first)

	if err != nil {
		return err
	}

	p.table[duplicate].open.appendMode = true
	p.table[duplicate].cloexec = true

	fmt.Printf("set on the duplicate, read on the original: O_APPEND %v, close-on-exec %v\n",
		p.table[first].open.appendMode, p.table[first].cloexec)

	return nil
}

// ANCHOR_END: experiments

// ANCHOR: lifetime
func names(fs *filesystem) error {
	fs.create("first")

	if err := fs.link("first", "second"); err != nil {
		return err
	}

	a, b := fs.names["first"], fs.names["second"]
	fmt.Printf("a second name for the file: same inode %v, link count %d\n", a == b, b.links)

	return nil
}

func unlinked(fs *filesystem) error {
	p := newProcess(fs)
	file := fs.create("unlinked")
	file.data = []byte("hello")

	fd, err := p.open("unlinked")

	if err != nil {
		return err
	}

	if err := fs.unlink("unlinked"); err != nil {
		return err
	}

	data, err := p.read(fd, 16)

	if err != nil {
		return err
	}

	fmt.Printf("the name removed, the file still open: link count %d, read through the descriptor returns %q\n",
		file.links, data)

	return p.close(fd)
}

// ANCHOR_END: lifetime

// ANCHOR: redirect
// redirect forks a child, points its descriptors 1 and 2 at the given
// descriptors, and has it write "out" and then "err". It returns the file's
// contents.
func redirect(shell *process, file *inode, stdout, stderr int) (string, error) {
	child := shell.fork()

	if err := child.dup2(stdout, 1); err != nil {
		return "", err
	}

	if err := child.dup2(stderr, 2); err != nil {
		return "", err
	}

	child.exec()

	if err := child.write(1, "out\n"); err != nil {
		return "", err
	}

	if err := child.write(2, "err\n"); err != nil {
		return "", err
	}

	return strings.Join(strings.Fields(string(file.data)), " "), nil
}

func redirections(fs *filesystem) error {
	shell := newProcess(fs)
	file := fs.create("output")
	stdout, err := shell.open("output")

	if err != nil {
		return err
	}

	text, err := redirect(shell, file, stdout, stdout)

	if err != nil {
		return err
	}

	fmt.Printf("> file 2>&1: the file holds %q\n", text)

	file.data = nil
	first, err := shell.open("output")

	if err != nil {
		return err
	}

	second, err := shell.open("output")

	if err != nil {
		return err
	}

	text, err = redirect(shell, file, first, second)

	if err != nil {
		return err
	}

	fmt.Printf("> file 2> file: the file holds %q\n", text)

	return nil
}

// ANCHOR_END: redirect

func main() {
	experiments := []func(*filesystem) error{numbers, limit, offsets, flags, names, unlinked, redirections}

	for _, experiment := range experiments {
		fs := newFilesystem()
		fs.create("file")

		if err := experiment(fs); err != nil {
			log.Fatal(err)
		}
	}
}
