#!/usr/bin/env python3
"""Every animation in the book, written to src/figures/.

Each builder scripts one run from the book on a `motion` timeline and draws
it. `render` writes three files per animation: a GIF, an MP4 of the same
frames, and a JSON step list that the HTML book uses for its step buttons.
The stage is 520 units wide, so the text stays readable on a phone.

    python3 tools/animations.py              # every animation
    python3 tools/animations.py ring-sleep   # some of them

After a render, `python3 tools/anim_markup.py` points the chapters at the new
videos. `make animations` runs both.
"""

import sys

from art import crab, gopher
from motion import (BRASS, BRASS_LT, FAINT, INK, LINE, MUTED, NIGHT, OUT, PAPER, TEAL, TEAL_LT, Timeline,
                    caption, clamp, progress, render, robot, scoreboard, title_block, zzz)


# --------------------------------------------------------------- chapter 1

def ring_sleep():
    """The small ring of chapter 1 with a writer and a reader on it: the
    calls of handpipe's first experiment, then the rest of the writer's 30
    bytes, the close, and the read that returns 0."""
    tl = Timeline(caption="", kind="step", head=0.0, tail=0.0, w_awake=1.0, r_awake=1.0, w_lit=1.0,
                  w_sub="", r_sub="", o0=0.0, o1=0.0, o2=0.0, o3=0.0, l0=0.0, l1=0.0, l2=0.0, l3=0.0)

    def put(slot, length, new=True):
        """The writer's bytes arrive in one page."""
        tl.to(0.6, **{"l%d" % slot: float(length)})

        if new:
            tl.set(head=tl.sample(tl.end()).head + 1)

    def take(slot, upto, frees=False):
        """The reader's bytes leave one page, from the front."""
        s = tl.sample(tl.end())
        gone = upto - s["o%d" % slot]
        tl.to(0.6, **{"o%d" % slot: float(upto), "l%d" % slot: s["l%d" % slot] - gone})

        if frees:
            tl.set(tail=s.tail + 1, **{"o%d" % slot: 0.0})

    tl.chapter("put")
    tl.say("The writer puts 12 bytes. Page 0 takes 8 of them and page 1 takes 4.")
    tl.set(w_sub="write 12")
    put(0, 8)
    put(1, 4)
    tl.wait(0.6)

    tl.chapter("take")
    tl.say("The reader takes 3 bytes from page 0, the oldest. Page 0 still holds 5.")
    tl.set(r_sub="read 3")
    take(0, 3)
    tl.wait(0.6)

    tl.chapter("full")
    tl.say("The writer puts 30. Page 1 takes 4 more, and pages 2 and 3 take 8 each.")
    tl.set(w_sub="write 30")
    put(1, 8, new=False)
    put(2, 8)
    put(3, 8)
    tl.say("Every slot is in use, and 10 bytes are still to go. The writer sleeps.", "fail")
    tl.set(w_sub="10 bytes left")
    tl.to(0.5, w_awake=0.0)
    tl.wait(0.8)

    tl.chapter("wake")
    tl.say("The reader takes 5 more. Page 0 is empty, so slot 0 is free again.")
    tl.set(r_sub="read 5")
    take(0, 8, frees=True)
    tl.say("The reader wakes the writer, which puts 8 bytes in slot 0. The ring has wrapped.", "insight")
    tl.to(0.4, w_awake=1.0)
    put(0, 8)
    tl.set(w_sub="2 bytes left")
    tl.to(0.4, w_awake=0.0)
    tl.wait(0.6)
    tl.say("The reader takes 8. Slot 1 is free, and the writer's last 2 bytes go in.")
    tl.set(r_sub="read 8")
    take(1, 8, frees=True)
    tl.to(0.4, w_awake=1.0)
    put(1, 2)
    tl.set(w_sub="write returned 30")
    tl.wait(0.6)

    tl.chapter("end")
    tl.say("The writer closes its end. The reader takes the 26 bytes that remain.")
    tl.set(w_sub="closed")
    tl.to(0.4, w_lit=0.0)
    tl.set(r_sub="read 26")
    take(2, 8, frees=True)
    take(3, 8, frees=True)
    take(0, 8, frees=True)
    take(1, 2, frees=True)
    tl.say("The ring is empty and no writer is left, so the next read returns 0.", "insight")
    tl.set(r_sub="read returned 0")
    tl.wait(1.6)

    def draw(p, s, total):
        t = s.t
        head, tail = round(s.head), round(s.tail)
        title_block(p, "Sleep and wake on a ring", "4 pages of 8 bytes. Each square is 1 byte.")
        scoreboard(p, [("head", head, TEAL), ("tail", tail, BRASS)])

        with p.group(opacity=0.35 + 0.65 * s.w_lit):
            p.add(crab(120, 208, 0.62, "happy" if s.w_awake >= 0.5 else "sleepy", look=1))

        p.add(gopher(400, 212, 0.56, look=-1))

        for x, name, sub in ((120, "writer", s.w_sub), (400, "reader", s.r_sub)):
            p.text(x, 236, name, 14, INK, 600, "middle")
            p.text(x, 253, sub, 11.5, MUTED, 400, "middle", mono=True)

        for slot in range(4):
            x, y = 40 + 112 * slot, 278
            offset, length = s["o%d" % slot], s["l%d" % slot]
            edge, width, mark = LINE, 1.3, ""

            if head != tail and slot == (head - 1) % 4:
                edge, width, mark = TEAL, 2.4, "newest"

            if head != tail and slot == tail % 4:
                edge, width, mark = BRASS, 2.4, "oldest"

            p.rect(x, y, 104, 30, PAPER, edge, 6, width)
            p.text(x + 52, y - 8, "slot %d" % slot, 11, MUTED, 600, "middle")

            for cell in range(8):
                filled = clamp(min(cell + 1.0, offset + length) - max(float(cell), offset))
                p.rect(x + 6 + 11.5 * cell, y + 6, 9.5, 18, "#eef2f5", "none", 2)

                if filled > 0.01:
                    p.rect(x + 6 + 11.5 * cell, y + 6, 9.5, 18, TEAL, "none", 2, opacity=filled)

            if mark:
                p.text(x + 52, y + 46, mark, 11, edge, 700, "middle")

        caption(p, tl, t, 340)
        progress(p, tl, t, total, 430)

    return tl, draw, 462


