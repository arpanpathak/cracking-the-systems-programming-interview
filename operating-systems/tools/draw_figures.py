"""Draws every figure of the book into src/figures (light) and
src/figures/dark (dark).

Run:  python3 tools/draw_figures.py            all figures
      python3 tools/draw_figures.py ch07       figures whose name starts with ch07
"""
import sys

from figkit import Fig

FIGURES = []


def figure(function):
    FIGURES.append(function)
    return function


# ---------------------------------------------------------------- Preface

@figure
def preface_roadmap():
    fig = Fig("preface_roadmap", "Figure P-2. Curriculum Architecture: Four Parts, One Unified Systems Journey", 476)

    parts = [
        (28, "blue", "Part I: Core", "Silicon to Syscalls", "layers", [
            ("Ch 01: Ontological Role", "small"),
            ("Ch 02: Hardware Arch", "small"),
            ("Ch 03: Process Model", "small"),
            ("Ch 07: Virtual Memory", "small"),
            ("Ch 08: Memory Alloc", "small"),
            ("Ch 09: Syscall Boundary", "small"),
        ]),
        (218, "purple", "Part II: Parallel", "Threads & Scheduling", "timer", [
            ("Ch 04: Thread Hazards", "small"),
            ("Ch 05: CPU Scheduling", "small"),
            ("Ch 06: Synchronization", "small"),
            ("Ch 17: NUMA Systems", "small"),
        ]),
        (408, "teal", "Part III: Systems", "I/O, IPC & Isolation", "lan", [
            ("Ch 10: Signals & Traps", "small"),
            ("Ch 11: IPC & Shared Mem", "small"),
            ("Ch 12: File Systems", "small"),
            ("Ch 13: I/O Event Loops", "small"),
            ("Ch 14: Sockets & TCP", "small"),
            ("Ch 15: Daemons & Init", "small"),
            ("Ch 16: Virtualization", "small"),
        ]),
        (598, "amber", "Part IV: Practice", "Perf & Interviews", "engineering", [
            ("Ch 18: Profiling & Perf", "small"),
            ("Ch 19: Systems Problems", "small"),
        ]),
    ]

    for x, tone, title, subtitle, icon, chapters in parts:
        fig.node(x, 12, 172, 394, tone, kind="tonal", r=12)
        fig.tile(x + 10, 22, icon, tone, 28)
        fig.text(x + 44, 32, title, "name", fit=(x + 44, x + 168))
        fig.text(x + 44, 46, subtitle, "small", fit=(x + 44, x + 168))

        y_cur = 60
        for ch_title, ch_cls in chapters:
            fig.cell(x + 8, y_cur, 156, 36, tone, [(ch_title, ch_cls)], kind="card", r=7)
            y_cur += 44

    fig.cell(36, 328, 156, 68, "blue", [
        ("Hardware Abstraction", "small"),
        ("MMU page translation", "small"),
        ("and kernel trap gates.", "small")
    ], kind="card", r=7)

    fig.cell(226, 240, 156, 156, "purple", [
        ("Key Invariants", "small"),
        ("• MESI coherence", "small"),
        ("• False sharing (64B)", "small"),
        ("• Atomics & ordering", "small"),
        ("• Lock-free ring buffer", "small"),
        ("• Priority inversion", "small")
    ], kind="card", r=7)

    fig.cell(606, 152, 156, 114, "amber", [
        ("48-Hour Fast Track", "small"),
        ("High-yield chapters:", "small"),
        ("Ch 06 (Synchronization)", "small"),
        ("Ch 07 (Virtual Memory)", "small"),
        ("Ch 08 (Allocators)", "small"),
        ("Ch 13 (I/O Multiplex)", "small")
    ], kind="card", r=7)

    fig.cell(606, 274, 156, 122, "amber", [
        ("Dual-Language Code", "small"),
        ("Side-by-side listings:", "small"),
        ("• ISO C++20 (sympathy)", "small"),
        ("• Rust 2024 (safety)", "small"),
        ("• 100% test harness", "small"),
        ("• Zero fictional code", "small")
    ], kind="card", r=7)

    fig.wire([(201, 36), (217, 36)], "blue", width=2.0)
    fig.wire([(391, 36), (407, 36)], "purple", width=2.0)
    fig.wire([(581, 36), (597, 36)], "teal", width=2.0)

    fig.node(28, 418, 744, 46, "gray", [("Curriculum Progression: Part I (Silicon to Syscalls) → Part II (Concurrency) → Part III (I/O & IPC) → Part IV (Interviews)", "small")], icon="play_arrow", layout="left", kind="tonal", icon_size=24)

    fig.save([
        "Readers with imminent interview deadlines may jump directly to the 48-Hour Interview Track in Part IV.",
        "Every chapter is accompanied by side-by-side C++20 and Rust (2024 edition) production implementations.",
    ])


@figure
def preface_ring_transition():
    fig = Fig("preface_ring_transition", "Figure P-1. Hardware Privilege Transition: Ring 3 (User) → Ring 0 (Kernel)", 416)

    fig.add('''
  <style>
    @keyframes flow-down {
      from { stroke-dashoffset: 24; }
      to { stroke-dashoffset: 0; }
    }
    @keyframes flow-up {
      from { stroke-dashoffset: 0; }
      to { stroke-dashoffset: 24; }
    }
    @keyframes gate-glow {
      0%, 100% { filter: drop-shadow(0 0 2px rgba(26, 95, 196, 0.3)); }
      50% { filter: drop-shadow(0 0 10px rgba(27, 122, 58, 0.6)); }
    }
    .flow-down {
      stroke-dasharray: 6 6;
      animation: flow-down 1.2s linear infinite;
    }
    .flow-up {
      stroke-dasharray: 6 6;
      animation: flow-up 1.2s linear infinite;
    }
    .gate-glow {
      animation: gate-glow 2.5s ease-in-out infinite;
    }
  </style>
''')

    # 1. Ring 3: User Mode
    fig.node(28, 8, 744, 136, "blue")
    fig.tile(42, 18, "terminal", "blue", 28)
    fig.text(78, 38, "Ring 3: User Space (CPL = 3)", "name")
    fig.text(320, 38, "Private Virtual Memory · Hardware Protection Enforced", "small")

    fig.cell(42, 54, 224, 78, "blue", [
        ("User Thread Context", "name"),
        ("• %rsp: 0x7fff_ffff_e480", "mono"),
        ("• %rip: 0x0000_0040_1020", "mono"),
        ("• Calling libc read(fd, ...)", "small"),
    ], kind="card", r=8)

    fig.cell(284, 54, 232, 78, "blue", [
        ("Syscall Register Setup", "name"),
        ("• %rax = 0 (sys_read)", "mono"),
        ("• %rdi = fd, %rsi = buf", "mono"),
        ("• %rdx = len (argument setup)", "small"),
    ], kind="card", r=8)

    fig.cell(534, 54, 224, 78, "blue", [
        ("Ring 3 Restrictions", "name"),
        ("• MMU blocks supervisor PTE", "small"),
        ("• Inaccessible: CR0, CR3, CR4", "small"),
        ("• Trapped: cli, sti, invlpg", "small"),
    ], kind="card", r=8)

    # 2. Hardware Privilege Boundary
    fig.rule(28, 182, 772, 182, "gray", width=2, dash="3 5")

    # Gate container
    fig.add('<g class="gate-glow">')
    fig.node(215, 158, 370, 48, "amber", [
        ("Privilege Gate: SYSCALL / SYSENTER", "name"),
        ("Atomic CPL switch 3 → 0 · Pipeline flush", "small")
    ], icon="shield", layout="left", kind="card", r=10, icon_size=28)
    fig.add("</g>")

    # 3. Ring 0: Kernel Mode
    fig.node(28, 236, 744, 136, "green")
    fig.tile(42, 246, "settings_suggest", "green", 28)
    fig.text(78, 266, "Ring 0: Kernel Space (CPL = 0)", "name")
    fig.text(320, 266, "Supervisor Execution · Physical Memory Control · Device MMIO", "small")

    fig.cell(42, 282, 224, 78, "green", [
        ("Per-CPU Kernel Stack", "name"),
        ("• swapgs sets kernel GS", "small"),
        ("• Switches to TSS.rsp0 stack", "small"),
        ("• Pushes trapframe context", "small"),
    ], kind="card", r=8)

    fig.cell(284, 282, 232, 78, "green", [
        ("MSR_LSTAR Dispatch", "name"),
        ("• Silicon loads %rip from MSR", "small"),
        ("• sys_call_table[%rax]", "mono"),
        ("• Invokes ksys_read() handler", "small"),
    ], kind="card", r=8)

    fig.cell(534, 282, 224, 78, "green", [
        ("Supervisor Privileges", "name"),
        ("• Full physical memory access", "small"),
        ("• Modifies CR3 & page tables", "small"),
        ("• Arbitrates interrupts & DMA", "small"),
    ], kind="card", r=8)

    # Wires and animation paths: positioned cleanly in the gap (y=134..156 and y=210..234)
    # and labels offset to the side so the vertical arrows never pierce the text!
    fig.wire([(112, 134), (112, 234)], "blue", width=2.4)
    fig.label(122, 186, "syscall trap", tone="blue", anchor="start", backed=True)

    fig.wire([(688, 234), (688, 134)], "green", width=2.4)
    fig.label(678, 186, "sysretq / iret", tone="green", anchor="end", backed=True)

    # Animated pulse elements
    fig.add('''
  <!-- Animated Trap Particle (Ring 3 -> Ring 0) -->
  <g>
    <circle r="5" class="a-blue">
      <animateMotion path="M 112,134 L 112,234" dur="1.8s" repeatCount="indefinite" />
    </circle>
    <circle r="9" class="a-blue" opacity="0.35">
      <animateMotion path="M 112,134 L 112,234" dur="1.8s" repeatCount="indefinite" />
    </circle>
  </g>

  <!-- Animated Return Particle (Ring 0 -> Ring 3) -->
  <g>
    <circle r="5" class="a-green">
      <animateMotion path="M 688,234 L 688,134" dur="1.8s" repeatCount="indefinite" />
    </circle>
    <circle r="9" class="a-green" opacity="0.35">
      <animateMotion path="M 688,234 L 688,134" dur="1.8s" repeatCount="indefinite" />
    </circle>
  </g>
''')

    fig.save([
        "The syscall instruction does not call a C function; it raises a hardware trap that atomically switches the privilege ring from 3 to 0.",
        "CPU hardware swaps the user stack (%rsp) to the per-CPU kernel stack (TSS.rsp0) and vectors execution to MSR_LSTAR.",
    ])


# ---------------------------------------------------------------- Chapter 1

@figure
def ch01_layers():
    fig = Fig("ch01_layers", "Figure 1-1. Four layers, one machine.", 388)

    layers = [
        (0, 68, "blue", "apps", ["Applications", "browser, editor, server, your program"],
         ["talk to the operating system,", "never to the hardware directly"]),
        (100, 68, "purple", "library_books",
         ["System libraries", "libc, the C++ standard library, the Rust standard library"],
         ["turn ordinary function calls into", "system calls, and buffer the results"]),
        (200, 88, "green", "settings_suggest",
         ["Kernel", "processes and threads · virtual memory · file systems",
          "device drivers · networking · scheduling · interrupts"],
         ["the only code that runs in", "privileged mode (ring 0)"]),
        (320, 68, "amber", "memory",
         ["Hardware", "CPU cores, caches, memory, disks, network interfaces, timers"],
         ["executes instructions and", "raises interrupts"]),
    ]

    for y, height, tone, icon, left, right in layers:
        box = fig.node(28, y, 744, height, tone, left, icon=icon, icon_size=40)
        fig.lines(756, box.cy, [(line, "sub") for line in right], "end", fit=(540, 760))

    down = [(68, 100, "requests flow down"), (168, 200, "system calls"), (288, 320, "instructions, DMA")]
    for top, bottom, text in down:
        fig.wire([(250, top + 3), (250, bottom - 3)], "wire", width=2.2)
        fig.text(264, (top + bottom) / 2 + 4.5, text, "sub")

    fig.wire([(520, 317), (520, 291)], "red", width=2.2)
    fig.text(534, 308.5, "interrupts flow up", "sub", tone="red")

    fig.save()


# ---------------------------------------------------------------- Chapter 2

@figure
def ch02_machine():
    fig = Fig("ch02_machine", "Figure 2-1. The machine model used throughout this book.", 404)

    fig.text(476, 16, "interrupts pause the current instruction stream", "sub", "middle", tone="red")

    cpu = fig.node(28, 30, 320, 226, "blue")
    fig.tile(44, 44, "memory", "blue", 34)
    fig.text(90, 66, "CPU core", "name")
    fig.text(44, 98, "registers", "sub")

    fig.cell(44, 106, 52, 30, "blue", [("PC", "mono")], kind="card")
    fig.cell(102, 106, 52, 30, "blue", [("SP", "mono")], kind="card")
    fig.cell(160, 106, 96, 30, "blue", [("R0 … R15", "mono")], kind="card")
    fig.cell(262, 106, 70, 30, "blue", [("flags", "mono")], kind="card")

    fig.cell(44, 148, 96, 46, "blue", [("ALU", "name")], kind="card")
    fig.cell(148, 148, 184, 46, "blue", [("control unit", "name"), ("fetch · decode · execute", "small")], kind="card")
    fig.cell(44, 206, 288, 34, "blue", [("MMU: virtual → physical addresses", "sub")], kind="card")

    l1 = fig.cell(388, 70, 180, 54, "teal", [("L1 I-cache / D-cache", "name"), "32–64 KiB, ≈4 cycles"], kind="tonal", r=12)
    l2 = fig.cell(388, 136, 180, 54, "teal", [("L2 cache", "name"), "256 KiB–1 MiB, ≈10 cycles"], kind="tonal", r=12)
    l3 = fig.cell(388, 202, 180, 54, "teal", [("L3 cache (shared)", "name"), "4–32 MiB, ≈40 cycles"], kind="tonal", r=12)
    for cache in (l1, l2, l3):
        fig.wire([(cpu.r + 3, cache.cy), (cache.x - 3, cache.cy)])

    irq = fig.node(604, 30, 168, 56, "red", [("interrupt", "name"), ("controller", "name")], icon="notifications_active", r=12)
    controller = fig.node(604, 120, 168, 56, "gray", [("memory", "name"), ("controller", "name")], icon="tune", r=12)
    dram = fig.node(604, 200, 168, 56, "green", ["DRAM", "main memory"], icon="view_module", r=12)

    fig.wire([(irq.x - 3, 46), (cpu.r + 3, 46)], "red")
    fig.wire([(l2.r + 3, 158), (controller.x - 3, 158)])
    fig.wire([(controller.cx, controller.b + 2), (dram.cx, dram.y - 2)])

    fig.text(28, 290, "PCIe bus", "sub")
    fig.rect(28, 298, 744, 10, "m-gray", r=5)

    devices = [
        (28, 170, "lan", ["NIC", "network"]),
        (214, 170, "save", ["SSD controller", "storage"]),
        (400, 170, "developer_board", ["accelerator", "GPU / ML silicon"]),
        (586, 186, "timer", ["timer", "ticks for scheduling"]),
    ]
    for x, width, icon, text in devices:
        device = fig.node(x, 338, width, 64, "amber", text, icon=icon, r=12)
        fig.wire([(device.cx, device.y - 2), (device.cx, 310)])

    fig.save([
        "A device reports a finished transfer, new data, or an error to the CPU through the interrupt controller.",
        "With direct memory access (DMA), a device copies data to and from DRAM while the CPU does other work.",
    ])


@figure
def ch02_privilege():
    fig = Fig("ch02_privilege", "Figure 2-4. Two privilege levels; every trap crosses the boundary.", 300)

    fig.node(28, 0, 744, 120, "blue")
    fig.tile(44, 12, "person", "blue", 28)
    fig.text(82, 32, "User mode (ring 3)", "name")
    process_a = fig.node(44, 52, 176, 54, "blue", ["process A", "private address space"], layout="center", kind="card", r=10)
    fig.node(232, 52, 176, 54, "blue", ["process B", "private address space"], layout="center", kind="card", r=10)
    fig.lines(430, 79, [("can only touch its own memory,", "sub"), ("and cannot execute privileged instructions", "sub")],
              "start", fit=(430, 764))

    fig.rule(28, 150, 772, 150, "gray", width=3, dash="2 7")
    fig.icon(338, 139, "shield", "gray", 20)
    fig.label(420, 155, "privilege boundary", cls="sub")

    fig.node(28, 180, 744, 120, "green")
    fig.tile(44, 192, "settings_suggest", "green", 28)
    fig.text(82, 212, "Kernel mode (ring 0)", "name")
    fig.node(44, 232, 190, 54, "green", ["kernel code and data", "mapped into every process"], layout="center", kind="card", r=10)
    fig.node(246, 232, 204, 54, "green", ["device registers", "only the kernel touches them"], layout="center", kind="card", r=10)
    fig.lines(472, 259, [("executes privileged instructions,", "sub"), ("handles traps and interrupts", "sub")],
              "start", fit=(472, 764))

    fig.wire([(process_a.cx, 123), (process_a.cx, 177)], "blue", width=2.2)
    fig.label(process_a.cx + 14, 155, "system call (trap)", tone="blue", anchor="start")

    fig.wire([(640, 177), (640, 123)], "green", width=2.2)
    fig.label(654, 155, "return to user", tone="green", anchor="start")

    fig.save()


@figure
def ch02_stack_frame():
    fig = Fig("ch02_stack_frame", "Figure 2-2. Function Activation Record: Call Stack Frame Layout and Register Pointers", 404)

    fig.text(28, 14, "high memory", "small")
    fig.wire([(46, 22), (46, 376)], "gray", width=1.6)
    fig.text(28, 394, "low memory", "small")

    x, w = 104, 430

    # Caller Frame
    fig.node(x, 12, w, 54, "gray", [
        ("Caller Activation Record", "name"),
        ("caller local variables & saved registers", "small"),
    ], icon="layers", r=10)

    fig.cell(x, 72, w, 36, "gray", [("Caller Outgoing Args (arg 7+, if beyond registers)", "sub")], kind="mid", r=7)

    # Callee Frame boundary container
    fig.node(x - 8, 116, w + 16, 224, "purple", kind="dashed", r=12)

    ret = fig.cell(x, 124, w, 46, "amber", [
        ("Return Address (saved RIP / x30 LR)", "name"),
        ("pushed by CALL or saved in prologue", "small"),
    ], kind="mid", r=7)

    fp = fig.cell(x, 176, w, 46, "blue", [
        ("Saved Frame Pointer (old RBP / x29 FP)", "name"),
        ("points to caller's frame pointer base", "small"),
    ], kind="mid", r=7)

    fig.cell(x, 228, w, 54, "purple", [
        ("Callee-Saved Registers & Local Variables", "name"),
        ("RBX, R12–R15 / x19–x28 · stack buffers [RBP - offset]", "small"),
    ], kind="card", r=7)

    sp = fig.cell(x, 288, w, 46, "teal", [
        ("Outgoing Parameter Area / Scratch Space", "name"),
        ("16-byte ABI stack alignment boundary", "small"),
    ], kind="mid", r=7)

    redzone = fig.node(x, 348, w, 42, "red", kind="dashed", r=8)
    fig.text(redzone.cx, redzone.cy + 4.5, "Unallocated Stack / 128-Byte Red Zone (x86-64 leaf functions) ↓", "sub", "middle")

    # Register Pointers on the right
    fig.wire([(578, ret.cy), (ret.r + 3, ret.cy)], "amber", width=2.0)
    fig.cell(582, ret.cy - 18, 190, 36, "amber", [("[RBP + 8] → Return PC", "mono")], kind="card", r=7)

    fig.wire([(578, fp.cy), (fp.r + 3, fp.cy)], "blue", width=2.2)
    fig.cell(582, fp.cy - 22, 190, 44, "blue", [("FP (RBP / x29)", "monob"), ("invariant frame anchor", "small")], kind="card", r=7)

    fig.wire([(578, sp.b - 8), (sp.r + 3, sp.b - 8)], "teal", width=2.2)
    fig.cell(582, sp.b - 28, 190, 44, "teal", [("SP (RSP / SP_EL0)", "monob"), ("active top of stack", "small")], kind="card", r=7)

    # Frame pointer chain arc on the left
    fig.wire([(x, fp.cy), (74, fp.cy), (74, 39), (x - 3, 39)], "blue", dash=True, width=1.8)

    fig.save([
        "The stack grows downward toward lower virtual addresses. Pushing decrements SP; popping increments SP.",
        "FP (RBP / x29) forms a singly linked chain of activation records, enabling O(depth) stack unwinding for debuggers and profilers.",
        "System V AMD64 and AAPCS64 ABIs mandate 16-byte SP alignment at function call boundaries for SIMD vector instructions.",
    ])


@figure
def ch02_interrupt_flow():
    fig = Fig("ch02_interrupt_flow", "Figure 2-8. End-to-End Hardware Interrupt Lifecycle: Device Signal, Top-Half hardirq, EOI, and Bottom-Half softirq.", 384)

    # Top row: Hardware delivery pipeline
    dev = fig.node(28, 16, 168, 102, "amber", [
        ("1. Peripheral", "name"),
        ("NIC / NVMe / Timer", "small"),
        ("DMA done, raises IRQ", "small"),
    ], icon="lan", layout="center", icon_size=26, r=10)

    apic = fig.node(220, 16, 172, 102, "red", [
        ("2. IRQ Controller", "name"),
        ("IO-APIC → Local APIC", "small"),
        ("(or ARM GICv3/v4)", "small"),
    ], icon="notifications_active", layout="center", icon_size=26, r=10)

    cpu = fig.node(416, 16, 168, 102, "blue", [
        ("3. CPU Core Gate", "name"),
        ("Checks IF / DAIF mask", "small"),
        ("Switches Ring 3 → 0", "small"),
    ], icon="memory", layout="center", icon_size=26, r=10)

    idt = fig.node(608, 16, 164, 102, "purple", [
        ("4. Vector Table", "name"),
        ("IDT[vec] / VBAR_EL1", "mono"),
        ("Loads ISR entry PC", "small"),
    ], icon="table_rows", layout="center", icon_size=26, r=10)

    fig.wire([(dev.r + 2, 67), (apic.x - 2, 67)], "amber", width=2.2)
    fig.wire([(apic.r + 2, 67), (cpu.x - 2, 67)], "red", width=2.2)
    fig.wire([(cpu.r + 2, 67), (idt.x - 2, 67)], "blue", width=2.2)

    # Bottom row: Kernel execution & hardware trapframe
    trap = fig.node(28, 158, 226, 206, "blue")
    fig.tile(40, 170, "shield", "blue", 28)
    fig.text(76, 190, "5. Context Save", "name", fit=(76, 246))
    fig.text(40, 210, "Pushed to Kernel Stack (TSS.rsp0):", "small")
    for idx, reg in enumerate(["SS & User RSP (stack)", "RFLAGS / PSTATE (flags)", "CS & User RIP (return PC)", "Error Code / GP Registers"]):
        fig.cell(40, 220 + idx * 33, 202, 28, "blue", [(reg, "mono")], kind="card", r=6)

    top_half = fig.node(276, 158, 236, 206, "green")
    fig.tile(288, 170, "bolt", "green", 28)
    fig.text(324, 190, "6. Top-Half (hardirq)", "name", fit=(324, 504))
    fig.cell(288, 206, 212, 46, "green", [
        ("Interrupts Masked on Core", "body"),
        ("Zero blocking · Minimal latency", "small"),
    ], kind="card", r=7)
    fig.cell(288, 258, 212, 46, "green", [
        ("Ack Device & Queue Work", "body"),
        ("Read MMIO status, raise softirq", "small"),
    ], kind="card", r=7)
    eoi = fig.cell(288, 310, 212, 44, "red", [
        ("7. Write EOI to Local APIC", "name"),
        ("Unmasks controller for next IRQ", "small"),
    ], kind="mid", r=7)

    bot_half = fig.node(534, 158, 238, 206, "teal")
    fig.tile(546, 170, "schedule", "teal", 28)
    fig.text(582, 190, "8. Bottom-Half & Exit", "name", fit=(582, 764))
    fig.cell(546, 206, 214, 68, "teal", [
        ("Deferred Execution (softirq)", "name"),
        ("IRQs enabled · TCP/IP stack,", "small"),
        ("block I/O completion, NAPI poll", "small"),
    ], kind="card", r=7)
    fig.cell(546, 282, 214, 70, "purple", [
        ("9. Return: IRETQ / ERET", "name"),
        ("Restores RIP, RSP, RFLAGS;", "small"),
        ("demotes CPL 0 → 3 (or preempts)", "small"),
    ], kind="card", r=7)

    # Connecting wires from top row to bottom row (routed strictly through empty corridors!)
    fig.wire([(idt.cx, idt.b + 2), (idt.cx, 134), (141, 134), (141, trap.y - 2)], "purple", width=2.0)
    fig.wire([(trap.r + 2, 261), (top_half.x - 2, 261)], "blue", width=2.2)
    fig.wire([(top_half.r + 2, 240), (bot_half.x - 2, 240)], "green", width=2.2)
    # Route EOI wire down, then up through the vertical gap x=265 between trap (r=254) and top_half (x=276)!
    fig.wire([(eoi.cx, eoi.b + 10), (eoi.cx, 374), (265, 374), (265, 144), (306, 144), (306, apic.b + 2)], "red", dash=True, width=1.8)

    fig.save([
        "Hardware saves the interrupted user context onto the per-CPU kernel stack before executing the first ISR instruction.",
        "Splitting handlers into an atomic Top-Half (hardirq) and an interruptible Bottom-Half (softirq) prevents IRQ loss under heavy load.",
    ])


# ---------------------------------------------------------------- Chapter 3

