"""The LRU cache chapter animations (ch13-lru-cache.md), drawn with `motion`.

    python3 tools/animations.py lru-shelf lru-stamps lru-touch lru-put
"""

from anim_kernel import lines_containing
from motion import *  # noqa: F401,F403
from motion import Timeline, render

# ------------------------------------------------- 13.1: the policy, on a shelf

REQUESTS = "ABACADAB"
ITEMS = "ABCD"
SLOT_X, SLOT_Y = [262, 352, 442], 176
STORE = (700, 176)
TRAY = (560, 268)
RULES = ["hit: move the entry to the front",
         "miss, room left: fetch it, put it at the front",
         "miss, full: evict the back entry, then fetch",
         "FIFO: a hit changes nothing; evict the oldest arrival"]


def lru_shelf():
    init = {"caption": "", "kind": "step", "code": -1.0, "req": -1, "policy": "LRU",
            "hits": 0.0, "misses": 0.0, "evicted": "", "fetch_u": 0.0, "fetch_a": 0.0,
            "slow": 0.0, "glow": ""}
    for item in ITEMS:
        init.update({"x" + item: float(STORE[0]), "y" + item: float(STORE[1]), "a" + item: 0.0})
    tl = Timeline(**init)

    def place(order, dur):
        moves = {}
        for k, item in enumerate(order):
            moves.update({"x" + item: float(SLOT_X[k]), "y" + item: float(SLOT_Y),
                          "a" + item: 1.0})
        tl.to(dur, in_out, **moves)

    def run(policy, notes, k_fast):
        order, hits, misses = [], 0, 0
        for i, key in enumerate(REQUESTS):
            k = 1.0 if i < 4 else k_fast
            if i in notes:
                tl.say(*notes[i])
            tl.set(req=i)
            tl.wait(0.3 * k)
            if key in order:
                hits += 1
                tl.set(glow=key, code=0.0 if policy == "LRU" else 3.0)
                tl.wait(0.4 * k)
                if policy == "LRU":
                    order.remove(key)
                    order.insert(0, key)
                    place(order, 0.6 * k)
                tl.to(0.2, hits=float(hits))
                tl.set(glow="")
                continue
            misses += 1
            tl.set(code=1.0 if len(order) < 3 else 2.0)
            tl.set(fetch_u=0.0)
            tl.to(0.1, fetch_a=1.0)
            tl.to(0.5 * k, in_out, fetch_u=1.0)
            tl.to(0.1, fetch_a=0.0)
            tl.to(0.3, slow=1.0)
            tl.wait(0.4 * k)
            tl.to(0.2, slow=0.0)
            if len(order) == 3:
                victim = order.pop()
                tl.set(evicted=victim)
                tl.to(0.5 * k, in_out, **{"x" + victim: float(TRAY[0]),
                                          "y" + victim: float(TRAY[1])})
                tl.to(0.3, **{"a" + victim: 0.0})
                tl.set(**{"x" + victim: float(STORE[0]), "y" + victim: float(STORE[1])})
            tl.set(**{"x" + key: float(STORE[0]), "y" + key: float(STORE[1])})
            order.insert(0, key)
            place(order, 0.7 * k)
            tl.to(0.2, misses=float(misses))
        return hits, misses

    tl.chapter("LRU")
    tl.say("The cache keeps three entries on its shelf, most recent on the left. Anything else "
           "is in the slow backing store.")
    tl.wait(0.6)
    run("LRU", {
        0: ("A is not cached: a miss. The cache fetches it from the store, the slow path, and puts "
            "it at the front.",),
        2: ("A again: a hit. No trip to the store, and A moves to the front: it is the most "
            "recent now.",),
        5: ("D misses with the shelf full. B, at the back, is the least recently used, so B is "
            "evicted.",),
        7: ("A was used three times and never left the shelf.",),
    }, 0.6)
    tl.say("3 hits, 5 misses. The key used most stayed in the cache the whole time.", "insight")
    tl.wait(1.2)

    tl.chapter("FIFO")
    tl.say("Now the same requests with first in, first out: a hit does not move anything.",
           "fail")
    reset = {"req": -1, "policy": "FIFO", "hits": 0.0, "misses": 0.0, "evicted": "", "code": -1.0}
    for item in ITEMS:
        reset.update({"a" + item: 0.0, "x" + item: float(STORE[0]), "y" + item: float(STORE[1])})
    tl.set(**reset)
    tl.wait(0.4)
    run("FIFO", {
        5: ("D misses. A arrived first, so FIFO evicts A, the entry used most.", "fail"),
        6: ("The very next request is A: a miss, and another trip to the store.", "fail"),
    }, 0.6)
    tl.say("2 hits, 6 misses. Ignoring use threw out the hottest key.", "fail")
    tl.wait(1.6)

    def draw(p, s, total):
        t = s.t
        title_block(p, "A cache with room for three",
                    "A hit is served from the shelf. A miss is a slow trip to the backing store.")
        scoreboard(p, [("hits", int(round(s.hits)), TEAL), ("misses", int(round(s.misses)), RUST)])
        p.text(26, 98, "requests", 11, MUTED, 600)
        for i, key in enumerate(REQUESTS):
            done = i < int(s.req)
            now = i == int(s.req)
            chip(p, 112 + i * 38, 94, key, BRASS if now else (FAINT if done else INK),
                 BRASS_LT if now else (STAGE if done else PAPER), 12)
        p.text(500, 98, "policy: " + s.policy, 12, RUST if s.policy == "FIFO" else TEAL, 700,
               mono=True)
        robot(p, 110, 252, TEAL, 1.0, 1.0, "cache", "capacity 3")
        for k, x in enumerate(SLOT_X):
            p.rect(x - 36, SLOT_Y - 30, 72, 60, STAGE, LINE, 8, 1.2)
        p.text(SLOT_X[0], SLOT_Y - 40, "most recent", 10.5, MUTED, 600, "middle")
        p.text(SLOT_X[2], SLOT_Y - 40, "evicted next", 10.5, MUTED, 600, "middle")
        robot(p, STORE[0], 252, NIGHT, 1.0, 1.0, "backing store", "slow")
        if s.slow > 0.01:
            chip(p, STORE[0], STORE[1] - 96, "fetching...", NIGHT, NIGHT_LT, 10.5,
                 opacity=clamp(s.slow))
        p.text(TRAY[0], TRAY[1] + 34, "evicted", 10.5, MUTED, 600, "middle")
        for item in ITEMS:
            a = s["a" + item]
            if a <= 0.01:
                continue
            x, y = s["x" + item], s["y" + item]
            hot = s.glow == item
            p.rect(x - 26, y - 22, 52, 44, BRASS_LT if hot else PAPER, BRASS if hot else INK, 6,
                   1.6, opacity=a)
            p.text(x, y + 7, item, 20, INK, 700, "middle", mono=True, opacity=a)
        if s.fetch_a > 0.01:
            x = lerp(SLOT_X[0], STORE[0] - 50, s.fetch_u)
            pill(p, x, SLOT_Y - 52, "fetch " + REQUESTS[int(s.req)], NIGHT, NIGHT_LT, 10.5,
                 opacity=s.fetch_a, shadow=None)
        code_panel(p, 26, 312, W - 52, "the rule", RULES, s.code, size=11.0, lead=17.0,
                   tint=RUST if s.policy == "FIFO" else TEAL, reveal=s.timeline.reached("code", t))
        caption(p, tl, t, 452)
        progress(p, tl, t, total, 538)

    return tl, draw, 572


