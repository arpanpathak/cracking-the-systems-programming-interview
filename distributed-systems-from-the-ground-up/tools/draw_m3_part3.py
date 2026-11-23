#!/usr/bin/env python3
"""Generate 15 spacious Material Design 3 light+dark SVG figures for Part III (Chapters 14-18).

Every figure prioritizes generous whitespace, concise crisp labels, zero text
overflow in Chrome/Safari, and clear separation of control and data planes.
"""
from figkit_m3 import Fig, WIDTH, MARGIN, build_use_case_fig

INNER = WIDTH - 2 * MARGIN  # 856px usable width


def step_badge(f, cx, cy, num, tone="blue", ring="paper"):
    """Draw a high-contrast circular step badge (r=10 + 3px halo) for light & dark modes."""
    f.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="13.0" class="{ring}"/>')
    f.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="10.0" class="a-{tone}"/>')
    f.add(f'<text x="{cx:.1f}" y="{cy + 3.7:.1f}" text-anchor="middle" class="badge paper">{num}</text>')


def path_legend(f, y, sync_text="Solid: Sync data path (1->5)", async_text="Dashed: Async / control plane"):
    """Draw a compact legend strip distinguishing synchronous data vs async/control wires."""
    f.rect(MARGIN, y, INNER, 28, "c-gray", r=8)
    f.wire([(MARGIN + 18, y + 14), (MARGIN + 52, y + 14)], tone="blue", width=2.0)
    f.text(MARGIN + 60, y + 18, sync_text, "small", "start", tone="blue")
    mid = MARGIN + INNER / 2 + 12
    f.wire([(mid, y + 14), (mid + 34, y + 14)], tone="purple", dash=True, width=1.7)
    f.text(mid + 42, y + 18, async_text, "small", "start", tone="purple")


# =============================================================================
# CHAPTER 14: URL SHORTENER
# =============================================================================

def ch14_use_cases():
    return build_use_case_fig(
        "ch14_use_cases",
        "Figure 14-1. Actors and Use Cases of the Global URL Shortener.",
        "System Boundary: Global URL Shortener",
        "Read-optimized edge redirects · Base62 key allocation · Async analytics",
        actors=[
            ("Link Author", "Web console & API clients", "blue", "person"),
            ("Link Visitor", "Browsers & mobile apps", "teal", "laptop"),
            ("Trust & Analytics", "Abuse filter & click jobs", "purple", "shield"),
        ],
        cases=[
            ("Create Short URL", "POST /v1/links  ->  201 {code, ttl}", "blue", "edit_note"),
            ("Resolve & Redirect", "GET /{code}  ->  302 Location", "teal", "bolt"),
            ("Manage Alias & Expiry", "PATCH / DELETE /v1/links/{code}", "amber", "schedule"),
            ("Query Click Analytics", "GET /v1/links/{code}/stats", "green", "table_rows"),
            ("Quarantine Abusive Link", "POST /v1/links/{code}:block", "red", "block"),
        ],
        links=[
            (0, [0, 2, 3], "blue"),
            (1, [1], "teal"),
            (2, [3, 4], "purple"),
        ],
        notes=[
            ("Redirect traffic exceeds link creation by two to three orders of magnitude, making edge caching essential.", "noteb"),
            "Click aggregation and abuse quarantine run on asynchronous and administrative paths so they never add tail latency to visitor redirects.",
        ],
    )


def ch14_architecture():
    f = Fig(
        "ch14_architecture",
        "Figure 14-2. Control Plane Range Allocator and Read-Optimized Edge Redirect Plane.",
        578,
    )

    # Top: Control Plane
    f.zone(
        MARGIN, 0, INNER, 146, "purple",
        "Control Plane (Abuse Policy, Click Analytics & ID Range Allocation)",
        "Blocklist propagation · Off-path click telemetry · Disjoint counter lease blocks",
        icon="settings_suggest", dashed=True,
    )
    c_abuse = f.node(
        MARGIN + 18, 60, 270, 70, "red",
        [("Abuse & Blocklist Push", "name"), ("Phishing & spam filters", "sub")],
        icon="shield", kind="card", icon_size=26,
    )
    c_click = f.node(
        MARGIN + 308, 60, 310, 70, "teal",
        [("Click Stream & OLAP", "name"), ("Kafka -> ClickHouse", "sub")],
        icon="table_rows", kind="card", icon_size=26,
    )
    c_range = f.node(
        MARGIN + 638, 60, 200, 70, "purple",
        [("Range Allocator", "name"), ("100k blocks (etcd)", "sub")],
        icon="dns", kind="card", icon_size=26,
    )

    # Bottom: Data Plane (concise header leaves x >= 450 completely clear for control wires)
    f.zone(
        MARGIN, 178, INNER, 352, "blue",
        "Data Plane (Edge Redirect & Mapping Store)",
        "L1 CDN -> Redirect -> Redis + Bloom -> Sharded DB",
        icon="layers",
    )

    # Row 1 inside Data Plane (y=240, h=86; badged gaps = 48px >= 46px; wrt.cx == c_range.cx == 770)
    vis = f.node(
        MARGIN + 18, 240, 148, 86, "blue",
        [("App / Web", "name"), ("GET /{code}", "mono")],
        icon="laptop", kind="card", icon_size=24,
    )
    cdn = f.node(
        MARGIN + 214, 240, 172, 86, "teal",
        [("CDN Edge PoP", "name"), ("L1 cache · 302", "sub")],
        icon="bolt", kind="card", icon_size=24,
    )
    rds = f.node(
        MARGIN + 434, 240, 184, 86, "blue",
        [("Redirect Service", "name"), ("Stateless lookup", "sub")],
        icon="swap_horiz", kind="card", icon_size=24,
    )
    wrt = f.node(
        MARGIN + 638, 240, 200, 86, "amber",
        [("Write API", "name"), ("Base62 encoder", "sub")],
        icon="edit_note", kind="card", icon_size=24,
    )

    # Row 2 inside Data Plane (y=406, h=102; db.cx = 664 = midpoint(rds.cx=558, wrt.cx=770))
    rcache = f.node(
        MARGIN + 18, 406, 384, 102, "teal",
        [("Regional Redis Cluster", "name"), ("Hot code -> URL mappings (LRU)", "sub"), ("In-memory Bloom filter for 404 shield", "small")],
        icon="memory", kind="card", icon_size=28,
    )
    db = f.node(
        MARGIN + 426, 406, 412, 102, "blue",
        [("Sharded Mapping Store (3 AZs)", "name"), ("Hash-partitioned by short code", "sub"), ("Primary writes · Read replicas", "small")],
        icon="save", kind="card", icon_size=28,
    )

    # Data plane wires (equal shaft clearance on both sides of every badge)
    f.wire([vis.right(0), cdn.left(0)], tone="blue", width=2.0)
    step_badge(f, (vis.r + cdn.x - 9) / 2, vis.cy, "1", "blue", ring="c-blue")

    f.wire([cdn.right(0), rds.left(0)], tone="teal", width=2.0)
    f.label((cdn.r + rds.x - 9) / 2, cdn.cy - 22, "Miss", tone="teal", cls="badge", back_cls="c-blue")
    step_badge(f, (cdn.r + rds.x - 9) / 2, cdn.cy, "2", "teal", ring="c-blue")

    # Redirect Service centered exit -> clean split at y=354 to Redis (center) & dead-straight DB (-106)
    db_dx = wrt.cx - db.cx  # +106.0 (exact mirror of rds.cx - db.cx = -106.0)
    f.wire([rds.bottom(0), (rds.cx, 354)], tone="teal", head=False, width=1.9)
    f.wire([(rds.cx, 354), (rcache.cx, 354), rcache.top(0)], tone="teal", width=1.9)
    f.label((rcache.cx + rds.cx) / 2, 382, "L2 lookup + Bloom", tone="teal", cls="small", back_cls="c-blue")
    step_badge(f, (rcache.cx + rds.cx) / 2, 354, "3", "teal", ring="c-blue")

    # Redirect Service -> DB (dead-straight vertical into db.top(-106))
    f.wire([(rds.cx, 354), db.top(-db_dx)], tone="blue", width=1.9)
    f.label(rds.cx + 48, 382, "Cold miss", tone="blue", cls="small", back_cls="c-blue")
    step_badge(f, rds.cx, (354 + db.y - 9) / 2, "4", "blue", ring="c-blue")

    # Write API -> DB (dead-straight vertical into db.top(+106))
    f.wire([wrt.bottom(0), db.top(db_dx)], tone="amber", width=2.0)
    f.label(wrt.cx - 48, (wrt.b + db.y - 9) / 2 + 4, "PUT map", tone="amber", cls="small", back_cls="c-blue")
    step_badge(f, wrt.cx, (wrt.b + db.y - 9) / 2, "5", "amber", ring="c-blue")

    # Control plane dashed wires — ZERO header or wire crossings!
    # Blocklist sync routed cleanly via outer left gutter (x=16) to y=344 -> cdn.bottom(0)
    f.wire([c_abuse.left(0), (16, c_abuse.cy), (16, 344), (cdn.cx, 344), cdn.bottom(0)], tone="red", dash=True, width=1.6)
    f.label(144, 348, "Blocklist sync", tone="red", cls="small", back_cls="c-blue")

    # Async clicks & ID range lease (dead-straight vertical at x=760)
    f.wire([rds.top(0), (rds.cx, 162), (c_click.cx, 162), c_click.bottom(0)], tone="teal", dash=True, width=1.6)
    f.label(536, 164, "Async clicks", tone="teal", cls="small")

    f.wire([c_range.bottom(0), wrt.top(0)], tone="purple", dash=True, width=1.6)
    f.label(c_range.cx - 64, 164, "ID range lease", tone="purple", cls="small")

    path_legend(
        f, 542,
        "Solid: Sync redirect & write (1 Device -> 2 CDN -> 3 Redis -> 4-5 DB)",
        "Dashed: Blocklist push, async clicks & ID range lease",
    )

    return f.save([
        ("Range leasing eliminates cross-host write coordination while keeping short codes collision-free across regions (5).", "noteb"),
        "Write servers pre-allocate disjoint 100,000-ID ranges from etcd and encode each value with a Feistel permutation before Base62 formatting; redirect traffic resolves via L1 CDN and L2 Redis + Bloom (1-4).",
    ])


