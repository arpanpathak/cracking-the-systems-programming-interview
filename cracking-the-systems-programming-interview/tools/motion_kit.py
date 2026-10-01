"""Shared pieces for the algorithm animations: arrays, pointers, maps, stacks,
grids, and a driver that turns a list of steps into a timeline.

An algorithm animation is written as a simulation. The builder runs the
algorithm on the chapter's input and records one step per thing a reader should
see, each with a caption, the code line being run, and the state after it. `play`
turns the steps into a timeline: numbers in the state slide from one value to
the next, and everything else changes when its step starts.

Pointers never cover the element they point at. A pointer sits above or below
its cell, and two pointers at the same index stack outward.
"""

from __future__ import annotations

import pathlib
import re

from motion import (BRASS, BRASS_LT, FAINT, INK, LINE, MUTED, PAPER, RUST, RUST_LT, STAGE,
                    TEAL, TEAL_LT, W, Timeline, back, clamp, ease_out, in_out, lerp, mix,
                    text_width)

LAB = pathlib.Path(__file__).resolve().parent.parent.parent / "rust-interview-lab"

NAVY = "#3b5b92"
NAVY_LT = "#e6ecf6"


# ------------------------------------------------------------------ source


def source(path: str, first: str, last: str | None = None, drop_comments=True) -> list[str]:
    """Lines of a lab source file, from the line containing `first` to the line
    containing `last` (inclusive), dedented. `last="}"` means the closing brace of
    the item that starts at `first`. The panel then always shows the
    code the chapter lists."""
    lines = (LAB / path).read_text().split("\n")
    a = next(i for i, l in enumerate(lines) if first in l)
    if last is None:
        b = a
    elif last == "}":
        # the end of the item that starts at `first`, found by matching braces
        depth, b = 0, a
        for i in range(a, len(lines)):
            body = re.sub(r'"(\\.|[^"\\])*"', '""', re.sub(r"//.*", "", lines[i]))
            body = re.sub(r"'(\\.|[^'\\])'", "''", body)
            depth += body.count("{") - body.count("}")
            if depth == 0 and "{" in "".join(lines[a:i + 1]):
                b = i
                break
    else:
        b = next(i for i in range(a, len(lines)) if last in lines[i])
    out = lines[a:b + 1]
    if drop_comments:
        out = [l for l in out if not l.strip().startswith("//")]
    out = [l for l in out if l.strip()]
    pad = min(len(l) - len(l.lstrip()) for l in out if l.strip())
    return [l[pad:] for l in out]


def line_of(lines: list[str], text: str, nth: int = 0) -> int:
    """Index of the `nth` line in `lines` containing `text`."""
    hits = [i for i, l in enumerate(lines) if text in l]
    return hits[nth]


