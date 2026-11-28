"""Figures for chapter 32: sweep-line algorithms."""
from svgkit import *
OUT = "src/figures/"

# 1. the skyline of 5 buildings
f = Figure(760, 330)
f.text(20, 22, "The skyline of 5 buildings: a key point wherever the tallest active height changes", 12, bold=True)
x0, base, unit_x, unit_y = 50, 280, 26, 13
buildings = [(2, 9, 10), (3, 7, 15), (5, 12, 12), (15, 20, 10), (19, 24, 8)]
for left, right, height in buildings:
    f.rect(x0 + left * unit_x, base - height * unit_y, (right - left) * unit_x, height * unit_y,
           PALE, BORDER, 0, width=1.0, opacity=0.85)
f.line(x0 - 10, base, x0 + 26 * unit_x, base, MUTED)
for x in range(0, 26, 2):
    f.line(x0 + x * unit_x, base, x0 + x * unit_x, base + 4, MUTED)
    f.text(x0 + x * unit_x, base + 17, str(x), 9, MUTED, anchor="middle")
outline = [(2, 0), (2, 10), (3, 10), (3, 15), (7, 15), (7, 12), (12, 12), (12, 0), (15, 0),
           (15, 10), (20, 10), (20, 8), (24, 8), (24, 0)]
for (xa, ya), (xb, yb) in zip(outline, outline[1:]):
    f.line(x0 + xa * unit_x, base - ya * unit_y, x0 + xb * unit_x, base - yb * unit_y, TEAL, 3)
points = [(2, 10, "end"), (3, 15, "middle"), (7, 12, "start"), (12, 0, "start"),
          (15, 10, "middle"), (20, 8, "start"), (24, 0, "start")]
for x, y, anchor in points:
    px, py = x0 + x * unit_x, base - y * unit_y
    f.circle(px, py, 4.5, RUST, RUST)
    dx = {"end": -7, "start": 7, "middle": 0}[anchor]
    f.text(px + dx, py - 9, f"[{x}, {y}]", 10, RUST, mono=True, anchor=anchor, bold=True)
f.text(x0, base + 38, "Buildings [left, right, height]: [2, 9, 10], [3, 7, 15], [5, 12, 12], [15, 20, 10], [19, 24, 8]", 10, MUTED, mono=True)
f.save(OUT + "ch32-skyline.svg")
print("ok")
