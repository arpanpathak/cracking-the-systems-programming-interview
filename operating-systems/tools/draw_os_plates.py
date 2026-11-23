#!/usr/bin/env python3
"""Generate publication-grade Swiss-Modernist / Bauhaus geometric SVG chapter
cover plates (960x400, paired Light + Dark) for all 19 chapters of
*Operating Systems: A Hands-On Approach*.

Uses the exact APCA / OKLCH high-contrast palette and zero-blur architectural
geometry established in draw_m3_plates.py.
"""
import math
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "src" / "art"
W, H = 960, 400

LIGHT = {
    "bg_kv": "#F7F9FC",
    "bg_rl": "#F5FAF8",
    "bg_pay": "#FAF8F3",
    "grid_kv": "#E3EAF4",
    "grid_rl": "#DDEEE9",
    "grid_pay": "#EAE3D7",
    "ink": "#161B26",
    "muted": "#526075",
    "hair": "#D0DAE6",
    "blue": "#1A5FC4",
    "blue_soft": "#DCE9FD",
    "teal": "#0E7168",
    "teal_soft": "#D3EFEA",
    "terra": "#CC5328",
    "terra_soft": "#FBE3DA",
    "ochre": "#D48806",
    "ochre_soft": "#FDF0D1",
    "indigo": "#4F46E5",
    "indigo_soft": "#E5E4FC",
    "surface": "#FFFFFF",
}

# Exact APCA / OKLCH high-contrast dark palette (zero pure-white halation,
# zero neon chroma vibration, zero Gaussian blur filters).
DARK = {
    "bg_kv": "rgba(0, 0, 0, 0.22)",
    "bg_rl": "rgba(0, 0, 0, 0.22)",
    "bg_pay": "rgba(0, 0, 0, 0.22)",
    "grid_kv": "rgba(226, 232, 240, 0.04)",
    "grid_rl": "rgba(226, 232, 240, 0.04)",
    "grid_pay": "rgba(226, 232, 240, 0.04)",
    "ink": "#F2F6FC",
    "muted": "#D0DAE8",
    "hair": "rgba(226, 232, 240, 0.18)",
    "blue": "#89B4FA",
    "blue_soft": "rgba(137, 180, 250, 0.12)",
    "teal": "#89D8D3",
    "teal_soft": "rgba(137, 216, 211, 0.12)",
    "terra": "#F3A6B2",
    "terra_soft": "rgba(243, 166, 178, 0.12)",
    "ochre": "#F2C98A",
    "ochre_soft": "rgba(242, 201, 138, 0.12)",
    "indigo": "#C8B6FF",
    "indigo_soft": "rgba(200, 182, 255, 0.12)",
    "surface": "#121722",
}


def header_svg(aria: str, bg: str, grid_col: str, t: dict) -> list[str]:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" '
        f'shape-rendering="geometricPrecision" text-rendering="geometricPrecision" role="img" aria-label="{escape(aria)}">',
        "  <style>",
        '    .sans { font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }',
        '    .mono { font-family: "SF Mono", SFMono-Regular, ui-monospace, Menlo, Consolas, monospace; }',
        "  </style>",
        f'  <rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="14" fill="{bg}" stroke="{t["hair"]}" stroke-width="1"/>',
    ]
    for gx in range(40, W, 40):
        parts.append(f'  <line x1="{gx}" y1="1" x2="{gx}" y2="{H - 1}" stroke="{grid_col}" stroke-width="0.75"/>')
    for gy in range(40, H, 40):
        parts.append(f'  <line x1="1" y1="{gy}" x2="{W - 1}" y2="{gy}" stroke="{grid_col}" stroke-width="0.75"/>')
    return parts


def swiss_lockup(num: str, title: str, sub1: str, sub2: str, accent: str, t: dict) -> list[str]:
    """Minimalist Swiss editorial chapter lockup."""
    fs = 23 if len(title) > 19 else 25
    return [
        f'  <rect x="44" y="42" width="42" height="4" rx="2" fill="{accent}"/>',
        f'  <text x="44" y="88" class="mono" font-size="38" font-weight="700" fill="{accent}" letter-spacing="-0.03em">{escape(num)}</text>',
        f'  <text x="44" y="132" class="sans" font-size="{fs}" font-weight="750" fill="{t["ink"]}" letter-spacing="-0.015em">{escape(title)}</text>',
        f'  <text x="44" y="158" class="mono" font-size="11" font-weight="600" fill="{t["muted"]}" letter-spacing="0.06em">{escape(sub1)}</text>',
        f'  <text x="44" y="176" class="mono" font-size="11" font-weight="600" fill="{t["muted"]}" letter-spacing="0.06em">{escape(sub2)}</text>',
    ]


def base_plate(num: str, title: str, s1: str, s2: str, bg_key: str, grid_key: str,
               accent_key: str, eq_line: str, t: dict, aria: str) -> list[str]:
    p = header_svg(aria, t[bg_key], t[grid_key], t)
    p += swiss_lockup(num, title, s1, s2, t[accent_key], t)
    p += [
        f'  <line x1="44" y1="336" x2="304" y2="336" stroke="{t["hair"]}" stroke-width="1"/>',
        f'  <text x="44" y="358" class="mono" font-size="10.5" fill="{t["muted"]}">{escape(eq_line)}</text>',
    ]
    return p


def arc_path(cx: float, cy: float, r: float, a1_deg: float, a2_deg: float) -> str:
    a1, a2 = math.radians(a1_deg), math.radians(a2_deg)
    x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
    x2, y2 = cx + r * math.cos(a2), cy + r * math.sin(a2)
    large = 1 if (a2_deg - a1_deg) % 360 > 180 else 0
    return f"M {x1:.2f} {y1:.2f} A {r:.2f} {r:.2f} 0 {large} 1 {x2:.2f} {y2:.2f}"


def arrow_head(x: float, y: float, angle_deg: float, col: str, size: float = 7.0) -> str:
    a = math.radians(angle_deg)
    a1 = a + math.radians(150)
    a2 = a - math.radians(150)
    p1 = f"{x:.1f},{y:.1f}"
    p2 = f"{x + size * math.cos(a1):.1f},{y + size * math.sin(a1):.1f}"
    p3 = f"{x + size * math.cos(a2):.1f},{y + size * math.sin(a2):.1f}"
    return f'  <polygon points="{p1} {p2} {p3}" fill="{col}"/>'


# =============================================================================
# CH 01: THE OPERATING SYSTEM — PRIVILEGE RINGS & MULTIPLEXED HARDWARE PILLARS
# =============================================================================
def plate_ch01(t: dict) -> str:
    p = base_plate(
        "01", "The Operating System", "PRIVILEGE RINGS · ISOLATION", "HARDWARE MULTIPLEXING",
        "bg_kv", "grid_kv", "blue", "Ring 0 (Kernel) ⊃ Ring 3 (User)", t,
        "Chapter 1 geometric artwork: concentric CPU privilege rings from Ring 3 user space to Ring 0 kernel core linked to three multiplexed hardware pillars for CPU, RAM, and I/O."
    )
    cx, cy = 496, 200
    # Outer Ring 3 (User space)
    p.append(f'  <circle cx="{cx}" cy="{cy}" r="134" fill="{t["blue_soft"]}" fill-opacity="0.55" stroke="{t["blue"]}" stroke-width="2"/>')
    p.append(f'  <path d="{arc_path(cx, cy, 134, -140, -40)}" fill="none" stroke="{t["blue"]}" stroke-width="8"/>')
    # Intermediate Ring 1/2 hairline
    p.append(f'  <circle cx="{cx}" cy="{cy}" r="96" fill="none" stroke="{t["hair"]}" stroke-width="1.3" stroke-dasharray="4 5"/>')
    # Ring 0 Kernel boundary
    p.append(f'  <circle cx="{cx}" cy="{cy}" r="66" fill="{t["teal_soft"]}" stroke="{t["teal"]}" stroke-width="2.4"/>')
    p.append(f'  <circle cx="{cx}" cy="{cy}" r="28" fill="{t["surface"]}" stroke="{t["terra"]}" stroke-width="2.4"/>')
    p.append(f'  <circle cx="{cx}" cy="{cy}" r="9" fill="{t["terra"]}"/>')
    p.append(f'  <text x="{cx}" y="{cy - 110}" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["blue"]}">RING 3 · USER</text>')
    p.append(f'  <text x="{cx}" y="{cy + 52}" text-anchor="middle" class="mono" font-size="9.5" font-weight="700" fill="{t["teal"]}">RING 0 · KERNEL</text>')

    # User process nodes orbiting Ring 3
    for deg, lbl in [(-155, "P1"), (155, "P2"), (35, "P3")]:
        a = math.radians(deg)
        nx, ny = cx + 114 * math.cos(a), cy + 114 * math.sin(a)
        p.append(f'  <circle cx="{nx:.1f}" cy="{ny:.1f}" r="14" fill="{t["surface"]}" stroke="{t["blue"]}" stroke-width="2"/>')
        p.append(f'  <text x="{nx:.1f}" y="{ny + 3.5:.1f}" text-anchor="middle" class="mono" font-size="9.5" font-weight="700" fill="{t["blue"]}">{lbl}</text>')

    # Multiplexed bus bridges to 3 hardware pillars
    pillars = [
        (706, "CPU", "TIME SLICES", t["blue"], t["blue_soft"]),
        (782, "RAM", "PAGE FRAMES", t["teal"], t["teal_soft"]),
        (858, "I/O", "DMA · IRQS", t["ochre"], t["ochre_soft"]),
    ]
    for idx, (px, lbl, sub, sc, sf) in enumerate(pillars):
        by = 128 + idx * 72
        p.append(f'  <line x1="{cx + 66}" y1="{cy}" x2="{px}" y2="{by}" stroke="{sc}" stroke-width="1.6" stroke-dasharray="4 4" opacity="0.75"/>')
        p.append(f'  <rect x="{px}" y="82" width="58" height="236" rx="10" fill="{sf}" stroke="{sc}" stroke-width="2"/>')
        p.append(f'  <rect x="{px}" y="82" width="58" height="32" rx="10" fill="{sc}"/>')
        p.append(f'  <text x="{px + 29}" y="102" text-anchor="middle" class="mono" font-size="11.5" font-weight="700" fill="{t["surface"]}">{lbl}</text>')
        for k in range(5):
            sy = 130 + k * 34
            p.append(f'  <rect x="{px + 10}" y="{sy}" width="38" height="20" rx="4" fill="{t["surface"]}" stroke="{sc}" stroke-width="1.3" opacity="{0.95 - k*0.12:.2f}"/>')
    p.append(f'  <text x="811" y="346" text-anchor="middle" class="mono" font-size="10.5" fill="{t["muted"]}">MULTIPLEXED HARDWARE</text>')
    p.append("</svg>\n")
    return "\n".join(p)