class Panel:
    """Real code for a code panel, as the chapter shows it.

    `ranges` is a list of (first, last) pairs in one lab file, read as in
    `source`: `last` is a text, a (text, extra lines) pair, "}" for the end of
    the block opened on `first`, or None for one line. `first` may be a (text, nth) pair. Indentation is
    kept, so every arm sits inside its `match` and every line inside its block.
    Between two ranges the panel shows `// ...` at the indentation of the code
    that follows, so a reader can see that lines were left out.

    `separate=True` is for ranges taken from different functions: each range
    keeps its own indentation instead of sharing the file's.

    `focus` lists the texts that a timeline's code index counts through: index
    k means the panel line holding `focus[k]`. `at(c)` turns such an index into
    a panel line, so a builder can keep numbering its steps 0, 1, 2.
    """

    def __init__(self, path, ranges, focus=(), comments=False, separate=False):
        src = (LAB / path).read_text().split("\n")
        segments, spans = [], []
        for first, last in ranges:
            text, nth = first if isinstance(first, tuple) else (first, 0)
            a = [i for i, l in enumerate(src) if text in l][nth]
            if last is None:
                b = a
            elif last == "}":
                depth, b = 0, a
                for i in range(a, len(src)):
                    body = re.sub(r'"(\\.|[^"\\])*"', '""', re.sub(r"//.*", "", src[i]))
                    depth += body.count("{") - body.count("}")
                    if depth <= 0 and "{" in "".join(src[a:i + 1]):
                        b = i
                        break
            else:
                text, extra = last if isinstance(last, tuple) else (last, 0)
                b = next(i for i in range(a, len(src)) if text in src[i]) + extra
            keep = [l for l in src[a:b + 1]
                    if l.strip() and (comments or not l.strip().startswith("//"))]
            segments.append(keep)
            spans.append((a, b))
        if separate:
            # ranges from different functions: each keeps its own structure
            segments = [[l[min(len(x) - len(x.lstrip()) for x in seg):] for l in seg]
                        for seg in segments]
        pad = min(len(l) - len(l.lstrip()) for seg in segments for l in seg)
        self.lines = []
        for k, seg in enumerate(segments):
            between = src[spans[k - 1][1] + 1:spans[k][0]] if k else []
            skipped = any(l.strip() and not l.strip().startswith("//") for l in between)
            if k and (skipped or spans[k][0] < spans[k - 1][1]):
                before, after = segments[k - 1][-1], seg[0]
                indent = len(after) - len(after.lstrip()) - pad
                if before.rstrip().endswith("{"):
                    indent = len(before) - len(before.lstrip()) - pad + 4
                self.lines.append(" " * indent + "// ...")
            self.lines += [l[pad:] for l in seg]
        self.marks = [self._mark(f) for f in focus]

    def _mark(self, text):
        """A focus line, or None when this panel does not hold it, so several
        panels can share one numbering and each shows only its own lines."""
        try:
            return self.find(text)
        except IndexError:
            return None

    def find(self, text, nth=0):
        """The panel line holding `text` (or its `nth` occurrence)."""
        if isinstance(text, tuple):
            text, nth = text
        return [i for i, l in enumerate(self.lines) if text in l][nth]

    def at(self, c):
        """A timeline code index (into `focus`) as a panel line; negative stays."""
        if c is None or c < 0 or not self.marks:
            return c
        lo = min(int(c), len(self.marks) - 1)
        hi = min(lo + 1, len(self.marks) - 1)
        a, b = self.marks[lo], self.marks[hi]
        if a is None:
            return -1.0
        if b is None or b < a:
            return float(a)
        return a + (b - a) * (c - int(c))

    def __len__(self):
        return len(self.lines)

    def reached(self, s, t, track="code", per_line=0.12, longest=0.6):
        """How far down this panel the highlight has been, in panel lines.

        Like `Timeline.reached`, but measured after mapping, because a builder's
        step order need not follow the order of the lines in the file."""
        segments = [(start, self.at(b)) for start, _e, _a, b, _ease in s.timeline.segments[track]
                    if isinstance(b, (int, float)) and b >= 0]
        first = self.at(s.timeline.initial[track])
        upcoming = [b for _s, b in segments if b is not None and b >= 0]
        best = first if first is not None and first >= 0 else (upcoming[0] if upcoming else 0)
        for start, b in segments:
            if start > t:
                break
            if b is None or b <= best:
                continue
            ramp = min(longest, per_line * (b - best))
            u = 1.0 if ramp <= 0 else min(1.0, max(0.0, (t - start) / ramp))
            best += (b - best) * u
        return best

    def height(self, lead):
        return 30 + len(self.lines) * lead + 8

    def draw(self, p, x, y, w, title, s, t, track="code", strike=None, reveal=True, **kw):
        """`code_panel` with the timeline's indices mapped onto these lines.

        Pass `reveal=False` for a panel that is one of several taking turns: it
        is shown whole when its turn comes."""
        from motion import code_panel
        mark = None if strike is None or strike < 0 else int(round(self.at(strike)))
        shown = self.reached(s, t, track) if reveal else None
        return code_panel(p, x, y, w, title, self.lines, self.at(s[track]), strike=mark,
                          reveal=shown, **kw)


def nth_after(path, text, anchor):
    """Which occurrence of `text` in a lab file is the first one after `anchor`,
    for a `Panel` range whose first line is not unique in the file."""
    src = (LAB / path).read_text().split("\n")
    start = next(i for i, l in enumerate(src) if anchor in l)
    return sum(1 for l in src[:start] if text in l)


