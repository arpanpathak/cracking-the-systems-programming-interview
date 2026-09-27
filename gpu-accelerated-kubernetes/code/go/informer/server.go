// server.go models the Kubernetes API server. It stores objects, numbers every
// write, keeps a history of recent changes, and serves lists and watches.

package main

import (
	"errors"
	"fmt"
	"maps"
	"slices"
	"strings"
	"sync"
)

// Spec is the part of an object that a user writes: the desired state.
type Spec struct {
	// GPUs is the number of GPUs the job asks for.
	GPUs int
}

// Status is the part of an object that the controller writes: the observed state.
type Status struct {
	// GPUs is the number of GPUs the controller has provided to the job.
	GPUs int
}

// Object is one stored record, such as a training job.
type Object struct {
	// Name identifies the object on the server.
	Name string
	// Spec holds what the user asked for.
	Spec Spec
	// Status holds what the controller has done about it.
	Status Status
	// ResourceVersion is the server's write counter at the object's latest change.
	ResourceVersion int
}

// String formats an object for the demonstration's log lines.
func (o Object) String() string {
	return fmt.Sprintf("%s{spec.GPUs: %d, status.GPUs: %d, v%d}",
		o.Name, o.Spec.GPUs, o.Status.GPUs, o.ResourceVersion)
}

// EventType is the kind of change that an Event records.
type EventType int

// The kinds of change that a watch reports.
const (
	Added    EventType = iota // the object was created
	Modified                  // the object was updated
	Deleted                   // the object was removed
)

// String returns the name that the Kubernetes watch protocol uses for t.
func (t EventType) String() string {
	return [...]string{"ADDED", "MODIFIED", "DELETED"}[t]
}

// Event records one change to one object.
type Event struct {
	// Type is the kind of change.
	Type EventType
	// Object is the object after the change, or its final state if it was deleted.
	Object Object
}

// Errors that the server returns. The first two carry the HTTP status codes
// that the Kubernetes API server uses for the same conditions.
var (
	// ErrGone reports that the history a watch needs has been discarded.
	ErrGone = errors.New("410 Gone: resource version too old")
	// ErrConflict reports a conditional write whose resource version is out of date.
	ErrConflict = errors.New("409 Conflict: object has been modified")
	// ErrUnreachable reports that the client cannot reach the server.
	ErrUnreachable = errors.New("server unreachable")
)

// APIServer stores objects and streams their changes to watchers. Its methods
// are safe for concurrent use.
type APIServer struct {
	// mu guards every field below.
	mu sync.Mutex
	// version is the last resource version the server handed out.
	version int
	// objects holds the current state of every object, keyed by name.
	objects map[string]Object
	// history holds the events newer than compacted, oldest first.
	history []Event
	// compacted is the oldest version from which a watch may resume.
	compacted int
	// watches holds one channel for each open watch.
	watches []chan Event
	// unreachable makes new watches fail, to simulate a network partition.
	unreachable bool
}

// NewAPIServer returns an empty server.
func NewAPIServer() *APIServer {
	return &APIServer{objects: map[string]Object{}}
}

// Update creates or replaces an object and returns ErrConflict if the write's
// condition fails. A non-zero o.ResourceVersion is a condition: the caller read
// the object at that version and wants the write applied only if the object is
// still at it. A zero ResourceVersion writes unconditionally.
func (s *APIServer) Update(o Object) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	current, exists := s.objects[o.Name]
	if o.ResourceVersion != 0 && o.ResourceVersion != current.ResourceVersion {
		return ErrConflict
	}
	eventType := Modified
	if !exists {
		eventType = Added
	}
	s.version++
	o.ResourceVersion = s.version
	s.objects[o.Name] = o
	s.publish(Event{eventType, o})
	return nil
}

// Delete removes the named object, if it exists.
func (s *APIServer) Delete(name string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	o, exists := s.objects[name]
	if !exists {
		return
	}
	delete(s.objects, name)
	s.version++
	o.ResourceVersion = s.version
	s.publish(Event{Deleted, o})
}

// publish appends e to the history and sends it to every open watch.
// The caller must hold s.mu.
func (s *APIServer) publish(e Event) {
	s.history = append(s.history, e)
	for _, w := range s.watches {
		w <- e
	}
}

// List returns every object, sorted by name, and the version at which the
// snapshot was taken.
func (s *APIServer) List() ([]Object, int) {
	s.mu.Lock()
	defer s.mu.Unlock()
	byName := func(a, b Object) int { return strings.Compare(a.Name, b.Name) }
	return slices.SortedFunc(maps.Values(s.objects), byName), s.version
}

// Watch returns a channel that first delivers the stored events newer than
// version and then every new event, until the server closes it.
func (s *APIServer) Watch(version int) (<-chan Event, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	switch {
	case s.unreachable:
		return nil, ErrUnreachable
	case version < s.compacted:
		return nil, ErrGone
	}
	w := make(chan Event, 1024)
	for _, e := range s.history {
		if e.Object.ResourceVersion > version {
			w <- e
		}
	}
	s.watches = append(s.watches, w)
	return w, nil
}

// Compact discards the event history, as etcd discards old versions.
func (s *APIServer) Compact() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.compacted = s.version
	s.history = nil
}

// DropWatches closes every open watch, as a load balancer's idle timeout would.
func (s *APIServer) DropWatches() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.dropWatches()
}

// Partition closes every open watch and makes new watches fail until Heal.
func (s *APIServer) Partition() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.unreachable = true
	s.dropWatches()
}

// Heal ends a partition, so new watches succeed again.
func (s *APIServer) Heal() {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.unreachable = false
}

// dropWatches closes and forgets every watch channel. The caller must hold s.mu.
func (s *APIServer) dropWatches() {
	for _, w := range s.watches {
		close(w)
	}
	s.watches = nil
}
