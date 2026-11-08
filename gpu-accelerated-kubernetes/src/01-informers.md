# 1. Keeping a local copy of the cluster

A training job states the hardware it needs: a number of GPUs, a GPU model, and the
device memory each GPU must have. A job that fine-tunes a model with 70 billion parameters
might ask for 4 Jetson AGX Thor GPUs with at least 100 GiB each. A Jetson Orin NX has 16 GB
of memory, shared between its CPU and GPU, so the same model does not fit there.

Kubernetes handles such a request with 2 mechanisms. The scheduler counts GPUs as an
*extended resource* named `nvidia.com/gpu`. Each machine advertises a whole number of
units, and 1 unit is 1 physical GPU by default. The count carries no model and no memory
size, so an Orin NX and a Thor both advertise `nvidia.com/gpu: 1`. The model and the
memory are expressed as node labels, such as `nvidia.com/gpu.product`. A pod selects
machines by those labels with a `nodeSelector`. Chapter 2 measures what 1 unit contains,
chapter 5 adds the labels, and chapter 8 places jobs across machines.

A program that runs training jobs reacts to 3 kinds of change. When a user creates a job,
the program starts containers on machines that satisfy the request. When the user raises
the request from 1 GPU to 2, the program replaces the containers. When the user deletes
the job, the program stops the containers, and the GPUs return to the pool. Kubernetes
calls a program like this a *controller*.

Most of the design work in a controller goes into learning about changes. A controller
follows thousands of objects. It has to see every creation, update, and deletion soon
after it happens. It must not miss a change, and it must not act on 1 change twice. A
missed deletion leaves GPUs allocated to a job that no longer exists. An update handled
twice can give 1 job 2 sets of containers.

In this chapter we build the machinery that keeps a controller informed. The program has 5
parts: an API server, a cache, a loop that keeps the cache current, a work queue, and the
controller. Each part appears with the failure it prevents. We then run the program through
a burst of edits, a dropped connection, and a network partition. The last sections match
each part with its counterpart in client-go, the library that Go controllers use.

The program exists in Go and in Rust, with the same parts and the same output. It uses only
the standard library of each language. The Go files are in `code/go/informer` and run with
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

Kubernetes stores everything it manages as *objects*. An object is a named record with 2
main parts. A training job in this chapter's model looks like this:

```text
name:    train
spec:    gpu: 2 x Thor (100 GiB)      what the user asked for
status:  gpu: 1 x Thor (100 GiB)      what the controller has provided
```

The *spec* holds the desired state, and the user writes it. The *status* holds the request
the controller has satisfied, and the controller writes it. A controller compares the 2
parts and acts when they differ. For `train`, the spec asks for 2 Thor GPUs and the status
shows 1. The controller replaces the job's container with one that holds 2 GPUs. It then
writes `2 x Thor (100 GiB)` into the status. A status equal to the spec means the
controller has nothing left to do.

All objects live behind 1 HTTP service, the *API server*. The API server stores them in
etcd, a replicated key-value database. Every read and every write of an object goes through
the API server. Users, `kubectl`, and controllers are all clients of the API server, and
none of them reads etcd directly.

## Numbering every write

A controller could poll: ask for every object every few seconds and compare the answers.
Polling fails at scale. A cluster with 50,000 pods stores a few kilobytes of JSON per pod,
so 1 listing of all pods is about 200 MB. Suppose 12 controllers each fetch that every 5 seconds.
The API server then sends 12 × 200 MB / 5 s, about 480 MB per second. Between 2
fetches, only a handful of pods change.

The alternative is a stream of changes from the API server to each client. A stream needs
a way to resume after a broken connection. Servers restart, load balancers close idle
connections, and networks fail for a few seconds. A client that reconnects must ask for the
changes it missed. For that request, it needs an identifier for the last change it
received.

The API server provides that identifier by numbering its writes. It keeps 1 counter for the
whole store. Every create, update, or delete of any object increments the counter. The new
value is stamped on the changed object as its *resource version*. The numbers come from
etcd, which gives every write a *revision* from 1 counter for the whole database. A client
that has seen every change up to version 10 asks for the changes after version 10. The
server knows exactly which changes those are.

