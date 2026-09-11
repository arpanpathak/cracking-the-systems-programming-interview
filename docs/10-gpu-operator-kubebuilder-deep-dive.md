# 10: GPU Operator & Kubebuilder Deep Dive

The GPU Operator combines Kubernetes controllers, CRDs, DaemonSets, node feature
discovery, device plugins, container runtime configuration, MIG, monitoring, and
validation. The sections below cover how the parts fit together and which practices
transfer to a Kubebuilder project.

> Version note: GPU Operator evolves quickly. Modern releases expose a
> `ClusterPolicy` custom resource (often named `cluster-policy`) and are
> installed with a Helm chart. Some older releases were driven entirely by Helm
> values. Component names also change across releases. The architecture and
> reasoning below are stable; exact names, labels, and flags should be verified
> against the release under discussion.

---

## 1. What the GPU Operator solves

A GPU node is not useful to Kubernetes until several node-level pieces exist:

1. The kernel driver is installed and loaded on the host.
2. The user-space driver libraries are available to containers.
3. The container runtime knows how to inject GPU devices/libraries.
4. A device plugin advertises `nvidia.com/gpu` to the kubelet.
5. The node is labelled so the scheduler can find the right GPU product/MIG
   profile.
6. Monitoring can export DCGM metrics.
7. Validation that a GPU workload can run.

Doing this by hand across a cluster is slow and error-prone. The GPU Operator
turns it into declarative cluster state: when a GPU node joins, components are
reconciled onto it automatically.

---

## 2. Deployment model and reconciliation

Typical install:

```bash
helm install gpu-operator nvidia/gpu-operator \
  --namespace gpu-operator \
  --create-namespace
```

The Helm chart installs:

- a namespace (`gpu-operator`),
- CRDs (notably `ClusterPolicy`),
- the GPU Operator controller Deployment (manager),
- RBAC,
- service accounts,
- configuration for the operator.

A typical installation produces:

```bash
kubectl get clusterpolicy
NAME             AGE
cluster-policy   2m
```

The `ClusterPolicy` object is the desired state. The GPU Operator controller
watches it (and nodes/daemonsets) and reconciles the actual node-level
components. This is the Kubebuilder/controller-runtime model from
`docs/04-kubernetes-operator.md`: a custom resource is the API contract; a
controller turns it into built-in Kubernetes objects.

```text
User
 │ helm install / kubectl edit clusterpolicy
 ▼
ClusterPolicy CR (declarative desired state)
 │
 ▼
GPU Operator controller (Kubebuilder/controller-runtime manager)
 │  reads ClusterPolicy + node labels + component status
 │  watches owned DaemonSets/Deployments/Jobs
 ▼
DaemonSets + Deployments + Jobs + ConfigMaps
 │
 ├── Node Feature Discovery ──► labels nodes
 ├── Driver DaemonSet        ──► kernel driver/user libs
 ├── Container Toolkit       ──► runtime config + CDI
 ├── Device Plugin DaemonSet ──► advertises nvidia.com/gpu
 ├── GPU Feature Discovery   ──► GPU labels
 ├── MIG Manager             ──► partitions GPUs
 ├── DCGM Exporter           ──► metrics
 └── Validator               ──► end-to-end check
```

---

## 3. Component-by-component breakdown

### 3.1 GPU Operator controller

Responsibilities:

- reconcile `ClusterPolicy`,
- create/update the component DaemonSets/Deployments,
- react to nodes joining/leaving and label changes,
- manage enable/disable flags (driver, toolkit, device plugin, DCGM, MIG, etc.),
- report operator/component status.

Kubebuilder/controller-runtime patterns here:

- **One manager with many watches.** The controller may watch `ClusterPolicy`,
  nodes, and owned DaemonSets, and map relevant events to reconciles.
- **Declarative component enablement.** A field such as
  `driver.enabled` / `devicePlugin.enabled` changes what children are created.
- **Status carries state.** The ClusterPolicy/operator status tells users which
  components are deployed, what version, and what failed.
- **Upgrades are rollouts.** The operator does not replace a running driver in
  place; it rolls out DaemonSets with node lifecycle handling.

### 3.2 Node Feature Discovery (NFD)

NFD detects hardware features and labels nodes. GPU Operator can deploy NFD
workers as a DaemonSet. Features discovered include PCI devices, kernel
modules, CPUs, and network devices. GPU-related output might label nodes
with PCI vendor/device info used by later components.

