# 1. Keeping a local copy of the cluster

In this chapter, we will learn how a Kubernetes controller keeps an exact, current copy of
the objects it manages, and how it turns changes to those objects into work. A
*controller* is a program that compares what users asked for with what exists and acts
on the difference. Our running example is a controller for GPU training jobs: when a user
creates a job that asks for 1 GPU, the controller starts a container on a machine with a
free GPU; when the user raises the request to 2, it replaces the container; when the user
deletes the job, it stops the container and frees the GPU.

Every controller in Kubernetes is built from the same 4 parts: a *reflector* that lists
and watches the API server, a *cache* that holds the result, a *work queue* of object
names, and a *reconcile* function that acts on one name at a time. We will first derive
each part from the problem it solves, then build all 4 in Go and in Rust, run them
through a burst of edits, a dropped connection and a network partition, and finally map
each one onto client-go, the library that real Go controllers use.

The Go files are in `code/go/informer` and run with `go run ./informer` from `code/go`.
The Rust files are in `code/rust/informer` and run with `cargo run -p informer` from
`code/rust`. Neither needs anything beyond its language's standard library.

<div class="covers">

This chapter covers

- objects, the API server, and the revision counter in etcd behind every resource version
- optimistic concurrency, and the `409 Conflict` that protects a write
- list and watch, the invariant that joins them, and the `410 Gone` that forces a relist
- the reflector, the cache, the work queue and the reconcile function, in Go and in Rust
- level-triggered control, and why it survives lost events
- the same design in client-go: DeltaFIFO, indexers, shared informers, rate limits

</div>

## 1.1 Objects and the API server

<div class="definition">

**Definition 1.1** (Object). An *object* is a named record stored by Kubernetes. Its
*spec* holds the state a user asked for, such as "run this image with 1 GPU". Its
*status* holds the state a controller has observed, such as "running on 1 GPU".

</div>

All objects live behind 1 HTTP service, the *API server*. Every read and every write of
every object goes through it, and it persists the objects in etcd, a replicated key-value
store. Users, `kubectl` and controllers are all clients of the API server, and none of
them talks to etcd directly.

A controller needs 2 things from the API server: an exact view of every object of its
kind, and notice of each change within a fraction of a second. The obvious way to get both
is to ask for every object every few seconds, and it does not scale. A cluster with
50,000 pods stores about 4 KB of JSON per pod, so 1 request for all of them transfers
200 MB. If 12 controllers did that every 5 seconds, the API server would send 480 MB per
second, while only a handful of pods change between 2 requests. The API server therefore
offers a second kind of read: a stream of changes. A stream needs a way to name a point in
the history of the store, so that a client whose connection breaks can ask for everything
after the last change it saw. That name is the resource version.

## 1.2 Resource versions

etcd keeps a single counter, the *revision*, for the whole store. Every create, update and
delete of any key takes the next value of the counter, and etcd keeps the old values of a
key under their old revisions until a compaction removes them. Figure 1.1 shows 12 writes
to 4 keys and the index etcd keeps from each key to the revisions that wrote it.

<figure>
<img src="figures/ch01-revisions.svg" alt="Twelve writes numbered 1 to 12, coloured by the key they wrote: job-a, job-b, pod-1 and pod-2. Below, the key index lists for each key the revisions that wrote it. job-a was written at 1, 4, 5, 9 and 11, so its resourceVersion is 11.">
<figcaption><b>Figure 1.1</b> The revision counter in etcd. Each object's resource version is the revision of its latest write.</figcaption>
</figure>

<div class="definition">

**Definition 1.2** (Resource version). The *resource version* of an object is the etcd
revision of the last write that changed it. The resource version of a list is the
revision of the store at the moment the list was read.

</div>

The API conventions require clients to treat resource versions as opaque strings, to be
compared only for equality and passed back to the server unchanged. Our model uses
integers so that we can print and compare them, and nothing in the design depends on
their order except inside the server.

The resource version serves 2 purposes. The first is the stream of changes in section 1.3.
The second is safe concurrent writing. Two clients that read the same object and write it
back would otherwise overwrite each other: each sends a whole object, and the second write
replaces the first one's change with the value it read before that change. Figure 1.2
traces this case, with the server refusing the second write.

<figure>
<img src="figures/ch01-conflict.svg" alt="Client A and client B both read job-a at version 7. A writes 2 GPUs with version 7 and the server accepts it as version 8. B writes a new image with version 7 and the server answers 409 Conflict. B reads version 8, writes again with version 8, and the server stores version 9 with both changes.">
<figcaption><b>Figure 1.2</b> Optimistic concurrency. A write carries the version it was based on, and the server accepts it only if the object is still at that version.</figcaption>
</figure>

<div class="definition">

**Definition 1.3** (Conditional write). An update that carries a resource version
succeeds only if the stored object still has that version. Otherwise the API server
rejects it with `409 Conflict`, and the client must read the object again and reapply
its change.

</div>