# --------------------------------------------------------------- chapter 6

def cfs_pick():
    """The first 12 slices of `cfs` for A and B at nice 0 and C at nice 5: the
    task with the smallest virtual runtime runs, and C is charged 3.06 ms for
    each millisecond."""
    tl = Timeline(caption="", kind="step", va=0.0, vb=0.0, vc=0.0, hot="", seq="")
    v = {"A": 0.0, "B": 0.0, "C": 0.0}
    charge = {"A": 1.0, "B": 1.0, "C": 1024 / 335}
    order = []

    def tick(k=1.0):
        name = min(v, key=lambda n: (round(v[n], 6), n))
        v[name] += charge[name]
        order.append(name)
        tl.set(hot=name)
        tl.wait(0.25 * k)
        tl.to(0.55 * k, **{"v" + name.lower(): v[name]})
        tl.set(seq=" ".join(order))
        tl.wait(0.2 * k)

    tl.chapter("start")
    tl.say("A, B and C start at 0. A runs for 1 ms, and its vruntime becomes 1.00.")
    tick()
    tl.say("B now has the smallest vruntime, so B runs. Then C runs.")
    tick()
    tl.chapter("weight")
    tl.say("C has weight 335. For 1 ms of running it is charged 1024 / 335 = 3.06 ms.", "insight")
    tick(1.6)
    tl.wait(0.8)
    tl.chapter("catch up")
    tl.say("A and B take turns until their vruntime passes 3.06. C waits at the back.")

    for _ in range(6):
        tick(0.7)

    tl.chapter("again")
    tl.say("C is the smallest again and runs: its second slice, against 4 each for A and B.")
    tick(1.4)
    tl.say("The pattern repeats. Over time the shares follow the weights 1024 : 1024 : 335.", "insight")
    tick(0.7)
    tick(0.7)
    tl.set(hot="")
    tl.wait(1.6)

    def draw(p, s, total):
        t = s.t
        title_block(p, "The smallest vruntime runs next", "Slices of 1 ms. A and B have nice 0, C has nice 5.")
        rows = [("A", "weight 1024", s.va), ("B", "weight 1024", s.vb), ("C", "weight 335", s.vc)]

        for k, (name, sub, value) in enumerate(rows):
            y = 92 + 58 * k
            hot = s.hot == name
            p.rect(26, y, 468, 46, TEAL_LT if hot else PAPER, TEAL if hot else LINE, 8, 2.2 if hot else 1.3)
            p.text(42, y + 22, name, 17, INK, 700)
            p.text(42, y + 38, sub, 10.5, MUTED, 500)
            p.rect(128, y + 13, 290, 20, "#eef2f5", "none", 4)

            if value > 0.01:
                p.rect(128, y + 13, 290 * value / 7.0, 20, TEAL if hot else NIGHT, "none", 4)

            p.text(482, y + 28, "%.2f" % value, 13, INK, 700, "end", mono=True)

        p.text(26, 286, "order of slices", 11, MUTED, 600)
        p.rect(26, 294, 468, 34, "#fbfcfd", LINE, 8, 1.3)
        p.text(40, 316, s.seq, 14, INK, 700, mono=True)
        caption(p, tl, t, 344)
        progress(p, tl, t, total, 434)

    return tl, draw, 466


# --------------------------------------------------------------- chapter 9

