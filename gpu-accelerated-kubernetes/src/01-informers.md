# 1. Keeping a local copy of the cluster

This chapter depicts what happens under the hood when a Kubernetes controller learns that
something in the cluster has changed. We'll examine how the API server numbers every write,
how a client turns a list and a stream of changes into an exact copy of the cluster, what the
client does when that stream breaks, and how the copy is turned into work without doing the same
work twice. We'll build each piece as a small model in Go and in Rust, run it through a burst of
edits, a dropped connection and a network partition, and then match every piece to client-go,
the library that real Go controllers use.

## A controller, and the simplest way to build one

Our running example is a program that runs GPU training jobs. A user creates a job that asks for
1 GPU, and our program starts a container for it on a machine with a free GPU. When the user
raises the request to 2 GPUs, our program replaces the container. When the user deletes the job,
our program stops the container and frees the GPU. In Kubernetes, a program that watches what
users ask for and acts until the world matches is called a **controller**.

Kubernetes stores what users ask for as **objects**. An object is a named record with 2 main
parts. Its **spec** holds the desired state, such as "run this image with 1 GPU". Its
**status** holds the observed state, such as "running on 1 GPU". Every object lives behind 1 HTTP
service, the **API server**, which keeps them in etcd, a replicated key-value store. Users,
`kubectl` and controllers all read and write objects through the API server, and none of them
talks to etcd directly.

The simplest controller we could write asks the API server for every job every few seconds and
compares each one with what it's running. On a small cluster this works well. Our own lab fleet,
5 Jetson AGX Thors, 2 DGX Sparks and a Jetson Orin NX Super, runs a few hundred pods, and a full
list of them is well under a megabyte.

Now let's scale it up. A large cluster runs 50,000 pods, and each pod is about 4 KB of JSON, so 1
list is 200 MB. If 12 controllers each list every 5 seconds, the API server sends
12 × 200 MB ÷ 5 s = 480 MB every second. Between 2 lists, perhaps 3 pods changed. Almost all of
those bytes describe objects the controller already knew about.

This problem isn't new. Google's Borg ran cluster state through a central master for years, and
its successor research system, Omega, published in 2013, let many schedulers share one copy of the
cluster state and resolve clashes with version checks instead of locks. Kubernetes, announced in
2014, took that idea and added a stream of changes on top of it. The rest of this chapter follows
the problems that the simple polling loop runs into, one per section, and the mechanism that fixes
each one.

## Polling sends 200 MB to learn about 3 changes

What we'd like is for the API server to tell us about each change as it happens. That needs a way
to name a point in the history of the store, so that a client whose connection breaks can say "send
me everything after the last change I saw".

etcd already keeps such a name. It has 1 counter for the whole store, called the **revision**.
Every create, update and delete of any key takes the next value of the counter, and etcd keeps
older values of a key under their old revisions until a clean-up removes them. Figure 1.1 shows 12
writes to 4 keys. The top row is the history in order. The bottom rows are etcd's key index, which
records, for each key, the revisions that wrote it.

<figure>
<img src="figures/ch01-revisions.svg" alt="Twelve writes numbered 1 to 12, coloured by the key they wrote: job-a, job-b, pod-1 and pod-2. Below, the key index lists for each key the revisions that wrote it. job-a was written at 1, 4, 5, 9 and 11, so its resourceVersion is 11.">
<figcaption><b>Figure 1.1</b> One counter numbers every write. An object's resource version is the revision of its latest write, the solid cell in each row.</figcaption>
</figure>

Kubernetes passes the revision through to clients as the **resource version** of an object: the
revision of the last write that changed it. In Figure 1.1, `job-a` was last written at revision 11,
so its resource version is 11, and `pod-1`'s is 8. A list also carries a resource version, the
revision of the whole store at the moment the list was read.[^opaque]

[^opaque]: Kubernetes asks clients to treat resource versions as opaque strings and to compare them only for equality. Our model uses plain integers so that we can print them, and nothing in the client depends on their order.

## Two writers undo each other

The resource version solves a second problem before we even get to streams. A client writes an
object by sending the whole object back. Suppose 2 clients read `job-a` at version 7. Client A
raises the GPU count and writes the job back. A moment later, client B changes the image and
writes the job back too, still holding the copy it read at version 7. Client B's copy has the old
GPU count, so its write quietly undoes client A's change.

The fix is to let a write say which version it was based on. Figure 1.2 traces the same 2 clients
with that rule in place. At marker ➏ the server accepts client A's write, because the object was
still at version 7, and stores it as version 8. At marker ➐ client B also says "I read this at
version 7", but the object is now at version 8, so at ➑ the server refuses with `409 Conflict`.
Client B reads the job again at ➒, reapplies its change, and this time the write succeeds.

