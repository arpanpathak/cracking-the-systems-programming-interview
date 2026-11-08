#!/usr/bin/env python3
"""Draw the cover and the chapter-opener plates.

Each plate has a different animal at work on the chapter's subject: a stork, an
owl, a beaver, bees, a hound, a raccoon on traffic duty, a fox at a gate, a
hermit crab, parrots, a sheepdog, squirrels, a magpie, a chameleon and a
hedgehog. The SVG is written to src/art/, with a JSON file of the descriptions
that the chapters use as alternative text.

    python3 tools/art.py              # every plate
    python3 tools/art.py ch03 cover   # some of them
"""

import json
import math
import sys
from xml.sax.saxutils import escape

from artkit import (BRASS, CREAM, FLOOR, FOREST, GROUND, H, INK, MEADOW, MONO, OUT, RUST, SAND, SANS, SEA, SNOW,
                    STEEL, TEAL, W, backdrop, box, circle, ellipse, eye, label, line, path, pine, rect, ribbon, rot,
                    shadow, sparkle)

PLATES = {}
GPU_GREEN = "#76b900"
NIGHT = dict(sky=("#0e1b2e", "#24476b"), ground=("#2c3e55", "#3c5470"))
DOCK = dict(sky=("#13243a", "#355f86"), ground=("#6b5a48", "#8f7a62"))


def plate(name, number, title, crew, description, size=(W, H)):
    """Registers a function that returns the parts of one plate."""

    def register(draw):
        PLATES[name] = (number, title, crew, description, draw, size)

        return draw

    return register


# ------------------------------------------------------------------ props

def chip(cx, cy, s=1.0, text="GPU", glow=True):
    """A GPU package: a green die on a dark substrate with pins on 4 sides."""
    w = 70 * s
    pins = []

    for k in range(5):
        off = -w / 2 + w * (k + 0.5) / 5

        pins += [rect(cx + off - 2.5 * s, cy - w / 2 - 8 * s, 5 * s, 8 * s, "#c9ccd1"),
                 rect(cx + off - 2.5 * s, cy + w / 2, 5 * s, 8 * s, "#c9ccd1"),
                 rect(cx - w / 2 - 8 * s, cy + off - 2.5 * s, 8 * s, 5 * s, "#c9ccd1"),
                 rect(cx + w / 2, cy + off - 2.5 * s, 8 * s, 5 * s, "#c9ccd1")]

    halo = [circle(cx, cy, w * 0.95, GPU_GREEN, 'opacity="0.16"')] if glow else []

    return "\n".join([*halo, *pins, rect(cx - w / 2, cy - w / 2, w, w, "#23272e", 6 * s),
                      rect(cx - w * 0.32, cy - w * 0.32, w * 0.64, w * 0.64, GPU_GREEN, 4 * s),
                      label(cx, cy + 6 * s, text, 16 * s, "#10220a", font=MONO)])


def server(x, y, w=86, h=120, lamp="#55d17a", tag=""):
    """A rack server seen from the front: 4 drive bays and a status lamp."""
    bays = [rect(x + 10, y + 12 + 24 * k, w - 20, 16, "#3a4656", 3) for k in range(4)]

    return "\n".join([rect(x, y, w, h, "#20293a", 6, "#4d5b70", 2), *bays, circle(x + w - 14, y + h - 12, 5, lamp),
                      label(x + w / 2 - 8, y + h - 7, tag, 13, "#c4d2e2", font=MONO, weight=600)])


def cone(cx, base, s=1.0):
    return "\n".join([path(f"M{cx - 16 * s:.1f},{base:.1f} L{cx:.1f},{base - 46 * s:.1f} L{cx + 16 * s:.1f},{base:.1f} Z", "#f07a26"),
                      rect(cx - 9 * s, base - 30 * s, 18 * s, 7 * s, SNOW), rect(cx - 22 * s, base - 4 * s, 44 * s, 6 * s, "#d0611a", 2)])


def screen(x, y, w, h, lines, title=""):
    """A terminal window with a title bar and monospaced lines."""
    body = [label(x + 14, y + 44 + 22 * k, text, 15, "#bfe9c4", "start", MONO, 500) for k, text in enumerate(lines)]

    return "\n".join([rect(x, y, w, h, "#0f1722", 8, "#56657a", 2), rect(x, y, w, 24, "#2b3646", 8),
                      circle(x + 14, y + 12, 4, "#ff6159"), circle(x + 28, y + 12, 4, "#ffbd2e"),
                      circle(x + 42, y + 12, 4, "#28c941"), label(x + w / 2, y + 17, title, 13, "#c4d2e2", font=MONO, weight=600),
                      *body])


def tag(x, y, text, fill="#e8c877", ink="#12263d", size=15):
    w = 14 + 9.2 * len(text) * size / 15

    return rect(x - w / 2, y - 14, w, 26, fill, 6) + label(x, y + 5, text, size, ink, font=MONO)


def heart(cx, cy, r, fill="#ff5d73"):
    return path(f"M{cx:.1f},{cy + r:.1f} C{cx - 1.6 * r:.1f},{cy - 0.2 * r:.1f} {cx - 0.9 * r:.1f},{cy - 1.4 * r:.1f}"
                f" {cx:.1f},{cy - 0.55 * r:.1f} C{cx + 0.9 * r:.1f},{cy - 1.4 * r:.1f} {cx + 1.6 * r:.1f},{cy - 0.2 * r:.1f}"
                f" {cx:.1f},{cy + r:.1f} Z", fill)


def wheel(cx, cy, r, fill=BRASS, spokes=7):
    """A ship's wheel with handles."""
    parts = [circle(cx, cy, r, "none", f'stroke="{fill}" stroke-width="{r * 0.16:.1f}"'),
             circle(cx, cy, r * 0.22, fill)]

    for k in range(spokes):
        a = 2 * math.pi * k / spokes - math.pi / 2
        parts += [line(cx, cy, cx + 1.32 * r * math.cos(a), cy + 1.32 * r * math.sin(a), fill, r * 0.09),
                  circle(cx + 1.36 * r * math.cos(a), cy + 1.36 * r * math.sin(a), r * 0.10, fill)]

    return "\n".join(parts)


def hexagon(cx, cy, r, fill, stroke="none", sw=0):
    pts = " ".join(f"{cx + r * math.cos(math.pi / 3 * k + math.pi / 6):.1f},{cy + r * math.sin(math.pi / 3 * k + math.pi / 6):.1f}"
                   for k in range(6))

    return f'<polygon points="{pts}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


# ------------------------------------------------------------------ the crew