# =============================================================================
# CH 02: THE MACHINE — CPU PIPELINE, LATENCY PYRAMID & 64B CACHE LINE
# =============================================================================
def plate_ch02(t: dict) -> str:
    p = base_plate(
        "02", "The Machine", "CPU PIPELINE · CACHE TIERS", "64-BYTE CACHE LINES",
        "bg_kv", "grid_kv", "teal", "L1 (1ns) ≪ L2 (4ns) ≪ L3 ≪ RAM (65ns)", t,
        "Chapter 2 geometric artwork: a 5-stage CPU pipeline above a stepped L1/L2/L3/RAM latency pyramid and a subdivided 64-byte cache line block."
    )
    # Top: 5-stage CPU pipeline
    stages = [
        ("IF", t["blue"], t["blue_soft"]),
        ("ID", t["teal"], t["teal_soft"]),
        ("EX", t["ochre"], t["ochre_soft"]),
        ("MEM", t["indigo"], t["indigo_soft"]),
        ("WB", t["terra"], t["terra_soft"]),
    ]
    p.append(f'  <text x="364" y="64" class="mono" font-size="10" font-weight="700" fill="{t["muted"]}">5-STAGE INSTRUCTION PIPELINE</text>')
    for i, (st, sc, sf) in enumerate(stages):
        sx = 364 + i * 112
        p.append(f'  <rect x="{sx}" y="76" width="90" height="44" rx="8" fill="{sf}" stroke="{sc}" stroke-width="2"/>')
        p.append(f'  <text x="{sx + 45}" y="102" text-anchor="middle" class="mono" font-size="13" font-weight="700" fill="{sc}">{st}</text>')
        if i < 4:
            p.append(f'  <line x1="{sx + 90}" y1="98" x2="{sx + 110}" y2="98" stroke="{t["muted"]}" stroke-width="1.8"/>')
            p.append(arrow_head(sx + 111, 98, 0, t["muted"], 5.5))

    # Bottom-left: Latency pyramid (L1, L2, L3, RAM)
    p.append(f'  <text x="498" y="158" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["teal"]}">MEMORY LATENCY PYRAMID</text>')
    tiers = [
        ("L1 · 1 ns", 92, t["teal"], t["teal_soft"]),
        ("L2 · 4 ns", 148, t["blue"], t["blue_soft"]),
        ("L3 · 12 ns", 204, t["indigo"], t["indigo_soft"]),
        ("DRAM · 65 ns", 264, t["ochre"], t["ochre_soft"]),
    ]
    for i, (lbl, w, sc, sf) in enumerate(tiers):
        tx = 498 - w / 2
        ty = 172 + i * 44
        p.append(f'  <rect x="{tx:.1f}" y="{ty}" width="{w}" height="34" rx="7" fill="{sf}" stroke="{sc}" stroke-width="1.9"/>')
        p.append(f'  <text x="498" y="{ty + 21}" text-anchor="middle" class="mono" font-size="10.5" font-weight="700" fill="{sc}">{lbl}</text>')

    # Bottom-right: 64-byte Cache Line structure
    p.append(f'  <text x="790" y="158" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["blue"]}">64-BYTE CACHE LINE</text>')
    p.append(f'  <rect x="668" y="172" width="244" height="166" rx="10" fill="{t["surface"]}" stroke="{t["hair"]}" stroke-width="1.6"/>')
    # Tag / Index / Offset strip
    hdrs = [(680, 96, "TAG", t["terra"], t["terra_soft"]), (782, 56, "IDX", t["ochre"], t["ochre_soft"]), (844, 56, "OFF", t["teal"], t["teal_soft"])]
    for hx, hw, hl, sc, sf in hdrs:
        p.append(f'  <rect x="{hx}" y="186" width="{hw}" height="30" rx="5" fill="{sf}" stroke="{sc}" stroke-width="1.6"/>')
        p.append(f'  <text x="{hx + hw/2:.1f}" y="205" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{sc}">{hl}</text>')
    # 8 x 8-byte words (2 rows of 4)
    for r in range(2):
        for c in range(4):
            wx = 680 + c * 56
            wy = 232 + r * 46
            idx = r * 4 + c
            col = t["blue"] if idx % 2 == 0 else t["teal"]
            bg = t["blue_soft"] if idx % 2 == 0 else t["teal_soft"]
            p.append(f'  <rect x="{wx}" y="{wy}" width="48" height="36" rx="5" fill="{bg}" stroke="{col}" stroke-width="1.5"/>')
            p.append(f'  <text x="{wx + 24}" y="{wy + 22}" text-anchor="middle" class="mono" font-size="9.5" font-weight="700" fill="{col}">W{idx}</text>')
    p.append("</svg>\n")
    return "\n".join(p)


# =============================================================================
# CH 03: PROCESSES — STATE FSM & FORK() TREE WITH PIDS
# =============================================================================
def plate_ch03(t: dict) -> str:
    p = base_plate(
        "03", "Processes", "PROCESS STATE FSM", "FORK() TREE · PCB · COW",
        "bg_rl", "grid_rl", "blue", "READY -> RUNNING -> BLOCKED", t,
        "Chapter 3 geometric artwork: a three-state process lifecycle automaton paired with a hierarchical fork() process tree showing parent and child PIDs."
    )
    # Left-center: 3-state FSM
    r_pos = (420, 126)
    run_pos = (588, 126)
    blk_pos = (504, 276)

    # Transition curves
    p.append(f'  <path d="M 464 114 Q 504 86 544 114" fill="none" stroke="{t["teal"]}" stroke-width="2.2"/>')
    p.append(arrow_head(545, 114, 30, t["teal"], 6.5))
    p.append(f'  <path d="M 544 138 Q 504 166 464 138" fill="none" stroke="{t["ochre"]}" stroke-width="2"/>')
    p.append(arrow_head(463, 138, 210, t["ochre"], 6.5))
    p.append(f'  <path d="M 578 168 Q 568 232 542 260" fill="none" stroke="{t["terra"]}" stroke-width="2.2"/>')
    p.append(arrow_head(541, 261, 135, t["terra"], 6.5))
    p.append(f'  <path d="M 466 260 Q 438 232 428 168" fill="none" stroke="{t["blue"]}" stroke-width="2.2"/>')
    p.append(arrow_head(428, 167, -100, t["blue"], 6.5))

    p.append(f'  <text x="504" y="88" text-anchor="middle" class="mono" font-size="9.5" fill="{t["teal"]}">dispatch</text>')
    p.append(f'  <text x="504" y="170" text-anchor="middle" class="mono" font-size="9.5" fill="{t["ochre"]}">preempt</text>')
    p.append(f'  <text x="598" y="232" class="mono" font-size="9.5" fill="{t["terra"]}">I/O wait</text>')
    p.append(f'  <text x="404" y="232" text-anchor="end" class="mono" font-size="9.5" fill="{t["blue"]}">wake</text>')

    for (nx, ny), lbl, sc, sf in [
        (r_pos, "READY", t["blue"], t["blue_soft"]),
        (run_pos, "RUNNING", t["teal"], t["teal_soft"]),
        (blk_pos, "BLOCKED", t["terra"], t["terra_soft"]),
    ]:
        p.append(f'  <rect x="{nx - 46}" y="{ny - 24}" width="92" height="48" rx="24" fill="{sf}" stroke="{sc}" stroke-width="2.4"/>')
        p.append(f'  <text x="{nx}" y="{ny + 4}" text-anchor="middle" class="mono" font-size="11.5" font-weight="700" fill="{sc}">{lbl}</text>')

    # Divider hairline
    p.append(f'  <line x1="664" y1="68" x2="664" y2="338" stroke="{t["hair"]}" stroke-width="1.2" stroke-dasharray="4 5"/>')

    # Right: fork() process tree
    p.append(f'  <text x="794" y="68" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["blue"]}">FORK() PROCESS TREE</text>')
    # Orthogonal connectors
    p.append(f'  <path d="M 794 122 L 794 150 M 734 150 L 854 150 M 734 150 L 734 176 M 854 150 L 854 176" fill="none" stroke="{t["blue"]}" stroke-width="2"/>')
    p.append(f'  <path d="M 734 218 L 734 246 M 698 246 L 770 246 M 698 246 L 698 272 M 770 246 L 770 272" fill="none" stroke="{t["teal"]}" stroke-width="1.8"/>')

    nodes = [
        (794, 102, 92, "PID 1", t["ochre"], t["ochre_soft"]),
        (734, 196, 86, "PID 42", t["blue"], t["blue_soft"]),
        (854, 196, 86, "PID 43", t["indigo"], t["indigo_soft"]),
        (698, 292, 64, "108", t["teal"], t["teal_soft"]),
        (770, 292, 64, "109", t["teal"], t["teal_soft"]),
    ]
    for nx, ny, nw, lbl, sc, sf in nodes:
        p.append(f'  <rect x="{nx - nw/2:.1f}" y="{ny - 20}" width="{nw}" height="40" rx="8" fill="{sf}" stroke="{sc}" stroke-width="2"/>')
        p.append(f'  <text x="{nx}" y="{ny + 4}" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="{sc}">{lbl}</text>')
    p.append(f'  <text x="854" y="296" text-anchor="middle" class="mono" font-size="9.5" fill="{t["muted"]}">COW PAGES</text>')
    p.append("</svg>\n")
    return "\n".join(p)


# =============================================================================
# CH 04: THREADS — SHARED ADDRESS SPACE, PARALLEL STACKS & INTERLEAVED TIMELINE
# =============================================================================
def plate_ch04(t: dict) -> str:
    p = base_plate(
        "04", "Threads", "SHARED ADDRESS SPACE", "PRIVATE STACKS · INTERLEAVING",
        "bg_rl", "grid_rl", "indigo", "1 Heap/Code · N Stacks & Registers", t,
        "Chapter 4 geometric artwork: a shared process address space with common code and heap supporting three private thread stacks, beside an interleaved multi-thread execution timeline."
    )
    # Left-center: Shared Address Space box
    p.append(f'  <rect x="358" y="68" width="258" height="270" rx="12" fill="{t["surface"]}" stroke="{t["indigo"]}" stroke-width="2"/>')
    p.append(f'  <text x="487" y="90" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["indigo"]}">PROCESS ADDRESS SPACE</text>')

    # 3 private thread stacks at top
    tcols = [(t["blue"], t["blue_soft"], "T0"), (t["teal"], t["teal_soft"], "T1"), (t["ochre"], t["ochre_soft"], "T2")]
    for i, (sc, sf, lbl) in enumerate(tcols):
        sx = 374 + i * 78
        p.append(f'  <rect x="{sx}" y="106" width="68" height="108" rx="7" fill="{sf}" stroke="{sc}" stroke-width="1.9"/>')
        p.append(f'  <text x="{sx + 34}" y="126" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="{sc}">{lbl}</text>')
        p.append(f'  <text x="{sx + 34}" y="144" text-anchor="middle" class="mono" font-size="9" fill="{t["muted"]}">STACK</text>')
        p.append(f'  <line x1="{sx + 12}" y1="160" x2="{sx + 56}" y2="160" stroke="{sc}" stroke-width="1.4" opacity="0.6"/>')
        p.append(f'  <line x1="{sx + 12}" y1="176" x2="{sx + 56}" y2="176" stroke="{sc}" stroke-width="1.4" opacity="0.4"/>')
        p.append(f'  <text x="{sx + 34}" y="200" text-anchor="middle" class="mono" font-size="8.5" fill="{sc}">PC · SP</text>')

    # Shared Heap + Code slabs below
    p.append(f'  <rect x="374" y="228" width="224" height="44" rx="7" fill="{t["indigo_soft"]}" stroke="{t["indigo"]}" stroke-width="1.8"/>')
    p.append(f'  <text x="486" y="254" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="{t["indigo"]}">SHARED HEAP &amp; GLOBALS</text>')
    p.append(f'  <rect x="374" y="282" width="224" height="40" rx="7" fill="{t["blue_soft"]}" stroke="{t["blue"]}" stroke-width="1.8"/>')
    p.append(f'  <text x="486" y="306" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="{t["blue"]}">SHARED TEXT (CODE)</text>')

    # Right: Interleaved execution timeline
    p.append(f'  <text x="784" y="90" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["teal"]}">INTERLEAVED EXECUTION</text>')
    lanes = [
        (134, "T0", t["blue"], [(654, 52), (766, 44), (862, 46)]),
        (204, "T1", t["teal"], [(706, 60), (810, 52)]),
        (274, "T2", t["ochre"], [(654, 34), (744, 48), (836, 68)]),
    ]
    for ly, lbl, col, segs in lanes:
        p.append(f'  <line x1="650" y1="{ly}" x2="914" y2="{ly}" stroke="{t["hair"]}" stroke-width="1.5"/>')
        p.append(f'  <text x="642" y="{ly + 4}" text-anchor="end" class="mono" font-size="10.5" font-weight="700" fill="{col}">{lbl}</text>')
        for sx, sw in segs:
            p.append(f'  <rect x="{sx}" y="{ly - 14}" width="{sw}" height="28" rx="6" fill="{col}" opacity="0.88"/>')
    # Context-switch vertical dashed markers
    for cx0 in (706, 766, 810, 862):
        p.append(f'  <line x1="{cx0}" y1="108" x2="{cx0}" y2="306" stroke="{t["terra"]}" stroke-width="1.2" stroke-dasharray="3 4" opacity="0.7"/>')
    p.append(f'  <text x="784" y="336" text-anchor="middle" class="mono" font-size="10" fill="{t["muted"]}">TIME  ──&gt;   (CTX SWITCH)</text>')
    p.append("</svg>\n")
    return "\n".join(p)


