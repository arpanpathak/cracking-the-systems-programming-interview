// Command phi compares two ways of deciding that a host has failed: a fixed
// timeout, and the phi accrual failure detector, which learns how regular each
// host's heartbeats are and reports how unlikely the current silence is.
//
// Two simulated hosts both send a heartbeat about once a second. One is
// steady; the other sits on a congested network and its heartbeats arrive
// between 0.4 and 2.4 seconds apart. For each host, the program prints the
// detector's suspicion level, phi, after different lengths of silence, next to
// the verdict of a 2-second timeout.
//
// Run it from code/go with:
//
//	go run ./phi
package main

import (
	"fmt"
	"math"
)

// ANCHOR: detector
// timeout is the fixed timeout that the program compares against, in seconds.
const timeout = 2.0

// minStdDev is the smallest standard deviation the detector assumes, in
// seconds. Without it, a perfectly regular host would make any delay look
// infinitely suspicious.
const minStdDev = 0.2

// Detector is a phi accrual failure detector for one host.
type Detector struct {
	// intervals holds the most recent gaps between heartbeats, in seconds.
	intervals []float64
	// window is the number of gaps the detector remembers.
	window int
	// last is the time of the most recent heartbeat, in seconds.
	last float64
}

// NewDetector returns a detector that remembers window gaps and has seen a
// first heartbeat at time first.
func NewDetector(window int, first float64) *Detector {
	return &Detector{window: window, last: first}
}

// Heartbeat records a heartbeat that arrived at time now.
func (d *Detector) Heartbeat(now float64) {
	d.intervals = append(d.intervals, now-d.last)
	if len(d.intervals) > d.window {
		d.intervals = d.intervals[1:]
	}
	d.last = now
}

// ANCHOR_END: detector

// ANCHOR: phi
// Phi returns the suspicion level at time now: minus the base-10 logarithm of
// the probability that a heartbeat would still arrive after this much silence,
// given the gaps seen so far. Phi 1 means a 10% chance the host is fine, phi 2
// means 1%, and phi 3 means 0.1%.
func (d *Detector) Phi(now float64) float64 {
	var mean float64
	for _, gap := range d.intervals {
		mean += gap
	}
	mean /= float64(len(d.intervals))
	var variance float64
	for _, gap := range d.intervals {
		variance += (gap - mean) * (gap - mean)
	}
	stdDev := math.Max(math.Sqrt(variance/float64(len(d.intervals))), minStdDev)

	// The probability that a gap is longer than the current silence, from a
	// logistic approximation of the normal distribution.
	silence := now - d.last
	y := (silence - mean) / stdDev
	e := math.Exp(-y * (1.5976 + 0.070566*y*y))
	pLater := 1 - 1/(1+e)
	if silence > mean {
		pLater = e / (1 + e)
	}
	return -math.Log10(pLater)
}

// ANCHOR_END: phi

// ANCHOR: main
// hosts lists the simulated hosts and the gaps between their heartbeats.
var hosts = []struct {
	name string
	gaps []float64
}{
	{"steady", []float64{1.0, 1.02, 0.98, 1.01, 0.99, 1.0, 1.03, 0.97, 1.0, 1.0}},
	{"jittery", []float64{0.4, 1.9, 0.6, 1.7, 0.5, 1.8, 0.7, 1.6, 0.4, 2.4}},
}

// main feeds each host's heartbeats to a detector and prints phi after
// increasing lengths of silence.
func main() {
	for _, host := range hosts {
		detector := NewDetector(100, 0)
		var now float64
		for _, gap := range host.gaps {
			now += gap
			detector.Heartbeat(now)
		}
		fmt.Printf("%s host, silent for:\n", host.name)
		for _, silence := range []float64{1.0, 1.5, 2.0, 2.5, 3.0, 4.0} {
			verdict := "alive"
			if silence > timeout {
				verdict = "dead"
			}
			fmt.Printf("  %.1fs  phi = %6.2f   %.0fs timeout says %s\n",
				silence, detector.Phi(now+silence), timeout, verdict)
		}
	}
}

// ANCHOR_END: main
