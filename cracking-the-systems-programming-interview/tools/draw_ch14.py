"""Figures for chapter 14: shards and consistent hashing."""
import math
from svgkit import *
OUT = "src/figures/"
NODE_COLORS = {"a": RUST, "b": TEAL, "c": BRASS}


def circle(f, cx, cy, r, fill="none", stroke=INK, width=1.6):
    f.parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{width}"/>')


# 1. one lock against many
f = Figure(760, 250)
f.text(20, 22, "One lock for the whole map, or one lock per shard", 12, bold=True)
f.text(20, 50, "Mutex<HashMap>: every thread waits for the one lock", 11, MUTED)
f.rect(40, 70, 200, 120, PALE, INK, 6); f.text(140, 136, "Mutex<HashMap>", 11, mono=True, anchor="middle")
for i, (t, state) in enumerate([("thread 1", "holds the lock"), ("thread 2", "waits"), ("thread 3", "waits"), ("thread 4", "waits")]):
    y = 76 + i * 30
    f.cell(260, y, 70, 22, t, GREEN if i == 0 else PINK, size=9)
    f.text(338, y + 15, state, 9, TEAL if i == 0 else RUST)
f.text(420, 50, "ShardedCache: threads on different shards run together", 11, MUTED)
for s in range(8):
    x = 420 + (s % 4) * 82; y = 70 + (s // 4) * 70
    busy = s in (0, 3, 6)
    f.rect(x, y, 72, 50, GREEN if busy else PALE, INK, 5)
    f.text(x + 36, y + 20, f"shard {s}", 10, mono=True, anchor="middle")
    f.text(x + 36, y + 38, "thread " + {0: "1", 3: "2", 6: "3"}[s] if busy else "idle", 9, TEAL if busy else MUTED, anchor="middle")
f.text(20, 234, "Two threads wait for each other only when their keys hash to the same shard.", 10, MUTED)
f.save(OUT + "shard-locks.svg")

# 2. the mask
f = Figure(760, 200)
f.text(20, 22, "Picking a shard: keep the low bits of the hash", 12, bold=True)
bits = "1011010011100110"
f.text(20, 58, "hash (last 16 bits)", 10, MUTED)
for i, b in enumerate(bits):
    f.cell(170 + i * 26, 42, 26, 26, b, GREEN if i >= 13 else PALE, size=11)
f.text(20, 98, "mask = 8 - 1 = 0b111", 10, MUTED)
for i, b in enumerate("0" * 13 + "111"):
    f.cell(170 + i * 26, 82, 26, 26, b, CREAM if b == "1" else "#ffffff", size=11)
f.text(20, 138, "hash & mask", 10, MUTED)
for i, b in enumerate("0" * 13 + "110"):
    f.cell(170 + i * 26, 122, 26, 26, b, GREEN if i >= 13 else "#ffffff", size=11)
f.text(600, 140, "= 6: shard 6", 11, TEAL, bold=True)
f.text(20, 182, "With a power-of-two count, hash & (count - 1) equals hash % count, computed with one AND instruction.", 10, MUTED)
f.save(OUT + "shard-mask.svg")

# 3. modulo remapping
f = Figure(760, 262)
f.text(20, 22, "Placing keys with hash % N: going from 3 nodes to 4 moves most keys", 12, bold=True)
hdr = ["hash", "% 3", "% 4", "moved?"]
for j, h in enumerate(hdr):
    f.text(60 + j * 90, 50, h, 10, MUTED, anchor="middle")
for i, h in enumerate(range(12)):
    y = 58 + (i % 6) * 28
    ox = 0 if i < 6 else 380
    a, b = h % 3, h % 4
    moved = a != b
    for j, v in enumerate([h, a, b, "yes" if moved else "no"]):
        f.cell(ox + 20 + j * 90, y, 80, 24, str(v), PINK if (moved and j == 3) else (GREEN if j == 3 else PALE), size=10)
    if i == 0:
        for j, hh in enumerate(hdr):
            f.text(400 + j * 90 + 20, 50, hh, 10, MUTED, anchor="middle")
f.text(20, 250, "Only hashes 0, 1, and 2 of every 12 keep their node: 3 in 12 stay, so 75% of the keys move.", 10, MUTED)
f.save(OUT + "shard-modulo.svg")

# 4. the ring
f = Figure(760, 340)
f.text(20, 22, "A hash ring with 3 nodes and 4 virtual nodes each", 12, bold=True)
cx, cy, R = 200, 185, 130
circle(f, cx, cy, R)
f.text(cx, cy - R - 10, "0 / 2^64", 10, MUTED, anchor="middle")
points = [(10, "a"), (38, "b"), (70, "c"), (104, "a"), (140, "b"), (170, "c"), (205, "b"), (232, "a"), (262, "c"),
          (290, "b"), (318, "c"), (345, "a")]
for deg, n in points:
    t = math.radians(deg - 90)
    x, y = cx + R * math.cos(t), cy + R * math.sin(t)
    circle(f, round(x, 1), round(y, 1), 10, NODE_COLORS[n], INK, 1.2)
    f.text(round(x, 1), round(y + 4, 1), n, 10, "#ffffff", anchor="middle", bold=True)
kd = 120
t = math.radians(kd - 90); kx, ky = cx + R * math.cos(t), cy + R * math.sin(t)
f.rect(kx - 6, ky - 6, 12, 12, INK, INK, 1)
f.text(kx + 14, ky - 10, 'hash("job-42")', 10, mono=True)
for a0 in range(kd + 4, 138, 3):
    t0, t1 = math.radians(a0 - 90), math.radians(a0 + 2 - 90)
    f.line(round(cx + (R + 14) * math.cos(t0), 1), round(cy + (R + 14) * math.sin(t0), 1),
           round(cx + (R + 14) * math.cos(t1), 1), round(cy + (R + 14) * math.sin(t1), 1), TEAL, 2.4)
f.text(cx, cy - 6, "hash values increase", 10, MUTED, anchor="middle")
f.text(cx, cy + 10, "clockwise", 10, MUTED, anchor="middle")
notes = ["Each node is placed at several points, its virtual nodes.",
         "A key belongs to the first point clockwise from its hash.",
         "job-42 lands between an a point and a b point,",
         "so its owner is node b.",
         "A hash past the last point wraps around to the first."]
for i, t_ in enumerate(notes):
    f.text(400, 90 + i * 22, t_, 11)
for i, n in enumerate("abc"):
    circle(f, 410 + i * 110, 300, 8, NODE_COLORS[n], INK, 1.2); f.text(424 + i * 110, 304, f"node-{n}", 10)
f.save(OUT + "ring.svg")

# 5. adding a node
f = Figure(760, 250)
f.text(20, 22, "Adding node c: only keys in the arcs that c takes over change owner", 12, bold=True)
def strip(y, pts, label):
    f.text(20, y + 5, label, 10, MUTED)
    f.line(120, y, 720, y, INK, 1.4)
    for x, n in pts:
        circle(f, x, y, 9, NODE_COLORS[n], INK, 1.2); f.text(x, y + 4, n, 9, "#ffffff", anchor="middle", bold=True)
before = [(170, "a"), (300, "b"), (430, "a"), (560, "b"), (690, "a")]
strip(70, before, "before")
after = sorted(before + [(250, "c"), (500, "c")])
strip(160, after, "after")
for x0, x1, owner in [(120, 170, "a"), (170, 300, "b"), (300, 430, "a"), (430, 560, "b"), (560, 690, "a")]:
    f.text((x0 + x1) / 2, 98, f"keys here go to {owner}", 8, MUTED, anchor="middle")
for x0, x1 in [(170, 250), (430, 500)]:
    f.rect(x0 + 10, 176, x1 - x0 - 20, 14, PINK, RUST, 3)
f.text(210, 206, "moved b to c", 9, RUST, anchor="middle"); f.text(465, 206, "moved b to c", 9, RUST, anchor="middle")
f.text(20, 236, "Every other key keeps its owner. With n nodes, adding one moves about 1/(n+1) of the keys.", 10, MUTED)
f.save(OUT + "ring-add.svg")

# 6. partition_point on the sorted ring
f = Figure(760, 190)
f.text(20, 22, "Finding the owner: partition_point on the sorted Vec", 12, bold=True)
ring = [(12, "a"), (31, "b"), (47, "c"), (58, "a"), (73, "b"), (90, "c")]
f.text(20, 58, "ring", 10, MUTED)
for i, (h, n) in enumerate(ring):
    f.cell(80 + i * 100, 42, 100, 28, f"({h}, {n})", GREEN if i == 3 else (PALE if h > 50 else GREY), size=10)
    f.text(130 + i * 100, 88, str(i), 9, MUTED, anchor="middle")
f.text(20, 118, "key hash 50: point <= 50 is true for indexes 0 to 2 and false from index 3, so partition_point returns 3.", 10)
f.text(20, 138, "The owner is ring[3], node a. A hash above 90 would return 6, the length, which wraps to index 0.", 10)
f.text(20, 162, "The predicate must be true for a prefix and false after it. A sorted ring guarantees that.", 10, MUTED)
f.save(OUT + "ring-search.svg")
print("ok")
