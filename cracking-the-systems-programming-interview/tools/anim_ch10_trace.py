"""merge_two line by line, with what every variable owns or borrows
(ch10-merge-k.md, section 10.4.4).

    python3 tools/animations.py merge-trace
"""

from motion import *  # noqa: F401,F403
from motion import Timeline, render
from motion_kit import Panel, arrow, layout

CODE = Panel("src/bin/merge_k_sorted_lists_owned.rs",
             [("fn merge_two(mut left: Link, mut right: Link) -> Link {", "}")],
             ["fn merge_two(mut left: Link, mut right: Link) -> Link {",
              "let mut dummy = Box::new(Node { val: 0, next: None });",
              "let mut tail = &mut dummy;",
              "while let (Some(l), Some(r)) = (&left, &right) {",
              "if r.val < l.val {",
              "(left, right) = (right, left);",
              "let mut node = left.unwrap();",
              "left = node.next.take();",
              "tail = tail.next.insert(node);",
              "tail.next = left.or(right);",
              "dummy.next"])
BAD = ["while let (Some(l), Some(r)) = (&left, &right) {",
       "    if r.val < l.val {",
       "        (left, right) = (right, left);",
       "    }",
       "    println!(\"{}\", l.val); // l is used after the swap",
       "}"]
ROWS = {"left": 108, "right": 160, "node": 216, "out": 274}
X0, STEP = 196, 48
DUMMY_X = X0 - 6
VALUES = ["1", "4", "2", "3", "5"]
VARS = ["left", "right", "l", "r", "node", "dummy", "tail"]
TABLE_X, TABLE_Y, ROW_H = 470, 92, 29


