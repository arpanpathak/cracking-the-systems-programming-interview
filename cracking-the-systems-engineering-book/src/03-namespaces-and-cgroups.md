# 3. Namespaces and cgroups: What a Container Actually Is {#namespaces-and-cgroups}

A container is, at minimum, a set of processes running in new namespaces,
constrained by cgroup limits. Nothing about that sentence involves a new
kernel, a hypervisor, or a new kind of process. It uses the `task_struct` from
Chapter 1 and two further mechanisms this chapter covers: namespaces, which
change what a process can see, and cgroups, which change what a process can
use.

## What a namespace isolates

Namespaces give processes a different view of system resources. `clone()` and
`unshare()` accept namespace flags; `setns()` joins an existing namespace.

| Namespace | Flag | Isolates |
|---|---|---|
| Mount | `CLONE_NEWNS` | Mount points and filesystem view |
| PID | `CLONE_NEWPID` | Process IDs; PID 1 inside is not host PID 1 |
| Network | `CLONE_NEWNET` | Network interfaces, routes, firewall, sockets |
| UTS | `CLONE_NEWUTS` | Hostname and NIS domain |
| IPC | `CLONE_NEWIPC` | System V IPC and POSIX message queues |
| User | `CLONE_NEWUSER` | User and group IDs (unprivileged namespaces) |
| Cgroup | `CLONE_NEWCGROUP` | View of the cgroup hierarchy root |
| Time | `CLONE_NEWTIME` | Clock offsets |

A process inside a new PID namespace sees itself as PID 1, but the host sees
it with another PID. `ps` inside a container only shows processes in that PID
namespace by default.

The mechanism is smaller than the vocabulary suggests. The kernel keeps one
namespace object per type, a `struct uts_namespace`, a `struct pid_namespace`,
and so on, and each task holds a pointer to one of them. Every system call
that resolves a name, `gethostname`, `kill`, `mount`, `socket`, resolves it
through the namespace the calling task points at. Creating a namespace
allocates a fresh object and repoints one task; nothing is copied, and nothing
is isolated behind a hypervisor boundary. That is why a container starts in
milliseconds, and also why a kernel bug reachable through a namespace is a
host bug rather than a guest bug.

UTS is the smallest namespace to demonstrate, because it holds a single field.
The program below asks for its own copy of that field.

```c
/* ns.c: the UTS namespace holds the hostname, so a process can have its own. */
#define _GNU_SOURCE
#include <errno.h>
#include <sched.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int main(void)
{
    char before[256];
    char after[256];

    if (gethostname(before, sizeof before) != 0) {
        perror("gethostname");
        return 1;
    }

    if (unshare(CLONE_NEWUTS) != 0) {
        printf("unshare(CLONE_NEWUTS) = -1 errno=%d (%s)\n", errno, strerror(errno));
        printf("this needs CAP_SYS_ADMIN, so try:\n");
        printf("  unshare --user --map-root-user --uts ./ns\n");
        return 1;
    }

    if (sethostname("in-a-namespace", 14) != 0) {
        perror("sethostname");
        return 1;
    }
    gethostname(after, sizeof after);

    printf("hostname before: %s\n", before);
    printf("hostname after : %s\n", after);
    return 0;
}
```

Run as an ordinary user it fails:

```text
$ gcc -O2 -o ns ns.c && ./ns
unshare(CLONE_NEWUTS) = -1 errno=1 (Operation not permitted)
this needs CAP_SYS_ADMIN, so try:
  unshare --user --map-root-user --uts ./ns
```

Creating a namespace is privileged, because namespaces are what confinement is
built from. The route available to an unprivileged user is the user
namespace: it can be created without privilege, and inside it the user's uid
is mapped to root, which grants the capability needed to create the rest.

```text
$ unshare --user --map-root-user --uts ./ns
hostname before: yahboom
hostname after : in-a-namespace
```

That pair of results explains how `docker run` works for an ordinary user,
and why rootless containers exist. The runtime does not perform a privileged
operation on the user's behalf; the user namespace grants the privileges it
needs inside a scope it cannot escape.

## cgroups v2: accounting and limiting

cgroup v2, mounted at `/sys/fs/cgroup`, organizes processes into a tree. The
controllers that matter most: `cpu.max`, written as `$MAX_PERIOD $PERIOD`, so
`50000 100000` allocates 50% of one CPU; `memory.max`, a hard memory limit,
with `memory.current` and `memory.events` reporting usage and OOM counts;
`memory.high`, a throttle applied before the hard limit; `io.max`, I/O
bandwidth and IOPS limits; `pids.max`, the maximum number of tasks and
threads; and `cpuset.cpus`/`cpuset.mems`, CPU and memory affinity.

