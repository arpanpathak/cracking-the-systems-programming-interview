#!/usr/bin/env python3
"""Generate spacious Material Design 3 light+dark SVG figures for Parts IV & V (Chapters 20-24).

Every figure uses WIDTH = 920, MARGIN = 32, INNER = 856 with generous padding,
concise labels, clean orthogonal wires, and clear control/data plane separation.
"""
from figkit_m3 import Fig, WIDTH, MARGIN, build_use_case_fig

INNER = WIDTH - 2 * MARGIN  # 856px usable width


# =============================================================================
# CHAPTER 20: TICKET BOOKING
# =============================================================================

def ch20_use_cases():
    return build_use_case_fig(
        "ch20_use_cases",
        "Figure 20-1. Actors and Use Cases of the High-Contention Ticket Booking System.",
        "System Boundary: Ticket Booking System",
        "Virtual waiting room · Event-sharded seats · Idempotent checkout",
        actors=[
            ("Ticket Buyer", "Web and mobile purchasers", "blue", "person"),
            ("Event Organizer", "Promoters and venue ops", "purple", "edit_note"),
            ("Payment Processor", "Card network and webhooks", "teal", "handshake"),
        ],
        cases=[
            ("Join Queue & View Seat Map", "GET /v1/shows/{id}/seats (cached)", "blue", "view_module"),
            ("Place Timed Seat Hold", "POST /v1/shows/{id}/holds (TTL 10m)", "amber", "lock"),
            ("Confirm Booking & Pay", "POST /v1/bookings (Idempotency-Key)", "green", "bolt"),
            ("Configure Venue & Sale Gate", "PUT /v1/shows/{id}/layout & rate", "purple", "tune"),
            ("Deliver Settlement Webhook", "POST /v1/webhooks/payment-settled", "teal", "notifications_active"),
        ],
        links=[
            (0, [0, 1, 2], "blue"),
            (1, [3], "purple"),
            (2, [4], "teal"),
        ],
        notes=[
            ("Buyers traverse an admission queue before reaching the synchronous seat-hold and checkout path, isolating the inventory database from flash-sale bursts.", "noteb"),
            "Organizers configure venue layouts and admission rates through the control plane, while payment processors confirm settlement asynchronously via signed webhooks.",
        ],
    )


def ch20_architecture():
    f = Fig(
        "ch20_architecture",
        "Figure 20-2. Virtual Waiting Room, Event-Sharded Inventory Service, and Payment Saga.",
        566,
    )
    # Control Plane (Top)
    cp = f.zone(
        MARGIN, 0, INNER, 140, "purple",
        "Control Plane (Admission Pacing, Shard Directory & Lease Reclamation)",
        "Controls crowd ingress rate · Maps events to shards · Reclaims expired holds",
        icon="settings_suggest", dashed=True,
    )
    c1 = f.node(
        MARGIN + 18, 56, 256, 68, "purple",
        [("Queue Pacing Controller", "name"), ("Token rate per show", "sub")],
        icon="tune", kind="card", icon_size=26,
    )
    c2 = f.node(
        MARGIN + 298, 56, 260, 68, "purple",
        [("Event Shard Directory", "name"), ("Routes show_id to shard", "sub")],
        icon="dns", kind="card", icon_size=26,
    )
    c3 = f.node(
        MARGIN + 582, 56, 256, 68, "teal",
        [("Lease Sweeper Worker", "name"), ("Frees timed-out holds", "sub")],
        icon="schedule", kind="card", icon_size=26,
    )

    # Data Plane (Bottom)
    dp = f.zone(
        MARGIN, 174, INNER, 384, "blue",
        "Data Plane (Admission Gate, Event-Sharded Inventory & Payment Saga)",
        "Waiting room absorbs spike · Row-level CAS prevents double selling under contention",
        icon="layers",
    )

    # Row 1: Ingress & Cache
    buyer = f.node(
        MARGIN + 18, 232, 178, 78, "blue",
        [("Buyers (100k+)", "name"), ("Flash-sale traffic", "sub")],
        icon="person", kind="card", icon_size=24,
    )
    vwr = f.node(
        MARGIN + 222, 232, 196, 78, "amber",
        [("Waiting Room", "name"), ("Signed pass token", "sub")],
        icon="hourglass_top", kind="card", icon_size=24,
    )
    gw = f.node(
        MARGIN + 444, 232, 186, 78, "teal",
        [("Booking API", "name"), ("Verifies pass & key", "sub")],
        icon="swap_horiz", kind="card", icon_size=24,
    )
    cache = f.node(
        MARGIN + 656, 232, 182, 78, "gray",
        [("Seat Map CDN", "name"), ("Eventual reads", "sub")],
        icon="memory", kind="tonal", icon_size=24,
    )

    # Row 2: Inventory & Saga
    inv = f.node(
        MARGIN + 18, 356, 258, 82, "blue",
        [("Inventory Service", "name"), ("Conditional hold & CAS", "sub")],
        icon="inventory_2", kind="card", icon_size=26,
    )
    saga = f.node(
        MARGIN + 312, 356, 246, 82, "purple",
        [("Payment Saga Engine", "name"), ("Idempotent charge step", "sub")],
        icon="loop", kind="card", icon_size=26,
    )
    psp = f.node(
        MARGIN + 594, 356, 244, 82, "green",
        [("Payment Processor", "name"), ("Authorize, capture, refund", "sub")],
        icon="handshake", kind="card", icon_size=26,
    )

    # Row 3: Durable Stores
    db = f.node(
        MARGIN + 18, 466, 258, 72, "blue",
        [("Event-Sharded Seat DB", "name"), ("PRIMARY(show, seat) + ver", "mono")],
        icon="save", kind="mid", icon_size=24,
    )
    outbox = f.node(
        MARGIN + 312, 466, 246, 72, "purple",
        [("Saga Outbox & Journal", "name"), ("Durable step recovery", "sub")],
        icon="table_rows", kind="tonal", icon_size=24,
    )
    tkt = f.node(
        MARGIN + 594, 466, 244, 72, "green",
        [("Ticket Issuance Store", "name"), ("Immutable QR & order", "sub")],
        icon="description", kind="tonal", icon_size=24,
    )

    # Control Plane -> Data Plane dashed wires
    f.wire([c1.bottom(0), (c1.cx, 158), (vwr.cx, 158), vwr.top(0)], tone="purple", dash=True, width=1.6)
    f.label(250, 156, "Admit rate", tone="purple", cls="small")

    f.wire([c2.bottom(0), (c2.cx, 158), (gw.cx, 158), gw.top(0)], tone="purple", dash=True, width=1.6)
    f.label(514, 156, "Shard map", tone="purple", cls="small")

    f.wire([c3.bottom(0), (c3.cx, 206), (MARGIN + 850, 206), (MARGIN + 850, 550), (db.cx, 550), db.bottom(0)],
           tone="teal", dash=True, width=1.5)

    # Data Plane solid wires
    f.wire([buyer.right(0), vwr.left(0)], tone="blue", width=1.9)
    f.wire([vwr.right(0), gw.left(0)], tone="amber", width=1.9)
    f.wire([gw.right(0), cache.left(0)], tone="gray", dash=True, width=1.6)

    f.wire([gw.bottom(-36), (gw.cx - 36, 332), (inv.cx, 332), inv.top(0)], tone="teal", width=1.9)
    f.label(354, 330, "Hold / Confirm", tone="teal", cls="small", back_cls="c-blue")

    f.wire([gw.bottom(28), (gw.cx + 28, 332), (saga.cx, 332), saga.top(0)], tone="purple", width=1.9)
    f.wire([inv.right(0), saga.left(0)], tone="blue", width=1.8, tail=True)
    f.wire([saga.right(0), psp.left(0)], tone="green", width=1.9, tail=True)

    f.wire([inv.bottom(0), db.top(0)], tone="blue", width=1.9)
    f.wire([saga.bottom(0), outbox.top(0)], tone="purple", width=1.8)
    f.wire([psp.bottom(0), tkt.top(0)], tone="green", width=1.8)

    return f.save([
        ("Sharding inventory by event identifier keeps multi-seat holds inside a single database transaction while the virtual waiting room caps concurrent load.", "noteb"),
        "External card rails cannot join a local database transaction, so a durable saga coordinates seat holds, payment capture, and compensating refunds.",
    ])


