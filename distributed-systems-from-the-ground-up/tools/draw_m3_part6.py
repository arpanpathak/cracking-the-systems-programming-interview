#!/usr/bin/env python3
"""Generate 12 spacious Material Design 3 light+dark SVG figures for Part VI (Chapters 25-28).

Every figure prioritizes generous whitespace, concise crisp labels, zero text
overflow in Chrome/Safari, and clear separation of control and data planes.
"""
from figkit_m3 import Fig, WIDTH, MARGIN, build_use_case_fig

INNER = WIDTH - 2 * MARGIN  # 856px usable width


# =============================================================================
# CHAPTER 25: CLOUD FILE SYNCHRONIZATION SERVICE
# =============================================================================

def ch25_use_cases():
    return build_use_case_fig(
        "ch25_use_cases",
        "Figure 25-1. Actors and Use Cases of the Cloud File Synchronization Service.",
        "System Boundary: Cloud File Synchronization Service",
        "Content-addressed chunking · Delta sync · Multi-device conflict isolation",
        actors=[
            ("Desktop / Mobile Client", "Local watcher & sync agent", "blue", "laptop"),
            ("Collaborator Device", "Shared folder subscriber", "teal", "person"),
            ("Storage Operator", "GC & quota administrator", "purple", "engineering"),
        ],
        cases=[
            ("Upload Changed File Chunks", "PUT /v1/blocks/{sha256} (CDC)", "blue", "save"),
            ("Commit File Manifest Version", "PUT /v1/files/{id}  If-Match: <ver>", "amber", "description"),
            ("Subscribe to Delta Change Feed", "GET /v1/changes?cursor=<seq>", "teal", "notifications_active"),
            ("Branch Conflicting Offline Edits", "Preserve diverged revision copy", "red", "call_split"),
            ("Garbage-Collect Orphan Blocks", "Mark-and-sweep unreferenced chunks", "purple", "tune"),
        ],
        links=[
            (0, [0, 1, 3], "blue"),
            (1, [2, 3], "teal"),
            (2, [4], "purple"),
        ],
        notes=[
            ("Sync clients separate immutable block uploads from conditional metadata commits so interrupted transfers never corrupt live file versions.", "noteb"),
            "When two offline devices modify the same base version, the service branches the second upload into a conflict copy rather than overwriting user data.",
        ],
    )


def ch25_architecture():
    f = Fig(
        "ch25_architecture",
        "Figure 25-2. Sync Metadata Service, Content-Addressed Block Store, and Delta Notification Bus.",
        544,
    )
    # Top-left: Sync Clients
    cli_zone = f.zone(
        MARGIN, 0, 264, 152, "blue",
        "Client Sync Agents",
        "Desktop & mobile watchers",
        icon="laptop",
    )
    cli = f.node(
        MARGIN + 16, 60, 232, 76, "blue",
        [("CDC & Merkle Agent", "name"), ("Watch FS · Diff chunks", "sub")],
        icon="folder", kind="card", icon_size=26,
    )

    # Top-right: Control Plane
    cp_x = 338
    cp_w = WIDTH - MARGIN - cp_x  # 550
    f.zone(
        cp_x, 0, cp_w, 152, "purple",
        "Control Plane (Metadata, CAS & Garbage Collection)",
        "Namespace authority · Optimistic version checks · Block reference counting",
        icon="settings_suggest", dashed=True,
    )
    meta_api = f.node(
        cp_x + 16, 60, 250, 76, "purple",
        [("Metadata & CAS API", "name"), ("Manifest commits · ACLs", "sub")],
        icon="dns", kind="card", icon_size=26,
    )
    gc_ctrl = f.node(
        cp_x + 284, 60, 250, 76, "purple",
        [("GC & Quota Sweeper", "name"), ("Mark-and-sweep orphans", "sub")],
        icon="tune", kind="card", icon_size=26,
    )

    # Middle Row: Block Gateway, Delta Notification Bus, Metadata Store
    gw_zone = f.zone(
        MARGIN, 194, 264, 140, "teal",
        "Data Plane: Block Gateway",
        "SHA-256 verify · Deduplication",
        icon="swap_horiz",
    )
    gw = f.node(
        MARGIN + 16, 252, 232, 66, "teal",
        [("Chunk Ingress Tier", "name"), ("Pre-signed PUT / GET", "sub")],
        icon="bolt", kind="card", icon_size=24,
    )

    bus_zone = f.zone(
        338, 194, 264, 140, "amber",
        "Delta Notification Bus",
        "Per-folder cursor fanout",
        icon="notifications_active",
    )
    bus = f.node(
        354, 252, 232, 66, "amber",
        [("Push & Long-Poll Edge", "name"), ("Wake subscribed devices", "sub")],
        icon="lan", kind="card", icon_size=24,
    )

    mdb_zone = f.zone(
        624, 194, 264, 140, "purple",
        "Metadata Store (3-AZ)",
        "Serializable ACID quorum",
        icon="table_rows",
    )
    mdb = f.node(
        640, 252, 232, 66, "purple",
        [("Files & Change Cursors", "name"), ("files · chunks · seq_log", "mono")],
        kind="card",
    )

    # Bottom Row: Content-Addressed Block Store
    store_zone = f.zone(
        MARGIN, 374, INNER, 162, "blue",
        "Data Plane: Content-Addressed Block Store (Multi-AZ Object Storage)",
        "Immutable chunk payloads keyed by SHA-256 digest enable global deduplication and lock-free retries",
        icon="layers",
    )
    f.node(
        MARGIN + 16, 434, 260, 84, "blue",
        [("Immutable Chunk Store", "name"), ("key = sha256(bytes)", "mono"), ("Erasure-coded across AZs", "small")],
        icon="inventory_2", kind="card", icon_size=26,
    )
    f.node(
        MARGIN + 298, 434, 260, 84, "teal",
        [("Edge Download Cache", "name"), ("Hot shared file blocks", "sub"), ("Zero-copy range reads", "small")],
        icon="memory", kind="card", icon_size=26,
    )
    f.node(
        MARGIN + 580, 434, 260, 84, "gray",
        [("Delayed Sweep Archive", "name"), ("Unreferenced > 30 days", "sub"), ("Safe tombstone retention", "small")],
        icon="schedule", kind="card", icon_size=26,
    )

    # Orthogonal wires (zero crossings)
    f.wire([cli_zone.bottom(-40), (cli_zone.cx - 40, gw_zone.y)], tone="blue", width=2.0, tail=True)
    f.label(cli_zone.cx - 40, 178, "Chunk PUT / GET", tone="blue", cls="small")

    f.wire([cli.right(0), meta_api.left(0)], tone="purple", width=1.9, tail=True)
    f.label(318, 86, "CAS", tone="purple", cls="small")

    f.wire([meta_api.bottom(40), (meta_api.cx + 40, 174), (mdb_zone.cx - 42, 174), (mdb_zone.cx - 42, mdb_zone.y)],
           tone="purple", width=1.8, tail=True)

    f.wire([gc_ctrl.bottom(42), (gc_ctrl.cx + 42, mdb_zone.y)], tone="purple", dash=True, width=1.6, tail=True)

    f.wire([mdb_zone.left(0), bus_zone.right(0)], tone="amber", width=1.9)

    f.wire([bus_zone.top(-46), (bus_zone.cx - 46, 174), (cli_zone.cx + 58, 174), (cli_zone.cx + 58, cli_zone.b)],
           tone="amber", dash=True, width=1.8)
    f.label(342, 178, "Delta wake", tone="amber", cls="small")

    f.wire([gw_zone.bottom(0), (gw_zone.cx, store_zone.y)], tone="teal", width=2.0, tail=True)
    f.label(gw_zone.cx + 68, 358, "SHA-256 blocks", tone="teal", cls="small")

    f.wire([mdb_zone.bottom(0), (mdb_zone.cx, store_zone.y)], tone="purple", dash=True, width=1.6)
    f.label(mdb_zone.cx - 72, 358, "Orphan sweep", tone="purple", cls="small")

    return f.save([
        ("Separating metadata CAS commits (control plane) from immutable SHA-256 block transfers (data plane) keeps storage horizontally scalable.", "noteb"),
        "Clients upload missing chunks directly to the block gateway, then issue a single conditional metadata commit that appends a monotonic entry to the delta notification bus.",
    ])


