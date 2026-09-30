"""Figures for chapter 12: graphs."""
import math
from svgkit import *
OUT = "src/figures/"


def node(f, x, y, label, fill=PALE, r=17, stroke=INK, width=1.4):
    f.rect(x - r, y - r, 2 * r, 2 * r, fill, stroke, r, width=width)
    f.text(x, y + 4, str(label), 12, mono=True, anchor="middle")


def link(f, a, b, label=None, color=INK, directed=True, r=17, width=1.6, dash=False, off=(0, -6)):
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    x1, y1 = a[0] + r * math.cos(ang), a[1] + r * math.sin(ang)
    x2, y2 = b[0] - (r + 1) * math.cos(ang), b[1] - (r + 1) * math.sin(ang)
    if directed:
        f.arrow(x1, y1, x2, y2, color, width, dash)
    else:
        f.line(x1, y1, x2, y2, color, width, dash)
    if label is not None:
        f.text((x1 + x2) / 2 + off[0], (y1 + y2) / 2 + off[1], str(label), 11, color, mono=True, anchor="middle")


SAMPLE = {"A": (60, 130), "B": (150, 70), "C": (150, 190), "D": (250, 130)}
SAMPLE_EDGES = [("A", "B", 1), ("A", "C", 4), ("B", "C", 2), ("B", "D", 5), ("C", "D", 1)]


def sample(f, dx=0, dy=0, fills=None, labels=None, weights=True):
    P = {k: (x + dx, y + dy) for k, (x, y) in SAMPLE.items()}
    offs = {("A", "B"): (-8, -4), ("A", "C"): (-8, 12), ("B", "C"): (-8, 4), ("B", "D"): (8, -4), ("C", "D"): (8, 12)}
    for a, b, w in SAMPLE_EDGES:
        link(f, P[a], P[b], w if weights else None, off=offs[(a, b)])
    for k, (x, y) in P.items():
        node(f, x, y, (labels or {}).get(k, k), (fills or {}).get(k, PALE))
    return P


# 1. vocabulary and the sample graph
f = Figure(760, 262)
f.text(20, 22, "Graph terms", 12, bold=True)
f.text(20, 46, "undirected: roads", 11, MUTED)
U = {"x": (50, 100), "y": (140, 80), "z": (100, 170)}
for a, b in [("x", "y"), ("y", "z"), ("x", "z")]:
    link(f, U[a], U[b], directed=False)
for k, (x, y) in U.items():
    node(f, x, y, k)
f.text(20, 236, "an edge works both ways", 10, MUTED)
f.text(20, 251, "x, y, z form a cycle", 10, MUTED)
f.text(230, 46, "directed and weighted: the chapter's sample", 11, MUTED)
sample(f, 200, 8)
f.text(230, 236, "an edge has a direction and a weight", 10, MUTED)
f.text(230, 251, "no cycle: no path returns to its start", 10, MUTED)
notes = ["node (vertex): a thing, such as A", "edge: a connection from one node to another",
         "neighbors of B: C and D", "weight: a cost on an edge, such as 5 for B to D",
         "path: A to B to D, cost 1 + 5 = 6", "cycle: a path that returns to its start"]
for i, t in enumerate(notes):
    f.text(500, 70 + i * 26, t, 11)
f.save(OUT + "graph-terms.svg")

# 2. adjacency list layouts
f = Figure(760, 300)
f.text(20, 22, "Two ways to store the sample graph as an adjacency list", 12, bold=True)
f.text(20, 50, "index form: Vec<Vec<(usize, u32)>>, A=0, B=1, C=2, D=3", 11, MUTED)
f.text(20, 76, "stack", 10, MUTED)
f.cell(20, 82, 46, 24, "ptr", CREAM, size=10); f.cell(66, 82, 40, 24, "4", CREAM, size=10); f.cell(106, 82, 40, 24, "4", CREAM, size=10)
f.text(66, 120, "len, cap", 9, MUTED)
f.line(43, 106, 43, 140); f.line(43, 140, 160, 140); f.line(160, 140, 160, 94); f.arrow(160, 94, 178, 94)
rows = [["(1,1)", "(2,4)"], ["(2,2)", "(3,5)"], ["(3,1)"], []]
f.text(200, 76, "heap: one Vec header per node", 10, MUTED)
for i, row in enumerate(rows):
    y = 82 + i * 30
    f.text(192, y + 16, str(i), 10, MUTED, mono=True, anchor="end")
    f.cell(200, y, 46, 24, "ptr", PALE, size=10); f.cell(246, y, 30, 24, str(len(row)), PALE, size=10)
    f.cell(276, y, 30, 24, str(len(row)), PALE, size=10)
    if row:
        f.arrow(306, y + 12, 346, y + 12)
        for j, e in enumerate(row):
            f.cell(348 + j * 58, y, 58, 24, e, GREEN, size=10)
    else:
        f.text(320, y + 16, "no allocation", 10, MUTED)
