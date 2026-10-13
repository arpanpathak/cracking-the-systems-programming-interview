#!/usr/bin/env python3
"""Draw the cover and the chapter-opener plates.

Each plate has an animal at work on the chapter's subject. The SVG is written to
src/art/, with a JSON file of the descriptions that the chapters use as
alternative text.

    python3 tools/art.py              # every plate
    python3 tools/art.py ch03 cover   # some of them
"""

import json
import math
import sys
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).resolve().parent.parent / "src" / "art"
W, H = 960, 420
GROUND = 322

INK, SNOW, CREAM = "#1b2430", "#ffffff", "#f6efe0"
RUST, BRASS, TEAL, STEEL, WOOD = "#d9622b", "#c89b3c", "#2f7f86", "#5b6b7c", "#8a6a44"
SANS = "Avenir Next Condensed, Avenir Next, Helvetica Neue, Arial, sans-serif"
MONO = "JetBrains Mono, SF Mono, Menlo, Consolas, monospace"

PLATES = {}


def plate(name, title, crew, description, size=(W, H)):
    """Registers a function that returns the parts of one plate."""

    def register(draw):
        PLATES[name] = (title, crew, description, draw, size)

        return draw

    return register


# ---------------------------------------------------------------- primitives

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
    return ellipse(cx, base + 3, rx, rx * 0.11, "#0d1a28", 'opacity="0.22"')


def eye(cx, cy, r, look=0.0, pupil=0.52):
    return "\n".join([circle(cx, cy, r, SNOW), circle(cx + look * r * 0.32, cy + r * 0.06, r * pupil, INK),
                      circle(cx + look * r * 0.32 + r * 0.18, cy - r * 0.16, r * 0.16, SNOW)])


# ------------------------------------------------------------------ the crew

def penguin(cx, base=GROUND, s=1.0, look=0.0, left=18, right=-18, scarf=None, hat=None, asleep=False):
    """Tux. `s` scales it; 1.0 is 190 units tall. `left` and `right` are flipper angles."""
    h = 190 * s
    y = lambda f: base - f * h
    parts = [
        shadow(cx, base, 0.36 * h),
        ellipse(cx - 0.13 * h, y(0.02), 0.11 * h, 0.04 * h, "#f2a23a"), ellipse(cx + 0.13 * h, y(0.02), 0.11 * h, 0.04 * h, "#f2a23a"),
        ellipse(cx - 0.29 * h, y(0.46), 0.065 * h, 0.21 * h, INK, rot(left, cx - 0.27 * h, y(0.62))),
        ellipse(cx + 0.29 * h, y(0.46), 0.065 * h, 0.21 * h, INK, rot(right, cx + 0.27 * h, y(0.62))),
        ellipse(cx, y(0.40), 0.30 * h, 0.39 * h, INK), ellipse(cx, y(0.35), 0.21 * h, 0.30 * h, "#fbfbf7"),
        circle(cx, y(0.80), 0.20 * h, INK),
        ellipse(cx - 0.075 * h, y(0.80), 0.085 * h, 0.10 * h, "#fbfbf7"), ellipse(cx + 0.075 * h, y(0.80), 0.085 * h, 0.10 * h, "#fbfbf7"),
    ]

    for side in (-1, 1):
        ex = cx + side * 0.07 * h

        if asleep:
            parts.append(path(f"M{ex - 0.03 * h:.1f},{y(0.80):.1f} q{0.03 * h:.1f},{0.03 * h:.1f} {0.06 * h:.1f},0", stroke=INK, sw=2.4 * s + 1))
        else:
            parts += [circle(ex + look * 0.022 * h, y(0.80), 0.030 * h, INK), circle(ex + look * 0.022 * h + 0.010 * h, y(0.812), 0.009 * h, SNOW)]

    parts.append(path(f"M{cx - 0.075 * h:.1f},{y(0.725):.1f} Q{cx:.1f},{y(0.765):.1f} {cx + 0.075 * h:.1f},{y(0.725):.1f}"
                      f" Q{cx:.1f},{y(0.635):.1f} {cx - 0.075 * h:.1f},{y(0.725):.1f} Z", "#f2a23a"))

    if scarf:
        parts += [path(f"M{cx - 0.17 * h:.1f},{y(0.635):.1f} Q{cx:.1f},{y(0.575):.1f} {cx + 0.17 * h:.1f},{y(0.635):.1f}"
                       f" L{cx + 0.16 * h:.1f},{y(0.575):.1f} Q{cx:.1f},{y(0.515):.1f} {cx - 0.16 * h:.1f},{y(0.575):.1f} Z", scarf),
                  rect(cx + 0.07 * h, y(0.60), 0.07 * h, 0.16 * h, scarf, 3)]

    if hat == "hard":
        parts += [path(f"M{cx - 0.19 * h:.1f},{y(0.93):.1f} A{0.19 * h:.1f},{0.17 * h:.1f} 0 0 1 {cx + 0.19 * h:.1f},{y(0.93):.1f} Z", BRASS),
                  rect(cx - 0.23 * h, y(0.94), 0.46 * h, 0.03 * h, "#a57f2c", 3)]
    elif hat == "nightcap":
        parts += [path(f"M{cx - 0.18 * h:.1f},{y(0.93):.1f} Q{cx:.1f},{y(1.16):.1f} {cx + 0.30 * h:.1f},{y(1.02):.1f}"
                       f" Q{cx + 0.10 * h:.1f},{y(1.00):.1f} {cx + 0.18 * h:.1f},{y(0.93):.1f} Z", "#4a63c9"),
                  rect(cx - 0.20 * h, y(0.95), 0.40 * h, 0.04 * h, SNOW, 4), circle(cx + 0.31 * h, y(1.02), 0.035 * h, SNOW)]

    return "\n".join(parts)


def gopher(cx, base=GROUND, s=1.0, look=0.0, arm=0):
    """A gopher: a tall blue capsule with round ears, large eyes and 2 front teeth."""
    h, coat, tan = 180 * s, "#6ad1e3", "#e8c9a0"
    y = lambda f: base - f * h

    return "\n".join([
        shadow(cx, base, 0.36 * h),
        ellipse(cx - 0.16 * h, y(0.01), 0.10 * h, 0.04 * h, tan), ellipse(cx + 0.16 * h, y(0.01), 0.10 * h, 0.04 * h, tan),
        circle(cx - 0.27 * h, y(0.93), 0.07 * h, coat), circle(cx + 0.27 * h, y(0.93), 0.07 * h, coat),
        circle(cx - 0.27 * h, y(0.93), 0.035 * h, "#3aa3b8"), circle(cx + 0.27 * h, y(0.93), 0.035 * h, "#3aa3b8"),
        ellipse(cx - 0.34 * h, y(0.45), 0.055 * h, 0.12 * h, coat, rot(20, cx - 0.34 * h, y(0.55))),
        ellipse(cx + 0.34 * h, y(0.45), 0.055 * h, 0.12 * h, coat, rot(-20 - arm, cx + 0.34 * h, y(0.55))),
        rect(cx - 0.30 * h, y(1.0), 0.60 * h, h, coat, 0.30 * h),
        ellipse(cx, y(0.30), 0.21 * h, 0.22 * h, "#c4eef5"),
        eye(cx - 0.14 * h, y(0.76), 0.10 * h, look), eye(cx + 0.14 * h, y(0.76), 0.10 * h, look),
        ellipse(cx, y(0.60), 0.10 * h, 0.06 * h, tan), ellipse(cx, y(0.635), 0.04 * h, 0.026 * h, "#3a2a1a"),
        rect(cx - 0.036 * h, y(0.565), 0.072 * h, 0.065 * h, SNOW, 2, "#c9b9a0", 1),
        line(cx, y(0.565), cx, y(0.50), "#c9b9a0", 1),
    ])


def daemon(cx, base=GROUND, s=1.0, look=0.0):
    """A small red daemon with horns, a pointed tail and green sneakers, holding a fork."""
    h, coat = 180 * s, "#d94f3d"
    y = lambda f: base - f * h

    return "\n".join([
        shadow(cx, base, 0.34 * h),
        path(f"M{cx - 0.18 * h:.1f},{y(0.16):.1f} C{cx - 0.52 * h:.1f},{y(0.10):.1f} {cx - 0.50 * h:.1f},{y(0.48):.1f} {cx - 0.36 * h:.1f},{y(0.52):.1f}",
             stroke=coat, sw=0.055 * h),
        path(f"M{cx - 0.36 * h:.1f},{y(0.62):.1f} l{0.09 * h:.1f},{0.10 * h:.1f} l{-0.13 * h:.1f},{0.03 * h:.1f} Z", coat),
        ellipse(cx - 0.11 * h, y(0.02), 0.11 * h, 0.045 * h, "#3d8f5a"), ellipse(cx + 0.11 * h, y(0.02), 0.11 * h, 0.045 * h, "#3d8f5a"),
        ellipse(cx, y(0.32), 0.23 * h, 0.29 * h, coat), ellipse(cx, y(0.28), 0.14 * h, 0.18 * h, "#f08a6a"),
        ellipse(cx - 0.25 * h, y(0.42), 0.05 * h, 0.12 * h, coat, rot(18, cx - 0.25 * h, y(0.52))),
        ellipse(cx + 0.27 * h, y(0.46), 0.05 * h, 0.12 * h, coat, rot(-50, cx + 0.25 * h, y(0.52))),
        path(f"M{cx - 0.17 * h:.1f},{y(0.90):.1f} Q{cx - 0.30 * h:.1f},{y(1.00):.1f} {cx - 0.24 * h:.1f},{y(1.10):.1f} Q{cx - 0.14 * h:.1f},{y(1.02):.1f} {cx - 0.07 * h:.1f},{y(0.95):.1f} Z", CREAM),
        path(f"M{cx + 0.17 * h:.1f},{y(0.90):.1f} Q{cx + 0.30 * h:.1f},{y(1.00):.1f} {cx + 0.24 * h:.1f},{y(1.10):.1f} Q{cx + 0.14 * h:.1f},{y(1.02):.1f} {cx + 0.07 * h:.1f},{y(0.95):.1f} Z", CREAM),
        circle(cx, y(0.76), 0.21 * h, coat),
        eye(cx - 0.085 * h, y(0.78), 0.065 * h, look), eye(cx + 0.085 * h, y(0.78), 0.065 * h, look),
        path(f"M{cx - 0.08 * h:.1f},{y(0.67):.1f} Q{cx:.1f},{y(0.60):.1f} {cx + 0.08 * h:.1f},{y(0.67):.1f}", stroke="#7a1f14", sw=3 * s + 1),
        line(cx + 0.40 * h, y(0.02), cx + 0.40 * h, y(1.02), WOOD, 5 * s + 1),
        path(f"M{cx + 0.31 * h:.1f},{y(1.16):.1f} V{y(1.02):.1f} H{cx + 0.49 * h:.1f} V{y(1.16):.1f} M{cx + 0.40 * h:.1f},{y(1.02):.1f} V{y(1.18):.1f}",
             stroke="#aebccb", sw=5 * s + 1),
    ])