def ch14_redirect_cache():
    f = Fig(
        "ch14_redirect_cache",
        "Figure 14-3. Multi-Tier Redirect Cache Hierarchy and Bloom-Filter Negative Lookup Defense.",
        492,
    )

    # Top Zone: Multi-tier read cascade (50px badged gaps)
    f.zone(
        MARGIN, 0, INNER, 196, "blue",
        "Multi-Tier Redirect Cache Cascade (99.8% of Lookups Resolved Before Storage)",
        "Each tier absorbs progressively colder traffic while bounding tail latency under read spikes",
        icon="bolt",
    )
    tiers = [
        ("L1: CDN Edge PoP", "~10 ms · 80% hit", "Hot viral links", "green", "bolt"),
        ("L2: Regional Redis", "~2 ms · 18% hit", "Active LRU tail", "teal", "memory"),
        ("Bloom Filter Gate", "< 0.2 ms · O(k)", "Blocks 404 scans", "amber", "shield"),
        ("L3: Sharded Store", "~12 ms · < 2%", "Cold long-tail", "blue", "save"),
    ]
    tw = 168
    tgap = 50
    tboxes = []
    badge_tones = ["green", "teal", "amber"]
    for i, (t_hdr, t_stat, t_sub, tone, ic) in enumerate(tiers):
        tx = MARGIN + 17 + i * (tw + tgap)
        box = f.node(
            tx, 66, tw, 108, tone,
            [(t_hdr, "name"), (t_stat, "monob"), (t_sub, "small")],
            icon=ic, layout="center", kind="card", icon_size=26,
        )
        tboxes.append(box)
        if i < 3:
            a, b = box.r, tx + tw + tgap
            f.wire([box.right(0), (b, box.cy)], tone=badge_tones[i], width=1.9)
            cx = (a + b - 9) / 2
            lbl = "Miss" if i < 2 else "Maybe"
            f.label(cx, box.cy - 22, lbl, tone=badge_tones[i], cls="badge", back_cls="c-blue")
            step_badge(f, cx, box.cy, str(i + 1), badge_tones[i], ring="c-blue")

    # Bottom Left: Bloom Filter Defense
    lw = 416
    f.zone(
        MARGIN, 218, lw, 264, "amber",
        "Bloom-Filter Negative Lookup Defense",
        "Stops random code enumeration from exhausting DB IOPS",
        icon="shield",
    )
    bf1 = f.node(
        MARGIN + 18, 280, 164, 64, "red",
        [("Unknown Code", "name"), ("GET /x9Z2q1", "mono")],
        layout="center", kind="mid", r=10,
    )
    bf2 = f.node(
        MARGIN + 234, 280, 164, 64, "amber",
        [("k=7 Hash Bits", "name"), ("Bit[h_i] == 0?", "mono")],
        layout="center", kind="card", r=10,
    )
    f.wire([bf1.right(0), bf2.left(0)], tone="amber", width=1.9)
    step_badge(f, (bf1.r + bf2.x - 9) / 2, bf1.cy, "4", "amber", ring="c-amber")

    bf3 = f.node(
        MARGIN + 18, 404, 178, 64, "green",
        [("Any Bit = 0", "monob"), ("Instant 404 (0 DB reads)", "small")],
        layout="center", kind="card", r=10,
    )
    bf4 = f.node(
        MARGIN + 220, 404, 178, 64, "blue",
        [("All Bits = 1", "monob"), ("Query DB (~1% FP rate)", "small")],
        layout="center", kind="card", r=10,
    )
    # Clean orthogonal split bus at y=374 (exact vertical midpoint between 344 and 404)
    bus_y = 374
    f.wire([bf2.bottom(0), (bf2.cx, bus_y)], tone="amber", head=False, width=1.8)
    f.rule(bf3.cx, bus_y, bf2.cx, bus_y, tone="amber", width=1.8)
    f.wire([(bf3.cx, bus_y), bf3.top(0)], tone="green", width=1.8)
    f.wire([(bf4.cx, bus_y), bf4.top(0)], tone="blue", width=1.8)
    step_badge(f, (bf3.cx + bf2.cx) / 2, bus_y, "5", "purple", ring="c-amber")

    # Bottom Right: 301 vs 302 Trade-Off
    rx = MARGIN + lw + 24
    rw = INNER - lw - 24
    f.zone(
        rx, 218, rw, 264, "purple",
        "HTTP 301 vs. 302 Redirect Trade-Off",
        "Balancing origin load against telemetry and revocation",
        icon="tune",
    )
    f.node(
        rx + 18, 286, rw - 36, 76, "gray",
        [("301 Moved Permanently", "name"), ("Browser caches target · Bypasses click count", "sub")],
        icon="schedule", kind="card", icon_size=24,
    )
    f.node(
        rx + 18, 384, rw - 36, 76, "green",
        [("302 Found (Chosen Default)", "name"), ("Revalidates at edge · Instant link revocation", "sub")],
        icon="play_arrow", kind="card", icon_size=24,
    )

    return f.save([
        ("A 10 bits-per-key Bloom filter cuts database negative lookups by roughly 99% while occupying about 1.2 GB for 1 billion active codes.", "noteb"),
        "Returning HTTP 302 with short edge cache TTLs keeps click telemetry accurate and allows quarantined links to stop redirecting within seconds.",
    ])


# =============================================================================
# CHAPTER 15: NEWS FEED
# =============================================================================

def ch15_use_cases():
    return build_use_case_fig(
        "ch15_use_cases",
        "Figure 15-1. Actors and Use Cases of the Social News Feed Service.",
        "System Boundary: Social News Feed Service",
        "Hybrid fan-out · Cursor-paginated timelines · ML candidate ranking",
        actors=[
            ("Post Author", "Regular & celebrity users", "blue", "person"),
            ("Feed Reader", "Mobile & web timelines", "teal", "laptop"),
            ("Ranking & Safety", "ML scorer & moderation", "purple", "tune"),
        ],
        cases=[
            ("Publish Post & Media", "POST /v1/posts  ->  201 {post_id}", "blue", "edit_note"),
            ("Fetch Ranked Timeline", "GET /v1/feeds/{id}?cursor=c&limit=n", "teal", "view_week"),
            ("Follow or Unfollow", "PUT / DELETE /v1/users/{u}/following/{v}", "amber", "handshake"),
            ("Delete or Hide Post", "DELETE /v1/posts/{id}", "red", "close"),
            ("Rank & Filter Candidates", "Score top-K + policy suppression", "purple", "settings_suggest"),
        ],
        links=[
            (0, [0, 2, 3], "blue"),
            (1, [1, 2], "teal"),
            (2, [4], "purple"),
        ],
        notes=[
            ("Feed construction balances sub-100 ms timeline reads against extreme follower skew for high-fan-out celebrity accounts.", "noteb"),
            "Cursor pagination keyed by opaque post identifiers prevents duplicate or skipped items when new posts arrive between page fetches.",
        ],
    )


