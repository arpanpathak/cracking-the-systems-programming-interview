#!/usr/bin/env python3
"""The animated figures, written to src/figures/*.gif.

Each animation is a list of steps. Every step becomes one frame: a picture with
one more move applied, a sentence naming the move, and a scoreboard of the values
the listing beside it uses. The frames are held for about two seconds each, so the
animation is read rather than watched, and the transition between two frames
moves the drawing while the words change in one clean step.

This module holds the five animations that belong to the opening chapters. The
rest live in `anim_problems`, `anim_structures`, and `anim_systems`.

    python3 tools/animations.py            # every animation
    python3 tools/animations.py window     # one of them
"""

import sys

import anim_problems
import anim_structures
import anim_systems
from animlib import *  # noqa: F401,F403
from animlib import Frame, frames, publish


# --------------------------------------------------------------- sliding window


def window():
    """The longest substring with no repeated character, over "pwwkew"."""
    text = "pwwkew"
    # start, end, best, the earlier index of the repeated character, the step line
    steps = [
        (0, 0, 1, None, "end reaches 0. The window is \"p\", and best becomes 1."),
        (0, 1, 2, None, "end reaches 1. The window is \"pw\", and best becomes 2."),
        (2, 2, 2, 1, "end reaches 2. This 'w' repeats the one at index 1, so start jumps past it."),
        (2, 3, 2, None, "end reaches 3. The window is \"wk\", and best stays 2."),
        (2, 4, 3, None, "end reaches 4. The window is \"wke\", and best becomes 3."),
        (3, 5, 3, 2, "end reaches 5. This 'w' repeats the one at index 2, so start moves to 3."),
        (3, 5, 3, None, "end has passed the last index. The longest window was \"wke\". The answer is 3."),
    ]
    insight = (2, "start jumps past the duplicate and never before it, so no index is visited twice.")

    cw, gap = 76, 10
    x0 = (W - (len(text) * cw + (len(text) - 1) * gap)) / 2.0

    def make(step, height=None, insight_rows=0):
        start, end, best, repeat_at, line = step
        first = step is steps[0]
        f = Frame(
            "Sliding window: the longest run with no repeated character",
            sub="The window grows at the right edge and shrinks at the left edge.",
            diagram=204,
            legend=[("in the window", GREEN, TEAL), ("the repeat", PINK, RUST),
                    ("outside", PALE, INK)],
            step=line,
            note="start only ever moves forward, so a character leaves the window once.",
            pairs=[("start", start, TEAL), ("end", end, RUST), ("best", best, INK)],
            insight=insight[1] if step is steps[insight[0]] else None,
            height=height, insight_rows=insight_rows,
        )
        t = f.top
        row_y, ch = t + 62, 62
        previous = (0, 0) if first else (steps[steps.index(step) - 1][0],
                                         steps[steps.index(step) - 1][1])

        # Both bands go down before the cells, so the tint sits behind the
        # characters and the cells keep the colour the legend promised.
        if (previous) != (start, end):
            f.zone(x0 + previous[0] * (cw + gap) - 10, row_y - 10,
                   (previous[1] - previous[0]) * (cw + gap) + cw + 20, ch + 20,
                   color=TEAL, dash=True, opacity=0.07)
        f.zone(x0 + start * (cw + gap) - 10, row_y - 10,
               (end - start) * (cw + gap) + cw + 20, ch + 20,
               color=TEAL, dash=False, opacity=0.10)

        cells = row(f, x0, row_y, cw, ch, list(text), gap=gap, size=T_CELL + 2,
                    fills=[PINK if (repeat_at is not None and i in (repeat_at, end))
                           else (GREEN if start <= i <= end else PALE) for i in range(len(text))],
                    strokes=[RUST if (repeat_at is not None and i in (repeat_at, end))
                             else (TEAL if start <= i <= end else BORDER)
                             for i in range(len(text))])
        index_labels(f, cells, row_y + ch + 18, color=MUTED)

        f.text(PAD + 2, row_y + ch / 2 + 6, "window", T_CHIP, TEAL, bold=True)
        pointer_down(f, x0 + end * (cw + gap) + cw / 2, row_y - 3, "end", RUST, gap=24)
        pointer_up(f, x0 + start * (cw + gap) + cw / 2, row_y + ch + 3, "start", TEAL, gap=28, leader=False)
        return f

    publish("ch03-window.gif", frames(make, steps),
            [2400] * len(steps))


# ----------------------------------------------------------------- binary search


