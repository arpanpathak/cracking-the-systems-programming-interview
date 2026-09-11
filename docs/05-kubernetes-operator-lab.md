# 05: Kubernetes Operator Lab (GpuWorkload), Step by Step

The repository contains a Kubebuilder/controller-runtime operator in `operator/`.
It compiles, has unit tests, generates CRDs and RBAC, and runs against a Kind
cluster. The sections below follow the code in the order it executes.

---

## 1. What the lab builds

The operator defines a `GpuWorkload` custom resource:

```yaml
apiVersion: gpucloud.example.com/v1
kind: GpuWorkload
metadata:
  name: triton-kind
  namespace: default
spec:
  image: nginx:1.27-alpine   # CPU-safe sample for Kind
  replicas: 1
  gpuCount: 0                # local Kind nodes do not have GPUs
  servicePort: 8080
  containerPort: 80
```

The controller reconciles each `GpuWorkload` into:

- a `Deployment` named `<name>-gpu`,
- a `Service` named `<name>-svc`,
- CR status with ready/available replicas and standard conditions.

On a real GPU cluster the sample uses `gpuCount: 1`, `runtimeClassName: nvidia`,
and a Triton image so the pod can request `nvidia.com/gpu`.

---

## 2. Kubebuilder project structure

```text
operator/
├── PROJECT
├── Makefile
├── go.mod
├── cmd/main.go
├── api/v1/
│   ├── groupversion_info.go
│   ├── gpuworkload_types.go
│   └── zz_generated.deepcopy.go
├── internal/controller/
│   ├── gpuworkload_controller.go
│   └── gpuworkload_controller_test.go
├── config/
│   ├── crd/bases/
│   ├── rbac/
│   ├── samples/
│   └── manager/
└── Dockerfile
```

The layout matters:

- `api/v1` is the API contract; `internal/controller` is the behavior.
- Generated files (`zz_generated.deepcopy.go`, CRD YAML, RBAC YAML) should be
  regenerated with `make generate manifests` when API/controller markers change.
- `config/` is a kustomize base; production overlay variations (dev, prod,
  restricted) compose it.

---

## 3. API types: `api/v1/gpuworkload_types.go`

### 3.1 Spec design

```go
type GpuWorkloadSpec struct {
    Image            string            `json:"image"`
    Replicas         *int32            `json:"replicas,omitempty"`
    GpuCount         int32             `json:"gpuCount,omitempty"`
    RuntimeClassName string            `json:"runtimeClassName,omitempty"`
    Command          []string          `json:"command,omitempty"`
    Args             []string          `json:"args,omitempty"`
    ServicePort      int32             `json:"servicePort,omitempty"`
    ContainerPort    int32             `json:"containerPort,omitempty"`
    Labels           map[string]string `json:"labels,omitempty"`
    NodeSelector     map[string]string `json:"nodeSelector,omitempty"`
    Tolerations      []Toleration      `json:"tolerations,omitempty"`
}
```

Markers on the fields:

```go
// +kubebuilder:validation:Required
Image string `json:"image"`

// +kubebuilder:validation:Minimum=0
// +kubebuilder:default=0
// +optional
GpuCount int32 `json:"gpuCount,omitempty"`
```

Observations:

- `Image` has no `omitempty` and is required; the CRD rejects objects without it.
- `Replicas` is a pointer because `0` and "unset" are different. The controller
  defaults unset to 1.
- `GpuCount` defaults to 0, so CPU-only workloads need no explicit field.
- `Tolerations` is a local type, not `corev1.Toleration`, keeping the API
  dependency-light and giving a stable external schema.

### 3.2 Status design

```go
type GpuWorkloadStatus struct {
    ReadyReplicas      int32              `json:"readyReplicas,omitempty"`
    AvailableReplicas  int32              `json:"availableReplicas,omitempty"`
    ObservedGeneration int64              `json:"observedGeneration,omitempty"`
    DeploymentName     string             `json:"deploymentName,omitempty"`
    ServiceName        string             `json:"serviceName,omitempty"`
    Phase              string             `json:"phase,omitempty"`
    Conditions         []metav1.Condition `json:"conditions,omitempty"`
}
```

Status is separate from spec because users should not be able to write status
through normal updates. The CRD marker enables the status subresource:

```go
// +kubebuilder:subresource:status
```

### 3.3 Root markers

```go
// +kubebuilder:object:root=true
// +kubebuilder:resource:path=gpuworkloads,scope=Namespaced,shortName=gw
// +kubebuilder:printcolumn:name="Phase",type=string,JSONPath=`.status.phase`
// +kubebuilder:printcolumn:name="GPUs",type=integer,JSONPath=`.spec.gpuCount`
// +kubebuilder:printcolumn:name="Ready",type=integer,JSONPath=`.status.readyReplicas`
```

`printcolumn` makes `kubectl get gpuworkload` show useful columns.

---

## 4. Controller: `internal/controller/gpuworkload_controller.go`

### 4.1 Reconcile skeleton

