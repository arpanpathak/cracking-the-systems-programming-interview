"""The linked list chapter's operation animations (ch09-linked-lists.md).

    python3 tools/animations.py list-replace list-drop list-doubly
"""

from anim_kernel import lines_containing
from motion import *  # noqa: F401,F403
from motion import Timeline, render


def link_arrow(p, x0, y0, x1, y1, color, width=2.0, opacity=1.0, bend=0.0, dash=None):
    """A straight or bent arrow from (x0, y0) to (x1, y1)."""
    if opacity <= 0.01:
        return
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2 + bend
    with p.group(opacity=opacity):
        p.path("M %.1f %.1f Q %.1f %.1f %.1f %.1f" % (x0, y0, cx, cy, x1, y1), "none", color,
               width, dash=dash)
        dx, dy = x1 - cx, y1 - cy
        n = max(1e-6, (dx * dx + dy * dy) ** 0.5)
        ux, uy = dx / n, dy / n
        p.path("M %.1f %.1f L %.1f %.1f L %.1f %.1f Z" % (
            x1, y1, x1 - 9 * ux - 4.5 * uy, y1 - 9 * uy + 4.5 * ux,
            x1 - 9 * ux + 4.5 * uy, y1 - 9 * uy - 4.5 * ux), color, "none")


# ------------------------------------------------- 9.4: push and pop with replace

PUSH_POP = lines_containing("src/bin/singly_linked_list.rs",
                            "let old = std::mem::replace(self, List::Empty);",
                            "*self = List::Node {",
                            "next: Link::new(old),",
                            "match std::mem::replace(self, List::Empty) {",
                            "List::Node { value, next } => {",
                            "*self = *next;",
                            "Some(value)")
MOVE_OUT = ["let old = *self;",
            "*self = List::Node { value, next: Link::new(old) };"]
X0, STEP = 250, 92
ROW_A, ROW_B = 162, 262
NODE_W, NODE_H = 64, 44
CALLER = (734, 236)


