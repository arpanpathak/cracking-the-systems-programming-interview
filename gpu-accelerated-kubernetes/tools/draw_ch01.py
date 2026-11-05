#!/usr/bin/env python3
"""The figures of chapter 1, written to src/figures/ch01-*.svg.

    python3 tools/draw_ch01.py                 # every figure
    python3 tools/draw_ch01.py revisions       # some of them

Each figure shows the data a mechanism works on: the revisions in etcd, the
versions a client sends, the names in the work queue. The cards, wires and
the frame come from figkit, so the figures match the rest of the book.
"""
import sys
from html import escape
from pathlib import Path

from figkit import EDGE, INK, KINDS, MUTED, PAPER, WIRE, card, save, tag, text, width_of, wire

OUT = Path(__file__).resolve().parent.parent / "src" / "figures"
FIGURES = {}

# One colour per object, used for every cell that belongs to it.
KEY = {"job-a": "client", "job-b": "service", "pod-1": "store", "pod-2": "outside"}
GREY = ("#9AA6B2", "#EEF1F4")


def figure(draw):
    FIGURES[draw.__name__.replace("_", "-")] = draw

    return draw


def tone(kind):
    return GREY if kind == "grey" else KINDS[kind]


def cell(x, y, w, h, kind, body="", cls="mono", bold=False, dashed=False, strong=False):
    """A rectangle in the colours of `kind`, with `body` in its middle."""
    accent, tint = tone(kind)
    dash = ' stroke-dasharray="4 3"' if dashed else ""
    fill = accent if strong else tint
    colour = "#FFFFFF" if strong else (accent if bold else INK)
    weight = ' font-weight="700"' if bold or strong else ""
    parts = [f'  <rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="6" fill="{fill}"'
             f' stroke="{accent}" stroke-width="1.3"{dash}/>']
    if body:
        parts.append(f'  <text x="{x + w / 2:.1f}" y="{y + h / 2 + 4.3:.1f}" class="{cls}" text-anchor="middle"'
                     f' style="fill:{colour}"{weight}>{escape(body)}</text>')

    return "\n".join(parts)


def label(x, y, body, cls="note", anchor="start", fill=None):
    return text(x, y, body, cls, anchor, fill)


def line(x1, y1, x2, y2, colour=WIRE, width=1.4, dash=None, arrow=False):
    dashed = f' stroke-dasharray="{dash}"' if dash else ""
    head = ' marker-end="url(#head)"' if arrow else ""

    return (f'  <path d="M{x1:.1f},{y1:.1f} L{x2:.1f},{y2:.1f}" fill="none" stroke="{colour}"'
            f' stroke-width="{width}"{dashed}{head}/>')


def bracket(x1, x2, y, body, kind="client", up=False):
    """A square bracket under (or over) the span x1..x2, with a label."""
    accent, _ = tone(kind)
    tip = -7 if up else 7
    path = f"M{x1},{y + tip} V{y} H{x2} V{y + tip}"

    return "\n".join([f'  <path d="{path}" fill="none" stroke="{accent}" stroke-width="1.6"/>',
                      text((x1 + x2) / 2, y + (-10 if up else 22), body, "pill", "middle", accent)])


def badge(x, y, n):
    """A numbered step marker centred on (x, y)."""
    return (f'  <circle cx="{x}" cy="{y}" r="10" fill="{INK}"/>\n'
            f'  <text x="{x}" y="{y + 4}" class="pill" text-anchor="middle" style="fill:#FFFFFF">{n}</text>')


def panel(x, y, w, h, heading, kind="idle"):
    """A light frame with a heading tab, for one half of a comparison."""
    accent, _ = tone(kind)

    return "\n".join([
        f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="#FFFFFF" stroke="{EDGE}" stroke-width="1.2"/>',
        f'  <rect x="{x}" y="{y}" width="{w}" height="4" rx="2" fill="{accent}"/>',
        text(x + 18, y + 30, heading, "name", fill=accent),
    ])


