#!/usr/bin/env python3
"""Generate 18 spacious Material Design 3 light+dark SVG figures for Part II (Chapters 8-13).

Every figure uses WIDTH = 920, MARGIN = 32, INNER = 856, separates control and
data planes clearly, and enforces zero text overflow or overlap in Chrome.
"""
from figkit_m3 import Fig, WIDTH, MARGIN, build_use_case_fig

INNER = WIDTH - 2 * MARGIN  # 856px usable width


def step_badge(f, cx, cy, num, tone="blue", ring="paper"):
    """Draw a high-contrast circular step badge (r=10 + 3px halo) for light & dark modes."""
    f.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="13.0" class="{ring}"/>')
    f.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="10.0" class="a-{tone}"/>')
    f.add(f'<text x="{cx:.1f}" y="{cy + 3.7:.1f}" text-anchor="middle" class="badge paper">{num}</text>')


def badge_on_seg(f, p1, p2, num, tone="blue", ring="paper", head=True, tail=False):
    """Center a step badge on straight wire segment p1->p2, accounting for 9px arrowheads."""
    x1, y1 = float(p1[0]), float(p1[1])
    x2, y2 = float(p2[0]), float(p2[1])
    dx, dy = x2 - x1, y2 - y1
    length = (dx * dx + dy * dy) ** 0.5
    if length < 45.5:
        raise ValueError(f"Badged wire segment for step {num} is too short: {length:.1f}px (< 46px)")
    ux, uy = dx / length, dy / length
    start_off = 9.0 if tail else 0.0
    end_off = 9.0 if head else 0.0
    mid_dist = (start_off + (length - end_off)) / 2.0
    cx = x1 + ux * mid_dist
    cy = y1 + uy * mid_dist
    step_badge(f, cx, cy, num, tone=tone, ring=ring)
    return cx, cy


def path_legend(f, y, sync_text="Solid: Sync data path (1->5)", async_text="Dashed: Async / control plane"):
    """Draw a compact legend strip distinguishing synchronous data vs async/control wires."""
    f.rect(MARGIN, y, INNER, 28, "c-gray", r=8)
    f.wire([(MARGIN + 18, y + 14), (MARGIN + 52, y + 14)], tone="blue", width=2.0)
    f.text(MARGIN + 60, y + 18, sync_text, "small", "start", tone="blue")
    mid = MARGIN + INNER / 2 + 12
    f.wire([(mid, y + 14), (mid + 34, y + 14)], tone="purple", dash=True, width=1.7)
    f.text(mid + 42, y + 18, async_text, "small", "start", tone="purple")


# =============================================================================
# CHAPTER 8: DISTRIBUTED UNIQUE ID GENERATOR
# =============================================================================

def ch08_use_cases():
    return build_use_case_fig(
        "ch08_use_cases",
        "Figure 8-1. Actors and Use Cases of the Distributed Unique ID Generator.",
        "System Boundary: Distributed Unique ID Generator",
        "Zero-coordination 64-bit IDs · K-sortable ordering · Worker leasing",
        actors=[
            ("Application Service", "Orders, feeds & events", "blue", "laptop"),
            ("Control Plane Admin", "Fleet & datacenter ops", "purple", "engineering"),
            ("Observability Agent", "NTP drift & saturation", "teal", "notifications_active"),
        ],
        cases=[
            ("Generate Single 64-Bit ID", "POST /v1/ids:allocate -> uint64", "blue", "bolt"),
            ("Allocate Batched ID Block", "POST /v1/ids:batchAllocate?count=N", "teal", "view_module"),
            ("Decode Embedded Metadata", "Extract timestamp, worker & seq", "amber", "code"),
            ("Lease & Reclaim Worker ID", "Acquire unique 10-bit worker_id", "purple", "handshake"),
            ("Monitor Clock Drift & Rate", "NTP offset, rollback & seq alerts", "green", "timer"),
        ],
        links=[
            (0, [0, 1, 2], "blue"),
            (1, [3], "purple"),
            (2, [4], "teal"),
        ],
        notes=[
            ("Application services invoke the stateless data plane for sub-millisecond ID issuance while administrative tooling manages worker-ID leases.", "noteb"),
            "Separating lease acquisition from per-request generation eliminates cross-node coordination on the hot path.",
        ],
    )


def ch08_architecture():
    f = Fig(
        "ch08_architecture",
        "Figure 8-2. Control Plane Worker-ID Leasing and Zero-Coordination ID Generation Path.",
        586,
    )
    # Top-left: Clients
    cli = f.node(
        MARGIN, 10, 286, 82, "blue",
        [("Application Clients", "name"), ("gRPC / HTTP/2 · Batch prefetch", "sub")],
        icon="laptop", kind="card", icon_size=26,
    )

    # Top-right: Control Plane
    cp_x = 356
    cp_w = WIDTH - MARGIN - cp_x  # 532
    f.zone(
        cp_x, 0, cp_w, 162, "purple",
        "Control Plane (Worker-ID Lease Coordinator)",
        "3-node etcd / ZooKeeper quorum · Leases unique 10-bit worker_id (0..1023)",
        icon="settings_suggest", dashed=True,
    )
    lease_q = f.node(
        cp_x + 18, 60, 238, 84, "purple",
        [("Lease Quorum (etcd)", "name"), ("Ephemeral lock · TTL 30 s", "sub")],
        icon="dns", kind="card", icon_size=26,
    )
    clk_guard = f.node(
        cp_x + 274, 60, 240, 84, "purple",
        [("Epoch Checkpoint Store", "name"), ("Persists max_ts per worker", "sub")],
        icon="schedule", kind="card", icon_size=26,
    )

    # Middle-left: Edge Load Balancer (50px below cli)
    lb_zone = f.zone(
        MARGIN, 142, 286, 134, "teal",
        "Data Plane: Local-AZ Proxy",
        "Zone-aware L7 routing · < 0.5 ms",
        icon="swap_horiz",
    )
    lb_node = f.node(
        MARGIN + 16, 196, 254, 68, "teal",
        [("Stateless Edge Router", "name"), ("Local-AZ affinity · Zero state", "sub")],
        icon="call_split", kind="card", icon_size=26,
    )

    # Bottom: Shared-Nothing Generator Fleet (50px below lb_zone)
    fleet = f.zone(
        MARGIN, 326, INNER, 212, "blue",
        "Data Plane: Shared-Nothing Snowflake Generator Fleet (Multi-AZ)",
        "Zero inter-node RPC on the hot path · Lock-free 64-bit atomic state per generator host",
        icon="layers",
    )
    cw = 262
    cgap = 18
    cx_list = [MARGIN + 17 + i * (cw + cgap) for i in range(3)]
    hosts = [
        ("AZ-A · Worker 0x014", "Atomic CAS · 4,096/ms", "Monotonic clock + lease", "blue"),
        ("AZ-B · Worker 0x109", "Atomic CAS · 4,096/ms", "Monotonic clock + lease", "teal"),
        ("AZ-C · Worker 0x2F1", "Atomic CAS · 4,096/ms", "Monotonic clock + lease", "green"),
    ]
    for i, (hdr, top_line, bot_line, tone) in enumerate(hosts):
        x = cx_list[i]
        f.rect(x, 382, cw, 142, "card", r=12, lift=True)
        f.text(x + 14, 404, hdr, "name", "start", tone=tone, fit=(x + 10, x + cw - 10))
        f.node(x + 12, 416, cw - 24, 46, tone, [(top_line, "monob")], kind="mid", r=8)
        f.node(x + 12, 470, cw - 24, 42, "gray", [(bot_line, "small")], kind="tonal", r=8)

    # Orthogonal wires with >= 50px segments and mathematically centered badges
    p1_s, p1_e = cli.bottom(0), (cli.cx, lb_zone.y)
    f.wire([p1_s, p1_e], tone="blue", width=2.0)
    badge_on_seg(f, p1_s, p1_e, "1", "blue")
    f.label(cli.cx + 78, 117, "POST /v1/ids:allocate", tone="blue", cls="small")

    p2_s, p2_e = (lb_zone.cx, lb_zone.b), (lb_zone.cx, fleet.y)
    f.wire([p2_s, p2_e], tone="teal", width=2.0)
    badge_on_seg(f, p2_s, p2_e, "2", "teal")
    f.label(lb_zone.cx + 84, 301, "Local-AZ gRPC call", tone="teal", cls="small")

    p3_s, p3_e = (lease_q.cx, 162), (lease_q.cx, fleet.y)
    f.wire([p3_s, p3_e], tone="purple", dash=True, width=1.6, tail=True)
    badge_on_seg(f, p3_s, p3_e, "3", "purple", head=True, tail=True)
    f.label(lease_q.cx + 88, 248, "Lease & 10 s keepalive", tone="purple", cls="small")

    p4_s, p4_e = (clk_guard.cx, 162), (clk_guard.cx, fleet.y)
    f.wire([p4_s, p4_e], tone="purple", dash=True, width=1.6, tail=True)
    badge_on_seg(f, p4_s, p4_e, "4", "purple", head=True, tail=True)
    f.label(clk_guard.cx + 78, 248, "Boot max_ts verify", tone="purple", cls="small")

    path_legend(
        f, 550,
        "Solid: Sync hot path (1 Client -> 2 Local-AZ Proxy -> RAM CAS)",
        "Dashed: Boot/keepalive control plane (3 Lease, 4 Epoch)",
    )

    return f.save([
        ("Generators contact the control plane only on boot and periodic lease renewal (3-4); every ID request (1-2) resolves strictly in local RAM.", "noteb"),
        "If the lease quorum suffers a transient outage, active hosts continue serving until lease expiry and then fail closed to prevent duplicate worker IDs.",
    ])


