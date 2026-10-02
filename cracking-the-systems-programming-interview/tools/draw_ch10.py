"""Figures for chapter 10: merging sorted lists."""
from svgkit import *
OUT = "src/figures/"

# merge two lists by hand
f = Figure(760, 300)
f.text(20, 22, "Merging 1 → 4 → 5 with 1 → 3 → 4, one node per step", 12, bold=True)
steps = [([1, 4, 5], [1, 3, 4], []), ([4, 5], [1, 3, 4], [1]), ([4, 5], [3, 4], [1, 1]),
         ([4, 5], [4], [1, 1, 3]), ([5], [4], [1, 1, 3, 4]), ([5], [], [1, 1, 3, 4, 4])]
f.text(90, 44, "left", 10, MUTED); f.text(250, 44, "right", 10, MUTED); f.text(420, 44, "output", 10, MUTED)
for r, (a, b, out) in enumerate(steps):
    y = 52 + r * 38
    f.text(20, y + 18, f"step {r}", 10, MUTED)
    for i, v in enumerate(a):
        f.cell(90 + i * 36, y, 34, 26, str(v), CREAM if i == 0 else PALE, size=11)
    for i, v in enumerate(b):
        f.cell(250 + i * 36, y, 34, 26, str(v), CREAM if i == 0 else PALE, size=11)
    for i, v in enumerate(out):
        f.cell(420 + i * 36, y, 34, 26, str(v), GREEN, size=11)
f.text(20, 292, "Each step compares the two front nodes (cream) and moves the smaller one to the output. When one side is empty, the other is attached whole.", 10)
f.save(OUT + "merge-two.svg")

# strategies
f = Figure(760, 330)
f.text(20, 22, "Three ways to merge k = 4 lists", 12, bold=True)
# one at a time
f.text(20, 50, "1. One at a time: O(kN)", 11, RUST, bold=True)
row, x = [], 20
for i, l in enumerate(["L1", "L1+L2", "L1+L2+L3", "all 4"]):
    box = (x, 60, 100 + i * 12, 28)
    f.cell(*box, l, PINK if i else PALE, size=10)
    row.append(box)
    x += box[2] + 58
for a, b in zip(row, row[1:]):
    f.link(a, b, color=RUST, width=1.4)
f.text(20, 104, "The growing result is walked again at every step.", 10, RUST)
# pairwise
f.text(20, 136, "2. Pairwise rounds: O(N log k)", 11, TEAL, bold=True)
leaves = [(20 + i * 80, 146, 60, 26) for i in range(4)]
for box, l in zip(leaves, ["L1", "L2", "L3", "L4"]):
    f.cell(*box, l, PALE, size=10)
pairs = [(50, 200, 80, 26), (210, 200, 80, 26)]
for box, l in zip(pairs, ["L1+L2", "L3+L4"]):
    f.cell(*box, l, GREEN, size=10)
top = (130, 254, 80, 26)
f.cell(*top, "all 4", GREEN, size=10)
for i, leaf in enumerate(leaves):
    f.link(leaf, pairs[i // 2], color=TEAL, width=1.3, gap=3)
for pair in pairs:
    f.link(pair, top, color=TEAL, width=1.3, gap=3)
f.text(20, 304, "Each node takes part in one merge per round; there are log2 k rounds.", 10, TEAL)
# heap
f.text(420, 136, "3. A heap of the k heads: O(N log k)", 11, BRASS, bold=True)
heap = (580, 146, 90, 128)
f.cell(*heap, "min-heap", CREAM, size=11)
for i, l in enumerate(["head of L1", "head of L2", "head of L3", "head of L4"]):
    y = 146 + i * 34
    f.cell(420, y, 100, 26, l, PALE, size=10)
    f.arrow(524, y + 13, 574, y + 13, BRASS, 1.3)
f.arrow(674, 210, 712, 210, BRASS, 1.4)
f.text(716, 214, "output", 10)
f.text(420, 304, "Pop the smallest head, push that list's next node.", 10, BRASS)
f.save(OUT + "merge-strategies.svg")

# interval rounds on 5 lists
f = Figure(760, 250)
f.text(20, 22, "Interval rounds on five lists: each round merges lists[i] with lists[i + interval]", 12, bold=True)
rows = [("start", ["0", "1", "2", "3", "4"]), ("interval 1", ["0+1", "", "2+3", "", "4"]),
        ("interval 2", ["0+1+2+3", "", "", "", "4"]), ("interval 4", ["all five", "", "", "", ""])]
for r, (label, cells) in enumerate(rows):
    y = 44 + r * 50
    f.text(20, y + 19, label, 11, MUTED)
    for i, c in enumerate(cells):
        fill = GREEN if r == 3 and i == 0 else (CREAM if c and r > 0 and "+" in c else (PALE if c else GREY))
        f.cell(130 + i * 110, y, 100, 28, c if c else "(taken)", fill, size=10, color=INK if c else "#9aa7b4", dash=not c)
f.text(20, 244, "Positions shown as (taken) were emptied by take() when their list moved into a merge.", 10)
f.save(OUT + "merge-interval.svg")

# dummy + tail
f = Figure(760, 190)
f.text(20, 22, "Building the output with a dummy head and a tail pointer", 12, bold=True)
f.cell(20, 60, 90, 30, "dummy", GREY, dash=True, size=11)
f.cell(150, 60, 60, 30, "1", GREEN, size=11); f.cell(250, 60, 60, 30, "1", GREEN, size=11)
f.arrow(110, 75, 148, 75); f.arrow(210, 75, 248, 75)
f.text(196, 120, "tail points here", 10, TEAL)
f.arrow(290, 112, 290, 92, TEAL)
f.cell(420, 40, 60, 28, "4", CREAM, size=11); f.cell(480, 40, 60, 28, "5", PALE, size=11); f.text(560, 58, "left", 10, MUTED)
f.cell(420, 100, 60, 28, "3", CREAM, size=11); f.cell(480, 100, 60, 28, "4", PALE, size=11); f.text(560, 118, "right", 10, MUTED)
f.arrow(312, 75, 418, 112, RUST, 1.4, dash=True); f.text(330, 128, "next: move 3 here", 10, RUST)
f.text(20, 170, "dummy.next is the merged list. The dummy exists so that appending the first node needs no special case.", 10)
f.save(OUT + "merge-tail.svg")
print("ok")
