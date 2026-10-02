"""Merging with owned values only (ch10-merge-k.md, section 10.4.4).

    python3 tools/animations.py merge-owned
"""

from anim_ch09_ops import link_arrow
from motion import *  # noqa: F401,F403
from motion import Timeline, render
from motion_kit import Panels, layout

OWNED = Panels("src/bin/merge_k_sorted_lists_owned.rs",
               [[("fn merge_two(mut left: Link, mut right: Link) -> Link {", "}")],
                [("fn reverse(mut current: Link) -> Link {", "}")]],
               ["merge_two", "reverse"],
               ["(Some(mut l), Some(r)) if l.val <= r.val => {", "(l, Some(mut r)) => {",
                "(Some(mut l), None) => {", "(None, None) => break,", "node.next = reversed;",
                "reversed = Some(node);", "reverse(reversed)", "current = node.next.take();",
                "node.next = previous;", "previous = Some(node);"])
ROWS = {"left": 112, "right": 172, "rev": 246, "out": 316}
LABELS = {"left": "left", "right": "right", "rev": "reversed (new nodes go on the front)",
          "out": "previous: the result, in order"}
X0, STEP = 210, 66
VALUES = ["1", "4", "2", "3", "5"]


def merge_owned():
    init = {"caption": "", "kind": "step", "code": -1.0, "rows": "", "hot": "", "bad": 0.0,
            "strike": -1.0}
    for v in VALUES:
        init.update({"x" + v: 0.0, "y" + v: 0.0})
    tl = Timeline(**init)
    rows = {"left": ["1", "4"], "right": ["2", "3", "5"], "rev": [], "out": []}

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

    def move(src, dst, k, code_arm, code_link):
        v = rows[src].pop(0)
        tl.set(code=code_arm, hot=v)
        tl.wait(0.5 * k)
        # lift the node out, then slide the rest of its list along
        tl.to(0.35 * k, in_out, **{"y" + v: float(ROWS[src] - 34)})
        rows[dst].insert(0, v)
        sync(0.6 * k)
        tl.set(code=code_link)
        tl.wait(0.3 * k)
        tl.set(code=code_link + 1.0, hot="")
        tl.wait(0.3 * k)

    sync()
    tl.chapter("merge")
    tl.say("Two sorted lists. Think of two stacks of numbered cards, smallest on top.")
    tl.wait(1.4)
    tl.say("Take the smaller top card and put it on your pile. The pile ends up largest on top: "
           "reversed.")
    tl.wait(1.6)
    k = 1.4
    while rows["left"] or rows["right"]:
        if rows["left"] and rows["right"]:
            if int(rows["left"][0]) <= int(rows["right"][0]):
                if k > 1:
                    tl.say("1 <= 2, so the first arm matches. take() unhooks 1 from the rest of "
                           "left, and 1 goes on the front of reversed.")
                move("left", "rev", k, 0.0, 4.0)
            else:
                move("right", "rev", k, 1.0, 4.0)
        elif rows["right"]:
            tl.say("left is empty, so the second arm takes from right until it runs out.")
            move("right", "rev", k, 1.0, 4.0)
        else:
            move("left", "rev", k, 2.0, 4.0)
        k = 0.7
    tl.set(code=3.0)
    tl.say("Both lists are None, so the loop breaks. reversed holds 5 4 3 2 1: every node, in "
           "the opposite order.")
    tl.wait(1.8)

    tl.chapter("reverse")
    tl.set(code=6.0)
    tl.say("One pass of chapter 9's reverse turns it around, with the same three moves per node.")
    tl.wait(1.2)
    k = 1.2
    while rows["rev"]:
        move("rev", "out", k, 7.0, 8.0)
        k = 0.6
    tl.say("1 2 3 4 5. Every node is a box from the input, moved by pointer. No node was "
           "copied, and nothing was allocated.", "insight")
    tl.wait(2.0)

    tl.chapter("no reverse")
    tl.say("Now return reversed as it is, without the call to reverse.", "fail")
    tl.wait(0.8)
    rows.update(left=["1", "4"], right=["2", "3", "5"], rev=[], out=[])
    sync(0.6, code=-1.0, bad=0.0, strike=6.0)
    tl.wait(0.6)
    for src in ("left", "right", "right", "left", "right"):
        move(src, "rev", 0.4, 0.0 if src == "left" else 1.0, 4.0)
    tl.set(code=6.0)
    tl.to(0.4, bad=1.0)
    tl.say("The caller gets 5 4 3 2 1. The next round of merge_k compares front nodes, and each "
           "front is now the largest.", "fail")
    tl.wait(1.6)
    tl.say("Its output is out of order, with no error. The tests catch it: they compare against "
           "a sorted Vec.", "fail")
    tl.wait(2.2)

    def draw(p, s, total):
        t = s.t
        title_block(p, "Merging two lists with owned values only",
                    "Push each smaller front node onto a pile, then reverse the pile once.")
        layout_rows = {}
        for part in s.rows.split(";"):
            name, vals = part.split(":")
            layout_rows[name] = [v for v in vals.split(",") if v]
        for name, y in ROWS.items():
            p.text(26, y + 5, LABELS[name] if name in ("left", "right") else "", 12, MUTED, 700,
                   mono=True)
            if name in ("rev", "out"):
                p.text(26, y - 30, LABELS[name], 11, MUTED, 600)
            vals = layout_rows.get(name, [])
            for a, b in zip(vals, vals[1:]):
                ax, ay = s["x" + a], s["y" + a]
                bx, by = s["x" + b], s["y" + b]
                if abs(ay - by) < 1:
                    link_arrow(p, ax + 22, ay, bx - 24, by, TEAL, 1.8)
            if not vals:
                p.text(X0 - 22, y + 5, "None", 12, FAINT, 700, mono=True)
        for v in VALUES:
            x, y = s["x" + v], s["y" + v]
            hot = s.hot == v
            bad = s.bad > 0.5 and v in layout_rows.get("rev", [])
            fill = RUST_LT if bad else (BRASS_LT if hot else PAPER)
            edge = RUST if bad else (BRASS if hot else INK)
            p.rect(x - 22, y - 20, 44, 40, fill, edge, 8, 1.7,
                   shadow="lift" if hot else None)
            p.text(x, y + 6, v, 17, INK, 700, "middle", mono=True)
        OWNED.draw(p, 26, 352, W - 52, s, t, strike=s.strike, size=10.4, lead=13.6,
                   tint=RUST if s.kind == "fail" else TEAL)
        caption(p, tl, t, CAP)
        progress(p, tl, t, total, RAIL)

    CAP, RAIL, height = layout(352, len(OWNED), 13.6)
    return tl, draw, height


def build_merge_owned(only=None):
    tl, draw, height = merge_owned()
    return render("ch10-merge-owned.gif", tl, draw, height, only=only)


BUILDERS = {
    "merge-owned": build_merge_owned,
}
