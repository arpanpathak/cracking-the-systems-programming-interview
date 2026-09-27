# 2. What one GPU means

So far our pods have asked for `nvidia.com/gpu: 1` as if a GPU were a single, indivisible
thing. In this chapter, we will open that unit up. We will first look at what a GPU is
made of and measure the one in our cluster, then see exactly what Kubernetes gives a pod
when it grants one unit. Then we will go through the ways a GPU can be shared or divided:
time-slicing, the Multi-Process Service, Multi-Instance GPU, virtual GPUs, and Dynamic
Resource Allocation. We will try time-slicing on our own cluster and measure what it
does.

## The programs in this chapter

We use four programs, two that run on the GPU and two that look at the cluster.

`gpu_info` and `gpu_load` are CUDA programs in `code/gpu-sharing`. We compile them on the
host with `nvcc`, the CUDA compiler, for the compute capability of our GPU, and link the
CUDA runtime library into each binary. Each binary then needs only the driver library,
`libcuda`, at run time, and that library is one of the files the NVIDIA container runtime
mounts into a GPU container (Appendix A). We copy both binaries into one image,
`gpu-sharing:1`, and run them in pods that request `nvidia.com/gpu`. When such a pod
starts, the device plugin tells the kubelet to set `NVIDIA_VISIBLE_DEVICES` in the
container, the NVIDIA runtime adds the GPU's device files and `libcuda`, and the CUDA
calls in our programs reach the GPU through them.

- `gpu_info` asks the CUDA runtime for the properties of the GPU it sees and prints them,
  one per line. It shows what one `nvidia.com/gpu` unit contains.
- `gpu_load` launches a compute-heavy kernel ten times, waits for all ten to finish, and
  prints the elapsed time. Several copies running at once show how much GPU time each one
  receives.

`gpuusage` is written in Go (`code/go/gpuusage`) and in Rust (`code/rust/gpuusage`). It is
an ordinary Kubernetes client that runs on our workstation. It lists every node and every
pod through the API server, adds up the `nvidia.com/gpu` units that running pods hold on
each node, and prints them next to the node's capacity. It shows the scheduler's view of
the GPU: how many units exist and who holds them. We run it in a second terminal, from
`code/go` with `go run ./gpuusage` or from `code/rust` with `cargo run -p gpuusage`, while
the pods from `code/gpu-sharing` run.

## What a GPU is made of

A GPU is a large number of simple processors grouped into *streaming multiprocessors*
(SMs). Each SM contains arithmetic units (the CUDA cores for ordinary floating-point and
integer work, and Tensor Cores for matrix multiplication), a large register file,
schedulers, and a block of fast on-chip memory that is used as shared memory and L1
cache. A CUDA program launches a *kernel*, a function that runs on the GPU, as a grid of
thread blocks. The GPU assigns each block to an SM, and the SM runs its threads in groups
of 32, called *warps*. An SM keeps many warps resident at once and switches between them
whenever one waits for memory, which is how a GPU hides memory latency: by having other
work ready, where a CPU would rely on large caches.

Memory is arranged in levels, from fastest and smallest to slowest and largest:

- registers, private to each thread;
- shared memory and L1 cache, one block per SM;
- the L2 cache, shared by all SMs;
- device memory: HBM on data center GPUs, GDDR on graphics cards, and, on integrated
  GPUs such as the Jetson's, the same LPDDR memory that the CPU uses.

Next to the SMs sit fixed-function engines. *Copy engines* move data between host memory
and device memory while kernels run, so transfers and computation can overlap. Video
decoders and encoders (NVDEC and NVENC) and JPEG decoders handle media without using the
SMs.

A *discrete* GPU is a separate card with its own memory, attached over PCIe or a
dedicated interconnect; a program copies data into that memory before a kernel can use
it. An *integrated* GPU sits on the same chip as the CPU and shares the system's memory
with it.

## Measuring our GPU

The CUDA runtime reports most of these properties through `cudaGetDeviceProperties`.
This program prints them, along with the current free and total device memory:

```cpp
{{#include ../code/gpu-sharing/gpu_info.cu}}
```

The image for this chapter holds `gpu_info` and a second program, `gpu_load`, which we
use later:

```dockerfile
{{#include ../code/gpu-sharing/Dockerfile}}
```

```console
$ cd code/gpu-sharing
$ /usr/local/cuda/bin/nvcc -O2 -arch=sm_87 -cudart static -o gpu_info gpu_info.cu
$ /usr/local/cuda/bin/nvcc -O2 -arch=sm_87 -cudart static -o gpu_load gpu_load.cu
$ docker build -t gpu-sharing:1 .
$ kind load docker-image gpu-sharing:1 --name gpu-lab
```

We run it in a pod that asks for one GPU:

```yaml
{{#include ../code/gpu-sharing/gpu-info-pod.yaml}}
```

```console
$ kubectl apply -f gpu-info-pod.yaml
$ kubectl logs gpu-info
device                      Orin
compute capability          8.7
integrated with the CPU     yes
streaming multiprocessors   8
max resident threads/SM     1536
registers per SM            65536
shared memory per SM        164 KiB
L2 cache                    2048 KiB
device memory (total)       15.3 GiB
device memory (free now)    1.8 GiB
copy engines                2
concurrent kernels          yes
managed memory              yes
```

The GPU in our cluster has 8 SMs. An Ampere SM of this generation has 128 CUDA cores,
which gives the 1,024 cores in NVIDIA's specification for the Orin NX, and each SM can
hold 1,536 threads at once, 12,288 for the whole GPU. All SMs share a 2 MiB L2 cache, and
two copy engines move data. For comparison, a data center H100 SXM5 has 132 SMs and
80 GB of HBM3 memory.

The memory lines show what "integrated" means in practice. The GPU's device memory is
the board's 15.3 GiB of LPDDR5, the same memory the operating system and every CPU
program use. Only 1.8 GiB was free when the pod ran, because other programs on the board
were using the rest. On a discrete GPU, device memory belongs to the GPU alone; on an
integrated GPU, the amount available to a kernel depends on everything else running on
the machine.

## What one unit gives a pod

By default, the device plugin advertises one `nvidia.com/gpu` unit for each physical
GPU, and a pod that is granted a unit receives the whole device: every SM, all of its
memory, and all of its engines. Kubernetes counts extended resources as integers. A pod
cannot ask for half a GPU, and the node never hands out more units than it advertises.

`gpuusage` shows the same accounting that the scheduler does. It sums the GPU limits of
every pod that is bound to a node and has not finished, and compares the sum with the
node's allocatable units. The Go version uses client-go's typed clientset:

```go
{{#include ../code/go/gpuusage/main.go}}
```

The Rust version uses kube-rs:

```rust
{{#include ../code/rust/gpuusage/src/main.rs}}
```

Both programs list the nodes and the pods with one request each, keep the pods that hold
GPU units, and group them by node. A pod counts from the moment the scheduler binds it to
a node until it succeeds or fails; a finished pod has released its units even though the
object still exists. With no GPU pods running, both print the same report:

```console
$ go run ./gpuusage
NODE                   CAPACITY  ALLOCATABLE  IN USE  FREE
gpu-lab-control-plane  1         1            0       1
$ cargo run -p gpuusage
NODE                   CAPACITY  ALLOCATABLE  IN USE  FREE
gpu-lab-control-plane  1         1            0       1
```

This is simple and gives each pod exclusive use of its GPU, but it is coarse. An
inference service that keeps 5 percent of the SMs busy still holds the entire GPU, and
the other 95 percent sits idle while other pods wait. The rest of this chapter covers the
ways to share or divide a GPU, each with a different trade-off between isolation and
flexibility.

## Sharing by taking turns: time-slicing