def ch08_clock_drift():
    f = Fig(
        "ch08_clock_drift",
        "Figure 8-3. 64-Bit Snowflake Layout and Monotonic Clock-Regression Defense.",
        474,
    )
    # Top Zone: Bit Layout
    f.zone(
        MARGIN, 0, INNER, 146, "blue",
        "64-Bit Signed Integer Layout (Big-Endian K-Sortable)",
        "Fits native BIGINT primary keys and preserves sequential B-tree index append locality",
        icon="code",
    )
    fields = [
        ("Sign", "1b · 0", "bit 63", 90, "gray"),
        ("Timestamp (ms since epoch)", "41 bits · 69.7 yr", "bits 62..22", 312, "blue"),
        ("Datacenter + Worker ID", "10 bits · 1,024 hosts", "bits 21..12", 214, "purple"),
        ("Per-ms Sequence", "12 bits · 4,096/ms", "bits 11..0", 190, "teal"),
    ]
    cur_x = MARGIN + 16
    for idx, (title, detail, rng, w, tone) in enumerate(fields):
        f.node(cur_x, 56, w, 62, tone, [
            (title, "name" if w >= 190 else "badge"),
            (detail, "mono" if w >= 190 else "small"),
        ], layout="center", kind="mid" if tone != "gray" else "tonal", r=8)
        f.text(cur_x + w / 2, 134, rng, "small", "middle", fit=(cur_x, cur_x + w))
        cur_x += w + 6

    # Bottom Zone: Clock Regression Defense (symmetric 1-to-3 split bus with 50px trunk & branches)
    f.zone(
        MARGIN, 166, INNER, 298, "amber",
        "Clock-Regression Defense Pipeline (Triggered When t_now < last_ts)",
        "Wall-clock adjustments from NTP step sync, leap seconds, or VM migration must never emit duplicate IDs",
        icon="shield",
    )
    tiers = [
        ("Tier 1: Small Drift (delta <= 5 ms)", "Spin-wait until t_now >= last_ts; zero caller errors", "green", "timer"),
        ("Tier 2: Moderate (5 ms < delta <= 500 ms)", "Advance logical last_ts or consume sequence reserve", "amber", "tune"),
        ("Tier 3: Severe Drift (delta > 500 ms)", "Fail closed (HTTP 503), release worker lease, page SRE", "red", "block"),
    ]
    tx = 350
    tw = WIDTH - MARGIN - tx - 18  # 520
    t_boxes = []
    for i, (hdr, sub, tone, ic) in enumerate(tiers):
        ty = 224 + i * 78
        tb = f.node(tx, ty, tw, 64, tone, [(hdr, "name"), (sub, "sub")], icon=ic, kind="card" if tone != "red" else "mid", icon_size=24)
        t_boxes.append(tb)

    trig = f.node(
        MARGIN + 18, t_boxes[1].cy - 59, 200, 118, "red",
        [
            ("Clock Regressed", "name"),
            ("delta = last_ts - t_now", "mono"),
            ("Anchor: CLOCK_MONOTONIC", "small"),
        ],
        icon="warning", layout="center", kind="mid", icon_size=26,
    )

    x_mid = (trig.r + tx) / 2.0  # (250 + 350) / 2 = 300.0 (50px trunk + 50px equal branches)
    f.wire([trig.right(0), (x_mid, trig.cy)], tone="red", head=False, width=1.9)
    badge_on_seg(f, trig.right(0), (x_mid, trig.cy), "1", "red", ring="c-amber", head=False, tail=False)

    f.wire([(x_mid, t_boxes[0].cy), (x_mid, t_boxes[2].cy)], tone="amber", head=False, width=1.9)
    for idx, (tb, tone) in enumerate(zip(t_boxes, ("green", "amber", "red"))):
        b_s, b_e = (x_mid, tb.cy), tb.left(0)
        f.wire([b_s, b_e], tone=tone, width=1.9)
        badge_on_seg(f, b_s, b_e, str(idx + 2), tone, ring="c-amber")

    return f.save([
        ("Combining CLOCK_MONOTONIC for runtime elapsed deltas with a persisted max_ts checkpoint prevents duplicate IDs across both live NTP steps and reboots.", "noteb"),
        "Using NTP slewing (chrony) keeps normal clock drift under 1 ms, ensuring Tier 3 fail-closed ejections occur only during severe host faults.",
    ])


# =============================================================================
# CHAPTER 9: DISTRIBUTED CACHE
# =============================================================================

def ch09_use_cases():
    return build_use_case_fig(
        "ch09_use_cases",
        "Figure 9-1. Actors and Use Cases of the Distributed Cache Service.",
        "System Boundary: Distributed Cache Service",
        "Sub-millisecond RAM tier · Consistent sharding · Stampede defense",
        actors=[
            ("Application Service", "Read-heavy web & API hosts", "blue", "laptop"),
            ("Cache Operator", "Capacity & ring manager", "purple", "engineering"),
            ("Origin & CDC Stream", "OLTP DB & binlog tailer", "teal", "save"),
        ],
        cases=[
            ("Lookup and Populate Key", "GET / SET key value EX ttl", "blue", "bolt"),
            ("Coalesce Concurrent Misses", "Singleflight lock per hot key", "teal", "handshake"),
            ("Rebalance Hash Ring & Warm", "Add or drain nodes with vnodes", "purple", "tune"),
            ("Invalidate Stale Entries", "DEL key via write path or CDC", "amber", "close"),
            ("Track Hit Ratio & Evictions", "W-TinyLFU metrics & RAM alerts", "green", "memory"),
        ],
        links=[
            (0, [0, 1], "blue"),
            (1, [2, 4], "purple"),
            (2, [3], "teal"),
        ],
        notes=[
            ("Application services read through the low-latency cache-aside path while CDC streams asynchronously purge stale keys after database commits.", "noteb"),
            "Virtual-node ring management allows operators to scale cluster memory horizontally while remapping only 1/N of cached keys.",
        ],
    )


def ch09_architecture():
    f = Fig(
        "ch09_architecture",
        "Figure 9-2. Control Plane Ring Management and Sharded Cache Data Plane.",
        586,
    )
    # Top-left: Entry Devices & Clients
    cli = f.node(
        MARGIN, 10, 286, 82, "blue",
        [("Mobile / Web / App Clients", "name"), ("L7 LB · Cache-aside binary", "sub")],
        icon="laptop", kind="card", icon_size=26,
    )

    # Top-right: Control Plane
    cp_x = 356
    cp_w = WIDTH - MARGIN - cp_x  # 532
    f.zone(
        cp_x, 0, cp_w, 154, "purple",
        "Control Plane (Ring & Health Coordinator)",
        "Config quorum + active health checks · Publishes consistent hash ring epoch",
        icon="settings_suggest", dashed=True,
    )
    ring_mgr = f.node(
        cp_x + 18, 56, 238, 80, "purple",
        [("Ring Membership Map", "name"), ("256 vnodes · Epoch v18", "sub")],
        icon="dns", kind="card", icon_size=26,
    )
    hotkey_mgr = f.node(
        cp_x + 274, 56, 240, 80, "purple",
        [("Hot-Key & Auto-Scaler", "name"), ("Detect skew · Replicate hot", "sub")],
        icon="tune", kind="card", icon_size=26,
    )

    # Middle-left: Proxy Tier (50px below cli)
    proxy_z = f.zone(
        MARGIN, 142, 286, 132, "teal",
        "Data Plane: Cache Proxy Tier",
        "L1 local cache + request coalescing",
        icon="swap_horiz",
    )
    proxy_n = f.node(
        MARGIN + 16, 194, 254, 68, "teal",
        [("Smart Client / Mcrouter", "name"), ("Consistent hash · Singleflight", "sub")],
        icon="call_split", kind="card", icon_size=26,
    )

    # Bottom-left: Sharded Cache Cluster (52px below proxy_z)
    cache_w = 526
    cache_z = f.zone(
        MARGIN, 326, cache_w, 214, "blue",
        "Data Plane: Sharded In-Memory Cache Tier (Multi-AZ)",
        "Slab allocator · W-TinyLFU eviction · Active-standby shard replicas",
        icon="memory",
    )
    sw = 158
    sgap = 10
    for i, (stitle, srng, ssub, tone) in enumerate([
        ("Shard A (AZ-A)", "Ring 0..33%", "Primary + Standby", "blue"),
        ("Shard B (AZ-B)", "Ring 33..66%", "Primary + Standby", "teal"),
        ("Shard C (AZ-C)", "Ring 66..100%", "Primary + Standby", "green"),
    ]):
        sx = MARGIN + 16 + i * (sw + sgap)
        f.rect(sx, 382, sw, 144, "card", r=12, lift=True)
        f.text(sx + sw / 2, 405, stitle, "name", "middle", tone=tone, fit=(sx + 6, sx + sw - 6))
        f.node(sx + 10, 418, sw - 20, 44, tone, [(srng, "monob")], kind="mid", r=8)
        f.node(sx + 10, 470, sw - 20, 42, "gray", [(ssub, "small")], kind="tonal", r=8)

    # Bottom-right: Origin Database & CDC (54px gap from cache_z)
    orig_x = MARGIN + cache_w + 54  # 612
    orig_w = WIDTH - MARGIN - orig_x  # 276
    orig_z = f.zone(
        orig_x, 326, orig_w, 214, "amber",
        "Origin & CDC Tier",
        "Cold miss & invalidation",
        icon="save",
    )
    oltp = f.node(
        orig_x + 14, 380, orig_w - 28, 54, "amber",
        [("Authoritative OLTP DB", "name"), ("Serves coalesced misses", "sub")],
        icon="table_rows", kind="card", icon_size=24,
    )
    cdc = f.node(
        orig_x + 14, 480, orig_w - 28, 50, "green",
        [("CDC Invalidation", "name"), ("Binlog -> async DEL key", "sub")],
        icon="loop", kind="card", icon_size=24,
    )

    # Zero-crossing orthogonal wires with >= 46px badged segments
    p1_s, p1_e = cli.bottom(0), (cli.cx, proxy_z.y)
    f.wire([p1_s, p1_e], tone="blue", width=2.0)
    badge_on_seg(f, p1_s, p1_e, "1", "blue")
    f.label(cli.cx + 76, 117, "GET / SET / DEL", tone="blue", cls="small")

    f.wire([hotkey_mgr.left(0), ring_mgr.right(0)], tone="purple", dash=True, width=1.6)
    f.wire([ring_mgr.bottom(0), (ring_mgr.cx, 204), proxy_n.right(-24)], tone="purple", dash=True, width=1.6)
    f.label(420, 196, "Ring & hot-key watch", tone="purple", cls="small")

    p2_s, p2_e = (proxy_z.cx, proxy_z.b), (proxy_z.cx, cache_z.y)
    f.wire([p2_s, p2_e], tone="teal", width=2.0)
    badge_on_seg(f, p2_s, p2_e, "2", "teal")
    f.label(proxy_z.cx + 82, 300, "Shard hit (< 1 ms)", tone="teal", cls="small")

    f.wire([proxy_n.right(14), (orig_z.cx, proxy_n.cy + 14), (orig_z.cx, orig_z.y)], tone="amber", width=1.9)
    badge_on_seg(f, (orig_z.cx, proxy_n.cy + 14), (orig_z.cx, orig_z.y), "3", "amber")
    f.label(534, proxy_n.cy + 8, "Coalesced miss read", tone="amber", cls="small")

    p4_s, p4_e = oltp.bottom(0), cdc.top(0)
    f.wire([p4_s, p4_e], tone="amber", dash=True, width=1.6)
    badge_on_seg(f, p4_s, p4_e, "4", "amber", ring="c-amber")

    p5_s, p5_e = (orig_z.x, cdc.cy), (cache_z.r, cdc.cy)
    f.wire([p5_s, p5_e], tone="green", dash=True, width=1.8)
    badge_on_seg(f, p5_s, p5_e, "5", "green")

    path_legend(
        f, 550,
        "Solid: Sync read/miss path (1 Client -> 2 Cache -> 3 Origin)",
        "Dashed: Ring watch, binlog (4) & async CDC DEL (5)",
    )

    return f.save([
        ("Cache hits resolve in one network hop between the smart proxy and the target RAM shard (1-2), shielding the origin database (3) from 99%+ of read load.", "noteb"),
        "Asynchronous CDC invalidation (4-5) complements write-path deletes so stale entries converge quickly even if an application host crashes mid-request.",
    ])


