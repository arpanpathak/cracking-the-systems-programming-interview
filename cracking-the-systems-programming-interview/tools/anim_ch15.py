"""The memory chapter animations (ch15-memory-os.md), drawn with `motion`.

    python3 tools/animations.py mem-hierarchy false-sharing
"""

from motion_kit import Panel, Panels, layout
from motion import *  # noqa: F401,F403
from motion import Timeline, render

LOOPS = Panel("src/bin/cs_locality.rs",
              [("fn sequential_sum(data: &[u64])", "}"), ("fn strided_sum(data: &[u64])", "}")],
              ["let sum = data.iter().sum();", "index = (index + STRIDE) % data.len();",
               "sum = sum.wrapping_add(data[index]);"])
SHARING = Panels("src/bin/false_sharing.rs",
                 [[(("thread::scope(|s| {", 0), "}")], [(("thread::scope(|s| {", 1), "}")]],
                 ["two threads, one struct: same.a and same.b",
                  "two threads, padded: p0 and p1"],
                 ["same.a.fetch_add(1, Ordering::Relaxed);",
                  "same.b.fetch_add(1, Ordering::Relaxed);",
                  "p0.0.fetch_add(1, Ordering::Relaxed);",
                  "p1.0.fetch_add(1, Ordering::Relaxed);"])

# ------------------------------------------------- 15.1: the memory hierarchy

CORE_X, CORE_DESK = 92, 214
LEVELS = [  # name, x0, x1, size, measured time per dependent read
    ("L1", 196, 280, "48 KiB", 2.2),
    ("L2", 296, 400, "512 KiB", 5.6),
    ("L3", 416, 560, "6 MiB", 42.3),
    ("RAM", 576, 794, "16 GiB", 146.2),
]
LEVEL_Y, LEVEL_H = 96, 112


def level_center(n):
    _, x0, x1, _, _ = LEVELS[n]
    return ((x0 + x1) / 2, LEVEL_Y + LEVEL_H / 2)


