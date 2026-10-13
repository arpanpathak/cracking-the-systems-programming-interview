// Command cgmodel models the control group hierarchy: every group counts the
// processes and the memory of its whole subtree, a fork is refused when any
// group above it is at its limit, and a group that exceeds its memory limit
// loses the largest process in its subtree.
//
// Run it from code/go with:
//
//	go run ./cgmodel
package main

// ANCHOR: imports
import (
	"errors"
	"fmt"
	"math"
)

// ANCHOR_END: imports

// ANCHOR: types
// unlimited is the value of a limit that is written "max" in a control file.
const unlimited = math.MaxInt

var errAgain = errors.New("EAGAIN")

// A group is one node of the hierarchy. pids and memory are the usage of the
// group and of every group below it. refused and oomKills are the counters
// the kernel publishes in pids.events and memory.events.
type group struct {
	name      string
	parent    *group
	children  []*group
	processes []*process

	pidsMax, memoryMax int
	pids, memory       int
	refused, oomKills  int
}

// A process belongs to one group and holds an amount of memory.
type process struct {
	name   string
	home   *group
	memory int
}

// child adds a group below g, with no limits of its own.
func (g *group) child(name string) *group {
	c := &group{name: name, parent: g, pidsMax: unlimited, memoryMax: unlimited}
	g.children = append(g.children, c)

	return c
}

// ANCHOR_END: types

// ANCHOR: pids
// spawn starts a process in g. The process is counted in g and in every
// group above it, so it is refused when any of them is at its limit.
func (g *group) spawn(name string) (*process, error) {
	for up := g; up != nil; up = up.parent {
		if up.pids == up.pidsMax {
			up.refused++

			return nil, errAgain
		}
	}

	for up := g; up != nil; up = up.parent {
		up.pids++
	}

	p := &process{name: name, home: g}
	g.processes = append(g.processes, p)

	return p, nil
}

// ANCHOR_END: pids

// ANCHOR: memory
// charge adds an amount, which may be negative, to the memory count of a
// group and of every group above it.
func (g *group) charge(amount int) {
	for up := g; up != nil; up = up.parent {
		up.memory += amount
	}
}

// allocate gives a process more memory. While a group above the process is
// over its limit, the largest process in that group's subtree is killed. It
// returns the names of the processes killed.
func (p *process) allocate(amount int) []string {
	p.memory += amount
	p.home.charge(amount)

	var killed []string

	for up := p.home; up != nil; up = up.parent {
		for up.memory > up.memoryMax {
			victim := up.largest()
			up.oomKills++
			killed = append(killed, victim.name)
			victim.kill()
		}
	}

	return killed
}

// largest returns the process with the most memory in the subtree of g.
func (g *group) largest() *process {
	var found *process

	for _, p := range g.processes {
		if found == nil || p.memory > found.memory {
			found = p
		}
	}

	for _, c := range g.children {
		if p := c.largest(); p != nil && (found == nil || p.memory > found.memory) {
			found = p
		}
	}

	return found
}

// kill removes a process from its group and returns its memory and its
// place in the process count.
func (p *process) kill() {
	p.home.charge(-p.memory)

	for up := p.home; up != nil; up = up.parent {
		up.pids--
	}

	for i, other := range p.home.processes {
		if other == p {
			p.home.processes = append(p.home.processes[:i], p.home.processes[i+1:]...)

			break
		}
	}
}

// ANCHOR_END: memory

// ANCHOR: trace
func main() {
	team := &group{name: "team", pidsMax: 4, memoryMax: 100}
	jobA, jobB := team.child("job-a"), team.child("job-b")

	var started []*process

	for _, start := range []struct {
		in   *group
		name string
	}{{jobA, "a1"}, {jobA, "a2"}, {jobA, "a3"}, {jobB, "b1"}} {
		p, err := start.in.spawn(start.name)

		if err != nil {
			fmt.Println(err)

			return
		}

		started = append(started, p)
	}

	fmt.Printf("3 processes in job-a and 1 in job-b: pids.current job-a %d, job-b %d, team %d\n",
		jobA.pids, jobB.pids, team.pids)

	_, err := jobB.spawn("b2")
	fmt.Printf("another process in job-b, team at pids.max 4: %v, pids.events max of team %d\n", err, team.refused)

	a1, b1 := started[0], started[3]

	a1.allocate(60)
	fmt.Printf("a1 allocates 60: memory.current job-a %d, job-b %d, team %d\n", jobA.memory, jobB.memory, team.memory)

	killed := b1.allocate(50)
	fmt.Printf("b1 allocates 50, team at memory.max 100: killed %v, oom_kill of team %d\n", killed, team.oomKills)
	fmt.Printf("afterwards: memory.current job-a %d, job-b %d, team %d, pids.current team %d\n",
		jobA.memory, jobB.memory, team.memory, team.pids)
}

// ANCHOR_END: trace