def ch09_stampede_defense():
    f = Fig(
        "ch09_stampede_defense",
        "Figure 9-3. Singleflight Request Coalescing and Probabilistic Early Expiration.",
        476,
    )
    # Top Zone: Singleflight (dead-straight >= 48px wires with centered badges 1-4)
    f.zone(
        MARGIN, 0, INNER, 232, "blue",
        "1. Singleflight Request Coalescing (Cold-Miss Thundering Herd Collapse)",
        "1,000 simultaneous cache misses for a hot key collapse into exactly one origin database query",
        icon="handshake",
    )
    herd = f.node(
        MARGIN + 18, 60, 170, 156, "red",
        [("1,000 Misses", "name"), ("Key: catalog:top", "mono"), ("Expired at t = 0", "small")],
        icon="warning", layout="center", kind="mid", icon_size=26,
    )
    gate = f.node(
        MARGIN + 242, 60, 210, 156, "blue",
        [("Singleflight Gate", "name"), ("Req 1 acquires mutex", "sub"), ("Req 2..1000 await", "mono")],
        icon="lock", layout="center", kind="card", icon_size=26,
    )
    origin = f.node(
        MARGIN + 512, 60, 326, 54, "amber",
        [("Single Origin DB Fetch", "name"), ("1 query (~12 ms) instead of 1,000", "sub")],
        icon="save", kind="card", icon_size=24,
    )
    bcast = f.node(
        MARGIN + 512, 162, 326, 54, "green",
        [("Populate Cache & Broadcast", "name"), ("SET key + wake 999 waiting callers", "sub")],
        icon="play_arrow", kind="card", icon_size=24,
    )
    p1_s, p1_e = herd.right(0), gate.left(0)
    f.wire([p1_s, p1_e], tone="red", width=1.9)
    badge_on_seg(f, p1_s, p1_e, "1", "red", ring="c-blue")

    p2_s, p2_e = (gate.r, origin.cy), origin.left(0)
    f.wire([p2_s, p2_e], tone="amber", width=1.9)
    badge_on_seg(f, p2_s, p2_e, "2", "amber", ring="c-blue")

    p3_s, p3_e = origin.bottom(0), bcast.top(0)
    f.wire([p3_s, p3_e], tone="green", width=1.9)
    badge_on_seg(f, p3_s, p3_e, "3", "green", ring="c-blue")

    p4_s, p4_e = bcast.left(0), (gate.r, bcast.cy)
    f.wire([p4_s, p4_e], tone="green", dash=True, width=1.7)
    badge_on_seg(f, p4_s, p4_e, "4", "green", ring="c-blue")

    # Bottom Zone: XFetch (50px gaps with centered badges 5-6)
    f.zone(
        MARGIN, 248, INNER, 218, "teal",
        "2. Probabilistic Early Expiration (XFetch Algorithm)",
        "One reader triggers an asynchronous recompute before hard TTL expiry using compute cost delta",
        icon="timer",
    )
    f.node(
        MARGIN + 18, 304, INNER - 36, 38, "teal",
        [("Refresh early if:   t_now - delta * beta * ln(rand(0, 1)) >= expiry", "monob")],
        layout="center", kind="card", r=8,
    )
    phases = [
        ("Phase A: 0..80% TTL", "Pure RAM Hit Path", "P(refresh) ~ 0 · zero origin I/O", "green"),
        ("Phase B: 80..99% TTL", "Probabilistic Window", "One reader triggers async reload", "teal"),
        ("Phase C: 100% TTL", "Seamless Cutover", "Fresh TTL installed before expiry", "blue"),
    ]
    pw = 240
    pgap = 50
    p_boxes = []
    for i, (hdr, sub, foot, tone) in enumerate(phases):
        px = MARGIN + 18 + i * (pw + pgap)
        pb = f.node(px, 358, pw, 90, tone, [(hdr, "name"), (sub, "monob"), (foot, "small")], layout="center", kind="card", r=10)
        p_boxes.append(pb)
    p5_s, p5_e = p_boxes[0].right(0), p_boxes[1].left(0)
    f.wire([p5_s, p5_e], tone="teal", width=1.8)
    badge_on_seg(f, p5_s, p5_e, "5", "teal", ring="c-teal")

    p6_s, p6_e = p_boxes[1].right(0), p_boxes[2].left(0)
    f.wire([p6_s, p6_e], tone="blue", width=1.8)
    badge_on_seg(f, p6_s, p6_e, "6", "blue", ring="c-teal")

    return f.save([
        ("Singleflight (1-4) protects the database during cold starts and unexpected evictions; XFetch (5-6) prevents hot keys from ever hitting a synchronous miss.", "noteb"),
        "Tuning beta > 1 biases XFetch toward earlier background refresh for expensive queries with large recomputation latency delta.",
    ])


# =============================================================================
# CHAPTER 10: DISTRIBUTED LOCK SERVICE
# =============================================================================

def ch10_use_cases():
    return build_use_case_fig(
        "ch10_use_cases",
        "Figure 10-1. Actors and Use Cases of the Distributed Lock Service.",
        "System Boundary: Distributed Lock Service",
        "Linearizable Raft leases · Monotonic fencing tokens · Session watch",
        actors=[
            ("Worker / Application", "Competing distributed nodes", "blue", "laptop"),
            ("Protected Resource", "Storage or external API", "teal", "save"),
            ("Cluster Operator", "SRE & quorum administrator", "purple", "engineering"),
        ],
        cases=[
            ("Acquire Exclusive Lease", "POST /v1/locks/{k} -> {lease, token}", "blue", "lock"),
            ("Renew Active Lease Heartbeat", "POST /v1/leases/{id}:renew", "green", "timer"),
            ("Release Lock Voluntarily", "DELETE /v1/locks/{k}?token=T", "amber", "logout"),
            ("Validate Monotonic Fence Token", "Reject write if token < max_seen", "teal", "shield"),
            ("Audit Quorum & Active Leases", "Inspect Raft term, leader & holders", "purple", "tune"),
        ],
        links=[
            (0, [0, 1, 2], "blue"),
            (1, [3], "teal"),
            (2, [4], "purple"),
        ],
        notes=[
            ("Clients obtain bounded leases and monotonic fencing tokens from the Raft lock service, then attach the token to every write against the protected resource.", "noteb"),
            "Cooperating storage engines enforce true mutual exclusion by rejecting any request carrying a lower fencing token than previously accepted.",
        ],
    )


