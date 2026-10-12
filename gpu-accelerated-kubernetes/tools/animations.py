#!/usr/bin/env python3
"""Every animation in the book, written to src/figures/.

Each builder scripts one run of a program from the book on a `motion`
timeline and draws it. `render` writes three files per animation: a GIF, an
MP4 of the same frames, and a JSON step list that the HTML book uses for its
step buttons.

    python3 tools/animations.py              # every animation
    python3 tools/animations.py work-queue   # some of them

After a render, `python3 tools/anim_markup.py` points the chapters at the new
videos. `make animations` runs both.
"""

import sys

from motion import (BRASS, BRASS_LT, FAINT, INK, LINE, MUTED, NIGHT, NIGHT_LT, OUT, PAPER, RUST,
                    RUST_LT, STAGE, TEAL, TEAL_LT, W, Timeline, caption, chip, clamp, focus, in_out,
                    lerp, linear, meter, pill, progress, render, robot, scoreboard, title_block, zzz)


def panel(p, x, y, w, h, title, edge=LINE, fill="#fbfcfd"):
    """A titled box that holds one part of the system."""
    p.rect(x, y, w, h, fill, edge, 8, 1.3)
    p.text(x + 12, y + 19, title, 11, MUTED, 600)


# --------------------------------------------------------------- chapter 1

def list_watch():
    """The run of `informer` from chapter 1: list, watch, a dropped watch, and a
    partition that ends in 410 Gone and a second list. The versions and the
    objects are the ones in code/output/go-informer.txt."""
    tl = Timeline(caption="", kind="step", sver=2.0, sa="spec 1  status 0  v1", sb="spec 8  status 0  v2",
                  sb_a=1.0, ca="", cb="", ca_a=0.0, cb_a=0.0, resume="", link=0.0, cut="none",
                  compacted=0.0, stale=0.0, fly_u=0.0, fly_a=0.0, fly_label="", fly_dir=1.0,
                  fly_kind="event", mark=0.0)

    def fly(label, kind="event", direction=1.0, k=1.0):
        tl.set(fly_label=label, fly_kind=kind, fly_dir=direction, fly_u=0.0)
        tl.to(0.12, fly_a=1.0)
        tl.to(0.7 * k, in_out, fly_u=1.0)
        tl.to(0.12, fly_a=0.0)

    def write(version, a=None, b=None, k=1.0):
        """One write on the server, and the event that carries it to the cache."""
        tl.set(sver=float(version), **({"sa": a} if a else {}), **({"sb": b} if b else {}))
        tl.wait(0.25 * k)
        fly("event %d" % version, k=k)
        tl.set(resume=str(version), **({"ca": a} if a else {}), **({"cb": b} if b else {}))
        tl.wait(0.2 * k)

    tl.chapter("list")
    tl.say("The server holds two jobs and has numbered two writes. The reflector starts with an empty cache.")
    tl.wait(0.8)
    tl.say("It lists. The answer carries both jobs and the version of the snapshot, 2.")
    fly("list", "ask", -1.0)
    fly("2 jobs at version 2", "event", 1.0, 1.3)
    tl.set(ca="spec 1  status 0  v1", cb="spec 8  status 0  v2", resume="2")
    tl.to(0.4, ca_a=1.0, cb_a=1.0)
    tl.chapter("watch")
    tl.say("It opens a watch from version 2. From here on, the server sends one event for each write.")
    fly("watch from 2", "ask", -1.0)
    tl.to(0.4, link=1.0)
    tl.say("The controller writes each job's status. Each write takes the next version and returns as an event.")
    write(3, a="spec 1  status 1  v3")
    write(4, b="spec 8  status 8  v4")
    tl.say("A user edits job-a five times. Events 5 to 9 arrive, then the status write as event 10.")

    for n in range(5):
        write(5 + n, a="spec %d  status 1  v%d" % (2 + n, 5 + n), k=0.55 if n else 1.0)

    write(10, a="spec 6  status 6  v10")
    tl.say("The cache now equals the server, and the reflector remembers 10, the last event it applied.",
           "insight")
    tl.wait(1.0)

    tl.chapter("drop")
    tl.say("The server closes the watch. Nothing was written meanwhile.")
    tl.set(cut="drop")
    tl.to(0.4, link=0.0)
    tl.wait(0.6)
    tl.say("The reflector opens a new watch from 10. The server has nothing to replay, and no list is needed.")
    fly("watch from 10", "ask", -1.0)
    tl.set(cut="none")
    tl.to(0.4, link=1.0)

    tl.chapter("partition")
    tl.say("The network fails. The reflector's attempts to connect get no answer.", "fail")
    tl.set(cut="partition")
    tl.to(0.4, link=0.0)
    tl.wait(0.8)
    tl.say("Meanwhile job-b is deleted at version 11. No event reaches the cache, which still holds job-b.",
           "fail")
    tl.set(sver=11.0)
    tl.to(0.5, sb_a=0.0)
    tl.to(0.4, stale=1.0)
    tl.say("The server compacts its history through version 11. The deletion event no longer exists.", "fail")
    tl.to(0.6, compacted=11.0)
    tl.wait(0.6)
    tl.chapter("410 Gone")
    tl.say("The network heals. The reflector asks to watch from 10, and the server answers 410 Gone.")
    tl.set(cut="none")
    fly("watch from 10", "ask", -1.0)
    fly("410 Gone", "gone", 1.0, 1.3)
    tl.say("So it lists again. The new list, at version 11, holds only job-a.")
    fly("list", "ask", -1.0)
    fly("1 job at version 11", "event", 1.0, 1.3)
    tl.set(resume="11")
    tl.say("job-b is in the old cache and missing from the list. Replace reports its name, and the "
           "controller releases its GPUs.", "insight")
    tl.to(0.5, mark=1.0)
    tl.to(0.6, cb_a=0.0, stale=0.0)
    tl.to(0.3, mark=0.0)
    fly("watch from 11", "ask", -1.0)
    tl.to(0.4, link=1.0)
    tl.wait(1.4)

    def draw(p, s, total):
        t = s.t
        title_block(p, "List, then watch",
                    "The reflector keeps a copy of the server's objects, exact up to the last event it applied.")
        sx, cx, top, pw, ph = 26, 494, 80, 300, 190
        panel(p, sx, top, pw, ph, "API server")
        p.text(sx + pw - 12, top + 19, "version %d" % round(s.sver), 12, INK, 700, "end", mono=True)
        panel(p, cx, top, pw, ph, "reflector and cache")

        if s.resume:
            p.text(cx + pw - 12, top + 19, "applied up to %s" % s.resume, 12, TEAL, 700, "end", mono=True)

        def row(x, y, name, body, opacity, edge=LINE, fill=PAPER):
            if opacity <= 0.01:
                return

            with p.group(opacity=opacity):
                p.rect(x + 12, y, pw - 24, 30, fill, edge, 6, 1.2)
                p.text(x + 22, y + 20, name, 12, INK, 700, mono=True)
                p.text(x + 78, y + 20, body, 11.5, MUTED, 500, mono=True)

        row(sx, top + 32, "job-a", s.sa, 1.0)
        row(sx, top + 68, "job-b", s.sb, s.sb_a)
        row(cx, top + 32, "job-a", s.ca, s.ca_a)
        row(cx, top + 68, "job-b", s.cb, s.cb_a, mix_edge(s.stale), mix_fill(s.stale))

        if s.stale > 0.5 and s.cb_a > 0.5:
            p.text(cx + pw - 22, top + 115, "deleted on the server", 10.5, RUST, 600, "end")

        focus(p, cx + 12, top + 68, pw - 24, 30, s.mark, BRASS, 5)

        # The server's record of recent events, oldest on the left.
        p.text(sx + 12, top + 132, "recent events", 10.5, MUTED, 600)
        newest = int(round(s.sver))

        for k, version in enumerate(range(max(1, newest - 7), newest + 1)):
            gone = version <= s.compacted + 0.5
            x = sx + 12 + k * 34
            p.rect(x, top + 142, 30, 26, "#eef2f5" if gone else TEAL_LT, FAINT if gone else TEAL, 5, 1.1)
            p.text(x + 15, top + 160, str(version), 11.5, FAINT if gone else INK, 700, "middle", mono=True)

            if gone:
                p.line(x + 5, top + 163, x + 25, top + 147, FAINT, 1.3)

        if s.compacted > 0.5:
            p.text(sx + 12, top + 184, "compacted through %d" % round(s.compacted), 10.5, RUST, 600)


        # The connection, and whatever is travelling along it.
        y = top + 96
        x0, x1 = sx + pw + 8, cx - 8

        if s.cut == "partition":
            p.line(x0, y, x1, y, RUST, 2.0, dash="3 7", opacity=0.9)
            p.text((x0 + x1) / 2, y - 12, "no route", 11, RUST, 700, "middle")
        elif s.link > 0.02:
            p.line(x0, y, x1, y, TEAL, 2.4, opacity=s.link)
            p.text((x0 + x1) / 2, y - 12, "watch open", 11, TEAL, 600, "middle", opacity=s.link)
        else:
            p.line(x0, y, x1, y, FAINT, 1.6, dash="5 6")

            if s.cut == "drop":
                p.text((x0 + x1) / 2, y - 12, "watch closed", 11, MUTED, 600, "middle")

        if s.fly_a > 0.01:
            a, b = (x0 + 30, x1 - 30) if s.fly_dir > 0 else (x1 - 30, x0 + 30)
            color, fill = {"ask": (NIGHT, NIGHT_LT), "gone": (RUST, RUST_LT)}.get(s.fly_kind, (TEAL, TEAL_LT))
            pill(p, lerp(a, b, s.fly_u), y + 36, s.fly_label, color, fill, 10.5, opacity=s.fly_a, shadow=None)

        caption(p, tl, t, 292)
        progress(p, tl, t, total, 382)

    return tl, draw, 412


