#!/usr/bin/env python3
"""Generate 15 spacious Material Design 3 light+dark SVG figures for Part III (Chapters 14-18).

Every figure prioritizes generous whitespace, concise crisp labels, zero text
overflow in Chrome/Safari, and clear separation of control and data planes.
"""
from figkit_m3 import Fig, WIDTH, MARGIN, build_use_case_fig

INNER = WIDTH - 2 * MARGIN  # 856px usable width


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
            ("Quarantine Abusive Link", "POST /v1/admin/block/{code}", "red", "block"),
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
        536,
    )

    # Top: Control Plane
    f.zone(
        MARGIN, 0, INNER, 146, "purple",
        "Control Plane (Abuse Policy, Click Analytics & ID Range Allocation)",
        "Blocklist propagation · Off-path click telemetry · Disjoint counter lease blocks",
        icon="settings_suggest", dashed=True,
    )
    c_abuse = f.node(
        MARGIN + 18, 60, 256, 70, "red",
        [("Abuse & Blocklist Push", "name"), ("Phishing & spam filters", "sub")],
        icon="shield", kind="card", icon_size=26,
    )
    c_click = f.node(
        MARGIN + 298, 60, 260, 70, "teal",
        [("Click Stream & OLAP", "name"), ("Kafka -> ClickHouse", "sub")],
        icon="table_rows", kind="card", icon_size=26,
    )
    c_range = f.node(
        MARGIN + 582, 60, 256, 70, "purple",
        [("Range Allocator (etcd)", "name"), ("Disjoint 100k ID blocks", "sub")],
        icon="dns", kind="card", icon_size=26,
    )

    # Bottom: Data Plane
    f.zone(
        MARGIN, 178, INNER, 348, "blue",
        "Data Plane (Global Edge Redirect Tier & Sharded Mapping Store)",
        "Edge L1 cache -> Stateless redirect tier -> Regional Redis + Bloom filter -> Sharded DB",
        icon="layers",
    )

    # Row 1 inside Data Plane (y=240, h=86)
    vis = f.node(
        MARGIN + 18, 240, 156, 86, "blue",
        [("Visitors", "name"), ("GET /{code}", "mono")],
        icon="laptop", kind="card", icon_size=24,
    )
    cdn = f.node(
        MARGIN + 196, 240, 192, 86, "teal",
        [("CDN Edge PoP", "name"), ("L1 cache · 302", "sub")],
        icon="bolt", kind="card", icon_size=24,
    )
    rds = f.node(
        MARGIN + 410, 240, 204, 86, "blue",
        [("Redirect Service", "name"), ("Stateless lookup", "sub")],
        icon="swap_horiz", kind="card", icon_size=24,
    )
    wrt = f.node(
        MARGIN + 636, 240, 202, 86, "amber",
        [("Write API", "name"), ("Base62 encoder", "sub")],
        icon="edit_note", kind="card", icon_size=24,
    )

    # Row 2 inside Data Plane (y=396, h=106)
    rcache = f.node(
        MARGIN + 18, 396, 384, 106, "teal",
        [("Regional Redis Cluster", "name"), ("Hot code -> URL mappings (LRU)", "sub"), ("In-memory Bloom filter for 404 shield", "small")],
        icon="memory", kind="card", icon_size=28,
    )
    db = f.node(
        MARGIN + 444, 396, 394, 106, "blue",
        [("Sharded Mapping Store (3 AZs)", "name"), ("Hash-partitioned by short code", "sub"), ("Primary writes · Read replicas", "small")],
        icon="save", kind="card", icon_size=28,
    )

    # Data plane wires
    f.wire([vis.right(0), cdn.left(0)], tone="blue", width=2.0)
    f.wire([cdn.right(0), rds.left(0)], tone="teal", width=2.0)
    f.label(431, 232, "Miss", tone="teal", cls="badge", back_cls="c-blue")

    # Redirect Service -> Redis and DB
    f.wire([rds.bottom(-36), (rds.cx - 36, 358), (rcache.cx, 358), rcache.top(0)], tone="teal", width=1.9, tail=True)
    f.label(358, 349, "L2 lookup + Bloom", tone="teal", cls="small", back_cls="c-blue")

    f.wire([rds.bottom(36), (rds.cx + 36, 358), (db.cx - 60, 358), db.top(-60)], tone="blue", width=1.9)
    f.label(566, 349, "Cold miss", tone="blue", cls="small", back_cls="c-blue")

    # Write API -> DB
    f.wire([wrt.bottom(0), (wrt.cx, 396)], tone="amber", width=2.0)
    f.label(wrt.cx, 360, "PUT mapping", tone="amber", cls="small", back_cls="c-blue")

    # Control plane dashed wires
    f.wire([c_abuse.bottom(40), (c_abuse.cx + 40, 162), (cdn.cx, 162), cdn.top(0)], tone="red", dash=True, width=1.6)
    f.label(212, 164, "Blocklist sync", tone="red", cls="small")

    f.wire([rds.top(0), (rds.cx, 162), (c_click.cx, 162), c_click.bottom(0)], tone="teal", dash=True, width=1.6)
    f.label(540, 164, "Async clicks", tone="teal", cls="small")

    f.wire([c_range.bottom(0), (c_range.cx, 162), (wrt.cx, 162), wrt.top(0)], tone="purple", dash=True, width=1.6)
    f.label(742, 164, "ID range lease", tone="purple", cls="small")

    return f.save([
        ("Range leasing eliminates cross-host write coordination while keeping short codes collision-free across regions.", "noteb"),
        "Write servers pre-allocate disjoint 100,000-ID ranges from etcd and encode each value with a Feistel permutation before Base62 formatting to prevent sequential enumeration.",
    ])


