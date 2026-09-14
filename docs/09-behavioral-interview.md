# 09: Behavioral Interview

Senior engineering roles on cloud platform teams are cross-functional: you work with
backend, SRE, product, and partner teams, often on problems without a clear
specification. The behavioral interview tests how you have handled that work in the
past. Interviewers look for ownership, engineering judgment, collaboration, and your
approach to ambiguity.

This chapter explains how to structure an answer, lists the questions you should
prepare for, and gives a complete example.

**This chapter covers**

- Structuring answers with the STAR format
- Preparing a set of stories that covers the common themes
- Common behavioral questions for systems engineering roles
- A worked example about building a Kubernetes operator
- Questions to ask the interviewer, and how to deliver answers

## The STAR format

Structure each answer in four parts:

| Part | Content | Length |
|---|---|---|
| **Situation** | The context: the team, the system, and the problem | One or two sentences |
| **Task** | What you were responsible for | One sentence |
| **Action** | The steps you took, including technical decisions and the alternatives you rejected | Most of the answer |
| **Result** | The outcome, with numbers where possible, and what you learned | One or two sentences |

Most weak answers spend too long on the situation and too little on the action. The
interviewer is assessing what *you* did and why.

## Prepare stories by theme

Prepare six to eight stories before the interview. Many questions can be answered
with the same story told from a different angle, so choose stories that cover
several themes. The table gives an example story for each common theme:

| Theme | Example story |
|---|---|
| Innovation | Built a code generator that replaced hundreds of hand-written SDK methods |
| Impact | Reduced API p99 latency from 800 ms to 200 ms, which unblocked onboarding for GPU clusters |
| Collaboration | Worked with backend and API teams to design the first version of a GPU workload API |
| Quality | Added integration tests that caught an incompatible CRD change before release |
| Speed | Shipped a minimal CLI in one week, then improved it based on customer feedback |
| Persistence | Spent several days finding the cause of a rare race condition in GPU allocation |
| Mentoring | Taught junior engineers the patterns for writing Kubernetes controllers |

## Common questions

1. Tell me about a complex cloud feature you designed and shipped.
2. Tell me about a time you disagreed with a teammate or manager. How was it resolved?
3. How do you decide whether to build a component, buy it, or use an open-source
   project?
4. Describe a production incident you resolved. What was the root cause, and what
   changed afterward?
5. How do you maintain code quality when a deadline is tight?
6. Tell me about a time you explained a technical design to people who are not
   engineers.
7. What is your experience contributing to open-source projects?
8. How do you proceed when requirements are ambiguous?
9. Tell me about a project that failed. What did you do, and what did you learn?
10. Why do you want to work on GPU cloud infrastructure?

For questions about disagreement and failure, make sure the answer shows what you did
to resolve the situation and what you would do differently. Do not blame others.

## A worked example

The following answer responds to question 1.

> **Situation:** Our platform let customers create GPU inference endpoints, but
> supporting a new GPU type required manual changes in every cluster.
>
> **Task:** I led the replacement of our custom Python provisioning service with a
> Kubernetes operator.
>
> **Action:** I designed a `GpuWorkload` custom resource with status conditions and
> wrote the reconciler with controller-runtime. I added finalizers so that deleting a
> workload released its GPU reservation in our cloud account, and I generated the SDK
> and CLI types from our OpenAPI specification so they stayed consistent with the API.
> I worked with the SRE team to test driver installation on a real A100 cluster, and I
> added Kind-based tests so that CI could run without GPUs.
>
> **Result:** Supporting a new GPU type became a configuration change. The p95 time to
> create an endpoint dropped by 35%, and the same operator now runs in three regions.

The answer names specific technical decisions (status conditions, finalizers,
generated types), explains why each one was made, describes work with another team,
and ends with measurable results.

## Questions to ask the interviewer

Prepare several questions. They show interest in the work and help you evaluate the
team:

- How does the team use Kubernetes today: many clusters, virtual clusters, or both?
- How does the team work with the GPU Operator and other NVIDIA platform teams?
- How do the SDK and CLI teams receive API requirements from the backend teams?
- What is the team's largest scaling challenge for the next year?
- How are on-call duties and production incidents handled?
- What does the team currently generate from OpenAPI or Protocol Buffers?
- What would success look like for this role after six months?

## Delivery

- **Describe your own contribution.** Say "I designed" and "I wrote" for your work,
  and credit others by name or role for theirs. An answer that says only "we" does
  not show what you did.
- **Quantify results** wherever possible: latency, cost, time saved, incidents
  prevented.
- **Keep each answer under two minutes.** The interviewer will ask follow-up questions
  if they want more detail.
- **Say what you learned** and what you would do differently.
- **Practice technical terms aloud** so that they come easily: reconciler, finalizer,
  controller-runtime, device plugin, MIG, DCGM.

## Summary

- Use STAR, and spend most of the answer on your actions and decisions.
- Prepare six to eight stories that together cover the common themes.
- Show ownership with first-person statements, and show judgment by explaining the
  alternatives you considered.
- End each story with a measurable result and a lesson.
- Prepare questions for the interviewer about the team's systems and challenges.
