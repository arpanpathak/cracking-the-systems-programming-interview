#!/usr/bin/env python3
"""Generates the front cover illustration (`src/art/cover.svg`) for
*Operating Systems: A Hands-On Approach*.

The cover is a 960 x 1280 portrait vector plate matching the companion books in
`cracking-the-systems-programming-interview` (*Democratizing Linux* and
*Distributed Systems from the Ground Up*).
"""

import math
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parent.parent / "src" / "art"
COVER_W, COVER_H = 960, 1280

INK, SNOW, CREAM = "#1b2430", "#ffffff", "#f6efe0"
RUST, BRASS, TEAL, STEEL, WOOD = "#d9622b", "#c89b3c", "#2f7f86", "#5b6b7c", "#8a6a44"
SANS = "Avenir Next Condensed, Avenir Next, Helvetica Neue, Arial, sans-serif"
SERIF = "Georgia, Iowan Old Style, Times New Roman, serif"
MONO = "JetBrains Mono, SF Mono, Menlo, Consolas, monospace"


def rect(x, y, w, h, fill, rx=0, stroke="none", sw=0, extra=""):
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}"'
            f' stroke="{stroke}" stroke-width="{sw}" {extra}/>')


def ellipse(cx, cy, rx, ry, fill, extra=""):
    return f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{fill}" {extra}/>'


def circle(cx, cy, r, fill, extra=""):
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}" {extra}/>'


def path(d, fill="none", stroke="none", sw=0, extra=""):
    return (f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round"'
            f' stroke-linejoin="round" {extra}/>')


def line(x1, y1, x2, y2, stroke, sw=3, extra=""):
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}"'
            f' stroke-linecap="round" {extra}/>')


def label(x, y, body, size=20, fill=SNOW, anchor="middle", font=SANS, weight=700, extra=""):
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{font}" font-size="{size}" font-weight="{weight}"'
            f' fill="{fill}" text-anchor="{anchor}" {extra}>{escape(body)}</text>')


def rot(angle, cx, cy):
    return f'transform="rotate({angle} {cx:.1f} {cy:.1f})"'


def shadow(cx, base, rx):
    return ellipse(cx, base + 3, rx, rx * 0.12, "#060b14", 'opacity="0.32"')


def eye(cx, cy, r, look=0.0, pupil=0.52):
    return "\n".join([
        circle(cx, cy, r, SNOW),
        circle(cx + look * r * 0.32, cy + r * 0.06, r * pupil, INK),
        circle(cx + look * r * 0.32 + r * 0.18, cy - r * 0.16, r * 0.16, SNOW),
    ])


def sparkle(cx, cy, r, fill=SNOW, opacity=0.85):
    return path(
        f"M{cx},{cy - r} Q{cx},{cy} {cx + r},{cy} Q{cx},{cy} {cx},{cy + r} "
        f"Q{cx},{cy} {cx - r},{cy} Q{cx},{cy} {cx},{cy - r} Z",
        fill,
        extra=f'opacity="{opacity}"',
    )


