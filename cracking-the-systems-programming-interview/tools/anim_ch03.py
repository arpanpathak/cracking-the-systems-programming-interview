"""The chapter 3 animations (ch03-collections.md), drawn with `motion`.

Each builder runs the chapter's algorithm on the chapter's input and records one
step per thing the reader should see. `motion_kit.play` turns the steps into a
timeline, and the draw function paints one frame from the state.

    python3 tools/animations.py two-sum
"""

from motion import (BRASS, BRASS_LT, FAINT, INK, LINE, MUTED, PAPER, RUST, RUST_LT, TEAL,
                    TEAL_LT, W, caption, code_panel, progress, render, scoreboard, title_block)
from motion_kit import (NAVY, cells, fact, kv_panel, layout, line_of, play, pointer, row_xs,
                        source, stack_panel)


def frame_furniture(p, tl, t, total, title, sub, code_title, code, line, caption_y, rail_y,
                    code_y, code_size=11.0, lead=16.0, tint=TEAL, strike=-1.0):
    title_block(p, title, sub)
    code_panel(p, 26, code_y, W - 52, code_title, code, line, size=code_size, lead=lead,
               tint=RUST if strike >= 0 else tint, reveal=tl.reached("code", t),
               strike=int(strike) if strike >= 0 else None)
    caption(p, tl, t, caption_y)
    progress(p, tl, t, total, rail_y)


# ------------------------------------------------------------------ two sum


def two_sum():
    nums, target = [2, 7, 11, 15], 9
    code = source("src/problems/two_sum.rs", "pub fn two_sum", "}")
    get = line_of(code, "seen.get")
    hit = line_of(code, "Some(&prev)")
    ins = line_of(code, "seen.insert")
    loop = line_of(code, "for (idx")

    steps = [dict(say="The input is 2, 7, 11, 15, and the target is 9. seen is an "
                  "empty map from a number to its index.", code=0.0)]
    seen = []
    for idx, num in enumerate(nums):
        need = target - num
        steps.append(dict(chapter="index %d" % idx if idx < 2 else None,
                          say="idx = %d, so num = %d. Its partner is target - num = %d." % (idx, num, need),
                          i=float(idx), i_a=1.0, need=str(need), code=float(loop), hot="", miss="",
                          done=""))
        steps.append(dict(say="seen.get(&%d) looks for the partner among the numbers already passed."
                          % need, code=float(get)))
        found = dict(seen)
        if need in found:
            steps.append(dict(say="seen holds %d at index %d, so get returns Some(&%d)." % (
                need, found[need], found[need]), hot=str(need), code=float(hit), kind="step"))
            steps.append(dict(say="The function returns Some((%d, %d)). It read %d of the %d numbers."
                              % (found[need], idx, idx + 1, len(nums)),
                              done="%d,%d" % (found[need], idx), kind="insight", hold=2.0))
            break
        steps.append(dict(say="seen has no %d yet, so get returns None." % need, miss=str(need)))
        seen.append((num, idx))
        steps.append(dict(say="The None arm stores %d -> %d, so a later number can find it." % (num, idx),
                          entries=list(seen), miss="", code=float(ins)))
    steps = [{k: v for k, v in s.items() if v is not None} for s in steps]

    # The failing case: the same function with the insert moved above the lookup.
    steps += [
        dict(chapter="insert first", say="Now target 4 and the array [2], with the insert moved "
             "above the lookup.", kind="fail", nums="2", target=4, entries=[], i=0.0, i_a=1.0,
             need="", hot="", miss="", done="", code=-1.0, swapped=True),
        dict(say="The insert runs first and stores 2 -> 0.", kind="fail", entries=[(2, 0)],
             code=float(get)),
        dict(say="Then the lookup asks for 4 - 2 = 2, and finds the 2 it has just stored.",
             kind="fail", need="2", hot="2", code=float(get + 1)),
        dict(say="The result pairs index 0 with itself. Looking up first, as the listing does, "
             "prevents it.", kind="fail", done="0,0", hold=2.4),
    ]
    tl = play(steps, dict(code=-1.0, i=0.0, i_a=0.0, need="", entries=[], hot="", miss="", done="",
                          nums="2,7,11,15", target=9, swapped=False))

    def draw(p, s, total):
        t = s.t
        values = [int(v) for v in s.nums.split(",")]
        xs = row_xs(len(values), 64, 14, cx=270)
        top = 150
        pair = [int(v) for v in s.done.split(",")] if s.done else []
        fills, edges, inks = [], [], []
        for k in range(len(values)):
            if k in pair:
                fills.append(TEAL_LT); edges.append(TEAL); inks.append(INK)
            elif s.i_a > 0.5 and k < s.i - 0.01:
                fills.append("#f3f5f7"); edges.append(LINE); inks.append(MUTED)
            elif s.i_a > 0.5 and abs(k - s.i) < 0.5:
                fills.append(BRASS_LT); edges.append(BRASS); inks.append(INK)
            else:
                fills.append(PAPER); edges.append(LINE); inks.append(INK)
        bottom = cells(p, xs, top, values, cell=64, fills=fills, edges=edges, inks=inks, size=24)
        p.text(xs[0] - 50, top + 39, "nums", 13, MUTED, 600, "end", mono=True)
        x_i = xs[0] + s.i * (xs[1] - xs[0]) if len(xs) > 1 else xs[0]
        pointer(p, x_i, top, "idx", BRASS, "above", opacity=s.i_a)
        if s.i_a > 0.5 and s.need:
            fact(p, 70, bottom + 34, "partner = target - num =", s.need, BRASS, 17)
        if len(pair) == 2:
            p.text(270, bottom + 66, "Some((%d, %d))" % tuple(pair), 18,
                   RUST if pair[0] == pair[1] else TEAL, 700, "middle", mono=True)

        kv_panel(p, tl, t, 520, 96, 274, "seen: HashMap<i32, usize>", s.entries, "entries",
                 hot=s.hot or None, miss=s.miss or None, rows=4)
        scoreboard(p, [("target", s.target, RUST)])

        shown = list(code)
        if s.swapped:
            shown = [l for k, l in enumerate(code) if k not in (ins,)]
            shown.insert(get, "        seen.insert(num, idx);  // moved up")
        frame_furniture(p, tl, t, total, "Two Sum: one pass with a map",
                        "For each number, look up the partner it needs among the numbers already passed.",
                        "two_sum", shown, s.code, cap_y, rail_y, CODE_Y, code_size=11.2,
                        lead=15.6, tint=RUST if s.swapped else TEAL)

    CODE_Y = 312
    cap_y, rail_y, height = layout(CODE_Y, len(code))
    return tl, draw, height


def build_two_sum(only=None):
    tl, draw, height = two_sum()
    return render("ch03-two-sum.gif", tl, draw, height, only=only)


# ------------------------------------------------------------------ brackets


