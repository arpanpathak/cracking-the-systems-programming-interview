"""Figures for chapter 16: threads, atomics, and locks."""
import math
from svgkit import *
OUT = "src/figures/"


def circle(f, cx, cy, r, fill="none", stroke=INK, width=1.6):
    f.parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')


# 1. lost update
f = Figure(760, 250)
f.text(20, 22, "Two threads add 1 to the same plain counter. One increment is lost", 12, bold=True)
f.text(120, 50, "thread 1", 11, TEAL, anchor="middle", bold=True); f.text(400, 50, "thread 2", 11, RUST, anchor="middle", bold=True)
f.text(640, 50, "counter in memory", 11, MUTED, anchor="middle")
steps = [("read 5", "", "5"), ("", "read 5", "5"), ("add 1: 6", "", "5"), ("", "add 1: 6", "5"), ("write 6", "", "6"), ("", "write 6", "6")]
for i, (a, b, m) in enumerate(steps):
    y = 62 + i * 26
    if a:
        f.cell(40, y, 160, 22, a, GREEN, size=10)
    if b:
        f.cell(320, y, 160, 22, b, PINK, size=10)
    f.cell(600, y, 80, 22, m, PALE, size=10)
f.text(20, 236, "Both threads read 5 before either wrote. The final value is 6, not 7. fetch_add does the read, add, and write as one step.", 10, MUTED)
f.save(OUT + "lost-update.svg")

# 2. scoped threads summing chunks
f = Figure(760, 250)
f.text(20, 22, "thread::scope: workers borrow chunks of the slice, and the scope waits for all of them", 12, bold=True)
f.text(20, 52, "values: &[i32]", 10, MUTED, mono=True)
for i in range(4):
    f.cell(20 + i * 180, 60, 180, 28, f"chunk {i}", [GREEN, CREAM, PINK, PALE][i], size=10)
    f.arrow(110 + i * 180, 90, 110 + i * 180, 120)
    f.cell(50 + i * 180, 122, 120, 28, f"worker {i}: sum", "#ffffff", size=10)
    f.arrow(110 + i * 180, 152, 380, 190, MUTED, 1.2)
f.cell(300, 192, 160, 28, "join all, add", GREEN, size=10)
f.text(20, 240, "Each worker holds a &[i32] into the caller's data. No Arc is needed, because the scope ends before the data can be dropped.", 10, MUTED)
f.save(OUT + "scope-chunks.svg")

# 3. Amdahl
f = Figure(760, 320)
f.text(20, 22, "Amdahl's law: speedup = 1 / (s + (1 - s) / p)", 12, bold=True)
ox, oy, W, H = 70, 280, 440, 240
f.line(ox, oy, ox + W, oy); f.line(ox, oy, ox, oy - H)
for p in (1, 2, 4, 8, 16):
    x = ox + (math.log2(p) / 4) * W
    f.line(x, oy, x, oy + 5); f.text(x, oy + 18, str(p), 10, MUTED, anchor="middle")
f.text(ox + W / 2, oy + 34, "processors (log scale)", 10, MUTED, anchor="middle")
for v in (1, 4, 8, 12, 16):
    y = oy - (v / 16) * H
    f.line(ox - 5, y, ox, y); f.text(ox - 8, y + 4, str(v), 10, MUTED, anchor="end")
f.text(ox + 10, 44, "speedup", 10, MUTED)
colors = [INK, TEAL, BRASS, RUST, "#8a5cc2"]
for idx, s in enumerate((0.0, 0.05, 0.10, 0.25, 0.50)):
    pts = []
    for k in range(0, 41):
        p = 2 ** (k / 10)
        sp = 1 / (s + (1 - s) / p)
        pts.append(f"{ox + (math.log2(p) / 4) * W:.1f},{oy - (sp / 16) * H:.1f}")
    f.parts.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="{colors[idx]}" stroke-width="2"/>')
    end = 1 / (s + (1 - s) / 16)
    f.text(560, 70 + idx * 26, f"serial {s:.2f}: {end:.2f}x at 16", 11, colors[idx])
f.text(560, 220, "The serial part never shrinks.", 10, MUTED)
f.text(560, 236, "As p grows, speedup approaches 1 / s.", 10, MUTED)
f.save(OUT + "amdahl.svg")

# 4. acquire / release
f = Figure(760, 260)
f.text(20, 22, "Release and acquire: what one thread wrote before releasing, the next sees after acquiring", 12, bold=True)
f.text(150, 52, "thread A", 11, TEAL, anchor="middle", bold=True); f.text(560, 52, "thread B", 11, RUST, anchor="middle", bold=True)
a = [("lock: CAS false to true (Acquire)", PALE), ("*value += 1", GREEN), ("unlock: store false (Release)", CREAM)]
for i, (t, fill) in enumerate(a):
    f.cell(40, 64 + i * 40, 230, 28, t, fill, size=10)
