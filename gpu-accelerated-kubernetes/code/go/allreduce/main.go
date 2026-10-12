// Command allreduce runs one step of distributed training's communication:
// five workers each hold a gradient, and every worker has to end the step
// holding the sum of all five.
//
// The workers are goroutines connected in a ring by channels, and they run
// the ring all-reduce algorithm. The program runs the step three ways: with
// every worker healthy, with one worker failing part of the way through, and
// then as arithmetic, to find how often a job of a given size should save a
// checkpoint.
//
// Run it from code/go with:
//
//	go run ./allreduce
package main

import (
	"errors"
	"fmt"
	"math"
	"strings"
	"sync"
	"time"
)

// ANCHOR: worker
// message carries one chunk of a gradient from a worker to its right-hand
// neighbour.
type message struct {
	// chunk is the index of the chunk within the gradient.
	chunk int
	// value is the chunk's contents: one number stands for the whole chunk.
	value int
}

// Worker is one machine's part in the step.
type Worker struct {
	// id is the worker's position in the ring, from 0.
	id int
	// gradient holds one value per chunk. It starts as this worker's own
	// gradient and ends as the sum over all workers.
	gradient []int
	// in receives from the left-hand neighbour, and out sends to the right.
	in  <-chan message
	out chan<- message
	// failAfter is the number of messages the worker exchanges before it
	// fails, or -1 for a worker that stays healthy.
	failAfter int
}

// errFailed is the result of the worker that the run makes fail.
var errFailed = errors.New("failed")

// patience is how long a worker waits for its neighbour before giving up.
const patience = 100 * time.Millisecond

// ANCHOR_END: worker

// name returns the host name of the worker at a ring position.
func name(id int) string { return fmt.Sprintf("thor-%d", id+1) }

// mod returns a modulo n as a value from 0 to n-1, for negative a as well.
func mod(a, n int) int { return ((a % n) + n) % n }

// ANCHOR: run
// Run performs the worker's 2(n-1) exchanges. In each one it sends a chunk to
// the right and receives a chunk from the left. During the first n-1
// exchanges it adds what it receives to its own chunk. During the last n-1
// the chunks it receives are finished sums, and it stores them. Run returns
// the number of exchanges completed and the reason it stopped early, if any.
func (w *Worker) Run(n int) (int, error) {
	for step := range 2 * (n - 1) {
		if step == w.failAfter {
			return step, errFailed
		}
		// The chunk to send moves one place back around the gradient each
		// step, so after the first step it is the chunk just received.
		chunk := mod(w.id-step, n)
		w.out <- message{chunk, w.gradient[chunk]}
		reducing := step < n-1

		select {
		case m := <-w.in:
			if reducing {
				w.gradient[m.chunk] += m.value
			} else {
				w.gradient[m.chunk] = m.value
			}
		case <-time.After(patience):
			return step, fmt.Errorf("no chunk from %s within %v", name(mod(w.id-1, n)), patience)
		}
	}
	return 2 * (n - 1), nil
}

// ANCHOR_END: run

// ANCHOR: ring
// result is what one worker reports when it stops.
type result struct {
	steps int
	err   error
}

// ring connects n workers in a circle, runs them all at once, and returns the
// workers and their results. The worker at position failing stops after
// failAfter exchanges; pass -1 for a run with no failure.
func ring(n, failing, failAfter int) ([]*Worker, []result) {
	// Each link holds every message a worker can send in one step, so a send
	// goes through even when the receiver has stopped.
	links := make([]chan message, n)
	for i := range links {
		links[i] = make(chan message, 2*(n-1))
	}
	workers := make([]*Worker, n)
	for i := range workers {
		gradient := make([]int, n)
		for chunk := range gradient {
			gradient[chunk] = i + 1 + 10*chunk
		}
		workers[i] = &Worker{id: i, gradient: gradient, in: links[i], out: links[mod(i+1, n)], failAfter: -1}
	}
	if failing >= 0 {
		workers[failing].failAfter = failAfter
	}

	results := make([]result, n)
	var wg sync.WaitGroup
	for i, w := range workers {
		wg.Go(func() {
			steps, err := w.Run(n)
			results[i] = result{steps, err}
		})
	}
	wg.Wait()
	return workers, results
}

// ANCHOR_END: ring

// show formats a gradient as its values separated by spaces.
func show(gradient []int) string {
	return strings.Trim(fmt.Sprint(gradient), "[]")
}

// ANCHOR: checkpoint
// Costs and failure rates for the checkpoint arithmetic, in seconds.
const (
	// checkpointCost is the time one checkpoint takes to write.
	checkpointCost = 50.0
	// machineMTBF is the mean time between failures of one machine: 30 days.
	machineMTBF = 30 * 24 * 3600.0
)

// interval returns the time between checkpoints that loses the least work,
// by Young's formula: the square root of twice the checkpoint cost times the
// job's mean time between failures.
func interval(jobMTBF float64) float64 {
	return math.Sqrt(2 * checkpointCost * jobMTBF)
}

// ANCHOR_END: checkpoint

// ANCHOR: main
func main() {
	const n = 5

	fmt.Printf("ring all-reduce over %d workers, %d chunks each:\n", n, n)
	workers, _ := ring(n, -1, 0)
	for i := range n {
		own := make([]int, n)
		for chunk := range own {
			own[chunk] = i + 1 + 10*chunk
		}
		fmt.Printf("  %s starts with %-17s and ends with %s\n", name(i), show(own), show(workers[i].gradient))
	}
	sent := 2 * (n - 1)
	fmt.Printf("  each worker sent %d chunks, %.1f times its gradient; %d messages in all\n",
		sent, float64(sent)/n, sent*n)

	fmt.Printf("the same step, with %s failing after 2 of its %d exchanges:\n", name(2), sent)
	_, results := ring(n, 2, 2)
	for i, r := range results {
		fmt.Printf("  %s stopped after %d of %d: %v\n", name(i), r.steps, sent, r.err)
	}

	fmt.Println("checkpoint interval, for a 50 s checkpoint and one failure per machine every 30 days:")
	fmt.Println("  machines  job fails every  checkpoint every  time lost")
	for _, machines := range []int{1, 5, 64, 512} {
		jobMTBF := machineMTBF / float64(machines)
		every := interval(jobMTBF)
		lost := checkpointCost/every + every/(2*jobMTBF)
		fmt.Printf("  %8d  %10.1f hours  %9.0f minutes  %8.1f%%\n", machines, jobMTBF/3600, every/60, lost*100)
	}
}

// ANCHOR_END: main
