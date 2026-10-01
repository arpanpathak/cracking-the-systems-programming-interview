"""The animations for chapters 13, 14, 16, 17, and 19, drawn with `motion`.

    python3 tools/animations.py lru ring spin-lock deadlock bounded-buffer token-bucket
"""

import math

from motion import (BRASS, BRASS_LT, FAINT, INK, LINE, MUTED, NIGHT, PAPER, RUST, RUST_LT,
                    TEAL, TEAL_LT, W, caption, chip, code_panel, pill, progress, render, robot,
                    title_block, zzz)
from motion_kit import NAVY, layout, line_of, play, source


def furniture(p, tl, t, total, title, sub, code_title, code, line, cap_y, rail_y, code_y,
              tint=TEAL, size=11.0, lead=15.6, strike=-1.0):
    title_block(p, title, sub)
    code_panel(p, 26, code_y, W - 52, code_title, code, line, size=size, lead=lead,
               tint=RUST if strike >= 0 else tint, reveal=tl.reached("code", t),
               strike=int(strike) if strike >= 0 else None)
    caption(p, tl, t, cap_y)
    progress(p, tl, t, total, rail_y)


# ------------------------------------------------------------- 13: LRU cache


def lru():
    rules = ["get(key): on a hit, the key moves to the most recent end",
             "put(key, value): the key moves to the most recent end",
             "put of a new key into a full cache: evict the least recent end"]
    calls = [("put(A, 1)", "put", "A"), ("put(B, 2)", "put", "B"), ("get(A)", "get", "A"), ("put(C, 3)", "put", "C")]

    def run(calls, label, fail=False):
        order = []          # most recent first
        out = [dict(chapter=label, say="A cache with room for two entries. The left end is the most recent, "
                    "the right end is evicted next.", order=[], call="", evicted="", code=-1.0)]
        for text, op, key in calls:
            if op == "get":
                order.remove(key)
                order.insert(0, key)
                out.append(dict(say="%s is a hit, and a hit counts as a use, so A moves to the most recent end."
                                % text, call=text, order=list(order), evicted="", code=0.0))
            else:
                if key not in order and len(order) == 2:
                    gone = order.pop()
                    out.append(dict(say="%s: %s is new and the cache is full, so %s, the least recent entry, is "
                                    "evicted." % (text, key, gone), call=text, evicted=gone, order=list(order),
                                    code=2.0, kind="fail" if fail else "step"))
                order.insert(0, key)
                out.append(dict(say="%s puts %s at the most recent end." % (text, key), call=text,
                                order=list(order), code=1.0, evicted="" if not out[-1].get("evicted") else
                                out[-1]["evicted"]))
        return out

    steps = run(calls, "with get(A)")
    steps.append(dict(say="B was evicted, because get(A) made A more recent than B.", kind="insight", code=-1.0,
                      hold=1.2))
    steps += run([c for c in calls if c[1] != "get"], "without get(A)", fail=True)
    steps.append(dict(say="Without the get, A is the least recent entry when C arrives, so A is evicted "
                      "instead.", kind="fail", code=-1.0, hold=1.8))
    tl = play(steps, dict(order=[], call="", evicted="", code=-1.0))

    def draw(p, s, total):
        t = s.t
        p.text(W / 2, 112, s.call, 22, NAVY, 700, "middle", mono=True)
        x0 = 250
        for k in range(2):
            p.rect(x0 + k * 170, 140, 150, 110, "#f6f8fa", LINE, 12, 1.4, dash="5 5")
        p.text(x0 + 75, 272, "most recent", 12, TEAL, 700, "middle")
        p.text(x0 + 170 + 75, 272, "evicted next", 12, RUST, 700, "middle")
        for k, key in enumerate(s.order):
            p.rect(x0 + k * 170 + 10, 150, 130, 90, TEAL_LT if k == 0 else PAPER, TEAL if k == 0 else NAVY, 10,
                   1.8, shadow="shadow")
            p.text(x0 + k * 170 + 75, 205, key, 30, INK, 700, "middle", mono=True)
        if s.evicted:
            p.text(x0 + 2 * 170 + 40, 205, "%s evicted" % s.evicted, 16, RUST, 700, mono=True)
        furniture(p, tl, t, total, "An LRU cache with room for two",
                  "Every use moves a key to the most recent end. A full cache evicts from the other end.",
                  "the rules", rules, s.code, cap_y, rail_y, CODE_Y)

    CODE_Y = 300
    cap_y, rail_y, height = layout(CODE_Y, len(rules))
    return tl, draw, height


