# 1. Keeping a local copy of the cluster

A training job on a GPU cluster states what hardware it needs: how many GPUs, which GPU
model, and how much device memory each GPU must have. A job that fine-tunes a model with
70 billion parameters might ask for 4 Jetson AGX Thor GPUs with at least 100 GiB each,
because a Jetson Orin NX, with 16 GB shared between its CPU and GPU, cannot hold the model
at all.

Kubernetes splits that request across 2 mechanisms. The scheduler counts GPUs as an
*extended resource* named `nvidia.com/gpu`: each machine advertises a whole number of units,
1 unit is 1 physical GPU by default, and a pod asks for units in its resource limits. The
count carries no information about the model or the memory, so an Orin NX and a Thor both
advertise `nvidia.com/gpu: 1`. The model and the memory are expressed through node labels
such as `nvidia.com/gpu.product`, which a pod selects with a `nodeSelector`. Chapter 2
measures what 1 unit contains, chapter 5 adds the labels, and chapter 8 places jobs across
machines.

A program that runs such jobs reacts to 3 kinds of change. When a user creates a job, it
starts the job's containers on machines that satisfy the request. When the user raises the
request from 1 GPU to 2, it replaces the containers. When the user deletes the job, it stops
them and the GPUs return to the pool. Kubernetes calls a program like this a *controller*.

Most of the design work in a controller goes into learning about changes. A controller
follows thousands of objects, and it has to see every creation, update, and deletion soon
after it happens, without missing one and without acting on one twice. A missed deletion leaves GPUs allocated to a job that no longer exists.
An update handled twice can give 1 job 2 sets of containers.

This chapter builds the machinery that keeps a controller informed, as a small program with
5 parts: an API server, a cache, a loop that keeps the cache up to date, a work queue, and
the controller itself. Each part is introduced together with the failure it prevents. At
the end, the program is run through a burst of edits, a dropped connection, and a network
partition, and each part is matched with its counterpart in client-go, the library that
production Go controllers are built on.

The program exists in Go and in Rust, with the same parts and the same behaviour, and uses
only each language's standard library. The Go files are in `code/go/informer` and run with
`go run ./informer` from `code/go`. The Rust files are in `code/rust/informer` and run with
`cargo run -p informer` from `code/rust`.

<div class="covers">

This chapter covers

- objects, and the API server that stores them
- resource versions, and the `409 Conflict` that protects a write
- listing and watching, and the `410 Gone` that forces a second list
- a cache, a reflector, a work queue, and a controller, each in Go and in Rust
- 1 run through a burst of edits, a dropped watch, and a partition
- the parts of client-go that match the model

</div>

## Objects, specs, and statuses

Kubernetes keeps everything it manages as *objects*. An object is a named record with 2
main parts. A training job in this chapter's model looks like this:

```text
name:    train
spec:    gpu: 2 x Thor (100 GiB)      what the user asked for
status:  gpu: 1 x Thor (100 GiB)      what the controller has provided
```

The *spec* is written by the user and describes the desired state. The *status* is written
by the controller and records the request it has satisfied. A controller compares the 2,
does the work that brings the cluster in line with the spec, and then copies the satisfied
request into the status. For `train`, the spec asks for 2 Thor GPUs and the status shows 1,
so the controller replaces the job's container with one that holds 2 GPUs and then writes
`2 x Thor (100 GiB)` into the status. A status equal to the spec means there is nothing
left to do.

All objects are stored behind 1 HTTP service, the *API server*, which keeps them in etcd, a
replicated key-value database. Every read and every write goes through the API server.
Users, `kubectl`, and controllers are all ordinary clients of it, and none of them talks to
etcd directly.

## Numbering every write

A controller could stay informed by asking the API server for every object every few
seconds and comparing the answer with the previous one. In a small cluster that works. In a
cluster with 50,000 pods, each stored as a few kilobytes of JSON, 1 complete listing is
about 200 MB. If 12 controllers each fetched that every 5 seconds, the API server would send
about 480 MB per second, and between 2 fetches only a handful of pods would have changed.

A better design is for the API server to send each change to the clients that are
interested, as it happens. That design has to cope with broken connections. A server
restarts, a load balancer closes a connection it thinks is idle, or the network fails for a
few seconds. When a client reconnects, it needs to ask for the changes it missed, and to
ask for them it needs a way to identify the last change it received.