def hermit(cx, base=GROUND, s=1.0, look=0.0):
    """A hermit crab in a spiral shell."""
    h, coat = 170 * s, "#e8743b"
    y = lambda f: base - f * h
    sx, sy, r = cx - 0.12 * h, y(0.50), 0.44 * h

    return "\n".join([
        shadow(cx + 0.1 * h, base, 0.62 * h),
        *[line(cx + (0.22 + 0.13 * k) * h, y(0.16), cx + (0.30 + 0.15 * k) * h, y(0.0), "#c25a26", 6 * s + 1) for k in range(3)],
        circle(sx, sy, r, "#e3c486", f'stroke="{WOOD}" stroke-width="{3 * s + 1:.1f}"'),
        path(f"M{sx + r * 0.72:.1f},{sy:.1f} A{r * 0.72:.1f},{r * 0.72:.1f} 0 1 0 {sx:.1f},{sy + r * 0.72:.1f} A{r * 0.50:.1f},{r * 0.50:.1f} 0 1 0 {sx - r * 0.28:.1f},{sy - r * 0.06:.1f}"
             f" A{r * 0.26:.1f},{r * 0.26:.1f} 0 1 0 {sx + r * 0.10:.1f},{sy + r * 0.12:.1f}", stroke=WOOD, sw=3 * s + 1.5),
        ellipse(cx + 0.36 * h, y(0.24), 0.30 * h, 0.19 * h, coat),
        line(cx + 0.28 * h, y(0.40), cx + 0.26 * h, y(0.66), coat, 6 * s + 1), line(cx + 0.46 * h, y(0.40), cx + 0.48 * h, y(0.66), coat, 6 * s + 1),
        eye(cx + 0.26 * h, y(0.70), 0.075 * h, look), eye(cx + 0.48 * h, y(0.70), 0.075 * h, look),
        path(f"M{cx + 0.28 * h:.1f},{y(0.20):.1f} q{0.09 * h:.1f},{0.07 * h:.1f} {0.18 * h:.1f},0", stroke="#7a2f10", sw=3 * s + 1),
        circle(cx + 0.74 * h, y(0.40), 0.13 * h, coat),
        path(f"M{cx + 0.74 * h:.1f},{y(0.40):.1f} l{0.16 * h:.1f},{-0.10 * h:.1f} l{-0.02 * h:.1f},{0.16 * h:.1f} Z", "#fff3e6"),
        line(cx + 0.58 * h, y(0.28), cx + 0.68 * h, y(0.36), coat, 8 * s + 1),
    ])


def owl(cx, base=GROUND, s=1.0, look=0.0):
    h, coat = 175 * s, "#8a5a3a"
    y = lambda f: base - f * h
    belly = [path(f"M{cx + dx * h:.1f},{y(fy):.1f} l{0.03 * h:.1f},{0.03 * h:.1f} l{0.03 * h:.1f},{-0.03 * h:.1f}", stroke="#a9825c", sw=2.5)
             for dx, fy in ((-0.10, 0.36), (0.04, 0.36), (-0.03, 0.26), (-0.10, 0.16), (0.04, 0.16))]

    return "\n".join([
        shadow(cx, base, 0.34 * h),
        ellipse(cx - 0.10 * h, y(0.01), 0.07 * h, 0.03 * h, BRASS), ellipse(cx + 0.10 * h, y(0.01), 0.07 * h, 0.03 * h, BRASS),
        path(f"M{cx - 0.24 * h:.1f},{y(0.86):.1f} L{cx - 0.30 * h:.1f},{y(1.06):.1f} L{cx - 0.10 * h:.1f},{y(0.94):.1f} Z", coat),
        path(f"M{cx + 0.24 * h:.1f},{y(0.86):.1f} L{cx + 0.30 * h:.1f},{y(1.06):.1f} L{cx + 0.10 * h:.1f},{y(0.94):.1f} Z", coat),
        ellipse(cx, y(0.47), 0.30 * h, 0.47 * h, coat), ellipse(cx, y(0.28), 0.19 * h, 0.25 * h, "#e2c59c"), *belly,
        ellipse(cx - 0.30 * h, y(0.42), 0.07 * h, 0.22 * h, "#6d452b", rot(12, cx - 0.28 * h, y(0.6))),
        ellipse(cx + 0.30 * h, y(0.42), 0.07 * h, 0.22 * h, "#6d452b", rot(-12, cx + 0.28 * h, y(0.6))),
        circle(cx - 0.125 * h, y(0.72), 0.135 * h, CREAM), circle(cx + 0.125 * h, y(0.72), 0.135 * h, CREAM),
        eye(cx - 0.125 * h, y(0.72), 0.085 * h, look, 0.6), eye(cx + 0.125 * h, y(0.72), 0.085 * h, look, 0.6),
        path(f"M{cx - 0.04 * h:.1f},{y(0.66):.1f} h{0.08 * h:.1f} l{-0.04 * h:.1f},{0.08 * h:.1f} Z", BRASS),
    ])


def gnu(cx, base=GROUND, s=1.0, look=0.0):
    """A gnu in a referee's striped shirt."""
    h = 195 * s
    y = lambda f: base - f * h
    stripes = [rect(cx + dx * h - 0.025 * h, y(0.52 - abs(dx) * 0.25), 0.05 * h, (0.40 - abs(dx) * 0.55) * h, INK, 3)
               for dx in (-0.16, -0.05, 0.06, 0.17)]

    return "\n".join([
        shadow(cx, base, 0.34 * h),
        rect(cx - 0.16 * h, y(0.12), 0.11 * h, 0.12 * h, "#5a4a3c", 4), rect(cx + 0.05 * h, y(0.12), 0.11 * h, 0.12 * h, "#5a4a3c", 4),
        ellipse(cx, y(0.34), 0.27 * h, 0.27 * h, SNOW, f'stroke="{INK}" stroke-width="2"'), *stripes,
        path(f"M{cx - 0.08 * h:.1f},{y(0.96):.1f} C{cx - 0.34 * h:.1f},{y(1.00):.1f} {cx - 0.36 * h:.1f},{y(1.20):.1f} {cx - 0.16 * h:.1f},{y(1.16):.1f}",
             stroke="#e9dcc0", sw=0.05 * h),
        path(f"M{cx + 0.08 * h:.1f},{y(0.96):.1f} C{cx + 0.34 * h:.1f},{y(1.00):.1f} {cx + 0.36 * h:.1f},{y(1.20):.1f} {cx + 0.16 * h:.1f},{y(1.16):.1f}",
             stroke="#e9dcc0", sw=0.05 * h),
        ellipse(cx - 0.17 * h, y(0.88), 0.07 * h, 0.035 * h, "#6b5a4a", rot(-20, cx - 0.17 * h, y(0.88))),
        ellipse(cx + 0.17 * h, y(0.88), 0.07 * h, 0.035 * h, "#6b5a4a", rot(20, cx + 0.17 * h, y(0.88))),
        ellipse(cx, y(0.76), 0.13 * h, 0.21 * h, "#6b5a4a"), ellipse(cx, y(0.63), 0.11 * h, 0.085 * h, "#4a3d32"),
        path(f"M{cx - 0.06 * h:.1f},{y(0.55):.1f} L{cx:.1f},{y(0.44):.1f} L{cx + 0.06 * h:.1f},{y(0.55):.1f} Z", "#3a2f26"),
        eye(cx - 0.065 * h, y(0.82), 0.045 * h, look), eye(cx + 0.065 * h, y(0.82), 0.045 * h, look),
        circle(cx - 0.04 * h, y(0.64), 0.014 * h, INK), circle(cx + 0.04 * h, y(0.64), 0.014 * h, INK),
    ])


def hare(cx, base=GROUND, s=1.0, look=0.0):
    h, coat = 125 * s, "#dcd5c8"
    y = lambda f: base - f * h

    return "\n".join([
        shadow(cx, base, 0.30 * h),
        ellipse(cx - 0.06 * h, y(1.06), 0.05 * h, 0.24 * h, coat, rot(-8, cx - 0.06 * h, y(0.85))),
        ellipse(cx + 0.06 * h, y(1.06), 0.05 * h, 0.24 * h, coat, rot(10, cx + 0.06 * h, y(0.85))),
        ellipse(cx + 0.06 * h, y(1.06), 0.022 * h, 0.17 * h, "#f0b6b6", rot(10, cx + 0.06 * h, y(0.85))),
        ellipse(cx, y(0.30), 0.23 * h, 0.30 * h, coat), ellipse(cx - 0.12 * h, y(0.02), 0.13 * h, 0.05 * h, coat), ellipse(cx + 0.14 * h, y(0.02), 0.13 * h, 0.05 * h, coat),
        circle(cx, y(0.68), 0.18 * h, coat),
        eye(cx - 0.07 * h, y(0.71), 0.05 * h, look), eye(cx + 0.07 * h, y(0.71), 0.05 * h, look),
        ellipse(cx, y(0.62), 0.03 * h, 0.02 * h, "#e58a8a"),
    ])


