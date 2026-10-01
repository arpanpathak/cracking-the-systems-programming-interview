#!/usr/bin/env python3
"""Flag badly placed arrows in the hand-drawn SVG figures.

    python3 tools/lint_arrows.py                 # every figure in src/figures
    python3 tools/lint_arrows.py ch03-*.svg      # a selection

An arrow in these figures is a <line> whose end carries a small <polygon>
head. For each one the checker reports:

  * skew: the shaft is almost, but not quite, horizontal or vertical. A pointer
    from one box to another that drops 6 pixels over 260 reads as a mistake.
  * floating tip: the head stops short of every box, or overshoots into one.
  * loose tail: the tail starts in empty space, away from any box.
  * crossing: the shaft passes through a box that is neither its source nor its
    target.

The boxes are the <rect> elements of the figure. A figure where an arrow is
meant to point at text or at nothing can be listed in ALLOW with a reason.
"""

from __future__ import annotations

import math
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIGURES = ROOT / "src" / "figures"
NS = "{http://www.w3.org/2000/svg}"

SKEW_DEG = 9.0        # a shaft within this many degrees of an axis, but not on it
TOUCH = 7.5           # how close a tip or tail must be to a box edge (link() leaves 6)
ALLOW: dict[str, str] = {}


def num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def boxes(root):
    out = []
    for r in root.iter(NS + "rect"):
        w, h = num(r.get("width")), num(r.get("height"))
        if w <= 0 or h <= 0:
            continue
        x, y = num(r.get("x")), num(r.get("y"))
        if w >= 600 and h >= 120:       # the canvas background
            continue
        out.append((x, y, x + w, y + h))
    return out


def arrows(root):
    lines = [(num(l.get("x1")), num(l.get("y1")), num(l.get("x2")), num(l.get("y2")))
             for l in root.iter(NS + "line")]
    heads = []
    for poly in root.iter(NS + "polygon"):
        pts = [tuple(map(float, p.split(","))) for p in poly.get("points", "").split()
               if "," in p]
        if len(pts) == 3:
            heads.append(pts[0])
    out = []
    for x1, y1, x2, y2 in lines:
        if any(abs(hx - x2) < 0.6 and abs(hy - y2) < 0.6 for hx, hy in heads):
            out.append((x1, y1, x2, y2))
    return out


def dist_to_box(px, py, b):
    x0, y0, x1, y1 = b
    dx = max(x0 - px, 0, px - x1)
    dy = max(y0 - py, 0, py - y1)
    return math.hypot(dx, dy)


def inside(px, py, b, margin=0.0):
    x0, y0, x1, y1 = b
    return x0 + margin < px < x1 - margin and y0 + margin < py < y1 - margin


def crosses(seg, b, shrink=3.0):
    """Whether the segment passes through the inside of box b."""
    x0, y0, x1, y1 = b[0] + shrink, b[1] + shrink, b[2] - shrink, b[3] - shrink
    if x1 <= x0 or y1 <= y0:
        return False
    (ax, ay, bx, by) = seg
    steps = 60
    for i in range(1, steps):
        t = i / steps
        px, py = ax + (bx - ax) * t, ay + (by - ay) * t
        if x0 < px < x1 and y0 < py < y1:
            return True
    return False


def contains(outer, inner):
    return (outer != inner and outer[0] <= inner[0] and outer[1] <= inner[1]
            and outer[2] >= inner[2] and outer[3] >= inner[3])


def check(path):
    root = ET.parse(path).getroot()
    every = boxes(root)
    # A box that holds other boxes is a region (user mode, a stack frame), not a
    # target: arrows run inside it on purpose.
    regions = {b for b in every if any(contains(b, o) for o in every)}
    bx = [b for b in every if b not in regions]
    found = []
    for seg in arrows(root):
        x1, y1, x2, y2 = seg
        length = math.hypot(x2 - x1, y2 - y1)
        if length < 6:
            continue
        ang = abs(math.degrees(math.atan2(y2 - y1, x2 - x1))) % 90
        off_axis = min(ang, 90 - ang)
        if 0.4 < off_axis < SKEW_DEG and length > 30:
            found.append("skew %.1f deg: (%g, %g) -> (%g, %g)" % (off_axis, x1, y1, x2, y2))
        tip = [b for b in bx if dist_to_box(x2, y2, b) <= TOUCH]
        if bx and not tip:
            found.append("floating tip at (%g, %g)" % (x2, y2))
        deep = [b for b in bx if inside(x2, y2, b, margin=TOUCH)]
        if deep:
            found.append("tip buried inside a box at (%g, %g)" % (x2, y2))
        src = [b for b in bx if dist_to_box(x1, y1, b) <= TOUCH or inside(x1, y1, b)]
        if bx and not src:
            found.append("loose tail at (%g, %g)" % (x1, y1))
        ends = set(src) | set(tip)
        for b in bx:
            if b not in ends and crosses(seg, b):
                found.append("shaft (%g, %g) -> (%g, %g) crosses box at (%g, %g)"
                             % (x1, y1, x2, y2, b[0], b[1]))
                break
    return found


def main(argv):
    names = argv or None
    files = sorted(FIGURES.glob("*.svg"))
    if names:
        files = [f for f in files if any(f.match(n) for n in names)]
    flagged = total = 0
    for f in files:
        if f.name in ALLOW:
            continue
        problems = check(f)
        if problems:
            flagged += 1
            total += len(problems)
            for p in problems:
                print("%s: %s" % (f.name, p))
    print("%d/%d figures flagged, %d arrow findings" % (flagged, len(files), total))
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