def mix_edge(stale):
    return RUST if stale > 0.5 else LINE


def mix_fill(stale):
    return RUST_LT if stale > 0.5 else PAPER


def work_queue():
    """The work queue from chapter 1: one name through Add, Get, Add, Add, Done,
    as in the chapter's table, then the same calls on a queue that has no
    `processing` set."""
    tl = Timeline(caption="", kind="step", call="", ready=0.0, dirty=0.0, proc=0.0, mode="queue",
                  w1=0.0, w2=0.0, w2_show=0.0, mark="", spec="1", reconciles=0.0, held=0.0)

    def call(name):
        tl.set(call=name)
        tl.wait(0.5)

    tl.chapter("Add")
    tl.say("The queue keeps a list of names that are ready, and two sets: dirty and processing.")
    tl.wait(0.8)
    tl.say("Add(job-a). The name is new, so it goes into dirty and onto the ready list.")
    call("Add(job-a)")
    tl.set(mark="ready")
    tl.to(0.5, ready=1.0, dirty=1.0)
    tl.chapter("Get")
    tl.say("Get(). The worker takes the name. It leaves ready and dirty and enters processing.")
    call("Get() -> job-a")
    tl.set(mark="proc")
    tl.to(0.5, ready=0.0, dirty=0.0, proc=1.0, w1=1.0)
    tl.say("The worker reads job-a from the cache, with a spec of 2 GPUs, and starts 20 ms of work.")
    tl.set(spec="2")
    tl.wait(0.8)
    tl.chapter("Add while held")
    tl.say("The user edits job-a again. Add(job-a) finds the name in processing: it marks the name "
           "dirty and leaves ready empty.")
    call("Add(job-a)")
    tl.set(mark="dirty", spec="3")
    tl.to(0.5, dirty=1.0, held=1.0)
    tl.say("Three more edits, three more Add calls. The name is already dirty, so nothing changes.")

    for spec in ("4", "5", "6"):
        tl.set(call="Add(job-a)", spec=spec)
        tl.wait(0.7)

    tl.chapter("Done")
    tl.say("Done(job-a). The worker hands the name back. It is still dirty, so it goes onto ready again.")
    call("Done(job-a)")
    tl.set(mark="ready", reconciles=1.0)
    tl.to(0.5, proc=0.0, w1=0.0, ready=1.0, held=0.0)
    tl.say("The second reconcile reads a spec of 6 GPUs. Five edits cost two reconciles, one at a time.",
           "insight")
    call("Get() -> job-a")
    tl.set(mark="proc")
    tl.to(0.5, ready=0.0, dirty=0.0, proc=1.0, w1=1.0)
    tl.wait(0.8)
    tl.set(call="Done(job-a)", reconciles=2.0, mark="")
    tl.to(0.5, proc=0.0, w1=0.0)
    tl.wait(1.2)

    tl.chapter("no processing set")
    tl.say("The same calls on a queue with no processing set, and two workers.", "fail")
    tl.set(mode="bare", call="", ready=0.0, dirty=0.0, proc=0.0, w1=0.0, w2=0.0, reconciles=0.0,
           spec="1", mark="")
    tl.to(0.4, w2_show=1.0)
    call("Add(job-a)")
    tl.to(0.4, ready=1.0, dirty=1.0)
    call("Get() -> job-a")
    tl.to(0.4, ready=0.0, dirty=0.0, w1=1.0)
    tl.set(spec="2")
    tl.say("An edit arrives while worker 1 is busy. Nothing records that the name is held, so it "
           "becomes ready.", "fail")
    call("Add(job-a)")
    tl.set(spec="3")
    tl.to(0.4, ready=1.0, dirty=1.0)
    tl.say("Worker 2 takes it. Two workers now act on job-a at once, and each starts a container.", "fail")
    call("Get() -> job-a")
    tl.to(0.4, ready=0.0, dirty=0.0, w2=1.0)
    tl.wait(1.8)

    def draw(p, s, total):
        t = s.t
        title_block(p, "A queue of names",
                    "One name, five edits. The sets decide when a worker may take the name.")
        scoreboard(p, [("spec.GPUs", s.spec, INK), ("reconciles", int(round(s.reconciles)), TEAL)])

        if s.call:
            p.text(26, 92, "call", 11, MUTED, 600)
            chip(p, 62, 88, s.call, NIGHT, NIGHT_LT, 12.5, anchor="start")

        boxes = [("ready", "ready, a list", 26, s.ready), ("dirty", "dirty, a set", 290, s.dirty),
                 ("proc", "processing, a set", 554, s.proc)]

        for key, title, x, held in boxes:
            bare = s.mode == "bare" and key == "proc"
            panel(p, x, 112, 240, 78, title, RUST if bare else LINE, "#fdf3ee" if bare else "#fbfcfd")

            if bare:
                p.line(x + 12, 128, x + 12 + 118, 128, RUST, 1.6)
                p.text(x + 120, 160, "removed", 12, RUST, 700, "middle")
            elif held > 0.01:
                chip(p, x + 120, 158, "job-a", TEAL, TEAL_LT, 13, opacity=clamp(held))

            if s.mark == key and not bare:
                focus(p, x, 112, 240, 78, 1.0, BRASS, 4)

        if s.held > 0.5:
            p.text(410, 206, "held back: a worker has it", 11, BRASS, 700, "middle")

        two = s.w2_show > 0.5
        x1 = 300 if two else 410
        robot(p, x1, 330, TEAL, 1.0, s.w1, "worker 1" if two else "worker",
              "reconcile(job-a)" if s.w1 > 0.5 else "waiting in Get()")

        if s.w1 > 0.5:
            chip(p, x1 + 78, 262, "job-a", TEAL, TEAL_LT, 12)

        if two:
            with p.group(opacity=clamp(s.w2_show)):
                robot(p, 540, 330, RUST, 1.0, s.w2, "worker 2",
                      "reconcile(job-a)" if s.w2 > 0.5 else "waiting in Get()")

                if s.w2 > 0.5:
                    chip(p, 618, 262, "job-a", RUST, RUST_LT, 12)

        caption(p, tl, t, 396)
        progress(p, tl, t, total, 486)

    return tl, draw, 516


# --------------------------------------------------------------- chapter 3

