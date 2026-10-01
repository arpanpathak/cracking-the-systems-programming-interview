"""The async chapter animations (ch22-async.md), drawn with `motion`: things move, rather than swap.

    python3 tools/animations.py poll-wake task-queue await-state pin
"""

import math

from motion import *  # noqa: F401,F403
from motion import Timeline, render


# ---------------------------------------------------- 22.3: poll, park, wake

EX_X, CARD_X, TM_X = 128, 410, 690
DESK_Y = 258
CARD = (296, 112, 228, 158)          # x, y, w, h of the future
SLOT = (CARD[0] + 167, CARD[1] + 116)  # centre of the waker slot
CODE_Y = 350

BLOCK_ON = ["loop {",
            "  match fut.poll(&mut cx) {",
            "    Ready(v) => return v,",
            "    Pending => thread::park(),",
            "  }",
            "}"]
DELAY_POLL = ["let mut g = self.state.lock();",
              "if g.ready {",
              "  return Poll::Ready(());",
              "}",
              "g.waker = Some(cx.waker().clone());",
              "Poll::Pending"]
TIMER = ["thread::sleep(duration);",
         "g.ready = true;",
         "let w = g.waker.take();",
         "// the lock is released here",
         "if let Some(w) = w {",
         "  w.wake();",
         "}"]