# Figure 1.1 -----------------------------------------------------------------

WRITES = ["job-a", "job-b", "pod-1", "job-a", "job-a", "pod-2", "job-b", "pod-1", "job-a", "job-b", "job-a", "pod-2"]


@figure
def revisions():
    x0, y0, w, h, gap = 112, 118, 66, 40, 6
    parts = [label(32, y0 + 25, "revision", "tab"), label(32, y0 + 70, "key written", "tab")]

    for i, key in enumerate(WRITES):
        x = x0 + i * (w + gap)
        parts += [cell(x, y0, w, h, KEY[key], str(i + 1), bold=True),
                  label(x + w / 2, y0 + 70, key, "mono", "middle", KINDS[KEY[key]][0])]

    # The key index: for each key, the revisions that wrote it.
    iy = 250
    parts.append(label(32, iy - 22, "THE KEY INDEX: EVERY REVISION OF EVERY KEY", "tab"))
    for row, key in enumerate(["job-a", "job-b", "pod-1", "pod-2"]):
        y = iy + row * 46
        revs = [i + 1 for i, k in enumerate(WRITES) if k == key]
        parts += [cell(32, y, 96, 34, KEY[key], key, bold=True),
                  line(128, y + 17, 150, y + 17, arrow=True)]
        for j, r in enumerate(revs):
            last = j == len(revs) - 1
            parts.append(cell(156 + j * 50, y + 2, 42, 30, KEY[key], str(r), strong=last))
        parts.append(label(156 + len(revs) * 50 + 10, y + 22,
                           f"resourceVersion {revs[-1]}", "note"))

    parts += [
        label(560, iy + 2, "Every create, update and delete takes the next value", "note"),
        label(560, iy + 21, "of 1 counter for the whole store.", "note"),
        label(560, iy + 52, "An object's resourceVersion is the revision of", "note"),
        label(560, iy + 71, "its latest write, the solid cell in each row.", "note"),
        label(560, iy + 102, "Old revisions stay readable until a compaction", "note"),
        label(560, iy + 121, "removes them.", "note"),
    ]
    save(OUT / "ch01-revisions.svg", 1000, 450,
         "Twelve writes numbered 1 to 12, coloured by the key they wrote: job-a, job-b, pod-1 and pod-2. "
         "Below, the key index lists for each key the revisions that wrote it. job-a was written at 1, 4, 5, 9 "
         "and 11, so its resourceVersion is 11.",
         "One counter numbers every write in etcd",
         "12 writes to 4 keys. The key index records which revisions wrote each key.", parts)


# Figure 1.2 -----------------------------------------------------------------

@figure
def conflict():
    xa, xs, xb = 150, 500, 850
    top, bottom = 110, 560
    parts = []
    for x, name, kind in [(xa, "client A", "client"), (xs, "API server", "service"), (xb, "client B", "outside")]:
        accent, tint = KINDS[kind]
        parts += [f'  <rect x="{x - 80}" y="{top - 30}" width="160" height="36" rx="8" fill="{tint}" stroke="{accent}" stroke-width="1.3"/>',
                  text(x, top - 7, name, "name", "middle", accent),
                  line(x, top + 6, x, bottom, EDGE, 2, "5 5")]

    steps = [
        (xa, xs, "GET job-a", None),
        (xs, xa, "v7  gpus 1  image x", "client"),
        (xb, xs, "GET job-a", None),
        (xs, xb, "v7  gpus 1  image x", "outside"),
        (xa, xs, "PUT gpus 2, read at v7", None),
        (xs, xa, "200 OK, now v8", "good"),
        (xb, xs, "PUT image y, read at v7", None),
        (xs, xb, "409 Conflict: object is at v8", "danger"),
        (xb, xs, "GET, then PUT image y, read at v8", None),
        (xs, xb, "200 OK, now v9: gpus 2, image y", "good"),
    ]
    for n, (x1, x2, body, kind) in enumerate(steps):
        y = top + 34 + n * 42
        colour = KINDS[kind][0] if kind else WIRE
        end = x2 - 6 if x2 > x1 else x2 + 6
        parts += [f'  <path d="M{x1},{y} H{end}" fill="none" stroke="{colour}" stroke-width="1.8" marker-end="url(#head)"/>',
                  text((x1 + x2) / 2, y - 7, body, "mono", "middle", colour if kind else INK),
                  badge(xa - 26 if xa in (x1, x2) else xb + 26, y, n + 1)]

    save(OUT / "ch01-conflict.svg", 1000, 580,
         "Client A and client B both read job-a at version 7. A writes 2 GPUs with version 7 and the server "
         "accepts it as version 8. B writes a new image with version 7 and the server answers 409 Conflict. B "
         "reads version 8, writes again with version 8, and the server stores version 9 with both changes.",
         "A write that names the version it was based on",
         "Client B's first write would undo client A's change, so the server refuses it.", parts)


