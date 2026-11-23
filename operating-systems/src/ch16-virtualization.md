# 16. Virtualization and Containerization

Modern cloud infrastructure packs dozens of mutually untrusted customer workloads onto a single physical server while preserving the illusion that each tenant owns a dedicated machine. Systems engineers achieve this multi-tenancy through two distinct architectural mechanisms: **hardware Virtual Machines (`VM`s)**, which virtualize the physical processor and memory controller beneath complete guest kernels, and **containers**, which partition visibility and resource quotas inside a single shared host kernel.

## 16.1 Virtual Machines and Hypervisor Orchestration

A **virtual machine** executes an unmodified guest operating system (such as Linux or Windows) inside an isolated hardware environment synthesized by a **hypervisor** (such as Linux **Kernel-based Virtual Machine (`KVM`)**, Xen, VMware ESXi, or Apple Virtualization.framework). Early software-only hypervisors faced a difficult architectural problem on x86: several sensitive instructions behaved differently in unprivileged rings instead of trapping, forcing complex binary translation.

Modern processors resolve this directly in silicon by introducing a dedicated hypervisor privilege tier orthogonal to Ring 0 through Ring 3 (Figure 16-1):
- **On x86-64 (**Intel Virtualization Technology (`VT-x`)** / **AMD Virtualization (`AMD-V`)**):** The processor divides execution into **Virtual Machine Extensions (`VMX`)** Root mode (where the host kernel and hypervisor run) and `VMX` Non-Root mode (where the guest kernel runs at guest Ring 0 and guest applications run at guest Ring 3). Each **Virtual Central Processing Unit (`vCPU`)** is backed by an in-memory **Virtual Machine Control Structure (`VMCS`)** storing guest registers, host registers, and an execution-control bitmap specifying which sensitive guest instructions (`cpuid`, `hlt`, `in`/`out`, `mov cr3`, **Extended Page Tables (`EPT`)** violations) trigger a hardware **VM-Exit** back into the hypervisor, and how `VMLAUNCH` or `VMRESUME` re-enters the guest (**VM-Entry**).
- **On ARM64:** The processor provides an explicit **Exception Level 2 (`EL2`)** strictly above the guest kernel (**Exception Level 1 (`EL1`)**) and guest applications (**Exception Level 0 (`EL0`)**).

<figure>
<img src="figures/ch16_vm_vs_container.svg" alt="Virtual machines stack guest OSes on a hypervisor; containers share one host kernel with namespaces and cgroups"/>
</figure>

### 16.1.1 Two-Stage Hardware Address Translation (`EPT` / `NPT`)

Virtualizing memory poses a subtle challenge: the guest kernel believes it owns physical **Dynamic Random-Access Memory (`DRAM`)** starting at address `0x0`, so it writes **Guest Physical Addresses (`GPA`s)** into its own page tables (`Guest CR3`). The host hypervisor cannot allow the guest kernel to map arbitrary **Host Physical Addresses (`HPA`s)** directly, or a compromised guest could read another tenant's `DRAM`.

Hardware-assisted virtualization solves this with **Two-Stage Address Translation** (Intel `EPT`, AMD **Nested Page Tables (`NPT`)**, and ARM64 **Stage-2 Translation**), illustrated in Figure 16-2:

<figure>
<img src="figures/ch16_ept_walk.svg" alt="Two-stage hardware virtualization showing Guest CR3 translating GVA to GPA and Hypervisor EPT translating every guest level GPA to Host Physical Address HPA"/>
</figure>