def tortoise(cx, base=GROUND, s=1.0):
    h = 90 * s
    y = lambda f: base - f * h

    return "\n".join([
        shadow(cx, base, 0.75 * h),
        rect(cx - 0.50 * h, y(0.22), 0.20 * h, 0.24 * h, "#9ccf8a", 6), rect(cx + 0.26 * h, y(0.22), 0.20 * h, 0.24 * h, "#9ccf8a", 6),
        ellipse(cx + 0.78 * h, y(0.52), 0.20 * h, 0.16 * h, "#9ccf8a"), eye(cx + 0.84 * h, y(0.56), 0.055 * h, 1),
        path(f"M{cx - 0.66 * h:.1f},{y(0.18):.1f} A{0.66 * h:.1f},{0.74 * h:.1f} 0 0 1 {cx + 0.66 * h:.1f},{y(0.18):.1f} Z", "#4f9a63", "#356b45", 3),
        path(f"M{cx - 0.3 * h:.1f},{y(0.18):.1f} L{cx - 0.15 * h:.1f},{y(0.55):.1f} L{cx + 0.15 * h:.1f},{y(0.55):.1f} L{cx + 0.3 * h:.1f},{y(0.18):.1f}"
             f" M{cx - 0.15 * h:.1f},{y(0.55):.1f} L{cx:.1f},{y(0.86):.1f} L{cx + 0.15 * h:.1f},{y(0.55):.1f}", stroke="#356b45", sw=3),
    ])


def elephant(cx, base=GROUND, s=1.0, look=0.0):
    h, coat, dark = 200 * s, "#9aa7b5", "#8492a1"
    y = lambda f: base - f * h

    return "\n".join([
        shadow(cx, base, 0.42 * h),
        rect(cx - 0.26 * h, y(0.16), 0.17 * h, 0.16 * h, coat, 8), rect(cx + 0.09 * h, y(0.16), 0.17 * h, 0.16 * h, coat, 8),
        ellipse(cx, y(0.36), 0.33 * h, 0.30 * h, coat),
        ellipse(cx - 0.31 * h, y(0.76), 0.17 * h, 0.22 * h, dark), ellipse(cx + 0.31 * h, y(0.76), 0.17 * h, 0.22 * h, dark),
        ellipse(cx - 0.31 * h, y(0.76), 0.10 * h, 0.15 * h, "#e6b9b9"), ellipse(cx + 0.31 * h, y(0.76), 0.10 * h, 0.15 * h, "#e6b9b9"),
        circle(cx, y(0.76), 0.23 * h, coat),
        path(f"M{cx:.1f},{y(0.70):.1f} C{cx:.1f},{y(0.40):.1f} {cx + 0.10 * h:.1f},{y(0.30):.1f} {cx + 0.30 * h:.1f},{y(0.36):.1f} S{cx + 0.44 * h:.1f},{y(0.56):.1f} {cx + 0.40 * h:.1f},{y(0.62):.1f}",
             stroke=coat, sw=0.105 * h),
        path(f"M{cx - 0.09 * h:.1f},{y(0.62):.1f} q{-0.03 * h:.1f},{0.10 * h:.1f} {0.02 * h:.1f},{0.13 * h:.1f}", stroke=SNOW, sw=0.035 * h),
        path(f"M{cx + 0.09 * h:.1f},{y(0.62):.1f} q{0.03 * h:.1f},{0.10 * h:.1f} {-0.02 * h:.1f},{0.13 * h:.1f}", stroke=SNOW, sw=0.035 * h),
        eye(cx - 0.09 * h, y(0.82), 0.045 * h, look), eye(cx + 0.09 * h, y(0.82), 0.045 * h, look),
    ])


def squirrel(cx, base=GROUND, s=1.0, look=0.0):
    h, coat = 165 * s, "#c9783a"
    y = lambda f: base - f * h

    return "\n".join([
        shadow(cx - 0.1 * h, base, 0.44 * h),
        path(f"M{cx - 0.12 * h:.1f},{y(0.10):.1f} C{cx - 0.70 * h:.1f},{y(0.05):.1f} {cx - 0.78 * h:.1f},{y(0.86):.1f} {cx - 0.38 * h:.1f},{y(1.04):.1f}"
             f" C{cx - 0.12 * h:.1f},{y(1.12):.1f} {cx - 0.10 * h:.1f},{y(0.80):.1f} {cx - 0.28 * h:.1f},{y(0.72):.1f} C{cx - 0.40 * h:.1f},{y(0.60):.1f} {cx - 0.30 * h:.1f},{y(0.36):.1f} {cx - 0.12 * h:.1f},{y(0.10):.1f} Z", "#a85a26"),
        ellipse(cx - 0.11 * h, y(0.02), 0.11 * h, 0.04 * h, "#a85a26"), ellipse(cx + 0.12 * h, y(0.02), 0.11 * h, 0.04 * h, "#a85a26"),
        ellipse(cx, y(0.33), 0.22 * h, 0.31 * h, coat), ellipse(cx + 0.02 * h, y(0.28), 0.13 * h, 0.21 * h, "#f3dcc0"),
        path(f"M{cx - 0.13 * h:.1f},{y(0.86):.1f} l{-0.03 * h:.1f},{-0.14 * h:.1f} l{0.11 * h:.1f},{0.08 * h:.1f} Z", coat),
        path(f"M{cx + 0.13 * h:.1f},{y(0.86):.1f} l{0.03 * h:.1f},{-0.14 * h:.1f} l{-0.11 * h:.1f},{0.08 * h:.1f} Z", coat),
        circle(cx, y(0.74), 0.19 * h, coat), ellipse(cx, y(0.68), 0.12 * h, 0.09 * h, "#f3dcc0"),
        eye(cx - 0.08 * h, y(0.78), 0.05 * h, look), eye(cx + 0.08 * h, y(0.78), 0.05 * h, look),
        ellipse(cx, y(0.70), 0.025 * h, 0.018 * h, "#5a2e12"),
        ellipse(cx + 0.24 * h, y(0.40), 0.075 * h, 0.09 * h, "#b98444"),
        path(f"M{cx + 0.155 * h:.1f},{y(0.43):.1f} A{0.085 * h:.1f},{0.07 * h:.1f} 0 0 1 {cx + 0.325 * h:.1f},{y(0.43):.1f} Z", "#6b4a2a"),
        ellipse(cx + 0.17 * h, y(0.36), 0.045 * h, 0.09 * h, coat, rot(-60, cx + 0.17 * h, y(0.36))),
    ])


def octopus(cx, base=GROUND, s=1.0, look=0.0, reach=()):
    """An octopus. `reach` lists points that arms stretch to."""
    h, coat = 175 * s, "#8e6bd1"
    y = lambda f: base - f * h
    arms = [path(f"M{cx + dx * h:.1f},{y(0.34):.1f} C{cx + dx * 1.6 * h:.1f},{y(0.10):.1f} {cx + dx * 2.6 * h:.1f},{y(0.22):.1f} {cx + dx * 2.9 * h:.1f},{y(0.02):.1f}",
                 stroke=coat, sw=0.075 * h) for dx in (-0.20, -0.10, 0.08, 0.18)]
    arms += [path(f"M{cx + 0.2 * h:.1f},{y(0.50):.1f} C{cx + 0.6 * h:.1f},{y(0.70):.1f} {(cx + 0.2 * h + tx) / 2:.1f},{ty + 40:.1f} {tx:.1f},{ty:.1f}", stroke=coat, sw=0.06 * h)
             for tx, ty in reach]

    return "\n".join([
        shadow(cx, base, 0.6 * h), *arms,
        ellipse(cx, y(0.62), 0.30 * h, 0.34 * h, coat), ellipse(cx - 0.10 * h, y(0.80), 0.10 * h, 0.07 * h, "#a98ae0", 'opacity="0.7"'),
        eye(cx - 0.11 * h, y(0.58), 0.075 * h, look), eye(cx + 0.11 * h, y(0.58), 0.075 * h, look),
        path(f"M{cx - 0.07 * h:.1f},{y(0.44):.1f} q{0.07 * h:.1f},{0.06 * h:.1f} {0.14 * h:.1f},0", stroke="#4a3382", sw=3 * s + 1),
        path(f"M{cx - 0.30 * h:.1f},{y(0.64):.1f} A{0.30 * h:.1f},{0.36 * h:.1f} 0 0 1 {cx + 0.30 * h:.1f},{y(0.64):.1f}", stroke=STEEL, sw=6 * s),
        rect(cx - 0.36 * h, y(0.68), 0.09 * h, 0.16 * h, STEEL, 6), rect(cx + 0.27 * h, y(0.68), 0.09 * h, 0.16 * h, STEEL, 6),
    ])


def pigeon(cx, base=GROUND, s=1.0, face=1):
    """A carrier pigeon facing right (`face` 1) or left (-1), with a note on its leg."""
    h, coat = 120 * s, "#9aa7b5"
    y = lambda f: base - f * h
    x = lambda f: cx + face * f * h

    return "\n".join([
        shadow(cx, base, 0.42 * h),
        line(x(-0.04), y(0.14), x(-0.04), y(0.0), "#e58a5a", 4), line(x(0.10), y(0.14), x(0.10), y(0.0), "#e58a5a", 4),
        rect(x(0.10) - 9, y(0.10), 18, 14, CREAM, 3, WOOD, 1.5),
        path(f"M{x(-0.30):.1f},{y(0.40):.1f} L{x(-0.62):.1f},{y(0.22):.1f} L{x(-0.36):.1f},{y(0.24):.1f} Z", "#7d8a98"),
        ellipse(cx, y(0.40), 0.36 * h, 0.27 * h, coat), ellipse(x(-0.06), y(0.42), 0.22 * h, 0.15 * h, "#7d8a98", rot(-face * 12, x(-0.06), y(0.42))),
        ellipse(x(0.24), y(0.60), 0.11 * h, 0.14 * h, "#5fb0a0"), circle(x(0.28), y(0.80), 0.15 * h, coat),
        eye(x(0.32), y(0.83), 0.05 * h, face), path(f"M{x(0.41):.1f},{y(0.80):.1f} L{x(0.56):.1f},{y(0.76):.1f} L{x(0.41):.1f},{y(0.72):.1f} Z", BRASS),
    ])