# -------------------------------------------------------- 14: the hash ring


def ring():
    code = source("src/problems/consistent_hash.rs", "pub fn get(&self, key", "}")
    nodes0 = {"a": 25, "b": 60, "d": 90}
    keys = [10, 30, 50, 75, 95]

    def owner(k, nodes):
        after = sorted((pos, n) for n, pos in nodes.items() if pos > k)
        return after[0][1] if after else min((pos, n) for n, pos in nodes.items())[1]

    O = lambda nodes: {str(k): owner(k, nodes) for k in keys}
    steps = [dict(chapter="ring", say="Nodes a, b, and d sit at 25, 60, and 90 on a ring of 0 to 99. Each key "
                  "belongs to the first node clockwise from it.", nodes={"a": 25, "b": 60, "d": 90}, own=O(nodes0),
                  code=-1.0),
             dict(say="get hashes the key, and partition_point finds the first point after it in the sorted ring.",
                  code=7.0),
             dict(say="Key 95 has no point after it, so the index wraps to 0, and 95 belongs to a at 25.", hot="95",
                  code=8.0)]
    nodes1 = dict(nodes0, c=45)
    steps.append(dict(chapter="add c", say="Node c joins at 45. It takes over the arc from 25 to 45, and nothing else.",
                      nodes=nodes1, hot="", c_a=1.0))
    steps.append(dict(say="Key 30 now finds c first, so it moves from b to c. The other four keys keep their node.",
                      own=O(nodes1), hot="30", kind="insight", hold=1.4))
    steps.append(dict(chapter="hash % N", say="With hash % N instead, going from 3 servers to 4 changes the server "
                      "of most keys.", kind="fail", hot="", modulo=1.0))
    steps.append(dict(say="Keys 10, 30, 75, and 95 move: 4 of 5. The ring moved 1 of 5.", kind="fail", hold=2.0))
    tl = play(steps, dict(nodes=nodes0, own=O(nodes0), hot="", c_a=0.0, modulo=0.0, code=-1.0))
    colors = {"a": (TEAL, TEAL_LT), "b": (NAVY, "#e6ecf6"), "c": (BRASS, BRASS_LT), "d": ("#7a5fb0", "#eae4f6")}

    def draw(p, s, total):
        t = s.t
        cx, cy, r = 250, 216, 112
        p.circle(cx, cy, r, "none", LINE, 6)
        def at(v, rr=r):
            a = math.radians(-90 + v * 3.6)
            return cx + rr * math.cos(a), cy + rr * math.sin(a)
        p.text(cx, cy - r - 14, "0", 11, FAINT, 600, "middle", mono=True)
        for name, pos in sorted(s.nodes.items()):
            col, fill = colors[name]
            x, y = at(pos)
            op = s.c_a if name == "c" else 1.0
            with p.group(opacity=op):
                p.circle(x, y, 15, fill, col, 2.2)
                p.text(x, y + 5, name, 14, col, 700, "middle", mono=True)
                lx, ly = at(pos, r + 34)
                p.text(lx, ly + 4, str(pos), 11, MUTED, 600, "middle", mono=True)
        for k in keys:
            x, y = at(k, r - 30)
            name = s.own[str(k)]
            col, fill = colors[name]
            hot = str(k) == s.hot
            p.circle(x, y, 13 if hot else 11, fill, RUST if hot else col, 2.4 if hot else 1.6)
            p.text(x, y + 4, str(k), 10, INK, 700, "middle", mono=True)
        # owner table
        tx = 470
        p.text(tx, 108, "key", 12, MUTED, 600)
        p.text(tx + 70, 108, "ring", 12, MUTED, 600)
        if s.modulo > 0.01:
            p.text(tx + 150, 108, "% 3", 12, MUTED, 600, opacity=s.modulo)
            p.text(tx + 210, 108, "% 4", 12, MUTED, 600, opacity=s.modulo)
        for i, k in enumerate(keys):
            y = 136 + i * 28
            p.text(tx, y, str(k), 14, INK, 700, mono=True)
            name = s.own[str(k)]
            p.text(tx + 70, y, name, 14, colors[name][0], 700, mono=True)
            if s.modulo > 0.01:
                moved = k % 3 != k % 4
                with p.group(opacity=s.modulo):
                    p.text(tx + 150, y, str(k % 3), 14, INK, 700, mono=True)
                    p.text(tx + 210, y, str(k % 4), 14, RUST if moved else INK, 700, mono=True)
        furniture(p, tl, t, total, "Consistent hashing: a key belongs to the next node clockwise",
                  "Adding a node moves only the keys in the arc it takes over.",
                  "get", code, s.code, cap_y, rail_y, CODE_Y)

    CODE_Y = 372
    cap_y, rail_y, height = layout(CODE_Y, len(code))
    return tl, draw, height


