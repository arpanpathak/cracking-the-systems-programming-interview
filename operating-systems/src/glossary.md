# Glossary of Architectural Terms & Abbreviations

Every systems abbreviation across the book links directly to its architectural card below. Each entry explains the physical or kernel constraint that motivates the mechanism, its exact role in hardware or software, and (where applicable) an idiomatic Rust 2024 snippet illustrating how systems code interacts with it.

<div class="md-glossary-grid">

<div id="term-abi" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">ABI</span><span class="md-term-full">Application Binary Interface</span></div>
  <p>Compiled machine code has no concept of source-level types or parameter names. The ABI fixes the binary contract across function and kernel boundaries: which registers hold arguments, which registers callees must preserve, stack alignment (16 bytes on x86-64 and ARM64), and how struct fields are laid out in memory. (Ch. 2, 8, 9)</p>
  <div class="md-term-rust">#[repr(C)]
struct SockAddrIn { family: u16, port: u16, addr: u32 }</div>
</div>

<div id="term-ack" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">ACK</span><span class="md-term-full">Acknowledgment (TCP)</span></div>
  <p>Because IP networks drop and reorder packets freely, TCP tracks every transmitted byte by sequence number. Setting the ACK flag tells the sender the next byte offset expected, advancing the sliding window and cancelling retransmission timers for all prior bytes. (Ch. 13, 14)</p>
</div>

<div id="term-amd-v" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">AMD-V</span><span class="md-term-full">AMD Virtualization</span></div>
  <p>Hardware hypervisor extensions on AMD x86-64 processors that isolate guest kernels without binary translation, pairing host/guest execution modes with Nested Page Tables (NPT) for two-stage memory translation. (Ch. 16)</p>
</div>

<div id="term-apfs" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">APFS</span><span class="md-term-full">Apple File System</span></div>
  <p>Copy-on-write, extent-based filesystem powering macOS and Apple platforms. Rather than overwriting metadata blocks in place, APFS writes new tree nodes and atomically swaps the container checkpoint, enabling instant zero-copy file clones and crash-consistent snapshots. (Ch. 12)</p>
</div>

<div id="term-api" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">API</span><span class="md-term-full">Application Programming Interface</span></div>
  <p>The source-level contract of types, signatures, preconditions, and error values exposed by a library or kernel wrapper. Whereas an API governs source compatibility, an ABI governs binary compatibility. (Ch. 1, 13)</p>
</div>

<div id="term-apic" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">APIC</span><span class="md-term-full">Advanced Programmable Interrupt Controller</span></div>
  <p>x86-64 interrupt routing fabric split into a system-wide IO-APIC (routing peripheral signals) and per-core Local APICs (delivering preemptive timer ticks and cross-core Inter-Processor Interrupts). (Ch. 2, 5)</p>
</div>

<div id="term-asic" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">ASIC</span><span class="md-term-full">Application-Specific Integrated Circuit</span></div>
  <p>Fixed-function silicon engineered for a single workload such as AES encryption, video encoding, or matrix multiplication, achieving orders-of-magnitude higher performance per watt than general-purpose CPU cores. (Ch. 17)</p>
</div>

<div id="term-asid" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">ASID</span><span class="md-term-full">Address Space Identifier</span></div>
  <p>An 8- or 16-bit hardware tag on ARM64 attached to every TLB entry so translations from distinct processes coexist safely across context switches without flushing the TLB. (Ch. 7, 16, 19)</p>
</div>

<div id="term-aslr" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">ASLR</span><span class="md-term-full">Address Space Layout Randomization</span></div>
  <p>Kernel security mitigation that randomizes the virtual base addresses of the stack, heap, shared libraries, and executable on every launch, preventing attackers from jumping to hardcoded gadget addresses. (Ch. 3, 7)</p>
</div>

<div id="term-avl" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">AVL</span><span class="md-term-full">Available for Operating System Use</span></div>
  <p>Bits [11:9] of an x86-64 Page Table Entry ignored by silicon and left free for kernel software metadata such as copy-on-write markers or swap-slot bookkeeping. (Ch. 7)</p>
</div>

<div id="term-avx" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">AVX</span><span class="md-term-full">Advanced Vector Extensions</span></div>
  <p>256-bit and 512-bit SIMD vector instructions on x86-64 that process 8 or 16 32-bit values in a single cycle, requiring properly aligned memory buffers to avoid split-line penalties. (Ch. 19)</p>
</div>

<div id="term-bsd" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">BSD</span><span class="md-term-full">Berkeley Software Distribution</span></div>
  <p>Unix lineage that introduced the socket API, reliable signal handlers, and the kqueue event subsystem, forming the POSIX layer of macOS and Darwin. (Ch. 10, 13, 14, 15)</p>
</div>

<div id="term-bss" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">BSS</span><span class="md-term-full">Block Started by Symbol</span></div>
  <p>Executable segment holding zero-initialized static globals. Storing only its byte length in the binary header rather than megabytes of zeros keeps executables small; the kernel maps demand-zeroed frames lazily on first touch. (Ch. 3)</p>
  <div class="md-term-rust">static ZERO_INIT: AtomicU64 = AtomicU64::new(0); // placed in .bss</div>
</div>

<div id="term-cas" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">CAS</span><span class="md-term-full">Compare-And-Swap</span></div>
  <p>Hardware atomic read-modify-write primitive that stores a new value into memory if and only if the current value equals an expected snapshot, forming the building block of lock-free algorithms and mutex fast paths. (Ch. 6)</p>
  <div class="md-term-rust">state.compare_exchange_weak(
    0, 1, Ordering::Acquire, Ordering::Relaxed
)</div>
</div>

<div id="term-cfs" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">CFS</span><span class="md-term-full">Completely Fair Scheduler</span></div>
  <p>Linux proportional-share scheduler tracking each runnable thread's weighted virtual runtime (vruntime) in a red-black tree and always dispatching the leftmost thread with the smallest vruntime. (Ch. 5)</p>
</div>

<div id="term-cisc" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">CISC</span><span class="md-term-full">Complex Instruction Set Computer</span></div>
  <p>Architecture family (such as x86-64) offering variable-length, memory-operating instructions like LOCK CMPXCHG that execute atomic read-modify-write sequences in a single instruction. (Ch. 6)</p>
</div>

<div id="term-cow" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">COW</span><span class="md-term-full">Copy-on-Write</span></div>
  <p>Virtual-memory technique that avoids eager physical copying during fork() by mapping parent and child PTEs to the same physical frames with Read/Write = 0. The first store triggers a hardware fault, prompting the kernel to duplicate only that single 4 KiB frame. (Ch. 3, 7, 11)</p>
  <div class="md-term-rust">// MAP_PRIVATE requests copy-on-write semantics across fork()
