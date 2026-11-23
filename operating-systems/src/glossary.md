# Glossary of Architectural Terms & Abbreviations

Every systems abbreviation across the book links directly to its definition below. Each entry explains the physical or kernel constraint that motivates the mechanism, its exact role in hardware or software, and (where applicable) an idiomatic Rust 2024 snippet illustrating how systems code interacts with it.

### `ABA`: ABA Problem (Lock-Free Reuse Hazard) {#term-aba}

Hazard in lock-free Compare-And-Swap algorithms where a thread reads pointer A, gets preempted while another thread pops A, frees it, and reallocates a distinct object at the identical address A. Without version tags or epoch-based reclamation, CAS succeeds erroneously and corrupts a Treiber stack or lock-free queue. (Ch. 6, 8)

```rust
// Pack a monotonic version tag alongside the pointer or index
let next = ((ver.wrapping_add(1)) << 32) | (new_idx as u64);
head.compare_exchange_weak(old, next, Ordering::AcqRel, Ordering::Acquire)
```

### `ABI`: Application Binary Interface {#term-abi}

Compiled machine code has no concept of source-level types or parameter names. The ABI fixes the binary contract across function and kernel boundaries: which registers hold arguments, which registers callees must preserve, stack alignment (16 bytes on x86-64 and ARM64), and how struct fields are laid out in memory. (Ch. 2, 8, 9)

```rust
#[repr(C)]
struct SockAddrIn { family: u16, port: u16, addr: u32 }
```

### `ACK`: Acknowledgment (TCP) {#term-ack}

Because IP networks drop and reorder packets freely, TCP tracks every transmitted byte by sequence number. Setting the ACK flag tells the sender the next byte offset expected, advancing the sliding window and cancelling retransmission timers for all prior bytes. (Ch. 13, 14)

### `AF_UNIX`: Unix Domain Socket Address Family {#term-af-unix}

Address family for kernel-mediated local IPC addressed by filesystem paths or anonymous socketpair() endpoints. Bypassing IP routing, checksums, and TCP handshakes yields lower latency than loopback TCP and enables kernel-verified credential passing and file-descriptor transfer via SCM_RIGHTS. (Ch. 11)

```rust
use std::os::unix::net::UnixStream;
let (mut a, mut b) = UnixStream::pair()?;
```

### `AMD-V`: AMD Virtualization {#term-amd-v}

Hardware hypervisor extensions on AMD x86-64 processors that isolate guest kernels without binary translation, pairing host/guest execution modes with Nested Page Tables (NPT) for two-stage memory translation. (Ch. 16)

### `APFS`: Apple File System {#term-apfs}

Copy-on-write, extent-based filesystem powering macOS and Apple platforms. Rather than overwriting metadata blocks in place, APFS writes new tree nodes and atomically swaps the container checkpoint, enabling instant zero-copy file clones and crash-consistent snapshots. (Ch. 12)

### `API`: Application Programming Interface {#term-api}

The source-level contract of types, signatures, preconditions, and error values exposed by a library or kernel wrapper. Whereas an API governs source compatibility, an ABI governs binary compatibility. (Ch. 1, 13)

### `APIC`: Advanced Programmable Interrupt Controller {#term-apic}

x86-64 interrupt routing fabric split into a system-wide IO-APIC (routing peripheral signals) and per-core Local APICs (delivering preemptive timer ticks and cross-core Inter-Processor Interrupts). (Ch. 2, 5)

### `ASIC`: Application-Specific Integrated Circuit {#term-asic}

Fixed-function silicon engineered for a single workload such as AES encryption, video encoding, or matrix multiplication, achieving orders-of-magnitude higher performance per watt than general-purpose CPU cores. (Ch. 17)

### `ASID`: Address Space Identifier {#term-asid}

An 8- or 16-bit hardware tag on ARM64 attached to every TLB entry so translations from distinct processes coexist safely across context switches without flushing the TLB. (Ch. 7, 16, 19)

### `ASLR`: Address Space Layout Randomization {#term-aslr}

Kernel security mitigation that randomizes the virtual base addresses of the stack, heap, shared libraries, and executable on every launch, preventing attackers from jumping to hardcoded gadget addresses. (Ch. 3, 7)

### `AVL`: Available for Operating System Use {#term-avl}

Bits [11:9] of an x86-64 Page Table Entry ignored by silicon and left free for kernel software metadata such as copy-on-write markers or swap-slot bookkeeping. (Ch. 7)

### `AVX`: Advanced Vector Extensions {#term-avx}

256-bit and 512-bit SIMD vector instructions on x86-64 that process 8 or 16 32-bit values in a single cycle, requiring properly aligned memory buffers to avoid split-line penalties. (Ch. 19)

### `BDP`: Bandwidth-Delay Product {#term-bdp}

Product of link bandwidth and round-trip latency (B x RTT), quantifying the exact number of bytes that must remain in flight to saturate a network pipe. If socket send/receive buffers or the TCP receive window fall below the BDP, the sender stalls waiting for ACKs even on an uncongested link. (Ch. 13, 14)

```rust
// 10 Gbps link with 20 ms RTT requires 25 MiB in flight
let bdp_bytes: u64 = (10_000_000_000 / 8) * 20 / 1_000;
```

### `BSD`: Berkeley Software Distribution {#term-bsd}

Unix lineage that introduced the socket API, reliable signal handlers, and the kqueue event subsystem, forming the POSIX layer of macOS and Darwin. (Ch. 10, 13, 14, 15)

### `BSS`: Block Started by Symbol {#term-bss}

Executable segment holding zero-initialized static globals. Storing only its byte length in the binary header rather than megabytes of zeros keeps executables small; the kernel maps demand-zeroed frames lazily on first touch. (Ch. 3)

```rust
static ZERO_INIT: AtomicU64 = AtomicU64::new(0); // placed in .bss
```

### `CAS`: Compare-And-Swap {#term-cas}

Hardware atomic read-modify-write primitive that stores a new value into memory if and only if the current value equals an expected snapshot, forming the building block of lock-free algorithms and mutex fast paths. (Ch. 6)

```rust
state.compare_exchange_weak(
    0, 1, Ordering::Acquire, Ordering::Relaxed
)
```

### `CFS`: Completely Fair Scheduler {#term-cfs}

Linux proportional-share scheduler tracking each runnable thread's weighted virtual runtime (vruntime) in a red-black tree and always dispatching the leftmost thread with the smallest vruntime. (Ch. 5)

### `CISC`: Complex Instruction Set Computer {#term-cisc}

Architecture family (such as x86-64) offering variable-length, memory-operating instructions like LOCK CMPXCHG that execute atomic read-modify-write sequences in a single instruction. (Ch. 6)

### `CLOSE_WAIT`: TCP Passive-Close Waiting State {#term-close-wait}

TCP state entered after receiving a peer's FIN and acknowledging it while the local application has still left its socket descriptor open. Accumulating sockets stuck in CLOSE_WAIT signals a file-descriptor leak where the server failed to call close() after observing EOF, eventually exhausting EMFILE limits. (Ch. 13, 14)

```rust
// Dropping TcpStream invokes close(), transitioning out of CLOSE_WAIT
if stream.read(&mut buf)? == 0 {
    drop(stream);
}
```

### `COW / CoW`: Copy-on-Write {#term-cow}

Virtual-memory technique that avoids eager physical copying during fork() by mapping parent and child PTEs to the same physical frames with Read/Write = 0. The first store triggers a hardware fault, prompting the kernel to duplicate only that single 4 KiB frame. (Ch. 3, 7, 11)

```rust
// MAP_PRIVATE requests copy-on-write semantics across fork()
libc::mmap(ptr::null_mut(), len, PROT_READ | PROT_WRITE,
           MAP_PRIVATE | MAP_ANON, -1, 0)
```

### `CPI`: Cycles Per Instruction {#term-cpi}

Reciprocal of IPC measuring average CPU clock cycles spent retiring each machine instruction via PMU hardware counters. A rising CPI (above 1.0 on superscalar cores) pinpoints front-end branch mispredictions or back-end LLC and DRAM stalls where wider parallelism or better cache locality is needed. (Ch. 18)

```rust
let cpi: f64 = cycles_retired as f64 / instructions_retired as f64;
assert!(cpi.is_finite());
```

### `CPL`: Current Privilege Level {#term-cpl}

Hardware privilege ring stored in the x86-64 code-segment register (Ring 3 for unprivileged user code; Ring 0 for kernel mode). Every privileged instruction and page-table U/S bit is checked against CPL in silicon. (Ch. 2, 9)

### `CPU`: Central Processing Unit {#term-cpu}

General-purpose processor executing instruction streams across fetch, decode, out-of-order execution, and retirement pipelines. Operating systems multiplex finite CPU cores across thousands of runnable threads using hardware timer interrupts, privilege rings, and preemptive scheduling. (Ch. 1 to 19)

```rust
let cores = std::thread::available_parallelism()?.get();
```

### `CR2`: Control Register 2 {#term-cr2}

x86-64 hardware register into which the MMU latches the exact faulting 64-bit virtual address before vectoring into the kernel's Page Fault (#PF) handler, allowing the kernel to look up the offending Virtual Memory Area. (Ch. 7)

### `CR3`: Control Register 3 {#term-cr3}

Privileged x86-64 register storing the 4 KiB-aligned physical base address of the active process's Level 4 (PML4) root page table. Context switching between processes reloads CR3; switching between sibling threads leaves CR3 untouched. (Ch. 3, 4, 7, 16)

### `CWND`: Congestion Window (TCP) {#term-cwnd}

Sender-side TCP bound limiting unacknowledged bytes in flight based on observed network congestion (packet loss or ECN marks). Without CWND slow-start and multiplicative decrease, concurrent senders would overwhelm router queues and trigger global congestion collapse. (Ch. 13, 14)

```rust
// Effective TCP flight size is bounded by both CWND and peer RWND
let in_flight_limit = cwnd_bytes.min(rwnd_bytes);
```

### `DDR4 / DDR5`: Double Data Rate Synchronous DRAM {#term-ddr}

Main system memory modules attached to processor memory controllers, transferring data on both rising and falling clock edges to balance multi-gigabyte capacity against ~60 to 100 ns latency. (Ch. 17)

### `DMA`: Direct Memory Access {#term-dma}

Hardware mechanism allowing NVMe drives, NICs, and GPUs to read and write physical DRAM directly over PCIe while CPU cores execute other work, raising an interrupt only once the entire transfer completes. (Ch. 2, 3, 16, 17)

### `DNS`: Domain Name System {#term-dns}

Hierarchical naming service resolving hostnames into binary IPv4/IPv6 addresses, queried safely in Rust via ToSocketAddrs (wrapping POSIX getaddrinfo). (Ch. 14)

```rust
use std::net::ToSocketAddrs;
let addrs: Vec<_> = "localhost:443".to_socket_addrs()?.collect();
```

### `DRAM`: Dynamic Random-Access Memory {#term-dram}

Off-chip volatile main memory storing bits in tiny capacitors refreshed every few milliseconds. Because a single DRAM miss stalls a 3 GHz core for 200+ cycles, systems software structures data for spatial locality inside L1/L2 caches. (Ch. 2, 5, 7, 8, 16, 17, 18, 19)

### `dTLB`: Data Translation Lookaside Buffer {#term-dtlb}

First-level core-private associative cache holding ~64 recent data-page translations (~0.5 to 1 cycle hit). With 4 KiB pages its reach is only 256 KiB, explaining why random access over larger buffers triggers translation stalls. (Ch. 7, 18)

### `EACCES`: Permission Denied (errno) {#term-eacces}

POSIX error returned when a process lacks the UID/GID file mode bits, directory search permission, or capability required for open(), execve(), or bind() on a privileged port. Ignoring EACCES obscures misconfigured filesystem ACLs and least-privilege sandbox violations. (Ch. 9, 12, 15)

```rust
use std::io::ErrorKind;
if let Err(e) = std::fs::File::open("/etc/shadow") {
    assert_eq!(e.kind(), ErrorKind::PermissionDenied);
}
```

### `EAGAIN / EWOULDBLOCK`: Resource Temporarily Unavailable (errno) {#term-eagain}

