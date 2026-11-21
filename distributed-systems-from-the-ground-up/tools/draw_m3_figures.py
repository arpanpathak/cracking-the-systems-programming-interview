#!/usr/bin/env python3
"""Generate spacious Material Design 3 light+dark SVG figures (WIDTH = 920).

Every figure prioritizes generous whitespace, concise crisp labels, zero text
overflow in Chrome/Safari, and clear separation of control and data planes.
"""
import math
from figkit_m3 import Fig, WIDTH, MARGIN

INNER = WIDTH - 2 * MARGIN  # 856px usable width


# =============================================================================
# REUSABLE USE-CASE DIAGRAM BUILDER (CLEAN MATERIAL 3 BOUNDARY & ACTORS)
# =============================================================================

def build_use_case_fig(name, title, boundary_title, boundary_sub, actors, cases, links, notes):
    """Spacious UML-inspired Material Design 3 use-case diagram (WIDTH = 920)."""
    # Layout: left column = actors (w=252), right = system boundary (x=344..888)
    n_cases = len(cases)
    case_h = 58
    case_gap = 16
    inner_h = 70 + n_cases * case_h + (n_cases - 1) * case_gap + 18
    total_h = max(360, inner_h + 10)
    f = Fig(name, title, total_h)

    # System boundary on right
    bx = 346
    bw = WIDTH - MARGIN - bx  # 542
    f.zone(bx, 0, bw, total_h - 8, "blue", boundary_title, boundary_sub, icon="layers", dashed=True)

    # Place use-case cards inside boundary
    case_boxes = []
    for idx, (uc_title, uc_sub, tone, ic) in enumerate(cases):
        cy = 68 + idx * (case_h + case_gap)
        box = f.node(bx + 22, cy, bw - 44, case_h, tone, [(uc_title, "name"), (uc_sub, "mono")], icon=ic, kind="card", icon_size=26)
        case_boxes.append(box)

    # Place actor cards evenly along left column
    n_act = len(actors)
    act_h = 84
    act_span = (total_h - 24) - n_act * act_h
    act_gap = act_span / max(1, n_act - 1) if n_act > 1 else 0
    act_boxes = []
    for idx, (a_title, a_sub, tone, ic) in enumerate(actors):
        ay = 14 + idx * (act_h + act_gap)
        box = f.node(MARGIN, ay, 248, act_h, tone, [(a_title, "name"), (a_sub, "sub")], icon=ic, kind="card", icon_size=28)
        act_boxes.append(box)

    # Orthogonal fan-out wires from actors to their use cases via distinct vertical buses
    bus_xs = [296 + i * 16 for i in range(n_act)]
    for act_idx, uc_indices, tone in links:
        ab = act_boxes[act_idx]
        bus_x = bus_xs[act_idx]
        for uc_idx in uc_indices:
            cb = case_boxes[uc_idx]
            f.wire([ab.right(0), (bus_x, ab.cy), (bus_x, cb.cy), cb.left(0)], tone=tone, width=1.8, radius=7)

    return f.save(notes)


# =============================================================================
# CHAPTER 1: DISTRIBUTED KEY-VALUE STORE
# =============================================================================

def ch01_use_cases():
    return build_use_case_fig(
        "ch01_use_cases",
        "Figure 1-1. Actors and Use Cases of the Distributed Key-Value Store.",
        "System Boundary: Distributed Key-Value Store",
        "HTTP/2 external API · Multi-AZ durable storage & cluster operations",
        actors=[
            ("Application Service", "Stateless web & API hosts", "blue", "laptop"),
            ("Cluster Operator", "SRE / placement controller", "purple", "engineering"),
            ("Observability Platform", "Probes & Prometheus", "teal", "notifications_active"),
        ],
        cases=[
            ("Point Read, Write, and Delete", "PUT / GET / DELETE /v1/keys/{key}", "blue", "save"),
            ("Conditional Compare-and-Swap", "PUT /v1/keys/{key}  If-Match: <ver>", "amber", "lock"),
            ("Paginated Prefix Listing", "GET /v1/keys?prefix=p&limit=n", "teal", "table_rows"),
            ("Online Node Reconfiguration", "Add, drain, or replace storage hosts", "purple", "tune"),
            ("Health & Consensus Telemetry", "GET /healthz  ·  Raft lag & disk metrics", "green", "bolt"),
        ],
        links=[
            (0, [0, 1, 2], "blue"),
            (1, [3], "purple"),
            (2, [4], "teal"),
        ],
        notes=[
            ("Application services exercise the synchronous data plane; cluster operators and observability systems interact through dedicated control and telemetry paths.", "noteb"),
            "Every functional requirement in Section 1.1 maps directly to one of these five verifiable system use cases.",
        ],
    )