b = [("spin: load is true, wait", GREY), ("spin: load is true, wait", GREY), ("CAS false to true (Acquire)", CREAM), ("reads *value: sees + 1", GREEN)]
for i, (t, fill) in enumerate(b):
    f.cell(450, 64 + i * 40, 230, 28, t, fill, size=10)
f.arrow(270, 158, 450, 158, BRASS, 2)
f.text(360, 150, "synchronizes with", 10, BRASS, anchor="middle")
f.text(20, 236, "Release keeps A's earlier writes from moving after the unlock. Acquire keeps B's later reads from moving before the lock.", 10, MUTED)
f.text(20, 252, "Together they guarantee that B sees the increment.", 10, MUTED)
f.save(OUT + "acquire-release.svg")

# 5. semaphore
f = Figure(760, 220)
f.text(20, 22, "A semaphore with 2 permits: at most two threads run the guarded section at once", 12, bold=True)
f.rect(260, 50, 240, 110, PALE, INK, 8)
f.text(380, 72, "Mutex<State> + Condvar", 10, MUTED, mono=True, anchor="middle")
f.text(380, 100, "available: 0", 12, mono=True, anchor="middle", bold=True)
f.text(380, 124, "waiters sleep on the Condvar", 10, MUTED, anchor="middle")
f.text(380, 140, "until release calls notify_one", 10, MUTED, anchor="middle")
for i, t in enumerate(["thread 1: holds a permit", "thread 2: holds a permit"]):
    f.cell(540, 60 + i * 40, 200, 28, t, GREEN, size=10)
for i, t in enumerate(["thread 3: waiting", "thread 4: waiting"]):
    f.cell(30, 60 + i * 40, 200, 28, t, PINK, size=10)
f.arrow(230, 74, 258, 90, RUST, 1.2); f.arrow(230, 114, 258, 110, RUST, 1.2)
f.text(20, 196, "Dropping a SemaphoreGuard adds 1 to available and wakes one waiter, which then takes the permit.", 10, MUTED)
f.save(OUT + "semaphore.svg")

# 6. poisoning timeline
f = Figure(760, 230)
f.text(20, 22, "A panic while holding a MutexGuard poisons the Mutex", 12, bold=True)
tl = [("Branch A|locks", PALE), ("stock 5000|to 4000", GREEN), ("cash 10000|to 11200", GREEN), ("panic! guard|dropped", PINK),
      ("Mutex|poisoned", PINK), ("Audit: lock()|is Err", CREAM), ("into_inner()|repairs data", GREEN)]
for i, (t, fill) in enumerate(tl):
    x = 20 + i * 104
    f.cell(x, 60, 100, 44, "", fill, size=9)
    top, bottom = t.split("|")
    f.text(x + 50, 78, top, 9, anchor="middle")
    f.text(x + 50, 94, bottom, 9, anchor="middle")
    if i:
        f.arrow(x - 4, 82, x, 82, MUTED, 1)
f.text(20, 140, "The transaction stopped halfway: stock went down and cash went up, but it was never marked settled.", 10)
f.text(20, 158, "Poisoning makes every later lock() return Err(PoisonError), so no thread reads the half-done state by accident.", 10)
f.text(20, 176, "PoisonError::into_inner() hands over the guard anyway, for code that knows how to repair the data.", 10)
f.text(20, 210, "Repairing the data does not clear the flag: later lock() calls still return Err.", 10, MUTED)
f.save(OUT + "poison.svg")

# 7. wait-for graphs
f = Figure(760, 220)
f.text(20, 22, "Wait-for graphs: an edge from T0 to T1 means T0 waits for a lock that T1 holds", 12, bold=True)
def tnode(x, y, label, fill=PALE):
    circle(f, x, y, 20, fill); f.text(x, y + 4, label, 11, mono=True, anchor="middle")
def tedge(a, b, color=INK):
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    f.arrow(a[0] + 21 * math.cos(ang), a[1] + 21 * math.sin(ang), b[0] - 22 * math.cos(ang), b[1] - 22 * math.sin(ang), color)
L = {"T0": (90, 90), "T1": (230, 90), "T2": (160, 180)}
tedge(L["T0"], L["T1"]); tedge(L["T1"], L["T2"]); tedge(L["T0"], L["T2"])
for k, p in L.items():
    tnode(*p, k)
f.text(90, 210, "no cycle: T2 finishes, then T1, then T0", 10, TEAL)
R = {"T0": (470, 90), "T1": (610, 90), "T2": (540, 180)}
tedge(R["T0"], R["T1"], RUST); tedge(R["T1"], R["T2"], RUST); tedge(R["T2"], R["T0"], RUST)
for k, p in R.items():
    tnode(*p, k, PINK)
f.text(470, 210, "cycle: each waits for the next, forever", 10, RUST)
f.save(OUT + "wait-for.svg")
print("ok")
