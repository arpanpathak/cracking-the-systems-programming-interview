# 1. Keeping a local copy of the cluster

This chapter depicts what happens under the hood when a Kubernetes controller learns that an
object in the cluster has changed. We will examine how the API server numbers every write, how a
client combines a list and a stream of changes into an exact copy of the cluster, what the client
does when that stream breaks, and how the copy is turned into work. We will build each of these
pieces as a small program in Go and in Rust, starting with the data structures and adding one
operation at a time, and we will finish by running the whole model through a burst of edits, a
dropped connection and a network partition.

## Objects and controllers

Kubernetes represents the state of a cluster as a set of objects, and every change to that state
is a change to an object. We first define the terms precisely and then illustrate them with the GPU
training job that serves as the example throughout this chapter.

<div class="definition">

**Definition 1.1** (Object). An *object* is a record stored by the Kubernetes API server and
identified by its kind and its name. It consists of a *spec*, which describes the desired state of
the entity the object represents, and a *status*, which describes the most recently observed state
of that entity.

</div>

<div class="definition">

**Definition 1.2** (API server). The *API server* is the HTTP service through which every object is
created, read, updated and deleted. It stores the objects in etcd, a replicated key-value store,
and no other component of the cluster accesses etcd directly.

</div>

<div class="definition">

**Definition 1.3** (Controller). A *controller* is a process that, for every object of a given
kind, compares the spec with the observed state of the cluster, acts to remove any difference
between the 2, and records the result in the status.

</div>

The spec and the status have different writers. The spec is written by the owner of the object,
which is a user or another program, and the status is written only by the controller responsible
for the object. Since each part has exactly 1 writer, a controller can always distinguish the state
that was requested from the state it has achieved.

<div class="example">

**Example 1.1** (A GPU training job). Let `job-a` be an object of kind `GpuJob` with
`spec.gpus = 1` and `status.gpus = 0` immediately after its creation. Its controller starts a
container with 1 GPU on a machine that has a free GPU and then sets `status.gpus = 1`, at which
point spec and status agree. If the owner later sets `spec.gpus = 2`, the 2 parts differ again, and
the controller replaces the container and sets `status.gpus = 2`. If the owner deletes `job-a`, the
controller stops the container and releases its GPUs.

</div>

Listing 1.1 defines the object of our model. A Kubernetes object carries many more fields, among
them labels, owner references and a container specification. A GPU count in the spec and in the
status is sufficient for every mechanism in this chapter. The field `ResourceVersion` is defined in
the next section (Definition 1.4).

<div class="code-tabs">

<p class="listing"><b>Listing 1.1</b> An object, with its spec and its status. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">Rust</a></p>

```go
{{#include ../code/go/informer/server.go:types}}
```

```rust
{{#include ../code/rust/informer/src/server.rs:types}}
```

</div>

To do its work, a controller requires 2 things from the API server: the current state of every
object of its kind, and notification of each change to such an object shortly after the change
occurs.

## The cost of asking for everything

The simplest way for a controller to obtain both is to request every object of its kind every few
seconds and to compare the result with the state it has recorded. We can estimate the cost of this approach
for a large cluster. Suppose the cluster runs 50,000 pods and each pod is about 4 KB of JSON. A
single request for all pods then transfers 50,000 × 4 KB = 200 MB. If 12 controllers each repeat
the request every 5 seconds, the API server sends 12 × 200 MB ÷ 5 s = 480 MB every second. Between
2 requests, perhaps 3 pods have changed, so almost all of those bytes describe objects that the
controller already knew about. On our own lab fleet, 5 Jetson AGX Thors, 2 DGX Sparks and a Jetson
Orin NX Super, a few hundred pods fit in well under 1 MB and polling works, and so the
approach is tempting. Its cost grows with the size of the cluster, while the useful information it
returns grows only with the rate of change.

Kubernetes inherited the answer to this problem from its predecessors at Google. Borg kept the
state of a cluster in a central master, and Omega, described in 2013, let many schedulers share 1
copy of that state and settle clashing updates with version checks instead of locks. Kubernetes,
announced in 2014, kept the version checks and added a stream of changes, so that a client reads
the whole state once and then receives only the changes. The rest of this chapter builds that
mechanism one step at a time.

## Numbering every write

