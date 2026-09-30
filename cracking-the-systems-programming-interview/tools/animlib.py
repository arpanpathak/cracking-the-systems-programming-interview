"""Shared helpers for the chapter animations, and the layout they all share.

`tools/animations.py` and the animation modules import these. A frame is a
`Frame`, which is a `Figure` with a fixed skeleton:

    title
    one line of orientation
    ------------------------------------------------
    the drawing area            <- the builder paints here, and only here
    ------------------------------------------------
    an insight band, when the step is the one that explains the idea
    the step sentence, in the largest body type on the canvas
    a note, when the frame needs one caveat
    name = value, name = value, name = value        <- pinned to the foot

The foot is laid out from the bottom up and measured before the canvas is
created, so a long sentence in one frame cannot push the counter row off the
canvas, and two frames of one animation always put the same furniture in the
same place. A reader following a moving picture leans on that stability.

The drawing area carries the part of the explanation a reader can see: a tinted
`zone` for the region under discussion, a `focus` wash that dims everything else,
a `ghost` left behind by whatever just moved, and a `chip` naming a pointer. The
insight band is saved for the single step where the idea clicks.
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
T_TITLE = 21.0
T_SUB = 13.5
T_STEP = 16.0
T_NOTE = 13.0
T_COUNTER = 14.5
T_CELL = 17.0
T_CHIP = 12.0
T_ZONE = 12.5

LEAD_STEP = 23.0
LEAD_NOTE = 18.0
LEAD_INSIGHT = 22.0

DIAGRAM_TOP = 88.0
LEGEND_ROW = 24.0

# The static chapter figures keep the plain scales; only the frame skeleton here
# changes how an animation is laid out.
Figure.type_scale = 1.0
Figure.height_scale = 1.0

Animation.speed = 1.0
Animation.hold = 1900
Animation.tween = 2
Animation.tween_ms = 110
Animation.scale = 1.85


def _lines(text, size, width, mono=False):
    return wrap(text, size, width, mono) if text else []


class Frame(Figure):
    """One step of an animation: a title, a drawing area, and a measured foot."""

    def __init__(self, title, sub=None, diagram=190, step=None, note=None, insight=None,
                 pairs=None, legend=None, glow=None, height=None, insight_rows=0):
        self.diagram = diagram
        self.title = title
        self.sub = sub
        self.step_text = step
        self.note_text = note
        self.insight_text = insight
        self.pairs = pairs or []
        self.legend_entries = legend
        self.glow_at = glow

        self.legend_row = LEGEND_ROW if legend else 0.0
        self.step_lines = _lines(step, T_STEP, CONTENT)
        self.note_lines = _lines(note, T_NOTE, CONTENT)
        self.insight_lines = _lines(insight, T_STEP - 1.0, CONTENT - 74)
        # The insight row is reserved for every frame of an animation that uses
        # one, so the sentence and the scoreboard below it never shift when the
        # band appears.
        self.insight_rows = max(insight_rows, len(self.insight_lines))

        self.top = DIAGRAM_TOP + self.legend_row
        self.bottom = self.top + diagram
        super().__init__(W, max(self._natural_height(), height or 0.0))
        self._furniture()

    def _natural_height(self):
        """The height at which the foot sits directly under the drawing."""
        return self.bottom + 22 + self._foot_height() + 18

    def _foot_height(self):
        foot = 0.0
        if self.insight_rows:
            foot += 20 + self.insight_rows * LEAD_INSIGHT + 6 + 16
        if self.step_lines:
            foot += len(self.step_lines) * LEAD_STEP + 6
        if self.note_lines:
            foot += len(self.note_lines) * LEAD_NOTE
        foot += 16 + 24
        return foot

    def _furniture(self):
        """Everything the builder never has to think about, laid out top-down.

        Every block below the drawing sits at a fixed offset, so a frame that
        carries an insight band and a frame that does not still agree on where
        the sentence, the note, and the scoreboard go. Only the white margin at
        the very foot of the canvas differs.
        """
        if self.glow_at:
            self.glow(*(self.glow_at))

        self.text(PAD, 32, self.title, T_TITLE, INK, bold=True, layer="text")
        if self.sub:
            self.text(PAD, 57, self.sub, T_SUB, MUTED, layer="text")
        if self.legend_entries:
            legend(self, 84, self.legend_entries)

        y = self.bottom + 22
        if self.insight_rows:
            band_h = 20 + self.insight_rows * LEAD_INSIGHT + 6
            if self.insight_lines:
                insight_band(self, y, self.insight_lines, band_h)
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

    # The drawing area, as a box, for the helpers that want one.
    def area(self, pad=0):
        return (PAD - pad, self.top - pad, CONTENT + 2 * pad, self.diagram + 2 * pad)

    def mid(self):
        return self.top + self.diagram / 2.0


def frames(make, specs):
    """Build every frame again until the whole animation shares one canvas.

    GIF frames cannot differ in height, and the frames of one animation have to
    keep the same furniture in the same place, so the tallest frame and the
    widest insight band set the shape for all of them. Reserving the insight row
    can make a frame taller, which can raise the tallest frame in turn, so the
    pass repeats until nothing moves. It settles after two rounds.
    """
    built = [make(spec) for spec in specs]
    for _ in range(4):
        tallest = max(frame.height for frame in built)
        rows = max(frame.insight_rows for frame in built)
        if all(abs(frame.height - tallest) < 0.01 and frame.insight_rows == rows
               for frame in built):
            return built
        built = [make(spec, tallest, rows) for spec in specs]
    return built


def publish(name, built, durations=None):
    Animation(built, durations).save(OUT / name)
    return name


# ------------------------------------------------------------------ furniture


def counter(f, y, pairs, size=T_COUNTER):
    """A row of `name = value` facts, spread evenly across the content width.

    The row is the frame's scoreboard: the values the listing beside it uses,
    spelled the way the listing spells them. Each pair is measured in monospace
    before it is drawn, so the columns land where the reader expects them.
    """
    if not pairs:
        return
    size = size * f.type_scale
    widths = [text_width("%s = " % name, size, True) + text_width(str(value), size, True)
              for name, value, _ in pairs]
    gap = (CONTENT - sum(widths)) / max(1, len(pairs) - 1)
    gap = max(24.0, min(gap, 110.0))
    x = PAD
    for (name, value, color) in pairs:
        label = "%s = " % name
        f.text(x, y, label, size, MUTED, mono=True, scaled=False, layer="text")
        x += text_width(label, size, True)
        f.text(x, y, str(value), size, color, mono=True, bold=True, scaled=False, layer="text")
        x += text_width(str(value), size, True) + gap


def insight_band(f, y, rows, height=None):
    """The band that marks the step where the idea clicks.

    Cream ground, a brass edge, and a lit bulb. It is the only furniture in the
    book drawn this way, so the reader learns in one frame that this is the step
    to remember. The band belongs to the label layer: it appears whole, rather
    than fading up under text that has already changed.
    """
    height = height or 20 + len(rows) * LEAD_INSIGHT + 6
    f.rect(PAD, y, CONTENT, height, CREAM, BRASS, 9, width=1.6, layer="text")
    f.rect(PAD, y, 6, height, BRASS, BRASS, 3, width=0.6, layer="text")
    by = y + 20 + (len(rows) - 1) * LEAD_INSIGHT / 2.0
    f.glow(PAD + 34, by, 26, BRASS, 0.5)
    f.circle(PAD + 34, by, 7.5, BRASS, BRASS, 1.2)
    f.text(PAD + 34, by + 4.5, "!", 10, WHITE, anchor="middle", bold=True, scaled=False,
           layer="text")
    for i, row in enumerate(rows):
        f.text(PAD + 56, y + 20 + i * LEAD_INSIGHT, row, T_STEP - 1.0, INK, bold=True,
               layer="text")
    return y + height


def legend(f, y, entries, size=T_CHIP + 0.5):
    """A key for the colours, right-aligned on its own row under the title.

    `entries` is a list of `(label, fill, stroke)`. Every animation that uses a
    colour to mean something carries one, so the picture never depends on the
    reader having read an earlier frame.
    """
    size = size * f.type_scale
    widths = [22 + text_width(label, size) for label, _, _ in entries]
    total = sum(widths) + 22 * (len(entries) - 1)
    x = W - PAD - total
    for (label, fill, stroke), width in zip(entries, widths):
        f.rect(x, y - 10, 14, 14, fill, stroke, 4, width=1.4, layer="text")
        f.text(x + 20, y, label, size, MUTED, scaled=False, layer="text")
        x += width + 22


# ------------------------------------------------------------------- pointer


def chip(f, x, y, label, color=TEAL, fill=WHITE, size=T_CHIP, mono=True):
    """A named pill that labels a pointer without a long leader line.

    The pill is a label, not a drawing, so it lands whole on the frame it
    belongs to. A pointer that glides leaves its arrow to do the gliding.
    """
    size = size * f.type_scale
    w = text_width(label, size, mono) + 20
    h = size + 12
    f.rect(x - w / 2, y - h / 2, w, h, fill, color, 6, width=1.5)
    f.text(x, y + size * 0.36, label, size, color, mono, "middle", bold=True, scaled=False)
    return (x - w / 2, y - h / 2, w, h)


def pointer_down(f, x, tip, label, color, size=T_CHIP, gap=30, leader=True):
    """A chip above `tip`, joined to it by a short arrow.

    `leader=False` drops the shaft. A shaft that would run through an index row
    costs more in legibility than it adds in pointing, and a chip sitting under
    its own column needs no help.
    """
    if leader:
        f.arrow(x, tip - gap + 12, x, tip - 3, color, 1.8)
    return chip(f, x, tip - gap - 4, label, color)


def pointer_up(f, x, tip, label, color, size=T_CHIP, gap=30, leader=True):
    """A chip below `tip`, joined to it by a short arrow."""
    if leader:
        f.arrow(x, tip + gap - 12, x, tip + 3, color, 1.8)
    return chip(f, x, tip + gap + 6, label, color)


def ghost(f, x, y, w, h, label=None, size=T_CELL, color="#b9c6d2"):
    """Where something used to be.

    A faint outline at the previous position turns a jump into a movement: the
    reader sees both ends of the step at once instead of inferring the change.
    """
    f.rect(x, y, w, h, "none", color, 4, width=1.4, dash=True)
    if label is not None:
        f.text(x + w / 2, y + h / 2 + size * f.type_scale * 0.36, label, size, color, True,
               "middle", scaled=False)


def track(f, x1, y1, x2, y2, color=TEAL, width=1.6, head=8.0):
    """A dotted line from where a thing was to where it now is."""
    f.arrow(x1, y1, x2, y2, color, width, dash=True, head=head)


# ---------------------------------------------------------------------- rows


def row(f, x0, y, cw, ch, values, gap=0, size=T_CELL, mono=True,
        fill=PALE, stroke=INK, color=INK, fills=None, strokes=None, colors=None,
        dashes=None, rx=4, widths=None):
    """Lay out a row of cells and return their boxes.

    `fills`, `strokes`, `colors`, and `dashes` override `fill`, `stroke`,
    `color`, and the dashed state for the entry at the same index. `widths`
    gives per-cell widths, for a row whose cells hold different amounts of text.
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
    """The centre point of cell `i` in a row returned by `row`."""
    x, y, w, h = boxes[i]
    return x + w / 2.0, y + h / 2.0


