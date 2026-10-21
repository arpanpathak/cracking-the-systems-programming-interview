# Introduction

This book is about running GPU workloads on Kubernetes and about the machinery inside
Kubernetes that makes it possible. Each topic is first worked out as a small model, written
in both Go and Rust with only the standard library, so that the data structures and their
failure cases can be read in a few hundred lines. The same machinery is then built with the
libraries that production controllers use, controller-runtime in Go and kube-rs in Rust,
and run on a real cluster.

GPU workloads range from training jobs that span many machines to inference services that
answer requests continuously. Run by hand, each job needs a machine chosen for it, a record
of which GPUs are free, and someone to restart it when it fails. Kubernetes takes over that
work. A user declares what should run, and the scheduler and controllers place the work and
keep it running. Kubernetes is also extensible, so it can be taught about GPUs and about new
kinds of work such as training jobs.

A model too large for one machine is trained across many, and every training step needs
every GPU in the job. That requirement shapes the scheduling problem. All of a job's workers
have to start together, because a job that receives only some of its workers holds those
GPUs and makes no progress. The workers should run close to each other, because GPUs in one
machine exchange data much faster than GPUs in different machines. When several teams share
a cluster, queues and quotas divide the GPUs between them. The chapters take these problems
in turn, beginning with how a controller learns that a new job exists.

The examples run on any Kubernetes cluster with GPU nodes: a managed cluster from a cloud
provider, a cluster in a private data center, or a single-machine cluster.

Kubernetes has no built-in knowledge of GPUs. It knows each machine's CPU cores and memory
and places containers on machines with enough of both. Two pieces of software from the GPU
vendor add GPUs to that picture.

The first is the *device plugin*, a small program on every GPU machine. It counts the
machine's GPUs and reports the count to the kubelet, the Kubernetes agent on each machine,
which then advertises the GPUs as a resource alongside CPU and memory. For NVIDIA GPUs the
resource is named `nvidia.com/gpu`. A *pod*, the object in which Kubernetes runs one or more
containers, can ask for `nvidia.com/gpu: 1` in the same way it asks for two CPU cores, and
the *scheduler*, the component that chooses a machine for each new pod, places it only on a
machine with a free GPU. One unit is one whole physical GPU by default. Chapter 2 examines
what that unit contains and the ways a GPU can be shared or divided.

The second is a GPU-aware *container runtime*. A container normally sees none of the
machine's hardware devices, and its image does not contain the machine's GPU driver. When a
pod has been granted a GPU, the runtime adds the GPU's device files and the driver's
libraries to the container just before it starts, and a program inside the container can
then open the GPU.

Figure I.1 follows one request for a GPU past both pieces.

<figure>
<img src="figures/gpu-request.svg" alt="A pod whose limits ask for nvidia.com/gpu: 1 goes to the scheduler, which picks a machine that advertises a free unit. On that machine the kubelet starts the pod's containers, the device plugin reports the number of GPUs to the kubelet, and the GPU container runtime adds the GPU's device files and driver libraries to the container.">
<figcaption><b>Figure I.1</b> A pod asks for one GPU, the scheduler finds a machine that advertises one, and the two vendor pieces on that machine count the GPUs and open one to the container.</figcaption>
</figure>

Every example was developed and tested on a single-node cluster created with kind, a tool
that runs Kubernetes nodes as Docker containers. Appendix A builds that cluster and installs
both pieces on it.

The book assumes the reader can read Go and Rust and has used containers and kubectl. Each
Kubernetes concept is defined where it is first needed.

## Running the code

The book and all of its code live in the
[`gpu-accelerated-kubernetes`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/tree/prep-v2/gpu-accelerated-kubernetes) directory of the
[cracking-the-systems-programming-interview](https://github.com/arpanpathak/cracking-the-systems-programming-interview)
repository on GitHub:

```console
$ git clone https://github.com/arpanpathak/cracking-the-systems-programming-interview.git
$ cd cracking-the-systems-programming-interview/gpu-accelerated-kubernetes
```

Every listing is included from a file under `code/`, so the printed code is the code that
runs. The link above each listing opens its file on GitHub.

- [`code/go`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/tree/prep-v2/gpu-accelerated-kubernetes/code/go) is one Go module. `informer` is the in-memory model from chapter 1, `gpujob`
  is the controller from section 1.1, built on controller-runtime, and `gpuusage` is the
  GPU accounting tool from chapter 2:

  ```console
  $ cd code/go
  $ go run ./informer
  $ go run ./gpujob/cmd/controller
  ```

- [`code/rust`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/tree/prep-v2/gpu-accelerated-kubernetes/code/rust) is one Cargo workspace with the same three programs as packages. `gpujob`
  and `gpuusage` are built on kube-rs:

  ```console
  $ cd code/rust
  $ cargo run -p informer
  $ cargo run -p gpujob
  ```

- [`code/manifests`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/tree/prep-v2/gpu-accelerated-kubernetes/code/manifests) holds the example objects that both controllers act on.
- [`code/gpu-sharing`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/tree/prep-v2/gpu-accelerated-kubernetes/code/gpu-sharing) holds the CUDA programs and manifests for chapter 2.
- [`code/jetson-gpu`](https://github.com/arpanpathak/cracking-the-systems-programming-interview/tree/prep-v2/gpu-accelerated-kubernetes/code/jetson-gpu) holds the script, manifests, and test program for the kind cluster in
  Appendix A.

Every program has the same name in both trees. From chapter 3 on, each is one directory under
`code/go`, run with `go run ./<name>`, and one package under `code/rust`, run with
`cargo run -p <name>`:

| Chapter | Programs |
|---|---|
| 1. Keeping a local copy of the cluster | `informer` |
| 1.1 A GPU job controller on a real cluster | `gpujob` |
| 2. What one GPU means | `gpuusage`, and the CUDA programs `gpu_info` and `gpu_load` |
| 3. Knowing which machines are alive | `heartbeats`, `phi`, `leaseagent`, `leasewatch` |
| 4. A control plane for a fleet of hosts | `fleethealth`, `fencing` |
| 5. Kubernetes in a new cloud account | `provisioner` |
| 6. Virtual machines on Kubernetes | `migration` |
| 7. Collective communication and training failures | `allreduce` |
| 8. Placing jobs on GPUs | `gangsched` |
| 9. Counting across replicas | `counter` |
| 10. A content-addressed artifact store | `cas` |
| 11. A command-line tool for Windows, macOS, and Linux | `gpuctl` |

The programs of chapters 4 to 10 are models: they need no cluster, finish in well under a
second, and print the same output in Go and in Rust. The output shown in each chapter is
included from `code/output`, where a run of the program wrote it.

Each chapter has the same shape. It states the problem and works a small example by hand,
draws the design, and lists the types and the rules they keep in a box headed "Low-level
design". The code follows in short parts, each beside the text that explains it, and the
complete programs are printed at the end.

The Go module declares Go 1.26, and the Rust programs need Rust 1.89 or later, the
minimum version of the kube crate. The controllers need a Kubernetes cluster in the
current kubeconfig context.

The diagrams are drawn by `tools/draw_figures.py` and the animations by
`tools/animations.py`; `make figures` and `make animations` run them, and their output in
`src/figures` is part of the repository. The book's build removes the `ANCHOR` comments
that mark the parts of each program, with `tools/strip_anchors.py`, so Python 3 has to be
installed.

To read the book in a browser, install mdBook and run:

```console
$ mdbook serve --open
```