Resource versions also prevent a *lost update*: a write that silently undoes another
client's write. In the sequence below, 2 clients read the job `train` at version 7. Each
client changes a different field.

```text
version 7   client A reads train              client B reads train
version 8   A writes count 2, read at 7       accepted
            B writes product GB10, read at 7  refused: train is at version 8
            B reads train again at version 8 and reapplies product GB10
version 9   B writes product GB10, read at 8  accepted, and count 2 is kept
```

A write replaces the whole object. Without a check, the server would store B's copy, with
the old count of 1, and A's change would disappear without an error. B's write states that
B read version 7. The job is at version 8, so the server refuses the write with the HTTP
status `409 Conflict`. B reads the job again and applies its change to version 8. Neither
client takes a lock.

## Listing, then watching

A client builds an exact copy of the objects of 1 kind with 2 requests.

1. A *list* returns every object of the kind and the resource version of the snapshot.
2. A *watch* stays open and delivers 1 *event* for each change after a given version. The
   client passes the version from its list.

The version closes a gap between the 2 requests, because other clients keep writing. In the
timeline below, the list is taken at version 10. A user edits `job-a` at version 11. The
watch opens when the store is at version 12.

```text
version:   10          11             12
           list        job-a edited   watch opened
           snapshot                   from version 10
                                      -> the server replays event 11,
                                         then sends new events as they occur
```

The watch asks for every change after version 10. The server first replays event 11 from
its record of recent changes. It then sends new events as they happen. The client holds the
snapshot at version 10 plus every later change, with nothing missing and nothing applied
twice. A watch opened at version 12 would never deliver the edit at version 11. The
client's copy of `job-a` would stay wrong until `job-a` changed again.

## When the history runs out

The server can replay only the changes it still has. etcd keeps every revision of every key
until a *compaction* discards the old ones. Without compaction, the database would grow
without limit. The Kubernetes API server compacts every 5 minutes by default.

After a compaction, a watch from an older version cannot be served, because its events are
gone. The API server answers with the HTTP status `410 Gone`. The client must list again
and watch from the new list's version.

Watches also end for ordinary reasons. The API server closes each watch after a random
timeout between 30 and 60 minutes. The random spread keeps thousands of clients from
reconnecting at the same moment. A load balancer may close a connection that carries no
data for a while. The network may fail, and new connections fail with it.

Each ending needs its own response:

| How the watch ended | What the client does |
|---|---|
| the connection closed | opens a new watch from the last version it received |
| the server cannot be reached | waits, then tries again from the same version |
| the server answered `410 Gone` | lists again and watches from the new list's version |

## Building the server

The model's API server keeps its objects in memory. It numbers every write, remembers recent
events, and answers lists and watches. It also has 3 methods that a real server lacks:
`DropWatches`, `Partition`, and `Heal`. The demonstration at the end of the chapter uses
them to cause each failure from the previous section.

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

Each part is 1 source file in each language. The sections below build the parts in this
order.

</div>

An object in the model has a name, a spec, a status, and a resource version. The spec and
the status both hold a `GPURequest`. A `GPURequest` has 3 fields: a count of whole GPUs, the
GPU model, and the memory per GPU. In a real pod, the count becomes the `nvidia.com/gpu` limit, and
the model and memory become a node selector. The spec and the status share 1 type, so the
controller decides whether it has work with 1 equality test. A change to any field, the
model as much as the count, makes the 2 differ.

An event pairs an object with the kind of change: added, modified, or deleted. The server
returns 2 errors that a client must tell apart: a conflict on a write, and `410 Gone` on a
watch.

<p class="listing"><b>Listing 1.1</b> Objects, events, and the 2 errors, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">code/go/informer/server.go</a></p>

```go
{{#include ../code/go/informer/server.go:objects}}
```


<p class="listing"><b>Listing 1.2</b> Objects, events, and the 2 errors, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">code/rust/informer/src/server.rs</a></p>

```rust
{{#include ../code/rust/informer/src/server.rs:objects}}
```


