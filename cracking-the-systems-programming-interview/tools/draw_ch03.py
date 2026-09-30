"""Figures for chapter 3."""
from svgkit import *

OUT = "src/figures/"

# Vec layout
f = Figure(700, 200)
f.text(20, 22, "let mut v: Vec<i32> = Vec::with_capacity(6);  then push 10, 20, 30, 40", 12, mono=True)
f.text(20, 52, "stack", 11, MUTED)
f.cell(20, 60, 90, 34, "ptr"); f.cell(110, 60, 70, 34, "len 4"); f.cell(180, 60, 70, 34, "cap 6")
f.text(20, 112, "24 bytes: three 8-byte numbers", 10, MUTED)
f.text(330, 52, "heap: one block for 6 i32 values (4 bytes each)", 11, MUTED)
for i, v in enumerate(["10", "20", "30", "40", "", ""]):
    f.cell(330 + i * 56, 60, 56, 34, v, GREEN if v else GREY, dash=not v)
    f.text(330 + i * 56 + 28, 112, f"[{i}]", 10, MUTED, anchor="middle")
f.arrow(65, 94, 330, 88, TEAL)
f.text(330, 140, "v[2] is at address ptr + 2 × 4 bytes, so reading it is one step,", 11)
f.text(330, 156, "however long the vector is. Indexes 4 and 5 are reserved, not in use.", 11)
f.save(OUT + "ch03-vec-layout.svg")

# Vec growth
f = Figure(700, 170)
f.text(20, 22, "v.push(50) when len == cap == 4", 12, mono=True)
f.text(20, 50, "old block (cap 4)", 11, MUTED)
for i, v in enumerate(["10", "20", "30", "40"]):
    f.cell(20 + i * 50, 58, 50, 32, v, GREY)
f.text(330, 50, "new block (cap 8)", 11, MUTED)
for i, v in enumerate(["10", "20", "30", "40", "50", "", "", ""]):
    f.cell(330 + i * 44, 58, 44, 32, v, GREEN if v else GREY, dash=not v, size=11)
f.arrow(222, 74, 326, 74, TEAL)
f.text(234, 68, "1. copy", 10, TEAL)
f.text(20, 118, "1. Allocate a block twice as large.  2. Copy the old elements.  3. Write 50.  4. Free the old block.", 11)
f.text(20, 138, "Most pushes find room and cost one write. A push that grows copies everything, but growth", 11)
f.text(20, 154, "doubles the capacity, so it happens rarely. On average a push costs a constant amount.", 11)
f.save(OUT + "ch03-vec-grow.svg")

# UTF-8
f = Figure(560, 170)
f.text(20, 22, "The String \"café\" in memory", 12, mono=True)
chars = [("c", ["63"]), ("a", ["61"]), ("f", ["66"]), ("é", ["C3", "A9"])]
x = 20
for ch, bs in chars:
    w = 60 * len(bs)
    f.cell(x, 40, w, 30, ch, CREAM)
    for j, b in enumerate(bs):
        f.cell(x + j * 60, 76, 60, 30, "0x" + b, PALE, size=11)
    x += w
f.text(20, 128, "4 characters (chars().count() == 4), stored in 5 bytes (len() == 5).", 11)
f.text(20, 146, "é needs two bytes, so byte index 4 is in the middle of a character.", 11)
f.save(OUT + "ch03-utf8.svg")

# HashMap buckets
f = Figure(720, 230)
f.text(20, 22, "A hash map with 8 buckets holding three keys", 12, bold=True)
keys = [("7", 3), ("2", 6), ("11", 3)]
for i, (k, b) in enumerate(keys):
    y = 50 + i * 50
    f.cell(20, y, 60, 30, f"key {k}", CREAM, size=11)
    f.cell(130, y, 110, 30, "hash(key)", PALE, size=11)
    f.arrow(80, y + 15, 130, y + 15)
    f.text(250, y + 20, f"= ...{'10110011' if k=='7' else '01000110' if k=='2' else '00101011'} → bucket {b}", 10, MUTED, mono=True)
for i in range(8):
    y = 40 + i * 22
    f.cell(480, y, 40, 22, str(i), GREY, size=10)
    if i == 3:
        f.cell(530, y, 70, 22, "7 → 0", GREEN, size=10); f.cell(606, y, 70, 22, "11 → 2", GREEN, size=10)
    if i == 6:
        f.cell(530, y, 70, 22, "2 → 1", GREEN, size=10)
f.text(20, 216, "To find a key, hash it, go to its bucket, and compare only the few keys stored there.", 11)
f.save(OUT + "ch03-hashmap.svg")

# Stack trace for "{[()]}"
f = Figure(720, 190)
f.text(20, 22, "Checking \"{[()]}\" with a stack", 12, bold=True)
steps = [("{", ["{"]), ("[", ["{", "["]), ("(", ["{", "[", "("]), (")", ["{", "["]), ("]", ["{"]), ("}", [])]
for i, (ch, st) in enumerate(steps):
    x = 20 + i * 116
    f.text(x + 40, 46, f"read {ch}", 11, anchor="middle", mono=True)
    f.text(x + 40, 62, "push" if ch in "{[(" else f"pop, matches", 10, TEAL if ch not in "{[(" else MUTED, anchor="middle")
    for j, s in enumerate(st):
        f.cell(x + 15, 150 - (j + 1) * 24, 50, 24, s, GREEN if j == len(st) - 1 else PALE, size=11)
    f.line(x + 10, 151, x + 70, 151)
    if not st:
        f.text(x + 40, 140, "empty", 10, MUTED, anchor="middle")
