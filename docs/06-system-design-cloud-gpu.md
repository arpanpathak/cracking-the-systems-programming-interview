# 06: System Design: Cloud GPU Services

The system design interview will likely be a variation of:

> "Design a cloud GPU service where users can create, connect to, and monitor
> GPU instances or GPU-accelerated workloads."

## Step 1: Requirements

### Functional requirements

- Users create/delete/list GPU workloads (instances, jobs, inference endpoints).
- Users select GPU type, count, region/zone, OS/image, storage, network.
- Users connect via SSH / Jupyter / API / gRPC.
- Users see health, GPU metrics, logs, billing.
- Admin can manage quota, RBAC, node pools, maintenance.
- Workloads survive node failure; auto-healing.

### Non-functional requirements

- Multi-tenancy and isolation.
- High availability: control plane multi-AZ; data plane resilient.
- Latency: create GPU instance p95 < 30s (often limited by driver/firmware/image).
- Scale: thousands of concurrent creates, millions of API calls/day.
- Security: TLS, mTLS, IAM, network policies, image scanning.
- Cost: right-sizing, MIG/time-slicing, spot/on-demand, idle reclaim.
- Observability: metrics, logs, traces, alerts.

## Step 2: High-level architecture

```text
                ┌──────────────┐
  SDK/CLI ─────►│  API Gateway │
                └──────┬───────┘
                       │
                ┌──────▼───────┐
                │  AuthN/AuthZ │
                └──────┬───────┘
                       │
                ┌──────▼───────────────────────────────┐
                │  Control Plane Services              │
                │  - Tenant service                    │
                │  - Catalog service (GPU types, images)│
                │  - Quota service                     │
                │  - Placement service                 │
                │  - Workflow service                  │
                │  - Billing/audit                     │
                └──────┬───────────────────────────────┘
                       │
          ┌────────────▼────────────┐
          │ Kubernetes/Cluster Mgr  │
          │  - Multi-cluster agent  │
          │  - GPU Operator         │
          │  - CRDs / controllers   │
          └────────────┬────────────┘
                       │
              ┌────────▼────────┐
              │ GPU Node Pools  │
              │  A100/H100/L40S │
              └─────────────────┘
```

Control plane responsibilities:

- **Tenant/Project**: isolate users, namespaces, quotas.
- **Catalog**: GPU models, regions, images, price.
- **Placement**: find cluster/zone/node with capacity and GPU type.
- **Provisioner**: call cluster API to create a workload CR / namespace / quota.
- **Health monitor**: watch CR status, node conditions, GPU metrics.
- **Billing/usage**: consume metering events (DCGM, node exporter).

## Step 3: Deep dive on key components

### API and SDK/CLI

- Versioned REST API: `POST /v1/gpu-workloads`, `GET /v1/gpu-workloads/{id}`, `DELETE`.
- Async create pattern: return `202 Accepted` + `Location`, user polls status or gets webhook.
- Idempotency keys for retries.
- SDKs generate typed clients from OpenAPI.
- CLI is a thin wrapper: auth → API → table/JSON output → exit code.

### Quota and admission

- Before create, check `requested_gpus <= remaining_quota`.
- Quota types: project quota, region quota, GPU model quota.
- Race conditions solved with transaction/locking or reservation flow:
  1. `POST /reservations` creates a reservation.
  2. Provisioner consumes reservation.
  3. Timeout releases stale reservations.
- Kubernetes side: namespace `ResourceQuota`, but the cloud control plane still needs its own quota for billing.

### Workflow for creating a GPU workload

1. Validate request.
2. Check quota; reserve GPUs.
3. Select cluster/node pool based on capacity and GPU type.
4. Create a Kubernetes `GpuWorkload` CR (or directly a `Deployment`).
5. Operator reconciles Deployment/Service.
6. Wait for Pod running + readiness.
7. Mark workload `Ready`; update billing.

Failure handling: timeouts, retries, idempotency, compensation (rollback reservations).

### Storage and state

- Use a SQL DB (Postgres) for tenants, quotas, catalogs, reservations.
- Use Kubernetes API for live workload state.
- Use object storage for logs/artifacts.
- Cache reads with Redis, but not as the source of truth.
- Use an outbox/event bus for cross-service consistency (billing, notifications).

### GPU scheduling and utilization

- GPU node capacity is `nvidia.com/gpu`.
- Device plugin advertises GPUs; operator allocates.
- MIG partitions for fractional GPU.
- Time-slicing for oversubscription.
- GPU metrics via DCGM (`dcgm-exporter`).
- Node health: driver, Xid errors, temperature, power, ECC.

## Step 4: Scale and performance

- API Gateway: global routing, rate limit, auth.
- Control-plane services: stateless, horizontal scaling.
- Event queues: decouple provisioning workflows.
- Database: partition by tenant/region; read replicas.
- Kubernetes clusters: multi-cluster federation/agent rather than one giant cluster.
- Create path: the time goes to image pull, driver load, and pod start.
- Pre-pull base images on nodes.
- Cache VM/container images and snapshots.

## Step 5: Availability and failure modes

- Region outage: failover to another region; data replication.
- Node failure: pod rescheduling by K8s; if VM, replacement by cluster autoscaler.
- Control-plane API down: clients need retries/backoff; cluster keeps running.
- Operator crash: Deployment remains; on restart operator reconciles.
- Partial failure: e.g., Service created but Deployment pending; status must reflect that.

## Step 6: Security and multi-tenancy

- Namespace per tenant/project.
- NetworkPolicy per tenant.
- RBAC least privilege.
- Pod security standards.
- Secret management.
- Image provenance/signing.
- Audit logs.
- mTLS between services.

## Sample whiteboard answer outline

1. Requirements (FR/NFR)
2. API design (resources + async ops)
3. Block diagram
4. Data model
5. Provisioning workflow
6. Kubernetes integration and operator
7. Failure handling
8. Metrics and alerting
9. Scale bottlenecks
10. Trade-offs and next steps

## Core design claims

- "The API server is a declarative control plane rather than a task runner."
- "The GPU workload lifecycle is a state machine: Pending, Provisioning, Running,
  Stopping, Terminated."
- "Retries and idempotency belong in the SDK as well as the server."
- "Operators reconcile the real world to the API object; health checks feed the status."
- "The device plugin and GPU Operator handle node-level GPU plumbing; the service
  builds tenant-level orchestration on top."
