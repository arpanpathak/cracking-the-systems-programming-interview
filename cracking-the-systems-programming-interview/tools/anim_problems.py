"""Animations for the problem chapters, chapters 3 to 6.

Each builder writes one looping GIF to `src/figures`. A frame shows one step of
the algorithm the chapter quotes, with the same variable names, so a reader can
check a frame against the listing beside it.

A sequence of values is drawn as a rail: the values above a baseline, the indexes
below it, and state carried by a colour on the value and by a rule spanning a run.
A cell is used only where the thing really is a cell, such as a grid square, a
buffer slot, or a heap node.

Every animation ends on a frame that shows the case the algorithm has to reject,
in a rust band: a duplicate that drags the window backwards, a target that is
absent, an amount no coin can make, a closer that matches the wrong opener.
"""

from animlib import *  # noqa: F401,F403
from animlib import Frame, frames, publish

RAIL = 54.0
RULE = 116.0


def _heap_positions(count, base_x, top, dy, spacing):
    """Centres for a complete binary tree of `count` nodes, by array index."""
    out = {}
    for i in range(count):
        level = (i + 1).bit_length() - 1
        first = (1 << level) - 1
        width = spacing / (1 << (level - 1)) if level else 0
        offset = (i - first - ((1 << level) - 1) / 2.0) * width
        out[i] = (base_x + offset, top + level * dy)
    return out


def heap_tree(f, values, base_x, top, dy=62, spacing=210, r=21.0, fills=None, strokes=None,
              colors=None):
    """A complete binary tree over the array `values`, drawn as small circles."""
    pos = _heap_positions(len(values), base_x, top, dy, spacing)
    for i in range(1, len(values)):
        parent = (i - 1) // 2
        f.line(pos[parent][0], pos[parent][1] + r, pos[i][0], pos[i][1] - r, BORDER, 1.4)
    for i, value in enumerate(values):
        x, y = pos[i]
        f.circle(x, y, r, fills[i] if fills else WHITE, strokes[i] if strokes else BORDER, 1.6)
        f.text(x, y + 6, value, T_CELL - 1, colors[i] if colors else INK, mono=True,
               anchor="middle")
    return pos


# --------------------------------------------------------------- Two Sum (3.5)

