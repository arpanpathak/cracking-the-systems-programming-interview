"""Animations for the problem chapters, chapters 3 to 6.

Each builder writes one looping GIF to `src/figures`. A frame shows one step of
the algorithm the chapter quotes, with the same variable names, so a reader can
check a frame against the listing beside it.

The drawing area of each frame carries the part of the explanation a reader can
see: the tinted band for the region under discussion, a faint outline where the
region was a step ago, and a chip naming each pointer. The insight band is saved
for the one step where the idea clicks.
"""

from animlib import *  # noqa: F401,F403
from animlib import Frame, frames, publish


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


def heap_tree(f, values, base_x, top, dy=62, spacing=210, w=56, h=40,
              fills=None, strokes=None, colors=None):
    """Draw a complete binary tree over the array `values`, top-down."""
    pos = _heap_positions(len(values), base_x, top, dy, spacing)
    for i in range(1, len(values)):
        parent = (i - 1) // 2
        f.line(pos[parent][0], pos[parent][1] + h / 2, pos[i][0], pos[i][1] - h / 2, BORDER, 1.6)
    for i, value in enumerate(values):
        x, y = pos[i]
        f.cell(x - w / 2, y - h / 2, w, h, value,
               fills[i] if fills else PALE, strokes[i] if strokes else INK,
               size=T_CELL - 1, mono=True, color=colors[i] if colors else INK)
    return pos


# --------------------------------------------------------------- Two Sum (3.5)

def two_sum():
    """One pass over the array, with a map of the values already seen."""
    nums = [2, 7, 11, 15]
    target = 9
    steps = [
        (0, {}, "miss",
         "i = 0 holds 2. The partner it needs is 9 - 2 = 7, and the map is empty, so 2 is stored instead."),
        (1, {2: 0}, "hit",
         "i = 1 holds 7. The partner it needs is 9 - 7 = 2, and the map holds 2 at index 0. The pair is (0, 1)."),
        (1, {2: 0}, "done",
         "The scan stops after two of the four numbers, because the pair is already complete."),
    ]

    cw, gap = 92, 10
    x0 = PAD
    panel_x = x0 + 4 * (cw + gap) + 34

    def make(step, height=None, insight_rows=0):
        i, seen, kind, line = step
        last = step is steps[-1]
        f = Frame(
            "Two Sum: remember each number so a later one can find its partner",
            sub="One pass. For each x, ask the map for target - x.",
            diagram=210,
            legend=[("the current number", PINK, RUST), ("the pair", GREEN, TEAL)],
            step=line,
            note="The map turns a second scan into a single lookup.",
            pairs=[("i", i, RUST), ("x", nums[i], INK), ("need", target - nums[i], TEAL)],
            insight=("The map holds the partner of every number already passed, so one pass "
                     "is enough.") if last else None,
            height=height, insight_rows=insight_rows,
        )
        t = f.top
        row_y, ch = t + 56, 62
        pair = {0, 1} if last else set()
        cells = row(f, x0, row_y, cw, ch, nums, gap=gap, size=T_CELL + 1,
                    fills=[GREEN if k in pair else (PINK if k == i else PALE) for k in range(len(nums))],
                    strokes=[TEAL if k in pair else (RUST if k == i else BORDER) for k in range(len(nums))])
        index_labels(f, cells, row_y + ch + 20)
        pointer_down(f, row_center(cells, i)[0], row_y - 2, "i", RUST, gap=24)

        f.panel(panel_x, row_y - 14, W - PAD - panel_x, ch + 28, "the map: value -> index")
        if not seen:
            f.text(panel_x + 18, row_y + 44, "empty", T_STEP, MUTED, mono=True)
        for k, (value, index) in enumerate(sorted(seen.items())):
            f.text(panel_x + 18, row_y + 46 + k * 30, "%d  ->  %d" % (value, index), T_STEP,
                   INK, mono=True, bold=True)
        if kind == "hit":
            f.glow(panel_x + 120, row_y + 44 + 30 * len(seen), 74, TEAL, 0.34)
        f.text(panel_x + 18, row_y + 100, "look up  %d" % (target - nums[i]), T_STEP - 1,
               TEAL if kind == "hit" else MUTED, mono=True, bold=kind == "hit")
        return f

    publish("ch03-two-sum.gif", frames(make, steps), [2600] * len(steps))


# ---------------------------------------------------------- Brackets (3.6.1)

