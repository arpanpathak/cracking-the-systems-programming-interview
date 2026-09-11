# 03: Kubernetes Concepts, Deep Dive

A request enters through the API server, is placed by the scheduler, and becomes a
running container through the kubelet. This chapter follows that path, then covers
the extension points, device plugins, and Dynamic Resource Allocation that GPU
workloads depend on.

Operator material is in `docs/04-kubernetes-operator.md` and
`docs/10-gpu-operator-kubebuilder-deep-dive.md`. Overlapping ground is linked
rather than repeated.

> **Version note.** Current stable is Kubernetes **v1.37** (released 2026-08-26).
> Feature states below are quoted with the version in which they changed. The
> upstream documentation's `main` branch is one release ahead of stable, so the
> Workload/PodGroup scheduling APIs described in §8.7 are beta features that a
> given cluster may not have enabled.

---

## 1. Cluster architecture and the API server request path

### 1.1 The components and what each one owns

Kubernetes is a set of cooperating control loops around one durable API. The
components divide as follows:

| Component | Owns | Talks to |
|---|---|---|
| `kube-apiserver` | The only component that reads/writes etcd; serves the REST API | etcd, all clients |
| `etcd` | Durable cluster state (the source of truth) | API server only |
| `kube-scheduler` | The binding decision: which node runs an unscheduled Pod | API server |
| `kube-controller-manager` | Built-in controllers (Deployment, ReplicaSet, Job, Node lifecycle, EndpointSlice, GC, …) | API server |
| `cloud-controller-manager` | Cloud-specific controllers: LBs, routes, node lifecycle | API server, cloud APIs |
| `kubelet` | Pods on one node: sandbox, containers, volumes, probes, status | API server, CRI, CSI, device plugins |
| `kube-proxy` (optional) | Service forwarding rules on a node | API server (via local watch) |
| Container runtime (containerd/CRI-O) | Runs containers | kubelet over CRI |

Add-ons such as CoreDNS, a CNI plugin, the device plugin, and the GPU
Operator are ordinary workloads installed into `kube-system` or their own
namespace.

Two design consequences follow:

1. **Everything is an API object.** A controller does not reach into a node and
   flip a switch; it writes an object and another controller reacts. The GPU
   Operator does not load `nvidia.ko` itself, it creates a driver DaemonSet.
2. **The system is level-triggered.** Controllers compare desired state (spec) to
   observed state and act until they match. They do not depend on seeing every
   event, which is why a restarted controller re-reads the world and converges.

### 1.2 A write request, end to end

Every mutation, `kubectl apply`, a controller updating status, a kubelet posting
node status, traverses the same pipeline in the API server:

```text
client (kubectl / controller / kubelet)
  │  HTTPS: JSON, or protobuf for performance
  ▼
TLS termination + authentication        (identity of the caller)
  ▼
authorization (RBAC / node / webhook)   (whether the verb is permitted here)
  ▼
mutating admission                      (built-ins + MutatingAdmissionWebhooks)
  ▼
schema validation / defaulting          (types, required fields, defaults)
  ▼
validating admission                    (built-ins + ValidatingAdmissionWebhooks)
  ▼
conversion to the storage version
  ▼
persist to etcd (with optimistic concurrency)
  ▼
watch event fan-out to all watchers
```

The order matters. Mutating admission runs **before** validation, because
mutation is where defaults and sidecars get injected, and an object that is later
rejected never reaches etcd. A mutating webhook that rewrote a field after
validation would let objects bypass it, which is why the order is fixed. Webhooks
can be scoped by match conditions (GA in v1.30) and run under a failure policy:
`Fail` (default) blocks the write if the webhook is unreachable, `Ignore` lets it
through. A webhook with `Fail` and a short timeout is a common cause of
cluster-wide outages.

The API server is also the **only** writer to etcd. Clients never talk to etcd
directly, which is what makes authorization, admission, and audit enforceable in
one place.

### 1.3 Authentication

The API server authenticates with, among others:

- X.509 client certificates (kubelet, `admin.conf`, controller-manager),
- bearer tokens / static token files,
- OpenID Connect (human users, groups),
- webhook token review,
- ServiceAccount tokens.

Inside the cluster, a Pod gets a ServiceAccount. Since v1.24 the kubelet projects a
**short-lived, rotating, audience-bound token** via the `TokenRequest` API into a
projected volume rather than using a static Secret. The token's audience and
expiry are part of the volume spec, and the kubelet refreshes it before
expiration. That is why long-running Pods do not hold credentials valid for years,
and why `automountServiceAccountToken: false` is a real hardening step for Pods
that never call the API.

The Node authorizer restricts a kubelet to objects related to its own node, and the
`NodeRestriction` admission plugin stops a compromised kubelet from modifying other
nodes or relabeling itself.

### 1.4 Authorization

RBAC is the default model: `Role`/`RoleBinding` are namespaced,
`ClusterRole`/`ClusterRoleBinding` are cluster-scoped, and a `RoleBinding` may
reference a `ClusterRole` to grant those permissions inside one namespace. Verbs
are `get`, `list`, `watch`, `create`, `update`, `patch`, `delete`,
`deletecollection`. Common traps:

- `list`/`watch` are separate from `get`; a controller that can `get` but not
  `list` will fail to populate its informer cache.
- RBAC is purely additive, there are no deny rules. Restricting access means not
  granting it, or using admission/authorization webhooks.
- `system:masters` bypasses RBAC entirely, so it should not be granted.

Operators should follow least privilege. Kubebuilder generates RBAC from markers:

```go
// +kubebuilder:rbac:groups=apps,resources=deployments,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=apps,resources=deployments/status,verbs=get;update;patch
```

### 1.5 Admission in practice

Admission enforces policy:

- **Built-ins:** `NamespaceLifecycle`, `LimitRanger` (applies LimitRange defaults
  and caps), `ResourceQuota`, `ServiceAccount`, `NodeRestriction`,
  `TaintNodesByCondition`, `Priority`, `StorageObjectInUseProtection`, and Pod
  Security Admission (`baseline`/`restricted`).
- **Mutating webhooks:** add defaults, sidecar containers, labels, and
  annotations. They have side effects, so they must be idempotent and fast.
- **Validating webhooks:** reject invalid domain objects. Prefer CRD `x-kubernetes-validations`
  (CEL) or `ValidatingAdmissionPolicy` for rule-like checks, so that a webhook is
  not required for a few field comparisons.

For a CRD, structural-schema validation plus CEL expressions cover most cases.
Custom webhooks are for cross-object or cluster-context checks that CEL cannot
express. A validating webhook sees the object **after** mutation, so a default it
depends on is already present.

### 1.6 etcd and watch

etcd is a Raft-replicated key-value store. Writes are serialized through a leader
and committed once a quorum (majority of members) acknowledges them. Practical
consequences:

- Three members tolerate one failure; five tolerate two. Adding a third member to
  a two-member cluster is not "one more failure", it restores quorum.
- etcd is latency-sensitive. It needs fast local disks (SSD), and fsync latency
  directly limits API server write throughput. A slow etcd shows up as slow
  `kubectl apply`, slow controller convergence, and leader election churn.
- The data directory grows with revisions; compaction and defragmentation are
  operational tasks that have to be scheduled.
- At-rest encryption is configured on the API server (now with KMS v2 as the
  recommended provider). Encrypting Secrets at rest protects the etcd disk, not
  the API; RBAC still governs who can read them.

The API server keeps a **watch cache** (an in-memory, per-resource cache built on
etcd watches) so that a `list` does not have to read etcd every time and a `watch`
can stream changes from a recent `resourceVersion`. `resourceVersion` is an opaque
etcd revision marker, not a timestamp or a counter to be used in arithmetic.
Rules:

- On `update`, send the `resourceVersion` that was read. If another writer wrote
  first, the write fails with **409 Conflict**. This is optimistic concurrency, and
  a retry that does not re-read clobbers fields.
- A `watch` started from a `resourceVersion` older than the cache retention gets
  **410 Gone**; clients must re-list and then watch from the new `resourceVersion`.
  client-go's Reflector does this.
- List pagination uses `limit`/`continue`; watches can request bookmarks so
  clients can advance their stored version without receiving an object per event.

### 1.7 API Priority and Fairness

`APIPriorityAndFairness` (APF, stable v1.29) is a second gate behind admission and
authorization. It classifies each request through a `FlowSchema` into a
`PriorityLevelConfiguration`, and isolates concurrency per level. This prevents a
runaway controller or a misbehaving client from starving the API. The default
configuration includes distinct levels for leader election, node requests,
built-in controllers, and the catch-all. If an operator starts hammering the API
server with unbounded list/watch loops, APF will throttle it, and the symptom is
`429` responses plus increasing request latency, not an immediate crash.

### 1.8 Extending the API

Two extension mechanisms exist:

- **Custom resources (CRDs):** a new resource type is declared, the API server
  serves it, and a controller is written against it. This is what operators use.
- **Aggregation layer:** a separate API server is registered behind the main one,
  which owns the storage and the behavior (used by metrics-server,
  `custom.metrics.k8s.io`, and similar).

API versioning is at the *resource* level, not the field level: the API server
converts between served versions and one storage version, so the same object can
be read at `v1beta1` or `v1` during a migration window. Beta APIs may change;
GA APIs (`v1`) carry a compatibility commitment, and the API version of a custom
resource carries that commitment with it.

---

## 2. Objects, metadata, and the API contract

### 2.1 The shape of every object

Every Kubernetes object has `apiVersion`, `kind`, `metadata`, and (almost always)
`spec` and `status`. The fields that carry operational meaning:

| Field | Meaning |
|---|---|
| `metadata.name` / `namespace` | Identity. Names are unique per (group, kind, namespace). |
| `metadata.labels` | Selectable key/value pairs; used by controllers to find objects. |
| `metadata.annotations` | Non-identifying metadata; not selectable. |
| `metadata.ownerReferences` | Parent/child links used by garbage collection. |
| `metadata.finalizers` | Pre-deletion hooks; an object with a finalizer cannot be removed. |
| `metadata.generation` | Bumped on spec changes (when the status subresource exists). |
| `status.observedGeneration` | The generation the controller has processed. |
| `metadata.managedFields` | Field ownership for server-side apply. |
| `status.conditions` | Typed `True/False/Unknown` observations with reason/message. |

`generation` and `observedGeneration` show whether a controller has caught up. If
`observedGeneration` lags `generation`, the controller has not finished handling
the latest spec.

### 2.2 Labels, selectors, and ownership

Labels are how Kubernetes decouples producers from consumers. A Deployment's
ReplicaSet finds its Pods with `spec.selector`; a Service finds endpoints the same
way. Two consequences:

- **Selector immutability.** A Deployment/StatefulSet/DaemonSet selector is
  immutable in `apps/v1`. Changing it would orphan or steal Pods, so the API
  rejects it.
- **Owner references are not labels.** Ownership is a graph (`ownerReferences`),
  used for garbage collection, while labels are a flat index. A Service uses
  labels to find EndpointSlices but *also* sets owner references on them. A
  controller should not delete objects it merely matched by label.

### 2.3 Namespaces are scope, not a security boundary

Namespaces scope names and are the unit for RBAC and quota, but they are not a
kernel isolation mechanism. Without NetworkPolicy, Pods in different namespaces
can talk freely; without admission controls, a privileged Pod can reach the host.
"Namespace per tenant" is the start of a tenant model, not the whole model (see
§9).

### 2.4 Finalizers and deletion

A finalizer is a string in `metadata.finalizers`. When an object that has
finalizers is deleted, the API server sets `metadata.deletionTimestamp` but keeps
the object; the owning controller performs its cleanup and then removes its
finalizer, which releases the object. Failure modes are common:

- A controller that crashes before removing its finalizer leaves the object
  **stuck in Terminating** forever.
- Finalizers must be idempotent, because the controller can be restarted between
  cleanup and finalizer removal.
- Namespace deletion itself finalizes: a namespace stuck `Terminating` usually
  means some object in it has an unresolved finalizer or an API that cannot be
  reached.

### 2.5 Garbage collection and ownership

The garbage collector deletes objects whose owner references no longer resolve.
Cross-namespace ownership is disallowed by design: a namespaced dependent may
reference a namespaced owner only in its own namespace. The three deletion modes:

- **Background (default):** the owner is deleted immediately; dependents are
  collected afterward.
- **Foreground:** the owner is marked `deletionTimestamp` with the
  `foregroundDeletion` finalizer and stays visible until dependents are gone.
- **Orphan:** dependents survive; their owner references are removed.

`kubectl delete --cascade=foreground|background|orphan` selects the behavior.
Server-side, the `blockOwnerDeletion` field on an owner reference controls whether
a dependent can block foreground deletion.

### 2.6 The API surface worth knowing

- **Discovery:** `GET /api`, `GET /apis`, and `kubectl api-resources` map
  kind → group/version → REST plural.
- **Inspection:** `kubectl explain pod.spec.containers --recursive` reads the
  OpenAPI schema the API server publishes.
- **Field selectors** are server-side filters on supported fields
  (`metadata.name`, `metadata.namespace`, `status.phase`, …). They are not the
  same as label selectors and are much cheaper than client-side filtering.
- **Watch** is a long-lived streaming `GET` with `?watch=1`; controllers should
  use it instead of polling.
- **Dry-run** (`?dryRun=All`) runs the full admission and validation path without
  persisting. It tests a webhook or an apply without writing anything.
- **Server-side apply** tracks field ownership in `managedFields`; two controllers
  that write the same field produce a conflict, which `--force-conflicts` resolves
  explicitly rather than by clobbering.

---

## 3. Workload controllers and object semantics

Each controller owns a defined set of objects and creates others.

### 3.1 Pod

The Pod is the smallest deployable unit and the unit of scheduling:

- Containers in a Pod share a network namespace (one IP, `localhost`), the Pod
  sandbox, and any volumes mounted into several containers.
- The kubelet starts a Pod by asking the runtime (CRI) for a **sandbox** first.
  On Linux that sandbox is the `pause` container, which holds the network and IPC
  namespaces and the pod-level cgroup. App containers join that sandbox. This is
  why a Pod's IP exists before any app container starts, and why the
  `PodReadyToStartContainers` condition (stable v1.37, formerly `PodHasNetwork`)
  tracks sandbox and network setup.
- Containers in a Pod can share a process namespace with
  `shareProcessNamespace: true`, which is useful for debugging but changes signal
  and `/proc` semantics.
- A Pod does not survive the loss of its node. Anything that must outlive a node
  belongs to a workload controller that recreates it.

### 3.2 QoS classes

The scheduler and the kubelet both care about requests and limits, and the
combination determines the Pod's QoS class:

| QoS | Condition | Practical effect |
|---|---|---|
| `Guaranteed` | Every container has CPU and memory requests equal to limits (and both non-zero) | Least likely to be evicted; eligible for exclusive CPUs under the `static` CPU policy |
| `Burstable` | At least one container has a request or limit, but not `Guaranteed` | Guaranteed its requests; can burst to limits/node capacity |
| `BestEffort` | No requests or limits at all | First to be evicted under node pressure |

Rules:

- **Requests** are what the scheduler accounts for; **limits** are what the
  kernel enforces. A container over its memory limit is OOM-killed in its cgroup;
  a container over its CPU limit is throttled, not killed.
- The **effective Pod request** is the sum over app and sidecar containers, but
  for init containers it is the *maximum* init request, plus pod overhead. A large
  init container can therefore reserve resources the Pod never uses at runtime.
- QoS is decided at creation and is immutable across in-place resize; a resize
  that would change the class is rejected.
- `memory.high`-based throttling and tiered memory protection are opt-in kubelet
  behaviors (Memory QoS, beta v1.37).

### 3.3 Sidecar containers

Native sidecars are init containers with `restartPolicy: Always`
(`SidecarContainers`, beta v1.29, stable v1.33). They solve three problems:

- **Ordering.** They start before app containers and are torn down after the app
  containers have stopped, in reverse order, so a log shipper or proxy stays up
  while the app drains.
- **Job completion.** A sidecar does not prevent a Job from completing when the
  main container exits.
- **Restart semantics.** A sidecar restarts independently of the app container.

Before native sidecars existed, sidecars were run as regular containers and
`preStop` hooks were used to fake ordering. Running an Envoy proxy beside a Triton
server and guaranteeing that it becomes ready first is now handled by a native
sidecar with a startup and a readiness probe, not by a `preStop` sequence.

### 3.4 ReplicaSet and Deployment

A ReplicaSet is the simplest controller: it owns N Pods matching a selector and
creates/deletes Pods until the count matches. A Deployment is a controller that
manages ReplicaSets and owns rollout policy:

- Editing `spec.template` creates a new ReplicaSet; scaling does not trigger a
  rollout.
- `strategy.rollingUpdate.maxSurge` (default 25%) and `maxUnavailable` (default
  25%) bound how many extra/fewer Pods exist during a rollout.
- `revisionHistoryLimit` controls how many old ReplicaSets are kept for rollback.
- `progressDeadlineSeconds` (default 600) marks a rollout as failed if it makes no
  progress; it does *not* roll back automatically.
- `kubectl rollout status|history|undo|pause|resume` are the daily tools.

A rollback scales the old ReplicaSet up and the new one down. It does not restore
application state, so a schema migration still has to be reversible.

### 3.5 StatefulSet

StatefulSet gives Pods **stable identity**, which GPU training and databases
need:

- Pods are named `<name>-<ordinal>` (`web-0`, `web-1`). `.spec.ordinals.start`
  shifts the start ordinal; `.spec.serviceName` controls the governing headless
  Service and DNS.
- `podManagementPolicy: OrderedReady` (default) starts/stops Pods in order;
  `Parallel` starts them together.
- Each Pod can claim a stable PVC, and `persistentVolumeClaimRetentionPolicy`
  controls whether those PVCs are deleted when the Pod or the StatefulSet is
  deleted.
- Updates default to `RollingUpdate` from the highest ordinal down;
  `.spec.updateStrategy.rollingUpdate.maxUnavailable` allows more than one Pod at
  a time, and `partition` canaries a subset.
- `maxUnavailable` has been alpha since v1.24 and is beta (on by default) from
  v1.35; it is not GA as of v1.37, so it has to be verified on the target cluster
  before it is relied on. The `apps.kubernetes.io/pod-index` label carries the
  ordinal for selectors.

For distributed training, rank and stable network identity are what the workload
needs. A hand-rolled StatefulSet with `RANK=$(hostname | ...)` still works, but the
direction in current releases is the Workload/PodGroup APIs plus gang scheduling
(§8.7).

### 3.6 DaemonSet

A DaemonSet runs one Pod per eligible node, the right primitive for node-local
agents: driver containers, `nvidia-container-toolkit`, the device plugin,
DCGM exporter, CNI, node-exporter, log agents.

Scheduling details that matter on GPU nodes:

- The DaemonSet controller writes the Pod's `nodeAffinity` for `metadata.name`,
  and the scheduler taints `node.kubernetes.io/not-ready`,
  `unreachable`, `disk-pressure`, `memory-pressure`, `pid-pressure`, and
  `unschedulable`; DaemonSet Pods get matching tolerations automatically so they
  keep running on unhealthy nodes where their telemetry matters most.
- `updateStrategy` is `RollingUpdate` (default) or `OnDelete`. RollingUpdate
  supports `maxUnavailable` (default 1) and `maxSurge` (default 0); surge for
  DaemonSets has been GA since v1.25. `OnDelete` leaves replacement to the
  operator, which suits drivers that must not restart until a node is drained.

### 3.7 Job and CronJob

A Job runs Pods to completion:

- `completions` (how many successes), `parallelism` (how many at once),
  `completionMode` (`NonIndexed` default or `Indexed`, which gives each Pod a
  stable index used for sharding).
- `backoffLimit` bounds retries; `activeDeadlineSeconds` bounds wall-clock time.
- `podFailurePolicy` distinguishes retryable from fatal failures, so a `Failed` Pod
  from a non-zero application exit can be marked fatal when the input is bad.
- `ttlSecondsAfterFinished` lets the TTL controller delete a finished Job and its
  Pods.
- `successPolicy` and `podReplacementPolicy` define when a large Job counts as done
  and how its failed Pods are replaced.

A CronJob creates Jobs on a schedule and adds:

- `concurrencyPolicy: Allow|Forbid|Replace`; `Forbid` is the safe default for
  GPU jobs that would collide over the same device set.
- `startingDeadlineSeconds`: a run that is too late is skipped rather than piling up.
- `timeZone`, the schedule is interpreted in this zone.
- history limits (`successfulJobsHistoryLimit`, `failedJobsHistoryLimit`).

The missed-schedule rule: the controller counts missed schedules since the last
successful one (or since creation); beyond 100 it logs and stops scheduling, and
`startingDeadlineSeconds` decides how late a run may start.

### 3.8 Autoscaling

- **HPA** scales replicas from metrics (CPU, memory, custom/external). It needs
  the metrics API; the core `metrics-server` provides resource metrics.
- **VPA** recommends or sets requests/limits. It does not work well with GPU
  extended resources, because those are integer, non-overcommittable, and
  frequently require a Pod replacement.
- **Cluster infrastructure scaling** (Cluster Autoscaler, Karpenter, cloud node
  pools) adds or removes nodes. It is a control loop *outside* the core, which
  makes it an example of a controller that talks to an external API.

### 3.9 PodDisruptionBudget (PDB)

A PDB does not prevent disruptions; it prevents the **Eviction API** from
disrupting more Pods than the budget allows. `minAvailable`/`maxUnavailable`
define the budget, and `unhealthyPodEvictionPolicy: AlwaysAllow|IfHealthyBudget`
decides whether unhealthy Pods count against it. Draining a node routes through
the Eviction API, so a PDB is what keeps a rollout from taking out a quorum.

---

## 4. Pod lifecycle, kubelet, scheduling, and eviction

### 4.1 From `kubectl apply` to a running container

```text
kubectl apply (Deployment)
        │
        ▼
API server: authn → authz → mutation → validation → etcd → watch event
        │
        ▼
Deployment controller → creates ReplicaSet (ownerReference)
        │
        ▼
ReplicaSet controller → creates Pod (ownerReference, nodeName empty)
        │
        ▼
kube-scheduler: PreFilter → Filter → PostFilter → PreScore → Score
                → Reserve → Permit → PreBind → Bind
        │  writes spec.nodeName (Binding subresource)
        ▼
kubelet on the chosen node (it was watching for Pods bound to it)
        │
        ├─ admit Pod, mount volumes, allocate devices/DRA resources
        ├─ CRI: create sandbox (pause), configure network (CNI)
        ├─ CRI: create/start init containers, then sidecars, then app containers
        └─ run probes, update Pod status/conditions
        │
        ▼
EndpointSlice controller adds the Ready Pod to the Service's endpoints
```

Two details matter: the scheduler writes only `spec.nodeName` (the **Binding**
subresource) and never starts containers; and the controllers that update status
observe the Pod through their own watch, so the chain is asynchronous and
eventually consistent.

### 4.2 Pod phase vs container state

`status.phase` is a coarse summary:
`Pending` → `Running` → `Succeeded`/`Failed`, with `Unknown` when the kubelet
cannot be reached. `CrashLoopBackOff` and `Terminating` are `kubectl` display
strings derived from container states and deletion timestamps, not phases. Each
container has `Waiting`, `Running`, or `Terminated`, with a reason and exit code.

Conditions (kubelet-managed) are the useful signal: `PodScheduled`,
`PodReadyToStartContainers`, `Initialized`, `ContainersReady`, `Ready`,
`DisruptionTarget`, `PodResizePending`, `PodResizeInProgress`.

`Ready` is the conjunction of all containers being ready *and* any
`readinessGates` being `True`. Readiness gates are how a service mesh or a
controller injects its own notion of "ready" without the kubelet knowing about it.

### 4.3 Scheduling: framework, not predicates

The scheduler (scheduling framework, stable v1.19) runs each Pod through a
**scheduling cycle** (select a node) and a **binding cycle** (apply the decision).
Cycles are serial per Pod; binding can run concurrently. The extension points:

| Extension point | Purpose |
|---|---|
| `PreEnqueue` | Gate entry to the active queue (used by scheduling gates, gang quorum) |
| `QueueSort` | Order Pods in the queue (priority) |
| `PreFilter` | Precompute state; fail the cycle early |
| `Filter` | Reject infeasible nodes; runs concurrently per node |
| `PostFilter` | Only if no node passed: preemption and similar recovery |
| `PreScore` / `Score` / `NormalizeScore` | Rank feasible nodes |
| `Reserve` / `Unreserve` | Reserve resources before binding; undo on failure |
| `Permit` | Approve, deny, or wait (used by gang scheduling to hold a member) |
| `PreBind` / `Bind` | Provision (e.g. volumes) and write the Binding |
| `PostBind` | Informational cleanup |

Behaviors:

- `Reserve` happens before `Bind` to avoid races while the bind is in flight; if
  anything later fails, `Unreserve` runs in reverse order and **must not fail**.
- `Permit` is where gang scheduling holds a member until the rest of the gang is
  ready.
- The scheduler has a `QueueingHint` mechanism (stable v1.34) so that a Pod that
  failed is only retried when a relevant event occurs, rather than on every
  cluster change.
- Multiple profiles, or a second scheduler, can run side by side; a Pod selects one
  with `spec.schedulerName`.

### 4.4 Node selection primitives

From simplest to most expressive:

- `spec.nodeName`: bypasses the scheduler (used for static Pods and tests).
- `nodeSelector`: equality on node labels.
- **Node affinity:** `requiredDuringSchedulingIgnoredDuringExecution` (hard) and
  `preferredDuringSchedulingIgnoredDuringExecution` (soft, with weights), plus
  `matchExpressions` operators (`In`, `NotIn`, `Exists`, `DoesNotExist`,
  `Gt`, `Lt`).
- **Inter-pod affinity/anti-affinity:** co-locate or separate Pods by
  `topologyKey` (e.g. keeping replicas off the same node). This is O(n²)-ish at
  scale, and topology spread constraints are the better tool where they apply.
- **Topology spread constraints:** `maxSkew`, `topologyKey`, `whenUnsatisfiable`
  (`DoNotSchedule`/`ScheduleAnyway`), `minDomains`, `nodeAffinityPolicy`,
  `nodeTaintsPolicy`. This is how replicas are spread across zones.
- **Taints and tolerations:** nodes repel Pods; effects are `NoSchedule`
  (no new Pods), `PreferNoSchedule` (soft), and `NoExecute` (evict running Pods
  that do not tolerate it). `tolerationSeconds` lets a Pod stay briefly after a
  `NoExecute` taint appears, which is what gives a rolling node upgrade time.
- **Priority and preemption:** a `PriorityClass` (non-namespaced, value ≤ 1e9
  for user classes) lets the scheduler preempt lower-priority Pods when no node
  fits. `preemptionPolicy: Never` opts a high-priority Pod out of preempting
  others. The built-in `system-cluster-critical` (2000000000) and
  `system-node-critical` (2000001000) classes protect control-plane add-ons.

`kubectl cordon` marks a node unschedulable; `kubectl drain` cordons and evicts
through the Eviction API so PDBs are respected.

### 4.5 Kubelet responsibilities

The kubelet is the node's reconciliation agent:

- watches for Pods assigned to its node and admits/creates them,
- calls CRI to run the sandbox and containers,
- mounts volumes and calls CSI,
- drives the device manager and DRA `NodePrepareResources`,
- runs liveness/readiness/startup probes,
- reports Pod and Node status (and a Lease heartbeat),
- garbage-collects images and dead containers,
- enforces eviction thresholds.

The kubelet uses **PLEG** (Pod Lifecycle Event Generator) to detect container state
changes and a sync loop to reconcile. `EventedPLEG` can use runtime events instead
of polling. A slow PLEG shows up as `PLEG is not healthy` and as node `NotReady`
flapping.

### 4.6 Probes and restart policy

- `startupProbe` gates the other probes while a slow container starts; if it never
  succeeds, the container is restarted.
- `livenessProbe` failure restarts the container.
- `readinessProbe` failure removes the Pod from Service endpoints (it does not
  restart anything).
- Probes can be `exec`, `httpGet`, `tcpSocket`, or `grpc`. gRPC probes suit
  Triton/KServe-style servers that expose gRPC health.