f.text(348, 76, "heap: (neighbor, weight) pairs", 10, MUTED)
f.text(20, 222, "map form: HashMap<&str, &[(&str, u32)]>", 11, MUTED)
for i, (k, v) in enumerate([("\"A\"", "[(\"B\",1), (\"C\",4)]"), ("\"B\"", "[(\"C\",2), (\"D\",5)]"),
                            ("\"C\"", "[(\"D\",1)]"), ("\"D\"", "[]")]):
    x = 20 + i * 180
    f.cell(x, 232, 40, 24, k, CREAM, size=10); f.cell(x + 40, 232, 130, 24, v, GREEN, size=9)
f.text(20, 280, "The index form finds a node's edges with one array index. The map form hashes the key, "
       "and allows any node type.", 10, MUTED)
f.save(OUT + "graph-layout.svg")

# 3. BFS and DFS traces
f = Figure(760, 330)
f.text(20, 22, "Breadth first uses a queue; depth first uses a stack", 12, bold=True)
sample(f, 0, 20, weights=False)
f.text(300, 50, "bfs_vec from A (queue: take from the front)", 11, TEAL, bold=True)
bfs = [("start", "A", ""), ("take A", "B C", "A"), ("take B", "C D", "A B"), ("take C", "D", "A B C"),
       ("take D", "", "A B C D")]
f.text(300, 72, "step", 10, MUTED); f.text(390, 72, "queue after", 10, MUTED); f.text(530, 72, "visit order", 10, MUTED)
for i, (s, q, o) in enumerate(bfs):
    y = 90 + i * 20
    f.text(300, y, s, 10, mono=True); f.text(390, y, q or "empty", 10, mono=True); f.text(530, y, o, 10, mono=True)
f.text(300, 200, "dfs_vec from A (stack: take from the top, the right end)", 11, RUST, bold=True)
dfs = [("start", "A", ""), ("take A", "B C", "A"), ("take C", "B D", "A C"), ("take D", "B", "A C D"),
       ("take B", "C D", "A C D B"), ("take D", "C", "seen: skip"), ("take C", "", "seen: skip")]
for i, (s, q, o) in enumerate(dfs):
    y = 222 + i * 15
    f.text(300, y, s, 10, mono=True); f.text(390, y, q or "empty", 10, mono=True); f.text(530, y, o, 10, mono=True)
f.text(20, 230, "BFS visits A, B, C, D:", 10, TEAL)
f.text(20, 246, "nodes one edge away, then two.", 10, TEAL)
f.text(20, 270, "DFS visits A, C, D, B:", 10, RUST)
f.text(20, 286, "it follows the last neighbor pushed", 10, RUST)
f.text(20, 302, "as deep as it can go first.", 10, RUST)
f.save(OUT + "graph-bfs-dfs.svg")

# 4. islands
f = Figure(760, 215)
f.text(20, 22, "Counting islands: each flood fill from new land adds one", 12, bold=True)
grid = ["11000", "11000", "00100", "00011"]
island = {(0, 0): 1, (0, 1): 1, (1, 0): 1, (1, 1): 1, (2, 2): 2, (3, 3): 3, (3, 4): 3}
fills = {1: GREEN, 2: CREAM, 3: PINK}
for r, row in enumerate(grid):
    for c, ch in enumerate(row):
        f.cell(40 + c * 36, 40 + r * 36, 36, 36, ch, fills.get(island.get((r, c)), "#ffffff"), size=12)
for c in range(5):
    f.text(58 + c * 36, 200, str(c), 9, MUTED, anchor="middle")
for r in range(4):
    f.text(30, 62 + r * 36, str(r), 9, MUTED, anchor="end")