@figure
def ch03_pcb_layout():
    fig = Fig(
        "ch03_pcb_layout",
        "Figure 3-1. Internal Data Structure of the Process Control Block (Linux struct task_struct) and Indirect Kernel Subsystems.",
        452,
    )

    # Left container: struct task_struct (PCB)
    pcb = fig.node(20, 20, 324, 412, "blue")
    fig.tile(32, 32, "layers", "blue", 28)
    fig.text(68, 48, "Process Control Block", "name")
    fig.text(68, 63, "struct task_struct (~6-10 KiB SLUB slab)", "small")

    c_id = fig.cell(32, 76, 300, 50, "blue", [
        ("Identity & Process Tree", "monob"),
        ("pid, tgid, *parent, children/sibling", "small"),
    ], kind="card", r=6)

    c_sched = fig.cell(32, 134, 300, 50, "purple", [
        ("Scheduling & Execution State", "monob"),
        ("state, on_cpu, se (vruntime, weight)", "small"),
    ], kind="card", r=6)

    c_ctx = fig.cell(32, 192, 300, 50, "amber", [
        ("Hardware Context & Kernel Stack", "monob"),
        ("void *stack, thread_struct (SP, FPU, TLS)", "small"),
    ], kind="card", r=6)

    c_mm = fig.cell(32, 250, 300, 50, "teal", [
        ("Memory Descriptor Pointer", "monob"),
        ("struct mm_struct *mm  (refcounted)", "small"),
    ], kind="card", r=6)

    c_files = fig.cell(32, 308, 300, 50, "green", [
        ("File & Filesystem Pointers", "monob"),
        ("files_struct *files, fs_struct *fs", "small"),
    ], kind="card", r=6)

    c_sig = fig.cell(32, 366, 300, 50, "red", [
        ("Signals & Security Credentials", "monob"),
        ("*sighand, pending/blocked, *cred", "small"),
    ], kind="card", r=6)

    # Right column: referenced kernel subsystems
    r_tree = fig.node(424, 24, 356, 72, "purple")
    fig.tile(436, 36, "table_rows", "purple", 26)
    fig.text(470, 52, "Intrusive Kernel Lists (list_head)", "name")
    fig.lines(602, 78, [
        ("Parent/children tree + Per-CPU CFS runqueue / wait queues", "small"),
    ], "middle", fit=(432, 772))

    r_kstack = fig.node(424, 110, 356, 72, "amber")
    fig.tile(436, 122, "memory", "amber", 26)
    fig.text(470, 138, "Kernel Stack (8-16 KiB per thread)", "name")
    fig.lines(602, 164, [
        ("Top: pt_regs trapframe (RIP, RSP)  |  Kernel frames below", "small"),
    ], "middle", fit=(432, 772))

    r_mm = fig.node(424, 196, 356, 72, "teal")
    fig.tile(436, 208, "layers", "teal", 26)
    fig.text(470, 224, "struct mm_struct (Shared by Threads)", "name")
    fig.lines(602, 250, [
        ("pgd -> CR3 / TTBR0_EL1 | VMA tree (text, heap, stack)", "small"),
    ], "middle", fit=(432, 772))

    r_files = fig.node(424, 282, 356, 72, "green")
    fig.tile(436, 294, "folder", "green", 26)
    fig.text(470, 310, "struct files_struct & struct fs_struct", "name")
    fig.lines(602, 336, [
        ("fd_array[0..N] -> struct file -> inode  |  pwd, root, cloexec", "small"),
    ], "middle", fit=(432, 772))

    r_sig = fig.node(424, 368, 356, 64, "red")
    fig.tile(436, 380, "shield", "red", 26)
    fig.text(470, 396, "Signal Table & RCU Credentials", "name")
    fig.lines(602, 418, [
        ("action[1..64] (sigaction)  |  Immutable UID, GID, capabilities", "small"),
    ], "middle", fit=(432, 772))

    # Wires connecting PCB fields to indirect kernel structures
    fig.wire([(pcb.r + 2, 100), (382, 100), (382, 52), (r_tree.x - 2, 52)], "blue", width=1.8)
    fig.wire([(pcb.r + 2, 158), (392, 158), (392, 68), (r_tree.x - 2, 68)], "purple", width=1.8)
    fig.wire([(pcb.r + 2, 217), (386, 217), (386, 146), (r_kstack.x - 2, 146)], "amber", width=1.8)
    fig.wire([(pcb.r + 2, 275), (392, 275), (392, 232), (r_mm.x - 2, 232)], "teal", width=1.8)
    fig.wire([(pcb.r + 2, 333), (386, 333), (386, 318), (r_files.x - 2, 318)], "green", width=1.8)
    fig.wire([(pcb.r + 2, 391), (r_sig.x - 2, 391)], "red", width=1.8)

    fig.save([
        "Storing mm, files, and sighand as reference-counted pointers lets clone() create threads by sharing tables rather than copying them.",
        "Hot scheduling fields (state, kernel stack, sched_entity) are cache-line aligned near the start of task_struct to minimize context-switch misses.",
    ])


@figure
def ch03_address_space():
    fig = Fig("ch03_address_space", "Figure 3-2. The address space of one process (64-bit, simplified).", 446)

    fig.text(28, 12, "high addresses", "small")
    fig.wire([(40, 440), (40, 22)], "gray", width=1.6)
    fig.text(28, 444, "0", "small", "end", fit=(14, 30))

    x, width = 64, 500

    fig.node(x, 20, width, 60, "gray", ["kernel", "mapped into every process, not accessible from user mode"], icon="lock")

    stack = fig.node(x, 88, width, 68, "purple", ["stack", "local variables, call frames, return addresses"], icon="layers")
    fig.text(stack.r - 14, 112, "grows down ↓", "sub", "end", tone="purple")

    gap = fig.node(x, 164, width, 44, "gray", kind="dashed", r=10)
    fig.text(gap.cx, gap.cy + 4.5, "unmapped region; shared libraries and mmap live here on Linux", "sub", "middle",
             fit=(gap.x + 6, gap.r - 6))

    heap = fig.node(x, 216, width, 68, "green", ["heap", "memory from malloc / new / Box, grows up ↑"], icon="widgets")

    bss = fig.node(x, 292, width, 40, "amber", r=10)
    fig.text(x + 16, bss.cy + 5, "BSS", "name")
    fig.text(x + 70, bss.cy + 4.5, "uninitialized globals (zero-filled)", "sub")

    data = fig.node(x, 338, width, 40, "amber", kind="mid", r=10)
    fig.text(x + 16, data.cy + 5, "data", "name")
    fig.text(x + 70, data.cy + 4.5, "initialized globals and statics", "sub")

    fig.node(x, 386, width, 60, "blue", ["text", "the machine code of your program; read-only, shared"], icon="code")

    fig.wire([(604, 150), (stack.r + 3, 150)], "purple")
    fig.text(612, 147, "stack pointer", "name")
    fig.text(612, 165, "points here", "sub")

    fig.wire([(604, 222), (heap.r + 3, 222)], "green")
    fig.text(612, 227, "break pointer", "name")

    fig.save([
        "Listing 3-1 in Section 3.2 prints one address from each region.",
        "macOS places the heap in a separate region, but the order of the regions is the same.",
        "Linux places shared libraries and mmap regions between heap and stack.",
    ])


@figure
def ch03_fork():
    fig = Fig("ch03_fork", "Figure 3-3. fork() creates a second process that starts as a copy.", 212)

    fig.heading(28, 16, "before")
    before = fig.node(28, 30, 240, 66, "blue", ["process, PID 100", "one address space"], icon="terminal")
    memory = fig.node(28, 122, 240, 90, "gray", [("text + data + heap + stack", "sub"), ("open files, cwd, signal masks", "sub")],
                      layout="center", kind="card", r=10)
    fig.wire([(before.cx, before.b + 2), (memory.cx, memory.y - 2)])

    fig.wire([(284, 121), (372, 121)], "blue", width=2.4)
    fig.tile(311, 78, "call_split", "blue", 34)
    fig.text(328, 142, "fork()", "monob", "middle")

    fig.heading(388, 16, "after")
    copies = [
        (388, "blue", "PID 100 (parent)", "fork() returned 200"),
        (592, "green", "PID 200 (child)", "fork() returned 0"),
    ]
    tops = []
    for x, tone, name, returned in copies:
        top = fig.node(x, 30, 180, 66, tone, [name, (returned, "mono")], layout="center")
        bottom = fig.node(x, 122, 180, 90, tone,
                          [("its own copy of", "sub"), ("the address space", "sub"), ("(copy-on-write)", "sub")],
                          layout="center", kind="card", r=10)
        fig.wire([(top.cx, top.b + 2), (bottom.cx, bottom.y - 2)])
        tops.append(top)

    fig.wire([(tops[0].r + 2, 63), (tops[1].x - 2, 63)], "gray", dash=True, tail=True, width=1.5)

    fig.save([
        "Each process has its own PID, parent PID, and descriptor table. Memory is copied only when one of them writes to a page.",
        "The child continues at the instruction after fork(), with the same code and the same variable values.",
        ("A program tells parent and child apart by the return value of fork().", "noteb"),
        "fork() returns the child’s PID in the parent, 0 in the child, and -1 on error.",
    ])


@figure
def ch03_process_lifecycle():
    fig = Fig("ch03_process_lifecycle", "Figure 3-4. The Five-State Process Lifecycle Automaton: Kernel Scheduling, Blocking, and Reaping", 332)

    # Top row: New -> Ready <-> Running -> Zombie -> Terminated
    new_st = fig.node(28, 32, 126, 96, "purple", [
        ("New", "name"),
        ("fork / clone", "mono"),
        ("PCB allocated", "small"),
    ], icon="call_split", layout="center", icon_size=24, r=10)

    ready_st = fig.node(196, 32, 144, 96, "blue", [
        ("Ready", "name"),
        ("In CPU runqueue", "small"),
        ("(TASK_RUNNING)", "mono"),
    ], icon="view_week", layout="center", icon_size=24, r=10)

    run_st = fig.node(416, 32, 144, 96, "green", [
        ("Running", "name"),
        ("On physical core", "small"),
        ("PC/SP active", "mono"),
    ], icon="memory", layout="center", icon_size=24, r=10)

    zombie_st = fig.node(614, 32, 158, 96, "red", [
        ("Zombie", "name"),
        ("exit() / _exit()", "mono"),
        ("Awaits waitpid()", "small"),
    ], icon="pending", layout="center", icon_size=24, r=10)

    # Bottom row: Blocked and Reaped
    block_st = fig.node(260, 214, 236, 98, "amber", [
        ("Blocked (Waiting)", "name"),
        ("read() / sleep / page fault", "mono"),
        ("Suspended in device wait queue", "small"),
    ], icon="hourglass_top", layout="center", icon_size=24, r=10)

    reaped_st = fig.node(614, 214, 158, 98, "gray", [
        ("Reaped", "name"),
        ("Parent waitpid()", "mono"),
        ("PCB & PID freed", "small"),
    ], icon="close", layout="center", icon_size=24, r=10)

    # Transitions
    fig.wire([(new_st.r + 2, 80), (ready_st.x - 2, 80)], "purple", width=2.2)
    fig.label(175, 68, "admit", tone="purple", backed=False)

    # Ready -> Running (dispatch)
    fig.wire([(ready_st.r + 2, 62), (run_st.x - 2, 62)], "green", width=2.2)
    fig.label(378, 50, "dispatch", tone="green", backed=False)

    # Running -> Ready (preempt)
    fig.wire([(run_st.x - 2, 98), (ready_st.r + 2, 98)], "blue", dash=True, width=2.0)
    fig.label(378, 116, "preempt", tone="blue", backed=False)

    # Running -> Zombie (exit)
    fig.wire([(run_st.r + 2, 80), (zombie_st.x - 2, 80)], "red", width=2.2)
    fig.label(587, 68, "exit()", tone="red", backed=False)

    # Zombie -> Reaped (waitpid)
    fig.wire([(zombie_st.cx, zombie_st.b + 2), (reaped_st.cx, reaped_st.y - 2)], "gray", width=2.2)
    fig.label(693, 174, "SIGCHLD + waitpid()", tone="gray", backed=True)

    # Running -> Blocked (straight vertical drop from x=454 into block_st top-right, label offset to right)
    fig.wire([(454, run_st.b + 2), (454, block_st.y - 2)], "amber", width=2.2)
    fig.label(466, 174, "I/O or lock wait", tone="amber", anchor="start", backed=False)

    # Blocked -> Ready (straight vertical rise from x=302 into ready_st bottom-right, label offset to left)
    fig.wire([(302, block_st.y - 2), (302, ready_st.b + 2)], "blue", width=2.2)
    fig.label(290, 174, "IRQ / wakeup", tone="blue", anchor="end", backed=False)

    fig.save([
        "A blocked process consumes zero CPU cycles; the kernel removes its PCB from the scheduler runqueue until an interrupt wakes it.",
        "Upon exit(), the process releases its user virtual memory mappings, but its PCB persists in the Zombie state until the parent calls waitpid().",
    ])


# ---------------------------------------------------------------- Chapter 4

@figure
def ch04_threads():
    fig = Fig("ch04_threads", "Figure 4-1. Threads share the address space; each keeps its own stack and registers.", 246)

    fig.heading(28, 16, "one thread")
    fig.node(28, 30, 220, 62, "blue", ["process", "PID, files, address space"], layout="center")
    fig.node(28, 104, 220, 142, "gray")
    fig.text(138, 128, "text · data · heap", "sub", "middle")
    fig.node(44, 146, 120, 84, "purple", [("stack", "name"), "+ registers"], icon="layers", layout="center",
             kind="card", r=10, icon_size=26)

    fig.heading(272, 16, "three threads, one process")
    fig.node(272, 30, 300, 62, "blue", ["process", "one PID, one address space, one file table"], layout="center")
    fig.node(272, 104, 300, 142, "gray")
    fig.text(422, 124, "text · data · heap (shared)", "sub", "middle")
    for index, x in enumerate((288, 380, 472)):
        stack = fig.node(x, 146, 84, 84, "purple", [(f"T{index + 1}", "name"), "stack"], icon="layers", layout="center",
                         kind="card", r=10, icon_size=26)
        fig.wire([(stack.cx, 143), (stack.cx, 131)], "purple", width=1.5)

    notes = [
        (52, "blue", ["shared: everything else", "private: stack + registers"]),
        (134, "purple", ["threads are how one process", "does several things at once"]),
        (210, "green", ["scheduling unit = thread,", "ownership unit = process"]),
    ]
    for cy, tone, text in notes:
        fig.rect(590, cy - 20, 3, 40, f"a-{tone}", r=1.5)
        fig.lines(602, cy, [(line, "sub") for line in text], "start", fit=(602, 776))

    fig.save([
        "A switch between threads of one process is cheaper than a switch between processes, because the page table stays the same.",
        "Because threads share an address space, two of them can write to one variable at the same time.",
        "Section 4.2 measures the result.",
    ])


@figure
def ch04_race_timeline():
    fig = Fig("ch04_race_timeline", "Figure 4-2. A lost update: two threads, one counter, four memory operations.", 296)

    fig.text(28, 14, "time →", "sub")
    fig.wire([(84, 10), (736, 10)], "gray", width=1.4)

    slot_x = [112, 238, 364, 490, 616]
    slot_w = 118

    fig.node(28, 28, 744, 72, "blue", r=12)
    fig.text(40, 68.5, "thread 1", "name")
    fig.node(28, 144, 744, 72, "purple", r=12)
    fig.text(40, 184.5, "thread 2", "name")

    for lane_y, tone in ((36, "blue"), (152, "purple")):
        fig.cell(slot_x[0], lane_y, slot_w, 56, tone, [("load", "name"), ("counter = 42", "mono")], kind="card", r=9)
        fig.cell(slot_x[1], lane_y, slot_w, 56, tone, [("add 1", "name"), ("→ 43", "mono")], kind="card", r=9)

    store_1 = fig.cell(slot_x[3], 36, slot_w, 56, "red", [("store 43", "name"), ("counter = 43", "mono")], kind="mid", r=9)
    store_2 = fig.cell(slot_x[4], 152, slot_w, 56, "red", [("store 43", "name"), ("counter = 43", "mono")], kind="mid", r=9)

    marker = fig.node(slot_x[2], 36, slot_w, 172, "gray", kind="dashed", r=10)
    fig.rect(slot_x[2] + 1, 37, slot_w - 2, 170, "paper", r=9)
    fig.lines(marker.cx, marker.cy, [("thread 2", "sub"), ("runs", "sub"), ("between", "sub"), ("load and", "sub"), ("store", "sub")],
              "middle", fit=(marker.x + 4, marker.r - 4))

    counter = fig.node(490, 236, 244, 60, "red", ["counter", "ends at 43, not 44"], icon="error", kind="card", r=12)
    fig.wire([(store_1.cx, store_1.b + 2), (store_1.cx, counter.y - 2)], "red")
    fig.wire([(store_2.cx, store_2.b + 2), (store_2.cx, counter.y - 2)], "red")

    fig.save(["Both threads load 42 and both store 43, so one of the two increments is lost."])


@figure
def ch04_thread_lifecycle():
    fig = Fig("ch04_thread_lifecycle", "Figure 4-3. Thread Lifecycle State Machine: Creation, Synchronization Parking, Join, and Detach", 332)

    init_st = fig.node(28, 32, 126, 96, "purple", [
        ("Spawned", "name"),
        ("pthread_create", "mono"),
        ("Stack + TCB init", "small"),
    ], icon="call_split", layout="center", icon_size=24, r=10)

    runnable_st = fig.node(196, 32, 144, 96, "blue", [
        ("Runnable", "name"),
        ("In core runqueue", "small"),
        ("Ready to execute", "small"),
    ], icon="view_week", layout="center", icon_size=24, r=10)

    active_st = fig.node(416, 32, 144, 96, "green", [
        ("Running", "name"),
        ("Executing on core", "small"),
        ("Private PC & SP", "mono"),
    ], icon="memory", layout="center", icon_size=24, r=10)

    term_st = fig.node(614, 32, 158, 96, "teal", [
        ("Terminated", "name"),
        ("Return / exit", "small"),
        ("Holds return value", "small"),
    ], icon="pending", layout="center", icon_size=24, r=10)

    parked_st = fig.node(260, 214, 236, 98, "amber", [
        ("Sleeping / Parked", "name"),
        ("Mutex / Condvar / Futex / I/O", "small"),
        ("Wait queue (0% CPU usage)", "small"),
    ], icon="lock", layout="center", icon_size=24, r=10)

    reclaimed_st = fig.node(614, 214, 158, 98, "gray", [
        ("Reclaimed", "name"),
        ("join() or detached", "mono"),
        ("Stack & TCB unmapped", "small"),
    ], icon="close", layout="center", icon_size=24, r=10)

    # Wires
    fig.wire([(init_st.r + 2, 80), (runnable_st.x - 2, 80)], "purple", width=2.2)
    fig.label(175, 68, "admit", tone="purple", backed=False)

    fig.wire([(runnable_st.r + 2, 62), (active_st.x - 2, 62)], "green", width=2.2)
    fig.label(378, 50, "dispatch", tone="green", backed=False)

    fig.wire([(active_st.x - 2, 98), (runnable_st.r + 2, 98)], "blue", dash=True, width=2.0)
    fig.label(378, 116, "preempt", tone="blue", backed=False)

    fig.wire([(active_st.r + 2, 80), (term_st.x - 2, 80)], "teal", width=2.2)
    fig.label(587, 68, "return", tone="teal", backed=False)

    fig.wire([(term_st.cx, term_st.b + 2), (reclaimed_st.cx, reclaimed_st.y - 2)], "gray", width=2.2)
    fig.label(693, 174, "thread::join()", tone="gray", backed=True)

    # Running -> Parked (straight vertical drop at x=454, label cleanly to the right)
    fig.wire([(454, active_st.b + 2), (454, parked_st.y - 2)], "amber", width=2.2)
    fig.label(466, 174, "lock / cond.wait", tone="amber", anchor="start", backed=False)

    # Parked -> Runnable (straight vertical rise at x=302, label cleanly to the left)
    fig.wire([(302, parked_st.y - 2), (302, runnable_st.b + 2)], "blue", width=2.2)
    fig.label(290, 174, "unlock / notify", tone="blue", anchor="end", backed=False)

    fig.save([
        "A joinable thread retains its Thread Control Block (TCB) and stack allocation after termination until another thread calls join().",
        "In Rust, std::thread::JoinHandle detaches automatically on drop, whereas C++20 std::jthread joins automatically in its destructor.",
    ])


# ---------------------------------------------------------------- Chapter 5

@figure
def ch05_queues():
    fig = Fig("ch05_queues", "Figure 5-1. The scheduler moves jobs between three places.", 262)

    ready = fig.node(28, 50, 210, 150, "blue")
    fig.tile(42, 60, "view_week", "blue", 28)
    fig.text(80, 80, "ready queue", "name")
    for x, job in ((44, "C"), (106, "B"), (168, "A")):
        fig.cell(x, 100, 54, 36, "blue", [(job, "name")], kind="card", r=9)
    fig.lines(ready.cx, 168, [("jobs that want the CPU", "sub"), ("waiting in order", "sub")], "middle",
              fit=(ready.x + 6, ready.r - 6))

    cpu = fig.node(318, 50, 150, 104, "green", ["CPU", "one job runs", "at a time"], icon="memory", layout="center",
                   icon_size=30)

    wait = fig.node(572, 50, 200, 150, "amber")
    fig.tile(586, 60, "hourglass_top", "amber", 28)
    fig.text(624, 80, "wait queue", "name")
    fig.cell(588, 100, 168, 36, "amber", [("blocked on I/O", "sub")], kind="card", r=9)
    fig.lines(wait.cx, 168, [("jobs waiting", "sub"), ("for an event", "sub")], "middle", fit=(wait.x + 6, wait.r - 6))

    fig.wire([(ready.r + 3, 92), (cpu.x - 3, 92)], "blue", width=2.2)
    fig.label(278, 82, "dispatch", tone="blue")

    fig.wire([(cpu.r + 3, 92), (wait.x - 3, 92)], "red", width=2.2)
    fig.label(520, 82, "blocks on I/O", tone="red")

    fig.wire([(cpu.cx + 30, cpu.y - 3), (cpu.cx + 30, 22), (ready.cx, 22), (ready.cx, ready.y - 3)], "wire")
    fig.label(278, 16, "time slice expires → back to ready", backed=False)

    fig.wire([(cpu.cx, cpu.b + 3), (cpu.cx, 204)], "green", width=2.2)
    fig.text(cpu.cx + 14, 186, "job finishes → exit", "sub", tone="green")

    fig.wire([(wait.cx, wait.b + 3), (wait.cx, 240), (ready.cx, 240), (ready.cx, ready.b + 3)], "wire")
    fig.label(400, 244.5, "I/O completes → back to ready")

    fig.save([
        "A job leaves the CPU when it finishes, when it blocks on I/O, or when its time slice expires.",
        "A scheduling policy decides which ready job is dispatched next. Section 5.2 compares three policies.",
        "A preemptive scheduler can interrupt a running job. A cooperative scheduler waits until the job gives up the CPU.",
    ])


@figure
def ch05_gantt():
    fig = Fig("ch05_gantt", "Figure 5-2. Three policies, the same three jobs (A = 10, B = 5, C = 5).", 236)

    tones = {"A": "blue", "B": "green", "C": "amber"}
    unit, left = 20, 136
    rows = [
        ("FCFS", [("A", 0, 10), ("B", 10, 15), ("C", 15, 20)], "average turnaround 15", [0, 10, 15, 20]),
        ("SJF", [("B", 0, 5), ("C", 5, 10), ("A", 10, 20)], "average turnaround 11.7", [0, 5, 10, 20]),
        ("RR, q = 5", [("A", 0, 5), ("B", 5, 10), ("C", 10, 15), ("A", 15, 20)], "average turnaround 15", [0, 5, 10, 15, 20]),
    ]

    for index, (policy, bars, average, ticks) in enumerate(rows):
        y = index * 84
        fig.text(28, y + 24, policy, "name")

        for job, start, end in bars:
            x = left + start * unit
            fig.cell(x + 1.5, y, (end - start) * unit - 3, 38, tones[job], [(f"{job} ({start}–{end})", "sub")],
                     kind="mid", r=8, text_tone=None)

        fig.rule(left, y + 44, left + 20 * unit, y + 44, "gray", width=1.4)
        for tick in ticks:
            x = left + tick * unit
            fig.rule(x, y + 40, x, y + 49, "gray", width=1.4)
            fig.text(x, y + 63, str(tick), "small", "middle")

        fig.icon(560, y + 9, "schedule", "gray", 19)
        fig.text(586, y + 24, average, "body")

    fig.save([
        "FCFS runs jobs in arrival order, so short jobs wait behind a long one.",
        "SJF gives the smallest average turnaround when all jobs arrive together, but it must know each running time.",
        "RR gives every job a turn within one pass through the queue, at the cost of more switches.",
    ])


@figure
def ch05_cfs_vruntime():
    fig = Fig("ch05_cfs_vruntime", "Figure 5-3. Linux CFS Red-Black Tree Runqueue and Weighted Virtual Runtime Accounting", 392)

    # Left: Red-Black Tree Structure (x=28..452, w=424)
    fig.node(28, 12, 424, 362, "blue", kind="tonal", r=12)
    fig.tile(42, 22, "call_split", "blue", 26)
    fig.text(76, 36, "Per-Core Red-Black Tree Runqueue", "name", fit=(76, 440))
    fig.text(76, 52, "Ordered strictly ascending by virtual runtime (vruntime)", "small", fit=(76, 440))

    root = fig.cell(168, 72, 146, 52, "blue", [
        ("Task B (nice 0)", "name"),
        ("vruntime: 14.0 ms", "mono"),
    ], kind="card", r=8)

    left_ch = fig.cell(44, 162, 168, 56, "green", [
        ("Task A (nice -10)", "name"),
        ("vruntime: 9.8 ms", "mono"),
    ], kind="card", r=8)

    right_ch = fig.cell(264, 162, 172, 56, "amber", [
        ("Task C (nice +10)", "name"),
        ("vruntime: 21.5 ms", "mono"),
    ], kind="card", r=8)

    fig.wire([(root.cx - 24, root.b + 2), (left_ch.cx + 12, left_ch.y - 2)], "green", width=2.2)
    fig.wire([(root.cx + 24, root.b + 2), (right_ch.cx - 12, right_ch.y - 2)], "amber", width=2.2)

    leftmost = fig.cell(44, 250, 168, 48, "green", [
        ("rb_leftmost pointer", "monob"),
        ("O(1) next-task dispatch", "small"),
    ], kind="mid", r=8)
    fig.wire([(leftmost.cx, leftmost.y - 2), (left_ch.cx, left_ch.b + 2)], "green", width=2.2)

    fig.cell(236, 250, 200, 48, "purple", [
        ("EEVDF Virtual Deadline", "name"),
        ("d = vruntime + slice / w", "mono"),
    ], kind="card", r=8)

    fig.cell(44, 314, 392, 46, "blue", [
        ("Enqueue / Re-insert: O(log N)  |  Pick Next: O(1)", "mono"),
        ("Minimum execution floor (min_granularity) prevents cache thrashing", "small"),
    ], kind="card", r=8)

    # Right: Worked Numerical Example (x=476..772, w=296)
    fig.node(476, 12, 296, 362, "teal", kind="tonal", r=12)
    fig.tile(490, 22, "schedule", "teal", 26)
    fig.text(524, 36, "Same 4 ms Physical Slice", "name", fit=(524, 760))
    fig.text(524, 52, "Δvruntime = Δexec × (1024 / w)", "mono", fit=(524, 760))

    fig.cell(492, 74, 264, 82, "green", [
        ("High Priority (nice -10)", "name"),
        ("weight = 9,548 (~9.3× base)", "small"),
        ("Δvruntime = 4 × (1024 / 9548)", "mono"),
        ("= +0.43 ms  (stays leftmost)", "monob"),
    ], kind="card", r=8)

    fig.cell(492, 174, 264, 82, "blue", [
        ("Baseline Priority (nice 0)", "name"),
        ("weight = 1,024 (1.0× base)", "small"),
        ("Δvruntime = 4 × (1024 / 1024)", "mono"),
        ("= +4.00 ms  (1:1 wall time)", "monob"),
    ], kind="card", r=8)

    fig.cell(492, 274, 264, 82, "amber", [
        ("Batch Priority (nice +10)", "name"),
        ("weight = 110 (~0.11× base)", "small"),
        ("Δvruntime = 4 × (1024 / 110)", "mono"),
        ("= +37.2 ms  (moves far right)", "monob"),
    ], kind="card", r=8)

    fig.save([
        "Because higher-priority tasks possess larger weights, their virtual runtime advances slowly, keeping them near rb_leftmost.",
        "Linux 6.6 EEVDF pairs eligibility lag with virtual deadlines so short latency-sensitive tasks preempt long compute bursts.",
    ])


