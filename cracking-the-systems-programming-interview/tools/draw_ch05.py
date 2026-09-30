"""Figures for chapter 5: heaps."""
from svgkit import *
OUT = "src/figures/"

def tree(f, x0, y0, vals, hi=None, w=300):
    pos = {}
    for i, v in enumerate(vals):
        level = (i + 1).bit_length() - 1
        first = 2 ** level - 1
        k = i - first
        slots = 2 ** level
        x = x0 + (k + 0.5) * w / slots
        y = y0 + level * 50
        pos[i] = (x, y)
    for i in pos:
        if i > 0:
            px, py = pos[(i - 1) // 2]; x, y = pos[i]
            f.line(px, py + 14, x, y - 14)
    for i, v in enumerate(vals):
        x, y = pos[i]
        fill = CREAM if hi and i in hi else PALE
        f.rect(x - 16, y - 14, 32, 28, fill, INK, 14)
        f.text(x, y + 5, str(v), 12, mono=True, anchor="middle")
    return pos

# heap as tree and array
f = Figure(720, 230)
f.text(20, 22, "A max-heap: every parent is at least as large as its children", 12, bold=True)
vals = [9, 7, 8, 3, 5, 6]
tree(f, 20, 55, vals, hi={0})
f.text(360, 60, "stored in a Vec, level by level:", 11, MUTED)
for i, v in enumerate(vals):
    f.cell(360 + i * 52, 70, 52, 30, str(v), CREAM if i == 0 else PALE, size=12)
    f.text(360 + i * 52 + 26, 116, f"[{i}]", 10, MUTED, anchor="middle")
f.text(360, 146, "children of index i:  2i + 1  and  2i + 2", 11, mono=True)
f.text(360, 164, "parent of index i:    (i - 1) / 2", 11, mono=True)
f.text(360, 190, "No pointers are stored; the positions come", 11)
f.text(360, 206, "from arithmetic on the index.", 11)
f.save(OUT + "heap-layout.svg")

# push with sift up
f = Figure(760, 210)
f.text(20, 22, "push(10): add at the end, then swap upward while larger than the parent", 12, bold=True)
tree(f, 10, 60, [9, 7, 8, 3, 5, 6, 10], hi={6}, w=230)
f.text(40, 200, "1. appended at [6]", 11, MUTED)
tree(f, 260, 60, [9, 7, 10, 3, 5, 6, 8], hi={2}, w=230)
f.text(290, 200, "2. 10 > 8: swap with parent", 11, MUTED)
tree(f, 510, 60, [10, 7, 9, 3, 5, 6, 8], hi={0}, w=230)
f.text(540, 200, "3. 10 > 9: swap; now at the top", 11, MUTED)
f.save(OUT + "heap-push.svg")

# pop with sift down
f = Figure(760, 210)
f.text(20, 22, "pop(): take the top, move the last element to the top, swap downward with the larger child", 12, bold=True)
tree(f, 10, 60, [6, 7, 9, 3, 5, 8], hi={0}, w=230)
f.text(20, 200, "1. 10 removed; last element 6 moved up", 11, MUTED)
tree(f, 260, 60, [9, 7, 6, 3, 5, 8], hi={2}, w=230)
f.text(270, 200, "2. larger child is 9: swap", 11, MUTED)
tree(f, 510, 60, [9, 7, 8, 3, 5, 6], hi={5}, w=230)
f.text(520, 200, "3. larger child is 8: swap; done", 11, MUTED)
f.save(OUT + "heap-pop.svg")

# bounded min heap of size k
f = Figure(900, 262)
f.text(20, 22, "Keeping the 3 most frequent words with a min-heap of size 3", 12, bold=True)
steps = [("push (this, 2)", ["(2,this)"], ""),
         ("push (count, 2)", ["(2,count)", "(2,this)"], ""),
         ("push (sentence, 2)", ["(2,count)", "(2,sentence)", "(2,this)"], ""),
         ("push (words, 2), size 4", ["(2,count)", "(2,sentence)", "(2,this)", "(2,words)"], "pop removes the smallest: (2,count)"),
         ("push (a, 1), size 4", ["(1,a)", "(2,sentence)", "(2,this)", "(2,words)"], "pop removes (1,a)")]
for r, (label, heap, note) in enumerate(steps):
    y = 40 + r * 36
    f.text(20, y + 19, label, 11, mono=True)
    for i, v in enumerate(heap):
        f.cell(230 + i * 100, y, 96, 26, v, CREAM if i == 0 else PALE, size=10)
    if note:
        f.text(230 + len(heap) * 100 + 6, y + 18, note, 10, RUST)
f.text(20, 232, "Contents listed smallest first. The smallest entry (cream) is at the top of the heap, so pop removes it.", 11)
f.text(20, 248, "The heap never holds more than k + 1 entries. Words arrive in whatever order the HashMap yields them.", 11)
f.save(OUT + "heap-topk.svg")
print("ok")