def merge_trace():
    init = {"caption": "", "kind": "step", "code": -1.0, "mode": "ok", "rows": "", "hot_var": "",
            "error": 0.0}
    for name in VARS:
        init["v_" + name] = ""
    for v in VALUES:
        init.update({"x" + v: 0.0, "y" + v: 0.0, "a" + v: 0.0})
    tl = Timeline(**init)
    rows = {"left": ["1", "4"], "right": ["2", "3", "5"], "node": [], "out": []}

    def chain(vals):
        return " -> ".join(vals) if vals else "None"

    def targets():
        moves = {}
        for name, vals in rows.items():
            for k, v in enumerate(vals):
                x0 = DUMMY_X + STEP + 4 if name == "out" else X0
                moves["x" + v] = float(x0 + k * STEP)
                moves["y" + v] = float(ROWS[name])
                moves["a" + v] = 1.0
        return moves

    def show(dur=0.5, **extra):
        tl.set(rows=";".join("%s:%s" % (n, ",".join(v)) for n, v in rows.items()), **extra)
        tl.to(dur, in_out, **targets())

    def step(code, say, kind="step", hold=1.0, var="", dur=0.5, **vars):
        tl.say(say, kind)
        show(dur, code=float(code), hot_var=var, **{"v_" + k: v for k, v in vars.items()})
        tl.wait(hold)

    def owns():
        return {"left": "owns " + chain(rows["left"]) if rows["left"] else "None",
                "right": "owns " + chain(rows["right"]) if rows["right"] else "None",
                "dummy": "owns dummy -> " + chain(rows["out"]) if rows["out"] else "owns dummy"}

    tl.chapter("set up")
    show(0.01, code=-1.0)
    step(0, "merge_two takes both lists by value. left owns 1 -> 4, and right owns 2 -> 3 -> 5.",
         var="left", hold=1.6, **owns())
    step(1, "dummy owns a heap node with no value of its own. The output will hang off its next "
            "field.", var="dummy", hold=1.6, **owns())
    step(2, "tail is a &mut borrow of dummy. It is the only mutable reference in the function, "
            "and it always points at the last node.", var="tail", hold=2.0,
         tail="&mut the last node: dummy", **owns())

    tail_on = "dummy"
    for n in range(10):
        tl.chapter("pass %d" % (n + 1) if rows["left"] and rows["right"] else "the end")
        slow = n == 0 or n == 1
        k = 1.0 if slow else 0.55
        if not (rows["left"] and rows["right"]):
            step(3, "left is None, so the pattern does not match and the loop ends. l and r are "
                    "not bound.", var="left", hold=1.6, l="", r="", node="", **owns())
            break
        fl, fr = rows["left"][0], rows["right"][0]
        say = ("while let borrows both lists with &: l points at %s, the front of left, and r at %s. "
               "Neither can change through these borrows." % (fl, fr)) if n == 0 else \
            "Both lists still have a node. l borrows %s and r borrows %s." % (fl, fr)
        step(3, say, var="l", hold=1.8 * k, l="& front of left: %s" % fl,
             r="& front of right: %s" % fr, **owns())
        if int(fr) < int(fl):
            step(4, "r.val < l.val: %s < %s. This is the last use of l and r, so both shared "
                    "borrows end here." % (fr, fl), var="r", hold=1.8 * k, l="", r="", **owns())
            rows["left"], rows["right"] = rows["right"], rows["left"]
            step(5, "With the borrows gone, the swap may move left and right. The two lists trade "
                    "owners. No node moves in memory.", var="left", hold=2.0 * k, dur=0.7,
                 **owns())
        else:
            step(4, "r.val < l.val is %s < %s: false. left already holds the smaller front. The "
                    "borrows l and r end here." % (fr, fl), var="l", hold=1.6 * k, l="", r="",
                 **owns())
        moved = rows["left"]
        rows["node"], rows["left"] = moved, []
        step(6, "left.unwrap() moves the whole list out of left. node owns %s now, and left is "
                "moved-from: reading it here would not compile." % chain(moved), var="node",
             hold=2.2 * k, dur=0.6, node="owns " + chain(moved),
             left="moved out (unusable)")
        rest = rows["node"][1:]
        rows["node"], rows["left"] = rows["node"][:1], rest
        step(7, "node.next.take() cuts node %s off, and the rest, %s, goes back into left. left "
                "is usable again." % (rows["node"][0], chain(rest)), var="left", hold=1.8 * k,
             dur=0.6, node="owns %s alone" % rows["node"][0], **owns())
        v = rows["node"][0]
        rows["node"], rows["out"] = [], rows["out"] + [v]
        tail_on = v
        step(8, "insert(node) moves node into %s.next, so dummy's chain owns it. node is moved "
                "out. tail moves on to node %s." % ("dummy" if len(rows["out"]) == 1 else
                                                     rows["out"][-2], v),
             var="tail", hold=2.0 * k, dur=0.6, node="moved out",
             tail="&mut the last node: %s" % v, **owns())
        tl.set(v_node="")

    rest = rows["left"] or rows["right"]
    step(9, "left.or(right) moves out whichever list is Some: %s. tail.next takes it whole, so "
            "no loop over the rest." % chain(rest), var="tail", hold=1.6,
         **{"left": "moved into or()", "right": "moved into or()"})
    rows["out"] += rest
    rows["left"], rows["right"] = [], []
    show(0.7, v_dummy="owns dummy -> " + chain(rows["out"]), hot_var="dummy")
    tl.wait(1.2)
    step(10, "dummy.next moves the merged list out of dummy. The dummy node is freed when the "
             "function returns. tail's borrow ended at its last use.", var="dummy", hold=1.6,
         tail="", dummy="returns " + chain(rows["out"]))
    tl.say("One &mut for the whole merge, and every node moved, never copied.", "insight")
    tl.wait(2.0)

    tl.chapter("l after the swap")
    tl.set(mode="bad", code=4.0, error=0.0)
    tl.say("Now read l after the swap, as in this version of the loop.", "fail")
    tl.wait(1.6)
    tl.set(code=2.0)
    tl.say("The swap moves left while l still borrows its front node, because l is used on the "
           "next line.", "fail")
    tl.wait(1.8)
    tl.to(0.4, error=1.0)
    tl.say("rustc rejects it twice: E0506, cannot assign to left because it is borrowed, and "
           "E0505, cannot move out of left. Use l and r only in the comparison.", "fail")
    tl.wait(2.4)

    def draw(p, s, total):
        t = s.t
        title_block(p, "merge_two, line by line",
                    "Who owns each node, and who borrows it, after every line.")
        layout_rows = {}
        for part in s.rows.split(";"):
            if ":" in part:
                name, vals = part.split(":")
                layout_rows[name] = [v for v in vals.split(",") if v]
        labels = {"left": "left", "right": "right", "node": "node", "out": "output"}
        for name, y in ROWS.items():
            hot = s.hot_var == name or (name == "out" and s.hot_var == "dummy")
            p.text(26, y + 5, labels[name], 12.5, BRASS if hot else INK, 700, mono=True)
            vals = layout_rows.get(name, [])
            for a, b in zip(vals, vals[1:]):
                ax, ay, bx, by = s["x" + a], s["y" + a], s["x" + b], s["y" + b]
                if abs(ay - by) < 1 and abs(bx - ax - STEP) < 1:
                    arrow(p, ax + 18, ay, bx - 18, by, TEAL if name == "out" else MUTED, 1.6,
                          head=7)
            if not vals and name in ("left", "right"):
                moved = s["v_" + name].startswith("moved")
                p.text(X0 - 16, y + 5, "moved out" if moved else "None", 11,
                       RUST if moved else FAINT, 700, mono=True)
        # dummy and the output chain
        oy = ROWS["out"]
        p.rect(DUMMY_X - 20, oy - 16, 40, 32, STAGE, FAINT, 6, 1.2, dash="4 3")
        p.text(DUMMY_X, oy + 4, "dummy", 8.5, MUTED, 700, "middle", mono=True)
        out = layout_rows.get("out", [])
        if out:
            arrow(p, DUMMY_X + 21, oy, DUMMY_X + STEP + 4 - 18, oy, TEAL, 1.6, head=7)
        for v in VALUES:
            a = s["a" + v]
            if a <= 0.01:
                continue
            x, y = s["x" + v], s["y" + v]
            in_node = v in layout_rows.get("node", [])
            fill = BRASS_LT if in_node else (TEAL_LT if v in out else PAPER)
            edge = BRASS if in_node else (TEAL if v in out else INK)
            p.rect(x - 17, y - 16, 34, 32, fill, edge, 6, 1.6, opacity=a)
            p.text(x, y + 5, v, 14, INK, 700, "middle", mono=True, opacity=a)
        # shared borrows l and r, and the &mut tail
        for name, row, color in (("l", "left", TEAL), ("r", "right", TEAL)):
            if s["v_" + name] and layout_rows.get(row):
                fx = s["x" + layout_rows[row][0]]
                fy = s["y" + layout_rows[row][0]]
                p.text(fx - 52, fy + 5, name + " (&)", 11, color, 700, "end", mono=True)
                arrow(p, fx - 48, fy, fx - 20, fy, color, 1.6, head=7, dash="3 2")
        if s.v_tail:
            last = s.v_tail.rsplit(": ", 1)[-1]
            tx = s["x" + last] if last in VALUES else DUMMY_X
            arrow(p, tx, oy + 38, tx, oy + 18, RUST, 1.8, head=7)
            p.text(tx, oy + 50, "tail (&mut)", 10, RUST, 700, "middle", mono=True)
        # the ownership table
        p.text(TABLE_X, TABLE_Y - 10, "variable", 10, MUTED, 700)
        p.text(TABLE_X + 66, TABLE_Y - 10, "owns or borrows", 10, MUTED, 700)
        for i, name in enumerate(VARS):
            y = TABLE_Y + i * ROW_H
            hot = s.hot_var == name
            p.rect(TABLE_X - 6, y - 2, 330, ROW_H - 4, BRASS_LT if hot else STAGE,
                   BRASS if hot else LINE, 5, 1.2)
            p.text(TABLE_X + 2, y + 16, name, 11.5, INK, 700, mono=True)
            text = s["v_" + name] or ("not in scope" if name in ("l", "r", "node")
                                      else "")
            color = RUST if "moved" in text else (TEAL if text.startswith("&") else
                                                  (FAINT if text == "not in scope" else INK))
            p.text(TABLE_X + 66, y + 16, text, 10, color, 600, mono=True)
        if s.mode == "bad":
            code_panel(p, 26, 326, W - 52, "a loop that reads l after the swap", BAD, s.code,
                       size=10.6, lead=15.0, tint=RUST)
            if s.error > 0.01:
                chip(p, W / 2, 470, "error[E0506]: cannot assign to `left` because it is "
                     "borrowed", RUST, RUST_LT, 11, opacity=clamp(s.error))
                chip(p, W / 2, 500, "error[E0505]: cannot move out of `left` because it is "
                     "borrowed", RUST, RUST_LT, 11, opacity=clamp(s.error))
        else:
            CODE.draw(p, 26, 326, W - 52, "merge_two", s, t, reveal=False, size=10.4, lead=13.6)
        caption(p, tl, t, CAP)
        progress(p, tl, t, total, RAIL)

    CAP, RAIL, height = layout(326, len(CODE), 13.6)
    return tl, draw, height


def build_merge_trace(only=None):
    tl, draw, height = merge_trace()
    return render("ch10-merge-trace.gif", tl, draw, height, only=only)


BUILDERS = {
    "merge-trace": build_merge_trace,
}