def cat(cx, base, s=1.0, fur="#f0a35a", look=0.0, number="1"):
    """A cat sitting in a cardboard box that carries a number."""
    h = 150 * s
    y = lambda f: base - f * h
    whiskers = [line(cx + side * 0.07 * h, y(0.66 - 0.02 * k), cx + side * 0.26 * h, y(0.69 - 0.05 * k), "#5a4a3c", 1.6) for side in (-1, 1) for k in range(2)]

    return "\n".join([
        shadow(cx, base, 0.50 * h),
        path(f"M{cx - 0.16 * h:.1f},{y(0.86):.1f} l{-0.03 * h:.1f},{-0.17 * h:.1f} l{0.13 * h:.1f},{0.09 * h:.1f} Z", fur),
        path(f"M{cx + 0.16 * h:.1f},{y(0.86):.1f} l{0.03 * h:.1f},{-0.17 * h:.1f} l{-0.13 * h:.1f},{0.09 * h:.1f} Z", fur),
        circle(cx, y(0.72), 0.20 * h, fur),
        ellipse(cx - 0.08 * h, y(0.75), 0.04 * h, 0.05 * h, "#bfe37a"), ellipse(cx + 0.08 * h, y(0.75), 0.04 * h, 0.05 * h, "#bfe37a"),
        ellipse(cx - 0.08 * h + look * 0.01 * h, y(0.75), 0.014 * h, 0.045 * h, INK), ellipse(cx + 0.08 * h + look * 0.01 * h, y(0.75), 0.014 * h, 0.045 * h, INK),
        path(f"M{cx - 0.025 * h:.1f},{y(0.68):.1f} h{0.05 * h:.1f} l{-0.025 * h:.1f},{0.03 * h:.1f} Z", "#e58a8a"), *whiskers,
        path(f"M{cx - 0.44 * h:.1f},{y(0.52):.1f} l{-0.10 * h:.1f},{-0.10 * h:.1f} M{cx + 0.44 * h:.1f},{y(0.52):.1f} l{0.10 * h:.1f},{-0.10 * h:.1f}", stroke="#b08a54", sw=8 * s + 2),
        rect(cx - 0.44 * h, y(0.52), 0.88 * h, 0.52 * h, "#d2a868", 4, "#8a6a44", 2.5),
        ellipse(cx - 0.14 * h, y(0.52), 0.06 * h, 0.035 * h, fur), ellipse(cx + 0.14 * h, y(0.52), 0.06 * h, 0.035 * h, fur),
        circle(cx, y(0.26), 0.13 * h, RUST), label(cx, y(0.26) + 0.05 * h, "#" + number, 0.14 * h, font=MONO),
    ])


def beaver(cx, base=GROUND, s=1.0, look=0.0):
    h, coat = 170 * s, "#8a5a3a"
    y = lambda f: base - f * h

    return "\n".join([
        shadow(cx - 0.1 * h, base, 0.48 * h),
        ellipse(cx - 0.36 * h, y(0.07), 0.24 * h, 0.075 * h, "#5a3d28"),
        path(f"M{cx - 0.54 * h:.1f},{y(0.07):.1f} h{0.30 * h:.1f} M{cx - 0.46 * h:.1f},{y(0.12):.1f} l{0.14 * h:.1f},{0.10 * h:.1f} M{cx - 0.32 * h:.1f},{y(0.12):.1f} l{-0.14 * h:.1f},{0.10 * h:.1f}", stroke="#3e2a1b", sw=2),
        ellipse(cx - 0.11 * h, y(0.02), 0.11 * h, 0.04 * h, "#5a3d28"), ellipse(cx + 0.12 * h, y(0.02), 0.11 * h, 0.04 * h, "#5a3d28"),
        ellipse(cx, y(0.34), 0.25 * h, 0.33 * h, coat), ellipse(cx, y(0.28), 0.15 * h, 0.22 * h, "#d9b48a"),
        ellipse(cx - 0.27 * h, y(0.42), 0.055 * h, 0.12 * h, coat, rot(18, cx - 0.27 * h, y(0.5))),
        ellipse(cx + 0.27 * h, y(0.44), 0.055 * h, 0.12 * h, coat, rot(-48, cx + 0.25 * h, y(0.5))),
        circle(cx - 0.15 * h, y(0.90), 0.05 * h, coat), circle(cx + 0.15 * h, y(0.90), 0.05 * h, coat),
        circle(cx, y(0.76), 0.20 * h, coat), ellipse(cx, y(0.68), 0.12 * h, 0.085 * h, "#d9b48a"),
        eye(cx - 0.08 * h, y(0.80), 0.05 * h, look), eye(cx + 0.08 * h, y(0.80), 0.05 * h, look),
        ellipse(cx, y(0.72), 0.035 * h, 0.022 * h, "#3e2a1b"),
        rect(cx - 0.04 * h, y(0.675), 0.08 * h, 0.085 * h, SNOW, 2, "#c9b9a0", 1), line(cx, y(0.675), cx, y(0.59), "#c9b9a0", 1),
        path(f"M{cx - 0.19 * h:.1f},{y(0.89):.1f} A{0.19 * h:.1f},{0.16 * h:.1f} 0 0 1 {cx + 0.19 * h:.1f},{y(0.89):.1f} Z", BRASS),
        rect(cx - 0.23 * h, y(0.90), 0.46 * h, 0.03 * h, "#a57f2c", 3),
    ])


def whale(cx, cy, s=1.0):
    """A blue whale seen from the side, facing left, with a flat back."""
    w = 330 * s
    x = lambda f: cx + f * w
    y = lambda f: cy + f * w

    return "\n".join([
        path(f"M{x(0.44):.1f},{y(-0.02):.1f} C{x(0.56):.1f},{y(-0.20):.1f} {x(0.66):.1f},{y(-0.22):.1f} {x(0.70):.1f},{y(-0.26):.1f}"
             f" C{x(0.66):.1f},{y(-0.10):.1f} {x(0.72):.1f},{y(-0.02):.1f} {x(0.76):.1f},{y(0.06):.1f} C{x(0.64):.1f},{y(0.04):.1f} {x(0.54):.1f},{y(0.08):.1f} {x(0.44):.1f},{y(0.14):.1f} Z", "#2f78ad"),
        path(f"M{x(-0.50):.1f},{y(0.02):.1f} C{x(-0.50):.1f},{y(-0.16):.1f} {x(-0.30):.1f},{y(-0.20):.1f} {x(0.0):.1f},{y(-0.20):.1f} S{x(0.42):.1f},{y(-0.12):.1f} {x(0.50):.1f},{y(0.04):.1f}"
             f" C{x(0.36):.1f},{y(0.20):.1f} {x(0.0):.1f},{y(0.24):.1f} {x(-0.30):.1f},{y(0.20):.1f} S{x(-0.50):.1f},{y(0.12):.1f} {x(-0.50):.1f},{y(0.02):.1f} Z", "#3c8dc5"),
        path(f"M{x(-0.48):.1f},{y(0.08):.1f} C{x(-0.30):.1f},{y(0.14):.1f} {x(0.10):.1f},{y(0.16):.1f} {x(0.40):.1f},{y(0.10):.1f}"
             f" C{x(0.20):.1f},{y(0.24):.1f} {x(-0.30):.1f},{y(0.24):.1f} {x(-0.48):.1f},{y(0.08):.1f} Z", "#cfe6f5"),
        eye(x(-0.34), y(-0.03), 0.035 * w, -1),
        path(f"M{x(-0.48):.1f},{y(0.05):.1f} q{0.08 * w:.1f},{0.05 * w:.1f} {0.16 * w:.1f},{0.02 * w:.1f}", stroke="#1f5a85", sw=3),
        path(f"M{x(-0.20):.1f},{y(-0.21):.1f} q{-0.03 * w:.1f},{-0.13 * w:.1f} {-0.10 * w:.1f},{-0.14 * w:.1f} M{x(-0.20):.1f},{y(-0.21):.1f} q{0.03 * w:.1f},{-0.13 * w:.1f} {0.10 * w:.1f},{-0.14 * w:.1f}",
             stroke="#bfe3f7", sw=6 * s),
    ])


