#!/usr/bin/env python3
"""Flag labels that overflow or collide in the SVG figures.

    python3 tools/lint_figures.py                  # every figure in src/figures
    python3 tools/lint_figures.py ch03-*.svg ...   # a selection

Two families of figure are checked the same way:

  * the hand-drawn figures, written by `tools/draw_chNN.py`
  * the Graphviz figures, rendered from `diagrams/*.dot`

For each run of text the checker estimates the box the glyphs occupy, after
applying the transforms on the enclosing `<g>` elements, and reports:

  * a box that leaves the viewBox (text spilling off the canvas)
  * two boxes that overlap by more than a quarter of the smaller one
  * a box crossed by a line or an arrow shaft

The advance width is Menlo's for a monospace label and an average for the
sans-serif face. The estimate is deliberately a little generous: a label the
linter clears will fit.
"""

from __future__ import annotations

import math
import os
import pathlib
import re
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIGURES = ROOT / "src" / "figures"

# Fallback advance widths, as a fraction of the font size, for a machine with
# none of the fonts below. Menlo is monospace, so its ratio is exact; the
# sans-serif figure is a conservative average.
MONO_RATIO = 0.601
SANS_RATIO = 0.50
ASCENT, DESCENT = 0.78, 0.22
# Digits, capitals, and most punctuation sit on the baseline. Only these glyphs
# reach below it, so only a label containing one of them needs a descender.
DESCENDERS = set("gjpqy,;()[]{}@_|")
DIGIT_DESCENT = 0.03
# A circle narrower than this is decoration, such as the hub of a drawn gear,
# not a badge that is meant to hold a label.
MIN_BADGE_RADIUS = 7.0
SVG = "{http://www.w3.org/2000/svg}"

# The faces the figures ask for, in the order the renderer would find them.
SANS_FONTS = [
    "/System/Library/Fonts/Helvetica.ttc",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
MONO_FONTS = [
    "/System/Library/Fonts/Menlo.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
]


def _load_font(candidates, size=100):
    try:
        from PIL import ImageFont
    except ImportError:
        return None
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return None


_FONTS = {}

IDENTITY = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def mul(m, n):
    """Compose two affine matrices, `m` applied after `n`."""
    a1, b1, c1, d1, e1, f1 = m
    a2, b2, c2, d2, e2, f2 = n
    return (
        a1 * a2 + c1 * b2,
        b1 * a2 + d1 * b2,
        a1 * c2 + c1 * d2,
        b1 * c2 + d1 * d2,
        a1 * e2 + c1 * f2 + e1,
        b1 * e2 + d1 * f2 + f1,
    )


def apply(m, x, y):
    a, b, c, d, e, f = m
    return a * x + c * y + e, b * x + d * y + f


TOKEN = re.compile(r"(translate|scale|rotate|matrix)\s*\(([^)]*)\)")


def parse_transform(value: str):
    m = IDENTITY
    for name, raw in TOKEN.findall(value or ""):
        nums = [float(v) for v in re.split(r"[\s,]+", raw.strip()) if v]
        if name == "translate":
            t = (1, 0, 0, 1, nums[0], nums[1] if len(nums) > 1 else 0)
        elif name == "scale":
            sx = nums[0]
            sy = nums[1] if len(nums) > 1 else sx
            t = (sx, 0, 0, sy, 0, 0)
        elif name == "rotate":
            a = math.radians(nums[0])
            t = (math.cos(a), math.sin(a), -math.sin(a), math.cos(a), 0, 0)
            if len(nums) == 3:
                t = mul((1, 0, 0, 1, nums[1], nums[2]), mul(t, (1, 0, 0, 1, -nums[1], -nums[2])))
        else:  # matrix
            t = tuple(nums[:6]) if len(nums) >= 6 else IDENTITY
        m = mul(m, t)
    return m


def width_of(s: str, size: float, mono: bool) -> float:
    """Advance width of `s` at `size`, from real font metrics where possible."""
    key = "mono" if mono else "sans"
    if key not in _FONTS:
        _FONTS[key] = _load_font(MONO_FONTS if mono else SANS_FONTS)
    font = _FONTS[key]
    widest = 0.0
    for line in str(s).split("\n"):
        if font is not None:
            # The font is loaded at 100 pt, so scale the measurement to `size`.
            widest = max(widest, font.getlength(line) * size / 100.0)
        else:
            widest = max(widest, len(line) * size * (MONO_RATIO if mono else SANS_RATIO))
    return widest


class Label:
    def __init__(self, x, y, text, size, anchor, mono, order=0):
        w = width_of(text, size, mono)
        if anchor == "middle":
            x0 = x - w / 2
        elif anchor == "end":
            x0 = x - w
        else:
            x0 = x
        self.text, self.size, self.order = text, size, order
        self.x0, self.x1 = x0, x0 + w

        # Only some glyphs reach below the baseline. Applying a full descender to
        # a label of digits moves its lower edge past where the ink actually is,
        # which would report a label that fits as spilling out of its box.
        descent = DESCENT if any(ch in DESCENDERS for ch in text) else DIGIT_DESCENT
        self.y0, self.y1 = y - ASCENT * size, y + descent * size

    def overlap(self, other: "Label") -> float:
        dx = min(self.x1, other.x1) - max(self.x0, other.x0)
        dy = min(self.y1, other.y1) - max(self.y0, other.y0)
        if dx <= 0 or dy <= 0:
            return 0.0
        small = min((self.x1 - self.x0) * (self.y1 - self.y0), (other.x1 - other.x0) * (other.y1 - other.y0))
        return (dx * dy) / small if small else 0.0


def segment_hits_box(x1, y1, x2, y2, box, shrink=1.5) -> bool:
    x0, y0, x3, y3 = box[0] + shrink, box[1] + shrink, box[2] - shrink, box[3] - shrink
    if x3 <= x0 or y3 <= y0:
        return False
    dx, dy = x2 - x1, y2 - y1
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x1 - x0), (dx, x3 - x1), (-dy, y1 - y0), (dy, y3 - y1)):
        if p == 0:
            if q < 0:
                return False
        else:
            r = q / p
            if p < 0:
                t0 = max(t0, r)
            else:
                t1 = min(t1, r)
            if t0 > t1:
                return False
    return True


