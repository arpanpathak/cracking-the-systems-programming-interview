"""Figures for chapter 19: rate limits, retries, and idempotency."""
import random
from svgkit import *
OUT = "src/figures/"

# 1. token bucket over time
f = Figure(760, 280)
f.text(20, 22, "A token bucket with capacity 5 and a refill of 1 token per second (the test it_works)", 12, bold=True)
ox, oy, W, H = 60, 220, 600, 160
f.line(ox, oy, ox + W, oy); f.line(ox, oy, ox, oy - H)
for v in range(6):
    y = oy - v * H / 5
    f.text(ox - 8, y + 4, str(v), 10, MUTED, anchor="end")
    if v:
        f.line(ox, y, ox + W, y, "#e3e8ee", 0.8)
f.text(20, 44, "tokens", 10, MUTED)
for t, label in [(0, "0 s"), (300, "1 s")]:
    f.text(ox + t, oy + 16, label, 10, MUTED, anchor="middle")
pts = [(0, 5)]
for k in range(5):
    x = 10 + k * 14
    pts += [(x, 5 - k), (x, 4 - k)]
pts += [(90, 0), (300, 0.93), (310, 1.0), (310, 0.0), (330, 0.07)]
path = " ".join(f"{ox + x:.1f},{oy - v * H / 5:.1f}" for x, v in pts)
f.parts.append(f'<polyline points="{path}" fill="none" stroke="{TEAL}" stroke-width="2.2"/>')
notes = [(80, "five try_acquire calls take all 5"), (95, "the 6th finds 0 tokens: false"),
         (330, "after 1 s, 1 token has refilled: true"), (345, "then 0 again: false")]
for i, (x, t) in enumerate(notes):
    f.text(ox + x + 14, 70 + i * 20, t, 10, RUST if "false" in t else TEAL)
f.text(20, 262, "Each call first adds elapsed seconds x rate, capped at the capacity, then takes one token if at least one is there.", 10, MUTED)
f.save(OUT + "token-bucket.svg")

# 2. atomic interleaving
f = Figure(760, 250)
f.text(20, 22, "The atomic version: a check and a take that are two separate steps", 12, bold=True)
f.text(150, 50, "thread A", 11, TEAL, anchor="middle", bold=True); f.text(430, 50, "thread B", 11, RUST, anchor="middle", bold=True)
f.text(650, 50, "tokens", 11, MUTED, anchor="middle")
rows = [("load: 1 > 0", "", "1"), ("", "load: 1 > 0", "1"), ("fetch_sub: old 1 > 0: true", "", "0"),
        ("", "fetch_sub: old 0: false", "-1")]
for i, (a, b, t) in enumerate(rows):
    y = 62 + i * 32
    if a:
        f.cell(40, y, 220, 26, a, GREEN, size=10)
    if b:
        f.cell(320, y, 220, 26, b, PINK, size=10)
    f.cell(610, y, 80, 26, t, PALE if t != "-1" else PINK, size=10)
f.text(20, 208, "B was refused, which is correct, but its fetch_sub still took a token: the count is now -1.", 10)
f.text(20, 226, "The next refill starts from -1, so fewer requests pass than the rate allows. Measured: 17 to 19 of 20.", 10, MUTED)
f.save(OUT + "atomic-bucket.svg")

# 3. backoff delays
f = Figure(760, 260)
f.text(20, 22, "Exponential backoff: base 100 ms, doubling, capped at 1,000 ms", 12, bold=True)
ox, oy = 90, 220
delays = [100, 200, 400, 800, 1000, 1000]
for i, d in enumerate(delays):
    y = 44 + i * 28
    f.text(ox - 10, y + 16, f"retry {i}", 10, MUTED, anchor="end")
    w = d * 0.5
    f.rect(ox, y, w, 20, CREAM if d < 1000 else PINK, INK, 2)
    f.text(ox + w + 8, y + 15, f"{d} ms" + ("  (capped)" if d == 1000 else ""), 10, mono=True)
f.text(620, 70, "full jitter: pick a", 10, TEAL)
f.text(620, 86, "random delay from", 10, TEAL)
f.text(620, 102, "0 up to the bar", 10, TEAL)
f.text(20, 236, "exponential_delay(attempt) = min(base x 2^attempt, max_delay). A Retry-After hint from the server raises the delay,", 10, MUTED)
f.text(20, 252, "never lowers it.", 10, MUTED)
f.save(OUT + "backoff.svg")

# 4. jitter spreading retries
random.seed(7)
f = Figure(760, 230)
f.text(20, 22, "Twenty clients retry after a failure at time 0", 12, bold=True)
f.text(20, 56, "no jitter", 10, MUTED)
f.line(110, 60, 720, 60, "#c6ced6")
for i in range(20):
    f.rect(110 + 400 * 0.6 - 3, 44 + (i % 5) * 3, 6, 6, RUST, "none", 3)
f.text(360, 90, "all 20 retry at 400 ms, together", 10, RUST, anchor="middle")
f.text(20, 146, "full jitter", 10, MUTED)
f.line(110, 150, 720, 150, "#c6ced6")
for i in range(20):
    t = random.random() * 400
    f.rect(110 + t * 0.6 - 3, 144, 6, 6, TEAL, "none", 3)
f.text(360, 180, "each picks a random time in [0, 400 ms]: the load spreads out", 10, TEAL, anchor="middle")
for t in (0, 200, 400, 600, 800, 1000):
    f.text(110 + t * 0.6, 210, f"{t}", 9, MUTED, anchor="middle")
f.text(720, 210, "ms", 9, MUTED)
f.save(OUT + "jitter.svg")

# 5. idempotency
f = Figure(760, 230)
f.text(20, 22, "An idempotency key: the second call with the same key returns the stored result", 12, bold=True)
f.cell(20, 60, 200, 30, 'execute("order-1", charge)', GREEN, size=9)
f.arrow(220, 75, 260, 75)
f.cell(260, 60, 180, 30, "key not stored: run f()", CREAM, size=9)
f.arrow(440, 75, 480, 75)
f.cell(480, 60, 250, 30, 'charging card... store "txn_42"', PINK, size=9)
f.cell(20, 120, 200, 30, 'execute("order-1", charge)', GREEN, size=9)
f.arrow(220, 135, 260, 135)
f.cell(260, 120, 180, 30, "key stored: skip f()", CREAM, size=9)
f.arrow(440, 135, 480, 135)
f.cell(480, 120, 250, 30, 'return "txn_42" again', GREEN, size=9)
f.text(20, 186, "A client that retries after a timeout sends the same key. The card is charged once, and both calls get the same answer.", 10)
f.text(20, 204, "A failed f() stores nothing, so the next call with that key tries again.", 10, MUTED)
f.save(OUT + "idempotency.svg")
print("ok")