class Panels:
    """Several real-code panels from one file that take turns.

    Each group of ranges is one panel, typically one function. All panels share
    one `focus` numbering, so a timeline's code index names a line in exactly
    one of them. The panel shown is the one holding the latest line the
    timeline has highlighted, so it stays put between steps.
    """

    def __init__(self, path, groups, titles, focus):
        self.panels = [Panel(path, ranges, focus) for ranges in groups]
        self.titles = titles
        # one box size for the whole group, so the frame does not jump
        tallest = max(len(p.lines) for p in self.panels)
        for panel in self.panels:
            panel.lines += [""] * (tallest - len(panel.lines))

    def pick(self, s, t, track="code"):
        latest = None
        for start, _end, _a, b, _ease in s.timeline.segments[track]:
            if start > t:
                break
            if isinstance(b, (int, float)) and b >= 0:
                latest = b
        if latest is None:
            first = s.timeline.initial[track]
            latest = first if isinstance(first, (int, float)) and first >= 0 else 0
        k = min(int(round(latest)), len(self.panels[0].marks) - 1)
        for n, panel in enumerate(self.panels):
            if panel.marks[k] is not None:
                return n
        return 0

    def __len__(self):
        return max(len(p) for p in self.panels)

    def draw(self, p, x, y, w, s, t, track="code", **kw):
        n = self.pick(s, t, track)
        return self.panels[n].draw(p, x, y, w, self.titles[n], s, t, track=track,
                                   reveal=False, **kw)


# ------------------------------------------------------------------ layout


def layout(code_y: float, code_lines: int, lead: float = 15.6):
    """Positions below the drawing, computed from the code panel's real height so
    the panel, the caption, and the progress rail can never overlap.

    Returns (caption_y, rail_y, height)."""
    code_h = 30 + code_lines * lead + 8
    caption_y = code_y + code_h + 14
    rail_y = caption_y + 2 * 23.0 + 26 + 18
    return caption_y, rail_y, rail_y + 36


# ------------------------------------------------------------------ driver


def play(steps: list[dict], defaults: dict, slide=0.75, hold=0.5) -> Timeline:
    """A timeline from steps.

    Each step is a dict with `say`, and optionally `kind` ("step", "insight",
    "fail"), `chapter` (a label for the progress rail), `dur` (how long its
    numbers take to slide), `hold` (a pause after the motion), and `events`
    (names passed to `tl.event`). Every other key is state, and must have a
    default.
    """
    control = {"say", "kind", "chapter", "dur", "hold", "events"}
    tl = Timeline(**defaults)
    for step in steps:
        if "chapter" in step:
            tl.chapter(step["chapter"])
        tl.say(step["say"], step.get("kind", "step"))
        state = {k: v for k, v in step.items() if k not in control}
        unknown = set(state) - set(defaults)
        if unknown:
            raise KeyError("no default for %s" % ", ".join(sorted(unknown)))
        numbers = {k: v for k, v in state.items()
                   if isinstance(v, (int, float)) and not isinstance(v, bool)}
        others = {k: v for k, v in state.items() if k not in numbers}
        if others:
            tl.set(**others)
        for name in step.get("events", ()):
            tl.event(name)
        if numbers:
            tl.to(step.get("dur", slide), in_out, **numbers)
        tl.wait(step.get("hold", hold))
    return tl


def since(tl: Timeline, name: str, t: float) -> float:
    """Seconds since the value `name` last changed, or a large number."""
    when, old = tl.changed(name, t)
    return 99.0 if old is None else t - when


def pop(age: float, length=0.45) -> float:
    """0 to 1 over `length` seconds, with an overshoot: how a new thing arrives."""
    return back(clamp(age / length)) if age < length else 1.0


# ------------------------------------------------------------------ arrays


def row_xs(n: int, cell: float, gap: float, cx: float = W / 2.0) -> list[float]:
    total = n * cell + (n - 1) * gap
    left = cx - total / 2.0
    return [left + cell / 2.0 + i * (cell + gap) for i in range(n)]