def brackets():
    code = source("src/problems/valid_parentheses.rs", "pub fn is_valid", "}")
    push = line_of(code, "stack.push(ch)")
    pop_line = line_of(code, "stack.pop()")
    bad = line_of(code, "return false")
    end = line_of(code, "stack.is_empty()")
    pairs = {")": "(", "]": "[", "}": "{"}

    def run(text, label, fail=False):
        kind = "step"
        out = [dict(chapter=label, say="The input is \"%s\". The stack starts empty." % text,
                    text=text, i=-1.0, stack=[], verdict="", top_ok="", code=-1.0, kind=kind)]
        stack = []
        for k, ch in enumerate(text):
            if ch in "([{":
                stack.append(ch)
                out.append(dict(say="'%s' is an opener, so it is pushed." % ch, i=float(k),
                                stack=list(stack), top_ok="", code=float(push), kind="step"))
            else:
                top = stack.pop() if stack else None
                want = pairs[ch]
                if top == want:
                    out.append(dict(say="'%s' is a closer. pop returns '%s', and '%s' expects '%s'. They match."
                                    % (ch, top, ch, want), i=float(k), top_ok="yes",
                                    code=float(pop_line), kind="step"))
                    out.append(dict(say="The matched opener is gone from the stack.", stack=list(stack),
                                    top_ok="", kind="step", hold=0.2))
                else:
                    out.append(dict(say="'%s' is a closer. pop returns '%s', but '%s' expects '%s'."
                                    % (ch, top, ch, want), i=float(k), top_ok="no",
                                    code=float(pop_line), kind="step"))
                    out.append(dict(say="The two differ, so is_valid returns false: '%s' closed a bracket "
                                    "that was not the most recent one opened." % ch,
                                    verdict="false", code=float(bad), kind="fail", hold=2.2))
                    return out
        out.append(dict(say="The input is used up and the stack is empty, so is_valid returns true.",
                        i=float(len(text)), verdict="true", code=float(end), kind="insight", hold=1.8))
        return out

    steps = run("([{}])", "([{}])") + run("([)]", "([)]", fail=True)
    tl = play(steps, dict(text="([{}])", i=-1.0, stack=[], verdict="", top_ok="", code=-1.0))

    def draw(p, s, total):
        t = s.t
        xs = row_xs(len(s.text), 58, 12, cx=270)
        top = 150
        fills, edges = [], []
        for k in range(len(s.text)):
            if abs(k - s.i) < 0.5:
                fills.append(BRASS_LT); edges.append(BRASS)
            elif k < s.i:
                fills.append("#f3f5f7"); edges.append(LINE)
            else:
                fills.append(PAPER); edges.append(LINE)
        cells(p, xs, top, list(s.text), cell=58, fills=fills, edges=edges, size=26)
        p.text(xs[0] - 46, top + 36, "s", 14, MUTED, 600, "end", mono=True)
        if 0 <= s.i < len(s.text):
            x = xs[0] + s.i * (xs[1] - xs[0])
            pointer(p, x, top, "ch", BRASS, "above")
        if s.verdict:
            ok = s.verdict == "true"
            p.text(270, top + 128, "is_valid -> %s" % s.verdict, 18, TEAL if ok else RUST, 700,
                   "middle", mono=True)
        stack_panel(p, tl, t, 560, 84, 200, "stack: Vec<char>", s.stack, "stack", rows=4,
                    hot_top=s.top_ok == "yes", bad_top=s.top_ok == "no")
        frame_furniture(p, tl, t, total, "Checking brackets with a stack",
                        "An opener is pushed. A closer pops the top, which must be its partner.",
                        "is_valid", code, s.code, cap_y, rail_y, CODE_Y)

    CODE_Y = 318
    cap_y, rail_y, height = layout(CODE_Y, len(code))
    return tl, draw, height


# ---------------------------------------------------------------- three sum


def three_sum():
    nums = [-4, -1, -1, 0, 1, 2]
    target = 0
    code = source("src/problems/three_sum.rs", "for i in 0..numbers.len()", "results.push")
    skip = line_of(code, "continue")
    init = line_of(code, "let (mut left")
    less = line_of(code, "Less =>")
    more = line_of(code, "Greater =>")
    push = line_of(code, "results.push")

    steps = [dict(say="The sorted array is -4, -1, -1, 0, 1, 2, and the target is 0. i fixes the "
                  "first number.", code=-1.0)]
    results = []
    for i in range(len(nums)):
        if i > 0 and nums[i] == nums[i - 1]:
            steps.append(dict(chapter="skip", say="numbers[%d] = %d equals the number before it, so i = %d "
                              "is skipped. Its triples were already found." % (i, nums[i], i),
                              i=float(i), i_a=1.0, l_a=0.0, r_a=0.0, sum="", code=float(skip)))
            continue
        left, right = i + 1, len(nums) - 1
        if left >= right:
            break
        steps.append(dict(chapter="i = %d" % i, say="i = %d fixes %d. left starts after it, and right "
                          "starts at the end." % (i, nums[i]), i=float(i), i_a=1.0, left=float(left),
                          right=float(right), l_a=1.0, r_a=1.0, sum="", code=float(init)))
        while left < right:
            total = nums[i] + nums[left] + nums[right]
            expr = "%d + %d + %d = %d" % (nums[i], nums[left], nums[right], total)
            if total < target:
                left += 1
                steps.append(dict(say="%s is too small. Moving left right is the only way to raise it."
                                  % expr, sum=expr, code=float(less), left=float(left)))
            elif total > target:
                right -= 1
                steps.append(dict(say="%s is too large. Moving right left is the only way to lower it."
                                  % expr, sum=expr, code=float(more), right=float(right)))
            else:
                results.append("(%d, %d, %d)" % (nums[i], nums[left], nums[right]))
                steps.append(dict(say="%s matches the target, so the triple is recorded." % expr, sum=expr,
                                  results=list(results), code=float(push), kind="insight"))
                while left < right and nums[left] == nums[left + 1]:
                    left += 1
                while left < right and nums[right] == nums[right - 1]:
                    right -= 1
                left += 1
                right -= 1
                steps.append(dict(say="Both pointers step past equal values, then move inward once.",
                                  left=float(left), right=float(right), sum=""))
    steps.append(dict(say="Two triples, found with one inward walk for each fixed number: O(n^2).",
                      kind="insight", i_a=0.0, l_a=0.0, r_a=0.0, sum="", code=-1.0, hold=2.0))
    dup_test = line_of(code, "numbers[i] == numbers[i - 1]")
    steps.append(dict(chapter="no skip", say="Now take out the check that skips a repeated first number. "
                      "i = 2 holds the second -1.", kind="fail", strike=float(dup_test), i=2.0, i_a=1.0,
                      left=3.0, right=5.0, l_a=1.0, r_a=1.0, sum="", code=float(init)))
    steps.append(dict(say="-1 + 0 + 2 = 1 is too large, so right moves left.", kind="fail",
                      sum="-1 + 0 + 2 = 1", right=4.0, code=float(more)))
    steps.append(dict(say="-1 + 0 + 1 = 0 matches, so the triple is recorded again.", kind="fail",
                      sum="-1 + 0 + 1 = 0", results=list(results) + ["(-1, 0, 1)"], code=float(push)))
    steps.append(dict(say="(-1, 0, 1) appears twice. The two -1s are different indices, but the triple is "
                      "the same, so the answer is wrong.", kind="fail", i_a=0.0, l_a=0.0, r_a=0.0,
                      sum="", code=-1.0, hold=2.2))
    steps = [{k: v for k, v in st.items() if v is not None} for st in steps]
    for st in steps:
        if st.get("chapter") == "skip":
            st.pop("chapter")
    tl = play(steps, dict(code=-1.0, i=0.0, i_a=0.0, left=1.0, right=5.0, l_a=0.0, r_a=0.0, sum="",
                          results=[], strike=-1.0))

    def draw(p, s, total):
        t = s.t
        xs = row_xs(len(nums), 62, 14, cx=W / 2)
        top = 140
        span_lo = s.left if s.l_a > 0.5 else 99
        span_hi = s.right if s.r_a > 0.5 else -1
        fills, edges = [], []
        for k in range(len(nums)):
            if s.i_a > 0.5 and abs(k - s.i) < 0.5:
                fills.append(BRASS_LT); edges.append(BRASS)
            elif span_lo - 0.5 <= k <= span_hi + 0.5:
                fills.append(PAPER); edges.append(NAVY)
            else:
                fills.append("#f3f5f7"); edges.append(LINE)
        below = cells(p, xs, top, nums, cell=62, fills=fills, edges=edges, size=22)
        step = xs[1] - xs[0]
        pointer(p, xs[0] + s.i * step, top, "i", BRASS, "above", opacity=s.i_a)
        same = abs(s.left - s.right) < 0.5
        pointer(p, xs[0] + s.left * step, below, "left", NAVY, "below", opacity=s.l_a)
        pointer(p, xs[0] + s.right * step, below, "right", RUST, "below", slot=1 if same else 0,
                opacity=s.r_a)
        if s.sum:
            p.text(W / 2, 92, s.sum, 17, INK, 700, "middle", mono=True)
        p.text(W - 40, 236, "results", 12, MUTED, 600, "end")
        for k, r in enumerate(s.results):
            again = r in s.results[:k]
            p.text(W - 40, 260 + k * 22, r + ("  again" if again else ""), 15,
                   RUST if again else TEAL, 700, "end", mono=True)
        frame_furniture(p, tl, t, total, "Three Sum: fix one number, close two pointers",
                        "The array is sorted, so the sum says which pointer to move.",
                        "three_sum (the search loop)", code, s.code, cap_y, rail_y, CODE_Y,
                        code_size=10.6, lead=15.0, strike=s.strike)

    CODE_Y = 364
    cap_y, rail_y, height = layout(CODE_Y, len(code), 15.0)
    return tl, draw, height


