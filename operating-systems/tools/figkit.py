"""The drawing kit for the book's figures.

Every figure is a Material-style paper card: tonal containers with rounded
corners and no outline, elevated cards, icon tiles, and arrows with sharp
heads. A figure is drawn once and written twice, as a light and a dark SVG
that differ only in their style sheet. `theme/figures.js` shows the variant
that matches the reader's theme.

Icons in `icons/` are Material Icons (Apache License 2.0), from the
`@material-design-icons/svg` package, "round" style.
"""
import math
import re
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICONS = Path(__file__).resolve().parent / "icons"
OUT = ROOT / "src" / "figures"

WIDTH = 800
MARGIN = 28

# tone: (container, mid, accent)
LIGHT = {
    "paper": "#FFFFFF", "card": "#FFFFFF", "ink": "#1B1F27", "muted": "#566070",
    "hair": "#DCE0E7", "shadow": "#1B2430", "shadow_opacity": "0.14",
    "tones": {
        "blue": ("#E6EFFD", "#C7DBFA", "#1A5FC4"),
        "green": ("#E2F4E7", "#BEE5C9", "#1B7A3A"),
        "amber": ("#FFF1D9", "#FFDDA1", "#9A5600"),
        "red": ("#FDE8E4", "#F8C8BF", "#BF3620"),
        "purple": ("#EFE9FC", "#D9CDF8", "#6240C4"),
        "teal": ("#DDF3F1", "#B3E3DE", "#0E7168"),
        "gray": ("#EEF0F4", "#D9DDE5", "#566070"),
        "wire": ("#EEF0F4", "#D9DDE5", "#5B6676"),
    },
}

DARK = {
    "is_dark": True,
    "paper": "#12161F", "card": "#1E2636", "card_stroke": "#4E6080",
    "ink": "#F8FAFC", "muted": "#D8E0EE",
    "hair": "#3E4C66", "shadow": "#000000", "shadow_opacity": "0.35",
    "tones": {
        "blue":   ("#182B49", "#1E3A63", "#93C5FD"),
        "green":  ("#133328", "#184D3B", "#86EFAC"),
        "amber":  ("#34250F", "#4F3814", "#FDE078"),
        "red":    ("#3A1B23", "#582430", "#FDA4AF"),
        "purple": ("#261E47", "#382B6B", "#DDD6FE"),
        "teal":   ("#113136", "#164A52", "#5EEAD4"),
        "gray":   ("#1E2534", "#2C364A", "#D8E0EE"),
        "wire":   ("#1E2534", "#2C364A", "#CBD5E1"),
    },
}

SANS = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
MONO = '"SF Mono", SFMono-Regular, ui-monospace, Menlo, Consolas, monospace'

# class: (font size, line height, bold, mono)
FONTS = {
    "title": (17.5, 24, True, False),
    "head": (15.5, 21, True, False),
    "name": (15, 20, True, False),
    "body": (13.5, 18, False, False),
    "sub": (13, 17.5, False, False),
    "mono": (12.5, 17.5, False, True),
    "monob": (12.5, 17.5, True, True),
    "small": (12, 16, False, False),
    "note": (13.5, 20, False, False),
    "noteb": (13.5, 20, True, False),
}