def poll_wake():
    tl = Timeline(
        caption="", kind="step",
        ex_awake=1.0, ex_lit=1.0, cpu=0.0, ex_code=-1.0,
        tm_awake=0.0, tm_lit=0.0, tm_code=0.0, sw=0.0, clock="",
        dl_code=-1.0,
        poll_u=0.0, poll_a=0.0, poll_bell=1.0,
        res_u=0.0, res_a=0.0, res_label="Pending", res_color=RUST,
        ready=0.0, ready_focus=0.0, slot_focus=0.0,
        bx=0.0, by=0.0, ba=0.0, bs=1.0, stored=0.0,
        wave_u=0.0, wave_a=0.0,
        polls=0, wakes=0, bug=0.0, verdict=0.0, missing=0.0, done=0.0,
    )

    def say(text, kind="step"):
        tl.say(text, kind)

    def poll_trip(bell_rides=True):
        """The executor sends poll(cx), carrying the waker, across to the future."""
        tl.to(0.5, ex_code=1.0, cpu=1.0, ex_awake=1.0, ex_lit=1.0)
        tl.set(poll_u=0.0, poll_a=0.0, poll_bell=1.0 if bell_rides else 0.0)
        tl.set(polls=tl._at("polls", tl.now) + 1)
        tl.to(0.25, ease_out, poll_a=1.0)
        tl.to(1.1, in_out, poll_u=1.0)
        tl.to(0.2, poll_a=0.0)

    def reply(label, color):
        tl.set(res_u=0.0, res_label=label, res_color=color)
        tl.to(0.2, res_a=1.0)
        tl.to(1.0, in_out, res_u=1.0)
        tl.to(0.2, res_a=0.0)

    # ---- the cast
    tl.chapter("cast")
    say("block_on drives one future on this thread. A timer thread will finish the "
        "future's work in 50 ms.")
    tl.wait(3.2)
    sleep_from = tl.now

    # ---- first poll
    tl.chapter("poll")
    say("The executor calls poll. The Context cx carries a waker, drawn here as a bell: "
        "ringing it wakes this thread.")
    poll_trip()
    tl.to(0.4, dl_code=0.0)
    say("poll locks the shared state and reads ready. It is false, so the work is not done.")
    tl.to(0.35, dl_code=1.0, ready_focus=1.0)
    tl.wait(1.4)
    tl.to(0.3, ready_focus=0.0)
    say("Before returning Pending, poll stores a clone of the waker in the shared state.")
    ax, ay = CARD[0] + 8, CARD[1] + 80
    tl.set(bx=ax, by=ay, ba=1.0)
    tl.to(0.35, dl_code=4.0)
    tl.to(0.9, back, bx=SLOT[0], by=SLOT[1] + 9, slot_focus=1.0)
    tl.set(stored=1.0)
    tl.wait(1.2)
    tl.to(0.3, slot_focus=0.0, dl_code=5.0)
    say("Then it returns Pending to the executor.")
    reply("Pending", RUST)
    tl.set(dl_code=-1.0)

    # ---- park
    tl.chapter("park")
    say("Pending, so the executor parks the thread. A parked thread sleeps in the kernel "
        "and uses no CPU.")
    tl.to(0.4, ex_code=3.0)
    tl.to(1.2, in_out, ex_awake=0.0, ex_lit=0.0, cpu=0.0)
    tl.wait(2.4)
    tl._tween(sleep_from, tl.now - sleep_from, linear, {"sw": 1.0})

    # ---- wake
    tl.chapter("wake")
    say("50 ms pass. The timer thread wakes up and sets ready = true.")
    tl.to(0.6, back, tm_awake=1.0, tm_lit=1.0)
    tl.to(0.3, tm_code=1.0)
    tl.to(0.6, back, ready=1.0, ready_focus=1.0)
    tl.wait(0.9)
    tl.to(0.3, ready_focus=0.0)
    say("It takes the waker out of the state, and drops the lock before calling it.")
    tl.to(0.3, tm_code=2.0)
    tl.set(stored=0.0)
    tl.to(1.1, in_out, bx=TM_X - 84, by=DESK_Y - 52)
    tl.to(0.35, tm_code=3.0)
    tl.wait(0.6)
    say("wake() rings the bell. For this waker, ringing means unpark the executor thread.")
    tl.to(0.3, tm_code=5.0)
    tl.set(wakes=1).event("ring")
    tl.wait(0.6)
    tl.set(wave_u=0.0, wave_a=1.0)
    tl.to(1.2, in_out, wave_u=1.0)
    tl.also(0.5, ba=0.0)
    tl.also(0.9, in_out, cpu=1.0)
    tl.to(0.9, back, ex_awake=1.0, ex_lit=1.0, ex_code=1.0)
    tl.to(0.3, wave_a=0.0, tm_code=-1.0, tm_awake=0.0, tm_lit=0.0)

    # ---- ready
    tl.chapter("ready")
    say("The executor polls again. This time ready is true.")
    poll_trip(bell_rides=True)
    tl.to(0.35, dl_code=1.0, ready_focus=1.0)
    tl.wait(0.8)
    tl.to(0.3, dl_code=2.0, ready_focus=0.0)
    say("poll returns Ready(()), and block_on returns the value.")
    reply("Ready(())", TEAL)
    tl.to(0.35, ex_code=2.0, done=1.0)
    tl.to(0.5, cpu=0.0, ex_code=-1.0, dl_code=-1.0)
    say("Two polls and one wake. While the timer ran, the executor used no CPU at all.",
        "insight")
    tl.wait(4.0)

    # ---- the bug
    tl.chapter("no waker")
    tl.to(0.8, done=0.0, ready=0.0, sw=0.0, bug=1.0, polls=0, wakes=0,
          ex_awake=1.0, ex_lit=1.0, tm_code=0.0)
    say("Now delete one line: poll no longer stores the waker. Watch the same run.", "fail")
    tl.wait(2.8)
    sleep_from = tl.now
    say("poll reads ready = false and returns Pending. The waker is never stored.", "fail")
    poll_trip()
    tl.to(0.35, dl_code=1.0, ready_focus=1.0)
    tl.wait(0.4)
    tl.set(bx=CARD[0] + 8, by=CARD[1] + 80, ba=1.0)
    tl.to(0.3, ready_focus=0.0, dl_code=5.0)
    tl.to(1.0, ease_in, by=CARD[1] + CARD[3] + 50, ba=0.0)
    reply("Pending", RUST)
    tl.set(dl_code=-1.0)
    say("The executor parks, as before.", "fail")
    tl.to(0.4, ex_code=3.0)
    tl.to(1.0, in_out, ex_awake=0.0, ex_lit=0.0, cpu=0.0)
    tl.wait(1.2)
    tl._tween(sleep_from, tl.now - sleep_from, linear, {"sw": 1.0})
    say("The timer sets ready = true and takes the waker. The slot holds None, so there "
        "is nothing to call.", "fail")
    tl.to(0.5, back, tm_awake=1.0, tm_lit=1.0)
    tl.to(0.3, tm_code=1.0)
    tl.to(0.5, back, ready=1.0)
    tl.to(0.3, tm_code=2.0)
    tl.to(0.5, back, missing=1.0, slot_focus=1.0)
    tl.wait(1.6)
    tl.to(0.3, tm_code=-1.0, tm_awake=0.0, tm_lit=0.0, slot_focus=0.0)
    say("The executor sleeps forever. No panic, no error, no CPU use. The task is lost.",
        "fail")
    tl.to(0.5, verdict=1.0)
    for label in ("1 s", "10 s", "1 min", "1 hour", "forever"):
        tl.set(clock=label)
        tl.wait(0.9)
    tl.wait(1.6)

    def draw(p, s, total):
        t = s.t
        title_block(p, "A future is polled, parks the thread, and is woken",
                    "block_on and a Delay future, one poll at a time.")
        # scoreboard
        scoreboard(p, [("polls", int(round(s.polls)), TEAL), ("wakes", int(round(s.wakes)), BRASS)])

        # ---- the executor
        robot(p, EX_X, DESK_Y, TEAL, s.ex_awake, s.ex_lit, "executor thread", "block_on",
              look=s.poll_a * 0.8)
        zzz(p, EX_X + 44, DESK_Y - 108, t, 1 - s.ex_awake)
        meter(p, EX_X - 70, DESK_Y + 72, 140, s.cpu, TEAL if s.cpu > 0.05 else NIGHT, "CPU",
              "%d%%" % round(clamp(s.cpu) * 100))
        if s.done > 0.01:
            pill(p, EX_X, DESK_Y - 150, "returns ()", TEAL, TEAL_LT, 12, opacity=s.done,
                 shadow=None)

        # ---- the future
        x, y, w, h = CARD
        edge = mix(LINE, RUST, s.bug)
        p.rect(x, y, w, h, PAPER, edge, 12, 1.6, shadow="shadow")
        p.rect(x, y, w, 42, mix(STAGE, RUST_LT, s.bug), "none", 12)
        p.rect(x, y + 30, w, 12, mix(STAGE, RUST_LT, s.bug), "none", 0)
        p.text(x + 14, y + 20, "Delay", 15, INK, 700)
        p.text(x + 66, y + 20, "the future", 12, MUTED)
        p.text(x + 14, y + 36, "Arc<Mutex<DelayState>>", 10.5, MUTED, mono=True)
        # ready row
        ry = y + 70
        p.text(x + 16, ry + 5, "ready", 13, INK, 600, mono=True)
        focus(p, x + 96, ry - 13, 116, 26, s.ready_focus, BRASS, 4)
        rv = "true" if s.ready > 0.5 else "false"
        col = mix(RUST, TEAL, s.ready)
        pop = 1 + 0.18 * math.sin(math.pi * clamp(s.ready)) if 0 < s.ready < 1 else 1
        with p.group(scale=pop, cx=x + 154, cy=ry):
            chip(p, x + 154, ry, rv, col, mix(RUST_LT, TEAL_LT, s.ready), 13)
        # waker row
        wy = y + 116
        p.text(x + 16, wy + 5, "waker", 13, INK, 600, mono=True)
        focus(p, x + 96, wy - 20, 116, 40, s.slot_focus, RUST if s.missing > 0.5 else BRASS, 4)
        p.rect(x + 104, wy - 17, 100, 34, "#fbfcfd", FAINT, 8, 1.3, dash="4 4")
        if s.stored > 0.5 and s.ba > 0.01:
            p.text(x + 110, wy + 5, "Some(", 12, BRASS, 700, mono=True)
            p.text(x + 198, wy + 5, ")", 12, BRASS, 700, "end", mono=True)
        elif s.ba < 0.5 or s.stored < 0.5:
            none_col = mix(FAINT, RUST, s.missing)
            p.text(x + 154, wy + 5, "None", 13, none_col, 700 if s.missing > 0.5 else 400,
                   "middle", mono=True)
        if s.missing > 0.01:
            with p.group(opacity=clamp(s.missing), scale=s.missing, cx=x + 226, cy=wy):
                p.circle(x + 226, wy, 13, RUST)
                p.text(x + 226, wy + 6, "?", 17, PAPER, 700, "middle")

        # ---- the timer thread
        robot(p, TM_X, DESK_Y, "#7a6a4f", s.tm_awake, s.tm_lit, "timer thread",
              "spawned by Delay::new", look=-0.8)
        zzz(p, TM_X + 44, DESK_Y - 108, t, (1 - s.tm_awake) * 0.6)
        # stopwatch
        sx, sy, r = TM_X + 88, DESK_Y - 62, 21
        p.circle(sx, sy, r + 3, PAPER, INK, 2.2)
        p.rect(sx - 4, sy - r - 10, 8, 6, INK, "none", 1.5)
        sw = math.floor(s.sw * 60) / 60.0
        if sw > 0.001:
            a1 = -90 + 359.9 * clamp(sw)
            x1 = sx + r * math.cos(math.radians(a1))
            y1 = sy + r * math.sin(math.radians(a1))
            large = 1 if sw > 0.5 else 0
            p.path("M %s %s L %s %s A %s %s 0 %d 1 %s %s Z"
                   % (f2(sx), f2(sy), f2(sx), f2(sy - r), f2(r), f2(r), large, f2(x1), f2(y1)),
                   mix(BRASS_LT, BRASS, 0.55), "none")
        hand = -90 + 360 * sw
        p.line(sx, sy, sx + (r - 4) * math.cos(math.radians(hand)),
               sy + (r - 4) * math.sin(math.radians(hand)), INK, 2)
        p.circle(sx, sy, 2.4, INK)
        forever = bool(s.clock)
        p.text(sx, sy + r + 20, s.clock or "%d ms" % round(50 * sw), 12.5,
               RUST if forever else INK, 700, "middle", mono=True)

        # ---- the poll message
        if s.poll_a > 0.01:
            px = lerp(EX_X + 62, CARD[0] - 2, s.poll_u)
            py = DESK_Y - 88
            pill(p, px, py, "poll(cx)", TEAL, PAPER, 13,
                 icon="bell" if s.poll_bell > 0.5 else None,
                 opacity=s.poll_a, scale=lerp(0.85, 1.0, s.poll_a))
        if s.res_a > 0.01:
            rx = lerp(CARD[0] - 2, EX_X + 62, s.res_u)
            ry2 = DESK_Y - 30
            pill(p, rx, ry2, s.res_label, s.res_color,
                 TEAL_LT if s.res_color == TEAL else RUST_LT, 13, opacity=s.res_a)

        # ---- the bell
        age = s.timeline.age("ring", t)
        wiggle = 0.0
        if age is not None and age < 1.6:
            wiggle = 22 * math.sin(age * 26) * math.exp(-age * 2.2)
        if s.ba > 0.01:
            bell(p, s.bx, s.by, 1.0, wiggle, opacity=s.ba)
            if age is not None and s.ba > 0.5:
                ring_waves(p, s.bx, s.by - 14, age)

        # ---- the wake signal, from the timer thread to the executor
        if s.wave_a > 0.01:
            p0, p1, p2 = (TM_X - 40, DESK_Y - 128), (CARD_X, 60), (EX_X + 30, DESK_Y - 128)
            pts = [bezier(p0, p1, p2, s.wave_u * i / 24.0) for i in range(25)]
            d = "M " + " L ".join("%s %s" % (f2(a), f2(b)) for a, b in pts)
            p.path(d, "none", BRASS, 3, opacity=s.wave_a, dash="2 7")
            hx, hy = pts[-1]
            p.circle(hx, hy, 12, BRASS, opacity=0.3 * s.wave_a, filter="blur")
            p.circle(hx, hy, 6, BRASS, opacity=s.wave_a)
            mx, my = bezier(p0, p1, p2, 0.5)
            p.text(mx, my - 12, "wake()  =  unpark(executor)", 12.5, BRASS, 700, "middle",
                   mono=True, opacity=s.wave_a * clamp(s.wave_u * 3))

        # ---- the failure verdict
        if s.verdict > 0.01:
            with p.group(opacity=s.verdict):
                chip(p, EX_X, DESK_Y - 150, "parked forever", RUST, RUST_LT, 12.5)

        # ---- the code
        code_panel(p, 26, CODE_Y, 232, "executor: block_on", BLOCK_ON, s.ex_code, tint=TEAL,
                   reveal=s.timeline.reached('ex_code', t))
        code_panel(p, 270, CODE_Y, 282, "future: Delay::poll", DELAY_POLL, s.dl_code,
                   size=10.6, strike=4 if s.bug > 0.5 else None, tint=RUST if s.bug > 0.5 else TEAL,
                   reveal=s.timeline.reached('dl_code', t))
        code_panel(p, 564, CODE_Y, 230, "timer thread", TIMER, s.tm_code, size=10.8,
                   lead=15.6, tint=BRASS,
                   reveal=s.timeline.reached('tm_code', t))

        caption(p, tl, t, 520)
        progress(p, tl, t, total, 606)

    return tl, draw, 640


