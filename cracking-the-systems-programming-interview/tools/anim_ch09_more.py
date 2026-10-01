"""More linked list animations (ch09-linked-lists.md): building and reading a list,
the two node layouts, removal with a cursor, and pop_back on the doubly linked list.

    python3 tools/animations.py list-build list-layouts list-remove list-pop-back
"""

from anim_ch09_ops import link_arrow
from motion import *  # noqa: F401,F403
from motion import Timeline, render
from motion_kit import Panel, layout

LIST = "src/problems/linked_list.rs"


def box_node(p, x, y, label, edge=INK, fill=PAPER, opacity=1.0, w=56, h=40, size=16, sub=None):
    if opacity <= 0.01:
        return
    p.rect(x - w / 2, y - h / 2, w, h, fill, edge, 8, 1.7, opacity=opacity)
    p.text(x, y + (2 if sub else 6), label, size, INK, 700, "middle", mono=True, opacity=opacity)
    if sub:
        p.text(x, y + 15, sub, 9, MUTED, 600, "middle", mono=True, opacity=opacity)


# ------------------------------------------------- 9.3: from_slice and to_vec

BUILD = Panel(LIST, [("pub fn from_slice(values: &[i32])", "}"), ("pub fn to_vec(", "}")],
              ["let mut head = None;", "for &value in values.iter().rev() {",
               "head = Some(Box::new(ListNode {", "next: head,", ("}));", 0),
               "let mut current = head;", "while let Some(node) = current {",
               "result.push(node.val);", "current = node.next;", ("result", 2), ("head", 3)])
BX = [300, 410, 520]
BY, SLICE_Y, OUT_Y = 196, 104, 268


