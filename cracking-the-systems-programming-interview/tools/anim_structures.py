"""Animations for the tree and graph chapters, chapters 11 and 12.

Every frame is one step of the algorithm the chapter quotes: one insertion, one
node taken off the queue, one edge kept or skipped. Colours carry the state, and
every animation that leans on a colour carries a legend that names it:

  * pale   not reached yet
  * cream  waiting in the frontier, or the thing being examined now
  * green  settled, visited, or kept
  * grey   ruled out

Positions are written relative to `Frame.top`, the top of the drawing area, so a
frame can grow or shrink at the foot without moving the picture.
"""

import math

from animlib import *  # noqa: F401,F403
from animlib import Frame, frames, publish

NW, NH = 48, 38          # a graph node


def node(f, x, y, label, fill=PALE, stroke=INK, size=T_CELL - 1, w=NW, h=NH, layer="art"):
    f.cell(x - w / 2, y - h / 2, w, h, label, fill, stroke, size=size, mono=True, layer=layer)
    return (x - w / 2, y - h / 2, w, h)


def boxes_of(pos, w=NW, h=NH):
    return {k: (x - w / 2, y - h / 2, w, h) for k, (x, y) in pos.items()}


def graph(f, pos, edges, w=NW, h=NH, edge=BORDER, width=1.8, directed=False, edge_colors=None,
          ghosts=()):
    """Draw a graph: the edges first, then the labelled nodes on top.

    `ghosts` are edges drawn faint and dashed, for an edge that has just been
    taken out of the picture.
    """
    boxes = boxes_of(pos, w, h)
    for a, b in edges:
        ax, ay = box_edge(boxes[a], pos[b])
        bx, by = box_edge(boxes[b], pos[a])
        color, weight = (edge_colors or {}).get((a, b), (edge, width))
        if directed:
            f.arrow(ax, ay, bx, by, color, weight, head=9.0)
        else:
            f.line(ax, ay, bx, by, color, weight)
    for a, b in ghosts:
        ax, ay = box_edge(boxes[a], pos[b])
        bx, by = box_edge(boxes[b], pos[a])
        f.line(ax, ay, bx, by, BORDER, 1.6, dash=True, opacity=0.8)
    return boxes


def ring(f, box, color=BRASS, pad=6, width=2.0, dash=True):
    """A dashed halo around a node: this one is in the frontier."""
    x, y, w, h = box
    f.rect(x - pad, y - pad, w + 2 * pad, h + 2 * pad, "none", color, 10, width=width, dash=dash)


# ---------------------------------------------------- Binary search tree (11.3)

BST_POS = {8: (410, 42), 3: (232, 108), 10: (594, 108),
           1: (120, 176), 6: (330, 176), 14: (700, 176), 13: (626, 242)}
BST_EDGES = [(8, 3), (8, 10), (3, 1), (3, 6), (10, 14), (14, 13)]


