"""The thread pool animations (ch18-thread-pools.md), drawn with `motion`.

    python3 tools/animations.py pool-lock pool-panic
"""

from anim_kernel import padlock
from motion_kit import Panel, layout, nth_after
from motion import *  # noqa: F401,F403
from motion import Timeline, render

V1_LOOP = Panel("src/bin/thread_pool.rs", [("thread::spawn(move || {", "}")],
                ["while let Ok(job) = rx.lock().unwrap().recv() {", "job();"])
V2_LOOP = Panel("src/problems/thread_pool_v2.rs",
                [(("thread::spawn(move || {",
                   nth_after("src/problems/thread_pool_v2.rs", "thread::spawn(move || {",
                             "let receiver = Arc::clone")), "}")],
                ["let job = receiver.lock().unwrap().recv();", "Ok(job) => job(),"])
V3_LOOP = Panel("src/problems/thread_pool_v3.rs", [("fn worker_loop(", "}")],
                ["let job = guard.recv();", "Ok(job) => job(),"])
V4_LOOP = Panel("src/problems/thread_pool_v4.rs", [("fn worker_loop(", "}")],
                ["let job = guard.recv();",
                 "match panic::catch_unwind(AssertUnwindSafe(job)) {",
                 "Ok(()) => counters", "Err(_) => counters"])

WORKERS = [470, 560, 650, 740]
DESK = 214
CHANNEL = (60, 300, 118)      # x0, x1, y of the job channel
RECEIVER = (360, 118)


def channel_jobs(p, count, color=BRASS, fill=BRASS_LT, label="job"):
    x0, x1, y = CHANNEL
    p.rect(x0, y - 18, x1 - x0, 36, "#e6ecf6", INK, 18, 1.3)
    p.text(x0, y - 26, "channel", 10.5, MUTED, 600)
    for k in range(count):
        chip(p, x1 - 34 - 58 * k, y, label, color, fill, 10)


def worker(p, k, awake, color, label, progress=0.0, note="", note_color=MUTED, gone=0.0):
    x = WORKERS[k]
    with p.group(opacity=1.0 - 0.6 * gone, scale=0.6, cx=x, cy=DESK):
        robot(p, x, DESK, FAINT if gone > 0.5 else color, awake, awake, None)
    p.text(x, DESK + 20, label, 11, INK, 600, "middle")
    if progress > 0.001:
        p.rect(x - 34, DESK + 30, 68, 7, "#e6ebf0", "none", 3)
        p.rect(x - 34, DESK + 30, 68 * clamp(progress), 7, TEAL, "none", 3)
    if note:
        p.text(x, DESK + 52, note, 10, note_color, 700, "middle")


# ---------------------------------------------------------- 18.2: the lock


