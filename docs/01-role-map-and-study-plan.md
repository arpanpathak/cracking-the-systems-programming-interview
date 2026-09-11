# 01: Role Map and Study Plan

## The role

Senior Cloud Software Engineer for **Cloud GPU Services**.

The role calls for engineers who can:

- build SDKs and CLIs that talk to GPU cloud services,
- work across platform, backend, and partner teams,
- use **Python, Go, or Rust**,
- understand RESTful services,
- write high-quality tested software,
- drive CI/CD, performance tuning, and automation,
- support and document software,
- know Linux, containers, Kubernetes, and cloud platforms,
- ideally know code generation and have open-source experience.

The role covers the **GPU cloud control plane**, **multi-tenant scheduling**,
**cluster lifecycle**, **device plugins**, and the **developer experience
(SDK/CLI)** built on those APIs.

## Interview stages

1. **Phone and recruiter screen**
   - Background, title level, stack, compensation expectations.
   - The one-sentence summary that fits this role: *"I build cloud-facing APIs,
     SDKs and CLIs, and the controllers behind them."*

2. **Technical phone screen (coding)**
   - Usually 45 to 60 minutes.
   - One or two medium or hard problems.
   - Rust, Go, or Python is usually acceptable; Rust is this repository's focus.
   - Common themes: LRU cache, rate limiter, worker pool, token bucket, async
     HTTP, event processing, distributed counter, dependency graph.

3. **Virtual onsite**
   - System design: design a GPU cloud service or a multi-tenant GPU cluster API.
   - Linux and operating system session: processes, memory, cgroups, namespaces,
     networking, debugging, perf.
   - Kubernetes session: control plane, scheduling, operators, CRDs, device
     plugins, Helm, service mesh, GPU Operator.
   - Behavioural and leadership session.
   - Possibly a take-home or pair-programming lab building a small operator or
     controller.

4. **Team and manager round**
   - Ownership, priorities, ambiguity, cross-team collaboration.

## Four-week plan

| Week | Focus | Deliverable |
|---|---|---|
| 1 | Linux and OS fundamentals | `02-linux-concepts.md`, every command run, the debugging scenarios practised |
| 2 | Kubernetes core and operator theory | `03-kubernetes-concepts.md`, `04-kubernetes-operator.md`, `10-gpu-operator-kubebuilder-deep-dive.md` |
| 3 | Operator lab and system design | `scripts/verify-kind.sh` run, every line of the reconciler traced, `06-system-design-cloud-gpu.md` |
| 4 | SDK, CLI, Rust, and behavioural mocks | `rust-interview-lab`, `11/12/13-rust-guide-*.md`, mock interviews |

## Cheat sheet

- **The story**: one page of narrative for the most complex cloud feature shipped.
- **STAR** for behavioural questions.
- **Quantified results**: "cut API p99 latency 40% by adding client-side caching
  and async pagination."
- **A diagram** of the control plane: API server, controller, device plugin, GPU
  driver.
- **GPU internals**: where knowledge is incomplete, name the components involved
  (driver, container runtime, device plugin, MIG, DCGM, Triton) rather than
  improvising.
