#!/usr/bin/env python3
"""Generate spacious Material Design 3 light+dark SVG figures for Parts IV & V (Chapters 20-24).

Every figure uses WIDTH = 920, MARGIN = 32, INNER = 856 with generous padding,
concise labels, clean orthogonal wires, and clear control/data plane separation.
"""
from figkit_m3 import Fig, WIDTH, MARGIN, build_use_case_fig

INNER = WIDTH - 2 * MARGIN  # 856px usable width


def step_badge(f, cx, cy, num, tone="blue"):
    """Draw a crisp circular numbered step badge with paper halo (light + dark safe)."""
    f.add(
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="11.5" class="paper"/>'
        f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="9.5" class="a-{tone}"/>'
        f'<text x="{cx:.1f}" y="{cy + 3.8:.1f}" text-anchor="middle" class="badge paper">{num}</text>'
    )


def seg_mid(a, b, head=True, tail=False):
    """Exact visual midpoint of a wire segment a -> b accounting for 9px arrowheads."""
    if head and not tail:
        return (a + b - 9) / 2 if b > a else (a + b + 9) / 2
    if tail and not head:
        return (a + b + 9) / 2 if b > a else (a + b - 9) / 2
    return (a + b) / 2


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
            ("Deliver Settlement Webhook", "POST /v1/webhooks/payments", "teal", "notifications_active"),
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
        594,
    )
    # Control Plane (Top)
    f.zone(
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
        MARGIN + 582, 56, 250, 68, "teal",
        [("Lease Sweeper Worker", "name"), ("Frees timed-out holds", "sub")],
        icon="schedule", kind="card", icon_size=26,
    )

    # Data Plane (Bottom)
    f.zone(
        MARGIN, 174, INNER, 412, "blue",
        "Data Plane: Admission & Inventory",
        "Waiting room · Row-level CAS · Payment saga",
        icon="layers",
    )

    # Row 1: Ingress & Cache (48px badged gaps for clean badge spacing)
    buyer = f.node(
        MARGIN + 14, 232, 174, 76, "blue",
        [("Buyers (100k+)", "name"), ("Web & mobile", "small")],
        icon="person", kind="card", icon_size=22,
    )
    vwr = f.node(
        MARGIN + 236, 232, 178, 76, "amber",
        [("Waiting Room", "name"), ("Signed pass", "sub")],
        icon="hourglass_top", kind="card", icon_size=22,
    )
    gw = f.node(
        MARGIN + 462, 232, 174, 76, "teal",
        [("Booking API", "name"), ("Pass & key", "sub")],
        icon="swap_horiz", kind="card", icon_size=22,
    )
    cache = f.node(
        MARGIN + 670, 232, 172, 76, "gray",
        [("Seat Map CDN", "name"), ("Eventual reads", "sub")],
        icon="memory", kind="tonal", icon_size=22,
    )

    # Row 2: Inventory & Saga (48px gaps, aligned with Row 3)
    inv = f.node(
        MARGIN + 14, 360, 244, 78, "blue",
        [("Inventory Service", "name"), ("Conditional hold & CAS", "sub")],
        icon="inventory_2", kind="card", icon_size=24,
    )
    saga = f.node(
        MARGIN + 306, 360, 244, 78, "purple",
        [("Payment Saga Engine", "name"), ("Idempotent charge step", "sub")],
        icon="loop", kind="card", icon_size=24,
    )
    psp = f.node(
        MARGIN + 598, 360, 244, 78, "green",
        [("Payment Processor", "name"), ("Authorize, capture, refund", "sub")],
        icon="handshake", kind="card", icon_size=24,
    )

    # Row 3: Durable Stores (50px vertical gap below Row 2)
    db = f.node(
        MARGIN + 14, 488, 244, 72, "blue",
        [("Event-Sharded Seat DB", "name"), ("PK(show, seat) + ver", "mono")],
        icon="save", kind="mid", icon_size=22,
    )
    outbox = f.node(
        MARGIN + 306, 488, 244, 72, "purple",
        [("Saga Outbox & Journal", "name"), ("Durable step recovery", "sub")],
        icon="table_rows", kind="tonal", icon_size=22,
    )
    tkt = f.node(
        MARGIN + 598, 488, 244, 72, "green",
        [("Ticket Issuance Store", "name"), ("Immutable QR & order", "sub")],
        icon="description", kind="tonal", icon_size=22,
    )

    # Control Plane -> Data Plane dashed wires (clear of DP header)
    f.wire([c1.bottom(0), (c1.cx, 158), (vwr.cx, 158), vwr.top(0)], tone="purple", dash=True, width=1.6)
    f.label((c1.cx + vwr.cx) / 2, 156, "Admit rate", tone="purple", cls="small")

    f.wire([c2.bottom(0), (c2.cx, 158), (gw.cx, 158), gw.top(0)], tone="purple", dash=True, width=1.6)
    f.label((c2.cx + gw.cx) / 2, 156, "Shard map", tone="purple", cls="small")

    f.wire([c3.bottom(0), (c3.cx, 158), (880, 158), (880, 574), (db.cx, 574), db.bottom(0)],
           tone="teal", dash=True, width=1.5)
    f.label(810, 156, "Reclaim TTL", tone="teal", cls="small")

    # Data Plane synchronous critical path (solid)
    f.wire([buyer.right(0), vwr.left(0)], tone="blue", width=1.9)
    f.wire([vwr.right(0), gw.left(0)], tone="amber", width=1.9)
    f.wire([gw.right(0), cache.left(0)], tone="gray", dash=True, width=1.6)

    # Distinct parallel routing corridors (y=328 and y=344)
    f.wire([gw.bottom(-24), (gw.cx - 24, 328), (inv.cx, 328), inv.top(0)], tone="teal", width=1.9)
    f.label((inv.cx + gw.cx - 24) / 2 - 74, 326, "Hold / Confirm", tone="teal", cls="small", back_cls="c-blue")

    f.wire([gw.bottom(24), (gw.cx + 24, 344), (saga.cx, 344), saga.top(0)], tone="purple", width=1.9)
    f.wire([inv.right(0), saga.left(0)], tone="blue", width=1.8, tail=True)
    f.wire([saga.right(0), psp.left(0)], tone="green", width=1.9, tail=True)

    f.wire([inv.bottom(0), db.top(0)], tone="blue", width=1.9)
    f.wire([saga.bottom(0), outbox.top(0)], tone="purple", width=1.8)
    f.wire([psp.bottom(0), tkt.top(0)], tone="green", dash=True, width=1.8)

    # Symmetrically centered numbered step badges (1-6)
    step_badge(f, seg_mid(buyer.r, vwr.x, head=True), buyer.cy, 1, "blue")
    step_badge(f, seg_mid(vwr.r, gw.x, head=True), vwr.cy, 2, "amber")
    step_badge(f, seg_mid(inv.cx, gw.cx - 24, head=False), 328, 3, "teal")
    step_badge(f, inv.cx, seg_mid(inv.b, db.y, head=True), 4, "blue")
    step_badge(f, seg_mid(saga.r, psp.x, head=True, tail=True), saga.cy, 5, "green")
    step_badge(f, psp.cx, seg_mid(psp.b, tkt.y, head=True), 6, "green")

    return f.save([
        ("Solid wires trace the synchronous hold-and-checkout path (steps 1-5); dashed wires mark control-plane pacing, TTL reclamation, CDN reads, and async ticket issuance (6).", "noteb"),
        "Sharding inventory by event identifier keeps multi-seat holds inside a single database transaction while the virtual waiting room caps concurrent load.",
    ])