def crab(cx, base=GROUND, s=1.0, mood="happy", look=0.0, shade=True):
    """A crab in the orange of Rust, in one of 5 moods: happy, cute, angry, sleepy or shocked."""
    h, coat, dark = 120 * s, "#f46a35", "#c2441a"
    y = lambda f: base - f * h
    up = 0.98 if mood in ("happy", "angry", "shocked") else 0.70
    parts = [shadow(cx, base, 0.62 * h)] if shade else []
    parts += [line(cx + side * (0.30 + 0.12 * k) * h, y(0.24), cx + side * (0.44 + 0.16 * k) * h, y(0.0), dark, 5 * s + 1.5)
              for side in (-1, 1) for k in range(3)]

    for side in (-1, 1):
        tip = (cx + side * 0.80 * h, y(up))
        parts += [path(f"M{cx + side * 0.46 * h:.1f},{y(0.46):.1f} Q{cx + side * 0.80 * h:.1f},{y(0.44):.1f} {tip[0]:.1f},{tip[1] + 0.10 * h:.1f}", stroke=coat, sw=0.09 * h),
                  circle(tip[0], tip[1], 0.15 * h, coat),
                  path(f"M{tip[0]:.1f},{tip[1]:.1f} l{side * 0.02 * h:.1f},{-0.19 * h:.1f} l{-side * 0.13 * h:.1f},{0.08 * h:.1f} Z", "#fff1e6")]

    parts += [
        path(f"M{cx - 0.56 * h:.1f},{y(0.40):.1f} L{cx - 0.50 * h:.1f},{y(0.70):.1f} L{cx - 0.34 * h:.1f},{y(0.66):.1f} L{cx - 0.22 * h:.1f},{y(0.82):.1f}"
             f" L{cx:.1f},{y(0.74):.1f} L{cx + 0.22 * h:.1f},{y(0.82):.1f} L{cx + 0.34 * h:.1f},{y(0.66):.1f} L{cx + 0.50 * h:.1f},{y(0.70):.1f} L{cx + 0.56 * h:.1f},{y(0.40):.1f} Z", coat),
        ellipse(cx, y(0.38), 0.58 * h, 0.30 * h, coat),
        ellipse(cx, y(0.24), 0.36 * h, 0.12 * h, "#ffb08a", 'opacity="0.55"'),
    ]

    for side in (-1, 1):
        ex, ey = cx + side * 0.17 * h, y(0.50)

        if mood == "sleepy":
            parts.append(path(f"M{ex - 0.08 * h:.1f},{ey:.1f} q{0.08 * h:.1f},{0.07 * h:.1f} {0.16 * h:.1f},0", stroke=INK, sw=3 * s + 1.5))
            continue

        parts.append(ellipse(ex, ey, 0.10 * h, 0.13 * h, SNOW))
        size = {"cute": 0.085, "shocked": 0.035}.get(mood, 0.055) * h
        parts += [circle(ex + look * 0.03 * h, ey + 0.01 * h, size, INK), circle(ex + look * 0.03 * h + size * 0.35, ey - size * 0.3, size * 0.32, SNOW)]

        if mood == "cute":
            parts += [circle(ex + look * 0.03 * h - size * 0.3, ey + size * 0.4, size * 0.18, SNOW), ellipse(ex + side * 0.16 * h, y(0.34), 0.07 * h, 0.04 * h, "#ff9aa8", 'opacity="0.8"')]

        if mood == "angry":
            parts.append(line(ex - side * 0.12 * h, y(0.62), ex + side * 0.10 * h, y(0.70), INK, 4 * s + 1.5))

    mouth = {
        "happy": path(f"M{cx - 0.12 * h:.1f},{y(0.30):.1f} Q{cx:.1f},{y(0.12):.1f} {cx + 0.12 * h:.1f},{y(0.30):.1f} Z", "#7a1f0a"),
        "cute": path(f"M{cx - 0.07 * h:.1f},{y(0.30):.1f} q{0.035 * h:.1f},{0.05 * h:.1f} {0.07 * h:.1f},0 q{0.035 * h:.1f},{0.05 * h:.1f} {0.07 * h:.1f},0", stroke="#7a1f0a", sw=2.5 * s + 1),
        "angry": path(f"M{cx - 0.11 * h:.1f},{y(0.22):.1f} Q{cx:.1f},{y(0.34):.1f} {cx + 0.11 * h:.1f},{y(0.22):.1f}", stroke="#7a1f0a", sw=3 * s + 1.5),
        "sleepy": ellipse(cx, y(0.27), 0.035 * h, 0.03 * h, "#7a1f0a"),
        "shocked": ellipse(cx, y(0.25), 0.06 * h, 0.08 * h, "#7a1f0a"),
    }[mood]
    parts.append(mouth)

    if mood == "angry":
        parts += [path(f"M{cx + side * 0.50 * h:.1f},{y(1.02):.1f} q{side * 0.06 * h:.1f},{-0.10 * h:.1f} 0,{-0.18 * h:.1f}", stroke="#ffd9c7", sw=3 * s + 1) for side in (-1, 1)]

    if mood == "sleepy":
        parts += [label(cx + (0.46 + 0.14 * k) * h, y(0.86 + 0.16 * k), "z", (14 + 6 * k) * s + 4, "#cfe1f0", weight=800) for k in range(3)]

    return "\n".join(parts)


def builder_crab(cx, base):
    """A crab in a hard hat, in tears over a column of sums."""
    h = 120
    y = lambda f: base - f * h
    tear = lambda x, top: path(f"M{x:.1f},{top:.1f} q{-7},{14} 0,{20} q{7},{-6} 0,{-20} Z", "#6ec6ff")

    return "\n".join([
        crab(cx, base, 1.0, "sleepy", shade=False).replace(">z<", "><"),
        path(f"M{cx - 0.13 * h:.1f},{y(0.24):.1f} Q{cx:.1f},{y(0.36):.1f} {cx + 0.13 * h:.1f},{y(0.24):.1f}", stroke="#7a1f0a", sw=4.5),
        ellipse(cx, y(0.27), 0.05 * h, 0.04 * h, "#f46a35"),
        tear(cx - 0.17 * h, y(0.44)), tear(cx + 0.17 * h, y(0.44)), tear(cx - 0.25 * h, y(0.36)), tear(cx + 0.25 * h, y(0.36)),
        path(f"M{cx - 0.36 * h:.1f},{y(0.70):.1f} A{0.36 * h:.1f},{0.32 * h:.1f} 0 0 1 {cx + 0.36 * h:.1f},{y(0.70):.1f} Z", "#f2b632", "#a57f2c", 3),
        rect(cx - 0.44 * h, y(0.72), 0.88 * h, 0.07 * h, "#d99a1c", 4, "#a57f2c", 2),
        rect(cx - 0.03 * h, y(1.0), 0.06 * h, 0.27 * h, "#d99a1c", 3),
    ])


def box(x, y, w, h, fill, text="", ink=SNOW):
    """A shipping container."""
    ribs = [line(x + w * k / 8, y + 5, x + w * k / 8, y + h - 5, "#00000033", 2) for k in range(1, 8)]

    return "\n".join([rect(x, y, w, h, fill, 4, "#00000055", 2), *ribs, label(x + w / 2, y + h / 2 + 7, text, 19, ink, font=MONO)])


# ----------------------------------------------------------------- background

def backdrop(sky=("#12263d", "#2c5c86"), ground=("#c5d8e6", "#e8f1f7"), seed=0, size=(W, H), stars=True):
    """A sky with stars and a band of light, over ground of 2 tones."""
    width, height = size
    base = height - (H - GROUND)
    dots = [circle((k * 197 + seed * 53) % width, (k * 89 + seed * 31) % (base - 130) + 12, 1.1 + (k % 3) * 0.6, SNOW,
                   f'opacity="{0.35 + (k % 4) * 0.15:.2f}"') for k in range(46 if stars else 0)]

    return "\n".join([
        f'<defs><linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{sky[0]}"/>'
        f'<stop offset="1" stop-color="{sky[1]}"/></linearGradient>'
        '<linearGradient id="glow" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#3fd6a8" stop-opacity="0"/>'
        '<stop offset="0.5" stop-color="#3fd6a8" stop-opacity="0.30"/><stop offset="1" stop-color="#7aa6ff" stop-opacity="0"/>'
        '</linearGradient></defs>',
        rect(0, 0, width, height, "url(#sky)"),
        path(f"M0,{120 + seed % 3 * 12} C240,{40 + seed % 5 * 8} 520,{190 - seed % 4 * 10} {width},{80 + seed % 3 * 14} L{width},{150 + seed % 3 * 14}"
             f" C520,{250 - seed % 4 * 10} 240,{110 + seed % 5 * 8} 0,{190 + seed % 3 * 12} Z", "url(#glow)"),
        *dots,
        path(f"M0,{base - 26} C200,{base - 52} 420,{base - 8} 640,{base - 34} S900,{base - 20} {width},{base - 40} L{width},{height} L0,{height} Z", ground[0]),
        path(f"M0,{base - 6} C260,{base - 26} 520,{base + 8} {width},{base - 14} L{width},{height} L0,{height} Z", ground[1]),
    ])


ICE = dict(ground=("#c5d8e6", "#e8f1f7"))
MEADOW = dict(sky=("#17324a", "#3f7f8f"), ground=("#5f9a62", "#86bd7c"))
SAND = dict(sky=("#1d2f4d", "#b7684a"), ground=("#d6b47c", "#ecd4a4"))
FOREST = dict(sky=("#13283a", "#2f5f55"), ground=("#4a7a4c", "#6fa268"))
FLOOR = dict(sky=("#1b2738", "#3b4f6b"), ground=("#8a7a66", "#b3a48f"), stars=False)
SEA = dict(sky=("#102a44", "#2f6f9a"), ground=("#1f5a85", "#2c79ad"))


def ribbon(number, title, crew, size=(W, H)):
    """The plate's caption: the chapter and the name of the character."""
    height = size[1]
    wide = 44 + 16.6 * len(title)

    return "\n".join([
        rect(28, height - 60, 96, 40, RUST, 6), label(76, height - 32, number, 22),
        rect(118, height - 60, wide, 40, "#12263d", 6), label(136, height - 32, title.upper(), 22, anchor="start", extra='letter-spacing="1.5"'),
        rect(size[0] - 46 - 10.5 * len(crew), height - 56, 22 + 10.5 * len(crew), 32, "#ffffffcc", 16),
        label(size[0] - 36, height - 34, crew, 17, "#27405a", "end", weight=600),
    ])


def pipe(x1, y, x2, r=22):
    return "\n".join([rect(x1, y - r, x2 - x1, 2 * r, STEEL, 4), rect(x1, y - r, x2 - x1, r * 0.55, "#8fa0b1", 4),
                      rect(x1 - 8, y - r - 6, 16, 2 * r + 12, "#44525f", 3), rect(x2 - 8, y - r - 6, 16, 2 * r + 12, "#44525f", 3)])