This scheme is called *optimistic concurrency*. No client holds a lock on the object.
Each assumes that nobody else will write in the meantime, and the server detects the
cases where that assumption failed at the only moment that matters, when the write
arrives.

## 1.3 List, then watch

With numbered writes, a client can build an exact view of the cluster in 2 requests.

<div class="definition">

**Definition 1.4** (List and watch). A *list* returns every object of a kind together
with the resource version of the store at the time of the read. A *watch* from version
*v* is a long-lived request that returns, in order, 1 *event* for every change with a
revision greater than *v*: `ADDED`, `MODIFIED` or `DELETED`, each carrying the object as
it was after the change, or its last state for a deletion.

</div>

The list and the watch are 2 separate requests, and other clients keep writing between
them. Consider a list read at version 10, a user edits a job at version 11, and the
watch opens when the store is at version 12. If the watch asks for changes after the
version the store has when it opens, the edit at 11 is never delivered. If it asks for
changes after the list's version, the server replays 11 and 12 from its history and then
continues with new events. Figure 1.3 compares the 2 choices.

<figure>
<img src="figures/ch01-list-watch-gap.svg" alt="Two rows of versions 8 to 14. In both a list is taken at version 10. In the first row the watch starts from 10, and versions 11 to 14 are delivered. In the second the watch starts from 12, the version current when it opened, and versions 11 and 12 are missed.">
<figcaption><b>Figure 1.3</b> A watch from the list's version covers every write after the snapshot. A watch from the current version leaves a gap.</figcaption>
</figure>

<div class="invariant">

**Invariant 1.1** (No gap, no duplicate). Let a client list at version *v* and then
watch from *v*. Its view after applying events up to version *u* equals the state of the
store at *u*: the snapshot covers every write up to *v*, and the watch delivers every
write after *v* exactly once.

</div>

kube-apiserver does not send every watch to etcd. For each resource type it keeps a *watch
cache*: the current objects and a window of recent events in memory, fed by a single etcd
watch. Most watches, and lists that accept slightly stale data, are served from it. A list
with no resource version is a *consistent read*, which must reflect every write
acknowledged before the request; until Kubernetes 1.31 such reads went to etcd as quorum
reads, and since 1.31, with a recent enough etcd, the API server serves them from the watch
cache after checking that the cache has caught up with etcd's current revision.

## 1.4 When the history runs out

A watch can only replay events the server still has. etcd keeps every revision of every
key until it is told to discard old ones. That clean-up is called *compaction*, and
kube-apiserver requests one every 5 minutes by default. The watch cache also holds only a
bounded window of events. A watch that asks to resume from a version older than what
remains cannot be served, and the API server answers `410 Gone`. The only way back to an
exact view is a new list.

Watches also end for ordinary reasons. kube-apiserver closes every watch after a random
timeout between 30 and 60 minutes, by default, so that thousands of clients do not
reconnect at the same moment. A load balancer may close a connection that has been quiet
for too long, and a network partition may make the server unreachable for a while. A
reflector has to tell these endings apart, because only 1 of them requires a list.

<figure>
<img src="figures/ch01-watch-endings.svg" alt="A watch from version v can end in 3 ways. If the stream closes, the reflector watches again from v. If the server is unreachable, it waits and retries from v, doubling the wait after each failure. If the server answers 410 Gone, v is older than the compaction point and the reflector lists again.">
<figcaption><b>Figure 1.4</b> The 3 ways a watch ends. Resuming from <i>v</i> is correct in the first 2 because the cache is exact up to <i>v</i>.</figcaption>
</figure>

A watch on a kind of object that rarely changes receives few events, so the version it
would resume from grows old and falls behind the next compaction even though nothing was
missed. The API server addresses this with *bookmark* events, which carry a resource
version and no object and move a quiet watch's position forward.

## 1.5 The cache

Once the client has listed and is watching, it can keep its own copy of every object in
memory, exact up to the last event applied. Reading an object becomes a map lookup, and
the API server sends each change to each process once.

A cache needs 2 operations. *Apply* records 1 event: it stores the object for `ADDED` and
`MODIFIED` and removes it for `DELETED`. *Replace* installs the result of a new list, and
it has a second duty that events cannot perform. When a relist follows `410 Gone`, some
objects may have been deleted while the client was cut off, and their `DELETED` events
were discarded by the compaction. No event will ever report those deletions. The only
evidence is that the objects are in the old cache and absent from the new list.

<figure>
<img src="figures/ch01-replace.svg" alt="Four objects compared between the old cache and a new list taken at version 12. job-a went from 9 to 11 and is reported modified. job-b is in the old cache but not in the list and is reported deleted. job-c is new and reported added. job-d is unchanged at 6 and is not queued.">
<figcaption><b>Figure 1.5</b> Replace compares the old cache with the new list. A name that is in the cache and missing from the list is a deletion whose event no longer exists.</figcaption>
</figure>

<div class="algorithm">

