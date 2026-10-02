"""The merge-k chapter animations (ch10-merge-k.md), drawn with `motion`.

    python3 tools/animations.py merge-two merge-rounds
"""

from motion_kit import Panel, layout
from motion import *  # noqa: F401,F403
from motion import Timeline, render

MERGE_TWO = Panel("src/bin/merge_k_sorted_list_zero_copy.rs",
                  [("let mut dummy = Box::new(Node { val: 0, next: None });", "dummy.next")],
                  ["while let (Some(left_head), Some(right_head)) = (&left, &right) {",
                   "let smaller = if left_head.val <= right_head.val {",
                   "let mut node = smaller.take().unwrap();",
                   "*smaller = node.next.take();",
                   "tail = tail.next.insert(node);",
                   "tail.next = if left.is_some() { left } else { right };",
                   "dummy.next"])
MERGE_K = Panel("src/bin/merge_k_sorted_list_zero_copy.rs",
                [("while gap < list_count {", "}")],
                ["while gap < list_count {", "let left = lists[index].take();",
                 "let right = lists[index + gap].take();", "lists[index] = merge_two(left, right);",
                 "index += gap * 2;", "gap *= 2;"])
MERGE_GAP = Panel("src/bin/merge_k_sorted_lists_owned.rs",
                  [("while gap < size {", "}")],
                  ["while gap < size {", "lists[i] = merge_two(", "lists[i] = merge_two(",
                   "lists[i] = merge_two(", "i += gap * 2;", "gap *= 2;"])

# ------------------------------------------------- 10.1: merging two lists

ROWS = {"left": 112, "right": 176, "out": 262}
X0, STEP = 210, 66


def chain(p, values, y, color, fill, x0=X0, faded=()):
    for k, v in enumerate(values):
        x = x0 + k * STEP
        a = 0.3 if k in faded else 1.0
        p.rect(x - 22, y - 16, 44, 32, fill, color, 6, 1.4, opacity=a)
        p.text(x, y + 5, str(v), 13, INK, 700, "middle", mono=True, opacity=a)
        if k + 1 < len(values):
            p.line(x + 22, y, x + STEP - 26, y, color, 1.4, opacity=a)
            p.path("M %s %s l -6 -4 l 0 8 z" % (x + STEP - 22, y), fill=color, stroke="none",
                   opacity=a)


