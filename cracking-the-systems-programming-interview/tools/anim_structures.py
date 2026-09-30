"""Animations for the tree and graph chapters, chapters 11 and 12.

Every frame is one step of the algorithm the chapter quotes: one insertion, one
node taken off the queue, one edge kept or skipped.

A node is a small circle, not a rectangle. State is a colour on the circle and a
wordless ring around it, so the reader compares colours rather than parsing a grid
of boxes. A queue, a stack, or a finished order is a rail under the graph.

Colours carry the state, and every animation that leans on a colour carries a
legend that names it:

  * plain   not reached yet
  * cream   waiting in the frontier, or the thing being examined now
  * green   settled, visited, or kept

Each animation ends on the case the algorithm has to handle and the chapter's
prose usually skips: a value that is absent, a node no walk can reach, a graph
with a cycle, a graph in two pieces.
"""

from animlib import *  # noqa: F401,F403
from animlib import Frame, frames, publish

R = 21.0             # node radius


def node(f, x, y, label, fill=WHITE, stroke=BORDER, size=T_CELL - 1, r=R):
    f.circle(x, y, r, fill, stroke, 1.8)
    f.text(x, y + 6, label, size, INK, mono=True, anchor="middle")


def boxes_of(pos, r=R):
    return {k: (x - r, y - r, 2 * r, 2 * r) for k, (x, y) in pos.items()}


def edges_of(f, pos, edges, colors=None, ghosts=(), r=R, width=1.6):
    """Draw the edges first, so the nodes sit on top of them."""
    boxes = boxes_of(pos, r)
    for a, b in edges:
        ax, ay = box_edge(boxes[a], pos[b])
        bx, by = box_edge(boxes[b], pos[a])
        color, w = (colors or {}).get((a, b), (BORDER, width))
        f.line(ax, ay, bx, by, color, w)
    for a, b in ghosts:
        ax, ay = box_edge(boxes[a], pos[b])
        bx, by = box_edge(boxes[b], pos[a])
        f.line(ax, ay, bx, by, BORDER, 1.4, dash=True, opacity=0.7)


def arrows_of(f, pos, edges, colors=None, r=R, width=1.6):
    boxes = boxes_of(pos, r)
    for a, b in edges:
        ax, ay = box_edge(boxes[a], pos[b])
        bx, by = box_edge(boxes[b], pos[a])
        color, w = (colors or {}).get((a, b), (BORDER, width))
        f.arrow(ax, ay, bx, by, color, w, head=9.0)


def rail_of(f, y, values, x0=None, unit=42, gap=8, colors=None, size=T_CELL, empty="the queue"):
    """A queue, a stack, or an order, drawn on a rail under the graph."""
    if not values:
        f.text(PAD, y + 6, "empty", T_MARK, MUTED, mono=True, layer="text")
        return []
    return rail_row(f, y, values, x0=x0, unit=unit, gap=gap, size=size, ticks=False,
                    colors=colors or [INK] * len(values))


# ---------------------------------------------------- Binary search tree (11.3)

BST_POS = {8: (410, 40), 3: (232, 106), 10: (594, 106),
           1: (120, 174), 6: (330, 174), 14: (700, 174), 13: (626, 240)}
BST_EDGES = [(8, 3), (8, 10), (3, 1), (3, 6), (10, 14), (14, 13)]


