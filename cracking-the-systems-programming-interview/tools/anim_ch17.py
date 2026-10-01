"""The queues chapter animations (ch17-queues.md): waiting on a condition
variable, closing a queue, and the lock-free ring buffer.

    python3 tools/animations.py queue-wait queue-close ring-spsc
"""

from motion import *  # noqa: F401,F403
from motion import Timeline, render
from motion_kit import Panel, Panels, layout

PRODUCER, CONSUMER = 96, 724
DESK = 236


def item_box(p, x, y, label, edge=BRASS, fill=BRASS_LT, opacity=1.0, w=50):
    if opacity <= 0.01:
        return
    p.rect(x - w / 2, y - 22, w, 44, fill, edge, 8, 1.8, opacity=opacity)
    p.text(x, y + 7, label, 18, INK, 700, "middle", mono=True, opacity=opacity)


def lock_badge(p, x, y, owner):
    """The mutex, with the name of the thread that holds it."""
    held = bool(owner)
    p.rect(x - 96, y - 16, 192, 32, BRASS_LT if held else STAGE, BRASS if held else LINE, 8, 1.4)
    p.text(x, y + 5, ("lock held by %s" % owner) if held else "lock free", 11.5,
           BRASS if held else MUTED, 700, "middle", mono=True)


# ------------------------------------------------- 17.2: waiting on a Condvar

SYNC = Panel("src/bin/thread_safe_queue.rs",
             [("fn push(&self, item: i32) {", "}"), ("fn pop(&self) -> Option<i32> {", "}")],
             ["if let Ok(mut q) = self.items.lock() {", "q.push_back(item);",
              "self.not_empty.notify_one();", "let q = self.items.lock().ok()?;",
              ".wait_while(q, |q| q.is_empty())", "q.pop_front()"])
SLOTS_X = [330, 410, 490]
QUEUE_Y = 160


