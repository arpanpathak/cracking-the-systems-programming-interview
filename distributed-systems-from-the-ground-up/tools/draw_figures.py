#!/usr/bin/env python3
"""The book's diagrams, written to src/figures/ as SVG.

    python3 tools/draw_figures.py                  # every figure
    python3 tools/draw_figures.py write-path       # some of them

Every figure is 480 units wide and runs from top to bottom, so that it fits
the width of a phone with its labels still readable. `figkit` refuses to write
a figure in which a label is wider than its box or a wire runs at an angle.
"""
import math
import sys
from pathlib import Path

from figkit import stacked, CARD, EDGE, GLYPHS, INK, KINDS, MUTED, WIRE, card, icon, must_fit, width_of, cylinder, legend, person, save, sheet, tag, text, wire, zone

OUT = Path(__file__).resolve().parent.parent / "src" / "figures"
WIDTH = 480
FIGURES = {}


def figure(draw):
    """Registers `draw` under its name, with underscores written as hyphens."""
    FIGURES[draw.__name__.replace("_", "-")] = draw

    return draw


def lines(x, y, rows, cls="note", anchor="start", lead=17):
    """Plain lines of text, one under the other."""

    return "\n".join(text(x, y + lead * row, body, cls, anchor) for row, body in enumerate(rows))


def box(x, y, w, h, fill, stroke=EDGE, rx=6, width=1.3):
    """A plain rectangle, for the pictures figkit has no part for."""

    return (f'  <rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" fill="{fill}"'
            f' stroke="{stroke}" stroke-width="{width}"/>')


def fields(x, y, w, kind, title, rows):
    """An entity: its name and one line for each field shown."""
    accent, tint = KINDS[kind]
    h = 34 + 19 * len(rows) + 8
    parts = [box(x, y, w, h, CARD, EDGE, 10), box(x, y, w, 28, tint, accent, 10),
             text(x + 12, y + 19, title, "mono strong")]
    parts += [text(x + 12, y + 50 + 19 * k, row, "mono").replace(
        "<text ", '<text textLength="%d" lengthAdjust="spacingAndGlyphs" ' % (w - 24), 1) if len(row) * 7.4 > w - 24
        else text(x + 12, y + 50 + 19 * k, row, "mono") for k, row in enumerate(rows)]

    return "\n".join(parts), h



def annotated(name, title, lede, rows, alt):
    """A piece of raw output explained line by line: each line in a box, with what it means under it."""
    parts, y = [], 96

    for raw, note, kind in rows:
        accent, tint = KINDS[kind]
        parts += [box(32, y, 416, 30, "#EEF2F7", EDGE, 6), text(44, y + 20, raw, "mono strong"),
                  box(32, y + 34, 5, 20 * len(note) - 2, accent, accent, 2)]
        parts += [text(46, y + 48 + 20 * k, line_, "sub") for k, line_ in enumerate(note)]
        y += 34 + 20 * len(note) + 18

    save(OUT / (name + ".svg"), WIDTH, y, alt, title, lede, parts)


def meter(x, y, w, label_, value, limit, unit, kind):
    """A horizontal gauge: how much of a limit is used."""
    accent, tint = KINDS[kind]
    filled = max(6, w * min(value / limit, 1.0))

    return "\n".join([text(x, y - 8, label_, "name"), text(x + w, y - 8, "%s of %s %s" % (value, limit, unit), "mono", "end"),
                      box(x, y, w, 22, CARD, EDGE, 6), box(x, y, filled, 22, tint, accent, 6)])


def chain(steps, x=80, w=320, y0=96, pitch=76, h=58):
    """Cards one under the other, joined by arrows. Returns the parts and the bottom edge."""
    parts = []

    for k, (kind, name, sub, glyph) in enumerate(steps):
        y = y0 + pitch * k
        parts.append(card(x, y, w, h, kind, name, [sub] if isinstance(sub, str) else sub, glyph=glyph))

        if k:
            parts.append(wire([(x + w / 2, y - (pitch - h)), (x + w / 2, y)]))

    return parts, y0 + pitch * len(steps)


def chip(x, y, w, body, kind, h=30):
    accent, tint = KINDS[kind]

    return "\n".join([box(x, y, w, h, tint, accent, 8), text(x + w / 2, y + h / 2 + 4, body, "pill", "middle", accent)])


def two_views(name, title, lede, left, right, rows, alt, note):
    """2 columns that describe the same thing from 2 sides, row by row."""
    parts = [card(32, 104, 200, 44, "client", left, []), card(248, 104, 200, 44, "outside", right, [])]

    for k, (what, a, b) in enumerate(rows):
        y = 162 + 58 * k
        parts += [box(32, y, 200, 46, CARD, EDGE, 8), box(248, y, 200, 46, CARD, EDGE, 8),
                  text(44, y + 18, what, "tab"), text(44, y + 36, a, "mono strong"),
                  text(260, y + 18, what, "tab"), text(260, y + 36, b, "mono strong")]

    y = 162 + 58 * len(rows) + 18
    parts.append(lines(32, y, note))
    save(OUT / (name + ".svg"), WIDTH, y + 17 * len(note) + 10, alt, title, lede, parts)


def link(x1, y1, x2, y2, kind="idle"):
    """A plain association line between an actor and a use case."""
    return f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{KINDS[kind][0]}" stroke-width="1.4" opacity="0.7"/>'


def node(x, y, w, name, role, kind, state=None):
    """A machine: a small card with its role as a pill."""
    return card(x, y, w, 48, kind, name, [role], pill=state)


def cross(cx, cy, r=13):
    red = KINDS["danger"][0]

    return (f'  <path d="M{cx - r},{cy - r} L{cx + r},{cy + r} M{cx + r},{cy - r} L{cx - r},{cy + r}" stroke="{red}"'
            f' stroke-width="4" stroke-linecap="round"/>')


def cells(x, y, labels, kind, w=44, h=30, hot=()):
    """A row of boxes with a label in each, such as the records of a log."""
    accent, tint = KINDS[kind]
    parts = []

    for k, body in enumerate(labels):
        on = k in hot
        parts += [box(x + (w + 4) * k, y, w, h, tint if not on else KINDS["danger"][1], accent if not on else KINDS["danger"][0], 5),
                  text(x + (w + 4) * k + w / 2, y + h / 2 + 4, body, "mono strong", "middle")]

    return "\n".join(parts)


# ------------------------------------------------- chapter 1: the system design

def fitted(x, y, body, cls, anchor, room, fill=None):
    """Text in the code face that is squeezed to `room` when a wide font would overflow it."""
    drawn = text(x, y, body, cls, anchor, fill)

    if len(body) * 7.4 > room:
        drawn = drawn.replace("<text ", '<text textLength="%d" lengthAdjust="spacingAndGlyphs" ' % room, 1)

    return drawn


def oval(cx, cy, w, body, detail, kind):
    """A use case: what the actor does, and the part of the system that serves it."""
    accent, tint = KINDS[kind]

    return "\n".join([f'  <rect x="{cx - w / 2}" y="{cy - 22}" width="{w}" height="44" rx="12" fill="{tint}" stroke="{accent}" stroke-width="1.4"/>',
                      text(cx, cy - 3, body, "pill", "middle", INK), fitted(cx, cy + 13, detail, "mono dim", "middle", w - 24)])


@figure
def use_cases():
    groups = [
        ("glasses", "Application", ["a service that keeps", "Its state in store"], "client", [
            ("store a value", "PUT /v1/keys/{key}"), ("read a value", "GET /v1/keys/{key}"), ("delete a key", "DELETE /v1/keys/{key}"),
            ("write only if unchanged", "PUT with If-Match"), ("list keys by prefix", "GET /v1/keys?prefix=")]),
        ("cap", "Operator", ["Changes set", "of machines"], "service", [
            ("add a node", "Ring gains its tokens"), ("remove a node", "Ring loses its tokens"), ("replace a failed node", "Copied from replicas")]),
        ("curly", "Monitoring", ["watches every", "node"], "store", [
            ("check health", "GET /healthz"), ("read metrics", "keys, last sequence")]),
    ]
    parts, y = [], 140
    shapes, top = [], 100

    for look, name, sub, kind, cases in groups:
        first, last = y, y + 52 * (len(cases) - 1)
        middle = (first + last) / 2
        parts += [person(42, middle - 46, look, 56), text(70, middle + 28, name, "name", "middle")]
        parts += [text(70, middle + 45 + 15 * k, line_, "sub", "middle") for k, line_ in enumerate(sub)]

        for k, (body, detail) in enumerate(cases):
            cy = first + 52 * k
            parts.append(link(104, middle - 18, 206, cy, kind))
            shapes.append(oval(318, cy, 224, body, detail, kind))

        y = last + 84

    bottom = y - 84 + 40
    parts = [zone(190, top, 258, bottom - top, "key-value store")] + parts + shapes
    save(OUT / "use-cases.svg", WIDTH, bottom + 24,
         "A use case diagram of the key-value store with 3 actors. The application, a service that keeps its state in the "
         "store, stores a value with PUT /v1/keys/{key}, reads a value with GET, deletes a key with DELETE, writes only if the "
         "value is unchanged with PUT and If-Match, and lists keys by prefix with GET /v1/keys. The operator, who changes the "
         "set of machines, adds a node, removes a node, and replaces a failed node. Monitoring, which watches every node, "
         "checks health with GET /healthz and reads metrics.",
         "Who uses store, and for what", "Actors on left, use cases on right.", parts)


@figure
def capacity():
    bar = lambda y, label_, value, share, kind: "\n".join([
        text(32, y - 8, label_, "name"), text(448, y - 8, value, "mono", "end"),
        box(32, y, 416, 20, CARD, EDGE, 6), box(32, y, max(8, 416 * share), 20, KINDS[kind][1], KINDS[kind][0], 6)])
    need = 32 + 416 * 60000 / 88800
    parts = [
        text(32, 104, "STORAGE", "tab"),
        bar(132, "1 copy: 1 billion keys x 1.1 KB", "1.1 TB", 1 / 3, "store"),
        bar(184, "3 copies of every key", "3.3 TB", 1.0, "store"),
        bar(236, "1 of 24 nodes", "138 GB", 138 / 3300, "store"),
        text(32, 292, "RECORDS STORED PER SECOND", "tab"),
        bar(320, "1 node, 1 fsync per record", "185", 185 / 88800, "danger"),
        bar(372, "1 node, 20 records per fsync", "3700", 3700 / 88800, "service"),
        bar(424, "24 nodes", "88800", 1.0, "good"),
        f'  <line x1="{need:.1f}" y1="414" x2="{need:.1f}" y2="452" stroke="{INK}" stroke-width="2" stroke-dasharray="4 3"/>',
        text(need, 468, "required: 60000", "pill", "middle", INK),
        lines(32, 498, ["20000 writes per second are stored on 3 nodes each: 60000.", "185 is measured in chapter 2 on an NVMe disk."], "sub"),
    ]
    save(OUT / "capacity.svg", WIDTH, 532,
         "The capacity estimate as bars. Storage: 1 copy of 1 billion keys at 1.1 KB each is 1.1 TB, 3 copies are 3.3 TB, and "
         "each of 24 nodes holds 138 GB. Records stored per second: 1 node that calls fsync for every record stores 185, 1 "
         "node that groups 20 records per fsync stores 3700, and 24 nodes store 88800, against a requirement of 60000, which "
         "is 20000 writes per second stored on 3 nodes each.",
         "Size of system", "Requirements expressed as disks and nodes.", parts)


@figure
def entities():
    a, ha = fields(32, 96, 186, "client", "Entry", ["key      string", "value    bytes", "version  u64"])
    b, hb = fields(262, 96, 186, "store", "Record", ["sequence  u64", "kind      put | delete", "key       string", "value     bytes"])
    c, hc = fields(32, 262, 186, "service", "Shard", ["first_token  u64", "last_token   u64", "term         u64", "leader       Node", "followers    Node[]"])
    d, hd = fields(262, 262, 186, "outside", "Node", ["id       string", "address  host:port", "tokens   u64[]", "state    up | down"])
    e, he = fields(262, 262 + hd + 16, 186, "model", "Ring", ["version  u64", "nodes    Node[]", "shards   Shard[]"])
    bottom = 262 + hd + 16 + he
    parts = [a, b, c, d, e,
             wire([(218, 130), (262, 130)], arrow=False),
             wire([(125, 96 + ha), (125, 262)]), wire([(218, 300), (262, 300)]), wire([(262, bottom - 40), (125, bottom - 40), (125, 262 + hc)]),
             lines(32, bottom + 30, ["An Entry is current value of a key. Its version is the", "Sequence of Record that last wrote it.",
                                     "A Shard is a range of ring, held on 3 Nodes.", "Ring lists every Node with its tokens, and every Shard."], "sub")]
    save(OUT / "entities.svg", WIDTH, bottom + 30 + 17 * 4,
         "The core entities. An Entry has a key, a value and a version. A Record has a sequence, a kind that is put or delete, "
         "a key and a value, and the version of an Entry is the sequence of the Record that last wrote it. A Shard has a first "
         "and a last token, a term, a leader Node and follower Nodes. A Node has an id, an address, its tokens and a state. "
         "Ring has a version, list of Nodes and list of Shards.",
         "Core entities", "What system stores, and what it stores it on.", parts)


def on_ring(cx, cy, r, position_):
    angle = 2 * math.pi * position_ / 100 - math.pi / 2

    return cx + r * math.cos(angle), cy + r * math.sin(angle)


def arc(cx, cy, r, start, end, colour, width=10):
    (x1, y1), (x2, y2) = on_ring(cx, cy, r, start), on_ring(cx, cy, r, end)
    large = 1 if (end - start) % 100 > 50 else 0

    return f'  <path d="M{x1:.1f},{y1:.1f} A{r},{r} 0 {large} 1 {x2:.1f},{y2:.1f}" fill="none" stroke="{colour}" stroke-width="{width}" stroke-linecap="butt" opacity="0.55"/>'


def token(cx, cy, r, position_, name, kind, label_=None):
    accent, tint = KINDS[kind]
    x, y = on_ring(cx, cy, r, position_)
    lx, ly = on_ring(cx, cy, r + 30, position_)

    return "\n".join([f'  <circle cx="{x:.1f}" cy="{y:.1f}" r="13" fill="{tint}" stroke="{accent}" stroke-width="2"/>',
                      text(x, y + 4.5, name, "pill", "middle", accent), text(lx, ly + 4, label_ or str(position_), "mono dim", "middle")])


def key_mark(cx, cy, r, position_, name):
    x, y = on_ring(cx, cy, r, position_)
    ix, iy = on_ring(cx, cy, r - 40, position_)

    return "\n".join([f'  <rect x="{x - 6:.1f}" y="{y - 6:.1f}" width="12" height="12" fill="{INK}" transform="rotate(45 {x:.1f} {y:.1f})"/>',
                      text(ix, iy + 4, name, "pill", "middle", INK)])


def ring_picture(cx, cy, r, tokens, arcs=(), keys=()):
    parts = [f'  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{EDGE}" stroke-width="10"/>']
    parts += [arc(cx, cy, r, start, end, KINDS[kind][0]) for start, end, kind in arcs]
    parts += [token(cx, cy, r, position_, name, kind) for position_, name, kind in tokens]
    parts += [key_mark(cx, cy, r, position_, name) for position_, name in keys]

    return parts


def badge(x, y, number):
    """The number of a step, on a dark disc. The same number appears in the list under the picture."""
    return "\n".join([f'  <circle cx="{x}" cy="{y}" r="10" fill="{INK}" stroke="#FFFFFF" stroke-width="2"/>',
                      text(x, y + 4, str(number), "pill", "middle", "#FFFFFF")])


def legend_steps(y, rows, start=1, pitch=24):
    """The steps of a picture, one line each, with the badge that marks the step in the picture."""
    parts = []

    for k, body in enumerate(rows):
        must_fit(body, 384)
        parts += [badge(44, y + pitch * k, start + k), text(64, y + pitch * k + 4, body, "note", fill=INK)]

    return "\n".join(parts), y + pitch * len(rows)


def step_rows(y, rows, start=1):
    """Numbered steps as rows: a number, what happens, and a detail."""
    parts = []

    for k, (kind, body, sub) in enumerate(rows):
        top = y + 54 * k
        parts += [box(32, top, 416, 46, CARD, EDGE, 8), box(32, top, 34, 46, KINDS[kind][1], KINDS[kind][0], 8),
                  text(49, top + 28, str(start + k), "mono strong", "middle"), text(78, top + 20, body, "name"), text(78, top + 37, sub, "sub")]
        must_fit(body, 360, 14, bold=True)
        must_fit(sub, 360)

    return "\n".join(parts), y + 54 * len(rows)


def server(x, y, w, name, sub, mark, kind="idle"):
    """A component: a paper card with a symbol for its role, a name and 1 line about what it does."""
    return card(x, y, w, 50, kind, name, [sub], glyph=mark)


def disk(x, y, w, body):
    """A disk: a small light label under the machine that owns it."""
    accent, tint = KINDS["store"]
    must_fit(body, w - 20)

    return "\n".join([box(x, y, w, 30, tint, accent, 8), text(x + w / 2, y + 19, body, "pill", "middle", accent)])


@figure
def system_overview():
    """The whole system, drawn wide: a request travels from left to right."""
    wide = 1140
    mini = "".join(f'<rect x="{844 + 46 * k}" y="412" width="38" height="16" rx="4" fill="#F1F4F7" stroke="#C9D3DF" stroke-width="1"/>'
                   f'<circle cx="{874 + 46 * k}" cy="420" r="2.2" fill="#5FD38D"/>' for k in range(5))
    parts = [
        # the path of a request, left to right
        server(40, 232, 190, "Applications", "HTTP clients", "laptop", "client"),
        wire([(230, 257), (290, 257)]), badge(260, 239, 1),
        server(290, 232, 200, "Load balancer", "spreads requests", "swap", "idle"),
        wire([(490, 257), (550, 257)]), badge(520, 239, 2),

        zone(550, 150, 220, 224, "routers"),
        server(564, 172, 192, "router 1", "stateless", "curve", "client"),
        server(564, 236, 192, "router 2", "stateless", "curve", "client"),
        server(564, 300, 192, "router 3", "stateless", "curve", "client"),
        wire([(770, 197), (844, 197)]), badge(807, 179, 3),

        zone(830, 150, 270, 320, "storage nodes: 24 machines"),
        server(844, 172, 222, "node-10", "leader, log on disk", "chip", "store"), badge(868, 240, 4),
        server(844, 258, 222, "node-1", "follower, log on disk", "chip", "service"),
        server(844, 334, 222, "node-6", "follower, log on disk", "chip", "service"),
        wire([(930, 222), (930, 258)]), badge(952, 240, 5),
        wire([(1066, 197), (1086, 197), (1086, 359), (1066, 359)]), badge(1086, 278, 5),
        "  " + mini, text(844, 452, "21 more nodes hold the other shards", "sub"),

        # around the path
        server(564, 64, 192, "Coordinator", "holds the ring", "stack", "model"),
        wire([(660, 114), (660, 150)], kind="idle"), badge(684, 132, 0),
        server(564, 412, 192, "Monitoring", "health, metrics", "eye", "danger"),
        wire([(756, 437), (830, 437)], kind="idle"),

        text(40, 520, "THE PATH OF A WRITE", "tab"),
    ]
    steps = [
        "Routers hold a copy of the ring, sent by the coordinator.",
        "An application sends PUT /v1/keys/user-1.",
        "The load balancer passes it to a healthy router.",
        "The router hashes the key and finds the leader, node-10.",
        "node-10 stores the record in its log, on disk.",
        "node-10 sends the record to node-1 and node-6.",
        "When 1 of them has stored it, node-10 answers 201 Created.",
        "The answer returns the way the request came.",
    ]

    for number, body in enumerate(steps):
        x, y = (52, 548 + 26 * number) if number < 4 else (600, 548 + 26 * (number - 4))
        parts += [badge(x, y, number), text(x + 20, y + 4, body, "note", fill=INK)]

    save(OUT / "system-overview.svg", wide, 668,
         "The high-level design of the key-value store, drawn from left to right, with the path of a write numbered. "
         "Applications send requests to a load balancer, which passes each request to 1 of 3 routers. The routers have no "
         "data of their own. They hold a copy of the ring, which the coordinator, drawn above them, sends them. On the right "
         "are 24 storage nodes. For the key user-1, node-10 is the leader and node-1 and node-6 are the followers, and each "
         "has a log on disk. A monitoring system, drawn below the routers, reads the health and the metrics of every node. "
         "Step 0: routers hold a copy of the ring, sent by the coordinator. Step 1: an application sends PUT /v1/keys/user-1. "
         "Step 2: the load balancer passes it to a healthy router. Step 3: the router hashes the key and finds the leader, "
         "node-10. Step 4: node-10 stores the record in its log, on disk. Step 5: node-10 sends the record to node-1 and "
         "node-6. Step 6: when 1 of them has stored it, node-10 answers 201 Created. Step 7: the answer returns the way the "
         "request came.",
         "The high-level design", "A request travels from left to right. Follow the numbers from 0 to 7.", parts)


@figure
def ring():
    parts = ring_picture(240, 250, 126, [(12, "A", "client"), (37, "B", "store"), (62, "C", "service"), (87, "D", "outside")],
                         arcs=[(20, 37, "store")], keys=[(20, "user-1")])
    (kx, ky), (bx, by), (cx_, cy_), (dx, dy) = (on_ring(240, 232, 104, p) for p in (20, 37, 62, 87))
    out = lambda position_, far: on_ring(240, 250, 126 + far, position_)
    parts += [badge(*out(20, 26), 1), badge(*out(28.5, 24), 2), badge(*out(37, 58), 3), badge(*out(62, 58), 4), badge(*out(87, 58), 4),
              text(240, 246, "positions", "sub", "middle"), text(240, 263, "0 to 99", "sub", "middle")]
    steps, bottom = legend_steps(452, [
        "Hash key. user-1 lands on position 20.",
        "Walk clockwise from 20 to the next token.",
        "The next token is 37. It belongs to B, so B owns key.",
        "The next 2 nodes, C and D, hold the other copies.",
    ])
    parts += [steps, lines(32, bottom + 12, ["A token is a position that a node owns. B owns every position", "From 13 to 37, because 12 is token before it."], "sub")]
    save(OUT / "ring.svg", WIDTH, bottom + 50,
         "A hash ring with positions 0 to 99. Node A has the token 12, B has 37, C has 62 and D has 87. Step 1: hash the key, "
         "and user-1 lands on position 20. Step 2: walk clockwise from 20 to the next token. Step 3: the next token is 37, "
         "which belongs to B, so B owns the key. Step 4: the next 2 different nodes, C and D, hold the other copies. B owns "
         "Every position from 13 to 37, because 12 is token before it.",
         "Finding node of a key", "Follow numbers from 1 to 4.", parts)


@figure
def ring_route():
    rows, bottom = step_rows(96, [
        ("model", "Coordinator holds ring version 7", "Tokens of every node, and each shard's leader"),
        ("client", "Each router keeps a copy and watches it", "Coordinator sends version 8 when it exists"),
        ("client", "Router hashes key of a request", "user-1 hashes to position 0x7c76..."),
        ("client", "It finds the next token in its sorted list", "a binary search over 6144 tokens: 13 steps"),
        ("store", "It sends request to shard's leader", "With ring version it used: 7"),
        ("store", "Node compares ring versions", "Same version: It serves request"),
        ("danger", "A node refuses a router with an old ring", "It answers: Wrong node, ring is at version 8"),
        ("client", "Router gets version 8 and sends again", "Client sees 1 slower request and no error"),
    ], start=0)
    parts = [rows, lines(32, bottom + 18, ["No request passes through coordinator. A router answers", "Question which node from its own memory."], "sub")]
    save(OUT / "ring-route.svg", WIDTH, bottom + 56,
         "How the ring is used for a request, in 8 steps numbered from 0. Step 0: the coordinator holds the ring at version 7, with the "
         "tokens of every node and the leader of each shard. Step 1: each router keeps a copy and watches the coordinator, which sends "
         "version 8 as soon as it exists. Step 2: a request arrives and the router hashes the key. Step 3: it searches its "
         "sorted tokens for the next one, a binary search of 13 steps over 6144 tokens. Step 4: it sends the request to that "
         "shard's leader with the ring version it used. Step 5: the node compares versions and serves the request if they are "
         "the same. Step 6: if the router's ring is old, the node refuses and answers that the ring is at version 8. Step 7: "
         "the router fetches version 8 and sends again, and the client sees 1 slower request and no error.",
         "How a router uses ring", "Follow numbers from 0 to 7.", parts)


@figure
def ring_join():
    rows, bottom = step_rows(96, [
        ("service", "Operator starts node-25", "It is given coordinator's address"),
        ("model", "node-25 registers as joining", "its 256 tokens are computed from its name"),
        ("model", "Coordinator publishes ring version 8", "node-25 owns no keys yet"),
        ("store", "Owners copy their ranges to node-25", "an owner still serves its range meanwhile"),
        ("store", "node-25 confirms that a range is complete", "Its log holds every record of range"),
        ("model", "Coordinator assigns it range", "ring version 9: routers send its keys to node-25"),
        ("idle", "Old owner deletes its copy", "steps 3 to 6 repeat for every range"),
    ])
    parts = [rows, lines(32, bottom + 18, ["A range changes owner only after its data has arrived, so every", "key is readable during the whole procedure."], "sub")]
    save(OUT / "ring-join.svg", WIDTH, bottom + 56,
         "How a node joins the ring, in 7 steps. Step 1: the operator starts node-25 and gives it the address of the coordinator. Step 2: "
         "node-25 registers in the coordinator as joining, with 256 tokens computed from its name. Step 3: the coordinator publishes ring version "
         "8, in which node-25 owns no keys yet. Step 4: each current owner copies 1 range to node-25 and still serves the "
         "range meanwhile. Step 5: node-25 confirms that a range is complete. Step 6: the coordinator moves that range to node-25 in "
         "version 9, and routers send its keys to node-25 from now on. Step 7: the old owner deletes its copy of the range, "
         "and steps 3 to 6 repeat for every range.",
         "A node joins a running cluster", "Follow numbers from 1 to 7.", parts)


@figure
def gossip():
    def round_(y, title, knows):
        out = [text(32, y, title, "tab")]

        for k in range(8):
            on = k in knows
            out += [box(32 + 52 * k, y + 10, 44, 32, KINDS["good"][1] if on else CARD, KINDS["good"][0] if on else EDGE, 8),
                    text(54 + 52 * k, y + 31, "v8" if on else "v7", "mono strong" if on else "mono dim", "middle")]

        return out

    parts = [*round_(104, "START: 1 NODE OF 8 HAS RING VERSION 8", {0}), *round_(176, "AFTER ROUND 1: 2 NODES", {0, 5}),
             *round_(248, "AFTER ROUND 2: 4 NODES", {0, 2, 5, 6}), *round_(320, "AFTER ROUND 3: ALL 8 NODES", set(range(8))),
             lines(32, 392, ["Once per second, every node picks another node at random and", "2 compare ring versions. One with older ring takes",
                             "newer. Number of nodes that know doubles each round,", "so 24 nodes need about 5 rounds and 1000 nodes about 10."], "sub")]
    save(OUT / "gossip.svg", WIDTH, 462,
         "How a gossip protocol spreads a new ring among 8 nodes without a coordinator. At the start, 1 node has ring version "
         "8 and 7 have version 7. After round 1, 2 nodes have version 8. After round 2, 4 nodes. After round 3, all 8. Once "
         "per second, every node picks another node at random and the 2 compare ring versions, and the one with the older "
         "ring takes the newer. The number of nodes that know doubles each round, so 24 nodes need about 5 rounds and 1000 "
         "nodes about 10.",
         "Gossip: Ring without a coordinator", "Each box is a node and shows ring version it holds.", parts)


@figure
def failover():
    rows, bottom = step_rows(96, [
        ("danger", "node-10, a leader, stops", "its followers stop receiving heartbeats"),
        ("service", "After 1 second, node-1 stands for election", "It raises term from 4 to 5"),
        ("service", "node-6 votes for node-1", "its own log is no longer than node-1's"),
        ("model", "Coordinator records new leader", "term 5, leader node-1: a new ring version"),
        ("client", "Routers receive new ring", "Writes to shard succeed again"),
        ("idle", "node-10 returns and becomes a follower", "term 5 is newer than its own term 4"),
    ])
    parts = [rows, lines(32, bottom + 18, ["Writes to this shard fail between steps 1 and 5.", "Shards whose leader is on another node are not affected."], "sub")]
    save(OUT / "failover.svg", WIDTH, bottom + 56,
         "What happens when a leader fails, in 6 steps. Step 1: node-10, a leader, stops, and its followers stop receiving "
         "heartbeats. Step 2: after 1 second, node-1 stands for election and raises the term from 4 to 5. Step 3: node-6 votes "
         "for node-1, because its own log is no longer than node-1's. Step 4: the coordinator records the new leader, term 5, leader "
         "node-1, as a new ring version. Step 5: routers receive the new ring, and writes to the shard succeed again. Step 6: "
         "node-10 returns and becomes a follower, because term 5 is newer than its own term 4.",
         "A leader fails", "Follow numbers from 1 to 6.", parts)


@figure
def ring_add():
    parts = ring_picture(240, 262, 126, [(12, "A", "client"), (37, "B", "store"), (62, "C", "service"), (87, "D", "outside"), (50, "E", "danger")],
                         arcs=[(37, 50, "danger")])
    parts += [text(240, 258, "E joins", "sub", "middle"), text(240, 275, "at 50", "sub", "middle"),
              lines(32, 468, ["Before E joined, positions 38 to 62 belonged to C.", "E takes positions 38 to 50, shaded arc.",
                              "13 of 100 positions change owner, all of them from C to E.", "Keys on A, B and D, and keys at 51 to 62 on C, stay in place.",
                              "With hash mod N, going from 4 to 5 nodes moves 80 of 100."], "sub")]
    save(OUT / "ring-add.svg", WIDTH, 558,
         "The same ring after node E joins with the token 50. Before, positions 38 to 62 belonged to C. E takes positions 38 "
         "to 50. 13 of the 100 positions change owner, all of them from C to E, and the keys on A, B and D and the keys at 51 "
         "to 62 on C stay in place. With hash mod N, going from 4 to 5 nodes moves 80 of 100.",
         "A node joins ring", "Only arc before new token changes owner.", parts)


@figure
def ring_spread():
    scale = lambda share: 32 + 416 * share / 12
    rows = [("1 token per node", 0.16, 11.26, "danger"), ("8 tokens per node", 1.42, 7.83, "store"),
            ("64 tokens per node", 3.35, 5.07, "service"), ("256 tokens per node", 3.86, 4.73, "good")]
    parts = [text(32, 104, "SHARE OF THE KEYS PER NODE, LOWEST TO HIGHEST", "tab")]
    ideal = scale(100 / 24)

    for k, (name, low, high, kind) in enumerate(rows):
        y = 134 + 58 * k
        parts += [text(32, y - 8, name, "name"), text(448, y - 8, "%.2f%% to %.2f%%" % (low, high), "mono", "end"),
                  box(32, y, 416, 20, CARD, EDGE, 6), box(scale(low), y, max(6, scale(high) - scale(low)), 20, KINDS[kind][1], KINDS[kind][0], 6),
                  f'  <line x1="{ideal:.1f}" y1="{y - 3}" x2="{ideal:.1f}" y2="{y + 23}" stroke="{INK}" stroke-width="2"/>']

    parts += [text(ideal, 354, "ideal: 4.17%", "pill", "middle", INK), text(32, 354, "0%", "mono dim"), text(448, 354, "12%", "mono dim", "end"),
              lines(32, 388, ["100000 keys on 24 nodes, measured by ringsim.", "With 1 token, fullest node holds 70 times as many keys as",
                              "emptiest. With 256 tokens ratio is 1.2."], "sub")]
    save(OUT / "ring-spread.svg", WIDTH, 444,
         "The share of 100000 keys held by the emptiest and the fullest of 24 nodes, for 4 numbers of tokens per node, against "
         "an ideal share of 4.17 percent. With 1 token per node the shares run from 0.16 to 11.26 percent. With 8 tokens, from "
         "1.42 to 7.83. With 64 tokens, from 3.35 to 5.07. With 256 tokens, from 3.86 to 4.73.",
         "Virtual nodes even out load", "More tokens per node bring each node closer to ideal.", parts)


@figure
def consistency_models():
    def model(y, kind, name, answer, why):
        return "\n".join([box(32, y, 416, 74, CARD, EDGE, 10), box(32, y, 8, 74, KINDS[kind][0], KINDS[kind][0], 4),
                          text(52, y + 24, name, "name"), text(436, y + 24, answer, "mono strong", "end"),
                          text(52, y + 45, why[0], "sub"), text(52, y + 62, why[1], "sub")])

    parts = [
        text(32, 104, "WHAT HAPPENED", "tab"),
        step_rows(114, [
            ("store", "A client writes basket = tea, milk", "the write is acknowledged"),
            ("idle", "Replica 3 has not received the write yet", "it still holds basket = tea"),
            ("client", "Another client reads the basket", "which answer may it get?"),
        ])[0],
        text(32, 300, "THE ANSWER UNDER EACH MODEL", "tab"),
        model(310, "good", "Strong", "always tea, milk", ["Every read sees the latest acknowledged write.", "A read may have to wait, or fail during a partition."]),
        model(392, "danger", "Eventual", "tea, or tea, milk", ["Any replica may answer with what it has.", "Replicas agree some time after writes stop."]),
        model(474, "store", "Tunable", "set per request", ["Each request names how many replicas must answer.", "More replicas: fresher answers, slower and less available."]),
        lines(32, 578, ["This chapter's store is strongly consistent."], "sub"),
    ]
    save(OUT / "consistency-models.svg", WIDTH, 600,
         "The 3 consistency models, shown with 1 situation. A client writes basket = tea, milk, and the write is "
         "acknowledged. Replica 3 has not received the write yet and still holds basket = tea. Another client reads the "
         "basket. Under strong consistency the answer is always tea, milk: every read sees the latest acknowledged write, and "
         "a read may have to wait or fail during a partition. Under eventual consistency the answer is tea or tea, milk: any "
         "replica may answer with what it has, and replicas agree some time after writes stop. Under tunable consistency the "
         "answer depends on the request, which names how many replicas must answer. This chapter's store is strongly "
         "consistent.",
         "Strong, eventual, tunable", "1 situation, and the answer a reader gets under each model.", parts)


