"""Figures for chapter 17: queues and bounded buffers."""
import math
from svgkit import *
OUT = "src/figures/"

# 1. unbounded against bounded
f = Figure(760, 250)
f.text(20, 22, "A fast producer and a slow consumer", 12, bold=True)
f.text(20, 50, "unbounded: the queue grows until memory runs out", 10, MUTED)
f.cell(20, 60, 110, 30, "producer", GREEN, size=10)
for i in range(11):
    f.rect(150 + i * 36, 62, 32, 26, PINK if i > 6 else PALE, INK, 3)
f.text(546, 80, "...", 14, RUST)
f.cell(610, 60, 110, 30, "consumer", CREAM, size=10)
f.arrow(130, 75, 148, 75); f.arrow(568, 75, 608, 75, MUTED)
f.text(20, 140, "bounded (capacity 3): a full queue makes the producer wait", 10, MUTED)
f.cell(20, 150, 110, 30, "producer", GREY, size=10)
f.text(75, 198, "waits in push()", 9, RUST, anchor="middle")
for i in range(3):
    f.rect(260 + i * 36, 152, 32, 26, PALE, INK, 3)
f.rect(252, 146, 124, 38, "none", TEAL, 6, dash=True)
f.cell(610, 150, 110, 30, "consumer", CREAM, size=10)
f.arrow(130, 165, 250, 165, RUST, dash=True); f.arrow(378, 165, 608, 165, MUTED)
f.text(20, 236, "Making the producer wait is called backpressure. The system slows down instead of failing.", 10, MUTED)
f.save(OUT + "queue-backpressure.svg")

# 2. two waiting rooms
f = Figure(760, 270)
f.text(20, 22, "One Mutex, two Condvars: producers wait in not_full, consumers wait in not_empty", 12, bold=True)
f.rect(250, 60, 260, 120, PALE, INK, 8)
f.text(380, 82, "Mutex<VecDeque<T>>", 11, mono=True, anchor="middle")
for i in range(3):
    f.cell(290 + i * 60, 100, 56, 30, f"item", GREEN, size=10)
f.text(380, 160, "full: len == capacity", 10, RUST, anchor="middle")
f.rect(20, 60, 180, 120, CREAM, BRASS, 8)
f.text(110, 82, "not_full", 11, mono=True, anchor="middle", bold=True)
f.text(110, 108, "producer 0 sleeping", 10, anchor="middle"); f.text(110, 128, "producer 1 sleeping", 10, anchor="middle")
f.rect(560, 60, 180, 120, CREAM, BRASS, 8)
f.text(650, 82, "not_empty", 11, mono=True, anchor="middle", bold=True)
f.text(650, 108, "(empty: no consumer", 10, MUTED, anchor="middle"); f.text(650, 124, "is waiting now)", 10, MUTED, anchor="middle")
f.text(20, 214, "pop() takes an item, then calls not_full.notify_one(): one slot opened, so one producer wakes.", 10)
f.text(20, 232, "push() adds an item, then calls not_empty.notify_one(): one item arrived, so one consumer wakes.", 10)
f.text(20, 256, "A woken thread relocks the mutex and checks its condition again before it continues.", 10, MUTED)
f.save(OUT + "queue-condvars.svg")

# 3. wait step by step
f = Figure(760, 250)
f.text(20, 22, "What happens inside a blocked push", 12, bold=True)
steps = [("1", "lock the mutex", "producer holds the guard"),
         ("2", "len == capacity: call not_full.wait(guard)", "wait unlocks the mutex and sleeps, in one step"),
         ("3", "a consumer locks, pops, unlocks", "then calls not_full.notify_one()"),
         ("4", "wait returns a new guard", "the producer holds the mutex again"),
         ("5", "while loop checks len again", "another producer may have taken the slot"),
         ("6", "push_back, unlock, notify not_empty", "")]