def ch15_architecture():
    f = Fig(
        "ch15_architecture",
        "Figure 15-2. Publish Pipeline, Social Graph Service, Timeline Store, and Ranking Path.",
        594,
    )

    # Top: Control Plane (ordered ML | Graph | Policy so all 3 outer-gutter routes have ZERO crossings)
    f.zone(
        MARGIN, 0, INNER, 146, "purple",
        "Control Plane (Ranking Models, Social Graph & Fan-Out Thresholds)",
        "Feature weights · Sharded follower edge lists · Celebrity fan-out cutoff (> 100k)",
        icon="settings_suggest", dashed=True,
    )
    c_ml = f.node(
        MARGIN + 18, 60, 256, 70, "teal",
        [("Ranking Model Registry", "name"), ("Weights & safety rules", "sub")],
        icon="developer_board", kind="card", icon_size=26,
    )
    c_graph = f.node(
        MARGIN + 298, 60, 260, 70, "purple",
        [("Social Graph Service", "name"), ("Sharded follower lists", "sub")],
        icon="lan", kind="card", icon_size=26,
    )
    c_pol = f.node(
        MARGIN + 582, 60, 256, 70, "amber",
        [("Fan-Out Policy Config", "name"), ("Celebrity cutoff > 100k", "sub")],
        icon="tune", kind="card", icon_size=26,
    )

    # Bottom: Data Plane
    f.zone(
        MARGIN, 178, INNER, 346, "blue",
        "Data Plane (Publish Fan-Out & Low-Latency Feed Read Assembly)",
        "Top lane: author device -> durable publish -> fan-out   |   Bottom lane: merge -> rank -> reader device",
        icon="layers",
    )

    # Write Lane (Left -> Right, y=242, h=84; badged gaps = 48px >= 46px; fw.cx == tcache.cx == 776)
    pub = f.node(
        MARGIN + 18, 242, 174, 84, "blue",
        [("Post API", "name"), ("App / Web POST", "mono")],
        icon="edit_note", kind="card", icon_size=24,
    )
    pstore = f.node(
        MARGIN + 240, 242, 178, 84, "blue",
        [("Post Store (DB)", "name"), ("Durable content", "sub")],
        icon="save", kind="card", icon_size=24,
    )
    mq = f.node(
        MARGIN + 466, 242, 152, 84, "amber",
        [("Kafka Topic", "name"), ("Publish log", "sub")],
        icon="swap_horiz", kind="card", icon_size=24,
    )
    fw = f.node(
        MARGIN + 650, 242, 188, 84, "teal",
        [("Fan-Out Workers", "name"), ("Push normal IDs", "sub")],
        icon="bolt", kind="card", icon_size=24,
    )

    # Read Lane (Right -> Left serpentine, y=402, h=106; badged gaps = 50px >= 46px)
    rank = f.node(
        MARGIN + 18, 402, 238, 106, "green",
        [("Ranker -> Reader App", "name"), ("Score top-K candidates", "sub"), ("Paged JSON to Mobile/Web", "small")],
        icon="play_arrow", kind="card", icon_size=26,
    )
    agg = f.node(
        MARGIN + 306, 402, 294, 106, "blue",
        [("Feed Aggregator", "name"), ("Merge inbox + celebrity", "sub"), ("Hydrate post bodies", "small")],
        icon="view_week", kind="card", icon_size=26,
    )
    tcache = f.node(
        MARGIN + 650, 402, 188, 106, "teal",
        [("Timeline Store", "name"), ("Redis ZSETs", "sub"), ("Top 800 IDs", "small")],
        icon="memory", kind="card", icon_size=24,
    )

    # Write lane wires (equal shaft clearance on both sides of every badge)
    f.wire([pub.right(0), pstore.left(0)], tone="blue", width=1.9)
    step_badge(f, (pub.r + pstore.x - 9) / 2, pub.cy, "1", "blue", ring="c-blue")

    f.wire([pstore.right(0), mq.left(0)], tone="amber", width=1.9)
    step_badge(f, (pstore.r + mq.x - 9) / 2, pstore.cy, "2", "amber", ring="c-blue")

    f.wire([mq.right(0), fw.left(0)], tone="amber", dash=True, width=1.8)

    # Serpentine drop: Fan-Out Workers -> Timeline Store (76px vertical arrow)
    f.wire([fw.bottom(0), (fw.cx, tcache.y)], tone="teal", dash=True, width=1.9)
    f.label(fw.cx - 64, (fw.b + tcache.y - 9) / 2 + 4, "ZADD post_id", tone="teal", cls="mono", back_cls="c-blue")
    step_badge(f, fw.cx, (fw.b + tcache.y - 9) / 2, "3", "teal", ring="c-blue")

    # Read lane wires (Right -> Left; left-pointing single arrows -> +9/2)
    f.wire([tcache.left(0), agg.right(0)], tone="teal", width=2.0)
    step_badge(f, (agg.r + tcache.x + 9) / 2, agg.cy, "4", "teal", ring="c-blue")

    f.wire([agg.left(0), rank.right(0)], tone="green", width=2.0)
    step_badge(f, (rank.r + agg.x + 9) / 2, agg.cy, "5", "green", ring="c-blue")

    # Hydrate post store -> Feed Aggregator (clean inner channel, centered endpoints, zero crossings)
    f.wire([pstore.bottom(0), (pstore.cx, 364), (agg.cx, 364), agg.top(0)], tone="blue", dash=True, width=1.6, tail=True)
    f.label((pstore.cx + agg.cx) / 2, 354, "Hydrate", tone="blue", cls="small", back_cls="c-blue")

    # Control plane dashed wires — dedicated outer left, right-inner, and right-outer/bottom gutters (ZERO crossings!)
    # 1. Model push: left outer gutter x=16 -> bottom gutter y=540 -> rank.bottom(0)
    f.wire([c_ml.left(0), (16, c_ml.cy), (16, 540), (rank.cx, 540), rank.bottom(0)], tone="teal", dash=True, width=1.6)
    f.label(270, 542, "Model push (left gutter)", tone="teal", cls="small")

    # 2. Follower lookup: top corridor y=160 -> right inner gutter x=896 -> fw.right(0)
    f.wire([c_graph.bottom(0), (c_graph.cx, 160), (896, 160), (896, fw.cy), fw.right(0)], tone="purple", dash=True, width=1.6, tail=True)
    f.label(660, 162, "Follower lookup", tone="purple", cls="small")

    # 3. Cutoff policy: right outer gutter x=908 -> bottom gutter y=540 -> agg.bottom(0)
    f.wire([c_pol.right(0), (908, c_pol.cy), (908, 540), (agg.cx, 540), agg.bottom(0)], tone="amber", dash=True, width=1.6)
    f.label(684, 542, "Cutoff policy (> 100k -> pull merge)", tone="amber", cls="small")

    path_legend(
        f, 558,
        "Solid: Sync publish & read assembly (1-2 Publish, 4-5 Merge & Rank)",
        "Dashed: Async Kafka fan-out (3), hydrate & control gutters",
    )

    return f.save([
        ("Timeline entries store compact 8-byte post IDs rather than full payloads so active feeds remain memory-resident in Redis.", "noteb"),
        "Fan-out workers act as the sole asynchronous writers to user timelines (3), preventing write contention while allowing the feed aggregator to hydrate and rank candidates on read (4-5).",
    ])