def queue_wait():
    tl = Timeline(caption="", kind="step", code=-1.0, strike=-1.0, held="", lock="",
                  c_sleep=0.0, p_say="", c_say="", fly="", fly_u=0.0, fly_a=0.0, out_u=0.0,
                  out_a=0.0, out_v="", hang=0.0)

    def push(v, notify=True, slow=1.0):
        tl.set(p_say="push(%s)" % v, code=0.0, lock="producer")
        tl.wait(0.7 * slow)
        tl.set(code=1.0, fly=v, fly_u=0.0)
        tl.to(0.15, fly_a=1.0)
        tl.to(0.6 * slow, in_out, fly_u=1.0)
        tl.set(held=v, fly_a=0.0)
        tl.wait(0.4 * slow)
        if notify:
            tl.set(code=2.0).event("ring")
            tl.wait(1.0 * slow)
        tl.set(lock="", p_say="returned")

    tl.chapter("empty")
    tl.say("The queue is empty. The consumer calls pop, and lock gives it the mutex.")
    tl.set(code=3.0, lock="consumer", c_say="pop()")
    tl.wait(1.4)
    tl.say("wait_while checks is_empty(): true. In one step it releases the lock and puts the "
           "consumer to sleep.")
    tl.set(code=4.0)
    tl.wait(0.6)
    tl.set(lock="", c_say="asleep in wait_while")
    tl.to(0.5, c_sleep=1.0)
    tl.wait(1.2)

    tl.chapter("push")
    tl.say("The producer calls push. The lock is free, so it takes it and adds 7.")
    push("7", slow=1.3)
    tl.say("notify_one wakes one sleeping consumer. The producer's guard drops at the end of push, "
           "which frees the lock.")
    tl.wait(0.6)
    tl.set(code=4.0, lock="consumer", c_say="woken")
    tl.to(0.5, c_sleep=0.0)
    tl.say("The consumer wakes holding the lock. wait_while checks again: not empty, so it "
           "returns the guard.")
    tl.wait(1.4)
    tl.set(code=5.0, out_v="7", out_u=0.0)
    tl.to(0.15, out_a=1.0)
    tl.to(0.7, in_out, out_u=1.0)
    tl.to(0.15, out_a=0.0)
    tl.set(held="", c_say="popped 7", lock="")
    tl.say("pop_front returns Some(7). The consumer used no CPU while it waited.", "insight")
    tl.wait(1.6)

    tl.chapter("no notify")
    tl.set(strike=2.0, code=-1.0, c_say="asleep in wait_while", p_say="", lock="")
    tl.to(0.4, c_sleep=1.0)
    tl.say("Now take out notify_one. The consumer is asleep on the empty queue again.", "fail")
    tl.wait(1.4)
    push("8", notify=False, slow=1.0)
    tl.say("The producer adds 8 and returns. Nothing calls notify_one, so nothing wakes the "
           "consumer.", "fail")
    tl.wait(1.2)
    tl.to(0.4, hang=1.0)
    tl.say("8 sits in the queue while the consumer sleeps. With no more pushes, it sleeps "
           "forever.", "fail")
    tl.wait(2.2)

    def draw(p, s, total):
        t = s.t
        title_block(p, "Waiting for an item with a Condvar",
                    "wait_while sleeps with the lock released. notify_one wakes a sleeper.")
        robot(p, PRODUCER, DESK, "#3b7dd8", 1.0, 1.0, "producer", s.p_say or " ")
        robot(p, CONSUMER, DESK, TEAL, 1 - 0.85 * s.c_sleep, 1 - s.c_sleep, "consumer",
              s.c_say or " ")
        zzz(p, CONSUMER + 44, DESK - 108, t, s.c_sleep)
        age = s.timeline.age("ring", t)
        if age is not None and age < 1.2:
            ring_waves(p, CONSUMER - 40, DESK - 70, age)
        p.text(SLOTS_X[0] - 40, QUEUE_Y - 34, "VecDeque<i32>, behind the Mutex", 10.5, MUTED, 600)
        for x in SLOTS_X:
            p.rect(x - 32, QUEUE_Y - 26, 64, 52, STAGE, LINE, 8, 1.2, dash="4 4")
        if s.held:
            item_box(p, SLOTS_X[0], QUEUE_Y, s.held, RUST if s.hang > 0.5 else BRASS,
                     RUST_LT if s.hang > 0.5 else BRASS_LT)
        if s.fly_a > 0.01:
            item_box(p, lerp(PRODUCER + 60, SLOTS_X[0], s.fly_u), QUEUE_Y, s.fly, opacity=s.fly_a)
        if s.out_a > 0.01:
            item_box(p, lerp(SLOTS_X[0], CONSUMER - 60, s.out_u), QUEUE_Y, s.out_v,
                     TEAL, TEAL_LT, s.out_a)
        lock_badge(p, 410, 232, s.lock)
        if s.hang > 0.01:
            chip(p, CONSUMER, 92, "never woken", RUST, RUST_LT, 12, opacity=clamp(s.hang))
        SYNC.draw(p, 26, 300, W - 52, "SyncQueue::push and pop", s, t, strike=s.strike,
                  size=10.6, lead=14.4, tint=RUST if s.strike >= 0 else TEAL)
        caption(p, tl, t, CAP)
        progress(p, tl, t, total, RAIL)

    CAP, RAIL, height = layout(300, len(SYNC), 14.4)
    return tl, draw, height


# ------------------------------------------------- 17.6: closing a queue

QUEUE = "src/problems/bounded_queue.rs"
CLOSE = Panels(QUEUE,
               [[("pub fn push(&self, item: T) -> Result<(), T> {", "}")],
                [("pub fn pop(&self) -> Option<T> {", "}")],
                [("pub fn close(&self) {", "}")]],
               ["push", "pop", "close"],
               ["if state.closed {", "return Err(item);", "state.items.push_back(item);",
                "    .not_full", "if let Some(item) = state.items.pop_front() {", "return None;",
                "    .not_empty", "state.closed = true;", "self.not_empty.notify_all();",
                "self.not_full.notify_all();"])
CAP_X = [370, 450]