for i, (n, a, b) in enumerate(steps):
    y = 44 + i * 32
    f.rect(20, y, 24, 24, TEAL if n != "3" else RUST, "none", 12); f.text(32, y + 16, n, 11, "#ffffff", anchor="middle", bold=True)
    f.text(56, y + 16, a, 11, mono=True)
    f.text(420, y + 16, b, 10, MUTED)
f.save(OUT + "queue-wait.svg")

# 4. close
f = Figure(760, 220)
f.text(20, 22, "Closing a queue: everyone waiting wakes up, and the loops end", 12, bold=True)
rows = [("close()", "closed = true, then notify_all on both condvars", CREAM),
        ("push(item) after close", "returns Err(item): the caller gets the item back", PINK),
        ("pop() with items left", "returns Some(item): the queue drains first", GREEN),
        ("pop() when empty and closed", "returns None: a while let Some(..) loop ends", PALE)]
for i, (a, b, fill) in enumerate(rows):
    y = 44 + i * 40
    f.cell(20, y, 250, 30, a, fill, size=10)
    f.text(290, y + 20, b, 11)
f.save(OUT + "queue-close.svg")

# 5. ring buffer
f = Figure(760, 290)
f.text(20, 22, "An SPSC ring with N = 8 slots: head and tail only grow, and index = counter % N", 12, bold=True)
cx, cy, R = 230, 160, 100
for k in range(8):
    a0 = math.radians(k * 45 - 90 - 22.5); a1 = math.radians(k * 45 - 90 + 22.5)
    full = k in (3, 4, 5)
    pts = [(cx + 50 * math.cos(a0), cy + 50 * math.sin(a0)), (cx + R * math.cos(a0), cy + R * math.sin(a0)),
           (cx + R * math.cos(a1), cy + R * math.sin(a1)), (cx + 50 * math.cos(a1), cy + 50 * math.sin(a1))]
    d = f"M {pts[0][0]:.1f} {pts[0][1]:.1f} L {pts[1][0]:.1f} {pts[1][1]:.1f} A {R} {R} 0 0 1 {pts[2][0]:.1f} {pts[2][1]:.1f} L {pts[3][0]:.1f} {pts[3][1]:.1f} A 50 50 0 0 0 {pts[0][0]:.1f} {pts[0][1]:.1f} Z"
    f.parts.append(f'<path d="{d}" fill="{GREEN if full else "#ffffff"}" stroke="{INK}" stroke-width="1.2"/>')
    am = math.radians(k * 45 - 90)
    f.text(cx + 75 * math.cos(am), cy + 75 * math.sin(am) + 4, str(k), 10, mono=True, anchor="middle")
f.text(cx, cy + 4, "slots", 10, MUTED, anchor="middle")
am = math.radians(3 * 45 - 90); f.arrow(cx + 150 * math.cos(am), cy + 150 * math.sin(am) - 10, cx + 104 * math.cos(am), cy + 104 * math.sin(am), TEAL)
f.text(cx + 150 * math.cos(am) - 10, cy + 150 * math.sin(am) + 6, "head = 11", 10, TEAL, mono=True)
am = math.radians(6 * 45 - 90); f.arrow(cx + 150 * math.cos(am) - 10, cy + 150 * math.sin(am), cx + 104 * math.cos(am), cy + 104 * math.sin(am), RUST)
f.text(cx + 150 * math.cos(am) - 40, cy + 150 * math.sin(am) - 12, "tail = 14", 10, RUST, mono=True)
notes = ["The consumer reads at head % 8 = 3. Only it changes head.",
         "The producer writes at tail % 8 = 6. Only it changes tail.",
         "len = tail - head = 3 items, in slots 3, 4, and 5.",
         "full when tail - head == 8; empty when head == tail.",
         "push: write the slot, then store tail + 1 with Release.",
         "pop: load tail with Acquire, read the slot, store head + 1."]
for i, t in enumerate(notes):
    f.text(410, 90 + i * 24, t, 10)
f.save(OUT + "ring.svg".replace("ring", "spsc-ring"))