def ch01_architecture():
    f = Fig(
        "ch01_architecture",
        "Figure 1-2. Control Plane and Data Plane Topology of the Distributed Key-Value Store.",
        546,
    )
    # Top-left: Clients
    cli = f.node(
        MARGIN, 10, 290, 82, "blue",
        [("Application Clients", "name"), ("HTTP/2 + mTLS · If-Match CAS", "sub")],
        icon="laptop", kind="card",
    )

    # Top-right: Control Plane
    cp_x = 360
    cp_w = WIDTH - MARGIN - cp_x  # 528
    f.zone(
        cp_x, 0, cp_w, 162, "purple",
        "Control Plane (Metadata & Placement)",
        "3-node Raft metadata cluster · Cluster epoch · Auto-rebalancer",
        icon="settings_suggest", dashed=True,
    )
    meta_raft = f.node(
        cp_x + 18, 60, 236, 84, "purple",
        [("Metadata Raft Quorum", "name"), ("Epoch v42 · Ring map", "sub")],
        icon="dns", kind="card", icon_size=28,
    )
    rebal = f.node(
        cp_x + 274, 60, 236, 84, "purple",
        [("Placement Controller", "name"), ("AZ balance & splits", "sub")],
        icon="tune", kind="card", icon_size=28,
    )

    # Middle-left: Data Plane Router Tier
    dp_router = f.zone(
        MARGIN, 130, 290, 146, "teal",
        "Data Plane: Stateless Routers",
        "L7 LB -> 6 routers across 3 AZs",
        icon="swap_horiz",
    )
    router = f.node(
        MARGIN + 16, 188, 258, 72, "teal",
        [("Request Router Tier", "name"), ("Cached ring · Hedged reads", "sub")],
        icon="call_split", kind="card", icon_size=28,
    )

    # Bottom: Multi-AZ Storage Tier
    storage = f.zone(
        MARGIN, 314, INNER, 224, "blue",
        "Data Plane: Partitioned Multi-Raft Storage Tier (24 Nodes Across 3 AZs)",
        "Each shard is an independent 3-replica Raft group placed across distinct availability zones",
        icon="layers",
    )

    az_w = 262
    az_gap = 18
    az_x = [MARGIN + 17 + i * (az_w + az_gap) for i in range(3)]
    az_titles = ["Availability Zone A", "Availability Zone B", "Availability Zone C"]

    for i in range(3):
        f.rect(az_x[i], 372, az_w, 150, "card", r=12, lift=True)
        f.text(az_x[i] + 14, 394, az_titles[i], "name", "start", tone="blue", fit=(az_x[i] + 10, az_x[i] + az_w - 10))
        if i == 0:
            f.node(az_x[i] + 12, 406, az_w - 24, 50, "amber",
                   [("Shard 01 · LEADER (T4)", "monob"), ("WAL fsync -> LSM engine", "small")],
                   kind="mid", r=8)
            f.node(az_x[i] + 12, 464, az_w - 24, 48, "gray",
                   [("Shard 02 · Follower", "mono"), ("Async apply", "small")],
                   kind="tonal", r=8)
        elif i == 1:
            f.node(az_x[i] + 12, 406, az_w - 24, 50, "gray",
                   [("Shard 01 · Follower", "mono"), ("Quorum ACK (2 of 3)", "small")],
                   kind="tonal", r=8)
            f.node(az_x[i] + 12, 464, az_w - 24, 48, "amber",
                   [("Shard 02 · LEADER (T7)", "monob"), ("WAL fsync -> LSM engine", "small")],
                   kind="mid", r=8)
        else:
            f.node(az_x[i] + 12, 406, az_w - 24, 50, "gray",
                   [("Shard 01 · Follower", "mono"), ("3rd replica standby", "small")],
                   kind="tonal", r=8)
            f.node(az_x[i] + 12, 464, az_w - 24, 48, "gray",
                   [("Shard 02 · Follower", "mono"), ("Quorum ACK (2 of 3)", "small")],
                   kind="tonal", r=8)

    # Clean orthogonal wires with generous label clearance
    f.wire([cli.bottom(0), (cli.cx, dp_router.y)], tone="blue", width=2.0)
    f.label(cli.cx + 78, 114, "PUT / GET / DELETE", tone="blue", cls="small")

    f.wire([meta_raft.bottom(-30), (meta_raft.cx - 30, 224), router.right(0)], tone="purple", dash=True, width=1.6)
    f.label(446, 206, "Epoch watch stream", tone="purple", cls="small")

    f.wire([rebal.bottom(0), (rebal.cx, storage.y)], tone="purple", dash=True, width=1.6, tail=True)
    f.label(rebal.cx, 240, "Leases & shard placement", tone="purple", cls="small")

    f.wire([router.bottom(0), (router.cx, storage.y)], tone="teal", width=2.0)
    f.label(router.cx + 96, 298, "gRPC direct to Leader", tone="teal", cls="small")

    f.wire([(az_x[0] + az_w - 12, 431), (az_x[1] + 12, 431)], tone="amber", width=1.9)
    f.wire([(az_x[1] + az_w - 12, 431), (az_x[2] + 12, 431)], tone="amber", dash=True, width=1.6)

    return f.save([
        ("Solid wires carry the synchronous data path (client -> stateless router -> shard Raft leader -> cross-AZ quorum).", "noteb"),
        "Dashed purple wires carry control-plane metadata watches and lease heartbeats. During a control-plane outage, routers continue serving from cached epoch v42 and refresh via storage-node redirects.",
    ])


def ch01_consistency_models():
    f = Fig(
        "ch01_consistency_models",
        "Figure 1-3. Operation Visibility Across Linearizable, Tunable Quorum, and Eventual Consistency.",
        452,
    )
    axis_x1, axis_x2 = 240, WIDTH - MARGIN - 12
    f.text(MARGIN, 20, "Consistency Model", "head", "start")
    f.text(axis_x1, 20, "Real-Time Execution Timeline (t0 -> t5)", "head", "start", tone="blue")
    f.wire([(axis_x1, 34), (axis_x2, 34)], tone="wire", width=1.5)
    for idx, lbl in enumerate(["t0", "t1", "t2", "t3", "t4", "t5"]):
        tx = axis_x1 + idx * (axis_x2 - axis_x1 - 24) / 5
        f.rule(tx, 30, tx, 434, tone="gray", width=1.0, dash="3 4")
        f.text(tx, 50, lbl, "small", "middle")

    # Lane 1
    y1 = 64
    f.zone(MARGIN, y1, INNER, 114, "blue", "1. Linearizable (Strong)", "Single-copy illusion via Raft quorum + ReadIndex", icon="shield")
    f.cell(244, y1 + 54, 198, 46, "blue", [("PUT(k, v2) -> 2/3 ACK", "monob"), ("Committed before t2", "small")], kind="card")
    f.wire([(442, y1 + 77), (484, y1 + 77)], tone="blue", width=1.8)
    f.cell(488, y1 + 54, 244, 46, "green", [("GET(k) -> Leader ReadIndex", "monob"), ("Always returns v2", "small")], kind="card")
    f.pill(WIDTH - MARGIN - 18, y1 + 67, "Chosen", tone="green", anchor="end")

    # Lane 2
    y2 = 194
    f.zone(MARGIN, y2, INNER, 114, "amber", "2. Tunable Quorum (R + W > N)", "Leaderless Dynamo-style: client selects W and R", icon="tune")
    f.cell(244, y2 + 54, 194, 46, "amber", [("PUT(k, v2)  W=2/3", "monob"), ("R1, R2 updated; R3 lags", "small")], kind="card")
    f.cell(456, y2 + 54, 206, 46, "teal", [("GET R=2 -> {R2, R3}", "monob"), ("Returns v2 + read-repair", "small")], kind="card")
    f.cell(680, y2 + 54, 190, 46, "red", [("W=1, R=1 -> {R3}", "monob"), ("Returns stale v1", "small")], kind="mid")

    # Lane 3
    y3 = 324
    f.zone(MARGIN, y3, INNER, 114, "purple", "3. Eventual Consistency", "Local ACK + asynchronous anti-entropy convergence", icon="loop")
    f.cell(244, y3 + 54, 194, 46, "purple", [("PUT(k, v2) Local ACK", "monob"), ("Async stream to peers", "small")], kind="card")
    f.cell(456, y3 + 54, 202, 46, "red", [("GET(k) at R3 -> v1", "monob"), ("Stale read during lag", "small")], kind="mid")
    f.wire([(658, y3 + 77), (686, y3 + 77)], tone="purple", dash=True, width=1.6)
    f.cell(690, y3 + 54, 180, 46, "green", [("t5: Anti-entropy", "monob"), ("Replicas converge v2", "small")], kind="card")

    return f.save([
        ("Linearizability forbids any read invoked after an acknowledged write from observing an older value.", "noteb"),
        "Selecting linearizability ensures conditional compare-and-swap writes (If-Match) and lock metadata remain immune to concurrent lost updates.",
    ])