def byte(x, y, text, fill="#e8c877"):
    return rect(x - 15, y - 15, 30, 30, fill, 6) + label(x, y + 7, text, 17, "#12263d", font=MONO)


def flame(cx, base, s=1.0):
    return "\n".join([
        path(f"M{cx - 44 * s:.1f},{base:.1f} C{cx - 70 * s:.1f},{base - 60 * s:.1f} {cx - 16 * s:.1f},{base - 70 * s:.1f} {cx - 24 * s:.1f},{base - 128 * s:.1f}"
             f" C{cx + 8 * s:.1f},{base - 96 * s:.1f} {cx + 22 * s:.1f},{base - 108 * s:.1f} {cx + 14 * s:.1f},{base - 150 * s:.1f}"
             f" C{cx + 64 * s:.1f},{base - 100 * s:.1f} {cx + 62 * s:.1f},{base - 46 * s:.1f} {cx + 44 * s:.1f},{base:.1f} Z", "#f0612d"),
        path(f"M{cx - 24 * s:.1f},{base:.1f} C{cx - 38 * s:.1f},{base - 40 * s:.1f} {cx - 4 * s:.1f},{base - 50 * s:.1f} {cx - 6 * s:.1f},{base - 92 * s:.1f}"
             f" C{cx + 30 * s:.1f},{base - 62 * s:.1f} {cx + 34 * s:.1f},{base - 30 * s:.1f} {cx + 24 * s:.1f},{base:.1f} Z", "#ffc24a"),
    ])


# --------------------------------------------------------------------- plates

COVER_W, COVER_H = 960, 1280
SERIF = "Georgia, Iowan Old Style, Times New Roman, serif"


def sparkle(cx, cy, r, fill=SNOW, opacity=0.9):
    return path(f"M{cx},{cy - r} Q{cx},{cy} {cx + r},{cy} Q{cx},{cy} {cx},{cy + r} Q{cx},{cy} {cx - r},{cy} Q{cx},{cy} {cx},{cy - r} Z",
                fill, extra=f'opacity="{opacity}"')


def lighthouse(cx, base, s=1.0, lit=True):
    """A lighthouse on a rock. The lamp is at (cx, base - 190 * s)."""
    h = 190 * s
    y = lambda f: base - f * h
    stripe = lambda a, b: path(f"M{cx - (0.17 - 0.07 * a) * h:.1f},{y(a):.1f} L{cx + (0.17 - 0.07 * a) * h:.1f},{y(a):.1f}"
                               f" L{cx + (0.17 - 0.07 * b) * h:.1f},{y(b):.1f} L{cx - (0.17 - 0.07 * b) * h:.1f},{y(b):.1f} Z", "#c8452c")
    lamp = "#ffe27a" if lit else "#4a5568"
    parts = [
        path(f"M{cx - 0.62 * h:.1f},{base + 0.06 * h:.1f} C{cx - 0.5 * h:.1f},{y(0.2):.1f} {cx - 0.2 * h:.1f},{y(0.16):.1f} {cx:.1f},{y(0.14):.1f}"
             f" C{cx + 0.3 * h:.1f},{y(0.2):.1f} {cx + 0.55 * h:.1f},{y(0.08):.1f} {cx + 0.66 * h:.1f},{base + 0.06 * h:.1f} Z", "#2a3346"),
        path(f"M{cx - 0.17 * h:.1f},{y(0.1):.1f} L{cx + 0.17 * h:.1f},{y(0.1):.1f} L{cx + 0.105 * h:.1f},{y(0.86):.1f} L{cx - 0.105 * h:.1f},{y(0.86):.1f} Z", "#f4efe4"),
        stripe(0.1, 0.29), stripe(0.48, 0.67),
        rect(cx - 0.14 * h, y(0.90), 0.28 * h, 0.05 * h, "#1b2430", 2),
        rect(cx - 0.085 * h, y(1.04), 0.17 * h, 0.14 * h, lamp, 3, "#1b2430", 2.5),
        path(f"M{cx - 0.12 * h:.1f},{y(1.04):.1f} L{cx:.1f},{y(1.17):.1f} L{cx + 0.12 * h:.1f},{y(1.04):.1f} Z", "#1b2430"),
        rect(cx - 0.03 * h, y(0.42), 0.06 * h, 0.09 * h, "#1b2430", 3),
    ]

    if lit:
        parts.insert(0, circle(cx, y(0.97), 0.62 * h, "url(#lamp)"))

    return "\n".join(parts)


def wave(y, amp, fill, shift=0, width=COVER_W, height=COVER_H):
    d = f"M0,{y}"

    for x in range(0, width + 121, 120):
        d += f" Q{x + 30 + shift},{y - amp} {x + 60 + shift},{y} T{x + 120 + shift},{y}"

    return path(d + f" L{width},{height} L0,{height} Z", fill)


@plate("cover", "", "", "The cover of Distributed Systems from the Ground Up. On a stormy night 5 lighthouses stand on rocks in the "
       "sea, each kept by a crab, and beams of light join their lamps into a ring. Lightning strikes one lighthouse: its lamp "
       "is dark, its beams are broken, and its crab is shocked. The other 4 lamps still shine, and a paper boat carrying the "
       "word PUT sails safely between them. A sign reads: 4 of 5 still agree.", size=(COVER_W, COVER_H))
def cover():
    towers = [(232, 720, 0.78, True), (716, 690, 0.74, False), (118, 930, 0.98, True), (842, 920, 0.98, True), (480, 1100, 1.18, True)]
    lamp = lambda cx, base, s: (cx, base - 0.97 * 190 * s)
    lamps = [lamp(cx, base, s) for cx, base, s, _ in towers]
    ring = [(0, 2), (2, 4), (4, 3), (0, 4), (2, 3), (0, 3)]
    broken = [(0, 1), (1, 3), (1, 4)]

    defs = """<defs>
<linearGradient id="storm" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#070b18"/><stop offset="0.5" stop-color="#15243f"/>
<stop offset="0.8" stop-color="#1f4a5c"/><stop offset="1" stop-color="#2d6a73"/></linearGradient>
<linearGradient id="title" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#a9cdea"/></linearGradient>
<radialGradient id="lamp"><stop offset="0" stop-color="#ffe9a3" stop-opacity="0.75"/><stop offset="0.4" stop-color="#ffd15c" stop-opacity="0.22"/>
<stop offset="1" stop-color="#ffd15c" stop-opacity="0"/></radialGradient>
<radialGradient id="flash"><stop offset="0" stop-color="#e9f3ff" stop-opacity="0.75"/><stop offset="1" stop-color="#e9f3ff" stop-opacity="0"/></radialGradient>
</defs>"""

    cloud = lambda cx, cy, s, fill: "\n".join(ellipse(cx + dx * s, cy + dy * s, rx * s, ry * s, fill) for dx, dy, rx, ry in
                                              ((0, 0, 150, 52), (-110, 18, 100, 40), (120, 14, 110, 44), (40, -30, 90, 44), (-50, -22, 80, 38)))

    sky = [
        defs, rect(0, 0, COVER_W, COVER_H, "url(#storm)"),
        *[circle((k * 211 + 37) % COVER_W, (k * 131 + 17) % 420, 0.9 + (k % 4) * 0.4, SNOW, f'opacity="{0.25 + (k % 5) * 0.12:.2f}"') for k in range(60)],
        circle(716, 470, 260, "url(#flash)"),
        cloud(700, 452, 1.25, "#232d45"), cloud(210, 480, 1.0, "#1d2740"), cloud(470, 430, 0.8, "#283350"), cloud(860, 520, 0.7, "#1d2740"),
        path("M742,470 L690,566 L722,566 L676,668 L770,540 L734,540 L772,470 Z", "#ffe27a", "#fff6c9", 3),
        *[line(40 + 67 * k, 520 + (k * 37) % 90, 26 + 67 * k, 560 + (k * 37) % 90, "#9fc4dd", 2, 'opacity="0.35"') for k in range(14)],
    ]

    beam = lambda a, b: "\n".join([line(*lamps[a], *lamps[b], "#ffd15c", 9, 'opacity="0.16"'), line(*lamps[a], *lamps[b], "#ffe9a3", 2.5, 'opacity="0.9"')])
    dead = lambda a, b: line(*lamps[a], *lamps[b], "#ff8a70", 2.5, 'opacity="0.75" stroke-dasharray="3 12"')

    sea = [
        wave(700, 14, "#1c4a63"), wave(760, 16, "#1a4560", 40),
        lighthouse(*towers[0][:3]), lighthouse(*towers[1][:3], lit=False),
        crab(232 + 78, 724, 0.34, "happy", look=1, shade=False), crab(716 - 78, 696, 0.34, "shocked", look=1, shade=False),
        wave(850, 18, "#17405a", 20), wave(930, 20, "#143a54", 70),
        lighthouse(*towers[2][:3]), lighthouse(*towers[3][:3]),
        crab(118 + 96, 936, 0.42, "cute", look=1, shade=False), crab(842 - 96, 926, 0.42, "angry", look=-1, shade=False),
        *[dead(a, b) for a, b in broken], *[beam(a, b) for a, b in ring],
        '<g transform="translate(-140 -18)">',
        path("M420,842 L540,842 L512,880 L448,880 Z", "#fffaf0", "#cfd8e3", 2), path("M480,842 L480,768 L530,836 Z", "#fffaf0", "#cfd8e3", 2),
        path("M480,842 L480,790 L444,836 Z", "#e9eef5", "#cfd8e3", 2), label(498, 828, "PUT", 15, RUST, font=MONO, weight=800),
        path("M404,880 q20,-12 40,0 t40,0 t40,0 t40,0", stroke="#9fc4dd", sw=3, extra='opacity="0.6"'), "</g>",
        wave(1040, 22, "#11324b", 30), wave(1120, 24, "#0e2a41", 90),
        lighthouse(*towers[4][:3]), crab(480 + 124, 1112, 0.56, "happy", look=-1, shade=False),
        wave(1196, 14, "#0b2236", 50),
    ]

    title = [
        label(64, 92, "BUILDING RESILIENT, FAULT-TOLERANT", 27, "#cfe1f0", "start", weight=600, extra='letter-spacing="6"'),
        label(64, 128, "AND ROBUST", 27, "#cfe1f0", "start", weight=600, extra='letter-spacing="6"'),
        label(60, 236, "DISTRIBUTED", 102, "url(#title)", "start", weight=900),
        label(60, 340, "SYSTEMS", 102, "url(#title)", "start", weight=900),
        label(66, 408, "From the Ground Up", 56, "#ffc24a", "start", SERIF, 700, 'font-style="italic"'),
        rect(66, 428, 300, 4, "#ffc24a", 2, extra='opacity="0.7"'),
    ]

    sign = [
        rect(40, 1196, 330, 64, "#fff6e2", 10, WOOD, 4),
        label(205, 1224, "4 OF 5 STILL AGREE", 19, "#5a421a", weight=800, extra='letter-spacing="2.5"'),
        label(205, 1247, "the system keeps its promise", 15, RUST, font=SERIF, weight=700, extra='font-style="italic"'),
        label(920, 1232, "System Design and", 22, "#e3eef8", "end", SERIF, 700), label(920, 1260, "Low-Level Design in Rust", 22, "#e3eef8", "end", SERIF, 700),
    ]

    return sky + sea + title + sign