**Algorithm 1.1** Replace(*cache*, *list*) returns the names that changed

1. *changed* ← empty list
2. for each object *o* in *list*:
    1. if *cache* has no entry for *o*.name, or its version differs from *o*.version, append *o*.name to *changed*
3. for each name *n* in *cache* that is not in *list*: append *n* to *changed*
4. *cache* ← the objects of *list*, by name
5. return *changed*

</div>

## 1.6 The reflector

<div class="definition">

**Definition 1.5** (Reflector). A *reflector* is the loop that keeps a cache equal to the
server's state. It lists, installs the list with Replace, watches from the list's
version, applies each event, and starts over with a list when the watch fails with
`410 Gone`.

</div>

<div class="algorithm">

**Algorithm 1.2** Reflector(*server*, *cache*, *queue*)

1. loop:
    1. (*objects*, *v*) ← *server*.List()
    2. add every name returned by Replace(*cache*, *objects*) to *queue*
    3. WatchFrom(*v*); when it returns, continue at step 1.1
2. WatchFrom(*v*):
    1. open a watch from *v*; if the server is unreachable, wait and repeat this step
    2. if the server answers `410 Gone`, return
    3. for each event *e*: Apply(*cache*, *e*); add *e*.object.name to *queue*; *v* ← *e*.version
    4. when the stream closes, go to step 2.1 with the same *v*

</div>

The variable *v* always holds the version of the last event applied to the cache, so the
cache is exact up to *v* and a new watch from *v* resumes with nothing missing. Step 2.3
also fixes an order: the cache is updated before the name is queued. In the other order a
worker could take the name, read the cache before the update lands, find nothing to do,
and finish; the name would not be queued again, and the change would wait until the object
happened to change once more. Figure 1.6 shows both orders with the same event.

<figure>
<img src="figures/ch01-order.svg" alt="Two orderings of the reflector's steps. Left: the name is queued before the cache is updated, a worker reads the old spec of 1 GPU, finds nothing to do, and the edit to 2 GPUs is never handled. Right: the cache is updated first, so the worker reads 2 GPUs and acts.">
<figcaption><b>Figure 1.6</b> The cache is updated before the name is queued, so any worker that takes the name reads the change.</figcaption>
</figure>

<div class="invariant">

**Invariant 1.2** (Cache before queue). When a worker takes a name from the queue, the
cache already reflects every event that caused the name to be queued.

</div>

## 1.7 The work queue

The reflector learns about changes, and the controller acts on them. The direct
connection, a call into the controller for every event, fails in 2 ways. A user who edits
a job 5 times in 1 second produces 5 events, and a controller called 5 times starts work
for 4 specs that are already out of date. After a relist, Replace reports which names
changed, and the individual events that led there no longer exist, so a controller that
depends on seeing every event misses changes each time history is compacted.

The queue therefore carries *names* of objects, and the controller reads each object's
current state from the cache when it reaches the name. 5 edits put the same name in the
queue 5 times, and if the queue ignores a name it already holds, they collapse into 1
reconcile of the latest spec. The controller takes names in 1 or more *workers*, each
processing 1 name at a time.

<div class="definition">

**Definition 1.6** (Work queue). A *work queue* holds a FIFO list *ready* and 2 sets of
names. *dirty* holds every name that needs processing. *processing* holds every name a
worker has taken and not yet returned.

</div>

<div class="algorithm">

**Algorithm 1.3** The 3 operations of the work queue, each under 1 lock

1. Add(*n*): if *n* ∈ *dirty*, return. Insert *n* into *dirty*. If *n* ∉ *processing*, append *n* to *ready* and wake 1 waiting worker.
2. Get(): wait until *ready* is non-empty. Remove its first name *n*, move *n* from *dirty* to *processing*, return *n*.
3. Done(*n*): remove *n* from *processing*. If *n* ∈ *dirty*, append *n* to *ready* and wake 1 waiting worker.

</div>

The *processing* set handles a change that arrives while a worker is reconciling the same
object. Without it, the event would make the name ready again, a second worker would take
it, and 2 workers would act on 1 object at once. With status writes, one of them fails
with a conflict and its work is wasted; with actions outside Kubernetes, such as starting
a container, both succeed and the job ends up with 2 containers. With the set, Add marks
the name dirty and keeps it out of *ready*, and Done makes it ready again once the first
worker has finished. Figure 1.7 follows 1 name through that sequence.

<figure>
<img src="figures/ch01-queue-states.svg" alt="The ready list, the dirty set and the processing set after each call: Add puts job-a in ready and dirty; Get moves it to processing; Adds during the reconcile mark it dirty only; Done makes it ready again; a second Get starts a reconcile that reads the latest spec.">
<figcaption><b>Figure 1.7</b> The state of the queue after each call. The name is never in <i>ready</i> while it is in <i>processing</i>.</figcaption>
</figure>

<div class="invariant">

**Invariant 1.3** (One worker per name). A name is in *processing* for at most 1 worker,
and it appears in *ready* at most once.