def ch20_seat_hold_cas():
    f = Fig(
        "ch20_seat_hold_cas",
        "Figure 20-3. Seat State Machine: Conditional Hold, TTL Lease Expiry, and Atomic Confirmation.",
        476,
    )
    # Top: State Machine Zone
    f.zone(
        MARGIN, 0, INNER, 232, "blue",
        "Per-Seat State Machine (Guarded by Monotonic Version and Lease Token)",
        "Every state transition executes an atomic compare-and-swap on the seat row",
        icon="loop",
    )
    s_avail = f.node(
        MARGIN + 22, 82, 214, 84, "green",
        [("1. AVAILABLE", "name"), ("hold_id = NULL", "mono"), ("ver = v", "small")],
        icon="play_arrow", kind="card", icon_size=24,
    )
    s_held = f.node(
        MARGIN + 318, 82, 224, 84, "amber",
        [("2. HELD (Lease)", "name"), ("exp = t0 + 10m", "mono"), ("ver = v + 1", "small")],
        icon="hourglass_top", kind="card", icon_size=24,
    )
    s_sold = f.node(
        MARGIN + 622, 82, 212, 84, "blue",
        [("3. CONFIRMED", "name"), ("order_id = ord_9", "mono"), ("ver = v + 2", "small")],
        icon="lock", kind="card", icon_size=24,
    )

    # Forward transition wires
    f.wire([s_avail.right(0), s_held.left(0)], tone="amber", width=2.0)
    f.label((s_avail.r + s_held.x) / 2, 72, "CAS Hold", tone="amber", cls="small", back_cls="c-blue")

    f.wire([s_held.right(0), s_sold.left(0)], tone="blue", width=2.0)
    f.label((s_held.r + s_sold.x) / 2, 72, "CAS Confirm", tone="blue", cls="small", back_cls="c-blue")

    # Expiry return wire
    f.wire([s_held.bottom(0), (s_held.cx, 198), (s_avail.cx, 198), s_avail.bottom(0)],
           tone="red", dash=True, width=1.8)
    f.label((s_avail.cx + s_held.cx) / 2, 202, "TTL Expired or Payment Failed (Release)", tone="red", cls="small", back_cls="c-blue")

    # Bottom Left: Atomic SQL CAS
    lw = 416
    f.zone(
        MARGIN, 254, lw, 214, "amber",
        "Atomic Conditional Hold (Single-Row CAS)",
        "Zero rows updated signals contention (HTTP 409)",
        icon="code",
    )
    f.rect(MARGIN + 16, 314, lw - 32, 136, "card", r=10, lift=True)
    code_lines = [
        ("UPDATE seats", "monob"),
        ("SET state = 'HELD', hold_id = $1,", "mono"),
        ("    expires_at = NOW() + INTERVAL '10m',", "mono"),
        ("    ver = ver + 1", "mono"),
        ("WHERE seat_id = $2 AND state = 'AVAIL'", "monob"),
        ("  AND ver = $3;  -- 1 row = win", "mono"),
    ]
    for idx, (txt, cls) in enumerate(code_lines):
        f.text(MARGIN + 28, 336 + idx * 19, txt, cls, "start",
               tone="amber" if cls == "monob" else None,
               fit=(MARGIN + 24, MARGIN + lw - 24))

    # Bottom Right: Late Payment Fencing
    rx = MARGIN + lw + 24
    rw = WIDTH - MARGIN - rx  # 416
    f.zone(
        rx, 254, rw, 214, "red",
        "Late Payment Race & Fencing",
        "Expired lease rejects delayed payment confirmation",
        icon="shield",
    )
    f.node(
        rx + 18, 314, rw - 36, 62, "red",
        [("Buyer A Pays After Lease Expiry", "name"), ("t = t0 + 10m05s · Buyer B holds ver = v+3", "small")],
        icon="warning", kind="card", icon_size=24,
    )
    f.node(
        rx + 18, 390, rw - 36, 62, "green",
        [("Fenced Confirm Fails (0 Rows)", "name"), ("Predicate hold_id=A fails -> auto-refund", "small")],
        icon="shield", kind="card", icon_size=24,
    )

    return f.save([
        ("A conditional update on state, lease token, and monotonic version guarantees mutual exclusion without long-lived database row locks.", "noteb"),
        "If a buyer completes payment after the lease expires, the confirmation predicate fails atomically and the saga issues a compensating refund.",
    ])


# =============================================================================
# CHAPTER 21: RIDE HAILING
# =============================================================================

def ch21_use_cases():
    return build_use_case_fig(
        "ch21_use_cases",
        "Figure 21-1. Actors and Use Cases of the Geospatial Ride-Hailing Platform.",
        "System Boundary: Ride-Hailing Platform",
        "High-rate GPS ingestion · Spatial matching · Exclusive dispatch",
        actors=[
            ("Rider", "Passenger mobile client", "blue", "person"),
            ("Driver", "Driver mobile client", "teal", "laptop"),
            ("City Operations", "Dispatch and surge admins", "purple", "engineering"),
        ],
        cases=[
            ("Stream Driver GPS Position", "POST /v1/drivers/{id}/positions (3s)", "teal", "bolt"),
            ("Request Ride & View ETA", "POST /v1/rides (pickup, dropoff)", "blue", "play_arrow"),
            ("Accept or Decline Offer", "PUT /v1/rides/{id}/assignments/{drv}", "amber", "handshake"),
            ("Track Active Trip Lifecycle", "WS /v1/rides/{id}/stream (updates)", "green", "schedule"),
            ("Configure City Policy & Surge", "PUT /v1/regions/{city}/policy", "purple", "tune"),
        ],
        links=[
            (0, [1, 3], "blue"),
            (1, [0, 2, 3], "teal"),
            (2, [4], "purple"),
        ],
        notes=[
            ("Driver location heartbeats dominate write volume and flow into an ephemeral spatial index, whereas trip matching and assignments require durable state.", "noteb"),
            "City operations adjust regional cell boundaries, offer timeouts, and dynamic pricing thresholds without disrupting active trips.",
        ],
    )


