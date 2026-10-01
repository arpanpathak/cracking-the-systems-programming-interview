"""The chapter 6 animations (ch06-dynamic-programming.md), drawn with `motion`.

    python3 tools/animations.py coin-change subsets
"""

from motion import (BRASS, BRASS_LT, FAINT, INK, LINE, MUTED, PAPER, RUST, RUST_LT, TEAL,
                    TEAL_LT, W, caption, code_panel, progress, render, title_block)
from motion_kit import NAVY, cells, edge, layout, line_of, node, play, row_xs, source

INF = "∞"


def furniture(p, tl, t, total, title, sub, code_title, code, line, cap_y, rail_y, code_y,
              lead=15.6, tint=TEAL):
    title_block(p, title, sub)
    code_panel(p, 26, code_y, W - 52, code_title, code, line, size=11.0, lead=lead, tint=tint,
               reveal=tl.reached("code", t))
    caption(p, tl, t, cap_y)
    progress(p, tl, t, total, rail_y)


# --------------------------------------------------------------- coin change


def coin_change():
    coins, amount = [1, 2, 5], 11
    code = source("src/problems/dp.rs", "for total in 1..=amount", "}")
    loop_c = line_of(code, "for &coin in coins")
    skip = line_of(code, "continue")
    best = line_of(code, "dp[total] = dp[total].min")
    dp = [0] + [None] * amount
    show = lambda: [INF if v is None else str(v) for v in dp]
    steps = [dict(chapter="dp[1..2]", say="dp[t] is the fewest coins that add up to t. dp[0] = 0, and every "
                  "other entry starts at infinity.", dp=show(), code=-1.0)]
    for total in range(1, amount + 1):
        detail = total <= 2 or total == amount
        options = [(c, dp[total - c] + 1) for c in coins if c <= total and dp[total - c] is not None]
        if detail:
            skipped = [c for c in coins if c > total]
            for c, cand in options:
                was = dp[total]
                dp[total] = cand if was is None else min(was, cand)
                verdict = ("the first count found" if was is None else
                           "smaller than %d, so it replaces it" % was if cand < was else
                           "not smaller than %d, so dp[%d] stays" % (was, total))
                steps.append(dict(chapter="dp[11]" if total == amount and c == coins[0] else None,
                                  say="t = %d, coin %d: dp[%d] + 1 = %d, %s." % (total, c, total - c, cand, verdict),
                                  amt=float(total), src=[total - c], dp=show(), code=float(best)))
            if skipped:
                steps.append(dict(say="Coin%s %s %s larger than %d, so the loop skips %s." % (
                    "s" if len(skipped) > 1 else "", " and ".join(map(str, skipped)),
                    "are" if len(skipped) > 1 else "is", total, "them" if len(skipped) > 1 else "it"),
                    src=[], code=float(skip), hold=0.2))
        else:
            dp[total] = min(v for _, v in options)
            steps.append(dict(chapter="dp[3..10]" if total == 3 else None,
                              say="t = %d: the smallest of %s, plus 1, is %d." % (
                                  total, ", ".join("dp[%d]" % (total - c) for c, _ in options), dp[total]),
                              amt=float(total), src=[total - c for c, _ in options], dp=show(),
                              code=float(best), hold=0.2))
    steps.append(dict(say="dp[11] = 3: 5 + 5 + 1. Each entry used only entries to its left, so one pass "
                      "filled the table.", src=[10, 9, 6], kind="insight", code=-1.0, hold=1.6))
    steps.append(dict(chapter="greedy", say="The chapter's other example: coins 1, 3, 4 and amount 6. Greedy "
                      "takes the largest coin that fits, 4.", kind="fail", amt=-1.0, src=[], greedy="4", hold=0.4))
    steps.append(dict(say="Then 1, then 1 again: three coins. The table finds 3 + 3, two coins. Greedy never "
                      "reconsiders the 4.", kind="fail", greedy="4 + 1 + 1", hold=2.0))
    steps = [{a: b for a, b in st.items() if b is not None} for st in steps]
    tl = play(steps, dict(dp=[INF] * (amount + 1), amt=-1.0, src=[], code=-1.0, greedy=""))

    def draw(p, s, total):
        t = s.t
        xs = row_xs(amount + 1, 56, 6)
        top = 150
        fills, edges = [], []
        for k in range(amount + 1):
            if abs(k - s.amt) < 0.5:
                fills.append(BRASS_LT); edges.append(BRASS)
            elif k in s.src:
                fills.append(TEAL_LT); edges.append(TEAL)
            elif s.dp[k] != INF:
                fills.append("#f6f8fa"); edges.append(NAVY)
            else:
                fills.append(PAPER); edges.append(LINE)
        cells(p, xs, top, s.dp, cell=56, fills=fills, edges=edges, size=20)
        p.text(xs[0] - 34, top + 34, "dp", 14, MUTED, 600, "end", mono=True)
        if s.amt >= 0:
            tx = xs[0] + s.amt * (xs[1] - xs[0])
            for k in s.src:
                x = xs[k]
                mid = (x + tx) / 2
                p.path("M %.1f %.1f Q %.1f %.1f %.1f %.1f" % (x, top - 4, mid, top - 46 - abs(tx - x) * 0.12,
                                                              tx - 6, top - 6), "none", TEAL, 2)
            p.text(tx, top - 12 - 52, "t = %d" % round(s.amt), 13, BRASS, 700, "middle", mono=True)
        p.text(W / 2, 256, "coins: 1, 2, 5", 14, MUTED, 600, "middle", mono=True)
        if s.greedy:
            p.text(W / 2, 286, "greedy for 6 with coins 1, 3, 4:  %s" % s.greedy, 15, RUST, 700, "middle",
                   mono=True)
        furniture(p, tl, t, total, "Coin change: fill the table left to right",
                  "dp[t] = the smallest dp[t - coin] + 1 over the coins that fit.",
                  "coin_change (the table loop)", code, s.code, cap_y, rail_y, CODE_Y)

    CODE_Y = 312
    cap_y, rail_y, height = layout(CODE_Y, len(code))
    return tl, draw, height


