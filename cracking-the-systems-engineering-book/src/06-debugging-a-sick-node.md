# 6. Debugging a Sick Linux Node {#debugging-a-sick-node}

Every mechanism in the previous five chapters shows up as a symptom before it
shows up as a cause. A Pod stuck in `Pending`, a container stuck in
`CrashLoopBackOff`, a node reporting `NotReady`: each is a kernel object,
process state, memory limit, or network path from earlier chapters, observed
from outside instead of read from the source. This chapter is the diagnostic
order that turns a symptom back into one of those mechanisms.

## Triage order

The order runs from the node down to the accelerator, because each layer's
tools only mean something once the layer above it has been ruled out. Node
availability comes first: `kubectl get node`, `kubectl describe node`. Then
load and resource baselines: `uptime`, `free -h`, `df -h`, `top`. Then kernel
and device messages: `dmesg -T | tail`. Then the container runtime: `crictl ps
-a`, `journalctl -u containerd`. Then the kubelet itself: `journalctl -u
kubelet`, and the contents of `/var/lib/kubelet`. Then application logs:
`kubectl logs`, `kubectl describe pod`. And only once a Pod is confirmed
scheduled and running does a GPU-specific check, `nvidia-smi`, device plugin
logs, allocatable resources, Xid and ECC errors, mean anything.

## Pods stuck in `Pending`

`Pending` means the scheduler has not placed the Pod. The usual causes: no
node has enough CPU, memory, or GPU; no node matches the Pod's `nodeSelector`,
affinity, or tolerations; `nvidia.com/gpu` is missing from every node's
allocatable resources; a `ResourceQuota` or `LimitRange` in the namespace
blocks admission; a `PersistentVolumeClaim` is unbound, which fails scheduling
after node filtering has already run; a node is tainted `NoSchedule` and the
Pod carries no matching toleration; or the scheduler itself is down or marked
unschedulable.

```bash
kubectl describe pod <pod>
kubectl get nodes -o wide
kubectl describe node <node>
kubectl get events -A --sort-by=.lastTimestamp
kubectl get pvc
```

## Pod scheduled but stuck in `ContainerCreating`

At this stage the kubelet is involved rather than the scheduler. An image
pull failure shows up in `kubectl describe pod`'s events. A storage mount
failure shows up there too, and in `journalctl -u kubelet`. A runtime start
failure shows up in `crictl ps -a` and `journalctl -u containerd`. A device
plugin allocation failure shows up in `kubectl describe pod` as `Failed to
create pod sandbox` or `Allocate failed`.

## Pod in `CrashLoopBackOff`

`kubectl logs <pod> --previous` shows the crash reason from the terminated
container rather than the one currently restarting. Exit code 137 is
`SIGKILL`, most often an OOM kill or a failed liveness probe; exit code 143 is
`SIGTERM`. If exit code 137 comes with `OOMKilled` in the Pod's status, the
memory limit and `memory.events` from Chapter 2 are where to look next. If a
liveness probe is failing instead, `kubectl describe pod` names the probe
failure directly.

## GPU node cannot allocate GPUs

The checks run in a fixed order, because each one rules out a different
layer. First, is the driver visible on the host at all:

```bash
nvidia-smi
```

If it is not, the driver module is not loaded, or the node needs a reboot
after a driver install. Second, is the device plugin running:

```bash
kubectl get pods -n gpu-operator -l app=nvidia-device-plugin-daemonset
kubectl logs -n gpu-operator -l app=nvidia-device-plugin-daemonset
```

Third, does the node actually advertise the resource:

```bash
kubectl describe node | grep -A5 'nvidia.com/gpu'
```

A missing `Allocatable` entry means plugin registration did not complete.
Fourth, does the Pod's request match: `nvidia.com/gpu` is an extended
resource, so it must appear in `limits`, and Kubernetes requires `requests`
equal `limits` for extended resources. Fifth, does runtime injection actually
work inside the container:

```bash
kubectl exec <pod> -- nvidia-smi
```

If the binary is missing there, the container toolkit or GPU Operator did not
configure runtime hooking correctly. Sixth, and only after the first five have
passed, check for hardware or kernel errors:

```bash
dmesg | grep -i xid
dmesg | grep -i nvidia
nvidia-smi -q -d ECC
nvidia-smi -q -d PAGE_RETIREMENT
```

Xid errors are messages the NVIDIA driver emits for GPU-level faults, and
different Xid numbers mean different things. Xid errors alongside ECC errors
are a strong signal of a hardware or driver fault rather than a Kubernetes
configuration problem, and the order above exists so that a misconfiguration
is ruled out before hardware is blamed.

## High CPU with no obvious process

```bash
top -b -n1 -H | head -20
pidstat 1
perf top
cat /proc/loadavg
ps -eo pid,stat,wchan:30,comm
```

The `wchan` column names the kernel function a task is blocked in. A process
sitting in state `R` with high CPU may simply be spinning rather than blocked
at all; `perf top` samples where the time is going, and a stack trace can be
captured directly:

```bash
perf record -F 99 -g -p <pid> -- sleep 10
perf report
```

## Performance tools by layer

| Layer | Tool | What to look for |
|---|---|---|
| CPU | `top`, `pidstat -u`, `perf top` | `%usr` vs `%sys`, context switches, runnable threads |
| CPU scheduler | `/proc/pressure/cpu`, `cat /sys/fs/cgroup/cpu.stat` | Runnable pressure, throttling events |
| Memory | `free`, `/proc/pressure/memory` | PSI, anonymous vs. file-backed memory, swap, OOM events |
| Disk | `iostat -x`, `pidstat -d`, `/proc/pressure/io` | Await, `%util`, per-process I/O volume |
| Network | `sar -n DEV`, `ss`, `tcpdump`, `ethtool -S` | Drops, retransmits, queue saturation |
| Syscalls | `strace -f -tt` | Blocked calls, `EAGAIN` spin loops |
| Tracing | `perf trace`, `bpftrace`, `ftrace` | Kernel-level explanations |
| Containers | `crictl stats`, `systemd-cgtop` | Per-Pod and per-container resource use |

Pressure Stall Information, `/proc/pressure/{cpu,memory,io}`, reports the
fraction of time tasks spent waiting on a resource, which is a more
actionable number than a raw utilization percentage: a disk at 100% util
might still have room, while non-zero I/O pressure means something is
actually waiting on it. `bpftrace` reaches further than `strace` when the
question is systemic rather than per-process:

```bash
bpftrace -e 'tracepoint:sched:sched_process_exec { printf("%s %s\n", comm, args->filename); }'
bpftrace -e 'tracepoint:syscalls:sys_enter_openat { printf("%s %s\n", comm, str(args->filename)); }'
grep oom_kill /sys/fs/cgroup/memory.events
```

## The page cache is not a leak

The page cache holds file contents in RAM. Reads that hit it skip disk
entirely; writes are buffered in it and flushed back later. `free` reporting
most memory "used" by this cache is expected behavior, not a resource
problem, because the kernel reclaims it on demand. Dropping the page cache
manually is rarely a real performance fix: it discards data that was cached
because it was actually being used, and the next read pays the disk latency
that the cache existed to avoid.

## References

- The Kubernetes documentation on debugging Pods and debugging running Pods.
- The `perf`, `bpftrace`, and `strace` man pages and their respective project
  documentation.
- The kernel documentation on Pressure Stall Information, under
  `Documentation/accounting/psi.rst`.