def queue_close():
    tl = Timeline(caption="", kind="step", code=-1.0, strike=-1.0, held="", closed=0.0,
                  p_sleep=0.0, c_sleep=0.0, p_say="", c_say="", main="", back_a=0.0, back_u=0.0,
                  back_v="", out_a=0.0, out_u=0.0, out_v="", hang=0.0, got="")

    def take(v, got):
        tl.set(code=4.0, out_v=v, out_u=0.0)
        tl.to(0.15, out_a=1.0)
        tl.to(0.6, in_out, out_u=1.0)
        tl.to(0.15, out_a=0.0)
        tl.set(c_say="pop() = Some(%s)" % v, got=got)

    tl.chapter("full")
    tl.set(held="1,2")
    tl.say("A queue with room for 2 holds 1 and 2. The producer calls push(3).")
    tl.wait(1.2)
    tl.set(code=0.0, p_say="push(3)")
    tl.wait(0.6)
    tl.say("Not closed, and full. The producer waits on not_full, with the lock released.")
    tl.set(code=3.0, p_say="waiting to push 3")
    tl.to(0.5, p_sleep=1.0)
    tl.wait(1.4)

    tl.chapter("close")
    tl.set(main="main: queue.close()")
    tl.say("main decides to shut down and calls close. The flag is set under the lock.")
    tl.set(code=7.0)
    tl.to(0.4, closed=1.0)
    tl.wait(1.0)
    tl.set(code=8.0).event("ring_c")
    tl.wait(0.5)
    tl.set(code=9.0).event("ring_p")
    tl.say("notify_all wakes every thread waiting on either condition variable.")
    tl.wait(1.0)
    tl.set(code=0.0, p_say="woken")
    tl.to(0.4, p_sleep=0.0)
    tl.say("The producer's loop checks closed first. It is true, so push returns Err(3).")
    tl.wait(1.0)
    tl.set(code=1.0, back_v="Err(3)", back_u=0.0)
    tl.to(0.15, back_a=1.0)
    tl.to(0.6, in_out, back_u=1.0)
    tl.set(p_say="push(3) = Err(3)")
    tl.to(0.15, back_a=0.0)
    tl.say("Err carries the item back, so the producer still owns 3. Nothing is lost.", "insight")
    tl.wait(1.4)

    tl.chapter("drain")
    tl.say("The consumer pops. A closed queue still gives up the items already in it.")
    take("1", "1")
    tl.set(held="2")
    tl.wait(0.6)
    take("2", "1, 2")
    tl.set(held="")
    tl.wait(0.6)
    tl.set(code=5.0, c_say="pop() = None")
    tl.say("Now the queue is empty and closed, so pop returns None. while let Some(item) = "
           "queue.pop() ends.", "insight")
    tl.wait(1.8)

    tl.chapter("no notify_all")
    tl.set(strike=8.0, code=-1.0, held="", closed=0.0, main="", c_say="waiting for an item",
           p_say="", got="")
    tl.to(0.4, c_sleep=1.0)
    tl.say("Now close without notify_all. The consumer is asleep on an empty queue.", "fail")
    tl.wait(1.4)
    tl.set(main="main: queue.close()", code=7.0)
    tl.to(0.4, closed=1.0)
    tl.say("close sets closed = true, and returns. Nobody wakes the consumer to see it.", "fail")
    tl.wait(1.4)
    tl.to(0.4, hang=1.0)
    tl.say("The consumer sleeps forever, and main's join on it never returns. Shutdown hangs.",
           "fail")
    tl.wait(2.2)

    def draw(p, s, total):
        t = s.t
        title_block(p, "Closing a queue: wake everyone, then let them finish",
                    "push hands the item back. pop drains what is left, then returns None.")
        robot(p, PRODUCER, DESK, "#3b7dd8", 1 - 0.85 * s.p_sleep, 1 - s.p_sleep, "producer",
              s.p_say or " ")
        zzz(p, PRODUCER + 44, DESK - 108, t, s.p_sleep)
        robot(p, CONSUMER, DESK, TEAL, 1 - 0.85 * s.c_sleep, 1 - s.c_sleep, "consumer",
              s.c_say or " ")
        zzz(p, CONSUMER + 44, DESK - 108, t, s.c_sleep)
        for name, x in (("ring_p", PRODUCER + 40), ("ring_c", CONSUMER - 40)):
            age = s.timeline.age(name, t)
            if age is not None and age < 1.2 and s.strike < 0:
                ring_waves(p, x, DESK - 70, age)
        p.text(CAP_X[0] - 32, QUEUE_Y - 34, "capacity 2", 10.5, MUTED, 600)
        for x in CAP_X:
            p.rect(x - 32, QUEUE_Y - 26, 64, 52, STAGE, LINE, 8, 1.2, dash="4 4")
        for k, v in enumerate([v for v in s.held.split(",") if v]):
            item_box(p, CAP_X[k], QUEUE_Y, v)
        closed = s.closed > 0.5
        chip(p, 410, 228, "closed: %s" % ("true" if closed else "false"),
             RUST if closed else MUTED, RUST_LT if closed else STAGE, 12)
        if s.main:
            chip(p, 410, 94, s.main, NIGHT, NIGHT_LT, 12)
        if s.back_a > 0.01:
            pill(p, lerp(CAP_X[0] - 40, PRODUCER + 50, s.back_u), QUEUE_Y + 46, s.back_v, RUST,
                 RUST_LT, 11, opacity=s.back_a, shadow=None)
        if s.out_a > 0.01:
            item_box(p, lerp(CAP_X[0], CONSUMER - 60, s.out_u), QUEUE_Y, s.out_v, TEAL, TEAL_LT,
                     s.out_a)
        if s.hang > 0.01:
            chip(p, CONSUMER, 92, "never woken", RUST, RUST_LT, 12, opacity=clamp(s.hang))
        CLOSE.draw(p, 26, 300, W - 52, s, t, strike=s.strike, size=10.4, lead=14.0,
                   tint=RUST if s.strike >= 0 else TEAL)
        caption(p, tl, t, CAP)
        progress(p, tl, t, total, RAIL)

    CAP, RAIL, height = layout(300, len(CLOSE), 14.0)
    return tl, draw, height