The API server provides that identifier by numbering its writes. It keeps 1 counter for
the whole store, and every create, update, or delete of any object increments the counter.
The new value is stamped on the object that changed and is called the object's *resource
version*. The numbers come from etcd, which assigns every write a *revision* from a single
counter for the whole database. A client that has seen every change up to version 10 can
ask for the changes after version 10, and the server can tell exactly which ones those are.

Resource versions also prevent a second problem, the *lost update*. In the sequence below,
2 clients read the job `train` at version 7 and each changes a different field:

```text
version 7   client A reads train           client B reads train
version 8   A writes gpus: 2, read at 7    accepted
            B writes image: v2, read at 7  refused: train is at version 8
            B reads train again at version 8 and reapplies image: v2
version 9   B writes image: v2, read at 8  accepted, and gpus: 2 is kept
```

A write replaces the whole object. If the server accepted B's first write, it would store
B's copy of the job, which still has the old GPU count, and A's change would disappear
without any error. Because B states the version it read, the server can see that the job
has changed since then and refuse the write with the HTTP status `409 Conflict`. B reads the
job again and applies its change to the current version. Neither client takes a lock; each
one shows, at the moment it writes, which version its change is based on.

## Listing, then watching

Numbered writes let a client build an exact copy of the cluster's objects with 2 requests.

The first request is a *list*. It returns every object of a kind, together with the
resource version at which the server took that snapshot. The second is a *watch*: a request
that stays open, through which the server sends 1 *event* for every change made after a
given version. The client passes the version that came back with its list.

Passing that version closes a gap. The list and the watch are separate requests, and other
clients keep writing between them. In this timeline the list is taken at version 10, a user
edits a job at version 11, and the watch opens when the store is already at version 12:

```text
version:   10          11             12
           list        job-a edited   watch opened
           snapshot                   from version 10
                                      -> the server replays event 11,
                                         then sends new events as they occur
```

The watch asks for every change after version 10, so the server first sends event 11 from
its record of recent changes and then continues with new events as they happen. The client
ends up with the snapshot at version 10 plus every change since, with nothing missing and
nothing applied twice. A watch opened at the current version, 12, would never deliver the
edit made at version 11, and the client's copy of `job-a` would stay out of date until
`job-a` changed again.

## When the history runs out

The server can replay only the changes it still remembers. etcd keeps every revision of
every key until it is told to discard the old ones, an operation called *compaction*,
because without it the database would grow without limit. The Kubernetes API server
compacts every 5 minutes by default. After a compaction, a watch that asks to resume from
an older version cannot be served, since the events it needs no longer exist. The API
server answers it with the HTTP status `410 Gone`, and the client has to list again and
watch from the new list's version.

Watches also end for ordinary reasons. The API server closes each watch after a timeout
chosen at random between 30 and 60 minutes, so that thousands of clients do not reconnect at
the same moment. A load balancer may close a connection that has carried no data for a
while. The network may fail, and for a time even new connections fail.

A client has to handle each of these endings differently:

| How the watch ended | What the client does |
|---|---|
| the connection closed | opens a new watch from the last version it received |
| the server cannot be reached | waits, then tries again from the same version |
| the server answered `410 Gone` | lists again and watches from the new list's version |

## Building the server

The model's API server keeps its objects in memory, numbers every write, remembers recent
events, and answers lists and watches. It also has 3 methods that a real server does not
have, `DropWatches`, `Partition`, and `Heal`, which let the demonstration at the end of the
chapter produce each of the failures described above whenever it needs them.

<div class="lld">

Low-level design: the model

| Part | Holds | Rule it keeps |
|---|---|---|
| `Object` | a name, a spec, a status, a version | the version is the number of the write that last changed it |
| `APIServer` | the objects, the write counter, recent events, the open watches | every write increments the counter and publishes 1 event |
| `Cache` | a copy of every object | exact up to the last event applied |
| `Reflector` | the server, the cache, the queue | updates the cache before it queues a name |
| `WorkQueue` | the ready names, and the sets `dirty` and `processing` | a name is with at most 1 worker at a time |
| `Controller` | the server, the cache, the queue | acts only on the object's current state |

Each part is 1 source file in each language, and the sections below build them in this
order.

</div>

