# 04: Kubernetes Operators and Kubebuilder, Deep Dive

An operator is a chain: Kubernetes API mechanics, controller-runtime machinery,
code generation, and reconciliation. The sections below follow that chain, and the
corresponding code is in `operator/`.

---

## 1. What is an operator?

An operator is a **controller for a custom resource** that encodes operational
knowledge in code. The Kubernetes built-in controllers (Deployment,
ReplicaSet, etc.) already do this for built-in APIs. An operator does the same
for domain objects:

- a **CRD** extends the API with a typed resource,
- a **controller** watches that resource (and often child resources),
- **business logic** creates/updates/deletes real things until the observed
  state matches the desired state.

Examples:

- **GPU Operator** reconciles a `ClusterPolicy`/Helm release into node-level
  components: driver DaemonSets, container toolkit, device plugin, DCGM
  exporter, MIG manager, validators.
- **KubeFlow Training Operator** manages distributed training jobs.
- **Triton inference operators** manage the lifecycle of inference servers.

A plain Helm chart installs software once; an operator continuously reconciles
software, hardware state, upgrades, failures, and cleanup.

---

## 2. Kubernetes API mechanics

### 2.1 Group, Version, Kind, Resource

Every API object is identified by:

- **Group**: `apps`, `batch`, `gpucloud.example.com`
- **Version**: `v1`, `v1beta1`
- **Kind**: `Deployment`, `GpuWorkload`
- **Resource** (REST plural): `deployments`, `gpuworkloads`

The URL path is `/apis/<group>/<version>/namespaces/<ns>/<resource>`.
`kubectl api-resources` shows the mapping.

### 2.2 CRD vs CR

- **CRD** (`CustomResourceDefinition`) defines the schema and API plumbing.
- **CR** (`CustomResource`) is an instance of that schema, e.g. a
  `GpuWorkload` named `triton-demo`.

`kubectl apply -f config/crd/` creates a CRD. Applying a sample YAML creates a CR.

### 2.3 Structural schema

Modern CRDs require a structural schema. The API server uses it to:

- validate fields,
- prune unknown fields (unless `x-kubernetes-preserve-unknown-fields`),
- generate OpenAPI,
- support server-side apply and field validation.

This is generated from Go types by `controller-gen`. The generated CRD YAML in
`config/crd/bases/gpucloud.example.com_gpuworkloads.yaml` is not hand-written.

### 2.4 Status subresource

Declaring `+kubebuilder:subresource:status` creates a separate `/status`
endpoint, which means:

- normal users updating spec cannot accidentally overwrite status,
- controllers update status through the status subresource,
- admission webhooks see status changes only when configured,
- field selectors and conditions are more trustworthy.

### 2.5 Versioning and conversion

Multiple API versions can be served at once (`v1alpha1`, `v1`). One version is
marked as the **storage version**. Objects are converted between versions when
read/written by clients using a different version. Kubebuilder supports
conversion webhooks for non-trivial conversions and `conversion-gen` for
lossless round-trip conversions.

---

## 3. Controller-runtime internals

### 3.1 The watch → queue → reconcile loop

A controller-runtime controller is a **level-triggered loop**, not an event
handler that acts on each event as it arrives. It is built from:

```text
API server (etcd)
      │ list/watch
      ▼
Informer / Reflector ──► DeltaFIFO ──► ThreadSafeStore (cache)
                                          │ add/update/delete
                                          ▼
                                   EventHandlers
                                          │ push key
                                          ▼
                                  RateLimitingWorkQueue
                                          │ pop key
                                          ▼
                                    Reconciler (Reconcile)
                                          │ get latest object from cache
                                          │ compute desired state
                                          │ create/update/delete children
                                          ▼
                                     status updates / requeue
```

The **informer** uses a list/watch against the API server. The reflector
maintains a local cache so reads are fast and the API server is not hammered.
The **work queue** deduplicates keys: if 10 events for the same object arrive
before the reconciler handles it, they collapse into one queue entry. The
**reconciler** does not receive the event object; it receives only a
`NamespacedName` and must fetch the latest state.

### 3.2 Manager, Cache, Client, APIReader

In controller-runtime:

- **Manager** owns the shared dependencies: scheme, cache, clients, leader
  election, health/metrics servers, webhook server, and controllers.
- **Cache** provides informer-backed reads. Reads from cache are fast but may
  lag slightly behind the API server.
- **Client** (`mgr.GetClient()`) reads from cache for `Get`/`List`, writes
  directly to the API server. `mgr.GetAPIReader()` bypasses the cache where a
  strongly consistent read is required.
- Each **Reconciler** is registered with the manager via a `Builder`.

### 3.3 Builder: For, Owns, Watches

```go
func (r *GpuWorkloadReconciler) SetupWithManager(mgr ctrl.Manager) error {
    return ctrl.NewControllerManagedBy(mgr).
        For(&gpucloudv1.GpuWorkload{}).          // primary watch
        Owns(&appsv1.Deployment{}).              // watch owned children
        Owns(&corev1.Service{}).
        WithEventFilter(predicate.GenerationChangedPredicate{}).
        Complete(r)
}
```

- `For(&GpuWorkload{})`: enqueue a reconcile when a `GpuWorkload` changes.
- `Owns(&Deployment{})`: enqueue the owning `GpuWorkload` when a Deployment
  with a controller owner reference changes. This is how Deployment status
  changes wake up the custom-resource controller.
- `Watches(&corev1.Node{}, handler.EnqueueRequestsFromMapFunc(...))`: map an
  arbitrary object to one or more custom resources. GPU Operator might watch
  nodes to react to GPU labels/taints.
- `WithEventFilter(...)`: ignore events that should not trigger reconciliation
  (e.g. only spec-generation changes, only status phase changes, only label
  changes).

### 3.4 Reconciler contract

Every reconciler implements:

```go
func (r *GpuWorkloadReconciler) Reconcile(
    ctx context.Context,
    req ctrl.Request,
) (ctrl.Result, error)
```

Semantics:

- Return `ctrl.Result{}, nil`: success, no requeue.
- Return `ctrl.Result{}, err`: failure. The controller logs it, increments the
  reconcile error metric, and requeues with rate-limited backoff.
- Return `ctrl.Result{RequeueAfter: 30 * time.Second}`: success but check again
  later (useful for external resources without events).
- Return `ctrl.Result{Requeue: true}`: requeue immediately.

`context` carries the logger and deadline/cancellation, and is threaded through
client calls.

### 3.5 Level-triggered vs edge-triggered

Edge-triggered logic would try to remember every event and act on the
transition. Level-triggered logic always compares the latest actual state with
the desired state. That holds even though events can be lost, coalesced, or
replayed; the controller converges from the current state alone.

**Reconcile is idempotent and level-triggered: it reads the latest object and
converges the world to it.**

### 3.6 Rate limiting and requeue

controller-runtime workqueues use an item-based rate limiter: per-key
exponential backoff plus a global maximum. A transient API error therefore does
not hot-loop the API server. On success the entry is forgotten, so a later
error starts backoff fresh. `controller_runtime_reconcile_total`,
`controller_runtime_reconcile_errors_total`, and
`workqueue_*` metrics expose this behavior.

---

## 4. Reconciliation code patterns

### 4.1 The Reconcile body

```go
func (r *GpuWorkloadReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    logger := log.FromContext(ctx).WithValues("gpuworkload", req.NamespacedName)

    // 1. Fetch the latest object.
    workload := &gpucloudv1.GpuWorkload{}
    if err := r.Get(ctx, req.NamespacedName, workload); err != nil {
        if apierrors.IsNotFound(err) {
            // Object deleted: child objects are garbage collected via owner refs.
            return ctrl.Result{}, nil
        }
        return ctrl.Result{}, err // will requeue with backoff
    }

    // 2. Handle deletion (finalizer) if the API has marked it deleted.
    if !workload.DeletionTimestamp.IsZero() {
        return r.handleDeletion(ctx, workload)
    }

    // 3. Reconcile children: CreateOrUpdate Deployment and Service.
    if err := r.reconcileDeployment(ctx, workload); err != nil {
        return ctrl.Result{}, err
    }
    if err := r.reconcileService(ctx, workload); err != nil {
        return ctrl.Result{}, err
    }

    // 4. Read actual status from children and update the CR.
    if err := r.updateStatus(ctx, workload); err != nil {
        return ctrl.Result{}, err
    }

    return ctrl.Result{}, nil
}
```