def penguin(cx, base, s=1.0, look=0.0, left=18, right=-18, scarf=None, hat=None):
    h = 190 * s
    y = lambda f: base - f * h
    parts = [
        shadow(cx, base, 0.36 * h),
        ellipse(cx - 0.13 * h, y(0.02), 0.11 * h, 0.04 * h, "#f2a23a"),
        ellipse(cx + 0.13 * h, y(0.02), 0.11 * h, 0.04 * h, "#f2a23a"),
        ellipse(cx - 0.29 * h, y(0.46), 0.065 * h, 0.21 * h, INK, rot(left, cx - 0.27 * h, y(0.62))),
        ellipse(cx + 0.29 * h, y(0.46), 0.065 * h, 0.21 * h, INK, rot(right, cx + 0.27 * h, y(0.62))),
        ellipse(cx, y(0.40), 0.30 * h, 0.39 * h, INK),
        ellipse(cx, y(0.35), 0.21 * h, 0.30 * h, "#fbfbf7"),
        circle(cx, y(0.80), 0.20 * h, INK),
        ellipse(cx - 0.075 * h, y(0.80), 0.085 * h, 0.10 * h, "#fbfbf7"),
        ellipse(cx + 0.075 * h, y(0.80), 0.085 * h, 0.10 * h, "#fbfbf7"),
    ]
    for side in (-1, 1):
        ex = cx + side * 0.07 * h
        parts += [
            circle(ex + look * 0.022 * h, y(0.80), 0.030 * h, INK),
            circle(ex + look * 0.022 * h + 0.010 * h, y(0.812), 0.009 * h, SNOW),
        ]
    parts.append(path(
        f"M{cx - 0.075 * h:.1f},{y(0.725):.1f} Q{cx:.1f},{y(0.765):.1f} {cx + 0.075 * h:.1f},{y(0.725):.1f}"
        f" Q{cx:.1f},{y(0.635):.1f} {cx - 0.075 * h:.1f},{y(0.725):.1f} Z", "#f2a23a"
    ))
    if scarf:
        parts += [
            path(
                f"M{cx - 0.17 * h:.1f},{y(0.635):.1f} Q{cx:.1f},{y(0.575):.1f} {cx + 0.17 * h:.1f},{y(0.635):.1f}"
                f" L{cx + 0.16 * h:.1f},{y(0.575):.1f} Q{cx:.1f},{y(0.515):.1f} {cx - 0.16 * h:.1f},{y(0.575):.1f} Z",
                scarf,
            ),
            rect(cx + 0.07 * h, y(0.60), 0.07 * h, 0.16 * h, scarf, 3),
        ]
    if hat == "hard":
        parts += [
            path(f"M{cx - 0.19 * h:.1f},{y(0.93):.1f} A{0.19 * h:.1f},{0.17 * h:.1f} 0 0 1 {cx + 0.19 * h:.1f},{y(0.93):.1f} Z", BRASS),
            rect(cx - 0.23 * h, y(0.94), 0.46 * h, 0.03 * h, "#a57f2c", 3),
        ]
    return "\n".join(parts)


def daemon(cx, base, s=1.0, look=0.0):
    h, coat = 180 * s, "#d94f3d"
    y = lambda f: base - f * h
    return "\n".join([
        shadow(cx, base, 0.34 * h),
        path(f"M{cx - 0.18 * h:.1f},{y(0.16):.1f} C{cx - 0.52 * h:.1f},{y(0.10):.1f} {cx - 0.50 * h:.1f},{y(0.48):.1f} {cx - 0.36 * h:.1f},{y(0.52):.1f}",
             stroke=coat, sw=0.055 * h),
        path(f"M{cx - 0.36 * h:.1f},{y(0.62):.1f} l{0.09 * h:.1f},{0.10 * h:.1f} l{-0.13 * h:.1f},{0.03 * h:.1f} Z", coat),
        ellipse(cx - 0.11 * h, y(0.02), 0.11 * h, 0.045 * h, "#3d8f5a"),
        ellipse(cx + 0.11 * h, y(0.02), 0.11 * h, 0.045 * h, "#3d8f5a"),
        ellipse(cx, y(0.32), 0.23 * h, 0.29 * h, coat),
        ellipse(cx, y(0.28), 0.14 * h, 0.18 * h, "#f08a6a"),
        ellipse(cx - 0.25 * h, y(0.42), 0.05 * h, 0.12 * h, coat, rot(18, cx - 0.25 * h, y(0.52))),
        ellipse(cx + 0.27 * h, y(0.46), 0.05 * h, 0.12 * h, coat, rot(-50, cx + 0.25 * h, y(0.52))),
        path(f"M{cx - 0.17 * h:.1f},{y(0.90):.1f} Q{cx - 0.30 * h:.1f},{y(1.00):.1f} {cx - 0.24 * h:.1f},{y(1.10):.1f} Q{cx - 0.14 * h:.1f},{y(1.02):.1f} {cx - 0.07 * h:.1f},{y(0.95):.1f} Z", CREAM),
        path(f"M{cx + 0.17 * h:.1f},{y(0.90):.1f} Q{cx + 0.30 * h:.1f},{y(1.00):.1f} {cx + 0.24 * h:.1f},{y(1.10):.1f} Q{cx + 0.14 * h:.1f},{y(1.02):.1f} {cx + 0.07 * h:.1f},{y(0.95):.1f} Z", CREAM),
        circle(cx, y(0.76), 0.21 * h, coat),
        eye(cx - 0.085 * h, y(0.78), 0.065 * h, look),
        eye(cx + 0.085 * h, y(0.78), 0.065 * h, look),
        path(f"M{cx - 0.08 * h:.1f},{y(0.65):.1f} Q{cx:.1f},{y(0.58):.1f} {cx + 0.08 * h:.1f},{y(0.65):.1f}", stroke="#7a1f14", sw=3 * s + 1),
        line(cx + 0.40 * h, y(0.02), cx + 0.40 * h, y(1.02), WOOD, 5 * s + 1),
        path(f"M{cx + 0.31 * h:.1f},{y(1.16):.1f} V{y(1.02):.1f} H{cx + 0.49 * h:.1f} V{y(1.16):.1f} M{cx + 0.40 * h:.1f},{y(1.02):.1f} V{y(1.18):.1f}",
             stroke="#aebccb", sw=5 * s + 1),
    ])