```go
func (r *GpuWorkloadReconciler) Reconcile(ctx context.Context, req ctrl.Request) (ctrl.Result, error) {
    logger := log.FromContext(ctx).WithValues("gpuworkload", req.NamespacedName)

    workload := &gpucloudv1.GpuWorkload{}
    if err := r.Get(ctx, req.NamespacedName, workload); err != nil {
        if apierrors.IsNotFound(err) {
            return ctrl.Result{}, nil
        }
        return ctrl.Result{}, err
    }

    if err := r.reconcileDeployment(ctx, workload); err != nil {
        logger.Error(err, "failed to reconcile Deployment")
        return ctrl.Result{}, err
    }

    if err := r.reconcileService(ctx, workload); err != nil {
        logger.Error(err, "failed to reconcile Service")
        return ctrl.Result{}, err
    }

    if err := r.updateStatus(ctx, workload); err != nil {
        logger.Error(err, "failed to update status")
        return ctrl.Result{}, err
    }

    return ctrl.Result{}, nil
}
```

Key points:

- It receives only a `NamespacedName`; it always fetches the latest object.
- NotFound means the object was deleted. Because child objects have owner refs,
  Kubernetes GC removes them; no manual delete is needed.
- Returning an error causes the controller-runtime work queue to retry with
  rate-limited backoff.

### 4.2 SetupWithManager

```go
func (r *GpuWorkloadReconciler) SetupWithManager(mgr ctrl.Manager) error {
    return ctrl.NewControllerManagedBy(mgr).
        For(&gpucloudv1.GpuWorkload{}).
        Owns(&appsv1.Deployment{}).
        Owns(&corev1.Service{}).
        Complete(r)
}
```

- `For` triggers reconciles when a `GpuWorkload` changes.
- `Owns` maps changes of owned Deployments/Services back to their controlling
  `GpuWorkload`. That is how Deployment `AvailableReplicas` changes wake up this
  controller so it can update status.
- A `Watches` on nodes would allow the controller to react to node labels and GPU
  availability without a custom resource changing.

### 4.3 reconcileDeployment

```go
deployment := &appsv1.Deployment{
    ObjectMeta: metav1.ObjectMeta{
        Name:      deploymentName(workload.Name),
        Namespace: workload.Namespace,
    },
}

_, err := controllerutil.CreateOrUpdate(ctx, r.Client, deployment, func() error {
    if err := controllerutil.SetControllerReference(workload, deployment, r.Scheme); err != nil {
        return err
    }
    // Set labels, replicas, image, ports, GPU resources, runtime class.
    return nil
})
```

`CreateOrUpdate` does three things:

- It gets the current object if it exists.
- The callback mutates the object to the desired state.
- It creates or updates only when the desired state differs.

Traps:

- `SetControllerReference` must be called before creating a child, or the child
  will not be garbage-collected with the parent.
- `Deployment.Spec.Selector` is immutable after creation; a blind change on
  update is rejected.
- Service `ClusterIP` is allocated at creation and immutable; the lab preserves
  existing fields before assigning `service.Spec`.

### 4.4 GPU resource injection

```go
func gpuResources(gpuCount int32) corev1.ResourceRequirements {
    if gpuCount == 0 {
        return corev1.ResourceRequirements{}
    }
    quantity := resource.MustParse(strconv.Itoa(int(gpuCount)))
    return corev1.ResourceRequirements{
        Requests: corev1.ResourceList{"nvidia.com/gpu": quantity},
        Limits:   corev1.ResourceList{"nvidia.com/gpu": quantity},
    }
}
```

Both request and limit are required: extended resources require
`requests == limits`, and device plugins and kubelet accounting use the allocated
quantity. The Deployment's Pod template then contains:

```yaml
resources:
  requests:
    nvidia.com/gpu: "1"
  limits:
    nvidia.com/gpu: "1"
```

### 4.5 Status update

`updateStatus` fetches the current Deployment, reads `ReadyReplicas` and
`AvailableReplicas`, builds a status struct, compares it with the latest CR
status, and only writes when different.

```go
latest := &gpucloudv1.GpuWorkload{}
if err := r.Get(ctx, client.ObjectKeyFromObject(workload), latest); err != nil {
    return err
}
newStatus := ...
if equality.Semantic.DeepEqual(latest.Status, newStatus) {
    return nil
}
latest.Status = newStatus
return r.Status().Update(ctx, latest)
```

The second fetch matters: the object received at the top of `Reconcile` may be
stale by the time status is written. Updating with a stale `resourceVersion`
causes conflicts. The fresh fetch reduces conflicts and ensures status is based
on the newest spec generation.

`ObservedGeneration` is set from `latest.Generation`; clients compare it with
`metadata.generation` to know whether status reflects the current spec.

### 4.6 Phase and conditions helpers

Pure helper functions (`phaseFor`, `conditionsFor`) are easy to unit test and
keep `Reconcile` readable. `conditionsFor` uses `metav1.Condition` with Type,
Status, Reason, Message, ObservedGeneration, and LastTransitionTime. In a
production operator, condition helper code should preserve LastTransitionTime
when the condition status has not changed; the lab sets `now` for simplicity so
the code stays small.

