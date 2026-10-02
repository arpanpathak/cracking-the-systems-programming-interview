"""The chapter 9 animation (ch09-linked-lists.md), drawn with `motion`.

    python3 tools/animations.py reverse
"""

from motion import (BRASS, BRASS_LT, FAINT, INK, LINE, MUTED, PAPER, RUST, RUST_LT, TEAL,
                    TEAL_LT, W, caption, code_panel, progress, render, title_block)
from motion_kit import NAVY, arrow, layout, line_of, play, source

XS = [170, 330, 490, 650]
NODE_Y = 170


def reverse():
    code = source("src/problems/linked_list.rs", "pub fn reverse_list", "}")
    take = line_of(code, "current = node.next.take()")
    flip = line_of(code, "node.next = previous")
    adv = line_of(code, "previous = Some(node)")
    loop = line_of(code, "while let Some(mut node)")
    ret = line_of(code, "    previous") if any(l.strip() == "previous" for l in code) else len(code) - 2
    # link{k}: "r" forward to k+1, "l" back to k-1, "none" (points at None), "cut" (moved out)
    links = {k: ("r" if k < 3 else "none") for k in range(4)}

    def L():
        return {"link%d" % k: v for k, v in links.items()}

    steps = [dict(chapter="loop", say="The list is 1 → 2 → 3 → 4. previous starts as None, and "
                  "current owns the whole list.", prev=-1.0, cur=0.0, nodev=-1.0, code=-1.0, **L())]
    for k in range(4):
        steps.append(dict(say="while let Some(mut node) = current moves node %d out of current." % (k + 1),
                          nodev=float(k), code=float(loop)))
        links[k] = "cut"
        steps.append(dict(say="node.next.take() moves the rest of the list into current, and leaves None in "
                          "node.next.", cur=float(k + 1) if k < 3 else 4.0, code=float(take), **L()))
        links[k] = "l" if k > 0 else "none"
        steps.append(dict(say="node.next = previous points node %d back at %s." % (
            k + 1, "None" if k == 0 else "node %d" % k), code=float(flip), **L()))
        steps.append(dict(say="previous = Some(node): node %d is the new front of the reversed part." % (k + 1),
                          prev=float(k), nodev=-1.0, code=float(adv), hold=0.2))
    steps.append(dict(say="current is None, so the loop ends. previous owns 4 → 3 → 2 → 1. No node "
                      "was copied or allocated.", kind="insight", code=-1.0, hold=1.6))
    links = {k: ("r" if k < 3 else "none") for k in range(4)}
    steps.append(dict(chapter="flip first", say="Now suppose the loop flipped the link before taking the rest.",
                      kind="fail", prev=-1.0, cur=0.0, nodev=0.0, code=float(flip), **L()))
    links[0] = "none"
    steps.append(dict(say="node.next = previous overwrites the only link to 2 → 3 → 4. Nothing owns "
                      "those nodes now, so they are dropped.", kind="fail", lost=1.0, **L(), hold=2.2))
    tl = play(steps, dict(prev=-1.0, cur=0.0, nodev=-1.0, code=-1.0, lost=0.0,
                          **{"link%d" % k: ("r" if k < 3 else "none") for k in range(4)}))

    def draw(p, s, total):
        t = s.t
        half_w = 34
        for k in range(4):
            x = XS[k]
            lost = s.lost > 0.5 and k > 0
            in_hand = abs(s.nodev - k) < 0.5
            done = s.prev >= k - 0.01 and s.prev >= 0 and s.lost < 0.5
            fill = RUST_LT if lost else (BRASS_LT if in_hand else (TEAL_LT if done else PAPER))
            edge_c = RUST if lost else (BRASS if in_hand else (TEAL if done else NAVY))
            p.rect(x - half_w, NODE_Y - 24, 2 * half_w, 48, fill, edge_c, 10, 1.8)
            p.text(x, NODE_Y + 8, str(k + 1), 22, INK, 700, "middle", mono=True)
            link = s["link%d" % k]
            if link == "r":
                arrow(p, x + half_w + 4, NODE_Y - 8, XS[k + 1] - half_w - 4, NODE_Y - 8, MUTED)
            elif link == "l":
                arrow(p, x - half_w - 4, NODE_Y + 8, XS[k - 1] + half_w + 4, NODE_Y + 8, TEAL)
            elif link == "none":
                if k == 0 and s.lost < 0.5:
                    arrow(p, x - half_w - 4, NODE_Y + 8, x - half_w - 34, NODE_Y + 8, TEAL)
                    p.text(x - half_w - 40, NODE_Y + 13, "None", 12, TEAL, 600, "end", mono=True)
                else:
                    arrow(p, x + half_w + 4, NODE_Y - 8, x + half_w + 34, NODE_Y - 8, FAINT)
                    p.text(x + half_w + 40, NODE_Y - 3, "None", 12, FAINT, 600, mono=True)
        if s.lost > 0.5:
            p.text((XS[1] + XS[3]) / 2, NODE_Y - 52, "nothing owns 2 -> 3 -> 4", 13, RUST, 700,
                   "middle")

        def pointer(name, at, color, y):
            """A variable as a tag under the node it owns, or `= None`."""
            if at < -0.5 or at > 3.5:
                p.text(40, y + 4, "%s = None" % name, 13, color, 700, mono=True)
                return
            x = XS[0] + (XS[1] - XS[0]) * at
            arrow(p, x, y - 14, x, NODE_Y + 30, color, 1.8, head=9)
            p.text(x, y + 4, name, 13, color, 700, "middle", mono=True)
        pointer("previous", s.prev, TEAL, NODE_Y + 74)
        pointer("current", s.cur, NAVY, NODE_Y + 122)
        if s.nodev >= 0:
            x = XS[0] + (XS[1] - XS[0]) * s.nodev
            p.text(x, NODE_Y - 62, "node", 13, BRASS, 700, "middle", mono=True)
            arrow(p, x, NODE_Y - 56, x, NODE_Y - 30, BRASS, 1.8, head=9)
        title_block(p, "Reversing a linked list in place",
                    "Each step moves one node from current to the front of previous.")
        code_panel(p, 26, CODE_Y, W - 52, "reverse_list", code, s.code, size=11.0, lead=15.6,
                   reveal=tl.reached("code", t), tint=RUST if s.lost > 0.5 else TEAL)
        caption(p, tl, t, cap_y)
        progress(p, tl, t, total, rail_y)

    CODE_Y = 342
    cap_y, rail_y, height = layout(CODE_Y, len(code))
    return tl, draw, height


def build(name, fn, extra=()):
    def run(only=None):
        tl, draw, height = fn()
        return render(name, tl, draw, height, only=only, extra_colors=extra)
    return run


BUILDERS = {
    "reverse": build("ch04-reverse.gif", reverse, (NAVY,)),
}