# ---------------------------------------------------------- 16: spin lock


def spin_lock():
    code = source("src/problems/spin_lock.rs", "pub fn lock(&self)", "}")
    cas = line_of(code, ".compare_exchange_weak")
    ret = line_of(code, "return SpinGuard")
    spin = line_of(code, "while self.locked.load")
    steps = [dict(chapter="A locks", say="locked is false. Thread A calls lock().", locked=0.0, a_state="calls lock",
                  b_state="", code=0.0),
             dict(say="compare_exchange_weak(false, true) finds false and stores true in one atomic step. A holds "
                  "the lock.", locked=1.0, a_state="holds the lock", code=float(ret), msg="A"),
             dict(chapter="B spins", say="Thread B calls lock(). Its compare_exchange_weak finds true, so it fails.",
                  b_state="exchange failed", code=float(cas), msg="B"),
             dict(say="B spins on a plain load until locked reads false. It stays on the CPU the whole time.",
                  b_state="spinning", spin=1.0, code=float(spin), hold=1.6),
             dict(chapter="handoff", say="A finishes and unlock stores false with Release ordering.", locked=0.0,
                  a_state="released", msg="", hold=0.4),
             dict(say="B's load sees false. Its next compare_exchange_weak succeeds, with Acquire ordering.",
                  locked=1.0, b_state="holds the lock", spin=0.0, msg="B", code=float(ret)),
             dict(say="The Release store and the Acquire exchange pair up, so B sees every write A made while it "
                  "held the lock.", kind="insight", code=-1.0, hold=1.8),
             dict(chapter="never released", say="Now A leaks its guard with std::mem::forget. The guard's Drop "
                  "never runs, so unlock never runs.", kind="fail", locked=1.0, a_state="guard forgotten",
                  b_state="calls lock", msg="A", code=0.0),
             dict(say="B's exchange fails, and B spins on the load. locked stays true.", kind="fail",
                  b_state="spinning", spin=1.0, cpu=1.0, code=float(spin), hold=1.2),
             dict(say="Nothing will ever store false. B spins forever, and keeps one core at 100%.",
                  kind="fail", hold=2.2)]
    tl = play(steps, dict(locked=0.0, a_state="", b_state="", code=-1.0, msg="", spin=0.0, cpu=0.0))

    def draw(p, s, total):
        t = s.t
        robot(p, 130, 240, TEAL, 1.0, 1.0, "thread A", s.a_state or " ")
        robot(p, 690, 240, "#3b7dd8", 1.0, 1.0, "thread B", s.b_state or " ")
        if s.spin > 0.01:
            ang = (t * 360) % 360
            with p.group(opacity=s.spin, rotate=ang, cx=690, cy=110):
                p.path("M 690 92 A 18 18 0 1 1 672 110", "none", RUST, 3)
            p.text(690, 82, "spinning", 11, RUST, 700, "middle", opacity=s.spin)
        if s.cpu > 0.01:
            chip(p, 560, 110, "B: CPU 100%, forever", RUST, RUST_LT, 12, opacity=min(1.0, s.cpu))
        lockv = s.locked > 0.5
        p.rect(330, 150, 160, 90, RUST_LT if lockv else TEAL_LT, RUST if lockv else TEAL, 12, 2)
        p.text(410, 178, "locked: AtomicBool", 11.5, MUTED, 600, "middle")
        p.text(410, 216, "true" if lockv else "false", 26, RUST if lockv else TEAL, 700, "middle", mono=True)
        if s.msg:
            p.text(410, 268, "held by %s" % s.msg, 13, INK, 700, "middle")
        furniture(p, tl, t, total, "A spin lock: one atomic word decides who is inside",
                  "compare_exchange changes false to true only if nobody got there first.",
                  "lock", code, s.code, cap_y, rail_y, CODE_Y)

    CODE_Y = 330
    cap_y, rail_y, height = layout(CODE_Y, len(code))
    return tl, draw, height


# ----------------------------------------------------------- 16: deadlock


