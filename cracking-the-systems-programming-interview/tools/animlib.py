"""Shared helpers for the chapter animations, and the layout they all share.

A frame is a `Frame`, which is a `Figure` with a fixed skeleton:

    title
    one line of orientation
    ------------------------------------------------
    the drawing area            <- the builder paints here, and only here
    ------------------------------------------------
    a band: the insight, or the case that fails
    the step sentence, in the largest body type on the canvas
    a note, when the frame needs one caveat
    name = value, name = value, name = value
    a progress rail, so the reader knows where they are

The foot is measured before the canvas is created, so a long sentence in one
frame cannot push the scoreboard off another, and the frames of one animation
share a canvas height, which GIF requires.

## How a picture is drawn

A sequence of values is a **rail**: a thin baseline with the values sitting above
it and their indexes below, with state carried by a short coloured bar under each
station rather than by a filled box around it. A diagram of eight array elements
is eight small bars on one line, not eight rectangles.

    value        p     w     w     k     e     w
    rail     ────┴─────┴─────┴─────┴─────┴─────┴────
    index        0     1     2     3     4     5
    state     ▬▬▬▬▬ ▬▬▬▬▬ ▬▬▬▬▬ ····  ····  ····

A run of stations, such as a window or a live range, is a `band`: one coloured
rule spanning the run. A pointer is a `caret` on the rail with a small label. A
cell is only used for something that is genuinely a cell: a grid square, a buffer
slot, a tree node.

That is the whole grammar. It keeps the ink down, so the one element that changed
is the one the eye lands on, and it keeps every animation in the book looking
like every other one.
"""

import pathlib

from svgkit import *  # noqa: F401,F403
from svgkit import Figure, Animation, text_width, wrap, center, MONO_RATIO

OUT = pathlib.Path(__file__).resolve().parent.parent / "src" / "figures"

# The drawing canvas. The browser edition gives a figure 820px, so a unit here is
# a CSS pixel there, minus the small difference the page margins make.
W = 820
PAD = 26
CONTENT = W - 2 * PAD

# Type sizes, in drawing units. These are the numbers that decide whether the
# GIF is readable, so they are named rather than sprinkled through the builders.
T_TITLE = 20.0
T_SUB = 13.0
T_STEP = 16.0
T_NOTE = 13.0
T_COUNTER = 14.0
T_VALUE = 19.0
T_MARK = 11.0
T_CELL = 16.0

LEAD_STEP = 23.0
LEAD_NOTE = 18.0
LEAD_INSIGHT = 22.0
LEAD_FAIL = 22.0

DIAGRAM_TOP = 84.0
LEGEND_ROW = 24.0
PROGRESS_H = 26.0

Figure.type_scale = 1.0
Figure.height_scale = 1.0

# Every hold is long enough to read the sentence and then look back at the
# picture. The last frame is held longer still, so the loop does not cut away
# from the answer while the reader is still on it.
Animation.speed = 1.0
Animation.hold = 4000
Animation.tween = 2
Animation.tween_ms = 130
Animation.scale = 1.85


def holds(count, longer=(), base=None, extra=1500):
    """Durations for one animation: a steady hold, with some frames held longer.

    `longer` names the frames that deserve more time, which is the frame that
    carries the insight and the frame that carries the failing case.
    """
    base = base or Animation.hold
    out = [float(base)] * count
    for i in longer:
        if 0 <= i < count:
            out[i] += 700
    out[-1] = base + extra
    return out


def _lines(text, size, width, mono=False):
    return wrap(text, size, width, mono) if text else []