An object in the model carries a name, a spec, a status, and a resource version. The spec
and the status both hold a `GPURequest`: a count of whole GPUs, the GPU model, and the
device memory each GPU must have. The count is what a real pod would put in its
`nvidia.com/gpu` limit, and the model and memory are what it would match against node
labels. Holding the same type on both sides lets the controller decide whether it has work
to do with 1 equality test, and a change to any of the 3 fields, the model as much as the
count, makes the status differ from the spec. An event pairs an object with the kind of
change: added, modified, or deleted. The server can return 2 errors that a client must be
able to tell apart, because they call for different responses: a conflict on a write, and
`410 Gone` on a watch.

<p class="listing"><b>Listing 1.1</b> Objects, events, and the two errors, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">code/go/informer/server.go</a></p>

```go
{{#include ../code/go/informer/server.go:objects}}
```


<p class="listing"><b>Listing 1.2</b> Objects, events, and the two errors, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">code/rust/informer/src/server.rs</a></p>

```rust
{{#include ../code/rust/informer/src/server.rs:objects}}
```


The server's state is 4 things behind 1 lock: the objects, the counter, the events it still
remembers, and the watches that are open.

<p class="listing"><b>Listing 1.3</b> The server's state, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">code/go/informer/server.go</a></p>

```go
{{#include ../code/go/informer/server.go:server}}
```


<p class="listing"><b>Listing 1.4</b> The server's state, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">code/rust/informer/src/server.rs</a></p>

```rust
{{#include ../code/rust/informer/src/server.rs:server}}
```


Writes and reads follow the rules from the first half of the chapter. An update carries the
version the client read; if it differs from the stored version, the server refuses it with a
conflict. A version of 0 skips the check, which is how the demonstration plays a user
editing a job by hand. Every successful write increments the counter and publishes 1 event,
and a deletion publishes the object's final state under a new version.

<p class="listing"><b>Listing 1.5</b> Writing: update, delete, and publish, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">code/go/informer/server.go</a></p>

```go
{{#include ../code/go/informer/server.go:writes}}
```


<p class="listing"><b>Listing 1.6</b> Writing: update, delete, and publish, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">code/rust/informer/src/server.rs</a></p>

```rust
{{#include ../code/rust/informer/src/server.rs:writes}}
```


A watch opened from version 10 must receive event 11 exactly once, even if another client is
writing at that very moment. The server guarantees this with its lock. Publishing an event
happens while the lock is held, and opening a watch holds the same lock while it replays the
remembered events and registers the new watcher. Any event is therefore either part of the
replay or delivered after registration, and never both.

<p class="listing"><b>Listing 1.7</b> Reading: list and watch, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">code/go/informer/server.go</a></p>

```go
{{#include ../code/go/informer/server.go:listwatch}}
```


<p class="listing"><b>Listing 1.8</b> Reading: list and watch, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">code/rust/informer/src/server.rs</a></p>

```rust
{{#include ../code/rust/informer/src/server.rs:listwatch}}
```


The 2 languages differ in what happens when a watcher stops reading. A Go watch has a buffer
of 1,024 events, and once it is full, publishing would block while holding the lock and
stall every writer; the real API server closes a watch that falls this far behind. The Rust
channel has no limit. To end a watch, the Go server closes the channel and the Rust server
drops the sending half, which ends the receiver's loop.

The last 4 methods produce the failures on demand: compaction, closing every watch, and
cutting the server off from its clients and reconnecting it. After a compaction, a watch
that asks for a version older than `compacted` receives the gone error.

<p class="listing"><b>Listing 1.9</b> Compaction, dropped watches, and partitions, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">code/go/informer/server.go</a></p>

```go
{{#include ../code/go/informer/server.go:faults}}
```


<p class="listing"><b>Listing 1.10</b> Compaction, dropped watches, and partitions, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">code/rust/informer/src/server.rs</a></p>

```rust
{{#include ../code/rust/informer/src/server.rs:faults}}
```


## A local copy of the objects

A client that has listed and is watching can keep its own copy of every object in memory, and
that copy is exact up to the last event it received. Reading an object becomes a map lookup
in place of a network request, and the server sends each change to the client once. This
copy is called the *cache*.

The cache is a map behind a read-write lock. Every reconcile reads from it and only incoming
events write to it, so many readers can proceed at the same time. Applying an event stores
the object for an addition or a modification and removes it for a deletion.

<p class="listing"><b>Listing 1.11</b> The cache, a lookup, and applying one event, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/cache.go">code/go/informer/cache.go</a></p>

```go
{{#include ../code/go/informer/cache.go:cache}}
```