The server's state is 4 values behind 1 lock: the objects, the counter, the recent events,
and the open watches.

<p class="listing"><b>Listing 1.3</b> The server's state, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">code/go/informer/server.go</a></p>

```go
{{#include ../code/go/informer/server.go:server}}
```


<p class="listing"><b>Listing 1.4</b> The server's state, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">code/rust/informer/src/server.rs</a></p>

```rust
{{#include ../code/rust/informer/src/server.rs:server}}
```


An update carries the version the client read. If that version differs from the stored
version, the server refuses the update with a conflict. A version of 0 skips the check; the
demonstration uses it to play a user who edits a job by hand. Every successful write
increments the counter and publishes 1 event. A deletion publishes the object's final state
under a new version.

<p class="listing"><b>Listing 1.5</b> Writing: update, delete, and publish, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">code/go/informer/server.go</a></p>

```go
{{#include ../code/go/informer/server.go:writes}}
```


<p class="listing"><b>Listing 1.6</b> Writing: update, delete, and publish, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">code/rust/informer/src/server.rs</a></p>

```rust
{{#include ../code/rust/informer/src/server.rs:writes}}
```


A watch opened from version 10 must receive event 11 exactly once, even while another
client writes. The lock provides that guarantee. The server publishes events while it holds
the lock. Opening a watch holds the same lock while it replays the recent events and
registers the watcher. Each event is therefore part of the replay or arrives after
registration, never both.

<p class="listing"><b>Listing 1.7</b> Reading: list and watch, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">code/go/informer/server.go</a></p>

```go
{{#include ../code/go/informer/server.go:listwatch}}
```


<p class="listing"><b>Listing 1.8</b> Reading: list and watch, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">code/rust/informer/src/server.rs</a></p>

```rust
{{#include ../code/rust/informer/src/server.rs:listwatch}}
```


The 2 languages handle a slow watcher differently. A Go watch buffers 1,024 events. When the
buffer is full, publishing blocks while it holds the lock, and every writer stalls. The real
API server closes a watch that falls this far behind. The Rust channel has no limit. To end
a watch, the Go server closes the channel. The Rust server drops the sending half, which ends
the receiver's loop.

The last 4 methods cause the failures on demand. `Compact` discards old events, `DropWatches`
closes every watch, and `Partition` and `Heal` cut off and restore the clients. A watch that
asks for a version older than `compacted` receives the gone error.

<p class="listing"><b>Listing 1.9</b> Compaction, dropped watches, and partitions, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">code/go/informer/server.go</a></p>

```go
{{#include ../code/go/informer/server.go:faults}}
```


<p class="listing"><b>Listing 1.10</b> Compaction, dropped watches, and partitions, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">code/rust/informer/src/server.rs</a></p>

```rust
{{#include ../code/rust/informer/src/server.rs:faults}}
```


## A local copy of the objects

A client that has listed and is watching can keep a copy of every object in memory. The copy
is exact up to the last event the client received. Reading an object becomes a map lookup,
with no network request. The server sends each change to the client once. This copy is the
*cache*.

The cache is a map behind a read-write lock. Every reconcile reads the cache, and only
incoming events write to it, so many readers run at once. An addition or a modification
stores the object. A deletion removes it.

<p class="listing"><b>Listing 1.11</b> The cache, a lookup, and applying 1 event, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/cache.go">code/go/informer/cache.go</a></p>

```go
{{#include ../code/go/informer/cache.go:cache}}
```


<p class="listing"><b>Listing 1.12</b> The cache, a lookup, and applying 1 event, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/cache.rs">code/rust/informer/src/cache.rs</a></p>

```rust
{{#include ../code/rust/informer/src/cache.rs:cache}}
```


The cache also installs a complete list, and that step finds deletions that no event
reports. Suppose `job-b` is deleted while the client is disconnected, and a compaction then
discards the deletion event. The new list lacks `job-b`. The only evidence of the deletion
is that `job-b` is in the old cache and missing from the new list.