def ch01_partitioning_vnodes():
    f = Fig(
        "ch01_partitioning_vnodes",
        "Figure 1-4. Consistent Hash Ring Partitioning, Virtual Node Balance, and Scan Trade-offs.",
        444,
    )
    # Left panel: Spacious Hash Ring
    lw = 414
    f.zone(MARGIN, 0, lw, 434, "teal", "Consistent Hash Ring (64-bit Space)", "Clockwise walk selects 3 distinct AZ replicas", icon="loop")
    cx, cy, rad = MARGIN + lw / 2, 226, 102
    f.circle(cx, cy, rad, "o-teal", extra=' stroke-width="2.6"')
    f.circle(cx, cy, rad - 22, "hair", extra=' stroke-dasharray="4 4"')
    f.text(cx, cy - 8, "Hash Space", "name", "middle", tone="teal")
    f.text(cx, cy + 14, "0 .. 2^64 - 1", "mono", "middle")

    tokens = [
        (332, "N1:v1", "blue"),
        (32, "N2:v1", "green"),
        (90, "N3:v1", "purple"),
        (148, "N1:v2", "blue"),
        (208, "N4:v1", "amber"),
        (262, "N2:v2", "green"),
    ]
    for deg, lbl, tone in tokens:
        ang = math.radians(deg)
        px, py = cx + rad * math.cos(ang), cy + rad * math.sin(ang)
        f.circle(px, py, 7.0, f"a-{tone}")
        lx, ly = cx + (rad + 34) * math.cos(ang), cy + (rad + 26) * math.sin(ang)
        f.text(lx, ly + 4, lbl, "monob", "middle", tone=tone)

    kang = math.radians(298)
    f.circle(cx + rad * math.cos(kang), cy + rad * math.sin(kang), 6.5, "a-red")
    f.pill(cx + 92, 76, "H(user-1) -> N1, N2, N3", tone="red", anchor="middle")

    f.text(MARGIN + 20, 396, "Adding 1 node to 24 moves only 4.33% of keys", "small", "start", tone="teal")
    f.text(MARGIN + 20, 415, "(compared to 96.0% under hash(k) mod N).", "small", "start")

    # Right top panel: Empirical VNode Skew
    rx = MARGIN + lw + 22
    rw = WIDTH - MARGIN - rx  # 420
    f.zone(rx, 0, rw, 224, "blue", "Empirical Skew (ringsim, 24 Nodes)", "100,000 keys · Ideal share = 4.17% per node", icon="table_rows")
    rows = [
        ("1 vnode", 0.16, 11.26, "red"),
        ("8 vnodes", 1.42, 7.83, "amber"),
        ("64 vnodes", 3.35, 5.07, "teal"),
        ("256 vnodes", 3.86, 4.73, "green"),
    ]
    bar_x0 = rx + 104
    bar_w_max = 200
    ideal_x = bar_x0 + (4.17 / 12.0) * bar_w_max
    f.rule(ideal_x, 60, ideal_x, 198, tone="blue", width=1.4, dash="4 3")
    f.text(ideal_x, 212, "Ideal 4.17%", "small", "middle", tone="blue")

    for idx, (lbl, lo, hi, tone) in enumerate(rows):
        ry = 66 + idx * 33
        f.text(rx + 18, ry + 14, lbl, "monob", "start")
        f.rect(bar_x0, ry + 4, bar_w_max, 14, "c-gray", r=5)
        x_lo = bar_x0 + (lo / 12.0) * bar_w_max
        x_hi = bar_x0 + (hi / 12.0) * bar_w_max
        f.rect(x_lo, ry + 4, max(8, x_hi - x_lo), 14, f"a-{tone}", r=5)
        f.text(bar_x0 + bar_w_max + 10, ry + 15, f"{lo:.2f}-{hi:.2f}%", "small", "start", tone=tone)

    # Right bottom panel: Hash vs Range Partitioning
    f.zone(rx, 242, rw, 192, "amber", "Hash vs. Range Partitioning", "Impact on prefix scans (GET /v1/keys?prefix=)", icon="call_split")
    f.node(rx + 16, 298, rw - 32, 56, "teal",
           [("Consistent Hashing", "name"), ("Uniform writes; prefix scan scatters", "sub")],
           kind="card", r=10)
    f.node(rx + 16, 364, rw - 32, 56, "purple",
           [("Sorted Range Partitioning", "name"), ("Single-shard scans; needs range splits", "sub")],
           kind="card", r=10)

    return f.save([
        ("Virtual nodes compress worst-case skew from 2.7x ideal (11.26%) down to 1.13x ideal (4.73%) at 256 tokens per host.", "noteb"),
        "Production stores pair hash partitioning on a tenant prefix with sorted range keys inside each partition (DynamoDB) or dynamic range splits (CockroachDB, TiKV).",
    ])


def ch01_replication_failover():
    f = Fig(
        "ch01_replication_failover",
        "Figure 1-5. Raft Quorum Write Commit, Linearizable ReadIndex, and Split-Brain Fencing.",
        456,
    )
    lw = 416
    # Left panel: Normal Path
    f.zone(MARGIN, 0, lw, 446, "green", "Normal Path: Quorum + ReadIndex", "Single shard leader · Majority (2 of 3) durability", icon="bolt")
    rtr = f.node(MARGIN + 18, 62, lw - 36, 58, "teal", [("1. Router -> Shard Leader (Term 4)", "name"), ("PUT /v1/keys/u1 (If-Match: 7)", "mono")], kind="card")
    ldr = f.node(MARGIN + 18, 146, lw - 36, 72, "amber", [("2. Shard Leader (AZ-A)", "name"), ("Check version == 7 · WAL fsync (idx=42)", "sub"), ("Parallel AppendEntries(term=4)", "small")], kind="card")
    f1 = f.node(MARGIN + 18, 248, 182, 70, "blue", [("Follower B (AZ-B)", "name"), ("WAL fsync OK", "sub"), ("ACK in 1.4 ms", "small")], kind="card")
    f2 = f.node(MARGIN + 216, 248, 182, 70, "gray", [("Follower C (AZ-C)", "name"), ("Slow network", "sub"), ("Async catch-up", "small")], kind="tonal")
    ri = f.node(MARGIN + 18, 348, lw - 36, 80, "green", [("3. Commit & ReadIndex", "name"), ("2 of 3 quorum -> Apply & reply 200", "sub"), ("GET confirms quorum heartbeat first", "small")], kind="card")

    f.wire([rtr.bottom(0), ldr.top(0)], tone="teal", width=1.8)
    f.wire([ldr.bottom(-92), f1.top(0)], tone="amber", width=1.8, tail=True)
    f.wire([ldr.bottom(92), f2.top(0)], tone="gray", dash=True, width=1.5)
    f.wire([f1.bottom(0), (f1.cx, ri.y)], tone="green", width=1.8)

    # Right panel: Partition & Fencing
    rx = MARGIN + lw + 24
    rw = WIDTH - MARGIN - rx  # 416
    f.zone(rx, 0, rw, 446, "red", "Failure Path: Partition & Fencing", "Isolated leader fenced by monotonic Raft term", icon="warning")

    f.rect(rx + 18, 62, rw - 36, 118, "card", r=12, lift=True)
    f.pill(rx + 32, 74, "MINORITY PARTITION (1 of 3)", tone="red", anchor="start")
    f.text(rx + 32, 118, "Stale Leader A (Term 4)", "name", "start", tone="red")
    f.text(rx + 32, 140, "Writes stall: no second vote", "sub", "start")
    f.text(rx + 32, 160, "ReadIndex fails -> returns 503", "small", "start")

    f.rule(rx + 18, 202, rx + rw - 18, 202, tone="red", width=2.0, dash="8 5")
    f.label(rx + rw / 2, 206, "NETWORK PARTITION", tone="red", cls="badge", back_cls="c-red")

    f.rect(rx + 18, 226, rw - 36, 202, "card", r=12, lift=True)
    f.pill(rx + 32, 238, "MAJORITY PARTITION (2 of 3)", tone="green", anchor="start")
    f.node(rx + 32, 270, rw - 64, 66, "amber", [("New Leader B (Term 5)", "name"), ("Wins vote with idx >= 42", "sub")], kind="mid", r=10)
    f.node(rx + 32, 348, rw - 64, 66, "blue", [("Follower C (Term 5)", "name"), ("Rejects any RPC where term < 5", "sub")], kind="tonal", r=10)

    return f.save([
        ("Quorum intersection ensures any newly elected majority leader holds every previously committed write.", "noteb"),
        "ReadIndex prevents stale reads from a partitioned leader without physical clock synchronization; leader leases require bounded clock-drift guarantees.",
    ])


