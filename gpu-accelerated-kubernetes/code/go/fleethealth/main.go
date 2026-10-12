// Command fleethealth models the part of a control plane that keeps a fleet of
// GPU machines healthy. It reads failure signals, decides whether each one
// blames a job, a machine, or the network between machines, and moves each
// machine through a lifecycle: cordon, drain, repair, validate, and return.
//
// The fleet is eight machines: five Jetson AGX Thor developer kits on one
// 25 GbE switch, two DGX Sparks joined by a 200 GbE cable, and one Jetson
// Orin NX. The program replays a scripted list of signals without real time
// passing and prints every decision it makes.
//
// Run it from code/go with:
//
//	go run ./fleethealth
package main

import "fmt"

// ANCHOR: fleet
// Node is one machine in the fleet.
type Node struct {
	// Name is the machine's host name.
	Name string
	// Model is the product the machine is.
	Model string
	// Link names the switch or cable that connects the machine to its peers.
	Link string
}

// fleet lists the machines in the order the program reports them.
var fleet = []Node{
	{"thor-1", "Jetson AGX Thor", "switch-25g"},
	{"thor-2", "Jetson AGX Thor", "switch-25g"},
	{"thor-3", "Jetson AGX Thor", "switch-25g"},
	{"thor-4", "Jetson AGX Thor", "switch-25g"},
	{"thor-5", "Jetson AGX Thor", "switch-25g"},
	{"spark-1", "DGX Spark", "cable-200g"},
	{"spark-2", "DGX Spark", "cable-200g"},
	{"orin-nx-1", "Jetson Orin NX", "bench"},
}

// ANCHOR_END: fleet

// ANCHOR: signal
// Kind is the class of a failure signal.
type Kind int

// The classes of signal the model understands.
const (
	AppFault  Kind = iota // the GPU rejected work from one program
	MemoryECC             // an uncorrectable memory error on the GPU
	OffBus                // the GPU stopped answering the driver
	LinkFlap              // the machine's network link went down and up
)

// String returns the class as it appears in the log.
func (k Kind) String() string {
	return [...]string{"application fault", "uncorrectable ECC", "GPU off the bus", "link flap"}[k]
}

// Signal is one failure report from a machine.
type Signal struct {
	// At is the second at which the signal arrived.
	At int
	// Node is the machine that reported it.
	Node string
	// Job is the job that was using the GPU, or "" for a signal with no job.
	Job string
	// Kind is the signal's class.
	Kind Kind
}

// ANCHOR_END: signal

// ANCHOR: state
// State is a machine's place in the repair lifecycle.
type State int

// The lifecycle, in the order a failing machine passes through it.
const (
	Healthy     State = iota // schedulable
	Cordoned                 // no new work; waiting for the disruption budget
	Draining                 // jobs are checkpointing and leaving
	Remediating              // a repair action is running
	Validating               // a burn-in test is running
	Quarantined              // every repair failed; a person has to look
)

// String returns the state's name for the log.
func (s State) String() string {
	return [...]string{"Healthy", "Cordoned", "Draining", "Remediating", "Validating", "Quarantined"}[s]
}

// ladder lists the repair actions from the cheapest to the most thorough.
var ladder = []string{"reset the GPU", "reboot", "reimage"}

// ANCHOR_END: state

// Thresholds and durations, in seconds unless stated otherwise.
const (
	blameAfter   = 3 // distinct jobs (or nodes) before an application fault blames a node (or a job)
	fabricAfter  = 3 // machines on one link that must flap together to blame the link
	fabricWindow = 5 // how close in time those flaps have to be
	budget       = 2 // machines that may be out of service at once
	drainTime    = 4 // time a job gets to write a checkpoint and leave
	repairTime   = 3 // time one repair action takes
	burnInTime   = 3 // time the burn-in test takes
	duration     = 110
)

// record is what the control plane remembers about one machine.
type record struct {
	node  Node
	state State
	// since is the second at which the machine entered its state.
	since int
	// step indexes the next action on the ladder.
	step int
	// faultJobs holds the distinct jobs that have faulted on this machine.
	faultJobs map[string]bool
	// lastFlap is the second of the machine's latest link flap, or -1.
	lastFlap int
}

// Plane is the control plane's state: one record per machine, the nodes each
// job has faulted on, and a scripted answer for each burn-in test.
type Plane struct {
	records []*record
	// jobNodes holds, for each job, the distinct nodes it has faulted on.
	jobNodes map[string]map[string]bool
	// blamed holds the jobs and links already reported, so each is reported once.
	blamed map[string]bool
	// burnIn says how many burn-in tests a machine fails before one passes.
	burnIn map[string]int
}

// NewPlane returns a plane in which every machine is Healthy.
func NewPlane(burnIn map[string]int) *Plane {
	p := &Plane{jobNodes: map[string]map[string]bool{}, blamed: map[string]bool{}, burnIn: burnIn}
	for _, n := range fleet {
		p.records = append(p.records, &record{node: n, faultJobs: map[string]bool{}, lastFlap: -1})
	}
	return p
}

// find returns the record of the named machine.
func (p *Plane) find(name string) *record {
	for _, r := range p.records {
		if r.node.Name == name {
			return r
		}
	}
	panic("unknown node " + name)
}

// move puts a machine in a new state and logs the transition with its reason.
func (p *Plane) move(now int, r *record, to State, why string) {
	fmt.Printf("%4ds  %-10s %-11s -> %-11s %s\n", now, r.node.Name, r.state, to, why)
	r.state, r.since = to, now
}

