#!/usr/bin/env python3
"""Generate 18 spacious Material Design 3 light+dark SVG figures for Part II (Chapters 8-13).

Every figure uses WIDTH = 920, MARGIN = 32, INNER = 856, separates control and
data planes clearly, and enforces zero text overflow or overlap in Chrome.
"""
from figkit_m3 import Fig, WIDTH, MARGIN, build_use_case_fig

INNER = WIDTH - 2 * MARGIN  # 856px usable width


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
            ("Generate Single 64-Bit ID", "GET /v1/ids/next -> uint64", "blue", "bolt"),
            ("Allocate Batched ID Block", "POST /v1/ids/batch?count=N", "teal", "view_module"),
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
        536,
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

    # Middle-left: Edge Load Balancer
    lb_zone = f.zone(
        MARGIN, 130, 286, 146, "teal",
        "Data Plane: Local-AZ Proxy",
        "Zone-aware L7 routing · < 0.5 ms",
        icon="swap_horiz",
    )
    lb_node = f.node(
        MARGIN + 16, 188, 254, 72, "teal",
        [("Stateless Edge Router", "name"), ("Local-AZ affinity · Zero state", "sub")],
        icon="call_split", kind="card", icon_size=26,
    )

    # Bottom: Shared-Nothing Generator Fleet
    fleet = f.zone(
        MARGIN, 314, INNER, 214, "blue",
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
        f.rect(x, 370, cw, 142, "card", r=12, lift=True)
        f.text(x + 14, 392, hdr, "name", "start", tone=tone, fit=(x + 10, x + cw - 10))
        f.node(x + 12, 404, cw - 24, 46, tone, [(top_line, "monob")], kind="mid", r=8)
        f.node(x + 12, 458, cw - 24, 42, "gray", [(bot_line, "small")], kind="tonal", r=8)

    # Orthogonal wires with generous spacing
    f.wire([cli.bottom(0), (cli.cx, lb_zone.y)], tone="blue", width=2.0)
    f.label(cli.cx + 74, 114, "GET /v1/ids/next", tone="blue", cls="small")

    f.wire([lb_node.bottom(0), (lb_node.cx, fleet.y)], tone="teal", width=2.0)
    f.label(lb_node.cx + 88, 298, "Local-AZ gRPC call", tone="teal", cls="small")

    f.wire([lease_q.bottom(0), (lease_q.cx, fleet.y)], tone="purple", dash=True, width=1.6, tail=True)
    f.label(lease_q.cx, 236, "Lease & 10 s keepalive", tone="purple", cls="small")

    f.wire([clk_guard.bottom(0), (clk_guard.cx, fleet.y)], tone="purple", dash=True, width=1.6, tail=True)
    f.label(clk_guard.cx, 236, "Boot max_ts verify", tone="purple", cls="small")

    return f.save([
        ("Generators contact the control plane only on boot and periodic lease renewal; every ID request resolves strictly in local RAM.", "noteb"),
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

    # Bottom Zone: Clock Regression Defense
    f.zone(
        MARGIN, 166, INNER, 298, "amber",
        "Clock-Regression Defense Pipeline (Triggered When t_now < last_ts)",
        "Wall-clock adjustments from NTP step sync, leap seconds, or VM migration must never emit duplicate IDs",
        icon="shield",
    )
    trig = f.node(
        MARGIN + 18, 286, 224, 118, "red",
        [
            ("Clock Regressed", "name"),
            ("delta = last_ts - t_now", "mono"),
            ("Anchor: CLOCK_MONOTONIC", "small"),
        ],
        icon="warning", layout="center", kind="mid", icon_size=26,
    )

    tiers = [
        ("Tier 1: Small Drift (delta <= 5 ms)", "Spin-wait until t_now >= last_ts; zero caller errors", "green", "timer"),
        ("Tier 2: Moderate (5 ms < delta <= 500 ms)", "Advance logical last_ts or consume sequence reserve", "amber", "tune"),
        ("Tier 3: Severe Drift (delta > 500 ms)", "Fail closed (HTTP 503), release worker lease, page SRE", "red", "block"),
    ]
    tx = 324
    tw = WIDTH - MARGIN - tx - 18  # 546
    t_boxes = []
    for i, (hdr, sub, tone, ic) in enumerate(tiers):
        ty = 224 + i * 78
        tb = f.node(tx, ty, tw, 64, tone, [(hdr, "name"), (sub, "sub")], icon=ic, kind="card" if tone != "red" else "mid", icon_size=24)
        t_boxes.append(tb)

    bus_x = 294
    f.wire([trig.right(-22), (bus_x, trig.cy - 22), (bus_x, t_boxes[0].cy), t_boxes[0].left(0)], tone="green", width=1.9)
    f.wire([trig.right(0), t_boxes[1].left(0)], tone="amber", width=1.9)
    f.wire([trig.right(22), (bus_x, trig.cy + 22), (bus_x, t_boxes[2].cy), t_boxes[2].left(0)], tone="red", width=1.9)

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
        548,
    )
    # Top-left: Clients
    cli = f.node(
        MARGIN, 10, 286, 82, "blue",
        [("Application Clients", "name"), ("Cache-aside · Binary protocol", "sub")],
        icon="laptop", kind="card", icon_size=26,
    )

    # Top-right: Control Plane
    cp_x = 356
    cp_w = WIDTH - MARGIN - cp_x  # 532
    f.zone(
        cp_x, 0, cp_w, 158, "purple",
        "Control Plane (Ring & Health Coordinator)",
        "Config quorum + active health checks · Publishes consistent hash ring epoch",
        icon="settings_suggest", dashed=True,
    )
    ring_mgr = f.node(
        cp_x + 18, 58, 238, 82, "purple",
        [("Ring Membership Map", "name"), ("256 vnodes · Epoch v18", "sub")],
        icon="dns", kind="card", icon_size=26,
    )
    hotkey_mgr = f.node(
        cp_x + 274, 58, 240, 82, "purple",
        [("Hot-Key & Auto-Scaler", "name"), ("Detect skew · Replicate hot", "sub")],
        icon="tune", kind="card", icon_size=26,
    )

    # Middle-left: Proxy Tier
    proxy_z = f.zone(
        MARGIN, 126, 286, 146, "teal",
        "Data Plane: Cache Proxy Tier",
        "L1 local cache + request coalescing",
        icon="swap_horiz",
    )
    proxy_n = f.node(
        MARGIN + 16, 184, 254, 72, "teal",
        [("Smart Client / Mcrouter", "name"), ("Consistent hash · Singleflight", "sub")],
        icon="call_split", kind="card", icon_size=26,
    )

    # Bottom-left: Sharded Cache Cluster
    cache_w = 556
    cache_z = f.zone(
        MARGIN, 314, cache_w, 224, "blue",
        "Data Plane: Sharded In-Memory Cache Tier (Multi-AZ)",
        "Slab allocator · W-TinyLFU eviction · Active-standby shard replicas",
        icon="memory",
    )
    sw = 166
    sgap = 12
    for i, (stitle, srng, ssub, tone) in enumerate([
        ("Shard A (AZ-A)", "Ring 0..33%", "Primary + Standby", "blue"),
        ("Shard B (AZ-B)", "Ring 33..66%", "Primary + Standby", "teal"),
        ("Shard C (AZ-C)", "Ring 66..100%", "Primary + Standby", "green"),
    ]):
        sx = MARGIN + 16 + i * (sw + sgap)
        f.rect(sx, 372, sw, 150, "card", r=12, lift=True)
        f.text(sx + sw / 2, 396, stitle, "name", "middle", tone=tone, fit=(sx + 6, sx + sw - 6))
        f.node(sx + 10, 410, sw - 20, 46, tone, [(srng, "monob")], kind="mid", r=8)
        f.node(sx + 10, 464, sw - 20, 44, "gray", [(ssub, "small")], kind="tonal", r=8)

    # Bottom-right: Origin Database & CDC
    orig_x = MARGIN + cache_w + 24  # 612
    orig_w = WIDTH - MARGIN - orig_x  # 276
    orig_z = f.zone(
        orig_x, 314, orig_w, 224, "amber",
        "Origin & CDC Tier",
        "Cold miss & invalidation",
        icon="save",
    )
    oltp = f.node(
        orig_x + 14, 374, orig_w - 28, 66, "amber",
        [("Authoritative OLTP DB", "name"), ("Serves coalesced misses", "sub")],
        icon="table_rows", kind="card", icon_size=24,
    )
    cdc = f.node(
        orig_x + 14, 456, orig_w - 28, 66, "green",
        [("CDC Invalidation", "name"), ("Binlog -> async DEL key", "sub")],
        icon="loop", kind="card", icon_size=24,
    )

    # Orthogonal wires
    f.wire([cli.bottom(0), (cli.cx, proxy_z.y)], tone="blue", width=2.0)
    f.label(cli.cx + 68, 112, "GET / SET / DEL", tone="blue", cls="small")

    f.wire([ring_mgr.bottom(-24), (ring_mgr.cx - 24, 220), proxy_n.right(0)], tone="purple", dash=True, width=1.6)
    f.label(440, 204, "Ring map watch", tone="purple", cls="small")

    f.wire([hotkey_mgr.bottom(0), (hotkey_mgr.cx, 256), (480, 256), (480, cache_z.y)], tone="purple", dash=True, width=1.6, tail=True)
    f.label(664, 240, "Hot-key stats & rebalance", tone="purple", cls="small")

    f.wire([proxy_n.bottom(-30), (proxy_n.cx - 30, cache_z.y)], tone="teal", width=2.0)
    f.label(proxy_n.cx - 30, 296, "Shard hit (< 1 ms)", tone="teal", cls="small")

    f.wire([proxy_n.bottom(55), (proxy_n.cx + 55, 292), (orig_z.cx, 292), (orig_z.cx, orig_z.y)], tone="amber", dash=True, width=1.8)
    f.label(orig_z.cx, 278, "Coalesced miss read", tone="amber", cls="small")

    f.wire([cdc.left(0), (cache_z.r, cdc.cy)], tone="green", dash=True, width=1.8)

    return f.save([
        ("Cache hits resolve in one network hop between the smart proxy and the target RAM shard, shielding the origin database from 99%+ of read load.", "noteb"),
        "Asynchronous CDC invalidation complements write-path deletes so stale entries converge quickly even if an application host crashes mid-request.",
    ])


def ch09_stampede_defense():
    f = Fig(
        "ch09_stampede_defense",
        "Figure 9-3. Singleflight Request Coalescing and Probabilistic Early Expiration.",
        466,
    )
    # Top Zone: Singleflight
    f.zone(
        MARGIN, 0, INNER, 220, "blue",
        "1. Singleflight Request Coalescing (Cold-Miss Thundering Herd Collapse)",
        "1,000 simultaneous cache misses for a hot key collapse into exactly one origin database query",
        icon="handshake",
    )
    herd = f.node(
        MARGIN + 18, 72, 186, 126, "red",
        [("1,000 Misses", "name"), ("Key: catalog:top", "mono"), ("Expired at t = 0", "small")],
        icon="warning", layout="center", kind="mid", icon_size=26,
    )
    gate = f.node(
        MARGIN + 236, 72, 224, 126, "blue",
        [("Singleflight Gate", "name"), ("Req 1 acquires mutex", "sub"), ("Req 2..1000 await", "mono")],
        icon="lock", layout="center", kind="card", icon_size=26,
    )
    origin = f.node(
        MARGIN + 494, 62, 344, 66, "amber",
        [("Single Origin DB Fetch", "name"), ("1 query (~12 ms) instead of 1,000", "sub")],
        icon="save", kind="card", icon_size=24,
    )
    bcast = f.node(
        MARGIN + 494, 142, 344, 66, "green",
        [("Populate Cache & Broadcast", "name"), ("SET key + wake 999 waiting callers", "sub")],
        icon="play_arrow", kind="card", icon_size=24,
    )
    f.wire([herd.right(0), gate.left(0)], tone="red", width=1.9)
    f.wire([gate.right(-20), (gate.r + 16, gate.cy - 20), (gate.r + 16, origin.cy), origin.left(0)], tone="amber", width=1.9)
    f.wire([origin.bottom(0), bcast.top(0)], tone="green", width=1.9)
    f.wire([bcast.left(0), (gate.r + 16, bcast.cy), (gate.r + 16, gate.cy + 20), gate.right(20)], tone="green", dash=True, width=1.7)

    # Bottom Zone: XFetch
    f.zone(
        MARGIN, 240, INNER, 216, "teal",
        "2. Probabilistic Early Expiration (XFetch Algorithm)",
        "One reader triggers an asynchronous recompute before hard TTL expiry using compute cost delta",
        icon="timer",
    )
    f.node(
        MARGIN + 18, 298, INNER - 36, 38, "teal",
        [("Refresh early if:   t_now - delta * beta * ln(rand(0, 1)) >= expiry", "monob")],
        layout="center", kind="card", r=8,
    )
    phases = [
        ("Phase A: 0..80% TTL", "Pure RAM Hit Path", "P(refresh) ~ 0 · zero origin I/O", "green"),
        ("Phase B: 80..99% TTL", "Probabilistic Window", "One reader triggers async reload", "teal"),
        ("Phase C: 100% TTL", "Seamless Cutover", "Fresh TTL installed before expiry", "blue"),
    ]
    pw = 262
    pgap = 18
    p_boxes = []
    for i, (hdr, sub, foot, tone) in enumerate(phases):
        px = MARGIN + 17 + i * (pw + pgap)
        pb = f.node(px, 352, pw, 88, tone, [(hdr, "name"), (sub, "monob"), (foot, "small")], layout="center", kind="card", r=10)
        p_boxes.append(pb)
    f.wire([p_boxes[0].right(0), p_boxes[1].left(0)], tone="teal", width=1.8)
    f.wire([p_boxes[1].right(0), p_boxes[2].left(0)], tone="blue", width=1.8)

    return f.save([
        ("Singleflight protects the database during cold starts and unexpected evictions; XFetch prevents hot keys from ever hitting a synchronous miss.", "noteb"),
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
            ("Renew Active Lease Heartbeat", "PUT /v1/leases/{id}/keepalive", "green", "timer"),
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
        544,
    )
    # Top-left: Client Tier
    cli_z = f.zone(
        MARGIN, 0, 316, 250, "blue",
        "Client Tier (Lock Contenders)",
        "Session keepalive & lock watch",
        icon="laptop",
    )
    c1 = f.node(
        MARGIN + 16, 62, 284, 78, "green",
        [("Client A (Lease Holder)", "name"), ("Lease #42 · Token = 34", "mono")],
        icon="lock", kind="card", icon_size=24,
    )
    c2 = f.node(
        MARGIN + 16, 156, 284, 78, "gray",
        [("Client B (Waiting)", "name"), ("Watches expiry · Backoff", "sub")],
        icon="hourglass_top", kind="card", icon_size=24,
    )

    # Top-right: Raft Consensus Lock Service
    cp_x = 386
    cp_w = WIDTH - MARGIN - cp_x  # 502
    raft_z = f.zone(
        cp_x, 0, cp_w, 250, "purple",
        "Consensus Plane (5-Node Raft Lock Service)",
        "Linearizable lease state machine across 3 AZs · Monotonic Raft index token",
        icon="settings_suggest", dashed=True,
    )
    leader = f.node(
        cp_x + 18, 62, 224, 78, "amber",
        [("Raft Leader (AZ-A)", "name"), ("Issues token = Raft idx", "sub")],
        icon="dns", kind="card", icon_size=24,
    )
    followers = f.node(
        cp_x + 260, 62, 224, 78, "purple",
        [("4 Raft Followers", "name"), ("Quorum commit (3 of 5)", "sub")],
        icon="layers", kind="card", icon_size=24,
    )
    wheel = f.node(
        cp_x + 18, 156, cp_w - 36, 78, "teal",
        [("Lease Expiry Wheel & Watch Stream", "name"), ("Revokes silent leases after TTL · Notifies queued contenders", "sub")],
        icon="schedule", kind="card", icon_size=24,
    )

    # Bottom: Fenced Storage Tier
    stor_z = f.zone(
        MARGIN, 306, INNER, 228, "teal",
        "Data Plane: Fenced Resource & Storage Tier (Enforces Mutual Exclusion)",
        "Every state-mutating request must carry a fencing token verified atomically against max_token",
        icon="shield",
    )
    guard = f.node(
        MARGIN + 18, 376, 258, 134, "teal",
        [("Fencing Guard", "name"), ("IF req.token < max:", "mono"), ("  return 409 STALE", "monob")],
        icon="rule", layout="center", kind="card", icon_size=26,
    )
    engine = f.node(
        MARGIN + 300, 376, 266, 134, "blue",
        [("Primary Storage Engine", "name"), ("Atomic write + update", "sub"), ("max_token = 34", "monob")],
        icon="save", layout="center", kind="card", icon_size=26,
    )
    audit = f.node(
        MARGIN + 590, 376, 248, 134, "amber",
        [("Stale-Write Audit Log", "name"), ("Records rejected tokens", "sub"), ("Alerts split-brain GC", "small")],
        icon="description", layout="center", kind="card", icon_size=26,
    )

    # Orthogonal wires
    f.wire([c1.right(0), leader.left(0)], tone="green", width=1.9, tail=True)
    f.label(358, 86, "Keepalive", tone="green", cls="small")

    f.wire([c2.right(0), wheel.left(0)], tone="purple", dash=True, width=1.7, tail=True)
    f.label(358, 180, "Watch", tone="purple", cls="small")

    f.wire([leader.right(0), followers.left(0)], tone="amber", width=1.8, tail=True)
    f.wire([leader.bottom(0), (leader.cx, wheel.y)], tone="teal", width=1.6)

    f.wire([c1.bottom(-60), (c1.cx - 60, 276), (guard.cx, 276), (guard.cx, stor_z.y)], tone="green", width=2.0)
    f.label(guard.cx + 106, 286, "Write(payload, token=34)", tone="green", cls="small")

    f.wire([guard.right(-18), engine.left(-18)], tone="blue", width=1.9)
    f.wire([guard.right(26), (guard.r + 12, guard.cy + 26), (guard.r + 12, 522), (audit.cx, 522), audit.bottom(0)], tone="red", dash=True, width=1.6)
    f.wire([engine.right(0), audit.left(0)], tone="amber", dash=True, width=1.6)

    return f.save([
        ("Using the Raft log commit index as the fencing token guarantees strict monotonicity across leader elections without extra consensus rounds.", "noteb"),
        "A lock service provides liveness and coordination, whereas the fenced storage guard enforces safety under arbitrary process pauses or network delays.",
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

    # Clean vertical handoff indicators
    f.wire([(291, y2 + 42), (291, y1 + 82)], tone="blue", width=1.6)
    f.wire([(577, y2 + 82), (577, y3 + 42)], tone="green", width=1.6)
    f.wire([(680, y3 + 82), (680, y4 + 42)], tone="teal", width=1.6)
    f.wire([(798, y1 + 82), (798, y4 + 42)], tone="red", dash=True, width=1.7)

    return f.save([
        ("Process pauses from garbage collection, page faults, or hypervisor stalls invalidate any client-side assumption that a lease is still active.", "noteb"),
        "Because Client 2 already persisted token 34 to the storage server, Client 1's delayed write carrying token 33 is deterministically rejected with HTTP 409.",
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
        548,
    )
    # Top-left: Producers
    prod = f.node(
        MARGIN, 10, 286, 82, "blue",
        [("Producer Fleet", "name"), ("Batching · hash(key) % P · acks=all", "sub")],
        icon="laptop", kind="card", icon_size=26,
    )

    # Top-right: Control Plane
    cp_x = 356
    cp_w = WIDTH - MARGIN - cp_x  # 532
    f.zone(
        cp_x, 0, cp_w, 134, "purple",
        "Control Plane (KRaft Metadata & Group Coordinator)",
        "3-node Raft metadata log · Tracks topic partitions, ISR sets, and consumer offsets",
        icon="settings_suggest", dashed=True,
    )
    ctrl = f.node(
        cp_x + 18, 56, 238, 64, "purple",
        [("Active Controller", "name"), ("Leader election & ISR", "sub")],
        icon="dns", kind="card", icon_size=24,
    )
    gcoord = f.node(
        cp_x + 274, 56, 240, 64, "purple",
        [("Group Coordinator", "name"), ("Rebalance & __offsets", "sub")],
        icon="handshake", kind="card", icon_size=24,
    )

    # Middle: Partitioned Brokers
    brk_z = f.zone(
        MARGIN, 166, INNER, 214, "blue",
        "Data Plane: Partitioned Broker Cluster (Append-Only Commit Logs Across 3 AZs)",
        "Sequential disk append · Page-cache zero-copy sendfile() · In-Sync Replica (ISR) quorum",
        icon="layers",
    )
    bw = 262
    bgap = 18
    bx_list = [MARGIN + 17 + i * (bw + bgap) for i in range(3)]
    brokers = [
        ("Broker 1 (AZ-A)", "P0 LEADER [0..94]", "P1 Follower (ISR)", "amber"),
        ("Broker 2 (AZ-B)", "P1 LEADER [0..88]", "P2 Follower (ISR)", "amber"),
        ("Broker 3 (AZ-C)", "P2 LEADER [0..91]", "P0 Follower (ISR)", "amber"),
    ]
    for i, (hdr, lead, fol, tone) in enumerate(brokers):
        bx = bx_list[i]
        f.rect(bx, 222, bw, 142, "card", r=12, lift=True)
        f.text(bx + 14, 244, hdr, "name", "start", tone="blue", fit=(bx + 10, bx + bw - 10))
        f.node(bx + 12, 256, bw - 24, 46, tone, [(lead, "monob")], kind="mid", r=8)
        f.node(bx + 12, 310, bw - 24, 42, "gray", [(fol, "mono")], kind="tonal", r=8)

    # Bottom: Consumer Group
    cons_z = f.zone(
        MARGIN, 418, INNER, 120, "teal",
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
        cb = f.node(bx_list[i], 472, bw, 52, "teal", [(cname, "name"), (csub, "mono")], kind="card")
        c_boxes.append(cb)

    # Orthogonal wires
    f.wire([prod.bottom(0), (prod.cx, brk_z.y)], tone="blue", width=2.0)
    f.label(prod.cx + 80, 128, "Batch append (acks=all)", tone="blue", cls="small")

    f.wire([ctrl.bottom(0), (ctrl.cx, brk_z.y)], tone="purple", dash=True, width=1.6, tail=True)
    f.label(ctrl.cx, 150, "Metadata & ISR sync", tone="purple", cls="small")

    f.wire([gcoord.bottom(0), (gcoord.cx, brk_z.y)], tone="purple", dash=True, width=1.6, tail=True)
    f.label(gcoord.cx, 150, "Offset commit log", tone="purple", cls="small")

    for i in range(3):
        cx = bx_list[i] + bw / 2
        f.wire([(cx, brk_z.b), (cx, cons_z.y)], tone="teal", width=1.9)
    f.label(bx_list[1] + bw / 2 + 78, 399, "Zero-copy FETCH", tone="teal", cls="small")

    return f.save([
        ("Keyed routing places all events for the same entity onto one partition, guaranteeing strict per-key ordering without global serialization.", "noteb"),
        "Producers writing with acks=all wait until every In-Sync Replica (ISR) appends the batch, ensuring zero acknowledged message loss on single-broker failure.",
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
    sw = 258
    sgap = 24
    s_boxes = []
    for i, (hdr, l1, l2, l3, tone) in enumerate(stages):
        sx = MARGIN + 17 + i * (sw + sgap)
        sb = f.node(sx, 62, sw, 152, tone, [
            (hdr, "name"),
            (l1, "mono"),
            (l2, "mono"),
            (l3, "small"),
        ], layout="center", kind="card", r=12)
        s_boxes.append(sb)
    f.wire([s_boxes[0].right(0), s_boxes[1].left(0)], tone="amber", width=1.9)
    f.wire([s_boxes[1].right(0), s_boxes[2].left(0)], tone="green", width=1.9)

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
        548,
    )
    # Top-left: Clients
    cli = f.node(
        MARGIN, 10, 286, 82, "blue",
        [("Job Clients & Pipelines", "name"), ("POST /v1/jobs · Cron & DAG", "sub")],
        icon="laptop", kind="card", icon_size=26,
    )

    # Top-right: Control Plane
    cp_x = 356
    cp_w = WIDTH - MARGIN - cp_x  # 532
    f.zone(
        cp_x, 0, cp_w, 148, "purple",
        "Control Plane (Job Registry & DAG State Store)",
        "Validates cron & DAG specs · Persists durable schedules across 3 AZs",
        icon="settings_suggest", dashed=True,
    )
    api = f.node(
        cp_x + 18, 56, 238, 76, "purple",
        [("Scheduler API Tier", "name"), ("Cron parse · DAG check", "sub")],
        icon="rule", kind="card", icon_size=24,
    )
    db = f.node(
        cp_x + 274, 56, 240, 76, "amber",
        [("Metadata & Run DB", "name"), ("jobs · runs · deps", "mono")],
        icon="save", kind="card", icon_size=24,
    )

    # Middle: Sharded Time-Wheel Dispatch
    disp_z = f.zone(
        MARGIN, 186, INNER, 152, "amber",
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
        dbx = f.node(dx, 246, dw, 74, tone, [(hdr, "name"), (sub, "mono" if i == 0 else "sub")], icon=ic, kind="card", icon_size=24)
        d_boxes.append(dbx)
    f.wire([d_boxes[0].right(0), d_boxes[1].left(0)], tone="amber", width=1.8)
    f.wire([d_boxes[1].right(0), d_boxes[2].left(0)], tone="blue", width=1.8)

    # Bottom: Worker Pool & Recovery
    wrk_z = f.zone(
        MARGIN, 378, INNER, 160, "green",
        "Data Plane: Stateless Worker Execution Pool, Lease Reaper, and DLQ",
        "Workers execute idempotent tasks with fencing attempt_id while the reaper reclaims crashed leases",
        icon="developer_board",
    )
    w1 = f.node(MARGIN + 17, 440, 262, 82, "green", [("Worker Pool (Auto-Scaled)", "name"), ("Pull task · Heartbeat 10 s", "sub")], icon="play_arrow", kind="card", icon_size=24)
    w2 = f.node(MARGIN + 297, 440, 262, 82, "amber", [("Lease Reaper Daemon", "name"), ("Reclaims expired RUNNING", "sub")], icon="timer", kind="card", icon_size=24)
    w3 = f.node(MARGIN + 577, 440, 262, 82, "red", [("Dead-Letter Queue (DLQ)", "name"), ("Max retries -> SRE triage", "sub")], icon="warning", kind="mid", icon_size=24)

    # Orthogonal wires
    f.wire([cli.right(0), (cp_x, cli.cy)], tone="blue", width=2.0)
    f.wire([api.right(0), db.left(0)], tone="purple", width=1.8)

    f.wire([db.bottom(-30), (db.cx - 30, 166), (d_boxes[0].cx, 166), (d_boxes[0].cx, disp_z.y)], tone="amber", width=1.8, tail=True)
    f.label(480, 160, "Claim due window (60 s)", tone="amber", cls="small")

    f.wire([d_boxes[2].bottom(0), (d_boxes[2].cx, 358), (w1.cx, 358), (w1.cx, wrk_z.y)], tone="blue", width=2.0)
    f.label(460, 354, "Dispatch leased task", tone="blue", cls="small")

    f.wire([w1.right(0), w2.left(0)], tone="amber", dash=True, width=1.6)
    f.wire([w2.right(0), w3.left(0)], tone="red", dash=True, width=1.7)

    return f.save([
        ("Staging upcoming runs into sharded in-memory time wheels avoids hammering the primary database on every 1-second tick.", "noteb"),
        "If a dispatcher crashes, another shard claims its unleased database rows on the next poll cycle without losing scheduled runs.",
    ])


def ch12_lease_execution():
    f = Fig(
        "ch12_lease_execution",
        "Figure 12-3. Lease-Based Job Claiming, Heartbeat Extension, and Dead-Letter Recovery.",
        472,
    )
    # Top Zone: State Machine
    f.zone(
        MARGIN, 0, INNER, 246, "blue",
        "Job Attempt Lifecycle (Bounded Leases and Monotonic Attempt Fencing)",
        "Every transition increments attempt_id so late responses from zombie workers are rejected",
        icon="loop",
    )
    # Row 1: Happy path (4 states)
    r1_w = 186
    r1_gap = 25
    r1_y = 60
    r1_states = [
        ("1. PENDING", "run_at reached", "gray"),
        ("2. LEASED", "TTL = 30 s claim", "blue"),
        ("3. RUNNING", "Heartbeat 10 s", "teal"),
        ("4. SUCCEEDED", "Trigger DAG child", "green"),
    ]
    r1_boxes = []
    for i, (hdr, sub, tone) in enumerate(r1_states):
        rx = MARGIN + 18 + i * (r1_w + r1_gap)
        rb = f.node(rx, r1_y, r1_w, 66, tone, [(hdr, "monob"), (sub, "small")], layout="center", kind="card", r=10)
        r1_boxes.append(rb)
    for i in range(3):
        f.wire([r1_boxes[i].right(0), r1_boxes[i + 1].left(0)], tone="blue" if i < 2 else "green", width=1.8)

    # Row 2: Failure & recovery path (3 states)
    r2_y = 162
    exp = f.node(r1_boxes[2].x, r2_y, r1_w, 66, "amber", [("LEASE EXPIRED", "monob"), ("Crash or hang", "small")], layout="center", kind="mid", r=10)
    ret = f.node(r1_boxes[1].x, r2_y, r1_w, 66, "purple", [("BACKOFF RETRY", "monob"), ("attempt < max", "small")], layout="center", kind="card", r=10)
    dlq = f.node(r1_boxes[3].x, r2_y, r1_w, 66, "red", [("DEAD LETTER", "monob"), ("attempt == max", "small")], layout="center", kind="mid", r=10)

    f.wire([r1_boxes[2].bottom(0), exp.top(0)], tone="amber", width=1.8)
    f.wire([exp.left(0), ret.right(0)], tone="purple", width=1.8)
    f.wire([exp.right(0), dlq.left(0)], tone="red", width=1.8)
    f.wire([ret.left(0), (r1_boxes[0].cx, ret.cy), r1_boxes[0].bottom(0)], tone="purple", dash=True, width=1.8)
    f.label(r1_boxes[0].cx + 56, 150, "Requeue (attempt+1)", tone="purple", cls="small")

    # Bottom Zone: Invariants
    f.zone(
        MARGIN, 266, INNER, 196, "teal",
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
        f.node(ix, 326, iw, 118, tone, [(hdr, "name"), (mono_l, "monob"), (sub, "small")], layout="center", kind="card", r=10)

    return f.save([
        ("Bounded leases guarantee liveness when workers crash abruptly, while monotonic attempt identifiers fence late commits from stalled workers.", "noteb"),
        "Terminal jobs exceeding their retry budget move deterministically to the dead-letter queue for operator inspection and selective replay.",
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
            ("Submit Notification Request", "POST /v1/notify (priority, dedup_id)", "blue", "notifications_active"),
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
        552,
    )
    # Top-left: Upstream Services
    up = f.node(
        MARGIN, 10, 280, 82, "blue",
        [("Upstream Product Services", "name"), ("Auth OTP · Orders · Campaigns", "sub")],
        icon="laptop", kind="card", icon_size=26,
    )

    # Top-right: Control Plane
    cp_x = 350
    cp_w = WIDTH - MARGIN - cp_x  # 538
    f.zone(
        cp_x, 0, cp_w, 146, "purple",
        "Control Plane (Templates, Preferences & Routing Policy)",
        "Cached in Redis · Enforces opt-outs, quiet hours, rate caps, and provider weights",
        icon="settings_suggest", dashed=True,
    )
    pref = f.node(
        cp_x + 16, 56, 244, 74, "purple",
        [("Preference & Cap Store", "name"), ("Opt-out · DND · Freq cap", "sub")],
        icon="tune", kind="card", icon_size=24,
    )
    tmpl = f.node(
        cp_x + 276, 56, 246, 74, "purple",
        [("Template & Routing DB", "name"), ("i18n · Provider SLA rank", "sub")],
        icon="edit_note", kind="card", icon_size=24,
    )

    # Middle-left: Ingestion API
    ing_z = f.zone(
        MARGIN, 126, 280, 198, "teal",
        "Data Plane: Ingestion Tier",
        "Dedup, validate & enrich",
        icon="shield",
    )
    ing = f.node(
        MARGIN + 16, 188, 248, 118, "teal",
        [("Notification API", "name"), ("SETNX dedup_id (24h)", "mono"), ("Evaluate prefs & DND", "sub")],
        icon="bolt", layout="center", kind="card", icon_size=26,
    )

    # Middle-right: Priority Queues
    q_z = f.zone(
        cp_x, 178, cp_w, 146, "amber",
        "Data Plane: Priority-Isolated Queues (Separate Kafka Topics)",
        "Dedicated broker topics prevent million-user campaigns from delaying OTP alerts",
        icon="view_week",
    )
    qw = 160
    qgap = 12
    for i, (hdr, sub, tone, kind) in enumerate([
        ("P0 Critical", "OTP · < 2 s SLO", "red", "mid"),
        ("P1 Transactional", "Orders · < 15 s", "amber", "card"),
        ("P2 Bulk Promo", "Throttled · Async", "gray", "card"),
    ]):
        qx = cp_x + 16 + i * (qw + qgap)
        f.node(qx, 236, qw, 72, tone, [(hdr, "name"), (sub, "small")], layout="center", kind=kind, r=10)

    # Bottom: Channel Workers & Gateways
    gw_z = f.zone(
        MARGIN, 364, INNER, 178, "blue",
        "Data Plane: Channel Workers, Provider Gateways & Receipt Pipeline",
        "Per-channel worker pools isolate third-party latency and execute automatic provider failover",
        icon="lan",
    )
    gw_w = 196
    gw_gap = 13
    gws = [
        ("Push Workers", "APNs & FCM HTTP/2", "Token refresh", "blue"),
        ("SMS Workers", "Twilio -> Vonage", "Circuit breaker", "teal"),
        ("Email Workers", "SES -> SendGrid", "DKIM & SPF", "purple"),
        ("Receipt Pipeline", "Delivered & bounces", "Auto-suppress", "green"),
    ]
    for i, (hdr, l1, l2, tone) in enumerate(gws):
        gx = MARGIN + 16 + i * (gw_w + gw_gap)
        f.node(gx, 424, gw_w, 102, tone, [(hdr, "name"), (l1, "mono"), (l2, "small")], layout="center", kind="card", r=10)

    # Orthogonal wires
    f.wire([up.bottom(0), (up.cx, ing_z.y)], tone="blue", width=2.0)
    f.label(up.cx + 68, 112, "POST /v1/notify", tone="blue", cls="small")

    f.wire([pref.bottom(-54), (pref.cx - 54, 162), (330, 162), (330, 212), ing.right(-34)], tone="purple", dash=True, width=1.6, tail=True)
    f.wire([tmpl.bottom(0), (tmpl.cx, 162), (330, 162)], tone="purple", dash=True, width=1.5, head=False)

    f.wire([ing.right(18), (cp_x, ing.cy + 18)], tone="amber", width=2.0)
    f.label(330, 286, "Route", tone="amber", cls="small")

    for i in range(3):
        qx = cp_x + 16 + i * (qw + qgap) + qw / 2
        f.wire([(qx, q_z.b), (qx, gw_z.y)], tone="blue", width=1.8)
    f.label(cp_x + 188, 346, "Dedicated worker pools per lane", tone="blue", cls="small")

    f.wire([(MARGIN + 16 + 3 * (gw_w + gw_gap) + gw_w / 2, gw_z.y), (MARGIN + 16 + 3 * (gw_w + gw_gap) + gw_w / 2, 344), (WIDTH - MARGIN - 16, 344)], tone="green", dash=True, width=1.6, head=False)

    return f.save([
        ("Decoupling ingestion from channel delivery via priority-isolated queues absorbs traffic spikes and shields upstream APIs from provider outages.", "noteb"),
        "Delivery receipts and hard-bounce webhooks update the preference and suppression store asynchronously to protect sender reputation.",
    ])


def ch13_priority_fanout():
    f = Fig(
        "ch13_priority_fanout",
        "Figure 13-3. Priority Lane Isolation, Per-Provider Circuit Breakers, and Deduplication.",
        462,
    )
    cw1, cw2, cw3 = 258, 270, 276
    gap = 26
    x1 = MARGIN
    x2 = x1 + cw1 + gap  # 316
    x3 = x2 + cw2 + gap  # 612

    # Column 1: Deduplication & Compliance
    f.zone(x1, 0, cw1, 452, "blue", "1. Dedup & Policy Gate", "Exactly-once intent", icon="shield")
    d1 = f.node(x1 + 14, 66, cw1 - 28, 108, "blue", [
        ("Idempotency Store", "name"),
        ("SETNX dedup:{id}", "mono"),
        ("24 h TTL suppresses retry", "small"),
    ], icon="lock", layout="center", kind="card", icon_size=24)
    d2 = f.node(x1 + 14, 194, cw1 - 28, 108, "amber", [
        ("Suppression Filter", "name"),
        ("Drop opt-out & bounces", "sub"),
        ("Quiet hours -> defer P2", "small"),
    ], icon="block", layout="center", kind="card", icon_size=24)
    d3 = f.node(x1 + 14, 322, cw1 - 28, 112, "teal", [
        ("User Frequency Cap", "name"),
        ("<= 3 promos / user / day", "mono"),
        ("P0 OTP always bypasses", "small"),
    ], icon="timer", layout="center", kind="card", icon_size=24)

    # Column 2: Priority Lane Isolation
    f.zone(x2, 0, cw2, 452, "amber", "2. Priority Lanes", "Zero head-of-line lag", icon="view_week")
    p0 = f.node(x2 + 14, 66, cw2 - 28, 108, "red", [
        ("P0 Critical (OTP)", "name"),
        ("Reserved hot workers", "sub"),
        ("p99 delivery < 2 s", "monob"),
    ], layout="center", kind="mid", r=10)
    p1 = f.node(x2 + 14, 194, cw2 - 28, 108, "amber", [
        ("P1 Transactional", "name"),
        ("Autoscaled consumer pool", "sub"),
        ("p99 delivery < 15 s", "monob"),
    ], layout="center", kind="card", r=10)
    p2 = f.node(x2 + 14, 322, cw2 - 28, 112, "gray", [
        ("P2 Bulk / Promo", "name"),
        ("Token-bucket rate limit", "sub"),
        ("Shed first under load", "small"),
    ], layout="center", kind="card", r=10)

    # Column 3: Per-Provider Circuit Breakers
    f.zone(x3, 0, cw3, 452, "teal", "3. Circuit Breakers", "Multi-provider failover", icon="call_split")
    cb1 = f.node(x3 + 14, 66, cw3 - 28, 108, "teal", [
        ("Primary Gateway", "name"),
        ("Err > 5% -> OPEN state", "mono"),
        ("Isolates slow provider", "small"),
    ], layout="center", kind="card", r=10)
    cb2 = f.node(x3 + 14, 194, cw3 - 28, 108, "green", [
        ("Secondary Failover", "name"),
        ("Reroutes P0 & P1 traffic", "sub"),
        ("Zero user-visible drop", "small"),
    ], layout="center", kind="card", r=10)
    cb3 = f.node(x3 + 14, 322, cw3 - 28, 112, "purple", [
        ("Half-Open Probe & DLQ", "name"),
        ("Canary 1% -> CLOSE", "mono"),
        ("Park exhausted -> DLQ", "small"),
    ], layout="center", kind="card", r=10)

    # Clean horizontal column connectors
    f.wire([d1.right(0), p0.left(0)], tone="red", width=1.8)
    f.wire([d2.right(0), p1.left(0)], tone="amber", width=1.8)
    f.wire([d3.right(0), p2.left(0)], tone="gray", width=1.7)

    f.wire([p0.right(0), cb1.left(0)], tone="teal", width=1.9)
    f.wire([p1.right(0), cb2.left(0)], tone="green", width=1.8)
    f.wire([p2.right(0), cb3.left(0)], tone="purple", dash=True, width=1.7)

    # Vertical state transition inside Column 3
    f.wire([cb1.bottom(0), cb2.top(0)], tone="red", dash=True, width=1.6)
    f.wire([cb2.bottom(0), cb3.top(0)], tone="purple", dash=True, width=1.6)

    return f.save([
        ("Combining deduplication keys with isolated priority queues prevents both duplicate OTP alerts on retries and queue starvation during marketing blasts.", "noteb"),
        "Per-provider circuit breakers shift traffic to secondary gateways within seconds of an upstream outage while half-open probes automate recovery.",
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