Rules visible in this code:

1. If the object is not found, return `nil`: the object is gone and there is
   nothing to reconcile.
2. If `Get` fails for another reason, return the error and let the rate-limited
   queue retry.
3. The contents of `req` are never acted on directly; the latest object is
   fetched first.
4. Use helpers per child type so each `Reconcile` step is readable.

### 4.2 CreateOrUpdate with a mutate callback

`controllerutil.CreateOrUpdate` is a wrapper that:

1. tries to `Get` the object,
2. if missing, calls the mutate callback and then `Create`,
3. if present, calls the mutate callback and then `Update`,
4. returns whether it created/updated and any error.

```go
_, err := controllerutil.CreateOrUpdate(ctx, r.Client, deployment, func() error {
    if err := controllerutil.SetControllerReference(workload, deployment, r.Scheme); err != nil {
        return err
    }

    // Fill the desired spec.
    deployment.Labels = labels
    deployment.Spec = appsv1.DeploymentSpec{ ... }

    return nil
})
```

The mutate callback receives the object that will be sent to the API server. If
the object already exists, the API server may reject immutable fields (e.g.
Service `clusterIP`, Deployment `selector`). Production operators use
strategic-merge patches or a `mergePatch` rather than a full `Update`, which
avoids clobbering fields owned by other controllers.

### 4.3 Never mutate cached objects

The client `Get` returns a deep copy from the cache in controller-runtime
(more precisely, the cache store returns a copy through the client). A retained
object returned by a client should nevertheless not be mutated in place. Mutating
an existing object for a custom check requires `obj.DeepCopy()` first.

### 4.4 Owner references and garbage collection

`controllerutil.SetControllerReference(owner, child, scheme)` sets:

```yaml
ownerReferences:
- apiVersion: gpucloud.example.com/v1
  kind: GpuWorkload
  name: triton-demo
  uid: <uid>
  controller: true
  blockOwnerDeletion: true
```

The API server then garbage-collects the child when the owner is deleted.
`controller: true` means one owner controls the lifecycle; `Owns(...)` in the
builder uses this reference to map child events back to the owner.

External resources (cloud instances, DNS records, reservations) cannot be removed
by Kubernetes GC, so they need a **finalizer** that deletes them.

### 4.5 Finalizers

A finalizer is a string in `metadata.finalizers`. When set:

1. User deletes the object.
2. API server sets `metadata.deletionTimestamp` but does not remove the object.
3. Controllers watching the object see the deletion timestamp and run cleanup.
4. After cleanup succeeds, the controller removes the finalizer.
5. API server deletes the object.

If no controller removes the finalizer, the object stays in `Terminating`
forever, which prevents data loss and orphaned cloud resources.

```go
const gpuInstanceFinalizer = "gpucloud.example.com/gpu-instance-cleanup"

func (r *GpuWorkloadReconciler) handleDeletion(ctx context.Context, workload *gpucloudv1.GpuWorkload) (ctrl.Result, error) {
    if !controllerutil.ContainsFinalizer(workload, gpuInstanceFinalizer) {
        return ctrl.Result{}, nil
    }

    // Call the cloud provider API to terminate the GPU instance / release the
    // reservation. Retry until it succeeds.
    if err := r.terminateCloudInstance(ctx, workload); err != nil {
        return ctrl.Result{}, err
    }

    controllerutil.RemoveFinalizer(workload, gpuInstanceFinalizer)
    if err := r.Update(ctx, workload); err != nil {
        return ctrl.Result{}, err
    }
    return ctrl.Result{}, nil
}
```

The finalizer must be added when the external resource is created rather than
later. It also needs a dedicated `finalizers` RBAC verb, generated by the marker:

```go
// +kubebuilder:rbac:groups=gpucloud.example.com,resources=gpuworkloads/finalizers,verbs=update
```

### 4.6 Status conditions and observedGeneration