# Figure 1.3 -----------------------------------------------------------------

@figure
def list_watch_gap():
    w, h, gap = 74, 40, 8
    parts = []

    def row(y, heading, watch_from, kind):
        x0 = 210
        out = [panel(32, y, 936, 170, heading, kind)]
        for i, v in enumerate(range(8, 15)):
            x = x0 + i * (w + gap)
            if v <= 10:
                out.append(cell(x, y + 56, w, h, "client", str(v)))
            elif v <= watch_from:
                out.append(cell(x, y + 56, w, h, "danger", str(v), bold=True, dashed=True))
            else:
                out.append(cell(x, y + 56, w, h, "good", str(v), bold=True))
        out += [label(50, y + 81, "versions", "tab"),
                bracket(x0, x0 + 3 * (w + gap) - gap, y + 106, "list snapshot at 10"),
                line(x0 + 3 * (w + gap) + 6 + (w + gap) * (watch_from - 10), y + 48,
                     x0 + 3 * (w + gap) + 6 + (w + gap) * (watch_from - 10), y + 106, INK, 2)]

        return out

    parts += row(90, "Watch from the list's version, 10", 10, "good")
    parts += [label(482 + 104, 90 + 148, "11 is replayed from history; 12 and later arrive live", "note")]
    parts += row(290, "Watch from the version current when the watch opens, 12", 12, "danger")
    parts += [label(482 + 104, 290 + 148, "11 and 12 happened before the watch opened and are never delivered", "note",
                    fill=KINDS["danger"][0])]
    parts += [tag(32, 486, "covered by the list", "client"), tag(200, 486, "delivered by the watch", "good"),
              tag(400, 486, "missed", "danger")]
    save(OUT / "ch01-list-watch-gap.svg", 1000, 520,
         "Two rows of versions 8 to 14. In both a list is taken at version 10. In the first row the watch starts "
         "from 10, and versions 11 to 14 are delivered. In the second the watch starts from 12, the version "
         "current when it opened, and versions 11 and 12 are missed.",
         "The watch must start from the list's version",
         "A list taken at 10, an edit at 11, and a watch opened when the store is at 12.", parts)


# Figure 1.4 -----------------------------------------------------------------

@figure
def watch_endings():
    parts = [card(340, 92, 320, 66, "service", "Watch from v", ["v: version of the last event applied"], glyph="swap")]
    columns = [
        (40, "client", "The stream closes", ["timeout, idle proxy,", "server restart"], "Watch again from v",
         ["the server replays", "everything after v"]),
        (370, "store", "The server is unreachable", ["connection refused,", "network partition"], "Wait, then retry from v",
         ["the wait doubles after", "each failure, with a cap"]),
        (700, "danger", "410 Gone", ["v is older than the", "compaction point"], "List again",
         ["Replace the cache, then", "watch from the new version"]),
    ]
    for x, kind, cause, why, action, how in columns:
        parts += [wire([(500, 158), (500, 196), (x + 130, 196), (x + 130, 236)]),
                  card(x, 236, 260, 78, kind, cause, why),
                  wire([(x + 130, 314), (x + 130, 364)]),
                  card(x, 364, 260, 78, "good", action, how)]
    save(OUT / "ch01-watch-endings.svg", 1000, 466,
         "A watch from version v can end in 3 ways. If the stream closes, the reflector watches again from v. If "
         "the server is unreachable, it waits and retries from v, doubling the wait after each failure. If the "
         "server answers 410 Gone, v is older than the compaction point and the reflector lists again.",
         "3 ways a watch ends, and what the reflector does next",
         "Each action ends in a new watch. Only 410 Gone costs a full list first.", parts)