@figure
def api_resources():
    row = lambda y, method, path, does, kind: "\n".join([
        box(32, y, 416, 46, CARD, EDGE, 8), chip(42, y + 9, 66, method, kind, 28),
        text(120, y + 20, path, "mono strong"), text(120, y + 37, does, "sub")])
    parts = [
        text(32, 104, "ONE KEY", "tab"),
        row(114, "PUT", "/v1/keys/{key}", "Create or replace value: 201 or 204", "store"),
        row(166, "GET", "/v1/keys/{key}", "Read value and its version: 200", "client"),
        row(218, "DELETE", "/v1/keys/{key}", "Remove key: 204", "danger"),
        text(32, 292, "THE COLLECTION", "tab"),
        row(302, "GET", "/v1/keys?prefix=&after=&limit=", "one page of keys, in order: 200", "client"),
        text(32, 376, "THE NODE", "tab"),
        row(386, "GET", "/healthz", "whether this node can serve: 200", "service"),
        lines(32, 458, ["A key is a resource with its own URL. Method says what", "Happens to it, and status code says what happened."], "sub"),
    ]
    save(OUT / "api-resources.svg", WIDTH, 492,
         "The resources of the API. For one key, at /v1/keys/{key}: PUT creates or replaces the value and answers 201 or 204, "
         "GET reads the value and its version and answers 200, and DELETE removes the key and answers 204. For the collection, "
         "GET /v1/keys with prefix, after and limit returns one page of keys in order. For the node, GET /healthz says whether "
         "Node can serve.",
         "Resources and their methods", "5 operations on 3 resources.", parts)


@figure
def request_annotated():
    annotated("request-annotated", "Reading a conditional write", "A request, and 2 answers it can receive.", [
        ("PUT /v1/keys/user-1 HTTP/1.1", ["PUT names the whole new state of resource,", "so sending it twice leaves the same result"], "store"),
        ('If-Match: "1"', ["condition: Write only if key is still", "At version 1, version this client read"], "client"),
        ("HTTP/1.1 204 No Content", ["Value was replaced, and there is no body"], "good"),
        ('etag: "2"', ["New version, to use in the next If-Match"], "good"),
        ("HTTP/1.1 412 Precondition Failed", ["another client wrote first: nothing was changed.", "Read key again and decide what to do"], "danger"),
    ], "A conditional write explained line by line. PUT /v1/keys/user-1 names the whole new state of the resource, so sending "
       "it twice leaves the same result. The header If-Match with version 1 makes the write happen only if the key is still at "
       "the version this client read. The answer 204 No Content means the value was replaced, and the etag header carries the "
       "new version 2. The answer 412 Precondition Failed means another client wrote first and nothing was changed.")


@figure
def replicated_write():
    step = lambda y, n, body, sub, kind: "\n".join([
        box(32, y, 416, 46, CARD, EDGE, 8), box(32, y, 34, 46, KINDS[kind][1], KINDS[kind][0], 8),
        text(49, y + 28, n, "mono strong", "middle"), text(78, y + 20, body, "name"), text(78, y + 37, sub, "sub")])
    parts = [
        node(32, 96, 128, "node-10", "leader", "store"), node(176, 96, 128, "node-1", "follower", "service"), node(320, 96, 128, "node-6", "slow follower", "service"),
        cells(40, 156, ["41", "42"], "store", 52), cells(184, 156, ["41", "42"], "service", 52), cells(328, 156, ["41"], "service", 52),
        text(32, 216, "RECORD 42, STEP BY STEP", "tab"),
        step(226, "1", "Leader appends record 42 to its log", "and waits for its own disk", "store"),
        step(278, "2", "It sends record 42 to both followers", "in parallel", "store"),
        step(330, "3", "node-1 appends it, waits for its disk, answers", "node-6 has not answered yet", "service"),
        step(382, "4", "2 of 3 logs hold record 42: it is committed", "Leader applies it and answers client", "good"),
        step(434, "5", "node-6 receives it later", "Client did not wait for slowest node", "idle"),
    ]
    save(OUT / "replicated-write.svg", WIDTH, 504,
         "A write to a shard of 3 replicas. The leader on node-10 and the follower on node-1 hold records 41 and 42, and the "
         "slow follower on node-6 holds only record 41. Step 1: the leader appends record 42 to its log and waits for its "
         "disk. Step 2: it sends the record to both followers in parallel. Step 3: node-1 appends it, waits for its disk and "
         "answers. Step 4: 2 of 3 logs hold the record, so it is committed, and the leader applies it and answers the client. "
         "Step 5: node-6 receives it later.",
         "One write, on 3 nodes", "Client is answered when 2 of 3 logs hold record.", parts)


@figure
def majority():
    def trio(y, title, states, note):
        out = [text(32, y, title, "tab")]

        for k, (name, state) in enumerate(zip(["node-10", "node-1", "node-6"], states)):
            x, kind = 32 + 144 * k, {"lost": "idle", "has record 42": "good"}.get(state, "store")
            out += [box(x, y + 10, 128, 44, KINDS[kind][1], KINDS[kind][0], 8),
                    text(x + 64, y + 30, name, "name", "middle"), text(x + 64, y + 46, state, "sub", "middle")]

            if state == "lost":
                out.append(cross(x + 110, y + 24, 7))

        return out + [text(32, y + 74, note, "sub")]

    parts = [*trio(104, "RECORD 42 IS ACKNOWLEDGED", ["has record 42", "has record 42", "ends at 41"], "node-6 was slow. 2 of 3 logs hold record, which is enough."),
             *trio(214, "THEN NODE 3 IS LOST", ["lost", "has record 42", "ends at 41"], "node-1 still has record 42."),
             *trio(324, "NODES 1 AND 6 ELECT A LEADER", ["lost", "has record 42", "ends at 41"], "node-1 has longer log, so it becomes leader."),
             lines(32, 432, ["A write needs 2 of 3 nodes and an election needs 2 of 3 nodes.", "2 groups of 2 out of 3 always share a node, so every election",
                              "includes a node that holds every acknowledged record."], "sub")]
    save(OUT / "majority.svg", WIDTH, 484,
         "Why a majority is enough. Record 42 was written to node-10 and node-1 while node-6 was slow and its log ends at "
         "record 41, and the write was acknowledged. Then node-10 is lost, and node-1 still has the record. node-1 and node-6 elect "
         "a leader, and node-1 has the longer log, so it becomes the leader. A write needs 2 of 3 nodes and an election needs 2 of 3 nodes, and 2 groups of 2 out of 3 always "
         "share a node, so every election includes a node that holds every acknowledged record.",
         "Why 2 of 3 is enough", "Nodes that write and nodes that elect overlap.", parts)


@figure
def partition():
    parts = [
        zone(32, 104, 196, 170, "this side: 1 of 3"), zone(252, 104, 196, 170, "this side: 2 of 3"),
        node(44, 130, 172, "node-10", "leader of term 4", "store"),
        node(264, 130, 172, "node-1", "leader of term 5", "service"), node(264, 190, 172, "node-6", "follower", "service"),
        f'  <line x1="240" y1="96" x2="240" y2="282" stroke="{KINDS["danger"][0]}" stroke-width="3" stroke-dasharray="7 6"/>',
        text(44, 204, "a write reaches 1 log", "sub"), text(44, 222, "it is never committed", "sub"), text(44, 240, "Client gets an error", "sub"),
        text(264, 258, "writes are committed", "sub"),
        lines(32, 312, ["Network splits, and node-10 cannot reach the others.", "node-10 still believes it leads, and accepts a write. It cannot",
                         "Copy record to a second node, so it cannot acknowledge it.", "Side with 2 nodes elects node-1 and continues.",
                         "At most 1 side can hold 2 of 3 nodes, so at most 1 side accepts", "writes. A side with 1 node refuses writes: it gives up availability",
                         "To keep data consistent."], "sub"),
    ]
    save(OUT / "partition.svg", WIDTH, 442,
         "A network partition splits a shard. On one side is node-10 alone, the leader of term 4. On the other side are nodes 1 "
         "and 11. A write that reaches node-10 is in 1 log, is never committed, and the client gets an error. The side with 2 "
         "nodes elects node-1 as leader of term 5 and commits writes. At most 1 side can hold 2 of 3 nodes, so at most 1 side "
         "accepts writes, and the side with 1 node refuses writes: it gives up availability to keep the data consistent.",
         "Network splits", "Side with a majority continues. The other side stops.", parts)


# -------------------------------------------- chapter 2: the storage node

@figure
def node_inside():
    parts = [
        card(100, 96, 280, 52, "client", "HTTP handler", ["key, headers, body"], glyph="listen"),
        wire([(240, 148), (240, 176)]),
        card(100, 176, 280, 52, "service", "Store", ["Checks version condition"], glyph="lock"),
        wire([(170, 228), (170, 262)], label="1"), wire([(310, 228), (310, 262)], label="2"),
        zone(32, 262, 200, 150, "on disk"), zone(248, 262, 200, 150, "in memory"),
        cylinder(52, 290, 160, 74, "store", "log", ["every change in order"]),
        card(262, 290, 172, 74, "model", "map", ["key to entry,", "sorted by key"]),
        text(132, 392, "survives a crash", "pill", "middle", KINDS["store"][0]), text(348, 392, "rebuilt at start", "pill", "middle", KINDS["model"][0]),
        lines(32, 444, ["A write goes to log first and to map second.", "A read uses map only.", "After a restart map is empty, and log fills it again."], "sub"),
    ]
    save(OUT / "node-inside.svg", WIDTH, 502,
         "The inside of a storage node. The HTTP handler reads the key, the headers and the body, and calls the store, which "
         "checks the condition on the version. A write goes first to the log on disk, which holds every change in order and "
         "survives a crash, and second to the map in memory, which goes from key to entry, is sorted by key, and is rebuilt at "
         "start. A read uses map only.",
         "Inside a storage node", "A log on disk, and a map in memory that is built from it.", parts)


@figure
def record_layout():
    def field(x, y, w, value, name, kind):
        accent, tint = KINDS[kind]

        return "\n".join([box(x, y, w, 34, tint, accent, 5), text(x + w / 2, y + 21, value, "mono strong", "middle"),
                          text(x + w / 2, y + 52, name, "pill", "middle", accent)])

    parts = [
        text(32, 104, "THE FRAME: 8 BYTES", "tab"),
        field(32, 114, 204, "14 00 00 00", "length", "client"), field(244, 114, 204, "8d d3 da 1d", "checksum", "danger"),
        text(32, 204, "THE PAYLOAD: 20 BYTES", "tab"),
        field(32, 214, 196, "01 00 00 00 00 00 00 00", "sequence", "store"), field(234, 214, 36, "01", "kind", "service"),
        field(276, 214, 58, "06 00", "key length", "outside"), field(340, 214, 62, "user-1", "key", "outside"), field(408, 214, 40, "ada", "value", "model"),
        lines(32, 310, ["length: Payload is 0x14 = 20 bytes", "checksum: CRC-32 of those 20 bytes",
                        "sequence: 1, as 8 bytes", "kind: 1 is a put, 2 is a delete",
                        "Key length: 6, then 6 bytes of key", "value: The rest of payload, 3 bytes"], "mono", lead=19),
        lines(32, 444, ["Reader takes 8 bytes, learns length, takes that many", "bytes more, and compares their checksum. A record that was cut",
                        "short or damaged fails 1 of these steps."], "sub"),
    ]
    save(OUT / "record-layout.svg", WIDTH, 500,
         "The 28 bytes of the first record of the log. The frame is 8 bytes: the length, 14 00 00 00, which says that the "
         "payload is 20 bytes, and the checksum, 8d d3 da 1d, the CRC-32 of those 20 bytes. The payload is the sequence 1 as 8 "
         "bytes, the kind 01 for a put, the key length 6 as 2 bytes, the 6 bytes of the key user-1, and the value ada as the "
         "Rest of payload.",
         "One record of log", "Bytes of PUT /v1/keys/user-1 with value ada.", parts)


@figure
def crash_points():
    row = lambda y, when, disk, client, after, kind: "\n".join([
        box(32, y, 416, 82, CARD, EDGE, 8), box(32, y, 6, 82, KINDS[kind][0], KINDS[kind][0], 3),
        text(48, y + 20, when, "name"), text(48, y + 40, "on disk: " + disk, "sub"), text(48, y + 57, "client: " + client, "sub"),
        text(48, y + 74, "after restart: " + after, "sub")])
    parts = [
        row(96, "Crash before record is written", "nothing", "No answer, connection breaks", "Write did not happen", "idle"),
        row(186, "Crash in middle of record", "part of a record", "no answer", "Part is cut off: It did not happen", "danger"),
        row(276, "Crash after fsync, before answer", "the whole record", "no answer", "Write happened", "store"),
        row(366, "Crash after answer", "the whole record", "201 or 204", "Write happened", "good"),
        lines(32, 474, ["In every row, a write that was acknowledged is there after the", "restart. In rows 1 to 3 client has no answer and cannot tell",
                         "which row it is in. It sends the same PUT again, which is safe:", "PUT sets value, so doing it twice gives the same result."], "sub"),
    ]
    save(OUT / "crash-points.svg", WIDTH, 550,
         "The 4 moments at which a node can crash during a write. Before the record is written: nothing is on disk, the client "
         "gets no answer, and after restart the write did not happen. In the middle of the record: part of a record is on "
         "disk, the client gets no answer, and after restart the part is cut off. After fsync but before the answer: the whole "
         "record is on disk, the client gets no answer, and after restart the write happened. After the answer: the whole "
         "Record is on disk, client got 201 or 204, and write happened.",
         "A crash at each moment of a write", "Disk, client, and state after a restart.", parts)


@figure
def recovery_scan():
    parts = [
        text(32, 104, "THE LOG AFTER A CRASH: 63 BYTES", "tab"),
        box(32, 114, 110, 40, KINDS["good"][1], KINDS["good"][0], 6), text(87, 139, "record 1", "mono strong", "middle"),
        box(146, 114, 118, 40, KINDS["good"][1], KINDS["good"][0], 6), text(205, 139, "record 2", "mono strong", "middle"),
        box(268, 114, 26, 40, KINDS["danger"][1], KINDS["danger"][0], 6), text(281, 139, "..", "mono strong", "middle"),
        text(32, 172, "0", "mono dim"), text(146, 172, "28", "mono dim"), text(268, 172, "58", "mono dim"), text(298, 172, "63", "mono dim"),
        text(32, 208, "THE SCAN", "tab"),
    ]
    steps = [("good", "At 0: frame says 20 bytes, checksum matches", "record 1, sequence 1"),
             ("good", "At 28: frame says 22 bytes, checksum matches", "record 2, sequence 2"),
             ("danger", "At 58: only 5 bytes are left, a frame needs 8", "incomplete: stop here"),
             ("store", "Cut file to 58 bytes", "the next record will have sequence 3")]

    for k, (kind, body, sub) in enumerate(steps):
        y = 218 + 56 * k
        parts += [box(32, y, 416, 48, CARD, EDGE, 8), box(32, y, 6, 48, KINDS[kind][0], KINDS[kind][0], 3), text(48, y + 20, body, "name"), text(48, y + 38, sub, "sub")]

    parts.append(lines(32, 470, ["Scan stops at the first record that is incomplete or fails", "its checksum. Everything before it is kept, and the rest is removed",
                             "so that new records follow the last good one."], "sub"))
    save(OUT / "recovery-scan.svg", WIDTH, 526,
         "Recovery of a log of 63 bytes after a crash. Record 1 occupies bytes 0 to 27 and record 2 bytes 28 to 57, and 5 "
         "bytes of a third record follow. The scan reads a frame at 0 that says 20 bytes and whose checksum matches: record 1. "
         "At 28 the frame says 22 bytes and the checksum matches: record 2. At 58 only 5 bytes are left and a frame needs 8, so "
         "the record is incomplete and the scan stops. The file is cut to 58 bytes, and the next record will have sequence 3.",
         "Reading log after a crash", "Every complete record is kept. What follows is removed.", parts)


@figure
def sync_cost():
    bar = lambda y, label_, value, share, kind: "\n".join([
        text(32, y - 8, label_, "name"), text(448, y - 8, value, "mono", "end"),
        box(32, y, 416, 22, CARD, EDGE, 6), box(32, y, max(6, 416 * share), 22, KINDS[kind][1], KINDS[kind][0], 6)])
    parts = [
        text(32, 104, "TIME FOR 1 RECORD", "tab"),
        bar(132, "write only", "0.003 ms", 0.003 / 5.395, "good"), bar(186, "write, then fsync", "5.395 ms", 1.0, "danger"),
        text(32, 246, "RECORDS PER SECOND", "tab"),
        bar(274, "write only", "366991", 1.0, "good"), bar(328, "write, then fsync", "185", 185 / 366991, "danger"),
        lines(32, 384, ["Write copies bytes into kernel's memory and returns.", "Fsync waits until disk reports that bytes are stored.",
                         "Wait is about 1900 times longer than copy. An answer", "sent after fsync still holds after a power failure."], "sub"),
    ]
    save(OUT / "sync-cost.svg", WIDTH, 456,
         "The cost of fsync on an NVMe disk. Appending 1 record takes 0.003 ms with write only and 5.395 ms "
         "with write followed by fsync. That is 366991 records per second against 185. write copies the bytes into the "
         "kernel's memory and returns, and fsync waits until the disk reports that the bytes are stored.",
         "Cost of waiting for disk", "500 records of 100 bytes, appended to a file on NVMe.", parts)


@figure
def survives():
    col = lambda x, title, kind, rows: "\n".join([card(x, 104, 200, 44, kind, title, [])] + [
        "\n".join([box(x, 162 + 62 * k, 200, 52, CARD, EDGE, 8), text(x + 12, 182 + 62 * k, what, "tab"), text(x + 12, 202 + 62 * k, value, "mono strong")])
        for k, (what, value) in enumerate(rows)])
    parts = [col(32, "process killed", "client", [("Map in process", "lost"), ("bytes given to write", "kept"), ("bytes after fsync", "kept")]),
             col(248, "power failure", "danger", [("Map in process", "lost"), ("bytes given to write", "lost"), ("bytes after fsync", "kept")]),
             lines(32, 372, ["After write, bytes are in kernel's memory. kernel", "Outlives process, so a killed process loses nothing it wrote.",
                              "A power failure empties kernel's memory too. Only fsync", "Covers both, and a test that kills process cannot show the",
                              "difference."], "sub")]
    save(OUT / "survives.svg", WIDTH, 468,
         "What survives 2 kinds of failure. When the process is killed, the map in the process is lost, bytes given to write "
         "are kept, and bytes after fsync are kept. When the power fails, the map is lost, bytes given to write are lost, and "
         "bytes after fsync are kept. After write the bytes are in the kernel's memory, and the kernel outlives the process, "
         "So only a power failure shows difference.",
         "What a crash takes away", "A killed process and a power failure lose different things.", parts)


@figure
def two_machines():
    parts = [
        zone(32, 104, 196, 150, "node-a: client"), zone(252, 104, 196, 150, "node-b: server"),
        card(44, 130, 172, 52, "client", "kvctl load", ["sends PUT"], glyph="terminal"),
        card(264, 130, 172, 52, "store", "kvd", ["port 7001"], glyph="listen"),
        wire([(216, 156), (264, 156)]),
        cylinder(54, 192, 152, 54, "idle", "acked.txt", []), cylinder(274, 192, 152, 54, "store", "kv.log", []),
        text(32, 290, "THE TEST", "tab"),
    ]
    steps = [("client", "Kvctl writes keys and notes each one server answered"), ("danger", "After 3 seconds kvd is killed with signal 9"),
             ("store", "kvd is started again and reads its log"), ("good", "kvctl reads every noted key: 1107 of 1107 are there")]

    for k, (kind, body) in enumerate(steps):
        y = 300 + 42 * k
        parts += [box(32, y, 416, 34, CARD, EDGE, 8), box(32, y, 6, 34, KINDS[kind][0], KINDS[kind][0], 3), text(48, y + 22, body, "sub")]

    save(OUT / "two-machines.svg", WIDTH, 484,
         "The test on 2 machines. On node-a, kvctl load sends PUT requests and writes each "
         "acknowledged key to acked.txt. On node-b, kvd listens on port 7001 and writes "
         "kv.log. kvctl writes keys and notes each one the server answered. After 3 seconds kvd is killed with signal 9. kvd is "
         "started again and reads its log. kvctl reads every noted key, and 1107 of 1107 are there.",
         "The same test on 2 machines", "Client keeps its own record of what server promised.", parts)


# ------------------------------------------------ chapter 3: replication

def log_row(x, y, name, last, total, kind, committed=None, w=30):
    """A log as a row of numbered records. Records up to `committed` are filled."""
    accent, tint = KINDS[kind]
    parts = [text(x, y + 20, name, "name")]

    for k in range(1, total + 1):
        left = x + 96 + (w + 3) * (k - 1)
        present, done = k <= last, committed is not None and k <= committed
        parts += [box(left, y, w, 30, (tint if done or committed is None else CARD) if present else "#F4F5F7", accent if present else EDGE, 5),
                  text(left + w / 2, y + 20, str(k) if present else "", "mono strong", "middle")]

    return "\n".join(parts)


@figure
def repl_nodes():
    parts = [
        server(120, 96, 240, "Client", "kvctl or curl", "terminal", "client"),
        wire([(240, 146), (240, 196)]), badge(240, 170, 1),
        server(100, 196, 280, "node 1: leader", "HTTP on port 7001", "chip", "store"),
        disk(170, 254, 140, "log"), badge(150, 269, 2),
        wire([(150, 246), (150, 322), (118, 322), (118, 352)]), wire([(330, 246), (330, 322), (362, 322), (362, 352)]),
        badge(118, 322, 3), badge(362, 322, 3),
        server(32, 352, 200, "node 2", "gRPC port 7102", "chip", "service"),
        server(248, 352, 200, "node 3", "gRPC port 7103", "chip", "service"),
        disk(62, 410, 140, "log"), disk(278, 410, 140, "log"), badge(42, 425, 4), badge(258, 425, 4),
    ]
    steps, bottom = legend_steps(476, [
        "Client sends a write to leader over HTTP.",
        "Leader appends record to its log, on disk.",
        "It sends record to both followers in an Append call.",
        "Each follower stores record on its disk and answers.",
        "After the first answer, 2 of 3 logs hold record.",
        "Leader applies record and answers client.",
    ])
    parts.append(steps)
    save(OUT / "repl-nodes.svg", WIDTH, bottom + 14,
         "The 3 nodes of the chapter and the path of a write. Step 1: the client sends a write to the leader, node 1, over "
         "HTTP on port 7001. Step 2: the leader appends the record to its log and waits for the disk. Step 3: it sends the "
         "record to both followers, node 2 on port 7102 and node 3 on port 7103, in an Append call over gRPC. Step 4: each "
         "follower appends the record, waits for its disk and answers. Step 5: after the first answer, 2 of 3 logs hold the "
         "record. Step 6: Leader applies record and answers client.",
         "A leader and 2 followers", "Follow numbers from 1 to 6.", parts)


@figure
def repl_state():
    parts = [
        log_row(32, 104, "log", 9, 9, "store", committed=7),
        f'  <line x1="{128 + 33 * 7 - 1.5}" y1="96" x2="{128 + 33 * 7 - 1.5}" y2="170" stroke="{INK}" stroke-width="2" stroke-dasharray="4 3"/>',
        text(128 + 33 * 7 - 8, 162, "committed: 7", "pill", "end", INK), text(128 + 33 * 7 + 6, 162, "last: 9", "pill", "start", INK),
        card(32, 190, 200, 78, "good", "records 1 to 7", ["On a majority of logs", "Applied to entries"]),
        card(248, 190, 200, 78, "store", "records 8 and 9", ["not yet on a majority", "not applied, not visible"]),
        lines(32, 300, ["A replica keeps 2 positions in its log. Last is the end of log.", "committed is the last record known to be on a majority.",
                        "Reads see entries, which contain records up to committed.", "A record moves from right group to left when a majority",
                        "Of replicas has stored it."], "sub"),
    ]
    save(OUT / "repl-state.svg", WIDTH, 392,
         "The state of a replica. Its log holds records 1 to 9. Records 1 to 7 are committed: they are on a majority of the "
         "logs and are applied to the entries. Records 8 and 9 are on this log and perhaps on others, are not applied and "
         "are not visible to reads. The replica keeps 2 positions, last, the end of the log, and committed, the last record "
         "known to be on a majority.",
         "Committed and uncommitted records", "A replica with 9 records, of which 7 are committed.", parts)


@figure
def repl_commit_rule():
    parts = [
        text(32, 104, "THE LAST SEQUENCE OF EACH REPLICA", "tab"),
        log_row(32, 114, "leader", 10, 10, "store", w=27), log_row(32, 152, "follower 1", 7, 10, "service", w=27), log_row(32, 190, "follower 2", 9, 10, "service", w=27),
        text(32, 252, "SORTED, HIGHEST FIRST", "tab"),
        chip(32, 262, 120, "10", "store", 34), chip(180, 262, 120, "9", "good", 34), chip(328, 262, 120, "7", "idle", 34),
        text(92, 314, "leader", "sub", "middle"), text(240, 314, "follower 2", "sub", "middle"), text(388, 314, "follower 1", "sub", "middle"),
        lines(32, 348, ["Value in middle is 9. At least 2 of 3 replicas hold", "Every record up to 9, so leader commits up to 9.",
                        "Record 10 is on 1 log and stays uncommitted.", "With 5 replicas rule takes third of 5 sorted values."], "sub"),
    ]
    save(OUT / "repl-commit-rule.svg", WIDTH, 424,
         "How the leader computes the committed sequence. The leader's log ends at 10, the log of follower 1 at 7 and the "
         "log of follower 2 at 9. Sorted with the highest first, the values are 10, 9 and 7. The value in the middle is 9, "
         "so at least 2 of the 3 replicas hold every record up to 9, and the leader commits up to 9. Record 10 is on 1 log "
         "and stays uncommitted.",
         "Commit rule", "Highest sequence stored on a majority of replicas.", parts)


@figure
def repl_catchup():
    parts = [log_row(32, 104, "leader", 9, 9, "store"), log_row(32, 142, "follower", 7, 9, "service"),
             text(32, 200, "THE LEADER BELIEVES THAT THE FOLLOWER'S LOG ENDS AT 6", "tab")]
    rows, bottom = step_rows(212, [
        ("store", "Leader sends records 7 to 9", "previous_sequence 6"),
        ("danger", "Follower's log ends at 7. It refuses", "appended false, last_sequence 7"),
        ("store", "Leader sends records 8 and 9", "previous_sequence 7"),
        ("good", "Follower appends them", "appended true, last_sequence 9"),
    ])
    parts += [rows, lines(32, bottom + 18, ["A follower appends only when message starts exactly where", "Its log ends. A refusal carries position of its log, and the",
                                            "leader's next message starts there."], "sub")]
    save(OUT / "repl-catchup.svg", WIDTH, bottom + 72,
         "How a leader and a follower agree on where to continue. The leader's log holds records 1 to 9 and the follower's "
         "records 1 to 7, and the leader believes that the follower's log ends at 6. Step 1: the leader sends records 7 to 9 "
         "with previous_sequence 6. Step 2: the follower's log ends at 7, so it refuses and answers appended false, "
         "last_sequence 7. Step 3: the leader sends records 8 and 9 with previous_sequence 7. Step 4: the follower appends "
         "them and answers appended true, last_sequence 9.",
         "Bringing a follower up to date", "Follow numbers from 1 to 4.", parts)


@figure
def repl_write_path():
    rows, bottom = step_rows(96, [
        ("client", "Handler takes its turn", "writes are processed 1 after another"),
        ("store", "It waits for all earlier records to commit", "Condition is checked against a settled state"),
        ("store", "propose: check condition, append, fsync", "Record is in leader's log, uncommitted"),
        ("store", "It wakes 2 follower tasks", "Each sends follower what it lacks"),
        ("service", "A follower answers", "Task records follower's last sequence"),
        ("good", "Commit rule advances committed", "Record is applied to entries"),
        ("client", "Handler sees its sequence committed", "It answers 201 or 204 with version"),
        ("danger", "If 1 second passes without a majority", "It answers 503, and record stays in log"),
    ])
    parts = [rows]
    save(OUT / "repl-write-path.svg", WIDTH, bottom + 12,
         "The steps of a write in the leader. Step 1: the handler takes its turn, since writes are processed 1 after another. "
         "Step 2: it waits until every earlier record is committed. Step 3: propose checks the condition, appends the record "
         "and waits for the disk. Step 4: it wakes the 2 follower tasks, and each sends its follower what it lacks. Step 5: a "
         "follower answers, and the task records the follower's last sequence. Step 6: the commit rule gives a new committed "
         "sequence, and the record is applied to the entries. Step 7: the handler sees its sequence committed and answers "
         "201 or 204 with the version. Step 8: if 1 second passes without a majority, it answers 503, and the record stays "
         "In log.",
         "A write in leader", "Follow numbers from 1 to 8.", parts)


@figure
def repl_promote():
    rows, bottom = step_rows(96, [
        ("danger", "Leader's machine and disk are lost", "228 writes had been acknowledged"),
        ("service", "Operator reads both followers' health", "both logs end at 228"),
        ("model", "Follower with longer log is chosen", "it holds every acknowledged record"),
        ("store", "It is restarted as leader with term 2", "1 more than term of lost leader"),
        ("service", "The other follower receives term 2", "It adopts term 2 and follows new leader"),
        ("idle", "A new, empty node is added as a follower", "Leader sends it all 228 records"),
        ("danger", "A message of term 1 is refused from now on", "Lost leader cannot disturb shard if it returns"),
    ])
    parts = [rows]
    save(OUT / "repl-promote.svg", WIDTH, bottom + 12,
         "Replacing a lost leader by hand, in 7 steps. Step 1: the leader's machine is lost with its disk, after 228 writes "
         "had been acknowledged. Step 2: the operator reads the health of both followers, and both logs end at 228. Step 3: "
         "the follower with the longest log is chosen, because it holds every acknowledged record. Step 4: it is restarted "
         "as leader with term 2. Step 5: the other follower receives a message of term 2, adopts the term and follows the "
         "new leader. Step 6: a new, empty node is added as a follower, and the leader sends it all 228 records. Step 7: a "
         "message of term 1 is refused from now on, so the lost leader cannot disturb the shard if it returns.",
         "Replacing a lost leader", "Follow numbers from 1 to 7.", parts)


# ------------------------------------------------ chapter 4: leader election

def term_row(x, y, name, terms, kind, hot=(), w=34):
    """A log as a row of records, each showing its sequence and, under it, its term."""
    accent, tint = KINDS[kind]
    parts = [text(x, y + 20, name, "name")]

    for k, term in enumerate(terms):
        left = x + 96 + (w + 4) * k
        bad = k in hot
        parts += [box(left, y, w, 30, KINDS["danger"][1] if bad else tint, KINDS["danger"][0] if bad else accent, 5),
                  text(left + w / 2, y + 20, str(k + 1), "mono strong", "middle"), text(left + w / 2, y + 46, "t%d" % term, "mono dim", "middle")]

    return "\n".join(parts)


@figure
def elect_roles():
    parts = [
        card(32, 104, 118, 64, "service", "Follower", ["takes records", "from a leader"]),
        card(181, 104, 118, 64, "store", "Candidate", ["asks for the", "others' votes"]),
        card(330, 104, 118, 64, "good", "Leader", ["takes writes,", "sends records"]),
        wire([(150, 124), (181, 124)]), wire([(299, 124), (330, 124)]),
        badge(165, 104, 1), badge(314, 104, 2),
        wire([(389, 168), (389, 222), (70, 222), (70, 168)]), badge(240, 222, 3),
        wire([(240, 168), (240, 194), (112, 194), (112, 168)], kind="idle"), badge(180, 194, 4),
    ]
    steps, bottom = legend_steps(266, [
        "A follower hears nothing from a leader for 1 to 2 seconds.",
        "A majority of members votes for candidate.",
        "A leader sees a higher term and becomes a follower.",
        "A candidate sees a leader of its term, or a higher term.",
    ])
    parts += [steps, lines(32, bottom + 12, ["Every member starts as a follower. A candidate that wins no", "majority waits for its timeout and stands again in a new term."], "sub")]
    save(OUT / "elect-roles.svg", WIDTH, bottom + 50,
         "The 3 roles of a member and the transitions between them. A follower accepts records from a leader. A candidate "
         "asks the others for their votes. A leader accepts writes and sends records. Transition 1, follower to candidate: "
         "the follower hears nothing from a leader for 1 to 2 seconds. Transition 2, candidate to leader: a majority of the "
         "members votes for the candidate. Transition 3, leader to follower: the leader sees a higher term. Transition 4, "
         "candidate to follower: the candidate sees a leader of its term, or a higher term.",
         "Roles of a member", "Each number is a transition, explained below.", parts)


@figure
def elect_steps():
    rows, bottom = step_rows(96, [
        ("service", "3 members start as followers in term 0", "timeouts: member 1: 17 ticks, 2: 14, 3: 11"),
        ("store", "After 11 ticks, member 3 stands for term 1", "it stores term 1 and its own vote on disk"),
        ("store", "It sends RequestVote to members 1 and 2", "with the end of its log and that record's term"),
        ("service", "Members 1 and 2 grant their votes", "Each stores vote on disk before answering"),
        ("good", "Member 3 has 3 votes of 3 and leads term 1", "2 votes would have been enough"),
        ("good", "It appends marker of term 1: Record 1", "and sends it to both followers"),
        ("service", "Followers store record 1 and answer", "record 1 is committed"),
        ("good", "Leader accepts writes", "the first write becomes record 2"),
    ])
    parts = [rows]
    save(OUT / "elect-steps.svg", WIDTH, bottom + 12,
         "The first election of a shard, in 8 steps. Step 1: 3 members start as followers in term 0, with election timeouts "
         "of 17, 14 and 11 ticks. Step 2: after 11 ticks, member 3 stands for term 1 and stores term 1 and its own vote on "
         "disk. Step 3: it sends RequestVote to members 1 and 2 with the end of its log and the term of that record. Step 4: "
         "members 1 and 2 grant their votes, each storing the vote on disk before answering. Step 5: member 3 has 3 votes of "
         "3 and leads term 1. Step 6: it appends the marker of term 1 as record 1 and sends it to both followers. Step 7: the "
         "followers store record 1 and answer, and record 1 is committed. Step 8: the leader accepts writes, and the first "
         "write becomes record 2.",
         "An election, step by step", "Follow numbers from 1 to 8.", parts)


@figure
def elect_vote_rule():
    parts = [
        term_row(32, 104, "member 1", [1, 1, 1, 1], "service"), term_row(32, 168, "member 2", [1, 1, 1, 1, 2], "store"),
        term_row(32, 232, "member 3", [1, 1, 1], "service"),
        text(32, 312, "THE END OF EACH LOG: (LAST TERM, LAST SEQUENCE)", "tab"),
        chip(32, 322, 128, "(1, 4)", "service", 32), chip(176, 322, 128, "(2, 5)", "store", 32), chip(320, 322, 128, "(1, 3)", "service", 32),
        text(96, 372, "member 1", "sub", "middle"), text(240, 372, "member 2", "sub", "middle"), text(384, 372, "member 3", "sub", "middle"),
    ]
    rows, bottom = step_rows(396, [
        ("store", "Member 2 stands: it receives both votes", "(2, 5) is not lower than (1, 4) or (1, 3)"),
        ("service", "Member 1 stands: only member 3 votes yes", "member 2 refuses, since (1, 4) is lower than (2, 5)"),
        ("danger", "Member 3 stands: it receives no vote", "(1, 3) is lower than both other logs"),
    ])
    parts += [rows, lines(32, bottom + 18, ["A member votes only for a candidate whose log ends at least as", "Far as its own. Term is compared first, then sequence."], "sub")]
    save(OUT / "elect-vote-rule.svg", WIDTH, bottom + 56,
         "The rule for granting a vote, with 3 logs. Member 1 has 4 records, all of term 1. Member 2 has 5 records, the last "
         "of term 2. Member 3 has 3 records of term 1. The ends of the logs, as term and sequence, are 1 and 4, 2 and 5, and "
         "1 and 3. If member 2 stands, it receives both votes. If member 1 stands, only member 3 votes for it, and member 2 "
         "refuses. If member 3 stands, it receives no vote. A member votes only for a candidate whose log ends at least as "
         "Far as its own, and term is compared first, then sequence.",
         "Which candidate receives a vote", "Under each record: Term in which it was written.", parts)


