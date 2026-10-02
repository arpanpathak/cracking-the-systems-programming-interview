"""Merging two lists held in one tuple (ch10-merge-k.md, section 10.4.4).

    python3 tools/animations.py merge-owned
"""

from motion import *  # noqa: F401,F403
from motion import Timeline, render
from motion_kit import Panel, arrow, layout

MERGE = Panel("src/bin/merge_k_sorted_lists_owned.rs",
              [("fn merge_two(left: Link, right: Link) -> Link {", "}")],
              ["while let (Some(left), Some(right)) = lists {",
               "let (mut smaller, larger) = if left.val <= right.val {",
               "lists = (smaller.next.take(), Some(larger));",
               "tail = &mut tail.insert(smaller).next;", "*tail = lists.0.or(lists.1);", ("head", 2)])
ROWS = {"0": 118, "1": 182, "out": 270}
X0, STEP = 220, 66
VALUES = ["1", "4", "2", "3", "5"]


def merge_owned():
    init = {"caption": "", "kind": "step", "code": -1.0, "strike": -1.0, "rows": "", "hot": "",
            "gone": 0.0}
    for v in VALUES:
        init.update({"x" + v: 0.0, "y" + v: 0.0, "a" + v: 1.0})
    tl = Timeline(**init)
    rows = {"0": ["1", "4"], "1": ["2", "3", "5"], "out": []}

    def targets():
        moves = {}
        for name, vals in rows.items():
            for k, v in enumerate(vals):
                moves["x" + v] = float(X0 + k * STEP)
                moves["y" + v] = float(ROWS[name])
        return moves

    def sync(dur=0.0, **extra):
        tl.set(rows=";".join("%s:%s" % (n, ",".join(v)) for n, v in rows.items()), **extra)
        if dur:
            tl.to(dur, in_out, **targets())
        else:
            tl.set(**targets())

    def merge(k, notes, attach=True):
        n = 0
        while rows["0"] and rows["1"]:
            a, b = rows["0"][0], rows["1"][0]
            tl.set(code=0.0)
            tl.wait(0.35 * k)
            small = "0" if int(a) <= int(b) else "1"
            v = rows[small][0]
            tl.set(code=1.0, hot=v)
            if ("pick", n) in notes:
                tl.say(*notes[("pick", n)])
            tl.wait(0.6 * k)
            # the front node goes to the end of the output
            rows[small].pop(0)
            rows["out"].append(v)
            tl.set(code=3.0)
            sync(0.6 * k)
            # the rest of the smaller list, then the larger list, go back into the tuple
            rest, larger = rows[small], rows["1" if small == "0" else "0"]
            rows["0"], rows["1"] = rest, larger
            tl.set(code=2.0, hot="")
            if ("back", n) in notes:
                tl.say(*notes[("back", n)])
            sync(0.5 * k)
            tl.wait(0.4 * k)
            n += 1
            k = max(0.6, k * 0.8)
        tl.set(code=0.0)
        tl.wait(0.5)
        if attach:
            tl.set(code=4.0)
            left = rows["0"] or rows["1"]
            rows["out"] += left
            rows["0"], rows["1"] = [], []
            sync(0.7)
            tl.set(code=5.0)
        else:
            tl.set(code=4.0)
            tl.to(0.5, gone=1.0)

    sync()
    tl.chapter("merge")
    tl.say("lists is a tuple of two sorted lists. The output starts empty, and tail is its end.")
    tl.wait(1.4)
    merge(1.4, {
        ("pick", 0): ("Both lists have a node, so the pattern matches. 1 <= 2, so smaller is the "
                      "first list.",),
        ("back", 0): ("1 went to the end of the output. The rest of its list, 4, and the whole "
                      "larger list go back into the tuple.",),
        ("pick", 1): ("4 > 2, so this time smaller is the second list.",),
        ("back", 1): ("The rest of the smaller list goes back first, so the two rows trade "
                      "places.",),
    })
    tl.say("lists.0 is empty, so the pattern fails and nothing moves. or picks the list that "
           "is left, 5, and tail attaches it.", "insight")
    tl.wait(2.2)

    tl.chapter("no or")
    tl.say("Now leave out the line after the loop.", "fail")
    tl.wait(0.8)
    rows.update({"0": ["1", "4"], "1": ["2", "3", "5"], "out": []})
    sync(0.6, code=-1.0, strike=4.0, gone=0.0)
    tl.wait(0.4)
    merge(0.5, {}, attach=False)
    tl.say("The output stops at 4. Node 5 stays in lists, and is dropped when merge_two "
           "returns.", "fail")
    tl.wait(2.2)

    def draw(p, s, total):
        t = s.t
        title_block(p, "Merging two lists held in one tuple",
                    "Each pass moves the smaller front node to the end of the output.")
        layout_rows = {}
        for part in s.rows.split(";"):
            name, vals = part.split(":")
            layout_rows[name] = [v for v in vals.split(",") if v]
        labels = {"0": "lists.0", "1": "lists.1", "out": "output"}
        for name, y in ROWS.items():
            p.text(26, y + 5, labels[name], 13, INK if name != "out" else TEAL, 700, mono=True)
            vals = layout_rows.get(name, [])
            for a, b in zip(vals, vals[1:]):
                ax, ay = s["x" + a], s["y" + a]
                bx, by = s["x" + b], s["y" + b]
                if abs(ay - by) < 1 and abs(bx - ax - STEP) < 1:
                    arrow(p, ax + 25, ay, bx - 25, by, TEAL if name == "out" else MUTED, 1.8,
                          head=8)
            if not vals:
                p.text(X0 - 20, y + 5, "None", 12, FAINT, 700, mono=True)
        out = layout_rows.get("out", [])
        tx = X0 + len(out) * STEP
        p.text(tx, ROWS["out"] + 44, "tail", 12, TEAL, 700, "middle", mono=True)
        arrow(p, tx, ROWS["out"] + 30, tx, ROWS["out"] + 8, TEAL, 1.6, head=8)
        for v in VALUES:
            x, y = s["x" + v], s["y" + v]
            hot = s.hot == v
            dropped = s.gone > 0.01 and v in layout_rows.get("0", []) + layout_rows.get("1", [])
            fill = RUST_LT if dropped else (BRASS_LT if hot else
                                            (TEAL_LT if v in out else PAPER))
            edge = RUST if dropped else (BRASS if hot else (TEAL if v in out else INK))
            p.rect(x - 22, y - 20, 44, 40, fill, edge, 8, 1.7, shadow="lift" if hot else None)
            p.text(x, y + 6, v, 17, INK, 700, "middle", mono=True)
            if dropped:
                p.text(x, y + 36, "dropped", 10.5, RUST, 700, "middle",
                       opacity=clamp(s.gone))
        MERGE.draw(p, 26, 330, W - 52, "merge_two", s, t, strike=s.strike, size=10.6,
                   lead=14.4, tint=RUST if s.strike >= 0 else TEAL)
        caption(p, tl, t, CAP)
        progress(p, tl, t, total, RAIL)

    CAP, RAIL, height = layout(330, len(MERGE), 14.4)
    return tl, draw, height


def build_merge_owned(only=None):
    tl, draw, height = merge_owned()
    return render("ch10-merge-owned.gif", tl, draw, height, only=only)


BUILDERS = {
    "merge-owned": build_merge_owned,
}
