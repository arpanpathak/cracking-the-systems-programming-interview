# 1.1 A GPU job controller on a real cluster

In chapter 1, we built a server, a cache, a reflector, a work queue, and a controller, and
ran all of them inside one process. In this chapter, we will take that machinery to a real
Kubernetes cluster and write a controller that runs GPU jobs on a real GPU. We will first
teach the API server a new kind of object, the GPU job, and then watch those objects
arrive the way our reflector did. Then we will write the controller, run it, and see a
CUDA program run on a GPU inside a pod that our controller created. Finally we
will make two clients collide on the same object and watch the API server's version check
stop the second one.

This time we will not write the machinery ourselves. We will use each language's standard
Kubernetes library, which provides the same parts we built by hand:

- In Go, we will use *controller-runtime*. It is built on client-go, the library whose
  parts we listed at the end of chapter 1, and it is what Kubebuilder, the usual tool for
  starting a Go controller project, generates code for.
- In Rust, we will use *kube-rs*, published as the `kube` crate.

We will introduce each part of these libraries at the moment we need it, and relate it to
the piece we built in chapter 1.

Our cluster is created with kind, which runs each Kubernetes node as a Docker container.
We talk to it with kubectl, the Kubernetes command-line client:

```console
$ kind get clusters
gpu-lab
$ kubectl get nodes
NAME                    STATUS   ROLES           AGE   VERSION
gpu-lab-control-plane   Ready    control-plane   22s   v1.37.0
```

Pods in this cluster can use a GPU. Appendix A shows how we set that up.

## The projects

Our Go code lives in the module in `code/go`, next to the model from chapter 1:

<p class="listing"><a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/go.mod">code/go/go.mod</a></p>

```text
{{#include ../code/go/go.mod:1:10}}
```

We depend on four modules. `k8s.io/api` holds the Go types of the built-in Kubernetes
objects, such as `Pod`. `k8s.io/apimachinery` holds what all objects share: metadata,
resource quantities such as "2 CPUs", and the errors the API server returns.
`k8s.io/client-go` is the client library, and `sigs.k8s.io/controller-runtime` is the
controller framework built on it. We pick versions that match our cluster's
Kubernetes 1.37.

Our Rust code is the `gpujob` package in the Cargo workspace in `code/rust`, next to the
model's `informer` package:

<p class="listing"><a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/Cargo.toml">code/rust/Cargo.toml</a></p>

```toml
{{#include ../code/rust/Cargo.toml}}
```

<p class="listing"><a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/gpujob/Cargo.toml">code/rust/gpujob/Cargo.toml</a></p>

```toml
{{#include ../code/rust/gpujob/Cargo.toml}}
```

`kube` is the client. We turn on its `runtime` feature for the controller machinery and
its `derive` feature for generating our own object types. `k8s-openapi` provides the
Rust types of the built-in objects; its `v1_36` feature selects the newest Kubernetes
version it supports. The other dependencies do supporting work: `schemars` generates JSON
schemas, `serde` and `serde_json` convert objects to and from JSON, `tokio` runs our
asynchronous code, `futures` gives us operations on streams, `thiserror` derives our
error type, and `tracing` writes the controller's log. Finally, `default-run` lets us
start the controller with a plain `cargo run -p gpujob`.

## Teaching the API server a new kind of object

In chapter 1 our jobs were records with a GPU count. A real cluster has no such kind of
object: it knows about pods, services, deployments, and the other built-in kinds, and
that is all. Fortunately, the API server can be taught new kinds. We describe the new kind
in a *CustomResourceDefinition* (CRD): its API group and version, its name, and the
schema of its fields. Once we install the CRD, the API server stores, validates, lists, and
watches objects of our new kind exactly as it does its built-in kinds. That means
everything from chapter 1 applies to our jobs too: they get resource versions, clients
can list and watch them, and writes can be conditional.

We will call our kind `GpuJob`, in the API group `gpucloud.dev`, version `v1`. Its spec
holds a container image, an optional command, and a GPU count. Its status holds a phase,
a message, and the generation it describes. In both languages, we write the kind as
ordinary types and let a tool generate the CRD from them.

### In Go

A Go API package usually has two files. The first one names the group and version, and it
registers our types in a *scheme*. A scheme is a table that maps Go types to the API kinds
they represent. A client needs it to know that JSON with `"kind": "GpuJob"` should become a
`GpuJob` value, and which URL to use when it sends one to the server.

