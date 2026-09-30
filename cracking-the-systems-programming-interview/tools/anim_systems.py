"""Animations for the concurrency and network chapters.

These picture the runtime behaviour the chapters describe: an atomic exchange, a
lock order that deadlocks, a bounded buffer that blocks a producer, and HTTP
body framing. The sockets and async chapters are drawn frame by frame instead,
in `anim_sockets` and `anim_async`.

Each frame names the state of every actor and shows the one thing that changed,
so a reader can follow a race between two threads the way they would follow a
race between two pointers.
"""

from animlib import *  # noqa: F401,F403
from animlib import Frame, frames, publish


def lane(f, y, name, state, color, detail="", state_fill=None, state_stroke=None):
    """One actor on one line: who it is, what it is doing, and why."""
    f.text(PAD, y + 5, name, T_STEP - 2, INK, mono=True, bold=True)
    f.cell(148, y - 16, 250, 34, state, state_fill or PALE, state_stroke or BORDER,
           size=T_MARK, mono=False, color=color)
    if detail:
        f.text(416, y + 5, detail, T_MARK, MUTED)


# --------------------------------------------------------- Spin lock (16.4)

def spin_lock():
    """One atomic word decides which thread is inside."""
    steps = [
        (False, None, "idle", "idle",
         "The lock is one AtomicBool holding false, and nothing owns it."),
        (True, "A", "working", "tries",
         "Thread A runs compare_exchange(false, true). It succeeds, so A enters the critical section."),
        (True, "A", "working", "spins",
         "Thread B runs the same exchange and fails, because the word is already true. B loops and tries again."),
        (True, "A", "working", "spins",
         "B is still spinning and A is still inside, so the word stays true."),
        (False, None, "done", "spins",
         "A finishes and stores false. The release ordering means B's next acquire sees A's writes."),
        (True, "B", "tries", "working",
         "B's exchange succeeds. Ownership passed from A to B without the kernel being involved."),
        (False, None, "done", "done",
         "B stores false, and the lock is idle again."),
    ]

    def make(step, height=None, rows=0, index=0):
        held, owner, a_state, b_state, line = step
        last = step is steps[-1]
        f = Frame(
            "A spin lock: one atomic word, two threads",
            sub="compare_exchange(false, true) takes the lock. A plain store releases it.",
            diagram=252,
            legend=[("inside", TEAL), ("spinning", BORDER), ("trying", BRASS)],
            step=line,
            note="A spin lock is worth it only when the critical section is shorter than a thread wake-up.",
            pairs=[("lock", "held by %s" % owner if owner else "free", RUST if owner else TEAL),
                   ("owner", owner or "-", INK)],
            insight=("No kernel call appears in this lock: a thread that fails the exchange "
                     "tries again.") if last else None,
            fails=("A spinning thread burns a core for as long as it waits. The exchange fails "
                   "until the holder releases, so the spin pays off only over a short section."
                   ) if index == 2 else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        f.panel(216, t + 4, 304, 84, "AtomicBool")
        f.cell(252, t + 36, 232, 40, "true" if held else "false",
               PINK if held else GREEN, RUST if held else TEAL, size=T_CELL,
               color=WHITE if held else INK)

        f.panel(548, t + 4, 246, 156, "critical")
        if owner:
            f.cell(566, t + 46, 210, 44, "thread %s is inside" % owner, GREEN, TEAL,
                   size=T_MARK, mono=False)
        else:
            f.cell(566, t + 46, 210, 44, "empty", GREY, BORDER, size=T_MARK, mono=False,
                   color=MUTED, dash=True)

        for y, state, name in ((t + 130, a_state, "A"), (t + 190, b_state, "B")):
            fill, stroke, color = {
                "working": (GREEN, TEAL, INK),
                "spins": (GREY, BORDER, MUTED),
                "tries": (CREAM, BRASS, INK),
                "idle": (GREY, BORDER, MUTED),
                "done": (GREY, BORDER, MUTED),
            }[state]
            lane(f, y, "Thread %s" % name,
                 {"working": "inside the critical section",
                  "spins": "spinning on the exchange",
                  "tries": "trying the exchange",
                  "done": "finished"}.get(state, "not started"),
                 color, state_fill=fill, state_stroke=stroke)
        if owner:
            inside_y = t + 130 if owner == "A" else t + 190
            f.arrow(548, inside_y, 530, inside_y, TEAL, 2.0)
        return f

    publish("ch16-spin-lock.gif", frames(make, steps),
            holds(len(steps), longer=(2, len(steps) - 1)))


# ------------------------------------------------------------- Deadlock (16.7)

def deadlock():
    """Two threads each hold one lock and want the other."""
    steps = [
        ("free", "free", False, False, "Two threads, two mutexes. Both mutexes start free."),
        ("A", "free", False, False, "Thread A locks m1 and keeps it."),
        ("A", "B", False, False, "Thread B locks m2 and keeps it."),
        ("A", "B", True, False,
         "A asks for m2. B holds m2, so A blocks and waits, still holding m1."),
        ("A", "B", True, True,
         "B asks for m1. A holds m1, so B blocks too. Each waits for the other, and neither can run."),
    ]

    def make(step, height=None, rows=0, index=0):
        m1, m2, a_waits, b_waits, line = step
        last = step is steps[-1]
        f = Frame(
            "Deadlock: two threads each hold one lock and want the other",
            sub="A waits-for cycle is the signature. Breaking the order breaks the cycle.",
            diagram=280,
            legend=[("held", TEAL), ("wanted", RUST), ("free", BORDER)],
            step=line,
            note="Both locks are healthy. It is the order of the two requests that jams the pair.",
            pairs=[("m1", "held by A" if m1 == "A" else "free", TEAL if m1 == "A" else MUTED),
                   ("m2", "held by B" if m2 == "B" else "free", TEAL if m2 == "B" else MUTED),
                   ("waiting", "both" if a_waits and b_waits else ("A" if a_waits else "-"), RUST)],
            insight=("A holds m1 and waits for m2 without letting m1 go. A thread that blocks while "
                     "holding a lock is what gives the cycle its first edge.") if index == 3 else None,
            fails=("Each thread holds one lock and waits for the other, so neither can proceed. No "
                   "lock failed, and the two requests were simply made in different orders."
                   ) if last else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        f.panel(PAD, t + 4, 350, 168, "Thread A")
        f.panel(444, t + 4, 350, 168, "Thread B")
        f.cell(PAD + 24, t + 54, 140, 44,
               "holds m1" if m1 == "A" else ("wants m1" if a_waits else "m1 free"),
               GREEN if m1 == "A" else (PINK if a_waits else GREY),
               TEAL if m1 == "A" else (RUST if a_waits else BORDER),
               size=T_MARK + 1, mono=False, color=WHITE if m1 == "A" or a_waits else INK)
        f.cell(PAD + 180, t + 54, 140, 44, "wants m2" if a_waits else "m2 free",
               PINK if a_waits else GREY, RUST if a_waits else BORDER,
               size=T_MARK + 1, mono=False, color=WHITE if a_waits else MUTED)
        f.cell(444 + 24, t + 54, 140, 44,
               "holds m2" if m2 == "B" else "m2 free",
               GREEN if m2 == "B" else GREY, TEAL if m2 == "B" else BORDER,
               size=T_MARK + 1, mono=False, color=WHITE if m2 == "B" else INK)
        f.cell(444 + 180, t + 54, 140, 44, "wants m1" if b_waits else "m1 free",
               PINK if b_waits else GREY, RUST if b_waits else BORDER,
               size=T_MARK + 1, mono=False, color=WHITE if b_waits else MUTED)

        if a_waits:
            f.arrow(PAD + 250, t + 118, 444 + 94, t + 118, RUST, 2.2, head=9)
            f.text((PAD + 250 + 444 + 94) / 2, t + 106, "wants m2", T_MARK, RUST,
                   anchor="middle", bold=True)
        if b_waits:
            f.arrow(444 + 94, t + 154, PAD + 250, t + 154, RUST, 2.2, head=9)
            f.text((PAD + 250 + 444 + 94) / 2, t + 186, "wants m1", T_MARK, RUST,
                   anchor="middle", bold=True)
        return f

    publish("ch16-deadlock.gif", frames(make, steps),
            holds(len(steps), longer=(3, len(steps) - 1)))


# --------------------------------------------------- Bounded buffer (17.3)

def bounded_buffer():
    """A fixed number of slots, and a producer that has to wait."""
    capacity = 3
    steps, buf = [], []
    steps.append((list(buf), "-", "push", "running", "running",
                  "The buffer holds %d items. The producer pushes and the consumer pops, and each waits when it cannot move." % capacity))
    for item in (1, 2, 3):
        buf.append(item)
        steps.append((list(buf), item, "push", "running", "running",
                      "The producer pushes %d. %s" % (item, "That fills the buffer." if len(buf) == capacity else "There is room left.")))
    steps.append((list(buf), 4, "push", "blocked", "running",
                  "The producer wants to push 4, but the buffer is full, so it waits on the not-full condition."))
    steps.append((list(buf), 1, "pop", "waiting", "running",
                  "The consumer pops 1 and signals not-full. The producer wakes, but must take the lock before it can run."))
    buf.pop(0)
    buf.append(4)
    steps.append((list(buf), 4, "push", "running", "running",
                  "The producer pushes 4, and the buffer is full again."))
    for item in (2, 3, 4):
        buf.pop(0)
        steps.append((list(buf), item, "pop", "running", "running",
                      "The consumer pops %d. %s" % (item, "The buffer is empty, so the consumer waits next." if not buf else "The producer can push again.")))

    sw, sh = 118, 66

    def make(step, height=None, rows=0, index=0):
        values, item, kind, producer, consumer, line = step
        full = len(values) == capacity
        blocked = producer == "blocked"
        f = Frame(
            "A bounded buffer: backpressure from a fixed number of slots",
            sub="The producer waits when the buffer is full. The consumer waits when it is empty.",
            diagram=260,
            legend=[("holding an item", TEAL), ("empty slot", BORDER), ("blocked", RUST)],
            step=line,
            note="A condition variable is what turns a full buffer into a sleeping thread rather than a spin.",
            pairs=[("event", kind, RUST), ("item", item, INK), ("slots used", "%d of %d" % (len(values), capacity), TEAL)],
            insight=("The consumer pops an item and signals not-full, which wakes the producer. "
                     "A sleeping waiter uses no CPU.") if index == 5 else None,
            fails=("A full buffer blocks the producer instead of dropping an item or growing, so "
                   "the wait itself is the backpressure.") if blocked else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        f.text(PAD, t + 20, "slots, oldest first", T_MARK, MUTED)
        sx = (W - (capacity * sw + (capacity - 1) * 14)) / 2.0
        for i in range(capacity):
            x = sx + i * (sw + 14)
            if i < len(values):
                f.cell(x, t + 34, sw, sh, values[i], GREEN, TEAL, size=T_CELL + 2)
            else:
                f.cell(x, t + 34, sw, sh, "empty", GREY, BORDER, size=T_MARK, mono=False,
                       dash=True, color=MUTED)
            if i == 0 and values:
                f.text(x + sw / 2, t + 122, "head", T_MARK, MUTED, anchor="middle")
                f.arrow(x + sw / 2, t + 114, x + sw / 2, t + 104, MUTED, 1.4)
        if full:
            f.zone(sx - 12, t + 22, capacity * sw + (capacity - 1) * 14 + 24, sh + 24,
                   color=RUST, dash=True, opacity=0.07)
        f.text(W - PAD, t + 20, "full" if full else "room for %d" % (capacity - len(values)),
               T_MARK, RUST if full else MUTED, anchor="end")

        lane(f, t + 168, "producer",
             "blocked on not-full" if blocked else ("ready" if item == "-" else "pushing %s" % item),
             RUST if blocked else TEAL,
             "the buffer is full" if blocked else "the lock is free",
             state_fill=PINK if blocked else GREEN, state_stroke=RUST if blocked else TEAL)
        lane(f, t + 216, "consumer", "popping %s" % item if kind == "pop" else "ready",
             TEAL, "signals not-full" if kind == "pop" else "waiting for an item",
             state_fill=GREEN, state_stroke=TEAL)
        return f

    publish("ch17-bounded-buffer.gif", frames(make, steps),
            holds(len(steps), longer=(4, 5)))


# ---------------------------------------------------- Token bucket (19.1)

def token_bucket():
    """Refill from the clock, then spend."""
    capacity = 5
    steps = [
        (5, "start", "The bucket holds 5 tokens, which is its capacity, so a burst can spend all of them at once."),
        (3, "spend", "Two calls take two tokens. Three are left."),
        (1, "spend", "Two more calls take two tokens. One is left."),
        (0, "spend", "The last token goes, and the bucket is empty."),
        (0, "refuse", "Another call finds no token, so it is refused. The caller waits, or gets a 429."),
        (1, "refill", "One second passes. The bucket gains 1 token from the elapsed time, with no timer thread."),
        (0, "spend", "A call takes that token. The next call must wait for the clock again."),
    ]
    tw, th = 84, 66

    def make(step, height=None, rows=0, index=0):
        tokens, kind, line = step
        previous = steps[index - 1][0] if index else tokens
        f = Frame(
            "A token bucket: refill from elapsed time, then spend",
            sub="Capacity %d. A call adds the tokens earned since the last call before it checks." % capacity,
            diagram=260,
            legend=[("a token", TEAL), ("spent or missing", BORDER)],
            step=line,
            note="The bucket never fills past its capacity, however long the caller waits.",
            pairs=[("tokens", tokens, TEAL if tokens else RUST),
                   ("event", {"start": "full", "spend": "one call served", "refuse": "refused (429)",
                              "refill": "clock advanced"}[kind], INK),
                   ("capacity", capacity, MUTED)],
            insight=("The refill is computed from the clock, so the bucket needs no timer."
                     ) if kind == "refill" else None,
            fails=("A call that finds no token is refused rather than queued. The bucket caps the "
                   "rate; it never lends tokens.") if kind == "refuse" else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        x0 = (W - (capacity * tw + (capacity - 1) * 12)) / 2.0
        for i in range(capacity):
            x = x0 + i * (tw + 12)
            full = i < tokens
            if kind == "refill" and i == tokens - 1:
                f.glow(x + tw / 2, t + 94, 62, BRASS, 0.5)
            f.cell(x, t + 62, tw, th, "1" if full else "", GREEN if full else GREY,
                   TEAL if full else BORDER, size=T_CELL + 2, dash=not full)
            if full and i >= previous and kind == "refill":
                f.text(x + tw / 2, t + 46, "new", T_MARK, BRASS, anchor="middle", bold=True)
        f.text(x0, t + 26, "tokens in the bucket", T_MARK, MUTED)
        if kind == "refuse":
            f.zone(x0 - 12, t + 50, capacity * tw + (capacity - 1) * 12 + 24, th + 24,
                   color=RUST, dash=True, opacity=0.07)
            chip(f, W - PAD - 70, t + 94, "refused", RUST)
            f.arrow(W - PAD - 110, t + 94, W - PAD - 138, t + 94, RUST, 1.8)
        f.text(PAD, t + 172, "elapsed time is the only input: tokens = min(capacity, tokens + elapsed * rate)",
               T_NOTE, MUTED, mono=True)
        return f

    publish("ch19-token-bucket.gif", frames(make, steps),
            holds(len(steps), longer=(4, 5)))


# ---------------------------------------------------- HTTP framing (21.1)

def http_framing():
    """How the headers decide where the body ends."""
    steps = [
        ("cl", "POST /v1/jobs HTTP/1.1\r\nHost: x\r\nContent-Length: 5\r\n\r\nhello",
         "body 5 bytes", TEAL,
         "The head ends at the first blank line. Content-Length says the body is exactly 5 bytes: hello."),
        ("cl", "POST /v1/jobs HTTP/1.1\r\nHost: x\r\nContent-Length: 5\r\n\r\nhelloGET /x HTTP/1.1...",
         "body 5 bytes", TEAL,
         "The parser takes 5 body bytes, so the next request starts exactly there and nothing is left over."),
        ("chunked", "POST /v1/jobs HTTP/1.1\r\nHost: x\r\nTransfer-Encoding: chunked\r\n\r\n5\r\nhello\r\n0\r\n\r\n",
         "size CRLF data CRLF", TEAL,
         "There is no Content-Length. Each chunk is a hex size, CRLF, the data, CRLF, and a size of 0 ends the body."),
        ("both", "POST /v1/jobs HTTP/1.1\r\nHost: x\r\nContent-Length: 5\r\nTransfer-Encoding: chunked\r\n\r\nhello",
         "two rules, one message", RUST,
         "Both headers are present. A proxy might frame by Content-Length while the back end frames by chunked."),
        ("reject", "400 Bad Request\r\nConnection: close",
         "refused", RUST,
         "The parser refuses the request and closes the connection, so the two readings can never disagree."),
    ]

    def make(step, height=None, rows=0, index=0):
        kind, text, verdict, vcolor, line = step
        last = step is steps[-1]
        danger = kind in ("both",)
        f = Frame(
            "HTTP/1.1 body framing: the headers decide where the message ends",
            sub="When two rules disagree, one request can be read as two. The parser refuses that.",
            diagram=250,
            legend=[("one reading", TEAL), ("two readings", RUST)],
            step=line,
            note="The boundary of a message is a decision the headers make, not something the bytes carry.",
            pairs=[("framing", {"cl": "Content-Length", "chunked": "chunked", "both": "ambiguous",
                                "reject": "rejected"}[kind], RUST if danger or kind == "reject" else TEAL)],
            insight=("The parser takes exactly the five body bytes, so the next request starts "
                     "there and nothing is left over.") if index == 1 else None,
            fails=("Both a length and a chunked rule are present, so two readers can disagree "
                   "about where the body ends. The parser rejects the request.") if last else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        lines = len(text.split("\r\n"))
        y = t + 30 + lines * 24 + 14
        f.rect(PAD - 4, t + 6, CONTENT + 8, lines * 24 + 22,
               PINK if kind == "reject" else PALE,
               RUST if kind == "reject" else BORDER, 6, width=1.4)
        for i, chunk in enumerate(text.split("\r\n")):
            f.text(PAD, t + 30 + i * 24, chunk, T_NOTE, INK, mono=True)
        f.cell(PAD, y, 340, 40, verdict, PINK if danger or kind == "reject" else GREEN,
               RUST if danger or kind == "reject" else TEAL, size=T_MARK + 1, mono=False,
               color=RUST if danger or kind == "reject" else INK)
        if danger:
            f.text(PAD + 360, y + 26, "a proxy and a server can disagree here", T_MARK, RUST)
        return f

    publish("ch21-http-framing.gif", frames(make, steps),
            holds(len(steps), longer=(1, len(steps) - 1)))


BUILDERS = {
    "spin-lock": spin_lock,
    "deadlock": deadlock,
    "bounded-buffer": bounded_buffer,
    "token-bucket": token_bucket,
    "http-framing": http_framing,
}