def raccoon(cx, base=GROUND, s=1.0, look=0.0, cape=None, cap=False, arm=0):
    """A raccoon: grey coat, black mask, ringed tail. `cape` colours a hero's cape; `cap` adds a police cap."""
    h, coat = 180 * s, "#8c939c"
    y = lambda f: base - f * h
    parts = [shadow(cx, base, 0.34 * h)]

    if cape:
        parts.append(path(f"M{cx - 0.18 * h:.1f},{y(0.66):.1f} Q{cx - 0.56 * h:.1f},{y(0.30):.1f} {cx - 0.46 * h:.1f},{y(0.0):.1f}"
                          f" L{cx + 0.46 * h:.1f},{y(0.0):.1f} Q{cx + 0.56 * h:.1f},{y(0.30):.1f} {cx + 0.18 * h:.1f},{y(0.66):.1f} Z", cape))

    rings = [ellipse(cx - 0.30 * h - 0.07 * h * k, y(0.18 + 0.09 * k), 0.07 * h, 0.05 * h,
                     INK if k % 2 else coat, rot(35, cx - 0.30 * h - 0.07 * h * k, y(0.18 + 0.09 * k))) for k in range(5)]
    parts += rings
    parts += [ellipse(cx - 0.10 * h, y(0.02), 0.09 * h, 0.035 * h, "#3d4249"), ellipse(cx + 0.10 * h, y(0.02), 0.09 * h, 0.035 * h, "#3d4249"),
              ellipse(cx, y(0.33), 0.24 * h, 0.31 * h, coat), ellipse(cx, y(0.28), 0.15 * h, 0.21 * h, "#d5d9de"),
              ellipse(cx - 0.25 * h, y(0.38), 0.05 * h, 0.14 * h, coat, rot(16, cx - 0.25 * h, y(0.5))),
              ellipse(cx + 0.25 * h, y(0.42), 0.05 * h, 0.14 * h, coat, rot(-16 - arm, cx + 0.24 * h, y(0.54))),
              path(f"M{cx - 0.19 * h:.1f},{y(0.86):.1f} L{cx - 0.14 * h:.1f},{y(1.02):.1f} L{cx - 0.05 * h:.1f},{y(0.90):.1f} Z", coat),
              path(f"M{cx + 0.19 * h:.1f},{y(0.86):.1f} L{cx + 0.14 * h:.1f},{y(1.02):.1f} L{cx + 0.05 * h:.1f},{y(0.90):.1f} Z", coat),
              circle(cx, y(0.76), 0.20 * h, coat),
              path(f"M{cx - 0.21 * h:.1f},{y(0.79):.1f} Q{cx:.1f},{y(0.70):.1f} {cx + 0.21 * h:.1f},{y(0.79):.1f}"
                   f" Q{cx:.1f},{y(0.88):.1f} {cx - 0.21 * h:.1f},{y(0.79):.1f} Z", INK),
              eye(cx - 0.08 * h, y(0.79), 0.042 * h, look), eye(cx + 0.08 * h, y(0.79), 0.042 * h, look),
              ellipse(cx, y(0.66), 0.11 * h, 0.07 * h, "#e9ecef"), ellipse(cx, y(0.69), 0.03 * h, 0.02 * h, INK)]

    if cap:
        parts += [path(f"M{cx - 0.18 * h:.1f},{y(0.90):.1f} Q{cx:.1f},{y(1.06):.1f} {cx + 0.18 * h:.1f},{y(0.90):.1f} Z", "#1f3b73"),
                  rect(cx - 0.22 * h, y(0.915), 0.44 * h, 0.035 * h, INK, 3), circle(cx, y(0.96), 0.03 * h, BRASS)]

    return "\n".join(parts)


def stork(cx, base=GROUND, s=1.0, bundle=None):
    """A stork on long legs. `bundle` is a text for the bundle that hangs from its beak."""
    h = 230 * s
    y = lambda f: base - f * h
    parts = [shadow(cx, base, 0.22 * h),
             line(cx - 0.05 * h, y(0.0), cx - 0.04 * h, y(0.36), "#e0583a", 3.5 * s + 1),
             line(cx + 0.05 * h, y(0.0), cx + 0.04 * h, y(0.36), "#e0583a", 3.5 * s + 1),
             ellipse(cx, y(0.47), 0.22 * h, 0.12 * h, SNOW, rot(-12, cx, y(0.47))),
             path(f"M{cx - 0.20 * h:.1f},{y(0.44):.1f} Q{cx - 0.02 * h:.1f},{y(0.36):.1f} {cx + 0.16 * h:.1f},{y(0.48):.1f}"
                  f" Q{cx - 0.02 * h:.1f},{y(0.52):.1f} {cx - 0.20 * h:.1f},{y(0.44):.1f} Z", INK),
             path(f"M{cx + 0.13 * h:.1f},{y(0.53):.1f} Q{cx + 0.20 * h:.1f},{y(0.70):.1f} {cx + 0.15 * h:.1f},{y(0.82):.1f}", stroke=SNOW, sw=0.07 * h),
             circle(cx + 0.16 * h, y(0.85), 0.06 * h, SNOW), eye(cx + 0.18 * h, y(0.865), 0.017 * h, 0.6),
             path(f"M{cx + 0.21 * h:.1f},{y(0.86):.1f} L{cx + 0.42 * h:.1f},{y(0.80):.1f} L{cx + 0.21 * h:.1f},{y(0.83):.1f} Z", "#e0583a")]

    if bundle:
        bx, by = cx + 0.40 * h, y(0.80)
        parts += [line(bx, by, bx, by + 0.14 * h, "#d9cfb8", 2),
                  path(f"M{bx - 0.13 * h:.1f},{by + 0.14 * h:.1f} Q{bx:.1f},{by + 0.08 * h:.1f} {bx + 0.13 * h:.1f},{by + 0.14 * h:.1f}"
                       f" L{bx + 0.10 * h:.1f},{by + 0.34 * h:.1f} L{bx - 0.10 * h:.1f},{by + 0.34 * h:.1f} Z", "#f2e8d2", "#c9b98f", 2),
                  label(bx, by + 0.27 * h, bundle, 13, "#4b3b1e", font=MONO)]

    return "\n".join(parts)


def owl(cx, base=GROUND, s=1.0, look=0.0, glasses=True):
    h, coat = 175 * s, "#7a5a3c"
    y = lambda f: base - f * h
    parts = [shadow(cx, base, 0.32 * h),
             ellipse(cx - 0.10 * h, y(0.01), 0.07 * h, 0.03 * h, BRASS), ellipse(cx + 0.10 * h, y(0.01), 0.07 * h, 0.03 * h, BRASS),
             path(f"M{cx - 0.24 * h:.1f},{y(0.86):.1f} L{cx - 0.30 * h:.1f},{y(1.04):.1f} L{cx - 0.10 * h:.1f},{y(0.94):.1f} Z", coat),
             path(f"M{cx + 0.24 * h:.1f},{y(0.86):.1f} L{cx + 0.30 * h:.1f},{y(1.04):.1f} L{cx + 0.10 * h:.1f},{y(0.94):.1f} Z", coat),
             ellipse(cx, y(0.47), 0.30 * h, 0.47 * h, coat), ellipse(cx, y(0.30), 0.19 * h, 0.25 * h, "#e7d0ac"),
             ellipse(cx - 0.30 * h, y(0.42), 0.07 * h, 0.22 * h, "#5e432c", rot(12, cx - 0.28 * h, y(0.6))),
             ellipse(cx + 0.30 * h, y(0.44), 0.07 * h, 0.22 * h, "#5e432c", rot(-40, cx + 0.28 * h, y(0.6))),
             circle(cx - 0.125 * h, y(0.72), 0.13 * h, CREAM), circle(cx + 0.125 * h, y(0.72), 0.13 * h, CREAM),
             eye(cx - 0.125 * h, y(0.72), 0.08 * h, look, 0.6), eye(cx + 0.125 * h, y(0.72), 0.08 * h, look, 0.6),
             path(f"M{cx - 0.04 * h:.1f},{y(0.66):.1f} h{0.08 * h:.1f} l{-0.04 * h:.1f},{0.08 * h:.1f} Z", BRASS)]

    if glasses:
        parts += [circle(cx - 0.125 * h, y(0.72), 0.10 * h, "none", f'stroke="{INK}" stroke-width="{2.5 * s + 0.5:.1f}"'),
                  circle(cx + 0.125 * h, y(0.72), 0.10 * h, "none", f'stroke="{INK}" stroke-width="{2.5 * s + 0.5:.1f}"'),
                  line(cx - 0.025 * h, y(0.72), cx + 0.025 * h, y(0.72), INK, 2.5 * s + 0.5)]

    return "\n".join(parts)


