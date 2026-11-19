"""Generates the front cover (src/art/cover.svg and src/art/monograph-cover.svg)
for Operating Systems: A Hands-On Approach.

Visual theme:
- Panoramic twilight-to-dawn mountain range in the background (faceted Material
  Design alpine peaks with warm horizon glow and subtle silicon contour lines).
- Spacious open sky typography (zero cramped boxes around the title).
- Sleek Material Design POSIX Shell & Kernel Telemetry terminal in the midground.
- Glowing Unified Silicon Die & Motherboard plaza in the foreground with creative
  Material-design vector characters (Tux with a UNIX pipe, Ferris slotting a
  4 KiB page frame into the MMU, and Hex the PID 1 daemon sprite on the shell).
"""
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import figkit

OUT = ROOT / "src" / "art" / "cover.svg"
OUT_BUST = ROOT / "src" / "art" / "monograph-cover.svg"


def build_cover() -> str:
    W, H = 960, 1280
    out: list[str] = []

    def add(s: str):
        out.append(s)

    def icon(name: str, x: float, y: float, size: float, color: str):
        inner = figkit.icon_markup(name)
        scale = size / 24.0
        add(f'  <g transform="translate({x:.1f} {y:.1f}) scale({scale:.4f})" fill="{color}">{inner}</g>')

    add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="100%" height="100%" role="img" aria-label="Operating Systems: A Hands-On Approach — Front Cover">')
    add("""  <defs>
    <!-- Sky & Horizon Gradients -->
    <linearGradient id="sky-grad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#091024"/>
      <stop offset="35%" stop-color="#132247"/>
      <stop offset="68%" stop-color="#1F3B6D"/>
      <stop offset="88%" stop-color="#3B5284"/>
      <stop offset="100%" stop-color="#F59E0B" stop-opacity="0.55"/>
    </linearGradient>
    <radialGradient id="sun-glow" cx="50%" cy="46%" r="45%">
      <stop offset="0%" stop-color="#FDE68A" stop-opacity="0.75"/>
      <stop offset="35%" stop-color="#F59E0B" stop-opacity="0.32"/>
      <stop offset="70%" stop-color="#38BDF8" stop-opacity="0.10"/>
      <stop offset="100%" stop-color="#091024" stop-opacity="0"/>
    </radialGradient>
    <linearGradient id="mtn-far-l" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#60A5FA"/>
      <stop offset="100%" stop-color="#1E3A8A"/>
    </linearGradient>
    <linearGradient id="mtn-far-r" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#2563EB"/>
      <stop offset="100%" stop-color="#172554"/>
    </linearGradient>
    <linearGradient id="mtn-mid-l" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#14B8A6"/>
      <stop offset="100%" stop-color="#115E59"/>
    </linearGradient>
    <linearGradient id="mtn-mid-r" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#0D9488"/>
      <stop offset="100%" stop-color="#0F172A"/>
    </linearGradient>
    <linearGradient id="ground-grad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#0F172A"/>
      <stop offset="40%" stop-color="#0B1325"/>
      <stop offset="100%" stop-color="#070C18"/>
    </linearGradient>
    <linearGradient id="shell-bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#111827" stop-opacity="0.96"/>
      <stop offset="100%" stop-color="#0B1120" stop-opacity="0.98"/>
    </linearGradient>
    <linearGradient id="die-grad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#1E293B"/>
      <stop offset="50%" stop-color="#0F172A"/>
      <stop offset="100%" stop-color="#1E1B4B"/>
    </linearGradient>
    <filter id="mat-shadow" x="-8%" y="-8%" width="116%" height="120%">
      <feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#020617" flood-opacity="0.55"/>
    </filter>
    <filter id="soft-glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="3.5" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <style>
    .sans { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
    .mono { font-family: "SF Mono", SFMono-Regular, ui-monospace, Menlo, Consolas, monospace; }
  </style>
""")

    # =========================================================================
    # 1. SKY, STARS & SUNRISE GLOW (y = 0..640)
    # =========================================================================
    add(f'  <rect width="{W}" height="{H}" rx="16" fill="#070C18"/>')
    add(f'  <rect width="{W}" height="660" rx="16" fill="url(#sky-grad)"/>')
    add(f'  <rect width="{W}" height="660" fill="url(#sun-glow)"/>')

    # Subtle constellation / starfield in upper sky
    stars = [
        (78, 52, 1.5), (164, 38, 1.2), (285, 62, 1.6), (412, 40, 1.3),
        (560, 48, 1.8), (690, 36, 1.4), (825, 58, 1.6), (895, 42, 1.2),
        (110, 118, 1.2), (860, 112, 1.5), (65, 195, 1.4), (902, 185, 1.3),
        (140, 250, 1.2), (830, 240, 1.5),
    ]
    for sx, sy, sr in stars:
        add(f'  <circle cx="{sx}" cy="{sy}" r="{sr}" fill="#E0F2FE" opacity="0.75"/>')

    # Rising alpine sun disk behind the central mountain pass
    add('  <circle cx="480" cy="435" r="78" fill="#FDE68A" opacity="0.22"/>')
    add('  <circle cx="480" cy="435" r="46" fill="#FEF08A" opacity="0.55"/>')

    # =========================================================================
    # 2. SPACIOUS OPEN-SKY TYPOGRAPHY (y = 58..275)
    # =========================================================================
    # Top pill badge
    add('  <rect x="290" y="50" width="380" height="32" rx="16" fill="#0F172A" fill-opacity="0.72" stroke="#38BDF8" stroke-width="1.2"/>')
    add('  <circle cx="312" cy="66" r="4.5" fill="#34D399"/>')
    add('  <text x="490" y="71" text-anchor="middle" class="mono" font-size="12.5" font-weight="700" letter-spacing="1.4" fill="#E0F2FE">C++20 · RUST 2024 · x86-64 &amp; ARM64</text>')

    # Main Book Title
    add('  <text x="480" y="152" text-anchor="middle" class="sans" font-size="68" font-weight="800" letter-spacing="-1.2" fill="#FFFFFF" filter="url(#mat-shadow)">Operating Systems</text>')

    # Subtitle
    add('  <text x="480" y="198" text-anchor="middle" class="sans" font-size="27" font-weight="500" letter-spacing="0.4" fill="#7DD3FC">A Hands-On Approach</text>')

    # Clean golden horizon divider rule
    add('  <line x1="270" y1="220" x2="690" y2="220" stroke="#F59E0B" stroke-width="1.8" stroke-opacity="0.75"/>')
    add('  <circle cx="480" cy="220" r="4" fill="#FDE68A"/>')

    # Spacious descriptive sub-caption
    add('  <text x="480" y="248" text-anchor="middle" class="sans" font-size="15.5" font-weight="500" fill="#E2E8F0">From Silicon Microarchitecture &amp; Kernel Internals to Shells, Event Loops &amp; Daemons</text>')

    # =========================================================================
    # 3. LAYERED MATERIAL DESIGN MOUNTAINS (y = 290..580)
    # =========================================================================
    # Distant Left Peak (Mount Rainier / Alpine Faceted Peak)
    add('  <polygon points="0,540 0,430 115,355 235,288 375,445 440,540" fill="url(#mtn-far-l)"/>')
    # Shaded eastern facet of Left Peak
    add('  <polygon points="235,288 375,445 440,540 270,540 218,395" fill="url(#mtn-far-r)"/>')
    # Snow cap on Left Peak
    add('  <polygon points="235,288 184,321 206,338 224,324 239,344 268,325" fill="#E0F2FE" opacity="0.92"/>')

    # Distant Right Peak (Granite Spire)
    add('  <polygon points="470,540 595,365 725,276 865,390 960,445 960,540" fill="url(#mtn-far-l)"/>')
    # Shaded facet of Right Peak
    add('  <polygon points="725,276 865,390 960,445 960,540 705,540 695,382" fill="url(#mtn-far-r)"/>')
    # Snow cap on Right Peak
    add('  <polygon points="725,276 676,313 698,329 718,314 736,336 772,316" fill="#E0F2FE" opacity="0.92"/>')

    # Central Distant Peak framing the sun pass
    add('  <polygon points="330,540 480,348 630,540" fill="#1E3A8A" opacity="0.85"/>')
    add('  <polygon points="480,348 630,540 495,540" fill="#172554" opacity="0.9"/>')
    add('  <polygon points="480,348 448,386 468,396 482,382 498,398 512,386" fill="#FDE68A" opacity="0.85"/>')

    # Midground Material Teal Foothills with Silicon Trace Contours
    add('  <polygon points="0,565 0,468 155,398 335,488 510,425 685,485 835,402 960,465 960,565" fill="url(#mtn-mid-l)"/>')
    add('  <polygon points="155,398 335,488 335,565 140,565" fill="url(#mtn-mid-r)" opacity="0.55"/>')
    add('  <polygon points="510,425 685,485 685,565 495,565" fill="url(#mtn-mid-r)" opacity="0.55"/>')
    add('  <polygon points="835,402 960,465 960,565 815,565" fill="url(#mtn-mid-r)" opacity="0.55"/>')

    # Glowing circuit-trace horizon lines along the mountain foothills
    add('  <path d="M 40 495 L 155 445 L 260 495 L 390 495" fill="none" stroke="#38BDF8" stroke-width="1.5" stroke-opacity="0.45"/>')
    add('  <circle cx="155" cy="445" r="3.5" fill="#38BDF8" opacity="0.75"/>')
    add('  <path d="M 570 495 L 710 495 L 835 442 L 920 482" fill="none" stroke="#34D399" stroke-width="1.5" stroke-opacity="0.45"/>')
    add('  <circle cx="835" cy="442" r="3.5" fill="#34D399" opacity="0.75"/>')

    # Deep dark-slate valley floor (y = 535..1280)
    add(f'  <rect x="0" y="535" width="{W}" height="{H-535}" fill="url(#ground-grad)"/>')

    # Perspective Silicon Valley Grid lines on the ground plane (y = 810..1150)
    for gx in range(80, 960, 80):
        add(f'  <line x1="{gx}" y1="790" x2="{480 + (gx - 480) * 1.35:.1f}" y2="1150" stroke="#1E293B" stroke-width="1"/>')
    for gy in [820, 875, 935, 1000, 1070, 1145]:
        add(f'  <line x1="36" y1="{gy}" x2="{W-36}" y2="{gy}" stroke="#1E293B" stroke-width="1"/>')

    # =========================================================================
    # 4. COOL SHELL TERMINAL & OS TELEMETRY CONSOLE (y = 488..786)
    # =========================================================================
    add('  <rect x="64" y="488" width="832" height="296" rx="14" fill="url(#shell-bg)" stroke="#38BDF8" stroke-width="1.8" filter="url(#mat-shadow)"/>')
    # Terminal Window Header Bar
    add('  <path d="M 64 502 Q 64 488 78 488 L 882 488 Q 896 488 896 502 L 896 530 L 64 530 Z" fill="#1E293B"/>')
    add('  <line x1="64" y1="530" x2="896" y2="530" stroke="#334155" stroke-width="1.2"/>')
    # Traffic light window controls
    add('  <circle cx="90" cy="509" r="6" fill="#EF4444"/>')
    add('  <circle cx="110" cy="509" r="6" fill="#F59E0B"/>')
    add('  <circle cx="130" cy="509" r="6" fill="#10B981"/>')

    # Shell Tabs
    add('  <rect x="160" y="495" width="182" height="28" rx="6" fill="#0F172A" stroke="#38BDF8" stroke-width="1"/>')
    icon("terminal", 170, 500, 18, "#38BDF8")
    add('  <text x="194" y="514" class="mono" font-size="12" font-weight="700" fill="#E0F2FE">zsh · tty0 (Ring 3)</text>')

    add('  <rect x="352" y="495" width="178" height="28" rx="6" fill="#1E293B" stroke="#475569" stroke-width="1"/>')
    icon("memory", 362, 500, 18, "#94A3B8")
    add('  <text x="386" y="514" class="mono" font-size="12" font-weight="600" fill="#94A3B8">vm_map · 4-Level PT</text>')

    add('  <rect x="540" y="495" width="178" height="28" rx="6" fill="#1E293B" stroke="#475569" stroke-width="1"/>')
    icon("bolt", 550, 500, 18, "#F59E0B")
    add('  <text x="574" y="514" class="mono" font-size="12" font-weight="600" fill="#FDE68A">kqueue · io_uring</text>')

    # Left Console Pane: Interactive POSIX Shell Session
    add('  <text x="88" y="560" class="mono" font-size="13" font-weight="700" fill="#34D399">arpan@darwin-xnu</text>')
    add('  <text x="226" y="560" class="mono" font-size="13" font-weight="600" fill="#94A3B8">~ $</text>')
    add('  <text x="260" y="560" class="mono" font-size="13" font-weight="700" fill="#F8FAFC">fork() &amp;&amp; execve("/bin/sh", argv, envp)</text>')
    add('  <text x="88" y="584" class="mono" font-size="12" font-weight="500" fill="#7DD3FC">├─ PID 1 (launchd) ──► PID 4280 (worker) · COW pages mapped</text>')

    add('  <text x="88" y="618" class="mono" font-size="13" font-weight="700" fill="#34D399">arpan@darwin-xnu</text>')
    add('  <text x="226" y="618" class="mono" font-size="13" font-weight="600" fill="#94A3B8">~ $</text>')
    add('  <text x="260" y="618" class="mono" font-size="13" font-weight="700" fill="#F8FAFC">pagetable --walk 0x0000_7FFF_ABCD_EF01</text>')
    add('  <text x="88" y="642" class="mono" font-size="12" font-weight="500" fill="#C4B5FD">└─ CR3 0x1000_0000 → PML4[255] → PDPT[510] → PD[350] → PT[223]</text>')
    add('  <text x="88" y="664" class="mono" font-size="12" font-weight="700" fill="#FDE68A">   ✓ TLB Hit (PCID 4) · Physical Frame PA = 0x0000_0000_8A42_0F01</text>')

    add('  <text x="88" y="698" class="mono" font-size="13" font-weight="700" fill="#34D399">arpan@darwin-xnu</text>')
    add('  <text x="226" y="698" class="mono" font-size="13" font-weight="600" fill="#94A3B8">~ $</text>')
    add('  <text x="260" y="698" class="mono" font-size="13" font-weight="700" fill="#F8FAFC">kevent(kq, EVFILT_READ | EVFILT_PROC)</text>')
    add('  <rect x="572" y="685" width="9" height="16" rx="1.5" fill="#38BDF8"/>')

    # Bottom status strip inside shell
    add('  <rect x="84" y="724" width="510" height="42" rx="8" fill="#1E293B" stroke="#334155" stroke-width="1"/>')
    icon("shield", 96, 735, 20, "#F59E0B")
    add('  <text x="124" y="742" class="sans" font-size="11.5" font-weight="700" fill="#FDE68A">TRAP GATE · SYSCALL / SVC #0 · RING 3 → RING 0</text>')
    add('  <text x="124" y="758" class="mono" font-size="11" font-weight="500" fill="#94A3B8">Saves RIP/RFLAGS to TSS.rsp0 · Dispatches IDT / VBAR_EL1</text>')

    # Vertical divider inside console
    add('  <line x1="612" y1="544" x2="612" y2="766" stroke="#1E293B" stroke-width="1.5"/>')

    # Right Console Pane: 3 Clean Material Kernel Cards
    chips = [
        ("schedule", "#34D399", "#064E3B", "CFS / EEVDF Scheduler", "vruntime RB-Tree · Futex"),
        ("view_module", "#38BDF8", "#0C4A6E", "Arena &amp; Lock-Free Ring", "LruCache&lt;K,V&gt; · SPSC 64B"),
        ("lan", "#C084FC", "#3B0764", "VFS &amp; Zero-Copy I/O", "Page Cache · WAL · DMA"),
    ]
    for idx, (ic, fg, bg, t1, t2) in enumerate(chips):
        cy = 548 + idx * 74
        add(f'  <rect x="628" y="{cy}" width="248" height="62" rx="8" fill="#1E293B" stroke="{fg}" stroke-width="1.2"/>')
        add(f'  <rect x="640" y="{cy+13}" width="36" height="36" rx="8" fill="{bg}"/>')
        icon(ic, 646, cy + 19, 24, fg)
        add(f'  <text x="688" y="{cy+27}" class="sans" font-size="13" font-weight="700" fill="#F8FAFC">{t1}</text>')
        add(f'  <text x="688" y="{cy+46}" class="mono" font-size="11.2" font-weight="500" fill="{fg}">{t2}</text>')

    # =========================================================================
    # 5. CREATIVE MATERIAL CHARACTERS & UNIFIED SILICON DIE (y = 786..1138)
    # =========================================================================
    # Glowing Gold & Cyan PCB Bus Traces connecting Shell -> Silicon Die -> Characters
    add('  <path d="M 480 784 L 480 838" fill="none" stroke="#F59E0B" stroke-width="3" filter="url(#soft-glow)"/>')
    add('  <path d="M 330 784 L 330 816 L 410 816 L 410 838" fill="none" stroke="#38BDF8" stroke-width="2.2"/>')
    add('  <path d="M 630 784 L 630 816 L 550 816 L 550 838" fill="none" stroke="#34D399" stroke-width="2.2"/>')

    # Horizontal motherboard buses to Tux (left) and Ferris (right)
    add('  <path d="M 255 965 L 348 965" fill="none" stroke="#38BDF8" stroke-width="3" stroke-dasharray="6 4"/>')
    add('  <path d="M 612 965 L 705 965" fill="none" stroke="#F97316" stroke-width="3" stroke-dasharray="6 4"/>')

    # -------------------------------------------------------------------------
    # CENTERPIECE: Unified Memory & Multi-Core Silicon Die (x = 348..612, y = 838..1094)
    # -------------------------------------------------------------------------
    # Outer Ceramic Substrate & Gold Pins
    add('  <rect x="348" y="838" width="264" height="256" rx="16" fill="url(#die-grad)" stroke="#F59E0B" stroke-width="2.2" filter="url(#mat-shadow)"/>')
    for p in range(7):
        px = 376 + p * 34
        add(f'  <rect x="{px}" y="829" width="12" height="9" rx="2" fill="#F59E0B"/>')
        add(f'  <rect x="{px}" y="1094" width="12" height="9" rx="2" fill="#F59E0B"/>')
    for p in range(6):
        py = 866 + p * 36
        add(f'  <rect x="339" y="{py}" width="9" height="12" rx="2" fill="#F59E0B"/>')
        add(f'  <rect x="612" y="{py}" width="9" height="12" rx="2" fill="#F59E0B"/>')

    add('  <text x="480" y="864" text-anchor="middle" class="sans" font-size="12" font-weight="800" letter-spacing="1.4" fill="#FDE68A">UNIFIED SILICON &amp; RING 0 DIE</text>')

    # 4 Processor & Accelerator Cores inside the Die
    cores = [
        (368, 878, "#38BDF8", "#0C4A6E", "CORE 0 · SMP", "Out-of-Order ALU"),
        (486, 878, "#38BDF8", "#0C4A6E", "CORE 1 · SMP", "MESI L1d / L2"),
        (368, 954, "#34D399", "#064E3B", "MMU &amp; TLB", "4-Level Radix PT"),
        (486, 954, "#C084FC", "#3B0764", "UMA · GPU/NPU", "Zero-Copy Fabric"),
    ]
    for cx, cy, fg, bg, ct, cs in cores:
        add(f'  <rect x="{cx}" y="{cy}" width="106" height="64" rx="8" fill="{bg}" stroke="{fg}" stroke-width="1.4"/>')
        add(f'  <text x="{cx+53}" y="{cy+27}" text-anchor="middle" class="mono" font-size="11.5" font-weight="700" fill="#FFFFFF">{ct}</text>')
        add(f'  <text x="{cx+53}" y="{cy+47}" text-anchor="middle" class="sans" font-size="10.5" font-weight="500" fill="{fg}">{cs}</text>')

    # Bottom Coherent Interconnect Bar inside the Silicon Die
    add('  <rect x="368" y="1032" width="224" height="44" rx="8" fill="#0F172A" stroke="#F59E0B" stroke-width="1.2"/>')
    add('  <text x="480" y="1051" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="#FDE68A">COHERENT FABRIC · IO-APIC / GICv4</text>')
    add('  <text x="480" y="1068" text-anchor="middle" class="mono" font-size="10.2" font-weight="500" fill="#94A3B8">64B Cache Lines · NVMe &amp; NIC DMA</text>')

    # -------------------------------------------------------------------------
    # CHARACTER 1 (LEFT): Tux the Systems Penguin Engineer (x = 70..275, y = 855..1095)
    # -------------------------------------------------------------------------
    add('  <rect x="64" y="852" width="242" height="242" rx="16" fill="#0F172A" fill-opacity="0.85" stroke="#38BDF8" stroke-width="1.5" filter="url(#mat-shadow)"/>')
    # Tux Illustration (Geometric Material Vector)
    add('  <g transform="translate(185 955)">')
    # Webbed orange feet
    add('    <ellipse cx="-24" cy="64" rx="18" ry="8" fill="#F59E0B"/>')
    add('    <ellipse cx="24" cy="64" rx="18" ry="8" fill="#F59E0B"/>')
    # Torso & white belly
    add('    <ellipse cx="0" cy="14" rx="46" ry="52" fill="#1E293B" stroke="#475569" stroke-width="1.5"/>')
    add('    <ellipse cx="0" cy="20" rx="31" ry="40" fill="#F8FAFC"/>')
    # Head
    add('    <circle cx="0" cy="-38" r="32" fill="#1E293B" stroke="#475569" stroke-width="1.5"/>')
    # Cool Cyan Systems Engineer Visor / Glasses
    add('    <rect x="-24" y="-48" width="48" height="16" rx="8" fill="#0284C7" stroke="#7DD3FC" stroke-width="1.5"/>')
    add('    <circle cx="-10" cy="-40" r="3.5" fill="#E0F2FE"/>')
    add('    <circle cx="10" cy="-40" r="3.5" fill="#E0F2FE"/>')
    # Orange beak
    add('    <polygon points="-9,-29 9,-29 0,-18" fill="#F59E0B"/>')
    # Flippers holding a glowing UNIX Pipe (`pipe(fd)`)
    add('    <ellipse cx="-44" cy="12" rx="11" ry="26" transform="rotate(18 -44 12)" fill="#1E293B"/>')
    add('    <ellipse cx="44" cy="12" rx="11" ry="26" transform="rotate(-18 44 12)" fill="#1E293B"/>')
    # Glowing Green UNIX Pipe held across chest
    add('    <rect x="-36" y="18" width="72" height="18" rx="9" fill="#064E3B" stroke="#34D399" stroke-width="1.6"/>')
    add('    <text x="0" y="31" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="#6EE7B7">pipe(fd)</text>')
    add('  </g>')
    add('  <text x="185" y="1052" text-anchor="middle" class="sans" font-size="13.5" font-weight="700" fill="#F8FAFC">Kernel &amp; POSIX Pipelines</text>')
    add('  <text x="185" y="1072" text-anchor="middle" class="mono" font-size="11" font-weight="500" fill="#7DD3FC">fork · dup2 · waitpid · signals</text>')

    # -------------------------------------------------------------------------
    # CHARACTER 2 (RIGHT): Ferris the Rust Systems Crab (x = 654..896, y = 852..1094)
    # -------------------------------------------------------------------------
    add('  <rect x="654" y="852" width="242" height="242" rx="16" fill="#0F172A" fill-opacity="0.85" stroke="#F97316" stroke-width="1.5" filter="url(#mat-shadow)"/>')
    # Ferris Illustration (Geometric Material Vector)
    add('  <g transform="translate(775 952)">')
    # Crab legs
    for lx in [-46, -32, 32, 46]:
        add(f'    <path d="M {lx} 28 L {lx*1.25:.1f} 52" stroke="#EA580C" stroke-width="5" stroke-linecap="round"/>')
    # Side claws raised holding a glowing 4 KiB Memory Page Frame
    add('    <path d="M -42 0 C -62 -18 -58 -42 -36 -46" fill="none" stroke="#F97316" stroke-width="6" stroke-linecap="round"/>')
    add('    <circle cx="-36" cy="-46" r="9" fill="#FB923C"/>')
    add('    <path d="M 42 0 C 62 -18 58 -42 36 -46" fill="none" stroke="#F97316" stroke-width="6" stroke-linecap="round"/>')
    add('    <circle cx="36" cy="-46" r="9" fill="#FB923C"/>')
    # Glowing 4 KiB Page Frame held aloft between claws
    add('    <rect x="-44" y="-68" width="88" height="24" rx="6" fill="#3B0764" stroke="#C084FC" stroke-width="1.6"/>')
    add('    <text x="0" y="-52" text-anchor="middle" class="mono" font-size="10.5" font-weight="700" fill="#E9D5FF">4 KiB PTE</text>')
    # Crab shell body with cute gear spikes
    add('    <ellipse cx="0" cy="10" rx="48" ry="34" fill="#F97316" stroke="#FDBA74" stroke-width="1.5"/>')
    add('    <ellipse cx="0" cy="18" rx="34" ry="20" fill="#FB923C"/>')
    # Eye stalks
    add('    <line x1="-16" y1="-20" x2="-16" y2="-32" stroke="#EA580C" stroke-width="4" stroke-linecap="round"/>')
    add('    <line x1="16" y1="-20" x2="16" y2="-32" stroke="#EA580C" stroke-width="4" stroke-linecap="round"/>')
    add('    <circle cx="-16" cy="-34" r="7" fill="#FFFFFF"/>')
    add('    <circle cx="-16" cy="-34" r="3.5" fill="#0F172A"/>')
    add('    <circle cx="16" cy="-34" r="7" fill="#FFFFFF"/>')
    add('    <circle cx="16" cy="-34" r="3.5" fill="#0F172A"/>')
    # Friendly smile & Send+Sync badge
    add('    <path d="M -10 -2 Q 0 6 10 -2" fill="none" stroke="#7C2D12" stroke-width="2.5" stroke-linecap="round"/>')
    add('    <rect x="-36" y="12" width="72" height="17" rx="5" fill="#0F172A"/>')
    add('    <text x="0" y="24" text-anchor="middle" class="mono" font-size="9.8" font-weight="700" fill="#FDBA74">Send + Sync</text>')
    add('  </g>')
    add('  <text x="775" y="1052" text-anchor="middle" class="sans" font-size="13.5" font-weight="700" fill="#F8FAFC">Zero-Cost Memory Safety</text>')
    add('  <text x="775" y="1072" text-anchor="middle" class="mono" font-size="11" font-weight="500" fill="#FDBA74">Arena LRU · Atomics · mmap</text>')

    # -------------------------------------------------------------------------
    # CHARACTER 3 (PERCHED ON SHELL TOP-RIGHT): Hex the PID 1 Daemon Bot
    # -------------------------------------------------------------------------
    add('  <g transform="translate(838 470)">')
    # Cute rounded robot head perched on the shell top border
    add('    <line x1="0" y1="-26" x2="0" y2="-38" stroke="#F59E0B" stroke-width="2.5"/>')
    add('    <circle cx="0" cy="-41" r="4.5" fill="#34D399" filter="url(#soft-glow)"/>')
    add('    <rect x="-24" y="-26" width="48" height="32" rx="10" fill="#1E293B" stroke="#F59E0B" stroke-width="1.8"/>')
    add('    <circle cx="-9" cy="-12" r="4" fill="#38BDF8"/>')
    add('    <circle cx="9" cy="-12" r="4" fill="#38BDF8"/>')
    add('    <rect x="-14" y="-2" width="28" height="4" rx="2" fill="#34D399"/>')
    add('  </g>')

    # =========================================================================
    # 6. SPACIOUS EDITORIAL FOOTER BAR (y = 1148..1234)
    # =========================================================================
    add('  <rect x="64" y="1148" width="832" height="84" rx="14" fill="#0F172A" stroke="#334155" stroke-width="1.5" filter="url(#mat-shadow)"/>')
    add('  <rect x="64" y="1148" width="8" height="84" rx="4" fill="#38BDF8"/>')
    add('  <text x="92" y="1177" class="sans" font-size="11" font-weight="700" letter-spacing="2" fill="#7DD3FC">AUTHOR</text>')
    add('  <text x="92" y="1208" class="sans" font-size="24" font-weight="800" letter-spacing="0.8" fill="#FFFFFF">ARPAN PATHAK</text>')

    add('  <line x1="304" y1="1164" x2="304" y2="1216" stroke="#1E293B" stroke-width="1.5"/>')
    add('  <text x="326" y="1181" class="sans" font-size="14" font-weight="700" fill="#F8FAFC">19 Chapters · 54 Verified C++20 &amp; Rust 2024 Programs · 41 Vector Diagrams</text>')
    add('  <text x="326" y="1205" class="mono" font-size="11.2" font-weight="500" fill="#94A3B8">Processes · Concurrency · Virtual Memory · File Systems · Networking · Daemons</text>')

    add("</svg>\n")
    return "\n".join(out)