Restart rules extend beyond the three pod-level values:

- Pod-level `restartPolicy` is `Always` (default), `OnFailure`, or `Never`, and
  a container can override it (`ContainerRestartRules`, beta v1.35).
- The kubelet backs off exponentially on repeated crashes, which is the state
  reported as `CrashLoopBackOff`. The backoff is capped by
  `KubeletCrashLoopBackOffMax` (beta v1.35).
- A container that runs successfully for a while resets the backoff.
- Sidecars always restart regardless of the Pod-level policy.

### 4.7 Termination order

1. A delete sets `metadata.deletionTimestamp` and the grace period
   (`terminationGracePeriodSeconds`, default 30s); the object stays visible as
   `Terminating`.
2. The control plane starts removing the Pod from `EndpointSlice` endpoints. The
   endpoint is not deleted immediately: it gets `terminating: true` and
   `ready: false` (for compatibility), while `serving` reflects actual readiness.
   This window is what lets a load balancer drain connections.
3. On the node, the kubelet runs each container's `preStop` hook (if any); if the
   hook outlives the grace period, the kubelet grants about two extra seconds.
4. The kubelet asks the runtime to send the container's stop signal, the
   image's `STOPSIGNAL` if set (overridable per container with the
   `ContainerStopSignals` feature), otherwise `SIGTERM`, to PID 1.
5. When the grace period expires, the runtime sends `SIGKILL` to whatever is
   left, the Pod moves to a terminal phase, and the API object is removed.

With sidecars, the kubelet waits for the last app container to stop before sending
`TERM` to sidecars, then terminates them in reverse order. Regular containers alone
do not provide that ordering.

On GPU nodes, a CUDA process must handle `SIGTERM` and release its context. If it
ignores the signal, the kubelet `SIGKILL`s it and the device plugin marks the device
free, but a half-dead process holding the GPU can make the next Pod fail until the
runtime cleans up. Graceful shutdown is a correctness requirement there.

### 4.8 Node lifecycle and heartbeat failure

Each node has a `Lease` in `kube-node-lease` that the kubelet renews. The node
controller:

- checks node status on `--node-monitor-period` (default 5s),
- marks `Ready=False`/`Unknown` when heartbeats stop,
- adds the corresponding taints (`node.kubernetes.io/not-ready`,
  `unreachable`),
- marks the node `Unknown` after `--node-monitor-grace-period` (default 40s), and
  then lets the default 5-minute window elapse before starting **API-initiated
  eviction** of the Pods (Pods get a default `NoExecute` toleration of 300s for
  the `not-ready`/`unreachable` taints),
- rate-limits evictions to `--node-eviction-rate` (default 0.1/s, i.e. one node
  per 10s), and degrades further if more than
  `--unhealthy-zone-threshold` (default 0.55) of a zone's nodes are unhealthy.

If *all* zones are unhealthy, the node controller assumes a control-plane
connectivity problem and stops evicting, so an outage of the control plane cannot
trigger cluster-wide eviction. For a node that is shutting down cleanly,
`GracefulNodeShutdown` (beta v1.21) lets the kubelet detect the event and terminate
Pods within a configured grace period rather than let them die with the node.

### 4.9 Node-pressure eviction

This is different from API-initiated eviction. The kubelet's eviction manager
watches signals and evicts Pods on the node:

- Signals: `memory.available`, `nodefs.available`, `nodefs.inodesFree`,
  `imagefs.available`, `imagefs.inodesFree`, `containerfs.available`,
  `containerfs.inodesFree`, `pid.available`.
- Hard eviction (`evictionHard`) triggers immediately at the threshold; soft
  eviction (`evictionSoft`) only triggers after
  `evictionSoftGracePeriod`.
- Default thresholds include `memory.available<100Mi`,
  `nodefs.available<10%`, `imagefs.available<15%`, and inode thresholds on Linux.
- Eviction order follows QoS and priority: `BestEffort` first, then
  `Burstable` Pods exceeding their requests, then `Guaranteed`; within a class,
  lower priority goes first. Only Pods **above their requests** are candidates
  under resource pressure, which is why requests are a protection mechanism.

`kubelet --eviction-hard` is separate from scheduler behavior: the scheduler
placed the Pods, but the kubelet is the one that evicts when the node itself runs
out.

---

## 5. Controllers, informers, and reconciliation

### 5.1 The pattern

A controller watches one or more resource types, computes the difference between
desired state (spec) and observed state (status/children), and acts through the
API. It is:

- **level-triggered:** it reconciles the whole object, not one event; missing an
  event changes nothing because the next sync re-reads state;
- **idempotent:** running reconcile twice with the same input is safe;
- **self-healing:** if a child is deleted, the next reconcile recreates it.

A reconcile is stateless with respect to the cluster: read the world, compute,
write, return. Caching what the previous reconcile did and assuming it still holds
is a common source of drift.

### 5.2 The client-go layers

Underneath `controller-runtime` (and most operators) is the client-go machinery:

- **Reflector** does a `list` then a `watch` from the returned
  `resourceVersion`. On `410 Gone` it re-lists. It is the only thing that talks to
  the API for reads.
- **DeltaFIFO** turns watch events into deltas.
- **Indexer** stores objects in a thread-safe cache with configurable indexes
  (by namespace, by owner, custom).
- **Informer** (`SharedInformer`) delivers add/update/delete notifications from
  that cache, so N controllers can share one watch and one cache.
- **Workqueue** deduplicates keys, rate-limits retries with exponential backoff,
  and supports delayed re-queuing. If ten updates for one Deployment arrive
  during a reconcile, the queue still ends with one entry.

Three consequences follow. Controllers **must not rely on receiving every event**;
a cache may be slightly stale; and `resourceVersion` conflicts are expected.

### 5.3 controller-runtime vocabulary

- `Manager` owns clients, caches, and the leader-election lock.
- `Reconciler.Reconcile(ctx, req)` receives a `NamespacedName`, fetches the
  object, and returns a result (requeue after duration) or an error.
- Predicates filter events (e.g. only reconcile on generation change, so status
  writes do not cause a loop).
- `client.Status().Update()` writes the status subresource; `client.Update()`
  writes spec and metadata. Writing one through the other's client is a common bug.
- `Owns()`/`Watches()` set up watches on child resources so that a changed child
  re-triggers the parent's reconcile.
- Finalizers are added/removed explicitly; removal must happen only after cleanup
  succeeds.

### 5.4 Consistency and field ownership

Three mechanics prevent controllers from clobbering each other:

1. **Optimistic concurrency:** updates carry `resourceVersion`; a stale write gets
   `409 Conflict`.
2. **Status subresource:** spec writes and status writes are separate endpoints,
   so a controller reporting status cannot overwrite a user's spec.
3. **Server-side apply:** `managedFields` records which manager owns which field.
   If two managers own the same field, apply reports a conflict instead of
   silently winning.

For an operator, the practical rule is to read the latest object, mutate only the
fields it manages, and let conflicts surface instead of retrying blindly. A field
that must be owned is claimed through field management rather than by deleting
another controller's value.

The `Reconcile` body, `CreateOrUpdate` patterns, status conditions, and
controller-runtime builder usage are in `docs/04-kubernetes-operator.md`.

---

## 6. Services, endpoints, and cluster networking

### 6.1 Service types and what they mean

| Type | Behavior |
|---|---|
| `ClusterIP` | A stable virtual IP inside the cluster; the default |
| `NodePort` | Allocates a port on every node and forwards to the Service |
| `LoadBalancer` | Asks the cloud (via the service controller) for an external LB |
| `ExternalName` | DNS CNAME to an external name; no proxying |
| Headless (`clusterIP: None`) | No VIP; DNS returns the Pod IPs directly |

ClusterIPs are allocated by the API server from the service CIDR (a range
separate from the pod CIDR) and released when the Service is deleted. Services
that need external cleanup carry a `metadata.finalizers` entry, a
`LoadBalancer` gets `service.kubernetes.io/load-balancer-cleanup`, which can hold
the object in `Terminating` until the cloud LB is gone. Headless Services
plus StatefulSet's `serviceName` are how `pod-0.svc` DNS names are produced.

`externalIPs` is deprecated (v1.36); an external load balancer or the Gateway API
replaces it.

### 6.2 EndpointSlices and readiness

The EndpointSlice controller (in `kube-controller-manager`) populates
`EndpointSlice` objects from Pods that match a Service selector. Mechanics:

- Slices are grouped by IP family, protocol, port, and Service, up to
  `--max-endpoints-per-slice` (default 100, max 1000).
- Each endpoint has `ready`, `serving`, and `terminating` conditions.
  `serving` maps to the Pod's `Readiness`; `terminating` is set when the Pod
  receives a deletion timestamp. `ready` is effectively `serving && !terminating`.
- kube-proxy consumes EndpointSlices, not the legacy `Endpoints` API. The
  `Endpoints` API is deprecated (v1.33) and EndpointSlice mirroring is deprecated;
  for selectorless Services, create EndpointSlices directly.
- Endpoints can be duplicated across slices while updates propagate, so consumers
  must aggregate and dedupe. kube-proxy's `EndpointSliceCache` is the reference.

Before a slow-shutting-down Pod is removed, it becomes
`terminating=true, ready=false` while `serving` still reflects whether it is
answering. That gap is where connection draining happens.

### 6.3 How a Service routes traffic

kube-proxy programs node-level forwarding. There are three modes:

- **`iptables`** (default in v1.37): installs iptables rules per Service and per
  endpoint; a `ClusterIP` connection is DNATed to a chosen Pod IP:port, and
  conntrack reverses the translation for replies. It is O(rules) and gets slow in
  huge clusters, though modern sync (minSyncPeriod, partial sync) helps.
- **`ipvs`**: a kernel hash-table load balancer. It was an experiment for higher
  throughput and has more balancing algorithms, but the IPVS model fit the
  Services API poorly. It is **deprecated**: the mode is deprecated as of v1.35,
  the `KubeProxyIPVS` feature gate is deprecated in v1.37, support is disabled by
  default from v1.40, and it will be removed in v1.43. It is not a choice for a new
  cluster.
- **`nftables`** (stable v1.33): an nftables-native implementation that replaces
  both iptables and IPVS with better performance at scale. Upstream has said the
  default will move to nftables in a future release; a mature v1.37 cluster is
  still likely on iptables unless it opted in.

Other Service fields:

- `sessionAffinity: ClientIP` pins a client to a backend for a duration.
- `internalTrafficPolicy`/`externalTrafficPolicy: Local|Cluster` controls whether
  node-local endpoints are preferred (topology-aware routing uses these).
- `trafficDistribution` accepts `PreferSameZone` and `PreferSameNode` in current
  releases (`PreferClose` is a deprecated alias for `PreferSameZone`); it expresses
  a preference rather than the hard topology guarantee of the traffic policies.
- `ipFamilyPolicy`/`ipFamilies` configure dual-stack.

Cilium can replace kube-proxy entirely with eBPF load balancing and policy in the
kernel data path. The trade-off is operational complexity and a data path that is
harder to inspect with `iptables -L`.

### 6.4 DNS

CoreDNS serves cluster DNS. A Pod's `/etc/resolv.conf` points at the cluster DNS
service, and the search domains allow short names. Two issues:

- `ndots:5` means a name with few dots is tried as `name.ns.svc.cluster.local`
  first, generating extra queries; high-QPS workloads sometimes tune this or use
  FQDNs.
- `dnsPolicy` (`ClusterFirst` default, `Default`, `ClusterFirstWithHostNet`,
  `None`) decides the resolver; host-networked Pods need attention.

Headless Services and StatefulSets rely on DNS for stable identity; CoreDNS is a
hard dependency for anything that resolves Service names.

### 6.5 CNI and pod networking

The CNI plugin gives each Pod an IP and connectivity:

1. create a veth pair; one end in the Pod's netns, one on the host,
2. attach the host end to a bridge/OVS or a routing/encap device,
3. assign the Pod IP (usually from the node's pod CIDR),
4. install routes and, where supported, policy.

Options differ in routing model (overlay vs native/cloud routes), IPAM, MTU, and
whether policy is enforced in iptables or eBPF. MTU mismatches cause
hard-to-diagnose hangs with large frames and on RDMA/GPUDirect setups.

### 6.6 NetworkPolicy

NetworkPolicy is a Pod-level firewall keyed on labels. Defaults matter: if no
policy selects a Pod, all traffic is allowed; once a policy selects it, only
allowed traffic flows (for the directions that policy covers). Policies are
additive, there are no deny rules, and they are enforced by the CNI (Calico,
Cilium, …), not by kube-proxy. For GPU clouds, a default-deny baseline in tenant
namespaces plus explicit allow rules is the standard starting point.

---

## 7. Storage, configuration, and secrets

### 7.1 PersistentVolumes, PVCs, and StorageClasses

- A **PVC** is a namespaced request (size, access mode, storage class).
- A **PV** is the cluster-scoped resource; binding ties them together.
- A **StorageClass** defines the provisioner (CSI driver), parameters, reclaim
  policy, and volume binding mode.

Points that matter:

- **Access modes:** `ReadWriteOnce` (one node), `ReadOnlyMany`, `ReadWriteMany`
  (driver-dependent), and `ReadWriteOncePod` (one Pod, stricter than RWO).
- **Reclaim policy:** `Delete` (remove backing storage) or `Retain` (keep it; an
  admin must clean up manually). `Recycle` is deprecated.
- **Volume binding mode:** `Immediate` vs `WaitForFirstConsumer`. The latter is
  essential when the storage is zonal, because it delays binding until the Pod's
  node (and therefore zone) is known.
- **Expansion:** PVCs can grow if the StorageClass has
  `allowVolumeExpansion: true` and the driver supports it.
- **Snapshots:** `VolumeSnapshotClass`/`VolumeSnapshot` via CSI.
- **CSI** is the standard driver interface; in-tree drivers have been migrated or
  removed. A CSI driver can be a DaemonSet (node plugin) plus a controller
  Deployment (provisioner, attacher, resizer).

GPU training usually wants high-throughput shared storage (Lustre, Weka, NFS, or
cloud parallel filesystems) mounted read-only for datasets, and a fast local
scratch volume for checkpoints.

### 7.2 ConfigMaps and Secrets

- ConfigMaps hold non-sensitive config, consumable as env vars, files, or
  command-line args.
- Secrets hold sensitive bytes. They are **base64-encoded, not encrypted** by
  default; encryption at rest (KMS v2), RBAC, and an external store (Vault, a cloud
  secret manager) each cover a different part of that gap.
- Both can be `immutable: true`, which improves performance (no watch fan-out on
  change) at the cost of requiring a new object to update.
- Projected volumes combine sources (ConfigMap, Secret, Downward API,
  ServiceAccount token) into one mount.

ServiceAccount tokens are the security-sensitive case: since v1.24 the kubelet
projects short-lived, audience-bound, auto-rotating tokens via `TokenRequest`,
rather than mounting a static Secret. Long-lived static tokens still exist but are
discouraged. `automountServiceAccountToken: false` on Pods that never call the API
removes an unused credential from them.

### 7.3 Quota and limit ranges

- **ResourceQuota** caps aggregate consumption per namespace (compute, storage,
  object counts) and can be scoped (`BestEffort`, `NotBestEffort`, `Terminating`,
  `NotTerminating`, `PriorityClass`, `CrossNamespacePodAffinity`). A quota also
  forces Pods to declare requests/limits for the constrained resources.
- **LimitRange** supplies defaults and per-Pod/per-container min/max, and can
  enforce a default request/limit ratio. It is admission-time policy, not a
  scheduler feature.

For GPU clouds, quota at the Kubernetes layer is necessary but not sufficient. A
reservations and billing system is also required, because `nvidia.com/gpu` quota is
a blunt instrument and MIG or time-slicing change what a "GPU" is.

---

## 8. Scheduling GPU workloads: extended resources, device plugins, and DRA

### 8.1 Extended resources

`nvidia.com/gpu` is an **extended resource**: a fully-qualified resource name
outside `kubernetes.io`. Rules:

- Integer only, no overcommit, no fractional values.
- It must be specified in `limits`; if `requests` is also specified, it must equal
  the limit (the API defaults the request to the limit).
- Devices cannot be shared between containers via the extended-resource path;
  each requested unit is exclusive.
- The scheduler treats the quantity as an opaque integer. It does **not** know
  which physical GPU it is; that mapping happens later at the node.

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: triton-server
spec:
  containers:
    - name: triton
      image: nvcr.io/nvidia/tritonserver:latest
      resources:
        limits:
          nvidia.com/gpu: 1     # integer; no requests value needed
```

A GPU request is usually accompanied by CPU and memory requests, because the
scheduler packs by those. A Pod that requests one GPU but no CPU or memory is
`BestEffort` for both and competes with other Pods for them.

### 8.2 How a device plugin works

A device plugin is a node-local gRPC server, usually a DaemonSet, that registers
with the kubelet over a Unix socket:

```text
Device plugin (DaemonSet, privileged, mounts /var/lib/kubelet/device-plugins)
        │  1. Register(ResourceName=nvidia.com/gpu, socket, API version)
        ▼
kubelet Device Manager: ListAndWatch keeps device health up to date
        │  2. Node status advertises capacity/allocatable: nvidia.com/gpu
        ▼
scheduler places a Pod requesting a GPU on a node with allocatable capacity
        │  3. kubelet calls Allocate(deviceIDs) for the container
        ▼
AllocateResponse: device nodes, mounts, env vars, annotations, or CDI device names
        │
        ▼
container runtime injects the GPU; container starts with CUDA available
```

API surface (from the upstream device plugin docs):

- `GetDevicePluginOptions`, which optional RPCs the plugin supports.
- `ListAndWatch`, streams the device list and health changes.
- `Allocate`, returns the runtime changes for a container.
- `GetPreferredAllocation`, optional hint for grouping devices (e.g. NVLink
  peers or same NUMA node).
- `PreStartContainer`, optional device reset/prep before each start.

Registration ordering matters: the plugin must be serving gRPC **before** it calls
`Register` on `/var/lib/kubelet/device-plugins/kubelet.sock`. If the kubelet
restarts, it deletes the sockets in that directory, so the plugin must watch for
that condition and re-register. `ListAndWatch` is also how a device that fails (Xid error,
ECC, over-temperature) is marked unhealthy: the kubelet decrements *allocatable*
(not capacity), so no new Pods are placed there, while already-assigned Pods keep
the device and typically crash.

Since v1.31 the device plugin API can return **fully-qualified CDI device names**
(`DevicePluginCDIDevices`, GA v1.31), and the container runtime injects through
CDI. This replaces the older environment-variable injection model.

### 8.3 What the node advertises

After a healthy plugin registers, `kubectl describe node <gpu-node>` shows
`nvidia.com/gpu` under Capacity and Allocatable. When it is missing there are three
causes: the plugin is not registered, it is not healthy, or the driver is missing.

Resource names currently in use:

- `nvidia.com/gpu`, whole GPUs.
- `nvidia.com/mig-<slice>g.<memory>gb`, MIG devices under the `mixed` strategy.
- Time-sliced or MPS replicas advertised under a renamed resource such as
  `nvidia.com/gpu.shared` (plugin configuration; `renameByDefault: true`).

Node labels for placement are produced by GPU Feature Discovery (GFD) and Node
Feature Discovery (NFD), for example `nvidia.com/gpu.product`,
`nvidia.com/gpu.memory`, `nvidia.com/gpu.count`, `nvidia.com/gpu.family`,
`nvidia.com/gpu.replicas`, `nvidia.com/gpu.sharing-strategy`,
`nvidia.com/mig.capable`, `nvidia.com/mig.strategy`, and CUDA driver/runtime
version labels. A hard-coded label list is unreliable; the labels on the node
itself enumerate what is present:

```bash
kubectl get node <node> -o json \
  | jq -r '.metadata.labels | to_entries[]
           | select(.key | startswith("nvidia.com/")) | "\(.key)=\(.value)"'
```

A node selector or affinity then targets those labels, e.g.:

```yaml
spec:
  nodeSelector:
    nvidia.com/gpu.product: NVIDIA-A100-SXM4-80GB
```

### 8.4 MIG, time-slicing, and MPS

GPUs support several sharing models, and the Kubernetes mapping differs:

- **MIG (Multi-Instance GPU)** partitions a GPU into isolated instances with
  dedicated memory and SM slices. With the device plugin's `migStrategy: single`,
  each MIG instance is advertised as `nvidia.com/gpu`; with `mixed`, whole GPUs
  and MIG instances are advertised separately (`nvidia.com/gpu` for whole GPUs
  and `nvidia.com/mig-<slice>g.<memory>gb` for instances). MIG gives memory
  isolation, which matters for multi-tenant inference.
- **CUDA time-slicing** lets several containers share one GPU, interleaved in
  time. It gives no memory isolation and no fault isolation: one workload's OOM
  or illegal access can affect the others. Configured in the plugin config with
  `replicas`; the plugin advertises that many logical devices.
- **MPS (Multi-Process Service)** is an alternative sharing mechanism; the vendor's
  plugin notes time-slicing and MPS are mutually exclusive and that the sharing
  strategy is applied to all GPUs on a node, not per GPU.

The trade-off: MIG is for tenants that must not affect each other; time-slicing is
for best-effort oversubscription where isolation is not a requirement.

The GPU Operator's implementation of these modes, MIG manager, GFD labels, and
the node lifecycle, is in `docs/10-gpu-operator-kubebuilder-deep-dive.md`.

### 8.5 NUMA and topology managers

GPU performance depends on where the GPU, its memory, and the NIC sit relative to
the CPU and memory. Several kubelet managers cooperate:

- **CPU Manager** (`static` policy) gives `Guaranteed` Pods with integer CPU
  requests exclusive cores.
- **Topology Manager** aligns CPU, memory, and device allocations to the same NUMA
  node according to a policy (`none`, `best-effort`, `restricted`, `single-numa-node`).
  Device plugins supply the NUMA hints via `TopologyInfo`; a plugin that omits
  them makes alignment impossible.
- **Memory Manager** makes memory and hugepages NUMA-aligned.

For a low-latency inference node, the goal is exclusive cores, GPU, and NIC on one
NUMA node, with the correct PCIe/NVLink topology. That is a platform-level setup
rather than a Pod-level flag.

### 8.6 Dynamic Resource Allocation (DRA)

DRA decouples resource allocation from the scheduler's integer counting.

API objects (`resource.k8s.io/v1`):

| Object | Role |
|---|---|
| `DeviceClass` | A category of devices plus CEL selectors and optional `extendedResourceName` |
| `ResourceClaim` | A request for specific devices; can be shared by referencing Pods |
| `ResourceClaimTemplate` | A template from which the control plane generates a per-Pod `ResourceClaim` |
| `ResourceSlice` | A driver-published inventory of devices on nodes, with attributes and capacity |

Workflow:

1. The driver creates `ResourceSlice` objects describing devices and their
   attributes.
2. A user or workload operator creates a `ResourceClaimTemplate` (per-Pod) or a
   `ResourceClaim` (shared).
3. A controller generates `ResourceClaim`s from templates.
4. The scheduler filters nodes by which `ResourceSlice`s can satisfy the claim,
   then allocates devices into the claim's status using structured parameters
   (first-fit, lexicographic by pool/slice name, drivers can prioritize by
   naming).
5. The kubelet calls the driver's `NodePrepareResources`; the driver prepares the
   device and returns CDI devices.
6. On cleanup the kubelet calls `NodeUnprepareResources`.

What it changes:

- Constraints can be **expressed in CEL** (`device.attributes[...].memory > ...`)
  instead of inventing one extended resource per device shape.
- **Arbitrary device attributes and capacity** can be requested, not just an
  integer count.
- Claims have a lifecycle independent of Pods, so a claim can outlive a Pod or be
  shared among Pods.
- **Partitionable devices** (`DRAPartitionableDevices`, beta v1.36) let one
  physical device back multiple advertised devices (the MIG-style use case).
- **Extended resource allocation by DRA** (`DRAExtendedResource`: alpha v1.34,
  beta v1.36, stable v1.37) lets a `DeviceClass` declare an
  `extendedResourceName`, so existing Pods that request `example.com/gpu: 2`
  keep working while the allocation is handled by DRA. A special
  `deviceclass.resource.kubernetes.io/<class>` resource name allocates from any
  DeviceClass without a hand-written claim.
- **Prioritized requests** (`DRAPrioritizedList`, stable v1.36) let a claim list
  alternatives, and the scheduler picks the first available.
- The PodResources API exposes DRA allocations, so monitoring can map a device to
  a Pod.

The two mechanisms differ as follows:

| | Device plugin | DRA |
|---|---|---|
| Allocation model | Integer extended resource | Structured parameters from `ResourceSlice` |
| Constraints | Fixed resource names + node labels | CEL over device attributes/capacity |
| Lifecycle | Tied to Pod scheduling | Independent claims, shareable, templated |
| Maturity | Stable and ubiquitous | Stable core since v1.34; features still landing |
| Fit | Whole GPUs, MIG via named resources | Heterogeneous devices, MIG-style partitioning, advanced placement |

In current production deployments the GPU Operator still uses the device plugin
path, while its capabilities are being migrated to DRA.

### 8.7 Gang scheduling and the Workload API

Distributed training needs **all-or-nothing** placement: if a job needs 8 ranks
across 8 GPUs and only 7 nodes are free, starting 7 ranks wastes GPU-hours while
the last waits, and can deadlock. The `GangScheduling` plugin (introduced alpha
v1.35) implements this, and in v1.37 it was folded into the **`GenericWorkload`**
feature gate (alpha v1.35, beta v1.37, disabled by default) together with the
`Workload` and `PodGroup` APIs and workload-aware preemption.

Mechanism, as documented upstream:

1. Pods are held in `PreEnqueue` until the referenced `PodGroup` exists and the
   number of Pods reaches the policy's `minCount`.
2. Once quorum exists, the scheduler evaluates placements for the group in a
   single atomic scheduling cycle; a `PlacementFeasible` check tracks whether the
   `minCount` constraint is still satisfiable.
3. If at least `minCount` Pods can be placed, they bind; otherwise none are
   scheduled and they wait, freeing resources for other work.

`CompositePodGroup` (alpha v1.37) extends this hierarchically: groups of groups
with a `minGroupCount`, which models replicated multi-component training. Where the
feature is not enabled, the same all-or-nothing requirement can be met through the
scheduler's `Permit` extension point.

### 8.8 Putting it together for a GPU node

A working GPU Pod requires, in order:

1. A supported kernel and driver on the host (or in a driver container).
2. The container toolkit, so the runtime injects driver libraries and
   device nodes.
3. A healthy device plugin advertising `nvidia.com/gpu` (or a DRA driver
   publishing `ResourceSlice`s).
4. Node labels so the scheduler can pick the right GPU product/profile.
5. A Pod request in `limits`, plus CPU/memory requests for sane packing.
6. A container image whose CUDA user-space is compatible with the host driver.

The GPU Operator automates steps 1–4 and is covered in
`docs/10-gpu-operator-kubebuilder-deep-dive.md`.

---

## 9. Multi-tenancy and GPU cloud control planes

### 9.1 Soft vs hard multi-tenancy

Upstream's security documentation does not settle on a single definition of
multi-tenancy. The distinction that matters here:

- **Soft multi-tenancy:** tenants are mutually trusting (different teams in one
  company). Namespaces, RBAC, quotas, and NetworkPolicy are usually sufficient.
- **Hard multi-tenancy:** tenants may be adversarial (a public GPU cloud).
  Soft controls are not sufficient, and the boundary has to be stronger: dedicated
  nodes, sandboxed runtimes (gVisor, Kata), separate clusters, or VMs.

Namespaces are not a security boundary. A privileged Pod, a hostPath mount, or a
container escape crosses them. Pod Security Admission (`baseline`/`restricted`)
raises the floor, but a hard boundary requires isolation at the kernel or
hypervisor layer.

### 9.2 Controls to layer

| Layer | Control |
|---|---|
| Identity | OIDC/OIDC-projected identities, RBAC least privilege, no shared cluster-admin |
| Admission | Pod Security Admission, LimitRange, ResourceQuota, ValidatingAdmissionPolicy, tenant-scoped webhooks |
| Network | Default-deny NetworkPolicy per namespace, egress policy, separate CNI for tenant traffic |
| Compute | Quota, priority classes, node taints, dedicated node pools, MIG for GPU isolation |
| Runtime | seccomp, AppArmor/SELinux, read-only rootfs, no privileged, sandboxed runtime classes |
| Storage | Per-tenant StorageClasses and CSI credentials; avoid hostPath |
| Control plane | APF to prevent noisy-neighbor API starvation; audit logging |
| Data plane fairness | QoS, PCI/NUMA alignment, GPU sharing policy (MIG vs time-slicing) |

### 9.3 A GPU cloud control plane on top of Kubernetes

A service like "provision me 4 A100s for 8 hours" is not a single Kubernetes
object. A typical layering:

```text
Tenant-facing API (REST/gRPC/SDK/CLI)
        │  authn, rate limiting, idempotency keys
        ▼
Control-plane services
  reservations, quota/billing, placement, job orchestration, image registry
        │  create Kubernetes objects
        ▼
Kubernetes: Namespace, ResourceQuota, CRs (e.g. GpuWorkload), Job/StatefulSet, PDB
        │
        ▼
GPU nodes: GPU Operator, device plugin or DRA, MIG/time-slicing, DCGM metrics
```

Design points:

- **Quota is two-layered.** Kubernetes `ResourceQuota` is necessary but not
  sufficient; the product needs reservations and billing, which live outside
  Kubernetes and must reconcile with it.
- **Placement is a policy problem.** Scheduling by GPU product or MIG profile, by
  topology, by tenant fairness, and by cost are different objectives, and a
  scheduler optimizes one of them explicitly.
- **Failure must be survivable.** A node can be lost at any time, so a workload
  with a reservation has to be rescheduled, and the reservation must not leak.
- **The API must be idempotent.** A "create job" API needs idempotency keys and
  reconciliation, because retries are inevitable.
- **Observability is part of the product.** DCGM metrics, per-tenant attribution,
  and GPU health (Xid/ECC) determine whether billing is possible and whether SLAs
  can be kept.

---

## 10. Practical kubectl, client-go, and apply semantics

### 10.1 kubectl commands

```bash
# Cluster and node state
kubectl get nodes -o wide
kubectl describe node <node>                 # capacity, allocatable, taints, events
kubectl get nodes -o custom-columns=\
NAME:.metadata.name,GPU:.status.allocatable.nvidia\\.com/gpu

# Workload debugging
kubectl get pods -A -o wide --field-selector=status.phase!=Running
kubectl describe pod <pod>                   # events, conditions, container states
kubectl logs <pod> --previous --tail=200
kubectl logs <pod> -c <container> -f
kubectl exec -it <pod> -- sh
kubectl debug -it <pod> --image=busybox --target=<container>   # ephemeral container

# Events and rollout
kubectl get events -A --sort-by=.lastTimestamp
kubectl rollout status deployment/<name>
kubectl rollout undo deployment/<name>
kubectl rollout restart deployment/<name>

# API surface and validation
kubectl api-resources | grep -i gpu
kubectl explain pod.spec.containers --recursive
kubectl apply --dry-run=server -f manifest.yaml
kubectl diff -f manifest.yaml

# JSONPath, useful in scripts
kubectl get pod <pod> -o jsonpath='{.status.phase}{"\n"}'
kubectl get pvc -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.status.phase}{"\n"}{end}'
```

`kubectl debug` with an ephemeral container (`EphemeralContainers`, stable
v1.25) provides a shell in a distroless container: it adds a container to the
running Pod rather than restarting it, so the workload is not disturbed.

### 10.2 Talking to the API without kubectl

`kubectl` is an HTTP client with authentication. The same requests can be made
with `curl` and a token or client certificate:

```bash
APISERVER=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
TOKEN=$(kubectl create token default)
curl -sS -H "Authorization: Bearer $TOKEN" "$APISERVER/api/v1/namespaces/default/pods" | jq '.items[].metadata.name'
```

It is the same path every SDK takes, and it makes the role of certs, bearer tokens,
and API group paths concrete.

### 10.3 client-go vs controller-runtime

- `client-go` provides typed clients, informers, listers, and work queues. It is
  the foundation.
- `controller-runtime` (Kubebuilder/Operator SDK) wraps the informer/cache/queue
  machinery behind a `Manager` and a `Reconciler`, and adds
  scheme registration, watches, leader election, metrics, and webhook helpers.

An operator uses `controller-runtime`. A CLI or a small client needs only a plain
`client-go` clientset.

### 10.4 Apply semantics

- `kubectl create` fails if the object exists.
- `kubectl replace` overwrites the whole object, which is destructive when the
  full spec is not available.
- `kubectl apply` is a PATCH. Client-side apply diffs against a stored
  `last-applied-configuration` annotation; server-side apply uses `managedFields`
  and field ownership.
- `kubectl patch` supports strategic merge, JSON merge, and JSON patch. Status is
  written with a PATCH on the status subresource.

The operator-relevant rule: server-side apply or a precise patch is preferable to
read-modify-write when only part of an object is owned. Where read-modify-write is
required, `409 Conflict` is handled by re-reading and recomputing rather than by
retrying the same stale body.

---

## 11. Failure and debugging scenarios

The diagnosis follows a **layered triage**: API state → scheduler decision →
kubelet/runtime → node → GPU. `nvidia-smi` is only meaningful once the Pod has been
scheduled at all.

### 11.1 Pod stuck in `Pending`

`Pending` means the Pod is not running; it may or may not be scheduled. The events
on the Pod carry the scheduler's precise reason.

```bash
kubectl describe pod <pod>            # read Events and Conditions
kubectl get events --field-selector involvedObject.name=<pod>
kubectl get nodes -o wide
kubectl describe node <node> | sed -n '/Allocatable/,/System Info/p'
kubectl get pvc
kubectl get resourcequota,limitrange -n <ns>
```

Categories and their signals:

- **Insufficient resources:** `0/3 nodes are available: 3 Insufficient nvidia.com/gpu`.
- **Taints/affinity:** `node(s) had untolerated taint` or
  `didn't match node selector/affinity`.