<p class="listing"><a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/gpujob/api/v1/groupversion.go">code/go/gpujob/api/v1/groupversion.go</a></p>

```go
{{#include ../code/go/gpujob/api/v1/groupversion.go}}
```

The second file defines the types themselves:

<p class="listing"><a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/gpujob/api/v1/types.go">code/go/gpujob/api/v1/types.go</a></p>

```go
{{#include ../code/go/gpujob/api/v1/types.go}}
```

The comments that begin with `+kubebuilder:` are *markers*. They are instructions for
controller-gen, a code generator from the Kubebuilder project, which reads our source code
and writes the CRD for us. Let us go through the ones we use:

- `object:root=true` marks `GpuJob` and `GpuJobList` as complete API objects, as opposed to
  structs that only appear inside other objects.
- `subresource:status` turns on the *status subresource*, which we explain below.
- `resource:shortName=gj` lets us type `kubectl get gj` instead of `kubectl get gpujobs`.
- The two `printcolumn` markers add the GPU count and the phase to the table that
  `kubectl get` prints.
- The `validation` markers become rules in the schema. The API server enforces them, so a
  job with a negative GPU count or an unknown phase is rejected before our controller ever
  sees it.

The ordinary comments on our types and fields matter as well: controller-gen copies them
into the CRD as field descriptions, and `kubectl explain gpujob.spec` shows them to users.

`StatusFromPod` works out a job's status from its pod. The pod's phase maps directly onto
our `Phase`. There is one extra piece of information worth passing on. When the scheduler
cannot find a machine for a pod, it sets the pod's `PodScheduled` condition to `False` and
writes the reason in the condition's message. `StatusFromPod` copies that message into
the job's status, so that a user who runs `kubectl get gpujob` can see why the job is
still waiting.

The `go:generate` line in `groupversion.go` tells Go how to run controller-gen. It writes
two files for us. The first is `zz_generated.deepcopy.go`, with a `DeepCopy` method for
each type. Every Kubernetes API type needs these, because the shared caches described at the end
of chapter 1 hand out pointers, and a controller must copy an object
before changing it. The second file is the CRD itself, in `gpujob/config/crd`. Both
generated files are checked into the repository, so we only need to run the generator again
when we change the types:

```console
$ go install sigs.k8s.io/controller-tools/cmd/controller-gen@v0.22.0
$ go generate ./gpujob/api/...
$ kubectl apply -f gpujob/config/crd/
customresourcedefinition.apiextensions.k8s.io/gpujobs.gpucloud.dev configured
```

### In Rust

In Rust, there is no separate generator to run. kube-rs builds the CRD while our program
compiles, from derive macros on our types:

<p class="listing"><a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/gpujob/src/lib.rs">code/rust/gpujob/src/lib.rs</a></p>

```rust
{{#include ../code/rust/gpujob/src/lib.rs}}
```

The `CustomResource` derive generates a `GpuJob` type for us. It holds our spec together
with the object's metadata and an optional status, the same shape as the Go struct we
wrote by hand. The `#[kube(...)]` attribute does the job of the Go markers. `group` and
`version` place the kind at `gpucloud.dev/v1`. `namespaced` makes each job belong to a
*namespace*, a named partition of the cluster's objects, so that two teams can each have a
job called `train`. `status` turns on the status subresource, and `shortname` and
`printcolumn` do the same as their Go counterparts. The `///` comments become the field
descriptions, and our `Phase` enum becomes a string field whose allowed values are the
variant names.

One attribute deserves a closer look. The schema that kube-rs generates for a `u32` has
the format `uint32`, which the API server does not recognise, and it complains with a
warning every time the CRD is applied. The attribute `#[schemars(with = "i32", range(min =
0))]` publishes the field as a non-negative 32-bit integer instead, which is exactly the
schema the Go field of type `int32` with its `Minimum=0` marker produces, while the Rust
field itself stays unsigned. `from_pod` is the Rust version of `StatusFromPod`.

A tiny program prints the CRD, and we pipe it straight into kubectl:

<p class="listing"><a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/gpujob/src/bin/crdgen.rs">code/rust/gpujob/src/bin/crdgen.rs</a></p>

```rust
{{#include ../code/rust/gpujob/src/bin/crdgen.rs}}
```

```console
$ cargo run -p gpujob --bin crdgen | kubectl apply -f -
customresourcedefinition.apiextensions.k8s.io/gpujobs.gpucloud.dev created
```