def beaver(cx, base=GROUND, s=1.0, look=0.0):
    h, coat = 170 * s, "#8a5a3a"
    y = lambda f: base - f * h

    return "\n".join([
        shadow(cx - 0.1 * h, base, 0.48 * h),
        ellipse(cx - 0.36 * h, y(0.07), 0.24 * h, 0.075 * h, "#5a3d28"),
        ellipse(cx - 0.11 * h, y(0.02), 0.11 * h, 0.04 * h, "#5a3d28"), ellipse(cx + 0.12 * h, y(0.02), 0.11 * h, 0.04 * h, "#5a3d28"),
        ellipse(cx, y(0.34), 0.25 * h, 0.33 * h, coat), ellipse(cx, y(0.28), 0.15 * h, 0.22 * h, "#d9b48a"),
        ellipse(cx - 0.27 * h, y(0.42), 0.055 * h, 0.12 * h, coat, rot(18, cx - 0.27 * h, y(0.5))),
        ellipse(cx + 0.27 * h, y(0.46), 0.055 * h, 0.12 * h, coat, rot(-62, cx + 0.25 * h, y(0.5))),
        circle(cx - 0.15 * h, y(0.90), 0.05 * h, coat), circle(cx + 0.15 * h, y(0.90), 0.05 * h, coat),
        circle(cx, y(0.76), 0.20 * h, coat), ellipse(cx, y(0.68), 0.12 * h, 0.085 * h, "#d9b48a"),
        eye(cx - 0.08 * h, y(0.80), 0.05 * h, look), eye(cx + 0.08 * h, y(0.80), 0.05 * h, look),
        ellipse(cx, y(0.72), 0.035 * h, 0.022 * h, "#3e2a1b"),
        rect(cx - 0.04 * h, y(0.675), 0.08 * h, 0.085 * h, SNOW, 2, "#c9b9a0", 1),
        path(f"M{cx - 0.19 * h:.1f},{y(0.89):.1f} A{0.19 * h:.1f},{0.16 * h:.1f} 0 0 1 {cx + 0.19 * h:.1f},{y(0.89):.1f} Z", BRASS),
        rect(cx - 0.23 * h, y(0.90), 0.46 * h, 0.03 * h, "#a57f2c", 3),
    ])


def bee(cx, cy, s=1.0, tilt=0, look=0.6):
    """A worker bee in flight."""
    r = 20 * s
    stripes = [rect(cx - r * (0.35 - 0.5 * k), cy - r * 0.62, r * 0.22, r * 1.24, INK, 2) for k in range(2)]

    return f'<g {rot(tilt, cx, cy)}>' + "\n".join([
        ellipse(cx - r * 0.2, cy - r * 0.95, r * 0.55, r * 0.35, "#dff3ff", 'opacity="0.85"'),
        ellipse(cx + r * 0.3, cy - r * 0.95, r * 0.45, r * 0.30, "#dff3ff", 'opacity="0.85"'),
        ellipse(cx, cy, r * 1.0, r * 0.65, "#ffcc33"), *stripes,
        path(f"M{cx - r:.1f},{cy:.1f} l{-r * 0.35:.1f},{r * 0.1:.1f} l{r * 0.35:.1f},{r * 0.1:.1f} Z", INK),
        circle(cx + r * 1.05, cy - r * 0.1, r * 0.45, INK), eye(cx + r * 1.18, cy - r * 0.2, r * 0.17, look),
        path(f"M{cx + r * 1.15:.1f},{cy - r * 0.5:.1f} q{r * 0.1:.1f},{-r * 0.5:.1f} {r * 0.45:.1f},{-r * 0.6:.1f}", stroke=INK, sw=2),
    ]) + "</g>"


def hound(cx, base=GROUND, s=1.0, look=0.0, scope=True):
    """A basset-style hound with long ears and, by default, a stethoscope."""
    h, coat = 175 * s, "#b9773e"
    y = lambda f: base - f * h
    parts = [shadow(cx, base, 0.36 * h),
             ellipse(cx - 0.12 * h, y(0.02), 0.10 * h, 0.04 * h, "#8a5528"), ellipse(cx + 0.12 * h, y(0.02), 0.10 * h, 0.04 * h, "#8a5528"),
             ellipse(cx, y(0.34), 0.26 * h, 0.32 * h, coat), ellipse(cx, y(0.30), 0.15 * h, 0.22 * h, "#f3e3cc"),
             rect(cx - 0.20 * h, y(0.62), 0.40 * h, 0.30 * h, SNOW, 10, extra='opacity="0.92"'),
             circle(cx, y(0.78), 0.19 * h, coat),
             ellipse(cx - 0.20 * h, y(0.70), 0.07 * h, 0.19 * h, "#7a4720", rot(14, cx - 0.2 * h, y(0.8))),
             ellipse(cx + 0.20 * h, y(0.70), 0.07 * h, 0.19 * h, "#7a4720", rot(-14, cx + 0.2 * h, y(0.8))),
             ellipse(cx, y(0.69), 0.11 * h, 0.08 * h, "#f3e3cc"), ellipse(cx, y(0.73), 0.045 * h, 0.03 * h, INK),
             eye(cx - 0.07 * h, y(0.82), 0.04 * h, look), eye(cx + 0.07 * h, y(0.82), 0.04 * h, look)]

    if scope:
        parts += [path(f"M{cx - 0.10 * h:.1f},{y(0.62):.1f} Q{cx - 0.16 * h:.1f},{y(0.40):.1f} {cx:.1f},{y(0.36):.1f}"
                       f" Q{cx + 0.16 * h:.1f},{y(0.40):.1f} {cx + 0.10 * h:.1f},{y(0.62):.1f}", stroke="#3b4a5c", sw=3.5 * s + 0.5),
                  line(cx, y(0.36), cx + 0.30 * h, y(0.44), "#3b4a5c", 3.5 * s + 0.5), circle(cx + 0.32 * h, y(0.44), 0.035 * h, "#c3cdd8")]

    return "\n".join(parts)