def two_sum():
    """One pass over the array, with a map of the values already seen."""
    nums = [2, 7, 11, 15]
    target = 9
    steps = [
        (nums, target, 0, {}, "miss",
         "i = 0 holds 2. The partner it needs is 7, and the map is empty, so 2 is stored instead."),
        (nums, target, 1, {2: 0}, "hit",
         "i = 1 holds 7. The partner it needs is 2, and the map holds 2 at index 0. The pair is (0, 1)."),
        (nums, target, 1, {2: 0}, "done",
         "The scan stops after two of the four numbers, because the pair is complete."),
        ([1, 2, 3], 7, 2, {1: 0, 2: 1}, "none",
         "Now target 7 over 1, 2, 3. Every partner is missing from the map."),
    ]
    insight_at, fail_at = 1, 3

    def make(step, height=None, rows=0, index=0):
        seq, want, i, seen, kind, line = step
        missing = kind == "none"
        pair = {0, 1} if kind == "done" else set()
        f = Frame(
            "Two Sum: remember each number so a later one can find its partner",
            sub="One pass. For each x, ask the map for target - x.",
            diagram=150,
            legend=[("the pair", TEAL), ("the current number", RUST)],
            step=line,
            note="The map turns a second scan into a single lookup.",
            pairs=[("target", want, RUST), ("x", seq[i], INK), ("need", want - seq[i], TEAL),
                   ("found", "yes" if kind in ("hit", "done") else "no", INK)],
            insight=("The map holds the partner of every number already passed, so one pass is "
                     "enough.") if index == insight_at else None,
            fails=("The pass ends with the map full and no pair in it. A missing pair is the "
                   "ordinary case, not an error, so the function returns nothing.") if missing else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        xs = rail_row(f, t + RAIL, seq, unit=86, gap=14, size=T_VALUE + 1,
                      colors=[TEAL if k in pair else (RUST if k == i else MUTED)
                              for k in range(len(seq))],
                      bolds=[k == i or k in pair for k in range(len(seq))])
        index_row(f, xs, t + RAIL + 44, halo=True)
        pointer(f, xs[i], t + RAIL - 16, "i", RUST, above=True)

        # The map is drawn as the pairs it holds, not as an empty panel.
        f.text(PAD, t + RULE + 24, "the map", T_MARK, MUTED, layer="text")
        x = PAD + 78
        if not seen:
            f.text(x, t + RULE + 24, "empty", T_MARK, MUTED, mono=True, layer="text")
        for value, at in sorted(seen.items()):
            label = "%d -> %d" % (value, at)
            w = text_width(label, T_MARK + 1, True) + 20
            f.rect(x, t + RULE + 10, w, 20, PALE, BORDER, 4)
            f.text(x + w / 2, t + RULE + 24, label, T_MARK + 1, INK, mono=True,
                   anchor="middle")
            x += w + 10
        f.text(W - PAD, t + RULE + 24, "look up %d" % (want - seq[i]), T_MARK,
               TEAL if kind == "hit" else MUTED, mono=True, anchor="end", layer="text")
        if kind == "hit":
            f.glow(xs[i], t + RAIL - 14, 40, TEAL, 0.3)
        return f

    publish("ch03-two-sum.gif", frames(make, steps),
            holds(len(steps), longer=(insight_at, fail_at)))


# ---------------------------------------------------------- Brackets (3.6.1)

def brackets():
    """A stack of openers, popped by every closer."""
    steps = [
        ("([{}])", -1, "", None,
         "Start before the first character. The stack is empty."),
        ("([{}])", 0, "(", None,
         "An opener, so it goes on the stack. The stack records what still waits for a partner."),
        ("([{}])", 1, "([", None, "Another opener, pushed on top of the first."),
        ("([{}])", 2, "([{", None, "A third opener, pushed. From the bottom up, the stack is ( [ { ."),
        ("([{}])", 3, "([", "match",
         "A closer. Pop the top, which is '{', and compare. It matches, so the pair is closed."),
        ("([{}])", 4, "(", "match", "A closer. Pop '[' and compare. It matches."),
        ("([{}])", 5, "", "match",
         "A closer. Pop '(' and compare. It matches, and the stack is empty again."),
        ("([{}])", 6, "", None,
         "No characters are left and the stack is empty, so every opener found its closer."),
        ("([)]", 3, "([", "wrong",
         "Now the input \"([)]\". The closer ')' pops '[' and they do not match."),
    ]
    insight_at, fail_at = 5, 8

    def make(step, height=None, rows=0, index=0):
        text, i, stack, kind, line = step
        failing = kind == "wrong"
        f = Frame(
            "Valid brackets: a closer must match the most recent unmatched opener",
            sub="Counting openers is not enough. The order decides the answer.",
            diagram=190,
            legend=[("on the stack", TEAL), ("the character now", RUST)],
            step=line,
            note="The stack is the reason a single counter cannot answer this.",
            pairs=[("i", i, RUST), ("char", text[i] if 0 <= i < len(text) else "-", INK),
                   ("stack", len(stack), TEAL)],
            insight=("A closer must match the most recent opener, which is what a stack hands "
                     "back.") if index == insight_at else None,
            fails=("The counts are even and the string is still invalid: ')' arrives while '[' is "
                   "on top. The stack catches this, and counting openers cannot.") if failing else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        xs = rail_row(f, t + RAIL, list(text), unit=46, gap=10, size=T_VALUE + 1,
                      colors=[RUST if k == i else (TEAL if k <= i else MUTED)
                              for k in range(len(text))],
                      bolds=[k == i for k in range(len(text))])
        if 0 <= i < len(text):
            pointer(f, xs[i], t + RAIL - 16, "i", RUST, above=True)
        index_row(f, xs, t + RAIL + 44, halo=True)

        # The stack is a row of circles that grows to the right.
        f.text(PAD, t + RULE + 6, "stack", T_MARK, MUTED, layer="text")
        sx = PAD + 68
        if stack:
            for k, ch in enumerate(stack):
                top = k == len(stack) - 1
                x = sx + 34 + k * 56
                f.circle(x, t + RULE, 22, GREEN if top else WHITE,
                         RUST if (top and failing) else (TEAL if top else BORDER), 1.8)
                f.text(x, t + RULE + 7, ch, T_VALUE - 1, INK, mono=True, anchor="middle")
            f.text(sx + 34 + (len(stack) - 1) * 56, t + RULE + 44, "top", T_MARK,
                   RUST if failing else TEAL, anchor="middle", bold=True, layer="text")
        else:
            f.text(sx, t + RULE + 7, "empty", T_MARK, MUTED, mono=True, layer="text")
        if failing:
            mark = sx + 34 + len(stack) * 56
            cross(f, mark, t + RULE, RUST, 12.0, 2.6)
            f.text(mark + 26, t + RULE + 6, "wrong opener on top", T_MARK, RUST,
                   anchor="start", bold=True, layer="text")
        return f

    publish("ch03-brackets.gif", frames(make, steps),
            holds(len(steps), longer=(insight_at, fail_at)))


# --------------------------------------------------------- Three Sum (3.7.2)

def _three_sum_trace(nums):
    trace = []
    n = len(nums)
    for i in range(n - 2):
        if i > 0 and nums[i] == nums[i - 1]:
            trace.append((i, i + 1, n - 1, None,
                          "nums[%d] repeats the value before it, so every triple that starts here "
                          "has already been found." % i))
            continue
        lo, hi = i + 1, n - 1
        while lo < hi:
            total = nums[i] + nums[lo] + nums[hi]
            if total == 0:
                found = (nums[i], nums[lo], nums[hi])
                trace.append((i, lo, hi, found,
                              "The sum is 0, so (%d, %d, %d) is a triple. Move both pointers inward." % found))
                lo += 1
                hi -= 1
            elif total < 0:
                trace.append((i, lo, hi, None,
                              "The sum is %d, below 0, so the left value must grow and lo moves right." % total))
                lo += 1
            else:
                trace.append((i, lo, hi, None,
                              "The sum is %d, above 0, so the right value must shrink and hi moves left." % total))
                hi -= 1
    return trace


def three_sum():
    """Fix one value, then close two pointers over the rest of the sorted array."""
    nums = [-4, -1, -1, 0, 1, 2]
    trace = _three_sum_trace(nums)
    so_far, running = [], []
    for record in trace:
        if record[3]:
            running = running + [record[3]]
        so_far.append(running)
    # The case with no answer at all, run over an array that has no triple.
    empty_nums = [1, 2, 3, 4]
    empty_trace = _three_sum_trace(empty_nums)
    steps = ([(nums, record, k) for k, record in enumerate(trace)]
             + [(empty_nums, empty_trace[-1], len(trace) - 1)])
    insight_at, fail_at = 3, len(steps) - 1

    def make(step, height=None, rows=0, index=0):
        seq, record, at_step = step
        i, lo, hi, triple, line = record
        failing = index == fail_at
        found = so_far[min(at_step, len(so_far) - 1)] if not failing else []
        f = Frame(
            "Three Sum: fix one number, then close two pointers over the rest",
            sub="Sorted input turns a pointer move into a decision instead of a guess.",
            diagram=170,
            legend=[("found", TEAL), ("the pointers", BRASS), ("ruled out", BORDER)],
            step=line,
            note="Every move drops one index, so the pair of pointers costs one scan, not two.",
            pairs=[("i", i, TEAL), ("lo", lo, BRASS), ("hi", hi, RUST),
                   ("sum", seq[i] + seq[lo] + seq[hi] if lo < len(seq) and hi >= 0 else "-", INK)],
            insight=("A sum below zero can only be fixed by a larger left value, and the array is "
                     "sorted, so lo moves right.") if index == insight_at else None,
            fails=("The pointers have met at every i and no triple sums to zero. The answer is the "
                   "empty list, which is a real answer and not a failure of the search."
                   ) if failing else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        xs = rail_row(f, t + RAIL, seq, unit=84, gap=10, size=T_VALUE,
                      colors=[TEAL if triple and k in (i, lo, hi) else
                              (INK if k == i else (BRASS if k in (lo, hi) else MUTED))
                              for k in range(len(seq))],
                      bolds=[k in (i, lo, hi) for k in range(len(seq))])
        if lo <= hi:
            f.line(xs[lo] - 16, t + RULE, xs[hi] + 16, t + RULE, BRASS, 3.0)
        pointer(f, xs[i], t + RAIL - 16, "i", TEAL, above=True)
        pointer(f, xs[min(lo, len(seq) - 1)], t + RULE + 34, "lo", BRASS, above=False)
        pointer(f, xs[max(hi, 0)], t + RULE + 34, "hi", RUST, above=False)
        index_row(f, xs, t + RAIL + 44, halo=True)
        f.text(PAD, t + RULE + 4, "triples:  %s"
               % ("  ".join("(%d,%d,%d)" % tr for tr in found) or "none"),
               T_MARK, TEAL if found else MUTED, mono=True, layer="text")
        if failing:
            f.text(W - PAD, t + RULE + 4, "no triple sums to zero", T_MARK, RUST,
                   anchor="end", layer="text")
        return f

    publish("ch03-three-sum.gif", frames(make, steps),
            holds(len(steps), longer=(insight_at, fail_at)))


# ---------------------------------------------------- Merge intervals (3.9)

def merge_intervals():
    """Sort by start, then extend the current range or keep it."""
    raw = [(15, 18), (2, 6), (1, 3), (8, 10)]
    ordered = sorted(raw)
    steps = [
        (raw, [], None, "The input arrives unsorted, so no range can be trusted to arrive next."),
        (ordered, [], None, "Sort by start. Now any range that overlaps the last one always arrives next."),
        (ordered, [], (1, 3), "Start with [1, 3] as the current merged range."),
        (ordered, [], (1, 6), "[2, 6] starts at 2, not after 3, so it overlaps and the end grows to 6."),
        (ordered, [(1, 6)], (8, 10), "[8, 10] starts after 6, so [1, 6] is kept and [8, 10] becomes current."),
        (ordered, [(1, 6), (8, 10)], (15, 18), "[15, 18] starts after 10, so [8, 10] is kept."),
        (ordered, [(1, 6), (8, 10), (15, 18)], None, "The input ends. Twenty ticks became three ranges."),
        ([], [], None, "An empty input has no ranges, so the answer is the empty list."),
    ]
    insight_at, fail_at = 6, 7

    def x_of(v):
        return 92 + v * 32

    def bar(f, span, y, h, fill, stroke, text_color=INK, size=T_MARK):
        a, b = span
        f.rect(x_of(a), y, max(3.0, x_of(b) - x_of(a)), h, fill, stroke, 3)
        f.text((x_of(a) + x_of(b)) / 2, y + h / 2 + size * 0.36, "%d-%d" % (a, b), size,
               text_color, anchor="middle")

    def make(step, height=None, rows=0, index=0):
        order, kept, current, line = step
        failing = not order
        last = index == insight_at
        keep = list(kept) + ([current] if current else [])
        f = Frame(
            "Merge intervals: sort by start, then extend or keep",
            sub="Every range is visited once after the sort.",
            diagram=250,
            legend=[("kept", TEAL), ("current", BRASS), ("waiting", BORDER)],
            step=line,
            note="Sorting is what makes the decision local: only the last merged range matters.",
            pairs=[("ranges", len(order), MUTED), ("merged", len(kept), INK),
                   ("current", "%d-%d" % current if current else "-", BRASS)],
            insight=("After the sort a range either overlaps the last one kept or it starts a new "
                     "one, so the decision costs one comparison per range.") if last else None,
            fails=("No ranges arrive at all, so nothing is compared and nothing is merged. The "
                   "empty input returns the empty list without touching the loop body."
                   ) if failing else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        # The range being merged now is the last raw span inside the running
        # range. Draw it in the current colour, a span already inside a merged
        # range in the kept colour, and the rest as still waiting.
        hot = None
        if current:
            for span in order:
                if current[0] <= span[0] and span[1] <= current[1]:
                    hot = span
        for k, span in enumerate(order):
            y = t + 16 + k * 30
            if span == hot:
                bar(f, span, y, 24, CREAM, BRASS, INK)
            elif any(a <= span[0] and span[1] <= b for a, b in keep):
                bar(f, span, y, 24, GREEN, TEAL, INK)
            else:
                bar(f, span, y, 24, GREY, BORDER, MUTED)
        axis = t + 16 + len(order) * 30 + 40
        f.line(x_of(0), axis, x_of(20), axis, INK, 1.4)
        for v in range(0, 21, 5):
            f.line(x_of(v), axis, x_of(v), axis + 7, BORDER, 1.2)
            f.text(x_of(v), axis + 26, str(v), T_MARK, MUTED, anchor="middle")
        if not failing:
            f.text(PAD, axis - 24, "merged", T_MARK, MUTED, layer="text")
            for span in sorted(keep):
                bar(f, span, axis - 46, 26, GREEN, TEAL, INK, T_MARK + 1)
        else:
            cross(f, W / 2 - 96, axis + 46, RUST, 13.0, 2.6)
            f.text(W / 2 - 74, axis + 52, "nothing arrives, so nothing is merged",
                   T_MARK, RUST, anchor="start", bold=True, layer="text")
        return f

    publish("ch03-merge-intervals.gif", frames(make, steps),
            holds(len(steps), longer=(insight_at, fail_at)))


# ------------------------------------------------------- Rotate grid (3.11)

def rotate_grid():
    """Transpose the grid, then reverse every row."""
    grid = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]

    def snap():
        return [r[:] for r in grid]

    def swap(a, b):
        grid[a[0]][a[1]], grid[b[0]][b[1]] = grid[b[0]][b[1]], grid[a[0]][a[1]]

    steps = [(snap(), [], ("start", None),
              "Start. Reading the grid row by row gives 1 2 3 / 4 5 6 / 7 8 9.")]
    for a, b in (((0, 1), (1, 0)), ((0, 2), (2, 0)), ((1, 2), (2, 1))):
        swap(a, b)
        steps.append((snap(), [a, b], ("transpose", a),
                      "Transpose: swap (%d, %d) with (%d, %d). Only the cells above the diagonal "
                      "are visited, so each pair trades places once." % (a + b)))
    steps.append((snap(), [], ("transposed", None),
                  "The transpose is complete. The cell at (i, j) now holds what (j, i) held."))
    for r in range(3):
        grid[r].reverse()
        steps.append((snap(), [(r, 0), (r, 2)], ("reverse row %d" % r, (r, 0)),
                      "Reverse row %d in place. The two ends of the row trade places." % r))
    steps.append((snap(), [], ("done", None),
                  "The grid has turned a quarter turn clockwise, using two sweeps of swaps."))
    steps.append(([[1]], [], ("1 x 1", (0, 0)),
                  "A 1 x 1 grid has no cell to trade with, so both sweeps do nothing."))
    insight_at, fail_at = len(steps) - 2, len(steps) - 1

    def make(step, height=None, rows=0, index=0):
        values, hot, kind, line = step
        size = len(values)
        failing = size == 1
        side = 62.0 if size == 3 else 62.0
        gap = 10.0
        span = size * side + (size - 1) * gap
        x0 = (W - span) / 2.0
        f = Frame(
            "Rotate a grid in place: transpose, then reverse every row",
            sub="Two sweeps of simple swaps, with no second grid and no extra memory.",
            diagram=250,
            legend=[("swapping now", RUST), ("in place", BORDER)],
            step=line,
            note="A transpose swaps across the diagonal. Reversing each row then turns it clockwise.",
            pairs=[("sweep", kind[0], RUST), ("grid", "%d x %d" % (size, size), MUTED)],
            insight=("Transpose then reverse is the rotation, and both sweeps trade pairs in place, "
                     "so the grid needs no second array.") if index == insight_at else None,
            fails=("With one row and one column there is no pair to swap, so both loops run zero "
                   "times and the grid is already its own rotation.") if failing else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        y0 = t + 66
        for c in range(size):
            f.text(x0 + c * (side + gap) + side / 2, t + 34, "col %d" % c, T_MARK, MUTED,
                   anchor="middle", layer="text")
        for r, row_values in enumerate(values):
            f.text(x0 - 16, y0 + r * (side + gap) + side / 2 + 5, "row %d" % r, T_MARK, MUTED,
                   anchor="end", layer="text")
            for c, value in enumerate(row_values):
                x = x0 + c * (side + gap)
                y = y0 + r * (side + gap)
                on = (r, c) in hot
                f.cell(x, y, side, side, value, WHITE, RUST if on else BORDER,
                       size=T_VALUE, color=RUST if on else INK, rx=6,
                       width=2.0 if on else 1.2)
        if len(hot) == 2 and hot[0] != hot[1]:
            f.text(x0 - 96, y0 + 40, "swap", T_MARK, RUST, mono=True, bold=True, layer="text")
            f.text(x0 - 96, y0 + 62, "(%d,%d)" % hot[0], T_MARK, INK, mono=True, layer="text")
            f.text(x0 - 96, y0 + 82, "(%d,%d)" % hot[1], T_MARK, INK, mono=True, layer="text")
            f.arrow(x0 - 40, y0 + 72, x0 - 8, y0 + 72, RUST, 1.8)
        f.text(W - PAD, t + 44, "clockwise", T_MARK, MUTED, anchor="end", layer="text")
        f.arrow(W - PAD - 96, t + 70, W - PAD, t + 70, TEAL, 2.0)
        if failing:
            f.text(W / 2, y0 + 110, "nothing to rotate", T_MARK, RUST, anchor="middle",
                   bold=True, layer="text")
        return f

    publish("ch03-rotate-grid.gif", frames(make, steps),
            holds(len(steps), longer=(insight_at, fail_at)))


# -------------------------------------------- Rotated binary search (3.10.1)

def rotated_search():
    """Binary search on a rotated sorted array, then for a value that is absent."""
    nums = [4, 5, 6, 7, 0, 1, 2]
    steps = [
        (nums, 0, 0, 6, 3, "lo = 0, hi = 6, mid = 3. The left half 4..7 is sorted, and 0 is not in it, so lo = 4."),
        (nums, 0, 4, 6, 5, "lo = 4, hi = 6, mid = 5. The left half 0..1 is sorted and holds 0, so hi = 5."),
        (nums, 0, 4, 5, 4, "lo = 4, hi = 5, mid = 4. a[4] = 0. Found after three comparisons."),
        (nums, 9, 0, 6, 3, "Now search for 9. mid = 3, and the sorted left half 4..7 does not hold it, so lo = 4."),
        (nums, 9, 4, 6, 5, "mid = 5. The sorted left half 0..1 does not hold 9, so lo = 6."),
        (nums, 9, 7, 6, 6, "lo has passed hi, so the range is empty and the search reports -1."),
    ]
    insight_at, fail_at = 2, 5

    def make(step, height=None, rows=0, index=0):
        seq, target, lo, hi, mid, line = step
        found = index == insight_at
        f = Frame(
            "Binary search on a rotated sorted array",
            sub="At every split, at least one half is still sorted. That half decides the move.",
            diagram=170,
            legend=[("the sorted half", TEAL), ("ruled out", BORDER)],
            step=line,
            note="One half of a rotated array is always sorted, and a sorted half is two comparisons to test.",
            pairs=[("target", target, RUST), ("lo", lo, TEAL), ("hi", hi, TEAL), ("mid", mid, INK)],
            insight=("A rotated array is two sorted runs, so one of the two halves at mid is always "
                     "sorted.") if found else None,
            fails=("The array is rotated, not unsorted: every half that was tested was sorted, and 9 "
                   "is in none of them. The scan reports -1.") if index == fail_at else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        live = lo <= hi
        mid = min(max(mid, 0), len(seq) - 1)
        sorted_half = ((lo, mid) if seq[lo] <= seq[mid] else (mid, hi)) if live else (0, 0)
        xs = rail_row(f, t + RAIL, seq, unit=74, gap=12, size=T_VALUE,
                      colors=[TEAL if found and k == mid else
                              (INK if lo <= k <= hi else MUTED) for k in range(len(seq))],
                      bolds=[found and k == mid for k in range(len(seq))])
        if live:
            f.line(xs[lo] - 20, t + RULE, xs[hi] + 20, t + RULE, BORDER, 2.4)
            a, b = sorted_half
            f.line(xs[a] - 20, t + RULE, xs[b] + 20, t + RULE, TEAL, 4.0)
            f.text(xs[a] - 26, t + RULE + 5, "lo", T_MARK, TEAL, anchor="end", layer="text")
            f.text(xs[hi] + 26, t + RULE + 5, "hi", T_MARK, TEAL, anchor="start", layer="text")
            pointer(f, xs[mid], t + RAIL - 16, "mid", INK, above=True)
        else:
            f.text(W / 2, t + RULE + 6, "the range is empty", T_MARK, RUST, anchor="middle",
                   bold=True, layer="text")
        if found:
            f.glow(xs[mid], t + RAIL - 4, 42, TEAL, 0.35)
        index_row(f, xs, t + RAIL + 44, halo=True)
        return f

    publish("ch03-rotated-search.gif", frames(make, steps),
            holds(len(steps), longer=(insight_at, fail_at)))


# ------------------------------------------------------------- KMP (3.12)

def _kmp_lps(needle):
    lps = [0] * len(needle)
    filled = {0}
    length, i = 0, 1
    trace = [(0, 0, 0, set(filled), "start",
              "lps[0] is 0. A one-character string has no proper prefix that is also a suffix.")]
    while i < len(needle):
        compared = length
        if needle[i] == needle[compared]:
            length += 1
            lps[i] = length
            filled.add(i)
            trace.append((i, compared, length, set(filled), "match",
                          "needle[%d] equals needle[%d], so the matched prefix grows to %d and "
                          "lps[%d] = %d." % (i, compared, length, i, length)))
            i += 1
        elif length > 0:
            length = lps[length - 1]
            trace.append((i, compared, length, set(filled), "fallback",
                          "needle[%d] does not match needle[%d], so fall back to length = lps[%d] = %d "
                          "and compare again, without moving i." % (i, compared, compared - 1, length)))
        else:
            lps[i] = 0
            filled.add(i)
            trace.append((i, compared, 0, set(filled), "zero",
                          "needle[%d] does not match needle[0] and length is already 0, so lps[%d] = 0 "
                          "and i moves on." % (i, i)))
            i += 1
    return lps, trace


def kmp_lps():
    """Build the longest-proper-prefix table for the needle."""
    needle = "aabaaac"
    lps, trace = _kmp_lps(needle)
    steps = [(needle, r) for r in trace] + [("a", trace[0])]
    insight_at, fail_at = 3, len(steps) - 1

    def make(step, height=None, rows=0, index=0):
        seq, record = step
        i, compared, length, filled, kind, line = record
        failing = index == fail_at
        f = Frame(
            "KMP, first step: the longest proper prefix that is also a suffix",
            sub="The table is built from the needle alone, before the haystack is read.",
            diagram=200,
            legend=[("matched prefix", TEAL), ("compared with i", BRASS), ("not written yet", BORDER)],
            step=line,
            note="The table is what the search falls back to, so it is built once, up front.",
            pairs=[("i", i if not failing else 0, RUST), ("length", length, TEAL),
                   ("needle[length]", seq[length] if length < len(seq) else "-", BRASS)],
            insight=("On a mismatch the table says how much of the prefix still matches, so no pair "
                     "of characters is compared twice.") if index == insight_at else None,
            fails=("A one-character needle never enters the loop: lps[0] is 0 by definition, so the "
                   "table is written before the first comparison.") if failing else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        xs = rail_row(f, t + RAIL, list(seq), unit=62, gap=8, size=T_VALUE,
                      colors=[RUST if k == i and not failing else
                              (BRASS if k == compared else (TEAL if k < length else MUTED))
                              for k in range(len(seq))],
                      bolds=[k <= length for k in range(len(seq))])
        index_row(f, xs, t + RAIL + 44, halo=True)
        pointer(f, xs[min(i, len(seq) - 1)], t + RAIL - 16, "i", RUST, above=True)
        if kind == "match" and compared < len(seq) and not failing:
            band(f, xs, 0, length - 1, t + RAIL + 66, TEAL, 3.0,
                 label="the prefix that matches")

        values = [str(lps[k]) if k in filled else "." for k in range(len(seq))]
        rail_row(f, t + 156, values, unit=62, gap=8, size=T_CELL + 1,
                 colors=[BRASS if k == i and not failing else
                         (INK if k in filled else MUTED) for k in range(len(seq))],
                 ticks=False)
        f.text(PAD, t + 156, "lps", T_MARK, MUTED, layer="text")
        return f

    publish("ch03-kmp-lps.gif", frames(make, steps),
            holds(len(steps), longer=(insight_at, fail_at)))


def _kmp_search(haystack, needle):
    lps, _ = _kmp_lps(needle)
    left = 0
    trace = [(0, 0, "start", 0,
              "Start: left and right are both 0, so the needle is aligned with the first character.")]
    for right in range(len(haystack)):
        while left > 0 and needle[left] != haystack[right]:
            before = left
            left = lps[left - 1]
            trace.append((left, right, "fallback", left,
                          "needle[%d] does not match haystack[%d], so left falls back to lps[%d] = %d. "
                          "right stays at %d, so no haystack character is read twice."
                          % (before, right, before - 1, left, right)))
        if needle[left] == haystack[right]:
            left += 1
            trace.append((left, right, "match", left - 1,
                          "haystack[%d] matches needle[%d], so left becomes %d." % (right, left - 1, left)))
        else:
            trace.append((left, right, "skip", left,
                          "haystack[%d] matches nothing and left is already 0, so right moves on." % right))
        if left == len(needle):
            trace.append((left, right, "found", left - 1,
                          "left reached %d, the length of the needle. The match starts at "
                          "right - left + 1 = %d." % (len(needle), right - left + 1)))
            return trace
    return trace


def kmp_search():
    """Search for the needle without ever moving right backwards."""
    haystack, needle = "aabaaabaaac", "aabaaac"
    trace = _kmp_search(haystack, needle)
    # The same search for a needle that is not there at all.
    missing_trace = _kmp_search("aabaab", "aabaaac")
    steps = [(haystack, needle, r) for r in trace] + [("aabaab", needle, missing_trace[-1])]
    insight_at, fail_at = len(trace) - 1, len(steps) - 1

    def make(step, height=None, rows=0, index=0):
        text, ndl, record = step
        left, right, kind, compared, line = record
        failing = index == fail_at
        start = right - left + 1 if kind in ("match", "found") else right - left
        start = max(start, 0)
        f = Frame(
            "KMP search: reuse the characters that already matched",
            sub="right only ever moves forward. On a mismatch, left falls back instead.",
            diagram=210,
            legend=[("matched so far", TEAL), ("the character under right", RUST)],
            step=line,
            note="Green is one run of characters that matched, reused rather than re-read.",
            pairs=[("left", left, TEAL), ("right", right, RUST), ("start", start, INK)],
            insight=("right never moves backwards, so each character of the text is read once."
                     ) if index == insight_at else None,
            fails=("The text ends with left at 0. The needle never aligned, so the search reports "
                   "\"not found\" and costs one pass over the text.") if failing else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        xs = rail_row(f, t + RAIL, list(text), unit=48, gap=7, size=T_VALUE - 1,
                      colors=[RUST if k == right else
                              (TEAL if start <= k <= right else MUTED) for k in range(len(text))],
                      bolds=[start <= k <= right for k in range(len(text))])
        index_row(f, xs, t + RAIL + 40, halo=True)
        pointer(f, xs[min(right, len(text) - 1)], t + RAIL - 14, "right", RUST, above=True)

        # The needle sits under the text at the offset start implies.
        ny = t + RULE + 34
        for k, ch in enumerate(ndl):
            x = xs[0] + (start + k) * (48 + 7)
            if x - 24 > W - PAD or x > xs[-1] + 40:
                continue
            matched = k < left and (start + k) <= right and not failing
            here = k == compared
            f.cell(x - 22, ny - 20, 44, 40, ch, WHITE,
                   RUST if here else (TEAL if matched else BORDER),
                   size=T_VALUE - 1, color=INK, rx=6, width=2.0 if here or matched else 1.2)
        f.text(PAD, ny, "needle", T_MARK, MUTED, layer="text")
        if failing:
            f.text(W - PAD, ny, "the needle never fits", T_MARK, RUST, anchor="end",
                   layer="text")
        return f

    publish("ch03-kmp-search.gif", frames(make, steps),
            holds(len(steps), longer=(insight_at, fail_at)))


# ------------------------------------------------------------- Heaps (5.2)

def heap_sift():
    """A new value climbs to its place; the last value sinks after a pop."""
    steps = []
    heap = [9, 5, 8, 3, 2]
    steps.append((heap[:], [], MUTED, "climb",
                  "A valid max-heap: index 0 holds 9, and every parent is at least as large as its children."))
    heap = heap + [10]
    steps.append((heap[:], [len(heap) - 1], TEAL, "climb",
                  "push(10) appends 10 at index 5. Its parent is at (5 - 1) / 2 = 2, which holds 8."))
    i = len(heap) - 1
    while i > 0 and heap[(i - 1) // 2] < heap[i]:
        parent = (i - 1) // 2
        heap[i], heap[parent] = heap[parent], heap[i]
        steps.append((heap[:], [parent, i], TEAL, "climb",
                      "The child is greater than its parent, so they swap and the new value climbs "
                      "to index %d." % parent))
        i = parent
    steps.append((heap[:], [], GREEN, "climb",
                  "Index 0 has no parent, so the climb stops and the heap is valid again."))
    root, last_value = heap[0], heap.pop()
    heap[0] = last_value
    steps.append((heap[:], [0], RUST, "sink",
                  "pop() returns the root, %d. The last value, %d, moves to the root and sinks." % (root, last_value)))
    i = 0
    while True:
        children = [c for c in (2 * i + 1, 2 * i + 2) if c < len(heap)]
        big = max(children, key=lambda c: heap[c]) if children else i
        if not children or heap[big] <= heap[i]:
            break
        heap[i], heap[big] = heap[big], heap[i]
        steps.append((heap[:], [i, big], RUST, "sink",
                      "The larger child is above its parent, so they swap and the value sinks to index %d." % big))
        i = big
    steps.append((heap[:], [], GREEN, "sink",
                  "Neither child is larger, so the sink stops and the heap is valid again."))
    steps.append(([42], [], RUST, "sink",
                  "pop() on a heap of one value: the root leaves and the heap is empty."))
    insight_at, fail_at = len(steps) - 3, len(steps) - 1

    def make(step, height=None, rows=0, index=0):
        values, hot, accent, phase, line = step
        failing = len(values) == 1 and index == fail_at
        f = Frame(
            "Heap push and pop: a new value climbs, the last value sinks",
            sub="A max-heap in an array. The children of i are 2i+1 and 2i+2; the parent is (i-1)/2.",
            diagram=300,
            legend=[("on the move", BRASS), ("in place", BORDER)],
            step=line,
            note="The tree is the array: no links, no allocation, and the parent of i is one division away.",
            pairs=[("phase", phase, RUST), ("index 0", values[0], TEAL), ("size", len(values), INK)],
            insight=("A heap of n values is log n levels deep, so a climb or a sink costs log n."
                     ) if index == insight_at else None,
            fails=("After the root leaves there is no last value to move up, so the heap is empty and "
                   "a second pop has nothing to return.") if failing else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        fills = [CREAM if k in hot else WHITE for k in range(len(values))]
        strokes = [accent if k in hot else BORDER for k in range(len(values))]
        xs = rail_row(f, t + 40, values, unit=62, gap=10, size=T_VALUE,
                      colors=[INK] * len(values), bolds=[k in hot for k in range(len(values))],
                      ticks=False, x0=PAD + 40)
        for k, x in enumerate(xs):
            f.rect(x - 28, t + 22, 56, 6, strokes[k], "none", 2)
        index_labels(f, [(x - 28, t + 22, 56, 6) for x in xs], t + 64)
        if hot:
            f.glow(xs[min(hot)], t + 40, 48, accent, 0.3)
        f.text(PAD, t + 128, "the same values as a tree", T_MARK, MUTED, layer="text")
        heap_tree(f, values, base_x=470, top=t + 170, dy=62, spacing=210, r=19,
                  fills=fills, strokes=strokes)
        if failing:
            cross(f, 470, t + 210, RUST, 26.0, 2.8)
            f.text(470, t + 250, "the heap is empty", T_MARK, RUST, anchor="middle",
                   bold=True, layer="text")
        return f

    publish("ch05-heap-sift.gif", frames(make, steps),
            holds(len(steps), longer=(insight_at, fail_at)))


# -------------------------------------------------- Top k frequent (5.4)

def top_k():
    """Keep a min-heap of size k over the counts."""
    stream = [1, 1, 1, 2, 2, 3]
    counts = []
    for v in stream:
        for i, (value, c) in enumerate(counts):
            if value == v:
                counts[i] = (value, c + 1)
                break
        else:
            counts.append((v, 1))
    heap = []
    steps = [(list(heap), None, 2, "start",
              "Count each number first, then keep a min-heap of size k over the counts.")]
    for value, count in counts:
        if len(heap) < 2:
            heap.append((value, count))
            heap.sort(key=lambda e: e[1])
            steps.append((list(heap), (value, count), 2, "push",
                          "%d appears %d times and the heap has room, so it goes in." % (value, count)))
        elif count > heap[0][1]:
            out = heap[0]
            heap[0] = (value, count)
            heap.sort(key=lambda e: e[1])
            steps.append((list(heap), (value, count), 2, "replace",
                          "%d appears %d times, more than the smallest kept count %d, so %d is dropped."
                          % (value, count, out[1], out[0])))
        else:
            steps.append((list(heap), (value, count), 2, "skip",
                          "%d appears %d times, no more than the smallest kept count %d, so it is ignored."
                          % (value, count, heap[0][1])))
    steps.append((list(heap), None, 2, "done",
                  "Every number has been counted once. The heap holds the two values with the largest counts."))
    steps.append(([(1, 3), (2, 2), (3, 1)], None, 9, "k too big",
                  "Now k = 9 over the same counts. The heap has room for nine entries and only three exist."))
    insight_at, fail_at = len(steps) - 2, len(steps) - 1

    def make(step, height=None, rows=0, index=0):
        values, arriving, k, kind, line = step
        too_big = kind == "k too big"
        f = Frame(
            "The k most frequent values: a heap of size k, never bigger",
            sub="The heap stores k entries, so its cost does not grow with the input.",
            diagram=180,
            legend=[("kept", TEAL), ("just arrived", BRASS), ("ignored", BORDER)],
            step=line,
            note="The root of a min-heap is the weakest entry kept, so a new count is compared with it alone.",
            pairs=[("k", k, INK), ("kept", len(values), TEAL),
                   ("arriving", "%d : %d" % arriving if arriving else "-", BRASS)],
            insight=("The heap holds k entries, so each new count costs log k rather than a full sort."
                     ) if index == insight_at else None,
            fails=("k larger than the number of distinct values is not an error. The heap simply "
                   "never fills, so the answer is every value there is.") if too_big else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        f.text(PAD, t + 20, "counts", T_MARK, MUTED, layer="text")
        cxs = rail_row(f, t + 40, ["%d:%d" % c for c in counts], unit=84, gap=10,
                       size=T_CELL, ticks=False, x0=PAD + 110,
                       colors=[BRASS if arriving and c == arriving else
                               (INK if c in values else MUTED) for c in counts],
                       bolds=[c in values for c in counts])
        f.text(PAD, t + 124, "the best k, as a min-heap", T_MARK, MUTED, layer="text")
        if values:
            hxs = rail_row(f, t + 144, ["%d:%d" % e for e in values], unit=84, gap=10,
                           size=T_CELL, ticks=False, x0=PAD + 110,
                           colors=[INK] * len(values))
            for x in hxs:
                f.rect(x - 38, t + 126, 76, 5, TEAL, "none", 2)
            f.text(hxs[0], t + 186, "root: the smallest count kept", T_MARK, TEAL,
                   anchor="middle", bold=True, layer="text")
        else:
            f.text(PAD + 110, t + 148, "empty", T_MARK, MUTED, mono=True, layer="text")
        if too_big:
            f.text(W - PAD, t + 124, "the heap never fills", T_MARK, RUST, anchor="end",
                   layer="text")
        return f

    publish("ch05-top-k.gif", frames(make, steps),
            holds(len(steps), longer=(insight_at, fail_at)))


# -------------------------------------------------- Coin change DP (6.1)

def coin_change():
    """Fill dp[0] to dp[amount] from the coins."""
    coins, amount = [1, 2, 5], 11
    dp = [None] * (amount + 1)
    dp[0] = 0
    trace = [(0, 0, None, dp[:], "dp[0] = 0. Zero coins make zero, whatever the coins are.")]
    for t_ in range(1, amount + 1):
        best, src, options = None, None, []
        for c in coins:
            if c <= t_ and dp[t_ - c] is not None:
                options.append((c, dp[t_ - c] + 1))
                if best is None or dp[t_ - c] + 1 < best:
                    best, src = dp[t_ - c] + 1, t_ - c
        dp[t_] = best
        trace.append((t_, best, src, dp[:],
                      "dp[%d] reads %s, and the smallest is %d."
                      % (t_, ", ".join("dp[%d] + 1 = %d" % (t_ - c, v) for c, v in options), best)))
    steps = [(coins, amount, r) for r in trace] + [([3, 5], 7, None)]
    insight_at, fail_at = len(trace) - 1, len(steps) - 1

    def make(step, height=None, rows=0, index=0):
        cs, want, record = step
        failing = record is None
        if failing:
            table = [None] * (want + 1)
            table[0] = 0
            for t_ in range(1, want + 1):
                best = None
                for c in cs:
                    if c <= t_ and table[t_ - c] is not None:
                        best = table[t_ - c] + 1 if best is None else min(best, table[t_ - c] + 1)
                table[t_] = best
            t_, best, src = want, table[want], None
            snapshot = table
            line = "Now coins 3 and 5 for the amount 7. No combination of them makes 7."
        else:
            t_, best, src, snapshot, line = record
        f = Frame(
            "Coin change: the fewest coins for every amount up to 11",
            sub="dp[t] is the smallest of dp[t - coin] + 1 over the coins.",
            diagram=170,
            legend=[("being filled", RUST), ("read by it", BRASS), ("unreachable", BORDER)],
            step=line,
            note="A dot means the amount cannot be made from the coins, so no rule reaches it yet.",
            pairs=[("coins", " ".join(str(c) for c in cs), INK), ("t", t_, RUST),
                   ("dp[t]", best if best is not None else "unreachable", TEAL)],
            insight=("dp[t] reads only entries below t, so the table fills left to right and each "
                     "entry is computed once.") if index == insight_at else None,
            fails=("Some amounts cannot be made at all, and the table leaves them holding \"no "
                   "answer\" rather than 0. Reporting 0 coins would be the wrong answer.") if failing else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        values = [str(snapshot[k]) if snapshot[k] is not None else "." for k in range(want + 1)]
        sources = ({t_ - c for c in cs if c <= t_ and snapshot[t_ - c] is not None}
                   if not failing else {t_ - c for c in cs if c <= t_ and snapshot[t_ - c] is not None})
        xs = rail_row(f, t + RAIL, values, unit=52, gap=6, size=T_CELL + 1,
                      colors=[BRASS if k in sources and k != t_ else
                              (RUST if k == t_ else (INK if snapshot[k] is not None else MUTED))
                              for k in range(want + 1)],
                      bolds=[k == t_ for k in range(want + 1)], ticks=False)
        for k, x in enumerate(xs):
            f.rect(x - 21, t + RAIL + 12, 42, 5,
                   RUST if k == t_ else (BRASS if k in sources and k != t_ else BORDER),
                   "none", 2)
        index_row(f, xs, t + RAIL + 38, halo=True)
        f.text(PAD, t + RAIL + 2, "dp", T_MARK, MUTED, layer="text")
        if failing:
            f.text(W - PAD, t + RAIL + 2, "no combination makes %d" % t_, T_MARK, RUST,
                   anchor="end", layer="text")
            f.text(W / 2, t + RULE + 4, "with coins 3 and 5, the amounts 1, 2, 4 and 7 stay unreachable",
                   T_MARK, RUST, anchor="middle", layer="text")
        return f

    publish("ch06-coin-change.gif", frames(make, steps),
            holds(len(steps), longer=(insight_at, fail_at)))


# -------------------------------------------------------- Subsets (6.2)

def subsets():
    """Every path down the choice tree is one subset."""
    nums = [1, 2, 3]
    records, result = [], []

    def backtrack(start, path):
        result.append(list(path))
        records.append((nums, list(path), start))
        for idx in range(start, len(nums)):
            path.append(nums[idx])
            backtrack(idx + 1, path)
            path.pop()

    backtrack(0, [])
    records.append(([], [], 0))

    nodes = [(), (1,), (2,), (3,), (1, 2), (1, 3), (2, 3), (1, 2, 3)]
    pos = {(): (410, 34), (1,): (250, 106), (2,): (410, 106), (3,): (570, 106),
           (1, 2): (180, 178), (1, 3): (320, 178), (2, 3): (410, 178),
           (1, 2, 3): (180, 250)}
    edges = [((), (1,)), ((), (2,)), ((), (3,)), ((1,), (1, 2)), ((1,), (1, 3)),
             ((2,), (2, 3)), ((1, 2), (1, 2, 3))]
    insight_at, fail_at = len(records) - 2, len(records) - 1

    def label(node):
        return "{}" if not node else "{%s}" % ",".join(str(v) for v in node)

    def make(step, height=None, rows=0, index=0):
        seq, path, start = step
        cur = tuple(path)
        empty = not seq
        last = index == insight_at
        f = Frame(
            "Subsets: every path down the tree is one subset",
            sub="Each call records the path so far, then tries every larger index.",
            diagram=296,
            legend=[("the path now", BRASS), ("its prefixes", TEAL), ("off the path", BORDER)],
            step=("An empty input has one subset, the empty set, and the loop never runs."
                  if empty else
                  "The call reaches %s and records it, then tries each index from %d upward."
                  % (label(cur), start)),
            note="Backtracking pops the value it added, so one path buffer serves the whole tree.",
            pairs=[("path", label(cur), BRASS), ("start", start, INK),
                   ("recorded", 1 if empty else index + 1, TEAL)],
            insight=("Every node of the tree is one subset, and a tree of n choices has 2^n nodes."
                     ) if last else None,
            fails=("With no values to choose between there is nothing to branch on, so the whole "
                   "answer is the one empty subset. The count is still 2^0 = 1.") if empty else None,
            at=(index, len(records)),
            height=height, insight_rows=rows,
        )
        t = f.top
        if empty:
            f.text(W / 2, t + 130, "{}   one subset", T_VALUE, INK, mono=True,
                   anchor="middle")
            f.text(W / 2, t + 170, "the loop has nothing to iterate over", T_MARK, MUTED,
                   anchor="middle", layer="text")
            return f
        local = {k: (x, y + t) for k, (x, y) in pos.items()}
        for a, b in edges:
            on = cur[:len(a)] == a and cur[:len(b)] == b
            f.line(local[a][0], local[a][1] + 22, local[b][0], local[b][1] - 22,
                   TEAL if on else BORDER, 2.4 if on else 1.4)
        for key in nodes:
            x, y = local[key]
            prefix = tuple(key) == cur[:len(key)]
            here = key == cur
            text = label(key)
            r = max(26.0, text_width(text, T_CELL - 2, True) / 2.0 + 11)
            f.circle(x, y, r, WHITE, BRASS if here else (TEAL if prefix else BORDER),
                     2.2 if here or prefix else 1.2)
            f.text(x, y + 6, text, T_CELL - 2, INK, mono=True, anchor="middle", bold=here)
        f.text(PAD, t + 278, "recorded:  %s"
               % "  ".join(label(tuple(r)) for r in result[:index + 1]),
               T_MARK, MUTED, mono=True, layer="text")
        return f

    publish("ch06-subsets.gif", frames(make, records),
            holds(len(records), longer=(insight_at, fail_at)))


BUILDERS = {
    "two-sum": two_sum,
    "brackets": brackets,
    "three-sum": three_sum,
    "merge-intervals": merge_intervals,
    "rotate-grid": rotate_grid,
    "rotated-search": rotated_search,
    "kmp-lps": kmp_lps,
    "kmp-search": kmp_search,
    "heap-sift": heap_sift,
    "top-k": top_k,
    "coin-change": coin_change,
    "subsets": subsets,
}