# Figure 1.5 -----------------------------------------------------------------

@figure
def replace():
    rows = [
        ("job-a", "v9", "v11", "modified", "client", "queued"),
        ("job-b", "v10", None, "deleted", "danger", "queued"),
        ("job-c", None, "v12", "added", "good", "queued"),
        ("job-d", "v6", "v6", "unchanged", "grey", "not queued"),
    ]
    xs = [32, 232, 432, 632, 812]
    heads = ["object", "old cache", "new list at v12", "reported as", "work queue"]
    parts = [label(x, 112, hd.upper(), "tab") for x, hd in zip(xs, heads)]
    for r, (name, old, new, verdict, kind, queued) in enumerate(rows):
        y = 128 + r * 56
        parts += [cell(xs[0], y, 150, 40, "idle", name),
                  cell(xs[1], y, 150, 40, "client" if old else "grey", old or "absent", dashed=not old),
                  cell(xs[2], y, 150, 40, "client" if new else "grey", new or "absent", dashed=not new),
                  cell(xs[3], y, 150, 40, kind, verdict, cls="pill", bold=True),
                  cell(xs[4], y, 150, 40, "good" if queued == "queued" else "grey", queued, cls="pill")]
    parts += [label(32, 380, "job-b's deletion event was removed by the compaction. Its only trace is that it is in", "note"),
              label(32, 399, "the old cache and missing from the new list, so Replace must compare the two.", "note")]
    save(OUT / "ch01-replace.svg", 1000, 420,
         "Four objects compared between the old cache and a new list taken at version 12. job-a went from 9 to "
         "11 and is reported modified. job-b is in the old cache but not in the list and is reported deleted. "
         "job-c is new and reported added. job-d is unchanged at 6 and is not queued.",
         "Replace: what a new list tells us about the old cache",
         "A relist after 410 Gone. Every row that changed puts its name in the work queue.", parts)


# Figure 1.6 -----------------------------------------------------------------

@figure
def order():
    parts = []

    def lanes(x, y, heading, kind, steps, verdict, vkind):
        out = [panel(x, y, 456, 384, heading, kind)]
        for n, (who, body, k) in enumerate(steps):
            yy = y + 58 + n * 50
            lane_x = x + 24 if who == "reflector" else x + 236
            out += [badge(lane_x + 4, yy + 18, n + 1),
                    cell(lane_x + 20, yy, 176, 36, k, body, cls="note")]
        out += [label(x + 44, y + 50, "REFLECTOR", "tab"), label(x + 256, y + 50, "WORKER", "tab"),
                cell(x + 24, y + 330, 408, 36, vkind, verdict, cls="pill", bold=True)]

        return out

    parts += lanes(32, 90, "Queue first, then update the cache", "danger", [
        ("reflector", "event: gpus 1 to 2", "idle"),
        ("reflector", "queue job-a", "idle"),
        ("worker", "Get: job-a", "idle"),
        ("worker", "cache says gpus 1", "danger"),
        ("reflector", "cache: gpus 2", "idle"),
    ], "status already 1: done. The edit is never handled.", "danger")
    parts += lanes(512, 90, "Update the cache, then queue", "good", [
        ("reflector", "event: gpus 1 to 2", "idle"),
        ("reflector", "cache: gpus 2", "idle"),
        ("reflector", "queue job-a", "idle"),
        ("worker", "Get: job-a", "idle"),
        ("worker", "cache says gpus 2", "good"),
    ], "status 1, spec 2: the worker acts on the edit.", "good")
    save(OUT / "ch01-order.svg", 1000, 494,
         "Two orderings of the reflector's steps. Left: the name is queued before the cache is updated, a "
         "worker reads the old spec of 1 GPU, finds nothing to do, and the edit to 2 GPUs is never handled. Right: "
         "the cache is updated first, so the worker reads 2 GPUs and acts.",
         "The reflector updates the cache before it queues the name",
         "The same event in both columns. Only the order of 2 steps differs.", parts)


