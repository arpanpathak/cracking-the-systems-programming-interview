"""The chapter 6 animations (ch06-dynamic-programming.md), drawn with `motion`.

    python3 tools/animations.py coin-change subsets
"""

from motion import (BRASS, BRASS_LT, FAINT, INK, LINE, MUTED, PAPER, RUST, RUST_LT, TEAL,
                    TEAL_LT, W, bezier, caption, chip, clamp, code_panel, lerp, mix, pill,
                    progress, render, scoreboard, title_block)
from motion_kit import (NAVY, Panels, arrow, cells, edge, layout, line_of, node, play, row_xs,
                        source)

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


# ---------------------------------------------- jobs that need memory and cores

JOBS = [("A", 1, 3, 12, 20, 50), ("B", 2, 4, 8, 10, 10), ("C", 3, 5, 40, 60, 40),
        ("D", 3, 6, 60, 90, 70)]
PREV = [0, 0, 1, 1]
CARDS = [("gpu 0", 80, 108), ("gpu 1", 16, 40)]
FITS_SMALL = [True, True, False, False]
X0, XSTEP = 190, 82
ROW_Y, ROW_H, BAR_H = 140, 32, 22
AXIS_Y, CARD_Y, CARD_H = 266, 64, 54
DP_Y, DP_CELL, DP_GAP = 320, 60, 10
LANE_Y = [304, 346]
CODE_Y, CODE_LEAD = 410, 14.4
SPLIT_JOBS = {0: ["A", "D"], 1: ["B"]}
SPLIT_SUM = {0: 120, 1: 10}


def job_x(t):
    return X0 + t * XSTEP


def cell_arrow(p, xs, src, tgt, color, bend, dash=None, opacity=1.0, dx=0.0):
    """An arrow from the top of cell `src` into the top of cell `tgt`."""
    arrow(p, xs[src] + dx, DP_Y - 6, xs[tgt] + dx, DP_Y - 2, color=color, width=2.4, head=11,
          bend=bend, dash=dash, opacity=opacity)


GPU_CODE = Panels("src/bin/gpu_job_schedule.rs",
                  [[("let prev: Vec<usize> = jobs", ".collect();")],
                   [("let pick_jobs_dp = |gpu: &Gpu| {", "}")],
                   [("gpus.iter()", ".unwrap_or(0)")]],
                  ["prev: the jobs that finish in time", "dp: one pass per GPU",
                   "the best GPU wins"],
                  ["let prev: Vec<usize> = jobs",
                   "jobs.partition_point(|earlier| earlier.end <= job.start)",
                   "for index in 0..jobs.len() {",
                   "if gpu.fits(job) {",
                   "dp[index].max(dp[prev[index]] + job.profit)",
                   "gpus.iter()"])