- **Volume:** `pod has unbound immediate PersistentVolumeClaims` or a topology
  conflict.
- **Quota/limit range:** the API server rejects the Pod at admission, so the
  symptom is a `FailedCreate` event on the owning ReplicaSet or Job rather than a
  scheduler message.
- **Scheduling gate:** `spec.schedulingGates` (stable v1.30) deliberately holds
  the Pod out of the queue until a controller removes the gate.

### 11.2 Pod scheduled but stuck in `ContainerCreating`

The kubelet is responsible from this point:

```bash
kubectl describe pod <pod>                 # image pull, volume mount, sandbox events
journalctl -u kubelet -n 200 --no-pager
crictl ps -a
crictl logs <container-id>
journalctl -u containerd -n 200 --no-pager
```

Common causes: image pull auth or network, a CSI mount that never attaches, a
CNI sandbox failure, or a device plugin/DRA prepare failure. On GPU nodes, a
`FailedCreatePodSandBox` with a driver/runtime error message usually means the runtime hook or
CDI setup, not the scheduler.

### 11.3 `CrashLoopBackOff`

```bash
kubectl logs <pod> --previous
kubectl get pod <pod> -o jsonpath='{.status.containerStatuses[*].lastState}'
kubectl describe pod <pod>
```

The exit code identifies the cause: `137` is SIGKILL (often OOM or a failed
liveness probe), `143` is SIGTERM. If `lastState.terminated.reason` is `OOMKilled`,
the memory limit is too low or the workload leaks; check the cgroup OOM counter as
well (`/sys/fs/cgroup/.../memory.events`). If the exit code is application-specific,
the fault is in the application. `CrashLoopBackOff` itself is only the kubelet's
backoff, not a diagnosis.

### 11.4 Node `NotReady`

```bash
kubectl get node <node> -o yaml | grep -A20 conditions
kubectl describe node <node> | sed -n '/Conditions:/,/Addresses:/p'
systemctl status kubelet containerd
journalctl -u kubelet -n 300 --no-pager
df -h; free -h; uptime
dmesg -T | tail -50
```

Causes: kubelet stopped, runtime down, disk or inode pressure, PID exhaustion,
network partition, or a kernel issue. The node controller marks `Ready=Unknown`
when heartbeats stop, even if the kubelet is running but starved.

### 11.5 Service has endpoints but connections fail

```bash
kubectl get endpointslice -l kubernetes.io/service-name=<svc> -o yaml
kubectl get svc <svc> -o yaml
kubectl get pod -o wide -l <selector>
kubectl exec -it <client> -- wget -qO- <podIP>:<targetPort>   # bypass the Service
```

In order: whether the endpoint list contains a `ready` endpoint, whether
`targetPort` matches the container port, and whether the CNI enforces a
NetworkPolicy that blocks the client. If direct Pod IP works but the Service VIP
does not, the problem is in kube-proxy/CNI forwarding or conntrack, not the
application.
Terminating endpoints (`serving: true, ready: false`) are a frequent source of
"some requests fail during a rollout".

### 11.6 DNS failures

```bash
kubectl exec -it <pod> -- cat /etc/resolv.conf
kubectl exec -it <pod> -- nslookup kubernetes.default.svc.cluster.local
kubectl get pods -n kube-system -l k8s-app=kube-dns
kubectl logs -n kube-system -l k8s-app=kube-dns
```

Typical causes: CoreDNS down/overloaded, `ndots` causing excessive lookups,
NetworkPolicy blocking UDP/TCP 53, or a `dnsPolicy` mismatch on host-networked
Pods.