def fox(cx, base=GROUND, s=1.0, look=0.0, cap=True):
    h, coat = 180 * s, "#e07a32"
    y = lambda f: base - f * h
    parts = [shadow(cx, base, 0.34 * h),
             path(f"M{cx - 0.18 * h:.1f},{y(0.12):.1f} Q{cx - 0.62 * h:.1f},{y(0.18):.1f} {cx - 0.50 * h:.1f},{y(0.46):.1f}"
                  f" Q{cx - 0.36 * h:.1f},{y(0.30):.1f} {cx - 0.16 * h:.1f},{y(0.26):.1f} Z", coat),
             path(f"M{cx - 0.50 * h:.1f},{y(0.46):.1f} Q{cx - 0.55 * h:.1f},{y(0.36):.1f} {cx - 0.44 * h:.1f},{y(0.34):.1f} Z", SNOW),
             ellipse(cx - 0.10 * h, y(0.02), 0.08 * h, 0.035 * h, INK), ellipse(cx + 0.10 * h, y(0.02), 0.08 * h, 0.035 * h, INK),
             ellipse(cx, y(0.33), 0.22 * h, 0.31 * h, coat), ellipse(cx, y(0.30), 0.13 * h, 0.22 * h, SNOW),
             ellipse(cx - 0.23 * h, y(0.40), 0.05 * h, 0.13 * h, coat, rot(16, cx - 0.23 * h, y(0.5))),
             ellipse(cx + 0.23 * h, y(0.44), 0.05 * h, 0.13 * h, coat, rot(-56, cx + 0.22 * h, y(0.52))),
             path(f"M{cx - 0.18 * h:.1f},{y(0.82):.1f} L{cx - 0.15 * h:.1f},{y(1.04):.1f} L{cx - 0.03 * h:.1f},{y(0.90):.1f} Z", coat),
             path(f"M{cx + 0.18 * h:.1f},{y(0.82):.1f} L{cx + 0.15 * h:.1f},{y(1.04):.1f} L{cx + 0.03 * h:.1f},{y(0.90):.1f} Z", coat),
             circle(cx, y(0.76), 0.19 * h, coat),
             path(f"M{cx - 0.17 * h:.1f},{y(0.72):.1f} Q{cx:.1f},{y(0.50):.1f} {cx + 0.17 * h:.1f},{y(0.72):.1f} Q{cx:.1f},{y(0.66):.1f} {cx - 0.17 * h:.1f},{y(0.72):.1f} Z", SNOW),
             circle(cx, y(0.60), 0.028 * h, INK),
             eye(cx - 0.075 * h, y(0.79), 0.04 * h, look), eye(cx + 0.075 * h, y(0.79), 0.04 * h, look)]

    if cap:
        parts += [path(f"M{cx - 0.17 * h:.1f},{y(0.91):.1f} Q{cx:.1f},{y(1.05):.1f} {cx + 0.17 * h:.1f},{y(0.91):.1f} Z", "#2c4a6e"),
                  rect(cx - 0.05 * h, y(0.925), 0.30 * h, 0.03 * h, "#1d324c", 3)]

    return "\n".join(parts)


def hermit(cx, base=GROUND, s=1.0, look=0.0, shell="#c98a5a"):
    """A hermit crab in a spiral shell."""
    h = 150 * s
    y = lambda f: base - f * h
    spiral = path(f"M{cx - 0.05 * h:.1f},{y(0.55):.1f} a{0.12 * h:.1f},{0.12 * h:.1f} 0 1 1 {0.10 * h:.1f},{0.10 * h:.1f}"
                  f" a{0.22 * h:.1f},{0.22 * h:.1f} 0 1 1 {-0.30 * h:.1f},{-0.12 * h:.1f}", stroke="#8a5530", sw=4 * s)

    return "\n".join([
        shadow(cx, base, 0.42 * h),
        *[line(cx + 0.16 * h + 0.07 * h * k, y(0.22), cx + 0.24 * h + 0.08 * h * k, y(0.0), "#e2553f", 4 * s) for k in range(3)],
        ellipse(cx - 0.05 * h, y(0.50), 0.38 * h, 0.40 * h, shell), spiral,
        ellipse(cx + 0.32 * h, y(0.30), 0.16 * h, 0.13 * h, "#e2553f"),
        ellipse(cx + 0.52 * h, y(0.36), 0.09 * h, 0.07 * h, "#e2553f"),
        line(cx + 0.34 * h, y(0.42), cx + 0.32 * h, y(0.58), "#e2553f", 3 * s), line(cx + 0.42 * h, y(0.42), cx + 0.46 * h, y(0.58), "#e2553f", 3 * s),
        eye(cx + 0.32 * h, y(0.62), 0.045 * h, look), eye(cx + 0.46 * h, y(0.62), 0.045 * h, look),
    ])


def parrot(cx, base, s=1.0, body="#2fb36b", wing="#1d7fc6", face=1, look=0.5):
    """A parrot perched with its feet at `base`. `face` is 1 for right, -1 for left."""
    h = 110 * s
    y = lambda f: base - f * h
    f = face

    return "\n".join([
        path(f"M{cx - 0.06 * f * h:.1f},{y(0.20):.1f} L{cx - 0.20 * f * h:.1f},{y(-0.35):.1f} L{cx + 0.04 * f * h:.1f},{y(0.18):.1f} Z", wing),
        ellipse(cx, y(0.45), 0.20 * h, 0.32 * h, body),
        ellipse(cx - 0.06 * f * h, y(0.42), 0.12 * h, 0.24 * h, wing, rot(10 * f, cx, y(0.45))),
        circle(cx + 0.05 * f * h, y(0.80), 0.16 * h, body),
        circle(cx + 0.10 * f * h, y(0.84), 0.07 * h, SNOW), eye(cx + 0.11 * f * h, y(0.84), 0.04 * h, look * f),
        path(f"M{cx + 0.17 * f * h:.1f},{y(0.86):.1f} Q{cx + 0.32 * f * h:.1f},{y(0.84):.1f} {cx + 0.24 * f * h:.1f},{y(0.68):.1f}"
             f" L{cx + 0.17 * f * h:.1f},{y(0.74):.1f} Z", "#f6c33b"),
        line(cx - 0.05 * h, y(0.12), cx - 0.06 * h, y(0.0), "#6b5a48", 3), line(cx + 0.05 * h, y(0.12), cx + 0.06 * h, y(0.0), "#6b5a48", 3),
    ])


def sheepdog(cx, base=GROUND, s=1.0, look=0.0):
    """A black-and-white herding dog, standing on 4 legs and facing right."""
    h = 120 * s
    y = lambda f: base - f * h

    return "\n".join([
        shadow(cx, base, 0.55 * h),
        *[rect(cx + dx * h, y(0.42), 0.07 * h, 0.42 * h, INK if k % 2 else SNOW, 6) for k, dx in enumerate((-0.42, -0.28, 0.20, 0.33))],
        path(f"M{cx - 0.50 * h:.1f},{y(0.62):.1f} Q{cx - 0.82 * h:.1f},{y(0.75):.1f} {cx - 0.78 * h:.1f},{y(0.95):.1f}"
             f" Q{cx - 0.66 * h:.1f},{y(0.72):.1f} {cx - 0.48 * h:.1f},{y(0.56):.1f} Z", INK),
        ellipse(cx - 0.05 * h, y(0.62), 0.52 * h, 0.22 * h, INK), ellipse(cx + 0.24 * h, y(0.58), 0.20 * h, 0.17 * h, SNOW),
        circle(cx + 0.46 * h, y(0.88), 0.21 * h, INK),
        path(f"M{cx + 0.46 * h:.1f},{y(1.05):.1f} L{cx + 0.40 * h:.1f},{y(0.70):.1f} L{cx + 0.52 * h:.1f},{y(0.70):.1f} Z", SNOW),
        ellipse(cx + 0.66 * h, y(0.80), 0.14 * h, 0.08 * h, SNOW), circle(cx + 0.78 * h, y(0.81), 0.035 * h, INK),
        path(f"M{cx + 0.30 * h:.1f},{y(1.02):.1f} L{cx + 0.34 * h:.1f},{y(1.18):.1f} L{cx + 0.42 * h:.1f},{y(1.04):.1f} Z", INK),
        path(f"M{cx + 0.52 * h:.1f},{y(1.04):.1f} L{cx + 0.60 * h:.1f},{y(1.18):.1f} L{cx + 0.62 * h:.1f},{y(1.00):.1f} Z", INK),
        eye(cx + 0.52 * h, y(0.93), 0.05 * h, look),
    ])


