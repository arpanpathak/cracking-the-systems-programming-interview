"""The first chapter's animation (ch01-bindings.md), drawn with `motion`.

    python3 tools/animations.py fib-calls
"""

from anim_kernel import block_at
from motion import *  # noqa: F401,F403
from motion import Timeline, render

RECURSIVE = block_at("src/bin/cs_fib.rs", 9, 15)
MEMO = block_at("src/bin/cs_fib.rs", 28, 37)
N = 5
TREE_X0, TREE_X1, TREE_Y, LEVEL = 40, 540, 100, 40


def simulate(n, memo):
    """Run fib(n) and record each call: nodes (n, depth, parent) and events."""
    nodes, events = [], []
    cache = [0] * (n + 1)

    def call(k, depth, parent):
        me = len(nodes)
        nodes.append((k, depth, parent))
        events.append(("enter", me))
        if k < 2:
            events.append(("return", me, k))
            return k
        if memo and cache[k]:
            events.append(("hit", me, cache[k]))
            return cache[k]
        value = call(k - 1, depth + 1, me) + call(k - 2, depth + 1, me)
        if memo:
            cache[k] = value
            events.append(("store", k, value))
        events.append(("return", me, value))
        return value

    call(n, 0, None)
    return nodes, events


def positions(nodes):
    """x by leaf order, y by depth."""
    children = {i: [j for j, (_, _, parent) in enumerate(nodes) if parent == i]
                for i in range(len(nodes))}
    leaves = [i for i in range(len(nodes)) if not children[i]]
    step = (TREE_X1 - TREE_X0) / max(1, len(leaves) - 1)
    xs = {}

    def place(i):
        if not children[i]:
            xs[i] = TREE_X0 + leaves.index(i) * step
        else:
            for c in children[i]:
                place(c)
            xs[i] = sum(xs[c] for c in children[i]) / len(children[i])

    place(0)
    return {i: (xs[i], TREE_Y + nodes[i][1] * LEVEL) for i in range(len(nodes))}