Our Go and Rust definitions describe the same kind with the same fields. We can install
either one, and either controller can then serve the jobs.

### The status subresource

Why did we turn on the status subresource? Think about two writers touching the same job:
a user who edits the spec, and our controller, which writes the status. Without the
subresource, both write the whole object, and whoever writes second can overwrite the
other's part with an older copy. With the subresource, the status gets its own endpoint,
`/status`. The API server takes only status fields from writes to `/status`, and only spec
fields from writes to the main endpoint, so the user and the controller can no longer step
on each other.

The subresource has a second effect. The API server now increments `metadata.generation`
only when the spec changes. That gives our status field `observedGeneration` its meaning:
our controller copies the generation it acted on into it, and anyone comparing the two
numbers can tell whether the latest spec change has been handled yet.

## Watching the jobs

In chapter 1, our reflector listed the objects, watched from the list's version, and
listed again when the history ran out. Both libraries give us that loop ready-made. To see
exactly what it delivers, we will write a small program in each language that prints every
event it receives.

In Go, the loop comes packaged inside an *informer*, just like in client-go:
controller-runtime's `cache` package creates one informer per kind of object. To hear
about changes, we register an *event handler*: a set of three functions that the informer
calls whenever it adds, updates, or deletes an object in its cache. Our handlers simply
print what they receive:

<p class="listing"><a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/gpujob/cmd/watch-jobs/main.go">code/go/gpujob/cmd/watch-jobs/main.go</a></p>

```go
{{#include ../code/go/gpujob/cmd/watch-jobs/main.go}}
```

The add handler gets an extra flag, `isInInitialList`, which is true for objects that came
from the first list, so we can tell the objects that already existed from the ones created
later. The handler's registration has a `HasSynced` method that becomes true once our
handler has seen the whole initial list, and `WaitForCacheSync` waits for that moment
before we print "list complete". The delete handler may receive a
`DeletedFinalStateUnknown` value instead of a job. That is the marker from chapter 1 for a
deletion that the informer only discovered by relisting, and `describe` unwraps it.

In Rust, kube-rs hands us the loop directly as a *stream*: a sequence of values that
arrive over time, which we read one at a time with `await`. It is the asynchronous
counterpart of an iterator. The function `watcher` returns a stream of `Event` values for one
kind of object:

<p class="listing"><a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/gpujob/src/bin/watch_jobs.rs">code/rust/gpujob/src/bin/watch_jobs.rs</a></p>

```rust
{{#include ../code/rust/gpujob/src/bin/watch_jobs.rs}}
```

The `Event` enum spells out the list-then-watch sequence we reasoned about in chapter 1.
`Init`, then one `InitApply` for each object that existed at the time of the list, then
`InitDone`, together make up a list. After that, each event is an `Apply` for an object
that was created or changed, or a `Delete`. If the watch has to start over, for example
after `410 Gone`, the stream begins a new `Init` sequence by itself. A consumer that
rebuilds its state at every `Init` therefore gets the same result as the `Replace` method
of our chapter 1 cache. kube-rs provides exactly such a consumer and calls it a
*reflector*: it applies the events to a store that the rest of the program can read.

We started each program before any jobs existed and left it running while we did
everything else in this chapter. The Go program printed:

```console
$ go run ./gpujob/cmd/watch-jobs
list started
list complete, watching
  changed  smoke-test gpus=0 v41900
  changed  train gpus=1 v41901
  changed  smoke-test gpus=0 v41904
  changed  train gpus=1 v41909
  changed  smoke-test gpus=0 v41920
  changed  train gpus=1 v41923
  changed  train gpus=1 v41931
  changed  smoke-test gpus=0 v41960
  changed  train gpus=2 v41972
  changed  train gpus=2 v41977
  changed  train gpus=2 v41979
  deleted  smoke-test gpus=0 v41992
```

And the Rust program printed:

```console
$ cargo run -p gpujob --bin watch_jobs
list started
list complete, watching
  changed  smoke-test gpus=0 v656
  changed  train gpus=1 v657
  changed  train gpus=1 v661
  changed  smoke-test gpus=0 v662
  changed  train gpus=1 v676
  changed  smoke-test gpus=0 v684
  changed  train gpus=1 v688
  changed  smoke-test gpus=0 v722
  changed  train gpus=2 v731
  changed  train gpus=2 v737
  changed  train gpus=2 v739
  deleted  smoke-test gpus=0 v752
```