</div>

Animation 1.1 plays the same sequence with the burst of 5 edits from the run in section
1.10. Its last part repeats the calls on a queue without the *processing* set, and a
second worker takes the name while the first is still working.

<figure class="anim">
<video class="motion" src="figures/work-queue.mp4" autoplay loop muted playsinline preload="metadata" aria-label="Three boxes, ready, dirty and processing, above a worker. Add puts job-a in ready and dirty. Get moves it to processing and the worker starts a reconcile. Four more Add calls during the reconcile mark the name dirty and leave ready empty. Done moves the name back to ready, and a second reconcile reads a spec of 6 GPUs. In the last part the processing set is removed: an Add during the reconcile makes the name ready, and a second worker takes it while the first is still working." data-chapters="[[0.0, &quot;Add&quot;], [7.86, &quot;Get&quot;], [18.06, &quot;Add while held&quot;], [33.66, &quot;Done&quot;], [46.86, &quot;no processing set&quot;]]"><img src="figures/work-queue.gif" alt="Three boxes, ready, dirty and processing, above a worker. Add puts job-a in ready and dirty. Get moves it to processing and the worker starts a reconcile. Four more Add calls during the reconcile mark the name dirty and leave ready empty. Done moves the name back to ready, and a second reconcile reads a spec of 6 GPUs. In the last part the processing set is removed: an Add during the reconcile makes the name ready, and a second worker takes it while the first is still working."></video>
<figcaption><b>Animation 1.1</b> One name through the work queue. 5 edits lead to 2 reconciles, and the 2 never overlap.</figcaption>
</figure>

A worker that calls Get on an empty queue must sleep without holding the lock, or Add
could never acquire it to insert a name. Both implementations use a *condition variable*
(`sync.Cond` in Go, `std::sync::Condvar` in Rust), whose wait releases the lock and
sleeps in 1 atomic step. The wait sits in a loop that checks *ready* again on waking,
because with several workers another may have taken the name first.

## 1.8 Reconciling

<div class="definition">

**Definition 1.7** (Reconcile). To *reconcile* an object is to read its current spec,
compare it with the state of the world, act to remove the difference, and record the
result in its status.

</div>

A reconcile looks only at the object's current state, and it does not know why it was
called. A name queued once and a name queued 10 times lead to the same action, and so do
a change reported by an event and a change discovered by a relist. This style is called
*level-triggered*, after the circuits that respond to the present level of a signal. An
*edge-triggered* controller responds to each change of the signal, 1 action per event.
Figure 1.8 runs both against the same burst of edits.

<figure>
<img src="figures/ch01-edge-level.svg" alt="Five edits of a job's GPU count, to 2, 3, 4, 5 and 6. An edge-triggered handler runs once per edit, 5 times, and 4 of those runs act on specs that were already replaced. A level-triggered reconcile runs twice and each time reads the current spec from the cache, first 2 and then 6.">
<figcaption><b>Figure 1.8</b> An edge-triggered controller does 1 action per event. A level-triggered controller does 1 action per state it reads, and a lost event costs it nothing.</figcaption>
</figure>

The cache trails the server by the time an event takes to arrive, and a reconcile takes
time to act. If a user changes the spec during that time and the controller writes its
copy back unconditionally, it stores the old spec together with a status computed for
the old spec, and the user's edit disappears. The controller therefore writes with the
resource version it read (Definition 1.3). If the object changed, the write fails with
`409 Conflict`, the worker returns the name to the queue, and the next reconcile reads the
newer object from the cache.

## 1.9 The model in Go and in Rust

Figure 1.9 assembles the parts. The API server numbers every write; inside the
controller's process, the reflector applies each event to the cache and then queues the
name; a worker takes the name, reads the cache, and writes the status back with the
version it read.

<figure>
<img src="figures/informer-pipeline.svg" alt="The API server numbers every write and stores objects in etcd. Inside the controller's process, the reflector receives events, applies each one to the cache, and then adds the object's name to the work queue. The controller gets a name from the queue, reads the object from the cache, and writes the status back to the API server with the version it read.">
<figcaption><b>Figure 1.9</b> The path of 1 change: an event, the cache, the work queue, a reconcile, and a conditional write back to the server.</figcaption>
</figure>

<div class="lld">

Low-level design: the model

| Part | Holds | Rule it keeps |
|---|---|---|
| `Object` | a name, a spec, a status, a version | the version is the revision of the write that last changed it |
| `APIServer` | the objects, the revision counter, recent events, the open watches | every write takes the next revision and publishes 1 event |
| `Cache` | a copy of every object | exact up to the last event applied (Invariant 1.1) |
| `Reflector` | the server, the cache, the queue | updates the cache before it queues a name (Invariant 1.2) |
| `WorkQueue` | *ready*, *dirty*, *processing* | a name is with at most 1 worker (Invariant 1.3) |
| `Controller` | the server, the cache, the queue | acts on the current state and writes conditionally |

