"""The chapter 12 animations (ch12-graphs.md), drawn with `motion`.

    python3 tools/animations.py bfs dfs islands topo dijkstra kruskal
"""

from motion import (BRASS, BRASS_LT, FAINT, INK, LINE, MUTED, PAPER, RUST, RUST_LT, TEAL,
                    TEAL_LT, W, caption, chip, code_panel, progress, render, title_block)
from motion_kit import NAVY, edge, layout, line_of, node, play, source

GRAPH_POS = {0: (120, 186), 1: (280, 120), 2: (280, 252), 3: (440, 120), 4: (440, 252), 5: (600, 186),
             6: (720, 252)}
GRAPH_EDGES = [(0, 1), (0, 2), (1, 3), (2, 3), (2, 4), (3, 5), (4, 5)]
ADJ = {k: [] for k in GRAPH_POS}
for a, b in GRAPH_EDGES:
    ADJ[a].append(b)
    ADJ[b].append(a)
for k in ADJ:
    ADJ[k].sort()


def furniture(p, tl, t, total, title, sub, code_title, code, line, cap_y, rail_y, code_y,
              tint=TEAL, size=11.0, lead=15.6, strike=-1.0):
    title_block(p, title, sub)
    code_panel(p, 26, code_y, W - 52, code_title, code, line, size=size, lead=lead,
               tint=RUST if strike >= 0 else tint, reveal=tl.reached("code", t),
               strike=int(strike) if strike >= 0 else None)
    caption(p, tl, t, cap_y)
    progress(p, tl, t, total, rail_y)


def lane(p, x, y, title, items, color=NAVY, hot_first=False, width=None):
    """A queue or stack drawn as a row of chips."""
    p.text(x, y, title, 12, MUTED, 600)
    cx = x
    for k, it in enumerate(items):
        first = hot_first and k == 0
        w = chip(p, cx + 0, y + 26, str(it), BRASS if first else color, BRASS_LT if first else PAPER, 13,
                 anchor="start")
        cx += w + 8
    if not items:
        p.text(x, y + 30, "empty", 13, FAINT, 400, mono=True)


def draw_graph(p, pos, edges, s_visited, s_frontier, s_at, hot_edges=(), r=22, labels=None, weights=None,
               dist=None, skip_edges=(), kept_edges=()):
    for a, b, *w in edges:
        key = (min(a, b), max(a, b))
        if key in kept_edges:
            col, width = TEAL, 3.2
        elif key in skip_edges:
            col, width = RUST, 2.0
        elif key in hot_edges:
            col, width = BRASS, 3.0
        else:
            col, width = LINE, 1.8
        edge(p, pos[a], pos[b], col, width, r=r, dash="5 4" if key in skip_edges else None)
        if w:
            mx, my = (pos[a][0] + pos[b][0]) / 2, (pos[a][1] + pos[b][1]) / 2
            p.circle(mx, my, 11, PAPER, "none")
            p.text(mx, my + 4.5, str(w[0]), 12, MUTED, 700, "middle", mono=True)
    for k, (x, y) in pos.items():
        if k == s_at:
            fill, edge_c = BRASS_LT, BRASS
        elif k in s_visited:
            fill, edge_c = TEAL_LT, TEAL
        elif k in s_frontier:
            fill, edge_c = PAPER, BRASS
        else:
            fill, edge_c = PAPER, NAVY
        node(p, x, y, labels[k] if labels else k, fill, edge_c, r=r, size=16)
        if dist is not None:
            d = dist.get(str(k), "∞")
            p.text(x, y - r - 8, "dist %s" % d, 11.5, TEAL if str(k) in s_visited or k in s_visited else MUTED,
                   700, "middle", mono=True)


# ----------------------------------------------------------------------- BFS


