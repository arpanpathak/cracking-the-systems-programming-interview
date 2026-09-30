"""Figures for chapter 11: trees and tries."""
from svgkit import *
OUT = "src/figures/"

def node(f, x, y, label, fill=PALE, r=16, badge=None):
    f.rect(x - r, y - 14, 2 * r, 28, fill, INK, 14)
    f.text(x, y + 5, str(label), 12, mono=True, anchor="middle")
    if badge is not None:
        f.rect(x + r - 4, y - 24, 18, 16, CREAM, BRASS, 8); f.text(x + r + 5, y - 12, str(badge), 9, anchor="middle")

def edge(f, a, b, color=INK, dash=False):
    f.line(a[0], a[1] + 14, b[0], b[1] - 14, color, 1.4, dash)

# terms
f = Figure(740, 250)
f.text(20, 22, "Tree terms, on the tree used by the tests", 12, bold=True)
P = {3: (200, 60), 9: (110, 130), 20: (290, 130), 15: (240, 200), 7: (340, 200)}
for a, b in [(3, 9), (3, 20), (20, 15), (20, 7)]:
    edge(f, P[a], P[b])
for k, (x, y) in P.items():
    node(f, x, y, k, CREAM if k == 3 else (GREEN if k in (9, 15, 7) else PALE))
f.rect(222, 102, 150, 126, "none", TEAL, 8, True)
notes = [("root: the node with no parent (3)", CREAM), ("leaf: a node with no children (9, 15, 7)", GREEN),
         ("children of 20: 15 (left) and 7 (right)", PALE), ("subtree of 20: 20 and everything below it (dashed box)", "#ffffff"),
         ("depth: the number of levels; this tree has depth 3", "#ffffff")]
for i, (t, fill) in enumerate(notes):
    f.rect(420, 50 + i * 36, 14, 14, fill, INK, 3); f.text(442, 62 + i * 36, t, 11)
f.save(OUT + "tree-terms.svg")

# three orders
f = Figure(760, 222)
f.text(20, 22, "The order each traversal visits the same tree (badges show the visit order)", 12, bold=True)
orders = [("pre-order: node, left, right", {3: 1, 9: 2, 20: 3, 15: 4, 7: 5}),
          ("in-order: left, node, right", {9: 1, 3: 2, 15: 3, 20: 4, 7: 5}),
          ("post-order: left, right, node", {9: 1, 15: 2, 7: 3, 20: 4, 3: 5})]
for c, (title, order) in enumerate(orders):
    ox = c * 250
    Q = {3: (ox + 110, 82), 9: (ox + 60, 140), 20: (ox + 160, 140), 15: (ox + 125, 195), 7: (ox + 195, 195)}
    f.text(ox + 20, 46, title, 11, MUTED)
    for a, b in [(3, 9), (3, 20), (20, 15), (20, 7)]:
        edge(f, Q[a], Q[b])
    for k, (x, y) in Q.items():
        node(f, x, y, k, badge=order[k])
f.save(OUT + "tree-orders.svg")

# BST search
f = Figure(740, 230)
f.text(20, 22, "A binary search tree: searching for 7", 12, bold=True)
B = {10: (200, 60), 5: (120, 125), 15: (280, 125), 3: (80, 190), 7: (160, 190), 12: (240, 190), 18: (320, 190)}
for a, b in [(10, 5), (10, 15), (5, 3), (5, 7), (15, 12), (15, 18)]:
    edge(f, B[a], B[b], TEAL if (a, b) in [(10, 5), (5, 7)] else INK)
for k, (x, y) in B.items():
    node(f, x, y, k, GREEN if k in (10, 5, 7) else PALE)
steps = ["7 < 10: go left", "7 > 5: go right", "7 == 7: found, after 3 comparisons"]
for i, st in enumerate(steps):
    f.text(420, 80 + i * 26, f"{i + 1}. {st}", 11, TEAL)
f.text(420, 170, "Left subtree: values smaller than the node.", 11)
f.text(420, 188, "Right subtree: values larger than the node.", 11)
f.save(OUT + "bst-search.svg")