def brackets():
    """A stack of openers, popped by every closer."""
    text = "([{}])"
    steps = [
        (-1, "", "Start before the first character. The stack is empty."),
        (0, "(", "An opener, so it goes on the stack. The stack records what still waits for a partner."),
        (1, "([", "Another opener, pushed on top of the first."),
        (2, "([{", "A third opener, pushed. From the bottom up, the stack is ( [ { ."),
        (3, "([", "A closer. Pop the top, which is '{', and compare. It matches, so the pair is closed."),
        (4, "(", "A closer. Pop '[' and compare. It matches."),
        (5, "", "A closer. Pop '(' and compare. It matches, and the stack is empty again."),
        (6, "", "No characters are left and the stack is empty, so every opener found its closer."),
    ]

    cw, gap = 56, 8
    x0 = (W - (len(text) * cw + (len(text) - 1) * gap)) / 2.0

    def make(step, height=None, insight_rows=0):
        i, stack, line = step
        last = step is steps[-1]
        previous = steps[steps.index(step) - 1][1] if steps.index(step) else ""
        popped = previous[-1] if len(previous) > len(stack) else None
        f = Frame(
            "Valid brackets: a closer must match the most recent unmatched opener",
            sub="Counting openers is not enough. The order decides the answer.",
            diagram=240,
            legend=[("the stack", GREEN, TEAL), ("the character now", PINK, RUST)],
            step=line,
            note="The stack is the reason a single counter cannot answer this.",
            pairs=[("i", i, RUST), ("char", text[i] if 0 <= i < len(text) else "-", INK),
                   ("stack", len(stack), TEAL)],
            insight=("A closer must match the most recent opener, which is what a stack "
                     "hands back.") if last else None,
            height=height, insight_rows=insight_rows,
        )
        t = f.top
        f.text(PAD, t + 34, "input", T_CHIP, MUTED)
        boxes = row(f, x0, t + 46, cw, 56, text, gap=gap, size=T_CELL,
                    fills=[PINK if k == i else PALE for k in range(len(text))],
                    strokes=[RUST if k == i else BORDER for k in range(len(text))],
                    colors=[WHITE if k == i else INK for k in range(len(text))])
        index_labels(f, boxes, t + 124)

        sy = t + 160
        f.text(PAD, sy + 30, "stack", T_CHIP, MUTED)
        if stack:
            sboxes = row(f, x0, sy, cw, 54, stack, gap=gap, size=T_CELL,
                         fills=[GREEN] * len(stack))
            top = row_center(sboxes, len(stack) - 1)
            f.text(top[0], sy + 78, "top", T_CHIP, TEAL, anchor="middle", bold=True)
            f.arrow(top[0], sy + 70, top[0], sy + 60, TEAL, 1.5)
        else:
            f.rect(x0, sy, cw, 54, WHITE, BORDER, 6, dash=True)
            f.text(x0 + cw / 2, sy + 34, "empty", T_CHIP, MUTED, anchor="middle")
        if popped is not None:
            f.text(x0 + max(1, len(stack)) * (cw + gap) + 12, sy + 34,
                   "popped %s" % popped, T_CHIP, RUST, mono=True, bold=True)
        return f

    publish("ch03-brackets.gif", frames(make, steps), [2100] * len(steps))


# --------------------------------------------------------- Three Sum (3.7.2)

def _three_sum_trace(nums):
    trace = []
    n = len(nums)
    for i in range(n - 2):
        if i > 0 and nums[i] == nums[i - 1]:
            trace.append((i, i + 1, n - 1, None,
                          "nums[%d] repeats the value just before it, so every triple that starts "
                          "here has already been found." % i))
            continue
        lo, hi = i + 1, n - 1
        while lo < hi:
            total = nums[i] + nums[lo] + nums[hi]
            if total == 0:
                found = (nums[i], nums[lo], nums[hi])
                trace.append((i, lo, hi, found,
                              "The sum is 0, so (%d, %d, %d) is a triple. Move both pointers inward "
                              "and keep looking." % found))
                lo += 1
                hi -= 1
            elif total < 0:
                trace.append((i, lo, hi, None,
                              "The sum is %d, below 0. The left value must grow, so lo moves right." % total))
                lo += 1
            else:
                trace.append((i, lo, hi, None,
                              "The sum is %d, above 0. The right value must shrink, so hi moves left." % total))
                hi -= 1
    return trace


