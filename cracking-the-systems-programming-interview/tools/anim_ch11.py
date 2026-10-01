"""The chapter 11 animations (ch11-trees.md), drawn with `motion`.

    python3 tools/animations.py bst trie
"""

from motion import (BRASS, BRASS_LT, FAINT, INK, LINE, MUTED, PAPER, RUST, RUST_LT, TEAL,
                    TEAL_LT, W, caption, code_panel, pill, progress, render, title_block)
from motion_kit import NAVY, edge, layout, line_of, node, play, source


def furniture(p, tl, t, total, title, sub, code_title, code, line, cap_y, rail_y, code_y,
              tint=TEAL):
    title_block(p, title, sub)
    code_panel(p, 26, code_y, W - 52, code_title, code, line, size=11.0, lead=15.6, tint=tint,
               reveal=tl.reached("code", t))
    caption(p, tl, t, cap_y)
    progress(p, tl, t, total, rail_y)


# ----------------------------------------------------------------------- BST


def bst_layout(values, cx=W / 2, top=132, dy=58, spread=180):
    """Positions of the BST built by inserting `values` in order, and each node's parent."""
    pos, parent = {}, {}
    for v in values:
        if not pos:
            pos[v] = (cx, top)
            parent[v] = None
            continue
        cur, depth, x, w = values[0], 1, cx, spread
        while True:
            go_left = v < cur
            nxt = [u for u in pos if parent.get(u) == cur and ((u < cur) == go_left)]
            x = pos[cur][0] + (-w if go_left else w)
            if not nxt:
                pos[v] = (x, top + depth * dy)
                parent[v] = cur
                break
            cur = nxt[0]
            depth += 1
            w /= 2
    return pos, parent


def bst():
    code = source("src/bin/bst_clean.rs", "pub fn insert", "}")
    empty = line_of(code, "Self::Empty =>")
    less = line_of(code, "Ordering::Less => left.insert")
    more = line_of(code, "Ordering::Greater => right.insert")
    values = [8, 3, 10, 1, 6, 14, 13]
    pos, parent = bst_layout(values)
    chain = [1, 2, 3, 4, 5]
    cpos, cparent = bst_layout(chain, cx=W / 2 - 160, top=110, spread=70, dy=44)
    steps = [dict(chapter="insert", say="Insert 8, 3, 10, 1, 6, 14, 13 into an empty tree. Each value walks down "
                  "from the root, comparing as it goes.", code=-1.0)]
    shown = []
    for v in values:
        path = []
        cur = values[0] if shown else None
        while cur is not None:
            path.append(cur)
            kids = [u for u in shown if parent[u] == cur and ((u < cur) == (v < cur))]
            cur = kids[0] if kids else None
        px, py = (pos[values[0]][0], 88) if shown else pos[v]
        steps.append(dict(say="Insert %d." % v, probe=str(v), px=px, py=88.0, pa=1.0, hot="", code=-1.0, dur=0.4))
        for u in path:
            side = "left" if v < u else "right"
            steps.append(dict(say="%d is %s than %d, so it goes %s." % (v, "smaller" if v < u else "larger", u, side),
                              hot=str(u), px=pos[u][0], py=pos[u][1] - 44, code=float(less if v < u else more),
                              dur=0.6, hold=0.1))
        shown.append(v)
        steps.append(dict(say="The %s subtree is empty, so %d becomes a new node there." % (
            "left" if parent[v] is not None and v < parent[v] else "right", v) if parent[v] is not None else
            "The tree is empty, so 8 becomes the root.", shown=list(shown), pa=0.0, hot="", px=pos[v][0], py=pos[v][1],
            code=float(empty)))
    steps.append(dict(say="contains(&6) takes the same walk: 6 < 8 goes left, 6 > 3 goes right, "
                      "and 6 matches.", hot="8 3 6", found="6", kind="insight", hold=1.6))
    steps.append(dict(chapter="sorted input", say="Now insert 1, 2, 3, 4, 5, already sorted. Each value is larger "
                      "than every node, so it always goes right.", kind="fail", shown=[], hot="", found="",
                      chain=chain, hold=1.0))
    steps.append(dict(say="The tree is a chain of five levels. A search costs O(n), not O(log n): the shape "
                      "depends on the insert order.", kind="fail", hold=2.0))
    tl = play(steps, dict(shown=[], probe="", px=W / 2, py=88.0, pa=0.0, hot="", found="", code=-1.0, chain=[]))

    def draw(p, s, total):
        t = s.t
        hot = s.hot.split()
        for v in s.shown:
            if parent[v] is not None:
                on = str(v) in hot and str(parent[v]) in hot
                edge(p, pos[parent[v]], pos[v], TEAL if on else LINE, 2.4 if on else 1.8, r=24)
        for v in values:
            if v not in s.shown:
                continue
            x, y = pos[v]
            if str(v) == s.found:
                node(p, x, y, v, TEAL_LT, TEAL, r=24, size=17)
            elif str(v) in hot:
                node(p, x, y, v, BRASS_LT, BRASS, r=24, size=17)
            else:
                node(p, x, y, v, PAPER, NAVY, r=24, size=17)
        if s.chain:
            for v in s.chain:
                if cparent[v] is not None:
                    edge(p, cpos[cparent[v]], cpos[v], RUST, 1.8, r=20)
                node(p, cpos[v][0], cpos[v][1], v, RUST_LT, RUST, r=20, size=15)
        if s.pa > 0.01:
            pill(p, s.px, s.py, s.probe, BRASS, BRASS_LT, 15, opacity=s.pa)
        furniture(p, tl, t, total, "A binary search tree: every insert is a walk",
                  "Smaller values go left, larger values go right. The walk ends at an empty subtree.",
                  "insert", code, s.code, cap_y, rail_y, CODE_Y)

    CODE_Y = 364
    cap_y, rail_y, height = layout(CODE_Y, len(code))
    return tl, draw, height


