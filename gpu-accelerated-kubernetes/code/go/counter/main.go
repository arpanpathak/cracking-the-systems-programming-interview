// Command counter shows how replicas of a service that cannot always reach
// each other can keep one count.
//
// Three replicas of a usage service run beside the three groups of machines
// in our fleet: the shelf, the desk, and the bench. Each records the GPU time
// that jobs near it report. The program counts in four ways: with one number
// per replica, with a grow-only counter, with a counter that also goes down,
// and with a quota divided into allowances.
//
// Run it from code/go with:
//
//	go run ./counter
package main

import "fmt"

// The replicas, by index.
const (
	shelf = iota
	desk
	bench
	replicas
)

// names lists the replicas in index order.
var names = [replicas]string{"shelf", "desk", "bench"}

// ANCHOR: gcounter
// GCounter is a count that only grows. It keeps one entry per replica, and
// each replica adds only to its own entry.
type GCounter [replicas]int

// Add records n more at the given replica.
func (c *GCounter) Add(replica, n int) { c[replica] += n }

// Merge takes, entry by entry, the larger of this counter's value and the
// other's. Merging is safe to repeat and to do in any order.
func (c *GCounter) Merge(other GCounter) {
	for i := range c {
		c[i] = max(c[i], other[i])
	}
}

// Value is the count: the sum of every replica's entry.
func (c GCounter) Value() int {
	total := 0

	for _, n := range c {
		total += n
	}

	return total
}

// ANCHOR_END: gcounter

// ANCHOR: pncounter
// PNCounter is a count that goes up and down, built from two counters that
// only grow: one for the increments and one for the decrements.
type PNCounter struct {
	Up, Down GCounter
}

// Add records a change of n, which may be negative, at the given replica.
func (c *PNCounter) Add(replica, n int) {
	if n >= 0 {
		c.Up.Add(replica, n)
	} else {
		c.Down.Add(replica, -n)
	}
}

// Merge merges both halves.
func (c *PNCounter) Merge(other PNCounter) {
	c.Up.Merge(other.Up)
	c.Down.Merge(other.Down)
}

// Value is the increments minus the decrements.
func (c PNCounter) Value() int { return c.Up.Value() - c.Down.Value() }

// ANCHOR_END: pncounter

// ANCHOR: naive
// oneNumber counts with a single number per replica and synchronises by
// keeping the larger of two numbers.
func oneNumber() {
	totals := [replicas]int{}
	adds := [replicas]int{300, 120, 40}
	sum := 0

	for r, n := range adds {
		totals[r] += n
		sum += n
		fmt.Printf("  %-5s records %d GPU-seconds\n", names[r], n)
	}

	largest := max(totals[shelf], totals[desk], totals[bench])
	fmt.Printf("  after synchronising, every replica says %d; the jobs used %d\n", largest, sum)
}

// ANCHOR_END: naive

// show prints one replica's counter and its value.
func show(replica int, c GCounter) {
	fmt.Printf("  %-5s holds %v = %d\n", names[replica], [replicas]int(c), c.Value())
}

// ANCHOR: grow
// growOnly counts the same usage with a GCounter at each replica, through a
// partition that cuts the bench off from the other two.
func growOnly() {
	var at [replicas]GCounter

	for r, n := range [replicas]int{300, 120, 40} {
		at[r].Add(r, n)
	}

	fmt.Println("  the bench is cut off; shelf and desk exchange counters")
	at[shelf].Merge(at[desk])
	at[desk].Merge(at[shelf])
	at[shelf].Add(shelf, 60)
	at[bench].Add(bench, 25)

	for r := range at {
		show(r, at[r])
	}

	fmt.Println("  the network heals; counters are exchanged in no particular order, some twice")
	at[desk].Merge(at[bench])
	at[shelf].Merge(at[desk])
	at[bench].Merge(at[shelf])
	at[desk].Merge(at[shelf])
	at[desk].Merge(at[shelf])

	for r := range at {
		show(r, at[r])
	}
}

// ANCHOR_END: grow

// ANCHOR: updown
// upAndDown counts GPUs in use. A job's start and its end may be recorded at
// different replicas.
func upAndDown() {
	var at [replicas]PNCounter
	at[shelf].Add(shelf, 3)  // three jobs start on the Thors
	at[desk].Add(desk, 2)    // two start on the Sparks
	at[shelf].Add(shelf, -1) // one Thor job ends
	at[bench].Add(bench, -1) // the bench replica hears that a Spark job ended

	for r := range at {
		for other := range at {
			at[r].Merge(at[other])
		}
	}

	c := at[bench]
	fmt.Printf("  started %v, ended %v: %d GPUs in use\n", [replicas]int(c.Up), [replicas]int(c.Down), c.Value())
}

// ANCHOR_END: updown

// ANCHOR: quota
// quota is the number of GPUs one team may use at once.
const quota = 6

// sharedLimit lets each replica admit a job whenever its own view of the
// count leaves room under the quota.
func sharedLimit() {
	var at [replicas]PNCounter
	at[shelf].Add(shelf, 3)
	at[desk].Add(desk, 1)
	at[shelf].Merge(at[desk])
	at[desk].Merge(at[shelf])
	fmt.Printf("  both replicas see %d of %d in use; then they lose contact\n", at[shelf].Value(), quota)

	for _, r := range []int{shelf, desk} {
		if at[r].Value()+2 <= quota {
			at[r].Add(r, 2)
			fmt.Printf("  %-5s admits a 2-GPU job: by its count, %d of %d are in use\n", names[r], at[r].Value(), quota)
		}
	}

	at[shelf].Merge(at[desk])
	fmt.Printf("  after they merge: %d of %d in use\n", at[shelf].Value(), quota)
}

// allowances gives each replica a share of the quota. A replica admits a job
// only from its own share, and shares move between replicas when they can
// reach each other.
func allowances() {
	share := [replicas]int{4, 2, 0}
	used := [replicas]int{3, 1, 0}
	fmt.Printf("  shares %v, in use %v; then the replicas lose contact\n", share, used)
	admit := func(r, gpus int) {
		if left := share[r] - used[r]; left < gpus {
			fmt.Printf("  %-5s refuses a %d-GPU job: its share has %d left\n", names[r], gpus, left)

			return
		}

		used[r] += gpus
		fmt.Printf("  %-5s admits a %d-GPU job\n", names[r], gpus)
	}
	admit(shelf, 2)
	admit(desk, 2)
	fmt.Println("  contact returns; desk gives its unused GPU to shelf")
	share[desk]--
	share[shelf]++
	admit(shelf, 2)
	fmt.Printf("  shares %v, in use %v: %d of %d\n", share, used, used[shelf]+used[desk]+used[bench], quota)
}

// ANCHOR_END: quota

func main() {
	fmt.Println("one number per replica:")
	oneNumber()
	fmt.Println("one entry per replica, merged by taking the larger:")
	growOnly()
	fmt.Println("a count that goes down as well:")
	upAndDown()
	fmt.Println("a quota checked against each replica's own count:")
	sharedLimit()
	fmt.Println("a quota divided into shares:")
	allowances()
}
