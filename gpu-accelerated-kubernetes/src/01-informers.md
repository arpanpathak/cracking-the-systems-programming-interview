# 1. Keeping a local copy of the cluster

Suppose we want to write a program that runs GPU training jobs on Kubernetes. A user
creates a job and says "this job needs one GPU". Our program has to notice the new job,
start its container on a machine with a free GPU, and write down that the job is
running. When the user changes the job to ask for two GPUs, our program has to notice
that too and replace the container. When the user deletes the job, our program has to
stop the container and free the GPU.

In Kubernetes, a program like this is called a *controller*. In this chapter, we will
learn how a controller finds out what is happening in the cluster, which turns out to be
the most interesting part of the whole design. We will first build intuition by reasoning
about the problems a controller runs into, and quickly prototype the data structures that
solve them: a small API server, a cache, a loop that keeps the cache up to date, a work
queue, and the controller itself. Then we will run our prototype through a burst of edits,
a dropped connection, and a network partition, and finally we will map each piece onto
client-go, the library that real Go controllers use.

We will build the model twice, in Go and in Rust, with the same six parts and the same
behaviour. The Go files are in `code/go/informer`, and we run them with
`go run ./informer` from `code/go`. The Rust files are in `code/rust/informer`, and we run
them with `cargo run -p informer` from `code/rust`. Neither version needs anything beyond
its language's standard library.

<div class="covers">

This chapter covers

- objects, and the API server that stores them
- resource versions, and the `409 Conflict` that protects a write
- listing and watching, and the `410 Gone` that forces a second list
- a cache, a reflector, a work queue, and a controller, each in Go and in Rust
- one run through a burst of edits, a dropped watch, and a partition
- the parts of client-go that match the model

</div>

## Objects, specs, and statuses

Kubernetes describes a cluster as a collection of *objects*. An object is a record with a
name and two main parts. The *spec* holds what a user asked for: "run this image with one
GPU". The *status* holds what has actually happened so far: "running on one GPU". A
training job in our cluster will be one such object.

All objects live behind a single HTTP service, the *API server*. Every read and every
write of every object goes through it, and it stores the objects in etcd, a replicated
key-value database. Users, command-line tools, and controllers are all just clients of
the API server.

A controller's job is to compare each object's spec with the real world and act on any
difference, then record what it did in the status. To do that well, it needs two things
from the API server: an accurate view of every object of its kind, and news of every
change within a fraction of a second. Let us see how to get both.

## Numbering every write

The most obvious approach is to ask the API server for every object every few seconds.
It works for a handful of objects, and it falls apart as the cluster grows. A cluster with
50,000 pods stores a few kilobytes of JSON per pod, so a single request for all of them
transfers around 200 megabytes. If a dozen controllers each did that every five seconds,
the API server would be sending almost half a gigabyte per second, and between two of
those requests only a handful of pods would have changed.

What we really want is for the API server to tell us about each change as it happens.
That idea brings a problem with it. Connections break: networks fail, servers restart,
and proxies close connections they consider idle. When our connection breaks and we open
a new one, we need to say "send me everything I missed", and that requires a way to name
the point where we left off.

The API server solves this by numbering its writes. It keeps a single counter for the
whole store. Every time any object is created, updated, or deleted, it increments the
counter and stamps the new value onto the object that changed. Kubernetes calls this
number the object's *resource version*. The numbers come straight from etcd, which gives
every write a *revision* number from one counter for the whole database.

The same number helps with a second problem. Imagine two clients read a job at version 7.
The first changes the GPU count and writes the job back. The second changes the image and
writes the job back a moment later, still based on what it read at version 7. Without
any check, the second write would replace the whole object and silently undo the first
client's change. With resource versions, the second client sends "I read this at
version 7" along with its write. The object is now at version 8, so the server refuses
the write with the HTTP status `409 Conflict`, and the second client knows it has to read
the job again and redo its change on top of the new version.

## Listing, then watching

With numbered writes, a client can build an exact view of the cluster in two steps.

First it asks for every object. This request is called a *list*, and the response carries
the objects together with the resource version at which the server took the snapshot.
Then the client opens a *watch*: a request that stays open and asks the server to send
every change made after a given version, one *event* per change. The client passes the
version it got from the list.

Passing that version is the important detail. The list and the watch are two separate
requests, and other clients keep writing in between. Suppose our list is taken at
version 10, then a user edits a job at version 11, and only then does our watch open, when
the store is at version 12:

```text
version:   10          11             12
           list        job-a edited   watch opened
           snapshot                   from version 10
                                      -> the server replays event 11,
                                         then sends new events as they occur
```

Because the watch asks for everything after version 10, the server first sends us event 11
from its record of recent changes and then carries on with new events. Our view is the
snapshot at version 10 plus every change after it: nothing missing, nothing counted twice.
If we had opened the watch at the current version, 12, we would have skipped the edit at
version 11 and kept an out-of-date copy of `job-a` until the job happened to change again.

## When the history runs out

The server can only replay changes it still has. etcd keeps every revision of every key
until it is told to throw old ones away, and that clean-up is called *compaction*.
Without it the database would grow forever. The Kubernetes API server asks etcd to
compact every five minutes by default. After a compaction, a watch that asks to resume
from an older version cannot be served, because the events it needs have been thrown
away. The API server answers with the HTTP status `410 Gone`, and the only way for us to
get back to an exact view is to list again and watch from the new list's version.

Watches also end for ordinary reasons. The API server closes every watch after a timeout,
chosen at random between 30 and 60 minutes by default, so that thousands of clients do not
all reconnect at the same moment. A load balancer between us and the server may close a
connection that has been quiet for too long. And the network may fail for a while, so
that even new connections fail.

Each of these calls for a different response, and our client has to tell them apart. If
the watch simply closed, we reopen it from the last version we received. If we cannot
connect at all, we wait and try again. If the server says `410 Gone`, we list again.

## Building the server

Now we have enough understanding to build a model. We start with the server. It keeps the
objects in memory, numbers every write, records recent events, and answers lists and
watches. We also give it three extra methods, `DropWatches`, `Partition`, and `Heal`, so
that our demonstration at the end of the chapter can cause each of the failures we just
discussed.

<div class="lld">

Low-level design: the model

| Part | Holds | Rule it keeps |
|---|---|---|
| `Object` | a name, a spec, a status, a version | the version is the number of the write that last changed it |
| `APIServer` | the objects, the write counter, recent events, the open watches | every write increments the counter and publishes one event |
| `Cache` | a copy of every object | exact up to the last event applied |
| `Reflector` | the server, the cache, the queue | updates the cache before it queues a name |
| `WorkQueue` | the ready names, and the sets `dirty` and `processing` | a name is with at most one worker at a time |
| `Controller` | the server, the cache, the queue | acts only on the object's current state |

Each part is one source file in each language, and the sections below build them in this
order.

</div>

The server's data comes first: the object, the event that reports a change to it, and the
two errors a client has to tell apart.

<p class="listing"><b>Listing 1.1</b> Objects, events, and the two errors, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">code/go/informer/server.go</a></p>

```go
{{#include ../code/go/informer/server.go:objects}}
```


<p class="listing"><b>Listing 1.2</b> Objects, events, and the two errors, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">code/rust/informer/src/server.rs</a></p>

```rust
{{#include ../code/rust/informer/src/server.rs:objects}}
```


The model reduces a job to a GPU count in its spec and in its status.

The server itself is a lock around four things: the objects, the counter, the events it
still has, and the watches that are open.

<p class="listing"><b>Listing 1.3</b> The server's state, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">code/go/informer/server.go</a></p>

```go
{{#include ../code/go/informer/server.go:server}}
```


<p class="listing"><b>Listing 1.4</b> The server's state, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">code/rust/informer/src/server.rs</a></p>

```rust
{{#include ../code/rust/informer/src/server.rs:server}}
```


Two methods change objects, and both end by publishing an event.

<p class="listing"><b>Listing 1.5</b> Writing: update, delete, and publish, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">code/go/informer/server.go</a></p>

```go
{{#include ../code/go/informer/server.go:writes}}
```


<p class="listing"><b>Listing 1.6</b> Writing: update, delete, and publish, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">code/rust/informer/src/server.rs</a></p>

```rust
{{#include ../code/rust/informer/src/server.rs:writes}}
```


`Update` carries both uses of the resource version. A zero version skips the check, which
the demonstration uses to play a user editing a job. Any other version must equal the
stored one, and a missing object counts as version 0. Each successful write increments the
counter and publishes one event. `Delete` publishes the object's final state under a new
version.

Two methods read: one for the snapshot and one for the stream of changes after it.

