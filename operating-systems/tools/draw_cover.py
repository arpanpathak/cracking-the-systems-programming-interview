"""Generates the front cover (src/art/cover.svg) for
Operating Systems: A Hands-On Approach.

Design language: Swiss-Grid / Material Engineering Monograph schematic.
Clean editorial typography, precision architectural drafting grid, real Material
hardware icons, orthogonal circuit buses, and automated bounding-box verification.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import figkit

OUT = ROOT / "src" / "art" / "cover.svg"


def build_cover() -> str:
    W, H = 960, 1280
    out: list[str] = []

    def add(s: str):
        out.append(s)

    add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" height="100%" role="img" aria-label="Operating Systems: A Hands-On Approach — Front Cover">')
    add("""  <defs>
    <pattern id="grid-minor" width="24" height="24" patternUnits="userSpaceOnUse">
      <path d="M 24 0 L 0 0 0 24" fill="none" stroke="#ECEFF4" stroke-width="0.8"/>
    </pattern>
    <pattern id="grid-major" width="120" height="120" patternUnits="userSpaceOnUse">
      <rect width="120" height="120" fill="url(#grid-minor)"/>
      <path d="M 120 0 L 0 0 0 120" fill="none" stroke="#E0E5EC" stroke-width="1.2"/>
    </pattern>
    <marker id="arr-blue" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto">
      <path d="M 0 1.5 L 9 5 L 0 8.5 z" fill="#1A73E8"/>
    </marker>
    <marker id="arr-amber" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto">
      <path d="M 0 1.5 L 9 5 L 0 8.5 z" fill="#E37400"/>
    </marker>
    <marker id="arr-green" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto">
      <path d="M 0 1.5 L 9 5 L 0 8.5 z" fill="#188038"/>
    </marker>
    <marker id="arr-purple" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto">
      <path d="M 0 1.5 L 9 5 L 0 8.5 z" fill="#7627BB"/>
    </marker>
    <marker id="arr-teal" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6.5" markerHeight="6.5" orient="auto">
      <path d="M 0 1.5 L 9 5 L 0 8.5 z" fill="#007B83"/>
    </marker>
  </defs>
  <style>
    .sans { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
    .mono { font-family: "SF Mono", SFMono-Regular, ui-monospace, Menlo, Consolas, monospace; }
    .kicker { font-size: 12.5px; font-weight: 700; letter-spacing: 2.2px; fill: #1A73E8; }
    .spec { font-size: 11.5px; font-weight: 600; fill: #5F6368; }
    .h1 { font-size: 56px; font-weight: 800; letter-spacing: -1.2px; fill: #111827; }
    .h2 { font-size: 26px; font-weight: 500; letter-spacing: -0.3px; fill: #374151; }
    .sec-tag { font-size: 11.5px; font-weight: 700; letter-spacing: 1.4px; }
    .card-title { font-size: 13.8px; font-weight: 700; fill: #1F2937; }
    .card-sub { font-size: 12px; font-weight: 500; fill: #4B5563; }
    .code-line { font-size: 11.8px; font-weight: 600; fill: #1F2937; }
    .code-muted { font-size: 11.2px; font-weight: 500; fill: #5F6368; }
    .pill-txt { font-size: 11.5px; font-weight: 700; }
    .author-lbl { font-size: 11px; font-weight: 700; letter-spacing: 2px; fill: #6B7280; }
    .author-name { font-size: 22px; font-weight: 800; letter-spacing: 0.8px; fill: #111827; }
  </style>
""")

    def icon(name: str, x: float, y: float, size: float, color: str):
        inner = figkit.icon_markup(name)
        scale = size / 24.0
        add(f'  <g transform="translate({x:.1f} {y:.1f}) scale({scale:.4f})" fill="{color}">{inner}</g>')

    # 1. Outer Architectural Sheet & Swiss Drafting Grid
    add(f'  <rect width="{W}" height="{H}" rx="12" fill="#FAFBFD"/>')
    add(f'  <rect x="24" y="24" width="{W-48}" height="{H-48}" rx="8" fill="url(#grid-major)" stroke="#D0D7E2" stroke-width="1.5"/>')

    # Architectural corner registration marks
    for cx, cy in [(40, 40), (W - 40, 40), (40, H - 40), (W - 40, H - 40)]:
        add(f'  <path d="M {cx-8} {cy} L {cx+8} {cy} M {cx} {cy-8} L {cx} {cy+8}" stroke="#9AA5B4" stroke-width="1.2"/>')

    # 2. Top Monograph Masthead (y = 48..296)
    add(f'  <rect x="48" y="52" width="{W-96}" height="236" rx="8" fill="#FFFFFF" stroke="#D0D7E2" stroke-width="1.5"/>')
    # Top accent bar segmented into the 6 architectural palette colors
    seg_w = (W - 96) / 6.0
    for idx, col in enumerate(["#1A73E8", "#E37400", "#188038", "#7627BB", "#007B83", "#D93025"]):
        add(f'  <rect x="{48 + idx*seg_w:.1f}" y="52" width="{seg_w + 0.5:.1f}" height="6" fill="{col}"/>')

    add('  <text x="76" y="92" class="sans kicker">SYSTEMS ARCHITECTURE &amp; KERNEL ENGINEERING MONOGRAPH</text>')
    add(f'  <rect x="{W-244}" y="74" width="172" height="26" rx="13" fill="#E8F0FE" stroke="#1A73E8" stroke-width="1"/>')
    add(f'  <text x="{W-158}" y="91" text-anchor="middle" class="mono pill-txt" fill="#1A73E8">C++20 · RUST 2024</text>')

    add('  <text x="76" y="156" class="sans h1">Operating Systems</text>')
    add('  <text x="76" y="194" class="sans h2">A Hands-On Approach to Kernel &amp; Systems Engineering</text>')

    add(f'  <line x1="76" y1="216" x2="{W-76}" y2="216" stroke="#E5E9F0" stroke-width="1.2"/>')

    # Four specification badges in the masthead footer
    specs = [
        ("developer_board", "#1A73E8", "#E8F0FE", "ISA: x86-64 &amp; ARM64"),
        ("layers",          "#188038", "#E6F4EA", "19 CHAPTERS · 4 PARTS"),
        ("terminal",        "#7627BB", "#F3E8FD", "54 VERIFIED PROGRAMS"),
        ("memory",          "#007B83", "#E4F7FB", "41 VECTOR SCHEMATICS"),
    ]
    bw = 194
    bgap = (W - 152 - 4 * bw) / 3.0
    for i, (ic, fg, bg, label) in enumerate(specs):
        bx = 76 + i * (bw + bgap)
        by = 234
        add(f'  <rect x="{bx:.1f}" y="{by}" width="{bw}" height="34" rx="6" fill="{bg}" stroke="{fg}" stroke-width="1"/>')
        icon(ic, bx + 10, by + 7, 20, fg)
        add(f'  <text x="{bx + 36:.1f}" y="{by + 21}" class="mono pill-txt" fill="{fg}">{label}</text>')

    # =========================================================================
    # 3. LAYER I: USER-MODE EXECUTION (RING 3 / EL0)  (y = 312..506)
    # =========================================================================
    add(f'  <rect x="48" y="312" width="{W-96}" height="194" rx="8" fill="#FFFFFF" stroke="#1A73E8" stroke-width="1.6"/>')
    add(f'  <rect x="48" y="312" width="{W-96}" height="34" rx="8" fill="#E8F0FE"/>')
    add(f'  <rect x="48" y="338" width="{W-96}" height="8" fill="#E8F0FE"/>')
    icon("apps", 66, 319, 20, "#1A73E8")
    add('  <text x="94" y="334" class="sans sec-tag" fill="#1A73E8">LAYER I · USER-MODE ADDRESS SPACE (RING 3 / EL0)</text>')
    add(f'  <text x="{W-68}" y="334" text-anchor="end" class="mono code-muted">User VA: 0x0000_0000_0000_0000 .. 0x0000_7FFF_FFFF_FFFF</text>')

    # Three equal cards in Layer I
    cw = 264
    cgap = (W - 136 - 3 * cw) / 2.0
    u_cards = [
        (
            "person", "#1A73E8", "#E8F0FE",
            "Processes &amp; Threads",
            "fork() · execve() · waitpid()",
            "NEW → READY → RUNNING → ZOMBIE",
            "Joinable TCB · TLS · Red Zone",
        ),
        (
            "view_module", "#7627BB", "#F3E8FD",
            "Lock-Free &amp; Arena Memory",
            "LruCache&lt;K,V&gt; · SPSC Ring · Heap",
            "alignas(64) Acquire / Release",
            "O(1) Arena Splice · Zero Syscall",
        ),
        (
            "loop", "#007B83", "#E4F7FB",
            "Event Loops &amp; Daemons",
            "kqueue · epoll_wait · launchd",
            "EVFILT_READ · EVFILT_PROC",
            "O(K_ready) Event Loop Dispatch",
        ),
    ]
    u_centers = []
    for i, (ic, fg, bg, title, l1, l2, l3) in enumerate(u_cards):
        cx = 68 + i * (cw + cgap)
        cy = 360
        u_centers.append(cx + cw / 2.0)
        fit_hdr = f"{cx+50:.1f},{cx+cw-12:.1f}"
        fit_body = f"{cx+16:.1f},{cx+cw-12:.1f}"
        add(f'  <rect x="{cx:.1f}" y="{cy}" width="{cw}" height="130" rx="6" fill="#FAFBFD" stroke="#D0D7E2" stroke-width="1.2"/>')
        add(f'  <rect x="{cx:.1f}" y="{cy}" width="5" height="130" rx="2.5" fill="{fg}"/>')
        add(f'  <rect x="{cx+16:.1f}" y="{cy+12}" width="28" height="28" rx="6" fill="{bg}"/>')
        icon(ic, cx + 20, cy + 16, 20, fg)
        add(f'  <text x="{cx+52:.1f}" y="{cy+31}" class="sans card-title" data-fit="{fit_hdr}">{title}</text>')
        add(f'  <line x1="{cx+16:.1f}" y1="{cy+48}" x2="{cx+cw-14:.1f}" y2="{cy+48}" stroke="#E5E9F0" stroke-width="1"/>')
        add(f'  <text x="{cx+18:.1f}" y="{cy+69}" class="mono code-line" fill="{fg}" data-fit="{fit_body}">{l1}</text>')
        add(f'  <text x="{cx+18:.1f}" y="{cy+91}" class="mono code-muted" data-fit="{fit_body}">{l2}</text>')
        add(f'  <text x="{cx+18:.1f}" y="{cy+113}" class="sans card-sub" data-fit="{fit_body}">{l3}</text>')

    # Downward bus arrows from Layer I to Hardware Trap Gate
    trap_labels = ["syscall / svc #0", "#PF / #GP Trap", "kevent / io_uring"]
    for i, ux in enumerate(u_centers):
        add(f'  <line x1="{ux:.1f}" y1="506" x2="{ux:.1f}" y2="538" stroke="#E37400" stroke-width="2" marker-end="url(#arr-amber)"/>')
        add(f'  <rect x="{ux + 8:.1f}" y="511" width="118" height="20" rx="4" fill="#FEF7E0" stroke="#F6AD01" stroke-width="0.8"/>')
        add(f'  <text x="{ux + 67:.1f}" y="525" text-anchor="middle" class="mono" font-size="11" font-weight="600" fill="#B06000">{trap_labels[i]}</text>')

    # =========================================================================
    # 4. HARDWARE PRIVILEGE & EXCEPTION BOUNDARY BAR (y = 542..594)
    # =========================================================================
    add(f'  <rect x="48" y="542" width="{W-96}" height="52" rx="8" fill="#FEF7E0" stroke="#E37400" stroke-width="1.8"/>')
    add('  <rect x="64" y="553" width="30" height="30" rx="6" fill="#E37400"/>')
    icon("bolt", 69, 558, 20, "#FFFFFF")
    add('  <text x="106" y="565" class="sans" font-size="13.5" font-weight="800" letter-spacing="1.2" fill="#B06000" data-fit="106,756">HARDWARE PRIVILEGE &amp; INTERRUPT BOUNDARY · RING 3 → RING 0 (EL0 → EL1)</text>')
    add('  <text x="106" y="584" class="mono code-muted" data-fit="106,756">CPU pushes SS, RSP, RFLAGS, CS, RIP to TSS.rsp0 · Dispatches IDT[vec] / VBAR_EL1</text>')
    add(f'  <rect x="{W-188}" y="555" width="124" height="26" rx="5" fill="#FFFFFF" stroke="#E37400" stroke-width="1.2"/>')
    add(f'  <text x="{W-126}" y="572" text-anchor="middle" class="mono pill-txt" fill="#B06000">SYSRET / ERET</text>')

    # Downward bus arrows from Trap Gate to Layer II
    for ux in u_centers:
        add(f'  <line x1="{ux:.1f}" y1="594" x2="{ux:.1f}" y2="622" stroke="#188038" stroke-width="2" marker-end="url(#arr-green)"/>')

    # =========================================================================
    # 5. LAYER II: KERNEL SUPERVISOR SUBSYSTEMS (RING 0 / EL1) (y = 626..920)
    # =========================================================================
    add(f'  <rect x="48" y="626" width="{W-96}" height="294" rx="8" fill="#FFFFFF" stroke="#188038" stroke-width="1.6"/>')
    add(f'  <rect x="48" y="626" width="{W-96}" height="34" rx="8" fill="#E6F4EA"/>')
    add(f'  <rect x="48" y="652" width="{W-96}" height="8" fill="#E6F4EA"/>')
    icon("shield", 66, 633, 20, "#188038")
    add('  <text x="94" y="648" class="sans sec-tag" fill="#188038">LAYER II · KERNEL SUPERVISOR SUBSYSTEMS (CPL = 0 / EL1)</text>')
    add(f'  <text x="{W-68}" y="648" text-anchor="end" class="mono code-muted">VA: 0xFFFF_8000_0000_0000 .. 0xFFFF_FFFF_FFFF_FFFF</text>')

    # Top row inside Kernel: 3 subsystem modules aligned with u_cards
    k_cards = [
        (
            "schedule", "#188038", "#E6F4EA",
            "Scheduler &amp; Sync",
            "CFS / EEVDF vruntime RB-Tree",
            "futex(WAIT/WAKE) · Seqlock",
            "Top-Half hardirq / softirq EOI",
        ),
        (
            "table_rows", "#1A73E8", "#E8F0FE",
            "Virtual Memory &amp; MMU",
            "CR3 / TTBR0 4-Level Page Walk",
            "COW Fork · Demand Zero · Guard",
            "TLB PCID/ASID &amp; IPI Shootdowns",
        ),
        (
            "dns", "#007B83", "#E4F7FB",
            "VFS, Page Cache &amp; Sockets",
            "fd → file → dentry → inode",
            "Page Cache · WAL · fsync()",
            "Zero-Copy DMA · TCP Automaton",
        ),
    ]
    for i, (ic, fg, bg, title, l1, l2, l3) in enumerate(k_cards):
        cx = 68 + i * (cw + cgap)
        cy = 672
        fit_hdr = f"{cx+50:.1f},{cx+cw-12:.1f}"
        fit_body = f"{cx+16:.1f},{cx+cw-12:.1f}"
        add(f'  <rect x="{cx:.1f}" y="{cy}" width="{cw}" height="126" rx="6" fill="#FAFBFD" stroke="#D0D7E2" stroke-width="1.2"/>')
        add(f'  <rect x="{cx:.1f}" y="{cy}" width="5" height="126" rx="2.5" fill="{fg}"/>')
        add(f'  <rect x="{cx+16:.1f}" y="{cy+12}" width="28" height="28" rx="6" fill="{bg}"/>')
        icon(ic, cx + 20, cy + 16, 20, fg)
        add(f'  <text x="{cx+52:.1f}" y="{cy+31}" class="sans card-title" data-fit="{fit_hdr}">{title}</text>')
        add(f'  <line x1="{cx+16:.1f}" y1="{cy+46}" x2="{cx+cw-14:.1f}" y2="{cy+46}" stroke="#E5E9F0" stroke-width="1"/>')
        add(f'  <text x="{cx+18:.1f}" y="{cy+67}" class="mono code-line" fill="{fg}" data-fit="{fit_body}">{l1}</text>')
        add(f'  <text x="{cx+18:.1f}" y="{cy+89}" class="mono code-muted" data-fit="{fit_body}">{l2}</text>')
        add(f'  <text x="{cx+18:.1f}" y="{cy+110}" class="sans card-sub" data-fit="{fit_body}">{l3}</text>')

    # Bottom row inside Kernel: Full-width Hand-Calculated 4-Level Radix Page Walk Pipeline (y = 812..906)
    add(f'  <rect x="68" y="812" width="{W-136}" height="94" rx="6" fill="#F8FAFC" stroke="#1A73E8" stroke-width="1.2"/>')
    add('  <text x="86" y="833" class="sans" font-size="11.5" font-weight="700" letter-spacing="0.8" fill="#1A73E8">48-BIT CANONICAL RADIX PAGE WALK PIPELINE</text>')
    add(f'  <text x="{W-86}" y="833" text-anchor="end" class="mono code-muted">VA 0x0000_7FFF_ABCD_EF01 → PA 0x0000_0000_8A42_0F01</text>')

    stages = [
        ("CR3 Base",   "0x1000_0000", "#5F6368", "#F1F3F4"),
        ("L4 · PML4",  "idx 255 (9b)", "#1A73E8", "#E8F0FE"),
        ("L3 · PDPT",  "idx 510 (9b)", "#1A73E8", "#E8F0FE"),
        ("L2 · PD",    "idx 350 (9b)", "#1A73E8", "#E8F0FE"),
        ("L1 · PT",    "idx 223 (9b)", "#7627BB", "#F3E8FD"),
        ("Offset",     "+ 0xF01 (12b)", "#E37400", "#FEF7E0"),
        ("4 KiB Frame","PFN 0x8A420",   "#188038", "#E6F4EA"),
    ]
    sw = 100
    sgap = (W - 172 - len(stages) * sw) / (len(stages) - 1)
    for i, (st_title, st_sub, fg, bg) in enumerate(stages):
        sx = 86 + i * (sw + sgap)
        sy = 844
        add(f'  <rect x="{sx:.1f}" y="{sy}" width="{sw}" height="50" rx="5" fill="{bg}" stroke="{fg}" stroke-width="1.2"/>')
        add(f'  <text x="{sx + sw/2:.1f}" y="{sy + 21}" text-anchor="middle" class="sans" font-size="12" font-weight="700" fill="{fg}">{st_title}</text>')
        add(f'  <text x="{sx + sw/2:.1f}" y="{sy + 39}" text-anchor="middle" class="mono" font-size="11" font-weight="600" fill="#1F2937">{st_sub}</text>')
        if i < len(stages) - 1:
            ax1 = sx + sw + 2
            ax2 = sx + sw + sgap - 3
            add(f'  <line x1="{ax1:.1f}" y1="{sy+25}" x2="{ax2:.1f}" y2="{sy+25}" stroke="#1A73E8" stroke-width="1.6" marker-end="url(#arr-blue)"/>')

    # Downward bus arrows from Layer II to Layer III (Hardware Silicon)
    for ux in u_centers:
        add(f'  <line x1="{ux:.1f}" y1="920" x2="{ux:.1f}" y2="948" stroke="#7627BB" stroke-width="2" marker-end="url(#arr-purple)"/>')

    # =========================================================================
    # 6. LAYER III: SILICON MICROARCHITECTURE & UNIFIED MEMORY FABRIC (y = 952..1128)
    # =========================================================================
    add(f'  <rect x="48" y="952" width="{W-96}" height="176" rx="8" fill="#FFFFFF" stroke="#7627BB" stroke-width="1.6"/>')
    add(f'  <rect x="48" y="952" width="{W-96}" height="34" rx="8" fill="#F3E8FD"/>')
    add(f'  <rect x="48" y="978" width="{W-96}" height="8" fill="#F3E8FD"/>')
    icon("memory", 66, 959, 20, "#7627BB")
    add('  <text x="94" y="974" class="sans sec-tag" fill="#7627BB">LAYER III · SILICON &amp; UNIFIED MEMORY FABRIC (UMA / NUMA)</text>')
    add(f'  <text x="{W-68}" y="974" text-anchor="end" class="mono code-muted">MESI / MOESI · 64B Cache Lines · PCIe MSI-X</text>')

    hw_cards = [
        (
            "developer_board", "#7627BB", "#F3E8FD",
            "Out-of-Order SMP Cores",
            "RIP/PC · RSP/SP · RFLAGS/PSTATE",
            "L1d / L2 / L3 + Store Buffers",
        ),
        (
            "memory", "#1A73E8", "#E8F0FE",
            "Apple Silicon UMA &amp; NPU",
            "Zero-Copy CPU / GPU / ANE Fabric",
            "Coherent Shared Physical DRAM",
        ),
        (
            "save", "#D93025", "#FCE8E6",
            "APIC / GICv4 &amp; NVMe DMA",
            "Ring Buffers · Scatter-Gather",
            "APFS / ext4 · NIC TX/RX Queues",
        ),
    ]
    for i, (ic, fg, bg, title, l1, l2) in enumerate(hw_cards):
        cx = 68 + i * (cw + cgap)
        cy = 998
        fit_hdr = f"{cx+50:.1f},{cx+cw-12:.1f}"
        fit_body = f"{cx+16:.1f},{cx+cw-12:.1f}"
        add(f'  <rect x="{cx:.1f}" y="{cy}" width="{cw}" height="112" rx="6" fill="#FAFBFD" stroke="#D0D7E2" stroke-width="1.2"/>')
        add(f'  <rect x="{cx:.1f}" y="{cy}" width="5" height="112" rx="2.5" fill="{fg}"/>')
        add(f'  <rect x="{cx+16:.1f}" y="{cy+12}" width="28" height="28" rx="6" fill="{bg}"/>')
        icon(ic, cx + 20, cy + 16, 20, fg)
        add(f'  <text x="{cx+52:.1f}" y="{cy+31}" class="sans card-title" data-fit="{fit_hdr}">{title}</text>')
        add(f'  <line x1="{cx+16:.1f}" y1="{cy+46}" x2="{cx+cw-14:.1f}" y2="{cy+46}" stroke="#E5E9F0" stroke-width="1"/>')
        add(f'  <text x="{cx+18:.1f}" y="{cy+69}" class="mono code-line" fill="{fg}" data-fit="{fit_body}">{l1}</text>')
        add(f'  <text x="{cx+18:.1f}" y="{cy+93}" class="sans card-sub" data-fit="{fit_body}">{l2}</text>')

    # =========================================================================
    # 7. EDITORIAL COLOPHON & AUTHOR FOOTER (y = 1146..1232)
    # =========================================================================
    add(f'  <rect x="48" y="1146" width="{W-96}" height="82" rx="8" fill="#FFFFFF" stroke="#D0D7E2" stroke-width="1.5"/>')
    add('  <rect x="48" y="1146" width="8" height="82" rx="4" fill="#1A73E8"/>')
    add('  <text x="76" y="1174" class="sans author-lbl">AUTHOR</text>')
    add('  <text x="76" y="1204" class="sans author-name">ARPAN PATHAK</text>')

    add(f'  <line x1="310" y1="1162" x2="310" y2="1212" stroke="#E5E9F0" stroke-width="1.2"/>')
    add('  <text x="334" y="1178" class="sans" font-size="13.5" font-weight="700" fill="#1F2937">First-Principles Systems Engineering &amp; Senior Interview Reference</text>')
    add('  <text x="334" y="1202" class="mono code-muted">Processes · Concurrency · Virtual Memory · VFS · kqueue/io_uring · Daemons · UMA</text>')

    add("</svg>\n")
    return "\n".join(out)


def audit_cover(svg_text: str):
    import xml.etree.ElementTree as ET
    root = ET.fromstring(svg_text)
    boxes = []
    for el in root.iter():
        if el.tag.split("}")[-1] == "text":
            txt = "".join(el.itertext()).strip()
            if not txt:
                continue
            x = float(el.attrib.get("x", 0))
            y = float(el.attrib.get("y", 0))
            anchor = el.attrib.get("text-anchor", "start")
            cls = el.attrib.get("class", "")
            fsize = float(el.attrib.get("font-size", 0))
            lspace = float(el.attrib.get("letter-spacing", 0))
            if not fsize:
                if "h1" in cls: fsize = 56
                elif "h2" in cls: fsize = 26
                elif "author-name" in cls: fsize = 22
                elif "card-title" in cls: fsize = 13.8
                elif "kicker" in cls: fsize = 12.5; lspace = 2.2
                elif "sec-tag" in cls: fsize = 11.5; lspace = 1.4
                elif "code-line" in cls: fsize = 11.8
                elif "code-muted" in cls: fsize = 11.2
                else: fsize = 12
            is_mono = "mono" in cls
            char_w = fsize * (0.61 if is_mono else 0.57) + max(0.0, lspace)
            w = len(txt) * char_w
            x0 = {"start": x, "middle": x - w / 2, "end": x - w}[anchor]
            x1 = x0 + w
            y0 = y - fsize * 0.85
            y1 = y + fsize * 0.2
            boxes.append((txt, x0, y0, x1, y1, el.attrib.get("data-fit")))

    errors = []
    for i, (t1, x0, y0, x1, y1, fit) in enumerate(boxes):
        if x0 < 24 or x1 > 936:
            errors.append(f"Out of horizontal bounds: {t1!r} ({x0:.1f}..{x1:.1f})")
        if fit:
            low, high = map(float, fit.split(","))
            if x0 < low - 2 or x1 > high + 2:
                errors.append(f"Card fit overflow: {t1!r} ({x0:.1f}..{x1:.1f} vs {low:.1f}..{high:.1f})")
        for t2, bx0, by0, bx1, by1, _ in boxes[i + 1:]:
            if min(x1, bx1) - max(x0, bx0) > 4 and min(y1, by1) - max(y0, by0) > 3:
                errors.append(f"Overlap between {t1!r} and {t2!r}")
    if errors:
        raise SystemExit("Cover SVG Audit FAILED:\n" + "\n".join(errors))
    print(f"Cover SVG Audit Passed: {len(boxes)} text elements verified, 0 overlaps, 0 card overflows.")


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    svg = build_cover()
    audit_cover(svg)
    OUT.write_text(svg, encoding="utf-8")
    print(f"wrote {OUT} ({len(svg):,} bytes)")