`Replace` therefore builds the new contents from the list and reports 2 groups of names.
The first group holds each object whose version differs from the cached version. The second
holds each cached name that the list no longer contains. A new object has no cached version,
which Go reads as 0 and Rust as `None`, so new objects land in the first group.

<p class="listing"><b>Listing 1.13</b> Replacing the cache with a fresh list, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/cache.go">code/go/informer/cache.go</a></p>

```go
{{#include ../code/go/informer/cache.go:replace}}
```


<p class="listing"><b>Listing 1.14</b> Replacing the cache with a fresh list, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/cache.rs">code/rust/informer/src/cache.rs</a></p>

```rust
{{#include ../code/rust/informer/src/cache.rs:replace}}
```


## The reflector

A loop keeps the cache in step with the server. The loop lists, installs the result with
`Replace`, and queues the reported names for the controller. It then watches from the list's
version and applies each event as it arrives. When the history it needs is gone, it lists
again. Kubernetes calls this loop the *reflector*, because it reflects the server's state
into local memory.

The inner loop keeps 1 variable, `version`: the version of the last event applied to the
cache. The cache is complete up to `version`, so a watch reopened from `version` continues
exactly where the last one stopped. The 3 endings from the table map onto 3 branches:

- When the server drops the connection, the reflector opens a new watch from `version`. The
  server replays whatever happened during the reconnection.
- When the server is unreachable, the reflector waits 10 milliseconds and retries with the
  same `version`. client-go waits longer after each consecutive failure. The growing wait
  keeps thousands of clients from overloading a recovering server.
- When the server answers with the gone error, `version` is older than the compaction point.
  The inner loop returns, and the outer loop lists again.

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


In the event loop, the reflector updates the cache before it queues the name. The reverse
order loses changes. A worker could take the name at once and read the cache before the
update. The worker would find the old state and finish with nothing to do. The name would
not be queued again, and the change would wait for the object's next change.

In client-go, a reflector, its cache, and the code that notifies the program of changes
together form an *informer*.

## A queue of names

The reflector could call the controller once per event. That design fails in 2 situations.

The first is a burst of edits. A user who changes a job 5 times in 1 second produces 5
events. A controller called 5 times would start work on 4 specs that were already out of
date.

The second is a relist. After `410 Gone`, `Replace` reports which names changed. The events
behind those changes no longer exist. A controller that needs every event has nothing to
react to.

The reflector therefore passes only the *names* of changed objects. The controller reads
each object's current state from the cache when it reaches the name. A queue that ignores a
name it already holds turns 5 edits into 1 reconcile. That reconcile works on the latest
spec. The controller takes names from the queue in 1 or more *workers*, and each worker
handles 1 name at a time. The model runs 1 worker.

Removing duplicates is not enough, because an object can change during a reconcile. The new
event would put the name back on the queue. A second worker would take it, and 2 workers
would act on 1 object at once. If both write a status with a version check, 1 write fails
with a conflict, and its work is wasted. If both start a container, both succeed, and the
job has 2 containers.

The queue prevents this with 2 sets beside its list of ready names. The set `dirty` holds
every name that needs processing. The set `processing` holds every name that a worker has
taken and not yet returned. When `Add` receives a name that a worker holds, it marks the
name dirty and keeps it off the ready list. When the worker calls `Done`, the queue sees the
mark and makes the name ready again. The next reconcile then reads the object after the
change. The table follows 1 name through that sequence:

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


Animation 1.1 plays the sequence with the burst of 5 edits from the run at the end of the
chapter. Its last part removes the `processing` set. The queue then hands the name to a
second worker while the first is still busy.

