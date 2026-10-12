// Command fencing shows why a checkpoint store has to check who is writing.
//
// A training job runs on thor-1. The Thor loses its network link and keeps
// training. The control plane sees silence, declares thor-1 dead, and starts
// the job again on thor-2 from the last checkpoint. For a while two copies of
// the job run, and both write checkpoints to the same store.
//
// The program plays that sequence twice: against a store that accepts every
// write, and against a store that remembers the highest epoch it has seen
// and refuses writes that carry an older one.
//
// Run it from code/go with:
//
//	go run ./fencing
package main

import (
	"errors"
	"fmt"
)

// ANCHOR: store
// Checkpoint is what a worker saves: the training step it reached and the
// epoch of the assignment under which it was running.
type Checkpoint struct {
	// Step is the training step the checkpoint holds.
	Step int
	// Epoch is the assignment number the writer was given.
	Epoch int
	// Writer is the host that wrote the checkpoint.
	Writer string
}

// ErrFenced is returned to a writer whose epoch is older than one the store
// has already accepted.
var ErrFenced = errors.New("fenced: a newer assignment has written")

// Store holds the latest checkpoint of one job.
type Store struct {
	// Fencing turns the epoch check on.
	Fencing bool
	// latest is the stored checkpoint.
	latest Checkpoint
}

// Write stores a checkpoint. With fencing on, a checkpoint whose epoch is
// lower than the stored one is refused.
func (s *Store) Write(c Checkpoint) error {
	if s.Fencing && c.Epoch < s.latest.Epoch {
		return ErrFenced
	}

	s.latest = c

	return nil
}

// ANCHOR_END: store

// ANCHOR: assign
// ControlPlane hands out assignments of one job. Each assignment gets the
// next epoch, so a later assignment always carries a higher number.
type ControlPlane struct {
	epoch int
}

// Assign gives the job to a host and returns the epoch of the assignment.
func (c *ControlPlane) Assign(host string) int {
	c.epoch++
	fmt.Printf("  control plane: job assigned to %s with epoch %d\n", host, c.epoch)

	return c.epoch
}

// ANCHOR_END: assign

// ANCHOR: run
// save writes one checkpoint and prints what the store answered.
func save(s *Store, host string, epoch, step int) {
	err := s.Write(Checkpoint{Step: step, Epoch: epoch, Writer: host})

	if err != nil {
		fmt.Printf("  %s writes step %d with epoch %d: refused, %v\n", host, step, epoch, err)

		return
	}

	fmt.Printf("  %s writes step %d with epoch %d: stored\n", host, step, epoch)
}

// run plays the sequence against one store.
func run(s *Store) {
	var plane ControlPlane
	first := plane.Assign("thor-1")
	save(s, "thor-1", first, 1000)
	fmt.Println("  thor-1 loses its link and keeps training; its Lease expires")
	second := plane.Assign("thor-2")
	fmt.Printf("  thor-2 resumes from step %d\n", s.latest.Step)
	save(s, "thor-2", second, 2000)
	fmt.Println("  thor-1's link returns; it still holds epoch 1")
	save(s, "thor-1", first, 1500)
	fmt.Printf("  a restart now resumes from step %d, written by %s\n", s.latest.Step, s.latest.Writer)
}

func main() {
	fmt.Println("a store that accepts every write:")
	run(&Store{})
	fmt.Println("a store that checks the epoch:")
	run(&Store{Fencing: true})
}

// ANCHOR_END: run