<figure>
<img src="figures/ch01-conflict.svg" alt="Client A and client B both read job-a at version 7. A writes 2 GPUs with version 7 and the server accepts it as version 8. B writes a new image with version 7 and the server answers 409 Conflict. B reads version 8, writes again with version 8, and the server stores version 9 with both changes.">
<figcaption><b>Figure 1.2</b> A write that names the version it read is accepted only if the object is still at that version.</figcaption>
</figure>

This is called **optimistic concurrency**, also known as compare-and-set. Nobody holds a lock on
the object. Each client assumes nobody else will write in the meantime, and the server catches the
cases where that assumption was wrong at the one moment it matters: when the write arrives.

Before we write any code, Figure 1.3 shows what our model API server holds. It's 4 fields behind 1
lock: the objects, the revision counter, a history of recent events, and the open watches. The
markers follow 1 update and 1 watch through it, and we'll meet the watch half in the next section.

<figure>
<img src="figures/ch01-server-struct.svg" alt="The API server holds 4 fields behind 1 lock: objects (job-a at version 10, job-b at 8), the version counter 10, a history of events 3 to 10 with 1 and 2 compacted, and 2 open watches that have been sent everything up to 10. Update checks the version, increments the counter, stores the object, and publishes 1 event to the history and every watch. Watch from 8 checks the compaction point, replays 9 and 10, and registers itself under the same lock.">
<figcaption><b>Figure 1.3</b> The model API server after 10 writes.</figcaption>
</figure>

Listing 1.1 is the update path, markers ➊ to ➌. A version of 0 means "write unconditionally",
which our demonstration uses to play a user editing a job, and a missing object counts as version 0.

<div class="code-tabs">

<p class="listing"><b>Listing 1.1</b> A write that checks the version it was based on. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">Rust</a></p>

```go
{{#include ../code/go/informer/server.go:update}}
```

```rust
{{#include ../code/rust/informer/src/server.rs:update}}
```

</div>

The counter increment and the store happen under the same lock as the check. If they didn't, 2
writers could both pass the check against version 7 before either stored its result, and we'd be
back to a lost update.

## A watch that starts late misses writes

With numbered writes, a client can build an exact copy of the cluster in 2 requests. First it
sends a **list**, which returns every object of a kind together with the revision at which the
list was read. Then it opens a **watch**, a long-lived request that returns 1 **event** for each
change after a given revision: `ADDED`, `MODIFIED` or `DELETED`, each carrying the object as it
was after the change.

<div class="callout note">

**A bank statement and a stream of alerts.** Think of how you'd keep track of a bank account
without visiting the branch. You ask for a statement, and the statement ends with "balance after
transaction 10". Then you sign up for text alerts. If you ask for alerts "from transaction 10
onwards", you'll get transaction 11, which happened while you were reading the statement, and
everything after it. If you ask for alerts "from now", you'll miss transaction 11 for good, and
your balance will be wrong until you ask for another statement. The analogy breaks down in one
place: a real bank keeps every transaction forever, while the API server keeps only a few minutes
of recent changes, which is the subject of the next section. Mapping it back: the statement is the
list, "transaction 10" is the list's resource version, the alerts are the watch, and asking for
alerts "from 10" is opening the watch from the list's version.

</div>

The list and the watch are 2 separate requests, and other clients keep writing between them.
Figure 1.4 shows a list read at version 10, an edit at version 11, and a watch that opens when the
store is already at version 12. In the top row the watch asks for changes after 10, so the server
replays 11 and 12 from its history and then carries on with new events. In the bottom row the watch
asks for changes after the current version, 12, and the edits at 11 and 12 are never delivered.

<figure>
<img src="figures/ch01-list-watch-gap.svg" alt="Two rows of versions 8 to 14. In both a list is taken at version 10. In the first row the watch starts from 10, and versions 11 to 14 are delivered. In the second the watch starts from 12, the version current when it opened, and versions 11 and 12 are missed.">
<figcaption><b>Figure 1.4</b> A watch must start from the list's version. Starting from the current version leaves a gap.</figcaption>
</figure>

<div class="invariant">

**Invariant 1.1** (No gap, no duplicate). If a client lists at version *v* and then watches from
*v*, its copy after applying events up to version *u* equals the store at version *u*. The list
covers every write up to *v*, and the watch delivers every write after *v* exactly once.

</div>

Listing 1.2 is the server's side of that promise, markers ➍ and ➎ of Figure 1.3. `Watch` holds
the same lock as `Update` while it replays the history and registers the new watch, so every event
lands either in the replay or on the new channel, never in neither and never in both.