POSIX error signaling that a non-blocking read(), write(), or accept() cannot complete immediately without sleeping, or that fork() hit a process-limit ceiling. Event-driven loops treat EAGAIN as the exact stopping signal when draining an O_NONBLOCK descriptor until the next readiness notification. (Ch. 3, 6, 9, 13, 14)

```rust
match stream.read(&mut buf) {
    Err(e) if e.kind() == std::io::ErrorKind::WouldBlock => break,
    Ok(n) => process(&buf[..n]),
    Err(e) => return Err(e),
}
```

### `EBADF`: Bad File Descriptor (errno) {#term-ebadf}

POSIX error returned when a syscall receives a negative integer, an already-closed descriptor, or one opened with an incompatible access mode (such as writing to an O_RDONLY file). In multi-threaded code, EBADF often reveals a use-after-close bug where one thread closed a descriptor another thread still held. (Ch. 9, 11, 12, 15)

```rust
// OwnedFd prevents double-close and EBADF via RAII ownership
use std::os::fd::OwnedFd;
fn read_owned(fd: &OwnedFd, buf: &mut [u8]) -> isize {
    unsafe { libc::read(std::os::fd::AsRawFd::as_raw_fd(fd), buf.as_mut_ptr().cast(), buf.len()) }
}
```

### `eBPF`: Extended Berkeley Packet Filter {#term-ebpf}

In-kernel verified bytecode runtime allowing engineers to attach safe, JIT-compiled observability tracers and packet filters directly to kernel tracepoints without user-space context switches or kernel modules. (Ch. 16, 18)

### `ECHILD`: No Child Processes (errno) {#term-echild}

POSIX error returned by waitpid() when the caller has zero unwaited child processes matching the requested PID filter (or when SIGCHLD was set to SIG_IGN so the kernel auto-reaped them). Signal-driven supervisors treat ECHILD as the normal termination condition of a WNOHANG reaping loop. (Ch. 3, 10)

```rust
let rc = unsafe { libc::waitpid(-1, &mut status, libc::WNOHANG) };
if rc < 0 && std::io::Error::last_os_error().raw_os_error() == Some(libc::ECHILD) {
    // All children have been reaped
}
```

### `EEVDF`: Earliest Eligible Virtual Deadline First {#term-eevdf}

Linux scheduler replacing CFS heuristics with explicit virtual deadlines, allowing short latency-sensitive tasks to preempt long-running CPU jobs cleanly while preserving long-term proportional fairness. (Ch. 5)

### `EFAULT`: Bad Address (errno) {#term-efault}

POSIX error returned when user code passes an unmapped or read-only pointer to a syscall buffer argument. Rather than panicking the kernel on copy_from_user() or copy_to_user(), the kernel's exception table catches the fault cleanly and returns EFAULT to Ring 3. (Ch. 9, 10, 11, 12)

```rust
// Passing a null buffer to write() fails safely with EFAULT
let rc = unsafe { libc::write(1, std::ptr::null(), 16) };
assert_eq!(rc, -1);
```

### `EINTR`: Interrupted System Call (errno) {#term-eintr}

POSIX error returned when an asynchronous signal interrupts a blocking syscall (such as read(), poll(), or waitpid()) before any progress occurs. Failing to retry on EINTR causes spurious I/O aborts whenever a child exits or a timer fires in production. (Ch. 3, 9, 10, 13, 14, 15)

```rust
loop {
    match file.read(&mut buf) {
        Err(e) if e.kind() == std::io::ErrorKind::Interrupted => continue,
        res => break res,
    }
}
```

### `EL0 / EL1 / EL2`: ARM64 Exception Levels {#term-el0}

Hardware privilege hierarchy on ARM64: EL0 runs user applications, EL1 runs the operating system kernel, and EL2 runs the hypervisor beneath guest kernels. (Ch. 2, 7, 16)

### `ELF`: Executable and Linkable Format {#term-elf}

Standard binary container format on Linux specifying program headers that tell execve() exactly which file offsets map into the read-only text segment, initialized data segment, and zero-filled BSS segment. (Ch. 3)

### `EMFILE`: Too Many Open Files (errno) {#term-emfile}

POSIX error returned when a process exhausts its per-process RLIMIT_NOFILE descriptor table. Without a reserved idle descriptor or connection cap, an accept() loop hitting EMFILE spins at 100% CPU because the pending connection stays ready in the listen queue forever. (Ch. 9, 11, 12, 13, 15)

```rust
// Inspect or handle EMFILE during accept() backoff
if err.raw_os_error() == Some(libc::EMFILE) {
    std::thread::sleep(std::time::Duration::from_millis(5));
}
```

### `ENOENT`: No Such File or Directory (errno) {#term-enoent}

POSIX error returned when path resolution traverses a missing directory entry, dangling symlink, or absent Unix socket path. Treating ENOENT explicitly lets systems code distinguish a cold-start state (create a fresh file) from genuine storage or permission failures. (Ch. 9, 12, 15)

```rust
match std::fs::read("state.bin") {
    Err(e) if e.kind() == std::io::ErrorKind::NotFound => Vec::new(),
    Ok(bytes) => bytes,
    Err(e) => return Err(e),
}
```

### `ENOMEM`: Out of Memory (errno) {#term-enomem}

POSIX error returned when mmap(), brk(), or fork() cannot reserve virtual address space, physical frames, or cgroup memory quota. Checking for ENOMEM (or MAP_FAILED) prevents null-pointer dereferences and allows services to shed load gracefully instead of crashing. (Ch. 3, 13, 15)

```rust
let mut buf = Vec::new();
buf.try_reserve_exact(64 * 1024 * 1024)?; // returns Err on ENOMEM
```

### `EOF`: End-of-File {#term-eof}

Condition reported when read() returns 0 bytes (never an error). On pipes and TCP sockets, EOF arrives only once every open write descriptor has been closed, making closing unused pipe ends after fork() mandatory. (Ch. 11, 13, 15)

```rust
match stream.read(&mut buf)? {
    0 => break, // peer closed write half (EOF)
    n => handle(&buf[..n]),
}
```

### `EOI`: End of Interrupt {#term-eoi}

Register write issued by a top-half interrupt handler to the Local APIC or ARM GIC signaling that hardware may clear the active vector bit and deliver subsequent interrupts of equal or lower priority. (Ch. 2)

### `EPIPE`: Broken Pipe (errno) {#term-epipe}

POSIX error returned by write() or send() when the remote reader has closed its pipe end or TCP socket (once SIGPIPE is ignored or masked). Network servers rely on EPIPE to detect abrupt client disconnects cleanly instead of terminating abruptly from an unhandled SIGPIPE. (Ch. 9, 11, 13)

```rust
match stream.write_all(frame) {
    Err(e) if e.kind() == std::io::ErrorKind::BrokenPipe => close_peer(),
    res => res?,
}
```

### `EPT`: Extended Page Tables {#term-ept}

Intel hardware second-stage page tables controlled by the hypervisor that translate every Guest Physical Address (GPA) into a Host Physical Address (HPA), isolating tenant VMs in silicon while avoiding software shadow page tables. (Ch. 16)

### `EVFILT_PROC`: kqueue Process-Lifecycle Event Filter {#term-evfilt-proc}

BSD and macOS kqueue filter that attaches directly to a target PID inside the kernel to deliver process-lifecycle events (such as NOTE_EXIT) asynchronously. Unlike polling waitpid() or relying on coalesced SIGCHLD signals, EVFILT_PROC integrates child supervision directly into a single event loop. (Ch. 15)

```rust
// Register a kqueue watch for child process exit on macOS/BSD
let ev = libc::kevent {
    ident: child_pid as usize,
    filter: libc::EVFILT_PROC,
    flags: libc::EV_ADD | libc::EV_ONESHOT,
    fflags: libc::NOTE_EXIT,
    data: 0,
    udata: std::ptr::null_mut(),
};
```

### `FAR_EL1`: Fault Address Register (EL1) {#term-far-el1}

ARM64 kernel system register capturing the faulting virtual address whenever a translation or permission abort occurs (the architectural counterpart to x86-64 CR2). (Ch. 7)

### `FCFS`: First-Come, First-Served Scheduling {#term-fcfs}

Non-preemptive scheduling policy that runs each job strictly in arrival order until completion or blocking. Although simple and starvation-free, FCFS suffers from the convoy effect: one long CPU-bound job stalls every short interactive task queued behind it, inflating average turnaround time. (Ch. 5)

```rust
use std::collections::VecDeque;
// FCFS dispatches strictly from the front of the arrival queue
while let Some(job) = ready_queue.pop_front() {
    run_to_completion(job);
}
```

### `FFS`: Fast File System (Berkeley FFS) {#term-ffs}

Classic Unix on-disk filesystem design that partitions storage into Cylinder Groups, placing inodes near their data blocks and directories near their children. Without this spatial locality, spinning disks wasted most of their I/O budget on mechanical seek latency across scattered tracks. (Ch. 12)

```rust
// Group metadata and payload contiguously to minimize disk seeks
let block_group = inode_num / inodes_per_group;
```

### `FIFO`: First-In, First-Out {#term-fifo}

Strict arrival-order queueing discipline preserving element ordering in pipes, bounded producer-consumer rings, and hardware store buffers. (Ch. 5, 6, 11, 19)

```rust
use std::collections::VecDeque;
let mut q = VecDeque::with_capacity(64);
q.push_back(job);
let next = q.pop_front(); // O(1) FIFO dequeue
```

### `FIN`: Finish (TCP) {#term-fin}

TCP control flag signaling that the sender will transmit no further bytes, initiating graceful half-close teardown while still allowing in-flight data in the reverse direction to drain cleanly. (Ch. 13, 14)

### `FTL`: Flash Translation Layer {#term-ftl}

Firmware layer inside every SSD translating logical block addresses (LBAs) into physical NAND flash pages while performing wear leveling and background garbage collection. Because flash cells must be erased in large blocks before rewriting, random small writes cause write amplification unless batched sequentially. (Ch. 12)

```rust
// Sequential append-only writes minimize SSD FTL write amplification
let mut log = std::fs::OpenOptions::new().create(true).append(true).open("wal.log")?;
std::io::Write::write_all(&mut log, record)?;
```

### `GDDR`: Graphics Double Data Rate {#term-gddr}

High-bandwidth memory soldered directly onto discrete GPU cards, optimized for wide parallel streaming throughput rather than single-thread CPU latency. (Ch. 17)

### `GIC`: Generic Interrupt Controller {#term-gic}

ARM64 interrupt routing architecture (GICv3) connecting SoC peripherals through a central Distributor and per-core Redistributors to CPU interrupt inputs. (Ch. 2)

### `GID`: Group Identifier {#term-gid}

Numeric Unix security identifier stored in a process's credential struct and in every file inode, governing group-level read, write, and execute permissions. (Ch. 3, 12)

### `#GP`: General Protection Fault {#term-gp}

x86-64 hardware exception (Vector 13) raised immediately when unprivileged code executes a privileged instruction or dereferences a non-canonical 64-bit pointer whose bits [63:48] fail to replicate bit 47. (Ch. 7)

### `GPA`: Guest Physical Address {#term-gpa}

Physical address perceived by a VM guest kernel starting at 0x0. Hardware translates every GPA into a true Host Physical Address (HPA) via EPT or NPT so guests cannot touch sibling tenants' DRAM. (Ch. 16)

### `GPU`: Graphics Processing Unit {#term-gpu}

Throughput-oriented processor packing thousands of parallel arithmetic lanes to accelerate graphics, machine learning, and scientific kernels, connected either over PCIe or Unified Memory. (Ch. 16, 17)

### `GVA`: Guest Virtual Address {#term-gva}

Virtual address issued inside a VM, translated across two hardware stages: GVA to GPA via Guest CR3, and GPA to HPA via hypervisor EPT/NPT. (Ch. 16)

### `HBM`: High Bandwidth Memory {#term-hbm}

3D-stacked, ultra-wide memory co-packaged on an interposer beside AI/HPC accelerators, delivering multi-terabyte-per-second bandwidth far exceeding host PCIe links. (Ch. 17)

### `HPA`: Host Physical Address {#term-hpa}

