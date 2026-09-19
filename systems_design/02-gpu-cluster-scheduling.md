# 2. Cluster Scheduling and GPU Sharing

## 2.1 Resource model

GPU capacity is an extended resource in Kubernetes.

Quantities are whole numbers. A pod requests 1, 2, or 4 GPUs, and there is no way
to express half a device through this mechanism.

The request must equal the limit. Extended resources are not oversubscribed.

The scheduler sees a count. A node reports eight units of a named resource, and
nothing about the generation, memory size, topology, or health of the individual
devices. That information has to come from node labels or a scheduler extension,
so placement constraints are expressed through node affinity, taints, or a custom
scheduling component.

## 2.2 Device plugin architecture

A device plugin is a DaemonSet on each GPU node. It discovers the devices present
on the node, registers the resource name with the kubelet, and answers allocation
requests with the identifiers of specific devices for the kubelet to mount into
the container.

```mermaid
flowchart TB
    subgraph Node["GPU node"]
        DP["Device plugin (DaemonSet)"]
        KLT["kubelet"]
        GPU["GPU devices"]
        DP -->|"1. register resource name"| KLT
        DP -->|"2. report healthy inventory"| KLT
        KLT -->|"3. allocate request"| DP
        DP -->|"4. return device IDs"| KLT
        DP --- GPU
    end
    KLT -->|"5. node capacity and allocatable"| API["API server"]
    API --> SCHED["kube-scheduler"]
```

The scheduler picks the node and the device plugin picks the device on that node.
The scheduler cannot see individual devices.

## 2.3 Allocation sequence

```mermaid
sequenceDiagram
    participant U as User
    participant S as kube-scheduler
    participant K as kubelet
    participant D as Device plugin
    participant G as GPU

    U->>S: Pod requests nvidia.com/gpu: 2
    S->>S: Filter nodes with 2 free GPU units
    S->>S: Score candidates
    S->>K: Bind pod to selected node
    K->>D: Allocate(2)
    D->>D: Select two physical devices
    D-->>K: Device IDs
    K->>G: Mount devices into the container
```

Allocation commits at binding, so a node can be over-committed if capacity
changes between scheduling and binding. The device plugin is the only component
that sees individual devices, so device-level policy such as affinity,
exclusivity, and health is implemented there.

## 2.4 Placement constraints

These constraints are not modelled by the default scheduler.

| Constraint | Reason it matters | Mechanism |
|---|---|---|
| Device type or generation | A workload may require a particular architecture or a minimum memory size | Node labels with node affinity, or a scheduler plugin |
| Topology locality | Collectives between devices on different PCIe roots or in different NVLink islands run at a lower rate | Topology-aware plugin, or node labels describing the interconnect |
| Co-scheduling | Distributed training needs all ranks running, and partial placement holds devices that produce no progress | Coscheduling, Volcano, or Kueue |
| Exclusive access | A latency-sensitive workload may need a device to itself | Whole-device request, or MIG partitioning |
| NUMA alignment | Host memory locality affects transfer performance | Topology manager policies |

### Gang scheduling

The default scheduler places pods one at a time. A 64-rank training job can
therefore start incrementally: half the ranks hold devices while the rest wait.
Those devices are unavailable to other work, so the cluster loses throughput to a
job making no progress.

```mermaid
flowchart LR
    Q["Pending job"] --> A{"Can every rank<br/>be placed now?"}
    A -->|"yes"| B["Admit the whole job"]
    A -->|"no"| C["Hold all ranks in queue"]
    C -->|"capacity released"| A
```

Waiting until every rank can be placed avoids this, at the cost of idle capacity
while a large job waits for its last slot.

## 2.5 Sharing models

Three mechanisms let more than one workload use a single device, and they differ
mainly in isolation.

```mermaid
flowchart LR
    TS["Time slicing<br/>context switching<br/>no memory isolation"] --> MPS["MPS<br/>concurrent kernels<br/>shared memory space"]
    MPS --> MIG["MIG<br/>hardware partition<br/>dedicated SMs and memory"]
```

| Model | Isolation | Cost | Suitable for |
|---|---|---|---|
| Exclusive | Complete | One device per workload | Large training, latency-critical inference |
| Time slicing | Limited to scheduling | Context switch overhead, tail latency that cannot be bounded | Interactive development, low-utilization batch work |
| MPS | Partial, with a shared memory space | Requires coordinated launch | Several small models on one device |
| MIG | Strong, with dedicated SMs and memory | Fixed partition shapes, which may leave capacity unused | Multi-tenancy needing hardware separation |

### MIG

MIG splits a device into independent instances with dedicated compute and memory.
The device plugin advertises each partition profile as its own extended resource,
so the scheduler places partitions rather than whole devices.

Partition shapes are fixed at configuration time, so capacity can be stranded in
shapes for which there is no demand. A workload that needs the full memory of a
device cannot use a partition. Metering becomes precise, because a partition is a
hardware resource rather than a scheduling convention.

## 2.6 Fairness and preemption

A job that holds a device for a week removes that device from circulation,
however fairly it was selected. Fair placement does not correct this, so the
queue has to bound how long a job may hold capacity.

### Queues with quota

Each team or priority class gets a queue with a guaranteed share, plus the
ability to use capacity that is currently idle.

```mermaid
flowchart TB
    subgraph Teams["Submitting teams"]
        T1["Team A<br/>guaranteed 30"]
        T2["Team B<br/>guaranteed 70"]
    end
    T1 --> Q["Admission and queueing"]
    T2 --> Q
    Q --> P{"Placement by<br/>guaranteed share,<br/>then borrowing"}
    P --> G["GPU pool"]
    P -->|"no capacity"| HOLD["Hold in queue"]
```

### Preemption

Preemption lets higher-priority work reclaim borrowed capacity. A device cannot
be suspended cheaply, so preemption means stopping a workload, waiting for it to
release the device, and restarting it from its last checkpoint.

Checkpoint frequency therefore sets the cost of preemption. A job that
checkpoints every ten minutes is cheap to preempt, and one that checkpoints daily
is not.

### Starvation

Borrowing must be bounded so the lower-priority class is not delayed
indefinitely. The usual mechanisms are aging, in which a waiting job's effective
priority rises with the time it has waited, and a cap on how long capacity may be
borrowed.

## 2.7 Summary

GPU capacity is advertised through a device plugin. Placement constraints are
expressed through node labels and affinity, or through a scheduler extension.
Distributed jobs need all-or-nothing admission to avoid the partial-placement
state. The sharing model is chosen from the isolation requirement, and time
slicing and MIG are not interchangeable. Fairness is expressed as queues with
guaranteed shares, preemption is implemented as a drain and restart, and the
checkpoint interval is an input to the scheduling design.