# Figure 1.7 -----------------------------------------------------------------

@figure
def queue_states():
    calls = [
        ("Add(job-a)", ["job-a"], ["job-a"], [], "ready for a worker"),
        ("Get() = job-a", [], [], ["job-a"], "a worker takes it, reconcile starts"),
        ("Add(job-a)", [], ["job-a"], ["job-a"], "edited during the run: marked dirty only"),
        ("Add(job-a) x3", [], ["job-a"], ["job-a"], "already dirty: no change"),
        ("Done(job-a)", ["job-a"], ["job-a"], [], "dirty, so ready again"),
        ("Get() = job-a", [], [], ["job-a"], "second reconcile reads the latest spec"),
    ]
    xs = [32, 232, 372, 512, 652]
    parts = [label(x, 112, hd, "tab") for x, hd in zip(xs, ["CALL", "READY", "DIRTY", "PROCESSING", "EFFECT"])]
    for r, (call, ready, dirty, proc, effect) in enumerate(calls):
        y = 126 + r * 50
        parts.append(cell(xs[0], y, 180, 38, "idle", call))
        for x, items, kind in [(xs[1], ready, "client"), (xs[2], dirty, "store"), (xs[3], proc, "service")]:
            parts.append(cell(x, y, 120, 38, kind if items else "grey", items[0] if items else "", dashed=not items))
        parts.append(label(xs[4], y + 24, effect, "note"))
    save(OUT / "ch01-queue-states.svg", 1000, 440,
         "The ready list, the dirty set and the processing set after each call: Add puts job-a in ready and "
         "dirty; Get moves it to processing; Adds during the reconcile mark it dirty only; Done makes it ready "
         "again; a second Get starts a reconcile that reads the latest spec.",
         "One name through the work queue",
         "5 edits during 1 reconcile lead to exactly 1 more reconcile, never 2 at once.", parts)


# Figure 1.8 -----------------------------------------------------------------

@figure
def edge_level():
    x0, step, w = 200, 104, 84
    edits = [2, 3, 4, 5, 6]
    parts = [label(32, 132, "spec edits", "tab")]
    for i, g in enumerate(edits):
        parts.append(cell(x0 + i * step, 110, w, 34, "client", f"gpus {g}", bold=True))

    parts.append(label(32, 210, "edge-triggered", "tab"))
    for i, g in enumerate(edits):
        kind = "good" if i == len(edits) - 1 else "danger"
        parts.append(cell(x0 + i * step, 188, w, 34, kind, f"act on {g}", cls="note"))
    parts.append(label(x0, 246, "1 run per event: 5 runs, and 4 of them act on a spec that is already replaced",
                       "note", fill=KINDS["danger"][0]))

    parts.append(label(32, 300, "level-triggered", "tab"))
    parts += [cell(x0, 278, 3 * step + w, 34, "good", "reconcile 1 reads the cache: gpus 2", cls="note"),
              cell(x0 + 4 * step, 278, w + 60, 34, "good", "reconcile 2: gpus 6", cls="note"),
              label(x0, 336, "1 run per state: 2 runs, each reads the current spec from the cache",
                    "note", fill=KINDS["good"][0])]
    parts += [line(x0 - 6, 368, x0 + 5 * step + 60, 368, MUTED, 1.4, arrow=True),
              label(x0 + 5 * step + 60, 388, "time", "note", "end")]
    save(OUT / "ch01-edge-level.svg", 1000, 410,
         "Five edits of a job's GPU count, to 2, 3, 4, 5 and 6. An edge-triggered handler runs once per edit, "
         "5 times, and 4 of those runs act on specs that were already replaced. A level-triggered reconcile runs "
         "twice and each time reads the current spec from the cache, first 2 and then 6.",
         "Reacting to events, and reacting to state",
         "The burst of edits from the run of the model, seen by 2 kinds of controller.", parts)


