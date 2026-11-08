#!/usr/bin/env python3
"""Build the cover and the chapter-opener plates from the paintings.

Each plate is an SVG that embeds 1 picture from tools/paintings/ (made by
tools/paint.py) and draws the chapter's number, title and character over it as
text, so the lettering stays sharp at any size. The descriptions are written to
src/art/plates.json, and the chapters use them as alternative text.

    python3 tools/art.py              # every plate
    python3 tools/art.py ch03 cover   # some of them
"""

import base64
import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
PAINTINGS = ROOT / "tools" / "paintings"
OUT = ROOT / "src" / "art"
SANS = "Inter, Avenir Next, Helvetica Neue, Arial, sans-serif"
SERIF = "Georgia, Iowan Old Style, Times New Roman, serif"
ACCENT = "#d9622b"

PLATES = {
    "intro": ("I", "Introduction", "Bundle the stork",
              "Bundle, a white stork, stands on a wooden dock at dusk. Behind it a container ship loaded with stacked "
              "containers waits under cargo cranes."),
    "ch01": ("1", "A local copy of the cluster", "Ledger the owl",
             "Ledger, a great horned owl, sits on an open ledger at a library desk at night, under a warm desk lamp."),
    "ch01-1": ("1.1", "A controller on a real cluster", "Rivet the beaver",
               "Rivet, a beaver in a yellow hard hat, works at a bench in a workshop, fitting a part that glows green."),
    "ch02": ("2", "What one GPU means", "The hive",
             "A honeybee hovers beside honeycomb whose cells glow green, like the cells of a chip."),
    "ch03": ("3", "Knowing which machines are alive", "Doc the hound",
             "Doc, a basset hound in a white doctor's coat, stands in an aisle of a dark data center lit by status lights."),
    "ch04": ("4", "A control plane for a fleet", "Sergeant Cone the raccoon",
             "Sergeant Cone, a raccoon in a police cap and a reflective vest, directs traffic on a wet street at night, "
             "with police cars and traffic lights behind."),
    "ch05": ("5", "Kubernetes in a new account", "Badge the fox",
             "Badge, a red fox in a security uniform, stands guard at a gated checkpoint at night."),
    "ch06": ("6", "Virtual machines on Kubernetes", "Shellby the hermit crab",
             "Shellby, a hermit crab, crawls across the sand at sunset between shells, with the sea behind."),
    "ch07": ("7", "Collective communication", "The relay parrots",
             "6 macaws sit side by side on 1 branch in a rainforest, each next to its neighbours."),
    "ch08": ("8", "Placing jobs on GPUs", "Flock the sheepdog",
             "Flock, a border collie, sits in front of a flock of sheep by a fence on a hillside at sunset."),
    "ch09": ("9", "Counting across replicas", "The tally squirrels",
             "4 red squirrels sit side by side on a mossy branch in a forest."),
    "ch10": ("10", "A content-addressed artifact store", "Hash the magpie",
             "Hash, a magpie, perches on a wooden cabinet of small drawers and jars in a dim room."),
    "ch11": ("11", "A command-line tool for 3 systems", "Chroma the chameleon",
             "Chroma, a chameleon, stands on a desk in a dark room beside 2 glowing screens."),
    "appendix": ("A", "A local GPU cluster with kind", "Kindle the hedgehog",
                 "Kindle, a hedgehog, sits on a workbench beside a small computer and its screen, under a green lamp."),
}
COVER = ("The cover of GPU-Accelerated Kubernetes: a raccoon in a dark cape stands at the rail of a ship at night, under "
         "storm clouds and a full moon, with harbour lights behind.")


def picture(name):
    data = base64.b64encode((PAINTINGS / (name + ".jpg")).read_bytes()).decode()

    return f"data:image/jpeg;base64,{data}"