A stream of changes needs a way to name a point in the history of the store, so that a client whose
connection breaks can ask for every change after the last one it received. etcd provides such a
name. It keeps 1 counter, called the **revision**, for the whole store, and every create, update and
delete of any key takes the next value of that counter. etcd also keeps the older values of each key
under their old revisions until a clean-up removes them.

Fig. 1.1 shows 12 writes to 4 keys. The top row is the history in the order of the writes, coloured
by the key that each write changed. The rows below form etcd's key index, which lists for each key
the revisions that wrote it. For example, `job-a` was written at revisions 1, 4, 5, 9 and 11, and
`pod-1` at revisions 3 and 8.

<figure>
<img src="figures/ch01-revisions.svg" alt="Twelve writes numbered 1 to 12, coloured by the key they wrote: job-a, job-b, pod-1 and pod-2. Below, the key index lists for each key the revisions that wrote it. job-a was written at 1, 4, 5, 9 and 11, so its resourceVersion is 11.">
<figcaption><b>Figure 1.1</b> One counter numbers every write. An object's resource version is the revision of its latest write, the solid cell in each row.</figcaption>
</figure>

<div class="definition">

**Definition 1.4** (Resource version). The *resource version* of an object is the etcd revision of
the last write that changed the object. The resource version of a list of objects is the revision
of the whole store at the moment the list was read.[^opaque]

</div>

In Fig. 1.1 the resource version of `job-a` is therefore 11, and that of `pod-1` is 8. A client
that holds a list read at resource version *v* knows the state of the cluster exactly as it was
after revision *v*.

[^opaque]: Kubernetes asks clients to treat resource versions as opaque strings and to compare them only for equality. Our model uses plain integers so that we can print them, and nothing in the client depends on their order.

Each change that the API server reports to a client is an **event**. An event has a type, `ADDED`,
`MODIFIED` or `DELETED`, and it carries the whole object as it was after the change, or its last
state for a deletion. Sending the whole object, rather than only the fields that changed, means that
a client can apply an event without knowing anything about the object's earlier state. Listing 1.2
gives the event, together with the 3 errors that the server can return. We will meet `409 Conflict`
in the next section and `410 Gone` when we discuss lost history.

<div class="code-tabs">

<p class="listing"><b>Listing 1.2</b> Events, and the errors the server returns. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">Rust</a></p>

```go
{{#include ../code/go/informer/server.go:events}}
```

```rust
{{#include ../code/rust/informer/src/server.rs:events}}
```

</div>

## Two writers and one object

The resource version also solves a problem that has nothing to do with streams. A client updates
an object by sending the whole object back to the API server. Consider 2 clients that both read
`job-a` at resource version 7. Client A raises the job's GPU count and sends the job back. A moment
later, client B changes the job's container image and sends its copy back as well. Client B's copy
still holds the GPU count it read at version 7, so its write replaces client A's change with the
old value. Neither client receives an error, and the GPU change is simply gone. This failure is
called a **lost update**.

The API server prevents it by letting each write state the resource version it was based on.
Fig. 1.2 traces the same 2 clients under that rule. Both read version 7 at markers ➋ and ➍. At
marker ➎ client A sends its change with "read at version 7"; the object is still at version 7, so at
➏ the server accepts the write and stores it as version 8. At ➐ client B sends its change, also
with "read at version 7". The object is now at version 8, so at ➑ the server refuses the write
with `409 Conflict`. Client B then reads the job again, applies its image change to version 8, and
at ➓ the write succeeds as version 9, which holds both changes.

<figure>
<img src="figures/ch01-conflict.svg" alt="Client A and client B both read job-a at version 7. A writes 2 GPUs with version 7 and the server accepts it as version 8. B writes a new image with version 7 and the server answers 409 Conflict. B reads version 8, writes again with version 8, and the server stores version 9 with both changes.">
<figcaption><b>Figure 1.2</b> A write that names the version it read is accepted only if the object is still at that version.</figcaption>
</figure>

<div class="definition">

**Definition 1.5** (Conditional write). An update that carries a resource version *v* succeeds only
if the stored object still has resource version *v*. Otherwise the API server rejects the update
with the HTTP status `409 Conflict`, and the client must read the object again and reapply its
change.

</div>