libc::mmap(ptr::null_mut(), len, PROT_READ | PROT_WRITE,
           MAP_PRIVATE | MAP_ANON, -1, 0)</div>
</div>

<div id="term-cpl" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">CPL</span><span class="md-term-full">Current Privilege Level</span></div>
  <p>Hardware privilege ring stored in the x86-64 code-segment register (Ring 3 for unprivileged user code; Ring 0 for kernel mode). Every privileged instruction and page-table U/S bit is checked against CPL in silicon. (Ch. 2, 9)</p>
</div>

<div id="term-cr2" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">CR2</span><span class="md-term-full">Control Register 2</span></div>
  <p>x86-64 hardware register into which the MMU latches the exact faulting 64-bit virtual address before vectoring into the kernel's Page Fault (#PF) handler, allowing the kernel to look up the offending Virtual Memory Area. (Ch. 7)</p>
</div>

<div id="term-cr3" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">CR3</span><span class="md-term-full">Control Register 3</span></div>
  <p>Privileged x86-64 register storing the 4 KiB-aligned physical base address of the active process's Level 4 (PML4) root page table. Context switching between processes reloads CR3; switching between sibling threads leaves CR3 untouched. (Ch. 3, 4, 7, 16)</p>
</div>

<div id="term-ddr" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">DDR4 / DDR5</span><span class="md-term-full">Double Data Rate Synchronous DRAM</span></div>
  <p>Main system memory modules attached to processor memory controllers, transferring data on both rising and falling clock edges to balance multi-gigabyte capacity against ~60 to 100 ns latency. (Ch. 17)</p>
</div>

<div id="term-dma" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">DMA</span><span class="md-term-full">Direct Memory Access</span></div>
  <p>Hardware mechanism allowing NVMe drives, NICs, and GPUs to read and write physical DRAM directly over PCIe while CPU cores execute other work, raising an interrupt only once the entire transfer completes. (Ch. 2, 3, 16, 17)</p>
</div>

<div id="term-dns" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">DNS</span><span class="md-term-full">Domain Name System</span></div>
  <p>Hierarchical naming service resolving hostnames into binary IPv4/IPv6 addresses, queried safely in Rust via ToSocketAddrs (wrapping POSIX getaddrinfo). (Ch. 14)</p>
  <div class="md-term-rust">use std::net::ToSocketAddrs;
let addrs: Vec&lt;_&gt; = "localhost:443".to_socket_addrs()?.collect();</div>
</div>

<div id="term-dram" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">DRAM</span><span class="md-term-full">Dynamic Random-Access Memory</span></div>
  <p>Off-chip volatile main memory storing bits in tiny capacitors refreshed every few milliseconds. Because a single DRAM miss stalls a 3 GHz core for 200+ cycles, systems software structures data for spatial locality inside L1/L2 caches. (Ch. 2, 5, 7, 8, 16, 17, 18, 19)</p>
</div>

<div id="term-dtlb" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">dTLB</span><span class="md-term-full">Data Translation Lookaside Buffer</span></div>
  <p>First-level core-private associative cache holding ~64 recent data-page translations (~0.5 to 1 cycle hit). With 4 KiB pages its reach is only 256 KiB, explaining why random access over larger buffers triggers translation stalls. (Ch. 7, 18)</p>
</div>

<div id="term-ebpf" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">eBPF</span><span class="md-term-full">Extended Berkeley Packet Filter</span></div>
  <p>In-kernel verified bytecode runtime allowing engineers to attach safe, JIT-compiled observability tracers and packet filters directly to kernel tracepoints without user-space context switches or kernel modules. (Ch. 16, 18)</p>
</div>

<div id="term-eevdf" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">EEVDF</span><span class="md-term-full">Earliest Eligible Virtual Deadline First</span></div>
  <p>Linux scheduler replacing CFS heuristics with explicit virtual deadlines, allowing short latency-sensitive tasks to preempt long-running CPU jobs cleanly while preserving long-term proportional fairness. (Ch. 5)</p>
</div>

<div id="term-el0" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">EL0 / EL1 / EL2</span><span class="md-term-full">ARM64 Exception Levels</span></div>
  <p>Hardware privilege hierarchy on ARM64: EL0 runs user applications, EL1 runs the operating system kernel, and EL2 runs the hypervisor beneath guest kernels. (Ch. 2, 7, 16)</p>
</div>

<div id="term-elf" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">ELF</span><span class="md-term-full">Executable and Linkable Format</span></div>
  <p>Standard binary container format on Linux specifying program headers that tell execve() exactly which file offsets map into the read-only text segment, initialized data segment, and zero-filled BSS segment. (Ch. 3)</p>
</div>

<div id="term-eof" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">EOF</span><span class="md-term-full">End-of-File</span></div>
  <p>Condition reported when read() returns 0 bytes (never an error). On pipes and TCP sockets, EOF arrives only once every open write descriptor has been closed, making closing unused pipe ends after fork() mandatory. (Ch. 11, 13, 15)</p>
  <div class="md-term-rust">match stream.read(&amp;mut buf)? {
    0 =&gt; break, // peer closed write half (EOF)
    n =&gt; handle(&amp;buf[..n]),
}</div>
</div>

<div id="term-eoi" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">EOI</span><span class="md-term-full">End of Interrupt</span></div>
  <p>Register write issued by a top-half interrupt handler to the Local APIC or ARM GIC signaling that hardware may clear the active vector bit and deliver subsequent interrupts of equal or lower priority. (Ch. 2)</p>
</div>

<div id="term-ept" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">EPT</span><span class="md-term-full">Extended Page Tables</span></div>
  <p>Intel hardware second-stage page tables controlled by the hypervisor that translate every Guest Physical Address (GPA) into a Host Physical Address (HPA), isolating tenant VMs in silicon while avoiding software shadow page tables. (Ch. 16)</p>
</div>

<div id="term-far-el1" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">FAR_EL1</span><span class="md-term-full">Fault Address Register (EL1)</span></div>
  <p>ARM64 kernel system register capturing the faulting virtual address whenever a translation or permission abort occurs (the architectural counterpart to x86-64 CR2). (Ch. 7)</p>
</div>

<div id="term-fifo" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">FIFO</span><span class="md-term-full">First-In, First-Out</span></div>
  <p>Strict arrival-order queueing discipline preserving element ordering in pipes, bounded producer-consumer rings, and hardware store buffers. (Ch. 5, 6, 11, 19)</p>
  <div class="md-term-rust">use std::collections::VecDeque;
