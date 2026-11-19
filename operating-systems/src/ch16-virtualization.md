# 16. Virtualization and Containerization

Modern computing environments frequently run multiple isolated workloads on a single physical machine. This is achieved through two distinct architectural approaches: virtual machines (VMs), which provide heavy-weight isolation through hardware emulation, and containers, which provide light-weight isolation through kernel-level namespace and resource-control mechanisms.

## 16.1 Virtual Machines and Hypervisor Orchestration

A virtual machine provides a high-fidelity simulation of hardware, allowing one or more "guest" operating systems to run concurrently on a single physical host. This is managed by a **hypervisor**, a software layer that operates at a privilege level even more elevated than the guest kernels.

The hypervisor mediates the guest's interaction with the underlying hardware through three primary mechanisms:
- **Two-Stage Address Translation:** To maintain isolation, the hypervisor manages a secondary layer of page tables. While the guest kernel manages the translation from virtual addresses to "guest physical" addresses, the hypervisor manages the translation from guest physical addresses to the actual machine frames. On modern processors, this is implemented in hardware via Extended Page Tables (EPT) or Nested Page Tables (NPT).
- **Device Virtualization:** The hypervisor intercepts privileged I/O operations, either by emulating a virtual device in software or by assigning a physical device directly to a guest.
- **CPU and Interrupt Scheduling:** The hypervisor acts as a meta-scheduler, allocating physical CPU time to guests and delivering virtualized hardware interrupts to their respective kernels.

Because each VM runs a complete operating system, they provide exceptional security isolation; a compromise of a guest kernel does not inherently grant access to the host or other guests. The trade-off is the significant computational and memory overhead required to maintain multiple full OS environments.

<figure>
<img src="figures/ch16_vm_vs_container.svg" alt="Virtual machines stack guest OSes on a hypervisor; containers share one host kernel with namespaces and cgroups"/>
</figure>

## 16.2 Containerization: Namespace and Resource Isolation

Containers represent a more lightweight approach to workload isolation. Rather than running a complete guest operating system, a container consists of a group of processes that share the single host kernel but are restricted in their visibility and resource consumption. This is achieved through two kernel-level mechanisms:

- **Namespaces:** These provide the mechanism for **visibility isolation**. Namespaces partition kernel resources so that a process sees only a subset of the system. Examples include **PID namespaces** (providing a private process numbering scheme), **mount namespaces** (providing a private file system hierarchy), **network namespaces** (providing isolated network stacks), and **user namespaces** (mapping user identities).
- **Control Groups (cgroups):** These provide the mechanism for **resource isolation**. Cgroups allow the kernel to enforce strict limits on the consumption of hardware resources, such as CPU cycles, memory capacity, and I/O bandwidth, preventing a single container from exhausting the host's capacity.

The lifecycle of a container is managed by a runtime that utilizes system calls like `clone` (with namespace flags), configures cgroups, sets the root directory for the mount namespace, and finally executes the target program via `execve`.

While containers offer near-native performance and rapid startup times, they offer weaker isolation than VMs, as all containers share the same host kernel and are thus vulnerable to kernel-level exploits.

<figure>
<img src="figures/ch16_namespaces.svg" alt="Two PID namespaces presenting their own numbering over one host process table"/>
</figure>

## 16.3 Architectural Synthesis in Cloud Computing

In modern cloud infrastructure, these two technologies are frequently combined to balance the competing requirements of security and efficiency. Cloud providers utilize virtual machines to establish strong security boundaries between different customers, ensuring that one tenant cannot compromise another. Within these secure VMs, customers deploy containers to manage their individual workloads with high density and minimal overhead.