def text(x, y, body, size, fill, anchor="start", font=SANS, weight=700, extra=""):
    return (f'<text x="{x}" y="{y}" font-family="{font}" font-size="{size}" font-weight="{weight}" fill="{fill}"'
            f' text-anchor="{anchor}" {extra}>{escape(body)}</text>')


def plate(name, number, title, crew):
    """A 960 x 412 plate: the painting, a dark band at the foot, and the chapter's ribbon."""
    w, h = 960, 412

    return [
        '<defs><linearGradient id="foot" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0.45" stop-color="#05080d" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#05080d" stop-opacity="0.88"/></linearGradient></defs>',
        f'<image href="{picture(name)}" x="0" y="0" width="{w}" height="{h}" preserveAspectRatio="xMidYMid slice"/>',
        f'<rect x="0" y="0" width="{w}" height="{h}" fill="url(#foot)"/>',
        f'<rect x="32" y="{h - 92}" width="6" height="62" fill="{ACCENT}"/>',
        text(52, h - 64, "CHAPTER " + number if number not in ("I", "A") else
             ("INTRODUCTION" if number == "I" else "APPENDIX A"), 15, "#f2b48f", weight=700, extra='letter-spacing="3"'),
        text(52, h - 34, title, 34, "#ffffff", weight=800),
        text(w - 32, h - 34, crew, 18, "#d7e3ef", "end", SERIF, 400, 'font-style="italic"'),
    ]


def cover():
    """A 960 x 1280 cover: the painting, darkened at the top and foot for the lettering."""
    w, h = 960, 1280

    return [
        '<defs><linearGradient id="shade" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0" stop-color="#03060b" stop-opacity="0.92"/>'
        '<stop offset="0.32" stop-color="#03060b" stop-opacity="0"/>'
        '<stop offset="0.72" stop-color="#03060b" stop-opacity="0"/>'
        '<stop offset="1" stop-color="#03060b" stop-opacity="0.92"/></linearGradient></defs>',
        f'<image href="{picture("cover")}" x="0" y="0" width="{w}" height="{h}" preserveAspectRatio="xMidYMid slice"/>',
        f'<rect x="0" y="0" width="{w}" height="{h}" fill="url(#shade)"/>',
        text(64, 118, "GPU-ACCELERATED", 60, "#ffffff", weight=800, extra='letter-spacing="4"'),
        text(60, 224, "KUBERNETES", 112, "#e8f0f8", weight=900, extra='letter-spacing="2"'),
        f'<rect x="64" y="250" width="240" height="5" fill="{ACCENT}"/>',
        text(64, 300, "Distributed GPU kernel and job scheduling", 30, "#ffd79a", font=SERIF, weight=400,
             extra='font-style="italic"'),
        text(64, 338, "in a cloud native way", 30, "#ffd79a", font=SERIF, weight=400, extra='font-style="italic"'),
        text(w - 64, h - 112, "ARPAN PATHAK", 32, "#ffffff", "end", weight=700, extra='letter-spacing="4"'),
        text(w - 64, h - 66, "Controllers, schedulers and GPU fleets, in Go and in Rust", 22, "#d7e3ef", "end", SERIF,
             400, 'font-style="italic"'),
    ]


def write(name, parts, description, size):
    (OUT / (name + ".svg")).write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size[0]} {size[1]}" width="{size[0]}"'
        f' height="{size[1]}" role="img" aria-label="{escape(description)}">\n' + "\n".join(parts) + "\n</svg>\n")
    print("  " + name)


def main(names):
    OUT.mkdir(parents=True, exist_ok=True)

    for name in names or ["cover", *PLATES]:
        if name == "cover":
            write("cover", cover(), COVER, (960, 1280))
        else:
            number, title, crew, description = PLATES[name]
            write(name, plate(name, number, title, crew), description, (960, 412))

    descriptions = {"cover": COVER, **{name: p[3] for name, p in PLATES.items()}}
    (OUT / "plates.json").write_text(json.dumps(descriptions, indent=2) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