# ------------------------------------------------- 13.2: stamped events

EVICT = lines_containing("src/problems/lru_cache.rs",
                         "while self.map.len() > self.capacity {",
                         "let Some((key, generation)) = self.recency.pop_front() else {",
                         "Some((_, current)) if *current == generation => {",
                         "self.map.remove(&key);", "_ => {}")


def lru_stamps():
    tl = Timeline(caption="", kind="step", code=-1.0, queue="", mapping="", gen=0.0,
                  popped="", stale=0.0, removed="", mode="evict")

    def show(queue, mapping, gen):
        tl.set(queue=" ".join("%s%d" % e for e in queue),
               mapping=" ".join("%s:%d" % kv for kv in mapping.items()), gen=float(gen))

    queue, mapping, gen = [], {}, 0
    calls = [("put", "a"), ("put", "b"), ("get", "a"), ("put", "c")]
    tl.chapter("stamps")
    tl.say("Capacity 2. Every call adds 1 to generation and stamps the key with it, in the map "
           "and in the queue.")
    tl.wait(0.4)
    for n, (op, key) in enumerate(calls):
        gen += 1
        mapping[key] = gen
        queue.append((key, gen))
        if n == 2:
            tl.say("get(a) stamps a again with 3. The event (a, 1) is still in the queue, but it "
                   "is stale now.")
        if n == 3:
            tl.say("put(c) makes three keys, one too many. The cache must evict.")
        show(queue, mapping, gen)
        tl.wait(1.0 if n >= 2 else 0.7)

    tl.chapter("evict")
    tl.say("Pop the oldest event, (a, 1). The map says a's stamp is 3, not 1: stale. Skip it.")
    tl.set(code=1.0, popped="a1")
    queue.pop(0)
    show(queue, mapping, gen)
    tl.wait(0.4)
    tl.set(code=2.0)
    tl.to(0.4, stale=1.0)
    tl.wait(0.8)
    tl.to(0.3, stale=0.0)
    tl.say("Pop (b, 2). b's stamp in the map is 2: current. b is the least recently used, and is "
           "removed.")
    tl.set(code=1.0, popped="b2")
    queue.pop(0)
    show(queue, mapping, gen)
    tl.wait(0.4)
    tl.set(code=3.0, removed="b")
    del mapping["b"]
    show(queue, mapping, gen)
    tl.say("Each event is pushed once and popped at most once: O(1) per call, amortized.",
           "insight")
    tl.set(popped="")
    tl.wait(1.2)

    tl.chapter("all hits")
    tl.say("Now a run of hits: get(a), get(c), get(a), and so on. Nothing is evicted.", "fail")
    tl.set(code=-1.0, removed="")
    for n in range(8):
        key = "a" if n % 2 == 0 else "c"
        gen += 1
        mapping[key] = gen
        queue.append((key, gen))
        show(queue, mapping, gen)
        tl.wait(0.45)
    tl.say("The map holds 2 keys, and the queue holds 10 events. Only eviction removes events, "
           "so the queue grows with every hit.", "fail")
    tl.wait(1.6)

    def draw(p, s, total):
        t = s.t
        title_block(p, "Version 1: stamped events",
                    "A queue of (key, stamp) events. Only the event that matches the map counts.")
        scoreboard(p, [("generation", int(s.gen), INK)])
        p.text(26, 96, "map: key -> latest stamp", 11, MUTED, 600)
        for k, kv in enumerate(s.mapping.split()):
            key, stamp = kv.split(":")
            chip(p, 60 + k * 90, 122, "%s: %s" % (key, stamp), TEAL, TEAL_LT, 13)
        if s.removed:
            chip(p, 330, 122, "%s removed" % s.removed, RUST, RUST_LT, 12)
        p.text(26, 168, "recency queue: oldest at the front", 11, MUTED, 600)
        events = s.queue.split()
        current = {kv.split(":")[0]: kv.split(":")[1] for kv in s.mapping.split()}
        for k, e in enumerate(events[:9]):
            key, stamp = e[0], e[1:]
            live = current.get(key) == stamp
            chip(p, 64 + k * 80, 196, "(%s, %s)" % (key, stamp), TEAL if live else FAINT,
                 TEAL_LT if live else STAGE, 12)
        if len(events) > 9:
            p.text(64 + 9 * 80 - 30, 200, "+%d" % (len(events) - 9), 13, MUTED, 700)
        p.text(26, 238, "queue length %d, map size %d" % (len(events), len(current)), 12, INK,
               700, mono=True)
        if s.popped:
            chip(p, 600, 122, "popped (%s, %s)" % (s.popped[0], s.popped[1:]), BRASS, BRASS_LT,
                 12)
            if s.stale > 0.01:
                p.text(600, 152, "stale: skip", 11, RUST, 700, "middle", opacity=clamp(s.stale))
        code_panel(p, 26, 262, W - 52, "evict_if_needed", EVICT, s.code, size=10.6, lead=16.0,
                   reveal=s.timeline.reached("code", t))
        caption(p, tl, t, 392)
        progress(p, tl, t, total, 478)

    return tl, draw, 512