# ----------------------------------------------------------- sliding window


def window():
    code = source("src/problems/sliding_window.rs", "pub fn length_of_longest_substring", "}")
    get = line_of(code, "if let Some(&previous)")
    move = line_of(code, "start = start.max")
    grow = line_of(code, "longest = longest.max")
    ins = line_of(code, "last_seen.insert")

    def run(text, label, fail=False):
        kind = "step"
        out = [dict(chapter=label, say="The input is \"%s\". start and longest begin at 0, and last_seen "
                    "is empty." % text, text=text, start=0.0, end=0.0, e_a=0.0, longest=0, entries=[],
                    hot="", code=-1.0, kind=kind, wrong=-1.0)]
        last, start, longest = {}, 0, 0
        for end, ch in enumerate(text):
            group = []
            if ch in last:
                prev = last[ch]
                new_start = max(start, prev + 1)
                group.append(dict(say="end = %d reads '%s'." % (end, ch), end=float(end), e_a=1.0,
                                  hot="", code=float(get)))
                if fail and new_start == start:
                    group.append(dict(say="'%s' was last seen at %d, before the window starts at %d."
                                      % (ch, prev, start), hot=ch))
                    group.append(dict(say="Without max, start would move back to %d, and the window "
                                      "would hold two '%s's again." % (prev + 1, text[start]),
                                      wrong=float(prev + 1), code=float(move), kind="fail", hold=1.4))
                    group.append(dict(say="With max, start stays at %d." % start, wrong=-1.0))
                else:
                    group.append(dict(say="'%s' was last seen at %d, inside the window, so start moves "
                                      "to %d." % (ch, prev, new_start), hot=ch, start=float(new_start),
                                      code=float(move)))
                start = new_start
            else:
                group.append(dict(say="end = %d reads '%s', which is not in last_seen." % (end, ch),
                                  end=float(end), e_a=1.0, hot="", code=float(get)))
            if end - start + 1 > longest:
                longest = end - start + 1
                group.append(dict(say="The window \"%s\" has length %d, the longest so far." % (
                    text[start:end + 1], longest), longest=longest, code=float(grow)))
            last[ch] = end
            group[-1]["entries"] = sorted(last.items(), key=lambda kv: text.index(kv[0]))
            for st in group:
                st.setdefault("kind", kind)
            out += group
        out.append(dict(say="The function returns %d. end visited each character once, and start only "
                        "moved forward." % longest, e_a=0.0, code=-1.0,
                        kind="insight", hold=1.8))
        return out

    steps = run("pwwkew", "pwwkew") + run("abba", "abba", fail=True)
    tl = play(steps, dict(text="pwwkew", start=0.0, end=0.0, e_a=0.0, longest=0, entries=[], hot="",
                          code=-1.0, wrong=-1.0))

    def draw(p, s, total):
        t = s.t
        xs = row_xs(len(s.text), 58, 12, cx=260)
        top = 150
        step = xs[1] - xs[0]
        fills, edges = [], []
        for k in range(len(s.text)):
            inside = s.e_a > 0.5 and s.start - 0.01 <= k <= s.end + 0.01
            if inside and abs(k - s.end) < 0.5:
                fills.append(BRASS_LT); edges.append(BRASS)
            elif inside:
                fills.append(TEAL_LT); edges.append(TEAL)
            else:
                fills.append(PAPER); edges.append(LINE)
        below = cells(p, xs, top, list(s.text), cell=58, fills=fills, edges=edges, size=24)
        if s.e_a > 0.01:
            x0 = xs[0] + s.start * step - 29
            x1 = xs[0] + s.end * step + 29
            p.rect(x0 - 5, top - 5, x1 - x0 + 10, 68, "none", TEAL, 12, 2.4, opacity=s.e_a)
        pointer(p, xs[0] + s.end * step, top, "end", BRASS, "above", opacity=s.e_a)
        pointer(p, xs[0] + s.start * step, below, "start", TEAL, "below", opacity=s.e_a)
        if s.wrong >= 0:
            pointer(p, xs[0] + s.wrong * step, below, "start without max", RUST, "below", slot=1)
        fact(p, 70, 330, "longest =", s.longest, TEAL, 18)
        kv_panel(p, tl, t, 560, 84, 234, "last_seen: HashMap<char, usize>", s.entries, "entries",
                 hot=s.hot or None, rows=4)
        frame_furniture(p, tl, t, total, "Sliding window: the longest run with no repeat",
                        "end moves one character at a time. start moves only when a repeat arrives.",
                        "length_of_longest_substring", code, s.code, cap_y, rail_y, CODE_Y)

    CODE_Y = 352
    cap_y, rail_y, height = layout(CODE_Y, len(code))
    return tl, draw, height