def ch14_redirect_cache():
    f = Fig(
        "ch14_redirect_cache",
        "Figure 14-3. Multi-Tier Redirect Cache Hierarchy and Bloom-Filter Negative Lookup Defense.",
        468,
    )

    # Top Zone: Multi-tier read cascade
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
    tw = 186
    tgap = 24
    tboxes = []
    for i, (t_hdr, t_stat, t_sub, tone, ic) in enumerate(tiers):
        tx = MARGIN + 20 + i * (tw + tgap)
        box = f.node(
            tx, 66, tw, 108, tone,
            [(t_hdr, "name"), (t_stat, "monob"), (t_sub, "small")],
            icon=ic, layout="center", kind="card", icon_size=26,
        )
        tboxes.append(box)
        if i < 3:
            f.wire([box.right(0), (tx + tw + tgap, box.cy)], tone="wire", width=1.8)
            lbl = "Miss" if i < 2 else "Maybe"
            f.label(tx + tw + tgap / 2, box.cy - 14, lbl, tone="gray", cls="badge", back_cls="c-blue")

    # Bottom Left: Bloom Filter Defense
    lw = 416
    f.zone(
        MARGIN, 218, lw, 240, "amber",
        "Bloom-Filter Negative Lookup Defense",
        "Stops random code enumeration from exhausting DB IOPS",
        icon="shield",
    )
    bf1 = f.node(
        MARGIN + 18, 282, 174, 72, "red",
        [("Unknown Code", "name"), ("GET /x9Z2q1", "mono")],
        layout="center", kind="mid", r=10,
    )
    bf2 = f.node(
        MARGIN + 224, 282, 174, 72, "amber",
        [("k=7 Hash Bits", "name"), ("Bit[h_i] == 0?", "mono")],
        layout="center", kind="card", r=10,
    )
    f.wire([bf1.right(0), bf2.left(0)], tone="amber", width=1.8)

    bf3 = f.node(
        MARGIN + 18, 376, 178, 64, "green",
        [("Any Bit = 0", "monob"), ("Instant 404 (0 DB reads)", "small")],
        layout="center", kind="card", r=10,
    )
    bf4 = f.node(
        MARGIN + 216, 376, 182, 64, "blue",
        [("All Bits = 1", "monob"), ("Query DB (~1% FP rate)", "small")],
        layout="center", kind="card", r=10,
    )
    f.wire([bf2.bottom(-30), (bf2.cx - 30, 365), (bf3.cx, 365), bf3.top(0)], tone="green", width=1.6)
    f.wire([bf2.bottom(30), (bf2.cx + 30, 365), (bf4.cx, 365), bf4.top(0)], tone="blue", width=1.6)

    # Bottom Right: 301 vs 302 Trade-Off
    rx = MARGIN + lw + 24
    rw = INNER - lw - 24
    f.zone(
        rx, 218, rw, 240, "purple",
        "HTTP 301 vs. 302 Redirect Trade-Off",
        "Balancing origin load against telemetry and revocation",
        icon="tune",
    )
    f.node(
        rx + 18, 282, rw - 36, 72, "gray",
        [("301 Moved Permanently", "name"), ("Browser caches target · Bypasses click count", "sub")],
        icon="schedule", kind="card", icon_size=24,
    )
    f.node(
        rx + 18, 370, rw - 36, 72, "green",
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
            ("Follow or Unfollow", "PUT / DELETE /v1/graph/{u}/follows/{v}", "amber", "handshake"),
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
        540,
    )

    # Top: Control Plane
    f.zone(
        MARGIN, 0, INNER, 146, "purple",
        "Control Plane (Ranking Models, Fan-Out Thresholds & Social Graph)",
        "Feature weights · Celebrity fan-out cutoff · Sharded follower edge lists",
        icon="settings_suggest", dashed=True,
    )
    c_ml = f.node(
        MARGIN + 18, 60, 256, 70, "teal",
        [("Ranking Model Registry", "name"), ("Weights & safety rules", "sub")],
        icon="developer_board", kind="card", icon_size=26,
    )
    c_pol = f.node(
        MARGIN + 298, 60, 260, 70, "amber",
        [("Fan-Out Policy Config", "name"), ("Celebrity cutoff > 100k", "sub")],
        icon="tune", kind="card", icon_size=26,
    )
    c_graph = f.node(
        MARGIN + 582, 60, 256, 70, "purple",
        [("Social Graph Service", "name"), ("Sharded follower lists", "sub")],
        icon="lan", kind="card", icon_size=26,
    )

    # Bottom: Data Plane
    f.zone(
        MARGIN, 178, INNER, 352, "blue",
        "Data Plane (Asynchronous Publish Fan-Out and Low-Latency Read Assembly)",
        "Top lane: durable publish and fan-out   |   Bottom lane: serpentine read merge and ranking",
        icon="layers",
    )

    # Write Lane (Left -> Right, y=242, h=84)
    pub = f.node(
        MARGIN + 18, 242, 182, 84, "blue",
        [("Post Service", "name"), ("POST /v1/posts", "mono")],
        icon="edit_note", kind="card", icon_size=24,
    )
    pstore = f.node(
        MARGIN + 224, 242, 182, 84, "blue",
        [("Post Store (DB)", "name"), ("Durable content", "sub")],
        icon="save", kind="card", icon_size=24,
    )
    mq = f.node(
        MARGIN + 430, 242, 182, 84, "amber",
        [("Kafka Topic", "name"), ("Post-created log", "sub")],
        icon="swap_horiz", kind="card", icon_size=24,
    )
    fw = f.node(
        MARGIN + 636, 242, 202, 84, "teal",
        [("Fan-Out Workers", "name"), ("Push normal IDs", "sub")],
        icon="bolt", kind="card", icon_size=24,
    )

    # Read Lane (Right -> Left serpentine, y=402, h=106)
    rank = f.node(
        MARGIN + 18, 402, 246, 106, "green",
        [("Ranking & Filter Svc", "name"), ("Score top-K candidates", "sub"), ("Return paged JSON", "small")],
        icon="play_arrow", kind="card", icon_size=26,
    )
    agg = f.node(
        MARGIN + 300, 402, 256, 106, "blue",
        [("Feed Aggregator", "name"), ("Merge inbox + celebrity", "sub"), ("Hydrate post bodies", "small")],
        icon="view_week", kind="card", icon_size=26,
    )
    tcache = f.node(
        MARGIN + 592, 402, 246, 106, "teal",
        [("Timeline Store (Redis)", "name"), ("Per-user sorted sets", "sub"), ("Top 800 post IDs", "small")],
        icon="memory", kind="card", icon_size=26,
    )

    # Write lane wires
    f.wire([pub.right(0), pstore.left(0)], tone="blue", width=1.9)
    f.wire([pstore.right(0), mq.left(0)], tone="amber", width=1.9)
    f.wire([mq.right(0), fw.left(0)], tone="amber", width=1.9)

    # Serpentine drop: Fan-Out Workers -> Timeline Store
    f.wire([fw.bottom(0), (fw.cx, tcache.y)], tone="teal", width=2.0)
    f.label(fw.cx - 4, 366, "ZADD post_id", tone="teal", cls="mono", back_cls="c-blue")

    # Read lane wires (Right -> Left)
    f.wire([tcache.left(0), agg.right(0)], tone="teal", width=2.0)
    f.wire([agg.left(0), rank.right(0)], tone="green", width=2.0)

    # Hydrate post store -> Feed Aggregator
    f.wire([pstore.bottom(20), (pstore.cx + 20, 364), (agg.cx - 60, 364), agg.top(-60)], tone="blue", dash=True, width=1.6, tail=True)
    f.label(358, 355, "Hydrate", tone="blue", cls="small", back_cls="c-blue")

    # Control plane dashed wires
    f.wire([c_ml.bottom(-60), (c_ml.cx - 60, 162), (MARGIN + 10, 162), (MARGIN + 10, rank.cy), rank.left(0)], tone="teal", dash=True, width=1.5)
    f.label(144, 164, "Model push", tone="teal", cls="small")

    f.wire([c_pol.bottom(0), (c_pol.cx, 162), (450, 162), (450, agg.y)], tone="amber", dash=True, width=1.5)
    f.label(486, 164, "Cutoff policy", tone="amber", cls="small")

    f.wire([c_graph.bottom(0), (c_graph.cx, 162), (fw.cx, 162), fw.top(0)], tone="purple", dash=True, width=1.6, tail=True)
    f.label(756, 164, "Follower lookup", tone="purple", cls="small")

    return f.save([
        ("Timeline entries store compact 8-byte post IDs rather than full payloads so active feeds remain memory-resident in Redis.", "noteb"),
        "Fan-out workers act as the sole writers to user timelines, preventing write contention while allowing the feed aggregator to hydrate and rank candidates on read.",
    ])


