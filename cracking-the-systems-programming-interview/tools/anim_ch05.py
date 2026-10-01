"""The chapter 5 animations (ch05-heaps.md), drawn with `motion`.

    python3 tools/animations.py heap-sift top-k
"""

import math

from motion import (BRASS, BRASS_LT, FAINT, INK, LINE, MUTED, PAPER, RUST, RUST_LT, TEAL,
                    TEAL_LT, W, caption, code_panel, progress, render, title_block)
from motion_kit import (NAVY, cells, edge, heap_positions, kv_panel, layout, line_of, node,
                        play, row_xs, source)


def furniture(p, tl, t, total, title, sub, code_title, code, line, cap_y, rail_y, code_y,
              lead=15.6, tint=TEAL):
    title_block(p, title, sub)
    code_panel(p, 26, code_y, W - 52, code_title, code, line, size=11.0, lead=lead, tint=tint,
               reveal=tl.reached("code", t))
    caption(p, tl, t, cap_y)
    progress(p, tl, t, total, rail_y)


# ---------------------------------------------------------------- heap sift


def heap_sift():
    rule = ["parent(i)   = (i - 1) / 2",
            "children(i) = 2i + 1, 2i + 2",
            "push: append, then swap up while larger than the parent",
            "pop:  take index 0, move the last value there, then swap",
            "      down with the larger child while smaller than it"]
    values = [9, 5, 8, 3, 2, 10]
    POS = heap_positions(6, W / 2, 112, 66, 130)
    XS = row_xs(6, 52, 8, cx=W / 2)
    defaults = dict(code=-1.0, n=5, hot="", gone=0.0, bad="")
    for i, v in enumerate(values):
        defaults["tx%d" % v], defaults["ty%d" % v] = POS[i]
        defaults["ax%d" % v] = XS[i]
    heap = [9, 5, 8, 3, 2]

    def where():
        out = {}
        for i, v in enumerate(heap):
            out["tx%d" % v], out["ty%d" % v] = POS[i]
            out["ax%d" % v] = XS[i]
        return out

    steps = [dict(chapter="push", say="A max-heap: every parent is at least as large as its children. "
                  "The array is 9, 5, 8, 3, 2.", code=0.0)]
    heap.append(10)
    st = dict(say="push(10) appends 10 at index 5, the next free spot on the bottom level.", n=6, hot="10",
              code=2.0)
    st.update(where()); steps.append(st)
    i = 5
    while i > 0:
        parent = (i - 1) // 2
        if heap[i] <= heap[parent]:
            break
        steps.append(dict(say="Its parent is index (%d - 1) / 2 = %d, holding %d. 10 is larger, so they swap."
                          % (i, parent, heap[parent]), code=0.0))
        heap[i], heap[parent] = heap[parent], heap[i]
        st = dict(say="10 is now at index %d." % parent, code=2.0, dur=1.0)
        st.update(where()); steps.append(st)
        i = parent
    steps.append(dict(say="10 reached the root. Two swaps for a heap of three levels: O(log n).",
                      kind="insight", hot="", code=-1.0, hold=1.0))
    # pop
    steps.append(dict(chapter="pop", say="pop() takes the root, 10, the largest value.", hot="10", code=3.0))
    last = heap.pop()
    root = heap[0]
    heap[0] = last
    st = dict(say="The last value, %d, moves into the hole at the root." % last, gone=1.0, n=5, hot=str(last),
              code=3.0, dur=1.1)
    st.update(where()); steps.append(st)
    i = 0
    while True:
        l, r = 2 * i + 1, 2 * i + 2
        kids = [c for c in (l, r) if c < len(heap)]
        if not kids:
            break
        big = max(kids, key=lambda c: heap[c])
        if heap[big] <= heap[i]:
            break
        steps.append(dict(say="Its children hold %s. The larger is %d, and %d is smaller than it, so they swap."
                          % (" and ".join(str(heap[c]) for c in kids), heap[big], heap[i]), code=4.0))
        heap[i], heap[big] = heap[big], heap[i]
        st = dict(say="%d is now at index %d." % (heap[big], big), dur=1.0)
        st.update(where()); steps.append(st)
        i = big
    steps.append(dict(say="The heap is valid again: 9, 5, 8, 3, 2.", kind="insight", hot="", code=-1.0, hold=1.0))
    # the failing case: swap with the smaller child
    heap = [8, 5, 9, 3, 2]
    st = dict(chapter="wrong child", say="Back to the moment 8 sat at the root. Suppose it swapped with the "
              "smaller child, 5, instead.", kind="fail", hot="8", code=4.0, dur=1.0)
    st.update(where()); steps.append(st)
    heap = [5, 8, 9, 3, 2]
    st = dict(say="5 becomes the parent of 9. A parent smaller than its child breaks the heap rule.",
              kind="fail", bad="5,9", dur=1.0, hold=1.8)
    st.update(where()); steps.append(st)
    tl = play(steps, defaults)

    def draw(p, s, total):
        t = s.t
        n = int(round(s.n))
        pos = POS
        for i in range(1, 6):
            parent = (i - 1) // 2
            on = i < n
            edge(p, pos[parent], pos[i], LINE if on else "#eef2f5", 1.8, r=24)
        for i in range(6):
            if i >= n:
                p.circle(pos[i][0], pos[i][1], 24, "none", "#e3e8ee", 1.4, dash="4 4")
            p.text(pos[i][0] + 30, pos[i][1] - 16, str(i), 10.5, FAINT, 600, mono=True)
        xs = XS
        ay = 336
        p.text(xs[0] - 40, ay + 32, "array", 12, MUTED, 600, "end")
        for i in range(6):
            p.rect(xs[i] - 26, ay, 52, 52, "#f6f8fa" if i < n else "none", LINE if i < n else "#e3e8ee",
                   8, 1.2, dash=None if i < n else "4 4")
            p.text(xs[i], ay + 70, str(i), 10.5, FAINT, 600, "middle", mono=True)
        bad = s.bad.split(",") if s.bad else []
        for v in values:
            if v == 10 and (s.gone > 0.5 or s.n < 5.5):
                continue
            x, y, ax = s["tx%d" % v], s["ty%d" % v], s["ax%d" % v]
            # While two values swap, lift the one moving left and drop the one
            # moving right, so they pass each other instead of overlapping.
            when, old = tl.changed("ax%d" % v, t)
            lift = 0.0
            if old is not None:
                target = next((b for a0, _e, _a, b, _ease in tl.segments["ax%d" % v] if a0 == when), ax)
                if abs(target - old) > 1:
                    u = (ax - old) / (target - old)
                    if 0 < u < 1:
                        lift = math.sin(math.pi * u) * 30 * (-1 if target < old else 1)
            hot = str(v) == s.hot
            fill, edge_c = (BRASS_LT, BRASS) if hot else (PAPER, NAVY)
            if str(v) in bad:
                fill, edge_c = RUST_LT, RUST
            node(p, x, y, v, fill, edge_c, r=24, size=17)
            p.rect(ax - 22, ay + 4 + lift, 44, 44, fill, edge_c, 7, 1.6)
            p.text(ax, ay + 33 + lift, str(v), 17, INK, 700, "middle", mono=True)
        furniture(p, tl, t, total, "A heap: push swaps up, pop swaps down",
                  "The tree lives in the array. Index arithmetic finds each node's parent and children.",
                  "the rules", rule, s.code, cap_y, rail_y, CODE_Y)

    CODE_Y = 430
    cap_y, rail_y, height = layout(CODE_Y, len(rule))
    return tl, draw, height