def list_build():
    init = {"caption": "", "kind": "step", "code": -1.0, "strike": -1.0, "at": -1.0,
            "head": -1.0, "cur": -1.0, "out": "", "order": "123", "freed": "", "call": ""}
    for v in "123":
        init.update({"x" + v: float(BX["123".index(v)]), "y" + v: float(BY), "a" + v: 0.0})
    tl = Timeline(**init)

    def build(order, slow, fail=False):
        """Push the slice's values at the front, last value first (or first value
        first, when `fail` leaves out the .rev())."""
        tl.set(code=0.0, head=-1.0)
        tl.wait(0.6 * slow)
        seq = "123" if fail else "321"
        final = seq[::-1]
        for n, v in enumerate(seq):
            slot = final.index(v)
            tl.set(code=1.0, at=float("123".index(v)))
            tl.wait(0.5 * slow)
            tl.set(**{"x" + v: float(BX[slot]), "y" + v: float(BY - 60)})
            tl.set(code=2.0)
            tl.to(0.4 * slow, **{"a" + v: 1.0})
            tl.set(code=3.0)
            tl.to(0.5 * slow, in_out, **{"y" + v: float(BY)})
            tl.set(code=4.0, head=float(slot))
            tl.wait(0.5 * slow)
        tl.set(at=-1.0, code=10.0)
        tl.wait(0.4 * slow)

    tl.chapter("build")
    tl.set(call="ListNode::from_slice(&[1, 2, 3])")
    tl.say("from_slice builds the list from the back. Each new node goes in front of the list "
           "built so far.")
    tl.wait(1.0)
    tl.say("3 first: it points at None and becomes head. Then 2 points at 3, then 1 at 2.")
    build("321", 1.3)
    tl.say("The last value pushed is values[0], so 1 ends up first. No pointer to the end was "
           "ever needed.", "insight")
    tl.wait(1.6)

    tl.chapter("read")
    tl.set(call="ListNode::to_vec(head)", code=5.0, cur=0.0)
    tl.say("to_vec takes the list by value. current owns the whole chain.")
    tl.wait(1.2)
    out = ""
    for n, v in enumerate("123"):
        tl.set(code=6.0)
        if n == 0:
            tl.say("Each pass moves one box out of current, copies its value into the Vec, and "
                   "moves next into current.")
        tl.to(0.4, in_out, **{"y" + v: float(BY - 40)})
        out += v
        tl.set(code=7.0, out=out)
        tl.wait(0.5)
        tl.set(code=8.0, cur=float(n + 1))
        tl.to(0.4, **{"a" + v: 0.0})
        tl.wait(0.4)
    tl.set(code=9.0)
    tl.say("current is None, so the loop ends. Every box was freed as its pass ended.",
           "insight")
    tl.wait(1.6)

    tl.chapter("no .rev()")
    tl.set(call="from_slice, without .rev()", strike=1.0, out="", cur=-1.0, head=-1.0,
           **{"a" + v: 0.0 for v in "123"})
    tl.say("Now leave out .rev(): the loop pushes 1, then 2, then 3, each at the front.", "fail")
    tl.wait(1.2)
    build("123", 0.8, fail=True)
    tl.say("The list reads 3, 2, 1. Pushing at the front reverses the order of the pushes.",
           "fail")
    tl.wait(1.2)
    tl.say("The tests catch it: to_vec would return [3, 2, 1] for &[1, 2, 3].", "fail")
    tl.set(out="321")
    tl.wait(2.0)

    def draw(p, s, total):
        t = s.t
        title_block(p, "Building a list, then reading it back",
                    "from_slice pushes at the front, last value first. to_vec moves each box out.")
        if s.call:
            p.text(W - 26, 34, s.call, 13, BRASS, 700, "end", mono=True)
        p.text(26, SLICE_Y + 4, "values:", 11.5, MUTED, 600)
        for k, v in enumerate("123"):
            hot = abs(s.at - k) < 0.5
            x = 110 + k * 46
            p.rect(x - 18, SLICE_Y - 16, 36, 30, BRASS_LT if hot else STAGE, BRASS if hot else LINE,
                   5, 1.3)
            p.text(x, SLICE_Y + 5, v, 13, INK, 700, "middle", mono=True)
            p.text(x, SLICE_Y + 28, "[%d]" % k, 9.5, MUTED, 600, "middle", mono=True)
        pos = {v: (s["x" + v], s["y" + v]) for v in "123" if s["a" + v] > 0.01}
        order = sorted(pos, key=lambda v: pos[v][0])
        for a, b in zip(order, order[1:]):
            (ax, ay), (bx, by) = pos[a], pos[b]
            if abs(ay - BY) < 1 and abs(by - BY) < 1:
                link_arrow(p, ax + 28, ay, bx - 30, by, TEAL)
        for v, (x, y) in pos.items():
            box_node(p, x, y, v, opacity=s["a" + v])
        if order:
            last = pos[order[-1]]
            if abs(last[1] - BY) < 1:
                p.text(last[0] + 40, BY + 5, "→ None", 11, FAINT, 600, mono=True)
        if s.head >= 0:
            x = BX[int(round(s.head))]
            p.text(x, BY - 34, "head", 11.5, TEAL, 700, "middle", mono=True)
        if s.cur >= 0:
            x = BX[0] + (BX[1] - BX[0]) * s.cur
            p.text(x, BY + 42, "current" if s.cur < 2.5 else "current = None", 11, NIGHT, 700,
                   "middle", mono=True)
        p.text(26, OUT_Y + 4, "result:", 11.5, MUTED, 600)
        wrong = s.strike >= 0
        for k, v in enumerate(s.out):
            chip(p, 110 + k * 46, OUT_Y, v, RUST if wrong else TEAL, RUST_LT if wrong else TEAL_LT,
                 13)
        BUILD.draw(p, 26, 300, W - 52, "from_slice and to_vec", s, t, strike=s.strike,
                   size=10.2, lead=13.0, tint=RUST if wrong else TEAL)
        caption(p, tl, t, CAP)
        progress(p, tl, t, total, RAIL)

    CAP, RAIL, height = layout(300, len(BUILD), 13.0)
    return tl, draw, height