<p class="listing"><b>Listing 1.7</b> Reading: list and watch, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">code/go/informer/server.go</a></p>

```go
{{#include ../code/go/informer/server.go:listwatch}}
```


<p class="listing"><b>Listing 1.8</b> Reading: list and watch, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">code/rust/informer/src/server.rs</a></p>

```rust
{{#include ../code/rust/informer/src/server.rs:listwatch}}
```


`publish` runs while the server lock is held, and `Watch` holds the same lock while it
replays the history and registers the new watch. Every event is therefore either in the
replayed history or delivered after registration: no watch misses an event or receives
one twice.

A Go watch buffers 1,024 events. A client that stops reading would eventually block
`publish` while it holds the lock and stall every writer; the real API server closes such
a watch. The Rust channel is unbounded. In Go the server ends a watch by closing its
channel; in Rust it drops the sender, which ends the receiver's loop.

The last four methods cause the failures of the previous section on request.

<p class="listing"><b>Listing 1.9</b> Compaction, dropped watches, and partitions, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">code/go/informer/server.go</a></p>

```go
{{#include ../code/go/informer/server.go:faults}}
```


<p class="listing"><b>Listing 1.10</b> Compaction, dropped watches, and partitions, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">code/rust/informer/src/server.rs</a></p>

```rust
{{#include ../code/rust/informer/src/server.rs:faults}}
```


`Watch` fails with the gone error when the requested version is older than `compacted`.
`Compact`, `DropWatches`, `Partition`, and `Heal` exist only to reproduce the failures
described above.

## A local copy of the objects

Once we have listed and are watching, we can keep our own copy of every object in memory.
The copy is exact up to the last event we received. Reading an object becomes a map
lookup instead of a network request, and the server only has to send each change to us
once. We call this copy the *cache*.

The cache is a map behind a lock, with a method for one event.

<p class="listing"><b>Listing 1.11</b> The cache, a lookup, and applying one event, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/cache.go">code/go/informer/cache.go</a></p>

```go
{{#include ../code/go/informer/cache.go:cache}}
```


<p class="listing"><b>Listing 1.12</b> The cache, a lookup, and applying one event, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/cache.rs">code/rust/informer/src/cache.rs</a></p>

```rust
{{#include ../code/rust/informer/src/cache.rs:cache}}
```


Both caches use a read-write lock: every reconcile reads the cache, and only incoming
events write to it.

`Apply` records a single event. It stores the object for an addition or a modification
and removes it for a deletion.

A second method installs a whole list.

<p class="listing"><b>Listing 1.13</b> Replacing the cache with a fresh list, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/cache.go">code/go/informer/cache.go</a></p>

```go
{{#include ../code/go/informer/cache.go:replace}}
```


<p class="listing"><b>Listing 1.14</b> Replacing the cache with a fresh list, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/cache.rs">code/rust/informer/src/cache.rs</a></p>

```rust
{{#include ../code/rust/informer/src/cache.rs:replace}}
```


`Replace` installs the result of a fresh list, and it has one more job that events alone
cannot do. Think about what happens when we relist after `410 Gone`. Some objects may have
been deleted while we were disconnected, and their deletion events were thrown away by the
compaction. Nobody will ever send us those events. The only evidence that the objects are
gone is that they are in our old cache and missing from the new list. So `Replace` builds
the new contents from the list, reports every object whose version differs from the one we
had, and then reports every name that was in the old cache but is missing from the list.
Objects that are new to us have no cached version at all; Go reads the missing entry as
version 0 and Rust compares against `None`, so new objects get reported as changed too.

## The reflector

Next we need a loop that keeps the cache in step with the server. It lists, installs the
result with `Replace`, and queues the names of the objects that `Replace` reported, so
that the controller will look at them. Then it watches from the list's version and
applies each event as it arrives. When the history it needs is gone, it lists again. We
call this loop the *reflector*.

The outer loop lists, installs the list, and hands over to the watch.

<p class="listing"><b>Listing 1.15</b> The reflector and its list step, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/reflector.go">code/go/informer/reflector.go</a></p>

```go
{{#include ../code/go/informer/reflector.go:run}}
```


<p class="listing"><b>Listing 1.16</b> The reflector and its list step, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/reflector.rs">code/rust/informer/src/reflector.rs</a></p>

```rust
{{#include ../code/rust/informer/src/reflector.rs:run}}
```


The inner loop watches, and decides what each kind of ending calls for.