</div>

The server keeps the objects in memory, numbers every write, records recent events and
answers lists and watches. It also has 4 methods that exist only to reproduce failures
on request: `Compact`, `DropWatches`, `Partition` and `Heal`. The model reduces a job to a
GPU count in its spec and in its status.

<p class="listing"><b>Listing 1.1</b> Objects, events, and the 2 errors, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">code/go/informer/server.go</a></p>

```go
{{#include ../code/go/informer/server.go:objects}}
```

<p class="listing"><b>Listing 1.2</b> Objects, events, and the 2 errors, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">code/rust/informer/src/server.rs</a></p>

```rust
{{#include ../code/rust/informer/src/server.rs:objects}}
```

The server is 1 lock around 4 things: the objects, the counter, the events it still
has, and the open watches.

<p class="listing"><b>Listing 1.3</b> The server's state, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">code/go/informer/server.go</a></p>

```go
{{#include ../code/go/informer/server.go:server}}
```

<p class="listing"><b>Listing 1.4</b> The server's state, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">code/rust/informer/src/server.rs</a></p>

```rust
{{#include ../code/rust/informer/src/server.rs:server}}
```

`Update` implements Definition 1.3. A version of 0 skips the check, which the
demonstration uses to play a user editing a job; any other version must equal the stored
one, and a missing object counts as version 0. `Delete` publishes the object's final
state under a new version.

<p class="listing"><b>Listing 1.5</b> Update, delete, and publish, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">code/go/informer/server.go</a></p>

```go
{{#include ../code/go/informer/server.go:writes}}
```

<p class="listing"><b>Listing 1.6</b> Update, delete, and publish, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">code/rust/informer/src/server.rs</a></p>

```rust
{{#include ../code/rust/informer/src/server.rs:writes}}
```

`Watch` holds the server lock while it replays the history and registers the new watch,
and `publish` runs under the same lock. Every event is therefore either in the replayed
history or delivered after registration, which is Invariant 1.1 on the server side.

<p class="listing"><b>Listing 1.7</b> List and watch, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">code/go/informer/server.go</a></p>

```go
{{#include ../code/go/informer/server.go:listwatch}}
```

<p class="listing"><b>Listing 1.8</b> List and watch, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">code/rust/informer/src/server.rs</a></p>

```rust
{{#include ../code/rust/informer/src/server.rs:listwatch}}
```

A Go watch buffers 1,024 events; a client that stopped reading would eventually block
`publish` while it holds the lock and stall every writer. The real API server
therefore closes a watch that falls too far behind. The Rust channel is unbounded. Go ends a watch
by closing its channel, and Rust by dropping the sender.

<p class="listing"><b>Listing 1.9</b> Compaction, dropped watches, and partitions, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">code/go/informer/server.go</a></p>

```go
{{#include ../code/go/informer/server.go:faults}}
```

<p class="listing"><b>Listing 1.10</b> Compaction, dropped watches, and partitions, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">code/rust/informer/src/server.rs</a></p>

```rust
{{#include ../code/rust/informer/src/server.rs:faults}}
```

The cache is a map behind a read-write lock, because every reconcile reads it and only
the reflector writes it. `Replace` is Algorithm 1.1. A new object has no cached version:
Go reads the missing entry as version 0 and Rust compares against `None`, so both report
it as changed.

<p class="listing"><b>Listing 1.11</b> The cache and Apply, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/cache.go">code/go/informer/cache.go</a></p>

```go
{{#include ../code/go/informer/cache.go:cache}}
```

<p class="listing"><b>Listing 1.12</b> The cache and Apply, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/cache.rs">code/rust/informer/src/cache.rs</a></p>

```rust
{{#include ../code/rust/informer/src/cache.rs:cache}}
```

<p class="listing"><b>Listing 1.13</b> Replace, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/cache.go">code/go/informer/cache.go</a></p>

```go
{{#include ../code/go/informer/cache.go:replace}}
```

<p class="listing"><b>Listing 1.14</b> Replace, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/cache.rs">code/rust/informer/src/cache.rs</a></p>

```rust
{{#include ../code/rust/informer/src/cache.rs:replace}}
```

The reflector is Algorithm 1.2: `Run` is its outer loop, and `watchFrom` (`watch_from`
in Rust) is step 2. The model retries an unreachable server every 10 milliseconds; client-go
doubles the wait after each failure in a row, up to a cap, so that thousands of clients do
not overload a server that is recovering.

<p class="listing"><b>Listing 1.15</b> The reflector's list step, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/reflector.go">code/go/informer/reflector.go</a></p>

```go
{{#include ../code/go/informer/reflector.go:run}}
```

<p class="listing"><b>Listing 1.16</b> The reflector's list step, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/reflector.rs">code/rust/informer/src/reflector.rs</a></p>

```rust
{{#include ../code/rust/informer/src/reflector.rs:run}}
```

<p class="listing"><b>Listing 1.17</b> Watching from a version, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/reflector.go">code/go/informer/reflector.go</a></p>