### 11.7 GPU pod cannot see the GPU

Order of checks mirrors §8.8:

```bash
# 1. Host sees the GPU?
nvidia-smi

# 2. Device plugin healthy and registered?
kubectl get pods -n gpu-operator -l app=nvidia-device-plugin-daemonset
kubectl logs -n gpu-operator -l app=nvidia-device-plugin-daemonset --tail=100

# 3. Node advertises the resource?
kubectl describe node <node> | grep -A6 'nvidia.com/gpu'

# 4. Pod request correct? (limits only; integer)
kubectl get pod <pod> -o jsonpath='{.spec.containers[*].resources}'

# 5. Runtime injection works?
kubectl exec <pod> -- nvidia-smi

# 6. Hardware errors?
dmesg -T | grep -i xid
nvidia-smi -q -d ECC,PAGE_RETIREMENT
```

If the resource is advertised but the Pod is `Pending`, the issue is capacity or
selection. If it is scheduled but `nvidia-smi` is missing, the runtime/toolkit
injection failed. If `nvidia-smi` works but workloads fail, the remaining causes are
CUDA/driver compatibility and Xid errors.

### 11.8 Controller or API problems

```bash
kubectl -n <ns> logs deploy/<operator> --tail=200
kubectl get <crd-object> -o yaml | grep -A5 status
kubectl get lease -A
kubectl get --raw /metrics | grep apiserver_request_total | head
```

Symptoms and causes:

- Objects stuck `Terminating` → orphaned finalizer.
- Controller hot-looping → reconcile triggered by its own status writes; addressed
  with predicates.
- `409 Conflict` storms → conflicting writers; addressed with field ownership.
- API latency and `429` → APF throttling or etcd pressure.
- Leader election flapping → etcd latency or clock skew.

---

## 12. Questions with answer sketches

### From `kubectl apply` to a running Pod

API server: TLS/authn → RBAC authz → mutating admission (defaults, sidecar
injection) → schema validation → validating admission → conversion → persist to
etcd with optimistic concurrency → watch event. The Deployment controller creates
a ReplicaSet with an ownerReference; the ReplicaSet controller creates Pods. The
scheduler runs PreFilter/Filter/PostFilter/Score, reserves, and writes
`spec.nodeName` via the Binding subresource. The kubelet on that node admits the
Pod, mounts volumes, asks CRI for a sandbox, configures CNI networking, starts
init containers, sidecars, then app containers, and updates status/conditions. The
EndpointSlice controller adds ready Pods to Service endpoints. Everything after
etcd is asynchronous and eventually consistent.

*Follow-up:* what happens if the Deployment controller is down when an object is
applied. The object persists; when the controller restarts it lists existing
Deployments and reconciles them, because controllers are level-triggered.

### A node that dies under a running Pod

The kubelet stops renewing its Lease. The node controller marks the node
`Ready=Unknown` and adds `node.kubernetes.io/unreachable` (NoExecute), which
evicts Pods that do not tolerate it; after the grace period it issues API
evictions for the rest, rate-limited per zone. The owning ReplicaSet/StatefulSet
controller creates replacement Pods elsewhere if capacity exists. The old Pod
objects may linger until eviction completes, which is why "the Pod is still there
but the node is gone" is expected.

### A stuck Deployment rollout

The rollout waits on new ReplicaSet Pods becoming Ready. The causes are image pull,
probes, resource requests against node capacity, taints and tolerations, PVC
binding, quota, and `maxUnavailable`. `kubectl rollout status` plus events identify
the stage, and `progressDeadlineSeconds` also matters: a rollout marked failed does
not roll back automatically.

### How a Service selects healthy Pods

The EndpointSlice controller matches the Service selector against Pod labels and
only includes Pods that are Ready (and, for compatibility, marks terminating ones
`ready=false` while exposing `serving`). kube-proxy/Cilium programs forwarding
from those endpoints. A Pod that fails readiness drops out of endpoints without
being restarted.

### GPU requests in the scheduling cycle

Each node advertises an integer `nvidia.com/gpu` allocatable after a healthy
device plugin registers. The scheduler counts it like CPU/memory
(integer, non-overcommittable), places the Pod on a node with capacity, and the
kubelet later calls the plugin's `Allocate` to turn the integer into specific
device nodes, mounts, and CDI names. With DRA, the scheduler instead matches
`ResourceSlice`s using structured parameters and CEL constraints.

*Follow-up:* where the device plugin runs and what selects the device. It is a
DaemonSet registered with the kubelet over a Unix socket; the kubelet calls
`Allocate` after scheduling, and the plugin picks the device, optionally informed
by `GetPreferredAllocation` and NUMA topology.

### Device plugin or DRA for MIG

Today, the device plugin with `migStrategy: mixed` is the common,
battle-tested path and it advertises `nvidia.com/mig-<slice>g.<memory>gb`. For new
designs that need richer constraints, dynamic profiles, or claims that outlive
Pods, DRA is the strategic choice; partitionable devices (beta v1.36) are the
DRA-native MIG-style model, and DRA-extended-resource (stable v1.37) keeps
existing `nvidia.com/gpu` requests working. Which path applies depends on the
driver and the cluster.

### Gang scheduling for training

Partial placement wastes resources and can deadlock. The scheduler's
`Permit` extension point holds a member until the group is approved, and the
`Workload`/`PodGroup` APIs (beta v1.37 under `GenericWorkload`) express
`minCount`/`minGroupCount`. Without it, 7 of 8 ranks may start and block the
cluster.

### Requests and limits

Requests drive scheduling and QoS; limits drive kernel enforcement. Exceeding a
memory limit causes a cgroup OOM kill; exceeding a CPU limit causes throttling.
Requests are also the protection line for eviction: a Pod within its requests is
less likely to be evicted under pressure.

### etcd and the effect of its latency

etcd is the durable source of truth, replicated by Raft and written only by the
API server. Slow etcd means slow writes, slow watch fan-out, and leader-election
churn across controllers; running workloads keep running for a while because the
kubelet and runtime do not need etcd to keep containers alive. If etcd is lost
without a backup, cluster state is lost.

### Isolating two teams on one GPU cluster

Soft: namespace per team, RBAC least privilege, ResourceQuota/LimitRange, Pod
Security Admission at `restricted`, default-deny NetworkPolicy, separate service
accounts, audit. Hard: dedicated node pools with taints/tolerations, MIG for GPU
memory/fault isolation, sandboxed runtimes (gVisor/Kata) or separate clusters,
and per-tenant admission. A namespace is not a security boundary.

### A hot-looping controller and a slow API server

Causes to check: whether status writes re-trigger reconcile, whether the work queue
is flooded by a wide label selector, whether the controller writes on every pass
instead of only on change, and whether it re-lists instead of using the informer
cache. APF throttling shows as `429`, and the work-queue metrics show the rest; rate
limiting and event filtering address both.

---

## 13. Primary sources

The upstream documentation is authoritative.

- Kubernetes documentation, concepts: <https://kubernetes.io/docs/concepts/>
  - Cluster architecture: <https://kubernetes.io/docs/concepts/architecture/>
  - Controllers: <https://kubernetes.io/docs/concepts/architecture/controller/>
  - Garbage collection: <https://kubernetes.io/docs/concepts/architecture/garbage-collection/>
  - Nodes and heartbeats: <https://kubernetes.io/docs/concepts/architecture/nodes/>
  - Pod lifecycle: <https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/>
  - Sidecar containers: <https://kubernetes.io/docs/concepts/workloads/pods/sidecar-containers/>
  - Pod QoS: <https://kubernetes.io/docs/concepts/workloads/pods/pod-qos/>
  - Scheduling framework: <https://kubernetes.io/docs/concepts/scheduling-eviction/scheduling-framework/>
  - Node-pressure eviction: <https://kubernetes.io/docs/concepts/scheduling-eviction/node-pressure-eviction/>
  - Services and virtual IPs: <https://kubernetes.io/docs/reference/networking/virtual-ips/>
  - EndpointSlices: <https://kubernetes.io/docs/concepts/services-networking/endpoint-slices/>
  - Device plugins: <https://kubernetes.io/docs/concepts/extend-kubernetes/compute-storage-net/device-plugins/>
  - DRA: <https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/>
  - Gang scheduling: <https://kubernetes.io/docs/concepts/scheduling-eviction/gang-scheduling/>
  - Multi-tenancy: <https://kubernetes.io/docs/concepts/security/multi-tenancy/>
  - API Priority and Fairness: <https://kubernetes.io/docs/concepts/cluster-administration/flow-control/>
  - Feature gates (version history): <https://kubernetes.io/docs/reference/command-line-tools-reference/feature-gates/>
- Enhancement proposals (KEPs): <https://github.com/kubernetes/enhancements>
  - Scheduling framework, KEP-624
  - Sidecar containers, KEP-753
  - Dynamic Resource Allocation, KEP-4381
- Books worth reading end to end (not summaries):
  - *Kubernetes: Up and Running*, Burns, Beda, Hightower
  - *Kubernetes in Action*, Marko Lukša
  - *Programming Kubernetes*, Hausenblas, Schimanski (operators, client-go)
  - *Designing Distributed Systems*, Brendan Burns (controller patterns)
- Upstream:
  - device plugin: <https://github.com/NVIDIA/k8s-device-plugin>
  - GPU Operator: <https://github.com/NVIDIA/gpu-operator>
  - GPU Feature Discovery: <https://github.com/NVIDIA/gpu-feature-discovery>