def bfs():
    code = source("src/problems/graph_bfs.rs", "pub fn bfs_vec", "}")
    pop = line_of(code, "queue.pop_front()")
    push = line_of(code, "queue.push_back(neighbor)")
    rec = line_of(code, "result.push(current_node)")
    steps = [dict(chapter="queue", say="BFS from node 0. visited marks node 0, and the queue holds it.",
                  queue=[0], marked=[0], code=float(line_of(code, "visited[start_node] = true")))]
    queue, marked, order = [0], [0], []
    while queue:
        cur = queue.pop(0)
        order.append(cur)
        steps.append(dict(say="pop_front takes %d, the oldest entry, and records it." % cur, at=cur,
                          queue=list(queue), order=list(order), code=float(rec)))
        new = []
        for nb in ADJ[cur]:
            if nb not in marked:
                marked.append(nb)
                queue.append(nb)
                new.append(nb)
        if new:
            steps.append(dict(say="Its unvisited neighbors, %s, are marked and pushed at the back." % (
                " and ".join(map(str, new))), queue=list(queue), marked=list(marked), code=float(push),
                hot=[[min(cur, n), max(cur, n)] for n in new]))
        else:
            steps.append(dict(say="Every neighbor of %d is already marked, so nothing is pushed." % cur,
                              hot=[], code=float(pop), hold=0.2))
    steps.append(dict(say="The order is %s: by distance from 0, one ring at a time." % ", ".join(map(str, order)),
                      at=-1, hot=[], kind="insight", code=-1.0, hold=1.2))
    steps.append(dict(chapter="node 6", say="Node 6 has no edge to the others, so BFS from 0 never reaches it.",
                      kind="fail", hold=1.8, missing=1.0))
    tl = play(steps, dict(queue=[], marked=[], order=[], at=-1, hot=[], code=-1.0, missing=0.0))

    def draw(p, s, total):
        t = s.t
        draw_graph(p, GRAPH_POS, GRAPH_EDGES, set(s.order), set(s.marked) - set(s.order), s.at,
                   hot_edges={tuple(h) for h in s.hot})
        if s.missing > 0.5:
            x, y = GRAPH_POS[6]
            p.circle(x, y, 28, "none", RUST, 2.2, dash="5 4")
        lane(p, 26, 316, "queue (front first)", s.queue, hot_first=True)
        lane(p, 440, 316, "result", s.order, TEAL)
        furniture(p, tl, t, total, "Breadth-first search",
                  "A queue visits nodes in order of distance: the start, its neighbors, theirs, and so on.",
                  "bfs_vec", code, s.code, cap_y, rail_y, CODE_Y)

    CODE_Y = 372
    cap_y, rail_y, height = layout(CODE_Y, len(code))
    return tl, draw, height


# ----------------------------------------------------------------------- DFS