def three_sum():
    """Fix one value, then close two pointers over the rest of the sorted array."""
    nums = [-4, -1, -1, 0, 1, 2]
    trace = _three_sum_trace(nums)
    # The triples found up to and including each step, worked out once. A frame
    # is rebuilt several times while the canvas height settles, so a builder
    # closure must not accumulate anything.
    so_far = []
    running = []
    for record in trace:
        if record[3]:
            running = running + [record[3]]
        so_far.append(running)

    cw, gap = 86, 8
    x0 = (W - (len(nums) * cw + (len(nums) - 1) * gap)) / 2.0

    def make(step, height=None, insight_rows=0):
        i, lo, hi, triple, line = step
        found = so_far[trace.index(step)]
        first_triple = bool(triple) and len(found) == 1
        f = Frame(
            "Three Sum: fix one number, then close two pointers over the rest",
            sub="Sorted input turns a pointer move into a decision instead of a guess.",
            diagram=260,
            legend=[("fixed", CREAM, TEAL), ("the two pointers", CREAM, BRASS), ("the triple", GREEN, TEAL)],
            step=line,
            note="Every move drops one index, so the pair of pointers costs one scan, not two.",
            pairs=[("i", i, TEAL), ("lo", lo, BRASS), ("hi", hi, RUST),
                   ("sum", nums[i] + nums[lo] + nums[hi] if lo < len(nums) and hi >= 0 else "-", INK)],
            insight=("A sum that is too small needs a larger left value, and the array is "
                     "sorted, so lo moves right.") if first_triple else None,
            height=height, insight_rows=insight_rows,
        )
        t = f.top
        row_y, ch = t + 66, 62
        fills = [GREEN if triple and k in (i, lo, hi) else
                 (CREAM if k in (i, lo, hi) else PALE) for k in range(len(nums))]
        strokes = [TEAL if triple and k in (i, lo, hi) else
                   (TEAL if k == i else (BRASS if k in (lo, hi) else BORDER))
                   for k in range(len(nums))]
        cells = row(f, x0, row_y, cw, ch, nums, gap=gap, size=T_CELL + 1, fills=fills,
                    strokes=strokes)
        index_labels(f, cells, row_y + ch + 20)
        f.zone(x0 + lo * (cw + gap) - 10, row_y - 10, (hi - lo) * (cw + gap) + cw + 20, ch + 20,
               color=BRASS, dash=True, opacity=0.07)
        pointer_down(f, row_center(cells, i)[0], row_y - 2, "i", TEAL, gap=24)
        pointer_up(f, row_center(cells, lo)[0], row_y + ch + 2, "lo", BRASS, gap=22, leader=False)
        pointer_up(f, row_center(cells, hi)[0], row_y + ch + 2, "hi", RUST, gap=22, leader=False)

        f.text(PAD, t + 224, "triples so far:  %s"
               % ("  ".join("(%d,%d,%d)" % t3 for t3 in found) or "none"),
               T_STEP - 1, TEAL if found else MUTED, mono=True)
        return f

    publish("ch03-three-sum.gif", frames(make, trace), [2300] * len(trace))


# ---------------------------------------------------- Merge intervals (3.9)

def merge_intervals():
    """Sort by start, then extend the current range or keep it."""
    raw = [(15, 18), (2, 6), (1, 3), (8, 10)]
    ordered = sorted(raw)
    steps = [
        (raw, None, set(), -1, "The input arrives unsorted, so no range can be trusted to arrive next."),
        (ordered, None, set(), -1, "Sort by start. Now any range that overlaps the last one always arrives next."),
        (ordered, ordered[0], set(), 0, "Start with [1, 3] as the current merged range."),
        (ordered, (1, 6), {0}, 1, "[2, 6] starts at 2, which is not after 3, so it overlaps. The end grows to 6."),
        (ordered, (8, 10), {0, 1}, 2, "[8, 10] starts after 6, so it does not overlap. Keep [1, 6] and start [8, 10]."),
        (ordered, (15, 18), {0, 1, 2}, 3, "[15, 18] starts after 10, so keep [8, 10] and start [15, 18]."),
        (ordered, None, {0, 1, 2, 3}, -1, "The input ends, so the last range is kept. Twenty ticks became three ranges."),
    ]
    merged_after = [set(), set(), set(), set(), {(1, 6)}, {(1, 6), (8, 10)},
                    {(1, 6), (8, 10), (15, 18)}]

    def x_of(v):
        return 66 + v * 36

    def bar(f, span, y, h, fill, stroke, text_color=INK, size=T_CHIP):
        a, b = span
        f.rect(x_of(a), y, x_of(b) - x_of(a), h, fill, stroke, 4)
        f.text((x_of(a) + x_of(b)) / 2, y + h / 2 + size * 0.36, "%d-%d" % (a, b), size,
               text_color, anchor="middle")

    def make(step, height=None, insight_rows=0):
        index = steps.index(step)
        order, current, done, hot, line = step
        last = step is steps[-1]
        f = Frame(
            "Merge intervals: sort by start, then extend or keep",
            sub="Every range is visited once after the sort.",
            diagram=290,
            legend=[("kept", GREEN, TEAL), ("current range", CREAM, TEAL), ("waiting", GREY, BORDER)],
            step=line,
            note="Sorting is what makes the decision local: only the last merged range matters.",
            pairs=[("current", "%d-%d" % current if current else "-", TEAL),
                   ("merged", len(merged_after[index]), INK),
                   ("ranges", len(order), MUTED)],
            insight=("After the sort, a range either overlaps the last one kept or it starts "
                     "a new one.") if last else None,
            height=height, insight_rows=insight_rows,
        )
        t = f.top
        f.text(PAD, t + 16, "input order", T_CHIP, MUTED)
        for k, span in enumerate(order):
            y = t + 26 + k * 32
            if k in done:
                bar(f, span, y, 26, GREEN, TEAL, INK)
            elif k == hot:
                bar(f, span, y, 26, CREAM, TEAL, INK)
            else:
                bar(f, span, y, 26, GREY, BORDER, MUTED)
        axis = t + 186
        f.line(x_of(0), axis, x_of(20), axis, INK, 1.6)
        for v in range(0, 21, 5):
            f.line(x_of(v), axis - 4, x_of(v), axis + 4, INK, 1.2)
            f.text(x_of(v), axis + 20, str(v), T_CHIP, MUTED, anchor="middle")
        f.text(PAD, axis + 54, "merged", T_CHIP, MUTED)
        keep = set(merged_after[index])
        if order and current:
            keep = keep | {current}
        for span in sorted(keep):
            bar(f, span, axis + 36, 28, GREEN, TEAL, INK, T_CHIP + 1)
        return f

    publish("ch03-merge-intervals.gif", frames(make, steps), [2200] * len(steps))


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

    cw, gap = 78, 8
    x0 = (W - (3 * cw + 2 * gap)) / 2.0

    def make(step, height=None, insight_rows=0):
        values, hot, kind, line = step
        last = step is steps[-1]
        f = Frame(
            "Rotate a grid in place: transpose, then reverse every row",
            sub="Two sweeps of simple swaps, with no second grid and no extra memory.",
            diagram=310,
            legend=[("swapping now", PINK, RUST), ("in place", PALE, BORDER)],
            step=line,
            note="A transpose swaps across the diagonal. Reversing each row then turns it clockwise.",
            pairs=[("sweep", kind[0], RUST),
                   ("cell", "%d,%d" % kind[1] if kind[1] else "-", INK),
                   ("grid", "3 x 3", MUTED)],
            insight=("Transpose then reverse is the rotation, and both sweeps work in place."
                     ) if last else None,
            height=height, insight_rows=insight_rows,
        )
        t = f.top
        y0 = t + 44
        for c in range(3):
            f.text(x0 + c * (cw + gap) + cw / 2, t + 14, "col %d" % c, T_CHIP, MUTED,
                   anchor="middle")
        for r, row_values in enumerate(values):
            f.text(x0 - 18, y0 + r * (cw + gap) + cw / 2 + 5, "row %d" % r, T_CHIP, MUTED,
                   anchor="end")
            for c, value in enumerate(row_values):
                x = x0 + c * (cw + gap)
                y = y0 + r * (cw + gap)
                on = (r, c) in hot
                f.cell(x, y, cw, cw, value, PINK if on else PALE, RUST if on else BORDER,
                       size=T_CELL + 1, color=WHITE if on else INK)
        if len(hot) == 2:
            a, b = hot
            f.text(x0 - 120, y0 + 40, "swap", T_CHIP, RUST, mono=True, bold=True)
            f.text(x0 - 120, y0 + 64, "(%d,%d)" % a, T_CHIP, INK, mono=True)
            f.text(x0 - 120, y0 + 84, "(%d,%d)" % b, T_CHIP, INK, mono=True)
            f.arrow(x0 - 40, y0 + 74, x0 - 8, y0 + 74, RUST, 1.8)
        f.text(W - PAD, y0 + 40, "clockwise", T_CHIP, MUTED, anchor="end")
        f.arrow(W - PAD - 110, y0 + 66, W - PAD, y0 + 66, TEAL, 2.0)
        return f

    publish("ch03-rotate-grid.gif", frames(make, steps), [2000] * len(steps))


