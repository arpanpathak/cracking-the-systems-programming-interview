# Book Enhancement Plan & Systems Engineering Roadmap

## Context & Objectives
This book, *Operating Systems: A Hands-On Approach*, is a rigorous, production-grade systems software textbook and senior interview preparation guide (targeting high-bar engineering organizations such as Apple Cloud OS, Meta, Google, Jane Street, and Datadog).

To prevent context degradation, hallucinations, or regressions, **all future agent runs MUST proceed incrementally**, executing one discrete phase at a time and committing verified changes to Git after running both the Technical Prose Quality Audit and the SVG Diagram Visual & Geometric Audit.

---

## Non-Negotiable Engineering Rules for Agents
1. **NO ASCII ART**: Never insert ASCII box drawings or text-based diagrams into markdown files. All diagrams MUST be Material Design SVGs generated via `tools/draw_figures.py` and `tools/figkit.py`, rendered to `src/figures/` (and `src/figures/dark/`), and embedded with `<figure><img src="figures/....svg" alt="..."/></figure>`.
2. **Formal Technical English**: Maintain formal, rigorous Computer Science English. Strictly eliminate casual phrasing (e.g., "basically", "under the hood", "sort of", "magic") and ungrounded buzzwords. Retain established ontological chapter framing (e.g., *Chapter 1: The Ontological Necessity of the Operating System*).
3. **Rigorous Rust Safety Documentation**: All `unsafe` blocks and low-level POSIX bindings must include detailed `// SAFETY:` docstrings proving invariants, pointer validity, alignment, provenance, and lifecycle guarantees.
4. **Zero-Warning Code Compilation**: All listings must compile cleanly under `-std=c++20 -O2 -Wall -Wextra -Werror` and `rustc --edition 2024 -D warnings -O`.
5. **Quality & Diagram Audit Verification Gates**: Every agent run must execute both the automated technical prose audit script and the automated SVG diagram geometry/collision audit script (plus headless Chrome visual rendering check) before concluding.
6. **Always Verify**: After any changes, always run:
   ```bash
   python3 tools/draw_figures.py
   ./code/run_all.sh
   mdbook build
   ./scripts/generate_pdf.sh
   git status
   ```

---

## Quality Audit Protocol: Computer Science Engineering Technical Writing & SVG Diagrams

Every section and diagram of this book must adhere to the editorial standards of premier computer systems literature (e.g., ACM SOSP, USENIX OSDI, and foundational treatises by Saltzer & Kaashoek, McKusick, and Kerrisk).

### 1. Lexical & Stylistic Invariants
- **Zero Colloquialisms**: Strictly prohibit informal expressions (`basically`, `under the hood`, `kind of`, `sort of`, `pretty much`, `in a nutshell`, `handy`, `magic`, `stuff`). Replace them with exact systems terminology (e.g., instead of "under the hood it does X", use "at the microarchitectural level, the control unit executes X").
- **No Buzzword Inflation**: Reject vague technology buzzwords. Ground every concept in concrete hardware structures (registers, bus interfaces, TLBs, DRAM controllers) or kernel state structures (page tables, PCBs, file descriptor tables).
- **Active & Precise Technical Voice**: State the operating principle, the failure condition without it, the hardware mechanism enforcing it, and the software policy governing it.

### 2. Ontological & Conceptual Depth
- **First-Principles Framing**: Every chapter must begin with its ontological necessity—why the bare physical hardware fails to provide concurrency, memory protection, or resource isolation without the supervisory layer.
- **Mechanism vs. Policy Separation**: Always clearly bifurcate hardware-enforced primitives (context switches, radix page walks, trap dispatches) from kernel scheduling and eviction algorithms (CFS, LRU, Round-Robin).
- **Compound Modifiers & Terminology Consistency**:
  - Always hyphenate compound attributive adjectives: `user-mode execution`, `kernel-level authority`, `lock-free ring buffer`, `zero-copy transfer`, `copy-on-write page fault`.
  - Use standardized naming across x86-64 and ARM64: `PC` / `RIP` / `PC_EL0`, `SP` / `RSP` / `SP_EL0`, `FP` / `RBP` / `x29`, `FLAGS` / `RFLAGS` / `PSTATE`.