@figure
def elect_repair():
    parts = [
        term_row(32, 104, "leader", [1, 1, 1, 1, 2, 2], "store"), term_row(32, 168, "member 3", [1, 1, 1, 1, 1], "service", hot=[4]),
        text(32, 248, "RECORD 5 OF MEMBER 3 WAS NEVER COMMITTED", "tab"),
    ]
    rows, bottom = step_rows(260, [
        ("store", "Leader sends record 6, after (5, t2)", "its guess for a member it has not heard from"),
        ("danger", "Member 3 has record 5 of term 1: refused", "it answers: continue from 4"),
        ("store", "Leader sends 5 and 6, after (4, t1)", "record 4 is of term 1 in both logs"),
        ("danger", "Member 3 compares both records 5", "they differ: it removes its record 5"),
        ("good", "Member 3 appends leader's records", "both logs are equal"),
    ])
    parts += [rows, lines(32, bottom + 18, ["If 2 logs hold a record of the same term at the same sequence,", "Logs are equal up to that record. Leader steps back until",
                                            "It finds such a record, and follower's log is replaced after it."], "sub")]
    save(OUT / "elect-repair.svg", WIDTH, bottom + 72,
         "How a member whose log differs from the leader's is repaired. The leader has 6 records: 4 of term 1 and 2 of term "
         "2. Member 3 has 5 records of term 1, and its record 5 was written in term 1 and never committed. Step 1: the leader "
         "sends record 6 with previous sequence 5 and term 2. Step 2: member 3 finds that its record 5 is of term 1, refuses, "
         "and answers that the leader should continue from 4. Step 3: the leader sends records 5 and 6 with previous sequence "
         "4 and term 1, which matches. Step 4: member 3 compares its record 5 with the leader's, finds that they differ, and "
         "removes its record 5. Step 5: member 3 appends the leader's records 5 and 6, and both logs are equal.",
         "Repairing a log that differs", "Follow numbers from 1 to 5.", parts)


@figure
def elect_probe():
    scale = lambda second: 32 + 416 * second / 20
    parts = [
        text(32, 104, "20 SECONDS OF WRITES AGAINST 3 MEMBERS", "tab"),
        box(32, 116, 416, 36, KINDS["good"][1], KINDS["good"][0], 6),
        box(scale(6.05), 116, scale(7.1) - scale(6.05), 36, KINDS["danger"][1], KINDS["danger"][0], 3),
        f'  <line x1="{scale(6):.1f}" y1="106" x2="{scale(6):.1f}" y2="162" stroke="{INK}" stroke-width="2" stroke-dasharray="4 3"/>',
        text(scale(6) - 6, 178, "leader killed at 6 s", "pill", "end", INK), text(scale(7.1) + 6, 178, "writes resume at 7.1 s", "pill", "start", INK),
        text(32, 200, "0 s", "mono dim"), text(448, 200, "20 s", "mono dim", "end"),
        card(32, 222, 200, 70, "good", "1443 writes", ["acknowledged, and all", "found afterwards"]),
        card(248, 222, 200, 70, "danger", "1.05 seconds", ["Longest pause between", "2 acknowledged writes"]),
        lines(32, 324, ["Pause is election timeout of follower that stood,", "followed by 1 round of votes and 1 round of records.",
                        "No operator took part."], "sub"),
    ]
    save(OUT / "elect-probe.svg", WIDTH, 382,
         "A timeline of 20 seconds of writes against 3 members. The leader is killed at 6 seconds, and writes resume at 7.1 "
         "seconds. 1443 writes were acknowledged, and all were found afterwards. The longest pause between 2 acknowledged "
         "writes was 1.05 seconds: the election timeout of the follower that stood, followed by 1 round of votes and 1 round "
         "of records. No operator took part.",
         "Cost of losing a leader", "Measured with program probe.", parts)


# ------------------------------------- block diagrams for the code of chapters 3 and 4

def decisions(y, checks, result, kind="good"):
    """A chain of checks. Each has a question and the outcome when the answer is no, and continues downward on yes."""
    parts = []

    for k, (question, detail, refusal) in enumerate(checks):
        top = y + 112 * k
        must_fit("no: " + refusal, 232, 11, bold=True)
        parts += [card(32, top, 416, 56, "client", question, [detail]),
                  wire([(110, top + 56), (110, top + 112)], label="yes"),
                  box(200, top + 68, 248, 32, KINDS["danger"][1], KINDS["danger"][0], 8),
                  text(324, top + 88, "no: " + refusal, "pill", "middle", KINDS["danger"][0])]

    bottom = y + 112 * len(checks)
    parts.append(card(32, bottom, 416, 56, kind, result[0], [result[1]]))

    return "\n".join(parts), bottom + 56


def block(x, y, w, h, kind, name, sub=()):
    return card(x, y, w, h, kind, name, list(sub))


@figure
def repl_replica_struct():
    parts = [
        zone(32, 104, 416, 86, "on disk"),
        cylinder(48, 122, 180, 58, "store", "kv.log", ["every record, in order"]),
        text(250, 148, "survives a restart", "sub"), text(250, 166, "read once, at open", "sub"),
        wire([(138, 190), (138, 232)]), badge(138, 210, 1),
        zone(32, 232, 416, 250, "In memory: Fields of Replica"),
        block(48, 252, 180, 60, "store", "records", ["a Vec, index n - 1"]),
        block(252, 252, 180, 60, "idle", "committed, term", ["2 numbers"]),
        wire([(138, 312), (138, 352)]), badge(138, 331, 2),
        block(48, 352, 180, 60, "model", "entries", ["a sorted map"]),
        block(252, 352, 180, 60, "client", "get, list", ["answer reads"]),
        wire([(252, 382), (228, 382)]), badge(240, 364, 3),
        text(48, 440, "Records holds the whole log. Entries holds result of", "sub"), text(48, 457, "applying only records 1 to committed.", "sub"),
    ]
    steps, bottom = legend_steps(512, [
        "Open reads log file into records. Nothing is applied.",
        "commit(n) applies records up to n to entries.",
        "get and list read entries: committed data only.",
    ])
    parts.append(steps)
    save(OUT / "repl-replica-struct.svg", WIDTH, bottom + 12,
         "The data of a Replica. On disk is the file kv.log with every record in order, which survives a restart and is "
         "read once, at open. In memory are records, a vector that holds the whole log with record n at index n minus 1, "
         "the numbers committed and term, and entries, a sorted map. Step 1: open reads the log file into records and "
         "applies nothing. Step 2: commit(n) applies records up to n to entries. Step 3: get and list read entries, so "
         "they see committed data only.",
         "Data of a replica", "Follow numbers from 1 to 3.", parts)


@figure
def repl_follower_flow():
    body, bottom = decisions(104, [
        ("Is message's term at least mine?", "request.term >= self.term", "refuse, report my term"),
        ("Does it start where my log ends?", "previous_sequence == last", "refuse, report my last sequence"),
    ], ("Append records, apply committed ones", "answer: appended, with my new last sequence"))
    parts = [body, lines(32, bottom + 26, ["A refusal changes nothing in follower. Leader reads the", "reported number and sends a message that passes both checks."], "sub")]
    save(OUT / "repl-follower-flow.svg", WIDTH, bottom + 66,
         "The decisions of handle_append. First check: is the term of the message at least the follower's own term? If "
         "no, the follower refuses and reports its term. Second check: does the message start where the follower's log "
         "ends, that is, does previous_sequence equal the last sequence? If no, the follower refuses and reports its last "
         "sequence. If both checks pass, the follower appends the records, applies the committed ones, and answers that it "
         "appended, with its new last sequence.",
         "What a follower does with a message", "2 checks, from top to bottom.", parts)


@figure
def repl_leader_parts():
    parts = [
        block(32, 104, 200, 56, "client", "HTTP handler", ["Node::write"]),
        block(248, 104, 200, 56, "idle", "turn", ["1 write holds it"]),
        wire([(232, 132), (248, 132)], arrow=False),
        wire([(132, 160), (132, 204)]), badge(132, 182, 1),
        block(32, 204, 416, 60, "store", "Replica, behind a mutex", ["Propose appends record to leader's log"]),
        wire([(132, 264), (132, 308)]), badge(132, 286, 2),
        block(32, 308, 200, 56, "service", "follower task 1", ["append_for, then gRPC"]),
        block(248, 308, 200, 56, "service", "follower task 2", ["append_for, then gRPC"]),
        wire([(348, 264), (348, 308)]),
        wire([(132, 364), (132, 408)]), wire([(348, 364), (348, 408)]), badge(132, 386, 3), badge(348, 386, 3),
        block(32, 408, 416, 56, "good", "record: Commit rule", ["majority_sequence of 3 last sequences"]),
        wire([(240, 464), (240, 508)]), badge(240, 486, 4),
        block(32, 508, 416, 56, "model", "committed: a watch channel", ["Handler waits here for its sequence"]),
    ]
    steps, bottom = legend_steps(596, [
        "Handler appends record and wakes both tasks.",
        "Each task asks replica what its follower lacks.",
        "An answer arrives. Record notes follower's position.",
        "Committed sequence is published. Handler answers.",
    ])
    parts.append(steps)
    save(OUT / "repl-leader-parts.svg", WIDTH, bottom + 12,
         "The parts of a leader in kvnode. The HTTP handler, Node::write, holds the turn, which 1 write holds at any "
         "moment. Step 1: the handler calls propose on the Replica, which is behind a mutex, and the record is appended to "
         "the leader's log. Step 2: both follower tasks are woken, and each calls append_for to learn what its follower "
         "lacks and sends it over gRPC. Step 3: an answer arrives, and the function record stores the follower's last "
         "sequence and applies the commit rule, majority_sequence of the 3 last sequences. Step 4: the committed sequence is "
         "published on a watch channel, where the handler waits for its sequence, and the handler answers.",
         "Parts of a leader", "Follow numbers from 1 to 4.", parts)


@figure
def elect_disk_memory():
    parts = [
        zone(32, 104, 416, 96, "on disk: must survive a restart"),
        cylinder(48, 124, 190, 62, "store", "kv.log", ["records and term markers"]),
        cylinder(254, 124, 178, 62, "danger", "state", ["term and vote"]),
        zone(32, 232, 416, 162, "in memory: rebuilt after a restart"),
        block(48, 252, 190, 56, "store", "records, terms", ["read from kv.log"]),
        block(254, 252, 178, 56, "danger", "term, voted_for", ["read from state"]),
        block(48, 320, 190, 56, "model", "entries, committed", ["start empty and at 0"]),
        block(254, 320, 178, 56, "idle", "role, leader", ["start as follower"]),
        wire([(143, 186), (143, 252)]), wire([(343, 186), (343, 252)]),
        lines(32, 424, ["A member that restarts knows its log, its term and its vote.", "It does not know which records are committed, or who leads.",
                        "Both arrive with the first message from a leader."], "sub"),
    ]
    save(OUT / "elect-disk-memory.svg", WIDTH, 484,
         "The state of a member, divided by where it is kept. On disk, where it must survive a restart: the file kv.log "
         "with the records and the term markers, and the file state with the term and the vote. In memory, rebuilt after a "
         "restart: records and terms, read from kv.log, and term and voted_for, read from state, and entries and committed, "
         "which start empty and at 0, and role and leader, which start as follower with no leader known.",
         "What a member keeps on disk", "2 files hold everything a member must remember.", parts)


@figure
def elect_append_flow():
    body, bottom = decisions(104, [
        ("Is message's term at least mine?", "request.term >= self.term", "refuse, report my last sequence"),
        ("Do I have a record at previous?", "previous_sequence <= last", "refuse, report my last sequence"),
        ("Is my record there of that term?", "term_at(previous) == previous_term", "refuse, report previous - 1"),
    ], ("Store records, apply committed ones", "answer: appended, up to previous + number of records"))
    parts = [body, lines(32, bottom + 26, ["Passing the first check also makes member a follower of the", "sender and restarts its election timeout."], "sub")]
    save(OUT / "elect-append-flow.svg", WIDTH, bottom + 66,
         "The decisions of on_append. First check: is the term of the message at least the member's own? If no, refuse "
         "and report the end of the log. Second check: does the member have a record at previous_sequence? If no, refuse and "
         "report the end of the log. Third check: is the member's record at that sequence of the term previous_term? If no, "
         "refuse and report the sequence before it. If all 3 checks pass, the member stores the records, applies the "
         "committed ones and answers that it appended. Passing the first check also makes the member a follower of the "
         "sender and restarts its election timeout.",
         "What a member does with Append", "3 checks, from top to bottom.", parts)


@figure
def elect_store_example():
    def row(y, name, values, kinds):
        out = [text(32, y + 20, name, "name")]

        for k, (value, kind) in enumerate(zip(values, kinds)):
            accent, tint = KINDS[kind]
            out += [box(170 + 56 * k, y, 50, 30, tint if value else "#F4F5F7", accent if value else EDGE, 5),
                    text(195 + 56 * k, y + 20, value, "mono strong", "middle")]

        return out

    parts = [
        text(170, 104, "sequence:      4        5        6        7        8", "mono dim"),
        *row(114, "member has", ["d", "e", "x", "y", ""], ["idle", "idle", "danger", "danger", "idle"]),
        *row(158, "leader sends", ["", "e", "f", "g", "h"], ["idle", "store", "store", "store", "store"]),
        text(32, 220, "previous_sequence is 4, and both logs hold d there in the same term", "sub"),
    ]
    rows, bottom = step_rows(238, [
        ("good", "Record 5: e in both logs, same term", "Skip it: Member already has it"),
        ("danger", "Record 6: x in log, f from leader", "Remove x and y, which follow difference"),
        ("store", "Append f, g and h in 1 write", "Log is now d e f g h"),
    ])
    parts += [rows, lines(32, bottom + 18, ["Skipping equal records makes a repeated message harmless. Only", "Records after committed sequence can differ, so only those", "are ever removed."], "sub")]
    save(OUT / "elect-store-example.svg", WIDTH, bottom + 72,
         "An example of the method store. The member holds d, e, x and y at sequences 4 to 7. The leader sends e, f, g and "
         "h for sequences 5 to 8, with previous_sequence 4, where both logs hold d in the same term. Step 1: record 5 is e "
         "in both logs with the same term, so it is skipped. Step 2: record 6 is x in the member's log and f from the "
         "leader, so the member removes x and y. Step 3: it appends f, g and h in 1 write, and the log is d, e, f, g, h.",
         "Making a log equal to leader's", "Follow numbers from 1 to 3.", parts)


@figure
def elect_node_loop():
    parts = [
        block(32, 104, 180, 56, "idle", "clock task", ["every 100 ms"]),
        block(228, 104, 180, 56, "client", "HTTP handler", ["a write"]),
        wire([(122, 160), (122, 204)]), wire([(318, 160), (318, 204)]), badge(122, 182, 1), badge(318, 182, 1),
        block(32, 204, 376, 60, "store", "Member, behind a mutex", ["tick, propose and handle return messages"]),
        wire([(220, 264), (220, 308)]), badge(220, 286, 2),
        block(32, 308, 376, 56, "service", "dispatch", ["1 task for each message"]),
        wire([(220, 364), (220, 408)]), badge(220, 386, 3),
        block(32, 408, 376, 56, "outside", "gRPC call to another member", ["Append or RequestVote, limit 500 ms"]),
        wire([(408, 436), (438, 436), (438, 234), (408, 234)]), badge(438, 335, 4),
    ]
    steps, bottom = legend_steps(496, [
        "Clock or a handler calls member, under lock.",
        "Member returns messages that have to be sent.",
        "Each message is sent as a gRPC call, in its own task.",
        "Response is a message too. It goes back to member.",
    ])
    parts += [steps, lines(32, bottom + 12, ["Member is the only code that decides. Everything around it", "Carries messages and tells it time."], "sub")]
    save(OUT / "elect-node-loop.svg", WIDTH, bottom + 50,
         "How kvraft drives a member. A clock task, every 100 ms, and an HTTP handler, for a write, call the member, which "
         "is behind a mutex. Step 1: the clock or a handler calls the member under the lock. Step 2: the member returns the "
         "messages that have to be sent. Step 3: dispatch sends each message as a gRPC call, Append or RequestVote, in its "
         "own task and with a time limit of 500 ms. Step 4: the response is a message too, and it goes back to the member, "
         "which may return more messages.",
         "Loop around a member", "Follow numbers from 1 to 4.", parts)


# ------------------------------------------------------- chapter 5: the router

@figure
def route_overview():
    parts = [
        server(120, 96, 240, "Client", "knows 1 address", "laptop", "client"),
        wire([(240, 146), (240, 196)]), badge(240, 170, 1),
        server(100, 196, 280, "Router", "port 7000", "curve", "idle"),
        wire([(190, 246), (190, 350)]), badge(190, 290, 3),
        zone(32, 330, 200, 196, "shard-a"), zone(248, 330, 200, 196, "shard-b"),
        server(44, 350, 176, "member 3", "leader", "chip", "store"), server(44, 406, 176, "member 1", "follower", "chip", "service"),
        server(44, 462, 176, "member 2", "follower", "chip", "service"),
        server(260, 350, 176, "member 3", "leader", "chip", "store"), server(260, 406, 176, "member 1", "follower", "chip", "service"),
        server(260, 462, 176, "member 2", "follower", "chip", "service"),
        badge(398, 221, 2),
    ]
    steps, bottom = legend_steps(560, [
        "A client sends every request to the router.",
        "The router hashes the key. The ring names a shard.",
        "It forwards the request to that shard's leader.",
    ])
    parts += [steps, lines(32, bottom + 12, ["Each shard is a group of 3 members from chapter 4.", "The other shard never sees this request."], "sub")]
    save(OUT / "route-overview.svg", WIDTH, bottom + 50,
         "A router in front of 2 shards. Step 1: a client, which knows 1 address, sends every request to the router on port "
         "7000. Step 2: the router hashes the key, and the ring names a shard. Step 3: it forwards the request to that "
         "shard's leader. Each shard is a group of 3 members, 1 leader and 2 followers, and the other shard never sees the "
         "request.",
         "A router in front of 2 shards", "Follow the numbers from 1 to 3.", parts)


@figure
def route_attempts():
    row = lambda y, kind, said, means, does: "\n".join([
        box(32, y, 416, 78, CARD, EDGE, 10), box(32, y, 8, 78, KINDS[kind][0], KINDS[kind][0], 4),
        text(52, y + 24, said, "name"), text(52, y + 45, means, "sub"), text(52, y + 64, does, "pill", "start", KINDS[kind][0])])
    parts = [
        text(32, 104, "WHAT A MEMBER ANSWERS, AND WHAT THE ROUTER DOES", "tab"),
        row(114, "good", "Any other status: 200, 201, 204, 404, 412", "the leader served the request", "Served: pass the response to the client"),
        row(200, "store", "421: the leader is member 1", "a follower: nothing was changed", "Refused: ask member 1"),
        row(286, "store", "503, type no-leader", "an election is running: nothing was changed", "Refused: ask the next member, after a pause"),
        row(372, "store", "The connection is refused", "the process is down: nothing was changed", "Refused: ask the next member"),
        row(458, "danger", "503 of another type, or a timeout", "the write may or may not have happened", "Unknown: answer 503, the client decides"),
        lines(32, 566, ["The router repeats a request only when it is certain that the", "first attempt changed nothing."], "sub"),
    ]
    save(OUT / "route-attempts.svg", WIDTH, 606,
         "What a member can answer and what the router does. Any other status, such as 200, 201, 204, 404 or 412, means "
         "the leader served the request, and the router passes the response to the client. 421 with the text the leader is "
         "member 1 comes from a follower that changed nothing, and the router asks member 1. 503 of type no-leader means an "
         "election is running and nothing was changed, and the router asks the next member after a pause. A refused "
         "connection means the process is down and nothing was changed, and the router asks the next member. 503 of another "
         "type, or a timeout, means the write may or may not have happened, and the router answers 503 so that the client "
         "decides.",
         "When the router asks again", "5 answers, sorted into served, refused and unknown.", parts)


# ------------------------------------------------------ chapter 6: group commit

@figure
def group_timeline():
    def lane(y, name, blocks, note):
        out = [text(32, y - 8, name, "name"), box(32, y, 416, 34, CARD, EDGE, 6)]

        for start, wide, body, kind in blocks:
            out += [box(32 + start, y + 3, wide, 28, KINDS[kind][1], KINDS[kind][0], 5),
                    text(32 + start + wide / 2, y + 22, body, "pill", "middle", KINDS[kind][0])]

        return out + [text(32, y + 52, note, "sub")]

    parts = [
        text(32, 104, "5 WRITES ARRIVE WITHIN 1 MILLISECOND", "tab"),
        *lane(140, "1 wait for each write", [(4 + 82 * k, 78, "w%d" % (k + 1), "danger") for k in range(5)],
              "5 waits of 5.4 ms: the last write is answered after 27 ms"),
        *lane(250, "Group commit", [(4, 78, "w1", "danger"), (86, 78, "w2 to w5", "good")],
              "2 waits: the last write is answered after 10.8 ms"),
    ]
    steps, bottom = legend_steps(344, [
        "The committer takes w1 and starts to wait for the disk.",
        "w2 to w5 arrive during that wait and queue up.",
        "The wait ends. The committer takes all 4 that are waiting.",
        "It stores them with 1 write and 1 wait, and answers all 4.",
    ])
    parts += [steps, lines(32, bottom + 12, ["Nobody waits for a timer. A batch is whatever arrived while the", "disk was busy, so a lone write is still stored at once."], "sub")]
    save(OUT / "group-timeline.svg", WIDTH, bottom + 50,
         "5 writes that arrive within 1 millisecond, stored in 2 ways. With 1 wait for each write, there are 5 waits of 5.4 "
         "ms, and the last write is answered after 27 ms. With group commit there are 2 waits, and the last write is "
         "answered after 10.8 ms. Step 1: the committer takes write 1 and starts to wait for the disk. Step 2: writes 2 to 5 "
         "arrive during that wait and queue up. Step 3: the wait ends, and the committer takes all 4 that are waiting. Step "
         "4: it stores them with 1 write and 1 wait, and answers all 4.",
         "Group commit, step by step", "Follow the numbers from 1 to 4.", parts)


@figure
def group_results():
    scale = lambda rate: 416 * rate / 17218
    rows = [("1 client", 167, 165, "1.0"), ("8 clients", 181, 712, "4.0"), ("64 clients", 180, 4993, "31.9"), ("256 clients", None, 17218, "119.9")]
    parts = [text(32, 104, "WRITES PER SECOND", "tab")]

    for k, (name, alone, grouped, batch) in enumerate(rows):
        y = 124 + 92 * k
        parts += [text(32, y + 10, name, "name"), text(448, y + 10, "%s writes per batch" % batch, "sub", "end")]

        if alone:
            parts += [box(32, y + 20, max(4, scale(alone)), 18, KINDS["danger"][1], KINDS["danger"][0], 4),
                      text(32 + max(4, scale(alone)) + 8, y + 34, "%d without" % alone, "mono dim")]

        parts += [box(32, y + 44, max(4, scale(grouped)), 18, KINDS["good"][1], KINDS["good"][0], 4),
                  text(32 + scale(grouped) + 8, y + 58, "%d with group commit" % grouped, "mono strong") if scale(grouped) < 240
                  else text(448, y + 80, "%d with group commit" % grouped, "mono strong", "end")]

    parts.append(lines(32, 512, ["Without group commit the rate stays near 180 whatever the load.", "With it, the rate grows with the number of clients, because",
                                 "each wait for the disk stores more writes."], "sub"))
    save(OUT / "group-results.svg", WIDTH, 566,
         "Writes per second without and with group commit. With 1 client: 167 without and 165 with, at 1.0 writes per "
         "batch. With 8 clients: 181 without and 712 with, at 4.0 writes per batch. With 64 clients: 180 without and 4993 "
         "with, at 31.9 writes per batch. With 256 clients: 17218 with group commit, at 119.9 writes per batch. Without "
         "group commit the rate stays near 180 whatever the load, and with it the rate grows with the number of clients.",
         "The effect of group commit", "Measured on 1 node with an NVMe disk.", parts)


# --------------------------------------------- builders for the design chapters

def design(name, title, grid, areas, edges, steps, alt=None):
    """A wide design diagram on a grid of cells, with numbered arrows.

    `grid` maps an id to (column, row, name, sub, glyph, kind). `areas` are
    (label, first column, first row, last column, last row). `edges` are
    (from, to, number or None, kind): an arrow between 2 cells of one row or
    one column, drawn from edge to edge. `steps` are the lines of the legend."""
    alt = alt or "%s. The components are %s. %s" % (
        title, ", ".join(cell[2] for cell in grid.values()),
        " ".join("Step %d: %s" % (number + 1, body) for number, body in enumerate(steps)))
    pitch_x, pitch_y, w, left, top = 276, 104, 222, 44, 112
    place = lambda column, row: (left + pitch_x * column, top + pitch_y * row)
    columns = 1 + max(cell[0] for cell in grid.values())
    rows = 1 + max(cell[1] for cell in grid.values())
    parts = []

    for label, c1, r1, c2, r2 in areas:
        (x1, y1), (x2, y2) = place(c1, r1), place(c2, r2)
        parts.append(zone(x1 - 16, y1 - 26, x2 - x1 + w + 32, y2 - y1 + 50 + 44, label))

    for column, row, name_, sub, glyph, kind in grid.values():
        x, y = place(column, row)
        parts.append(server(x, y, w, name_, sub, glyph, kind))

    for source, target, number, kind in edges:
        (c1, r1), (c2, r2) = grid[source][:2], grid[target][:2]
        (x1, y1), (x2, y2) = place(c1, r1), place(c2, r2)

        if r1 == r2:
            forward = c2 > c1
            start, end = (x1 + w, x2) if forward else (x1, x2 + w)
            lane = y1 + (18 if forward else 34)
            parts.append(wire([(start, lane), (end, lane)], kind=kind))
            mark = ((start + end) / 2, lane - 16 if forward else lane + 16)
        elif c1 == c2:
            down = r2 > r1
            start, end = (y1 + 50, y2) if down else (y1, y2 + 50)
            lane = x1 + (w / 2 - 22 if down else w / 2 + 22)
            parts.append(wire([(lane, start), (lane, end)], kind=kind))
            mark = (lane + (-18 if down else 18), (start + end) / 2)
        else:
            raise ValueError("%s to %s: an arrow joins 2 cells of one row or one column" % (source, target))

        if number is not None:
            parts.append(badge(mark[0], mark[1], number))

    base = top + pitch_y * rows + 6
    width = left * 2 + pitch_x * (columns - 1) + w
    half = (len(steps) + 1) // 2 if columns > 2 else len(steps)
    parts.append(text(left, base, "FOLLOW THE NUMBERS", "tab"))

    for number, body in enumerate(steps):
        x, y = (left + 12, base + 28 + 26 * number) if number < half else (width / 2 + 12, base + 28 + 26 * (number - half))
        must_fit(body, (width / 2 if columns > 2 else width) - 60)
        parts += [badge(x, y, number + 1), text(x + 20, y + 4, body, "note", fill=INK)]

    save(OUT / (name + ".svg"), width, base + 28 + 26 * half + 14, alt, title, "Arrows show the direction of each call.", parts)


def actors(name, system, groups, alt=None):
    """A use case diagram: each actor on the left, beside the things it does."""
    alt = alt or "A use case diagram of %s. %s" % (system, " ".join(
        "%s: %s." % (who, ", ".join("%s (%s)" % case for case in cases)) for _look, who, _sub, _kind, cases in groups))
    parts, shapes, y = [], [], 140

    for look, who, sub, kind, cases in groups:
        first, last = y, y + 52 * (len(cases) - 1)
        middle = max((first + last) / 2, first + 30)
        parts += [person(42, middle - 46, look, 56), text(70, middle + 28, who, "name", "middle")]
        parts += [text(70, middle + 45 + 15 * k, line_, "sub", "middle") for k, line_ in enumerate(sub)]

        for k, (body, detail) in enumerate(cases):
            parts.append(link(104, middle - 18, 206, first + 52 * k, kind))
            shapes.append(oval(318, first + 52 * k, 224, body, detail, kind))

        y = max(last + 84, first + 150)

    bottom = max(last + 40, first + 106)
    save(OUT / (name + ".svg"), WIDTH, bottom + 24, alt, "Who uses it, and for what", "Actors on the left, use cases on the right.",
         [zone(190, 100, 258, bottom - 100, system)] + parts + shapes)


def records(name, entities, notes, alt=None):
    """The core entities, 2 to a row, each with its fields."""
    alt = alt or "The core entities. %s %s" % (" ".join(
        "%s has the fields %s." % (title_, ", ".join(" ".join(row.split()) for row in rows)) for _kind, title_, rows in entities), " ".join(notes))
    parts, y = [], 96

    for k in range(0, len(entities), 2):
        tall = 0

        for column, (kind, title_, rows) in enumerate(entities[k:k + 2]):
            drawn, h = fields(32 + 222 * column, y, 194, kind, title_, rows)
            parts.append(drawn)
            tall = max(tall, h)

        y += tall + 18

    parts.append(lines(32, y + 14, notes, "sub"))
    save(OUT / (name + ".svg"), WIDTH, y + 14 + 17 * len(notes) + 6, alt, "The core entities", "What the system stores.", parts)


# ------------------------------------------------- chapters 7 to 16: the designs

S, M, T, O, C, I, D = "service", "model", "store", "outside", "client", "idle", "danger"


@figure
def limiter_figures():
    actors("limiter-use-cases", "the rate limiter", [
        ("glasses", "Client", ["a program that", "calls the API"], C, [("call the API", "GET /v1/orders"), ("be told to slow down", "429, Retry-After: 2")]),
        ("cap", "Operator", ["sets the limits"], S, [("set a client's limit", "PUT /v1/limits/{client}"), ("read a client's usage", "GET /v1/limits/{client}")]),
    ])
    records("limiter-entities", [(C, "Limit", ["client    string", "capacity  u32", "rate      per second"]), (T, "Bucket", ["client   string", "tokens   f64", "updated  time"])],
            ["A Limit is what the operator sets. A Bucket is the running", "state the limiter keeps for each client."])
    design("limiter-design", "A rate limiter in front of an API", {
        "clients": (0, 1, "Clients", "call the API", "laptop", C), "gateway": (1, 1, "API gateway", "asks before each call", "swap", I),
        "api": (2, 1, "API servers", "do the work", "chip", T), "limiter": (1, 0, "Rate limiter", "token buckets", "clock", M),
        "store": (2, 0, "Counter store", "shared, in memory", "stack", S),
    }, [], [("clients", "gateway", 1, "flow"), ("gateway", "limiter", 2, "flow"), ("limiter", "store", 3, "flow"), ("gateway", "api", 4, "flow")], [
        "A client sends a request to the gateway.", "The gateway asks the limiter about this client.",
        "The limiter refills and updates the client's bucket.", "Allowed: the request goes on. Refused: 429."])


@figure
def idgen_figures():
    actors("idgen-use-cases", "the id generator", [
        ("glasses", "Service", ["needs ids for", "new records"], C, [("get a new id", "POST /v1/ids"), ("read the time of an id", "the top 41 bits")]),
        ("cap", "Operator", ["runs the nodes"], S, [("give a node its number", "0 to 1023, no 2 alike")]),
    ])
    records("idgen-entities", [(C, "Id: 64 bits", ["time     41 bits, ms", "node     10 bits", "counter  12 bits"]), (T, "Node", ["number   0 to 1023", "last     time, ms", "counter  0 to 4095"])],
            ["An id is 3 numbers packed into 64 bits. Because the time is at", "the top, ids sort in the order they were made."])
    design("idgen-design", "Ids without a shared counter", {
        "services": (0, 0, "Services", "ask for ids", "laptop", C), "node1": (1, 0, "Id node 1", "its own counter", "chip", T),
        "node2": (1, 1, "Id node 2", "its own counter", "chip", T), "coordinator": (2, 0, "Coordinator", "gives node numbers", "stack", M),
    }, [], [("coordinator", "node1", 1, "idle"), ("services", "node1", 2, "flow")], [
        "At startup, each node receives its own number.", "A service asks any node for an id.",
        "The node joins the time, its number and a counter.", "No node talks to another node to make an id."])


@figure
def shortener_figures():
    actors("shortener-use-cases", "the URL shortener", [
        ("glasses", "Author", ["shares links"], C, [("shorten a URL", "POST /v1/links"), ("read the click count", "GET /v1/links/{code}")]),
        ("curly", "Visitor", ["follows a link"], T, [("open a short link", "GET /{code}, then 301")]),
    ])
    records("shortener-entities", [(C, "Link", ["code     7 characters", "url      string", "owner    string", "created  time"]), (T, "Click", ["code  7 characters", "at    time"])],
            ["A Link is written once and read many times. Clicks are", "counted apart from links, so that reading a link stays cheap."])
    design("shortener-design", "A URL shortener", {
        "visitors": (0, 1, "Visitors", "open short links", "browser", C), "balancer": (1, 1, "Load balancer", "spreads requests", "swap", I),
        "web": (2, 1, "Web servers", "no data of their own", "chip", T), "cache": (2, 0, "Cache", "popular links", "clock", M),
        "store": (3, 1, "Key-value store", "code to URL", "stack", S), "ids": (2, 2, "Id generator", "for new links", "key", O),
    }, [], [("visitors", "balancer", 1, "flow"), ("balancer", "web", 2, "flow"), ("web", "cache", 3, "flow"), ("web", "store", 4, "flow"), ("web", "ids", 5, "idle")], [
        "A visitor opens a short link.", "The load balancer picks a web server.", "The server looks for the code in the cache.",
        "On a miss it reads the store and fills the cache.", "For a new link, it takes the next id and encodes it.", "The visitor is redirected with status 301."])