def dfs():
    code = source("src/problems/graph_dfs.rs", "pub fn dfs_vec", "}")
    pop = line_of(code, "stack.pop()")
    skip = line_of(code, "continue")
    mark = line_of(code, "result.push(current_node)")
    push = line_of(code, "stack.push(neighbor)")
    steps = [dict(chapter="stack", say="DFS from node 0 with an explicit stack. The stack starts as [0].",
                  stack=[0], code=float(line_of(code, "let mut stack")))]
    stack, visited, order = [0], set(), []
    while stack:
        cur = stack.pop()
        if cur in visited:
            steps.append(dict(say="pop returns %d, which is already visited, so it is skipped." % cur, at=cur,
                              stack=list(stack), code=float(skip), hold=0.1))
            continue
        visited.add(cur)
        order.append(cur)
        steps.append(dict(say="pop returns %d, the newest entry. It is visited and recorded." % cur, at=cur,
                          stack=list(stack), order=list(order), code=float(mark)))
        if ADJ[cur]:
            stack.extend(ADJ[cur])
            steps.append(dict(say="All its neighbors, %s, are pushed. The last one pushed is popped next."
                              % ", ".join(map(str, ADJ[cur])), stack=list(stack), code=float(push),
                              hot=[[min(cur, n), max(cur, n)] for n in ADJ[cur]]))
    steps.append(dict(say="The order is %s. The newest entry goes first, so the walk runs deep before it "
                      "goes wide." % ", ".join(map(str, order)), at=-1, hot=[], kind="insight", code=-1.0,
                      hold=1.6))
    check = line_of(code, "if visited[current_node]")
    steps.append(dict(chapter="no visited check", say="Now run it without the visited check. Every pop is "
                      "recorded, and every neighbor is pushed again.", kind="fail", stack=[0], order=[],
                      at=-1, hot=[], strike=float(check), code=float(line_of(code, "let mut stack"))))
    stack, order = [0], []
    for n in range(9):
        cur = stack.pop()
        order.append(cur)
        stack.extend(ADJ[cur])
        steps.append(dict(say="pop returns %d. It is recorded again%s, and %s are pushed." % (
            cur, "" if order.count(cur) > 1 else " for the first time", ", ".join(map(str, ADJ[cur]))),
            kind="fail", at=cur, stack=list(stack)[-9:], order=list(order)[-9:], code=float(push),
            hot=[[min(cur, x), max(cur, x)] for x in ADJ[cur]], dur=0.4, hold=0.1 if n > 1 else 0.6))
    steps.append(dict(say="Each node pushes its neighbor back. The stack never empties, and the loop never "
                      "ends.", kind="fail", hot=[], code=-1.0, hold=2.2))
    tl = play(steps, dict(stack=[], order=[], at=-1, hot=[], code=-1.0, strike=-1.0))

    def draw(p, s, total):
        t = s.t
        draw_graph(p, GRAPH_POS, GRAPH_EDGES, set(s.order), set(), s.at, hot_edges={tuple(h) for h in s.hot})
        lane(p, 26, 316, "stack (bottom first; pop takes the last)", s.stack)
        lane(p, 440, 316, "result", s.order, TEAL)
        furniture(p, tl, t, total, "Depth-first search with a stack",
                  "The same loop as BFS, with a stack in place of the queue.",
                  "dfs_vec", code, s.code, cap_y, rail_y, CODE_Y, strike=s.strike)

    CODE_Y = 372
    cap_y, rail_y, height = layout(CODE_Y, len(code))
    return tl, draw, height


# ------------------------------------------------------------------- islands