def bst():
    """Insert seven values, then search for 6."""
    order = [8, 3, 10, 1, 6, 14, 13]
    tree, root, steps = {}, None, []
    for value in order:
        if root is None:
            root = value
            tree[value] = [None, None]
            steps.append((set(tree), [value], value,
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
        steps.append((set(tree), path + [value], value,
                      "Insert %d: %s, so it hangs off %d on the %s."
                      % (value, " -> ".join(str(v) for v in path), path[-1], way)))
    for i, value in enumerate([8, 3, 6]):
        if value == 6:
            text = "Search for 6: compare with 6. Equal, so the value is found after three comparisons."
        elif 6 < value:
            text = "Search for 6: 6 is less than %d, so only the left subtree can hold it." % value
        else:
            text = "Search for 6: 6 is greater than %d, so only the right subtree can hold it." % value
        steps.append((set(tree), [8, 3, 6][:i + 1], value, text, "search"))

    def make(step, height=None, insight_rows=0):
        placed, path, value = step[0], step[1], step[2]
        searching = len(step) == 5
        last = step is steps[-1]
        f = Frame(
            "A binary search tree: the ordering decides which way to go",
            sub="Every node is larger than the whole of its left subtree, and smaller than its right.",
            diagram=290,
            legend=[("on the path", CREAM, TEAL), ("placed", GREEN, TEAL), ("not yet placed", GREY, BORDER)],
            step=step[3],
            note="The tree keeps one value per node. A search visits one node per level.",
            pairs=[("value", value, RUST), ("comparisons", len(path), TEAL),
                   ("nodes", len(placed), INK)],
            insight=("Each comparison discards a whole subtree, so a search costs the height."
                     ) if last else None,
            height=height, insight_rows=insight_rows,
        )
        t = f.top
        pos = {k: (x, y + t) for k, (x, y) in BST_POS.items()}
        path_edges = [(a, b) for a, b in BST_EDGES
                      if a in path and b in path and BST_POS[a][1] == BST_POS[b][1] - 66]
        edge_colors = {e: (TEAL, 3.0) for e in path_edges}
        live_edges = [(a, b) for a, b in BST_EDGES if a in placed and b in placed]
        boxes = graph(f, pos, live_edges, edge_colors=edge_colors)
        for k in BST_POS:
            if k not in placed:
                continue
            x, y = pos[k]
            fill, stroke = (GREEN, TEAL) if k in placed else (GREY, BORDER)
            if k in path:
                fill, stroke = CREAM, TEAL
            if k == path[-1] and not searching:
                f.glow(x, y, 52, BRASS, 0.45)
            node(f, x, y, k, fill, stroke)
        return f

    publish("ch11-bst.gif", frames(make, steps), [2100] * len(steps))


# --------------------------------------------------------------- Trie (11.6)

TRIE_POS = {"": (410, 42), "c": (296, 108), "d": (566, 108),
            "ca": (240, 176), "do": (566, 176),
            "cat": (156, 244), "car": (300, 244), "dog": (566, 244)}
TRIE_EDGES = [("", "c"), ("", "d"), ("c", "ca"), ("ca", "cat"), ("ca", "car"),
              ("d", "do"), ("do", "dog")]
TRIE_WORDS = ("cat", "car", "dog")


def trie():
    """Insert cat, car, and dog one character at a time, then look for ca and cab."""
    created = {""}
    steps = []
    for word in TRIE_WORDS:
        for i in range(1, len(word) + 1):
            prefix = word[:i]
            fresh = prefix not in created
            created.add(prefix)
            steps.append((prefix, word, set(created), "/".join(["root"] + [word[:j] for j in range(1, i + 1)]),
                          "Insert \"%s\": %s, and this node %s."
                          % (word,
                             "there is no edge for '%s', so a new one is added" % prefix[-1] if fresh
                             else "the edge for '%s' already exists, so the walk follows it" % prefix[-1],
                             "ends the word" if i == len(word) else "carries the walk on")))
    for query in ("ca", "cab"):
        for i in range(1, len(query) + 1):
            prefix = query[:i]
            if prefix not in created:
                steps.append((prefix[:-1], query, set(created),
                              "/".join(["root"] + [query[:j] for j in range(1, i)]),
                              "Look up \"%s\": there is no edge for '%s', so the walk stops and "
                              "reports that the key is missing." % (query, prefix[-1])))
                break
            steps.append((prefix, query, set(created),
                          "/".join(["root"] + [query[:j] for j in range(1, i + 1)]),
                          "Look up \"%s\": follow the edge for '%s' to the node \"%s\"."
                          % (query, prefix[-1], prefix)))
        else:
            steps.append((query, query, set(created),
                          "/".join(["root"] + [query[:j] for j in range(1, len(query) + 1)]),
                          "Look up \"%s\": the walk reaches a node that ends a stored word, so \"%s\" "
                          "is in the trie." % (query, query)))

    def make(step, height=None, insight_rows=0):
        prefix, word, live, walk, line = step
        last = step is steps[-1]
        f = Frame(
            "A trie: every edge is one character, so prefixes are shared",
            sub="A word is stored by walking its characters from the root.",
            diagram=300,
            legend=[("the walk", GREEN, TEAL), ("ends a word", WHITE, BRASS)],
            step=line,
            note="One node per distinct prefix, not one node per word.",
            pairs=[("walk", walk, TEAL), ("word", "\"%s\"" % word, RUST),
                   ("ends a word", "yes" if prefix in TRIE_WORDS else "no", INK)],
            insight=("cat and car share the node for \"ca\", so a lookup costs the key length."
                     ) if last else None,
            height=height, insight_rows=insight_rows,
        )
        t = f.top
        pos = {k: (x, y + t) for k, (x, y) in TRIE_POS.items() if k in live}
        edges = [(a, b) for a, b in TRIE_EDGES if a in live and b in live]
        boxes = graph(f, pos, edges, directed=True)
        for key in pos:
            on = key and (prefix == key or prefix.startswith(key))
            f.cell(*boxes[key], ("root" if key == "" else key),
                   GREEN if on else PALE, TEAL if on else BORDER, size=T_CELL - 3, mono=True)
        for stored in TRIE_WORDS:
            if stored in live:
                ring(f, boxes[stored], BRASS, pad=4, dash=False)
        return f

    publish("ch11-trie.gif", frames(make, steps), [1900] * len(steps))


# ------------------------------------------------------- Breadth first (12.3)

GRAPH_POS = {0: (120, 120), 1: (286, 58), 2: (286, 182),
             3: (462, 58), 4: (462, 182), 5: (628, 120)}
GRAPH_EDGES = [(0, 1), (0, 2), (1, 3), (2, 3), (2, 4), (3, 5), (4, 5)]
ADJ = {0: [1, 2], 1: [0, 3], 2: [0, 3, 4], 3: [1, 2, 5], 4: [2, 5], 5: [3, 4]}


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
                  "The queue is empty, so every reachable node has been visited."))
    return steps