<p class="listing"><b>Listing 1.17</b> Watching from a version, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/reflector.go">code/go/informer/reflector.go</a></p>

```go
{{#include ../code/go/informer/reflector.go:watch}}
```


<p class="listing"><b>Listing 1.18</b> Watching from a version, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/reflector.rs">code/rust/informer/src/reflector.rs</a></p>

```rust
{{#include ../code/rust/informer/src/reflector.rs:watch}}
```


The heart of the reflector is `watchFrom` (`watch_from` in Rust). It keeps a variable,
`version`, that always holds the version of the last event it applied to the cache. That
means our cache is complete up to `version`, so a new watch opened from `version` picks up
exactly where the old one stopped. With that in mind, here is what the function does for
each of the three ways a watch can end:

- If the watch channel closes because the server dropped the connection, we log the
  version and open a new watch from it. The server replays anything that happened while
  we were reconnecting.
- If `Watch` fails because the server is unreachable, we wait 10 milliseconds and try
  again with the same version. client-go waits a little longer after each failure in a
  row, so that thousands of clients do not hammer a server that is trying to recover.
- If `Watch` fails with the gone error, our version is older than the compaction point,
  and no watch can continue from it. `watchFrom` returns, and `Run` starts over with a new
  list.

Look closely at the order of the two calls inside the event loop: we update the cache
first, and only then queue the object's name. Suppose we did it the other way round. A
worker could take the name straight away, read the object from the cache before our update
landed, see the old state, decide there was nothing to do, and finish. The name would not
be queued again, and the change would sit unhandled until the object happened to change
once more. Updating the cache first rules that out.

client-go uses the same name for this loop, *reflector*, because it reflects the server's
state into local memory. A reflector together with its cache, plus the plumbing that tells
other code about changes, is what client-go calls an *informer*.

## A queue of names

The reflector knows when an object changes, and the controller needs to hear about it.
The obvious design is for the reflector to call the controller once for every event.
Let us see why that design breaks down.

The first problem is bursts. A user who edits a job five times in one second produces five
events. A controller called five times would start work for four specs that were already
out of date before the work finished. The second problem is lost events. After a relist,
`Replace` tells us which names changed, but the individual events that led there are gone
for good. A controller that relies on seeing every event would have nothing to react to,
and it would miss changes every time the history was compacted.

So we give the controller only the *names* of objects that changed, and the controller
reads the object's current state from the cache when it gets to the name. Five edits now
put the same name in the queue five times, and if the queue simply ignores a name it
already holds, they turn into one reconcile that acts on the latest spec. The controller
takes names from the queue in one or more *workers*, each processing one name at a time.
Our model runs a single worker.

The queue's state is a list and two sets behind one lock.

<p class="listing"><b>Listing 1.19</b> The queue's state, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/queue.go">code/go/informer/queue.go</a></p>

```go
{{#include ../code/go/informer/queue.go:state}}
```


<p class="listing"><b>Listing 1.20</b> The queue's state, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/queue.rs">code/rust/informer/src/queue.rs</a></p>

```rust
{{#include ../code/rust/informer/src/queue.rs:state}}
```


Besides the list of names that are ready for a worker, the queue keeps two sets. `dirty`
holds every name that needs processing. `processing` holds every name that a worker has
taken and not yet handed back.

Three operations work on that state.

<p class="listing"><b>Listing 1.21</b> Add, Get, and Done, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/queue.go">code/go/informer/queue.go</a></p>

```go
{{#include ../code/go/informer/queue.go:ops}}
```


<p class="listing"><b>Listing 1.22</b> Add, Get, and Done, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/queue.rs">code/rust/informer/src/queue.rs</a></p>

```rust
{{#include ../code/rust/informer/src/queue.rs:ops}}
```


Why the second set? Because an object can change while a worker is in the middle of
reconciling it. Without `processing`, the new event would put the name back in the ready
list, a second worker would take it, and two workers would be acting on the same object at
once. If both write a status with a version check, one of them fails with a conflict and
its work is wasted. If both do something outside Kubernetes, like starting a container,
both succeed, and our job ends up with two containers. So the queue holds the name back
instead. When `Add` sees a name that a worker is holding, it marks the name dirty but
leaves it out of the ready list. When the worker calls `Done`, the queue notices the mark
and makes the name ready again, and the next reconcile sees the object as it is after the
change. The table follows one name through that sequence:

