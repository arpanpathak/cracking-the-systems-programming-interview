# 16. Virtualization and Containers

A data center runs many independent workloads on each physical machine,
and these workloads must not interfere with one another. Two mechanisms
divide a machine among them. A **virtual machine** runs a complete
operating system of its own on simulated hardware. A **container** is a
group of ordinary processes that share the kernel of the host but have a
restricted view of the system.

In this chapter, we explain both mechanisms in terms of the privilege
levels, page tables, and processes of earlier chapters. We then compare
their costs and the isolation that each provides. This chapter contains
no listings.

<div class="callout glance">
<span class="label">This chapter covers</span>

- hypervisors and guest operating systems
- two-stage address translation
- namespaces, with the PID namespace as an example
- control groups (cgroups)
- the steps that start a container
- isolation and cost of virtual machines and containers

</div>

Figure 16-1 shows the two mechanisms side by side. With virtual machines,
each application runs on its own guest operating system, and a hypervisor
divides the hardware among the guests. With containers, all applications
run on one host kernel.

<figure>
<img src="figures/ch16_vm_vs_container.svg" alt="Virtual machines stack guest OSes on a hypervisor; containers share one host kernel with namespaces and cgroups"/>
</figure>

## 16.1 Virtual machines

In Chapter 2, we used only two privilege levels, but processors have
more. A **hypervisor** is software that runs at a level more privileged
than an operating system kernel. Above it run one or more **guests**. Each
guest is a complete operating system with its own kernel, which runs as
if it controlled a whole machine.

Most instructions of a guest execute directly on the CPU. Certain
operations, however, cause the CPU to leave the guest and enter the
hypervisor, in the same way that a trap takes a program into the kernel.
The hypervisor handles the operation and resumes the guest. Three such
cases are important.

- **Memory.** A guest kernel maintains page tables that translate virtual
  addresses into what the guest believes are physical addresses. The
  hypervisor maintains a second set of tables that translate those *guest
  physical* addresses into real frames. Current processors perform both
  translations in hardware. Intel calls this feature Extended Page Tables,
  and AMD calls it Nested Page Tables. Each guest can therefore access
  only the frames that the hypervisor has assigned to it.
- **Devices.** When a guest writes to the register of a device, the
  hypervisor intercepts the write and applies it to a *virtual device*
  that it implements in software. Alternatively, the hypervisor can assign
  a real device to one guest for its exclusive use.
- **Time.** The hypervisor schedules guests on the physical cores, much as
  a kernel schedules threads, and delivers timer interrupts to each guest.

Each entry into the hypervisor takes time, and each guest needs memory for
its own kernel and system services. A virtual machine is therefore more
expensive than a process. In return, guests share no kernel code, so a
fault or a security hole in the kernel of one guest does not affect the
other guests.

<div class="callout keyidea">
<span class="label">Key idea</span>

A hypervisor does for operating systems what a kernel does for processes.
It maps the memory of each guest to real frames, schedules the guests on
the cores, and handles the privileged operations that a guest cannot
perform by itself.

</div>

## 16.2 Containers

A container does not run a second operating system. It consists of
processes on the host kernel for which the kernel applies two kinds of
restrictions.

**Namespaces** restrict what a process can see. The kernel keeps global
tables of processes, mounted file systems, network interfaces, and users.
A namespace gives a group of processes a view of one such table that is
limited to their own entries.

- In a **PID namespace**, processes are numbered separately. The first
  process in the namespace has PID 1, and processes outside the namespace
  are invisible. Figure 16-2 shows two PID namespaces. Each maps its own
  PIDs 1 and 2 to entries of the host process table.
- A **mount namespace** has its own tree of mounted file systems.
- A **network namespace** has its own network interfaces and routing
  table.
- A **user namespace** maps user IDs. A process can be root inside the
  namespace and an unprivileged user on the host.

A namespace does not copy the objects of the kernel. The processes of a
container are entries in the process table of the host, and the namespace
only determines which entries a process can see and under which numbers.

<figure>
<img src="figures/ch16_namespaces.svg" alt="Two PID namespaces presenting their own numbering over one host process table"/>
</figure>

**Control groups**, or **cgroups**, restrict what a group of processes can
consume. A cgroup can limit CPU time, memory, and the rate of disk and
network I/O. For example, when a container has a memory limit of 512 MiB,
the kernel counts the pages of all its processes together. When the total
reaches the limit, the kernel first tries to reclaim pages from the group.
If that is not enough, it terminates a process of the group, and the rest
of the host is unaffected.

A container runtime starts a container with system calls that we have
mostly met already.

1. It creates a process with `clone`, a variant of `fork` that accepts
   flags for creating new namespaces.
2. It places the process in a cgroup and sets the limits.
3. It changes the root of the mount namespace to the file system image of
   the container.
4. It calls `execve` to run the main program of the container.

Tools such as Docker and Kubernetes automate these steps and distribute
container images to many machines.

## 16.3 Choosing between them

The two mechanisms differ in the strength of their isolation and in their
cost.

A virtual machine is isolated by the hardware. Each guest has its own
kernel, and the hypervisor controls the page tables that determine which
frames a guest can access. An attacker who takes over the kernel of one
guest has gained control of that guest only. The cost is the memory and
startup time of a full operating system for each instance, and additional
time for operations that enter the hypervisor.

A container is isolated by the host kernel. Starting a container means
starting a few processes, which takes milliseconds, and a thousand
containers need little more memory than their processes do. However, all
containers on a host make system calls to the same kernel. That kernel is
large, and a flaw in it can give a process in one container access to all
the others.

Cloud providers commonly combine the two. They separate customers from
one another with virtual machines, because customers do not trust each
other. Inside its virtual machines, each customer runs its workloads in
containers, because those workloads belong to one organization, and
containers use the machine more efficiently.

<div class="callout caution">
<span class="label">Watch out</span>

A container does not isolate as strongly as a virtual machine. Namespaces
limit what a process can see, and cgroups limit what it can consume, but a
process in a container still calls the host kernel directly. Code from
untrusted sources should not be separated from other workloads by
containers alone.

</div>

<div class="callout summary">
<span class="label">Summary</span>

- A hypervisor runs complete guest operating systems. It translates guest
  physical addresses to real frames, implements or assigns devices, and
  schedules the guests.
- A container is a group of processes on the host kernel. Namespaces limit
  what the processes can see, and cgroups limit what they can consume.
- Virtual machines provide stronger isolation at a higher cost per
  instance. Containers start quickly and cost little, but share one
  kernel.
- Many deployments run containers inside virtual machines.

In Chapter 17, we return to the hardware and study machines with many
cores and several processor sockets.

</div>