@figure
def cache_figures():
    actors("cache-use-cases", "the cache", [
        ("glasses", "Service", ["reads slow data", "often"], C, [("read through the cache", "GET /v1/entries/{key}"), ("store a value for a time", "PUT, with a TTL"), ("drop a stale value", "DELETE /v1/entries/{key}")]),
        ("cap", "Operator", ["runs the nodes"], S, [("add a cache node", "the ring gains its tokens")]),
    ])
    records("cache-entities", [(C, "Item", ["key      string", "value    bytes", "expires  time", "used     time"]), (T, "Cache node", ["id      string", "tokens  u64[]", "memory  bytes"])],
            ["An Item is a copy of data that lives elsewhere. It can be", "dropped at any moment, and the cache then fetches it again."])
    design("cache-design", "A distributed cache", {
        "services": (0, 1, "Services", "read and write", "laptop", C), "client": (1, 1, "Cache library", "a hash ring inside", "curve", I),
        "node": (2, 1, "Cache node B", "keeps recent keys", "clock", M), "a": (2, 0, "Cache node A", "keeps recent keys", "clock", M),
        "c": (2, 2, "Cache node C", "keeps recent keys", "clock", M), "db": (1, 2, "Database", "the source of truth", "stack", S),
    }, [("cache nodes", 2, 0, 2, 2)], [("services", "client", 1, "flow"), ("client", "node", 2, "flow"), ("client", "db", 3, "flow")], [
        "A service asks the cache library for a key.", "The library hashes the key and asks 1 node.",
        "On a miss, the service reads the database.", "It stores the value in the cache with a time limit."])


@figure
def queue_figures():
    actors("queue-use-cases", "the message queue", [
        ("glasses", "Producer", ["a service that", "reports events"], C, [("publish a message", "POST /v1/topics/{t}/messages")]),
        ("curly", "Consumer", ["a service that", "reacts to events"], T, [("fetch messages", "GET ...?offset=42"), ("commit an offset", "PUT .../offsets/{group}")]),
        ("cap", "Operator", ["runs the brokers"], S, [("add a partition", "more consumers in parallel")]),
    ])
    records("queue-entities", [(C, "Message", ["offset  u64", "key     string", "body    bytes", "time    time"]), (T, "Partition", ["topic   string", "number  u32", "leader  broker"]),
                               (M, "Offset", ["group      string", "partition  u32", "committed  u64"])],
            ["A Partition is an append-only log, like the log of chapter 2.", "An Offset records how far a group of consumers has read."])
    design("queue-design", "A message queue", {
        "producers": (0, 0, "Producers", "publish messages", "pencil", C), "leader": (1, 0, "Broker 1", "leads partition 0", "chip", T),
        "follower": (2, 0, "Broker 2", "follows partition 0", "chip", S), "consumers": (1, 1, "Consumers", "1 group, 2 members", "laptop", C),
        "offsets": (2, 1, "Offset store", "committed offsets", "stack", M),
    }, [], [("producers", "leader", 1, "flow"), ("leader", "follower", 2, "flow"), ("consumers", "leader", 3, "flow"), ("consumers", "offsets", 4, "flow")], [
        "A producer sends a message with a key.", "The leader appends it and copies it to a follower.",
        "A consumer fetches from its committed offset.", "After acting on them, it commits the new offset."])


@figure
def lock_figures():
    actors("lock-use-cases", "the lock service", [
        ("glasses", "Worker", ["must be alone in", "a critical step"], C, [("acquire a lock", "POST /v1/locks/{name}"), ("renew its lease", "PUT /v1/locks/{name}"), ("release the lock", "DELETE /v1/locks/{name}")]),
    ])
    records("lock-entities", [(C, "Lock", ["name     string", "holder   string", "token    u64", "expires  time"]), (T, "Protected write", ["token  u64", "data   bytes"])],
            ["The token grows by 1 with every lease. The storage that the", "lock protects checks the token on every write."])
    design("lock-design", "A lock service with fencing tokens", {
        "worker": (0, 0, "Worker", "wants to be alone", "laptop", C), "locks": (1, 0, "Lock service", "3 nodes, a majority", "lock", M),
        "storage": (0, 1, "Storage", "checks the token", "stack", T),
    }, [], [("worker", "locks", 1, "flow"), ("worker", "storage", 2, "flow")], [
        "The worker asks for the lock and receives a token.", "It sends the token with every write to the storage.",
        "The storage refuses a token lower than the last one.", "A worker with an old lease can therefore do no harm."])


@figure
def jobs_figures():
    actors("jobs-use-cases", "the job scheduler", [
        ("glasses", "Developer", ["has work to run", "later"], C, [("submit a job", "POST /v1/jobs"), ("read a job's state", "GET /v1/jobs/{id}")]),
        ("curly", "Worker", ["runs jobs"], T, [("take a job", "POST /v1/leases"), ("report the result", "PUT /v1/jobs/{id}/results/{lease}")]),
    ])
    records("jobs-entities", [(C, "Job", ["id        u64", "payload   bytes", "state     waiting|...", "attempts  u32", "run_at    time"]), (T, "Lease", ["job       u64", "worker    string", "deadline  time"])],
            ["A Lease lends a job to a worker until a deadline. A job whose", "lease runs out goes back to the queue."])
    design("jobs-design", "A job scheduler", {
        "clients": (0, 0, "Developers", "submit jobs", "laptop", C), "api": (1, 0, "Scheduler", "hands out leases", "clock", I),
        "store": (2, 0, "Job store", "replicated", "stack", S), "workers": (1, 1, "Workers", "take, run, report", "chip", T),
        "timer": (2, 1, "Reclaimer", "finds expired leases", "search", M),
    }, [], [("clients", "api", 1, "flow"), ("api", "store", 2, "flow"), ("workers", "api", 3, "flow"), ("timer", "store", 4, "idle")], [
        "A developer submits a job.", "The scheduler stores it, in the state waiting.",
        "A worker takes a job and receives a lease.", "A job whose lease has run out is queued again."])


@figure
def notify_figures():
    actors("notify-use-cases", "the notification service", [
        ("glasses", "Service", ["has something to", "tell a user"], C, [("send a notification", "POST /v1/notifications"), ("read its state", "GET /v1/notifications/{id}")]),
        ("curly", "User", ["receives messages"], T, [("choose channels", "PUT /v1/users/{id}/channels")]),
    ])
    records("notify-entities", [(C, "Notification", ["id       u64", "user     string", "channel  email|sms|push", "body     string", "key      string"]), (T, "Attempt", ["notification  u64", "try           1 to 5", "result        ok|error"])],
            ["The key is chosen by the caller. A second request with the", "same key is recognised and sends nothing."])
    design("notify-design", "A notification service", {
        "services": (0, 0, "Services", "ask to notify", "laptop", C), "api": (1, 0, "API", "drops repeats by key", "listen", I),
        "queue": (2, 0, "Queue", "1 message each", "stack", S), "senders": (3, 0, "Senders", "retry with pauses", "chip", T),
        "provider": (3, 1, "Provider", "email, SMS, push", "swap", O), "dead": (2, 1, "Set aside", "after 5 failed tries", "doc", D),
    }, [], [("services", "api", 1, "flow"), ("api", "queue", 2, "flow"), ("queue", "senders", 3, "flow"), ("senders", "provider", 4, "flow"), ("queue", "dead", 5, "idle")], [
        "A service asks for a notification, with a key.", "The API drops a repeat and queues the rest.", "A sender takes a message from the queue.",
        "It calls the provider, and tries again on failure.", "After 5 failed tries the message is set aside."])


@figure
def feed_figures():
    actors("feed-use-cases", "the news feed", [
        ("glasses", "Member", ["posts and reads"], C, [("publish a post", "POST /v1/posts"), ("read the feed", "GET /v1/newsfeeds/{user}/posts"), ("follow an account", "PUT /v1/follows/{id}")]),
    ])
    records("feed-entities", [(C, "Post", ["id      u64", "author  string", "body    string", "time    time"]), (T, "Follow", ["follower  string", "followed  string"]),
                              (M, "Feed item", ["owner  string", "post   u64", "time   time"])],
            ["A Feed item is a copy of a pointer to a post, kept for 1", "reader. The post itself is stored once."])
    design("feed-design", "A news feed", {
        "writers": (0, 0, "Authors", "publish posts", "pencil", C), "posts": (1, 0, "Post service", "stores the post", "doc", T),
        "queue": (2, 0, "Queue", "1 task per post", "stack", S), "fanout": (3, 0, "Fan-out workers", "copy to followers", "chip", T),
        "readers": (0, 1, "Readers", "open the feed", "browser", C), "feeds": (1, 1, "Feed service", "merges and sorts", "curve", I),
        "cache": (3, 1, "Feed cache", "1 list per reader", "clock", M),
    }, [], [("writers", "posts", 1, "flow"), ("posts", "queue", 2, "flow"), ("queue", "fanout", 3, "flow"), ("fanout", "cache", 4, "flow"), ("readers", "feeds", 5, "flow"), ("feeds", "cache", 6, "flow")], [
        "An author publishes a post.", "The post is stored, and a task is queued.", "A worker takes the task.",
        "It adds the post to each follower's list.", "A reader opens the feed.", "The feed service reads the reader's list."])


@figure
def objects_figures():
    actors("objects-use-cases", "the object store", [
        ("glasses", "Application", ["keeps files"], C, [("upload an object", "PUT /v1/buckets/{b}/{key}"), ("download an object", "GET /v1/buckets/{b}/{key}"), ("list a bucket", "GET /v1/buckets/{b}?prefix=")]),
        ("cap", "Operator", ["replaces disks"], S, [("replace a failed node", "copies are made again")]),
    ])
    records("objects-entities", [(C, "Object", ["bucket  string", "key     string", "size    u64", "chunks  checksum[]"]), (T, "Chunk", ["checksum  u32", "size      up to 4 MB", "nodes     3 nodes"])],
            ["An Object is a list of chunks. A Chunk is named by the", "checksum of its bytes, so equal chunks are stored once."])
    design("objects-design", "An object store", {
        "apps": (0, 0, "Applications", "upload and download", "laptop", C), "api": (1, 0, "API servers", "cut into chunks", "chip", I),
        "meta": (2, 0, "Metadata store", "names to chunks", "stack", S), "nodes": (1, 1, "Storage nodes", "chunks, 3 copies", "doc", T),
        "repair": (2, 1, "Repair worker", "replaces lost copies", "gear", M),
    }, [], [("apps", "api", 1, "flow"), ("api", "nodes", 2, "flow"), ("api", "meta", 3, "flow"), ("repair", "nodes", 4, "idle")], [
        "An application uploads an object.", "The server stores each chunk on 3 nodes.",
        "It records the object's chunk list.", "A repair worker replaces copies that are lost."])


@figure
def stream_figures():
    actors("stream-use-cases", "the video service", [
        ("glasses", "Viewer", ["watches videos"], C, [("play a video", "GET /v1/videos/{id}/manifests/default"), ("fetch the next 4 seconds", "GET .../1200/piece-17.ts")]),
        ("curly", "Creator", ["uploads videos"], T, [("upload a video", "PUT /v1/videos/{id}/source"), ("see when it is ready", "GET /v1/videos/{id}")]),
    ])
    records("stream-entities", [(C, "Video", ["id        u64", "title     string", "duration  seconds", "state     ready|..."]), (T, "Rendition", ["video    u64", "bitrate  kbit/s", "pieces   count"]),
                                (M, "Piece", ["rendition  u64", "number     u32", "seconds    4", "bytes      in object store"])],
            ["A Rendition is the whole video at 1 quality. A Piece is 4", "seconds of 1 rendition, stored as an object."])
    design("stream-design", "Uploading and playing a video", {
        "creator": (0, 0, "Creator", "uploads 1 file", "pencil", C), "upload": (1, 0, "Upload service", "stores the source", "listen", I),
        "queue": (2, 0, "Queue", "1 task per video", "stack", S), "encoders": (3, 0, "Encoders", "4 qualities, in pieces", "gear", T),
        "store": (3, 1, "Object store", "every piece", "doc", S), "cdn": (2, 1, "CDN", "copies near viewers", "clock", M),
        "viewer": (0, 1, "Viewer", "plays the video", "browser", C), "api": (1, 1, "Video API", "returns the manifest", "curve", I),
    }, [], [("creator", "upload", 1, "flow"), ("upload", "queue", 2, "flow"), ("queue", "encoders", 3, "flow"), ("encoders", "store", 4, "flow"),
            ("viewer", "api", 5, "flow"), ("cdn", "store", 6, "idle")], [
        "A creator uploads the source file.", "The upload service queues an encoding task.", "Encoders make 4 qualities, cut into pieces.",
        "Every piece is stored as an object.", "A viewer asks for the manifest: the list of pieces.", "The player fetches pieces from the CDN."])


@figure
def chat_figures():
    actors("chat-use-cases", "the chat service", [
        ("glasses", "Member", ["sends and reads", "messages"], C, [("send a message", "POST /v1/conversations/{id}/messages"), ("catch up after being offline", "GET ...?after=17"), ("see who is online", "GET /v1/members/{id}/presence")]),
    ])
    records("chat-entities", [(C, "Message", ["conversation  u64", "number        u64", "sender        string", "text          string"]), (T, "Conversation", ["id       u64", "members  string[]", "last     u64"]),
                              (M, "Cursor", ["member        string", "conversation  u64", "received      u64"])],
            ["Every message has a number within its conversation. A Cursor", "records the last number a member's device has received."])
    design("chat-design", "Delivering a chat message", {
        "sender": (0, 0, "Sender's phone", "an open connection", "laptop", C), "gateway1": (1, 0, "Gateway A", "holds connections", "listen", I),
        "chat": (2, 0, "Chat service", "numbers the message", "curve", T), "store": (3, 0, "Message store", "by conversation", "stack", S),
        "gateway2": (2, 1, "Gateway B", "holds connections", "listen", I), "receiver": (3, 1, "Receiver's phone", "an open connection", "laptop", C),
        "sessions": (1, 1, "Session store", "who is on which gateway", "search", M),
    }, [], [("sender", "gateway1", 1, "flow"), ("gateway1", "chat", 2, "flow"), ("chat", "store", 3, "flow"), ("chat", "gateway2", 4, "flow"), ("gateway2", "receiver", 5, "flow")], [
        "The sender's phone sends the message over its connection.", "The gateway passes it to the chat service.", "The service gives it the next number and stores it.",
        "It finds the receiver's gateway and forwards the message.", "The gateway pushes it to the receiver's phone."])


@figure
def pay_figures():
    actors("pay-use-cases", "the payment system", [
        ("glasses", "Shop", ["charges its", "customers"], C, [("charge a customer", "POST /v1/payments"), ("refund a payment", "POST /v1/payments/{id}/refunds"), ("read a payment", "GET /v1/payments/{id}")]),
        ("cap", "Accountant", ["checks the books"], S, [("read an account's entries", "GET /v1/accounts/{id}/entries")]),
    ])
    records("pay-entities", [(C, "Payment", ["id      u64", "key     string", "amount  cents", "state   done|refused"]), (T, "Entry", ["payment  u64", "account  string", "amount   +/- cents"]),
                             (M, "Account", ["id       string", "balance  cents"])],
            ["A Payment produces 2 Entries that add up to 0: money leaves", "1 account and enters another. A balance is the sum of entries."])
    design("pay-design", "Charging a customer", {
        "shop": (0, 0, "Shop", "sends a charge", "laptop", C), "api": (1, 0, "Payment API", "checks the key", "listen", I),
        "ledger": (2, 0, "Ledger", "entries in pairs", "stack", S), "bank": (2, 1, "Card network", "outside our system", "swap", O),
        "keys": (1, 1, "Key store", "1 result per key", "key", M),
    }, [], [("shop", "api", 1, "flow"), ("api", "keys", 2, "flow"), ("api", "ledger", 3, "flow"), ("ledger", "bank", 4, "flow")], [
        "A shop sends a charge with a key of its own.", "A key seen before returns the earlier result.",
        "The ledger writes 2 entries in 1 transaction.", "The card network moves the money between banks."])


@figure
def booking_figures():
    actors("booking-use-cases", "the booking system", [
        ("glasses", "Buyer", ["wants a seat"], C, [("see which seats are free", "GET /v1/shows/{id}/seats"), ("hold a seat", "POST /v1/shows/{id}/holds"), ("pay for a held seat", "POST /v1/bookings")]),
    ])
    records("booking-entities", [(C, "Seat", ["show   u64", "label  string", "state  free|held|sold"]), (T, "Hold", ["seat     string", "buyer    string", "expires  time"]),
                                 (M, "Booking", ["id       u64", "seat     string", "buyer    string", "payment  u64"])],
            ["A Hold reserves a seat for a few minutes. A Booking is made", "from a hold that is still valid when the payment succeeds."])
    design("booking-design", "Booking a seat", {
        "buyer": (0, 0, "Buyer", "picks a seat", "browser", C), "api": (1, 0, "Booking API", "conditional writes", "listen", I),
        "seats": (2, 0, "Seat store", "strongly consistent", "stack", S), "pay": (1, 1, "Payment system", "see chapter 19", "key", O),
        "reaper": (2, 1, "Hold reaper", "frees expired holds", "clock", M),
    }, [], [("buyer", "api", 1, "flow"), ("api", "seats", 2, "flow"), ("api", "pay", 3, "flow"), ("reaper", "seats", 4, "idle")], [
        "A buyer asks to hold seat 12.", "The API writes the hold only if the seat is free.",
        "The buyer pays, and the hold becomes a booking.", "Holds that are not paid in time are released."])


@figure
def nearby_figures():
    actors("nearby-use-cases", "the ride service", [
        ("glasses", "Rider", ["wants a ride"], C, [("request a ride", "POST /v1/rides"), ("watch the driver approach", "GET /v1/rides/{id}")]),
        ("curly", "Driver", ["offers rides"], T, [("report a position", "POST /v1/drivers/{id}/positions"), ("accept a ride", "PUT /v1/rides/{id}/assignments/{driver}")]),
    ])
    records("nearby-entities", [(C, "Driver", ["id        string", "position  x, y", "square    column, row", "state     free|busy"]), (T, "Ride", ["id      u64", "rider   string", "driver  string", "state   requested|..."])],
            ["A driver's square is computed from the position. The service", "keeps, for every square, the list of drivers inside it."])
    design("nearby-design", "Finding a driver for a rider", {
        "driver": (0, 0, "Drivers", "report every 4 s", "laptop", C), "location": (1, 0, "Location service", "position to square", "curve", I),
        "grid": (2, 0, "Grid index", "drivers per square", "search", M), "rider": (0, 1, "Rider", "requests a ride", "browser", C),
        "match": (1, 1, "Matching service", "asks nearby drivers", "swap", T), "rides": (2, 1, "Ride store", "strongly consistent", "stack", S),
    }, [], [("driver", "location", 1, "flow"), ("location", "grid", 2, "flow"), ("rider", "match", 3, "flow"), ("match", "rides", 4, "flow")], [
        "Every driver reports its position.", "The location service files it under a grid square.",
        "A rider requests a ride from a position.", "The matcher reads 9 squares and records the ride."])


@figure
def typeahead_figures():
    actors("typeahead-use-cases", "the suggestion service", [
        ("glasses", "Searcher", ["types a search"], C, [("get suggestions", "GET /v1/suggestions?q=ka"), ("run the search", "GET /v1/search?q=kafka")]),
    ])
    records("typeahead-entities", [(C, "Search count", ["text   string", "count  u32, per week"]), (T, "Suggestion list", ["prefix  string", "top     5 searches"])],
            ["Counts are collected from the searches people run. Lists are", "computed from the counts ahead of time, 1 for each prefix."])
    design("typeahead-design", "Suggestions while typing", {
        "user": (0, 0, "Searcher", "types a letter", "browser", C), "api": (1, 0, "Suggestion API", "answers from memory", "listen", I),
        "lists": (2, 0, "Prefix lists", "top 5 per prefix", "search", M), "log": (0, 1, "Search log", "every search made", "doc", S),
        "counter": (1, 1, "Counting job", "runs every hour", "gear", T), "counts": (2, 1, "Search counts", "text and count", "stack", S),
    }, [], [("user", "api", 1, "flow"), ("api", "lists", 2, "flow"), ("log", "counter", 3, "flow"), ("counter", "counts", 4, "flow"), ("counts", "lists", 5, "idle")], [
        "After each letter, the browser asks for suggestions.", "The API returns the stored list for that prefix.", "Every search that is run is written to a log.",
        "A job counts the searches of the last week.", "New lists are built from the counts."])


# ------------------------------------------------ chapter 7: the 5 algorithms

GOOD, BAD, WAIT = KINDS["good"][0], KINDS["danger"][0], KINDS["store"][0]
ARRIVALS = [600, 700, 800, 900, 950, 1000, 1050, 1100, 1150, 1200, 1250]


def wrap(body, room=396, size=12.5):
    """Breaks a sentence into rows that fit `room`."""
    rows, row = [], ""

    for word in body.split():
        longer = (row + " " + word).strip()

        if row and width_of(longer, size) > room:
            rows.append(row)
            row = word
        else:
            row = longer

    return rows + [row]


def at(time, lo, hi):
    return 48 + 384 * (time - lo) / (hi - lo)


def dot(x, y, kind, r=6):
    """A request: green when forwarded, a red cross when refused, amber while it waits."""
    if kind == "no":
        return (f'  <circle cx="{x:.1f}" cy="{y}" r="{r}" fill="#FFFFFF" stroke="{BAD}" stroke-width="1.8"/>\n'
                f'  <path d="M{x - r / 2:.1f},{y - r / 2} l{r},{r} m0,{-r} l{-r},{r}" stroke="{BAD}" stroke-width="1.8"/>')

    return f'  <circle cx="{x:.1f}" cy="{y}" r="{r}" fill="{GOOD if kind == "ok" else WAIT}" stroke="#FFFFFF" stroke-width="1.2"/>'


def timeline(y, lo, hi, marks, now=None, bounds=(), label=None, r=6, step=500):
    """A time axis with the requests on it. `marks` are (time, kind) pairs."""
    parts = [f'  <line x1="40" y1="{y}" x2="440" y2="{y}" stroke="{MUTED}" stroke-width="1.6"/>']

    for time in range(lo, hi + 1, step):
        x = at(time, lo, hi)
        parts += [f'  <line x1="{x:.1f}" y1="{y - 5}" x2="{x:.1f}" y2="{y + 5}" stroke="{MUTED}" stroke-width="1.6"/>',
                  text(x, y + 21, "%.1f s" % (time / 1000), "mono dim", "middle")]

    parts += [f'  <line x1="{at(time, lo, hi):.1f}" y1="{y - 36}" x2="{at(time, lo, hi):.1f}" y2="{y + 6}" stroke="{WIRE}" stroke-width="1.4" stroke-dasharray="4 4"/>'
              for time in bounds]
    parts += [dot(at(time, lo, hi), y - 14, kind, r) for time, kind in marks]

    if now is not None:
        x = at(now, lo, hi)
        parts += [f'  <line x1="{x:.1f}" y1="{y - 32}" x2="{x:.1f}" y2="{y + 6}" stroke="{INK}" stroke-width="2"/>',
                  text(x, y - 37, "now", "pill", "middle", INK)]

    if label:
        parts.append(text(40, y - 54, label, "tab"))

    return "\n".join(parts)


def slots(x, y, filled, kind, total=5, w=30, labels=None):
    """A row of places, of which `filled` are taken. A fraction fills part of a place."""
    accent, tint = KINDS[kind]
    parts = []

    for k in range(total):
        share = min(max(filled - k, 0), 1)
        left = x + (w + 6) * k
        parts.append(box(left, y, w, 26, CARD, EDGE, 5))

        if share > 0:
            parts.append(box(left, y, max(4, w * share), 26, tint, accent, 5))

        if labels and k < len(labels):
            parts.append(text(left + w / 2, y + 17, labels[k], "mono strong", "middle"))

    return "\n".join(parts)


def panel(x, y, w, heading, body, active):
    """A labelled piece of state. The piece that the current step uses has a dark outline."""
    return "\n".join([box(x, y, w, 76, CARD, INK if active else EDGE, 10, 2 if active else 1.3),
                      text(x + 12, y + 20, heading, "tab"), body])


def frames(prefix, title, steps, height=396, caption_y=296):
    """Writes 1 picture for each step. `steps` are (parts, caption) pairs."""
    for k, (parts, caption) in enumerate(steps):
        rows = wrap(caption)

        if len(rows) > 4:
            raise ValueError("caption of %s step %d needs %d rows" % (prefix, k + 1, len(rows)))

        note = [box(32, caption_y, 416, 88, "#EEF2F7", EDGE, 10)]
        note += [text(44, caption_y + 23 + 18 * row, body, "note", fill=INK) for row, body in enumerate(rows)]
        save(OUT / ("%s-%02d.svg" % (prefix, k + 1)), WIDTH, height, "%s, step %d of %d. %s" % (title, k + 1, len(steps), caption),
             title, "The limit is 5 requests per second. Step %d of %d." % (k + 1, len(steps)), parts + note)


def story(prefix, title, steps, lede="Step %d of %d."):
    """A picture in steps made of labelled panels of text. `steps` are (panels, caption) pairs, and
    `panels` are (heading, lines, active). A line that starts with "! " is drawn in red, and one
    that starts with "> " in bold."""
    count = len(steps[0][0])
    tall = [30 + 19 * max(len(panels[k][1]) for panels, said in steps) + 8 for k in range(count)]
    caption_y = 96 + sum(tall) + 10 * count + 4

    for number, (panels, caption) in enumerate(steps):
        parts, y = [], 96

        for k, (heading, rows, active) in enumerate(panels):
            parts += [box(32, y, 416, tall[k], CARD, INK if active else EDGE, 10, 2 if active else 1.3), text(44, y + 20, heading, "tab")]

            for row, body in enumerate(rows):
                cls = "mono trap" if body.startswith("! ") else "mono strong" if body.startswith("> ") else "mono"
                parts.append(fitted(44, y + 42 + 19 * row, body[2:] if body[:2] in ("! ", "> ") else body, cls, "start", 392))

            y += tall[k] + 10

        rows = wrap(caption)

        if len(rows) > 4:
            raise ValueError("caption of %s step %d needs %d rows" % (prefix, number + 1, len(rows)))

        parts.append(box(32, caption_y, 416, 88, "#EEF2F7", EDGE, 10))
        parts += [text(44, caption_y + 23 + 18 * row, body, "note", fill=INK) for row, body in enumerate(rows)]
        save(OUT / ("%s-%02d.svg" % (prefix, number + 1)), WIDTH, caption_y + 100,
             "%s, step %d of %d. %s" % (title, number + 1, len(steps), caption), title, lede % (number + 1, len(steps)), parts)


def marks_until(seen):
    return [(time, "ok" if passed else "no") for time, passed in seen]


def busiest(times):
    return max(sum(1 for time in times if start <= time < start + 1000) for start in times)


@figure
def steps_limiter_fixed():
    steps, counts, seen = [], {0: 0, 1: 0}, []

    def picture(now, window):
        body = lambda w: slots(44 + 216 * w, 228, counts[w], "client", w=22)
        return [timeline(150, 500, 1500, marks_until(seen), now, [1000], "REQUESTS OF 1 CLIENT"),
                panel(32, 196, 200, "WINDOW 0: 0.0 S TO 1.0 S", body(0) + "\n" + text(228, 246, "%d of 5" % counts[0], "mono", "end"), window == 0),
                panel(248, 196, 200, "WINDOW 1: 1.0 S TO 2.0 S", body(1) + "\n" + text(444, 246, "%d of 5" % counts[1], "mono", "end"), window == 1)]

    steps.append((picture(None, None), "The limiter keeps 1 number for the client: how many requests it has forwarded in the current window. "
                  "Windows are the seconds of the clock, and each starts with a count of 0."))

    for now in ARRIVALS:
        window = now // 1000
        passed = counts[window] < 5
        first = counts[window] == 0 and window == 1
        counts[window] += passed
        seen.append((now, passed))
        said = ("At %d ms the clock is in window %d. " % (now, window)
                + ("This is a new window, so the count starts again from 0. " if first else "")
                + ("The count rises to %d, which is within 5: forwarded." % counts[window] if passed
                   else "The count is already 5: refused, and the count stays 5."))
        steps.append((picture(now, window), said))

    times = [time for time, passed in seen if passed]
    steps.append((picture(None, None), "%d of 11 requests were forwarded, and all %d of them arrived within %d ms. Each window obeyed "
                  "the limit of 5, and the client still sent twice the limit in well under 1 second."
                  % (len(times), busiest(times), times[-1] - times[0])))
    frames("steps-limiter-fixed", "Fixed window counter", steps)


@figure
def steps_limiter_log():
    steps, log, seen = [], [], []

    def picture(now):
        cells_ = slots(44, 228, len(log), "service", w=70, labels=[str(time) for time in log])
        return [timeline(150, 500, 1500, marks_until(seen), now, [], "REQUESTS OF 1 CLIENT"),
                panel(32, 196, 416, "LOG: ARRIVAL TIMES OF THE FORWARDED REQUESTS, IN MS", cells_, now is not None)]

    steps.append((picture(None), "The limiter keeps a log: the arrival time of every request it forwarded during the last second. "
                  "The log has room for 5 times, because the limit is 5."))

    for now in ARRIVALS:
        log[:] = [time for time in log if time + 1000 > now]
        passed = len(log) < 5
        held = len(log)

        if passed:
            log.append(now)

        seen.append((now, passed))
        oldest = "No entry is older than 1 second, so none is removed. " if held else ""
        said = ("At %d ms. %s" % (now, oldest)
                + ("The log holds %d entries, fewer than 5, so %d is added: forwarded." % (held, now) if passed
                   else "The log holds 5 entries, all from the last second: refused. A refused request is not logged."))
        steps.append((picture(now), said))

    steps.append((picture(None), "5 of 11 requests were forwarded. The next request can pass at 1600 ms, when the entry 600 becomes "
                  "1 second old and is removed. No span of 1 second ever contains more than 5 forwarded requests."))
    frames("steps-limiter-log", "Sliding window log", steps)


@figure
def steps_limiter_counter():
    steps, counts, seen = [], {-1: 0, 0: 0, 1: 0}, []

    def picture(now, formula):
        window = 0 if now is None else now // 1000
        left = panel(32, 196, 200, "PREVIOUS WINDOW", slots(44, 228, counts[window - 1], "idle"), False)
        right = panel(248, 196, 200, "CURRENT WINDOW", slots(260, 228, counts[window], "client"), now is not None)
        return [timeline(150, 500, 1500, marks_until(seen), now, [1000], "REQUESTS OF 1 CLIENT"), left, right,
                text(240, 290, formula, "mono strong", "middle")]

    steps.append((picture(None, "estimate = previous x overlap + current"),
                  "The limiter keeps 2 counts: the window before, and the current window. From them it estimates how many "
                  "requests the last second contained."))

    for now in ARRIVALS:
        window, into = now // 1000, now % 1000
        overlap = (1000 - into) / 1000
        estimate = counts[window - 1] * overlap + counts[window]
        passed = estimate + 1 <= 5
        formula = "estimate = %d x %.2f + %d = %.2f" % (counts[window - 1], overlap, counts[window], estimate)
        counts[window] += passed
        seen.append((now, passed))
        said = ("At %d ms, the current window is %d ms old, so the last second still covers %d%% of the previous window. "
                % (now, into, round(overlap * 100))
                + ("The estimate is %.2f. With this request it is %.2f, within 5: forwarded." % (estimate, estimate + 1) if passed
                   else "The estimate is %.2f. With this request it would be %.2f, above 5: refused." % (estimate, estimate + 1)))
        steps.append((picture(now, formula), said))

    steps.append((picture(None, "forwarded: 600 700 800 900 950 and 1250"),
                  "6 of 11 requests were forwarded: 1 more than the log allowed. At 1250 ms the estimate was 3.75, yet all 5 "
                  "earlier requests lay inside the last second. The estimate assumes they were spread evenly over their window."))
    frames("steps-limiter-counter", "Sliding window counter", steps, 414, 314)


@figure
def steps_limiter_token():
    steps, seen, tokens, updated = [], [], 5.0, 600

    def picture(now, amount):
        bucket = slots(44, 228, amount, "store", w=58) + "\n" + text(436, 246, "%.2f tokens" % amount, "mono strong", "end")
        return [timeline(150, 500, 1500, marks_until(seen), now, [], "REQUESTS OF 1 CLIENT"),
                panel(32, 196, 416, "BUCKET: UP TO 5 TOKENS, 1 NEW TOKEN EVERY 200 MS", bucket, now is not None)]

    steps.append((picture(None, 5.0), "The limiter keeps a bucket of tokens for the client. The client has been quiet, so the bucket "
                  "is full: 5 tokens. Every request must take 1 token, and 1 new token arrives every 200 ms."))

    for now in ARRIVALS:
        gained = (now - updated) / 200
        filled = min(tokens + gained, 5.0)
        passed = filled >= 1
        tokens, updated = filled - passed, now
        seen.append((now, passed))
        refill = ("%d ms have passed, which adds %.2f tokens: %.2f in the bucket. " % (round(gained * 200), gained, filled)
                  if gained else "The bucket holds %.2f tokens. " % filled)
        said = ("At %d ms. " % now + refill
                + ("The request takes 1 token: forwarded, and %.2f tokens remain." % tokens if passed
                   else "That is less than 1 token: refused. The bucket keeps its %.2f tokens." % tokens))
        steps.append((picture(now, tokens), said))

    times = [time for time, passed in seen if passed]
    steps.append((picture(None, tokens), "%d of 11 requests were forwarded: the 5 tokens of the full bucket, and %d more that arrived "
                  "during these 650 ms. A token bucket allows its capacity as a burst, and its rate on top of that."
                  % (len(times), len(times) - 5)))
    frames("steps-limiter-token", "Token bucket", steps)


@figure
def steps_limiter_leaky():
    steps, seen, leaves, free_at = [], [], [], 0

    def picture(now):
        waiting = [time for time in leaves if now is not None and time > now]
        out = [(time, "ok" if now is None or time <= now else "wait") for time in leaves]
        queue = slots(44, 300, len(waiting), "store", w=58) + "\n" + text(436, 318, "%d waiting" % len(waiting), "mono strong", "end")
        return [timeline(150, 500, 2300, marks_until(seen), now, [], "REQUESTS ARRIVE", 5),
                timeline(240, 500, 2300, out, now, [], "REQUESTS LEAVE FOR THE API, 1 EVERY 200 MS", 5),
                panel(32, 268, 416, "QUEUE: UP TO 5 REQUESTS WAIT FOR THEIR TURN", queue, now is not None)]

    steps.append((picture(None), "The limiter keeps a queue with 5 places. Requests leave the queue for the API at a fixed pace: "
                  "1 every 200 ms. A request that finds the queue full is refused."))

    for now in ARRIVALS:
        turn = max(now, free_at)
        wait = turn - now
        passed = wait < 1000

        if passed:
            leaves.append(turn)
            free_at = turn + 200

        seen.append((now, passed))
        said = ("At %d ms, the next free turn to leave is at %d ms. " % (now, turn)
                + (("The request leaves at once." if wait == 0 else "The request joins the queue and waits %d ms." % wait) if passed
                   else "A wait of %d ms means 5 requests are already queued: refused." % wait))
        steps.append((picture(now), said))

    steps.append((picture(None), "%d of 11 requests were accepted. They arrived in a clump within 650 ms and left evenly spaced, "
                  "1 every 200 ms, until %d ms. The API never saw more than 5 requests in any second." % (len(leaves), leaves[-1])))
    frames("steps-limiter-leaky", "Leaky bucket", steps, 468, 368)