This technique is called *optimistic concurrency control*, also known as compare-and-set. No client
holds a lock on the object while it computes its change. Each client proceeds on the assumption that
no other client will write the object in the meantime, and the server detects the cases in which
that assumption was false at the moment the write arrives. The cost of a false assumption is 1
additional read and 1 additional write, which is small when conflicts are rare, as they are for most
Kubernetes objects.

We now have enough to build the server's side of these rules. Fig. 1.3 shows the state that our
model API server keeps after 10 writes. There are 4 fields behind 1 lock. The **objects** map holds
the current version of each object. The **version** counter plays the role of etcd's revision. The
**history** holds recent events in order, and the **watches** are the open streams of changes,
which the next section introduces. A fifth field, **compacted**, records how much of the oldest
history has been discarded.

<figure>
<img src="figures/ch01-server-struct.svg" alt="The API server holds 4 fields behind 1 lock: objects (job-a at version 10, job-b at 8), the version counter 10, a history of events 3 to 10 with 1 and 2 compacted, and 2 open watches that have been sent everything up to 10. Update checks the version, increments the counter, stores the object, and publishes 1 event to the history and every watch. Watch from 8 checks the compaction point, replays 9 and 10, and registers itself under the same lock.">
<figcaption><b>Figure 1.3</b> The model API server after 10 writes. Markers ➊ to ➌ follow an update, and ➍ and ➎ a new watch.</figcaption>
</figure>

Listing 1.3 declares these fields. The field `unreachable` has no counterpart in Kubernetes; our
demonstration sets it to make the server behave as if a network partition had cut it off.

<div class="code-tabs">

<p class="listing"><b>Listing 1.3</b> The state of the API server. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">Rust</a></p>

```go
{{#include ../code/go/informer/server.go:server}}
```

```rust
{{#include ../code/rust/informer/src/server.rs:server}}
```

</div>

The update path follows markers ➊ to ➌ in Fig. 1.3. The server first compares the version that the
caller read with the version it has stored, and returns `409 Conflict` if they differ. It then
increments the counter, stamps the object with the new value, stores it, and publishes 1 event to
the history and to every open watch. In our model a version of 0 means that the caller wants to
write unconditionally, which the demonstration uses to play a user editing a job, and an object
that does not exist yet counts as version 0.

<div class="code-tabs">

<p class="listing"><b>Listing 1.4</b> An update that checks the version it was based on. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">Rust</a></p>

```go
{{#include ../code/go/informer/server.go:update}}
```

```rust
{{#include ../code/rust/informer/src/server.rs:update}}
```

</div>

The check, the increment and the store all happen while the lock is held. If the lock were released
between the check and the store, 2 writers could both pass the check against version 7 before
either stored its result, and the lost update would return. Note that the lock is held only for the
time of a few map operations, so it does not limit the server's throughput in our model; the real
API server delegates the same check to etcd, which performs it as a single transaction.

## A watch that starts late misses writes

With numbered writes, a client can build an exact copy of the cluster in 2 requests. First it
sends a **list**, which returns every object of a kind together with the revision at which the
list was read. Then it opens a **watch**, a long-lived request that returns 1 **event** for each
change after a given revision: `ADDED`, `MODIFIED` or `DELETED`, each carrying the object as it
was after the change.

<div class="callout note">

**Following a chess game from another room.** Suppose we follow a chess game that is played in
another room, and a messenger carries news to us. First we ask for the position of the board, and
the messenger brings a drawing of the board as it stood after move 30. Then we ask to be told every
move from now on. Moves are numbered, and each report says only which piece moved where, so our
board is correct only if we apply every move, in order. If we ask for moves "after move 30", the
messenger also brings move 31, which was played while the drawing was on its way, and our board
stays correct. If we ask for moves "from now", and move 31 has already been played, we never hear
of it, and every later move is applied to a wrong board. The comparison breaks down in 1 place.
Every move of a game is written on the score sheet and can be read back at any time, while the API
server keeps only the last few minutes of changes; a client that asks for changes older than that
must ask for a new drawing, which is the subject of the next section. Mapped back to Kubernetes, the
drawing is the list, "after move 30" is the list's resource version, the reported moves are the
watch events, and asking for moves after 30 is opening the watch from the list's version.

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

Listing 1.5 is the server's side of that promise, markers ➍ and ➎ of Figure 1.3. `Watch` holds
the same lock as `Update` while it replays the history and registers the new watch, so every event
lands either in the replay or on the new channel, never in neither and never in both.