def bfs():
    """A queue visits nodes in rings around the start."""
    steps = _bfs_steps(0)

    def make(step, height=None, insight_rows=0):
        queue, seen, done, here, line = step
        last = step is steps[-1]
        f = Frame(
            "Breadth-first search: a queue visits nodes in rings",
            sub="Every neighbour of the current node is queued before any of their neighbours.",
            diagram=300,
            legend=[("visited", GREEN, TEAL), ("in the queue", CREAM, BRASS), ("not seen", PALE, INK)],
            step=line,
            note="The queue is the frontier: it holds the nodes one edge away from what is visited.",
            pairs=[("visiting", here if here is not None else "-", RUST),
                   ("in queue", len(queue), BRASS), ("visited", len(done), TEAL)],
            insight=("The queue holds the frontier, so distance d is finished before distance d+1."
                     ) if last else None,
            height=height, insight_rows=insight_rows,
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
                fills[key], strokes[key] = PALE, INK
        boxes = graph(f, pos, GRAPH_EDGES)
        for key, box in boxes.items():
            if key in queue:
                ring(f, box, BRASS)
            if key == here:
                f.glow(pos[key][0], pos[key][1], 54, RUST, 0.4)
            f.cell(*box, key, fills[key], RUST if key == here else strokes[key],
                   size=T_CELL - 1, mono=True)

        # The queue itself, so the frontier is a thing the reader can see.
        y = t + 236
        f.text(PAD, y + 22, "the queue", T_CHIP, MUTED)
        start_x = 200
        if queue:
            row(f, start_x, y, 46, 38, queue, gap=8, size=T_CELL - 2,
                fills=[CREAM] * len(queue), strokes=[BRASS] * len(queue))
        else:
            f.rect(start_x, y, 46, 38, WHITE, BORDER, 4, dash=True)
            f.text(start_x + 23, y + 26, "-", T_CHIP, MUTED, anchor="middle")
        f.text(start_x + max(1, len(queue)) * 54 - 8 + 22, y + 26, "front of the queue", T_CHIP, MUTED)
        return f

    publish("ch12-bfs.gif", frames(make, steps), [2100] * len(steps))


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
                  "Every node has been visited once. The stack is empty, so the recursion is done."))
    return steps