def deadlock():
    code = ["thread A:  let _g1 = m1.lock();  let _g2 = m2.lock();",
            "thread B:  let _g2 = m2.lock();  let _g1 = m1.lock();",
            "",
            "fixed order, both threads:  m1, then m2"]
    steps = [dict(chapter="opposite order", say="Thread A takes m1, then m2. Thread B takes m2, then m1.", code=-1.0),
             dict(say="A locks m1.", m1="A", code=0.0),
             dict(say="B locks m2. Each lock is free when it is taken, so nothing has gone wrong yet.", m2="B",
                  code=1.0),
             dict(say="A asks for m2, which B holds, so A waits while it still holds m1.", wa="m2", code=0.0),
             dict(say="B asks for m1, which A holds. Each thread waits for the other, and neither can go on.",
                  wb="m1", code=1.0, kind="fail"),
             dict(say="The wait forms a cycle: A waits for B, and B waits for A. Neither lock is buggy; the order "
                  "is.", kind="fail", cycle=1.0, hold=1.6),
             dict(chapter="fixed order", say="Fix the order: both threads take m1 first.", m1="A", m2="", wa="",
                  wb="m1", cycle=0.0, code=3.0),
             dict(say="B waits for m1 while holding nothing, so A can take m2 and finish.", m2="A"),
             dict(say="A releases both locks, and B takes m1 and then m2. No cycle can form.", m1="B", m2="B", wa="",
                  wb="", kind="insight", hold=1.6)]
    tl = play(steps, dict(m1="", m2="", wa="", wb="", cycle=0.0, code=-1.0))

    def draw(p, s, total):
        t = s.t
        robot(p, 130, 250, TEAL, 0.3 if s.wa else 1.0, 1.0, "thread A", ("waits for %s" % s.wa) if s.wa else " ")
        robot(p, 690, 250, "#3b7dd8", 0.3 if s.wb else 1.0, 1.0, "thread B", ("waits for %s" % s.wb) if s.wb else " ")
        locks = {"m1": (410, 120), "m2": (410, 236)}
        for name, (x, y) in locks.items():
            holder = s[name]
            p.rect(x - 70, y - 34, 140, 68, BRASS_LT if holder else PAPER, BRASS if holder else NAVY, 12, 2)
            p.text(x, y - 6, name, 18, INK, 700, "middle", mono=True)
            p.text(x, y + 18, ("held by %s" % holder) if holder else "free", 12, BRASS if holder else MUTED, 700,
                   "middle")
            if holder:
                hx = 200 if holder == "A" else 620
                p.line(hx, 190, x + (-70 if holder == "A" else 70), y, BRASS, 2.4)
        for who, want in (("A", s.wa), ("B", s.wb)):
            if want:
                x, y = locks[want]
                hx = 200 if who == "A" else 620
                p.line(hx, 210, x + (-70 if who == "A" else 70), y + 10, RUST, 2.2, dash="6 4")
        if s.cycle > 0.01:
            p.text(410, 306, "A → m2 → B → m1 → A", 15, RUST, 700, "middle", mono=True,
                   opacity=s.cycle)
        furniture(p, tl, t, total, "Deadlock: two locks taken in opposite orders",
                  "Each thread holds one lock and waits for the other.", "the two threads", code, s.code,
                  cap_y, rail_y, CODE_Y, tint=RUST if s.cycle > 0.5 else TEAL)

    CODE_Y = 340
    cap_y, rail_y, height = layout(CODE_Y, len(code))
    return tl, draw, height


# -------------------------------------------------------- 17: bounded buffer