def style(theme):
    """The style sheet and shared definitions for one theme."""
    is_dark = theme.get("is_dark", False)
    card_stroke = f" stroke: {theme['card_stroke']}; stroke-width: 1;" if is_dark else ""
    rules = [
        f"text {{ font-family: {SANS}; fill: {theme['ink']}; }}",
        f".paper {{ fill: {theme['paper']}; }}",
        f".frame {{ fill: {theme['paper']}; stroke: {theme['hair']}; stroke-width: 1.2; }}",
        f".card {{ fill: {theme['card']};{card_stroke} }}",
        f".hair {{ stroke: {theme['hair']}; stroke-width: 1.2; fill: none; }}",
        f".muted {{ fill: {theme['muted']}; }}",
        f".ink {{ fill: {theme['ink']}; }}",
    ]
    for cls, (size, _, bold, mono) in FONTS.items():
        family = f" font-family: {MONO};" if mono else ""
        weight = " font-weight: 650;" if bold else ""
        rules.append(f".{cls} {{ font-size: {size}px;{weight}{family} }}")
    rules.append(f".sub, .small, .note {{ fill: {theme['muted']}; }}")
    for tone, (container, mid, accent) in theme["tones"].items():
        if is_dark and tone not in ("wire",):
            rules.append(f".c-{tone} {{ fill: {container}; stroke: {accent}; stroke-opacity: 0.48; stroke-width: 1.2; }}")
            rules.append(f".m-{tone} {{ fill: {mid}; stroke: {accent}; stroke-opacity: 0.78; stroke-width: 1.2; }}")
        else:
            rules.append(f".c-{tone} {{ fill: {container}; }}")
            rules.append(f".m-{tone} {{ fill: {mid}; }}")
        rules.append(f".a-{tone} {{ fill: {accent}; }}")
        rules.append(f".t-{tone} {{ fill: {accent}; }}")
        rules.append(f".w-{tone} {{ stroke: {accent}; fill: none; stroke-linecap: butt; stroke-linejoin: round; }}")
        rules.append(f".o-{tone} {{ stroke: {accent}; fill: none; stroke-width: 1.5; }}")
        rules.append(f".h-{tone} {{ stroke: {accent}; stroke-width: 1.4; }}")
    body = "\n    ".join(rules)
    return f"""  <style>
    {body}
  </style>
  <defs>
    <filter id="lift" x="-10%" y="-15%" width="120%" height="140%">
      <feDropShadow dx="0" dy="1" stdDeviation="1.2" flood-color="{theme['shadow']}" flood-opacity="{theme['shadow_opacity']}"/>
      <feDropShadow dx="0" dy="3" stdDeviation="4" flood-color="{theme['shadow']}" flood-opacity="{float(theme['shadow_opacity']) * 0.7:.2f}"/>
    </filter>
  </defs>"""


NARROW = set("iljI.,:;'|!` ")
SLIM = set("ftr()[]-/\\\"·*")
WIDE = {"m": 0.86, "w": 0.76, "M": 0.88, "W": 0.96, "—": 1.0, "→": 1.0, "←": 1.0, "↑": 0.6,
        "↓": 0.6, "…": 1.0, "%": 0.9, "@": 1.0, "–": 0.58}


def char_width(char):
    """The width of one character in ems, for a Helvetica-like face."""
    if char in WIDE:
        return WIDE[char]
    if char in NARROW:
        return 0.29
    if char in SLIM:
        return 0.36
    if char.isupper():
        return 0.7
    if char.isdigit():
        return 0.6
    return 0.57


def width_of(body, cls="sub"):
    """A cautious estimate of how wide `body` renders, in pixels."""
    size, _, bold, mono = FONTS[cls]
    if mono:
        return len(body) * size * 0.61
    ems = sum(char_width(char) for char in body)
    return ems * size * (1.01 if bold else 0.975)


def wrap(body, room, cls="note"):
    """Breaks `body` into lines that fit `room` pixels, of about equal length."""
    lines = fill(body, room, cls)
    narrow = room
    while narrow > room * 0.5 and len(fill(body, narrow - 12, cls)) == len(lines):
        narrow -= 12
    return fill(body, narrow, cls)


def fill(body, room, cls):
    """Packs words greedily into lines of at most `room` pixels."""
    glued = re.sub(r"\b(Chapter|Section|Figure) ", "\\1\u00a0", body).replace(" —", "\u00a0—")
    lines, current = [], ""
    for word in glued.split(" "):
        trial = f"{current} {word}".strip()
        if current and width_of(trial, cls) > room:
            lines.append(current)
            current = word
            continue
        current = trial
    lines.append(current)
    return [line.replace("\u00a0", " ") for line in lines]


def icon_markup(name):
    """The paths of one Material icon, on its 24 x 24 grid."""
    source = (ICONS / f"{name}.svg").read_text()
    inner = re.sub(r"^<svg[^>]*>|</svg>\s*$", "", source.strip())
    return inner


class Box:
    """A placed rectangle, with the points wires attach to."""

    def __init__(self, x, y, w, h):
        self.x, self.y, self.w, self.h = x, y, w, h
        self.r, self.b = x + w, y + h
        self.cx, self.cy = x + w / 2, y + h / 2

    def left(self, dy=0):
        return (self.x, self.cy + dy)

    def right(self, dy=0):
        return (self.r, self.cy + dy)

    def top(self, dx=0):
        return (self.cx + dx, self.y)

    def bottom(self, dx=0):
        return (self.cx + dx, self.b)


def normalize(items):
    """Turns ["Title", "sub line"] into [(text, class)] pairs."""
    pairs = []
    for index, item in enumerate(items):
        if isinstance(item, tuple):
            pairs.append(item)
            continue
        pairs.append((item, "name" if index == 0 else "sub"))
    return pairs