# =============================================================================
# CHAPTER 7: DISTRIBUTED RATE LIMITER
# =============================================================================

def ch07_use_cases():
    return build_use_case_fig(
        "ch07_use_cases",
        "Figure 7-1. Actors and Use Cases of the Distributed Rate Limiter.",
        "System Boundary: Distributed Rate Limiter",
        "Edge admission control · Dynamic policy push · Shadow telemetry",
        actors=[
            ("API Client", "External SDKs & callers", "blue", "laptop"),
            ("Platform Operator", "Product & API admins", "purple", "edit_note"),
            ("Security & SRE Team", "Abuse & reliability ops", "teal", "shield"),
        ],
        cases=[
            ("Invoke Protected Endpoint", "200 OK + RateLimit-*  or  429 Retry-After", "blue", "play_arrow"),
            ("Author & Push Quota Policies", "PUT /v1/policies/{tenant}/{route}", "purple", "tune"),
            ("Configure Failure Mode", "Fail-Open (local) vs. Fail-Closed (503)", "amber", "call_split"),
            ("Evaluate Rules in Shadow Mode", "Dry-run verdict logging without blocking", "teal", "rule"),
            ("Monitor Throttles & Hot Keys", "429 burn rates & Count-Min heavy hitters", "green", "notifications_active"),
        ],
        links=[
            (0, [0], "blue"),
            (1, [1, 2], "purple"),
            (2, [3, 4], "teal"),
        ],
        notes=[
            ("External callers interact with the limiter exclusively through HTTP status codes and standardized RateLimit-* headers on protected API responses.", "noteb"),
            "Operators and SRE teams decouple policy updates and shadow-mode validation from live request evaluation.",
        ],
    )


def ch07_architecture():
    f = Fig(
        "ch07_architecture",
        "Figure 7-2. Control Plane and Data Plane Topology of a Distributed Rate Limiting Platform.",
        506,
    )
    # Top: Control Plane
    f.zone(MARGIN, 0, INNER, 144, "purple",
           "Control Plane (Policy Compilation & Shadow Telemetry)",
           "Zero-downtime rule updates · Dry-run shadow evaluation · Heavy-hitter detection",
           icon="settings_suggest", dashed=True)
    c1 = f.node(MARGIN + 18, 60, 258, 68, "purple", [("Policy API & Config DB", "name"), ("Versioned quota rules", "sub")], icon="edit_note", kind="card", icon_size=26)
    c2 = f.node(MARGIN + 298, 60, 260, 68, "purple", [("Rule Compiler & xDS", "name"), ("Sub-second rule push", "sub")], icon="bolt", kind="card", icon_size=26)
    c3 = f.node(MARGIN + 580, 60, 258, 68, "teal", [("Shadow & Telemetry", "name"), ("429 rates & hot keys", "sub")], icon="notifications_active", kind="card", icon_size=26)
    f.wire([c1.right(0), c2.left(0)], tone="purple", width=1.8)

    # Bottom: Data Plane
    f.zone(MARGIN, 174, INNER, 322, "blue",
           "Data Plane (Hot Path: < 1 ms p99 Overhead Across 3 Availability Zones)",
           "L1 local quota lease -> Stateless gRPC limiter -> Sharded Redis Cluster with atomic Lua GCRA",
           icon="layers")

    cli = f.node(MARGIN + 18, 240, 152, 82, "blue", [("Clients", "name"), ("50k-250k RPS", "sub")], icon="laptop", kind="card", icon_size=24)
    gw = f.node(MARGIN + 196, 232, 234, 98, "teal", [("API Gateway (Envoy)", "name"), ("AuthN + L1 lease cache", "sub"), ("Fast-reject 429 path", "small")], icon="shield", kind="card", icon_size=26)
    api = f.node(MARGIN + 462, 240, 176, 82, "green", [("Backend APIs", "name"), ("Allowed traffic", "sub")], icon="apps", kind="card", icon_size=24)
    rej = f.node(MARGIN + 662, 240, 176, 82, "red", [("429 Reject", "name"), ("Retry-After", "sub")], icon="block", kind="mid", icon_size=24)

    rls = f.node(MARGIN + 196, 384, 248, 92, "amber", [("Rate Limiter (gRPC)", "name"), ("Batch leasing & policy", "sub"), ("Circuit breaker guard", "small")], icon="timer", kind="card", icon_size=26)
    red = f.node(MARGIN + 498, 384, 340, 92, "blue", [("Sharded Redis Cluster (3 AZs)", "name"), ("Hash tag {tenant:route} · 1 slot", "sub"), ("Atomic Lua GCRA (8 B/key, TTL)", "small")], icon="memory", kind="card", icon_size=26)

    # Wires
    f.wire([cli.right(0), gw.left(0)], tone="blue", width=2.0)
    f.wire([gw.right(-14), api.left(-14)], tone="green", width=2.0)
    f.label(478, 250, "Allow", tone="green", cls="badge", back_cls="c-blue")

    f.wire([gw.right(22), (476, 303), (476, 348), (782, 348), rej.bottom(0)], tone="red", dash=True, width=1.6)
    f.label(630, 349, "Quota exhausted -> 429", tone="red", cls="small", back_cls="c-blue")

    f.wire([(gw.cx, gw.b), (gw.cx, rls.y)], tone="amber", width=1.9, tail=True)
    f.label(gw.cx - 86, 358, "gRPC ShouldRateLimit", tone="amber", cls="small", back_cls="c-blue")

    f.wire([rls.right(0), red.left(0)], tone="blue", width=1.9, tail=True)
    f.label(502, 412, "EVALSHA", tone="blue", cls="mono", back_cls="c-blue")

    # Control Plane dashed wires (cleanly routed outside cards)
    f.wire([c2.bottom(-20), (c2.cx - 20, 158), (gw.cx, 158), gw.top(0)], tone="purple", dash=True, width=1.6)
    f.wire([red.right(0), (WIDTH - MARGIN - 6, red.cy), (WIDTH - MARGIN - 6, 158), (c3.cx, 158), c3.bottom(0)], tone="teal", dash=True, width=1.5)

    return f.save([
        ("Separating rule compilation (control plane) from quota evaluation (data plane) keeps hot-path p99 under 1 ms.", "noteb"),
        "On Redis store timeout, the gateway circuit breaker enforces the route policy: fail-open with local fallback for general traffic, or fail-closed for authentication and billing endpoints.",
    ])


