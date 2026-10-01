"""Figures for chapter 13: the LRU cache."""
from svgkit import *
OUT = "src/figures/"

# 1. the behaviour, capacity 2
f = Figure(760, 250)
f.text(20, 22, "An LRU cache with room for 2 entries: the recency order after each call", 12, bold=True)
f.text(300, 48, "most recent", 10, MUTED); f.text(420, 48, "least recent", 10, MUTED)
steps = [("put(A, 1)", ["A"], ""), ("put(B, 2)", ["B", "A"], ""), ("get(A) returns 1", ["A", "B"], "A moves to the front"),
         ("put(C, 3)", ["C", "A"], "full: B, the least recent, is evicted"), ("get(B) returns None", ["C", "A"], "B is gone")]
for i, (call, order, note) in enumerate(steps):
    y = 60 + i * 36
    f.text(40, y + 17, call, 11, mono=True)
    for j, k in enumerate(order):
        f.cell(300 + j * 120, y, 100, 26, k, GREEN if j == 0 else PALE, size=11)
        if j:
            f.arrow(300 + j * 120 - 20, y + 13, 300 + j * 120 - 2, y + 13, MUTED, 1.2)
    if call.startswith("put(C"):
        f.cell(540, y, 60, 26, "B", PINK, RUST, 11, dash=True)
    f.text(610, y + 17, note, 10, TEAL)
f.save(OUT + "lru-behaviour.svg")

# 2. generation stamps
f = Figure(760, 270)
f.text(20, 22, "Version 1: a map with stamps, and a queue of access events", 12, bold=True)
f.text(20, 48, "calls: put(a,1) put(b,2) get(a) put(c,3), capacity 2", 11, MUTED, mono=True)
f.text(20, 80, "recency: VecDeque<(K, u64)>, oldest event at the front", 10, MUTED)
ev = [("a", 1, "stale: a is now at 3"), ("b", 2, "current: evict b"), ("a", 3, ""), ("c", 4, "")]
for i, (k, g, note) in enumerate(ev):
    x = 20 + i * 110
    stale = "stale" in note
    f.cell(x, 90, 100, 28, f"({k}, {g})", GREY if stale else (PINK if "evict" in note else PALE), size=11)
    if note:
        f.text(x + 50, 136, note, 9, RUST if not stale else MUTED, anchor="middle")
f.text(20, 170, "map: HashMap<K, (V, u64)>, each key's value and its latest stamp", 10, MUTED)
for i, (k, v, g) in enumerate([("a", 1, 3), ("b", 2, 2), ("c", 3, 4)]):
    x = 20 + i * 150
    f.cell(x, 180, 40, 28, k, CREAM, size=11); f.cell(x + 40, 180, 90, 28, f"({v}, {g})", PINK if k == "b" else GREEN, size=11)
f.text(480, 90, "put(c, 3) makes the map hold 3 keys.", 10)
f.text(480, 108, "Eviction pops events from the front:", 10)
f.text(480, 126, "(a, 1): a's stamp is 3, not 1. Skip.", 10, mono=False)
f.text(480, 144, "(b, 2): b's stamp is 2. Remove b.", 10)
f.text(20, 240, "An event is current only if its stamp equals the key's stamp in the map. Older events for the same key are skipped.", 10, MUTED)
f.save(OUT + "lru-stamps.svg")

# 3. arena layout
f = Figure(760, 300)
f.text(20, 22, "Version 2: nodes in a Vec, linked by index", 12, bold=True)
f.text(20, 46, "after put(A,10) put(B,20) put(C,30) get(A), capacity 3", 11, MUTED, mono=True)
f.text(20, 78, "lookup_table: HashMap<K, usize>", 10, MUTED)
for i, (k, idx) in enumerate([("A", 0), ("B", 1), ("C", 2)]):
    f.cell(20, 86 + i * 30, 40, 26, k, CREAM, size=11); f.cell(60, 86 + i * 30, 40, 26, str(idx), PALE, size=11)
f.text(200, 78, "nodes: Vec<Node<K, V>>", 10, MUTED)
hdr = ["index", "key", "value", "prev", "next"]
for j, h in enumerate(hdr):
    f.text(250 + j * 80, 100, h, 10, MUTED, anchor="middle")
rows = [(0, "A", "10", "None", "Some(2)"), (1, "B", "20", "Some(2)", "None"), (2, "C", "30", "Some(0)", "Some(1)")]
for i, r in enumerate(rows):
    y = 108 + i * 30
    for j, v in enumerate(r):
        f.cell(210 + j * 80, y, 80, 26, str(v), CREAM if j == 0 else (GREEN if i == 0 else (PINK if i == 1 else PALE)), size=10)