def sheep(cx, base=GROUND, s=1.0, number=None):
    """A sheep facing right, with an optional number painted on its fleece."""
    h = 90 * s
    y = lambda f: base - f * h
    puffs = [circle(cx + dx * h, y(0.62 + dy), 0.20 * h, "#f4f1ea") for dx, dy in
             ((-0.36, 0.0), (-0.18, 0.12), (0.02, 0.14), (0.20, 0.08), (0.30, -0.04), (-0.26, -0.12), (0.0, -0.10), (0.18, -0.14))]
    parts = [shadow(cx, base, 0.5 * h), *[rect(cx + dx * h, y(0.36), 0.07 * h, 0.36 * h, INK, 3) for dx in (-0.32, -0.14, 0.10, 0.26)],
             *puffs, ellipse(cx + 0.52 * h, y(0.66), 0.15 * h, 0.20 * h, INK, rot(-20, cx + 0.52 * h, y(0.66))),
             eye(cx + 0.56 * h, y(0.72), 0.045 * h, 0.5), ellipse(cx + 0.42 * h, y(0.78), 0.08 * h, 0.04 * h, INK)]

    if number:
        parts.append(label(cx - 0.05 * h, y(0.56), number, 22 * s, "#c2432c", font=MONO))

    return "\n".join(parts)


def squirrel(cx, base=GROUND, s=1.0, look=0.0):
    h, coat = 130 * s, "#b86b33"
    y = lambda f: base - f * h

    return "\n".join([
        shadow(cx, base, 0.30 * h),
        path(f"M{cx - 0.10 * h:.1f},{y(0.10):.1f} Q{cx - 0.80 * h:.1f},{y(0.10):.1f} {cx - 0.52 * h:.1f},{y(0.80):.1f}"
             f" Q{cx - 0.30 * h:.1f},{y(1.10):.1f} {cx - 0.12 * h:.1f},{y(0.90):.1f} Q{cx - 0.40 * h:.1f},{y(0.70):.1f} {cx - 0.10 * h:.1f},{y(0.30):.1f} Z", "#a85d2a"),
        ellipse(cx, y(0.32), 0.18 * h, 0.28 * h, coat), ellipse(cx + 0.02 * h, y(0.28), 0.10 * h, 0.18 * h, "#f0d7b4"),
        circle(cx + 0.04 * h, y(0.72), 0.16 * h, coat),
        path(f"M{cx - 0.06 * h:.1f},{y(0.82):.1f} L{cx - 0.04 * h:.1f},{y(1.00):.1f} L{cx + 0.04 * h:.1f},{y(0.86):.1f} Z", coat),
        eye(cx + 0.09 * h, y(0.75), 0.045 * h, look), circle(cx + 0.19 * h, y(0.69), 0.025 * h, INK),
        ellipse(cx + 0.18 * h, y(0.44), 0.05 * h, 0.09 * h, coat, rot(-40, cx + 0.16 * h, y(0.48))),
    ])


def magpie(cx, base, s=1.0, look=0.6):
    """A magpie perched, facing left: black head and back, white belly, blue wing sheen."""
    h = 120 * s
    y = lambda f: base - f * h

    return "\n".join([
        path(f"M{cx + 0.10 * h:.1f},{y(0.30):.1f} L{cx + 0.70 * h:.1f},{y(0.05):.1f} L{cx + 0.72 * h:.1f},{y(0.14):.1f} L{cx + 0.16 * h:.1f},{y(0.40):.1f} Z", "#1d3a66"),
        ellipse(cx, y(0.46), 0.26 * h, 0.22 * h, INK), ellipse(cx - 0.04 * h, y(0.40), 0.16 * h, 0.13 * h, SNOW),
        ellipse(cx + 0.08 * h, y(0.50), 0.16 * h, 0.10 * h, "#2f5fa5", rot(-15, cx + 0.08 * h, y(0.5))),
        circle(cx - 0.22 * h, y(0.68), 0.13 * h, INK), eye(cx - 0.26 * h, y(0.70), 0.04 * h, -look),
        path(f"M{cx - 0.34 * h:.1f},{y(0.70):.1f} L{cx - 0.50 * h:.1f},{y(0.66):.1f} L{cx - 0.34 * h:.1f},{y(0.63):.1f} Z", "#3a3f47"),
        line(cx - 0.04 * h, y(0.26), cx - 0.06 * h, y(0.0), "#3a3f47", 3), line(cx + 0.06 * h, y(0.26), cx + 0.06 * h, y(0.0), "#3a3f47", 3),
    ])


def chameleon(cx, base, s=1.0, body="#4fb36a"):
    """A chameleon on a branch, facing right, with a curled tail."""
    h = 110 * s
    y = lambda f: base - f * h

    return "\n".join([
        path(f"M{cx - 0.40 * h:.1f},{y(0.40):.1f} Q{cx - 0.80 * h:.1f},{y(0.40):.1f} {cx - 0.80 * h:.1f},{y(0.10):.1f}"
             f" A{0.14 * h:.1f},{0.14 * h:.1f} 0 1 1 {cx - 0.56 * h:.1f},{y(0.12):.1f}", stroke=body, sw=0.10 * h),
        ellipse(cx - 0.05 * h, y(0.50), 0.42 * h, 0.24 * h, body),
        path(f"M{cx - 0.40 * h:.1f},{y(0.62):.1f} Q{cx - 0.05 * h:.1f},{y(0.86):.1f} {cx + 0.30 * h:.1f},{y(0.64):.1f}", stroke="#2f8a4a", sw=0.04 * h),
        *[line(cx + dx * h, y(0.36), cx + (dx + 0.04) * h, y(0.0), body, 0.06 * h) for dx in (-0.30, -0.10, 0.10, 0.24)],
        path(f"M{cx + 0.28 * h:.1f},{y(0.70):.1f} L{cx + 0.66 * h:.1f},{y(0.52):.1f} L{cx + 0.30 * h:.1f},{y(0.34):.1f} Z", body),
        path(f"M{cx + 0.20 * h:.1f},{y(0.70):.1f} L{cx + 0.38 * h:.1f},{y(0.92):.1f} L{cx + 0.40 * h:.1f},{y(0.66):.1f} Z", "#3d9c58"),
        circle(cx + 0.40 * h, y(0.56), 0.09 * h, "#3d9c58"), eye(cx + 0.42 * h, y(0.56), 0.05 * h, 0.8),
    ])