def mem_hierarchy():
    tl = Timeline(caption="", kind="step", code=-1.0, req_u=0.0, req_a=0.0, req_to=0,
                  line_u=0.0, line_a=0.0, line_from=0, ns=0.0, lit=-1, cached=0.0, used=0.0,
                  hits=0.0, misses=0.0, mode="one")

    def read(level, k=1.0, count_ns=None):
        tl.set(req_to=level, req_u=0.0, lit=-1)
        tl.to(0.1, req_a=1.0)
        tl.to(0.5 + 0.35 * level * k, in_out, req_u=1.0)
        tl.set(lit=level)
        tl.to(0.1, req_a=0.0)
        tl.set(line_from=level, line_u=0.0)
        tl.to(0.1, line_a=1.0)
        tl.to(0.5 + 0.35 * level * k, in_out, line_u=1.0,
              ns=count_ns if count_ns is not None else LEVELS[level][4])
        tl.to(0.1, line_a=0.0)

    tl.chapter("one read")
    tl.say("The core needs one u64. It asks L1 first, then each larger, slower level in turn.")
    tl.wait(0.4)
    tl.say("With 16 KiB of data, the value is already in L1: 2.2 ns.")
    read(0)
    tl.wait(0.6)
    tl.say("With 2 MiB, it misses L1 and L2, and comes from L3: 42.3 ns.")
    tl.set(ns=0.0)
    read(2)
    tl.wait(0.6)
    tl.say("With 256 MiB, it misses every cache and comes from RAM: 146 ns.")
    tl.set(ns=0.0)
    read(3)
    tl.say("Each level is larger and slower than the one above it. RAM is about 65 times slower "
           "than L1.", "insight")
    tl.wait(1.0)

    tl.chapter("a line")
    tl.say("Memory moves in 64-byte lines. A miss on one u64 brings the next seven with it.")
    tl.set(mode="seq", ns=0.0, code=0.0, lit=-1)
    read(3, 0.7, 146.2)
    tl.to(0.4, cached=8.0, used=1.0, misses=1.0)
    tl.say("Reading in order, the next seven values are already in L1. Each costs about 2 ns.")
    for k in range(7):
        tl.to(0.3, used=float(k + 2), hits=float(k + 1), ns=146.2 + 2.2 * (k + 1))
    tl.say("Eight values for one trip to RAM. The CPU also fetches the next line early, so the "
           "next miss is hidden too.", "insight")
    tl.wait(1.0)

    tl.chapter("scattered")
    tl.say("Now read scattered values, each in a different line.", "fail")
    tl.set(mode="scatter", ns=0.0, cached=0.0, used=0.0, hits=0.0, misses=0.0, code=1.0)
    for k in range(4):
        read(3, 0.45 if k else 0.7, 146.2 * (k + 1))
        tl.to(0.2, cached=8.0, used=1.0, misses=float(k + 1))
        if k == 0:
            tl.say("Every read pays for a whole line and uses one value of the eight.", "fail")
    tl.say("Same work, eight times the traffic. Independent reads overlap, but a chain of them "
           "waits on each one.", "fail")
    tl.wait(1.6)

    def draw(p, s, total):
        t = s.t
        title_block(p, "How far away is memory?",
                    "Measured time for one dependent read, by where the data is.")
        scoreboard(p, [("time", "%.1f ns" % s.ns, RUST if s.mode == "scatter" else TEAL)])
        robot(p, CORE_X, CORE_DESK, TEAL, 1.0, 1.0, "core", "registers")
        for n, (name, x0, x1, size, ns) in enumerate(LEVELS):
            lit = int(s.lit) == n
            p.rect(x0, LEVEL_Y, x1 - x0, LEVEL_H, BRASS_LT if lit else STAGE, BRASS if lit else LINE,
                   8, 1.6 if lit else 1.2)
            p.text((x0 + x1) / 2, LEVEL_Y + 22, name, 14, INK, 700, "middle")
            p.text((x0 + x1) / 2, LEVEL_Y + 40, size, 10.5, MUTED, 600, "middle")
            p.text((x0 + x1) / 2, LEVEL_Y + LEVEL_H + 18, "%.1f ns" % ns, 11, INK, 700, "middle",
                   mono=True)
        # the line held in L1: eight u64 slots
        if s.cached > 0.5:
            _, x0, x1, _, _ = LEVELS[0]
            for k in range(8):
                used = k < int(round(s.used))
                cx = x0 + 10 + (k % 4) * 17
                cy = LEVEL_Y + 56 + (k // 4) * 20
                p.rect(cx, cy, 14, 14, TEAL if used else PAPER, TEAL, 3, 1.1)
            p.text((x0 + x1) / 2, LEVEL_Y + LEVEL_H - 6, "one line", 9.5, MUTED, 600, "middle")
        if s.mode != "one":
            p.text(196, 270, "values used from lines fetched: %d of %d" % (
                int(round(s.used)) if s.mode == "seq" else int(round(s.misses)),
                8 * max(1, int(round(s.misses)))), 11.5, INK, 700, mono=True)
        if s.req_a > 0.01:
            a = (CORE_X + 40, CORE_DESK - 70)
            b = level_center(int(s.req_to))
            x, y = bezier(a, ((a[0] + b[0]) / 2, 74), b, s.req_u)
            pill(p, x, y, "read", TEAL, PAPER, 10, opacity=s.req_a, shadow=None)
        if s.line_a > 0.01:
            a = level_center(int(s.line_from))
            b = (CORE_X + 40, CORE_DESK - 70)
            x, y = bezier(a, ((a[0] + b[0]) / 2, LEVEL_Y + LEVEL_H + 50), b, s.line_u)
            pill(p, x, y, "64-byte line", BRASS, BRASS_LT, 10, opacity=s.line_a, shadow=None)

        LOOPS.draw(p, 26, 300, W - 52, "sequential_sum and strided_sum", s, t, size=10.6,
                   lead=14.0, tint=RUST if s.mode == "scatter" else TEAL)
        caption(p, tl, t, CAP)
        progress(p, tl, t, total, RAIL)

    CAP, RAIL, height = layout(300, len(LOOPS), 14.0)
    return tl, draw, height


# ------------------------------------------------- 15.4: false sharing

CORES = [180, 640]
F_DESK = 190
MEM = (410, 254)


def false_sharing():
    tl = Timeline(caption="", kind="step", code=-1.0, mode="same", owner=-1, move_u=0.0,
                  move_a=0.0, move_from=0, transfers=0.0, a=0.0, b=0.0, inval=-1, clock="")

    def write(core, k=1.0, transfer=True):
        if transfer:
            tl.set(move_from=1 - core, move_u=0.0, inval=1 - core)
            tl.to(0.1, move_a=1.0)
            tl.to(0.7 * k, in_out, move_u=1.0)
            tl.to(0.1, move_a=0.0)
            tl.to(0.15, transfers=tl._at("transfers", tl.now) + 1)
        tl.set(owner=core, inval=-1, code=float(core))
        field = "a" if core == 0 else "b"
        tl.to(0.25 * k, **{field: tl._at(field, tl.now) + 1})

    tl.chapter("one line")
    tl.say("Thread 0 increments a, and thread 1 increments b. Both fields sit in one 64-byte line.")
    tl.wait(0.4)
    tl.say("To write, a core must hold the only copy of the line. Core 0 takes it and adds 1 to a.")
    tl.set(owner=0, code=0.0)
    tl.to(0.4, a=1.0)
    tl.wait(0.4)
    tl.say("Core 1 now writes b. Core 0's copy is invalidated, and the line moves to core 1.")
    write(1)
    tl.say("Core 0 writes a again, so the line moves back. Every write pays for a transfer.")
    write(0)
    for k in range(6):
        write(k % 2 == 0 and 1 or 0, 0.4)
    tl.say("The threads share no data, but they share a line. Two million writes each: 838 ms.",
           "fail")
    tl.wait(1.2)

    tl.chapter("padded")
    tl.say("Now each counter is aligned to 64 bytes, so each has a line of its own.")
    tl.set(mode="padded", owner=-1, transfers=0.0, a=0.0, b=0.0, code=2.0)
    tl.wait(0.4)
    tl.say("Each core keeps its own line in its own L1. No write invalidates the other core.")
    for k in range(8):
        tl.set(code=2.0 + k % 2)
        tl.to(0.25, a=float(k // 2 + 1) if k % 2 == 0 else tl._at("a", tl.now),
              b=float(k // 2 + 1) if k % 2 else tl._at("b", tl.now))
    tl.say("Zero transfers. The same writes took 170 ms, about five times faster.", "insight")
    tl.wait(1.6)

    def line_box(p, x, y, fields, held, faded=False):
        w = 200
        p.rect(x - w / 2, y - 22, w, 44, TEAL_LT if held else STAGE, TEAL if held else LINE, 6,
               1.6 if held else 1.0, opacity=0.35 if faded else 1.0)
        for k, (name, value) in enumerate(fields):
            fx = x - w / 2 + 12 + k * 64
            p.rect(fx, y - 14, 56, 28, PAPER, INK, 4, 1.0, opacity=0.35 if faded else 1.0)
            p.text(fx + 28, y + 5, "%s=%d" % (name, value), 11, INK, 700, "middle", mono=True,
                   opacity=0.35 if faded else 1.0)

    def draw(p, s, total):
        t = s.t
        title_block(p, "False sharing",
                    "Cores move whole 64-byte lines. Two counters in one line fight over it.")
        scoreboard(p, [("line transfers", int(round(s.transfers)), RUST)])
        for core, x in enumerate(CORES):
            robot(p, x, F_DESK, TEAL if core == 0 else NIGHT, 1.0, 1.0,
                  "core %d" % core, "thread %d" % core)
            p.text(x, F_DESK + 66, "L1", 11, MUTED, 600, "middle")
            if s.mode == "same":
                held = int(s.owner) == core
                if held or int(s.inval) == core:
                    line_box(p, x, F_DESK + 96, [("a", int(s.a)), ("b", int(s.b))], held,
                             faded=not held)
                    if int(s.inval) == core:
                        p.text(x, F_DESK + 132, "invalidated", 10.5, RUST, 700, "middle")
            else:
                field = ("a", int(s.a)) if core == 0 else ("b", int(s.b))
                line_box(p, x, F_DESK + 96, [field], True)
        if s.move_a > 0.01:
            a = (CORES[int(s.move_from)], F_DESK + 96)
            b = (CORES[1 - int(s.move_from)], F_DESK + 96)
            x, y = bezier(a, ((a[0] + b[0]) / 2, F_DESK + 30), b, s.move_u)
            pill(p, x, y, "line a,b", RUST, RUST_LT, 10.5, opacity=s.move_a, shadow=None)

        SHARING.draw(p, 26, 340, W - 52, s, t, size=10.6, lead=14.0,
                     tint=TEAL if s.mode == "padded" else RUST)
        caption(p, tl, t, CAP)
        progress(p, tl, t, total, RAIL)

    CAP, RAIL, height = layout(340, len(SHARING), 14.0)
    return tl, draw, height


def build_mem_hierarchy(only=None):
    tl, draw, height = mem_hierarchy()
    return render("ch15-mem-hierarchy.gif", tl, draw, height, only=only)


def build_false_sharing(only=None):
    tl, draw, height = false_sharing()
    return render("ch15-false-sharing.gif", tl, draw, height, only=only)


BUILDERS = {
    "mem-hierarchy": build_mem_hierarchy,
    "false-sharing": build_false_sharing,
}
