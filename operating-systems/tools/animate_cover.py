"""Generates a 72-frame (6-second @ 12 fps) looping animated GIF and MP4 of the
Operating Systems: A Hands-On Approach front cover for LinkedIn.

Outputs:
- Operating-Systems-Cover-LinkedIn.gif
- Operating-Systems-Cover-LinkedIn.mp4
- src/art/cover-linkedin.gif
"""
import concurrent.futures
import math
import shutil
import subprocess
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import figkit

FRAMES_DIR = Path("/tmp/os_cover_anim_frames")
N_FRAMES = 72
FPS = 12


def build_frame(frame_idx: int) -> str:
    W, H = 960, 1280
    t = frame_idx / N_FRAMES  # 0.0 .. 1.0
    tau = 2.0 * math.pi * t
    out: list[str] = []

    def add(s: str):
        out.append(s)

    def icon(name: str, x: float, y: float, size: float, color: str):
        inner = figkit.icon_markup(name)
        scale = size / 24.0
        add(f'  <g transform="translate({x:.1f} {y:.1f}) scale({scale:.4f})" fill="{color}">{inner}</g>')

    sun_r1 = 78.0
    sun_r2 = 46.0
    sun_op = 0.24

    add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">')
    add("""  <defs>
    <linearGradient id="sky-grad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#091024"/>
      <stop offset="35%" stop-color="#132247"/>
      <stop offset="68%" stop-color="#1F3B6D"/>
      <stop offset="88%" stop-color="#3B5284"/>
      <stop offset="100%" stop-color="#F59E0B" stop-opacity="0.55"/>
    </linearGradient>
    <radialGradient id="sun-glow" cx="50%" cy="46%" r="45%">
      <stop offset="0%" stop-color="#FDE68A" stop-opacity="0.78"/>
      <stop offset="35%" stop-color="#F59E0B" stop-opacity="0.34"/>
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
    <radialGradient id="crab-shell" cx="45%" cy="35%" r="65%">
      <stop offset="0%" stop-color="#EA580C"/>
      <stop offset="45%" stop-color="#C2410C"/>
      <stop offset="80%" stop-color="#9A3412"/>
      <stop offset="100%" stop-color="#431407"/>
    </radialGradient>
    <linearGradient id="crab-claw" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#F97316"/>
      <stop offset="55%" stop-color="#B45309"/>
      <stop offset="100%" stop-color="#7C2D12"/>
    </linearGradient>
    <linearGradient id="steel-base" x1="0" y1="0" x2="1" y2="0.3">
      <stop offset="0%" stop-color="#94A3B8"/>
      <stop offset="35%" stop-color="#64748B"/>
      <stop offset="70%" stop-color="#475569"/>
      <stop offset="100%" stop-color="#334155"/>
    </linearGradient>
    <linearGradient id="rust-streak" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#7F1D1D" stop-opacity="0.92"/>
      <stop offset="45%" stop-color="#9A3412" stop-opacity="0.95"/>
      <stop offset="80%" stop-color="#C2410C" stop-opacity="0.90"/>
      <stop offset="100%" stop-color="#D97706" stop-opacity="0.85"/>
    </linearGradient>
    <filter id="mat-shadow" x="-8%" y="-8%" width="116%" height="120%">
      <feDropShadow dx="0" dy="8" stdDeviation="10" flood-color="#020617" flood-opacity="0.55"/>
    </filter>
    <filter id="soft-glow" x="-30%" y="-30%" width="160%" height="160%">
      <feGaussianBlur stdDeviation="4" result="b"/>
      <feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <style>
    .sans { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }
    .mono { font-family: "SF Mono", SFMono-Regular, ui-monospace, Menlo, Consolas, monospace; }
  </style>
""")

    # 1. SKY, TWINKLING STARS & BREATHING SUNRISE
    add(f'  <rect width="{W}" height="{H}" rx="16" fill="#070C18"/>')
    add(f'  <rect width="{W}" height="660" rx="16" fill="url(#sky-grad)"/>')
    add(f'  <rect width="{W}" height="660" fill="url(#sun-glow)"/>')

    stars = [
        (78, 52, 1.6), (164, 38, 1.3), (285, 62, 1.7), (412, 40, 1.4),
        (560, 48, 1.9), (690, 36, 1.5), (825, 58, 1.7), (895, 42, 1.3),
        (110, 118, 1.3), (860, 112, 1.6), (65, 195, 1.5), (902, 185, 1.4),
        (140, 250, 1.3), (830, 240, 1.6),
    ]
    for idx, (sx, sy, sr) in enumerate(stars):
        sop = 0.45 + 0.45 * math.sin(tau + idx * 0.9)
        add(f'  <circle cx="{sx}" cy="{sy}" r="{sr:.2f}" fill="#E0F2FE" opacity="{sop:.2f}"/>')

    add(f'  <circle cx="480" cy="435" r="{sun_r1:.1f}" fill="#FDE68A" opacity="{sun_op:.2f}"/>')
    add(f'  <circle cx="480" cy="435" r="{sun_r2:.1f}" fill="#FEF08A" opacity="0.58"/>')

    # 2. OPEN-SKY TYPOGRAPHY
    add('  <rect x="290" y="50" width="380" height="32" rx="16" fill="#0F172A" fill-opacity="0.72" stroke="#38BDF8" stroke-width="1.2"/>')
    dot_op = 0.55 + 0.45 * math.sin(2 * tau)
    add(f'  <circle cx="312" cy="66" r="4.8" fill="#34D399" opacity="{dot_op:.2f}"/>')
    add('  <text x="490" y="71" text-anchor="middle" class="mono" font-size="12.5" font-weight="700" letter-spacing="1.4" fill="#E0F2FE">C++20 · RUST 2024 · x86-64 &amp; ARM64</text>')

    add('  <text x="480" y="152" text-anchor="middle" class="sans" font-size="68" font-weight="800" letter-spacing="-1.2" fill="#FFFFFF" filter="url(#mat-shadow)">Operating Systems</text>')
    add('  <text x="480" y="198" text-anchor="middle" class="sans" font-size="27" font-weight="500" letter-spacing="0.4" fill="#7DD3FC">A Hands-On Approach</text>')
    add('  <line x1="270" y1="220" x2="690" y2="220" stroke="#F59E0B" stroke-width="1.8" stroke-opacity="0.75"/>')
    add('  <circle cx="480" cy="220" r="4" fill="#FDE68A"/>')
    add('  <text x="480" y="248" text-anchor="middle" class="sans" font-size="15.5" font-weight="500" fill="#E2E8F0">From Silicon Microarchitecture &amp; Kernel Internals to Shells, Event Loops &amp; Daemons</text>')

    # 3. LAYERED MATERIAL DESIGN MOUNTAINS
    add('  <polygon points="0,540 0,430 115,355 235,288 375,445 440,540" fill="url(#mtn-far-l)"/>')
    add('  <polygon points="235,288 375,445 440,540 270,540 218,395" fill="url(#mtn-far-r)"/>')
    add('  <polygon points="235,288 184,321 206,338 224,324 239,344 268,325" fill="#E0F2FE" opacity="0.92"/>')

    add('  <polygon points="470,540 595,365 725,276 865,390 960,445 960,540" fill="url(#mtn-far-l)"/>')
    add('  <polygon points="725,276 865,390 960,445 960,540 705,540 695,382" fill="url(#mtn-far-r)"/>')
    add('  <polygon points="725,276 676,313 698,329 718,314 736,336 772,316" fill="#E0F2FE" opacity="0.92"/>')

    add('  <polygon points="330,540 480,348 630,540" fill="#1E3A8A" opacity="0.85"/>')
    add('  <polygon points="480,348 630,540 495,540" fill="#172554" opacity="0.9"/>')
    add('  <polygon points="480,348 448,386 468,396 482,382 498,398 512,386" fill="#FDE68A" opacity="0.85"/>')

    add('  <polygon points="0,565 0,468 155,398 335,488 510,425 685,485 835,402 960,465 960,565" fill="url(#mtn-mid-l)"/>')
    add('  <polygon points="155,398 335,488 335,565 140,565" fill="url(#mtn-mid-r)" opacity="0.55"/>')
    add('  <polygon points="510,425 685,485 685,565 495,565" fill="url(#mtn-mid-r)" opacity="0.55"/>')
    add('  <polygon points="835,402 960,465 960,565 815,565" fill="url(#mtn-mid-r)" opacity="0.55"/>')

    add('  <path d="M 40 495 L 155 445 L 260 495 L 390 495" fill="none" stroke="#38BDF8" stroke-width="1.5" stroke-opacity="0.45"/>')
    add('  <circle cx="155" cy="445" r="3.5" fill="#38BDF8" opacity="0.85"/>')
    add('  <path d="M 570 495 L 710 495 L 835 442 L 920 482" fill="none" stroke="#34D399" stroke-width="1.5" stroke-opacity="0.45"/>')
    add('  <circle cx="835" cy="442" r="3.5" fill="#34D399" opacity="0.85"/>')

    add(f'  <rect x="0" y="535" width="{W}" height="{H-535}" fill="url(#ground-grad)"/>')

    for gx in range(80, 960, 80):
        add(f'  <line x1="{gx}" y1="790" x2="{480 + (gx - 480) * 1.35:.1f}" y2="1150" stroke="#1E293B" stroke-width="1"/>')
    for gy in [820, 875, 935, 1000, 1070, 1145]:
        add(f'  <line x1="36" y1="{gy}" x2="{W-36}" y2="{gy}" stroke="#1E293B" stroke-width="1"/>')

    # =========================================================================
    # 4. COOL SHELL TERMINAL & LIVE TYPING / TELEMETRY (y = 488..784)
    # =========================================================================
    active_phase = int(t * 3) % 3  # 0: emma/CFS, 1: adam/MMU, 2: orphan/VFS
    add('  <rect x="64" y="488" width="832" height="296" rx="14" fill="url(#shell-bg)" stroke="#38BDF8" stroke-width="1.8" filter="url(#mat-shadow)"/>')
    add('  <path d="M 64 502 Q 64 488 78 488 L 882 488 Q 896 488 896 502 L 896 530 L 64 530 Z" fill="#1E293B"/>')
    add('  <line x1="64" y1="530" x2="896" y2="530" stroke="#334155" stroke-width="1.2"/>')
    add('  <circle cx="90" cy="509" r="6" fill="#EF4444"/>')
    add('  <circle cx="110" cy="509" r="6" fill="#F59E0B"/>')
    add('  <circle cx="130" cy="509" r="6" fill="#10B981"/>')

    # Shell Tabs (highlight active tab matching phase)
    tab_specs = [
        (160, 182, "terminal", "#38BDF8", "zsh · tty0 (Ring 3)"),
        (352, 178, "memory",   "#C084FC", "vm_map · 4-Level PT"),
        (540, 178, "bolt",     "#F59E0B", "kqueue · io_uring"),
    ]
    for tidx, (tx, tw, tic, tcol, tlbl) in enumerate(tab_specs):
        is_act = (tidx == active_phase)
        tbg = "#0F172A" if is_act else "#1E293B"
        tstr = tcol if is_act else "#475569"
        tfg = "#E0F2FE" if is_act else "#94A3B8"
        add(f'  <rect x="{tx}" y="495" width="{tw}" height="28" rx="6" fill="{tbg}" stroke="{tstr}" stroke-width="{1.5 if is_act else 1.0}"/>')
        icon(tic, tx + 10, 500, 18, tcol if is_act else "#94A3B8")
        add(f'  <text x="{tx+34}" y="514" class="mono" font-size="12" font-weight="700" fill="{tfg}">{tlbl}</text>')

    # Left Console Pane: emma, adam, orphan
    add('  <text x="88" y="560" class="mono" font-size="13" font-weight="700" fill="#34D399">emma@darwin-xnu</text>')
    add('  <text x="226" y="560" class="mono" font-size="13" font-weight="600" fill="#94A3B8">~ $</text>')
    add('  <text x="260" y="560" class="mono" font-size="13" font-weight="700" fill="#F8FAFC">fork() &amp;&amp; execve("/bin/sh", argv, envp)</text>')
    emma_col = "#6EE7B7" if active_phase == 0 else "#7DD3FC"
    add(f'  <text x="88" y="584" class="mono" font-size="12" font-weight="500" fill="{emma_col}">├─ PID 1 (launchd) ──► PID 4280 (worker) · COW pages mapped</text>')

    add('  <text x="88" y="618" class="mono" font-size="13" font-weight="700" fill="#38BDF8">adam@darwin-xnu</text>')
    add('  <text x="226" y="618" class="mono" font-size="13" font-weight="600" fill="#94A3B8">~ $</text>')
    add('  <text x="260" y="618" class="mono" font-size="13" font-weight="700" fill="#F8FAFC">pagetable --walk 0x0000_7FFF_ABCD_EF01</text>')
    add('  <text x="88" y="642" class="mono" font-size="12" font-weight="500" fill="#C4B5FD">└─ CR3 0x1000_0000 → PML4[255] → PDPT[510] → PD[350] → PT[223]</text>')
    tlb_col = "#FEF08A" if active_phase == 1 else "#FDE68A"
    add(f'  <text x="88" y="664" class="mono" font-size="12" font-weight="700" fill="{tlb_col}">   ✓ TLB Hit (PCID 4) · Physical Frame PA = 0x0000_0000_8A42_0F01</text>')

    # Live typing effect on orphan@darwin-xnu prompt
    full_cmd = "kevent(kq, EVFILT_READ | EVFILT_PROC)"
    if t < 0.18:
        n_chars = max(6, int((t / 0.18) * len(full_cmd)))
    else:
        n_chars = len(full_cmd)
    typed_cmd = full_cmd[:n_chars]
    cursor_x = 268 + n_chars * 7.8 + 4
    cursor_on = (frame_idx % 8) < 5 or t < 0.18

    add('  <text x="88" y="698" class="mono" font-size="13" font-weight="700" fill="#F59E0B">orphan@darwin-xnu</text>')
    add('  <text x="234" y="698" class="mono" font-size="13" font-weight="600" fill="#94A3B8">~ $</text>')
    add(f'  <text x="268" y="698" class="mono" font-size="13" font-weight="700" fill="#F8FAFC">{typed_cmd}</text>')
    if cursor_on:
        add(f'  <rect x="{cursor_x:.1f}" y="685" width="9" height="16" rx="1.5" fill="#38BDF8" filter="url(#soft-glow)"/>')

    # Bottom Trap Gate status strip (pulses gold)
    trap_stroke = "#F59E0B" if (frame_idx % 24) < 12 else "#475569"
    add(f'  <rect x="84" y="724" width="510" height="42" rx="8" fill="#1E293B" stroke="{trap_stroke}" stroke-width="1.4"/>')
    icon("shield", 96, 735, 20, "#F59E0B")
    add('  <text x="124" y="742" class="sans" font-size="11.5" font-weight="700" fill="#FDE68A">TRAP GATE · SYSCALL / SVC #0 · RING 3 → RING 0</text>')
    add('  <text x="124" y="758" class="mono" font-size="11" font-weight="500" fill="#94A3B8">Saves RIP/RFLAGS to TSS.rsp0 · Dispatches IDT / VBAR_EL1</text>')

    add('  <line x1="612" y1="544" x2="612" y2="766" stroke="#1E293B" stroke-width="1.5"/>')

    # Right Console Pane: 3 Material Kernel Cards with cycling active highlight
    chips = [
        ("schedule", "#34D399", "#064E3B", "CFS / EEVDF Scheduler", "vruntime RB-Tree · Futex"),
        ("view_module", "#38BDF8", "#0C4A6E", "Arena &amp; Lock-Free Ring", "LruCache&lt;K,V&gt; · SPSC 64B"),
        ("lan", "#C084FC", "#3B0764", "VFS &amp; Zero-Copy I/O", "Page Cache · WAL · DMA"),
    ]
    for idx, (ic, fg, bg, t1, t2) in enumerate(chips):
        cy = 548 + idx * 74
        is_hi = (idx == active_phase)
        sw = 2.2 if is_hi else 1.2
        cfill = "#243247" if is_hi else "#1E293B"
        add(f'  <rect x="628" y="{cy}" width="248" height="62" rx="8" fill="{cfill}" stroke="{fg}" stroke-width="{sw}"/>')
        add(f'  <rect x="640" y="{cy+13}" width="36" height="36" rx="8" fill="{bg}"/>')
        icon(ic, 646, cy + 19, 24, fg)
        add(f'  <text x="688" y="{cy+27}" class="sans" font-size="13" font-weight="700" fill="#F8FAFC">{t1}</text>')
        add(f'  <text x="688" y="{cy+46}" class="mono" font-size="11.2" font-weight="500" fill="{fg}">{t2}</text>')

    # =========================================================================
    # 5. ANIMATED PCB BUS PACKETS, SILICON DIE & CHARACTERS
    # =========================================================================
    add('  <path d="M 480 784 L 480 838" fill="none" stroke="#F59E0B" stroke-width="3"/>')
    add('  <path d="M 330 784 L 330 816 L 410 816 L 410 838" fill="none" stroke="#38BDF8" stroke-width="2.2"/>')
    add('  <path d="M 630 784 L 630 816 L 550 816 L 550 838" fill="none" stroke="#34D399" stroke-width="2.2"/>')

    dash_off = -(frame_idx * 1.5) % 20
    add(f'  <path d="M 306 965 L 348 965" fill="none" stroke="#38BDF8" stroke-width="3" stroke-dasharray="6 4" stroke-dashoffset="{dash_off:.1f}"/>')
    add(f'  <path d="M 612 965 L 654 965" fill="none" stroke="#F97316" stroke-width="3" stroke-dasharray="6 4" stroke-dashoffset="{-dash_off:.1f}"/>')

    # Animated glowing bus packets flowing from Shell -> Silicon Die -> Tux & Crabbie
    p_prog = (t * 3.0) % 1.0
    py_center = 784 + p_prog * (838 - 784)
    add(f'  <circle cx="480" cy="{py_center:.1f}" r="5" fill="#FDE68A" filter="url(#soft-glow)"/>')
    px_left = 348 - p_prog * (348 - 306)
    px_right = 612 + p_prog * (654 - 612)
    add(f'  <circle cx="{px_left:.1f}" cy="965" r="4.5" fill="#38BDF8" filter="url(#soft-glow)"/>')
    add(f'  <circle cx="{px_right:.1f}" cy="965" r="4.5" fill="#FB923C" filter="url(#soft-glow)"/>')

    # CENTERPIECE: Unified Silicon & Ring 0 Die
    add('  <rect x="348" y="838" width="264" height="256" rx="16" fill="url(#die-grad)" stroke="#F59E0B" stroke-width="2.2" filter="url(#mat-shadow)"/>')
    for p in range(7):
        px = 376 + p * 34
        pcol = "#FDE68A" if (p + frame_idx // 3) % 7 == 0 else "#F59E0B"
        add(f'  <rect x="{px}" y="829" width="12" height="9" rx="2" fill="{pcol}"/>')
        add(f'  <rect x="{px}" y="1094" width="12" height="9" rx="2" fill="{pcol}"/>')
    for p in range(6):
        py = 866 + p * 36
        pcol = "#FDE68A" if (p + frame_idx // 3) % 6 == 0 else "#F59E0B"
        add(f'  <rect x="339" y="{py}" width="9" height="12" rx="2" fill="{pcol}"/>')
        add(f'  <rect x="612" y="{py}" width="9" height="12" rx="2" fill="{pcol}"/>')

    add('  <text x="480" y="864" text-anchor="middle" class="sans" font-size="12" font-weight="800" letter-spacing="1.4" fill="#FDE68A">UNIFIED SILICON &amp; RING 0 DIE</text>')

    active_core = (frame_idx // 9) % 4
    cores = [
        (368, 878, "#38BDF8", "#0C4A6E", "CORE 0 · SMP", "Out-of-Order ALU"),
        (486, 878, "#38BDF8", "#0C4A6E", "CORE 1 · SMP", "MESI L1d / L2"),
        (368, 954, "#34D399", "#064E3B", "MMU &amp; TLB", "4-Level Radix PT"),
        (486, 954, "#C084FC", "#3B0764", "UMA · GPU/NPU", "Zero-Copy Fabric"),
    ]
    for cidx, (cx, cy, fg, bg, ct, cs) in enumerate(cores):
        c_sw = 2.4 if cidx == active_core else 1.4
        add(f'  <rect x="{cx}" y="{cy}" width="106" height="64" rx="8" fill="{bg}" stroke="{fg}" stroke-width="{c_sw}"/>')
        if cidx == active_core:
            add(f'  <rect x="{cx+2}" y="{cy+2}" width="102" height="60" rx="7" fill="none" stroke="#FFFFFF" stroke-opacity="0.35" stroke-width="1"/>')
        add(f'  <text x="{cx+53}" y="{cy+27}" text-anchor="middle" class="mono" font-size="11.5" font-weight="700" fill="#FFFFFF">{ct}</text>')
        add(f'  <text x="{cx+53}" y="{cy+47}" text-anchor="middle" class="sans" font-size="10.5" font-weight="500" fill="{fg}">{cs}</text>')

    add('  <rect x="368" y="1032" width="224" height="44" rx="8" fill="#0F172A" stroke="#F59E0B" stroke-width="1.2"/>')
    add('  <text x="480" y="1051" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="#FDE68A">COHERENT FABRIC · IO-APIC / GICv4</text>')
    add('  <text x="480" y="1068" text-anchor="middle" class="mono" font-size="10.2" font-weight="500" fill="#94A3B8">64B Cache Lines · NVMe &amp; NIC DMA</text>')

    # -------------------------------------------------------------------------
    # CHARACTER 1 (LEFT): Animated Tux with Scanning Visor & Pulsing UNIX Pipe
    # -------------------------------------------------------------------------
    tux_bob = 2.8 * math.sin(tau)
    visor_scan = 4.0 * math.sin(2 * tau)
    add('  <rect x="64" y="852" width="242" height="242" rx="16" fill="#0F172A" fill-opacity="0.85" stroke="#38BDF8" stroke-width="1.5" filter="url(#mat-shadow)"/>')
    add(f'  <g transform="translate(185 {955 + tux_bob:.2f})">')
    add('    <ellipse cx="-24" cy="64" rx="18" ry="8" fill="#F59E0B"/>')
    add('    <ellipse cx="24" cy="64" rx="18" ry="8" fill="#F59E0B"/>')
    add('    <ellipse cx="0" cy="14" rx="46" ry="52" fill="#1E293B" stroke="#475569" stroke-width="1.5"/>')
    add('    <ellipse cx="0" cy="20" rx="31" ry="40" fill="#F8FAFC"/>')
    add('    <circle cx="0" cy="-38" r="32" fill="#1E293B" stroke="#475569" stroke-width="1.5"/>')
    add('    <rect x="-24" y="-48" width="48" height="16" rx="8" fill="#0284C7" stroke="#7DD3FC" stroke-width="1.5"/>')
    add(f'    <circle cx="{-10 + visor_scan:.1f}" cy="-40" r="3.5" fill="#E0F2FE"/>')
    add(f'    <circle cx="{10 + visor_scan:.1f}" cy="-40" r="3.5" fill="#E0F2FE"/>')
    add('    <polygon points="-9,-29 9,-29 0,-18" fill="#F59E0B"/>')
    add('    <ellipse cx="-44" cy="12" rx="11" ry="26" transform="rotate(18 -44 12)" fill="#1E293B"/>')
    add('    <ellipse cx="44" cy="12" rx="11" ry="26" transform="rotate(-18 44 12)" fill="#1E293B"/>')
    add('    <rect x="-36" y="18" width="72" height="18" rx="9" fill="#064E3B" stroke="#34D399" stroke-width="1.6"/>')
    pipe_dot_x = -26 + ((t * 4.0) % 1.0) * 52
    add(f'    <circle cx="{pipe_dot_x:.1f}" cy="27" r="7" fill="#34D399" opacity="0.28"/>')
    add('    <text x="0" y="31" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="#6EE7B7">pipe(fd)</text>')
    add('  </g>')
    add('  <text x="185" y="1052" text-anchor="middle" class="sans" font-size="13.5" font-weight="700" fill="#F8FAFC">Kernel &amp; POSIX Pipelines</text>')
    add('  <text x="185" y="1072" text-anchor="middle" class="mono" font-size="11" font-weight="500" fill="#7DD3FC">fork · dup2 · waitpid · signals</text>')

    # -------------------------------------------------------------------------
    # CHARACTER 2 (RIGHT): Animated Realistic Rust Crabbie Swinging Rusty Blade
    # -------------------------------------------------------------------------
    crab_bob = 3.0 * math.sin(tau + math.pi * 0.5)
    sword_swing = -34.0 + 7.5 * math.sin(2 * tau)
    claw_pinch = 4.0 * math.sin(2 * tau)
    leg_step = 2.5 * math.sin(2 * tau)

    add('  <rect x="654" y="852" width="242" height="242" rx="16" fill="#0F172A" fill-opacity="0.85" stroke="#EA580C" stroke-width="1.5" filter="url(#mat-shadow)"/>')
    add(f'  <g transform="translate(772 {958 + crab_bob:.2f})">')

    # Articulated Walking Legs
    add(f'    <path d="M -34 10 L -60 12 L -74 {34 + leg_step:.1f} L -80 {50 + leg_step:.1f}" fill="none" stroke="#9A3412" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round"/>')
    add(f'    <path d="M -34 10 L -60 12 L -74 {34 + leg_step:.1f}" fill="none" stroke="#EA580C" stroke-width="2.5" stroke-linecap="round"/>')
    add(f'    <path d="M -38 20 L -66 28 L -78 {50 - leg_step:.1f} L -82 {64 - leg_step:.1f}" fill="none" stroke="#7C2D12" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>')
    add(f'    <path d="M -38 20 L -66 28 L -78 {50 - leg_step:.1f}" fill="none" stroke="#C2410C" stroke-width="2.2" stroke-linecap="round"/>')
    add(f'    <path d="M -32 28 L -56 42 L -64 {62 + leg_step:.1f} L -66 {74 + leg_step:.1f}" fill="none" stroke="#7C2D12" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>')

    add(f'    <path d="M 34 10 L 60 12 L 74 {34 - leg_step:.1f} L 80 {50 - leg_step:.1f}" fill="none" stroke="#9A3412" stroke-width="5.5" stroke-linecap="round" stroke-linejoin="round"/>')
    add(f'    <path d="M 34 10 L 60 12 L 74 {34 - leg_step:.1f}" fill="none" stroke="#EA580C" stroke-width="2.5" stroke-linecap="round"/>')
    add(f'    <path d="M 38 20 L 66 28 L 78 {50 + leg_step:.1f} L 82 {64 + leg_step:.1f}" fill="none" stroke="#7C2D12" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>')
    add(f'    <path d="M 38 20 L 66 28 L 78 {50 + leg_step:.1f}" fill="none" stroke="#C2410C" stroke-width="2.2" stroke-linecap="round"/>')
    add(f'    <path d="M 32 28 L 56 42 L 64 {62 - leg_step:.1f} L 66 {74 - leg_step:.1f}" fill="none" stroke="#7C2D12" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>')

    # Left Crusher Claw (snapping animation)
    add('    <path d="M -36 -4 C -58 -14 -68 -36 -54 -52" fill="none" stroke="#9A3412" stroke-width="8" stroke-linecap="round"/>')
    add('    <path d="M -36 -4 C -58 -14 -68 -36 -54 -52" fill="none" stroke="#EA580C" stroke-width="3.5" stroke-linecap="round"/>')
    add(f'    <g transform="rotate({claw_pinch:.1f} -54 -50)">')
    add('      <path d="M -56 -48 C -72 -62 -64 -82 -42 -78 C -50 -70 -50 -62 -40 -58 Z" fill="url(#crab-claw)" stroke="#FDBA74" stroke-width="1"/>')
    add('      <path d="M -52 -46 C -34 -44 -28 -60 -38 -70 C -44 -64 -44 -58 -48 -52 Z" fill="url(#crab-claw)" stroke="#FDBA74" stroke-width="1"/>')
    add('      <circle cx="-45" cy="-68" r="1.6" fill="#FEF3C7"/>')
    add('      <circle cx="-42" cy="-63" r="1.5" fill="#FEF3C7"/>')
    add('    </g>')

    # Right Cheliped Arm gripping the Realistic Rusted Blade
    add('    <path d="M 34 -4 C 48 -14 44 -32 24 -44" fill="none" stroke="#9A3412" stroke-width="8" stroke-linecap="round"/>')
    add('    <path d="M 34 -4 C 48 -14 44 -32 24 -44" fill="none" stroke="#EA580C" stroke-width="3.5" stroke-linecap="round"/>')

    # Realistic Weathered & Corroded Rusty Blade (swinging in right claw)
    add(f'    <g transform="translate(22 -46) rotate({sword_swing:.2f}) scale(0.88)">')
    add('      <circle cx="-48" cy="0" r="6.5" fill="#78350F" stroke="#B45309" stroke-width="1.5"/>')
    add('      <circle cx="-48" cy="0" r="2.5" fill="#9A3412"/>')
    add('      <rect x="-42" y="-4.5" width="26" height="9" rx="2.5" fill="#451A03" stroke="#92400E" stroke-width="1.2"/>')
    for hx in [-37, -31, -25, -19]:
        add(f'      <line x1="{hx}" y1="-4.2" x2="{hx+3}" y2="4.2" stroke="#B45309" stroke-width="1.5"/>')
    add('      <rect x="-16" y="-15" width="7" height="30" rx="2.5" fill="#78350F" stroke="#D97706" stroke-width="1.2"/>')
    add('      <circle cx="-12.5" cy="-9" r="2.2" fill="#9A3412"/>')
    add('      <circle cx="-12.5" cy="8" r="2.5" fill="#7F1D1D"/>')

    add('      <path d="M -9 -8.5 L 18 -8.5 L 21 -5.2 L 24 -8.5 L 58 -8.0 L 61 -4.8 L 64 -7.8 L 88 -6.5 L 106 0 L 86 7.5 L 52 8.5 L 49 5.5 L 46 8.5 L -9 8.5 Z" fill="url(#steel-base)" stroke="#CBD5E1" stroke-width="0.9"/>')
    add('      <path d="M -9 0 L 96 0 L 86 7.5 L 52 8.5 L 49 5.5 L 46 8.5 L -9 8.5 Z" fill="#334155" opacity="0.65"/>')
    add('      <line x1="-4" y1="-2.2" x2="76" y2="-1.5" stroke="#1E293B" stroke-width="2.4" stroke-linecap="round"/>')
    add('      <path d="M -6 8.2 L 45 8.2 M 53 8.2 L 85 7.2 L 105 0" fill="none" stroke="#E2E8F0" stroke-width="1.1" stroke-opacity="0.8"/>')

    # Ferric-oxide rust patches
    add('      <path d="M -9 -8.2 C 4 -8.5 14 -6 19 -1 C 22 3 12 8.2 -9 8.2 Z" fill="url(#rust-streak)"/>')
    add('      <path d="M 25 -7.5 C 36 -8 48 -6 55 -1.5 C 58 2 47 7.8 33 7.5 C 24 6 20 0 25 -7.5 Z" fill="url(#rust-streak)"/>')
    add('      <path d="M 29 -5.2 C 37 -5.5 45 -3.5 49 0 C 46 4 36 5.2 28 3.8 Z" fill="#7F1D1D" opacity="0.85"/>')
    add('      <path d="M 65 -7.2 C 77 -6.8 89 -5.5 99 -1.5 C 91 3.5 78 6.5 67 4.8 C 61 2 62 -3 65 -7.2 Z" fill="url(#rust-streak)"/>')
    for rx, ry, rr, rcol in [
        (-2, -3.5, 3.2, "#D97706"), (5, 2.8, 2.6, "#EA580C"), (12, -4.0, 2.2, "#B45309"),
        (32, -2.5, 3.4, "#EA580C"), (41, 3.2, 2.8, "#D97706"), (47, -4.2, 2.1, "#9A3412"),
        (59, 2.0, 2.5, "#C2410C"), (73, -2.8, 3.5, "#EA580C"), (82, 2.2, 2.7, "#D97706"),
        (91, -1.0, 2.0, "#F97316"), (16, 4.5, 1.8, "#7F1D1D"), (53, -2.0, 1.9, "#7F1D1D"),
    ]:
        add(f'      <circle cx="{rx}" cy="{ry}" r="{rr}" fill="{rcol}" opacity="0.88"/>')
    for px, py in [
        (0, 0), (8, -1), (15, 1), (22, -3), (28, 2), (35, 0), (43, -1),
        (50, 3), (57, -3), (63, 1), (70, 0), (77, 3), (84, -2), (93, 1),
    ]:
        add(f'      <circle cx="{px}" cy="{py}" r="1.0" fill="#451A03" opacity="0.9"/>')
    # Animated falling rust flakes & oxide sparks
    flake_drop = ((t * 2.0) % 1.0) * 14.0
    add(f'      <circle cx="38" cy="{12 + flake_drop:.1f}" r="1.7" fill="#EA580C" opacity="{1.0 - flake_drop/16:.2f}"/>')
    add(f'      <circle cx="66" cy="{11 + (flake_drop + 5) % 14:.1f}" r="1.5" fill="#D97706" opacity="0.8"/>')
    add(f'      <circle cx="84" cy="{10 + (flake_drop + 9) % 14:.1f}" r="1.6" fill="#C2410C" opacity="0.85"/>')
    add('    </g>')

    # Right Pincer Claw wrapped over the blade grip
    add('    <path d="M 14 -40 C 16 -54 30 -58 36 -48 C 32 -40 22 -36 14 -40 Z" fill="url(#crab-claw)" stroke="#FDBA74" stroke-width="1.1"/>')
    add('    <path d="M 16 -36 C 24 -30 36 -34 36 -44 C 28 -40 22 -38 16 -36 Z" fill="url(#crab-claw)" stroke="#FDBA74" stroke-width="1.1"/>')

    # Realistic Textured Crab Carapace
    add('    <path d="M -52 4 L -46 -10 L -38 -8 L -32 -18 L -22 -15 L -14 -22 L 0 -20 L 14 -22 L 22 -15 L 32 -18 L 38 -8 L 46 -10 L 52 4 C 54 28 34 44 0 44 C -34 44 -54 28 -52 4 Z" fill="url(#crab-shell)" stroke="#F97316" stroke-width="1.6"/>')
    add('    <path d="M -26 0 C -18 14 18 14 26 0" fill="none" stroke="#7C2D12" stroke-width="2" stroke-linecap="round"/>')
    add('    <path d="M -34 14 C -20 28 20 28 34 14" fill="none" stroke="#9A3412" stroke-width="1.6" stroke-linecap="round"/>')
    add('    <circle cx="-28" cy="4" r="3.5" fill="#7C2D12" opacity="0.65"/>')
    add('    <circle cx="26" cy="6" r="4.0" fill="#7C2D12" opacity="0.65"/>')
    add('    <circle cx="-18" cy="-8" r="2.2" fill="#FDBA74" opacity="0.45"/>')

    # Stalked Compound Eyes
    add('    <path d="M -15 -19 L -18 -33" stroke="#9A3412" stroke-width="4.5" stroke-linecap="round"/>')
    add('    <path d="M 15 -19 L 18 -33" stroke="#9A3412" stroke-width="4.5" stroke-linecap="round"/>')
    add('    <circle cx="-18" cy="-35" r="6.5" fill="#111827" stroke="#F97316" stroke-width="1.4"/>')
    add('    <circle cx="-20" cy="-37" r="2.2" fill="#FFFFFF"/>')
    add('    <circle cx="18" cy="-35" r="6.5" fill="#111827" stroke="#F97316" stroke-width="1.4"/>')
    add('    <circle cx="16" cy="-37" r="2.2" fill="#FFFFFF"/>')

    # Mandibles & Weathered Riveted Iron Breastplate (`Send + Sync`)
    add('    <path d="M -12 -5 Q 0 1 12 -5" fill="none" stroke="#431407" stroke-width="2.5" stroke-linecap="round"/>')
    add('    <rect x="-38" y="13" width="76" height="19" rx="5" fill="#1C1917" stroke="#B45309" stroke-width="1.4"/>')
    add('    <circle cx="-33" cy="22.5" r="1.5" fill="#D97706"/>')
    add('    <circle cx="33" cy="22.5" r="1.5" fill="#D97706"/>')
    add('    <text x="0" y="26" text-anchor="middle" class="mono" font-size="9.8" font-weight="700" fill="#FDBA74">Send + Sync</text>')
    add('  </g>')
    add('  <text x="775" y="1052" text-anchor="middle" class="sans" font-size="13.5" font-weight="700" fill="#F8FAFC">Fearless Bare-Metal Rust</text>')
    add('  <text x="775" y="1072" text-anchor="middle" class="mono" font-size="11" font-weight="500" fill="#FDBA74">Arena LRU · Atomics · mmap</text>')

    # CHARACTER 3: Hex the PID 1 Daemon Bot
    bot_bob = 2.0 * math.sin(2 * tau)
    add(f'  <g transform="translate(838 {470 + bot_bob:.1f})">')
    add('    <line x1="0" y1="-26" x2="0" y2="-38" stroke="#F59E0B" stroke-width="2.5"/>')
    add(f'    <circle cx="0" cy="-41" r="{4.5 + 1.2*math.sin(3*tau):.1f}" fill="#34D399" filter="url(#soft-glow)"/>')
    add('    <rect x="-24" y="-26" width="48" height="32" rx="10" fill="#1E293B" stroke="#F59E0B" stroke-width="1.8"/>')
    add('    <circle cx="-9" cy="-12" r="4" fill="#38BDF8"/>')
    add('    <circle cx="9" cy="-12" r="4" fill="#38BDF8"/>')
    add('    <rect x="-14" y="-2" width="28" height="4" rx="2" fill="#34D399"/>')
    add('  </g>')

    # 6. EDITORIAL FOOTER BAR
    add('  <rect x="64" y="1148" width="832" height="84" rx="14" fill="#0F172A" stroke="#334155" stroke-width="1.5" filter="url(#mat-shadow)"/>')
    add('  <rect x="64" y="1148" width="8" height="84" rx="4" fill="#38BDF8"/>')
    add('  <text x="92" y="1177" class="sans" font-size="11" font-weight="700" letter-spacing="2" fill="#7DD3FC">AUTHOR</text>')
    add('  <text x="92" y="1208" class="sans" font-size="24" font-weight="800" letter-spacing="0.8" fill="#FFFFFF">ARPAN PATHAK</text>')
    add('  <line x1="304" y1="1164" x2="304" y2="1216" stroke="#1E293B" stroke-width="1.5"/>')
    add('  <text x="326" y="1181" class="sans" font-size="14" font-weight="700" fill="#F8FAFC">19 Chapters · 54 Verified C++20 &amp; Rust 2024 Programs · 41 Vector Diagrams</text>')
    add('  <text x="326" y="1205" class="mono" font-size="11.2" font-weight="500" fill="#94A3B8">Processes · Concurrency · Virtual Memory · File Systems · Networking · Daemons</text>')

    add("</svg>\n")
    return "\n".join(out)


def render_one(idx: int):
    svg_path = FRAMES_DIR / f"frame_{idx:03d}.svg"
    png_path = FRAMES_DIR / f"frame_{idx:03d}.png"
    svg_path.write_text(build_frame(idx), encoding="utf-8")
    subprocess.run(
        ["rsvg-convert", "-w", "960", "-h", "1280", str(svg_path), "-o", str(png_path)],
        check=True,
    )


def main():
    if FRAMES_DIR.exists():
        shutil.rmtree(FRAMES_DIR)
    FRAMES_DIR.mkdir(parents=True)

    print(f"Rendering {N_FRAMES} frames at 960x1280 via rsvg-convert...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        list(ex.map(render_one, range(N_FRAMES)))

    gif_out = ROOT / "Operating-Systems-Cover-LinkedIn.gif"
    gif_art = ROOT / "src" / "art" / "cover-linkedin.gif"
    mp4_out = ROOT / "Operating-Systems-Cover-LinkedIn.mp4"

    # High-quality 256-color palette GIF via ffmpeg
    subprocess.run(
        [
            "ffmpeg", "-y", "-framerate", str(FPS),
            "-i", str(FRAMES_DIR / "frame_%03d.png"),
            "-vf", "split[s0][s1];[s0]palettegen=max_colors=256:stats_mode=full[p];[s1][p]paletteuse=dither=sierra2_4a:diff_mode=rectangle",
            str(gif_out),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    shutil.copy2(gif_out, gif_art)

    # Also generate crisp 1080p-ready MP4 for LinkedIn video posts
    subprocess.run(
        [
            "ffmpeg", "-y", "-framerate", str(FPS),
            "-i", str(FRAMES_DIR / "frame_%03d.png"),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
            str(mp4_out),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    shutil.rmtree(FRAMES_DIR)
    print(f"wrote {gif_out} ({gif_out.stat().st_size / 1024 / 1024:.2f} MB)")
    print(f"wrote {mp4_out} ({mp4_out.stat().st_size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    main()
