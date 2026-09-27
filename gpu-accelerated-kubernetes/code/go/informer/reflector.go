// reflector.go keeps a Cache current by listing and watching the server.

package main

import (
	"errors"
	"time"
)

// Reflector copies the server's objects into a cache and queues the name of
// every object that changes.
type Reflector struct {
	// server is the source of objects and events.
	server *APIServer
	// cache receives every object the reflector sees.
	cache *Cache
	// queue receives the name of every object that changes.
	queue *WorkQueue
}

// Run lists every object, watches from the list's version, and lists again
// whenever the server can no longer resume the watch. It does not return.
func (r *Reflector) Run() {
	for {
		list, version := r.server.List()
		r.queue.Add(r.cache.Replace(list)...)
		logf("reflector: list at version %d: %v", version, list)
		r.watchFrom(version)
	}
}

// watchFrom applies events from version onward, reopens the watch after each
// disconnect, and returns when the server reports that the history is gone.
func (r *Reflector) watchFrom(version int) {
	for {
		w, err := r.server.Watch(version)
		if errors.Is(err, ErrGone) {
			logf("reflector: watch from version %d: %v", version, err)
			return
		}
		if err != nil {
			time.Sleep(10 * time.Millisecond) // client-go backs off exponentially
			continue
		}
		for e := range w {
			// Update the cache before queueing the name, so that a worker
			// that takes the name reads the object as of this event.
			r.cache.Apply(e)
			r.queue.Add(e.Object.Name)
			version = e.Object.ResourceVersion
		}
		logf("reflector: watch closed, resuming from version %d", version)
	}
}