def audit_cover(svg_text: str):
    root = ET.fromstring(svg_text)
    boxes = []

    def walk(el, dx=0.0, dy=0.0):
        import re
        tr = el.attrib.get("transform", "")
        m = re.search(r"translate\(\s*([-\d.]+)[,\s]+([-\d.]+)\s*\)", tr)
        if m:
            dx += float(m.group(1))
            dy += float(m.group(2))
        if el.tag.split("}")[-1] == "text":
            txt = "".join(el.itertext()).strip()
            if txt:
                x = float(el.attrib.get("x", 0)) + dx
                y = float(el.attrib.get("y", 0)) + dy
                anchor = el.attrib.get("text-anchor", "start")
                cls = el.attrib.get("class", "")
                fsize = float(el.attrib.get("font-size", 12))
                lspace = float(el.attrib.get("letter-spacing", 0))
                is_mono = "mono" in cls
                char_w = fsize * (0.60 if is_mono else 0.54) + max(0.0, lspace)
                w = len(txt) * char_w
                x0 = {"start": x, "middle": x - w / 2, "end": x - w}[anchor]
                x1 = x0 + w
                y0 = y - fsize * 0.85
                y1 = y + fsize * 0.2
                boxes.append((txt, x0, y0, x1, y1))
        for child in el:
            walk(child, dx, dy)

    walk(root)
    errors = []
    for i, (t1, x0, y0, x1, y1) in enumerate(boxes):
        if x0 < 30 or x1 > 930:
            errors.append(f"Out of horizontal bounds: {t1!r} ({x0:.1f}..{x1:.1f})")
        for t2, bx0, by0, bx1, by1 in boxes[i + 1:]:
            if min(x1, bx1) - max(x0, bx0) > 4 and min(y1, by1) - max(y0, by0) > 3:
                errors.append(f"Overlap between {t1!r} and {t2!r}")
    if errors:
        raise SystemExit("Cover SVG Audit FAILED:\n" + "\n".join(errors))
    print(f"Cover SVG Audit Passed: {len(boxes)} text elements verified, 0 overlaps, 0 out-of-bounds.")


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    svg = build_cover()
    audit_cover(svg)
    OUT.write_text(svg, encoding="utf-8")
    OUT_BUST.write_text(svg, encoding="utf-8")
    print(f"wrote {OUT} and {OUT_BUST} ({len(svg):,} bytes)")