def binary_search():
    """Half-open binary search for 23 in a sorted array of eight values."""
    nums = [2, 5, 8, 12, 16, 23, 38, 56]
    target = 23
    # lo, hi, the move this frame shows, and the step line
    steps = [
        (0, 8, "lo = 0, hi = 8, mid = 4. a[4] = 16, which is below 23, so 23 can only lie to the right. lo = 5.",
         "The left half, indexes 0 to 4, is now out of the search."),
        (5, 8, "lo = 5, hi = 8, mid = 6. a[6] = 38, which is above 23, so 23 can only lie to the left. hi = 6.",
         "The right half, indexes 6 and 7, is now out of the search."),
        (5, 6, "lo = 5, hi = 6, mid = 5. a[5] = 23. The value is found after three comparisons.",
         "One cell is left, and it holds the target."),
    ]
    insight = "Each comparison discards half of what is left, so a million values take twenty."

    cw, gap = 78, 10
    x0 = (W - (len(nums) * cw + (len(nums) - 1) * gap)) / 2.0

    def make(step, height=None, insight_rows=0):
        lo, hi, line, note = step
        mid = (lo + hi) // 2
        found = nums[mid] == target
        index = steps.index(step)
        f = Frame(
            "Binary search: each comparison halves the range",
            sub="The array is sorted. The range is half open: lo is included and hi is not.",
            diagram=206,
            legend=[("in range", GREEN, TEAL), ("ruled out", GREY, BORDER)],
            step=line,
            note=note,
            pairs=[("lo", lo, TEAL), ("hi", hi, TEAL), ("mid", mid, INK), ("a[mid]", nums[mid], RUST)],
            insight=insight if found else None,
            height=height, insight_rows=insight_rows,
        )
        t = f.top
        row_y, ch = t + 64, 56
        if found:
            f.glow(x0 + mid * (cw + gap) + cw / 2, row_y + ch / 2, 62, TEAL, 0.45)

        for i, value in enumerate(nums):
            if i == mid:
                fill, stroke, color = GREEN, TEAL, INK
            elif lo <= i < hi:
                fill, stroke, color = PALE, INK, INK
            else:
                fill, stroke, color = GREY, BORDER, MUTED
            f.cell(x0 + i * (cw + gap), row_y, cw, ch, value, fill, stroke, size=T_CELL,
                   color=color)
            f.text(x0 + i * (cw + gap) + cw / 2, row_y + ch + 22, str(i), T_CHIP, MUTED,
                   anchor="middle")

        # The range as a bracket, so its two ends can be named without two chips
        # landing on the same cell when one cell is all that is left.
        left = x0 + lo * (cw + gap)
        right = x0 + (hi - 1) * (cw + gap) + cw
        f.line(left, row_y + ch + 40, right, row_y + ch + 40, TEAL, 2.0)
        for x in (left, right):
            f.line(x, row_y + ch + 40, x, row_y + ch + 50, TEAL, 2.0)
        chip(f, left, row_y + ch + 76, "lo", TEAL)
        chip(f, right, row_y + ch + 76, "hi", TEAL)

        pointer_down(f, x0 + mid * (cw + gap) + cw / 2, row_y, "mid", INK, gap=34)
        if index:
            # Where the range was before this step cut it in half.
            prev_lo, prev_hi, _, _ = steps[index - 1]
            f.rect(x0 + prev_lo * (cw + gap) - 6, row_y - 6,
                   (prev_hi - prev_lo) * (cw + gap) - gap + 12, ch + 12,
                   "none", BORDER, 8, width=1.3, dash=True, opacity=0.85)
        return f

    publish("ch03-binary-search.gif", frames(make, steps), [2600] * len(steps))




# ------------------------------------------------------------- linked list reverse