@figure
def ch05_priority_inversion():
    fig = Fig("ch05_priority_inversion", "Figure 5-4. Unbounded Priority Inversion vs. Priority Inheritance Protocol Timeline", 386)

    # Top Timeline: Unbounded Priority Inversion Hazard (y=12..182)
    fig.node(28, 12, 744, 172, "red", kind="tonal", r=12)
    fig.tile(42, 22, "warning", "red", 24)
    fig.text(74, 35, "Scenario A: Unbounded Priority Inversion (No Inheritance — Mars Pathfinder Failure Mode)", "name", fit=(74, 760))

    lanes_a = [("T_High", 62, "red"), ("T_Med", 100, "amber"), ("T_Low", 138, "blue")]
    for label, ly, tone in lanes_a:
        fig.text(42, ly + 17, label, "monob", tone=tone, fit=(40, 102))
        fig.rule(108, ly + 13, 754, ly + 13, "gray", width=1.0, dash="3 3")

    # T_Low acquires M at t=0..2
    fig.cell(112, 136, 90, 26, "blue", [("holds M", "small")], kind="mid", r=6)
    # T_High wakes at t=2, tries M, blocks!
    fig.cell(204, 60, 74, 26, "red", [("lock(M)", "small")], kind="card", r=6)
    fig.rect(282, 60, 286, 26, "paper", r=6)
    fig.cell(282, 60, 286, 26, "red", [("BLOCKED on M (preempted by T_Med)", "small")], kind="dashed", r=6)
    # T_Med wakes at t=3, preempts T_Low for an unbounded duration!
    fig.cell(282, 98, 224, 26, "amber", [("T_Med preempts T_Low (CPU-bound)", "small")], kind="mid", r=6)
    # Finally T_Med finishes, T_Low resumes and unlocks M
    fig.cell(508, 136, 62, 26, "blue", [("unlock", "small")], kind="mid", r=6)
    # T_High finally runs
    fig.cell(572, 60, 178, 26, "green", [("T_High runs (severe delay)", "small")], kind="mid", r=6)

    # Bottom Timeline: Priority Inheritance Rescue (y=202..372)
    fig.node(28, 202, 744, 172, "green", kind="tonal", r=12)
    fig.tile(42, 212, "shield", "green", 24)
    fig.text(74, 225, "Scenario B: Priority Inheritance (PTHREAD_PRIO_INHERIT / FUTEX_LOCK_PI)", "name", fit=(74, 760))

    lanes_b = [("T_High", 252, "green"), ("T_Med", 290, "amber"), ("T_Low", 328, "blue")]
    for label, ly, tone in lanes_b:
        fig.text(42, ly + 17, label, "monob", tone=tone, fit=(40, 102))
        fig.rule(108, ly + 13, 754, ly + 13, "gray", width=1.0, dash="3 3")

    # T_Low holds M
    fig.cell(112, 326, 90, 26, "blue", [("holds M", "small")], kind="mid", r=6)
    # T_High blocks on M -> boosts T_Low!
    fig.cell(204, 250, 74, 26, "amber", [("lock(M)", "small")], kind="card", r=6)
    fig.rect(282, 250, 112, 26, "paper", r=6)
    fig.cell(282, 250, 112, 26, "gray", [("bounded wait", "small")], kind="dashed", r=6)
    # T_Low boosted to prio(T_High), finishes critical section immediately while T_Med stays runnable
    fig.cell(282, 326, 112, 26, "green", [("boosted → unlock", "small")], kind="mid", r=6)
    # T_High acquires M immediately and finishes!
    fig.cell(396, 250, 152, 26, "green", [("T_High acquires M & runs", "small")], kind="mid", r=6)
    # T_Med runs only AFTER T_High completes
    fig.cell(550, 288, 200, 26, "amber", [("T_Med runs after T_High finishes", "small")], kind="mid", r=6)

    fig.save([
        "Without priority inheritance, an unrelated medium-priority thread prevents the low-priority lock owner from releasing M.",
        "With priority inheritance, blocking on M temporarily donates T_High's priority to T_Low, bounding T_High's wait time.",
    ])


# ---------------------------------------------------------------- Chapter 6

@figure
def ch06_mutex():
    fig = Fig("ch06_mutex", "Figure 6-1. A mutex: one owner, everyone else waits.", 220)

    thread_1 = fig.node(28, 0, 200, 96, "green", ["thread 1", "lock() succeeds", "owns the mutex"], icon="person")
    thread_2 = fig.node(28, 124, 200, 96, "red", ["thread 2", "lock() blocks", "waits in the queue"], icon="hourglass_top")
    mutex = fig.node(300, 0, 200, 96, "amber", ["mutex", ("unlocked / locked", "body"), "owner + wait queue"], icon="lock")
    section = fig.node(572, 0, 200, 96, "gray", ["critical section", "runs while the owner", "holds the mutex"],
                       layout="center", kind="dashed")

    fig.wire([(thread_1.r + 3, 48), (mutex.x - 3, 48)], "green", width=2.2)
    fig.wire([(mutex.r + 3, 48), (section.x - 3, 48)], "wire", width=2.2)

    fig.wire([(thread_2.r + 3, 150), (350, 150), (350, mutex.b + 3)], "red", dash=True, width=2)
    fig.wire([(450, mutex.b + 3), (450, 196), (thread_2.r + 3, 196)], "green", width=2)

    fig.lines(464, 150, [("unlock(): owner releases;", "sub"), ("one waiter wakes and becomes owner", "sub")], "start",
              fit=(464, 776))

    fig.save([
        "Inside the critical section, the three steps load, add, and store run without interference from other threads.",
        "A mutex does not decide which waiting thread runs next. Condition variables, in Section 6.2, let a thread wait for a condition.",
    ])


@figure
def ch06_deadlock():
    fig = Fig("ch06_deadlock", "Figure 6-2. Deadlock: each worker holds one resource and waits for the other.", 250)

    worker_1 = fig.node(28, 0, 210, 96, "blue", ["worker 1", ("lock(A) → holds A", "mono"), ("lock(B) → waits …", "mono")],
                        icon="engineering")
    worker_2 = fig.node(562, 0, 210, 96, "purple", ["worker 2", ("lock(B) → holds B", "mono"), ("lock(A) → waits …", "mono")],
                        icon="engineering")

    for cx, letter in ((310, "A"), (490, "B")):
        fig.add(f'<circle cx="{cx}" cy="150" r="44" class="m-amber"/>')
        fig.icon(cx - 9, 113, "lock", "amber", 18)
        fig.lines(cx, 157, [("resource", "name"), (letter, "name")], "middle", fit=(cx - 40, cx + 40))

    fig.wire([(worker_1.cx, worker_1.b + 3), (worker_1.cx, 150), (263, 150)], "green", width=2.2)
    fig.label(worker_1.cx + 62, 144, "holds", tone="green", backed=False)

    fig.wire([(worker_2.cx, worker_2.b + 3), (worker_2.cx, 150), (537, 150)], "green", width=2.2)
    fig.label(worker_2.cx - 62, 144, "holds", tone="green", backed=False)

    fig.wire([(worker_1.r + 3, 30), (490, 30), (490, 103)], "red", dash=True, width=2)
    fig.label(364, 24, "wants B", tone="red", backed=False)

    fig.wire([(worker_2.cx + 50, worker_2.b + 3), (worker_2.cx + 50, 232), (310, 232), (310, 197)], "red", dash=True, width=2)
    fig.label(500, 226, "wants A", tone="red", backed=False)

    fig.save([
        "A deadlock needs four conditions: mutual exclusion, hold and wait, no preemption, and circular wait.",
        "Removing one condition prevents the deadlock. Listing 6-6 removes hold and wait with try_lock.",
    ])


@figure
def ch06_cas_llsc():
    fig = Fig("ch06_cas_llsc", "Figure 6-3. Compare-And-Swap Realization: x86-64 LOCK CMPXCHG vs. ARM64 LL/SC Reservation Monitor", 408)

    # Top container: x86-64 LOCK CMPXCHG (y=12..152)
    fig.node(28, 12, 744, 140, "blue", kind="tonal", r=12)
    fig.tile(42, 22, "memory", "blue", 24)
    fig.text(74, 35, "x86-64: Single-Instruction Atomic CAS (LOCK CMPXCHG)", "name", fit=(74, 760))
    fig.text(74, 50, "Micro-coded instruction locks the 64-byte cache line in MESI Modified (M) state throughout RMW", "small", fit=(74, 760))

    x_a = fig.cell(44, 66, 208, 72, "blue", [
        ("1. Load Expected", "name"),
        ("RAX = expected (5)", "mono"),
        ("RDX = desired  (6)", "mono"),
    ], kind="card", r=8)

    x_b = fig.cell(286, 66, 228, 72, "amber", [
        ("2. LOCK CMPXCHG", "name"),
        ("Compare [mem] == RAX", "mono"),
        ("Zero spurious failures", "small"),
    ], kind="card", r=8)

    x_c = fig.cell(548, 66, 208, 72, "green", [
        ("3. Commit or Reload", "name"),
        ("ZF=1 → [mem]=6 (Ok)", "mono"),
        ("ZF=0 → RAX=[mem] (Err)", "mono"),
    ], kind="card", r=8)

    fig.wire([(x_a.r + 2, 102), (x_b.x - 2, 102)], "blue", width=2.0)
    fig.wire([(x_b.r + 2, 102), (x_c.x - 2, 102)], "green", width=2.0)

    # Bottom container: ARM64 LL/SC (y=168..396)
    fig.node(28, 168, 744, 226, "purple", kind="tonal", r=12)
    fig.tile(42, 178, "swap_horiz", "purple", 24)
    fig.text(74, 191, "ARM64: Load-Linked / Store-Conditional (LDXR / STXR) and compare_exchange_weak", "name", fit=(74, 760))
    fig.text(74, 206, "Split into two instructions monitored by a hardware Exclusive Reservation Monitor on the cache line", "small", fit=(74, 760))

    a_1 = fig.cell(44, 224, 206, 78, "purple", [
        ("1. Load-Linked (LDXR)", "name"),
        ("x0 = [addr]  (reads 5)", "mono"),
        ("Sets Exclusive Monitor", "small"),
        ("on 64B/128B cache line", "small"),
    ], kind="card", r=8)

    a_2 = fig.cell(284, 224, 220, 78, "amber", [
        ("2. Reservation Window", "name"),
        ("Check x0 == expected", "mono"),
        ("IRQ or sibling write to", "small"),
        ("same line clears Monitor", "small"),
    ], kind="card", r=8)

    a_3 = fig.cell(538, 224, 218, 78, "green", [
        ("3. Store-Cond (STXR)", "name"),
        ("Monitor intact → Ok", "mono"),
        ("Monitor cleared → Err", "mono"),
        ("(Spurious fail even if 5)", "small"),
    ], kind="card", r=8)

    fig.wire([(a_1.r + 2, 263), (a_2.x - 2, 263)], "purple", width=2.0)
    fig.wire([(a_2.r + 2, 263), (a_3.x - 2, 263)], "amber", width=2.0)

    fig.cell(44, 318, 344, 62, "green", [
        ("compare_exchange_weak (Use in Loops)", "name"),
        ("Single LDXR/STXR pair; outer while-loop retries", "small"),
        ("spurious monitor clears with zero nested branch.", "small"),
    ], kind="card", r=8)

    fig.cell(412, 318, 344, 62, "red", [
        ("compare_exchange (Use One-Shot)", "name"),
        ("Compiler emits a hidden inner loop around STXR", "small"),
        ("to suppress spurious failures outside a loop.", "small"),
    ], kind="card", r=8)

    fig.save([
        "On ARM64 LL/SC hardware, compare_exchange_weak compiles to one LDXR/STXR pair; an enclosing retry loop handles spurious failures.",
        "ARMv8.1 Large System Extensions (LSE) add single-instruction CASAL, narrowing the gap under heavy multi-core contention.",
    ])


@figure
def ch06_store_buffer_litmus():
    fig = Fig("ch06_store_buffer_litmus", "Figure 6-4. Per-Core Hardware Store Buffers: Store-Buffering (SB) vs. Acquire-Release Message Passing (MP)", 424)

    # Top: Store-Buffering Litmus Test (y=12..216)
    fig.node(28, 12, 744, 202, "red", kind="tonal", r=12)
    fig.tile(42, 22, "warning", "red", 24)
    fig.text(74, 35, "Litmus 1: Store Buffering (SB) — Why Store-Load Reordering Happens Even on x86-64 TSO", "name", fit=(74, 760))

    c0 = fig.cell(44, 54, 178, 66, "blue", [
        ("Core 0 Program", "name"),
        ("1. x.store(1)", "mono"),
        ("2. r1 = y.load()", "mono"),
    ], kind="card", r=8)

    sb0 = fig.cell(44, 140, 178, 58, "amber", [
        ("Core 0 Store Buffer", "name"),
        ("x = 1  (unflushed)", "mono"),
        ("invisible to Core 1", "small"),
    ], kind="mid", r=8)

    mem = fig.cell(264, 76, 272, 122, "red", [
        ("Coherent L1/L2 Cache & DRAM", "name"),
        ("Initial state: x = 0, y = 0", "mono"),
        ("Core 0 loads y → observes 0", "small"),
        ("Core 1 loads x → observes 0", "small"),
        ("Result: r1 == 0 && r2 == 0", "monob"),
        ("Fix: SeqCst drains store buffers", "small"),
    ], kind="card", r=8)

    c1 = fig.cell(578, 54, 178, 66, "purple", [
        ("Core 1 Program", "name"),
        ("1. y.store(1)", "mono"),
        ("2. r2 = x.load()", "mono"),
    ], kind="card", r=8)

    sb1 = fig.cell(578, 140, 178, 58, "amber", [
        ("Core 1 Store Buffer", "name"),
        ("y = 1  (unflushed)", "mono"),
        ("invisible to Core 0", "small"),
    ], kind="mid", r=8)

    fig.wire([(c0.cx, c0.b + 2), (sb0.cx, sb0.y - 2)], "amber", width=2.0)
    fig.wire([(c1.cx, c1.b + 2), (sb1.cx, sb1.y - 2)], "amber", width=2.0)
    fig.wire([(c0.r + 2, 92), (mem.x - 2, 92)], "blue", width=2.0)
    fig.wire([(c1.x - 2, 92), (mem.r + 2, 92)], "purple", width=2.0)

    # Bottom: Message-Passing Litmus Test (y=230..410)
    fig.node(28, 230, 744, 180, "blue", kind="tonal", r=12)
    fig.tile(42, 240, "bolt", "blue", 24)
    fig.text(74, 253, "Litmus 2: Message Passing (MP) — Acquire-Release Happens-Before Edge", "name", fit=(74, 760))

    mp_p = fig.cell(44, 274, 236, 120, "blue", [
        ("Producer (Core 0)", "name"),
        ("1. payload = 0xCAFE;", "mono"),
        ("── Release Barrier ──", "small"),
        ("2. ready.store(1, Release)", "monob"),
        ("Prior stores cannot float down", "small"),
    ], kind="card", r=8)

    mp_e = fig.cell(310, 294, 180, 80, "teal", [
        ("Happens-Before", "name"),
        ("Synchronizes-With", "small"),
        ("STLR → LDAR (ARM64)", "mono"),
    ], kind="mid", r=8)

    mp_c = fig.cell(520, 274, 236, 120, "green", [
        ("Consumer (Core 1)", "name"),
        ("1. ready.load(Acquire) == 1", "monob"),
        ("── Acquire Barrier ──", "small"),
        ("2. assert(payload == 0xCAFE)", "mono"),
        ("Later reads cannot float up", "small"),
    ], kind="card", r=8)

    fig.wire([(mp_p.r + 2, 334), (mp_e.x - 2, 334)], "blue", width=2.2)
    fig.wire([(mp_e.r + 2, 334), (mp_c.x - 2, 334)], "teal", width=2.2)

    fig.save([
        "In Store Buffering, neither Release nor Acquire prevents a later load from bypassing an earlier store; only SeqCst drains the buffer.",
        "In Message Passing, Relaxed accidentally passes on x86-64 TSO but breaks on weakly ordered ARM64 without Release/Acquire.",
    ])


@figure
def ch06_futex_automaton():
    fig = Fig("ch06_futex_automaton", "Figure 6-6. Fast Userspace Mutex (futex / __ulock): Ring 3 Fast Path vs. Ring 0 Wait-Queue Parking", 364)

    # Ring 3 User Mode band (y=12..196)
    fig.node(28, 12, 744, 184, "blue", kind="tonal", r=12)
    fig.tile(42, 22, "lock", "blue", 24)
    fig.text(74, 35, "Ring 3 (User Mode): Single 32-Bit Atomic Word — Zero System Calls When Uncontended", "name", fit=(74, 760))

    s0 = fig.cell(44, 58, 212, 120, "green", [
        ("State 0: UNLOCKED", "name"),
        ("atomic_word == 0", "mono"),
        ("Fast lock (~5 ns):", "small"),
        ("CAS(0 → 1, Acquire)", "mono"),
        ("Zero kernel traps", "small"),
    ], kind="card", r=8)

    s1 = fig.cell(294, 58, 212, 120, "blue", [
        ("State 1: LOCKED", "name"),
        ("atomic_word == 1", "mono"),
        ("No sleeping waiters", "small"),
        ("Fast unlock (~5 ns):", "small"),
        ("swap(0, Release) == 1", "mono"),
    ], kind="card", r=8)

    s2 = fig.cell(544, 58, 212, 120, "amber", [
        ("State 2: CONTENDED", "name"),
        ("atomic_word == 2", "mono"),
        ("Contender executes:", "small"),
        ("swap(2, Acquire)", "mono"),
        ("→ traps to Ring 0", "small"),
    ], kind="card", r=8)

    fig.wire([(s0.r + 2, 102), (s1.x - 2, 102)], "green", width=2.2)
    fig.wire([(s1.x - 2, 134), (s0.r + 2, 134)], "blue", dash=True, width=2.0)
    fig.wire([(s1.r + 2, 118), (s2.x - 2, 118)], "amber", width=2.2)

    # Privilege boundary rule
    fig.rule(28, 214, 772, 214, "gray", width=1.8, dash="4 4")
    fig.label(400, 218, "Ring 3 / Ring 0 Syscall Boundary (Only Crossed Under Contention)", backed=True)

    # Ring 0 Kernel band (y=234..352)
    fig.node(28, 234, 744, 118, "teal", kind="tonal", r=12)
    fig.tile(42, 244, "shield", "teal", 24)
    fig.text(74, 257, "Ring 0 (Kernel Mode): Futex Hash-Bucket Wait Queue", "name", fit=(74, 620))

    k_wake = fig.cell(44, 276, 336, 62, "green", [
        ("futex(&state, FUTEX_WAKE, 1)", "monob"),
        ("Invoked only when unlock's swap(0) returns 2;", "small"),
        ("moves one sleeping TCB back to core runqueue.", "small"),
    ], kind="card", r=8)

    k_wait = fig.cell(420, 276, 336, 62, "amber", [
        ("futex(&state, FUTEX_WAIT, 2)", "monob"),
        ("Acquires bucket spinlock, verifies *(&state) == 2,", "small"),
        ("parks TCB on wait queue (or returns EAGAIN if 0).", "small"),
    ], kind="card", r=8)

    fig.wire([(650, s2.b + 2), (650, k_wait.y - 2)], "amber", width=2.2)

    fig.save([
        "Over 95% of lock acquisitions in well-tuned systems succeed on the 0 → 1 Ring 3 fast path without a single system call.",
        "Kernel re-verification of *(&state) == 2 inside FUTEX_WAIT eliminates the lost-wakeup race between Ring 3 and Ring 0.",
    ])


@figure
def ch06_seqlock():
    fig = Fig("ch06_seqlock", "Figure 6-7. Lock-Free Sequence Lock (Seqlock): Zero-Write Reader Scaling and Torn-Read Retry", 358)

    # Top lane: Writer (y=12..118)
    fig.node(28, 12, 744, 102, "purple", kind="tonal", r=12)
    fig.text(44, 34, "Writer (Single)", "name", tone="purple")
    fig.text(44, 50, "Mutates seq", "small")

    w1 = fig.cell(168, 28, 168, 70, "amber", [
        ("1. Begin Write", "name"),
        ("seq: 4 → 5 (ODD)", "monob"),
        ("store(Release)", "small"),
    ], kind="card", r=8)

    w2 = fig.cell(372, 28, 186, 70, "purple", [
        ("2. Update Payload", "name"),
        ("ticks = 1001", "mono"),
        ("scaled_ns = 10010", "mono"),
    ], kind="card", r=8)

    w3 = fig.cell(594, 28, 162, 70, "green", [
        ("3. Publish Snapshot", "name"),
        ("seq: 5 → 6 (EVEN)", "monob"),
        ("store(Release)", "small"),
    ], kind="card", r=8)

    fig.wire([(w1.r + 2, 63), (w2.x - 2, 63)], "amber", width=2.0)
    fig.wire([(w2.r + 2, 63), (w3.x - 2, 63)], "green", width=2.0)

    # Middle lane: Overlapping Reader B (retries cleanly) (y=130..236)
    fig.node(28, 130, 744, 102, "red", kind="tonal", r=12)
    fig.text(44, 152, "Reader B", "name", tone="red")
    fig.text(44, 168, "Overlaps writer", "small")

    rb1 = fig.cell(168, 146, 168, 70, "blue", [
        ("1. Sample s1 = 4", "name"),
        ("s1 is EVEN (Acquire)", "mono"),
        ("Proceeds to copy", "small"),
    ], kind="card", r=8)

    rb2 = fig.cell(372, 146, 186, 70, "red", [
        ("2. Torn Payload Read", "name"),
        ("Sees mixed old/new", "small"),
        ("Acquire fence()", "mono"),
    ], kind="card", r=8)

    rb3 = fig.cell(594, 146, 162, 70, "red", [
        ("3. Verify s2 = 6", "name"),
        ("s1 (4) ≠ s2 (6)", "monob"),
        ("Discard & retry loop", "small"),
    ], kind="mid", r=8)

    fig.wire([(rb1.r + 2, 181), (rb2.x - 2, 181)], "red", width=2.0)
    fig.wire([(rb2.r + 2, 181), (rb3.x - 2, 181)], "red", width=2.0)

    # Bottom lane: Clean Reader A (zero shared writes) (y=248..348)
    fig.node(28, 248, 744, 96, "green", kind="tonal", r=12)
    fig.text(44, 270, "Reader A", "name", tone="green")
    fig.text(44, 286, "Clean window", "small")

    ra1 = fig.cell(168, 262, 168, 68, "green", [
        ("1. Sample s1 = 6", "name"),
        ("s1 is EVEN (Acquire)", "mono"),
    ], kind="card", r=8)

    ra2 = fig.cell(372, 262, 186, 68, "green", [
        ("2. Read Payload", "name"),
        ("1001, 10010 (Shared S)", "mono"),
    ], kind="card", r=8)

    ra3 = fig.cell(594, 262, 162, 68, "green", [
        ("3. Verify s2 = 6", "name"),
        ("s1 == s2 → Valid", "monob"),
    ], kind="mid", r=8)

    fig.wire([(ra1.r + 2, 296), (ra2.x - 2, 296)], "green", width=2.0)
    fig.wire([(ra2.r + 2, 296), (ra3.x - 2, 296)], "green", width=2.0)

    fig.save([
        "Readers never modify shared memory: dozens of cores hold the Seqlock cache line in MESI Shared (S) state simultaneously.",
        "Linux vDSO clock_gettime() relies on a Seqlock in the read-only vvar page so user processes read system time without trapping.",
    ])


# ---------------------------------------------------------------- Chapter 7

@figure
def ch07_vm_paging():
    fig = Fig("ch07_vm_paging", "Figure 7-1. Each process sees a private, contiguous space; pages land anywhere in RAM.", 356)

    tones = ["blue", "purple", "teal", "amber", "green"]
    frame_of = [3, 7, 1, 5, 0]

    fig.node(28, 0, 230, 328, "blue")
    fig.lines(143, 30, [("virtual address space", "name"), ("process A", "sub")], "middle", fit=(34, 252))
    page_y = [62 + index * 43 for index in range(6)]
    for index in range(5):
        fig.cell(44, page_y[index], 198, 35, tones[index], [(f"page {index}", "body")], kind="mid")
    unused = fig.node(44, page_y[5], 198, 35, "gray", kind="dashed", r=7)
    fig.text(unused.cx, unused.cy + 4.5, "page 5 (not yet used)", "sub", "middle", fit=(unused.x + 4, unused.r - 4))

    table = fig.node(318, 8, 170, 312, "gray", kind="card")
    fig.tile(332, 18, "table_rows", "gray", 26, "c-gray")
    fig.text(366, 37, "page table", "name")
    for index in range(5):
        fig.cell(328, page_y[index], 150, 35, tones[index], [(f"page {index} → frame {frame_of[index]}", "mono")],
                 kind="tonal")
    fig.cell(328, page_y[5], 150, 35, "red", [("page 5 → invalid", "mono")], kind="tonal", text_tone="red")

    fig.node(572, 0, 200, 328, "green")
    fig.lines(672, 30, [("physical memory", "name"), ("frames, any order", "sub")], "middle", fit=(578, 766))
    frame_y = [60 + index * 33 for index in range(8)]
    owner = {frame: page for page, frame in enumerate(frame_of)}
    other = {2: "frame 2 (other process)", 4: "frame 4 (other process)", 6: "frame 6 (free)"}
    for frame in range(8):
        if frame in other:
            fig.cell(588, frame_y[frame], 168, 28, "gray", [(other[frame], "small")], kind="card")
            continue
        page = owner[frame]
        fig.cell(588, frame_y[frame], 168, 28, tones[page], [(f"frame {frame} ← page {page}", "body")], kind="mid")

    for index in range(5):
        cy = page_y[index] + 17.5
        fig.wire([(244, cy), (326, cy)], tones[index], width=1.8)
        fig.wire([(480, cy), (586, frame_y[frame_of[index]] + 14)], tones[index], width=1.8)

    fault_y = page_y[5] + 17.5
    fig.wire([(244, fault_y), (326, fault_y)], "red", dash=True, width=1.8)
    fig.icon(331, 337, "warning", "red", 17)
    fig.text(354, 351, "access page 5 → fault", "sub", tone="red")

    fig.save([
        "A process uses consecutive virtual addresses, and the Memory Management Unit finds the frame for each one in the page table.",
        "The kernel allocates a frame for a page only when the program first accesses that page.",
    ])