def ch20_seat_hold_cas():
    f = Fig(
        "ch20_seat_hold_cas",
        "Figure 20-3. Seat State Machine: Conditional Hold, TTL Lease Expiry, and Atomic Confirmation.",
        490,
    )
    # Top: State Machine Zone
    f.zone(
        MARGIN, 0, INNER, 236, "blue",
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

    # Forward transition wires (82px and 80px gaps)
    f.wire([s_avail.right(0), s_held.left(0)], tone="amber", width=2.0)
    f.label((s_avail.r + s_held.x) / 2, 102, "CAS Hold", tone="amber", cls="small", back_cls="c-blue")
    step_badge(f, seg_mid(s_avail.r, s_held.x, head=True), s_avail.cy, 1, "amber")

    f.wire([s_held.right(0), s_sold.left(0)], tone="blue", width=2.0)
    f.label((s_held.r + s_sold.x) / 2, 102, "CAS Confirm", tone="blue", cls="small", back_cls="c-blue")
    step_badge(f, seg_mid(s_held.r, s_sold.x, head=True), s_held.cy, 2, "blue")

    # Expiry return wire (301px horizontal segment)
    f.wire([s_held.bottom(0), (s_held.cx, 198), (s_avail.cx, 198), s_avail.bottom(0)],
           tone="red", dash=True, width=1.8)
    f.label((s_avail.cx + s_held.cx) / 2, 224, "TTL Expired or Payment Failed (Release)", tone="red", cls="small", back_cls="c-blue")
    step_badge(f, seg_mid(s_held.cx, s_avail.cx, head=False), 198, 3, "red")

    # Bottom Left: Atomic SQL CAS
    lw = 416
    f.zone(
        MARGIN, 256, lw, 226, "amber",
        "Atomic Conditional Hold (Single-Row CAS)",
        "Zero rows updated signals contention (HTTP 409)",
        icon="code",
    )
    f.rect(MARGIN + 16, 316, lw - 32, 146, "card", r=10, lift=True)
    code_lines = [
        ("UPDATE seats", "monob"),
        ("SET state = 'HELD', hold_id = $1,", "mono"),
        ("    expires_at = NOW() + INTERVAL '10m',", "mono"),
        ("    ver = ver + 1", "mono"),
        ("WHERE seat_id = $2 AND state = 'AVAIL'", "monob"),
        ("  AND ver = $3;  -- 1 row = win", "mono"),
    ]
    for idx, (txt, cls) in enumerate(code_lines):
        f.text(MARGIN + 28, 340 + idx * 20, txt, cls, "start",
               tone="amber" if cls == "monob" else None,
               fit=(MARGIN + 24, MARGIN + lw - 24))

    # Bottom Right: Late Payment Fencing (48px vertical gap for step 4)
    rx = MARGIN + lw + 24
    rw = WIDTH - MARGIN - rx  # 416
    f.zone(
        rx, 256, rw, 226, "red",
        "Late Payment Race & Fencing",
        "Expired lease rejects delayed payment confirmation",
        icon="shield",
    )
    f1 = f.node(
        rx + 18, 312, rw - 36, 56, "red",
        [("Buyer A Pays After Lease Expiry", "name"), ("t = t0 + 10m05s · Buyer B holds ver = v+3", "small")],
        icon="warning", kind="card", icon_size=22,
    )
    f2 = f.node(
        rx + 18, 416, rw - 36, 56, "green",
        [("Fenced Confirm Fails (0 Rows)", "name"), ("Predicate hold_id=A fails -> auto-refund", "small")],
        icon="shield", kind="card", icon_size=22,
    )
    f.wire([f1.bottom(0), f2.top(0)], tone="red", width=1.9)
    step_badge(f, f1.cx, seg_mid(f1.b, f2.y, head=True), 4, "red")

    return f.save([
        ("A conditional update on state, lease token, and monotonic version guarantees mutual exclusion without long-lived database row locks (steps 1-3).", "noteb"),
        "If a buyer completes payment after the lease expires, the confirmation predicate fails atomically and the saga issues a compensating refund (step 4).",
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
            ("Configure City Policy & Surge", "PUT /v1/regions/{city}/policies", "purple", "tune"),
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
        586,
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
        MARGIN, 174, INNER, 404, "blue",
        "Data Plane: Spatial & Dispatch",
        "In-RAM spatial index · Raft trip FSM",
        icon="layers",
    )

    # Track 1: Location Ingestion Plane (48px badged horizontal gaps; idx.cx + 36 == c3.cx == 742)
    drv = f.node(
        MARGIN + 14, 232, 184, 80, "teal",
        [("Driver Mobile", "name"), ("3s GPS ping", "sub")],
        icon="laptop", kind="card", icon_size=22,
    )
    ing = f.node(
        MARGIN + 246, 232, 212, 80, "teal",
        [("Location Gateway", "name"), ("Routes by cell ID", "sub")],
        icon="swap_horiz", kind="card", icon_size=22,
    )
    idx = f.node(
        MARGIN + 506, 232, 336, 80, "blue",
        [("Cell-Sharded Spatial Index (RAM)", "name"), ("Latest (lat, lon, ts) · TTL evicts stale", "sub")],
        icon="memory", kind="card", icon_size=26,
    )

    # Track 2: Dispatch & Durable State (48px horizontal gaps, 84px vertical drop to ETA)
    rdr = f.node(
        MARGIN + 14, 364, 184, 80, "blue",
        [("Rider Mobile", "name"), ("POST /v1/rides", "mono")],
        icon="person", kind="card", icon_size=22,
    )
    disp = f.node(
        MARGIN + 246, 364, 212, 80, "amber",
        [("Dispatch Engine", "name"), ("Ring search + FSM", "sub")],
        icon="call_split", kind="card", icon_size=22,
    )
    lock = f.node(
        MARGIN + 506, 352, 144, 72, "purple",
        [("Offer Lock", "name"), ("1 offer / drv", "small")],
        icon="lock", kind="card", icon_size=20,
    )
    trip = f.node(
        MARGIN + 698, 352, 144, 72, "green",
        [("Trip Store", "name"), ("Raft FSM", "small")],
        icon="save", kind="mid", icon_size=20,
    )
    eta = f.node(
        MARGIN + 506, 492, 336, 72, "gray",
        [("Road-Graph Routing & ETA Engine", "name"), ("Ranks top-K spatial candidates by drive time", "sub")],
        icon="schedule", kind="tonal", icon_size=24,
    )

    # Control Plane -> Data Plane dashed wires (clean orthogonal buses, symmetric +/-36 on idx)
    f.wire([c1.bottom(0), (c1.cx, 157), (ing.cx, 157), ing.top(0)], tone="purple", dash=True, width=1.6)
    f.label((c1.cx + ing.cx) / 2, 160, "Cell map", tone="purple", cls="small")

    f.wire([c2.bottom(0), (c2.cx, 157), (idx.cx - 36, 157), idx.top(-36)], tone="purple", dash=True, width=1.6)
    f.label((c2.cx + idx.cx - 36) / 2, 160, "Policy", tone="purple", cls="small")

    f.wire([idx.top(36), c3.bottom(0)], tone="teal", dash=True, width=1.6)
    f.label(c3.cx + 46, 160, "Cell counts", tone="teal", cls="small")

    # Data Plane wires (telemetry dashed, dispatch critical path solid)
    f.wire([drv.right(0), ing.left(0)], tone="teal", dash=True, width=1.8)
    f.wire([ing.right(0), idx.left(0)], tone="teal", dash=True, width=1.8)

    f.wire([rdr.right(0), disp.left(0)], tone="blue", width=1.9)
    f.wire([disp.top(0), (disp.cx, 336), (idx.cx, 336), idx.bottom(0)], tone="blue", width=1.8, tail=True)
    f.label(458, 326, "Query cells", tone="blue", cls="small", back_cls="c-blue")

    f.wire([disp.right(-16), lock.left(0)], tone="purple", width=1.8)
    f.wire([lock.right(0), trip.left(0)], tone="green", width=1.8)
    f.wire([disp.bottom(0), (disp.cx, eta.cy), eta.left(0)], tone="amber", width=1.8, tail=True)
    f.label((disp.cx + eta.x) / 2, eta.cy - 12, "Rank ETA", tone="amber", cls="small", back_cls="c-blue")

    # Symmetrically centered numbered step badges (1-6)
    step_badge(f, seg_mid(drv.r, ing.x, head=True), drv.cy, 1, "teal")
    step_badge(f, seg_mid(ing.r, idx.x, head=True), ing.cy, 2, "teal")
    step_badge(f, seg_mid(rdr.r, disp.x, head=True), rdr.cy, 3, "blue")
    step_badge(f, seg_mid(disp.cx, idx.cx, head=False), 336, 4, "blue")
    step_badge(f, disp.cx, seg_mid(disp.b, eta.cy, head=False, tail=True), 5, "amber")
    step_badge(f, seg_mid(lock.r, trip.x, head=True), lock.cy, 6, "green")

    return f.save([
        ("Dashed wires carry high-frequency GPS telemetry (steps 1-2) and control-plane policies; solid wires trace synchronous ride matching, ETA ranking, and Raft trip commits (3-6).", "noteb"),
        "Separating volatile GPS updates from durable trip storage prevents high-frequency writes from saturating consensus logs.",
    ])


def ch21_spatial_dispatch():
    f = Fig(
        "ch21_spatial_dispatch",
        "Figure 21-3. Hierarchical Spatial Cell Ring Expansion and Exclusive Driver Offer Protocol.",
        520,
    )
    # Left panel: 3x3 Spatial Cell Grid + Ring Expansion
    lw = 414
    f.zone(
        MARGIN, 0, lw, 512, "teal",
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

    n1 = f.node(
        MARGIN + 18, 306, lw - 36, 66, "blue",
        [("1. Read Center + 8 Neighbors", "name"), ("Captures drivers right across cell borders", "sub")],
        icon="view_module", kind="card", icon_size=24,
    )
    n2 = f.node(
        MARGIN + 18, 420, lw - 36, 66, "teal",
        [("2. Escalate to Ring 2 or Parent", "name"), ("Adaptive radius handles low-density suburbs", "sub")],
        icon="layers", kind="card", icon_size=24,
    )
    f.wire([n1.bottom(0), n2.top(0)], tone="teal", width=1.9)
    step_badge(f, n1.cx, seg_mid(n1.b, n2.y, head=True), 1, "teal")

    # Right panel: Exclusive Driver Offer Protocol (48px badged vertical gaps)
    rx = MARGIN + lw + 24
    rw = WIDTH - MARGIN - rx  # 418
    f.zone(
        rx, 0, rw, 512, "amber",
        "Exclusive Driver Offer Protocol",
        "Serialized 15-second leases prevent dual assignment",
        icon="handshake",
    )
    p1 = f.node(
        rx + 18, 60, rw - 36, 68, "blue",
        [("1. Rank Top-K by Road ETA", "name"), ("Sorted list: [D1 (2m), D2 (3m), D3 (5m)]", "sub")],
        icon="bolt", kind="card", icon_size=22,
    )
    p2 = f.node(
        rx + 18, 176, rw - 36, 68, "amber",
        [("2. Lock D1 & Send Offer #1", "name"), ("Atomic lease: driver D1 locked for 15s", "sub")],
        icon="lock", kind="card", icon_size=22,
    )
    p3 = f.node(
        rx + 18, 292, rw - 36, 68, "red",
        [("3. Timeout / Decline Releases D1", "name"), ("No reply at 15s -> release lock, advance", "sub")],
        icon="timer", kind="mid", icon_size=22,
    )
    p4 = f.node(
        rx + 18, 408, rw - 36, 78, "green",
        [("4. Offer #2 -> D2 Accepts (CAS)", "name"), ("Ride = MATCHED · D2 = EN_ROUTE", "mono")],
        icon="handshake", kind="card", icon_size=22,
    )

    f.wire([p1.bottom(0), p2.top(0)], tone="blue", width=1.9)
    f.wire([p2.bottom(0), p3.top(0)], tone="amber", width=1.9)
    f.wire([p3.bottom(0), p4.top(0)], tone="green", width=1.9)

    step_badge(f, p1.cx, seg_mid(p1.b, p2.y, head=True), 2, "blue")
    step_badge(f, p2.cx, seg_mid(p2.b, p3.y, head=True), 3, "amber")
    step_badge(f, p3.cx, seg_mid(p3.b, p4.y, head=True), 4, "green")

    return f.save([
        ("Searching the rider cell together with all eight surrounding neighbors (step 1) guarantees that a nearby driver across a grid boundary is never missed.", "noteb"),
        "Holding an exclusive short-lived lease on each offered driver (steps 2-4) prevents two concurrent riders from matching the same vehicle simultaneously.",
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
        590,
    )
    # Control & Offline Build Plane (Top)
    f.zone(
        MARGIN, 0, INNER, 264, "purple",
        "Control & Offline Build Plane (Aggregation, Filtering & Snapshot Rollout)",
        "Batch pipeline decouples write-heavy counting from read-only edge serving nodes",
        icon="settings_suggest", dashed=True,
    )
    # Row 1: 48px badged gaps (qlog->agg, bldr->flt) and 38px unbadged gap (agg->bldr)
    qlog = f.node(
        MARGIN + 14, 58, 172, 72, "teal",
        [("Query Log", "name"), ("Sampled logs", "sub")],
        icon="description", kind="card", icon_size=22,
    )
    agg = f.node(
        MARGIN + 234, 58, 176, 72, "purple",
        [("Aggregator", "name"), ("Counts + decay", "sub")],
        icon="loop", kind="card", icon_size=22,
    )
    bldr = f.node(
        MARGIN + 448, 58, 172, 72, "amber",
        [("Trie Builder", "name"), ("Top-K / node", "sub")],
        icon="code", kind="card", icon_size=22,
    )
    flt = f.node(
        MARGIN + 668, 58, 174, 72, "red",
        [("Safety Filter", "name"), ("Blocklist scrub", "sub")],
        icon="shield", kind="card", icon_size=22,
    )

    snap = f.node(
        MARGIN + 118, 174, 296, 72, "purple",
        [("Immutable Snapshot Store", "name"), ("Versioned trie blobs (v108)", "sub")],
        icon="inventory_2", kind="card", icon_size=24,
    )
    ctrl = f.node(
        MARGIN + 462, 174, 296, 72, "purple",
        [("Snapshot Rollout Controller", "name"), ("Canary check & atomic swap", "sub")],
        icon="swap_horiz", kind="card", icon_size=24,
    )

    # Offline async batch wires (dashed; 44px vertical corridor y=130..174)
    f.wire([qlog.right(0), agg.left(0)], tone="teal", dash=True, width=1.8)
    f.wire([agg.right(0), bldr.left(0)], tone="purple", dash=True, width=1.8)
    f.wire([bldr.right(0), flt.left(0)], tone="amber", dash=True, width=1.8)
    f.wire([flt.bottom(0), (flt.cx, 152), (snap.cx, 152), snap.top(0)], tone="purple", dash=True, width=1.8)
    f.wire([snap.right(0), ctrl.left(0)], tone="purple", dash=True, width=1.8)

    # Data Plane (Bottom)
    f.zone(
        MARGIN, 302, INNER, 280, "blue",
        "Online Data Plane (Edge Query Path: Read-Only, < 20 ms p99)",
        "Debounced keystrokes hit CDN cache first, then prefix-sharded in-memory trie replicas",
        icon="layers",
    )
    # Row 1: equal 48px badged horizontal gaps
    cli = f.node(
        MARGIN + 14, 362, 170, 82, "blue",
        [("Browser / App", "name"), ("Debounce + seq", "small")],
        icon="laptop", kind="card", icon_size=22,
    )
    cdn = f.node(
        MARGIN + 232, 362, 172, 82, "green",
        [("CDN Cache", "name"), ("Hot 1-2 chars", "small")],
        icon="bolt", kind="card", icon_size=22,
    )
    rtr = f.node(
        MARGIN + 452, 362, 170, 82, "teal",
        [("Prefix Router", "name"), ("Shards a-z", "small")],
        icon="call_split", kind="card", icon_size=22,
    )
    trie = f.node(
        MARGIN + 670, 362, 172, 82, "blue",
        [("In-RAM Trie", "name"), ("O(L) lookup", "small")],
        icon="memory", kind="card", icon_size=22,
    )

    guard = f.node(
        MARGIN + 14, 494, 396, 68, "amber",
        [("Client Out-of-Order Guard", "name"), ("Discards late replies when response_seq < latest_seq", "sub")],
        icon="rule", kind="tonal", icon_size=24,
    )
    swap = f.node(
        MARGIN + 438, 494, 404, 68, "purple",
        [("Double-Buffered Atomic Swap", "name"), ("Loads v108 beside v107, flips read pointer lock-free", "sub")],
        icon="swap_horiz", kind="tonal", icon_size=24,
    )

    # Control -> Data Plane dashed wire (aligned to trie.cx, centered in 38px inter-zone gap)
    f.wire([ctrl.bottom(0), (ctrl.cx, 283), (trie.cx, 283), trie.top(0)], tone="purple", dash=True, width=1.8)
    f.label((ctrl.cx + trie.cx) / 2, 286, "Push v108", tone="purple", cls="small")

    # Data Plane synchronous critical path (solid)
    f.wire([cli.right(0), cdn.left(0)], tone="blue", width=1.9)
    f.wire([cdn.right(0), rtr.left(0)], tone="green", width=1.9)
    f.wire([rtr.right(0), trie.left(0)], tone="teal", width=1.9)

    # Symmetric helper links connecting lower mechanism cards directly to cli & trie (50px corridor)
    f.wire([cli.bottom(0), (cli.cx, 469), (guard.cx, 469), guard.top(0)], tone="amber", dash=True, width=1.5)
    f.wire([trie.bottom(0), (trie.cx, 469), (swap.cx, 469), swap.top(0)], tone="purple", dash=True, width=1.5)

    # Symmetrically centered numbered step badges (1-3 online, 4-6 offline/rollout)
    step_badge(f, seg_mid(cli.r, cdn.x, head=True), cli.cy, 1, "blue")
    step_badge(f, seg_mid(cdn.r, rtr.x, head=True), cdn.cy, 2, "green")
    step_badge(f, seg_mid(rtr.r, trie.x, head=True), rtr.cy, 3, "teal")
    step_badge(f, seg_mid(qlog.r, agg.x, head=True), qlog.cy, 4, "teal")
    step_badge(f, seg_mid(bldr.r, flt.x, head=True), bldr.cy, 5, "amber")
    step_badge(f, trie.cx, seg_mid(302, trie.y, head=True), 6, "purple")

    return f.save([
        ("Solid wires trace the < 20 ms synchronous keystroke lookup path (steps 1-3); dashed wires mark the offline decay/build pipeline (4-5) and lock-free snapshot rollout (6).", "noteb"),
        "Client-side debouncing and sequence numbers prevent stale network responses from overwriting newer keystrokes in the search box.",
    ])


def ch22_trie_pipeline():
    f = Fig(
        "ch22_trie_pipeline",
        "Figure 22-3. Precomputed Top-K Prefix Trie Nodes and Exponential Frequency Decay.",
        490,
    )
    # Left panel: Precomputed Top-K Trie
    lw = 472
    f.zone(
        MARGIN, 0, lw, 482, "blue",
        "Precomputed Top-K Prefix Trie",
        "Each node stores its sorted Top-K completions for O(L) reads",
        icon="layers",
    )

    root = f.cell(MARGIN + 178, 56, 116, 36, "gray", [("Root (empty)", "monob")], kind="card", r=8)
    nk = f.cell(MARGIN + 150, 140, 172, 44, "teal", [("Node 'k'", "monob"), ("Top-3 cached", "small")], kind="card", r=8)

    # Highlighted 'ka' node card
    ka_x, ka_y, ka_w, ka_h = MARGIN + 22, 232, 224, 108
    ka_cx = ka_x + ka_w / 2
    f.rect(ka_x, ka_y, ka_w, ka_h, "card", r=12, lift=True)
    f.rect(ka_x, ka_y, ka_w, 28, "m-amber", r=10)
    f.text(ka_x + 12, ka_y + 19, "Node 'ka'  (Query Match)", "monob", "start", tone="amber", fit=(ka_x + 8, ka_x + ka_w - 8))
    f.text(ka_x + 14, ka_y + 49, "1. kafka           940", "mono", "start", fit=(ka_x + 10, ka_x + ka_w - 10))
    f.text(ka_x + 14, ka_y + 70, "2. kayak           610", "mono", "start", fit=(ka_x + 10, ka_x + ka_w - 10))
    f.text(ka_x + 14, ka_y + 91, "3. karma           420", "mono", "start", fit=(ka_x + 10, ka_x + ka_w - 10))

    # Sibling 'ki' node
    ki_x, ki_y, ki_w, ki_h = MARGIN + 268, 232, 184, 88
    ki_cx = ki_x + ki_w / 2
    f.rect(ki_x, ki_y, ki_w, ki_h, "c-gray", r=10)
    f.text(ki_x + 12, ki_y + 23, "Node 'ki'", "monob", "start", fit=(ki_x + 8, ki_x + ki_w - 8))
    f.text(ki_x + 12, ki_y + 46, "1. kindle     530", "mono", "start", fit=(ki_x + 8, ki_x + ki_w - 8))
    f.text(ki_x + 12, ki_y + 68, "2. kicad      280", "mono", "start", fit=(ki_x + 8, ki_x + ki_w - 8))

    # Child 'kaf' node (48px below 'ka')
    kaf_x, kaf_y, kaf_w, kaf_h = MARGIN + 22, 388, 224, 80
    kaf_cx = kaf_x + kaf_w / 2
    f.rect(kaf_x, kaf_y, kaf_w, kaf_h, "card", r=10, lift=True)
    f.text(kaf_x + 12, kaf_y + 22, "Node 'kaf'", "monob", "start", tone="green", fit=(kaf_x + 8, kaf_x + kaf_w - 8))
    f.text(kaf_x + 12, kaf_y + 45, "1. kafka streams   480", "mono", "start", fit=(kaf_x + 8, kaf_x + kaf_w - 8))
    f.text(kaf_x + 12, kaf_y + 66, "2. kafka connect   310", "mono", "start", fit=(kaf_x + 8, kaf_x + kaf_w - 8))

    # Trie edges: root -> nk (48px), symmetric 1-to-2 split nk -> (ka, ki), ka -> kaf (48px)
    f.wire([root.bottom(0), nk.top(0)], tone="teal", width=1.9)
    y_split = (nk.b + ka_y) / 2  # 208.0
    f.wire([nk.bottom(0), (nk.cx, y_split)], tone="teal", head=False, width=1.8)
    f.wire([(nk.cx, y_split), (ka_cx, y_split), (ka_cx, ka_y)], tone="amber", width=2.0)
    f.wire([(nk.cx, y_split), (ki_cx, y_split), (ki_cx, ki_y)], tone="gray", width=1.6)
    f.wire([(ka_cx, ka_y + ka_h), (kaf_cx, kaf_y)], tone="green", width=1.9)

    # Numbered lookup badges (1-3)
    step_badge(f, root.cx, seg_mid(root.b, nk.y, head=True), 1, "teal")
    step_badge(f, seg_mid(nk.cx, ka_cx, head=False), y_split, 2, "amber")
    step_badge(f, ka_cx, seg_mid(ka_y + ka_h, kaf_y, head=True), 3, "green")

    f.node(
        MARGIN + 268, 388, 184, 80, "blue",
        [("Lookup Cost", "name"), ("O(L) pointer hops", "mono"), ("Zero subtree scan", "small")],
        kind="tonal", r=10,
    )

    # Right panel: Exponential Frequency Decay
    rx = MARGIN + lw + 22
    rw = WIDTH - MARGIN - rx  # 362
    f.zone(
        rx, 0, rw, 482, "purple",
        "Exponential Frequency Decay",
        "Recent surges outrank stale historical counts",
        icon="schedule",
    )

    # Formula Card
    f.rect(rx + 16, 58, rw - 32, 82, "card", r=10, lift=True)
    f.text(rx + 28, 81, "Weighted Score Recurrence", "name", "start", tone="purple", fit=(rx + 24, rx + rw - 24))
    f.text(rx + 28, 104, "S(t) = a * C(t) + (1 - a) * S(t-1)", "monob", "start", fit=(rx + 24, rx + rw - 24))
    f.text(rx + 28, 125, "Hourly decay a = 0.35 favors fresh trends", "small", "start", fit=(rx + 24, rx + rw - 24))

    # Decay weight bars (46px below Formula Card)
    f.rect(rx + 16, 186, rw - 32, 174, "card", r=10, lift=True)
    f.text(rx + 28, 209, "Relative Weight by Age (a = 0.35)", "name", "start", fit=(rx + 24, rx + rw - 24))
    bars = [
        ("Current hr", 1.00, "green"),
        ("t - 1 hr", 0.65, "teal"),
        ("t - 2 hr", 0.42, "blue"),
        ("t - 4 hr", 0.18, "gray"),
    ]
    bx0 = rx + 114
    bw_max = 152
    for idx, (lbl, weight, tone) in enumerate(bars):
        by = 224 + idx * 32
        f.text(rx + 28, by + 15, lbl, "small", "start", fit=(rx + 24, bx0 - 8))
        f.rect(bx0, by + 4, bw_max, 14, "c-gray", r=5)
        f.rect(bx0, by + 4, max(10, bw_max * weight), 14, f"a-{tone}", r=5)
        f.text(bx0 + bw_max + 10, by + 15, f"{weight:.2f}", "monob", "start", tone=tone, fit=(bx0 + bw_max + 6, rx + rw - 20))

    # Memory bound card (46px below Decay Bars)
    f.node(
        rx + 16, 406, rw - 32, 62, "amber",
        [("Bounded Memory Footprint", "name"), ("Cap prefix length <= 50; store Top-K only", "sub")],
        icon="memory", kind="card", icon_size=22,
    )

    # Numbered decay pipeline arrows (4-5)
    rcx = rx + rw / 2
    f.wire([(rcx, 140), (rcx, 186)], tone="purple", width=1.8)
    step_badge(f, rcx, seg_mid(140, 186, head=True), 4, "purple")
    f.wire([(rcx, 360), (rcx, 406)], tone="amber", width=1.8)
    step_badge(f, rcx, seg_mid(360, 406, head=True), 5, "amber")

    return f.save([
        ("Caching the Top-K ranked completions directly inside every trie node converts each keystroke into a fixed-depth pointer traversal (steps 1-3) with no subtree merge.", "noteb"),
        "Exponentially decaying historical query counts (steps 4-5) allows emerging events to surface in top suggestions within a single build cycle.",
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
        586,
    )
    # Control Plane (Top)
    f.zone(
        MARGIN, 0, INNER, 140, "purple",
        "Control Plane (Seed Coordinator, Host Rules & Robots Cache)",
        "Consistent-hash host ownership · robots.txt compliance · Crawl-trap defense",
        icon="settings_suggest", dashed=True,
    )
    c1 = f.node(
        MARGIN + 18, 56, 240, 68, "purple",
        [("Seed Coordinator", "name"), ("Assigns host partitions", "sub")],
        icon="edit_note", kind="card", icon_size=26,
    )
    c2 = f.node(
        MARGIN + 308, 56, 240, 68, "amber",
        [("Host Policy & Traps", "name"), ("Blocks infinite calendars", "sub")],
        icon="shield", kind="card", icon_size=26,
    )
    c3 = f.node(
        MARGIN + 598, 56, 240, 68, "teal",
        [("Robots & DNS Cache", "name"), ("TTL-cached rules & IPs", "sub")],
        icon="dns", kind="card", icon_size=26,
    )

    # Data Plane (Bottom) — concise header leaves x >= 260 completely clear
    f.zone(
        MARGIN, 174, INNER, 404, "blue",
        "Data Plane: Crawl Loop",
        "Per-host frontier · Dedup",
        icon="layers",
    )

    # Row 1: Frontier -> Fetch -> Origin (equal 50px horizontal gaps)
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
        [("External Web Hosts", "name"), ("Origin servers · 1 req/delay", "small")],
        icon="lan", kind="tonal", icon_size=26,
    )

    # Row 2: URL Seen <- Parse -> Deduplicator (exact vertical alignment, 48px vertical gap)
    seen = f.node(
        MARGIN + 18, 364, 240, 82, "purple",
        [("URL Seen Filter", "name"), ("Sharded Bloom + RocksDB", "sub")],
        icon="rule", kind="card", icon_size=26,
    )
    parse = f.node(
        MARGIN + 308, 364, 240, 82, "teal",
        [("HTML Parser", "name"), ("Extracts & normalizes URLs", "sub")],
        icon="code", kind="card", icon_size=26,
    )
    dedup = f.node(
        MARGIN + 598, 364, 240, 82, "green",
        [("Content Deduplicator", "name"), ("SimHash near-dup check", "sub")],
        icon="layers", kind="card", icon_size=26,
    )

    # Row 3: Durable Page Store (48px below Row 2)
    store = f.node(
        MARGIN + 308, 494, 530, 66, "green",
        [("Crawled Page Object Store & Indexer Feed", "name"), ("Stores unique pages · GET /v1/pages?after={cursor}", "mono")],
        icon="save", kind="mid", icon_size=24,
    )

    # Control Plane -> Data Plane dashed wires (zero header crossings, dead-straight on fetch & orig)
    f.wire([c1.bottom(0), (c1.cx, 157), (16, 157), (16, front.cy), front.left(0)], tone="purple", dash=True, width=1.6)
    f.label(93, 160, "Seeds", tone="purple", cls="small")

    f.wire([c2.bottom(0), fetch.top(0)], tone="amber", dash=True, width=1.6)
    f.label(c2.cx + 46, 160, "Trap rules", tone="amber", cls="small")

    f.wire([c3.bottom(0), orig.top(0)], tone="teal", dash=True, width=1.6, tail=True)
    f.label(c3.cx + 58, 160, "robots.txt / DNS", tone="teal", cls="small")

    # Data Plane solid wires (aligned to card midpoints)
    f.wire([front.right(0), fetch.left(0)], tone="amber", width=1.9)
    f.wire([fetch.right(0), orig.left(0)], tone="blue", width=1.9, tail=True)
    f.wire([fetch.bottom(0), parse.top(0)], tone="blue", width=1.9)
    f.label(fetch.cx + 58, 342, "HTML body", tone="blue", cls="small", back_cls="c-blue")

    f.wire([parse.left(0), seen.right(0)], tone="purple", width=1.9)
    f.wire([seen.top(0), front.bottom(0)], tone="purple", dash=True, width=1.8)
    f.label(seen.cx + 62, 342, "Unseen URLs", tone="purple", cls="small", back_cls="c-blue")

    f.wire([parse.right(0), dedup.left(0)], tone="teal", width=1.9)
    f.wire([dedup.bottom(0), (dedup.cx, 470), (store.cx, 470), store.top(0)], tone="green", width=1.9)

    # Symmetrically centered numbered step badges (1-6)
    step_badge(f, seg_mid(front.r, fetch.x, head=True), front.cy, 1, "amber")
    step_badge(f, seg_mid(fetch.r, orig.x, head=True, tail=True), fetch.cy, 2, "blue")
    step_badge(f, fetch.cx, seg_mid(fetch.b, parse.y, head=True), 3, "blue")
    step_badge(f, seg_mid(parse.x, seen.r, head=True), parse.cy, 4, "purple")
    step_badge(f, seg_mid(parse.r, dedup.x, head=True), parse.cy, 5, "teal")
    step_badge(f, seg_mid(dedup.cx, store.cx, head=False), 470, 6, "green")

    return f.save([
        ("Solid wires trace the active crawl loop (steps 1-6); dashed wires mark control-plane seeds, host policies, DNS/robots lookups, and async frontier feedback.", "noteb"),
        "Routing discovered URLs by hostname assigns each external domain to a single frontier shard, guaranteeing polite request spacing without global locks.",
    ])


def ch23_politeness_frontier():
    f = Fig(
        "ch23_politeness_frontier",
        "Figure 23-3. Mercator Two-Stage Frontier: Priority Front Queues and Per-Host Back Queues.",
        500,
    )
    # Stage 1: Front Queues (Left)
    s1_w = 244
    f.zone(
        MARGIN, 0, s1_w, 492, "purple",
        "Stage 1: Front Queues",
        "Orders URLs by importance",
        icon="tune",
    )
    prio = f.node(
        MARGIN + 14, 58, s1_w - 28, 58, "blue",
        [("URL Prioritizer", "name"), ("PageRank & age", "sub")],
        icon="bolt", kind="card", icon_size=22,
    )
    fq1 = f.cell(MARGIN + 14, 162, s1_w - 28, 48, "green", [("Front Queue P1 (High)", "monob"), ("News & root pages", "small")], kind="card", r=9)
    fq2 = f.cell(MARGIN + 14, 220, s1_w - 28, 48, "blue", [("Front Queue P2 (Med)", "monob"), ("Standard articles", "small")], kind="card", r=9)
    fq3 = f.cell(MARGIN + 14, 278, s1_w - 28, 48, "gray", [("Front Queue P3 (Low)", "monob"), ("Deep archive links", "small")], kind="tonal", r=9)

    sel = f.node(
        MARGIN + 14, 372, s1_w - 28, 68, "purple",
        [("Biased Selector", "name"), ("Draws P1 more often", "sub")],
        icon="call_split", kind="mid", icon_size=22,
    )

    f.wire([prio.bottom(0), fq1.top(0)], tone="purple", width=1.8)
    f.wire([fq3.bottom(0), sel.top(0)], tone="purple", width=1.8)

    # Stage 2: Per-Host Back Queues & Min-Heap (Right)
    s2_x = MARGIN + s1_w + 32  # 308
    s2_w = WIDTH - MARGIN - s2_x  # 580
    f.zone(
        s2_x, 0, s2_w, 492, "amber",
        "Stage 2: Per-Host Back Queues & Politeness Min-Heap",
        "Invariant: every back queue holds URLs for exactly one origin host",
        icon="schedule",
    )

    # Left column inside Stage 2: Back Queues + Mapping Table
    bq_x = s2_x + 20  # 328
    bq_w = 240
    bq1 = f.cell(bq_x, 62, bq_w, 60, "blue", [("Back Queue B1", "monob"), ("news.example (4 URLs)", "small")], kind="card", r=9)
    bq2 = f.cell(bq_x, 142, bq_w, 60, "teal", [("Back Queue B2", "monob"), ("wiki.example (7 URLs)", "small")], kind="card", r=9)
    bq3 = f.cell(bq_x, 222, bq_w, 60, "purple", [("Back Queue B3", "monob"), ("docs.example (2 URLs)", "small")], kind="card", r=9)

    hmap = f.node(
        bq_x, 344, bq_w, 124, "gray",
        [("Host-to-Queue Table", "name"), ("news.example -> B1", "mono"), ("wiki.example -> B2", "mono"), ("docs.example -> B3", "mono")],
        kind="card", r=10,
    )

    # Right column inside Stage 2: Min-Heap + Fetcher Dispatch + Re-insert (48px horizontal gap)
    hp_x = bq_x + bq_w + 48  # 616
    hp_w = s2_x + s2_w - 20 - hp_x  # 252
    f.rect(hp_x, 62, hp_w, 126, "card", r=12, lift=True)
    f.rect(hp_x, 62, hp_w, 30, "m-amber", r=10)
    f.text(hp_x + 12, 82, "Min-Heap (Next Fetch Time)", "monob", "start", tone="amber", fit=(hp_x + 8, hp_x + hp_w - 8))
    f.text(hp_x + 14, 112, "root -> B1  (t = 10.0s)", "monob", "start", tone="green", fit=(hp_x + 10, hp_x + hp_w - 10))
    f.text(hp_x + 14, 136, "next -> B2  (t = 11.5s)", "mono", "start", fit=(hp_x + 10, hp_x + hp_w - 10))
    f.text(hp_x + 14, 160, "next -> B3  (t = 14.2s)", "mono", "start", fit=(hp_x + 10, hp_x + hp_w - 10))

    disp = f.node(
        hp_x, 236, hp_w, 78, "green",
        [("Fetcher Worker Pop", "name"), ("Wait until now >= t_min", "sub")],
        icon="play_arrow", kind="card", icon_size=24,
    )
    reins = f.node(
        hp_x, 362, hp_w, 106, "amber",
        [("Politeness Re-Insert", "name"), ("t_next = now + delay", "mono"), ("Refill B1 if empty", "small")],
        icon="timer", kind="mid", icon_size=24,
    )

    # Straight horizontal wire Stage 1 -> Stage 2 (sel.cy == hmap.cy == 406, 66px long)
    f.wire([sel.right(0), hmap.left(0)], tone="purple", width=1.9)
    f.wire([hmap.top(0), bq3.bottom(0)], tone="purple", dash=True, width=1.8)

    # Wire Back Queues -> Min-Heap -> Fetcher -> Re-Insert
    f.wire([bq1.right(0), (hp_x, bq1.cy)], tone="blue", width=1.8)
    f.wire([bq2.right(0), (hp_x, bq2.cy)], tone="teal", width=1.8)
    f.wire([(hp_x + hp_w / 2, 188), disp.top(0)], tone="green", width=1.9)
    f.wire([disp.bottom(0), reins.top(0)], tone="amber", width=1.9)
    f.wire([reins.right(0), (s2_x + s2_w - 8, reins.cy), (s2_x + s2_w - 8, 125), (hp_x + hp_w, 125)],
           tone="amber", dash=True, width=1.7)

    # Symmetrically centered numbered step badges (1-7)
    step_badge(f, prio.cx, seg_mid(prio.b, fq1.y, head=True), 1, "purple")
    step_badge(f, fq3.cx, seg_mid(fq3.b, sel.y, head=True), 2, "purple")
    step_badge(f, seg_mid(sel.r, hmap.x, head=True), sel.cy, 3, "purple")
    step_badge(f, hmap.cx, seg_mid(hmap.y, bq3.b, head=True), 4, "purple")
    step_badge(f, seg_mid(bq1.r, hp_x, head=True), bq1.cy, 5, "blue")
    step_badge(f, hp_x + hp_w / 2, seg_mid(188, disp.y, head=True), 6, "green")
    step_badge(f, disp.cx, seg_mid(disp.b, reins.y, head=True), 7, "amber")

    return f.save([
        ("Separating priority front queues (steps 1-3) from per-host back queues (4-5) resolves the conflict between crawling high-value pages first and respecting per-host politeness.", "noteb"),
        "A min-heap keyed by each back queue's earliest permissible fetch timestamp (steps 6-7) guarantees at most one concurrent request per host without scanning idle queues.",
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
        598,
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
        MARGIN + 582, 56, 250, 68, "red",
        [("Dead-Man Watchdog", "name"), ("Pages if monitor stalls", "sub")],
        icon="shield", kind="card", icon_size=26,
    )

    # Data Plane (Bottom) — concise header leaves x >= 300 completely clear
    f.zone(
        MARGIN, 174, INNER, 416, "blue",
        "Data Plane: TSDB & Alerting",
        "WAL head · 2h blocks · PromQL",
        icon="layers",
    )

    # Row 1: Scrape -> Distribute -> Ingest (48px badged gaps, clean vertical spine x=496)
    ag = f.node(
        MARGIN + 14, 238, 192, 76, "teal",
        [("Host Agents", "name"), ("Scrape /metrics", "small")],
        icon="developer_board", kind="card", icon_size=22,
    )
    dist = f.node(
        MARGIN + 254, 238, 186, 76, "blue",
        [("Write Distributor", "name"), ("Hash(series)", "sub")],
        icon="call_split", kind="card", icon_size=22,
    )
    ing = f.node(
        MARGIN + 488, 238, 354, 76, "blue",
        [("Sharded TSDB Ingesters", "name"), ("WAL + Gorilla head chunks (3x rep)", "sub")],
        icon="memory", kind="card", icon_size=24,
    )

    # Row 2: Object Store <-> Compactor -> Query Engine (56px below Row 1, aligned spine x=496)
    obj = f.node(
        MARGIN + 14, 370, 192, 76, "amber",
        [("Object Store (S3)", "name"), ("2h blocks", "small")],
        icon="inventory_2", kind="card", icon_size=22,
    )
    comp = f.node(
        MARGIN + 254, 370, 186, 76, "purple",
        [("Compactor", "name"), ("5m & 1h rollups", "small")],
        icon="layers", kind="card", icon_size=22,
    )
    qfe = f.node(
        MARGIN + 488, 370, 354, 76, "teal",
        [("Query Engine (PromQL)", "name"), ("Merges RAM head + object blocks", "sub")],
        icon="bolt", kind="card", icon_size=24,
    )

    # Row 3: Alert Evaluator -> Alertmanager (54px below Row 2, 48px horizontal gap)
    evl = f.node(
        MARGIN + 14, 500, 390, 70, "red",
        [("Alert Evaluator (Pending -> Firing)", "name"), ("Evaluates rules every 30s; resists flapping", "sub")],
        icon="schedule", kind="card", icon_size=24,
    )
    am = f.node(
        MARGIN + 452, 500, 390, 70, "red",
        [("Alertmanager & Pager Routing", "name"), ("Groups alerts, inhibits noise, pages SRE", "sub")],
        icon="notifications_active", kind="mid", icon_size=24,
    )

    # Control Plane -> Data Plane dashed wires (zero header or card crossings, symmetric on evl)
    f.wire([c1.bottom(0), (c1.cx, 157), (16, 157), (16, ag.cy), ag.left(0)],
           tone="purple", dash=True, width=1.6)
    f.label(97, 160, "Targets", tone="purple", cls="small")

    f.wire([c2.bottom(0), (c2.cx, 157), (496, 157), (496, 462), (evl.cx - 28, 462), evl.top(-28)],
           tone="purple", dash=True, width=1.5)
    f.label(536, 160, "Alert rules", tone="purple", cls="small")

    f.wire([am.right(0), (880, am.cy), (880, 157), (c3.cx, 157), c3.bottom(0)],
           tone="red", dash=True, width=1.5)
    f.label(809, 160, "Heartbeat", tone="red", cls="small")

    # Data Plane wires (sync critical path solid, async flush dashed; symmetric +/-28 on ing & evl)
    f.wire([ag.right(0), dist.left(0)], tone="teal", width=1.9)
    f.wire([dist.right(0), ing.left(0)], tone="blue", width=1.9)

    f.wire([ing.bottom(-28), (ing.cx - 28, 342), (obj.cx, 342), obj.top(0)], tone="amber", dash=True, width=1.8)
    f.label(270, 332, "Flush 2h block", tone="amber", cls="small", back_cls="c-blue")

    f.wire([ing.bottom(28), qfe.top(28)], tone="teal", width=1.8, tail=True)
    f.wire([obj.right(0), comp.left(0)], tone="purple", dash=True, width=1.7, tail=True)
    f.wire([comp.right(0), qfe.left(0)], tone="teal", width=1.8)
    f.wire([qfe.bottom(0), (qfe.cx, 480), (evl.cx + 28, 480), evl.top(28)], tone="red", width=1.8)
    f.wire([evl.right(0), am.left(0)], tone="red", width=1.9)

    # Symmetrically centered numbered step badges (1-6)
    step_badge(f, seg_mid(ag.r, dist.x, head=True), ag.cy, 1, "teal")
    step_badge(f, seg_mid(dist.r, ing.x, head=True), dist.cy, 2, "blue")
    step_badge(f, seg_mid(obj.cx, ing.cx - 28, head=False), 342, 3, "amber")
    step_badge(f, ing.cx + 28, seg_mid(ing.b, qfe.y, head=True, tail=True), 4, "teal")
    step_badge(f, 585, 480, 5, "red")
    step_badge(f, seg_mid(evl.r, am.x, head=True), evl.cy, 6, "red")

    return f.save([
        ("Solid wires trace metric ingestion, live PromQL reads, and alerting (steps 1-2, 4-6); dashed wires mark 2h block flushes (3), compaction, rule sync, and the dead-man heartbeat.", "noteb"),
        "Sharding ingestion by series label set lets each TSDB ingester append compressed chunks sequentially in memory before flushing immutable blocks to object storage.",
    ])


def ch24_tsdb_ingestion():
    f = Fig(
        "ch24_tsdb_ingestion",
        "Figure 24-4. Gorilla Delta-of-Delta Timestamp and XOR Value Compression Pipeline.",
        480,
    )
    # Top Panel: Delta-of-Delta Timestamp Compression (48px badged horizontal gaps)
    f.zone(
        MARGIN, 0, INNER, 206, "blue",
        "1. Timestamp Compression: Delta-of-Delta (DoD) Bit Packing",
        "Regular 10-second scrape intervals yield D = 0, encoded in a single '0' bit",
        icon="schedule",
    )
    t1 = f.cell(MARGIN + 14, 58, 171, 72, "blue", [("Raw Timestamps", "name"), ("100, 110, 120", "mono"), ("64 bits each", "small")], kind="card", r=10)
    t2 = f.cell(MARGIN + 233, 58, 171, 72, "teal", [("First Delta (dt)", "name"), ("dt1=10, dt2=10", "mono"), ("t(n) - t(n-1)", "small")], kind="card", r=10)
    t3 = f.cell(MARGIN + 452, 58, 171, 72, "amber", [("Delta-of-Delta", "name"), ("D = dt2-dt1 = 0", "monob"), ("Zero jitter", "small")], kind="card", r=10)
    t4 = f.cell(MARGIN + 671, 58, 171, 72, "green", [("Encoded Bits", "name"), ("Emit '0' (1 bit)", "monob"), ("64x reduction", "small")], kind="mid", r=10)

    f.wire([t1.right(0), t2.left(0)], tone="blue", width=1.9)
    f.wire([t2.right(0), t3.left(0)], tone="teal", width=1.9)
    f.wire([t3.right(0), t4.left(0)], tone="green", width=1.9)

    step_badge(f, seg_mid(t1.r, t2.x, head=True), t1.cy, 1, "blue")
    step_badge(f, seg_mid(t2.r, t3.x, head=True), t2.cy, 2, "teal")
    step_badge(f, seg_mid(t3.r, t4.x, head=True), t3.cy, 3, "green")

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
    lx, ly, lw, lh = MARGIN + 16, 282, 396, 172
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

    # Right: Three XOR Encoding Cases (68px gap for symmetric 1-to-3 fan-out)
    rx = lx + lw + 68  # 512
    rw = WIDTH - MARGIN - 16 - rx  # 360
    ca = f.node(
        rx, 282, rw, 50, "green",
        [("Case A: XOR == 0 (Same Value)", "name"), ("Write control bit '0' (1 bit)", "mono")],
        kind="mid", r=10,
    )
    cb = f.node(
        rx, 343, rw, 50, "teal",
        [("Case B: Fits Prior Zero Window", "name"), ("Write '10' + meaningful bits only", "mono")],
        kind="card", r=10,
    )
    cc = f.node(
        rx, 404, rw, 50, "purple",
        [("Case C: New Zero Window", "name"), ("Write '11' + 5b lead + 6b len + bits", "mono")],
        kind="card", r=10,
    )

    # Symmetric 1-to-3 orthogonal fan-out at exact horizontal midpoint x_mid = (lx + lw + rx) / 2
    x_src = lx + lw  # 444
    x_mid = (x_src + rx) / 2  # 478.0
    f.wire([(x_src, cb.cy), (x_mid, cb.cy)], tone="purple", head=False, width=1.8)
    f.wire([(x_mid, cb.cy), (x_mid, ca.cy), ca.left(0)], tone="green", width=1.8)
    f.wire([(x_mid, cb.cy), cb.left(0)], tone="teal", width=1.8)
    f.wire([(x_mid, cb.cy), (x_mid, cc.cy), cc.left(0)], tone="purple", width=1.8)
    step_badge(f, x_mid, cb.cy, 4, "purple")

    return f.save([
        ("Combining delta-of-delta timestamp coding (steps 1-3) with XOR value packing (step 4) shrinks each 16-byte raw sample to roughly 1.4 bytes on average in production time-series engines.", "noteb"),
        "High compression ratios allow hours of active series chunks to remain resident in RAM head blocks, sustaining low-latency queries and fast alert evaluation.",
    ])


def ch24_distributed_agents():
    f = Fig(
        "ch24_distributed_agents",
        "Figure 24-3. Distributed Host Fleet, Local Collection Agents, Service Discovery, and Pull vs. Push Ingestion.",
        536,
    )

    # Top Control Plane: Service Discovery
    f.zone(
        MARGIN, 0, INNER, 108, "purple",
        "Control Plane: Service Discovery (Kubernetes / Consul / EC2 Tags)",
        "Watches host & pod IP churn; streams active scrape target lists to sharded collectors",
        icon="settings_suggest", dashed=True,
    )
    sd = f.node(
        MARGIN + 220, 48, 416, 48, "purple",
        [("Target Discovery Watch API", "name"), ("Consistent-hash shard assignment · zero static IP lists", "small")],
        icon="tune", kind="card", icon_size=22,
    )

    # Left Column: Distributed Production Hosts (3 distinct hosts across AZs)
    hx = MARGIN
    hw = 272
    f.zone(
        hx, 154, hw, 344, "blue",
        "Production Host Fleet",
        "App processes + local agents",
        icon="dns",
    )
    h1 = f.node(
        hx + 12, 214, hw - 24, 78, "blue",
        [("Host 1 (AZ-A · Agent)", "name"), (":9090/metrics · exporter", "small"), ("eBPF + /proc ring buffer", "small")],
        icon="developer_board", kind="card", icon_size=22,
    )
    h2 = f.node(
        hx + 12, 308, hw - 24, 78, "blue",
        [("Host 2 (AZ-B · Agent)", "name"), (":9090/metrics · OTel", "small"), ("Local disk queue on split", "small")],
        icon="developer_board", kind="card", icon_size=22,
    )
    h3 = f.node(
        hx + 12, 402, hw - 24, 78, "amber",
        [("Host 3 (Batch Job)", "name"), ("Exits before scrape tick", "sub"), ("Pushes OTLP / gateway", "small")],
        icon="bolt", kind="card", icon_size=22,
    )

    # Middle Column: Sharded Collector & Push Gateway Tier (56px gap from hosts)
    cx = hx + hw + 56  # 360
    cw = 238
    f.zone(
        cx, 154, cw, 344, "teal",
        "Sharded Collectors",
        "Pull scrapers + push ingest",
        icon="swap_horiz",
    )
    pull_c = f.node(
        cx + 12, 232, cw - 24, 118, "teal",
        [("Pull Scraper Shard", "name"), ("GET /metrics (15s)", "small"), ("Jittered scrape offsets", "small"), ("Detects host UP/DOWN", "small")],
        icon="schedule", kind="card", icon_size=22,
    )
    push_c = f.node(
        cx + 12, 402, cw - 24, 78, "amber",
        [("Push / OTLP Ingest", "name"), ("gRPC / HTTP2 batches", "small"), ("Short-lived jobs & edge", "small")],
        icon="play_arrow", kind="card", icon_size=22,
    )

    # Right Column: Isolated TSDB & Alerting Plane (56px gap from collectors)
    tx = cx + cw + 56  # 654
    tw = WIDTH - MARGIN - tx  # 234
    f.zone(
        tx, 154, tw, 344, "green",
        "Isolated TSDB Plane",
        "Separate failure domain",
        icon="layers",
    )
    ing = f.node(
        tx + 12, 232, tw - 24, 118, "green",
        [("TSDB Ingesters", "name"), ("Remote Write (Snappy)", "small"), ("WAL + Gorilla RAM head", "small"), ("3x quorum replication", "small")],
        icon="save", kind="mid", icon_size=22,
    )
    alrt = f.node(
        tx + 12, 402, tw - 24, 78, "red",
        [("Alert Evaluator", "name"), ("Dead-man & up==0", "small"), ("Pages SRE on outage", "small")],
        icon="notifications_active", kind="card", icon_size=22,
    )

    # 1. Control plane -> Sharded Collector (dead-straight vertical down at collector center)
    f.wire([(cx + cw / 2, sd.b), (cx + cw / 2, 154)], tone="purple", dash=True, width=1.8)
    step_badge(f, cx + cw / 2, seg_mid(sd.b, 154, head=True), 1, "purple")
    f.label(cx + cw / 2 + 78, 128, "SD target list", tone="purple", cls="small")

    # 2. Symmetric 2-to-1 Pull Scrape bus between Host 1 / Host 2 and Pull Scraper Shard
    x_mid_1 = (hx + hw + cx) / 2  # 340.0
    f.wire([pull_c.left(0), (x_mid_1, pull_c.cy)], tone="teal", width=1.9, head=False)
    f.wire([(x_mid_1, h1.cy), (x_mid_1, h2.cy)], tone="teal", width=1.9, head=False)
    f.wire([(x_mid_1, h1.cy), h1.right(0)], tone="teal", width=1.9, tail=True)
    f.wire([(x_mid_1, h2.cy), h2.right(0)], tone="teal", width=1.9, tail=True)
    step_badge(f, x_mid_1, pull_c.cy, 2, "teal")
    f.label(x_mid_1, 200, "Pull /metrics", tone="teal", cls="small")

    # 3. Dead-straight horizontal Push wire from Host 3 -> Push Gateway
    f.wire([h3.right(0), push_c.left(0)], tone="amber", width=1.9)
    step_badge(f, seg_mid(h3.r, push_c.x, head=True), h3.cy, 3, "amber")

    # 4. Dead-straight horizontal Remote Write from Pull Scraper -> TSDB Ingesters
    f.wire([pull_c.right(0), ing.left(0)], tone="green", width=1.9)
    step_badge(f, seg_mid(pull_c.r, ing.x, head=True), pull_c.cy, 4, "green")

    # 5. Clean orthogonal Remote Write from Push Gateway -> TSDB Ingesters (exact midpoint corridor)
    x_mid_2 = (cx + cw + tx) / 2  # 640.0
    f.wire([push_c.right(0), (x_mid_2, push_c.cy), (x_mid_2, ing.cy + 28), ing.left(28)], tone="amber", dash=True, width=1.7)
    step_badge(f, x_mid_2, 376, 5, "amber")

    # 6. Dead-straight vertical wire from TSDB Ingesters -> Alert Evaluator
    f.wire([ing.bottom(0), alrt.top(0)], tone="red", width=1.9)
    step_badge(f, ing.cx, seg_mid(ing.b, alrt.y, head=True), 6, "red")

    return f.save([
        ("Service Discovery (1) assigns hosts across sharded scrapers so Pull agents (2) sample /metrics on a jittered schedule and immediately detect silent host death (up == 0), while short-lived batch jobs push via OTLP (3).", "noteb"),
        "Collectors batch and compress samples into Snappy/Protobuf Remote Write streams (4-5) to an isolated TSDB and Alerting plane (6), buffering locally on disk if the monitoring network partitions.",
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
    ch24_distributed_agents,
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