def ch25_merkle_cdc():
    f = Fig(
        "ch25_merkle_cdc",
        "Figure 25-3. Content-Defined Chunking (CDC), Merkle Tree Diffing, and Conflict Branching.",
        430,
    )
    # Top Band: Fixed vs Content-Defined Chunking
    f.zone(
        MARGIN, 0, INNER, 178, "teal",
        "1. Content-Defined Chunking (Rolling Hash Prevents Boundary Shifts)",
        "Inserting 1 byte at offset 0 shifts every fixed-size block but alters only the first CDC chunk",
        icon="view_week",
    )

    # Left half: Fixed-Size Cuts
    f.text(MARGIN + 18, 66, "Fixed-Size Cuts (4 KB stride): 4 of 4 chunks dirty", "name", "start", tone="red", fit=(MARGIN + 14, 452))
    fixed_labels = [("C1' dirty", "red"), ("C2' dirty", "red"), ("C3' dirty", "red"), ("C4' dirty", "red")]
    for i, (lbl, tone) in enumerate(fixed_labels):
        cx = MARGIN + 18 + i * 100
        f.cell(cx, 78, 92, 46, tone, [(lbl, "monob"), ("Re-upload", "small")], kind="mid", r=8)
    f.text(MARGIN + 18, 152, "100% bandwidth re-transmitted on prepend", "small", "start", tone="red")

    # Divider
    f.rule(460, 56, 460, 166, tone="gray", width=1.2, dash="4 4")

    # Right half: Content-Defined Cuts
    f.text(478, 66, "FastCDC Cuts (hash mod 2^13 == 0): 1 of 4 dirty", "name", "start", tone="green", fit=(474, WIDTH - MARGIN - 10))
    cdc_labels = [
        ("C1' dirty", "Upload", "amber", "mid"),
        ("C2 same", "Deduped", "green", "card"),
        ("C3 same", "Deduped", "green", "card"),
        ("C4 same", "Deduped", "green", "card"),
    ]
    for i, (lbl, sub, tone, knd) in enumerate(cdc_labels):
        cx = 478 + i * 98
        f.cell(cx, 78, 90, 46, tone, [(lbl, "monob"), (sub, "small")], kind=knd, r=8)
    f.text(478, 152, "Anchor bytes restore alignment; 75% skipped", "small", "start", tone="green")

    # Bottom-left: Merkle Tree Diffing
    f.zone(
        MARGIN, 198, 416, 224, "blue",
        "2. Merkle Tree Diffing (O(log N) Sync)",
        "Prune matching subtrees; transfer only changed leaves",
        icon="call_split",
    )
    root = f.cell(174, 256, 132, 34, "amber", [("Root v4 != v3", "monob")], kind="mid", r=8)
    h01 = f.cell(62, 314, 152, 36, "green", [("H(C1,C2) Match", "monob")], kind="card", r=8)
    h23 = f.cell(264, 314, 154, 36, "amber", [("H(C3',C4) Diff", "monob")], kind="mid", r=8)
    c3 = f.cell(240, 374, 98, 34, "red", [("C3' Upload", "monob")], kind="mid", r=8)
    c4 = f.cell(346, 374, 88, 34, "green", [("C4 Same", "monob")], kind="card", r=8)
    f.pill(138, 379, "Subtree skipped", tone="green", anchor="middle")

    f.wire([root.bottom(-24), (216, 302), (h01.cx, 302), h01.top(0)], tone="green", width=1.6)
    f.wire([root.bottom(24), (264, 302), (h23.cx, 302), h23.top(0)], tone="amber", width=1.6)
    f.wire([h23.bottom(-24), (317, 362), (c3.cx, 362), c3.top(0)], tone="red", width=1.6)
    f.wire([h23.bottom(24), (365, 362), (c4.cx, 362), c4.top(0)], tone="green", width=1.6)

    # Bottom-right: Conflict Branching
    rx = 472
    rw = WIDTH - MARGIN - rx  # 416
    f.zone(
        rx, 198, rw, 224, "amber",
        "3. Offline Conflict Branching (Zero Loss)",
        "Optimistic CAS rejects stale parent version cleanly",
        icon="warning",
    )
    base = f.cell(rx + 18, 294, 108, 62, "blue", [("Base v3", "name"), ("Shared", "small")], kind="card", r=10)
    win = f.node(rx + 158, 258, 240, 62, "green", [
        ("Laptop CAS(v3 -> v4)", "monob"),
        ("200 OK · Mainline v4", "small"),
    ], kind="card", r=10)
    lose = f.node(rx + 158, 338, 240, 68, "red", [
        ("Phone CAS(v3 -> v4)", "monob"),
        ("409 Conflict -> Fork copy", "small"),
    ], kind="mid", r=10)

    f.wire([base.right(-14), (rx + 142, base.cy - 14), (rx + 142, win.cy), win.left(0)], tone="green", width=1.8)
    f.wire([base.right(14), (rx + 142, base.cy + 14), (rx + 142, lose.cy), lose.left(0)], tone="red", width=1.8)

    return f.save([
        ("Content-defined chunking aligns boundaries to local byte patterns rather than fixed offsets, preventing cascading re-uploads after small insertions.", "noteb"),
        "Merkle tree comparison isolates modified blocks in logarithmic round trips, while optimistic CAS converts concurrent offline edits into explicit conflict copies.",
    ])