# ------------------------------------------------ 22.5: waking is scheduling

TASK_COLORS = {1: "#3b7dd8", 2: "#8a5cc2", 3: "#c0508a"}
Q_Y = 196                     # ticket centre line in the queue
SLOTS = [404, 510, 616]       # queue slots, front first
DESK = (262, 196)             # where the popped ticket is polled
TRAY_X = 744
TRAY = [150, 214, 278]        # completed tickets, top to bottom in finishing order
LOST = (262, 324)             # where a task with no wake ends up
TICKET_W, TICKET_H = 92, 100

RUN = ["loop {",
       "  let Some(task) = queue.pop_front() else { return };",
       "  let waker = Waker::from(task.clone());",
       "  let mut cx = Context::from_waker(&waker);",
       "  if task.future.poll(&mut cx).is_ready() {",
       "    task.completed = true;",
       "  }",
       "}"]
WAKE = ["impl Wake for Task {",
        "  fn wake_by_ref(self: &Arc<Self>) {",
        "    self.queue.push_back(self.clone());",
        "  }",
        "}"]


def ticket(p, x, y, n, left, total, scale=1.0, opacity=1.0, stamp=0.0, ring=None,
           lost=0.0, broken=False, glow=0.0):
    """One task: a ticket with its number, the yields it has left, and its bell."""
    if opacity <= 0.01:
        return
    color = mix(TASK_COLORS[n], FAINT, lost)
    w, h = TICKET_W, TICKET_H
    with p.group(opacity=opacity, scale=scale, cx=x, cy=y):
        if glow > 0.01:
            p.rect(x - w / 2 - 6, y - h / 2 - 6, w + 12, h + 12, "none", BRASS, 14, 2.4,
                   opacity=glow, dash="6 5")
        p.rect(x - w / 2, y - h / 2, w, h, mix(PAPER, STAGE, lost), mix(LINE, FAINT, lost), 10,
               1.4, shadow="shadow")
        p.rect(x - w / 2, y - h / 2, w, 26, color, "none", 10)
        p.rect(x - w / 2, y - h / 2 + 16, w, 10, color, "none", 0)
        p.text(x - w / 2 + 10, y - h / 2 + 18, "task %d" % n, 13, PAPER, 700)
        p.text(x, y + 2, "YieldTimes(%d)" % total, 10, MUTED, 400, "middle", mono=True)
        p.text(x, y + 22, "yields left", 9.5, FAINT, 400, "middle")
        for i in range(total):
            px = x - (total - 1) * 8 + i * 16
            full = i < left
            p.circle(px, y + 36, 5.2, color if full else PAPER, color, 1.6)
        # its own waker
        age = ring
        wig = 0.0
        if age is not None and age < 1.4:
            wig = 24 * math.sin(age * 26) * math.exp(-age * 2.4)
        bx, by = x + w / 2 - 14, y - h / 2 + 22
        bell(p, bx, by, 0.55, wig, fill=mix(BRASS, FAINT, lost))
        if age is not None:
            ring_waves(p, bx, by - 8, age, span=0.7, count=2)
        if broken:
            p.line(bx - 11, by - 17, bx + 11, by + 3, RUST, 2.4)
        if stamp > 0.01:
            a = clamp(stamp)
            with p.group(opacity=a, rotate=-12, cx=x, cy=y + 12, scale=lerp(1.8, 1.0, a)):
                p.rect(x - 42, y + 6 - 16, 84, 32, PAPER, "none", 7)
                p.rect(x - 38, y + 6 - 14, 76, 28, TEAL_LT, TEAL, 6, 2.6)
                p.text(x, y + 6 + 6, "Ready", 16, TEAL, 700, "middle")