let mut q = VecDeque::with_capacity(64);
q.push_back(job);
let next = q.pop_front(); // O(1) FIFO dequeue</div>
</div>

<div id="term-fin" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">FIN</span><span class="md-term-full">Finish (TCP)</span></div>
  <p>TCP control flag signaling that the sender will transmit no further bytes, initiating graceful half-close teardown while still allowing in-flight data in the reverse direction to drain cleanly. (Ch. 13, 14)</p>
</div>

<div id="term-gddr" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">GDDR</span><span class="md-term-full">Graphics Double Data Rate</span></div>
  <p>High-bandwidth memory soldered directly onto discrete GPU cards, optimized for wide parallel streaming throughput rather than single-thread CPU latency. (Ch. 17)</p>
</div>

<div id="term-gic" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">GIC</span><span class="md-term-full">Generic Interrupt Controller</span></div>
  <p>ARM64 interrupt routing architecture (GICv3) connecting SoC peripherals through a central Distributor and per-core Redistributors to CPU interrupt inputs. (Ch. 2)</p>
</div>

<div id="term-gid" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">GID</span><span class="md-term-full">Group Identifier</span></div>
  <p>Numeric Unix security identifier stored in a process's credential struct and in every file inode, governing group-level read, write, and execute permissions. (Ch. 3, 12)</p>
</div>

<div id="term-gp" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">#GP</span><span class="md-term-full">General Protection Fault</span></div>
  <p>x86-64 hardware exception (Vector 13) raised immediately when unprivileged code executes a privileged instruction or dereferences a non-canonical 64-bit pointer whose bits [63:48] fail to replicate bit 47. (Ch. 7)</p>
</div>

<div id="term-gpa" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">GPA</span><span class="md-term-full">Guest Physical Address</span></div>
  <p>Physical address perceived by a VM guest kernel starting at 0x0. Hardware translates every GPA into a true Host Physical Address (HPA) via EPT or NPT so guests cannot touch sibling tenants' DRAM. (Ch. 16)</p>
</div>

<div id="term-gpu" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">GPU</span><span class="md-term-full">Graphics Processing Unit</span></div>
  <p>Throughput-oriented processor packing thousands of parallel arithmetic lanes to accelerate graphics, machine learning, and scientific kernels, connected either over PCIe or Unified Memory. (Ch. 16, 17)</p>
</div>

<div id="term-gva" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">GVA</span><span class="md-term-full">Guest Virtual Address</span></div>
  <p>Virtual address issued inside a VM, translated across two hardware stages: GVA to GPA via Guest CR3, and GPA to HPA via hypervisor EPT/NPT. (Ch. 16)</p>
</div>

<div id="term-hbm" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">HBM</span><span class="md-term-full">High Bandwidth Memory</span></div>
  <p>3D-stacked, ultra-wide memory co-packaged on an interposer beside AI/HPC accelerators, delivering multi-terabyte-per-second bandwidth far exceeding host PCIe links. (Ch. 17)</p>
</div>

<div id="term-hpa" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">HPA</span><span class="md-term-full">Host Physical Address</span></div>
  <p>Actual physical DRAM bus address on the bare-metal server hosting virtual machines, known solely to the host hypervisor and IOMMU. (Ch. 16)</p>
</div>

<div id="term-hpc" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">HPC</span><span class="md-term-full">High-Performance Computing</span></div>
  <p>Large-scale numerical and scientific workloads where NUMA first-touch placement, cache-line alignment, and accelerator memory bandwidth govern scalability. (Ch. 17)</p>
</div>

<div id="term-http" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">HTTP</span><span class="md-term-full">Hypertext Transfer Protocol</span></div>
  <p>Application-layer request/response protocol demonstrating explicit message framing (Content-Length or chunked framing) above byte-stream TCP (HTTP/1.1, HTTP/2) or multiplexed QUIC/UDP (HTTP/3). (Ch. 14)</p>
</div>