@figure
def ch07_mmu_architecture():
    fig = Fig("ch07_mmu_architecture", "Figure 7-2. Virtual-to-physical address translation: the VPN maps to a PFN while the page-offset bits pass through unmodified.", 378)

    def bit_strip(x, y, h, cells, tone):
        """Draws a contiguous register strip of | cell | cell | ... | boxes."""
        total_w = sum(w for _, w in cells)
        fig.rect(x, y, total_w, h, f"m-{tone}", r=7)
        cx = x
        for idx, (label, w) in enumerate(cells):
            if idx > 0:
                fig.rule(cx, y + 3, cx, y + h - 3, tone, width=1.1)
            cls = "monob" if "·" not in label else "sub"
            fig.text(cx + w / 2, y + h / 2 + 4.5, label, cls, "middle", fit=(cx - 2, cx + w + 2))
            cx += w
        return (x + total_w / 2, y + h)

    # Top: Virtual Address bit-cell strip with group renaming brackets above
    fig.lines(122, 62, [("Virtual", "name"), ("Address", "name")], "end", fit=(24, 126))

    # Top group brackets
    fig.rule(136, 30, 480, 30, "blue", width=1.4)
    fig.rule(136, 30, 136, 36, "blue", width=1.4)
    fig.rule(480, 30, 480, 36, "blue", width=1.4)
    fig.label(308, 22, "Virtual Page Number (VPN) · 36 bits", tone="blue", cls="small")

    fig.rule(488, 30, 668, 30, "green", width=1.4)
    fig.rule(488, 30, 488, 36, "green", width=1.4)
    fig.rule(668, 30, 668, 36, "green", width=1.4)
    fig.label(578, 22, "Page Offset · 12 bits", tone="green", cls="small")

    vpn_cells = [("b47", 44), ("b46", 44), ("b45", 44), ("· · ·", 80), ("b14", 44), ("b13", 44), ("b12", 44)]
    off_cells = [("b11", 34), ("b10", 34), ("· · ·", 44), ("b1", 34), ("b0", 34)]
    _, vpn_b = bit_strip(136, 42, 40, vpn_cells, "blue")
    off_cx, off_b = bit_strip(488, 42, 40, off_cells, "green")

    # Middle: TLB (fast path) and Page Table Walk (miss path)
    tlb_box = fig.node(136, 130, 160, 88, "purple", [
        ("TLB Cache", "name"),
        ("VPN → PFN", "monob"),
        ("~1 cycle hit", "small"),
    ], layout="center", kind="card", r=10)

    pt_box = fig.node(320, 130, 160, 88, "amber", [
        ("Page Table (CR3)", "name"),
        ("4-level radix walk", "sub"),
        ("checks P, R/W, U/S, NX", "small"),
    ], layout="center", kind="card", r=10)

    # Wires: VPN -> TLB -> (miss) -> Page Table -> PFN
    fig.wire([(tlb_box.cx, vpn_b + 2), (tlb_box.cx, tlb_box.y - 2)], "blue", width=2.0)
    fig.wire([(tlb_box.r + 2, tlb_box.cy), (pt_box.x - 2, pt_box.cy)], "amber", dash=True, width=1.8)
    fig.text((tlb_box.r + pt_box.x) / 2, tlb_box.cy - 10, "miss", "small", "middle", tone="amber")

    fig.wire([(tlb_box.cx, tlb_box.b + 2), (tlb_box.cx, 240), (308, 240), (308, 266)], "teal", width=2.0)
    fig.wire([(pt_box.cx, pt_box.b + 2), (pt_box.cx, 240), (308, 240)], "teal", head=False, width=2.0)
    fig.label(216, 234, "hit", tone="teal", cls="small")

    # Straight pass-through for Page Offset bits b11..b0
    fig.wire([(off_cx, off_b + 2), (off_cx, 266)], "green", width=2.2)
    fig.label(off_cx, 174, "copied bit-for-bit (2^12 B = 4 KiB)", tone="green", cls="small")

    # Bottom: Physical Address bit-cell strip with group renaming brackets below
    fig.lines(122, 288, [("Physical", "name"), ("Address", "name")], "end", fit=(24, 126))
    pfn_cells = [("p51", 44), ("p50", 44), ("p49", 44), ("· · ·", 80), ("p14", 44), ("p13", 44), ("p12", 44)]
    bit_strip(136, 268, 40, pfn_cells, "teal")
    bit_strip(488, 268, 40, off_cells, "green")

    fig.rule(136, 320, 480, 320, "teal", width=1.4)
    fig.rule(136, 314, 136, 320, "teal", width=1.4)
    fig.rule(480, 314, 480, 320, "teal", width=1.4)
    fig.label(308, 336, "Physical Frame Number (PFN) · 40 bits", tone="teal", cls="small")

    fig.rule(488, 320, 668, 320, "green", width=1.4)
    fig.rule(488, 314, 488, 320, "green", width=1.4)
    fig.rule(668, 314, 668, 320, "green", width=1.4)
    fig.label(578, 336, "Page Offset · 12 bits", tone="green", cls="small")

    fig.text(402, 366, "PA = (PFN << 12) | Offset", "monob", "middle", tone="teal")

    fig.save([
        "Bits b11..b0 pass straight from the Virtual Address into the Physical Address unchanged because pages and frames share an identical 4 KiB (2^12-byte) alignment.",
        "Only bits b47..b12 (VPN) are translated through the Translation Lookaside Buffer (TLB) or page table rooted at Control Register 3 (CR3) to produce p51..p12 (PFN).",
    ])


@figure
def ch07_pagewalk():
    fig = Fig("ch07_pagewalk", "Figure 7-3. Four-level hierarchical radix page-table walk (x86-64, 4 KiB pages).", 300)

    fig.text(28, 12, "48-bit canonical virtual address (bits 47:0)", "sub")

    fields = [
        (28, 112, "gray", "bits 63:48"),
        (142, 124, "blue", "PML4 (9)"),
        (268, 124, "purple", "PDPT (9)"),
        (394, 124, "teal", "PD (9)"),
        (520, 124, "amber", "PT (9)"),
        (646, 126, "green", "Offset (12)"),
    ]
    centers = []
    for x, width, tone, text in fields:
        box = fig.cell(x, 22, width, 44, tone, [(text, "body")], kind="mid", r=8)
        centers.append(box.cx)

    table_tones = ["blue", "purple", "teal", "amber"]
    table_names = ["L4 PML4", "L3 PDPT", "L2 PD", "L1 PT"]
    entry_y = 176
    tables = []
    for name, tone in zip(table_names, table_tones):
        cx = centers[1 + len(tables)]
        table = fig.node(cx - 40, 108, 80, 150, tone, r=10)
        fig.text(cx, 127, name, "small", "middle", fit=(cx - 38, cx + 38))
        for row in range(5):
            y = 138 + row * 23
            fig.rect(cx - 30, y, 60, 18, "card" if row != 1 else f"a-{tone}", r=4)
        fig.wire([(cx, 68), (cx, 106)], tone, width=1.8)
        tables.append(table)

    frame_cx = centers[5]
    frame = fig.node(frame_cx - 52, 108, 104, 150, "green", r=10)
    fig.lines(frame_cx, 136, [("Page Frame", "name"), ("4 KiB", "sub")], "middle", fit=(frame.x + 3, frame.r - 3))
    fig.rect(frame_cx - 38, 164, 76, 78, "card", r=6)
    fig.rect(frame_cx - 9, 198, 18, 12, "a-green", r=3)
    fig.wire([(frame_cx, 68), (frame_cx, 106)], "green", width=1.8)

    targets = tables[1:] + [frame]
    for table, target, tone in zip(tables, targets, table_tones):
        fig.wire([(table.cx + 30, entry_y + 0.5), (target.x - 2, entry_y + 0.5)], tone, width=1.8)

    fig.node(28, 142, 118, 70, "gray", [("CR3 Register", "name"), ("physical base", "small"), ("of L4 PML4", "small")],
             layout="center", kind="card", r=10)
    fig.wire([(148, 177), (tables[0].x - 2, 177)], "wire", width=1.8)

    fig.lines(772, 282, [("offset selects the byte", "sub"), ("inside the 4 KiB frame", "sub")], "end", fit=(580, 776))

    fig.save([
        "A TLB miss requires four sequential 8-byte memory reads across the radix hierarchy before the target byte is accessed.",
        "Section 7.2.4 quantifies how access latency rises once the working set exceeds TLB reach.",
    ])


@figure
def ch07_canonical_va():
    fig = Fig("ch07_canonical_va", "Figure 7-4. Bit-level 9-9-9-9-12 decomposition of 0x0000_7FFF_ABCD_EF01 and canonical 64-bit address space.", 392)

    # Panel 1: Exact | | | | bit cells for VA = 0x0000_7FFF_ABCD_EF01
    fig.heading(28, 16, "1. bit-level slicing of VA = 0x0000_7FFF_ABCD_EF01 (bits 63..0)")

    # Sign-ext bits [63:48] compressed as | 0 | 0 | ·· | 0 | (width 68 at x=28..96)
    sign_cells = [("0", 15), ("0", 15), ("··", 23), ("0", 15)]
    sx = 28
    fig.text(sx + 2, 42, "63", "small", "start")
    fig.text(sx + 66, 42, "48", "small", "end")
    fig.rect(sx, 48, 68, 34, "m-gray", r=5)
    cx = sx
    for idx, (lbl, w) in enumerate(sign_cells):
        if idx > 0:
            fig.rule(cx, 50, cx, 80, "gray", width=1.0)
        fig.text(cx + w / 2, 69, lbl, "mono" if lbl != "··" else "small", "middle", fit=(cx - 2, cx + w + 2))
        cx += w

    # Group bracket & renamed label under Sign Ext
    fig.rule(28, 92, 96, 92, "gray", width=1.3)
    fig.rule(28, 86, 28, 92, "gray", width=1.3)
    fig.rule(96, 86, 96, 92, "gray", width=1.3)
    fig.cell(28, 100, 68, 56, "gray", [
        ("Sign Ext", "small"),
        ("16 bits", "small"),
        ("0x0000", "monob"),
    ], kind="card", r=6)

    # Active 48 bits [47:0] = 0x7FFF_ABCD_EF01 in binary, grouped into 9-9-9-9-12
    # 7    F    F    F    A    B    C    D    E    F    0    1
    # 0111 1111 1111 1111 1010 1011 1100 1101 1110 1111 0000 0001
    groups = [
        ("PML4 (L4)", "blue",   "47", "39", "011111111", "0x0FF (255)"),
        ("PDPT (L3)", "purple", "38", "30", "111111110", "0x1FE (510)"),
        ("PD (L2)",   "teal",   "29", "21", "101011110", "0x15E (350)"),
        ("PT (L1)",   "amber",  "20", "12", "011011111", "0x0DF (223)"),
        ("Offset",    "green",  "11", "0",  "111100000001", "0xF01 (3,841)"),
    ]
    bw = 13.5
    gap = 6.0
    gx = 100.0
    for name, tone, hi, lo, bits_str, val_str in groups:
        gw = len(bits_str) * bw
        fig.text(gx + 1, 42, hi, "small", "start")
        fig.text(gx + gw - 1, 42, lo, "small", "end")
        fig.rect(gx, 48, gw, 34, f"m-{tone}", r=5)
        for i, ch in enumerate(bits_str):
            bx = gx + i * bw
            if i > 0:
                fig.rule(bx, 50, bx, 80, tone, width=0.9)
            fig.text(bx + bw / 2, 69, ch, "mono", "middle", fit=(bx - 2, bx + bw + 2))
        # Group-renaming bracket and card below
        fig.rule(gx, 92, gx + gw, 92, tone, width=1.4)
        fig.rule(gx, 86, gx, 92, tone, width=1.4)
        fig.rule(gx + gw, 86, gx + gw, 92, tone, width=1.4)
        fig.cell(gx, 100, gw, 56, tone, [
            (f"{name} ({len(bits_str)}b)", "small"),
            (val_str, "monob"),
        ], kind="card", r=6)
        gx += gw + gap

    # Span annotation for 36-bit VPN vs 12-bit Offset
    fig.rule(100, 174, 604, 174, "blue", width=1.4)
    fig.rule(100, 168, 100, 174, "blue", width=1.4)
    fig.rule(604, 168, 604, 174, "blue", width=1.4)
    fig.label(352, 178, "36-bit Virtual Page Number (VPN = 0x7FFF_ABCDE)", tone="blue", cls="small")

    fig.rule(610, 174, 772, 174, "green", width=1.4)
    fig.rule(610, 168, 610, 174, "green", width=1.4)
    fig.rule(772, 168, 772, 174, "green", width=1.4)
    fig.label(691, 178, "12-bit Offset (F01)", tone="green", cls="small")

    # Panel 2: Canonical Address Space Map
    fig.heading(28, 224, "2. 64-bit canonical address space (bits 63:48 replicate bit 47)")

    fig.cell(28, 240, 260, 88, "blue", [
        ("User Canonical Space (128 TiB)", "name"),
        ("0x0000_0000_0000_0000", "mono"),
        ("to 0x0000_7FFF_FFFF_FFFF", "mono"),
        ("bit 47 = 0 · bits 63:48 = 0x0000", "small"),
    ], kind="tonal", r=10)

    fig.hatch(296, 240, 208, 88, "red", r=10)
    fig.cell(316, 258, 168, 52, "red", [
        ("Non-Canonical Hole", "name"),
        ("raises #GP(0) fault", "small"),
    ], kind="card", r=8, text_tone="red")

    fig.cell(512, 240, 260, 88, "purple", [
        ("Kernel Canonical Space (128 TiB)", "name"),
        ("0xFFFF_8000_0000_0000", "mono"),
        ("to 0xFFFF_FFFF_FFFF_FFFF", "mono"),
        ("bit 47 = 1 · bits 63:48 = 0xFFFF", "small"),
    ], kind="tonal", r=10)

    fig.text(400, 358, "4,096 B table frame ÷ 8 B/PTE = 512 entries (2^9 → 9-bit index per level); 4,096 B page = 2^12 → 12-bit offset", "sub", "middle")

    fig.save([
        "Every active bit of 0x0000_7FFF_ABCD_EF01 is drawn in its own cell: the 12-bit offset aligns cleanly with the last three hex digits (F01), while 9-bit indices straddle 4-bit hex nibbles.",
        "Bits 63:48 must copy bit 47 (0x0000 for user space, 0xFFFF for kernel space); any non-canonical pointer triggers a General Protection Fault (#GP) before a page walk.",
    ])


@figure
def ch07_radix_walk_trace():
    fig = Fig("ch07_radix_walk_trace", "Figure 7-5. Four-level hardware page walk for 0x0000_7FFF_ABCD_EF01 and complete 64-bit x86-64 leaf PTE bit layout.", 382)

    # Panel 1: 4-hop walk + Physical Address composition
    fig.heading(28, 16, "1. four-level physical memory walk (CR3 = 0x1000_0000; Entry PA = Base + Index × 8)")

    hops = [
        (28,  "blue",   "L4: PML4", "0x1000_0000", "+ 255 × 8", "→ 0x2040_0000"),
        (178, "purple", "L3: PDPT", "0x2040_0000", "+ 510 × 8", "→ 0x3080_0000"),
        (328, "teal",   "L2: PD",   "0x3080_0000", "+ 350 × 8", "→ 0x40C0_0000"),
        (478, "amber",  "L1: PT",   "0x40C0_0000", "+ 223 × 8", "→ PFN 0x8A420"),
    ]
    boxes = []
    for x, tone, title, base, idx, out in hops:
        b = fig.node(x, 34, 136, 114, tone, [
            (title, "name"),
            (base, "mono"),
            (idx, "mono"),
            (out, "monob"),
        ], layout="center", kind="card", r=10)
        boxes.append(b)

    final_pa = fig.node(628, 34, 144, 114, "green", [
        ("Physical Addr", "name"),
        ("0x8A42_0000", "mono"),
        ("| offset 0xF01", "mono"),
        ("= 0x8A42_0F01", "monob"),
    ], layout="center", kind="mid", r=10)

    for left_b, right_b, tone in zip(boxes, boxes[1:] + [final_pa], ["blue", "purple", "teal", "amber"]):
        fig.wire([(left_b.r + 2, left_b.cy), (right_b.x - 2, right_b.cy)], tone, width=2.0)

    # Panel 2: Complete 64-bit Leaf PTE Register Bit-Field Layout with | | | | bit cells & ·· ellipsis
    fig.heading(28, 184, "2. complete 64-bit x86-64 leaf PTE bit layout (PTE = 0x8000_0000_8A42_0067)")

    # Each entry: (width, tone, kind, bits_hdr, subcells_list, group_label)
    pte_fields = [
        (40,  "red",    "mid",   "63",    ["1"],                           "NX"),
        (74,  "gray",   "tonal", "62:52", ["0", "··", "0"],                "Ign / PK"),
        (228, "green",  "mid",   "51:12", ["0", "··", "0x000_8A420", "··", "0"], "Physical Frame Number (40b)"),
        (56,  "gray",   "tonal", "11:9",  ["0", "0", "0"],                 "AVL"),
        (34,  "teal",   "tonal", "8",     ["0"],                           "G"),
        (40,  "amber",  "tonal", "7",     ["0"],                           "PAT"),
        (36,  "purple", "mid",   "6",     ["1"],                           "D"),
        (36,  "purple", "mid",   "5",     ["1"],                           "A"),
        (58,  "gray",   "tonal", "4:3",   ["0", "0"],                      "PCD/WT"),
        (42,  "blue",   "mid",   "2",     ["1"],                           "U/S"),
        (42,  "blue",   "mid",   "1",     ["1"],                           "R/W"),
        (36,  "teal",   "mid",   "0",     ["1"],                           "P"),
    ]
    # Check sum: 40+74+228+56+34+40+36+36+58+42+42+36 + 11*2 = 722 + 22 = 744!
    cx = 28
    for w, tone, kind, bits_hdr, subcells, grp_lbl in pte_fields:
        fig.text(cx + w / 2, 214, bits_hdr, "small", "middle", fit=(cx - 2, cx + w + 2))
        fill_cls = f"m-{tone}" if kind == "mid" else f"c-{tone}"
        fig.rect(cx, 222, w, 36, fill_cls, r=5)
        # Allocate subcell widths proportionally (wider for 0x000_8A420)
        if len(subcells) == 5:
            sws = [22, 26, 132, 26, 22]
        elif len(subcells) == 3 and "··" in subcells:
            sws = [22, 30, 22]
        else:
            sws = [w / len(subcells)] * len(subcells)
        scx = cx
        for idx, (slbl, sw) in enumerate(zip(subcells, sws)):
            if idx > 0:
                fig.rule(scx, 225, scx, 255, tone, width=0.9)
            scls = "monob" if slbl != "··" else "small"
            fig.text(scx + sw / 2, 244, slbl, scls, "middle", fit=(scx - 2, scx + sw + 2))
            scx += sw
        # Group bracket + name below
        fig.rule(cx, 268, cx + w, 268, tone, width=1.2)
        fig.rule(cx, 263, cx, 268, tone, width=1.2)
        fig.rule(cx + w, 263, cx + w, 268, tone, width=1.2)
        fig.text(cx + w / 2, 285, grp_lbl, "small", "middle", tone=tone if kind == "mid" else None, fit=(cx - 4, cx + w + 4))
        cx += w + 2

    fig.text(400, 324, "Low 12 bits = 0x067 (P=1, R/W=1, U/S=1, A=1, D=1)  ·  Bit 63 = 1 (NX)  ·  Frame Base = PTE & 0x000F_FFFF_FFFF_F000", "sub", "middle")
    fig.text(400, 348, "Every 4 KiB-aligned table base ends in 0x000, so bits [11:0] store flags while Index × 8 fits directly into those low three hex digits.", "small", "middle")

    fig.save([
        "All 64 bits of the leaf Page Table Entry (PTE) are shown: bits 51:12 store the 40-bit Physical Frame Number (0x8A420), bits 11:0 encode permissions and activity flags, and bit 63 enforces No-Execute.",
        "Concatenating the masked frame base (0x8A42_0000) with the unmodified 12-bit offset (0xF01) yields physical address 0x0000_0000_8A42_0F01.",
    ])


@figure
def ch07_tlb_reach():
    fig = Fig("ch07_tlb_reach", "Figure 7-6. Measured memory access latency versus working-set size (Listing 7-5) and huge-page TLB reach.", 396)

    # Panel 1: Quantitative Horizontal Bar Chart from code/out/ch07_tlb.out
    fig.heading(28, 16, "1. measured latency per page-strided access (Listing 7-5, 4 KiB pages)")

    rows = [
        ("1 page (4 KiB)",        1.7,  "green", "L1 dTLB hit"),
        ("16 pages (64 KiB)",     1.7,  "green", None),
        ("64 pages (256 KiB)",    1.8,  "green", None),
        ("256 pages (1 MiB)",     2.5,  "blue",  "L2 STLB hit"),
        ("1,024 pages (4 MiB)",   4.7,  "blue",  None),
        ("4,096 pages (16 MiB)",  8.9,  "amber", "Page walk (L1/L2 cache)"),
        ("16,384 pages (64 MiB)", 10.6, "amber", None),
        ("65,536 pages (256 MiB)",13.4, "red",   "Page walk (DRAM miss)"),
    ]
    x0 = 204
    plot_w = 356
    max_ns = 15.0

    # Grid lines at 0, 5, 10, 15 ns
    for tick in (0, 5, 10, 15):
        gx = x0 + (tick / max_ns) * plot_w
        fig.rule(gx, 32, gx, 240, "gray", width=1.0, dash="3 3" if tick > 0 else None)
        fig.text(gx, 255, f"{tick} ns", "small", "middle")

    for i, (label, ns, tone, regime) in enumerate(rows):
        y = 36 + i * 25
        fig.text(x0 - 10, y + 13, label, "small", "end", fit=(24, x0 - 6))
        bw = (ns / max_ns) * plot_w
        fig.rect(x0, y, bw, 18, f"a-{tone}", r=4)
        fig.text(x0 + bw + 8, y + 13, f"{ns:.1f} ns", "monob", "start", tone=tone)
        if regime:
            fig.text(770, y + 13, regime, "small", "end", tone=tone, fit=(600, 774))

    # Panel 2: 4 KiB vs 2 MiB Huge Pages
    fig.heading(28, 286, "2. expanding TLB reach with 2 MiB huge pages (PDE.PS = 1)")

    fig.node(28, 302, 358, 84, "amber", [
        ("4 KiB pages (4-level walk)", "name"),
        ("PML4 → PDPT → PD → PT (12-bit offset)", "small"),
        ("1,536 × 4 KiB = 6 MiB reach", "monob"),
    ], icon="table_rows", kind="tonal", r=12, icon_size=30)

    fig.node(414, 302, 358, 84, "green", [
        ("2 MiB huge pages (3-level walk)", "name"),
        ("PML4 → PDPT → PD (21-bit offset, skips PT)", "small"),
        ("1,536 × 2 MiB = 3 GiB reach (512×)", "monob"),
    ], icon="bolt", kind="tonal", r=12, icon_size=30)

    fig.save([
        "Access latency remains flat (~1.7 ns) within L1 dTLB reach, climbs through L2 STLB capacity, and jumps above 8.9 ns once 4-level walks dominate.",
        "Setting PDE.PS = 1 maps 2 MiB huge pages, eliminating the L1 PT lookup and increasing L2 STLB coverage by 512× (from 6 MiB to 3 GiB).",
    ])


@figure
def ch07_page_fault_handling():
    fig = Fig("ch07_page_fault_handling", "Figure 7-7. Page-fault exception path and kernel VMA resolution dispositions.", 336)

    # Top: Hardware Fault Trigger
    trigger = fig.node(28, 12, 744, 78, "red", [
        ("MMU Exception (#PF): PTE.Present == 0 or Permission Violation (R/W, U/S, NX)", "name"),
        ("Hardware latches faulting VA in CR2 (FAR_EL1 on ARM64), pushes error code, and traps to kernel", "sub"),
    ], icon="warning", kind="tonal", r=12, icon_size=34)

    vma_check = fig.node(160, 116, 480, 56, "blue", [
        ("Kernel VMA Tree Lookup (current->mm)", "name"),
        ("classify faulting VA against registered vm_area_struct intervals", "sub"),
    ], icon="table_rows", kind="card", r=10, icon_size=28)

    fig.wire([(trigger.cx, trigger.b + 2), (vma_check.cx, vma_check.y - 2)], "red", width=2.2)

    # Bottom: Four Formal Kernel Dispositions
    outcomes = [
        (28,  "green",  "1. Zero-Fill",         "valid anonymous VMA",   "allocate & zero 4 KiB", "P = 1, retry"),
        (218, "blue",   "2. Demand Paging",     "valid file-backed VMA", "read page from disk",   "P = 1, retry"),
        (408, "purple", "3. Copy-on-Write",     "shared VMA, R/W = 0",   "copy to private frame", "R/W = 1, retry"),
        (598, "red",    "4. Protection Fault",  "unmapped or PROT_NONE", "illegal access / guard","SIGSEGV / SIGBUS"),
    ]
    for x, tone, title, l1, l2, l3 in outcomes:
        box = fig.cell(x, 206, 174, 112, tone, [
            (title, "name"),
            (l1, "small"),
            (l2, "small"),
            (l3, "monob"),
        ], kind="tonal" if tone != "red" else "mid", r=10)
        fig.wire([(vma_check.cx, vma_check.b + 2), (vma_check.cx, 188), (box.cx, 188), (box.cx, box.y - 2)], tone, width=1.8)

    fig.save([
        "Dispositions 1 through 3 resolve faults transparently by attaching or duplicating a physical frame and restarting the faulting instruction.",
        "Disposition 4 occurs on unmapped addresses, permission violations, or PROT_NONE guard pages, terminating the process via SIGSEGV (Linux) or SIGBUS (macOS).",
    ])


# ---------------------------------------------------------------- Chapter 8

