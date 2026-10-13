#!/usr/bin/env python3
"""Draw the cover and the chapter-opener plates.

Each plate has a different animal at work on the chapter's subject: a penguin,
a gopher, a daemon, a hermit crab, an owl, a gnu, an elephant, a squirrel, an
octopus, a pair of pigeons, cats, a beaver and a whale. The SVG is written to
src/art/, with a JSON file of the descriptions that the chapters use as
alternative text.

    python3 tools/art.py              # every plate
    python3 tools/art.py ch03 cover   # some of them
"""

import json
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

@plate("cover", "", "", "The cover of Democratizing Linux: A Pipe Dream. A penguin in a nightcap sleeps on an ice floe and dreams "
       "of a desktop computer with a penguin on its screen, under the words the year of the Linux desktop. Beside it a "
       "dumpster is on fire, with a broken four-pane window sticking out of it. The dumpster is labelled teraSlop, and a sign "
       "reads: the evolution of spyware, vapourware and bloatware.", size=(960, 680))
def cover():
    base = 680 - (H - GROUND)
    pane = lambda x, y, c: rect(x, y, 34, 34, c, 3)

    return [
        label(480, 74, "DEMOCRATIZING LINUX", 60, extra='letter-spacing="5"'),
        label(480, 116, "A PIPE DREAM", 28, "#9fd8c6", extra='letter-spacing="10"'),
        *[circle(300 + 20 * k, 372 - 32 * k, 7 + 4 * k, SNOW, 'opacity="0.92"') for k in range(3)],
        rect(330, 150, 330, 122, SNOW, 50, extra='opacity="0.95"'),
        rect(370, 172, 110, 70, "#12263d", 6, STEEL, 4), rect(414, 242, 22, 12, STEEL), rect(396, 252, 58, 8, STEEL, 3),
        penguin(425, 236, 0.26),
        label(562, 198, "THE YEAR OF", 17, "#27405a"), label(562, 222, "THE LINUX", 21, RUST), label(562, 246, "DESKTOP", 21, RUST),
        penguin(230, base + 4, 1.0, asleep=True, left=8, right=-8, scarf=RUST, hat="nightcap"),
        *[label(150 - 18 * k, 400 - 24 * k, "z", 20 + 8 * k, "#cfe1f0", weight=800) for k in range(3)],
        flame(740, base - 96, 1.25), flame(812, base - 96, 0.9), flame(676, base - 96, 0.8),
        f'<g transform="rotate(-14 760 {base - 150})">' + pane(722, base - 190, "#4aa3e0") + pane(760, base - 190, "#4aa3e0")
        + pane(722, base - 152, "#4aa3e0") + pane(760, base - 152, "#4aa3e0")
        + path(f"M730,{base - 186} l18,22 l-8,10 l14,24", stroke=SNOW, sw=2.5) + "</g>",
        path(f"M640,{base - 100} H880 L860,{base + 2} H660 Z", "#2e6b4a", "#1d4a32", 4),
        rect(628, base - 112, 264, 18, "#3d8f5a", 5, "#1d4a32", 3),
        rect(676, base + 2, 22, 12, "#1d2733", 3), rect(822, base + 2, 22, 12, "#1d2733", 3),
        label(760, base - 44, "teraSlop", 34, SNOW, font=MONO),
        crab(540, base + 8, 0.62, "angry", look=1),
        rect(560, base + 26, 380, 54, "#fff8ea", 8, WOOD, 3),
        label(750, base + 48, "THE EVOLUTION OF", 15, "#5a421a", extra='letter-spacing="2"'),
        label(750, base + 70, "spyware · vapourware · bloatware", 19, RUST, font=MONO),
        label(250, base + 50, "The kernel's ideas, built by hand", 21, "#27405a", weight=600),
        label(250, base + 76, "in Go and in Rust", 21, "#27405a", weight=600),
    ]


@plate("ch01", "Pipes", "Flange the penguin", "Flange, a penguin in a hard hat, feeds the bytes of the word hello into a pipe. "
       "They come out of the other end in the same order, where a gopher is waiting to catch them.")
def ch01():
    return [backdrop(seed=1, **ICE),
            pipe(310, 230, 690), *[byte(350 + 62 * k, 230, c) for k, c in enumerate("hello")],
            byte(280, 230, "!", "#f0b27a"), byte(732, 230, "h", "#f0b27a"),
            penguin(170, s=0.9, look=1, right=-62, hat="hard"), gopher(830, s=0.82, look=-1),
            crab(500, 208, 0.5, "cute", shade=False)]


@plate("ch02", "File Descriptors", "Docket the gopher", "Docket, a gopher, stands at a wall of pigeonholes numbered 0 to 5. Holes 0, "
       "1 and 2 hold tickets for the terminal, and a string runs from the ticket in hole 3 to a filing cabinet.")