<div class="code-tabs">

<p class="listing"><b>Listing 1.2</b> List, and watch from a version. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">Rust</a></p>

```go
{{#include ../code/go/informer/server.go:listwatch}}
```

```rust
{{#include ../code/rust/informer/src/server.rs:listwatch}}
```

</div>

The real API server doesn't send every watch to etcd. For each kind of object it keeps a **watch
cache**: the current objects and a window of recent events in memory, fed by 1 etcd watch, and it
serves most watches from there. Since Kubernetes 1.31 it serves consistent lists from that cache
too, after checking that the cache has caught up with etcd's latest revision.

## The server forgets old history

A watch can replay only events the server still has. etcd keeps every revision of every key until
it's told to throw old ones away. That clean-up is called **compaction**, and kube-apiserver asks
for one every 5 minutes by default. When a client asks to resume from a revision older than what's
left, the API server answers `410 Gone`, and the only way back to an exact copy is a fresh list.

Watches also end for ordinary reasons. kube-apiserver closes every watch after a random timeout
between 30 and 60 minutes, so that thousands of clients don't all reconnect at once. A load
balancer may drop a connection that's been quiet too long. A network partition may make the server
unreachable for a while. Figure 1.5 shows the 3 endings and what a client does after each. The
variable *v* is the version of the last event the client applied, and since its copy is exact up to
*v*, resuming from *v* is correct in the first 2 cases.

<figure>
<img src="figures/ch01-watch-endings.svg" alt="A watch from version v can end in 3 ways. If the stream closes, the reflector watches again from v. If the server is unreachable, it waits and retries from v, doubling the wait after each failure. If the server answers 410 Gone, v is older than the compaction point and the reflector lists again.">
<figcaption><b>Figure 1.5</b> Only <code>410 Gone</code> costs a full list. The other 2 endings resume from the last version applied.</figcaption>
</figure>

A watch on a kind of object that rarely changes receives few events, so its *v* can fall behind
the next compaction even though nothing was missed. To avoid that needless relist, the API server
sends **bookmark** events, which carry a resource version and no object, and move a quiet watch's
position forward.

## Deletions that no event reports

Once we've listed and are watching, we can keep our own copy of every object in memory. We call it
the **cache**. Reading an object becomes a map lookup, and the API server sends each change to our
process once.

The cache needs 2 operations. *Apply* records 1 event. *Replace* installs a fresh list, and it has a
job that events can't do. When we relist after `410 Gone`, some objects may have been deleted while
we were cut off, and their `DELETED` events went away with the compaction. Nobody will ever send us
those events. The only evidence is that an object is in our old cache and missing from the new list.
Figure 1.6 compares the 2 for 4 objects.

<figure>
<img src="figures/ch01-replace.svg" alt="Four objects compared between the old cache and a new list taken at version 12. job-a went from 9 to 11 and is reported modified. job-b is in the old cache but not in the list and is reported deleted. job-c is new and reported added. job-d is unchanged at 6 and is not queued.">
<figcaption><b>Figure 1.6</b> Replace finds changes by comparing the old cache with the new list. <code>job-b</code>'s deletion has no event left anywhere.</figcaption>
</figure>

<div class="algorithm">

**Algorithm 1.1** Replace(*cache*, *list*) returns the names that changed

1. *changed* ← an empty list
2. for each object *o* in *list*: if *cache* has no entry for *o*.name, or its version differs from *o*.version, append *o*.name to *changed*
3. for each name *n* in *cache* that isn't in *list*: append *n* to *changed*
4. *cache* ← the objects of *list*, by name
5. return *changed*

</div>

<div class="code-tabs">

<p class="listing"><b>Listing 1.3</b> Replace. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/cache.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/cache.rs">Rust</a></p>

```go
{{#include ../code/go/informer/cache.go:replace}}
```

```rust
{{#include ../code/rust/informer/src/cache.rs:replace}}
```

</div>

An object that's new to us has no cached version. Go reads the missing map entry as version 0, and
Rust compares against `None`, so both report it as changed, which is step 2 of Algorithm 1.1.

## A worker reads the cache too early

The loop that keeps the cache in step with the server is called a **reflector**, because it
reflects the server's state into local memory. It lists, installs the list with Replace, watches
from the list's version, and applies each event. It also hands the name of each changed object to
whatever does the work, and the order of those 2 steps matters more than it looks.

<div class="algorithm">

**Algorithm 1.2** Reflector(*server*, *cache*, *queue*)