1. **Stage 1 (Controlled by Guest OS):** The guest application issues a **Guest Virtual Address (`GVA`)**. The **Memory Management Unit (`MMU`)** begins walking the guest's 4-level page table rooted at `Guest CR3` to translate `GVA -> GPA`.
2. **Stage 2 (Controlled by Host Hypervisor):** Every pointer stored inside the guest's **Page Map Level 4 (`PML4`)**, **Page Directory Pointer Table (`PDPT`)**, **Page Directory (`PD`)**, and **Page Table (`PT`)** is itself a *Guest Physical Address*, *not* a real host `DRAM` address. Before the `MMU` can read any of those four guest page-table entries, hardware must first walk the hypervisor's 4-level `EPT` (rooted at the **Extended Page Table Pointer (`EPTP`)** inside the `VMCS`) to translate that guest table's `GPA -> HPA`. Once the guest walk finally yields the data frame's `GPA`, hardware walks the `EPT` a fifth time to obtain the true host `DRAM` frame `HPA`.
3. **The 2D Page-Walk Cost and Hardware Mitigations:** Whereas a native 4-level **Translation Lookaside Buffer (`TLB`)** miss requires 4 `DRAM` accesses, a completely cold nested 4×4 walk requires up to `(4 * 4) + 4 + 4 = 24` memory reads (4 `EPT` reads for each of the 4 guest levels, 4 reads of the guest entries themselves, plus 4 `EPT` reads for the final data page). Hardware and hypervisors neutralize this penalty through direct `GVA -> HPA` `TLB` caching (delivering 1-cycle hits once resolved), **Virtual Processor Identifier (`VPID`)** / **Address Space Identifier (`ASID`)** tagging so VM-Exit and VM-Entry do not flush the `TLB`, and 2 MiB or 1 GiB host huge pages that shrink `EPT` depth and expand `TLB` reach by 512×.

### 16.1.2 Device Virtualization: Emulation, `virtio`, and Direct Passthrough

A guest kernel expects disk controllers and **Network Interface Cards (`NIC`s)** to exist on its virtual **Peripheral Component Interconnect Express (`PCIe`)** bus. Hypervisors provide virtual **Input/Output (`I/O`)** across three performance tiers:
- **Full Hardware Emulation:** Every guest **Memory-Mapped Input/Output (`MMIO`)** register write traps via a VM-Exit into user-space **Quick Emulator (`QEMU`)**, which emulates a legacy device (such as an Intel e1000 `NIC`). Compatible with any guest operating system, yet thousands of VM-Exits per second cap throughput severely.
- **Paravirtualization (`virtio`):** The guest runs a hypervisor-aware driver (`virtio-net`, `virtio-blk`) that places batches of `I/O` descriptors into shared-memory lock-free **virtqueues** in guest `DRAM` and notifies the host once per batch via a single doorbell write, amortizing VM-Exit cost across dozens of packets or disk requests.
- **Hardware Passthrough (**Virtual Function I/O (`VFIO`)** / **Single Root I/O Virtualization (`SR-IOV`)**):** Using an **Input-Output Memory Management Unit (`IOMMU`)** (Intel `VT-d`, AMD `AMD-Vi`, or ARM **System Memory Management Unit (`SMMU`)**) to translate device **Direct Memory Access (`DMA`)** addresses through the guest's `GPA -> HPA` mapping safely in silicon, the hypervisor assigns a physical **Graphics Processing Unit (`GPU`)** or `SR-IOV` `NIC` virtual function directly to the guest, achieving near-bare-metal latency and zero hypervisor data-plane overhead.

## 16.2 Containerization: Namespace and Resource Isolation

Running a complete guest kernel for every microservice duplicates hundreds of megabytes of kernel memory and requires seconds to boot. **Containers** (Docker, `containerd`, Kubernetes pods) take the opposite architectural path: every container shares the **single host Linux kernel**, executing as ordinary host processes constrained by three kernel subsystems (Figure 16-3):

