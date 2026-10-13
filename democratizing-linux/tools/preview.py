#!/usr/bin/env python3
"""Render chosen moments of motion animations into one contact sheet.

    python3 tools/preview.py OUT.png two-sum:12 window:40 kmp-lps:60

Each argument is an animation name from `animations.MOTION` and a time in
seconds. The frames are scaled down and laid out two to a row, so a layout
problem in any of them shows up in one image.
"""

import sys

from PIL import Image

import animations


def main(argv):
    out, picks = argv[0], argv[1:]
    frames = []
    for pick in picks:
        name, when = pick.rsplit(":", 1)
        for path in animations.MOTION[name](only=[float(when)]):
            frames.append(Image.open(path).convert("RGB"))
    frames = [f.resize((f.width * 45 // 100, f.height * 45 // 100)) for f in frames]
    width = max(f.width for f in frames)
    height = max(f.height for f in frames)
    rows = (len(frames) + 1) // 2
    sheet = Image.new("RGB", (width * 2, height * rows), "white")
    for k, f in enumerate(frames):
        sheet.paste(f, ((k % 2) * width, (k // 2) * height))
    sheet.save(out)
    print(out)


if __name__ == "__main__":
    main(sys.argv[1:])