def ch21_architecture():
    f = Fig(
        "ch21_architecture",
        "Figure 21-2. Location Ingestion Plane, Cell-Sharded Spatial Index, and Dispatch Engine.",
        564,
    )
    # Control Plane (Top)
    f.zone(
        MARGIN, 0, INNER, 140, "purple",
        "Control Plane (Region Partitioning, Dispatch Policy & Pricing)",
        "City-to-shard ownership · Ring search thresholds · Surge multipliers",
        icon="settings_suggest", dashed=True,
    )
    c1 = f.node(
        MARGIN + 18, 56, 256, 68, "purple",
        [("Cell Partition Map", "name"), ("Maps S2/H3 cells to hosts", "sub")],
        icon="dns", kind="card", icon_size=26,
    )
    c2 = f.node(
        MARGIN + 298, 56, 260, 68, "purple",
        [("Dispatch Policy Store", "name"), ("Offer TTL & ring limits", "sub")],
        icon="tune", kind="card", icon_size=26,
    )
    c3 = f.node(
        MARGIN + 582, 56, 256, 68, "teal",
        [("Surge & Supply Monitor", "name"), ("Cell-level demand balance", "sub")],
        icon="notifications_active", kind="card", icon_size=26,
    )

    # Data Plane (Bottom)
    f.zone(
        MARGIN, 174, INNER, 382, "blue",
        "Data Plane (Ephemeral Location Ingestion & Durable Trip Dispatch)",
        "In-memory spatial index handles 1M+ GPS updates/s; Raft-backed store guards trip state",
        icon="layers",
    )

    # Track 1: Location Ingestion Plane
    drv = f.node(
        MARGIN + 18, 232, 182, 82, "teal",
        [("Driver Clients", "name"), ("3s GPS heartbeat", "sub")],
        icon="laptop", kind="card", icon_size=24,
    )
    ing = f.node(
        MARGIN + 232, 232, 214, 82, "teal",
        [("Location Gateway", "name"), ("Routes by cell ID", "sub")],
        icon="swap_horiz", kind="card", icon_size=24,
    )
    idx = f.node(
        MARGIN + 478, 232, 360, 82, "blue",
        [("Cell-Sharded Spatial Index (RAM)", "name"), ("Latest (lat, lon, ts) · TTL evicts stale", "sub")],
        icon="memory", kind="card", icon_size=26,
    )

    # Track 2: Dispatch & Durable State
    rdr = f.node(
        MARGIN + 18, 364, 182, 82, "blue",
        [("Rider Clients", "name"), ("POST /v1/rides", "mono")],
        icon="person", kind="card", icon_size=24,
    )
    disp = f.node(
        MARGIN + 232, 364, 214, 82, "amber",
        [("Dispatch Engine", "name"), ("Ring search + offer FSM", "sub")],
        icon="call_split", kind="card", icon_size=24,
    )
    lock = f.node(
        MARGIN + 478, 348, 174, 72, "purple",
        [("Offer Lock", "name"), ("1 active offer / drv", "small")],
        icon="lock", kind="card", icon_size=22,
    )
    trip = f.node(
        MARGIN + 668, 348, 170, 72, "green",
        [("Trip Store", "name"), ("Raft durable FSM", "small")],
        icon="save", kind="mid", icon_size=22,
    )
    eta = f.node(
        MARGIN + 478, 444, 360, 72, "gray",
        [("Road-Graph Routing & ETA Engine", "name"), ("Ranks top-K spatial candidates by drive time", "sub")],
        icon="schedule", kind="tonal", icon_size=24,
    )

    # Control Plane -> Data Plane dashed wires
    f.wire([c1.bottom(0), (c1.cx, 158), (ing.cx, 158), ing.top(0)], tone="purple", dash=True, width=1.6)
    f.label(270, 156, "Cell map", tone="purple", cls="small")

    f.wire([c2.bottom(0), (c2.cx, 158), (idx.cx - 80, 158), (idx.cx - 80, 232)], tone="purple", dash=True, width=1.6)
    f.label(536, 156, "Policy", tone="purple", cls="small")

    f.wire([idx.top(90), (idx.cx + 90, 158), (c3.cx, 158), c3.bottom(0)], tone="teal", dash=True, width=1.6)
    f.label(752, 156, "Cell counts", tone="teal", cls="small")

    # Data Plane solid wires
    f.wire([drv.right(0), ing.left(0)], tone="teal", width=1.9)
    f.wire([ing.right(0), idx.left(0)], tone="teal", width=1.9)

    f.wire([rdr.right(0), disp.left(0)], tone="blue", width=1.9)
    f.wire([disp.top(44), (disp.cx + 44, 330), (idx.cx - 90, 330), (idx.cx - 90, 314)], tone="blue", width=1.8, tail=True)
    f.label(486, 330, "Query cells", tone="blue", cls="small", back_cls="c-blue")

    f.wire([disp.right(-20), lock.left(0)], tone="purple", width=1.8)
    f.wire([lock.right(0), trip.left(0)], tone="green", width=1.8)
    f.wire([disp.bottom(0), (disp.cx, eta.cy), eta.left(0)], tone="amber", width=1.8, tail=True)
    f.label(358, 496, "Rank ETA", tone="amber", cls="small", back_cls="c-blue")

    return f.save([
        ("Separating volatile GPS updates from durable trip storage prevents high-frequency writes from saturating consensus logs.", "noteb"),
        "Spatial lookups return candidate drivers from memory in milliseconds, after which the routing engine ranks candidates by real road-network travel time.",
    ])


def ch21_spatial_dispatch():
    f = Fig(
        "ch21_spatial_dispatch",
        "Figure 21-3. Hierarchical Spatial Cell Ring Expansion and Exclusive Driver Offer Protocol.",
        472,
    )
    # Left panel: 3x3 Spatial Cell Grid + Ring Expansion
    lw = 414
    f.zone(
        MARGIN, 0, lw, 464, "teal",
        "Hierarchical Spatial Cell Ring Expansion",
        "Query center cell + 8 neighbors; widen if sparse",
        icon="view_module",
    )

    # Outer Ring 2 dashed halo
    gx0, gy0 = MARGIN + 78, 70
    cw, ch = 82, 56
    gap = 6
    grid_w = 3 * cw + 2 * gap
    grid_h = 3 * ch + 2 * gap
    f.rect(gx0 - 16, gy0 - 12, grid_w + 32, grid_h + 40, "o-teal", r=14, extra=' stroke-dasharray="6 5"')
    f.text(gx0 + grid_w / 2, gy0 + grid_h + 18, "Ring 2 (5x5 fallback if < K free drivers)", "small", "middle", tone="teal")

    cells_meta = [
        [("N1", "1 drv", "card", "gray"), ("N2", "0 drv", "card", "gray"), ("N3", "2 drv", "card", "teal")],
        [("N4", "edge drv", "mid", "amber"), ("CENTER", "Rider + 1", "mid", "blue"), ("N5", "2 drv", "card", "teal")],
        [("N6", "0 drv", "card", "gray"), ("N7", "1 drv", "card", "teal"), ("N8", "0 drv", "card", "gray")],
    ]
    for r in range(3):
        for c in range(3):
            title_c, sub_c, kind_c, tone_c = cells_meta[r][c]
            cx = gx0 + c * (cw + gap)
            cy = gy0 + r * (ch + gap)
            f.cell(cx, cy, cw, ch, tone_c, [(title_c, "monob"), (sub_c, "small")], kind=kind_c, r=8)

    f.node(
        MARGIN + 18, 302, lw - 36, 66, "blue",
        [("1. Read Center + 8 Neighbors", "name"), ("Captures drivers right across cell borders", "sub")],
        icon="view_module", kind="card", icon_size=24,
    )
    f.node(
        MARGIN + 18, 382, lw - 36, 66, "teal",
        [("2. Escalate to Ring 2 or Parent", "name"), ("Adaptive radius handles low-density suburbs", "sub")],
        icon="layers", kind="card", icon_size=24,
    )

    # Right panel: Exclusive Driver Offer Protocol
    rx = MARGIN + lw + 24
    rw = WIDTH - MARGIN - rx  # 418
    f.zone(
        rx, 0, rw, 464, "amber",
        "Exclusive Driver Offer Protocol",
        "Serialized 15-second leases prevent dual assignment",
        icon="handshake",
    )
    p1 = f.node(
        rx + 18, 66, rw - 36, 72, "blue",
        [("1. Rank Top-K by Road ETA", "name"), ("Sorted list: [D1 (2m), D2 (3m), D3 (5m)]", "sub")],
        icon="bolt", kind="card", icon_size=24,
    )
    p2 = f.node(
        rx + 18, 162, rw - 36, 74, "amber",
        [("2. Lock D1 & Send Offer #1", "name"), ("Atomic lease: driver D1 locked for 15s", "sub")],
        icon="lock", kind="card", icon_size=24,
    )
    p3 = f.node(
        rx + 18, 260, rw - 36, 74, "red",
        [("3. Timeout / Decline Releases D1", "name"), ("No reply at 15s -> release lock, advance", "sub")],
        icon="timer", kind="mid", icon_size=24,
    )
    p4 = f.node(
        rx + 18, 358, rw - 36, 82, "green",
        [("4. Offer #2 -> D2 Accepts (CAS)", "name"), ("Ride = MATCHED · D2 = EN_ROUTE", "mono")],
        icon="handshake", kind="card", icon_size=24,
    )

    f.wire([p1.bottom(0), p2.top(0)], tone="blue", width=1.8)
    f.wire([p2.bottom(0), p3.top(0)], tone="amber", width=1.8)
    f.wire([p3.bottom(0), p4.top(0)], tone="green", width=1.8)

    return f.save([
        ("Searching the rider cell together with all eight surrounding neighbors guarantees that a nearby driver across a grid boundary is never missed.", "noteb"),
        "Holding an exclusive short-lived lease on each offered driver prevents two concurrent riders from matching the same vehicle simultaneously.",
    ])


