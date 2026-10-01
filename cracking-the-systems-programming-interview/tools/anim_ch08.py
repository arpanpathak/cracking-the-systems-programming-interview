"""The pointer chapter animations (ch08-pointers.md), drawn with `motion`.

    python3 tools/animations.py rc-refcell weak-parent
"""

from anim_kernel import lines_containing
from motion import *  # noqa: F401,F403
from motion import Timeline, render

RC_CODE = lines_containing("src/problems/smart_pointers.rs",
                           "let counter = Rc::new(RefCell::new(0));",
                           "let alias = Rc::clone(&counter);",
                           "*alias.borrow_mut() += 1;", "*counter.borrow_mut() += 10;",
                           "*counter.borrow()")
WEAK_CODE = lines_containing("src/problems/smart_pointers.rs", "let root = TreeNode::root(1);",
                             "let child = TreeNode::child_of(&root, 2);",
                             "assert_eq!(child.parent_value(), Some(1));", "drop(root);",
                             "assert_eq!(child.parent_value(), None);")

STACK_X = 60
HEAP = (470, 96, 250, 150)


def stack_var(p, y, name, alpha=1.0, color=TEAL):
    with p.group(opacity=alpha):
        p.rect(STACK_X, y - 16, 150, 32, PAPER, color, 6, 1.4)
        p.text(STACK_X + 12, y + 5, name, 12, INK, 700, mono=True)
        p.circle(STACK_X + 134, y, 4, color)


def arrow(p, a, b, color, dashed=False, alpha=1.0):
    p.line(a[0], a[1], b[0], b[1], color, 1.5, dash="5 4" if dashed else None, opacity=alpha)
    p.circle(b[0], b[1], 3.5, color, opacity=alpha)


# ---------------------------------------------------------- 8.4: Rc and RefCell


