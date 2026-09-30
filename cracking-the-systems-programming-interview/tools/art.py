#!/usr/bin/env python3
"""Draw the cover and the chapter-opener plates.

Every plate is composed from the same parts: a blueprint ground, a robot
mechanic drawn from a small set of heads, eyes, and tools, and one machine that
stands for the chapter's subject. The SVG is written to src/art/ and rasterised
to PNG with rsvg-convert, so the lettering looks the same in the browser and in
the PDF.

    python3 tools/art.py
"""

from __future__ import annotations

import math
import pathlib
import shutil
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "src" / "art"

INK = "#1d2733"
STEEL = "#5b6b7c"
STEEL_LIGHT = "#aebccb"
STEEL_PALE = "#d9e1e8"
PAPER = "#f3ede0"
RUST = "#d9622b"
BRASS = "#c89b3c"
TEAL = "#2f7f86"
CREAM = "#fbf7ee"

STENCIL = "DIN Condensed, Avenir Next Condensed, Helvetica Neue, sans-serif"
SERIF = "Charter, Iowan Old Style, Georgia, serif"
SANS = "Avenir Next, Helvetica Neue, sans-serif"


# ---------------------------------------------------------------- primitives


def gear(cx: float, cy: float, r: float, teeth: int, fill: str, hole: str | None = PAPER,
         stroke: str = INK, width: float = 2, rotate: float = 0) -> str:
    """A spur gear: `teeth` square teeth around a disc, with an axle hole."""
    depth = r * 0.18
    points = []
    steps = teeth * 4
    for i in range(steps):
        angle = 2 * math.pi * i / steps + math.radians(rotate)
        radius = r + depth if i % 4 in (1, 2) else r
        points.append("%.1f,%.1f" % (cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    body = '<polygon points="%s" fill="%s" stroke="%s" stroke-width="%s" stroke-linejoin="round"/>' % (
        " ".join(points), fill, stroke, width)
    if hole:
        body += '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="%s" stroke-width="%s"/>' % (
            cx, cy, r * 0.28, hole, stroke, width)
        for k in range(6):
            a = math.pi * k / 3 + math.radians(rotate)
            body += '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s"/>' % (
                cx + r * 0.62 * math.cos(a), cy + r * 0.62 * math.sin(a), r * 0.08, stroke)
    return body


def rivets(x: float, y: float, w: float, h: float, inset: float = 7, r: float = 2.4) -> str:
    return "".join(
        '<circle cx="%.1f" cy="%.1f" r="%s" fill="%s"/>' % (px, py, r, INK)
        for px, py in ((x + inset, y + inset), (x + w - inset, y + inset),
                       (x + inset, y + h - inset), (x + w - inset, y + h - inset)))


def rect(x, y, w, h, fill, stroke=INK, width=2.5, rx=4, extra=""):
    return '<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" rx="%s" fill="%s" stroke="%s" stroke-width="%s" %s/>' % (
        x, y, w, h, rx, fill, stroke, width, extra)


def line(x1, y1, x2, y2, stroke=INK, width=2.5, extra=""):
    return '<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" stroke="%s" stroke-width="%s" stroke-linecap="round" %s/>' % (
        x1, y1, x2, y2, stroke, width, extra)


def circle(cx, cy, r, fill, stroke=INK, width=2.5, extra=""):
    return '<circle cx="%.1f" cy="%.1f" r="%.1f" fill="%s" stroke="%s" stroke-width="%s" %s/>' % (
        cx, cy, r, fill, stroke, width, extra)


def text(x, y, body, size, fill=INK, family=STENCIL, anchor="start", weight="normal",
         spacing=0, extra=""):
    return ('<text x="%.1f" y="%.1f" font-family="%s" font-size="%s" fill="%s" text-anchor="%s" '
            'font-weight="%s" letter-spacing="%s" %s>%s</text>') % (
        x, y, family, size, fill, anchor, weight, spacing, extra, body)


def box(x, y, w, h, fill, label="", size=16):
    """A crate or memory cell with an optional stencilled label."""
    out = rect(x, y, w, h, fill, rx=2)
    out += line(x + 4, y + 4, x + w - 4, y + h - 4, STEEL, 1, 'opacity="0.35"')
    if label:
        out += text(x + w / 2, y + h / 2 + size * 0.36, label, size, INK, anchor="middle")
    return out


def arrow(x1, y1, x2, y2, color=INK, width=2.5):
    angle = math.atan2(y2 - y1, x2 - x1)
    head = 10
    left = (x2 - head * math.cos(angle - 0.45), y2 - head * math.sin(angle - 0.45))
    right = (x2 - head * math.cos(angle + 0.45), y2 - head * math.sin(angle + 0.45))
    return line(x1, y1, x2, y2, color, width) + '<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="%s"/>' % (
        x2, y2, left[0], left[1], right[0], right[1], color)


def defs() -> str:
    return """
<defs>
  <pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">
    <path d="M 24 0 L 0 0 0 24" fill="none" stroke="#c9d4de" stroke-width="0.8"/>
  </pattern>
  <pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
    <line x1="0" y1="0" x2="0" y2="6" stroke="#1d2733" stroke-width="1.1" opacity="0.55"/>
  </pattern>
  <pattern id="hatch-fine" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(-35)">
    <line x1="0" y1="0" x2="0" y2="4" stroke="#1d2733" stroke-width="0.7" opacity="0.4"/>
  </pattern>
  <pattern id="stripes" width="20" height="20" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
    <rect width="10" height="20" fill="#1d2733"/><rect x="10" width="10" height="20" fill="#e3b23c"/>
  </pattern>
  <linearGradient id="steel" x1="0" x2="1" y1="0" y2="1">
    <stop offset="0" stop-color="#e3e9ef"/><stop offset="1" stop-color="#9fb0c1"/>
  </linearGradient>
  <linearGradient id="brass" x1="0" x2="0" y1="0" y2="1">
    <stop offset="0" stop-color="#e8c56b"/><stop offset="1" stop-color="#b3842c"/>
  </linearGradient>
  <linearGradient id="copper" x1="0" x2="0" y1="0" y2="1">
    <stop offset="0" stop-color="#ee8a52"/><stop offset="1" stop-color="#b9471b"/>
  </linearGradient>
</defs>"""


# ------------------------------------------------------------------- robots


def tool(kind: str, x: float, y: float) -> str:
    """A tool gripped at (x, y), the end of the robot's right arm."""
    if kind == "wrench":
        return ('<g transform="rotate(-35 %.1f %.1f)">' % (x, y)
                + rect(x - 5, y - 70, 10, 78, "url(#steel)", rx=4)
                + '<path d="M %.1f %.1f a 16 16 0 1 1 18 0 l -4 -12 h -10 z" fill="url(#steel)" stroke="%s" stroke-width="2.5"/>'
                % (x - 9, y - 66, INK) + "</g>")
    if kind == "hammer":
        return (rect(x - 4, y - 60, 8, 70, BRASS, rx=3)
                + rect(x - 22, y - 76, 44, 20, "url(#steel)", rx=3))
    if kind == "torch":
        return (rect(x - 5, y - 40, 10, 48, STEEL, rx=3)
                + '<path d="M %.1f %.1f q 10 -22 0 -40 q -10 18 0 40 z" fill="%s" stroke="%s" stroke-width="2"/>'
                % (x, y - 40, RUST, INK)
                + '<path d="M %.1f %.1f q 5 -12 0 -22 q -5 10 0 22 z" fill="#f6d36b"/>' % (x, y - 42))
    if kind == "clipboard":
        return (rect(x - 20, y - 56, 40, 54, CREAM, rx=3)
                + rect(x - 8, y - 60, 16, 8, STEEL, rx=2)
                + "".join(line(x - 13, y - 44 + 9 * i, x + 13, y - 44 + 9 * i, STEEL, 2) for i in range(4))
                + '<path d="M %.1f %.1f l 5 5 l 9 -11" fill="none" stroke="%s" stroke-width="3"/>' % (x - 12, y - 14, RUST))
    if kind == "screwdriver":
        return ('<g transform="rotate(-20 %.1f %.1f)">' % (x, y)
                + rect(x - 7, y - 30, 14, 36, RUST, rx=5)
                + rect(x - 2, y - 72, 4, 44, "url(#steel)", width=2, rx=1) + "</g>")
    if kind == "oilcan":
        return ('<path d="M %.1f %.1f l 22 0 l 6 -26 l -34 0 z" fill="url(#brass)" stroke="%s" stroke-width="2.5"/>' % (x - 14, y, INK)
                + line(x + 10, y - 22, x + 40, y - 50, INK, 3.5))
    if kind == "stopwatch":
        return (circle(x, y - 28, 22, CREAM) + rect(x - 5, y - 58, 10, 8, STEEL, rx=2)
                + line(x, y - 28, x, y - 44, RUST, 3) + line(x, y - 28, x + 10, y - 22, INK, 2.5))
    if kind == "magnifier":
        return (circle(x + 14, y - 38, 20, "#d8eef0") + line(x, y - 14, x + 4, y - 22, INK, 7))
    if kind == "flag":
        return (line(x, y + 6, x, y - 72, INK, 3.5)
                + '<path d="M %.1f %.1f h 44 l -10 14 l 10 14 h -44 z" fill="%s" stroke="%s" stroke-width="2.5"/>' % (x, y - 72, RUST, INK))
    return ""


def robot(x: float, y: float, s: float, head: str = "box", eyes: str = "round", antenna: str = "bolt",
          body: str = "url(#steel)", accent: str = RUST, held: str = "wrench", badge: str = "") -> str:
    """A robot mechanic standing with feet on y, centred on x, scaled by s."""
    parts: list[str] = ['<g transform="translate(%.1f %.1f) scale(%.2f)">' % (x, y, s)]
    # Legs and boots.
    parts.append(rect(-34, -70, 20, 64, STEEL_LIGHT, rx=3) + rect(14, -70, 20, 64, STEEL_LIGHT, rx=3))
    parts.append(rect(-42, -10, 34, 12, INK, rx=4) + rect(8, -10, 34, 12, INK, rx=4))
    parts.append(line(-34, -40, -14, -40, INK, 2) + line(14, -40, 34, -40, INK, 2))
    # Torso with a chest panel and a hazard belt.
    parts.append(rect(-52, -170, 104, 104, body, rx=10))
    parts.append(rivets(-52, -170, 104, 104))
    parts.append(rect(-30, -150, 60, 44, INK, rx=4))
    parts.append(rect(-52, -82, 104, 12, "url(#stripes)", rx=2))
    if badge:
        parts.append(text(0, -119, badge, 20, "#9fe3c8", anchor="middle", spacing=1))
    else:
        parts.append(''.join(circle(-14 + 14 * i, -128, 5, c, INK, 1.5) for i, c in enumerate(("#9fe3c8", accent, "#f6d36b"))))
    # Left arm hangs, right arm raised holding the tool.
    parts.append(circle(-60, -158, 11, accent))
    parts.append(line(-62, -150, -74, -100, INK, 13) + line(-62, -150, -74, -100, STEEL_LIGHT, 8))
    parts.append(circle(-76, -96, 9, INK))
    parts.append(circle(60, -158, 11, accent))
    parts.append(line(62, -152, 92, -118, INK, 13) + line(62, -152, 92, -118, STEEL_LIGHT, 8))
    parts.append(line(92, -118, 104, -160, INK, 13) + line(92, -118, 104, -160, STEEL_LIGHT, 8))
    parts.append(circle(92, -118, 7, accent))
    parts.append(tool(held, 104, -160))
    parts.append(circle(104, -162, 9, INK))
    # Neck.
    parts.append(rect(-12, -186, 24, 18, STEEL, rx=2))
    # Head.
    if head == "dome":
        parts.append('<path d="M -46 -186 v -34 a 46 46 0 0 1 92 0 v 34 z" fill="%s" stroke="%s" stroke-width="2.5"/>' % (body, INK))
        top = -266
    elif head == "tv":
        parts.append(rect(-54, -254, 108, 70, body, rx=14))
        parts.append(rect(-44, -246, 88, 54, "#243241", rx=10))
        top = -254
    elif head == "tall":
        parts.append(rect(-34, -268, 68, 84, body, rx=8))
        parts.append(rivets(-34, -268, 68, 84, 6, 2))
        top = -268
    else:
        parts.append(rect(-44, -250, 88, 66, body, rx=8))
        parts.append(rivets(-44, -250, 88, 66, 6, 2))
        top = -250
    # Ears.
    parts.append(rect(-58 if head != "tall" else -46, -232, 12, 28, accent, rx=3))
    parts.append(rect(46 if head != "tall" else 34, -232, 12, 28, accent, rx=3))
    # Eyes.
    ey = -222
    if eyes == "goggles":
        parts.append(rect(-44, ey - 12, 88, 10, INK, rx=3))
        parts.append(circle(-18, ey, 15, "url(#brass)") + circle(18, ey, 15, "url(#brass)"))
        parts.append(circle(-18, ey, 9, "#9fe3c8") + circle(18, ey, 9, "#9fe3c8"))
        parts.append(circle(-15, ey - 3, 3, "#ffffff", "none", 0) + circle(21, ey - 3, 3, "#ffffff", "none", 0))
    elif eyes == "visor":
        parts.append(rect(-36, ey - 10, 72, 20, INK, rx=10))
        parts.append(rect(-28, ey - 4, 56, 8, "#ff8a5c", "none", 0, rx=4))
    elif eyes == "screen":
        parts.append(rect(-34, ey - 22, 68, 40, "#243241", rx=6))
        parts.append(text(0, ey + 8, "&gt;_", 28, "#9fe3c8", family="Menlo, monospace", anchor="middle", weight="bold"))
    elif eyes == "mono":
        parts.append(circle(0, ey, 17, "url(#brass)") + circle(0, ey, 10, "#9fe3c8") + circle(3, ey - 3, 3, "#ffffff", "none", 0))
    else:
        parts.append(circle(-18, ey, 11, CREAM) + circle(18, ey, 11, CREAM))
        parts.append(circle(-16, ey, 5, INK, "none", 0) + circle(20, ey, 5, INK, "none", 0))
    # Mouth grille.
    if eyes != "screen":
        parts.append(rect(-20, -204, 40, 10, INK, rx=2))
        parts.append("".join(line(-12 + 8 * i, -203, -12 + 8 * i, -196, STEEL_LIGHT, 1.5) for i in range(4)))
    # Antenna.
    if antenna == "bolt":
        parts.append(line(0, top, 0, top - 24, INK, 3) + circle(0, top - 28, 7, accent))
    elif antenna == "dish":
        parts.append(line(0, top, 0, top - 16, INK, 3))
        parts.append('<path d="M -20 %.1f a 20 12 0 0 0 40 0 z" fill="url(#brass)" stroke="%s" stroke-width="2.5"/>' % (top - 18, INK))
    elif antenna == "spring":
        coil = "M 0 %.1f " % top + " ".join("l %d -5" % (8 if i % 2 == 0 else -8) for i in range(6))
        parts.append('<path d="%s" fill="none" stroke="%s" stroke-width="2.5"/>' % (coil, INK) + circle(0, top - 34, 6, accent))
    elif antenna == "hat":
        parts.append(rect(-40, top - 12, 80, 14, "#f0b429", rx=6) + '<path d="M -30 %.1f a 30 26 0 0 1 60 0 z" fill="#f0b429" stroke="%s" stroke-width="2.5"/>' % (top - 10, INK))
    elif antenna == "twin":
        parts.append(line(-20, top, -30, top - 24, INK, 3) + circle(-31, top - 28, 5, accent))
        parts.append(line(20, top, 30, top - 24, INK, 3) + circle(31, top - 28, 5, accent))
    parts.append("</g>")
    return "".join(parts)


# ------------------------------------------------------------------ machines


def machine_types(x, y):
    """A shape sorter: blocks on a belt, and a gate that accepts one profile."""
    out = rect(x, y + 120, 380, 22, INK, rx=11)
    out += "".join(circle(x + 22 + 42 * i, y + 131, 7, STEEL_LIGHT) for i in range(9))
    out += rect(x + 241, y - 20, 108, 140, "url(#steel)", rx=4) + rivets(x + 241, y - 20, 108, 140)
    out += '<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="%s" stroke="%s" stroke-width="2.5"/>' % (
        x + 272, y + 70, x + 318, y + 70, x + 295, y + 30, INK, INK)
    out += text(x + 295, y + 8, "TRY_FROM", 18, INK, anchor="middle", spacing=1)
    out += '<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="%s" stroke="%s" stroke-width="2.5"/>' % (
        x + 160, y + 118, x + 212, y + 118, x + 186, y + 72, "url(#copper)", INK)
    out += rect(x + 30, y + 72, 46, 46, "url(#brass)", rx=2) + circle(x + 118, y + 95, 23, TEAL)
    out += text(x + 53, y + 104, "u32", 18, INK, anchor="middle")
    out += text(x + 118, y + 101, "&amp;str", 16, CREAM, anchor="middle")
    out += rect(x + 360, y + 60, 50, 60, "#e8f5e9", rx=4) + text(x + 385, y + 98, "OK", 22, TEAL, anchor="middle")
    out += rect(x + 196, y - 60, 44, 40, "#fbe3d6", rx=4) + text(x + 218, y - 33, "ERR", 16, RUST, anchor="middle")
    out += arrow(x + 186, y + 66, x + 212, y - 16, RUST)
    return out


def machine_files(x, y):
    """A filing cabinet, a stack of pages, and a paper feed."""
    out = rect(x, y - 30, 140, 200, "url(#steel)", rx=4)
    for i in range(3):
        out += rect(x + 12, y - 18 + 64 * i, 116, 54, STEEL_PALE, rx=3)
        out += rect(x + 50, y + 2 + 64 * i, 40, 10, INK, rx=4)
        out += text(x + 70, y - 2 + 64 * i, ("/etc", "/var", "/home")[i], 16, INK, anchor="middle", family="Menlo, monospace")
    for i in range(5):
        out += rect(x + 190 + i * 6, y + 90 - i * 8, 90, 70, CREAM, rx=2)
    out += "".join(line(x + 232, y + 72 + 10 * k, x + 305, y + 72 + 10 * k, STEEL, 2) for k in range(4))
    out += text(x + 262, y + 62, "PAGE 3", 16, RUST, anchor="middle")
    out += arrow(x + 150, y + 40, x + 196, y + 60, RUST)
    out += rect(x + 320, y - 10, 70, 180, INK, rx=6) + text(x + 355, y + 30, "OFFSET", 15, CREAM, anchor="middle")
    out += text(x + 355, y + 58, "4096", 24, "#9fe3c8", anchor="middle")
    return out


def machine_arrays(x, y):
    """A parts shelf of numbered bins and a hashing hopper."""
    out = ""
    for i in range(6):
        out += box(x + 60 * i, y + 90, 56, 56, ("url(#brass)" if i == 3 else STEEL_PALE), str(i), 20)
    out += line(x - 8, y + 148, x + 366, y + 148, INK, 5)
    out += '<path d="M %.1f %.1f h 120 l -40 60 h -40 z" fill="url(#steel)" stroke="%s" stroke-width="2.5"/>' % (x + 120, y - 50, INK)
    out += text(x + 180, y - 22, "HASH", 22, INK, anchor="middle", spacing=2)
    out += arrow(x + 180, y + 14, x + 212, y + 84, RUST, 3)
    # The label ends before the arrow starts, so the shaft does not cross the text.
    out += text(x + 44, y - 46, '"gpu"', 18, TEAL, family="Menlo, monospace")
    out += arrow(x + 108, y - 52, x + 132, y - 36, TEAL)
    return out


def machine_chain(x, y):
    """A crane hook holding a chain of links, one opened for splicing."""
    out = rect(x + 10, y - 70, 360, 16, INK, rx=4)
    out += line(x + 60, y - 54, x + 60, y - 20, INK, 4)
    out += '<path d="M %.1f %.1f q 0 24 -18 24 q -14 0 -14 -12" fill="none" stroke="%s" stroke-width="6"/>' % (x + 60, y - 20, INK)
    for i in range(6):
        cx = x + 60 + i * 56
        cy = y + 6 + (i % 2) * 6
        out += '<rect x="%.1f" y="%.1f" width="58" height="30" rx="15" fill="none" stroke="%s" stroke-width="9"/>' % (cx - 20, cy, INK)
        out += '<rect x="%.1f" y="%.1f" width="58" height="30" rx="15" fill="none" stroke="%s" stroke-width="5"/>' % (
            cx - 20, cy, BRASS if i != 3 else RUST)
        out += text(cx + 9, cy + 58, ("head", "next", "next", "take()", "next", "None")[i], 15, STEEL, family="Menlo, monospace", anchor="middle")
    return out


def machine_merge(x, y):
    """Three conveyor belts feeding one."""
    out = ""
    for i in range(3):
        by = y - 40 + i * 60
        out += rect(x, by, 170, 16, INK, rx=8)
        for k in range(3):
            out += box(x + 12 + 50 * k, by - 32, 32, 30, (STEEL_PALE, "url(#brass)", "#d8eef0")[i], str(1 + i + 3 * k), 16)
        out += arrow(x + 176, by + 8, x + 222, y + 68, RUST)
    out += rect(x + 226, y + 40, 90, 56, "url(#steel)", rx=6) + text(x + 271, y + 76, "HEAP", 22, INK, anchor="middle")
    out += rect(x + 316, y + 78, 110, 16, INK, rx=8)
    out += "".join(box(x + 328 + 34 * k, y + 50, 28, 26, CREAM, str(k + 1), 14) for k in range(3))
    return out


def machine_tree(x, y):
    """A branching pipe manifold drawn as a binary tree."""
    nodes = {1: (x + 200, y - 40), 2: (x + 100, y + 40), 3: (x + 300, y + 40),
             4: (x + 50, y + 120), 5: (x + 150, y + 120), 6: (x + 250, y + 120), 7: (x + 350, y + 120)}
    out = ""
    for parent in (1, 2, 3):
        for child in (2 * parent, 2 * parent + 1):
            (px, py), (cx, cy) = nodes[parent], nodes[child]
            out += line(px, py, cx, cy, INK, 12) + line(px, py, cx, cy, STEEL_LIGHT, 7)
    for key, (cx, cy) in nodes.items():
        out += gear(cx, cy, 20, 10, "url(#brass)" if key == 1 else "url(#steel)", hole=CREAM, rotate=key * 7)
        out += text(cx, cy + 6, str([0, 8, 4, 12, 2, 6, 10, 14][key]), 16, INK, anchor="middle")
    return out


def machine_graph(x, y):
    """Pipes and valves wired into a small weighted graph."""
    pos = [(x + 30, y + 40), (x + 150, y - 30), (x + 150, y + 120), (x + 290, y + 20), (x + 400, y + 90)]
    edges = [(0, 1, "4"), (0, 2, "1"), (2, 1, "2"), (1, 3, "5"), (2, 3, "8"), (3, 4, "3")]
    out = ""
    for a, b, w in edges:
        (ax, ay), (bx, by) = pos[a], pos[b]
        out += line(ax, ay, bx, by, INK, 11) + line(ax, ay, bx, by, TEAL if (a, b) in ((0, 2), (2, 1), (1, 3), (3, 4)) else STEEL_LIGHT, 6)
        out += circle((ax + bx) / 2, (ay + by) / 2, 13, CREAM, INK, 2) + text((ax + bx) / 2, (ay + by) / 2 + 6, w, 16, INK, anchor="middle")
    for i, (cx, cy) in enumerate(pos):
        out += circle(cx, cy, 22, "url(#copper)" if i in (0, 4) else "url(#steel)")
        out += line(cx - 12, cy, cx + 12, cy, INK, 4) + text(cx, cy - 30, "ABCDE"[i], 20, INK, anchor="middle")
    return out


def machine_recursion(x, y):
    """A train of gears, each half the size of the last."""
    out = ""
    cx, r = x + 90, 80
    for k in range(5):
        out += gear(cx, y + 50 + (80 - r) * 0.4, r, max(8, int(r / 5)), "url(#brass)" if k % 2 == 0 else "url(#steel)", rotate=k * 11)
        cx += r + r * 0.5 + 10
        r *= 0.55
    out += text(x + 60, y - 70, "fib(n) = fib(n-1) + fib(n-2)", 18, STEEL, family="Menlo, monospace")
    return out


def machine_lru(x, y):
    """A rack of drawers with the least recently used crate leaving on a chute."""
    out = rect(x, y - 40, 250, 190, "url(#steel)", rx=4) + rivets(x, y - 40, 250, 190)
    labels = ["k7", "k2", "k9", "k4", "k1", "k5"]
    for i, label in enumerate(labels):
        col, row = i % 3, i // 3
        out += box(x + 18 + 76 * col, y - 20 + 86 * row, 62, 66, "url(#brass)" if i == 0 else STEEL_PALE, label, 20)
    out += text(x + 125, y - 52, "MRU  ...  LRU", 16, INK, anchor="middle", spacing=2)
    out += '<path d="M %.1f %.1f l 120 60" stroke="%s" stroke-width="10" fill="none"/>' % (x + 250, y + 90, INK)
    out += box(x + 330, y + 120, 50, 50, "#fbe3d6", "k5", 18)
    out += text(x + 355, y + 100, "EVICT", 18, RUST, anchor="middle", spacing=1)
    return out


def machine_ring(x, y):
    """A turntable of shards: the consistent-hash ring."""
    cx, cy, r = x + 200, y + 50, 110
    out = circle(cx, cy, r + 14, INK, INK, 2) + circle(cx, cy, r, "url(#steel)")
    out += circle(cx, cy, r - 30, PAPER)
    colors = [RUST, TEAL, BRASS, RUST, TEAL, BRASS, RUST, TEAL, BRASS]
    for i in range(9):
        a = 2 * math.pi * i / 9 - math.pi / 2
        out += circle(cx + (r - 15) * math.cos(a), cy + (r - 15) * math.sin(a), 11, colors[i], INK, 2)
    out += gear(cx, cy, 34, 12, "url(#brass)")
    out += text(x + 390, y - 20, "node A", 18, RUST) + text(x + 390, y + 10, "node B", 18, TEAL) + text(x + 390, y + 40, "node C", 18, "#9b7420")
    out += arrow(x + 360, y + 110, cx + r * 0.72, cy + r * 0.72, INK)
    out += text(x + 364, y + 130, 'hash("key")', 16, INK, family="Menlo, monospace")
    return out


def machine_memory(x, y):
    """A memory board of page frames, and a pressure gauge."""
    out = rect(x, y - 30, 270, 180, "#1f5f4a", rx=6)
    for r_ in range(3):
        for c in range(6):
            fill = RUST if (r_, c) in ((0, 2), (1, 4)) else ("url(#brass)" if (r_ + c) % 3 == 0 else "#2e7d63")
            out += rect(x + 16 + 42 * c, y - 12 + 52 * r_, 34, 40, fill, rx=2)
    out += "".join(line(x + 20 + 12 * i, y + 150, x + 20 + 12 * i, y + 164, BRASS, 3) for i in range(20))
    out += circle(x + 360, y + 40, 64, CREAM) + circle(x + 360, y + 40, 6, INK)
    for k in range(9):
        a = math.pi * (0.8 + 1.4 * k / 8)
        out += line(x + 360 + 50 * math.cos(a), y + 40 + 50 * math.sin(a), x + 360 + 60 * math.cos(a), y + 40 + 60 * math.sin(a), INK, 2)
    out += line(x + 360, y + 40, x + 400, y + 10, RUST, 4)
    out += text(x + 360, y + 80, "CACHE MISS", 12, INK, anchor="middle", spacing=1)
    return out


def machine_locks(x, y):
    """Spools of thread and a heavy padlock on the shared axle."""
    out = line(x, y + 60, x + 400, y + 60, INK, 10)
    for i in range(3):
        cx = x + 50 + 110 * i
        out += rect(cx - 30, y + 10, 60, 100, "url(#copper)" if i == 1 else "url(#steel)", rx=6)
        out += "".join(line(cx - 30, y + 20 + 8 * k, cx + 30, y + 24 + 8 * k, INK, 1.4) for k in range(11))
        out += rect(cx - 38, y + 2, 76, 12, INK, rx=3) + rect(cx - 38, y + 106, 76, 12, INK, rx=3)
        out += text(cx, y + 142, "T%d" % i, 18, INK, anchor="middle")
    out += '<path d="M %.1f %.1f v -40 a 34 34 0 0 1 68 0 v 40" fill="none" stroke="%s" stroke-width="12"/>' % (x + 316, y + 20, INK)
    out += rect(x + 300, y + 16, 100, 90, "url(#brass)", rx=8) + circle(x + 350, y + 52, 10, INK) + rect(x + 346, y + 56, 8, 26, INK, rx=2)
    return out


def machine_queue(x, y):
    """A carousel ring buffer beside a conveyor queue."""
    out = rect(x, y + 110, 230, 18, INK, rx=9)
    for k in range(4):
        out += box(x + 14 + 54 * k, y + 64, 44, 44, "url(#brass)" if k == 3 else STEEL_PALE, "J%d" % (4 - k), 16)
    out += arrow(x + 236, y + 118, x + 278, y + 118, RUST, 3)
    cx, cy = x + 360, y + 50
    out += circle(cx, cy, 80, "url(#steel)")
    for k in range(8):
        a = 2 * math.pi * k / 8 - math.pi / 2
        filled = k in (1, 2, 3, 4)
        out += rect(cx + 56 * math.cos(a) - 14, cy + 56 * math.sin(a) - 14, 28, 28, "url(#copper)" if filled else CREAM, rx=3)
    out += circle(cx, cy, 20, INK)
    out += text(cx - 58, cy - 92, "tail", 16, INK, family="Menlo, monospace") + text(cx + 40, cy + 116, "head", 16, INK, family="Menlo, monospace")
    return out


def machine_pool(x, y):
    """A job hopper feeding four small worker bots at a line shaft."""
    out = '<path d="M %.1f %.1f h 110 l -30 50 h -50 z" fill="url(#steel)" stroke="%s" stroke-width="2.5"/>' % (x + 150, y - 70, INK)
    out += text(x + 205, y - 44, "JOBS", 18, INK, anchor="middle", spacing=2)
    out += line(x + 205, y - 20, x + 205, y + 6, INK, 6)
    out += line(x + 20, y + 10, x + 400, y + 10, INK, 8)
    for i in range(4):
        wx = x + 55 + 100 * i
        out += line(wx, y + 10, wx, y + 40, INK, 3)
        out += robot(wx, y + 150, 0.38, head=("box", "dome", "tv", "tall")[i],
                     eyes=("round", "visor", "screen", "goggles")[i], antenna=("bolt", "twin", "dish", "spring")[i],
                     accent=(RUST, TEAL, BRASS, RUST)[i], held=("hammer", "wrench", "screwdriver", "torch")[i])
    return out


def machine_bucket(x, y):
    """A token bucket under a refill valve, with tokens leaving through a spout."""
    out = line(x + 40, y - 70, x + 190, y - 70, INK, 12) + line(x + 40, y - 70, x + 190, y - 70, STEEL_LIGHT, 7)
    out += line(x + 190, y - 70, x + 190, y - 30, INK, 12) + line(x + 190, y - 70, x + 190, y - 30, STEEL_LIGHT, 7)
    out += circle(x + 110, y - 70, 18, "url(#copper)") + line(x + 98, y - 70, x + 122, y - 70, INK, 4)
    out += text(x + 110, y - 98, "REFILL / s", 16, INK, anchor="middle", spacing=1)
    out += '<path d="M %.1f %.1f l 20 150 h 120 l 20 -150 z" fill="url(#steel)" stroke="%s" stroke-width="3"/>' % (x + 110, y - 20, INK)
    for k, (tx, ty) in enumerate(((150, 110), (190, 110), (230, 110), (170, 84), (210, 84), (190, 58))):
        out += circle(x + tx, y + ty, 15, "url(#brass)") + text(x + tx, y + ty + 5, "T", 14, INK, anchor="middle")
    out += circle(x + 190, y - 12, 8, "url(#brass)")
    out += line(x + 270, y + 110, x + 330, y + 110, INK, 12)
    out += circle(x + 352, y + 110, 15, "url(#brass)") + circle(x + 390, y + 110, 15, "url(#brass)")
    out += text(x + 370, y + 150, "429 when empty", 16, RUST, anchor="middle", family="Menlo, monospace")
    return out


def machine_network(x, y):
    """A lattice radio mast with waves, and a patch panel of sockets."""
    out = '<path d="M %.1f %.1f l 40 -200 l 40 200" fill="none" stroke="%s" stroke-width="5"/>' % (x + 40, y + 150, INK)
    for k in range(5):
        yy = y + 150 - 40 * k
        out += line(x + 40 + 8 * k, yy, x + 120 - 8 * k, yy, INK, 3)
        out += line(x + 40 + 8 * k, yy, x + 112 - 8 * k, yy - 40, INK, 1.5)
    out += circle(x + 80, y - 54, 9, RUST)
    for k in range(3):
        out += '<path d="M %.1f %.1f a %d %d 0 0 1 0 %d" fill="none" stroke="%s" stroke-width="3"/>' % (
            x + 100 + 16 * k, y - 54 - 14 - 10 * k, 18 + 10 * k, 18 + 10 * k, 28 + 20 * k, TEAL)
    out += rect(x + 200, y - 10, 210, 130, INK, rx=6)
    for r_ in range(2):
        for c in range(4):
            px, py = x + 216 + 48 * c, y + 6 + 56 * r_
            out += rect(px, py, 36, 36, STEEL_PALE, rx=3) + rect(px + 9, py + 12, 18, 14, INK, "none", 0, rx=2)
            out += circle(px + 18, py - 2 + 48, 3, "#9fe3c8" if (r_ + c) % 2 == 0 else RUST, "none", 0)
    out += text(x + 305, y + 142, ":8080", 18, INK, anchor="middle", family="Menlo, monospace")
    return out


def machine_http(x, y):
    """A pneumatic tube carrying a request capsule into a sorting office."""
    y -= 45
    out = '<path d="M %.1f %.1f h 170 q 40 0 40 40 v 70" fill="none" stroke="%s" stroke-width="30" stroke-linecap="round"/>' % (x, y, INK)
    out += '<path d="M %.1f %.1f h 170 q 40 0 40 40 v 70" fill="none" stroke="#d8eef0" stroke-width="22" stroke-linecap="round"/>' % (x, y)
    out += rect(x + 60, y - 10, 70, 20, "url(#copper)", rx=10)
    out += text(x + 95, y + 34, "GET /jobs HTTP/1.1", 15, INK, anchor="middle", family="Menlo, monospace")
    out += rect(x + 170, y + 110, 240, 80, "url(#steel)", rx=6) + rivets(x + 170, y + 110, 240, 80)
    for k, label in enumerate(("200", "404", "400", "413")):
        out += rect(x + 184 + 56 * k, y + 130, 46, 40, CREAM if k else "#e8f5e9", rx=3)
        out += text(x + 207 + 56 * k, y + 157, label, 16, TEAL if k == 0 else RUST, anchor="middle")
    out += rect(x + 300, y - 40, 110, 70, CREAM, rx=4)
    out += text(x + 312, y - 16, "Host:", 14, INK, family="Menlo, monospace") + text(x + 312, y + 4, "Content-", 14, INK, family="Menlo, monospace")
    out += text(x + 312, y + 22, " Length: 42", 14, INK, family="Menlo, monospace")
    return out


def machine_async(x, y):
    """A flywheel driven by a piston, with futures parked on a rail."""
    out = circle(x + 120, y + 50, 90, "none", INK, 10) + circle(x + 120, y + 50, 90, "none", "url(#steel)", 5)
    for k in range(6):
        a = math.pi * k / 3
        out += line(x + 120, y + 50, x + 120 + 86 * math.cos(a), y + 50 + 86 * math.sin(a), INK, 6)
    out += gear(x + 120, y + 50, 26, 10, "url(#brass)")
    out += line(x + 120 + 60, y + 50 - 40, x + 290, y + 50, INK, 9)
    out += rect(x + 280, y + 24, 110, 52, "url(#steel)", rx=4) + rect(x + 290, y + 34, 40, 32, "url(#copper)", rx=3)
    out += text(x + 360, y + 60, "poll", 16, INK, anchor="middle", family="Menlo, monospace")
    out += line(x + 20, y + 170, x + 420, y + 170, INK, 6)
    for k, label in enumerate(("Ready", "Pending", "Pending", "Ready")):
        out += rect(x + 30 + 96 * k, y + 142, 84, 26, "#e8f5e9" if label == "Ready" else CREAM, rx=13)
        out += text(x + 72 + 96 * k, y + 161, label, 14, TEAL if label == "Ready" else STEEL, anchor="middle", family="Menlo, monospace")
    return out


def machine_drill(x, y):
    """A drill press over a workpiece stamped with a problem."""
    out = rect(x + 40, y + 150, 220, 22, INK, rx=4)
    out += rect(x + 60, y - 70, 26, 222, "url(#steel)", rx=4)
    out += rect(x + 60, y - 90, 170, 60, "url(#steel)", rx=8) + rivets(x + 60, y - 90, 170, 60)
    out += text(x + 150, y - 52, "DRILL", 22, INK, anchor="middle", spacing=3)
    out += rect(x + 170, y - 30, 30, 50, STEEL, rx=3) + '<path d="M %.1f %.1f h 12 l -6 34 z" fill="%s" stroke="%s" stroke-width="2"/>' % (x + 179, y + 20, STEEL_LIGHT, INK)
    out += line(x + 230, y - 60, x + 290, y - 90, INK, 6) + circle(x + 294, y - 92, 9, RUST)
    out += rect(x + 120, y + 80, 150, 60, "url(#brass)", rx=3)
    out += text(x + 195, y + 118, "O(n log n)", 18, INK, anchor="middle", family="Menlo, monospace")
    out += rect(x + 300, y + 10, 110, 140, CREAM, rx=4)
    for k in range(5):
        out += rect(x + 314, y + 26 + 24 * k, 14, 14, "#e8f5e9", TEAL, 2, rx=2)
        out += line(x + 336, y + 33 + 24 * k, x + 398, y + 33 + 24 * k, STEEL, 2)
        out += '<path d="M %.1f %.1f l 3 4 l 7 -9" fill="none" stroke="%s" stroke-width="2.5"/>' % (x + 316, y + 33 + 24 * k, TEAL)
    return out


def machine_book(x, y):
    """An open manual on a lectern, for the appendices."""
    out = '<path d="M %.1f %.1f l 150 -20 l 150 20 v 130 l -150 -20 l -150 20 z" fill="%s" stroke="%s" stroke-width="3"/>' % (x + 40, y - 20, CREAM, INK)
    out += line(x + 190, y - 40, x + 190, y + 90, INK, 3)
    for k in range(6):
        out += line(x + 60, y + 4 + 14 * k, x + 170, y - 8 + 14 * k, STEEL, 2)
        out += line(x + 210, y - 8 + 14 * k, x + 320, y + 4 + 14 * k, STEEL, 2)
    out += rect(x + 150, y + 110, 80, 60, "url(#steel)", rx=3)
    out += gear(x + 370, y + 40, 40, 12, "url(#brass)")
    return out


# ------------------------------------------------------------------- plates


CHAPTERS = [
    # number, machine, robot options, name, trade
    (1, machine_types, dict(head="box", eyes="goggles", antenna="bolt", held="clipboard"), "RIVET", "the inspector who rejects bad parts at the gate"),
    (2, machine_files, dict(head="tall", eyes="round", antenna="dish", held="flag", accent=TEAL), "LEDGER", "keeper of the file room"),
    (3, machine_arrays, dict(head="tv", eyes="screen", antenna="twin", held="magnifier"), "BINS", "stockroom clerk, finds any part in one look"),
    (4, machine_chain, dict(head="dome", eyes="mono", antenna="spring", held="hammer", accent=BRASS), "SHACKLE", "chain-smith, splices links without dropping one"),
    (5, machine_merge, dict(head="box", eyes="visor", antenna="bolt", held="wrench", accent=TEAL), "CONVEYOR", "runs the merge line, ten shifts and counting"),
    (6, machine_tree, dict(head="tall", eyes="goggles", antenna="twin", held="screwdriver"), "BRANCH", "pipefitter of the manifold"),
    (7, machine_graph, dict(head="tv", eyes="visor", antenna="dish", held="flag", accent=TEAL), "VALVE", "plumber of shortest paths"),
    (8, machine_recursion, dict(head="dome", eyes="round", antenna="spring", held="oilcan", accent=BRASS), "COG", "keeps a notebook so no gear turns twice"),
    (9, machine_lru, dict(head="box", eyes="mono", antenna="bolt", held="clipboard", accent=RUST), "DRAWER", "quartermaster of the hot shelf"),
    (10, machine_ring, dict(head="tall", eyes="visor", antenna="hat", held="wrench", accent=TEAL), "TURNTABLE", "spins the ring, moves only what must move"),
    (11, machine_memory, dict(head="tv", eyes="goggles", antenna="spring", held="magnifier", accent=BRASS), "GAUGE", "reads the pressure of every cache line"),
    (12, machine_locks, dict(head="box", eyes="visor", antenna="twin", held="hammer"), "SPINDLE", "locksmith of the shared axle"),
    (13, machine_queue, dict(head="dome", eyes="screen", antenna="dish", held="flag", accent=TEAL), "CAROUSEL", "loads the ring, never overfills it"),
    (14, machine_pool, dict(head="tall", eyes="goggles", antenna="hat", held="clipboard", accent=BRASS), "FOREMAN", "hires the crew, sends them home cleanly"),
    (15, machine_bucket, dict(head="box", eyes="round", antenna="bolt", held="stopwatch", accent=RUST), "THROTTLE", "meters the steam, one token at a time"),
    (16, machine_network, dict(head="tv", eyes="visor", antenna="dish", held="screwdriver", accent=TEAL), "SIGNAL", "lineman of the socket panel"),
    (17, machine_http, dict(head="dome", eyes="mono", antenna="bolt", held="clipboard", accent=BRASS), "COURIER", "reads every header before opening the parcel"),
    (18, machine_async, dict(head="tall", eyes="screen", antenna="spring", held="oilcan", accent=RUST), "FLYWHEEL", "polls every future, sleeps when none are ready"),
    (19, machine_drill, dict(head="box", eyes="goggles", antenna="hat", held="stopwatch", accent=RUST), "DRILL", "sergeant of the timed round"),
]

APPENDICES = [
    ("a", dict(head="dome", eyes="goggles", antenna="twin", held="clipboard", accent=TEAL), "MANUAL", "the reference shelf"),
    ("b", dict(head="tv", eyes="round", antenna="bolt", held="flag", accent=RUST), "DISPATCH", "the morning of the interview"),
]


def plate(label: str, machine, options: dict, name: str, trade: str) -> str:
    width, height = 1000, 320
    body = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">' % (width, height, width, height),
        defs(),
        rect(0, 0, width, height, PAPER, "none", 0, rx=0),
        rect(0, 0, width, height, "url(#grid)", "none", 0, rx=0),
        gear(930, 40, 70, 14, "none", hole=None, stroke="#c9d4de", width=3),
        gear(40, 300, 50, 12, "none", hole=None, stroke="#c9d4de", width=3),
        rect(0, 288, width, 32, INK, "none", 0, rx=0),
        rect(0, 284, width, 4, RUST, "none", 0, rx=0),
        text(24, 311, "CHAPTER" if label.isdigit() else "APPENDIX", 18, STEEL_LIGHT, spacing=4),
        text(width - 24, 311, "%s &#183; %s" % (name, trade.upper()), 15, CREAM, anchor="end", spacing=1.5),
        text(150, 311, label.upper().zfill(2) if label.isdigit() else label.upper(), 22, "#f6d36b", spacing=2),
        robot(170, 270, 0.88, **options),
        machine(470, 110),
    ]
    body.append("</svg>")
    return "\n".join(body)


def cover() -> str:
    """The front cover: a title block over a framed engraving of the chief mechanic."""
    w, h = 1400, 1750
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">' % (w, h, w, h), defs()]
    out.append(rect(0, 0, w, h, "#f1e9d8", "none", 0, rx=0))
    # Title block, set flush left in the manner of the classic technical imprints.
    out.append(rect(0, 0, w, 520, "#16324f", "none", 0, rx=0))
    out.append(rect(0, 520, w, 12, RUST, "none", 0, rx=0))
    out.append(text(90, 170, "Cracking the", 92, "#f6efe0", family=SERIF, weight="bold"))
    out.append(text(90, 280, "Systems Programming", 92, "#f6efe0", family=SERIF, weight="bold"))
    out.append(text(90, 390, "Interview", 92, "#f6d36b", family=SERIF, weight="bold"))
    out.append(text(92, 460, "Rust from data structures to the kernel boundary", 38, "#c7d6e6", family=SERIF, extra='font-style="italic"'))
    # The engraving frame.
    fx, fy, fw, fh = 140, 600, 1120, 950
    out.append(rect(fx - 14, fy - 14, fw + 28, fh + 28, "none", INK, 3, rx=0))
    out.append(rect(fx, fy, fw, fh, "#f7f1e3", INK, 5, rx=0))
    out.append(rect(fx, fy, fw, fh, "url(#hatch-fine)", "none", 0, rx=0))
    # Background machinery: a boiler, a flywheel, gears, and a gantry.
    out.append(gear(fx + 250, fy + 260, 150, 22, "#e9dcc2", hole="#f7f1e3", width=4, rotate=4))
    out.append(gear(fx + 250, fy + 260, 150, 22, "url(#hatch)", hole=None, width=0, rotate=4))
    out.append(gear(fx + 440, fy + 150, 80, 14, "#dfc9a0", hole="#f7f1e3", width=3, rotate=9))
    out.append(gear(fx + 880, fy + 250, 120, 18, "#e9dcc2", hole="#f7f1e3", width=4, rotate=2))
    out.append(gear(fx + 880, fy + 250, 120, 18, "url(#hatch)", hole=None, width=0, rotate=2))
    out.append(gear(fx + 1010, fy + 120, 60, 12, "#dfc9a0", hole="#f7f1e3", width=3))
    out.append(rect(fx + 40, fy + 60, 20, fh - 60, "url(#hatch)", INK, 3, rx=0))
    out.append(rect(fx + fw - 60, fy + 60, 20, fh - 60, "url(#hatch)", INK, 3, rx=0))
    out.append(rect(fx + 40, fy + 50, fw - 80, 24, "#d9c7a4", INK, 3, rx=0))
    out.append(line(fx + 700, fy + 74, fx + 700, fy + 210, INK, 4))
    out.append('<path d="M %.1f %.1f q 0 30 -24 30 q -18 0 -18 -16" fill="none" stroke="%s" stroke-width="7"/>' % (fx + 700, fy + 210, INK))
    for k in range(4):
        out.append('<rect x="%.1f" y="%.1f" width="26" height="46" rx="13" fill="none" stroke="%s" stroke-width="7"/>' % (
            fx + 671 + (8 if k % 2 else 0), fy + 232 + 40 * k, INK))
    out.append(rect(fx + 630, fy + 400, 110, 70, "url(#brass)", INK, 4, rx=4))
    out.append(text(fx + 685, fy + 446, "unsafe", 26, INK, family="Menlo, monospace", anchor="middle"))
    out.append(rect(fx, fy + fh - 120, fw, 120, "#d9c7a4", INK, 4, rx=0))
    out.append(rect(fx, fy + fh - 120, fw, 120, "url(#hatch)", "none", 0, rx=0))
    # Crates of the trade on the floor.
    for k, label in enumerate(("Arc", "Mutex", "epoll", "Box")):
        bx = fx + 700 + 110 * (k % 2) + (40 if k > 1 else 0)
        by = fy + fh - 220 - (100 if k > 1 else 0)
        out.append(rect(bx, by, 100, 100, "#e2cf9f", INK, 3, rx=2))
        out.append(line(bx, by, bx + 100, by + 100, INK, 1.5) + line(bx + 100, by, bx, by + 100, INK, 1.5))
        out.append(rect(bx + 14, by + 36, 72, 28, "#f7f1e3", INK, 2, rx=2))
        out.append(text(bx + 50, by + 57, label, 22, INK, family="Menlo, monospace", anchor="middle"))
    # The chief mechanic.
    out.append(robot(fx + 380, fy + fh - 110, 2.25, head="box", eyes="goggles", antenna="bolt",
                     body="url(#steel)", accent=RUST, held="wrench", badge="&amp;mut"))
    out.append(text(fx + fw / 2, fy + fh + 64, "Chief Mechanic of the Ferrous Works, Borrow-Checker Division", 30, INK,
                    family=SERIF, anchor="middle", extra='font-style="italic"'))
    out.append(text(90, h - 70, "Arpan Pathak", 48, INK, family=SERIF, weight="bold"))
    out.append(rect(w - 380, h - 120, 290, 68, INK, "none", 0, rx=4))
    out.append(text(w - 235, h - 74, "IN RUST", 34, "#f6d36b", anchor="middle", spacing=8))
    out.append("</svg>")
    return "\n".join(out)


def rasterise(svg: pathlib.Path, width: int) -> None:
    png = svg.with_suffix(".png")
    subprocess.run(["rsvg-convert", "-w", str(width), "-o", str(png), str(svg)], check=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if shutil.which("rsvg-convert") is None:
        raise SystemExit("rsvg-convert is required: brew install librsvg")

    target = OUT / "cover.svg"
    target.write_text(cover(), encoding="utf-8")
    rasterise(target, 1400)

    for number, machine, options, name, trade in CHAPTERS:
        target = OUT / ("ch%02d.svg" % number)
        target.write_text(plate(str(number), machine, options, name, trade), encoding="utf-8")
        rasterise(target, 2000)

    for letter, options, name, trade in APPENDICES:
        target = OUT / ("app-%s.svg" % letter)
        target.write_text(plate(letter, machine_book, options, name, trade), encoding="utf-8")
        rasterise(target, 2000)

    print("wrote %d plates to %s" % (len(CHAPTERS) + len(APPENDICES) + 1, OUT.relative_to(ROOT)))


if __name__ == "__main__":
    main()