# =============================================================================
# CHAPTER 22: SEARCH AUTOCOMPLETE
# =============================================================================

def ch22_use_cases():
    return build_use_case_fig(
        "ch22_use_cases",
        "Figure 22-1. Actors and Use Cases of the Real-Time Search Autocomplete Service.",
        "System Boundary: Search Autocomplete Service",
        "Sub-20 ms edge prefix lookup · Batch ranking · Policy filtering",
        actors=[
            ("Searcher", "Browser and mobile clients", "blue", "person"),
            ("Search Backend", "Completed query log emitter", "teal", "dns"),
            ("Trust & Safety Ops", "Moderation and blocklists", "purple", "shield"),
        ],
        cases=[
            ("Fetch Top-K Suggestions", "GET /v1/suggestions?q={prefix}", "blue", "bolt"),
            ("Emit Completed Search Event", "Async append -> Query Log Stream", "teal", "description"),
            ("Aggregate & Build Trie Snap", "Batch decay + Top-K trie artifact", "amber", "layers"),
            ("Roll Out Snapshot to Edge", "Atomic blue/green pointer swap", "green", "swap_horiz"),
            ("Enforce Safety Blocklist", "PUT /v1/blocklist (filtered terms)", "purple", "block"),
        ],
        links=[
            (0, [0], "blue"),
            (1, [1, 2], "teal"),
            (2, [3, 4], "purple"),
        ],
        notes=[
            ("Keystroke lookups execute solely against read-only precomputed snapshots, avoiding lock contention with continuous query aggregation.", "noteb"),
            "Trust and safety filters scrub prohibited terms both during offline snapshot assembly and at edge serving boundaries.",
        ],
    )


def ch22_architecture():
    f = Fig(
        "ch22_architecture",
        "Figure 22-2. Offline Aggregation Pipeline, Trie Snapshot Rollout, and Edge Query Path.",
        558,
    )
    # Control & Offline Build Plane (Top)
    f.zone(
        MARGIN, 0, INNER, 248, "purple",
        "Control & Offline Build Plane (Aggregation, Filtering & Snapshot Rollout)",
        "Batch pipeline decouples write-heavy counting from read-only edge serving nodes",
        icon="settings_suggest", dashed=True,
    )
    qlog = f.node(
        MARGIN + 18, 58, 184, 72, "teal",
        [("Query Log", "name"), ("Sampled events", "sub")],
        icon="description", kind="card", icon_size=24,
    )
    agg = f.node(
        MARGIN + 228, 58, 198, 72, "purple",
        [("Aggregator", "name"), ("Counts + decay", "sub")],
        icon="loop", kind="card", icon_size=24,
    )
    bldr = f.node(
        MARGIN + 452, 58, 184, 72, "amber",
        [("Trie Builder", "name"), ("Top-K per node", "sub")],
        icon="code", kind="card", icon_size=24,
    )
    flt = f.node(
        MARGIN + 662, 58, 176, 72, "red",
        [("Safety Filter", "name"), ("Blocklist scrub", "sub")],
        icon="shield", kind="card", icon_size=24,
    )

    snap = f.node(
        MARGIN + 118, 158, 296, 72, "purple",
        [("Immutable Snapshot Store", "name"), ("Versioned trie blobs (v108)", "sub")],
        icon="inventory_2", kind="card", icon_size=24,
    )
    ctrl = f.node(
        MARGIN + 462, 158, 296, 72, "purple",
        [("Snapshot Rollout Controller", "name"), ("Canary check & atomic swap", "sub")],
        icon="swap_horiz", kind="card", icon_size=24,
    )

    f.wire([qlog.right(0), agg.left(0)], tone="teal", width=1.8)
    f.wire([agg.right(0), bldr.left(0)], tone="purple", width=1.8)
    f.wire([bldr.right(0), flt.left(0)], tone="amber", width=1.8)
    f.wire([flt.bottom(0), (flt.cx, 144), (snap.cx, 144), snap.top(0)], tone="purple", width=1.8)
    f.wire([snap.right(0), ctrl.left(0)], tone="purple", width=1.8)

    # Data Plane (Bottom)
    f.zone(
        MARGIN, 286, INNER, 264, "blue",
        "Online Data Plane (Edge Query Path: Read-Only, < 20 ms p99)",
        "Debounced keystrokes hit CDN cache first, then prefix-sharded in-memory trie replicas",
        icon="layers",
    )
    cli = f.node(
        MARGIN + 18, 346, 178, 82, "blue",
        [("Browser Client", "name"), ("Debounce + seq ID", "sub")],
        icon="laptop", kind="card", icon_size=24,
    )
    cdn = f.node(
        MARGIN + 224, 346, 186, 82, "green",
        [("CDN Edge Cache", "name"), ("Hot 1-2 char keys", "sub")],
        icon="bolt", kind="card", icon_size=24,
    )
    rtr = f.node(
        MARGIN + 438, 346, 178, 82, "teal",
        [("Prefix Router", "name"), ("Prefix shards a-z", "sub")],
        icon="call_split", kind="card", icon_size=24,
    )
    trie = f.node(
        MARGIN + 644, 346, 194, 82, "blue",
        [("In-Memory Trie", "name"), ("O(L) RAM lookup", "sub")],
        icon="memory", kind="card", icon_size=24,
    )

    guard = f.node(
        MARGIN + 18, 460, 392, 68, "amber",
        [("Client Out-of-Order Guard", "name"), ("Discards late replies when response_seq < latest_seq", "sub")],
        icon="rule", kind="tonal", icon_size=24,
    )
    swap = f.node(
        MARGIN + 438, 460, 400, 68, "purple",
        [("Double-Buffered Atomic Swap", "name"), ("Loads v108 beside v107, flips read pointer lock-free", "sub")],
        icon="swap_horiz", kind="tonal", icon_size=24,
    )

    # Control -> Data Plane dashed wire
    f.wire([ctrl.bottom(40), (ctrl.cx + 40, 268), (trie.cx, 268), trie.top(0)], tone="purple", dash=True, width=1.7)
    f.label(712, 266, "Push v108", tone="purple", cls="small")

    # Data Plane solid wires
    f.wire([cli.right(0), cdn.left(0)], tone="blue", width=1.9)
    f.wire([cdn.right(0), rtr.left(0)], tone="green", width=1.9)
    f.wire([rtr.right(0), trie.left(0)], tone="teal", width=1.9)

    return f.save([
        ("Precomputing immutable trie snapshots offline lets edge nodes serve prefix lookups strictly from memory with zero write locks.", "noteb"),
        "Client-side debouncing and sequence numbers prevent stale network responses from overwriting newer keystrokes in the search box.",
    ])