1. loop:
    1. (*objects*, *v*) ← *server*.List()
    2. add every name that Replace(*cache*, *objects*) returns to *queue*
    3. WatchFrom(*v*); when it returns, go back to step 1.1
2. WatchFrom(*v*):
    1. open a watch from *v*; if the server is unreachable, wait and repeat this step
    2. if the server answers `410 Gone`, return
    3. for each event *e*: Apply(*cache*, *e*), then add *e*.object.name to *queue*, then *v* ← *e*.version
    4. when the stream closes, go to step 2.1 with the same *v*

</div>

Step 2.3 updates the cache before it queues the name. Figure 1.7 shows why. In the left column the
name is queued first, at marker ➋. A worker takes it at ➌ and reads the cache at ➍ before the
update lands at ➎. It sees the old spec of 1 GPU, decides there's nothing to do, and finishes. The
name won't be queued again, so the edit to 2 GPUs waits until the job happens to change once more.
In the right column the cache is updated first, and the worker reads 2 GPUs.

<figure>
<img src="figures/ch01-order.svg" alt="Two orderings of the reflector's steps. Left: the name is queued before the cache is updated, a worker reads the old spec of 1 GPU, finds nothing to do, and the edit to 2 GPUs is never handled. Right: the cache is updated first, so the worker reads 2 GPUs and acts.">
<figcaption><b>Figure 1.7</b> The same event in both columns. Only the order of 2 steps differs.</figcaption>
</figure>

<div class="invariant">

**Invariant 1.2** (Cache before queue). When a worker takes a name from the queue, the cache
already reflects every event that caused the name to be queued.

</div>

Listing 1.4 is step 2 of Algorithm 1.2. Our model retries an unreachable server every 10
milliseconds. client-go doubles the wait after each failure in a row, up to a cap, so that
thousands of clients don't overload a server that's trying to recover.

<div class="code-tabs">

<p class="listing"><b>Listing 1.4</b> Watching from a version, and the 3 endings. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/reflector.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/reflector.rs">Rust</a></p>

```go
{{#include ../code/go/informer/reflector.go:watch}}
```

```rust
{{#include ../code/rust/informer/src/reflector.rs:watch}}
```

</div>

## A burst of edits starts work that's already out of date

The reflector knows when an object changes, and the controller needs to hear about it. The direct
way is to call the controller once for every event. That goes wrong in 2 ways. A user who edits a
job 5 times in 1 second produces 5 events, and a controller called 5 times starts work for 4 specs
that are out of date before the work finishes. And after a relist, Replace reports which names
changed, but the events that led there no longer exist.

So the controller is handed only the *names* of objects that changed, through a **work queue**,
and it reads each object's current state from the cache when it gets to the name. 5 edits put the
same name in the queue 5 times, and if the queue ignores a name it already holds, they collapse
into 1 piece of work on the latest spec. The controller takes names in 1 or more **workers**, each
handling 1 name at a time.

A queue that only dropped duplicates would still let 2 workers handle the same object at once: an
edit that arrives while worker 1 is busy with `job-a` would make the name ready again, and worker 2
would take it. With status writes, one of them fails with a conflict and its work is wasted. With
actions outside Kubernetes, such as starting a container, both succeed, and the job ends up with 2
containers. The client-go work queue avoids this with 2 sets beside the list of ready names. The
**dirty** set holds every name that needs handling. The **processing** set holds every name a
worker has taken and not yet returned. Figure 1.8 follows 1 name through the calls.

<figure>
<img src="figures/ch01-queue-states.svg" alt="The ready list, the dirty set and the processing set after each call: Add puts job-a in ready and dirty; Get moves it to processing; Adds during the reconcile mark it dirty only; Done makes it ready again; a second Get starts a reconcile that reads the latest spec.">
<figcaption><b>Figure 1.8</b> The queue's state after each call. The name is never ready while a worker holds it.</figcaption>
</figure>

<div class="invariant">

**Invariant 1.3** (One worker per name). A name is in *processing* for at most 1 worker, and it
appears in the ready list at most once.

</div>

`Add` puts a name in *dirty*, and in the ready list only if no worker holds it. That's the third
row of Figure 1.8: the name is marked and left out of the ready list.

<div class="code-tabs">

<p class="listing"><b>Listing 1.5</b> Add. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/queue.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/queue.rs">Rust</a></p>

```go
{{#include ../code/go/informer/queue.go:add}}
```

```rust
{{#include ../code/rust/informer/src/queue.rs:add}}
```

</div>