def islands():
    grid = [[1, 1, 0, 0], [1, 0, 0, 1], [0, 0, 1, 1], [0, 0, 0, 0]]
    code = source("src/bin/count_islands.rs", "for r in 0..rows {", "}")
    found = line_of(code, "count += 1")
    fill = line_of(code, "bfs((r, c)")
    n = len(grid)
    steps = [dict(say="A 1 is land and a 0 is water. Land cells that touch on a side form one "
                  "island.", code=-1.0)]
    seen, count, owner = set(), 0, {}
    for r in range(n):
        for c in range(n):
            if grid[r][c] == 1 and (r, c) not in seen:
                count += 1
                steps.append(dict(chapter="island %d" % count, say="The scan reaches (%d, %d): land that no fill "
                                  "has visited. count becomes %d." % (r, c, count), scan="%d %d" % (r, c),
                                  count=count, code=float(found)))
                q = [(r, c)]
                seen.add((r, c))
                owner["%d %d" % (r, c)] = count
                while q:
                    cr, cc = q.pop(0)
                    for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < n and 0 <= nc < n and grid[nr][nc] == 1 and (nr, nc) not in seen:
                            seen.add((nr, nc))
                            owner["%d %d" % (nr, nc)] = count
                            q.append((nr, nc))
                    steps.append(dict(say="The flood fill spreads from (%d, %d) to its land neighbors." % (cr, cc),
                                      owner=dict(owner), code=float(fill), dur=0.5, hold=0.1))
            elif grid[r][c] == 1:
                steps.append(dict(say="(%d, %d) is land, but the fill already visited it, so the scan moves on."
                                  % (r, c), scan="%d %d" % (r, c), hold=0.1))
    steps.append(dict(say="The scan is done. Each fill marked one whole island, so count is %d." % count,
                      scan="", kind="insight", code=-1.0, hold=1.6))
    test = line_of(code, "!visited.contains")
    steps.append(dict(chapter="no visited check", say="Now drop && !visited.contains(&(r, c)) from the scan's "
                      "test.", kind="fail", strike=float(test), count=0, owner={}, scan="", code=-1.0))
    bad = 0
    for r in range(n):
        for c in range(n):
            if grid[r][c] == 1:
                bad += 1
                steps.append(dict(say="(%d, %d) is land, so count becomes %d, visited or not." % (r, c, bad),
                                  kind="fail", scan="%d %d" % (r, c), count=bad, code=float(found),
                                  dur=0.4, hold=0.2))
    steps.append(dict(say="count is %d, not 2. Every land cell started its own island, because the scan "
                      "never asked whether a fill had reached it." % bad, kind="fail", scan="", code=-1.0,
                      hold=2.2))
    steps = [{a: b for a, b in st.items() if b is not None} for st in steps]
    tl = play(steps, dict(scan="", count=0, owner={}, code=-1.0, strike=-1.0))

    def draw(p, s, total):
        t = s.t
        size, x0, y0 = 62, 250, 92
        colors = {1: (TEAL_LT, TEAL), 2: (BRASS_LT, BRASS)}
        for r in range(n):
            for c in range(n):
                key = "%d %d" % (r, c)
                land = grid[r][c] == 1
                fill, edge_c = (("#eaf2fb", "#bcd3ea") if not land else (PAPER, NAVY))
                if key in s.owner:
                    fill, edge_c = colors[s.owner[key]]
                p.rect(x0 + c * size + 3, y0 + r * size + 3, size - 6, size - 6, fill, edge_c, 8, 1.8)
                p.text(x0 + c * size + size / 2, y0 + r * size + size / 2 + 7, "1" if land else "0", 20,
                       INK if land else "#9ab", 700, "middle", mono=True)
        if s.scan:
            r, c = map(int, s.scan.split())
            p.rect(x0 + c * size - 2, y0 + r * size - 2, size + 4, size + 4, "none", RUST, 10, 2.6)
        p.text(x0 + n * size + 30, y0 + 30, "count = %d" % s.count, 18,
               RUST if s.strike >= 0 else INK, 700, mono=True)
        furniture(p, tl, t, total, "Counting islands: scan, then flood fill",
                  "Each unvisited land cell starts a new island; the fill marks the rest of it.",
                  "count_islands (the scan)", code, s.code, cap_y, rail_y, CODE_Y, strike=s.strike)

    CODE_Y = 356
    cap_y, rail_y, height = layout(CODE_Y, len(code))
    return tl, draw, height


# ------------------------------------------------------------------ topo sort


TOPO_POS = {0: (120, 186), 1: (300, 116), 2: (300, 256), 3: (480, 186), 4: (660, 186)}
TOPO_EDGES = [(0, 1), (0, 2), (1, 3), (2, 3), (3, 4)]


def arrow_edge(p, a, b, color, width, r=22):
    import math
    (x1, y1), (x2, y2) = a, b
    d = math.hypot(x2 - x1, y2 - y1)
    ux, uy = (x2 - x1) / d, (y2 - y1) / d
    sx, sy, ex, ey = x1 + ux * r, y1 + uy * r, x2 - ux * (r + 2), y2 - uy * (r + 2)
    p.line(sx, sy, ex, ey, color, width)
    px, py = -uy, ux
    p.path("M %.1f %.1f L %.1f %.1f L %.1f %.1f Z" % (ex, ey, ex - ux * 10 + px * 5, ey - uy * 10 + py * 5,
                                                      ex - ux * 10 - px * 5, ey - uy * 10 - py * 5), color, "none")