def ch22_trie_pipeline():
    f = Fig(
        "ch22_trie_pipeline",
        "Figure 22-3. Precomputed Top-K Prefix Trie Nodes and Exponential Frequency Decay.",
        466,
    )
    # Left panel: Precomputed Top-K Trie
    lw = 472
    f.zone(
        MARGIN, 0, lw, 458, "blue",
        "Precomputed Top-K Prefix Trie",
        "Each node stores its sorted Top-K completions for O(L) reads",
        icon="layers",
    )

    root = f.cell(MARGIN + 178, 62, 116, 40, "gray", [("Root (empty)", "monob")], kind="card", r=8)
    nk = f.cell(MARGIN + 150, 126, 172, 46, "teal", [("Node 'k'", "monob"), ("Top-3 cached", "small")], kind="card", r=8)

    # Highlighted 'ka' node card
    ka_x, ka_y, ka_w, ka_h = MARGIN + 22, 206, 224, 116
    f.rect(ka_x, ka_y, ka_w, ka_h, "card", r=12, lift=True)
    f.rect(ka_x, ka_y, ka_w, 30, "m-amber", r=10)
    f.text(ka_x + 12, ka_y + 20, "Node 'ka'  (Query Match)", "monob", "start", tone="amber", fit=(ka_x + 8, ka_x + ka_w - 8))
    f.text(ka_x + 14, ka_y + 52, "1. kafka           940", "mono", "start", fit=(ka_x + 10, ka_x + ka_w - 10))
    f.text(ka_x + 14, ka_y + 74, "2. kayak           610", "mono", "start", fit=(ka_x + 10, ka_x + ka_w - 10))
    f.text(ka_x + 14, ka_y + 96, "3. karma           420", "mono", "start", fit=(ka_x + 10, ka_x + ka_w - 10))

    # Sibling 'ki' node
    ki_x, ki_y, ki_w, ki_h = MARGIN + 268, 206, 184, 92
    f.rect(ki_x, ki_y, ki_w, ki_h, "c-gray", r=10)
    f.text(ki_x + 12, ki_y + 24, "Node 'ki'", "monob", "start", fit=(ki_x + 8, ki_x + ki_w - 8))
    f.text(ki_x + 12, ki_y + 48, "1. kindle     530", "mono", "start", fit=(ki_x + 8, ki_x + ki_w - 8))
    f.text(ki_x + 12, ki_y + 70, "2. kicad      280", "mono", "start", fit=(ki_x + 8, ki_x + ki_w - 8))

    # Child 'kaf' node
    kaf_x, kaf_y, kaf_w, kaf_h = MARGIN + 22, 354, 224, 86
    f.rect(kaf_x, kaf_y, kaf_w, kaf_h, "card", r=10, lift=True)
    f.text(kaf_x + 12, kaf_y + 24, "Node 'kaf'", "monob", "start", tone="green", fit=(kaf_x + 8, kaf_x + kaf_w - 8))
    f.text(kaf_x + 12, kaf_y + 48, "1. kafka streams   480", "mono", "start", fit=(kaf_x + 8, kaf_x + kaf_w - 8))
    f.text(kaf_x + 12, kaf_y + 70, "2. kafka connect   310", "mono", "start", fit=(kaf_x + 8, kaf_x + kaf_w - 8))

    # Trie edges
    f.wire([root.bottom(0), nk.top(0)], tone="teal", width=1.8)
    f.wire([nk.bottom(-36), (nk.cx - 36, 188), (ka_x + ka_w / 2, 188), (ka_x + ka_w / 2, ka_y)], tone="amber", width=2.0)
    f.wire([nk.bottom(36), (nk.cx + 36, 188), (ki_x + ki_w / 2, 188), (ki_x + ki_w / 2, ki_y)], tone="gray", width=1.6)
    f.wire([(ka_x + ka_w / 2, ka_y + ka_h), (kaf_x + kaf_w / 2, kaf_y)], tone="green", width=1.8)

    f.node(
        MARGIN + 268, 354, 184, 86, "blue",
        [("Lookup Cost", "name"), ("O(L) pointer hops", "mono"), ("Zero subtree scan", "small")],
        kind="tonal", r=10,
    )

    # Right panel: Exponential Frequency Decay
    rx = MARGIN + lw + 22
    rw = WIDTH - MARGIN - rx  # 362
    f.zone(
        rx, 0, rw, 458, "purple",
        "Exponential Frequency Decay",
        "Recent surges outrank stale historical counts",
        icon="schedule",
    )

    # Formula Card
    f.rect(rx + 16, 62, rw - 32, 86, "card", r=10, lift=True)
    f.text(rx + 28, 86, "Weighted Score Recurrence", "name", "start", tone="purple", fit=(rx + 24, rx + rw - 24))
    f.text(rx + 28, 110, "S(t) = a * C(t) + (1 - a) * S(t-1)", "monob", "start", fit=(rx + 24, rx + rw - 24))
    f.text(rx + 28, 132, "Hourly decay a = 0.35 favors fresh trends", "small", "start", fit=(rx + 24, rx + rw - 24))

    # Decay weight bars
    f.rect(rx + 16, 166, rw - 32, 186, "card", r=10, lift=True)
    f.text(rx + 28, 190, "Relative Weight by Age (a = 0.35)", "name", "start", fit=(rx + 24, rx + rw - 24))
    bars = [
        ("Current hr", 1.00, "green"),
        ("t - 1 hr", 0.65, "teal"),
        ("t - 2 hr", 0.42, "blue"),
        ("t - 4 hr", 0.18, "gray"),
    ]
    bx0 = rx + 114
    bw_max = 152
    for idx, (lbl, weight, tone) in enumerate(bars):
        by = 208 + idx * 34
        f.text(rx + 28, by + 15, lbl, "small", "start", fit=(rx + 24, bx0 - 8))
        f.rect(bx0, by + 4, bw_max, 14, "c-gray", r=5)
        f.rect(bx0, by + 4, max(10, bw_max * weight), 14, f"a-{tone}", r=5)
        f.text(bx0 + bw_max + 10, by + 15, f"{weight:.2f}", "monob", "start", tone=tone, fit=(bx0 + bw_max + 6, rx + rw - 20))

    # Memory bound card
    f.node(
        rx + 16, 370, rw - 32, 70, "amber",
        [("Bounded Memory Footprint", "name"), ("Cap prefix length <= 50; store Top-K only", "sub")],
        icon="memory", kind="card", icon_size=24,
    )

    return f.save([
        ("Caching the Top-K ranked completions directly inside every trie node converts each keystroke into a fixed-depth pointer traversal with no subtree merge.", "noteb"),
        "Exponentially decaying historical query counts allows emerging events to surface in top suggestions within a single build cycle.",
    ])


# =============================================================================
# CHAPTER 23: WEB CRAWLER
# =============================================================================

def ch23_use_cases():
    return build_use_case_fig(
        "ch23_use_cases",
        "Figure 23-1. Actors and Use Cases of the Distributed Web Crawler.",
        "System Boundary: Distributed Web Crawler",
        "Polite host scheduling · Robots compliance · Content dedup",
        actors=[
            ("Crawl Operator", "Seed and host policy admins", "purple", "engineering"),
            ("Target Web Host", "External origin HTTP servers", "amber", "dns"),
            ("Search Indexer", "Downstream page consumers", "teal", "library_books"),
        ],
        cases=[
            ("Submit Seed URLs", "POST /v1/seeds (priority & depth)", "purple", "edit_note"),
            ("Configure Host Crawl Rules", "PUT /v1/hosts/{host}/rules", "amber", "tune"),
            ("Fetch robots.txt & Pages", "Polite HTTP GET (1 req / delay)", "blue", "play_arrow"),
            ("Filter Traps & Duplicates", "URL Bloom filter + SimHash dedup", "red", "block"),
            ("Consume Crawled Page Feed", "GET /v1/pages?after={cursor}", "teal", "table_rows"),
        ],
        links=[
            (0, [0, 1], "purple"),
            (1, [2], "amber"),
            (2, [3, 4], "teal"),
        ],
        notes=[
            ("Operators inject seed URLs and override host-level crawl delays, while external web hosts dictate permitted paths through robots.txt directives.", "noteb"),
            "Downstream indexers consume a deduplicated, monotonically ordered page feed without re-parsing duplicate mirrors or crawler traps.",
        ],
    )