### 3. SVG Diagram Geometric & Visual Invariants
Every SVG diagram in `tools/draw_figures.py` must satisfy four strict geometric invariants:
1. **Zero Text Overflow (`data-fit`)**: Every label and heading inside a container or card must pass `figkit.py`'s `width_of()` check with zero `"does not fit"` warnings and at least `6px` horizontal padding inside its bounding box.
2. **Zero Text-on-Text Collision**: No two `<text>` bounding boxes may overlap horizontally and vertically.
3. **Zero Arrow-Through-Text / Card Collision**: Orthogonal wires (`fig.wire`) must be routed strictly through empty whitespace corridors between cards (`>= 24px` gap so `10px` arrowheads never clip). Labels on vertical wires must either use `anchor="start"` / `anchor="end"` offset by `10-12px` to the side of the wire, or use `backed=True` in an uncrowded corridor.
4. **Visual Screenshot Verification**: New or modified SVGs must be rendered to PNG via Headless Chrome (`--headless=new --window-size=840,700 --screenshot=...`) and visually inspected to confirm crisp alignment of legends, arrowheads, and cards.

### 4. Automated Prose & SVG Geometry Audit Script
Before committing changes in any phase, execute this combined audit check:
```bash
python3 -c '
import glob, re, sys, xml.etree.ElementTree as ET
sys.path.insert(0, "tools")
import figkit

filler_patterns = [
    r"\bbasically\b", r"\bunder the hood\b", r"\bsort of\b",
    r"\bkind of\b", r"\bpretty much\b", r"\bin a nutshell\b",
    r"\bstuff\b", r"\bhandy\b", r"\bneat\b"
]

errors = []
for f in sorted(glob.glob("src/*.md") + glob.glob("code/ch*/*.cpp") + glob.glob("code/ch*/*.rs")):
    text = open(f).read()
    if "+---" in text or "┌──" in text or "|   |" in text:
        errors.append(f"{f}: ASCII art box detected!")
    if re.search(r"\$\$|\$[^$\n]+\$|\\text\{|\\frac\{|\\ge\b|\\le\b|\\times\b", text):
        errors.append(f"{f}: Unrendered raw LaTeX delimiter/macro detected! Use HTML <sup>/<sub>/&times;/&ge; instead.")
    if f.endswith(".md"):
        for pat in filler_patterns:
            if re.search(pat, text, re.I):
                errors.append(f"{f}: Casual filler pattern {pat} detected!")

for f in sorted(glob.glob("src/figures/*.svg")):
    tree = ET.parse(f)
    texts = []
    def walk(el, dx=0.0, dy=0.0):
        tr = el.attrib.get("transform", "")
        m = re.search(r"translate\(\s*([-\d.]+)\s+([-\d.]+)\s*\)", tr)
        if m:
            dx += float(m.group(1)); dy += float(m.group(2))
        if el.tag.split("}")[-1] == "text" and "rotate" not in tr:
            x = float(el.attrib.get("x", 0)) + dx
            y = float(el.attrib.get("y", 0)) + dy
            cls = next((c for c in el.attrib.get("class", "sub").split() if c in figkit.FONTS), "sub")
            anchor = el.attrib.get("text-anchor", "start")
            txt = "".join(el.itertext())
            w = figkit.width_of(txt, cls)
            size = figkit.FONTS[cls][0]
            x0 = {"start": x, "middle": x - w/2, "end": x - w}[anchor]
            texts.append((txt, x0, y - size*0.85, x0 + w, y + size*0.2, el.attrib.get("data-fit")))
        for child in el:
            walk(child, dx, dy)
    walk(tree.getroot())
    for i, (t1, x0, y0, x1, y1, fit) in enumerate(texts):
        if fit:
            low, high = map(float, fit.split(","))
            if x0 < low - 1.5 or x1 > high + 1.5:
                errors.append(f"{f}: SVG fit overflow on {t1!r} ({x0:.1f}..{x1:.1f} vs {low:.1f}..{high:.1f})")
        for t2, bx0, by0, bx1, by1, _ in texts[i+1:]:
            if min(x1, bx1) - max(x0, bx0) > 3 and min(y1, by1) - max(y0, by0) > 3:
                errors.append(f"{f}: SVG text overlap between {t1!r} and {t2!r}")

if errors:
    print("\n".join(errors))
    exit(1)
else:
    print("Quality & SVG Geometry Audit Passed: Zero ASCII art, zero filler words, zero SVG text overflows/overlaps.")
'
```