# ------------------------------------------------------------------ subsets


def subsets():
    nums = [1, 2, 3]
    code = source("src/problems/backtracking.rs", "fn backtrack(", "}")
    rec = line_of(code, "result.push(path.clone())")
    push = line_of(code, "path.push(nums[idx])")
    call = line_of(code, "backtrack(nums, idx + 1")
    pop = line_of(code, "path.pop()")
    # every node of the choice tree, by its path
    order = []

    def walk(start, path):
        order.append(tuple(path))
        for i in range(start, len(nums)):
            walk(i + 1, path + [nums[i]])
    walk(0, [])
    # A tidy layout: leaves are spaced evenly in depth-first order, and each
    # parent sits above the middle of its children.
    kids = {pth: [q for q in order if len(q) == len(pth) + 1 and q[:-1] == pth] for pth in order}
    xs, slot = {}, [0]

    def place(pth):
        if not kids[pth]:
            xs[pth] = 120 + slot[0] * 150
            slot[0] += 1
        else:
            for q in kids[pth]:
                place(q)
            xs[pth] = sum(xs[q] for q in kids[pth]) / len(kids[pth])
    place(())
    steps = [dict(say="Each node of the tree is one subset. Going down adds the next element; coming back "
                  "removes it.", code=-1.0)]
    result = []

    def bt(start, path):
        result.append(list(path))
        steps.append(dict(say="Record %s." % ("[]" if not path else "[" + ", ".join(map(str, path)) + "]"),
                          at=" ".join(map(str, path)), result=[list(r) for r in result], code=float(rec)))
        for i in range(start, len(nums)):
            path.append(nums[i])
            steps.append(dict(say="Push %d. The path is [%s]." % (nums[i], ", ".join(map(str, path))),
                              at=" ".join(map(str, path)), code=float(push), dur=0.6))
            bt(i + 1, path)
            path.pop()
            steps.append(dict(say="Back from the call: pop %d." % nums[i], at=" ".join(map(str, path)),
                              code=float(pop), hold=0.1, dur=0.5))
    bt(0, [])
    steps.append(dict(say="Eight subsets, in depth-first order. Each loop starts at start, so no subset is "
                      "listed twice.", kind="insight", at="", code=-1.0, hold=1.4))
    steps.append(dict(chapter="loop from 0", say="If the loop started at 0 instead, the node [2] would push 1, "
                      "and record [2, 1], a copy of [1, 2].", kind="fail", at="2", dup=1.0, hold=2.2))
    steps = [{a: b for a, b in st.items() if b is not None} for st in steps]
    steps[0]["chapter"] = "walk"
    tl = play(steps, dict(at="", result=[], code=-1.0, dup=0.0))

    def ypos(pth):
        return 112 + len(pth) * 62

    def draw(p, s, total):
        t = s.t
        cur = tuple(int(v) for v in s.at.split()) if s.at else ()
        on_path = {cur[:k] for k in range(len(cur) + 1)}
        recorded = {tuple(r) for r in s.result}
        for pth in order:
            if pth:
                parent = pth[:-1]
                on = pth in on_path
                edge(p, (xs[parent], ypos(parent)), (xs[pth], ypos(pth)), TEAL if on else LINE, 2.4 if on else 1.4,
                     r=21)
                p.text((xs[parent] + xs[pth]) / 2 - 8, (ypos(parent) + ypos(pth)) / 2, "+%d" % pth[-1], 11,
                       TEAL if on else FAINT, 700, "end")
        for pth in order:
            label = "{%s}" % ",".join(map(str, pth)) if pth else "{}"
            here = pth == cur
            fill = BRASS_LT if here else (TEAL_LT if pth in recorded else PAPER)
            edge_c = BRASS if here else (TEAL if pth in on_path else (NAVY if pth in recorded else LINE))
            p.rect(xs[pth] - 40, ypos(pth) - 17, 80, 34, fill, edge_c, 17, 1.8)
            p.text(xs[pth], ypos(pth) + 5, label, 13, INK, 700, "middle", mono=True)
        if s.dup > 0.01:
            x, y = xs[(2,)] - 110, ypos((2,)) + 124
            with p.group(opacity=s.dup):
                edge(p, (xs[(2,)], ypos((2,))), (x, y), RUST, 2.4, r=21, dash="5 4")
                p.rect(x - 40, y - 17, 80, 34, RUST_LT, RUST, 17, 1.8)
                p.text(x, y + 5, "{2,1}", 13, RUST, 700, "middle", mono=True)
        p.text(26, 380, "result", 12, MUTED, 600)
        txt = "  ".join("[%s]" % ", ".join(map(str, r)) for r in s.result)
        p.text(84, 380, txt, 13.5, TEAL, 700, mono=True)
        furniture(p, tl, t, total, "Subsets by backtracking",
                  "Depth first: push an element, recurse, then pop it and try the next one.",
                  "backtrack", code, s.code, cap_y, rail_y, CODE_Y)

    CODE_Y = 400
    cap_y, rail_y, height = layout(CODE_Y, len(code))
    return tl, draw, height


def build(name, fn, extra=()):
    def run(only=None):
        tl, draw, height = fn()
        return render(name, tl, draw, height, only=only, extra_colors=extra)
    return run


BUILDERS = {
    "coin-change": build("ch06-coin-change.gif", coin_change, (NAVY,)),
    "subsets": build("ch06-subsets.gif", subsets, (NAVY,)),
}
