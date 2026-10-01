#!/usr/bin/env python3
"""The animated figures, written to src/figures/*.gif.

Each animation is a list of steps. Every step becomes one frame: a picture with
one more move applied, a sentence naming the move, and a scoreboard of the values
the listing beside it uses. Frames are held for four seconds, so the animation is
read rather than watched, and a rail at the foot of each frame says how far in the
reader is.

An animation that has a case to reject ends on it, drawn in a rust band: an
unmatched closer, an amount no coin can make, a target that is absent, a graph
with a cycle. An algorithm that is only ever shown succeeding is an algorithm the
reader cannot debug.

This module holds the five animations that belong to the opening chapters. The
rest live in `anim_problems`, `anim_structures`, `anim_systems`, and the motion
modules `anim_sockets`, `anim_http`, and `anim_async`.

    python3 tools/animations.py            # every animation
    python3 tools/animations.py window     # one of them
"""

import sys

import anim_async
import anim_http
import anim_problems
import anim_sockets
import anim_structures
import anim_systems
from animlib import *  # noqa: F401,F403
from animlib import Frame, frames, publish


RAIL = 54.0          # where the values sit above the baseline in a rail picture
RULE = 116.0         # where a band that spans a run of stations sits


# --------------------------------------------------------------- sliding window


def window():
    """The longest substring with no repeated character, over "pwwkew".

    The last step runs a second input, "abba", because that is the one that
    catches the mistake this algorithm invites: taking the duplicate's last index
    plus one without holding start where it already was.
    """
    text = "pwwkew"
    # start, end, best, the earlier index of the repeated character, the step line
    steps = [
        (0, 0, 1, None, "end reaches 0. The window is \"p\", and best becomes 1."),
        (0, 1, 2, None, "end reaches 1. The window is \"pw\", and best becomes 2."),
        (2, 2, 2, 1, "end reaches 2. This 'w' repeats the one at index 1, so start jumps past it, to 2."),
        (2, 3, 2, None, "end reaches 3. The window is \"wk\", and best stays 2."),
        (2, 4, 3, None, "end reaches 4. The window is \"wke\", and best becomes 3."),
        (3, 5, 3, 2, "end reaches 5. This 'w' repeats the one at index 2, so start moves to 3."),
        (3, 5, 3, None, "end has passed the last index. The longest window was \"wke\", so the answer is 3."),
        ("abba", 3, 2, 2, 0,
         "Now the same code on \"abba\". At index 3 the 'a' repeats index 0, which is already behind the window."),
    ]
    insight_at, fail_at = 2, 7

    def make(step, height=None, rows=0, index=0):
        if step[0] == "abba":
            _, end, start, best, repeat_at, line = step
            seq, failing = "abba", True
        else:
            start, end, best, repeat_at, line = step
            seq, failing = text, False
        previous = (start, end) if index == 0 or failing else (
            steps[index - 1][0], steps[index - 1][1])
        f = Frame(
            "Sliding window: the longest run with no repeated character",
            sub="The window grows at the right edge and shrinks at the left edge.",
            diagram=176,
            legend=[("the window", TEAL), ("outside it", BORDER), ("a repeat", RUST)],
            step=line,
            note="start never moves backwards, so a character leaves the window once.",
            pairs=[("start", start, TEAL), ("end", end, RUST), ("best", best, INK)],
            insight=("start jumps past the duplicate and never before it, so no index is visited twice."
                     ) if index == insight_at else None,
            fails=("The duplicate at 0 is behind the window. last + 1 would set start to 1, drag the "
                   "window back over \"bb\", and report 3. The rule is max(start, last + 1)."
                   ) if failing else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        xs = rail_row(f, t + RAIL, list(seq), unit=50, gap=12, size=T_VALUE + 1,
                      colors=[RUST if (repeat_at is not None and i in (repeat_at, end))
                              else (INK if start <= i <= end else MUTED)
                              for i in range(len(seq))],
                      bolds=[start <= i <= end for i in range(len(seq))])

        # The window is one rule spanning a run, not a box per character, and its
        # two ends are start and end. The names sit outside the ends, so the rule
        # never has to be read against a caret somewhere else on the canvas.
        left, right = xs[start] - 18, xs[end] + 18
        f.line(left, t + RULE, right, t + RULE, TEAL, 4.0)
        for x in (left, right):
            f.line(x, t + RULE, x, t + RULE - 9, TEAL, 2.0)
        f.text(left - 10, t + RULE + 5, "start", T_MARK, TEAL, anchor="end", layer="text",
               bold=not failing and index > 0 and start != previous[0])
        f.text(right + 10, t + RULE + 5, "end", T_MARK, RUST, anchor="start", layer="text",
               bold=not failing and index > 0 and end != previous[1])

        if repeat_at is not None:
            dot(f, xs[repeat_at], t + RAIL + 14, RUST, 5.5)

        index_row(f, xs, t + RAIL + 44, halo=True)

        if failing:
            # The window the wrong rule would have produced: it reaches back over
            # the duplicate and measures a run that still contains a repeat.
            f.line(xs[1] - 18, t + 146, xs[3] + 18, t + 146, RUST, 2.0, dash=True)
            f.text(xs[2], t + 166, "last + 1 would give this window", T_MARK, RUST,
                   anchor="middle", layer="text")
        return f

    publish("ch03-window.gif", frames(make, steps),
            holds(len(steps), longer=(insight_at, fail_at)))


# ----------------------------------------------------------------- binary search


def binary_search():
    """Half-open binary search, first for a value that is there, then one that is not."""
    nums = [2, 5, 8, 12, 16, 23, 38, 56]
    # target, lo, hi, the step line
    steps = [
        (23, 0, 8, "lo = 0, hi = 8, mid = 4. a[4] = 16, below the target, so 23 can only lie to the right. lo = 5."),
        (23, 5, 8, "lo = 5, hi = 8, mid = 6. a[6] = 38, above the target, so 23 can only lie to the left. hi = 6."),
        (23, 5, 6, "lo = 5, hi = 6, mid = 5. a[5] = 23. Found after three comparisons."),
        (24, 0, 8, "The same search for 24. mid = 4, and a[4] = 16 is below it, so lo = 5."),
        (24, 5, 8, "mid = 6, and a[6] = 38 is above it, so hi = 6."),
        (24, 5, 6, "mid = 5, and a[5] = 23 is below it, so lo = 6."),
        (24, 6, 6, "lo and hi have met, so the range is empty. 24 is not in the array and the loop returns -1."),
    ]
    insight_at, fail_at = 2, 6

    def make(step, height=None, rows=0, index=0):
        target, lo, hi, line = step
        searching = target == 24
        mid = (lo + hi) // 2
        empty = lo >= hi
        found = not searching and index == insight_at
        f = Frame(
            "Binary search: each comparison halves the range",
            sub="The array is sorted. The range is half open: lo is included and hi is not.",
            diagram=160,
            legend=[("in range", TEAL), ("ruled out", BORDER)],
            step=line,
            note="Each comparison throws away half of what is left, so eight values take three comparisons.",
            pairs=[("target", target, RUST), ("lo", lo, TEAL), ("hi", hi, TEAL),
                   ("mid", "-" if empty else mid, INK)],
            insight=("Half the range goes at every comparison, so a million values take twenty, not a million."
                     ) if found else None,
            fails=("lo and hi meet without finding the target. The loop condition is lo < hi, so it "
                   "stops on the empty range and reports -1 rather than looping.") if empty else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        xs = rail_row(f, t + RAIL, nums, unit=76, gap=12, size=T_VALUE,
                      colors=[TEAL if (found and i == mid) else
                              (INK if lo <= i < hi else MUTED) for i in range(len(nums))],
                      bolds=[found and i == mid for i in range(len(nums))])

        if not empty:
            left, right = xs[lo] - 22, xs[hi - 1] + 22
            f.line(left, t + RULE, right, t + RULE, TEAL, 4.0)
            for x in (left, right):
                f.line(x, t + RULE, x, t + RULE - 9, TEAL, 2.0)
            f.text(left - 10, t + RULE + 5, "lo", T_MARK, TEAL, anchor="end", layer="text")
            f.text(right + 10, t + RULE + 5, "hi", T_MARK, TEAL, anchor="start", layer="text")
            pointer(f, xs[mid], t + RAIL - 16, "mid", INK, above=True)
        else:
            # An empty range has no width, so it is drawn as the two ends meeting.
            f.line(xs[lo] - 18, t + RULE, xs[lo] + 18, t + RULE, RUST, 3.0)
            f.line(xs[lo], t + RULE - 9, xs[lo], t + RULE + 9, RUST, 2.0)
            f.text(xs[lo], t + RULE + 26, "lo and hi meet", T_MARK, RUST, anchor="middle",
                   bold=True, layer="text")
        if found:
            f.glow(xs[mid], t + RAIL - 4, 48, TEAL, 0.45)

        index_row(f, xs, t + RAIL + 44, halo=True)
        return f

    publish("ch03-binary-search.gif", frames(make, steps),
            holds(len(steps), longer=(insight_at, fail_at)))


# ------------------------------------------------------------- linked list reverse


def reverse():
    """Reverse a singly linked list, then show the two lists that need no work."""
    vals = [1, 2, 3, 4]
    # what the list is, how many nodes are reversed, previous index, current index, the step line
    steps = [
        ("walk", 0, None, 0, "Start. previous is None and current is the head, node 1. Save next = 2 before the link is cut."),
        ("walk", 1, 0, 1, "Point node 1 at previous, which is None. previous becomes 1 and current becomes 2."),
        ("walk", 2, 1, 2, "Point node 2 at node 1. The reversed part is 2 -> 1."),
        ("walk", 3, 2, 3, "Point node 3 at node 2. The reversed part is 3 -> 2 -> 1."),
        ("walk", 4, 3, None, "current is None, so the loop stops. previous, node 4, is the new head."),
        ("empty", 0, None, None,
         "An empty list: the loop body never runs and the function returns None."),
        ("single", 0, None, 0,
         "One node: current becomes None after a single step, and the node still points at None."),
    ]
    insight_at, fail_at = 4, 6

    def make(step, height=None, rows=0, index=0):
        kind, reversed_count, prev_i, cur_i, line = step
        special = kind in ("empty", "single")
        nodes = [] if kind == "empty" else ([1] if kind == "single" else vals)
        last = index == insight_at
        f = Frame(
            "Reversing a singly linked list with three bindings",
            sub="previous and current walk the list. next holds the rest so the link is safe to cut.",
            diagram=150,
            legend=[("points back", TEAL), ("not yet reversed", BORDER)],
            step=line,
            note="Teal arrows point backwards, into the part already reversed.",
            pairs=[("previous", "-" if special or prev_i is None else nodes[prev_i], TEAL),
                   ("current", "-" if special or cur_i is None else nodes[cur_i], RUST),
                   ("reversed", 0 if special else reversed_count, INK)],
            insight=("next holds the rest of the list before the link is cut, so three bindings are "
                     "enough and no node is lost.") if last else None,
            fails=("The loop is written for a list that has a node to move. An empty list returns None "
                   "and a one-node list returns itself, because current is already None."
                   ) if special and kind == "single" else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        y = t + 58
        pitch = 118.0
        xs = [200.0 + i * pitch for i in range(len(nodes))]
        if not nodes:
            f.text(W / 2, y + 6, "None", T_VALUE, MUTED, mono=True, anchor="middle")
            f.text(W / 2, y + 52, "nothing to reverse", T_MARK, MUTED, anchor="middle",
                   layer="text")
        else:
            f.text(xs[0] - 52, y + 6, "None", T_MARK, MUTED, mono=True, anchor="end")
            for i, value in enumerate(nodes):
                f.circle(xs[i], y, 21, GREEN if i < reversed_count else WHITE,
                         TEAL if i < reversed_count else BORDER, 1.8)
                f.text(xs[i], y + 7, value, T_VALUE - 1, INK, mono=True, anchor="middle")
            if reversed_count:
                f.arrow(xs[0] - 40, y, xs[0] - 23, y, TEAL, 2.0, head=8)
            for i in range(len(nodes) - 1):
                if i < reversed_count:
                    # A reversed link runs right to left, so its head points back.
                    f.arrow(xs[i + 1] - 27, y, xs[i] + 27, y, TEAL, 2.2, head=8)
                else:
                    f.arrow(xs[i] + 27, y, xs[i + 1] - 27, y, BORDER, 1.8, head=8)
            for i, value in enumerate(nodes):
                if i < reversed_count:
                    f.line(xs[i], y + 30, xs[i], y + 38, TEAL, 2.0)
            if reversed_count:
                f.line(xs[0] - 30, y + 40, xs[reversed_count - 1] + 30, y + 40, TEAL, 3.5)
                f.text(xs[0] - 40, y + 45, "reversed", T_MARK, TEAL, anchor="end",
                       bold=True, layer="text")
            if reversed_count < len(nodes):
                f.line(xs[reversed_count] - 30, y + 40, xs[-1] + 30, y + 40, BORDER, 2.0)
                f.text(xs[-1] + 40, y + 45, "to do", T_MARK, MUTED, anchor="start",
                       layer="text")
            if prev_i is not None and prev_i < len(nodes):
                pointer(f, xs[prev_i], y - 30, "previous", TEAL, above=True)
            if cur_i is not None and cur_i < len(nodes):
                pointer(f, xs[cur_i], y + 56, "current", RUST, above=False)
        return f

    publish("ch04-reverse.gif", frames(make, steps),
            holds(len(steps), longer=(insight_at, fail_at)))


# --------------------------------------------------------------------- LRU cache


def lru():
    """An LRU cache with room for two entries."""
    steps = [
        (["-", "-"], "put(a, 1)", None, "The cache is empty. Both slots are free, so a goes into the left one."),
        (["a", "b"], "put(b, 2)", None, "b goes into the free slot. Both slots are full, and a has gone unused longer."),
        (["b", "a"], "get(a)", None, "a is a hit, so it moves to the most recent end. b is now the least recent."),
        (["c", "a"], "put(c, 3)", "b", "put into a full cache evicts the least recent entry, b, and c takes its place."),
        (["c", "a"], "get(z)", None, "get(z) is a miss. A miss on its own changes nothing: it evicts nothing and moves nothing."),
    ]
    insight_at, fail_at = 3, 4

    def make(step, height=None, rows=0, index=0):
        slots, op, evicted, line = step
        missing = op == "get(z)"
        f = Frame(
            "An LRU cache with room for two entries",
            sub="The left end is the least recently used. The right end is the most recently used.",
            diagram=150,
            legend=[("in the cache", TEAL), ("free slot", BORDER)],
            step=line,
            note="A hit refreshes recency without touching the other entry.",
            pairs=[("op", op, RUST), ("evicted", evicted or "-", RUST if evicted else MUTED),
                   ("size", sum(1 for v in slots if v != "-"), INK)],
            insight=("A hit replaces a search, and an eviction is always the far end, so both cost the "
                     "same whether the cache holds two entries or two million.") if index == insight_at else None,
            fails=("A miss evicts nothing. Only a put that has no free slot takes an entry out, which "
                   "is why the two operations have to be counted separately.") if missing else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        y = t + 56
        unit, gap = 190, 70
        left = (W - (2 * unit + gap)) / 2.0
        xs = [left + unit / 2.0 + i * (unit + gap) for i in range(2)]
        f.line(left, y + 44, left + 2 * unit + gap, y + 44, BORDER, 1.4)
        f.text(left, y - 46, "least recent", T_MARK, MUTED, layer="text")
        f.text(left + 2 * unit + gap, y - 46, "most recent", T_MARK, MUTED, anchor="end",
               layer="text")
        for i, value in enumerate(slots):
            free = value == "-"
            if evicted and i == 0:
                f.glow(xs[i], y, 78, RUST, 0.4)
            f.circle(xs[i], y, 40, WHITE if free else GREEN, BORDER if free else TEAL, 1.8,
                     dash=free)
            f.text(xs[i], y + 9 if free else y + 11, "free" if free else value,
                   T_VALUE + 3 if not free else T_MARK, MUTED if free else INK,
                   mono=not free, anchor="middle")
        if evicted:
            f.circle(xs[0], y, 48, "none", RUST, 1.8, dash=True)

        # The recency order is one arrow, not a row of labels repeated per frame.
        f.arrow(left - 40, y, left - 12, y, MUTED, 1.6, head=7)
        f.arrow(left + 2 * unit + gap + 12, y, left + 2 * unit + gap + 40, y, MUTED, 1.6, head=7)
        f.text((left + left + 2 * unit + gap) / 2.0, y + 68, "recency grows this way",
               T_MARK, MUTED, anchor="middle", layer="text")
        if missing:
            cross(f, xs[0] + unit / 2.0 + gap / 2.0, y, RUST, 9.0, 2.6)
            f.text(xs[0] + unit / 2.0 + gap / 2.0, y + 30, "no such key", T_MARK, RUST,
                   anchor="middle", bold=True, layer="text")
        return f

    publish("ch13-lru.gif", frames(make, steps),
            holds(len(steps), longer=(insight_at, fail_at)))


# -------------------------------------------------------------- consistent hashing


def ring():
    """Adding a node to a consistent-hash ring, and the key that wraps."""
    nodes = [(20, "a"), (45, "b"), (55, "c"), (70, "a"), (90, "b")]
    keys = [10, 30, 50, 60, 80]

    def owner(key, table):
        for pos, name in table:
            if pos >= key:
                return name
        return table[0][1]

    steps = [
        (nodes, None, "Five virtual nodes sit on the ring. Each key belongs to the first node clockwise from it."),
        (nodes, 50, "Key 50 meets c before b, so it moves from b to c. The other four keys stay where they were."),
        (nodes, 50, "One key in five moved. Adding a node to a ring of n moves about one key in n+1."),
        (nodes, 95, "Key 95 sits past the last node. It wraps to the first node clockwise, which is a at 20."),
    ]
    insight_at, fail_at = 1, 3

    def make(step, height=None, rows=0, index=0):
        table, moved, line = step
        wrapping = moved == 95
        cx, cy, r = W / 2.0, 130.0, 104.0
        f = Frame(
            "Consistent hashing: a new node takes only its own arc of keys",
            sub="Nodes and keys share one ring. A key belongs to the first node clockwise from it.",
            diagram=272,
            legend=[("a node", INK), ("its arc", TEAL), ("the key that moved", RUST)],
            step=line,
            note="Moving one key means one cache miss, not a rebuild of the whole table.",
            pairs=[("nodes", len(table), INK), ("keys", len(keys), TEAL),
                   ("moved", 1 if index else 0, RUST)],
            insight=("Only the keys inside the new node's arc change hands, so a new node costs a few "
                     "cache misses.") if index == insight_at else None,
            fails=("The ring has no beginning, so a key past the last node wraps to the first one "
                   "clockwise. A table that ignored the wrap would return nothing at all."
                   ) if wrapping else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        cy = t + 128
        f.circle(cx, cy, r, "none", BORDER, 1.6)
        if index:
            f.arc(cx, cy, r, 45 / 100.0 * 360, 55 / 100.0 * 360, TEAL, 9.0, opacity=0.5)
        for pos, name in table:
            x, y = polar(cx, cy, r, pos / 100.0 * 360)
            fresh = name == "c"
            f.circle(x, y, 17, WHITE, RUST if fresh else INK, 1.8)
            f.text(x, y + 6, name, T_CELL - 2.0, RUST if fresh else INK, anchor="middle",
                   bold=True)
        for key in keys:
            here = key == moved
            ang = key / 100.0 * 360
            x, y = polar(cx, cy, r - 40, ang)
            f.circle(x, y, 4.5, RUST if here else MUTED, "none")
            lx, ly = polar(cx, cy, r - 72, ang)
            f.text(lx, ly + 5, str(key), T_MARK, RUST if here else MUTED, mono=True,
                   anchor="middle", bold=here)
        if wrapping:
            # The wrap itself, drawn as the arc the key travels.
            f.arc(cx, cy, r + 20, 95 / 100.0 * 360, 20 / 100.0 * 360, RUST, 2.4, dash=True)
            f.text(cx, cy + r + 44, "95 wraps to a", T_MARK, RUST, anchor="middle",
                   bold=True, layer="text")
        elif index:
            f.text(cx, cy + r + 44, "50 now belongs to c", T_MARK, TEAL, anchor="middle",
                   bold=True, layer="text")
        return f

    publish("ch14-ring.gif", frames(make, steps),
            holds(len(steps), longer=(insight_at, fail_at)))


BUILDERS = {
    "window": window,
    "binary-search": binary_search,
    "reverse": reverse,
    "lru": lru,
    "ring": ring,
}
BUILDERS.update(anim_problems.BUILDERS)
BUILDERS.update(anim_structures.BUILDERS)
BUILDERS.update(anim_systems.BUILDERS)

# Animations drawn frame by frame with `motion`. They are kept apart from
# BUILDERS because `lint_animations.py` checks slide frames, and these have none.
MOTION = dict(anim_async.BUILDERS)
MOTION.update(anim_sockets.BUILDERS)
MOTION.update(anim_http.BUILDERS)


def main(argv):
    everything = dict(BUILDERS, **MOTION)
    names = argv or list(everything)
    unknown = [n for n in names if n not in everything]
    if unknown:
        print("unknown animation(s): %s" % ", ".join(unknown), file=sys.stderr)
        print("available: %s" % ", ".join(everything), file=sys.stderr)
        return 2
    for name in names:
        everything[name]()
        print("  %s.gif" % name)
    print("wrote %d animations to %s" % (len(names), OUT.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