# ---------------------------------------------------------------------- trie


def trie():
    code_ins = source("src/problems/trie.rs", "pub fn insert", "}")
    code_find = source("src/problems/trie.rs", "fn find_node", "}")
    code = code_ins + code_find
    entry = line_of(code, "node.children.entry(ch).or_default()")
    term = line_of(code, "node.terminal = true")
    get = line_of(code, "node.children.get(&ch)?")
    some = line_of(code, "Some(node)")
    words = ["cat", "car", "dog"]
    # final trie layout
    nodes = {""}
    for w in words:
        for k in range(1, len(w) + 1):
            nodes.add(w[:k])
    kids = {n: sorted(m for m in nodes if len(m) == len(n) + 1 and m.startswith(n)) for n in nodes}
    xs, slot = {}, [0]

    def place(n):
        if not kids[n]:
            xs[n] = 200 + slot[0] * 210
            slot[0] += 1
        else:
            for m in kids[n]:
                place(m)
            xs[n] = sum(xs[m] for m in kids[n]) / len(kids[n])
    place("")
    ypos = {n: 100 + len(n) * 58 for n in nodes}

    steps = []
    made = {""}
    ends = set()
    for wi, w in enumerate(words):
        steps.append(dict(chapter="insert %s" % w, say="insert(\"%s\") starts at the root." % w, at="", path="",
                          code=0.0))
        for k in range(1, len(w) + 1):
            pre = w[:k]
            if pre in made:
                steps.append(dict(say="'%s': the child already exists, so the walk follows it." % w[k - 1], at=pre,
                                  path=pre, code=float(entry)))
            else:
                made.add(pre)
                steps.append(dict(say="'%s': no child for it yet, so entry().or_default() creates one." % w[k - 1],
                                  at=pre, path=pre, made=sorted(made), code=float(entry)))
        ends.add(w)
        steps.append(dict(say="The last node gets terminal = true: \"%s\" ends here." % w, ends=sorted(ends),
                          code=float(term), hold=0.2))
    steps.append(dict(chapter="queries", say="starts_with(\"ca\") walks c, a and finds a node. It ends no word, but "
                      "it exists, so \"ca\" is a prefix.", at="ca", path="ca", query="ca", code=float(some),
                      kind="insight", hold=1.0))
    steps.append(dict(say="search(\"ca\") reaches the same node, but terminal is false, so \"ca\" is not a "
                      "stored word.", hold=0.8))
    steps.append(dict(say="\"cab\": the node ca has no child 'b', so get returns None and the ? returns None "
                      "at once.", at="ca", path="ca", query="cab", missing=1.0, code=float(get), kind="fail",
                      hold=1.8))
    tl = play(steps, dict(at="", path="", made=[""], ends=[], query="", missing=0.0, code=-1.0))

    def draw(p, s, total):
        t = s.t
        made = set(s.made)
        on = {s.path[:k] for k in range(len(s.path) + 1)}
        for n in sorted(made, key=len):
            if n:
                parent = n[:-1]
                hot = n in on
                edge(p, (xs[parent], ypos[parent]), (xs[n], ypos[n]), TEAL if hot else LINE, 2.4 if hot else 1.8,
                     r=21)
                p.text((xs[parent] + xs[n]) / 2 + (10 if xs[n] >= xs[parent] else -10),
                       (ypos[parent] + ypos[n]) / 2 + 2, n[-1], 13, TEAL if hot else MUTED, 700,
                       "start" if xs[n] >= xs[parent] else "end", mono=True)
        for n in made:
            here = n == s.at
            fill = BRASS_LT if here else (TEAL_LT if n in on else PAPER)
            edge_c = BRASS if here else (TEAL if n in on else NAVY)
            node(p, xs[n], ypos[n], "" if n else "root", fill, edge_c, r=21, size=10 if not n else 13)
            if n:
                p.text(xs[n], ypos[n] + 5, '"%s"' % n, 10.5, INK, 700, "middle", mono=True)
            if n in s.ends:
                p.circle(xs[n], ypos[n], 27, "none", BRASS, 2.4)
        if s.missing > 0.5:
            x, y = xs["ca"] + 70, ypos["ca"] + 58
            edge(p, (xs["ca"], ypos["ca"]), (x, y), RUST, 2, r=21, dash="5 4")
            p.circle(x, y, 21, RUST_LT, RUST, 1.8, dash="5 4")
            p.text(x, y + 5, "b?", 13, RUST, 700, "middle", mono=True)
        if s.query:
            p.text(W - 40, 112, "query: \"%s\"" % s.query, 15, RUST if s.missing > 0.5 else TEAL, 700, "end",
                   mono=True)
        p.text(W - 40, 140, "brass ring = terminal", 11.5, BRASS, 600, "end")
        furniture(p, tl, t, total, "A trie: one node per prefix",
                  "Words that start the same way share nodes. A flag marks where a stored word ends.",
                  "insert and find_node", code, s.code, cap_y, rail_y, CODE_Y)

    CODE_Y = 344
    cap_y, rail_y, height = layout(CODE_Y, len(code))
    return tl, draw, height


def build(name, fn, extra=()):
    def run(only=None):
        tl, draw, height = fn()
        return render(name, tl, draw, height, only=only, extra_colors=extra)
    return run


BUILDERS = {
    "bst": build("ch11-bst.gif", bst, (NAVY,)),
    "trie": build("ch11-trie.gif", trie, (NAVY,)),
}