def hedgehog(cx, base=GROUND, s=1.0, look=0.0):
    h = 110 * s
    y = lambda f: base - f * h
    spikes = []

    for k in range(13):
        a = math.pi * (0.15 + 0.85 * k / 12)
        bx, by = cx - 0.05 * h + 0.48 * h * math.cos(a), y(0.40) - 0.40 * h * math.sin(a)
        spikes.append(path(f"M{bx - 0.06 * h:.1f},{by + 0.04 * h:.1f} L{bx + 0.18 * h * math.cos(a):.1f},{by - 0.18 * h * math.sin(a):.1f}"
                           f" L{bx + 0.06 * h:.1f},{by + 0.04 * h:.1f} Z", "#5d4632"))

    return "\n".join([
        shadow(cx, base, 0.6 * h), *spikes,
        ellipse(cx - 0.05 * h, y(0.36), 0.50 * h, 0.36 * h, "#7a5c40"),
        path(f"M{cx + 0.20 * h:.1f},{y(0.62):.1f} Q{cx + 0.70 * h:.1f},{y(0.40):.1f} {cx + 0.72 * h:.1f},{y(0.30):.1f}"
             f" Q{cx + 0.50 * h:.1f},{y(0.06):.1f} {cx + 0.18 * h:.1f},{y(0.10):.1f} Z", "#e7cfa8"),
        circle(cx + 0.74 * h, y(0.31), 0.05 * h, INK), eye(cx + 0.44 * h, y(0.40), 0.06 * h, look),
        ellipse(cx + 0.02 * h, y(0.02), 0.08 * h, 0.04 * h, "#5d4632"), ellipse(cx + 0.30 * h, y(0.02), 0.08 * h, 0.04 * h, "#5d4632"),
    ])


# --------------------------------------------------------------------- plates

COVER_W, COVER_H = 960, 1280
SERIF = "Georgia, Iowan Old Style, Times New Roman, serif"


@plate("cover", "", "", "", "The cover of GPU-Accelerated Kubernetes. At night in a harbour, a raccoon in a dark blue cape and its "
       "natural black mask stands at a ship's wheel on the deck of a container ship. The containers are stacked in rows, and "
       "each glows with a green GPU chip. A stork flies overhead carrying a bundle marked nvidia.com/gpu: 1, a hound listens to a "
       "server with a stethoscope on the dock, and 5 parrots sit on a ring-shaped perch on the mast.", size=(COVER_W, COVER_H))
def cover():
    parts = [backdrop(("#0a1424", "#1d3f66"), ("#163352", "#1d4166"), seed=7, size=(COVER_W, COVER_H)),
             circle(872, 410, 46, "#fff3c8"), circle(860, 400, 8, "#f0dca0"), circle(886, 424, 5, "#f0dca0"),
             label(70, 150, "GPU-ACCELERATED", 66, SNOW, "start", SANS, 800, 'letter-spacing="3"'),
             label(66, 268, "KUBERNETES", 118, "#dfe9f4", "start", SANS, 900, 'letter-spacing="2"'),
             label(70, 334, "Distributed GPU kernel and job scheduling,", 32, "#ffd36b", "start", SERIF, 400, 'font-style="italic"'),
             label(70, 374, "in a cloud native way", 32, "#ffd36b", "start", SERIF, 400, 'font-style="italic"'),
             rect(70, 394, 300, 4, "#ffd36b", 2)]

    # The sea and the ship's hull.
    parts += [rect(0, 960, COVER_W, 320, "#0f2a47"),
              *[path(f"M{x},{990 + 34 * k} q30,-12 60,0 t60,0", stroke="#2c5c86", sw=3, extra='opacity="0.6"')
                for k in range(8) for x in range(-40 + 50 * (k % 2), COVER_W, 220)],
              path("M90,850 L870,850 L810,1010 L150,1010 Z", "#a8392e"), rect(90, 838, 780, 18, "#6d2620", 4),
              label(480, 950, "kube-ship", 34, "#ffd9cf", font=MONO, weight=700)]

    # The cargo: 3 rows of containers, each holding a GPU.
    colours = ["#2f7f86", "#c89b3c", "#4d6fa8", "#7a4d8a", "#3e8a58", "#c2612d"]

    for row in range(3):
        for k in range(5 - row):
            x, y = 130 + 110 * k + 55 * row, 760 - 90 * row
            parts += [box(x, y, 100, 78, colours[(k + row * 2) % 6]), chip(x + 50, y + 39, 0.5, "", glow=True)]

    # The mast, its ring of parrots, and the stork.
    parts += [line(760, 838, 760, 470, "#5b4630", 10), line(700, 520, 820, 520, "#5b4630", 6),
              circle(760, 600, 70, "none", 'stroke="#b58a52" stroke-width="7"')]

    for k, (body, wing) in enumerate([("#2fb36b", "#1d7fc6"), ("#e8463c", "#2f6fd6"), ("#f2b632", "#2fa0a8"),
                                      ("#3aa0e0", "#f2c032"), ("#9b59d0", "#2fb36b")]):
        a = 2 * math.pi * k / 5 - math.pi / 2
        parts.append(parrot(760 + 70 * math.cos(a), 600 + 70 * math.sin(a) + 4, 0.42, body, wing, 1 if math.cos(a) >= 0 else -1))

    parts += [stork(330, 580, 0.55, "1 GPU")]

    # The captain at the wheel.
    parts += [wheel(680, 770, 40), raccoon(560, 850, 1.05, look=0.6, cape="#1f2f6b", arm=30)]

    # The dock with the hound.
    parts += [rect(0, 1120, 380, 160, "#5b4a38"), *[line(40 * k, 1120, 40 * k, 1280, "#4a3b2c", 3) for k in range(10)],
              server(220, 1000, 80, 112, "#55d17a"), hound(120, 1124, 0.6, look=0.8),
              heart(330, 990, 14), path("M300,960 l20,0 l8,-18 l10,34 l8,-16 l22,0", stroke="#ff5d73", sw=3)]

    parts += [label(890, 1236, "Go and Rust, from first principles", 26, "#dfe9f4", "end", SERIF, 400, 'font-style="italic"'),
              label(890, 1196, "ARPAN PATHAK", 30, SNOW, "end", SANS, 700, 'letter-spacing="3"')]

    return parts


@plate("intro", "I", "Introduction", "Bundle the stork", "Bundle, a stork, flies over a harbour at dusk carrying a cloth bundle "
       "marked nvidia.com/gpu: 1 towards a container ship. On the dock, a crane lowers a container that holds a glowing GPU chip.")
def intro():
    return [backdrop(**DOCK, seed=1),
            rect(0, 300, W, 120, "#1d4166"), path("M520,250 L900,250 L870,320 L550,320 Z", "#a8392e"),
            box(570, 190, 100, 60, "#2f7f86"), chip(620, 220, 0.42, "", True), box(680, 190, 100, 60, "#c89b3c"),
            line(830, 60, 830, 250, "#c89b3c", 8), line(700, 64, 900, 64, "#c89b3c", 8), line(740, 64, 740, 120, "#9aa5b1", 2),
            box(700, 120, 80, 46, "#4d6fa8"), chip(740, 143, 0.3, "", True),
            stork(250, 250, 0.9, "gpu: 1")]


@plate("ch01", "1", "A local copy of the cluster", "Ledger the owl", "Ledger, an owl in round glasses, sits at a desk between "
       "a large book of record on the left, whose lines are numbered v10, v11 and v12, and a small notebook on the right in "
       "which it copies each numbered line. A ribbon of paper carries events from the book to the notebook.")
