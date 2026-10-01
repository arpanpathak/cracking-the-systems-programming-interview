#!/usr/bin/env python3
"""Point every motion animation in the chapters at its video.

`motion.render` writes three files per animation: the GIF, an MP4 of the same
frames, and a JSON file with the loop's steps. In the HTML book the MP4 is used,
because a reader can pause it, slow it down, and jump between steps
(theme/anim.js adds those controls); the GIF stays inside the <video> tag as the
fallback. This rewrites the <img> of each such animation into that <video>, and
refreshes the step list when an animation is rendered again.

    python3 tools/anim_markup.py
"""

import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIGURES = ROOT / "src" / "figures"

IMG = re.compile(r'<img src="figures/(?P<stem>[a-z0-9-]+)\.gif" alt="(?P<alt>[^"]*)">')
VIDEO = re.compile(r'<video class="motion" src="figures/(?P<stem>[a-z0-9-]+)\.mp4"[^>]*>'
                   r'<img src="figures/(?P=stem)\.gif" alt="(?P<alt>[^"]*)"></video>')


def markup(stem, alt):
    steps = json.loads((FIGURES / (stem + ".json")).read_text())["chapters"]
    return ('<video class="motion" src="figures/%s.mp4" autoplay loop muted playsinline '
            'preload="metadata" aria-label="%s" data-chapters="%s">'
            '<img src="figures/%s.gif" alt="%s"></video>'
            % (stem, alt, html.escape(json.dumps(steps), quote=True), stem, alt))


def main():
    changed = 0
    for page in sorted((ROOT / "src").glob("*.md")):
        text = page.read_text()

        def swap(m):
            stem = m.group("stem")
            if not (FIGURES / (stem + ".mp4")).exists() or not (FIGURES / (stem + ".json")).exists():
                return m.group(0)
            return markup(stem, m.group("alt"))

        new = VIDEO.sub(swap, IMG.sub(swap, text))
        if new != text:
            page.write_text(new)
            changed += 1
    print("updated %d chapter(s)" % changed)


if __name__ == "__main__":
    main()