def lease_expiry():
    """The run from chapter 3: gpu-host-b renews its Lease every two seconds,
    is killed at 18:31:25, and starts again at 18:31:39. The watcher measures
    the silence on its own clock. A last part compares the two clocks instead."""
    tl = Timeline(caption="", kind="step", clock=16.0, renew="18:31:16", alive=1.0, fly_u=0.0, fly_a=0.0,
                  seen="18:31:16", silence=0.0, state="renewing", mode="observe", skew=0.0, flash=0.0)

    def tick(second, k=1.0):
        """Two seconds pass; the agent renews at `second` and the watcher sees it."""
        tl.also(0.9 * k, linear, clock=float(second), silence=2.0)
        tl.wait(0.9 * k)
        tl.set(fly_u=0.0)
        tl.to(0.08, fly_a=1.0)
        tl.to(0.4 * k, in_out, fly_u=1.0)
        tl.to(0.08, fly_a=0.0)
        stamp = "18:31:%02d" % second
        tl.set(renew=stamp, seen=stamp, silence=0.0, state="renewing")

    tl.chapter("renewals")
    tl.say("The agent for gpu-host-b writes the current time into its Lease every two seconds.")
    tick(18)
    tl.say("The watcher notes its own clock each time renewTime changes, and counts the seconds since.")
    tick(20)
    tick(22, 0.7)
    tick(24, 0.7)
    tl.chapter("kill -9")
    tl.say("At 18:31:25 the agent is killed. It writes nothing more, and renewTime stays at 18:31:24.", "fail")
    tl.to(0.5, linear, clock=25.0, silence=1.0)
    tl.to(0.3, alive=0.0)
    tl.say("The watcher's count keeps rising. The Lease lasts six seconds after a renewal.")
    tl.to(3.6, linear, clock=30.0, silence=6.0)
    tl.chapter("expired")
    tl.say("At 18:31:31 the count passes six. The watcher reports gpu-host-b as expired, once.", "insight")
    tl.to(0.7, linear, clock=31.0, silence=7.0)
    tl.set(state="expired")
    tl.to(0.3, flash=1.0)
    tl.wait(1.0)
    tl.to(2.4, linear, clock=38.0, silence=14.0)
    tl.chapter("back")
    tl.say("At 18:31:39 the agent starts again and renews at once. The watcher reports it as renewing again.")
    tl.to(0.4, linear, clock=39.0, silence=15.0)
    tl.to(0.3, alive=1.0, flash=0.0)
    tl.set(fly_u=0.0)
    tl.to(0.08, fly_a=1.0)
    tl.to(0.5, in_out, fly_u=1.0)
    tl.to(0.08, fly_a=0.0)
    tl.set(renew="18:31:39", seen="18:31:39", silence=0.0, state="renewing")
    tl.wait(1.4)

    tl.chapter("comparing clocks")
    tl.say("A watcher that subtracts renewTime from its own clock depends on both clocks agreeing.", "fail")
    tl.set(mode="compare", clock=16.0, renew="18:31:16", seen="18:31:16", silence=0.0, state="renewing",
           alive=1.0)
    tl.wait(0.8)
    tl.say("Suppose the host's clock runs eight seconds behind. The agent renews on time, every two seconds.",
           "fail")
    tl.to(0.6, skew=8.0)
    tl.set(renew="18:31:08", silence=8.0)

    for second in (18, 20):
        tl.also(0.9, linear, clock=float(second))
        tl.wait(0.9)
        tl.set(fly_u=0.0)
        tl.to(0.08, fly_a=1.0)
        tl.to(0.4, in_out, fly_u=1.0)
        tl.to(0.08, fly_a=0.0)
        tl.set(renew="18:31:%02d" % (second - 8))

    tl.say("Each renewTime is already eight seconds old on the watcher's clock. A healthy host looks expired.",
           "fail")
    tl.set(state="expired")
    tl.to(0.3, flash=1.0)
    tl.wait(1.8)

    def draw(p, s, total):
        t = s.t
        compare = s.mode == "compare"
        title_block(p, "A Lease that stops being renewed",
                    "The watcher measures silence on its own clock. renewTime only has to change.")
        scoreboard(p, [("watcher's clock", "18:31:%02d" % int(s.clock), INK)])

        robot(p, 120, 250, TEAL if s.alive > 0.5 else "#8a97a5", s.alive, s.alive, "leaseagent",
              "gpu-host-b")
        zzz(p, 150, 150, t, 0.0)

        if s.alive < 0.5:
            p.text(120, 124, "killed", 12, RUST, 700, "middle")

        if s.skew > 0.5:
            p.text(120, 124, "its clock: 18:31:%02d" % int(s.clock - s.skew), 11.5, RUST, 700, "middle",
                   mono=True)

        panel(p, 262, 96, 250, 150, "Lease fleet/gpu-host-b")
        rows = [("holderIdentity", "gpu-host-b", MUTED), ("leaseDurationSeconds", "6", MUTED),
                ("renewTime", s.renew, INK)]

        for k, (name, value, color) in enumerate(rows):
            y = 142 + k * 30
            p.text(274, y, name, 11, MUTED, 500, mono=True)
            p.text(500, y, value, 11.5, color, 700, "end", mono=True)

        started, _ = s.timeline.changed("renew", t)
        focus(p, 268, 188, 238, 26, clamp(1 - (t - started) / 0.6) if started > 0 else 0.0, TEAL, 2)

        if s.fly_a > 0.01:
            pill(p, lerp(196, 262, s.fly_u), 200, "renew", TEAL, TEAL_LT, 10.5, opacity=s.fly_a, shadow=None)

        expired = s.state == "expired"
        robot(p, 700, 250, RUST if expired else NIGHT, 1.0, 1.0, "leasewatch",
              "compares the clocks" if compare else "counts on its own clock")
        panel(p, 548, 96, 104, 150, "it noted" if not compare else "it computes",
              RUST if expired else LINE, "#fdf3ee" if expired else "#fbfcfd")

        if compare:
            p.text(600, 146, "now -", 11, MUTED, 500, "middle", mono=True)
            p.text(600, 164, "renewTime", 11, MUTED, 500, "middle", mono=True)
        else:
            p.text(600, 146, "change at", 11, MUTED, 500, "middle")
            p.text(600, 164, s.seen, 11.5, INK, 700, "middle", mono=True)

        p.text(600, 204, "%d s" % int(s.silence), 20, RUST if s.silence > 6 else INK, 700, "middle",
               mono=True)
        p.text(600, 226, "of 6 s", 10.5, MUTED, 500, "middle")
        meter(p, 262, 276, 250, s.silence / 6.0, RUST if s.silence > 6 else TEAL, "seconds without a renewal",
              "%d of 6" % min(int(s.silence), 99))

        if s.flash > 0.01:
            chip(p, 728, 104, "expired" if not compare else "expired (wrongly)", RUST, RUST_LT, 12,
                 opacity=clamp(s.flash))

        caption(p, tl, t, 318)
        progress(p, tl, t, total, 408)

    return tl, draw, 438


# --------------------------------------------------------------- chapter 7

