# Preface {#preface}

## About the book

A cloud platform interview asks what happens between `kubectl apply` and a
running container, why a Pod is stuck in `Pending`, why the first `docker
build` of an image is slow and the second is fast, and what a device plugin
returns when the kubelet calls `Allocate`. This book answers those questions in
order. It starts at the Linux kernel, because a container is a small set of
existing kernel mechanisms, namespaces, cgroups, a union filesystem, rather
than a new kind of computer. It builds up through Docker into Kubernetes and
the operators that extend it, and it ends with the system-design, SDK, and
behavioral material that surrounds the technical rounds of the interview.

The companion volume, *Coding Interviews for Cracked Rustaceans*, covers the
data structures and concurrency primitives asked for in the coding round. This
book covers the platform those programs run on.

## What you need to know

The book assumes you can read a Go or Rust function, that you have run
`docker` or `kubectl` before even without being able to explain what either
does internally, and that you can read a shell pipeline. Each mechanism used in
an explanation is either built earlier in the book or named explicitly as an
assumption.

## How the book is organized

Part I covers Linux: processes, memory, namespaces and cgroups, filesystems,
networking, and how to read a node's diagnostic output. Part II covers Docker:
what `docker run` constructs, and how image layers and the build cache work.

Part III covers Kubernetes: the request path through the API server, the
objects and controllers, scheduling, networking, storage, and accelerator
scheduling. Part IV covers writing a controller: the general pattern, a
specific operator read end to end, and the GPU Operator as a case study.

Part V covers the system-design, SDK, CLI, and testing, CI/CD, and
observability material that surrounds the Kubernetes-specific rounds in this
kind of interview. Part VI covers the behavioral round.

## Conventions

A diagram is boxes and arrows in a fixed-width font:

```text
caller ──► component ──► effect
```

A command block beginning with `$` was run, and its output is reproduced
beneath it unedited, except where a note says a value is specific to the
machine it ran on. Each chapter closes with a short list of references: the
primary source the chapter draws from, and where to read the argument in full.

## What this book does not cover

It is not a Kubernetes reference manual or a certification study guide. Where a
claim depends on a specific Kubernetes release, the release is named: this book
was written against Kubernetes v1.37, and a beta feature named here may be
stable, changed, or removed by the time it is read. Version-sensitive claims
should be checked against the cluster in question.

## Acknowledgments

The claims in this book rest on the Kubernetes project's documentation and
enhancement proposals, on Linux kernel and LWN.net documentation, on the NVIDIA
GPU Operator and device plugin projects, and on the references named at the
end of each chapter.

*Arpan Pathak*