def ch15_hybrid_fanout():
    f = Fig(
        "ch15_hybrid_fanout",
        "Figure 15-3. Hybrid Fan-Out: Push for Normal Accounts and Read-Time Merge for Celebrities.",
        476,
    )

    # Top Zone: Symmetric 1-to-2 Fan-Out Split by Follower Threshold
    f.zone(
        MARGIN, 0, INNER, 256, "purple",
        "Publish Path: Follower-Threshold Split (<= 100k Push vs. > 100k Pull)",
        "Routes normal accounts to async inbox push and celebrity accounts to single-write outbox cache",
        icon="call_split",
    )
    pub_node = f.node(
        MARGIN + 18, 108, 168, 86, "blue",
        [("New Post Publish", "name"), ("Check follower count", "sub"), ("Threshold = 100k", "small")],
        icon="edit_note", layout="center", kind="card", icon_size=24,
    )

    # Path A (Normal <= 100k): cy = 98
    a1 = f.node(
        MARGIN + 282, 60, 254, 76, "teal",
        [("Path A: Normal (<= 100k)", "name"), ("Push post IDs via Kafka", "sub"), ("500 async Redis ZADD", "small")],
        icon="bolt", kind="card", icon_size=24,
    )
    a2 = f.node(
        MARGIN + 588, 60, 250, 76, "green",
        [("Follower Inbox ZSET", "name"), ("O(1) read latency", "sub"), ("Bounded write work", "small")],
        icon="memory", kind="card", icon_size=24,
    )

    # Path B (Celebrity > 100k): cy = 204
    b1 = f.node(
        MARGIN + 282, 166, 254, 76, "amber",
        [("Path B: Celebrity (> 100k)", "name"), ("Skip follower push", "sub"), ("Append to own outbox", "small")],
        icon="person", kind="card", icon_size=24,
    )
    b2 = f.node(
        MARGIN + 588, 166, 250, 76, "purple",
        [("Author Outbox Cache", "name"), ("1 write · Zero storm", "sub"), ("Merged on active read", "small")],
        icon="save", kind="card", icon_size=24,
    )

    # Symmetric 1-to-2 split: exact midpoint x_mid = (pub_node.r + a1.x) / 2 = 266
    x_mid = (pub_node.r + a1.x) / 2
    f.wire([pub_node.right(0), (x_mid, pub_node.cy)], tone="blue", head=False, width=2.0)
    f.rule(x_mid, a1.cy, x_mid, b1.cy, tone="blue", width=2.0)
    f.wire([(x_mid, a1.cy), a1.left(0)], tone="teal", width=2.0)
    f.wire([(x_mid, b1.cy), b1.left(0)], tone="amber", width=2.0)
    f.label((x_mid + a1.x) / 2, a1.cy - 14, "<= 100k", tone="teal", cls="badge", back_cls="c-purple")
    f.label((x_mid + b1.x) / 2, b1.cy + 20, "> 100k", tone="amber", cls="badge", back_cls="c-purple")
    step_badge(f, (pub_node.r + x_mid) / 2, pub_node.cy, "1", "blue", ring="c-purple")

    # Path A & B horizontal arrows (52px >= 46px)
    f.wire([a1.right(0), a2.left(0)], tone="teal", width=2.0)
    step_badge(f, (a1.r + a2.x - 9) / 2, a1.cy, "2", "teal", ring="c-purple")

    f.wire([b1.right(0), b2.left(0)], tone="amber", width=2.0)
    step_badge(f, (b1.r + b2.x - 9) / 2, b1.cy, "3", "amber", ring="c-purple")

    # Centered transition connector between Publish and Read-Time Merge zones
    f.wire([(WIDTH / 2, 256), (WIDTH / 2, 304)], tone="blue", dash=True, width=1.9)
    f.label(WIDTH / 2 + 88, 284, "On reader timeline fetch", tone="blue", cls="small")

    # Bottom Zone: Read-time K-way merge (52px badged gaps)
    f.zone(
        MARGIN, 304, INNER, 162, "blue",
        "Read-Time K-Way Merge & Cursor Pagination (Feed Aggregator)",
        "Combines precomputed normal inbox with followed celebrity outboxes in under 50 ms",
        icon="view_week",
    )
    m1 = f.node(
        MARGIN + 18, 368, 238, 76, "teal",
        [("Fetch Normal Inbox", "name"), ("Precomputed Redis ZSET", "sub")],
        icon="memory", kind="card", icon_size=24,
    )
    m2 = f.node(
        MARGIN + 308, 368, 240, 76, "blue",
        [("K-Way Heap Merge", "name"), ("Add celebrity outboxes", "sub")],
        icon="layers", kind="card", icon_size=24,
    )
    m3 = f.node(
        MARGIN + 600, 368, 238, 76, "green",
        [("Rank & Return Page", "name"), ("?cursor=last_post_id", "mono")],
        icon="play_arrow", kind="card", icon_size=24,
    )
    f.wire([m1.right(0), m2.left(0)], tone="blue", width=2.0)
    step_badge(f, (m1.r + m2.x - 9) / 2, m1.cy, "4", "blue", ring="c-blue")

    f.wire([m2.right(0), m3.left(0)], tone="green", width=2.0)
    step_badge(f, (m2.r + m3.x - 9) / 2, m2.cy, "5", "green", ring="c-blue")

    return f.save([
        ("Pure push collapses when a 10-million-follower account publishes, whereas pure pull creates slow fan-in queries for every reader.", "noteb"),
        "Splitting authors at a configurable follower threshold (such as 100,000) bounds both background write work and synchronous read fan-in.",
    ])


# =============================================================================
# CHAPTER 16: OBJECT STORE
# =============================================================================

def ch16_use_cases():
    return build_use_case_fig(
        "ch16_use_cases",
        "Figure 16-1. Actors and Use Cases of the Distributed Object Store.",
        "System Boundary: Distributed Object Store",
        "Immutable blob storage · Erasure-coded durability · Background repair",
        actors=[
            ("Application Client", "Services & SDK uploads", "blue", "apps"),
            ("Bucket Owner", "Lifecycle & access policy", "amber", "lock"),
            ("Storage Operator", "Scrubbing & capacity SRE", "purple", "engineering"),
        ],
        cases=[
            ("Upload & Download Object", "PUT / GET /v1/buckets/{b}/{key}", "blue", "save"),
            ("Multipart Large Upload", "Init -> UploadPart -> Complete", "teal", "layers"),
            ("Delete & Version Control", "DELETE /v1/buckets/{b}/{key}", "amber", "close"),
            ("List Bucket Prefix", "GET /v1/buckets/{b}?prefix=p", "green", "table_rows"),
            ("Scrub, Repair & Reclaim", "Checksum verify · RS rebuild · GC", "purple", "shield"),
        ],
        links=[
            (0, [0, 1, 2, 3], "blue"),
            (1, [2, 3], "amber"),
            (2, [4], "purple"),
        ],
        notes=[
            ("Separating object metadata (names and chunk manifests) from immutable byte storage enables independent scaling of namespace lookups and disk throughput.", "noteb"),
            "Garbage collection reclaims unreferenced chunks only after a grace period so concurrent multipart commits cannot lose newly linked data.",
        ],
    )


def ch16_architecture():
    f = Fig(
        "ch16_architecture",
        "Figure 16-2. Metadata Control Plane, API Gateway, and Erasure-Coded Chunk Storage Nodes.",
        596,
    )

    # Top: Control Plane
    f.zone(
        MARGIN, 0, INNER, 148, "purple",
        "Control Plane (Metadata Namespace, Placement Map & Background Repair)",
        "Atomic manifest commits · Failure-domain placement · Continuous bit-rot scrubbing",
        icon="settings_suggest", dashed=True,
    )
    c_meta = f.node(
        MARGIN + 18, 60, 260, 72, "purple",
        [("Metadata Cluster", "name"), ("Key -> chunk manifest", "sub")],
        icon="dns", kind="card", icon_size=26,
    )
    c_map = f.node(
        MARGIN + 300, 60, 256, 72, "amber",
        [("Placement Controller", "name"), ("AZ & rack failure map", "sub")],
        icon="lan", kind="card", icon_size=26,
    )
    c_scrub = f.node(
        MARGIN + 578, 60, 260, 72, "teal",
        [("Scrubber & GC Tier", "name"), ("CRC verify · RS repair", "sub")],
        icon="loop", kind="card", icon_size=26,
    )

    # Bottom: Data Plane
    f.zone(
        MARGIN, 180, INNER, 368, "blue",
        "Data Plane (Stateless Object Gateways & Erasure-Coded Chunk Nodes)",
        "Objects split into 64 MB immutable chunks encoded as RS(6, 3) stripes across 3 AZs",
        icon="layers",
    )

    # Row 1: Ingress and Gateway (strictly symmetric around x=460; badged gaps = 50px >= 46px)
    app = f.node(
        MARGIN + 18, 240, 216, 86, "blue",
        [("Clients / SDKs", "name"), ("Mobile · Web · S3", "sub")],
        icon="laptop", kind="card", icon_size=24,
    )
    gw = f.node(
        MARGIN + 284, 240, 288, 86, "teal",
        [("Object API Gateway", "name"), ("Auth · 64 MB chunk · CRC32C", "sub"), ("RS(6, 3) stripe encoder/decoder", "small")],
        icon="swap_horiz", kind="card", icon_size=26,
    )
    mp = f.node(
        MARGIN + 622, 240, 216, 86, "amber",
        [("Multipart Manager", "name"), ("Stage · Atomic seal", "sub")],
        icon="inventory_2", kind="card", icon_size=24,
    )

    # Row 2: 3 Failure Domains (az_boxes[1].cx == gw.cx == 460)
    az_w = 258
    az_gap = 22
    az_xs = [MARGIN + 19 + i * (az_w + az_gap) for i in range(3)]
    az_specs = [
        ("Failure Domain A (AZ-1)", "Shards D1, D2, P1", "NVMe chunk stores + CRC", "blue"),
        ("Failure Domain B (AZ-2)", "Shards D3, D4, P2", "NVMe chunk stores + CRC", "blue"),
        ("Failure Domain C (AZ-3)", "Shards D5, D6, P3", "NVMe chunk stores + CRC", "blue"),
    ]
    az_boxes = []
    for i, (t1, t2, t3, tone) in enumerate(az_specs):
        box = f.node(
            az_xs[i], 414, az_w, 114, tone,
            [(t1, "name"), (t2, "monob"), (t3, "small")],
            icon="save", layout="center", kind="card", icon_size=26,
        )
        az_boxes.append(box)

    # Data plane wires (equal shaft clearance on both sides of every badge)
    f.wire([app.right(0), gw.left(0)], tone="blue", width=2.0)
    step_badge(f, (app.r + gw.x - 9) / 2, app.cy, "1", "blue", ring="c-blue")

    f.wire([gw.right(0), mp.left(0)], tone="amber", width=1.8, tail=True)
    step_badge(f, (gw.r + mp.x) / 2, gw.cy, "2", "amber", ring="c-blue")

    # Symmetric 1-to-3 Gateway -> 3 AZs fan-out bus (trunk=50px, equal branches=38px)
    bus_y = 376
    f.wire([gw.bottom(0), (gw.cx, bus_y)], tone="teal", head=False, width=2.0)
    f.rule(az_boxes[0].cx, bus_y, az_boxes[2].cx, bus_y, tone="teal", width=2.0)
    for b in az_boxes:
        f.wire([(b.cx, bus_y), b.top(0)], tone="teal", width=2.0)
    f.label(gw.cx + 140, bus_y + 18, "Parallel RS(6, 3) shard write / read", tone="teal", cls="small", back_cls="c-blue")
    step_badge(f, gw.cx, (gw.b + bus_y) / 2, "3", "teal", ring="c-blue")

    # Control plane dashed wires — ZERO header or wire crossings!
    # 1. Manifest commit: left outer gutter x=16 -> y=348 -> gw.bottom(-96)
    f.wire([c_meta.left(0), (16, c_meta.cy), (16, 348), (gw.cx - 96, 348), gw.bottom(-96)], tone="purple", dash=True, width=1.6, tail=True)
    f.label(162, 352, "Manifest commit", tone="purple", cls="small", back_cls="c-blue")
    step_badge(f, 16, (c_meta.cy + 348) / 2, "4", "purple")

    # 2. Placement map: top corridor y=162 -> right inner gutter x=896 -> y=348 -> gw.bottom(96)
    f.wire([c_map.bottom(0), (c_map.cx, 162), (896, 162), (896, 348), (gw.cx + 96, 348), gw.bottom(96)], tone="amber", dash=True, width=1.6)
    f.label(664, 164, "Placement map", tone="amber", cls="small")

    # 3. Scrub & rebuild: right outer gutter x=908 -> az_boxes[2].right(0)
    f.wire([c_scrub.right(0), (908, c_scrub.cy), (908, az_boxes[2].cy), az_boxes[2].right(0)], tone="teal", dash=True, width=1.6, tail=True)
    step_badge(f, 908, (c_scrub.cy + az_boxes[2].cy) / 2, "5", "teal")

    path_legend(
        f, 560,
        "Solid: Sync blob upload (1 PUT -> 2 Stage -> 3 RS(6,3) stripe)",
        "Dashed: Manifest commit (4), placement map & async scrub (5)",
    )

    return f.save([
        ("Chunks are immutable and written across 3 AZs (1-3) before the metadata manifest commits (4), so aborted uploads never expose partial objects.", "noteb"),
        "Spreading the nine shards of an RS(6, 3) stripe evenly across three availability zones lets the store survive an entire AZ outage while background scrubbers (5) repair silent bit-rot.",
    ])