# ------------------------------------------------- 13.3: the list moves

LOOKUP = "let i = *self.lookup_table.get(key)?;"
TOUCH = lines_containing("src/problems/lru_cache_easy.rs", LOOKUP,
                         "Some(p) => self.nodes[p].next = next,",
                         "None => self.head = next,",
                         "Some(n) => self.nodes[n].prev = prev,",
                         "None => self.tail = prev,",
                         "self.nodes[i].next = self.head;",
                         "self.nodes[h].prev = Some(i);",
                         "self.head = Some(i);")
PUT = lines_containing("src/problems/lru_cache_easy.rs",
                       "if let Some(&i) = self.lookup_table.get(&key) {",
                       "self.nodes[i].value = value;",
                       "if self.nodes.len() < self.cap {",
                       "self.nodes.push(Node {",
                       "self.lookup_table.insert(key, i);",
                       "if let Some(i) = self.tail {",
                       "let old_key = std::mem::replace(&mut self.nodes[i].key, key);",
                       "self.lookup_table.remove(&old_key);",
                       "self.touch(i);")
KEYS = "ABCDEF"
COLS = [250, 380, 510, 640]
ROW, LIFT, SLOT_Y = 186, 112, 268
HALF_W, HALF_H = 38, 24


class ListScene:
    """An arena LRU list, simulated, with every change sent to a timeline.

    Each key has a position (x, y) and an opacity, so a node can be lifted out of
    the chain, carried to the front, and set back down. The links are drawn from
    the nodes' current positions, so an arrow follows the node it points at.
    """

    def __init__(self, code_lines):
        init = {"caption": "", "kind": "step", "code": -1.0, "strike": -1.0, "call": "",
                "links": "", "head": "", "tail": "", "slots": "", "table": "", "vals": "",
                "hot": "", "doom": "", "look": "", "glow": "", "loose": "", "answer": "",
                "gone": ""}
        for k in KEYS:
            init.update({"x" + k: float(COLS[0]), "y" + k: float(ROW), "a" + k: 0.0})
        self.tl = Timeline(**init)
        self.code_lines = code_lines
        self.next, self.prev, self.slot, self.table, self.val = {}, {}, {}, {}, {}
        self.head = self.tail = None

    # ---- the model, written out to the timeline
    def order(self):
        out, k = [], self.head
        while k is not None and k not in out:
            out.append(k)
            k = self.next.get(k)
        return out

    def sync(self, **extra):
        links = ["n%s:%s" % kv for kv in self.next.items() if kv[1]]
        links += ["p%s:%s" % kv for kv in self.prev.items() if kv[1]]
        self.tl.set(links=" ".join(links), head=self.head or "", tail=self.tail or "",
                    slots=" ".join("%s:%d" % kv for kv in self.slot.items()),
                    table=" ".join("%s:%d" % kv for kv in self.table.items()),
                    vals=" ".join("%s:%s" % kv for kv in self.val.items()), **extra)

    def place(self, keys, dur, start=0):
        self.tl.to(dur, in_out, **{"x" + k: float(COLS[start + n]) for n, k in enumerate(keys)})

    def reset(self, order, values, slots):
        self.next, self.prev, self.val, self.slot = {}, {}, dict(values), dict(slots)
        self.table = dict(slots)
        for a, b in zip(order, order[1:]):
            self.next[a], self.prev[b] = b, a
        self.head, self.tail = (order[0], order[-1]) if order else (None, None)
        moves = {}
        for k in KEYS:
            moves.update({"a" + k: 1.0 if k in order else 0.0, "y" + k: float(ROW)})
        for n, k in enumerate(order):
            moves["x" + k] = float(COLS[n])
        self.tl.set(**moves)
        self.sync(hot="", doom="", look="", glow="", loose="", answer="", gone="", code=-1.0)

    # ---- touch, step by step, as the code does it
    def touch(self, k, k_slow=1.0, line=None, skip_tail=False):
        tl = self.tl
        at = (lambda n: line if line is not None else float(n))
        prev, nxt = self.prev.get(k), self.next.get(k)
        linked = prev or nxt or self.head == k or self.tail == k
        if linked:
            tl.to(0.5 * k_slow, in_out, **{"y" + k: float(LIFT)})
            self.sync(loose=k)
            tl.wait(0.2 * k_slow)
            if prev:
                self.next[prev] = nxt
                self.sync(code=at(1), glow="n" + prev, loose=k)
            else:
                self.head = nxt
                self.sync(code=at(2), glow="head", loose=k)
            tl.wait(0.9 * k_slow)
            if nxt:
                self.prev[nxt] = prev
                self.sync(code=at(3), glow="p" + nxt, loose=k)
            elif not skip_tail:
                self.tail = prev
                self.sync(code=at(4), glow="tail", loose=k)
            else:
                self.sync(code=at(4), glow="", loose=k)
            tl.wait(0.9 * k_slow)
            rest = [x for x in self.order() if x != k]
            self.place(rest, 0.6 * k_slow, start=1)
        else:
            rest = self.order()
            tl.to(0.5 * k_slow, in_out, **{"y" + k: float(LIFT)})
            self.place(rest, 0.6 * k_slow, start=1)
        tl.to(0.8 * k_slow, in_out, **{"x" + k: float(COLS[0])})
        self.prev[k] = None
        self.next[k] = self.head
        self.sync(code=at(5), glow="n" + k, loose="")
        tl.wait(0.7 * k_slow)
        if self.head:
            self.prev[self.head] = k
            self.sync(code=at(6), glow="p" + self.head)
            tl.wait(0.6 * k_slow)
        self.head = k
        if self.tail is None:
            self.tail = k
        tl.to(0.4 * k_slow, in_out, **{"y" + k: float(ROW)})
        self.sync(code=at(7), glow="head")
        tl.wait(0.6 * k_slow)
        self.sync(glow="", hot="")

    # ---- drawing
    def draw_scene(self, p, s, title, sub, code_title, code_y, cap_y, rail_y, total):
        t = s.t
        title_block(p, title, sub)
        if s.call:
            p.text(W - 26, 34, s.call, 15, BRASS, 700, "end", mono=True)
        pos = {k: (s["x" + k], s["y" + k]) for k in KEYS if s["a" + k] > 0.01}
        alpha = {k: s["a" + k] for k in KEYS}
        slots = dict(kv.split(":") for kv in s.slots.split())
        table = dict(kv.split(":") for kv in s.table.split())
        vals = dict(kv.split(":") for kv in s.vals.split())
        # the Vec: slots never move
        p.text(26, SLOT_Y + 18, "nodes: Vec", 11, MUTED, 600)
        owner = {int(v): k for k, v in slots.items() if k in pos}
        for i, x in enumerate(COLS):
            k = owner.get(i)
            p.rect(x - 42, SLOT_Y, 84, 28, STAGE if k else PAPER, LINE, 6, 1.1,
                   dash=None if k else "4 4")
            p.text(x, SLOT_Y + 19, "[%d] %s" % (i, k or ""), 11.5, INK if k else FAINT, 700,
                   "middle", mono=True)
            if k and k in (s.hot, s.doom, s.look):
                edge = RUST if k == s.doom else BRASS
                p.rect(x - 42, SLOT_Y, 84, 28, "none", edge, 6, 2.0)
        # the lookup table
        p.text(26, 92, "lookup_table", 11, MUTED, 600)
        for n, (k, i) in enumerate(table.items()):
            y = 114 + n * 25
            stale = k not in vals or slots.get(k) != i
            looked = s.look == k
            color = RUST if (stale and s.answer) else (BRASS if looked else TEAL)
            fill = RUST_LT if (stale and s.answer) else (BRASS_LT if looked else TEAL_LT)
            chip(p, 26, y, "%s -> %s" % (k, i), color, fill, 11.5, anchor="start")
            if looked and int(i) < len(COLS):
                sx, by = COLS[int(i)], SLOT_Y + 40
                p.path("M 104 %.1f L 180 %.1f L %.1f %.1f L %.1f %.1f" % (y, by, sx, by, sx,
                                                                      SLOT_Y + 29),
                       "none", BRASS, 1.6, dash="5 4")
        # links, drawn from where the nodes are now
        for item in s.links.split():
            kind, rest = item[0], item[1:]
            a, b = rest.split(":")
            if a not in pos or b not in pos:
                continue
            glow = s.glow == kind + a
            faint = s.loose == a
            color = BRASS if glow else (TEAL if kind == "n" else FAINT)
            curve(p, pos[a], pos[b], kind == "n", color, 2.6 if glow else 1.8,
                  0.3 if faint else 1.0)
        # nodes
        for k, (x, y) in pos.items():
            hot = s.hot == k
            doom = s.doom == k
            fill = RUST_LT if doom else (BRASS_LT if hot else PAPER)
            edge = RUST if doom else (BRASS if hot else INK)
            p.rect(x - HALF_W, y - HALF_H, 2 * HALF_W, 2 * HALF_H, fill, edge, 8, 1.7,
                   opacity=alpha[k], shadow="lift" if y < ROW - 4 else None)
            p.text(x, y + 2, "%s = %s" % (k, vals.get(k, "")), 14, INK, 700, "middle",
                   mono=True, opacity=alpha[k])
            if k in slots:
                p.text(x, y + 17, "slot %s" % slots[k], 9.5, MUTED, 600, "middle", mono=True,
                       opacity=alpha[k])
        if s.gone:
            chip(p, 700, 114, "%s removed" % s.gone, RUST, RUST_LT, 11.5)
        for name, key, dy, color, glow in (("head", s.head, -HALF_H - 14, TEAL, "head"),
                                           ("tail", s.tail, HALF_H + 17, RUST, "tail")):
            if key in pos:
                x, y = pos[key]
                bright = s.glow == glow
                p.text(x, y + dy, name, 12.5 if bright else 11.5, BRASS if bright else color,
                       700, "middle", mono=True)
        p.text(COLS[0] - 46, ROW - 50, "most recent", 10, MUTED, 600, "end")
        p.text(COLS[-1] + 46, ROW - 50, "least recent", 10, MUTED, 600)
        if s.answer:
            chip(p, 640, 112, s.answer, RUST, RUST_LT, 12)
        code_panel(p, 26, code_y, W - 52, code_title, self.code_lines, s.code, size=10.4,
                   lead=14.6, strike=int(s.strike) if s.strike >= 0 else None,
                   tint=RUST if s.strike >= 0 or s.kind == "fail" else TEAL,
                   reveal=s.timeline.reached("code", t))
        caption(p, self.tl, t, cap_y)
        progress(p, self.tl, t, total, rail_y)