`Get` moves a name from *dirty* to *processing*, and `Done` takes it out of *processing* and makes it
ready again if it was marked dirty in the meantime. A worker that calls `Get` on an empty queue has
to sleep without holding the lock, or `Add` could never get in to add a name. Both versions use a
**condition variable** (`sync.Cond` in Go, `std::sync::Condvar` in Rust), whose wait releases the
lock and sleeps in 1 step. The wait sits in a loop that looks at the list again after waking up,
because another worker may have taken the name first.

<div class="code-tabs">

<p class="listing"><b>Listing 1.6</b> Get and Done. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/queue.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/queue.rs">Rust</a></p>

```go
{{#include ../code/go/informer/queue.go:getdone}}
```

```rust
{{#include ../code/rust/informer/src/queue.rs:getdone}}
```

</div>

Animation 1.1 plays the same calls with the burst of 5 edits from the run at the end of this chapter. Its last
part removes the *processing* set and shows a second worker taking the name while the first is
still busy.

<figure class="anim">
<video class="motion" src="figures/work-queue.mp4" autoplay loop muted playsinline preload="metadata" aria-label="Three boxes, ready, dirty and processing, above a worker. Add puts job-a in ready and dirty. Get moves it to processing and the worker starts a reconcile. Four more Add calls during the reconcile mark the name dirty and leave ready empty. Done moves the name back to ready, and a second reconcile reads a spec of 6 GPUs. In the last part the processing set is removed: an Add during the reconcile makes the name ready, and a second worker takes it while the first is still working." data-chapters="[[0.0, &quot;Add&quot;], [7.86, &quot;Get&quot;], [18.06, &quot;Add while held&quot;], [33.66, &quot;Done&quot;], [46.86, &quot;no processing set&quot;]]"><img src="figures/work-queue.gif" alt="Three boxes, ready, dirty and processing, above a worker. Add puts job-a in ready and dirty. Get moves it to processing and the worker starts a reconcile. Four more Add calls during the reconcile mark the name dirty and leave ready empty. Done moves the name back to ready, and a second reconcile reads a spec of 6 GPUs. In the last part the processing set is removed: an Add during the reconcile makes the name ready, and a second worker takes it while the first is still working."></video>
<figcaption><b>Animation 1.1</b> One name through the work queue. 5 edits lead to 2 runs, and the 2 never overlap.</figcaption>
</figure>

## Events that never arrive

The function a worker runs for each name is called **reconcile**: it reads the object's current
spec, compares it with the world, acts to remove the difference, and records the result in the
status. It doesn't know, or care, why it was called. A name queued once and a name queued 10 times
lead to the same action, and so do a change reported by an event and a change found by a relist.

Engineers call this style **level-triggered**, after circuits that respond to the present level of
a signal. An **edge-triggered** circuit responds to each change of the signal instead, and a
controller built that way does 1 action per event. Figure 1.9 runs both against the same burst of
5 edits. The edge-triggered controller acts 5 times, and 4 of those actions are for specs that were
already replaced. The level-triggered controller acts twice, each time on what the cache holds. If
an event is lost to a compaction, the edge-triggered controller never acts on it, and the
level-triggered one finds the change on its next read.

<figure>
<img src="figures/ch01-edge-level.svg" alt="Five edits of a job's GPU count, to 2, 3, 4, 5 and 6. An edge-triggered handler runs once per edit, 5 times, and 4 of those runs act on specs that were already replaced. A level-triggered reconcile runs twice and each time reads the current spec from the cache, first 2 and then 6.">
<figcaption><b>Figure 1.9</b> 1 action per event, and 1 action per state read.</figcaption>
</figure>

Figure 1.10 lays out 1 reconcile as a decision flow. There's one more trap in it, at marker ➎. Our
cache trails the server by the time an event takes to arrive, and the work at ➍ takes time too. If
the user changes the spec meanwhile and we write our copy of the object back unconditionally, we
store the old spec along with a status computed for it, and the user's edit disappears. So
reconcile writes the status with the version it read, exactly as client B did in Figure 1.2. If the
object has changed, the write fails with `409 Conflict`, the name goes back in the queue, and the
next run reads the newer object.

<figure>
<img src="figures/ch01-reconcile-flow.svg" alt="The reconcile decision flow. Get a name from the work queue, read the object from the cache. If it does not exist, release its GPUs and finish. If its status equals its spec, finish. Otherwise do the work, then write the status with the version that was read. If the write fails with 409 Conflict, add the name to the queue again.">
<figcaption><b>Figure 1.10</b> One reconcile. Every path ends with Done, and only a conflict puts the name back.</figcaption>
</figure>

In our model, a 20-millisecond sleep stands in for the work at marker ➍. A missing object at ➋ was
deleted, and a real controller would release what it had set up for it; our model logs a message.