---

## Completed Foundation Phases (Phases 1–5)

### Phase 1: Microarchitecture, Interrupt Subsystem & Process/Thread Lifecycles (Chapters 2, 3, 4) — [COMPLETED & AUDITED]
- [x] **Processor Registers & Datapath (Ch 2)**: Formal explanation of `PC`/`RIP`/`PC_EL0`, `SP`/`RSP`/`SP_EL0`, `FP`/`RBP`/`x29`, `FLAGS`/`RFLAGS`/`PSTATE`, GPR calling conventions (System V AMD64 & AAPCS64), 4-stage out-of-order fetch-decode-execute pipeline, function activation records, and 128-byte Red Zone.
- [x] **Atomicity Gap (Ch 2)**: Formal derivation of 3-instruction Read-Modify-Write (`mov`/`ldr`, `add`, `mov`/`str`) decomposition and lost updates across L1 data caches.
- [x] **Interrupt Subsystem Depth (Ch 2)**: IO-APIC Redirection Tables, Local APIC, PCIe MSI-X, ARM GICv3/v4 (`GICD`, `GICR`, `ITS`), IDT (`IDTR`) and `VBAR_EL1`, hardware context save onto `TSS.rsp0` (`SS`, `RSP`, `RFLAGS`, `CS`, `RIP`, error code + GPR trapframe), Top-Half (`hardirq`) vs. Bottom-Half (`softirq`, NAPI, workqueues, threaded IRQs), and `EOI` lifecycle.
- [x] **Process & Thread Lifecycle State Machines (Ch 3 & Ch 4)**: 5-state process automaton (New, Ready, Running, Blocked, Zombie &rarr; Reaped), orphan reparenting to PID 1, `execve` descriptor preservation, and 5-state thread automaton (Spawned, Runnable, Running, Sleeping/Parked, Terminated &rarr; Reclaimed, `join` vs. `detach`, C++20 `std::jthread` vs. Rust `Send`/`Sync`).
- [x] **Verified Material SVGs**: `ch02_stack_frame.svg`, `ch02_interrupt_flow.svg`, `ch03_process_lifecycle.svg`, `ch04_thread_lifecycle.svg` (all visually audited via Headless Chrome).

### Phase 2: Virtual Memory & Hand-Calculated Translation (Chapter 7) — [COMPLETED & AUDITED]
- [x] **Canonical Address & Radix Geometry**: Derivation of 48-bit canonical sign extension (`#GP(0)` on non-canonical fault) and 2<sup>9</sup> = 512 8-byte PTEs per 4 KiB page table.
- [x] **Hand-Calculated 4-Level Page Walk**: Step-by-step bitwise and hexadecimal walkthrough of `0x0000_7FFF_ABCD_EF01` from `CR3 = 0x1000_0000` through PML4 (`255`), PDPT (`510`), PD (`350`), PT (`223`), and Offset (`0xF01`), plus full 64-bit PTE bit layout (`P`, `R/W`, `U/S`, `A`, `D`, `PS`, `G`, `PFN`, `NX`), TLB reach, Huge Pages (2 MiB / 1 GiB), `PCID`/`ASID`, and multi-core IPI TLB shootdowns.
- [x] **Verified Material SVG**: `ch07_canonical_va.svg`.

### Phase 3: Rust Code Safety Comments & Invariant Proofs — [COMPLETED & AUDITED]
- [x] Upgraded `// SAFETY:` and memory-ordering invariant proofs across Chapters 3, 4, 7, 8, 9, 10, 11, 15, and 19 (`fork.rs`, `race.rs`, `race_atomic.rs`, `pagesize.rs`, `bump.rs`, `free_list.rs`, `syscall_cost.rs`, `write_buffered.rs`, `signals.rs`, `pipe.rs`, `daemon.rs`, `kqueue_supervisor.rs`, `free_list_allocator.rs`, `spsc_ring.rs`, `mini_pipeline.rs`).