# =============================================================================
# CHAPTER 26: REAL-TIME COLLABORATIVE DOCUMENT EDITOR
# =============================================================================

def ch26_use_cases():
    return build_use_case_fig(
        "ch26_use_cases",
        "Figure 26-1. Actors and Use Cases of the Real-Time Collaborative Document Editor.",
        "System Boundary: Real-Time Collaborative Editor",
        "Sequence CRDT convergence · WebSocket fanout · Versioned snapshots",
        actors=[
            ("Co-Author Browser", "Local CRDT state & cursor", "blue", "laptop"),
            ("Offline Mobile Editor", "Buffered local op queue", "amber", "edit_note"),
            ("Document Admin", "ACL, audit & restore", "purple", "shield"),
        ],
        cases=[
            ("Apply Concurrent Text Edits", "WS /v1/docs/{id}/ops (CRDT delta)", "blue", "edit_note"),
            ("Broadcast Presence & Cursors", "Ephemeral selection & caret state", "teal", "notifications_active"),
            ("Reconnect & Reconcile Offline Ops", "Exchange state vector & missing ops", "amber", "loop"),
            ("Restore Historical Snapshot", "GET /v1/docs/{id}/revisions/{ver}", "green", "schedule"),
            ("Enforce Sharing & Role ACLs", "PATCH /v1/docs/{id}/permissions", "purple", "lock"),
        ],
        links=[
            (0, [0, 1, 3], "blue"),
            (1, [0, 2], "amber"),
            (2, [3, 4], "purple"),
        ],
        notes=[
            ("Local edits execute immediately against the client-side CRDT replica so typing latency stays under 16 ms regardless of network RTT.", "noteb"),
            "Offline mobile editors queue deltas locally and exchange compact state vectors upon reconnection to merge without central locking.",
        ],
    )


def ch26_architecture():
    f = Fig(
        "ch26_architecture",
        "Figure 26-2. Session Coordinator, Collaboration Gateways, Operation Log, and Snapshot Store.",
        544,
    )
    # Top-left: Co-Author Clients
    cli_zone = f.zone(
        MARGIN, 0, 264, 150, "blue",
        "Co-Author Clients",
        "Browser & mobile CRDT replicas",
        icon="laptop",
    )
    cli = f.node(
        MARGIN + 16, 58, 232, 76, "blue",
        [("Local CRDT Engine", "name"), ("0 ms local apply · Queue", "sub")],
        icon="edit_note", kind="card", icon_size=26,
    )

    # Top-right: Control Plane
    cp_x = 338
    cp_w = WIDTH - MARGIN - cp_x  # 550
    f.zone(
        cp_x, 0, cp_w, 150, "purple",
        "Control Plane (Session Routing & Access Control)",
        "Sticky document-to-gateway placement · Fencing epochs · Live ACL revocation",
        icon="settings_suggest", dashed=True,
    )
    coord = f.node(
        cp_x + 16, 58, 250, 76, "purple",
        [("Session Coordinator", "name"), ("Consistent doc_id lease", "sub")],
        icon="dns", kind="card", icon_size=26,
    )
    acl = f.node(
        cp_x + 284, 58, 250, 76, "purple",
        [("ACL & Auth Service", "name"), ("RBAC scopes · Revoke", "sub")],
        icon="shield", kind="card", icon_size=26,
    )

    # Middle Tier: Collaboration Gateways
    gw_zone = f.zone(
        MARGIN, 192, INNER, 150, "teal",
        "Data Plane: Sticky Collaboration Gateways (Partitioned by doc_id)",
        "All active editors of a document converge on a single gateway shard for low-latency delta fanout",
        icon="swap_horiz",
    )
    pod_a = f.node(
        MARGIN + 16, 250, 258, 76, "teal",
        [("Gateway Pod A (doc_42)", "name"), ("WS fanout · Op buffer", "sub")],
        icon="bolt", kind="card", icon_size=26,
    )
    pod_b = f.node(
        MARGIN + 298, 250, 258, 76, "teal",
        [("Gateway Pod B (doc_99)", "name"), ("In-RAM CRDT merge", "sub")],
        icon="memory", kind="card", icon_size=26,
    )
    pres = f.node(
        MARGIN + 580, 250, 260, 76, "amber",
        [("Presence & Pub/Sub Bus", "name"), ("Cursors · Cross-AZ relay", "sub")],
        icon="notifications_active", kind="card", icon_size=26,
    )

    # Bottom Tier: Durable Operation Log & Snapshot Store
    dur_zone = f.zone(
        MARGIN, 384, INNER, 152, "blue",
        "Data Plane: Durable Operation Log and Snapshot Compaction Tier",
        "Appends every CRDT delta durably before compaction folds long histories into fast-loading checkpoints",
        icon="layers",
    )
    oplog = f.node(
        MARGIN + 16, 442, 258, 76, "amber",
        [("Append-Only Op Log", "name"), ("Keyed by doc_id · 3-AZ", "sub")],
        icon="table_rows", kind="card", icon_size=26,
    )
    comp = f.node(
        MARGIN + 298, 442, 258, 76, "green",
        [("Snapshot Compactor", "name"), ("Async fold every N ops", "sub")],
        icon="loop", kind="card", icon_size=26,
    )
    snap = f.node(
        MARGIN + 580, 442, 260, 76, "blue",
        [("Snapshot Object Store", "name"), ("Compressed CRDT state", "sub")],
        icon="inventory_2", kind="card", icon_size=26,
    )

    # Clean orthogonal wires (zero crossings)
    f.wire([cli_zone.bottom(0), (cli_zone.cx, gw_zone.y)], tone="blue", width=2.0, tail=True)
    f.label(cli_zone.cx + 76, 174, "WS deltas + carets", tone="blue", cls="small")

    f.wire([cli.right(0), coord.left(0)], tone="purple", dash=True, width=1.7, tail=True)
    f.label(318, 86, "Route", tone="purple", cls="small")

    f.wire([coord.bottom(0), (coord.cx, gw_zone.y)], tone="purple", dash=True, width=1.7)
    f.label(coord.cx + 66, 174, "Pod lease", tone="purple", cls="small")

    f.wire([acl.bottom(0), (acl.cx, gw_zone.y)], tone="purple", dash=True, width=1.7)
    f.label(acl.cx - 64, 174, "ACL revoke", tone="purple", cls="small")

    f.wire([pod_a.bottom(0), (pod_a.cx, dur_zone.y)], tone="amber", width=2.0)
    f.label(pod_a.cx + 76, 366, "Persist op delta", tone="amber", cls="small")

    f.wire([oplog.right(0), comp.left(0)], tone="amber", width=1.8)
    f.wire([comp.right(0), snap.left(0)], tone="green", width=1.8)

    f.wire([(snap.cx, dur_zone.y), (snap.cx, gw_zone.b)], tone="teal", dash=True, width=1.8)
    f.label(snap.cx - 76, 366, "Cold doc hydrate", tone="teal", cls="small")

    return f.save([
        ("Pinning active document sessions to a sticky collaboration gateway minimizes fanout hops while keeping ephemeral presence out of durable storage.", "noteb"),
        "On cold open or failover, a gateway hydrates the latest compressed snapshot from object storage and replays only the trailing tail of the append-only operation log.",
    ])