def ch01():
    parts = [backdrop(**FLOOR, seed=2), rect(150, 250, 660, 24, "#7a5a3c", 4), rect(170, 274, 20, 50, "#5e432c"), rect(770, 274, 20, 50, "#5e432c")]
    parts += [rect(120, 70, 250, 180, "#f3ead6", 8, "#b9a98a", 3), label(245, 100, "API SERVER", 18, "#7a5a3c")]

    for k, text in enumerate(["v10  job-a  gpu: 1", "v11  job-a  gpu: 2", "v12  job-b  gpu: 8"]):
        parts.append(label(140, 140 + 36 * k, text, 17, "#3b2c1c", "start", MONO, 600))

    parts += [rect(600, 110, 210, 140, "#fffaf0", 8, "#c9b98f", 3), label(705, 138, "CACHE", 18, "#7a5a3c")]

    for k, text in enumerate(["job-a  v11", "job-b  v12"]):
        parts.append(label(620, 176 + 34 * k, text, 17, "#3b2c1c", "start", MONO, 600))

    parts += [path("M370,150 C440,90 530,90 600,150", stroke="#c89b3c", sw=3, extra='stroke-dasharray="7 6"'),
              tag(485, 104, "watch from v10"), owl(485, 254, 0.78, look=0.6)]

    return parts


@plate("ch01-1", "1.1", "A controller on a real cluster", "Rivet the beaver", "Rivet, a beaver in a hard hat, places a glowing "
       "GPU chip into an open pea pod. The pod holds 2 more peas shaped like containers, and a tag on the pod reads GpuJob train.")
def ch01_1():
    return [backdrop(**MEADOW, seed=3),
            path("M420,270 C470,180 760,170 820,250 C760,300 480,310 420,270 Z", "#7cc36b", "#4f8f45", 4),
            path("M440,262 C500,215 740,205 800,250", stroke="#4f8f45", sw=3),
            box(500, 222, 70, 44, "#2f7f86"), box(600, 214, 70, 44, "#c89b3c"), chip(720, 238, 0.45, "", True),
            tag(620, 170, "GpuJob train"), beaver(300, GROUND, 1.0, look=0.7)]


@plate("ch02", "2", "What one GPU means", "Comb and the hive", "8 hexagonal cells of a honeycomb are labelled SM 0 to SM 7. "
       "Bees fill the cells in rows of 32, and a lead bee named Comb carries a card that reads 1 unit = the whole GPU.")