def ch23_architecture():
    f = Fig(
        "ch23_architecture",
        "Figure 23-2. Seed Coordinator, Politeness Frontier, Fetcher Workers, and Content Deduplicator.",
        566,
    )
    # Control Plane (Top)
    f.zone(
        MARGIN, 0, INNER, 140, "purple",
        "Control Plane (Seed Coordinator, Host Rules & Robots Cache)",
        "Consistent-hash host ownership · robots.txt compliance · Crawl-trap defense",
        icon="settings_suggest", dashed=True,
    )
    c1 = f.node(
        MARGIN + 18, 56, 256, 68, "purple",
        [("Seed Coordinator", "name"), ("Assigns host partitions", "sub")],
        icon="edit_note", kind="card", icon_size=26,
    )
    c2 = f.node(
        MARGIN + 298, 56, 260, 68, "amber",
        [("Host Policy & Traps", "name"), ("Blocks infinite calendars", "sub")],
        icon="shield", kind="card", icon_size=26,
    )
    c3 = f.node(
        MARGIN + 582, 56, 256, 68, "teal",
        [("Robots & DNS Cache", "name"), ("TTL-cached rules & IPs", "sub")],
        icon="dns", kind="card", icon_size=26,
    )

    # Data Plane (Bottom)
    f.zone(
        MARGIN, 174, INNER, 384, "blue",
        "Data Plane (Polite Crawl Loop: Frontier -> Fetch -> Parse -> Deduplicate)",
        "Hostname partitioning ensures a single frontier shard strictly enforces per-host crawl delay",
        icon="layers",
    )

    # Row 1: Frontier -> Fetch -> Origin
    front = f.node(
        MARGIN + 18, 234, 240, 82, "amber",
        [("Politeness Frontier", "name"), ("Host queues + min-heap", "sub")],
        icon="schedule", kind="card", icon_size=26,
    )
    fetch = f.node(
        MARGIN + 308, 234, 240, 82, "blue",
        [("Fetcher Worker Pool", "name"), ("Async HTTP/TLS fetch", "sub")],
        icon="bolt", kind="card", icon_size=26,
    )
    orig = f.node(
        MARGIN + 598, 234, 240, 82, "gray",
        [("External Web Hosts", "name"), ("1 request / host delay", "sub")],
        icon="lan", kind="tonal", icon_size=26,
    )

    # Row 2: URL Seen <- Parse -> Deduplicator
    seen = f.node(
        MARGIN + 18, 362, 240, 82, "purple",
        [("URL Seen Filter", "name"), ("Sharded Bloom + RocksDB", "sub")],
        icon="rule", kind="card", icon_size=26,
    )
    parse = f.node(
        MARGIN + 308, 362, 240, 82, "teal",
        [("HTML Parser", "name"), ("Extracts & normalizes URLs", "sub")],
        icon="code", kind="card", icon_size=26,
    )
    dedup = f.node(
        MARGIN + 598, 362, 240, 82, "green",
        [("Content Deduplicator", "name"), ("SimHash near-dup check", "sub")],
        icon="layers", kind="card", icon_size=26,
    )

    # Row 3: Durable Page Store
    store = f.node(
        MARGIN + 308, 474, 530, 66, "green",
        [("Crawled Page Object Store & Change Feed", "name"), ("Stores unique pages · GET /v1/pages?after={cursor}", "mono")],
        icon="save", kind="mid", icon_size=24,
    )

    # Control Plane -> Data Plane dashed wires
    f.wire([c1.bottom(0), (c1.cx, 158), (front.cx, 158), front.top(0)], tone="purple", dash=True, width=1.6)
    f.label(168, 156, "Seeds", tone="purple", cls="small")

    f.wire([c2.bottom(0), (c2.cx, 158), (front.cx + 76, 158), front.top(76)], tone="amber", dash=True, width=1.6)
    f.label(350, 156, "Trap rules", tone="amber", cls="small")

    f.wire([c3.bottom(0), (c3.cx, 158), (fetch.cx, 158), fetch.top(0)], tone="teal", dash=True, width=1.6)
    f.label(598, 156, "DNS / robots", tone="teal", cls="small")

    # Data Plane solid wires
    f.wire([front.right(0), fetch.left(0)], tone="amber", width=1.9)
    f.wire([fetch.right(0), orig.left(0)], tone="blue", width=1.9, tail=True)
    f.wire([fetch.bottom(0), parse.top(0)], tone="blue", width=1.9)
    f.label(fetch.cx + 56, 338, "HTML body", tone="blue", cls="small", back_cls="c-blue")

    f.wire([parse.left(0), seen.right(0)], tone="purple", width=1.9)
    f.wire([seen.top(0), front.bottom(0)], tone="purple", width=1.9)
    f.label(seen.cx + 56, 338, "Unseen URLs", tone="purple", cls="small", back_cls="c-blue")

    f.wire([parse.right(0), dedup.left(0)], tone="teal", width=1.9)
    f.wire([dedup.bottom(0), (dedup.cx, store.y)], tone="green", width=1.9)

    return f.save([
        ("Routing discovered URLs by hostname assigns each external domain to a single frontier shard, guaranteeing polite request spacing without global locks.", "noteb"),
        "URL deduplication avoids revisiting known addresses, whereas content fingerprinting eliminates duplicate pages served under distinct URLs.",
    ])


def ch23_politeness_frontier():
    f = Fig(
        "ch23_politeness_frontier",
        "Figure 23-3. Mercator Two-Stage Frontier: Priority Front Queues and Per-Host Back Queues.",
        472,
    )
    # Stage 1: Front Queues (Left)
    s1_w = 248
    f.zone(
        MARGIN, 0, s1_w, 464, "purple",
        "Stage 1: Front Queues",
        "Orders URLs by importance",
        icon="tune",
    )
    prio = f.node(
        MARGIN + 16, 62, s1_w - 32, 66, "blue",
        [("URL Prioritizer", "name"), ("PageRank & freshness", "sub")],
        icon="bolt", kind="card", icon_size=24,
    )
    fq1 = f.cell(MARGIN + 16, 154, s1_w - 32, 54, "green", [("Front Queue P1 (High)", "monob"), ("News & root pages", "small")], kind="card", r=9)
    fq2 = f.cell(MARGIN + 16, 224, s1_w - 32, 54, "blue", [("Front Queue P2 (Med)", "monob"), ("Standard articles", "small")], kind="card", r=9)
    fq3 = f.cell(MARGIN + 16, 294, s1_w - 32, 54, "gray", [("Front Queue P3 (Low)", "monob"), ("Deep archive links", "small")], kind="tonal", r=9)

    sel = f.node(
        MARGIN + 16, 376, s1_w - 32, 68, "purple",
        [("Biased Selector", "name"), ("Draws P1 more often", "sub")],
        icon="call_split", kind="mid", icon_size=24,
    )

    f.wire([prio.bottom(0), fq1.top(0)], tone="purple", width=1.7)
    f.wire([fq3.bottom(0), sel.top(0)], tone="purple", width=1.7)

    # Stage 2: Per-Host Back Queues & Min-Heap (Right)
    s2_x = MARGIN + s1_w + 32
    s2_w = WIDTH - MARGIN - s2_x  # 576
    f.zone(
        s2_x, 0, s2_w, 464, "amber",
        "Stage 2: Per-Host Back Queues & Politeness Min-Heap",
        "Invariant: every back queue holds URLs for exactly one origin host",
        icon="schedule",
    )

    # Left column inside Stage 2: Back Queues + Mapping Table
    bq_x = s2_x + 20
    bq_w = 248
    bq1 = f.cell(bq_x, 66, bq_w, 60, "blue", [("Back Queue B1", "monob"), ("news.example (4 URLs)", "small")], kind="card", r=9)
    bq2 = f.cell(bq_x, 144, bq_w, 60, "teal", [("Back Queue B2", "monob"), ("wiki.example (7 URLs)", "small")], kind="card", r=9)
    bq3 = f.cell(bq_x, 222, bq_w, 60, "purple", [("Back Queue B3", "monob"), ("docs.example (2 URLs)", "small")], kind="card", r=9)

    hmap = f.node(
        bq_x, 316, bq_w, 128, "gray",
        [("Host-to-Queue Table", "name"), ("news.example -> B1", "mono"), ("wiki.example -> B2", "mono"), ("docs.example -> B3", "mono")],
        kind="card", r=10,
    )

    # Right column inside Stage 2: Min-Heap + Fetcher Dispatch + Re-insert
    hp_x = bq_x + bq_w + 36
    hp_w = s2_x + s2_w - 20 - hp_x  # 252
    f.rect(hp_x, 66, hp_w, 128, "card", r=12, lift=True)
    f.rect(hp_x, 66, hp_w, 30, "m-amber", r=10)
    f.text(hp_x + 12, 86, "Min-Heap (Next Fetch Time)", "monob", "start", tone="amber", fit=(hp_x + 8, hp_x + hp_w - 8))
    f.text(hp_x + 14, 116, "root -> B1  (t = 10.0s)", "monob", "start", tone="green", fit=(hp_x + 10, hp_x + hp_w - 10))
    f.text(hp_x + 14, 140, "next -> B2  (t = 11.5s)", "mono", "start", fit=(hp_x + 10, hp_x + hp_w - 10))
    f.text(hp_x + 14, 164, "next -> B3  (t = 14.2s)", "mono", "start", fit=(hp_x + 10, hp_x + hp_w - 10))

    disp = f.node(
        hp_x, 224, hp_w, 82, "green",
        [("Fetcher Worker Pop", "name"), ("Wait until now >= t_min", "sub")],
        icon="play_arrow", kind="card", icon_size=24,
    )
    reins = f.node(
        hp_x, 342, hp_w, 102, "amber",
        [("Politeness Re-Insert", "name"), ("t_next = now + delay", "mono"), ("Refill B1 if empty", "small")],
        icon="timer", kind="mid", icon_size=24,
    )

    # Wire Stage 1 -> Stage 2
    f.wire([sel.right(0), (MARGIN + s1_w + 16, sel.cy), (MARGIN + s1_w + 16, hmap.cy), hmap.left(0)],
           tone="purple", width=1.9)
    f.wire([hmap.top(0), bq3.bottom(0)], tone="purple", dash=True, width=1.6)

    # Wire Back Queues -> Min-Heap -> Fetcher -> Re-Insert
    f.wire([bq1.right(0), (hp_x, bq1.cy)], tone="blue", width=1.8)
    f.wire([bq2.right(0), (hp_x, bq2.cy)], tone="teal", width=1.8)
    f.wire([(hp_x + hp_w / 2, 194), disp.top(0)], tone="green", width=1.9)
    f.wire([disp.bottom(0), reins.top(0)], tone="amber", width=1.9)
    f.wire([reins.right(0), (s2_x + s2_w - 8, reins.cy), (s2_x + s2_w - 8, 128), (hp_x + hp_w, 128)],
           tone="amber", dash=True, width=1.7)

    return f.save([
        ("Separating priority front queues from per-host back queues resolves the conflict between crawling high-value pages first and respecting per-host politeness.", "noteb"),
        "A min-heap keyed by each back queue's earliest permissible fetch timestamp guarantees at most one concurrent request per host without scanning idle queues.",
    ])


