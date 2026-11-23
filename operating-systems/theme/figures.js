// 1. Shows the dark variant of each figure in the dark themes, and the light
//    variant in the light themes and in print.
// 2. Transforms consecutive C++20 and Rust 2024 listing blocks into independent
//    Material Design tabbed code cards (with optional per-card desktop split view).
(function () {
  var DARK_THEMES = ['coal', 'navy', 'ayu'];

  function isDark() {
    var classes = document.documentElement.classList;
    return DARK_THEMES.some(function (name) { return classes.contains(name); });
  }

  function applyFigures(forceLight) {
    var dark = !forceLight && isDark();
    document.querySelectorAll('img[src*="figures/"]').forEach(function (img) {
      var current = img.getAttribute('src');
      var light = current.replace('figures/dark/', 'figures/');
      var wanted = dark ? light.replace('figures/', 'figures/dark/') : light;
      if (wanted !== current) img.setAttribute('src', wanted);
    });
  }

  function isListingHeader(el) {
    if (!el || el.tagName !== 'P') return false;
    var strong = el.querySelector('strong:first-child');
    if (!strong) return false;
    return /^Listing\s+\d+/i.test(strong.textContent.trim());
  }

  function isOutputHeader(el) {
    if (!el || el.tagName !== 'P') return false;
    var strong = el.querySelector('strong:first-child');
    if (!strong) return false;
    return /^Output\s+\d+/i.test(strong.textContent.trim());
  }

  function getPreLang(el) {
    if (!el || el.tagName !== 'PRE') return null;
    var code = el.querySelector('code');
    if (!code) return null;
    if (code.classList.contains('language-cpp') || code.classList.contains('cpp')) return 'cpp';
    if (code.classList.contains('language-rust') || code.classList.contains('rust')) return 'rust';
    return 'other';
  }

  function collectUnit(children, startIdx) {
    if (!isListingHeader(children[startIdx])) return null;
    var nextEl = children[startIdx + 1];
    var lang = getPreLang(nextEl);
    if (lang !== 'cpp' && lang !== 'rust') return null;

    var nodes = [children[startIdx], nextEl];
    var idx = startIdx + 2;

    while (idx < children.length) {
      if (isOutputHeader(children[idx]) && children[idx + 1] && children[idx + 1].tagName === 'PRE') {
        nodes.push(children[idx], children[idx + 1]);
        idx += 2;
      } else if (isListingHeader(children[idx]) && getPreLang(children[idx + 1]) === lang) {
        nodes.push(children[idx], children[idx + 1]);
        idx += 2;
      } else {
        break;
      }
    }

    return { lang: lang, nodes: nodes, nextIndex: idx };
  }

  function extractShortTitle(nodes, fallback) {
    var firstStrong = nodes[0] && nodes[0].querySelector('strong');
    if (!firstStrong) return fallback;
    var raw = firstStrong.textContent.trim();
    var m = raw.match(/^(Listing\s+[\d-]+[a-z]?)/i);
    return m ? m[1] : fallback;
  }

  // Updates ONLY the clicked card: never mutates other cards on the page.
  function activateCardMode(card, mode) {
    card.classList.toggle('is-split', mode === 'split');

    card.querySelectorAll('.md-code-tab').forEach(function (btn) {
      var active = btn.getAttribute('data-mode') === mode;
      btn.classList.toggle('active', active);
      btn.setAttribute('aria-selected', active ? 'true' : 'false');
    });

    card.querySelectorAll('.md-code-panel').forEach(function (panel) {
      var lang = panel.getAttribute('data-lang');
      var visible = mode === 'split' || lang === mode;
      panel.classList.toggle('active', visible);
    });
  }

  function initMaterialCodeTabs() {
    var main = document.querySelector('.content main');
    if (!main) return;

    var children = Array.prototype.slice.call(main.children);
    var i = 0;

    while (i < children.length) {
      var unit1 = collectUnit(children, i);
      if (unit1 && unit1.lang === 'cpp') {
        var unit2 = collectUnit(children, unit1.nextIndex);
        if (unit2 && unit2.lang === 'rust') {
          var card = document.createElement('div');
          card.className = 'md-code-tabs';

          var bar = document.createElement('div');
          bar.className = 'md-code-tabs-bar';
          bar.setAttribute('role', 'tablist');

          var cppListingId = extractShortTitle(unit1.nodes, 'C++20');
          var rustListingId = extractShortTitle(unit2.nodes, 'Rust 2024');

          var btnCpp = document.createElement('button');
          btnCpp.type = 'button';
          btnCpp.className = 'md-code-tab active';
          btnCpp.setAttribute('data-mode', 'cpp');
          btnCpp.setAttribute('role', 'tab');
          btnCpp.setAttribute('aria-selected', 'true');
          btnCpp.innerHTML =
            '<span class="md-lang-chip cpp">C++20</span>' +
            '<span class="md-tab-title">' + cppListingId + '</span>';

          var btnRust = document.createElement('button');
          btnRust.type = 'button';
          btnRust.className = 'md-code-tab';
          btnRust.setAttribute('data-mode', 'rust');
          btnRust.setAttribute('role', 'tab');
          btnRust.setAttribute('aria-selected', 'false');
          btnRust.innerHTML =
            '<span class="md-lang-chip rust">Rust 2024</span>' +
            '<span class="md-tab-title">' + rustListingId + '</span>';

          var btnSplit = document.createElement('button');
          btnSplit.type = 'button';
          btnSplit.className = 'md-code-tab md-code-tab-split';
          btnSplit.setAttribute('data-mode', 'split');
          btnSplit.setAttribute('role', 'tab');
          btnSplit.setAttribute('aria-selected', 'false');
          btnSplit.innerHTML =
            '<span class="md-lang-chip split">Split</span>' +
            '<span class="md-tab-title">Side by Side</span>';

          (function (thisCard) {
            btnCpp.addEventListener('click', function () { activateCardMode(thisCard, 'cpp'); });
            btnRust.addEventListener('click', function () { activateCardMode(thisCard, 'rust'); });
            btnSplit.addEventListener('click', function () { activateCardMode(thisCard, 'split'); });
          })(card);

          bar.appendChild(btnCpp);
          bar.appendChild(btnRust);
          bar.appendChild(btnSplit);
          card.appendChild(bar);

          var panelsWrap = document.createElement('div');
          panelsWrap.className = 'md-code-panels';

          var panelCpp = document.createElement('div');
          panelCpp.className = 'md-code-panel active';
          panelCpp.setAttribute('data-lang', 'cpp');
          panelCpp.setAttribute('role', 'tabpanel');

          var panelRust = document.createElement('div');
          panelRust.className = 'md-code-panel';
          panelRust.setAttribute('data-lang', 'rust');
          panelRust.setAttribute('role', 'tabpanel');

          main.insertBefore(card, unit1.nodes[0]);
          unit1.nodes.forEach(function (n) { panelCpp.appendChild(n); });
          unit2.nodes.forEach(function (n) { panelRust.appendChild(n); });

          panelsWrap.appendChild(panelCpp);
          panelsWrap.appendChild(panelRust);
          card.appendChild(panelsWrap);

          i = unit2.nextIndex;
          continue;
        }
      }
      i += 1;
    }
  }

  // 3. Auto-link every systems abbreviation in prose & inline code to glossary.html#term-...
  //    with an instant Material hover tooltip showing the full expansion and definition.
  var GLOSSARY = {
    'ABI': ['term-abi', 'Application Binary Interface: binary contract for registers, calling conventions, and syscalls.'],
    'ACK': ['term-ack', 'Acknowledgment: TCP control flag confirming cumulative byte receipt.'],
    'AMD-V': ['term-amd-v', 'AMD Virtualization: hardware hypervisor extensions on AMD x86-64 CPUs.'],
    'APFS': ['term-apfs', 'Apple File System: copy-on-write, extent-based filesystem on macOS.'],
    'API': ['term-api', 'Application Programming Interface: source-level library/runtime contract.'],
    'APIC': ['term-apic', 'Advanced Programmable Interrupt Controller: x86-64 interrupt & timer controller.'],
    'ASIC': ['term-asic', 'Application-Specific Integrated Circuit: custom silicon accelerator.'],
    'ASID': ['term-asid', 'Address Space Identifier: ARM64 TLB tag avoiding context-switch flushes.'],
    'ASLR': ['term-aslr', 'Address Space Layout Randomization: randomizes virtual segment base addresses.'],
    'AVL': ['term-avl', 'Available for OS Use: PTE bits [11:9] reserved for kernel software metadata.'],
    'AVX': ['term-avx', 'Advanced Vector Extensions: 256/512-bit x86-64 SIMD instructions.'],
    'BSD': ['term-bsd', 'Berkeley Software Distribution: Unix lineage behind sockets, kqueue, and macOS.'],
    'BSS': ['term-bss', 'Block Started by Symbol: demand-zeroed uninitialized global data segment.'],
    'CAS': ['term-cas', 'Compare-And-Swap: atomic read-modify-write synchronization primitive.'],
    'CFS': ['term-cfs', 'Completely Fair Scheduler: Linux proportional-share vruntime scheduler.'],
    'CISC': ['term-cisc', 'Complex Instruction Set Computer: architecture supporting multi-step instructions (x86-64).'],
    'COW': ['term-cow', 'Copy-on-Write: shares read-only frames until a store faults and duplicates the page.'],
    'CPL': ['term-cpl', 'Current Privilege Level: active x86-64 privilege ring (Ring 0 kernel, Ring 3 user).'],
    'CR2': ['term-cr2', 'Control Register 2: x86-64 register latching the faulting VA on #PF.'],
    'CR3': ['term-cr3', 'Control Register 3: x86-64 register holding the physical base of L4 PML4.'],
    'DDR4': ['term-ddr', 'Double Data Rate 4: host system DRAM memory standard.'],
    'DDR5': ['term-ddr', 'Double Data Rate 5: host system DRAM memory standard.'],
    'DMA': ['term-dma', 'Direct Memory Access: device-to-DRAM transfers bypassing CPU cores.'],
    'DNS': ['term-dns', 'Domain Name System: translates hostnames to IPv4/IPv6 addresses.'],
    'DRAM': ['term-dram', 'Dynamic Random-Access Memory: off-chip main physical memory (~60–100 ns).'],
    'dTLB': ['term-dtlb', 'Data Translation Lookaside Buffer: L1 per-core data translation cache (~64 entries).'],
    'eBPF': ['term-ebpf', 'Extended Berkeley Packet Filter: verified in-kernel bytecode VM for tracing & filtering.'],
    'EEVDF': ['term-eevdf', 'Earliest Eligible Virtual Deadline First: Linux latency-aware proportional scheduler.'],
    'EL0': ['term-el0', 'Exception Level 0: ARM64 unprivileged user mode.'],
    'EL1': ['term-el0', 'Exception Level 1: ARM64 operating system kernel mode.'],
    'EL2': ['term-el0', 'Exception Level 2: ARM64 hardware hypervisor mode.'],
    'ELF': ['term-elf', 'Executable and Linkable Format: standard Linux binary executable format.'],
    'EOF': ['term-eof', 'End-of-File: read() returning 0 when no bytes or writers remain.'],
    'EOI': ['term-eoi', 'End of Interrupt: signal acknowledging interrupt completion to APIC/GIC.'],
    'EPT': ['term-ept', 'Extended Page Tables: Intel two-stage GPA-to-HPA virtualization page tables.'],
    'FAR_EL1': ['term-far-el1', 'Fault Address Register (EL1): ARM64 register holding faulting VA on page fault.'],
    'FIFO': ['term-fifo', 'First-In, First-Out: strict arrival-order queueing discipline.'],
    'FIN': ['term-fin', 'Finish: TCP control flag initiating graceful half-close teardown.'],
    'GDDR': ['term-gddr', 'Graphics Double Data Rate: high-bandwidth discrete GPU memory.'],
    'GIC': ['term-gic', 'Generic Interrupt Controller: ARM64 interrupt routing controller (GICv3).'],
    'GID': ['term-gid', 'Group Identifier: numeric Unix group ownership identifier.'],
    '#GP': ['term-gp', 'General Protection Fault: x86-64 exception raised on non-canonical addresses or privilege violations.'],
    'GPA': ['term-gpa', 'Guest Physical Address: physical address perceived by a VM guest kernel.'],
    'GPU': ['term-gpu', 'Graphics Processing Unit: massively parallel throughput accelerator.'],
    'GVA': ['term-gva', 'Guest Virtual Address: virtual address inside a virtual machine.'],
    'HBM': ['term-hbm', 'High Bandwidth Memory: 3D-stacked ultra-wide accelerator memory.'],
    'HPA': ['term-hpa', 'Host Physical Address: true physical DRAM address on the bare-metal host.'],
    'HPC': ['term-hpc', 'High-Performance Computing: large-scale numerical/scientific workloads.'],
    'HTTP': ['term-http', 'Hypertext Transfer Protocol: web application request/response protocol.'],
    'IDT': ['term-idt', 'Interrupt Descriptor Table: 256-entry x86-64 exception/interrupt vector table.'],
    'IDTR': ['term-idt', 'Interrupt Descriptor Table Register: points hardware to the IDT base.'],
    'I/O': ['term-io', 'Input/Output: data transfer between memory and storage, network, or terminal devices.'],
    'IOMMU': ['term-iommu', 'Input-Output Memory Management Unit: translates & isolates device DMA addresses.'],
    'IOPS': ['term-iops', 'Input/Output Operations Per Second: storage block throughput metric.'],
    'IPv4': ['term-ip', 'Internet Protocol Version 4: 32-bit network-layer addressing.'],
    'IPv6': ['term-ip', 'Internet Protocol Version 6: 128-bit network-layer addressing.'],
    'IPC': ['term-ipc', 'Inter-Process Communication (Ch. 11) / Instructions Per Cycle (Ch. 18).'],
    'IPI': ['term-ipi', 'Inter-Processor Interrupt: cross-core hardware interrupt for wakeups & TLB shootdowns.'],
    'IRQ': ['term-irq', 'Interrupt Request: asynchronous hardware interrupt signal from a device.'],
    'ISA': ['term-isa', 'Instruction Set Architecture: hardware/software contract (x86-64, ARM64).'],
    'JIT': ['term-jit', 'Just-In-Time Compilation: runtime generation of executable machine code.'],
    'KPTI': ['term-kpti', 'Kernel Page-Table Isolation: separates user/kernel page tables to mitigate Meltdown.'],
    'KVM': ['term-kvm', 'Kernel-based Virtual Machine: Linux hardware-assisted hypervisor.'],
    'LLC': ['term-llc', 'Last-Level Cache: largest shared on-chip cache (L3) before DRAM.'],
    'LLVM': ['term-llvm', 'Low-Level Virtual Machine: modular compiler infrastructure powering Clang and rustc.'],
    'LRU': ['term-lru', 'Least Recently Used: eviction policy discarding the oldest unreferenced item.'],
    'MESI': ['term-mesi', 'Modified-Exclusive-Shared-Invalid: 4-state hardware cache-coherency protocol.'],
    'MOESI': ['term-mesi', 'Modified-Owned-Exclusive-Shared-Invalid: 5-state cache-coherency protocol.'],
    'MMIO': ['term-mmio', 'Memory-Mapped Input/Output: device control registers mapped into physical address space.'],
    'MMU': ['term-mmu', 'Memory Management Unit: hardware circuit translating VA to PA and checking permissions.'],
    'MSI-X': ['term-msi-x', 'Message Signaled Interrupts Extended: PCIe DMA-based per-core interrupt delivery.'],
    'MTU': ['term-mtu', 'Maximum Transmission Unit: largest unfragmented packet payload on a link.'],
    'NAPI': ['term-napi', 'New API: Linux network polling mode preventing interrupt livelock under high packet rates.'],
    'NEON': ['term-neon', 'ARM Advanced SIMD: 128-bit vector instructions on ARM64.'],
    'NIC': ['term-nic', 'Network Interface Card: Ethernet/network hardware controller.'],
    'NMI': ['term-nmi', 'Non-Maskable Interrupt: unignorable hardware interrupt used by PMU profilers & watchdogs.'],
    'NPT': ['term-npt', 'Nested Page Tables: AMD hardware two-stage virtualization page tables.'],
    'NPU': ['term-npu', 'Neural Processing Unit: dedicated hardware accelerator for neural network inference.'],
    'NTFS': ['term-ntfs', 'New Technology File System: Windows journaling filesystem.'],
    'NUMA': ['term-numa', 'Non-Uniform Memory Access: multi-socket topology with fast local and slower remote DRAM.'],
    'NX': ['term-nx', 'No-Execute: PTE bit 63 blocking instruction fetches from data pages (W^X).'],
    'OCI': ['term-oci', 'Open Container Initiative: standard container image and runtime specification.'],
    'OOM': ['term-oom', 'Out-of-Memory: exhaustion of physical RAM or cgroup memory.max limit.'],
    'PA': ['term-pa', 'Physical Address: hardware memory-bus address targeting a byte in physical DRAM.'],
    'PAT': ['term-pat', 'Page Attribute Table: leaf PTE bit 7 selecting caching attributes.'],
    'PCB': ['term-pcb', 'Process Control Block: per-process kernel struct (task_struct) tracking state and resources.'],
    'PCD': ['term-pcd', 'Page-Level Cache Disable: PTE bit 4 disabling caching for MMIO regions.'],
    'PCID': ['term-pcid', 'Process-Context Identifier: 12-bit x86-64 TLB tag avoiding flushes across context switches.'],
    'PCIe': ['term-pcie', 'Peripheral Component Interconnect Express: high-speed serial I/O bus.'],
    'PD': ['term-pd', 'Page Directory (Level 2): radix table covering 2 MiB per entry.'],
    'PDPT': ['term-pdpt', 'Page Directory Pointer Table (Level 3): radix table covering 1 GiB per entry.'],
    '#PF': ['term-pf', 'Page Fault Exception: MMU trap on Present = 0 or permission violation.'],
    'PFN': ['term-pfn', 'Physical Frame Number: upper bits identifying a 4 KiB physical DRAM frame.'],
    'PGD': ['term-pgd', 'Page Global Directory: Linux name for Level 4 (PML4) root page table.'],
    'PGID': ['term-pgid', 'Process Group Identifier: groups processes for job-control signaling.'],
    'PID': ['term-pid', 'Process Identifier: unique positive integer identifying a process.'],
    'PKU': ['term-pku', 'Memory Protection Keys: user-switchable hardware page protection domains.'],
    'PMD': ['term-pgd', 'Page Middle Directory: Linux name for Level 2 (PD) page table.'],
    'PML4': ['term-pml4', 'Page Map Level 4: x86-64 root page table (bits [47:39], 512 GiB/entry).'],
    'PMU': ['term-pmu', 'Performance Monitoring Unit (Ch. 18) / Power Management Unit (Ch. 15).'],
    'POSIX': ['term-posix', 'Portable Operating System Interface: IEEE Unix syscall and threading standard.'],
    'PS': ['term-ps', 'Page Size Bit: PD/PDPT bit 7 mapping 2 MiB or 1 GiB huge pages directly.'],
    'PT': ['term-pt', 'Page Table (Level 1 Leaf): maps individual 4 KiB virtual pages to frames.'],
    'PTE': ['term-pte', 'Page Table Entry: 64-bit entry holding PFN and permission/activity flags.'],
    'PUD': ['term-pgd', 'Page Upper Directory: Linux name for Level 3 (PDPT) page table.'],
    'PWT': ['term-pcd', 'Page-Level Write-Through: PTE bit 3 selecting write-through caching.'],
    'QEMU': ['term-qemu', 'Quick Emulator: user-space machine emulator & device model paired with KVM.'],
    'QUIC': ['term-quic', 'Quick UDP Internet Connections: encrypted multiplexed transport over UDP (HTTP/3).'],
    'RAII': ['term-raii', 'Resource Acquisition Is Initialization: ties resource cleanup deterministically to scope exit.'],
    'RCU': ['term-rcu', 'Read-Copy-Update: lock-free kernel read synchronization with deferred reclamation.'],
    'RFO': ['term-rfo', 'Read-For-Ownership: cache-coherency invalidation broadcast before writing a Shared line.'],
    'RISC': ['term-risc', 'Reduced Instruction Set Computer: load/store architecture (ARM64).'],
    'RPC': ['term-rpc', 'Remote Procedure Call: cross-process or cross-network request/response invocation.'],
    'SID': ['term-sid', 'Session Identifier: groups process groups attached to one controlling terminal.'],
    'SIGABRT': ['term-sigterm', 'Abort Signal: terminates process with core dump on fatal assertion or watchdog timeout.'],
    'SIGBUS': ['term-sigsegv', 'Bus Error: fatal signal on invalid memory access, guard page, or alignment fault (macOS).'],
    'SIGCHLD': ['term-sigchld', 'Child Status Changed: notifies parent when a child terminates or stops.'],
    'SIGHUP': ['term-sigterm', 'Signal Hangup: terminal disconnect; conventionally triggers daemon config reload.'],
    'SIGINT': ['term-sigterm', 'Signal Interrupt: interactive Ctrl-C interrupt from controlling terminal.'],
    'SIGKILL': ['term-sigkill', 'Kill Signal (9): uncatchable, unblockable immediate kernel termination.'],
    'SIGPIPE': ['term-sigterm', 'Broken Pipe: delivered when writing to a pipe or socket with zero open readers.'],
    'SIGSEGV': ['term-sigsegv', 'Segmentation Violation: fatal signal on unmapped memory or PTE permission violation.'],
    'SIGSTOP': ['term-sigkill', 'Stop Signal (19): uncatchable, unblockable process suspension.'],
    'SIGTERM': ['term-sigterm', 'Signal Terminate: catchable request for graceful shutdown.'],
    'SIMD': ['term-simd', 'Single Instruction, Multiple Data: parallel vector instructions (SSE, AVX, NEON).'],
    'SLC': ['term-slc', 'System Level Cache: shared on-die cache on Apple Silicon SoCs.'],
    'SLO': ['term-slo', 'Service-Level Objective: quantitative reliability or tail-latency target.'],
    'SLUB': ['term-slub', 'Unqueued Slab Allocator: primary Linux kernel fixed-size object allocator.'],
    'SMMU': ['term-smmu', 'System Memory Management Unit: ARM64 IOMMU for DMA translation and isolation.'],
    'SMP': ['term-smp', 'Symmetric Multiprocessing: identical CPU cores sharing one address space and kernel.'],
    'SMT': ['term-smt', 'Simultaneous Multithreading: hardware threads sharing one physical core.'],
    'SoC': ['term-soc', 'System-on-Chip: integrated silicon package combining CPU, GPU, NPU, and I/O.'],
    'SRAM': ['term-sram', 'Static Random-Access Memory: fast on-chip memory used for L1/L2/L3 caches.'],
    'SR-IOV': ['term-sr-iov', 'Single Root I/O Virtualization: partitions one physical PCIe NIC into VM virtual functions.'],
    'SSD': ['term-ssd', 'Solid-State Drive: non-volatile flash block storage (~50–200 µs latency).'],
    'SSE': ['term-sse', 'Streaming SIMD Extensions: 128-bit x86-64 vector instruction set.'],
    'STLB': ['term-stlb', 'Shared Translation Lookaside Buffer: L2 unified per-core TLB (1,024–2,048 entries).'],
    'SYN': ['term-syn', 'Synchronize: TCP control flag initiating the three-way handshake.'],
    'TCB': ['term-tcb', 'Thread Control Block: per-thread kernel execution and register-state structure.'],
    'TCP': ['term-tcp', 'Transmission Control Protocol: reliable, ordered, full-duplex byte-stream transport.'],
    'TLB': ['term-tlb', 'Translation Lookaside Buffer: core-private hardware cache of VPN-to-PFN translations.'],
    'TLS': ['term-tls', 'Transport Layer Security (Ch. 14) / Thread-Local Storage (Ch. 3, 4).'],
    'TTBR0_EL1': ['term-ttbr0', 'Translation Table Base Register 0: ARM64 user-space root page-table register.'],
    'TTBR1_EL1': ['term-ttbr0', 'Translation Table Base Register 1: ARM64 kernel-space root page-table register.'],
    'TTY': ['term-tty', 'Teletype: interactive terminal device governing foreground job-control signals.'],
    'UDP': ['term-udp', 'User Datagram Protocol: connectionless, boundary-preserving unreliable datagrams.'],
    'UID': ['term-uid', 'User Identifier: numeric Unix owner/privilege identity (0 = root).'],
    'UMA': ['term-uma', 'Unified Memory Architecture: shared physical memory pool across CPU, GPU, and NPU.'],
    'UPI': ['term-upi', 'Ultra Path Interconnect: Intel cache-coherent inter-socket NUMA link.'],
    'VA': ['term-va', 'Virtual Address: program pointer translated to a Physical Address by the MMU.'],
    'vCPU': ['term-vcpu', 'Virtual Central Processing Unit: virtual processor core inside a VM.'],
    'vDSO': ['term-vdso', 'Virtual Dynamic Shared Object: user-mapped kernel page avoiding Ring 0 clock syscalls.'],
    'VFIO': ['term-vfio', 'Virtual Function I/O: IOMMU-isolated direct PCIe device passthrough to VMs.'],
    'VM': ['term-vm', 'Virtual Machine: hardware-isolated guest OS running atop a hypervisor.'],
    'VMA': ['term-vma', 'Virtual Memory Area: kernel struct tracking a valid virtual memory interval & permissions.'],
    'VMCS': ['term-vmcs', 'Virtual Machine Control Structure: Intel VT-x state block for a vCPU.'],
    'VMX': ['term-vmx', 'Virtual Machine Extensions: Intel VT-x Root / Non-Root execution modes.'],
    'VPID': ['term-vpid', 'Virtual Processor Identifier: Intel TLB tag avoiding flushes on VM-Exit/VM-Entry.'],
    'VPN': ['term-vpn', 'Virtual Page Number: upper VA bits identifying a 4 KiB virtual page.'],
    'VRAM': ['term-vram', 'Video Random-Access Memory: dedicated memory on discrete GPU cards.'],
    'VT-x': ['term-vt-x', 'Intel Virtualization Technology: Intel x86-64 hardware virtualization extensions.'],
    'W^X': ['term-wx', 'Write XOR Execute: invariant prohibiting pages from being simultaneously writable and executable.'],
    'XFS': ['term-xfs', 'Extended File System: high-performance 64-bit journaling Linux filesystem.'],
    'XNU': ['term-xnu', 'X is Not Unix: hybrid Mach + BSD kernel powering macOS and Darwin.']
  };

  function initGlossaryLinks() {
    var path = window.location.pathname || '';
    if (/\/(glossary|toc|cover)\.html$/.test(path)) return;
    var main = document.querySelector('.content main');
    if (!main) return;

    var keys = Object.keys(GLOSSARY).sort(function (a, b) { return b.length - a.length; });
    var escaped = keys.map(function (k) { return k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); });
    var re = new RegExp('(^|[^A-Za-z0-9_])(' + escaped.join('|') + ')(?=$|[^A-Za-z0-9_])', 'g');

    var SKIP_TAGS = { A: 1, PRE: 1, SCRIPT: 1, STYLE: 1, H1: 1, H2: 1, H3: 1, H4: 1, H5: 1, H6: 1, BUTTON: 1 };

    function makeLink(term) {
      var info = GLOSSARY[term];
      var a = document.createElement('a');
      a.className = 'md-abbr-link';
      a.href = 'glossary.html#' + info[0];
      a.title = info[1];
      a.setAttribute('data-tooltip', info[1]);
      a.textContent = term;
      return a;
    }

    // Link inline <code> containing an exact glossary term (e.g. `MMU`, `TLB`, `CR3`)
    main.querySelectorAll('code').forEach(function (codeEl) {
      if (codeEl.closest('pre, a, h1, h2, h3, h4, h5, h6, button')) return;
      var txt = codeEl.textContent.trim();
      if (Object.prototype.hasOwnProperty.call(GLOSSARY, txt)) {
        var link = makeLink(txt);
        link.classList.add('md-abbr-code');
        codeEl.textContent = '';
        codeEl.appendChild(link);
      }
    });

    // Link plain-text occurrences in paragraphs, list items, table cells, and callouts
    var walker = document.createTreeWalker(main, NodeFilter.SHOW_TEXT, null, false);
    var textNodes = [];
    var node;
    while ((node = walker.nextNode())) {
      if (!node.nodeValue || !node.nodeValue.trim()) continue;
      var parent = node.parentElement;
      if (!parent) continue;
      var skip = false;
      var cur = parent;
      while (cur && cur !== main) {
        if (SKIP_TAGS[cur.tagName] || cur.tagName === 'CODE' || cur.classList.contains('md-code-tabs-bar')) {
          skip = true;
          break;
        }
        cur = cur.parentElement;
      }
      if (!skip) textNodes.push(node);
    }

    textNodes.forEach(function (tNode) {
      var str = tNode.nodeValue;
      re.lastIndex = 0;
      if (!re.test(str)) return;
      re.lastIndex = 0;
      var frag = document.createDocumentFragment();
      var lastIdx = 0;
      var m;
      while ((m = re.exec(str)) !== null) {
        var prefix = m[1];
        var term = m[2];
        var termStart = m.index + prefix.length;
        if (termStart > lastIdx) {
          frag.appendChild(document.createTextNode(str.slice(lastIdx, termStart)));
        }
        frag.appendChild(makeLink(term));
        lastIdx = termStart + term.length;
      }
      if (lastIdx < str.length) {
        frag.appendChild(document.createTextNode(str.slice(lastIdx)));
      }
      tNode.parentNode.replaceChild(frag, tNode);
    });
  }

  function initAll() {
    initMaterialCodeTabs();
    initGlossaryLinks();
  }

  applyFigures(false);
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAll);
  } else {
    initAll();
  }

  new MutationObserver(function () { applyFigures(false); })
    .observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
  window.addEventListener('beforeprint', function () { applyFigures(true); });
  window.addEventListener('afterprint', function () { applyFigures(false); });
})();
