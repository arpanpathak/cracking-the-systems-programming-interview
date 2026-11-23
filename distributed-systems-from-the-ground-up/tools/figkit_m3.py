"""Material Design 3 figure drawing kit for Distributed Systems from the Ground Up.

Ported from Operating Systems: A Hands-On Approach (`operating-systems/tools/figkit.py`).
Every figure renders as a clean Material 3 tonal card diagram in paired light and dark
SVG variants under `src/figures/m3/` and `src/figures/m3/dark/`. `theme/figures.js`
selects the matching variant automatically for light, dark, and print contexts.

Icons in `tools/m3_icons/` are Material Icons Round (Apache License 2.0).
"""
import math
import re
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ICONS = Path(__file__).resolve().parent / "m3_icons"
OUT = ROOT / "src" / "figures" / "m3"

WIDTH = 920
MARGIN = 32

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

# Adaptive, soothing, high-contrast dark palette:
# Uses a translucent outer canvas (.frame) and translucent hue-coded containers so every
# diagram harmonizes natively with Night Owl (#011627), Deep Ocean (#0F111A), and
# Oceanic Next (#1B2B34), with Material 3 tonal elevation instead of muddy drop shadows.
# Perceptually calibrated (APCA / OKLCH) dark palette:
# Avoids pure #FFFFFF halation and neon chroma vibration; uses calm off-white ink (#E4E9F2,
# APCA Lc ~86), legible secondary text (#B4C0D2, Lc ~66), and desaturated pastel accents
# (OKLCH L~0.79, C~0.10) over a gently elevated translucent surface that adapts to coal,
# navy, and ayu with zero eye strain.
DARK = {
    "is_dark": True,
    "paper": "#121722", "frame_fill": "rgba(0, 0, 0, 0.22)",
    "card": "rgba(13, 18, 28, 0.80)", "card_stroke": "rgba(203, 213, 225, 0.24)",
    "ink": "#F2F6FC", "muted": "#D0DAE8",
    "hair": "rgba(226, 232, 240, 0.18)", "shadow": "#000000", "shadow_opacity": "0.0",
    "tones": {
        "blue":   ("rgba(137, 180, 250, 0.08)", "rgba(137, 180, 250, 0.16)", "#89B4FA"),
        "green":  ("rgba(166, 227, 161, 0.08)", "rgba(166, 227, 161, 0.15)", "#A6E3A1"),
        "amber":  ("rgba(242, 201, 138, 0.08)", "rgba(242, 201, 138, 0.16)", "#F2C98A"),
        "red":    ("rgba(243, 166, 178, 0.08)", "rgba(243, 166, 178, 0.16)", "#F3A6B2"),
        "purple": ("rgba(200, 182, 255, 0.08)", "rgba(200, 182, 255, 0.16)", "#C8B6FF"),
        "teal":   ("rgba(137, 216, 211, 0.08)", "rgba(137, 216, 211, 0.15)", "#89D8D3"),
        "gray":   ("rgba(226, 232, 240, 0.04)", "rgba(226, 232, 240, 0.10)", "#CBD5E4"),
        "wire":   ("rgba(226, 232, 240, 0.04)", "rgba(226, 232, 240, 0.10)", "#AAB7C9"),
    },
}

SANS = '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif'
MONO = '"SF Mono", SFMono-Regular, ui-monospace, Menlo, Consolas, monospace'

# class: (font size, line height, bold, mono)
FONTS = {
    "title": (17.0, 23, True, False),
    "head": (14.5, 20, True, False),
    "name": (14.0, 19, True, False),
    "body": (13.0, 17.5, False, False),
    "sub": (12.2, 16.5, False, False),
    "mono": (11.8, 16.5, False, True),
    "monob": (11.8, 16.5, True, True),
    "small": (11.2, 15, False, False),
    "badge": (10.5, 14, True, False),
    "note": (12.8, 19, False, False),
    "noteb": (12.8, 19, True, False),
}