def ch07_gcra_state_machine():
    f = Fig(
        "ch07_gcra_state_machine",
        "Figure 7-3. Generic Cell Rate Algorithm (GCRA): Single-Timestamp State Machine and Memory Footprint.",
        436,
    )
    f.zone(MARGIN, 0, INNER, 92, "teal",
           "GCRA Equivalence to Token Bucket (O(1) State = One 8-Byte Integer TAT)",
           "Rate R = 5 req/s -> emission interval tau = 200 ms   |   Burst B = 3 -> tolerance T = (B - 1) * tau = 400 ms",
           icon="tune")
    f.text(MARGIN + 18, 76, "Allow: t_now >= TAT - T    |    Update: TAT' = max(t_now, TAT) + tau    |    Wait: (TAT - T) - t_now", "mono", "start", tone="teal")

    # 4 Spacious Step Cards
    steps = [
        ("Req 1 (t = 0 ms)", "TAT = 0 · allow = -400", "ALLOW -> TAT = 200", "green"),
        ("Req 2 (t = 50 ms)", "TAT = 200 · allow = -200", "ALLOW -> TAT = 400", "green"),
        ("Req 3 (t = 100 ms)", "TAT = 400 · allow = 0", "ALLOW -> TAT = 600", "green"),
        ("Req 4 (t = 150 ms)", "TAT = 600 · allow = 200", "REJECT (wait 50 ms)", "red"),
    ]
    cw = 198
    gap = 21
    for i, (hdr, st, dec, tone) in enumerate(steps):
        x = MARGIN + i * (cw + gap)
        card = f.node(x, 114, cw, 124, tone, [
            (hdr, "name"),
            (st, "small"),
            (dec, "monob"),
        ], layout="center", kind="card" if tone == "green" else "mid", r=12, text_tone=tone if tone == "red" else None)
        if i < 3:
            f.wire([card.right(0), (x + cw + gap, card.cy)], tone="wire", width=1.6)

    # Bottom: Memory Comparison
    f.zone(MARGIN, 260, INNER, 166, "blue",
           "Active Memory Footprint Comparison (1,000,000 Active Keys)",
           "Comparing per-key Redis payload, boundary behavior, and concurrency complexity",
           icon="memory")

    cols = [
        ("GCRA (Chosen)", "8 B/key -> 8 MB", "Exact burst; 1 atomic key", "green"),
        ("Token Bucket", "16-64 B -> 64 MB", "2 fields; Lua atomic", "teal"),
        ("Sliding Counter", "16 B/key -> 16 MB", "Approx (~0.003% err)", "blue"),
        ("Sliding Log", "80 KB -> 80 GB", "Unbounded memory", "red"),
    ]
    mw = 196
    mgap = 14
    for i, (title, mem, note, tone) in enumerate(cols):
        mx = MARGIN + 15 + i * (mw + mgap)
        f.node(mx, 322, mw, 86, tone, [
            (title, "name"),
            (mem, "monob"),
            (note, "small"),
        ], layout="center", kind="card" if tone != "red" else "mid", r=10)

    return f.save([
        ("GCRA collapses token-bucket state (tokens and last refill timestamp) into a single 64-bit integer timestamp TAT.", "noteb"),
        "Storing one 8-byte integer per key executes inside a single Redis Lua script with lower memory overhead than multi-field hashes and zero clock-boundary doubling.",
    ])


def ch07_distributed_sync():
    f = Fig(
        "ch07_distributed_sync",
        "Figure 7-4. Distributed Quota Synchronization Patterns: Latency, Accuracy, and Hot-Key Scaling.",
        428,
    )
    cw = 270
    gap = 23
    xs = [MARGIN + i * (cw + gap) for i in range(3)]

    # Col 1
    f.zone(xs[0], 0, cw, 418, "blue", "1. Sync Atomic Lua", "Single-region exactness", icon="lock")
    f.node(xs[0] + 16, 62, cw - 32, 66, "blue", [("Every Request", "name"), ("1 gRPC + 1 Redis Lua", "sub")], kind="card")
    f.node(xs[0] + 16, 152, cw - 32, 72, "amber", [("Redis Cluster Shard", "name"), ("Single-thread GCRA", "sub"), ("Server TIME (no skew)", "small")], kind="card")
    f.wire([(xs[0] + cw / 2, 128), (xs[0] + cw / 2, 152)], tone="blue", width=1.8, tail=True)
    f.node(xs[0] + 16, 244, cw - 32, 156, "gray", [
        ("Engineering Profile", "head"),
        ("p99: 0.5-1.5 ms", "mono"),
        ("Overshoot: 0 (exact)", "mono"),
        ("Hot key: ~80k ops/s", "mono"),
        ("Use: Auth & billing", "sub"),
    ], kind="card")

    # Col 2
    f.zone(xs[1], 0, cw, 418, "teal", "2. Local Quota Lease", "High-QPS & hot-key relief", icon="bolt")
    f.node(xs[1] + 16, 62, cw - 32, 66, "teal", [("Gateway L1 Lease", "name"), ("Prefetch k=50 tokens", "sub")], kind="card")
    f.node(xs[1] + 16, 152, cw - 32, 72, "blue", [("Async Batch Refill", "name"), ("1 Redis call per k reqs", "sub"), ("10-50x less Redis load", "small")], kind="card")
    f.wire([(xs[1] + cw / 2, 128), (xs[1] + cw / 2, 152)], tone="teal", dash=True, width=1.8, tail=True)
    f.node(xs[1] + 16, 244, cw - 32, 156, "gray", [
        ("Engineering Profile", "head"),
        ("p99: ~10 us (L1 RAM)", "mono"),
        ("Overshoot: <= N * k", "mono"),
        ("Hot key: Millions/s", "mono"),
        ("Use: Public APIs & CDN", "sub"),
    ], kind="card")

    # Col 3
    f.zone(xs[2], 0, cw, 418, "purple", "3. Multi-Region Sync", "Global active-active edge", icon="lan")
    f.node(xs[2] + 16, 62, cw - 32, 66, "purple", [("Regional Redis", "name"), ("US / EU / AP local", "sub")], kind="card")
    f.node(xs[2] + 16, 152, cw - 32, 72, "amber", [("Delta-CRDT Gossip", "name"), ("Async sync (200 ms)", "sub"), ("Dynamic quota split", "small")], kind="card")
    f.wire([(xs[2] + cw / 2, 128), (xs[2] + cw / 2, 152)], tone="purple", dash=True, width=1.8, tail=True)
    f.node(xs[2] + 16, 244, cw - 32, 156, "gray", [
        ("Engineering Profile", "head"),
        ("p99: Local region RTT", "mono"),
        ("Overshoot: R * lag", "mono"),
        ("Zero cross-WAN stall", "mono"),
        ("Use: Global edge PoPs", "sub"),
    ], kind="card")

    return f.save([
        ("Cross-region synchronous Redis calls violate a 1 ms p99 SLO by two orders of magnitude due to 60-150 ms WAN RTT.", "noteb"),
        "Production platforms combine Pattern 1 (strict auth/billing keys), Pattern 2 (high-QPS public APIs), and Pattern 3 (multi-region active-active edge deployments).",
    ])