def task_queue():
    init = dict(caption="", kind="step", ex_awake=1.0, ex_lit=1.0, run_code=-1.0,
                wake_code=-1.0, polls=0, done=0, bug=0.0, desk_glow=0.0, empty=0.0,
                limbo=0.0, verdict=0.0, pend=0.0)
    for n in (1, 2, 3):
        init.update({"x%d" % n: SLOTS[n - 1], "y%d" % n: Q_Y, "lift%d" % n: 0.0,
                     "s%d" % n: 1.0, "a%d" % n: 1.0, "left%d" % n: n, "stamp%d" % n: 0.0,
                     "lost%d" % n: 0.0})
    tl = Timeline(**init)

    def say(text, kind="step"):
        tl.say(text, kind)

    queue = [1, 2, 3]
    finished = []
    state = {"polls": 0}

    def pop(k):
        n = queue.pop(0)
        d = 0.8 * k
        tl.set(run_code=1.0)
        tl.also(d, in_out, **{"x%d" % n: DESK[0], "y%d" % n: DESK[1]})
        tl.also(d / 2, ease_out, **{"lift%d" % n: 1.0})
        tl.also(d / 2, ease_in, delay=d / 2, **{"lift%d" % n: 0.0})
        for i, m in enumerate(queue):
            tl.also(d * 0.8, in_out, delay=d * 0.25, **{"x%d" % m: SLOTS[i]})
        tl.wait(d)
        return n

    def poll(n, k):
        state["polls"] += 1
        tl.set(polls=state["polls"])
        tl.to(0.3 * k, run_code=4.0, desk_glow=1.0)
        tl.wait(0.5 * k)
        if tl._at("left%d" % n, tl.now) > 0:
            tl.to(0.45 * k, back, **{"left%d" % n: tl._at("left%d" % n, tl.now) - 1})
            tl.wait(0.3 * k)
            return "pending"
        return "ready"

    def requeue(n, k):
        tl.set(wake_code=2.0).event("ring%d" % n)
        tl.wait(0.7 * k)
        slot = SLOTS[len(queue)]
        queue.append(n)
        d = 1.2 * k
        tl.also(d, in_out, **{"x%d" % n: slot})
        tl.also(d / 2, ease_out, **{"lift%d" % n: 1.0})
        tl.also(d / 2, ease_in, delay=d / 2, **{"lift%d" % n: 0.0})
        tl.also(0.3, delay=d * 0.4, desk_glow=0.0)
        tl.event("pending", delay=d * 0.6)
        tl.wait(d)
        tl.set(wake_code=-1.0)

    def complete(n, k):
        tl.to(0.3 * k, run_code=5.0)
        tl.to(0.6 * k, back, **{"stamp%d" % n: 1.0})
        tl.wait(0.6 * k)
        finished.append(n)
        d = 0.9 * k
        tl.also(d, in_out, **{"x%d" % n: TRAY_X, "y%d" % n: TRAY[len(finished) - 1],
                              "s%d" % n: 0.58})
        tl.also(d / 2, ease_out, **{"lift%d" % n: 0.6})
        tl.also(d / 2, ease_in, delay=d / 2, **{"lift%d" % n: 0.0})
        tl.also(0.3, delay=d * 0.3, desk_glow=0.0)
        tl.wait(d)
        tl.set(done=len(finished))

    # ---- the cast
    tl.chapter("spawn")
    say("spawn put three tasks on the queue. Each wraps a YieldTimes future: task n yields "
        "n times, then returns Ready.")
    tl.wait(3.8)

    tl.chapter("round 1")
    say("run() pops the front task and polls it on this thread.")
    n = pop(1.0)
    poll(n, 1.0)
    say("YieldTimes uses up one yield and calls wake_by_ref(). The task is its own waker.")
    tl.wait(0.9)
    say("Waking a Task pushes it onto the back of the queue. Then poll returns Pending.")
    requeue(n, 1.0)
    tl.wait(0.4)
    say("Task 2 is popped and polled next. It yields, and its wake sends it to the back.")
    n = pop(0.8)
    poll(n, 0.8)
    requeue(n, 0.8)
    say("Task 3 does the same. After one poll each, the queue is 1, 2, 3 again.")
    n = pop(0.8)
    poll(n, 0.8)
    requeue(n, 0.8)
    say("Each yield gave every other task one turn. That is round-robin scheduling.",
        "insight")
    tl.wait(3.2)

    tl.chapter("round 2")
    say("Task 1 has no yields left. Its poll returns Ready, so run() marks it completed.")
    n = pop(0.9)
    poll(n, 0.9)
    complete(n, 0.9)
    say("Nobody wakes a finished task, so it never re-enters the queue.")
    tl.wait(1.8)

    tl.chapter("the rest")
    say("The same two rules run the rest: a yield goes to the back, and a Ready leaves.")
    while queue:
        n = pop(0.45)
        if poll(n, 0.45) == "pending":
            requeue(n, 0.45)
        else:
            complete(n, 0.45)
    tl.to(0.4, run_code=1.0, empty=1.0)
    say("The queue is empty, so run() returns. The tasks finished in the order 1, 2, 3.",
        "insight")
    tl.wait(4.0)

    # ---- the bug: task 1 returns Pending without waking
    tl.chapter("no wake")
    reset = {"run_code": -1.0, "empty": 0.0, "polls": 0, "done": 0, "bug": 1.0}
    for n in (1, 2, 3):
        reset.update({"x%d" % n: SLOTS[n - 1], "y%d" % n: Q_Y, "s%d" % n: 1.0,
                      "left%d" % n: n, "stamp%d" % n: 0.0})
    tl.to(1.0, in_out, **reset)
    state["polls"] = 0
    queue[:] = [1, 2, 3]
    finished.clear()
    say("Now break task 1: its future returns Pending without calling wake. Same run.",
        "fail")
    tl.wait(2.8)
    n = pop(0.9)
    poll(n, 0.9)
    say("Task 1 returned Pending, and nothing pushed it back. It is in no queue at all.",
        "fail")
    tl.to(0.3, pend=1.0)
    tl.wait(0.5)
    tl.to(1.1, in_out, x1=LOST[0], y1=LOST[1], s1=0.72, lost1=1.0, desk_glow=0.0, pend=0.0,
          limbo=1.0)
    tl.wait(1.4)
    say("Tasks 2 and 3 still run to the end.", "fail")
    while queue:
        n = pop(0.3)
        if poll(n, 0.3) == "pending":
            requeue(n, 0.3)
        else:
            complete(n, 0.3)
    tl.to(0.4, run_code=1.0, empty=1.0, verdict=1.0)
    say("run() returns with task 1 unfinished. No panic and no error: it just never ran "
        "again.", "fail")
    tl.wait(4.5)

    def draw(p, s, total):
        t = s.t
        title_block(p, "Waking a task puts it back on the queue",
                    "MiniExecutor::run pops the front task, polls it, and repeats until the "
                    "queue is empty.")
        scoreboard(p, [("polls", int(round(s.polls)), TEAL), ("completed", int(round(s.done)),
                                                               TEAL)])

        robot(p, 110, 258, TEAL, s.ex_awake, s.ex_lit, "executor thread", "run()", look=0.8)

        # the queue rail
        left, right = SLOTS[0] - 58, SLOTS[-1] + 58
        p.rect(left, 254, right - left, 6, "#e6ebf0", "none", 3)
        for x in SLOTS:
            p.rect(x - TICKET_W / 2 - 2, 140, TICKET_W + 4, 112, "none", LINE, 10, 1.2,
                   dash="4 5")
        p.text((left + right) / 2, 280, "run queue", 13, INK, 700, "middle")
        p.text((left + right) / 2, 297, "VecDeque<Arc<Task>>", 11, MUTED, 400, "middle",
               mono=True)
        p.text(left, 280, "front", 11, MUTED, 600)
        p.text(right, 280, "back", 11, MUTED, 600, "end")
        if s.empty > 0.01:
            p.text((left + right) / 2, 202, "empty", 18, FAINT, 700, "middle", opacity=s.empty)

        # the poll desk
        dx, dy = DESK
        p.rect(dx - 58, 138, 116, 116, "none", mix(LINE, TEAL, s.desk_glow), 12, 1.6,
               dash="4 5")
        p.text(dx, 276, "being polled", 11, TEAL, 600, "middle")
        age = s.timeline.age("pending", t)
        if s.pend > 0.01:
            pill(p, dx, 118, "Pending", RUST, RUST_LT, 12, opacity=s.pend, shadow=None)
        elif age is not None and age < 1.3:
            a = clamp(age / 0.2) * clamp((1.3 - age) / 0.4)
            pill(p, dx, 118 - 10 * age, "Pending", RUST, RUST_LT, 12, opacity=a, shadow=None)

        # the completed column
        p.text(TRAY_X, 106, "completed", 12, INK, 700, "middle")
        for y in TRAY:
            p.rect(TRAY_X - 30, y - 32, 60, 64, "none", LINE, 8, 1.1, dash="3 4")
        if s.limbo > 0.01:
            with p.group(opacity=s.limbo):
                p.text(LOST[0] + 46, LOST[1] - 6, "lost: in no queue,", 12, RUST, 700)
                p.text(LOST[0] + 46, LOST[1] + 11, "never polled again", 12, RUST, 700)

        # tickets, the moving ones last so they pass over the others
        order = sorted((1, 2, 3), key=lambda n: (s["lift%d" % n] > 0.001, s["y%d" % n] == DESK[1]))
        for n in order:
            lift = s["lift%d" % n]
            y = s["y%d" % n] - 90 * math.sin(math.pi * 0.5 * lift)
            ticket(p, s["x%d" % n], y, n, int(round(s["left%d" % n])), n,
                   s["s%d" % n] * (1 - 0.14 * lift),
                   1.0, s["stamp%d" % n], s.timeline.age("ring%d" % n, t), s["lost%d" % n],
                   broken=(n == 1 and s.bug > 0.5))

        code_panel(p, 26, 366, 432, "MiniExecutor::run", RUN, s.run_code, size=10.5, lead=15.2,
                   reveal=s.timeline.reached('run_code', t))
        code_panel(p, 470, 366, 324, "a task is its own waker", WAKE, s.wake_code,
                   size=10.5, lead=15.2, tint=BRASS,
                   reveal=s.timeline.reached('wake_code', t))
        caption(p, tl, t, 532)
        progress(p, tl, t, total, 618)

    return tl, draw, 652