# =============================================================================
# CHAPTER 24: METRICS AND MONITORING
# =============================================================================

def ch24_use_cases():
    return build_use_case_fig(
        "ch24_use_cases",
        "Figure 24-1. Actors and Use Cases of the Time-Series Metrics and Alerting Platform.",
        "System Boundary: Metrics & Alerting Platform",
        "High-cardinality ingestion · PromQL queries · Isolated alerting",
        actors=[
            ("Instrumented Service", "App and host exporters", "blue", "developer_board"),
            ("SRE / On-Call Engineer", "Dashboards and alert rules", "purple", "engineering"),
            ("Incident Pager", "Escalation webhook sink", "red", "notifications_active"),
        ],
        cases=[
            ("Scrape or Push Samples", "GET /metrics  or  Remote Write", "blue", "bolt"),
            ("Query & Aggregate Series", "GET /v1/series?query=rate(...)", "teal", "table_rows"),
            ("Define Alert Thresholds", "PUT /v1/alerts/{name} (for: 5m)", "purple", "edit_note"),
            ("Compact & Downsample Data", "2h blocks -> 5m / 1h rollups", "amber", "layers"),
            ("Dispatch & Heartbeat Alerts", "Fire incident + dead-man switch", "red", "warning"),
        ],
        links=[
            (0, [0], "blue"),
            (1, [1, 2, 3], "purple"),
            (2, [4], "red"),
        ],
        notes=[
            ("Monitored services expose counters and histograms on a lightweight /metrics endpoint, while engineers query aggregated time series and define alert expressions.", "noteb"),
            "Running the alerting pipeline and a dead-man's switch in an isolated failure domain ensures that outages in production services do not silence alarms.",
        ],
    )


def ch24_architecture():
    f = Fig(
        "ch24_architecture",
        "Figure 24-2. Collection Agents, Sharded TSDB Ingesters, Object-Store Blocks, and Alert Evaluator.",
        566,
    )
    # Control Plane (Top)
    f.zone(
        MARGIN, 0, INNER, 140, "purple",
        "Control Plane (Service Discovery, Alert Registry & Independent Watchdog)",
        "Isolated monitoring infrastructure · Zero shared dependency with monitored hosts",
        icon="settings_suggest", dashed=True,
    )
    c1 = f.node(
        MARGIN + 18, 56, 256, 68, "purple",
        [("Target Discovery", "name"), ("Lists /metrics endpoints", "sub")],
        icon="dns", kind="card", icon_size=26,
    )
    c2 = f.node(
        MARGIN + 298, 56, 260, 68, "purple",
        [("Alert Rule Registry", "name"), ("PromQL rules & silences", "sub")],
        icon="rule", kind="card", icon_size=26,
    )
    c3 = f.node(
        MARGIN + 582, 56, 256, 68, "red",
        [("Dead-Man Watchdog", "name"), ("Pages if monitor stalls", "sub")],
        icon="shield", kind="card", icon_size=26,
    )

    # Data Plane (Bottom)
    f.zone(
        MARGIN, 174, INNER, 384, "blue",
        "Data Plane (Sharded TSDB Ingestion, Tiered Object Storage & Alert Evaluation)",
        "WAL + in-memory head blocks absorb high sample rates before flushing immutable 2h blocks",
        icon="layers",
    )

    # Row 1: Scrape -> Distribute -> Ingest
    ag = f.node(
        MARGIN + 18, 232, 206, 82, "teal",
        [("Collection Agents", "name"), ("Scrape /metrics (10s)", "sub")],
        icon="developer_board", kind="card", icon_size=24,
    )
    dist = f.node(
        MARGIN + 258, 232, 196, 82, "blue",
        [("Write Distributor", "name"), ("Hash(series) shard", "sub")],
        icon="call_split", kind="card", icon_size=24,
    )
    ing = f.node(
        MARGIN + 488, 232, 350, 82, "blue",
        [("Sharded TSDB Ingesters", "name"), ("WAL + Gorilla head chunks (3x rep)", "sub")],
        icon="memory", kind="card", icon_size=26,
    )

    # Row 2: Object Store <- Compactor | Query Engine
    obj = f.node(
        MARGIN + 18, 354, 260, 82, "amber",
        [("Object-Store Blocks", "name"), ("Immutable 2h TSDB blocks", "sub")],
        icon="inventory_2", kind="card", icon_size=24,
    )
    comp = f.node(
        MARGIN + 308, 354, 240, 82, "purple",
        [("Compactor & Rollups", "name"), ("5m & 1h downsampling", "sub")],
        icon="layers", kind="card", icon_size=24,
    )
    qfe = f.node(
        MARGIN + 578, 354, 260, 82, "teal",
        [("Query Engine (PromQL)", "name"), ("Merges RAM head + blocks", "sub")],
        icon="bolt", kind="card", icon_size=24,
    )

    # Row 3: Alert Evaluator -> Alertmanager
    evl = f.node(
        MARGIN + 18, 468, 396, 70, "red",
        [("Alert Evaluator (Pending -> Firing)", "name"), ("Evaluates rules every 30s; resists flapping", "sub")],
        icon="schedule", kind="card", icon_size=24,
    )
    am = f.node(
        MARGIN + 448, 468, 390, 70, "red",
        [("Alertmanager & Pager Routing", "name"), ("Groups alerts, inhibits noise, pages SRE", "sub")],
        icon="notifications_active", kind="mid", icon_size=24,
    )

    # Control Plane -> Data Plane dashed wires
    f.wire([c1.bottom(0), (c1.cx, 158), (ag.cx, 158), ag.top(0)], tone="purple", dash=True, width=1.6)
    f.label(144, 156, "Targets", tone="purple", cls="small")

    f.wire([c2.bottom(0), (c2.cx, 158), (MARGIN + 468, 158), (MARGIN + 468, 452), (evl.cx + 110, 452), evl.top(110)],
           tone="purple", dash=True, width=1.5)
    f.label(486, 156, "Alert rules", tone="purple", cls="small")

    f.wire([am.right(0), (MARGIN + 850, am.cy), (MARGIN + 850, 158), (c3.cx, 158), c3.bottom(0)],
           tone="red", dash=True, width=1.5)
    f.label(752, 156, "Heartbeat", tone="red", cls="small")

    # Data Plane solid wires
    f.wire([ag.right(0), dist.left(0)], tone="teal", width=1.9)
    f.wire([dist.right(0), ing.left(0)], tone="blue", width=1.9)

    f.wire([ing.bottom(-90), (ing.cx - 90, 334), (obj.cx, 334), obj.top(0)], tone="amber", width=1.8)
    f.label(390, 332, "Flush 2h block", tone="amber", cls="small", back_cls="c-blue")

    f.wire([ing.bottom(70), (ing.cx + 70, 354)], tone="teal", width=1.8, tail=True)
    f.wire([obj.right(0), comp.left(0)], tone="purple", width=1.8, tail=True)
    f.wire([comp.right(0), qfe.left(0)], tone="teal", width=1.8)
    f.wire([qfe.bottom(0), (qfe.cx, 452), (evl.cx, 452), evl.top(0)], tone="red", width=1.8)
    f.wire([evl.right(0), am.left(0)], tone="red", width=1.9)

    return f.save([
        ("Sharding ingestion by series label set lets each TSDB ingester append compressed chunks sequentially in memory before flushing immutable blocks to object storage.", "noteb"),
        "Downsampling preserves long-term retention budgets, while keeping the raw alert path independent of production systems prevents blind outages.",
    ])


