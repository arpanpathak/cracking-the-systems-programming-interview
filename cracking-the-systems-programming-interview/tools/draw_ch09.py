"""Figures for chapter 9: linked lists."""
from svgkit import *
OUT = "src/figures/"

f = Figure(740, 250)
f.text(20, 22, "The values 1, 2, 3 in a Vec and in a linked list", 12, bold=True)
f.text(20, 50, "Vec: one block, elements side by side", 11, MUTED)
for i, v in enumerate(["1", "2", "3"]):
    f.cell(20 + i * 50, 60, 50, 30, v, GREEN, size=12)
f.text(20, 110, "linked list: one heap block per node, anywhere in memory", 11, MUTED)
f.cell(20, 130, 70, 30, "head", CREAM, size=11)
nodes = [(170, 190, "1"), (360, 125, "2"), (560, 195, "3")]
f.arrow(90, 145, 168, 200, TEAL)
for i, (x, y, v) in enumerate(nodes):
    f.cell(x, y, 50, 30, v, PALE, size=12)
    f.cell(x + 50, y, 70, 30, "next" if i < 2 else "None", PALE, size=10)
    if i < 2:
        nx, ny, _ = nodes[i + 1]
        f.arrow(x + 110, y + 15, nx - 2, ny + 15, TEAL)
f.text(20, 244, "Reaching the third value means following two pointers, one at a time; there is no index arithmetic.", 11)
f.save(OUT + "list-vs-vec.svg")

f = Figure(700, 170)
f.text(20, 22, "Option::take moves the value out and leaves None behind", 12, bold=True)
f.text(20, 52, "before:  let rest = node.next.take();", 11, mono=True)
f.cell(20, 62, 70, 30, "node", CREAM, size=11); f.cell(90, 62, 110, 30, "next: Some", PALE, size=10)
f.cell(260, 62, 110, 30, "rest of list", GREEN, size=10); f.arrow(200, 77, 258, 77, TEAL)
f.text(20, 122, "after:", 11, mono=True)
f.cell(20, 132, 70, 30, "node", CREAM, size=11); f.cell(90, 132, 110, 30, "next: None", GREY, size=10)
f.cell(260, 132, 110, 30, "rest of list", GREEN, size=10); f.cell(390, 132, 70, 30, "rest", PALE, size=11)
f.arrow(390, 147, 372, 147, TEAL)
f.text(480, 100, "The node stays valid (it holds None),", 11)
f.text(480, 118, "and the variable rest now owns the", 11)
f.text(480, 136, "rest of the list.", 11)
f.save(OUT + "list-take.svg")
print("ok")

# recursive vs iterative drop
f = Figure(740, 300)
f.text(20, 22, "Dropping a list of 270,000 boxed nodes", 12, bold=True)
f.text(20, 46, "Default drop: each node frees the next one first", 11, RUST)
frames = ["drop(list)", "drop(node 1) must first drop node 2", "drop(node 2) must first drop node 3", "...", "drop(node 265,000): the stack is full"]
for i, fr in enumerate(frames):
    y = 236 - i * 42
    fill = PINK if i == len(frames) - 1 else PALE
    if fr == "...":
        f.text(160, y + 20, "... one stack frame per node ...", 11, MUTED, anchor="middle")
    else:
        f.cell(20, y, 280, 32, fr, fill, size=10)
f.text(20, 290, "The frames pile up until the thread's stack runs out.", 10, RUST)
f.text(400, 46, "Iterative Drop: detach, then free", 11, TEAL)
steps = ["current = head.take()", "node = current;  current = node.next.take()", "node is freed; its next is already None", "repeat until current is None"]
for i, st in enumerate(steps):
    y = 60 + i * 50
    f.cell(400, y, 320, 32, st, GREEN if i == 2 else PALE, size=10)
    if i < 3:
        f.arrow(560, y + 32, 560, y + 48, TEAL)
f.line(720, 186, 734, 186, TEAL); f.line(734, 186, 734, 126, TEAL); f.arrow(734, 126, 722, 126, TEAL)
f.text(400, 290, "One loop in one frame, however long the list is.", 10, TEAL)
f.save(OUT + "list-drop.svg")

# doubly linked list
f = Figure(760, 230)
f.text(20, 22, "A doubly linked list after push_front(10), push_front(20), push_back(30), push_back(40)", 12, bold=True)
xs = [120, 280, 440, 600]
for i, v in enumerate(["20", "10", "30", "40"]):
    x = xs[i]
    f.cell(x, 100, 40, 30, "prev", PALE, size=9); f.cell(x + 40, 100, 40, 30, v, GREEN, size=12); f.cell(x + 80, 100, 40, 30, "next", PALE, size=9)
    if i < 3:
        f.arrow(x + 120, 110, xs[i + 1] - 2, 110, INK, 1.8)
        f.line(xs[i + 1] + 20, 130, xs[i + 1] + 20, 150, TEAL, 1.4, True)
        f.line(xs[i + 1] + 20, 150, x + 60, 150, TEAL, 1.4, True)
        f.arrow(x + 60, 150, x + 60, 132, TEAL, 1.4, dash=True)
f.cell(20, 40, 90, 28, "head", CREAM, size=11); f.cell(640, 40, 90, 28, "tail", CREAM, size=11)
f.arrow(65, 68, 138, 98, INK, 1.8); f.arrow(685, 68, 660, 98, INK, 1.8)
f.line(40, 186, 80, 186, INK, 1.8); f.text(90, 190, "Rc: a strong link that owns the node it points to", 11)
f.line(40, 210, 80, 210, TEAL, 1.4, True); f.text(90, 214, "Weak: a back-link that does not keep the node alive", 11)
f.save(OUT + "list-doubly.svg")
print("ok2")