def style(theme):
    """The style sheet and shared definitions for one theme."""
    is_dark = theme.get("is_dark", False)
    frame_fill = theme.get("frame_fill", theme["paper"])
    card_stroke = f" stroke: {theme['card_stroke']}; stroke-width: 1;" if is_dark else ""
    rules = [
        f"text {{ font-family: {SANS}; fill: {theme['ink']}; }}",
        f".paper {{ fill: {theme['paper']}; }}",
        f".frame {{ fill: {frame_fill}; stroke: {theme['hair']}; stroke-width: 1.2; }}",
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
    size, _, bold, mono = FONTS[cls]
    if mono:
        return len(body) * size * 0.66
    ems = sum(char_width(char) for char in body)
    return ems * size * (1.10 if bold else 1.05)


def wrap(body, room, cls="note"):
    lines = fill(body, room, cls)
    narrow = room
    while narrow > room * 0.5 and len(fill(body, narrow - 12, cls)) == len(lines):
        narrow -= 12
    return fill(body, narrow, cls)


def fill(body, room, cls):
    glued = re.sub(r"\b(Chapter|Section|Figure) ", "\\1\u00a0", body)
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
    source = (ICONS / f"{name}.svg").read_text()
    inner = re.sub(r"^<svg[^>]*>|</svg>\s*$", "", source.strip())
    return inner


class Box:
    """A placed rectangle, with anchor points for wire attachment."""

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
    pairs = []
    for index, item in enumerate(items):
        if isinstance(item, tuple):
            pairs.append(item)
            continue
        pairs.append((item, "name" if index == 0 else "sub"))
    return pairs


class Fig:
    """One Material 3 figure. Coordinates start at the top-left of the content area."""

    def __init__(self, name, title, height):
        self.name = name
        self.height = height
        self.parts = []
        self.problems = []
        self.title_lines = wrap(title, WIDTH - 2 * MARGIN, "title")
        self.top = 34 + 23 * len(self.title_lines) + 14

    def add(self, markup):
        self.parts.append(markup)

    def rect(self, x, y, w, h, cls, r=14, lift=False, extra=""):
        shadow = ' filter="url(#lift)"' if lift else ""
        self.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" class="{cls}"{shadow}{extra}/>')

    def circle(self, cx, cy, rad, cls, extra=""):
        self.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rad:.1f}" class="{cls}"{extra}/>')

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
            line_tone = tone if cls in ("sub", "small", "body", "mono", "badge") and tone else None
            self.text(x, baseline, body, cls, anchor, tone=line_tone, fit=fit)
            cursor += line_height
        return total

    def icon(self, x, y, name, tone, size=20):
        scale = size / 24
        self.add(f'<g transform="translate({x:.1f} {y:.1f}) scale({scale:.3f})" class="a-{tone}">{icon_markup(name)}</g>')

    def tile(self, x, y, name, tone, size=32, fill=None):
        self.rect(x, y, size, size, fill or f"m-{tone}", r=round(size * 0.3))
        glyph = size * 0.62
        self.icon(x + (size - glyph) / 2, y + (size - glyph) / 2, name, tone, glyph)
        return Box(x, y, size, size)

    def zone(self, x, y, w, h, tone, title, subtitle=None, icon=None, dashed=False, title_align="left"):
        """A tonal grouping container (e.g., Control Plane, Data Plane, PCI CDE, AZ)."""
        if dashed:
            self.rect(x, y, w, h, f"c-{tone}", r=16)
            self.rect(x, y, w, h, f"o-{tone}", r=16, extra=' stroke-dasharray="6 5"')
        else:
            self.rect(x, y, w, h, f"c-{tone}", r=16)
        if title_align == "center":
            cx = x + w / 2
            if subtitle:
                self.text(cx, y + 23, title, "head", "middle", tone=tone, fit=(x + 12, x + w - 12))
                self.text(cx, y + 38, subtitle, "small", "middle", fit=(x + 12, x + w - 12))
            else:
                self.text(cx, y + 28, title, "head", "middle", tone=tone, fit=(x + 12, x + w - 12))
            return Box(x, y, w, h)
        if title_align == "right":
            rx = x + w - 14
            if subtitle:
                self.text(rx, y + 23, title, "head", "end", tone=tone, fit=(x + 12, rx))
                self.text(rx, y + 38, subtitle, "small", "end", fit=(x + 12, rx))
            else:
                self.text(rx, y + 28, title, "head", "end", tone=tone, fit=(x + 12, rx))
            return Box(x, y, w, h)
        tx = x + 14
        if icon:
            self.tile(x + 12, y + 10, icon, tone, 28, f"m-{tone}")
            tx = x + 48
        if subtitle:
            self.text(tx, y + 23, title, "head", "start", tone=tone, fit=(tx, x + w - 10))
            self.text(tx, y + 38, subtitle, "small", "start", fit=(tx, x + w - 10))
        else:
            self.text(tx, y + 28, title, "head", "start", tone=tone, fit=(tx, x + w - 10))
        return Box(x, y, w, h)

    def pill(self, x, y, text, tone="blue", anchor="start"):
        """A compact Material tonal chip/badge."""
        w = width_of(text, "badge") + 16
        h = 20
        rx = {"start": x, "middle": x - w / 2, "end": x - w}[anchor]
        self.rect(rx, y, w, h, f"m-{tone}", r=10)
        self.text(rx + w / 2, y + 13.5, text, "badge", "middle", tone=tone, fit=(rx + 2, rx + w - 2))
        return Box(rx, y, w, h)

    def node(self, x, y, w, h, tone, items=(), icon=None, layout="left", kind="tonal",
             r=12, icon_size=32, text_tone=None):
        if kind == "tonal":
            self.rect(x, y, w, h, f"c-{tone}", r)
        elif kind == "mid":
            self.rect(x, y, w, h, f"m-{tone}", r)
        elif kind == "card":
            self.rect(x, y, w, h, "card", r, lift=True)
        elif kind == "dashed":
            self.rect(x, y, w, h, f"o-{tone}", r, extra=' stroke-dasharray="6 5"')

        box = Box(x, y, w, h)
        tile_fill = f"c-{tone}" if kind == "card" else f"m-{tone}"
        if kind == "mid":
            tile_fill = "card"

        v_pad = 10.0 if h >= 44 else 6.0
        avail_h = max(14.0, h - 2 * v_pad)

        if layout == "left":
            text_x = x + 16
            if icon:
                eff_icon = min(icon_size, max(22, h - 18))
                self.tile(x + 14, box.cy - eff_icon / 2, icon, tone, eff_icon, tile_fill)
                text_x = x + 14 + eff_icon + 12
            if items:
                self.lines(text_x, box.cy, items, "start", fit=(text_x, box.r - 12), tone=text_tone, max_h=avail_h)
            return box

        pairs = normalize(items)
        raw_text_h = sum(FONTS[cls][1] for _, cls in pairs)
        eff_icon = icon_size
        icon_gap = 5.0 if icon else 0.0
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
            self.lines(box.cx, cursor + text_height / 2, pairs, "middle", fit=(x + 10, box.r - 10), tone=text_tone, max_h=text_avail)
        return box

    def cell(self, x, y, w, h, tone, items=(), kind="mid", r=7, text_tone=None):
        return self.node(x, y, w, h, tone, items, layout="center", kind=kind, r=r, text_tone=text_tone)

    def heading(self, x, y, body, icon=None, tone="gray", anchor="start"):
        if not icon:
            self.text(x, y, body, "head", anchor, tone=tone if tone != "gray" else None)
            return
        wide = width_of(body, "head")
        start = x if anchor == "start" else x - (wide + 26) / 2
        self.icon(start, y - 15, icon, tone, 19)
        self.text(start + 26, y, body, "head", tone=tone if tone != "gray" else None)

    def label(self, x, y, body, tone=None, cls="small", anchor="middle", backed=True, back_cls="paper"):
        wide = width_of(body, cls) + 10
        size = FONTS[cls][0]
        start = {"start": x - 5, "middle": x - wide / 2, "end": x - wide + 5}[anchor]
        if backed:
            self.rect(start, y - size, wide, size + 5, back_cls, r=4)
        self.text(x, y, body, cls, anchor, tone=tone)

    def head(self, tip, direction, tone, length=9.5):
        ux, uy = direction
        nx, ny = -uy, ux
        half = length * 0.42
        back = (tip[0] - ux * length, tip[1] - uy * length)
        notch = (tip[0] - ux * length * 0.72, tip[1] - uy * length * 0.72)
        points = [tip, (back[0] + nx * half, back[1] + ny * half), notch, (back[0] - nx * half, back[1] - ny * half)]
        path = " ".join(f"{px:.1f},{py:.1f}" for px, py in points)
        self.add(f'<polygon points="{path}" class="a-{tone}"/>')

    def wire(self, points, tone="wire", dash=False, head=True, tail=False, width=1.8, radius=8):
        points = [tuple(map(float, point)) for point in points]

        def unit(a, b):
            dx, dy = b[0] - a[0], b[1] - a[1]
            size = math.hypot(dx, dy) or 1.0
            return dx / size, dy / size, size

        ux, uy, last = unit(points[-2], points[-1])
        head_length = min(9.5, max(5.5, last * 0.45))
        end = points[-1]
        if head:
            self.head(end, (ux, uy), tone, head_length)
            points[-1] = (end[0] - ux * head_length * 0.7, end[1] - uy * head_length * 0.7)

        sx, sy, first = unit(points[1], points[0])
        tail_length = min(9.5, max(5.5, first * 0.45))
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

        dashes = ' stroke-dasharray="6 4"' if dash else ""
        self.add(f'<path d="{path}" class="w-{tone}" stroke-width="{width}"{dashes}/>')

    def rule(self, x1, y1, x2, y2, tone="gray", width=1.4, dash=None):
        dashes = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" class="w-{tone}" stroke-width="{width}"{dashes}/>')

    def render(self, theme, notes):
        note_width = WIDTH - 2 * MARGIN - 62
        note_lines = []
        for note in notes:
            body, cls = note if isinstance(note, tuple) else (note, "note")
            for line in wrap(body, note_width, cls):
                note_lines.append((line, cls))
            note_lines.append(None)
        note_lines = note_lines[:-1] if note_lines else []

        note_top = self.top + self.height + 20
        note_height = sum(7 if line is None else 19 for line in note_lines) + 26 if note_lines else 0
        total = note_top + note_height + (22 if note_lines else 16)

        out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {total:.0f}" width="{WIDTH}" height="{total:.0f}">',
               style(theme),
               f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{total - 1:.0f}" rx="16" class="frame"/>']

        baseline = 42
        for index, line in enumerate(self.title_lines):
            match = re.match(r"(Figure [\d.-]+\.)\s*(.*)", line) if index == 0 else None
            if match:
                out.append(f'<text x="{MARGIN}" y="{baseline}" class="title"><tspan class="t-blue">{escape(match.group(1))}</tspan> {escape(match.group(2))}</text>')
            else:
                out.append(f'<text x="{MARGIN}" y="{baseline}" class="title">{escape(line)}</text>')
            baseline += 23

        out.append(f'<g transform="translate(0 {self.top})">')
        out.extend(self.parts)
        out.append("</g>")

        if note_lines:
            out.append(f'<rect x="{MARGIN}" y="{note_top}" width="{WIDTH - 2 * MARGIN}" height="{note_height}" rx="12" class="c-gray"/>')
            out.append(f'<g transform="translate({MARGIN + 14} {note_top + 11}) scale(0.833)" class="a-gray">{icon_markup("info")}</g>')
            cursor = note_top + 11
            for line in note_lines:
                if line is None:
                    cursor += 7
                    continue
                body, cls = line
                extra = " ink" if cls == "noteb" else ""
                out.append(f'<text x="{MARGIN + 46}" y="{cursor + 14.0:.1f}" class="{cls}{extra}" data-fit="{MARGIN + 46},{WIDTH - MARGIN - 12}">{escape(body)}</text>')
                cursor += 19

        out.append("</svg>")
        return "\n".join(out) + "\n"

    def save(self, notes=()):
        for problem in self.problems:
            print(f"does not fit [{self.name}]: {problem}")
        (OUT / "dark").mkdir(parents=True, exist_ok=True)
        (OUT / f"{self.name}.svg").write_text(self.render(LIGHT, notes))
        (OUT / "dark" / f"{self.name}.svg").write_text(self.render(DARK, notes))
        return len(self.problems)