def dfs():
    """One branch of the graph at a time, following the call stack."""
    steps = _dfs_steps(0)

    def make(step, height=None, insight_rows=0):
        done, stack, here, line = step
        last = step is steps[-1]
        f = Frame(
            "Depth-first search: follow one edge as far as it goes",
            sub="The recursion returns only when the current node has no unseen neighbour left.",
            diagram=300,
            legend=[("visited", GREEN, TEAL), ("being explored", RUST, RUST), ("not seen", PALE, INK)],
            step=line,
            note="The stack is the path from the start to the node being explored.",
            pairs=[("visiting", here if here is not None else "-", RUST),
                   ("stack", len(stack), BRASS), ("visited", len(done), TEAL)],
            insight=("The call stack is the path from the start, so memory follows the "
                     "longest path.") if last else None,
            height=height, insight_rows=insight_rows,
        )
        t = f.top
        pos = {k: (x, y + t) for k, (x, y) in GRAPH_POS.items()}
        done_set = set(done)
        fills, strokes = {}, {}
        for key in pos:
            if key == here:
                fills[key], strokes[key] = RUST, RUST
            elif key in done_set:
                fills[key], strokes[key] = GREEN, TEAL
            else:
                fills[key], strokes[key] = PALE, INK
        on_path = set(stack) | ({here} if here is not None else set())
        edge_colors = {}
        for i, a in enumerate(stack):
            b = here if i == len(stack) - 1 else stack[i + 1] if i + 1 < len(stack) else None
            if b is not None:
                edge_colors[(a, b)] = (TEAL, 3.2)
                edge_colors[(b, a)] = (TEAL, 3.2)
        boxes = graph(f, pos, GRAPH_EDGES, edge_colors=edge_colors)
        for key, box in boxes.items():
            if key in on_path:
                ring(f, box, TEAL, dash=False, width=1.6)
            f.cell(*box, key, fills[key], strokes[key],
                   size=T_CELL - 1, mono=True, color=WHITE if key == here else INK)

        y = t + 236
        f.text(PAD, y + 22, "the stack", T_CHIP, MUTED)
        start_x = 200
        if stack or here is not None:
            values = stack + ([here] if here is not None else [])
            row(f, start_x, y, 46, 38, values, gap=8, size=T_CELL - 2,
                fills=[PALE] * (len(values) - 1) + [RUST], strokes=[BORDER] * (len(values) - 1) + [RUST],
                colors=[INK] * (len(values) - 1) + [WHITE])
        else:
            f.rect(start_x, y, 46, 38, WHITE, BORDER, 4, dash=True)
            f.text(start_x + 23, y + 26, "-", T_CHIP, MUTED, anchor="middle")
        f.text(start_x + max(1, len(stack) + 1) * 54 - 8 + 22, y + 26, "top of the stack", T_CHIP, MUTED)
        return f

    publish("ch12-dfs.gif", frames(make, steps), [1900] * len(steps))


# --------------------------------------------------------- Islands (12.7)

ISLAND_GRID = [[1, 1, 0, 0],
               [1, 0, 0, 1],
               [0, 0, 1, 1],
               [0, 0, 0, 0]]