def ch07_failure_defense():
    f = Fig(
        "ch07_failure_defense",
        "Figure 7-5. Defense-in-Depth: Tiered Failure Policies and Adaptive Load Shedding.",
        388,
    )
    s1 = f.node(MARGIN, 124, 182, 140, "purple", [
        ("1. Edge L4 / IP", "name"),
        ("Coarse DDoS filter", "sub"),
        ("eBPF / XDP drop", "mono"),
    ], icon="shield", layout="center", kind="card")

    s2 = f.zone(248, 12, 344, 364, "blue", "2. Policy-Tiered Rate Limiter", "Fallback when Redis is unreachable", icon="call_split")
    fo = f.node(266, 76, 308, 124, "green", [
        ("General APIs (Fail-Open)", "name"),
        ("Catalog, Search, Reads", "sub"),
        ("Fallback: local node bucket", "small"),
    ], icon="play_arrow", kind="card", icon_size=26)
    fc = f.node(266, 224, 308, 128, "red", [
        ("Auth & Billing (Fail-Closed)", "name"),
        ("Login, OTP, Payments", "sub"),
        ("Return 503 + Retry-After", "small"),
    ], icon="lock", kind="mid", icon_size=26)

    s3 = f.zone(628, 12, WIDTH - MARGIN - 628, 364, "amber", "3. Backend Shedding", "Protects under aggregate load", icon="warning")
    aimd = f.node(646, 76, 224, 124, "amber", [
        ("AIMD Concurrency", "name"),
        ("Little's Law: L = lam*W", "mono"),
        ("Back off on queue spike", "small"),
    ], kind="card")
    prio = f.node(646, 224, 224, 128, "teal", [
        ("CoDel & Priority", "name"),
        ("Shed batch traffic first", "sub"),
        ("Preserve p999 checkout", "small"),
    ], kind="card")

    f.wire([s1.right(-28), (230, 166), (230, fo.cy), fo.left(0)], tone="green", width=1.9)
    f.wire([s1.right(28), (230, 222), (230, fc.cy), fc.left(0)], tone="red", width=1.9)
    f.wire([fo.right(0), aimd.left(0)], tone="teal", width=1.9)
    f.wire([fc.right(0), prio.left(0)], tone="amber", dash=True, width=1.7)

    return f.save([
        ("Rate limiting enforces per-caller fairness; adaptive load shedding protects service stability when aggregate valid traffic exceeds capacity.", "noteb"),
        "Both layers are required in production: 10,000 well-behaved clients staying inside their individual quotas can still saturate a downstream database during a traffic spike.",
    ])


# =============================================================================
# CHAPTER 19: DISTRIBUTED PAYMENT SYSTEM
# =============================================================================

def ch19_use_cases():
    return build_use_case_fig(
        "ch19_use_cases",
        "Figure 19-1. Actors and Use Cases of the Distributed Payment Platform.",
        "System Boundary: Distributed Payment Platform",
        "Idempotent orchestration · Double-entry ledger · PCI-DSS CDE vault",
        actors=[
            ("Merchant / Checkout", "Storefronts & billing APIs", "blue", "laptop"),
            ("External PSP / Rail", "Card networks & banks", "purple", "lan"),
            ("Finance & Auditor", "Treasury & compliance", "teal", "library_books"),
        ],
        cases=[
            ("Authorize & Capture Charge", "POST /v1/payments (Idempotency-Key)", "blue", "save"),
            ("Full or Partial Refund", "POST /v1/payments/{id}/refunds", "amber", "swap_horiz"),
            ("Deliver Webhooks & T+1 Files", "Signed async status + clearing batch", "purple", "notifications_active"),
            ("Query Double-Entry Ledger", "GET /v1/accounts/{id}/entries", "teal", "table_rows"),
            ("Run Three-Way Reconciliation", "Join Ledger vs. PSP vs. Bank (T+2)", "green", "rule"),
        ],
        links=[
            (0, [0, 1], "blue"),
            (1, [2], "purple"),
            (2, [3, 4], "teal"),
        ],
        notes=[
            ("Merchant requests always carry a caller-supplied Idempotency-Key and an opaque card token issued directly by the isolated PCI-DSS vault.", "noteb"),
            "External PSPs and banks act asynchronously outside the local ACID boundary, making webhooks and T+2 reconciliation mandatory.",
        ],
    )


def ch19_architecture():
    f = Fig(
        "ch19_architecture",
        "Figure 19-2. Payment Platform Architecture with PCI-DSS CDE Isolation and Async Clearing.",
        536,
    )
    shop = f.node(MARGIN, 10, 220, 82, "blue", [
        ("Merchant / Checkout", "name"),
        ("POST /v1/payments", "mono"),
    ], icon="laptop", kind="card", icon_size=26)

    gw = f.node(278, 10, 228, 82, "teal", [
        ("Payment API Gateway", "name"),
        ("mTLS · AuthZ · Rate Limit", "sub"),
    ], icon="shield", kind="card", icon_size=26)

    cde_x = 538
    cde_w = WIDTH - MARGIN - cde_x  # 350
    f.zone(
        cde_x, 0, cde_w, 166, "red",
        "PCI-DSS Vault Zone (CDE)",
        "Isolated VPC · Zero PANs leave CDE",
        icon="lock", dashed=True,
    )
    vault = f.node(cde_x + 16, 60, cde_w - 32, 88, "red", [
        ("Tokenization Vault & HSM", "name"),
        ("PAN <-> tok_9f2a · EMV", "mono"),
        ("Direct egress to PSPs", "small"),
    ], icon="shield", kind="card", icon_size=26)

    core = f.zone(
        MARGIN, 120, 474, 240, "blue",
        "Non-CDE Payment Core (3 Availability Zones)",
        "Stores opaque tokens only · Synchronous quorum ACID durability",
        icon="layers",
    )
    orch = f.node(MARGIN + 18, 180, 438, 72, "teal", [
        ("Payment Orchestrator (Stateless · 12 Pods)", "name"),
        ("Atomic phases · Zero DB locks during PSP RPC", "sub"),
    ], icon="engineering", kind="card", icon_size=26)
    db = f.node(MARGIN + 18, 268, 438, 76, "amber", [
        ("Core Ledger & Idempotency DB (3-AZ Quorum)", "name"),
        ("idempotency · payments · ledger · outbox", "mono"),
    ], icon="save", kind="card", icon_size=26)

    psp = f.node(cde_x, 200, cde_w, 160, "purple", [
        ("External PSPs & Card Rails", "name"),
        ("Issuer <-> Visa/MC <-> Acquirer", "sub"),
        ("RTT 200-5000 ms · Unreliable", "small"),
        ("Webhooks + T+1 Clearing", "mono"),
    ], icon="lan", layout="center", kind="card", icon_size=28)

    bg = f.zone(
        MARGIN, 392, INNER, 134, "green",
        "Asynchronous Clearing, Recovery & Three-Way Reconciliation Tier",
        "Guarantees convergence across internal ledger, PSP clearing files, and bank cash statements",
        icon="loop",
    )
    f.node(MARGIN + 18, 450, 260, 62, "green", [("CDC Outbox -> Kafka", "name"), ("Debezium WAL tailing", "sub")], kind="card")
    f.node(MARGIN + 298, 450, 260, 62, "amber", [("Poller & Webhooks", "name"), ("Resolves UNKNOWN state", "sub")], kind="card")
    f.node(MARGIN + 578, 450, 260, 62, "teal", [("T+1 / T+2 Reconciler", "name"), ("Ledger vs. PSP vs. Bank", "sub")], kind="card")

    f.wire([shop.right(0), gw.left(0)], tone="blue", width=2.0)
    f.wire([gw.bottom(0), (gw.cx, core.y)], tone="teal", width=2.0)
    f.wire([orch.bottom(0), db.top(0)], tone="amber", width=1.9, tail=True)
    f.wire([orch.right(-14), (520, 202), (520, vault.cy), vault.left(0)], tone="red", dash=True, width=1.7, tail=True)
    f.wire([orch.right(14), (520, 230), (520, 264), psp.left(-16)], tone="purple", width=1.9, tail=True)
    f.wire([db.bottom(-90), (db.cx - 90, bg.y)], tone="green", width=1.8)
    f.wire([psp.bottom(-45), (psp.cx - 45, bg.y)], tone="purple", dash=True, width=1.7, tail=True)
    f.wire([psp.bottom(45), (psp.cx + 45, bg.y)], tone="teal", dash=True, width=1.7)

    return f.save([
        ("Isolating raw card numbers inside the PCI-DSS CDE vault removes the payment core, ledger, Kafka, and analytics pipelines from PCI compliance scope.", "noteb"),
        "State mutations commit atomically with a transactional outbox record; downstream notifications and settlement workflows never drift from the ledger.",
    ])