def topo():
    code = source("src/problems/graph_topology.rs", "let mut queue: VecDeque", "then_some(order)")
    pop = line_of(code, "queue.pop_front()")
    dec = line_of(code, "indegree[next] -= 1")
    push = line_of(code, "queue.push_back(next)")
    end = line_of(code, "then_some(order)")
    indeg = {k: 0 for k in TOPO_POS}
    for a, b in TOPO_EDGES:
        indeg[b] += 1
    D = lambda: {str(k): v for k, v in indeg.items()}
    queue = [k for k in TOPO_POS if indeg[k] == 0]
    steps = [dict(chapter="Kahn", say="indegree counts the edges into each node. Only node 0 has none, so the "
                  "queue starts with it.", indeg=D(), queue=list(queue), code=0.0)]
    order, live = [], list(TOPO_EDGES)
    while queue:
        node_ = queue.pop(0)
        order.append(node_)
        steps.append(dict(say="pop_front takes %d. Nothing it depends on is left, so it goes next in the order."
                          % node_, at=node_, queue=list(queue), order=list(order), code=float(pop)))
        outs = [b for a, b in live if a == node_]
        if outs:
            for b in outs:
                indeg[b] -= 1
            live = [e for e in live if e[0] != node_]
            ready = [b for b in outs if indeg[b] == 0]
            queue += ready
            steps.append(dict(say="Its edges are removed: %s. %s" % (
                ", ".join("indegree[%d] drops to %d" % (b, indeg[b]) for b in outs),
                ("%s reach 0 and join the queue." % " and ".join(map(str, ready))) if len(ready) > 1 else
                ("%d reaches 0 and joins the queue." % ready[0]) if ready else "No node reaches 0."),
                indeg=D(), live=[list(e) for e in live], queue=list(queue), code=float(push if ready else dec)))
    steps.append(dict(say="The order is %s. It has all five nodes, so the function returns Some(order)."
                      % ", ".join(map(str, order)), at=-1, kind="insight", code=float(end), hold=1.4))
    steps.append(dict(chapter="cycle", say="Now add an edge from 4 back to 1. Then 1, 3, and 4 wait on each other.",
                      kind="fail", at=-1, order=[], queue=[0], live=[list(e) for e in TOPO_EDGES] + [[4, 1]],
                      indeg={"0": 0, "1": 2, "2": 1, "3": 2, "4": 1}, cycle=1.0, code=-1.0))
    steps.append(dict(say="Kahn's loop takes 0, then 2. indegree[3] stops at 1, so 1, 3, and 4 never reach 0.",
                      kind="fail", order=[0, 2], queue=[], live=[[1, 3], [3, 4], [4, 1]],
                      indeg={"0": 0, "1": 1, "2": 0, "3": 1, "4": 1}))
    steps.append(dict(say="order has 2 of 5 nodes, so then_some returns None: no order exists.", kind="fail",
                      code=float(end), hold=1.8))
    tl = play(steps, dict(indeg={}, queue=[], order=[], at=-1, live=[list(e) for e in TOPO_EDGES], code=-1.0,
                          cycle=0.0))

    def draw(p, s, total):
        t = s.t
        live = {tuple(e) for e in s.live}
        edges = list(TOPO_EDGES) + ([(4, 1)] if s.cycle > 0.5 else [])
        for a, b in edges:
            on = (a, b) in live
            col = RUST if (s.cycle > 0.5 and on and (a, b) in {(1, 3), (3, 4), (4, 1)}) else (NAVY if on else "#e3e8ee")
            if (a, b) == (4, 1):
                (x1, y1), (x2, y2) = TOPO_POS[4], TOPO_POS[1]
                p.path("M %.1f %.1f Q %.1f %.1f %.1f %.1f" % (x1 - 10, y1 - 22, 520, 60, x2 + 22, y2 - 8),
                       "none", col, 2.2)
                p.path("M %.1f %.1f l 11 -6 l -2 11 Z" % (x2 + 22, y2 - 8), col, "none")
                continue
            arrow_edge(p, TOPO_POS[a], TOPO_POS[b], col, 2.2 if on else 1.4)
        for k, (x, y) in TOPO_POS.items():
            done = k in s.order
            here = k == s.at
            fill, edge_c = (BRASS_LT, BRASS) if here else ((TEAL_LT, TEAL) if done else (PAPER, NAVY))
            node(p, x, y, k, fill, edge_c, r=22, size=16)
            d = s.indeg.get(str(k), 0)
            p.text(x, y + 40, "in %d" % d, 11.5, TEAL if d == 0 else MUTED, 700, "middle", mono=True)
        lane(p, 26, 316, "queue", s.queue, hot_first=True)
        lane(p, 440, 316, "order", s.order, TEAL)
        furniture(p, tl, t, total, "Topological order with Kahn's algorithm",
                  "A node is ready when nothing points into it. Taking it removes its outgoing edges.",
                  "topological_sort (the loop)", code, s.code, cap_y, rail_y, CODE_Y)

    CODE_Y = 372
    cap_y, rail_y, height = layout(CODE_Y, len(code))
    return tl, draw, height