@figure
def ch08_gen_arena():
    fig = Fig(
        "ch08_gen_arena",
        "Figure 8-1. Generational Arena with Intrusive Free List: Stale-Handle Rejection vs. LinkedList and Linux Intrusive Lists.",
        408,
    )

    # Top panel: Contiguous Vec<Slot<T>> + Intrusive Free List
    top = fig.node(20, 18, 760, 224, "blue")
    fig.tile(32, 30, "layers", "blue", 30)
    fig.text(70, 50, "Contiguous Vec<Slot<T>>  +  Intrusive Free List (free_head = Some(2))", "name")
    fig.text(70, 70, "Empty slots thread the free list directly inside the array; zero separate heap nodes", "sub")

    slots = [
        ("slot[0]  gen = 1", "Occupied(\"gamma\")", "green"),
        ("slot[1]  gen = 0", "Occupied(\"beta\")", "green"),
        ("slot[2]  gen = 2", "Free { next: 3 }", "amber"),
        ("slot[3]  gen = 1", "Free { next: None }", "gray"),
    ]
    sx = 34
    for hdr, body, tone in slots:
        fig.cell(sx, 84, 174, 58, tone, [(hdr, "small"), (body, "monob")], kind="card", r=8)
        sx += 186

    # Intrusive free-list arrow from slot[2] -> slot[3]
    fig.wire([(580, 113), (592, 113)], "amber", width=2.2)

    # Stale vs. Live handle checks below slot[0]
    fig.cell(34, 174, 344, 54, "red", [
        ("Stale Handle { index: 0, gen: 0 }", "monob"),
        ("0 != slot[0].gen (1)  ->  returns None (ABA blocked)", "small"),
    ], kind="card", r=8)
    fig.cell(404, 174, 360, 54, "green", [
        ("Live Handle { index: 0, gen: 1 }", "monob"),
        ("1 == slot[0].gen (1)  ->  returns Some(\"gamma\")", "small"),
    ], kind="card", r=8)

    fig.wire([(121, 172), (121, 144)], "red", dash=True, width=1.8)
    fig.wire([(460, 172), (460, 158), (156, 158), (156, 144)], "green", width=1.8)

    # Bottom row: 3 architectural comparison cards
    cards = [
        (20, "red", "Textbook LinkedList<T>", "1 heap alloc per node", "Scattered RAM; cache miss", "per pointer hop (avoid)"),
        (280, "purple", "Linux list_head + SLUB", "Intrusive links in object", "Multi-list task_struct;", "stable addresses + slabs"),
        (540, "green", "GenArena + Free List", "Contiguous Vec<Slot<T>>", "O(1) reuse, zero unsafe,", "stale handles caught"),
    ]
    for cx, tone, title, l1, l2, l3 in cards:
        fig.node(cx, 258, 240, 134, tone)
        fig.text(cx + 120, 284, title, "monob", "middle", tone=tone, fit=(cx + 8, cx + 232))
        fig.lines(cx + 120, 342, [
            (l1, "name"),
            (l2, "sub"),
            (l3, "sub"),
        ], "middle", fit=(cx + 8, cx + 232))

    fig.save([
        "Freeing slot 0 increments its generation from 0 to 1 and pushes index 0 onto free_head; reusing slot 0 issues Handle(0, 1).",
        "Any leftover Handle(0, 0) fails the generation check (0 != 1) and returns None instead of silently reading the new object.",
    ])


@figure
def ch08_bump():
    fig = Fig("ch08_bump", "Figure 8-2. Bump Allocator Layout: Sequential Offsets and Explicit 16-Byte Alignment Padding", 336)

    # Top container: 64 KiB Arena Linear Byte Layout (y=12..166)
    fig.node(28, 12, 744, 152, "gray", kind="tonal", r=12)
    fig.text(44, 34, "Contiguous 64 KiB Arena (Byte Offsets 0 .. 65,535)", "name")
    fig.text(44, 50, "Each allocation advances next_offset; alignment padding fills any gap to the next power-of-two boundary", "small", fit=(44, 756))

    fig.cell(44, 68, 126, 76, "blue", [
        ("Block 1 (8 B)", "name"),
        ("bytes 0..7", "mono"),
        ("align = 8", "small"),
    ], kind="card", r=8)

    fig.cell(178, 68, 114, 76, "purple", [
        ("Block 2 (3 B)", "name"),
        ("bytes 8..10", "mono"),
        ("align = 8", "small"),
    ], kind="card", r=8)

    fig.cell(300, 68, 116, 76, "amber", [
        ("5 B Padding", "name"),
        ("bytes 11..15", "mono"),
        ("align 11 → 16", "small"),
    ], kind="mid", r=8)

    fig.cell(424, 68, 150, 76, "teal", [
        ("Block 3 (16 B)", "name"),
        ("bytes 16..31", "mono"),
        ("align = 16", "small"),
    ], kind="card", r=8)

    free_box = fig.cell(582, 68, 174, 76, "green", [
        ("Free Arena Space", "name"),
        ("bytes 32..65535", "mono"),
        ("next_offset = 32", "monob"),
    ], kind="card", r=8)

    # Bottom row: Step-by-step arithmetic explanation (y=182..322)
    fig.cell(28, 182, 232, 136, "blue", [
        ("Step 1: alloc(8, align=8)", "name"),
        ("next_offset = 0", "mono"),
        ("(0 + 7) & ~7 = 0", "mono"),
        ("Returns base + 0", "small"),
        ("Advances offset: 0 → 8", "small"),
    ], kind="card", r=10)

    fig.cell(284, 182, 232, 136, "purple", [
        ("Step 2: alloc(3, align=8)", "name"),
        ("next_offset = 8", "mono"),
        ("(8 + 7) & ~7 = 8", "mono"),
        ("Returns base + 8", "small"),
        ("Advances offset: 8 → 11", "small"),
    ], kind="card", r=10)

    fig.cell(540, 182, 232, 136, "teal", [
        ("Step 3: alloc(16, align=16)", "name"),
        ("next_offset = 11 (misaligned)", "mono"),
        ("(11 + 15) & ~15 = 16", "monob"),
        ("Skips 5 pad bytes (11..15)", "small"),
        ("Advances offset: 16 → 32", "small"),
    ], kind="card", r=10)

    fig.save([
        "Why bytes 11..15 are skipped: 11 is not a multiple of 16, so rounding up inserts 5 bytes of alignment padding.",
        "Individual objects cannot be freed; reset() rewinds next_offset to 0 in O(1) to reclaim the entire arena.",
    ])


@figure
def ch08_freelist():
    fig = Fig("ch08_freelist", "Figure 8-3. Free-List Allocator: Unified Trace of Header Layout, Block Splitting, and Coalescing", 414)

    # Band 1: Initial allocations A(100), B(200), C(300) (y=12..130)
    fig.node(28, 12, 744, 118, "blue", kind="tonal", r=12)
    fig.text(44, 34, "1. Initial Layout After alloc(100), alloc(200), alloc(300)  (BlockHeader = 24 bytes)", "name", fit=(44, 756))

    fig.cell(44, 48, 166, 68, "blue", [
        ("Hdr 24B | Block A", "name"),
        ("off 0 · 100 B", "mono"),
        ("next → offset 124", "small"),
    ], kind="card", r=8)

    fig.cell(226, 48, 166, 68, "purple", [
        ("Hdr 24B | Block B", "name"),
        ("off 124 · 200 B", "mono"),
        ("next → offset 348", "small"),
    ], kind="card", r=8)

    fig.cell(408, 48, 166, 68, "teal", [
        ("Hdr 24B | Block C", "name"),
        ("off 348 · 300 B", "mono"),
        ("next → offset 672", "small"),
    ], kind="card", r=8)

    fig.cell(590, 48, 166, 68, "gray", [
        ("Hdr 24B | Free Tail", "name"),
        ("off 672 · free", "mono"),
        ("next → null", "small"),
    ], kind="card", r=8)

    fig.wire([(210, 82), (224, 82)], "blue", width=1.8)
    fig.wire([(392, 82), (406, 82)], "purple", width=1.8)
    fig.wire([(574, 82), (588, 82)], "teal", width=1.8)

    # Band 2: Splitting Block B's 200 B hole on alloc(150) (y=146..268)
    fig.node(28, 146, 744, 122, "amber", kind="tonal", r=12)
    fig.text(44, 168, "2. Block Splitting: free(B) leaves 200 B; alloc(150) carves a 24 B header + 26 B remainder", "name", fit=(44, 756))

    fig.cell(44, 184, 126, 68, "gray", [
        ("Block A", "name"),
        ("used 100 B", "mono"),
    ], kind="card", r=8)

    fig.cell(184, 184, 196, 68, "green", [
        ("Hdr 24B | Block D", "name"),
        ("off 124 · used 150 B", "mono"),
        ("reuses old B address", "small"),
    ], kind="card", r=8)

    fig.cell(394, 184, 212, 68, "amber", [
        ("New Hdr 24B | Free Rem", "name"),
        ("offset 298 · free 26 B", "mono"),
        ("200 − 150 − 24 = 26 B", "small"),
    ], kind="mid", r=8)

    fig.cell(620, 184, 136, 68, "gray", [
        ("Block C + Tail", "name"),
        ("offset 348 ..", "mono"),
    ], kind="card", r=8)

    fig.wire([(380, 218), (392, 218)], "green", width=1.8)
    fig.wire([(606, 218), (618, 218)], "amber", width=1.8)

    # Band 3: Coalescing adjacent free blocks on free(D) (y=284..402)
    fig.node(28, 284, 744, 118, "green", kind="tonal", r=12)
    fig.text(44, 306, "3. Coalescing: free(D) merges adjacent free blocks and reclaims the 24 B middle header", "name", fit=(44, 756))

    c_left = fig.cell(44, 322, 166, 66, "amber", [
        ("Free Block D", "name"),
        ("150 B payload", "mono"),
    ], kind="card", r=8)

    c_mid = fig.cell(224, 322, 164, 66, "amber", [
        ("Hdr 24B + Rem", "name"),
        ("24 B + 26 B free", "mono"),
    ], kind="card", r=8)

    c_merged = fig.cell(442, 322, 314, 66, "green", [
        ("Coalesced Free Block (offset 124)", "name"),
        ("150 + 24 + 26 = 200 B payload restored", "monob"),
        ("External fragmentation eliminated", "small"),
    ], kind="card", r=8)

    fig.wire([(c_left.r + 2, 355), (c_mid.x - 2, 355)], "amber", width=1.8)
    fig.wire([(c_mid.r + 4, 355), (c_merged.x - 4, 355)], "green", width=2.4)

    fig.save([
        "The user pointer returned by alloc() points 24 bytes past BlockHeader; free(ptr) subtracts 24 bytes to recover the header.",
        "Splitting requires leftover_bytes >= sizeof(BlockHeader) + 16 so the remainder holds a valid header and usable payload.",
    ])


@figure
def ch08_allocator_hierarchy():
    fig = Fig("ch08_allocator_hierarchy", "Figure 8-4. Production Allocator Architecture: Thread Caches, Boundary Tags, and mmap Threshold", 392)

    # Tier 1: Thread-Local Cache (tcache) (y=12..126)
    fig.node(28, 12, 744, 114, "green", kind="tonal", r=12)
    fig.tile(42, 22, "bolt", "green", 24)
    fig.text(74, 35, "Tier 1: Per-Thread Cache (tcache) — Lock-Free Ring 3 Fast Path for Small Allocations", "name", fit=(74, 760))

    classes = [("16 B Bin", "freelist head"), ("32 B Bin", "freelist head"), ("64 B Bin", "freelist head"), ("128 B..4 KiB", "segregated bins")]
    for idx, (label, sub) in enumerate(classes):
        x = 44 + idx * 180
        fig.cell(x, 54, 168, 56, "green", [(label, "name"), (sub, "small")], kind="card", r=8)

    # Tier 2: Central Arenas & Boundary Tags (y=142..268)
    fig.node(28, 142, 744, 126, "blue", kind="tonal", r=12)
    fig.tile(42, 152, "layers", "blue", 24)
    fig.text(74, 165, "Tier 2: Central Size-Class Arenas & Knuth Boundary Tags (O(1) Bidirectional Coalescing)", "name", fit=(74, 760))

    fig.cell(44, 184, 134, 68, "amber", [
        ("Prev Footer", "name"),
        ("size | free_bit", "mono"),
        ("O(1) back-peek", "small"),
    ], kind="card", r=8)

    fig.cell(190, 184, 114, 68, "blue", [
        ("Header", "name"),
        ("size | flag", "mono"),
        ("8 B tag", "small"),
    ], kind="mid", r=8)

    fig.cell(312, 184, 200, 68, "blue", [
        ("User Payload Region", "name"),
        ("16-byte aligned address", "mono"),
        ("returned to caller", "small"),
    ], kind="card", r=8)

    fig.cell(520, 184, 114, 68, "blue", [
        ("Footer", "name"),
        ("size | flag", "mono"),
        ("replicated", "small"),
    ], kind="mid", r=8)

    fig.cell(646, 184, 110, 68, "amber", [
        ("Next Header", "name"),
        ("size | flag", "mono"),
        ("O(1) fwd", "small"),
    ], kind="card", r=8)

    # Tier 3: Large Allocations via Direct mmap (y=284..378)
    fig.node(28, 284, 744, 94, "purple", kind="tonal", r=12)
    fig.tile(42, 294, "memory", "purple", 24)
    fig.text(74, 307, "Tier 3: Large Allocations (≥ 128 KiB, M_MMAP_THRESHOLD) — Direct mmap / munmap", "name", fit=(74, 760))

    fig.cell(44, 326, 344, 38, "purple", [
        ("alloc(≥ 128 KiB) → dedicated mmap() region", "mono"),
    ], kind="card", r=8)

    fig.cell(412, 326, 344, 38, "purple", [
        ("free() → immediate munmap() back to OS", "mono"),
    ], kind="card", r=8)

    fig.save([
        "Per-thread segregated size-class caches satisfy small allocations in Ring 3 without acquiring global arena locks.",
        "Replicating size and free status in a block Footer lets free() inspect the previous physical block in O(1) time.",
    ])


# ---------------------------------------------------------------- Chapter 9

@figure
def ch09_trap():
    fig = Fig("ch09_trap", "Figure 9-1. One system call: six steps across the privilege boundary.", 346)

    fig.node(28, 0, 744, 150, "blue")
    fig.tile(44, 10, "person", "blue", 26)
    fig.text(80, 29, "user mode", "name")

    fig.node(28, 196, 744, 150, "green")
    fig.tile(44, 206, "settings_suggest", "green", 26)
    fig.text(80, 225, "kernel mode", "name")

    def step(x, y, tone, text):
        return fig.node(x, y, 160, 92, tone, [(line, "body") for line in text], layout="center", kind="card", r=10)

    step_1 = step(44, 46, "blue", ["1. program calls", "getppid()", "(libc stub)"])
    step_2 = step(240, 46, "blue", ["2. stub puts the syscall", "number and arguments", "in registers"])
    step_6 = step(596, 46, "blue", ["6. return value in a", "register; program", "resumes"])
    step_3 = step(240, 242, "green", ["3. CPU saves the", "user registers,", "switches rings"])
    step_4 = step(418, 242, "green", ["4. syscall table", "selects the handler", "for number 110"])
    step_5 = step(596, 242, "green", ["5. kernel reads the", "parent PID from the", "process table"])

    fig.rule(28, 173, 772, 173, "gray", width=3, dash="2 7")

    fig.wire([(step_1.r + 3, 92), (step_2.x - 3, 92)], "blue", width=2.2)
    fig.wire([(step_2.cx, step_2.b + 3), (step_3.cx, step_3.y - 3)], "blue", width=2.4)
    fig.label(step_2.cx + 14, 178, "trap", tone="blue", cls="name", anchor="start")
    fig.wire([(step_3.r + 2, 288), (step_4.x - 2, 288)], "green", width=2)
    fig.wire([(step_4.r + 2, 288), (step_5.x - 2, 288)], "green", width=2)
    fig.wire([(step_5.cx, step_5.y - 3), (step_6.cx, step_6.b + 3)], "green", width=2.4)
    fig.rect(step_5.cx + 10, 157, 76, 34, "paper", r=4)
    fig.lines(step_5.cx + 14, 174, [("returns", "sub"), ("to ring 3", "sub")], "start", tone="green")

    fig.save(["Most of the cost lies in steps 3 and 6, where the CPU saves and restores registers and changes its privilege level."])


@figure
def ch09_buffering():
    fig = Fig("ch09_buffering", "Figure 9-2. The user-level buffer turns N system calls into N / B.", 218)

    fig.heading(28, 16, "unbuffered")
    program = fig.node(28, 28, 200, 66, "blue", ["program", "17 bytes at a time"], icon="terminal")
    kernel = fig.node(572, 28, 200, 66, "red", ["kernel", "200,000 syscalls"], icon="settings_suggest")
    for offset in (-20, -10, 0, 10, 20):
        fig.wire([(program.r + 4, 61 + offset), (kernel.x - 4, 61 + offset)], "red", width=1.4)
    fig.label(400, 65.5, "write(2) ×N", tone="red", cls="monob")

    fig.heading(28, 138, "buffered")
    program = fig.node(28, 150, 200, 66, "blue", ["program", "17 bytes at a time"], icon="terminal")
    buffer = fig.node(310, 150, 180, 66, "amber", ["64 KiB buffer", "(in the program)"], icon="inventory_2")
    kernel = fig.node(572, 150, 200, 66, "green", ["kernel", "≈53 syscalls"], icon="settings_suggest")
    fig.wire([(program.r + 4, 183), (buffer.x - 4, 183)], "amber", width=2.2)
    fig.label(269, 172, "fills up", backed=False)
    fig.wire([(buffer.r + 4, 183), (kernel.x - 4, 183)], "green", width=3)
    fig.label(531, 172, "flushes", backed=False)

    fig.save(["Both programs deliver the same bytes. They differ in the number of system calls."])


# ---------------------------------------------------------------- Chapter 10

@figure
def ch10_signal_lifecycle():
    fig = Fig("ch10_signal_lifecycle", "Figure 10-1. A signal is generated, kept pending, then delivered.", 196)

    generated = fig.node(28, 0, 220, 96, "blue", ["generated", "raise(), kill(),", "or a hardware event"], icon="bolt")
    pending = fig.node(290, 0, 220, 96, "amber", ["pending set", "a per-process bitmask:", "one bit per signal"], icon="pending")
    delivered = fig.node(552, 0, 220, 96, "green", ["delivered", "the handler runs", "in user mode"], icon="play_arrow")

    fig.wire([(generated.r + 3, 48), (pending.x - 3, 48)], "wire", width=2.4)
    fig.wire([(pending.r + 3, 48), (delivered.x - 3, 48)], "wire", width=2.4)

    blocked = fig.node(28, 132, 380, 64, "red", kind="dashed", r=12)
    fig.icon(42, 153, "block", "red", 22)
    fig.lines(74, blocked.cy, [("blocked signals stay pending until unblocked", "sub"),
                               ("a second SIGUSR1 while pending is not queued twice", "sub")],
              "start", fit=(74, blocked.r - 6), tone="red")
    fig.wire([(340, pending.b + 3), (340, blocked.y - 3)], "red", dash=True, width=2)

    decision = fig.node(432, 132, 340, 64, "gray", r=12)
    fig.tile(444, 147, "rule", "gray", 34)
    fig.lines(489, decision.cy, [("kernel decides: the signal’s action", "sub"), ("default · ignore · or run the handler", "sub")],
              "start", fit=(481, decision.r - 6))
    fig.wire([(460, pending.b + 3), (460, decision.y - 3)], "wire", width=2)

    fig.save(["A handler runs on the stack of the receiving thread, between two of its instructions, so it should do very little."])


# ---------------------------------------------------------------- Chapter 11

@figure
def ch11_pipe():
    fig = Fig("ch11_pipe", "Figure 11-1. A pipe is a byte stream held in a kernel buffer.", 156)

    fig.node(28, 0, 200, 156, "blue")
    fig.lines(128, 46, [("process 1 (child)", "name"), ("write(fd[1], …)", "mono"), ("closes fd[0]", "sub")], "middle",
              fit=(34, 222))
    fd_write = fig.cell(152, 104, 64, 36, "blue", [("fd 1", "monob")], kind="card", r=9)

    fig.node(572, 0, 200, 156, "purple")
    fig.lines(672, 46, [("process 2 (parent)", "name"), ("read(fd[0], …)", "mono"), ("closes fd[1]", "sub")], "middle",
              fit=(578, 766))
    fd_read = fig.cell(584, 104, 64, 36, "purple", [("fd 0", "monob")], kind="card", r=9)

    kernel = fig.node(304, 0, 192, 156, "green")
    fig.lines(400, 50, [("kernel buffer", "name"), ("bounded, FIFO", "sub"), ("no message boundaries", "sub"),
                        ("read blocks when empty;", "sub"), ("write blocks when full", "sub")], "middle",
              fit=(kernel.x + 4, kernel.r - 4))
    for index in range(6):
        fig.rect(319 + index * 28, 110, 22, 24, "a-green" if index < 4 else "card", r=5)

    fig.wire([(fd_write.r + 3, 122), (kernel.x - 3, 122)], "blue", width=2.4)
    fig.label(266, 110, "bytes in", backed=False)
    fig.wire([(kernel.r + 3, 122), (fd_read.x - 3, 122)], "purple", width=2.4)
    fig.label(534, 110, "bytes out", backed=False)

    fig.save([
        "pipe() creates both descriptors, and fork() duplicates them. Each process then closes the end it does not use.",
        "A reader receives end-of-file only after every copy of the write end has been closed.",
    ])


@figure
def ch11_shm():
    fig = Fig("ch11_shm", "Figure 11-2. Shared memory: two page tables, one physical frame.", 226)

    process_1 = fig.node(28, 0, 190, 110, "blue", ["process 1", "virtual page A", "(mutex + counter)"], icon="terminal",
                         layout="center", icon_size=28)
    process_2 = fig.node(582, 0, 190, 110, "purple", ["process 2", "virtual page B", "(mutex + counter)"], icon="terminal",
                         layout="center", icon_size=28)

    table_1 = fig.node(258, 0, 130, 110, "blue", kind="card", r=12)
    fig.text(table_1.cx, 30, "page table 1", "sub", "middle")
    fig.cell(270, 46, 106, 34, "blue", [("A → frame 9", "mono")], kind="mid")

    table_2 = fig.node(412, 0, 130, 110, "purple", kind="card", r=12)
    fig.text(table_2.cx, 30, "page table 2", "sub", "middle")
    fig.cell(424, 46, 106, 34, "purple", [("B → frame 9", "mono")], kind="mid")

    frame = fig.node(300, 156, 200, 70, "green", ["frame 9", "the shared object"], icon="view_module")

    fig.wire([(process_1.r + 3, 63), (table_1.x - 3, 63)], "blue", width=2.2)
    fig.wire([(process_2.x - 3, 63), (table_2.r + 3, 63)], "purple", width=2.2)
    fig.wire([(table_1.cx, table_1.b + 3), (table_1.cx, 133), (360, 133), (360, frame.y - 3)], "blue", width=2.2)
    fig.wire([(table_2.cx, table_2.b + 3), (table_2.cx, 133), (440, 133), (440, frame.y - 3)], "purple", width=2.2)

    fig.save([
        "Both processes load and store the same bytes, so they must synchronize their access.",
        "A process-shared mutex stored in the shared page protects the counter.",
    ])


# ---------------------------------------------------------------- Chapter 12

@figure
def ch12_fs_layout():
    fig = Fig("ch12_fs_layout", "Figure 12-1. A file system organizes fixed-size blocks into metadata and data.", 238)

    fig.text(28, 12, "one file system on a partition", "sub")

    strip = [
        (28, 110, "purple", "superblock", "geometry"),
        (141, 110, "purple", "inode bitmap", "free inodes"),
        (254, 110, "purple", "data bitmap", "free blocks"),
        (367, 170, "amber", "inode table", "one inode per file"),
        (540, 232, "green", "data blocks", "file contents and directories"),
    ]
    for x, width, tone, name, sub in strip:
        fig.cell(x, 22, width, 64, tone, [(name, "body"), (sub, "small")], kind="mid", r=8)

    directory = fig.node(28, 136, 250, 102, "green",
                         [("a directory is a file", "name"), ("\"notes.txt\" → inode 42", "mono"), ("\"src\" → inode 51", "mono"),
                          ("entries: name + inode number", "sub")], icon="folder")
    inode = fig.node(372, 136, 160, 102, "amber",
                     [("inode 42", "name"), "mode, owner, size,", "timestamps, links,", "block pointers"], layout="center")
    data = fig.node(626, 136, 146, 102, "green",
                    [("data blocks", "name"), "the bytes of", "notes.txt", "several blocks"], layout="center")

    fig.rule(inode.cx, 88, inode.cx, 134, "amber", width=1.4, dash="2 5")
    fig.rule(data.cx, 88, data.cx, 134, "green", width=1.4, dash="2 5")

    fig.wire([(directory.r + 3, 187), (inode.x - 3, 187)], "wire", width=2.2)
    fig.label(325, 177, "lookup", backed=False)
    fig.wire([(inode.r + 3, 187), (data.x - 3, 187)], "wire", width=2.2)
    fig.label(579, 177, "block pointers", backed=False)

    fig.save([
        "A directory entry holds the name of a file. The inode holds all other information about it.",
        "A hard link is a second directory entry with the same inode number. Deleting a name removes one entry.",
        ("Opening a file: path lookup", "noteb"),
        "The kernel looks up each name of the path in its directory, reads the inode, checks permissions, and returns "
        "a descriptor that refers to the inode. Later calls use the descriptor and not the path.",
        "A file can be deleted while it is open. Its inode remains until the last descriptor is closed.",
    ])


@figure
def ch12_inode():
    fig = Fig("ch12_inode", "Figure 12-2. An inode points to data blocks directly and indirectly.", 306)

    fig.node(28, 0, 220, 306, "amber")
    fig.tile(44, 12, "description", "amber", 28)
    fig.text(82, 32, "inode", "name")
    fig.lines(44, 78, [("mode · uid · gid", "sub"), ("size · timestamps", "sub"), ("link count", "sub")], "start", fit=(44, 240))
    fig.rule(44, 112, 232, 112, "amber", width=1.2)

    pointers = [("direct 0", "blue"), ("direct 1", "blue"), ("… direct 11", "blue"),
                ("indirect", "purple"), ("double", "purple"), ("triple", "purple")]
    rows = []
    for index, (text, tone) in enumerate(pointers):
        rows.append(fig.cell(44, 122 + index * 30, 188, 25, tone, [(text, "small")], kind="card", r=6))

    for row in rows[:3]:
        block = fig.cell(340, row.y, 130, 25, "blue", [("data block", "small")], kind="mid", r=6)
        fig.wire([(row.r + 3, row.cy), (block.x - 3, row.cy)], "blue", width=1.8)

    indirect = fig.cell(340, rows[3].y, 130, 25, "purple", [("indirect block:", "small")], kind="mid", r=6)
    fig.wire([(rows[3].r + 3, rows[3].cy), (indirect.x - 3, indirect.cy)], "purple", width=1.8)

    for dy in (-17, 17):
        block = fig.cell(580, indirect.cy + dy - 12.5, 130, 25, "blue", [("data block", "small")], kind="mid", r=6)
        fig.wire([(indirect.r + 3, indirect.cy), (525, indirect.cy), (525, block.cy), (block.x - 3, block.cy)], "purple",
                 width=1.8)

    fig.save([
        "A file of up to 12 blocks needs only the direct pointers. A larger file needs one more block read for each level of indirection.",
        "An inode contains no name. stat() returns the fields of an inode without reading data blocks.",
    ])


# ---------------------------------------------------------------- Chapter 13