def ch26_crdt_convergence():
    f = Fig(
        "ch26_crdt_convergence",
        "Figure 26-3. Concurrent Edits Converging via Sequence CRDT Identifiers and Causal Broadcast.",
        466,
    )
    # Top Band: Initial Shared State
    f.zone(
        MARGIN, 0, INNER, 92, "blue",
        "1. Shared Base Sequence on Both Replicas (Immutable Anchor Identifiers)",
        "Each character carries a globally unique (lamport_clock, site_id) key rather than a mutable array index",
        icon="code",
    )
    init_cells = [
        ("HEAD", "start", "gray", "tonal"),
        ("(1, 1)  'A'", "anchor", "blue", "card"),
        ("(2, 1)  'C'", "anchor", "blue", "card"),
        ("TAIL", "end", "gray", "tonal"),
    ]
    ix = MARGIN + 104
    for idx, (lbl, sub, tone, knd) in enumerate(init_cells):
        c = f.cell(ix + idx * 172, 50, 132, 32, tone, [(lbl, "monob")], kind=knd, r=8)
        if idx < 3:
            f.wire([c.right(0), (ix + (idx + 1) * 172, c.cy)], tone="blue", width=1.6)

    # Middle Band: Two Concurrent Replicas with Causal Broadcast in Center
    lw = 384
    rx = WIDTH - MARGIN - lw  # 504
    f.zone(
        MARGIN, 112, lw, 208, "teal",
        "2a. Replica A (site_id = 1)",
        "Inserts 'B' after (1,1) while offline",
        icon="laptop",
    )
    a1 = f.node(MARGIN + 16, 170, lw - 32, 58, "green", [
        ("Local op1: Ins('B', after=(1,1))", "monob"),
        ("Assigned id = (3, 1) -> \"ABC\"", "small"),
    ], kind="card", r=10)
    a2 = f.node(MARGIN + 16, 244, lw - 32, 60, "amber", [
        ("Receive op2: id = (3, 2) 'X'", "monob"),
        ("Tie-break (3,2) > (3,1) -> \"AXBC\"", "small"),
    ], kind="card", r=10)

    f.zone(
        rx, 112, lw, 208, "purple",
        "2b. Replica B (site_id = 2)",
        "Concurrently inserts 'X' after (1,1)",
        icon="laptop",
    )
    b1 = f.node(rx + 16, 170, lw - 32, 58, "amber", [
        ("Local op2: Ins('X', after=(1,1))", "monob"),
        ("Assigned id = (3, 2) -> \"AXC\"", "small"),
    ], kind="card", r=10)
    b2 = f.node(rx + 16, 244, lw - 32, 60, "green", [
        ("Receive op1: id = (3, 1) 'B'", "monob"),
        ("Tie-break (3,2) > (3,1) -> \"AXBC\"", "small"),
    ], kind="card", r=10)

    # Non-crossing causal broadcast wires in the 88px center corridor (x=416..504)
    f.wire([(MARGIN + lw, 198), (rx, 198)], tone="green", dash=True, width=1.8)
    f.label(460, 190, "op1 (3,1)", tone="green", cls="small")
    f.wire([(rx, 274), (MARGIN + lw, 274)], tone="amber", dash=True, width=1.8)
    f.label(460, 266, "op2 (3,2)", tone="amber", cls="small")

    # Bottom Band: Converged State
    f.zone(
        MARGIN, 340, INNER, 118, "green",
        "3. Converged Sequence State on Both Replicas (Strong Eventual Consistency)",
        "Deterministic total order on (clock, site_id) guarantees identical \"AXBC\" regardless of arrival order",
        icon="play_arrow",
    )
    final_cells = [
        ("HEAD", "gray", "tonal"),
        ("(1,1) 'A'", "blue", "card"),
        ("(3,2) 'X'", "amber", "mid"),
        ("(3,1) 'B'", "green", "mid"),
        ("(2,1) 'C'", "blue", "card"),
        ("TAIL", "gray", "tonal"),
    ]
    fx = MARGIN + 20
    cw = 118
    fgap = 22
    for idx, (lbl, tone, knd) in enumerate(final_cells):
        c = f.cell(fx + idx * (cw + fgap), 396, cw, 38, tone, [(lbl, "monob")], kind=knd, r=8)
        if idx < len(final_cells) - 1:
            f.wire([c.right(0), (fx + (idx + 1) * (cw + fgap), c.cy)], tone="green", width=1.6)

    f.pill(WIDTH - MARGIN - 16, 352, "Commutative · Idempotent", tone="green", anchor="end")

    return f.save([
        ("Because sequence CRDT operations reference immutable anchor identifiers rather than volatile integer offsets, concurrent insertions never corrupt sibling positions.", "noteb"),
        "Causal broadcast guarantees that every referenced parent anchor arrives before its dependent insertion, while deletions mark tombstones to preserve downstream references.",
    ])