def fib_calls():
    plans = {"memo": simulate(N, True), "plain": simulate(N, False)}
    layouts = {mode: positions(nodes) for mode, (nodes, _) in plans.items()}
    tl = Timeline(caption="", kind="step", code=-1.0, mode="memo", shown=0, vals="", hits="",
                  stack="", calls=0.0, cache="0,0,0,0,0,0", hot=-1)

    def run(mode, k, notes):
        nodes, events = plans[mode]
        shown, vals, hits, stack, calls = 0, {}, set(), [], 0
        cache = [0] * (N + 1)
        for event in events:
            kind = event[0]
            key = (kind, event[1])
            if key in notes:
                tl.say(*notes[key])
            if kind == "enter":
                i = event[1]
                shown, calls = shown + 1, calls + 1
                stack.append("go(%d)" % nodes[i][0] if mode == "memo" else "recursive(%d)" %
                             nodes[i][0])
                tl.set(shown=shown, hot=i, stack=",".join(stack),
                       code=1.0 if nodes[i][0] < 2 else (5.0 if mode == "memo" else 4.0))
                tl.to(0.2, calls=float(calls))
            elif kind == "hit":
                i, value = event[1], event[2]
                vals[i] = value
                hits.add(i)
                stack.pop()
                tl.set(vals=";".join("%d=%d" % kv for kv in vals.items()),
                       hits=",".join(map(str, hits)), stack=",".join(stack), code=8.0)
            elif kind == "store":
                cache[event[1]] = event[2]
                tl.set(cache=",".join(map(str, cache)), code=6.0)
            else:
                i, value = event[1], event[2]
                vals[i] = value
                stack.pop()
                tl.set(vals=";".join("%d=%d" % kv for kv in vals.items()), stack=",".join(stack))
            tl.wait(k)

    tl.chapter("with a cache")
    tl.say("memoized(5) calls go(5). Each call pushes a frame on the stack, shown on the right.")
    tl.set(mode="memo", code=-1.0)
    tl.wait(0.6)
    run("memo", 0.55, {
        ("return", 4): ("go(1) is a base case. It returns 1 at once, and its frame is popped.",),
        ("store", 2): ("go(2) has both answers. It stores fib(2) = 1 in the cache, and returns.",),
        ("enter", 7): ("go(4) now calls go(2). Its slot in the cache is filled, so go returns it "
                       "without calling further.",),
    })
    tl.say("9 calls for memoized(5). Each value from 2 to 5 was computed once, then read.",
           "insight")
    tl.wait(1.2)

    tl.chapter("no cache")
    tl.say("Now recursive(5), the same calls without the cache.", "fail")
    tl.set(mode="plain", shown=0, vals="", hits="", stack="", calls=0.0, cache="0,0,0,0,0,0",
           hot=-1, code=-1.0)
    tl.wait(0.6)
    run("plain", 0.32, {
        ("enter", 7): ("recursive(4) calls recursive(2), which was computed a moment ago. It "
                       "runs again.", "fail"),
        ("enter", 10): ("recursive(5) calls recursive(3), and all of its work repeats.", "fail"),
    })
    tl.say("15 calls. fib(3) ran twice and fib(2) three times. The count grows about 1.6 times "
           "per step of n.", "fail")
    tl.wait(1.6)

    def draw(p, s, total):
        t = s.t
        nodes, _ = plans[s.mode]
        place = layouts[s.mode]
        title_block(p, "Fibonacci: the calls and the stack",
                    "memoized(5) with a cache, then recursive(5) without one.")
        scoreboard(p, [("calls", int(round(s.calls)), TEAL if s.mode == "memo" else RUST)])
        shown = int(s.shown)
        vals = dict(tuple(map(int, kv.split("="))) for kv in s.vals.split(";") if kv)
        hits = {int(h) for h in s.hits.split(",") if h}
        seen = {}
        for i in range(shown):
            k, _, parent = nodes[i]
            if parent is not None:
                a, b = place[parent], place[i]
                p.line(a[0], a[1] + 14, b[0], b[1] - 14, LINE, 1.4)
        for i in range(shown):
            k, _, _ = nodes[i]
            x, y = place[i]
            repeat = s.mode == "plain" and k >= 2 and seen.get(k, 0) > 0
            seen[k] = seen.get(k, 0) + 1
            hit = i in hits
            fill = BRASS_LT if hit else (RUST_LT if repeat else (TEAL_LT if i in vals else PAPER))
            edge = BRASS if hit else (RUST if repeat else TEAL)
            p.circle(x, y, 15, fill, edge, 1.6)
            p.text(x, y + 4, str(k), 11, INK, 700, "middle", mono=True)
            if i in vals:
                p.text(x, y + 28, "=%d" % vals[i], 9.5, MUTED, 700, "middle", mono=True)
            if int(s.hot) == i:
                p.circle(x, y, 20, "none", BRASS, 2.0, dash="4 3")
        # the stack
        stack = [f for f in s.stack.split(",") if f]
        sx, sy = 590, 300
        p.text(sx, 90, "stack (top at the top)", 10.5, MUTED, 600)
        p.rect(sx, sy - 6 * 30 - 8, 200, 6 * 30 + 12, STAGE, LINE, 8, 1.0)
        for d, frame in enumerate(stack):
            fy = sy - (d + 1) * 30
            p.rect(sx + 8, fy, 184, 26, PAPER, TEAL, 5, 1.2)
            p.text(sx + 100, fy + 17, frame, 11, INK, 700, "middle", mono=True)
        if s.mode == "memo":
            values = s.cache.split(",")
            p.text(40, 334, "cache", 11, MUTED, 600)
            for k, v in enumerate(values):
                x = 96 + k * 48
                filled = k >= 2 and v != "0"
                p.rect(x, 318, 42, 26, TEAL_LT if filled else PAPER, TEAL if filled else LINE, 4,
                       1.2)
                p.text(x + 21, 336, v, 11, INK if filled else FAINT, 700, "middle", mono=True)
                p.text(x + 21, 358, str(k), 9.5, MUTED, 600, "middle", mono=True)
        lines = MEMO if s.mode == "memo" else RECURSIVE
        title = "memoized: the inner function go" if s.mode == "memo" else "recursive"
        code_panel(p, 26, 372, W - 52, title, lines, s.code, size=10.6, lead=15.5,
                   tint=TEAL if s.mode == "memo" else RUST,
                   reveal=s.timeline.reached("code", t))
        caption(p, tl, t, 580)
        progress(p, tl, t, total, 666)

    return tl, draw, 700


def build_fib_calls(only=None):
    tl, draw, height = fib_calls()
    return render("ch01-fib-calls.gif", tl, draw, height, only=only)


BUILDERS = {
    "fib-calls": build_fib_calls,
}