def tag(elem) -> str:
    return elem.tag.replace(SVG, "") if isinstance(elem.tag, str) else ""


def flatten(elem, m=IDENTITY):
    """Yield (element, accumulated transform) in paint order, parents first."""
    m = mul(m, parse_transform(elem.get("transform", "")))
    yield elem, m
    for child in list(elem):
        yield from flatten(child, m)


MONO_MARKERS = ("mono", "menlo", "courier", "consol", "dejavu sans mono", "liberation mono")


def is_mono(family: str) -> bool:
    low = (family or "").lower()
    return any(marker in low for marker in MONO_MARKERS)


def collect_text(elem, m, labels: list[Label], order: int = 0) -> None:
    # A halo is a white copy of the glyphs drawn under the real ones, so it is a
    # duplicate of one label rather than a label of its own.
    if elem.get("data-halo"):
        return
    anchor = elem.get("text-anchor", "start")
    mono = is_mono(elem.get("font-family"))
    # A font-size inside a scaled group renders smaller by that factor, so the
    # glyph box has to be measured at the scaled size.
    factor = scale_of(m)
    size = float(elem.get("font-size", 11)) * factor
    tspans = [c for c in list(elem) if tag(c) == "tspan"]
    if tspans:
        for span in tspans:
            content = "".join(span.itertext()).strip()
            if not content:
                continue
            sx = span.get("x", elem.get("x", "0"))
            sy = span.get("y", elem.get("y", "0"))
            own = span.get("font-size")
            ssize = float(own) * factor if own else size
            x, y = apply(m, float(sx), float(sy))
            labels.append(Label(x, y, content, ssize, anchor, mono, order))
        return
    content = "".join(elem.itertext()).strip()
    if not content:
        return
    x, y = apply(m, float(elem.get("x", 0)), float(elem.get("y", 0)))
    labels.append(Label(x, y, content, size, anchor, mono, order))