def ch16_erasure_coding():
    f = Fig(
        "ch16_erasure_coding",
        "Figure 16-3. Reed-Solomon RS(6, 3) Placement Across Failure Domains and Background Scrubbing.",
        476,
    )

    # Top Zone: RS(6, 3) Stripe Across 3 Failure Domains
    f.zone(
        MARGIN, 0, INNER, 200, "blue",
        "Reed-Solomon RS(6, 3) Stripe Layout Across 9 Disks in 3 Availability Zones",
        "6 data shards + 3 parity shards = 1.5x storage overhead (vs. 3.0x for 3-way replication)",
        icon="view_module",
    )
    f.pill(WIDTH - MARGIN - 16, 16, "Tolerates any 3 losses", tone="green", anchor="end")

    dom_w = 258
    dom_gap = 22
    dom_xs = [MARGIN + 19 + i * (dom_w + dom_gap) for i in range(3)]
    domains = [
        ("AZ-1 (Rack 1)", [("D1", "blue", "OK"), ("D2", "blue", "OK"), ("P1", "amber", "OK")]),
        ("AZ-2 (Rack 2)", [("D3", "blue", "OK"), ("D4", "red", "BAD"), ("P2", "amber", "OK")]),
        ("AZ-3 (Rack 3)", [("D5", "blue", "OK"), ("D6", "blue", "OK"), ("P3", "amber", "OK")]),
    ]
    for i, (dtitle, shards) in enumerate(domains):
        dx = dom_xs[i]
        f.rect(dx, 62, dom_w, 120, "card", r=12, lift=True)
        f.text(dx + 14, 84, dtitle, "name", "start", tone="blue", fit=(dx + 10, dx + dom_w - 10))
        sw = 72
        sgap = 10
        for j, (sid, tone, status) in enumerate(shards):
            sx = dx + 11 + j * (sw + sgap)
            kind = "mid" if tone == "red" else "tonal"
            f.cell(sx, 98, sw, 68, tone, [(sid, "monob"), (status, "badge")], kind=kind, r=8, text_tone=tone)

    # Bottom Zone: Background Scrubbing and Reconstruction Pipeline
    f.zone(
        MARGIN, 224, INNER, 242, "teal",
        "Background Bit-Rot Scrubbing and Online Stripe Reconstruction",
        "Periodic checksum verification detects silent disk corruption before a second failure strikes",
        icon="shield",
    )
    steps = [
        ("Periodic Scrub", "Read shard + CRC32C", "Detects bit-rot on D4", "teal", "schedule"),
        ("Quarantine D4", "Mark shard offline", "Route reads via RS", "red", "warning"),
        ("RS(6, 3) Rebuild", "Read any 6 healthy", "Recompute D4 in RAM", "amber", "developer_board"),
        ("Atomic Swap", "Write D4 to spare", "Update chunk map", "green", "save"),
    ]
    cw = 168
    cgap = 50
    step_tones = ["red", "amber", "green"]
    for i, (hdr, sub1, sub2, tone, ic) in enumerate(steps):
        cx = MARGIN + 17 + i * (cw + cgap)
        box = f.node(
            cx, 288, cw, 114, tone,
            [(hdr, "name"), (sub1, "small"), (sub2, "small")],
            icon=ic, layout="center", kind="card" if tone != "red" else "mid", icon_size=24,
        )
        if i < 3:
            a, b = box.r, cx + cw + cgap
            f.wire([box.right(0), (b, box.cy)], tone=step_tones[i], width=1.9)
            step_badge(f, (a + b - 9) / 2, box.cy, str(i + 1), step_tones[i], ring="c-teal")

    # Summary comparison bar at bottom of zone
    f.cell(
        MARGIN + 20, 418, 400, 34, "gray",
        [("3-Way Replication: 3.0x space · Simple copy repair", "small")],
        kind="card", r=8,
    )
    f.cell(
        MARGIN + 436, 418, 400, 34, "green",
        [("RS(6, 3) Chosen: 1.5x space · 50% capacity saved", "small")],
        kind="card", r=8,
    )

    return f.save([
        ("Silent bit-rot returns corrupted bytes without triggering a disk I/O error; only end-to-end CRC32C scrubbing exposes latent damage.", "noteb"),
        "Reed-Solomon RS(6, 3) cuts raw storage overhead in half relative to triple replication while preserving durability across three concurrent shard or rack failures.",
    ])


# =============================================================================
# CHAPTER 17: VIDEO STREAMING
# =============================================================================

def ch17_use_cases():
    return build_use_case_fig(
        "ch17_use_cases",
        "Figure 17-1. Actors and Use Cases of the Adaptive Video Streaming Platform.",
        "System Boundary: Adaptive Video Streaming Platform",
        "Chunked transcoding DAG · HLS/DASH manifests · Multi-tier CDN playback",
        actors=[
            ("Content Creator", "Studio & user uploads", "blue", "person"),
            ("Video Viewer", "Smart TV, mobile & web", "teal", "laptop"),
            ("Platform Ops", "DRM & CDN traffic SRE", "purple", "engineering"),
        ],
        cases=[
            ("Upload Master Video", "POST /v1/videos -> resumable chunks", "blue", "save"),
            ("Transcode ABR Ladder", "Split GOP -> Encode 240p..4K -> Package", "amber", "developer_board"),
            ("Fetch Playback Manifest", "GET /v1/videos/{id}/manifest.m3u8", "teal", "description"),
            ("Stream Video Segments", "GET /{id}/{bitrate}/seg-{n}.m4s", "green", "play_arrow"),
            ("Manage DRM & Shielding", "Key rotation · CDN origin shield", "purple", "lock"),
        ],
        links=[
            (0, [0, 1], "blue"),
            (1, [2, 3], "teal"),
            (2, [1, 4], "purple"),
        ],
        notes=[
            ("Decoupling offline transcoding from edge segment delivery lets millions of concurrent viewers stream immutable files without touching compute pools.", "noteb"),
            "Every bitrate rung shares identical keyframe boundaries so players switch quality seamlessly between consecutive segments.",
        ],
    )