# ------------------------------------------------- 9.5: two node layouts

BOXED = Panel("benchmarking_examples/lists/boxed.rs",
              [("fn push_front(&mut self, value: T) {", "}"),
               ("fn pop_front(&mut self) -> Option<T> {", "}")],
              ["self.head = Some(Box::new(Node {", "next: self.head.take(),",
               "self.head.take().map(|node| {", "self.head = node.next;", "node.value"])
ENUM = Panel("benchmarking_examples/lists/enum_node.rs",
             [("fn push_front(&mut self, value: T) {", "}"),
              ("fn pop_front(&mut self) -> Option<T> {", "}")],
             [("let old_head = std::mem::replace(&mut self.head, ListNode::Empty);", 0),
              "self.head = ListNode::Next(value, Box::new(old_head));",
              ("let old_head = std::mem::replace(&mut self.head, ListNode::Empty);", 1),
              "self.head = *next_node;", "Some(value)", "ListNode::Empty => None,"])
LANE_B, LANE_E = 118, 228
STACK_X = 210
HEAP_X = [370, 470, 570, 670]


def list_layouts():
    tl = Timeline(caption="", kind="step", cb=-1.0, ce=-1.0, boxed="", enum="", moved_b=0.0,
                  moved_e=0.0, allocs_b=0.0, allocs_e=0.0, fly_b=0.0, fly_e=0.0, none_b=0.0,
                  none_e=0.0, call="")

    def show(b, e):
        tl.set(boxed=",".join(b), enum=",".join(e))

    boxed, enum = [], []   # values, front first; enum keeps enum[0] inline
    tl.chapter("push")
    tl.say("Two lists, the same pushes. Top: Option<Box<Node>>. Bottom: the enum, which keeps "
           "its first node inside the list value.")
    tl.wait(1.6)
    for n, v in enumerate(["10", "20", "30"]):
        k = 1.4 if n == 0 else 0.8
        tl.set(call="push_front(%s)" % v)
        tl.set(cb=0.0)
        if n == 0:
            tl.say("Boxed: one new box. take() moves the old head, an 8-byte pointer, into the "
                   "new node's next.")
        tl.to(0.5 * k, fly_b=1.0)
        tl.set(cb=1.0)
        boxed.insert(0, v)
        show(boxed, enum)
        tl.to(0.4 * k, moved_b=8.0 * (n + 1), allocs_b=float(n + 1), fly_b=0.0)
        tl.wait(0.6 * k)
        tl.set(ce=0.0)
        if n == 0:
            tl.say("Enum: replace moves the old head, 16 bytes held inline, out. Box::new puts "
                   "it on the heap. Here the old head is Empty.")
        tl.to(0.5 * k, fly_e=1.0)
        tl.set(ce=1.0)
        enum.insert(0, v)
        show(boxed, enum)
        tl.to(0.4 * k, moved_e=16.0 * (n + 1), allocs_e=float(n + 1), fly_e=0.0)
        tl.wait(0.8 * k)
        if n == 0:
            tl.say("So the enum's last box holds Empty: one of its boxes holds no value.",
                   "insight")
            tl.wait(1.6)
    tl.say("Three pushes, three boxes each. The boxed list moved 24 bytes; the enum moved 48.",
           "insight")
    tl.wait(1.8)

    tl.chapter("pop")
    tl.set(call="pop_front()", cb=2.0)
    tl.say("pop_front on the boxed list takes the head box and moves its next pointer into "
           "head.")
    tl.wait(0.8)
    tl.set(cb=3.0)
    boxed.pop(0)
    show(boxed, enum)
    tl.to(0.4, allocs_b=2.0)
    tl.set(cb=4.0)
    tl.wait(1.0)
    tl.set(ce=2.0)
    tl.say("The enum swaps Empty in, then *next_node moves the next node's 16 bytes out of its "
           "box and back inline.")
    tl.wait(0.8)
    tl.set(ce=3.0)
    enum.pop(0)
    show(boxed, enum)
    tl.to(0.4, allocs_e=2.0, moved_e=64.0)
    tl.set(ce=4.0)
    tl.wait(1.4)

    tl.chapter("empty")
    tl.say("Pop until both lists are empty. Then one more pop_front on each.", "fail")
    for _ in range(2):
        boxed.pop(0)
        enum.pop(0)
        show(boxed, enum)
        tl.wait(0.5)
    tl.set(allocs_b=0.0, allocs_e=0.0, call="pop_front() on an empty list", cb=2.0, ce=5.0)
    tl.wait(0.8)
    tl.to(0.3, none_b=1.0, none_e=1.0)
    tl.say("Both return None. map on an empty Option does nothing; the enum's match takes "
           "the Empty arm. Neither panics.", "fail")
    tl.wait(2.2)

    def draw(p, s, total):
        t = s.t
        title_block(p, "Two node layouts, push by push",
                    "Option<Box<Node>> moves an 8-byte pointer. The enum moves a 16-byte node.")
        if s.call:
            p.text(W - 26, 34, s.call, 13, BRASS, 700, "end", mono=True)
        for lane, label, vals, moved, allocs, fly, none_a, enum_lane in (
                (LANE_B, "boxed", s.boxed, s.moved_b, s.allocs_b, s.fly_b, s.none_b, False),
                (LANE_E, "enum", s.enum, s.moved_e, s.allocs_e, s.fly_e, s.none_e, True)):
            v = [x for x in vals.split(",") if x]
            p.text(26, lane - 28, label, 12, INK, 700, mono=True)
            p.text(26, lane - 12, "moved %d B, %d boxes" % (int(round(moved)), int(round(allocs))),
                   10.5, MUTED, 600, mono=True)
            # the list value on the stack
            p.text(STACK_X, lane - 32, "head (stack)", 9.5, MUTED, 600, "middle")
            if enum_lane:
                p.rect(STACK_X - 50, lane - 20, 100, 40, TEAL_LT, TEAL, 8, 1.6)
                inline = ("Next(%s)" % v[0]) if v else "Empty"
                p.text(STACK_X, lane + 5, inline, 12, INK, 700, "middle", mono=True)
                p.text(STACK_X + 54, lane + 28, "16 B inline", 9, MUTED, 600, "end")
                heap = v[1:] + ["Empty"] if v else []
            else:
                p.rect(STACK_X - 34, lane - 20, 68, 40, TEAL_LT, TEAL, 8, 1.6)
                p.text(STACK_X, lane + 5, "ptr" if v else "None", 12, INK, 700, "middle",
                       mono=True)
                p.text(STACK_X + 38, lane + 28, "8 B", 9, MUTED, 600, "end")
                heap = v
            prev_x = STACK_X + (50 if enum_lane else 34)
            for k, h in enumerate(heap):
                x = HEAP_X[k]
                empty = h == "Empty"
                box_node(p, x, lane, h, FAINT if empty else INK, STAGE if empty else PAPER,
                         w=70, size=12 if empty else 15)
                link_arrow(p, prev_x + 2, lane, x - 37, lane, TEAL)
                prev_x = x + 35
            if fly > 0.01:
                x = lerp(STACK_X, HEAP_X[0], fly)
                pill(p, x, lane - 30, "16 B" if enum_lane else "8 B", BRASS, BRASS_LT, 10,
                     opacity=min(1.0, fly * 3), shadow=None)
            if none_a > 0.01:
                chip(p, 520, lane, "pop_front() = None", RUST, RUST_LT, 11.5, opacity=none_a)
        p.text(HEAP_X[0] - 30, LANE_B - 32, "heap", 9.5, MUTED, 600)
        top = BOXED.draw(p, 26, 284, 300, "boxed.rs", s, t, track="cb", size=9.6, lead=12.8)
        ENUM.draw(p, 336, 284, W - 362, "enum_node.rs", s, t, track="ce", size=9.6, lead=12.8,
                  tint=NIGHT)
        caption(p, tl, t, CAP)
        progress(p, tl, t, total, RAIL)

    CAP, RAIL, height = layout(284, max(len(BOXED), len(ENUM)), 12.8)
    return tl, draw, height