def gpu_jobs():
    code = GPU_CODE
    empty_dp = ",".join(["-"] * 5)
    steps = [dict(chapter="the jobs", job=-1.0, gpu=-1.0, dp=empty_dp, prev_v="-,-,-,-",
                  compat="", probe=-1.0, skip_from=-1.0, take_from=-1.0, winner="", nofit=0.0,
                  strike=-1.0, best="", split=0.0, code=-1.0,
                  say="Four jobs. Each has a start, an end, a memory need, a core need, and a "
                      "profit.")]
    steps.append(dict(say="gpu 0 has 80 GB and 108 cores. gpu 1 has 16 GB and 40 cores."))

    steps.append(dict(chapter="prev", code=0.0,
                      say="Sort the jobs by end time. For each job, count the jobs that finish by "
                          "the time it starts."))
    shown = ["-"] * 4
    for i, (name, start, end, mem, cores, profit) in enumerate(JOBS):
        earlier = [j for j in range(i) if JOBS[j][2] <= start]
        shown[i] = str(len(earlier))
        if earlier:
            say = "%s starts at %d. %s ends by then, so prev = %d." % (
                name, start, " and ".join(JOBS[j][0] for j in earlier), len(earlier))
        else:
            say = "%s starts at %d. No earlier job ends by then, so prev = 0." % (name, start)
        steps.append(dict(say=say, probe=float(start), job=str(i),
                          compat=",".join(str(j) for j in earlier), prev_v=",".join(shown),
                          code=1.0, dur=0.5))
    steps.append(dict(say="The jobs are sorted by end, so the ones that finish in time are a "
                          "prefix, and one search finds its length.", kind="insight", probe=-1.0,
                      job="-1", compat="", code=1.0, hold=1.2))

    for g, values in ((0, [0, 50, 50, 90, 120]), (1, [0, 50, 50, 50, 50])):
        name = CARDS[g][0]
        steps.append(dict(chapter=name, code=2.0, gpu=float(g), job="-1", dp=empty_dp,
                          skip_from="-1", take_from="-1", winner="", nofit=0.0,
                          say="Now the same table for %s." % name))
        filled = ["0"] + ["-"] * 4
        for i, (job, start, end, mem, cores, profit) in enumerate(JOBS):
            if g == 1 and not FITS_SMALL[i]:
                filled[i + 1] = filled[i]
                steps.append(dict(
                    say="%s needs %d GB and %d cores. %s has %d GB and %d cores, so %s does not "
                        "fit, and dp[%d] copies %s." % (job, mem, cores, name, CARDS[g][1],
                                                        CARDS[g][2], job, i + 1, filled[i]),
                    dp=",".join(filled), job=str(i), skip_from=str(i),
                    take_from=str(PREV[i]), winner="skip", nofit=1.0, code=3.0, dur=0.5))
                continue
            skip, take = values[i], values[PREV[i]] + profit
            win = "take" if take > skip else "skip"
            filled[i + 1] = str(max(skip, take))
            verb = "takes %d" % take if win == "take" else "keeps %d" % skip
            steps.append(dict(
                say="%s fits. Skip keeps dp[%d] = %d. Take is dp[%d] + %d = %d. The table %s." % (
                    job, i, skip, PREV[i], profit, take, verb),
                dp=",".join(filled), job=str(i), skip_from=str(i), take_from=str(PREV[i]),
                winner=win, nofit=0.0, code=4.0, dur=0.5, events=("fly",), fly_job=str(i)))
        steps.append(dict(say="%s ends at %d." % (name, values[-1]), kind="insight", code=5.0,
                          job="-1", skip_from="-1", take_from="-1", winner="", nofit=0.0,
                          best=str(values[-1]), hold=1.2))

    steps.append(dict(chapter="the fit test", kind="fail", gpu=1.0, job="2", code=3.0, strike="3",
                      skip_from="2", take_from="1", winner="take", nofit=0.0, dp="0,50,50,90,-",
                      say="Strike the fit test. gpu 1 now takes C, which needs 40 GB it does not "
                          "have.", hold=1.0))
    steps.append(dict(say="Then D, which needs 60 GB. gpu 1 reports 120.", kind="fail", job="3",
                      skip_from="3", take_from="1", winner="take", dp="0,50,50,90,120", hold=1.2))
    steps.append(dict(say="gpu 1 has 16 GB, so that schedule is not real. The fit test keeps the "
                          "table to jobs the GPU can run.", kind="fail", strike="-1", job="-1",
                      skip_from="-1", take_from="-1", dp="0,50,50,50,50", hold=1.4))

    steps.append(dict(chapter="share", gpu=-1.0, job="-1", code=5.0, best="120",
                      say="With the fit test back, the best single GPU earns 120 while the other "
                          "one runs nothing.", kind="insight", hold=1.2))
    steps.append(dict(say="Share the jobs. A and D on gpu 0 earn 50 + 70 = 120, and B on gpu 1 "
                          "earns 10.", split=1.0, best="130", events=("fly",), fly_job="1",
                      hold=1.8))
    steps.append(dict(say="The total is 130. One table per GPU cannot choose this split.",
                      split=1.0, hold=2.2))

    steps = [{k: v for k, v in st.items() if v is not None} for st in steps]
    tl = play(steps, dict(job="-1", gpu=-1.0, dp=empty_dp, prev_v="-,-,-,-", compat="", probe=-1.0,
                          skip_from="-1", take_from="-1", winner="", nofit=0.0, strike="-1",
                          best="", split=0.0, code=-1.0, fly_job=""))

    def draw(p, s, total):
        t = s.t
        title_block(p, "Jobs that need memory and cores",
                    "One GPU runs one job at a time, and a job fits only when the GPU has its "
                    "memory and its cores.")
        scoreboard(p, [("best", s.best or "-", TEAL)])
        split = clamp(s.split)

        for i, (name, mem, cores) in enumerate(CARDS):
            x = 30 + i * 400
            on = abs(s.gpu - i) < 0.5
            p.rect(x, CARD_Y, 380, CARD_H, BRASS_LT if on else PAPER, BRASS if on else LINE, 10,
                   2.2 if on else 1.4)
            p.text(x + 14, CARD_Y + 22, name, 13.5, INK, 700, mono=True)
            p.text(x + 88, CARD_Y + 22, "%d GB, %d cores" % (mem, cores), 11.5, MUTED, 600)
            if split > 0.5:
                runs = " + ".join("%s %d" % (jb[0], jb[5]) for jb in JOBS
                                  if jb[0] in SPLIT_JOBS[i])
                p.text(x + 14, CARD_Y + 44, "%s = %d" % (runs, SPLIT_SUM[i]), 11, BRASS, 700,
                       mono=True)

        p.line(job_x(0), AXIS_Y, job_x(7), AXIS_Y, LINE, 2)
        for k in range(8):
            p.line(job_x(k), AXIS_Y, job_x(k), AXIS_Y + 6, LINE, 1.5)
            p.text(job_x(k), AXIS_Y + 20, str(k), 10, FAINT, 600, "middle", mono=True)
        if s.probe >= 0:
            p.line(job_x(s.probe), AXIS_Y - 132, job_x(s.probe), AXIS_Y + 4, BRASS, 2, dash="6 5")

        small = clamp(s.gpu)
        compat = {int(v) for v in s.compat.split(",") if v != ""}
        prevs = s.prev_v.split(",")
        chosen = SPLIT_JOBS[0] + SPLIT_JOBS[1]
        for i, (name, start, end, mem, cores, profit) in enumerate(JOBS):
            y = ROW_Y + i * ROW_H
            here = int(s.job) == i
            keep = i in compat
            no_fit = small > 0.5 and not FITS_SMALL[i]
            if no_fit:
                fill, line_c, ink = RUST_LT, RUST, RUST
            elif split > 0.5 and name in chosen:
                tint = BRASS if name in SPLIT_JOBS[0] else TEAL
                fill, line_c, ink = mix(tint, PAPER, 0.86), tint, INK
            elif here:
                fill, line_c, ink = BRASS_LT, BRASS, INK
            elif keep:
                fill, line_c, ink = TEAL_LT, TEAL, INK
            else:
                fill, line_c, ink = PAPER, LINE, INK
            op = 1.0 if split < 0.5 or name in chosen else 0.35
            if here and split < 0.5:
                p.rect(18, y - 3, W - 36, ROW_H + 6, BRASS_LT, "none", 8, opacity=0.65 * op)
                p.rect(18, y - 3, 4, ROW_H + 6, BRASS, "none", 2, opacity=op)
            p.text(26, y + 16, name, 15, BRASS if here else INK, 700, mono=True, opacity=op)
            p.text(52, y + 16, "%d GB, %d cores, profit %d" % (mem, cores, profit), 10, MUTED,
                   600, mono=True, opacity=op)
            p.text(job_x(start) - 10, y + 16, "prev %s" % prevs[i], 10,
                   TEAL if prevs[i] != "-" else FAINT, 700, "end", mono=True, opacity=op)
            p.rect(job_x(start), y, job_x(end) - job_x(start), BAR_H, fill, line_c, 7, 1.8,
                   opacity=op)
            p.text(job_x(start) + 8, y + 16, "%d-%d" % (start, end), 9.5, MUTED, 600, mono=True,
                   opacity=op)
            p.text(job_x(end) - 8, y + 16, "profit %d" % profit, 11, ink, 700, "end", mono=True,
                   opacity=op)
            if no_fit:
                chip(p, job_x(end) + 34, y + 11, "no fit", RUST, RUST_LT, 10, opacity=small)

        dp = s.dp.split(",")
        xs = row_xs(5, DP_CELL, DP_GAP)
        tgt = int(s.job) + 1 if int(s.job) >= 0 else -1
        fills, edgec = [], []
        for k in range(5):
            done = dp[k] != "-"
            fills.append(BRASS_LT if tgt == k else (TEAL_LT if done else PAPER))
            edgec.append(BRASS if tgt == k else (TEAL if done else LINE))
        cells(p, xs, DP_Y, dp, cell=DP_CELL, fills=fills, edges=edgec, size=18,
              index_labels=["dp[%d]" % k for k in range(5)], opacity=1 - split)
        if int(s.skip_from) >= 0 or int(s.take_from) >= 0:
            p.text(xs[0] - DP_CELL / 2 - 14, DP_Y + 16, "skip", 11, TEAL, 700, "end", mono=True,
                   opacity=1 - split)
            p.text(xs[0] - DP_CELL / 2 - 14, DP_Y + 36, "take", 11, BRASS, 700, "end", mono=True,
                   opacity=1 - split)
        if 0 <= tgt < 5 and split < 0.5:
            if int(s.skip_from) >= 0:
                cell_arrow(p, xs, int(s.skip_from), tgt, TEAL, -26, dx=-12,
                           opacity=0.25 if s.winner == "take" else 1.0)
            if int(s.take_from) >= 0:
                nofit = s.nofit > 0.5
                col = RUST if nofit else BRASS
                cell_arrow(p, xs, int(s.take_from), tgt, col, -48, dx=12,
                           dash="5 4" if nofit else None,
                           opacity=0.25 if (s.winner == "skip" and not nofit) else 1.0)
                if nofit:
                    hx, hy = xs[tgt] + 12, DP_Y - 6
                    p.line(hx - 7, hy - 7, hx + 7, hy + 7, RUST, 2.2)
                    p.line(hx - 7, hy + 7, hx + 7, hy - 7, RUST, 2.2)

        age = s.timeline.age("fly", t)
        if s.fly_job and age is not None and age < 0.6:
            i = int(s.fly_job)
            u = clamp(age / 0.6)
            if split > 0.5:
                p0 = (job_x(JOBS[i][2]), ROW_Y + i * ROW_H + BAR_H / 2)
                p2 = (596, CARD_Y + CARD_H / 2)
                p1 = ((p0[0] + p2[0]) / 2, 150)
                x, y = bezier(p0, p1, p2, u)
                pill(p, x, y, JOBS[i][0], TEAL, TEAL_LT, 11)
            elif 0 <= tgt < 5:
                take = s.winner == "take"
                src = int(s.take_from if take else s.skip_from)
                bend = -48 if take else -26
                col = BRASS if take else TEAL
                light = BRASS_LT if take else TEAL_LT
                label = "+%d" % JOBS[int(s.job)][5] if take else dp[tgt]
                p0 = (xs[src], DP_Y - 6)
                p2 = (xs[tgt], DP_Y - 2)
                p1 = ((p0[0] + p2[0]) / 2, DP_Y - 6 + bend)
                x, y = bezier(p0, p1, p2, u)
                pill(p, x, y, label, col, light, 11)

        if split > 0.01:
            with p.group(opacity=split):
                for g in (0, 1):
                    y = LANE_Y[g]
                    col = BRASS if g == 0 else TEAL
                    p.text(X0 - 16, y + 20, CARDS[g][0], 12, INK, 700, "end", mono=True)
                    p.rect(X0, y, job_x(7) - X0, 30, "#fbfcfd", LINE, 8, 1.4)
                    for jb in JOBS:
                        name, start, end, mem, cores, profit = jb
                        if name not in SPLIT_JOBS[g]:
                            continue
                        p.rect(job_x(start) + 2, y + 3, job_x(end) - job_x(start) - 4, 24,
                               mix(col, PAPER, 0.8), col, 6, 1.6)
                        p.text(job_x(start) + 10, y + 20, "%s %d" % (name, profit), 11, INK, 700,
                               mono=True)
                    p.text(job_x(7) + 6, y + 20, "= %d" % SPLIT_SUM[g], 12, col, 700, mono=True)

        code.draw(p, 26, CODE_Y, W - 52, s, t, size=10.4, lead=CODE_LEAD,
                  strike=float(s.strike) if float(s.strike) >= 0 else None)
        caption(p, tl, t, CAP)
        progress(p, tl, t, total, RAIL)

    CAP, RAIL, height = layout(CODE_Y, len(code), CODE_LEAD)
    return tl, draw, height


def build(name, fn, extra=()):
    def run(only=None):
        tl, draw, height = fn()
        return render(name, tl, draw, height, only=only, extra_colors=extra)
    return run


BUILDERS = {
    "coin-change": build("ch06-coin-change.gif", coin_change, (NAVY,)),
    "subsets": build("ch06-subsets.gif", subsets, (NAVY,)),
    "gpu-jobs": build("ch06-gpu-jobs.gif", gpu_jobs, (NAVY,)),
}