When we started them again later, with `train` still in the cluster, each one listed the
job before it started watching. In Go:

```console
$ go run ./gpujob/cmd/watch-jobs
list started
  listed   train gpus=2 v41979
list complete, watching
```

In Rust:

```console
$ cargo run -p gpujob --bin watch_jobs
list started
  listed   train gpus=2 v739
list complete, watching
```

The resource versions are etcd's revision numbers. Since etcd counts every write in the
cluster, including those made by Kubernetes' own components, the numbers of one job
jump by more than one between its changes. The Go run happened later in the cluster's
life, so its numbers are larger. Most of the `changed` lines are our controller writing a
new status: the object changes, even though its spec stays the same.

## The controller

Now we can write the controller. It will run each `GpuJob` as a pod and report the
pod's progress in the job's status. Both versions follow the same plan, so we show both
listings first and then walk through them together.

In Go:

<p class="listing"><a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/gpujob/cmd/controller/main.go">code/go/gpujob/cmd/controller/main.go</a></p>

```go
{{#include ../code/go/gpujob/cmd/controller/main.go}}
```

In Rust:

<p class="listing"><a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/gpujob/src/bin/controller.rs">code/rust/gpujob/src/bin/controller.rs</a></p>

```rust
{{#include ../code/rust/gpujob/src/bin/controller.rs}}
```

### The pod for a job

`desiredPod` (`desired_pod` in Rust) builds the pod that a job should have. The
interesting part is how the pod asks for a GPU. It puts `nvidia.com/gpu` in its resource
limits, just as it would put CPU or memory there. Kubernetes calls a resource like this an
*extended resource*: a name that Kubernetes itself does not understand, but whose
quantity a machine can advertise as a whole number, and which the scheduler counts like
any other resource. The name `nvidia.com/gpu` is advertised by the NVIDIA device plugin, a
small program on each GPU machine that counts the GPUs and reports them to Kubernetes;
Appendix A shows it at work. Extended resources can only be requested in whole units, and
they are requested through `limits`. One unit of `nvidia.com/gpu` is, by default, one whole
physical GPU; chapter 2 examines what that includes and how a GPU can be divided.

The pod also carries an *owner reference*, a note in its metadata that says "this pod
belongs to that job". It has two uses. When the job is deleted, Kubernetes' garbage
collector, a controller built into every cluster, sees the note and deletes the pod as
well, so we never have to clean up after deleted jobs ourselves. And because the note has
its `controller` flag set, both libraries can take any event about the pod and work out
which job it belongs to, which is how our controller hears about its pods.

The two languages build the pod differently. The Go version builds an *apply
configuration*, a type from client-go in which every field is optional and is filled in
through `With` methods. The value ends up containing exactly the fields our controller
cares about and nothing else, which matters for the kind of write we are about to do. The
Rust version builds an ordinary `Pod` value and leaves everything else at its default;
serde leaves the empty fields out when it turns the pod into JSON, which has the same
effect.

`podGPUs` (`pod_gpus` in Rust) reads the GPU count back out of an existing pod. In Go it
returns the count and a flag saying whether the pod had a GPU limit at all. In Rust it
returns an `Option<u32>`, and each `?` bails out with `None` as soon as any field along the
way is missing.

### Reconciling a job

Our reconcile function receives a job and brings the cluster into line with it in three
steps.

The first step covers a change that cannot be made in place. Kubernetes fixes a pod's
resources when the pod is created, so if the user changes the job's GPU count, we cannot
simply edit the pod. Instead we delete the pod and ask to be called again in two seconds,
by which time it should be gone. The Go version asks for that with
`ctrl.Result{RequeueAfter: 2 * time.Second}`, and the Rust version with `Action::requeue`.
The Rust condition uses a *let chain*, `if let ... && ...`, available since the 2024
edition, to check for the pod and compare its GPU count in one expression.

The second step creates or updates the pod with a single call, using *server-side apply*.
We send the pod we want, and the API server merges it into whatever it has stored. The
server also records which fields each writer set; a writer in this sense is called a
*field manager*, and our controller calls itself `gpujob-controller`. Applying the same
object twice changes nothing, which makes server-side apply a natural fit for a
level-triggered controller: we can apply on every single reconcile, without first
checking whether the pod exists. We also force ownership, with `client.ForceOwnership` in
Go and `force()` in Rust. If some other writer has set a field that we also set, we take
that field over, which is what we want from a controller that is the only authority over
its pods.