# =============================================================================
# CHAPTER 27: LOW-LATENCY ELECTRONIC STOCK EXCHANGE
# =============================================================================

def ch27_use_cases():
    return build_use_case_fig(
        "ch27_use_cases",
        "Figure 27-1. Actors and Use Cases of the Low-Latency Electronic Stock Exchange.",
        "System Boundary: Electronic Stock Exchange",
        "Binary SBE order entry · Deterministic matching · Real-time market data",
        actors=[
            ("Trading Firm / Broker", "Co-located FIX / SBE client", "blue", "laptop"),
            ("Market Data Subscriber", "Multicast L2 / L3 consumer", "teal", "notifications_active"),
            ("Clearing & Surveillance", "Risk, settlement & regulator", "purple", "shield"),
        ],
        cases=[
            ("Submit & Cancel Limit Orders", "Binary SBE NewOrder / CancelOrder", "blue", "bolt"),
            ("Enforce Pre-Trade Risk Limits", "Credit, price-collar & kill-switch checks", "amber", "shield"),
            ("Match Orders (Price-Time FIFO)", "Deterministic in-memory order book", "green", "swap_horiz"),
            ("Disseminate Market Data Feed", "UDP multicast L2 / L3 book deltas", "teal", "lan"),
            ("Audit Trades & T+1 Settlement", "Immutable sequencer journal & fills", "purple", "library_books"),
        ],
        links=[
            (0, [0, 1, 2], "blue"),
            (1, [3], "teal"),
            (2, [1, 4], "purple"),
        ],
        notes=[
            ("Electronic exchanges enforce strict pre-trade risk limits before orders enter the deterministic sequencer so runaway algorithms cannot destabilize the book.", "noteb"),
            "Market data subscribers consume low-jitter UDP multicast deltas, while clearing houses settle executed trades against the authoritative sequencer journal.",
        ],
    )


def ch27_architecture():
    f = Fig(
        "ch27_architecture",
        "Figure 27-2. Order Gateway, Risk Check, Deterministic Sequencer, and Partitioned Matching Engines.",
        544,
    )
    # Top-left: Trading Firms
    firms = f.node(
        MARGIN, 18, 224, 92, "blue",
        [("Trading Firms", "name"), ("Co-located FIX / SBE", "sub"), ("Kernel-bypass TCP", "small")],
        icon="laptop", kind="card", icon_size=26,
    )

    # Top-right: Control Plane
    cp_x = 286
    cp_w = WIDTH - MARGIN - cp_x  # 602
    f.zone(
        cp_x, 0, cp_w, 148, "purple",
        "Control Plane (Risk Rules, Symbol Map & Market Surveillance)",
        "Margin limits · Fat-finger collars · Circuit breakers · Kill switch",
        icon="settings_suggest", dashed=True,
    )
    risk_ctrl = f.node(
        cp_x + 16, 58, 276, 74, "purple",
        [("Risk & Limit Manager", "name"), ("Credit caps · Price collars", "sub")],
        icon="shield", kind="card", icon_size=26,
    )
    surv = f.node(
        cp_x + 310, 58, 276, 74, "purple",
        [("Surveillance & Halts", "name"), ("Symbol routing · Kill switch", "sub")],
        icon="warning", kind="card", icon_size=26,
    )

    # Middle Tier: Deterministic Order Pipeline
    pipe = f.zone(
        MARGIN, 190, INNER, 158, "teal",
        "Data Plane: Deterministic Order Matching Pipeline (< 100 us p99)",
        "Zero-allocation binary path across kernel-bypass NICs, in-RAM risk checks, global sequencer, and pinned matching cores",
        icon="bolt",
    )
    st_w = 186
    st_gap = 26
    sx = [MARGIN + 17 + i * (st_w + st_gap) for i in range(4)]
    s1 = f.node(sx[0], 250, st_w, 80, "blue", [
        ("1. Order Gateway", "name"),
        ("Decode SBE · Auth", "sub"),
        ("Rate & session ID", "small"),
    ], layout="center", kind="card")
    s2 = f.node(sx[1], 250, st_w, 80, "amber", [
        ("2. Pre-Trade Risk", "name"),
        ("In-RAM limits", "sub"),
        ("Fat-finger check", "small"),
    ], layout="center", kind="card")
    s3 = f.node(sx[2], 250, st_w, 80, "purple", [
        ("3. Sequencer", "name"),
        ("Total seq_id", "sub"),
        ("Append journal", "small"),
    ], layout="center", kind="card")
    s4 = f.node(sx[3], 250, st_w, 80, "green", [
        ("4. Matching Core", "name"),
        ("Sharded by symbol", "sub"),
        ("Price-time FIFO", "small"),
    ], layout="center", kind="card")

    f.wire([s1.right(0), s2.left(0)], tone="blue", width=1.9)
    f.wire([s2.right(0), s3.left(0)], tone="amber", width=1.9)
    f.wire([s3.right(0), s4.left(0)], tone="purple", width=1.9)

    # Bottom Tier: Outputs, Standby Replay & Market Data
    out_zone = f.zone(
        MARGIN, 388, INNER, 148, "blue",
        "Data Plane: Execution Drop Copy, Deterministic Standby, and Market Data Feeds",
        "Downstream consumers subscribe to the sequenced journal and matching outputs without blocking the matching loop",
        icon="layers",
    )
    o1 = f.node(MARGIN + 16, 446, 258, 72, "green", [
        ("Drop Copy & Clearing", "name"),
        ("Exec reports · T+1 DTCC", "sub"),
    ], icon="library_books", kind="card", icon_size=24)
    o2 = f.node(MARGIN + 298, 446, 258, 72, "amber", [
        ("Hot Standby Shards", "name"),
        ("Deterministic journal replay", "sub"),
    ], icon="loop", kind="card", icon_size=24)
    o3 = f.node(MARGIN + 580, 446, 260, 72, "teal", [
        ("Market Data Publisher", "name"),
        ("UDP multicast L2 / L3", "sub"),
    ], icon="lan", kind="card", icon_size=24)

    # Clean orthogonal wires (zero crossings)
    f.wire([firms.bottom(0), (firms.cx, pipe.y)], tone="blue", width=2.0, tail=True)
    f.label(firms.cx + 76, 170, "Orders / ExecReports", tone="blue", cls="small")

    f.wire([risk_ctrl.bottom(-86), (s2.cx, pipe.y)], tone="purple", dash=True, width=1.7)
    f.label(s2.cx + 52, 170, "Risk limits", tone="purple", cls="small")

    f.wire([surv.bottom(44), (s4.cx, pipe.y)], tone="purple", dash=True, width=1.7)
    f.label(s4.cx - 64, 170, "Halt / kill switch", tone="purple", cls="small")

    f.wire([(s1.cx, pipe.b), (s1.cx, out_zone.y)], tone="green", width=1.8, tail=True)
    f.label(s1.cx + 68, 370, "Fills & audit", tone="green", cls="small")

    f.wire([(s3.cx, pipe.b), (s3.cx, 370), (o2.cx, 370), (o2.cx, out_zone.y)], tone="amber", dash=True, width=1.8)
    f.label(486, 366, "Seq stream", tone="amber", cls="small")

    f.wire([(s4.cx, pipe.b), (s4.cx, out_zone.y)], tone="teal", width=2.0)
    f.label(s4.cx - 72, 370, "Book deltas", tone="teal", cls="small")

    return f.save([
        ("Assigning a strict total order in the sequencer before matching allows partitioned symbol engines to execute deterministically without cross-core locks.", "noteb"),
        "Hot-standby engines consume the identical sequenced input stream in parallel, eliminating synchronous replication pauses from the critical order-to-fill path.",
    ])