def reverse():
    """Reverse a singly linked list with previous, current, and next."""
    vals = [1, 2, 3, 4]
    # how many nodes are reversed, previous index, current index, the step line
    steps = [
        (0, None, 0, "Start. previous is None and current is the head, node 1. Save next = 2 before the link is cut."),
        (1, 0, 1, "Point node 1 at previous, which is None. previous becomes 1, current becomes 2."),
        (2, 1, 2, "Point node 2 at node 1. The reversed part is 2 -> 1."),
        (3, 2, 3, "Point node 3 at node 2. The reversed part is 3 -> 2 -> 1."),
        (4, 3, None, "Point node 4 at node 3. current is None, so the loop stops. previous, node 4, is the new head."),
    ]
    insight = "next holds the rest of the list, so the link is safe to cut."

    cw, gap = 96, 52
    x0 = 176
    none_w = 76

    def make(step, height=None, insight_rows=0):
        reversed_count, prev_i, cur_i, line = step
        last = step is steps[-1]
        f = Frame(
            "Reversing a singly linked list with three bindings",
            sub="previous and current walk the list. next holds the rest so the link is safe to cut.",
            diagram=208,
            legend=[("points back", GREEN, TEAL), ("not yet reversed", PALE, INK)],
            step=line,
            note="Teal arrows point backwards, into the part already reversed.",
            pairs=[("previous", "None" if prev_i is None else vals[prev_i], TEAL),
                   ("current", "None" if cur_i is None else vals[cur_i], RUST),
                   ("reversed", reversed_count, INK)],
            insight=insight if last else None,
            height=height, insight_rows=insight_rows,
        )
        t = f.top
        row_y, ch = t + 76, 58

        # The two zones: what is reversed so far, and what is still to do.
        if reversed_count:
            f.zone(x0 - 16, row_y - 16, reversed_count * (cw + gap) - gap + 32, ch + 32,
                   color=TEAL, dash=True)
        if reversed_count < len(vals):
            rx = x0 + reversed_count * (cw + gap) - 16
            f.zone(rx, row_y - 16, (len(vals) - reversed_count) * (cw + gap) - gap + 32,
                   ch + 32, color=BORDER, fill=GREY, dash=True)

        none_x, none_w2 = x0 - none_w - 44, none_w
        f.cell(none_x, row_y + 10, none_w2, ch - 20, "None", WHITE, BORDER, size=T_CHIP,
               mono=True, dash=True, color=MUTED, pad=4)

        cells = row(f, x0, row_y, cw, ch, vals, gap=gap, size=T_CELL + 2,
                    fills=[GREEN if i < reversed_count else PALE for i in range(len(vals))],
                    strokes=[TEAL if i < reversed_count else INK for i in range(len(vals))])

        for i in range(len(vals) - 1):
            a, b = row_center(cells, i), row_center(cells, i + 1)
            if i < reversed_count:
                f.arrow(a[0] + cw / 2 + 6, a[1], b[0] - cw / 2 - 6, b[1], TEAL, 2.2)
            else:
                f.arrow(b[0] - cw / 2 - 6, b[1], a[0] + cw / 2 + 6, a[1], INK, 1.8)
        if reversed_count:
            f.arrow(none_x + none_w2 + 6, row_y + ch / 2, x0 - 6, row_y + ch / 2, TEAL, 2.2)
        if reversed_count < len(vals) - 1:
            # The link that had to be saved before it was cut.
            a, b = row_center(cells, reversed_count), row_center(cells, reversed_count + 1)
            f.text((a[0] + b[0]) / 2, row_y - 6, "next", T_CHIP, BRASS, mono=True,
                   anchor="middle", bold=True)

        if prev_i is not None:
            pointer_down(f, row_center(cells, prev_i)[0], row_y - 18, "previous", TEAL, gap=34)
        if cur_i is not None:
            pointer_up(f, row_center(cells, cur_i)[0], row_y + ch + 18, "current", RUST, gap=34)
        return f

    publish("ch04-reverse.gif", frames(make, steps), [2200] * len(steps))


# --------------------------------------------------------------------- LRU cache


def lru():
    """An LRU cache with room for two entries."""
    steps = [
        (["-", "-"], "put(a, 1)", None, "The cache is empty. Two slots are free, so a goes into the left one."),
        (["a", "b"], "put(b, 2)", None, "b goes into the free slot. Both slots are occupied, and a has gone unused longer."),
        (["b", "a"], "get(a)", None, "a is a hit, so it moves to the most recent end. b is now the least recent entry."),
        (["c", "a"], "put(c, 3)", "b", "The cache is full, so the least recent entry, b, is evicted and c takes its place."),
    ]
    insight = "A hit replaces a search, and an eviction is always the far end."

    def make(step, height=None, insight_rows=0):
        slots, op, evicted, line = step
        index = steps.index(step)
        f = Frame(
            "An LRU cache with room for two entries",
            sub="The left end is the least recently used. The right end is the most recently used.",
            diagram=192,
            legend=[("in the cache", GREEN, TEAL), ("free slot", GREY, BORDER)],
            step=line,
            note="A hit refreshes recency without touching the other entry.",
            pairs=[("op", op, RUST), ("evicted", evicted or "-", RUST if evicted else MUTED),
                   ("size", sum(1 for v in slots if v != "-"), INK)],
            insight=insight if index == len(steps) - 1 else None,
            height=height, insight_rows=insight_rows,
        )
        t = f.top
        sw, sh, sgap = 176, 78, 76
        sx = (W - (2 * sw + sgap)) / 2.0
        row_y = t + 42

        each = sw + sgap
        f.text(sx, row_y - 16, "least recent", T_CHIP, MUTED)
        f.text(sx + each + sw, row_y - 16, "most recent", T_CHIP, MUTED, anchor="end")
        f.line(sx + sw / 2, row_y - 40, sx + each + sw / 2, row_y - 40, BORDER, 1.4)

        for i, value in enumerate(slots):
            x = sx + i * each
            free = value == "-"
            if evicted and i == 0:
                f.glow(x + sw / 2, row_y + sh / 2, 88, RUST, 0.42)
            f.cell(x, row_y, sw, sh, "free" if free else value, GREY if free else GREEN,
                   BORDER if free else TEAL, size=T_CELL + 5, mono=False if free else True,
                   dash=free, color=MUTED if free else INK)

        # Where the evicted entry used to sit.
        if evicted:
            f.rect(sx - 5, row_y - 5, sw + 10, sh + 10, "none", RUST, 10, width=1.8,
                   dash=True, opacity=0.85)

        f.arrow(sx - 30, row_y + sh / 2, sx - 7, row_y + sh / 2, MUTED, 1.6, head=7)
        f.arrow(sx + each + sw + 7, row_y + sh / 2, sx + each + sw + 30,
                row_y + sh / 2, MUTED, 1.6, head=7)
        f.line(sx, row_y + sh + 26, sx + each + sw, row_y + sh + 26, BORDER, 1.4)
        f.text((sx + sx + each + sw) / 2, row_y + sh + 48,
               "recency grows this way", T_CHIP, MUTED, anchor="middle")
        return f

    publish("ch13-lru.gif", frames(make, steps), [2400] * len(steps))