CELL = 68
CGAP = 8


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

    def snap(found, scan, caption, glow=None, fresh=False):
        steps.append(([r[:] for r in grid], found, scan, caption, glow, fresh))

    snap(0, (0, 0), "Four rows by four columns. A 1 is land, a 0 is water, and land touches at its four sides.")
    for r in range(len(grid)):
        for c in range(len(grid[0])):
            if grid[r][c] == 1:
                count += 1
                snap(count, (r, c),
                     "The scan reaches land at row %d, column %d that nothing has marked yet, so this "
                     "cell opens island %d." % (r, c, count), (r, c))
                _fill(grid, r, c, 2)
                snap(count, (r, c),
                     "Flood fill spreads from row %d, column %d in all four directions and marks "
                     "one whole island." % (r, c), (r, c))
    snap(count, None, "Every land cell has been marked exactly once, so the grid holds %d islands." % count)

    def make(step, height=None, insight_rows=0):
        values, found, scan, line, glow_at, fresh = step
        last = step is steps[-1]
        f = Frame(
            "Counting islands: one flood fill per unvisited land cell",
            sub="Water stops the fill, so each fill covers exactly one island.",
            diagram=340,
            legend=[("water", GREY, BORDER), ("new land", CREAM, RUST), ("already counted", GREEN, TEAL)],
            step=line,
            note="The scan walks each cell once, and the fills never revisit a marked cell.",
            pairs=[("islands", found, RUST), ("scan", "%d,%d" % scan if scan else "-", TEAL)],
            insight=("Each fill consumes a whole island, so every cell of the grid is visited once."
                     ) if last else None,
            height=height, insight_rows=insight_rows,
        )
        t = f.top
        x0 = (W - (4 * CELL + 3 * CGAP)) / 2.0
        for c in range(4):
            f.text(x0 + c * (CELL + CGAP) + CELL / 2, t + 8, "col %d" % c, T_CHIP, MUTED,
                   anchor="middle")
        for r, row_values in enumerate(values):
            f.text(x0 - 14, t + 42 + r * (CELL + CGAP) + CELL / 2 + 5, "row %d" % r, T_CHIP,
                   MUTED, anchor="end")
            for c, value in enumerate(row_values):
                x, y = x0 + c * (CELL + CGAP), t + 42 + r * (CELL + CGAP)
                if value == 0:
                    fill, stroke, color, label = GREY, BORDER, MUTED, "0"
                elif value == 1:
                    fill, stroke, color, label = CREAM, RUST, INK, "1"
                else:
                    fill, stroke, color, label = GREEN, TEAL, INK, "1"
                if glow_at == (r, c):
                    f.glow(x + CELL / 2, y + CELL / 2, 64, RUST, 0.5 if fresh else 0.3)
                f.cell(x, y, CELL, CELL, label, fill, stroke, size=T_CELL, mono=True, color=color)
                if scan == (r, c):
                    f.rect(x - 6, y - 6, CELL + 12, CELL + 12, "none", RUST, 10, width=2.2,
                           dash=True)
        return f

    publish("ch12-islands.gif", frames(make, steps), [2400] * len(steps))


# ------------------------------------------------------ Topological (12.8)

TOPO_POS = {0: (120, 120), 1: (300, 58), 2: (300, 190),
            3: (500, 120), 4: (676, 120)}
TOPO_EDGES = [(0, 1), (0, 2), (1, 3), (2, 3), (3, 4)]


