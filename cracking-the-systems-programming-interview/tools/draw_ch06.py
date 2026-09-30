"""Figures for chapter 6: dynamic programming."""
from svgkit import *
OUT = "src/figures/"

# greedy fails
f = Figure(640, 150)
f.text(20, 22, "Coins 1, 3, 4. Make 6 with as few coins as possible.", 12, bold=True)
f.text(20, 52, "Greedy (always take the largest coin that fits):", 11)
for i, c in enumerate([4, 1, 1]):
    f.rect(320 + i * 46, 36, 38, 26, PINK, RUST, 13); f.text(339 + i * 46, 54, str(c), 12, mono=True, anchor="middle")
f.text(470, 54, "3 coins", 11, RUST)
f.text(20, 96, "Best:", 11)
for i, c in enumerate([3, 3]):
    f.rect(320 + i * 46, 80, 38, 26, GREEN, TEAL, 13); f.text(339 + i * 46, 98, str(c), 12, mono=True, anchor="middle")
f.text(470, 98, "2 coins", 11, TEAL)
f.text(20, 136, "Taking the largest coin first can lead to a worse answer, so the program must consider every coin.", 11)
f.save(OUT + "dp-greedy.svg")

# coin change table
f = Figure(760, 240)
f.text(20, 22, "Filling dp for coins [1, 2, 5]: dp[t] = fewest coins that make t", 12, bold=True)
dp = [0, 1, 1, 2, 2, 1, 2, 2, 3, 3, 2, 3]
for t, v in enumerate(dp):
    fill = CREAM if t == 11 else (GREEN if t in (10, 9, 6) else PALE)
    f.cell(20 + t * 60, 60, 60, 34, str(v), fill, size=13)
    f.text(20 + t * 60 + 30, 112, f"t={t}", 10, MUTED, anchor="middle")
f.text(20, 50, "dp", 11, MUTED, mono=True)
f.text(20, 140, "To fill dp[11], try each coin c and look back at dp[11 - c] (green cells):", 11)
for i, (t, coin) in enumerate([(10, 1), (9, 2), (6, 5)]):
    f.cell(20 + i * 230, 152, 215, 30, f"coin {coin}: dp[{t}] + 1 = {dp[t] + 1}", GREEN, TEAL, size=11)
f.text(20, 206, "The smallest option is 3, so dp[11] = 3 (cream).", 11)
f.text(20, 232, "Every cell depends only on cells to its left, so filling the table from left to right works.", 11)
f.save(OUT + "dp-coins.svg")

# LIS tails
f = Figure(760, 330)
f.text(20, 22, "tails while reading [10, 9, 2, 5, 3, 7, 101, 18]", 12, bold=True)
steps = [(10, [10], "new length 1"), (9, [9], "9 replaces 10"), (2, [2], "2 replaces 9"), (5, [2, 5], "5 extends"),
         (3, [2, 3], "3 replaces 5"), (7, [2, 3, 7], "7 extends"), (101, [2, 3, 7, 101], "101 extends"), (18, [2, 3, 7, 18], "18 replaces 101")]
for r, (n, tails, note) in enumerate(steps):
    y = 40 + r * 34
    f.text(20, y + 18, f"read {n}", 11, mono=True)
    for i, v in enumerate(tails):
        changed = (i == len(tails) - 1 and "extends" in note) or ("replaces" in note and v == n)
        f.cell(120 + i * 60, y, 60, 26, str(v), GREEN if changed else PALE, size=11)
    f.text(380, y + 18, note, 11, MUTED)
f.text(20, 318, "tails[k] is the smallest value that can end an increasing run of length k + 1. Its length, 4, is the answer.", 11)
f.save(OUT + "dp-lis.svg")

# jobs timeline
f = Figure(700, 220)
f.text(20, 22, "Four jobs on a timeline; A and D do not overlap and earn 50 + 70 = 120", 12, bold=True)
def x(t): return 120 + (t - 1) * 100
for t in range(1, 7):
    f.line(x(t), 36, x(t), 180, "#d9e1e8", 1)
    f.text(x(t), 196, str(t), 10, MUTED, anchor="middle")
jobs = [("A", 1, 3, 50, True), ("B", 2, 4, 10, False), ("C", 3, 5, 40, False), ("D", 3, 6, 70, True)]
for r, (name, s, e, p, pick) in enumerate(jobs):
    y = 44 + r * 34
    f.text(20, y + 17, f"job {name}", 11, mono=True)
    f.rect(x(s), y, x(e) - x(s), 24, GREEN if pick else PALE, TEAL if pick else INK, 4)
    f.text(x(s) + 8, y + 16, f"[{s}, {e})  profit {p}", 10, mono=True)
f.text(20, 214, "A job [s, e) runs from time s up to, but not including, time e. A ends at 3 and D starts at 3, so both fit.", 11)
f.save(OUT + "dp-jobs.svg")

# subsets tree
f = Figure(700, 260)
f.text(20, 22, "Every subset of [1, 2, 3] as a tree of choices", 12, bold=True)
nodes = {"[]": (350, 50), "[1]": (170, 120), "[2]": (350, 120), "[3]": (530, 120),
         "[1,2]": (90, 190), "[1,3]": (250, 190), "[2,3]": (350, 190), "[1,2,3]": (90, 245)}
edges = [("[]", "[1]", "push 1"), ("[]", "[2]", "push 2"), ("[]", "[3]", "push 3"), ("[1]", "[1,2]", "push 2"),
         ("[1]", "[1,3]", "push 3"), ("[2]", "[2,3]", "push 3"), ("[1,2]", "[1,2,3]", "push 3")]
for a, b, label in edges:
    (x1, y1), (x2, y2) = nodes[a], nodes[b]
    f.arrow(x1, y1 + 13, x2, y2 - 13, INK, 1.3)
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    f.text(mx + (8 if x2 >= x1 else -8), my, label, 10, TEAL, anchor="start" if x2 >= x1 else "end")
for n, (x, y) in nodes.items():
    w = 16 + 9 * len(n)
    f.cell(x - w / 2, y - 13, w, 26, n, CREAM if n == "[]" else PALE, size=11)
f.text(400, 240, "Each node is recorded as one subset.", 11, MUTED)
f.save(OUT + "dp-subsets.svg")
print("ok")