def ch17_architecture():
    f = Fig(
        "ch17_architecture",
        "Figure 17-2. Ingest Control Plane, Distributed Transcode Pipeline, and Multi-Tier CDN Playback.",
        598,
    )

    # Top: Control Plane
    f.zone(
        MARGIN, 0, INNER, 146, "purple",
        "Control Plane (Ingest API, Transcode DAG Scheduler & Manifest Service)",
        "Resumable upload coordination · Job orchestration · HLS/DASH playlists & DRM keys",
        icon="settings_suggest", dashed=True,
    )
    c_ing = f.node(
        MARGIN + 18, 60, 256, 70, "purple",
        [("Upload & Ingest API", "name"), ("Auth · Chunk verification", "sub")],
        icon="save", kind="card", icon_size=26,
    )
    c_dag = f.node(
        MARGIN + 298, 60, 260, 70, "amber",
        [("DAG Job Scheduler", "name"), ("Split, encode, package", "sub")],
        icon="tune", kind="card", icon_size=26,
    )
    c_man = f.node(
        MARGIN + 582, 60, 256, 70, "teal",
        [("Manifest & DRM Svc", "name"), ("Playlists & license keys", "sub")],
        icon="lock", kind="card", icon_size=26,
    )

    # Middle: Offline Media Plane (concise header leaves x >= 450 completely clear)
    f.zone(
        MARGIN, 178, INNER, 148, "amber",
        "Offline Media Plane (Transcode & Origin)",
        "Parallel GOP encoding -> 4 s ABR segments",
        icon="developer_board",
    )
    raw = f.node(
        MARGIN + 18, 240, 238, 70, "gray",
        [("Raw Object Store", "name"), ("Master mezzanine file", "sub")],
        icon="folder", kind="card", icon_size=26,
    )
    enc = f.node(
        MARGIN + 306, 240, 244, 70, "amber",
        [("Transcode Workers", "name"), ("Parallel H.264 / AV1", "sub")],
        icon="widgets", kind="card", icon_size=26,
    )
    orig = f.node(
        MARGIN + 600, 240, 238, 70, "blue",
        [("Packaged Origin Store", "name"), ("Immutable 4 s segments", "sub")],
        icon="inventory_2", kind="card", icon_size=26,
    )

    # Bottom: Playback Data Plane (concise header leaves x >= 560 clear for Origin -> Shield)
    f.zone(
        MARGIN, 358, INNER, 172, "blue",
        "Playback Data Plane (CDN Shield, Edge & ABR)",
        "HTTP/3 immutable segment delivery from nearest PoP",
        icon="play_arrow",
    )
    player = f.node(
        MARGIN + 18, 422, 238, 92, "blue",
        [("TV / Mobile Players", "name"), ("HLS / DASH ABR buffer", "sub"), ("Dynamic bitrate choice", "small")],
        icon="laptop", kind="card", icon_size=26,
    )
    edge = f.node(
        MARGIN + 306, 422, 244, 92, "green",
        [("Global CDN Edge PoPs", "name"), ("95%+ hit · < 20 ms RTT", "sub"), ("Immutable cache TTL", "small")],
        icon="bolt", kind="card", icon_size=26,
    )
    shield = f.node(
        MARGIN + 600, 422, 238, 92, "teal",
        [("Origin Shield Cache", "name"), ("Collapses edge misses", "sub"), ("Protects origin egress", "small")],
        icon="shield", kind="card", icon_size=26,
    )

    # Middle pipeline wires (Left -> Right; 50px gaps, equal shaft clearance)
    f.wire([raw.right(0), enc.left(0)], tone="amber", width=1.9)
    step_badge(f, (raw.r + enc.x - 9) / 2, raw.cy, "1", "amber", ring="c-amber")

    f.wire([enc.right(0), orig.left(0)], tone="blue", width=1.9)
    step_badge(f, (enc.r + orig.x - 9) / 2, enc.cy, "2", "blue", ring="c-amber")

    # Serpentine drop: Origin -> Origin Shield (112px downward arrow; badge cleanly inside Playback zone at y=390)
    f.wire([orig.bottom(0), (orig.cx, shield.y)], tone="teal", width=2.0)
    f.label(orig.cx - 58, 394, "Cache fill", tone="teal", cls="small", back_cls="c-blue")
    step_badge(f, orig.cx, 390, "3", "teal", ring="c-blue")

    f.wire([shield.left(0), edge.right(0)], tone="green", width=2.0)
    step_badge(f, (edge.r + shield.x + 9) / 2, edge.cy, "4", "green", ring="c-blue")

    f.wire([edge.left(0), player.right(0)], tone="blue", width=2.0)
    step_badge(f, (player.r + edge.x + 9) / 2, player.cy, "5", "blue", ring="c-blue")

    # Control plane dashed wires — ZERO header or wire crossings!
    # 1. Write master: left outer gutter x=16 -> inter-zone gap y=342 -> raw.bottom(0)
    f.wire([c_ing.left(0), (16, c_ing.cy), (16, 342), (raw.cx, 342), raw.bottom(0)], tone="purple", dash=True, width=1.6)
    f.label(250, 345, "Write master (left)", tone="purple", cls="small")

    # 2. Dispatch GOPs: straight down at x=460 (well right of Offline Media Plane header)
    f.wire([c_dag.bottom(0), (c_dag.cx, enc.y)], tone="amber", dash=True, width=1.6)
    f.label(c_dag.cx + 58, 162, "Dispatch GOPs", tone="amber", cls="small")

    # 3. Manifest & DRM keys: right outer gutter x=904 -> bottom gutter y=546 -> player.bottom(0)
    f.wire([c_man.right(0), (904, c_man.cy), (904, 546), (player.cx, 546), player.bottom(0)], tone="teal", dash=True, width=1.6)
    f.label(530, 548, "Manifest & DRM keys (control fetch via outer gutter)", tone="teal", cls="small")

    path_legend(
        f, 562,
        "Solid: Media & playback path (1-2 Transcode -> 3 Shield -> 4 Edge -> 5 Player)",
        "Dashed: Ingest, GOP dispatch & DRM manifest",
    )

    return f.save([
        ("Origin shielding collapses concurrent cache misses from hundreds of edge PoPs into a single upstream fetch per segment (3-5).", "noteb"),
        "Separating manifest and DRM authorization from static media delivery allows global CDN PoPs to cache encrypted segments indefinitely.",
    ])


def ch17_transcode_abr():
    f = Fig(
        "ch17_transcode_abr",
        "Figure 17-3. Chunked DAG Transcoding Ladder and Client-Side ABR Buffer Selection.",
        486,
    )

    # Top Zone: Chunked DAG Transcoding Ladder (symmetric 1-to-3 fan-out & 3-to-1 fan-in)
    f.zone(
        MARGIN, 0, INNER, 220, "amber",
        "Chunked Parallel Transcoding DAG (Aligned 4-Second GOP Segments)",
        "Master video is split at keyframes so independent workers encode all bitrate rungs in parallel",
        icon="developer_board",
    )
    m_in = f.node(
        MARGIN + 18, 92, 142, 86, "gray",
        [("Master File", "name"), ("60 min · 4K raw", "sub")],
        icon="folder", layout="center", kind="card", icon_size=24,
    )
    splitter = f.node(
        MARGIN + 208, 92, 142, 86, "amber",
        [("GOP Splitter", "name"), ("4 s keyframes", "sub")],
        icon="call_split", layout="center", kind="card", icon_size=24,
    )

    # 3 Parallel Bitrate Rungs (cy = 83, 135, 187 — symmetric around 135)
    rx = MARGIN + 442
    rw = 160
    rungs = [
        ("1080p · 5.0 Mbps", "High motion HD", "green", 62),
        ("720p · 2.5 Mbps", "Balanced mobile", "teal", 114),
        ("480p · 1.0 Mbps", "Constrained link", "amber", 166),
    ]
    rboxes = []
    for lbl, sub, tone, ry in rungs:
        rb = f.node(rx, ry, rw, 42, tone, [(lbl, "monob"), (sub, "small")], layout="center", kind="card", r=8)
        rboxes.append(rb)

    pkg = f.node(
        MARGIN + 694, 92, 144, 86, "blue",
        [("CMAF Packager", "name"), ("HLS + DASH index", "sub")],
        icon="inventory_2", layout="center", kind="card", icon_size=24,
    )

    # Step 1: Master File -> GOP Splitter (48px gap)
    f.wire([m_in.right(0), splitter.left(0)], tone="amber", width=1.9)
    step_badge(f, (m_in.r + splitter.x - 9) / 2, m_in.cy, "1", "amber", ring="c-amber")

    # Step 2: Symmetric 1-to-3 Fan-Out (x_mid_1 = (382 + 474) / 2 = 428; trunk=46px, branches=46px)
    x_mid_1 = (splitter.r + rx) / 2
    f.wire([splitter.right(0), (x_mid_1, splitter.cy)], tone="amber", head=False, width=1.9)
    f.rule(x_mid_1, rboxes[0].cy, x_mid_1, rboxes[2].cy, tone="amber", width=1.9)
    for rb in rboxes:
        f.wire([(x_mid_1, rb.cy), rb.left(0)], tone="amber", width=1.9)
    step_badge(f, (splitter.r + x_mid_1) / 2, splitter.cy, "2", "amber", ring="c-amber")

    # Step 3: Symmetric 3-to-1 Fan-In (x_mid_2 = (634 + 726) / 2 = 680; feeds=46px, trunk=46px)
    x_mid_2 = (rboxes[0].r + pkg.x) / 2
    for rb in rboxes:
        f.wire([rb.right(0), (x_mid_2, rb.cy)], tone="blue", head=False, width=1.9)
    f.rule(x_mid_2, rboxes[0].cy, x_mid_2, rboxes[2].cy, tone="blue", width=1.9)
    f.wire([(x_mid_2, pkg.cy), pkg.left(0)], tone="blue", width=1.9)
    step_badge(f, (x_mid_2 + pkg.x - 9) / 2, pkg.cy, "3", "blue", ring="c-amber")

    # Bottom Zone: Client-Side ABR Selection Timeline (50px badged gaps)
    f.zone(
        MARGIN, 244, INNER, 232, "blue",
        "Client-Side Adaptive Bitrate (ABR) Selection Across Bandwidth Fluctuations",
        "Player monitors throughput and buffer occupancy to switch rungs at segment boundaries without stalling",
        icon="play_arrow",
    )
    segs = [
        ("Seg 1-2 · Healthy", "BW: 8.0 Mbps", "Pick 1080p (5M)", "Buffer: 16 s", "green"),
        ("Seg 3-4 · Dip", "BW: 2.2 Mbps", "Drop 720p (2.5M)", "Buffer: 10 s", "amber"),
        ("Seg 5-6 · Drop", "BW: 1.1 Mbps", "Drop 480p (1M)", "Buffer: 6 s", "red"),
        ("Seg 7-8 · Recover", "BW: 4.5 Mbps", "Step 720p (2.5M)", "Buffer: 12 s", "teal"),
    ]
    sw = 168
    sgap = 50
    abr_tones = ["amber", "red", "teal"]
    for i, (s_hdr, s_bw, s_pick, s_buf, tone) in enumerate(segs):
        sx = MARGIN + 17 + i * (sw + sgap)
        box = f.node(
            sx, 310, sw, 144, tone,
            [(s_hdr, "name"), (s_bw, "small"), (s_pick, "monob"), (s_buf, "badge")],
            layout="center", kind="card" if tone != "red" else "mid", r=10,
            text_tone=tone if tone == "red" else None,
        )
        if i < 3:
            a, b = box.r, sx + sw + sgap
            f.wire([box.right(0), (b, box.cy)], tone=abr_tones[i], width=1.9)
            step_badge(f, (a + b - 9) / 2, box.cy, str(i + 4), abr_tones[i], ring="c-blue")

    return f.save([
        ("Splitting uploads at Group-of-Pictures (GOP) boundaries reduces end-to-end transcoding latency from hours to a few minutes.", "noteb"),
        "Buffer-aware ABR algorithms step down quality aggressively when buffer occupancy shrinks and step up conservatively to avoid oscillation and rebuffering.",
    ])