# ------------------------------------------------------------------ Dijkstra


DIJK_POS = {0: (150, 196), 1: (380, 116), 2: (380, 276), 3: (620, 196)}
DIJK_EDGES = [(0, 1, 4), (0, 2, 1), (2, 1, 2), (1, 3, 1), (2, 3, 5)]
DIJK_NAMES = {0: "A", 1: "B", 2: "C", 3: "D"}


def dijkstra():
    code = source("src/problems/graph_dijkstra.rs", "pub fn dijkstra_vec", "}")
    pop = line_of(code, "min_heap.pop()")
    stale = line_of(code, "continue")
    relax = line_of(code, "distances[neighbor] = Some(new_distance)")
    adj = {k: [] for k in DIJK_POS}
    for a, b, w in DIJK_EDGES:
        adj[a].append((b, w))
        adj[b].append((a, w))
    N = DIJK_NAMES
    dist = {0: 0}
    heap = [(0, 0)]
    done = []
    steps = [dict(chapter="settle", say="Shortest distances from A. distances[A] = 0, and the heap holds (0, A).",
                  dist={"0": "0"}, heap=["(0, A)"], code=float(line_of(code, "distances[start_node] = Some(0)")))]
    while heap:
        heap.sort()
        cost, cur = heap.pop(0)
        H = lambda: ["(%d, %s)" % (c, N[n]) for c, n in sorted(heap)]
        if cost > dist[cur]:
            steps.append(dict(say="pop returns (%d, %s), but distances[%s] is already %d. The entry is stale, "
                              "so it is skipped." % (cost, N[cur], N[cur], dist[cur]), heap=H(), at=cur,
                              code=float(stale), hold=0.4))
            continue
        done.append(cur)
        steps.append(dict(say="pop returns (%d, %s), the smallest cost in the heap. %s is settled at %d."
                          % (cost, N[cur], N[cur], cost), heap=H(), at=cur,
                          settled=[str(d) for d in done], code=float(pop)))
        for nb, w in sorted(adj[cur]):
            nd = cost + w
            if nb not in dist or nd < dist[nb]:
                old = dist.get(nb)
                dist[nb] = nd
                heap.append((nd, nb))
                steps.append(dict(say="%s to %s costs %d + %d = %d, %s. distances[%s] = %d, and (%d, %s) is pushed."
                                  % (N[cur], N[nb], cost, w, nd, "the first path found" if old is None else
                                     "less than %d" % old, N[nb], nd, nd, N[nb]),
                                  dist={str(k): str(v) for k, v in dist.items()}, heap=H(),
                                  hot=[min(cur, nb), max(cur, nb)], code=float(relax), hold=0.2))
    steps.append(dict(say="Every node is settled: A 0, B 3, C 1, D 4. B's first entry, (4, B), was stale and "
                      "skipped.", at=-1, hot=[], kind="insight", code=-1.0, hold=1.6))
    steps.append(dict(chapter="unreachable", say="Now add a node E with no edges. No relaxation ever reaches it, "
                      "so nothing pushes E.", kind="fail", lone=1.0, code=float(pop), hold=1.0))
    steps.append(dict(say="The heap empties, and distances[E] is still None. The caller must handle None: no "
                      "path, not distance 0.", kind="fail", heap=[], code=-1.0, hold=2.2))
    tl = play(steps, dict(dist={}, heap=[], at=-1, settled=[], hot=[], code=-1.0, lone=0.0))

    def draw(p, s, total):
        t = s.t
        hot = {tuple(s.hot)} if s.hot else set()
        draw_graph(p, DIJK_POS, [(a, b, w) for a, b, w in DIJK_EDGES], set(int(x) for x in s.settled), set(),
                   s.at, hot_edges=hot, labels=N, dist=s.dist)
        lane(p, 26, 334, "min_heap (smallest first)", s.heap, hot_first=True)
        if s.lone > 0.01:
            node(p, 740, 300, "E", RUST_LT, RUST, r=22, size=16)
            p.text(740, 264, "dist None", 11.5, RUST, 700, "middle", mono=True)
        furniture(p, tl, t, total, "Dijkstra: settle the closest node, then relax its edges",
                  "Weights are non-negative, so the smallest cost in the heap is final.",
                  "dijkstra_vec", code, s.code, cap_y, rail_y, CODE_Y, size=10.6, lead=15.0)

    CODE_Y = 388
    cap_y, rail_y, height = layout(CODE_Y, len(code), 15.0)
    return tl, draw, height