def list_replace():
    tl = Timeline(caption="", kind="step", code=-1.0, mode="ok", chain="", cy=float(ROW_A),
                  shift=0.0, new_v="", new_a=0.0, place_a=0.0, out_v="", out_u=0.0, out_a=0.0,
                  popped="", ghost="", ghost_a=0.0, hot=0.0, hole=0.0, error=0.0, call="")
    chain = []

    def push(v, k):
        tl.set(call="push_front(%d)" % v)
        tl.set(code=0.0, place_a=1.0)
        tl.to(0.7 * k, in_out, cy=float(ROW_B))
        tl.wait(0.6 * k)
        tl.set(code=1.0, new_v=str(v))
        tl.to(0.4 * k, new_a=1.0, place_a=0.0)
        tl.wait(0.3 * k)
        tl.set(code=2.0)
        tl.to(0.7 * k, in_out, cy=float(ROW_A), shift=1.0)
        chain.insert(0, str(v))
        tl.set(chain=",".join(chain), shift=0.0, new_a=0.0, new_v="")
        tl.wait(0.5 * k)

    def pop(k, popped):
        tl.set(call="pop_front()")
        tl.set(code=3.0, place_a=1.0)
        tl.to(0.7 * k, in_out, cy=float(ROW_B))
        tl.wait(0.5 * k)
        tl.set(code=4.0, hot=1.0, out_v=chain[0], out_u=0.0)
        tl.wait(0.4 * k)
        tl.to(0.15, out_a=1.0)
        tl.to(0.8 * k, in_out, out_u=1.0)
        tl.to(0.15, out_a=0.0)
        popped.append(chain[0])
        tl.set(popped=", ".join(popped))
        tl.set(code=5.0, ghost=chain[0], ghost_a=1.0, hot=0.0)
        del chain[0]
        tl.set(chain=",".join(chain), shift=1.0)
        tl.to(0.7 * k, in_out, cy=float(ROW_A), shift=0.0, place_a=0.0, ghost_a=0.0)
        tl.set(code=6.0)
        tl.wait(0.5 * k)

    tl.chapter("push")
    tl.say("The list is one value of type List, owned by the caller. push_front gets only "
           "&mut self: a borrow of that place.")
    tl.wait(1.2)
    tl.say("replace(self, List::Empty) moves the old list out into old, and leaves Empty in the "
           "place in the same step.")
    push(1, 1.6)
    tl.say("The new node takes the place and owns old through its Box. The place was never "
           "without a valid List.", "insight")
    tl.wait(1.2)
    tl.say("push_front(2) and push_front(3) do the same.")
    push(2, 0.9)
    push(3, 0.9)

    tl.chapter("pop")
    popped = []
    tl.say("pop_front swaps Empty in, and matches on the list it took out.")
    pop(1.5, popped)
    tl.say("The value goes to the caller. *next moves the rest out of its Box and back into the "
           "place, and the empty box is freed.", "insight")
    tl.wait(1.0)
    pop(0.9, popped)
    tl.say("Last pushed, first popped. The list behaves as a stack.", "insight")
    tl.wait(1.2)

    tl.chapter("move out")
    tl.set(mode="fail", code=0.0, call="push_front(4)")
    tl.say("Now write push_front without replace: let old = *self; moves the list out of the "
           "borrowed place.", "fail")
    tl.wait(0.6)
    tl.to(0.6, in_out, cy=float(ROW_B - 40), hole=1.0)
    tl.wait(0.8)
    tl.say("Between the two lines, *self would hold nothing. The owner could see that hole if "
           "anything went wrong in between.", "fail")
    tl.wait(1.2)
    tl.to(0.3, error=1.0)
    tl.say("So the compiler refuses: error[E0507], cannot move out of *self, which is behind a "
           "mutable reference.", "fail")
    tl.to(0.6, in_out, cy=float(ROW_A), hole=0.0)
    tl.wait(2.0)

    def node(p, x, y, label, edge=INK, fill=PAPER, opacity=1.0):
        p.rect(x - NODE_W / 2, y - NODE_H / 2, NODE_W, NODE_H, fill, edge, 8, 1.7,
               opacity=opacity)
        p.text(x, y + 7, label, 18, INK, 700, "middle", mono=True, opacity=opacity)

    def empty_box(p, x, y, color=FAINT, opacity=1.0, label="Empty"):
        p.rect(x - NODE_W / 2, y - 15, NODE_W, 30, STAGE, color, 6, 1.3, dash="4 4",
               opacity=opacity)
        p.text(x, y + 4, label, 11, color, 700, "middle", mono=True, opacity=opacity)

    def draw(p, s, total):
        t = s.t
        title_block(p, "Moving a list out of a borrowed place",
                    "replace swaps a placeholder in, so *self always holds a valid List.")
        if s.call:
            p.text(W - 26, 34, s.call, 15, BRASS, 700, "end", mono=True)
        robot(p, 92, 230, TEAL, 1.0, 1.0, "list owner", "&mut self")
        p.text(X0 - 50, ROW_A - 34, "*self", 13, TEAL, 700, "middle", mono=True)
        p.rect(X0 - NODE_W / 2 - 8, ROW_A - NODE_H / 2 - 8, NODE_W + 16, NODE_H + 16, "none",
               TEAL, 10, 1.4, dash="6 5")
        p.text(X0 - 50, ROW_B - 34, "old", 13, MUTED, 700, "middle", mono=True)
        vals = [v for v in s.chain.split(",") if v]
        cy = s.cy
        for i, v in enumerate(vals):
            x = X0 + (i + s.shift) * STEP
            hot = i == 0 and s.hot > 0.5
            node(p, x, cy, v, BRASS if hot else INK, BRASS_LT if hot else PAPER)
            link_arrow(p, x + NODE_W / 2, cy, x + STEP - NODE_W / 2 - 2, cy, TEAL)
        end_x = X0 + (len(vals) + s.shift) * STEP
        empty_box(p, end_x, cy)
        if s.place_a > 0.01:
            empty_box(p, X0, ROW_A, TEAL, s.place_a, "Empty")
        if s.new_a > 0.01:
            node(p, X0, ROW_A, s.new_v, BRASS, BRASS_LT, s.new_a)
            tx = X0 + s.shift * STEP
            if cy > ROW_A + 30:
                link_arrow(p, X0 + 12, ROW_A + NODE_H / 2, tx - 6, cy - 17, BRASS,
                           opacity=s.new_a, bend=-10)
            else:
                link_arrow(p, X0 + NODE_W / 2, ROW_A, tx - NODE_W / 2 - 2, cy, BRASS,
                           opacity=s.new_a)
        if s.ghost_a > 0.01:
            p.rect(X0 - NODE_W / 2, ROW_B - NODE_H / 2, NODE_W, NODE_H, "none", FAINT, 8, 1.4,
                   dash="4 4", opacity=s.ghost_a)
            p.text(X0, ROW_B + 4, "freed", 11, FAINT, 700, "middle", opacity=s.ghost_a)
        if s.hole > 0.01:
            p.rect(X0 - NODE_W / 2, ROW_A - NODE_H / 2, NODE_W, NODE_H, RUST_LT, RUST, 8, 1.8,
                   opacity=s.hole)
            p.text(X0, ROW_A + 8, "?", 22, RUST, 700, "middle", opacity=s.hole)
        if s.error > 0.01:
            chip(p, 480, 98, "error[E0507]: cannot move out of `*self`", RUST, RUST_LT, 11.5,
                 opacity=clamp(s.error))
        if s.out_a > 0.01:
            x = lerp(X0, CALLER[0] - 50, s.out_u)
            y = lerp(ROW_B, CALLER[1] - 70, s.out_u)
            pill(p, x, y, "value " + s.out_v, BRASS, BRASS_LT, 11, opacity=s.out_a, shadow=None)
        robot(p, CALLER[0], CALLER[1], NIGHT, 1.0, 1.0, "caller",
              "got " + (s.popped or "nothing"))
        lines = MOVE_OUT if s.mode == "fail" else PUSH_POP
        code_panel(p, 26, 300, W - 52, "push_front and pop_front" if s.mode == "ok"
                   else "push_front without replace", lines, s.code, size=10.8, lead=15.5,
                   tint=RUST if s.mode == "fail" else TEAL,
                   reveal=s.timeline.reached("code", t))
        caption(p, tl, t, 464)
        progress(p, tl, t, total, 550)

    return tl, draw, 584