# Figure 1.9 -----------------------------------------------------------------

@figure
def shared_informer():
    parts = [card(32, 210, 200, 70, "service", "API server", ["1 watch on pods"], glyph="gear")]
    parts += [card(320, 150, 250, 190, "store", "Shared informer", ["reflector", "DeltaFIFO", "indexer (cache)",
                                                                     "1 copy of every pod"], glyph="stack"),
              wire([(232, 245), (320, 245)], label="events")]
    for i, name in enumerate(["GPU job controller", "Node health controller", "Quota controller"]):
        y = 110 + i * 110
        parts += [card(690, y, 280, 70, "client", name, ["own handler, own work queue"], glyph="gear"),
                  wire([(570, 245), (630, 245), (630, y + 35), (690, y + 35)])]
    save(OUT / "ch01-shared-informer.svg", 1000, 450,
         "One API server watch on pods feeds a shared informer holding the reflector, the DeltaFIFO and the "
         "indexer. Three controllers in the same process each register a handler and keep their own work queue.",
         "Controllers in one process share one watch and one cache",
         "SharedInformerFactory hands every controller the same informer for a given kind.", parts)


def marker(x, y, n):
    """A numbered marker, the same glyph the prose uses: a dark disc with a white digit."""
    return badge(x, y, n)


def legend_rows(x, y, rows, width=440):
    out = []
    for n, body in rows:
        out += [marker(x + 10, y - 4, n), label(x + 28, y, body, "note", fill=INK)]
        y += 24
    return out


# Structure of the API server ------------------------------------------------

@figure
def server_struct():
    parts = [
        f'  <rect x="330" y="96" width="638" height="300" rx="16" fill="#F3F1EA" stroke="#E4E0D4" stroke-width="1.2"/>',
        label(350, 122, "APISERVER: 4 FIELDS BEHIND 1 LOCK", "tab"),
        label(350, 156, "objects", "tab"),
        cell(450, 138, 150, 30, "client", "job-a  v10"), cell(610, 138, 150, 30, "service", "job-b  v8"),
        label(350, 202, "version", "tab"), cell(450, 184, 70, 30, "client", "10", strong=True),
        label(350, 248, "history", "tab"),
        cell(450, 230, 90, 30, "grey", "1-2 gone", cls="note", dashed=True),
    ]
    for i, v in enumerate(range(3, 11)):
        parts.append(cell(548 + i * 50, 230, 44, 30, "idle", str(v)))
    parts += [label(350, 294, "watches", "tab"),
              cell(450, 276, 200, 30, "good", "watch A: sent to 10", cls="note"),
              cell(660, 276, 200, 30, "good", "watch B: sent to 10", cls="note"),
              label(350, 348, "compacted", "tab"), cell(450, 330, 70, 30, "grey", "2"),
              label(530, 350, "a watch from below 2 gets 410 Gone", "note")]

    parts += [cell(32, 136, 250, 40, "client", "Update(job-a, read at v10)", cls="note"),
              line(282, 156, 330, 156, arrow=True), marker(306, 140, 1),
              cell(32, 300, 250, 40, "outside", "Watch(from 8)", cls="note"),
              line(282, 320, 330, 320, arrow=True), marker(306, 304, 4),
              marker(540, 199, 2), marker(954, 245, 3), marker(882, 291, 5)]
    rows = [(1, "Update compares the version the caller read with the stored one: equal, or 409 Conflict."),
            (2, "It increments the counter, stamps the object with the new value and stores it."),
            (3, "It appends 1 event to the history and sends it on every open watch."),
            (4, "Watch(from 8) checks 8 against the compaction point, then replays events 9 and 10,"),
            (5, "and registers the new watch under the same lock, so no event falls between the 2.")]
    parts += legend_rows(32, 436, rows)
    save(OUT / "ch01-server-struct.svg", 1000, 560,
         "The API server holds 4 fields behind 1 lock: objects (job-a at version 10, job-b at 8), the version counter 10, "
         "a history of events 3 to 10 with 1 and 2 compacted, and 2 open watches that have been sent everything up to 10. "
         "Update checks the version, increments the counter, stores the object, and publishes 1 event to the history and every "
         "watch. Watch from 8 checks the compaction point, replays 9 and 10, and registers itself under the same lock.",
         "Inside the model API server",
         "The state after 10 writes. Markers follow 1 Update and 1 Watch through it.", parts)


