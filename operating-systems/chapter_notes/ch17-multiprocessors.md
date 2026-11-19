# Chapter 17: Multiprocessor Systems and Hardware Accelerators

As computing scale increases, the idealized model of a single, uniform pool of memory and a set of identical cores gives way to more complex architectures. Large-scale systems are characterized by Non-Uniform Memory Access (NUMA) topologies and the integration of specialized hardware accelerators, both of which impose unique constraints on operating system design and application performance.

## 17.1 NUMA Topologies and Locality Optimization

In a Non-Uniform Memory Access (NUMA) architecture, the system is composed of multiple processor sockets, each possessing its own local memory controller and associated DRAM. While any core can access any memory address in the system, the latency and bandwidth of an access depend heavily on the physical distance between the core and the target memory. Accessing memory local to a socket is fast, whereas accessing memory across the inter-socket interconnect incurs a significant latency penalty.

To mitigate the performance degradation caused by remote memory access, the operating system employs two primary strategies:
- **Processor Affinity:** The scheduler attempts to maintain thread-to-socket locality by scheduling threads on the cores of the socket that currently holds their most frequently accessed data.
- **First-Touch Placement:** The kernel optimizes initial memory allocation by mapping a virtual page to a physical frame on the socket where the thread that first writes to that page is currently executing. This ensures that the data and the thread that uses it are co-located from the outset.

## 17.2 Cache Coherence and the False Sharing Phenomenon

The complexity of modern multiprocessor systems is further compounded by the requirement for hardware-level **cache coherence**. To ensure that all cores perceive a consistent view of memory, the hardware must manage the movement and invalidation of cache lines across the various levels of the cache hierarchy. When a core writes to a memory location, it must obtain exclusive ownership of the corresponding cache line, which necessitates invalidating any existing copies of that line in the caches of other cores.

This mechanism introduces the performance hazard known as **false sharing**. False sharing occurs when two or more threads, which are logically operating on independent variables, happen to access data that resides within the same 64-byte cache line. Because the hardware manages coherence at the granularity of the cache line, the threads inadvertently trigger a continuous "ping-pong" effect, where the cache line is repeatedly transferred between cores. This results in massive, unintended synchronization overhead and can degrade performance by an order of magnitude. The remedy is to use architectural alignment (e.g., `alignas(64)`) to ensure that frequently written, independent variables reside on distinct cache lines.

## 17.3 Hardware Accelerators: Scheduling and Data Orchestration

Beyond general-purpose CPUs, modern systems increasingly rely on specialized accelerators, such as GPUs, to handle computationally intensive workloads. An accelerator is essentially a secondary processor with its own execution model and memory subsystem, typically connected via the PCIe bus. The operating system's role in managing accelerators involves three critical domains:

- **Workload Scheduling:** The driver and runtime must manage the queuing and dispatching of tasks to the accelerator, effectively implementing a scheduling policy for non-CPU resources.
- **Data Orchestration:** Because an accelerator's memory is distinct from main system memory, data must be transferred via Direct Memory Access (DMA). To minimize the high overhead of PCIe transactions, applications should batch data transfers rather than issuing many small requests. Furthermore, the kernel must "pin" memory (ensuring it is not paged out) before a DMA transfer to prevent corruption or the need for intermediate copies.
- **Security and Isolation:** The driver must enforce isolation between different processes using the accelerator, ensuring that one process cannot access the private memory or state of another, thereby extending the principles of privilege and protection to heterogeneous hardware.