@figure
def ch13_event_loop():
    fig = Fig("ch13_event_loop", "Figure 13-1. One thread, many connections: the event loop pattern.", 216)

    fig.node(28, 0, 360, 216, "blue")
    fig.tile(44, 10, "loop", "blue", 28)
    fig.text(82, 30, "event loop (one thread)", "name")

    def step(x, y, text):
        return fig.node(x, y, 150, 58, "blue", [(text[0], "body"), (text[1], "small")], layout="center", kind="card", r=10)

    step_1 = step(44, 52, ["1. poll(fds)", "which fds are ready?"])
    step_2 = step(222, 52, ["2. dispatch", "read / write / accept"])
    step_3 = step(222, 142, ["3. handle events", "never blocks"])
    step_4 = step(44, 142, ["4. loop", "back to poll"])

    fig.wire([(step_1.r + 2, 81), (step_2.x - 2, 81)], "blue", width=2)
    fig.wire([(step_2.cx, step_2.b + 2), (step_3.cx, step_3.y - 2)], "blue", width=2)
    fig.wire([(step_3.x - 2, 171), (step_4.r + 2, 171)], "blue", width=2)
    fig.wire([(step_4.cx, step_4.y - 2), (step_1.cx, step_1.b + 2)], "blue", width=2)

    fig.node(472, 0, 300, 216, "green")
    fig.tile(488, 10, "settings_suggest", "green", 28)
    fig.text(526, 30, "kernel", "name")
    queue_4 = fig.cell(488, 52, 130, 46, "green", [("wait queue: fd 4", "sub")], kind="card", r=10)
    queue_5 = fig.cell(626, 52, 130, 46, "green", [("wait queue: fd 5", "sub")], kind="card", r=10)
    buffers = fig.node(488, 126, 268, 74, "green", [("socket buffers", "body"), ("data arrives → wake the waiter", "small")],
                       layout="center", kind="card", r=10)
    fig.wire([(queue_4.cx, buffers.y - 2), (queue_4.cx, queue_4.b + 2)], "green", width=1.8)
    fig.wire([(queue_5.cx, buffers.y - 2), (queue_5.cx, queue_5.b + 2)], "green", width=1.8)

    fig.wire([(391, 76), (469, 76)], "blue", width=2.2)
    fig.label(430, 66, "register", tone="blue", backed=False)
    fig.wire([(469, 150), (391, 150)], "green", width=2.2)
    fig.label(430, 140, "ready list", tone="green", backed=False)

    fig.save([
        "With blocking I/O, each connection has a thread that waits in read() inside the kernel.",
        "In an event loop, one thread asks the kernel which descriptors are ready and serves them in turn.",
        "poll(2) works on Linux and macOS. epoll (Linux) and kqueue (macOS, BSD) return only the ready descriptors.",
        "With all three, the loop thread must not block outside the wait call. Blocking work belongs on another thread.",
    ])


# ---------------------------------------------------------------- Chapter 14

@figure
def ch14_tcp():
    fig = Fig("ch14_tcp", "Figure 14-1. A TCP connection: handshake, data, teardown.", 420)

    host_a = fig.node(28, 0, 240, 70, "blue", ["host A (client)", ("connect(), write(), close()", "small")], icon="laptop")
    host_b = fig.node(532, 0, 240, 70, "purple", ["host B (server)", ("bind(), listen(), accept()", "small")], icon="dns")

    phases = [
        (84, "blue", "handshake", [
            (True, "1. SYN, seq = x", "wire"),
            (False, "2. SYN + ACK, seq = y, ack = x + 1", "wire"),
            (True, "3. ACK, ack = y + 1 (connection established)", "green"),
        ]),
        (222, "green", "swap_horiz", [
            (True, "data, seq = x + 1 (stream, ordered)", "green"),
            (False, "ACK, ack = x + 1 + n bytes", "green"),
        ]),
        (320, "red", "close", [
            (True, "FIN (I have no more to send)", "red"),
            (False, "FIN + ACK (both sides closed)", "red"),
        ]),
    ]

    left, right = host_a.cx, host_b.cx
    for top, tone, icon, messages in phases:
        height = 40 * len(messages) + 18
        fig.rect(28, top, 744, height, f"c-{tone}", r=12)
        fig.tile(40, top + height / 2 - 15, icon, tone, 30)
        for index, (forward, text, wire_tone) in enumerate(messages):
            y = top + 38 + index * 40
            ends = [(left + 4, y), (right - 4, y)] if forward else [(right - 4, y), (left + 4, y)]
            fig.wire(ends, wire_tone, width=2)
            fig.text(400, y - 8, text, "sub", "middle", tone=None if wire_tone == "wire" else wire_tone)

    fig.rule(left, 72, left, 420, "blue", width=2, dash="2 6")
    fig.rule(right, 72, right, 420, "purple", width=2, dash="2 6")

    fig.save([
        "A connection opens with three segments. Sequence numbers count bytes, because TCP carries a byte stream.",
        "UDP has no handshake, no retransmission, and no ordering. It sends each datagram once.",
    ])


# ---------------------------------------------------------------- Chapter 15

@figure
def ch15_daemonize():
    fig = Fig("ch15_daemonize", "Figure 15-1. Becoming a daemon: four steps to detach from the terminal.", 414)

    fig.heading(28, 16, "before")
    shell = fig.node(28, 28, 236, 66, "gray", [("shell (session leader)", "body"), "controlling terminal"], icon="person")
    daemon = fig.node(310, 28, 220, 66, "blue", [("daemon-to-be", "body"), "child of the shell"], icon="settings")
    terminal = fig.node(576, 28, 196, 66, "amber", [("terminal", "body")], icon="terminal")
    fig.wire([(shell.r + 3, 61), (daemon.x - 3, 61)], "wire", width=2.2)
    fig.wire([(daemon.r + 3, 61), (terminal.x - 3, 61)], "wire", width=2.2)

    steps = [
        ("call_split", "blue", "1. fork: the parent exits; the daemon runs in the child."),
        ("logout", "purple", "2. setsid: the child becomes leader of a new session, with no controlling terminal."),
        ("call_split", "teal", "3. fork again: the session leader exits, so no terminal can ever be acquired."),
        ("edit_note", "green", "4. chdir(\"/\"), umask, stdio to log and /dev/null, write the pidfile, install handlers."),
    ]
    for index, (icon, tone, text) in enumerate(steps):
        y = 120 + index * 48
        fig.rect(28, y, 744, 42, f"c-{tone}", r=12)
        fig.tile(44, y + 8, icon, tone, 26)
        fig.text(84, y + 25.5, text, "body", fit=(84, 766))

    fig.heading(28, 334, "after")
    session = fig.node(28, 346, 190, 66, "gray", [("session", "body"), "no terminal"], icon="block")
    final = fig.node(264, 346, 212, 66, "green", [("daemon", "body"), "PID 1 reparented"], icon="settings")
    fig.node(522, 346, 250, 66, "amber", [("stdin ← /dev/null", "mono"), ("stdout/stderr → log file", "mono")],
             icon="description")
    fig.wire([(session.r + 3, 379), (final.x - 3, 379)], "wire", width=2.2)

    fig.save([
        "SIGHUP now means \"reload configuration\"; SIGTERM means \"shut down gracefully\". Both arrive from the supervisor, "
        "not the terminal. systemd and launchd start, restart, and log a daemon, so the daemon need not do this itself.",
    ])


# ---------------------------------------------------------------- Chapter 16

@figure
def ch16_vm_vs_container():
    fig = Fig("ch16_vm_vs_container", "Figure 16-1. Virtual machines duplicate the operating system; containers share it.", 286)

    fig.heading(204, 18, "virtual machines", icon="dns", tone="purple", anchor="middle")
    for x, app in ((28, "app A"), (210, "app B")):
        fig.node(x, 30, 170, 124, "purple", kind="dashed", r=14)
        fig.cell(x + 8, 38, 154, 50, "blue", [(app, "body")], kind="mid", r=10)
        fig.cell(x + 8, 96, 154, 50, "purple", [("guest OS", "body")], kind="mid", r=10)
    fig.cell(28, 164, 352, 56, "teal", [("hypervisor", "body"), ("partitions the machine", "small")], kind="tonal", r=12)
    fig.cell(28, 228, 352, 56, "amber", [("hardware", "body"), ("CPU, memory, devices", "small")], kind="tonal", r=12)

    fig.heading(596, 18, "containers", icon="inventory_2", tone="green", anchor="middle")
    for x, app in ((420, "app A"), (602, "app B")):
        fig.node(x, 30, 170, 66, "green", kind="dashed", r=14)
        fig.cell(x + 8, 38, 154, 50, "blue", [(app, "body")], kind="mid", r=10)
    fig.cell(420, 104, 352, 50, "green", [("container runtime", "body")], kind="tonal", r=12)
    fig.cell(420, 164, 352, 56, "green", [("one host kernel", "body"), ("namespaces + cgroups", "small")], kind="mid", r=12)
    fig.cell(420, 228, 352, 56, "amber", [("hardware", "body"), ("CPU, memory, devices", "small")], kind="tonal", r=12)

    fig.save([
        "Virtual machines isolate strongly and can run any guest OS, but each instance costs more.",
        "Containers share one kernel and run at nearly native speed. The host kernel provides their isolation.",
        "Data centers often separate customers with virtual machines and run containers inside them.",
    ])


@figure
def ch16_namespaces():
    fig = Fig("ch16_namespaces", "Figure 16-3. A PID namespace maps its own numbers onto the host’s table.", 270)

    fig.node(28, 0, 290, 270, "gray")
    fig.tile(44, 12, "table_rows", "gray", 28)
    fig.text(82, 32, "host PID table", "name")

    host_rows = [
        (54, "gray", "PID 1: init"),
        (96, "purple", "PID 42: container A’s app"),
        (130, "purple", "PID 43: container A’s shell"),
        (192, "teal", "PID 91: container B’s app"),
        (226, "teal", "PID 92: container B’s shell"),
    ]
    for y, tone, text in host_rows:
        kind = "card" if tone == "gray" else "mid"
        fig.cell(44, y, 258, 28, tone, [(text, "sub")], kind=kind, r=7)

    spaces = [(80, "purple", "container A’s", (96, 130)), (178, "teal", "container B’s", (192, 226))]
    for top, tone, owner, row_ys in spaces:
        space = fig.node(430, top, 342, 88, tone)
        for y, text in zip(row_ys, ("PID 1: its app", "PID 2: its shell")):
            fig.cell(446, y, 150, 28, tone, [(text, "sub")], kind="card", r=7)
            fig.wire([(304, y + 14), (444, y + 14)], tone, width=2)
        fig.lines(612, (row_ys[0] + row_ys[1] + 28) / 2, [(owner, "name"), ("PID namespace", "name"), ("nothing else exists", "small")], "start",
                  fit=(612, space.r - 6))

    fig.save([
        "The kernel keeps one process table. Each namespace numbers a subset of its entries separately.",
        "Mount, network, and user namespaces restrict other kernel tables in the same way. cgroups limit resource use.",
    ])


# ---------------------------------------------------------------- Chapter 17

@figure
def ch17_numa():
    fig = Fig("ch17_numa", "Figure 17-1. NUMA: memory close to the core is fast; the other socket’s memory is slow.", 236)

    sockets = []
    for x, name in ((28, "socket 0"), (452, "socket 1")):
        fig.node(x, 0, 320, 204, "blue")
        fig.text(x + 160, 26, name, "name", "middle")
        cores = []
        for index in range(3):
            cores.append(fig.node(x + 16 + index * 100, 40, 88, 48, "blue", [("core", "body")], icon="memory",
                                  kind="card", r=10, icon_size=26))
        memory = fig.node(x + 16, 122, 288, 66, "green", [("local memory controller", "body"), ("+ DRAM banks", "sub")],
                          icon="view_module", r=12)
        sockets.append((cores, memory))

    fig.wire([(351, 64), (449, 64)], "wire", tail=True, width=3)
    fig.label(400, 52, "interconnect", backed=False)

    local_core = sockets[0][0][0]
    fig.wire([(local_core.cx, local_core.b + 2), (local_core.cx, sockets[0][1].y - 2)], "green", width=2.4)

    remote_core = sockets[0][0][2]
    remote_memory = sockets[1][1]
    fig.wire([(remote_core.cx, remote_core.b + 2), (remote_core.cx, 105), (remote_memory.x + 40, 105),
              (remote_memory.x + 40, remote_memory.y - 2)], "red", dash=True, width=2.2)

    fig.text(188, 228, "local access: short path, low latency", "sub", "middle", tone="green")
    fig.text(612, 228, "remote access: across the interconnect", "sub", "middle", tone="red")

    fig.save([
        "A thread runs fastest when its pages are in the memory of the socket on which it runs.",
        "Under first-touch placement, a page is allocated on the socket of the core that first writes to it.",
    ])


@figure
def ch17_false_sharing():
    fig = Fig("ch17_false_sharing", "Figure 17-3. False sharing: two independent counters, one contested cache line.", 198)

    fig.heading(28, 16, "unpadded")
    fig.rect(28, 28, 352, 58, "c-red", r=12)
    fig.cell(38, 38, 96, 38, "red", [("counter A", "sub")], kind="mid", r=8)
    fig.cell(138, 38, 96, 38, "red", [("counter B", "sub")], kind="mid", r=8)
    fig.hatch(238, 38, 132, 38, "gray", r=8)
    fig.text(204, 174, "one 64-byte line holds both", "sub", "middle")

    core_a = fig.tile(69, 118, "memory", "red", 34)
    core_b = fig.tile(305, 118, "memory", "red", 34)
    fig.wire([(86, 115), (86, 90)], "red", width=2)
    fig.wire([(322, 115), (322, 90), ], "red", width=2)
    fig.wire([(core_a.r + 6, 135), (core_b.x - 6, 135)], "red", tail=True, dash=True, width=2)
    fig.text(204, 194, "the line bounces between cores on every write", "sub", "middle", tone="red")

    fig.heading(420, 16, "padded")
    for x, counter in ((420, "counter A"), (602, "counter B")):
        fig.rect(x, 28, 170, 58, "c-green", r=12)
        fig.cell(x + 10, 38, 96, 38, "green", [(counter, "sub")], kind="mid", r=8)
        fig.hatch(x + 110, 38, 50, 38, "gray", r=8)
        fig.tile(x + 41, 118, "memory", "green", 34)
        fig.wire([(x + 58, 115), (x + 58, 90)], "green", width=2)
    fig.text(596, 174, "each counter owns a line", "sub", "middle")
    fig.text(596, 194, "no sharing, no bounce, no slowdown", "sub", "middle", tone="green")

    fig.save([
        "The two counters are independent, but a core must own the whole cache line before it writes to either one.",
        "Listing 17-1 measures both layouts.",
    ])


# ---------------------------------------------------------------- Chapter 18

@figure
def ch18_pyramid():
    fig = Fig("ch18_pyramid", "Figure 18-1. The memory hierarchy: smaller and faster at the top.", 312)

    levels = [
        ("registers", "~1 ns · ~1 KB", "red"),
        ("L1 cache", "~1 ns · 32–64 KiB", "red"),
        ("L2 cache", "~3–4 ns · 256 KiB–1 MiB", "amber"),
        ("L3 cache", "~10 ns · 4–32 MiB", "amber"),
        ("DRAM", "~60–100 ns · GBs", "green"),
        ("SSD", "~10–100 µs", "blue"),
        ("disk · network", "", "purple"),
    ]
    center = 290
    for index, (name, cost, tone) in enumerate(levels):
        y = index * 45
        width = 116 + index * 68
        kind = "mid" if index % 2 == 0 else "tonal"
        bar = fig.cell(center - width / 2, y, width, 40, tone, [(name, "name")], kind=kind, r=10)
        if not cost:
            continue
        fig.rule(bar.r + 8, bar.cy, 584, bar.cy, tone, width=1.3, dash="2 5")
        fig.text(592, bar.cy + 4.5, cost, "body", fit=(592, 776))

    fig.save([
        "Access time rises sharply from each level to the next. Listing 18-1 measures these steps.",
        "The numbers are orders of magnitude. Exact values depend on the processor.",
        "Programs run fast when they reuse recently accessed data and access data that lies close together.",
    ])


# ---------------------------------------------------------------- Chapter 19

@figure
def ch19_bounded_queue():
    fig = Fig("ch19_bounded_queue", "Figure 19-1. A bounded queue: coordinating producers and consumers via dual condition variables.", 260)

    prod = fig.node(28, 20, 204, 100, "blue", ["producers", "push(item)", "waits while full"], icon="person", icon_size=28)
    cv_prod = fig.node(28, 140, 204, 96, "red", ["waiting_producers", "condition variable", "sleeps when full"], icon="hourglass_top", kind="mid", icon_size=28)

    queue_box = fig.node(262, 20, 276, 216, "green")
    fig.tile(276, 34, "lock", "green", 34)
    fig.text(322, 56, "std::mutex", "name")
    fig.text(400, 86, "0 <= size <= capacity", "monob", "middle")

    for i in range(6):
        col = i % 3
        row = i // 3
        x = 276 + col * 86
        y = 104 + row * 50
        txt = f"[{i}]" if i < 3 else "empty"
        fig.cell(x, y, 76, 42, "green", [(txt, "mono")], kind="card", r=8)

    fig.text(400, 218, "FIFO ring slots (capacity = 6)", "sub", "middle")

    cons = fig.node(568, 20, 204, 100, "purple", ["consumers", "pop() -> item", "waits while empty"], icon="person", icon_size=28)
    cv_cons = fig.node(568, 140, 204, 96, "amber", ["waiting_consumers", "condition variable", "sleeps when empty"], icon="hourglass_top", kind="mid", icon_size=28)

    fig.wire([(prod.r + 2, 70), (queue_box.x - 2, 70)], "blue", width=2.2)
    fig.wire([(queue_box.r + 2, 70), (cons.x - 2, 70)], "purple", width=2.2)

    fig.wire([(cv_prod.r + 2, 188), (queue_box.x - 2, 188)], "red", dash=True, width=2.0)
    fig.wire([(queue_box.r + 2, 188), (cv_cons.x - 2, 188)], "amber", dash=True, width=2.0)

    fig.save([
        "Producers sleep on waiting_producers when the queue is full; consumers sleep on waiting_consumers when empty.",
        "Predicate loops (while (is_full()) wait(lock)) prevent race conditions from spurious wakeups and lock re-acquisition.",
    ])


@figure
def ch19_ring_variants():
    fig = Fig(
        "ch19_ring_variants",
        "Figure 19-2. Hand-Rolled Ring Buffer (head + len) Wrap-Around Geometry and Backing-Store Trade-Offs.",
        372,
    )

    # Top panel: Wrap-around ring array of 6 slots (head=4, len=3 -> tail=(4+3)%6=1)
    ring_panel = fig.node(20, 18, 760, 174, "blue")
    fig.tile(32, 30, "loop", "blue", 30)
    fig.text(70, 50, "Fixed-Capacity Ring: Vec<Option<T>>  (cap = 6, head = 4, len = 3)", "name")
    fig.text(70, 70, "tail = (head + len) % cap = (4 + 3) % 6 = 1  (no full-vs-empty ambiguity)", "mono", tone="blue")

    slots = [
        ("0", "Some(C)", "green"),
        ("1", "None", "gray"),
        ("2", "None", "gray"),
        ("3", "None", "gray"),
        ("4", "Some(A)", "green"),
        ("5", "Some(B)", "green"),
    ]
    sx = 44
    for idx_s, val_s, tone in slots:
        fig.cell(sx, 86, 110, 52, tone, [(f"buf[{idx_s}]", "small"), (val_s, "monob")], kind="card", r=8)
        sx += 120

    # Pointers below slots: tail at slot 1 (cx = 44 + 120 + 55 = 219), head at slot 4 (cx = 44 + 4*120 + 55 = 579)
    fig.wire([(219, 162), (219, 141)], "purple", width=2.0)
    fig.label(219, 174, "tail = 1 (next push)", tone="purple", cls="monob")
    fig.wire([(579, 162), (579, 141)], "blue", width=2.0)
    fig.label(579, 174, "head = 4 (oldest -> pop)", tone="blue", cls="monob")

    # Bottom row: 4 backing-store comparison cards
    cards = [
        (20, "green", "VecDeque<T>", "Interview Default", "O(1) push & pop", "Built-in MaybeUninit ring"),
        (214, "blue", "Vec<Option<T>>", "Safe Hand-Rolled", "O(1) push & pop", "take() moves T; no unsafe"),
        (408, "purple", "Box<[MaybeUninit]>", "Zero-Overhead Ring", "O(1) push & pop", "Zero tag; manual Drop"),
        (602, "red", "Vec::remove(0)", "O(N) Red Flag", "Shifts all items", "2-stack Vec = amort. O(1)"),
    ]
    for cx, tone, title, tag, perf, note in cards:
        fig.node(cx, 210, 178, 144, tone)
        fig.text(cx + 89, 236, title, "monob", "middle", tone=tone, fit=(cx + 8, cx + 170))
        fig.cell(cx + 12, 248, 154, 30, tone, [(tag, "small")], kind="card", r=6)
        fig.lines(cx + 89, 314, [
            (perf, "monob"),
            (note, "sub"),
        ], "middle", fit=(cx + 8, cx + 170))

    fig.save([
        "Tracking (head, len) instead of (head, tail) distinguishes empty (len == 0) from full (len == cap) without wasting a sentinel slot.",
        "Option<T>::take() moves non-Copy items out of buf[head] safely while leaving None so Drop runs only on live elements.",
    ])


@figure
def ch19_option_maybeuninit_layout():
    fig = Fig(
        "ch19_option_maybeuninit_layout",
        "Figure 19-3. Memory Layout Inside One 64-Byte Cache Line: Option<u64> Tag + Padding, Niche Optimization, and MaybeUninit<u64>.",
        396,
    )

    # Row 1: Option<u64> -> 16 bytes/slot -> 4 slots in 64 bytes
    r1 = fig.node(20, 18, 760, 108, "red")
    fig.text(34, 40, "1. Vec<Option<u64>>:  16 bytes/slot (4 slots per 64 B cache line -> 50% overhead)", "name")
    fig.text(34, 58, "u64 uses all 2^64 bit patterns -> compiler adds 1 B discriminant tag + 7 B alignment padding", "sub")
    x = 34
    for i in range(4):
        # 180 px per 16-byte slot: 38px tag + 58px pad + 80px payload
        fig.cell(x, 68, 38, 44, "red", [("tag", "small"), ("1 B", "mono")], kind="card", r=5)
        fig.cell(x + 40, 68, 56, 44, "gray", [("pad", "small"), ("7 B", "mono")], kind="card", r=5)
        fig.cell(x + 98, 68, 78, 44, "blue", [(f"u64[{i}]", "small"), ("8 B", "monob")], kind="card", r=5)
        x += 184

    # Row 2: Option<Box<u64>> -> Niche optimization -> 8 bytes/slot -> 8 slots in 64 bytes
    r2 = fig.node(20, 140, 760, 108, "teal")
    fig.text(34, 162, "2. Rust Niche Optimization: Option<Box<u64>>  (8 bytes/slot, 8 slots per 64 B line)", "name")
    fig.text(34, 180, "NonNull pointer can never be 0x0 -> Rust encodes None as 0x0 (zero tag, zero padding)", "sub")
    x = 34
    niche_vals = ["0x0 (None)", "0x0 (None)", "ptr A", "ptr B", "ptr C", "0x0 (None)", "0x0 (None)", "0x0 (None)"]
    for i, lbl in enumerate(niche_vals):
        tone = "green" if lbl.startswith("ptr") else "gray"
        short = "0x0" if lbl.startswith("0x0") else lbl
        sub = "None" if lbl.startswith("0x0") else "8 B"
        fig.cell(x, 190, 88, 44, tone, [(short, "monob"), (sub, "small")], kind="card", r=6)
        x += 92

    # Row 3: Box<[MaybeUninit<u64>]> / C++ raw byte storage -> 8 bytes/slot -> 8 slots in 64 bytes
    r3 = fig.node(20, 262, 760, 118, "green")
    fig.text(34, 284, "3. Box<[MaybeUninit<u64>]> / C++ alignas(T) std::byte[8]:  8 bytes/slot (8 slots/line)", "name")
    fig.text(34, 302, "Zero per-slot tag for ANY type T; validity tracked externally by (head = 2, len = 3)", "sub")
    x = 34
    raw_slots = [
        ("uninit", "gray"), ("uninit", "gray"),
        ("u64 A", "green"), ("u64 B", "green"), ("u64 C", "green"),
        ("uninit", "gray"), ("uninit", "gray"), ("uninit", "gray"),
    ]
    for i, (lbl, tone) in enumerate(raw_slots):
        fig.cell(x, 312, 88, 44, tone, [(lbl, "monob"), (f"[{i}] 8 B", "small")], kind="card", r=6)
        x += 92
    fig.text(400, 370, "Manual Drop required: drop only live indices [head .. (head + len) % cap) so uninit bytes are never dropped.", "sub", "middle", fit=(28, 772))

    fig.save([
        "Option<u64> doubles slot size from 8 B to 16 B because 1 tag byte forces 7 alignment padding bytes to keep every u64 8-byte aligned.",
        "MaybeUninit<T> is #[repr(transparent)]: zero tag, zero padding, 2x L1 cache density for integers, and identical layout to raw T.",
    ])


@figure
def ch19_spsc_ring():
    fig = Fig("ch19_spsc_ring", "Figure 19-4. Lock-free SPSC ring buffer: single-writer indices and cache line isolation.", 240)

    p_box = fig.node(28, 20, 220, 190, "blue")
    fig.tile(42, 34, "developer_board", "blue", 34)
    fig.text(88, 56, "Core 0 (Producer)", "name")
    fig.cell(42, 80, 192, 46, "blue", [("tail index", "name"), ("alignas(64)", "mono")], kind="card", r=8)
    fig.lines(138, 160, [("exclusively writes tail", "sub"), ("release store commits payload", "sub")], "middle", fit=(32, 244))

    ring = fig.node(276, 20, 248, 190, "teal")
    fig.tile(290, 34, "loop", "teal", 34)
    fig.text(336, 56, "circular slots", "name")
    fig.text(400, 86, "0 <= tail - head <= cap", "monob", "middle")
    for i in range(5):
        fig.cell(290 + i * 44, 104, 38, 48, "teal", [(f"[{i}]", "mono")], kind="card", r=8)
    fig.lines(400, 180, [("acquire-release pairs synchronize", "sub"), ("data payload across cores", "sub")], "middle", fit=(280, 520))

    c_box = fig.node(552, 20, 220, 190, "purple")
    fig.tile(566, 34, "developer_board", "purple", 34)
    fig.text(612, 56, "Core 1 (Consumer)", "name")
    fig.cell(566, 80, 192, 46, "purple", [("head index", "name"), ("alignas(64)", "mono")], kind="card", r=8)
    fig.lines(662, 160, [("exclusively writes head", "sub"), ("acquire load observes payload", "sub")], "middle", fit=(556, 768))

    fig.wire([(p_box.r + 3, 103), (ring.x - 3, 103)], "blue", width=2.2)
    fig.wire([(ring.r + 3, 103), (c_box.x - 3, 103)], "purple", width=2.2)

    fig.save([
        "The single-writer discipline guarantees each atomic variable has exactly one writer, eliminating lock contention.",
        "Padding head and tail to distinct 64-byte cache lines prevents MESI coherency invalidation ping-ponging.",
    ])