def topo():
    """Kahn's algorithm: take the nodes nothing depends on."""
    edges = list(TOPO_EDGES)
    indeg = {k: 0 for k in TOPO_POS}
    for a, b in edges:
        indeg[b] += 1
    steps = [(list(edges), dict(indeg), [], [],
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
        steps.append((list(edges), dict(indeg), list(order), removed,
                      "Take %d, which nothing depends on, and drop its outgoing edges. %s"
                      % (take, (", ".join("%d falls to %d" % (b, indeg[b]) for _, b in removed)
                                + ".") if removed else "It had none.")))

    def make(step, height=None, insight_rows=0):
        edges_now, indeg_now, order, removed, line = step
        last = step is steps[-1]
        f = Frame(
            "Kahn's algorithm: remove the nodes that nothing depends on",
            sub="A node enters the order only when every edge into it has been removed.",
            diagram=250,
            legend=[("ordered", GREEN, TEAL), ("ready now", CREAM, BRASS), ("still blocked", PALE, INK)],
            step=line,
            note="Each edge is removed once, so the cost grows with the nodes plus the edges.",
            pairs=[("take", order[-1] if order else "-", RUST),
                   ("ready", len([k for k in TOPO_POS if indeg_now[k] == 0 and k not in order]), BRASS),
                   ("order", " ".join(str(v) for v in order) or "-", TEAL)],
            insight=("A node waits for every edge into it, so a cycle leaves nodes unordered."
                     ) if last else None,
            height=height, insight_rows=insight_rows,
        )
        t = f.top
        pos = {k: (x, y + t) for k, (x, y) in TOPO_POS.items()}
        boxes = graph(f, pos, edges_now, directed=True)
        for a, b in removed:
            ax, ay = box_edge(boxes[a], pos[b])
            bx, by = box_edge(boxes[b], pos[a])
            f.line(ax, ay, bx, by, BORDER, 1.6, dash=True, opacity=0.8)
        for key, box in boxes.items():
            if key in order:
                fill, stroke = GREEN, TEAL
            elif indeg_now[key] == 0:
                fill, stroke = CREAM, BRASS
                ring(f, box, BRASS, pad=5, width=1.8)
            else:
                fill, stroke = PALE, INK
            f.cell(*box, key, fill, stroke, size=T_CELL - 1, mono=True)
            f.text(pos[key][0], pos[key][1] + 40, "in %d" % indeg_now[key], T_CHIP,
                   BRASS if indeg_now[key] == 0 and key not in order else MUTED,
                   anchor="middle", mono=True)
        return f

    publish("ch12-topo.gif", frames(make, steps), [2300] * len(steps))


# ------------------------------------------------------------ Dijkstra (12.9)

DIJK_POS = {0: (140, 140), 1: (388, 56), 2: (388, 224), 3: (660, 140)}
DIJK_EDGES = [(0, 1, 4), (0, 2, 1), (2, 1, 2), (1, 3, 1), (2, 3, 5)]


def dijkstra():
    """Settle the closest node, then relax its edges."""
    dist = {k: math.inf for k in DIJK_POS}
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
                       ("Relax %s." % ", ".join("%d: %s -> %d" % (o, "inf" if o_ == math.inf else o_, n)
                                                for o, o_, n in relaxed)) if relaxed
                       else "No neighbour of it improves.")))

    def make(step, height=None, insight_rows=0):
        settled, dist, here, relaxed, line = step
        last = step is steps[-1]
        f = Frame(
            "Dijkstra's algorithm: settle the closest node, then relax its edges",
            sub="A node's distance is final the moment it is the closest unsettled one.",
            diagram=300,
            legend=[("settled", GREEN, TEAL), ("just relaxed", CREAM, BRASS), ("unsettled", PALE, INK)],
            step=line,
            note="Relaxing an edge lowers a neighbour's distance when the new route is shorter.",
            pairs=[("settle", here, RUST),
                   ("distance", "inf" if dist[here] == math.inf else dist[here], INK),
                   ("settled", len(settled), TEAL)],
            insight=("The closest unsettled node is already final: any other route to it is "
                     "farther.") if last else None,
            height=height, insight_rows=insight_rows,
        )
        t = f.top
        pos = {k: (x, y + t) for k, (x, y) in DIJK_POS.items()}
        relaxed_set = {o for o, _, _ in relaxed}
        edge_colors = {}
        for a, b, w in DIJK_EDGES:
            if a == here or b == here:
                other = b if a == here else a
                if other in relaxed_set:
                    edge_colors[(a, b)] = (BRASS, 3.4)
        boxes = graph(f, pos, DIJK_EDGES and [(a, b) for a, b, _ in DIJK_EDGES],
                      edge_colors=edge_colors)
        for a, b, w in DIJK_EDGES:
            x, y = (pos[a][0] + pos[b][0]) / 2, (pos[a][1] + pos[b][1]) / 2
            f.text(x, y - 8, str(w), T_CHIP, BRASS, mono=True, anchor="middle", halo=True)
        for key, box in boxes.items():
            if key in settled:
                fill, stroke = GREEN, TEAL
            else:
                fill, stroke = PALE, INK
            if key == here:
                f.glow(pos[key][0], pos[key][1], 58, TEAL, 0.45)
            f.cell(*box, key, fill, stroke, size=T_CELL - 1, mono=True)
            label = "inf" if dist[key] == math.inf else str(dist[key])
            f.text(pos[key][0] + 40, pos[key][1] - 24, "d = %s" % label, T_CHIP,
                   TEAL if key in settled else (BRASS if key in relaxed_set else MUTED), mono=True)
        return f

    publish("ch12-dijkstra.gif", frames(make, steps), [2700] * len(steps))