### Phase 4: Systems Interview & Systems Architecture Review (Chapter 19) — [COMPLETED & AUDITED]
- [x] Audited Bounded Blocking Queue, Free-List Allocator (16-byte alignment, splitting, coalescing), Lock-Free SPSC Ring Buffer (64-byte cache-line padding, acquire-release pairs), LRU Cache (`std::list::splice` & index arena), Reader-Writer Lock (writer-preference), Thread Pool, and Mini-Pipeline.

### Phase 5: Verification, Indexing, and PDF Publication — [COMPLETED & AUDITED]
- [x] Updated `src/toc.md` with all new subsections and subject index entries (0 broken anchors).
- [x] Executed `./code/run_all.sh`, `mdbook build`, and `./scripts/generate_pdf.sh`.

---

## Incremental Enrichment Roadmap: Phases 6–12 (Execute One Phase at a Time)

Each of the following phases addresses a major systems gap identified in our architectural analysis. **Execute one phase per iteration**, followed by the Prose & SVG Geometry Audit, Headless Chrome PNG inspection of any new diagrams, `./code/run_all.sh`, `mdbook build`, `./scripts/generate_pdf.sh`, and a clean Git commit.

### Phase 6: Production CPU Scheduling — CFS `vruntime`, EEVDF, and Priority Inversion (Chapter 5)
- [ ] **Objective**: Expand Chapter 5 from classic textbook policies (FCFS, SJF, RR) to modern production kernel schedulers and real-time concurrency hazards.
- [ ] **Proportional-Share & Linux Completely Fair Scheduler (CFS) / EEVDF**:
  - Derive **Virtual Runtime (`vruntime`)** weighted by nice value (`weight_0 / weight_i`), tracking physical execution time in nanoseconds.
  - Explain the **Red-Black Tree** runqueue (`rb_leftmost` O(1) cached minimum `vruntime` pointer), dynamic scheduling latency, and `min_granularity` preemption floor, plus the transition to **EEVDF** (Earliest Eligible Virtual Deadline First) for latency-critical tasks.