def pool_lock():
    tl = Timeline(caption="", kind="step", code=-1.0, variant="v2", queued=4, owner=-1,
                  fly_u=0.0, fly_a=0.0, fly_to=0, p0=0.0, p1=0.0, p2=0.0, p3=0.0, clock=0.0,
                  waiting="", held="")

    def take(k, dur=0.5):
        tl.set(owner=k, code=0.0)
        tl.set(fly_to=k, fly_u=0.0)
        tl.to(0.1, fly_a=1.0)
        tl.to(dur, in_out, fly_u=1.0)
        tl.to(0.1, fly_a=0.0)
        tl.set(queued=3 - k, held=tl._at("held", tl.now) + str(k))

    tl.chapter("version 2")
    tl.say("Four jobs wait in the channel. Each sleeps for 200 ms. Four workers share the receiver "
           "behind one Mutex.")
    tl.wait(0.6)
    tl.say("Worker 1 locks the receiver and takes job 1. The guard is dropped at the end of that "
           "let statement.")
    take(0, 0.8)
    tl.set(owner=-1)
    tl.wait(0.4)
    tl.say("So the lock is free before job 1 starts. Workers 2, 3, and 4 each take a job the same "
           "way.")
    for k in (1, 2, 3):
        take(k, 0.4)
        tl.set(owner=-1)
    tl.set(code=1.0)
    tl.say("All four jobs run at the same time.")
    tl.to(2.2, linear, p0=1.0, p1=1.0, p2=1.0, p3=1.0, clock=205.0)
    tl.say("205 ms for four 200 ms jobs: the pool ran them in parallel.", "insight")
    tl.wait(1.2)

    tl.chapter("version 1")
    tl.say("Now version 1. In while let, the guard lives until the end of the loop body.", "fail")
    tl.set(variant="v1", queued=4, owner=-1, p0=0.0, p1=0.0, p2=0.0, p3=0.0, clock=0.0,
           code=-1.0, held="")
    tl.wait(0.6)
    for k in range(4):
        if k == 0:
            tl.say("Worker 1 takes job 1 and runs it while still holding the lock.", "fail")
        take(k, 0.5 if k == 0 else 0.35)
        tl.set(code=1.0, waiting="".join(str(j) for j in range(4) if j != k))
        if k == 0:
            tl.say("The other workers block in lock(). They cannot even take a job.", "fail")
        tl.to(1.2 if k == 0 else 0.9, linear, **{"p%d" % k: 1.0, "clock": 204.0 * (k + 1)})
        tl.set(owner=-1)
    tl.set(waiting="", clock=814.0)
    tl.say("814 ms: four threads, but one job at a time. The lock turned the pool into a line.",
           "fail")
    tl.wait(1.6)

    def draw(p, s, total):
        t = s.t
        title_block(p, "Four workers, one shared receiver",
                    "A worker must release the receiver's lock before it runs the job.")
        scoreboard(p, [("elapsed", "%d ms" % int(round(s.clock)), RUST if s.variant == "v1"
                                                                    else TEAL)])
        channel_jobs(p, int(s.queued))
        rx, ry = RECEIVER
        p.rect(rx - 34, ry - 22, 68, 44, PAPER, INK, 8, 1.4)
        p.text(rx, ry + 4, "receiver", 10, INK, 600, "middle")
        if s.owner < 0:
            padlock(p, rx, ry - 34, TEAL)
            p.text(rx, ry + 38, "lock free", 10, TEAL, 700, "middle")
        else:
            x = WORKERS[int(s.owner)]
            padlock(p, x + 26, DESK - 70, RUST if s.variant == "v1" else BRASS)
            p.text(rx, ry + 38, "locked by %d" % (int(s.owner) + 1), 10,
                   RUST if s.variant == "v1" else BRASS, 700, "middle")
            p.line(rx + 34, ry, x - 20, DESK - 60, FAINT, 1.2, dash="4 4")
        for k in range(4):
            prog = getattr(s, "p%d" % k)
            waiting = str(k) in s.waiting
            note = "waiting for lock" if waiting else ("done" if prog >= 0.999 else "")
            worker(p, k, 0.0 if waiting else 1.0, TEAL, "worker %d" % (k + 1), prog, note,
                   NIGHT if waiting else TEAL)
            if str(k) in s.held and prog < 0.999:
                chip(p, WORKERS[k], DESK - 86, "job %d" % (k + 1), BRASS, BRASS_LT, 10)
        if s.fly_a > 0.01:
            a = (CHANNEL[1] - 34, CHANNEL[2])
            b = (WORKERS[int(s.fly_to)], DESK - 60)
            x, y = bezier(a, ((a[0] + b[0]) / 2, 70), b, s.fly_u)
            pill(p, x, y, "job %d" % (int(s.fly_to) + 1), BRASS, BRASS_LT, 10, opacity=s.fly_a,
                 shadow=None)

        panel = V1_LOOP if s.variant == "v1" else V2_LOOP
        title = "version 1 worker loop" if s.variant == "v1" else "version 2 worker loop"
        panel.draw(p, 26, 300, W - 52, title, s, t, reveal=False, size=10.8, lead=15.0,
                   tint=RUST if s.variant == "v1" else TEAL)
        caption(p, tl, t, CAP)
        progress(p, tl, t, total, RAIL)

    CAP, RAIL, height = layout(300, max(len(V1_LOOP), len(V2_LOOP)), 15.0)
    return tl, draw, height


# ---------------------------------------------------------- 18.5: a panicking job