def ch10_architecture():
    f = Fig(
        "ch10_architecture",
        "Figure 10-2. Raft-Backed Lock Service, Lease Renewal, and Storage Fencing Path.",
        584,
    )
    # Top-left: Client Tier
    cli_z = f.zone(
        MARGIN, 0, 316, 250, "blue",
        "Client Tier (Worker Contenders)",
        "Session keepalive & lock watch",
        icon="laptop",
    )
    c1 = f.node(
        MARGIN + 16, 62, 284, 78, "green",
        [("Worker A (Lease Holder)", "name"), ("Lease #42 · Token = 34", "mono")],
        icon="lock", kind="card", icon_size=24,
    )
    c2 = f.node(
        MARGIN + 16, 156, 284, 78, "gray",
        [("Worker B (Waiting)", "name"), ("Watches expiry · Backoff", "sub")],
        icon="hourglass_top", kind="card", icon_size=24,
    )

    # Top-right: Raft Consensus Lock Service (50px internal gap between leader & followers)
    cp_x = 394
    cp_w = WIDTH - MARGIN - cp_x  # 494
    raft_z = f.zone(
        cp_x, 0, cp_w, 250, "purple",
        "Consensus Plane (5-Node Raft Lock Service)",
        "Linearizable lease state machine across 3 AZs · Monotonic Raft index token",
        icon="settings_suggest", dashed=True,
    )
    leader = f.node(
        cp_x + 18, 62, 204, 78, "amber",
        [("Raft Leader (AZ-A)", "name"), ("Token = Raft index", "sub")],
        icon="dns", kind="card", icon_size=24,
    )
    followers = f.node(
        cp_x + 272, 62, 204, 78, "purple",
        [("4 Raft Followers", "name"), ("Quorum (3 of 5)", "sub")],
        icon="layers", kind="card", icon_size=24,
    )
    wheel = f.node(
        cp_x + 18, 156, cp_w - 36, 78, "teal",
        [("Lease Expiry Wheel & Watch Stream", "name"), ("Revokes silent leases after TTL · Notifies queued contenders", "sub")],
        icon="schedule", kind="card", icon_size=24,
    )

    # Bottom: Fenced Storage Tier (50px gaps between guard, engine, audit)
    stor_z = f.zone(
        MARGIN, 306, INNER, 228, "teal",
        "Data Plane: Fenced Resource & Storage Tier (Enforces Mutual Exclusion)",
        "Every state-mutating request must carry a fencing token verified atomically against max_token",
        icon="shield",
    )
    guard = f.node(
        MARGIN + 18, 376, 240, 134, "teal",
        [("Fencing Guard", "name"), ("IF req.token < max:", "mono"), ("  return 409 STALE", "monob")],
        icon="rule", layout="center", kind="card", icon_size=26,
    )
    engine = f.node(
        MARGIN + 308, 376, 240, 134, "blue",
        [("Primary Storage Engine", "name"), ("Atomic write + update", "sub"), ("max_token = 34", "monob")],
        icon="save", layout="center", kind="card", icon_size=26,
    )
    audit = f.node(
        MARGIN + 598, 376, 240, 134, "amber",
        [("Stale-Write Audit Log", "name"), ("Records rejected tokens", "sub"), ("Alerts split-brain GC", "small")],
        icon="description", layout="center", kind="card", icon_size=26,
    )

    # Orthogonal wires with >= 50px badged segments — ZERO card crossings
    p1_s, p1_e = c1.right(0), leader.left(0)
    f.wire([p1_s, p1_e], tone="green", width=1.9, tail=True)
    badge_on_seg(f, p1_s, p1_e, "1", "green", head=True, tail=True)
    f.label((p1_s[0] + p1_e[0]) / 2, 81, "Keepalive", tone="green", cls="small")

    f.wire([c2.right(0), wheel.left(0)], tone="purple", dash=True, width=1.7, tail=True)
    f.label((c2.r + wheel.x) / 2, 180, "Watch", tone="purple", cls="small")

    p2_s, p2_e = leader.right(0), followers.left(0)
    f.wire([p2_s, p2_e], tone="amber", width=1.8, tail=True)
    badge_on_seg(f, p2_s, p2_e, "2", "amber", ring="c-purple", head=True, tail=True)
    f.wire([leader.bottom(0), (leader.cx, wheel.y)], tone="teal", width=1.6)

    # Route Worker A -> Fencing Guard cleanly via outer left gutter (never touches Worker B!)
    f.wire([c1.left(0), (16, c1.cy), (16, 278), (guard.cx, 278), (guard.cx, stor_z.y)], tone="green", width=2.0)
    badge_on_seg(f, (16, 278), (guard.cx, 278), "3", "green", head=False, tail=False)
    f.label(guard.cx + 96, 282, "Write(payload, token=34)", tone="green", cls="small")

    p4_s, p4_e = guard.right(-18), engine.left(-18)
    f.wire([p4_s, p4_e], tone="blue", width=1.9)
    badge_on_seg(f, p4_s, p4_e, "4", "blue", ring="c-teal")

    f.wire([guard.right(28), (guard.r + 18, guard.cy + 28), (guard.r + 18, 522), (audit.cx, 522), audit.bottom(0)], tone="red", dash=True, width=1.6)
    p5_s, p5_e = engine.right(0), audit.left(0)
    f.wire([p5_s, p5_e], tone="amber", dash=True, width=1.6)
    badge_on_seg(f, p5_s, p5_e, "5", "amber", ring="c-teal")

    path_legend(
        f, 548,
        "Solid: Sync lease & fenced write (1 Acquire -> 2 Quorum -> 3-4 Write)",
        "Dashed: Watch stream & stale-token audit (5)",
    )

    return f.save([
        ("Using the Raft log commit index as the fencing token (1-2) guarantees strict monotonicity across leader elections without extra consensus rounds.", "noteb"),
        "A lock service provides liveness and coordination, whereas the fenced storage guard (3-5) enforces safety under arbitrary process pauses or network delays.",
    ])


def ch10_fencing_tokens():
    f = Fig(
        "ch10_fencing_tokens",
        "Figure 10-3. Monotonic Fencing Tokens Preventing Stale-Lease Corruption After GC Pause.",
        482,
    )
    axis_x1, axis_x2 = 224, WIDTH - MARGIN - 12
    f.text(MARGIN, 20, "Participant", "head", "start")
    f.text(axis_x1, 20, "Execution Timeline (t0 -> t5)", "head", "start", tone="blue")
    f.wire([(axis_x1, 34), (axis_x2, 34)], tone="wire", width=1.5)
    t_xs = [axis_x1 + idx * (axis_x2 - axis_x1 - 24) / 5 for idx in range(6)]
    for idx, tx in enumerate(t_xs):
        f.rule(tx, 30, tx, 464, tone="gray", width=1.0, dash="3 4")
        f.text(tx, 50, f"t{idx}", "small", "middle")

    # Lane 1: Client 1
    y1 = 62
    f.zone(MARGIN, y1, INNER, 92, "blue", "Client 1 (Old Holder)", "Suffers stop-the-world GC")
    f.cell(228, y1 + 42, 126, 40, "green", [("Acquire T=33", "monob")], kind="card")
    f.cell(362, y1 + 42, 352, 40, "red", [("GC Pause (45 s) · Lease Expires", "monob")], kind="mid")
    f.cell(722, y1 + 42, 152, 40, "amber", [("Write (T=33)", "monob")], kind="card")

    # Lane 2: Raft Lock Service
    y2 = 166
    f.zone(MARGIN, y2, INNER, 92, "purple", "Lock Service (Raft)", "Monotonic token counter")
    f.cell(228, y2 + 42, 126, 40, "blue", [("Grant T=33", "monob")], kind="card")
    f.cell(378, y2 + 42, 126, 40, "red", [("Expire T=33", "monob")], kind="mid")
    f.cell(514, y2 + 42, 126, 40, "green", [("Grant T=34", "monob")], kind="card")

    # Lane 3: Client 2
    y3 = 270
    f.zone(MARGIN, y3, INNER, 92, "teal", "Client 2 (New Holder)", "Acquires after expiry")
    f.cell(514, y3 + 42, 126, 40, "green", [("Acquire T=34", "monob")], kind="card")
    f.cell(648, y3 + 42, 126, 40, "teal", [("Write (T=34)", "monob")], kind="card")

    # Lane 4: Fenced Storage Service
    y4 = 374
    f.zone(MARGIN, y4, INNER, 92, "amber", "Fenced Storage", "Checks token >= max")
    f.cell(228, y4 + 42, 170, 40, "gray", [("max_token = 32", "mono")], kind="card")
    f.cell(554, y4 + 42, 158, 40, "green", [("OK T=34 (max=34)", "monob")], kind="card")
    f.cell(720, y4 + 42, 156, 40, "red", [("REJECT T=33 < 34", "monob")], kind="mid")

    # Clean vertical handoff wires (>= 64px) with centered numbered step badges 1-4
    p1_s, p1_e = (291, y2 + 42), (291, y1 + 82)
    f.wire([p1_s, p1_e], tone="blue", width=1.7)
    badge_on_seg(f, p1_s, p1_e, "1", "blue", ring="c-purple")

    p2_s, p2_e = (577, y2 + 82), (577, y3 + 42)
    f.wire([p2_s, p2_e], tone="green", width=1.7)
    badge_on_seg(f, p2_s, p2_e, "2", "green", ring="paper")

    p3_s, p3_e = (680, y3 + 82), (680, y4 + 42)
    f.wire([p3_s, p3_e], tone="teal", width=1.7)
    badge_on_seg(f, p3_s, p3_e, "3", "teal", ring="paper")

    p4_s, p4_e = (798, y1 + 82), (798, y4 + 42)
    f.wire([p4_s, p4_e], tone="red", dash=True, width=1.8)
    badge_on_seg(f, p4_s, p4_e, "4", "red", ring="paper")

    return f.save([
        ("Process pauses from garbage collection, page faults, or hypervisor stalls invalidate any client-side assumption that a lease (1) is still active.", "noteb"),
        "Because Client 2 already acquired and persisted token 34 (2-3) to the storage server, Client 1's delayed write carrying token 33 (4) is deterministically rejected with HTTP 409.",
    ])


# =============================================================================
# CHAPTER 11: DISTRIBUTED MESSAGE QUEUE
# =============================================================================