- [ ] **Priority Inversion and Priority Inheritance / Ceiling Protocols**:
  - Formalize the unbounded **Priority Inversion** hazard (the Mars Pathfinder failure mode: Low-priority thread `T_L` holds mutex `M`; High-priority thread `T_H` blocks on `M`; Medium-priority CPU-bound thread `T_M` preempts `T_L` indefinitely).
  - Derive **Priority Inheritance** (`PTHREAD_PRIO_INHERIT`, boosting `T_L` to `T_H`'s effective priority while holding `M`) and **Priority Ceiling** protocols.
- [ ] **Multi-Core Load Balancing & Cache Affinity**:
  - Per-CPU runqueues, work-stealing migration costs (L1/L2 cache warmth loss vs. core idle utilization), and NUMA scheduling domains.
- [ ] **Vector Diagram**: Implement `ch05_cfs_priority_inversion()` in `tools/draw_figures.py` showing the CFS Red-Black Tree `vruntime` timeline alongside a Priority Inversion / Priority Inheritance rescue timeline, and visually audit via Headless Chrome.
- [ ] **Poorly Written Appendix:** Rewrite Appendices A & B in formal, high-quality Computer Science English.

### Phase 7: Synchronization Beneath the Primitives — Futexes, Seqlocks, and Hardware Litmus Tests (Chapter 6)
- [ ] **Objective**: Reveal the kernel and microarchitectural mechanisms that implement user-space mutexes, reader-writer locks, and memory barriers in Chapter 6.
- [ ] **Fast Userspace Mutexes (`futex` on Linux / `__ulock` on Darwin)**:
  - Derive the two-path architecture of modern `std::mutex` / `pthread_mutex_t`:
    1. **Uncontended Fast Path (User Mode Ring 3):** A single atomic Compare-And-Swap (`CAS`, `0 -> 1`) acquires the lock in ~5 ns with **zero system calls**.
    2. **Contended Slow Path (Kernel Trap Ring 0):** Transitions lock state to `2` (contended) and invokes `futex(addr, FUTEX_WAIT, 2)`. The kernel atomically verifies `*addr == 2` before parking the TCB in the futex hash bucket wait queue, preventing lost wakeups between user-space check and kernel sleep.
- [ ] **Sequence Locks (`Seqlock`) and Read-Copy-Update (RCU) Concepts**:
  - Explain how a **Seqlock** eliminates reader-writer contention for read-mostly data (e.g., kernel system time `vdso`): writers increment a sequence counter to an odd number before mutation and to an even number after (`memory_order_release`); readers check that the sequence counter is even and unchanged before and after reading (`memory_order_acquire`), retrying without ever blocking writers or dirtying the cache line.
- [ ] **Hardware Memory Reordering Litmus Tests (Store Buffers & Invalidation Queues)**:
  - Provide the formal **Store-Buffering (SB)** and **Message-Passing (MP)** litmus tests explaining why x86-64 Total Store Order (TSO) permits `Store-Load` reordering (`r1 == 0 && r2 == 0` via per-core FIFO Store Buffers) while ARM64 weak ordering permits `Store-Store` and `Load-Load` reordering without explicit `dmb ish` / `ldar` / `stlr` barriers.
- [ ] **Vector Diagram**: Implement `ch06_futex_litmus()` in `tools/draw_figures.py` illustrating the Futex fast/slow path state machine and the Store-Buffer reordering datapath, and visually audit via Headless Chrome.

### Phase 8: Production Allocator Architecture, `mmap` Thresholds, and Lock-Free Reclamation (Chapter 8)
- [ ] **Objective**: Bridge the gap between Chapter 8's educational free-list allocator and production multi-threaded allocators (`jemalloc`, `tcmalloc`, `mimalloc`).
- [ ] **Boundary Tags for O(1) Bidirectional Coalescing**:
  - Derive Knuth's **Boundary Tag** layout (header + footer size/status replication), enabling immediate O(1) coalescing with both the physical predecessor and successor blocks without an O(N) linear list traversal.
- [ ] **Segregated Size Classes, Slab Caches, and Thread-Local Caches (`tcache`)**:
  - Show how size-class bucketing (`16, 32, 48, 64 ... 4096` bytes) bounds internal fragmentation while eliminating search scans, and how per-thread caches (`tcache`) satisfy small allocations in Ring 3 without acquiring any global heap mutex.
- [ ] **The `brk` vs. `mmap` Allocation Threshold (`M_MMAP_THRESHOLD`)**:
  - Explain why allocators sub-allocate small objects from persistent arenas (`sbrk` / `mmap` pools) to avoid per-object syscall and TLB-shootdown costs, while routing large allocations (&ge; 128 KiB) directly to standalone `mmap` regions so they can be returned immediately to the OS kernel via `munmap` upon `free()`.
- [ ] **Vector Diagram**: Implement `ch08_allocator_hierarchy()` in `tools/draw_figures.py` showing thread-local `tcache` bins, central size-class arenas, boundary-tag blocks, and direct `mmap` huge allocations, and visually audit via Headless Chrome.

### Phase 9: Modern System Call Acceleration (`vDSO`) and Zero-Copy Data Paths (Chapters 9 & 11)
- [ ] **Objective**: Enrich Chapter 9 (System Calls) and Chapter 11 (IPC) with kernel-bypass mechanisms and zero-copy I/O data paths.
- [ ] **Virtual Dynamic Shared Object (`vDSO`) and `vvar` Pages (Ch 9)**:
  - Explain how performance-critical queries like `clock_gettime(CLOCK_MONOTONIC)` and `gettimeofday()` avoid the Ring 3 &rarr; Ring 0 trap penalty entirely: the kernel maps a read-only shared page (`vvar`) containing hardware timer calibration multipliers and a Seqlock counter directly into every process's user address space, allowing user code (`vDSO`) to read the hardware cycle counter (`RDTSC` on x86-64; `CNTVCT_EL0` on ARM64) in ~15 ns.
- [ ] **Zero-Copy Transfer Paths: `sendfile`, `splice`, and DMA Scatter-Gather (Ch 9 / Ch 11)**:
  - Trace the 4 data copies and 4 mode switches of a traditional `read(file_fd, buf)` + `write(sock_fd, buf)` loop (Disk &rarr; Kernel Page Cache via DMA &rarr; User Buffer via CPU copy &rarr; Kernel Socket Buffer `sk_buff` via CPU copy &rarr; NIC TX ring via DMA).
  - Contrast with **`sendfile(out_fd, in_fd)`** and **`splice()`**, where data moves directly from the kernel Page Cache to the NIC DMA descriptor ring via pipe page-fragment references with **zero CPU byte copies** and a single system call—and explain why user-space TLS breaks zero-copy unless **Kernel TLS (`kTLS`)** or NIC TLS hardware offload is used.
- [ ] **File Descriptor Inheritance & `FD_CLOEXEC` Security Invariants (Ch 11)**:
  - Explain why failing to set `O_CLOEXEC` / `FD_CLOEXEC` leaks sensitive descriptors (sockets, lockfiles, pipes) across `fork() + execve()` boundaries into untrusted child binaries.
- [ ] **Vector Diagram**: Implement `ch09_zerocopy_vdso()` in `tools/draw_figures.py` comparing the traditional 4-copy `read`/`write` datapath against the zero-copy `sendfile` DMA scatter-gather datapath, and visually audit via Headless Chrome.

### Phase 10: VFS Page Cache Architecture, Write-Ahead Logging, and Crash Consistency (Chapter 12)
- [ ] **Objective**: Expand Chapter 12 to cover the Virtual File System (VFS) four-object model, the Unified Page Cache, `mmap` semantics (`MAP_SHARED` vs. `MAP_PRIVATE`), and crash-consistent storage engines.
- [ ] **The VFS Four-Object Hierarchy & Unified Page Cache (`address_space`)**:
  - Formalize the relationship between the per-process **File Descriptor Table** (`fd` array + `FD_CLOEXEC` bitmap), system-wide **Open File Table** (`struct file`: open flags, `f_pos` offset, reference count), **Dentry Cache (`dcache`)** (path component hash table), and **Inode Cache (`icache`)** (`struct inode` + `struct address_space` radix tree / XArray of cached 4 KiB pages).
- [ ] **File-Backed `mmap`: `MAP_SHARED` vs. `MAP_PRIVATE` & `msync` Hazards**:
  - Explain how `MAP_SHARED` maps the kernel Page Cache frames directly into user PTEs (writes dirty the page cache and flush asynchronously via writeback threads or synchronously via `msync(MS_SYNC)`), whereas `MAP_PRIVATE` maps the page cache read-only and triggers a Copy-on-Write fault into an anonymous private frame on the first store.
- [ ] **Crash Consistency, Write-Ahead Logging (WAL), and the Atomic Rename Pattern**:
  - Detail the ordering hazards of disk write caches when power fails mid-transaction.
  - Compare ext4/XFS journaling modes (**Writeback**, **Ordered**, and **Full Data Journaling**) and derive the canonical **Atomic File Replacement Pattern** (`open("file.tmp") -> write() -> fsync(tmp_fd) -> close() -> rename("file.tmp", "file") -> fsync(parent_dir_fd)`).
- [ ] **Vector Diagram**: Implement `ch12_vfs_pagecache()` in `tools/draw_figures.py` illustrating the VFS 4-level object indirection (`fd` &rarr; `struct file` &rarr; `dentry` &rarr; `inode` &rarr; `address_space` Page Cache) across forked and independent processes, and visually audit via Headless Chrome.

### Phase 11: Edge-Triggered Event Loops (`epoll`/`kqueue`) and Completion-Driven Asynchronous I/O (`io_uring`) (Chapter 13)
- [ ] **Objective**: Transform Chapter 13 into an authoritative guide on kernel event-multiplexing internals and modern completion-driven I/O rings.
- [ ] **Internal Kernel Architecture of `epoll` and `kqueue`**:
  - Contrast O(N) linear descriptor scanning in `select`/`poll` against `epoll`/`kqueue`'s persistent kernel state: a **Red-Black Tree** (or hash table) storing registered interest items (`epitem` / `knote`) paired with a **Doubly Linked Readiness List (`rdllist`)** populated directly by NIC/pipe interrupt wakeup callbacks in O(1) time, yielding O(K<sub>ready</sub>) harvest complexity.
- [ ] **Level-Triggered (LT) vs. Edge-Triggered (`EPOLLET` / `EV_CLEAR`) & Multi-Core Scaling**:
  - Derive the exact state transition difference: LT notifies continuously while buffer data remains unread; ET notifies **only on the state transition** from unready to ready.
  - Explain why an ET handler **must** loop over non-blocking `read()`/`accept()` until receiving `EAGAIN` / `EWOULDBLOCK` (otherwise remaining bytes stall the connection forever), and how **`EPOLLONESHOT`** and **`EPOLLEXCLUSIVE`** prevent multi-threaded race conditions and thundering-herd wakeups.
- [ ] **Completion-Driven Asynchronous I/O: `io_uring` Submission and Completion Rings**:
  - Contrast readiness-based I/O (`epoll` / `kqueue`) against completion-based I/O (`io_uring`).
  - Detail the shared-memory **Submission Queue (SQ)** and **Completion Queue (CQ)** single-producer single-consumer ring buffers mapped between user space and the kernel (`mmap`), enabling zero-syscall batched I/O submission and reaping (`IORING_SETUP_SQPOLL`).
- [ ] **Vector Diagram**: Implement `ch13_epoll_iouring()` in `tools/draw_figures.py` contrasting the `epoll` Red-Black Tree + Readiness List architecture against `io_uring` shared-memory SQ/CQ ring buffers, and visually audit via Headless Chrome.

### Phase 12: Production TCP State Automaton, Teardown Hazards, and Hardware Virtualization EPT Walks (Chapters 14 & 16)
- [ ] **Objective**: Enrich Chapter 14 (Networking) and Chapter 16 (Virtualization) with the complete TCP state machine, socket options, and two-dimensional hardware virtualization page tables.
- [ ] **The 11-State TCP Finite State Automaton & Teardown Pathology (Ch 14)**:
  - Formalize the active/passive open (`SYN_SENT`, `SYN_RCVD`, `ESTABLISHED`) and 4-way FIN teardown states:
    - Active Closer: `FIN_WAIT_1` &rarr; `FIN_WAIT_2` &rarr; **`TIME_WAIT`** (or `CLOSING` on simultaneous close).
    - Passive Closer: **`CLOSE_WAIT`** &rarr; `LAST_ACK` &rarr; `CLOSED`.
  - Derive the two mandatory roles of the **2 &times; MSL `TIME_WAIT` state** (preventing delayed duplicate segments from corrupting a reincarnated 4-tuple connection, and ensuring the remote peer receives the final `ACK`), and explain how a **`CLOSE_WAIT` accumulation leak** diagnoses a bug where the application read `0` (EOF) from the socket but failed to call `close(fd)`.
- [ ] **Production Socket Options & Transport Tuning (Ch 14)**:
  - **`TCP_NODELAY` vs. Nagle's Algorithm & Delayed ACKs** (why Nagle + Delayed ACK causes 40–200 ms tail-latency spikes in RPC protocols), **`SO_REUSEADDR` vs. `SO_REUSEPORT`** (kernel 4-tuple load distribution across multi-threaded accept queues), and **Bandwidth-Delay Product (BDP)** socket buffer sizing (`SO_SNDBUF` / `SO_RCVBUF`).
- [ ] **Hardware Virtualization (`VMX` / `SVM`) and Two-Dimensional EPT/NPT Page Walks (Ch 16)**:
  - Detail hardware virtualization extensions: **VMX Root** vs. **VMX Non-Root** operation, the **Virtual Machine Control Structure (`VMCS`)**, **VM Exits** on privileged traps (`CPUID`, `HLT`, MMIO), and `virtio` paravirtualized I/O rings (`vring`).
  - Derive the mathematics of **Two-Dimensional Address Translation** via **Extended Page Tables (`EPT` on Intel / `NPT` on AMD / Stage-2 MMU on ARM64)**: translating a Guest Virtual Address (`GVA`) to a Guest Physical Address (`GPA`) and then to a Host Physical Address (`HPA`). Show why a 4-level guest table over a 4-level host EPT turns a single TLB miss into a **2D page walk requiring up to (4 + 1) &times; 4 + 4 = 24 memory accesses**, making 2 MiB / 1 GiB Huge Pages mandatory for hypervisor performance.
- [ ] **Vector Diagrams**: Implement `ch14_tcp_state_machine()` and `ch16_ept_2d_walk()` in `tools/draw_figures.py`, and visually audit both via Headless Chrome.