<div class="code-tabs">

<p class="listing"><b>Listing 1.7</b> Reconciling 1 name. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/controller.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/controller.rs">Rust</a></p>

```go
{{#include ../code/go/informer/controller.go:reconcile}}
```

```rust
{{#include ../code/rust/informer/src/controller.rs:reconcile}}
```

</div>

## Running the model

Figure 1.11 puts the pieces together: the API server numbers every write, the reflector applies
each event to the cache and then queues the name, and a worker takes the name, reads the cache, and
writes the status back with the version it read.

<figure>
<img src="figures/informer-pipeline.svg" alt="The API server numbers every write and stores objects in etcd. Inside the controller's process, the reflector receives events, applies each one to the cache, and then adds the object's name to the work queue. The controller gets a name from the queue, reads the object from the cache, and writes the status back to the API server with the version it read.">
<figcaption><b>Figure 1.11</b> The path of 1 change through the controller's process.</figcaption>
</figure>

The demonstration creates 2 jobs, starts the reflector and 1 worker, and then causes each problem
from this chapter in turn: a burst of 5 edits during a reconcile, a dropped watch, and a partition
during which a job is deleted and the history is compacted. Go runs the reflector and the worker as
goroutines; Rust runs them on threads that share the server, cache and queue through `Arc`. Both
log to standard error with the milliseconds since the start. The Go version prints:

```console
$ go run ./informer
{{#include ../code/output/go-informer.txt}}
```

The Rust version prints the same sequence, with timings that differ by a millisecond or 2 and
field names in Rust's style:

```console
$ cargo run -p informer
{{#include ../code/output/rust-informer.txt}}
```

Here's the Go log read line by line against the sections of this chapter.

| Time | Log | What happened |
|---|---|---|
| 0 ms | list at version 2 | The reflector lists (Algorithm 1.2, step 1.1). Replace reports both jobs, and both names are queued. |
| 20 to 40 ms | 1 reconcile per job | Each status write is itself an event and queues the name again. The next run finds status equal to spec and returns without a log line. |
| 101 ms | 5 edits | The worker took `job-a` after the first edit and read a spec of 2 at version 5. The other 4 edits arrived while it held the name, so the queue only marked it dirty (Figure 1.8). |
| 121 ms | `409 Conflict` at version 5 | The object was at version 9 by then, so the conditional write failed and the name went back in the queue. |
| 141 ms | status 6 | The second run read version 9 and wrote status 6 at version 10. Specs 3, 4 and 5 were never acted on (Figure 1.9). |
| 257 ms | watch closed, resuming from 10 | The stream closed. The cache was exact up to 10, so the reflector watched again from 10 with no list. |
| 307 to 338 ms | `410 Gone`, list at version 11 | During the partition, `job-b` was deleted at 11 and history was compacted to 11, so a watch from 10 couldn't be served. |
| 338 ms | `job-b`: deleted | Replace found `job-b` in the old cache and missing from the list (Figure 1.6). Its `DELETED` event no longer existed anywhere. |

Animation 1.2 replays the run from the list at version 2 to the list at version 11, with the
server's objects on the left and the cache on the right.

<figure class="anim">
<video class="motion" src="figures/list-watch.mp4" autoplay loop muted playsinline preload="metadata" aria-label="The API server on the left with job-a, job-b and its recent events; the reflector's cache on the right. The reflector lists at version 2 and opens a watch. Events 3 to 10 arrive and the cache follows. The watch is closed and reopened from 10 with no list. During a partition job-b is deleted at version 11 and the history is compacted, while the cache still holds job-b. After the partition the server answers a watch from 10 with 410 Gone, the reflector lists at version 11, and job-b, present in the old cache and missing from the list, is removed." data-chapters="[[0.0, &quot;list&quot;], [10.01, &quot;watch&quot;], [34.28, &quot;drop&quot;], [43.69, &quot;partition&quot;], [60.08, &quot;410 Gone&quot;]]"><img src="figures/list-watch.gif" alt="The API server on the left with job-a, job-b and its recent events; the reflector's cache on the right. The reflector lists at version 2 and opens a watch. Events 3 to 10 arrive and the cache follows. The watch is closed and reopened from 10 with no list. During a partition job-b is deleted at version 11 and the history is compacted, while the cache still holds job-b. After the partition the server answers a watch from 10 with 410 Gone, the reflector lists at version 11, and job-b, present in the old cache and missing from the list, is removed."></video>
<figcaption><b>Animation 1.2</b> The run of the model: a list, a watch, a dropped watch that resumes, and a partition that ends in <code>410 Gone</code> and a second list.</figcaption>
</figure>