# ------------------------------------------------- 9.6: dropping a long list

LOOP_DROP = lines_containing("benchmarking_examples/lists/boxed_drop.rs",
                             "let mut current = self.head.take();",
                             "while let Some(mut node) = current {",
                             "current = node.next.take();") + ["}"]
GLUE = ["drop(list):        drop its field head",
        "drop(Box<Node>):   drop the Node inside, then free the box",
        "drop(Node):        drop value, then drop next",
        "next is a Box<Node>: go back to the second line"]
NODES = 5
NX0, NSTEP, NY = 200, 78, 150
TOWER_X, TOWER_W, TOWER_BASE, FRAME_H = 610, 184, 288, 22
STACK_BYTES = 8 * 1024 * 1024
FRAME_BYTES = 32


def list_drop():
    tl = Timeline(caption="", kind="step", code=-1.0, mode="glue", frames="", depth=0.0,
                  hot=-1.0, freed="", cur=-1.0, crashed=0.0, count=0.0, cut="")

    def frames_for(names):
        return "|".join(names)

    tl.chapter("default drop")
    tl.say("A list of 270,000 nodes goes out of scope. The first five are drawn; the rest are "
           "the same.")
    tl.wait(1.2)
    tl.say("Rust has no loop for this. It runs the drop code the compiler generates, one call "
           "per value.")
    stack = ["main"]
    tl.set(frames=frames_for(stack), depth=1.0)
    tl.wait(1.0)
    stack.append("drop(list)")
    tl.set(frames=frames_for(stack), depth=2.0, code=0.0)
    tl.wait(1.0)
    for i in range(NODES):
        stack.append("drop(node %d)" % (i + 1))
        tl.set(frames=frames_for(stack), depth=float(len(stack)), hot=float(i),
               code=1.0 if i == 0 else 3.0)
        if i == 0:
            tl.wait(0.6)
            tl.set(code=2.0)
            tl.say("drop(node 1) must drop node 1's next before it can return. That call goes "
                   "on top of the stack.")
            tl.wait(1.8)
        elif i == 1:
            tl.say("Node 2 does the same for node 3. Each frame waits for the one above it.")
            tl.wait(1.4)
        else:
            tl.wait(0.6)
    tl.say("No node is freed yet. The stack holds one frame per node, about 32 bytes each.",
           "insight")
    tl.wait(1.6)
    tl.say("The main thread's stack is 8 MiB: room for about 262,000 of these frames.", "fail")
    tl.set(code=3.0)
    tl.to(3.2, ease_in, depth=float(STACK_BYTES // FRAME_BYTES))
    tl.to(0.3, crashed=1.0)
    tl.say("Frame 262,144 does not fit. thread 'main' has overflowed its stack, and the process "
           "aborts.", "fail")
    tl.wait(2.0)

    tl.chapter("loop drop")
    tl.set(mode="loop", frames=frames_for(["main", "LinkedList::drop"]), depth=2.0, hot=-1.0,
           crashed=0.0, freed="", cur=-1.0, code=-1.0, count=0.0, cut="")
    tl.say("Now the same list with a hand-written Drop. Its body is one loop, in one frame.")
    tl.wait(1.2)
    tl.set(code=0.0, cur=0.0)
    tl.say("take() moves the whole chain out of head into current.")
    tl.wait(1.4)
    freed = []
    for i in range(NODES):
        k = 1.4 if i < 2 else 0.5
        tl.set(code=1.0, hot=float(i))
        if i == 0:
            tl.say("while let moves node 1 out of current into the local node.")
        tl.wait(0.6 * k)
        tl.set(code=2.0, cut=",".join(str(j) for j in range(i + 1)))
        if i == 0:
            tl.say("node.next.take() moves the rest into current. Node 1's next is None now.")
        tl.to(0.4 * k, in_out, cur=float(i + 1))
        tl.wait(0.4 * k)
        tl.set(code=3.0, frames=frames_for(["main", "LinkedList::drop",
                                            "drop(node %d)" % (i + 1)]), depth=3.0)
        if i == 0:
            tl.say("node goes out of scope and is freed. Its next is None, so that drop returns "
                   "at once.")
        tl.wait(0.5 * k)
        freed.append(str(i))
        tl.set(freed=",".join(freed), frames=frames_for(["main", "LinkedList::drop"]),
               depth=2.0, hot=-1.0, count=float(i + 1))
        tl.wait(0.4 * k)
    tl.say("The rest goes the same way. The counter runs to 270,000, and the stack never grows.",
           "insight")
    tl.set(code=1.0)
    tl.to(2.4, in_out, count=270000.0)
    tl.wait(0.4)
    tl.say("At most three frames, whatever the length. list_drop frees five million nodes this "
           "way.", "insight")
    tl.wait(2.0)

    def draw(p, s, total):
        t = s.t
        title_block(p, "Dropping a list: nested calls or a loop",
                    "The default drop nests one call per node. A Drop loop keeps the stack flat.")
        loop = s.mode == "loop"
        frames = [f for f in s.frames.split("|") if f]
        depth = int(round(s.depth))
        crashed = s.crashed > 0.5
        robot(p, 86, 262, RUST if crashed else TEAL, 0.0 if crashed else 1.0, 1.0,
              "main thread", "crashed" if crashed else ("dropping" if depth > 1 else ""))
        # the list
        freed = {int(x) for x in s.freed.split(",") if x}
        cut = {int(x) for x in s.cut.split(",") if x}
        p.text(NX0, NY - 30, "head", 11.5, TEAL, 700, "middle", mono=True)
        for i in range(NODES):
            x = NX0 + i * NSTEP
            if i in freed:
                p.rect(x - 26, NY - 20, 52, 40, "none", LINE, 7, 1.2, dash="4 4")
                p.text(x, NY + 4, "freed", 9.5, FAINT, 600, "middle")
                continue
            hot = abs(s.hot - i) < 0.5
            fill = RUST_LT if crashed else (BRASS_LT if hot else PAPER)
            edge = RUST if crashed else (BRASS if hot else INK)
            p.rect(x - 26, NY - 20, 52, 40, fill, edge, 7, 1.6)
            p.text(x, NY + 6, str(i + 1), 16, INK, 700, "middle", mono=True)
            if i < NODES - 1 and i not in cut:
                link_arrow(p, x + 26, NY, x + NSTEP - 28, NY, TEAL)
        p.text(NX0 + (NODES - 1) * NSTEP + 26, NY + 40, "+ 269,995 more nodes", 11, MUTED, 600,
               "end")
        if loop and s.cur >= 0:
            x = NX0 + min(s.cur, NODES - 0.4) * NSTEP
            p.text(x, NY + 46, "current", 11.5, NIGHT, 700, "middle", mono=True)
            link_arrow(p, x, NY + 34, x, NY + 23, NIGHT, 1.6)
        # the stack
        used = min(1.0, depth * FRAME_BYTES / STACK_BYTES)
        meter(p, TOWER_X, 96, TOWER_W, used, RUST if used > 0.9 else TEAL, "main thread stack",
              "%.2f of 8 MiB" % (used * 8))
        slots = 7
        top = TOWER_BASE - slots * (FRAME_H + 3)
        p.rect(TOWER_X - 6, top - 8, TOWER_W + 12, TOWER_BASE - top + 14, STAGE, LINE, 8, 1.0)
        p.line(TOWER_X - 6, top - 8, TOWER_X + TOWER_W + 6, top - 8, RUST, 2.0, dash="5 4")
        if depth <= slots:
            shown = frames
        else:
            shown = frames[:2] + ["... %s frames ..." % format(depth - 5, ",")] + [
                "drop(node %s)" % format(n, ",") for n in range(depth - 3, depth - 1)]
        for n, name in enumerate(shown):
            y = TOWER_BASE - (n + 1) * (FRAME_H + 3)
            top_frame = n == len(shown) - 1
            fill = RUST_LT if crashed else (BRASS_LT if top_frame and depth > 1 else PAPER)
            edge = RUST if crashed else (BRASS if top_frame else TEAL)
            p.rect(TOWER_X, y, TOWER_W, FRAME_H, fill, edge, 5, 1.2)
            p.text(TOWER_X + TOWER_W / 2, y + 15, name, 10.5, INK, 700, "middle", mono=True)
        if crashed:
            chip(p, TOWER_X + TOWER_W / 2, top + 16, "stack overflow", RUST, RUST_LT, 11.5)
        if loop:
            p.text(TOWER_X + TOWER_W / 2, TOWER_BASE + 18, "freed %s" % format(int(s.count), ","),
                   11.5, TEAL, 700, "middle", mono=True)
        lines = LOOP_DROP if loop else GLUE
        code_panel(p, 26, 316, W - 52, "impl Drop for LinkedList" if loop
                   else "the drop the compiler generates (as steps)", lines, s.code, size=10.8,
                   lead=16.0, tint=TEAL if loop else RUST, reveal=s.timeline.reached("code", t))
        caption(p, tl, t, 432)
        progress(p, tl, t, total, 518)

    return tl, draw, 552


# ------------------------------------------------- 9.8: the doubly linked list

DOUBLY = lines_containing("src/bin/ll.rs",
                          "old_head.borrow_mut().prev = Some(Rc::downgrade(&new_node));",
                          "new_node.borrow_mut().next = Some(old_head);",
                          "self.tail = Some(new_node.clone());",
                          "self.head = Some(new_node);",
                          "prev: self.tail.as_ref().map(Rc::downgrade),",
                          "old_tail.borrow_mut().next = Some(new_node.clone());",
                          "self.head.take().map(|old_head| {",
                          "let next = old_head.borrow_mut().next.take();",
                          "next_node.borrow_mut().prev = None;",
                          "self.head = Some(next_node);",
                          "let node = Rc::try_unwrap(old_head)")
DCOLS = [200, 330, 460, 590]
DROW = 182
VALUES = ["10", "20", "30", "40"]


def list_doubly():
    init = {"caption": "", "kind": "step", "code": -1.0, "mode": "weak", "nexts": "",
            "prevs": "", "head": "", "tail": "", "local": "", "glow": "", "out_v": "",
            "out_u": 0.0, "out_a": 0.0, "popped": "", "leak": 0.0, "dropped": 0.0, "call": ""}
    for v in VALUES:
        init.update({"x" + v: float(DCOLS[0]), "y" + v: float(DROW), "a" + v: 0.0})
    tl = Timeline(**init)
    st = {"next": {}, "prev": {}, "head": None, "tail": None, "order": []}

    def sync(**extra):
        tl.set(nexts=" ".join("%s:%s" % kv for kv in st["next"].items() if kv[1]),
               prevs=" ".join("%s:%s" % kv for kv in st["prev"].items() if kv[1]),
               head=st["head"] or "", tail=st["tail"] or "", **extra)

    def lay(dur):
        tl.to(dur, in_out, **{"x" + v: float(DCOLS[n]) for n, v in enumerate(st["order"])})

    def appear(v, x):
        tl.set(**{"x" + v: float(x), "y" + v: float(DROW - 70), "a" + v: 0.0})
        tl.to(0.4, **{"a" + v: 1.0})

    tl.chapter("push")
    tl.set(call="push_front(10)")
    tl.say("Each node lives in an Rc<RefCell<Node>>. The badge on a node is its strong count.")
    appear("10", DCOLS[0])
    st["order"] = ["10"]
    tl.to(0.5, in_out, y10=float(DROW))
    st["head"] = st["tail"] = "10"
    sync(code=2.0, glow="tail")
    tl.wait(0.8)
    sync(code=3.0, glow="head")
    tl.say("One node: head and tail both hold a strong Rc to it, so its count is 2.")
    tl.wait(1.6)

    tl.set(call="push_front(20)")
    tl.say("push_front(20). The old head, 10, must point back at the new node, weakly.")
    st["order"] = ["20", "10"]
    lay(0.6)
    appear("20", DCOLS[0])
    tl.to(0.5, in_out, y20=float(DROW))
    st["prev"]["10"] = "20"
    sync(code=0.0, glow="p10")
    tl.wait(1.4)
    st["next"]["20"] = "10"
    sync(code=1.0, glow="n20")
    tl.say("20's next takes the strong handle that head held. 10 is still at 2: 20's next and "
           "tail.")
    tl.wait(1.6)
    st["head"] = "20"
    sync(code=3.0, glow="head")
    tl.wait(1.0)

    for v in ("30", "40"):
        tl.set(call="push_back(%s)" % v)
        if v == "30":
            tl.say("push_back mirrors it. The new node's prev is a weak link to the old tail.")
        old = st["tail"]
        st["order"].append(v)
        appear(v, DCOLS[len(st["order"]) - 1])
        tl.to(0.5, in_out, **{"y" + v: float(DROW)})
        st["prev"][v] = old
        sync(code=4.0, glow="p" + v)
        tl.wait(0.9 if v == "30" else 0.5)
        st["next"][old] = v
        sync(code=5.0, glow="n" + old)
        tl.wait(0.9 if v == "30" else 0.5)
        st["tail"] = v
        sync(code=5.0, glow="tail")
        tl.wait(0.6)
    tl.say("Every node has one strong owner on its left: head, or the node before it. The tail "
           "has a second, tail.", "insight")
    sync(glow="")
    tl.wait(2.0)

    tl.chapter("pop_front")
    tl.set(call="pop_front()")
    tl.say("pop_front must move 20's value out. Rc::try_unwrap gives up the node only if this is "
           "the last strong handle.")
    tl.wait(1.4)
    st["head"] = None
    sync(code=6.0, local="20", glow="local")
    tl.say("head.take() moves the handle into old_head. 20's count stays 1: the handle moved.")
    tl.wait(1.8)
    st["next"]["20"] = None
    sync(code=7.0, local="20", glow="")
    tl.say("next.take() takes 20's strong link to 10 into the local next.")
    tl.wait(1.4)
    st["prev"]["10"] = None
    sync(code=8.0, local="20", glow="")
    tl.wait(0.9)
    st["head"] = "10"
    sync(code=9.0, local="20", glow="head")
    tl.wait(1.0)
    tl.set(code=10.0)
    tl.say("old_head is the only strong handle left, count 1, so try_unwrap succeeds. The value "
           "goes to the caller.", "insight")
    tl.set(out_v="20", out_u=0.0)
    tl.to(0.15, out_a=1.0)
    tl.to(0.9, in_out, out_u=1.0, a20=0.0)
    tl.to(0.15, out_a=0.0)
    st["order"].remove("20")
    sync(local="", popped="20")
    lay(0.6)
    tl.wait(1.4)

    tl.chapter("strong prev")
    tl.set(mode="strong", call="drop(list)", code=-1.0, popped="")
    st.update(head="20", tail="40")
    st["order"] = ["20", "10", "30", "40"]
    st["next"] = {"20": "10", "10": "30", "30": "40"}
    st["prev"] = {"10": "20", "30": "10", "40": "30"}
    tl.set(**{"a" + v: 1.0 for v in VALUES})
    lay(0.01)
    sync(glow="")
    tl.say("Now suppose prev were a strong Rc too. The same four nodes, with every link strong.",
           "fail")
    tl.wait(2.0)
    tl.say("Each pair of neighbours holds the other: every count is 2.", "fail")
    tl.wait(1.6)
    tl.say("Drop the list: head and tail let go. 20 and 40 fall to 1; 10 and 30 stay at 2.",
           "fail")
    st["head"] = st["tail"] = None
    sync(glow="")
    tl.to(0.6, dropped=1.0)
    tl.wait(1.6)
    tl.to(0.4, leak=1.0)
    tl.say("No count reaches 0, so no node is ever freed. The memory leaks, with no error.",
           "fail")
    tl.wait(2.4)

    def draw(p, s, total):
        t = s.t
        title_block(p, "A doubly linked list: strong next, weak prev",
                    "The strong count decides when a node is freed. Weak links do not count.")
        if s.call:
            p.text(W - 26, 34, s.call, 15, BRASS, 700, "end", mono=True)
        strong_prev = s.mode == "strong"
        pos = {v: (s["x" + v], s["y" + v]) for v in VALUES if s["a" + v] > 0.01}
        nexts = dict(kv.split(":") for kv in s.nexts.split())
        prevs = dict(kv.split(":") for kv in s.prevs.split())
        count = {v: 0 for v in VALUES}
        for b in nexts.values():
            count[b] += 1
        if strong_prev:
            for b in prevs.values():
                count[b] += 1
        for k in (s.head, s.tail, s.local):
            if k:
                count[k] += 1
        for a, b in nexts.items():
            if a in pos and b in pos:
                (ax, ay), (bx, by) = pos[a], pos[b]
                glow = s.glow == "n" + a
                link_arrow(p, ax + 30, ay - 10, bx - 30, by - 10, BRASS if glow else TEAL,
                           2.6 if glow else 2.0, bend=-22)
        for a, b in prevs.items():
            if a in pos and b in pos:
                (ax, ay), (bx, by) = pos[a], pos[b]
                glow = s.glow == "p" + a
                color = BRASS if glow else (RUST if strong_prev else FAINT)
                link_arrow(p, ax - 30, ay + 10, bx + 30, by + 10, color, 2.2 if glow else 1.8,
                           bend=22, dash=None if strong_prev else "5 4")
        for v, (x, y) in pos.items():
            a = s["a" + v]
            leaked = s.leak > 0.5
            p.rect(x - 30, y - 22, 60, 44, RUST_LT if leaked else PAPER,
                   RUST if leaked else INK, 8, 1.7, opacity=a)
            p.text(x, y + 7, v, 17, INK, 700, "middle", mono=True, opacity=a)
            c = count[v]
            fill = RUST if (strong_prev and s.dropped > 0.5) else (TEAL if c else FAINT)
            p.circle(x + 28, y - 24, 11, fill, PAPER, 2.0, opacity=a)
            p.text(x + 28, y - 20, str(c), 11, PAPER, 700, "middle", mono=True, opacity=a)
        for name, key, dy, color, g in (("head", s.head, -50, TEAL, "head"),
                                        ("tail", s.tail, 52, RUST, "tail"),
                                        ("old_head", s.local, 52, BRASS, "local")):
            if key in pos:
                x, y = pos[key]
                bright = s.glow == g
                p.text(x, y + dy, name, 12.5 if bright else 11.5, BRASS if bright else color,
                       700, "middle", mono=True)
        if s.leak > 0.01:
            chip(p, 395, 268, "leaked: 4 nodes, all counts above 0", RUST, RUST_LT, 11.5,
                 opacity=clamp(s.leak))
        p.text(26, 268, "strong next", 11, TEAL, 700, mono=True)
        p.line(116, 264, 150, 264, TEAL, 2.0)
        prev_label = "strong prev" if strong_prev else "weak prev"
        p.text(172, 268, prev_label, 11, RUST if strong_prev else MUTED, 700, mono=True)
        p.line(258, 264, 292, 264, RUST if strong_prev else FAINT, 1.8,
               dash=None if strong_prev else "5 4")
        if s.out_a > 0.01:
            x = lerp(DCOLS[0], 740, s.out_u)
            y = lerp(DROW, 150, s.out_u)
            pill(p, x, y, "value " + s.out_v, BRASS, BRASS_LT, 11, opacity=s.out_a, shadow=None)
        robot(p, 744, 238, NIGHT, 1.0, 1.0, "caller", "got " + (s.popped or "nothing"))
        code_panel(p, 26, 290, W - 52, "ll.rs: push and pop_front", DOUBLY, s.code, size=10.2,
                   lead=14.4, tint=RUST if strong_prev else TEAL,
                   reveal=s.timeline.reached("code", t))
        caption(p, tl, t, 496)
        progress(p, tl, t, total, 582)

    return tl, draw, 616


def build_list_replace(only=None):
    tl, draw, height = list_replace()
    return render("ch09-list-replace.gif", tl, draw, height, only=only)


def build_list_drop(only=None):
    tl, draw, height = list_drop()
    return render("ch09-list-drop.gif", tl, draw, height, only=only)


def build_list_doubly(only=None):
    tl, draw, height = list_doubly()
    return render("ch09-list-doubly.gif", tl, draw, height, only=only)


BUILDERS = {
    "list-replace": build_list_replace,
    "list-drop": build_list_drop,
    "list-doubly": build_list_doubly,
}
