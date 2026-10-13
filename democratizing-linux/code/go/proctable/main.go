// Command proctable models the kernel's process table: process numbers handed
// out in a cycle, a parent for every process, a zombie state between exit and
// wait, and a new parent for orphans. It applies a sequence of calls and
// prints the table after each.
//
// Run it from code/go with:
//
//	go run ./proctable
package main

// ANCHOR: imports
import (
	"errors"
	"fmt"
	"log"
	"slices"
	"strings"
)

// ANCHOR_END: imports

// ANCHOR: table
// The errors carry the names of the kernel's error codes for the same cases.
var (
	errAgain   = errors.New("EAGAIN: no process number is free")
	errNoChild = errors.New("ECHILD: the caller has no child to wait for")
	errSearch  = errors.New("ESRCH: no such process")
)

// initPid is the process that adopts orphans.
const initPid = 1

type state byte

const (
	running state = 'R'
	zombie  state = 'Z'
)

// A process is one entry of the table.
type process struct {
	parent int
	state  state
	status int
}

// A table maps process numbers to entries. last is the number given out most
// recently, and pidMax is the largest number allowed.
type table struct {
	procs  map[int]*process
	last   int
	pidMax int
}

func newTable(pidMax int) *table {
	return &table{
		procs:  map[int]*process{initPid: {state: running}},
		last:   initPid,
		pidMax: pidMax,
	}
}

// ANCHOR_END: table

// ANCHOR: fork
// allocate returns the first free number after last, wrapping around from
// pidMax to the number after initPid.
func (t *table) allocate() (int, error) {
	pid := t.last

	for range t.pidMax {
		pid++

		if pid > t.pidMax {
			pid = initPid + 1
		}

		if _, used := t.procs[pid]; !used {
			t.last = pid

			return pid, nil
		}
	}

	return 0, errAgain
}

// fork creates a child of parent and returns the child's number.
func (t *table) fork(parent int) (int, error) {
	if _, ok := t.procs[parent]; !ok {
		return 0, errSearch
	}

	pid, err := t.allocate()

	if err != nil {
		return 0, err
	}

	t.procs[pid] = &process{parent: parent, state: running}

	return pid, nil
}

// ANCHOR_END: fork

// ANCHOR: exit
// exit ends a process. The entry stays in the table as a zombie that holds
// the exit status, and the children of the process become children of init.
func (t *table) exit(pid, status int) error {
	p, ok := t.procs[pid]

	if !ok {
		return errSearch
	}

	p.state, p.status = zombie, status

	for _, child := range t.procs {
		if child.parent == pid {
			child.parent = initPid
		}
	}

	return nil
}

// ANCHOR_END: exit

// ANCHOR: wait
// wait removes a zombie child of parent from the table and returns its number
// and exit status. ok is false when parent has children and none of them has
// exited, the case in which the kernel suspends the caller.
func (t *table) wait(parent int) (pid, status int, ok bool, err error) {
	children := 0

	for _, pid := range t.pids() {
		child := t.procs[pid]

		if child.parent != parent {
			continue
		}

		children++

		if child.state == zombie {
			delete(t.procs, pid)

			return pid, child.status, true, nil
		}
	}

	if children == 0 {
		return 0, 0, false, errNoChild
	}

	return 0, 0, false, nil
}

// pids returns the process numbers in use, in increasing order.
func (t *table) pids() []int {
	pids := make([]int, 0, len(t.procs))

	for pid := range t.procs {
		pids = append(pids, pid)
	}

	slices.Sort(pids)

	return pids
}

// ANCHOR_END: wait

// ANCHOR: trace
// String renders the table as pid(parent)state for each entry.
func (t *table) String() string {
	var cells []string

	for _, pid := range t.pids() {
		p := t.procs[pid]
		cells = append(cells, fmt.Sprintf("%d(%d)%c", pid, p.parent, p.state))
	}

	return strings.Join(cells, " ")
}

// A call is one step of the trace: an operation, the process it applies to,
// and for exit the status.
type call struct {
	op     string
	pid    int
	status int
}

// apply performs a call and describes its result.
func (t *table) apply(c call) (string, error) {
	switch c.op {
	case "fork":
		child, err := t.fork(c.pid)

		return fmt.Sprintf("fork by %d: pid %d", c.pid, child), err

	case "exit":
		return fmt.Sprintf("exit of %d, status %d", c.pid, c.status), t.exit(c.pid, c.status)

	default:
		child, status, ok, err := t.wait(c.pid)

		if !ok {
			return fmt.Sprintf("wait by %d: would block", c.pid), err
		}

		return fmt.Sprintf("wait by %d: pid %d, status %d", c.pid, child, status), nil
	}
}

func main() {
	t := newTable(6)

	calls := []call{
		{op: "fork", pid: 1},
		{op: "fork", pid: 2},
		{op: "fork", pid: 3},
		{op: "wait", pid: 2},
		{op: "exit", pid: 3},
		{op: "wait", pid: 2},
		{op: "fork", pid: 2},
		{op: "exit", pid: 4, status: 7},
		{op: "wait", pid: 1},
		{op: "fork", pid: 2},
		{op: "fork", pid: 2},
	}

	fmt.Printf("%-30s %s\n", "start", t)

	for _, c := range calls {
		result, err := t.apply(c)

		if err != nil {
			log.Fatal(err)
		}

		fmt.Printf("%-30s %s\n", result, t)
	}
}

// ANCHOR_END: trace