<figure class="anim">
<video class="motion" src="figures/work-queue.mp4" autoplay loop muted playsinline preload="metadata" aria-label="Three boxes, ready, dirty and processing, above a worker. Add puts job-a in ready and dirty. Get moves it to processing and the worker starts a reconcile. Four more Add calls during the reconcile mark the name dirty and leave ready empty. Done moves the name back to ready, and a second reconcile reads a spec of 6 GPUs. In the last part the processing set is removed: an Add during the reconcile makes the name ready, and a second worker takes it while the first is still working." data-chapters="[[0.0, &quot;Add&quot;], [7.86, &quot;Get&quot;], [18.06, &quot;Add while held&quot;], [33.66, &quot;Done&quot;], [46.86, &quot;no processing set&quot;]]"><img src="figures/work-queue.gif" alt="Three boxes, ready, dirty and processing, above a worker. Add puts job-a in ready and dirty. Get moves it to processing and the worker starts a reconcile. Four more Add calls during the reconcile mark the name dirty and leave ready empty. Done moves the name back to ready, and a second reconcile reads a spec of 6 GPUs. In the last part the processing set is removed: an Add during the reconcile makes the name ready, and a second worker takes it while the first is still working."></video>
<figcaption><b>Animation 1.1</b> One name through the work queue. Five edits lead to two reconciles, and the two never overlap.</figcaption>
</figure>

A worker that calls `Get` on an empty queue sleeps until a name arrives. While it sleeps,
it must release the lock, or `Add` could never acquire it. Both versions use a *condition
variable*: `sync.Cond` in Go and `std::sync::Condvar` in Rust. Waiting on a condition
variable releases the lock and suspends the worker in 1 step. `Add` and `Done` signal the
variable when they make a name ready. The wait sits in a loop that checks the list again on
waking, because another worker may have taken the name first.

## Reconciling

The controller takes a name, reads the object from the cache, and makes the cluster match
it. Kubernetes calls this *reconciling*.

A name missing from the cache belongs to a deleted object. A real controller would release
what it had set up for the object; the model logs a message. A status equal to the spec
needs no work. Otherwise the controller does its work, which the model represents with a
20-millisecond sleep. It then sets the status and writes the object back.

A worker loop feeds names to the reconcile function. When a reconcile fails, the loop
queues the name again. The next attempt starts from whatever the cache holds by then.

<p class="listing"><b>Listing 1.23</b> Reconciling 1 name, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/controller.go">code/go/informer/controller.go</a></p>

```go
{{#include ../code/go/informer/controller.go:reconcile}}
```


<p class="listing"><b>Listing 1.24</b> Reconciling 1 name, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/controller.rs">code/rust/informer/src/controller.rs</a></p>

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


The reconcile function reads only the object's current state, with no record of why it was
called. A name queued once and a name queued 10 times lead to the same action. A change
reported by an event and a change found by a relist also lead to the same action.

This style is called *level-triggered*. The term comes from digital electronics. A
level-triggered circuit responds to the present level of a signal. An *edge-triggered*
circuit responds to each transition. A controller that reacted to individual events would
be edge-triggered. It would waste work during bursts and miss changes whose events a
compaction discarded.

## Writing back to the server

The cache trails the server by the time an event takes to arrive. During the 20 milliseconds
of a reconcile, a user may change the spec. An unconditional write would store the old spec
with a status computed for it. The user's edit would be lost.

The version check from the lost-update example prevents this. The controller writes the
object with the version it read. If the object changed meanwhile, the server refuses the
write with a conflict. The worker loop queues the name again, and the next reconcile reads
the newer object. This technique is called *optimistic concurrency*. The controller takes no
lock, and the server detects a concurrent change at write time.

## Running the model

Figure 1.1 shows the 5 parts together. It numbers the 2 steps the reflector takes for each
event.

<figure>
<img src="figures/informer-pipeline.svg" alt="The API server numbers every write and stores objects in etcd. Inside the controller's process, the reflector receives events, applies each one to the cache, and then adds the object's name to the work queue. The controller gets a name from the queue, reads the object from the cache, and writes the status back to the API server with the version it read.">
<figcaption><b>Figure 1.1</b> The path of 1 change: an event from the API server, the cache, the work queue, a reconcile, and a conditional write back to the server.</figcaption>
</figure>

The demonstration creates 2 jobs and starts the reflector and the controller. It then
causes each situation from this chapter in turn:

1. a burst of 5 edits that arrives during a reconcile;
2. a dropped watch;
3. a partition, during which a job is deleted and the history is compacted.