def ch11_use_cases():
    return build_use_case_fig(
        "ch11_use_cases",
        "Figure 11-1. Actors and Use Cases of the Distributed Message Queue.",
        "System Boundary: Distributed Message Queue",
        "Partitioned commit log · Consumer groups · Durable offset replay",
        actors=[
            ("Producer Service", "Event publishers & APIs", "blue", "laptop"),
            ("Consumer Group", "Competing worker instances", "teal", "apps"),
            ("Platform Operator", "Topic & broker administrator", "purple", "engineering"),
        ],
        cases=[
            ("Produce Partitioned Batch", "PRODUCE(topic, key, batch, acks=all)", "blue", "bolt"),
            ("Poll Ordered Log Segments", "FETCH(topic, part, offset, bytes)", "teal", "table_rows"),
            ("Commit & Replay Offsets", "COMMIT(group, part, offset) / SEEK", "green", "save"),
            ("Join Group & Rebalance", "Cooperative sticky partition assign", "amber", "swap_horiz"),
            ("Manage Topics & Retention", "Partitions, RF=3, TTL & compaction", "purple", "tune"),
        ],
        links=[
            (0, [0], "blue"),
            (1, [1, 2, 3], "teal"),
            (2, [4], "purple"),
        ],
        notes=[
            ("Producers append immutable record batches to topic partitions; consumer groups coordinate partition ownership and track progress via durable offsets.", "noteb"),
            "Retaining log segments on disk after consumption enables independent consumer groups and deterministic historical replay.",
        ],
    )


def ch11_architecture():
    f = Fig(
        "ch11_architecture",
        "Figure 11-2. Metadata Controller, Partitioned Commit Log Brokers, and Consumer Groups.",
        586,
    )
    # Top-left: Producers
    prod = f.node(
        MARGIN, 10, 286, 82, "blue",
        [("App / Edge Producers", "name"), ("Batching · hash(key) % P · acks=all", "sub")],
        icon="laptop", kind="card", icon_size=26,
    )

    # Top-right: Control Plane
    cp_x = 356
    cp_w = WIDTH - MARGIN - cp_x  # 532
    f.zone(
        cp_x, 0, cp_w, 126, "purple",
        "Control Plane (KRaft Metadata & Group Coordinator)",
        "3-node Raft metadata log · Tracks topic partitions, ISR sets, and consumer offsets",
        icon="settings_suggest", dashed=True,
    )
    ctrl = f.node(
        cp_x + 18, 54, 238, 62, "purple",
        [("Active Controller", "name"), ("Leader election & ISR", "sub")],
        icon="dns", kind="card", icon_size=24,
    )
    gcoord = f.node(
        cp_x + 274, 54, 240, 62, "purple",
        [("Group Coordinator", "name"), ("Rebalance & __offsets", "sub")],
        icon="handshake", kind="card", icon_size=24,
    )

    # Middle: Partitioned Brokers (50px internal gaps for ISR replication wire)
    brk_z = f.zone(
        MARGIN, 174, INNER, 198, "blue",
        "Data Plane: Partitioned Broker Cluster (Append-Only Commit Logs Across 3 AZs)",
        "Sequential disk append · Page-cache zero-copy sendfile() · In-Sync Replica (ISR) quorum",
        icon="layers",
    )
    bw = 240
    bgap = 50
    bx_list = [MARGIN + 18 + i * (bw + bgap) for i in range(3)]
    brokers = [
        ("Broker 1 (AZ-A)", "P0 LEADER [0..94]", "P1 Follower (ISR)", "amber"),
        ("Broker 2 (AZ-B)", "P1 LEADER [0..88]", "P2 Follower (ISR)", "amber"),
        ("Broker 3 (AZ-C)", "P2 LEADER [0..91]", "P0 Follower (ISR)", "amber"),
    ]
    for i, (hdr, lead, fol, tone) in enumerate(brokers):
        bx = bx_list[i]
        f.rect(bx, 226, bw, 134, "card", r=12, lift=True)
        f.text(bx + 14, 248, hdr, "name", "start", tone="blue", fit=(bx + 10, bx + bw - 10))
        f.node(bx + 12, 258, bw - 24, 44, tone, [(lead, "monob")], kind="mid", r=8)
        f.node(bx + 12, 310, bw - 24, 40, "gray", [(fol, "mono")], kind="tonal", r=8)

    # Bottom: Consumer Group (54px below brk_z)
    cons_z = f.zone(
        MARGIN, 426, INNER, 114, "teal",
        "Data Plane: Consumer Group (1 Partition -> Exactly 1 Active Consumer)",
        "Horizontal throughput scales linearly up to partition count P while preserving per-key order",
        icon="apps",
    )
    c_boxes = []
    for i, (cname, csub) in enumerate([
        ("Consumer C1", "Owns P0 · offset 94"),
        ("Consumer C2", "Owns P1 · offset 88"),
        ("Consumer C3", "Owns P2 · offset 91"),
    ]):
        cb = f.node(bx_list[i], 478, bw, 50, "teal", [(cname, "name"), (csub, "mono")], kind="card")
        c_boxes.append(cb)

    # Orthogonal wires with >= 48px segments and centered badges
    p1_s, p1_e = prod.bottom(0), (prod.cx, brk_z.y)
    f.wire([p1_s, p1_e], tone="blue", width=2.0)
    badge_on_seg(f, p1_s, p1_e, "1", "blue")
    f.label(prod.cx + 88, 132, "Batch append (acks=all)", tone="blue", cls="small")

    # Step 2: Explicit ISR replication wires between brokers (50px each)
    isr_y = 293
    p2_s, p2_e = (bx_list[0] + bw, isr_y), (bx_list[1], isr_y)
    f.wire([p2_s, p2_e], tone="amber", width=1.9)
    badge_on_seg(f, p2_s, p2_e, "2", "amber", ring="c-blue")
    f.wire([(bx_list[1] + bw, isr_y), (bx_list[2], isr_y)], tone="amber", width=1.9)

    # Step 3: Parallel symmetric FETCH wires (54px each)
    for i in range(3):
        cx = bx_list[i] + bw / 2
        f.wire([(cx, brk_z.b), (cx, cons_z.y)], tone="teal", width=1.9)
    badge_on_seg(f, (bx_list[0] + bw / 2, brk_z.b), (bx_list[0] + bw / 2, cons_z.y), "3", "teal")
    f.label((bx_list[1] + bw / 2 + bx_list[2] + bw / 2) / 2, 403, "Zero-copy FETCH", tone="teal", cls="small")

    # Step 4: KRaft metadata & group rebalance control wires (48px each, bidirectional)
    p4_s, p4_e = (ctrl.cx, 126), (ctrl.cx, brk_z.y)
    f.wire([p4_s, p4_e], tone="purple", dash=True, width=1.6, tail=True)
    badge_on_seg(f, p4_s, p4_e, "4", "purple", head=True, tail=True)
    f.label(ctrl.cx - 72, 154, "Metadata & ISR", tone="purple", cls="small")

    f.wire([(gcoord.cx - 36, 126), (gcoord.cx - 36, brk_z.y)], tone="purple", dash=True, width=1.6, tail=True)
    f.label(gcoord.cx - 104, 154, "Group rebalance", tone="purple", cls="small")

    # Step 5: Async offset commit routed cleanly via right outer gutter (x=904) to symmetric gcoord.cx + 36
    f.wire([cons_z.right(0), (904, cons_z.cy), (904, 150), (gcoord.cx + 36, 150), (gcoord.cx + 36, 126)], tone="purple", dash=True, width=1.6)
    badge_on_seg(f, (904, cons_z.cy), (904, 150), "5", "purple", head=False, tail=False)

    path_legend(
        f, 550,
        "Solid: Sync log path (1 Produce -> 2 ISR -> 3 FETCH)",
        "Dashed: KRaft metadata (4) & async offset commit (5)",
    )

    return f.save([
        ("Keyed routing places all events for the same entity onto one partition (1-2), guaranteeing strict per-key ordering without global serialization.", "noteb"),
        "Producers writing with acks=all wait until every In-Sync Replica (ISR) appends the batch; consumers poll via zero-copy sendfile() (3) while KRaft coordinates metadata (4) and async offset commits (5).",
    ])


def ch11_partition_rebalance():
    f = Fig(
        "ch11_partition_rebalance",
        "Figure 11-3. Cooperative Consumer Group Rebalance and Offset Commit Semantics.",
        466,
    )
    # Top Zone: Cooperative Rebalance
    f.zone(
        MARGIN, 0, INNER, 232, "teal",
        "Incremental Cooperative Rebalance (Zero Stop-the-World Pause)",
        "Consumer C3 joins a group owning partitions P0..P3; unaffected partitions P0..P2 keep processing",
        icon="swap_horiz",
    )
    stages = [
        ("Stage 1: Steady State", "C1: {P0, P1} · active", "C2: {P2, P3} · active", "C3 sends JoinGroup", "blue"),
        ("Stage 2: Selective Revoke", "C1 keeps {P0, P1} live", "C2 commits & revokes P3", "Zero pause on P0..P2", "amber"),
        ("Stage 3: Balanced Group", "C1: {P0, P1} · active", "C2: {P2} · active", "C3: {P3} from offset", "green"),
    ]
    sw = 240
    sgap = 50
    s_boxes = []
    for i, (hdr, l1, l2, l3, tone) in enumerate(stages):
        sx = MARGIN + 18 + i * (sw + sgap)
        sb = f.node(sx, 62, sw, 152, tone, [
            (hdr, "name"),
            (l1, "mono"),
            (l2, "mono"),
            (l3, "small"),
        ], layout="center", kind="card", r=12)
        s_boxes.append(sb)
    p1_s, p1_e = s_boxes[0].right(0), s_boxes[1].left(0)
    f.wire([p1_s, p1_e], tone="amber", width=1.9)
    badge_on_seg(f, p1_s, p1_e, "1", "amber", ring="c-teal")

    p2_s, p2_e = s_boxes[1].right(0), s_boxes[2].left(0)
    f.wire([p2_s, p2_e], tone="green", width=1.9)
    badge_on_seg(f, p2_s, p2_e, "2", "green", ring="c-teal")

    # Bottom Zone: Offset Commit Semantics
    f.zone(
        MARGIN, 252, INNER, 204, "blue",
        "Offset Commit Timing and Delivery Guarantees",
        "Ordering between downstream side effects and offset commits governs crash recovery semantics",
        icon="rule",
    )
    modes = [
        ("At-Most-Once", "Commit BEFORE process", "Crash drops batch", "Metrics & best-effort", "amber"),
        ("At-Least-Once (Default)", "Commit AFTER process", "Crash replays batch", "Idempotent consumer", "green"),
        ("Exactly-Once (EOS)", "Atomic tx: out + offset", "Read-committed filter", "Higher broker latency", "purple"),
    ]
    mw = 262
    mgap = 18
    for i, (hdr, l1, l2, l3, tone) in enumerate(modes):
        mx = MARGIN + 17 + i * (mw + mgap)
        f.node(mx, 312, mw, 128, tone, [
            (hdr, "name"),
            (l1, "monob"),
            (l2, "sub"),
            (l3, "small"),
        ], layout="center", kind="card", r=10)

    return f.save([
        ("Eager rebalancing halts every consumer in the group during membership changes; cooperative sticky rebalancing pauses only the migrated partitions.", "noteb"),
        "Most production pipelines pair at-least-once delivery with idempotent downstream writes to avoid the latency tax of cross-partition transactions.",
    ])