```text
call             ready      dirty      processing   effect
---------------  ---------  ---------  -----------  --------------------------------
Add(job-a)       [job-a]    {job-a}    {}           ready for a worker
Get() -> job-a   []         {}         {job-a}      a worker takes it
Add(job-a)       []         {job-a}    {job-a}      edited during the run: marked
Add(job-a)       []         {job-a}    {job-a}      already marked: no change
Done(job-a)      [job-a]    {job-a}    {}           marked, so ready again
```

Animation 1.1 plays that sequence with the burst of five edits from the run at the end of this
chapter. Its last part repeats the calls on a queue that has no `processing` set and gives
the name to a second worker.

<figure class="anim">
<video class="motion" src="figures/work-queue.mp4" autoplay loop muted playsinline preload="metadata" aria-label="Three boxes, ready, dirty and processing, above a worker. Add puts job-a in ready and dirty. Get moves it to processing and the worker starts a reconcile. Four more Add calls during the reconcile mark the name dirty and leave ready empty. Done moves the name back to ready, and a second reconcile reads a spec of 6 GPUs. In the last part the processing set is removed: an Add during the reconcile makes the name ready, and a second worker takes it while the first is still working." data-chapters="[[0.0, &quot;Add&quot;], [7.86, &quot;Get&quot;], [18.06, &quot;Add while held&quot;], [33.66, &quot;Done&quot;], [46.86, &quot;no processing set&quot;]]"><img src="figures/work-queue.gif" alt="Three boxes, ready, dirty and processing, above a worker. Add puts job-a in ready and dirty. Get moves it to processing and the worker starts a reconcile. Four more Add calls during the reconcile mark the name dirty and leave ready empty. Done moves the name back to ready, and a second reconcile reads a spec of 6 GPUs. In the last part the processing set is removed: an Add during the reconcile makes the name ready, and a second worker takes it while the first is still working."></video>
<figcaption><b>Animation 1.1</b> One name through the work queue. Five edits lead to two reconciles, and the two never overlap.</figcaption>
</figure>

One more detail: a worker that calls `Get` on an empty queue has to go to sleep until a
name arrives, and it must not hold the lock while it sleeps, or `Add` could never get in
to add one. Both versions solve this with a *condition variable*, `sync.Cond` in Go and
`std::sync::Condvar` in Rust. Waiting on a condition variable releases the lock and puts
the worker to sleep in one step. `Add` and `Done` signal it whenever they make a name
ready. The wait sits inside a loop that checks the list again after waking up, because
with several workers another one may have taken the name first.

## Reconciling

Now we can write the controller itself. It takes a name from the queue, reads the object
from the cache, and makes the world match it. Kubernetes calls this *reconciling*:
bringing what actually exists into agreement with what the user asked for.

The part that does the work is one function.

<p class="listing"><b>Listing 1.23</b> Reconciling one name, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/controller.go">code/go/informer/controller.go</a></p>

```go
{{#include ../code/go/informer/controller.go:reconcile}}
```


<p class="listing"><b>Listing 1.24</b> Reconciling one name, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/controller.rs">code/rust/informer/src/controller.rs</a></p>

```rust
{{#include ../code/rust/informer/src/controller.rs:reconcile}}
```


`reconcile` first looks the object up in the cache. If the object is missing, it was
deleted, and a real controller would now release whatever it had set up for it; our model
logs a message. If the status already matches the spec, there is nothing to do.
Otherwise the controller does its work, which our model stands in for with a
20-millisecond sleep, sets the status, and writes the object back.

Notice that `reconcile` looks only at the object's current state. It does not know, or
care, why it was called. A name queued once and a name queued ten times lead to the same
action, and so do a change reported by an event and a change discovered by a relist.
Engineers call this style *level-triggered*, a term borrowed from digital electronics,
where a level-triggered circuit responds to the present level of a signal and an
*edge-triggered* circuit responds to each change of the signal. A controller that reacted
to individual events would be edge-triggered, and it would do wasted work during bursts
of edits and miss changes whose events a compaction had discarded.

Around it sits the loop that feeds it names.

<p class="listing"><b>Listing 1.25</b> The controller and its worker loop, in Go. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/controller.go">code/go/informer/controller.go</a></p>

```go
{{#include ../code/go/informer/controller.go:run}}
```


<p class="listing"><b>Listing 1.26</b> The controller and its worker loop, in Rust. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/controller.rs">code/rust/informer/src/controller.rs</a></p>