The operator needs to distinguish GPU nodes from CPU nodes.
Rather than assuming every node has a GPU, it reacts to labels produced by NFD
(or by node metadata in cloud environments).

An operator that deploys per-node DaemonSets often starts by watching node
labels, and NFD is one way to produce those labels.

### 3.3 Driver DaemonSet

The driver component installs/manages the kernel driver and user-space
libraries on each GPU node.

On bare metal or non-custom cloud images this is complex:

- the driver must match the kernel version,
- DKMS may be used to build the module for the running kernel,
- the node may need a reboot or module reload,
- driver containers are privileged because they must access host kernel
  modules, `/lib/modules`, `/usr/src`, `/run/nvidia`, etc.,
- after install, the node should be validated before workloads are scheduled.

The operator encodes this lifecycle instead of requiring an admin to run an
installer per node.

GPU Operator labels and fields:

- driver version,
- CUDA driver version labels,
- node state (driver ready/not ready),
- `nvidia.com/gpu.present`, product, memory, etc. produced by GPU Feature
  Discovery (below).

### 3.4 Container toolkit / runtime component

The toolkit makes the host's GPU visible to containers. Components:

- installs or configures the container runtime,
- may configure containerd (`nvidia-container-runtime`), CRI-O, or Docker,
- creates/updates a `RuntimeClass` named `nvidia` (or similar) when requested,
- modern versions can generate **CDI (Container Device Interface)** specs under
  `/etc/cdi` so that containers can request `nvidia.com/gpu=0`-style CDI
  devices without a custom runtime.

RuntimeClass example in a workload:

```yaml
runtimeClassName: nvidia
resources:
  limits:
    nvidia.com/gpu: 1
```

If CDI is enabled, the runtime can inject the device based on CDI annotations
and specs. Older/non-CDI flows use the container runtime hook:
`nvidia-container-cli` mounts driver libraries and device nodes into the
container based on `NVIDIA_VISIBLE_DEVICES`.

### 3.5 Device Plugin

The device plugin is the Kubernetes extension point for node resources that are
not CPU/memory. It runs as a DaemonSet on GPU nodes and registers with the
local kubelet over a Unix socket.

The device plugin gRPC API:

- `GetDevicePluginOptions`
- `ListAndWatch`, return the list of devices (IDs + health) and stream changes.
- `Allocate`, called when a Pod using the devices is admitted; return
  container runtime settings: environment variables, mounts, devices.
- `GetPreferredAllocation`, optional, helps the scheduler choose devices.
- `PreStartContainer`, optional.

Registration flow:

1. Device plugin starts and connects to kubelet via
   `/var/lib/kubelet/device-plugins/kubelet.sock`.
2. Kubelet registers the plugin and learns the resource name
   (`nvidia.com/gpu`) and device list.
3. Kubelet updates node `capacity` and `allocatable` for the resource.
4. Scheduler uses the extended resource to place Pods.
5. On Pod admission, kubelet calls `Allocate` for the requested devices.
6. The plugin returns the concrete device nodes, mounts, and environment
   needed for the container runtime.

The GPU Operator does not schedule Pods; it installs the plugin that lets the
scheduler and kubelet perform GPU allocation. The scheduler only counts integers;
the device plugin converts those integers into specific devices at allocate time.

### 3.6 GPU Feature Discovery (GFD)

GFD discovers GPU properties on each node and labels it. Examples:

- product name (e.g. `NVIDIA-A100-SXM4-80GB`),
- memory size,
- GPU count,
- driver/CUDA version,
- MIG capability/profile.

These labels let users express node selection in Pod specs:

```yaml
nodeSelector:
  nvidia.com/gpu.product: NVIDIA-A100
```

They also let cluster autoscalers, billing, and scheduling policies make
product-aware decisions.

### 3.7 MIG manager

MIG (Multi-Instance GPU) partitions supported GPUs into isolated compute
instances with dedicated memory and compute slices. The MIG manager can:

- configure MIG mode on GPUs,
- create/delete GPU instances and compute instances,
- keep configuration consistent across reboots,
- expose MIG devices to the device plugin.

MIG strategies:

- **none**: no MIG partitioning; whole GPUs are exposed.
- **single**: all GPUs use the same MIG profile; each slice becomes a schedulable
  unit of `nvidia.com/gpu` (or a MIG-specific resource).
- **mixed**: individual MIG devices with different profiles are exposed; this is
  more flexible but more complex for scheduling/labels.

MIG is not a software emulation; it provides hardware isolation of compute,
memory, and fault domains. It is different from **time-slicing**, which lets
multiple Pods share one GPU over time without memory isolation.