def row_span(boxes, lo, hi, pad=8):
    """A box that covers cells `lo` to `hi` inclusive, for a zone or a range."""
    x0, y0, _, h = boxes[lo]
    x1 = boxes[hi][0] + boxes[hi][2]
    return x0 - pad, y0 - pad, (x1 - x0) + 2 * pad, h + 2 * pad


def row_under(f, boxes, texts, y, color, size=T_CHIP):
    """A label centred under each cell, all in one colour."""
    for i, text in enumerate(texts):
        cx, _ = row_center(boxes, i)
        f.text(cx, y, str(text), size, color, anchor="middle")


def index_labels(f, boxes, y, labels=None, color=None, size=T_CHIP):
    """Index numbers centred under the cells of a row."""
    row_under(f, boxes, [str(labels[i]) if labels else str(i) for i in range(len(boxes))],
              y, color or MUTED, size)


def lead_out(f, box, text, color=INK, size=T_CHIP, above=True, gap=26):
    """A short leader from a box to a label, for annotating one cell."""
    x, y, w, h = box
    cx = x + w / 2.0
    ty = y - gap if above else y + h + gap
    f.arrow(cx, y - 6 if above else y + h + 6, cx, y - 2 if above else y + h + 2, color, 1.4)
    return chip(f, cx, ty, text, color)