def ch19_atomic_phases():
    f = Fig(
        "ch19_atomic_phases",
        "Figure 19-3. Atomic-Phase Idempotency and Recovery Points Across Unreliable PSP Calls.",
        452,
    )
    p1 = f.zone(MARGIN, 0, INNER, 126, "blue",
                "Phase 1: Local ACID Transaction (< 5 ms), Reserve Key and Intent",
                "Recovery point: STARTED -> PENDING_PSP (zero external network I/O)",
                icon="lock")
    f.node(MARGIN + 18, 58, 258, 52, "blue", [("1. Lock Idempotency Key", "name"), ("Verify SHA-256 hash", "sub")], kind="card")
    f.node(MARGIN + 298, 58, 260, 52, "amber", [("2. Insert PENDING Row", "name"), ("Assign stable psp_ref_id", "sub")], kind="card")
    f.node(MARGIN + 580, 58, 258, 52, "green", [("3. Post Hold & COMMIT", "name"), ("Release DB locks now", "sub")], kind="card")
    f.wire([(MARGIN + 276, 84), (MARGIN + 298, 84)], tone="blue", width=1.8)
    f.wire([(MARGIN + 558, 84), (MARGIN + 580, 84)], tone="blue", width=1.8)

    p2 = f.zone(MARGIN, 152, INNER, 132, "purple",
                "Phase 2: External PSP RPC (200-5,000 ms), Zero Database Locks Held",
                "Deterministic psp_ref_id deduplicates retries; timeout leaves payment UNKNOWN",
                icon="lan", dashed=True)
    rpc = f.node(MARGIN + 18, 210, 268, 58, "purple", [("Call PSP Authorize/Capture", "name"), ("Idempotent psp_ref_id", "mono")], kind="card")
    ok = f.node(MARGIN + 320, 210, 232, 58, "green", [("Definite Reply", "name"), ("APPROVED or DECLINED", "mono")], kind="card")
    unk = f.node(MARGIN + 584, 210, 254, 58, "red", [("Timeout / 5xx / Crash", "name"), ("Outcome = UNKNOWN", "sub")], kind="mid")
    f.wire([rpc.right(-10), ok.left(-10)], tone="green", width=1.8)
    f.wire([rpc.right(14), (308, 253), (308, 276), (572, 276), (572, 253), unk.left(14)], tone="red", dash=True, width=1.6)

    p3 = f.zone(MARGIN, 310, INNER, 134, "green",
                "Phase 3: Finalize ACID Transaction (< 5 ms), Commit Ledger and Reply",
                "Conditional update WHERE state = PENDING_PSP; retries replay cached response",
                icon="save")
    f.node(MARGIN + 18, 368, 258, 60, "green", [("If APPROVED", "name"), ("CAPTURED + ledger + outbox", "sub")], kind="card")
    f.node(MARGIN + 298, 368, 260, 60, "amber", [("If DECLINED", "name"), ("DECLINED + cache 422 reply", "sub")], kind="card")
    f.node(MARGIN + 580, 368, 258, 60, "red", [("If UNKNOWN", "name"), ("Keep PENDING; poller queries", "sub")], kind="mid")

    f.wire([(MARGIN + 148, p1.b), (MARGIN + 148, p2.y)], tone="purple", width=1.8)
    f.wire([(ok.cx, p2.b), (ok.cx, p3.y)], tone="green", width=1.8)
    f.wire([(unk.cx, p2.b), (unk.cx, p3.y)], tone="red", dash=True, width=1.8)

    return f.save([
        ("Holding a database transaction open across a 3-second PSP call exhausts connection pools and causes cascading outages.", "noteb"),
        "If the orchestrator crashes after Phase 1 or during Phase 2, a retry bearing the same Idempotency-Key observes PENDING_PSP and queries the PSP by psp_ref_id before advancing.",
    ])