def rc_refcell():
    tl = Timeline(caption="", kind="step", code=-1.0, counter=0.0, alias=0.0, guard=0.0,
                  strong=0, value=0, flag="not borrowed", block=0.0, panic=0.0)

    tl.chapter("two handles")
    tl.say("Rc::new puts a RefCell holding 0 on the heap, with a strong count of 1.")
    tl.set(code=0.0)
    tl.to(0.6, block=1.0, counter=1.0)
    tl.set(strong=1)
    tl.wait(0.6)
    tl.say("Rc::clone copies the handle, not the value. The strong count becomes 2.")
    tl.set(code=1.0)
    tl.to(0.6, alias=1.0)
    tl.set(strong=2)
    tl.wait(0.8)

    tl.chapter("borrow")
    tl.say("borrow_mut through alias marks the cell mutably borrowed, and adds 1.")
    tl.set(code=2.0, flag="mutably borrowed")
    tl.wait(0.6)
    tl.set(value=1)
    tl.wait(0.6)
    tl.say("The guard is a temporary, dropped at the end of the statement. The borrow ends with it.")
    tl.set(flag="not borrowed")
    tl.wait(0.8)
    tl.say("Through counter, the same cell: borrow_mut, add 10, and the borrow ends again.")
    tl.set(code=3.0, flag="mutably borrowed")
    tl.wait(0.5)
    tl.set(value=11)
    tl.wait(0.5)
    tl.set(flag="not borrowed")
    tl.say("borrow reads 11 through a shared borrow. One value, two owners.")
    tl.set(code=4.0, flag="1 shared borrow")
    tl.wait(0.8)
    tl.set(flag="not borrowed")

    tl.chapter("drop")
    tl.say("The function returns. Dropping alias makes the count 1; dropping counter makes it 0.")
    tl.to(0.6, alias=0.0)
    tl.set(strong=1)
    tl.wait(0.4)
    tl.to(0.6, counter=0.0)
    tl.set(strong=0)
    tl.say("At 0 the value is freed. The last owner to leave frees it, whichever that is.",
           "insight")
    tl.to(0.8, block=0.0)
    tl.wait(0.8)

    tl.chapter("two guards")
    tl.say("Now keep the guard: let g = alias.borrow_mut(); and then call counter.borrow_mut().",
           "fail")
    tl.set(code=-1.0, value=0, strong=2, flag="not borrowed")
    tl.to(0.6, block=1.0, counter=1.0, alias=1.0)
    tl.set(code=2.0, flag="mutably borrowed")
    tl.to(0.5, guard=1.0)
    tl.wait(0.6)
    tl.say("g is still alive, so the cell is still mutably borrowed. The second borrow_mut panics.",
           "fail")
    tl.set(code=3.0)
    tl.to(0.4, back, panic=1.0)
    tl.say("The compiler cannot see this. RefCell moves the borrow check to run time, and a "
           "violation is a panic.", "fail")
    tl.wait(1.6)

    def draw(p, s, total):
        t = s.t
        title_block(p, "Rc<RefCell<i32>>: two owners, checked borrows",
                    "Rc counts the owners. RefCell checks each borrow while the program runs.")
        p.text(STACK_X, 84, "stack", 11, MUTED, 600)
        hx, hy, hw, hh = HEAP
        p.text(hx, 84, "heap", 11, MUTED, 600)
        rows = [("counter", 120, s.counter), ("alias", 176, s.alias), ("g: RefMut", 232, s.guard)]
        for name, y, alpha in rows:
            if alpha > 0.01:
                stack_var(p, y, name, alpha, BRASS if name.startswith("g") else TEAL)
                if not name.startswith("g") and s.block > 0.01:
                    arrow(p, (STACK_X + 138, y), (hx - 4, hy + 40 + (y - 120) / 4), TEAL,
                          alpha=min(alpha, s.block))
        if s.block > 0.01:
            with p.group(opacity=s.block):
                p.rect(hx, hy, hw, hh, PAPER, INK, 8, 1.6)
                p.text(hx + 14, hy + 28, "strong count", 11, MUTED, 600)
                p.text(hx + hw - 14, hy + 28, str(int(s.strong)), 16, INK, 700, "end", mono=True)
                p.line(hx + 10, hy + 42, hx + hw - 10, hy + 42, LINE, 1)
                p.text(hx + 14, hy + 66, "RefCell flag", 11, MUTED, 600)
                flag_color = BRASS if "mut" in s.flag else (TEAL if "shared" in s.flag else MUTED)
                chip(p, hx + hw - 80, hy + 62, s.flag, flag_color,
                     BRASS_LT if "mut" in s.flag else STAGE, 10)
                p.text(hx + 14, hy + 110, "value", 11, MUTED, 600)
                p.text(hx + hw - 14, hy + 114, str(int(s.value)), 22, INK, 700, "end", mono=True)
        if s.panic > 0.01:
            chip(p, hx + hw / 2, hy + hh + 26, "panic: already borrowed", RUST, RUST_LT, 11,
                 opacity=clamp(s.panic))

        code_panel(p, 26, 290, W - 52, "shared_counter_with_rc_refcell", RC_CODE, s.code,
                   size=11.0, lead=16.5, reveal=s.timeline.reached("code", t))
        caption(p, tl, t, 418)
        progress(p, tl, t, total, 504)

    return tl, draw, 538


# ---------------------------------------------------------- 8.5: Weak


NODES = {"root": (470, 130), "child": (470, 238)}