<div class="code-tabs">

<p class="listing"><b>Listing 1.5</b> List, and watch from a version. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">Rust</a></p>

```go
{{#include ../code/go/informer/server.go:listwatch}}
```

```rust
{{#include ../code/rust/informer/src/server.rs:listwatch}}
```

</div>

The real API server does not send every watch to etcd. For each kind of object it keeps a **watch
cache**: the current objects and a window of recent events in memory, fed by 1 etcd watch, and it
serves most watches from there. Since Kubernetes 1.31 it serves consistent lists from that cache
too, after checking that the cache has caught up with etcd's latest revision.

## The server forgets old history

A watch can replay only events the server still has. etcd keeps every revision of every key until
it is told to throw old ones away. That clean-up is called **compaction**, and kube-apiserver asks
for one every 5 minutes by default. When a client asks to resume from a revision older than what is
left, the API server answers `410 Gone`, and the only way back to an exact copy is a fresh list.

Watches also end for ordinary reasons. kube-apiserver closes every watch after a random timeout
between 30 and 60 minutes, so that thousands of clients do not all reconnect at once. A load
balancer may drop a connection that is been quiet too long. A network partition may make the server
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

Once we have listed and are watching, we can keep our own copy of every object in memory. We call it
the **cache**. Reading an object becomes a map lookup, and the API server sends each change to our
process once.

The cache needs 2 operations. *Apply* records 1 event. *Replace* installs a fresh list, and it has a
job that events cannot do. When we relist after `410 Gone`, some objects may have been deleted while
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
3. for each name *n* in *cache* that is not in *list*: append *n* to *changed*
4. *cache* ← the objects of *list*, by name
5. return *changed*

</div>

<div class="code-tabs">

<p class="listing"><b>Listing 1.6</b> Replace. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/cache.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/cache.rs">Rust</a></p>

```go
{{#include ../code/go/informer/cache.go:replace}}
```

```rust
{{#include ../code/rust/informer/src/cache.rs:replace}}
```

</div>

An object that is new to us has no cached version. Go reads the missing map entry as version 0, and
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
update lands at ➎. It sees the old spec of 1 GPU, decides there is nothing to do, and finishes. The
name will not be queued again, so the edit to 2 GPUs waits until the job happens to change once more.
In the right column the cache is updated first, and the worker reads 2 GPUs.

<figure>
<img src="figures/ch01-order.svg" alt="Two orderings of the reflector's steps. Left: the name is queued before the cache is updated, a worker reads the old spec of 1 GPU, finds nothing to do, and the edit to 2 GPUs is never handled. Right: the cache is updated first, so the worker reads 2 GPUs and acts.">
<figcaption><b>Figure 1.7</b> The same event in both columns. Only the order of 2 steps differs.</figcaption>
</figure>

<div class="invariant">

**Invariant 1.2** (Cache before queue). When a worker takes a name from the queue, the cache
already reflects every event that caused the name to be queued.

</div>

Listing 1.7 is step 2 of Algorithm 1.2. Our model retries an unreachable server every 10
milliseconds. client-go doubles the wait after each failure in a row, up to a cap, so that
thousands of clients do not overload a server that is trying to recover.

<div class="code-tabs">

<p class="listing"><b>Listing 1.7</b> Watching from a version, and the 3 endings. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/reflector.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/reflector.rs">Rust</a></p>

```go
{{#include ../code/go/informer/reflector.go:watch}}
```

```rust
{{#include ../code/rust/informer/src/reflector.rs:watch}}
```

</div>

## A burst of edits starts work that is already out of date

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

`Add` puts a name in *dirty*, and in the ready list only if no worker holds it. That is the third
row of Figure 1.8: the name is marked and left out of the ready list.

<div class="code-tabs">

<p class="listing"><b>Listing 1.8</b> Add. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/queue.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/queue.rs">Rust</a></p>

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

<p class="listing"><b>Listing 1.9</b> Get and Done. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/queue.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/queue.rs">Rust</a></p>

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
status. It does not know, or care, why it was called. A name queued once and a name queued 10 times
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

Figure 1.10 lays out 1 reconcile as a decision flow. There is one more trap in it, at marker ➎. Our
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

<p class="listing"><b>Listing 1.10</b> Reconciling 1 name. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/controller.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/controller.rs">Rust</a></p>

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