The third step works out the job's status and writes it through the status subresource,
but only if it differs from the status already stored. Skipping unchanged writes is more
than a saving. Every write produces a watch event, every event causes a reconcile, and a
controller that wrote on every reconcile would keep waking itself up forever. The Go
version writes the status with a *merge patch*, which sends only the fields that differ
from a copy of the job we saved before changing it. The Rust version applies the status
with server-side apply, just as it does the pod.

The two versions also read the pod differently, and the difference is worth
understanding. controller-runtime's client reads from the informer caches that the
manager keeps, so the Go `Get` of the pod is a lookup in memory, exactly like the cache
reads in chapter 1. A pod we have only just created is not in the cache yet; in that case
the Go version computes the status from an empty pod, which comes out as Pending, and the
pod's creation event soon triggers another reconcile that reports the real state.
kube-rs's `Api`, on the other hand, talks to the API server directly, so the Rust
`get_opt` is a real GET request. That is fine for our small controller. A Rust controller
that looks after thousands of pods would keep a reflector store of pods in its `Context`
and read them from memory, just as the Go version does.

When a reconcile fails, the Go version returns the error, and controller-runtime puts the
job back in the queue with the growing delay we described at the end of chapter 1. The
Rust version returns the error to kube-rs, which asks our `error_policy` function what to
do; ours logs the error and tries again in five seconds.

### Starting the controller

In Go, everything a controller process shares lives in a *manager*: the connection to the
cluster, the scheme, the informer caches, and the client that reads from them.
`ctrl.NewControllerManagedBy(mgr)` builds our controller inside the manager, and each
call in the chain wires up one piece. `For(&GpuJob{})` watches jobs and queues the name of
each job that changes. `Owns(&corev1.Pod{})` watches pods and queues the name of each pod's
owning job, using the owner reference we set. `Complete` registers our reconciler. Then
`mgr.Start` starts the caches, waits for their first lists, and runs the workers until the
process receives a signal such as Ctrl-C. We switch off the metrics endpoint that a
manager starts by default, since we do not need it here.

In Rust, `Controller::new` starts a watcher and a store for `GpuJob` objects, and `owns`
adds a second watcher, for pods, that queues each pod's owning job in the same way.
`run` starts the work queue and the workers and gives us back a stream with one item per
finished reconcile, and `for_each` keeps reading that stream until the program stops.
`shutdown_on_signal` ends the stream when we press Ctrl-C.

In both libraries, the work queue behaves exactly like the one we built in chapter 1: a
job waits in it at most once, and a job that one worker is reconciling is held back from
all the others until that worker is done.

## Running it

We will test the controller with two jobs. `smoke-test` asks for no GPUs and runs a short
shell command, which tells us the basic machinery works. `train` asks for one GPU and runs
`gpu-check`, a small CUDA program from Appendix A that adds two vectors on the GPU and
prints which device it used.

<p class="listing"><a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/manifests/gpujobs.yaml">code/manifests/gpujobs.yaml</a></p>

```yaml
{{#include ../code/manifests/gpujobs.yaml}}
```

We start the Go controller from `code/go`, create the jobs, and check on them:

```console
$ go run ./gpujob/cmd/controller
$ kubectl apply -f ../manifests/gpujobs.yaml
$ kubectl get gpujobs
NAME         GPUS   PHASE
smoke-test   0      Succeeded
train        1      Succeeded
$ kubectl logs train
device: Orin, compute 8.7, 8 SMs
kernel: no error, out[0] = 3.0, out[n-1] = 3.0
```

The log of `train` shows our CUDA kernel running on the cluster's GPU,
inside the pod our controller created. After its startup messages, the Go controller
logged the following lines, shown here with the date and time zone trimmed from the
timestamps:

```console
15:12:37  INFO  controller  status changed  {"name": "smoke-test", "phase": "Pending", "message": ""}
15:12:37  INFO  controller  status changed  {"name": "train", "phase": "Pending", "message": ""}
15:12:38  INFO  controller  status changed  {"name": "smoke-test", "phase": "Running", "message": ""}
15:12:38  INFO  controller  status changed  {"name": "train", "phase": "Running", "message": ""}
15:12:40  INFO  controller  status changed  {"name": "train", "phase": "Succeeded", "message": ""}
15:13:00  INFO  controller  status changed  {"name": "smoke-test", "phase": "Succeeded", "message": ""}
```

The Rust controller runs from `code/rust`, and the same steps give the same result:

```console
$ cargo run -p gpujob
$ kubectl apply -f ../manifests/gpujobs.yaml
$ kubectl get gpujobs
NAME         GPUS   PHASE
smoke-test   0      Succeeded
train        1      Succeeded
```

```console
14:01:15.949  INFO status changed name=train phase=Pending
14:01:15.954  INFO status changed name=smoke-test phase=Pending
14:01:15.985  INFO status changed name=smoke-test phase=Pending
14:01:17.124  INFO status changed name=train phase=Running
14:01:18.504  INFO status changed name=smoke-test phase=Running
14:01:18.959  INFO status changed name=train phase=Succeeded
14:01:39.957  INFO status changed name=smoke-test phase=Succeeded
```

In both runs, each job moved from Pending to Running to Succeeded along with its pod, and
every step reached our controller through the pod watch that `Owns` or `owns` set up.
`train` finished about two seconds after its pod was created, and `smoke-test` finished
after its twenty-second sleep.

Look at the Rust log once more: `smoke-test` reported Pending twice, 31 milliseconds
apart. Here is what happened. The first reconcile wrote the status. The pod's creation
then triggered a second reconcile before our own status write had come back through the
watch, so the job in the cache still had no status, the comparison saw a difference, and
the controller wrote the same status again. This is the read-your-own-writes gap from the
end of chapter 1. Here it costs one redundant write, which server-side
apply turns into a no-op.

## Two writers, one object

Our controllers never send a resource version when they write, because server-side apply
does not need one. Many clients do, though: a client that reads an object, changes it, and
sends the whole object back with an update includes the version it read, and the API
server applies the same check as our `Update` in chapter 1. To see that check on a real
server, we will write a program in which two clients read the `train` job and then both
try to write it back.

In Go:

<p class="listing"><a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/go/gpujob/cmd/conflict/main.go">code/go/gpujob/cmd/conflict/main.go</a></p>

```go
{{#include ../code/go/gpujob/cmd/conflict/main.go}}
```

In Rust:

<p class="listing"><a href="https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/gpu-accelerated-kubernetes/code/rust/gpujob/src/bin/conflict.rs">code/rust/gpujob/src/bin/conflict.rs</a></p>

```rust
{{#include ../code/rust/gpujob/src/bin/conflict.rs}}
```

The Go version recognises the conflict with `errors.As`, which digs the API server's
status out of the returned error, and compares its code with `http.StatusConflict`. The
Rust version matches the error against a pattern with a guard, `if status.code == 409`,
and every other outcome falls through to the second arm.

```console
$ go run ./gpujob/cmd/conflict
both clients read train at v41931
first write stored, now v41972
second write refused: 409 Operation cannot be fulfilled on gpujobs.gpucloud.dev "train":
the object has been modified; please apply your changes to the latest version and try again
```

```console
$ cargo run -p gpujob --bin conflict
both clients read train at v688
first write stored, now v731
second write refused: 409 Operation cannot be fulfilled on gpujobs.gpucloud.dev "train":
the object has been modified; please apply your changes to the latest version and try again
```

The first write raised `train` to two GPUs, and our controllers noticed. The Go
controller logged:

```console
15:13:07  INFO  controller  GPU count changed, replacing pod  {"name": "train"}
15:13:07  INFO  controller  status changed  {"name": "train", "phase": "Pending", "message": ""}
15:13:07  INFO  controller  status changed  {"name": "train", "phase": "Pending", "message":
          "0/1 nodes are available: 1 Insufficient nvidia.com/gpu. preemption: 0/1 nodes are
          available: 1 Preemption is not helpful for scheduling."}
```

And the Rust controller:

```console
14:01:46.101  INFO GPU count changed, replacing pod name=train
14:01:46.137  INFO status changed name=train phase=Pending
14:01:46.170  INFO status changed name=train phase=Pending 0/1 nodes are available:
                   1 Insufficient nvidia.com/gpu. preemption: 0/1 nodes are available:
                   1 Preemption is not helpful for scheduling.
```

Each controller deleted the old pod, because a pod's resources cannot change, and the
deletion event triggered the reconcile that created the replacement. The replacement asks
for two GPUs on a machine that has only one, so the scheduler cannot place it anywhere.
Thanks to the message we copy from the pod's `PodScheduled` condition, the job's status
tells the user exactly why, and `kubectl get gpujobs` shows the job as Pending until its
request is lowered or a machine with two free GPUs joins the cluster.