```rust
{{#include ../code/rust/informer/src/controller.rs:run}}
```


`Run` is the worker loop. It takes a name, reconciles it, and hands it back with `Done`.
If the reconcile failed, it adds the name again so that the next attempt starts from
whatever the cache holds by then.

## Writing back to the server

Our cache always trails the server by the time it takes an event to arrive. During the
20 milliseconds that `reconcile` spends working, a user might change the spec. If the
controller then wrote its copy of the object back unconditionally, it would store the old
spec together with a status computed for the old spec, and the user's edit would simply
disappear.

This is exactly the situation the resource version check was made for. `reconcile` writes
the object with the version it read. If the object changed in the meantime, the server
refuses the write with a conflict, `Run` puts the name back in the queue, and the next
reconcile reads the newer object from the cache. This approach is called *optimistic
concurrency*: we take no lock on the object, we assume nobody else will change it, and we
rely on the server to catch the cases where that assumption was wrong at the moment we
write.

## Running the model

Figure 1.1 shows the five parts together and numbers the two steps the reflector takes for
each event.

<figure>
<img src="figures/informer-pipeline.svg" alt="The API server numbers every write and stores objects in etcd. Inside the controller's process, the reflector receives events, applies each one to the cache, and then adds the object's name to the work queue. The controller gets a name from the queue, reads the object from the cache, and writes the status back to the API server with the version it read.">
<figcaption><b>Figure 1.1</b> The path of one change: an event from the API server, the cache, the work queue, a reconcile, and a conditional write back to the server.</figcaption>
</figure>

Time to see it all work together. `main` creates two jobs, starts the reflector and the
controller, and then puts the machinery through each situation from this chapter: a burst
of edits that arrives while a reconcile is running, a dropped watch, and a partition
during which a job is deleted and the history is compacted. The Go version runs the
reflector and the controller as goroutines. The Rust version runs them on threads, each
holding an `Arc` handle to the shared server, cache, and queue. Both write their log to
standard error, with the number of milliseconds since the program started; Rust does this
with a small `log!` macro, and Go with a `logf` function.

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

The Rust version prints the same sequence of events. Its timings differ by a millisecond
or two, and its field names follow Rust's naming conventions:

```console
$ cargo run -p informer
{{#include ../code/output/rust-informer.txt}}
```

Let us read the log from the top. The first three lines are the initial list and one
reconcile for each job. Each status write is itself a change, so the reflector receives an
event for it and queues the name again. The reconcile that follows finds the status equal
to the spec and returns quietly, so each job appears only once.

The burst of five edits led to just two reconciles of `job-a`. The controller took the
name right after the first edit, read a spec of 2 GPUs at version 5, and started its
20 milliseconds of work. The other four edits arrived while it was busy, moving the object
to version 9, and because the controller was holding the name, the queue marked it dirty.
When the controller wrote its status with version 5, the server refused it with a
conflict. `Done` made the name ready again, the next reconcile read a spec of 6 GPUs at
version 9, and it wrote a status of 6 at version 10. The specs of 3, 4, and 5 GPUs had been
replaced before the controller ever read them, so it did no work for them at all.

When the watch was dropped, the reflector reopened it from version 10, the version of the
last event it had applied, and there was no need to list. During the partition, `job-b`
was deleted at version 11 and the history was compacted, which moved the compaction point
to 11. When the partition ended, the reflector asked to resume from version 10, the server
answered `410 Gone`, and the reflector listed again. The new list held only `job-a`,
`Replace` reported `job-b` as missing, and the controller found no `job-b` in the cache and
released its GPUs. Our client learned about the deletion by comparing the list with its
cache, because the compaction had thrown the deletion event away.

Animation 1.2 replays the log from the list at version 2 to the list at version 11, with the
server's objects on the left and the cache on the right.