def crab(cx, base, s=1.0, mood="happy", look=0.0, shade=True):
    h, coat, dark = 120 * s, "#f46a35", "#c2441a"
    y = lambda f: base - f * h
    up = 0.98 if mood in ("happy", "angry", "shocked") else 0.70
    parts = [shadow(cx, base, 0.62 * h)] if shade else []
    parts += [
        line(cx + side * (0.30 + 0.12 * k) * h, y(0.24), cx + side * (0.44 + 0.16 * k) * h, y(0.0), dark, 5 * s + 1.5)
        for side in (-1, 1) for k in range(3)
    ]
    for side in (-1, 1):
        tip = (cx + side * 0.80 * h, y(up))
        parts += [
            path(f"M{cx + side * 0.46 * h:.1f},{y(0.46):.1f} Q{cx + side * 0.80 * h:.1f},{y(0.44):.1f} {tip[0]:.1f},{tip[1] + 0.10 * h:.1f}", stroke=coat, sw=0.09 * h),
            circle(tip[0], tip[1], 0.15 * h, coat),
            path(f"M{tip[0]:.1f},{tip[1]:.1f} l{side * 0.02 * h:.1f},{-0.19 * h:.1f} l{-side * 0.13 * h:.1f},{0.08 * h:.1f} Z", "#fff1e6"),
        ]
    parts += [
        path(
            f"M{cx - 0.56 * h:.1f},{y(0.40):.1f} L{cx - 0.50 * h:.1f},{y(0.70):.1f} L{cx - 0.34 * h:.1f},{y(0.66):.1f} L{cx - 0.22 * h:.1f},{y(0.82):.1f}"
            f" L{cx:.1f},{y(0.74):.1f} L{cx + 0.22 * h:.1f},{y(0.82):.1f} L{cx + 0.34 * h:.1f},{y(0.66):.1f} L{cx + 0.50 * h:.1f},{y(0.70):.1f} L{cx + 0.56 * h:.1f},{y(0.40):.1f} Z",
            coat,
        ),
        ellipse(cx, y(0.38), 0.58 * h, 0.30 * h, coat),
        ellipse(cx, y(0.24), 0.36 * h, 0.12 * h, "#ffb08a", 'opacity="0.55"'),
    ]
    for side in (-1, 1):
        ex, ey = cx + side * 0.17 * h, y(0.50)
        parts.append(ellipse(ex, ey, 0.10 * h, 0.13 * h, SNOW))
        size = 0.055 * h
        parts += [
            circle(ex + look * 0.03 * h, ey + 0.01 * h, size, INK),
            circle(ex + look * 0.03 * h + size * 0.35, ey - size * 0.3, size * 0.32, SNOW),
        ]
    parts.append(path(f"M{cx - 0.12 * h:.1f},{y(0.30):.1f} Q{cx:.1f},{y(0.12):.1f} {cx + 0.12 * h:.1f},{y(0.30):.1f} Z", "#7a1f0a"))
    return "\n".join(parts)