def bounded_buffer():
    push_code = source("src/bin/bounded_buffer.rs", "fn push(&self", "}")
    pop_code = source("src/bin/bounded_buffer.rs", "fn pop(&self", "}")
    code = push_code + pop_code
    wait_full = line_of(code, "guard = self.not_full.wait(guard)")
    push = line_of(code, "guard.push_back(item)")
    pop = line_of(code, "guard.pop_front()")
    notify_full = line_of(code, "self.not_full.notify_one()")
    steps = [dict(chapter="fill", say="A buffer with three slots, a producer, and a consumer.", code=-1.0)]
    buf = []
    for v in (1, 2, 3):
        buf.append(v)
        steps.append(dict(say="The producer pushes %d." % v, buf=list(buf), code=float(push), dur=0.5))
    steps += [dict(chapter="full", say="The buffer is full. push(4) finds len == capacity, so it waits on not_full "
                   "and sleeps.", p_wait=1.0, want="4", code=float(wait_full)),
              dict(say="The consumer pops 1 and calls not_full.notify_one().", buf=[2, 3], c_item="1",
                   code=float(notify_full)),
              dict(say="The producer wakes, checks the while condition again, finds room, and pushes 4.", p_wait=0.0,
                   want="", buf=[2, 3, 4], code=float(push)),
              dict(say="A fast producer cannot get ahead of a slow consumer by more than three items. That limit "
                   "is backpressure.", kind="insight", code=-1.0, hold=1.4)]
    for v in (2, 3, 4):
        buf_ = [x for x in [2, 3, 4] if x > v]
        steps.append(dict(chapter="drain" if v == 2 else None, say="The consumer pops %d." % v, buf=buf_,
                          c_item=str(v), code=float(pop), dur=0.5, hold=0.2))
    while_line = line_of(code, "while guard.len()")
    steps += [dict(chapter="if, not while", say="Full again: 5, 6, 7. The producer waits to push 8.",
                   buf=[5, 6, 7], p_wait=1.0, want="8", c_item="", code=float(wait_full)),
              dict(say="The consumer pops 5 and notifies. Before the producer wakes, a second producer pushes "
                   "9 into the free slot.", buf=[6, 7, 9], c_item="5", other=1.0, code=-1.0, hold=0.8),
              dict(say="With while, the woken producer checks len again, finds the buffer full, and sleeps.",
                   kind="insight", other=0.0, code=float(while_line), hold=1.0),
              dict(say="With if in place of while, it does not check again. It pushes 8: four items in three "
                   "slots.", kind="fail", strike=float(while_line), p_wait=0.0, want="", buf=[6, 7, 9, 8],
                   code=float(push), hold=1.0),
              dict(say="The capacity no longer holds, and a spurious wakeup can do the same with no second "
                   "producer at all.", kind="fail", hold=2.0)]
    steps = [{a: b for a, b in st.items() if b is not None} for st in steps]
    tl = play(steps, dict(buf=[], p_wait=0.0, want="", c_item="", code=-1.0, strike=-1.0,
                          other=0.0))

    def draw(p, s, total):
        t = s.t
        robot(p, 110, 250, "#3b7dd8", 1 - s.p_wait * 0.8, 1 - s.p_wait, "producer",
              ("waiting to push %s" % s.want) if s.want else " ")
        zzz(p, 150, 140, t, s.p_wait)
        robot(p, 710, 250, TEAL, 1.0, 1.0, "consumer", ("popped %s" % s.c_item) if s.c_item else " ")
        x0 = 280
        for k in range(3):
            p.rect(x0 + k * 90, 150, 80, 80, "#f6f8fa", LINE, 10, 1.4, dash="5 5")
        for k, v in enumerate(s.buf):
            over = k >= 3
            p.rect(x0 + k * 90 + 6, 156, 68, 68, RUST_LT if over else BRASS_LT, RUST if over else BRASS,
                   9, 1.8, shadow="shadow")
            p.text(x0 + k * 90 + 40, 199, str(v), 24, INK, 700, "middle", mono=True)
            if over:
                p.text(x0 + k * 90 + 40, 246, "no slot", 11, RUST, 700, "middle")
        if s.other > 0.01:
            pill(p, 420, 112, "producer 2: push(9)", NAVY, "#e6ecf6", 11, opacity=min(1.0, s.other),
                 shadow=None)
        p.text(x0, 256, "front: pop_front", 11, MUTED, 600)
        p.text(x0 + 260, 256, "back: push_back", 11, MUTED, 600, "end")
        full = len(s.buf) >= 3
        p.text(x0 + 130, 136, "len %d of 3%s" % (len(s.buf), ", full" if full else ""), 13,
               RUST if full else INK, 700, "middle", mono=True)
        furniture(p, tl, t, total, "A bounded buffer: the producer waits when it is full",
                  "Two condition variables put each side to sleep until the other side makes room or work.",
                  "push and pop", code, s.code, cap_y, rail_y, CODE_Y, size=10.6, lead=15.0,
                  strike=s.strike)

    CODE_Y = 318
    cap_y, rail_y, height = layout(CODE_Y, len(code), 15.0)
    return tl, draw, height


# -------------------------------------------------------- 19: token bucket