Actual physical DRAM bus address on the bare-metal server hosting virtual machines, known solely to the host hypervisor and IOMMU. (Ch. 16)

### `HPC`: High-Performance Computing {#term-hpc}

Large-scale numerical and scientific workloads where NUMA first-touch placement, cache-line alignment, and accelerator memory bandwidth govern scalability. (Ch. 17)

### `HTTP`: Hypertext Transfer Protocol {#term-http}

Application-layer request/response protocol demonstrating explicit message framing (Content-Length or chunked framing) above byte-stream TCP (HTTP/1.1, HTTP/2) or multiplexed QUIC/UDP (HTTP/3). (Ch. 14)

### `I/O`: Input / Output {#term-io}

Data movement between processor memory and external subsystems (storage, network, pipes, terminals). Because I/O latency is orders of magnitude slower than CPU cycles, systems software relies on user-space buffering and event-driven multiplexing. (Ch. 9, 12, 13, 14, 15, 16, 18)

```rust
use std::io::{BufWriter, Write};
let mut w = BufWriter::with_capacity(64 * 1024, file);
w.write_all(b"batched syscall\n")?;
```

### `IDT / IDTR`: Interrupt Descriptor Table &amp; Register {#term-idt}

256-entry hardware dispatch table on x86-64 mapping every exception (#GP, #PF) and hardware IRQ vector to its Ring 0 kernel handler entry point, located by the IDTR register. (Ch. 2)

### `IOMMU`: Input-Output Memory Management Unit {#term-iommu}

Hardware translation unit (Intel VT-d, AMD-Vi, ARM SMMU) placed between PCIe devices and physical DRAM to translate device DMA addresses through per-device page tables, preventing rogue or passthrough devices from corrupting host memory. (Ch. 16)

### `IOPS`: Input/Output Operations Per Second {#term-iops}

Storage performance metric counting discrete random block read/write operations completed per second, bounded per container via cgroups v2 io.max. (Ch. 16)

### `IP / IPv4 / IPv6`: Internet Protocol {#term-ip}

Best-effort, connectionless network-layer packet routing protocol (32-bit addresses in IPv4; 128-bit in IPv6). Because IP may drop or reorder packets, reliability is delegated to transport protocols like TCP or QUIC. (Ch. 11, 13, 14)

### `IPC`: Inter-Process Communication / Instructions Per Cycle {#term-ipc}

In OS architecture (Ch. 11, 15, 16), IPC denotes kernel-mediated channels (pipes, shared memory, Unix sockets) bridging isolated address spaces. In CPU profiling (Ch. 18), IPC measures retired instructions per clock cycle via hardware PMU counters.

### `IPI`: Inter-Processor Interrupt {#term-ipi}

Hardware interrupt dispatched by one CPU core to sibling cores via the APIC or GIC, used to wake idle schedulers and execute synchronous cross-core TLB shootdowns during munmap() or mprotect(). (Ch. 2, 7)

### `IRQ`: Interrupt Request {#term-irq}

Asynchronous hardware signal raised by a peripheral device (timer, NIC, NVMe controller) to preempt current execution and invoke a kernel top-half handler. (Ch. 2)

### `IRR`: Interrupt Request Register (Local APIC) {#term-irr}

256-bit hardware register inside the x86-64 Local APIC recording accepted interrupts waiting to be serviced by the CPU core. Separating pending bits (IRR) from currently executing bits (ISR) lets hardware prioritize higher-vector interrupts without dropping simultaneous arrivals. (Ch. 2)

```rust
// Conceptual model: APIC picks the highest-priority pending bit in IRR
let next_vector = 255 - irr_high_u64.leading_zeros();
```

### `ISA`: Instruction Set Architecture {#term-isa}

Formal hardware/software boundary defining machine instructions, register files, memory-ordering guarantees, and exception semantics (such as x86-64 and ARM64). (Ch. 2)

### `ISR`: In-Service Register / Interrupt Service Routine {#term-isr}

In x86-64 APIC hardware, the 256-bit In-Service Register tracks which interrupt vectors are currently executing until the handler writes EOI; in kernel software, ISR denotes the top-half Interrupt Service Routine invoked via the IDT. Keeping ISRs short and non-blocking prevents masking lower-priority timers and I/O devices. (Ch. 2)

```rust
// Top-half ISR captures minimal state and defers heavy work to a queue
irq_ring.push_event(event); // O(1) lock-free handoff before EOI
```

### `JIT`: Just-In-Time Compilation {#term-jit}

Runtime compilation emitting executable machine instructions into anonymous mmap pages, transitioning permissions from PROT_READ | PROT_WRITE to PROT_READ | PROT_EXEC via mprotect() to honor W^X invariants. (Ch. 8)

### `KPTI`: Kernel Page-Table Isolation {#term-kpti}

Mitigation against speculative Meltdown attacks that unmaps most kernel memory while in Ring 3, forcing a CR3 page-table switch on every system call and making hardware PCID tagging essential to prevent TLB thrashing. (Ch. 7, 9)

### `KVM`: Kernel-based Virtual Machine {#term-kvm}

Linux kernel subsystem transforming Linux into a hardware-assisted hypervisor by driving Intel VT-x, AMD-V, or ARM64 EL2 directly for guest vCPUs. (Ch. 16)

### `LLC`: Last-Level Cache {#term-llc}

Largest on-chip cache tier (typically shared L3, 8 to 128 MiB, ~12 to 20 ns) serving as the final filter before crossing the memory controller to off-chip DRAM. (Ch. 5, 18)

### `LLVM`: Low-Level Virtual Machine {#term-llvm}

Modular optimizing compiler backend powering Clang and rustc, known for heavy use of contiguous index-addressed arena allocators for intermediate representation graphs. (Ch. 8)

### `LRU`: Least Recently Used {#term-lru}

Cache eviction policy discarding the entry untouched for the longest interval, implemented in O(1) with a hash map plus doubly-linked list and approximated by OS kernels using PTE Accessed bits. (Ch. 7, 19)

### `MADV_HUGEPAGE`: Transparent Huge Page Memory Advice (Linux) {#term-madv-hugepage}

Linux madvise() hint advising the kernel (khugepaged) to back a 2 MiB-aligned virtual region with 2 MiB Transparent Huge Pages instead of 4 KiB pages. Expanding TLB reach by 512x cuts page-table walk overhead dramatically for large heaps, arenas, and in-memory indexes. (Ch. 7, 8)

```rust
#[cfg(target_os = "linux")]
unsafe {
    libc::madvise(base_ptr, len, libc::MADV_HUGEPAGE);
}
```

### `MAP_ANON / MAP_ANONYMOUS`: Anonymous Memory Mapping Flag {#term-map-anon}

mmap() flag requesting fresh, demand-zeroed virtual memory backed by RAM and swap rather than an open file descriptor (fd = -1). General-purpose allocators and arena managers rely on MAP_ANON to obtain page-aligned virtual address ranges directly from the kernel. (Ch. 7, 8, 11)

```rust
let ptr = unsafe {
    libc::mmap(
        std::ptr::null_mut(),
        1 << 20,
        libc::PROT_READ | libc::PROT_WRITE,
        libc::MAP_PRIVATE | libc::MAP_ANON,
        -1,
        0,
    )
};
```

### `MAP_FAILED`: mmap() Error Sentinel Pointer {#term-map-failed}

Sentinel value ((void *)-1, usize::MAX) returned by POSIX mmap() on failure instead of NULL because virtual address 0x0 was historically a valid mapping address. Testing for ptr.is_null() instead of ptr == MAP_FAILED misses allocation errors and dereferences 0xFFFF_FFFF_FFFF_FFFF into an immediate SIGSEGV. (Ch. 7, 8)

```rust
if ptr == libc::MAP_FAILED {
    return Err(std::io::Error::last_os_error());
}
```

### `MAP_PRIVATE`: Private Copy-on-Write Mapping Flag {#term-map-private}

mmap() visibility flag giving the calling process private copy-on-write pages whose stores remain invisible to other processes and never write back to an underlying file. Without MAP_PRIVATE, mutating a mapped executable or shared library would corrupt the file on disk for every running process. (Ch. 7, 8, 11)

```rust
let p = unsafe {
    libc::mmap(std::ptr::null_mut(), len, libc::PROT_READ | libc::PROT_WRITE,
               libc::MAP_PRIVATE | libc::MAP_ANON, -1, 0)
};
```

### `MAP_SHARED`: Shared Memory Mapping Flag {#term-map-shared}

mmap() visibility flag pointing multiple processes' PTEs directly at the exact same physical page frames so stores become immediately visible across address spaces and flush back to file-backed storage. Shared-memory ring buffers and IPC arenas require MAP_SHARED; using MAP_PRIVATE isolates each writer's updates into private copies. (Ch. 7, 11)

```rust
let shm = unsafe {
    libc::mmap(std::ptr::null_mut(), len, libc::PROT_READ | libc::PROT_WRITE,
               libc::MAP_SHARED, shm_fd, 0)
};
```

### `MCS`: Mellor-Crummey and Scott Queue Spinlock {#term-mcs}

Scalable FIFO spinlock where each contending core appends its own stack-allocated node to a tail pointer and spins exclusively on a local cache line until its predecessor flips a flag. Unlike a naive test-and-set spinlock, MCS eliminates O(N^2) MESI cache-line invalidation storms on high-core-count servers. (Ch. 6)

```rust
// Each waiter spins on its own cache-line-aligned node
#[repr(align(64))]
struct McsNode {
    next: AtomicPtr<McsNode>,
    locked: AtomicBool,
}
```

### `MESI / MOESI`: Modified-Exclusive-Shared-Invalid {#term-mesi}

Hardware cache-coherency state machine tracking every 64-byte cache line across cores. Writing to a Shared line forces a Read-For-Ownership invalidation across sibling cores, which is the physical root cause of false sharing. (Ch. 2, 5, 6, 17)

```rust
#[repr(align(64))] // isolate counters onto distinct MESI cache lines
struct PaddedCounter(AtomicU64);
```

### `ML`: Machine Learning {#term-ml}

Tensor- and bandwidth-intensive workloads that motivate discrete GPU DMA pinning on x86 servers and zero-copy Unified Memory Architectures on Apple Silicon. (Ch. 17)

### `MLFQ`: Multi-Level Feedback Queue Scheduler {#term-mlfq}

Preemptive scheduler maintaining multiple priority queues where newly arriving or I/O-blocking tasks stay at high priority with short quanta while CPU-bound jobs demote to lower queues with longer quanta. Periodic priority boosts prevent starvation while delivering fast interactive response without knowing job lengths in advance. (Ch. 5)

```rust
// Demote a thread that exhausts its full quantum without blocking
if used_ticks >= quantum_for_level(level) {
    level = (level + 1).min(MAX_LEVEL);
}
```

### `MMIO`: Memory-Mapped Input/Output {#term-mmio}

Hardware design mapping peripheral device control registers into physical memory addresses (with PTE cache-disable bits set) so drivers command devices using ordinary load and store instructions. (Ch. 2, 7, 16)

### `MMU`: Memory Management Unit {#term-mmu}

Silicon state machine inside every CPU core that intercepts every virtual address, translates VPN to PFN via the TLB or 4-level page-table walk, verifies PTE permission bits, and raises #PF on any violation. (Ch. 2, 3, 7, 16)

```rust
// Hardware translation invariant for 4 KiB (2^12 B) pages:
let vpn = va >> 12;
let offset = va & 0xFFF;
let pa = (pfn << 12) | offset;
```

### `MPSC`: Multi-Producer, Single-Consumer Queue {#term-mpsc}

Concurrency channel topology allowing multiple worker threads to push messages concurrently to one dedicated consumer thread (such as a logger or event loop). Producers synchronize via an atomic tail swap or mutex while the lone consumer dequeues without cross-consumer contention. (Ch. 6)

```rust
use std::sync::mpsc;
let (tx, rx) = mpsc::channel::<String>();
let tx2 = tx.clone(); // second producer thread
```

### `MQMS`: Multi-Queue Multiprocessor Scheduling {#term-mqms}

SMP scheduling architecture assigning every CPU core its own private runqueue to preserve L1/L2 cache affinity and avoid global lock contention. Periodic work stealing rebalances load across cores so one core never sits idle while a sibling's queue overflows. (Ch. 5)

```rust
// Pop locally first; steal from a sibling core only when empty
let task = local_queue.pop().or_else(|| steal_from_peer(&peers));
```

### `MSI-X`: Message Signaled Interrupts Extended {#term-msi-x}

Modern PCIe interrupt mechanism letting a device signal specific CPU cores via targeted DMA writes rather than shared legacy IRQ wires, enabling per-core lock-free NIC receive queues. (Ch. 2)

### `MSS`: Maximum Segment Size (TCP) {#term-mss}

Largest TCP payload a single segment can carry without IP fragmentation, negotiated during the SYN handshake as MTU minus IP and TCP headers (typically 1,460 bytes over 1,500-byte Ethernet). Exceeding path MSS forces IP fragmentation or silent black-holing when the IP DF (Do-Not-Fragment) bit is set. (Ch. 13, 14)

```rust
const ETHERNET_MTU: usize = 1500;
const TCP_IPV4_MSS: usize = ETHERNET_MTU - 20 - 20; // 1460 bytes
```

### `MTU`: Maximum Transmission Unit {#term-mtu}

Largest packet payload a physical network link can carry without fragmentation (typically 1,500 bytes on Ethernet); sending a UDP datagram exceeding the path limit fails with EMSGSIZE. (Ch. 14)

### `NAPI`: New API (Linux Network Polling) {#term-napi}

Linux driver framework that masks per-packet NIC interrupts under heavy traffic and drains batches of frames inside NET_RX_SOFTIRQ, preventing interrupt livelock. (Ch. 2)

### `NEON`: ARM Advanced SIMD {#term-neon}

128-bit vector execution unit standard across ARM64 processors, saved and restored inside the kernel's thread_struct during context switches. (Ch. 3, 19)

### `NIC`: Network Interface Card {#term-nic}

Peripheral controller transferring Ethernet frames between the physical network cable and kernel ring buffers via PCIe DMA and MSI-X interrupts. (Ch. 2, 13, 16)

### `NMI`: Non-Maskable Interrupt {#term-nmi}

Highest-priority hardware interrupt that fires even when normal interrupts are disabled, enabling PMU sampling profilers to capture stack traces inside interrupt-masked kernel critical sections. (Ch. 18)

### `NOTE_EXIT`: kqueue Process-Exit Filter Flag {#term-note-exit}

Event sub-flag paired with EVFILT_PROC on macOS and BSD asking kqueue to wake the supervisor immediately when the monitored PID terminates. Receiving NOTE_EXIT triggers a non-blocking waitpid(WNOHANG) call to collect the child's exit code and clear its zombie PCB entry. (Ch. 15)

```rust
if (ev.fflags & libc::NOTE_EXIT) != 0 {
    let mut status = 0;
    unsafe { libc::waitpid(ev.ident as libc::pid_t, &mut status, libc::WNOHANG) };
}
```

### `NPT`: Nested Page Tables {#term-npt}

AMD hardware two-stage virtualization page tables translating Guest Physical Addresses to Host Physical Addresses (functional equivalent of Intel EPT). (Ch. 16)

### `NPU`: Neural Processing Unit {#term-npu}

Dedicated silicon accelerator (such as Apple's Neural Engine) optimized for low-latency matrix and tensor inference over unified memory. (Ch. 17)

### `NTFS`: New Technology File System {#term-ntfs}

Primary metadata-journaling filesystem used on Microsoft Windows, logging structural updates before checkpointing them in place. (Ch. 12)

### `NUMA`: Non-Uniform Memory Access {#term-numa}

Multi-socket server architecture where each socket owns a local DRAM controller. Crossing an inter-socket link adds 30 to 100% latency, motivating processor affinity and first-touch physical frame allocation. (Ch. 5, 17)

### `NX`: No-Execute (Execute-Disable) {#term-nx}

Bit 63 of an x86-64 PTE blocking instruction fetches from writable stack and heap pages in silicon, enforcing hardware Write XOR Execute (W^X) defense against code injection. (Ch. 7, 8)

### `O_CLOEXEC`: Close-on-Exec File Descriptor Flag {#term-o-cloexec}

open() flag setting FD_CLOEXEC atomically when a descriptor is created so the kernel closes it automatically across execve(). Without O_CLOEXEC, multi-threaded programs leak open sockets, lock files, and pipes into spawned child processes, causing hung EOF signals and security exposure. (Ch. 3, 9, 12)

```rust
// Rust std::fs::File sets O_CLOEXEC automatically; raw libc calls must pass it
let fd = unsafe { libc::open(path.as_ptr(), libc::O_RDONLY | libc::O_CLOEXEC) };
```

### `O_CREAT`: Create File If Missing Flag {#term-o-creat}

open() flag instructing the kernel to allocate a new inode and directory entry when the target path does not exist, using the caller's mode bits masked by umask. Omitting the mode argument on raw open(..., O_CREAT) leaves random stack permissions on the newly created file. (Ch. 9, 12)

```rust
let fd = unsafe {
    libc::open(path.as_ptr(), libc::O_RDWR | libc::O_CREAT | libc::O_CLOEXEC, 0o644)
};
```

### `O_DIRECT`: Direct Unbuffered I/O Flag {#term-o-direct}

open() flag instructing the kernel to DMA directly between user-space buffers and the block device, bypassing the OS page cache. Database engines managing their own buffer pool use O_DIRECT to avoid double caching, accepting strict sector-size alignment constraints on buffers and offsets. (Ch. 12)

```rust
#[cfg(target_os = "linux")]
use std::os::unix::fs::OpenOptionsExt;
#[cfg(target_os = "linux")]
let f = std::fs::OpenOptions::new().read(true).custom_flags(libc::O_DIRECT).open("data.db")?;
```

### `O_NONBLOCK`: Non-Blocking I/O Descriptor Flag {#term-o-nonblock}

File-status flag directing read(), write(), accept(), and connect() to return EAGAIN immediately rather than putting the calling thread to sleep when data or buffer space is unavailable. Single-threaded reactors (poll, epoll, kqueue) require O_NONBLOCK on every socket so one slow peer never freezes the entire server. (Ch. 12, 13)

```rust
stream.set_nonblocking(true)?; // sets O_NONBLOCK via fcntl()
```

### `O_RDWR`: Read-Write Access Mode Flag {#term-o-rdwr}

POSIX open() access mode requesting both read and write permissions on the opened file description. Memory-mapping a file with PROT_READ | PROT_WRITE and MAP_SHARED requires an O_RDWR descriptor; opening with O_RDONLY causes mmap() to fail with EACCES. (Ch. 9, 12)

```rust
let file = std::fs::OpenOptions::new()
    .read(true)
    .write(true) // translates to O_RDWR
    .open("ledger.dat")?;
```

### `OCI`: Open Container Initiative {#term-oci}

Industry specification standardizing layered container image formats and runtime lifecycle interfaces across Docker, containerd, and Kubernetes. (Ch. 16)

### `OOM`: Out-of-Memory {#term-oom}

Condition triggered when host physical RAM or a container's cgroup memory.max ceiling is exhausted, causing the kernel OOM killer to terminate a process with SIGKILL to reclaim frames. (Ch. 16)

### `PA`: Physical Address {#term-pa}

True hardware address placed on the memory bus to read or write a byte in physical DRAM, composed by the MMU as (PFN &lt;&lt; 12) | Offset. (Ch. 7)

### `PAT`: Page Attribute Table {#term-pat}

Bit 7 of a leaf x86-64 PTE combining with PCD and PWT to select fine-grained memory caching attributes such as write-back or write-combining. (Ch. 7)

### `PCB`: Process Control Block {#term-pcb}

Authoritative per-process kernel structure (struct task_struct on Linux) holding scheduling state, saved registers, kernel stack pointer, page-table descriptor (mm_struct), open file descriptors, and signal masks. (Ch. 3, 10, 12, 15)

### `PCD / PWT`: Page-Level Cache Disable &amp; Write-Through {#term-pcd}

PTE bits [4:3] controlling hardware cacheability: 00 selects normal write-back cacheable DRAM, whereas disabling caching prevents stale reads from hardware MMIO registers. (Ch. 7)

### `PCID`: Process-Context Identifier {#term-pcid}

12-bit x86-64 hardware tag stored alongside every TLB entry so context switches and KPTI CR3 reloads preserve cached translations instead of flushing the TLB. (Ch. 7)

### `PCIe`: Peripheral Component Interconnect Express {#term-pcie}

Point-to-point serial expansion bus connecting NVMe SSDs, NICs, and discrete GPUs to the CPU, offering 32 to 64 GB/s per x16 link (far narrower than on-die unified memory). (Ch. 2, 16, 17)

### `PD`: Page Directory (Level 2) {#term-pd}

Third radix level in 4-level x86-64 paging indexed by VA bits [29:21]. Each of its 512 entries covers 2 MiB and terminates the walk early to map a 2 MiB huge page when PS = 1. (Ch. 7, 16)

### `PDPT`: Page Directory Pointer Table (Level 3) {#term-pdpt}

Second radix level indexed by VA bits [38:30]. Each entry covers 1 GiB and can map a 1 GiB huge page directly when PS = 1. (Ch. 7, 16)

### `PEBS`: Precise Event-Based Sampling (Intel) {#term-pebs}

Intel PMU hardware extension that records the exact architectural instruction pointer and register snapshot directly into a DRAM buffer when a counter overflows. Without PEBS, out-of-order execution skid shifts samples several instructions past the true cache-missing load, misleading flame graphs. (Ch. 18)

```rust
// In Linux perf, appending :pp selects hardware PEBS precision:
// perf record -e cache-misses:pp -g -- ./target/release/bench
```

### `#PF`: Page Fault Exception {#term-pf}

x86-64 hardware exception (Vector 14) raised when a PTE has Present = 0 or a memory reference violates R/W, U/S, or NX bits. In three of four cases (zero-fill, demand paging, copy-on-write), the kernel resolves #PF transparently and restarts the instruction. (Ch. 7)

### `PFN`: Physical Frame Number {#term-pfn}

40-bit frame index stored in PTE bits [51:12] identifying a 4 KiB-aligned frame in physical DRAM. Masking a leaf PTE with 0x000F_FFFF_FFFF_F000 recovers the physical frame base address. (Ch. 7)

```rust
let frame_base: u64 = pte & 0x000F_FFFF_FFFF_F000;
let pfn: u64 = frame_base >> 12;
```

### `PGD / PUD / PMD`: Page Global / Upper / Middle Directory {#term-pgd}

Architecture-independent Linux kernel names for the Level 4 (PML4), Level 3 (PDPT), and Level 2 (PD) radix page-table nodes. (Ch. 3, 7)

### `PGID`: Process Group Identifier {#term-pgid}

Numeric identifier grouping processes (such as a shell pipeline) so terminal job-control signals like SIGINT reach the entire foreground group together. (Ch. 15)

### `PID`: Process Identifier {#term-pid}

Unique positive integer identifying a process in the kernel table. PID 1 is the root supervisor (systemd or launchd) that adopts and reaps orphaned processes. (Ch. 3, 9, 10, 15, 16, 19)

```rust
let pid = std::process::id(); // portable user-space PID query
```

### `PKU`: Memory Protection Keys {#term-pku}

x86-64 hardware feature tagging PTEs into 16 protection domains whose read/write rights can be toggled in a single unprivileged user-mode register write without calling mprotect(). (Ch. 7)

### `PML4`: Page Map Level 4 {#term-pml4}

Root radix table pointed to by CR3 and indexed by VA bits [47:39]. Each of its 512 8-byte entries governs a 512 GiB virtual region, letting the kernel omit unmapped subtrees at zero RAM cost. (Ch. 7, 16)

### `PMU`: Performance Monitoring Unit / Power Management Unit {#term-pmu}

In CPU profiling (Ch. 18), silicon event counters tracking cycles, instructions, cache misses, and TLB misses at zero software cost. In hardware supervision (Ch. 15), the Power Management Unit watchdog timer.

### `POLLIN`: Readable-Data Event Bit (poll) {#term-pollin}

Bitmask flag in struct pollfd.events and revents signaling that normal data, an incoming listen-queue connection, or an EOF condition can be read without blocking. Failing to check POLLIN alongside POLLHUP and POLLERR causes event loops to miss half-closed sockets. (Ch. 13)

```rust
let mut pfd = libc::pollfd { fd: raw_fd, events: libc::POLLIN, revents: 0 };
if unsafe { libc::poll(&mut pfd, 1, 1000) } > 0 && (pfd.revents & libc::POLLIN) != 0 {
    drain_socket(raw_fd)?;
}
```

### `POSIX`: Portable Operating System Interface {#term-posix}

IEEE standard family defining uniform Unix system calls (open, mmap, fork, sigaction, poll, pthread_mutex_t) so low-level systems code compiles and behaves predictably across Linux and macOS. (Ch. 1 to 19)

### `PR_SET_PDEATHSIG`: Parent-Death Signal (Linux prctl) {#term-pr-set-pdeathsig}

Linux prctl() option telling the kernel to deliver a chosen signal (typically SIGTERM or SIGKILL) to a worker process the instant its parent thread exits. Without PR_SET_PDEATHSIG, a crashed supervisor leaves orphaned worker processes running indefinitely and holding ports or locks. (Ch. 15)

```rust
#[cfg(target_os = "linux")]
unsafe {
    libc::prctl(libc::PR_SET_PDEATHSIG, libc::SIGTERM);
}
```

### `PROT_EXEC`: Executable Page Protection Flag {#term-prot-exec}

mmap() and mprotect() flag clearing the PTE No-Execute (NX) bit so the CPU instruction fetcher may execute bytes from the page. Security-hardened runtimes and JIT engines forbid combining PROT_WRITE | PROT_EXEC simultaneously to uphold W^X invariants against code injection. (Ch. 7, 8)

```rust
// Transition JIT code buffer from RW to RX via mprotect()
unsafe { libc::mprotect(code_page, 4096, libc::PROT_READ | libc::PROT_EXEC) };
```

### `PROT_NONE`: No-Access Page Protection Flag {#term-prot-none}

mmap() and mprotect() flag reserving virtual address space while denying all reads, writes, and instruction fetches in hardware PTEs. Placing a PROT_NONE guard page beneath thread stacks or arena slabs converts silent buffer overflows into immediate, deterministic SIGSEGV or SIGBUS traps. (Ch. 4, 7, 8)

```rust
// Reserve a virtual guard page with zero physical RAM committed
unsafe {
    libc::mmap(std::ptr::null_mut(), 4096, libc::PROT_NONE,
               libc::MAP_PRIVATE | libc::MAP_ANON, -1, 0)
};
```

### `PROT_READ`: Readable Page Protection Flag {#term-prot-read}

mmap() and mprotect() permission flag enabling load instructions from the mapped virtual pages. On x86-64 and ARM64, separating PROT_READ from PROT_WRITE lets kernels protect read-only text segments, constant tables, and shared snapshots against accidental mutation. (Ch. 7, 8, 11)

```rust
let ro = unsafe {
    libc::mmap(std::ptr::null_mut(), len, libc::PROT_READ, libc::MAP_SHARED, fd, 0)
};
```

### `PROT_WRITE`: Writable Page Protection Flag {#term-prot-write}

mmap() and mprotect() permission flag setting the PTE Read/Write bit so store instructions succeed (or trigger copy-on-write on MAP_PRIVATE pages). Omitting PROT_WRITE catches unintended writes to immutable buffers directly in the MMU at zero runtime cost. (Ch. 7, 8, 11)

```rust
// Upgrade a previously reserved PROT_NONE page to readable and writable
unsafe { libc::mprotect(page, 4096, libc::PROT_READ | libc::PROT_WRITE) };
```

### `PS`: Page Size Bit {#term-ps}

Bit 7 of an x86-64 PD or PDPT entry. Setting PS = 1 terminates the radix walk early to map a contiguous 2 MiB or 1 GiB huge page, expanding TLB reach by 512× or 262,144×. (Ch. 7)

### `PT`: Page Table (Level 1 Leaf) {#term-pt}

Bottom radix table indexed by VA bits [20:12], holding 512 8-byte leaf PTEs that map individual 4 KiB virtual pages to physical DRAM frames. (Ch. 7, 16)

### `PTE`: Page Table Entry {#term-pte}

64-bit descriptor mapping one virtual page to one 4 KiB-aligned physical frame. Because the low 12 bits of every frame base are zero, hardware packs permission and activity flags (P, R/W, U/S, A, D) directly into bits [11:0] and NX into bit 63. (Ch. 7, 8, 11)

### `PTHREAD_PROCESS_SHARED`: Cross-Process Mutex/Condvar Attribute {#term-pthread-process-shared}

POSIX pthread attribute configuring a mutex or condition variable placed inside MAP_SHARED memory so distinct processes can synchronize on it safely. Without PTHREAD_PROCESS_SHARED, the kernel treats the futex wait key as process-private, causing deadlocks or lost wakeups across separate address spaces. (Ch. 11)

```rust
let mut attr: libc::pthread_mutexattr_t = unsafe { std::mem::zeroed() };
unsafe {
    libc::pthread_mutexattr_init(&mut attr);
    libc::pthread_mutexattr_setpshared(&mut attr, libc::PTHREAD_PROCESS_SHARED);
}
```

### `QEMU`: Quick Emulator {#term-qemu}

User-space machine emulator and virtual device model commonly paired with KVM to emulate legacy PCIe controllers or serve virtio device backends. (Ch. 16)

### `QUIC`: Quick UDP Internet Connections {#term-quic}

Encrypted, multiplexed transport protocol layered over UDP (powering HTTP/3) that combines TLS and transport setup into one round trip and eliminates cross-stream TCP head-of-line blocking. (Ch. 14)

### `RAII`: Resource Acquisition Is Initialization {#term-raii}

Ownership discipline tying resource cleanup (mutex unlocks, file closes, mmap unmaps, thread joins) deterministically to lexical scope exit via C++ destructors and Rust's Drop trait. (Ch. 4, 6)

```rust
impl Drop for Arena {
    fn drop(&mut self) { unsafe { libc::munmap(self.base, self.cap); } }
}
```

### `RAM`: Random-Access Memory {#term-ram}

Volatile main system memory (implemented with off-chip DRAM) holding active kernel structures, page tables, executable code, and the OS page cache. Because RAM capacity is finite and orders of magnitude slower than CPU registers, kernels manage it in 4 KiB physical frames with demand paging and eviction. (Ch. 2, 3, 7, 8, 11, 12, 19)

```rust
// Reserve virtual address space; physical RAM frames commit lazily on touch
let mut buf = vec![0u8; 4096];
buf[0] = 1; // triggers first physical frame commit
```

### `RCU`: Read-Copy-Update {#term-rcu}

Kernel synchronization protocol letting concurrent readers traverse read-mostly structures (such as process credentials) with zero locks or atomic writes, while deferring reclamation of replaced copies until all active readers complete. (Ch. 3)

### `RFO`: Read-For-Ownership {#term-rfo}

Cache-coherency bus broadcast issued when a core writes to a Shared cache line, forcing every sibling core to invalidate its copy before the store commits. (Ch. 17)

### `RISC`: Reduced Instruction Set Computer {#term-risc}

Load/store architecture family (such as ARM64) using fixed-width instructions and load-linked/store-conditional pairs (LDXR/STXR) for atomic updates. (Ch. 6)

### `RPC`: Remote Procedure Call {#term-rpc}

Request/response messaging abstraction invoking operations across isolated processes (Unix domain sockets) or networked hosts (TCP/gRPC). (Ch. 5, 11)

### `RWND`: Receive Window (TCP Flow Control) {#term-rwnd}

16-bit (scaled) buffer capacity advertised in every TCP ACK header telling the sender how many unconsumed bytes the receiver's kernel socket buffer can still absorb. Without RWND flow control, a fast sender would overflow a slow reader's kernel memory and trigger relentless packet drops. (Ch. 13, 14)

```rust
// Effective send ceiling obeys both peer RWND and local CWND
let send_budget = peer_rwnd.min(local_cwnd);
```

### `SA_RESTART`: Automatic Syscall Restart Signal Flag {#term-sa-restart}

sigaction() flag instructing the kernel to transparently restart interrupted slow syscalls (such as read() or waitpid()) after a signal handler returns instead of failing with EINTR. Clear SA_RESTART intentionally when a signal (such as SIGTERM or SIGALRM) must break a blocking read() to begin shutdown. (Ch. 10)

```rust
let mut sa: libc::sigaction = unsafe { std::mem::zeroed() };
sa.sa_sigaction = on_sigchld as usize;
sa.sa_flags = libc::SA_RESTART; // restart interrupted syscalls automatically
```

### `SCM_RIGHTS`: Unix Socket File-Descriptor Passing Control Message {#term-scm-rights}

Ancillary message type passed via sendmsg() and recvmsg() over AF_UNIX sockets that asks the kernel to duplicate an open file description directly into a peer process's descriptor table. Passing raw integer FD numbers as ordinary bytes fails because descriptor numbers are strictly process-local; SCM_RIGHTS enables privilege-separated servers to hand accepted sockets to unprivileged workers. (Ch. 11)

```rust
// Kernel copies the underlying struct file when cmsg_type == SCM_RIGHTS
let cmsg_type = libc::SCM_RIGHTS;
let cmsg_level = libc::SOL_SOCKET;
```

### `SID`: Session Identifier {#term-sid}

Numeric identifier grouping one or more process groups sharing a controlling terminal. Daemons call setsid() to create a fresh session with no controlling terminal. (Ch. 15)

### `SIG_DFL`: Default Signal Disposition {#term-sig-dfl}

Special handler sentinel passed to sigaction() restoring the kernel's built-in action for a signal (terminate, core dump, stop, or ignore). Because child processes inherit ignored dispositions across execve(), shells reset SIGINT and SIGPIPE back to SIG_DFL before executing external commands. (Ch. 3, 10)

```rust
unsafe { libc::signal(libc::SIGINT, libc::SIG_DFL) };
```

### `SIG_IGN`: Ignore Signal Disposition {#term-sig-ign}

Special handler sentinel instructing the kernel to discard a catchable signal immediately upon delivery. Network daemons set SIGPIPE to SIG_IGN so closed client sockets return EPIPE cleanly rather than terminating the server; setting SIGCHLD to SIG_IGN causes POSIX kernels to auto-reap exiting children without zombies. (Ch. 3, 10)

```rust
// Ignore SIGPIPE so writes to closed sockets return EPIPE instead of killing the server
unsafe { libc::signal(libc::SIGPIPE, libc::SIG_IGN) };
```

### `SIGABRT`: Abort Signal (Signal 6) {#term-sigabrt}

Signal raised by abort(), failed C assertions, or watchdog timers to terminate a malfunctioning process and generate a core dump for post-mortem debugging. Unlike SIGKILL, SIGABRT allows an emergency handler to flush crash diagnostics before the kernel tears down the address space. (Ch. 10, 15)

```rust
// Force immediate abnormal termination with SIGABRT on invariant breach
std::process::abort();
```

### `SIGALRM`: Alarm Clock Signal (Signal 14) {#term-sigalrm}

Asynchronous timer signal delivered when a per-process interval timer configured via alarm() or setitimer() expires. Historically used to bound blocking syscalls (with SA_RESTART disabled), modern event-driven services prefer poll()/kqueue() timeouts to avoid global per-process timer conflicts. (Ch. 10)

```rust
// Arm a 5-second one-shot SIGALRM watchdog
unsafe { libc::alarm(5) };
```

### `SIGCHLD`: Child Status Changed Signal {#term-sigchld}

Asynchronous notification delivered to a parent when a child exits. Because standard signals coalesce into a single pending bit, handlers must drain all zombies in a non-blocking waitpid(-1, &amp;mut status, WNOHANG) loop. (Ch. 3, 10, 15)

### `SIGKILL / SIGSTOP`: Uncatchable Kill &amp; Stop Signals {#term-sigkill}

Signals 9 and 19 bypass user signal masks and handlers unconditionally so the kernel and administrator can always terminate or pause a runaway process. (Ch. 9, 10, 15)

### `SIGPIPE`: Broken Pipe Signal (Signal 13) {#term-sigpipe}

Synchronous signal delivered when a process writes to a pipe or socket whose read end has zero remaining open descriptors. While helpful for halting shell pipelines (such as yes | head -n 1), ignoring SIGPIPE with SIG_IGN is mandatory in network servers so a single disconnecting client cannot kill the daemon. (Ch. 10, 11, 13)

```rust
// Rust std initializes SIGPIPE to SIG_IGN at startup; raw C/POSIX code sets it explicitly
unsafe { libc::signal(libc::SIGPIPE, libc::SIG_IGN) };
```

### `SIGSEGV / SIGBUS`: Segmentation Violation &amp; Bus Error {#term-sigsegv}

Synchronous fatal signals delivered when a process dereferences an unmapped address, violates PTE permissions, or touches a PROT_NONE guard page. (Ch. 7, 10)

### `SIGTERM / SIGHUP / SIGINT`: Lifecycle Control Signals {#term-sigterm}

Catchable signals steering long-running processes: SIGTERM requests graceful shutdown, SIGHUP triggers configuration reload, and SIGINT represents interactive Ctrl-C. Handlers record an atomic flag and exit promptly. (Ch. 10, 15)

```rust
static STOP: AtomicBool = AtomicBool::new(false);
extern "C" fn on_term(_: libc::c_int) { STOP.store(true, Ordering::Relaxed); }
```

### `SIGUSR1 / SIGUSR2`: User-Defined Signals {#term-sigusr}

Pair of POSIX signals with no kernel-assigned meaning, reserved exclusively for application-defined control commands such as reopening rotated log files, dumping heap statistics, or toggling debug tracing at runtime. Without a registered handler, their default disposition terminates the process. (Ch. 10, 15)

```rust
static RELOAD_STATS: AtomicBool = AtomicBool::new(false);
extern "C" fn on_usr1(_: libc::c_int) { RELOAD_STATS.store(true, Ordering::Relaxed); }
```

### `SIMD`: Single Instruction, Multiple Data {#term-simd}

Data-parallel vector instructions (SSE, AVX, NEON) operating on wide 128- to 512-bit registers in lockstep, imposing strict 16-byte alignment requirements on general-purpose allocators. (Ch. 3, 8, 19)

### `SJF`: Shortest Job First Scheduling {#term-sjf}

Non-preemptive scheduling policy that dispatches the ready job with the smallest total CPU burst next, provably minimizing average turnaround time when all jobs arrive simultaneously. If a short job arrives right after a long job begins, non-preemptive SJF still suffers convoy delay unless upgraded to preemptive STCF. (Ch. 5)

```rust
// Select the ready job with the minimum estimated burst duration
ready.sort_by_key(|job| job.burst_us);
```

### `SLC`: System Level Cache {#term-slc}

Large shared on-die cache in Apple Silicon SoCs bridging CPU, GPU, and NPU access to unified memory while absorbing repeated reads before DRAM. (Ch. 17)

### `SLO`: Service-Level Objective {#term-slo}

Quantitative tail-latency or availability target (such as p99 &lt; 20 ms) governing production engineering decisions where arithmetic averages hide tail amplification. (Ch. 18)

### `SLUB`: Unqueued Slab Allocator {#term-slub}

Primary Linux kernel allocator managing contiguous slabs of fixed-size kernel objects (such as task_struct and inode) with an intrusive free list threaded directly inside empty slots for O(1) cache-warm allocation. (Ch. 3, 8)

### `SMAP`: Supervisor Mode Access Prevention {#term-smap}

x86-64 hardware security feature (CR4.SMAP) that raises a Page Fault if Ring 0 kernel code directly reads or writes user-space pages (U/S = 1) outside explicit copy_from_user()/copy_to_user() windows. SMAP prevents kernel bugs from dereferencing attacker-controlled user buffers directly. (Ch. 2, 7, 9)

```rust
// Kernel must copy user buffers explicitly rather than dereferencing Ring 3 pointers
// copy_from_user(&mut kernel_buf, user_ptr, len)?;
```

### `SMEP`: Supervisor Mode Execution Prevention {#term-smep}

x86-64 hardware security feature (CR4.SMEP) that blocks Ring 0 from fetching instructions from any page marked User-accessible (U/S = 1). Without SMEP, a kernel pointer-overwrite exploit could pivot execution directly into attacker-mapped user shellcode with full kernel privileges. (Ch. 2, 7, 9)

```rust
// Enforced in silicon: Ring 0 instruction fetch on a U/S=1 PTE triggers #PF
const PTE_USER: u64 = 1 << 2; // Ring 0 cannot execute pages with this bit set under SMEP
```

### `SMMU`: System Memory Management Unit {#term-smmu}

ARM64 IOMMU translating peripheral DMA memory requests through stage-2 page tables to isolate passthrough devices safely inside guest VMs. (Ch. 16)

### `SMP`: Symmetric Multiprocessing {#term-smp}

Multi-core design where identical cores share one physical address space and kernel, requiring per-CPU runqueues and cache-coherent synchronization to scale. (Ch. 5, 17)

### `SMT`: Simultaneous Multithreading {#term-smt}

Hardware technique (Hyper-Threading) presenting two logical threads on one physical core sharing L1/L2 caches and execution pipelines to hide memory-stall cycles. (Ch. 5)

### `SO_REUSEADDR`: Socket Address Reuse Option {#term-so-reuseaddr}

setsockopt() flag allowing a restarted server to bind() a listening port immediately even while old connections from the previous instance linger in TIME_WAIT. Without SO_REUSEADDR, restarting a crashed or upgraded TCP daemon fails with EADDRINUSE for 60 to 120 seconds. (Ch. 13)

```rust
let yes: libc::c_int = 1;
unsafe {
    libc::setsockopt(fd, libc::SOL_SOCKET, libc::SO_REUSEADDR,
                     (&raw const yes).cast(), std::mem::size_of_val(&yes) as libc::socklen_t);
}
```

### `SoC`: System-on-Chip {#term-soc}

Integrated silicon package combining CPU cores, GPU, NPU, memory controllers, and I/O fabrics on one die or interposer for high bandwidth and low dispatch latency. (Ch. 17)

### `SOCK_DGRAM`: Datagram Socket Type {#term-sock-dgram}

Socket type providing connectionless, message-boundary-preserving packet delivery (UDP over IP or datagram AF_UNIX). Each sendto() produces one discrete datagram; readers receive either an entire message or a truncated prefix if the receive buffer is smaller than the payload. (Ch. 11, 14)

```rust
let fd = unsafe { libc::socket(libc::AF_INET, libc::SOCK_DGRAM, 0) };
```

### `SOCK_STREAM`: Stream Socket Type {#term-sock-stream}

Socket type providing reliable, ordered, full-duplex byte-stream transport (TCP over IP or stream AF_UNIX). Because SOCK_STREAM preserves byte order rather than write boundaries, a single read() may return partial or coalesced writes, making explicit application framing mandatory. (Ch. 11, 13, 14)

```rust
let fd = unsafe { libc::socket(libc::AF_INET, libc::SOCK_STREAM, 0) };
```

### `SPSC`: Single-Producer, Single-Consumer Ring Buffer {#term-spsc}

Lock-free bounded queue topology with exactly one writer updating the head index and one reader updating the tail index using Acquire/Release atomics on separate 64-byte cache lines. Eliminating Compare-And-Swap loops and locks makes SPSC rings the fastest inter-thread and io_uring handoff primitive. (Ch. 6, 19)

```rust
// Producer publishes slot with Release; consumer observes it with Acquire
let h = head.load(Ordering::Relaxed);
if h.wrapping_sub(tail.load(Ordering::Acquire)) < CAP {
    buf[h & (CAP - 1)] = item;
    head.store(h.wrapping_add(1), Ordering::Release);
}
```

### `SQMS`: Single-Queue Multiprocessor Scheduling {#term-sqms}

Simple SMP scheduler design sharing one global runqueue protected by a single mutex across all CPU cores. Although load balancing is trivial, global lock contention and constant thread migration across cores destroy L1/L2 cache locality as core counts grow, motivating MQMS. (Ch. 5)

```rust
// One shared mutex serializes every core's dispatch decision
let next = global_runqueue.lock().unwrap().pop_front();
```

### `SR-IOV`: Single Root I/O Virtualization {#term-sr-iov}

PCIe hardware feature splitting one physical NIC into multiple independent virtual functions that the hypervisor assigns directly to guest VMs via the IOMMU for near-bare-metal throughput. (Ch. 16)

### `SRAM`: Static Random-Access Memory {#term-sram}

Six-transistor on-chip memory requiring no refresh, used to build L1 (~1 ns), L2 (~4 ns), and L3 (~15 ns) caches at far higher cost per byte than off-chip DRAM. (Ch. 2)

### `SSD`: Solid-State Drive {#term-ssd}

Non-volatile flash storage device accessed over NVMe/PCIe (~50 to 200 µs latency). Volatile controller write caches still require an explicit fsync() flush to guarantee crash durability. (Ch. 12, 18)

### `SSE`: Streaming SIMD Extensions {#term-sse}

128-bit x86-64 vector instruction set whose aligned load/store instructions require 16-byte address alignment, shaping the System V AMD64 allocator contract. (Ch. 19)

### `STCF`: Shortest Time-to-Completion First Scheduling {#term-stcf}

Preemptive refinement of SJF that immediately preempts a running job whenever a newly arriving task has less remaining CPU time. STCF achieves optimal average turnaround time across arbitrary arrival patterns, though real kernels approximate it with MLFQ or EEVDF because future burst lengths are unknown. (Ch. 5)

```rust
// Always dispatch the runnable job with minimum remaining CPU time
if let Some(best) = ready.iter().min_by_key(|j| j.remaining_us) {
    dispatch(best.id);
}
```

### `STLB`: Shared Translation Lookaside Buffer (L2) {#term-stlb}

Second-level unified per-core TLB (1,024 to 2,048 entries) backing L1 instruction and data TLBs. With 4 KiB pages, 1,536 entries cover 6 MiB; with 2 MiB huge pages, the same entries cover 3 GiB. (Ch. 7)

### `SYN`: Synchronize (TCP) {#term-syn}

TCP control flag opening the three-way handshake (SYN, SYN-ACK, ACK) to synchronize initial byte sequence numbers before user data flows. (Ch. 13, 14)

### `TCB`: Thread Control Block {#term-tcb}

Per-thread kernel structure storing saved registers, kernel stack pointer, Thread-Local Storage base, and scheduler runqueue state. (Ch. 4, 6)

### `TCP`: Transmission Control Protocol {#term-tcp}

Connection-oriented, reliable, ordered byte-stream transport over IP. Because TCP coalesces or splits writes freely, higher-level protocols must frame every message explicitly. (Ch. 2, 11, 13, 14, 15)

```rust
use std::net::TcpListener;
let listener = TcpListener::bind("127.0.0.1:45678")?;
```

### `TCP_NODELAY`: Disable Nagle's Algorithm Socket Option {#term-tcp-nodelay}

TCP socket option disabling Nagle's coalescing timer so small outbound writes transmit immediately instead of waiting for prior ACKs. Leaving Nagle enabled alongside TCP Delayed ACK introduces artificial 40 to 200 ms stalls on interactive RPC and request/response protocols. (Ch. 13, 14)

```rust
stream.set_nodelay(true)?; // sets TCP_NODELAY to avoid Nagle + Delayed ACK stalls
```

### `TIME_WAIT`: TCP Active-Close Cooldown State (2 MSL) {#term-time-wait}

60- to 120-second state held by whichever TCP endpoint sent the final ACK of a four-way close. TIME_WAIT ensures the peer receives a retransmitted final ACK if lost and prevents delayed duplicate packets from corrupting a fresh connection on the same 4-tuple; bind() restarts pair it with SO_REUSEADDR. (Ch. 13, 14)

```rust
// Enable SO_REUSEADDR before bind() so restarts bypass lingering TIME_WAIT sockets
let listener = std::net::TcpListener::bind("127.0.0.1:8080")?;
```

### `TLB`: Translation Lookaside Buffer {#term-tlb}

Core-private associative cache storing recent VPN-to-PFN translations (~1 cycle hit), avoiding 4 sequential memory reads per load. Because TLBs are not coherent across cores, unmapping shared pages requires synchronous IPI shootdowns. (Ch. 4, 7, 13, 16, 18, 19)

### `TLS`: Transport Layer Security / Thread-Local Storage {#term-tls}

In networking (Ch. 14), cryptographic protocol encrypting TCP connections. In threading (Ch. 3, 4), per-thread private variable storage anchored at FS_BASE (x86-64) or TPIDR_EL0 (ARM64) for lock-free thread-local state like errno.

### `TSO`: Total Store Order Memory Model {#term-tso}

Hardware memory consistency model implemented by x86-64 that guarantees loads never reorder with loads and stores never reorder with stores, while still allowing a local store in a core's FIFO store buffer to appear after a subsequent load. Relying on TSO without explicit Acquire/Release atomics causes subtle data races when porting lock-free code to weakly ordered ARM64. (Ch. 6)

```rust
// Explicit SeqCst / Acquire-Release fences keep lock-free code portable beyond x86-64 TSO
flag.store(true, Ordering::Release);
let observed = ready.load(Ordering::Acquire);
```

### `TSS`: Task State Segment (x86-64) {#term-tss}

Per-core x86-64 hardware structure supplying the Ring 0 kernel stack pointer (RSP0) and dedicated Interrupt Stack Table pointers whenever an exception or interrupt vectors out of Ring 3. Without a valid TSS kernel stack, a hardware interrupt arriving while Ring 3 holds a corrupted or full user stack would trigger a fatal triple fault. (Ch. 2, 9)

```rust
// On every Ring 3 -> Ring 0 trap, hardware loads RSP from TSS.RSP0
#[repr(C, packed)]
struct Tss64Head { reserved0: u32, rsp0: u64, rsp1: u64, rsp2: u64 }
```

### `TTBR0_EL1 / TTBR1_EL1`: Translation Table Base Registers {#term-ttbr0}

Dual ARM64 root page-table registers separating user-space (TTBR0_EL1) and kernel-space (TTBR1_EL1) mappings natively in silicon without requiring CR3 switches on syscalls. (Ch. 3, 4, 7)

### `TTY`: Teletype (Terminal Device) {#term-tty}

Character device mediating interactive keyboard input, line discipline, and foreground job-control signals (SIGINT, SIGHUP). Daemons double-fork so they can never accidentally acquire a controlling TTY. (Ch. 15)

### `UDP`: User Datagram Protocol {#term-udp}

Connectionless, boundary-preserving datagram transport with an 8-byte header and zero handshake delay, ideal for DNS, telemetry, real-time media, and QUIC. Oversized datagrams are truncated without error if the receive buffer is too small. (Ch. 13, 14)

```rust
use std::net::UdpSocket;
let sock = UdpSocket::bind("127.0.0.1:0")?;
sock.send_to(b"ping-udp", "127.0.0.1:45680")?;
```

### `UID`: User Identifier {#term-uid}

Numeric Unix identity governing file ownership and privilege checks (UID 0 is root; user namespaces map container UID 0 to an unprivileged host UID). (Ch. 3, 12, 16)

### `UMA`: Unified Memory Architecture {#term-uma}

SoC memory design (such as Apple Silicon) where CPU, GPU, and NPU share one physical high-bandwidth memory pool, eliminating PCIe DMA copies while still requiring explicit cache flushes and command-buffer fences. (Ch. 17)

### `UPI`: Ultra Path Interconnect {#term-upi}

Intel high-speed point-to-point cache-coherent fabric linking multi-socket NUMA processors and carrying remote DRAM requests and MESI invalidations. (Ch. 5, 17)

### `USDT`: User-Level Statically Defined Tracing {#term-usdt}

Zero-overhead instrumentation probes embedded as NOP instructions in compiled user-space binaries (with metadata in ELF notes) that eBPF or DTrace can patch dynamically at runtime. USDT lets operators inspect live database queries or allocator events in production without recompiling or paying logging overhead when disabled. (Ch. 18)

```rust
// Attach an eBPF tracepoint to a compiled USDT probe at runtime:
// bpftrace -e 'usdt:./server:http:request_start { @reqs = count(); }'
```

### `VA`: Virtual Address {#term-va}

Program pointer address inside a process's private linear address space, sliced into four 9-bit radix indices and an invariant 12-bit page offset on 48-bit x86-64 systems. (Ch. 7)

### `vCPU`: Virtual Central Processing Unit {#term-vcpu}

Virtual core exposed to a guest OS, backed by a host thread and a hardware VMCS structure scheduled across physical host cores by the hypervisor. (Ch. 16)

### `vDSO`: Virtual Dynamic Shared Object {#term-vdso}

Read-only kernel page mapped directly into user space on Linux so high-frequency calls like clock_gettime() read calibrated hardware counters in ~15 ns without trapping into Ring 0. (Ch. 9)

### `VFIO`: Virtual Function I/O {#term-vfio}

Linux framework exposing physical PCIe devices directly to a VM or user-space driver safely through IOMMU DMA isolation. (Ch. 16)

### `VFS`: Virtual File System {#term-vfs}

Kernel abstraction layer defining uniform inode, dentry, superblock, and file operations so POSIX syscalls (open, read, stat, mmap) work identically across ext4, XFS, APFS, tmpfs, pipes, and /proc. Without VFS, every user application would need filesystem-specific code paths. (Ch. 12)

```rust
// Uniform POSIX VFS interface reads regular files, /proc entries, and pipes identically
let text = std::fs::read_to_string("/proc/self/stat")?;
```

### `VM`: Virtual Machine {#term-vm}

Hardware-isolated guest execution environment running an independent kernel atop a hypervisor, providing a strong multi-tenant security boundary at higher memory overhead than containers. (Ch. 16)

### `VMA`: Virtual Memory Area {#term-vma}

Kernel interval record (vm_area_struct) tracking every valid virtual region (text, heap, mmap, stack) and its logical permissions, consulted by the page-fault handler to distinguish lazy allocation from illegal SIGSEGV accesses. (Ch. 3, 7)

### `VMCS`: Virtual Machine Control Structure {#term-vmcs}

In-memory Intel VT-x state block storing guest registers, host registers, EPT root pointer, and VM-Exit intercept bitmaps for one vCPU. (Ch. 16)

### `VMX`: Virtual Machine Extensions {#term-vmx}

Intel VT-x execution architecture separating the host hypervisor (VMX Root) from guest kernels (VMX Non-Root) orthogonally to Rings 0 through 3. (Ch. 16)

### `VPID`: Virtual Processor Identifier {#term-vpid}

Intel hardware TLB tag isolating host and guest virtual translations across VM-Exit and VM-Entry without flushing the TLB. (Ch. 16)

### `VPN`: Virtual Page Number {#term-vpn}

Upper virtual address bits (VA &gt;&gt; 12) identifying a 4 KiB virtual page and indexing the TLB or 4-level radix page table while the low 12-bit offset passes through unmodified. (Ch. 7)

### `VRAM`: Video Random-Access Memory {#term-vram}

Dedicated high-bandwidth memory soldered onto discrete GPU cards, requiring explicit PCIe DMA copies and host page pinning when moving tensors from CPU DRAM. (Ch. 17)

### `VT-x`: Intel Virtualization Technology {#term-vt-x}

Intel x86-64 hardware virtualization extensions providing VMX Root/Non-Root execution modes, VMCS state switching, and Extended Page Tables. (Ch. 16)

### `W^X`: Write XOR Execute {#term-wx}

Memory-safety invariant prohibiting any virtual page from being simultaneously writable and executable, enforced in hardware via PTE bit 63 (NX = 1) on stack and heap allocations. (Ch. 7)

```rust
// Guard page: strip all R/W/X permissions in hardware PTE
unsafe { libc::mprotect(guard_ptr, page_size, libc::PROT_NONE) };
```

### `WAL`: Write-Ahead Log {#term-wal}

Crash-recovery protocol appending every state mutation sequentially to a durable log (flushed via fsync()) before applying in-place updates to primary data structures or filesystem metadata. If power fails mid-operation, replaying committed WAL records restores a consistent state without corruption. (Ch. 12)

```rust
use std::io::Write;
wal_file.write_all(entry_bytes)?;
wal_file.sync_data()?; // commit WAL record before mutating B-tree pages
```

### `WNOHANG`: Non-Blocking Wait Flag {#term-wnohang}

waitpid() option flag returning 0 immediately when child processes are still alive instead of blocking the caller. Event loops and SIGCHLD handlers loop over waitpid(-1, &amp;mut status, WNOHANG) until it returns 0 or ECHILD to reap every coalesced zombie without stalling the process. (Ch. 3, 10, 15)

```rust
let mut status: libc::c_int = 0;
while unsafe { libc::waitpid(-1, &mut status, libc::WNOHANG) } > 0 {
    // Reaped a terminated child without blocking
}
```

  
### `XFS`: Extended File System {#term-xfs}

  High-performance 64-bit journaling, extent-based Linux filesystem engineered for parallel multi-core I/O scalability and massive file sizes. (Ch. 12)

### `XNU`: X is Not Unix (Darwin Kernel) {#term-xnu}

Hybrid kernel powering macOS and Apple platforms, combining a Mach microkernel core (tasks, threads, Mach ports) with a BSD POSIX layer (processes, sockets, kqueue). (Ch. 3, 5)

## Additional Kernel Constants, Registers & Protocols

### `SRTF`: Shortest Remaining Time First {#term-srtf}

Preemptive variant of Shortest Job First that immediately switches the processor to any newly arriving job whose remaining burst is shorter than the active job. It minimizes average turnaround time in theory, yet requires predicting future CPU bursts and risks starving long compute jobs under steady short arrivals. (Ch. 5)

```rust
let next = ready.iter().min_by_key(|job| job.remaining_ms);
```

### `RMW`: Read-Modify-Write {#term-rmw}

Indivisible hardware instruction sequence that loads a memory word, computes a new value, and stores it back without allowing another core to interleave between the load and store. Atomics such as fetch_add and compare_exchange compile to RMW instructions like LOCK XADD or LDADDAL. (Ch. 2, 4, 6)

```rust
use std::sync::atomic::{AtomicU64, Ordering};
let prev = counter.fetch_add(1, Ordering::AcqRel);
```

### `TAS`: Test-and-Set {#term-tas}

Minimal atomic spinlock primitive that atomically writes true to a lock flag and returns its previous value. Under multi-core contention, repeated failed writes bounce the cache line in Modified state across cores and provide no FIFO fairness. (Ch. 6)

```rust
use std::sync::atomic::{AtomicBool, Ordering};
while lock.swap(true, Ordering::Acquire) { std::hint::spin_loop(); }
```

### `LDE`: Limited Direct Execution {#term-lde}

Core operating system execution model: programs run instructions directly on the physical CPU in unprivileged user mode at full speed, while hardware traps (system calls, faults, and timer interrupts) hand control back to the kernel to enforce isolation and preemption. (Ch. 3)

```rust
// User code executes directly until a trap or timer interrupt enters Ring 0
let pid = std::process::id();
```

### `PIP`: Priority Inheritance Protocol {#term-pip}

Real-time scheduling mechanism that temporarily elevates the priority of a low-priority thread holding a mutex to match the highest-priority thread blocked on that mutex, preventing unbounded priority inversion by medium-priority threads. (Ch. 5)

```rust
// Linux POSIX mutex attribute: PTHREAD_PRIO_INHERIT
// Prevents medium-priority threads from preempting a lock holder
```

### `PCP`: Priority Ceiling Protocol {#term-pcp}

Real-time lock protocol assigning each mutex a static priority ceiling equal to the highest priority of any thread that may acquire it, elevating the holder immediately on acquisition to prevent both priority inversion and chained blocking. (Ch. 5)

```rust
// Linux POSIX mutex attribute: PTHREAD_PRIO_PROTECT
// Raises holder to the mutex ceiling immediately upon lock acquisition
```

### `PIPE_BUF`: Atomic Pipe Write Threshold {#term-pipe-buf}

POSIX minimum guaranteed size (at least 512 bytes; 4,096 bytes on Linux and macOS) for which a single write to a pipe or FIFO is guaranteed not to interleave with concurrent writes from other processes. Writes larger than PIPE_BUF may fragment and interleave. (Ch. 11)

```rust
const MAX_ATOMIC_MSG: usize = libc::PIPE_BUF;
assert!(payload.len() <= MAX_ATOMIC_MSG);
```

### `RTT`: Round-Trip Time {#term-rtt}

Elapsed network latency for a packet to travel from sender to receiver and for the corresponding acknowledgment to return. Together with link bandwidth, RTT determines the Bandwidth-Delay Product required to keep a TCP pipe full. (Ch. 14)

```rust
let bdp_bytes = (bandwidth_bps / 8.0) * rtt_seconds;
```

### `WAF`: Write Amplification Factor {#term-waf}

Ratio of physical bytes written to NAND flash by an SSD Flash Translation Layer to logical bytes written by the host operating system. Random small writes trigger heavy garbage collection and push WAF well above 1.0, wearing out flash cells prematurely. (Ch. 12)

```rust
let waf = physical_flash_bytes_written as f64 / host_logical_bytes as f64;
```

### `TMA`: Top-Down Microarchitecture Analysis {#term-tma}

Structured CPU performance methodology that classifies every pipeline issue slot into four mutually exclusive categories: Retiring, Bad Speculation, Frontend Bound, or Backend Bound, pinpointing whether code is stalled on instruction fetch, branch misses, or memory latency. (Ch. 18)

```rust
// Measure with: perf stat --topdown -a -- ./benchmark
```

### `EPOLLET`: Edge-Triggered epoll Mode {#term-epollet}

Linux epoll registration flag that delivers a readiness notification only when a file descriptor transitions from not-ready to ready. Callers must drain the non-blocking descriptor in a loop until EAGAIN or risk permanent stalls on unread buffered bytes. (Ch. 13)

```rust
let ev = libc::epoll_event { events: (libc::EPOLLIN | libc::EPOLLET) as u32, u64: fd as u64 };
```

### `POLLOUT`: Socket Writable Readiness Event {#term-pollout}

Event-loop readiness flag indicating that the kernel socket send buffer has free space to accept outgoing bytes without blocking. Servers arm POLLOUT only when a non-blocking write returns EAGAIN and disarm it once the send queue drains. (Ch. 13)

```rust
let pfd = libc::pollfd { fd, events: libc::POLLIN | libc::POLLOUT, revents: 0 };
```

### `FUTEX_WAIT`: Futex Sleep Operation {#term-futex-wait}

Kernel futex command that atomically verifies *addr == expected under the wait-queue hash-bucket spinlock and parks the calling thread only if the condition still holds, closing the lost-wakeup race between user-mode state checks and kernel sleep. (Ch. 6)

```rust
// Only parks in Ring 0 if atomic state still equals 2 (contended)
// Returns EAGAIN immediately if another thread already unlocked
```

### `FUTEX_WAKE`: Futex Wakeup Operation {#term-futex-wake}

Kernel futex command that acquires the hash-bucket spinlock for a user-space address and transitions up to N parked waiters back onto the CPU runqueue when a contended lock or condition variable is released. (Ch. 6)

```rust
// Invoked on unlock only when previous state was 2 (waiters present)
```

### `MSG_ZEROCOPY`: Zero-Copy Socket Transmit Flag {#term-msg-zerocopy}

Linux send(2) flag that pins user-space memory pages and hands them directly to the NIC DMA engine instead of copying into kernel sk_buffs, notifying the sender via MSG_ERRQUEUE once the buffer is safe to reuse. (Ch. 14)

```rust
// Enable with setsockopt(fd, SOL_SOCKET, SO_ZEROCOPY, &1)
// Transmit with send(fd, buf, len, MSG_ZEROCOPY)
```

### `NAND`: NAND Flash Storage {#term-nand}

Non-volatile solid-state memory organized into 4 to 16 KiB pages (the unit of reads and writes) grouped into multi-megabyte erase blocks (the unit of erasure). Because flash pages cannot be overwritten in place, SSDs require a Flash Translation Layer. (Ch. 12)

```rust
// Sequential writes align with NAND erase blocks and minimize garbage collection
```

### `LBA`: Logical Block Address {#term-lba}

Linear block index exposed by an NVMe SSD or disk to the operating system. Inside an SSD, the Flash Translation Layer dynamically remaps each LBA to a physical NAND page on every write. (Ch. 12)

```rust
let lba_index: u64 = file_byte_offset / 4096;
```

### `PAN`: Privileged Access Never {#term-pan}

ARM64 hardware security feature (analogous to x86-64 SMAP) that traps any accidental kernel-mode load or store to user-space virtual memory unless executed through explicit copy_from_user or copy_to_user helpers. (Ch. 9)

```rust
// Enforced in hardware via PSTATE.PAN across EL1 kernel execution
```

### `ALU`: Arithmetic Logic Unit {#term-alu}

Combinational hardware circuit inside each CPU core that performs integer arithmetic, bitwise logic, and comparisons directly on architectural registers within a single clock cycle. (Ch. 2)

```rust
let sum = a.wrapping_add(b); // Single-cycle integer ALU add
```

### `MLP`: Memory-Level Parallelism {#term-mlp}

Ability of an out-of-order CPU core to keep multiple independent DRAM cache misses in flight concurrently via Line Fill Buffers, hiding 60 to 100 ns memory latency behind overlapped transfers. (Ch. 18)

```rust
// Independent array streams exploit MLP; linked-list pointer chasing serializes misses
```

### `LIFO`: Last-In, First-Out {#term-lifo}

Stack ordering discipline where the most recently pushed item is popped first. Kernel slab caches and thread pools often prefer LIFO order because the most recently freed object is still hot in L1/L2 cache. (Ch. 8, 17)

```rust
let mut freelist: Vec<usize> = Vec::new();
freelist.push(slot); let hot_slot = freelist.pop();
```

### `EPERM`: Operation Not Permitted Error {#term-eperm}

POSIX errno indicating that the calling process lacks the required privilege or that an operation is structurally forbidden, such as calling epoll_ctl on a regular disk file or setsid from a process group leader. (Ch. 13, 15)

```rust
if err.raw_os_error() == Some(libc::EPERM) { /* lacking privilege or invalid fd type */ }
```

### `C10M`: Ten Million Concurrent Connections {#term-c10m}

Systems scaling regime requiring kernel-bypass or completion-based I/O (io_uring, DPDK), per-core sharded state, and zero-copy packet paths because thread-per-connection memory and syscall overhead collapse well before 10 million sockets. (Ch. 13)

```rust
// Event-driven reactor + io_uring replaces 10M thread stacks with shared ring buffers
```

### `ZFS`: Zettabyte File System {#term-zfs}

Copy-on-write, end-to-end checksummed filesystem and volume manager that writes modified data and metadata into fresh blocks and commits atomically by updating a single root uberblock, eliminating in-place write-hole corruption. (Ch. 12)

```rust
// Copy-on-write root pointer swap makes every transaction atomic across power loss
```

### `RSP`: Stack Pointer Register (x86-64) {#term-rsp}

64-bit x86-64 architectural register pointing to the top (lowest address) of the active thread call stack. Calling a function decrements RSP to push the return address; returning increments it. (Ch. 2, 3)

```rust
// ARM64 equivalents: SP_EL0 (user stack) and SP_EL1 (kernel stack)
```

### `RIP`: Instruction Pointer Register (x86-64) {#term-rip}

64-bit x86-64 program counter holding the virtual address of the next instruction to fetch and execute. Saved automatically onto the kernel stack during traps and interrupts. (Ch. 2, 3)

```rust
// Hardware pushes RIP onto the kernel trapframe on interrupt or exception
```

### `RFLAGS`: Processor Flags Register (x86-64) {#term-rflags}

64-bit x86-64 status register holding arithmetic condition codes (Zero, Carry, Sign) and system control bits such as the Interrupt Flag (IF) that masks or enables hardware interrupts. (Ch. 2)

```rust
// Saved and restored atomically across interrupts by hardware iretq
```

### `FS_BASE`: x86-64 Thread-Local Base Register {#term-fs-base}

Model-specific x86-64 segment base register storing the per-thread pointer to Thread-Local Storage (TLS) so accessing thread-local variables like errno requires a single register-offset load with zero locks. (Ch. 4, 9)

```rust
thread_local! { static PER_THREAD_ID: std::cell::Cell<u64> = const { std::cell::Cell::new(0) }; }
```

### `TPIDR_EL0`: ARM64 Thread-Local Base Register {#term-tpidr}

ARM64 user-readable system register holding the base address of the current thread Thread-Local Storage block, serving the exact role of FS_BASE on x86-64. (Ch. 4, 9)

```rust
// Kernel swaps TPIDR_EL0 on every thread context switch
```

### `VBAR_EL1`: Vector Base Address Register (ARM64) {#term-vbar}

ARM64 EL1 system register pointing to the base address of the kernel exception vector table, analogous to IDTR on x86-64. (Ch. 2)

```rust
// Hardware jumps to VBAR_EL1 + vector_offset on synchronous traps and IRQs
```

### `GICD / GICR`: GIC Distributor and Redistributor {#term-gicd}

ARM64 GICv3 hardware components: the global Distributor (GICD) routes shared peripheral interrupts across cores, while each core private Redistributor (GICR) manages per-core SGI and PPI delivery. (Ch. 2)

```rust
// Replaces x86-64 IO-APIC (shared) and Local APIC (per-core)
```

### `SGI / PPI`: Software-Generated & Private Peripheral Interrupts {#term-sgi}

ARM64 core-local interrupt classes: SGIs (vectors 0 to 15) implement cross-core Inter-Processor Interrupts (IPIs), while PPIs (vectors 16 to 31) deliver per-core timer signals. (Ch. 2)

```rust
// Delivered directly through the target core GICR without global distributor contention
```

### `MSI`: Message Signaled Interrupts {#term-msi}

PCIe interrupt mechanism in which a device writes a small DMA message directly to the interrupt controller address space instead of asserting a shared physical IRQ wire, eliminating pin-sharing latency. (Ch. 2)

```rust
// Extended by MSI-X to support up to 2,048 independent per-queue vectors
```

### `SIG_BLOCK / SIG_UNBLOCK`: Signal Mask Operations {#term-sig-block}

Commands passed to sigprocmask or pthread_sigmask to atomically add signals to or remove signals from the thread blocked signal mask, deferring asynchronous delivery across critical sections. (Ch. 10)

```rust
// Block SIGTERM before entering a critical section; unblock or wait via pselect/signalfd
```

### `LISTEN_FDS`: systemd Socket Activation Environment Variable {#term-listen-fds}

Environment variable set by systemd indicating how many pre-bound listening file descriptors (starting at fd 3) were inherited across exec, enabling zero-downtime restarts without dropping connections. (Ch. 15)

```rust
let count: usize = std::env::var("LISTEN_FDS").ok().and_then(|v| v.parse().ok()).unwrap_or(0);
```

### `PR_SET_CHILD_SUBREAPER`: Linux Process Subreaper Flag {#term-subreaper}

Linux prctl(2) attribute designating a supervisor process to inherit orphaned descendants instead of PID 1, allowing service managers to track and reap grandchildren cleanly. (Ch. 15)

```rust
// unsafe { libc::prctl(libc::PR_SET_CHILD_SUBREAPER, 1, 0, 0, 0) };
```

### `CLONE_VM`: Linux Shared Address Space Clone Flag {#term-clone-vm}

Linux clone(2) flag instructing the kernel to share the caller virtual memory descriptor (mm_struct) with the newly created task, turning a clone call into a lightweight OS thread rather than an isolated process. (Ch. 3, 4)

```rust
// Combined with CLONE_THREAD | CLONE_FILES | CLONE_SIGHAND by pthread_create
```

### `SOL_SOCKET`: Socket-Level Option Namespace {#term-sol-socket}

Protocol level constant passed to setsockopt and getsockopt for transport-independent socket options such as SO_REUSEADDR, SO_KEEPALIVE, SO_RCVBUF, and SO_PEERCRED. (Ch. 11, 14)

```rust
// unsafe { libc::setsockopt(fd, libc::SOL_SOCKET, libc::SO_REUSEADDR, &one as *const _ as *const _, 4) };
```