# BST removal cases
f = Figure(760, 240)
f.text(20, 22, "The three cases of removing a value", 12, bold=True)
# case 1
f.text(20, 50, "1. no left child: replace", 11, MUTED); f.text(20, 64, "the node by its right subtree", 11, MUTED)
node(f, 90, 100, 5, PINK); node(f, 130, 160, 7); edge(f, (90, 100), (130, 160)); f.text(40, 170, "Empty", 9, MUTED, mono=True)
f.arrow(160, 130, 190, 130, TEAL); node(f, 220, 130, 7, GREEN)
# case 2
f.text(270, 50, "2. no right child: replace", 11, MUTED); f.text(270, 64, "the node by its left subtree", 11, MUTED)
node(f, 340, 100, 5, PINK); node(f, 300, 160, 3); edge(f, (340, 100), (300, 160)); f.text(360, 170, "Empty", 9, MUTED, mono=True)
f.arrow(400, 130, 430, 130, TEAL); node(f, 460, 130, 3, GREEN)
# case 3
f.text(520, 50, "3. two children: copy in the", 11, MUTED); f.text(520, 64, "smallest value on the right", 11, MUTED)
T = {10: (620, 100), 5: (560, 155), 15: (680, 155), 12: (650, 210), 18: (715, 210)}
for a, b in [(10, 5), (10, 15), (15, 12), (15, 18)]:
    edge(f, T[a], T[b])
for k, (x, y) in T.items():
    node(f, x, y, "10→12" if k == 10 else k, PINK if k == 10 else (GREEN if k == 12 else PALE), r=24 if k == 10 else 16)
f.text(520, 234, "then remove 12 from the right subtree (case 1)", 10, TEAL)
f.save(OUT + "bst-remove.svg")

# n-ary DFS vs BFS
f = Figure(760, 228)
f.text(20, 22, "One tree, two visiting orders", 12, bold=True)
for c, (title, order) in enumerate([("depth first (dfs): 1, 2, 4, 5, 3, 6", {1: 1, 2: 2, 4: 3, 5: 4, 3: 5, 6: 6}),
                                    ("breadth first (bfs): 1, 2, 3, 4, 5, 6", {1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6})]):
    ox = c * 380
    N = {1: (ox + 170, 82), 2: (ox + 100, 140), 3: (ox + 240, 140), 4: (ox + 60, 198), 5: (ox + 140, 198), 6: (ox + 240, 198)}
    f.text(ox + 20, 46, title, 11, MUTED)
    for a, b in [(1, 2), (1, 3), (2, 4), (2, 5), (3, 6)]:
        edge(f, N[a], N[b])
    for k, (x, y) in N.items():
        node(f, x, y, k, badge=order[k])
f.save(OUT + "tree-dfs-bfs.svg")

# serialize
f = Figure(740, 230)
f.text(20, 22, "Saving a tree as value and child-count pairs, in pre-order", 12, bold=True)
S = {"root": (140, 70), "a": (80, 135), "b": (210, 135), "a1": (40, 200), "a2": (120, 200), "b1": (210, 200)}
for a, b in [("root", "a"), ("root", "b"), ("a", "a1"), ("a", "a2"), ("b", "b1")]:
    edge(f, S[a], S[b])
for k, (x, y) in S.items():
    node(f, x, y, k, PALE, r=22)
lines = [("root", "2"), ("a", "2"), ("a1", "0"), ("a2", "0"), ("b", "1"), ("b1", "0")]
f.text(330, 50, "tree.bin, one token per line (pairs shown side by side)", 10, MUTED)
for i, (v, n) in enumerate(lines):
    f.cell(330, 60 + i * 26, 70, 24, v, CREAM, size=11); f.cell(400, 60 + i * 26, 40, 24, n, PALE, size=11)
    f.text(450, 77 + i * 26, f"{v} has {n} child{'ren' if n != '1' else ''}", 10, MUTED)
f.save(OUT + "tree-serialize.svg")

# trie
f = Figure(760, 230)
f.text(20, 22, "A trie after inserting \"gpu\" and \"gpucloud\"", 12, bold=True)
letters = "gpucloud"
x0, y = 70, 110
f.cell(20, y - 14, 50, 28, "root", CREAM, size=10)
prev = (70, y)
for i, ch in enumerate(letters):
    x = 120 + i * 78
    term = i in (2, 7)
    f.rect(x - 14, y - 14, 28, 28, GREEN if term else PALE, TEAL if term else INK, 14, width=2.4 if term else 1.4)
    f.arrow(prev[0], y, x - 16, y, INK, 1.2)
    f.text((prev[0] + x - 16) / 2, y - 8, ch, 12, TEAL, mono=True, anchor="middle")
    prev = (x + 14, y)
f.text(20, 170, "Each edge is one character. Green nodes are terminal: a stored word ends there.", 11)
f.text(20, 188, "search(\"gpu\") and search(\"gpucloud\") are true. search(\"gp\") is false: that node exists but is not terminal.", 11)
f.text(20, 206, "starts_with(\"gp\") is true, because it only needs the node to exist.", 11)
f.save(OUT + "trie.svg")
print("ok")