# -------------------------------------------- Rotated binary search (3.10.1)

def rotated_search():
    """Binary search on a rotated sorted array."""
    nums = [4, 5, 6, 7, 0, 1, 2]
    target = 0
    lo, hi, steps = 0, len(nums), []
    while lo < hi:
        mid = lo + (hi - lo) // 2
        if nums[mid] == target:
            steps.append((lo, hi, mid, None,
                          "mid points at 0, which is the target. The search ends after three comparisons."))
            break
        if nums[lo] <= nums[mid]:
            inside = nums[lo] <= target < nums[mid]
            steps.append((lo, hi, mid, (lo, mid),
                          "The left half %d..%d is sorted and 0 is %s it, so the search %s"
                          % (nums[lo], nums[mid], "inside" if inside else "not inside",
                             "moves there: hi = mid." if inside else "moves right: lo = mid + 1.")))
            if inside:
                hi = mid
            else:
                lo = mid + 1
        else:
            inside = nums[mid] < target <= nums[hi - 1]
            steps.append((lo, hi, mid, (mid, hi - 1),
                          "The right half %d..%d is sorted and 0 is %s it, so the search %s"
                          % (nums[mid], nums[hi - 1], "inside" if inside else "not inside",
                             "moves there: lo = mid + 1." if inside else "moves left: hi = mid.")))
            if inside:
                lo = mid + 1
            else:
                hi = mid

    cw, gap = 76, 10
    x0 = (W - (len(nums) * cw + (len(nums) - 1) * gap)) / 2.0

    def make(step, height=None, insight_rows=0):
        lo, hi, mid, sorted_half, line = step
        last = step is steps[-1]
        f = Frame(
            "Binary search on a rotated sorted array",
            sub="At every split, at least one half is still sorted. That half decides the move.",
            diagram=260,
            legend=[("the sorted half", GREEN, TEAL), ("ruled out", GREY, BORDER),
                    ("still in range", PALE, INK)],
            step=line,
            note="A sorted half can be tested with two comparisons, which is what keeps the cost logarithmic.",
            pairs=[("lo", lo, TEAL), ("hi", hi, RUST), ("mid", mid, INK),
                   ("nums[mid]", nums[mid], BRASS)],
            insight=("A rotated array is two sorted runs, so one half at mid is always sorted."
                     ) if last else None,
            height=height, insight_rows=insight_rows,
        )
        t = f.top
        row_y, ch = t + 62, 58
        fills, strokes, colors = [], [], []
        for k in range(len(nums)):
            if k == mid:
                fills.append(CREAM); strokes.append(BRASS); colors.append(INK)
            elif lo <= k < hi:
                fills.append(PALE); strokes.append(INK); colors.append(INK)
            else:
                fills.append(GREY); strokes.append(BORDER); colors.append(MUTED)
        if sorted_half:
            a, b = sorted_half
            for k in range(max(0, a), min(len(nums) - 1, b) + 1):
                if lo <= k < hi:
                    fills[k], strokes[k] = GREEN, TEAL
        cells = row(f, x0, row_y, cw, ch, nums, gap=gap, size=T_CELL, fills=fills,
                    strokes=strokes, colors=colors)
        index_labels(f, cells, row_y + ch + 20)
        left = x0 + lo * (cw + gap)
        right = x0 + (hi - 1) * (cw + gap) + cw
        f.line(left, row_y + ch + 40, right, row_y + ch + 40, TEAL, 2.0)
        for x in (left, right):
            f.line(x, row_y + ch + 40, x, row_y + ch + 50, TEAL, 2.0)
        chip(f, left, row_y + ch + 74, "lo", TEAL)
        chip(f, right, row_y + ch + 74, "hi", TEAL)
        pointer_down(f, row_center(cells, mid)[0], row_y - 2, "mid", BRASS, gap=24)
        return f

    publish("ch03-rotated-search.gif", frames(make, steps), [2600] * len(steps))