class Fig:
    """One figure. Coordinates passed to the drawing methods start at the
    top-left corner of the content area, below the title."""

    def __init__(self, name, title, height):
        self.name = name
        self.height = height
        self.parts = []
        self.problems = []
        self.title_lines = wrap(title, WIDTH - 2 * MARGIN, "title")
        self.top = 36 + 24 * len(self.title_lines) + 14

    # ---- primitives -------------------------------------------------

    def add(self, markup):
        self.parts.append(markup)

    def rect(self, x, y, w, h, cls, r=14, lift=False, extra=""):
        shadow = ' filter="url(#lift)"' if lift else ""
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" class="{cls}"{shadow}{extra}/>')

    def text(self, x, y, body, cls="sub", anchor="start", tone=None, fit=None, rotate=None):
        size = FONTS[cls][0]
        wide = width_of(body, cls)
        start = {"start": x, "middle": x - wide / 2, "end": x - wide}[anchor]
        low, high = fit if fit else (4, WIDTH - 4)
        if rotate is None and (start < low - 0.5 or start + wide > high + 0.5):
            self.problems.append(f"{body!r} spans {start:.0f}..{start + wide:.0f}, room {low:.0f}..{high:.0f}")
        classes = cls + (f" t-{tone}" if tone else "")
        attrs = f' text-anchor="{anchor}"' if anchor != "start" else ""
        if fit and rotate is None:
            attrs += f' data-fit="{low:.1f},{high:.1f}"'
        if rotate is not None:
            attrs += f' transform="rotate({rotate} {x:.1f} {y - size * 0.35:.1f})"'
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" class="{classes}"{attrs}>{escape(body)}</text>')

    def lines(self, x, cy, items, anchor="middle", fit=None, tone=None, max_h=None):
        """Stacks lines of text and centers the stack on `cy`, respecting `max_h`."""
        pairs = normalize(items)
        raw_total = sum(FONTS[cls][1] for _, cls in pairs)
        scale = 1.0
        if max_h is not None and len(pairs) > 1 and raw_total > max_h:
            scale = max(0.76, max_h / raw_total)
        total = raw_total * scale
        cursor = cy - total / 2
        for body, cls in pairs:
            size, line_height = FONTS[cls][0], FONTS[cls][1] * scale
            baseline = cursor + line_height / 2 + size * 0.33
            line_tone = tone if cls in ("sub", "small", "body", "mono") and tone else None
            self.text(x, baseline, body, cls, anchor, tone=line_tone, fit=fit)
            cursor += line_height
        return total

    def icon(self, x, y, name, tone, size=20):
        scale = size / 24
        self.add(f'<g transform="translate({x:.1f} {y:.1f}) scale({scale:.3f})" class="a-{tone}">{icon_markup(name)}</g>')

    def tile(self, x, y, name, tone, size=34, fill=None):
        """An icon on a rounded tonal square."""
        self.rect(x, y, size, size, fill or f"m-{tone}", r=round(size * 0.3))
        glyph = size * 0.62
        self.icon(x + (size - glyph) / 2, y + (size - glyph) / 2, name, tone, glyph)
        return Box(x, y, size, size)

    # ---- containers -------------------------------------------------

    def node(self, x, y, w, h, tone, items=(), icon=None, layout="left", kind="tonal",
             r=14, icon_size=34, text_tone=None):
        """A container with an optional icon tile and stacked text.

        kind: "tonal" (tinted, flat), "mid" (stronger tint, for cells),
        "card" (elevated surface), "dashed" (outlined placeholder).
        """
        if kind == "tonal":
            self.rect(x, y, w, h, f"c-{tone}", r)
        if kind == "mid":
            self.rect(x, y, w, h, f"m-{tone}", r)
        if kind == "card":
            self.rect(x, y, w, h, "card", r, lift=True)
        if kind == "dashed":
            self.rect(x, y, w, h, f"o-{tone}", r, extra=' stroke-dasharray="6 5"')

        box = Box(x, y, w, h)
        tile_fill = f"c-{tone}" if kind == "card" else f"m-{tone}"
        if kind == "mid":
            tile_fill = "card"

        v_pad = 8.0 if h >= 38 else 5.5
        avail_h = max(14.0, h - 2 * v_pad)

        if layout == "left":
            text_x = x + 14
            if icon:
                eff_icon = min(icon_size, max(20, h - 14))
                self.tile(x + 12, box.cy - eff_icon / 2, icon, tone, eff_icon, tile_fill)
                text_x = x + 12 + eff_icon + 11
            if items:
                self.lines(text_x, box.cy, items, "start", fit=(text_x, box.r - 8), tone=text_tone, max_h=avail_h)
            return box

        pairs = normalize(items)
        raw_text_h = sum(FONTS[cls][1] for _, cls in pairs)
        eff_icon = icon_size
        icon_gap = 6.0 if icon else 0.0
        if icon and (eff_icon + icon_gap + raw_text_h) > avail_h:
            eff_icon = max(20, min(icon_size, round(avail_h * 0.30)))
            icon_gap = 4.0
        text_avail = max(12.0, avail_h - (eff_icon + icon_gap if icon else 0.0))
        scale = 1.0
        if len(pairs) > 1 and raw_text_h > text_avail:
            scale = max(0.76, text_avail / raw_text_h)
        text_height = raw_text_h * scale
        stack = text_height + (eff_icon + icon_gap if icon else 0.0)
        cursor = box.cy - stack / 2
        if icon:
            self.tile(box.cx - eff_icon / 2, cursor, icon, tone, eff_icon, tile_fill)
            cursor += eff_icon + icon_gap
        if pairs:
            self.lines(box.cx, cursor + text_height / 2, pairs, "middle", fit=(x + 5, box.r - 5), tone=text_tone, max_h=text_avail)
        return box

    def cell(self, x, y, w, h, tone, items=(), kind="mid", r=7, text_tone=None):
        """A small box with centered text."""
        return self.node(x, y, w, h, tone, items, layout="center", kind=kind, r=r, text_tone=text_tone)

    def heading(self, x, y, body, icon=None, tone="gray", anchor="start"):
        """A section label such as "before" or "after"."""
        if not icon:
            self.text(x, y, body, "head", anchor)
            return
        wide = width_of(body, "head")
        start = x if anchor == "start" else x - (wide + 26) / 2
        self.icon(start, y - 15, icon, tone, 19)
        self.text(start + 26, y, body, "head")

    def label(self, x, y, body, tone=None, cls="sub", anchor="middle", backed=True):
        """A wire label, on a paper-colored backing so the wire does not cross it."""
        wide = width_of(body, cls) + 10
        size = FONTS[cls][0]
        start = {"start": x - 5, "middle": x - wide / 2, "end": x - wide + 5}[anchor]
        if backed:
            self.rect(start, y - size, wide, size + 6, "paper", r=4)
        self.text(x, y, body, cls, anchor, tone=tone)

    def hatch(self, x, y, w, h, tone, r=6):
        """A striped cell, for padding and unused space."""
        self.rect(x, y, w, h, f"c-{tone}", r)
        clip = f"clip-{len(self.parts)}"
        stripes = "".join(
            f'<line x1="{x + offset:.1f}" y1="{y + h:.1f}" x2="{x + offset + h:.1f}" y2="{y:.1f}" class="h-{tone}" opacity="0.45"/>'
            for offset in range(-int(h), int(w), 9)
        )
        self.add(f'<clipPath id="{clip}"><rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}"/></clipPath>'
                 f'<g clip-path="url(#{clip})">{stripes}</g>')
        return Box(x, y, w, h)

    # ---- wires ------------------------------------------------------

    def head(self, tip, direction, tone, length=10.0):
        """A sharp, swept-back arrowhead whose tip lands on `tip`."""
        ux, uy = direction
        nx, ny = -uy, ux
        half = length * 0.42
        back = (tip[0] - ux * length, tip[1] - uy * length)
        notch = (tip[0] - ux * length * 0.72, tip[1] - uy * length * 0.72)
        points = [tip, (back[0] + nx * half, back[1] + ny * half), notch, (back[0] - nx * half, back[1] - ny * half)]
        path = " ".join(f"{px:.1f},{py:.1f}" for px, py in points)
        self.add(f'<polygon points="{path}" class="a-{tone}"/>')

    def wire(self, points, tone="wire", dash=False, head=True, tail=False, width=1.8, radius=8):
        """A polyline with rounded corners and arrowheads drawn at its ends."""
        points = [tuple(map(float, point)) for point in points]

        def unit(a, b):
            dx, dy = b[0] - a[0], b[1] - a[1]
            size = math.hypot(dx, dy) or 1.0
            return dx / size, dy / size, size

        ux, uy, last = unit(points[-2], points[-1])
        head_length = min(10.0, max(5.5, last * 0.45))
        end = points[-1]
        if head:
            self.head(end, (ux, uy), tone, head_length)
            points[-1] = (end[0] - ux * head_length * 0.7, end[1] - uy * head_length * 0.7)

        sx, sy, first = unit(points[1], points[0])
        tail_length = min(10.0, max(5.5, first * 0.45))
        start = points[0]
        if tail:
            self.head(start, (sx, sy), tone, tail_length)
            points[0] = (start[0] - sx * tail_length * 0.7, start[1] - sy * tail_length * 0.7)

        path = f"M{points[0][0]:.1f},{points[0][1]:.1f}"
        for index in range(1, len(points) - 1):
            before, corner, after = points[index - 1], points[index], points[index + 1]
            ax, ay, into = unit(corner, before)
            bx, by, out = unit(corner, after)
            cut = min(radius, into / 2, out / 2)
            path += f" L{corner[0] + ax * cut:.1f},{corner[1] + ay * cut:.1f}"
            path += f" Q{corner[0]:.1f},{corner[1]:.1f} {corner[0] + bx * cut:.1f},{corner[1] + by * cut:.1f}"
        path += f" L{points[-1][0]:.1f},{points[-1][1]:.1f}"

        dashes = ' stroke-dasharray="6 5"' if dash else ""
        self.add(f'<path d="{path}" class="w-{tone}" stroke-width="{width}"{dashes}/>')

    def arc(self, start, end, depth, tone="wire", dash=False, width=1.6):
        """A curved wire that bows by `depth` pixels (down when positive)."""
        c1 = (start[0], start[1] + depth)
        c2 = (end[0], end[1] + depth)
        dx, dy = end[0] - c2[0], end[1] - c2[1]
        size = math.hypot(dx, dy) or 1.0
        ux, uy = dx / size, dy / size
        self.head(end, (ux, uy), tone, 9.0)
        stop = (end[0] - ux * 6.3, end[1] - uy * 6.3)
        dashes = ' stroke-dasharray="6 5"' if dash else ""
        self.add(f'<path d="M{start[0]:.1f},{start[1]:.1f} C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {stop[0]:.1f},{stop[1]:.1f}" '
                 f'class="w-{tone}" stroke-width="{width}"{dashes}/>')

    def rule(self, x1, y1, x2, y2, tone="gray", width=1.4, dash=None):
        dashes = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="w-{tone}" stroke-width="{width}"{dashes}/>')

    # ---- output -----------------------------------------------------

    def render(self, theme, notes):
        note_width = WIDTH - 2 * MARGIN - 62
        note_lines = []
        for note in notes:
            body, cls = note if isinstance(note, tuple) else (note, "note")
            for line in wrap(body, note_width, cls):
                note_lines.append((line, cls))
            note_lines.append(None)
        note_lines = note_lines[:-1] if note_lines else []

        note_top = self.top + self.height + 22
        note_height = sum(8 if line is None else 20 for line in note_lines) + 28 if note_lines else 0
        total = note_top + note_height + (24 if note_lines else 18)

        out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {total:.0f}" width="{WIDTH}" height="{total:.0f}">',
               style(theme),
               f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{total - 1:.0f}" rx="16" class="frame"/>']

        baseline = 44
        for index, line in enumerate(self.title_lines):
            match = re.match(r"(Figure [\d-]+\.)\s*(.*)", line) if index == 0 else None
            if match:
                out.append(f'<text x="{MARGIN}" y="{baseline}" class="title"><tspan class="t-blue">{escape(match.group(1))}</tspan> {escape(match.group(2))}</text>')
            else:
                out.append(f'<text x="{MARGIN}" y="{baseline}" class="title">{escape(line)}</text>')
            baseline += 24

        out.append(f'<g transform="translate(0 {self.top})">')
        out.extend(self.parts)
        out.append("</g>")

        if note_lines:
            out.append(f'<rect x="{MARGIN}" y="{note_top}" width="{WIDTH - 2 * MARGIN}" height="{note_height}" rx="12" class="c-gray"/>')
            out.append(f'<g transform="translate({MARGIN + 14} {note_top + 12}) scale(0.833)" class="a-gray">{icon_markup("info")}</g>')
            cursor = note_top + 12
            for line in note_lines:
                if line is None:
                    cursor += 8
                    continue
                body, cls = line
                extra = " ink" if cls == "noteb" else ""
                out.append(f'<text x="{MARGIN + 46}" y="{cursor + 14.5:.1f}" class="{cls}{extra}" data-fit="{MARGIN + 46},{WIDTH - MARGIN - 12}">{escape(body)}</text>')
                cursor += 20

        out.append("</svg>")
        return "\n".join(out) + "\n"

    def save(self, notes=()):
        for problem in self.problems:
            print(f"does not fit [{self.name}]: {problem}")
        (OUT / "dark").mkdir(parents=True, exist_ok=True)
        (OUT / f"{self.name}.svg").write_text(self.render(LIGHT, notes))
        (OUT / "dark" / f"{self.name}.svg").write_text(self.render(DARK, notes))