def ch27_lmax_pipeline():
    f = Fig(
        "ch27_lmax_pipeline",
        "Figure 27-3. Single-Threaded LMAX Ring-Buffer Matching Loop and Deterministic Replicated Standby.",
        472,
    )
    # Top Band: Primary LMAX Ring Buffer + Single-Threaded Matching Loop
    f.zone(
        MARGIN, 0, INNER, 260, "blue",
        "Primary Matching Shard (Pinned CPU Core · Zero Locks · Pre-Allocated Memory)",
        "Cache-line padded sequence counters avoid false sharing; zero heap allocations eliminate GC jitter",
        icon="developer_board",
    )

    # Ring Buffer visualization on left
    f.text(MARGIN + 20, 68, "Inbound Disruptor Ring Buffer (Power-of-2 Slots)", "name", "start", tone="blue")
    slot_w = 62
    slot_gap = 8
    sx0 = MARGIN + 20
    slots = [
        ("#101", "Done", "gray", "tonal"),
        ("#102", "Done", "gray", "tonal"),
        ("#103", "Match", "green", "mid"),
        ("#104", "Ready", "blue", "card"),
        ("#105", "Ready", "blue", "card"),
        ("#106", "Write", "amber", "mid"),
    ]
    for i, (num, st, tone, knd) in enumerate(slots):
        x = sx0 + i * (slot_w + slot_gap)
        f.cell(x, 82, slot_w, 56, tone, [(num, "monob"), (st, "small")], kind=knd, r=8)

    # Cursor pills beneath slots
    f.pill(sx0 + 2 * 70 + 31, 148, "Match Cursor", tone="green", anchor="middle")
    f.pill(sx0 + 5 * 70 + 31, 148, "Prod Cursor", tone="amber", anchor="middle")

    # Key properties box under ring buffer
    f.node(MARGIN + 20, 182, 412, 62, "teal", [
        ("Mechanical Sympathy Guarantees", "name"),
        ("Single-writer seq · L1/L2 prefetch · Busy-spin poll", "sub"),
    ], icon="memory", kind="card", icon_size=24)

    # Right side: Single-Threaded Matching Loop
    lx = 486
    lw = WIDTH - MARGIN - lx - 16  # 386
    f.zone(lx, 56, lw, 188, "green", "Single-Threaded Matching Loop", "No mutexes · No context switches", icon="play_arrow")
    l1 = f.node(lx + 14, 114, 110, 114, "blue", [("1. Poll", "name"), ("Read #103", "mono"), ("0 alloc", "small")], layout="center", kind="card")
    l2 = f.node(lx + 138, 114, 110, 114, "green", [("2. Match", "name"), ("L3 book", "mono"), ("FIFO fill", "small")], layout="center", kind="card")
    l3 = f.node(lx + 262, 114, 110, 114, "teal", [("3. Emit", "name"), ("Out ring", "mono"), ("L2 delta", "small")], layout="center", kind="card")
    f.wire([l1.right(0), l2.left(0)], tone="green", width=1.6)
    f.wire([l2.right(0), l3.left(0)], tone="green", width=1.6)

    # Wire from Ring Buffer to Loop
    f.wire([(sx0 + 6 * 70 - 8, 110), (lx, 110)], tone="blue", width=1.9)

    # Bottom Band: Deterministic Replicated Standby
    stb = f.zone(
        MARGIN, 294, INNER, 168, "amber",
        "Deterministic Replicated Standby (State Machine Replication)",
        "Replays the exact same sequenced input events on an isolated host for sub-50 ms failover",
        icon="loop", dashed=True,
    )
    b1 = f.node(MARGIN + 18, 356, 250, 86, "purple", [
        ("1. Sequenced Journal", "name"),
        ("Identical #101..#106", "mono"),
        ("Kernel-bypass multicast", "small"),
    ], icon="table_rows", kind="card", icon_size=24)
    b2 = f.node(MARGIN + 302, 356, 252, 86, "amber", [
        ("2. Standby Loop", "name"),
        ("Pure deterministic fn", "mono"),
        ("No wall-clock calls", "small"),
    ], icon="developer_board", kind="card", icon_size=24)
    b3 = f.node(MARGIN + 588, 356, 250, 86, "green", [
        ("3. Warm Shadow Book", "name"),
        ("Bit-identical state", "mono"),
        ("Outputs muted until cutover", "small"),
    ], icon="shield", kind="card", icon_size=24)

    f.wire([b1.right(0), b2.left(0)], tone="amber", width=1.9)
    f.wire([b2.right(0), b3.left(0)], tone="green", width=1.9)

    # Vertical replication wire from Primary to Standby
    f.wire([(175, 260), (175, stb.y)], tone="purple", dash=True, width=1.9)
    f.label(270, 279, "Ordered event stream (#101..#106)", tone="purple", cls="small")

    return f.save([
        ("Running the order book on a single pinned CPU core eliminates lock contention and cache-line bouncing, sustaining over one million orders per second per shard.", "noteb"),
        "Because every state transition depends solely on the sequenced input stream and never on local wall-clock time or randomness, the standby replica stays bit-for-bit identical.",
    ])