# --------------------------------------- 22.6: what an async block compiles to

BLOCK = ["async {",
         "    let first = YieldTimes::new(1).await;",
         "    let second = YieldTimes::new(2).await;",
         "    first + second",
         "}"]
STATES = [("Start", "{ }"), ("AwaitingFirst", "{ inner }"),
          ("AwaitingSecond", "{ first, inner }"), ("Done", "{ }")]
CODE_BOX = (26, 84, 392)          # x, y, w of the code panel
LEAD = 27.0
MEM = (440, 84, 354, 176)         # the future's memory
NODE_Y, NODE_W, NODE_H = 300, 176, 56
NODE_X = [26 + i * (NODE_W + 17.3) for i in range(4)]
LANE_Y = 408


def await_state():
    tl = Timeline(caption="", kind="step", line=-1.0, mark=-1.0, mark_a=0.0, tag="Start",
                  node=0.0, first_a=0.0, fly_u=0.0, fly_a=0.0,
                  inner_n=1, inner_left=1.0, inner_a=0.0, inner_flash=0.0,
                  second_a=0.0, sum_a=0.0,
                  poll_u=0.0, poll_a=0.0, poll_n=0, res_u=0.0, res_a=0.0,
                  res_label="Pending", res_color=RUST, loop_a=0.0, fail=0.0)

    def say(text, kind="step"):
        tl.say(text, kind)

    def poll_in(n):
        tl.set(poll_n=n, poll_u=0.0)
        tl.to(0.2, poll_a=1.0)
        tl.to(1.0, in_out, poll_u=1.0)
        tl.to(0.2, poll_a=0.0)

    def reply(label, color):
        tl.set(res_u=0.0, res_label=label, res_color=color)
        tl.to(0.2, res_a=1.0)
        tl.to(1.0, in_out, res_u=1.0)
        tl.to(0.2, res_a=0.0)

    tl.chapter("the block")
    say("The compiler turns this async block into an enum with one variant per state. "
        "Nothing runs until it is polled.")
    tl.wait(3.8)

    # poll 1
    tl.chapter("poll 1")
    say("Poll 1 starts at the top of the block and runs to the first await.")
    poll_in(1)
    tl.to(0.5, line=1.0)
    say("YieldTimes::new(1) is created, and the await polls it. It yields: Pending.")
    tl.to(0.5, back, inner_a=1.0)
    tl.wait(0.3)
    tl.to(0.4, back, inner_left=0.0, inner_flash=1.0)
    tl.to(0.3, inner_flash=0.0)
    say("So the block saves its place, a bookmark at this await, keeps the inner future, "
        "and returns Pending too.")
    tl.to(0.5, back, mark=1.0, mark_a=1.0, tag="AwaitingFirst", node=1.0)
    tl.to(0.3, line=-1.0)
    reply("Pending", RUST)
    tl.wait(0.4)

    # poll 2
    tl.chapter("poll 2")
    say("Poll 2 does not start over. It jumps straight to the bookmark.")
    poll_in(2)
    tl.to(0.5, line=1.0)
    tl.wait(0.4)
    say("The inner future returns Ready(1), so first = 1. The inner future is dropped.")
    tl.to(0.3, inner_flash=1.0)
    tl.to(0.4, inner_a=0.0, inner_flash=0.0)
    say("first is still needed after the next await, so it moves into the future's memory.")
    tl.set(fly_u=0.0)
    tl.to(0.2, fly_a=1.0)
    tl.to(1.0, in_out, fly_u=1.0)
    tl.set(first_a=1.0)
    tl.to(0.2, fly_a=0.0)
    tl.to(0.5, line=2.0)
    say("YieldTimes::new(2) is created and polled. It yields, so the block saves its place "
        "again.")
    tl.set(inner_n=2, inner_left=2.0)
    tl.to(0.5, back, inner_a=1.0)
    tl.to(0.4, back, inner_left=1.0, inner_flash=1.0)
    tl.to(0.3, inner_flash=0.0)
    tl.to(0.5, back, mark=2.0, tag="AwaitingSecond", node=2.0)
    tl.to(0.3, line=-1.0)
    reply("Pending", RUST)

    # poll 3
    tl.chapter("poll 3")
    say("Poll 3 resumes at the second await. The inner future yields again.")
    poll_in(3)
    tl.to(0.5, line=2.0)
    tl.to(0.4, back, inner_left=0.0, inner_flash=1.0)
    tl.to(0.3, inner_flash=0.0)
    tl.to(0.4, loop_a=1.0)
    say("A Pending poll leaves the machine in the same state, with the same saved values.",
        "insight")
    tl.to(0.3, line=-1.0)
    reply("Pending", RUST)
    tl.wait(1.4)
    tl.to(0.3, loop_a=0.0)

    # poll 4
    tl.chapter("poll 4")
    say("Poll 4: the inner future returns Ready(2), so second = 2.")
    poll_in(4)
    tl.to(0.5, line=2.0)
    tl.to(0.3, inner_flash=1.0)
    tl.to(0.4, inner_a=0.0, inner_flash=0.0)
    tl.to(0.5, back, second_a=1.0)
    tl.wait(0.6)
    say("first + second is 3. The block returns Ready(3) and the enum becomes Done.")
    tl.to(0.5, line=3.0, sum_a=1.0)
    tl.to(0.6, back, tag="Done", node=3.0, mark_a=0.0, first_a=0.0)
    tl.to(0.3, line=-1.0)
    reply("Ready(3)", TEAL)
    say("first lived across an await, so the enum stored it. second never did, so it was "
        "never stored in the future.", "insight")
    tl.wait(4.2)

    # poll after ready
    tl.chapter("poll 5?")
    say("A fifth poll would find Done. There is no code to resume, so the compiled future "
        "panics.", "fail")
    tl.to(0.4, second_a=0.0, sum_a=0.0)
    poll_in(5)
    tl.to(0.4, back, fail=1.0)
    tl.wait(1.6)
    say("That is why MiniExecutor marks a task completed on Ready, and never polls it "
        "again.", "fail")
    tl.wait(3.4)

    def draw(p, s, total):
        t = s.t
        title_block(p, "An async block is an enum: one state per await",
                    "Each poll resumes at the saved state, runs to the next Pending, and "
                    "saves again.")
        scoreboard(p, [("poll", "#%d" % s.poll_n if s.poll_n else "-", TEAL)])

        # ---- the code, with its bookmark
        cx, cy, cw = CODE_BOX
        ch = 30 + len(BLOCK) * LEAD + 12
        p.rect(cx, cy, cw, ch, "#fbfcfd", LINE, 8, 1.2)
        p.text(cx + 14, cy + 20, "the async block", 11, MUTED, 600)
        if s.line >= 0:
            by = cy + 30 + s.line * LEAD
            p.rect(cx + 30, by, cw - 38, LEAD, mix(TEAL, PAPER, 0.84), "none", 4)
            p.rect(cx + 30, by, 3, LEAD, TEAL, "none", 1.5)
        for i, row in enumerate(BLOCK):
            near = s.line >= 0 and abs(s.line - i) < 0.5
            p.text(cx + 40, cy + 30 + i * LEAD + LEAD * 0.68, row, 12.4,
                   INK if near else MUTED, 600 if near else 400, mono=True)
        if s.mark_a > 0.01 and s.mark >= 0:
            my = cy + 30 + s.mark * LEAD + 2
            with p.group(opacity=clamp(s.mark_a)):
                bx = cx + 10
                p.path("M %s %s L %s %s L %s %s L %s %s L %s %s Z"
                       % (f2(bx), f2(my - 4), f2(bx + 14), f2(my - 4), f2(bx + 14), f2(my + 22),
                          f2(bx + 7), f2(my + 16), f2(bx), f2(my + 22)), BRASS, "none")
        p.text(cx + cw - 14, cy + ch - 16, "bookmark: where the next poll resumes", 11, BRASS,
               600, "end")

        # ---- the future's memory
        mx, my0, mw, mh = MEM
        p.rect(mx, my0, mw, mh, PAPER, mix(LINE, RUST, s.fail), 12, 1.6, shadow="shadow")
        p.text(mx + 14, my0 + 20, "the future in memory: one enum value", 11, MUTED, 600)
        # the state tag, flipping when it changes
        started, old = tl.changed("tag", t)
        u = clamp((t - started) / 0.5)
        shown = s.tag if u >= 0.5 or old is None else old
        squash = abs(math.cos(math.pi * u)) if 0 < u < 1 and old is not None else 1.0
        p.text(mx + 14, my0 + 54, "state", 12.5, INK, 600, mono=True)
        tag_fill = mix(TEAL_LT, RUST_LT, s.fail)
        tag_edge = mix(TEAL, RUST, s.fail)
        p.rect(mx + 84, my0 + 34, 256, 32, tag_fill, tag_edge, 7, 1.6)
        p.add('<g transform="translate(0 %s) scale(1 %s) translate(0 %s)">'
              % (f2(my0 + 50), f2(max(squash, 0.02)), f2(-(my0 + 50))))
        p.text(mx + 212, my0 + 56, shown, 15, tag_edge, 700, "middle", mono=True)
        p.add("</g>")
        # the payload: two slots
        rows = [(my0 + 82, "first"), (my0 + 126, "inner")]
        for ry, name in rows:
            p.rect(mx + 14, ry, mw - 28, 36, "#fbfcfd", LINE, 7, 1.1, dash="4 4")
        if s.first_a < 0.5:
            p.text(mx + mw / 2, my0 + 105, "unused in this state", 11, FAINT, 400, "middle",
                   italic=True)
        if s.first_a > 0.01:
            with p.group(opacity=s.first_a):
                p.rect(mx + 14, my0 + 82, mw - 28, 36, BRASS_LT, BRASS, 7, 1.4)
                p.text(mx + 28, my0 + 105, "first: usize", 12.5, INK, 600, mono=True)
                chip(p, mx + mw - 46, my0 + 100, "1", BRASS, PAPER, 13)
        if s.inner_a < 0.5:
            p.text(mx + mw / 2, my0 + 149, "unused in this state", 11, FAINT, 400, "middle",
                   italic=True)
        if s.inner_a > 0.01:
            with p.group(opacity=clamp(s.inner_a), scale=lerp(0.8, 1.0, clamp(s.inner_a)),
                         cx=mx + mw / 2, cy=my0 + 144):
                edge = mix(TEAL, BRASS, s.inner_flash)
                p.rect(mx + 14, my0 + 126, mw - 28, 36, mix(PAPER, BRASS_LT, s.inner_flash), edge,
                       7, 1.4)
                p.text(mx + 28, my0 + 149, "inner: YieldTimes(%d)" % s.inner_n, 12.5, INK, 600,
                       mono=True)
                left = s.inner_left
                for i in range(int(s.inner_n)):
                    px = mx + mw - 40 - (int(s.inner_n) - 1 - i) * 18
                    full = clamp(left - i)
                    p.circle(px, my0 + 144, 6, mix(PAPER, TEAL, full), TEAL, 1.6)
        p.text(mx + mw, my0 + mh + 18, "its size is fixed: room for the largest state",
               11, MUTED, 400, "end")

        # first, flying from the code into memory
        if s.fly_a > 0.01:
            a = (cx + 108, cy + 30 + 1 * LEAD + 12)
            b = (mx + mw - 46, my0 + 100)
            fx, fy = bezier(a, ((a[0] + b[0]) / 2, a[1] - 60), b, s.fly_u)
            pill(p, fx, fy, "first = 1", BRASS, BRASS_LT, 12.5, opacity=s.fly_a)
        # second, a plain local
        if s.second_a > 0.01:
            pill(p, cx + cw - 70, cy + 30 + 2 * LEAD + 14, "second = 2", MUTED, PAPER, 11.5,
                 opacity=clamp(s.second_a), shadow=None)
        if s.sum_a > 0.01:
            pill(p, cx + cw - 70, cy + 30 + 3 * LEAD + 14, "= 3", TEAL, TEAL_LT, 12,
                 opacity=clamp(s.sum_a), shadow=None)

        # ---- the four states
        p.text(26, NODE_Y - 12, "the enum's variants", 11, MUTED, 600)
        for i, (name, fields) in enumerate(STATES):
            x = NODE_X[i]
            near = clamp(1 - abs(s.node - i))
            failing = s.fail > 0.01 and i == 3
            fill = mix(PAPER, TEAL_LT, near)
            edge = mix(LINE, TEAL, near)
            if failing:
                fill, edge = mix(fill, RUST_LT, s.fail), mix(edge, RUST, s.fail)
            p.rect(x, NODE_Y, NODE_W, NODE_H, fill, edge, 10, 1.4 + near)
            p.text(x + NODE_W / 2, NODE_Y + 23, name, 13, INK, 700, "middle", mono=True)
            p.text(x + NODE_W / 2, NODE_Y + 42, fields, 11.5, MUTED, 400, "middle", mono=True)
            if i < 3:
                x1, x2 = x + NODE_W + 2, NODE_X[i + 1] - 2
                p.line(x1, NODE_Y + NODE_H / 2, x2 - 4, NODE_Y + NODE_H / 2, FAINT, 1.6)
                p.path("M %s %s L %s %s L %s %s Z" % (f2(x2), f2(NODE_Y + NODE_H / 2),
                                                      f2(x2 - 7), f2(NODE_Y + NODE_H / 2 - 4),
                                                      f2(x2 - 7), f2(NODE_Y + NODE_H / 2 + 4)),
                       FAINT, "none")
        # the marker that travels between states
        k = clamp(s.node, 0, 3)
        gx = lerp(NODE_X[int(math.floor(k))], NODE_X[min(3, int(math.floor(k)) + 1)], k % 1.0)
        p.rect(gx - 4, NODE_Y - 4, NODE_W + 8, NODE_H + 8, "none",
               RUST if s.fail > 0.5 else TEAL, 13, 2.6)
        if s.loop_a > 0.01:
            lx = NODE_X[2] + NODE_W / 2
            with p.group(opacity=s.loop_a):
                p.path("M %s %s C %s %s %s %s %s %s"
                       % (f2(lx + 30), f2(NODE_Y - 4), f2(lx + 34), f2(NODE_Y - 36),
                          f2(lx - 34), f2(NODE_Y - 36), f2(lx - 26), f2(NODE_Y - 8)),
                       "none", RUST, 2.2)
                p.path("M %s %s L %s %s L %s %s Z" % (f2(lx - 26), f2(NODE_Y - 4), f2(lx - 33),
                                                      f2(NODE_Y - 13), f2(lx - 21), f2(NODE_Y - 13)),
                       RUST, "none")
                p.text(lx - 44, NODE_Y - 22, "Pending: same state", 11, RUST, 700, "end")

        # ---- the poll lane
        p.text(26, LANE_Y + 5, "executor", 12.5, INK, 700)
        p.line(96, LANE_Y, W - 26, LANE_Y, LINE, 1.4, dash="3 5")
        target = NODE_X[int(round(clamp(s.node, 0, 3)))] + NODE_W / 2
        if s.poll_a > 0.01:
            px = lerp(140, target, s.poll_u)
            pill(p, px, LANE_Y, "poll #%d" % s.poll_n, TEAL, PAPER, 12.5, opacity=s.poll_a)
        if s.res_a > 0.01:
            px = lerp(target, 140, s.res_u)
            pill(p, px, LANE_Y, s.res_label, s.res_color,
                 TEAL_LT if s.res_color == TEAL else RUST_LT, 12.5, opacity=s.res_a)
        if s.fail > 0.01:
            with p.group(opacity=clamp(s.fail)):
                pill(p, NODE_X[3] + NODE_W / 2, LANE_Y, "panic", RUST, RUST_LT, 13,
                     scale=lerp(1.4, 1.0, clamp(s.fail)))

        caption(p, tl, t, 438)
        progress(p, tl, t, total, 526)

    return tl, draw, 560