## What client-go adds

Real Go controllers use client-go, directly or through controller-runtime, which is built on it.
Every part of our model has a counterpart there.

| Our model | client-go |
|---|---|
| `APIServer.List`, `Watch` | `ListerWatcher`, backed by HTTP list and watch requests |
| `Reflector` | `cache.Reflector` |
| `Cache` | `cache.Indexer`, a thread-safe store with secondary indexes, such as all pods on 1 node |
| reflector and cache together | `cache.SharedIndexInformer`, usually just called an **informer** |
| `WorkQueue` | `workqueue`, with the same *dirty* and *processing* sets |
| `reconcile` | a controller's `Reconcile` method |

client-go also has a few mechanisms our model leaves out, and each one fixes a problem we can now
recognise.

**Shared informers.** If 3 controllers in 1 process all care about pods, they share 1 pod watch
and 1 cache through a `SharedInformerFactory`, and each keeps its own handler and work queue, as
Figure 1.12 shows. The API server then serves 1 watch per process instead of 1 per controller.
Because every controller reads the same objects, client-go hands out pointers into the shared
store, so a controller that wants to change an object must call its generated `DeepCopy` method and
change the copy. Otherwise it changes what every other controller in the process sees.

<figure>
<img src="figures/ch01-shared-informer.svg" alt="One API server watch on pods feeds a shared informer holding the reflector, the DeltaFIFO and the indexer. Three controllers in the same process each register a handler and keep their own work queue.">
<figcaption><b>Figure 1.12</b> 1 watch and 1 cache per kind per process, shared by every controller in it.</figcaption>
</figure>

**DeltaFIFO.** Between the reflector and the cache, client-go keeps a queue of pending changes per
object, so the code that updates the cache and notifies handlers takes 1 object at a time with all
its changes. When a relist shows that an object has disappeared, the deletion it reports is wrapped
in `DeletedFinalStateUnknown`, which warns handlers that the object they get is the last state the
cache saw, possibly older than the state at deletion.

**Rate-limited retries.** Our model retries a failed name at once. client-go's default rate
limiter waits 5 ms after the first failure of a name and doubles the wait after each further
failure, up to 1,000 s, and on top of that allows at most 10 retries per second with bursts of
100 across all names. Without such a limit, a controller with a bug that makes every write fail
would send the API server a request for every attempt, as fast as it could.

**Resync.** An informer can be told to queue every name in its cache again every so often, from
memory and without asking the server. This helps controllers that manage something outside
Kubernetes, such as a cloud load balancer, whose drift no Kubernetes event will ever report.

**Smaller caches.** A cache holds every object of its kind, so 50,000 pods at 4 KB each is 200 MB in
every process that watches pods. Controllers that need only names and labels use a metadata-only
informer, and any informer can be given a transform function that drops unneeded fields before an
object enters the cache.

**Reading your own writes.** A controller's own writes reach its cache the same way everyone
else's do, as events. Until the event arrives, the cache shows the state before the write. If a
reconcile creates a pod for a job and a second event for the job arrives before the pod's creation
event, the next reconcile finds no pod and creates another one. The ReplicaSet controller guards
against this with **expectations**: after creating 3 pods it waits to see 3 creation events, or a
timeout, before it looks at that ReplicaSet again. A second guard uses 2 numbers every object
carries. The API server increments `metadata.generation` whenever the spec changes, and the
controller copies the generation it acted on into `status.observedGeneration`. When the 2 differ,
anyone can see that the latest spec hasn't been handled yet.

An informer isn't always the right tool. A cache is always a little behind, so a decision that must
see the very latest state, such as granting the last free GPU of a quota, needs a direct read or a
conditional write at the moment of decision. And a controller that cares about a handful of objects
among millions pays for a cache of all of them unless it narrows its watch with a label or field
selector.

## Summary

- The API server numbers every write with etcd's revision, and an object's resource version is the revision of its latest write.
- A write that carries the version it read is refused with `409 Conflict` if the object has moved on, so 2 writers can't silently undo each other.
- A client lists, then watches from the list's version, and gets every change exactly once (Invariant 1.1).
- A watch resumes from the last version applied after a closed stream or an outage, and lists again only after `410 Gone`.
- Replace finds deletions whose events were compacted away by comparing the old cache with the new list.
- The reflector updates the cache before it queues a name (Invariant 1.2).
- The work queue's *dirty* and *processing* sets merge bursts of edits and keep 1 name with 1 worker (Invariant 1.3).
- A level-triggered reconcile acts on the current state, so lost or repeated events cost it nothing.

The next part of this chapter, *A GPU job controller on a real cluster*, runs the same design
against a real cluster, with client-go in Go and kube-rs in Rust.