<div id="term-idt" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">IDT / IDTR</span><span class="md-term-full">Interrupt Descriptor Table &amp; Register</span></div>
  <p>256-entry hardware dispatch table on x86-64 mapping every exception (#GP, #PF) and hardware IRQ vector to its Ring 0 kernel handler entry point, located by the IDTR register. (Ch. 2)</p>
</div>

<div id="term-io" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">I/O</span><span class="md-term-full">Input / Output</span></div>
  <p>Data movement between processor memory and external subsystems (storage, network, pipes, terminals). Because I/O latency is orders of magnitude slower than CPU cycles, systems software relies on user-space buffering and event-driven multiplexing. (Ch. 9, 12, 13, 14, 15, 16, 18)</p>
  <div class="md-term-rust">use std::io::{BufWriter, Write};
let mut w = BufWriter::with_capacity(64 * 1024, file);
w.write_all(b"batched syscall\n")?;</div>
</div>

<div id="term-iommu" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">IOMMU</span><span class="md-term-full">Input-Output Memory Management Unit</span></div>
  <p>Hardware translation unit (Intel VT-d, AMD-Vi, ARM SMMU) placed between PCIe devices and physical DRAM to translate device DMA addresses through per-device page tables, preventing rogue or passthrough devices from corrupting host memory. (Ch. 16)</p>
</div>

<div id="term-iops" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">IOPS</span><span class="md-term-full">Input/Output Operations Per Second</span></div>
  <p>Storage performance metric counting discrete random block read/write operations completed per second, bounded per container via cgroups v2 io.max. (Ch. 16)</p>
</div>

<div id="term-ip" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">IP / IPv4 / IPv6</span><span class="md-term-full">Internet Protocol</span></div>
  <p>Best-effort, connectionless network-layer packet routing protocol (32-bit addresses in IPv4; 128-bit in IPv6). Because IP may drop or reorder packets, reliability is delegated to transport protocols like TCP or QUIC. (Ch. 11, 13, 14)</p>
</div>

<div id="term-ipc" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">IPC</span><span class="md-term-full">Inter-Process Communication / Instructions Per Cycle</span></div>
  <p>In OS architecture (Ch. 11, 15, 16), IPC denotes kernel-mediated channels (pipes, shared memory, Unix sockets) bridging isolated address spaces. In CPU profiling (Ch. 18), IPC measures retired instructions per clock cycle via hardware PMU counters.</p>
</div>

<div id="term-ipi" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">IPI</span><span class="md-term-full">Inter-Processor Interrupt</span></div>
  <p>Hardware interrupt dispatched by one CPU core to sibling cores via the APIC or GIC, used to wake idle schedulers and execute synchronous cross-core TLB shootdowns during munmap() or mprotect(). (Ch. 2, 7)</p>
</div>

<div id="term-irq" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">IRQ</span><span class="md-term-full">Interrupt Request</span></div>
  <p>Asynchronous hardware signal raised by a peripheral device (timer, NIC, NVMe controller) to preempt current execution and invoke a kernel top-half handler. (Ch. 2)</p>
</div>

<div id="term-isa" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">ISA</span><span class="md-term-full">Instruction Set Architecture</span></div>
  <p>Formal hardware/software boundary defining machine instructions, register files, memory-ordering guarantees, and exception semantics (such as x86-64 and ARM64). (Ch. 2)</p>
</div>

<div id="term-jit" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">JIT</span><span class="md-term-full">Just-In-Time Compilation</span></div>
  <p>Runtime compilation emitting executable machine instructions into anonymous mmap pages, transitioning permissions from PROT_READ | PROT_WRITE to PROT_READ | PROT_EXEC via mprotect() to honor W^X invariants. (Ch. 8)</p>
</div>

<div id="term-kpti" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">KPTI</span><span class="md-term-full">Kernel Page-Table Isolation</span></div>
  <p>Mitigation against speculative Meltdown attacks that unmaps most kernel memory while in Ring 3, forcing a CR3 page-table switch on every system call and making hardware PCID tagging essential to prevent TLB thrashing. (Ch. 7, 9)</p>
</div>

<div id="term-kvm" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">KVM</span><span class="md-term-full">Kernel-based Virtual Machine</span></div>
  <p>Linux kernel subsystem transforming Linux into a hardware-assisted hypervisor by driving Intel VT-x, AMD-V, or ARM64 EL2 directly for guest vCPUs. (Ch. 16)</p>
</div>

<div id="term-llc" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">LLC</span><span class="md-term-full">Last-Level Cache</span></div>
  <p>Largest on-chip cache tier (typically shared L3, 8 to 128 MiB, ~12 to 20 ns) serving as the final filter before crossing the memory controller to off-chip DRAM. (Ch. 5, 18)</p>
</div>

<div id="term-llvm" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">LLVM</span><span class="md-term-full">Low-Level Virtual Machine</span></div>
  <p>Modular optimizing compiler backend powering Clang and rustc, known for heavy use of contiguous index-addressed arena allocators for intermediate representation graphs. (Ch. 8)</p>
</div>

<div id="term-lru" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">LRU</span><span class="md-term-full">Least Recently Used</span></div>
  <p>Cache eviction policy discarding the entry untouched for the longest interval, implemented in O(1) with a hash map plus doubly-linked list and approximated by OS kernels using PTE Accessed bits. (Ch. 7, 19)</p>
</div>

<div id="term-mesi" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">MESI / MOESI</span><span class="md-term-full">Modified-Exclusive-Shared-Invalid</span></div>
  <p>Hardware cache-coherency state machine tracking every 64-byte cache line across cores. Writing to a Shared line forces a Read-For-Ownership invalidation across sibling cores, which is the physical root cause of false sharing. (Ch. 2, 5, 6, 17)</p>
  <div class="md-term-rust">#[repr(align(64))] // isolate counters onto distinct MESI cache lines
struct PaddedCounter(AtomicU64);</div>
</div>

<div id="term-ml" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">ML</span><span class="md-term-full">Machine Learning</span></div>
  <p>Tensor- and bandwidth-intensive workloads that motivate discrete GPU DMA pinning on x86 servers and zero-copy Unified Memory Architectures on Apple Silicon. (Ch. 17)</p>
</div>

<div id="term-mmio" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">MMIO</span><span class="md-term-full">Memory-Mapped Input/Output</span></div>
  <p>Hardware design mapping peripheral device control registers into physical memory addresses (with PTE cache-disable bits set) so drivers command devices using ordinary load and store instructions. (Ch. 2, 7, 16)</p>
</div>

<div id="term-mmu" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">MMU</span><span class="md-term-full">Memory Management Unit</span></div>
  <p>Silicon state machine inside every CPU core that intercepts every virtual address, translates VPN to PFN via the TLB or 4-level page-table walk, verifies PTE permission bits, and raises #PF on any violation. (Ch. 2, 3, 7, 16)</p>
  <div class="md-term-rust">// Hardware translation invariant for 4 KiB (2^12 B) pages:
let vpn = va &gt;&gt; 12;
let offset = va &amp; 0xFFF;
let pa = (pfn &lt;&lt; 12) | offset;</div>
</div>

<div id="term-msi-x" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">MSI-X</span><span class="md-term-full">Message Signaled Interrupts Extended</span></div>
  <p>Modern PCIe interrupt mechanism letting a device signal specific CPU cores via targeted DMA writes rather than shared legacy IRQ wires, enabling per-core lock-free NIC receive queues. (Ch. 2)</p>
</div>

<div id="term-mtu" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">MTU</span><span class="md-term-full">Maximum Transmission Unit</span></div>
  <p>Largest packet payload a physical network link can carry without fragmentation (typically 1,500 bytes on Ethernet); sending a UDP datagram exceeding the path limit fails with EMSGSIZE. (Ch. 14)</p>
</div>

<div id="term-napi" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">NAPI</span><span class="md-term-full">New API (Linux Network Polling)</span></div>
  <p>Linux driver framework that masks per-packet NIC interrupts under heavy traffic and drains batches of frames inside NET_RX_SOFTIRQ, preventing interrupt livelock. (Ch. 2)</p>
</div>

<div id="term-neon" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">NEON</span><span class="md-term-full">ARM Advanced SIMD</span></div>
  <p>128-bit vector execution unit standard across ARM64 processors, saved and restored inside the kernel's thread_struct during context switches. (Ch. 3, 19)</p>
</div>

<div id="term-nic" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">NIC</span><span class="md-term-full">Network Interface Card</span></div>
  <p>Peripheral controller transferring Ethernet frames between the physical network cable and kernel ring buffers via PCIe DMA and MSI-X interrupts. (Ch. 2, 13, 16)</p>
</div>

<div id="term-nmi" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">NMI</span><span class="md-term-full">Non-Maskable Interrupt</span></div>
  <p>Highest-priority hardware interrupt that fires even when normal interrupts are disabled, enabling PMU sampling profilers to capture stack traces inside interrupt-masked kernel critical sections. (Ch. 18)</p>
</div>

<div id="term-npt" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">NPT</span><span class="md-term-full">Nested Page Tables</span></div>
  <p>AMD hardware two-stage virtualization page tables translating Guest Physical Addresses to Host Physical Addresses (functional equivalent of Intel EPT). (Ch. 16)</p>
</div>

<div id="term-npu" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">NPU</span><span class="md-term-full">Neural Processing Unit</span></div>
  <p>Dedicated silicon accelerator (such as Apple's Neural Engine) optimized for low-latency matrix and tensor inference over unified memory. (Ch. 17)</p>
</div>

<div id="term-ntfs" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">NTFS</span><span class="md-term-full">New Technology File System</span></div>
  <p>Primary metadata-journaling filesystem used on Microsoft Windows, logging structural updates before checkpointing them in place. (Ch. 12)</p>
</div>

<div id="term-numa" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">NUMA</span><span class="md-term-full">Non-Uniform Memory Access</span></div>
  <p>Multi-socket server architecture where each socket owns a local DRAM controller. Crossing an inter-socket link adds 30 to 100% latency, motivating processor affinity and first-touch physical frame allocation. (Ch. 5, 17)</p>
</div>

<div id="term-nx" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">NX</span><span class="md-term-full">No-Execute (Execute-Disable)</span></div>
  <p>Bit 63 of an x86-64 PTE blocking instruction fetches from writable stack and heap pages in silicon, enforcing hardware Write XOR Execute (W^X) defense against code injection. (Ch. 7, 8)</p>
</div>

<div id="term-oci" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">OCI</span><span class="md-term-full">Open Container Initiative</span></div>
  <p>Industry specification standardizing layered container image formats and runtime lifecycle interfaces across Docker, containerd, and Kubernetes. (Ch. 16)</p>
</div>

<div id="term-oom" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">OOM</span><span class="md-term-full">Out-of-Memory</span></div>
  <p>Condition triggered when host physical RAM or a container's cgroup memory.max ceiling is exhausted, causing the kernel OOM killer to terminate a process with SIGKILL to reclaim frames. (Ch. 16)</p>
</div>

<div id="term-pa" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">PA</span><span class="md-term-full">Physical Address</span></div>
  <p>True hardware address placed on the memory bus to read or write a byte in physical DRAM, composed by the MMU as (PFN &lt;&lt; 12) | Offset. (Ch. 7)</p>
</div>

<div id="term-pat" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">PAT</span><span class="md-term-full">Page Attribute Table</span></div>
  <p>Bit 7 of a leaf x86-64 PTE combining with PCD and PWT to select fine-grained memory caching attributes such as write-back or write-combining. (Ch. 7)</p>
</div>

<div id="term-pcb" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">PCB</span><span class="md-term-full">Process Control Block</span></div>
  <p>Authoritative per-process kernel structure (struct task_struct on Linux) holding scheduling state, saved registers, kernel stack pointer, page-table descriptor (mm_struct), open file descriptors, and signal masks. (Ch. 3, 10, 12, 15)</p>
</div>

<div id="term-pcd" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">PCD / PWT</span><span class="md-term-full">Page-Level Cache Disable &amp; Write-Through</span></div>
  <p>PTE bits [4:3] controlling hardware cacheability: 00 selects normal write-back cacheable DRAM, whereas disabling caching prevents stale reads from hardware MMIO registers. (Ch. 7)</p>
</div>

<div id="term-pcid" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">PCID</span><span class="md-term-full">Process-Context Identifier</span></div>
  <p>12-bit x86-64 hardware tag stored alongside every TLB entry so context switches and KPTI CR3 reloads preserve cached translations instead of flushing the TLB. (Ch. 7)</p>
</div>

<div id="term-pcie" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">PCIe</span><span class="md-term-full">Peripheral Component Interconnect Express</span></div>
  <p>Point-to-point serial expansion bus connecting NVMe SSDs, NICs, and discrete GPUs to the CPU, offering 32 to 64 GB/s per x16 link (far narrower than on-die unified memory). (Ch. 2, 16, 17)</p>
</div>

<div id="term-pd" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">PD</span><span class="md-term-full">Page Directory (Level 2)</span></div>
  <p>Third radix level in 4-level x86-64 paging indexed by VA bits [29:21]. Each of its 512 entries covers 2 MiB and terminates the walk early to map a 2 MiB huge page when PS = 1. (Ch. 7, 16)</p>
</div>

<div id="term-pdpt" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">PDPT</span><span class="md-term-full">Page Directory Pointer Table (Level 3)</span></div>
  <p>Second radix level indexed by VA bits [38:30]. Each entry covers 1 GiB and can map a 1 GiB huge page directly when PS = 1. (Ch. 7, 16)</p>
</div>

<div id="term-pf" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">#PF</span><span class="md-term-full">Page Fault Exception</span></div>
  <p>x86-64 hardware exception (Vector 14) raised when a PTE has Present = 0 or a memory reference violates R/W, U/S, or NX bits. In three of four cases (zero-fill, demand paging, copy-on-write), the kernel resolves #PF transparently and restarts the instruction. (Ch. 7)</p>
</div>

<div id="term-pfn" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">PFN</span><span class="md-term-full">Physical Frame Number</span></div>
  <p>40-bit frame index stored in PTE bits [51:12] identifying a 4 KiB-aligned frame in physical DRAM. Masking a leaf PTE with 0x000F_FFFF_FFFF_F000 recovers the physical frame base address. (Ch. 7)</p>
  <div class="md-term-rust">let frame_base: u64 = pte &amp; 0x000F_FFFF_FFFF_F000;
let pfn: u64 = frame_base &gt;&gt; 12;</div>
</div>

<div id="term-pgd" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">PGD / PUD / PMD</span><span class="md-term-full">Page Global / Upper / Middle Directory</span></div>
  <p>Architecture-independent Linux kernel names for the Level 4 (PML4), Level 3 (PDPT), and Level 2 (PD) radix page-table nodes. (Ch. 3, 7)</p>
</div>

<div id="term-pgid" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">PGID</span><span class="md-term-full">Process Group Identifier</span></div>
  <p>Numeric identifier grouping processes (such as a shell pipeline) so terminal job-control signals like SIGINT reach the entire foreground group together. (Ch. 15)</p>
</div>

<div id="term-pid" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">PID</span><span class="md-term-full">Process Identifier</span></div>
  <p>Unique positive integer identifying a process in the kernel table. PID 1 is the root supervisor (systemd or launchd) that adopts and reaps orphaned processes. (Ch. 3, 9, 10, 15, 16, 19)</p>
  <div class="md-term-rust">let pid = std::process::id(); // portable user-space PID query</div>
</div>

<div id="term-pku" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">PKU</span><span class="md-term-full">Memory Protection Keys</span></div>
  <p>x86-64 hardware feature tagging PTEs into 16 protection domains whose read/write rights can be toggled in a single unprivileged user-mode register write without calling mprotect(). (Ch. 7)</p>
</div>

<div id="term-pml4" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">PML4</span><span class="md-term-full">Page Map Level 4</span></div>
  <p>Root radix table pointed to by CR3 and indexed by VA bits [47:39]. Each of its 512 8-byte entries governs a 512 GiB virtual region, letting the kernel omit unmapped subtrees at zero RAM cost. (Ch. 7, 16)</p>
</div>

<div id="term-pmu" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">PMU</span><span class="md-term-full">Performance Monitoring Unit / Power Management Unit</span></div>
  <p>In CPU profiling (Ch. 18), silicon event counters tracking cycles, instructions, cache misses, and TLB misses at zero software cost. In hardware supervision (Ch. 15), the Power Management Unit watchdog timer.</p>
</div>

<div id="term-posix" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">POSIX</span><span class="md-term-full">Portable Operating System Interface</span></div>
  <p>IEEE standard family defining uniform Unix system calls (open, mmap, fork, sigaction, poll, pthread_mutex_t) so low-level systems code compiles and behaves predictably across Linux and macOS. (Ch. 1 to 19)</p>
</div>

<div id="term-ps" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">PS</span><span class="md-term-full">Page Size Bit</span></div>
  <p>Bit 7 of an x86-64 PD or PDPT entry. Setting PS = 1 terminates the radix walk early to map a contiguous 2 MiB or 1 GiB huge page, expanding TLB reach by 512× or 262,144×. (Ch. 7)</p>
</div>

<div id="term-pt" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">PT</span><span class="md-term-full">Page Table (Level 1 Leaf)</span></div>
  <p>Bottom radix table indexed by VA bits [20:12], holding 512 8-byte leaf PTEs that map individual 4 KiB virtual pages to physical DRAM frames. (Ch. 7, 16)</p>
</div>

<div id="term-pte" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">PTE</span><span class="md-term-full">Page Table Entry</span></div>
  <p>64-bit descriptor mapping one virtual page to one 4 KiB-aligned physical frame. Because the low 12 bits of every frame base are zero, hardware packs permission and activity flags (P, R/W, U/S, A, D) directly into bits [11:0] and NX into bit 63. (Ch. 7, 8, 11)</p>
</div>

<div id="term-qemu" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">QEMU</span><span class="md-term-full">Quick Emulator</span></div>
  <p>User-space machine emulator and virtual device model commonly paired with KVM to emulate legacy PCIe controllers or serve virtio device backends. (Ch. 16)</p>
</div>

<div id="term-quic" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">QUIC</span><span class="md-term-full">Quick UDP Internet Connections</span></div>
  <p>Encrypted, multiplexed transport protocol layered over UDP (powering HTTP/3) that combines TLS and transport setup into one round trip and eliminates cross-stream TCP head-of-line blocking. (Ch. 14)</p>
</div>

<div id="term-raii" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">RAII</span><span class="md-term-full">Resource Acquisition Is Initialization</span></div>
  <p>Ownership discipline tying resource cleanup (mutex unlocks, file closes, mmap unmaps, thread joins) deterministically to lexical scope exit via C++ destructors and Rust's Drop trait. (Ch. 4, 6)</p>
  <div class="md-term-rust">impl Drop for Arena {
    fn drop(&amp;mut self) { unsafe { libc::munmap(self.base, self.cap); } }
}</div>
</div>

<div id="term-rcu" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">RCU</span><span class="md-term-full">Read-Copy-Update</span></div>
  <p>Kernel synchronization protocol letting concurrent readers traverse read-mostly structures (such as process credentials) with zero locks or atomic writes, while deferring reclamation of replaced copies until all active readers complete. (Ch. 3)</p>
</div>

<div id="term-rfo" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">RFO</span><span class="md-term-full">Read-For-Ownership</span></div>
  <p>Cache-coherency bus broadcast issued when a core writes to a Shared cache line, forcing every sibling core to invalidate its copy before the store commits. (Ch. 17)</p>
</div>

<div id="term-risc" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">RISC</span><span class="md-term-full">Reduced Instruction Set Computer</span></div>
  <p>Load/store architecture family (such as ARM64) using fixed-width instructions and load-linked/store-conditional pairs (LDXR/STXR) for atomic updates. (Ch. 6)</p>
</div>

<div id="term-rpc" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">RPC</span><span class="md-term-full">Remote Procedure Call</span></div>
  <p>Request/response messaging abstraction invoking operations across isolated processes (Unix domain sockets) or networked hosts (TCP/gRPC). (Ch. 5, 11)</p>
</div>

<div id="term-sid" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">SID</span><span class="md-term-full">Session Identifier</span></div>
  <p>Numeric identifier grouping one or more process groups sharing a controlling terminal. Daemons call setsid() to create a fresh session with no controlling terminal. (Ch. 15)</p>
</div>

<div id="term-sigchld" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">SIGCHLD</span><span class="md-term-full">Child Status Changed Signal</span></div>
  <p>Asynchronous notification delivered to a parent when a child exits. Because standard signals coalesce into a single pending bit, handlers must drain all zombies in a non-blocking waitpid(-1, &amp;mut status, WNOHANG) loop. (Ch. 3, 10, 15)</p>
</div>

<div id="term-sigkill" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">SIGKILL / SIGSTOP</span><span class="md-term-full">Uncatchable Kill &amp; Stop Signals</span></div>
  <p>Signals 9 and 19 bypass user signal masks and handlers unconditionally so the kernel and administrator can always terminate or pause a runaway process. (Ch. 9, 10, 15)</p>
</div>

<div id="term-sigsegv" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">SIGSEGV / SIGBUS</span><span class="md-term-full">Segmentation Violation &amp; Bus Error</span></div>
  <p>Synchronous fatal signals delivered when a process dereferences an unmapped address, violates PTE permissions, or touches a PROT_NONE guard page. (Ch. 7, 10)</p>
</div>

<div id="term-sigterm" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">SIGTERM / SIGHUP / SIGINT</span><span class="md-term-full">Lifecycle Control Signals</span></div>
  <p>Catchable signals steering long-running processes: SIGTERM requests graceful shutdown, SIGHUP triggers configuration reload, and SIGINT represents interactive Ctrl-C. Handlers record an atomic flag and exit promptly. (Ch. 10, 15)</p>
  <div class="md-term-rust">static STOP: AtomicBool = AtomicBool::new(false);
extern "C" fn on_term(_: libc::c_int) { STOP.store(true, Ordering::Relaxed); }</div>
</div>

<div id="term-simd" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">SIMD</span><span class="md-term-full">Single Instruction, Multiple Data</span></div>
  <p>Data-parallel vector instructions (SSE, AVX, NEON) operating on wide 128- to 512-bit registers in lockstep, imposing strict 16-byte alignment requirements on general-purpose allocators. (Ch. 3, 8, 19)</p>
</div>

<div id="term-slc" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">SLC</span><span class="md-term-full">System Level Cache</span></div>
  <p>Large shared on-die cache in Apple Silicon SoCs bridging CPU, GPU, and NPU access to unified memory while absorbing repeated reads before DRAM. (Ch. 17)</p>
</div>

<div id="term-slo" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">SLO</span><span class="md-term-full">Service-Level Objective</span></div>
  <p>Quantitative tail-latency or availability target (such as p99 &lt; 20 ms) governing production engineering decisions where arithmetic averages hide tail amplification. (Ch. 18)</p>
</div>

<div id="term-slub" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">SLUB</span><span class="md-term-full">Unqueued Slab Allocator</span></div>
  <p>Primary Linux kernel allocator managing contiguous slabs of fixed-size kernel objects (such as task_struct and inode) with an intrusive free list threaded directly inside empty slots for O(1) cache-warm allocation. (Ch. 3, 8)</p>
</div>

<div id="term-smmu" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">SMMU</span><span class="md-term-full">System Memory Management Unit</span></div>
  <p>ARM64 IOMMU translating peripheral DMA memory requests through stage-2 page tables to isolate passthrough devices safely inside guest VMs. (Ch. 16)</p>
</div>

<div id="term-smp" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">SMP</span><span class="md-term-full">Symmetric Multiprocessing</span></div>
  <p>Multi-core design where identical cores share one physical address space and kernel, requiring per-CPU runqueues and cache-coherent synchronization to scale. (Ch. 5, 17)</p>
</div>

<div id="term-smt" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">SMT</span><span class="md-term-full">Simultaneous Multithreading</span></div>
  <p>Hardware technique (Hyper-Threading) presenting two logical threads on one physical core sharing L1/L2 caches and execution pipelines to hide memory-stall cycles. (Ch. 5)</p>
</div>

<div id="term-soc" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">SoC</span><span class="md-term-full">System-on-Chip</span></div>
  <p>Integrated silicon package combining CPU cores, GPU, NPU, memory controllers, and I/O fabrics on one die or interposer for high bandwidth and low dispatch latency. (Ch. 17)</p>
</div>

<div id="term-sram" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">SRAM</span><span class="md-term-full">Static Random-Access Memory</span></div>
  <p>Six-transistor on-chip memory requiring no refresh, used to build L1 (~1 ns), L2 (~4 ns), and L3 (~15 ns) caches at far higher cost per byte than off-chip DRAM. (Ch. 2)</p>
</div>

<div id="term-sr-iov" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">SR-IOV</span><span class="md-term-full">Single Root I/O Virtualization</span></div>
  <p>PCIe hardware feature splitting one physical NIC into multiple independent virtual functions that the hypervisor assigns directly to guest VMs via the IOMMU for near-bare-metal throughput. (Ch. 16)</p>
</div>

<div id="term-ssd" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">SSD</span><span class="md-term-full">Solid-State Drive</span></div>
  <p>Non-volatile flash storage device accessed over NVMe/PCIe (~50 to 200 µs latency). Volatile controller write caches still require an explicit fsync() flush to guarantee crash durability. (Ch. 12, 18)</p>
</div>

<div id="term-sse" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">SSE</span><span class="md-term-full">Streaming SIMD Extensions</span></div>
  <p>128-bit x86-64 vector instruction set whose aligned load/store instructions require 16-byte address alignment, shaping the System V AMD64 allocator contract. (Ch. 19)</p>
</div>

<div id="term-stlb" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">STLB</span><span class="md-term-full">Shared Translation Lookaside Buffer (L2)</span></div>
  <p>Second-level unified per-core TLB (1,024 to 2,048 entries) backing L1 instruction and data TLBs. With 4 KiB pages, 1,536 entries cover 6 MiB; with 2 MiB huge pages, the same entries cover 3 GiB. (Ch. 7)</p>
</div>

<div id="term-syn" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">SYN</span><span class="md-term-full">Synchronize (TCP)</span></div>
  <p>TCP control flag opening the three-way handshake (SYN, SYN-ACK, ACK) to synchronize initial byte sequence numbers before user data flows. (Ch. 13, 14)</p>
</div>

<div id="term-tcb" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">TCB</span><span class="md-term-full">Thread Control Block</span></div>
  <p>Per-thread kernel structure storing saved registers, kernel stack pointer, Thread-Local Storage base, and scheduler runqueue state. (Ch. 4, 6)</p>
</div>

<div id="term-tcp" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">TCP</span><span class="md-term-full">Transmission Control Protocol</span></div>
  <p>Connection-oriented, reliable, ordered byte-stream transport over IP. Because TCP coalesces or splits writes freely, higher-level protocols must frame every message explicitly. (Ch. 2, 11, 13, 14, 15)</p>
  <div class="md-term-rust">use std::net::TcpListener;
let listener = TcpListener::bind("127.0.0.1:45678")?;</div>
</div>

<div id="term-tlb" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">TLB</span><span class="md-term-full">Translation Lookaside Buffer</span></div>
  <p>Core-private associative cache storing recent VPN-to-PFN translations (~1 cycle hit), avoiding 4 sequential memory reads per load. Because TLBs are not coherent across cores, unmapping shared pages requires synchronous IPI shootdowns. (Ch. 4, 7, 13, 16, 18, 19)</p>
</div>

<div id="term-tls" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">TLS</span><span class="md-term-full">Transport Layer Security / Thread-Local Storage</span></div>
  <p>In networking (Ch. 14), cryptographic protocol encrypting TCP connections. In threading (Ch. 3, 4), per-thread private variable storage anchored at FS_BASE (x86-64) or TPIDR_EL0 (ARM64) for lock-free thread-local state like errno.</p>
</div>

<div id="term-ttbr0" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">TTBR0_EL1 / TTBR1_EL1</span><span class="md-term-full">Translation Table Base Registers</span></div>
  <p>Dual ARM64 root page-table registers separating user-space (TTBR0_EL1) and kernel-space (TTBR1_EL1) mappings natively in silicon without requiring CR3 switches on syscalls. (Ch. 3, 4, 7)</p>
</div>

<div id="term-tty" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">TTY</span><span class="md-term-full">Teletype (Terminal Device)</span></div>
  <p>Character device mediating interactive keyboard input, line discipline, and foreground job-control signals (SIGINT, SIGHUP). Daemons double-fork so they can never accidentally acquire a controlling TTY. (Ch. 15)</p>
</div>

<div id="term-udp" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">UDP</span><span class="md-term-full">User Datagram Protocol</span></div>
  <p>Connectionless, boundary-preserving datagram transport with an 8-byte header and zero handshake delay, ideal for DNS, telemetry, real-time media, and QUIC. Oversized datagrams are truncated without error if the receive buffer is too small. (Ch. 13, 14)</p>
  <div class="md-term-rust">use std::net::UdpSocket;
let sock = UdpSocket::bind("127.0.0.1:0")?;
sock.send_to(b"ping-udp", "127.0.0.1:45680")?;</div>
</div>

<div id="term-uid" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">UID</span><span class="md-term-full">User Identifier</span></div>
  <p>Numeric Unix identity governing file ownership and privilege checks (UID 0 is root; user namespaces map container UID 0 to an unprivileged host UID). (Ch. 3, 12, 16)</p>
</div>

<div id="term-uma" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">UMA</span><span class="md-term-full">Unified Memory Architecture</span></div>
  <p>SoC memory design (such as Apple Silicon) where CPU, GPU, and NPU share one physical high-bandwidth memory pool, eliminating PCIe DMA copies while still requiring explicit cache flushes and command-buffer fences. (Ch. 17)</p>
</div>

<div id="term-upi" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">UPI</span><span class="md-term-full">Ultra Path Interconnect</span></div>
  <p>Intel high-speed point-to-point cache-coherent fabric linking multi-socket NUMA processors and carrying remote DRAM requests and MESI invalidations. (Ch. 5, 17)</p>
</div>

<div id="term-va" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">VA</span><span class="md-term-full">Virtual Address</span></div>
  <p>Program pointer address inside a process's private linear address space, sliced into four 9-bit radix indices and an invariant 12-bit page offset on 48-bit x86-64 systems. (Ch. 7)</p>
</div>

<div id="term-vcpu" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">vCPU</span><span class="md-term-full">Virtual Central Processing Unit</span></div>
  <p>Virtual core exposed to a guest OS, backed by a host thread and a hardware VMCS structure scheduled across physical host cores by the hypervisor. (Ch. 16)</p>
</div>

<div id="term-vdso" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">vDSO</span><span class="md-term-full">Virtual Dynamic Shared Object</span></div>
  <p>Read-only kernel page mapped directly into user space on Linux so high-frequency calls like clock_gettime() read calibrated hardware counters in ~15 ns without trapping into Ring 0. (Ch. 9)</p>
</div>

<div id="term-vfio" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">VFIO</span><span class="md-term-full">Virtual Function I/O</span></div>
  <p>Linux framework exposing physical PCIe devices directly to a VM or user-space driver safely through IOMMU DMA isolation. (Ch. 16)</p>
</div>

<div id="term-vm" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">VM</span><span class="md-term-full">Virtual Machine</span></div>
  <p>Hardware-isolated guest execution environment running an independent kernel atop a hypervisor, providing a strong multi-tenant security boundary at higher memory overhead than containers. (Ch. 16)</p>
</div>

<div id="term-vma" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">VMA</span><span class="md-term-full">Virtual Memory Area</span></div>
  <p>Kernel interval record (vm_area_struct) tracking every valid virtual region (text, heap, mmap, stack) and its logical permissions, consulted by the page-fault handler to distinguish lazy allocation from illegal SIGSEGV accesses. (Ch. 3, 7)</p>
</div>

<div id="term-vmcs" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">VMCS</span><span class="md-term-full">Virtual Machine Control Structure</span></div>
  <p>In-memory Intel VT-x state block storing guest registers, host registers, EPT root pointer, and VM-Exit intercept bitmaps for one vCPU. (Ch. 16)</p>
</div>

<div id="term-vmx" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">VMX</span><span class="md-term-full">Virtual Machine Extensions</span></div>
  <p>Intel VT-x execution architecture separating the host hypervisor (VMX Root) from guest kernels (VMX Non-Root) orthogonally to Rings 0 through 3. (Ch. 16)</p>
</div>

<div id="term-vpid" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">VPID</span><span class="md-term-full">Virtual Processor Identifier</span></div>
  <p>Intel hardware TLB tag isolating host and guest virtual translations across VM-Exit and VM-Entry without flushing the TLB. (Ch. 16)</p>
</div>

<div id="term-vpn" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">VPN</span><span class="md-term-full">Virtual Page Number</span></div>
  <p>Upper virtual address bits (VA &gt;&gt; 12) identifying a 4 KiB virtual page and indexing the TLB or 4-level radix page table while the low 12-bit offset passes through unmodified. (Ch. 7)</p>
</div>

<div id="term-vram" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">VRAM</span><span class="md-term-full">Video Random-Access Memory</span></div>
  <p>Dedicated high-bandwidth memory soldered onto discrete GPU cards, requiring explicit PCIe DMA copies and host page pinning when moving tensors from CPU DRAM. (Ch. 17)</p>
</div>

<div id="term-vt-x" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">VT-x</span><span class="md-term-full">Intel Virtualization Technology</span></div>
  <p>Intel x86-64 hardware virtualization extensions providing VMX Root/Non-Root execution modes, VMCS state switching, and Extended Page Tables. (Ch. 16)</p>
</div>

<div id="term-wx" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">W^X</span><span class="md-term-full">Write XOR Execute</span></div>
  <p>Memory-safety invariant prohibiting any virtual page from being simultaneously writable and executable, enforced in hardware via PTE bit 63 (NX = 1) on stack and heap allocations. (Ch. 7)</p>
  <div class="md-term-rust">// Guard page: strip all R/W/X permissions in hardware PTE
unsafe { libc::mprotect(guard_ptr, page_size, libc::PROT_NONE) };</div>
</div>

<div id="term-xfs" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">XFS</span><span class="md-term-full">Extended File System</span></div>
  <p>High-performance 64-bit journaling, extent-based Linux filesystem engineered for parallel multi-core I/O scalability and massive file sizes. (Ch. 12)</p>
</div>

<div id="term-xnu" class="md-glossary-card">
  <div class="md-term-head"><span class="md-term-chip">XNU</span><span class="md-term-full">X is Not Unix (Darwin Kernel)</span></div>
  <p>Hybrid kernel powering macOS and Apple platforms, combining a Mach microkernel core (tasks, threads, Mach ports) with a BSD POSIX layer (processes, sockets, kqueue). (Ch. 3, 5)</p>
</div>

</div>