# --------------------------------------------------------------------- top k


def top_k():
    code = source("src/bin/top_k_frequent_words.rs", "let mut min_heap", "}")
    push = line_of(code, "min_heap.push")
    over = line_of(code, "if min_heap.len() > k")
    pop = line_of(code, "min_heap.pop()")
    k = 2
    counts = [("the", 3), ("cat", 1), ("and", 2), ("dog", 1)]
    steps = [dict(chapter="count", say="The words are counted first: the 3, cat 1, and 2, dog 1. k is 2.",
                  entries=[(w, c) for w, c in counts], code=-1.0),
             dict(say="The loop visits the map in no fixed order. This run takes the order shown.", code=0.0)]
    heap = []
    cur = 0
    for word, c in counts:
        heap.append((c, word))
        heap.sort()
        first = cur == 0
        steps.append(dict(chapter="heap" if first else None,
                          say="Push (%d, %s). Reverse makes the smallest count the top of the heap." % (c, word),
                          heap=[list(x) for x in heap], visit=float(cur), code=float(push), dropped=""))
        if len(heap) > k:
            low = heap.pop(0)
            steps.append(dict(say="The heap holds %d entries, more than k. pop removes the top, (%d, %s), the "
                              "least frequent so far." % (k + 1, low[0], low[1]), code=float(pop),
                              dropped="%d, %s" % low))
            steps.append(dict(say="The heap is back to k entries.", heap=[list(x) for x in heap], dropped="",
                              hold=0.2))
        cur += 1
    steps.append(dict(say="The heap keeps the two most frequent words, the and and. It never held more than "
                      "k + 1 entries.", kind="insight", visit=-1.0, code=-1.0, hold=1.6))
    steps = [{a: b for a, b in st.items() if b is not None} for st in steps]
    tl = play(steps, dict(entries=[], heap=[], visit=-1.0, code=-1.0, dropped=""))

    def draw(p, s, total):
        t = s.t
        kv_panel(p, tl, t, 26, 84, 250, "frequencies", s.entries, "entries",
                 hot=counts[int(s.visit)][0] if s.visit >= 0 else None, rows=4)
        p.text(330, 108, "min_heap (top first)", 12, MUTED, 600)
        for i, (c, w) in enumerate(s.heap):
            y = 122 + i * 46
            top = i == 0
            p.rect(330, y, 230, 38, BRASS_LT if top else PAPER, BRASS if top else NAVY, 8, 1.6)
            p.text(345, y + 25, "Rev((%d, \"%s\"))" % (c, w), 14, INK, 700, mono=True)
            if top:
                p.text(570, y + 24, "← top", 11.5, BRASS, 700)
        if s.dropped:
            p.text(330, 122 + 3 * 46 + 20, "popped: (%s)" % s.dropped, 13, RUST, 700, mono=True)
        p.text(650, 108, "k = %d" % k, 15, INK, 700, mono=True)
        furniture(p, tl, t, total, "Top k with a min-heap of size k",
                  "Each count is pushed. When the heap holds k + 1 entries, the smallest is popped.",
                  "top_k_frequent (the heap loop)", code, s.code, cap_y, rail_y, CODE_Y)

    CODE_Y = 300
    cap_y, rail_y, height = layout(CODE_Y, len(code))
    return tl, draw, height


def build(name, fn, extra=()):
    def run(only=None):
        tl, draw, height = fn()
        return render(name, tl, draw, height, only=only, extra_colors=extra)
    return run


BUILDERS = {
    "heap-sift": build("ch05-heap-sift.gif", heap_sift, (NAVY,)),
    "top-k": build("ch05-top-k.gif", top_k, (NAVY,)),
}
