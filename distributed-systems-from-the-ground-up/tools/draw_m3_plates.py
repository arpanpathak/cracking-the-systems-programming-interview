#!/usr/bin/env python3
"""Generate crisp, zero-blur abstract geometric SVG chapter plates (960x400).

Each plate is a thoughtful Swiss-Modernist / Bauhaus abstract composition that
visually encodes the core mathematical and architectural invariants of the
chapter's system. Every plate is written in paired Light (`src/art/<name>.svg`)
and Dark (`src/art/dark/<name>.svg`) variants with zero Gaussian blur filters.
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

# Perceptually calibrated (APCA / OKLCH) dark palette: zero pure-white halation,
# zero neon chroma vibration, calm off-white ink (#E4E9F2) & desaturated pastel accents.
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
    # Crisp architectural hairline grid (40px pitch)
    for gx in range(40, W, 40):
        parts.append(f'  <line x1="{gx}" y1="1" x2="{gx}" y2="{H - 1}" stroke="{grid_col}" stroke-width="0.75"/>')
    for gy in range(40, H, 40):
        parts.append(f'  <line x1="1" y1="{gy}" x2="{W - 1}" y2="{gy}" stroke="{grid_col}" stroke-width="0.75"/>')
    return parts


def swiss_lockup(num: str, title: str, sub1: str, sub2: str, accent: str, t: dict) -> list[str]:
    """Minimalist Swiss editorial chapter lockup (crisp, airy, zero heavy chrome)."""
    return [
        f'  <rect x="44" y="42" width="42" height="4" rx="2" fill="{accent}"/>',
        f'  <text x="44" y="88" class="mono" font-size="38" font-weight="700" fill="{accent}" letter-spacing="-0.03em">{escape(num)}</text>',
        f'  <text x="44" y="132" class="sans" font-size="25" font-weight="750" fill="{t["ink"]}" letter-spacing="-0.015em">{escape(title)}</text>',
        f'  <text x="44" y="158" class="mono" font-size="11" font-weight="600" fill="{t["muted"]}" letter-spacing="0.06em">{escape(sub1)}</text>',
        f'  <text x="44" y="176" class="mono" font-size="11" font-weight="600" fill="{t["muted"]}" letter-spacing="0.06em">{escape(sub2)}</text>',
    ]


def arc_path(cx: float, cy: float, r: float, a1_deg: float, a2_deg: float) -> str:
    a1, a2 = math.radians(a1_deg), math.radians(a2_deg)
    x1, y1 = cx + r * math.cos(a1), cy + r * math.sin(a1)
    x2, y2 = cx + r * math.cos(a2), cy + r * math.sin(a2)
    large = 1 if (a2_deg - a1_deg) % 360 > 180 else 0
    return f"M {x1:.2f} {y1:.2f} A {r:.2f} {r:.2f} 0 {large} 1 {x2:.2f} {y2:.2f}"


# =============================================================================
# CH 01: CONSISTENT HASH RING & QUORUM INTERSECTION (ABSTRACT GEOMETRIC)
# =============================================================================

def plate_ch01(t: dict) -> str:
    aria = (
        "Chapter 1 abstract geometric artwork: a concentric 64-bit consistent hash ring "
        "partitioned into color-coded shard arcs linked by crisp tangent geometry to three "
        "overlapping quorum intersection disks symbolizing Raft majority agreement."
    )
    p = header_svg(aria, t["bg_kv"], t["grid_kv"], t)
    p += swiss_lockup("01", "Key-Value Store", "CONSISTENT HASH RING", "LINEARIZABILITY · QUORUM", t["blue"], t)

    # Geometric architectural caption line at bottom-left
    p += [
        f'  <line x1="44" y1="336" x2="292" y2="336" stroke="{t["hair"]}" stroke-width="1"/>',
        f'  <text x="44" y="358" class="mono" font-size="11" fill="{t["muted"]}">|Q1 ∩ Q2| >= 1   ·   2f + 1 = 3 AZ</text>',
    ]

    # --- Sculptural Consistent Hash Ring (center: 472, 212) ---
    cx, cy = 472, 212
    # Subtle outer coordinate compass
    p.append(f'  <circle cx="{cx}" cy="{cy}" r="154" fill="none" stroke="{t["hair"]}" stroke-width="1" stroke-dasharray="3 5"/>')
    # Layered translucent shard arcs (partition segments)
    p.append(f'  <path d="{arc_path(cx, cy, 128, -95, 20)}" fill="none" stroke="{t["blue"]}" stroke-width="18" stroke-linecap="butt" opacity="0.88"/>')
    p.append(f'  <path d="{arc_path(cx, cy, 128, 28, 138)}" fill="none" stroke="{t["teal"]}" stroke-width="18" stroke-linecap="butt" opacity="0.85"/>')
    p.append(f'  <path d="{arc_path(cx, cy, 128, 146, 205)}" fill="none" stroke="{t["terra"]}" stroke-width="18" stroke-linecap="butt" opacity="0.88"/>')
    p.append(f'  <path d="{arc_path(cx, cy, 128, 213, 258)}" fill="none" stroke="{t["ochre"]}" stroke-width="18" stroke-linecap="butt" opacity="0.88"/>')

    # Inner virtual-node ring + radial ticks
    p.append(f'  <circle cx="{cx}" cy="{cy}" r="94" fill="none" stroke="{t["ink"]}" stroke-width="1.2" opacity="0.28"/>')
    p.append(f'  <circle cx="{cx}" cy="{cy}" r="58" fill="{t["blue_soft"]}" opacity="0.72"/>')
    p.append(f'  <circle cx="{cx}" cy="{cy}" r="22" fill="{t["surface"]}" stroke="{t["blue"]}" stroke-width="2"/>')
    p.append(f'  <circle cx="{cx}" cy="{cy}" r="6" fill="{t["terra"]}"/>')

    # 24 virtual-node geometric tick rays around the 94-110 annulus
    for k in range(24):
        deg = k * 15
        ang = math.radians(deg)
        r0 = 94 if k % 3 else 84
        r1 = 112
        x0, y0 = cx + r0 * math.cos(ang), cy + r0 * math.sin(ang)
        x1, y1 = cx + r1 * math.cos(ang), cy + r1 * math.sin(ang)
        col = [t["blue"], t["teal"], t["terra"], t["ochre"]][k % 4]
        sw = 2.0 if k % 3 == 0 else 1.0
        p.append(f'  <line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{col}" stroke-width="{sw}" opacity="0.85"/>')

    # Crisp key point mapped onto ring -> tangent bridge to Quorum Venn
    p.append(f'  <circle cx="{cx + 128*math.cos(math.radians(-38)):.1f}" cy="{cy + 128*math.sin(math.radians(-38)):.1f}" r="8" fill="{t["surface"]}" stroke="{t["terra"]}" stroke-width="3"/>')

    # --- Architectural Bridge Lines ---
    p.append(f'  <line x1="604" y1="168" x2="718" y2="168" stroke="{t["ink"]}" stroke-width="1.2" opacity="0.35"/>')
    p.append(f'  <line x1="600" y1="212" x2="682" y2="212" stroke="{t["blue"]}" stroke-width="1.6" stroke-dasharray="4 4"/>')

    # --- Sculptural 3-Node Quorum Venn Intersection (center: 786, 206) ---
    qx, qy = 786, 206
    qr = 74
    # Three interlocking circles positioned on an equilateral triangle
    v_pts = [
        (qx, qy - 42, t["ochre"], t["ochre_soft"]),
        (qx - 40, qy + 28, t["blue"], t["blue_soft"]),
        (qx + 40, qy + 28, t["teal"], t["teal_soft"]),
    ]
    for vx, vy, stroke_c, fill_c in v_pts:
        p.append(f'  <circle cx="{vx}" cy="{vy}" r="{qr}" fill="{fill_c}" fill-opacity="0.55" stroke="{stroke_c}" stroke-width="2.0"/>')

    # Crisp geometric equilateral triangle connecting the 3 AZ centers (majority quorum proof)
    p.append(f'  <polygon points="{qx},{qy-42} {qx-40},{qy+28} {qx+40},{qy+28}" fill="none" stroke="{t["ink"]}" stroke-width="1.3" opacity="0.55"/>')
    # Luminous solid center dot at the triple intersection
    p.append(f'  <circle cx="{qx}" cy="{qy + 4}" r="11" fill="{t["terra"]}"/>')
    p.append(f'  <circle cx="{qx}" cy="{qy + 4}" r="4.5" fill="{t["surface"]}"/>')
    for vx, vy, stroke_c, _ in v_pts:
        p.append(f'  <circle cx="{vx}" cy="{vy}" r="5.5" fill="{stroke_c}"/>')

    # Minimal geometric coordinate annotations
    p.append(f'  <text x="{cx}" y="382" text-anchor="middle" class="mono" font-size="10.5" fill="{t["muted"]}">RING [0 .. 2^64 - 1]</text>')
    p.append(f'  <text x="{qx}" y="382" text-anchor="middle" class="mono" font-size="10.5" fill="{t["muted"]}">QUORUM INTERSECTION</text>')

    p.append("</svg>\n")
    return "\n".join(p)


# =============================================================================
# CH 07: RATE LIMITER — TURBULENCE -> GCRA APERTURE -> LAMINAR CADENCE
# =============================================================================

def plate_ch07(t: dict) -> str:
    aria = (
        "Chapter 7 abstract geometric artwork: a chaotic burst of amber and terracotta "
        "arrival vectors passes through a central geometric GCRA clock-wheel aperture, "
        "deflecting excess surge trajectories downward while emitting evenly spaced cerulean "
        "and teal laminar pulses."
    )
    p = header_svg(aria, t["bg_rl"], t["grid_rl"], t)
    p += swiss_lockup("07", "Rate Limiter", "GCRA · QUOTA LEASING", "ADAPTIVE LOAD SHEDDING", t["teal"], t)

    # Bottom-left invariant notation
    p += [
        f'  <line x1="44" y1="336" x2="278" y2="336" stroke="{t["hair"]}" stroke-width="1"/>',
        f'  <text x="44" y="358" class="mono" font-size="11" fill="{t["muted"]}">ALLOW  t_now >= TAT - T</text>',
    ]

    # --- Left-Center Turbulent Arrival Burst (x: 336..500) ---
    ap_x, ap_y = 548, 200
    burst_rays = [
        (344, 96, t["terra"], 2.2), (358, 128, t["ochre"], 1.8), (336, 158, t["terra"], 2.6),
        (362, 182, t["ochre"], 2.0), (340, 204, t["terra"], 3.0), (366, 226, t["ochre"], 2.2),
        (346, 254, t["terra"], 2.4), (372, 286, t["ochre"], 1.8), (352, 312, t["terra"], 2.0),
    ]
    for bx, by, col, sw in burst_rays:
        p.append(f'  <path d="M {bx} {by} Q {(bx + ap_x)/2:.1f} {by + (ap_y - by)*0.22:.1f} {ap_x - 66} {ap_y + (by - ap_y)*0.28:.1f}" fill="none" stroke="{col}" stroke-width="{sw}" opacity="0.82"/>')
        p.append(f'  <circle cx="{bx}" cy="{by}" r="{sw * 2.2:.1f}" fill="{col}" opacity="0.88"/>')

    # Overlapping burst interference circles (stochastic arrival cluster)
    for ox, oy, orad, col in [
        (378, 166, 26, t["ochre_soft"]),
        (404, 212, 34, t["terra_soft"]),
        (372, 238, 22, t["ochre_soft"]),
    ]:
        p.append(f'  <circle cx="{ox}" cy="{oy}" r="{orad}" fill="{col}" fill-opacity="0.72" stroke="{t["terra"]}" stroke-width="1" stroke-opacity="0.45"/>')

    # --- Deflected Overflow Surge Geometry (429 Shed Facets below Aperture) ---
    p.append(f'  <polygon points="{ap_x - 28},{ap_y + 62} {ap_x + 28},{ap_y + 62} {ap_x - 16},{ap_y + 152} {ap_x - 74},{ap_y + 152}" fill="{t["terra_soft"]}" stroke="{t["terra"]}" stroke-width="1.5"/>')
    for k in range(4):
        sx = ap_x - 22 + k * 14
        p.append(f'  <line x1="{sx}" y1="{ap_y + 68}" x2="{sx - 34}" y2="{ap_y + 144}" stroke="{t["terra"]}" stroke-width="1.8" stroke-dasharray="4 4"/>')
    p.append(f'  <text x="{ap_x - 42}" y="378" text-anchor="middle" class="mono" font-size="10.5" font-weight="700" fill="{t["terra"]}">SHED (429)</text>')

    # --- Central Bauhaus GCRA Clock-Wheel Aperture (center: 540, 200) ---
    p.append(f'  <circle cx="{ap_x}" cy="{ap_y}" r="88" fill="{t["surface"]}" stroke="{t["teal"]}" stroke-width="2.2"/>')
    p.append(f'  <circle cx="{ap_x}" cy="{ap_y}" r="68" fill="{t["teal_soft"]}" opacity="0.85"/>')
    # Burst tolerance arc T (bold teal sector) and emission interval tau (blue sector)
    p.append(f'  <path d="{arc_path(ap_x, ap_y, 78, -110, 20)}" fill="none" stroke="{t["teal"]}" stroke-width="10"/>')
    p.append(f'  <path d="{arc_path(ap_x, ap_y, 78, 28, 86)}" fill="none" stroke="{t["blue"]}" stroke-width="10"/>')
    p.append(f'  <path d="{arc_path(ap_x, ap_y, 78, 96, 175)}" fill="none" stroke="{t["terra"]}" stroke-width="10" opacity="0.75"/>')
    # Clock ticks & precision crosshair
    for k in range(12):
        ang = math.radians(k * 30)
        x0, y0 = ap_x + 54 * math.cos(ang), ap_y + 54 * math.sin(ang)
        x1, y1 = ap_x + 64 * math.cos(ang), ap_y + 64 * math.sin(ang)
        p.append(f'  <line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{t["ink"]}" stroke-width="1.4" opacity="0.5"/>')
    # TAT clock hand
    p.append(f'  <line x1="{ap_x}" y1="{ap_y}" x2="{ap_x + 42}" y2="{ap_y - 32}" stroke="{t["ink"]}" stroke-width="2.6" stroke-linecap="round"/>')
    p.append(f'  <circle cx="{ap_x}" cy="{ap_y}" r="9" fill="{t["teal"]}"/>')
    p.append(f'  <circle cx="{ap_x}" cy="{ap_y}" r="3.5" fill="{t["surface"]}"/>')
    p.append(f'  <text x="{ap_x}" y="94" text-anchor="middle" class="mono" font-size="10.5" font-weight="700" fill="{t["teal"]}">GCRA APERTURE (TAT)</text>')

    # --- Right Third: Pure Laminar Harmonic Output (x: 650..916) ---
    p.append(f'  <line x1="{ap_x + 88}" y1="{ap_y}" x2="922" y2="{ap_y}" stroke="{t["teal"]}" stroke-width="1.5" opacity="0.45"/>')
    # Smooth rhythmic sine wave
    wave_pts = []
    for i in range(0, 270, 6):
        wx = 648 + i
        wy = ap_y - 44 * math.sin(i * math.pi / 44.0)
        wave_pts.append(f"{wx:.1f},{wy:.1f}")
    p.append(f'  <polyline points="{" ".join(wave_pts)}" fill="none" stroke="{t["blue"]}" stroke-width="1.8" opacity="0.55"/>')

    # Perfectly equidistant laminar pulses (exact tau spacing)
    for k in range(6):
        px = 668 + k * 44
        p.append(f'  <rect x="{px - 8}" y="{ap_y - 54}" width="16" height="108" rx="8" fill="{t["teal"] if k % 2 == 0 else t["blue"]}" opacity="0.88"/>')
        p.append(f'  <circle cx="{px}" cy="{ap_y - 68}" r="4" fill="{t["teal"]}"/>')
        p.append(f'  <line x1="{px}" y1="{ap_y + 62}" x2="{px}" y2="{ap_y + 76}" stroke="{t["muted"]}" stroke-width="1.1"/>')
    p.append(f'  <text x="778" y="302" text-anchor="middle" class="mono" font-size="10.5" fill="{t["teal"]}">LAMINAR CADENCE (Δt = τ)</text>')

    p.append("</svg>\n")
    return "\n".join(p)


# =============================================================================
# CH 19: PAYMENT SYSTEM — ZERO-SUM EQUILIBRIUM & ISOLATED CRYPTOGRAPHIC VAULT
# =============================================================================

def plate_ch19(t: dict) -> str:
    aria = (
        "Chapter 19 abstract geometric artwork: a Mondrian-inspired zero-sum double-entry "
        "equilibrium composition where emerald credit blocks above a horizontal fulcrum "
        "exactly match terracotta debit blocks below, paired with concentric octagonal "
        "PCI-DSS vault rings and three converging T+0 to T+2 reconciliation ribbons."
    )
    p = header_svg(aria, t["bg_pay"], t["grid_pay"], t)
    p += swiss_lockup("19", "Payment System", "ZERO-SUM LEDGER", "ATOMIC PHASES · PCI CDE", t["terra"], t)

    # Bottom-left conservation law
    p += [
        f'  <line x1="44" y1="336" x2="294" y2="336" stroke="{t["hair"]}" stroke-width="1"/>',
        f'  <text x="44" y="358" class="mono" font-size="11" fill="{t["muted"]}">Σ(delta_minor) == 0   ·   T+0 → T+2</text>',
    ]

    # --- Center-Left: Zero-Sum Double-Entry Geometric Equilibrium (x: 344..624, fulcrum y=214) ---
    fy = 214
    # Crisp architectural fulcrum axis
    p.append(f'  <line x1="330" y1="{fy}" x2="646" y2="{fy}" stroke="{t["ink"]}" stroke-width="2.2"/>')
    # Pivot diamond fulcrum
    p.append(f'  <polygon points="488,{fy - 9} 497,{fy} 488,{fy + 9} 479,{fy}" fill="{t["ochre"]}" stroke="{t["ink"]}" stroke-width="1.4"/>')

    # Positive Credit Blocks ABOVE fulcrum (total area = 110*80 + 36*80 = 146*80)
    p.append(f'  <rect x="356" y="{fy - 118}" width="112" height="110" rx="6" fill="{t["teal"]}" opacity="0.86"/>')
    p.append(f'  <rect x="372" y="{fy - 102}" width="80" height="78" rx="3" fill="none" stroke="{t["surface"]}" stroke-width="1.3" opacity="0.55"/>')
    p.append(f'  <text x="412" y="{fy - 58}" text-anchor="middle" class="mono" font-size="12" font-weight="700" fill="{t["surface"]}">+3884</text>')

    p.append(f'  <rect x="478" y="{fy - 44}" width="64" height="36" rx="6" fill="{t["blue"]}" opacity="0.88"/>')
    p.append(f'  <text x="510" y="{fy - 22}" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="{t["surface"]}">+116</text>')

    # Negative Debit Block BELOW fulcrum (exact mirrored geometric weight = 4000)
    p.append(f'  <rect x="424" y="{fy + 8}" width="194" height="76" rx="6" fill="{t["terra"]}" opacity="0.88"/>')
    p.append(f'  <rect x="438" y="{fy + 20}" width="166" height="52" rx="3" fill="none" stroke="{t["surface"]}" stroke-width="1.3" opacity="0.55"/>')
    p.append(f'  <text x="521" y="{fy + 51}" text-anchor="middle" class="mono" font-size="13" font-weight="700" fill="{t["surface"]}">-4000 EUR</text>')

    # Vertical dashed balance projection lines
    p.append(f'  <line x1="356" y1="{fy - 134}" x2="356" y2="{fy + 98}" stroke="{t["teal"]}" stroke-width="1.1" stroke-dasharray="3 4"/>')
    p.append(f'  <line x1="618" y1="{fy - 134}" x2="618" y2="{fy + 98}" stroke="{t["terra"]}" stroke-width="1.1" stroke-dasharray="3 4"/>')
    p.append(f'  <text x="488" y="346" text-anchor="middle" class="mono" font-size="10.5" fill="{t["muted"]}">DOUBLE-ENTRY CONSERVATION</text>')

    # --- Right: Concentric Octagonal PCI-DSS Vault & 3-Way Reconciliation Ribbons (center: 794, 186) ---
    vx, vy = 794, 186

    def oct_pts(cx0, cy0, rad):
        pts = []
        for k in range(8):
            ang = math.radians(22.5 + k * 45)
            pts.append(f"{cx0 + rad * math.cos(ang):.1f},{cy0 + rad * math.sin(ang):.1f}")
        return " ".join(pts)

    p.append(f'  <polygon points="{oct_pts(vx, vy, 118)}" fill="{t["terra_soft"]}" fill-opacity="0.55" stroke="{t["terra"]}" stroke-width="1.6" stroke-dasharray="6 4"/>')
    p.append(f'  <polygon points="{oct_pts(vx, vy, 86)}" fill="{t["surface"]}" stroke="{t["ochre"]}" stroke-width="2.0"/>')
    p.append(f'  <polygon points="{oct_pts(vx, vy, 54)}" fill="{t["ochre_soft"]}" stroke="{t["teal"]}" stroke-width="2.0"/>')
    p.append(f'  <polygon points="{vx},{vy - 24} {vx + 24},{vy} {vx},{vy + 24} {vx - 24},{vy}" fill="{t["teal"]}"/>')
    p.append(f'  <circle cx="{vx}" cy="{vy}" r="6" fill="{t["surface"]}"/>')

    # Three converging reconciliation ribbons (T+0, T+1, T+2) arriving into the bottom-right seal
    ribbon_y = [322, 342, 362]
    ribbon_c = [t["blue"], t["indigo"], t["teal"]]
    ribbon_l = ["T+0", "T+1", "T+2"]
    for ry, rc, rl in zip(ribbon_y, ribbon_c, ribbon_l):
        p.append(f'  <line x1="686" y1="{ry}" x2="868" y2="{ry}" stroke="{rc}" stroke-width="3.2" stroke-linecap="round"/>')
        p.append(f'  <text x="676" y="{ry + 4}" text-anchor="end" class="mono" font-size="10" font-weight="700" fill="{rc}">{rl}</text>')
    # Vertical convergence seal on right
    p.append(f'  <polygon points="886,326 902,342 886,358 870,342" fill="{t["ochre"]}"/>')
    p.append(f'  <circle cx="886" cy="342" r="4" fill="{t["surface"]}"/>')
    p.append(f'  <text x="{vx}" y="54" text-anchor="middle" class="mono" font-size="10.5" font-weight="700" fill="{t["terra"]}">ISOLATED PCI VAULT</text>')

    p.append("</svg>\n")
    return "\n".join(p)


# =============================================================================
# BOOK COVER (900x1260 MONOGRAPH PORTRAIT — SWISS BAUHAUS ABSTRACT GEOMETRY)
# =============================================================================

def book_cover(t: dict) -> str:
    CW, CH = 900, 1260
    bg = t["bg_pay"]
    grid = t["grid_pay"]
    aria = (
        "Cover of Distributed Systems from the Ground Up by Arpan Pathak. "
        "A crisp Swiss-Modernist abstract geometric composition featuring a concentric "
        "consistent-hash ring, a five-node consensus constellation with four interconnected "
        "quorum nodes separated by a dashed partition cut from one isolated node, and a "
        "harmonic rate-shaping wave."
    )
    p = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CW} {CH}" width="{CW}" height="{CH}" '
        f'shape-rendering="geometricPrecision" text-rendering="geometricPrecision" role="img" aria-label="{escape(aria)}">',
        "  <style>",
        '    .sans { font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; }',
        '    .serif { font-family: Georgia, "Iowan Old Style", "Times New Roman", serif; }',
        '    .mono { font-family: "SF Mono", SFMono-Regular, ui-monospace, Menlo, Consolas, monospace; }',
        "  </style>",
        f'  <rect x="0.5" y="0.5" width="{CW - 1}" height="{CH - 1}" rx="16" fill="{bg}" stroke="{t["hair"]}" stroke-width="1.2"/>',
    ]
    # Crisp architectural 45px grid
    for gx in range(45, CW, 45):
        p.append(f'  <line x1="{gx}" y1="1" x2="{gx}" y2="{CH - 1}" stroke="{grid}" stroke-width="0.75"/>')
    for gy in range(45, CH, 45):
        p.append(f'  <line x1="1" y1="{gy}" x2="{CW - 1}" y2="{gy}" stroke="{grid}" stroke-width="0.75"/>')

    # Clean outer Swiss editorial frame inset
    p.append(f'  <rect x="34" y="34" width="{CW - 68}" height="{CH - 68}" rx="8" fill="none" stroke="{t["hair"]}" stroke-width="1.1"/>')

    # --- Top Swiss Editorial Masthead ---
    p += [
        f'  <rect x="70" y="76" width="64" height="5" rx="2.5" fill="{t["terra"]}"/>',
        f'  <text x="70" y="110" class="mono" font-size="12.5" font-weight="700" fill="{t["muted"]}" letter-spacing="0.12em">SYSTEMS ARCHITECTURE MONOGRAPH  ·  SIX PARTS  ·  28 CHAPTERS</text>',
        f'  <text x="70" y="182" class="sans" font-size="60" font-weight="800" fill="{t["ink"]}" letter-spacing="-0.025em">Distributed Systems</text>',
        f'  <text x="70" y="238" class="serif" font-size="40" font-style="italic" fill="{t["blue"]}" letter-spacing="-0.01em">from the Ground Up</text>',
        f'  <text x="70" y="282" class="sans" font-size="17" font-weight="500" fill="{t["muted"]}">Consensus, Storage Engines, Traffic Control, and Fault-Tolerant Architecture</text>',
        f'  <line x1="70" y1="312" x2="{CW - 70}" y2="312" stroke="{t["hair"]}" stroke-width="1.2"/>',
    ]

    # --- Centerpiece Abstract Geometric Sculpture (cx=450, cy=692) ---
    cx, cy = 450, 692

    # Soft translucent Bauhaus background color planes (balanced asymmetric geometry)
    p.append(f'  <rect x="96" y="370" width="240" height="310" rx="6" fill="{t["blue_soft"]}" opacity="0.52"/>')
    p.append(f'  <rect x="564" y="692" width="240" height="296" rx="6" fill="{t["teal_soft"]}" opacity="0.52"/>')
    p.append(f'  <circle cx="678" cy="482" r="108" fill="{t["terra_soft"]}" opacity="0.58"/>')

    # Subtle harmonic laminar wave crossing the horizontal axis
    wave_pts = []
    for x in range(72, CW - 70, 8):
        y = cy + 54 * math.sin((x - 72) * math.pi / 151.0)
        wave_pts.append(f"{x:.1f},{y:.1f}")
    p.append(f'  <polyline points="{" ".join(wave_pts)}" fill="none" stroke="{t["teal"]}" stroke-width="1.8" opacity="0.45"/>')

    # Horizontal equilibrium / zero-sum datum line
    p.append(f'  <line x1="70" y1="{cy}" x2="{CW - 70}" y2="{cy}" stroke="{t["ink"]}" stroke-width="1.2" opacity="0.28"/>')
    p.append(f'  <line x1="{cx}" y1="346" x2="{cx}" y2="1038" stroke="{t["ink"]}" stroke-width="1.0" opacity="0.18" stroke-dasharray="4 6"/>')

    # Outer compass ring + segmented 64-bit consistent-hash arcs (R = 266)
    p.append(f'  <circle cx="{cx}" cy="{cy}" r="298" fill="none" stroke="{t["hair"]}" stroke-width="1.2" stroke-dasharray="4 6"/>')
    p.append(f'  <path d="{arc_path(cx, cy, 266, -110, -8)}" fill="none" stroke="{t["blue"]}" stroke-width="22"/>')
    p.append(f'  <path d="{arc_path(cx, cy, 266, 6, 118)}" fill="none" stroke="{t["teal"]}" stroke-width="22"/>')
    p.append(f'  <path d="{arc_path(cx, cy, 266, 132, 198)}" fill="none" stroke="{t["ochre"]}" stroke-width="22"/>')
    p.append(f'  <path d="{arc_path(cx, cy, 266, 212, 240)}" fill="none" stroke="{t["terra"]}" stroke-width="22" opacity="0.88"/>')

    # 36 radial virtual-node ticks between R=216 and R=244
    for k in range(36):
        ang = math.radians(k * 10)
        r0 = 212 if k % 3 == 0 else 224
        r1 = 244
        x0, y0 = cx + r0 * math.cos(ang), cy + r0 * math.sin(ang)
        x1, y1 = cx + r1 * math.cos(ang), cy + r1 * math.sin(ang)
        col = [t["blue"], t["teal"], t["ochre"], t["terra"]][k % 4]
        p.append(f'  <line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{col}" stroke-width="{2.0 if k % 3 == 0 else 1.0}" opacity="0.72"/>')

    # Inner consensus ring (R = 178) holding a 5-Node Quorum Constellation
    # 4 healthy nodes (N0..N3) fully connected in a majority quorum; 1 node (N4, top-right) isolated by a crisp partition cut!
    p.append(f'  <circle cx="{cx}" cy="{cy}" r="178" fill="{t["surface"]}" fill-opacity="0.82" stroke="{t["hair"]}" stroke-width="1.4"/>')
    node_angles = [-126, -198, -270, -342, -54]  # N4 at -54 deg (upper right) is partitioned
    pts = [(cx + 148 * math.cos(math.radians(a)), cy + 148 * math.sin(math.radians(a))) for a in node_angles]

    # Quorum mesh chords among the 4 agreed nodes (N0, N1, N2, N3)
    for i in range(4):
        for j in range(i + 1, 4):
            x1, y1 = pts[i]
            x2, y2 = pts[j]
            p.append(f'  <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{t["blue"]}" stroke-width="2.2" opacity="0.78"/>')

    # Translucent quorum polygon filling the 4 agreed nodes
    poly = " ".join(f"{pts[i][0]:.1f},{pts[i][1]:.1f}" for i in range(4))
    p.append(f'  <polygon points="{poly}" fill="{t["blue_soft"]}" fill-opacity="0.62" stroke="{t["blue"]}" stroke-width="2.2"/>')

    # Broken dashed links to the 1 partitioned node (N4)
    p4x, p4y = pts[4]
    for i in (0, 3):
        x1, y1 = pts[i]
        p.append(f'  <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{p4x:.1f}" y2="{p4y:.1f}" stroke="{t["terra"]}" stroke-width="1.6" stroke-dasharray="5 6" opacity="0.72"/>')

    # Crisp diagonal Partition Cut cleanly slicing between the 4-node quorum and isolated N4
    p.append(f'  <line x1="448" y1="518" x2="646" y2="716" stroke="{t["terra"]}" stroke-width="2.4" stroke-dasharray="9 6"/>')

    # Central Consensus Core (nested geometric diamond + circle)
    p.append(f'  <polygon points="{cx},{cy - 34} {cx + 34},{cy} {cx},{cy + 34} {cx - 34},{cy}" fill="{t["teal"]}"/>')
    p.append(f'  <circle cx="{cx}" cy="{cy}" r="12" fill="{t["surface"]}"/>')
    p.append(f'  <circle cx="{cx}" cy="{cy}" r="5" fill="{t["ochre"]}"/>')

    # Draw the 5 Quorum Nodes (N0 = Leader in Ochre, N1..N3 = Agreed Followers in Blue/Teal, N4 = Partitioned in Terracotta)
    node_styles = [
        (t["ochre"], t["surface"], 19),   # Leader
        (t["blue"], t["surface"], 16),    # Follower 1
        (t["teal"], t["surface"], 16),    # Follower 2
        (t["blue"], t["surface"], 16),    # Follower 3
        (t["terra"], t["terra_soft"], 16), # Partitioned
    ]
    for idx, ((nx, ny), (stroke_c, fill_c, nr)) in enumerate(zip(pts, node_styles)):
        p.append(f'  <circle cx="{nx:.1f}" cy="{ny:.1f}" r="{nr}" fill="{fill_c}" stroke="{stroke_c}" stroke-width="4.2"/>')
        if idx == 0:
            p.append(f'  <circle cx="{nx:.1f}" cy="{ny:.1f}" r="6.5" fill="{t["ochre"]}"/>')
        elif idx == 4:
            # Small crisp X mark inside partitioned node
            p.append(f'  <line x1="{nx - 5:.1f}" y1="{ny - 5:.1f}" x2="{nx + 5:.1f}" y2="{ny + 5:.1f}" stroke="{t["terra"]}" stroke-width="2.2" stroke-linecap="round"/>')
            p.append(f'  <line x1="{nx + 5:.1f}" y1="{ny - 5:.1f}" x2="{nx - 5:.1f}" y2="{ny + 5:.1f}" stroke="{t["terra"]}" stroke-width="2.2" stroke-linecap="round"/>')
        else:
            p.append(f'  <circle cx="{nx:.1f}" cy="{ny:.1f}" r="5" fill="{stroke_c}"/>')

    # Crisp geometric legend annotations around the sculpture
    p += [
        f'  <text x="96" y="1028" class="mono" font-size="11.5" font-weight="700" fill="{t["blue"]}">QUORUM  4 OF 5  ·  |Q1 ∩ Q2| &gt;= 1</text>',
        f'  <text x="{CW - 96}" y="1028" text-anchor="end" class="mono" font-size="11.5" font-weight="700" fill="{t["terra"]}">PARTITION ISOLATED</text>',
    ]

    # --- Bottom Author & Taxonomy Footer ---
    p += [
        f'  <line x1="70" y1="1084" x2="{CW - 70}" y2="1084" stroke="{t["ink"]}" stroke-width="1.6"/>',
        f'  <text x="70" y="1136" class="sans" font-size="26" font-weight="800" fill="{t["ink"]}" letter-spacing="0.06em">ARPAN PATHAK</text>',
        f'  <text x="70" y="1168" class="mono" font-size="12" font-weight="600" fill="{t["muted"]}" letter-spacing="0.05em">MULTI-RAFT  ·  GCRA  ·  DOUBLE-ENTRY LEDGERS  ·  EVENT STREAMING</text>',
        f'  <rect x="{CW - 122}" y="1112" width="52" height="52" rx="8" fill="{t["blue_soft"]}" stroke="{t["blue"]}" stroke-width="1.8"/>',
        f'  <circle cx="{CW - 96}" cy="1138" r="14" fill="none" stroke="{t["blue"]}" stroke-width="2.2"/>',
        f'  <circle cx="{CW - 96}" cy="1138" r="5" fill="{t["terra"]}"/>',
    ]

    p.append("</svg>\n")
    return "\n".join(p)


def main():
    from draw_m3_plates_all import EXTRA_PLATES
    (OUT / "dark").mkdir(parents=True, exist_ok=True)
    plates = {
        "cover.svg": book_cover,
        "ch01-plate.svg": plate_ch01,
        "ch07-plate.svg": plate_ch07,
        "ch19-plate.svg": plate_ch19,
    }
    plates.update(EXTRA_PLATES)
    for filename, fn in sorted(plates.items()):
        (OUT / filename).write_text(fn(LIGHT), encoding="utf-8")
        (OUT / "dark" / filename).write_text(fn(DARK), encoding="utf-8")
    print(f"generated {len(plates)} plates ({len(plates)*2} light+dark SVGs)")


if __name__ == "__main__":
    main()
