// controller.go reconciles objects whose names arrive on the work queue.

package main

import "time"

// Controller makes each object's status agree with its spec.
type Controller struct {
	// server receives the controller's status writes.
	server *APIServer
	// cache supplies the current state of each object.
	cache *Cache
	// queue supplies the names of objects to reconcile.
	queue *WorkQueue
}

// Run is a single worker: it takes names from the queue one at a time and
// reconciles them. It does not return.
func (c *Controller) Run() {
	for {
		name := c.queue.Get()
		err := c.reconcile(name)
		c.queue.Done(name)
		if err != nil {
			c.queue.Add(name) // client-go requeues with a backoff
		}
	}
}

// reconcile reads the named object from the cache and, if its status differs
// from its spec, writes a new status conditioned on the version it read.
func (c *Controller) reconcile(name string) error {
	o, ok := c.cache.Get(name)
	if !ok {
		logf("reconcile %s: deleted, releasing its GPUs", name)
		return nil
	}
	if o.Status.GPUs == o.Spec.GPUs {
		return nil
	}
	time.Sleep(20 * time.Millisecond) // slow work, such as starting containers
	o.Status.GPUs = o.Spec.GPUs
	if err := c.server.Update(o); err != nil {
		logf("reconcile %s: write at version %d: %v", name, o.ResourceVersion, err)
		return err
	}
	logf("reconcile %s: status.GPUs = %d", name, o.Status.GPUs)
	return nil
}