# =============================================================================
# CHAPTER 12: DISTRIBUTED JOB SCHEDULER
# =============================================================================

def ch12_use_cases():
    return build_use_case_fig(
        "ch12_use_cases",
        "Figure 12-1. Actors and Use Cases of the Distributed Job Scheduler.",
        "System Boundary: Distributed Job Scheduler",
        "Cron & DAG workflows · Lease-based dispatch · Dead-letter recovery",
        actors=[
            ("Job Author / Service", "Product & data pipelines", "blue", "laptop"),
            ("Worker Node Pool", "Stateless task executors", "teal", "developer_board"),
            ("Operations & SRE", "On-call & DLQ triage", "purple", "engineering"),
        ],
        cases=[
            ("Submit One-Shot, Cron, or DAG", "POST /v1/jobs (schedule, retries)", "blue", "schedule"),
            ("Pause, Cancel, or Trigger Run", "PATCH /v1/jobs/{id}/state", "amber", "tune"),
            ("Claim Lease & Heartbeat Task", "Pull task · extend TTL · report ACK", "teal", "handshake"),
            ("Replay Dead-Letter Jobs", "Inspect trace & requeue failed run", "red", "loop"),
            ("Audit Run History & Lag SLO", "Dispatch delay & worker metrics", "green", "description"),
        ],
        links=[
            (0, [0, 1], "blue"),
            (1, [2], "teal"),
            (2, [3, 4], "purple"),
        ],
        notes=[
            ("Clients declare schedule specifications and retry budgets once; the scheduler owns durable timing, dependency resolution, and failure recovery.", "noteb"),
            "Decoupling scheduling state from stateless worker pools lets operators scale compute independently of dispatch coordination.",
        ],
    )


def ch12_architecture():
    f = Fig(
        "ch12_architecture",
        "Figure 12-2. Control Plane DAG Registry, Sharded Time-Wheel Dispatch, and Worker Pool.",
        586,
    )
    # Top-left: Clients aligned vertically with Scheduler API for dead-straight wire
    cli = f.node(
        MARGIN, 56, 292, 76, "blue",
        [("Web / API Job Clients", "name"), ("POST /v1/jobs · Cron & DAG", "sub")],
        icon="laptop", kind="card", icon_size=26,
    )

    # Top-right: Control Plane (50px internal gap between api and db)
    cp_x = 376
    cp_w = WIDTH - MARGIN - cp_x  # 512
    f.zone(
        cp_x, 0, cp_w, 148, "purple",
        "Control Plane (Job Registry & DAG State Store)",
        "Validates cron & DAG specs · Persists durable schedules across 3 AZs",
        icon="settings_suggest", dashed=True,
    )
    api = f.node(
        cp_x + 18, 56, 212, 76, "purple",
        [("Scheduler API Tier", "name"), ("Cron parse · DAG check", "sub")],
        icon="rule", kind="card", icon_size=24,
    )
    db = f.node(
        cp_x + 280, 56, 214, 76, "amber",
        [("Metadata & Run DB", "name"), ("jobs · runs · deps", "mono")],
        icon="save", kind="card", icon_size=24,
    )

    # Middle: Sharded Time-Wheel Dispatch
    disp_z = f.zone(
        MARGIN, 188, INNER, 150, "amber",
        "Data Plane: Sharded Time-Wheel Dispatch Tier (Partitioned by Hash & run_at)",
        "Polls upcoming 60 s window from DB, buffers in RAM time wheels, and emits due tasks",
        icon="schedule",
    )
    dw = 258
    dgap = 24
    d_boxes = []
    for i, (hdr, sub, ic, tone) in enumerate([
        ("Sharded DB Pollers", "FOR UPDATE SKIP LOCKED", "table_rows", "amber"),
        ("Hashed Time Wheel", "O(1) tick · Jitter spread", "timer", "teal"),
        ("Partitioned Work Queue", "Priority lanes + retries", "view_week", "blue"),
    ]):
        dx = MARGIN + 17 + i * (dw + dgap)
        dbx = f.node(dx, 248, dw, 74, tone, [(hdr, "name"), (sub, "mono" if i == 0 else "sub")], icon=ic, kind="card", icon_size=24)
        d_boxes.append(dbx)
    f.wire([d_boxes[0].right(0), d_boxes[1].left(0)], tone="amber", width=1.8)
    f.wire([d_boxes[1].right(0), d_boxes[2].left(0)], tone="blue", width=1.8)

    # Bottom: Worker Pool & Recovery (50px internal gaps)
    wrk_z = f.zone(
        MARGIN, 378, INNER, 160, "green",
        "Data Plane: Stateless Worker Execution Pool, Lease Reaper, and DLQ",
        "Workers execute idempotent tasks with fencing attempt_id while the reaper reclaims crashed leases",
        icon="developer_board",
    )
    w1 = f.node(MARGIN + 18, 440, 240, 82, "green", [("Worker Pool (Scaled)", "name"), ("Pull task · Heartbeat 10 s", "sub")], icon="play_arrow", kind="card", icon_size=24)
    w2 = f.node(MARGIN + 308, 440, 240, 82, "amber", [("Lease Reaper Daemon", "name"), ("Reclaims expired runs", "sub")], icon="timer", kind="card", icon_size=24)
    w3 = f.node(MARGIN + 598, 440, 240, 82, "red", [("Dead-Letter Queue", "name"), ("Max retries -> SRE triage", "sub")], icon="warning", kind="mid", icon_size=24)

    # Symmetrically aligned orthogonal wires + centered step badges (>= 50px segments)
    p1_s, p1_e = cli.right(0), api.left(0)
    f.wire([p1_s, p1_e], tone="blue", width=2.0)
    badge_on_seg(f, p1_s, p1_e, "1", "blue")

    p2_s, p2_e = api.right(0), db.left(0)
    f.wire([p2_s, p2_e], tone="purple", width=1.8)
    badge_on_seg(f, p2_s, p2_e, "2", "purple", ring="c-purple")

    f.wire([db.bottom(0), (db.cx, 168), (d_boxes[0].cx, 168), (d_boxes[0].cx, disp_z.y)], tone="amber", width=1.9, tail=True)
    badge_on_seg(f, (db.cx, 168), (d_boxes[0].cx, 168), "3", "amber", head=False, tail=False)
    f.label(618, 164, "Claim due window (60 s)", tone="amber", cls="small")

    f.wire([d_boxes[2].bottom(0), (d_boxes[2].cx, 358), (w1.cx, 358), (w1.cx, wrk_z.y)], tone="blue", width=2.0)
    badge_on_seg(f, (d_boxes[2].cx, 358), (w1.cx, 358), "4", "blue", head=False, tail=False)
    f.label(600, 354, "Dispatch leased task", tone="blue", cls="small")

    f.wire([w1.right(0), w2.left(0)], tone="amber", dash=True, width=1.6)
    p5_s, p5_e = w2.right(0), w3.left(0)
    f.wire([p5_s, p5_e], tone="red", dash=True, width=1.7)
    badge_on_seg(f, p5_s, p5_e, "5", "red", ring="c-green")

    path_legend(
        f, 550,
        "Solid: Sync schedule & dispatch (1 Submit -> 2 Persist -> 3 Poll -> 4 Run)",
        "Dashed: Async lease expiry & DLQ recovery (5)",
    )

    return f.save([
        ("Staging upcoming runs into sharded in-memory time wheels (3-4) avoids hammering the primary database on every 1-second tick.", "noteb"),
        "If a dispatcher or worker crashes, another shard or the lease reaper (5) reclaims expired rows without losing scheduled runs.",
    ])