# ---------------------------------------------------------- merge intervals


def merge_intervals():
    raw = [(8, 10), (1, 3), (15, 18), (2, 6)]
    code = source("src/problems/merge_intervals.rs", "pub fn merge_intervals(", "}")
    sort = line_of(code, "sort_unstable_by_key")
    loop = line_of(code, "for Interval")
    ext = line_of(code, "previous.end = previous.end.max")
    push = line_of(code, "merged.push")
    order = sorted(range(len(raw)), key=lambda k: raw[k][0])
    defaults = dict(code=-1.0, cur=-1.0, merged=[], grow=0.0, sorted_a=0.0)
    for k in range(len(raw)):
        defaults["row%d" % k] = float(k)
    steps = [dict(chapter="sort", say="The input ranges arrive unsorted: [8,10] [1,3] [15,18] [2,6].")]
    st = dict(say="sort_unstable_by_key orders them by start. A range can now overlap only the "
              "range just before it.", code=float(sort), sorted_a=1.0, dur=1.4)
    for rank, k in enumerate(order):
        st["row%d" % k] = float(rank)
    steps.append(st)
    merged = []
    for rank, k in enumerate(order):
        start, end = raw[k]
        if merged and start <= merged[-1][1]:
            prev = list(merged[-1])
            steps.append(dict(chapter="walk" if rank == 0 else None, say="[%d,%d] starts at %d, which is not after the last merged end, %d. "
                              "They overlap." % (start, end, start, prev[1]), cur=float(k), code=float(loop)))
            merged[-1] = (prev[0], max(prev[1], end))
            steps.append(dict(say="previous.end becomes max(%d, %d) = %d. The merged range is now [%d,%d]."
                              % (prev[1], end, merged[-1][1], merged[-1][0], merged[-1][1]),
                              merged=[list(m) for m in merged], code=float(ext)))
        else:
            why = ("merged is empty" if not merged else
                   "%d is after the last merged end, %d" % (start, merged[-1][1]))
            steps.append(dict(chapter="walk" if rank == 0 else None,
                              say="[%d,%d]: %s, so it starts a new merged range." % (start, end, why),
                              cur=float(k), code=float(loop)))
            merged.append((start, end))
            steps.append(dict(say="merged.push adds [%d,%d]." % (start, end),
                              merged=[list(m) for m in merged], code=float(push)))
    steps.append(dict(say="The result is [1,6] [8,10] [15,18]: one sort and one walk, O(n log n).",
                      cur=-1.0, code=-1.0, kind="insight", hold=1.6))
    steps.append(dict(chapter="no sort", say="Without the sort, the walk would meet [8,10] first and "
                      "[2,6] last.", kind="fail", sorted_a=0.0, merged=[], cur=-1.0,
                      **{"row%d" % k: float(k) for k in range(len(raw))}))
    steps.append(dict(say="[2,6] would then be compared with [15,18] only, and [1,3] and [2,6] would "
                      "stay separate ranges.", kind="fail", hold=2.0,
                      merged=[[8, 10], [1, 3], [15, 18], [2, 6]]))
    steps = [{k: v for k, v in x.items() if v is not None} for x in steps]
    tl = play(steps, defaults)

    def draw(p, s, total):
        t = s.t
        x0, x1, lo, hi = 150, 760, 0, 20
        def X(v): return x0 + (x1 - x0) * (v - lo) / (hi - lo)
        top = 112
        p.text(26, top - 6, "intervals", 12, MUTED, 600)
        for k, (a, b) in enumerate(raw):
            y = top + 10 + s["row%d" % k] * 34
            active = abs(s.cur - k) < 0.5
            fill, edge = (BRASS_LT, BRASS) if active else (PAPER, NAVY)
            p.rect(X(a), y, X(b) - X(a), 24, fill, edge, 6, 1.8)
            p.text(X(a) - 10, y + 17, "[%d,%d]" % (a, b), 13, INK, 700, "end", mono=True)
        axis_y = top + 10 + 4 * 34 + 8
        p.line(x0, axis_y, x1, axis_y, LINE, 1.6)
        for v in range(0, 21, 2):
            p.line(X(v), axis_y, X(v), axis_y + 5, FAINT, 1.2)
            p.text(X(v), axis_y + 19, str(v), 10.5, FAINT, 400, "middle", mono=True)
        my = axis_y + 40
        p.text(26, my + 17, "merged", 12, MUTED, 600)
        for k, (a, b) in enumerate(s.merged):
            p.rect(X(a), my, X(b) - X(a), 24, TEAL_LT, TEAL, 6, 1.8)
            p.text(X(a) - 10, my + 17, "[%d,%d]" % (a, b), 13, TEAL, 700, "end", mono=True) if X(a) - 10 > 120 else None
        frame_furniture(p, tl, t, total, "Merging ranges: sort, then walk once",
                        "After sorting, each range either extends the last merged range or starts a new one.",
                        "merge_intervals", code, s.code, cap_y, rail_y, CODE_Y)

    CODE_Y = 352
    cap_y, rail_y, height = layout(CODE_Y, len(code))
    return tl, draw, height


# ------------------------------------------------------------ binary search