Here is the Go log read line by line against the sections of this chapter.

| Time | Log | What happened |
|---|---|---|
| 0 ms | list at version 2 | The reflector lists (Algorithm 1.2, step 1.1). Replace reports both jobs, and both names are queued. |
| 20 to 40 ms | 1 reconcile per job | Each status write is itself an event and queues the name again. The next run finds status equal to spec and returns without a log line. |
| 101 ms | 5 edits | The worker took `job-a` after the first edit and read a spec of 2 at version 5. The other 4 edits arrived while it held the name, so the queue only marked it dirty (Figure 1.8). |
| 121 ms | `409 Conflict` at version 5 | The object was at version 9 by then, so the conditional write failed and the name went back in the queue. |
| 141 ms | status 6 | The second run read version 9 and wrote status 6 at version 10. Specs 3, 4 and 5 were never acted on (Figure 1.9). |
| 257 ms | watch closed, resuming from 10 | The stream closed. The cache was exact up to 10, so the reflector watched again from 10 with no list. |
| 307 to 338 ms | `410 Gone`, list at version 11 | During the partition, `job-b` was deleted at 11 and history was compacted to 11, so a watch from 10 could not be served. |
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
anyone can see that the latest spec has not been handled yet.

An informer is not always the right tool. A cache is always a little behind, so a decision that must
see the very latest state, such as granting the last free GPU of a quota, needs a direct read or a
conditional write at the moment of decision. And a controller that cares about a handful of objects
among millions pays for a cache of all of them unless it narrows its watch with a label or field
selector.

## Summary

- The API server numbers every write with etcd's revision, and an object's resource version is the revision of its latest write.
- A write that carries the version it read is refused with `409 Conflict` if the object has moved on, so 2 writers cannot silently undo each other.
- A client lists, then watches from the list's version, and gets every change exactly once (Invariant 1.1).
- A watch resumes from the last version applied after a closed stream or an outage, and lists again only after `410 Gone`.
- Replace finds deletions whose events were compacted away by comparing the old cache with the new list.
- The reflector updates the cache before it queues a name (Invariant 1.2).
- The work queue's *dirty* and *processing* sets merge bursts of edits and keep 1 name with 1 worker (Invariant 1.3).
- A level-triggered reconcile acts on the current state, so lost or repeated events cost it nothing.

The next part of this chapter, *A GPU job controller on a real cluster*, runs the same design
against a real cluster, with client-go in Go and kube-rs in Rust.

## Exercises

1. In Figure 1.1, a client lists at revision 8 and watches from 8. Which revisions does it receive as events, and what is its cached resource version for `job-b` afterwards?
2. In Figure 1.3, a client calls `Watch(from 1)`. What does the server answer, and what must the client do next?
3. Swap the 2 steps of Algorithm 1.2, step 2.3, in the Go model, and add a 30-millisecond sleep between them. Run the demonstration and find the edit that is never reconciled.
4. Remove the *processing* set from the work queue and run the demonstration with 2 workers. How many reconciles of `job-a` overlap during the burst?
5. With client-go's default rate limiter, after how many consecutive failures does 1 name wait longer than 1 minute between attempts?
6. A relist finds an object with the same name, a different resource version and a different UID. What happened on the server, and what should a controller that owns a container for that object do?

## The complete program

The model is 6 source files in each language. Each is folded here, with Go and Rust as tabs.

<details class="program"><summary>The API server: server.go and server.rs</summary>

<div class="code-tabs">

<p class="listing"><b>Listing 1.11</b> The API server, complete. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/server.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/server.rs">Rust</a></p>

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

<p class="listing"><b>Listing 1.12</b> The cache, complete. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/cache.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/cache.rs">Rust</a></p>

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

<p class="listing"><b>Listing 1.13</b> The reflector, complete. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/reflector.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/reflector.rs">Rust</a></p>

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

<p class="listing"><b>Listing 1.14</b> The work queue, complete. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/queue.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/queue.rs">Rust</a></p>

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

<p class="listing"><b>Listing 1.15</b> The controller, complete. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/controller.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/controller.rs">Rust</a></p>

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

<p class="listing"><b>Listing 1.16</b> The demonstration, complete. <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/informer/main.go">Go</a> · <a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/informer/src/main.rs">Rust</a></p>

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