def ring_allreduce():
    """The run of `allreduce` from chapter 7: chunk 0 of five gradients summed
    around a ring of five Thors, and then the same step with thor-3 failing
    after two exchanges."""
    import math
    n = 5
    spots = [(250 + 132 * math.cos(math.radians(-90 + 72 * k)), 232 + 132 * math.sin(math.radians(-90 + 72 * k)))
             for k in range(n)]
    initial = {"v%d" % k: str(k + 1) for k in range(n)}
    initial.update({"c%d" % k: 0.0 for k in range(n)})
    initial.update({"s%d" % k: "ok" for k in range(n)})
    tl = Timeline(caption="", kind="step", mode="sum", pu=0.0, pa=0.0, pfrom=0.0, plabel="", du=0.0, da=0.0,
                  done=-1.0, exchange=0.0, **initial)

    def hop(src, label, k=1.0, others=True):
        tl.set(pfrom=float(src), plabel=label, pu=0.0, du=0.0)
        tl.to(0.12, pa=1.0, da=0.55 if others else 0.0)
        tl.also(0.9 * k, in_out, du=1.0)
        tl.to(0.9 * k, in_out, pu=1.0)
        tl.to(0.12, pa=0.0, da=0.0)

    tl.chapter("phase 1")
    tl.say("Five Thors in a ring. Each holds its own value for chunk 0 of the gradient: 1, 2, 3, 4 and 5.")
    tl.wait(0.8)
    tl.say("Exchange 1. thor-1 sends its chunk 0 to the right. thor-2 adds its own 2 and holds 3.")
    hop(0, "1", 1.3)
    tl.set(v1="3", exchange=1.0)
    tl.say("Every worker sends one chunk in every exchange. The grey dots are the other four chunks.")
    hop(1, "3")
    tl.set(v2="6", exchange=2.0)
    hop(2, "6", 0.8)
    tl.set(v3="10", exchange=3.0)
    hop(3, "10", 0.8)
    tl.set(v4="15", exchange=4.0, done=4.0)
    tl.say("After four exchanges thor-5 holds 15, the finished sum of chunk 0. Each worker holds one finished chunk.",
           "insight")
    tl.wait(1.0)
    tl.chapter("phase 2")
    tl.say("Four more exchanges carry each finished chunk around the ring. A receiver stores it and passes it on.")

    for k, src in enumerate((4, 0, 1, 2)):
        hop(src, "15", 0.8 if k else 1.2)
        tl.set(**{"v%d" % ((src + 1) % n): "15"}, exchange=5.0 + k)

    tl.say("Eight exchanges, and every worker holds the sum. Each sent 8 chunks: 1.6 gradients' worth.", "insight")
    tl.wait(1.4)

    tl.chapter("thor-3 fails")
    tl.say("The same step again. The numbers now count the exchanges each worker has completed.", "fail")
    reset = {"c%d" % k: 0.0 for k in range(n)}
    tl.set(mode="fail", exchange=0.0, done=-1.0, **reset)
    tl.wait(0.8)

    for count in (1.0, 2.0):
        tl.set(du=0.0)
        tl.to(0.1, da=0.7)
        tl.to(0.7, in_out, du=1.0)
        tl.to(0.1, da=0.0)
        tl.set(**{"c%d" % k: count for k in range(n)})

    tl.say("thor-3 fails after two exchanges. thor-4 has sent its third chunk and waits for one from thor-3.",
           "fail")
    tl.set(s2="failed")
    tl.wait(0.6)
    tl.set(s3="stuck", c4=3.0, c0=3.0, c1=3.0)
    tl.wait(1.0)
    tl.say("thor-5 received thor-4's third chunk and completed exchange 3. In exchange 4 nothing arrives.", "fail")
    tl.set(s4="stuck", c0=4.0, c1=4.0)
    tl.wait(1.0)
    tl.say("The stall moves one worker per exchange: thor-1 stops after 4, thor-2 after 5.", "fail")
    tl.set(s0="stuck", c1=5.0)
    tl.wait(1.0)
    tl.set(s1="stuck")
    tl.say("No worker holds the sum, and only thor-4 was waiting for the machine that failed.", "fail")
    tl.wait(2.0)

    def draw(p, s, total):
        t = s.t
        failing = s.mode == "fail"
        title_block(p, "A ring all-reduce over five Thors",
                    "Each exchange: send one chunk to the right, receive one from the left.")

        if not failing:
            scoreboard(p, [("exchanges", int(round(s.exchange)), TEAL)])

        for k in range(n):
            (x, y), (nx, ny) = spots[k], spots[(k + 1) % n]
            dead = failing and s["s%d" % k] == "failed"
            p.line(x, y, nx, ny, FAINT if not dead else RUST, 1.6, dash="4 6" if dead else None)

            if s.da > 0.01 and not (failing and s["s%d" % k] != "ok"):
                p.circle(lerp(x, nx, s.du), lerp(y, ny, s.du), 5, FAINT, opacity=s.da)

        if s.pa > 0.01:
            src = int(round(s.pfrom))
            (x, y), (nx, ny) = spots[src], spots[(src + 1) % n]
            pill(p, lerp(x, nx, s.pu), lerp(y, ny, s.pu), s.plabel, BRASS, BRASS_LT, 13, opacity=s.pa)

        for k in range(n):
            x, y = spots[k]
            state = s["s%d" % k]
            edge, fill = {"failed": (RUST, RUST_LT), "stuck": (BRASS, BRASS_LT)}.get(state, (TEAL, TEAL_LT))

            if not failing and int(round(s.done)) == k:
                edge, fill = BRASS, BRASS_LT

            p.rect(x - 46, y - 26, 92, 52, fill, edge, 10, 1.8)
            p.text(x, y - 6, "thor-%d" % (k + 1), 11.5, INK, 600, "middle")
            value = ("%d of 8" % int(round(s["c%d" % k]))) if failing else s["v%d" % k]
            p.text(x, y + 15, value, 14, edge if failing else INK, 700, "middle", mono=True)

        panel(p, 500, 96, 294, 268, "what each worker holds" if not failing else "why each worker stopped")

        for k in range(n):
            y = 136 + k * 44
            p.text(514, y, "thor-%d" % (k + 1), 12, INK, 700, mono=True)

            if failing:
                state = s["s%d" % k]
                body = {"failed": "failed", "stuck": "no chunk from thor-%d" % ((k - 1) % n + 1)}.get(state, "running")
                color = {"failed": RUST, "stuck": BRASS}.get(state, MUTED)
                p.text(576, y, body, 11.5, color, 600)
                p.text(576, y + 16, "completed %d of 8" % int(round(s["c%d" % k])), 10.5, MUTED, 500)
            else:
                p.text(576, y, "chunk 0 = %s" % s["v%d" % k], 12, INK, 600, mono=True)
                finished = s["v%d" % k] == "15"
                p.text(576, y + 16, "the finished sum" if finished else "a partial sum", 10.5,
                       TEAL if finished else MUTED, 500)

        caption(p, tl, t, 396)
        progress(p, tl, t, total, 486)

    return tl, draw, 516


# --------------------------------------------------------------- chapter 4