# ------------------------------------------------- 17.7: the SPSC ring

RING = "src/problems/ring_buffer.rs"
SPSC = Panels(RING,
              [[("pub fn push(&self, value: T) -> Result<(), T> {", "}")],
               [("pub fn pop(&self) -> Option<T> {", "}")]],
              ["push (the producer only)", "pop (the consumer only)"],
              ["let tail = self.tail.load(Ordering::Relaxed);",
               "let head = self.head.load(Ordering::Acquire);",
               "if tail.wrapping_sub(head) >= N {", "return Err(value);",
               "unsafe { (*self.slots[index].get()).write(value) };",
               ".store(tail.wrapping_add(1), Ordering::Release);",
               "let head = self.head.load(Ordering::Relaxed);",
               "let tail = self.tail.load(Ordering::Acquire);", "if head == tail {",
               "let value = unsafe { (*self.slots[index].get()).assume_init_read() };",
               ".store(head.wrapping_add(1), Ordering::Release);"])
EARLY = ["let index = tail % N;",
         "self.tail",
         "    .store(tail.wrapping_add(1), Ordering::Release);",
         "unsafe { (*self.slots[index].get()).write(value) };"]
N = 8
RX0, RSTEP, RY = 196, 61, 168


def ring_spsc():
    tl = Timeline(caption="", kind="step", code=-1.0, mode="ok", slots=",,,,,,,", head=0.0,
                  tail=0.0, hot=-1.0, p_say="", c_say="", fly_a=0.0, fly_u=0.0, fly_v="",
                  out_a=0.0, out_u=0.0, out_v="", back_a=0.0, back_v="", bad=-1.0)
    slots = [""] * N
    st = {"head": 0, "tail": 0}

    def show(**extra):
        tl.set(slots=",".join(slots), **extra)

    def push(v, k):
        tl.set(p_say="push(%s)" % v, code=0.0)
        tl.wait(0.4 * k)
        tl.set(code=1.0)
        tl.wait(0.3 * k)
        tl.set(code=2.0)
        tl.wait(0.3 * k)
        if st["tail"] - st["head"] >= N:
            tl.set(code=3.0, back_v="Err(%s)" % v)
            tl.to(0.3, back_a=1.0)
            tl.set(p_say="push(%s) = Err(%s)" % (v, v))
            return False
        i = st["tail"] % N
        tl.set(code=4.0, hot=float(i), fly_v=v, fly_u=0.0)
        tl.to(0.15, fly_a=1.0)
        tl.to(0.55 * k, in_out, fly_u=1.0)
        slots[i] = v
        show(fly_a=0.0)
        tl.wait(0.3 * k)
        st["tail"] += 1
        tl.set(code=5.0)
        tl.to(0.4 * k, in_out, tail=float(st["tail"]))
        tl.set(hot=-1.0, p_say="published %s" % v)
        tl.wait(0.3 * k)
        return True

    def pop(k):
        tl.set(c_say="pop()", code=6.0)
        tl.wait(0.4 * k)
        tl.set(code=7.0)
        tl.wait(0.3 * k)
        tl.set(code=8.0)
        tl.wait(0.3 * k)
        i = st["head"] % N
        v = slots[i]
        tl.set(code=9.0, hot=float(i), out_v=v, out_u=0.0)
        tl.to(0.15, out_a=1.0)
        tl.to(0.55 * k, in_out, out_u=1.0)
        slots[i] = ""
        show(out_a=0.0)
        st["head"] += 1
        tl.set(code=10.0)
        tl.to(0.4 * k, in_out, head=float(st["head"]))
        tl.set(hot=-1.0, c_say="popped %s" % v)
        tl.wait(0.3 * k)

    tl.chapter("push")
    tl.say("Eight slots and two counters. Only the producer writes tail; only the consumer "
           "writes head.")
    tl.wait(1.6)
    tl.say("push loads its own tail with Relaxed and the consumer's head with Acquire, then "
           "checks for room.")
    push("a", 1.5)
    tl.say("It writes the slot first. Then the Release store of tail publishes it: whoever reads "
           "tail with Acquire sees the slot written.", "insight")
    tl.wait(1.6)
    push("b", 0.7)
    push("c", 0.7)

    tl.chapter("pop")
    tl.say("pop is the mirror. An Acquire load of tail, then the slot, then a Release store of "
           "head frees it.")
    pop(1.4)
    pop(0.7)

    tl.chapter("wrap")
    for v in "defghi":
        push(v, 0.35)
    for _ in range(4):
        pop(0.35)
    tl.say("The counters only grow: tail is %d and head is %d. %% 8 maps them to slots %d and "
           "%d." % (st["tail"], st["head"], st["tail"] % N, st["head"] % N))
    tl.wait(2.0)

    tl.chapter("full")
    tl.say("The producer keeps pushing while the consumer is busy elsewhere.")
    n = 0
    while st["tail"] - st["head"] < N:
        push("jklmnopq"[n], 0.3)
        n += 1
    tl.say("tail - head is 8: full. The next push fails at the check.", "fail")
    tl.wait(1.0)
    push("r", 0.8)
    tl.say("push returns Err(r), handing the value back. No slot is overwritten.", "fail")
    tl.wait(1.8)

    tl.chapter("publish first")
    slots[:] = [""] * N
    st.update(head=0, tail=0)
    show(mode="early", head=0.0, tail=0.0, code=-1.0, back_a=0.0, p_say="", c_say="")
    tl.say("Now a push that stores tail before it writes the slot.", "fail")
    tl.wait(1.4)
    tl.set(p_say="push(x)", code=0.0, hot=0.0)
    tl.wait(0.5)
    tl.set(code=1.0)
    tl.to(0.4, tail=1.0)
    tl.say("tail is 1, and slot 0 is still empty. The consumer runs on another core.", "fail")
    tl.wait(1.2)
    tl.set(c_say="pop()", bad=0.0)
    tl.say("Its Acquire load sees tail = 1, so it reads slot 0: memory that was never written.",
           "fail")
    tl.wait(1.6)
    tl.set(code=3.0)
    slots[0] = "x"
    show()
    tl.say("The write lands too late. Reading uninitialized memory is undefined behaviour. The "
           "slot must be written before tail is stored.", "fail")
    tl.wait(2.4)

    def draw(p, s, total):
        t = s.t
        title_block(p, "A ring buffer without a lock",
                    "Write the slot, then publish the counter. The other side reads them in order.")
        robot(p, PRODUCER, DESK, "#3b7dd8", 1.0, 1.0, "producer", s.p_say or " ")
        robot(p, CONSUMER, DESK, TEAL, 1.0, 1.0, "consumer", s.c_say or " ")
        vals = s.slots.split(",")
        head, tail = int(round(s.head)), int(round(s.tail))
        for i in range(N):
            x = RX0 + i * RSTEP
            v = vals[i] if i < len(vals) else ""
            bad = abs(s.bad - i) < 0.5 and not v
            hot = abs(s.hot - i) < 0.5
            fill = RUST_LT if bad else (BRASS_LT if hot else (TEAL_LT if v else PAPER))
            edge = RUST if bad else (BRASS if hot else (TEAL if v else LINE))
            p.rect(x - 26, RY - 24, 52, 48, fill, edge, 7, 1.5, dash=None if v or hot or bad
                   else "4 4")
            p.text(x, RY + 7, "?" if bad else v, 18, RUST if bad else INK, 700, "middle",
                   mono=True)
            p.text(x, RY + 40, "[%d]" % i, 10, MUTED, 600, "middle", mono=True)
        # where each counter points, mapped with % N
        for name, value, color, dy in (("tail", tail, "#3b7dd8", -38), ("head", head, TEAL, 62)):
            x = RX0 + (value % N) * RSTEP
            label = "%s = %d  (%% 8 = %d)" % (name, value, value % N)
            p.text(x - 26, RY + dy, label, 11, color, 700, mono=True)
        if s.fly_a > 0.01:
            i = int(round(s.hot)) if s.hot >= 0 else 0
            item_box(p, lerp(PRODUCER + 60, RX0 + i * RSTEP, s.fly_u), RY - 70, s.fly_v,
                     opacity=s.fly_a, w=44)
        if s.out_a > 0.01:
            i = int(round(s.hot)) if s.hot >= 0 else 0
            item_box(p, lerp(RX0 + i * RSTEP, CONSUMER - 60, s.out_u), RY - 70, s.out_v, TEAL,
                     TEAL_LT, s.out_a, w=44)
        if s.back_a > 0.01:
            chip(p, PRODUCER + 120, 100, s.back_v, RUST, RUST_LT, 12, opacity=clamp(s.back_a))
        if s.mode == "early":
            code_panel(p, 26, 300, W - 52, "a push that publishes tail before writing the slot",
                       EARLY, s.code, size=10.4, lead=14.0, tint=RUST)
        else:
            SPSC.draw(p, 26, 300, W - 52, s, t, size=10.4, lead=14.0)
        caption(p, tl, t, CAP)
        progress(p, tl, t, total, RAIL)

    CAP, RAIL, height = layout(300, len(SPSC), 14.0)
    return tl, draw, height


def build_queue_wait(only=None):
    tl, draw, height = queue_wait()
    return render("ch17-queue-wait.gif", tl, draw, height, only=only)


def build_queue_close(only=None):
    tl, draw, height = queue_close()
    return render("ch17-queue-close.gif", tl, draw, height, only=only)


def build_ring_spsc(only=None):
    tl, draw, height = ring_spsc()
    return render("ch17-ring-spsc.gif", tl, draw, height, only=only)


BUILDERS = {
    "queue-wait": build_queue_wait,
    "queue-close": build_queue_close,
    "ring-spsc": build_ring_spsc,
}