@figure
def limiter_boundary():
    lo, hi = 500, 1500
    early, late = range(900, 1000, 20), range(1000, 1100, 20)
    parts = [box(48, 108, 192, 62, KINDS["client"][1], KINDS["client"][0], 8), box(240, 108, 192, 62, KINDS["service"][1], KINDS["service"][0], 8),
             text(60, 128, "window 0: count 5 of 5", "pill", fill=KINDS["client"][0]), text(252, 128, "window 1: count 5 of 5", "pill", fill=KINDS["service"][0]),
             timeline(190, lo, hi, [(time, "ok") for time in [*early, *late]], None, [1000], None, 3.4)]
    a, b = at(900, lo, hi) - 6, at(1080, lo, hi) + 6
    parts += [f'  <path d="M{a:.1f},224 V232 H{b:.1f} V224" fill="none" stroke="{BAD}" stroke-width="2"/>',
              text((a + b) / 2, 250, "10 requests in 180 ms", "pill", "middle", BAD),
              lines(32, 282, ["Each window counted 5 requests, so neither refused anything.", "The server received 10 requests in less than a fifth of a second."], "sub")]
    save(OUT / "limiter-boundary.svg", WIDTH, 322,
         "A time axis with 2 windows of 1 second. 5 requests arrive in the last 100 ms of window 0 and 5 in the first 100 ms of "
         "window 1. Each window counts 5 of 5, so all 10 requests are forwarded within 180 ms.",
         "A burst across a window boundary", "The limit is 5 requests per second.", parts)


@figure
def limiter_overlap():
    lo, hi = 0, 2000
    a, b = at(250, lo, hi), at(1250, lo, hi)
    grey, blue = KINDS["idle"][0], KINDS["client"][0]
    parts = [box(48, 100, 192, 50, KINDS["idle"][1], grey, 8), box(240, 100, 192, 50, KINDS["client"][1], blue, 8),
             text(60, 120, "previous window", "pill", fill=grey), text(60, 139, "count 5", "mono strong"),
             text(252, 120, "current window", "pill", fill=blue), text(252, 139, "count 0", "mono strong"),
             timeline(226, lo, hi, [(time, "ok") for time in ARRIVALS[:5]], 1250, [1000], None, 3.4),
             f'  <path d="M{a:.1f},264 V272 H240 V264" fill="none" stroke="{grey}" stroke-width="2.4"/>',
             f'  <path d="M240,264 V272 H{b:.1f} V264" fill="none" stroke="{blue}" stroke-width="2.4"/>',
             text(a, 292, "the last second covers 75% of the previous window", "pill", "start", grey),
             text(a, 311, "and 25% of the current window", "pill", "start", blue),
             box(32, 328, 416, 34, "#EEF2F7", EDGE, 8), text(240, 350, "estimate = 5 x 0.75 + 0 = 3.75", "mono strong", "middle"),
             lines(32, 388, ["The bracket under the axis is the last second, seen from 1250 ms.", "It contains all 5 requests. The estimate says 3.75, because it",
                             "treats the 5 requests as if they were spread evenly over the", "previous window."], "sub")]
    save(OUT / "limiter-overlap.svg", WIDTH, 458,
         "A time axis with a previous window that counted 5 requests and a current window that has counted 0. At 1250 ms the "
         "last second covers 75% of the previous window and 25% of the current window. The estimate is 5 times 0.75 plus 0, "
         "which is 3.75, although all 5 requests lie inside the last second.",
         "The estimate of the sliding counter", "The limit is 5 requests per second. Now is 1250 ms.", parts)


@figure
def limiter_token_bucket():
    amber, tint = KINDS["store"]
    coin = lambda cx, cy: (f'  <circle cx="{cx}" cy="{cy}" r="13" fill="{tint}" stroke="{amber}" stroke-width="2"/>\n'
                           + text(cx, cy + 4, "1", "pill", "middle", amber))
    parts = [card(130, 96, 220, 50, "store", "Refill", ["1 token every 200 ms"], glyph="clock"),
             wire([(240, 146), (240, 186)]),
             f'  <path d="M176,186 V330 Q176,342 188,342 H292 Q304,342 304,330 V186" fill="{CARD}" stroke="{INK}" stroke-width="2.4"/>',
             coin(208, 318), coin(240, 318), coin(272, 318), coin(224, 292), coin(256, 292),
             text(318, 206, "capacity 5", "name"), text(318, 224, "the largest burst", "sub"), text(318, 241, "that is forwarded", "sub"),
             text(162, 206, "full bucket:", "name", "end"), text(162, 224, "new tokens are", "sub", "end"), text(162, 241, "thrown away", "sub", "end"),
             wire([(240, 342), (240, 388)]),
             card(100, 388, 280, 50, "client", "A request takes 1 token", ["no token: it is refused"], glyph="laptop"),
             lines(32, 468, ["Rate decides how many requests pass over a long time.", "Capacity decides how many may pass in the same instant."], "sub")]
    save(OUT / "limiter-token-bucket.svg", WIDTH, 508,
         "A bucket that holds up to 5 tokens. A refill adds 1 token every 200 ms, and a token that arrives at a full bucket is "
         "thrown away. Each request takes 1 token from the bucket, and a request that finds no token is refused.",
         "The token bucket", "2 numbers: a rate and a capacity.", parts)


@figure
def limiter_shapes():
    stack = lambda y: "\n".join(dot(at(0, 0, 1000), y - 14 - 13 * k, "ok", 5) for k in range(5))
    parts = [text(40, 104, "ARRIVING: 20 REQUESTS IN THE SAME INSTANT", "tab"),
             timeline(190, 0, 1000, [], None, [], None),
             "\n".join(dot(at(0, 0, 1000) + 11 * column, 176 - 13 * row, "ok" if (column, row) == (0, 0) or column * 5 + row < 5 else "no", 5)
                       for column in range(4) for row in range(5)),
             text(40, 250, "TOKEN BUCKET FORWARDS: 5 IN THE SAME INSTANT", "tab"),
             timeline(336, 0, 1000, [], None, [], None), stack(336),
             text(40, 396, "LEAKY BUCKET FORWARDS: 1 EVERY 200 MS", "tab"),
             timeline(442, 0, 1000, [(time, "ok") for time in range(0, 1000, 200)], None, [], None, 5),
             lines(32, 496, ["Both forward 5 requests and refuse 15. The token bucket passes the", "burst on to the API. The leaky bucket spreads it out."], "sub")]
    save(OUT / "limiter-shapes.svg", WIDTH, 536,
         "3 time axes. On the first, 20 requests arrive in the same instant. On the second, a token bucket forwards 5 of them "
         "in that instant. On the third, a leaky bucket forwards 5 of them at 0, 200, 400, 600 and 800 ms.",
         "The same burst through 2 buckets", "Green is forwarded. A red cross is refused.", parts)


@figure
def limiter_race():
    rows, bottom = step_rows(100, [
        ("client", "Limiter node A reads the bucket", "tokens = 1"),
        ("service", "Limiter node B reads the bucket", "tokens = 1, the value that A also saw"),
        ("client", "Node A writes tokens = 0", "and forwards its request"),
        ("service", "Node B writes tokens = 0", "and forwards its request"),
        ("danger", "2 requests passed, and 1 token was taken", "the limit was exceeded without any error"),
    ])
    parts = [rows, chip(32, bottom + 6, 416, "The cure: the store refills and takes the token in 1 operation", "good"),
             lines(32, bottom + 62, ["Between a read and a write, another node can act on the old value.", "With 1 operation there is no moment in between."], "sub")]
    save(OUT / "limiter-race.svg", WIDTH, bottom + 100,
         "5 steps. Limiter node A reads the bucket and sees 1 token. Node B reads the bucket and sees the same token. Node A "
         "writes 0 tokens and forwards its request. Node B writes 0 tokens and forwards its request. 2 requests passed and 1 "
         "token was taken. The cure is for the store to refill and take the token in 1 operation.",
         "2 limiter nodes and 1 token", "2 requests of 1 client arrive at the same moment.", parts)


# ------------------------------------------------ chapter 8: unique ids

@figure
def idgen_layout():
    blue, green, amber, grey = KINDS["client"][0], KINDS["service"][0], KINDS["store"][0], KINDS["idle"][0]
    parts = [stacked(32, 104, 416, 46, [(3, grey, ""), (41, blue, ""), (10, green, ""), (12, amber, "")]),
             text(32, 172, "1 bit, always 0", "pill", fill=grey), text(170, 172, "time: 41 bits", "pill", fill=blue), text(318, 172, "node: 10", "pill", "middle", green), text(448, 172, "counter: 12", "pill", "end", amber),
             lines(32, 204, ["The first bit is left at 0, so that the id is a positive number", "in languages whose 64-bit integers are signed."], "sub"),
             box(32, 250, 416, 118, CARD, EDGE, 10), text(44, 272, "AN ID TAKEN APART", "tab"),
             text(44, 296, "time     1000 ms since the service's own start date", "mono"),
             text(44, 316, "node     1", "mono"), text(44, 336, "counter  2", "mono"),
             text(44, 356, "id       1000 x 4194304 + 1 x 4096 + 2 = 4194308098", "mono strong"),
             lines(32, 396, ["Multiplying by 4194304 moves the time 22 bits to the left, past the", "node and the counter. The time is therefore the most significant",
                             "part, and ids sort in the order in which they were made."], "sub")]
    save(OUT / "idgen-layout.svg", WIDTH, 450,
         "A 64-bit id divided into 4 fields from the most significant bit: 1 bit that is always 0, 41 bits of time in "
         "milliseconds, 10 bits for the number of the node, and 12 bits for a counter. An example with time 1000, node 1 and "
         "counter 2 gives the id 4194308098.",
         "The layout of an id", "3 numbers side by side in 1 integer.", parts)


@figure
def idgen_locality():
    pages = ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8"]
    parts = [text(32, 106, "RANDOM IDS: EACH INSERT LANDS ON A DIFFERENT PAGE", "tab"),
             cells(40, 118, pages, "idle", 44, 34, hot=(0, 2, 3, 5, 6, 7)),
             lines(32, 176, ["A new row belongs wherever its random id falls in the sorted index.", "Nearly every page is written and has to be kept in memory."], "sub"),
             text(32, 236, "TIME-ORDERED IDS: EVERY INSERT LANDS ON THE LAST PAGE", "tab"),
             cells(40, 248, pages, "idle", 44, 34, hot=(7,)),
             lines(32, 306, ["A new row has the largest id so far and is appended at the end.", "Only the last page is being written, and the rest can stay on disk."], "sub")]
    save(OUT / "idgen-locality.svg", WIDTH, 344,
         "2 rows of 8 index pages. With random ids, inserts land on 6 different pages scattered across the index. With "
         "time-ordered ids, every insert lands on the last page.",
         "Where a new row goes in an index", "A red page is one that recent inserts have written.", parts)


@figure
def idgen_ranges():
    rows, bottom = step_rows(100, [
        ("store", "The coordinator's counter stands at 1", "it is the only durable state"),
        ("client", "Node A asks for a block", "it receives 1 to 1000, and the counter moves to 1001"),
        ("service", "Node B asks for a block", "it receives 1001 to 2000, and the counter is now 2001"),
        ("client", "Both nodes give out ids from memory", "A: 1, 2, 3 ...   B: 1001, 1002 ..."),
        ("danger", "Node A crashes after giving out 37", "38 to 1000 are never used: a gap in the numbers"),
    ])
    parts = [rows, lines(32, bottom + 16, ["No number is in 2 blocks, so every id is unique. The order of ids", "no longer follows time: B's 1001 may be older than A's 37."], "sub")]
    save(OUT / "idgen-ranges.svg", WIDTH, bottom + 56,
         "5 steps. The coordinator's counter stands at 1. Node A asks for a block and receives 1 to 1000. Node B asks for a "
         "block and receives 1001 to 2000. Both nodes give out ids from memory. Node A crashes after giving out 37 ids, and "
         "the numbers 38 to 1000 are never used.",
         "Ids from blocks of numbers", "Each node fetches a block and spends it locally.", parts)


@figure
def steps_idgen_make():
    state = {1: [None, 0], 2: [None, 0]}
    made, steps = [], []

    def picture(active):
        show = lambda node: ["last time  %s" % ("none yet" if state[node][0] is None else "%d ms" % state[node][0]), "counter    %d" % state[node][1]]
        return [("NODE 1", show(1), active == 1), ("NODE 2", show(2), active == 2),
                ("IDS MADE SO FAR, WRITTEN AS TIME - NODE - COUNTER", (made[-5:] + [""] * 5)[:5], False)]

    steps.append((picture(None), "2 nodes, each with its own number. Neither will ever send the other a message. Each remembers the "
                  "millisecond of the last id it made and a counter within that millisecond."))
    events = [(1, 1000), (1, 1000), (2, 1000), (1, 1000), (2, 1001), (1, 1001)]

    for node, now in events:
        last, counter = state[node]
        counter = counter + 1 if now == last else 0
        state[node] = [now, counter]
        made.append("%d - %d - %d" % (now, node, counter))
        why = ("Its clock still reads %d ms, the millisecond of its last id, so the counter rises to %d." % (now, counter) if now == last
               else "Its clock reads %d ms, a millisecond in which it has made no id, so the counter starts at 0." % now)
        steps.append((picture(node), "Node %d is asked for an id. %s The id is %s." % (node, why, made[-1])))

    steps.append((picture(None), "6 ids, all different. Ids of 1 node in 1 millisecond differ in the counter, ids of 2 nodes differ in "
                  "the node number, and ids from different milliseconds differ in the time."))
    story("steps-idgen-make", "Ids from 2 nodes", steps)


@figure
def steps_idgen_clock():
    panel_ = lambda clock, last, counter, note: [("NODE 1", ["clock      %d ms" % clock, "last time  %d ms" % last, "counter    %d" % counter], True),
                                                ("WHAT THE NODE ANSWERS", [note], False)]
    story("steps-idgen-clock", "A clock that is set back", [
        (panel_(2000, 2000, 0, "> id 2000 - 1 - 0"), "The node makes an id at 2000 ms and remembers that time."),
        (panel_(1997, 2000, 0, ""), "The machine's clock is corrected. It had been running 3 ms fast, and the correction sets it back to 1997 ms."),
        (panel_(1997, 2000, 0, "! refused: the clock is behind the last id"),
         "A request arrives. The clock reads 1997 ms, which is earlier than the time of the last id. An id made now could repeat one "
         "that was made the first time the clock showed 1997 ms, so the node refuses."),
        (panel_(1999, 2000, 0, "! refused: the clock is behind the last id"), "2 ms later the clock reads 1999 ms. It is still behind, and the node still refuses."),
        (panel_(2000, 2000, 1, "> id 2000 - 1 - 1"), "The clock reaches 2000 ms again. This is the millisecond of the last id, so the counter continues from where it stopped: 1."),
        (panel_(2001, 2001, 0, "> id 2001 - 1 - 0"), "At 2001 ms the node is in a millisecond it has never used, and carries on as usual. No id was made twice, at the cost of 3 ms without ids."),
    ])


# ------------------------------------------------ chapter 9: cache

CACHE_REQUESTS = ["A", "A", "A", "B", "C", "D", "A"]


@figure
def steps_cache_lru():
    held, steps = [], []
    show = lambda: [("position %d   %s" % (k + 1, held[k] if k < len(held) else "empty")) for k in range(3)]
    steps.append(([("REQUEST", [""], False), ("CACHE: 3 PLACES, MOST RECENTLY USED FIRST", show(), False)],
                  "A cache with room for 3 entries, empty at the start. It keeps its entries in order of use, and when it needs room it removes the entry at the bottom, which was used longest ago."))

    for key in CACHE_REQUESTS:
        hit = key in held
        evicted = None if hit or len(held) < 3 else held[-1]
        held[:] = [key] + [other for other in held if other != key][:2]
        outcome = "> get %s: found in the cache" % key if hit else "! get %s: not in the cache, read from the database" % key
        said = ("%s is in the cache. It moves to position 1, because it is now the most recently used entry." % key if hit
                else "%s is not in the cache, so it is read from the database and stored at position 1.%s"
                % (key, " The cache was full, and %s, at the bottom, is removed to make room." % evicted if evicted else ""))
        steps.append(([("REQUEST", [outcome], True), ("CACHE: 3 PLACES, MOST RECENTLY USED FIRST", show(), False)], said))

    steps.append(([("REQUEST", ["4 of 7 requests were read from the database"], False), ("CACHE: 3 PLACES, MOST RECENTLY USED FIRST", show(), False)],
                  "A had been requested 3 times, more than any other key, and was removed all the same, because B, C and D arrived after it. The rule looks only at how recently an entry was used."))
    story("steps-cache-lru", "Least recently used", steps)


@figure
def steps_cache_lfu():
    counts, steps = {}, []
    show = lambda: (["%s   used %d time%s" % (key, counts[key], "" if counts[key] == 1 else "s") for key in counts] + ["empty"] * 3)[:3]
    steps.append(([("REQUEST", [""], False), ("CACHE: 3 PLACES, EACH WITH A COUNT OF ITS USES", show(), False)],
                  "The same cache with a different rule. Each entry carries a count of how often it has been used, and when room is needed the entry with the lowest count is removed."))

    for key in CACHE_REQUESTS:
        hit = key in counts
        evicted = None

        if not hit and len(counts) == 3:
            evicted = min(counts, key=counts.get)
            del counts[evicted]

        counts[key] = counts.get(key, 0) + 1
        outcome = "> get %s: found in the cache" % key if hit else "! get %s: not in the cache, read from the database" % key
        said = ("%s is in the cache, and its count rises to %d." % (key, counts[key]) if hit
                else "%s is not in the cache, so it is read from the database and stored with a count of 1.%s"
                % (key, " The cache was full, and %s, whose count was the lowest, is removed." % evicted if evicted else ""))
        steps.append(([("REQUEST", [outcome], True), ("CACHE: 3 PLACES, EACH WITH A COUNT OF ITS USES", show(), False)], said))

    steps.append(([("REQUEST", ["3 of 7 requests were read from the database"], False), ("CACHE: 3 PLACES, EACH WITH A COUNT OF ITS USES", show(), False)],
                  "A survived, because its count of 3 protected it, and the last request found it in the cache. The rule looks at how often an entry was used and ignores how long ago."))
    story("steps-cache-lfu", "Least frequently used", steps)


@figure
def steps_cache_race():
    frame_ = lambda db, cache, one, other, active: [("DATABASE", ["price of item 7 = %s" % db], active == "db"), ("CACHE", [("! item 7 = %s" % cache[2:]) if cache.startswith("! ") else "item 7 = %s" % cache], active == "cache"),
                                                   ("REQUEST 1, A READ", [one], False), ("REQUEST 2, A WRITE", [other], False)]
    story("steps-cache-race", "A stale value that stays", [
        (frame_("10", "(no entry)", "", "", None), "The database holds a price of 10 for item 7. The cache has no entry for it, perhaps because the entry has expired. 2 requests are about to arrive almost together."),
        (frame_("10", "(no entry)", "> looks in the cache: nothing", "", "cache"), "Request 1 wants to read the price. It looks in the cache first and finds nothing."),
        (frame_("10", "(no entry)", "> reads the database: 10", "", "db"), "Request 1 therefore reads the database and receives 10. It now intends to put 10 into the cache, and at this moment it is delayed for a few milliseconds."),
        (frame_("12", "(no entry)", "holds 10, has not stored it yet", "> writes 12 to the database", "db"), "Request 2 changes the price. It writes 12 to the database."),
        (frame_("12", "(no entry)", "holds 10, has not stored it yet", "> deletes the cache entry", "cache"), "Following the usual rule, request 2 then deletes the cache entry, so that the next reader fetches the new price. There is no entry to delete."),
        (frame_("12", "! 10", "! stores 10 in the cache", "finished", "cache"), "Request 1 resumes and stores what it read: 10. The cache now holds a price that the database replaced a moment ago."),
        (frame_("12", "! 10", "finished", "finished", None), "Every reader from now on receives 10 from the cache. Nothing will correct the entry until it expires or the price changes again. A time limit on every entry bounds how long this can last."),
    ])


@figure
def cache_stampede():
    rows, bottom = step_rows(100, [
        ("store", "A popular entry expires", "it was being read 500 times per second"),
        ("client", "500 requests find nothing in the cache", "all within the same second"),
        ("danger", "All 500 ask the database", "for the same row, each unaware of the others"),
        ("danger", "The database slows under the load", "and the 500 answers take longer to arrive"),
        ("danger", "New requests keep missing meanwhile", "since the cache is still empty"),
    ])
    parts = [rows, chip(32, bottom + 6, 416, "The cure: 1 request fetches the value, and the others wait for it", "good")]
    save(OUT / "cache-stampede.svg", WIDTH, bottom + 56,
         "5 steps. A popular entry that was being read 500 times per second expires. 500 requests find nothing in the cache. "
         "All 500 ask the database for the same row. The database slows under the load. New requests keep missing while the "
         "cache is still empty. The cure is for 1 request to fetch the value while the others wait for it.",
         "A stampede on 1 expired entry", "What happens when many readers miss together.", parts)


@figure
def cache_latency():
    parts = [text(32, 104, "AVERAGE TIME OF A READ", "tab")]

    for k, (share, value) in enumerate([(0, 20.0), (50, 10.5), (90, 2.9), (99, 1.19)]):
        y = 132 + 52 * k
        kind = "danger" if share == 0 else "store" if share == 50 else "service" if share == 90 else "good"
        parts += [text(32, y - 8, "%d%% of reads answered by the cache" % share, "name"), text(448, y - 8, "%s ms" % value, "mono strong", "end"),
                  box(32, y, 416, 18, CARD, EDGE, 6), box(32, y, max(8, 416 * value / 20), 18, KINDS[kind][1], KINDS[kind][0], 6)]

    parts.append(lines(32, 348, ["A cache read takes 1 ms and a database read takes 20 ms.", "Going from 90% to 99% halves the average, and also divides the",
                                 "number of reads that reach the database by 10."], "sub"))
    save(OUT / "cache-latency.svg", WIDTH, 402,
         "4 bars of the average time of a read when a cache read takes 1 ms and a database read 20 ms. With 0% of reads "
         "answered by the cache the average is 20 ms, with 50% it is 10.5 ms, with 90% it is 2.9 ms, and with 99% it is 1.19 ms.",
         "What the hit ratio is worth", "The same system at 4 hit ratios.", parts)


# ------------------------------------------------ chapter 10: lock

@figure
def steps_lock_fencing():
    f = lambda t, lock, a, b, storage, active: [("TIME", ["t = %d s" % t], False), ("LOCK SERVICE", lock, active == "lock"),
                                                ("WORKER A", [a], active == "a"), ("WORKER B", [b], active == "b"), ("STORAGE", storage, active == "storage")]
    held = lambda who, token, until: ["holder %s, token %d" % (who, token), "lease ends at t = %d s" % until]
    free = ["holder none", "last token given: 1"]
    story("steps-lock-fencing", "A paused worker and a fencing token", [
        (f(0, held("A", 1, 10), "> holds the lock, token 1", "waiting", ["highest token seen: none", "contents: empty"], "lock"),
         "Worker A asks for the lock and receives it for 10 seconds, together with the token 1. The token is a number that the lock service raises by 1 each time it grants the lock."),
        (f(2, held("A", 1, 10), "! paused: the process has stopped running", "waiting", ["highest token seen: none", "contents: empty"], "a"),
         "At 2 seconds worker A stops running. Its process has been suspended, for example by a long pause for memory management. A does not know this, because a suspended process does not know anything."),
        (f(10, free, "! paused", "waiting", ["highest token seen: none", "contents: empty"], "lock"),
         "At 10 seconds the lease ends without having been renewed. The lock service considers the lock free. This is the purpose of a lease: a holder that has vanished cannot block everyone else for ever."),
        (f(12, held("B", 2, 22), "! paused", "> holds the lock, token 2", ["highest token seen: none", "contents: empty"], "lock"),
         "Worker B asks for the lock and receives it with the next token, 2."),
        (f(13, held("B", 2, 22), "! paused", "> writes with token 2", ["highest token seen: 2", "contents: written by B"], "storage"),
         "B writes to the storage and presents its token. The storage has seen no higher token, so it accepts the write and remembers 2."),
        (f(17, held("B", 2, 22), "> awake, believes it holds the lock", "holds the lock, token 2", ["highest token seen: 2", "contents: written by B"], "a"),
         "Worker A resumes at 17 seconds, exactly where it stopped. From its point of view no time has passed. It checked the lock before the pause, and it is about to write."),
        (f(17, held("B", 2, 22), "! writes with token 1: refused", "holds the lock, token 2", ["highest token seen: 2", "contents: written by B"], "storage"),
         "A writes with token 1. The storage has already seen token 2 and refuses the lower one. Without the token, the storage could not have told A's late write from a legitimate one, and B's work would have been overwritten."),
    ])


@figure
def steps_lock_release():
    f = lambda lock, a, b, c, active: [("LOCK IN THE STORE", [lock], active == "lock"), ("WORKER A", [a], active == "a"),
                                       ("WORKER B", [b], active == "b"), ("WORKER C", [c], active == "c")]
    story("steps-lock-release", "Releasing another worker's lock", [
        (f("held by A, expires in 10 s", "> working", "waiting", "waiting", "lock"), "Worker A holds the lock with a lease of 10 seconds and begins a piece of work that it expects to take 5."),
        (f("free: A's lease has ended", "! still working, slower than expected", "waiting", "waiting", "lock"), "The work takes longer than 10 seconds. The lease ends while A is still busy."),
        (f("held by B, expires in 10 s", "! still working", "> working", "waiting", "b"), "Worker B acquires the lock, quite properly, and starts its own work."),
        (f("! deleted by A", "> finished: deletes the lock", "! working, believes it holds the lock", "waiting", "a"),
         "A finishes and releases the lock by deleting it. The lock it deletes is the one that B now holds, because the delete names only the lock and does not say whose lock it expects to find."),
        (f("held by C, expires in 10 s", "finished", "! working", "! working", "c"),
         "Worker C finds the lock free and acquires it. B and C are now working at the same time, each with good reason to believe that it is alone."),
        (f("held by C, expires in 10 s", "finished", "! working", "! working", None),
         "The cure is for a release to state its holder: delete this lock only if it is still mine. A's delete would then have found B's name on the lock and done nothing."),
    ])


@figure
def lock_failover():
    rows, bottom = step_rows(100, [
        ("client", "Worker A acquires the lock on the leader", "the leader confirms at once"),
        ("danger", "The leader fails before copying the lock", "its follower has never heard of the lock"),
        ("store", "The follower becomes the leader", "in its copy, the lock is free"),
        ("service", "Worker B acquires the same lock", "from the new leader, which sees no holder"),
        ("danger", "A and B both hold the lock", "and neither has been told of any problem"),
    ])
    parts = [rows, chip(32, bottom + 6, 416, "The cure: confirm a lock only when a majority has stored it", "good")]
    save(OUT / "lock-failover.svg", WIDTH, bottom + 56,
         "5 steps. Worker A acquires the lock on the leader, which confirms at once. The leader fails before it has copied the "
         "lock to its follower. The follower becomes the leader, and in its copy the lock is free. Worker B acquires the same "
         "lock from the new leader. A and B both hold the lock. The cure is to confirm a lock only when a majority has stored it.",
         "A lock lost in a failover", "A lock store that copies to its follower after confirming.", parts)


# ------------------------------------------------ chapter 11: message queue

QUEUE_LOG = ["offset 0   order-7 created", "offset 1   order-8 created", "offset 2   order-7 paid"]


def queue_frame(committed, consumer, done, active):
    return [("PARTITION: A LOG OF MESSAGES", QUEUE_LOG, False), ("COMMITTED OFFSET OF THE GROUP billing", ["%d" % committed], active == "offset"),
            ("CONSUMER", [consumer], active == "consumer"), ("INVOICES SENT", done or ["none"], active == "work")]


@figure
def steps_queue_after():
    story("steps-queue-after", "Commit after the work: at least once", [
        (queue_frame(0, "starts, and asks where the group stopped", [], "offset"), "A consumer of the group billing starts. The committed offset is 0, so it begins with the message at offset 0. Its job is to send an invoice for each created order."),
        (queue_frame(0, "> reads offset 0 and sends an invoice", ["invoice for order-7"], "work"), "It reads the message at offset 0 and does the work: an invoice for order 7 goes out. It has not yet committed anything."),
        (queue_frame(0, "> reads offset 1 and sends an invoice", ["invoice for order-7", "invoice for order-8"], "work"), "It continues with offset 1 and sends an invoice for order 8."),
        (queue_frame(0, "! crashes before committing", ["invoice for order-7", "invoice for order-8"], "consumer"), "The consumer intended to commit offset 2 next, to record that everything before it is done. It crashes first. The committed offset is still 0."),
        (queue_frame(0, "> restarts, and reads from offset 0 again", ["invoice for order-7", "invoice for order-8", "! invoice for order-7, a second time"], "work"),
         "A replacement starts and asks where the group stopped. The answer is 0, so it reads offset 0 again and sends a second invoice for order 7. No message was lost, and 2 were processed twice."),
        (queue_frame(3, "reads offsets 1 and 2, then commits 3", ["invoice for order-7", "invoice for order-8", "! invoice for order-7, a second time", "! invoice for order-8, a second time"], "offset"),
         "It finishes the partition and commits offset 3. Every message was acted on at least once. Duplicates are the price, and the consumer has to be built to tolerate them."),
    ])


@figure
def steps_queue_before():
    story("steps-queue-before", "Commit before the work: at most once", [
        (queue_frame(0, "starts, and asks where the group stopped", [], "offset"), "The same consumer, with the 2 steps in the other order: it will commit first and do the work afterwards."),
        (queue_frame(1, "> reads offset 0 and commits 1", [], "offset"), "It reads the message at offset 0 and at once commits offset 1, which declares the message handled."),
        (queue_frame(1, "> sends the invoice", ["invoice for order-7"], "work"), "It then sends the invoice for order 7. So far the result is the same as before."),
        (queue_frame(2, "> reads offset 1 and commits 2", ["invoice for order-7"], "offset"), "It reads offset 1 and commits offset 2."),
        (queue_frame(2, "! crashes before sending the invoice", ["invoice for order-7"], "consumer"), "It crashes before the invoice for order 8 has gone out. The committed offset already says that offset 1 is done."),
        (queue_frame(2, "> restarts, and reads from offset 2", ["invoice for order-7", "! order-8 is never invoiced"], "work"),
         "The replacement starts at offset 2. Nobody will ever read offset 1 again, and order 8 receives no invoice. Nothing was done twice, and 1 message was lost."),
    ])


@figure
def queue_partitions():
    blue, green, amber = "client", "service", "store"
    parts = [text(32, 104, "MESSAGES IN THE ORDER THEY WERE PUBLISHED", "tab"),
             cells(40, 116, ["7 new", "8 new", "7 paid", "9 new", "7 sent"], "idle", 72, 30),
             text(32, 186, "PARTITION 0: KEYS WHOSE HASH IS EVEN", "tab"), cells(40, 198, ["8 new"], green, 72, 30),
             text(32, 264, "PARTITION 1: KEYS WHOSE HASH IS ODD", "tab"), cells(40, 276, ["7 new", "7 paid", "9 new", "7 sent"], blue, 72, 30),
             lines(32, 340, ["Every message about order 7 is in partition 1, in its original order:", "new, paid, sent. Between partitions there is no order: nothing says",
                             "whether 8 new was published before or after 7 paid."], "sub")]
    save(OUT / "queue-partitions.svg", WIDTH, 394,
         "5 messages in the order they were published: order 7 new, order 8 new, order 7 paid, order 9 new, order 7 sent. "
         "Partition 0 receives order 8 new. Partition 1 receives order 7 new, order 7 paid, order 9 new and order 7 sent, in that order.",
         "The key chooses the partition", "Messages with the same key keep their order.", parts)


@figure
def steps_queue_group():
    f = lambda rows, note, active: [("PARTITIONS AND THE CONSUMER THAT READS EACH", rows, active), ("WHAT HAPPENED", [note], False)]
    story("steps-queue-group", "A consumer group shares the partitions", [
        (f(["partition 0   consumer A", "partition 1   consumer A", "partition 2   consumer A", "partition 3   consumer A"], "consumer A is the only member", False),
         "A topic with 4 partitions and a consumer group with 1 member. That member reads all 4 partitions."),
        (f(["partition 0   consumer A", "partition 1   consumer A", "> partition 2   consumer B", "> partition 3   consumer B"], "> consumer B joins the group", True),
         "A second consumer joins. The partitions are divided again, 2 each. B starts each of its partitions at the offset the group last committed there."),
        (f(["partition 0   consumer A", "> partition 1   consumer C", "partition 2   consumer B", "> partition 3   consumer D"], "> consumers C and D join", True),
         "With 4 members, each reads 1 partition. This is the greatest parallelism the topic allows, because a partition is read by 1 member of a group only."),
        (f(["partition 0   consumer A", "partition 1   consumer C", "partition 2   consumer B", "partition 3   consumer D"], "! consumer E joins and receives nothing", False),
         "A fifth member joins and is given no partition. It waits as a spare. More consumers than partitions add no speed, which is why the number of partitions has to be chosen with future load in mind."),
        (f(["partition 0   consumer A", "> partition 1   consumer E", "partition 2   consumer B", "partition 3   consumer D"], "! consumer C stops sending heartbeats", True),
         "Consumer C crashes. The group notices its silence and gives partition 1 to the spare. E resumes from the committed offset, so the messages C had read without committing are read again."),
    ])


@figure
def queue_outbox():
    rows, bottom = step_rows(100, [
        ("store", "The service opens 1 database transaction", "everything below happens in it, or none of it does"),
        ("store", "It writes the order", "into the orders table"),
        ("store", "It writes the message into an outbox table", "'order-7 created', as an ordinary row"),
        ("good", "The transaction commits", "the order and the message now exist together"),
        ("client", "A relay reads the outbox and publishes", "then marks the row as published"),
    ])
    parts = [rows, lines(32, bottom + 16, ["If the relay crashes after publishing and before marking the row, it", "publishes the message again. The message is published at least once."], "sub")]
    save(OUT / "queue-outbox.svg", WIDTH, bottom + 56,
         "5 steps. The service opens 1 database transaction. It writes the order into the orders table. It writes the message "
         "into an outbox table as an ordinary row. The transaction commits, so the order and the message exist together. A relay "
         "reads the outbox, publishes the message and marks the row as published.",
         "Publishing through an outbox", "How to change a database and publish a message as 1 step.", parts)


# ------------------------------------------------ chapter 12: job scheduler