# Reconcile as a decision flow ------------------------------------------------

@figure
def reconcile_flow():
    xs, w, last = [32, 292, 552, 812], 190, 156
    mid = lambda i: xs[i] + w / 2
    parts = [
        card(xs[0], 100, w, 62, "store", "Get a name", ["from the queue"], glyph="stack"),
        card(xs[1], 100, w, 62, "service", "Read the cache", ["object by name"], glyph="search"),
        wire([(xs[0] + w, 131), (xs[1], 131)]),
        card(xs[2], 100, w, 62, "idle", "Object exists?", ["missing: deleted"]),
        wire([(xs[1] + w, 131), (xs[2], 131)]),
        card(xs[3], 100, last, 62, "danger", "Release", ["GPUs, then Done"]),
        wire([(xs[2] + w, 131), (xs[3], 131)], label="no"),
        card(xs[2], 222, w, 62, "idle", "Status = spec?", ["already handled"]),
        wire([(mid(2), 162), (mid(2), 222)], label="yes"),
        card(xs[3], 222, last, 62, "good", "Done", ["no write needed"]),
        wire([(xs[2] + w, 253), (xs[3], 253)], label="yes"),
        card(xs[2], 344, w, 62, "client", "Do the work", ["start a container"], glyph="gear"),
        wire([(mid(2), 284), (mid(2), 344)], label="no"),
        card(xs[1], 344, w, 62, "client", "Write status", ["with version read"]),
        wire([(xs[2], 375), (xs[1] + w, 375)]),
        card(xs[0], 344, w, 62, "danger", "409 Conflict", ["Add the name again"]),
        wire([(xs[1], 375), (xs[0] + w, 375)], label="409"),
        marker(xs[1] - 2, 100, 1), marker(xs[2] - 2, 100, 2), marker(xs[2] - 2, 222, 3), marker(xs[2] - 2, 344, 4), marker(xs[1] - 2, 344, 5),
    ]
    rows = [(1, "The worker holds the name; no other worker can take it."),
            (2, "The cache is exact up to the last event, so a missing object was deleted."),
            (3, "A status equal to the spec means an earlier reconcile already finished the work."),
            (4, "Starting a container stands for any action outside Kubernetes."),
            (5, "A write that fails returns the name to the queue; the next run reads the newer object.")]
    parts += legend_rows(32, 452, rows)
    save(OUT / "ch01-reconcile-flow.svg", 1000, 580,
         "The reconcile decision flow. Get a name from the work queue, read the object from the cache. If it does not exist, "
         "release its GPUs and finish. If its status equals its spec, finish. Otherwise do the work, then write the status with "
         "the version that was read. If the write fails with 409 Conflict, add the name to the queue again.",
         "One reconcile, from name to status",
         "Every path ends with Done. Only a conflict puts the name back in the queue.", parts)


for name in sys.argv[1:] or list(FIGURES):
    FIGURES[name]()
    print("  ch01-" + name)