# 6. error conversions
f = Figure(760, 220)
f.text(20, 22, "Three ways the queues handle a poisoned mutex", 12, bold=True)
f.cell(20, 60, 230, 30, "lock(): Err(PoisonError<Guard>)", PINK, size=10)
opts = [("bounded_buffer.rs", ".unwrap(): the thread panics too", GREY),
        ("..._with_error_handling.rs", ".map_poison()?: Err(QueuePoisonedError)", GREEN),
        ("..._error_propagation.rs", ".map_err(|e| e.to_string())?: Box<dyn Error>", CREAM)]
for i, (a, b, fill) in enumerate(opts):
    y = 40 + i * 44
    f.arrow(250, 75, 300, y + 15, MUTED, 1.2)
    f.cell(300, y, 440, 30, f"{a}  {b}", fill, size=9)
f.text(20, 190, "The PoisonError holds a guard that borrows the mutex, so it cannot leave the function in a Box<dyn Error>.", 10, MUTED)
f.text(20, 206, "Both error-returning versions convert it into a value that owns nothing: a unit struct, or a String.", 10, MUTED)
f.save(OUT + "queue-errors.svg")

# 7. two producers on one tail, without and with compare-and-swap
f = Figure(760, 330)
f.text(20, 22, "Two producers push at the same moment", 12, bold=True)
f.text(20, 40, "Both producers read tail = 2. What happens next depends on how they advance it.", 10, MUTED)
f.panel(20, 56, 350, 250, "A plain store, as in the SPSC ring")
rows = [("A", "load tail -> 2", GREEN), ("B", "load tail -> 2", CREAM),
        ("A", "write 10 into slot 2", GREEN), ("B", "write 20 into slot 2", CREAM),
        ("A", "store tail = 3", GREEN), ("B", "store tail = 3", CREAM)]
for i, (who, what, fill) in enumerate(rows):
    y = 86 + i * 28
    f.cell(36, y, 30, 22, who, fill, size=10)
    f.text(78, y + 15, what, 10, mono=True)
f.text(36, 268, "Slot 2 holds 20, and the value 10 is lost.", 10, RUST, bold=True)
f.text(36, 286, "tail is 3 after two pushes, not 4.", 10, RUST)
f.panel(390, 56, 350, 250, "compare_exchange(2, 3) on tail")
rows = [("A", "CAS 2 -> 3 succeeds", GREEN), ("B", "CAS 2 -> 3 fails, sees 3", CREAM),
        ("A", "write 10 into slot 2", GREEN), ("B", "CAS 3 -> 4 succeeds", CREAM),
        ("B", "write 20 into slot 3", CREAM)]
for i, (who, what, fill) in enumerate(rows):
    y = 86 + i * 28
    f.cell(406, y, 30, 22, who, fill, size=10)
    f.text(448, y + 15, what, 10, mono=True)
f.text(406, 268, "Each position has exactly one owner.", 10, TEAL, bold=True)
f.text(406, 286, "Both values are kept, and tail is 4.", 10, TEAL)
f.save(OUT + "mpmc-cas.svg")

# 8. the life of one slot
f = Figure(760, 250)
f.text(20, 22, "The sequence number of slot 0 in a queue with capacity 4", 12, bold=True)
f.text(20, 40, "seq tells every thread whose turn the slot is. It only grows, so an old reading is never mistaken for a new one.", 10, MUTED)
states = [("seq = 0", "empty", "waits for the producer", "of position 0", PALE),
          ("seq = 1", "full", "waits for the consumer", "of position 0", GREEN),
          ("seq = 4", "empty", "waits for the producer", "of position 4", PALE),
          ("seq = 5", "full", "waits for the consumer", "of position 4", GREEN)]
for i, (a, b, c, d, fill) in enumerate(states):
    x = 20 + i * 188
    f.rect(x, 70, 150, 92, fill, BORDER, 8)
    f.text(x + 75, 92, a, 12, mono=True, anchor="middle", bold=True)
    f.text(x + 75, 112, b, 10, TEAL if fill == PALE else RUST, anchor="middle", bold=True)
    f.text(x + 75, 132, c, 9, MUTED, anchor="middle")
    f.text(x + 75, 146, d, 9, MUTED, anchor="middle")