def fleet_repair():
    """The run of `fleethealth` from chapter 4, from second 20 on: each machine
    is a chip on a board with one column per state, and the chips move as the
    program's log says they do."""
    machines = ["thor-1", "thor-2", "thor-3", "thor-4", "thor-5", "spark-1", "spark-2", "orin-nx-1"]
    columns = ["Healthy", "Cordoned", "Draining", "Remediating", "Validating", "Quarantined"]
    row = {name: k for k, name in enumerate(machines)}
    initial = {"p%d" % k: 0.0 for k in range(len(machines))}
    tl = Timeline(caption="", kind="step", clock=20.0, out=0.0, rung="", blocked=0.0, **initial)

    def move(second, moves, out, k=1.0, **extra):
        """At `second`, slide the named machines to their new columns."""
        tl.set(clock=float(second), **extra)
        tl.to(0.55 * k, in_out, **{"p%d" % row[name]: float(col) for name, col in moves})
        tl.set(out=float(out))
        tl.wait(0.25 * k)

    tl.chapter("one repair")
    tl.say("Eight machines, one column for each state. Second 20: spark-1 reports an uncorrectable memory error.")
    tl.wait(0.6)
    move(20, [("spark-1", 1)], 0, 1.3)
    tl.say("It is cordoned at once. The budget of two is free, so it starts to drain in the same second.")
    move(20, [("spark-1", 2)], 1, 1.3)
    tl.say("Its jobs checkpoint and leave, the GPU is reset, and a burn-in test runs.")
    move(24, [("spark-1", 3)], 1)
    move(27, [("spark-1", 4)], 1)
    tl.say("The burn-in passes at second 30, and spark-1 is back in service ten seconds after the error.",
           "insight")
    move(30, [("spark-1", 0)], 0)
    tl.wait(0.8)

    tl.chapter("the ladder")
    tl.say("Second 40: the GPU of thor-4 stops answering. It is cordoned, drained, and its GPU is reset.")
    move(40, [("thor-4", 1)], 0)
    move(40, [("thor-4", 2)], 1)
    move(44, [("thor-4", 3)], 1, rung="reset the GPU")
    move(47, [("thor-4", 4)], 1)
    tl.say("The burn-in fails, so it climbs the ladder: a reboot, then a reimage, with a burn-in after each.",
           "fail")
    move(50, [("thor-4", 3)], 1, 0.8, rung="reboot")
    move(53, [("thor-4", 4)], 1, 0.8)
    move(56, [("thor-4", 3)], 1, 0.8, rung="reimage")
    move(59, [("thor-4", 4)], 1, 0.8)
    tl.say("Every action has failed. At second 62 thor-4 is quarantined, and it keeps one slot of the budget.",
           "fail")
    move(62, [("thor-4", 5)], 1, rung="")
    tl.wait(0.8)

    tl.chapter("the budget")
    tl.say("Second 80: spark-2 and orin-nx-1 fail together. Both are cordoned.")
    move(80, [("spark-2", 1), ("orin-nx-1", 1)], 1, 1.3)
    tl.say("spark-2 takes the last slot and drains. orin-nx-1 is blocked: two machines are out of service.",
           "insight")
    move(80, [("spark-2", 2)], 2, 1.3)
    tl.to(0.3, blocked=1.0)
    tl.wait(0.6)
    move(84, [("spark-2", 3)], 2)
    move(87, [("spark-2", 4)], 2)
    tl.say("At second 90 spark-2 passes its burn-in and frees the slot. orin-nx-1 starts to drain.")
    move(90, [("spark-2", 0)], 1)
    tl.to(0.3, blocked=0.0)
    move(90, [("orin-nx-1", 2)], 2)
    move(94, [("orin-nx-1", 3)], 2)
    move(97, [("orin-nx-1", 4)], 2)
    move(100, [("orin-nx-1", 0)], 1)
    tl.say("Seven machines are healthy and one waits for a person. At most two were out of service at once.",
           "insight")
    tl.wait(1.6)

    def draw(p, s, total):
        t = s.t
        title_block(p, "A fleet under repair",
                    "Each machine moves through the lifecycle. The budget limits how many are out of service.")
        out = int(round(s.out))
        scoreboard(p, [("second", int(s.clock), INK), ("out of service", "%d of 2" % out, RUST if out >= 2 else TEAL)])
        x0, colw, top, rowh = 26, 128, 84, 30

        for c, name in enumerate(columns):
            holds = c >= 2
            p.rect(x0 + c * colw, top, colw - 6, 26 + rowh * len(machines) + 6, "#fbfcfd" if not holds else "#fdf7f1",
                   LINE, 8, 1.2)
            p.text(x0 + c * colw + (colw - 6) / 2, top + 18, name, 11, MUTED if not holds else RUST, 700, "middle")

        p.text(x0 + 2 * colw, top + 26 + rowh * len(machines) + 22, "these four columns each hold a budget slot", 10.5,
               RUST, 500)

        for k, name in enumerate(machines):
            col = s["p%d" % k]
            x = x0 + col * colw + 8
            y = top + 28 + k * rowh
            near = int(round(col))
            edge, fill = {0: (TEAL, TEAL_LT), 1: (MUTED, STAGE), 5: (RUST, RUST_LT)}.get(near, (BRASS, BRASS_LT))
            p.rect(x, y, colw - 22, rowh - 6, fill, edge, 7, 1.5)
            p.text(x + (colw - 22) / 2, y + 16.5, name, 11.5, INK, 600, "middle", mono=True)

            if name == "thor-4" and s.rung and near in (3, 4):
                p.text(x + colw - 14, y + 16.5, s.rung, 10.5, RUST, 600)

            if name == "orin-nx-1" and s.blocked > 0.01:
                p.text(x + colw - 14, y + 16.5, "blocked: the budget is spent", 10.5, RUST, 600, opacity=clamp(s.blocked))

        caption(p, tl, t, 396)
        progress(p, tl, t, total, 486)

    return tl, draw, 516


# --------------------------------------------------------------- chapter 5

def lost_reply():
    """The run of `provisioner` from chapter 5, for the pool of five Thors: the
    reply to the third create call is lost, and the retry is sent without a
    client token and then with one."""
    tl = Timeline(caption="", kind="step", mode="plain", made=0.0, owned=0.0, orphan=0.0, fly_u=0.0, fly_a=0.0,
                  fly_label="", fly_dir=1.0, fly_kind="ask", lost=0.0, slot="thor-1", refused=0.0)
    ids = {"plain": ["m-01", "m-02", "m-03", "m-06", "m-07"], "token": ["m-01", "m-02", "m-03", "m-06", "m-07"]}

    def call(label, reply, lose=False, k=1.0):
        tl.set(fly_label=label, fly_kind="ask", fly_dir=1.0, fly_u=0.0, lost=0.0)
        tl.to(0.1, fly_a=1.0)
        tl.to(0.6 * k, in_out, fly_u=1.0)
        tl.to(0.1, fly_a=0.0)

        return reply, lose

    def answer(reply, lose=False, kind="ok", k=1.0):
        tl.set(fly_label=reply, fly_kind=kind, fly_dir=-1.0, fly_u=0.0, lost=0.0)
        tl.to(0.1, fly_a=1.0)

        if lose:
            tl.to(0.35 * k, in_out, fly_u=0.5)
            tl.to(0.3, lost=1.0, fly_a=0.0)
        else:
            tl.to(0.6 * k, in_out, fly_u=1.0)
            tl.to(0.1, fly_a=0.0)

    def create(slot, label, made, owned, lose=False, kind="ok", reply=None, k=1.0):
        tl.set(slot=slot)
        call(label, None, k=k)
        tl.set(made=float(made))
        answer(reply or ("m-%02d" % (made if made < 4 else made + 2)), lose, kind, k)
        tl.set(owned=float(owned))

    tl.chapter("no token")
    tl.say("The controller wants five Thors. The account's quota is five. Each create call makes one machine.")
    create("thor-1", "create", 1, 1, k=1.2)
    create("thor-2", "create", 2, 2, k=0.8)
    tl.say("The third call makes machine m-03, and its reply is lost. The controller sees only a timeout.", "fail")
    create("thor-3", "create", 3, 2, lose=True)
    tl.wait(0.8)
    tl.say("It tries again with a plain create. The provider makes another machine, m-06, for the same slot.",
           "fail")
    create("thor-3", "create", 4, 3)
    tl.to(0.4, orphan=1.0)
    create("thor-4", "create", 5, 4, k=0.8)
    tl.say("The account now holds five Thors. The call for thor-5 is refused: the quota is spent.", "fail")
    tl.set(slot="thor-5")
    call("create", None)
    answer("quota exceeded", kind="bad")
    tl.to(0.3, refused=1.0)
    tl.say("The controller owns four machines and can get no more. m-03 runs and belongs to no pool.", "fail")
    tl.wait(1.6)

    tl.chapter("with a token")
    tl.say("The same run, with the slot's name sent as a client token on every call.")
    tl.set(mode="token", made=0.0, owned=0.0, orphan=0.0, refused=0.0, slot="thor-1")
    tl.wait(0.6)
    create("thor-1", "create, token thor-1", 1, 1, k=0.8)
    create("thor-2", "create, token thor-2", 2, 2, k=0.8)
    tl.say("The reply to the third call is lost again. Machine m-03 exists and carries the token thor-3.", "fail")
    create("thor-3", "create, token thor-3", 3, 2, lose=True)
    tl.wait(0.8)
    tl.say("The retry carries the same token. The provider finds m-03 under it and returns it, making nothing.",
           "insight")
    create("thor-3", "create, token thor-3", 3, 3, reply="m-03, already there", k=1.3)
    create("thor-4", "create, token thor-4", 4, 4, k=0.8)
    create("thor-5", "create, token thor-5", 5, 5, k=0.8)
    tl.say("Five machines, five owned, none left over.", "insight")
    tl.wait(1.6)

    def draw(p, s, total):
        t = s.t
        title_block(p, "A create call whose reply is lost",
                    "The controller counts what it was told. The provider counts what it made.")
        made, owned = int(round(s.made)), int(round(s.owned))
        scoreboard(p, [("controller owns", owned, TEAL), ("provider holds", made, RUST if made > owned + 0 and s.orphan > 0.5 else INK)])
        robot(p, 120, 262, TEAL, 1.0, 1.0, "controller", "filling " + s.slot)
        panel(p, 520, 92, 274, 232, "provider: Jetson AGX Thor, quota 5")
        names = ids[s.mode]

        for k in range(5):
            y = 124 + k * 38
            p.rect(534, y, 246, 30, "#f3f6f9", LINE, 6, 1.0)

            if k < made:
                orphan = s.mode == "plain" and k == 2 and s.orphan > 0.5
                edge, fill = (RUST, RUST_LT) if orphan else (TEAL, TEAL_LT)
                p.rect(534, y, 246, 30, fill, edge, 6, 1.4)
                p.text(546, y + 20, names[k], 12, INK, 700, mono=True)
                note = "no owner" if orphan else ("token thor-%d" % (k + 1) if s.mode == "token" else "")
                p.text(770, y + 20, note, 10.5, edge, 600, "end")

        if s.refused > 0.01:
            p.text(657, 340, "quota exceeded", 12, RUST, 700, "middle", opacity=clamp(s.refused))

        x0, x1 = 196, 510
        p.line(x0, 214, x1, 214, FAINT, 1.4, dash="5 6")

        if s.fly_a > 0.01 or s.lost > 0.01:
            a, b = (x0 + 60, x1 - 70) if s.fly_dir > 0 else (x1 - 70, x0 + 60)
            color, fill = {"ask": (NIGHT, NIGHT_LT), "bad": (RUST, RUST_LT)}.get(s.fly_kind, (TEAL, TEAL_LT))
            x = lerp(a, b, s.fly_u)
            pill(p, x, 214, s.fly_label, color, fill, 10.5, opacity=s.fly_a, shadow=None)

            if s.lost > 0.01:
                p.text(x, 190, "reply lost", 12, RUST, 700, "middle", opacity=clamp(s.lost))
                p.line(x - 9, 205, x + 9, 223, RUST, 2.6, opacity=clamp(s.lost))
                p.line(x - 9, 223, x + 9, 205, RUST, 2.6, opacity=clamp(s.lost))

        caption(p, tl, t, 372)
        progress(p, tl, t, total, 462)

    return tl, draw, 492