def weak_parent():
    tl = Timeline(caption="", kind="step", code=-1.0, mode="weak", root_var=0.0, child_var=0.0,
                  root_box=0.0, child_box=0.0, root_strong=0, root_weak=0, child_strong=0,
                  link=0.0, answer="", leaked=0.0, clock="")

    tl.chapter("weak link")
    tl.say("root is a node on the heap with a strong count of 1: the variable root.")
    tl.set(code=0.0)
    tl.to(0.6, root_var=1.0, root_box=1.0)
    tl.set(root_strong=1)
    tl.wait(0.4)
    tl.say("child_of makes a child whose parent link is Rc::downgrade(root): a Weak.")
    tl.set(code=1.0)
    tl.to(0.6, child_var=1.0, child_box=1.0, link=1.0)
    tl.set(child_strong=1, root_weak=1)
    tl.say("A weak link raises only the weak count. root's strong count is still 1.")
    tl.wait(0.8)
    tl.say("parent_value calls upgrade. The parent exists, so it returns Some(1).")
    tl.set(code=2.0, answer="Some(1)")
    tl.wait(1.0)

    tl.chapter("drop root")
    tl.say("drop(root) removes the only strong owner. The count reaches 0, and the node is freed.")
    tl.set(code=3.0, answer="")
    tl.to(0.6, root_var=0.0)
    tl.set(root_strong=0)
    tl.to(0.6, root_box=0.25)
    tl.say("upgrade now returns None. The child did not keep its parent alive.", "insight")
    tl.set(code=4.0, answer="None")
    tl.wait(1.2)

    tl.chapter("Rc both ways")
    tl.say("Now make both links strong: the parent holds the child, and the child holds the parent "
           "with an Rc.", "fail")
    tl.set(mode="cycle", code=-1.0, answer="", root_strong=2, child_strong=2, root_weak=0)
    tl.to(0.6, root_var=1.0, root_box=1.0, child_var=1.0, child_box=1.0, link=1.0)
    tl.wait(0.6)
    tl.say("Drop both variables. Each count falls to 1, held by the other node, and never reaches 0.",
           "fail")
    tl.to(0.6, root_var=0.0, child_var=0.0)
    tl.set(root_strong=1, child_strong=1)
    tl.to(0.4, leaked=1.0)
    for label in ("1 s", "1 min", "until the process exits"):
        tl.set(clock=label)
        tl.wait(0.9)
    tl.say("No variable can reach the pair any more, and neither is ever freed: a leak.", "fail")
    tl.wait(1.4)

    def node(p, name, alpha, strong, weak, value):
        x, y = NODES[name]
        with p.group(opacity=alpha):
            p.rect(x, y - 30, 250, 60, PAPER, RUST if s_mode[0] == "cycle" and alpha > 0.5 and
                   s_leaked[0] else INK, 8, 1.5)
            p.text(x + 14, y - 8, "%s  value %d" % (name, value), 12, INK, 700, mono=True)
            p.text(x + 14, y + 16, "strong %d   weak %d" % (strong, weak), 11, MUTED, 600,
                   mono=True)

    s_mode, s_leaked = [""], [0.0]

    def draw(p, s, total):
        t = s.t
        s_mode[0], s_leaked[0] = s.mode, s.leaked
        title_block(p, "Weak: a pointer that does not own",
                    "A child points back at its parent without keeping the parent alive.")
        p.text(STACK_X, 84, "stack", 11, MUTED, 600)
        p.text(470, 84, "heap", 11, MUTED, 600)
        for name, y in (("root", 130), ("child", 238)):
            alpha = getattr(s, name + "_var")
            if alpha > 0.01:
                stack_var(p, y, name, alpha)
                arrow(p, (STACK_X + 138, y), (NODES[name][0] - 4, NODES[name][1]), TEAL,
                      alpha=alpha)
        node(p, "root", s.root_box, int(s.root_strong), int(s.root_weak), 1)
        node(p, "child", s.child_box, int(s.child_strong), 0, 2)
        if s.link > 0.01:
            rx, ry = NODES["root"]
            cx, cy = NODES["child"]
            strong = s.mode == "cycle"
            arrow(p, (cx + 200, cy - 30), (rx + 200, ry + 30), RUST if strong else NIGHT,
                  dashed=not strong, alpha=s.link)
            p.text(rx + 214, (ry + cy) / 2 + 4, "Rc parent" if strong else "Weak parent", 10.5,
                   RUST if strong else NIGHT, 700, opacity=s.link)
            if strong:
                arrow(p, (rx + 60, ry + 30), (cx + 60, cy - 30), RUST, alpha=s.link)
                p.text(rx + 70, (ry + cy) / 2 + 4, "Rc child", 10.5, RUST, 700, opacity=s.link)
        if s.answer:
            chip(p, 340, 184, "parent_value() = " + s.answer, TEAL, TEAL_LT, 11)
        if s.leaked > 0.01:
            chip(p, 595, 296, "leaked" + (", " + s.clock if s.clock else ""), RUST, RUST_LT, 11,
                 opacity=clamp(s.leaked))

        code_panel(p, 26, 318, W - 52, "the test weak_parent_link_does_not_keep_the_parent_alive",
                   WEAK_CODE, s.code, size=11.0, lead=16.5, reveal=s.timeline.reached("code", t))
        caption(p, tl, t, 446)
        progress(p, tl, t, total, 532)

    return tl, draw, 566


def build_rc_refcell(only=None):
    tl, draw, height = rc_refcell()
    return render("ch08-rc-refcell.gif", tl, draw, height, only=only)


def build_weak_parent(only=None):
    tl, draw, height = weak_parent()
    return render("ch08-weak-parent.gif", tl, draw, height, only=only)


BUILDERS = {
    "rc-refcell": build_rc_refcell,
    "weak-parent": build_weak_parent,
}