The Go version runs the reflector and the controller as goroutines. The Rust version runs
them on threads, which share the server, cache, and queue through `Arc` handles. Both log to
standard error, with the milliseconds since the program started.

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

The first 3 lines are the initial list and 1 reconcile for each job. Each status write is a
change too, so the reflector queues the name again. The next reconcile finds the status
equal to the spec and returns without a log line.

The burst of 5 edits led to 2 reconciles of `job-a`:

1. The controller took the name after the first edit. It read a spec of `2 x Thor (100 GiB)`
   at version 5 and began 20 milliseconds of work.
2. The other 4 edits arrived during that work and moved the object to version 9. The
   controller held the name, so the queue only marked it dirty.
3. The status write based on version 5 failed with a conflict.
4. `Done` made the name ready again. The next reconcile read `6 x Thor (100 GiB)` at version
   9 and wrote it into the status at version 10.

The specs for 3, 4, and 5 GPUs were replaced before the controller read them. The controller
did no work for them.

When the watch was dropped, the reflector reopened it from version 10 without a list. During
the partition, `job-b` was deleted at version 11, and the history was compacted up to 11.
After the partition, the reflector asked to resume from version 10. The server answered
`410 Gone`, and the reflector listed again. The new list held only `job-a`. `Replace`
reported `job-b` as missing, and the controller released its GPUs. The client found the
deletion only by comparing the list with its cache.

Animation 1.2 replays the log from the list at version 2 to the list at version 11. The
server's objects are on the left, and the cache is on the right.

<figure class="anim">
<video class="motion" src="figures/list-watch.mp4" autoplay loop muted playsinline preload="metadata" aria-label="The API server on the left with job-a, job-b and its recent events; the reflector's cache on the right. The reflector lists at version 2 and opens a watch. Events 3 to 10 arrive and the cache follows. The watch is closed and reopened from 10 with no list. During a partition job-b is deleted at version 11 and the history is compacted, while the cache still holds job-b. After the partition the server answers a watch from 10 with 410 Gone, the reflector lists at version 11, and job-b, present in the old cache and missing from the list, is removed." data-chapters="[[0.0, &quot;list&quot;], [10.01, &quot;watch&quot;], [34.28, &quot;drop&quot;], [43.69, &quot;partition&quot;], [60.08, &quot;410 Gone&quot;]]"><img src="figures/list-watch.gif" alt="The API server on the left with job-a, job-b and its recent events; the reflector's cache on the right. The reflector lists at version 2 and opens a watch. Events 3 to 10 arrive and the cache follows. The watch is closed and reopened from 10 with no list. During a partition job-b is deleted at version 11 and the history is compacted, while the cache still holds job-b. After the partition the server answers a watch from 10 with 410 Gone, the reflector lists at version 11, and job-b, present in the old cache and missing from the list, is removed."></video>
<figcaption><b>Animation 1.2</b> The run of the model: a list, a watch, a dropped watch that resumes, and a partition that ends in <code>410 Gone</code> and a second list.</figcaption>
</figure>

## The same design in client-go

Go controllers use client-go, either directly or through controller-runtime, a library built
on it. Every part of the model has a counterpart in client-go:

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

client-go adds 5 mechanisms that the model leaves out. Each one answers a problem from this
chapter.

*The DeltaFIFO.* client-go places a queue called the DeltaFIFO between the reflector and the
cache. The queue collects each object's changes in arrival order. The code that updates the
cache takes 1 object at a time, with all of its pending changes. A relist can show that an
object has disappeared. The DeltaFIFO then emits a deletion wrapped in a
`DeletedFinalStateUnknown` marker. The marker tells event handlers that the object is the
last state the cache saw, which may be older than the state at deletion.

*Bookmarks.* The API server can send *bookmark* events, which carry a resource version and
no object. A watch on a rarely changing kind can go a long time without events. The version
it would resume from grows old, and after the next compaction a reconnect fails with
`410 Gone`. Bookmarks move the watch's position forward while nothing changes, so a
reconnect usually succeeds.