```go
{{#include ../code/go/informer/reflector.go:watch}}
```

<p class="listing"><b>Listing 1.18</b> Watching from a version, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/reflector.rs">code/rust/informer/src/reflector.rs</a></p>

```rust
{{#include ../code/rust/informer/src/reflector.rs:watch}}
```

The work queue is Definition 1.6 and Algorithm 1.3.

<p class="listing"><b>Listing 1.19</b> The queue's state, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/queue.go">code/go/informer/queue.go</a></p>

```go
{{#include ../code/go/informer/queue.go:state}}
```

<p class="listing"><b>Listing 1.20</b> The queue's state, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/queue.rs">code/rust/informer/src/queue.rs</a></p>

```rust
{{#include ../code/rust/informer/src/queue.rs:state}}
```

<p class="listing"><b>Listing 1.21</b> Add, Get, and Done, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/queue.go">code/go/informer/queue.go</a></p>

```go
{{#include ../code/go/informer/queue.go:ops}}
```

<p class="listing"><b>Listing 1.22</b> Add, Get, and Done, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/queue.rs">code/rust/informer/src/queue.rs</a></p>

```rust
{{#include ../code/rust/informer/src/queue.rs:ops}}
```

`reconcile` is Definition 1.7. A missing object was deleted, and a real controller would
release what it had set up for it; the model logs a message. A status that matches the
spec needs no action. Otherwise a 20-millisecond sleep stands in for the work, and the
status is written with the version that was read. The worker loop returns a name whose
reconcile failed to the queue, so the next attempt starts from whatever the cache holds by
then.

<p class="listing"><b>Listing 1.23</b> Reconciling 1 name, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/controller.go">code/go/informer/controller.go</a></p>

```go
{{#include ../code/go/informer/controller.go:reconcile}}
```

<p class="listing"><b>Listing 1.24</b> Reconciling 1 name, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/controller.rs">code/rust/informer/src/controller.rs</a></p>

```rust
{{#include ../code/rust/informer/src/controller.rs:reconcile}}
```

<p class="listing"><b>Listing 1.25</b> The worker loop, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/controller.go">code/go/informer/controller.go</a></p>

```go
{{#include ../code/go/informer/controller.go:run}}
```

<p class="listing"><b>Listing 1.26</b> The worker loop, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/controller.rs">code/rust/informer/src/controller.rs</a></p>

```rust
{{#include ../code/rust/informer/src/controller.rs:run}}
```

## 1.10 Running the model

`main` creates 2 jobs, starts the reflector and 1 worker, and then causes each situation
from this chapter in turn: a burst of 5 edits during a reconcile, a dropped watch, and a
partition during which a job is deleted and the history is compacted. Go runs the
reflector and the worker as goroutines; Rust runs them on threads that share the server,
cache and queue through `Arc`. Both log to standard error with the milliseconds since
start.

<p class="listing"><b>Listing 1.27</b> The demonstration, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/main.go">code/go/informer/main.go</a></p>

```go
{{#include ../code/go/informer/main.go:main}}
```

<p class="listing"><b>Listing 1.28</b> The demonstration, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/main.rs">code/rust/informer/src/main.rs</a></p>

```rust
{{#include ../code/rust/informer/src/main.rs:main}}
```

The Go version prints:

```console
$ go run ./informer
{{#include ../code/output/go-informer.txt}}
```

The Rust version prints the same sequence. Its timings differ by a millisecond or 2, and
its field names follow Rust's conventions:

```console
$ cargo run -p informer
{{#include ../code/output/rust-informer.txt}}
```

The table reads the Go log against the mechanisms of this chapter.

| Time | Log | Mechanism |
|---|---|---|
| 0 ms | list at version 2 | Algorithm 1.2, step 1.1. Replace reports both jobs, and both are queued. |
| 20 to 40 ms | 1 reconcile per job | Each status write is itself an event and queues the name again; the next reconcile finds status equal to spec and returns without logging. |
| 101 ms | 5 edits | The worker takes `job-a` after the first edit and reads a spec of 2 at version 5. The other 4 edits arrive while it holds the name, so the queue only marks it dirty (Figure 1.7). |
| 121 ms | `409 Conflict` at version 5 | The object is at version 9. The conditional write fails, and the name returns to the queue. |
| 141 ms | status 6 | The second reconcile reads version 9 and writes status 6 at version 10. Specs 3, 4 and 5 were never acted on (Figure 1.8). |
| 257 ms | watch closed, resuming from 10 | The stream closed. The cache is exact up to 10, so the reflector watches from 10 with no list. |
| 307 to 338 ms | `410 Gone`, list at version 11 | During the partition `job-b` was deleted at 11 and history compacted to 11. A watch from 10 cannot be served. |
| 338 ms | `job-b`: deleted | Replace finds `job-b` in the old cache and absent from the list (Figure 1.5). Its `DELETED` event no longer exists anywhere. |

