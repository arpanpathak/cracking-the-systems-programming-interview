// cache.go holds the client's local copy of the server's objects.

package main

import "sync"

// Cache is the client's copy of the server's objects, kept current by a
// Reflector. Its methods are safe for concurrent use.
type Cache struct {
	// mu guards objects.
	mu sync.RWMutex
	// objects holds the latest known state of every object, keyed by name.
	objects map[string]Object
}

// NewCache returns an empty cache.
func NewCache() *Cache {
	return &Cache{objects: map[string]Object{}}
}

// Get returns the cached copy of the named object and whether it exists.
func (c *Cache) Get(name string) (Object, bool) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	o, ok := c.objects[name]
	return o, ok
}

// Apply records one event from a watch.
func (c *Cache) Apply(e Event) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if e.Type == Deleted {
		delete(c.objects, e.Object.Name)
		return
	}
	c.objects[e.Object.Name] = e.Object
}

// Replace installs the result of a fresh list and returns the names of the
// objects that changed, including objects that disappeared while the client
// was not watching.
func (c *Cache) Replace(list []Object) []string {
	c.mu.Lock()
	defer c.mu.Unlock()
	old := c.objects
	c.objects = make(map[string]Object, len(list))
	var changed []string
	for _, o := range list {
		c.objects[o.Name] = o
		// A name missing from old reads as version 0, so it counts as changed.
		if old[o.Name].ResourceVersion != o.ResourceVersion {
			changed = append(changed, o.Name)
		}
	}
	for name := range old {
		if _, ok := c.objects[name]; !ok {
			changed = append(changed, name)
		}
	}
	return changed
}