def board(x, y, w, h):
    """A drawing board on legs, with a sheet of blue paper."""
    return "\n".join([line(x + 30, y + h, x + 10, GROUND + 4, WOOD, 7), line(x + w - 30, y + h, x + w - 10, GROUND + 4, WOOD, 7),
                      rect(x, y, w, h, "#e9dcc3", 8, WOOD, 4), rect(x + 12, y + 12, w - 24, h - 24, "#1f5a85", 4)])


@plate("ch01", "Key-Value Store: System Design", "Draft the owl", "Draft, an owl, stands beside a drawing board. The blueprint on "
       "it shows a request passing through a router to a group of 3 nodes, one of them marked as the leader. A crab looks up "
       "at the board.")
def ch01():
    bx, by = 330, 70
    block = lambda x, y, w, text, fill="#2c79ad": rect(bx + x, by + y, w, 34, fill, 5, "#cfe6f7", 2) + label(bx + x + w / 2, by + y + 23, text, 15, "#eaf5fd", font=MONO)
    link = lambda x1, y1, x2, y2: line(bx + x1, by + y1, bx + x2, by + y2, "#cfe6f7", 2.5, 'stroke-dasharray="6 5"')

    return [
        backdrop(seed=5, **MEADOW),
        board(bx, by, 420, 220),
        block(30, 30, 90, "client"), block(165, 30, 90, "router"), link(120, 47, 165, 47),
        block(300, 30, 90, "map", "#3d6b3f"), link(255, 47, 300, 47),
        block(30, 150, 100, "leader", "#b7791f"), block(160, 150, 100, "follower"), block(290, 150, 100, "follower"),
        link(210, 64, 80, 150), link(130, 167, 160, 167), link(260, 167, 290, 167),
        label(bx + 210, by + 118, "shard 8", 16, "#9fd0ee", font=MONO),
        owl(210, GROUND, 1.0, look=1),
        line(262, GROUND - 96, 336, GROUND - 150, WOOD, 5), circle(338, GROUND - 152, 5, RUST),
        crab(820, GROUND + 6, 0.7, "cute", look=-1),
    ]


@plate("ch02", "Key-Value Store: Storage Node", "Ledger the tortoise", "Ledger, a tortoise, writes each change in a long "
       "ledger before saying yes. Lightning strikes beside it and a crab jumps in shock, and the ledger still holds every line "
       "that was written: put user-1, put user-2, delete user-2.")
def ch02():
    row = lambda k, text, fill="#27405a": label(462, 150 + 34 * k, text, 18, fill, "start", MONO, 700)

    return [
        backdrop(seed=8, **FOREST),
        path("M760,20 L716,110 L744,110 L704,196 L790,90 L758,90 L792,20 Z", "#ffe27a", "#fff6c9", 3),
        rect(430, 96, 330, 190, "#fff8ea", 8, WOOD, 4), rect(430, 96, 330, 30, WOOD, 8),
        label(595, 118, "THE LOG", 17, SNOW, extra='letter-spacing="4"'),
        row(0, "1  put user-1 ada"), row(1, "2  put user-2 grace"), row(2, "3  delete user-2"), row(3, "4  put us", RUST),
        line(560, 256, 574, 240, RUST, 4),
        line(450, 286, 440, GROUND + 4, WOOD, 7), line(740, 286, 750, GROUND + 4, WOOD, 7),
        tortoise(300, GROUND, 1.25),
        crab(850, GROUND - 26, 0.6, "shocked", look=-1),
    ]


@plate("ch03", "Key-Value Store: Replication", "Relay the pigeons", "Ledger the tortoise sits at the first of 3 ledgers. "
       "2 pigeons carry copies of its newest line to the other 2 ledgers. The first ledger shows lines 1 to 3 ticked, and "
       "the other 2 ledgers show the same lines.")
def ch03():
    def ledger(x, y, lines, ticked):
        rows = [label(x + 16, y + 44 + 24 * k, text, 15, "#27405a", "start", MONO, 700) for k, text in enumerate(lines)]
        ticks = [path(f"M{x + 112},{y + 38 + 24 * k} l6,7 l11,-13", stroke="#2e8b3d", sw=3.5) for k in range(ticked)]

        return "\n".join([line(x + 20, y + 110, x + 12, GROUND + 4, WOOD, 6), line(x + 120, y + 110, x + 128, GROUND + 4, WOOD, 6),
                          rect(x, y, 140, 110, "#fff8ea", 8, WOOD, 4), rect(x, y, 140, 24, WOOD, 8), *rows, *ticks])

    sheet = lambda x, y: rect(x, y, 30, 22, "#fff8ea", 3, WOOD, 2) + label(x + 15, y + 16, "3", 14, RUST, font=MONO)

    return [
        backdrop(seed=11, **SEA),
        ledger(250, 120, ["1 put", "2 put", "3 del"], 3), ledger(520, 150, ["1 put", "2 put", "3 del"], 2), ledger(760, 120, ["1 put", "2 put"], 2),
        tortoise(140, GROUND, 1.2),
        pigeon(455, 150, 0.6, 1), sheet(470, 150), pigeon(700, 110, 0.6, 1), sheet(715, 110),
        path("M400,170 q30,-30 60,-10", stroke="#cfe6f7", sw=3, extra='stroke-dasharray="5 6"'),
        path("M640,130 q30,-30 60,-10", stroke="#cfe6f7", sw=3, extra='stroke-dasharray="5 6"'),
    ]


@plate("ch04", "Key-Value Store: Leader Election", "The ballot cats", "3 cats sit in boxes numbered 1, 2 and 3. The cat in "
       "box 3 wears a small crown, and the other 2 cats each hold up a paper marked with a tick. A ballot box stands between "
       "them under a banner that reads term 1.")
def ch04():
    vote = lambda x, y: rect(x, y, 34, 40, "#fff8ea", 4, WOOD, 2) + path(f"M{x + 8},{y + 22} l7,8 l12,-16", stroke="#2e8b3d", sw=4)
    crown = lambda cx, y: path(f"M{cx - 26},{y} l6,-26 l12,16 l8,-22 l8,22 l12,-16 l6,26 Z", "#f2b632", "#a57f2c", 3)

    return [
        backdrop(seed=14, **FLOOR),
        rect(410, 60, 140, 34, RUST, 8), label(480, 84, "TERM 1", 20, extra='letter-spacing="3"'),
        rect(430, 200, 100, 110, "#3b4f6b", 8, "#1b2738", 4), rect(455, 214, 50, 8, "#1b2738", 4), label(480, 270, "votes", 18, "#cfe1f0", font=MONO),
        cat(190, GROUND - 4, 0.9, "#f0a35a", look=1, number="1"), vote(250, 150),
        cat(330, GROUND - 4, 0.9, "#b9c2cf", look=1, number="2"), vote(388, 150),
        cat(720, GROUND - 4, 1.0, "#e8d9b5", look=-1, number="3"), crown(720, GROUND - 176),
    ]


@plate("ch05", "Key-Value Store: Router", "Switch the octopus", "Switch, an octopus, sits between 2 stacks of boxes "
       "marked shard-a and shard-b. It holds a parcel labelled user-1 in one arm and points another arm at shard-a.")
def ch05():
    crate = lambda x, y, text, fill: rect(x, y, 150, 64, fill, 6, "#00000055", 3) + label(x + 75, y + 40, text, 20, SNOW, font=MONO)

    return [
        backdrop(seed=17, **SAND),
        crate(90, GROUND - 64, "shard-a", "#2f7f86"), crate(90, GROUND - 132, "shard-a", "#3d8f96"),
        crate(720, GROUND - 64, "shard-b", "#8a6a44"), crate(720, GROUND - 132, "shard-b", "#9a7a54"),
        octopus(480, GROUND, 1.0, look=-1),
        rect(330, GROUND - 150, 104, 44, "#fff8ea", 6, WOOD, 3), label(382, GROUND - 121, "user-1", 18, RUST, font=MONO),
        path(f"M330,{GROUND - 128} q-40,-10 -80,6", stroke="#cfe6f7", sw=3, extra='stroke-dasharray="5 6"'),
    ]