<p class="listing"><b>Listing 1.12</b> The cache, a lookup, and applying one event, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/cache.rs">code/rust/informer/src/cache.rs</a></p>

```rust
{{#include ../code/rust/informer/src/cache.rs:cache}}
```


The cache also needs a way to install a complete list, and this is where a relist finds
deletions that no event will ever report. Suppose `job-b` is deleted while the client is
disconnected, and a compaction then discards the deletion event. When the client lists
again, `job-b` is absent from the result. The only evidence of the deletion is that
`job-b` is present in the old cache and missing from the new list. `Replace` therefore
builds the new contents from the list, reports each object whose version differs from the
cached one, and then reports each cached name that the list no longer contains. An object
the client has never seen has no cached version, which Go reads as 0 and Rust as `None`, so
new objects are reported as changed too.

<p class="listing"><b>Listing 1.13</b> Replacing the cache with a fresh list, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/cache.go">code/go/informer/cache.go</a></p>

```go
{{#include ../code/go/informer/cache.go:replace}}
```


<p class="listing"><b>Listing 1.14</b> Replacing the cache with a fresh list, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/cache.rs">code/rust/informer/src/cache.rs</a></p>

```rust
{{#include ../code/rust/informer/src/cache.rs:replace}}
```


## The reflector

A loop keeps the cache in step with the server. It lists, installs the result with
`Replace`, and puts the names that `Replace` reported on the work queue so the controller
will look at them. It then watches from the list's version and applies each event as it
arrives. When the history it needs has been compacted away, it lists again. Kubernetes calls
this loop the *reflector*, because it reflects the server's state into local memory.

The reflector's inner loop holds 1 variable, `version`, the version of the last event it
applied to the cache. Since the cache is complete up to `version`, a watch reopened from
`version` continues exactly where the previous watch stopped. The 3 ways a watch can end
from the table above map onto 3 branches:

- When the server drops the connection, the reflector opens a new watch from `version`, and
  the server replays whatever happened during the reconnection.
- When the server cannot be reached, the reflector waits 10 milliseconds and tries again
  with the same `version`. client-go waits a little longer after each consecutive failure,
  so that thousands of clients do not overload a server that is trying to recover.
- When the server answers with the gone error, `version` is older than the compaction point.
  The inner loop returns, and the outer loop starts over with a new list.

<p class="listing"><b>Listing 1.15</b> The reflector and its list step, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/reflector.go">code/go/informer/reflector.go</a></p>

```go
{{#include ../code/go/informer/reflector.go:run}}
```


<p class="listing"><b>Listing 1.16</b> The reflector and its list step, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/reflector.rs">code/rust/informer/src/reflector.rs</a></p>

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


Inside the event loop, the reflector updates the cache before it queues the object's name,
and the order is deliberate. If the name were queued first, a worker could take it at once,
read the cache before the update arrived, find the old state, decide there was nothing to
do, and finish. The name would not be queued again, and the change would wait until the
object happened to change once more.

In client-go, a reflector together with its cache and the code that notifies the rest of the
program about changes is called an *informer*.

## A queue of names

The reflector could call the controller once for every event. That approach fails in 2
situations.

The first is a burst of edits. A user who changes a job 5 times in 1 second produces 5
events, and a controller called 5 times would start work on 4 specs that were already out of
date. The second is a relist. After `410 Gone`, `Replace` reports which names changed, but
the individual events that led there no longer exist, so a controller that depends on seeing
every event has nothing to react to.

The reflector therefore hands the controller only the *names* of objects that changed, and
the controller reads each object's current state from the cache when it gets to the name. If
the queue ignores a name it already holds, 5 edits turn into 1 reconcile, and that reconcile
works on the latest spec. The controller takes names from the queue in 1 or more *workers*,
each handling 1 name at a time. The model runs a single worker.

A queue that only removes duplicates is not quite enough, because an object can change while
a worker is reconciling it. The new event would put the name back on the queue, a second
worker would take it, and 2 workers would act on 1 object at once. If both write a status
with a version check, 1 of them fails with a conflict and its work is wasted. If both act
outside Kubernetes, for example by starting a container, both succeed, and the job has 2
containers.

The queue prevents this with 2 sets beside its list of ready names. `dirty` holds every name
that needs processing, and `processing` holds every name a worker has taken and not yet
returned. When `Add` receives a name that a worker is holding, it marks the name dirty and
keeps it off the ready list. When the worker calls `Done`, the queue sees the mark and makes
the name ready again, so the next reconcile reads the object as it is after the change. This
table follows 1 name through that sequence:

```text
call             ready      dirty      processing   effect
---------------  ---------  ---------  -----------  --------------------------------
Add(job-a)       [job-a]    {job-a}    {}           ready for a worker
Get() -> job-a   []         {}         {job-a}      a worker takes it
Add(job-a)       []         {job-a}    {job-a}      edited during the run: marked
Add(job-a)       []         {job-a}    {job-a}      already marked: no change
Done(job-a)      [job-a]    {job-a}    {}           marked, so ready again
```

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


Animation 1.1 plays the same sequence with the burst of 5 edits from the run at the end of the
chapter. Its last part repeats the calls on a queue without a `processing` set, which hands
the name to a second worker while the first is still busy.

<figure class="anim">
<video class="motion" src="figures/work-queue.mp4" autoplay loop muted playsinline preload="metadata" aria-label="Three boxes, ready, dirty and processing, above a worker. Add puts job-a in ready and dirty. Get moves it to processing and the worker starts a reconcile. Four more Add calls during the reconcile mark the name dirty and leave ready empty. Done moves the name back to ready, and a second reconcile reads a spec of 6 GPUs. In the last part the processing set is removed: an Add during the reconcile makes the name ready, and a second worker takes it while the first is still working." data-chapters="[[0.0, &quot;Add&quot;], [7.86, &quot;Get&quot;], [18.06, &quot;Add while held&quot;], [33.66, &quot;Done&quot;], [46.86, &quot;no processing set&quot;]]"><img src="figures/work-queue.gif" alt="Three boxes, ready, dirty and processing, above a worker. Add puts job-a in ready and dirty. Get moves it to processing and the worker starts a reconcile. Four more Add calls during the reconcile mark the name dirty and leave ready empty. Done moves the name back to ready, and a second reconcile reads a spec of 6 GPUs. In the last part the processing set is removed: an Add during the reconcile makes the name ready, and a second worker takes it while the first is still working."></video>
<figcaption><b>Animation 1.1</b> One name through the work queue. Five edits lead to two reconciles, and the two never overlap.</figcaption>
</figure>

A worker that calls `Get` on an empty queue has to sleep until a name arrives, and it must
release the lock while it sleeps, or `Add` could never acquire it. Both versions use a
*condition variable* for this, `sync.Cond` in Go and `std::sync::Condvar` in Rust. Waiting
on a condition variable releases the lock and puts the worker to sleep in 1 step, and `Add`
and `Done` signal it when they make a name ready. The wait sits inside a loop that checks the
list again after waking, because with several workers another one may have taken the name
first.

## Reconciling

The controller takes a name from the queue, reads the object from the cache, and brings the
world in line with it. Kubernetes calls this *reconciling*.

If the name is missing from the cache, the object was deleted, and a real controller would
release whatever it had set up for it; the model logs a message. If the status already
matches the spec, there is nothing to do. Otherwise the controller does its work, which the
model stands in for with a 20-millisecond sleep, sets the status, and writes the object back.
A worker loop around this takes names from the queue, and when a reconcile fails, it queues
the name again so that the next attempt starts from whatever the cache holds by then.

<p class="listing"><b>Listing 1.23</b> Reconciling one name, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/controller.go">code/go/informer/controller.go</a></p>

```go
{{#include ../code/go/informer/controller.go:reconcile}}
```


<p class="listing"><b>Listing 1.24</b> Reconciling one name, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/controller.rs">code/rust/informer/src/controller.rs</a></p>

```rust
{{#include ../code/rust/informer/src/controller.rs:reconcile}}
```


<p class="listing"><b>Listing 1.25</b> The controller and its worker loop, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/controller.go">code/go/informer/controller.go</a></p>

```go
{{#include ../code/go/informer/controller.go:run}}
```


<p class="listing"><b>Listing 1.26</b> The controller and its worker loop, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/controller.rs">code/rust/informer/src/controller.rs</a></p>

```rust
{{#include ../code/rust/informer/src/controller.rs:run}}
```


The reconcile function looks only at the object's current state and has no idea why it was
called. A name queued once and a name queued 10 times lead to the same action, and so do a
change reported by an event and a change found by a relist. This style is called
*level-triggered*, a term from digital electronics, where a level-triggered circuit responds
to the present level of a signal and an *edge-triggered* circuit responds to each transition.
A controller that reacted to individual events would be edge-triggered in the same sense. It
would waste work during bursts and miss the changes whose events a compaction discarded.