steps = ["Scan the cells row by row, left to right.",
         "(0,0) is land and not visited: count = 1. BFS marks the", "   four green cells: (0,0), (0,1), (1,0), (1,1).",
         "(0,1), (1,0), (1,1) are already visited: skipped.",
         "(2,2) is new land: count = 2. Its neighbors are water.",
         "(3,3) is new land: count = 3. BFS also marks (3,4).",
         "(2,2) and (3,3) touch only at a corner, so they are separate."]
for i, t in enumerate(steps):
    f.text(250, 50 + i * 20, t, 11)
f.save(OUT + "graph-islands.svg")

# 5. cycle detection with three states
f = Figure(760, 250)
f.text(20, 22, "Cycle detection with three states", 12, bold=True)
f.text(20, 46, "A to B to C to A: C finds A still Visiting", 11, MUTED)
C3 = {"A": (60, 110), "B": (170, 110), "C": (115, 190)}
link(f, C3["A"], C3["B"]); link(f, C3["B"], C3["C"]); link(f, C3["C"], C3["A"], "back edge", RUST, width=2.4, off=(-34, 0))
for k, (x, y) in C3.items():
    node(f, x, y, k, CREAM, stroke=BRASS, width=2)
f.text(290, 46, "diamond: D is reached twice, but it is Done", 11, MUTED)
DM = {"A": (320, 140), "B": (420, 85), "C": (420, 195), "D": (520, 140)}
for a, b in [("A", "B"), ("A", "C"), ("B", "D")]:
    link(f, DM[a], DM[b])
link(f, DM["C"], DM["D"], "D is Done: no cycle", TEAL, width=2.2, off=(58, 16))
for k, (x, y) in DM.items():
    node(f, x, y, k, GREEN if k in "BD" else CREAM, stroke=INK if k in "BD" else BRASS, width=1.4 if k in "BD" else 2)
legend = [(GREY, "Unvisited: not reached yet"), (CREAM, "Visiting: on the current path"), (GREEN, "Done: fully explored")]
for i, (fill, t) in enumerate(legend):
    f.rect(590, 70 + i * 30, 14, 14, fill, INK, 3); f.text(612, 82 + i * 30, t, 10)
f.text(20, 238, "An edge to a Visiting node closes a loop. An edge to a Done node only joins a path explored earlier.", 10, MUTED)
f.save(OUT + "graph-cycle.svg")

# 6. Kahn's algorithm
f = Figure(760, 270)
f.text(20, 22, "Kahn's algorithm: take a node with no remaining prerequisites, then cross it off", 12, bold=True)
K = {"datastructs": (90, 120), "algos": (270, 70), "os": (270, 170), "compilers": (450, 120)}
for a, b in [("datastructs", "algos"), ("datastructs", "os"), ("algos", "compilers"), ("os", "compilers")]:
    (x1, y1), (x2, y2) = K[a], K[b]
    f.arrow(x1 + 62, y1 + (y2 - y1) * 0.18, x2 - 62, y2 - (y2 - y1) * 0.18)
for k, (x, y) in K.items():
    f.rect(x - 60, y - 16, 120, 32, GREEN if k == "datastructs" else PALE, INK, 16)
    f.text(x, y + 4, k, 11, mono=True, anchor="middle")
indeg = {"datastructs": 0, "algos": 1, "os": 1, "compilers": 2}
for k, (x, y) in K.items():
    f.text(x, y + 32, f"indegree {indeg[k]}", 10, MUTED, anchor="middle")
f.text(560, 58, "take         indegrees after", 10, MUTED, mono=True)
trace = [("datastructs", "algos 0, os 0"), ("algos", "compilers 1"), ("os", "compilers 0"), ("compilers", "")]
for i, (t, d) in enumerate(trace):
    f.text(560, 80 + i * 20, f"{t:<12} {d}", 10, mono=True)
f.text(20, 240, "An arrow points from a course to a course that depends on it. The indegree counts the arrows coming in.", 10, MUTED)
f.text(20, 256, "Order: datastructs, algos, os, compilers. If a cycle existed, its nodes would never reach indegree 0.", 10, MUTED)
f.save(OUT + "graph-kahn.svg")

