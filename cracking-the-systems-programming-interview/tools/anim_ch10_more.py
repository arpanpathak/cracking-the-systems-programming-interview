"""Merging with owned values only (ch10-merge-k.md, section 10.4.4).

    python3 tools/animations.py merge-owned
"""

from motion import *  # noqa: F401,F403
from motion import Timeline, render
from motion_kit import Panels, arrow, layout

OWNED = Panels("src/bin/merge_k_sorted_lists_owned.rs",
               [[("fn goes_first(x: &Link, y: &Link) -> bool {", "}"),
                 ("fn merge_two(mut a: Link, mut b: Link) -> Link {", "}")],
                [("fn reverse(mut list: Link) -> Link {", "}")]],
               ["goes_first and merge_two", "reverse"],
               ["if goes_first(&b, &a) {", "(a, b) = (b, a);",
                "let Some(mut node) = a else { break };", "a = node.next;", "node.next = pile;",
                "pile = Some(node);", "reverse(pile)", "list = node.next;",
                "node.next = reversed;", "reversed = Some(node);"])
ROWS = {"a": 116, "b": 176, "pile": 252, "out": 322}
LABELS = {"a": "a", "b": "b", "pile": "pile (largest on top)", "out": "the result, in order"}
X0, STEP = 210, 66
VALUES = ["1", "4", "2", "3", "5"]


def merge_owned():
    init = {"caption": "", "kind": "step", "code": -1.0, "strike": -1.0, "rows": "", "hot": "",
            "bad": 0.0}
    for v in VALUES:
        init.update({"x" + v: 0.0, "y" + v: 0.0})
    tl = Timeline(**init)
    rows = {"a": ["1", "4"], "b": ["2", "3", "5"], "pile": [], "out": []}

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

    def take(src, dst, k, codes):
        """Lift the front node of `src`, and put it on the front of `dst`."""
        v = rows[src].pop(0)
        tl.set(code=codes[0], hot=v)
        tl.wait(0.4 * k)
        tl.to(0.3 * k, in_out, **{"y" + v: float(ROWS[src] - 32)})
        tl.set(code=codes[1])
        rows[dst].insert(0, v)
        sync(0.6 * k)
        tl.set(code=codes[2])
        tl.wait(0.25 * k)
        tl.set(code=codes[3], hot="")
        tl.wait(0.25 * k)

    def front(name):
        return int(rows[name][0]) if rows[name] else None

    def merge(k, notes):
        step = 0
        while rows["a"] or rows["b"]:
            fa, fb = front("a"), front("b")
            tl.set(code=0.0)
            tl.wait(0.35 * k)
            if fb is not None and (fa is None or fb < fa):
                if ("swap", step) in notes:
                    tl.say(*notes[("swap", step)])
                rows["a"], rows["b"] = rows["b"], rows["a"]
                tl.set(code=1.0)
                sync(0.7 * k)
                tl.wait(0.3 * k)
            if ("take", step) in notes:
                tl.say(*notes[("take", step)])
            take("a", "pile", k, (2.0, 3.0, 4.0, 5.0))
            step += 1
            k = max(0.6, k * 0.8)
        tl.set(code=2.0)
        tl.wait(0.5)

    sync()
    tl.chapter("merge")
    tl.say("Two sorted lists, a and b. Think of two stacks of numbered cards, smallest on top.")
    tl.wait(1.4)
    tl.say("The rule: a always holds the card that comes next. If b is ahead, the two lists trade "
           "places.")
    tl.wait(1.6)
    merge(1.4, {
        ("take", 0): ("1 < 2, so a keeps its place. Its front node moves onto the pile: three "
                      "moves of owned values, no reference into a list.",),
        ("swap", 1): ("Now b's front, 2, is smaller than 4. (a, b) = (b, a) swaps the two lists "
                      "as values.",),
        ("swap", 4): ("a is empty and b is not, so they swap once more. Then 5 goes on the "
                      "pile.",),
    })
    tl.say("Both lists are empty, so let-else breaks the loop. The pile reads 5 4 3 2 1: every "
           "node, largest on top.")
    tl.wait(1.8)

    tl.chapter("reverse")
    tl.set(code=6.0)
    tl.say("One pass of chapter 9's reverse turns the pile over, with the same three moves per "
           "node.")
    tl.wait(1.2)
    k = 1.2
    while rows["pile"]:
        take("pile", "out", k, (7.0, 7.0, 8.0, 9.0))
        k = 0.6
    tl.say("1 2 3 4 5. Each node moved twice and was never copied, and the merge allocated "
           "nothing.", "insight")
    tl.wait(2.2)

    tl.chapter("no reverse")
    tl.say("Now return the pile as it is, without the call to reverse.", "fail")
    tl.wait(0.8)
    rows.update(a=["1", "4"], b=["2", "3", "5"], pile=[], out=[])
    sync(0.6, code=-1.0, bad=0.0, strike=6.0)
    tl.wait(0.6)
    merge(0.45, {})
    tl.set(code=6.0)
    tl.to(0.4, bad=1.0)
    tl.say("The caller gets 5 4 3 2 1. The next round of merge_k picks by the front node, and "
           "each front is now the largest.", "fail")
    tl.wait(1.6)
    tl.say("Its output is out of order, with no error. The tests catch it: they compare with a "
           "sorted Vec.", "fail")
    tl.wait(2.2)

    def draw(p, s, total):
        t = s.t
        title_block(p, "Merging two lists by moving owned nodes",
                    "Keep the next node at the front of a, move it to a pile, then reverse.")
        layout_rows = {}
        for part in s.rows.split(";"):
            name, vals = part.split(":")
            layout_rows[name] = [v for v in vals.split(",") if v]
        for name, y in ROWS.items():
            if name in ("a", "b"):
                p.text(26, y + 6, LABELS[name], 15, INK, 700, mono=True)
            else:
                p.text(26, y - 30, LABELS[name], 11, MUTED, 600)
            vals = layout_rows.get(name, [])
            for a, b in zip(vals, vals[1:]):
                ax, ay = s["x" + a], s["y" + a]
                bx, by = s["x" + b], s["y" + b]
                if abs(ay - by) < 1:
                    arrow(p, ax + 25, ay, bx - 25, by, TEAL, 1.8, head=8)
            if not vals:
                p.text(X0 - 22, y + 5, "None", 12, FAINT, 700, mono=True)
        for v in VALUES:
            x, y = s["x" + v], s["y" + v]
            hot = s.hot == v
            bad = s.bad > 0.5 and v in layout_rows.get("pile", [])
            fill = RUST_LT if bad else (BRASS_LT if hot else PAPER)
            edge = RUST if bad else (BRASS if hot else INK)
            p.rect(x - 22, y - 20, 44, 40, fill, edge, 8, 1.7, shadow="lift" if hot else None)
            p.text(x, y + 6, v, 17, INK, 700, "middle", mono=True)
        OWNED.draw(p, 26, 356, W - 52, s, t, strike=s.strike, size=10.4, lead=13.6,
                   tint=RUST if s.kind == "fail" else TEAL)
        caption(p, tl, t, CAP)
        progress(p, tl, t, total, RAIL)

    CAP, RAIL, height = layout(356, len(OWNED), 13.6)
    return tl, draw, height


def build_merge_owned(only=None):
    tl, draw, height = merge_owned()
    return render("ch10-merge-owned.gif", tl, draw, height, only=only)


BUILDERS = {
    "merge-owned": build_merge_owned,
}