1. **Namespaces (Visibility Isolation):** Partition global kernel tables via `clone()` flags or `unshare()` so processes inside a container perceive a private system view. `CLONE_NEWPID` assigns the container entrypoint `PID 1` internally while mapping it to an ordinary host `PID`; `CLONE_NEWNS` plus `pivot_root` isolates the mount table over an **Open Container Initiative (`OCI`)** image (`OverlayFS`); `CLONE_NEWNET` creates a private loopback, virtual Ethernet pair (`veth`), routing table, and **Extended Berkeley Packet Filter (`eBPF`)** firewall; and `CLONE_NEWUTS`, `CLONE_NEWIPC`, and `CLONE_NEWUSER` isolate hostnames, **Portable Operating System Interface (`POSIX`)** **Inter-Process Communication (`IPC`)** namespaces, and user/group mappings (mapping root `UID 0` inside a rootless container to an unprivileged host `UID`).
2. **Control Groups (`cgroups` v2, Resource Isolation):** Namespaces hide resources, whereas `cgroups` cap consumption via `/sys/fs/cgroup/` so a runaway container cannot starve noisy neighbors, enforcing hard ceilings on CPU bandwidth (`cpu.max`), physical memory (`memory.max`, triggering a container-scoped **Out-of-Memory (`OOM`)** kill when exceeded), process count (`pids.max`), and storage **Input/Output Operations Per Second (`IOPS`, `io.max`)**.
3. **Syscall Filtering (**Secure Computing Mode (`seccomp-bpf`)** and Linux Capabilities):** Because all containers share one host kernel, a vulnerability in an obscure system call threatens every container on the host. Runtimes drop unnecessary capabilities (`CAP_SYS_ADMIN`, `CAP_NET_RAW`) and attach a `seccomp-bpf` filter that intercepts system calls at Ring 0 entry and rejects disallowed numbers with `EPERM`.

<figure>
<img src="figures/ch16_namespaces.svg" alt="Two PID namespaces presenting their own numbering over one host process table"/>
</figure>

## 16.3 Architectural Synthesis in Cloud Computing

Virtual machines and containers solve complementary layers of the cloud isolation problem, so production platforms routinely combine both:

| Dimension | Virtual Machines (`KVM` / Firecracker) | Containers (Namespaces + `cgroups` v2) |
| :--- | :--- | :--- |
| **Isolation Boundary** | Hardware-enforced (`VMX` Non-Root + `EPT` + `IOMMU`); distinct guest kernel per `VM` | Software-enforced inside one shared host kernel |
| **Attack Surface** | Narrow hypervisor + `virtio` device boundary | Entire host Linux syscall surface (mitigated by `seccomp-bpf`) |
| **Startup Latency** | Hundreds of milliseconds (microVMs) to seconds (full `VM`s) | Tens of milliseconds (`clone` + `execve`) |
| **Memory Overhead** | Dedicated guest kernel + page cache per `VM` | Near zero (shared host kernel and page cache) |

Cloud providers place a hardware `VM` boundary between distinct tenants (using lightweight **microVMs** such as Firecracker or Kata Containers when serverless startup speed is required), and tenants deploy containers inside those `VM`s to package dependencies, orchestrate rolling upgrades, and pack microservices densely.

<div class="callout keyidea">
<span class="label">Key idea</span>

Virtual machines isolate tenants in silicon (`VMX` Non-Root, two-stage `EPT`/`NPT`, and `IOMMU` `DMA` remapping) at the cost of a separate guest kernel; containers isolate processes inside one shared host kernel via namespaces, `cgroups` v2, and `seccomp-bpf` with near-zero memory overhead.

</div>

<div class="callout experiment">
<span class="label">Experiment</span>

On Linux, launch an isolated `PID` and mount namespace directly from the shell (`sudo unshare --pid --fork --mount-proc bash`) and run `ps aux`. Notice that `bash` perceives itself as `PID 1` inside the namespace while `ps` on the host still lists it under an ordinary host `PID`.

</div>

<div class="callout caution">
<span class="label">Common Pitfall</span>

Treating container namespaces as a hardware security boundary equivalent to a `VM`. Because every container shares one host kernel, a privilege-escalation bug in a single exposed system call compromises all sibling containers on the node unless mitigated by `seccomp-bpf`, capability dropping, or a microVM boundary.

</div>
