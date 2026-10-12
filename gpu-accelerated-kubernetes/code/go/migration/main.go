// Command migration models the live migration of a virtual machine: moving a
// running VM's memory from one host to another while the VM keeps running.
//
// The model is the pre-copy algorithm. Each round sends the memory that
// changed during the round before it. The VM is paused only for the last
// round, when what remains is small enough to send within the allowed pause.
// The program runs the algorithm for VMs of two sizes over the links in our
// fleet and prints each round.
//
// Run it from code/go with:
//
//	go run ./migration
package main

import "fmt"

// ANCHOR: types
// VM describes the virtual machine being moved.
type VM struct {
	// Name labels the VM in the output.
	Name string
	// MemoryGB is the size of the VM's memory.
	MemoryGB float64
	// DirtyGBps is how much memory the VM's programs change each second.
	DirtyGBps float64
}

// Link is the network path between the two hosts.
type Link struct {
	// Name labels the link in the output.
	Name string
	// GBps is what the link carries, in gigabytes per second. A link of
	// 8 gigabits per second carries 1 gigabyte per second.
	GBps float64
}

// Limits of the algorithm.
const (
	// maxPauseSeconds is the longest the VM may be paused for the last round.
	maxPauseSeconds = 0.3
	// maxRounds ends a migration that keeps making progress too slowly.
	maxRounds = 30
	// throttleStep is how much more the guest is slowed each time a round
	// fails to shrink the remaining memory, as a fraction of full speed.
	throttleStep = 0.2
	// maxThrottle is the most the guest may be slowed.
	maxThrottle = 0.8
)

// ANCHOR_END: types

// ANCHOR: migrate
// Migrate runs pre-copy rounds until the remaining memory can be sent within
// the allowed pause, and prints each round. With throttle set, it slows the
// guest whenever a round leaves as much memory to send as it started with.
func Migrate(vm VM, link Link, throttle bool) {
	fmt.Printf("%s over %s", vm.Name, link.Name)

	if throttle {
		fmt.Print(", with throttling")
	}

	fmt.Println(":")

	remaining := vm.MemoryGB // memory still to be sent
	slowed := 0.0            // fraction by which the guest is slowed
	elapsed := 0.0

	for round := 1; round <= maxRounds; round++ {
		if remaining <= link.GBps*maxPauseSeconds {
			pause := remaining / link.GBps
			fmt.Printf("  round %2d: VM paused, %.2f GB sent in %.2f s\n", round, remaining, pause)
			fmt.Printf("  done in %.1f s; the VM was paused for %.0f ms\n", elapsed+pause, pause*1000)

			return
		}

		seconds := remaining / link.GBps
		dirtied := min(vm.DirtyGBps*(1-slowed)*seconds, vm.MemoryGB)
		fmt.Printf("  round %2d: %6.2f GB sent in %6.1f s, %6.2f GB changed meanwhile\n",
			round, remaining, seconds, dirtied)
		elapsed += seconds

		if dirtied >= remaining {
			if !throttle || slowed >= maxThrottle {
				fmt.Println("  does not converge: memory changes as fast as the link carries it")

				return
			}

			slowed += throttleStep
			fmt.Printf("            no progress: guest slowed to %.0f%% of full speed\n", (1-slowed)*100)
		}

		remaining = dirtied
	}

	fmt.Printf("  gave up after %d rounds\n", maxRounds)
}

// ANCHOR_END: migrate

// ANCHOR: main
func main() {
	// An inference VM sized for the Orin NX, and a training VM sized for a
	// Thor or a Spark.
	inference := VM{"16 GB inference VM (0.2 GB/s changed)", 16, 0.2}
	training := VM{"100 GB training VM (4 GB/s changed)", 100, 4}

	// The links in the fleet, in gigabytes per second.
	orin := Link{"1 GbE", 0.125}
	lane := Link{"one 25 GbE lane", 3.125}
	bonded := Link{"four bonded 25 GbE lanes", 12.5}
	spark := Link{"the Sparks' 200 GbE cable", 25}

	Migrate(inference, orin, false)
	Migrate(inference, lane, false)
	Migrate(training, lane, false)
	Migrate(training, lane, true)
	Migrate(training, bonded, false)
	Migrate(training, spark, false)
}

// ANCHOR_END: main