def binary_search():
    rule = ["while low < high {",
            "    let mid = low + (high - low) / 2;",
            "    if nums[mid] == target: found at mid",
            "    if nums[mid] <  target: low = mid + 1",
            "    if nums[mid] >  target: high = mid",
            "}",
            "// low == high: the range is empty"]

    def run(nums, target, label, fail=False):
        out = [dict(chapter=label, say="Search for %d in %s. low..high is the whole array, %d..%d."
                    % (target, ", ".join(map(str, nums)), 0, len(nums)), nums=list(nums), target=target,
                    low=0.0, high=float(len(nums)), mid=-1.0, found=-1.0, code=0.0)]
        low, high = 0, len(nums)
        while low < high:
            mid = low + (high - low) // 2
            out.append(dict(say="mid = %d + (%d - %d) / 2 = %d, which holds %d." % (low, high, low, mid, nums[mid]),
                            mid=float(mid), code=1.0))
            if nums[mid] == target:
                out.append(dict(say="nums[%d] is %d, the target. %d comparisons for %d elements."
                                % (mid, target, sum(1 for o in out if o.get("code") == 1.0), len(nums)),
                                found=float(mid), code=2.0, kind="insight", hold=1.6))
                return out
            if nums[mid] < target:
                low = mid + 1
                out.append(dict(say="%d < %d, so the target can only be to the right. low = %d."
                                % (nums[mid], target, low), low=float(low), mid=-1.0, code=3.0))
            else:
                high = mid
                out.append(dict(say="%d > %d, so the target can only be to the left. high = %d."
                                % (nums[mid], target, high), high=float(high), mid=-1.0, code=4.0))
        out.append(dict(say="low == high = %d: the range is empty, so %d is not in the array."
                        % (low, target), code=6.0, kind="fail", hold=1.8))
        return out

    nums = [2, 5, 8, 12, 16, 23, 38, 56]
    steps = run(nums, 23, "find 23") + run(nums, 20, "find 20", fail=True)
    tl = play(steps, dict(nums=nums, target=23, low=0.0, high=8.0, mid=-1.0, found=-1.0, code=-1.0))

    def draw(p, s, total):
        t = s.t
        xs = row_xs(len(s.nums), 70, 10)
        step = xs[1] - xs[0]
        top = 150
        fills, edges, inks = [], [], []
        for k in range(len(s.nums)):
            live = s.low - 0.01 <= k < s.high - 0.01
            if abs(k - s.found) < 0.5:
                fills.append(TEAL_LT); edges.append(TEAL); inks.append(INK)
            elif abs(k - s.mid) < 0.5:
                fills.append(BRASS_LT); edges.append(BRASS); inks.append(INK)
            elif live:
                fills.append(PAPER); edges.append(NAVY); inks.append(INK)
            else:
                fills.append("#f3f5f7"); edges.append(LINE); inks.append(FAINT)
        below = cells(p, xs, top, s.nums, cell=64, fills=fills, edges=edges, inks=inks, size=22)
        if s.mid >= 0:
            pointer(p, xs[0] + s.mid * step, top, "mid", BRASS, "above")
        left_edge = xs[0] - 35 + s.low * step
        right_edge = xs[0] - 35 + s.high * step - 10
        if s.high > s.low + 0.01:
            p.line(left_edge, below + 12, max(left_edge, right_edge), below + 12, NAVY, 3)
        pointer(p, xs[0] - 35 + s.low * step + 6, below + 14, "low", NAVY, "below")
        pointer(p, xs[0] - 35 + s.high * step - 6, below + 14, "high", RUST, "below",
                slot=1 if abs(s.high - s.low) < 0.6 else 0)
        scoreboard(p, [("target", s.target, RUST)])
        frame_furniture(p, tl, t, total, "Binary search: halve the range each step",
                        "low..high is half-open: low is the first live position, high is one past the last.",
                        "the loop", rule, s.code, cap_y, rail_y, CODE_Y)

    CODE_Y = 330
    cap_y, rail_y, height = layout(CODE_Y, len(rule))
    return tl, draw, height


# ----------------------------------------------------------- rotated search


def rotated_search():
    code = source("src/problems/binary_search.rs", "pub fn search_rotated", "}")
    mid_l = line_of(code, "let mid")
    hit = line_of(code, "return Some(mid)")
    sorted_l = line_of(code, "let left_is_sorted")
    go_left = line_of(code, "high = mid;")
    go_right = line_of(code, "low = mid + 1;")
    r_test = line_of(code, "} else if nums[mid] < target")
    r_right = line_of(code, "low = mid + 1;", 1)
    r_left = line_of(code, "high = mid;", 1)
    end = line_of(code, "None")

    def run(nums, target, label):
        out = [dict(chapter=label, say="Search for %d in %s, a sorted array rotated at 0."
                    % (target, ", ".join(map(str, nums))), nums=list(nums), target=target, low=0.0,
                    high=float(len(nums)), mid=-1.0, found=-1.0, half="", code=-1.0)]
        low, high = 0, len(nums)
        while low < high:
            mid = low + (high - low) // 2
            out.append(dict(say="mid = %d, which holds %d." % (mid, nums[mid]), mid=float(mid),
                            code=float(mid_l), half=""))
            if nums[mid] == target:
                out.append(dict(say="nums[%d] is the target." % mid, found=float(mid), code=float(hit),
                                kind="insight", hold=1.6))
                return out
            lo_v, mid_v, hi_v = nums[low], nums[mid], nums[high - 1]
            if nums[low] <= nums[mid]:
                out.append(dict(say="nums[low] = %d <= nums[mid] = %d, so the left half %d..%d is sorted."
                                % (nums[low], nums[mid], low, mid), half="left", code=float(sorted_l)))
                if nums[low] <= target < nums[mid]:
                    high = mid
                    out.append(dict(say="%d lies between %d and %d, so it can only be in the left half. "
                                    "high = %d." % (target, lo_v, mid_v, high), high=float(high),
                                    code=float(go_left)))
                else:
                    low = mid + 1
                    out.append(dict(say="%d is not between %d and %d, so it can only be in the right half. "
                                    "low = %d." % (target, lo_v, mid_v, low), low=float(low),
                                    code=float(go_right), mid=-1.0, half=""))
            else:
                out.append(dict(say="nums[low] > nums[mid], so the right half %d..%d is sorted."
                                % (mid + 1, high), half="right", code=float(r_test)))
                if nums[mid] < target <= nums[high - 1]:
                    low = mid + 1
                    out.append(dict(say="%d lies between %d and %d, so low = %d." % (
                        target, mid_v, hi_v, low), low=float(low), code=float(r_right),
                        mid=-1.0, half=""))
                else:
                    high = mid
                    out.append(dict(say="%d is not in the sorted right half, so high = %d." % (
                        target, high), high=float(high), code=float(r_left), mid=-1.0, half=""))
        out.append(dict(say="The range is empty, so the function returns None: %d is absent." % target,
                        code=float(end), kind="fail", hold=1.8))
        return out

    nums = [4, 5, 6, 7, 0, 1, 2]
    steps = run(nums, 0, "find 0") + run(nums, 3, "find 3")
    tl = play(steps, dict(nums=nums, target=0, low=0.0, high=7.0, mid=-1.0, found=-1.0, half="",
                          code=-1.0))

    def draw(p, s, total):
        t = s.t
        xs = row_xs(len(s.nums), 70, 10)
        step = xs[1] - xs[0]
        top = 150
        fills, edges, inks = [], [], []
        m = int(s.mid) if s.mid >= 0 else -1
        for k in range(len(s.nums)):
            live = s.low - 0.01 <= k < s.high - 0.01
            sorted_half = (s.half == "left" and s.low - 0.01 <= k <= m) or \
                          (s.half == "right" and m < k < s.high - 0.01)
            if abs(k - s.found) < 0.5:
                fills.append(TEAL_LT); edges.append(TEAL); inks.append(INK)
            elif k == m:
                fills.append(BRASS_LT); edges.append(BRASS); inks.append(INK)
            elif sorted_half:
                fills.append(TEAL_LT); edges.append(NAVY); inks.append(INK)
            elif live:
                fills.append(PAPER); edges.append(NAVY); inks.append(INK)
            else:
                fills.append("#f3f5f7"); edges.append(LINE); inks.append(FAINT)
        below = cells(p, xs, top, s.nums, cell=64, fills=fills, edges=edges, inks=inks, size=22)
        if s.mid >= 0:
            pointer(p, xs[0] + s.mid * step, top, "mid", BRASS, "above")
        if s.half:
            a = s.low if s.half == "left" else m + 1
            b = m if s.half == "left" else s.high - 1
            p.text((xs[0] + a * step + xs[0] + b * step) / 2, top - 44, "sorted half", 12, TEAL, 700,
                   "middle")
        if s.high > s.low + 0.01:
            p.line(xs[0] - 35 + s.low * step, below + 12, xs[0] - 45 + s.high * step, below + 12, NAVY, 3)
        pointer(p, xs[0] - 35 + s.low * step + 6, below + 14, "low", NAVY, "below")
        pointer(p, xs[0] - 35 + s.high * step - 6, below + 14, "high", RUST, "below",
                slot=1 if abs(s.high - s.low) < 0.6 else 0)
        scoreboard(p, [("target", s.target, RUST)])
        frame_furniture(p, tl, t, total, "Binary search on a rotated array",
                        "One half around mid is always sorted. Search it if it can hold the target.",
                        "search_rotated", code, s.code, cap_y, rail_y, CODE_Y, code_size=10.6, lead=15.0)

    CODE_Y = 330
    cap_y, rail_y, height = layout(CODE_Y, len(code), 15.0)
    return tl, draw, height