# =============================================================================
# CHAPTER 28: REAL-TIME AD-CLICK AGGREGATION PIPELINE
# =============================================================================

def ch28_use_cases():
    return build_use_case_fig(
        "ch28_use_cases",
        "Figure 28-1. Actors and Use Cases of the Real-Time Ad-Click Aggregation Pipeline.",
        "System Boundary: Real-Time Ad-Click Aggregation Pipeline",
        "High-throughput click ingestion · Event-time windows · Exact billing reconciliation",
        actors=[
            ("Visitor Browser / SDK", "Ad click telemetry beacon", "blue", "laptop"),
            ("Advertiser Dashboard", "Live campaign analytics", "teal", "apps"),
            ("Billing & Fraud Engine", "Invoicing & bot filtering", "purple", "shield"),
        ],
        cases=[
            ("Ingest Raw Ad-Click Events", "POST /v1/clicks (ad_id, event_ts)", "blue", "bolt"),
            ("Deduplicate & Filter Bot Clicks", "Drop duplicate click_id & invalid traffic", "amber", "shield"),
            ("Aggregate 1-Min Event-Time Counts", "Tumbling windows with watermarks", "green", "timer"),
            ("Query Live Campaign Top-K Counts", "GET /v1/ads/{id}/clicks?window=1m", "teal", "table_rows"),
            ("Reconcile Final Billing Counts", "Batch replay from raw immutable archive", "purple", "rule"),
        ],
        links=[
            (0, [0], "blue"),
            (1, [3], "teal"),
            (2, [1, 2, 4], "purple"),
        ],
        notes=[
            ("Ad-click pipelines balance low-latency live dashboards against audit-grade billing accuracy by pairing streaming aggregation with immutable raw-log replay.", "noteb"),
            "Every click carries a client-generated event timestamp and unique click identifier so downstream processors can deduplicate retries and group events by occurrence time.",
        ],
    )


def ch28_architecture():
    f = Fig(
        "ch28_architecture",
        "Figure 28-2. Click Collectors, Partitioned Event Log, Stateful Stream Processors, and OLAP Store.",
        544,
    )
    # Top-left: Browsers / SDKs
    browsers = f.node(
        MARGIN, 18, 256, 92, "blue",
        [("Visitor Browsers & SDKs", "name"), ("100k+ clicks/s · Edge L7 LB", "sub"), ("POST /v1/clicks", "mono")],
        icon="laptop", kind="card", icon_size=26,
    )

    # Top-right: Control Plane
    cp_x = 326
    cp_w = WIDTH - MARGIN - cp_x  # 562
    f.zone(
        cp_x, 0, cp_w, 148, "purple",
        "Control Plane (Stream Orchestration, Checkpoints & Schema)",
        "Partition rebalancing · Chandy-Lamport barriers · Avro schema registry",
        icon="settings_suggest", dashed=True,
    )
    schema_ctrl = f.node(
        cp_x + 16, 58, 256, 74, "purple",
        [("Schema & Broker Ctrl", "name"), ("Topic partitions · ACLs", "sub")],
        icon="dns", kind="card", icon_size=26,
    )
    flink_ctrl = f.node(
        cp_x + 290, 58, 256, 74, "purple",
        [("Stream Job Manager", "name"), ("Checkpoints · Watermarks", "sub")],
        icon="tune", kind="card", icon_size=26,
    )

    # Middle Tier: Real-Time Streaming Path
    stream = f.zone(
        MARGIN, 190, INNER, 158, "teal",
        "Data Plane: Real-Time Streaming Aggregation Path (Speed Layer)",
        "Stateless ingestion -> partitioned Kafka log -> stateful Flink event-time windows -> low-latency OLAP store",
        icon="bolt",
    )
    st_w = 186
    st_gap = 26
    sx = [MARGIN + 17 + i * (st_w + st_gap) for i in range(4)]
    c1 = f.node(sx[0], 250, st_w, 80, "blue", [
        ("1. Click Collectors", "name"),
        ("Validate · Enrich", "sub"),
        ("Fast 202 ACK", "small"),
    ], layout="center", kind="card")
    c2 = f.node(sx[1], 250, st_w, 80, "amber", [
        ("2. Event Log", "name"),
        ("Kafka · by ad_id", "sub"),
        ("3-AZ replication", "small"),
    ], layout="center", kind="card")
    c3 = f.node(sx[2], 250, st_w, 80, "teal", [
        ("3. Stream Engine", "name"),
        ("Dedup + Windows", "sub"),
        ("RocksDB state", "small"),
    ], layout="center", kind="card")
    c4 = f.node(sx[3], 250, st_w, 80, "green", [
        ("4. OLAP Store", "name"),
        ("Pinot / ClickHouse", "sub"),
        ("Live Top-K reads", "small"),
    ], layout="center", kind="card")

    f.wire([c1.right(0), c2.left(0)], tone="blue", width=1.9)
    f.wire([c2.right(0), c3.left(0)], tone="amber", width=1.9)
    f.wire([c3.right(0), c4.left(0)], tone="teal", width=1.9)

    # Bottom Tier: Raw Archive, Nightly Batch & Serving API
    batch = f.zone(
        MARGIN, 388, INNER, 148, "blue",
        "Data Plane: Immutable Raw Archive, Batch Reconciliation, and Serving API",
        "Preserves every raw click so nightly batch jobs correct stragglers and produce audit-grade advertiser invoices",
        icon="layers",
    )
    b1 = f.node(MARGIN + 16, 446, 258, 72, "purple", [
        ("Raw Click Archive", "name"),
        ("Parquet on S3 · 73 TB/yr", "sub"),
    ], icon="inventory_2", kind="card", icon_size=24)
    b2 = f.node(MARGIN + 298, 446, 258, 72, "amber", [
        ("Nightly Batch Reconciler", "name"),
        ("Re-aggregates late clicks", "sub"),
    ], icon="loop", kind="card", icon_size=24)
    b3 = f.node(MARGIN + 580, 446, 260, 72, "green", [
        ("Counts API & Billing", "name"),
        ("Dashboards + final bills", "sub"),
    ], icon="table_rows", kind="card", icon_size=24)

    f.wire([b1.right(0), b2.left(0)], tone="purple", width=1.8)
    f.wire([b2.right(0), b3.left(0)], tone="amber", width=1.8)

    # Clean orthogonal wires (zero crossings)
    f.wire([browsers.bottom(-18), (c1.cx, stream.y)], tone="blue", width=2.0)
    f.label(c1.cx + 68, 170, "Click beacons", tone="blue", cls="small")

    f.wire([schema_ctrl.bottom(-40), (schema_ctrl.cx - 40, 170), (c2.cx, 170), (c2.cx, stream.y)],
           tone="purple", dash=True, width=1.7)
    f.label(396, 166, "Schema", tone="purple", cls="small")

    f.wire([flink_ctrl.bottom(-40), (flink_ctrl.cx - 40, 170), (c3.cx, 170), (c3.cx, stream.y)],
           tone="purple", dash=True, width=1.7)
    f.label(638, 166, "Checkpoints", tone="purple", cls="small")

    f.wire([(c2.cx, stream.b), (c2.cx, 370), (b1.cx, 370), (b1.cx, batch.y)], tone="purple", width=1.9)
    f.label(268, 366, "Raw sink (Parquet)", tone="purple", cls="small")

    f.wire([(c4.cx, stream.b), (c4.cx, batch.y)], tone="green", width=2.0)
    f.label(c4.cx - 72, 370, "Live window counts", tone="green", cls="small")

    return f.save([
        ("Partitioning the event log by ad_id colocalizes all clicks for a campaign on one stateful stream processor, avoiding costly distributed shuffles.", "noteb"),
        "Sinking the immutable event log to cold Parquet storage enables full deterministic recomputation whenever late mobile beacons arrive or fraud rules change.",
    ])


