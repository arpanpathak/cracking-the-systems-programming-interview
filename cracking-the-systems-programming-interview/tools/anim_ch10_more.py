"""Merging two lists by swapping them by value (ch10-merge-k.md, section 10.4.4).

    python3 tools/animations.py merge-owned
"""

from motion import *  # noqa: F401,F403
from motion import Timeline, render
from motion_kit import Panel, arrow, layout

MERGE = Panel("src/bin/merge_k_sorted_lists_owned.rs",
              [("fn merge_two(mut left: Link, mut right: Link) -> Link {", "}")],
              ["while let (Some(l), Some(r)) = (&left, &right) {", "if r.val < l.val {",
               "(left, right) = (right, left);", "let mut node = left.unwrap();",
               "left = node.next.take();", "tail = tail.next.insert(node);",
               "tail.next = left.or(right);", "dummy.next"])
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
            tl.set(code=0.0)
            tl.wait(0.35 * k)
            tl.set(code=1.0)
            if ("cmp", n) in notes:
                tl.say(*notes[("cmp", n)])
            tl.wait(0.4 * k)
            if int(rows["1"][0]) < int(rows["0"][0]):
                rows["0"], rows["1"] = rows["1"], rows["0"]
                tl.set(code=2.0)
                if ("swap", n) in notes:
                    tl.say(*notes[("swap", n)])
                sync(0.7 * k)
                tl.wait(0.4 * k)
            v = rows["0"][0]
            tl.set(code=3.0, hot=v)
            tl.wait(0.5 * k)
            rows["0"].pop(0)
            rows["out"].append(v)
            tl.set(code=4.0)
            sync(0.6 * k)
            tl.set(code=5.0, hot="")
            tl.wait(0.4 * k)
            n += 1
            k = max(0.6, k * 0.8)
        tl.set(code=0.0)
        tl.wait(0.5)
        if attach:
            tl.set(code=6.0)
            left = rows["0"] or rows["1"]
            rows["out"] += left
            rows["0"], rows["1"] = [], []
            sync(0.7)
            tl.set(code=7.0)
        else:
            tl.set(code=6.0)
            tl.to(0.5, gone=1.0)

    sync()
    tl.chapter("merge")
    tl.say("Two sorted lists, left and right. The output starts at dummy, and tail is its end.")
    tl.wait(1.4)
    merge(1.4, {
        ("cmp", 0): ("Both lists have a node. 2 is not smaller than 1, so left already holds the "
                     "smaller front.",),
        ("cmp", 1): ("Now 2 < 4: right holds the smaller front.",),
        ("swap", 1): ("(left, right) = (right, left) swaps the two lists by value. No node moves, "
                      "and no reference is taken.",),
    })
    tl.say("left is empty, so the loop ends. left.or(right) is the list that is left, 5, and "
           "tail.next takes it whole.", "insight")
    tl.wait(2.2)

    tl.chapter("no or")
    tl.say("Now leave out the line after the loop.", "fail")
    tl.wait(0.8)
    rows.update({"0": ["1", "4"], "1": ["2", "3", "5"], "out": []})
    sync(0.6, code=-1.0, strike=6.0, gone=0.0)
    tl.wait(0.4)
    merge(0.5, {}, attach=False)
    tl.say("The output stops at 4. Node 5 stays in right, and is dropped when merge_two "
           "returns.", "fail")
    tl.wait(2.2)

    def draw(p, s, total):
        t = s.t
        title_block(p, "Merging two lists, swapping them by value",
                    "left always holds the smaller front node. It moves to the end of the output.")
        layout_rows = {}
        for part in s.rows.split(";"):
            name, vals = part.split(":")
            layout_rows[name] = [v for v in vals.split(",") if v]
        labels = {"0": "left", "1": "right", "out": "output"}
        for name, y in ROWS.items():
            p.text(26, y + 5, labels[name], 13, INK if name != "out" else TEAL, 700, mono=True)
            vals = layout_rows.get(name, [])
            for a, b in zip(vals, vals[1:]):
                ax, ay = s["x" + a], s["y" + a]
                bx, by = s["x" + b], s["y" + b]
                if abs(ay - by) < 1 and abs(bx - ax - STEP) < 1:
                    arrow(p, ax + 25, ay, bx - 25, by, TEAL if name == "out" else MUTED, 1.8,
                          head=8)
            if not vals and name != "out":
                p.text(X0 - 20, y + 5, "None", 12, FAINT, 700, mono=True)
        out = layout_rows.get("out", [])
        dx = X0 - 78
        p.rect(dx - 30, ROWS["out"] - 18, 60, 36, STAGE, FAINT, 7, 1.3, dash="4 4")
        p.text(dx, ROWS["out"] + 5, "dummy", 11, MUTED, 700, "middle", mono=True)
        if out:
            arrow(p, dx + 31, ROWS["out"], X0 - 25, ROWS["out"], TEAL, 1.8, head=8)
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