def cells(p, xs, y, values, cell=56.0, fills=None, edges=None, inks=None, size=22.0,
          index=True, index_labels=None, mono=True, widths=None, opacity=1.0):
    """A row of boxes with a value in each, and its index underneath.

    `y` is the top of the boxes. Returns the y of the bottom of the index row,
    which is where a pointer below the array starts.
    """
    with p.group(opacity=opacity):
        for i, (x, v) in enumerate(zip(xs, values)):
            w = widths[i] if widths else cell
            fill = fills[i] if fills else PAPER
            edge = edges[i] if edges else LINE
            ink = inks[i] if inks else INK
            p.rect(x - w / 2, y, w, cell, fill, edge, 9, 1.6)
            p.text(x, y + cell / 2 + size * 0.36, str(v), size, ink, 700, "middle", mono=mono)
            if index:
                label = index_labels[i] if index_labels else str(i)
                p.text(x, y + cell + 18, label, 11.5, FAINT, 600, "middle", mono=True)
    return y + cell + (26 if index else 6)


def pointer(p, x, y, name, color, side="above", slot=0, opacity=1.0, value=None):
    """A named arrow aimed at a cell edge, never drawn on the cell.

    For `side="above"`, `y` is the top of the cell and the arrow points down at
    it. For `side="below"`, `y` is the bottom of the index row and the arrow
    points up. `slot` stacks a second pointer at the same index further out.
    """
    if opacity <= 0.01:
        return
    step = 30.0
    with p.group(opacity=opacity):
        if side == "above":
            tip = y - 5 - slot * step
            p.path("M %.1f %.1f L %.1f %.1f L %.1f %.1f Z" % (x, tip, x - 7, tip - 10, x + 7, tip - 10),
                   color, "none")
            label = name if value is None else "%s = %s" % (name, value)
            p.text(x, tip - 15, label, 13, color, 700, "middle", mono=True)
        else:
            tip = y + 4 + slot * step
            p.path("M %.1f %.1f L %.1f %.1f L %.1f %.1f Z" % (x, tip, x - 7, tip + 10, x + 7, tip + 10),
                   color, "none")
            label = name if value is None else "%s = %s" % (name, value)
            p.text(x, tip + 26, label, 13, color, 700, "middle", mono=True)


def span(p, x0, x1, y, color, label=None, width=4.0, opacity=1.0):
    """A bracket under or over a run of cells: a window, a sorted half, a range."""
    if opacity <= 0.01:
        return
    with p.group(opacity=opacity):
        p.line(x0, y, x1, y, color, width)
        p.line(x0, y - 7, x0, y + 1, color, 2.4)
        p.line(x1, y - 7, x1, y + 1, color, 2.4)
        if label:
            p.text((x0 + x1) / 2, y + 18, label, 12, color, 700, "middle")


# ------------------------------------------------------------------ panels


def panel(p, x, y, w, h, title, edge=LINE, fill="#fbfcfd"):
    p.rect(x, y, w, h, fill, edge, 10, 1.3)
    p.text(x + 14, y + 21, title, 12, MUTED, 600)


def kv_panel(p, tl, t, x, y, w, title, entries, name, key_w=None, hot=None, miss=None,
             rows=5, row_h=30.0, arrow="→", empty="empty"):
    """A map drawn as a two-column table. `entries` is a list of (key, value)
    pairs in insertion order. A new entry pops in; `hot` highlights a key that
    a lookup found, and `miss` shows a key that a lookup did not find."""
    h = 34 + rows * row_h + 8
    panel(p, x, y, w, h, title)
    age = since(tl, name, t)
    key_w = key_w or w * 0.42
    if not entries:
        p.text(x + w / 2, y + 34 + row_h, empty, 13, FAINT, 400, "middle", mono=True)
    for i, (k, v) in enumerate(entries):
        ry = y + 34 + i * row_h
        newest = i == len(entries) - 1
        u = pop(age) if newest else 1.0
        found = hot is not None and str(k) == str(hot)
        fill = TEAL_LT if found else PAPER
        edge = TEAL if found else LINE
        with p.group(opacity=clamp(u), scale=lerp(0.7, 1.0, clamp(u)), cx=x + w / 2, cy=ry + 12):
            p.rect(x + 10, ry, w - 20, row_h - 6, fill, edge, 6, 1.3 + found)
            p.text(x + 10 + key_w / 2, ry + 17, str(k), 14, INK, 700, "middle", mono=True)
            p.text(x + 10 + key_w + 6, ry + 17, arrow, 14, FAINT, 400, "middle")
            p.text(x + 10 + key_w + 16 + (w - 36 - key_w) / 2, ry + 17, str(v), 14, MUTED, 600,
                   "middle", mono=True)
    if miss is not None:
        my = y + h + 18
        p.text(x + w / 2, my, "no key %s" % miss, 12.5, RUST, 700, "middle", mono=True)
    return y + h