### 3.8 DCGM exporter

DCGM (Data Center GPU Manager) exposes GPU telemetry: utilization, memory,
temperature, power, clocks, PCIe throughput, Xid/ECC counters, MIG usage, etc.
The exporter runs as a DaemonSet and produces Prometheus metrics, which
Grafana/Prometheus scrape.

Metric categories:

- `DCGM_FI_DEV_GPU_UTIL`,
- `DCGM_FI_DEV_MEM_COPY_UTIL`,
- `DCGM_FI_DEV_ENC_UTIL`,
- `DCGM_FI_DEV_MEMORY_USED` / `DCGM_FI_DEV_MEMORY_FREE`,
- `DCGM_FI_DEV_GPU_TEMP`,
- `DCGM_FI_DEV_POWER_USAGE`,
- `DCGM_FI_DEV_XID_ERRORS`,
- `DCGM_FI_DEV_ECC_CURRENT`,
- MIG device counters.

These feed control-plane monitoring, billing, and node-health checks.

### 3.9 Validator

The GPU Operator validator runs after components are installed to prove the
GPU stack works end to end. It may:

- create a small CUDA workload on a GPU node,
- check that the container can see the GPU,
- verify driver, runtime, device plugin, and monitoring integration.

The validator demonstrates an operator pattern: a rollout is not proven healthy by
DaemonSets reporting ready, so the operator runs a workload probe.

---

## 4. Lifecycle of a GPU node under the operator

1. Node joins the cluster (or is labelled as having a GPU).
2. NFD labels the node with PCI/GPU-related features.
3. GPU Operator sees the labels and/or ClusterPolicy and ensures the driver,
   toolkit, device plugin, DCGM, MIG, and validator components are scheduled to
   that node.
4. The driver DaemonSet installs/loads the driver.
5. The toolkit configures the container runtime/RuntimeClass/CDI.
6. The device plugin starts, registers with kubelet, and advertises
   `nvidia.com/gpu` (and MIG resources if enabled).
7. GFD labels GPU product/memory/count.
8. The validator runs and marks the node/operator state healthy.
9. Users create Pods requesting `nvidia.com/gpu`; the scheduler places them;
   kubelet calls `Allocate`; the runtime injects devices.

Node reboots require drivers to reload, MIG configuration to persist, and the
device plugin to re-register with the kubelet. The operator's DaemonSets and
stateful reconciliation handle this.

---

## 5. GPU scheduling path from Pod to device

```text
Pod spec
  resources:
    limits:
      nvidia.com/gpu: 1
        │
        ▼
API server admission / scheduler
  scheduler sees nvidia.com/gpu in node allocatable
        │
        ▼
Kubelet (node)
  admits Pod, calls Device Plugin Allocate
        │
        ▼
Device plugin returns:
  env: NVIDIA_VISIBLE_DEVICES=GPU-<uuid>
  mounts/device nodes
        │
        ▼
Container runtime (containerd/CRI-O + container toolkit/CDI)
  injects /dev/nvidia*, libcuda, etc.
        │
        ▼
Pod container runs nvidia-smi/CUDA successfully
```

**Extended resources must be specified as limits**, and for extended resources
Kubernetes requires requests == limits when requests are omitted. The Pod in the
sample above is valid because the resource appears in `limits`.

---

## 6. MIG, time-slicing, and vGPU compared

| Sharing mode | Isolation | Typical use |
|---|---|---|
| Whole GPU (`nvidia.com/gpu=1`) | Strong | One large workload per GPU |
| MIG | Hardware isolation of compute/memory | Multiple medium workloads, QoS-sensitive |
| Time-slicing | Software time-sharing only; no memory isolation | Interactive/dev workloads, oversubscription |
| vGPU | Virtual GPU in virtualized environments | VMs with accelerated graphics/compute |

MIG does not increase total GPU memory; each instance gets a slice of it.
Time-slicing can oversubscribe the GPU, and two Pods may interfere in compute and
memory, so it is not a hard isolation boundary.

---

## 7. Kubebuilder/controller-runtime takeaways from GPU Operator

The GPU Operator architecture demonstrates these patterns, which apply to any
operator:

1. **The control-plane API is separate from node-level machinery.** The
   `ClusterPolicy`/CR is control plane; DaemonSets are data plane.
2. **Events drive reconciliation.** Node labels, owned DaemonSets, CR changes, and
   version or config changes all feed it.