def num(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def scale_of(m):
    a, b, c, d, _, _ = m
    return math.sqrt(abs(a * d - b * c)) or 1.0


def parse_points(raw):
    out = []
    for token in re.split(r"[\s]+", (raw or "").strip()):
        if not token:
            continue
        parts = [num(v) for v in re.split(r"[,\s]+", token) if v]
        if len(parts) >= 2 and parts[0] is not None and parts[1] is not None:
            out.append((parts[0], parts[1]))
    return out


def dist(p, q):
    return math.hypot(p[0] - q[0], p[1] - q[1])


def arrow_tip(points):
    """For a triangle, return (tip, base_mid).

    The tip is the vertex whose distance to the midpoint of the other two is
    greatest, which is the height of the triangle from that vertex. For a narrow
    arrowhead the base is shorter than the two sides, so choosing the vertex
    opposite the longest edge would return a base corner, not the tip.
    """
    if len(points) != 3:
        return None, None
    best, best_height = None, -1.0
    for i, p in enumerate(points):
        others = [q for j, q in enumerate(points) if j != i]
        mid = ((others[0][0] + others[1][0]) / 2.0, (others[0][1] + others[1][1]) / 2.0)
        height = dist(p, mid)
        if height > best_height:
            best, best_height = p, height
    base = [q for q in points if q != best]
    if len(base) != 2:
        return None, None
    return best, ((base[0][0] + base[1][0]) / 2.0, (base[0][1] + base[1][1]) / 2.0)


def check(path: pathlib.Path) -> list[str]:
    raw_svg = path.read_text(encoding="utf-8")
    graphviz = "Generated by graphviz" in raw_svg
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        return ["unparseable SVG: %s" % exc]
    root = tree.getroot()

    vb = root.get("viewBox")
    if not vb:
        return ["no viewBox"]
    nums = [float(v) for v in re.split(r"[\s,]+", vb.strip()) if v]
    if len(nums) != 4:
        return ["bad viewBox %r" % vb]
    W, H = nums[2], nums[3]

    labels: list[Label] = []
    lines: list[tuple[float, float, float, float, int]] = []
    rects: list[tuple[float, float, float, float, int]] = []
    heads: list[tuple[tuple[float, float], tuple[float, float], int]] = []
    for order, (node, m) in enumerate(flatten(root)):
        name = tag(node)
        if name == "text":
            collect_text(node, m, labels, order)
        elif name == "line":
            p1 = apply(m, float(node.get("x1", 0)), float(node.get("y1", 0)))
            p2 = apply(m, float(node.get("x2", 0)), float(node.get("y2", 0)))
            lines.append((p1[0], p1[1], p2[0], p2[1], order))
        elif name == "rect":
            # A dimming panel is a whole-canvas wash, not a box that owns a label.
            if node.get("data-scrim"):
                continue
            w, h = num(node.get("width")), num(node.get("height"))
            if w is None or h is None:
                continue
            s = scale_of(m)
            x0, y0 = apply(m, num(node.get("x"), 0.0), num(node.get("y"), 0.0))
            rects.append((x0, y0, x0 + w * s, y0 + h * s, order))
        elif name == "circle":
            r = num(node.get("r"))
            # A circle counts as a label's box only when it is big enough to hold
            # one: a graph node or a legend swatch. A smaller circle, such as the
            # hub of a drawn gear, is decoration that a label may sit across.
            if not r or r > 40 or r < MIN_BADGE_RADIUS:
                continue
            s = scale_of(m)
            cx, cy = apply(m, num(node.get("cx"), 0.0), num(node.get("cy"), 0.0))
            rects.append((cx - r * s, cy - r * s, cx + r * s, cy + r * s, order))
        elif name == "polygon":
            pts = [apply(m, px, py) for px, py in parse_points(node.get("points"))]
            if pts:
                span = max(max(p[0] for p in pts) - min(p[0] for p in pts),
                           max(p[1] for p in pts) - min(p[1] for p in pts))
                # A small triangle is an arrowhead. A larger one is a drawn shape,
                # such as the gate in a plate, and is not checked as an arrow.
                if span <= 18.0:
                    tip, mid = arrow_tip(pts)
                    if tip is not None:
                        heads.append((tip, mid, order))

    problems: list[str] = []
    for lab in labels:
        if lab.x0 < -1 or lab.x1 > W + 1:
            problems.append("overflow-x  x=[%.0f,%.0f] of %.0f  %r" % (lab.x0, lab.x1, W, lab.text[:46]))
        if lab.y0 < -1 or lab.y1 > H + 1:
            problems.append("overflow-y  y=[%.0f,%.0f] of %.0f  %r" % (lab.y0, lab.y1, H, lab.text[:46]))
    for i, a in enumerate(labels):
        for b in labels[i + 1:]:
            tight = a.overlap(b)
            # A figure may draw the same label twice to change its box, for
            # example a node redrawn with a highlight. That is an overdraw, not
            # two labels competing for the same space.
            if tight > 0.85 and a.text == b.text:
                continue
            if tight > 0.25:
                problems.append("collision   %r / %r" % (a.text[:26], b.text[:26]))
    for lab in labels:
        for x1, y1, x2, y2, line_order in lines:
            # A line drawn before the label cannot obscure it.
            if line_order < lab.order:
                continue
            if segment_hits_box(x1, y1, x2, y2, (lab.x0, lab.y0, lab.x1, lab.y1)):
                problems.append("line-through  %r" % lab.text[:40])
                break

    # A label that belongs to a box but is not fully inside it is spilling out.
    # Two ways to tell that a box belongs to the label: the label's centre sits
    # in the box, or the label covers most of the box's area. The second catches
    # a label wider than its box, whose centre has drifted past the edge.
    labelled: set = set()
    for lab in labels:
        cx, cy = (lab.x0 + lab.x1) / 2.0, (lab.y0 + lab.y1) / 2.0
        for x0, y0, x1, y1, _order in rects:
            if x1 <= x0 or y1 <= y0:
                continue
            centred = x0 + 2 < cx < x1 - 2 and y0 + 2 < cy < y1 - 2
            if not centred:
                ox = min(lab.x1, x1) - max(lab.x0, x0)
                oy = min(lab.y1, y1) - max(lab.y0, y0)
                if ox <= 0 or oy <= 0 or (ox * oy) < 0.6 * (x1 - x0) * (y1 - y0):
                    continue
            labelled.add((x0, y0, x1, y1))
            over = []
            if lab.x0 < x0 - 1:
                over.append("left %.0f" % (x0 - lab.x0))
            if lab.x1 > x1 + 1:
                over.append("right %.0f" % (lab.x1 - x1))
            if lab.y0 < y0 - 1:
                over.append("top %.0f" % (y0 - lab.y0))
            if lab.y1 > y1 + 1:
                over.append("bottom %.0f" % (lab.y1 - y1))
            if over:
                problems.append("spills-box  %s  %r" % (", ".join(over), lab.text[:40]))
                break

    # Arrowheads: the tip must sit on the shaft, and the head must point the way
    # the shaft travels. Graphviz draws edges as bezier paths, which are skipped.
    if not graphviz:
        for tip, mid, head_order in heads:
            facing = (tip[0] - mid[0], tip[1] - mid[1])
            flen = math.hypot(facing[0], facing[1]) or 1.0
            facing = (facing[0] / flen, facing[1] / flen)
            best, best_score = None, -2.0
            for x1, y1, x2, y2, line_order in lines:
                if abs(line_order - head_order) > 8:
                    continue
                for end, other in (((x1, y1), (x2, y2)), ((x2, y2), (x1, y1))):
                    if dist(tip, end) > 4.0:
                        continue
                    tr = (tip[0] - other[0], tip[1] - other[1])
                    tlen = math.hypot(tr[0], tr[1]) or 1.0
                    # Two arrows may share a destination; the shaft that agrees
                    # with the head's facing direction is the one it belongs to.
                    score = (tr[0] * facing[0] + tr[1] * facing[1]) / tlen
                    if score > best_score:
                        best, best_score = (other, end), score
            if best is None:
                problems.append("arrow-loose  head at (%.0f,%.0f) has no shaft" % tip)
            elif best_score <= 0:
                problems.append("arrow-back  head at (%.0f,%.0f) points against the shaft" % tip)
    return problems


def main(argv: list[str]) -> int:
    patterns = argv or ["*.svg"]
    files: list[pathlib.Path] = []
    for pat in patterns:
        direct = pathlib.Path(pat)
        if direct.exists():
            files.append(direct)
        else:
            files.extend(sorted(FIGURES.glob(pat)))
    if not files:
        print("no figures matched", file=sys.stderr)
        return 2

    flagged = total = 0
    for path in files:
        problems = sorted(set(check(path)))
        if problems:
            flagged += 1
            total += len(problems)
            print(path.name)
            for p in problems:
                print("    %s" % p)
    print("\n%d/%d figures flagged, %d findings" % (flagged, len(files), total))
    return 1 if flagged else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