A cgroup that has child cgroups cannot also hold processes directly, the
no-internal-processes rule, and `cgroup.subtree_control` delegates a
controller to the children. The kernel charges a process to the cgroup that
contains it, and when a process forks, the child stays in the parent's cgroup
unless moved. `memory.events` carries `oom_kill`, `max`, and `high` counters.

```bash
cat /proc/self/cgroup
cat /sys/fs/cgroup/memory.max
cat /sys/fs/cgroup/memory.current
cat /sys/fs/cgroup/memory.events
cat /sys/fs/cgroup/cpu.max
cat /sys/fs/cgroup/pids.max
systemd-cgls
```

## From container image to running container

When Kubernetes schedules a Pod, the kubelet asks the CRI runtime, typically
containerd, to start a sandbox (the pause container) and then the application
containers. `containerd` receives the CRI request and builds an OCI bundle
from the image: a rootfs assembled from image layers, and a config file
listing mounts, environment, command, namespaces, cgroup path, and devices. It
invokes `runc` (or another OCI runtime) via `runc create`. `runc` creates the
namespaces with `clone()`/`unshare()`, sets cgroup membership, applies mounts
and `pivot_root` into the container rootfs, and starts the container process
via `exec`. The process then runs with a restricted view; PID 1 inside the
container is normally the application itself or a small init process.

```text
docker run / kubelet → containerd
  containerd: pull image, assemble OCI bundle (rootfs + config)
  containerd: runc create   (namespaces, cgroup, mounts, pivot_root)
  runc: exec                (starts PID 1 inside the new namespaces)
```

The pause, or sandbox, container holds the network namespace and other shared
infrastructure, which is what lets the application containers in one Pod share
`localhost` and volumes.

Chapter 7 picks this sequence apart in more detail for Docker specifically.
The point to take from it here: `docker run` and a Pod's containers are the
same mechanism at the bottom, namespaces plus cgroups plus a rootfs, wired up
by different daemons above `runc`.

## Container runtime device injection

A container by default has no access to `/dev/nvidia*` and no CUDA driver
user-space libraries. The GPU Operator and the NVIDIA Container Toolkit
automate that access. At a low level, `nvidia-container-cli` detects the host
driver version and CUDA compatibility, mounts the driver's user-space
libraries such as `libcuda.so` and `libnvidia-ml.so` into the container,
creates and bind-mounts the GPU device nodes, `/dev/nvidia0`,
`/dev/nvidiactl`, `/dev/nvidia-uvm`, `/dev/nvidia-modeset`, and any MIG
devices, into the container, and sets environment variables such as
`NVIDIA_VISIBLE_DEVICES` and `NVIDIA_DRIVER_CAPABILITIES`.

The container still runs on the host kernel; the driver's kernel module lives
on the host. The container gets the same kernel driver plus matching
user-space libraries, so the driver version on the host and the CUDA version
inside the container have to be compatible with each other.

The device plugin, not the container runtime, decides which GPUs are assigned.
The kubelet calls the plugin's `Allocate` RPC after scheduling; the plugin
returns device IDs and environment variables, and the runtime uses them to
inject the devices. Chapter 16 covers the device plugin protocol in full.

## Containers against virtual machines

| Aspect | Container | Virtual machine |
|---|---|---|
| Isolation boundary | Kernel namespaces, cgroups, seccomp | Hardware virtualization (KVM) |
| Kernel | Shared host kernel | Separate guest kernel |
| Boot time | Milliseconds (process start) | Seconds (kernel boot) |
| Device access | Mediated by runtime and device cgroup | Virtual devices or PCIe passthrough |
| Attack surface | Syscalls filtered by seccomp/AppArmor | Full kernel interface exposed to the guest |
| GPU options | Device plugin plus container runtime | vGPU, MIG, or PCIe passthrough |

A container shares the host kernel, so `uname` inside it matches the host, but
it runs in its own PID namespace, so `ps` only sees the PIDs inside that
namespace. A VM runs a separate kernel on virtualized hardware, which is
stronger isolation at the cost of a slower boot and no sharing of the host
kernel's resources. GPU cloud platforms use both: Kubernetes Pods with device
plugins and MIG for most workloads, and dedicated GPU instances or VMs for
tenants that need the harder isolation boundary.

## References

- The `namespaces(7)`, `cgroups(7)`, `unshare(2)`, and `clone(2)` man pages.
- The Open Container Initiative runtime specification, for what `runc create`
  actually constructs.
- containerd's architecture documentation, for the CRI-to-OCI path this
  chapter follows.
