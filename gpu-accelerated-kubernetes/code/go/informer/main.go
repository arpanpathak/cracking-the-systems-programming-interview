// Command informer models how a Kubernetes controller learns about objects:
// a server that numbers every write, a reflector that lists and watches into
// a local cache, a work queue of names, and a controller that reconciles them.
// It then causes a burst of edits, a dropped connection, and a partition, and
// logs how each part responds.
//
// Run it from code/go with:
//
//	go run ./informer
package main

import (
	"fmt"
	"log"
	"time"
)

// start is the time the program began, for the relative timestamps in the log.
var start = time.Now()

// logf prints one log line prefixed with the milliseconds since start.
func logf(format string, args ...any) {
	log.Printf("%4dms  %s", time.Since(start).Milliseconds(), fmt.Sprintf(format, args...))
}

func main() {
	log.SetFlags(0)
	server := NewAPIServer()
	server.Update(Object{Name: "job-a", Spec: Spec{GPUs: 1}})
	server.Update(Object{Name: "job-b", Spec: Spec{GPUs: 8}})

	cache := NewCache()
	queue := NewWorkQueue()
	go (&Reflector{server, cache, queue}).Run()
	go (&Controller{server, cache, queue}).Run()
	time.Sleep(100 * time.Millisecond)

	logf("--- job-a is edited five times in a burst")
	for gpus := 2; gpus <= 6; gpus++ {
		server.Update(Object{Name: "job-a", Spec: Spec{GPUs: gpus}})
		if gpus == 2 {
			time.Sleep(5 * time.Millisecond) // the controller starts on the first edit
		}
	}
	time.Sleep(150 * time.Millisecond)

	logf("--- the watch connection drops")
	server.DropWatches()
	time.Sleep(50 * time.Millisecond)

	logf("--- partition: job-b is deleted and the history compacted meanwhile")
	server.Partition()
	server.Delete("job-b")
	server.Compact()
	time.Sleep(30 * time.Millisecond)
	server.Heal()
	time.Sleep(150 * time.Millisecond)

	list, version := server.List()
	logf("final state at version %d: %v", version, list)
}
