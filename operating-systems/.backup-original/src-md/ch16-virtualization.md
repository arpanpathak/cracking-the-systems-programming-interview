# 16. Virtualization and Containers

One physical machine runs many independent workloads. Two mechanisms
divide it: the virtual machine, which duplicates the operating system
under a hypervisor, and the container, which shares one kernel and
fences workloads with namespaces and limits. This chapter explains
both from the primitives the earlier chapters built — privilege
levels, page tables, processes — and states where each belongs.

<div class="callout glance">
<span class="label">At a glance</span>

- A hypervisor uses a higher privilege level to run several guest
  kernels, each with its own page tables and devices.
- A container is a process — or a tree of processes — whose view of
  the kernel's objects is filtered by namespaces and limited by
  control groups.
- Virtual machines isolate strongly and cost more; containers cost
  little and isolate at the kernel's discretion.

</div>

## 16.1 Virtual machines

Chapter 2 collapsed the CPU's privilege levels to two. Real hardware
has more, and a **hypervisor** occupies the level above the kernel.
The guests — complete operating systems with their own kernels — run
where a normal kernel would, believing they own the machine, while
the hypervisor intercepts the instructions that would reveal
otherwise.

The interception is the whole mechanism. When a guest kernel updates
its page table base register, the hypervisor traps the instruction,
consults its own mapping, and installs a translation that points the
guest's pages at real physical frames — two levels of page tables,
one the guest maintains, one the hypervisor maintains. When a guest
writes a device register, the hypervisor traps that too and forwards
the operation to a virtual device. When a guest's timer interrupt
fires, the hypervisor decides how much real time the guest actually
received. The guest kernel runs unchanged; the hypervisor is the
machine.

The cost is the boundary: privileged operations that a native kernel
performs directly become traps into the hypervisor. Modern CPUs
shrink the cost with hardware support — nested page tables that walk
both levels in one pass, direct device assignment — but the shape
remains: a virtual machine pays a tax on everything privileged, in
exchange for the strongest isolation the hardware can express.

<div class="callout keyidea">
<span class="label">Key idea</span>

A hypervisor is an operating system whose processes are operating
systems. Its page tables map guest frames to real frames, its
scheduler schedules guest kernels, and its traps intercept every
privileged instruction a guest attempts.

</div>

## 16.2 Containers

A container is the opposite bet: one kernel, many fenced views. No
second operating system runs; instead, the host kernel attaches
filters to a process tree, and the filters are the container.

The first filter class is **namespaces**, which restrict what a
process can see of the kernel's shared objects. A PID namespace gives
the process its own numbering of the process table — its first child
is PID 1, and no other namespace's processes exist, as Figure 16-2
draws. A mount namespace gives it its own filesystem tree. A network
namespace gives it its own interfaces and routing table. A user
namespace maps its root user to an unprivileged user on the host.
Each namespace is a view, not a copy: the underlying objects are the
host's, shared, and the namespace only decides which are visible and
under what names.

<figure>
<img src="diagrams/ch16_namespaces.svg" alt="Two PID namespaces presenting their own numbering over one host process table"/>
</figure>

The second filter class is **control groups** — cgroups — which
restrict what a process can *consume*: CPU time, memory, block and
network I/O. A container with a 512 MiB memory limit is a cgroup
whose processes the kernel's page reclaimer treats as one accounting
unit; exceeding the limit means reclaim and, at the edge, the
out-of-memory path, scoped to the container rather than the host.

Container startup is therefore a sequence of the primitives this
book has already covered. Clone a process with new namespace flags —
`fork`'s configurable cousin. Set up the cgroup limits. Pivot the
mount namespace to the container's filesystem image. Execute the
container's entrypoint. What Docker and Kubernetes orchestrate is
exactly this sequence, distributed across machines, with image
layers — the sparse files of Chapter 12 — underneath.

<figure>
<img src="diagrams/ch16_vm_vs_container.svg" alt="Virtual machines stack guest OSes on a hypervisor; containers share one host kernel with namespaces and cgroups"/>
</figure>

## 16.3 Choosing between them

The choice is isolation against cost, and the two mechanisms sit at
the ends of the trade. A virtual machine isolates at the hardware's
strongest boundary: separate kernels, separate page tables owned by
the hypervisor, and no shared kernel code at all. A vulnerability in
one guest's kernel compromises that guest, not its neighbors. The
price is a second operating system's memory, boot, and privileged
overhead per instance.

A container isolates at the kernel's discretion. The boundary is the
host kernel's namespace and cgroup logic, which is large, subtle,
and — because it is shared — the single point whose compromise
reaches every container. The price paid is near zero: a container
starts in milliseconds, and a thousand of them cost little more than
a thousand process trees.

Data centers run both, in layers: virtual machines fence tenants from
one another, because tenant trust is exactly the thing a shared
kernel cannot assume; containers pack each tenant's workloads inside
its virtual machines, because within one tenant the shared kernel's
efficiency is worth its boundary. The layering is not redundancy; it
is the two mechanisms each doing the job it is best at.

<div class="callout caution">
<span class="label">Watch out</span>

A container is not a security boundary of the same strength as a
virtual machine. Namespaces filter visibility and cgroups filter
consumption; neither is designed to stop an attacker who has code
running against a kernel vulnerability. Placing untrusted tenants in
containers without a hypervisor beneath them is the industry's most
repeated isolation error.

</div>

<div class="callout summary">
<span class="label">Summary</span>

- Hypervisors use a higher privilege level and two-level page tables
  to run complete guest kernels; the tax is on privileged
  operations.
- Containers share one kernel; namespaces filter visibility, cgroups
  filter consumption, and the container is a configured process
  tree.
- VMs give hardware-strength isolation at real cost; containers give
  near-zero cost at the kernel's discretion.
- Production stacks layer them: hypervisors between tenants,
  containers within a tenant.
- Chapter 17 returns to the bare metal the hypervisor partitions:
  sockets, NUMA, accelerators, and the cache lines that still matter
  underneath everything.

</div>