def build_use_case_fig(name, title, boundary_title, boundary_sub, actors, cases, links, notes):
    """Spacious UML-inspired Material Design 3 use-case diagram (WIDTH = 920)."""
    n_cases = len(cases)
    case_h = 58
    case_gap = 16
    inner_h = 70 + n_cases * case_h + (n_cases - 1) * case_gap + 18
    total_h = max(360, inner_h + 10)
    f = Fig(name, title, total_h)

    bx = 346
    bw = WIDTH - MARGIN - bx
    f.zone(bx, 0, bw, total_h - 8, "blue", boundary_title, boundary_sub, icon="layers", dashed=True)

    case_boxes = []
    for idx, (uc_title, uc_sub, tone, ic) in enumerate(cases):
        cy = 68 + idx * (case_h + case_gap)
        box = f.node(bx + 22, cy, bw - 44, case_h, tone, [(uc_title, "name"), (uc_sub, "mono")], icon=ic, kind="card", icon_size=26)
        case_boxes.append(box)

    n_act = len(actors)
    act_h = 62
    # Align each actor vertically to the exact centroid of its linked use-case cards
    # so 1-to-1 links are dead-straight horizontal arrows and 1-to-N splits are symmetric
    # with ZERO wire crossings.
    target_ys = []
    link_map = {act_idx: uc_indices for act_idx, uc_indices, _ in links}
    for idx in range(n_act):
        ucs = link_map.get(idx, [])
        if ucs:
            mean_cy = sum(case_boxes[u].cy for u in ucs) / len(ucs)
            target_ys.append(mean_cy - act_h / 2)
        else:
            target_ys.append(68 + idx * (act_h + 16))

    min_gap = 10
    ys = list(target_ys)
    for i in range(1, n_act):
        if ys[i] < ys[i - 1] + act_h + min_gap:
            ys[i] = ys[i - 1] + act_h + min_gap
    max_y = total_h - 14 - act_h
    if n_act > 0 and ys[-1] > max_y:
        ys[-1] = max_y
        for i in range(n_act - 2, -1, -1):
            if ys[i] > ys[i + 1] - act_h - min_gap:
                ys[i] = ys[i + 1] - act_h - min_gap

    act_boxes = []
    for idx, (a_title, a_sub, tone, ic) in enumerate(actors):
        box = f.node(MARGIN, ys[idx], 248, act_h, tone, [(a_title, "name"), (a_sub, "sub")], icon=ic, kind="card", icon_size=28)
        act_boxes.append(box)

    # Exact symmetric midpoint corridor between actor right edge (280) and case left edge (368)
    bus_x = (MARGIN + 248 + bx + 22) / 2  # 324.0
    for act_idx, uc_indices, tone in links:
        ab = act_boxes[act_idx]
        if len(uc_indices) == 1:
            cb = case_boxes[uc_indices[0]]
            if abs(ab.cy - cb.cy) <= 1.5:
                f.wire([ab.right(0), cb.left(0)], tone=tone, width=1.9)
            else:
                f.wire([ab.right(0), (bus_x, ab.cy), (bus_x, cb.cy), cb.left(0)], tone=tone, width=1.9, radius=7)
        elif len(uc_indices) > 1:
            cys = [case_boxes[u].cy for u in uc_indices]
            y_min, y_max = min(cys), max(cys)
            f.wire([ab.right(0), (bus_x, ab.cy)], tone=tone, width=1.9, head=False)
            f.wire([(bus_x, min(y_min, ab.cy)), (bus_x, max(y_max, ab.cy))], tone=tone, width=1.9, head=False)
            for u in uc_indices:
                cb = case_boxes[u]
                f.wire([(bus_x, cb.cy), cb.left(0)], tone=tone, width=1.9)

    return f.save(notes)