def ch02():
    holes = []

    for k in range(6):
        x = 346 + 84 * k
        holes += [rect(x, 150, 72, 72, CREAM, 8, "#7b6a4a", 3), label(x + 36, 140, str(k), 22, SNOW, font=MONO),
                  rect(x + 13, 174, 46, 26, [STEEL, STEEL, STEEL, RUST, RUST, CREAM][k], 4)]

    return [backdrop(seed=2, **FLOOR),
            rect(330, 108, 536, 130, WOOD, 10), *holes,
            rect(716, 252, 130, 78, "#6f8196", 8), rect(728, 264, 106, 22, "#93a4b6", 4), rect(728, 296, 106, 22, "#93a4b6", 4),
            path("M632,200 C640,262 672,246 716,276", stroke=RUST, sw=4),
            gopher(200, s=0.95, look=1)]


@plate("ch03", "Processes", "Fork the daemon", "Fork, a small red daemon, holds a fork. Beside it stands a smaller copy of itself, "
       "just created. Tags give their numbers: 500 for the parent and 501 for the child.")
def ch03():
    return [backdrop(seed=3, sky=("#2a1730", "#7a3b4a"), ground=("#6b4a52", "#8f6a70")),
            daemon(330, s=1.0, look=1), daemon(610, s=0.62, look=-1),
            rect(288, 88, 84, 34, RUST, 8), label(330, 112, "500", 21, font=MONO),
            rect(574, 162, 72, 30, BRASS, 8), label(610, 184, "501", 19, "#12263d", font=MONO),
            path("M374,106 C470,96 520,130 572,170", stroke=SNOW, sw=3, extra='stroke-dasharray="7 7" opacity="0.85"'),
            label(476, 100, "fork()", 21, "#ffe3d6", font=MONO)]


@plate("ch04", "Building a Shell", "Conch the hermit crab", "Conch, a hermit crab, lives in a shell and types at a terminal. The screen "
       "shows a pipeline, and behind the terminal 3 small penguins stand in a row, each passing a fish to the next.")
def ch04():
    return [backdrop(seed=4, **SAND),
            rect(360, 92, 340, 180, "#0f1c2b", 14, "#6f8196", 5),
            label(384, 136, "$ seq 1 5 | sort | wc", 21, "#8ff0c6", "start", MONO), label(384, 170, "5", 21, SNOW, "start", MONO),
            label(384, 204, "$ _", 21, "#8ff0c6", "start", MONO),
            rect(500, 272, 60, 22, "#6f8196", 4), rect(460, 290, 140, 12, "#93a4b6", 5),
            hermit(170, s=1.0, look=1),
            *[penguin(748 + 70 * k, GROUND + 2, 0.40, look=1 if k < 2 else -1, right=-52) for k in range(3)],
            *[path(f"M{772 + 70 * k},292 q11,-9 22,0 q-11,9 -22,0 l-7,-6 v12 z", "#9fd8c6") for k in range(2)]]


@plate("ch05", "Signals", "Klaxon the owl", "Klaxon, an owl, is the night watch. Signal flags numbered 2, 9 and 15 fly from a mast, a "
       "bell rings, and a hare that was asleep jumps awake.")
def ch05():
    flags = []

    for k, (number, colour) in enumerate([("2", BRASS), ("9", RUST), ("15", TEAL)]):
        flags += [path(f"M520,{84 + 50 * k} h74 l-16,20 l16,20 h-74 Z", colour), label(550, 111 + 50 * k, number, 21, font=MONO)]

    return [backdrop(seed=5, **FOREST),
            rect(512, 74, 8, 254, "#93a4b6", 3), *flags,
            owl(230, s=1.0, look=1),
            path("M330,150 q30,-34 60,0 l10,34 h-80 Z", BRASS), rect(354, 122, 12, 24, "#a57f2c", 4), circle(360, 192, 9, "#a57f2c"),
            *[path(f"M{408 + 22 * k},{150 - 8 * k} q14,20 0,44", stroke=SNOW, sw=3.5, extra=f'opacity="{0.9 - 0.25 * k:.2f}"') for k in range(3)],
            hare(780, s=1.0, look=-1), label(780, 140, "!", 46, BRASS)]


@plate("ch06", "CPU Scheduling", "Tick the gnu", "Tick, a gnu in a referee's shirt, holds a stopwatch over a single running lane. A "
       "hare and a tortoise wait their turn, and the bib with the smallest number runs next.")