---

## 5. Manager entrypoint: `cmd/main.go`

`cmd/main.go`:

1. builds a scheme with client-go types and `gpucloudv1`,
2. creates a manager with metrics/health/leader-election options,
3. registers the reconciler with `SetupWithManager`,
4. adds `/healthz` and `/readyz` ping endpoints,
5. starts the manager and blocks until SIGTERM/SIGINT.

Points:

- `LeaderElectionID: "gpu-cloud-operator.example.com"` must be unique per
  operator in a cluster.
- Metrics bind address and health probe bind address are flags so tests/kind
  can start on non-default ports.
- `ctrl.GetConfigOrDie()` uses the in-cluster config when running as a Pod and
  the `KUBECONFIG` when running locally.

---

## 6. RBAC and generated config

The controller has kubebuilder RBAC markers:

```go
// +kubebuilder:rbac:groups=gpucloud.example.com,resources=gpuworkloads,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=gpucloud.example.com,resources=gpuworkloads/status,verbs=get;update;patch
// +kubebuilder:rbac:groups=gpucloud.example.com,resources=gpuworkloads/finalizers,verbs=update
// +kubebuilder:rbac:groups=apps,resources=deployments,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=core,resources=services,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=core,resources=pods,verbs=get;list;watch
```

After `make manifests`, `config/rbac/role.yaml` contains the ClusterRole.
Notice the separate verbs for `status` and `finalizers`; this is how the API
server protects those subresources.

---

## 7. Unit tests: `gpuworkload_controller_test.go`

The tests use controller-runtime's fake client:

```go
scheme := runtime.NewScheme()
utilruntime.Must(clientgoscheme.AddToScheme(scheme))
utilruntime.Must(gpucloudv1.AddToScheme(scheme))

c := fake.NewClientBuilder().
    WithScheme(scheme).
    WithObjects(workload).
    WithStatusSubresource(&gpucloudv1.GpuWorkload{}).
    Build()
```

Tests verify:

- Deployment and Service are created,
- owner reference is set,
- `runtimeClassName: nvidia` is present when requested,
- `nvidia.com/gpu` is present for GPU workloads and absent for CPU workloads,
- status contains the managed Deployment/Service names and a phase.

Limitations:

- fake client does not run a real Deployment controller or informers,
- it does not validate CRD schema,
- it does not test watch/queue wiring,
- it can still test reconcile logic, immutable-field preservation, and status
  subresource behavior.

---

## 8. Run it live on Kind

```bash
scripts/verify-kind.sh
```

The script:

1. checks `go`, `kind`, `kubectl`,
2. creates a Kind cluster named `systems-interview`,
3. installs the CRD and waits for `Established`,
4. runs `go test ./...`,
5. builds and starts the operator locally,
6. waits for `/healthz`,
7. applies the CPU-safe sample,
8. waits for the owned Deployment to roll out,
9. prints CR/Deployment/Service/Pod/operator-log evidence.

The Kind sample uses `gpuCount: 0` because Kind nodes do not have GPU drivers or
device plugins. On a real GPU cluster, GPU Operator is installed and the GPU sample
is applied with `gpuCount: 1`.

---

## 9. Explaining this operator

The narrative:

> "The operator exposes a `GpuWorkload` CRD with a small declarative spec. The
> controller watches those CRs and the Deployments/Services it owns. On each
> reconcile it reads the latest CR, creates or updates an owned Deployment that
> injects `nvidia.com/gpu` limits when needed, creates or updates a Service,
> then reads child status and writes it back to the CR with conditions and
> observedGeneration. Children are controller-owned, so Kubernetes garbage
> collects them when the CR is deleted. RBAC and CRD manifests are generated
> from markers; unit tests use a fake client and E2E runs on Kind."

Follow-up topics:

- Adding a finalizer: set the finalizer string, handle the deletion timestamp
  before child reconciliation, clean the external resource, remove the finalizer.
- Rejecting `gpuCount > 8`: a CRD maximum marker, or a validating webhook where
  the policy is cross-field.
- Adding custom metrics: register a Prometheus counter or vector in the
  reconciler, or use the controller-runtime metrics registry.
- Deleting the operator: children remain, status becomes stale, and deletion with
  finalizers blocks.
- Owner references on the Deployment: garbage collection and watch mapping.

---

## 10. Extensions to try

1. Add a **validating webhook** that rejects `gpuCount > maxGpus`.
2. Add a **mutating webhook** that defaults `servicePort`/`containerPort`
   based on the image's known inference port.
3. Add a **finalizer** that deletes a cloud reservation and blocks CR deletion
   until cleanup succeeds.
4. Add a **second controller** or watch on nodes that pauses workloads when GPU
   nodes disappear.
5. Add **Prometheus metrics** for reconciliation duration, errors, and CR phase.
6. Add **envtest** integration tests to validate generated CRD schema.
7. Add a **conversion webhook** and a `v1alpha1` version to practice API
   evolution.
8. Add **leader election** (`--leader-elect`) and run two operator replicas.