# ------------------------------------------------------------------- Kruskal


KR_POS = {0: (130, 196), 1: (320, 116), 2: (320, 276), 3: (520, 196), 4: (690, 196)}
KR_EDGES = [(0, 1, 4), (0, 2, 3), (1, 2, 1), (1, 3, 2), (2, 3, 4), (3, 4, 2)]


def kruskal():
    code = source("src/bin/kruskals_algorithm.rs", "fn kruskals(", "}")
    sort = line_of(code, "edges.sort_by_key")
    union = line_of(code, "if uf.union(edge.u, edge.v)")
    keep = line_of(code, "mst.push(edge)")
    parent = list(range(5))

    def find(x):
        while parent[x] != x:
            x = parent[x]
        return x

    def groups():
        return {str(k): find(k) for k in KR_POS}

    order = sorted(KR_EDGES, key=lambda e: e[2])
    steps = [dict(say="sort_by_key orders the edges by weight: %s." % ", ".join(
        "%d-%d (%d)" % (a, b, w) for a, b, w in order), code=float(sort), group=groups())]
    kept, skipped, total = [], [], 0
    for a, b, w in order:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
            kept.append([min(a, b), max(a, b)])
            total += w
            steps.append(dict(chapter="union-find" if len(kept) == 1 else None,
                              say="%d-%d (%d): %d and %d are in different sets, so union joins them and the edge is "
                              "kept." % (a, b, w, a, b), cur=[min(a, b), max(a, b)], kept=[list(k) for k in kept],
                              group=groups(), total=total, code=float(keep)))
        else:
            skipped.append([min(a, b), max(a, b)])
            steps.append(dict(say="%d-%d (%d): %d and %d are already in one set. The edge would close a cycle, so "
                              "union returns false." % (a, b, w, a, b), cur=[min(a, b), max(a, b)],
                              skipped=[list(k) for k in skipped], code=float(union)))
    steps.append(dict(say="Four edges join five nodes, with total weight %d." % total, cur=[], kind="insight",
                      code=-1.0, hold=1.6))
    steps.append(dict(chapter="no check", say="Now keep every edge without asking union-find. Same sorted "
                      "order.", kind="fail", strike=float(union), kept=[], skipped=[], total=0, cur=[],
                      group={str(k): 0 for k in KR_POS}, code=-1.0))
    all_kept, bad_total = [], 0
    for a, b, w in order:
        all_kept.append([min(a, b), max(a, b)])
        bad_total += w
        steps.append(dict(say="%d-%d (%d) is kept." % (a, b, w), kind="fail", cur=[min(a, b), max(a, b)],
                          kept=[list(k) for k in all_kept], total=bad_total, code=float(keep), dur=0.4,
                          hold=0.2))
    steps.append(dict(say="Six edges for five nodes, total %d instead of %d. 1-2-3 and 0-1-2 are cycles, so "
                      "this is not a tree." % (bad_total, total), kind="fail", cur=[], code=-1.0, hold=2.2))
    steps = [{x: y for x, y in st.items() if y is not None} for st in steps]
    tl = play(steps, dict(cur=[], kept=[], skipped=[], group={}, total=0, code=-1.0, strike=-1.0))

    def draw(p, s, total_):
        t = s.t
        palette = [(TEAL_LT, TEAL), (BRASS_LT, BRASS), ("#eae4f6", "#7a5fb0"), (RUST_LT, RUST), ("#e6ecf6", NAVY)]
        for a, b, w in KR_EDGES:
            key = [min(a, b), max(a, b)]
            if key in s.kept:
                col, width, dash = TEAL, 3.4, None
            elif key in s.skipped:
                col, width, dash = RUST, 2.0, "5 4"
            elif key == s.cur:
                col, width, dash = BRASS, 3.0, None
            else:
                col, width, dash = LINE, 1.8, None
            edge(p, KR_POS[a], KR_POS[b], col, width, r=22, dash=dash)
            mx, my = (KR_POS[a][0] + KR_POS[b][0]) / 2, (KR_POS[a][1] + KR_POS[b][1]) / 2
            p.circle(mx, my, 11, PAPER, "none")
            p.text(mx, my + 4.5, str(w), 12, MUTED, 700, "middle", mono=True)
        roots = sorted(set(s.group.values())) if s.group else []
        for k, (x, y) in KR_POS.items():
            g = roots.index(s.group[str(k)]) if s.group else k
            fill, edge_c = palette[g % len(palette)]
            node(p, x, y, k, fill, edge_c, r=22, size=16)
        p.text(W - 40, 112, "total = %d" % s.total, 16, INK, 700, "end", mono=True)
        p.text(W - 40, 134, "same colour = same set", 11.5, MUTED, 600, "end")
        furniture(p, tl, t, total_, "Kruskal: cheapest edges first, skipping cycles",
                  "Union-find tells whether an edge joins two separate pieces.",
                  "kruskals", code, s.code, cap_y, rail_y, CODE_Y, strike=s.strike)

    CODE_Y = 330
    cap_y, rail_y, height = layout(CODE_Y, len(code))
    return tl, draw, height


def build(name, fn, extra=()):
    def run(only=None):
        tl, draw, height = fn()
        return render(name, tl, draw, height, only=only, extra_colors=extra)
    return run


BUILDERS = {
    "bfs": build("ch12-bfs.gif", bfs, (NAVY,)),
    "dfs": build("ch12-dfs.gif", dfs, (NAVY,)),
    "islands": build("ch12-islands.gif", islands, (NAVY, "#eaf2fb", "#bcd3ea")),
    "topo": build("ch12-topo.gif", topo, (NAVY,)),
    "dijkstra": build("ch12-dijkstra.gif", dijkstra, (NAVY,)),
    "kruskal": build("ch12-kruskal.gif", kruskal, (NAVY, "#eae4f6", "#7a5fb0", "#e6ecf6")),
}