*Resync.* An informer can have a *resync period*. At each period, it queues the name of every
cached object again, from memory, with no request to the server. Resync serves controllers
that manage something outside Kubernetes, such as a cloud load balancer. A manual change to
the load balancer produces no Kubernetes event. A periodic resync gives the controller a
regular chance to find and correct the difference.

*Backoff.* The work queue waits before it retries a name whose reconcile failed. The wait
starts at 5 milliseconds and doubles after each failure, up to 1,000 seconds. The queue also
limits its overall rate. The model retries at once. A real controller that retried at once
while its writes kept failing would flood the API server with requests.

*Shared informers.* Informers are shared within a process. When 10 controllers in 1 program
watch pods, they share 1 pod watch and 1 cache through a `SharedInformerFactory`. Each
controller registers its own event handlers and its own work queue. The API server then
serves 1 watch per process.

## Sharing a cache safely

The model's cache returns copies. A caller can modify a copy, and no one else sees the change.
The client-go cache returns pointers into the shared store, which saves a copy on every read.
A client-go controller that modifies a cached object therefore modifies the object that
every other controller in the process reads. The server still holds the original, so the
other controllers see a state that exists nowhere else. The rule in client-go is to call the
object's generated `DeepCopy` method and modify the copy. `DeepCopy` copies every nested
slice and map.

## Reading your own writes

A controller's own writes reach its cache by the same route as other writes. The server
stores the write and emits an event, and the reflector applies the event. Until then, the
cache shows the state before the write. Suppose a reconcile creates a pod for a job. A second
event for the job arrives before the pod's creation event. The next reconcile finds no pod
in the cache and creates a second pod.

Kubernetes controllers use 2 techniques against this gap. The first is *expectations*, used
by the ReplicaSet controller, which keeps a requested number of identical pods running.
After it creates 3 pods, it records that it expects 3 creation events. It leaves that
ReplicaSet alone until the cache shows the 3 pods or a timeout passes.

The second technique uses 2 fields of every object. The API server increments
`metadata.generation` each time the spec changes. A controller copies the generation it
acted on into `status.observedGeneration`. Equal numbers mean the status describes the
current spec. Different numbers show that the latest spec change is still unhandled.

## The complete program

The model is 6 source files in each language, in the order this chapter built them.

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

<div class="summary">

## Summary

- A Kubernetes object holds a spec, written by the user, and a status, written by the
  controller. A controller acts when the 2 differ.
- `nvidia.com/gpu` counts whole GPUs and carries no model or memory size. Node labels carry
  the GPU model.
- The API server numbers every write. The number, the resource version, lets a watch resume
  and lets the server refuse a write based on an old read with `409 Conflict`.
- A list followed by a watch from the list's version gives an exact copy of the objects.
  After a compaction, the server answers `410 Gone`, and the client lists again.
- A relist finds deletions by comparing the new list with the cache.
- A work queue of names, with `dirty` and `processing` sets, merges bursts of edits and keeps
  2 workers off 1 object.
- A level-triggered reconcile reads the current state, and a conditional write catches
  changes made during the reconcile.

Section 1.1 runs the same design on a real cluster with controller-runtime and kube-rs.

</div>

## Exercises

1. A list returns version 40. Before the watch opens, 3 writes occur, at versions 41, 42,
   and 43. Which events does a watch opened from version 40 deliver? Which events does a
   watch opened from version 43 deliver, and which change does it miss?
2. Clients A and B read `train` at version 15. A writes at version 16. B then writes with
   "read at 15". Give the server's answer, and list the 2 steps B takes next.
3. Follow `job-a` through the work queue for this sequence: `Add`, `Get`, `Add`, `Add`,
   `Done`, `Get`, `Done`. After each call, give the contents of the ready list, `dirty`, and
   `processing`. How many reconciles run?
4. Swap the 2 statements in the reflector's event loop, so that the name is queued before
   the cache is updated. Describe a run of the model in which a change goes unhandled.
5. A cluster has 20,000 pods of 4 KB each. 8 controllers poll every 10 seconds. Compute the
   bytes per second the API server sends.
6. Add a field `MinCUDA string` to `GPURequest` in both languages. Which lines of the
   reconcile function change, and why does the equality test still work?