f.text(20, 178, "The top of the stack is always the most recent unclosed opener, the one the next closer must match.", 11)
f.save(OUT + "ch03-stack.svg")

# Two pointers reversing
f = Figure(560, 170)
f.text(20, 22, "Reversing \"abcd\" with two pointers", 12, bold=True)
rows = [("start", "abcd", 0, 3), ("after swap 1", "dbca", 1, 2), ("after swap 2", "dcba", 2, 1)]
for r, (label, s, a, b) in enumerate(rows):
    y = 40 + r * 42
    f.text(20, y + 21, label, 11, MUTED)
    for i, c in enumerate(s):
        fill = GREEN if (i in (a, b) and a < b) else PALE
        f.cell(130 + i * 44, y, 44, 30, c, fill)
    if a < b:
        f.text(130 + a * 44 + 22, y - 3, "start", 9, TEAL, anchor="middle")
        f.text(130 + b * 44 + 22, y - 3, "end", 9, TEAL, anchor="middle")
    else:
        f.text(330, y + 21, "start > end: stop", 10, MUTED)
f.save(OUT + "ch03-two-pointers.svg")

# intervals
f = Figure(640, 170)
f.text(20, 22, "Merging [1,3] [2,6] [8,10] [15,18] after sorting by start", 12, bold=True)
def iv(y, a, b, fill, label):
    f.rect(40 + a * 30, y, (b - a) * 30, 20, fill, INK, 3)
    f.text(40 + a * 30 + 4, y + 14, label, 10, mono=True)
for a, b, row in [(1, 3, 0), (2, 6, 1), (8, 10, 0), (15, 18, 0)]:
    iv(40 + row * 26, a, b, PALE, f"{a}-{b}")
f.text(20, 112, "merged", 10, MUTED)
for a, b in [(1, 6), (8, 10), (15, 18)]:
    iv(118, a, b, GREEN, f"{a}-{b}")
for t in range(0, 19, 3):
    f.text(40 + t * 30, 160, str(t), 9, MUTED, anchor="middle")
f.save(OUT + "ch03-intervals.svg")

# binary search on a sorted array
f = Figure(640, 190)
f.text(20, 22, "Binary search for 23 in a sorted array of 8 values", 12, bold=True)
arr = [2, 5, 8, 12, 16, 23, 38, 56]
rows = [(0, 8, 4), (5, 8, 6), (5, 6, 5)]
for r, (lo, hi, mid) in enumerate(rows):
    y = 40 + r * 46
    for i, v in enumerate(arr):
        inr = lo <= i < hi
        fill = CREAM if i == mid else (PALE if inr else GREY)
        f.cell(120 + i * 56, y, 56, 30, str(v), fill, color=INK if inr else "#9aa7b4")
    f.text(20, y + 20, f"low {lo}, high {hi}", 10, MUTED, mono=True)
f.text(20, 182, "Each step compares the middle value (cream) with 23 and discards the half that cannot contain it.", 11)
f.save(OUT + "ch03-binary-search.svg")

# rotate matrix
f = Figure(640, 150)
def grid(x, y, m, title):
    f.text(x, y - 8, title, 11, MUTED)
    for r in range(3):
        for c in range(3):
            f.cell(x + c * 34, y + r * 30, 34, 30, str(m[r][c]), PALE, size=11)
grid(20, 30, [[1,2,3],[4,5,6],[7,8,9]], "original")
grid(230, 30, [[1,4,7],[2,5,8],[3,6,9]], "after transpose")
grid(440, 30, [[7,4,1],[8,5,2],[9,6,3]], "after reversing rows")
f.arrow(130, 75, 225, 75, TEAL); f.arrow(340, 75, 435, 75, TEAL)
f.text(20, 140, "Transpose swaps m[i][j] with m[j][i]. Reversing each row then gives a clockwise quarter turn.", 11)
f.save(OUT + "ch03-rotate.svg")

# KMP shift
f = Figure(700, 200)
f.text(20, 22, "Searching for \"aabaaac\" in \"aabaaabaaac\"", 12, bold=True)
hay = "aabaaabaaac"
for i, c in enumerate(hay):
    f.cell(120 + i * 40, 40, 40, 28, c, PALE, size=11)
    f.text(120 + i * 40 + 20, 84, str(i), 9, MUTED, anchor="middle")
f.text(20, 58, "haystack", 10, MUTED)
needle = "aabaaac"
for i, c in enumerate(needle):
    fill = GREEN if i < 6 else PINK
    f.cell(120 + i * 40, 96, 40, 28, c, fill, size=11)
f.text(20, 114, "try at 0", 10, MUTED)
for i, c in enumerate(needle):
    f.cell(120 + (4 + i) * 40, 138, 40, 28, c, GREEN, size=11)
f.text(20, 156, "resume at 4", 10, MUTED)
f.text(20, 190, "Six characters matched, then 'c' ≠ 'b'. lps[5] = 2 says the last two matched characters, \"aa\", are also the needle's start.", 10)
f.save(OUT + "ch03-kmp.svg")
print("ok")