Animation 1.2 replays the run from the list at version 2 to the list at version 11, with
the server's objects on the left and the cache on the right.

<figure class="anim">
<video class="motion" src="figures/list-watch.mp4" autoplay loop muted playsinline preload="metadata" aria-label="The API server on the left with job-a, job-b and its recent events; the reflector's cache on the right. The reflector lists at version 2 and opens a watch. Events 3 to 10 arrive and the cache follows. The watch is closed and reopened from 10 with no list. During a partition job-b is deleted at version 11 and the history is compacted, while the cache still holds job-b. After the partition the server answers a watch from 10 with 410 Gone, the reflector lists at version 11, and job-b, present in the old cache and missing from the list, is removed." data-chapters="[[0.0, &quot;list&quot;], [10.01, &quot;watch&quot;], [34.28, &quot;drop&quot;], [43.69, &quot;partition&quot;], [60.08, &quot;410 Gone&quot;]]"><img src="figures/list-watch.gif" alt="The API server on the left with job-a, job-b and its recent events; the reflector's cache on the right. The reflector lists at version 2 and opens a watch. Events 3 to 10 arrive and the cache follows. The watch is closed and reopened from 10 with no list. During a partition job-b is deleted at version 11 and the history is compacted, while the cache still holds job-b. After the partition the server answers a watch from 10 with 410 Gone, the reflector lists at version 11, and job-b, present in the old cache and missing from the list, is removed."></video>
<figcaption><b>Animation 1.2</b> The run of the model: a list, a watch, a dropped watch that resumes, and a partition that ends in <code>410 Gone</code> and a second list.</figcaption>
</figure>

## 1.11 The same design in client-go

Real Go controllers use client-go, directly or through controller-runtime, which is built
on it. Every part of the model has a counterpart.

| Model | client-go |
|---|---|
| `APIServer.List`, `Watch` | `ListerWatcher`, backed by HTTP list and watch requests |
| `Reflector` | `cache.Reflector` |
| `Cache` | `cache.Indexer`, a thread-safe store with secondary indexes, such as all pods on 1 node |
| reflector and cache together | `cache.SharedIndexInformer` |
| `WorkQueue` | `workqueue`, with the same *dirty* and *processing* sets |
| `reconcile` | a controller's `Reconcile` method |

client-go adds 6 mechanisms that the model leaves out. Each solves a problem from the
earlier sections.

**DeltaFIFO.** Between the reflector and the indexer, client-go keeps a queue of pending
changes per object, so that the code that updates the indexer and notifies handlers takes
1 object at a time with all its changes. When a relist shows that an object has
disappeared, DeltaFIFO emits a deletion whose object is wrapped in
`DeletedFinalStateUnknown`. The wrapper tells handlers that the object they receive is the
last state the cache saw, which may be older than its state at deletion.

**Bookmarks.** The reflector requests bookmark events (section 1.4), so a watch on a quiet
kind keeps a recent resume point and survives compaction without a relist.

**Shared informers.** Controllers in 1 process that watch the same kind share 1 informer
through a `SharedInformerFactory`. Each registers its own handler and keeps its own work
queue, and the API server serves 1 watch per process (Figure 1.10). Since every
controller reads the same objects, client-go hands out pointers into the shared store. A
controller that modifies an object it read changes what every other controller in the
process sees, so the rule is to call the generated `DeepCopy` method and modify the copy.

<figure>
<img src="figures/ch01-shared-informer.svg" alt="One API server watch on pods feeds a shared informer holding the reflector, the DeltaFIFO and the indexer. Three controllers in the same process each register a handler and keep their own work queue.">
<figcaption><b>Figure 1.10</b> One watch and one cache per kind per process, shared by every controller in it.</figcaption>
</figure>

**Resync.** An informer can be given a resync period, after which it queues every name in
its cache again, from memory and without a request. This serves controllers that manage
something outside Kubernetes, such as a cloud load balancer, whose drift no Kubernetes
event reports.

**Rate-limited retries.** `DefaultControllerRateLimiter` combines 2 limits and applies the
larger delay: a per-name exponential backoff that starts at 5 ms and doubles after each
failure up to 1,000 s, and a token bucket of 10 retries per second with a burst of 100
across all names. The model retries at once. A real controller that did so while its
writes kept failing would send the API server a request per reconcile without pause.

**Memory.** A cache holds every object of its kind. For 50,000 pods at 4 KB each, that is
200 MB per process before indexes. Controllers that need only names and labels use a
metadata-only informer, which stores `PartialObjectMetadata` instead of the full object,
and an informer can be given a transform function that removes unneeded fields before an
object enters the cache.

### Reading your own writes

A controller's own writes reach its cache the way everyone else's do: the server stores
the write, emits an event, and the reflector applies it. Until the event arrives, the
cache shows the state from before the write. If a reconcile creates a pod for a job and a
second event for the job arrives before the pod's creation event, the next reconcile
finds no pod in the cache and creates a second one.

