// Command heartbeats models how a control plane tracks which machines in a
// fleet are alive. Every host sends a heartbeat once a second. The registry
// keeps each host's last heartbeat in memory, runs a sweep once a second, and
// records a durable write only when a host changes state: Up, Suspect, or Dead.
//
// The program simulates 10,000 hosts for 60 seconds without real time passing.
// Host 42 crashes at second 20, and host 7 misses four heartbeats from second
// 30 to second 33. It prints how many heartbeats the registry handled, how many
// durable writes it made, and each write.
//
// Run it from code/go with:
//
//	go run ./heartbeats
package main

import "fmt"

// ANCHOR: types
// State is what the registry believes about a host.
type State int

// The states a host moves through.
const (
	Up      State = iota // heartbeats are arriving
	Suspect              // heartbeats stopped recently; the host may be slow
	Dead                 // heartbeats stopped long enough to give up on the host
)

// String returns the state's name for the log.
func (s State) String() string {
	return [...]string{"Up", "Suspect", "Dead"}[s]
}

// Thresholds and the size of the simulation, in seconds and hosts.
const (
	suspectAfter = 3      // seconds without a heartbeat before a host is Suspect
	deadAfter    = 10     // seconds without a heartbeat before a host is Dead
	hostCount    = 10_000 // hosts in the fleet
	duration     = 60     // seconds simulated
)

// entry is the registry's in-memory record of one host.
type entry struct {
	// lastSeen is the second of the host's most recent heartbeat.
	lastSeen int
	// state is the host's current state.
	state State
}

// Transition is one durable write: a host entering a new state.
type Transition struct {
	// At is the second at which the sweep or heartbeat noticed the change.
	At int
	// Host is the host's number.
	Host int
	// State is the state the host entered.
	State State
}

// Registry holds the liveness of every host.
type Registry struct {
	// hosts is indexed by host number.
	hosts []entry
	// heartbeats counts the heartbeats handled in memory.
	heartbeats int
	// writes lists the durable writes, in order.
	writes []Transition
}

// ANCHOR_END: types

// ANCHOR: registry
// NewRegistry returns a registry in which every host is Up, as it would be
// after the hosts registered.
func NewRegistry(n int) *Registry {
	return &Registry{hosts: make([]entry, n)}
}

// Heartbeat records a heartbeat from host at second now. Only a host that was
// not Up costs a durable write.
func (r *Registry) Heartbeat(now, host int) {
	r.heartbeats++
	e := &r.hosts[host]
	e.lastSeen = now

	if e.state != Up {
		e.state = Up
		r.writes = append(r.writes, Transition{now, host, Up})
	}
}

// Sweep re-evaluates every host at second now and records each change of state.
func (r *Registry) Sweep(now int) {
	for host := range r.hosts {
		e := &r.hosts[host]

		if next := stateAfter(now - e.lastSeen); next != e.state {
			e.state = next
			r.writes = append(r.writes, Transition{now, host, next})
		}
	}
}

// stateAfter returns the state of a host that has been silent for the given
// number of seconds.
func stateAfter(silent int) State {
	switch {
	case silent >= deadAfter:
		return Dead
	case silent >= suspectAfter:
		return Suspect
	default:
		return Up
	}
}

// ANCHOR_END: registry

// ANCHOR: main
// sendsHeartbeat reports whether host sends a heartbeat at second now in the
// simulation.
func sendsHeartbeat(host, now int) bool {
	switch host {
	case 42:
		return now < 20 // crashes at second 20
	case 7:
		return now < 30 || now >= 34 // silent from second 30 to 33
	default:
		return true
	}
}

// main runs the simulation and prints the registry's work.
func main() {
	registry := NewRegistry(hostCount)

	for now := 0; now < duration; now++ {
		for host := 0; host < hostCount; host++ {
			if sendsHeartbeat(host, now) {
				registry.Heartbeat(now, host)
			}
		}

		registry.Sweep(now)
	}

	fmt.Printf("heartbeats handled in memory: %d\n", registry.heartbeats)
	fmt.Printf("durable writes:               %d\n", len(registry.writes))

	for _, w := range registry.writes {
		fmt.Printf("  second %2d  host %2d -> %s\n", w.At, w.Host, w.State)
	}
}

// ANCHOR_END: main