# ------------------------------------------------------------- Kruskal (12.10)

KRUSKAL_POS = {0: (120, 140), 1: (330, 58), 2: (330, 224), 3: (546, 140), 4: (712, 140)}
KRUSKAL_EDGES = [(0, 1, 4), (0, 2, 3), (1, 2, 1), (1, 3, 2), (2, 3, 4), (3, 4, 2)]


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
        steps.append((list(kept), (a, b, w), "skip" if same else "keep", total,
                      "Edge %d-%d of weight %d %s. %s"
                      % (a, b, w,
                         "joins two nodes that are already connected, so it would close a cycle"
                         if same else "joins two separate groups, so it is kept",
                         "Total weight is still %d." % total if same else "Total weight becomes %d." % total)))
    steps.append((list(kept), None, "done", total,
                  "Four edges connect all five nodes with no cycle, for a total weight of %d." % total))

    def make(step, height=None, insight_rows=0):
        kept, edge, kind, total, line = step
        last = step is steps[-1]
        order = sorted(KRUSKAL_EDGES, key=lambda e: e[2])
        f = Frame(
            "Kruskal's algorithm: take the cheapest edge that closes no cycle",
            sub="The edges are sorted by weight first. A union-find test decides each one.",
            diagram=300,
            legend=[("kept", TEAL, TEAL), ("skipped", WHITE, RUST), ("still to offer", BORDER, BORDER)],
            step=line,
            note="Sorting costs O(E log E). The union-find test is what keeps the result a tree.",
            pairs=[("edge", "%d-%d" % (edge[0], edge[1]) if edge else "-", RUST),
                   ("weight", edge[2] if edge else "-", INK),
                   ("total", total, TEAL)],
            insight=("The union-find test is what turns a greedy walk into a spanning tree."
                     ) if last else None,
            height=height, insight_rows=insight_rows,
        )
        t = f.top
        # The sorted offer list, so the order of the decisions is visible.
        y = t - 2
        f.text(PAD, y + 20, "offered cheapest first", T_CHIP, MUTED)
        row(f, 230, y, 74, 38, ["%d-%d : %d" % e for e in order], gap=8, size=T_CHIP + 1,
            mono=True,
            fills=[CREAM if edge and (e[0], e[1]) == (edge[0], edge[1]) else
                   (GREEN if e in kept else WHITE) for e in order],
            strokes=[RUST if edge and (e[0], e[1]) == (edge[0], edge[1]) else
                     (TEAL if e in kept else BORDER) for e in order],
            colors=[RUST if edge and (e[0], e[1]) == (edge[0], edge[1]) else INK for e in order])

        pos = {k: (x, yy + t + 66) for k, (x, yy) in KRUSKAL_POS.items()}
        kept_set = {(a, b) for a, b, _ in kept}
        edge_colors = {}
        for a, b, w in KRUSKAL_EDGES:
            if (a, b) in kept_set:
                edge_colors[(a, b)] = (TEAL, 4.0)
        boxes = graph(f, pos, [(a, b) for a, b, _ in KRUSKAL_EDGES], edge_colors=edge_colors)
        if edge is not None:
            a, b, w = edge
            color = RUST if kind == "skip" else BRASS
            ax, ay = box_edge(boxes[a], pos[b])
            bx, by = box_edge(boxes[b], pos[a])
            f.line(ax, ay, bx, by, color, 4.0, dash=(kind == "skip"))
        for key, box in boxes.items():
            on = any(key in (a, b) for a, b, _ in kept)
            f.cell(*box, key, GREEN if on else PALE, INK, size=T_CELL - 1, mono=True)
        for a, b, w in KRUSKAL_EDGES:
            x, yy = (pos[a][0] + pos[b][0]) / 2, (pos[a][1] + pos[b][1]) / 2
            f.text(x, yy - 6, str(w), T_CHIP, MUTED, mono=True, anchor="middle", halo=True)
        return f

    publish("ch12-kruskal.gif", frames(make, steps), [2300] * len(steps))


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
