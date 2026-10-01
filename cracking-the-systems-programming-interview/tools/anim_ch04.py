"""The iterator chapter animation (ch04-iterators.md), drawn with `motion`.

    python3 tools/animations.py lazy-chain
"""

from anim_kernel import block_at
from motion import *  # noqa: F401,F403
from motion import Timeline, render

CHAIN = block_at("src/bin/lifetime_reference_drill.rs", 10, 14)
INPUT = [10, 15, 20, 25, 30]
STAGES = [("iter()", 150), ("filter", 330), ("map", 500), ("collect", 680)]
LANE_Y = 160


def lazy_chain():
    tl = Timeline(caption="", kind="step", code=-1.0, item=-1, item_x=150.0, item_label="",
                  item_a=0.0, pull_u=0.0, pull_a=0.0, out="", dropped=0.0, consumed=0,
                  idle=0.0)

    def pull(k=1.0):
        tl.set(pull_u=0.0)
        tl.to(0.1, pull_a=1.0)
        tl.to(0.7 * k, in_out, pull_u=1.0)
        tl.to(0.1, pull_a=0.0)

    def flow(i, k=1.0, narrate=False):
        value = INPUT[i]
        pull(k)
        tl.set(item=i, item_x=150.0, item_label="&%d" % value, consumed=i + 1, code=1.0)
        tl.to(0.15, item_a=1.0)
        tl.to(0.5 * k, in_out, item_x=330.0)
        tl.set(code=2.0)
        if value % 2:
            if narrate:
                tl.say("15 is odd. filter drops it and asks iter for the next item at once.")
            tl.to(0.4, dropped=1.0, item_a=0.0)
            tl.wait(0.4 * k)
            tl.set(dropped=0.0)
            return False
        tl.to(0.5 * k, in_out, item_x=500.0)
        tl.set(item_label=str(value * 10), code=3.0)
        tl.to(0.5 * k, in_out, item_x=680.0)
        tl.set(code=4.0)
        out = [v for v in tl._at("out", tl.now).split(",") if v] + [str(value * 10)]
        tl.to(0.15, item_a=0.0)
        tl.set(out=",".join(out))
        return True

    tl.chapter("pull")
    tl.say("The chain only describes the work. collect starts it, by asking map for an item.")
    tl.set(code=4.0)
    tl.wait(0.4)
    tl.say("map asks filter, and filter asks iter. Each request is one call to next().")
    flow(0, 1.4)
    tl.say("&10 is even. It passes filter, map turns it into 100, and collect stores it.")
    tl.wait(0.8)

    tl.chapter("one at a time")
    tl.say("collect asks again. The next item, &15, starts only after 10 has gone all the way.")
    flow(1, 1.0, narrate=True)
    flow(2, 0.7)
    flow(3, 0.6)
    flow(4, 0.6)
    tl.say("Five items, one pass, and no vector between the stages: [100, 200, 300].", "insight")
    tl.wait(1.2)

    tl.chapter("no collect")
    tl.say("Now remove collect. The chain is built, and nothing asks it for an item.", "fail")
    tl.set(out="", consumed=0, code=-1.0, item=-1)
    tl.to(0.4, idle=1.0)
    tl.wait(1.2)
    tl.say("No next() is called, so filter and map never run. The compiler warns: unused Map "
           "that must be used.", "fail")
    tl.wait(1.6)

    def draw(p, s, total):
        t = s.t
        title_block(p, "A lazy chain",
                    "Adapters do nothing until something asks for items. Each item goes all the "
                    "way through.")
        p.text(26, 92, "input", 11, MUTED, 600)
        for i, v in enumerate(INPUT):
            used = i < int(s.consumed)
            chip(p, 92 + i * 50, 88, str(v), FAINT if used else INK, STAGE if used else PAPER,
                 11)
        p.line(110, LANE_Y, 720, LANE_Y, LINE, 2)
        for name, x in STAGES:
            active = (name != "iter()" and s.idle < 0.5) or name == "iter()"
            p.rect(x - 50, LANE_Y - 26, 100, 52, TEAL_LT if active else STAGE,
                   TEAL if active else LINE, 8, 1.4)
            p.text(x, LANE_Y + 5, name, 13, INK if active else FAINT, 700, "middle", mono=True)
        if s.idle > 0.01:
            p.rect(STAGES[3][1] - 50, LANE_Y - 26, 100, 52, PAPER, RUST, 8, 1.6, dash="5 4",
                   opacity=s.idle)
            p.text(STAGES[3][1], LANE_Y + 5, "(none)", 12, RUST, 700, "middle", mono=True,
                   opacity=s.idle)
            chip(p, 410, LANE_Y + 62, "warning: unused `Map` that must be used", RUST, RUST_LT,
                 11, opacity=s.idle)
        if s.pull_a > 0.01:
            x = lerp(680, 150, s.pull_u)
            pill(p, x, LANE_Y - 50, "next()", NIGHT, NIGHT_LT, 10, opacity=s.pull_a, shadow=None)
        if s.item_a > 0.01:
            pill(p, s.item_x, LANE_Y + 44, s.item_label, BRASS, BRASS_LT, 11, opacity=s.item_a,
                 shadow=None)
        if s.dropped > 0.01:
            chip(p, 330, LANE_Y + 70, "dropped: odd", RUST, RUST_LT, 10, opacity=s.dropped)
        p.text(26, 260, "Vec<i32> built by collect:", 11, MUTED, 600)
        out = [v for v in s.out.split(",") if v]
        p.text(210, 260, "[" + ", ".join(out) + "]", 14, INK, 700, mono=True)

        code_panel(p, 26, 286, W - 52, "functional_numbers_drill", CHAIN, s.code, size=11.0,
                   lead=16.5, strike=4 if s.idle > 0.5 else None,
                   reveal=s.timeline.reached("code", t))
        caption(p, tl, t, 430)
        progress(p, tl, t, total, 516)

    return tl, draw, 550


def build_lazy_chain(only=None):
    tl, draw, height = lazy_chain()
    return render("ch04-lazy-chain.gif", tl, draw, height, only=only)


BUILDERS = {
    "lazy-chain": build_lazy_chain,
}