## Writing back to the server

The cache is always slightly behind the server, by the time an event takes to arrive. During
the 20 milliseconds a reconcile spends working, a user may change the spec. If the controller
then wrote its copy of the object back unconditionally, it would store the old spec together
with a status computed for that old spec, and the user's edit would be lost.

This is the lost update from earlier in the chapter, and the same check prevents it. The
controller writes the object with the version it read. If the object changed in the meantime,
the server refuses the write with a conflict, the worker loop queues the name again, and the
next reconcile reads the newer object from the cache. The technique is called *optimistic
concurrency*: the controller takes no lock on the object and relies on the server to notice,
at write time, that someone else changed it.

## Running the model

Figure 1.1 shows the 5 parts together and numbers the 2 steps the reflector takes for each
event.

<figure>
<img src="figures/informer-pipeline.svg" alt="The API server numbers every write and stores objects in etcd. Inside the controller's process, the reflector receives events, applies each one to the cache, and then adds the object's name to the work queue. The controller gets a name from the queue, reads the object from the cache, and writes the status back to the API server with the version it read.">
<figcaption><b>Figure 1.1</b> The path of one change: an event from the API server, the cache, the work queue, a reconcile, and a conditional write back to the server.</figcaption>
</figure>

The demonstration creates 2 jobs, starts the reflector and the controller, and then puts
them through each situation from this chapter: a burst of edits that arrives during a
reconcile, a dropped watch, and a partition during which a job is deleted and the history is
compacted. The Go version runs the reflector and the controller as goroutines, and the Rust
version runs them on threads that share the server, cache, and queue through `Arc` handles.
Both log to standard error with the number of milliseconds since the program started.

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

The Rust version prints the same lines, with timings that differ by a millisecond or 2:

```console
$ cargo run -p informer
{{#include ../code/output/rust-informer.txt}}
```

The first 3 lines are the initial list and 1 reconcile for each job. Each status write is
itself a change, so the reflector receives an event for it and queues the name again; the
reconcile that follows finds the status equal to the spec and returns without logging.

The burst of 5 edits led to 2 reconciles of `job-a`. The controller took the name right
after the first edit, read a spec of `2 x Thor (100 GiB)` at version 5, and began its 20 milliseconds of
work. The other 4 edits arrived while it was busy and moved the object to version 9, and
because the controller was holding the name, the queue only marked it dirty. The status write
based on version 5 failed with a conflict. `Done` made the name ready again, the next
reconcile read a spec of `6 x Thor (100 GiB)` at version 9, and it wrote the same request into
the status at version 10. The specs for 3, 4, and 5 GPUs were replaced before the controller ever read them, so it did no
work for them at all.

When the watch was dropped, the reflector reopened it from version 10, the version of the
last event it had applied, without listing. During the partition, `job-b` was deleted at
version 11 and the history was compacted up to 11. When the partition ended, the reflector
asked to resume from version 10, the server answered `410 Gone`, and the reflector listed
again. The new list held only `job-a`, `Replace` reported `job-b` as missing, and the
controller found no `job-b` in the cache and released its GPUs. The client learned about the
deletion only by comparing the list with its cache, since the deletion event had been
compacted away.

Animation 1.2 replays the log from the list at version 2 to the list at version 11, with the
server's objects on the left and the cache on the right.

<figure class="anim">
<video class="motion" src="figures/list-watch.mp4" autoplay loop muted playsinline preload="metadata" aria-label="The API server on the left with job-a, job-b and its recent events; the reflector's cache on the right. The reflector lists at version 2 and opens a watch. Events 3 to 10 arrive and the cache follows. The watch is closed and reopened from 10 with no list. During a partition job-b is deleted at version 11 and the history is compacted, while the cache still holds job-b. After the partition the server answers a watch from 10 with 410 Gone, the reflector lists at version 11, and job-b, present in the old cache and missing from the list, is removed." data-chapters="[[0.0, &quot;list&quot;], [10.01, &quot;watch&quot;], [34.28, &quot;drop&quot;], [43.69, &quot;partition&quot;], [60.08, &quot;410 Gone&quot;]]"><img src="figures/list-watch.gif" alt="The API server on the left with job-a, job-b and its recent events; the reflector's cache on the right. The reflector lists at version 2 and opens a watch. Events 3 to 10 arrive and the cache follows. The watch is closed and reopened from 10 with no list. During a partition job-b is deleted at version 11 and the history is compacted, while the cache still holds job-b. After the partition the server answers a watch from 10 with 410 Gone, the reflector lists at version 11, and job-b, present in the old cache and missing from the list, is removed."></video>
<figcaption><b>Animation 1.2</b> The run of the model: a list, a watch, a dropped watch that resumes, and a partition that ends in <code>410 Gone</code> and a second list.</figcaption>
</figure>