# ---------------------------------------------- 22.6: why a future is pinned

BOX_W, BOX_H = 230, 150
BOX_Y = 132
ADDR_A, ADDR_B = 70, 520            # left edges of the two places a future can sit
RULER_Y = 318
HANDLE = [(150, 186), (150, 262)]   # two stack slots a Pin<Box<_>> handle can sit in
GARBAGE = ["#", "?", "!", "0"]


def future_box(p, x, y, letters, r_text, title="future", pinned=0.0, tint=LINE,
               opacity=1.0, shake=0.0, r_color=INK):
    """A suspended future: a buffer, and r, a reference into that buffer."""
    x += shake
    with p.group(opacity=opacity):
        p.rect(x, y, BOX_W, BOX_H, PAPER, tint, 12, 1.6, shadow="lift")
        p.rect(x, y, BOX_W, 32, STAGE, "none", 12)
        p.rect(x, y + 20, BOX_W, 12, STAGE, "none", 0)
        p.text(x + 14, y + 22, title, 13.5, INK, 700)
        p.text(x + BOX_W - 14, y + 22, "suspended at an await", 10.5, MUTED, 400, "end")
        p.text(x + 16, y + 67, "buf", 13, INK, 600, mono=True)
        for i, ch in enumerate(letters):
            cx = x + 70 + i * 36
            bad = ch in GARBAGE
            p.rect(cx, y + 46, 30, 30, RUST_LT if bad else BRASS_LT, RUST if bad else BRASS, 5,
                   1.3)
            p.text(cx + 15, y + 67, ch, 15, RUST if bad else INK, 700, "middle", mono=True)
        p.text(x + 16, y + 121, "r", 13, INK, 600, mono=True)
        p.rect(x + 70, y + 100, 102, 30, "#fbfcfd", LINE, 5, 1.3)
        p.text(x + 121, y + 121, r_text, 13, r_color, 700, "middle", mono=True)
        p.text(x + 182, y + 121, "= &buf", 11, MUTED, 400, mono=True)
        if pinned > 0.01:
            # a push pin, pressed into the top edge
            px, py = x + BOX_W - 26, y - 4 - 22 * (1 - clamp(pinned))
            with p.group(opacity=clamp(pinned * 2)):
                p.line(px, py, px + 4, py + 16, "#6b7785", 2.4)
                p.circle(px - 2, py - 6, 9, RUST)
                p.circle(px - 5, py - 9, 3, "#f3a98a")