def stack_panel(p, tl, t, x, y, w, title, items, name, rows=6, row_h=34.0, hot_top=False,
                bad_top=False):
    """A vector used as a stack, drawn bottom-up, with its top marked."""
    h = 34 + rows * row_h + 10
    panel(p, x, y, w, h, title)
    age = since(tl, name, t)
    base = y + h - 10
    for i, item in enumerate(items):
        ry = base - (i + 1) * row_h
        top = i == len(items) - 1
        u = pop(age) if top else 1.0
        fill, edge = PAPER, LINE
        if top and hot_top:
            fill, edge = TEAL_LT, TEAL
        if top and bad_top:
            fill, edge = RUST_LT, RUST
        with p.group(opacity=clamp(u), dy=(1 - clamp(u)) * -24):
            p.rect(x + 18, ry + 3, w - 36, row_h - 6, fill, edge, 6, 1.4)
            p.text(x + w / 2, ry + row_h / 2 + 6, str(item), 16, INK, 700, "middle", mono=True)
    if items:
        ry = base - len(items) * row_h + row_h / 2
        p.text(x + w + 8, ry + 4, "\u2190 top", 11, MUTED, 700)
    else:
        p.text(x + w / 2, base - row_h / 2, "empty", 13, FAINT, 400, "middle", mono=True)
    return y + h


def fact(p, x, y, label, value, color=INK, size=15, label_w=None):
    """`label  value` on one line, for the one or two numbers a step computes."""
    p.text(x, y, label, 12.5, MUTED, 600)
    lw = label_w if label_w is not None else text_width(label, 12.5) + 10
    p.text(x + lw, y, str(value), size, color, 700, mono=True)


def ghost_text(p, x, y, text, size=13, color=FAINT):
    p.text(x, y, text, size, color, 400, "middle", mono=True)


def grid_cells(p, x0, y0, n, size, values, fills=None, edges=None, inks=None, font=22.0):
    """An n x n grid of boxes. Returns the centre of each cell, row-major."""
    centres = []
    for r in range(n):
        for c in range(n):
            k = r * n + c
            x, y = x0 + c * size, y0 + r * size
            p.rect(x + 3, y + 3, size - 6, size - 6, fills[k] if fills else PAPER,
                   edges[k] if edges else LINE, 8, 1.6)
            p.text(x + size / 2, y + size / 2 + font * 0.36, str(values[k]), font,
                   inks[k] if inks else INK, 700, "middle", mono=True)
            centres.append((x + size / 2, y + size / 2))
    return centres


# ------------------------------------------------------------------- trees


def heap_positions(n, cx, top, dy=70.0, spread=150.0):
    """Centres of a complete binary tree of `n` nodes, by array index."""
    out = []
    for i in range(n):
        level = (i + 1).bit_length() - 1
        first = (1 << level) - 1
        k = i - first
        width = spread * 2 / (1 << level) * 2
        x = cx - spread * 2 + width / 2 + k * width if level else cx
        out.append((x, top + level * dy))
    return out


def node(p, x, y, label, fill=PAPER, edge=LINE, r=22.0, size=16.0, ink=INK, width=1.8,
         opacity=1.0, shadow=None):
    if opacity <= 0.01:
        return
    with p.group(opacity=opacity):
        p.circle(x, y, r, fill, edge, width)
        p.text(x, y + size * 0.36, str(label), size, ink, 700, "middle", mono=True)


def edge(p, a, b, color=LINE, width=1.8, r=22.0, opacity=1.0, dash=None):
    import math
    (x1, y1), (x2, y2) = a, b
    d = math.hypot(x2 - x1, y2 - y1) or 1.0
    ux, uy = (x2 - x1) / d, (y2 - y1) / d
    p.line(x1 + ux * r, y1 + uy * r, x2 - ux * r, y2 - uy * r, color, width, opacity=opacity, dash=dash)


__all__ = [n for n in dir() if not n.startswith("_")] + ["mix", "ease_out", "lerp", "clamp",
                                                          "re"]