def ch28_watermark_window():
    f = Fig(
        "ch28_watermark_window",
        "Figure 28-3. Event-Time Watermarks, Allowed Lateness Windows, and Late-Event Side Outputs.",
        472,
    )
    # Top Band: Event-Time Timeline
    f.zone(
        MARGIN, 0, INNER, 266, "blue",
        "Event-Time Window [12:00, 12:01) with Watermark W(t) = max_event_ts - 10 s",
        "Clicks arrive out of order due to mobile offline queues; watermarks bound how long a window waits",
        icon="timer",
    )

    # Time axis
    ax1, ax2 = MARGIN + 28, WIDTH - MARGIN - 28
    ay = 82
    f.wire([(ax1, ay), (ax2, ay)], tone="wire", width=1.6)
    ticks = [
        (ax1 + 24, "12:00:00", "Window Open", "blue"),
        (ax1 + 310, "12:01:00", "Window Close", "green"),
        (ax1 + 540, "12:01:20", "Lateness End (+20s)", "amber"),
        (ax1 + 740, "12:01:35", "Purged", "red"),
    ]
    for tx, tm, cap, tone in ticks:
        f.rule(tx, ay - 6, tx, 250, tone=tone, width=1.1, dash="4 4")
        f.text(tx, ay - 12, tm, "monob", "middle", tone=tone)
        f.text(tx, ay + 18, cap, "small", "middle", tone=tone)

    # Three event bands on timeline
    e1 = f.node(ax1 + 32, 114, 268, 42, "green", [
        ("On-Time (ev 12:00:12..58)", "monob"),
    ], layout="center", kind="card", r=8)
    e2 = f.node(ax1 + 320, 162, 210, 42, "amber", [
        ("Late Click (ev 12:00:55)", "monob"),
    ], layout="center", kind="mid", r=8)
    e3 = f.node(ax1 + 550, 206, 216, 42, "red", [
        ("Straggler (ev 12:00:40)", "monob"),
    ], layout="center", kind="mid", r=8)

    # Explanatory right-side annotations in empty timeline space
    f.pill(ax1 + 430, 125, "Included in initial emit", tone="green", anchor="start")
    f.pill(ax1 + 550, 173, "Updates window + retract", tone="amber", anchor="start")

    # Bottom Band: 3-Stage Window Lifecycle
    f.zone(
        MARGIN, 290, INNER, 172, "teal",
        "Window State Lifecycle and Late-Event Routing Policy",
        "Separates fast provisional results from bounded in-memory corrections and unbounded archive recovery",
        icon="rule",
    )
    s1 = f.node(MARGIN + 18, 352, 252, 92, "green", [
        ("1. Watermark Trigger", "name"),
        ("W(t) >= 12:01:00", "monob"),
        ("Emit initial count to OLAP", "small"),
    ], icon="play_arrow", kind="card", icon_size=24)
    s2 = f.node(MARGIN + 302, 352, 252, 92, "amber", [
        ("2. Allowed Lateness", "name"),
        ("12:01:00 < W <= 12:01:20", "monob"),
        ("Retain RocksDB · Upsert delta", "small"),
    ], icon="hourglass_top", kind="card", icon_size=24)
    s3 = f.node(MARGIN + 586, 352, 252, 92, "red", [
        ("3. Side Output & Purge", "name"),
        ("W(t) > 12:01:20", "monob"),
        ("Free RAM · Route to batch", "small"),
    ], icon="warning", kind="mid", icon_size=24)

    f.wire([s1.right(0), s2.left(0)], tone="amber", width=1.9)
    f.wire([s2.right(0), s3.left(0)], tone="red", width=1.9)

    return f.save([
        ("Watermarks formalize the latency-completeness trade-off: a longer watermark lag captures more out-of-order mobile clicks before emitting, at the cost of higher dashboard delay.", "noteb"),
        "Allowed lateness keeps window state in RocksDB for a bounded grace period to emit incremental retractions, after which stragglers route to a side output for batch reconciliation.",
    ])


ALL = [
    ch25_use_cases,
    ch25_architecture,
    ch25_merkle_cdc,
    ch26_use_cases,
    ch26_architecture,
    ch26_crdt_convergence,
    ch27_use_cases,
    ch27_architecture,
    ch27_lmax_pipeline,
    ch28_use_cases,
    ch28_architecture,
    ch28_watermark_window,
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
