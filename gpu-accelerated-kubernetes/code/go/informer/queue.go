// queue.go implements the work queue between the reflector and the controller.

package main

import "sync"

// WorkQueue stores the names of objects that need reconciling. A name waits
// in the queue at most once, and a name that a worker holds is handed to no
// other worker until the first calls Done.
type WorkQueue struct {
	// mu guards every field below.
	mu sync.Mutex
	// cond wakes workers blocked in Get.
	cond *sync.Cond
	// queue holds the names ready for a worker, in arrival order.
	queue []string
	// dirty holds every name that needs processing.
	dirty map[string]bool
	// processing holds every name that a worker currently holds.
	processing map[string]bool
}

// NewWorkQueue returns an empty queue.
func NewWorkQueue() *WorkQueue {
	q := &WorkQueue{dirty: map[string]bool{}, processing: map[string]bool{}}
	q.cond = sync.NewCond(&q.mu)
	return q
}

// Add marks each name as needing processing. A name that is already pending
// is left where it is. A name that a worker holds is queued again by Done.
func (q *WorkQueue) Add(names ...string) {
	q.mu.Lock()
	defer q.mu.Unlock()
	for _, name := range names {
		if q.dirty[name] {
			continue
		}
		q.dirty[name] = true
		if !q.processing[name] {
			q.queue = append(q.queue, name)
			q.cond.Signal()
		}
	}
}

// Get blocks until a name is ready and hands it to the caller.
func (q *WorkQueue) Get() string {
	q.mu.Lock()
	defer q.mu.Unlock()
	for len(q.queue) == 0 {
		q.cond.Wait()
	}
	name := q.queue[0]
	q.queue = q.queue[1:]
	delete(q.dirty, name)
	q.processing[name] = true
	return name
}

// Done releases a name that Get handed out, and queues it again if it was
// added while the worker held it.
func (q *WorkQueue) Done(name string) {
	q.mu.Lock()
	defer q.mu.Unlock()
	delete(q.processing, name)
	if q.dirty[name] {
		q.queue = append(q.queue, name)
		q.cond.Signal()
	}
}