f.text(630, 125, "head = Some(0)", 10, TEAL, mono=True); f.text(630, 145, "tail = Some(1)", 10, RUST, mono=True)
f.text(20, 220, "Following next from head gives the recency order:", 11)
order = [("A", "0", GREEN), ("C", "2", PALE), ("B", "1", PINK)]
for i, (k, idx, fill) in enumerate(order):
    x = 20 + i * 150
    f.cell(x, 232, 100, 28, f"{k} (index {idx})", fill, size=10)
    if i:
        f.arrow(x - 48, 246, x - 2, 246)
f.text(20, 278, "most recent", 10, TEAL); f.text(320, 278, "least recent, evicted next", 10, RUST)
f.text(470, 246, "An index is a pointer the borrow checker does not track.", 10, MUTED)
f.save(OUT + "lru-arena.svg")

# 4. touch: detach then push to front
f = Figure(760, 260)
f.text(20, 22, "Moving node C to the front: detach it, then link it at the head", 12, bold=True)
def chain(y, items, hi=None, label="", cut=None):
    f.text(20, y + 18, label, 10, MUTED)
    for i, k in enumerate(items):
        x = 150 + i * 130
        f.cell(x, y, 80, 28, k, GREEN if k == hi else PALE, size=11)
        if i:
            f.arrow(x - 50, y + 10, x - 2, y + 10, INK, 1.2)
            f.arrow(x - 2, y + 20, x - 50, y + 20, MUTED, 1.2, dash=True)
chain(50, ["B", "A", "C", "D"], "C", "before")
f.text(410, 96, "C.prev = A, C.next = D", 10, TEAL, mono=True)
chain(120, ["B", "A", "D"], None, "1. detach C")
f.text(150, 166, "A.next = D  and  D.prev = A: the neighbors now skip C", 10, TEAL, mono=True)
chain(190, ["C", "B", "A", "D"], "C", "2. push_front C")
f.text(150, 238, "C.prev = None, C.next = B, B.prev = C, head = C", 10, TEAL, mono=True)
f.text(640, 60, "solid: next", 10); f.text(640, 76, "dashed: prev", 10, MUTED)
f.save(OUT + "lru-touch.svg")

# 5. Rc layout vs arena layout
f = Figure(760, 300)
f.text(20, 22, "Where the nodes live: one block for the arena, one allocation per node for the Rc list", 12, bold=True)
f.text(20, 50, "arena: Vec<Node<u64, u64>>, 48 bytes per node, side by side", 11, MUTED)
for i in range(6):
    f.cell(20 + i * 90, 60, 90, 30, f"node {i}", GREEN, size=10)
f.text(570, 80, "one allocation, grown rarely", 10, MUTED)
f.text(20, 128, "Rc list: each node is a separate heap block of 56 bytes", 11, MUTED)
fields = [("strong count", 8), ("weak count", 8), ("RefCell borrow flag", 8), ("key", 8), ("value", 8),
          ("prev: Weak", 8), ("next: Option<Rc>", 8)]
for j, (name, size) in enumerate(fields):
    f.cell(20, 138 + j * 20, 170, 20, f"{name}  {size}", CREAM if j < 3 else PALE, size=9)
f.text(200, 152, "Rc and RefCell", 9, BRASS); f.text(200, 164, "bookkeeping", 9, BRASS)
spots = [(290, 150), (400, 236), (500, 150), (600, 236), (680, 150)]
for x, y in spots:
    f.cell(x, y, 60, 26, "node", PALE, size=10)
for (x1, y1), (x2, y2) in zip(spots, spots[1:]):
    f.link((x1, y1, 60, 26), (x2, y2, 60, 26))
f.text(300, 292, "Blocks sit wherever the allocator put them. A miss frees one and allocates another.", 10, MUTED)
f.save(OUT + "lru-rc-layout.svg")

# 6. benchmark bars
f = Figure(760, 170)
f.text(20, 22, "10,000,000 requests, 89.8% hits, capacity 65,536, i5-1038NG7, best of 3", 12, bold=True)
for i, (name, ms, ns, fill) in enumerate([("arena (Vec + indices)", 587.49, 59, GREEN), ("Rc<RefCell> list", 1860, 186, PINK)]):
    y = 50 + i * 50
    f.text(20, y + 20, name, 11, mono=True)
    w = ns / 186 * 420
    f.rect(220, y, w, 30, fill, INK, 3)
    f.text(228 + w, y + 20, f"{ns} ns per request", 11)
f.text(20, 158, "Measured with cargo run --release --bin benchmark cache. Times vary between runs and machines.", 10, MUTED)
f.save(OUT + "lru-bench.svg")
print("ok")