def draw_cover():
    defs = """<defs>
<linearGradient id="night" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#050b16"/>
  <stop offset="0.45" stop-color="#0f213d"/>
  <stop offset="0.78" stop-color="#18385c"/>
  <stop offset="1" stop-color="#0c1b2e"/>
</linearGradient>
<linearGradient id="title" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#ffffff"/>
  <stop offset="1" stop-color="#a8d0f0"/>
</linearGradient>
<linearGradient id="gold" x1="0" y1="0" x2="1" y2="1">
  <stop offset="0" stop-color="#ffe89e"/>
  <stop offset="0.5" stop-color="#e3a83b"/>
  <stop offset="1" stop-color="#8f5d14"/>
</linearGradient>
<linearGradient id="steel" x1="0" y1="0" x2="0" y2="1">
  <stop offset="0" stop-color="#3c4f66"/>
  <stop offset="1" stop-color="#1e2a38"/>
</linearGradient>
<radialGradient id="coreglow">
  <stop offset="0" stop-color="#48e5c2" stop-opacity="0.65"/>
  <stop offset="0.5" stop-color="#228be6" stop-opacity="0.22"/>
  <stop offset="1" stop-color="#228be6" stop-opacity="0"/>
</radialGradient>
<radialGradient id="gatehalo">
  <stop offset="0" stop-color="#ffc24a" stop-opacity="0.45"/>
  <stop offset="1" stop-color="#ffc24a" stop-opacity="0"/>
</radialGradient>
</defs>"""

    # 1. Starry deep-silicon night backdrop & title header
    bg = [
        defs,
        rect(0, 0, COVER_W, COVER_H, "url(#night)"),
        *[circle((k * 197 + 43) % COVER_W, (k * 113 + 29) % 520, 0.8 + (k % 4) * 0.45, SNOW,
                 f'opacity="{0.22 + (k % 5) * 0.14:.2f}"') for k in range(95)],
        *[sparkle(x, y, r) for x, y, r in ((880, 110, 9), (820, 260, 7), (92, 390, 8), (640, 80, 7), (900, 460, 8))],
    ]

    title = [
        label(62, 88, "FROM SILICON TO SUPERVISORS · C++20 & RUST 2024", 24, "#9fc4e6", "start", weight=700, extra='letter-spacing="4.5"'),
        label(58, 198, "OPERATING", 112, "url(#title)", "start", weight=900, extra='letter-spacing="2"'),
        label(58, 304, "SYSTEMS", 112, "url(#title)", "start", weight=900, extra='letter-spacing="2"'),
        label(64, 372, "A Hands-On Approach", 58, "#ffc24a", "start", SERIF, 700, 'font-style="italic"'),
        rect(64, 394, 340, 4, "#ffc24a", 2, extra='opacity="0.8"'),
    ]

    # 2. Upper Tier: Ring 3 User Space Observatory Deck (y = 435..640)
    ring3 = [
        rect(48, 438, 864, 188, "#162b46", 16, "#3b608c", 3),
        rect(64, 422, 236, 32, "#22589c", 8, "#7ab3ef", 2),
        label(182, 444, "RING 3 · USER SPACE", 17, SNOW, font=MONO, weight=800),

        # Left panel: 4-level Page Table & Virtual Memory Map
        rect(74, 470, 250, 136, "#0d1a2d", 10, "#2d4c73", 2),
        label(199, 494, "VIRTUAL ADDRESS SPACE", 15, "#8ec5fc", font=MONO, weight=700),
        rect(90, 508, 102, 24, "#3b2d66", 4, "#8468d4", 1.5),
        label(141, 525, "stack ↓", 14, "#dcd3ff", font=MONO),
        rect(90, 538, 102, 24, "#1c4a38", 4, "#48b88a", 1.5),
        label(141, 555, "heap ↑", 14, "#b8f5d8", font=MONO),
        rect(86, 568, 110, 24, "#1e3a5f", 4, "#5aa2f0", 1.5),
        label(141, 585, ".text / .data", 13, "#cbe3ff", font=MONO),
        # Page walk mini-tree
        rect(210, 508, 98, 84, "#15263d", 6, "#456b96", 1.5),
        label(259, 528, "CR3 → PML4", 12, "#ffc24a", font=MONO),
        label(259, 548, "PDPT → PD", 12, "#9fc4e6", font=MONO),
        label(259, 568, "PT → Frame", 12, "#6ee7b7", font=MONO),
        label(259, 585, "0x7FFF_EF01", 11, SNOW, font=MONO),

        # Right panel: Lock-Free SPSC Ring & Event Loop Switchboard
        rect(636, 470, 250, 136, "#0d1a2d", 10, "#2d4c73", 2),
        label(761, 494, "SPSC RING & kqueue", 15, "#6ee7b7", font=MONO, weight=700),
        *[rect(654 + k * 44, 510, 38, 36, "#1f4e54" if k < 3 else "#162638", 5, "#48e5c2" if k < 3 else "#36506b", 2)
          + label(673 + k * 44, 533, f"[{k}]", 14, SNOW if k < 3 else "#6f8ba6", font=MONO)
          for k in range(5)],
        label(761, 570, "head (Acquire) · tail (Release)", 12, "#ffd98a", font=MONO),
        label(761, 592, "alignas(64) · 0 false sharing", 12, "#9fc4e6", font=MONO),
    ]

    # 3. The Hardware Privilege Gate Bridge (SYSCALL / IDT Trap Gate at center x=480, y=640)
    gate = [
        circle(480, 650, 140, "url(#gatehalo)"),
        # Glowing vertical trap beam from Ring 3 to Ring 0
        rect(442, 575, 76, 175, "#ffc24a", 8, extra='opacity="0.18"'),
        line(462, 575, 462, 745, "#48e5c2", 4, 'stroke-dasharray="8 8"'),
        line(498, 745, 498, 575, "#ffc24a", 4, 'stroke-dasharray="8 8"'),
        # The physical Privilege Boundary line & Gate Arch
        line(36, 654, 924, 654, "#ffc24a", 4, 'stroke-dasharray="12 8"'),
        rect(300, 622, 360, 64, "url(#gold)", 14, "#fff3cf", 3),
        rect(310, 630, 340, 48, "#182436", 10),
        label(480, 652, "TRAP GATE · SYSCALL / SVC #0", 19, "#ffc24a", font=MONO, weight=800),
        label(480, 671, "CPL 3 → CPL 0  ·  swapgs  ·  TSS.rsp0", 13, "#cfe6ff", font=MONO),
    ]

    # Characters at the Ring 3 / Ring 0 boundary:
    # Ferris the Rust Crab (left) with hard hat guarding memory safety & Tux the Linux/OS Penguin (right)
    ring3_crew = [
        crab(404, 616, 0.72, "happy", look=1),
        rect(344, 484, 118, 28, RUST, 6),
        label(403, 504, "// SAFETY: ok", 14, SNOW, font=MONO),
        penguin(566, 616, 0.64, look=-1, left=38, right=-20, scarf=TEAL, hat="hard"),
        rect(516, 462, 108, 28, TEAL, 6),
        label(570, 482, "std::jthread", 14, SNOW, font=MONO),
    ]

    # 4. Lower Tier: Ring 0 Kernel Space & Silicon Die (y = 710..1135)
    silicon = [
        rect(48, 712, 864, 418, "url(#steel)", 18, "#5d7a99", 3.5),
        rect(64, 696, 260, 32, "#1b7a43", 8, "#74e39a", 2),
        label(194, 718, "RING 0 · KERNEL & SILICON", 17, SNOW, font=MONO, weight=800),

        # Center Glowing Apple Silicon / Multi-Core UMA Die
        circle(480, 910, 210, "url(#coreglow)"),
        rect(330, 766, 300, 268, "#0b1524", 16, "#48e5c2", 3),
        # Chip pins along all 4 sides
        *[rect(314, 786 + k * 24, 16, 10, BRASS, 2) for k in range(10)],
        *[rect(630, 786 + k * 24, 16, 10, BRASS, 2) for k in range(10)],
        *[rect(354 + k * 24, 750, 10, 16, BRASS, 2) for k in range(11)],
        *[rect(354 + k * 24, 1034, 10, 16, BRASS, 2) for k in range(11)],

        label(480, 794, "UNIFIED MEMORY SILICON (UMA)", 16, "#48e5c2", font=MONO, weight=800),
    ]

    # 4 CPU Cores + MMU/TLB + GPU/NPU inside the Silicon Die
    cores = []
    for idx in range(4):
        cx = 352 + (idx % 2) * 134
        cy = 810 + (idx // 2) * 74
        cores += [
            rect(cx, cy, 122, 62, "#162b46", 8, "#3e78b2", 2),
            label(cx + 61, cy + 22, f"CORE {idx} · Ring 0", 13, "#8ec5fc", font=MONO, weight=800),
            label(cx + 61, cy + 40, "RIP · RSP · RBP", 11, SNOW, font=MONO),
            label(cx + 61, cy + 54, "L1d 64B · MESI", 11, "#6ee7b7", font=MONO),
        ]

    uma_bar = [
        rect(352, 962, 256, 54, "#133b3a", 8, "#48e5c2", 2),
        label(480, 985, "MMU · TLB · APIC / GICv4 · DMA", 14, "#48e5c2", font=MONO, weight=800),
        label(480, 1005, "Zero-Copy Page Cache · 800 GB/s Bus", 12, "#d8f9f0", font=MONO),
    ]

    # Left of Die: Kernel Scheduler & Process Automaton + Fork the Daemon (PID 1 Supervisor)
    left_kernel = [
        rect(72, 746, 224, 150, "#0f1c2e", 12, "#3b597d", 2),
        label(184, 770, "SCHEDULER & IDT[vec]", 15, "#ffc24a", font=MONO, weight=800),
        rect(88, 784, 192, 28, "#1e3a2f", 5, "#48b88a", 1.5),
        label(184, 803, "Top-Half: hardirq → EOI", 13, "#a8f5cc", font=MONO),
        rect(88, 818, 192, 28, "#1e3352", 5, "#5aa2f0", 1.5),
        label(184, 837, "Bottom-Half: softirq", 13, "#cbe3ff", font=MONO),
        rect(88, 852, 192, 28, "#422329", 5, "#e86b6b", 1.5),
        label(184, 871, "waitpid() · EVFILT_PROC", 13, "#ffd1d1", font=MONO),
        # Daemon supervisor character standing at bottom left of Ring 0
        daemon(176, 1108, 0.96, look=1),
        rect(78, 926, 86, 30, RUST, 7),
        label(121, 947, "PID 1", 18, SNOW, font=MONO, weight=800),
    ]

    # Right of Die: NVMe / NIC / IPC Pipes & Page Frames
    right_kernel = [
        rect(664, 746, 224, 196, "#0f1c2e", 12, "#3b597d", 2),
        label(776, 770, "IPC · VFS · PCIe MSI-X", 15, "#48e5c2", font=MONO, weight=800),
        rect(680, 786, 192, 38, "#262347", 6, "#8c7ae6", 1.5),
        label(776, 804, "pipe(fd) · 64 KiB Ring", 13, "#dcd3ff", font=MONO),
        label(776, 819, "dup2() · close(write_fd)", 11, "#a8a0cf", font=MONO),
        rect(680, 832, 192, 38, "#1b3a3a", 6, "#48e5c2", 1.5),
        label(776, 850, "mmap(MAP_SHARED)", 13, "#b8f9ee", font=MONO),
        label(776, 865, "Zero-Copy Physical Frame", 11, "#82d4c8", font=MONO),
        rect(680, 878, 192, 48, "#382a18", 6, "#f0a348", 1.5),
        label(776, 898, "Free-List Arena (16B)", 13, "#ffe0b2", font=MONO),
        label(776, 916, "Split · Coalesce · Guard", 11, "#d9b47a", font=MONO),

        # Second Rust crab in Ring 0 inspecting physical memory frames
        crab(776, 1108, 0.78, "happy", look=-1),
        rect(704, 962, 144, 28, "#22589c", 6),
        label(776, 981, "PFN 0x8A420", 15, SNOW, font=MONO),
    ]

    # 5. Bottom Plaque & Signpost (y = 1158..1262)
    footer = [
        rect(48, 1162, 434, 88, "#fff6e2", 12, WOOD, 4),
        label(265, 1196, "ZERO FICTIONAL CODE · 100% VERIFIED", 17, "#5a421a", weight=800, extra='letter-spacing="1.2"'),
        label(265, 1226, "54 C++20 & Rust 2024 Programs · 41 Vector Diagrams", 14.5, RUST, font=SERIF, weight=700, extra='font-style="italic"'),

        label(912, 1196, "Processes, Concurrency, Virtual Memory,", 18.5, "#d8e8f8", "end", SERIF, 700),
        label(912, 1228, "IPC, Daemons & Systems Interviews", 18.5, "#ffc24a", "end", SERIF, 700),
    ]

    parts = bg + title + ring3 + gate + ring3_crew + silicon + cores + uma_bar + left_kernel + right_kernel + footer
    desc = (
        "The cover of Operating Systems: A Hands-On Approach. Under a starry night sky, "
        "a cross-section of a computer system is divided by a glowing gold Trap Gate (SYSCALL / SVC #0) "
        "into Ring 3 User Space above and Ring 0 Kernel and Unified Memory Silicon below. "
        "In Ring 3, Ferris the Rust crab and Tux the penguin in a hard hat coordinate virtual address "
        "spaces, four-level page tables (CR3 to PML4), and a lock-free SPSC ring buffer. "
        "In Ring 0 below, Fork the red daemon (PID 1) and a kernel crab supervise a four-core "
        "Unified Memory Silicon die, top-half and bottom-half interrupt handlers, pipes, and shared physical frames."
    )

    OUT.mkdir(parents=True, exist_ok=True)
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {COVER_W} {COVER_H}" '
        f'width="{COVER_W}" height="{COVER_H}" role="img" aria-label="{escape(desc)}">\n'
        + "\n".join(parts)
        + "\n</svg>\n"
    )
    (OUT / "cover.svg").write_text(svg)
    print(f"wrote {OUT / 'cover.svg'}")


if __name__ == "__main__":
    draw_cover()