`[]metav1.Condition` is preferable to ad-hoc boolean fields when the object has
several phases. Standard fields:

```go
type GpuWorkloadStatus struct {
    ReadyReplicas      int32              `json:"readyReplicas,omitempty"`
    AvailableReplicas  int32              `json:"availableReplicas,omitempty"`
    ObservedGeneration int64              `json:"observedGeneration,omitempty"`
    Phase              string             `json:"phase,omitempty"`
    Conditions         []metav1.Condition `json:"conditions,omitempty"`
}
```

Rules for conditions:

- `Type`: short machine-readable name, e.g. `Available`, `Progressing`, `Ready`.
- `Status`: `True`, `False`, or `Unknown`.
- `Reason`: short CamelCase reason, e.g. `DeploymentAvailable`, `NotAvailable`.
- `Message`: human-readable detail.
- `ObservedGeneration`: the CR generation this status reflects.
- `LastTransitionTime`: only changes when status flips.

`LastTransitionTime` should not be updated on every reconcile; it stays stable
while the condition value does not change.

`observedGeneration` lets clients detect stale status:

```bash
kubectl get gpuworkload triton-demo -o jsonpath='{.status.observedGeneration}/{.metadata.generation}'
```

If status observed generation is behind spec generation, the controller has not
processed the latest spec yet.

### 4.7 Status update races

Two controllers updating the same object can conflict. Patterns to avoid
conflicts:

- Update status through the status subresource (`r.Status().Update`).
- Fetch the latest object before writing status (as the `updateStatus` helper
  in this repo does).
- If `Update` returns a conflict, requeue and retry; controller-runtime returns
  the conflict error and the queue backs off.
- Use `patch` with optimistic concurrency (`resourceVersion`) for fine-grained
  updates.

---

## 5. Kubebuilder project layout and generated code

### 5.1 Layout

```text
operator/
├── PROJECT                        # machine-readable Kubebuilder metadata
├── Makefile                       # generate/manifests/test/run/docker targets
├── go.mod
├── Dockerfile
├── cmd/main.go                    # manager entrypoint
├── api/v1/
│   ├── groupversion_info.go       # GroupVersion + SchemeBuilder
│   ├── gpuworkload_types.go       # Spec/Status Go structs + markers
│   └── zz_generated.deepcopy.go   # generated DeepCopyObject methods
├── internal/controller/
│   ├── gpuworkload_controller.go  # reconciler + SetupWithManager
│   └── gpuworkload_controller_test.go
├── config/
│   ├── crd/bases/                 # generated CRD YAML
│   ├── rbac/                      # generated Role/ClusterRole from markers
│   ├── manager/                   # operator namespace/Deployment
│   ├── samples/                   # example CRs
│   └── default/                   # kustomize composition
└── hack/boilerplate.go.txt
```

### 5.2 The PROJECT file

`PROJECT` tells Kubebuilder/controller-gen which layout plugins and resources
exist. This repo uses `go.kubebuilder.io/v4` layout, CRD version `v1`, one
namespaced resource `GpuWorkload`, and one controller.

### 5.3 API type markers

Markers are comments that controller-gen reads:

```go
// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:resource:path=gpuworkloads,scope=Namespaced,shortName=gw
// +kubebuilder:printcolumn:name="Phase",type=string,JSONPath=`.status.phase`
// +kubebuilder:printcolumn:name="GPUs",type=integer,JSONPath=`.spec.gpuCount`
type GpuWorkload struct { ... }
```

Field markers:

```go
// +kubebuilder:validation:Required
// +kubebuilder:validation:Minimum=0
// +kubebuilder:default=1
// +optional
```

The generated CRD includes these as OpenAPI schema validations/defaults.

### 5.4 Code generation commands

```bash
make generate      # deepcopy functions (controller-gen object)
make manifests     # CRDs + RBAC (controller-gen rbac:crdName=... webhook paths)
make fmt vet       # gofmt + go vet
```

In CI, `make generate manifests` runs and the build fails if the git tree
becomes dirty, which catches Go type edits that were not regenerated.

### 5.5 RBAC markers

RBAC is generated from kubebuilder markers on the controller:

```go
// +kubebuilder:rbac:groups=apps,resources=deployments,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=core,resources=services,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=core,resources=pods,verbs=get;list;watch
```

`make manifests` writes `config/rbac/role.yaml`. The controller manager
Deployment binds that Role to its ServiceAccount.

### 5.6 Manager entrypoint

`cmd/main.go`:

- builds a `Scheme` and registers the client-go types plus the API types,
- creates a `ctrl.NewManager` with metrics address, health probe address, and
  leader-election settings,
- calls `SetupWithManager` on each reconciler,
- adds health/ready checks,
- starts with a signal handler that shuts down cleanly on SIGTERM.

Common flags in a Kubebuilder manager: `--metrics-bind-address`,
`--health-probe-bind-address`, `--leader-elect`.

### 5.7 Common Kubebuilder CLI flows

```bash
kubebuilder init --domain example.com --repo github.com/you/gpu-cloud-operator
kubebuilder create api --group gpucloud --version v1 --kind GpuWorkload \
  --resource --controller
kubebuilder create webhook --group gpucloud --version v1 --kind GpuWorkload \
  --defaulting --programmatic-validation
```

The concepts that matter: init, create api, create webhook, and the generated
files.

---

## 6. Webhooks

### 6.1 Admission phases

When an object is written:

1. Authentication/authorization.
2. **Mutating admission** webhooks (can change the object).
3. Schema validation.
4. **Validating admission** webhooks (can reject).
5. Persistence to etcd.

Webhooks are HTTP services with TLS. Kubebuilder configures a webhook server in
the manager and generates manifests. The API server calls them only if the
configuration (`MutatingWebhookConfiguration` / `ValidatingWebhookConfiguration`)
routes the relevant operations.

### 6.2 Defaulting (mutating webhook)

Example: if `spec.replicas` is nil, set it to 1; if `gpuCount` is empty/zero
but the workload is a GPU workload, set defaults. Defaulting in the API server
(`+kubebuilder:default=1`) only works when the field is omitted entirely and
cannot express cross-field defaults; a mutating webhook can.

### 6.3 Validation (validating webhook)

Example:

- reject `gpuCount > maxGpusPerWorkload`,
- reject invalid image repository for the environment,
- reject changes to immutable fields such as GPU type.

```go
func (w *GpuWorkloadValidator) ValidateCreate(ctx context.Context, obj runtime.Object) (admission.Warnings, error) {
    wl := obj.(*gpucloudv1.GpuWorkload)
    if wl.Spec.GpuCount > 8 {
        return nil, fmt.Errorf("gpuCount %d exceeds maximum 8", wl.Spec.GpuCount)
    }
    return nil, nil
}
```

API schema validation covers simple single-field checks; validating webhooks are
for cross-field or policy-based validation.

---

## 7. Leader election, metrics, and health

### 7.1 Leader election

Running multiple replicas of an operator manager is good for availability, but
controllers with side effects should not all act at once. controller-runtime
leader election uses a Lease object; only the elected replica starts the
controllers. The others stay ready but idle. If the leader dies, another
acquires the lease. Flag: `--leader-elect`.

### 7.2 Metrics

controller-runtime exposes Prometheus metrics at `/metrics`:

- reconcile total/errors/duration,
- workqueue depth/adds/retries,
- REST client requests,
- Go runtime metrics.

Business metrics are added with a custom collector or `prometheus.NewCounterVec`:
`gpu_workloads_ready`, `gpu_workload_reconcile_errors_total`,
`gpu_workload_deployment_seconds`.

### 7.3 Health/readiness probes

The manager exposes `/healthz` and `/readyz`:

```go
mgr.AddHealthzCheck("healthz", healthz.Ping)
mgr.AddReadyzCheck("readyz", healthz.Ping)
```

`healthz` means the process is alive; `readyz` can include dependencies such as
API server reachability. Kubernetes uses these in the operator Deployment's
probes.

---

## 8. Operator testing pyramid

### 8.1 Unit tests with fake client

Fake client tests run without a cluster, verify that Reconcile creates the
expected child objects, sets owner refs, adds GPU resources, and updates
status. Limitations: no informers, no API validation, and no Deployment
controller.

### 8.2 Envtest (integration)