def ch06():
    return [backdrop(seed=6, **MEADOW),
            path(f"M360,{GROUND + 6} H940", stroke=SNOW, sw=4, extra='stroke-dasharray="18 14" opacity="0.8"'),
            gnu(200, s=0.98, look=1),
            circle(318, 150, 36, SNOW, f'stroke="{BRASS}" stroke-width="6"'), line(318, 150, 318, 124, INK, 4), line(318, 150, 336, 158, RUST, 4),
            rect(310, 104, 16, 12, BRASS, 3),
            hare(540, s=1.05, look=1), rect(510, 196, 60, 28, TEAL, 6), label(540, 217, "2.0", 18, font=MONO),
            tortoise(780, s=1.25), rect(748, 196, 60, 28, STEEL, 6), label(778, 217, "3.1", 18, font=MONO)]


@plate("ch07", "Virtual Memory", "Atlas the elephant", "Atlas, an elephant, draws a map divided into numbered pages with a pencil "
       "held in its trunk. Most squares are blank, a few are filled in, and one is being drawn now that it is needed.")
def ch07():
    cells, filled = [], {0, 1, 5, 9, 10, 14}

    for k in range(18):
        x, y = 420 + 74 * (k % 6), 104 + 62 * (k // 6)
        cells.append(rect(x, y, 66, 54, "#e8c877" if k in filled else CREAM, 5, "#7b6a4a", 2.5, 'stroke-dasharray="6 6"' if k == 12 else ""))

        if k in filled:
            cells.append(label(x + 33, y + 35, str(k), 20, "#12263d", font=MONO))

    return [backdrop(seed=7, sky=("#1b2540", "#5a5a8a"), ground=("#a58e6a", "#c9b48e")),
            rect(404, 88, 462, 204, WOOD, 10), *cells,
            elephant(210, s=0.98, look=1),
            line(296, 204, 420, 250, RUST, 7), line(420, 250, 434, 255, "#f4e6da", 7)]


@plate("ch08", "The Page Cache", "Stash the squirrel", "Stash, a squirrel, keeps the pages it read most recently on a shelf within "
       "reach and holds an acorn. The full store is a hollow in a distant tree, a longer trip that the shelf saves.")
def ch08():
    books = [rect(404 + 32 * k, 148 + (k % 3) * 6, 26, 84 - (k % 3) * 6, colour, 3)
             for k, colour in enumerate([RUST, TEAL, BRASS, STEEL, RUST, TEAL, BRASS])]

    return [backdrop(seed=8, **FOREST),
            rect(388, 130, 258, 12, WOOD, 3), rect(388, 232, 258, 12, WOOD, 3), rect(388, 130, 12, 196, WOOD, 3), rect(634, 130, 12, 196, WOOD, 3), *books,
            rect(790, 110, 90, 220, "#6b4a2a", 14), circle(835, 60, 96, "#3f7a4a"), circle(770, 96, 60, "#4a8a55"), circle(900, 100, 58, "#4a8a55"),
            ellipse(835, 220, 26, 34, "#2a1c10"), label(835, 284, "DISK", 18, "#f3dcc0"),
            path("M660,300 H770", stroke=SNOW, sw=3, extra='stroke-dasharray="4 12" opacity="0.7"'),
            squirrel(220, s=1.0, look=1)]


@plate("ch09", "Event Loops and epoll", "Relay the octopus", "Relay, an octopus wearing a headset, works a switchboard. 2 lamps on the "
       "board are lit, and an arm reaches to each of them. The other lines are left alone.")
def ch09():
    lamps, lit = [], []

    for k in range(15):
        x, y = 470 + 78 * (k % 5), 120 + 66 * (k // 5)
        on = k in (3, 11)
        lamps += [circle(x, y, 18, BRASS if on else "#3b5068"), circle(x, y, 9, SNOW if on else "#52677f")]

        if on:
            lit.append((x, y))

    return [backdrop(seed=9, sky=("#101d33", "#27406b"), ground=("#2d4a6b", "#3e6088")),
            rect(436, 86, 380, 216, "#1c3149", 12, "#6f8196", 4), *lamps,
            octopus(220, s=1.0, look=1, reach=lit)]


@plate("ch10", "TCP Sockets", "Halyard and Cleat the pigeons", "Halyard and Cleat, 2 carrier pigeons on separate posts, face each "
       "other. Notes numbered 1, 2 and 3 travel along a line between them, in order.")
def ch10():
    return [backdrop(seed=10, sky=("#14283f", "#c98a5a"), ground=("#5f9a62", "#86bd7c")),
            rect(196, 232, 20, 100, WOOD, 4), rect(156, 222, 100, 16, WOOD, 5), rect(744, 232, 20, 100, WOOD, 4), rect(704, 222, 100, 16, WOOD, 5),
            pigeon(206, 222, 1.2, 1), pigeon(754, 222, 1.2, -1),
            path("M300,150 Q480,214 660,150", stroke=SNOW, sw=3),
            *[rect(366 + 82 * k, 160 + [6, 18, 6][k], 50, 30, CREAM, 4, "#7b6a4a", 2) + label(391 + 82 * k, 182 + [6, 18, 6][k], str(k + 1), 19, "#12263d", font=MONO)
              for k in range(3)],
            label(480, 120, "SYN   ·   ACK   ·   data", 18, "#ffe9cf", font=MONO)]


@plate("ch11", "Namespaces", "The box cats", "3 cats sit in 3 cardboard boxes. Every box is marked number 1, and each cat is sure it "
       "is the first. An owl on a branch above can see all 3.")
def ch11():
    return [backdrop(seed=11, **FLOOR),
            path("M700,96 H960", stroke=WOOD, sw=14), owl(860, 92, 0.42, look=-1),
            cat(190, GROUND + 4, 1.05, "#f0a35a", 1), cat(450, GROUND + 4, 1.05, "#8f98a3", 0), cat(710, GROUND + 4, 1.05, "#3a3f47", -1)]


@plate("ch12", "Control Groups", "Weir the beaver", "Weir, a beaver in a hard hat, has built a dam. A mark on the dam shows the limit, "
       "the water stands exactly at the mark, and no more is let through.")
def ch12():
    logs = [rect(470 + (k % 2) * 14, 150 + 26 * k, 330 - (k % 2) * 28, 22, "#8a5a3a" if k % 2 else "#a06a44", 11, "#5a3d28", 2) for k in range(7)]

    return [backdrop(seed=12, **MEADOW),
            rect(786, 196, 174, 150, "#3c8dc5"), path("M786,196 q22,-10 44,0 t44,0 t44,0 t44,0", stroke="#bfe3f7", sw=4),
            *logs,
            line(452, 196, 836, 196, RUST, 4, 'stroke-dasharray="10 8"'), rect(380, 180, 76, 32, RUST, 8), label(418, 203, "max", 20, font=MONO),
            beaver(220, s=1.0, look=1)]


@plate("ch13", "Building a Container", "Moby and the crew", "A whale carries shipping containers on its back across the sea. A "
       "penguin, a gopher and a crab ride on top, and the middle container has a window through which a small igloo can be seen.")
def ch13():
    return [backdrop(seed=13, **SEA),
            whale(480, 292, 1.3),
            box(404, 136, 134, 68, RUST, "pid"), box(544, 136, 134, 68, TEAL), box(474, 64, 134, 68, BRASS, "net", "#12263d"),
            rect(566, 150, 90, 40, "#dfeef5", 6, "#1d4f54", 3),
            path("M590,190 A20,20 0 0 1 630,190 Z", SNOW, "#9fb6c8", 2), rect(604, 176, 12, 14, "#27405a", 3),
            penguin(436, 136, 0.34, look=1), gopher(646, 136, 0.34, look=-1), hermit(528, 64, 0.30, look=1),
            *[path(f"M{60 + 150 * k},{H - 84} q20,-12 40,0 t40,0", stroke="#bfe3f7", sw=3, extra='opacity="0.6"') for k in range(6)]]



@plate("crab-moods", "", "", "4 crabs show what a write to a pipe can meet. A happy crab: the ring has room, and the bytes go in. "
       "A sleeping crab: the ring is full, and the writer sleeps. An angry crab: no reader is left, and the write fails with "
       "EPIPE. A cute crab: the writer closes its end, and the reader sees the end of the stream.", size=(960, 330))
def crab_moods():
    moods = [("happy", "the ring has room", "write returns"), ("sleepy", "the ring is full", "the writer sleeps"),
             ("angry", "no reader is left", "SIGPIPE, EPIPE"), ("cute", "the writer closes", "read returns 0")]
    parts = [rect(0, 0, 960, 330, "#12263d"), rect(0, 230, 960, 100, "#1c3856")]

    for k, (mood, when, result) in enumerate(moods):
        cx = 120 + 240 * k
        parts += [crab(cx, 196, 1.0, mood), label(cx, 262, when, 21), label(cx, 294, result, 19, "#ffd9c7", font=MONO, weight=600)]

    return parts


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

        if name == "cover":
            parts = [backdrop(seed=3, size=size, **ICE), *parts]
        elif name.startswith("ch"):
            parts.append(ribbon(str(int(name[2:])), title, crew, size))

        (OUT / (name + ".svg")).write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size[0]} {size[1]}" width="{size[0]}" height="{size[1]}" role="img"'
            f' aria-label="{escape(description)}">\n' + "\n".join(parts) + "\n</svg>\n")
        print("  " + name)

    for mood in ("happy", "cute", "angry", "sleepy", "shocked"):
        icon("crab-" + mood, crab(120, 172, 1.0, mood, shade=False))

    icon("gopher", gopher(100, 170, 0.9, look=0), (200, 184))

    (OUT / "plates.json").write_text(json.dumps({name: p[2] for name, p in PLATES.items()}, indent=2) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
