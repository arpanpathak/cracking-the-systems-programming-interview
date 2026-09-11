# 09: Behavioral Interview

Senior Cloud Software Engineer roles are cross-functional and senior. The
behavioral loop assesses ownership, engineering judgment, collaboration, and the
handling of ambiguity.

## The STAR format

- **Situation**: one sentence of context.
- **Task**: what the candidate owned.
- **Action**: concrete steps, including technical decisions and trade-offs.
- **Result**: a measured outcome.

## Stories mapped to company values

| Theme | Example story |
|---|---|
| Innovation | built a code generator that removed hundreds of hand-written SDK methods |
| Impact | cut API p99 from 800ms to 200ms; unblocked GPU cluster onboarding |
| Collaboration | worked with backend/API teams to design a v1 GPU workload API |
| Excellence | added integration tests and caught a CRD breaking change before release |
| Speed/agility | shipped a minimal CLI in a week, then iterated based on customer feedback |
| Determination | debugged a rare GPU allocation race for days |
| Inclusion | mentored junior engineers on Kubernetes controller patterns |

## Common systems-style behavioral questions

1. Tell me about a complex cloud feature you designed and shipped.
2. Tell me about a time you disagreed with a teammate or manager.
3. How do you decide when to build vs buy vs open source?
4. Describe a production incident you resolved. What was the root cause?
5. How do you keep high code quality when deadlines are tight?
6. Tell me about a time you had to explain a technical design to non-engineers.
7. What is your experience contributing to open source?
8. How do you handle ambiguous requirements?
9. Tell me about a time a project failed. What did you do?
10. Why this company? Why GPU cloud?

## A worked story (cloud and operator)

> **Situation**: Our SaaS platform allowed users to create GPU inference endpoints, but
> onboarding a new GPU type required manual per-cluster changes.
>
> **Task**: I led the move from a custom Python provisioner to a Kubernetes operator.
>
> **Action**: I designed a `GpuWorkload` CRD with status conditions, wrote the
> controller-runtime reconciler, added finalizers to release cloud GPU reservations,
> and generated SDK/CLI types from OpenAPI. I paired with SRE to test driver installs
> on a real A100 cluster and added Kind tests for CPU-only CI.
>
> **Result**: new GPU types became a config change; create-time p95 dropped 35%;
> the same operator now runs in three regions.

## Questions for the interviewer

- How do GPU cloud services use Kubernetes today: multi-cluster, virtual clusters, or both?
- What is the team's relationship with GPU Operator and DGX Cloud?
- How do SDK/CLI teams receive API requirements from backend teams?
- What is the biggest scaling challenge for the team in the next year?
- How are production incidents and on-call handled?
- What does the team generate from OpenAPI/protobuf today?
- What does success look like in the first six months?

## Delivery

- Attribution: state specific contributions rather than a collective "we".
- Results are quantified wherever possible.
- Ownership is shown by first-person verbs: drove, owned, shipped.
- Learning is shown by describing what would be done differently.
- Stories run under two minutes.
- Technical terms are practised aloud: reconciler, finalizer, controller-runtime,
  device plugin, MIG, DCGM.