3. **Status subresources and conditions report state.** A component operator tells
   users whether the desired version is deployed, available, degraded, or
   validating.
4. **Partial failure is represented per node.** A driver install can fail on one
   node while other nodes succeed, so status has to carry per-node and
   per-component state rather than one global boolean.
5. **Node-local work maps to DaemonSets.** Any per-node component (driver, plugin,
   exporter, MIG config) maps naturally to a DaemonSet with node selectors and
   labels.
6. **Generated ConfigMaps belong to the controller.** Mutable desired state in a
   ConfigMap that other actors edit drifts away from the CR.
7. **Validation lives in the operator.** Validator pods that exercise the GPU path
   catch what `kubectl get pods` cannot.
8. **Upgrades and rollback are coordinated.** Driver, toolkit, and plugin versions
   are coupled; the operator coordinates them rather than letting each DaemonSet
   drift.
9. **Metrics and events make failures visible.** Node-state transitions, driver
   failures, and allocation failures need to be observable and alertable.
10. **Leader election bounds external writes.** Multiple manager replicas can run,
    but only one reconciles external state at a time.

---

## 8. Troubleshooting checklist

### `nvidia.com/gpu` is not allocatable on the node

- Is the device plugin pod running? `kubectl get pods -n gpu-operator -o wide`.
- Is the device plugin registered? Check its logs for `Starting FS watcher`,
  `Starting OS watcher`, `ListAndWatch`, `Registered with kubelet`.
- Is kubelet restarted recently and plugin did not re-register?
  `journalctl -u kubelet | grep -i plugin`.
- Is `nvidia-smi` healthy on the host? If the driver is down, the plugin cannot
  list devices.
- Does the node have a GPU? If it is a CPU-only node, allocatable will not have
  `nvidia.com/gpu`; that is expected.

### Pod stuck `Pending` with `0/1 nodes available`

```bash
kubectl describe pod <pod>
kubectl describe node <node> | grep -A5 'Allocatable'
kubectl get nodes -l nvidia.com/gpu.present=true
```

Causes:

- no node with the requested GPU product label,
- insufficient allocatable GPUs,
- taints/tolerations,
- node selector mismatches,
- a resource request above node allocatable.

### Pod starts but `nvidia-smi` fails inside

- Does the RuntimeClass exist? `kubectl get runtimeclass nvidia`.
- Is the container toolkit configured for the runtime?
  `kubectl logs -n gpu-operator <toolkit pod>`.
- Does the Pod have the device plugin environment injection?
  `kubectl exec <pod> -- env | grep NVIDIA`.
- Are driver libraries compatible with the CUDA container image?
  `kubectl exec <pod> -- nvidia-smi` and check driver/CUDA versions.

### GPU errors

- `dmesg | grep -i xid`
- `nvidia-smi -q -d ECC`
- `nvidia-smi -q -d PAGE_RETIREMENT`
- `kubectl logs -n gpu-operator <dcgm-exporter>`

---

## 9. Questions with answer sketches

### How a Pod gets a GPU

The Pod requests `nvidia.com/gpu` as a limit. The scheduler places it on a node
with allocatable GPUs. The kubelet calls the device plugin's `Allocate`,
which returns device nodes/mounts/env. The container runtime injects them and
the application sees a usable GPU.

### What the device plugin does

It registers a resource with kubelet, streams device health via
`ListAndWatch`, and translates requested device counts into concrete GPU
devices at `Allocate` time.

### Device plugin against runtime toolkit

The device plugin is the Kubernetes scheduler/kubelet integration. The
container toolkit/runtime is the lower-level mechanism that makes GPU devices
and libraries visible inside a container after allocation. The GPU Operator
deploys both.

### Driver updates without disrupting workloads

The mechanics are release-specific, but the approach is node lifecycle management:
nodes are drained or cordoned (or the DaemonSet rollout is relied on), the new
driver is installed and loaded, it is validated, and new GPU Pods are then allowed.
Running containers are not mutated; the operator manages node-level components and
lets Kubernetes schedule around the maintenance.

### Why most components are DaemonSets

Driver, toolkit, device plugin, DCGM exporter, and MIG manager all need to run
on every GPU node (or a subset selected by labels). A DaemonSet is the native
Kubernetes primitive for "exactly one pod per matched node," with node rollout
and scheduling semantics.

### Applying GPU Operator concepts to another operator

The design is the same: desired state as a CR; watches on node labels and owned
resources; DaemonSets for per-node components; status conditions with
observedGeneration; validators; and DCGM-style operational metrics.