Without further configuration, a GPU runs work from one process's CUDA context at a time.
When several processes use the same GPU, the driver switches between their contexts,
giving each a slice of time on all the SMs. *Time-slicing* in Kubernetes uses exactly
this: the device plugin advertises each GPU as several units, called replicas, and every
pod that receives a replica of the same GPU gets the same device.

NVIDIA's GPU Operator documentation is direct about the cost: "Unlike Multi-Instance GPU
(MIG), there is no memory or fault-isolation between replicas." Every pod sees all of
the GPU's memory, one pod can allocate so much that the others fail, and, in the words of
the device plugin's README, workloads run "in the same fault-domain as of all the others
(meaning if one workload crashes, they all do)".

We can measure the effect. `gpu_load` launches a kernel ten times, each launch keeping
1,024 blocks of 256 threads busy with 200,000 multiply-adds per thread, and prints how
long the work took:

```cpp
{{#include ../code/gpu-sharing/gpu_load.cu}}
```

A Job runs four copies of it at once, each asking for one `nvidia.com/gpu`:

```yaml
{{#include ../code/gpu-sharing/gpu-load-job.yaml}}
```

With the device plugin as configured in Appendix A, the node advertises one unit. Three
of the four pods wait in Pending while the first runs:

```console
$ kubectl apply -f gpu-load-job.yaml
$ kubectl get pods -l job-name=gpu-load
gpu-load-5wf4d Completed
gpu-load-mbw4m Pending
gpu-load-w46sf Pending
gpu-load-w9h7x ContainerCreating
$ go run ./gpuusage
NODE                   CAPACITY  ALLOCATABLE  IN USE  FREE
gpu-lab-control-plane  1         1            1       0
  default/gpu-load-w9h7x holds 1 on gpu-lab-control-plane
```

`gpuusage` shows the reason: the node's one unit is held by the running pod, so the
scheduler has nowhere to place the others. Each pod prints its start time and its result.
They ran one after another, about three seconds apart, and each needed about 620
milliseconds of GPU time:

```console
23:29:59.987 gpu-load-5wf4d: no error, 612 ms
23:30:03.466 gpu-load-w9h7x: no error, 622 ms
23:30:06.487 gpu-load-w46sf: no error, 616 ms
23:30:09.495 gpu-load-mbw4m: no error, 634 ms
```

Time-slicing is switched on through the device plugin's configuration file. This
ConfigMap advertises each GPU as four replicas:

```yaml
{{#include ../code/gpu-sharing/time-slicing-config.yaml}}
```

The plugin reads the file named by its `CONFIG_FILE` setting. This manifest is the
plugin from Appendix A with the ConfigMap mounted and `CONFIG_FILE` set:

```yaml
{{#include ../code/gpu-sharing/device-plugin-time-sliced.yaml}}
```

```console
$ kubectl apply -f time-slicing-config.yaml -f device-plugin-time-sliced.yaml
$ kubectl get node -o jsonpath='{.items[0].status.allocatable.nvidia\.com/gpu}'; echo
4
```

The same GPU now counts as four units. Running the same Job again, all four pods start
at once:

```console
$ kubectl delete job gpu-load
$ kubectl apply -f gpu-load-job.yaml
$ kubectl get pods -l job-name=gpu-load
gpu-load-dk7h8 Running
gpu-load-grrkx Running
gpu-load-s4lb2 Running
gpu-load-t28sd Running
$ cargo run -p gpuusage
NODE                   CAPACITY  ALLOCATABLE  IN USE  FREE
gpu-lab-control-plane  4         4            4       0
  default/gpu-load-dk7h8 holds 1 on gpu-lab-control-plane
  default/gpu-load-grrkx holds 1 on gpu-lab-control-plane
  default/gpu-load-s4lb2 holds 1 on gpu-lab-control-plane
  default/gpu-load-t28sd holds 1 on gpu-lab-control-plane
```

```console
23:30:25.915 gpu-load-dk7h8: no error, 2198 ms
23:30:25.996 gpu-load-s4lb2: no error, 2231 ms
23:30:26.048 gpu-load-grrkx: no error, 2249 ms
23:30:26.052 gpu-load-t28sd: no error, 2260 ms
```