def pool_panic():
    tl = Timeline(caption="", kind="step", code=-1.0, variant="v4", completed=0.0, panicked=0.0,
                  alive="1111", hit=-1, flash=0.0, queued=0.0, clock="")

    def job(k, panics, dur=0.7):
        tl.set(hit=k)
        tl.to(dur * 0.5, flash=1.0 if panics else 0.0)
        tl.set(code=1.0 if panics else 0.0)
        tl.to(dur * 0.5, flash=0.0)

    tl.chapter("version 4")
    tl.say("Version 4's workers run each job inside catch_unwind.")
    tl.set(code=0.0)
    for k in range(4):
        job(k, False, 0.6)
        tl.to(0.2, completed=float(k + 1))
    tl.say("Worker 2's job panics. The unwinding stops at catch_unwind, which returns Err.")
    tl.set(code=1.0)
    job(1, True, 1.2)
    tl.to(0.3, panicked=1.0)
    tl.set(code=3.0)
    tl.say("The worker counts the panic and goes back for the next job. All four are still "
           "running.", "insight")
    for k in range(4):
        job(k, False, 0.5)
        tl.to(0.15, completed=float(5 + k))
    tl.wait(0.8)

    tl.chapter("version 3")
    tl.say("Version 3 has no catch_unwind. A panic unwinds out of the worker loop and ends the "
           "thread.", "fail")
    tl.set(variant="v3", completed=0.0, panicked=0.0, alive="1111", code=-1.0, hit=-1)
    tl.wait(0.6)
    for k, label in ((1, "Worker 2"), (3, "Worker 4"), (0, "Worker 1"), (2, "Worker 3")):
        if k == 1:
            tl.say("Worker 2's job panics. The thread ends, and the pool does not notice.",
                   "fail")
        tl.set(code=1.0)
        job(k, True, 0.9 if k == 1 else 0.6)
        alive = list(tl._at("alive", tl.now))
        alive[k] = "0"
        tl.set(alive="".join(alive))
        tl.to(0.3, panicked=tl._at("panicked", tl.now) + 1)
    tl.say("After four panics no worker is left. Jobs keep arriving and wait forever.", "fail")
    for n, label in ((3, "1 s"), (6, "1 min"), (9, "forever")):
        tl.to(0.6, queued=float(n))
        tl.set(clock=label)
        tl.wait(0.4)
    tl.wait(1.2)

    def draw(p, s, total):
        t = s.t
        title_block(p, "A job that panics",
                    "catch_unwind keeps the worker alive. Without it, each panic ends a thread.")
        scoreboard(p, [("completed", int(round(s.completed)), TEAL),
                       ("panicked", int(round(s.panicked)), RUST)])
        channel_jobs(p, min(int(round(s.queued)), 4))
        if s.queued >= 1:
            p.text(CHANNEL[0], CHANNEL[2] + 34, "%d jobs queued" % int(round(s.queued)), 10.5,
                   RUST, 700)
        if s.clock:
            p.text(CHANNEL[1], CHANNEL[2] + 34, "waiting " + s.clock, 10.5, RUST, 700, "end",
                   mono=True)
        for k in range(4):
            gone = 1.0 if s.alive[k] == "0" else 0.0
            hit = int(s.hit) == k
            color = RUST if hit and s.flash > 0.3 else TEAL
            note = "thread ended" if gone else ("panic caught" if hit and s.flash > 0.3 and
                                                s.variant == "v4" else "")
            worker(p, k, 0.0 if gone else 1.0, color, "worker %d" % (k + 1), 0.0, note,
                   RUST if gone else BRASS, gone)
            if hit and not gone:
                busy = s.flash > 0.05
                chip(p, WORKERS[k], DESK - 86, "panic!" if busy else "job",
                     RUST if busy else BRASS, RUST_LT if busy else BRASS_LT, 10)

        panel = V4_LOOP if s.variant == "v4" else V3_LOOP
        title = "version 4 worker loop" if s.variant == "v4" else "version 3 worker loop"
        panel.draw(p, 26, 300, W - 52, title, s, t, reveal=False, size=10.8, lead=14.0,
                   tint=TEAL if s.variant == "v4" else RUST)
        caption(p, tl, t, CAP)
        progress(p, tl, t, total, RAIL)

    CAP, RAIL, height = layout(300, max(len(V3_LOOP), len(V4_LOOP)), 14.0)
    return tl, draw, height


def build_pool_lock(only=None):
    tl, draw, height = pool_lock()
    return render("ch18-pool-lock.gif", tl, draw, height, only=only)


def build_pool_panic(only=None):
    tl, draw, height = pool_panic()
    return render("ch18-pool-panic.gif", tl, draw, height, only=only)


BUILDERS = {
    "pool-lock": build_pool_lock,
    "pool-panic": build_pool_panic,
}
