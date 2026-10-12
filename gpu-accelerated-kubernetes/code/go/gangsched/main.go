// Command gangsched models two decisions a scheduler makes for a training job
// that needs several GPUs at once: whether to start the job, and which
// machines to give it.
//
// The fleet is the eight machines of chapter 4, each with one GPU. The
// program first hands out GPUs one pod at a time and shows two jobs blocking
// each other. It then admits whole jobs, and finally compares two ways of
// choosing a job's machines by the network link the job would have to use.
//
// Run it from code/go with:
//
//	go run ./gangsched
package main

import (
	"fmt"
	"strings"
)

// ANCHOR: fleet
// Node is one machine with one GPU.
type Node struct {
	// Name is the machine's host name.
	Name string
	// Domain names the group of machines that share a fast link.
	Domain string
	// Job is the job that holds the machine's GPU, or "" when it is free.
	Job string
}

// Link is the network path a group of machines shares.
type Link struct {
	// Label is how the link is printed.
	Label string
	// GBps is what the link carries, in gigabytes per second.
	GBps float64
}

// links maps each domain to its link.
var links = map[string]Link{
	"shelf": {"the 25 GbE switch", 3.125},
	"desk":  {"the 200 GbE cable", 25},
	"bench": {"1 GbE", 0.125},
}

// houseNetwork is the link between machines in different domains.
var houseNetwork = Link{"the 1 GbE house network", 0.125}

// newFleet returns the machines in name order, all free.
func newFleet() []*Node {
	return []*Node{
		{Name: "orin-nx-1", Domain: "bench"},
		{Name: "spark-1", Domain: "desk"}, {Name: "spark-2", Domain: "desk"},
		{Name: "thor-1", Domain: "shelf"}, {Name: "thor-2", Domain: "shelf"}, {Name: "thor-3", Domain: "shelf"},
		{Name: "thor-4", Domain: "shelf"}, {Name: "thor-5", Domain: "shelf"},
	}
}

// Job is a group of workers that have to run at the same time, one GPU each.
type Job struct {
	Name    string
	Workers int
}

// ANCHOR_END: fleet

// free returns the machines whose GPU nobody holds, in name order.
func free(fleet []*Node) []*Node {
	var out []*Node

	for _, n := range fleet {
		if n.Job == "" {
			out = append(out, n)
		}
	}

	return out
}

// names joins the names of some machines with spaces.
func names(nodes []*Node) string {
	parts := make([]string, len(nodes))

	for i, n := range nodes {
		parts[i] = n.Name
	}

	return strings.Join(parts, " ")
}

// ANCHOR: podwise
// podAtATime gives each job one GPU in turn until none are left, the way a
// scheduler that sees only single pods would, and reports what each job
// ended up holding.
func podAtATime(fleet []*Node, jobs []Job) {
	held := map[string][]*Node{}

	for progress := true; progress; {
		progress = false

		for _, job := range jobs {
			open := free(fleet)

			if len(held[job.Name]) < job.Workers && len(open) > 0 {
				open[0].Job = job.Name
				held[job.Name] = append(held[job.Name], open[0])
				progress = true
			}
		}
	}

	running := 0

	for _, job := range jobs {
		fmt.Printf("  %-8s holds %d of %d GPUs: %s\n", job.Name, len(held[job.Name]), job.Workers, names(held[job.Name]))

		if len(held[job.Name]) == job.Workers {
			running++
		}
	}

	fmt.Printf("  %d of %d GPUs are held and %d jobs are running\n", len(fleet)-len(free(fleet)), len(fleet), running)
}

// ANCHOR_END: podwise

// ANCHOR: place
// A placer chooses machines for a job from the free ones, or returns nil when
// it cannot place every worker.
type placer func(open []*Node, workers int) []*Node

// firstFree takes the first free machines in name order.
func firstFree(open []*Node, workers int) []*Node {
	if len(open) < workers {
		return nil
	}

	return open[:workers]
}

// byTopology looks for one domain that can hold the whole job and, among
// those, takes the one with the fewest free machines, so that large domains
// stay whole for large jobs. A job that fits in no single domain is spread
// over the first free machines.
func byTopology(open []*Node, workers int) []*Node {
	byDomain := map[string][]*Node{}
	var order []string

	for _, n := range open {
		if byDomain[n.Domain] == nil {
			order = append(order, n.Domain)
		}

		byDomain[n.Domain] = append(byDomain[n.Domain], n)
	}

	best := ""

	for _, domain := range order {
		size := len(byDomain[domain])

		if size >= workers && (best == "" || size < len(byDomain[best])) {
			best = domain
		}
	}

	if best == "" {
		return firstFree(open, workers)
	}

	return byDomain[best][:workers]
}

// ANCHOR_END: place

// ANCHOR: cost
// gradientGB is the size of the gradient every worker contributes per step.
const gradientGB = 14.0

// slowest returns the link a job's all-reduce is limited by: the domain's
// link when every machine is in one domain, and the house network otherwise.
func slowest(nodes []*Node) Link {
	for _, n := range nodes {
		if n.Domain != nodes[0].Domain {
			return houseNetwork
		}
	}

	return links[nodes[0].Domain]
}

// exchangeSeconds is the time one ring all-reduce takes: each worker sends
// 2(n-1)/n gradients over the slowest link.
func exchangeSeconds(nodes []*Node) float64 {
	n := float64(len(nodes))

	return 2 * (n - 1) / n * gradientGB / slowest(nodes).GBps
}

// ANCHOR_END: cost

// ANCHOR: admit
// admit starts a job only when every one of its workers has a machine. It
// reports the placement and what the job's all-reduce will cost, and returns
// false when the job has to wait.
func admit(fleet []*Node, job Job, place placer) bool {
	open := free(fleet)
	nodes := place(open, job.Workers)

	if nodes == nil {
		fmt.Printf("  %-8s waits: it needs %d GPUs and %d are free\n", job.Name, job.Workers, len(open))

		return false
	}

	for _, n := range nodes {
		n.Job = job.Name
	}

	fmt.Printf("  %-8s runs on %s\n", job.Name, names(nodes))

	if len(nodes) > 1 {
		fmt.Printf("           over %s: %.1f s for each all-reduce\n", slowest(nodes).Label, exchangeSeconds(nodes))
	}

	return true
}

// release frees every GPU a job holds.
func release(fleet []*Node, job string) {
	for _, n := range fleet {
		if n.Job == job {
			n.Job = ""
		}
	}

	fmt.Printf("  %-8s finishes\n", job)
}

// ANCHOR_END: admit

// ANCHOR: main
func main() {
	two := []Job{{"train-a", 5}, {"train-b", 5}}

	fmt.Println("one pod at a time, two jobs of five workers:")
	podAtATime(newFleet(), two)

	fmt.Println("whole jobs at a time:")
	fleet := newFleet()
	admit(fleet, two[0], byTopology)
	admit(fleet, two[1], byTopology)
	release(fleet, "train-a")
	admit(fleet, two[1], byTopology)

	three := []Job{{"pair", 2}, {"quad", 4}, {"single", 1}}
	fmt.Println("three jobs, on the first free machines:")
	fleet = newFleet()

	for _, job := range three {
		admit(fleet, job, firstFree)
	}

	fmt.Println("the same three jobs, placed by topology:")
	fleet = newFleet()

	for _, job := range three {
		admit(fleet, job, byTopology)
	}
}

// ANCHOR_END: main