def merge_two():
    tl = Timeline(caption="", kind="step", code=-1.0, strike=-1.0, left="1,4,5", right="1,3,4",
                  out="", ring="", fly_u=0.0, fly_a=0.0, fly_from="left", fly_val="",
                  lost=0.0)

    def parse(text):
        return [v for v in text.split(",") if v]

    def step(side, k=1.0, first=False):
        left, right = parse(tl._at("left", tl.now)), parse(tl._at("right", tl.now))
        tl.set(code=0.0, ring="both")
        tl.wait(0.4 * k)
        tl.to(0.2, code=1.0)
        tl.set(ring=side)
        tl.wait(0.5 * k)
        value = (left if side == "left" else right)[0]
        tl.to(0.2, code=2.0)
        tl.set(fly_from=side, fly_val=value, fly_u=0.0)
        rest = ",".join((left if side == "left" else right)[1:])
        tl.set(**{side: rest}, code=3.0)
        tl.to(0.1, fly_a=1.0)
        tl.to(0.8 * k, in_out, fly_u=1.0)
        tl.to(0.1, fly_a=0.0)
        out = parse(tl._at("out", tl.now)) + [value]
        tl.set(out=",".join(out), ring="", code=4.0)
        tl.wait(0.3 * k)

    def run(fail):
        tag = "fail" if fail else "step"
        tl.say("Compare the two fronts. Both are 1, and <= prefers left, so left's node moves.", tag)
        step("left", 1.2, True)
        tl.say("The node is detached from left and linked after tail. tail moves onto it. Nothing "
               "is copied.", tag)
        tl.wait(0.6)
        tl.say("Then 1 from right, 3 from right, 4 from left, and 4 from right.", tag)
        for side in ("right", "right", "left", "right"):
            step(side, 0.55)
        tl.say("right is empty, so the while let stops. left still holds 5.", tag)
        tl.set(code=0.0)
        tl.wait(1.0)

    tl.chapter("merge")
    tl.say("Two sorted lists, 1 4 5 and 1 3 4. The output starts at a dummy node, and tail points "
           "at it.")
    tl.wait(0.6)
    run(False)
    tl.say("One link attaches whatever is left, whole. The merge moved six nodes and allocated "
           "only the dummy.", "insight")
    tl.to(0.3, code=5.0)
    tl.set(fly_from="left", fly_val="5", fly_u=0.0, left="")
    tl.to(0.1, fly_a=1.0)
    tl.to(0.7, in_out, fly_u=1.0)
    tl.to(0.1, fly_a=0.0)
    tl.set(out="1,1,3,4,4,5", code=6.0)
    tl.wait(1.4)

    tl.chapter("no attach")
    tl.say("Now delete the line that attaches the rest.", "fail")
    tl.set(left="1,4,5", right="1,3,4", out="", strike=5.0, code=-1.0)
    tl.wait(0.4)
    run(True)
    tl.say("The function returns dummy.next. left goes out of scope, and node 5 is freed. The "
           "output has five nodes.", "fail")
    tl.to(0.5, lost=1.0, code=6.0)
    tl.wait(1.6)

    def draw(p, s, total):
        t = s.t
        title_block(p, "Merging two sorted lists",
                    "Move the smaller front node to the tail. No value is copied.")
        for side in ("left", "right"):
            y = ROWS[side]
            p.text(40, y + 5, side, 12, MUTED, 700)
            values = [v for v in s[side].split(",") if v]
            chain(p, values, y, TEAL if side == "left" else NIGHT,
                  TEAL_LT if side == "left" else NIGHT_LT,
                  faded=(0,) if s.lost > 0.5 and side == "left" else ())
            if values and (s.ring == "both" or s.ring == side):
                focus(p, X0 - 22, y - 16, 44, 32, 1.0, BRASS, pad=5)
            if s.lost > 0.5 and side == "left" and values:
                p.text(X0, y + 34, "freed", 10.5, RUST, 700, "middle")
        y = ROWS["out"]
        p.text(40, y + 5, "output", 12, MUTED, 700)
        p.rect(X0 - 22 - STEP, y - 16, 44, 32, STAGE, FAINT, 6, 1.2, dash="4 3")
        p.text(X0 - STEP, y + 5, "dummy", 9.5, MUTED, 700, "middle")
        out = [v for v in s.out.split(",") if v]
        if out:
            p.line(X0 - STEP + 22, y, X0 - 26, y, BRASS, 1.4)
        chain(p, out, y, BRASS, BRASS_LT)
        tail_x = X0 + (len(out) - 1) * STEP if out else X0 - STEP
        p.text(tail_x, y + 34, "tail", 11, BRASS, 700, "middle", mono=True)
        if s.fly_a > 0.01:
            a = (X0, ROWS[s.fly_from])
            b = (X0 + len(out) * STEP, y)
            x, yy = bezier(a, ((a[0] + b[0]) / 2, ROWS["right"] + 40), b, s.fly_u)
            p.rect(x - 22, yy - 16, 44, 32, BRASS_LT, BRASS, 6, 1.6, opacity=s.fly_a)
            p.text(x, yy + 5, s.fly_val, 13, INK, 700, "middle", mono=True, opacity=s.fly_a)

        MERGE_TWO.draw(p, 26, 316, W - 52, "merge_two", s, t, strike=s.strike, size=10.4,
                       lead=14.0)
        caption(p, tl, t, CAP)
        progress(p, tl, t, total, RAIL)

    CAP, RAIL, height = layout(316, len(MERGE_TWO), 14.0)
    return tl, draw, height


# ------------------------------------------------- 10.2: rounds versus one at a time

BAR_X0, BAR_GAP, BAR_Y, UNIT = 70, 90, 250, 7