# ------------------------------------------------------------- KMP (3.12)

def _kmp_lps(needle):
    """The table, and one record for every comparison the build makes."""
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
                          "needle[%d] = '%s' equals needle[%d] = '%s', so the matched prefix grows "
                          "to %d and lps[%d] = %d." % (i, needle[i], compared, needle[compared],
                                                       length, i, length)))
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
                          "needle[%d] does not match needle[0] and length is already 0, so "
                          "lps[%d] = 0 and i moves on." % (i, i)))
            i += 1
    return lps, trace


def kmp_lps():
    """Build the longest-proper-prefix table for the needle."""
    needle = "aabaaac"
    lps, trace = _kmp_lps(needle)
    cw, gap = 68, 8
    x0 = (W - (len(needle) * cw + (len(needle) - 1) * gap)) / 2.0

    def make(step, height=None, insight_rows=0):
        i, compared, length, filled, kind, line = step
        last = step is trace[-1]
        f = Frame(
            "KMP, first step: the longest proper prefix that is also a suffix",
            sub="The table is built from the needle alone, before the haystack is read.",
            diagram=290,
            legend=[("matched prefix", GREEN, TEAL), ("compared with i", CREAM, BRASS),
                    ("not written yet", GREY, BORDER)],
            step=line,
            note="The table is what the search falls back to, so it is built once, up front.",
            pairs=[("i", i, RUST), ("length", length, TEAL),
                   ("needle[length]", needle[length] if length < len(needle) else "-", BRASS)],
            insight=("On a mismatch the table says how much of the prefix still matches."
                     ) if last else None,
            height=height, insight_rows=insight_rows,
        )
        t = f.top
        fills, strokes, colors = [], [], []
        for k in range(len(needle)):
            if k == i:
                fills.append(PINK); strokes.append(RUST); colors.append(WHITE)
            elif k == compared and kind != "start":
                fills.append(CREAM); strokes.append(BRASS); colors.append(INK)
            elif k < length:
                fills.append(GREEN); strokes.append(TEAL); colors.append(INK)
            else:
                fills.append(PALE); strokes.append(BORDER); colors.append(INK)
        f.text(PAD, t + 82, "needle", T_CHIP, MUTED)
        nb = row(f, x0, t + 56, cw, 54, needle, gap=gap, size=T_CELL,
                 fills=fills, strokes=strokes, colors=colors)
        index_labels(f, nb, t + 130)
        f.text(PAD, t + 202, "lps", T_CHIP, MUTED)
        values = [str(lps[k]) if k in filled else "." for k in range(len(needle))]
        row(f, x0, t + 176, cw, 54, values, gap=gap, size=T_CELL - 1,
            fills=[CREAM if k == i else GREY for k in range(len(needle))],
            strokes=[BRASS if k == i else BORDER for k in range(len(needle))],
            colors=[INK if k in filled else MUTED for k in range(len(needle))])
        pointer_down(f, row_center(nb, i)[0], t + 54, "i", RUST, gap=22)
        if kind == "match" and compared < len(needle):
            f.text(row_center(nb, compared)[0], t + 138, "length", T_CHIP, BRASS, mono=True,
                   anchor="middle", bold=True)
        return f

    publish("ch03-kmp-lps.gif", frames(make, trace), [2300] * len(trace))


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
    cw, gap = 54, 8
    x0 = (W - (len(haystack) * cw + (len(haystack) - 1) * gap)) / 2.0

    def make(step, height=None, insight_rows=0):
        left, right, kind, compared, line = step
        last = step is trace[-1]
        start = right - left + 1 if kind in ("match", "found") else right - left
        start = max(start, 0)
        f = Frame(
            "KMP search: reuse the characters that already matched",
            sub="right only ever moves forward. On a mismatch, left falls back instead.",
            diagram=290,
            legend=[("matched so far", GREEN, TEAL), ("the character under right", PINK, RUST)],
            step=line,
            note="Green is one run of characters that matched, reused rather than re-read.",
            pairs=[("left", left, TEAL), ("right", right, RUST), ("start", start, INK)],
            insight=("right never moves backwards, so each character of the text is read once."
                     ) if last else None,
            height=height, insight_rows=insight_rows,
        )
        t = f.top
        hy = t + 52
        f.text(PAD, hy + 30, "text", T_CHIP, MUTED)
        hb = row(f, x0, hy, cw, 52, list(haystack), gap=gap, size=T_CELL - 1,
                 fills=[GREEN if start <= k <= right else PALE for k in range(len(haystack))],
                 strokes=[BORDER] * len(haystack))
        index_labels(f, hb, hy + 74)
        if 0 <= right < len(haystack):
            f.cell(x0 + right * (cw + gap), hy, cw, 52, haystack[right], PINK, RUST,
                   size=T_CELL - 1, color=WHITE)
        pointer_down(f, x0 + right * (cw + gap) + cw / 2, hy - 2, "right", RUST, gap=22)

        ny = t + 168
        f.text(PAD, ny + 30, "needle", T_CHIP, MUTED)
        for k, ch in enumerate(needle):
            x = x0 + (start + k) * (cw + gap)
            if x + cw > W - PAD:
                continue
            matched = k < left and (start + k) <= right
            here = k == compared
            f.cell(x, ny, cw, 52, ch,
                   PINK if here else (GREEN if matched else PALE),
                   RUST if here else (TEAL if matched else BORDER),
                   size=T_CELL - 1, color=WHITE if here else INK)
        if kind == "found":
            f.glow(x0 + start * (cw + gap) + 3 * (cw + gap), ny + 26, 96, TEAL, 0.42)
        return f

    publish("ch03-kmp-search.gif", frames(make, trace), [2200] * len(trace))


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
        child_value, parent_value = heap[i], heap[parent]
        heap[i], heap[parent] = heap[parent], heap[i]
        steps.append((heap[:], [parent, i], TEAL, "climb",
                      "%d is greater than its parent %d, so they swap and %d climbs to index %d."
                      % (child_value, parent_value, child_value, parent)))
        i = parent
    steps.append((heap[:], [], GREEN, "climb",
                  "Index 0 has no parent, so the climb stops. Every parent is at least as large as its children again."))
    root, last_value = heap[0], heap.pop()
    heap[0] = last_value
    steps.append((heap[:], [0], RUST, "sink",
                  "pop() returns the root, %d. The last value, %d, moves to the root and then sinks."
                  % (root, last_value)))
    i = 0
    while True:
        children = [c for c in (2 * i + 1, 2 * i + 2) if c < len(heap)]
        big = max(children, key=lambda c: heap[c]) if children else i
        if not children or heap[big] <= heap[i]:
            break
        child_value, here = heap[big], heap[i]
        heap[i], heap[big] = heap[big], heap[i]
        steps.append((heap[:], [i, big], RUST, "sink",
                      "The larger child is %d at index %d, above %d at index %d, so they swap."
                      % (child_value, big, here, i)))
        i = big
    steps.append((heap[:], [], GREEN, "sink",
                  "Neither child is larger, so the sink stops and the heap is valid again."))

    def make(step, height=None, insight_rows=0):
        values, hot, accent, phase, line = step
        last = step is steps[-1]
        f = Frame(
            "Heap push and pop: a new value climbs, the last value sinks",
            sub="A max-heap in an array. The children of i are 2i+1 and 2i+2; the parent is (i-1)/2.",
            diagram=340,
            legend=[("on the move", CREAM, BRASS), ("in place", PALE, BORDER)],
            step=line,
            note="The tree is the array: no links and no allocation, and the parent of i is one division away.",
            pairs=[("phase", phase, RUST), ("index 0", values[0], TEAL), ("size", len(values), INK)],
            insight=("A heap of n values is log n levels deep, so a climb or a sink costs "
                     "log n.") if last else None,
            height=height, insight_rows=insight_rows,
        )
        t = f.top
        fills = [CREAM if k in hot else PALE for k in range(len(values))]
        strokes = [accent if k in hot else BORDER for k in range(len(values))]
        boxes = row(f, PAD, t + 10, 62, 50, values, gap=8, size=T_CELL - 1, fills=fills,
                    strokes=strokes)
        index_labels(f, boxes, t + 78)
        if hot:
            f.glow(row_center(boxes, min(hot))[0], t + 35, 60, accent, 0.35)
        f.text(PAD, t + 118, "the same values as a tree", T_CHIP, MUTED)
        heap_tree(f, values, base_x=420, top=t + 156, dy=64, spacing=220,
                  fills=fills, strokes=strokes)
        return f

    publish("ch05-heap-sift.gif", frames(make, steps), [2200] * len(steps))


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
    k = 2
    heap = []

    def times(n):
        return "once" if n == 1 else "%d times" % n

    steps = [(list(heap), None, "start",
              "Count each number first, then keep a min-heap of size k over the counts, so the root is the weakest entry still kept.")]
    for value, count in counts:
        if len(heap) < k:
            heap.append((value, count))
            heap.sort(key=lambda e: e[1])
            steps.append((list(heap), (value, count), "push",
                          "%d appears %s and the heap has room, so it goes in." % (value, times(count))))
        elif count > heap[0][1]:
            out = heap[0]
            heap[0] = (value, count)
            heap.sort(key=lambda e: e[1])
            steps.append((list(heap), (value, count), "replace",
                          "%d appears %s, more than the smallest count kept, %d, so %d is dropped."
                          % (value, times(count), out[1], out[0])))
        else:
            steps.append((list(heap), (value, count), "skip",
                          "%d appears %s, no more than the smallest count kept, %d, so it is ignored."
                          % (value, times(count), heap[0][1])))
    steps.append((list(heap), None, "done",
                  "Every number has been counted once. The heap holds the %d values with the largest counts." % k))

    cw, gap = 84, 8
    cx0 = (W - (len(counts) * cw + (len(counts) - 1) * gap)) / 2.0

    def make(step, height=None, insight_rows=0):
        values, arriving, kind, line = step
        last = step is steps[-1]
        f = Frame(
            "The k most frequent values: a heap of size k, never bigger",
            sub="The heap stores k entries, so its cost does not grow with the input.",
            diagram=290,
            legend=[("kept", GREEN, TEAL), ("just arrived", CREAM, BRASS), ("ignored", GREY, BORDER)],
            step=line,
            note="The root of a min-heap is the weakest entry kept, so a new count is compared with it alone.",
            pairs=[("arriving", "%d : %d" % arriving if arriving else "-", BRASS),
                   ("kept", len(values), TEAL), ("k", k, INK)],
            insight=("The heap holds k entries, so each new count costs log k, never a full "
                     "sort.") if last else None,
            height=height, insight_rows=insight_rows,
        )
        t = f.top
        f.text(PAD, t + 22, "counts", T_CHIP, MUTED)
        row(f, cx0, t + 32, cw, 56, ["%d : %d" % c for c in counts], gap=gap, size=T_CELL - 1,
            fills=[CREAM if arriving and c == arriving else PALE for c in counts],
            strokes=[BRASS if arriving and c == arriving else BORDER for c in counts])
        f.text(PAD, t + 126, "the best k, as a min-heap", T_CHIP, MUTED)
        if values:
            hb = row(f, cx0, t + 138, cw, 56, ["%d : %d" % e for e in values], gap=gap,
                     size=T_CELL - 1, fills=[GREEN] * len(values), strokes=[TEAL] * len(values))
            f.text(row_center(hb, 0)[0], t + 216, "root: the smallest count kept", T_CHIP, TEAL,
                   anchor="middle", bold=True)
        else:
            f.rect(cx0, t + 138, cw, 56, WHITE, BORDER, 6, dash=True)
            f.text(cx0 + cw / 2, t + 172, "empty", T_CHIP, MUTED, anchor="middle")
        return f

    publish("ch05-top-k.gif", frames(make, steps), [2200] * len(steps))