## The same design in client-go

Production Go controllers use client-go, either directly or through controller-runtime, a
higher-level library built on it. Every part of the model has a counterpart there:

```text
model                     client-go
------------------------  ---------------------------------------------------------
APIServer.List, Watch     ListerWatcher, backed by HTTP list and watch requests
Reflector                 Reflector
Cache                     Indexer: a thread-safe store with secondary indexes,
                          for example all pods on one node
Reflector and Cache       SharedIndexInformer
WorkQueue                 workqueue, with the same dirty and processing sets
Controller.reconcile      the Reconcile method of a controller
```

client-go also has several mechanisms that the model leaves out. Each one deals with a
problem from this chapter.

Between the reflector and the cache, client-go places a queue called the *DeltaFIFO*. It
collects each object's changes in the order they arrived, and the code that updates the
cache and notifies controllers takes 1 object at a time with all of its pending changes. When
a relist shows that an object has disappeared, the DeltaFIFO emits a deletion whose object is
wrapped in a `DeletedFinalStateUnknown` marker. The marker tells event handlers that the
object they receive is the last state the cache saw, which may be older than the state the
object had when it was deleted.

The API server can send *bookmark* events, which carry a resource version and no object.
A watch on a kind of object that rarely changes can go a long time without events, and the
version it would resume from grows old. After the next compaction, reconnecting from that
version fails with `410 Gone` and forces a full relist. Bookmarks move the watch's position
forward while nothing changes, so a reconnect usually succeeds.

An informer can be given a *resync period*. At each period it queues the name of every object
in its cache again, straight from memory, without asking the server for anything. Resync
exists for controllers that manage something outside Kubernetes, such as a cloud load
balancer. If someone changes that load balancer by hand, no Kubernetes event reports it, and
a periodic resync gives the controller a regular chance to notice the difference and correct
it.

The work queue waits before retrying a name whose reconcile failed. The wait starts at 5
milliseconds and doubles after each failure, up to 1,000 seconds, and the queue also limits
how fast it hands out names overall. The model retries at once. A real controller that did
the same while its writes kept failing, for example because of a bug in how it builds the
object, would flood the API server with requests.

Informers are shared within a process. If 10 controllers in 1 program all watch pods, they
share 1 pod watch and 1 cache through a `SharedInformerFactory`, and each registers its own
event handlers and its own work queue. The API server then serves 1 watch per process instead
of 1 per controller.

## Sharing a cache safely

The model's cache hands out copies, so a caller can modify what it receives without affecting
anyone else. client-go's cache hands out pointers into the shared store, to avoid copying
every object on every read. A client-go controller that changes a field of an object it read
from the cache is therefore changing the object that every other controller in the process
reads, while the server still holds the original. The other controllers then see a state that
exists nowhere else. The rule in client-go is to call the object's generated `DeepCopy`
method, which copies every nested slice and map, and to change the copy.

## Reading your own writes

A controller's own writes reach its cache by the same route as everyone else's. The server
stores the write and emits an event, and the reflector applies it. Until that event arrives,
the cache still shows the state from before the write. If a reconcile creates a pod for a
job, and a second event for the same job arrives before the pod's creation event, the next
reconcile finds no pod in the cache and creates a second one.

Kubernetes controllers use 2 techniques against this. The ReplicaSet controller, which keeps a
requested number of identical pods running, records *expectations*: after creating 3 pods, it
notes that it expects to see 3 creation events, and it leaves that ReplicaSet alone until the
cache has shown them or a timeout has passed. The second technique uses 2 fields that every
object carries. The API server increments `metadata.generation` each time the spec changes,
and a controller copies the generation it acted on into `status.observedGeneration`. When the
2 numbers are equal, the status describes the current spec. When they differ, both the
controller and anyone reading the object can see that the latest change to the spec has not
been handled yet.

## The complete program

The model is 6 source files in each language, printed here in the order the chapter built
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