def curve(p, a, b, forward, color, width, opacity):
    """A next link (above, forward) or a prev link (below) between two nodes."""
    (ax, ay), (bx, by) = a, b
    side = 1 if bx >= ax else -1
    dy = -9 if forward else 9
    x0, y0 = ax + side * HALF_W, ay + dy
    x1, y1 = bx - side * HALF_W, by + dy
    cx = (x0 + x1) / 2
    cy = (min(y0, y1) - 26) if forward else (max(y0, y1) + 26)
    with p.group(opacity=opacity):
        p.path("M %.1f %.1f Q %.1f %.1f %.1f %.1f" % (x0, y0, cx, cy, x1, y1), "none", color,
               width)
        dx, ddy = x1 - cx, y1 - cy
        n = max(1e-6, (dx * dx + ddy * ddy) ** 0.5)
        ux, uy = dx / n, ddy / n
        p.path("M %.1f %.1f L %.1f %.1f L %.1f %.1f Z" % (
            x1, y1, x1 - 9 * ux - 4.5 * uy, y1 - 9 * uy + 4.5 * ux,
            x1 - 9 * ux + 4.5 * uy, y1 - 9 * uy - 4.5 * ux), color, "none")


def lru_touch():
    sc = ListScene(TOUCH)
    tl = sc.tl
    slots = {"A": 0, "B": 1, "C": 2, "D": 3}
    values = {"A": 10, "B": 20, "C": 30, "D": 40}

    def lookup(k, note):
        tl.set(call="get(%s)" % k)
        tl.say(note)
        sc.sync(look=k, code=0.0)
        tl.wait(1.0)
        sc.sync(look="", hot=k)
        tl.wait(0.4)

    tl.chapter("middle")
    sc.reset(list("BACD"), values, slots)
    tl.say("Four entries, most recent on the left. Next links run above, prev links below. The "
           "Vec under them never moves.")
    tl.wait(1.4)
    lookup("C", "get(C). The table says C lives in slot 2. That is a hit, so C must move to the "
                "front.")
    tl.say("Detach: lift C out. Its neighbours are A on the left and D on the right.")
    sc.touch("C", k_slow=1.6)
    tl.say("A now points past the gap to D, and C sits at the front. Four links changed, and no "
           "node was copied.", "insight")
    tl.wait(1.6)

    tl.chapter("tail")
    lookup("D", "get(D). D is the tail: it has no next.")
    tl.say("A's next becomes None, and with no next on D's side, the tail moves back to A.")
    sc.touch("D", k_slow=1.3)
    tl.say("D is the most recent now, and A, at the tail, is the next to be evicted.", "insight")
    tl.wait(1.4)

    tl.chapter("tail left behind")
    sc.reset(list("CBAD"), values, slots)
    tl.set(strike=4.0, call="")
    tl.say("Run get(D) again without None => self.tail = prev.", "fail")
    tl.wait(1.2)
    lookup("D", "get(D) finds slot 3 and lifts D out of the chain.")
    sc.touch("D", k_slow=1.0, skip_tail=True)
    tl.say("tail still names D, which is now at the front. A, the real least recent, has no "
           "marker.", "fail")
    sc.sync(doom="D")
    tl.wait(1.4)
    tl.say("The next put evicts the tail: D, the entry read a moment ago. No panic, only a "
           "wrong eviction.", "fail")
    tl.wait(2.0)

    def draw(p, s, total):
        sc.draw_scene(p, s, "touch: detach, then push to the front",
                      "get(key) finds the slot, lifts the node out, and puts it at the head.",
                      "lookup, then touch", 316, 480, 566, total)

    return tl, draw, 600