class Frame(Figure):
    """One step of an animation: a title, a drawing area, and a measured foot."""

    def __init__(self, title, sub=None, diagram=190, step=None, note=None, insight=None,
                 fails=None, pairs=None, legend=None, glow=None, height=None,
                 insight_rows=0, at=None):
        self.diagram = diagram
        self.title = title
        self.sub = sub
        self.step_text = step
        self.note_text = note
        self.insight_text = insight
        self.fail_text = fails
        self.pairs = pairs or []
        self.legend_entries = legend
        self.glow_at = glow
        self.at = at

        self.legend_row = LEGEND_ROW if legend else 0.0
        self.step_lines = _lines(step, T_STEP, CONTENT)
        self.note_lines = _lines(note, T_NOTE, CONTENT)
        self.insight_lines = _lines(insight, T_STEP - 1.0, CONTENT - 74)
        self.fail_lines = _lines(fails, T_STEP - 1.0, CONTENT - 74)
        # The band row is reserved for every frame of an animation that uses one,
        # so the sentence and the scoreboard never shift when it appears.
        self.band_rows = max(insight_rows, len(self.insight_lines), len(self.fail_lines))

        self.top = DIAGRAM_TOP + self.legend_row
        self.bottom = self.top + diagram
        super().__init__(W, max(self._natural_height(), height or 0.0))
        self._furniture()

    def _natural_height(self):
        return self.bottom + 22 + self._foot_height() + PROGRESS_H + 14

    def _foot_height(self):
        foot = 0.0
        if self.band_rows:
            foot += 20 + self.band_rows * LEAD_INSIGHT + 6 + 16
        if self.step_lines:
            foot += len(self.step_lines) * LEAD_STEP + 6
        if self.note_lines:
            foot += len(self.note_lines) * LEAD_NOTE
        foot += 16 + 24
        return foot

    def _furniture(self):
        if self.glow_at:
            self.glow(*(self.glow_at))

        self.text(PAD, 32, self.title, T_TITLE, INK, bold=True, layer="text")
        if self.sub:
            self.text(PAD, 57, self.sub, T_SUB, MUTED, layer="text")
        if self.legend_entries:
            legend(self, 84, self.legend_entries)

        y = self.bottom + 22
        if self.band_rows:
            band_h = 20 + self.band_rows * LEAD_INSIGHT + 6
            if self.insight_lines:
                insight_band(self, y, self.insight_lines, band_h)
            elif self.fail_lines:
                fail_band(self, y, self.fail_lines, band_h)
            y += band_h + 16
        if self.step_lines:
            for i, line in enumerate(self.step_lines):
                self.text(PAD, y + i * LEAD_STEP, line, T_STEP, INK, layer="text")
            y += len(self.step_lines) * LEAD_STEP + 6
        if self.note_lines:
            for i, line in enumerate(self.note_lines):
                self.text(PAD, y + i * LEAD_NOTE, line, T_NOTE, MUTED, layer="text")
            y += len(self.note_lines) * LEAD_NOTE

        counter(self, y + 34, self.pairs)
        if self.at:
            progress(self, self.height - 16, self.at[0], self.at[1])

    def area(self, pad=0):
        return (PAD - pad, self.top - pad, CONTENT + 2 * pad, self.diagram + 2 * pad)

    def mid(self):
        return self.top + self.diagram / 2.0


def frames(make, specs):
    """Build every frame again until the whole animation shares one canvas.

    GIF frames cannot differ in height, and the frames of one animation have to
    keep the same furniture in the same place, so the tallest frame and the
    widest band set the shape for all of them. Reserving a band row can make a
    frame taller, which can raise the tallest frame in turn, so the pass repeats
    until nothing moves. It settles after two rounds.
    """
    built = [make(spec, None, 0, i) for i, spec in enumerate(specs)]
    for _ in range(4):
        tallest = max(frame.height for frame in built)
        rows = max(frame.band_rows for frame in built)
        if all(abs(frame.height - tallest) < 0.01 and frame.band_rows == rows
               for frame in built):
            return built
        built = []
        for i, spec in enumerate(specs):
            built.append(make(spec, tallest, rows, i))
    return built


def publish(name, built, durations=None):
    Animation(built, durations).save(OUT / name)
    return name


# ---------------------------------------------------------------- the rail