# --------------------------------------------------------------- chapter 6

def pre_copy():
    """Three of the migrations that `migration` prints in chapter 6, for the
    100 GB VM that dirties 4 GB a second: over four bonded lanes, over one
    lane, and over one lane with the guest slowed."""
    tl = Timeline(caption="", kind="step", link="four bonded 25 GbE lanes: 12.5 GB/s", round=1.0, left=100.0,
                  dirty=0.0, paused=0.0, speed=100.0, clock=0.0, verdict="")

    def round_(n, send, dirtied, seconds, k=1.0):
        tl.set(round=float(n), left=float(send), dirty=0.0)
        tl.also(1.6 * k, linear, clock=tl._at("clock", tl.now) + seconds)
        tl.to(1.6 * k, linear, left=0.0, dirty=float(dirtied))
        tl.wait(0.3 * k)

    tl.chapter("12.5 GB/s")
    tl.say("A 100 GB VM keeps running and changes 4 GB of its memory every second. Round 1 sends all 100 GB.")
    round_(1, 100, 32, 8.0, 1.4)
    tl.say("That took 8 seconds, and 32 GB changed meanwhile. Round 2 sends those 32 GB.")
    round_(2, 32, 10.24, 2.56)
    round_(3, 10.24, 3.28, 0.82, 0.8)
    tl.say("3.28 GB remain, which the link carries in 0.26 seconds. The VM is paused for that long, and moves.",
           "insight")
    tl.set(round=4.0, left=3.28, dirty=0.0)
    tl.to(0.3, paused=1.0)
    tl.also(0.8, linear, clock=11.6)
    tl.to(0.8, linear, left=0.0)
    tl.set(verdict="moved in 11.6 s, paused for 262 ms")
    tl.wait(1.6)

    tl.chapter("3.125 GB/s")
    tl.say("The same VM over one 25 GbE lane, which carries 3.125 GB a second: less than the VM changes.", "fail")
    tl.set(link="one 25 GbE lane: 3.125 GB/s", paused=0.0, clock=0.0, verdict="", left=100.0, dirty=0.0, round=1.0)
    tl.wait(0.6)
    round_(1, 100, 100, 32.0, 1.4)
    tl.say("Round 1 takes 32 seconds, and by then all 100 GB have changed again. No round can end smaller.",
           "fail")
    tl.set(verdict="does not converge")
    tl.wait(1.6)

    tl.chapter("slowed guest")
    tl.say("With throttling, each round that makes no progress slows the guest. At 60% it changes 2.4 GB a second.")
    tl.set(verdict="", clock=64.0, speed=60.0)
    for n, (send, dirtied, seconds) in enumerate([(100, 76.8, 32.0), (76.8, 58.98, 24.6), (58.98, 45.3, 18.9),
                                                   (45.3, 34.79, 14.5)]):
        round_(3 + n, send, dirtied, seconds, 0.9 if n else 1.2)
    tl.say("Each round is 0.768 of the one before. It takes 21 rounds and 201 seconds, with the job slowed.",
           "insight")
    tl.set(round=21.0, left=0.86, dirty=0.0, clock=200.7)
    tl.to(0.3, paused=1.0)
    tl.to(0.6, linear, left=0.0, clock=201.0)
    tl.set(verdict="moved in 201 s, paused for 276 ms")
    tl.wait(1.8)

    def draw(p, s, total):
        t = s.t
        title_block(p, "Moving a running VM, round by round",
                    "Each round sends what changed during the round before.")
        scoreboard(p, [("round", int(round(s.round)), INK), ("seconds", "%.1f" % s.clock, TEAL)])
        chip(p, 26, 92, s.link, NIGHT, NIGHT_LT, 12, anchor="start")
        base, scale = 330, 2.1
        for x, value, label, color, fill in ((150, s.left, "still to send", TEAL, TEAL_LT),
                                             (420, s.dirty, "changed during this round", RUST, RUST_LT)):
            p.rect(x, base - 100 * scale, 150, 100 * scale, "#f6f8fa", LINE, 6, 1.0)
            h = clamp(value / 100.0) * 100 * scale

            if h > 0.5:
                p.rect(x, base - h, 150, h, fill, color, 6, 1.6)

            p.text(x + 75, base - h - 8 if h < 180 else base - h + 22, "%.2f GB" % value, 14, INK, 700, "middle",
                   mono=True)
            p.text(x + 75, base + 20, label, 11.5, MUTED, 600, "middle")
        p.text(366, 250, "then", 11, FAINT, 600, "middle")
        paused = s.paused > 0.5
        chip(p, 690, 150, "VM paused" if paused else "VM running", RUST if paused else TEAL,
             RUST_LT if paused else TEAL_LT, 13)
        p.text(690, 190, "guest at %d%% speed" % int(round(s.speed)), 11.5, MUTED if s.speed > 99 else RUST, 600, "middle")

        if s.verdict:
            good = s.verdict.startswith("moved")
            p.text(690, 240, s.verdict.split(", ")[0], 12.5, TEAL if good else RUST, 700, "middle")

            if ", " in s.verdict:
                p.text(690, 260, s.verdict.split(", ")[1], 12.5, TEAL, 700, "middle")

        caption(p, tl, t, 372)
        progress(p, tl, t, total, 462)

    return tl, draw, 492


# --------------------------------------------------------------- chapter 8

FLEET = ["orin-nx-1", "spark-1", "spark-2", "thor-1", "thor-2", "thor-3", "thor-4", "thor-5"]