<figure class="anim">
<video class="motion" src="figures/list-watch.mp4" autoplay loop muted playsinline preload="metadata" aria-label="The API server on the left with job-a, job-b and its recent events; the reflector's cache on the right. The reflector lists at version 2 and opens a watch. Events 3 to 10 arrive and the cache follows. The watch is closed and reopened from 10 with no list. During a partition job-b is deleted at version 11 and the history is compacted, while the cache still holds job-b. After the partition the server answers a watch from 10 with 410 Gone, the reflector lists at version 11, and job-b, present in the old cache and missing from the list, is removed." data-chapters="[[0.0, &quot;list&quot;], [10.01, &quot;watch&quot;], [34.28, &quot;drop&quot;], [43.69, &quot;partition&quot;], [60.08, &quot;410 Gone&quot;]]"><img src="figures/list-watch.gif" alt="The API server on the left with job-a, job-b and its recent events; the reflector's cache on the right. The reflector lists at version 2 and opens a watch. Events 3 to 10 arrive and the cache follows. The watch is closed and reopened from 10 with no list. During a partition job-b is deleted at version 11 and the history is compacted, while the cache still holds job-b. After the partition the server answers a watch from 10 with 410 Gone, the reflector lists at version 11, and job-b, present in the old cache and missing from the list, is removed."></video>
<figcaption><b>Animation 1.2</b> The run of the model: a list, a watch, a dropped watch that resumes, and a partition that ends in <code>410 Gone</code> and a second list.</figcaption>
</figure>

## The same design in client-go

Real Go controllers use client-go, either directly or through controller-runtime, a
higher-level library built on top of it. Every part of our model has a counterpart there:

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

client-go also has a few mechanisms that our model leaves out, and each one fixes a
problem we can now recognize.

Between the reflector and the cache, client-go puts a queue called the *DeltaFIFO*. For
each object it collects the changes in the order they arrived, and the code that updates
the cache and notifies controllers takes one object at a time along with all of its
pending changes. When a relist shows that an object has disappeared, the DeltaFIFO emits
a deletion whose object is wrapped in a `DeletedFinalStateUnknown` marker. The marker
warns event handlers that the object they receive is the last state the cache had seen,
which may be older than the state the object was in when it was deleted.

The API server can send *bookmark* events, which carry a resource version and no object.
They solve a problem with quiet watches. A watch on a kind of object that rarely changes
can go a long time without any events, so the version it would resume from grows old.
After the next compaction, reconnecting from that version would fail with `410 Gone` and
force a full relist. Bookmarks move the watch's position forward even when nothing
changes, so a reconnect usually succeeds.

An informer can be given a *resync period*. Every so often it queues the name of every
object in its cache again, straight from memory and without asking the server for
anything. This is for controllers that manage something outside Kubernetes, such as a
cloud load balancer. If someone changes that load balancer by hand, no Kubernetes event
tells the controller, and a periodic resync gives it a regular chance to notice and fix
the drift.

The work queue waits before retrying a name whose reconcile failed. By default the wait
starts at 5 milliseconds and doubles after each failure, up to 1,000 seconds, and the queue
also limits how fast it hands out names overall. Our model retries at once. A real
controller that did that while its writes kept failing, say because of a bug in how it
builds the object, would flood the API server with requests.

Finally, informers are shared within a process. If ten controllers in one program all
care about pods, they share a single pod watch and a single cache through a
`SharedInformerFactory`, and each registers its own event handlers and its own work queue.
The API server then serves one watch per process instead of one per controller.

## Sharing a cache safely

Our model's cache hands out copies, so a caller can change what it gets without affecting
anyone else. client-go's cache hands out pointers into the shared store instead, to avoid
copying every object on every read. That has a sharp edge. If a client-go controller
changes a field of an object it read from the cache, it is changing the very object every
other controller in the process reads, while the server still holds the original. The
other controllers now see a state that exists nowhere else. The rule is to call the
object's generated `DeepCopy` method, which copies every nested slice and map, and to
change the copy.

## Reading your own writes

A controller's own writes reach its cache the same way everyone else's do: the server
stores the write, emits an event, and the reflector applies it. Until that event arrives,
the cache still shows the state from before the write. Picture a reconcile that creates a
pod for a job. If a second event for the same job arrives before the pod's creation event,
the next reconcile finds no pod in the cache and creates a second one.

Kubernetes controllers guard against this in two ways. The ReplicaSet controller, which
keeps a requested number of identical pods running, records *expectations*: after
creating three pods, it notes that it expects to see three creation events, and it leaves
that ReplicaSet alone until the cache has shown them or a timeout has passed. The second
technique uses two fields that every object carries. The API server increments
`metadata.generation` every time the spec changes, and a controller copies the generation
it acted on into `status.observedGeneration`. When the two numbers are equal, the status
describes the current spec. When they differ, both the controller and any user reading
the object can see that the latest change to the spec has not been handled yet.

## The complete program

The model is six source files in each language, printed here in the order the chapter built
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