def rail_row(f, y, values, x0=None, unit=46, gap=12, size=T_VALUE,
             colors=None, bolds=None, ticks=True, mono=True, above=True):
    """Values sitting on a baseline, with a tick under each one.

    Returns the centre x of every station, which is what the rest of the drawing
    is placed against: bands, carets, state bars, and index rows all take those
    numbers rather than computing positions of their own.
    """
    n = len(values)
    total = n * unit + (n - 1) * gap
    left = (W - total) / 2.0 if x0 is None else x0
    xs = [left + unit / 2.0 + i * (unit + gap) for i in range(n)]
    f.line(left - gap * 0.4, y, left + total + gap * 0.4, y, BORDER, 1.6)
    for i, (x, value) in enumerate(zip(xs, values)):
        color = colors[i] if colors else INK
        f.text(x, y - 13 if above else y + size + 2, str(value), size, color,
               mono=mono, anchor="middle",
               bold=bool(bolds[i]) if bolds else False)
        if ticks:
            f.line(x, y, x, y + 7, BORDER, 1.4)
    return xs


def state_row(f, xs, y, colors, unit=46, height=5, dash_color=None):
    """A short coloured bar under every station: the whole row at a glance.

    This is what replaces a fill inside a box. One bar per value costs a fraction
    of the ink and reads faster, because the eye compares lengths and colours
    instead of parsing eight rectangles.
    """
    for x, color in zip(xs, colors):
        if color is None:
            f.line(x - unit / 2.0 + 5, y + height / 2.0, x + unit / 2.0 - 5, y + height / 2.0,
                   dash_color or BORDER, 1.2, dash=True)
        else:
            f.rect(x - unit / 2.0 + 5, y, unit - 10, height, color, "none", 2)


def index_row(f, xs, y, labels=None, color=None, size=T_MARK, halo=False):
    """The index under every station.

    `halo` masks whatever was drawn under the digits. A pointer below the index
    row reaches the rail with a thin leader, and the halos are what stop that
    leader cutting through the numbers.
    """
    for i, x in enumerate(xs):
        f.text(x, y, str(labels[i]) if labels else str(i), size, color or MUTED,
               anchor="middle", halo=halo)


def band(f, xs, lo, hi, y, color, width=3.5, dash=False, pad=16, label=None):
    """One coloured rule spanning a run of stations: a window, a live range.

    A run is a single horizontal mark, which is the shape the reader is being
    asked to hold in mind anyway.
    """
    if lo > hi:
        return
    a, b = xs[lo] - pad, xs[hi] + pad
    f.line(a, y, b, y, color, width, dash=dash)
    if label:
        f.text((a + b) / 2.0, y - 9, label, T_MARK, color, anchor="middle", bold=True,
               halo=True, layer="text")


def caret(f, x, y, color, down=True, size=9.0):
    """A small filled triangle pointing at a station."""
    if down:
        pts = [(x, y), (x - size * 0.72, y - size), (x + size * 0.72, y - size)]
    else:
        pts = [(x, y), (x - size * 0.72, y + size), (x + size * 0.72, y + size)]
    f.shape(pts, color)


def pointer(f, x, tip_y, label, color, above=True, size=9.0, gap=7, leader_to=None):
    """A caret whose tip sits at `tip_y`, with its name beyond it.

    `above` puts the caret above the tip, pointing down; otherwise it goes below,
    pointing up. `leader_to` runs a thin line from the rail down to the tip, so a
    pointer that has to clear a row of index numbers still reads as attached to
    its station. Draw the index row after this one, with `halo=True`, so the
    digits mask the line rather than the line cutting through the digits.
    """
    if above:
        caret(f, x, tip_y, color, down=True, size=size)
        f.text(x, tip_y - size - gap - 4, label, T_MARK, color, anchor="middle",
               bold=True, halo=True, layer="text")
    else:
        if leader_to is not None:
            f.line(x, tip_y, x, leader_to, color, 1.2)
        caret(f, x, tip_y, color, down=False, size=size)
        f.text(x, tip_y + size + gap + 10, label, T_MARK, color, anchor="middle",
               bold=True, halo=True, layer="text")


def dot(f, x, y, color, r=5.0):
    f.circle(x, y, r, color, color, 1.0)