def lru_put():
    sc = ListScene(PUT)
    tl = sc.tl

    def put_new(k, v, slow, notes=()):
        i = len(sc.slot)
        tl.set(call="put(%s, %d)" % (k, v))
        if notes:
            tl.say(notes[0])
        sc.sync(code=0.0)
        tl.wait(0.4 * slow)
        sc.sync(code=2.0)
        tl.wait(0.4 * slow)
        sc.val[k] = v
        sc.slot[k] = i
        tl.set(**{"x" + k: float(COLS[i]), "y" + k: float(SLOT_Y - 40), "a" + k: 0.0})
        sc.sync(code=3.0, hot=k)
        tl.to(0.4 * slow, **{"a" + k: 1.0})
        tl.wait(0.4 * slow)
        sc.table[k] = i
        sc.sync(code=4.0, look=k)
        tl.wait(0.6 * slow)
        if len(notes) > 1:
            tl.say(notes[1])
        sc.sync(look="", code=8.0)
        sc.touch(k, k_slow=0.6 * slow, line=8.0)

    tl.chapter("room")
    sc.reset([], {}, {})
    tl.say("Capacity 4, empty. A new key with room left gets the next free slot in the Vec.")
    tl.wait(0.8)
    put_new("A", 10, 1.6, ("put(A, 10). Not in the table, and there is room.",
                           "push puts the node in slot 0, the table records A -> 0, and touch "
                           "makes it the head and the tail."))
    put_new("B", 20, 0.8)
    put_new("C", 30, 0.8)
    put_new("D", 40, 1.0, ("put(D, 40) takes slot 3, the last free one.",))
    tl.say("The chain reads D, C, B, A by recency. The Vec reads A, B, C, D by arrival.",
           "insight")
    tl.wait(1.6)

    tl.chapter("update")
    tl.set(call="put(B, 21)")
    tl.say("put(B, 21). B is in the table, so this is an update: same slot, new value.")
    sc.sync(code=0.0, look="B")
    tl.wait(1.0)
    sc.val["B"] = 21
    sc.sync(code=1.0, look="", hot="B")
    tl.wait(1.0)
    tl.say("Then touch moves B to the front, as get would.")
    sc.sync(code=8.0)
    sc.touch("B", k_slow=0.9, line=8.0)
    tl.wait(0.6)

    def evict(k, v, slow, skip_remove=False, notes=()):
        tl.set(call="put(%s, %d)" % (k, v))
        tl.say(notes[0], *notes[1:2])
        sc.sync(code=0.0)
        tl.wait(0.4 * slow)
        sc.sync(code=2.0)
        tl.wait(0.4 * slow)
        old = sc.tail
        i = sc.slot[old]
        sc.sync(code=5.0, doom=old)
        tl.wait(1.0 * slow)
        # the slot takes the new key: same node, same position
        for name in ("next", "prev"):
            links = getattr(sc, name)
            for a, b in list(links.items()):
                if a == old:
                    links[k] = links.pop(a)
                if b == old:
                    links[a] = k
        sc.head = k if sc.head == old else sc.head
        sc.tail = k if sc.tail == old else sc.tail
        del sc.val[old], sc.slot[old]
        sc.val[k], sc.slot[k] = v, i
        x = COLS[sc.order().index(k)]
        tl.set(**{"x" + k: float(x), "y" + k: float(ROW), "a" + k: 1.0, "a" + old: 0.0})
        sc.sync(code=6.0, doom=k)
        tl.wait(1.0 * slow)
        if not skip_remove:
            del sc.table[old]
            sc.sync(code=7.0, gone=old)
            tl.wait(0.9 * slow)
        sc.table[k] = i
        sc.sync(code=8.0, look=k, doom="", gone="")
        tl.wait(0.7 * slow)
        sc.sync(look="", code=8.0)
        sc.touch(k, k_slow=0.7 * slow, line=8.0)

    tl.chapter("evict")
    evict("E", 50, 1.4, notes=("put(E, 50) with all four slots taken. The tail, A, is the least "
                               "recently used.",))
    tl.say("Slot 0 now holds E. Nothing was freed and nothing was allocated.", "insight")
    tl.wait(1.6)

    tl.chapter("no remove")
    tl.set(strike=7.0)
    tl.say("Now leave out self.lookup_table.remove(&old_key).", "fail")
    tl.wait(1.0)
    evict("F", 60, 0.9, skip_remove=True,
          notes=("put(F, 60) evicts the tail, C, from slot 2.", "fail"))
    tl.set(call="get(C)")
    tl.say("The table still has C -> 2. get(C) follows it to slot 2, which now holds F.", "fail")
    sc.sync(look="C", code=-1.0)
    tl.wait(1.2)
    sc.sync(answer="get(C) = Some(60)")
    tl.say("get(C) returns 60, F's value. The cache answers for a key it evicted, with no "
           "error.", "fail")
    tl.wait(2.2)

    def draw(p, s, total):
        sc.draw_scene(p, s, "put: update, insert, or reuse the tail",
                      "Three cases. Each one ends with touch.",
                      "put", 316, 490, 576, total)

    return tl, draw, 610


def build_lru_shelf(only=None):
    tl, draw, height = lru_shelf()
    return render("ch13-lru-shelf.gif", tl, draw, height, only=only)


def build_lru_stamps(only=None):
    tl, draw, height = lru_stamps()
    return render("ch13-lru-stamps.gif", tl, draw, height, only=only)


def build_lru_touch(only=None):
    tl, draw, height = lru_touch()
    return render("ch13-lru-touch.gif", tl, draw, height, only=only)


def build_lru_put(only=None):
    tl, draw, height = lru_put()
    return render("ch13-lru-put.gif", tl, draw, height, only=only)


BUILDERS = {
    "lru-shelf": build_lru_shelf,
    "lru-stamps": build_lru_stamps,
    "lru-touch": build_lru_touch,
    "lru-put": build_lru_put,
}