# --------------------------------------------------------------- rotate grid


def rotate_grid():
    code = source("src/bin/rotate_matrix.rs", "fn rotate(", "}")
    swap = line_of(code, "let tmp")
    rev = line_of(code, "row.reverse()")
    n = 3
    defaults = dict(code=-1.0, hot="", phase="")
    for v in range(1, 10):
        defaults["r%d" % v] = float((v - 1) // n)
        defaults["c%d" % v] = float((v - 1) % n)
    grid = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    steps = [dict(chapter="transpose", say="Rotate a 3 by 3 grid a quarter turn clockwise, in place. "
                  "Step one: transpose.", code=-1.0)]

    def place():
        st = {}
        for r in range(n):
            for c in range(n):
                st["r%d" % grid[r][c]] = float(r)
                st["c%d" % grid[r][c]] = float(c)
        return st

    for i in range(n):
        for j in range(i + 1, n):
            a, b = grid[i][j], grid[j][i]
            grid[i][j], grid[j][i] = b, a
            st = dict(say="i = %d, j = %d: swap m[%d][%d] = %d with m[%d][%d] = %d." % (i, j, i, j, a, j, i, b),
                      code=float(swap), hot="%d,%d" % (a, b), dur=1.1)
            st.update(place())
            steps.append(st)
    steps.append(dict(say="j starts at i + 1, so only cells above the diagonal are visited, and each pair "
                      "swaps once.", hot="", kind="insight", hold=1.2))
    first = True
    for r in range(n):
        grid[r].reverse()
        st = dict(say="row.reverse() on row %d: %s." % (r, ", ".join(map(str, grid[r]))), code=float(rev),
                  hot=",".join(map(str, grid[r])), dur=1.1)
        if first:
            st["chapter"] = "reverse rows"
            first = False
        st.update(place())
        steps.append(st)
    steps.append(dict(say="The grid is 7 4 1 / 8 5 2 / 9 6 3: the quarter turn, with no second grid.",
                      hot="", code=-1.0, kind="insight", hold=1.4))
    # the bug: j from 0 swaps each pair twice
    grid = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
    st = dict(chapter="j from 0", say="Now suppose j started at 0 instead of i + 1.", kind="fail", hot="",
              phase="bug", code=-1.0, dur=1.0)
    st.update(place())
    steps.append(st)
    grid[0][1], grid[1][0] = 4, 2
    st = dict(say="i = 0, j = 1 swaps 2 and 4.", kind="fail", hot="2,4", code=float(swap), dur=1.0)
    st.update(place()); steps.append(st)
    grid[0][1], grid[1][0] = 2, 4
    st = dict(say="Later, i = 1, j = 0 swaps the same pair back. Every pair is undone, and the transpose "
              "does nothing.", kind="fail", hot="2,4", dur=1.0, hold=1.8)
    st.update(place()); steps.append(st)
    tl = play(steps, defaults)

    def draw(p, s, total):
        t = s.t
        size, x0, y0 = 82, 290, 96
        hot = s.hot.split(",") if s.hot else []
        for r in range(n):
            for c in range(n):
                diag = r == c
                p.rect(x0 + c * size + 3, y0 + r * size + 3, size - 6, size - 6,
                       "#f6f8fa" if not diag else "#eef2f7", LINE, 8, 1.2, dash="4 4")
        p.line(x0 + 10, y0 + 10, x0 + n * size - 10, y0 + n * size - 10, FAINT, 1.2, dash="3 5")
        for v in range(1, 10):
            x = x0 + s["c%d" % v] * size
            y = y0 + s["r%d" % v] * size
            on = str(v) in hot
            p.rect(x + 6, y + 6, size - 12, size - 12, BRASS_LT if on else PAPER, BRASS if on else NAVY,
                   8, 1.8, shadow="shadow" if on else None)
            p.text(x + size / 2, y + size / 2 + 9, str(v), 25, INK, 700, "middle", mono=True)
        for k in range(n):
            p.text(x0 - 14, y0 + k * size + size / 2 + 5, "row %d" % k, 11.5, MUTED, 600, "end")
        p.text(x0 + n * size + 14, y0 + n * size - 6, "diagonal", 11, FAINT, 600)
        frame_furniture(p, tl, t, total, "Rotating a grid: transpose, then reverse each row",
                        "Both steps work in place, by swapping values inside the grid.",
                        "rotate", code, s.code, cap_y, rail_y, CODE_Y)

    CODE_Y = 356
    cap_y, rail_y, height = layout(CODE_Y, len(code))
    return tl, draw, height


# --------------------------------------------------------------------- KMP


def kmp_lps_table(needle):
    lps = [0] * len(needle)
    left, right = 0, 1
    while right < len(needle):
        if needle[right] == needle[left]:
            left += 1
            lps[right] = left
            right += 1
        elif left > 0:
            left = lps[left - 1]
        else:
            right += 1
    return lps


HAYS = {"found": "aabaaabaaac", "absent": "aabaaabaab"}


def kmp_search():
    hay, needle = HAYS["found"], "aabaaac"
    lps = kmp_lps_table(needle)
    code = source("src/bin/kmp_pattern_matching.rs", "while right < haystack.len()", "-1")
    same = line_of(code, "if haystack[right] == needle[left]")
    back_l = line_of(code, "left = lps[left - 1]")
    skip = line_of(code, "right += 1;", 1)
    done = line_of(code, "return (right - left)")
    steps = [dict(chapter="match", say="Search for \"%s\" in \"%s\". right walks the haystack, and left "
                  "counts the needle characters matched so far." % (needle, hay), code=-1.0)]
    left = right = 0
    fell = False
    while right < len(hay):
        if hay[right] == needle[left]:
            steps.append(dict(say="haystack[%d] = '%s' equals needle[%d]. Both advance." % (
                right, hay[right], left), right=float(right), left=float(left), cmp="ok", code=float(same)))
            left += 1
            right += 1
            steps.append(dict(say="%d needle characters match." % left, right=float(right),
                              left=float(left), cmp="", hold=0.1, dur=0.5))
        elif left > 0:
            steps.append(dict(chapter=None if fell else "fall back",
                              say="haystack[%d] = '%s' differs from needle[%d] = '%s'." % (
                right, hay[right], left, needle[left]), right=float(right), left=float(left), cmp="bad",
                code=float(same)))
            new = lps[left - 1]
            steps.append(dict(say="lps[%d] = %d: the last %d matched characters are also the needle's start. "
                              "left = %d, and right stays at %d." % (left - 1, new, new, new, right),
                              left=float(new), cmp="", lps_hot=float(left - 1), code=float(back_l), dur=1.2,
                              kind="insight"))
            steps.append(dict(say="A naive search would move right back to %d and compare those characters "
                              "again. KMP never moves right backward." % (right - left + 1),
                              lps_hot=-1.0, kind="insight", hold=0.8))
            left = new
            fell = True
        else:
            steps.append(dict(say="Mismatch with nothing matched, so right advances.", right=float(right + 1),
                              code=float(skip)))
            right += 1
        if left == len(needle):
            steps.append(dict(say="All %d characters match. The needle starts at right - left = %d."
                              % (len(needle), right - left), found=1.0, code=float(done), kind="insight",
                              hold=1.8))
            break
    absent = HAYS["absent"]
    steps.append(dict(chapter="absent", say="Now a haystack that does not contain the needle: \"%s\"."
                      % absent, kind="fail", data="absent", right=0.0, left=0.0, cmp="", found=0.0,
                      code=-1.0, hold=0.6))
    left = right = 0
    while right < len(absent):
        if absent[right] == needle[left]:
            left += 1
            right += 1
            steps.append(dict(say="%d needle characters match." % left, kind="fail", right=float(right),
                              left=float(left), cmp="", code=float(same), dur=0.35, hold=0.0))
        elif left > 0:
            new = lps[left - 1]
            steps.append(dict(say="Mismatch: left falls back to lps[%d] = %d." % (left - 1, new),
                              kind="fail", left=float(new), cmp="bad", code=float(back_l), dur=0.5))
            left = new
        else:
            right += 1
            steps.append(dict(say="Mismatch at the needle's start: right advances.", kind="fail",
                              right=float(right), cmp="", code=float(skip), dur=0.35, hold=0.0))
    steps.append(dict(say="right reaches the end with %d characters matched, so the loop ends and returns -1. "
                      "Each haystack character was read once." % left, kind="fail", cmp="",
                      code=float(len(code) - 1), hold=2.2))
    steps = [{k: v for k, v in x.items() if v is not None} for x in steps]
    tl = play(steps, dict(code=-1.0, right=0.0, left=0.0, cmp="", found=0.0, lps_hot=-1.0,
                          data="found"))

    def draw(p, s, total):
        t = s.t
        hay = HAYS[s.data]
        cell, gap = 50, 6
        xs = row_xs(len(hay), cell, gap)
        step = xs[1] - xs[0]
        top = 120
        offset = s.right - s.left
        fills, edges = [], []
        for k in range(len(hay)):
            if s.found > 0.5 and offset - 0.01 <= k < offset + len(needle) - 0.01:
                fills.append(TEAL_LT); edges.append(TEAL)
            elif abs(k - s.right) < 0.5 and s.cmp:
                fills.append(TEAL_LT if s.cmp == "ok" else RUST_LT); edges.append(TEAL if s.cmp == "ok" else RUST)
            elif offset - 0.01 <= k < s.right - 0.01:
                fills.append(TEAL_LT); edges.append(LINE)
            else:
                fills.append(PAPER); edges.append(LINE)
        cells(p, xs, top, list(hay), cell=cell, fills=fills, edges=edges, size=20, index=True)
        p.text(xs[0] - 34, top + 32, "haystack", 12, MUTED, 600, "end")
        pointer(p, xs[0] + s.right * step, top, "right", BRASS, "above")
        ny = top + 96
        shown = [k for k in range(len(needle)) if offset + k < len(hay) - 0.01]
        nx = [xs[0] + (offset + k) * step for k in shown]
        nf, ne = [], []
        for k in range(len(needle)):
            if s.found > 0.5 or k < s.left - 0.01:
                nf.append(TEAL_LT); ne.append(TEAL)
            elif abs(k - s.left) < 0.5 and s.cmp:
                nf.append(TEAL_LT if s.cmp == "ok" else RUST_LT); ne.append(TEAL if s.cmp == "ok" else RUST)
            else:
                nf.append(PAPER); ne.append(LINE)
        below = cells(p, nx, ny, [needle[k] for k in shown], cell=cell, fills=[nf[k] for k in shown],
                      edges=[ne[k] for k in shown], size=20)
        p.text(nx[0] - 34, ny + 32, "needle", 12, MUTED, 600, "end")
        pointer(p, xs[0] + (offset + s.left) * step, below, "left", NAVY, "below")
        ly = below + 64
        p.text(xs[0] - 34, ly + 20, "lps", 12, MUTED, 600, "end")
        lx = row_xs(len(needle), 40, 4, cx=xs[0] + 3 * (40 + 4) + 0)
        lx = [xs[0] + k * 44 for k in range(len(needle))]
        cells(p, lx, ly, lps, cell=34, size=14, index=False,
              fills=[BRASS_LT if abs(k - s.lps_hot) < 0.5 else "#f6f8fa" for k in range(len(lps))],
              edges=[BRASS if abs(k - s.lps_hot) < 0.5 else LINE for k in range(len(lps))])
        frame_furniture(p, tl, t, total, "KMP search: right never moves backward",
                        "On a mismatch, lps says how many matched characters can be kept.",
                        "str_str (the loop)", code, s.code, cap_y, rail_y, CODE_Y)

    CODE_Y = 414
    cap_y, rail_y, height = layout(CODE_Y, len(code))
    return tl, draw, height


def kmp_lps():
    needle = "aabaaac"
    code = source("src/bin/kmp_pattern_matching.rs", "fn build_lps", "}")
    same = line_of(code, "if needle[right] == needle[left]")
    write = line_of(code, "lps[right] = left;")
    back_l = line_of(code, "left = lps[left - 1]")
    skip = line_of(code, "right += 1;", 1)
    steps = [dict(say="lps[i] is the length of the longest proper prefix of needle[0..=i] that is also its "
                  "suffix. lps[0] is always 0.", code=-1.0, known=1.0)]
    lps = [0] * len(needle)
    left, right = 0, 1
    while right < len(needle):
        if needle[right] == needle[left]:
            steps.append(dict(say="needle[%d] = '%s' equals needle[%d] = '%s'." % (right, needle[right], left,
                                                                                 needle[left]),
                              right=float(right), left=float(left), cmp="ok", code=float(same)))
            left += 1
            lps[right] = left
            steps.append(dict(say="So lps[%d] = %d: \"%s\" starts and ends with \"%s\"." % (
                right, left, needle[:right + 1], needle[:left]), lps=list(lps), known=float(right + 1),
                code=float(write), cmp=""))
            right += 1
            steps.append(dict(say="right moves to %d, and left to %d." % (right, left), right=float(right),
                              left=float(left), hold=0.1))
        elif left > 0:
            steps.append(dict(say="needle[%d] = '%s' differs from needle[%d] = '%s'." % (
                right, needle[right], left, needle[left]), right=float(right), left=float(left), cmp="bad",
                code=float(same)))
            new = lps[left - 1]
            steps.append(dict(say="left falls back to lps[%d] = %d, the next shorter prefix that could "
                              "still match. right stays." % (left - 1, new), left=float(new), cmp="",
                              code=float(back_l), kind="insight"))
            left = new
        else:
            steps.append(dict(say="needle[%d] = '%s' differs from needle[0], so lps[%d] stays 0." % (
                right, needle[right], right), right=float(right), cmp="bad", code=float(skip)))
            right += 1
            steps.append(dict(say="right moves to %d." % right, right=float(right), cmp="", known=float(right),
                              hold=0.1))
    steps.append(dict(say="The table is 0 1 0 1 2 2 0. The search uses it without ever re-reading the "
                      "haystack.", right=float(len(needle)), kind="insight", code=-1.0, hold=1.8,
                      known=float(len(needle))))
    good = list(lps)
    steps.append(dict(chapter="reset to 0", say="Now replace left = lps[left - 1] with left = 0: on a "
                      "mismatch, forget everything matched.", kind="fail", strike=float(back_l),
                      lps=[0] * len(needle), known=1.0, right=1.0, left=0.0, cmp="", code=-1.0))
    bad = [0] * len(needle)
    left, right = 0, 1
    while right < len(needle):
        if needle[right] == needle[left]:
            left += 1
            bad[right] = left
            right += 1
            steps.append(dict(say="Match: lps[%d] = %d." % (right - 1, left), kind="fail", lps=list(bad),
                              known=float(right), right=float(right), left=float(left), cmp="",
                              code=float(write), dur=0.4, hold=0.1))
        elif left > 0:
            steps.append(dict(say="needle[%d] = '%s' differs from needle[%d] = '%s'. left drops to 0." % (
                right, needle[right], left, needle[left]), kind="fail", right=float(right),
                left=0.0, cmp="bad", code=float(same)))
            left = 0
        else:
            right += 1
            steps.append(dict(say="No match at the start: lps[%d] stays 0." % (right - 1), kind="fail",
                              right=float(right), cmp="", known=float(right), code=float(skip), dur=0.4,
                              hold=0.1))
    wrong = [k for k in range(len(needle)) if bad[k] != good[k]]
    steps.append(dict(say="lps[%d] is %d, but \"%s\" starts and ends with \"%s\": the right value is %d. "
                      "The fallback to a shorter border was skipped." % (
                          wrong[0], bad[wrong[0]], needle[:wrong[0] + 1], needle[:good[wrong[0]]],
                          good[wrong[0]]), kind="fail", wrong=float(wrong[0]), code=-1.0, hold=2.4))
    tl = play(steps, dict(code=-1.0, right=1.0, left=0.0, cmp="", lps=[0] * len(needle), known=1.0,
                          strike=-1.0, wrong=-1.0))

    def draw(p, s, total):
        t = s.t
        xs = row_xs(len(needle), 60, 10)
        step = xs[1] - xs[0]
        top = 150
        fills, edges = [], []
        for k in range(len(needle)):
            if abs(k - s.right) < 0.5 and s.cmp:
                fills.append(TEAL_LT if s.cmp == "ok" else RUST_LT); edges.append(TEAL if s.cmp == "ok" else RUST)
            elif abs(k - s.left) < 0.5 and s.cmp:
                fills.append(BRASS_LT); edges.append(BRASS)
            else:
                fills.append(PAPER); edges.append(LINE)
        below = cells(p, xs, top, list(needle), cell=60, fills=fills, edges=edges, size=22)
        p.text(xs[0] - 44, top + 36, "needle", 12, MUTED, 600, "end")
        if s.right < len(needle) - 0.01:
            pointer(p, xs[0] + s.right * step, top, "right", RUST, "above")
        pointer(p, xs[0] + s.left * step, below, "left", NAVY, "below")
        ly = below + 64
        p.text(xs[0] - 44, ly + 24, "lps", 12, MUTED, 600, "end")
        vals = [str(v) if k < s.known - 0.01 else "" for k, v in enumerate(s.lps)]
        cells(p, xs, ly, vals, cell=40, size=16, index=False,
              fills=[RUST_LT if abs(k - s.wrong) < 0.5 else ("#f6f8fa" if v else PAPER)
                     for k, v in enumerate(vals)],
              edges=[RUST if abs(k - s.wrong) < 0.5 else LINE for k in range(len(vals))])
        frame_furniture(p, tl, t, total, "Building the lps table",
                        "The needle is compared with itself, with the same three branches as the search.",
                        "build_lps", code, s.code, cap_y, rail_y, CODE_Y, strike=s.strike)

    CODE_Y = 362
    cap_y, rail_y, height = layout(CODE_Y, len(code))
    return tl, draw, height


def build(name, fn, extra=()):
    def run(only=None):
        tl, draw, height = fn()
        return render(name, tl, draw, height, only=only, extra_colors=extra)
    return run


BUILDERS = {
    "two-sum": build_two_sum,
    "brackets": build("ch03-brackets.gif", brackets),
    "three-sum": build("ch03-three-sum.gif", three_sum, (NAVY,)),
    "window": build("ch03-window.gif", window),
    "merge-intervals": build("ch03-merge-intervals.gif", merge_intervals, (NAVY,)),
    "binary-search": build("ch03-binary-search.gif", binary_search, (NAVY,)),
    "rotated-search": build("ch03-rotated-search.gif", rotated_search, (NAVY,)),
    "rotate-grid": build("ch03-rotate-grid.gif", rotate_grid, (NAVY,)),
    "kmp-search": build("ch03-kmp-search.gif", kmp_search, (NAVY,)),
    "kmp-lps": build("ch03-kmp-lps.gif", kmp_lps, (NAVY,)),
}

if __name__ == "__main__":
    import sys
    args = sys.argv[1:]
    if args and args[0] == "frames":
        for path in BUILDERS[args[1]](only=[float(a) for a in args[2:]]):
            print(path)
    else:
        for name in args or BUILDERS:
            print(BUILDERS[name]())