@figure
def ch19_mpsc_vyukov():
    fig = Fig(
        "ch19_mpsc_vyukov",
        "Figure 19-4a. Vyukov lock-free MPSC queue: wait-free producer swap, stub-node chain, and single-consumer reclamation.",
        308,
    )

    # Top row: Single Consumer (left), Transient Window note (center), Producers (right)
    cons = fig.node(24, 18, 224, 102, "purple")
    fig.tile(36, 30, "developer_board", "purple", 30)
    fig.text(74, 49, "Single Consumer", "name")
    fig.cell(36, 68, 200, 38, "purple", [("tail.next.load(Acquire)", "mono")], kind="card", r=8)

    gap = fig.node(268, 18, 248, 102, "amber")
    fig.tile(280, 30, "warning", "amber", 30)
    fig.text(318, 49, "Transient Link Window", "name")
    fig.lines(
        392,
        88,
        [
            ("between step 1 and step 2,", "small"),
            ("prev.next is null; pop() yields None", "small"),
        ],
        "middle",
        fit=(274, 510),
    )

    prod = fig.node(536, 18, 240, 102, "blue")
    fig.tile(548, 30, "bolt", "blue", 30)
    fig.text(586, 49, "Producers (P0..Pn)", "name")
    fig.cell(548, 68, 216, 38, "blue", [("head.swap(node, AcqRel)", "mono")], kind="card", r=8)

    # Middle row: Linked-list chain from tail (oldest stub) to head (newest node)
    n0 = fig.cell(24, 162, 152, 62, "purple", [("Stub (tail)", "name"), ("data: None", "mono")], kind="card", r=10)
    n1 = fig.cell(220, 162, 152, 62, "teal", [("Node 1", "name"), ("data: Some(v1)", "mono")], kind="card", r=10)
    n2 = fig.cell(416, 162, 152, 62, "teal", [("Node 2 (prev)", "name"), ("data: Some(v2)", "mono")], kind="card", r=10)
    n3 = fig.cell(624, 162, 152, 62, "blue", [("Node 3 (head)", "name"), ("data: Some(v3)", "mono")], kind="card", r=10)

    # Vertical pointer wires from Consumer -> tail and Producers -> head
    fig.wire([(100, cons.b + 2), (100, n0.y - 3)], "purple", width=2.2)
    fig.label(154, 141, "tail (free old)", "purple", "small")

    fig.wire([(700, prod.b + 2), (700, n3.y - 3)], "blue", width=2.2)
    fig.label(642, 141, "1. swap head", "blue", "small")

    # Horizontal next links
    fig.wire([(n0.r + 3, 193), (n1.x - 3, 193)], "purple", width=2.0)
    fig.label(198, 179, "next", "purple", "small")

    fig.wire([(n1.r + 3, 193), (n2.x - 3, 193)], "teal", width=2.0)
    fig.label(394, 179, "next", "teal", "small")

    fig.wire([(n2.r + 3, 193), (n3.x - 3, 193)], "amber", dash=True, width=2.2)
    fig.label(596, 173, "2. link", "amber", "small")
    fig.label(596, 213, "Release", "amber", "small")

    # Bottom invariant banner
    fig.node(
        24,
        242,
        752,
        52,
        "teal",
        [
            ("Cache-line isolation: head and tail occupy separate 64-byte cache lines.", "name"),
            ("Safe reclamation: a non-null tail.next proves the producer finished linking and no thread retains tail.", "small"),
        ],
        icon="shield",
    )

    fig.save([
        "Producers are wait-free: each push executes one atomic exchange on head followed by one Release store on prev.next.",
        "The consumer never contends on head; once tail.next is non-null, it advances tail, reclaims the old stub, and takes the payload.",
    ])


@figure
def ch19_mini_pipeline():
    fig = Fig("ch19_mini_pipeline", "Figure 19-5. Process pipeline: stdout-to-stdin redirection via a kernel pipe buffer.", 270)

    c1 = fig.node(28, 20, 210, 140, "blue")
    fig.tile(42, 34, "terminal", "blue", 34)
    fig.text(88, 56, "child 1: echo", "name")
    fig.cell(42, 80, 182, 36, "blue", [("dup2(p[1], 1)", "mono")], kind="card", r=8)
    fig.lines(133, 134, [("closes p[0]; writes stdout", "sub")], "middle", fit=(32, 234))

    pipe_box = fig.node(270, 20, 260, 140, "green")
    fig.tile(284, 34, "swap_horiz", "green", 34)
    fig.text(330, 56, "kernel pipe buffer", "name")
    fig.cell(284, 80, 232, 36, "green", [("64 KiB circular buffer", "sub")], kind="card", r=8)
    fig.lines(400, 134, [("unidirectional byte stream", "sub")], "middle", fit=(274, 526))

    c2 = fig.node(562, 20, 210, 140, "purple")
    fig.tile(576, 34, "terminal", "purple", 34)
    fig.text(622, 56, "child 2: tr", "name")
    fig.cell(576, 80, 182, 36, "purple", [("dup2(p[0], 0)", "mono")], kind="card", r=8)
    fig.lines(667, 134, [("closes p[1]; reads stdin", "sub")], "middle", fit=(566, 768))

    fig.wire([(c1.r + 3, 98), (pipe_box.x - 3, 98)], "blue", width=2.2)
    fig.wire([(pipe_box.r + 3, 98), (c2.x - 3, 98)], "purple", width=2.2)

    parent = fig.node(28, 178, 744, 70, "amber",
                      [("parent process: closes p[0] & p[1] after fork; reaps via waitpid()", "name"),
                       ("closing parent p[1] is critical: otherwise child 2 never receives EOF and deadlocks", "small")],
                      icon="engineering")

    fig.save([
        "A reader encounters EOF only when every copy of the write descriptor across all processes is closed.",
        "If the parent retains p[1] open, child 2 hangs indefinitely awaiting input after child 1 exits.",
    ])


@figure
def ch19_lru_cache():
    fig = Fig("ch19_lru_cache", "Figure 19-6. LRU cache: hash table indexing into a doubly linked recency chain.", 270)

    h_box = fig.node(28, 16, 744, 76, "blue")
    fig.tile(42, 28, "table_rows", "blue", 34)
    fig.text(88, 52, "Hash Map: O(1) Key -> Node Pointer Lookup", "name")
    fig.cell(420, 28, 100, 48, "blue", [("key: 1", "mono"), ("-> Head", "small")], kind="card", r=8)
    fig.cell(535, 28, 100, 48, "blue", [("key: 2", "mono"), ("-> Mid", "small")], kind="card", r=8)
    fig.cell(650, 28, 100, 48, "blue", [("key: 3", "mono"), ("-> Tail", "small")], kind="card", r=8)

    list_box = fig.node(28, 114, 744, 134, "teal")
    fig.tile(42, 126, "swap_horiz", "teal", 34)
    fig.text(88, 146, "Doubly Linked List: Temporal Recency Ordering", "name")
    fig.text(88, 168, "front = most recently used; back = least recently used", "sub")

    mru = fig.cell(88, 184, 130, 46, "green", [("Head (MRU)", "name"), ("Node 1 (val: A)", "mono")], kind="card", r=8)
    node_b = fig.cell(310, 184, 130, 46, "teal", [("Mid Node", "name"), ("Node 2 (val: B)", "mono")], kind="card", r=8)
    lru = fig.cell(530, 184, 130, 46, "red", [("Tail (LRU)", "name"), ("Node 3 (val: C)", "mono")], kind="card", r=8)

    fig.wire([(mru.r + 3, 203), (node_b.x - 3, 203)], "teal", width=1.8)
    fig.wire([(node_b.x - 3, 211), (mru.r + 3, 211)], "teal", width=1.8)
    fig.wire([(node_b.r + 3, 203), (lru.x - 3, 203)], "teal", width=1.8)
    fig.wire([(lru.x - 3, 211), (node_b.r + 3, 211)], "teal", width=1.8)

    fig.wire([(lru.r + 3, 207), (710, 207)], "red", width=2.2)
    fig.text(714, 211, "evict", "monob", tone="red")

    fig.save([
        "A get() hit or put() splices the referenced node to the head (MRU) in O(1) time without reallocating nodes.",
        "When capacity is exceeded, the tail node (LRU) is popped and removed from the hash map in O(1) time.",
    ])


@figure
def ch02_x86_apic():
    fig = Fig(
        "ch02_x86_apic",
        "Figure 2-5. x86-64 Interrupt Controller Hardware Topology: Legacy IO-APIC, PCIe MSI-X Bypass, and Per-Core Local APICs.",
        396,
    )

    # Left column: Hardware Interrupt Sources
    legacy = fig.node(20, 22, 188, 114, "amber")
    fig.tile(32, 34, "developer_board", "amber", 30)
    fig.text(70, 54, "Legacy Devices", "name")
    fig.lines(114, 96, [
        ("Keyboard, UART, SATA", "small"),
        ("Physical copper IRQ pins", "sub"),
        ("IRQ 0..23 -> chipset", "mono"),
    ], "middle", fit=(26, 202))

    pcie = fig.node(20, 160, 188, 126, "blue")
    fig.tile(32, 172, "bolt", "blue", 30)
    fig.text(70, 192, "PCIe Devices", "name")
    fig.lines(114, 240, [
        ("NVMe, 100GbE NIC, GPU", "small"),
        ("MSI-X: zero IRQ pins", "sub"),
        ("DMA -> 0xFEE0_xxxx", "mono"),
        ("1 vector per queue", "sub"),
    ], "middle", fit=(26, 202))

    # Middle top: Chipset IO-APIC
    ioapic = fig.node(244, 22, 220, 114, "red")
    fig.tile(256, 34, "table_rows", "red", 30)
    fig.text(294, 54, "Chipset IO-APIC", "name")
    fig.cell(256, 72, 196, 52, "red", [
        ("24 Redirection Entries", "monob"),
        ("Pin -> Vector + Core ID", "small"),
    ], kind="card", r=8)

    # Middle bottom: PCIe Fabric / Interconnect Bus Banner
    bus = fig.node(244, 160, 220, 126, "teal")
    fig.tile(256, 172, "swap_horiz", "teal", 30)
    fig.text(294, 192, "System Interconnect", "name")
    fig.lines(354, 240, [
        ("MSI-X bypasses IO-APIC", "monob"),
        ("Device writes vector directly", "small"),
        ("to target core LAPIC MMIO", "small"),
        ("eliminating shared-pin contention", "sub"),
    ], "middle", fit=(250, 458))

    # Right column: Core 0 LAPIC + Core 1 LAPIC
    core0 = fig.node(500, 18, 280, 164, "purple")
    fig.tile(512, 30, "memory", "purple", 30)
    fig.text(550, 50, "Core 0: On-Die Local APIC", "name")
    fig.cell(512, 68, 124, 48, "purple", [
        ("IRR (256-bit)", "monob"),
        ("Pending vectors", "small"),
    ], kind="card", r=7)
    fig.cell(644, 68, 124, 48, "purple", [
        ("ISR (256-bit)", "monob"),
        ("Active in-service", "small"),
    ], kind="card", r=7)
    fig.cell(512, 124, 124, 44, "green", [
        ("APIC Timer", "monob"),
        ("Preemption tick", "small"),
    ], kind="card", r=7)
    fig.cell(644, 124, 124, 44, "red", [
        ("EOI Register", "monob"),
        ("Clears ISR bit", "small"),
    ], kind="card", r=7)

    core1 = fig.node(500, 214, 280, 92, "green")
    fig.tile(512, 226, "memory", "green", 30)
    fig.text(550, 246, "Core 1: On-Die Local APIC", "name")
    fig.cell(512, 260, 256, 36, "green", [
        ("IRR | ISR | APIC Timer | EOI", "mono"),
    ], kind="card", r=7)

    # Bottom summary banner: Why two 256-bit bitmaps (IRR vs ISR) + IPIs
    note_bar = fig.node(20, 322, 760, 62, "gray")
    fig.lines(400, 353, [
        ("Arbitration: LAPIC delivers the highest pending bit in IRR that outranks the active bit in ISR.", "small"),
        ("Vectors 0..31: hardware exceptions (#PF, #GP); Vectors 32..255: OS-assigned devices, timers, IPIs.", "sub"),
    ], "middle", fit=(28, 772))

    # Wires
    fig.wire([(legacy.r + 2, 79), (ioapic.x - 2, 79)], "amber", width=2.0)
    fig.wire([(ioapic.r + 2, 79), (core0.x - 2, 79)], "red", width=2.0)
    fig.wire([(pcie.r + 2, 223), (bus.x - 2, 223)], "blue", width=2.0)
    fig.wire([(bus.r + 2, 200), (482, 200), (482, 130), (core0.x - 2, 130)], "teal", width=2.0)
    fig.wire([(bus.r + 2, 258), (core1.x - 2, 258)], "teal", width=2.0)
    # Cross-core IPI arrow between Core 0 and Core 1
    fig.wire([(560, core0.b + 2), (560, core1.y - 2)], "purple", dash=True, width=1.8, tail=True)
    fig.label(674, 198, "IPI (TLB shootdown / wakeup)", tone="purple", cls="small")

    fig.save([
        "Legacy peripherals use shared copper pins routed through the chipset IO-APIC Redirection Table.",
        "Modern PCIe devices bypass the IO-APIC with MSI-X memory writes directly to a target core's Local APIC MMIO register.",
    ])


@figure
def ch02_arm_gic():
    fig = Fig(
        "ch02_arm_gic",
        "Figure 2-6. ARM64 Generic Interrupt Controller (GICv3 / GICv4): Distributor, ITS, Per-Core Redistributor, and CPU Interface.",
        366,
    )

    # Column 1: Sources
    spi_src = fig.node(20, 22, 176, 86, "amber")
    fig.tile(32, 34, "developer_board", "amber", 28)
    fig.text(68, 52, "SoC Peripherals", "name")
    fig.lines(108, 84, [
        ("SPI: IDs 32..1019", "monob"),
        ("Shared wired lines", "sub"),
    ], "middle", fit=(26, 190))

    lpi_src = fig.node(20, 126, 176, 92, "blue")
    fig.tile(32, 138, "bolt", "blue", 28)
    fig.text(68, 156, "PCIe MSI-X", "name")
    fig.lines(108, 190, [
        ("LPI: IDs 8192+", "monob"),
        ("Message-based DMA", "sub"),
    ], "middle", fit=(26, 190))

    priv_src = fig.node(20, 236, 176, 108, "green")
    fig.tile(32, 248, "timer", "green", 28)
    fig.text(68, 266, "Per-Core Local", "name")
    fig.lines(108, 308, [
        ("SGI: IDs 0..15 (IPIs)", "mono"),
        ("PPI: IDs 16..31", "mono"),
        ("(ARM Generic Timer)", "sub"),
    ], "middle", fit=(26, 190))

    # Column 2: GICD (Distributor) & ITS
    gicd = fig.node(232, 22, 168, 86, "red")
    fig.tile(244, 34, "call_split", "red", 28)
    fig.text(280, 52, "Distributor", "name")
    fig.lines(316, 84, [
        ("GICD (SoC-wide)", "monob"),
        ("Routes SPIs to cores", "sub"),
    ], "middle", fit=(238, 394))

    its = fig.node(232, 126, 168, 92, "teal")
    fig.tile(244, 138, "table_rows", "teal", 28)
    fig.text(280, 156, "GIC ITS", "name")
    fig.lines(316, 190, [
        ("Translation Service", "monob"),
        ("DeviceID -> LPI + Core", "sub"),
    ], "middle", fit=(238, 394))

    # Column 3: Per-Core Redistributor (GICR)
    gicr = fig.node(436, 22, 168, 322, "purple")
    fig.tile(448, 36, "layers", "purple", 30)
    fig.text(486, 56, "Redistributor", "name")
    fig.text(520, 82, "GICR (1 per core)", "monob", "middle", tone="purple")
    fig.cell(448, 98, 144, 62, "red", [
        ("SPI Queue", "monob"),
        ("From GICD", "small"),
    ], kind="card", r=7)
    fig.cell(448, 172, 144, 62, "teal", [
        ("LPI Table (RAM)", "monob"),
        ("From ITS", "small"),
    ], kind="card", r=7)
    fig.cell(448, 246, 144, 82, "green", [
        ("SGI + PPI State", "monob"),
        ("Core-private timer", "small"),
        ("and IPI delivery", "small"),
    ], kind="card", r=7)

    # Column 4: CPU Interface + Core
    cpuif = fig.node(638, 22, 142, 322, "blue")
    fig.tile(650, 36, "memory", "blue", 30)
    fig.text(688, 56, "Core N", "name")
    fig.text(709, 84, "CPU Interface", "monob", "middle", tone="blue")
    fig.cell(648, 102, 122, 66, "blue", [
        ("ICC_IAR1_EL1", "mono"),
        ("Acknowledge ID", "small"),
    ], kind="card", r=7)
    fig.cell(648, 182, 122, 66, "purple", [
        ("VBAR_EL1", "mono"),
        ("Jump to IRQ stub", "small"),
    ], kind="card", r=7)
    fig.cell(648, 262, 122, 66, "red", [
        ("ICC_EOIR1_EL1", "mono"),
        ("Signal EOI", "small"),
    ], kind="card", r=7)

    # Wires
    fig.wire([(spi_src.r + 2, 65), (gicd.x - 2, 65)], "amber", width=2.0)
    fig.wire([(gicd.r + 2, 65), (gicr.x - 2, 65)], "red", width=2.0)
    fig.wire([(lpi_src.r + 2, 172), (its.x - 2, 172)], "blue", width=2.0)
    fig.wire([(its.r + 2, 172), (gicr.x - 2, 172)], "teal", width=2.0)
    fig.wire([(priv_src.r + 2, 290), (gicr.x - 2, 290)], "green", width=2.0)
    fig.wire([(gicr.r + 2, 135), (cpuif.x - 2, 135)], "purple", width=2.2)

    fig.save([
        "ARM64 separates SoC-wide shared routing (GICD + ITS) from per-core arbitration (GICR) so interrupt delivery scales to hundreds of cores.",
        "GICv3 exposes the CPU Interface through fast architectural system registers (ICC_*) rather than slower MMIO reads.",
    ])


@figure
def ch02_idt_trapframe():
    fig = Fig(
        "ch02_idt_trapframe",
        "Figure 2-7. x86-64 Hardware Vector Dispatch: IDTR Lookup, TSS Kernel Stack Switch, and Trapframe Construction.",
        396,
    )

    # Left top: IDTR + IDT Table
    idt = fig.node(20, 20, 360, 176, "blue")
    fig.tile(32, 32, "table_rows", "blue", 30)
    fig.text(70, 52, "IDTR -> Interrupt Descriptor Table (IDT)", "name")
    fig.text(32, 74, "256 entries x 16 bytes (Gate Descriptors in kernel RAM)", "sub")
    fig.cell(32, 86, 336, 30, "gray", [("IDT[0..31]: CPU Exceptions (#DE, #GP, #PF)", "mono")], kind="card", r=6)
    fig.cell(32, 122, 336, 62, "blue", [
        ("IDT[v] (e.g. vector 0x30: NVMe MSI-X)", "monob"),
        ("64-bit ISR addr | CS=Ring 0 | Interrupt Gate (IF=0) | IST", "small"),
    ], kind="card", r=7)

    # Left bottom: TSS Stack Switch
    tss = fig.node(20, 218, 360, 158, "amber")
    fig.tile(32, 230, "shield", "amber", 30)
    fig.text(70, 250, "Per-Core Task State Segment (TSS)", "name")
    fig.lines(200, 286, [
        ("Why switch stacks? User RSP may be corrupt or unmapped.", "small"),
    ], "middle", fit=(28, 372))
    fig.cell(32, 306, 160, 56, "amber", [
        ("TSS.rsp0", "monob"),
        ("Per-thread Ring 0 stack", "small"),
    ], kind="card", r=7)
    fig.cell(204, 306, 164, 56, "red", [
        ("TSS.ist[1..7]", "monob"),
        ("Private #DF / #NMI stack", "small"),
    ], kind="card", r=7)

    # Right column: Kernel Stack Trapframe (high addr top -> low addr bottom)
    stack = fig.node(424, 20, 356, 356, "purple")
    fig.tile(436, 32, "layers", "purple", 30)
    fig.text(474, 52, "Kernel Stack Trapframe (Ring 0)", "name")
    fig.text(436, 74, "High address (top of kernel stack: TSS.rsp0)", "sub")

    hw_rows = [
        ("SS (User Stack Segment)", "amber"),
        ("User RSP (Saved User Stack Ptr)", "amber"),
        ("RFLAGS (Saved IF, ZF, CF...)", "amber"),
        ("CS (Previous CPL = 3)", "amber"),
        ("User RIP (Resume Address)", "amber"),
        ("Error Code (optional: #PF, #GP)", "red"),
    ]
    y = 86
    for label_txt, tone in hw_rows:
        fig.cell(438, y, 328, 28, tone, [(label_txt, "mono")], kind="card", r=6)
        y += 32

    fig.text(602, 288, "Pushed atomically by CPU silicon", "sub", "middle", tone="amber")
    fig.cell(438, 298, 328, 48, "teal", [
        ("Software Entry Stub: struct pt_regs", "monob"),
        ("Pushes RAX, RBX, RCX, RDX, RSI, RDI, RBP, R8..R15", "small"),
    ], kind="card", r=7)
    fig.text(602, 362, "iretq pops hardware frame atomically back to Ring 3", "sub", "middle", tone="purple")

    # Wires connecting left to right
    fig.wire([(idt.r + 2, 152), (stack.x - 2, 152)], "blue", width=2.0)
    fig.wire([(tss.r + 2, 322), (402, 322), (402, 98), (stack.x - 2, 98)], "amber", width=2.0)

    fig.save([
        "On a Ring 3 -> Ring 0 interrupt, CPU hardware switches RSP to TSS.rsp0 and pushes the 5-word return frame before running 1 instruction of kernel code.",
        "On ARM64, silicon stores the interrupted PC and flags in ELR_EL1 and SPSR_EL1 while switching SP_EL0 to SP_EL1 automatically.",
    ])


@figure
def ch16_ept_walk():
    fig = Fig(
        "ch16_ept_walk",
        "Figure 16-2. Two-Stage Hardware Virtualization (Intel EPT / AMD NPT): Guest Page Walk Nested Inside Host Page Walk.",
        356,
    )

    # Top row: Stage 1 (Guest OS)
    gva = fig.node(20, 24, 150, 96, "blue")
    fig.tile(32, 36, "apps", "blue", 28)
    fig.text(68, 54, "Guest App", "name")
    fig.lines(95, 90, [
        ("Guest Virtual Addr", "small"),
        ("GVA (48-bit)", "monob"),
    ], "middle", fit=(26, 164))

    gwalk = fig.node(210, 24, 248, 96, "purple")
    fig.tile(222, 36, "layers", "purple", 28)
    fig.text(258, 54, "Stage 1: Guest Page Table", "name")
    fig.lines(334, 90, [
        ("Guest CR3 (managed by Guest OS)", "small"),
        ("GVA -> Guest Physical (GPA)", "mono"),
    ], "middle", fit=(216, 452))

    # Bottom row: Stage 2 (Hypervisor EPT)
    ept = fig.node(210, 156, 248, 114, "amber")
    fig.tile(222, 168, "shield", "amber", 28)
    fig.text(258, 186, "Stage 2: Hypervisor EPT", "name")
    fig.lines(334, 232, [
        ("EPTP (controlled by Host Hypervisor)", "small"),
        ("GPA -> Host Physical (HPA)", "mono"),
        ("Invoked for every guest level + data", "sub"),
    ], "middle", fit=(216, 452))

    # Right column: Physical Host DRAM
    dram = fig.node(500, 24, 280, 246, "green")
    fig.tile(512, 38, "memory", "green", 30)
    fig.text(550, 58, "Physical Host DRAM", "name")
    fig.cell(512, 80, 256, 62, "purple", [
        ("Guest Page Table Frames", "monob"),
        ("4 Guest levels x 4 EPT walks", "small"),
    ], kind="card", r=7)
    fig.cell(512, 154, 256, 62, "green", [
        ("Target Guest Data Frame", "monob"),
        ("Final GPA -> HPA (+4 EPT walks)", "small"),
    ], kind="card", r=7)
    fig.text(640, 244, "Cold TLB miss: up to 24 RAM reads", "monob", "middle", tone="red")

    # Bottom takeaway bar
    bar = fig.node(20, 290, 760, 52, "teal")
    fig.lines(400, 316, [
        ("Hardware Mitigations: TLB caches GVA -> HPA directly (1 cycle); VPID/ASID tags avoid flushing TLBs on VM-Exit.", "small"),
    ], "middle", fit=(28, 772))

    # Wires
    fig.wire([(gva.r + 2, 72), (gwalk.x - 2, 72)], "blue", width=2.0)
    fig.wire([(334, gwalk.b + 2), (334, ept.y - 2)], "purple", width=2.0, tail=True)
    fig.label(408, 138, "each GPA lookup", tone="purple", cls="small")
    fig.wire([(ept.r + 2, 185), (dram.x - 2, 185)], "amber", width=2.0)
    fig.wire([(gwalk.r + 2, 100), (dram.x - 2, 100)], "purple", dash=True, width=1.8)

    fig.save([
        "A cold nested page walk multiplies 4 guest levels by 4 EPT levels plus 4 EPT lookups for the final data frame (up to 24 DRAM reads vs. 4 native).",
        "Using 2 MiB huge pages in both guest and host EPT collapses the 2D walk drastically and expands TLB coverage.",
    ])


@figure
def ch10_signal_masks():
    fig = Fig("ch10_signal_masks", "Figure 10-2. Per-thread pending and blocked signal bitmasks: deliverable = pending & ~blocked.", 316)

    # Bit-cell helper for 32-bit standard POSIX signal mask
    cols = [
        ("1",  "HUP",  "0", "0", "0", 52),
        ("2",  "INT",  "1", "0", "1", 52),
        ("9",  "KILL", "0", "0", "0", 52),
        ("10", "USR1", "1", "1", "0", 54),
        ("15", "TERM", "0", "0", "0", 54),
        ("17", "CHLD", "1", "0", "1", 54),
        ("19", "STOP", "0", "0", "0", 54),
        ("··", "··",   "··","··","··", 62),
        ("31", "SYS",  "0", "0", "0", 52),
    ]
    x0 = 266
    # Column headers (signal numbers & names)
    cx = x0
    for num, name, _, _, _, w in cols:
        fig.text(cx + w / 2, 18, num, "small", "middle", fit=(cx - 2, cx + w + 2))
        fig.text(cx + w / 2, 34, name, "small", "middle", tone="red" if name in ("KILL", "STOP") else None, fit=(cx - 2, cx + w + 2))
        cx += w

    def draw_row(y, title, sub, tone, idx_in_col):
        fig.lines(x0 - 14, y + 20, [(title, "name"), (sub, "small")], "end", fit=(24, x0 - 10))
        total_w = sum(c[5] for c in cols)
        fig.rect(x0, y, total_w, 40, f"c-{tone}", r=7)
        cx = x0
        for i, col in enumerate(cols):
            val, w = col[idx_in_col], col[5]
            if i > 0:
                fig.rule(cx, y + 3, cx, y + 37, tone, width=1.0)
            if val == "1":
                fig.rect(cx + 3, y + 3, w - 6, 34, f"m-{tone}", r=5)
            fig.text(cx + w / 2, y + 24, val, "monob" if val != "··" else "small", "middle",
                     tone=tone if val == "1" else None, fit=(cx - 2, cx + w + 2))
            cx += w

    draw_row(48,  "pending",     "set on arrival",    "amber", 2)
    draw_row(106, "blocked",     "sigprocmask()",     "purple", 3)
    fig.rule(x0, 160, x0 + sum(c[5] for c in cols), 160, "gray", width=1.4)
    draw_row(172, "deliverable", "pending & ~blocked","green", 4)

    # Callout strip explaining coalescing & uncatchable signals
    fig.node(28, 232, 360, 74, "amber", [
        ("Coalescing (1 bit per signal)", "name"),
        ("5 SIGCHLD arrivals still set one bit (17 = 1);", "small"),
        ("handler must loop waitpid(-1, ..., WNOHANG).", "small"),
    ], kind="tonal", r=10)

    fig.node(412, 232, 360, 74, "red", [
        ("SIGKILL (9) & SIGSTOP (19)", "name"),
        ("Kernel ignores attempts to set bits 9 or 19", "small"),
        ("in blocked; process control stays unconditional.", "small"),
    ], kind="tonal", r=10)

    fig.save([
        "Standard POSIX signals (1..31) use a single bit per signal number rather than a queue, so repeated arrivals coalesce into one pending bit.",
        "Here SIGUSR1 (10) is pending but deferred because bit 10 is masked in blocked; SIGINT (2) and SIGCHLD (17) are deliverable on return to Ring 3.",
    ])