# =============================================================================
# CHAPTER 18: REAL-TIME CHAT
# =============================================================================

def ch18_use_cases():
    return build_use_case_fig(
        "ch18_use_cases",
        "Figure 18-1. Actors and Use Cases of the Real-Time Messaging System.",
        "System Boundary: Real-Time Messaging System",
        "Stateful WebSocket gateways · Per-conversation ordering · Offline sync",
        actors=[
            ("Chat Member", "Mobile & desktop clients", "blue", "person"),
            ("Push Relay", "APNs & FCM gateways", "amber", "notifications_active"),
            ("Platform Ops", "Gateway drain & scaling", "purple", "engineering"),
        ],
        cases=[
            ("Maintain Live Session", "WSS /v1/ws + heartbeat presence", "teal", "lan"),
            ("Send Message (Idempotent)", "POST /v1/conversations/{id}/messages + client_id", "blue", "edit_note"),
            ("Sync Missed Messages", "GET /v1/conversations/{id}/messages?after=seq", "green", "loop"),
            ("Delivery & Read Receipts", "ACK delivered / read watermarks", "purple", "handshake"),
            ("Offline Push Alert", "Wake idle device via APNs / FCM", "amber", "notifications_active"),
        ],
        links=[
            (0, [0, 1, 2, 3], "blue"),
            (1, [4], "amber"),
            (2, [0], "purple"),
        ],
        notes=[
            ("Chat combines persistent stateful WebSocket gateways for low-latency push with durable sequence-numbered logs for reliable offline catch-up.", "noteb"),
            "Every message carries a client-generated idempotency identifier so network retries never produce duplicate messages in a conversation.",
        ],
    )


def ch18_architecture():
    f = Fig(
        "ch18_architecture",
        "Figure 18-2. Presence Directory, Stateful WebSocket Gateways, and Partitioned Message Store.",
        584,
    )

    # Top: Control Plane
    f.zone(
        MARGIN, 0, INNER, 146, "purple",
        "Control Plane (Session Directory, Presence & Offline Push Relay)",
        "Maps active user sessions to gateways · TTL heartbeats · APNs/FCM wakeups",
        icon="settings_suggest", dashed=True,
    )
    c_pres = f.node(
        MARGIN + 18, 60, 256, 70, "teal",
        [("Presence Heartbeat Svc", "name"), ("30 s TTL online state", "sub")],
        icon="timer", kind="card", icon_size=26,
    )
    c_dir = f.node(
        MARGIN + 298, 60, 260, 70, "purple",
        [("Session Directory (Redis)", "name"), ("user_id -> gateway_id", "sub")],
        icon="dns", kind="card", icon_size=26,
    )
    c_push = f.node(
        MARGIN + 582, 60, 256, 70, "amber",
        [("Offline Push Relay", "name"), ("APNs / FCM dispatch", "sub")],
        icon="notifications_active", kind="card", icon_size=26,
    )

    # Bottom: Data Plane (concise header leaves x >= 390 completely clear for symmetric control wires)
    f.zone(
        MARGIN, 178, INNER, 356, "blue",
        "Data Plane (WSS Gateways & Store)",
        "Durable commit before push · 100k/host",
        icon="layers",
    )

    # Row 1: Sender -> GW A -> Chat Router -> GW B -> Recipient
    gw_a = f.node(
        MARGIN + 18, 240, 232, 92, "teal",
        [("WebSocket Gateway A", "name"), ("Sender live WSS socket", "sub"), ("100k conns / host", "small")],
        icon="lan", kind="card", icon_size=26,
    )
    router = f.node(
        MARGIN + 298, 240, 260, 92, "blue",
        [("Chat Router & Sequencer", "name"), ("Dedup client_id · Assign seq", "sub"), ("Fan-out to recipient GWs", "small")],
        icon="swap_horiz", kind="card", icon_size=26,
    )
    gw_b = f.node(
        MARGIN + 606, 240, 232, 92, "teal",
        [("WebSocket Gateway B", "name"), ("Recipient live WSS socket", "sub"), ("Pushes frame seq=42", "small")],
        icon="lan", kind="card", icon_size=26,
    )

    # Row 2: Clients on sides, Partitioned Message Store in center
    sender = f.node(
        MARGIN + 18, 412, 232, 96, "blue",
        [("Sender (Mobile / Web)", "name"), ("WSS send + retry UUID", "sub")],
        icon="laptop", kind="card", icon_size=24,
    )
    mstore = f.node(
        MARGIN + 286, 412, 284, 96, "amber",
        [("Partitioned Message Store", "name"), ("Sharded by conv_id · seq", "sub"), ("Multi-AZ WAL + cursor", "small")],
        icon="save", kind="card", icon_size=26,
    )
    recip = f.node(
        MARGIN + 606, 412, 232, 96, "green",
        [("Recipient Devices", "name"), ("Mobile/Web · Live push", "sub")],
        icon="laptop", kind="card", icon_size=24,
    )

    # Data plane wires (equal shaft clearance on both sides of every badge)
    f.wire([sender.top(0), gw_a.bottom(0)], tone="blue", width=2.0)
    f.label(sender.cx + 56, (gw_a.b + sender.y + 9) / 2 + 4, "Send frame", tone="blue", cls="small", back_cls="c-blue")
    step_badge(f, sender.cx, (gw_a.b + sender.y + 9) / 2, "1", "blue", ring="c-blue")

    f.wire([gw_a.right(0), router.left(0)], tone="blue", width=2.0)
    step_badge(f, (gw_a.r + router.x - 9) / 2, gw_a.cy, "2", "blue", ring="c-blue")

    # Router <-> Message Store (durable write before push; bidirectional -> (a+b)/2)
    f.wire([router.bottom(0), mstore.top(0)], tone="amber", width=2.0, tail=True)
    f.label(router.cx + 70, (router.b + mstore.y) / 2 + 4, "Persist seq=42", tone="amber", cls="mono", back_cls="c-blue")
    step_badge(f, router.cx, (router.b + mstore.y) / 2, "3", "amber", ring="c-blue")

    f.wire([router.right(0), gw_b.left(0)], tone="teal", width=2.0)
    step_badge(f, (router.r + gw_b.x - 9) / 2, router.cy, "4", "teal", ring="c-blue")

    f.wire([gw_b.bottom(0), recip.top(0)], tone="green", width=2.0)
    f.label(gw_b.cx - 52, (gw_b.b + recip.y - 9) / 2 + 4, "Live push", tone="green", cls="small", back_cls="c-blue")
    step_badge(f, gw_b.cx, (gw_b.b + recip.y - 9) / 2, "5", "green", ring="c-blue")

    # Control plane dashed wires — ZERO header or wire crossings!
    # 1. Heartbeats: left outer gutter x=16 -> inter-zone corridor y=162 -> c_pres.bottom(0)
    f.wire([gw_a.left(0), (16, gw_a.cy), (16, 162), (c_pres.cx, 162), c_pres.bottom(0)], tone="teal", dash=True, width=1.6)
    f.label(96, 162, "Heartbeats", tone="teal", cls="small")

    # 2. Session Directory lookup & 3. Offline wakeup: symmetric (-44 / +44) on router.top
    f.wire([router.top(-44), (router.cx - 44, 162), (c_dir.cx, 162), c_dir.bottom(0)], tone="purple", dash=True, width=1.6, tail=True)
    f.label(354, 162, "Lookup GW", tone="purple", cls="small")

    f.wire([router.top(44), (router.cx + 44, 162), (c_push.cx, 162), c_push.bottom(0)], tone="amber", dash=True, width=1.6)
    f.label(623, 162, "Offline wakeup", tone="amber", cls="small")

    path_legend(
        f, 548,
        "Solid: Sync messaging path (1 Send -> 2 Route -> 3 Persist -> 4-5 Push)",
        "Dashed: Heartbeats, GW lookup & offline push",
    )

    return f.save([
        ("Persisting the message and assigning its per-conversation sequence number (3) before pushing (4-5) ensures recipients never observe unrecoverable frames.", "noteb"),
        "Stateless routers look up recipient gateway bindings in Redis, forwarding live frames to online sockets or dispatching APNs/FCM wakeups for offline devices.",
    ])