def ch24_tsdb_ingestion():
    f = Fig(
        "ch24_tsdb_ingestion",
        "Figure 24-3. Gorilla Delta-of-Delta Timestamp and XOR Value Compression Pipeline.",
        480,
    )
    # Top Panel: Delta-of-Delta Timestamp Compression
    f.zone(
        MARGIN, 0, INNER, 206, "blue",
        "1. Timestamp Compression: Delta-of-Delta (DoD) Bit Packing",
        "Regular 10-second scrape intervals yield D = 0, encoded in a single '0' bit",
        icon="schedule",
    )
    t1 = f.cell(MARGIN + 18, 58, 184, 72, "blue", [("Raw Timestamps", "name"), ("100, 110, 120", "mono"), ("64 bits each", "small")], kind="card", r=10)
    t2 = f.cell(MARGIN + 230, 58, 184, 72, "teal", [("First Delta (dt)", "name"), ("dt1=10, dt2=10", "mono"), ("t(n) - t(n-1)", "small")], kind="card", r=10)
    t3 = f.cell(MARGIN + 442, 58, 184, 72, "amber", [("Delta-of-Delta", "name"), ("D = dt2 - dt1 = 0", "monob"), ("Zero jitter", "small")], kind="card", r=10)
    t4 = f.cell(MARGIN + 654, 58, 184, 72, "green", [("Encoded Bits", "name"), ("Emit '0' (1 bit)", "monob"), ("64x reduction", "small")], kind="mid", r=10)

    f.wire([t1.right(0), t2.left(0)], tone="blue", width=1.8)
    f.wire([t2.right(0), t3.left(0)], tone="teal", width=1.8)
    f.wire([t3.right(0), t4.left(0)], tone="green", width=1.8)

    # Encoding table strip
    bins = [
        ("D = 0 -> '0' (1b)", "green", 184),
        ("[-63,64] -> '10'+7b", "teal", 196),
        ("[-255,256] -> '110'+9b", "blue", 214),
        ("Other -> '1111'+32b", "gray", 196),
    ]
    bx = MARGIN + 18
    for label, tone, bw in bins:
        f.cell(bx, 150, bw, 38, tone, [(label, "mono")], kind="tonal" if tone == "gray" else "card", r=8)
        bx += bw + 10

    # Bottom Panel: XOR Float64 Value Compression
    f.zone(
        MARGIN, 224, INNER, 248, "purple",
        "2. Float64 Value Compression: Bitwise XOR Window Encoding",
        "Adjacent readings share leading and trailing zero bits after IEEE-754 XOR",
        icon="bolt",
    )

    # Left: Bitwise XOR Example Card
    lx, ly, lw, lh = MARGIN + 18, 282, 412, 172
    f.rect(lx, ly, lw, lh, "card", r=12, lift=True)
    f.text(lx + 14, ly + 26, "IEEE-754 Bitwise XOR Trace", "name", "start", tone="purple", fit=(lx + 10, lx + lw - 10))
    xor_rows = [
        ("v(n-1) = 42.10  01000000 01000101 00001100 ...", "mono", None),
        ("v(n)   = 42.10  01000000 01000101 00001100 ...", "mono", None),
        ("XOR == 0    ->  emit '0'  (1 bit total)", "monob", "green"),
        ("v(n+1) = 42.15  01000000 01000101 00010011 ...", "mono", None),
        ("XOR != 0    ->  21 lead + 30 trail zeros", "monob", "amber"),
    ]
    for idx, (txt, cls, tone) in enumerate(xor_rows):
        f.text(lx + 14, ly + 56 + idx * 24, txt, cls, "start", tone=tone, fit=(lx + 10, lx + lw - 10))

    # Right: Three XOR Encoding Cases
    rx = lx + lw + 22
    rw = WIDTH - MARGIN - 18 - rx  # 386
    f.node(
        rx, 282, rw, 50, "green",
        [("Case A: XOR == 0 (Same Value)", "name"), ("Write control bit '0' (1 bit)", "mono")],
        kind="mid", r=10,
    )
    f.node(
        rx, 343, rw, 50, "teal",
        [("Case B: Fits Prior Zero Window", "name"), ("Write '10' + meaningful bits only", "mono")],
        kind="card", r=10,
    )
    f.node(
        rx, 404, rw, 50, "purple",
        [("Case C: New Zero Window", "name"), ("Write '11' + 5b lead + 6b len + bits", "mono")],
        kind="card", r=10,
    )

    f.wire([(lx + lw, 336), (rx, 307)], tone="green", width=1.6)
    f.wire([(lx + lw, 368), (rx, 368)], tone="teal", width=1.6)
    f.wire([(lx + lw, 404), (rx, 429)], tone="purple", width=1.6)

    return f.save([
        ("Combining delta-of-delta timestamp coding with XOR value packing shrinks each 16-byte raw sample to roughly 1.4 bytes on average in production time-series engines.", "noteb"),
        "High compression ratios allow hours of active series chunks to remain resident in RAM head blocks, sustaining low-latency queries and fast alert evaluation.",
    ])


ALL = [
    ch20_use_cases,
    ch20_architecture,
    ch20_seat_hold_cas,
    ch21_use_cases,
    ch21_architecture,
    ch21_spatial_dispatch,
    ch22_use_cases,
    ch22_architecture,
    ch22_trie_pipeline,
    ch23_use_cases,
    ch23_architecture,
    ch23_politeness_frontier,
    ch24_use_cases,
    ch24_architecture,
    ch24_tsdb_ingestion,
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