@figure
def jobs_states():
    parts = [card(140, 100, 200, 50, "idle", "Waiting", ["in the queue"], glyph="clock"),
             card(140, 214, 200, 50, "client", "Running", ["lent to 1 worker"], glyph="gear"),
             card(32, 336, 190, 50, "good", "Succeeded", ["nothing more to do"], glyph="doc"),
             card(258, 336, 190, 50, "danger", "Dead", ["kept for a person"], glyph="eye"),
             wire([(220, 150), (220, 214)]), badge(202, 182, 1),
             wire([(340, 239), (400, 239), (400, 125), (340, 125)]), badge(400, 182, 2),
             wire([(190, 264), (190, 300), (127, 300), (127, 336)]), badge(158, 300, 3),
             wire([(290, 264), (290, 300), (353, 300), (353, 336)]), badge(322, 300, 4)]
    legend_, bottom = legend_steps(420, ["A worker takes the job and receives a lease.", "The job failed, or its lease ran out: it waits again.",
                                         "The worker reported success before its lease ran out.", "The job has failed 5 times and is tried no more."])
    save(OUT / "jobs-states.svg", WIDTH, bottom + 10,
         "The states of a job. A waiting job becomes running when a worker takes it and receives a lease. A running job returns "
         "to waiting when it fails or its lease runs out. A running job becomes succeeded when the worker reports success "
         "before its lease runs out. A running job becomes dead when it has failed 5 times.",
         "The states of a job", "Every job is in exactly 1 of 4 states.", parts + [legend_])


@figure
def steps_jobs_lease():
    f = lambda t, job, one, two, active: [("TIME", ["t = %d s" % t], False), ("JOB 1 IN THE JOB STORE", job, active == "job"),
                                          ("WORKER 1", [one], active == "one"), ("WORKER 2", [two], active == "two")]
    story("steps-jobs-lease", "A worker crashes during a job", [
        (f(0, ["state waiting", "attempts 0"], "idle", "busy with another job", None), "Job 1 is waiting in the store. Each time a worker takes it, the store counts an attempt."),
        (f(0, ["state running, lease 771", "held by worker 1 until t = 3 s", "attempts 1"], "> takes job 1 with lease 771", "busy with another job", "job"),
         "Worker 1 takes the job. The store marks it as running and notes who holds it and until when. The lease lasts 3 seconds."),
        (f(2, ["state running, lease 771", "held by worker 1 until t = 3 s", "attempts 1"], "! crashes", "busy with another job", "one"),
         "Worker 1 crashes. It sends no message about this, since a crashed process sends nothing. In the store the job still appears to be running."),
        (f(3, ["state waiting", "attempts 1"], "gone", "busy with another job", "job"),
         "At 3 seconds the lease runs out. A periodic check in the scheduler finds the expired lease and puts the job back in the queue."),
        (f(4, ["state running, lease 772", "held by worker 2 until t = 7 s", "attempts 2"], "gone", "> takes job 1 with lease 772", "job"),
         "Worker 2 becomes free and takes the job under a new lease, 772. The count of attempts is now 2."),
        (f(6, ["state succeeded", "attempts 2"], "gone", "> reports success with lease 772", "two"),
         "Worker 2 finishes and reports the result together with its lease number. The store finds that lease 772 is the current one and accepts. The job ran to completion although a worker died holding it."),
    ])


@figure
def steps_jobs_claim():
    f = lambda job, a, b, active: [("JOB 8231 IN THE JOB STORE", [job], active == "job"), ("WORKER A", [a], active == "a"), ("WORKER B", [b], active == "b")]
    story("steps-jobs-claim", "2 workers and 1 waiting job", [
        (f("state waiting", "idle", "idle", None), "1 job is waiting, and 2 idle workers ask for work at the same moment."),
        (f("state waiting", "> asks: which job is waiting? answer: 8231", "idle", "a"), "Worker A asks the store for a waiting job and is told of job 8231. It has not yet marked the job as its own."),
        (f("state waiting", "has read 8231", "> asks: which job is waiting? answer: 8231", "b"), "Worker B asks the same question before A has acted, and receives the same answer, since the job is still marked as waiting."),
        (f("state running, held by A", "> marks 8231 as running", "has read 8231", "job"), "A marks the job as running and starts on it."),
        (f("! state running, held by B", "! working on 8231", "! marks 8231 as running, and works on it", "job"),
         "B does the same and overwrites A's mark. Both workers now run the job. The question and the marking were 2 separate operations, and B's question fell between them."),
        (f("state running, held by A", "> change to running if still waiting: done", "! change to running if still waiting: refused", "job"),
         "The cure joins the 2 operations into 1 conditional change: mark the job as running only if it is still waiting. The store carries out 1 such change before it considers the next, so exactly 1 worker succeeds."),
    ])


@figure
def jobs_cron():
    rows, bottom = step_rows(100, [
        ("store", "The schedule says: every day at 02:00", "create the job 'nightly report'"),
        ("client", "Scheduler node 1 sees that it is 02:00", "and creates the job"),
        ("service", "Scheduler node 2 sees that it is 02:00", "and creates the job as well"),
        ("danger", "The report runs twice", "2 nodes each did what the schedule told them"),
    ])
    parts = [rows, chip(32, bottom + 6, 416, "The cure: name each run after its time", "good"),
             lines(32, bottom + 62, ["Both nodes try to create 'nightly report 2026-10-14 02:00'.", "The store accepts the first and tells the second that it exists."], "sub")]
    save(OUT / "jobs-cron.svg", WIDTH, bottom + 100,
         "4 steps. A schedule says to create the job nightly report every day at 02:00. Scheduler node 1 sees that it is 02:00 "
         "and creates the job. Scheduler node 2 sees the same and creates the job as well. The report runs twice. The cure is to "
         "name each run after its time and to create it only if it is absent.",
         "A recurring job on 2 scheduler nodes", "Both nodes watch the same schedule.", parts)


# ------------------------------------------------ chapter 13: notifications

@figure
def steps_notify_backoff():
    f = lambda t, tries, state, provider, active: [("TIME SINCE THE FIRST TRY", ["%d s" % t], False), ("NOTIFICATION order-9-shipped", ["tries so far: %d" % tries, state], active == "n"),
                                                   ("PROVIDER", [provider], active == "p")]
    story("steps-notify-backoff", "A longer pause after each failure", [
        (f(0, 1, "! try 1 failed", "! error 503: overloaded", "p"), "The sender hands the notification to the provider, and the provider answers that it is overloaded. This is a failure that may pass, so the sender will try again."),
        (f(1, 2, "! try 2 failed, after a pause of 1 s", "! error 503: overloaded", "n"), "It waits 1 second and tries again. The provider is still overloaded."),
        (f(3, 3, "! try 3 failed, after a pause of 2 s", "! error 503: overloaded", "n"), "The pause doubles to 2 seconds. The third try fails as well. Each failure is taken as a sign that the provider needs more time than was allowed."),
        (f(7, 4, "! try 4 failed, after a pause of 4 s", "! error 503: overloaded", "n"), "The pause doubles again, to 4 seconds. 7 seconds have now passed since the first try."),
        (f(15, 5, "> try 5 succeeded, after a pause of 8 s", "> accepted", "p"), "After a pause of 8 seconds the provider has recovered and accepts. 5 tries were spread over 15 seconds, and most of that time the provider was left alone."),
        (f(15, 5, "sent", "accepted", None), "Had the fifth try failed too, the notification would have been set aside for a person to look at. The limit of 5 tries keeps a notification that can never be sent from circulating for ever."),
    ])


@figure
def steps_notify_breaker():
    f = lambda state, failures, call, active: [("CIRCUIT BREAKER FOR THE SMS PROVIDER", ["state: %s" % state, "failures in a row: %d" % failures], active), ("THE NEXT NOTIFICATION", [call], False)]
    story("steps-notify-breaker", "A circuit breaker before a provider", [
        (f("closed", 0, "> sent to the provider: accepted", False), "A circuit breaker stands between the senders and a provider and counts failures. While it is closed, every notification is passed on to the provider. This is the normal state."),
        (f("closed", 4, "! sent to the provider: timed out after 10 s", True), "The provider stops answering. 4 notifications in a row have each waited 10 seconds for an answer that did not come."),
        (f("open", 5, "! sent to the provider: timed out after 10 s", True), "The fifth failure in a row reaches the limit, and the breaker opens."),
        (f("open", 5, "! not sent: refused at once by the breaker", False), "While the breaker is open, nothing is sent to the provider. A notification fails at once, without the wait of 10 seconds, and goes back to the queue or to a second provider. The first provider is left in peace to recover."),
        (f("half open", 5, "> 1 trial notification is sent: accepted", True), "After 30 seconds the breaker lets a single notification through as a trial. This state is called half open. The trial succeeds."),
        (f("closed", 0, "> sent to the provider: accepted", True), "A successful trial closes the breaker, and the count returns to 0. Had the trial failed, the breaker would have opened again for another 30 seconds."),
    ])


@figure
def notify_jitter():
    spikes = "\n".join(dot(at(time, 0, 8000), 176 - 12 * row, "no" if time < 7000 else "ok", 4.5) for time in (1000, 3000, 7000) for row in range(6))
    spread = [(time + offset, "no" if time < 4000 else "ok") for time, offsets in ((0, (300, 620, 880)), (1000, (150, 520, 1700)), (3000, (400, 1500, 2900)), (4500, (300, 1400, 2600)))
              for offset in offsets]
    parts = [text(40, 96, "THE SAME PAUSES FOR EVERYONE: 1 S, 2 S, 4 S", "tab"), timeline(190, 0, 8000, [], None, [], None, 4.5, 2000), spikes,
             text(40, 258, "A RANDOM PAUSE UP TO 1 S, 2 S, 4 S", "tab"), timeline(310, 0, 8000, spread, None, [], None, 4.5, 2000),
             lines(32, 364, ["Each dot is a retry by 1 of many senders that failed together at 0 s.", "With equal pauses they return together, and each wave hits the",
                             "provider as hard as the first. Random pauses turn the waves into", "a steady trickle that a recovering provider can absorb."], "sub")]
    save(OUT / "notify-jitter.svg", WIDTH, 434,
         "2 time axes of retries by many senders that failed together. With the same pauses for everyone, the retries arrive "
         "in 3 tall spikes at 1, 3 and 7 seconds. With a random pause, the retries are spread evenly along the axis.",
         "Why pauses are made random", "Retries of senders that all failed at the same moment.", parts)


@figure
def notify_stages():
    rows, bottom = step_rows(100, [
        ("client", "Accepted", "the service has stored the request and answered 202"),
        ("store", "Queued", "waiting for a sender"),
        ("service", "Handed to the provider", "the provider answered that it has taken the message"),
        ("good", "Delivered", "the provider reports that the phone or mailbox has it"),
        ("idle", "Opened", "known only for some channels, and only sometimes"),
    ])
    parts = [rows, lines(32, bottom + 16, ["A notification can stop at any stage. 'Handed to the provider' is the", "last stage that the service itself can observe."], "sub")]
    save(OUT / "notify-stages.svg", WIDTH, bottom + 56,
         "5 stages of a notification: accepted, when the service has stored the request and answered 202; queued, waiting for "
         "a sender; handed to the provider; delivered, when the provider reports later that the phone or mailbox has it; and "
         "opened, which is known only for some channels.",
         "How far a notification has got", "Each stage is further from what the service can see.", parts)


# ------------------------------------------------ chapter 14: URL shortener

@figure
def steps_short_encode():
    digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    f = lambda number, work, code, active: [("THE 62 DIGITS", ["0 to 9 stand for 0 to 9", "A to Z stand for 10 to 35", "a to z stand for 36 to 61"], False),
                                            ("THE NUMBER STILL TO BE WRITTEN", ["%d" % number, work], active), ("THE CODE, BUILT FROM THE RIGHT", [code or "(empty)"], False)]
    steps = [(f(1000000, "", "", False), "The link is number 1000000 from the counter. To write it as a code, we divide by 62 again and again. Each remainder is 1 digit of the code, starting from the right.")]
    number, code = 1000000, ""

    while number:
        rest, digit = divmod(number, 62)
        code = digits[digit] + code
        steps.append((f(rest, "> %d = %d x 62 + %d" % (number, rest, digit), code, True),
                      "%d divided by 62 is %d with a remainder of %d. The digit for %d is %s, which is written to the left of what we have." % (number, rest, digit, digit, digits[digit])))
        number = rest

    steps.append((f(0, "", code, False), "Nothing is left to divide, and the code is %s. Reading it back is the reverse: 4 x 62 x 62 x 62 + 12 x 62 x 62 + 9 x 62 + 2 = 1000000." % code))
    story("steps-short-encode", "Writing a number in base 62", steps)


@figure
def short_collide():
    red, green = KINDS["danger"], KINDS["good"]
    parts = [text(32, 104, "2 MILLION ADDRESSES, EACH GIVEN A CODE", "tab"),
             text(32, 138, "codes from a counter", "name"), text(448, 138, "0 addresses share a code", "mono strong", "end"),
             box(32, 146, 416, 18, CARD, EDGE, 6), box(32, 146, 6, 18, green[1], green[0], 6),
             text(32, 196, "6 characters of a hash", "name"), text(448, 196, "97 addresses share a code", "mono strong", "end"),
             box(32, 204, 416, 18, CARD, EDGE, 6), box(32, 204, 60, 18, red[1], red[0], 6),
             lines(32, 254, ["A counter gives each address a number that no other address has.", "A hash scatters addresses over the possible codes, and with enough",
                             "addresses, 2 of them land on the same code."], "sub")]
    save(OUT / "short-collide.svg", WIDTH, 308,
         "2 million addresses are each given a code. With codes from a counter, no 2 addresses share a code. With codes made "
         "of 6 characters of a hash, 97 addresses share a code with another address.",
         "Counter or hash", "Measured by the simulation of this chapter.", parts)


@figure
def short_guess():
    rows, bottom = step_rows(100, [
        ("client", "An author creates a link and receives 4C92", "it leads to a private document"),
        ("danger", "A stranger tries 4C91, 4C93, 4C94 ...", "the neighbours of a code they happened to see"),
        ("danger", "Each neighbour is somebody's link", "because codes come from a counter, in order"),
        ("danger", "A stranger reads other people's documents", "and can count how many links are made per day"),
    ])
    parts = [rows, chip(32, bottom + 6, 416, "The cure: scramble the number before writing it in base 62", "good"),
             lines(32, bottom + 62, ["A scrambling that maps every number to a different number keeps", "the codes unique and makes neighbouring numbers look unrelated."], "sub")]
    save(OUT / "short-guess.svg", WIDTH, bottom + 100,
         "4 steps. An author creates a link and receives the code 4C92, which leads to a private document. A stranger tries the "
         "neighbouring codes 4C91, 4C93 and 4C94. Each neighbour is somebody's link, because codes come from a counter. The "
         "stranger reads documents meant for others. The cure is to scramble the number before writing it in base 62.",
         "Codes that can be guessed", "What a counter gives away.", parts)


# ------------------------------------------------ chapter 15: news feed

@figure
def steps_feed_push():
    f = lambda posts, bob, cy, note, active: [("POSTS, STORED ONCE", posts, active == "posts"), ("FEED LIST OF BOB, WHO FOLLOWS ADA", bob, active == "lists"),
                                              ("FEED LIST OF CY, WHO FOLLOWS ADA AND DAN", cy, active == "lists"), ("WHAT HAPPENS", [note], False)]
    story("steps-feed-push", "Copy on write", [
        (f(["post 41 by dan"], ["(empty)"], ["post 41"], "", None), "Every member has a feed list, kept ready in a cache. It holds the numbers of the posts that the member should see, newest first. Cy follows Dan and already has post 41."),
        (f(["post 41 by dan", "> post 42 by ada"], ["(empty)"], ["post 41"], "> ada publishes post 42", "posts"), "Ada publishes a post. It is stored once, as post 42, and Ada receives her answer at this point."),
        (f(["post 41 by dan", "post 42 by ada"], ["> post 42"], ["post 41"], "> a worker copies 42 to bob's list", "lists"), "In the background, a worker looks up who follows Ada and adds the number 42 to the front of each follower's list. Bob is first."),
        (f(["post 41 by dan", "post 42 by ada"], ["post 42"], ["> post 42", "post 41"], "> a worker copies 42 to cy's list", "lists"), "Then Cy. The work of publishing is proportional to the number of followers: 2 followers, 2 additions."),
        (f(["post 41 by dan", "post 42 by ada"], ["post 42"], ["post 42", "post 41"], "> cy opens the feed: 1 list is read", None),
         "When Cy opens the feed, the service reads Cy's list, which is already complete and in order, and fetches the 2 posts. Reading is as cheap as it can be, because the work was done when the posts were written."),
    ])


@figure
def steps_feed_pull():
    f = lambda ada, dan, merged, note, active: [("POSTS BY ADA, NEWEST FIRST", ada, active == "ada"), ("POSTS BY DAN, NEWEST FIRST", dan, active == "dan"),
                                                ("CY'S FEED, BUILT FOR THIS REQUEST", merged, active == "feed"), ("WHAT HAPPENS", [note], False)]
    story("steps-feed-pull", "Collect on read", [
        (f(["post 42", "post 38"], ["post 41", "post 40"], ["(nothing is stored for cy)"], "", None), "Under the other scheme no feed lists exist. Each author's posts are kept together, and publishing a post adds 1 line to the author's own list and does nothing else."),
        (f(["post 42", "post 38"], ["post 41", "post 40"], ["(nothing is stored for cy)"], "> cy opens the feed", None), "Cy opens the feed. The service first looks up whom Cy follows: Ada and Dan."),
        (f(["> post 42", "> post 38"], ["post 41", "post 40"], [""], "> fetch ada's recent posts", "ada"), "It fetches the recent posts of Ada."),
        (f(["post 42", "post 38"], ["> post 41", "> post 40"], [""], "> fetch dan's recent posts", "dan"), "It fetches the recent posts of Dan. With 200 followed accounts, there would be 200 such fetches for this 1 request."),
        (f(["post 42", "post 38"], ["post 41", "post 40"], ["> post 42", "> post 41", "> post 40", "> post 38"], "> merge by time", "feed"),
         "The 2 lists are merged into 1 by time, and the first page is returned. Publishing cost almost nothing, and reading costs 1 fetch for every account the reader follows, on every visit."),
    ])


@figure
def feed_cost():
    parts = [text(32, 104, "WORK PER DAY FOR 1001 ACCOUNTS", "tab")]
    rows = [("copy on write for everyone", 20400000, "20400000 copies", "danger"), ("collect on read for everyone", 4000500, "4000500 fetches", "store"),
            ("mixture", 420005, "400000 copies + 20005 fetches", "good")]

    for k, (name, value, label_, kind) in enumerate(rows):
        y = 140 + 56 * k
        parts += [text(32, y - 8, name, "name"), text(448, y - 8, label_, "mono strong", "end"), box(32, y, 416, 18, CARD, EDGE, 6),
                  box(32, y, max(8, 416 * value / 20400000), 18, KINDS[kind][1], KINDS[kind][0], 6)]

    parts.append(lines(32, 322, ["Nearly all 20.4 million copies are for the 1 large account: 10 posts,", "each copied to 2 million lists. The mixture copies the posts of",
                                 "ordinary accounts and fetches the large account's posts on reading."], "sub"))
    save(OUT / "feed-cost.svg", WIDTH, 376,
         "3 bars of work per day for 1000 ordinary accounts and 1 account with 2 million followers. Copy on write for everyone "
         "makes 20400000 copies. Collect on read for everyone makes 4000500 fetches. The mixture makes 400000 copies and 20005 fetches.",
         "The cost of the 3 schemes", "1000 ordinary accounts and 1 with 2 million followers.", parts)


@figure
def steps_feed_page():
    f = lambda feed, asked, got, active: [("THE FEED, NEWEST FIRST", feed, active == "feed"), ("THE READER ASKS", [asked], False), ("THE READER RECEIVES", got, active == "got")]
    story("steps-feed-page", "A new post arrives between 2 pages", [
        (f(["position 1   post 50", "position 2   post 49", "position 3   post 48", "position 4   post 47"], "> page 1: the first 2 items", ["post 50", "post 49"], "got"),
         "A reader opens the feed and receives the first page, 2 items: posts 50 and 49."),
        (f(["> position 1   post 51", "position 2   post 50", "position 3   post 49", "position 4   post 48", "position 5   post 47"], "", ["post 50", "post 49"], "feed"),
         "While the reader looks at them, a new post, 51, is added to the front. Every older post moves down by 1 position."),
        (f(["position 1   post 51", "position 2   post 50", "position 3   post 49", "position 4   post 48", "position 5   post 47"], "! page 2 by position: skip 2, take 2", ["! post 49, seen already", "post 48"], "got"),
         "The reader scrolls, and the app asks for the items at positions 3 and 4. Position 3 is now post 49, which the reader has already seen. Asking by position shows a duplicate whenever something was added."),
        (f(["position 1   post 51", "position 2   post 50", "position 3   post 49", "position 4   post 48", "position 5   post 47"], "> page 2 by cursor: 2 items older than post 49", ["post 48", "post 47"], "got"),
         "The better request names the last item the reader saw: give me 2 items older than post 49. The answer does not depend on what was added at the front, so nothing is repeated and nothing is missed."),
    ])


# ------------------------------------------------ chapter 16: object store

@figure
def steps_obj_parity():
    f = lambda a, b, c, parity, note, active: [("DISK 1: DATA", [a], active == 1), ("DISK 2: DATA", [b], active == 2), ("DISK 3: DATA", [c], active == 3),
                                               ("DISK 4: PARITY, THE SUM OF THE OTHER 3", [parity], active == 4), ("ARITHMETIC", [note], False)]
    story("steps-obj-parity", "Rebuilding a lost piece from a sum", [
        (f("5", "3", "9", "", "", None), "An object is cut into 3 pieces, which for this picture are the numbers 5, 3 and 9. Each piece goes to a different disk."),
        (f("5", "3", "9", "> 17", "> 5 + 3 + 9 = 17", 4), "A fourth disk receives 1 extra piece, the sum of the other 3. This piece is called parity. It holds no new information, and it is what makes recovery possible."),
        (f("5", "! lost", "9", "17", "", 2), "Disk 2 fails. Its piece is gone, and no copy of it exists anywhere."),
        (f("5", "> 3", "9", "17", "> 17 - 5 - 9 = 3", 2), "The missing piece is the sum minus the pieces that survive: 17 - 5 - 9 = 3. The piece is computed and written to a new disk."),
        (f("5", "3", "9", "17", "4 disks hold 3 disks of data", None),
         "The object survived the loss of a disk and used 4 disks for 3 disks of data. 2 full copies would also survive 1 loss, and would need 6 disks. Real systems add several parity pieces and survive several losses."),
    ])


@figure
def steps_obj_scrub():
    f = lambda n1, n2, n3, note, active: [("NODE 1: COPY OF CHUNK c1", n1, active == 1), ("NODE 4: COPY OF CHUNK c1", n2, active == 2), ("NODE 5: COPY OF CHUNK c1", n3, active == 3),
                                          ("WHAT HAPPENS", [note], False)]
    good = ["stored checksum   7f3a", "checksum of bytes 7f3a"]
    bad = ["stored checksum   7f3a", "! checksum of bytes 19c4"]
    story("steps-obj-scrub", "A damaged copy is found and repaired", [
        (f(good, good, good, "", None), "A chunk is stored on 3 nodes. With each copy the node keeps the checksum that the bytes had when they were written."),
        (f(good, bad, good, "! 1 bit on the disk of node 4 changes", 2), "Months later, 1 bit of the copy on node 4 changes on the disk. No error is reported. The disk will return the altered bytes as if nothing had happened."),
        (f(good, bad, good, "> the scrubber reads node 4 and compares", 2), "A background process, the scrubber, reads every chunk in turn and computes its checksum afresh. On node 4 the result differs from the stored checksum, which proves that the bytes have changed."),
        (f(["> stored checksum   7f3a", "> checksum of bytes 7f3a"], bad, good, "> a good copy is read from node 1", 1), "The damaged copy cannot be mended from itself. A copy whose checksum still matches is read from another node."),
        (f(good, ["> stored checksum   7f3a", "> checksum of bytes 7f3a"], good, "> node 4 receives the good bytes", 2),
         "The good bytes replace the damaged copy, and the chunk has 3 sound copies again. Had nobody looked until the other 2 copies were damaged as well, the chunk would have been lost."),
    ])


@figure
def obj_overhead():
    parts = [text(32, 104, "DISK SPACE USED FOR EVERY 1 TB OF OBJECTS", "tab")]
    rows = [("3 full copies", 3.0, "3.0 TB, survives 2 losses", "store"), ("10 data + 4 parity pieces", 1.4, "1.4 TB, survives 4 losses", "good")]

    for k, (name, value, label_, kind) in enumerate(rows):
        y = 140 + 56 * k
        parts += [text(32, y - 8, name, "name"), text(448, y - 8, label_, "mono strong", "end"), box(32, y, 416, 18, CARD, EDGE, 6),
                  box(32, y, 416 * value / 3.0, 18, KINDS[kind][1], KINDS[kind][0], 6)]

    parts.append(lines(32, 256, ["Parity pieces protect better and use less than half the space.", "They cost computation on every write, and a repair has to read 10",
                                 "pieces where copying reads 1."], "sub"))
    save(OUT / "obj-overhead.svg", WIDTH, 310,
         "2 bars of the disk space used for every 1 TB of objects. 3 full copies use 3.0 TB and survive the loss of 2 "
         "copies. 10 data pieces with 4 parity pieces use 1.4 TB and survive the loss of any 4 pieces.",
         "Copies and parity compared", "2 ways of surviving lost disks.", parts)


@figure
def obj_collect():
    rows, bottom = step_rows(100, [
        ("store", "The collector lists unused chunks", "chunk c9 is on the list"),
        ("client", "An upload arrives that contains chunk c9", "the same bytes as before, so the same name"),
        ("client", "The server sees that c9 is already stored", "and records the new object as using it"),
        ("danger", "The collector deletes c9", "acting on a list that is now out of date"),
        ("danger", "The new object refers to a deleted chunk", "and cannot be read"),
    ])
    parts = [rows, chip(32, bottom + 6, 416, "The cure: delete only chunks that have been unused for a day", "good")]
    save(OUT / "obj-collect.svg", WIDTH, bottom + 56,
         "5 steps. The collector lists the chunks that no object uses, among them chunk c9. An upload arrives that contains "
         "chunk c9. The server sees that c9 is already stored and records the new object as using it. The collector deletes "
         "c9, acting on a list that is out of date. The new object refers to a chunk that is gone. The cure is to delete only "
         "chunks that have been unused for a day.",
         "A chunk deleted while being reused", "Garbage collection and an upload overlap.", parts)


# ------------------------------------------------ chapter 17: video streaming

@figure
def steps_stream_adapt():
    rows = [(1, 6000, 400, 0.3, 4.0), (2, 6000, 2500, 1.7, 6.3), (3, 6000, 2500, 1.7, 8.7), (4, 1500, 2500, 6.7, 6.0), (5, 1500, 1200, 3.2, 6.8),
            (6, 700, 1200, 6.9, 4.0), (7, 700, 400, 2.3, 5.7), (8, 3200, 400, 0.5, 9.2), (9, 6000, 2500, 1.7, 11.5), (10, 6000, 2500, 1.7, 13.9)]
    said = {1: "The player knows nothing about the connection yet, so it starts with the lowest quality. The piece arrives in 0.3 seconds, which tells the player that the connection is fast.",
            2: "The last download ran at 6000 kbit/s. The player takes the best quality that needs at most 80% of that: 2500. The piece plays for 4 seconds and took 1.7 seconds to fetch, so the buffer grows.",
            3: "Nothing has changed, and the buffer grows further. The player now has nearly 9 seconds of video in hand.",
            4: "The speed falls to 1500. The player does not know this yet and asks for 2500 again. The piece takes 6.7 seconds to arrive, longer than the 4 seconds it plays for, and the buffer shrinks.",
            5: "The player has now measured 1500 and steps down to 1200. The buffer covered the slow download, and the picture did not stop.",
            6: "The speed falls again, to 700. The player is once more 1 piece behind, and the piece at 1200 takes 6.9 seconds. The buffer is down to 4 seconds.",
            7: "The player steps down to 400, the lowest quality, which a connection of 700 can carry with room to spare. The buffer begins to recover.",
            8: "The connection improves to 3200. The player still chooses on the basis of the previous measurement, 700, and stays at 400 for 1 more piece.",
            9: "Having measured 3200, the player returns to 2500. The picture becomes sharp again.",
            10: "The buffer holds almost 14 seconds. Through 2 drops in speed the video never stopped: quality was given up to keep it playing."}
    steps = [([("PIECE", ["piece %d of 10" % piece], False), ("CONNECTION WHILE THIS PIECE DOWNLOADS", ["%d kbit/s" % speed], True),
               ("QUALITY THE PLAYER ASKS FOR", ["> %d kbit/s" % quality, "download takes %.1f s" % took], True), ("VIDEO IN THE BUFFER AFTERWARDS", ["%.1f s" % buffered], False)], said[piece])
             for piece, speed, quality, took, buffered in rows]
    story("steps-stream-adapt", "The player adapts to the connection", steps)


@figure
def stream_ladder():
    parts = [text(32, 104, "THE SAME VIDEO, ENCODED 4 TIMES", "tab")]
    rows = [("240 lines", 400, "client"), ("480 lines", 1200, "service"), ("720 lines", 2500, "store"), ("1080 lines", 5000, "outside")]

    for k, (name, rate, kind) in enumerate(rows):
        y = 140 + 54 * k
        parts += [text(32, y - 8, name, "name"), text(448, y - 8, "%d kbit/s, %.1f MB per piece" % (rate, rate * 4 / 8000), "mono strong", "end"),
                  box(32, y, 416, 18, CARD, EDGE, 6), box(32, y, 416 * rate / 5000, 18, KINDS[kind][1], KINDS[kind][0], 6)]

    parts.append(lines(32, 362, ["Each version is cut at the same moments into pieces of 4 seconds.", "Piece 17 covers the same 4 seconds in every version, so the player",
                                 "can take piece 17 at 1 quality and piece 18 at another."], "sub"))
    save(OUT / "stream-ladder.svg", WIDTH, 416,
         "The same video encoded 4 times: at 240 lines and 400 kbit/s, at 480 lines and 1200 kbit/s, at 720 lines and 2500 "
         "kbit/s, and at 1080 lines and 5000 kbit/s. Each version is cut at the same moments into pieces of 4 seconds.",
         "4 qualities of 1 video", "A piece of 4 seconds at each quality.", parts)


@figure
def stream_edge():
    rows, bottom = step_rows(100, [
        ("client", "A viewer in Lisbon asks for piece 17", "the request goes to the nearest edge server"),
        ("good", "The edge has the piece: a hit", "it answers from its own disk, 5 ms away"),
        ("store", "The edge lacks the piece: a miss", "it fetches the piece from the origin, 80 ms away"),
        ("service", "The edge keeps a copy", "the next viewer in Lisbon gets a hit"),
    ])
    parts = [rows, lines(32, bottom + 16, ["A popular video is fetched from the origin once for each edge and", "served from the edges millions of times."], "sub")]
    save(OUT / "stream-edge.svg", WIDTH, bottom + 56,
         "4 steps. A viewer in Lisbon asks for piece 17, and the request goes to the nearest edge server. If the edge has the "
         "piece, it answers from its own disk. If it lacks the piece, it fetches the piece from the origin. The edge keeps a "
         "copy, so the next viewer in Lisbon is served from the edge.",
         "A piece served from the edge", "Edge servers stand close to viewers.", parts)


@figure
def stream_encode():
    rows, bottom = step_rows(100, [
        ("client", "The uploaded file is stored as it is", "the source, 10 GB"),
        ("store", "The source is cut into 1-minute sections", "at points where a new picture begins"),
        ("service", "Each section becomes 4 encoding jobs", "1 for each quality, run by any free encoder"),
        ("service", "Each job cuts its result into 4 s pieces", "and stores them in the object store"),
        ("good", "A manifest lists every piece", "the video is now ready to play"),
    ])
    parts = [rows, lines(32, bottom + 16, ["A film of 2 hours gives 480 jobs. 100 encoders finish them in the", "time that 1 encoder needs for 5."], "sub")]
    save(OUT / "stream-encode.svg", WIDTH, bottom + 56,
         "5 steps. The uploaded file is stored as it is. The source is cut into sections of 1 minute. Each section becomes 4 "
         "encoding jobs, 1 for each quality. Each job cuts its result into pieces of 4 seconds and stores them in the object "
         "store. A manifest lists every piece, and the video is ready to play.",
         "From an upload to pieces", "Encoding is divided so that many machines can share it.", parts)


# ------------------------------------------------ chapter 18: chat

@figure
def chat_connections():
    arrive = lambda y: (f'  <line x1="{at(1300, 0, 3000):.1f}" y1="{y - 40}" x2="{at(1300, 0, 3000):.1f}" y2="{y + 6}" stroke="{KINDS["danger"][0]}" stroke-width="1.6" stroke-dasharray="4 4"/>')
    hold = lambda y, a, b: f'  <rect x="{at(a, 0, 3000):.1f}" y="{y - 20}" width="{at(b, 0, 3000) - at(a, 0, 3000):.1f}" height="12" rx="6" fill="{KINDS["store"][1]}" stroke="{KINDS["store"][0]}" stroke-width="1.2"/>'
    parts = [text(40, 100, "ASKING EVERY SECOND", "tab"), timeline(160, 0, 3000, [(0, "wait"), (1000, "wait"), (2000, "ok"), (3000, "wait")], None, [], None, 5, 1000), arrive(160),
             text(40, 218, "ASKING, AND WAITING FOR THE ANSWER", "tab"), hold(278, 0, 1300), hold(278, 1300, 3000),
             timeline(278, 0, 3000, [(1300, "ok")], None, [], None, 5, 1000), arrive(278),
             text(40, 336, "1 CONNECTION THAT STAYS OPEN", "tab"), hold(396, 0, 3000), timeline(396, 0, 3000, [(1300, "ok")], None, [], None, 5, 1000), arrive(396),
             lines(32, 450, ["The dashed line is the moment a message for this phone reaches", "the server, at 1.3 s. A green dot is the moment the phone receives",
                             "it. An amber dot is a request that came back empty, and an amber", "bar is a request or connection that is being held open."], "sub")]
    save(OUT / "chat-connections.svg", WIDTH, 522,
         "3 time axes on which a message for a phone reaches the server at 1.3 seconds. When the phone asks every second, it "
         "receives the message at 2.0 seconds, and 3 other requests come back empty. When the phone asks and the server holds "
         "the request until there is an answer, the phone receives the message at 1.3 seconds and asks again. With 1 "
         "connection that stays open, the phone receives the message at 1.3 seconds and no requests are made.",
         "3 ways for a phone to receive", "A message arrives at the server at 1.3 s.", parts)