def ch19_hot_account_ledger():
    f = Fig(
        "ch19_hot_account_ledger",
        "Figure 19-4. Immutable Double-Entry Ledger Invariant and Hot-Account Sub-Account Sharding.",
        438,
    )
    lw = 416
    f.zone(MARGIN, 0, lw, 428, "teal", "Immutable Double-Entry Journal", "Append-only rows · Integer cents · SUM == 0", icon="table_rows")
    f.node(MARGIN + 16, 62, lw - 32, 102, "blue", [
        ("tx_9001 (Charge EUR 40.00)", "name"),
        ("DEBIT  customer_ada  -4000 EUR", "mono"),
        ("CREDIT merchant_42   +3884 EUR", "mono"),
        ("CREDIT platform_fee   +116 EUR (sum=0)", "monob"),
    ], kind="card")
    f.node(MARGIN + 16, 180, lw - 32, 102, "amber", [
        ("tx_9044 (Append-Only Refund)", "name"),
        ("DEBIT  merchant_42   -3884 EUR", "mono"),
        ("DEBIT  platform_fee   -116 EUR", "mono"),
        ("CREDIT customer_ada  +4000 EUR (sum=0)", "monob"),
    ], kind="card")
    f.node(MARGIN + 16, 298, lw - 32, 114, "teal", [
        ("Accounting Invariants", "head"),
        ("1. int64 minor units + ISO-4217 code", "small"),
        ("2. Explicit remainder bucket on splits", "small"),
        ("3. Trigger enforces zero-sum per tx_id", "small"),
    ], kind="tonal")

    rx = MARGIN + lw + 24
    rw = WIDTH - MARGIN - rx  # 416
    f.zone(rx, 0, rw, 428, "amber", "Hot-Account Contention Sharding", "Eliminates row-lock queues on high-TPS accounts", icon="call_split")
    f.node(rx + 16, 62, rw - 32, 78, "red", [
        ("Bottleneck: Single Merchant Row", "name"),
        ("1,000 TPS SELECT ... FOR UPDATE", "mono"),
        ("Serializes payments on one lock", "small"),
    ], kind="mid")

    sol = f.node(rx + 16, 162, rw - 32, 58, "teal", [
        ("Write Fan-Out: hash(payment_id) % K", "name"),
        ("Distributes credits across K=16 buckets", "sub"),
    ], kind="card")

    sw = 88
    sgap = 10
    for i, lbl in enumerate(["#0", "#1", "#2", "..#15"]):
        sx = rx + 16 + i * (sw + sgap)
        f.cell(sx, 244, sw, 52, "blue", [(f"m42{lbl}", "monob"), ("Lock-free", "small")], kind="card")
        f.wire([(sol.cx, sol.b), (sx + sw / 2, 244)], tone="teal", width=1.4)

    rollup = f.node(rx + 16, 326, rw - 32, 86, "green", [
        ("Async Balance Rollup", "name"),
        ("Master = SUM(sub_accounts #0..#15)", "mono"),
        ("Periodic checkpoints bound read scan", "small"),
    ], kind="card")
    f.wire([(rx + rw / 2, 296), rollup.top(0)], tone="green", dash=True, width=1.8)

    return f.save([
        ("Double-entry bookkeeping converts data corruption into a verifiable conservation law: every transaction sums strictly to zero.", "noteb"),
        "Hot-account sharding applies to credit-heavy clearing and fee accounts; debit accounts enforcing strict overdraft checks use single-owner partitions (such as TigerBeetle).",
    ])


def ch19_reconciliation_pipeline():
    f = Fig(
        "ch19_reconciliation_pipeline",
        "Figure 19-5. Three-Way Financial Reconciliation Pipeline Across T+0 to T+2 Settlement.",
        420,
    )
    s1 = f.node(MARGIN, 24, 242, 102, "blue", [
        ("1. Internal Ledger", "name"),
        ("Immutable T+0 entries", "sub"),
        ("Source of intent", "monob"),
    ], icon="save", kind="card", icon_size=26)

    s2 = f.node(MARGIN, 154, 242, 102, "purple", [
        ("2. PSP Clearing File", "name"),
        ("T+1 batch (fees & FX)", "sub"),
        ("Source of capture", "monob"),
    ], icon="description", kind="card", icon_size=26)

    s3 = f.node(MARGIN, 284, 242, 102, "teal", [
        ("3. Bank Statement", "name"),
        ("T+2 MT940 / ISO 20022", "sub"),
        ("Source of cash truth", "monob"),
    ], icon="library_books", kind="card", icon_size=26)

    eng_x = 316
    eng_w = 248
    f.zone(eng_x, 54, eng_w, 304, "amber", "Reconciliation Engine", "Deterministic 3-way join", icon="rule")
    f.node(eng_x + 16, 118, eng_w - 32, 76, "amber", [("Join Keys", "name"), ("psp_ref_id + currency", "mono"), ("amount + date", "small")], kind="card")
    f.node(eng_x + 16, 212, eng_w - 32, 128, "gray", [
        ("Automated Checks", "head"),
        ("1. Exact 1:1:1 match", "small"),
        ("2. T+1/T+2 cutoff window", "small"),
        ("3. Fee & FX variance", "small"),
        ("4. Duplicate / orphan alert", "small"),
    ], kind="card")

    rx = 606
    rw = WIDTH - MARGIN - rx  # 282
    o1 = f.node(rx, 18, rw, 82, "green", [("Matched & Settled", "name"), ("Clear suspense -> cash", "sub")], icon="play_arrow", kind="card", icon_size=24)
    o2 = f.node(rx, 118, rw, 82, "blue", [("Timing Difference", "name"), ("Carry T+1; alert > 72h", "sub")], icon="schedule", kind="card", icon_size=24)
    o3 = f.node(rx, 218, rw, 82, "amber", [("Fee / FX Variance", "name"), ("Book adjusting entry", "sub")], icon="tune", kind="card", icon_size=24)
    o4 = f.node(rx, 318, rw, 82, "red", [("Critical Break", "name"), ("Page SRE + hold payout", "sub")], icon="error", kind="mid", icon_size=24)

    f.wire([s1.right(0), (296, s1.cy), (296, 150), (eng_x, 150)], tone="blue", width=1.8)
    f.wire([s2.right(0), (eng_x, s2.cy)], tone="purple", width=1.8)
    f.wire([s3.right(0), (296, s3.cy), (296, 270), (eng_x, 270)], tone="teal", width=1.8)

    f.wire([(eng_x + eng_w, 128), (586, 128), (586, o1.cy), o1.left(0)], tone="green", width=1.8)
    f.wire([(eng_x + eng_w, 180), (586, 180), (586, o2.cy), o2.left(0)], tone="blue", width=1.8)
    f.wire([(eng_x + eng_w, 240), (586, 240), (586, o3.cy), o3.left(0)], tone="amber", width=1.8)
    f.wire([(eng_x + eng_w, 296), (586, 296), (586, o4.cy), o4.left(0)], tone="red", width=1.8)

    return f.save([
        ("Reconciliation is the ultimate safety net of a payment platform because external card rails operate outside local ACID transactions.", "noteb"),
        "Classifying breaks into timing differences versus genuine cash shortfalls prevents alert fatigue while catching duplicate charges or missing settlements within 24 hours.",
    ])


from draw_m3_part1 import ALL as PART1_ALL
from draw_m3_part2 import ALL as PART2_ALL
from draw_m3_part3 import ALL as PART3_ALL
from draw_m3_part45 import ALL as PART45_ALL
from draw_m3_part6 import ALL as PART6_ALL

ALL = [
    ch01_use_cases,
    ch01_architecture,
    ch01_consistency_models,
    ch01_partitioning_vnodes,
    ch01_replication_failover,
    *PART1_ALL,
    ch07_use_cases,
    ch07_architecture,
    ch07_gcra_state_machine,
    ch07_distributed_sync,
    ch07_failure_defense,
    *PART2_ALL,
    *PART3_ALL,
    ch19_use_cases,
    ch19_architecture,
    ch19_atomic_phases,
    ch19_hot_account_ledger,
    ch19_reconciliation_pipeline,
    *PART45_ALL,
    *PART6_ALL,
]


def main():
    total_problems = 0
    for fn in ALL:
        problems = fn()
        total_problems += problems
        print(f"generated {fn.__name__} (light + dark) -> {problems} fit warnings")
    print(f"Done: {len(ALL)} figures ({len(ALL)*2} SVGs), total fit warnings: {total_problems}")
    if total_problems:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