def cross(f, x, y, color=RUST, r=6.0, width=2.2):
    """A small crossed circle. The mark for the case that fails."""
    f.circle(x, y, r, WHITE, color, 1.6)
    f.line(x - r * 0.5, y - r * 0.5, x + r * 0.5, y + r * 0.5, color, width)
    f.line(x - r * 0.5, y + r * 0.5, x + r * 0.5, y - r * 0.5, color, width)


def pair_link(f, x1, y1, x2, y2, color=RUST, width=1.8, dash=True):
    """A link between two stations, for a repeat or a matching pair."""
    f.arrow(x1, y1, x2, y2, color, width, dash=dash, head=7.0)


# ------------------------------------------------------------------ furniture


def counter(f, y, pairs, size=T_COUNTER):
    """A row of `name = value` facts, spread across the content width."""
    if not pairs:
        return
    size = size * f.type_scale
    widths = [text_width("%s = " % name, size, True) + text_width(str(value), size, True)
              for name, value, _ in pairs]
    gap = (CONTENT - sum(widths)) / max(1, len(pairs) - 1)
    gap = max(24.0, min(gap, 110.0))
    x = PAD
    for name, value, color in pairs:
        label = "%s = " % name
        f.text(x, y, label, size, MUTED, mono=True, scaled=False, layer="text")
        x += text_width(label, size, True)
        f.text(x, y, str(value), size, color or INK, mono=True, bold=True, scaled=False,
               layer="text")
        x += text_width(str(value), size, True) + gap


def band_ground(f, y, rows, height, fill, edge, size, mark):
    """The shared body of the insight band and the failure band."""
    f.rect(PAD, y, CONTENT, height, fill, edge, 9, width=1.6, layer="text")
    f.rect(PAD, y, 6, height, edge, edge, 3, width=0.6, layer="text")
    mark(PAD + 34, y + 20 + (len(rows) - 1) * LEAD_INSIGHT / 2.0)
    for i, row in enumerate(rows):
        f.text(PAD + 56, y + 20 + i * LEAD_INSIGHT, row, size, INK, bold=True, layer="text")


def insight_band(f, y, rows, height=None):
    """The band that marks the step where the idea clicks."""
    height = height or 20 + len(rows) * LEAD_INSIGHT + 6

    def mark(bx, by):
        f.glow(bx, by, 26, BRASS, 0.5)
        f.circle(bx, by, 7.5, BRASS, BRASS, 1.2)
        f.text(bx, by + 4.5, "!", 10, WHITE, anchor="middle", bold=True, scaled=False,
               layer="text")

    band_ground(f, y, rows, height, CREAM, BRASS, T_STEP - 1.0, mark)
    return y + height


def fail_band(f, y, rows, height=None):
    """The band that marks the case the algorithm has to reject.

    Same shape as the insight band and a different colour, so a reader learns in
    one frame which of the two they are looking at.
    """
    height = height or 20 + len(rows) * LEAD_FAIL + 6

    def mark(bx, by):
        cross(f, bx, by, RUST, 8.0, 2.4)

    band_ground(f, y, rows, height, PINK, RUST, T_STEP - 1.0, mark)
    return y + height


def legend(f, y, entries, size=T_MARK + 0.5):
    """A key for the colours, right-aligned on its own row under the title.

    A swatch is a short bar, the same shape the diagram uses for state, so the
    key and the thing it names are the same mark.
    """
    size = size * f.type_scale
    widths = [22 + text_width(label, size) for label, _ in entries]
    total = sum(widths) + 22 * (len(entries) - 1)
    x = W - PAD - total
    for (label, color), width in zip(entries, widths):
        f.rect(x, y - 7, 14, 5, color, "none", 2, layer="text")
        f.text(x + 20, y, label, size, MUTED, scaled=False, layer="text")
        x += width + 22


def progress(f, y, index, total):
    """A rail of segments at the foot: where this frame sits in the loop.

    A reader who knows how far in they are, and that the picture repeats, is a
    reader who can stop bracing for the next change.
    """
    if total < 2:
        return
    label = "%d / %d" % (index + 1, total)
    size = T_MARK - 1
    # The count sits past the end of the rail, so a long loop cannot put the
    # last segment under the digits.
    lead = text_width(label, size * f.type_scale) + 14
    gap = 6.0
    width = CONTENT - lead
    unit = (width - gap * (total - 1)) / total
    for i in range(total):
        x = PAD + i * (unit + gap)
        done = i <= index
        f.rect(x, y, unit, 4, TEAL if done else BORDER, "none", 2, layer="text")
    f.text(W - PAD, y + 3, label, size, MUTED, anchor="end", layer="text")


