# 5. Operations: Metering and Diagnosis

## 5.1 Metering

### Allocation and utilization

```mermaid
flowchart TB
    ALLOC["Allocated<br/>capacity reserved by a tenant<br/>obtained from the scheduler"]
    USED["Utilized<br/>work the device actually performed<br/>obtained from device counters"]
    ALLOC --> GAP{"Difference<br/>is idle capacity"}
    USED --> GAP
```

Bill on allocation alone, and a tenant can reserve a device and leave it unused.
Bill on utilization alone, and a tenant can hold an exclusive device while using a
fraction of it. Record both, and read the difference as unused reserved capacity.

### Collection

```mermaid
flowchart LR
    A["Workload identity<br/>tenant, job, priority"] --> D["Collector"]
    B["Device counters<br/>compute, memory, power"] --> D
    C["Lifecycle events<br/>start, stop, preempt"] --> D
    D --> E["Time series keyed by<br/>workload and tenant"]
    E --> F["Aggregation to<br/>GPU-seconds and cost"]
    F --> G["Reporting and<br/>chargeback"]
```

### Units of measure

| Dimension | Reason for including it |
|---|---|
| GPU-seconds | The primary unit of measurement |
| Device profile | A MIG partition and a complete device are different resources |
| Reserved memory | Accounts for workloads that use part of a device |
| Idle time | Separates the cost of reservation from the cost of computation |
| Preemption events | Quantifies the benefit obtained from the lower-priority tier |

### Accuracy

Under time slicing, attribution is approximate. The collector samples counters
across processes sharing the hardware, so per-tenant values land near wall-clock
utilization and rarely sum to it exactly. Document the limitation.

Under MIG, attribution is exact, because the partition is a hardware resource.

### Distributed work

Attribute a multi-rank training job to the workload identity, and optionally split
by rank afterwards. Attributing by pod charges the job once per rank and misstates
the cost of the logical unit of work.

## 5.2 Diagnosing performance regressions

### Symptom

Four hours became seven. The code has not changed, and no errors appear. Work
completes correctly; the rate dropped.

### Layers

```mermaid
flowchart TB
    S["Establish the layers"] --> L1["Application<br/>batch size, synchronization, code path"]
    L1 --> L2["Runtime<br/>driver, libraries, collective configuration"]
    L2 --> L3["Node<br/>clocks, thermal state, error counters, contention"]
    L3 --> L4["Fabric<br/>NVLink, PCIe, inter-node network"]
    L4 --> L5["Placement<br/>device generation, topology, sharing"]
```

Continuous or intermittent? Intermittent points at contention or thermal effects,
continuous at configuration or placement.

One workload or every workload on the node? One points at the workload, every one
at the node.

### Frequent causes

| Cause | Presentation |
|---|---|
| Contention from a co-resident workload | Slower only during activity by another tenant |
| Clock throttling | Reduced clocks from power or thermal limits, with utilization appearing normal |
| Degraded interconnect | Compute performance unchanged, collective performance reduced |
| Change in placement | A different device generation, or a less favorable topology |
| Memory pressure | Additional paging, or a reduction in effective batch size |
| Rising correctable error rate | Performance drift that precedes a hardware failure |
| Silent configuration change | A library selecting a slower execution path |

The first three account for a large share of reported regressions, and all three
leave the system running and error-free.

### Method

Reproduce the workload first, using the same data and the same class of node. A
regression needs a known-good measurement, so collect two data points.

Check the physical layers first. Clock state, thermal state, and contention are
cheap to rule out and often turn out to be the cause. Change one variable at a
time.

### Detection

Record per-workload step time alongside device utilization. Utilization records
whether the device was occupied, and it can stay high while the completion rate
falls. Alert on the ratio of work completed to time elapsed.