def bst():
    """Insert seven values, then search for one that is there and one that is not."""
    order = [8, 3, 10, 1, 6, 14, 13]
    tree, root, steps = {}, None, []
    for value in order:
        if root is None:
            root = value
            tree[value] = [None, None]
            steps.append((set(tree), [value], value, "insert",
                          "Insert %d. The tree is empty, so %d becomes the root." % (value, value)))
            continue
        path, here = [], root
        while True:
            path.append(here)
            left, right = tree[here]
            if value < here:
                if left is None:
                    tree[here][0] = value
                    break
                here = left
            else:
                if right is None:
                    tree[here][1] = value
                    break
                here = right
        tree[value] = [None, None]
        way = "left" if value < path[-1] else "right"
        steps.append((set(tree), path + [value], value, "insert",
                      "Insert %d: it walks %s and hangs off %d on the %s."
                      % (value, " -> ".join(str(v) for v in path), path[-1], way)))
    for i, value in enumerate([8, 3, 6]):
        steps.append((set(tree), [8, 3, 6][:i + 1], value, "search",
                      "Search for 6: compare with %d. %s"
                      % (value, "Equal, so the value is found after three comparisons."
                         if value == 6 else
                         ("6 is smaller, so only the left subtree can hold it." if 6 < value
                          else "6 is larger, so only the right subtree can hold it."))))
    steps.append((set(tree), [8, 3, 6], 7, "absent",
                  "Now search for 7. It walks 8 -> 3 -> 6 and then looks for a right child of 6."))
    insight_at, fail_at = len(steps) - 4, len(steps) - 1

    def make(step, height=None, rows=0, index=0):
        placed, path, value, kind, line = step
        failing = kind == "absent"
        f = Frame(
            "A binary search tree: the ordering decides which way to go",
            sub="Every node is larger than the whole of its left subtree, and smaller than its right.",
            diagram=290,
            legend=[("on the path", BRASS), ("placed", TEAL), ("not placed", BORDER)],
            step=line,
            note="The tree keeps one value per node, and a search visits one node per level.",
            pairs=[("value", value, RUST), ("comparisons", len(path), TEAL),
                   ("nodes", len(placed), INK)],
            insight=("Each comparison discards a whole subtree, so a search costs the height."
                     ) if index == insight_at else None,
            fails=("The walk reaches node 6 and finds no right child, so 7 is not in the tree. A "
                   "missing value ends at an empty child, not at a node holding it."
                   ) if failing else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        pos = {k: (x, y + t) for k, (x, y) in BST_POS.items()}
        live = [(a, b) for a, b in BST_EDGES if a in placed and b in placed]
        on_path = [(a, b) for a, b in live if a in path and b in path]
        edges_of(f, pos, live, colors={e: (BRASS, 3.0) for e in on_path})
        for k in placed:
            x, y = pos[k]
            if k in path and not failing:
                fill, stroke = CREAM, BRASS
            elif k == path[-1] and not failing:
                fill, stroke = GREEN, TEAL
            else:
                fill, stroke = (CREAM, BRASS) if failing and k in path else (GREEN, TEAL)
            node(f, x, y, k, fill, stroke)
        if failing:
            # The empty child that ends the search, drawn as the gap it is.
            x, y = pos[6]
            cross(f, x + 54, y + 34, RUST, 11.0, 2.4)
            f.text(x + 70, y + 40, "no right child, so 7 is not here", T_MARK, RUST,
                   anchor="start", bold=True, layer="text")
        return f

    publish("ch11-bst.gif", frames(make, steps),
            holds(len(steps), longer=(insight_at, fail_at)))


# --------------------------------------------------------------- Trie (11.6)

TRIE_POS = {"": (410, 40), "c": (296, 106), "d": (566, 106),
            "ca": (240, 174), "do": (566, 174),
            "cat": (156, 242), "car": (300, 242), "dog": (566, 242)}
TRIE_EDGES = [("", "c"), ("", "d"), ("c", "ca"), ("ca", "cat"), ("ca", "car"),
              ("d", "do"), ("do", "dog")]
TRIE_WORDS = ("cat", "car", "dog")


def trie():
    """Insert three words, then look up one that is there and one that is not."""
    created = {""}
    steps = []
    for word in TRIE_WORDS:
        for i in range(1, len(word) + 1):
            prefix = word[:i]
            fresh = prefix not in created
            created.add(prefix)
            steps.append((prefix, word, set(created), "insert",
                          "Insert \"%s\": %s, and this node %s."
                          % (word,
                             "there is no edge for '%s', so a new one is added" % prefix[-1] if fresh
                             else "the edge for '%s' already exists, so the walk follows it" % prefix[-1],
                             "ends the word" if i == len(word) else "carries the walk on")))
    for query in ("ca", "cab"):
        for i in range(1, len(query) + 1):
            prefix = query[:i]
            if prefix not in created:
                steps.append((prefix[:-1], query, set(created), "absent",
                              "Look up \"%s\": there is no edge for '%s', so the walk stops."
                              % (query, prefix[-1])))
                break
            steps.append((prefix, query, set(created), "lookup",
                          "Look up \"%s\": follow the edge for '%s' to the node \"%s\"."
                          % (query, prefix[-1], prefix)))
        else:
            steps.append((query, query, set(created), "lookup",
                          "Look up \"%s\": the walk reaches a node that ends a stored word, so "
                          "\"%s\" is in the trie." % (query, query)))
    steps.append(("", "zebra", set(created), "absent",
                  "Now look up \"zebra\". The root has no edge for 'z', so the walk stops immediately."))
    insight_at, fail_at = 4, len(steps) - 1

    def make(step, height=None, rows=0, index=0):
        prefix, word, live, kind, line = step
        failing = kind == "absent" and index == fail_at
        f = Frame(
            "A trie: every edge is one character, so prefixes are shared",
            sub="A word is stored by walking its characters from the root.",
            diagram=300,
            legend=[("the walk", TEAL), ("ends a word", BRASS), ("absent", RUST)],
            step=line,
            note="One node per distinct prefix, not one node per word.",
            pairs=[("word", "\"%s\"" % word, RUST),
                   ("reached", prefix or "root", TEAL),
                   ("ends a word", "yes" if prefix in TRIE_WORDS else "no", INK)],
            insight=("cat and car share the node for \"ca\", so a lookup costs the key length, not "
                     "the size of the dictionary.") if index == insight_at else None,
            fails=("A lookup that leaves the trie costs only the characters it matched, and here "
                   "that is none. A missing key is found fast, which is the point of the shape."
                   ) if failing else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        pos = {k: (x, y + t) for k, (x, y) in TRIE_POS.items() if k in live}
        keep = [(a, b) for a, b in TRIE_EDGES if a in live and b in live]
        arrows_of(f, pos, keep, width=1.4)
        for key in pos:
            x, y = pos[key]
            on = key and (prefix == key or prefix.startswith(key))
            text = "root" if key == "" else key
            r = max(R, text_width(text, T_CELL - 3, True) / 2.0 + 10)
            f.circle(x, y, r, CREAM if on else WHITE, TEAL if on else BORDER,
                     2.0 if on else 1.2)
            f.text(x, y + 5, text, T_CELL - 3, INK, mono=True, anchor="middle")
            if key in TRIE_WORDS:
                ring(f, (x - r, y - r, 2 * r, 2 * r), BRASS, pad=3, dash=False, width=1.6)
        if failing:
            x, y = pos[""]
            cross(f, x + 66, y + 30, RUST, 11.0, 2.4)
            f.text(x + 82, y + 36, "no edge for 'z'", T_MARK, RUST, anchor="start",
                   bold=True, layer="text")
        return f

    publish("ch11-trie.gif", frames(make, steps),
            holds(len(steps), longer=(insight_at, fail_at)))


# ------------------------------------------------------- Breadth first (12.3)

GRAPH_POS = {0: (120, 118), 1: (286, 56), 2: (286, 180),
             3: (462, 56), 4: (462, 180), 5: (628, 118), 6: (742, 236)}
GRAPH_EDGES = [(0, 1), (0, 2), (1, 3), (2, 3), (2, 4), (3, 5), (4, 5)]
ADJ = {0: [1, 2], 1: [0, 3], 2: [0, 3, 4], 3: [1, 2, 5], 4: [2, 5], 5: [3, 4], 6: []}


def _bfs_steps(start):
    from collections import deque
    seen, queue, done = {start}, deque([start]), []
    steps = [([start], {start}, [], None, "Put %d in the queue and mark it seen." % start)]
    while queue:
        here = queue.popleft()
        done.append(here)
        added = []
        for nxt in ADJ[here]:
            if nxt not in seen:
                seen.add(nxt)
                queue.append(nxt)
                added.append(nxt)
        steps.append((list(queue), set(seen), list(done), here,
                      "Take %d off the front. %s" % (here,
                       ("Its unseen neighbours %s go on the back." % added) if added
                       else "Every neighbour of it has been seen already.")))
    steps.append(([], set(seen), list(done), None,
                  "The queue is empty, so every node reachable from 0 has been visited."))
    steps.append(([], set(seen), list(done), None,
                  "Node 6 has no edge at all, so no walk from 0 can reach it and it stays unvisited."))
    return steps


def bfs():
    """A queue visits nodes in rings around the start."""
    steps = _bfs_steps(0)
    insight_at, fail_at = len(steps) - 2, len(steps) - 1

    def make(step, height=None, rows=0, index=0):
        queue, seen, done, here, line = step
        failing = index == fail_at
        f = Frame(
            "Breadth-first search: a queue visits nodes in rings",
            sub="Every neighbour of the current node is queued before any of their neighbours.",
            diagram=310,
            legend=[("visited", TEAL), ("in the queue", BRASS), ("not seen", BORDER)],
            step=line,
            note="The queue is the frontier: it holds the nodes one edge from what is visited.",
            pairs=[("visiting", here if here is not None else "-", RUST),
                   ("in queue", len(queue), BRASS), ("visited", len(done), TEAL)],
            insight=("The queue holds the frontier, so distance d is finished before distance d+1."
                     ) if index == insight_at else None,
            fails=("A search from one start reaches only its own component. Node 6 is a second "
                   "component, so counting the visited nodes is not the same as counting the graph."
                   ) if failing else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        pos = {k: (x, y + t) for k, (x, y) in GRAPH_POS.items()}
        fills, strokes = {}, {}
        for key in pos:
            if key in done:
                fills[key], strokes[key] = GREEN, TEAL
            elif key in seen:
                fills[key], strokes[key] = CREAM, BRASS
            else:
                fills[key], strokes[key] = WHITE, BORDER
        edges_of(f, pos, GRAPH_EDGES)
        boxes = boxes_of(pos)
        for key in pos:
            x, y = pos[key]
            if key in queue:
                ring(f, boxes[key], BRASS)
            if key == here:
                f.glow(x, y, 44, RUST, 0.35)
            f.circle(x, y, R, fills[key], RUST if key == here else strokes[key],
                     2.0 if key == here else 1.6)
            f.text(x, y + 6, key, T_CELL - 1, INK, mono=True, anchor="middle")
        if failing:
            ring(f, boxes[6], RUST, pad=6, width=2.0)
            cross(f, 742, 236, "none", 0) if False else None
            f.text(742, 292, "a second component", T_MARK, RUST, anchor="middle",
                   bold=True, layer="text")
        f.text(PAD, t + 252, "the queue", T_MARK, MUTED, layer="text")
        rail_of(f, t + 274, list(queue), x0=200, colors=[BRASS] * len(queue))
        if queue:
            f.text(200 + len(queue) * 50 + 6, t + 280, "front", T_MARK, MUTED, layer="text")
        return f

    publish("ch12-bfs.gif", frames(make, steps),
            holds(len(steps), longer=(insight_at, fail_at)))


# --------------------------------------------------------- Depth first (12.4)

def _dfs_steps(start):
    steps, done, seen = [], [], set()

    def visit(here, path):
        seen.add(here)
        done.append(here)
        deeper = [n for n in ADJ[here] if n not in seen]
        steps.append((list(done), list(path), here,
                      "Visit %d. %s" % (here, ("Go deeper into its first unseen neighbour."
                                               if deeper else
                                               "No unseen neighbour is left, so the recursion returns."))))
        for nxt in deeper:
            steps.append((list(done), list(path) + [here], here,
                          "From %d, follow the edge to %d before looking at anything else." % (here, nxt)))
            visit(nxt, path + [here])

    visit(start, [])
    steps.append((list(done), [], None,
                  "Every node reachable from 0 has been visited once. The stack is empty."))
    steps.append((list(done), [], None,
                  "Node 6 is still unvisited, and it always will be: no edge leads to it."))
    return steps


def dfs():
    """One branch at a time, following the call stack."""
    steps = _dfs_steps(0)
    insight_at, fail_at = len(steps) - 2, len(steps) - 1

    def make(step, height=None, rows=0, index=0):
        done, stack, here, line = step
        failing = index == fail_at
        f = Frame(
            "Depth-first search: follow one edge as far as it goes",
            sub="The recursion returns only when the current node has no unseen neighbour left.",
            diagram=310,
            legend=[("visited", TEAL), ("being explored", RUST), ("not seen", BORDER)],
            step=line,
            note="The stack is the path from the start to the node being explored.",
            pairs=[("visiting", here if here is not None else "-", RUST),
                   ("stack", len(stack), BRASS), ("visited", len(done), TEAL)],
            insight=("The call stack is the path from the start, so memory follows the longest path."
                     ) if index == insight_at else None,
            fails=("Depth-first has the same blind spot as breadth-first: it explores one component "
                   "and stops. Reaching every node needs a loop over the starts, not a bigger stack."
                   ) if failing else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        pos = {k: (x, y + t) for k, (x, y) in GRAPH_POS.items()}
        done_set = set(done)
        on_path = set(stack) | ({here} if here is not None else set())
        active = {}
        for i in range(len(stack)):
            a = stack[i]
            b = here if i == len(stack) - 1 else (stack[i + 1] if i + 1 < len(stack) else None)
            if b is not None:
                active[(a, b)] = (TEAL, 3.0)
                active[(b, a)] = (TEAL, 3.0)
        edges_of(f, pos, GRAPH_EDGES, colors=active)
        boxes = boxes_of(pos)
        for key in pos:
            x, y = pos[key]
            if key == here:
                fill, stroke = RUST, RUST
            elif key in done_set:
                fill, stroke = GREEN, TEAL
            else:
                fill, stroke = WHITE, BORDER
            if key in on_path:
                ring(f, boxes[key], TEAL, pad=5, dash=False, width=1.4)
            f.circle(x, y, R, fill, stroke, 1.8)
            f.text(x, y + 6, key, T_CELL - 1, WHITE if key == here else INK, mono=True,
                   anchor="middle")
        if failing:
            ring(f, boxes[6], RUST, pad=6, width=2.0)
            f.text(742, 292, "never reached", T_MARK, RUST, anchor="middle", bold=True,
                   layer="text")
        f.text(PAD, t + 252, "the stack", T_MARK, MUTED, layer="text")
        values = stack + ([here] if here is not None else [])
        rail_of(f, t + 274, values, x0=200, colors=[MUTED] * (len(values) - 1) + [RUST])
        if values:
            f.text(200 + len(values) * 50 + 6, t + 280, "top", T_MARK, MUTED, layer="text")
        return f

    publish("ch12-dfs.gif", frames(make, steps),
            holds(len(steps), longer=(insight_at, fail_at)))


# --------------------------------------------------------- Islands (12.7)

ISLAND_GRID = [[1, 1, 0, 0],
               [1, 0, 0, 1],
               [0, 0, 1, 1],
               [0, 0, 0, 0]]
CELL = 58
CGAP = 8
ALL_WATER = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]


def _fill(grid, r, c, mark):
    stack = [(r, c)]
    while stack:
        y, x = stack.pop()
        if y < 0 or x < 0 or y >= len(grid) or x >= len(grid[0]) or grid[y][x] != 1:
            continue
        grid[y][x] = mark
        stack.extend([(y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)])


def islands():
    """One flood fill per unvisited land cell."""
    grid = [r[:] for r in ISLAND_GRID]
    steps, count = [], 0

    def snap(values, found, scan, caption, fresh=False):
        steps.append((values, found, scan, caption, fresh))

    snap([r[:] for r in grid], 0, (0, 0),
         "Four rows by four columns. A 1 is land, a 0 is water, and land touches at its four sides.")
    for r in range(len(grid)):
        for c in range(len(grid[0])):
            if grid[r][c] == 1:
                count += 1
                snap([row[:] for row in grid], count, (r, c),
                     "The scan reaches land at row %d, column %d that nothing has marked, so this "
                     "cell opens island %d." % (r, c, count), True)
                _fill(grid, r, c, 2)
                snap([row[:] for row in grid], count, (r, c),
                     "Flood fill spreads from row %d, column %d in all four directions and marks one "
                     "whole island." % (r, c))
    snap([r[:] for r in grid], count, None,
         "Every land cell has been marked exactly once, so the grid holds %d islands." % count)
    snap([r[:] for r in ALL_WATER], 0, (0, 0),
         "An all-water grid: the scan visits every cell, finds no 1, and counts nothing.")
    insight_at, fail_at = len(steps) - 2, len(steps) - 1

    def make(step, height=None, rows=0, index=0):
        values, found, scan, line, fresh = step
        failing = index == fail_at
        size = len(values)
        span = size * CELL + (size - 1) * CGAP
        x0 = (W - span) / 2.0
        f = Frame(
            "Counting islands: one flood fill per unvisited land cell",
            sub="Water stops the fill, so each fill covers exactly one island.",
            diagram=300,
            legend=[("water", BORDER), ("new land", RUST), ("counted", TEAL)],
            step=line,
            note="The scan walks each cell once, and the fills never revisit a marked cell.",
            pairs=[("islands", found, RUST),
                   ("scan", "%d,%d" % scan if scan else "-", TEAL),
                   ("cells", size * size, MUTED)],
            insight=("Each fill consumes a whole island, so the outer scan never enters one twice. "
                     "The grid is walked once.") if index == insight_at else None,
            fails=("Zero is an answer, not a missing one. An all-water grid holds no island, and "
                   "an empty grid does too, so the counter starts at zero rather than at one."
                   ) if failing else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        y0 = t + 40
        for c in range(size):
            f.text(x0 + c * (CELL + CGAP) + CELL / 2, t + 16, "col %d" % c, T_MARK, MUTED,
                   anchor="middle", layer="text")
        for r, row_values in enumerate(values):
            f.text(x0 - 14, y0 + r * (CELL + CGAP) + CELL / 2 + 5, "row %d" % r, T_MARK,
                   MUTED, anchor="end", layer="text")
            for c, value in enumerate(row_values):
                x, y = x0 + c * (CELL + CGAP), y0 + r * (CELL + CGAP)
                if value == 0:
                    fill, stroke, color, label = GREY, BORDER, MUTED, "0"
                elif value == 1:
                    fill, stroke, color, label = WHITE, RUST, INK, "1"
                else:
                    fill, stroke, color, label = GREEN, TEAL, INK, "1"
                if fresh and scan == (r, c):
                    f.glow(x + CELL / 2, y + CELL / 2, 54, RUST, 0.45)
                f.cell(x, y, CELL, CELL, label, fill, stroke, size=T_VALUE - 2, mono=True,
                       color=color, rx=5, width=1.6 if (value == 1 or scan == (r, c)) else 1.2)
                if scan == (r, c):
                    f.rect(x - 6, y - 6, CELL + 12, CELL + 12, "none", RUST, 8, width=2.2)
        if failing:
            f.text(W / 2, y0 + span + 34, "no land anywhere, so the count stays 0", T_MARK,
                   RUST, anchor="middle", bold=True, layer="text")
        return f

    publish("ch12-islands.gif", frames(make, steps),
            holds(len(steps), longer=(insight_at, fail_at)))


# ------------------------------------------------------ Topological (12.8)

TOPO_POS = {0: (120, 112), 1: (300, 50), 2: (300, 182),
            3: (500, 112), 4: (676, 112)}
TOPO_EDGES = [(0, 1), (0, 2), (1, 3), (2, 3), (3, 4)]
CYCLE_POS = {0: (170, 96), 1: (410, 96), 2: (290, 206)}
CYCLE_EDGES = [(0, 1), (1, 2), (2, 0)]


def topo():
    """Kahn's algorithm, then the graph it cannot order."""
    edges = list(TOPO_EDGES)
    indeg = {k: 0 for k in TOPO_POS}
    for a, b in edges:
        indeg[b] += 1
    steps = [("dag", list(edges), dict(indeg), [],
              "Count the incoming edges of every node. A node with no incoming edge can go first.")]
    order = []
    while True:
        ready = sorted(k for k in TOPO_POS if indeg[k] == 0 and k not in order)
        if not ready:
            break
        take = ready[0]
        order.append(take)
        removed = [e for e in edges if e[0] == take]
        edges = [e for e in edges if e[0] != take]
        for a, b in removed:
            indeg[b] -= 1
        steps.append(("dag", list(edges), dict(indeg), list(order),
                      "Take %d, which nothing depends on, and drop its outgoing edges. %s"
                      % (take, (", ".join("%d falls to %d" % (b, indeg[b]) for _, b in removed) + ".")
                         if removed else "It had none.")))
    steps.append(("cycle", list(CYCLE_EDGES), {0: 1, 1: 1, 2: 1}, [],
                  "Now a graph with a cycle: 0 -> 1 -> 2 -> 0. Every node has an incoming edge."))
    insight_at, fail_at = len(steps) - 1, len(steps) - 1

    def make(step, height=None, rows=0, index=0):
        kind, edges_now, indeg_now, order, line = step
        cyclic = kind == "cycle"
        pos = CYCLE_POS if cyclic else TOPO_POS
        edges = CYCLE_EDGES if cyclic else TOPO_EDGES
        f = Frame(
            "Kahn's algorithm: remove the nodes that nothing depends on",
            sub="A node enters the order only when every edge into it has been removed.",
            diagram=300,
            legend=[("ordered", TEAL), ("ready now", BRASS), ("still blocked", BORDER)],
            step=line,
            note="Each edge is removed once, so the cost grows with the nodes plus the edges.",
            pairs=[("ready", len([k for k in pos if indeg_now[k] == 0 and k not in order]), BRASS),
                   ("ordered", len(order), TEAL),
                   ("left over", len(pos) - len(order), RUST if cyclic else MUTED)],
            insight=("A node enters the order only once every edge into it is gone, so a graph with "
                     "a cycle leaves nodes out.") if index == insight_at and not cyclic else None,
            fails=("The queue of ready nodes is empty and three nodes are still left. That is a "
                   "cycle, and it is the answer: this graph has no topological order."
                   ) if cyclic else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        p = {k: (x, y + t) for k, (x, y) in pos.items()}
        live = edges_now if not cyclic else CYCLE_EDGES
        arrows_of(f, p, live, width=1.6)
        boxes = boxes_of(p)
        for key in pos:
            x, y = p[key]
            if key in order:
                fill, stroke = GREEN, TEAL
            elif indeg_now[key] == 0:
                fill, stroke = CREAM, BRASS
                ring(f, boxes[key], BRASS)
            else:
                fill, stroke = WHITE, BORDER
            f.circle(x, y, R, fill, stroke, 1.8)
            f.text(x, y + 6, key, T_CELL - 1, INK, mono=True, anchor="middle")
            f.text(x, y + 40, "in %d" % indeg_now[key], T_MARK,
                   RUST if cyclic else (BRASS if indeg_now[key] == 0 else MUTED),
                   anchor="middle", mono=True, layer="text")
        if cyclic:
            for key in pos:
                cross(f, p[key][0] + 30, p[key][1] - 26, RUST, 10.0, 2.2)
        f.text(PAD, t + 272, "order", T_MARK, MUTED, layer="text")
        if order:
            rail_of(f, t + 272, list(order), x0=140, unit=36, gap=8, colors=[TEAL] * len(order))
        else:
            f.text(196, t + 278, "nothing yet", T_MARK, MUTED, mono=True, layer="text")
        return f

    publish("ch12-topo.gif", frames(make, steps),
            holds(len(steps), longer=(insight_at, fail_at)))


# ------------------------------------------------------------ Dijkstra (12.9)

DIJK_POS = {0: (140, 130), 1: (388, 48), 2: (388, 212), 3: (660, 130)}
DIJK_EDGES = [(0, 1, 4), (0, 2, 1), (2, 1, 2), (1, 3, 1), (2, 3, 5)]
DIJK_ISLAND = (760, 250)


def dijkstra():
    """Settle the closest node, then relax its edges."""
    dist = {k: float("inf") for k in DIJK_POS}
    dist[0] = 0
    settled, steps = [], []
    while len(settled) < len(DIJK_POS):
        here = min((k for k in DIJK_POS if k not in settled), key=lambda k: dist[k])
        settled.append(here)
        relaxed = []
        for a, b, w in DIJK_EDGES:
            other = b if a == here else (a if b == here else None)
            if other is None or other in settled:
                continue
            if dist[here] + w < dist[other]:
                old = dist[other]
                dist[other] = dist[here] + w
                relaxed.append((other, old, dist[other]))
        steps.append((set(settled), dict(dist), here, relaxed,
                      "Settle %d at distance %d. %s" % (here, dist[here],
                       ("Relax %s." % ", ".join("%d: %s -> %d" % (o, "inf" if o_ == float("inf") else o_, n)
                                                for o, o_, n in relaxed)) if relaxed
                       else "No neighbour of it improves.")))
    steps.append((set(settled), {k: dist[k] for k in DIJK_POS}, None, [],
                  "Now a second component, node 9, with no edge from any settled node."))
    insight_at, fail_at = len(steps) - 2, len(steps) - 1

    def make(step, height=None, rows=0, index=0):
        settled, d, here, relaxed, line = step
        failing = here is None
        f = Frame(
            "Dijkstra's algorithm: settle the closest node, then relax its edges",
            sub="A node's distance is final the moment it is the closest unsettled one.",
            diagram=290,
            legend=[("settled", TEAL), ("just relaxed", BRASS), ("unsettled", BORDER)],
            step=line,
            note="Relaxing an edge lowers a neighbour's distance when the new route is shorter.",
            pairs=[("settle", here if here is not None else "-", RUST),
                   ("distance", "inf" if failing or d.get(here, float("inf")) == float("inf")
                    else d[here], INK),
                   ("settled", len(settled), TEAL)],
            insight=("The closest unsettled node is already final: any other route to it is farther."
                     ) if index == insight_at else None,
            fails=("A node with no route from the start keeps a distance of infinity. That is the "
                   "answer: unreachable, and the algorithm never settles it.") if failing else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        pos = {k: (x, y + t) for k, (x, y) in DIJK_POS.items()}
        if failing:
            pos[9] = (DIJK_ISLAND[0], DIJK_ISLAND[1] + t)
        live = [(a, b) for a, b, _ in DIJK_EDGES]
        relaxed_set = {o for o, _, _ in relaxed}
        active = {}
        for a, b, w in DIJK_EDGES:
            if here is not None and here in (a, b):
                other = b if a == here else a
                if other in relaxed_set:
                    active[(a, b)] = (BRASS, 3.2)
        edges_of(f, pos, live, colors=active)
        for a, b, w in DIJK_EDGES:
            x, y = (pos[a][0] + pos[b][0]) / 2, (pos[a][1] + pos[b][1]) / 2
            f.text(x, y - 6, str(w), T_MARK, MUTED, mono=True, anchor="middle", halo=True)
        for key in pos:
            x, y = pos[key]
            if failing and key == 9:
                ring(f, (x - R, y - R, 2 * R, 2 * R), RUST, pad=6, width=2.0)
                fill, stroke = WHITE, RUST
            elif key in settled:
                fill, stroke = GREEN, TEAL
            else:
                fill, stroke = WHITE, BORDER
            if key == here:
                f.glow(x, y, 46, TEAL, 0.4)
            f.circle(x, y, R, fill, stroke, 1.8)
            f.text(x, y + 6, key, T_CELL - 1, INK, mono=True, anchor="middle")
            label = "inf" if failing and key == 9 else (
                "inf" if d.get(key, float("inf")) == float("inf") else str(d[key]))
            f.text(x, y - 34, label, T_MARK,
                   RUST if label == "inf" else (TEAL if key in settled else MUTED),
                   anchor="middle", mono=True, bold=label == "inf", layer="text")
        if failing:
            f.text(DIJK_ISLAND[0], DIJK_ISLAND[1] + t + 44, "unreachable", T_MARK, RUST,
                   anchor="middle", bold=True, layer="text")
        return f

    publish("ch12-dijkstra.gif", frames(make, steps),
            holds(len(steps), longer=(insight_at, fail_at)))


# ------------------------------------------------------------- Kruskal (12.10)

KRUSKAL_POS = {0: (120, 130), 1: (330, 48), 2: (330, 212), 3: (546, 130), 4: (712, 130)}
KRUSKAL_EDGES = [(0, 1, 4), (0, 2, 3), (1, 2, 1), (1, 3, 2), (2, 3, 4), (3, 4, 2)]
SPLIT_POS = {0: (170, 110), 1: (330, 110), 2: (560, 110), 3: (720, 110)}
SPLIT_EDGES = [(0, 1, 1), (2, 3, 2)]


def kruskal():
    """Take the cheapest edge that does not close a cycle."""
    parent = {k: k for k in KRUSKAL_POS}

    def find(a):
        while parent[a] != a:
            a = parent[a]
        return a

    steps, kept, total = [], [], 0
    for a, b, w in sorted(KRUSKAL_EDGES, key=lambda e: e[2]):
        ra, rb = find(a), find(b)
        same = ra == rb
        if not same:
            parent[ra] = rb
            kept.append((a, b, w))
            total += w
        steps.append((list(kept), (a, b, w), "skip" if same else "keep", total, None, None,
                      "Edge %d-%d of weight %d %s."
                      % (a, b, w,
                         "joins two nodes that are already connected, so it would close a cycle"
                         if same else "joins two separate groups, so it is kept")))
    steps.append((list(kept), None, "done", total, None, None,
                  "Four edges connect all five nodes with no cycle, for a total weight of %d." % total))
    steps.append(([(0, 1, 1), (2, 3, 2)], None, "split", 3, SPLIT_POS, SPLIT_EDGES,
                  "Now a graph in two pieces. The cheapest edges still form a forest, not one tree."))
    insight_at, fail_at = len(steps) - 2, len(steps) - 1

    def make(step, height=None, rows=0, index=0):
        kept, edge, kind, total, alt_pos, alt_edges, line = step
        split = kind == "split"
        pos = alt_pos if split else KRUSKAL_POS
        pool = alt_edges if split else KRUSKAL_EDGES
        f = Frame(
            "Kruskal's algorithm: take the cheapest edge that closes no cycle",
            sub="The edges are sorted by weight first. A union-find test decides each one.",
            diagram=280,
            legend=[("kept", TEAL), ("skipped", RUST), ("still to offer", BORDER)],
            step=line,
            note="Sorting costs O(E log E). The union-find test is what keeps the result a tree.",
            pairs=[("edge", "%d-%d" % (edge[0], edge[1]) if edge else "-", RUST),
                   ("total", total, TEAL),
                   ("parts", 2 if split else 1, RUST if split else INK)],
            insight=("The union-find test is what turns a greedy walk into a spanning tree."
                     ) if index == insight_at else None,
            fails=("With two components there is no spanning tree to find. The algorithm returns a "
                   "minimum spanning forest, and a spanning tree only exists for a connected graph."
                   ) if split else None,
            at=(index, len(steps)),
            height=height, insight_rows=rows,
        )
        t = f.top
        p = {k: (x, y + t) for k, (x, y) in pos.items()}
        kept_set = {(a, b) for a, b, _ in kept}
        colors = {e: (TEAL, 3.6) for e in kept_set}
        edges_of(f, p, [(a, b) for a, b, _ in pool], colors=colors)
        boxes = boxes_of(p)
        if edge is not None:
            a, b, w = edge
            ax, ay = box_edge(boxes[a], p[b])
            bx, by = box_edge(boxes[b], p[a])
            f.line(ax, ay, bx, by, RUST if kind == "skip" else BRASS, 3.6, dash=(kind == "skip"))
        for key in p:
            x, y = p[key]
            on = any(key in (a, b) for a, b, _ in kept)
            f.circle(x, y, R, GREEN if on else WHITE, INK if on else BORDER, 1.8)
            f.text(x, y + 6, key, T_CELL - 1, INK, mono=True, anchor="middle")
        for a, b, w in pool:
            x, y = (p[a][0] + p[b][0]) / 2, (p[a][1] + p[b][1]) / 2
            f.text(x, y - 6, str(w), T_MARK, MUTED, mono=True, anchor="middle", halo=True)
        if split:
            gap = (p[1][0] + p[2][0]) / 2
            f.line(gap, t + 40, gap, t + 200, RUST, 1.6, dash=True)
            f.text(gap, t + 220, "no edge crosses here", T_MARK, RUST, anchor="middle",
                   bold=True, layer="text")
        return f

    publish("ch12-kruskal.gif", frames(make, steps),
            holds(len(steps), longer=(insight_at, fail_at)))


BUILDERS = {
    "bst": bst,
    "trie": trie,
    "bfs": bfs,
    "dfs": dfs,
    "islands": islands,
    "topo": topo,
    "dijkstra": dijkstra,
    "kruskal": kruskal,
}