Each pod now took about 2,230 milliseconds for the same work, roughly 3.6 times as long
as it took alone. The four pods took turns on the same 8 SMs. Time-slicing added no
compute: it changed how many pods can hold the GPU at once and how long each one waits.
Together, the four runs occupied the GPU for about 2.3 seconds, close to the
4 × 620 = 2,480 milliseconds they needed one after another.

The scheduler now believes the node has four GPUs. A pod that asks for two replicas gets
two units of the same GPU and no more of its time; the plugin's `failRequestsGreaterThanOne`
option rejects such requests to make that explicit. To switch time-slicing off, we apply
the original plugin manifest again:

```console
$ kubectl apply -f ../jetson-gpu/device-plugin.yaml
$ go run ./gpuusage
NODE                   CAPACITY  ALLOCATABLE  IN USE  FREE
gpu-lab-control-plane  1         1            0       1
```

## Running kernels side by side: MPS

Time-slicing runs one process's kernels at a time. NVIDIA's MPS documentation states the
underlying rule: without MPS, work "from work queues belonging to different CUDA
contexts cannot execute concurrently". A process whose kernels fill only a few SMs leaves
the rest idle during its slice.

The *Multi-Process Service* (MPS) removes that restriction. An MPS server becomes "the
clients' shared connection to the GPU and owner of the GPU scheduling resources", and
kernels from different processes then run on the GPU at the same time. MPS also lets an
administrator limit each client: `CUDA_MPS_ACTIVE_THREAD_PERCENTAGE` caps the share of the
GPU's threads a client may use, and `CUDA_MPS_PINNED_DEVICE_MEM_LIMIT` caps the memory it
may allocate. Each client has its own GPU address space, but error containment is
limited: a fatal fault is reported to all clients on the affected GPU, "without
indicating which client generated the error".

The device plugin can hand out MPS shares in the same way as time-slicing replicas, each
with an equal fraction of the GPU's memory and compute. Its README marks this support as
experimental and limits it to whole GPUs without MIG. MPS runs on Tegra devices such as
ours with restrictions, so we do not use it here.

## Dividing the hardware: Multi-Instance GPU

Time-slicing and MPS share one GPU in software. *Multi-Instance GPU* (MIG) divides it in
hardware. According to NVIDIA's MIG user guide, a GPU can be "securely partitioned into
up to seven separate GPU Instances", and within each instance "the on-chip crossbar
ports, L2 cache banks, memory controllers, and DRAM address busses are all assigned
uniquely to an individual instance". SMs, copy engines, and decoders are divided as
well. An instance therefore keeps its cache and memory bandwidth "even if other tasks
are thrashing their own caches or saturating their DRAM interfaces", and a fault in one
instance does not affect the others.

Instances come in fixed sizes, called profiles. A profile name gives the number of
compute slices and the memory. The profiles of an H100 with 80 GB, from the MIG user
guide:

```text
profile      memory   SMs    copy engines   instances per GPU
-----------  -------  -----  -------------  -----------------
1g.10gb      1/8      1/7    1              7
1g.20gb      1/4      1/7    1              4
2g.20gb      2/8      2/7    2              3
3g.40gb      4/8      3/7    3              2
4g.40gb      4/8      4/7    4              1
7g.80gb      full     7/7    8              1
```

The device plugin exposes MIG instances according to its `MIG_STRATEGY` setting: with
the `single` strategy every instance is advertised as `nvidia.com/gpu`, and with the
`mixed` strategy each profile gets its own resource name, such as `nvidia.com/mig-1g.10gb`.
A pod then asks for a slice of known size and gets guaranteed memory and bandwidth.

MIG requires a supporting GPU: the A100, H100, H200, and B200 families support seven
instances, and smaller models support fewer. The Orin in our cluster does not support
MIG.

## Virtual GPUs for virtual machines: vGPU