# -------------------------------------------------------------- consistent hashing


def ring():
    """Adding a node to a consistent-hash ring."""
    before = [(20, "a"), (45, "b"), (70, "a"), (90, "b")]
    after = [(20, "a"), (45, "b"), (55, "c"), (70, "a"), (90, "b")]
    keys = [10, 30, 50, 60, 80]

    def owner(key, nodes):
        for pos, name in nodes:
            if pos >= key:
                return name
        return nodes[0][1]

    steps = [
        (before, None, "Four virtual nodes sit on the ring. Each key belongs to the first node clockwise from it."),
        (after, None, "Node c joins at position 55. Only the arc between b at 45 and c at 55 changes hands."),
        (after, 50, "Key 50 now meets c before b, so it moves from b to c. The other four keys stay where they were."),
        (after, 50, "One key in five moved. Adding node n+1 to a ring of n moves about one key in n+1."),
    ]
    insight = "Only the keys inside the new node's arc move, so one node costs a few misses."

    cx, cy, r = W / 2.0, 130.0, 104.0

    def make(step, height=None, insight_rows=0):
        nodes, moved, line = step
        index = steps.index(step)
        moved_key = moved
        f = Frame(
            "Consistent hashing: a new node takes only its own arc of keys",
            sub="Nodes and keys share one ring. A key belongs to the first node clockwise from it.",
            diagram=268,
            legend=[("a node", PALE, INK), ("the new node", CREAM, RUST)],
            step=line,
            note="Moving one key means one cache miss, not a rebuild of the whole table.",
            pairs=[("nodes", len(nodes), INK), ("moved", 1 if moved else 0, RUST),
                   ("keys", len(keys), TEAL)],
            insight=insight if index == len(steps) - 1 else None,
            height=height, insight_rows=insight_rows,
        )
        t = f.top
        cy = t + 130

        f.circle(cx, cy, r, "none", BORDER, 2.0)
        if moved is not None:
            # The arc whose ownership changed, drawn as the band it is.
            f.arc(cx, cy, r, 45 / 100.0 * 360, 55 / 100.0 * 360, TEAL, 9.0, opacity=0.55)
            f.arc(cx, cy, r, 45 / 100.0 * 360, 55 / 100.0 * 360, PINK, 5.0)

        for pos, name in nodes:
            x, y = polar(cx, cy, r, pos / 100.0 * 360)
            fresh = name == "c"
            f.circle(x, y, 18, CREAM if fresh else PALE, RUST if fresh else INK, 1.8)
            f.text(x, y + 5, name, T_ZONE, RUST if fresh else INK, anchor="middle", bold=True)

        for key in keys:
            x, y = polar(cx, cy, r - 34, key / 100.0 * 360)
            own = owner(key, nodes)
            here = moved is not None and key == moved
            f.circle(x, y, 8, RUST if here else WHITE, RUST if here else MUTED, 1.6)
            label = "%d" % key
            f.text(x, y - 20, label, T_CHIP, RUST if here else INK, mono=True,
                   anchor="middle", bold=here, halo=True)
            if here:
                f.text(x, y + 30, "now %s" % own, T_CHIP, RUST, mono=True, anchor="middle",
                       bold=True, halo=True)
        return f

    publish("ch14-ring.gif", frames(make, steps), [2600] * len(steps))


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


def main(argv):
    names = argv or list(BUILDERS)
    unknown = [n for n in names if n not in BUILDERS]
    if unknown:
        print("unknown animation(s): %s" % ", ".join(unknown), file=sys.stderr)
        print("available: %s" % ", ".join(BUILDERS), file=sys.stderr)
        return 2
    for name in names:
        BUILDERS[name]()
        print("  %s.gif" % name)
    print("wrote %d animations to %s" % (len(names), OUT.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