@figure
def steps_chat_catchup():
    f = lambda server, phone, cursor, note, active: [("CONVERSATION 301 ON THE SERVER", server, active == "server"), ("SHOWN ON THE PHONE", phone, active == "phone"),
                                                     ("THE PHONE'S CURSOR: LAST NUMBER SHOWN", [cursor], active == "phone"), ("WHAT HAPPENS", [note], False)]
    m = ["1  are you coming?", "2  hello?", "3  we are starting", "4  table 4"]
    story("steps-chat-catchup", "A phone catches up after a gap", [
        (f(m[:1], m[:1], "1", "> message 1 is delivered", "phone"), "The server gives every message of a conversation the next number. The phone is online and shows message 1. It remembers that 1 is the last number it has shown."),
        (f(m, m[:1], "1", "! the phone loses its connection", "server"), "The phone goes into a tunnel. 3 more messages are sent, and the server numbers and stores them as 2, 3 and 4. They cannot be delivered."),
        (f(m, m[:1], "1", "! message 4 arrives alone: ignored", "phone"), "The connection returns for an instant, and message 4 gets through. The phone expected number 2 next. A 4 after a 1 means that something is missing, so the phone does not show it."),
        (f(m, m[:1], "1", "> the phone reconnects and reports: I have 1", "phone"), "The connection is restored properly. The phone does not ask what it missed, which it cannot know. It states its position: the last message I have is number 1."),
        (f(m, m, "4", "> the server sends everything after 1", "server"), "The server sends every message with a number above 1. The phone shows 2, 3 and 4 in order and moves its cursor to 4."),
        (f(m, m, "4", "! the server sends message 3 again: ignored", "phone"), "An acknowledgement was lost on the way back, so the server sends message 3 once more. The phone's cursor is at 4, and a number at or below the cursor has been shown already. It is ignored."),
        (f(m, m, "4", "4 messages on the server, 4 on the phone", None), "1 number per message has handled a gap, a message that arrived out of order, and a repeat. The phone shows each message once, in the order the server gave them."),
    ])


@figure
def steps_chat_send():
    f = lambda phone, server, note, active: [("THE SENDER'S PHONE", phone, active == "phone"), ("CONVERSATION 301 ON THE SERVER", server, active == "server"), ("WHAT HAPPENS", [note], False)]
    story("steps-chat-send", "Sent twice, stored once", [
        (f(["message a7f3 'on my way': sending"], ["1  are you coming?"], "> the phone sends, with its own identifier a7f3", "phone"),
         "Before sending, the phone gives the message an identifier of its own, chosen at random: a7f3. The identifier travels with the message."),
        (f(["message a7f3 'on my way': sending"], ["1  are you coming?", "> 2  on my way   (a7f3)"], "> the server stores it as number 2", "server"),
         "The server stores the message as number 2 of the conversation and remembers that it came with the identifier a7f3."),
        (f(["! message a7f3: no answer yet"], ["1  are you coming?", "2  on my way   (a7f3)"], "! the answer is lost on the way back", "phone"),
         "The server's answer is lost. The phone cannot tell whether the message arrived. After a few seconds it does the only safe thing and sends the message again, with the same identifier."),
        (f(["message a7f3: sending again"], ["1  are you coming?", "2  on my way   (a7f3)"], "> the server recognises a7f3", "server"),
         "The server finds that it has already stored a message with the identifier a7f3 in this conversation. It stores nothing new and answers as it did the first time: this is message 2."),
        (f(["> message a7f3: sent, number 2"], ["1  are you coming?", "2  on my way   (a7f3)"], "the conversation holds the message once", None),
         "The phone marks the message as sent. Without the identifier, the second attempt would have been stored as message 3, and the receiver would have seen 'on my way' twice."),
    ])


# ------------------------------------------------ chapter 19: payments

@figure
def steps_pay_ledger():
    f = lambda entries, balances, total, active: [("LEDGER: ENTRIES ARE ADDED AND NEVER CHANGED", (entries + [""] * 6)[:6], active == "ledger"),
                                                  ("BALANCES: THE SUM OF EACH ACCOUNT'S ENTRIES", balances, active == "balances"), ("SUM OF ALL ENTRIES", [total], False)]
    e1 = ["payment 9001   ada    -4000", "payment 9001   shop   +4000"]
    e2 = e1 + ["payment 9002   ada    -6000", "payment 9002   shop   +6000"]
    e3 = e2 + ["> refund 9003    shop   -4000", "> refund 9003    ada    +4000"]
    story("steps-pay-ledger", "2 entries for every movement", [
        (f([], ["ada   10000", "shop      0"], "0", None), "Ada has 10000 cents and the shop has none. The ledger of movements is empty. Amounts are whole numbers of cents throughout."),
        (f(["> payment 9001   ada    -4000", "> payment 9001   shop   +4000"], ["ada    6000", "shop   4000"], "> -4000 + 4000 = 0", "ledger"),
         "Ada pays the shop 4000. The ledger receives 2 entries, written together: 4000 leaves Ada's account and 4000 enters the shop's. The 2 entries add up to 0."),
        (f(e1 + ["> payment 9002   ada    -6000", "> payment 9002   shop   +6000"], ["ada       0", "shop  10000"], "> 0", "ledger"),
         "A second payment of 6000 adds 2 more entries. Nothing already written is touched. A balance is the sum of the entries of its account."),
        (f(e3, ["ada    4000", "shop   6000"], "> 0", "ledger"),
         "The shop refunds the first payment. The original entries are not deleted or altered. 2 new entries are added that move 4000 the other way, so the ledger shows both what happened and that it was undone."),
        (f(e2 + ["refund 9003    shop   -4000", "refund 9003    ada    +4000"], ["ada    4000", "shop   6000"], "0, as after every movement", "balances"),
         "The sum of all entries is 0 after every movement, because each movement is a pair that cancels. A ledger whose entries do not add up to 0 has lost or invented money, and the check that reveals this takes a single addition."),
    ])


@figure
def steps_pay_pending():
    f = lambda state, ledger, network, note, active: [("PAYMENT 9004 IN OUR SYSTEM", ["state: %s" % state, ledger], active == "us"), ("THE CARD NETWORK", [network], active == "net"),
                                                      ("WHAT HAPPENS", [note], False)]
    story("steps-pay-pending", "A charge whose outcome is unknown", [
        (f("pending", "no entries yet", "has not heard of it", "> the payment is recorded as pending", "us"),
         "Before anything is sent to the card network, the payment is stored in our own system in the state pending, with a reference of our choosing. If we crash in the next step, the record will tell us what we were doing."),
        (f("pending", "no entries yet", "> charges the card: success", "> the charge is sent with our reference", "net"),
         "The charge is sent to the card network together with the reference. The network charges the customer's card and replies that it has done so."),
        (f("pending", "no entries yet", "charged", "! the reply does not arrive: timeout", "us"),
         "The reply is lost. Our system waits 10 seconds and gives up. At this moment we do not know whether the customer was charged. It would be wrong to report failure and wrong to report success."),
        (f("pending", "no entries yet", "charged", "> the shop is told: pending", "us"),
         "The shop is told the truth, that the payment is pending. Nothing is written to the ledger, and the charge is not sent again, since a second charge might take the money twice."),
        (f("pending", "no entries yet", "> answers: reference 9004 was charged", "> we ask: what became of reference 9004?", "net"),
         "A background process asks the network about the payment by its reference. Asking is safe to repeat. The network answers that the charge succeeded."),
        (f("done", "> 2 entries written", "charged", "> the shop is notified: done", "us"),
         "Only now are the ledger entries written and the payment marked as done. The shop is informed. The customer was charged once, and our records agree with the network's."),
    ])


@figure
def pay_stages():
    rows, bottom = step_rows(100, [
        ("client", "Authorisation", "the customer's bank sets the amount aside: seconds"),
        ("service", "Capture", "the shop confirms that it wants the money: at shipping"),
        ("store", "Settlement", "the banks actually move the money: 1 to 3 days later"),
        ("idle", "Refund or dispute", "possible for months afterwards"),
    ])
    parts = [rows, lines(32, bottom + 16, ["The customer sees 'payment accepted' after the first stage.", "The money reaches the shop only after the third."], "sub")]
    save(OUT / "pay-stages.svg", WIDTH, bottom + 56,
         "4 stages of a card payment. Authorisation, in which the customer's bank sets the amount aside, takes seconds. Capture, "
         "in which the shop confirms that it wants the money, happens at shipping. Settlement, in which the banks move the "
         "money, follows 1 to 3 days later. A refund or a dispute remains possible for months.",
         "The stages of a card payment", "What looks like 1 event is spread over days.", parts)


@figure
def pay_reconcile():
    two_views("pay-reconcile", "Comparing 2 records of the same day", "Our ledger and the bank's statement, payment by payment.",
              "Our ledger", "The bank's statement",
              [("PAYMENT 9001", "4000 done", "4000 settled"), ("PAYMENT 9002", "6000 done", "6000 settled"), ("PAYMENT 9004", "2500 pending", "2500 settled"), ("PAYMENT 9005", "1200 done", "(not listed)")],
              "2 records of the same payments, side by side. Payments 9001 and 9002 agree. Payment 9004 is pending in our ledger "
              "and settled on the bank's statement. Payment 9005 is done in our ledger and missing from the bank's statement.",
              ["9004: the bank has the money and we have not recorded it.", "9005: we recorded money that the bank never moved.", "Each difference is investigated and corrected with new entries."])


# ------------------------------------------------ chapter 20: ticket booking

@figure
def steps_booking_race():
    f = lambda seat, a, b, active: [("SEAT 12 IN THE SEAT STORE", [seat], active == "seat"), ("ADA'S REQUEST", [a], active == "a"), ("BOB'S REQUEST", [b], active == "b")]
    story("steps-booking-race", "2 buyers and 1 seat", [
        (f("free", "", "", None), "Seat 12 is free. Ada and Bob both press 'buy' on it within the same few milliseconds, and their requests reach 2 different servers."),
        (f("free", "> reads the seat: free", "", "a"), "The server handling Ada's request reads the seat and finds it free."),
        (f("free", "has read: free", "> reads the seat: free", "b"), "The server handling Bob's request reads the seat a moment later. Ada's server has not written anything yet, so the seat is still free."),
        (f("sold to ada", "> writes: sold to ada", "has read: free", "seat"), "Ada's server writes that the seat is sold to Ada and confirms her purchase."),
        (f("! sold to bob", "! was told: the seat is yours", "! writes: sold to bob", "seat"), "Bob's server, acting on what it read, writes that the seat is sold to Bob and confirms his purchase. Both buyers hold a confirmation for the same seat, and only 1 of them appears in the store."),
        (f("sold to ada", "> sold to ada, if still free: done", "! sold to bob, if still free: refused", "seat"),
         "The cure is to make the write conditional: mark the seat as sold only if it is still free. The store applies 1 such write completely before it looks at the next, so Bob's write finds the seat taken and is refused."),
    ])


@figure
def steps_booking_hold():
    f = lambda t, seat, a, b, active: [("TIME", ["minute %d" % t], False), ("SEAT 1 IN THE SEAT STORE", [seat], active == "seat"), ("ADA", [a], active == "a"), ("BOB", [b], active == "b")]
    story("steps-booking-hold", "A hold that runs out", [
        (f(0, "held for ada until minute 5", "> holds seat 1", "", "seat"), "Ada chooses seat 1. The seat is not sold to her yet. It is held in her name for 5 minutes, which gives her time to pay and keeps everyone else away from it meanwhile."),
        (f(1, "held for ada until minute 5", "entering her card details", "! asks for seat 1: refused", "b"), "Bob asks for the same seat a minute later and is refused, because the hold is still running. He is shown the seat as taken and chooses another, or waits."),
        (f(5, "held for ada until minute 5: run out", "! has gone to look for her card", "waiting", "seat"), "Ada is interrupted and does not pay. At minute 5 the hold runs out. Nothing has to happen at that instant: the hold carries its own end time, and anyone who looks at the seat after that time can see that it no longer counts."),
        (f(6, "held for bob until minute 11", "still away", "> holds seat 1", "seat"), "Bob tries again at minute 6. The seat's hold has run out, so the seat is available, and it is now held for Bob."),
        (f(7, "held for bob until minute 11", "! tries to pay for seat 1: refused", "entering his card details", "a"), "Ada returns at minute 7 and presses 'pay'. The system checks that the seat is held by her and that the hold is still running. It is not, and her payment is refused before any money moves."),
        (f(8, "sold to bob", "must choose another seat", "> pays: the seat is his", "seat"), "Bob pays at minute 8, within his hold. The seat becomes sold. It was promised to 1 buyer at every moment, and it was never kept from sale for longer than 5 minutes by a buyer who did not pay."),
    ])


@figure
def booking_room():
    rows, bottom = step_rows(100, [
        ("client", "2 million people arrive at 10:00", "for 50000 seats"),
        ("store", "Each is given a place in a waiting room", "a page that costs almost nothing to serve"),
        ("service", "5000 at once are admitted to the seat map", "the number the booking system can serve well"),
        ("service", "As buyers finish, more are admitted", "in the order of their places"),
        ("idle", "When the seats are gone, the rest are told", "without ever having reached the booking system"),
    ])
    parts = [rows, lines(32, bottom + 16, ["The booking system works at a steady, safe load throughout. The", "crowd waits in a queue that was built for crowds."], "sub")]
    save(OUT / "booking-room.svg", WIDTH, bottom + 56,
         "5 steps. 2 million people arrive at 10:00 for 50000 seats. Each is given a place in a waiting room. 5000 at once "
         "are admitted to the seat map. As buyers finish, more are admitted in the order of their places. When the seats are "
         "gone, the rest are told, without having reached the booking system.",
         "A waiting room in front of a sale", "Far more buyers than seats.", parts)


# ------------------------------------------------ chapter 21: ride hailing

def city_grid(x, y, size, cells_, drivers, rider=None, marked=()):
    """A square map divided into `cells_` by `cells_` squares, with drivers as dots and a rider as a diamond."""
    step = size / cells_
    parts = [box(x + step * column, y + step * row, step, step, KINDS["good"][1], KINDS["good"][0], 0, 1.6) for column, row in marked]
    parts += [f'  <rect x="{x}" y="{y}" width="{size}" height="{size}" fill="none" stroke="{MUTED}" stroke-width="1.6"/>']
    parts += [f'  <line x1="{x + step * k:.1f}" y1="{y}" x2="{x + step * k:.1f}" y2="{y + size}" stroke="{EDGE}" stroke-width="1"/>' for k in range(1, cells_)]
    parts += [f'  <line x1="{x}" y1="{y + step * k:.1f}" x2="{x + size}" y2="{y + step * k:.1f}" stroke="{EDGE}" stroke-width="1"/>' for k in range(1, cells_)]
    parts += [f'  <circle cx="{x + px * size:.1f}" cy="{y + py * size:.1f}" r="4" fill="{KINDS["client"][0]}"/>' for px, py in drivers]

    if rider:
        cx, cy = x + rider[0] * size, y + rider[1] * size
        parts.append(f'  <rect x="{cx - 6:.1f}" y="{cy - 6:.1f}" width="12" height="12" fill="{KINDS["danger"][0]}" transform="rotate(45 {cx:.1f} {cy:.1f})"/>')

    return "\n".join(parts)


def scatter(count, seed):
    points, state = [], seed

    for k in range(count * 2):
        state = (state * 1103515245 + 12345) % 2147483648
        points.append((state % 1000) / 1000)

    return list(zip(points[::2], points[1::2]))