labels = ["push writes, then\nstores seq = 0 + 1", "pop reads, then\nstores seq = 0 + 4", "push writes, then\nstores seq = 4 + 1"]
for i, label in enumerate(labels):
    x = 20 + i * 188 + 150
    f.arrow(x + 4, 116, x + 34, 116, INK)
    for j, line in enumerate(label.split("\n")):
        f.text(x + 19, 186 + j * 14, line, 9, anchor="middle")
f.text(20, 236, "Producer rule: proceed when seq == position.   Consumer rule: proceed when seq == position + 1.", 10, INK, bold=True)
f.save(OUT + "mpmc-slot-cycle.svg")

# 9. four slots across four operations
f = Figure(760, 300)
f.text(20, 22, "A queue with capacity 4: the counters and the sequence number of every slot", 12, bold=True)
steps = [("start", 0, 0, [("0", ""), ("1", ""), ("2", ""), ("3", "")]),
         ("push A", 1, 0, [("1", "A"), ("1", ""), ("2", ""), ("3", "")]),
         ("push B", 2, 0, [("1", "A"), ("2", "B"), ("2", ""), ("3", "")]),
         ("pop A", 2, 1, [("4", ""), ("2", "B"), ("2", ""), ("3", "")])]
for k in range(4):
    f.text(176 + k * 84 + 37, 52, f"slot {k}", 10, MUTED, anchor="middle")
for i, (name, tail, head, slots) in enumerate(steps):
    y = 64 + i * 54
    f.text(20, y + 26, name, 11, bold=True)
    f.text(90, y + 18, f"tail = {tail}", 9, RUST, mono=True)
    f.text(90, y + 34, f"head = {head}", 9, TEAL, mono=True)
    for k, (seq, val) in enumerate(slots):
        x = 176 + k * 84
        fill = GREEN if val else PALE
        f.rect(x, y, 74, 42, fill, BORDER, 6)
        f.text(x + 37, y + 18, f"seq {seq}", 10, mono=True, anchor="middle", bold=True)
        f.text(x + 37, y + 34, val if val else "empty", 10, INK if val else MUTED, anchor="middle")
notes = ["Slot k starts with seq = k.",
         "A push at position p stores",
         "seq = p + 1: full.",
         "A pop at position p stores",
         "seq = p + 4: empty for the",
         "producer one lap later.",
         "Slot 0 now waits for",
         "position 4, because 4 % 4 = 0."]
for i, t in enumerate(notes):
    f.text(530, 84 + i * 22, t, 10)
f.save(OUT + "mpmc-trace.svg")

# 10. the handoff through seq
f = Figure(760, 250)
f.text(20, 22, "How the value reaches the consumer: Release on seq, then Acquire on seq", 12, bold=True)
f.panel(20, 46, 330, 170, "Producer of position 5")
f.cell(40, 80, 290, 30, "write the value into the slot", GREEN, size=10)
f.cell(40, 140, 290, 30, "seq.store(6, Release)", GREEN, size=10)
f.arrow(185, 112, 185, 138, INK)
f.text(40, 196, "The write happens before the store.", 10, MUTED)
f.panel(410, 46, 330, 170, "Consumer of position 5")
f.cell(430, 80, 290, 30, "seq.load(Acquire) returns 6", CREAM, size=10)
f.cell(430, 140, 290, 30, "read the value from the slot", CREAM, size=10)
f.arrow(575, 112, 575, 138, INK)
f.text(430, 196, "The load happens before the read.", 10, MUTED)
f.arrow(332, 155, 428, 95, TEAL, dash=True)
f.text(380, 104, "synchronizes", 9, TEAL, anchor="middle")
f.text(380, 116, "with", 9, TEAL, anchor="middle")
f.text(20, 238, "Because the consumer saw 6, it is guaranteed to see every write the producer made before storing 6.", 10)
f.save(OUT + "mpmc-handoff.svg")
print("ok")