# -------------------------------------------------- Coin change DP (6.1)

def coin_change():
    """Fill dp[0] to dp[amount] from the coins."""
    coins, amount = [1, 2, 5], 11
    dp = [None] * (amount + 1)
    dp[0] = 0
    trace = [(0, 0, None, dp[:], ["dp[0] = 0. Zero coins make zero, whatever the coins are."])]
    for t_ in range(1, amount + 1):
        best, src, options = None, None, []
        for c in coins:
            if c <= t_ and dp[t_ - c] is not None:
                options.append((c, dp[t_ - c] + 1))
                if best is None or dp[t_ - c] + 1 < best:
                    best, src = dp[t_ - c] + 1, t_ - c
        dp[t_] = best
        trace.append((t_, best, src, dp[:],
                      ["dp[%d] reads %s." % (t_, ", ".join("dp[%d] + 1 = %d" % (t_ - c, v)
                                                          for c, v in options)),
                       "The smallest is %d, so dp[%d] = %d." % (best, t_, best)]))

    cw, gap = 58, 6
    x0 = (W - ((amount + 1) * cw + amount * gap)) / 2.0

    def make(step, height=None, insight_rows=0):
        t_, best, src, snapshot, lines = step
        last = step is trace[-1]
        f = Frame(
            "Coin change: the fewest coins for every amount up to 11",
            sub="dp[t] is the smallest of dp[t - coin] + 1 over the coins 1, 2, and 5.",
            diagram=250,
            legend=[("being filled", PINK, RUST), ("read by it", CREAM, TEAL),
                    ("not reachable", GREY, BORDER)],
            step=" ".join(lines),
            note="A dot means the amount cannot be made from the coins, so no rule reaches it yet.",
            pairs=[("t", t_, RUST), ("dp[t]", best if best is not None else "-", TEAL),
                   ("coins", " ".join(str(c) for c in coins), INK)],
            insight=("dp[t] reads only entries below t, so the table fills left to right, once."
                     ) if last else None,
            height=height, insight_rows=insight_rows,
        )
        t2 = f.top
        values = [str(snapshot[k]) if snapshot[k] is not None else "." for k in range(amount + 1)]
        sources = ({t_ - c for c in coins if c <= t_ and snapshot[t_ - c] is not None}
                   if last else {src})
        fills, strokes, colors = [], [], []
        for k in range(amount + 1):
            if k == t_:
                fills.append(PINK); strokes.append(RUST); colors.append(WHITE)
            elif k in sources and snapshot[k] is not None:
                fills.append(CREAM); strokes.append(TEAL); colors.append(INK)
            elif snapshot[k] is None:
                fills.append(GREY); strokes.append(BORDER); colors.append(MUTED)
            else:
                fills.append(PALE); strokes.append(BORDER); colors.append(INK)
        boxes = row(f, x0, t2 + 60, cw, 56, values, gap=gap, size=T_CELL - 2,
                    fills=fills, strokes=strokes, colors=colors)
        index_labels(f, boxes, t2 + 136)
        f.text(row_center(boxes, t_)[0], t2 + 38, "t", T_CHIP, RUST, anchor="middle", bold=True)
        for k in sorted(x for x in sources if x is not None):
            if 0 <= k < len(boxes) and k != t_:
                f.line(row_center(boxes, k)[0], t2 + 46, row_center(boxes, k)[0], t2 + 52,
                       TEAL, 1.6)
                f.arrow(row_center(boxes, k)[0], t2 + 50, row_center(boxes, t_)[0], t2 + 50,
                        TEAL, 1.4, head=7)
        f.text(PAD, t2 + 196, "dp", T_CHIP, MUTED)
        return f

    publish("ch06-coin-change.gif", frames(make, trace), [2100] * len(trace))


