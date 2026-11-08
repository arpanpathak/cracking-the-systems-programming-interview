"""Drawing primitives for the chapter plates, shared in style with Democratizing Linux.

The functions return SVG fragments as strings. `art.py` composes them into plates.
"""

import math
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


def outline(stroke, sw):
    """The stroke attributes, or nothing, so that a shape inherits its group's outline."""
    return f' stroke="{stroke}" stroke-width="{sw}"' if stroke != "none" else ""


def rect(x, y, w, h, fill, rx=0, stroke="none", sw=0, extra=""):
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}"'
            f'{outline(stroke, sw)} {extra}/>')


def ellipse(cx, cy, rx, ry, fill, extra=""):
    return f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{fill}" {extra}/>'


def circle(cx, cy, r, fill, extra=""):
    return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}" fill="{fill}" {extra}/>'


def path(d, fill="none", stroke="none", sw=0, extra=""):
    return (f'<path d="{d}" fill="{fill}"{outline(stroke, sw)} stroke-linecap="round"'
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


def sparkle(cx, cy, r, fill=SNOW, opacity=0.9):
    return path(f"M{cx},{cy - r} Q{cx},{cy} {cx + r},{cy} Q{cx},{cy} {cx},{cy + r} Q{cx},{cy} {cx - r},{cy} Q{cx},{cy} {cx},{cy - r} Z",
                fill, extra=f'opacity="{opacity}"')


def pine(cx, base, h, fill):
    return "\n".join(path(f"M{cx - h * (0.30 - 0.07 * k):.1f},{base - h * 0.28 * k:.1f} L{cx:.1f},{base - h * (0.52 + 0.24 * k):.1f}"
                          f" L{cx + h * (0.30 - 0.07 * k):.1f},{base - h * 0.28 * k:.1f} Z", fill) for k in range(3))



# ------------------------------------------------------------- finishing

DEFS = ('<defs>'
        '<filter id="lift" x="-20%" y="-20%" width="140%" height="140%">'
        '<feDropShadow dx="0" dy="4" stdDeviation="4" flood-color="#000000" flood-opacity="0.35"/></filter>'
        '<radialGradient id="gloss" cx="0.35" cy="0.3" r="0.7"><stop offset="0" stop-color="#ffffff" stop-opacity="0.38"/>'
        '<stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient>'
        '<radialGradient id="under" cx="0.5" cy="0.9" r="0.7"><stop offset="0" stop-color="#000000" stop-opacity="0.28"/>'
        '<stop offset="1" stop-color="#000000" stop-opacity="0"/></radialGradient>'
        '<radialGradient id="vignette" cx="0.5" cy="0.45" r="0.75"><stop offset="0.6" stop-color="#000000" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#000000" stop-opacity="0.45"/></radialGradient>'
        '</defs>')


def crew(*parts, ink="#141c26"):
    """A character: its shapes share an outline and a soft shadow, which gives the flat shapes weight."""
    return (f'<g stroke="{ink}" stroke-width="2.2" stroke-opacity="0.7" stroke-linejoin="round" filter="url(#lift)">'
            + "\n".join(parts) + "</g>")


def gloss(cx, cy, rx, ry, extra=""):
    """Light from the upper left and shade underneath, laid over a rounded shape."""
    return "\n".join([f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="url(#under)" stroke="none" {extra}/>',
                      f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="url(#gloss)" stroke="none" {extra}/>'])


def limb(x, y, length, angle, width, fill, hand=None):
    """An arm from the shoulder at (x, y). `angle` is in degrees from straight down, positive towards +x.
    Returns the parts and the position of the hand."""
    a = math.radians(angle)
    ex, ey = x + length * math.sin(a), y + length * math.cos(a)
    parts = [f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{ex:.1f}" y2="{ey:.1f}" stroke="{fill}" stroke-width="{width:.1f}"'
             f' stroke-linecap="round"/>']

    if hand is not None:
        r = width * 0.62
        parts.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="{r:.1f}" fill="{hand}"/>')

        for k in (-1, 0, 1):
            fa = a + k * 0.55
            parts.append(f'<circle cx="{ex + r * 0.85 * math.sin(fa):.1f}" cy="{ey + r * 0.85 * math.cos(fa):.1f}"'
                         f' r="{r * 0.38:.1f}" fill="{hand}"/>')

    return "\n".join(parts), (ex, ey)


def arrow(points, fill="#ffd36b", sw=4, dash=False, head=14):
    """A curved arrow through 4 points (a cubic Bezier) with a solid head at the end."""
    (x0, y0), (x1, y1), (x2, y2), (x3, y3) = points
    angle = math.atan2(y3 - y2, x3 - x2)
    hx, hy = x3 - head * 0.6 * math.cos(angle), y3 - head * 0.6 * math.sin(angle)
    tip = [(x3, y3), (x3 - head * math.cos(angle - 0.45), y3 - head * math.sin(angle - 0.45)),
           (x3 - head * math.cos(angle + 0.45), y3 - head * math.sin(angle + 0.45))]
    extra = ' stroke-dasharray="9 7"' if dash else ""

    return "\n".join([
        f'<path d="M{x0:.1f},{y0:.1f} C{x1:.1f},{y1:.1f} {x2:.1f},{y2:.1f} {hx:.1f},{hy:.1f}" fill="none" stroke="{fill}"'
        f' stroke-width="{sw}" stroke-linecap="round"{extra}/>',
        '<polygon points="' + " ".join(f"{px:.1f},{py:.1f}" for px, py in tip) + f'" fill="{fill}"/>'])


def straight(x0, y0, x3, y3, fill="#ffd36b", sw=4, dash=False, head=14):
    return arrow([(x0, y0), (x0 + (x3 - x0) / 3, y0 + (y3 - y0) / 3), (x0 + 2 * (x3 - x0) / 3, y0 + 2 * (y3 - y0) / 3),
                  (x3, y3)], fill, sw, dash, head)