def ch15_hybrid_fanout():
    f = Fig(
        "ch15_hybrid_fanout",
        "Figure 15-3. Hybrid Fan-Out: Push for Normal Accounts and Read-Time Merge for Celebrities.",
        476,
    )

    lw = 414
    rx = MARGIN + lw + 28
    rw = INNER - lw - 28

    # Left Zone: Push (Normal accounts)
    f.zone(
        MARGIN, 0, lw, 286, "teal",
        "Path A: Push Fan-Out (<= 100k Followers)",
        "Precomputes follower timelines asynchronously on publish",
        icon="bolt",
    )
    a1 = f.node(
        MARGIN + 18, 62, lw - 36, 60, "blue",
        [("Normal Author (500 followers)", "name"), ("Writes post once -> Kafka event", "sub")],
        icon="person", kind="card", icon_size=24,
    )
    a2 = f.node(
        MARGIN + 18, 144, lw - 36, 60, "teal",
        [("Fan-Out Workers Push IDs", "name"), ("500 async Redis ZADD calls", "sub")],
        icon="swap_horiz", kind="card", icon_size=24,
    )
    a3 = f.node(
        MARGIN + 18, 222, lw - 36, 48, "green",
        [("O(1) read latency · Bounded write amplification", "small")],
        layout="center", kind="mid", r=8,
    )
    f.wire([a1.bottom(0), a2.top(0)], tone="teal", width=1.8)

    # Right Zone: Pull (Celebrity accounts)
    f.zone(
        rx, 0, rw, 286, "amber",
        "Path B: Pull Merge (> 100k Followers)",
        "Skips follower push to prevent multi-million write storms",
        icon="call_split",
    )
    b1 = f.node(
        rx + 18, 62, rw - 36, 60, "amber",
        [("Celebrity Author (10M followers)", "name"), ("Appends to own outbox only", "sub")],
        icon="person", kind="card", icon_size=24,
    )
    b2 = f.node(
        rx + 18, 144, rw - 36, 60, "purple",
        [("Author Outbox Cache (1 Write)", "name"), ("Latest posts kept hot in Redis", "sub")],
        icon="memory", kind="card", icon_size=24,
    )
    b3 = f.node(
        rx + 18, 222, rw - 36, 48, "amber",
        [("Zero write storm · Merged only for active readers", "small")],
        layout="center", kind="mid", r=8,
    )
    f.wire([b1.bottom(0), b2.top(0)], tone="amber", width=1.8)

    # Bottom Zone: Read-time K-way merge
    f.zone(
        MARGIN, 316, INNER, 150, "blue",
        "Read-Time K-Way Merge & Cursor Pagination (Feed Aggregator)",
        "Combines precomputed normal inbox with followed celebrity outboxes in under 50 ms",
        icon="view_week",
    )
    m1 = f.node(
        MARGIN + 18, 378, 246, 70, "teal",
        [("1. Fetch Normal Inbox", "name"), ("Precomputed Redis ZSET", "sub")],
        icon="memory", kind="card", icon_size=24,
    )
    m2 = f.node(
        MARGIN + 304, 378, 248, 70, "blue",
        [("2. K-Way Heap Merge", "name"), ("Add celebrity outboxes", "sub")],
        icon="layers", kind="card", icon_size=24,
    )
    m3 = f.node(
        MARGIN + 592, 378, 246, 70, "green",
        [("3. Rank & Return Page", "name"), ("?cursor=last_post_id", "mono")],
        icon="play_arrow", kind="card", icon_size=24,
    )
    f.wire([m1.right(0), m2.left(0)], tone="blue", width=1.9)
    f.wire([m2.right(0), m3.left(0)], tone="green", width=1.9)

    # Vertical wires joining top zones to bottom merge zone
    f.wire([(MARGIN + 141, 286), (MARGIN + 141, 316)], tone="teal", width=2.0)
    f.wire([(rx + rw / 2, 286), (rx + rw / 2, 302), (m2.cx, 302), (m2.cx, 316)], tone="amber", width=2.0)

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
        542,
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
        MARGIN, 180, INNER, 352, "blue",
        "Data Plane (Stateless Object Gateways & Erasure-Coded Chunk Nodes)",
        "Objects split into 64 MB immutable chunks encoded as RS(6, 3) stripes across 3 AZs",
        icon="layers",
    )

    # Row 1: Ingress and Gateway
    app = f.node(
        MARGIN + 18, 240, 174, 86, "blue",
        [("Applications", "name"), ("PUT / GET blobs", "sub")],
        icon="laptop", kind="card", icon_size=24,
    )
    gw = f.node(
        MARGIN + 224, 240, 316, 86, "teal",
        [("Object API Gateway", "name"), ("Auth · 64 MB chunker · CRC32C", "sub"), ("RS(6, 3) stripe encoder/decoder", "small")],
        icon="swap_horiz", kind="card", icon_size=26,
    )
    mp = f.node(
        MARGIN + 572, 240, 266, 86, "amber",
        [("Multipart Coordinator", "name"), ("Stage parts · Atomic seal", "sub")],
        icon="inventory_2", kind="card", icon_size=24,
    )

    # Row 2: 3 Failure Domains
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
            az_xs[i], 392, az_w, 120, tone,
            [(t1, "name"), (t2, "monob"), (t3, "small")],
            icon="save", layout="center", kind="card", icon_size=26,
        )
        az_boxes.append(box)

    # Data plane wires
    f.wire([app.right(0), gw.left(0)], tone="blue", width=2.0)
    f.wire([gw.right(0), mp.left(0)], tone="amber", width=1.8, tail=True)

    # Gateway -> 3 AZs fan-out bus
    bus_y = 358
    f.wire([gw.bottom(0), (gw.cx, bus_y)], tone="teal", head=False, width=2.0)
    f.rule(az_boxes[0].cx, bus_y, az_boxes[2].cx, bus_y, tone="teal", width=2.0)
    for b in az_boxes:
        f.wire([(b.cx, bus_y), b.top(0)], tone="teal", width=2.0)
    f.label(gw.cx + 128, bus_y - 10, "Parallel shard write / read", tone="teal", cls="small", back_cls="c-blue")

    # Control plane dashed wires
    f.wire([c_meta.bottom(40), (c_meta.cx + 40, 164), (gw.cx - 80, 164), gw.top(-80)], tone="purple", dash=True, width=1.6, tail=True)
    f.label(270, 166, "Manifest commit", tone="purple", cls="small")

    f.wire([c_map.bottom(0), (c_map.cx, 164), (gw.cx + 40, 164), gw.top(40)], tone="amber", dash=True, width=1.6)
    f.label(476, 166, "Placement map", tone="amber", cls="small")

    f.wire([c_scrub.bottom(60), (c_scrub.cx + 60, 164), (WIDTH - MARGIN - 8, 164), (WIDTH - MARGIN - 8, az_boxes[2].cy), az_boxes[2].right(0)], tone="teal", dash=True, width=1.6, tail=True)
    f.label(752, 166, "Scrub & rebuild", tone="teal", cls="small")

    return f.save([
        ("Chunks are immutable and written before the metadata manifest commits, so aborted uploads never expose partial objects.", "noteb"),
        "Spreading the nine shards of an RS(6, 3) stripe evenly across three availability zones lets the store survive an entire AZ outage without data loss.",
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
        ("1. Periodic Scrub", "Read shard + CRC32C", "Detects bit-rot on D4", "teal", "schedule"),
        ("2. Quarantine D4", "Mark shard offline", "Route reads via RS", "red", "warning"),
        ("3. RS(6, 3) Rebuild", "Read any 6 healthy", "Recompute D4 in RAM", "amber", "developer_board"),
        ("4. Atomic Swap", "Write D4 to spare", "Update chunk map", "green", "save"),
    ]
    cw = 188
    cgap = 21
    for i, (hdr, sub1, sub2, tone, ic) in enumerate(steps):
        cx = MARGIN + 20 + i * (cw + cgap)
        box = f.node(
            cx, 288, cw, 114, tone,
            [(hdr, "name"), (sub1, "small"), (sub2, "small")],
            icon=ic, layout="center", kind="card" if tone != "red" else "mid", icon_size=24,
        )
        if i < 3:
            f.wire([box.right(0), (cx + cw + cgap, box.cy)], tone="wire", width=1.8)

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
        546,
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

    # Middle: Offline Media Plane
    f.zone(
        MARGIN, 178, INNER, 148, "amber",
        "Offline Media Plane (Distributed Transcode Pipeline & Origin Store)",
        "Parallel GOP-level encoding turns a 60-minute master into an ABR ladder in minutes",
        icon="developer_board",
    )
    raw = f.node(
        MARGIN + 18, 240, 246, 70, "gray",
        [("Raw Object Store", "name"), ("Master mezzanine file", "sub")],
        icon="folder", kind="card", icon_size=26,
    )
    enc = f.node(
        MARGIN + 304, 240, 248, 70, "amber",
        [("Transcode Workers", "name"), ("Parallel H.264 / AV1", "sub")],
        icon="widgets", kind="card", icon_size=26,
    )
    orig = f.node(
        MARGIN + 592, 240, 246, 70, "blue",
        [("Packaged Origin Store", "name"), ("Immutable 4 s segments", "sub")],
        icon="inventory_2", kind="card", icon_size=26,
    )

    # Bottom: Playback Data Plane
    f.zone(
        MARGIN, 358, INNER, 178, "blue",
        "Playback Data Plane (Multi-Tier CDN Shield, Edge PoPs & ABR Players)",
        "Read path serves immutable segments over HTTP/3 from edge PoPs nearest the viewer",
        icon="play_arrow",
    )
    player = f.node(
        MARGIN + 18, 424, 246, 92, "blue",
        [("Client ABR Players", "name"), ("HLS / DASH buffer loop", "sub"), ("Dynamic bitrate choice", "small")],
        icon="laptop", kind="card", icon_size=26,
    )
    edge = f.node(
        MARGIN + 304, 424, 248, 92, "green",
        [("Global CDN Edge PoPs", "name"), ("95%+ hit · < 20 ms RTT", "sub"), ("Immutable cache TTL", "small")],
        icon="bolt", kind="card", icon_size=26,
    )
    shield = f.node(
        MARGIN + 592, 424, 246, 92, "teal",
        [("Origin Shield Cache", "name"), ("Collapses edge misses", "sub"), ("Protects origin egress", "small")],
        icon="shield", kind="card", icon_size=26,
    )

    # Middle pipeline wires (Left -> Right)
    f.wire([raw.right(0), enc.left(0)], tone="amber", width=1.9)
    f.wire([enc.right(0), orig.left(0)], tone="blue", width=1.9)

    # Serpentine drop: Origin -> Origin Shield -> Edge -> Player (Right -> Left)
    f.wire([orig.bottom(0), (orig.cx, shield.y)], tone="teal", width=2.0)
    f.label(orig.cx - 58, 342, "Cache fill", tone="teal", cls="small")

    f.wire([shield.left(0), edge.right(0)], tone="green", width=2.0)
    f.wire([edge.left(0), player.right(0)], tone="blue", width=2.0)

    # Control plane dashed wires
    f.wire([c_ing.bottom(0), (c_ing.cx, raw.y)], tone="purple", dash=True, width=1.6)
    f.label(c_ing.cx + 52, 162, "Write master", tone="purple", cls="small")

    f.wire([c_dag.bottom(0), (c_dag.cx, enc.y)], tone="amber", dash=True, width=1.6)
    f.label(c_dag.cx + 54, 162, "Dispatch GOPs", tone="amber", cls="small")

    f.wire([c_man.right(0), (WIDTH - MARGIN - 6, c_man.cy), (WIDTH - MARGIN - 6, 342), (player.cx, 342), player.top(0)], tone="teal", dash=True, width=1.5)
    f.label(450, 342, "Manifest & DRM keys (control fetch)", tone="teal", cls="small")

    return f.save([
        ("Origin shielding collapses concurrent cache misses from hundreds of edge PoPs into a single upstream fetch per segment.", "noteb"),
        "Separating manifest and DRM authorization from static media delivery allows global CDN PoPs to cache encrypted segments indefinitely.",
    ])


def ch17_transcode_abr():
    f = Fig(
        "ch17_transcode_abr",
        "Figure 17-3. Chunked DAG Transcoding Ladder and Client-Side ABR Buffer Selection.",
        476,
    )

    # Top Zone: Chunked DAG Transcoding Ladder
    f.zone(
        MARGIN, 0, INNER, 210, "amber",
        "Chunked Parallel Transcoding DAG (Aligned 4-Second GOP Segments)",
        "Master video is split at keyframes so independent workers encode all bitrate rungs in parallel",
        icon="developer_board",
    )
    m_in = f.node(
        MARGIN + 18, 92, 166, 86, "gray",
        [("Master File", "name"), ("60 min · 4K raw", "sub")],
        icon="folder", layout="center", kind="card", icon_size=24,
    )
    splitter = f.node(
        MARGIN + 214, 92, 162, 86, "amber",
        [("GOP Splitter", "name"), ("4 s keyframes", "sub")],
        icon="call_split", layout="center", kind="card", icon_size=24,
    )

    # 3 Parallel Bitrate Rungs
    rx = MARGIN + 416
    rw = 204
    rungs = [
        ("1080p · 5.0 Mbps", "High motion HD", "green", 58),
        ("720p · 2.5 Mbps", "Balanced mobile", "teal", 108),
        ("480p · 1.0 Mbps", "Constrained link", "amber", 158),
    ]
    rboxes = []
    for lbl, sub, tone, ry in rungs:
        rb = f.node(rx, ry, rw, 42, tone, [(lbl, "monob"), (sub, "small")], layout="center", kind="card", r=8)
        rboxes.append(rb)

    pkg = f.node(
        MARGIN + 660, 92, 178, 86, "blue",
        [("CMAF Packager", "name"), ("HLS + DASH index", "sub")],
        icon="inventory_2", layout="center", kind="card", icon_size=24,
    )

    f.wire([m_in.right(0), splitter.left(0)], tone="wire", width=1.8)
    for rb in rboxes:
        f.wire([splitter.right(0), (rx - 20, splitter.cy), (rx - 20, rb.cy), rb.left(0)], tone="amber", width=1.6, radius=6)
        f.wire([rb.right(0), (pkg.x - 20, rb.cy), (pkg.x - 20, pkg.cy), pkg.left(0)], tone="blue", width=1.6, radius=6)

    # Bottom Zone: Client-Side ABR Selection Timeline
    f.zone(
        MARGIN, 234, INNER, 232, "blue",
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
    sw = 188
    sgap = 21
    for i, (s_hdr, s_bw, s_pick, s_buf, tone) in enumerate(segs):
        sx = MARGIN + 20 + i * (sw + sgap)
        box = f.node(
            sx, 300, sw, 144, tone,
            [(s_hdr, "name"), (s_bw, "small"), (s_pick, "monob"), (s_buf, "badge")],
            layout="center", kind="card" if tone != "red" else "mid", r=10,
            text_tone=tone if tone == "red" else None,
        )
        if i < 3:
            f.wire([box.right(0), (sx + sw + sgap, box.cy)], tone="wire", width=1.8)

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
            ("Send Message (Idempotent)", "POST /v1/conv/{id}/messages + client_id", "blue", "edit_note"),
            ("Sync Missed Messages", "GET /v1/conv/{id}/messages?after=seq", "green", "loop"),
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
        544,
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

    # Bottom: Data Plane
    f.zone(
        MARGIN, 178, INNER, 356, "blue",
        "Data Plane (500 Stateful WebSocket Gateways & Partitioned Message Store)",
        "Durable commit precedes live delivery; 100k concurrent TLS sockets per gateway host",
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
        MARGIN + 18, 412, 212, 96, "blue",
        [("Sender Device", "name"), ("WSS send + retry UUID", "sub")],
        icon="laptop", kind="card", icon_size=24,
    )
    mstore = f.node(
        MARGIN + 266, 412, 324, 96, "amber",
        [("Partitioned Message Store", "name"), ("Sharded by conv_id · Ordered seq", "sub"), ("Multi-AZ WAL + cursor index", "small")],
        icon="save", kind="card", icon_size=26,
    )
    recip = f.node(
        MARGIN + 626, 412, 212, 96, "green",
        [("Recipient Devices", "name"), ("Live push or sync pull", "sub")],
        icon="laptop", kind="card", icon_size=24,
    )

    # Data plane wires
    f.wire([sender.top(0), (sender.cx, gw_a.b)], tone="blue", width=2.0)
    f.label(sender.cx + 52, 374, "Send frame", tone="blue", cls="small", back_cls="c-blue")

    f.wire([gw_a.right(0), router.left(0)], tone="blue", width=2.0)
    f.wire([router.right(0), gw_b.left(0)], tone="teal", width=2.0)

    f.wire([gw_b.bottom(0), (gw_b.cx, recip.y)], tone="green", width=2.0)
    f.label(gw_b.cx - 48, 374, "Live push", tone="green", cls="small", back_cls="c-blue")

    # Router <-> Message Store (durable write before push)
    f.wire([router.bottom(0), (router.cx, mstore.y)], tone="amber", width=2.0, tail=True)
    f.label(router.cx + 76, 374, "Persist seq=42", tone="amber", cls="mono", back_cls="c-blue")

    # Control plane dashed wires
    f.wire([gw_a.top(0), (gw_a.cx, 162), (c_pres.cx, 162), c_pres.bottom(0)], tone="teal", dash=True, width=1.6)
    f.label(166, 164, "Heartbeats", tone="teal", cls="small")

    f.wire([router.top(0), (router.cx, c_dir.b)], tone="purple", dash=True, width=1.6, tail=True)
    f.label(router.cx + 68, 164, "Lookup GW", tone="purple", cls="small")

    f.wire([router.top(80), (router.cx + 80, 162), (c_push.cx, 162), c_push.bottom(0)], tone="amber", dash=True, width=1.6)
    f.label(666, 164, "Offline wakeup", tone="amber", cls="small")

    return f.save([
        ("Persisting the message and assigning its per-conversation sequence number before pushing ensures recipients never observe unrecoverable frames.", "noteb"),
        "Stateless routers look up recipient gateway bindings in Redis, forwarding live frames to online sockets or dispatching APNs/FCM wakeups for offline devices.",
    ])


def ch18_delivery_flow():
    f = Fig(
        "ch18_delivery_flow",
        "Figure 18-3. End-to-End Message Sequencing, Online Push, and Offline Cursor Catch-Up.",
        476,
    )

    # Top Zone: Online Write, Dedup, Sequence, and Push
    f.zone(
        MARGIN, 0, INNER, 206, "blue",
        "Online Path: Idempotent Write, Per-Conversation Sequencing, and Push Delivery",
        "Each conversation maintains a monotonic sequence counter; retries deduplicate on client_id",
        icon="bolt",
    )
    online_steps = [
        ("1. Client Send", "client_id = u9a1", "Retries reuse UUID", "blue", "edit_note"),
        ("2. Dedup & Seq", "Assign conv seq=42", "Durable WAL commit", "amber", "lock"),
        ("3. Route & Push", "Lookup -> GW B", "Deliver frame seq=42", "teal", "lan"),
        ("4. Delivery ACK", "Watermark -> 42", "Update sender state", "green", "handshake"),
    ]
    sw = 188
    sgap = 21
    for i, (hdr, sub1, sub2, tone, ic) in enumerate(online_steps):
        sx = MARGIN + 20 + i * (sw + sgap)
        box = f.node(
            sx, 66, sw, 118, tone,
            [(hdr, "name"), (sub1, "mono"), (sub2, "small")],
            icon=ic, layout="center", kind="card", icon_size=24,
        )
        if i < 3:
            f.wire([box.right(0), (sx + sw + sgap, box.cy)], tone="wire", width=1.8)

    # Bottom Zone: Gap Detection and Offline Cursor Catch-Up
    f.zone(
        MARGIN, 230, INNER, 236, "purple",
        "Offline Recovery: Sequence Gap Detection and Multi-Device Cursor Catch-Up",
        "Reconnecting devices pull missed ranges deterministically by sequence number rather than wall-clock time",
        icon="loop",
    )
    o1 = f.node(
        MARGIN + 20, 296, 250, 146, "red",
        [("1. Disconnect Window", "name"), ("Last local cursor: seq=40", "mono"), ("Misses seq 41, 42, 43", "small"), ("APNs/FCM wakes client", "small")],
        icon="warning", layout="center", kind="mid", icon_size=24,
    )
    o2 = f.node(
        MARGIN + 303, 296, 250, 146, "purple",
        [("2. Cursor Sync Query", "name"), ("GET /messages?after=40", "mono"), ("Sequential shard range scan", "small"), ("Bounded page limit (100)", "small")],
        icon="table_rows", layout="center", kind="card", icon_size=24,
    )
    o3 = f.node(
        MARGIN + 586, 296, 250, 146, "green",
        [("3. Ordered Reconcile", "name"), ("Applies seq 41, 42, 43", "mono"), ("Advances cursor -> 43", "small"), ("Resumes live WSS push", "small")],
        icon="play_arrow", layout="center", kind="card", icon_size=24,
    )
    f.wire([o1.right(0), o2.left(0)], tone="purple", width=1.9)
    f.wire([o2.right(0), o3.left(0)], tone="green", width=1.9)

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