@figure
def ch12_durability_path():
    fig = Fig("ch12_durability_path", "Figure 12-3. Write-to-durability path across volatile RAM and the 4-step crash-safe atomic rename protocol.", 352)

    # Top panel: Volatile vs Non-Volatile write path
    fig.heading(28, 16, "1. write() returns at volatile RAM; only fsync() flushes to stable media")

    b1 = fig.node(28, 34, 152, 92, "blue", [
        ("User Buffer", "name"),
        ("write(fd, buf, n)", "mono"),
        ("returns here", "small"),
    ], layout="center", kind="card", r=10)

    b2 = fig.node(214, 34, 186, 92, "amber", [
        ("Kernel Page Cache", "name"),
        ("volatile DRAM", "sub"),
        ("lost on power cut", "small"),
    ], layout="center", kind="tonal", r=10)

    b3 = fig.node(434, 34, 156, 92, "purple", [
        ("Metadata Journal", "name"),
        ("write-ahead log", "sub"),
        ("fsync() barrier", "small"),
    ], layout="center", kind="card", r=10)

    b4 = fig.node(624, 34, 148, 92, "green", [
        ("NVMe / SSD", "name"),
        ("stable media", "sub"),
        ("flush ACK", "small"),
    ], layout="center", kind="mid", r=10)

    fig.wire([(b1.r + 2, b1.cy), (b2.x - 2, b2.cy)], "blue", width=2.0)
    fig.wire([(b2.r + 2, b2.cy), (b3.x - 2, b3.cy)], "purple", width=2.0)
    fig.wire([(b3.r + 2, b3.cy), (b4.x - 2, b4.cy)], "green", width=2.0)

    # Dashed boundary separating volatile RAM from durable storage
    fig.rule(417, 26, 417, 138, "red", width=1.6, dash="5 4")
    fig.text(417, 154, "power-loss boundary (fsync required to cross)", "small", "middle", tone="red")

    # Bottom panel: 4-step crash-safe atomic file replacement
    fig.heading(28, 196, "2. crash-safe atomic file replacement protocol")

    steps = [
        (28,  "blue",   "1. write temp",  "write(tmp_fd, ...)",  "new payload in", "config.tmp"),
        (218, "purple", "2. fsync temp",  "fsync(tmp_fd)",       "flush data &",   "temp inode"),
        (408, "teal",   "3. rename()",    "rename(tmp, cfg)",    "atomic swap of", "directory entry"),
        (598, "green",  "4. fsync dir",   "fsync(dir_fd)",       "persist updated","parent directory"),
    ]
    s_boxes = []
    for x, tone, title, call, l1, l2 in steps:
        sb = fig.cell(x, 214, 174, 114, tone, [
            (title, "name"),
            (call, "mono"),
            (l1, "small"),
            (l2, "small"),
        ], kind="tonal" if tone != "green" else "mid", r=10)
        s_boxes.append(sb)

    for lb, rb, tone in zip(s_boxes[:-1], s_boxes[1:], ["blue", "purple", "teal"]):
        fig.wire([(lb.r + 2, lb.cy), (rb.x - 2, rb.cy)], tone, width=2.0)

    fig.save([
        "A successful write(2) only copies bytes into the kernel page cache in volatile DRAM; fsync(2) flushes dirty data and metadata across the power-loss boundary.",
        "Crash-safe updates must fsync the temporary file before atomic rename() and then fsync the parent directory so the new directory entry survives a crash.",
    ])


@figure
def ch13_poll_vs_epoll():
    fig = Fig("ch13_poll_vs_epoll", "Figure 13-2. Stateless poll() O(N) full-array scan versus stateful epoll / kqueue O(K) ready-queue delivery.", 348)

    # Left column: poll() O(N)
    fig.node(28, 10, 358, 326, "amber", kind="tonal", r=12)
    fig.text(207, 34, "stateless: poll() · O(N) per wait", "name", "middle", tone="amber")

    p1 = fig.node(46, 52, 322, 68, "amber", [
        ("User Space: pollfd[N] array", "name"),
        ("copy all N descriptors into Ring 0 on every call", "small"),
    ], layout="center", kind="card", r=8)

    p2 = fig.node(46, 148, 322, 74, "amber", [
        ("Kernel: linear scan of all N sockets", "name"),
        ("poll each fd; register wait-queue hooks", "small"),
        ("N = 50,000 idle sockets scanned every loop", "small"),
    ], layout="center", kind="card", r=8)

    p3 = fig.node(46, 250, 322, 68, "red", [
        ("User Space: scan all N revents", "name"),
        ("walk 50,000 entries to find K = 10 active", "small"),
    ], layout="center", kind="card", r=8, text_tone="red")

    fig.wire([(p1.cx, p1.b + 2), (p2.cx, p2.y - 2)], "amber", width=2.0)
    fig.wire([(p2.cx, p2.b + 2), (p3.cx, p3.y - 2)], "red", width=2.0)

    # Right column: epoll / kqueue O(K)
    fig.node(414, 10, 358, 326, "green", kind="tonal", r=12)
    fig.text(593, 34, "stateful: epoll / kqueue · O(K) ready", "name", "middle", tone="green")

    e1 = fig.node(432, 52, 322, 68, "blue", [
        ("Register once: epoll_ctl() / kevent()", "name"),
        ("kernel stores N sockets in red-black tree", "small"),
    ], layout="center", kind="card", r=8)

    e2 = fig.node(432, 148, 322, 74, "teal", [
        ("NIC Interrupt → O(1) Ready List", "name"),
        ("packet arrival appends active socket directly", "small"),
        ("idle sockets are never scanned", "small"),
    ], layout="center", kind="card", r=8)

    e3 = fig.node(432, 250, 322, 68, "green", [
        ("epoll_wait() returns K ready events", "name"),
        ("copies & dispatches only K = 10 active fds", "small"),
    ], layout="center", kind="mid", r=8)

    fig.wire([(e1.cx, e1.b + 2), (e2.cx, e2.y - 2)], "blue", width=2.0)
    fig.wire([(e2.cx, e2.b + 2), (e3.cx, e3.y - 2)], "green", width=2.0)

    fig.save([
        "Because poll() is stateless, both user space and the kernel pay O(N) work proportional to total open connections on every iteration.",
        "Stateful epoll and kqueue keep the N-descriptor interest set inside the kernel and wake the loop with only the K sockets that actually received events.",
    ])


@figure
def ch15_session_hierarchy():
    fig = Fig("ch15_session_hierarchy", "Figure 15-2. Unix session, process group, and controlling terminal hierarchy before and after detachment.", 316)

    # Left: Before detachment (attached to interactive shell session)
    fig.node(28, 10, 358, 294, "amber", kind="tonal", r=12)
    fig.text(207, 34, "before: interactive shell session", "name", "middle", tone="amber")

    tty = fig.node(48, 52, 318, 48, "red", [
        ("Controlling Terminal (/dev/ttys001)", "name"),
        ("sends SIGHUP on logout, SIGINT on Ctrl-C", "small"),
    ], layout="center", kind="card", r=8, text_tone="red")

    s1 = fig.node(48, 122, 318, 164, "amber", kind="card", r=10)
    fig.text(207, 144, "Session SID = 100 (leader: bash)", "name", "middle", tone="amber")
    fig.cell(64, 160, 136, 108, "gray", [
        ("PGID 100", "name"),
        ("PID 100", "mono"),
        ("bash shell", "small"),
    ], kind="tonal", r=8)
    fig.cell(214, 160, 136, 108, "amber", [
        ("PGID 200", "name"),
        ("PID 200", "mono"),
        ("launched proc", "small"),
    ], kind="mid", r=8)
    fig.wire([(tty.cx, tty.b + 2), (s1.cx, s1.y - 2)], "red", width=2.0)

    # Right: After fork -> setsid -> fork
    fig.node(414, 10, 358, 294, "green", kind="tonal", r=12)
    fig.text(593, 34, "after: fork() → setsid() → fork()", "name", "middle", tone="green")

    notty = fig.node(434, 52, 318, 48, "gray", [
        ("No Controlling Terminal", "name"),
        ("isolated from shell SIGHUP / SIGINT", "small"),
    ], layout="center", kind="dashed", r=8)

    s2 = fig.node(434, 122, 318, 164, "green", kind="card", r=10)
    fig.text(593, 144, "New Session SID = 201 · PGID = 201", "name", "middle", tone="green")
    fig.cell(450, 160, 136, 108, "gray", [
        ("PID 201", "mono"),
        ("session leader", "small"),
        ("(exits)", "small"),
    ], kind="dashed", r=8)
    fig.cell(600, 160, 136, 108, "green", [
        ("PID 202", "monob"),
        ("daemon", "name"),
        ("non-leader", "small"),
    ], kind="mid", r=8)
    fig.wire([(588, 214), (598, 214)], "green", width=1.8)

    fig.save([
        "The first fork() ensures the child is not a process group leader so setsid() succeeds and creates a new session with no controlling terminal.",
        "The second fork() exits session leader PID 201 so the daemon (PID 202) can never inadvertently re-acquire a controlling terminal by opening a TTY.",
    ])


@figure
def ch17_mesi_states():
    fig = Fig("ch17_mesi_states", "Figure 17-2. MESI cache-coherency four-state protocol per 64-byte cache line.", 312)

    m_box = fig.node(54,  28,  296, 106, "red", [
        ("M · Modified", "name"),
        ("dirty copy, owned exclusively", "sub"),
        ("DRAM is stale; must write back", "small"),
    ], icon="edit_note", kind="tonal", r=12, icon_size=30)

    e_box = fig.node(450, 28,  296, 106, "green", [
        ("E · Exclusive", "name"),
        ("clean copy, owned exclusively", "sub"),
        ("local store upgrades E → M silently", "small"),
    ], icon="lock", kind="tonal", r=12, icon_size=30)

    s_box = fig.node(450, 186, 296, 106, "blue", [
        ("S · Shared", "name"),
        ("clean copy in 1+ sibling caches", "sub"),
        ("store requires RFO invalidation", "small"),
    ], icon="layers", kind="tonal", r=12, icon_size=30)

    i_box = fig.node(54,  186, 296, 106, "gray", [
        ("I · Invalid", "name"),
        ("line absent or invalidated", "sub"),
        ("next access misses to bus / DRAM", "small"),
    ], icon="block", kind="card", r=12, icon_size=30)

    # Clean transitions without overlap
    fig.wire([(e_box.x - 2, 74), (m_box.r + 2, 74)], "red", width=2.0)
    fig.label(400, 62, "local write", tone="red", cls="small")

    fig.wire([(i_box.r + 2, 238), (s_box.x - 2, 238)], "blue", width=2.0)
    fig.label(400, 226, "read (shared)", tone="blue", cls="small")

    fig.wire([(s_box.x - 2, 206), (m_box.r + 2, 114)], "amber", width=2.0)
    fig.label(400, 158, "write (RFO inv)", tone="amber", cls="small")

    fig.wire([(m_box.cx, m_box.b + 2), (i_box.cx, i_box.y - 2)], "gray", dash=True, width=1.8)
    fig.label(m_box.cx, 160, "remote RFO", tone="gray", cls="small")

    fig.wire([(e_box.cx, e_box.b + 2), (s_box.cx, s_box.y - 2)], "blue", dash=True, width=1.8)
    fig.label(e_box.cx, 160, "remote read", tone="blue", cls="small")

    fig.save([
        "Writing to a Shared (S) cache line forces a Read-For-Ownership (RFO) broadcast across the interconnect to transition every sibling core's copy to Invalid (I).",
        "Under false sharing, two cores alternate RFO invalidations on the same 64-byte line, bouncing it continuously between Modified (M) and Invalid (I).",
    ])


@figure
def ch18_flamegraph():
    fig = Fig("ch18_flamegraph", "Figure 18-2. Anatomy of a CPU flame graph: Y-axis is call-stack depth; X-axis is sample proportion.", 316)

    # Y-axis arrow on left
    fig.wire([(46, 268), (46, 42)], "gray", width=1.8)
    fig.text(32, 155, "stack depth (Y)", "small", "middle", rotate=-90)

    # Flame graph stacked horizontal bars (bottom = main, top = leaf on-CPU)
    # Row 0 (bottom): main() 100% (x=76..768, w=692)
    fig.cell(76, 232, 692, 34, "gray", [("main() · 100% of samples", "monob")], kind="tonal", r=5)

    # Row 1: handle_request() 76% (w=526) | background_gc() 24% (w=162)
    fig.cell(76, 194, 526, 34, "blue", [("handle_request() · 76%", "monob")], kind="mid", r=5)
    fig.cell(606, 194, 162, 34, "teal", [("bg_flush() · 24%", "mono")], kind="mid", r=5)

    # Row 2: parse_json() 46% (w=318) | query_index() 30% (w=204) | write() 24% (w=162)
    fig.cell(76, 156, 318, 34, "amber", [("parse_json() · 46%", "monob")], kind="mid", r=5)
    fig.cell(398, 156, 204, 34, "purple", [("query_index() · 30%", "mono")], kind="mid", r=5)
    fig.cell(606, 156, 162, 34, "teal", [("fsync() · 24%", "mono")], kind="tonal", r=5)

    # Row 3 (top plateaus = hot leaf functions): utf8_validate() 38% (w=262) | alloc() 8% (w=52) | btree_probe() 26% (w=178)
    fig.cell(76, 118, 262, 34, "red", [("utf8_validate() · 38%", "monob")], kind="mid", r=5)
    fig.cell(342, 118, 52, 34, "amber", [("alloc", "small")], kind="tonal", r=5)
    fig.cell(398, 118, 178, 34, "purple", [("btree_probe() · 26%", "mono")], kind="tonal", r=5)

    # Callout pointing to the wide hot plateau
    fig.node(100, 26, 368, 56, "red", [
        ("wide flat top plateau = primary CPU bottleneck", "name"),
        ("utf8_validate() runs directly on-CPU in 38% of samples", "small"),
    ], layout="center", kind="card", r=8, text_tone="red")
    fig.wire([(207, 84), (207, 116)], "red", width=2.0)

    # X-axis arrow at bottom
    fig.wire([(76, 286), (768, 286)], "gray", width=1.8)
    fig.text(422, 304, "proportion of total profiler samples (sorted alphabetically, not chronological time)", "small", "middle")

    fig.save([
        "Read a flame graph from bottom to top to trace callers, and scan the top edges for wide plateaus representing leaf functions consuming the most CPU cycles.",
        "Because frames are merged alphabetically by function name, horizontal width measures total CPU share rather than execution order.",
    ])


@figure
def ch02_cache_blocks():
    fig = Fig("ch02_cache_blocks", "Figure 2-3. Multi-core cache hierarchy and inside a 64-byte set-associative cache line block.", 396)

    # Panel 1: Multi-Core Cache Hierarchy (Core 0 + Core 1 -> Shared L3 -> DRAM)
    fig.heading(28, 16, "1. multi-core cache hierarchy (private L1/L2 per core, shared L3, off-chip DRAM)")

    # Core 0
    fig.node(28, 30, 356, 118, "blue", kind="tonal", r=10)
    fig.text(206, 48, "Core 0 (private caches)", "name", "middle", tone="blue")
    fig.cell(42, 58, 158, 34, "blue", [("L1i · 32 KiB (~1 ns)", "small")], kind="card", r=6)
    fig.cell(212, 58, 158, 34, "blue", [("L1d · 32 KiB (~1 ns)", "small")], kind="card", r=6)
    fig.cell(42, 102, 328, 34, "purple", [("L2 Unified · 512 KiB–2 MiB (~4 ns)", "small")], kind="mid", r=6)

    # Core 1
    fig.node(416, 30, 356, 118, "teal", kind="tonal", r=10)
    fig.text(594, 48, "Core 1 (private caches)", "name", "middle", tone="teal")
    fig.cell(430, 58, 158, 34, "teal", [("L1i · 32 KiB (~1 ns)", "small")], kind="card", r=6)
    fig.cell(600, 58, 158, 34, "teal", [("L1d · 32 KiB (~1 ns)", "small")], kind="card", r=6)
    fig.cell(430, 102, 328, 34, "purple", [("L2 Unified · 512 KiB–2 MiB (~4 ns)", "small")], kind="mid", r=6)

    # Shared L3 + DRAM strip
    l3 = fig.cell(28, 174, 444, 40, "amber", [("Shared L3 / Last-Level Cache (16–128 MiB · ~15 ns)", "body")], kind="mid", r=8)
    dram = fig.cell(506, 174, 266, 40, "red", [("Main DRAM (64+ GiB · ~80 ns)", "body")], kind="mid", r=8)

    fig.wire([(206, 150), (206, 172)], "purple", width=2.0)
    fig.wire([(594, 150), (594, 162), (380, 162), (380, 172)], "purple", width=2.0)
    fig.wire([(l3.r + 2, l3.cy), (dram.x - 2, dram.cy)], "red", width=2.0)

    # Panel 2: Physical Address Split + Real 64-Byte Cache Line Blocks
    fig.heading(28, 246, "2. inside an L1d cache set: physical address indexing into 64-byte cache line blocks")

    # Address bit-cell bar: | Tag [51:12] | Set Index [11:6] | Offset [5:0] |
    fig.cell(28, 262, 336, 36, "blue", [("Tag · bits [51:12] (identifies line)", "small")], kind="mid", r=6)
    fig.cell(370, 262, 198, 36, "purple", [("Set Index · bits [11:6]", "small")], kind="mid", r=6)
    fig.cell(574, 262, 198, 36, "green", [("Byte Offset · bits [5:0] (64 B)", "small")], kind="mid", r=6)

    # Concrete Cache Line Block drawn with | V | D | Tag | B0 | B1 | B2 | ··· | B62 | B63 |
    cells = [
        ("V", 32, "teal"),
        ("D", 32, "amber"),
        ("Tag (40b)", 116, "blue"),
        ("B0", 54, "green"),
        ("B1", 54, "green"),
        ("B2", 54, "green"),
        ("B3", 54, "green"),
        ("· · · 64-byte cache line · · ·", 240, "green"),
        ("B62", 54, "green"),
        ("B63", 54, "green"),
    ]
    # Check width: 32+32+116+54*6+240 = 180 + 324 + 240 = 744! Exact (28..772)!
    cx = 28
    y_blk = 324
    fig.rect(28, y_blk, 744, 42, "c-green", r=7)
    for idx, (lbl, w, tone) in enumerate(cells):
        if idx < 3:
            fig.rect(cx, y_blk, w, 42, f"m-{tone}", r=6 if idx == 0 else 0)
        if idx > 0:
            fig.rule(cx, y_blk + 3, cx, y_blk + 39, tone, width=1.1)
        cls = "monob" if "·" not in lbl else "small"
        fig.text(cx + w / 2, y_blk + 25, lbl, cls, "middle", fit=(cx - 2, cx + w + 2))
        cx += w

    fig.wire([(196, 300), (196, 322)], "blue", width=1.8)
    fig.wire([(469, 300), (469, 322)], "purple", width=1.8)
    fig.wire([(673, 300), (673, 322)], "green", width=1.8)

    fig.text(400, 386, "Every DRAM miss fetches all 64 contiguous bytes (B0..B63) together; 6 offset bits (2^6 = 64) select the target byte.", "small", "middle")

    fig.save([
        "Hardware transfers memory in 64-byte cache lines (B0..B63), tagged with Valid (V), Dirty (D), and upper Tag bits inside each set-associative cache way.",
        "Sequential array scans hit B1..B63 in L1 (~1 ns) after one miss; concurrent writes by two cores to bytes inside the same 64-byte block trigger false sharing.",
    ])


@figure
def ch06_memory_orderings():
    """Figure 6-5. Visual intuition for atomic memory orderings: reordering walls & x86-64/ARM64 instructions."""
    fig = Fig(
        "ch06_memory_orderings",
        "Figure 6-5. Atomic memory orderings: reordering barriers and emitted x86-64 / ARM64 instructions.",
        402,
    )

    cols = [
        {
            "x": 20, "tone": "gray", "name": "Relaxed",
            "sub": "Atomicity only",
            "above": "prior load / store",
            "op": "fetch_add(Relaxed)",
            "below": "later load / store",
            "wall": "none",
            "rule": "Ops move freely",
            "x86": "x86: MOV / LOCK XADD",
            "arm": "ARM: LDR / STR / LDADD",
        },
        {
            "x": 212, "tone": "blue", "name": "Acquire (Load)",
            "sub": "One-way floor",
            "above": "prior ops (may sink)",
            "op": "load(Acquire)",
            "below": "BLOCKED from hoisting",
            "wall": "below",
            "rule": "Nothing floats UP",
            "x86": "x86: plain MOV (TSO)",
            "arm": "ARM: LDAR",
        },
        {
            "x": 404, "tone": "green", "name": "Release (Store)",
            "sub": "One-way ceiling",
            "above": "BLOCKED from sinking",
            "op": "store(1, Release)",
            "below": "later ops (may hoist)",
            "wall": "above",
            "rule": "Nothing sinks DOWN",
            "x86": "x86: plain MOV (TSO)",
            "arm": "ARM: STLR",
        },
        {
            "x": 596, "tone": "purple", "name": "SeqCst",
            "sub": "Global total order",
            "above": "BLOCKED both ways",
            "op": "store(1, SeqCst)",
            "below": "Drains Store Buffer",
            "wall": "both",
            "rule": "Full 2-way fence",
            "x86": "x86: XCHG / MFENCE",
            "arm": "ARM: STLR + LDAR",
        },
    ]

    w = 184
    for c in cols:
        x = c["x"]
        t = c["tone"]
        fig.rect(x, 12, w, 298, f"c-{t}", r=10)
        fig.rect(x + 8, 20, w - 16, 40, f"m-{t}", r=7)
        fig.text(x + w / 2, 37, c["name"], "name", "middle", fit=(x + 12, x + w - 12))
        fig.text(x + w / 2, 52, c["sub"], "small", "middle", fit=(x + 12, x + w - 12))

        # Prior ops box
        fig.rect(x + 12, 68, w - 24, 28, "card", r=6)
        fig.text(x + w / 2, 86, c["above"], "small", "middle", fit=(x + 16, x + w - 16))

        # Atomic op bar in middle
        fig.rect(x + 10, 128, w - 20, 32, f"m-{t}", r=6)
        fig.text(x + w / 2, 148, c["op"], "monob", "middle", fit=(x + 14, x + w - 14))

        # Later ops box
        fig.rect(x + 12, 192, w - 24, 28, "card", r=6)
        fig.text(x + w / 2, 210, c["below"], "small", "middle", fit=(x + 16, x + w - 16))

        # Visual barrier walls & reordering arrows
        if c["wall"] == "none":
            fig.wire([(x + 56, 99), (x + 56, 124)], "green", width=1.6, dash="3,2")
            fig.wire([(x + 128, 189), (x + 128, 164)], "green", width=1.6, dash="3,2")
        elif c["wall"] == "below":
            fig.wire([(x + 56, 99), (x + 56, 124)], "green", width=1.6, dash="3,2")
            fig.rule(x + 14, 170, x + w - 14, 170, "red", width=3.2)
            fig.text(x + w / 2, 184, "BARRIER (no hoist)", "small", "middle", fit=(x + 14, x + w - 14))
        elif c["wall"] == "above":
            fig.rule(x + 14, 118, x + w - 14, 118, "red", width=3.2)
            fig.text(x + w / 2, 111, "BARRIER (no sink)", "small", "middle", fit=(x + 14, x + w - 14))
            fig.wire([(x + 128, 189), (x + 128, 164)], "green", width=1.6, dash="3,2")
        else:
            fig.rule(x + 14, 118, x + w - 14, 118, "red", width=3.2)
            fig.rule(x + 14, 170, x + w - 14, 170, "red", width=3.2)
            fig.text(x + w / 2, 111, "NO SINK", "small", "middle", fit=(x + 14, x + w - 14))
            fig.text(x + w / 2, 184, "NO HOIST", "small", "middle", fit=(x + 14, x + w - 14))

        # Rule + ISA instruction strip
        fig.text(x + w / 2, 240, c["rule"], "name", "middle", fit=(x + 12, x + w - 12))
        fig.rect(x + 10, 252, w - 20, 48, "card", r=6)
        fig.text(x + w / 2, 271, c["x86"], "small", "middle", fit=(x + 12, x + w - 12))
        fig.text(x + w / 2, 290, c["arm"], "small", "middle", fit=(x + 12, x + w - 12))

    # Bottom handshake strip: Release -> Acquire synchronizes-with
    fig.rect(20, 324, 760, 58, "c-amber", r=10)
    fig.text(400, 341, "Release-Acquire Handshake: How Two Cores Publish Data Safely Without SeqCst", "name", "middle")
    fig.rect(34, 350, 286, 24, "m-green", r=5)
    fig.text(177, 366, "Core 0: data=42; ready.store(1, Release)", "small", "middle", fit=(38, 316))
    fig.rect(468, 350, 298, 24, "m-blue", r=5)
    fig.text(617, 366, "Core 1: while !ready.load(Acquire){}; read(data)", "small", "middle", fit=(472, 762))
    fig.wire([(324, 362), (464, 362)], "amber", width=2.4)
    fig.text(394, 358, "synchronizes-with", "small", "middle", fit=(326, 462))

    fig.save([
        "Acquire acts as a one-way floor (later reads cannot hoist above it); Release acts as a one-way ceiling (prior writes cannot sink below it); SeqCst imposes both walls plus a Store-Buffer drain.",
        "On x86-64 TSO, Acquire and Release compile to plain MOV instructions, whereas ARM64 emits explicit LDAR and STLR barriers.",
    ])


def main():
    prefix = sys.argv[1] if len(sys.argv) > 1 else ""
    drawn = 0
    for function in FIGURES:
        if not function.__name__.startswith(prefix):
            continue
        function()
        drawn += 1
    print(f"drew {drawn} figures")


if __name__ == "__main__":
    main()