def gang_placement():
    """The four experiments of `gangsched` from chapter 8 on the eight
    machines: one pod at a time, whole jobs, and two ways to choose machines."""
    initial = {"o%d" % k: "" for k in range(8)}
    tl = Timeline(caption="", kind="step", note_a="", note_b="", note_c="", **initial)
    colours = {"train-a": (NIGHT, NIGHT_LT), "train-b": (BRASS, BRASS_LT), "pair": (TEAL, TEAL_LT),
               "quad": (NIGHT, NIGHT_LT), "single": (BRASS, BRASS_LT)}

    def give(job, machines, pause=0.45):
        for name in machines:
            tl.set(**{"o%d" % FLEET.index(name): job})
            tl.wait(pause)

    def clear():
        tl.set(note_a="", note_b="", note_c="", **{"o%d" % k: "" for k in range(8)})

    tl.chapter("one pod at a time")
    tl.say("Eight machines, one GPU each. Two jobs arrive, and each needs five workers. Pods are placed in turn.")
    tl.wait(0.6)

    for a, b in zip(["orin-nx-1", "spark-2", "thor-2", "thor-4"], ["spark-1", "thor-1", "thor-3", "thor-5"]):
        give("train-a", [a], 0.4)
        give("train-b", [b], 0.4)

    tl.set(note_a="train-a holds 4 of 5", note_b="train-b holds 4 of 5", note_c="0 jobs are running")
    tl.say("Each job holds four GPUs and waits for a fifth. All eight are taken and no training happens.", "fail")
    tl.wait(1.8)

    tl.chapter("whole jobs")
    clear()
    tl.say("Now a job starts only when all of its workers fit. train-a is admitted and takes the five Thors.")
    give("train-a", FLEET[3:], 0.25)
    tl.set(note_a="train-a runs: 5 of 5", note_b="train-b waits and holds nothing", note_c="3 GPUs stay free")
    tl.say("train-b needs five and finds three. It waits without taking any, so smaller jobs can still run.",
           "insight")
    tl.wait(1.8)

    tl.chapter("first free")
    clear()
    tl.say("Three jobs of 2, 4 and 1 workers. First, each takes the first free machines in name order.")
    give("pair", FLEET[0:2])
    tl.set(note_a="pair: 1 GbE house network, 112.0 s per all-reduce")
    give("quad", FLEET[2:6], 0.3)
    tl.set(note_b="quad: 1 GbE house network, 168.0 s per all-reduce")
    give("single", ["thor-4"])
    tl.say("pair spans the bench and the desk, and quad spans the desk and the shelf. Both use the slowest path.",
           "fail")
    tl.wait(1.8)

    tl.chapter("by topology")
    clear()
    tl.say("The same jobs, each placed in the smallest group of machines that holds it.")
    give("pair", ["spark-1", "spark-2"])
    tl.set(note_a="pair: 200 GbE cable, 0.6 s per all-reduce")
    give("quad", FLEET[3:7], 0.3)
    tl.set(note_b="quad: 25 GbE switch, 6.7 s per all-reduce")
    give("single", ["orin-nx-1"])
    tl.say("pair fills the desk, quad stays on the shelf, and single takes the bench. One Thor is left free.",
           "insight")
    tl.wait(2.0)

    def draw(p, s, total):
        t = s.t
        title_block(p, "Placing jobs on eight GPUs",
                    "A job runs when all of its workers have a machine, at the speed of their slowest link.")
        groups = [("bench, 1 GbE", 26, 1), ("desk, 200 GbE cable", 134, 2), ("shelf, 25 GbE switch", 332, 5)]
        k = 0

        for label, x, count in groups:
            width = count * 90 + 10
            p.rect(x, 96, width, 150, "#fbfcfd", LINE, 10, 1.2)
            p.text(x + 10, 114, label, 10.5, MUTED, 700)

            for i in range(count):
                owner = s["o%d" % k]
                edge, fill = colours.get(owner, (FAINT, "#f3f6f9"))
                bx = x + 8 + i * 90
                p.rect(bx, 126, 82, 106, fill, edge, 9, 1.8 if owner else 1.0)
                p.text(bx + 41, 150, FLEET[k], 11, INK, 700, "middle", mono=True)
                p.text(bx + 41, 196, owner or "free", 12, edge if owner else FAINT, 700, "middle")
                k += 1

        p.text(410, 260, "between groups: the 1 GbE house network", 10.5, MUTED, 500, "middle")

        for row, note in enumerate((s.note_a, s.note_b, s.note_c)):
            if note:
                p.text(26, 290 + row * 22, note, 12.5, INK, 600, mono=True)

        caption(p, tl, t, 372)
        progress(p, tl, t, total, 462)

    return tl, draw, 492


# --------------------------------------------------------------- chapter 9

def gcounter_merge():
    """The second experiment of `counter` from chapter 9: three grow-only
    counters through a partition and an untidy recovery."""
    rows = {"shelf": [0, 0, 0], "desk": [0, 0, 0], "bench": [0, 0, 0]}
    initial = {}

    for name in rows:
        for i in range(3):
            initial["%s%d" % (name, i)] = 0.0

    tl = Timeline(caption="", kind="step", cut=0.0, fly_u=0.0, fly_a=0.0, fly_from=0.0, fly_to=1.0, mark="", **initial)
    order = ["shelf", "desk", "bench"]

    def put(name, values):
        rows[name] = list(values)
        tl.set(mark=name)
        tl.to(0.45, **{"%s%d" % (name, i): float(v) for i, v in enumerate(values)})

    def merge(dst, src, k=1.0):
        tl.set(fly_from=float(order.index(src)), fly_to=float(order.index(dst)), fly_u=0.0)
        tl.to(0.1, fly_a=1.0)
        tl.to(0.6 * k, in_out, fly_u=1.0)
        tl.to(0.1, fly_a=0.0)
        put(dst, [max(a, b) for a, b in zip(rows[dst], rows[src])])

    tl.chapter("apart")
    tl.say("Three replicas. Each holds a row with one entry per replica, and adds only to its own entry.")
    put("shelf", [300, 0, 0])
    put("desk", [0, 120, 0])
    put("bench", [0, 0, 40])
    tl.say("The bench is cut off. The shelf and the desk exchange rows, and each keeps the larger of every entry.",
           "fail")
    tl.to(0.4, cut=1.0)
    merge("shelf", "desk", 1.3)
    merge("desk", "shelf", 1.3)
    tl.say("Reports keep arriving on both sides: 60 more at the shelf, and 25 more at the bench.")
    put("shelf", [360, 120, 0])
    put("bench", [0, 0, 65])
    tl.say("The three replicas disagree: 480, 420 and 65. Each is missing reports that another one holds.", "fail")
    tl.set(mark="")
    tl.wait(1.4)
    tl.chapter("heal")
    tl.say("The network heals. Rows are exchanged in no particular order, and one exchange happens twice.")
    tl.to(0.4, cut=0.0)
    merge("desk", "bench")
    merge("shelf", "desk")
    merge("bench", "shelf")
    merge("desk", "shelf")
    merge("desk", "shelf", 0.7)
    tl.set(mark="")
    tl.say("All three hold 360, 120, 65, which is 545: every report, counted once.", "insight")
    tl.wait(2.0)

    def draw(p, s, total):
        t = s.t
        title_block(p, "Three grow-only counters", "A merge keeps the larger value of each entry, so it can be repeated and reordered.")
        ys = {"shelf": 118, "desk": 196, "bench": 274}

        for name in order:
            y = ys[name]
            hot = s.mark == name
            p.rect(150, y, 520, 58, "#fbfcfd", BRASS if hot else LINE, 10, 2.0 if hot else 1.2)
            p.text(40, y + 36, name, 15, INK, 700)
            total_value = 0

            for i, owner in enumerate(order):
                value = int(round(s["%s%d" % (name, i)]))
                total_value += value
                own = owner == name
                p.rect(166 + i * 112, y + 11, 100, 36, TEAL_LT if own else "#f3f6f9", TEAL if own else LINE, 7, 1.3)
                p.text(216 + i * 112, y + 35, str(value), 15, INK, 700, "middle", mono=True)

            p.text(166 + 3 * 112 + 6, y + 35, "=", 15, MUTED, 600, mono=True)
            p.text(650, y + 35, str(total_value), 16, INK, 700, "end", mono=True)

        for i, owner in enumerate(order):
            p.text(216 + i * 112, 108, owner + "'s entry", 10.5, MUTED, 600, "middle")

        if s.cut > 0.01:
            p.line(26, 264, 794, 264, RUST, 2.0, dash="3 7", opacity=clamp(s.cut))
            p.text(790, 258, "no route to the bench", 11, RUST, 700, "end", opacity=clamp(s.cut))

        if s.fly_a > 0.01:
            y0 = [ys[n] for n in order][int(round(s.fly_from))] + 29
            y1 = [ys[n] for n in order][int(round(s.fly_to))] + 29
            pill(p, 730, lerp(y0, y1, s.fly_u), "row", NIGHT, NIGHT_LT, 11, opacity=s.fly_a, shadow=None)

        caption(p, tl, t, 352)
        progress(p, tl, t, total, 442)

    return tl, draw, 472


# -------------------------------------------------------------- chapter 10