def pin_move():
    tl = Timeline(caption="", kind="step", bx=ADDR_A, box_a=1.0, ghost=0.0, garbage=0.0,
                  arrow_a=1.0, dangling=0.0, read_bad=0.0, heap=0.0, hx=150.0, hy=186.0,
                  handle_a=0.0, pinned=0.0, shake=0.0, reject=0.0, safe=0.0, code="",
                  code_a=0.0, unpin=0.0, ux=0.0)

    def say(text, kind="step"):
        tl.say(text, kind)

    def show_code(text):
        tl.to(0.2, code_a=0.0)
        tl.set(code=text)
        tl.to(0.3, code_a=1.0)

    tl.chapter("a borrow")
    say("This future is suspended. Its state holds buf, and r, a reference to buf that is "
        "used after the await.")
    tl.wait(4.0)

    tl.chapter("a move")
    say("Moving a value copies its bytes to a new address. Nothing rewrites the pointers "
        "inside it.")
    show_code("let moved = fut;")
    tl.wait(0.6)
    tl.to(1.8, in_out, bx=ADDR_B, ghost=1.0)
    tl.wait(0.4)
    say("buf now lives at 0x2000, but r still holds 0x1000. The old place is free for "
        "anything to reuse.", "fail")
    tl.to(0.5, dangling=1.0)
    tl.wait(0.6)
    tl.to(0.8, garbage=1.0)
    tl.wait(1.2)
    say("The next poll reads through r and gets whatever lives at 0x1000 now. Pin exists "
        "to rule this out.", "fail")
    show_code("fut.poll(cx)  // reads *r")
    tl.to(0.5, back, read_bad=1.0)
    tl.wait(3.0)

    tl.chapter("pinned")
    tl.to(0.8, box_a=0.0, ghost=0.0, garbage=0.0, dangling=0.0, read_bad=0.0, arrow_a=0.0,
          code_a=0.0)
    tl.set(bx=ADDR_B)
    say("Box::pin puts the future on the heap and pins it there. The program holds a "
        "Pin<Box<_>>, a pointer.")
    show_code("let mut fut = Box::pin(fut);")
    tl.to(0.6, box_a=1.0, heap=1.0, handle_a=1.0)
    tl.to(0.6, back, pinned=1.0)
    tl.to(0.5, arrow_a=1.0)
    tl.wait(2.0)
    say("Moving the Pin<Box<_>> moves only that pointer. The future stays at 0x2000, so r "
        "stays valid.", "insight")
    show_code("let moved = fut;")
    tl.to(1.4, in_out, hy=HANDLE[1][1])
    tl.to(0.4, back, safe=1.0)
    tl.wait(2.6)

    tl.chapter("rejected")
    say("To move the future itself, code needs a &mut to it. Pin does not hand one out for "
        "a type that is not Unpin.")
    show_code("mem::swap(&mut *fut, &mut other);")
    tl.event("shake")
    tl.wait(0.9)
    tl.to(0.4, back, reject=1.0)
    tl.wait(3.0)

    tl.chapter("Unpin")
    tl.to(0.5, reject=0.0, safe=0.0)
    say("A type with no reference into itself, like YieldTimes, is Unpin. Pin places no "
        "limit on it.", "insight")
    show_code("self.get_mut()  // fine for Unpin")
    tl.to(0.5, unpin=1.0)
    tl.to(1.2, in_out, ux=1.0)
    tl.to(1.2, in_out, ux=0.0)
    tl.wait(2.2)

    def draw(p, s, total):
        t = s.t
        title_block(p, "Why a future that borrows from itself must not move",
                    "Pin<&mut Self> is the promise that the future keeps one address after "
                    "its first poll.")

        # the address ruler
        p.line(40, RULER_Y, W - 26, RULER_Y, LINE, 1.6)
        p.text(40, RULER_Y + 42, "memory", 11, MUTED, 600)
        for x, label, a in ((ADDR_A, "0x1000", 1 - s.heap), (ADDR_B, "0x2000", 1.0)):
            if a > 0.01:
                p.line(x, RULER_Y - 6, x, RULER_Y + 6, FAINT, 1.6, opacity=a)
                p.text(x, RULER_Y + 22, label, 12, MUTED, 600, "middle", mono=True, opacity=a)
        if s.heap > 0.01:
            with p.group(opacity=s.heap):
                p.rect(ADDR_B - 20, 112, BOX_W + 40, RULER_Y - 122, "none", TEAL, 14, 1.4,
                       dash="5 5")
                p.text(ADDR_B - 30, RULER_Y - 14, "heap", 12, TEAL, 700, "end")
                p.rect(40, 150, 260, RULER_Y - 160, "none", FAINT, 14, 1.4, dash="5 5")
                p.text(52, 168, "stack", 12, MUTED, 700)
                for i, (hx, hy) in enumerate(HANDLE):
                    p.text(52, hy + 5, "ab"[i], 12, MUTED, 600, mono=True)

        # the ghost left behind at 0x1000
        if s.ghost > 0.01 and s.heap < 0.5:
            with p.group(opacity=clamp(s.ghost)):
                p.rect(ADDR_A, BOX_Y, BOX_W, BOX_H, "none", FAINT, 12, 1.4, dash="5 5")
                for i, ch in enumerate("ping"):
                    cx = ADDR_A + 70 + i * 36
                    bad = s.garbage > 0.5
                    p.rect(cx, BOX_Y + 46, 30, 30, RUST_LT if bad else STAGE,
                           RUST if bad else FAINT, 5, 1.2, dash=None if bad else "3 3")
                    p.text(cx + 15, BOX_Y + 67, GARBAGE[i] if bad else ch, 15,
                           RUST if bad else FAINT, 700, "middle", mono=True)
                p.text(ADDR_A + BOX_W / 2, BOX_Y + 118, "freed, then reused" if s.garbage > 0.5
                       else "old copy", 12, RUST if s.garbage > 0.5 else FAINT, 700, "middle")

        # the future itself
        age = s.timeline.age("shake", t)
        shake = 0.0
        if age is not None and age < 0.9:
            shake = 9 * math.sin(age * 40) * math.exp(-age * 4)
        r_text = "0x1000" if s.heap < 0.5 else "0x2000"
        future_box(p, s.bx, BOX_Y, "ping", r_text, "future", s.pinned,
                   mix(LINE, RUST, s.dangling), s.box_a, shake,
                   RUST if s.dangling > 0.5 else INK)

        # r's arrow: its tail rides with the future, its head stays where r points
        if s.arrow_a > 0.01:
            tail = (s.bx + shake + 86, BOX_Y + 100)
            if s.heap > 0.5:
                head = (s.bx + shake + 85, BOX_Y + 78)
            else:
                head = (ADDR_A + 85, BOX_Y + 78)
            color = mix(TEAL, RUST, s.dangling)
            if abs(tail[0] - head[0]) < 4:
                d = "M %s %s L %s %s" % (f2(tail[0]), f2(tail[1]), f2(head[0]), f2(head[1] + 6))
            else:
                mxp = (tail[0] + head[0]) / 2
                d = "M %s %s C %s %s %s %s %s %s" % (f2(tail[0]), f2(tail[1]), f2(tail[0] - 40),
                                                     f2(BOX_Y + 30), f2(mxp + 80), f2(BOX_Y - 10),
                                                     f2(head[0]), f2(head[1] + 6))
            with p.group(opacity=clamp(s.arrow_a)):
                p.path(d, "none", color, 2.4)
                hx, hy = head
                p.path("M %s %s L %s %s L %s %s Z" % (f2(hx), f2(hy), f2(hx - 5), f2(hy + 9),
                                                      f2(hx + 5), f2(hy + 9)), color, "none")
        if s.read_bad > 0.01:
            with p.group(opacity=clamp(s.read_bad)):
                pill(p, ADDR_A + BOX_W / 2, BOX_Y - 22, "*r reads \"#?!0\"", RUST, RUST_LT, 12.5,
                     scale=lerp(1.3, 1.0, clamp(s.read_bad)))

        # the Pin<Box<_>> handle on the stack, pointing at the heap
        if s.handle_a > 0.01:
            with p.group(opacity=s.handle_a):
                hx, hy = s.hx, s.hy
                p.rect(hx - 70, hy - 18, 140, 36, PAPER, TEAL, 8, 1.6, shadow="shadow")
                p.text(hx, hy + 5, "Pin<Box<_>>", 12.5, TEAL, 700, "middle", mono=True)
                x2, y2 = ADDR_B - 4, BOX_Y + 20
                p.path("M %s %s C %s %s %s %s %s %s" % (f2(hx + 70), f2(hy), f2(hx + 170),
                                                        f2(hy), f2(x2 - 90), f2(y2), f2(x2 - 8),
                                                        f2(y2)), "none", TEAL, 2)
                p.path("M %s %s L %s %s L %s %s Z" % (f2(x2), f2(y2), f2(x2 - 9), f2(y2 - 5),
                                                      f2(x2 - 9), f2(y2 + 5)), TEAL, "none")
        if s.safe > 0.01:
            with p.group(opacity=clamp(s.safe)):
                pill(p, ADDR_B + BOX_W / 2, BOX_Y + BOX_H + 22, "r still points at buf", TEAL,
                     TEAL_LT, 12, shadow=None)
        if s.reject > 0.01:
            with p.group(opacity=clamp(s.reject)):
                pill(p, ADDR_B + BOX_W / 2, BOX_Y + BOX_H + 22, "rejected at compile time",
                     RUST, RUST_LT, 12, shadow=None, scale=lerp(1.3, 1.0, clamp(s.reject)))
        if s.unpin > 0.01:
            with p.group(opacity=clamp(s.unpin)):
                ux = lerp(84, 164, s.ux)
                p.rect(ux, HANDLE[0][1] - 22, 124, 44, PAPER, TEAL, 8, 1.6, shadow="shadow")
                p.text(ux + 62, HANDLE[0][1] - 4, "YieldTimes", 12, INK, 700, "middle",
                       mono=True)
                p.text(ux + 62, HANDLE[0][1] + 13, "Unpin: moves freely", 10, TEAL, 600,
                       "middle")

        # the line of code being run
        if s.code_a > 0.01 and s.code:
            w = text_width(s.code, 13, True) + 28
            with p.group(opacity=s.code_a):
                p.rect(W - 26 - w, 76, w, 28, SCREEN, "none", 7)
                p.text(W - 26 - w / 2, 95, s.code, 13, "#e8eef3", 600, "middle", mono=True)

        caption(p, tl, t, 386)
        progress(p, tl, t, total, 474)

    return tl, draw, 508


def build_poll_wake(only=None):
    tl, draw, height = poll_wake()
    return render("ch22-poll-wake.gif", tl, draw, height, only=only)


def build_task_queue(only=None):
    tl, draw, height = task_queue()
    return render("ch22-task-queue.gif", tl, draw, height, only=only,
                  extra_colors=TASK_COLORS.values())


def build_await_state(only=None):
    tl, draw, height = await_state()
    return render("ch22-await.gif", tl, draw, height, only=only)


def build_pin(only=None):
    tl, draw, height = pin_move()
    return render("ch22-pin.gif", tl, draw, height, only=only)


BUILDERS = {
    "poll-wake": build_poll_wake,
    "task-queue": build_task_queue,
    "await-state": build_await_state,
    "pin": build_pin,
}

if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    if args and args[0] == "frames":
        name = args[1]
        times = [float(a) for a in args[2:]]
        for path in BUILDERS[name](only=times):
            print(path)
    else:
        for name in args or BUILDERS:
            print(BUILDERS[name]())