Kubernetes controllers use 2 techniques against this. The ReplicaSet controller records
*expectations*: after creating 3 pods it expects 3 creation events and leaves that
ReplicaSet alone until the cache has shown them or a timeout has passed. The second
technique uses 2 fields every object carries. The API server increments
`metadata.generation` on every change to the spec, and a controller copies the generation
it acted on into `status.observedGeneration`. When the 2 are equal, the status describes
the current spec; when they differ, the controller and every user reading the object can
see that the latest spec has not been handled yet.

## 1.12 The complete program

The model is 6 source files in each language, printed in the order the chapter built
them.

<p class="listing"><b>Listing 1.29</b> The API server, complete, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">code/go/informer/server.go</a></p>

```go
{{#include ../code/go/informer/server.go}}
```

<p class="listing"><b>Listing 1.30</b> The API server, complete, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">code/rust/informer/src/server.rs</a></p>

```rust
{{#include ../code/rust/informer/src/server.rs}}
```

<p class="listing"><b>Listing 1.31</b> The cache, complete, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/cache.go">code/go/informer/cache.go</a></p>

```go
{{#include ../code/go/informer/cache.go}}
```

<p class="listing"><b>Listing 1.32</b> The cache, complete, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/cache.rs">code/rust/informer/src/cache.rs</a></p>

```rust
{{#include ../code/rust/informer/src/cache.rs}}
```

<p class="listing"><b>Listing 1.33</b> The reflector, complete, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/reflector.go">code/go/informer/reflector.go</a></p>

```go
{{#include ../code/go/informer/reflector.go}}
```

<p class="listing"><b>Listing 1.34</b> The reflector, complete, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/reflector.rs">code/rust/informer/src/reflector.rs</a></p>

```rust
{{#include ../code/rust/informer/src/reflector.rs}}
```

<p class="listing"><b>Listing 1.35</b> The work queue, complete, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/queue.go">code/go/informer/queue.go</a></p>

```go
{{#include ../code/go/informer/queue.go}}
```

<p class="listing"><b>Listing 1.36</b> The work queue, complete, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/queue.rs">code/rust/informer/src/queue.rs</a></p>

```rust
{{#include ../code/rust/informer/src/queue.rs}}
```

<p class="listing"><b>Listing 1.37</b> The controller, complete, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/controller.go">code/go/informer/controller.go</a></p>

```go
{{#include ../code/go/informer/controller.go}}
```

<p class="listing"><b>Listing 1.38</b> The controller, complete, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/controller.rs">code/rust/informer/src/controller.rs</a></p>

```rust
{{#include ../code/rust/informer/src/controller.rs}}
```

<p class="listing"><b>Listing 1.39</b> The demonstration, complete, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/main.go">code/go/informer/main.go</a></p>

```go
{{#include ../code/go/informer/main.go}}
```

<p class="listing"><b>Listing 1.40</b> The demonstration, complete, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/main.rs">code/rust/informer/src/main.rs</a></p>

```rust
{{#include ../code/rust/informer/src/main.rs}}
```

<div class="exercises">

**Exercises**

1. In Figure 1.1, a client lists at revision 8 and watches from 8. Which events does it receive, and what is its cached resource version for `job-b` after applying them?
2. Change the reflector so that it queues the name before applying the event. Find an interleaving of 1 event and 1 worker that leaves a change unhandled, and confirm it by adding a sleep between the 2 steps.
3. Remove the *processing* set from the work queue and run the demonstration with 2 workers. How many reconciles of `job-a` overlap during the burst?
4. A relist finds an object at the same name with a different resource version and a different UID. What happened on the server, and what should a controller that owns external resources do?
5. With the default rate limiter, after how many consecutive failures does 1 name wait longer than 1 minute between attempts?

</div>

## References

1. Kubernetes documentation, "API Concepts": efficient detection of changes, resource versions, watch bookmarks. <https://kubernetes.io/docs/reference/using-api/api-concepts/>
2. Kubernetes API conventions, "Concurrency Control and Consistency". <https://github.com/kubernetes/community/blob/master/contributors/devel/sig-architecture/api-conventions.md>
3. etcd documentation, "Data model": revisions, the key index, and compaction. <https://etcd.io/docs/latest/learning/data_model/>
4. KEP-2340, "Consistent Reads from Cache", beta in Kubernetes 1.31. <https://github.com/kubernetes/enhancements/issues/2340>
5. client-go source: `tools/cache/reflector.go`, `tools/cache/delta_fifo.go`, `util/workqueue/queue.go`, `util/workqueue/default_rate_limiters.go`. <https://github.com/kubernetes/client-go>
6. M. Hausenblas and S. Schimanski, *Programming Kubernetes*, O'Reilly, 2019, chapter 3.
7. B. Burns, B. Grant, D. Oppenheimer, E. Brewer and J. Wilkes, "Borg, Omega, and Kubernetes", *ACM Queue* 14(1), 2016.