## Exercises

1. In Figure 1.1, a client lists at revision 8 and watches from 8. Which revisions does it receive as events, and what's its cached resource version for `job-b` afterwards?
2. In Figure 1.3, a client calls `Watch(from 1)`. What does the server answer, and what must the client do next?
3. Swap the 2 steps of Algorithm 1.2, step 2.3, in the Go model, and add a 30-millisecond sleep between them. Run the demonstration and find the edit that's never reconciled.
4. Remove the *processing* set from the work queue and run the demonstration with 2 workers. How many reconciles of `job-a` overlap during the burst?
5. With client-go's default rate limiter, after how many consecutive failures does 1 name wait longer than 1 minute between attempts?
6. A relist finds an object with the same name, a different resource version and a different UID. What happened on the server, and what should a controller that owns a container for that object do?

## The complete program

The model is 6 source files in each language. Each is folded here, with Go and Rust as tabs.

<details class="program"><summary>The API server: server.go and server.rs</summary>

<div class="code-tabs">

<p class="listing"><b>Listing 1.8</b> The API server, complete. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">Rust</a></p>

```go
{{#include ../code/go/informer/server.go}}
```

```rust
{{#include ../code/rust/informer/src/server.rs}}
```

</div>

</details>

<details class="program"><summary>The cache: cache.go and cache.rs</summary>

<div class="code-tabs">

<p class="listing"><b>Listing 1.9</b> The cache, complete. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/cache.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/cache.rs">Rust</a></p>

```go
{{#include ../code/go/informer/cache.go}}
```

```rust
{{#include ../code/rust/informer/src/cache.rs}}
```

</div>

</details>

<details class="program"><summary>The reflector: reflector.go and reflector.rs</summary>

<div class="code-tabs">

<p class="listing"><b>Listing 1.10</b> The reflector, complete. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/reflector.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/reflector.rs">Rust</a></p>

```go
{{#include ../code/go/informer/reflector.go}}
```

```rust
{{#include ../code/rust/informer/src/reflector.rs}}
```

</div>

</details>

<details class="program"><summary>The work queue: queue.go and queue.rs</summary>

<div class="code-tabs">

<p class="listing"><b>Listing 1.11</b> The work queue, complete. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/queue.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/queue.rs">Rust</a></p>

```go
{{#include ../code/go/informer/queue.go}}
```

```rust
{{#include ../code/rust/informer/src/queue.rs}}
```

</div>

</details>

<details class="program"><summary>The controller: controller.go and controller.rs</summary>

<div class="code-tabs">

<p class="listing"><b>Listing 1.12</b> The controller, complete. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/controller.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/controller.rs">Rust</a></p>

```go
{{#include ../code/go/informer/controller.go}}
```

```rust
{{#include ../code/rust/informer/src/controller.rs}}
```

</div>

</details>

<details class="program"><summary>The demonstration: main.go and main.rs</summary>

<div class="code-tabs">

<p class="listing"><b>Listing 1.13</b> The demonstration, complete. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/main.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/main.rs">Rust</a></p>

```go
{{#include ../code/go/informer/main.go}}
```

```rust
{{#include ../code/rust/informer/src/main.rs}}
```

</div>

</details>

## References

1. Kubernetes documentation, "API Concepts": efficient detection of changes, resource versions, watch bookmarks. <https://kubernetes.io/docs/reference/using-api/api-concepts/>
2. Kubernetes API conventions, "Concurrency Control and Consistency". <https://github.com/kubernetes/community/blob/master/contributors/devel/sig-architecture/api-conventions.md>
3. etcd documentation, "Data model": revisions, the key index, and compaction. <https://etcd.io/docs/latest/learning/data_model/>
4. KEP-2340, "Consistent Reads from Cache", beta in Kubernetes 1.31. <https://github.com/kubernetes/enhancements/issues/2340>
5. client-go source: `tools/cache/reflector.go`, `tools/cache/delta_fifo.go`, `util/workqueue/queue.go`, `util/workqueue/default_rate_limiters.go`. <https://github.com/kubernetes/client-go>
6. M. Schwarzkopf, A. Konwinski, M. Abd-El-Malek and J. Wilkes, "Omega: flexible, scalable schedulers for large compute clusters", EuroSys 2013.
7. B. Burns, B. Grant, D. Oppenheimer, E. Brewer and J. Wilkes, "Borg, Omega, and Kubernetes", *ACM Queue* 14(1), 2016.
8. M. Hausenblas and S. Schimanski, *Programming Kubernetes*, O'Reilly, 2019, chapter 3.