def ch02():
    parts = [backdrop(("#2a1d0e", "#7a5419"), ("#5a3d18", "#7a5622"), seed=4, stars=False)]

    for k in range(8):
        cx, cy = 300 + 92 * (k % 4) + (46 if k >= 4 else 0), 110 + 80 * (k // 4)
        parts += [hexagon(cx, cy, 50, "#f6c445", "#b07d14", 4), label(cx, cy - 8, f"SM {k}", 16, "#5a3d10", font=MONO)]
        parts += [circle(cx - 18 + 12 * j, cy + 14, 4, INK) for j in range(4)]

    parts += [bee(170, 140, 1.6, -8), rect(80, 200, 220, 60, "#fff6d6", 10, "#b07d14", 3),
              label(190, 226, "1 unit =", 18, "#5a3d10", font=MONO), label(190, 250, "the whole GPU", 18, "#5a3d10", font=MONO),
              bee(820, 90, 0.9, 10), bee(860, 230, 0.8, -12)]

    return parts


@plate("ch03", "3", "Which machines are alive", "Doc the hound", "Doc, a hound in a white coat, listens to a rack of servers "
       "with a stethoscope. A monitor above shows a regular heartbeat line for 2 servers and a flat line for the third, whose "
       "lamp is red.")
def ch03():
    parts = [backdrop(**FLOOR, seed=5)]

    for k, (lamp, name) in enumerate([("#55d17a", "thor-1"), ("#55d17a", "thor-2"), ("#ff5d5d", "thor-3")]):
        parts.append(server(470 + 110 * k, 200, 90, 120, lamp, name))

    parts += [rect(470, 70, 310, 100, "#0f1722", 8, "#56657a", 2),
              path("M480,105 h40 l10,-22 l12,44 l10,-22 h30 l10,-22 l12,44 l10,-22 h30", stroke="#55d17a", sw=3),
              path("M480,145 h40 l10,-18 l12,36 l10,-18 h30 l10,-18 l12,36 l10,-18 h30", stroke="#55d17a", sw=3),
              line(680, 120, 770, 120, "#ff5d5d", 3), label(725, 108, "thor-3", 13, "#ff9a9a", font=MONO),
              hound(300, GROUND, 1.0, look=0.8), heart(410, 80, 16)]

    return parts


@plate("ch04", "4", "A control plane for a fleet", "Sergeant Cone the raccoon", "Sergeant Cone, a raccoon in a police cap, "
       "directs traffic at a crossing with a raised paw and a whistle. A traffic light beside it shows green for healthy, amber "
       "for cordoned and red for quarantined. A server with a red lamp stands inside a ring of orange cones.")
def ch04():
    parts = [backdrop(("#14243a", "#3b5878"), ("#4a4f57", "#5f656e"), seed=6),
             *[rect(80 + 120 * k, 340, 70, 10, "#e8e1c8", 2) for k in range(8)],
             rect(170, 90, 56, 150, "#20293a", 10), circle(198, 118, 18, "#ff5d5d"), circle(198, 165, 18, "#ffbd2e"), circle(198, 212, 18, "#55d17a"),
             rect(192, 240, 12, 80, "#3a4656"),
             label(240, 124, "quarantine", 16, "#ffb0b0", "start", MONO, 600), label(240, 171, "cordon", 16, "#ffe0a0", "start", MONO, 600),
             label(240, 218, "healthy", 16, "#b8f0c8", "start", MONO, 600),
             server(660, 180, 90, 120, "#ff5d5d", "thor-4"), cone(615, 318), cone(795, 318), cone(705, 336, 0.8),
             raccoon(470, GROUND, 1.0, look=0.7, cap=True, arm=70), circle(526, 196, 8, "#c3cdd8")]

    return parts


@plate("ch05", "5", "Kubernetes in a new account", "Badge the fox", "Badge, a fox in a guard's cap, stands at a gate and "
       "hands an ID card to a new server that has arrived with a short-lived ticket. The card reads system:node:thor-3.")
def ch05():
    return [backdrop(**FOREST, seed=8),
            rect(120, 120, 22, 210, "#c9ccd1"), rect(320, 120, 22, 210, "#c9ccd1"),
            path("M142,140 L320,140", stroke="#d9622b", sw=10, extra='stroke-dasharray="22 14"'),
            label(231, 110, "CLUSTER GATE", 18, SNOW),
            fox(430, GROUND, 1.0, look=0.8),
            rect(520, 178, 150, 70, "#fffaf0", 8, "#c9b98f", 3), label(595, 206, "system:node:", 14, "#3b2c1c", font=MONO),
            label(595, 228, "thor-3", 18, "#3b2c1c", font=MONO),
            server(720, 200, 90, 120, "#ffbd2e", "new"), tag(765, 176, "token 10m", "#ffe0a0")]


@plate("ch06", "6", "Virtual machines", "Shellby the hermit crab", "Shellby, a hermit crab, moves from an old shell on the left to "
       "a new shell on the right while carrying a stack of memory pages. A thin line of pages already sits in the new shell, and "
       "the last few pages fly across.")
def ch06():
    parts = [backdrop(**SAND, seed=9),
             ellipse(200, 270, 120, 70, "#a77b52"), label(200, 280, "host A", 18, "#3b2c1c", font=MONO),
             ellipse(780, 260, 130, 80, "#d8a36e"), label(780, 270, "host B", 18, "#3b2c1c", font=MONO)]
    parts += [rect(730 + 14 * k, 180 - 8 * k, 46, 30, "#e8c877", 4, "#a57f2c", 2) for k in range(3)]
    parts += [rect(520 + 40 * k, 120 - 18 * k, 34, 24, "#e8c877", 4, "#a57f2c", 2, rot(-10 + 8 * k, 537 + 40 * k, 132 - 18 * k)) for k in range(3)]
    parts += [hermit(430, GROUND, 1.0, look=0.7)]

    return parts


@plate("ch07", "7", "Collective communication", "The ring parrots", "5 parrots of different colours sit on a ring-shaped perch. "
       "Each passes a seed to its right-hand neighbour, and the seeds carry the partial sums 1, 3, 6, 10 and 15.")
def ch07():
    parts = [backdrop(**FOREST, seed=10), circle(480, 190, 120, "none", 'stroke="#b58a52" stroke-width="10"'),
             line(480, 310, 480, 340, "#7a5a3c", 12)]
    birds = [("#2fb36b", "#1d7fc6"), ("#e8463c", "#2f6fd6"), ("#f2b632", "#2fa0a8"), ("#3aa0e0", "#f2c032"), ("#9b59d0", "#2fb36b")]

    for k, (body, wing) in enumerate(birds):
        a = 2 * math.pi * k / 5 - math.pi / 2
        x, y = 480 + 120 * math.cos(a), 190 + 120 * math.sin(a)
        parts.append(parrot(x, y + 4, 0.62, body, wing, 1 if math.cos(a) >= -0.01 else -1))

    for k, text in enumerate(["1", "3", "6", "10", "15"]):
        a = 2 * math.pi * (k + 0.5) / 5 - math.pi / 2
        parts.append(tag(480 + 170 * math.cos(a), 190 + 150 * math.sin(a), text, "#f2e2b0"))

    return parts


@plate("ch08", "8", "Placing jobs on GPUs", "Flock the sheepdog", "Flock, a sheepdog, herds 5 sheep numbered 1 to 5 together "
       "into 1 pen labelled shelf. A second pen labelled desk holds 2 sheep, and a gate stays closed until the whole flock is in.")
def ch08():
    parts = [backdrop(**MEADOW, seed=11),
             rect(470, 170, 400, 150, "none", 6, "#8a6a44", 6), label(670, 160, "shelf: 5 Thors", 18, SNOW, font=MONO),
             rect(60, 210, 220, 110, "none", 6, "#8a6a44", 6), label(170, 200, "desk: 2 Sparks", 18, SNOW, font=MONO)]
    parts += [sheep(520 + 70 * k, 300 - 18 * (k % 2), 0.7, str(k + 1)) for k in range(5)]
    parts += [sheep(120, 300, 0.6), sheep(210, 296, 0.6), sheepdog(370, GROUND, 0.9, look=0.8)]

    return parts


@plate("ch09", "9", "Counting across replicas", "The tally squirrels", "3 squirrels sit under 3 trees named shelf, desk and "
       "bench. Each holds a slate with a row of 3 numbers. After they compare slates, all 3 rows read 360, 120, 65.")
def ch09():
    parts = [backdrop(**FOREST, seed=12)]

    for k, (name, row) in enumerate([("shelf", "360 120 65"), ("desk", "360 120 65"), ("bench", "360 120 65")]):
        x = 170 + 310 * k
        parts += [rect(x - 14, 120, 28, 200, "#6b4a2e"), circle(x, 110, 80, "#3f7a46"), circle(x - 50, 140, 50, "#4a8a50"),
                  circle(x + 50, 140, 50, "#4a8a50"), label(x, 60, name, 20, SNOW, font=MONO),
                  rect(x + 30, 214, 120, 46, "#2b3646", 6, "#8a6a44", 3), label(x + 90, 244, row, 15, "#e9f4ff", font=MONO),
                  squirrel(x - 20, GROUND, 0.75, look=0.7)]

    return parts


@plate("ch10", "10", "A content-addressed store", "Hash the magpie", "Hash, a magpie, perches on a cabinet of small drawers. "
       "Every drawer is labelled with the first digits of a sha256 digest, and the magpie drops a shiny chunk into the drawer "
       "whose label matches it.")
def ch10():
    parts = [backdrop(**FLOOR, seed=13), rect(420, 90, 400, 230, "#8a6a44", 8, "#5e432c", 4)]
    names = ["a6a98d", "3f0c1e", "9be244", "c41d07", "77ab90", "e2f531", "08c6aa", "5d7b3e"]

    for k, name in enumerate(names):
        x, y = 440 + 95 * (k % 4), 110 + 104 * (k // 4)
        parts += [rect(x, y, 85, 90, "#c89b3c", 6, "#7a5a3c", 3), circle(x + 42, y + 60, 6, "#7a5a3c"),
                  label(x + 42, y + 30, name, 14, "#3b2c1c", font=MONO)]

    parts += [magpie(250, 200, 1.1), sparkle(140, 150, 14, "#d9e8ff"), sparkle(470, 70, 10, "#ffe9a8"),
              rect(150, 196, 40, 40, "#cfe3ff", 6, "#7d9cc6", 2), label(170, 222, "8K", 14, "#21406a", font=MONO)]

    return parts


@plate("ch11", "11", "A tool for 3 systems", "Chroma the chameleon", "Chroma, a chameleon, sits on a branch above 3 terminals "
       "labelled linux, macos and windows. Each terminal shows the same gpuctl nodes command, and the chameleon's colour shifts "
       "from green to blue to orange along its body.")
def ch11():
    parts = [backdrop(**FOREST, seed=14), path("M80,150 Q480,110 880,150", stroke="#6b4a2e", sw=14)]

    for k, (name, glow) in enumerate([("linux", "#55d17a"), ("macos", "#9fc4ff"), ("windows", "#ffb36b")]):
        parts.append(screen(110 + 260 * k, 190, 220, 120, ["$ gpuctl nodes", "gpu-lab  1 GPU", f"os: {name}"], name))

    parts += [chameleon(480, 146, 1.0, "#4fb36a")]

    return parts


@plate("appendix", "A", "A local GPU cluster", "Kindle the hedgehog", "Kindle, a hedgehog, plugs a small GPU board into a "
       "shipping container labelled kind node. A cable runs from the board to the container, and a lamp on the container turns green.")
def appendix():
    return [backdrop(**FLOOR, seed=15), box(500, 150, 300, 160, "#2f7f86", "kind node"), circle(780, 170, 9, "#55d17a"),
            rect(330, 200, 110, 80, "#1f2a1a", 6, GPU_GREEN, 3), chip(385, 240, 0.5, "", True),
            path("M440,240 C470,240 470,230 500,230", stroke="#c3cdd8", sw=5), hedgehog(220, GROUND, 1.0, look=0.7)]


def main(names):
    OUT.mkdir(parents=True, exist_ok=True)

    for name in names or list(PLATES):
        number, title, crew, description, draw, size = PLATES[name]
        parts = draw()

        if number:
            parts.append(ribbon(number, title, crew, size))

        (OUT / (name + ".svg")).write_text(
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size[0]} {size[1]}" width="{size[0]}" height="{size[1]}" role="img"'
            f' aria-label="{escape(description)}">\n' + "\n".join(parts) + "\n</svg>\n")
        print("  " + name)

    (OUT / "plates.json").write_text(json.dumps({name: p[3] for name, p in PLATES.items()}, indent=2) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