def ch18_delivery_flow():
    f = Fig(
        "ch18_delivery_flow",
        "Figure 18-3. End-to-End Message Sequencing, Online Push, and Offline Cursor Catch-Up.",
        486,
    )

    # Top Zone: Sequencing & Symmetric 1-to-2 Presence Split (Online vs. Offline)
    f.zone(
        MARGIN, 0, INNER, 256, "blue",
        "Online Sequencing & Presence-Based Delivery Split (Live Push vs. Offline Wakeup)",
        "Each conversation maintains a monotonic sequence counter; retries deduplicate on client_id",
        icon="bolt",
    )
    s1 = f.node(
        MARGIN + 18, 108, 142, 86, "blue",
        [("Client Send", "name"), ("client_id=u9a1", "mono"), ("Retries reuse ID", "small")],
        icon="edit_note", layout="center", kind="card", icon_size=24,
    )
    s2 = f.node(
        MARGIN + 208, 108, 150, 86, "amber",
        [("Dedup & Seq", "name"), ("Assign seq=42", "mono"), ("Durable WAL", "small")],
        icon="lock", layout="center", kind="card", icon_size=24,
    )

    # Online branch (cy = 98)
    on1 = f.node(
        MARGIN + 450, 60, 166, 76, "teal",
        [("GW B Live Push", "name"), ("WSS frame seq=42", "mono")],
        icon="lan", layout="center", kind="card", icon_size=22,
    )
    on2 = f.node(
        MARGIN + 666, 60, 172, 76, "green",
        [("Delivery ACK", "name"), ("Watermark -> 42", "mono")],
        icon="handshake", layout="center", kind="card", icon_size=22,
    )

    # Offline branch (cy = 204)
    off1 = f.node(
        MARGIN + 450, 166, 166, 76, "amber",
        [("APNs / FCM Alert", "name"), ("Wake idle device", "small")],
        icon="notifications_active", layout="center", kind="card", icon_size=22,
    )
    off2 = f.node(
        MARGIN + 666, 166, 172, 76, "purple",
        [("Pending Catch-Up", "name"), ("Client cursor=40", "mono")],
        icon="schedule", layout="center", kind="card", icon_size=22,
    )

    # Step 1: Client Send -> Dedup & Seq (48px gap)
    f.wire([s1.right(0), s2.left(0)], tone="blue", width=2.0)
    step_badge(f, (s1.r + s2.x - 9) / 2, s1.cy, "1", "blue", ring="c-blue")

    # Step 2: Symmetric 1-to-2 Split (x_mid = (390 + 482) / 2 = 436; trunk=46px, branches=46px)
    x_mid = (s2.r + on1.x) / 2
    f.wire([s2.right(0), (x_mid, s2.cy)], tone="amber", head=False, width=2.0)
    f.rule(x_mid, on1.cy, x_mid, off1.cy, tone="amber", width=2.0)
    f.wire([(x_mid, on1.cy), on1.left(0)], tone="teal", width=2.0)
    f.wire([(x_mid, off1.cy), off1.left(0)], tone="amber", width=2.0)
    f.label((x_mid + on1.x) / 2, on1.cy - 14, "Online", tone="teal", cls="badge", back_cls="c-blue")
    f.label((x_mid + off1.x) / 2, off1.cy + 20, "Offline", tone="amber", cls="badge", back_cls="c-blue")
    step_badge(f, (s2.r + x_mid) / 2, s2.cy, "2", "amber", ring="c-blue")

    # Step 3 & Step 4: Branch horizontal arrows (50px gaps)
    f.wire([on1.right(0), on2.left(0)], tone="green", width=2.0)
    step_badge(f, (on1.r + on2.x - 9) / 2, on1.cy, "3", "green", ring="c-blue")

    f.wire([off1.right(0), off2.left(0)], tone="purple", width=2.0)
    step_badge(f, (off1.r + off2.x - 9) / 2, off1.cy, "4", "purple", ring="c-blue")

    # Connector from Offline Pending Catch-Up -> Offline Recovery Zone
    f.wire([(off2.cx, 256), (off2.cx, 294)], tone="purple", dash=True, width=1.9)
    f.label(off2.cx - 64, 279, "On reconnect", tone="purple", cls="small")

    # Bottom Zone: Gap Detection and Offline Cursor Catch-Up (52px badged gaps)
    f.zone(
        MARGIN, 294, INNER, 182, "purple",
        "Offline Recovery: Sequence Gap Detection and Multi-Device Cursor Catch-Up",
        "Reconnecting devices pull missed ranges deterministically by sequence number rather than wall-clock time",
        icon="loop",
    )
    o1 = f.node(
        MARGIN + 18, 356, 238, 102, "red",
        [("Disconnect Window", "name"), ("Local cursor: seq=40", "mono"), ("Misses seq 41, 42, 43", "small")],
        icon="warning", layout="center", kind="mid", icon_size=24,
    )
    o2 = f.node(
        MARGIN + 308, 356, 240, 102, "purple",
        [("Cursor Sync Query", "name"), ("GET /v1/conversations/{id}", "mono"), ("Shard range scan (100)", "small")],
        icon="table_rows", layout="center", kind="card", icon_size=24,
    )
    o3 = f.node(
        MARGIN + 600, 356, 238, 102, "green",
        [("Ordered Reconcile", "name"), ("Apply seq 41, 42, 43", "mono"), ("Cursor -> 43 · Live WSS", "small")],
        icon="play_arrow", layout="center", kind="card", icon_size=24,
    )
    f.wire([o1.right(0), o2.left(0)], tone="purple", width=2.0)
    step_badge(f, (o1.r + o2.x - 9) / 2, o1.cy, "5", "purple", ring="c-purple")

    f.wire([o2.right(0), o3.left(0)], tone="green", width=2.0)
    step_badge(f, (o2.r + o3.x - 9) / 2, o2.cy, "6", "green", ring="c-purple")

    return f.save([
        ("Per-conversation monotonic sequence numbers allow any client to detect dropped or out-of-order frames immediately upon seeing a gap.", "noteb"),
        "Using cursor-based catch-up queries instead of server-side per-device queues keeps multi-device histories consistent across phones, tablets, and desktops.",
    ])


ALL = [
    ch14_use_cases,
    ch14_architecture,
    ch14_redirect_cache,
    ch15_use_cases,
    ch15_architecture,
    ch15_hybrid_fanout,
    ch16_use_cases,
    ch16_architecture,
    ch16_erasure_coding,
    ch17_use_cases,
    ch17_architecture,
    ch17_transcode_abr,
    ch18_use_cases,
    ch18_architecture,
    ch18_delivery_flow,
]


def main():
    total_problems = 0
    for fn in ALL:
        problems = fn()
        total_problems += problems
        print(f"generated {fn.__name__} (light + dark) -> {problems} fit warnings")
    print(f"Done: {len(ALL)} figures ({len(ALL) * 2} SVGs), total fit warnings: {total_problems}")
    if total_problems:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