Everything so far shares a GPU between containers on the same operating system. NVIDIA's
vGPU software shares a GPU between virtual machines: it "enables multiple virtual
machines (VMs) to have simultaneous, direct access to a single physical GPU". A vGPU is
either time-sliced, in which case the GPU "performs the work for each VM serially" under a
scheduler that can give each VM a fixed or equal share, or backed by a MIG instance, in
which case VMs run in parallel with MIG's isolation. Clusters that run virtual machines
on Kubernetes can use vGPUs to give each VM its own GPU device.

## Asking for GPUs by their properties: Dynamic Resource Allocation

The device plugin model reduces every GPU to an integer count of an opaque name. A pod
cannot ask for "a GPU with at least 40 GB of memory", and two containers cannot
explicitly share one GPU. *Dynamic Resource Allocation* (DRA), generally available since
Kubernetes 1.34, replaces the count with structured requests:

- a driver publishes the devices on each node, with their attributes such as model and
  memory size, as *ResourceSlice* objects;
- a *DeviceClass* groups devices of one kind, for example all NVIDIA GPUs;
- a pod refers to a *ResourceClaim*, which requests devices from a class and can filter
  them with expressions over their attributes; several pods can refer to the same claim
  to share its devices.

The scheduler then allocates concrete devices that satisfy each claim. Our cluster
already serves these APIs:

```console
$ kubectl api-resources --api-group=resource.k8s.io
NAME                     SHORTNAMES   APIVERSION           NAMESPACED   KIND
deviceclasses                         resource.k8s.io/v1   false        DeviceClass
devicetaintrules                      resource.k8s.io/v1   false        DeviceTaintRule
resourceclaims                        resource.k8s.io/v1   true         ResourceClaim
resourceclaimtemplates                resource.k8s.io/v1   true         ResourceClaimTemplate
resourceslices                        resource.k8s.io/v1   false        ResourceSlice
```

A driver has to publish the devices, and NVIDIA's DRA driver describes its GPU support
as not yet official: "While some GPU allocation features can be tried out, they are not
yet officially supported." Our cluster therefore stays with the device plugin.

## Choosing a method

```text
method          what a pod gets                 memory isolated   faults isolated
--------------  ------------------------------  ----------------  ---------------
whole GPU       the entire device               yes               yes
time-slicing    turns on the entire device      no                no
MPS             a share of threads and memory   by limits         partly
MIG             a hardware partition            yes               yes
vGPU            a device inside a VM            yes               yes
```

Whole GPUs suit training jobs that keep a GPU busy. Time-slicing suits development and
light, trusted workloads that tolerate each other. MPS suits many small inference
processes that each use part of the SMs. MIG suits multi-tenant clusters that need
guaranteed memory and bandwidth for each tenant. vGPU suits workloads that must run in
virtual machines.

## References

- NVIDIA Multi-Instance GPU user guide:
  <https://docs.nvidia.com/datacenter/tesla/mig-user-guide/index.html>
- NVIDIA GPU Operator, time-slicing GPUs in Kubernetes:
  <https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/latest/gpu-sharing.html>
- NVIDIA device plugin for Kubernetes, "Shared Access to GPUs":
  <https://github.com/NVIDIA/k8s-device-plugin>
- NVIDIA Multi-Process Service documentation: <https://docs.nvidia.com/deploy/mps/index.html>
- NVIDIA vGPU software user guide:
  <https://docs.nvidia.com/vgpu/latest/grid-vgpu-user-guide/index.html>
- Kubernetes, Dynamic Resource Allocation:
  <https://kubernetes.io/docs/concepts/resource-management/dynamic-resource-allocation/>
- Kubernetes v1.34: DRA has graduated to GA:
  <https://kubernetes.io/blog/2025/09/01/kubernetes-v1-34-dra-updates/>
- DRA Driver for NVIDIA GPUs: <https://github.com/NVIDIA/k8s-dra-driver-gpu>
- NVIDIA Jetson Orin technical specifications:
  <https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/>