# ------------------------------------------------- 9.4: removing with a cursor

REMOVE = Panel(LIST, [("pub fn remove_all(", "}")],
               ["let mut cursor = &mut head;", "while cursor.is_some() {", "if node.val == target {",
                "let next = node.next.take();", "*cursor = next;",
                "cursor = &mut cursor", ("head", 2)])
SKIP = ["while cursor.is_some() {",
        "    let node = cursor",
        "        .as_mut()",
        "        .expect(\"checked by is_some\");",
        "    if node.val == target {",
        "        let next = node.next.take();",
        "        *cursor = next;",
        "    }",
        "    // advances after every node, removed or not",
        "    cursor = &mut cursor",
        "        .as_mut()",
        "        .expect(\"checked by is_some\")",
        "        .next;",
        "}"]
RX = [190, 300, 410, 520, 630]
RY = 182


def list_remove():
    tl = Timeline(caption="", kind="step", code=-1.0, mode="ok", vals="", xs="", cur=-1.0,
                  test=-1.0, drop="", drop_u=0.0, result="", call="")

    def run(values, target, slow, skip=False, notes=None):
        """remove_all, step by step. `cur` is the link the cursor holds: -1 is head,
        k is node k's next. `skip` advances after a removal, the bug."""
        notes = notes or {}
        live = list(range(len(values)))         # node ids still linked
        tl.set(vals=",".join(values), xs=",".join(str(RX[k]) for k in range(len(values))),
               cur=-1.0, test=-1.0, drop="", result="")
        tl.set(code=0.0)
        tl.wait(0.8 * slow)
        pos = 0                                 # index into live of the node under test
        link = -1
        while pos < len(live):
            node = live[pos]
            tl.set(code=1.0 if not skip else 0.0)
            tl.set(test=float(node), code=2.0 if not skip else 4.0)
            if ("test", node) in notes:
                tl.say(*notes[("test", node)])
            tl.wait(0.7 * slow)
            if values[node] == target:
                tl.set(code=3.0 if not skip else 5.0, drop=str(node))
                tl.to(0.5 * slow, in_out, drop_u=1.0)
                live.pop(pos)
                tl.set(code=4.0 if not skip else 6.0,
                       vals=",".join(values[k] if k in live else "" for k in range(len(values))),
                       drop="", drop_u=0.0, test=-1.0)
                if ("drop", node) in notes:
                    tl.say(*notes[("drop", node)])
                tl.wait(0.9 * slow)
                if skip and pos < len(live):
                    link = live[pos]
                    pos += 1
                    tl.set(code=9.0, cur=float(link))
                    tl.wait(0.8 * slow)
            else:
                link = node
                pos += 1
                tl.set(code=5.0 if not skip else 9.0, cur=float(link), test=-1.0)
                tl.wait(0.6 * slow)
        tl.set(code=6.0 if not skip else -1.0, test=-1.0,
               result=" -> ".join(values[k] for k in live) or "None")
        tl.wait(1.0 * slow)

    tl.chapter("remove 2")
    tl.set(call="remove_all([2, 1, 2, 2, 3], 2)")
    tl.say("cursor is not a node. It is a mutable borrow of a link: first head itself.")
    run(["2", "1", "2", "2", "3"], "2", 1.4, notes={
        ("test", 0): ("The link points at a 2. It matches.",),
        ("drop", 0): ("take() moves the 2's next out, and *cursor = next makes head skip the "
                      "node. The 2 is freed. The cursor stays on head.",),
        ("test", 1): ("Now the link points at 1. It stays, so the cursor moves on to 1's next "
                      "link.",),
        ("drop", 2): ("The second 2 is unlinked the same way. The cursor stays, so it checks "
                      "the node that slid in.",),
        ("drop", 3): ("That was the third 2. Two matches in a row cost nothing extra.",),
    })
    tl.say("One pass, each node checked once, no node copied. The head was removed with the "
           "same two lines as any other node.", "insight")
    tl.wait(1.6)

    tl.chapter("absent")
    tl.set(call="remove_all([1, 3], 2)")
    tl.say("A target that is not there: the cursor walks to the end, and nothing changes.",
           "fail")
    run(["1", "3"], "2", 0.7)
    tl.wait(0.8)

    tl.chapter("all match")
    tl.set(call="remove_all([7, 7, 7], 7)")
    tl.say("Every node matches. The cursor never leaves head, and head ends as None.", "fail")
    run(["7", "7", "7"], "7", 0.7)
    tl.wait(0.8)

    tl.chapter("advance always")
    tl.set(mode="skip", call="remove_all([1, 2, 2, 3], 2), advancing every time")
    tl.say("Now a version that moves the cursor after every node, removed or not.", "fail")
    run(["1", "2", "2", "3"], "2", 1.0, skip=True, notes={
        ("drop", 1): ("The first 2 is unlinked, and the link now points at the second 2. Then "
                      "the cursor moves past it, unchecked.", "fail"),
    })
    tl.say("The second 2 was never tested, so it stays: 1, 2, 3. A test with two matches in a "
           "row catches it.", "fail")
    tl.wait(2.2)

    def draw(p, s, total):
        t = s.t
        title_block(p, "Removing nodes with a cursor",
                    "The cursor borrows one link. A match is unlinked by moving its next into it.")
        if s.call:
            p.text(W - 26, 34, s.call, 12, BRASS, 700, "end", mono=True)
        vals = s.vals.split(",") if s.vals else []
        xs = [float(x) for x in s.xs.split(",")] if s.xs else []
        live = [k for k, v in enumerate(vals) if v]
        # head and the links, drawn from the head box through the live nodes
        p.rect(60, RY - 18, 64, 36, TEAL_LT, TEAL, 7, 1.5)
        p.text(92, RY + 5, "head", 12, INK, 700, "middle", mono=True)
        chain = [-1] + live
        for a, b in zip(chain, chain[1:] + [None]):
            ax = 124 if a == -1 else xs[a] + 26
            hot = abs(s.cur - a) < 0.5
            color = BRASS if hot else TEAL
            if b is None:
                p.text(ax + 14, RY + 5, "None", 11, FAINT, 600, mono=True)
                if hot:
                    p.text(ax + 26, RY - 26, "cursor", 11.5, BRASS, 700, "middle", mono=True)
                continue
            bx = xs[b] - 28
            link_arrow(p, ax + 2, RY, bx, RY, color, 3.0 if hot else 2.0,
                       bend=-26 if bx - ax > 120 else 0)
            if hot:
                p.text((ax + bx) / 2, RY - 30 if bx - ax > 120 else RY - 18, "cursor", 11.5,
                       BRASS, 700, "middle", mono=True)
        for k in range(len(vals)):
            dropping = s.drop == str(k)
            if not vals[k] and not dropping:
                continue
            y = RY + (70 * s.drop_u if dropping else 0)
            testing = abs(s.test - k) < 0.5
            fill = RUST_LT if dropping else (BRASS_LT if testing else PAPER)
            edge = RUST if dropping else (BRASS if testing else INK)
            label = vals[k] or s.vals.split(",")[k]
            box_node(p, xs[k], y, label or "?", edge, fill,
                     opacity=1.0 - 0.7 * s.drop_u if dropping else 1.0)
        if s.result:
            bad = s.mode == "skip"
            chip(p, W / 2, RY + 74, "result: " + s.result, RUST if bad else TEAL,
                 RUST_LT if bad else TEAL_LT, 12)
        if s.mode == "skip":
            code_panel(p, 26, 290, W - 52, "a version that advances after every node", SKIP,
                       s.code, size=10.2, lead=13.0, tint=RUST)
        else:
            REMOVE.draw(p, 26, 290, W - 52, "remove_all", s, t, size=10.2, lead=13.0)
        caption(p, tl, t, CAP)
        progress(p, tl, t, total, RAIL)

    CAP, RAIL, height = layout(290, max(len(REMOVE), len(SKIP)), 13.0)
    return tl, draw, height