def merge_rounds(panel=MERGE_K):
    tl = Timeline(caption="", kind="step", code=-1.0, mode="pairwise",
                  sizes="3,3,3,3,3,3,3,3", moves=0.0, arc_u=0.0, arc_a=0.0, arc_from=1,
                  arc_to=0, gap=0, ring=-1)

    def merge(into, frm, k=1.0):
        sizes = [int(v) for v in tl._at("sizes", tl.now).split(",")]
        tl.set(arc_from=frm, arc_to=into, arc_u=0.0, ring=into)
        tl.to(0.1, arc_a=1.0)
        tl.to(0.7 * k, in_out, arc_u=1.0)
        tl.to(0.1, arc_a=0.0)
        moved = sizes[into] + sizes[frm]
        sizes[into], sizes[frm] = moved, 0
        tl.set(sizes=",".join(map(str, sizes)))
        tl.to(0.3 * k, moves=tl._at("moves", tl.now) + moved)
        tl.set(ring=-1)

    tl.chapter("pairwise")
    tl.say("Eight sorted lists of three nodes. Pairwise rounds merge lists that are gap apart, into "
           "the left one.")
    tl.set(code=0.0, gap=1)
    tl.wait(0.6)
    tl.say("Gap 1: four merges of 3 + 3 nodes. Every node moves once in this round: 24 moves.")
    for i in (0, 2, 4, 6):
        tl.set(code=3.0)
        merge(i, i + 1, 0.8 if i == 0 else 0.5)
    tl.set(code=5.0)
    tl.say("Gap 2: two merges of 6 + 6. Again 24 moves.")
    tl.set(gap=2)
    for i in (0, 4):
        tl.set(code=3.0)
        merge(i, i + 2, 0.6)
    tl.set(code=5.0)
    tl.say("Gap 4: one merge of 12 + 12. lists[0] holds all 24 nodes after 72 moves.")
    tl.set(gap=4)
    tl.set(code=3.0)
    merge(0, 4, 0.8)
    tl.say("Three rounds, log2 of 8, and each node moved once per round: N log k.", "insight")
    tl.wait(1.2)

    tl.chapter("one at a time")
    tl.say("Now merge one list at a time into a growing result.", "fail")
    tl.set(mode="single", sizes="3,3,3,3,3,3,3,3", moves=0.0, code=-1.0, gap=0)
    tl.wait(0.4)
    for j in range(1, 8):
        if j == 1:
            tl.say("Each merge walks the whole result so far, and the result keeps growing.", "fail")
        merge(0, j, 0.7 if j == 1 else 0.45)
    tl.say("105 moves for the same 24 nodes. The first nodes moved seven times: k N.", "fail")
    tl.wait(1.6)

    def draw(p, s, total):
        t = s.t
        title_block(p, "Merging k lists: rounds or one at a time",
                    "Count how many times a node moves. Each merge of a and b nodes moves a + b.")
        scoreboard(p, [("node moves", int(round(s.moves)),
                        RUST if s.mode == "single" else TEAL)])
        if s.mode == "pairwise" and s.gap:
            p.text(26, 92, "gap = %d" % int(s.gap), 13, INK, 700, mono=True)
        sizes = [int(v) for v in s.sizes.split(",")]
        for i, n in enumerate(sizes):
            x = BAR_X0 + i * BAR_GAP
            p.text(x + 20, BAR_Y + 22, "lists[%d]" % i, 10.5, MUTED, 600, "middle", mono=True)
            if n:
                h = n * UNIT
                p.rect(x, BAR_Y - h, 40, h, TEAL_LT if s.mode == "pairwise" else BRASS_LT,
                       TEAL if s.mode == "pairwise" else BRASS, 4, 1.3)
                p.text(x + 20, BAR_Y - h - 8, str(n), 11, INK, 700, "middle", mono=True)
            else:
                p.rect(x, BAR_Y - 2, 40, 2, LINE, "none", 1)
            if int(s.ring) == i:
                focus(p, x, BAR_Y - max(n, 3) * UNIT, 40, max(n, 3) * UNIT, 1.0, BRASS, pad=4)
        if s.arc_a > 0.01:
            a = (BAR_X0 + int(s.arc_from) * BAR_GAP + 20, BAR_Y - 30)
            b = (BAR_X0 + int(s.arc_to) * BAR_GAP + 20, BAR_Y - 30)
            x, y = bezier(a, ((a[0] + b[0]) / 2, 74), b, s.arc_u)
            pill(p, x, y, "merge", BRASS, BRASS_LT, 10, opacity=s.arc_a, shadow=None)

        panel.draw(p, 26, 290, W - 52, "merge_k: pairwise rounds", s, t, size=10.6,
                     lead=14.5, tint=TEAL, opacity=1.0 if s.mode == "pairwise" else 0.4)
        caption(p, tl, t, CAP)
        progress(p, tl, t, total, RAIL)

    CAP, RAIL, height = layout(290, len(panel), 14.5)
    return tl, draw, height


def build_merge_two(only=None):
    tl, draw, height = merge_two()
    return render("ch10-merge-two.gif", tl, draw, height, only=only)


def build_merge_rounds(only=None):
    tl, draw, height = merge_rounds()
    return render("ch10-merge-rounds.gif", tl, draw, height, only=only)


def build_merge_gap(only=None):
    tl, draw, height = merge_rounds(MERGE_GAP)
    return render("ch10-merge-gap.gif", tl, draw, height, only=only)


BUILDERS = {
    "merge-two": build_merge_two,
    "merge-rounds": build_merge_rounds,
    "merge-gap": build_merge_gap,
}