`envtest` downloads/uses `kube-apiserver` and `etcd` binaries. It starts a real
API server, installs CRDs, and can start the controller manager. This catches:

- CRD schema/validation issues,
- webhook configuration/TLS issues,
- controller manager startup,
- RBAC failures (where the exercise uses a restricted client).

### 8.3 Kind / real cluster E2E

Kind runs real kubelet/containerd/CNI inside containers. Full E2E:
install CRDs, run operator, apply sample CR, wait for owned Deployment to become
Available, inspect status and logs. This repo's `scripts/verify-kind.sh` does
that.

### 8.4 Table-driven tests for pure logic

Functions like `phaseFor`, `mergeLabels`, and `gpuResources` should have direct
table tests:

```go
func TestPhaseFor(t *testing.T) {
    tests := []struct{ name string; desired, ready, available int32; want string }{
        {"zero desired", 0, 0, 0, ""},
        {"ready", 2, 2, 2, "Ready"},
        {"degraded", 3, 2, 2, "Degraded"},
        {"pending", 3, 0, 0, "Pending"},
    }
    for _, tc := range tests { ... }
}
```

---

## 9. Operator design checklist

Each item applies to the `GpuWorkload` operator:

- [ ] Spec is declarative and minimal; status is observable.
- [ ] Status uses conditions and `observedGeneration`.
- [ ] Status subresource is enabled.
- [ ] Reconcile fetches latest object and is idempotent.
- [ ] Child resources use controller owner references.
- [ ] External resources use finalizers.
- [ ] Owned child resources are watched via `Owns`.
- [ ] Cached objects are not mutated; `DeepCopy` before local mutation.
- [ ] API schema uses Kubebuilder markers for defaults/validation.
- [ ] RBAC is least-privilege and generated from markers.
- [ ] Manager has leader election, metrics, health/ready probes.
- [ ] Unit tests cover pure functions and fake-client reconcile.
- [ ] Envtest/kind covers real API server + controller.
- [ ] Generated manifests are checked in and CI checks dirty tree.
- [ ] Operator upgrades are safe: new CRD fields are optional/compatible,
      old objects convert, rollout is rolling.

---

## 10. GPU Operator as a case study

GPU Operator is the most complex operator in the GPU platform stack, and it
demonstrates every operator concept in production:

- it is deployed with Helm and often modeled through a `ClusterPolicy` CRD,
- it watches cluster state (nodes, labels, driver state),
- it creates DaemonSets for node-level components,
- it uses node feature discovery to label nodes,
- it manages driver, container toolkit, device plugin, DCGM, MIG, and
  validation,
- it must tolerate node additions, reboots, driver upgrades, and partial
  failures.

See `docs/10-gpu-operator-kubebuilder-deep-dive.md` for the full deep
dive.

---

## 11. Questions with answer sketches

### Controllers and operators

A controller is the generic reconcile loop. An operator is a controller plus
custom resources and domain-specific operational knowledge (upgrades, backups,
recovery, cleanup). The Deployment controller is a controller; the GPU Operator
is an operator.

### Why controller logic is level-triggered

Events can be lost, reordered, and coalesced. A level-triggered loop
reads the latest desired and actual state on each run and converges, so it
cannot miss a transition and it is safe to run again.

### `nvidia.com/gpu` in limits

For extended resources Kubernetes requires `requests == limits`. Device plugins
and kubelet accounting key off the allocated quantity; if limits are missing
the Pod cannot be admitted for the GPU resource.

### The operator down with a workload present

The managed Deployment/Service keep running because they are normal Kubernetes
objects. Status will go stale and changes to the CR will not be applied until
the operator returns. If the CR is deleted with a finalizer and the operator is
down, deletion remains pending.

### Upgrade safety for an operator

API changes are additive first; old and new versions run together during a
rolling upgrade or under leader election; the storage version stays stable; CRD
compatibility is tested with envtest; finalizer and cleanup behavior is
preserved; and fields are not renamed or removed without a conversion.

### Metrics for an operator

Reconcile count/errors/duration, queue depth, workqueue retries, child object
creation failures, active CR count, and business metrics such as workloads
Ready/Pending/Failed.