# ------------------------------------------------- 9.8.3: pop_back on the doubly list

POP_BACK = Panel("src/bin/ll.rs", [("pub fn pop_back(&mut self) -> Option<T> {", "}")],
                 ["self.tail.take().map(|old_tail| {", ".prev", ".and_then(|w| w.upgrade());",
                  "prev_node.borrow_mut().next = None;", "self.tail = Some(prev_node);",
                  "self.head = None; // list becomes empty", "let node = Rc::try_unwrap(old_tail)",
                  "})"])
PX = [250, 380, 510]
PY = 178


def list_pop_back():
    tl = Timeline(caption="", kind="step", code=-1.0, vals="10,30,40", head="10", tail="40",
                  local="", up="", nexts="10:30 30:40", prevs="30:10 40:30", out_v="",
                  out_u=0.0, out_a=0.0, got="", none=0.0, call="")

    def counts(s):
        c = {}
        for v in [x for x in s.vals.split(",") if x]:
            c[v] = 0
        for kv in s.nexts.split():
            c[kv.split(":")[1]] = c.get(kv.split(":")[1], 0) + 1
        for k in (s.head, s.tail, s.local, s.up):
            if k:
                c[k] = c.get(k, 0) + 1
        return c

    tl.chapter("pop_back")
    tl.set(call="pop_back()")
    tl.say("The list after pop_front: 10, 30, 40. pop_back must reach 30 from 40, through a "
           "weak link.")
    tl.wait(1.6)
    tl.set(code=0.0, tail="", local="40")
    tl.say("tail.take() moves the tail's handle into old_tail. 40's count stays 2: 30's next "
           "and old_tail.")
    tl.wait(1.8)
    tl.set(code=1.0, prevs="30:10")
    tl.wait(0.6)
    tl.set(code=2.0, up="30")
    tl.say("prev.take() takes 40's weak link to 30. upgrade() turns it into a strong handle, "
           "so 30 has a count of 2 for now.")
    tl.wait(2.0)
    tl.set(code=3.0, nexts="10:30")
    tl.say("30's next is set to None. That drops the last link to 40 except old_tail.")
    tl.wait(1.6)
    tl.set(code=4.0, tail="30", up="")
    tl.wait(1.0)
    tl.set(code=6.0, out_v="40", out_u=0.0)
    tl.say("try_unwrap succeeds, because old_tail is 40's only strong handle. 40 goes to the "
           "caller.", "insight")
    tl.to(0.15, out_a=1.0)
    tl.to(0.9, in_out, out_u=1.0)
    tl.to(0.15, out_a=0.0)
    tl.set(vals="10,30", local="", got="40")
    tl.wait(1.4)

    tl.chapter("one node")
    tl.set(call="pop_back(), pop_back()")
    tl.say("Pop again, down to one node. Then pop the last node, 10.", "fail")
    tl.set(code=0.0, vals="10", nexts="", prevs="", head="10", tail="", local="10", got="40, 30")
    tl.wait(1.4)
    tl.set(code=2.0)
    tl.say("10 has no prev, so upgrade has nothing to upgrade: None. The other arm runs: head "
           "is cleared too.", "fail")
    tl.wait(1.8)
    tl.set(code=5.0, head="")
    tl.wait(1.0)
    tl.set(code=6.0, out_v="10", out_u=0.0)
    tl.to(0.15, out_a=1.0)
    tl.to(0.8, in_out, out_u=1.0)
    tl.to(0.15, out_a=0.0)
    tl.set(vals="", local="", got="40, 30, 10")
    tl.wait(1.0)

    tl.chapter("empty")
    tl.set(call="pop_back() on an empty list", code=0.0)
    tl.say("One more pop_back. tail is None, so map never calls the closure.", "fail")
    tl.wait(1.2)
    tl.set(code=7.0)
    tl.to(0.3, none=1.0)
    tl.say("It returns None. An empty list is a normal case here, not a panic.", "fail")
    tl.wait(2.0)

    def draw(p, s, total):
        t = s.t
        title_block(p, "pop_back: from the tail, through a weak link",
                    "upgrade() turns the weak prev link into a strong handle, if the node is alive.")
        if s.call:
            p.text(W - 26, 34, s.call, 13, BRASS, 700, "end", mono=True)
        vals = [v for v in s.vals.split(",") if v]
        pos = {v: (PX[k], PY) for k, v in enumerate(vals)}
        c = counts(s)
        for kv in s.nexts.split():
            a, b = kv.split(":")
            if a in pos and b in pos:
                link_arrow(p, pos[a][0] + 30, PY - 10, pos[b][0] - 30, PY - 10, TEAL, bend=-22)
        for kv in s.prevs.split():
            a, b = kv.split(":")
            if a in pos and b in pos:
                link_arrow(p, pos[a][0] - 30, PY + 10, pos[b][0] + 30, PY + 10, FAINT, 1.8,
                           bend=22, dash="5 4")
        for v, (x, y) in pos.items():
            hot = v in (s.local, s.up)
            box_node(p, x, y, v, BRASS if hot else INK, BRASS_LT if hot else PAPER, w=60, h=44,
                     size=17)
            p.circle(x + 28, y - 24, 11, TEAL if c.get(v) else FAINT, PAPER, 2.0)
            p.text(x + 28, y - 20, str(c.get(v, 0)), 11, PAPER, 700, "middle", mono=True)
        for name, key, dy, color in (("head", s.head, -50, TEAL), ("tail", s.tail, 52, RUST),
                                     ("old_tail", s.local, 52, BRASS),
                                     ("prev_node", s.up, -50, BRASS)):
            if key in pos:
                p.text(pos[key][0], PY + dy, name, 11.5, color, 700, "middle", mono=True)
        if not vals:
            p.text(PX[0], PY + 5, "head: None   tail: None", 12, FAINT, 700, mono=True)
        if s.out_a > 0.01:
            pill(p, lerp(PX[-1], 740, s.out_u), lerp(PY, 150, s.out_u), "value " + s.out_v,
                 BRASS, BRASS_LT, 11, opacity=s.out_a, shadow=None)
        robot(p, 744, 238, NIGHT, 1.0, 1.0, "caller", "got " + (s.got or "nothing"))
        if s.none > 0.01:
            chip(p, 640, 120, "pop_back() = None", RUST, RUST_LT, 12, opacity=s.none)
        POP_BACK.draw(p, 26, 290, W - 52, "pop_back", s, t, size=10.0, lead=13.0,
                      tint=RUST if s.kind == "fail" else TEAL)
        caption(p, tl, t, CAP)
        progress(p, tl, t, total, RAIL)

    CAP, RAIL, height = layout(290, len(POP_BACK), 13.0)
    return tl, draw, height


def build_list_build(only=None):
    tl, draw, height = list_build()
    return render("ch09-list-build.gif", tl, draw, height, only=only)


def build_list_layouts(only=None):
    tl, draw, height = list_layouts()
    return render("ch09-list-layouts.gif", tl, draw, height, only=only)


def build_list_remove(only=None):
    tl, draw, height = list_remove()
    return render("ch09-list-remove.gif", tl, draw, height, only=only)


def build_list_pop_back(only=None):
    tl, draw, height = list_pop_back()
    return render("ch09-list-pop-back.gif", tl, draw, height, only=only)


BUILDERS = {
    "list-build": build_list_build,
    "list-layouts": build_list_layouts,
    "list-remove": build_list_remove,
    "list-pop-back": build_list_pop_back,
}