def epoll_ready():
    """The epoll model of chapter 9 with 6 level-triggered pipes: writes put
    pipes on the ready list, a wait returns them, and a pipe that still has
    data goes back on the list."""
    tl = Timeline(caption="", kind="step", b1=0.0, b4=0.0, ready="", returned="", asleep=0.0)

    tl.chapter("")
    tl.say("6 pipes are registered. The ready list is empty, so a wait would sleep.")
    tl.to(0.5, asleep=1.0)
    tl.wait(0.8)

    tl.chapter("writes")
    tl.say("A write of 5 bytes to pipe 4 puts it on the ready list and wakes the loop.")
    tl.to(0.4, b4=5.0)
    tl.set(ready="4")
    tl.to(0.3, asleep=0.0)
    tl.say("Before the loop runs, 3 bytes arrive on pipe 1. It joins the list behind pipe 4.")
    tl.to(0.4, b1=3.0)
    tl.set(ready="4 1")
    tl.wait(0.6)

    tl.chapter("wait")
    tl.say("epoll_wait returns pipes 4 and 1. It examined 2 entries, and the other 4 pipes cost nothing.", "insight")
    tl.set(returned="4 1")
    tl.wait(1.0)
    tl.say("The handler reads 4 bytes from each. Pipe 1 is empty now. Pipe 4 has 1 byte left.")
    tl.to(0.5, b4=1.0)
    tl.to(0.5, b1=0.0)
    tl.wait(0.6)

    tl.chapter("again")
    tl.say("Both are level-triggered, so both stayed on the list. The next wait checks them again.")
    tl.set(returned="")
    tl.wait(1.0)
    tl.say("Pipe 1 has no data and is dropped. Pipe 4 is reported, and the handler reads its last byte.")
    tl.set(returned="4", ready="4")
    tl.to(0.5, b4=0.0)
    tl.wait(0.6)

    tl.chapter("idle")
    tl.say("The next wait drops pipe 4 as well. No pipe is ready, and the loop sleeps in epoll_wait.")
    tl.set(ready="", returned="")
    tl.to(0.5, asleep=1.0)
    tl.wait(1.6)

    def draw(p, s, total):
        t = s.t
        title_block(p, "The ready list of epoll", "6 pipes registered, all level-triggered.")
        listed = s.ready.split()
        p.text(26, 92, "interest list", 11, MUTED, 600)

        for k in range(6):
            x = 26 + 79 * k
            buffered = {1: s.b1, 4: s.b4}.get(k, 0.0)
            hot = str(k) in listed
            p.rect(x, 100, 73, 58, TEAL_LT if hot else PAPER, TEAL if hot else LINE, 8, 2.2 if hot else 1.3)
            p.text(x + 36.5, 124, "pipe %d" % k, 13, INK, 700, "middle")
            p.text(x + 36.5, 144, "%d bytes" % round(buffered), 11, TEAL if buffered > 0.5 else FAINT, 600, "middle",
                   mono=True)

        p.text(26, 190, "ready list", 11, MUTED, 600)
        p.rect(26, 198, 228, 46, "#fbfcfd", LINE, 8, 1.3)

        for k, name in enumerate(listed):
            p.rect(38 + 62 * k, 206, 54, 30, TEAL_LT, TEAL, 6, 1.6)
            p.text(65 + 62 * k, 226, "pipe " + name, 11.5, TEAL, 700, "middle")

        p.text(266, 190, "returned by epoll_wait", 11, MUTED, 600)
        p.rect(266, 198, 228, 46, BRASS_LT if s.returned else "#fbfcfd", BRASS if s.returned else LINE, 8, 1.3)
        p.text(280, 227, s.returned.replace(" ", ", ") if s.returned else "", 15, INK, 700, mono=True)

        if s.asleep > 0.01:
            p.text(380, 227, "the loop sleeps", 12, NIGHT, 600, "middle", opacity=s.asleep)
            zzz(p, 462, 226, t, s.asleep)

        caption(p, tl, t, 266)
        progress(p, tl, t, total, 356)

    return tl, draw, 388


def build(name, script):
    def run(only=None):
        tl, draw, height = script()

        return render(name + ".gif", tl, draw, height, only=only)

    return run


MOTION = {
    "ring-sleep": build("ring-sleep", ring_sleep),
    "cfs-pick": build("cfs-pick", cfs_pick),
    "epoll-ready": build("epoll-ready", epoll_ready),
}


def main(argv):
    names = argv or list(MOTION)
    unknown = [n for n in names if n not in MOTION]

    if unknown:
        print("unknown animation(s): %s" % ", ".join(unknown), file=sys.stderr)
        print("available: %s" % ", ".join(MOTION), file=sys.stderr)

        return 2

    for name in names:
        MOTION[name]()

    print("wrote %d animation(s) to %s" % (len(names), OUT))

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