# -------------------------------------------------------- Subsets (6.2)

def subsets():
    """Every path down the choice tree is one subset."""
    nums = [1, 2, 3]
    records, result = [], []

    def backtrack(start, path):
        result.append(list(path))
        records.append((list(path), start))
        for idx in range(start, len(nums)):
            path.append(nums[idx])
            backtrack(idx + 1, path)
            path.pop()

    backtrack(0, [])
    nodes = [(), (1,), (2,), (3,), (1, 2), (1, 3), (2, 3), (1, 2, 3)]
    pos = {(): (410, 26), (1,): (220, 108), (2,): (410, 108), (3,): (600, 108),
           (1, 2): (150, 190), (1, 3): (300, 190), (2, 3): (410, 190),
           (1, 2, 3): (150, 272)}
    edges = [((), (1,)), ((), (2,)), ((), (3,)), ((1,), (1, 2)), ((1,), (1, 3)),
             ((2,), (2, 3)), ((1, 2), (1, 2, 3))]

    def label(node):
        return "{}" if not node else "{%s}" % ",".join(str(v) for v in node)

    def make(step, height=None, insight_rows=0):
        path, start = step
        index = records.index(step)
        last = step is records[-1]
        cur = tuple(path)
        f = Frame(
            "Subsets: every path down the tree is one subset",
            sub="Each call records the path so far, then tries every larger index.",
            diagram=330,
            legend=[("the path now", CREAM, BRASS), ("its prefixes", GREEN, TEAL),
                    ("off the path", PALE, BORDER)],
            step="The call reaches %s and records it, then tries each index from %d upward."
                 % (label(cur), start),
            note="Backtracking pops the value it added, so one path buffer serves the whole tree.",
            pairs=[("path", label(cur), BRASS), ("start", start, INK),
                   ("recorded", index + 1, TEAL)],
            insight=("Every node of the tree is one subset, and a tree of n choices has 2^n "
                     "nodes.") if last else None,
            height=height, insight_rows=insight_rows,
        )
        t = f.top
        local = {k: (x, y + t) for k, (x, y) in pos.items()}
        for a, b in edges:
            ax, ay = local[a][0], local[a][1] + 20
            bx, by = local[b][0], local[b][1] - 20
            on = cur[:len(a)] == a and cur[:len(b)] == b
            f.line(ax, ay, bx, by, TEAL if on else BORDER, 2.6 if on else 1.6)
        for key in nodes:
            x, y = local[key]
            prefix = tuple(key) == cur[:len(key)]
            f.cell(x - 56, y - 20, 112, 40, label(key),
                   CREAM if key == cur else (GREEN if prefix else PALE),
                   BRASS if key == cur else (TEAL if prefix else BORDER),
                   size=T_CHIP + 2, mono=True)
        f.text(PAD, t + 308, "recorded: %s" % "  ".join(label(tuple(r)) for r in result[:index + 1]),
               T_CHIP, MUTED, mono=True)
        return f

    publish("ch06-subsets.gif", frames(make, records), [2100] * len(records))


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