def token_bucket():
    code = source("src/problems/rate_limiter.rs", "pub fn try_acquire", "}")
    refill = line_of(code, "s.tokens = (s.tokens + new_tokens).min(self.capacity)")
    take = line_of(code, "s.tokens -= 1.0")
    deny = line_of(code, "false")
    steps = [dict(chapter="spend", say="The bucket holds at most 5 tokens and refills 1 per second. It starts full.",
                  tokens=5.0, clock=0.0, code=-1.0)]
    for k in range(5):
        steps.append(dict(say="try_acquire at t = 0: refill adds nothing, and a token is taken. %d left." % (4 - k),
                          tokens=float(4 - k), result="true", code=float(take), dur=0.4, hold=0.1))
    steps += [dict(chapter="refuse", say="The sixth call at t = 0 finds 0 tokens, so it returns false.", result="false",
                   code=float(deny)),
              dict(chapter="refill", say="One second passes. Nothing runs during it: no timer and no thread.",
                   clock=1.0, result="", dur=1.6),
              dict(say="The next call computes elapsed = 1 s, so refill adds 1 token. The count catches up when it "
                   "is read.", tokens=1.0, code=float(refill)),
              dict(say="That token is taken, and the call returns true.", tokens=0.0, result="true", code=float(take)),
              dict(say="A burst of up to 5 calls passes at once; after that, calls pass at 1 per second.",
                   kind="insight", code=-1.0, result="", hold=1.6),
              dict(chapter="no cap", say="Now leave out .min(self.capacity), and let the limiter sit idle for an "
                   "hour.", kind="fail", strike=float(refill), clock=3600.0, result="", code=-1.0, dur=1.6),
              dict(say="The next call computes elapsed = 3,600 s and adds 3,600 tokens. Nothing stops at 5.",
                   kind="fail", tokens=3600.0, code=float(refill), dur=1.4),
              dict(say="The next 3,600 calls all pass at once: a burst 720 times the capacity. The limit is "
                   "gone.", kind="fail", result="true", hold=2.2)]
    tl = play(steps, dict(tokens=5.0, clock=0.0, result="", code=-1.0, strike=-1.0))

    def draw(p, s, total):
        t = s.t
        bx, by = 300, 110
        p.path("M %d %d L %d %d L %d %d L %d %d" % (bx, by, bx + 20, by + 180, bx + 200, by + 180, bx + 220, by),
               "none", NAVY, 3)
        n = s.tokens
        for k in range(5):
            full = clamp_f(n - k)
            if full > 0.01:
                y = by + 160 - k * 34
                with p.group(opacity=full):
                    p.circle(bx + 110, y, 15, BRASS, "#9a7426", 2)
                    p.text(bx + 110, y + 5, "T", 12, PAPER, 700, "middle")
        if n > 5.5:
            for k in range(4):
                p.circle(bx + 70 + k * 27, by - 12 - (k % 2) * 16, 13, RUST, "#9a7426", 2)
            p.text(bx + 110, by + 234, "+%s over capacity" % format(int(n - 5), ","), 12.5, RUST, 700,
                   "middle", mono=True)
        p.text(bx + 110, by + 210, "tokens = %s" % format(int(round(n)), ","), 16,
               RUST if n > 5.5 else INK, 700, "middle", mono=True)
        p.text(620, 150, "clock: t = %s s" % format(int(round(s.clock)), ","), 15, INK, 700, mono=True)
        if s.result:
            ok = s.result == "true"
            pill(p, 680, 210, "try_acquire -> %s" % s.result, TEAL if ok else RUST, TEAL_LT if ok else RUST_LT, 13,
                 shadow=None)
        furniture(p, tl, t, total, "A token bucket refills from the clock",
                  "Each call adds the tokens the elapsed time has earned, then tries to take one.",
                  "try_acquire", code, s.code, cap_y, rail_y, CODE_Y, strike=s.strike)

    CODE_Y = 360
    cap_y, rail_y, height = layout(CODE_Y, len(code))
    return tl, draw, height


def clamp_f(v):
    return 0.0 if v < 0 else 1.0 if v > 1 else v


def build(name, fn, extra=()):
    def run(only=None):
        tl, draw, height = fn()
        return render(name, tl, draw, height, only=only, extra_colors=extra)
    return run


BUILDERS = {
    "ring": build("ch14-ring.gif", ring, (NAVY, "#e6ecf6", "#7a5fb0", "#eae4f6")),
    "spin-lock": build("ch16-spin-lock.gif", spin_lock, ("#3b7dd8",)),
    "deadlock": build("ch16-deadlock.gif", deadlock, ("#3b7dd8", NAVY)),
    "bounded-buffer": build("ch17-bounded-buffer.gif", bounded_buffer, ("#3b7dd8",)),
    "token-bucket": build("ch19-token-bucket.gif", token_bucket, (NAVY, "#9a7426")),
}