# 7. Dijkstra trace
f = Figure(760, 300)
f.text(20, 22, "Dijkstra's algorithm on the graph in dijkstra.rs, starting at A", 12, bold=True)
DJ = {"A": (60, 130), "B": (180, 70), "C": (180, 190), "D": (300, 130)}
link(f, DJ["A"], DJ["B"], 4, off=(-8, -4)); link(f, DJ["A"], DJ["C"], 1, off=(-8, 12))
link(f, DJ["C"], DJ["B"], 2, TEAL, width=2.2, off=(-10, 4)); link(f, DJ["B"], DJ["D"], 1, TEAL, width=2.2, off=(8, -4))
link(f, DJ["C"], DJ["D"], 5, off=(8, 12))
for k, (x, y) in DJ.items():
    node(f, x, y, k)
f.text(20, 250, "A to B directly costs 4.", 10, MUTED)
f.text(20, 266, "A to C to B costs 1 + 2 = 3, so the", 10, MUTED)
f.text(20, 282, "direct entry (4, B) becomes stale.", 10, MUTED)
f.text(370, 50, "pop       dist after              heap after (smallest first)", 10, MUTED, mono=True)
rows = [("start", "A0", "(0,A)"), ("(0,A)", "A0 B4 C1", "(1,C) (4,B)"), ("(1,C)", "A0 B3 C1 D6", "(3,B) (4,B) (6,D)"),
        ("(3,B)", "A0 B3 C1 D4", "(4,B) (4,D) (6,D)"), ("(4,B)", "stale: 4 > 3", "(4,D) (6,D)"),
        ("(4,D)", "D has no edges", "(6,D)"), ("(6,D)", "stale: 6 > 4", "empty")]
for i, (p, d, h) in enumerate(rows):
    y = 74 + i * 22
    f.rect(365, y - 14, 385, 20, GREY if "stale" in d else "#ffffff", "none", 0)
    f.text(370, y, f"{p:<9} {d:<23} {h}", 10, RUST if "stale" in d else INK, mono=True)
f.text(370, 250, "Result: A 0, C 1, B 3, D 4. Each pop takes the smallest", 10)
f.text(370, 266, "cost in the heap, so the first time a node is popped with", 10)
f.text(370, 282, "its recorded cost, that cost is final.", 10)
f.save(OUT + "graph-dijkstra.svg")

# 8. Kruskal with union-find
f = Figure(760, 310)
f.text(20, 22, "Kruskal's algorithm: take edges from lightest to heaviest, skip any that close a loop", 12, bold=True)
KR = {0: (50, 150), 1: (150, 70), 2: (150, 230), 3: (250, 150), 4: (340, 150)}
kept = {(1, 2), (1, 3), (3, 4), (0, 2)}
for a, b, w in [(0, 1, 4), (0, 2, 3), (1, 2, 1), (1, 3, 2), (2, 3, 4), (3, 4, 2)]:
    k = (a, b) in kept
    link(f, KR[a], KR[b], w, TEAL if k else "#9aa7b4", directed=False, width=2.6 if k else 1.2, dash=not k,
         off=(-10, 0) if (a, b) == (1, 2) else (0, -6))
for k, (x, y) in KR.items():
    node(f, x, y, k)
f.text(400, 50, "edge   union        parent after      rank", 10, MUTED, mono=True)
tr = [("1-2 1", "roots 1, 2", "0 2 2 3 4", "rank[2] = 1"), ("1-3 2", "roots 2, 3", "0 2 2 2 4", ""),
      ("3-4 2", "roots 2, 4", "0 2 2 2 2", ""), ("0-2 3", "roots 0, 2", "2 2 2 2 2", ""),
      ("0-1 4", "same root 2", "skip: loop", ""), ("2-3 4", "same root 2", "skip: loop", "")]
for i, (e, u, p, r) in enumerate(tr):
    y = 72 + i * 22
    f.text(400, y, f"{e:<6} {u:<12} {p:<17} {r}", 10, RUST if "skip" in p else INK, mono=True)
f.text(400, 220, "parent[i] is the node i points to. A node that points", 10)
f.text(400, 236, "to itself is the root of its group. Two nodes are in the", 10)
f.text(400, 252, "same group when find() returns the same root.", 10)
f.text(20, 290, "Kept edges (solid): 1-2, 1-3, 3-4, 0-2, total weight 8. They connect all five nodes with four edges.", 10, MUTED)
f.save(OUT + "graph-kruskal.svg")
print("ok")