# =============================================================================
# CH 05: SCHEDULING — CFS RED-BLACK VRUNTIME TREE & MULTI-CORE QUANTUM SLICES
# =============================================================================
def plate_ch05(t: dict) -> str:
    p = base_plate(
        "05", "Scheduling", "CFS RED-BLACK TREE", "VRUNTIME · QUANTUM SLICES",
        "bg_pay", "grid_pay", "ochre", "pick_next = min(vruntime)", t,
        "Chapter 5 geometric artwork: a balanced Completely Fair Scheduler red-black tree highlighting the leftmost minimum-vruntime task alongside multi-core quantum timelines."
    )
    # Left-center: CFS Red-Black Tree
    p.append(f'  <text x="480" y="68" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["ochre"]}">CFS RB-TREE (VRUNTIME)</text>')
    # Edges
    edges = [
        (480, 114, 422, 184), (480, 114, 538, 184),
        (422, 184, 386, 258), (422, 184, 458, 258),
        (538, 184, 508, 258), (538, 184, 570, 258),
    ]
    for x1, y1, x2, y2 in edges:
        p.append(f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{t["hair"]}" stroke-width="2"/>')
    # Highlight leftmost path
    p.append(f'  <line x1="480" y1="114" x2="422" y2="184" stroke="{t["ochre"]}" stroke-width="2.6"/>')
    p.append(f'  <line x1="422" y1="184" x2="386" y2="258" stroke="{t["ochre"]}" stroke-width="2.6"/>')

    # Nodes: (x, y, label, is_red, is_min)
    rb_nodes = [
        (480, 114, "14", False, False),
        (422, 184, "08", True, False),
        (538, 184, "21", False, False),
        (386, 258, "03", False, True),
        (458, 258, "11", False, False),
        (508, 258, "18", True, False),
        (570, 258, "29", True, False),
    ]
    for nx, ny, val, is_red, is_min in rb_nodes:
        if is_min:
            p.append(f'  <circle cx="{nx}" cy="{ny}" r="27" fill="{t["ochre_soft"]}" stroke="{t["ochre"]}" stroke-width="2" stroke-dasharray="4 3"/>')
        sc = t["terra"] if is_red else t["blue"]
        sf = t["terra_soft"] if is_red else t["surface"]
        p.append(f'  <circle cx="{nx}" cy="{ny}" r="18" fill="{sf}" stroke="{sc}" stroke-width="2.4"/>')
        p.append(f'  <text x="{nx}" y="{ny + 4}" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="{sc}">{val}</text>')
    p.append(f'  <text x="386" y="306" text-anchor="middle" class="mono" font-size="9.5" font-weight="700" fill="{t["ochre"]}">MIN NEXT</text>')

    # Right: Multi-core quantum timeline
    p.append(f'  <text x="772" y="68" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["teal"]}">MULTI-CORE QUANTUM SLICES</text>')
    cores = [
        (114, "C0", [(634, 72, t["ochre"], "T03"), (712, 86, t["blue"], "T08"), (804, 104, t["teal"], "T14")]),
        (188, "C1", [(634, 96, t["teal"], "T11"), (736, 74, t["indigo"], "T18"), (816, 92, t["ochre"], "T03")]),
        (262, "C2", [(634, 58, t["terra"], "T21"), (698, 108, t["blue"], "T29"), (812, 96, t["teal"], "T08")]),
    ]
    for cy0, clbl, slices in cores:
        p.append(f'  <text x="622" y="{cy0 + 5}" text-anchor="end" class="mono" font-size="10.5" font-weight="700" fill="{t["muted"]}">{clbl}</text>')
        for sx, sw, sc, tlbl in slices:
            p.append(f'  <rect x="{sx}" y="{cy0 - 20}" width="{sw}" height="40" rx="7" fill="{sc}" opacity="0.86"/>')
            p.append(f'  <text x="{sx + sw/2:.1f}" y="{cy0 + 4}" text-anchor="middle" class="mono" font-size="10.5" font-weight="700" fill="{t["surface"]}">{tlbl}</text>')
    # Quantum tick axis
    p.append(f'  <line x1="634" y1="318" x2="908" y2="318" stroke="{t["hair"]}" stroke-width="1.5"/>')
    for k in range(5):
        tx = 634 + k * 68
        p.append(f'  <line x1="{tx}" y1="312" x2="{tx}" y2="324" stroke="{t["muted"]}" stroke-width="1.4"/>')
    p.append(f'  <text x="772" y="344" text-anchor="middle" class="mono" font-size="10" fill="{t["muted"]}">FAIRNESS EPOCH (Δvruntime)</text>')
    p.append("</svg>\n")
    return "\n".join(p)


# =============================================================================
# CH 06: SYNCHRONIZATION — ATOMIC CAS & RELEASE-ACQUIRE MEMORY BARRIER WALL
# =============================================================================
def plate_ch06(t: dict) -> str:
    p = base_plate(
        "06", "Synchronization", "ATOMIC CAS · LOCK-FREE", "RELEASE-ACQUIRE BARRIER",
        "bg_pay", "grid_pay", "terra", "store(Rel) ──hb──> load(Acq)", t,
        "Chapter 6 geometric artwork: Core 0 and Core 1 separated by a bold release-acquire memory barrier wall with a synchronized happens-before bridge and atomic CAS emblem."
    )
    # Central Memory Barrier Wall
    bx = 630
    p.append(f'  <rect x="{bx - 12}" y="62" width="24" height="276" rx="10" fill="{t["terra_soft"]}" stroke="{t["terra"]}" stroke-width="2.2"/>')
    for gy in range(84, 326, 22):
        p.append(f'  <line x1="{bx - 6}" y1="{gy}" x2="{bx + 6}" y2="{gy}" stroke="{t["terra"]}" stroke-width="1.6" opacity="0.7"/>')
    p.append(f'  <text x="{bx}" y="48" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["terra"]}">MEMORY BARRIER</text>')

    # Core 0 column (left of wall)
    p.append(f'  <text x="472" y="76" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="{t["blue"]}">CORE 0 (PRODUCER)</text>')
    c0_ops = [
        (98, "data = 42", t["blue"], t["blue_soft"]),
        (168, "store_rel(flag, 1)", t["teal"], t["teal_soft"]),
        (246, "CAS(&amp;lock, 0, 1)", t["ochre"], t["ochre_soft"]),
    ]
    for oy, olbl, sc, sf in c0_ops:
        p.append(f'  <rect x="364" y="{oy}" width="216" height="48" rx="9" fill="{sf}" stroke="{sc}" stroke-width="2"/>')
        p.append(f'  <text x="472" y="{oy + 28}" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="{sc}">{olbl}</text>')
    p.append(f'  <line x1="472" y1="146" x2="472" y2="164" stroke="{t["blue"]}" stroke-width="2"/>')
    p.append(arrow_head(472, 166, 90, t["blue"], 6))

    # Core 1 column (right of wall)
    p.append(f'  <text x="794" y="76" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="{t["indigo"]}">CORE 1 (CONSUMER)</text>')
    c1_ops = [
        (168, "load_acq(flag) == 1", t["teal"], t["teal_soft"]),
        (246, "assert(data == 42)", t["indigo"], t["indigo_soft"]),
    ]
    for oy, olbl, sc, sf in c1_ops:
        p.append(f'  <rect x="686" y="{oy}" width="216" height="48" rx="9" fill="{sf}" stroke="{sc}" stroke-width="2"/>')
        p.append(f'  <text x="794" y="{oy + 28}" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="{sc}">{olbl}</text>')
    p.append(f'  <line x1="794" y1="216" x2="794" y2="242" stroke="{t["indigo"]}" stroke-width="2"/>')
    p.append(arrow_head(794, 244, 90, t["indigo"], 6))

    # Synchronizes-with bridge crossing barrier
    p.append(f'  <line x1="580" y1="192" x2="680" y2="192" stroke="{t["teal"]}" stroke-width="3"/>')
    p.append(arrow_head(684, 192, 0, t["teal"], 7))
    p.append(f'  <circle cx="{bx}" cy="192" r="9" fill="{t["surface"]}" stroke="{t["teal"]}" stroke-width="2.6"/>')
    p.append(f'  <circle cx="{bx}" cy="192" r="3.5" fill="{t["teal"]}"/>')

    # Atomic CAS emblem top-right
    p.append(f'  <polygon points="794,96 822,122 794,148 766,122" fill="{t["ochre_soft"]}" stroke="{t["ochre"]}" stroke-width="2"/>')
    p.append(f'  <text x="794" y="126" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["ochre"]}">LOCK</text>')
    p.append(f'  <text x="{bx}" y="362" text-anchor="middle" class="mono" font-size="10" fill="{t["muted"]}">HAPPENS-BEFORE ORDERING GUARANTEE</text>')
    p.append("</svg>\n")
    return "\n".join(p)


# =============================================================================
# CH 07: VIRTUAL MEMORY — 4-LEVEL RADIX PAGE TABLE WALK + TLB FAST-PATH
# =============================================================================
def plate_ch07(t: dict) -> str:
    p = base_plate(
        "07", "Virtual Memory", "4-LEVEL RADIX PAGE WALK", "TLB FAST-PATH · MMU",
        "bg_kv", "grid_kv", "blue", "VA -> CR3 -> PGD..PTE -> PA", t,
        "Chapter 7 geometric artwork: a 48-bit virtual address driving a 4-level radix page table walk from CR3 through PGD, PUD, PMD, and PTE to a 4KB physical frame, with a glowing TLB hit fast-path bypass."
    )
    # Top: 48-bit Virtual Address bit fields
    p.append(f'  <text x="360" y="64" class="mono" font-size="10" font-weight="700" fill="{t["blue"]}">48-BIT VIRTUAL ADDRESS</text>')
    va_fields = [
        (360, 96, "PGD · 9b", t["blue"], t["blue_soft"]),
        (462, 96, "PUD · 9b", t["indigo"], t["indigo_soft"]),
        (564, 96, "PMD · 9b", t["teal"], t["teal_soft"]),
        (666, 96, "PTE · 9b", t["ochre"], t["ochre_soft"]),
        (768, 146, "OFFSET · 12b", t["terra"], t["terra_soft"]),
    ]
    for fx, fw, flbl, sc, sf in va_fields:
        p.append(f'  <rect x="{fx}" y="74" width="{fw}" height="34" rx="6" fill="{sf}" stroke="{sc}" stroke-width="1.8"/>')
        p.append(f'  <text x="{fx + fw/2:.1f}" y="95" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{sc}">{flbl}</text>')

    # Middle: CR3 -> 4-level Radix Page Tables -> Physical Frame
    p.append(f'  <rect x="360" y="168" width="58" height="44" rx="8" fill="{t["surface"]}" stroke="{t["ink"]}" stroke-width="2"/>')
    p.append(f'  <text x="389" y="194" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="{t["ink"]}">CR3</text>')

    tables = [
        (444, "PGD", t["blue"], t["blue_soft"], 1),
        (536, "PUD", t["indigo"], t["indigo_soft"], 2),
        (628, "PMD", t["teal"], t["teal_soft"], 0),
        (720, "PTE", t["ochre"], t["ochre_soft"], 2),
    ]
    # CR3 -> PGD arrow
    p.append(f'  <line x1="418" y1="190" x2="440" y2="190" stroke="{t["ink"]}" stroke-width="1.8"/>')
    p.append(arrow_head(442, 190, 0, t["ink"], 5.5))

    for idx, (tx, tlbl, sc, sf, sel_row) in enumerate(tables):
        p.append(f'  <rect x="{tx}" y="142" width="66" height="96" rx="8" fill="{t["surface"]}" stroke="{sc}" stroke-width="2"/>')
        p.append(f'  <rect x="{tx}" y="142" width="66" height="22" rx="8" fill="{sc}"/>')
        p.append(f'  <text x="{tx + 33}" y="157" text-anchor="middle" class="mono" font-size="9.5" font-weight="700" fill="{t["surface"]}">{tlbl}</text>')
        for r in range(3):
            ry = 172 + r * 20
            fill = sf if r == sel_row else "none"
            p.append(f'  <rect x="{tx + 8}" y="{ry}" width="50" height="14" rx="3" fill="{fill}" stroke="{sc}" stroke-width="{1.6 if r == sel_row else 0.8}" opacity="{1.0 if r == sel_row else 0.45}"/>')
        # Vertical index drop from VA field
        vx = va_fields[idx][0] + 48
        p.append(f'  <line x1="{vx}" y1="108" x2="{tx + 33}" y2="140" stroke="{sc}" stroke-width="1.3" stroke-dasharray="3 3"/>')
        # Arrow to next table or Frame
        sel_y = 179 + sel_row * 20
        nx = tables[idx + 1][0] if idx < 3 else 822
        p.append(f'  <path d="M {tx + 58} {sel_y} C {tx + 78} {sel_y} {nx - 14} 190 {nx - 4} 190" fill="none" stroke="{sc}" stroke-width="2"/>')
        p.append(arrow_head(nx - 2, 190, 0, sc, 5.5))

    # Physical 4KB Frame on right
    p.append(f'  <rect x="822" y="142" width="92" height="96" rx="10" fill="{t["terra_soft"]}" stroke="{t["terra"]}" stroke-width="2.4"/>')
    p.append(f'  <text x="868" y="182" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="{t["terra"]}">4 KB</text>')
    p.append(f'  <text x="868" y="200" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["terra"]}">FRAME</text>')
    p.append(f'  <text x="868" y="220" text-anchor="middle" class="mono" font-size="9" fill="{t["muted"]}">PHYS RAM</text>')

    # Bottom: TLB Hit Fast-Path Bypass
    p.append(f'  <rect x="444" y="282" width="242" height="48" rx="24" fill="{t["teal_soft"]}" stroke="{t["teal"]}" stroke-width="2.4"/>')
    p.append(f'  <text x="565" y="304" text-anchor="middle" class="mono" font-size="11.5" font-weight="700" fill="{t["teal"]}">TLB HIT FAST-PATH</text>')
    p.append(f'  <text x="565" y="320" text-anchor="middle" class="mono" font-size="9.5" fill="{t["muted"]}">VPN -&gt; PFN IN 1 CYCLE</text>')
    # Fast-path bypass lines
    p.append(f'  <path d="M 389 212 L 389 306 L 440 306" fill="none" stroke="{t["teal"]}" stroke-width="2.4"/>')
    p.append(arrow_head(442, 306, 0, t["teal"], 6))
    p.append(f'  <path d="M 686 306 L 868 306 L 868 242" fill="none" stroke="{t["teal"]}" stroke-width="2.4"/>')
    p.append(arrow_head(868, 240, -90, t["teal"], 6))

    p.append("</svg>\n")
    return "\n".join(p)


# =============================================================================
# CH 08: MEMORY ALLOCATION — BUDDY POWER-OF-2 BLOCKS & SLAB COALESCING
# =============================================================================
def plate_ch08(t: dict) -> str:
    p = base_plate(
        "08", "Memory Allocation", "BUDDY POWER-OF-2 · SLAB", "FREE-LIST COALESCING",
        "bg_rl", "grid_rl", "teal", "buddy(addr, k) = addr ^ (1 << k)", t,
        "Chapter 8 geometric artwork: recursive power-of-2 buddy allocator splits with coalescing arcs above a uniform fixed-size slab cache magazine."
    )
    # Top: Buddy Allocator power-of-2 hierarchy
    p.append(f'  <text x="362" y="64" class="mono" font-size="10" font-weight="700" fill="{t["teal"]}">BUDDY ALLOCATOR (POWER-OF-2 SPLITS)</text>')
    # Level 0: 64 KB
    p.append(f'  <rect x="362" y="74" width="548" height="32" rx="6" fill="{t["blue_soft"]}" stroke="{t["blue"]}" stroke-width="1.8"/>')
    p.append(f'  <text x="636" y="94" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="{t["blue"]}">64 KB ARENA (ORDER 4)</text>')
    # Level 1: 32 KB | 32 KB
    p.append(f'  <rect x="362" y="114" width="270" height="32" rx="6" fill="{t["teal_soft"]}" stroke="{t["teal"]}" stroke-width="1.8"/>')
    p.append(f'  <text x="497" y="134" text-anchor="middle" class="mono" font-size="10.5" font-weight="700" fill="{t["teal"]}">32 KB (SPLIT)</text>')
    p.append(f'  <rect x="640" y="114" width="270" height="32" rx="6" fill="{t["surface"]}" stroke="{t["hair"]}" stroke-width="1.5" stroke-dasharray="5 4"/>')
    p.append(f'  <text x="775" y="134" text-anchor="middle" class="mono" font-size="10.5" fill="{t["muted"]}">32 KB (FREE)</text>')
    # Level 2: 8 | 8 | 16 | 32
    lvl2 = [
        (362, 62, "8K", t["ochre"], t["ochre_soft"], True),
        (430, 62, "8K", t["ochre"], t["ochre_soft"], True),
        (498, 134, "16 KB · USED", t["indigo"], t["indigo_soft"], False),
        (640, 270, "32 KB · FREE", t["muted"], t["surface"], False),
    ]
    for lx, lw, llbl, sc, sf, is_buddy in lvl2:
        dash = ' stroke-dasharray="4 3"' if is_buddy else ""
        p.append(f'  <rect x="{lx}" y="154" width="{lw}" height="34" rx="6" fill="{sf}" stroke="{sc}" stroke-width="1.8"{dash}/>')
        p.append(f'  <text x="{lx + lw/2:.1f}" y="175" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{sc}">{llbl}</text>')
    # Coalescing merge arc between the two 8K buddies
    p.append(f'  <path d="M 393 190 Q 427 222 461 190" fill="none" stroke="{t["terra"]}" stroke-width="2.2"/>')
    p.append(f'  <text x="427" y="220" text-anchor="middle" class="mono" font-size="9.5" font-weight="700" fill="{t["terra"]}">COALESCE -&gt; 16K</text>')

    # Bottom: Slab Allocator fixed-size magazine
    p.append(f'  <text x="362" y="256" class="mono" font-size="10" font-weight="700" fill="{t["blue"]}">SLAB CACHE MAGAZINE (64 B OBJECTS · ZERO INTERNAL FRAG)</text>')
    p.append(f'  <rect x="362" y="268" width="548" height="72" rx="10" fill="{t["surface"]}" stroke="{t["blue"]}" stroke-width="1.8"/>')
    used_mask = [1, 1, 0, 1, 0, 1, 1, 0]
    free_xs = []
    for i, used in enumerate(used_mask):
        sx = 374 + i * 66
        if used:
            p.append(f'  <rect x="{sx}" y="282" width="56" height="44" rx="6" fill="{t["teal_soft"]}" stroke="{t["teal"]}" stroke-width="1.8"/>')
            p.append(f'  <text x="{sx + 28}" y="308" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["teal"]}">OBJ</text>')
        else:
            p.append(f'  <rect x="{sx}" y="282" width="56" height="44" rx="6" fill="{t["ochre_soft"]}" stroke="{t["ochre"]}" stroke-width="1.6" stroke-dasharray="4 3"/>')
            p.append(f'  <text x="{sx + 28}" y="308" text-anchor="middle" class="mono" font-size="9.5" font-weight="700" fill="{t["ochre"]}">FREE</text>')
            free_xs.append(sx + 28)
    # Free-list pointer chain connecting free slots
    for i in range(len(free_xs) - 1):
        x1, x2 = free_xs[i], free_xs[i + 1]
        p.append(f'  <path d="M {x1} 280 Q {(x1 + x2)/2:.1f} 254 {x2} 280" fill="none" stroke="{t["ochre"]}" stroke-width="1.8"/>')
    p.append("</svg>\n")
    return "\n".join(p)


# =============================================================================
# CH 09: SYSTEM CALLS — SYSCALL / SYSRET TRAP GATE & MSR DISPATCH
# =============================================================================
def plate_ch09(t: dict) -> str:
    p = base_plate(
        "09", "System Calls", "SYSCALL / SYSRET GATE", "MSR DISPATCH · KERNEL ABI",
        "bg_pay", "grid_pay", "ochre", "Ring 3 -> LSTAR MSR -> Ring 0", t,
        "Chapter 9 geometric artwork: a horizontal user/kernel privilege boundary crossed by a SYSCALL trap gate descending into MSR LSTAR dispatch and ascending back through SYSRET."
    )
    # Horizontal User / Kernel boundary
    by = 200
    p.append(f'  <line x1="350" y1="{by}" x2="920" y2="{by}" stroke="{t["terra"]}" stroke-width="2.4" stroke-dasharray="8 5"/>')
    p.append(f'  <text x="916" y="{by - 12}" text-anchor="end" class="mono" font-size="10" font-weight="700" fill="{t["blue"]}">USER SPACE (RING 3)</text>')
    p.append(f'  <text x="916" y="{by + 20}" text-anchor="end" class="mono" font-size="10" font-weight="700" fill="{t["terra"]}">KERNEL SPACE (RING 0)</text>')

    # User caller block (top-left)
    p.append(f'  <rect x="364" y="84" width="166" height="54" rx="9" fill="{t["blue_soft"]}" stroke="{t["blue"]}" stroke-width="2"/>')
    p.append(f'  <text x="447" y="108" text-anchor="middle" class="mono" font-size="11.5" font-weight="700" fill="{t["blue"]}">write(fd, buf, n)</text>')
    p.append(f'  <text x="447" y="126" text-anchor="middle" class="mono" font-size="9.5" fill="{t["muted"]}">RAX = 1 · RDI/RSI/RDX</text>')

    # User return block (top-right)
    p.append(f'  <rect x="738" y="84" width="156" height="54" rx="9" fill="{t["teal_soft"]}" stroke="{t["teal"]}" stroke-width="2"/>')
    p.append(f'  <text x="816" y="108" text-anchor="middle" class="mono" font-size="11.5" font-weight="700" fill="{t["teal"]}">RETURN (RAX)</text>')
    p.append(f'  <text x="816" y="126" text-anchor="middle" class="mono" font-size="9.5" fill="{t["muted"]}">RESTORE RIP · RFLAGS</text>')

    # SYSCALL Trap Gate diamond on boundary (x=447, y=200)
    p.append(f'  <polygon points="447,168 492,200 447,232 402,200" fill="{t["ochre_soft"]}" stroke="{t["ochre"]}" stroke-width="2.4"/>')
    p.append(f'  <text x="447" y="204" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["ochre"]}">SYSCALL</text>')

    # SYSRET Gate diamond on boundary (x=816, y=200)
    p.append(f'  <polygon points="816,168 861,200 816,232 771,200" fill="{t["teal_soft"]}" stroke="{t["teal"]}" stroke-width="2.4"/>')
    p.append(f'  <text x="816" y="204" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["teal"]}">SYSRET</text>')

    # Kernel MSR LSTAR & sys_call_table below boundary
    p.append(f'  <rect x="386" y="274" width="122" height="56" rx="9" fill="{t["terra_soft"]}" stroke="{t["terra"]}" stroke-width="2"/>')
    p.append(f'  <text x="447" y="298" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="{t["terra"]}">MSR LSTAR</text>')
    p.append(f'  <text x="447" y="316" text-anchor="middle" class="mono" font-size="9" fill="{t["muted"]}">entry_SYSCALL_64</text>')

    p.append(f'  <rect x="556" y="264" width="176" height="76" rx="10" fill="{t["surface"]}" stroke="{t["indigo"]}" stroke-width="2"/>')
    p.append(f'  <text x="644" y="286" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["indigo"]}">sys_call_table[nr]</text>')
    for i, sl in enumerate(["[0] sys_read", "[1] sys_write", "[2] sys_open"]):
        sy = 294 + i * 14
        col = t["ochre"] if i == 1 else t["muted"]
        p.append(f'  <text x="644" y="{sy + 10}" text-anchor="middle" class="mono" font-size="9.5" font-weight="{700 if i == 1 else 500}" fill="{col}">{sl}</text>')

    # Flow arrows
    p.append(f'  <line x1="447" y1="138" x2="447" y2="164" stroke="{t["ochre"]}" stroke-width="2.4"/>')
    p.append(arrow_head(447, 166, 90, t["ochre"], 6))
    p.append(f'  <line x1="447" y1="232" x2="447" y2="270" stroke="{t["terra"]}" stroke-width="2.4"/>')
    p.append(arrow_head(447, 272, 90, t["terra"], 6))
    p.append(f'  <line x1="508" y1="302" x2="552" y2="302" stroke="{t["indigo"]}" stroke-width="2.2"/>')
    p.append(arrow_head(554, 302, 0, t["indigo"], 6))
    p.append(f'  <path d="M 732 302 L 816 302 L 816 236" fill="none" stroke="{t["teal"]}" stroke-width="2.4"/>')
    p.append(arrow_head(816, 234, -90, t["teal"], 6))
    p.append(f'  <line x1="816" y1="168" x2="816" y2="142" stroke="{t["teal"]}" stroke-width="2.4"/>')
    p.append(arrow_head(816, 140, -90, t["teal"], 6))

    p.append("</svg>\n")
    return "\n".join(p)


# =============================================================================
# CH 10: SIGNALS — ASYNC BITMASK & PC PREEMPTION INTO HANDLER FRAME
# =============================================================================
def plate_ch10(t: dict) -> str:
    p = base_plate(
        "10", "Signals", "ASYNC BITMASK · SIGPENDING", "PC PREEMPTION · HANDLER",
        "bg_pay", "grid_pay", "terra", "deliver = sigpending & ~sigmask", t,
        "Chapter 10 geometric artwork: signal pending and mask bitfields triggering an asynchronous interruption of the normal program counter into a signal handler frame and sigreturn."
    )
    # Top: sigpending & sigmask bitfields
    sigs = [("HUP", 0, 0), ("INT", 1, 0), ("QUIT", 0, 1), ("ILL", 0, 0), ("ALRM", 1, 1), ("TERM", 1, 0), ("USR1", 0, 0), ("CHLD", 0, 1)]
    p.append(f'  <text x="362" y="64" class="mono" font-size="9.5" font-weight="700" fill="{t["terra"]}">SIGPENDING</text>')
    p.append(f'  <text x="362" y="114" class="mono" font-size="9.5" font-weight="700" fill="{t["muted"]}">SIGMASK</text>')
    for i, (name, pend, mask) in enumerate(sigs):
        bx = 446 + i * 58
        deliver = pend and not mask
        # Pending row
        sc = t["terra"] if deliver else (t["ochre"] if pend else t["hair"])
        sf = t["terra_soft"] if deliver else (t["ochre_soft"] if pend else t["surface"])
        p.append(f'  <rect x="{bx}" y="48" width="50" height="30" rx="5" fill="{sf}" stroke="{sc}" stroke-width="{2.0 if deliver else 1.2}"/>')
        p.append(f'  <text x="{bx + 25}" y="67" text-anchor="middle" class="mono" font-size="9.5" font-weight="700" fill="{sc if pend else t["muted"]}">{name}</text>')
        # Mask row
        mc = t["indigo"] if mask else t["hair"]
        mf = t["indigo_soft"] if mask else t["surface"]
        p.append(f'  <rect x="{bx}" y="92" width="50" height="28" rx="5" fill="{mf}" stroke="{mc}" stroke-width="1.3"/>')
        p.append(f'  <text x="{bx + 25}" y="110" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{mc if mask else t["muted"]}">{mask}</text>')

    # Async delivery drop from INT bit (i=1 -> bx=504, center=529)
    p.append(f'  <line x1="529" y1="120" x2="529" y2="274" stroke="{t["terra"]}" stroke-width="2.2" stroke-dasharray="5 4"/>')
    p.append(arrow_head(529, 276, 90, t["terra"], 6.5))
    p.append(f'  <text x="539" y="156" class="mono" font-size="9.5" font-weight="700" fill="{t["terra"]}">ASYNC INTERRUPT (SIGINT)</text>')

    # Normal PC execution rail (y=286)
    p.append(f'  <line x1="362" y1="286" x2="520" y2="286" stroke="{t["blue"]}" stroke-width="3.2"/>')
    p.append(f'  <circle cx="529" cy="286" r="8" fill="{t["terra"]}"/>')
    p.append(f'  <line x1="538" y1="286" x2="776" y2="286" stroke="{t["hair"]}" stroke-width="2" stroke-dasharray="4 5"/>')
    p.append(f'  <line x1="786" y1="286" x2="910" y2="286" stroke="{t["blue"]}" stroke-width="3.2"/>')
    p.append(arrow_head(912, 286, 0, t["blue"], 6.5))
    p.append(f'  <text x="440" y="314" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["blue"]}">NORMAL PC STREAM</text>')
    p.append(f'  <text x="850" y="314" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["blue"]}">RESUME PC</text>')

    # Elevated Signal Handler Frame (x=576..748, y=180..248)
    p.append(f'  <path d="M 529 278 L 529 214 L 572 214" fill="none" stroke="{t["terra"]}" stroke-width="2.4"/>')
    p.append(arrow_head(574, 214, 0, t["terra"], 6))
    p.append(f'  <rect x="576" y="176" width="174" height="72" rx="10" fill="{t["terra_soft"]}" stroke="{t["terra"]}" stroke-width="2.2"/>')
    p.append(f'  <text x="663" y="204" text-anchor="middle" class="mono" font-size="11.5" font-weight="700" fill="{t["terra"]}">HANDLER FRAME</text>')
    p.append(f'  <text x="663" y="224" text-anchor="middle" class="mono" font-size="9.5" fill="{t["muted"]}">saved ucontext_t</text>')
    p.append(f'  <path d="M 750 214 L 784 214 L 784 278" fill="none" stroke="{t["teal"]}" stroke-width="2.4"/>')
    p.append(arrow_head(784, 280, 90, t["teal"], 6))
    p.append(f'  <text x="836" y="218" class="mono" font-size="9.5" font-weight="700" fill="{t["teal"]}">sigreturn()</text>')

    p.append("</svg>\n")
    return "\n".join(p)


# =============================================================================
# CH 11: INTER-PROCESS COMMUNICATION — PIPE, MMAP SHM & UNIX DOMAIN SOCKETS
# =============================================================================
def plate_ch11(t: dict) -> str:
    p = base_plate(
        "11", "IPC", "PIPE · MMAP SHM", "UNIX DOMAIN SOCKETS",
        "bg_kv", "grid_kv", "teal", "Proc A ──[kernel/shm]──> Proc B", t,
        "Chapter 11 geometric artwork: two isolated processes bridged by three distinct IPC conduits: a ring-buffer pipe, a zero-copy mmap shared-memory region, and a bidirectional Unix domain socket."
    )
    # Left Proc A & Right Proc B pillars
    p.append(f'  <rect x="358" y="68" width="76" height="264" rx="10" fill="{t["blue_soft"]}" stroke="{t["blue"]}" stroke-width="2.2"/>')
    p.append(f'  <text x="396" y="196" text-anchor="middle" class="mono" font-size="12" font-weight="700" fill="{t["blue"]}">PROC</text>')
    p.append(f'  <text x="396" y="214" text-anchor="middle" class="mono" font-size="14" font-weight="700" fill="{t["blue"]}">A</text>')

    p.append(f'  <rect x="838" y="68" width="76" height="264" rx="10" fill="{t["teal_soft"]}" stroke="{t["teal"]}" stroke-width="2.2"/>')
    p.append(f'  <text x="876" y="196" text-anchor="middle" class="mono" font-size="12" font-weight="700" fill="{t["teal"]}">PROC</text>')
    p.append(f'  <text x="876" y="214" text-anchor="middle" class="mono" font-size="14" font-weight="700" fill="{t["teal"]}">B</text>')

    # Conduit 1 (Top): Pipe Ring Buffer
    y1 = 104
    p.append(f'  <line x1="434" y1="{y1}" x2="492" y2="{y1}" stroke="{t["blue"]}" stroke-width="2.2"/>')
    p.append(arrow_head(494, y1, 0, t["blue"], 6))
    for i in range(6):
        bx = 498 + i * 46
        filled = i in (1, 2, 3, 4)
        p.append(f'  <rect x="{bx}" y="{y1 - 18}" width="40" height="36" rx="5" fill="{t["blue_soft"] if filled else t["surface"]}" stroke="{t["blue"]}" stroke-width="1.8"/>')
    p.append(f'  <line x1="774" y1="{y1}" x2="834" y2="{y1}" stroke="{t["blue"]}" stroke-width="2.2"/>')
    p.append(arrow_head(836, y1, 0, t["blue"], 6))
    p.append(f'  <text x="636" y="{y1 - 26}" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["blue"]}">1 · PIPE RING BUFFER (64 KB)</text>')

    # Conduit 2 (Middle): Shared Memory mmap region (zero-copy)
    y2 = 200
    p.append(f'  <rect x="478" y="{y2 - 28}" width="316" height="56" rx="10" fill="{t["ochre_soft"]}" stroke="{t["ochre"]}" stroke-width="2.4"/>')
    p.append(f'  <line x1="434" y1="{y2}" x2="478" y2="{y2}" stroke="{t["ochre"]}" stroke-width="3"/>')
    p.append(f'  <line x1="794" y1="{y2}" x2="838" y2="{y2}" stroke="{t["ochre"]}" stroke-width="3"/>')
    p.append(f'  <text x="636" y="{y2 - 4}" text-anchor="middle" class="mono" font-size="11.5" font-weight="700" fill="{t["ochre"]}">2 · MMAP SHARED MEMORY</text>')
    p.append(f'  <text x="636" y="{y2 + 14}" text-anchor="middle" class="mono" font-size="9.5" fill="{t["muted"]}">ZERO-COPY PHYSICAL FRAMES</text>')

    # Conduit 3 (Bottom): Unix Domain Socket (full-duplex)
    y3 = 296
    p.append(f'  <line x1="438" y1="{y3 - 10}" x2="832" y2="{y3 - 10}" stroke="{t["indigo"]}" stroke-width="2.2"/>')
    p.append(arrow_head(834, y3 - 10, 0, t["indigo"], 6))
    p.append(f'  <line x1="834" y1="{y3 + 10}" x2="440" y2="{y3 + 10}" stroke="{t["teal"]}" stroke-width="2.2"/>')
    p.append(arrow_head(438, y3 + 10, 180, t["teal"], 6))
    p.append(f'  <rect x="556" y="{y3 - 18}" width="160" height="36" rx="18" fill="{t["surface"]}" stroke="{t["indigo"]}" stroke-width="1.8"/>')
    p.append(f'  <text x="636" y="{y3 + 4}" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["indigo"]}">AF_UNIX · FD PASS</text>')
    p.append(f'  <text x="636" y="{y3 + 38}" text-anchor="middle" class="mono" font-size="10" fill="{t["muted"]}">3 · FULL-DUPLEX SOCKET</text>')

    p.append("</svg>\n")
    return "\n".join(p)


# =============================================================================
# CH 12: FILE SYSTEMS — INODE POINTERS & WAL JOURNAL COMMIT BARRIER
# =============================================================================
def plate_ch12(t: dict) -> str:
    p = base_plate(
        "12", "File Systems", "INODE · BLOCK POINTERS", "WAL JOURNAL · NVMe BLOCKS",
        "bg_rl", "grid_rl", "blue", "inode -> direct[] | indirect -> WAL", t,
        "Chapter 12 geometric artwork: an inode fanning out to direct and indirect data blocks alongside a write-ahead journal crossing a commit barrier into persistent NVMe blocks."
    )
    # Left-center: Inode -> Direct & Indirect blocks
    p.append(f'  <text x="488" y="64" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["blue"]}">INODE INDEX TOPOLOGY</text>')
    p.append(f'  <rect x="360" y="132" width="94" height="120" rx="10" fill="{t["blue_soft"]}" stroke="{t["blue"]}" stroke-width="2.2"/>')
    p.append(f'  <text x="407" y="156" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="{t["blue"]}">INODE</text>')
    p.append(f'  <text x="407" y="176" text-anchor="middle" class="mono" font-size="9" fill="{t["muted"]}">mode · size</text>')
    for k in range(3):
        p.append(f'  <circle cx="442" cy="{196 + k * 20}" r="3.5" fill="{t["blue"]}"/>')

    # Direct blocks D0, D1
    for i, (by, lbl) in enumerate([(88, "DIRECT 0"), (148, "DIRECT 1")]):
        p.append(f'  <path d="M 454 {196 + i * 20} C 484 {196 + i * 20} 488 {by + 20} 516 {by + 20}" fill="none" stroke="{t["teal"]}" stroke-width="2"/>')
        p.append(f'  <rect x="518" y="{by}" width="92" height="40" rx="7" fill="{t["teal_soft"]}" stroke="{t["teal"]}" stroke-width="1.8"/>')
        p.append(f'  <text x="564" y="{by + 24}" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["teal"]}">{lbl}</text>')

    # Indirect pointer block -> 2 leaf blocks
    p.append(f'  <path d="M 454 236 C 484 236 488 236 516 236" fill="none" stroke="{t["ochre"]}" stroke-width="2"/>')
    p.append(f'  <rect x="518" y="216" width="92" height="40" rx="7" fill="{t["ochre_soft"]}" stroke="{t["ochre"]}" stroke-width="1.8"/>')
    p.append(f'  <text x="564" y="240" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["ochre"]}">INDIRECT</text>')
    for i, lx in enumerate([518, 568]):
        p.append(f'  <line x1="564" y1="256" x2="{lx + 20}" y2="288" stroke="{t["ochre"]}" stroke-width="1.6"/>')
        p.append(f'  <rect x="{lx}" y="290" width="42" height="34" rx="5" fill="{t["surface"]}" stroke="{t["ochre"]}" stroke-width="1.6"/>')
        p.append(f'  <text x="{lx + 21}" y="311" text-anchor="middle" class="mono" font-size="9.5" font-weight="700" fill="{t["ochre"]}">B{i}</text>')

    # Right: WAL Journal -> Commit Barrier -> NVMe Blocks
    p.append(f'  <text x="782" y="64" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["terra"]}">WAL JOURNAL COMMIT</text>')
    wal_items = [("TXB", t["blue"], t["blue_soft"]), ("LOG", t["teal"], t["teal_soft"]), ("CMT", t["ochre"], t["ochre_soft"])]
    for i, (wl, sc, sf) in enumerate(wal_items):
        wx = 656 + i * 54
        p.append(f'  <rect x="{wx}" y="96" width="46" height="62" rx="7" fill="{sf}" stroke="{sc}" stroke-width="1.8"/>')
        p.append(f'  <text x="{wx + 23}" y="131" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{sc}">{wl}</text>')

    # Vertical FSYNC Commit Barrier
    p.append(f'  <line x1="826" y1="78" x2="826" y2="338" stroke="{t["terra"]}" stroke-width="2.6" stroke-dasharray="6 4"/>')
    p.append(f'  <text x="826" y="356" text-anchor="middle" class="mono" font-size="9.5" font-weight="700" fill="{t["terra"]}">FSYNC BARRIER</text>')

    # NVMe 4KB persistent blocks to right of barrier
    for r in range(4):
        ny = 94 + r * 58
        p.append(f'  <rect x="844" y="{ny}" width="66" height="44" rx="7" fill="{t["teal_soft"]}" stroke="{t["teal"]}" stroke-width="1.8"/>')
        p.append(f'  <text x="877" y="{ny + 26}" text-anchor="middle" class="mono" font-size="9.5" font-weight="700" fill="{t["teal"]}">LBA {r}</text>')
    # Checkpoint arrow
    p.append(f'  <path d="M 736 158 L 736 254 L 838 254" fill="none" stroke="{t["teal"]}" stroke-width="2"/>')
    p.append(arrow_head(840, 254, 0, t["teal"], 6))
    p.append(f'  <text x="736" y="278" text-anchor="middle" class="mono" font-size="9.5" fill="{t["muted"]}">CHECKPOINT</text>')

    p.append("</svg>\n")
    return "\n".join(p)


# =============================================================================
# CH 13: I/O & EVENT LOOPS — EPOLL RB-TREE & IO_URING SQ/CQ RINGS
# =============================================================================
def plate_ch13(t: dict) -> str:
    p = base_plate(
        "13", "I/O & Event Loops", "EPOLL RB-TREE · READINESS", "IO_URING SQ / CQ RINGS",
        "bg_kv", "grid_kv", "indigo", "0 syscalls/op via shared SQ/CQ", t,
        "Chapter 13 geometric artwork: an epoll readiness red-black tree and ready queue on the left paired with interlocking io_uring Submission Queue and Completion Queue lock-free ring buffers on the right."
    )
    # Left-center: epoll RB-Tree + Ready Queue
    p.append(f'  <text x="458" y="64" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["indigo"]}">EPOLL INTEREST RB-TREE</text>')
    ep_edges = [(458, 106, 412, 160), (458, 106, 504, 160), (412, 160, 384, 212), (412, 160, 440, 212), (504, 160, 532, 212)]
    for x1, y1, x2, y2 in ep_edges:
        p.append(f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{t["hair"]}" stroke-width="1.8"/>')
    ep_nodes = [
        (458, 106, "fd7", t["indigo"], t["indigo_soft"]),
        (412, 160, "fd4", t["terra"], t["terra_soft"]),
        (504, 160, "fd9", t["indigo"], t["indigo_soft"]),
        (384, 212, "fd2", t["blue"], t["blue_soft"]),
        (440, 212, "fd5", t["teal"], t["teal_soft"]),
        (532, 212, "fd12", t["teal"], t["teal_soft"]),
    ]
    for nx, ny, nl, sc, sf in ep_nodes:
        p.append(f'  <circle cx="{nx}" cy="{ny}" r="16" fill="{sf}" stroke="{sc}" stroke-width="2"/>')
        p.append(f'  <text x="{nx}" y="{ny + 3.5}" text-anchor="middle" class="mono" font-size="9" font-weight="700" fill="{sc}">{nl}</text>')

    # Ready list queue below RB-tree
    p.append(f'  <text x="458" y="266" text-anchor="middle" class="mono" font-size="9.5" font-weight="700" fill="{t["teal"]}">READY LIST (O(1) POP)</text>')
    for i, rfd in enumerate(["fd4", "fd9", "fd12"]):
        rx = 374 + i * 58
        p.append(f'  <rect x="{rx}" y="278" width="50" height="36" rx="6" fill="{t["teal_soft"]}" stroke="{t["teal"]}" stroke-width="1.8"/>')
        p.append(f'  <text x="{rx + 25}" y="300" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["teal"]}">{rfd}</text>')

    # Divider
    p.append(f'  <line x1="576" y1="68" x2="576" y2="338" stroke="{t["hair"]}" stroke-width="1.2" stroke-dasharray="4 5"/>')

    # Right: io_uring Interlocking SQ & CQ Ring Buffers
    p.append(f'  <text x="752" y="64" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["blue"]}">IO_URING LOCK-FREE RINGS</text>')
    sq_x, sq_y = 682, 204
    cq_x, cq_y = 824, 204
    # Submission Queue Ring (left)
    p.append(f'  <circle cx="{sq_x}" cy="{sq_y}" r="82" fill="{t["blue_soft"]}" fill-opacity="0.5" stroke="{t["blue"]}" stroke-width="2"/>')
    p.append(f'  <path d="{arc_path(sq_x, sq_y, 70, -110, 40)}" fill="none" stroke="{t["blue"]}" stroke-width="12"/>')
    p.append(f'  <circle cx="{sq_x}" cy="{sq_y}" r="42" fill="{t["surface"]}" stroke="{t["blue"]}" stroke-width="2"/>')
    p.append(f'  <text x="{sq_x}" y="{sq_y - 2}" text-anchor="middle" class="mono" font-size="13" font-weight="700" fill="{t["blue"]}">SQ</text>')
    p.append(f'  <text x="{sq_x}" y="{sq_y + 14}" text-anchor="middle" class="mono" font-size="8.5" fill="{t["muted"]}">SUBMIT</text>')

    # Completion Queue Ring (right)
    p.append(f'  <circle cx="{cq_x}" cy="{cq_y}" r="82" fill="{t["teal_soft"]}" fill-opacity="0.5" stroke="{t["teal"]}" stroke-width="2"/>')
    p.append(f'  <path d="{arc_path(cq_x, cq_y, 70, 70, 220)}" fill="none" stroke="{t["teal"]}" stroke-width="12"/>')
    p.append(f'  <circle cx="{cq_x}" cy="{cq_y}" r="42" fill="{t["surface"]}" stroke="{t["teal"]}" stroke-width="2"/>')
    p.append(f'  <text x="{cq_x}" y="{cq_y - 2}" text-anchor="middle" class="mono" font-size="13" font-weight="700" fill="{t["teal"]}">CQ</text>')
    p.append(f'  <text x="{cq_x}" y="{cq_y + 14}" text-anchor="middle" class="mono" font-size="8.5" fill="{t["muted"]}">REAP</text>')

    # Head/Tail radial ticks on both rings
    for rcx, rcol in [(sq_x, t["blue"]), (cq_x, t["teal"])]:
        for k in range(8):
            ang = math.radians(k * 45)
            x0, y0 = rcx + 50 * math.cos(ang), 204 + 50 * math.sin(ang)
            x1, y1 = rcx + 60 * math.cos(ang), 204 + 60 * math.sin(ang)
            p.append(f'  <line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{rcol}" stroke-width="1.4" opacity="0.65"/>')

    # Shared memory bridge badge at intersection
    p.append(f'  <circle cx="753" cy="204" r="10" fill="{t["ochre"]}"/>')
    p.append(f'  <circle cx="753" cy="204" r="4" fill="{t["surface"]}"/>')
    p.append(f'  <text x="752" y="330" text-anchor="middle" class="mono" font-size="10" fill="{t["muted"]}">SHARED KERNEL/USER RING MEMORY</text>')

    p.append("</svg>\n")
    return "\n".join(p)


# =============================================================================
# CH 14: NETWORKING — TCP HANDSHAKE, PACKET HEADERS & CWND SAWTOOTH
# =============================================================================
def plate_ch14(t: dict) -> str:
    p = base_plate(
        "14", "Networking", "TCP HANDSHAKE · HEADERS", "CONGESTION WINDOW (AIMD)",
        "bg_kv", "grid_kv", "blue", "SYN -> SYN-ACK -> ACK · cwnd", t,
        "Chapter 14 geometric artwork: a TCP 3-way handshake ladder and an AIMD congestion window sawtooth waveform positioned above an encapsulated ETH/IP/TCP/DATA packet header strip."
    )
    # Top-left: TCP 3-way handshake
    p.append(f'  <text x="470" y="62" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["blue"]}">TCP 3-WAY HANDSHAKE</text>')
    p.append(f'  <line x1="392" y1="78" x2="392" y2="212" stroke="{t["blue"]}" stroke-width="2.4"/>')
    p.append(f'  <line x1="548" y1="78" x2="548" y2="212" stroke="{t["teal"]}" stroke-width="2.4"/>')
    p.append(f'  <text x="392" y="72" text-anchor="middle" class="mono" font-size="9.5" font-weight="700" fill="{t["blue"]}">CLI</text>')
    p.append(f'  <text x="548" y="72" text-anchor="middle" class="mono" font-size="9.5" font-weight="700" fill="{t["teal"]}">SRV</text>')

    p.append(f'  <line x1="396" y1="96" x2="542" y2="122" stroke="{t["blue"]}" stroke-width="2"/>')
    p.append(arrow_head(544, 122, 10, t["blue"], 6))
    p.append(f'  <text x="470" y="102" text-anchor="middle" class="mono" font-size="9.5" font-weight="700" fill="{t["blue"]}">SYN</text>')

    p.append(f'  <line x1="544" y1="136" x2="398" y2="162" stroke="{t["teal"]}" stroke-width="2"/>')
    p.append(arrow_head(396, 162, 170, t["teal"], 6))
    p.append(f'  <text x="470" y="144" text-anchor="middle" class="mono" font-size="9.5" font-weight="700" fill="{t["teal"]}">SYN-ACK</text>')

    p.append(f'  <line x1="396" y1="176" x2="542" y2="200" stroke="{t["ochre"]}" stroke-width="2"/>')
    p.append(arrow_head(544, 200, 10, t["ochre"], 6))
    p.append(f'  <text x="470" y="184" text-anchor="middle" class="mono" font-size="9.5" font-weight="700" fill="{t["ochre"]}">ACK</text>')

    # Top-right: AIMD Congestion Window (cwnd) Sawtooth
    p.append(f'  <text x="760" y="62" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["teal"]}">CWND AIMD SAWTOOTH</text>')
    p.append(f'  <line x1="612" y1="212" x2="910" y2="212" stroke="{t["hair"]}" stroke-width="1.6"/>')
    p.append(f'  <line x1="612" y1="78" x2="612" y2="212" stroke="{t["hair"]}" stroke-width="1.6"/>')
    # ssthresh ceiling
    p.append(f'  <line x1="612" y1="138" x2="910" y2="138" stroke="{t["ochre"]}" stroke-width="1.3" stroke-dasharray="4 4"/>')
    p.append(f'  <text x="908" y="132" text-anchor="end" class="mono" font-size="9" fill="{t["ochre"]}">ssthresh</text>')
    # Sawtooth waveform
    saw = "614,206 644,194 666,162 686,98 686,154 756,114 756,162 832,108 832,158 902,124"
    p.append(f'  <polyline points="{saw}" fill="none" stroke="{t["teal"]}" stroke-width="2.6" stroke-linejoin="round"/>')
    for lx, ly in [(686, 98), (756, 114), (832, 108)]:
        p.append(f'  <circle cx="{lx}" cy="{ly}" r="4.5" fill="{t["terra"]}"/>')

    # Bottom: Encapsulated Packet Header Strip
    p.append(f'  <text x="364" y="254" class="mono" font-size="10" font-weight="700" fill="{t["muted"]}">ENCAPSULATED WIRE FRAME</text>')
    pkt = [
        (364, 96, "ETH · 14B", t["indigo"], t["indigo_soft"]),
        (466, 108, "IP · 20B", t["blue"], t["blue_soft"]),
        (580, 112, "TCP · 20B", t["teal"], t["teal_soft"]),
        (698, 212, "APPLICATION PAYLOAD (MSS)", t["ochre"], t["ochre_soft"]),
    ]
    for px, pw, plbl, sc, sf in pkt:
        p.append(f'  <rect x="{px}" y="268" width="{pw}" height="58" rx="8" fill="{sf}" stroke="{sc}" stroke-width="2"/>')
        p.append(f'  <text x="{px + pw/2:.1f}" y="301" text-anchor="middle" class="mono" font-size="10.5" font-weight="700" fill="{sc}">{plbl}</text>')

    p.append("</svg>\n")
    return "\n".join(p)


# =============================================================================
# CH 15: DAEMONS & SUPERVISION — PID 1 TREE, CGROUPS & WATCHDOG HEARTBEATS
# =============================================================================
def plate_ch15(t: dict) -> str:
    p = base_plate(
        "15", "Daemons", "PID 1 SUPERVISION TREE", "CGROUPS · WATCHDOG · SIGTERM",
        "bg_rl", "grid_rl", "teal", "crash -> backoff -> respawn", t,
        "Chapter 15 geometric artwork: a PID 1 init supervisor managing three cgroup-isolated service cells with watchdog heartbeat pulses, graceful SIGTERM draining, and automatic respawn."
    )
    # PID 1 Supervisor Root
    p.append(f'  <rect x="546" y="64" width="184" height="52" rx="12" fill="{t["teal_soft"]}" stroke="{t["teal"]}" stroke-width="2.4"/>')
    p.append(f'  <text x="638" y="88" text-anchor="middle" class="mono" font-size="12" font-weight="700" fill="{t["teal"]}">PID 1 · SUPERVISOR</text>')
    p.append(f'  <text x="638" y="104" text-anchor="middle" class="mono" font-size="9" fill="{t["muted"]}">systemd / launchd</text>')

    # Orthogonal supervision tree connectors
    p.append(f'  <path d="M 638 116 L 638 152 M 446 152 L 830 152 M 446 152 L 446 184 M 638 152 L 638 184 M 830 152 L 830 184" fill="none" stroke="{t["teal"]}" stroke-width="2"/>')

    # Three cgroup-isolated service cells
    svcs = [
        (364, "SVC-A", "HEALTHY", t["teal"], t["teal_soft"]),
        (556, "SVC-B", "SIGTERM DRAIN", t["ochre"], t["ochre_soft"]),
        (748, "SVC-C", "RESPAWN (2s)", t["terra"], t["terra_soft"]),
    ]
    for sx, slbl, state, sc, sf in svcs:
        # Outer dashed cgroup cell
        p.append(f'  <rect x="{sx}" y="184" width="164" height="126" rx="12" fill="{t["surface"]}" stroke="{sc}" stroke-width="1.6" stroke-dasharray="5 4"/>')
        p.append(f'  <text x="{sx + 82}" y="204" text-anchor="middle" class="mono" font-size="9" font-weight="700" fill="{t["muted"]}">CGROUP v2 SLICE</text>')
        p.append(f'  <rect x="{sx + 16}" y="216" width="132" height="52" rx="8" fill="{sf}" stroke="{sc}" stroke-width="2"/>')
        p.append(f'  <text x="{sx + 82}" y="240" text-anchor="middle" class="mono" font-size="12" font-weight="700" fill="{sc}">{slbl}</text>')
        p.append(f'  <text x="{sx + 82}" y="256" text-anchor="middle" class="mono" font-size="9" font-weight="700" fill="{sc}">{state}</text>')

    # Heartbeat waveform inside SVC-A footer
    hb = "382,292 406,292 416,278 426,302 436,286 446,292 508,292"
    p.append(f'  <polyline points="{hb}" fill="none" stroke="{t["teal"]}" stroke-width="2" stroke-linejoin="round"/>')
    # Graceful drain bar inside SVC-B footer
    p.append(f'  <rect x="576" y="284" width="124" height="10" rx="5" fill="{t["hair"]}"/>')
    p.append(f'  <rect x="576" y="284" width="84" height="10" rx="5" fill="{t["ochre"]}"/>')
    # Respawn loop arc on SVC-C
    p.append(f'  <path d="M 862 288 A 24 14 0 1 1 800 288" fill="none" stroke="{t["terra"]}" stroke-width="2"/>')
    p.append(arrow_head(798, 288, -120, t["terra"], 5.5))

    p.append(f'  <text x="638" y="346" text-anchor="middle" class="mono" font-size="10" fill="{t["muted"]}">SOCKET ACTIVATION · WATCHDOG · RESOURCE QUOTAS</text>')
    p.append("</svg>\n")
    return "\n".join(p)


# =============================================================================
# CH 16: VIRTUALIZATION — VMX ROOT/NON-ROOT RINGS & CONTAINER CELLS
# =============================================================================
def plate_ch16(t: dict) -> str:
    p = base_plate(
        "16", "Virtualization", "VMX ROOT / NON-ROOT", "NAMESPACES · CGROUP CELLS",
        "bg_pay", "grid_pay", "indigo", "VM-Exit -> Hypervisor -> VM-Entry", t,
        "Chapter 16 geometric artwork: concentric VMX root hypervisor and guest VM rings on the left contrasted with three namespace-isolated container cells sharing a host kernel on the right."
    )
    # Left-center: Hypervisor VMX Root / Non-Root Rings
    p.append(f'  <text x="488" y="64" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["indigo"]}">HARDWARE VMs (VMX)</text>')
    p.append(f'  <rect x="358" y="78" width="260" height="252" rx="16" fill="{t["indigo_soft"]}" stroke="{t["indigo"]}" stroke-width="2.2"/>')
    p.append(f'  <text x="488" y="314" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["indigo"]}">VMX ROOT · HYPERVISOR</text>')

    # Two Guest VM rings inside
    for idx, (vx, lbl, sc, sf) in enumerate([(428, "VM 1", t["blue"], t["blue_soft"]), (548, "VM 2", t["teal"], t["teal_soft"])]):
        p.append(f'  <circle cx="{vx}" cy="176" r="52" fill="{t["surface"]}" stroke="{sc}" stroke-width="2.2"/>')
        p.append(f'  <circle cx="{vx}" cy="176" r="28" fill="{sf}" stroke="{sc}" stroke-width="1.6"/>')
        p.append(f'  <text x="{vx}" y="180" text-anchor="middle" class="mono" font-size="10.5" font-weight="700" fill="{sc}">{lbl}</text>')
        p.append(f'  <text x="{vx}" y="216" text-anchor="middle" class="mono" font-size="8.5" fill="{t["muted"]}">GUEST OS</text>')
    # VM-Exit / VM-Entry arrow down to hypervisor bar
    p.append(f'  <line x1="488" y1="234" x2="488" y2="286" stroke="{t["terra"]}" stroke-width="2.2"/>')
    p.append(arrow_head(488, 288, 90, t["terra"], 5.5))
    p.append(arrow_head(488, 232, -90, t["terra"], 5.5))
    p.append(f'  <text x="488" y="264" text-anchor="middle" class="mono" font-size="9" font-weight="700" fill="{t["terra"]}">VM-EXIT</text>')

    # Right: Shared Host Kernel + 3 Container Isolation Cells
    p.append(f'  <text x="784" y="64" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["teal"]}">CONTAINERS (NAMESPACES)</text>')
    ctrs = [
        (654, "CTR 1", t["teal"], t["teal_soft"]),
        (744, "CTR 2", t["ochre"], t["ochre_soft"]),
        (834, "CTR 3", t["blue"], t["blue_soft"]),
    ]
    for cx0, clbl, sc, sf in ctrs:
        p.append(f'  <rect x="{cx0}" y="86" width="80" height="172" rx="10" fill="{sf}" stroke="{sc}" stroke-width="2"/>')
        p.append(f'  <text x="{cx0 + 40}" y="114" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="{sc}">{clbl}</text>')
        for j, ns in enumerate(["PID", "NET", "MNT"]):
            ny = 136 + j * 36
            p.append(f'  <rect x="{cx0 + 12}" y="{ny}" width="56" height="24" rx="5" fill="{t["surface"]}" stroke="{sc}" stroke-width="1.3"/>')
            p.append(f'  <text x="{cx0 + 40}" y="{ny + 15}" text-anchor="middle" class="mono" font-size="9" font-weight="700" fill="{sc}">{ns}</text>')

    # Shared Host Kernel Base
    p.append(f'  <rect x="654" y="274" width="260" height="56" rx="10" fill="{t["terra_soft"]}" stroke="{t["terra"]}" stroke-width="2.2"/>')
    p.append(f'  <text x="784" y="306" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="{t["terra"]}">SHARED HOST LINUX KERNEL</text>')

    p.append("</svg>\n")
    return "\n".join(p)


# =============================================================================
# CH 17: MULTIPROCESSORS — NUMA DUAL-SOCKET & MESI CACHE COHERENCE
# =============================================================================
def plate_ch17(t: dict) -> str:
    p = base_plate(
        "17", "Multiprocessors", "NUMA DUAL-SOCKET", "MESI CACHE COHERENCE",
        "bg_kv", "grid_kv", "ochre", "Local RAM (65ns) < Remote (130ns)", t,
        "Chapter 17 geometric artwork: a dual-socket NUMA interconnect topology above a four-state MESI cache coherence state diagram."
    )
    # Top: Dual-Socket NUMA topology
    p.append(f'  <text x="636" y="60" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["blue"]}">DUAL-SOCKET NUMA INTERCONNECT</text>')
    for idx, (nx, lbl, sc, sf) in enumerate([
        (364, "SOCKET 0", t["blue"], t["blue_soft"]),
        (704, "SOCKET 1", t["teal"], t["teal_soft"]),
    ]):
        p.append(f'  <rect x="{nx}" y="72" width="206" height="122" rx="12" fill="{sf}" stroke="{sc}" stroke-width="2"/>')
        p.append(f'  <text x="{nx + 103}" y="94" text-anchor="middle" class="mono" font-size="10.5" font-weight="700" fill="{sc}">{lbl}</text>')
        for c in range(2):
            cx0 = nx + 16 + c * 92
            p.append(f'  <rect x="{cx0}" y="106" width="82" height="34" rx="6" fill="{t["surface"]}" stroke="{sc}" stroke-width="1.6"/>')
            p.append(f'  <text x="{cx0 + 41}" y="127" text-anchor="middle" class="mono" font-size="9.5" font-weight="700" fill="{sc}">CORE {idx*2 + c}</text>')
        p.append(f'  <rect x="{nx + 16}" y="150" width="174" height="32" rx="6" fill="{sc}" opacity="0.88"/>')
        p.append(f'  <text x="{nx + 103}" y="170" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["surface"]}">LOCAL DRAM {idx}</text>')

    # High-bandwidth UPI/IF interconnect bridge
    p.append(f'  <line x1="570" y1="124" x2="704" y2="124" stroke="{t["ochre"]}" stroke-width="3.2"/>')
    p.append(f'  <line x1="570" y1="142" x2="704" y2="142" stroke="{t["ochre"]}" stroke-width="3.2"/>')
    p.append(f'  <rect x="604" y="114" width="66" height="38" rx="6" fill="{t["surface"]}" stroke="{t["ochre"]}" stroke-width="1.8"/>')
    p.append(f'  <text x="637" y="137" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["ochre"]}">UPI</text>')

    # Bottom: MESI Cache Coherence States
    p.append(f'  <text x="636" y="232" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["ochre"]}">MESI CACHE COHERENCE PROTOCOL</text>')
    mesi = [
        (414, "M", "MODIFIED", t["terra"], t["terra_soft"]),
        (562, "E", "EXCLUSIVE", t["ochre"], t["ochre_soft"]),
        (710, "S", "SHARED", t["teal"], t["teal_soft"]),
        (858, "I", "INVALID", t["muted"], t["surface"]),
    ]
    # Connecting coherence bus rails
    p.append(f'  <line x1="414" y1="292" x2="858" y2="292" stroke="{t["hair"]}" stroke-width="2.2"/>')
    p.append(f'  <path d="M 414 260 Q 636 226 858 260" fill="none" stroke="{t["terra"]}" stroke-width="1.6" stroke-dasharray="4 4"/>')
    for mx, ch, name, sc, sf in mesi:
        p.append(f'  <circle cx="{mx}" cy="292" r="32" fill="{sf}" stroke="{sc}" stroke-width="2.4"/>')
        p.append(f'  <text x="{mx}" y="290" text-anchor="middle" class="mono" font-size="18" font-weight="700" fill="{sc}">{ch}</text>')
        p.append(f'  <text x="{mx}" y="308" text-anchor="middle" class="mono" font-size="8" font-weight="700" fill="{sc}">{name}</text>')
    p.append(f'  <text x="636" y="352" text-anchor="middle" class="mono" font-size="9.5" fill="{t["muted"]}">BusRd · BusRdX · FlushOpt · Invalidate</text>')

    p.append("</svg>\n")
    return "\n".join(p)


# =============================================================================
# CH 18: PERFORMANCE — FLAME GRAPH, EBPF PROBES & P50/P99 LATENCY HISTOGRAM
# =============================================================================
def plate_ch18(t: dict) -> str:
    p = base_plate(
        "18", "Performance", "FLAME GRAPH · EBPF PROBES", "P50 / P99 LATENCY HISTOGRAM",
        "bg_pay", "grid_pay", "terra", "Measure -> Profile -> Verify", t,
        "Chapter 18 geometric artwork: a stacked CPU flame graph instrumented by eBPF kprobe needles on the left beside a right-skewed latency histogram marking p50 and p99."
    )
    # Left-center: Stacked Flame Graph
    p.append(f'  <text x="504" y="64" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["terra"]}">CPU FLAME GRAPH + eBPF</text>')
    frames = [
        # (x, y, w, label, col, bg)
        (360, 294, 288, "main() · 100%", t["blue"], t["blue_soft"]),
        (360, 256, 174, "handle_req() · 60%", t["teal"], t["teal_soft"]),
        (540, 256, 108, "flush_io()", t["indigo"], t["indigo_soft"]),
        (360, 218, 96, "parse()", t["ochre"], t["ochre_soft"]),
        (462, 218, 72, "hash()", t["terra"], t["terra_soft"]),
        (540, 218, 92, "vfs_write()", t["terra"], t["terra_soft"]),
        (540, 180, 68, "nvme_sq", t["ochre"], t["ochre_soft"]),
    ]
    for fx, fy, fw, flbl, sc, sf in frames:
        p.append(f'  <rect x="{fx}" y="{fy}" width="{fw}" height="32" rx="5" fill="{sf}" stroke="{sc}" stroke-width="1.8"/>')
        p.append(f'  <text x="{fx + fw/2:.1f}" y="{fy + 20}" text-anchor="middle" class="mono" font-size="9.5" font-weight="700" fill="{sc}">{flbl}</text>')

    # eBPF kprobe needles tapping hot frames
    for px, plbl in [(498, "kprobe"), (574, "tracepoint")]:
        p.append(f'  <line x1="{px}" y1="108" x2="{px}" y2="174" stroke="{t["terra"]}" stroke-width="2" stroke-dasharray="4 3"/>')
        p.append(arrow_head(px, 176, 90, t["terra"], 6))
        p.append(f'  <rect x="{px - 36}" y="82" width="72" height="26" rx="13" fill="{t["surface"]}" stroke="{t["terra"]}" stroke-width="1.8"/>')
        p.append(f'  <text x="{px}" y="99" text-anchor="middle" class="mono" font-size="9" font-weight="700" fill="{t["terra"]}">{plbl}</text>')

    # Right: Latency Histogram (p50 / p99)
    p.append(f'  <text x="794" y="64" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["teal"]}">LATENCY DISTRIBUTION</text>')
    p.append(f'  <line x1="680" y1="326" x2="914" y2="326" stroke="{t["hair"]}" stroke-width="1.8"/>')
    heights = [28, 74, 152, 186, 134, 88, 56, 36, 22, 16, 10]
    for i, bh in enumerate(heights):
        bx = 686 + i * 20
        col = t["terra"] if i >= 8 else (t["teal"] if i <= 4 else t["blue"])
        p.append(f'  <rect x="{bx}" y="{326 - bh}" width="15" height="{bh}" rx="3" fill="{col}" opacity="0.86"/>')

    # p50 & p99 vertical markers
    p.append(f'  <line x1="754" y1="98" x2="754" y2="334" stroke="{t["teal"]}" stroke-width="2" stroke-dasharray="4 3"/>')
    p.append(f'  <text x="754" y="90" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["teal"]}">p50</text>')
    p.append(f'  <line x1="854" y1="98" x2="854" y2="334" stroke="{t["terra"]}" stroke-width="2" stroke-dasharray="4 3"/>')
    p.append(f'  <text x="854" y="90" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["terra"]}">p99</text>')
    p.append(f'  <text x="794" y="352" text-anchor="middle" class="mono" font-size="9.5" fill="{t["muted"]}">TAIL LATENCY (μs)</text>')

    p.append("</svg>\n")
    return "\n".join(p)


# =============================================================================
# CH 19: INTERVIEW PROBLEMS — BLUEPRINT GRID OF CLASSIC OS PRIMITIVES
# =============================================================================
def plate_ch19(t: dict) -> str:
    p = base_plate(
        "19", "Interview Problems", "CLASSIC OS PRIMITIVES", "CONCURRENCY · MEMORY · LOCKS",
        "bg_kv", "grid_kv", "blue", "First Principles -> Reference Code", t,
        "Chapter 19 geometric artwork: a 6-tile Swiss architectural blueprint grid depicting Bounded Queue, RW-Lock, Thread Pool, LRU Cache, Slab Allocator, and Event Loop."
    )
    tiles = [
        (360, 72, "BOUNDED QUEUE", t["blue"], t["blue_soft"], "ring"),
        (548, 72, "RW-LOCK", t["teal"], t["teal_soft"], "rwlock"),
        (736, 72, "THREAD POOL", t["indigo"], t["indigo_soft"], "pool"),
        (360, 212, "LRU CACHE", t["ochre"], t["ochre_soft"], "lru"),
        (548, 212, "SLAB ALLOC", t["terra"], t["terra_soft"], "slab"),
        (736, 212, "EVENT LOOP", t["teal"], t["teal_soft"], "loop"),
    ]
    for tx, ty, lbl, sc, sf, kind in tiles:
        p.append(f'  <rect x="{tx}" y="{ty}" width="174" height="122" rx="12" fill="{t["surface"]}" stroke="{sc}" stroke-width="2"/>')
        p.append(f'  <text x="{tx + 87}" y="{ty + 108}" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{sc}">{lbl}</text>')
        cx, cy = tx + 87, ty + 50
        if kind == "ring":
            p.append(f'  <circle cx="{cx}" cy="{cy}" r="28" fill="{sf}" stroke="{sc}" stroke-width="2"/>')
            p.append(f'  <path d="{arc_path(cx, cy, 22, -90, 110)}" fill="none" stroke="{sc}" stroke-width="7"/>')
            p.append(f'  <circle cx="{cx}" cy="{cy}" r="11" fill="{t["surface"]}"/>')
        elif kind == "rwlock":
            p.append(f'  <line x1="{cx - 46}" y1="{cy - 12}" x2="{cx + 46}" y2="{cy - 12}" stroke="{sc}" stroke-width="2.2"/>')
            p.append(f'  <line x1="{cx - 46}" y1="{cy + 12}" x2="{cx + 46}" y2="{cy + 12}" stroke="{sc}" stroke-width="2.2"/>')
            p.append(f'  <rect x="{cx - 12}" y="{cy - 24}" width="24" height="48" rx="6" fill="{sf}" stroke="{sc}" stroke-width="2"/>')
        elif kind == "pool":
            p.append(f'  <rect x="{cx - 52}" y="{cy - 12}" width="38" height="24" rx="4" fill="{sf}" stroke="{sc}" stroke-width="1.8"/>')
            for dy in (-20, 0, 20):
                p.append(f'  <line x1="{cx - 14}" y1="{cy}" x2="{cx + 22}" y2="{cy + dy}" stroke="{sc}" stroke-width="1.5"/>')
                p.append(f'  <circle cx="{cx + 32}" cy="{cy + dy}" r="9" fill="{sf}" stroke="{sc}" stroke-width="1.8"/>')
        elif kind == "lru":
            for k in range(4):
                rx = cx - 54 + k * 28
                p.append(f'  <rect x="{rx}" y="{cy - 14}" width="22" height="28" rx="4" fill="{sf}" stroke="{sc}" stroke-width="1.8"/>')
                if k < 3:
                    p.append(f'  <line x1="{rx + 22}" y1="{cy}" x2="{rx + 28}" y2="{cy}" stroke="{sc}" stroke-width="1.8"/>')
        elif kind == "slab":
            for r in range(2):
                for c in range(4):
                    rx = cx - 50 + c * 26
                    ry = cy - 22 + r * 24
                    fill = sc if (r + c) % 2 == 0 else sf
                    p.append(f'  <rect x="{rx}" y="{ry}" width="20" height="18" rx="3" fill="{fill}" stroke="{sc}" stroke-width="1.4" opacity="0.88"/>')
        elif kind == "loop":
            p.append(f'  <path d="{arc_path(cx, cy, 24, -40, 260)}" fill="none" stroke="{sc}" stroke-width="3.2"/>')
            p.append(arrow_head(cx + 18, cy - 16, 45, sc, 6.5))
            p.append(f'  <circle cx="{cx}" cy="{cy}" r="7" fill="{sc}"/>')

    p.append("</svg>\n")
    return "\n".join(p)


PLATES = {
    "ch01-plate.svg": plate_ch01,
    "ch02-plate.svg": plate_ch02,
    "ch03-plate.svg": plate_ch03,
    "ch04-plate.svg": plate_ch04,
    "ch05-plate.svg": plate_ch05,
    "ch06-plate.svg": plate_ch06,
    "ch07-plate.svg": plate_ch07,
    "ch08-plate.svg": plate_ch08,
    "ch09-plate.svg": plate_ch09,
    "ch10-plate.svg": plate_ch10,
    "ch11-plate.svg": plate_ch11,
    "ch12-plate.svg": plate_ch12,
    "ch13-plate.svg": plate_ch13,
    "ch14-plate.svg": plate_ch14,
    "ch15-plate.svg": plate_ch15,
    "ch16-plate.svg": plate_ch16,
    "ch17-plate.svg": plate_ch17,
    "ch18-plate.svg": plate_ch18,
    "ch19-plate.svg": plate_ch19,
}


def main():
    (OUT / "dark").mkdir(parents=True, exist_ok=True)
    for filename, fn in sorted(PLATES.items()):
        (OUT / filename).write_text(fn(LIGHT), encoding="utf-8")
        (OUT / "dark" / filename).write_text(fn(DARK), encoding="utf-8")
    print(f"generated {len(PLATES)} plates ({len(PLATES) * 2} light+dark SVGs)")


if __name__ == "__main__":
    main()