// ANCHOR: triage
// Observe takes one signal and decides what it blames. A hardware signal
// blames the machine. An application fault blames the job once the job has
// faulted on three machines, and blames the machine once three jobs have
// faulted on it. Link flaps blame the link when three machines on it flap
// within five seconds of each other.
func (p *Plane) Observe(s Signal) {
	r := p.find(s.Node)
	switch s.Kind {
	case MemoryECC, OffBus:
		p.condemn(s.At, r, s.Kind.String())
	case AppFault:
		r.faultJobs[s.Job] = true
		if p.jobNodes[s.Job] == nil {
			p.jobNodes[s.Job] = map[string]bool{}
		}
		p.jobNodes[s.Job][s.Node] = true
		switch {
		case len(p.jobNodes[s.Job]) >= blameAfter && !p.blamed[s.Job]:
			p.blamed[s.Job] = true
			fmt.Printf("%4ds  job %s faulted on %d machines: the job is at fault, no machine is drained\n",
				s.At, s.Job, len(p.jobNodes[s.Job]))
		case len(r.faultJobs) >= blameAfter:
			p.condemn(s.At, r, fmt.Sprintf("%d different jobs faulted here", len(r.faultJobs)))
		}
	case LinkFlap:
		r.lastFlap = s.At
		together := 0
		for _, other := range p.records {
			if other.node.Link == r.node.Link && other.lastFlap >= 0 && s.At-other.lastFlap <= fabricWindow {
				together++
			}
		}
		if together >= fabricAfter && !p.blamed[r.node.Link] {
			p.blamed[r.node.Link] = true
			fmt.Printf("%4ds  %d machines on %s flapped together: the link is at fault, no machine is drained\n",
				s.At, together, r.node.Link)
		}
	}
}

// ANCHOR_END: triage

// condemn cordons a Healthy machine. A machine already under repair stays
// where it is.
func (p *Plane) condemn(now int, r *record, why string) {
	if r.state == Healthy {
		r.step = 0
		p.move(now, r, Cordoned, why)
	}
}

// ANCHOR: budget
// outOfService counts the machines that hold a slot of the disruption budget:
// every machine that is draining, under repair, in burn-in, or quarantined.
func (p *Plane) outOfService() int {
	n := 0
	for _, r := range p.records {
		if r.state >= Draining {
			n++
		}
	}
	return n
}

// ANCHOR_END: budget

// ANCHOR: step
// Step advances every machine by one second. A Cordoned machine starts to
// drain when the budget has a free slot. The other states each last a fixed
// time and then move on; a failed burn-in sends the machine back for the next
// action on the ladder, and a machine with no actions left is quarantined.
func (p *Plane) Step(now int) {
	for _, r := range p.records {
		waited := now - r.since
		switch {
		case r.state == Cordoned && p.outOfService() < budget:
			p.move(now, r, Draining, "jobs told to checkpoint")
		case r.state == Cordoned && waited == 1:
			fmt.Printf("%4ds  %-10s blocked: %d machines are already out of service\n", now, r.node.Name, budget)
		case r.state == Draining && waited >= drainTime:
			p.move(now, r, Remediating, ladder[r.step])
		case r.state == Remediating && waited >= repairTime:
			p.move(now, r, Validating, "burn-in after "+ladder[r.step])
		case r.state == Validating && waited >= burnInTime:
			p.finishBurnIn(now, r)
		}
	}
}

// finishBurnIn acts on the result of a burn-in test. A pass returns the
// machine to service. A failure sends it back for the next action on the
// ladder, and a machine with no actions left is quarantined.
func (p *Plane) finishBurnIn(now int, r *record) {
	if p.burnIn[r.node.Name] == 0 {
		r.faultJobs = map[string]bool{}
		p.move(now, r, Healthy, "burn-in passed")
		return
	}
	p.burnIn[r.node.Name]--
	if r.step+1 == len(ladder) {
		p.move(now, r, Quarantined, "burn-in failed after every action; ticket opened")
		return
	}
	r.step++
	p.move(now, r, Remediating, "burn-in failed; "+ladder[r.step])
}

// ANCHOR_END: step

// ANCHOR: main
// script is the run: the signals in the order they arrive.
var script = []Signal{
	// One job faults on three different Thors.
	{5, "thor-1", "finetune-7b", AppFault},
	{9, "thor-2", "finetune-7b", AppFault},
	{14, "thor-3", "finetune-7b", AppFault},
	// A memory error on a Spark, which one GPU reset repairs.
	{20, "spark-1", "", MemoryECC},
	// A Thor whose GPU stops answering, and which no action repairs.
	{40, "thor-4", "", OffBus},
	// The 25 GbE switch restarts: four Thors lose their link together.
	{60, "thor-1", "", LinkFlap},
	{61, "thor-2", "", LinkFlap},
	{61, "thor-3", "", LinkFlap},
	{62, "thor-5", "", LinkFlap},
	// Two machines fail in the same second while thor-4 is quarantined.
	{80, "spark-2", "", OffBus},
	{80, "orin-nx-1", "", MemoryECC},
}

func main() {
	// thor-4 fails every burn-in; every other machine passes its first.
	p := NewPlane(map[string]int{"thor-4": len(ladder)})
	next := 0
	for now := 0; now <= duration; now++ {
		for ; next < len(script) && script[next].At == now; next++ {
			p.Observe(script[next])
		}
		p.Step(now)
	}
	fmt.Println("final states:")
	for _, r := range p.records {
		fmt.Printf("  %-10s %-16s %s\n", r.node.Name, r.node.Model, r.state)
	}
}

// ANCHOR_END: main