def ch12_lease_execution():
    f = Fig(
        "ch12_lease_execution",
        "Figure 12-3. Lease-Based Job Claiming, Heartbeat Extension, and Dead-Letter Recovery.",
        482,
    )
    # Top Zone: State Machine (48px horizontal gaps, 50px vertical gap, centered badges 1-7)
    f.zone(
        MARGIN, 0, INNER, 260, "blue",
        "Job Attempt Lifecycle (Bounded Leases and Monotonic Attempt Fencing)",
        "Every transition increments attempt_id so late responses from zombie workers are rejected",
        icon="loop",
    )
    # Row 1: Happy path (4 states)
    r1_w = 170
    r1_gap = 48
    r1_y = 60
    r1_states = [
        ("PENDING", "run_at reached", "gray"),
        ("LEASED", "TTL = 30 s claim", "blue"),
        ("RUNNING", "Heartbeat 10 s", "teal"),
        ("SUCCEEDED", "Trigger DAG child", "green"),
    ]
    r1_boxes = []
    for i, (hdr, sub, tone) in enumerate(r1_states):
        rx = MARGIN + 16 + i * (r1_w + r1_gap)
        rb = f.node(rx, r1_y, r1_w, 62, tone, [(hdr, "monob"), (sub, "small")], layout="center", kind="card", r=10)
        r1_boxes.append(rb)
    for i in range(3):
        tone = "blue" if i < 2 else "green"
        p_s, p_e = r1_boxes[i].right(0), r1_boxes[i + 1].left(0)
        f.wire([p_s, p_e], tone=tone, width=1.8)
        badge_on_seg(f, p_s, p_e, str(i + 1), tone, ring="c-blue")

    # Row 2: Failure & recovery path (3 states, 50px below Row 1)
    r2_y = 172
    exp = f.node(r1_boxes[2].x, r2_y, r1_w, 62, "amber", [("LEASE EXPIRED", "monob"), ("Crash or hang", "small")], layout="center", kind="mid", r=10)
    ret = f.node(r1_boxes[1].x, r2_y, r1_w, 62, "purple", [("BACKOFF RETRY", "monob"), ("attempt < max", "small")], layout="center", kind="card", r=10)
    dlq = f.node(r1_boxes[3].x, r2_y, r1_w, 62, "red", [("DEAD LETTER", "monob"), ("attempt == max", "small")], layout="center", kind="mid", r=10)

    p4_s, p4_e = r1_boxes[2].bottom(0), exp.top(0)
    f.wire([p4_s, p4_e], tone="amber", width=1.8)
    badge_on_seg(f, p4_s, p4_e, "4", "amber", ring="c-blue")

    p5_s, p5_e = exp.left(0), ret.right(0)
    f.wire([p5_s, p5_e], tone="purple", width=1.8)
    badge_on_seg(f, p5_s, p5_e, "5", "purple", ring="c-blue")

    p6_s, p6_e = exp.right(0), dlq.left(0)
    f.wire([p6_s, p6_e], tone="red", width=1.8)
    badge_on_seg(f, p6_s, p6_e, "6", "red", ring="c-blue")

    f.wire([ret.left(0), (r1_boxes[0].cx, ret.cy), r1_boxes[0].bottom(0)], tone="purple", dash=True, width=1.8)
    badge_on_seg(f, (r1_boxes[0].cx, ret.cy), r1_boxes[0].bottom(0), "7", "purple", ring="c-blue")
    f.label(r1_boxes[0].cx + 76, 154, "Requeue (attempt+1)", tone="purple", cls="small", back_cls="c-blue")

    # Bottom Zone: Invariants
    f.zone(
        MARGIN, 280, INNER, 192, "teal",
        "Failure-Recovery and Idempotency Invariants",
        "Protecting downstream systems when a partitioned worker resumes after lease reclamation",
        icon="shield",
    )
    invs = [
        ("1. Lease Heartbeat", "TTL = 30 s · renew 10 s", "Reaper reclaims after 3 misses", "blue"),
        ("2. Fencing Attempt ID", "Key: (job_id, attempt)", "Stale worker commit -> 409", "teal"),
        ("3. Decorrelated Jitter", "wait = base * 2^k + rand", "Eliminates retry thundering herd", "amber"),
    ]
    iw = 262
    igap = 18
    for i, (hdr, mono_l, sub, tone) in enumerate(invs):
        ix = MARGIN + 17 + i * (iw + igap)
        f.node(ix, 338, iw, 116, tone, [(hdr, "name"), (mono_l, "monob"), (sub, "small")], layout="center", kind="card", r=10)

    return f.save([
        ("Bounded leases (1-4) guarantee liveness when workers crash abruptly, while monotonic attempt identifiers fence late commits from stalled workers.", "noteb"),
        "Expired runs either backoff and requeue with attempt+1 (5, 7) or move deterministically to the dead-letter queue (6) once max retries are exhausted.",
    ])


# =============================================================================
# CHAPTER 13: MULTI-CHANNEL NOTIFICATION SERVICE
# =============================================================================

def ch13_use_cases():
    return build_use_case_fig(
        "ch13_use_cases",
        "Figure 13-1. Actors and Use Cases of the Multi-Channel Notification Service.",
        "System Boundary: Multi-Channel Notification Service",
        "Unified ingestion · User preferences · Push, SMS, Email & Webhook",
        actors=[
            ("Product Service", "Auth, orders & marketing", "blue", "laptop"),
            ("End User Device", "iOS, Android, SMS & Email", "teal", "person"),
            ("External Providers", "APNs, FCM, Twilio & SES", "purple", "lan"),
        ],
        cases=[
            ("Submit Notification Request", "POST /v1/notifications (priority, dedup_id)", "blue", "notifications_active"),
            ("Render Localized Templates", "Versioned templates + i18n vars", "teal", "edit_note"),
            ("Manage Preferences & DND", "Opt-out, quiet hours & daily caps", "amber", "tune"),
            ("Dispatch Multi-Channel Send", "APNs, FCM, SMS & Email failover", "purple", "swap_horiz"),
            ("Ingest Receipts & Bounces", "Delivery callbacks + suppression", "green", "description"),
        ],
        links=[
            (0, [0, 1], "blue"),
            (1, [2], "teal"),
            (2, [3, 4], "purple"),
        ],
        notes=[
            ("Product teams invoke one channel-agnostic API with an idempotency key and priority tier; user preferences and compliance filters apply centrally.", "noteb"),
            "External delivery gateways operate asynchronously and return receipts or hard-bounce callbacks that feed the suppression store.",
        ],
    )


def ch13_architecture():
    f = Fig(
        "ch13_architecture",
        "Figure 13-2. Ingestion API, Template/Preference Store, Priority Queues, and Provider Gateways.",
        590,
    )
    # Top-left: Upstream Services
    up = f.node(
        MARGIN, 10, 276, 82, "blue",
        [("Product APIs / Triggers", "name"), ("Auth OTP · Orders · Campaigns", "sub")],
        icon="laptop", kind="card", icon_size=26,
    )

    # Top-right: Control Plane
    cp_x = 360
    cp_w = WIDTH - MARGIN - cp_x  # 528
    f.zone(
        cp_x, 0, cp_w, 144, "purple",
        "Control Plane (Templates, Preferences & Routing Policy)",
        "Cached in Redis · Enforces opt-outs, quiet hours, rate caps, and provider weights",
        icon="settings_suggest", dashed=True,
    )
    pref = f.node(
        cp_x + 16, 56, 240, 74, "purple",
        [("Preference & Cap Store", "name"), ("Opt-out · DND · Freq cap", "sub")],
        icon="tune", kind="card", icon_size=24,
    )
    tmpl = f.node(
        cp_x + 272, 56, 240, 74, "purple",
        [("Template & Routing DB", "name"), ("i18n · Provider SLA rank", "sub")],
        icon="edit_note", kind="card", icon_size=24,
    )

    # Middle-left: Ingestion API (50px below up)
    ing_z = f.zone(
        MARGIN, 142, 276, 186, "teal",
        "Data Plane: Ingestion Tier",
        "Dedup, validate & enrich",
        icon="shield",
    )
    ing = f.node(
        MARGIN + 16, 198, 244, 114, "teal",
        [("Notification API", "name"), ("SETNX dedup_id (24h)", "mono"), ("Evaluate prefs & DND", "sub")],
        icon="bolt", layout="center", kind="card", icon_size=26,
    )

    # Middle-right: Priority Queues (52px right of ing_z)
    q_z = f.zone(
        cp_x, 184, cp_w, 144, "amber",
        "Data Plane: Priority-Isolated Queues (Separate Kafka Topics)",
        "Dedicated broker topics prevent million-user campaigns from delaying OTP alerts",
        icon="view_week",
    )
    qw = 156
    qgap = 14
    for i, (hdr, sub, tone, kind) in enumerate([
        ("P0 Critical", "OTP · < 2 s SLO", "red", "mid"),
        ("P1 Transactional", "Orders · < 15 s", "amber", "card"),
        ("P2 Bulk Promo", "Throttled · Async", "gray", "card"),
    ]):
        qx = cp_x + 16 + i * (qw + qgap)
        f.node(qx, 240, qw, 72, tone, [(hdr, "name"), (sub, "small")], layout="center", kind=kind, r=10)

    # Bottom: Channel Workers & Gateways (50px below q_z & ing_z)
    gw_z = f.zone(
        MARGIN, 378, INNER, 164, "blue",
        "Data Plane: Channel Workers, Provider Gateways & Receipt Pipeline",
        "Per-channel worker pools isolate third-party latency and deliver to Mobile, SMS & Email devices",
        icon="lan",
    )
    gw_w = 196
    gw_gap = 13
    gws = [
        ("Push Workers", "APNs & FCM -> Mobile", "Token refresh", "blue"),
        ("SMS Workers", "Twilio -> Vonage", "Circuit breaker", "teal"),
        ("Email Workers", "SES -> SendGrid", "DKIM & SPF", "purple"),
        ("Receipt Pipeline", "Delivered & bounces", "Auto-suppress", "green"),
    ]
    gw_boxes = []
    for i, (hdr, l1, l2, tone) in enumerate(gws):
        gx = MARGIN + 16 + i * (gw_w + gw_gap)
        gb = f.node(gx, 434, gw_w, 96, tone, [(hdr, "name"), (l1, "mono"), (l2, "small")], layout="center", kind="card", r=10)
        gw_boxes.append(gb)

    # Symmetrically aligned orthogonal wires + centered step badges (>= 50px segments)
    p1_s, p1_e = up.bottom(0), (up.cx, ing_z.y)
    f.wire([p1_s, p1_e], tone="blue", width=2.0)
    badge_on_seg(f, p1_s, p1_e, "1", "blue")
    f.label(up.cx + 78, 117, "POST /v1/notifications", tone="blue", cls="small")

    f.wire([pref.bottom(0), (pref.cx, 164)], tone="purple", dash=True, head=False, width=1.6)
    f.wire([tmpl.bottom(-36), (tmpl.cx - 36, 164)], tone="purple", dash=True, head=False, width=1.6)
    f.wire([(tmpl.cx - 36, 164), (334, 164), (334, ing.cy - 24), ing.right(-24)], tone="purple", dash=True, width=1.6)
    badge_on_seg(f, (pref.cx, 164), (334, 164), "4", "purple", head=False, tail=False)

    p2_s, p2_e = (ing_z.r, ing.cy + 24), (cp_x, ing.cy + 24)
    f.wire([p2_s, p2_e], tone="amber", width=2.0)
    badge_on_seg(f, p2_s, p2_e, "2", "amber")
    f.label((p2_s[0] + p2_e[0]) / 2, ing.cy + 6, "Route", tone="amber", cls="small")

    q_cxs = [cp_x + 16 + i * (qw + qgap) + qw / 2 for i in range(3)]
    for qx in q_cxs:
        f.wire([(qx, q_z.b), (qx, gw_z.y)], tone="blue", width=1.8)
    badge_on_seg(f, (q_cxs[0], q_z.b), (q_cxs[0], gw_z.y), "3", "blue")
    f.label((q_cxs[1] + q_cxs[2]) / 2, 357, "Per-lane workers", tone="blue", cls="small")

    # Step 5: Receipt Pipeline -> Control Plane cleanly via outer right gutter (x=904) to symmetric tmpl.bottom(+36)
    f.wire([gw_boxes[3].right(0), (904, gw_boxes[3].cy), (904, 164), (tmpl.cx + 36, 164), tmpl.bottom(36)], tone="green", dash=True, width=1.6)
    badge_on_seg(f, (904, gw_boxes[3].cy), (904, 164), "5", "green", head=False, tail=False)

    path_legend(
        f, 554,
        "Solid: Sync ingest & dispatch (1 Notify -> 2 Queue -> 3 Deliver)",
        "Dashed: Pref/template lookup (4) & async bounce suppression (5)",
    )

    return f.save([
        ("Decoupling ingestion from channel delivery via priority-isolated queues (1-3) absorbs traffic spikes and shields upstream APIs from provider outages.", "noteb"),
        "Cached preference/template lookups (4) enforce compliance on ingest, while delivery receipts and hard-bounce webhooks (5) update suppression state asynchronously.",
    ])