# ------------------------------------------------- shapes for a single cell


def chip(f, x, y, label, color=TEAL, fill=WHITE, size=T_MARK, mono=True):
    """A named pill, for the few pictures where a caret will not fit."""
    size = size * f.type_scale
    w = text_width(label, size, mono) + 20
    h = size + 12
    f.rect(x - w / 2, y - h / 2, w, h, fill, color, 6, width=1.5)
    f.text(x, y + size * 0.36, label, size, color, mono, "middle", bold=True, scaled=False)
    return (x - w / 2, y - h / 2, w, h)


def ghost(f, x, y, w, h, label=None, size=T_CELL, color="#c3cfda"):
    """Where something used to be, as a dashed outline and nothing else."""
    f.rect(x, y, w, h, "none", color, 4, width=1.4, dash=True)
    if label is not None:
        f.text(x + w / 2, y + h / 2 + size * f.type_scale * 0.36, label, size, color, True,
               "middle", scaled=False)


def track(f, x1, y1, x2, y2, color=TEAL, width=1.6, head=8.0):
    """A dotted line from where a thing was to where it now is."""
    f.arrow(x1, y1, x2, y2, color, width, dash=True, head=head)


def ring(f, box, color=BRASS, pad=6, width=2.0, dash=True):
    x, y, w, h = box
    f.rect(x - pad, y - pad, w + 2 * pad, h + 2 * pad, "none", color, 10, width=width, dash=dash)


# ---------------------------------------------------------------------- rows


def row(f, x0, y, cw, ch, values, gap=0, size=T_CELL, mono=True,
        fill=PALE, stroke=INK, color=INK, fills=None, strokes=None, colors=None,
        dashes=None, rx=4, widths=None):
    """Lay out a row of cells and return their boxes.

    For a grid, a buffer, or any picture where an element really is a cell.
    `labels` prints a small index under each cell.
    """
    boxes = []
    x = x0
    for i, value in enumerate(values):
        w = widths[i] if widths else cw
        f.cell(x, y, w, ch, value,
               fills[i] if fills else fill,
               strokes[i] if strokes else stroke,
               size=size, mono=mono,
               color=colors[i] if colors else color,
               dash=dashes[i] if dashes else False, rx=rx)
        boxes.append((x, y, w, ch))
        x += w + gap
    return boxes


def row_center(boxes, i):
    x, y, w, h = boxes[i]
    return x + w / 2.0, y + h / 2.0


def row_span(boxes, lo, hi, pad=8):
    x0, y0, _, h = boxes[lo]
    x1 = boxes[hi][0] + boxes[hi][2]
    return x0 - pad, y0 - pad, (x1 - x0) + 2 * pad, h + 2 * pad


def row_under(f, boxes, texts, y, color, size=T_MARK):
    for i, text in enumerate(texts):
        cx, _ = row_center(boxes, i)
        f.text(cx, y, str(text), size, color, anchor="middle")


def index_labels(f, boxes, y, labels=None, color=None, size=T_MARK):
    row_under(f, boxes, [str(labels[i]) if labels else str(i) for i in range(len(boxes))],
              y, color or MUTED, size)


def pointer_down(f, x, tip, label, color, size=T_MARK, gap=30, leader=True):
    """A chip above `tip`, for a picture whose elements are cells, not stations."""
    if leader:
        f.arrow(x, tip - gap + 12, x, tip - 3, color, 1.8)
    return chip(f, x, tip - gap - 4, label, color)


def pointer_up(f, x, tip, label, color, size=T_MARK, gap=30, leader=True):
    """A chip below `tip`."""
    if leader:
        f.arrow(x, tip + gap - 12, x, tip + 3, color, 1.8)
    return chip(f, x, tip + gap + 6, label, color)