@plate("ch06", "Key-Value Store: Group Commit", "Bundle the beaver", "Bundle, a beaver, carries 4 logs tied together "
       "with a rope toward a door marked disk, where a single log lies that was carried alone. A crab watches with a "
       "stopwatch.")
def ch06():
    log = lambda x, y, w: rect(x, y, w, 20, "#a8773f", 10, "#6b4a2a", 3) + ellipse(x + w - 4, y + 10, 5, 8, "#d9b27a")

    return [
        backdrop(seed=21, **FOREST),
        rect(730, GROUND - 170, 120, 170, "#3b4856", 8, "#1b2430", 4), label(790, GROUND - 120, "DISK", 22, extra='letter-spacing="3"'),
        circle(832, GROUND - 80, 6, BRASS),
        log(640, GROUND - 22, 80),
        beaver(330, GROUND, 1.1, look=1),
        log(410, GROUND - 120, 150), log(410, GROUND - 98, 150), log(410, GROUND - 76, 150), log(410, GROUND - 54, 150),
        rect(470, GROUND - 124, 10, 94, "#e9dcc3", 4), rect(520, GROUND - 124, 10, 94, "#e9dcc3", 4),
        crab(140, GROUND + 6, 0.6, "happy", look=1),
    ]


def board_plate(name, title, crew, description, animal, scene, sign):
    """A plate with 1 animal beside a sign that states the chapter's idea in a few words."""

    @plate(name, title, crew, description)
    def draw():
        lines_ = [label(650, 150 + 34 * k, text, 22, "#27405a", font=MONO, weight=700) for k, text in enumerate(sign)]

        return [
            backdrop(seed=sum(map(ord, name)), **scene),
            line(520, 250, 510, GROUND + 4, WOOD, 7), line(780, 250, 790, GROUND + 4, WOOD, 7),
            rect(470, 96, 360, 160, "#fff8ea", 10, WOOD, 4), rect(470, 96, 360, 30, WOOD, 10),
            *lines_,
            animal(),
            crab(880, GROUND + 6, 0.5, "happy", look=-1),
        ]

    return draw


board_plate("ch07", "Rate Limiter", "Toll the gnu", "Toll, a gnu, stands beside a sign that reads: 5 per second, burst of 10.",
            lambda: gnu(250, GROUND, 1.0, look=1), MEADOW, ["5 per second", "burst of 10", "then: 429"])
board_plate("ch08", "Unique ID Generator", "Stamp the squirrel", "Stamp, a squirrel, stands beside a sign that reads: time, node, counter.",
            lambda: squirrel(250, GROUND, 1.0, look=1), FOREST, ["time | node | counter", "41  +  10  +  12", "= 64 bits"])
board_plate("ch09", "Distributed Cache", "Recall the elephant", "Recall, an elephant, stands beside a sign that reads: keep what was used last.",
            lambda: elephant(250, GROUND, 0.9, look=1), SAND, ["keep what was", "used last", "drop the oldest"])
board_plate("ch10", "Distributed Lock", "Latch the hermit crab", "Latch, a hermit crab, stands beside a sign that reads: token 1, token 2, the lower one is refused.",
            lambda: hermit(250, GROUND, 1.0, look=1), SAND, ["lease: 10 s", "token 1 < token 2", "old token: refused"])
board_plate("ch11", "Message Queue", "Post the pigeons", "2 pigeons stand beside a sign that lists offsets 0, 1 and 2, with a mark at the committed one.",
            lambda: pigeon(220, GROUND, 1.0, 1) + pigeon(320, GROUND, 0.8, 1), SEA, ["0  order-7 created", "1  order-8 created", "2  order-7 paid  <"])
board_plate("ch12", "Job Scheduler", "Shift the daemon", "Shift, a small daemon, stands beside a sign that reads: waiting, running, done.",
            lambda: daemon(250, GROUND, 1.0, look=1), FLOOR, ["waiting", "running, until t=3", "done"])
board_plate("ch13", "Notification Service", "Chime the penguin", "Chime, a penguin, stands beside a sign that lists pauses of 1, 2, 4 and 8 seconds.",
            lambda: penguin(250, GROUND, 0.9, look=1, scarf=RUST), ICE, ["try, wait 1 s", "try, wait 2 s", "try, wait 4 s"])
board_plate("ch14", "URL Shortener", "Dash the hare", "Dash, a hare, stands beside a sign that reads: 1000000 becomes 4C92.",
            lambda: hare(250, GROUND, 1.1, look=1), MEADOW, ["1000000", "in base 62", "= 4C92"])
board_plate("ch15", "News Feed", "Echo the owl", "Echo, an owl, stands beside a sign that reads: copy on write, or collect on read.",
            lambda: owl(250, GROUND, 1.0, look=1), FOREST, ["copy on write?", "collect on read?", "both."])
board_plate("ch16", "Object Store", "Crate the gopher", "Crate, a gopher, stands beside a sign that reads: 10 MB, 3 chunks, 3 copies of each.",
            lambda: gopher(250, GROUND, 1.0, look=1), FLOOR, ["10 MB", "= 3 chunks", "x 3 copies"])


board_plate("ch17", "Video Streaming", "Reel the whale", "A whale swims beside a sign that reads: 4 seconds at a time, in 4 qualities.",
            lambda: whale(250, GROUND - 60, 0.7), SEA, ["4 seconds at a time", "400 to 5000 kbit/s", "pick by speed"])
board_plate("ch18", "Chat", "Chirp the pigeons", "2 pigeons stand beside a sign that lists messages 1 to 4 and the words: last received 1.",
            lambda: pigeon(220, GROUND, 1.0, 1) + pigeon(320, GROUND, 0.8, -1), MEADOW, ["1 2 3 4", "received: 1", "send 2, 3, 4"])
board_plate("ch19", "Payment System", "Ledger the tortoise", "A tortoise stands beside a sign that reads: minus 40, plus 40, total 0.",
            lambda: tortoise(250, GROUND, 1.3), FLOOR, ["ada   -40.00", "shop  +40.00", "total   0.00"])
board_plate("ch20", "Ticket Booking", "The seat cats", "A cat sits in a box numbered 12 beside a sign that reads: held for 5 minutes, then sold or free.",
            lambda: cat(250, GROUND - 4, 1.0, "#f0a35a", look=1, number="12"), FLOOR, ["seat 12", "held: 5 minutes", "then sold, or free"])
board_plate("ch21", "Ride Hailing", "Dash the hare", "A hare stands beside a sign that shows a grid of 9 squares with the middle one marked.",
            lambda: hare(250, GROUND, 1.1, look=1), MEADOW, ["[ ][ ][ ]", "[ ][x][ ]", "[ ][ ][ ]"])
board_plate("ch22", "Search Autocomplete", "Hint the owl", "An owl stands beside a sign that reads: ka, then kafka, karaoke, kayak.",
            lambda: owl(250, GROUND, 1.0, look=1), FOREST, ["ka|", "kafka", "karaoke near me"])


board_plate("ch23", "Web Crawler", "Reach the octopus", "An octopus stands beside a sign that reads: 1 queue per host, wait 2 seconds, never twice.",
            lambda: octopus(250, GROUND, 1.0, look=1), SEA, ["1 queue per host", "wait 2 s", "never twice"])
board_plate("ch24", "Metrics and Monitoring", "Gauge the owl", "An owl stands beside a sign that reads: 40, plus 2, minus 3, plus 1.",
            lambda: owl(250, GROUND, 1.0, look=1), FOREST, ["40", "+2  -3  +1", "2 bytes a point"])
board_plate("ch25", "File Sync", "Carry the beaver", "A beaver stands beside a sign that reads: based on version 3, now version 4.",
            lambda: beaver(250, GROUND, 1.0, look=1), MEADOW, ["based on: v3", "server: v3", "accepted: v4"])
board_plate("ch26", "Collaborative Editing", "The 2 penguins", "2 penguins stand beside a sign that reads: cat, chat, cats, chats.",
            lambda: penguin(215, GROUND, 0.8, look=1) + penguin(315, GROUND, 0.7, look=-1, scarf=RUST), ICE, ["cat", "chat + cats", "= chats"])
board_plate("ch27", "Stock Exchange", "Tally the squirrel", "A squirrel stands beside a sign that reads: sell 1005, buy 1000, no trade yet.",
            lambda: squirrel(250, GROUND, 1.0, look=1), FLOOR, ["sell  1005", "buy   1000", "no trade yet"])
board_plate("ch28", "Click Aggregation", "Count the hare", "A hare stands beside a sign that reads: happened at 7, arrived at 13, counted at 7.",
            lambda: hare(250, GROUND, 1.1, look=1), SAND, ["happened: 7 s", "arrived: 13 s", "counted at: 7 s"])


def icon(name, draw, size=(240, 190)):
    """Writes a small transparent picture for use beside text."""
    (OUT / (name + ".svg")).write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size[0]} {size[1]}" width="{size[0]}" height="{size[1]}" role="img"'
        f' aria-hidden="true">\n' + draw + "\n</svg>\n")


def main(names):
    OUT.mkdir(parents=True, exist_ok=True)

    for name in names or list(PLATES):
        title, crew, description, draw, size = PLATES[name]
        parts = draw()

        if name.startswith("ch"):
            parts.append(ribbon(str(int(name[2:])), title, crew, size))

        (OUT / (name + ".svg")).write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size[0]} {size[1]}" width="{size[0]}" height="{size[1]}" role="img"'
            f' aria-label="{escape(description)}">\n' + "\n".join(parts) + "\n</svg>\n")
        print("  " + name)

    icon("crab-builder", builder_crab(120, 176))

    for mood in ("happy", "cute", "angry", "sleepy", "shocked"):
        icon("crab-" + mood, crab(120, 172, 1.0, mood, shade=False))

    icon("gopher", gopher(100, 170, 0.9, look=0), (200, 184))

    (OUT / "plates.json").write_text(json.dumps({name: p[2] for name, p in PLATES.items()}, indent=2) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