def ch13_priority_fanout():
    f = Fig(
        "ch13_priority_fanout",
        "Figure 13-3. Priority Lane Isolation, Per-Provider Circuit Breakers, and Deduplication.",
        472,
    )
    cw1, cw2, cw3 = 248, 248, 248
    gap = 56
    x1 = MARGIN
    x2 = x1 + cw1 + gap  # 336
    x3 = x2 + cw2 + gap  # 640

    # Column 1: Deduplication & Compliance (sequential gates with 48px vertical gaps)
    z1 = f.zone(x1, 0, cw1, 460, "blue", "1. Dedup & Policy Gate", "Exactly-once intent", icon="shield")
    d1 = f.node(x1 + 14, 62, cw1 - 28, 94, "blue", [
        ("Idempotency Store", "name"),
        ("SETNX dedup:{id}", "mono"),
        ("24 h TTL suppresses retry", "small"),
    ], icon="lock", layout="center", kind="card", icon_size=24)
    d2 = f.node(x1 + 14, 204, cw1 - 28, 94, "amber", [
        ("Suppression Filter", "name"),
        ("Drop opt-out & bounces", "sub"),
        ("Quiet hours -> defer P2", "small"),
    ], icon="block", layout="center", kind="card", icon_size=24)
    d3 = f.node(x1 + 14, 346, cw1 - 28, 94, "teal", [
        ("User Frequency Cap", "name"),
        ("<= 3 promos / user / day", "mono"),
        ("P0 OTP always bypasses", "small"),
    ], icon="timer", layout="center", kind="card", icon_size=24)

    # Column 2: Priority Lane Isolation
    z2 = f.zone(x2, 0, cw2, 460, "amber", "2. Priority Lanes", "Zero head-of-line lag", icon="view_week")
    p0 = f.node(x2 + 14, 62, cw2 - 28, 94, "red", [
        ("P0 Critical (OTP)", "name"),
        ("Reserved hot workers", "sub"),
        ("p99 delivery < 2 s", "monob"),
    ], layout="center", kind="mid", r=10)
    p1 = f.node(x2 + 14, 204, cw2 - 28, 94, "amber", [
        ("P1 Transactional", "name"),
        ("Autoscaled consumer pool", "sub"),
        ("p99 delivery < 15 s", "monob"),
    ], layout="center", kind="card", r=10)
    p2 = f.node(x2 + 14, 346, cw2 - 28, 94, "gray", [
        ("P2 Bulk / Promo", "name"),
        ("Token-bucket rate limit", "sub"),
        ("Shed first under load", "small"),
    ], layout="center", kind="card", r=10)

    # Column 3: Per-Provider Circuit Breakers
    z3 = f.zone(x3, 0, cw3, 460, "teal", "3. Circuit Breakers", "Multi-provider failover", icon="call_split")
    cb1 = f.node(x3 + 14, 62, cw3 - 28, 94, "teal", [
        ("Primary Gateway", "name"),
        ("Err > 5% -> OPEN state", "mono"),
        ("Isolates slow provider", "small"),
    ], layout="center", kind="card", r=10)
    cb2 = f.node(x3 + 14, 204, cw3 - 28, 94, "green", [
        ("Secondary Failover", "name"),
        ("Reroutes P0 & P1 traffic", "sub"),
        ("Zero user-visible drop", "small"),
    ], layout="center", kind="card", r=10)
    cb3 = f.node(x3 + 14, 346, cw3 - 28, 94, "purple", [
        ("Half-Open Probe & DLQ", "name"),
        ("Canary 1% -> CLOSE", "mono"),
        ("Park exhausted -> DLQ", "small"),
    ], layout="center", kind="card", r=10)

    # Sequential policy gate arrows inside Column 1 (48px vertical gaps)
    s1_a, s1_b = d1.bottom(0), d2.top(0)
    f.wire([s1_a, s1_b], tone="blue", width=1.8)
    badge_on_seg(f, s1_a, s1_b, "1", "blue", ring="c-blue")

    s2_a, s2_b = d2.bottom(0), d3.top(0)
    f.wire([s2_a, s2_b], tone="amber", width=1.8)
    badge_on_seg(f, s2_a, s2_b, "2", "amber", ring="c-blue")

    # Symmetric 1-to-3 fan-out from Column 1 to Column 2 at exact midpoint x_mid = (z1.r + z2.x) / 2
    x_mid = (z1.r + z2.x) / 2.0  # 308.0
    f.wire([(z1.r, p1.cy), (x_mid, p1.cy)], tone="amber", head=False, width=1.9)
    f.wire([(x_mid, p0.cy), (x_mid, p2.cy)], tone="amber", head=False, width=1.9)
    f.wire([(x_mid, p0.cy), p0.left(0)], tone="red", width=1.9)
    f.wire([(x_mid, p1.cy), p1.left(0)], tone="amber", width=1.9)
    f.wire([(x_mid, p2.cy), p2.left(0)], tone="gray", width=1.8)
    badge_on_seg(f, (x_mid, p0.cy), (x_mid, p1.cy), "3", "amber", head=False, tail=False)

    # Clean horizontal column 2 -> column 3 connectors (84px each, badges centered in white gutter)
    s4_a, s4_b = p0.right(0), cb1.left(0)
    f.wire([s4_a, s4_b], tone="teal", width=1.9)
    badge_on_seg(f, s4_a, s4_b, "4", "teal")

    s5_a, s5_b = p1.right(0), cb2.left(0)
    f.wire([s5_a, s5_b], tone="green", width=1.8)
    badge_on_seg(f, s5_a, s5_b, "5", "green")

    s6_a, s6_b = p2.right(0), cb3.left(0)
    f.wire([s6_a, s6_b], tone="purple", dash=True, width=1.7)
    badge_on_seg(f, s6_a, s6_b, "6", "purple")

    # Vertical state transitions inside Column 3 (48px each)
    s7_a, s7_b = cb1.bottom(0), cb2.top(0)
    f.wire([s7_a, s7_b], tone="red", dash=True, width=1.7)
    badge_on_seg(f, s7_a, s7_b, "7", "red", ring="c-teal")

    s8_a, s8_b = cb2.bottom(0), cb3.top(0)
    f.wire([s8_a, s8_b], tone="purple", dash=True, width=1.7)
    badge_on_seg(f, s8_a, s8_b, "8", "purple", ring="c-teal")

    return f.save([
        ("Events pass sequentially through dedup and policy gates (1-2) before fanning out symmetrically across isolated priority lanes (3).", "noteb"),
        "Each lane routes into per-provider circuit breakers (4-6) that fail over on error spikes (7) and automate half-open recovery or DLQ parking (8).",
    ])


ALL = [
    ch08_use_cases,
    ch08_architecture,
    ch08_clock_drift,
    ch09_use_cases,
    ch09_architecture,
    ch09_stampede_defense,
    ch10_use_cases,
    ch10_architecture,
    ch10_fencing_tokens,
    ch11_use_cases,
    ch11_architecture,
    ch11_partition_rebalance,
    ch12_use_cases,
    ch12_architecture,
    ch12_lease_execution,
    ch13_use_cases,
    ch13_architecture,
    ch13_priority_fanout,
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
