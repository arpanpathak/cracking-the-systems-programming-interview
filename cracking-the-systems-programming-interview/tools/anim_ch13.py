"""The LRU cache chapter animations (ch13-lru-cache.md), drawn with `motion`.

    python3 tools/animations.py lru-shelf lru-stamps lru-arena
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


# ------------------------------------------------- 13.3: the arena

TOUCH = lines_containing("src/problems/lru_cache_easy.rs",
                         "Some(p) => self.nodes[p].next = next,",
                         "None => self.tail = prev,",
                         "self.nodes[i].next = self.head;",
                         "self.head = Some(i);",
                         "let old_key = std::mem::replace(&mut self.nodes[i].key, key);",
                         "self.lookup_table.remove(&old_key);")
SLOTS_X = [150, 330, 510]
SLOT_TOP = 160


def lru_arena():
    tl = Timeline(caption="", kind="step", code=-1.0, strike=-1.0, nodes="", table="",
                  head=-1, tail=-1, hot=-1, answer="", answer_bad=0.0)

    nodes = []           # [key, value, prev, next]
    table = {}
    state = {"head": None, "tail": None}

    def show(hot=-1):
        tl.set(nodes=";".join("%s,%s,%s,%s" % tuple("-" if v is None else v for v in n)
                              for n in nodes),
               table=" ".join("%s:%d" % kv for kv in table.items()),
               head=-1 if state["head"] is None else state["head"],
               tail=-1 if state["tail"] is None else state["tail"], hot=hot)

    def touch(i, slow=False):
        prev, nxt = nodes[i][2], nodes[i][3]
        linked = prev is not None or nxt is not None or state["head"] == i or state["tail"] == i
        if linked:
            tl.set(code=0.0)
            if prev is not None:
                nodes[prev][3] = nxt
            else:
                state["head"] = nxt
            if nxt is not None:
                nodes[nxt][2] = prev
            else:
                state["tail"] = prev
            show(i)
            tl.set(code=1.0)
            tl.wait(0.9 if slow else 0.4)
        nodes[i][2] = None
        nodes[i][3] = state["head"]
        if state["head"] is not None:
            nodes[state["head"]][2] = i
        tl.set(code=2.0)
        state["head"] = i
        if state["tail"] is None:
            state["tail"] = i
        show(i)
        tl.set(code=3.0)
        tl.wait(0.9 if slow else 0.4)

    def put(key, value, slow=False, drop_remove=False):
        if len(nodes) < 3:
            nodes.append([key, value, None, None])
            table[key] = len(nodes) - 1
            show(len(nodes) - 1)
            tl.wait(0.4)
            touch(len(nodes) - 1, slow)
            return
        i = state["tail"]
        old = nodes[i][0]
        tl.set(code=4.0)
        nodes[i][0], nodes[i][1] = key, value
        show(i)
        tl.wait(0.8 if slow else 0.4)
        if not drop_remove:
            tl.set(code=5.0)
            del table[old]
        table[key] = i
        show(i)
        tl.wait(0.8 if slow else 0.4)
        touch(i, slow)

    tl.chapter("fill")
    tl.say("Capacity 3. Each put pushes a node into the Vec and links it at the head. The links "
           "are indices into the Vec.")
    show()
    tl.wait(0.4)
    put("A", 10)
    put("B", 20)
    put("C", 30)
    tl.say("The list, by next links from the head, is C, B, A. A, at the tail, is next to go.",
           "insight")
    tl.wait(1.0)

    tl.chapter("touch")
    tl.say("get(A) touches slot 0. First detach: A has no next, so it was the tail, and the tail "
           "moves to its prev, B.")
    touch(0, slow=True)
    tl.say("Then push to the front: A.next is the old head C, C.prev is 0, and the head is 0.")
    tl.wait(1.0)

    tl.chapter("reuse")
    tl.say("put(D, 40) with the cache full. The tail is slot 1, B. Its slot is reused: no "
           "allocation, no free.")
    put("D", 40, slow=True)
    tl.say("B's key is removed from the map, D's is added, and slot 1 moves to the front.",
           "insight")
    tl.wait(1.0)

    tl.chapter("no remove")
    tl.say("Run it again without the line lookup_table.remove(&old_key).", "fail")
    nodes.clear()
    table.clear()
    state.update(head=None, tail=None)
    tl.set(strike=5.0, answer="")
    show()
    put("A", 10)
    put("B", 20)
    put("C", 30)
    touch(0)
    put("D", 40, drop_remove=True)
    tl.say("The map still says B is in slot 1. Slot 1 now holds D.", "fail")
    tl.wait(1.0)
    tl.say("get(B) finds slot 1 and returns 40, D's value, for the key B: a wrong answer, "
           "with no error.", "fail")
    tl.set(hot=1, answer="get(B) = Some(40)")
    tl.to(0.4, answer_bad=1.0)
    tl.wait(1.6)

    def draw(p, s, total):
        t = s.t
        title_block(p, "Version 2: a linked list inside a Vec",
                    "Links are indices. touch detaches a node and pushes it at the head.")
        rows = [r.split(",") for r in s.nodes.split(";") if r]
        p.text(26, 96, "lookup_table", 11, MUTED, 600)
        for k, kv in enumerate(s.table.split()):
            key, slot = kv.split(":")
            chip(p, 130 + k * 92, 92, "%s -> %s" % (key, slot), TEAL, TEAL_LT, 12)
        p.text(26, SLOT_TOP - 14, "nodes: Vec<Node>", 11, MUTED, 600)
        for i, x in enumerate(SLOTS_X):
            hot = int(s.hot) == i
            p.rect(x - 78, SLOT_TOP, 156, 92, BRASS_LT if hot else PAPER, BRASS if hot else LINE,
                   8, 1.6 if hot else 1.2)
            p.text(x - 70, SLOT_TOP + 16, "slot %d" % i, 10.5, MUTED, 700)
            if i < len(rows):
                key, value, prev, nxt = rows[i]
                p.text(x, SLOT_TOP + 42, "%s = %s" % (key, value), 18, INK, 700, "middle",
                       mono=True)
                p.text(x, SLOT_TOP + 70, "prev %s  next %s" % (prev, nxt), 12, INK, 600,
                       "middle", mono=True)
            for name, idx, dy, color in (("head", s.head, 110, TEAL), ("tail", s.tail, 128, RUST)):
                if int(idx) == i:
                    p.text(x, SLOT_TOP + dy, name, 12, color, 700, "middle", mono=True)
        # the list, read by following next from the head
        order, seen, cur = [], set(), int(s.head)
        while 0 <= cur < len(rows) and cur not in seen:
            seen.add(cur)
            order.append(rows[cur][0])
            nxt = rows[cur][3]
            cur = int(nxt) if nxt != "-" else -1
        p.text(26, 306, "the list, head to tail:  " + "  ->  ".join(order), 12.5, INK, 700,
               mono=True)
        if s.answer:
            chip(p, 640, 302, s.answer, RUST, RUST_LT, 12, opacity=clamp(s.answer_bad))
        code_panel(p, 26, 322, W - 52, "touch and put", TOUCH, s.code, size=10.4, lead=15.5,
                   strike=int(s.strike) if s.strike >= 0 else None,
                   reveal=s.timeline.reached("code", t))
        caption(p, tl, t, 470)
        progress(p, tl, t, total, 556)

    return tl, draw, 590


def build_lru_shelf(only=None):
    tl, draw, height = lru_shelf()
    return render("ch13-lru-shelf.gif", tl, draw, height, only=only)


def build_lru_stamps(only=None):
    tl, draw, height = lru_stamps()
    return render("ch13-lru-stamps.gif", tl, draw, height, only=only)


def build_lru_arena(only=None):
    tl, draw, height = lru_arena()
    return render("ch13-lru-arena.gif", tl, draw, height, only=only)


BUILDERS = {
    "lru-shelf": build_lru_shelf,
    "lru-stamps": build_lru_stamps,
    "lru-arena": build_lru_arena,
}