def cas_chunks():
    """The run of `cas` from chapter 10: two pushes that share six chunks, two
    pulls, one damaged chunk repaired, and a collection."""
    initial = {"r%d" % k: 0.0 for k in range(10)}
    initial.update({"n%d" % k: 0.0 for k in range(10)})
    tl = Timeline(caption="", kind="step", bad=0.0, swept=0.0, tag1=0.0, tag2=0.0, node1=0.0, node2=0.0,
                  stat="", **initial)

    def show(prefix, indexes, pause=0.12):
        for k in indexes:
            tl.to(pause, **{"%s%d" % (prefix, k): 1.0})

    tl.chapter("push")
    tl.say("Version 1 of the model is cut into eight chunks. Each is stored under the SHA-256 of its bytes.")
    show("r", range(8), 0.2)
    tl.to(0.3, tag1=1.0)
    tl.set(stat="push llm:v1: 8 chunks, 8 new")
    tl.say("Version 2 keeps the first three quarters. Six of its chunks have digests the registry already holds.",
           "insight")
    show("r", (8, 9), 0.4)
    tl.to(0.3, tag2=1.0)
    tl.set(stat="push llm:v2: 8 chunks, 2 new")
    tl.wait(1.2)
    tl.chapter("pull")
    tl.say("thor-1 has nothing. It pulls version 1 and fetches all eight chunks, 65,536 bytes.")
    show("n", range(8), 0.2)
    tl.to(0.2, node1=1.0)
    tl.set(stat="pull llm:v1: 8 chunks fetched")
    tl.say("For version 2 it asks only for the digests it lacks: two chunks, 16,384 bytes.", "insight")
    show("n", (8, 9), 0.4)
    tl.to(0.2, node2=1.0)
    tl.set(stat="pull llm:v2: 2 chunks fetched")
    tl.wait(1.2)
    tl.chapter("damage")
    tl.say("One bit flips in a chunk on thor-1. The next read hashes it and finds that the bytes and the name disagree.",
           "fail")
    tl.to(0.4, bad=1.0)
    tl.set(stat="read llm:v1: chunk 3 does not match its digest")
    tl.wait(1.2)
    tl.say("thor-1 drops that one blob and pulls again. Seven chunks are present, and one is fetched.")
    tl.to(0.3, n3=0.0, bad=0.0)
    tl.wait(0.3)
    tl.to(0.4, n3=1.0)
    tl.set(stat="pull llm:v1 again: 1 chunk fetched, 8,192 bytes")
    tl.wait(1.0)
    tl.chapter("collect")
    tl.say("The tag llm:v1 is deleted from the registry. Collection marks what llm:v2 leads to and sweeps the rest.")
    tl.to(0.4, tag1=0.0)
    tl.to(0.5, swept=1.0)
    tl.to(0.5, r6=0.0, r7=0.0)
    tl.set(stat="collected 3 blobs: 2 chunks and the manifest of v1")
    tl.say("The six shared chunks stay, because version 2 still lists them.", "insight")
    tl.wait(2.0)

    def draw(p, s, total):
        t = s.t
        title_block(p, "A model stored as chunks named by their digests",
                    "Chunks 0 to 5 belong to both versions, 6 and 7 to version 1, and 8 and 9 to version 2.")

        def grid(x, y, title, prefix, damaged):
            panel(p, x, y, 360, 126, title)

            for k in range(10):
                bx, by = x + 14 + (k % 5) * 68, y + 32 + (k // 5) * 44
                held = s["%s%d" % (prefix, k)]
                p.rect(bx, by, 60, 36, "#f3f6f9", LINE, 6, 1.0)

                if held > 0.01:
                    shared = k < 6
                    edge, fill = (TEAL, TEAL_LT) if shared else ((NIGHT, NIGHT_LT) if k < 8 else (BRASS, BRASS_LT))

                    if damaged and k == 3 and s.bad > 0.5:
                        edge, fill = RUST, RUST_LT

                    if prefix == "r" and k in (6, 7) and s.swept > 0.5:
                        edge, fill = RUST, RUST_LT

                    p.rect(bx, by, 60, 36, fill, edge, 6, 1.5, opacity=clamp(held))
                    p.text(bx + 30, by + 23, "chunk %d" % k, 10.5, INK, 700, "middle", opacity=clamp(held))

        grid(26, 92, "registry", "r", False)
        grid(434, 92, "thor-1", "n", True)

        for x, a, b in ((26, s.tag1, s.tag2), (434, s.node1, s.node2)):
            if a > 0.01:
                chip(p, x + 70, 240, "llm:v1: chunks 0 to 7", NIGHT, NIGHT_LT, 11, opacity=clamp(a))

            if b > 0.01:
                chip(p, x + 250, 240, "llm:v2: 0 to 5, 8, 9", BRASS, BRASS_LT, 11, opacity=clamp(b))

        if s.stat:
            p.text(26, 290, s.stat, 13, INK, 700, mono=True)

        caption(p, tl, t, 322)
        progress(p, tl, t, total, 412)

    return tl, draw, 442


# -------------------------------------------------------------- chapter 11

def cli_channels():
    """Three runs of `gpuctl` from chapter 11: a command that succeeds, a
    command that does not exist, and a cluster that cannot be reached."""
    tl = Timeline(caption="", kind="step", command="", out="", err="", status="", hot="")

    def run(command, out, err, status, hot):
        tl.set(command="", out="", err="", status="", hot="")
        tl.wait(0.4)
        tl.set(command=command)
        tl.wait(1.0)
        tl.set(out=out, err=err, hot=hot)
        tl.wait(0.6)
        tl.set(status=status)

    tl.chapter("success")
    tl.say("A command writes to two streams and returns a status. Here the cluster answers.")
    run("gpuctl nodes -o json", '[{"name": "gpu-lab-control-plane", "gpus": 1, ...}]', "", "0", "out")
    tl.say("The JSON goes to standard output and nothing else does, so a script can feed it to another program.",
           "insight")
    tl.wait(1.4)
    tl.chapter("wrong command")
    tl.say("A command gpuctl does not have. The message and the usage text are for a person.", "fail")
    run("gpuctl pods", "", 'gpuctl: unknown command "pods"  +  usage', "2", "err")
    tl.say("Standard output stays empty, and the status is 2: the command line itself was wrong.", "fail")
    tl.wait(1.4)
    tl.chapter("no cluster")
    tl.say("A valid command, and a kubeconfig that does not exist.", "fail")
    run("KUBECONFIG=/nonexistent gpuctl nodes", "", "gpuctl: invalid configuration: ...", "1", "err")
    tl.say("Status 1: the command was understood and failed. A script may retry this one, and should stop on a 2.",
           "insight")
    tl.wait(2.0)

    def draw(p, s, total):
        t = s.t
        title_block(p, "One command, three channels", "The result, the messages for a person, and the exit status stay apart.")
        panel(p, 26, 88, 768, 52, "command line")
        p.text(40, 128, "$ " + s.command if s.command else "$", 13.5, INK, 700, mono=True)
        boxes = [("out", "standard output: the result", 150, s.out, TEAL, TEAL_LT),
                 ("err", "standard error: messages for a person", 222, s.err, BRASS, BRASS_LT)]

        for key, title, y, body, edge, fill in boxes:
            hot = s.hot == key and body
            panel(p, 26, y, 600, 62, title, edge if hot else LINE, fill if hot else "#fbfcfd")
            p.text(40, y + 45, body or "(empty)", 12, INK if body else FAINT, 600 if body else 400, mono=True)

        code = s.status
        edge, fill = {"0": (TEAL, TEAL_LT), "1": (BRASS, BRASS_LT), "2": (RUST, RUST_LT)}.get(code, (LINE, "#fbfcfd"))
        panel(p, 646, 150, 148, 134, "exit status", edge, fill)
        p.text(720, 236, code or "", 44, edge if code else FAINT, 700, "middle", mono=True)
        meaning = {"0": "success", "1": "the command failed", "2": "wrong command line"}.get(code, "")
        p.text(720, 268, meaning, 11, edge if code else FAINT, 600, "middle")
        caption(p, tl, t, 312)
        progress(p, tl, t, total, 402)

    return tl, draw, 432


def build(name, script):
    def run(only=None):
        tl, draw, height = script()

        return render(name + ".gif", tl, draw, height, only=only)
    return run


MOTION = {
    "list-watch": build("list-watch", list_watch),
    "work-queue": build("work-queue", work_queue),
    "lease-expiry": build("lease-expiry", lease_expiry),
    "ring-allreduce": build("ring-allreduce", ring_allreduce),
    "fleet-repair": build("fleet-repair", fleet_repair),
    "lost-reply-run": build("lost-reply-run", lost_reply),
    "pre-copy-rounds": build("pre-copy-rounds", pre_copy),
    "gang-placement": build("gang-placement", gang_placement),
    "gcounter-merge": build("gcounter-merge", gcounter_merge),
    "cas-chunks": build("cas-chunks", cas_chunks),
    "cli-channels": build("cli-channels", cli_channels),
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