@figure
def nearby_grid():
    drivers = scatter(60, 7)
    rider = (0.42, 0.55)
    column, row = int(rider[0] * 6), int(rider[1] * 6)
    marked = [(column + dx, row + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
    inside = sum(1 for px, py in drivers if (int(px * 6), int(py * 6)) in marked)
    parts = [city_grid(96, 100, 288, 6, drivers, rider, marked),
             lines(32, 416, ["The city is divided into squares. The rider, the red diamond, is in", "1 square, and the search looks at that square and the 8 around it.",
                             "Of the 60 drivers on this map, %d are in those 9 squares. Only their" % inside, "distances are measured."], "sub")]
    save(OUT / "nearby-grid.svg", WIDTH, 490,
         "A square map divided into 36 squares, with 60 drivers scattered over it and a rider. The square that contains the "
         "rider and the 8 squares around it are shaded. Only the drivers in those 9 squares are considered.",
         "Searching 9 squares of a grid", "Blue dots are drivers.", parts)


@figure
def nearby_edge():
    parts = [city_grid(60, 100, 150, 2, [(0.56, 0.42), (0.1, 0.1), (0.9, 0.9), (0.2, 0.8)], (0.44, 0.44), [(0, 0)]),
             city_grid(270, 100, 150, 2, [(0.56, 0.42), (0.1, 0.1), (0.9, 0.9), (0.2, 0.8)], (0.44, 0.44), [(0, 0), (1, 0), (0, 1), (1, 1)]),
             text(135, 272, "the rider's square only", "pill", "middle", INK), text(345, 272, "with the neighbours", "pill", "middle", INK),
             lines(32, 304, ["The nearest driver is just across the border of the rider's square.", "A search of 1 square misses that driver and returns one who is much",
                             "further away. The neighbouring squares have to be searched as well."], "sub")]
    save(OUT / "nearby-edge.svg", WIDTH, 362,
         "2 copies of a map of 4 squares with a rider near the corner of 1 square and the nearest driver just across the "
         "border in the next square. On the left only the rider's square is searched, and the nearest driver is missed. On "
         "the right the neighbouring squares are searched as well, and the driver is found.",
         "Why neighbours are searched", "The same map, searched in 2 ways.", parts)


@figure
def steps_nearby_match():
    f = lambda ride, d1, d2, note, active: [("RIDE 501 IN THE RIDE STORE", ride, active == "ride"), ("DRIVER 19862, 0.19 KM AWAY", [d1], active == 1), ("DRIVER 7056, 0.84 KM AWAY", [d2], active == 2),
                                            ("WHAT HAPPENS", [note], False)]
    story("steps-nearby-match", "A ride offered to drivers in turn", [
        (f(["state: requested", "driver: none"], "free", "free", "> the 3 nearest free drivers are found", "ride"), "A rider requests a ride. The matching service finds the nearest free drivers from the grid and ranks them by distance."),
        (f(["state: offered to 19862", "driver: none"], "> sees the offer, 15 s to answer", "free", "> the ride is offered to the nearest driver", 1), "The ride is offered to the nearest driver only, who has 15 seconds to accept. Offering it to all of them at once would be faster and would disappoint all but 1."),
        (f(["state: offered to 19862", "driver: none"], "! does not answer", "free", "! 15 s pass without an answer", 1), "The driver is in the middle of a turn and does not respond. The offer is a lease: it ends by itself after 15 seconds."),
        (f(["state: offered to 7056", "driver: none"], "the offer has ended", "> sees the offer, 15 s to answer", "> the ride is offered to the next driver", 2), "The ride is offered to the next nearest driver."),
        (f(["state: accepted", "> driver: 7056"], "the offer has ended", "> accepts", "> set driver to 7056, if still unassigned: done", "ride"),
         "The second driver accepts. The ride store records the driver with a conditional write: assign this driver if the ride has none. The driver is marked as busy in the same step."),
        (f(["state: accepted", "driver: 7056"], "! accepts, too late: refused", "on the way to the rider", "! set driver to 19862, if still unassigned: refused", 1),
         "The first driver now taps 'accept' on an offer that has ended. The same conditional write finds that the ride has a driver and refuses. A ride is never assigned to 2 drivers."),
    ])


# ------------------------------------------------ chapter 22: search autocomplete

@figure
def type_trie():
    blue, tint = KINDS["client"]
    spots = {"": (240, 112), "k": (150, 176), "r": (382, 176), "ka": (70, 244), "ke": (170, 244), "ku": (250, 244), "ra": (382, 244),
             "kaf": (52, 312), "kar": (100, 312), "kay": (148, 312)}
    hot = {"", "k", "ka"}
    parts = []

    for name, (x, y) in spots.items():
        if name:
            px, py = spots[name[:-1]]
            on = name in hot
            parts.append(f'  <line x1="{px}" y1="{py}" x2="{x}" y2="{y}" stroke="{KINDS["danger"][0] if on else MUTED}" stroke-width="{2.6 if on else 1.4}"/>')

    for name, (x, y) in spots.items():
        on = name in hot
        parts += [f'  <circle cx="{x}" cy="{y}" r="15" fill="{KINDS["danger"][1] if on else tint}" stroke="{KINDS["danger"][0] if on else blue}" stroke-width="2"/>',
                  text(x, y + 4.5, name[-1:] or "*", "mono strong", "middle")]

    labels = [(52, 340, "kafka"), (100, 356, "karaoke"), (148, 340, "kayak"), (170, 272, "key..."), (250, 272, "kubernetes"), (382, 272, "raft, rate...")]
    parts += [text(x, y, body, "mono dim", "middle") for x, y, body in labels]
    parts.append(lines(32, 392, ["Each circle is 1 letter, and the path from the top to a circle spells", "a prefix. The red path spells 'ka'. Every search that begins with 'ka'",
                                 "lies below the last red circle, and nothing else does."], "sub"))
    save(OUT / "type-trie.svg", WIDTH, 448,
         "A tree of letters. From the top, branches lead to k and r. Below k are a, e and u. Below ka are f, r and y, which "
         "lead to kafka, karaoke and kayak. The path from the top through k to a is marked, and every search that begins "
         "with ka lies below it.",
         "A tree of prefixes", "The searches of the example, letter by letter.", parts)


@figure
def steps_type_lists():
    table_ = ["k     kubernetes 950, kafka 900, karaoke near me 800", "ka    kafka 900, karaoke near me 800, kayak 450", "kaf   kafka 900, kafka vs rabbitmq 300",
              "ke    key value store 700, keyboard 650", "ra    raft 600, rate limiter 500"]
    f = lambda typed, row, shown, active: [("WHAT THE SEARCHER HAS TYPED", [typed], False),
                                           ("STORED LISTS, 1 FOR EACH PREFIX", [("> " + line_) if k == row else line_ for k, line_ in enumerate(table_)], active),
                                           ("SHOWN UNDER THE SEARCH BOX", shown, False)]
    story("steps-type-lists", "1 lookup for each letter typed", [
        (f("", None, ["", "", ""], False), "For every prefix that occurs, the 3 most frequent searches that begin with it have been worked out in advance and stored. Answering is then a matter of looking up 1 row."),
        (f("k", 0, ["kubernetes", "kafka", "karaoke near me"], True), "The searcher types k. The service looks up the row for k and returns its 3 entries. No searching or sorting takes place while the searcher waits."),
        (f("ka", 1, ["kafka", "karaoke near me", "kayak"], True), "A second letter. The row for ka is a different row, prepared in the same way. Kubernetes has dropped out, since it does not begin with ka, and kayak has come in."),
        (f("kaf", 2, ["kafka", "kafka vs rabbitmq", ""], True), "A third letter. Only 2 searches begin with kaf, and both are shown."),
        (f("kafx", None, ["(no suggestion)", "", ""], False), "A fourth letter that leads nowhere. No row exists for kafx, and the service answers with an empty list as quickly as with a full one."),
    ])


@figure
def type_stale():
    rows, bottom = step_rows(100, [
        ("client", "The searcher types 'ka'", "request 1 is sent, and is slow"),
        ("client", "The searcher types 'kaf'", "request 2 is sent, and is fast"),
        ("good", "The answer to request 2 arrives", "the box shows: kafka, kafka vs rabbitmq"),
        ("danger", "The answer to request 1 arrives late", "the box now shows: kafka, karaoke, kayak"),
        ("danger", "The suggestions no longer match the text", "the box says 'kaf' and offers 'kayak'"),
    ])
    parts = [rows, chip(32, bottom + 6, 416, "The cure: show an answer only if it matches the box", "good")]
    save(OUT / "type-stale.svg", WIDTH, bottom + 56,
         "5 steps. The searcher types ka, and request 1 is sent and is slow. The searcher types kaf, and request 2 is sent and "
         "is fast. The answer to request 2 arrives and is shown. The answer to request 1 arrives late and replaces it. The "
         "suggestions no longer match the text in the box. The cure is to show an answer only if it is for the text now in the box.",
         "Answers that arrive out of order", "2 requests, and the first is the slower.", parts)


# ------------------------------------------------ chapters 23 to 28

@figure
def crawl_figures():
    actors("crawl-use-cases", "the crawler", [
        ("cap", "Operator", ["runs the crawl"], S, [("give starting addresses", "POST /v1/seeds"), ("set the rules for a host", "PUT /v1/hosts/{host}/rules"), ("read the progress", "GET /v1/crawls/{id}")]),
        ("glasses", "Indexer", ["uses the pages"], C, [("read the fetched pages", "GET /v1/pages?after=")]),
    ])
    records("crawl-entities", [(C, "Page", ["address   string", "fetched   time", "checksum  u64", "status    200|404|..."]), (T, "Host", ["name      string", "ready_at  time", "rules     robots.txt", "taken     pages so far"])],
            ["A Host is every address on 1 server. The crawler keeps a", "queue and a waiting time for each host, and not for each page."])
    design("crawl-design", "A web crawler", {
        "frontier": (0, 1, "Frontier", "1 queue per host", "stack", S), "fetchers": (1, 1, "Fetchers", "download pages", "chip", T),
        "parser": (2, 1, "Parser", "finds the links", "doc", I), "filter": (3, 1, "Link filter", "drops what was seen", "search", M),
        "rules": (1, 0, "Host rules", "what may be fetched", "lock", O), "pages": (2, 0, "Page store", "every fetched page", "stack", S),
        "seen": (3, 0, "Seen set", "every address so far", "eye", M),
    }, [], [("frontier", "fetchers", 1, "flow"), ("fetchers", "rules", 2, "flow"), ("fetchers", "parser", 3, "flow"), ("parser", "pages", 4, "flow"),
            ("parser", "filter", 5, "flow"), ("filter", "seen", 6, "flow")], [
        "The frontier hands out an address of a host that is ready.", "The fetcher checks the host's rules and downloads the page.", "The parser receives the page.",
        "The page is stored.", "The links of the page go to the filter.", "New addresses return to the frontier."])


@figure
def steps_crawl_frontier():
    f = lambda t, queues, fetched, active: [("TIME", ["t = %d s" % t], False), ("FRONTIER: 1 QUEUE FOR EACH HOST", queues, active), ("FETCHED AT THIS MOMENT", [fetched], False)]
    story("steps-crawl-frontier", "A frontier with 1 queue for each host", [
        (f(0, ["news       news/", "", ""], "> news/", True), "The crawl starts from 1 address. The frontier keeps a separate queue for every host, and each host may be asked once every 2 seconds."),
        (f(1, ["news       news/a, news/b   (may be asked at t = 2)", "shop       shop/", "calendar   calendar/day-1"], "> shop/, calendar/day-1", True),
         "The first page had links to 3 hosts. At 1 second, news has to rest, while shop and calendar have not been asked yet. The crawler fetches 1 page from each of them."),
        (f(2, ["news       news/a, news/b", "shop       shop/item-1, shop/item-2   (at t = 3)", "calendar   calendar/day-2   (at t = 3)"], "> news/a", True),
         "At 2 seconds, news may be asked again. The other 2 hosts are resting. The crawler is never idle while any host is ready, and never asks a host twice within 2 seconds."),
        (f(3, ["news       news/b   (at t = 4)", "shop       shop/item-1, shop/item-2", "calendar   calendar/day-2"], "> shop/item-1, calendar/day-2", True),
         "The pattern continues. Each host receives a request every 2 seconds, however many of its pages are waiting. The total speed of the crawl comes from the number of hosts, and no single host carries it."),
        (f(7, ["news       (empty)", "shop       (empty)", "! calendar   day-5 was not added: 4 pages taken"], "> calendar/day-4", True),
         "The calendar links every day to the next, without end. After 4 pages, the crawler takes no more addresses from that host. 10 pages were fetched in all, and 7 links led to addresses that had been seen before."),
    ])


@figure
def crawl_trap():
    rows, bottom = step_rows(100, [
        ("client", "A page shows the events of 1 day", "calendar/day-1"),
        ("client", "It links to the next day", "calendar/day-2, which links to day-3"),
        ("danger", "Every day exists, for ever", "the site computes each page when asked"),
        ("danger", "The crawler follows without end", "millions of pages with nothing new in them"),
    ])
    parts = [rows, chip(32, bottom + 6, 416, "The cure: a limit on pages and on depth for every host", "good")]
    save(OUT / "crawl-trap.svg", WIDTH, bottom + 56,
         "4 steps. A page shows the events of 1 day. It links to the next day, which links to the day after. Every day exists "
         "for ever, because the site computes each page when asked. A crawler that follows every link never finishes. The cure "
         "is a limit on pages and on depth for every host.",
         "A site that never ends", "An ordinary calendar is enough.", parts)


@figure
def metrics_figures():
    actors("metrics-use-cases", "the monitoring system", [
        ("glasses", "Service", ["reports numbers", "about itself"], C, [("send measurements", "POST /v1/points")]),
        ("cap", "Engineer", ["watches and", "is paged"], S, [("draw a graph", "GET /v1/series?name=&from=&to="), ("define an alert", "PUT /v1/alerts/{name}"), ("be paged when it fires", "a notification, chapter 13")]),
    ])
    records("metrics-entities", [(C, "Series", ["name    string", "labels  key=value, ..."]), (T, "Point", ["series  u64", "time    seconds", "value   f64"]),
                                 (M, "Alert", ["query      string", "threshold  f64", "for        duration"])],
            ["A Series is 1 name with 1 set of label values. Every different", "combination of label values is a separate series."])
    design("metrics-design", "A monitoring system", {
        "services": (0, 0, "Services", "report numbers", "laptop", C), "collector": (1, 0, "Collectors", "receive points", "listen", I),
        "store": (2, 0, "Series store", "compressed blocks", "stack", S), "query": (3, 0, "Query service", "graphs", "curve", T),
        "rollup": (2, 1, "Rollup job", "1 point per minute", "gear", M), "alerts": (3, 1, "Alert evaluator", "runs rules", "clock", O),
    }, [], [("services", "collector", 1, "flow"), ("collector", "store", 2, "flow"), ("store", "query", 3, "flow"), ("rollup", "store", 4, "idle"), ("alerts", "query", 5, "flow")], [
        "Every service sends its measurements every 10 seconds.", "A collector appends each point to its series.", "A graph is a query over a range of time.",
        "Older points are reduced to 1 per minute.", "Every rule is evaluated once a minute."])


@figure
def steps_metrics_delta():
    f = lambda raw, step, change, value, active: [("TIMES AS MEASURED", [raw], active == 1), ("EACH TIME AS ITS STEP FROM THE ONE BEFORE", [step], active == 2),
                                                  ("EACH STEP AS ITS CHANGE FROM THE STEP BEFORE", [change], active == 3), ("VALUES AS THEIR CHANGE FROM THE ONE BEFORE", [value], active == 4)]
    story("steps-metrics-delta", "Storing changes in place of numbers", [
        (f("1760000000  1760000001  1760000002  1760000003", "", "", "", 1), "4 measurements, 1 second apart. Each time is a number of 10 digits and needs 8 bytes when stored as it is."),
        (f("1760000000  1760000001  1760000002  1760000003", "> 1760000000  +1  +1  +1", "", "", 2), "After the first, each time is stored as its distance from the one before. Measurements are taken at a fixed interval, so the distances are small and nearly all the same."),
        (f("1760000000  1760000001  1760000002  1760000003", "1760000000  +1  +1  +1", "> 1760000000  +1  0  0", "", 3),
         "The distances are stored as their change from the distance before. For a steady interval that change is 0 almost every time, and a 0 can be written in a single bit or byte."),
        (f("1760000000  1760000001  1760000002  1760000003", "1760000000  +1  +1  +1", "1760000000  +1  0  0", "> 40  +2  -3  +1", 4),
         "The values are treated in the same way. A response time that moves between 38 and 42 ms changes by a few units from 1 measurement to the next, and a small change needs 1 byte."),
        (f("16 bytes for each point", "", "", "> about 2 bytes for each point", None), "In the simulation, an hour of 3600 points takes 57600 bytes as plain numbers and 7223 bytes as changes, 2 bytes for each point. Nothing has been lost: every original number can be computed back."),
    ])


@figure
def metrics_rollup():
    parts = [text(32, 104, "MINUTE 20: 57 SECONDS AT 40 MS AND 3 SECONDS AT 900 MS", "tab")]

    for k, (name, value, kind) in enumerate([("kept as the average of the minute", 83, "store"), ("kept as the largest value of the minute", 900, "danger")]):
        y = 140 + 56 * k
        parts += [text(32, y - 8, name, "name"), text(448, y - 8, "%d ms" % value, "mono strong", "end"), box(32, y, 416, 18, CARD, EDGE, 6),
                  box(32, y, 416 * value / 900, 18, KINDS[kind][1], KINDS[kind][0], 6)]

    parts.append(lines(32, 252, ["The average says that the minute was a little slow. The largest", "value says that some requests took nearly a second. Both are true,",
                                 "and a store that keeps only the average has lost the second fact."], "sub"))
    save(OUT / "metrics-rollup.svg", WIDTH, 306,
         "2 bars for a minute that contains 57 seconds at 40 ms and 3 seconds at 900 ms. Kept as its average, the minute is 83 "
         "ms. Kept as its largest value, the minute is 900 ms.",
         "What 1 point per minute keeps", "The same 60 measurements, reduced in 2 ways.", parts)


@figure
def sync_figures():
    actors("sync-use-cases", "the sync service", [
        ("glasses", "Person", ["has a laptop", "and a phone"], C, [("change a file on 1 device", "PUT /v1/files/{id}"), ("see it on the other", "GET /v1/changes?after="), ("settle a conflict", "both versions are kept")]),
    ])
    records("sync-entities", [(C, "File", ["id       u64", "path     string", "version  u64", "chunks   checksum[]"]), (T, "Chunk", ["checksum  u64", "bytes     in object store"]),
                              (M, "Device", ["id      string", "cursor  last change seen"])],
            ["A File is a list of chunks and a version. A Device remembers", "how far it has read in the list of changes."])
    design("sync-design", "Syncing a file between 2 devices", {
        "a": (0, 0, "Laptop", "changes a file", "laptop", C), "api": (1, 0, "Sync service", "checks the version", "listen", I),
        "meta": (2, 0, "Metadata store", "files and versions", "stack", S), "chunks": (0, 1, "Chunk store", "see chapter 16", "doc", S),
        "notify": (1, 1, "Notifier", "open connections", "swap", M), "b": (2, 1, "Phone", "fetches the change", "browser", C),
    }, [], [("a", "chunks", 1, "flow"), ("a", "api", 2, "flow"), ("api", "meta", 3, "flow"), ("api", "notify", 4, "flow"), ("notify", "b", 5, "flow")], [
        "The laptop uploads the chunks the store does not have.", "It sends the chunk list and the version it started from.", "The file is updated if that version is still current.",
        "The service tells the notifier.", "The phone is told, and fetches what changed."])


@figure
def sync_chunking():
    parts = [text(32, 104, "CUTS EVERY 1024 BYTES, AFTER 1 BYTE IS ADDED AT THE START", "tab"),
             cells(40, 116, ["c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8"], "idle", 44, 34, hot=(0, 1, 2, 3, 4, 5, 6, 7)),
             lines(32, 174, ["Every cut is now 1 byte later in the content, so every chunk has", "different bytes and a different checksum. All 65 are uploaded again."], "sub"),
             text(32, 234, "CUTS THAT DEPEND ON THE CONTENT, AFTER THE SAME CHANGE", "tab"),
             cells(40, 246, ["c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8"], "idle", 44, 34, hot=(0,)),
             lines(32, 304, ["A cut falls where the bytes themselves say so, and those places", "move with the content. Only the first chunk changed. 1 of 62 is uploaded."], "sub")]
    save(OUT / "sync-chunking.svg", WIDTH, 344,
         "2 rows of 8 chunks after 1 byte is added at the start of a file. With cuts every 1024 bytes, all chunks have "
         "changed. With cuts that depend on the content, only the first chunk has changed.",
         "Where a file is cut into chunks", "A red chunk has to be uploaded again.", parts)


@figure
def steps_sync_conflict():
    f = lambda server, laptop, phone, active: [("THE SERVER", [server], active == "s"), ("THE LAPTOP", [laptop], active == "l"), ("THE PHONE", [phone], active == "p")]
    story("steps-sync-conflict", "2 devices change the same file", [
        (f("notes.txt, version 3", "has version 3", "has version 3", None), "The laptop and the phone both hold version 3 of a file. Both go offline: the laptop on a flight, the phone in the mountains."),
        (f("notes.txt, version 3", "> edits its copy, based on version 3", "> edits its copy, based on version 3", None), "The same person edits the file on both devices. Neither device can know of the other's change."),
        (f("> notes.txt, version 4, written by the laptop", "> uploads, saying: based on version 3", "offline", "s"),
         "The laptop comes online first. It uploads its change and states the version it started from. The server is still at version 3, so the upload is accepted as version 4."),
        (f("notes.txt, version 4", "has version 4", "! uploads, saying: based on version 3: refused", "p"),
         "The phone comes online and uploads with the same statement: based on version 3. The server is at version 4, so somebody else has written in between. The upload is refused as a conflict."),
        (f("> notes.txt (v4) and notes (conflict, phone).txt", "has version 4", "> keeps its edit as a second file", "s"),
         "The service does not choose between the 2 edits, since either choice would throw away something the person wrote. The phone's version is stored beside the other under a different name, and the person decides."),
    ])


@figure
def edit_figures():
    actors("edit-use-cases", "the editing service", [
        ("glasses", "Author", ["types in a", "shared document"], C, [("change the text", "an operation, over an open connection"), ("see what others type", "their operations, pushed"), ("continue offline", "operations wait, then are sent")]),
    ])
    records("edit-entities", [(C, "Document", ["id        u64", "revision  u64", "text      at that revision"]), (T, "Operation", ["document  u64", "author    string", "based_on  revision", "change    insert|delete"])],
            ["An Operation says what was changed and which revision its", "author was looking at. The revision counts operations applied."])
    design("edit-design", "2 authors in 1 document", {
        "a": (0, 0, "Author A", "types", "pencil", C), "server": (1, 0, "Session server", "orders and adjusts", "curve", I),
        "log": (2, 0, "Operation log", "every change, in order", "stack", S), "b": (1, 1, "Author B", "types", "pencil", C),
        "snap": (2, 1, "Snapshots", "the text, now and then", "doc", M),
    }, [], [("a", "server", 1, "flow"), ("server", "log", 2, "flow"), ("server", "b", 3, "flow"), ("log", "snap", 4, "idle")], [
        "An author's change travels to the session server.", "The server adjusts it, numbers it and logs it.", "The adjusted change is sent to every other author.",
        "The text is saved now and then, to shorten the log."])


@figure
def steps_edit_positions():
    f = lambda a, b, note, active: [("ADA'S SCREEN", [a], active in ("a", "both")), ("BOB'S SCREEN", [b], active in ("b", "both")), ("WHAT HAPPENS", [note], False)]
    story("steps-edit-positions", "2 changes by position", [
        (f("cat", "cat", "", None), "Ada and Bob are both looking at the text 'cat'. Positions are counted from 0: c is at 0, a at 1, t at 2, and position 3 is the end."),
        (f("> chat", "> cats", "> ada: put h at 1.   bob: put s at 3.", "both"), "At the same moment, Ada puts an h at position 1 and Bob puts an s at position 3. Each sees their own change at once, and each change is sent to the other."),
        (f("! chast", "chats", "! ada applies bob's change as it is: s at 3", "a"), "Bob's change arrives at Ada's screen: put s at 3. In Ada's text, position 3 is now between a and t, because her h has moved everything after it. The s lands in the wrong place."),
        (f("chast", "chats", "! the 2 screens differ, and will stay different", None), "On Bob's screen, Ada's h at position 1 lands correctly, since nothing before it has moved. The 2 people now have different documents, and no later change will bring them together."),
        (f("> chats", "chats", "> bob's change adjusted: s at 4", "a"), "The cure adjusts a change for what its author had not seen. Bob wrote 'position 3' before Ada's h existed. Her h was put before position 3, so Bob's position becomes 4. Both screens show 'chats'."),
    ])


@figure
def steps_edit_names():
    f = lambda rows, note: [("EVERY CHARACTER, SORTED BY ITS NAME", rows, True), ("WHAT HAPPENS", [note], False)]
    story("steps-edit-names", "A name for every character", [
        (f(["1000   c", "2000   a", "3000   t", "", ""], ""), "In the second approach, a character is never referred to by its position. Each has a name of its own, a number that does not change, and the text is the characters in the order of their names."),
        (f(["1000   c", "> 1500   h", "2000   a", "3000   t", ""], "> ada: a new character named 1500"), "Ada puts h between c and a. She gives it a name between theirs, 1500. The change she sends is: add the character h with the name 1500."),
        (f(["1000   c", "1500   h", "2000   a", "3000   t", "> 4000   s"], "> bob: a new character named 4000"), "Bob's change is: add s with the name 4000. It does not mention a position, so nothing that Ada did can make it wrong. It can be applied before her change or after it, with the same result."),
        (f(["1000   c", "2000   a", "> 2500 from ada   r", "> 2500 from bob   n", "3000   t"], "> both choose the name 2500"), "Both may choose the same number, for instance when both type between a and t. The name therefore includes the author, and equal numbers are ordered by author. Every screen puts r before n."),
    ])


@figure
def match_figures():
    actors("match-use-cases", "the exchange", [
        ("glasses", "Trader", ["buys and sells"], C, [("place an order", "POST /v1/orders"), ("cancel an order", "DELETE /v1/orders/{id}"), ("watch the prices", "a stream of market data")]),
    ])
    records("match-entities", [(C, "Order", ["id        u64", "side      buy|sell", "price     cents", "quantity  shares"]), (T, "Trade", ["buy    order id", "sell   order id", "price  cents", "quantity  shares"]),
                               (M, "Book", ["buys   price -> queue", "sells  price -> queue"])],
            ["The Book holds the orders that are waiting. A Trade is made", "when a new order meets a waiting order at an agreed price."])
    design("match-design", "An exchange for 1 share", {
        "traders": (0, 0, "Traders", "send orders", "laptop", C), "gateway": (1, 0, "Gateway", "checks each order", "listen", I),
        "sequencer": (2, 0, "Sequencer", "1 order of events", "stack", S), "engine": (3, 0, "Matching engine", "1 thread, in memory", "chip", T),
        "journal": (2, 1, "Journal", "every event, on disk", "doc", S), "data": (3, 1, "Market data", "trades and prices", "curve", M),
    }, [], [("traders", "gateway", 1, "flow"), ("gateway", "sequencer", 2, "flow"), ("sequencer", "journal", 3, "flow"), ("sequencer", "engine", 4, "flow"), ("engine", "data", 5, "flow")], [
        "A trader sends an order.", "The gateway checks it and passes it on.", "The sequencer numbers it and writes it to the journal.",
        "The engine matches orders in the order of their numbers.", "Every trade is published."])


@figure
def steps_match_book():
    f = lambda order, sells, buys, trade: [("NEW ORDER", [order], True), ("WAITING TO SELL, LOWEST PRICE FIRST", sells, False), ("WAITING TO BUY, HIGHEST PRICE FIRST", buys, False), ("TRADES", trade, False)]
    story("steps-match-book", "An order book, order by order", [
        (f("orders 1 to 4 have arrived", ["1005   order 2: 30,  order 3: 40", "1010   order 1: 50"], ["1000   order 4: 60", ""], ["none: no buyer offers what any seller asks"]),
         "3 orders to sell and 1 to buy are waiting. The cheapest seller asks 1005 and the buyer offers 1000, so nobody trades. Prices are in cents, and the gap between 1000 and 1005 is called the spread."),
        (f("> order 5: buy 50 at 1005", ["> 1005   order 3: 20", "1010   order 1: 50"], ["1000   order 4: 60", ""], ["> 30 at 1005 with order 2", "> 20 at 1005 with order 3"]),
         "A buyer offers 1005, which the cheapest sellers accept. 2 orders wait at that price, and order 2 arrived first, so it is served first: 30 shares. The remaining 20 come from order 3, which keeps 20."),
        (f("> order 6: buy 100 at 1010", ["(nothing)", ""], ["> 1010   order 6: 30", "1000   order 4: 60"], ["> 20 at 1005 with order 3", "> 50 at 1010 with order 1"]),
         "A buyer offers up to 1010 for 100 shares. The engine takes the cheapest first: 20 at 1005, then 50 at 1010. The sellers are exhausted, and the 30 shares still wanted wait in the book as the best offer to buy."),
        (f("> order 7: sell 80 at 995", ["(nothing)", ""], ["> 1000   order 4: 10", ""], ["> 30 at 1010 with order 6", "> 50 at 1000 with order 4"]),
         "A seller accepts 995 or better. The best buyer offers 1010, and the trade is made at 1010, the price of the order that was waiting. The remaining 50 shares go to order 4 at 1000. 200 shares have traded in all."),
    ])


@figure
def match_replay():
    rows, bottom = step_rows(100, [
        ("store", "Every event goes to the journal first", "order 1, order 2, cancel 2, order 3 ..."),
        ("service", "The engine applies events in that order", "the same input always gives the same book"),
        ("danger", "The machine fails", "the book in its memory is gone"),
        ("good", "A standby replays the journal", "and arrives at exactly the same book"),
    ])
    parts = [rows, lines(32, bottom + 16, ["The engine needs no database. Its state can always be computed", "again from the journal, because it does nothing by chance."], "sub")]
    save(OUT / "match-replay.svg", WIDTH, bottom + 56,
         "4 steps. Every event is written to the journal first. The engine applies events in that order, and the same input "
         "always gives the same book. The machine fails, and the book in its memory is gone. A standby replays the journal "
         "and arrives at exactly the same book.",
         "Recovering by replaying the journal", "A deterministic engine and its record of inputs.", parts)


@figure
def click_figures():
    actors("click-use-cases", "the click counter", [
        ("curly", "Visitor", ["clicks on an", "advertisement"], C, [("a click is recorded", "POST /v1/clicks")]),
        ("glasses", "Advertiser", ["pays for clicks"], T, [("see clicks per minute", "GET /v1/ads/{id}/counts?from=&to="), ("receive the invoice", "from the final counts")]),
    ])
    records("click-entities", [(C, "Click", ["id        u64", "ad        u64", "happened  time", "arrived   time"]), (T, "Window count", ["ad      u64", "window  start time", "count   u32", "final   yes|no"])],
            ["A Click carries the time it happened on the visitor's device.", "A Window count is final once no more clicks are expected."])
    design("click-design", "Counting clicks in windows", {
        "visitors": (0, 0, "Visitors", "click", "browser", C), "collector": (1, 0, "Collectors", "accept clicks", "listen", I),
        "log": (2, 0, "Click log", "every click, kept", "stack", S), "processor": (3, 0, "Stream processor", "windows and watermark", "gear", T),
        "archive": (2, 1, "Archive", "for counting again", "doc", M), "counts": (3, 1, "Count store", "per ad and window", "stack", S),
    }, [], [("visitors", "collector", 1, "flow"), ("collector", "log", 2, "flow"), ("log", "processor", 3, "flow"), ("log", "archive", 4, "idle"), ("processor", "counts", 5, "flow")], [
        "A visitor's browser reports a click.", "The collector appends it to the log.", "The processor counts clicks in windows by event time.",
        "The log is also kept, so that counts can be made again.", "Finished windows are written to the count store."])


@figure
def steps_click_watermark():
    f = lambda click, watermark, open_, done, active: [("CLICK THAT ARRIVES", [click], True), ("WATERMARK: NEWEST EVENT TIME MINUS 5 S", [watermark], active == "w"),
                                                       ("OPEN WINDOWS", open_, active == "o"), ("FINISHED WINDOWS", done, active == "d")]
    story("steps-click-watermark", "Windows, late clicks and a watermark", [
        (f("clicks that happened at 1, 3, 4, 6, 8 and 9 s", "4 s", ["0-10 s: 6", ""], ["none"], "o"),
         "Clicks are counted in windows of 10 seconds, by the time at which they happened. 6 clicks of the first window have arrived. The watermark is the newest event time, 9, minus 5: the counter still expects clicks from after 4 s."),
        (f("! click 3 again, sent twice by a browser", "4 s", ["0-10 s: 6", ""], ["none"], "o"),
         "A browser retried a request, and click 3 arrives a second time. The counter remembers the ids it has counted and ignores the repeat."),
        (f("> a click that happened at 11 s", "6 s", ["0-10 s: 6", "10-20 s: 1"], ["none"], "o"),
         "A click of the second window arrives. The first window stays open, although the clock has passed 10 s, because the watermark is only at 6 s: clicks from before 10 s may still be on their way."),
        (f("> a click that happened at 7 s, arriving at 13 s", "6 s", ["> 0-10 s: 7", "10-20 s: 1"], ["none"], "o"),
         "One was. A phone held this click for 6 seconds before sending it. Its window is still open, and it is counted where it belongs. Counting by arrival time would have put it in the second window."),
        (f("> clicks at 14, 16 and 19 s", "14 s", ["10-20 s: 4", ""], ["> 0-10 s: 7"], "d"),
         "The newest event time reaches 19 s and the watermark 14 s, past the end of the first window. That window is declared finished with a count of 7, and its result is published."),
        (f("! a click that happened at 2 s, arriving at 62 s", "21 s", ["20-30 s: 1", ""], ["0-10 s: 7", "10-20 s: 4"], "d"),
         "A click from the first window arrives a minute late. Its window was finished long ago. The click is not thrown away: it is recorded as late, and a correction of the published count is made afterwards. The true count was 8."),
    ])


# ------------------------------------------------ deployment views

def deploy(name, title, tiers, note=()):
    """A deployment picture: tiers from top to bottom, each a labelled area with up to 3 kinds of
    machine and how many of each run. `tiers` are (label, cards, flow); a card is
    (name, sub, glyph, kind, count), and `flow` is the label on the arrow to the next tier."""
    width, parts, y = 860, [], 108
    alt = "%s. %s" % (title, " ".join(
        "%s: %s." % (label.capitalize(), ", ".join("%s (%s), %s" % (card[0], card[4], card[1]) for card in cards)) for label, cards, flow in tiers))

    for k, (label, cards, flow) in enumerate(tiers):
        parts.append(zone(40, y, 780, 96, label))
        span = 260 * len(cards) - 16
        left = 40 + (780 - span) / 2

        for n, (who, sub, glyph, kind, count) in enumerate(cards):
            parts.append(card(left + 260 * n, y + 24, 244, 56, kind, who, [sub], glyph=glyph))
            parts.append(tag(left + 260 * n + 232, y + 14, count, kind, anchor="end"))

        if k + 1 < len(tiers):
            parts.append(wire([(430, y + 96), (430, y + 96 + 46)], label=flow or None))

        y += 96 + 58

    rows = lines(40, y - 12, list(note), "sub") if note else ""
    save(OUT / (name + ".svg"), width, y + 17 * len(note), alt, title, "Each box is a kind of machine. The label on its corner says how many run.", parts + [rows])


DEPLOYS = {
    "kv": ("The key-value store, deployed", [
        ("applications", [("Applications", "keep their state here", "laptop", C, "120000 req/s")], "120000 req/s"),
        ("edge", [("Load balancers", "active and standby", "swap", I, "x 2"), ("Routers", "stateless, hold the ring", "curve", I, "x 12")], "each request to 1 shard leader"),
        ("storage, in 3 zones", [("Storage nodes", "zone a", "stack", S, "x 8"), ("Storage nodes", "zone b", "stack", S, "x 8"), ("Storage nodes", "zone c", "stack", S, "x 8")], "changes of the ring only"),
        ("control", [("Coordinator", "holds the ring", "key", M, "x 3"), ("Monitoring", "health and metrics", "eye", O, "x 2")], None),
    ], ["The 3 replicas of every shard are in 3 different zones, so that the loss of", "a whole zone leaves a majority of every shard."]),
    "limiter": ("The rate limiter, deployed", [
        ("clients", [("Clients", "1 million of them", "laptop", C, "50000 req/s")], "50000 req/s"),
        ("edge, in 3 zones", [("Load balancers", "1 pair in each zone", "swap", I, "x 6"), ("API gateways", "authenticate and ask", "listen", I, "x 30")], "1 check for each request"),
        ("limiting, in 3 zones", [("Limiter nodes", "token bucket rule", "clock", M, "x 9"), ("Counter store", "1 leader, 2 followers", "stack", S, "x 3")], "requests that passed"),
        ("the protected api", [("API servers", "do the work", "chip", T, "x 100")], None),
    ], ["A limiter node holds no buckets. Any of the 9 can check any request, and", "all of them update the same bucket in the counter store."]),
    "idgen": ("The id generator, deployed", [
        ("callers", [("Services", "need ids for new records", "laptop", C, "1 million ids/s")], "POST /v1/ids"),
        ("edge", [("Load balancers", "any id node will do", "swap", I, "x 2")], "to any node"),
        ("id nodes, in 3 zones", [("Id nodes", "zone a, numbers 0-99", "chip", T, "x 4"), ("Id nodes", "zone b, numbers 100-199", "chip", T, "x 4"), ("Id nodes", "zone c, numbers 200-299", "chip", T, "x 4")], "at startup only"),
        ("control", [("Coordinator", "gives out node numbers", "key", M, "x 3")], None),
    ], ["No arrow joins 1 id node to another. Each makes ids from its own clock,", "its own number and its own counter."]),
    "cache": ("The cache, deployed", [
        ("services", [("Service instances", "cache library inside", "laptop", C, "x 400")], "200000 reads/s, each to 1 node"),
        ("cache nodes, in 3 zones", [("Cache nodes", "zone a", "clock", M, "x 3"), ("Cache nodes", "zone b", "clock", M, "x 3"), ("Cache nodes", "zone c", "clock", M, "x 2")], "misses only: about 2000/s"),
        ("the source of truth", [("Database leader", "takes the writes", "stack", S, "x 1"), ("Database followers", "take the reads", "stack", S, "x 2")], None),
    ], ["There is no load balancer in front of the cache. The library in each", "service hashes the key and talks to the node that owns it."]),
    "lock": ("The lock service, deployed", [
        ("workers", [("Workers", "must be alone in a step", "laptop", C, "x 1000")], "acquire, renew, release"),
        ("lock service, 1 node in each zone", [("Lock node", "zone a, the leader", "lock", M, "x 1"), ("Lock node", "zone b, a follower", "lock", M, "x 1"), ("Lock node", "zone c, a follower", "lock", M, "x 1")], "every write carries a token"),
        ("what the lock protects", [("Storage", "checks the token", "stack", S, "replicated")], None),
    ], ["The lower arrow runs from the workers to the storage. The lock service", "never talks to the storage, which is why the storage must check tokens."]),
    "queue": ("The message queue, deployed", [
        ("producers", [("Producing services", "publish events", "pencil", C, "x 200")], "to the leader of a partition"),
        ("brokers, in 3 zones", [("Brokers", "zone a", "chip", T, "x 4"), ("Brokers", "zone b", "chip", T, "x 4"), ("Brokers", "zone c", "chip", T, "x 4")], "fetched by offset"),
        ("consumers", [("Consumer groups", "1 group for each service", "laptop", C, "x 30"), ("Offset store", "committed offsets", "stack", M, "x 3")], None),
    ], ["Every partition has 3 replicas on brokers in 3 zones, and leadership is", "spread so that each broker leads about a third of what it holds."]),
    "jobs": ("The job scheduler, deployed", [
        ("submitters", [("Services", "submit jobs", "laptop", C, "116 jobs/s")], "POST /v1/jobs"),
        ("scheduler, in 3 zones", [("Load balancers", "any scheduler node", "swap", I, "x 2"), ("Scheduler nodes", "stateless", "clock", I, "x 6"), ("Reclaimer", "1 of 2 is active", "search", M, "x 2")], "conditional writes"),
        ("job store, in 3 zones", [("Job store", "1 leader, 2 followers", "stack", S, "x 3")], "leases, taken by asking"),
        ("workers", [("Workers", "ask, run, report", "chip", T, "x 200")], None),
    ], ["Workers call the scheduler through the same load balancers. The lower", "arrow shows where the work goes, and who asks is the worker."]),
    "notify": ("The notification service, deployed", [
        ("callers", [("Calling services", "report events", "laptop", C, "580 req/s")], "POST /v1/notifications"),
        ("api, in 3 zones", [("Load balancers", "any API node", "swap", I, "x 2"), ("API nodes", "check key, preferences", "listen", I, "x 8"), ("Key store", "keys seen, with outbox", "stack", S, "x 3")], "1 message for each notification"),
        ("queues and senders", [("Queue brokers", "1 queue per priority", "stack", S, "x 6"), ("Senders", "a pool for each channel", "chip", T, "x 40")], "paced below each provider's limit"),
        ("outside", [("Email provider", "outside our control", "swap", O, "x 1"), ("SMS providers", "a second as fallback", "swap", O, "x 2"), ("Push providers", "1 per phone system", "swap", O, "x 2")], None),
    ], ["Each provider has its own circuit breaker and its own pacing, so that", "a failing provider cannot hold up the other channels."]),
    "shortener": ("The URL shortener, deployed", [
        ("visitors", [("Visitors", "open short links", "browser", C, "3900 redirects/s")], "GET /{code}"),
        ("edge, in 3 zones", [("Load balancers", "any web server", "swap", I, "x 2"), ("Web servers", "hold no data", "chip", T, "x 12")], "cache first, then the store"),
        ("data, in 3 zones", [("Cache nodes", "popular links", "clock", M, "x 6"), ("Key-value store", "8 shards x 3 replicas", "stack", S, "x 24"), ("Id counter", "blocks of numbers", "key", O, "x 3")], "1 record for each click"),
        ("counting", [("Click queue", "see chapter 11", "stack", S, "x 3"), ("Click counters", "sum each minute", "gear", T, "x 4")], None),
    ], ["A redirect touches the cache and, on a miss, 1 shard of the store.", "Nothing on that path waits for the counting tier."]),
    "feed": ("The news feed, deployed", [
        ("members", [("Members", "post and read", "browser", C, "10 million")], "reads far outnumber posts"),
        ("services, in 3 zones", [("Load balancers", "by service", "swap", I, "x 4"), ("Post service", "stores posts", "doc", T, "x 20"), ("Feed service", "merges and filters", "curve", I, "x 40")], "lists by member, posts by id"),
        ("data, in 3 zones", [("Feed cache", "1 list for each member", "clock", M, "x 12"), ("Post store", "shards x 3 replicas", "stack", S, "x 30"), ("Follow store", "who follows whom", "stack", S, "x 9")], "1 task for each post"),
        ("fan-out", [("Queue brokers", "see chapter 11", "stack", S, "x 6"), ("Fan-out workers", "copy to followers", "chip", T, "x 60")], None),
    ], ["The feed service reads the cache and the stores. The fan-out workers", "are the only writers of the feed cache."]),
    "objects": ("The object store, deployed", [
        ("applications", [("Applications", "upload and download", "laptop", C, "100 PB stored")], "PUT and GET over HTTP"),
        ("front end, in 3 zones", [("Load balancers", "any API server", "swap", I, "x 6"), ("API servers", "chunk, place, assemble", "chip", I, "x 200")], "names here, bytes there"),
        ("storage, in 3 zones", [("Metadata store", "20 shards x 3 replicas", "stack", S, "x 60"), ("Storage nodes", "36 disks in each", "doc", T, "x 600")], "work that never stops"),
        ("background", [("Scrubbers", "verify every chunk", "eye", M, "on each node"), ("Repair workers", "replace lost copies", "gear", M, "x 20"), ("Garbage collector", "after a day of grace", "gear", O, "x 4")], None),
    ], ["The copies or pieces of a chunk are placed on nodes in different racks", "and zones, so that no single failure removes more than 1 of them."]),
    "stream": ("The video service, deployed", [
        ("viewers", [("Viewers", "players choose quality", "browser", C, "millions")], "pieces, over plain HTTP"),
        ("near the viewers", [("Edge servers", "in hundreds of cities", "clock", M, "x 1000s")], "a miss fetches from the origin"),
        ("origin, in 3 zones", [("Video API", "manifests, rights", "curve", I, "x 20"), ("Object store", "every piece, chapter 16", "doc", S, "origin"), ("Catalogue store", "videos and states", "stack", S, "x 9")], "pieces written once, by encoders"),
        ("upload and encoding", [("Upload service", "stores the source", "listen", I, "x 10"), ("Job scheduler", "see chapter 12", "clock", S, "x 6"), ("Encoders", "1 section at 1 quality", "gear", T, "x 500")], None),
    ], ["The last arrow points upwards in effect: encoders write pieces into the", "object store, and viewers never reach the encoding tier."]),
    "chat": ("The chat service, deployed", [
        ("phones", [("Phones", "1 open connection each", "laptop", C, "50 million online")], "connections, spread by balancers"),
        ("connections, in 3 zones", [("Load balancers", "by connection", "swap", I, "x 20"), ("Gateways", "100000 connections each", "listen", I, "x 500")], "messages in, deliveries out"),
        ("services, in 3 zones", [("Chat service", "numbers, stores, forwards", "curve", T, "x 200"), ("Session store", "who is on which gateway", "search", M, "x 12")], "append to a conversation"),
        ("storage", [("Message store", "100 shards x 3 replicas", "stack", S, "x 300"), ("Notification service", "see chapter 13", "listen", O, "for offline phones")], None),
    ], ["A conversation lives on 1 shard, whose leader gives its messages their", "numbers. Gateways hold connections and nothing else."]),
    "pay": ("The payment system, deployed", [
        ("shops", [("Shops", "charge and refund", "laptop", C, "1000 payments/s")], "POST /v1/payments, with a key"),
        ("api, in 3 zones", [("Load balancers", "any API node", "swap", I, "x 2"), ("Payment API", "stateless", "listen", I, "x 12"), ("Vault", "card numbers, isolated", "lock", D, "x 3")], "1 transaction: key, entries, outbox"),
        ("ledger, in 3 zones", [("Ledger database", "1 leader, 2 followers", "stack", S, "x 3")], "read by background workers"),
        ("background", [("Outbox relay", "publishes events", "gear", M, "x 2"), ("Status poller", "asks about pending", "clock", M, "x 4"), ("Reconciliation", "ledger against bank", "search", M, "nightly")], "charges, and questions"),
        ("outside", [("Card network", "outside our control", "swap", O, "x 1")], None),
    ], ["The ledger confirms a write only when a follower in another zone holds", "it. When no follower can be reached, payments are refused."]),
    "booking": ("The booking system, deployed", [
        ("buyers", [("Buyers", "at the opening of a sale", "browser", C, "33000 arrivals/s")], "everyone, at once"),
        ("in front of the sale", [("Edge servers", "serve the waiting page", "clock", M, "x 100s"), ("Waiting room", "positions and tokens", "listen", I, "x 6")], "500 admitted per second"),
        ("booking, in 3 zones", [("Load balancers", "any API node", "swap", I, "x 2"), ("Booking API", "conditional writes", "listen", I, "x 20"), ("Seat map cache", "up to 2 s old", "clock", M, "x 4")], "1 conditional write for each seat"),
        ("state", [("Seat store", "by show, x 3 replicas", "stack", S, "x 9"), ("Payment system", "see chapter 19", "key", O, "its own tier")], None),
    ], ["The crowd is held in the second tier. The booking tier and the seat", "store see a steady 500 buyers per second, whatever arrives above."]),
    "nearby": ("The ride service, deployed", [
        ("phones", [("Drivers", "report every 4 s", "laptop", C, "500000"), ("Riders", "request rides", "browser", C, "1000 req/s")], "125000 position reports/s"),
        ("edge, in each region", [("Load balancers", "by connection", "swap", I, "x 8"), ("Gateways", "open connections", "listen", I, "x 40"), ("Location service", "position to square", "curve", I, "x 20")], "by region, then by square"),
        ("matching, in each region", [("Grid index", "in memory, by region", "search", M, "x 30"), ("Matching service", "rank and offer", "swap", T, "x 20")], "assignments and states"),
        ("durable state", [("Ride store", "shards x 3 replicas", "stack", S, "x 9"), ("Position log", "routes, for fares", "stack", S, "x 6")], None),
    ], ["The grid index is not replicated. If a node is lost, the drivers of its", "region reappear within 4 seconds, from their next reports."]),
    "typeahead": ("The suggestion service, deployed", [
        ("browsers", [("Browsers", "keep answers they had", "browser", C, "1 million req/s")], "most answered before the service"),
        ("near the users", [("Edge servers", "cache by prefix, 5 min", "clock", M, "x 100s")], "200000 req/s get this far"),
        ("serving, in 3 zones", [("Load balancers", "by range of prefixes", "swap", I, "x 4"), ("Suggestion API", "whole table in memory", "listen", I, "x 24")], "a new table every hour"),
        ("building, offline", [("Search log", "every search made", "doc", S, "x 6"), ("Counting job", "normalise, count, decay", "gear", T, "batch"), ("Trending processor", "the last hour", "gear", M, "x 4")], None),
    ], ["The serving tier only reads. It is fed from below, by a build that runs", "apart from it and can fail without affecting a single request."]),
    "crawl": ("The crawler, deployed", [
        ("control", [("Operator", "seeds and rules", "laptop", C, "1 crawl")], "seed addresses"),
        ("crawling", [("Frontier machines", "hosts assigned by hash", "stack", S, "x 40"), ("Fetchers", "many connections each", "chip", T, "x 300"), ("Resolver cache", "names to addresses", "search", M, "x 6")], "pages, 4000 per second"),
        ("processing", [("Parsers", "links, checksums", "doc", I, "x 60"), ("Seen set", "hashes or a filter", "eye", M, "x 8"), ("Link queue", "to the owning machine", "stack", S, "x 6")], "content"),
        ("storage", [("Page store", "an object store", "doc", S, "1 PB")], None),
    ], ["Every host belongs to exactly 1 frontier machine, which alone keeps", "that host's queue, its waiting time and its rules."]),
    "metrics": ("The monitoring system, deployed", [
        ("what is watched", [("Service instances", "expose current values", "laptop", C, "x 100000")], "asked every 10 seconds"),
        ("collection", [("Collectors", "2 for each group", "listen", I, "x 60")], "1 million points/s, to 2 nodes each"),
        ("storage", [("Series store", "2 copies of each series", "stack", S, "x 40"), ("Block storage", "finished blocks", "doc", S, "object store"), ("Rollup jobs", "per minute, per hour", "gear", M, "x 6")], "queries"),
        ("reading and alerting", [("Query service", "bounded queries", "curve", T, "x 12"), ("Alert evaluators", "both run every rule", "clock", O, "x 2"), ("Second watcher", "watches the watcher", "eye", D, "elsewhere")], None),
    ], ["Nothing in this picture is shared with the services being watched:", "not the machines, not the network path, not the storage."]),
    "sync": ("The sync service, deployed", [
        ("devices", [("Devices", "laptops and phones", "laptop", C, "40 million online")], "commits, and open connections"),
        ("services, in 3 zones", [("Load balancers", "by kind of request", "swap", I, "x 12"), ("Sync service", "compares versions", "listen", I, "x 100"), ("Notifiers", "1 connection per device", "swap", M, "x 400")], "metadata here, bytes there"),
        ("storage", [("Metadata store", "30 shards x 3 replicas", "stack", S, "x 90"), ("Chunk store", "see chapter 16", "doc", S, "1 EB")], None),
    ], ["Devices upload and download chunks directly from the chunk store.", "Only small requests about metadata pass through the sync service."]),
    "edit": ("The editing service, deployed", [
        ("authors", [("Authors", "1 open connection each", "pencil", C, "20 million")], "operations, both ways"),
        ("connections, in 3 zones", [("Load balancers", "by connection", "swap", I, "x 8"), ("Gateways", "route by document", "listen", I, "x 100")], "every author of a document, 1 server"),
        ("sessions", [("Session servers", "1 owner per document", "curve", T, "x 300"), ("Document directory", "which server owns what", "search", M, "x 3")], "append, then acknowledge"),
        ("storage", [("Operation log", "shards x 3 replicas", "stack", S, "x 30"), ("Snapshot store", "an object store", "doc", S, "chapter 16")], None),
    ], ["A document is owned by 1 session server, chosen by hashing its id.", "If that server fails, another loads the snapshot and the log."]),
    "match": ("The exchange, deployed", [
        ("participants", [("Trading firms", "programs, not people", "laptop", C, "210000 orders/s")], "paths of equal length"),
        ("entry", [("Gateways", "syntax, risk, rate", "listen", I, "x 16")], "orders that passed the checks"),
        ("ordering", [("Sequencer", "primary and standby", "stack", S, "x 2"), ("Journal", "3 replicas, in 2 sites", "doc", S, "x 3")], "1 sequence of events"),
        ("matching", [("Matching engines", "1 thread, some shares", "chip", T, "x 10"), ("Standby engines", "apply the same events", "chip", I, "x 10"), ("Market data", "to all, at once", "curve", M, "x 4")], "trades"),
        ("after the trade", [("Clearing", "ordinary databases", "stack", O, "not on the fast path")], None),
    ], ["There is no load balancer anywhere on the fast path. A share is matched", "by 1 engine, and capacity is added by dividing the shares."]),
    "click": ("The click counter, deployed", [
        ("browsers", [("Browsers", "report each click", "browser", C, "100000 clicks/s")], "POST /v1/clicks"),
        ("collection, in 3 zones", [("Load balancers", "any collector", "swap", I, "x 4"), ("Collectors", "append, and nothing else", "listen", I, "x 40")], "partitioned by advertisement"),
        ("the log", [("Click log", "brokers, chapter 11", "stack", S, "x 12"), ("Archive", "every raw click", "doc", S, "73 TB a year")], "read by position"),
        ("counting", [("Stream processors", "state in checkpoints", "gear", T, "x 24"), ("Nightly batch", "final counts", "gear", M, "from the archive")], "1 row for each window"),
        ("serving", [("Count store", "by ad and window", "stack", S, "x 9"), ("Counts API", "dashboards, invoices", "curve", I, "x 8")], None),
    ], ["Collectors stay simple so that they stay up. Everything below the log", "can be stopped and started again without losing a click."]),
}


def _deployment(slug, title, tiers, note):
    def draw():
        deploy(slug + "-deploy", title, tiers, note)

    draw.__name__ = slug + "_deploy"

    return figure(draw)


for _slug, (_title, _tiers, _note) in DEPLOYS.items():
    _deployment(_slug, _title, _tiers, _note)


for name in sys.argv[1:] or list(FIGURES):
    FIGURES[name]()
    print("  " + name)

print("wrote %d figure(s) to %s" % (len(sys.argv[1:]) or len(FIGURES), OUT))
