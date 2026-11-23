#!/usr/bin/env python3
"""Generate 12 spacious Material Design 3 light+dark SVG figures for Part VI (Chapters 25-28).

Every figure prioritizes generous whitespace, concise crisp labels, zero text
overflow in Chrome/Safari, and clear separation of control and data planes.
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
        548,
    )
    # Top-left: Physical Client Devices (aligned to gw.cx = 156)
    cli = f.node(
        MARGIN, 14, 248, 124, "blue",
        [("Desktop & Mobile Agents", "name"), ("Local FS watch · FastCDC", "sub"), ("Merkle diff · Chunk queue", "small")],
        icon="laptop", kind="card", icon_size=26,
    )

    # Top-right: Control Plane
    cp_x = 324
    cp_w = WIDTH - MARGIN - cp_x  # 564
    f.zone(
        cp_x, 0, cp_w, 148, "purple",
        "Control Plane (Metadata, CAS & Garbage Collection)",
        "Namespace authority · Optimistic version checks · Block reference counting",
        icon="settings_suggest", dashed=True,
    )
    meta_api = f.node(
        cp_x + 16, 58, 256, 74, "purple",
        [("Metadata & CAS API", "name"), ("Manifest commits · ACLs", "sub")],
        icon="dns", kind="card", icon_size=26,
    )
    gc_ctrl = f.node(
        cp_x + 292, 58, 256, 74, "purple",
        [("GC & Quota Sweeper", "name"), ("Mark-and-sweep orphans", "sub")],
        icon="tune", kind="card", icon_size=26,
    )

    # Middle Row: Block Gateway, Delta Notification Bus, Metadata Store (48px gap bus<->mdb)
    gw = f.node(
        MARGIN, 194, 248, 96, "teal",
        [("Block Gateway", "name"), ("SHA-256 verify · Dedup", "sub"), ("Pre-signed PUT / GET", "small")],
        icon="swap_horiz", kind="card", icon_size=26,
    )
    bus = f.node(
        324, 194, 248, 96, "amber",
        [("Delta Notification Bus", "name"), ("Push & long-poll edge", "sub"), ("Per-folder cursor fanout", "small")],
        icon="notifications_active", kind="card", icon_size=26,
    )
    mdb = f.node(
        620, 194, 268, 96, "purple",
        [("Metadata Store (3-AZ)", "name"), ("Serializable ACID quorum", "sub"), ("files · chunks · seq_log", "mono")],
        icon="table_rows", kind="card", icon_size=26,
    )

    # Bottom Row: Content-Addressed Block Store (concise header leaves x >= 320 clear)
    f.zone(
        MARGIN, 344, INNER, 196, "blue",
        "Content-Addressed Block Store",
        "Immutable SHA-256 · Global dedup",
        icon="layers",
    )
    ecache = f.node(
        MARGIN + 16, 412, 256, 104, "teal",
        [("Edge Download Cache", "name"), ("Hot shared file blocks", "sub"), ("Zero-copy range reads", "small")],
        icon="memory", kind="card", icon_size=26,
    )
    chunks = f.node(
        MARGIN + 300, 412, 256, 104, "blue",
        [("Immutable Chunk Store", "name"), ("key = sha256(bytes)", "mono"), ("Erasure-coded across AZs", "small")],
        icon="inventory_2", kind="card", icon_size=26,
    )
    archive = f.node(
        MARGIN + 584, 412, 256, 104, "gray",
        [("Delayed Sweep Archive", "name"), ("Unreferenced > 30 days", "sub"), ("Safe tombstone retention", "small")],
        icon="schedule", kind="card", icon_size=26,
    )

    # Synchronous critical path wires (solid, card-to-card, symmetric)
    f.wire([cli.bottom(-24), gw.top(-24)], tone="blue", width=2.0, tail=True)
    f.label(gw.cx - 86, 168, "Chunk PUT/GET", tone="blue", cls="small")

    f.wire([gw.bottom(0), (gw.cx, 320), (chunks.cx, 320), chunks.top(0)], tone="teal", width=2.0, tail=True)
    f.label(258, 318, "SHA-256 blocks", tone="teal", cls="small")

    f.wire([cli.right(19), meta_api.left(0)], tone="purple", width=1.9, tail=True)
    f.label(300, 74, "CAS", tone="purple", cls="small")

    f.wire([meta_api.bottom(0), (meta_api.cx, 166), (mdb.cx - 32, 166), mdb.top(-32)],
           tone="purple", width=1.9, tail=True)

    f.wire([mdb.left(0), bus.right(0)], tone="amber", width=1.9)

    # Async / control-plane wires (dashed, symmetric)
    f.wire([gc_ctrl.bottom(0), (gc_ctrl.cx, 166), (mdb.cx + 32, 166), mdb.top(32)],
           tone="purple", dash=True, width=1.6, tail=True)
    f.wire([bus.top(0), (bus.cx, 170), (cli.cx + 24, 170), cli.bottom(24)],
           tone="amber", dash=True, width=1.8)
    f.label((cli.cx + 24 + bus.cx) / 2, 154, "Delta wake", tone="amber", cls="small")

    f.wire([chunks.left(0), ecache.right(0)], tone="teal", dash=True, width=1.6)
    f.wire([mdb.bottom(0), (mdb.cx, 320), (archive.cx, 320), archive.top(0)], tone="purple", dash=True, width=1.6)
    f.label(archive.cx - 72, 320, "Orphan sweep", tone="purple", cls="small")

    # Symmetrically centered numbered step badges (1-6, zero border collisions)
    step_badge(f, gw.cx - 24, seg_mid(cli.b, gw.y, head=True, tail=True), 1, "blue")
    step_badge(f, chunks.cx, seg_mid(320, chunks.y, head=True), 2, "teal")
    step_badge(f, 300, 95, 3, "purple")
    step_badge(f, seg_mid(meta_api.cx, mdb.cx - 32, head=False), 166, 4, "purple")
    step_badge(f, seg_mid(mdb.x, bus.r, head=True), bus.cy, 5, "amber")
    step_badge(f, seg_mid(bus.cx, cli.cx + 24, head=False), 170, 6, "amber")

    return f.save([
        ("Solid wires trace the synchronous chunk-upload and CAS-commit path (steps 1-5); dashed wires carry async delta notifications (6), edge cache fills, and GC sweeps.", "noteb"),
        "Separating metadata CAS commits (control plane) from immutable SHA-256 block transfers (data plane) keeps storage horizontally scalable.",
    ])


def ch25_merkle_cdc():
    f = Fig(
        "ch25_merkle_cdc",
        "Figure 25-3. Content-Defined Chunking (CDC), Merkle Tree Diffing, and Conflict Branching.",
        462,
    )
    # Top Band: Fixed vs Content-Defined Chunking
    f.zone(
        MARGIN, 0, INNER, 176, "teal",
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
    f.text(MARGIN + 18, 150, "100% bandwidth re-transmitted on prepend", "small", "start", tone="red")

    # Divider
    f.rule(460, 56, 460, 164, tone="gray", width=1.2, dash="4 4")

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
    f.text(478, 150, "Anchor bytes restore alignment; 75% skipped", "small", "start", tone="green")

    # Bottom-left: Merkle Tree Diffing (symmetric 1-to-2 vertical splits + badges 1, 2)
    f.zone(
        MARGIN, 196, 416, 258, "blue",
        "2. Merkle Tree Diffing (O(log N) Sync)",
        "Prune matching subtrees; transfer only changed leaves",
        icon="call_split",
    )
    root = f.cell(174, 252, 132, 34, "amber", [("Root v4 != v3", "monob")], kind="mid", r=8)
    h01 = f.cell(62, 326, 152, 36, "green", [("H(C1,C2) Match", "monob")], kind="card", r=8)
    h23 = f.cell(264, 326, 154, 36, "amber", [("H(C3',C4) Diff", "monob")], kind="mid", r=8)
    c3 = f.cell(236, 404, 98, 34, "red", [("C3' Upload", "monob")], kind="mid", r=8)
    c4 = f.cell(346, 404, 88, 34, "green", [("C4 Same", "monob")], kind="card", r=8)
    f.pill(138, 410, "Subtree skipped", tone="green", anchor="middle")

    y_m1 = (root.b + h01.y) / 2  # 306.0
    f.wire([root.bottom(0), (root.cx, y_m1)], tone="amber", head=False, width=1.7)
    f.wire([(root.cx, y_m1), (h01.cx, y_m1), h01.top(0)], tone="green", width=1.7)
    f.wire([(root.cx, y_m1), (h23.cx, y_m1), h23.top(0)], tone="amber", width=1.8)
    step_badge(f, seg_mid(root.cx, h23.cx, head=False), y_m1, 1, "amber")

    y_m2 = (h23.b + c3.y) / 2  # 383.0
    f.wire([h23.bottom(0), (h23.cx, y_m2)], tone="amber", head=False, width=1.7)
    f.wire([(h23.cx, y_m2), (c3.cx, y_m2), c3.top(0)], tone="red", width=1.8)
    f.wire([(h23.cx, y_m2), (c4.cx, y_m2), c4.top(0)], tone="green", width=1.7)
    step_badge(f, seg_mid(h23.cx, c3.cx, head=False), y_m2, 2, "red")

    # Bottom-right: Conflict Branching (symmetric 1-to-2 horizontal split + badges 3, 4)
    rx = 472
    rw = WIDTH - MARGIN - rx  # 416
    f.zone(
        rx, 196, rw, 258, "amber",
        "3. Offline Conflict Branching (Zero Loss)",
        "Optimistic CAS rejects stale parent version cleanly",
        icon="warning",
    )
    win = f.node(rx + 172, 260, 230, 64, "green", [
        ("Laptop CAS(v3 -> v4)", "monob"),
        ("200 OK · Mainline v4", "small"),
    ], kind="card", r=10)
    lose = f.node(rx + 172, 368, 230, 64, "red", [
        ("Phone CAS(v3 -> v4)", "monob"),
        ("409 Conflict -> Fork copy", "small"),
    ], kind="mid", r=10)
    mid_y = (win.cy + lose.cy) / 2  # 346.0
    base = f.cell(rx + 14, mid_y - 31, 102, 62, "blue", [("Base v3", "name"), ("Shared", "small")], kind="card", r=10)

    x_mid = (base.r + win.x) / 2  # exact midpoint of 56px gap
    f.wire([base.right(0), (x_mid, base.cy)], tone="blue", head=False, width=1.8)
    f.wire([(x_mid, base.cy), (x_mid, win.cy), win.left(0)], tone="green", width=1.8)
    f.wire([(x_mid, base.cy), (x_mid, lose.cy), lose.left(0)], tone="red", width=1.8)
    step_badge(f, x_mid, seg_mid(base.cy, win.cy, head=False), 3, "green")
    step_badge(f, x_mid, seg_mid(base.cy, lose.cy, head=False), 4, "red")

    return f.save([
        ("Content-defined chunking aligns boundaries to local byte patterns rather than fixed offsets, preventing cascading re-uploads after small insertions.", "noteb"),
        "Merkle tree comparison isolates modified blocks in logarithmic round trips (steps 1-2), while optimistic CAS converts concurrent offline edits into explicit conflict copies (steps 3-4).",
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
            ("Apply Concurrent Text Edits", "WS /v1/documents/{id}/operations (CRDT delta)", "blue", "edit_note"),
            ("Broadcast Presence & Cursors", "Ephemeral selection & caret state", "teal", "notifications_active"),
            ("Reconnect & Reconcile Offline Ops", "Exchange state vector & missing ops", "amber", "loop"),
            ("Restore Historical Snapshot", "GET /v1/documents/{id}/revisions/{ver}", "green", "schedule"),
            ("Enforce Sharing & Role ACLs", "PATCH /v1/documents/{id}/permissions", "purple", "lock"),
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
        548,
    )
    # Top-left: Physical Co-Author Devices (centered over pod_a.cx = 168)
    cli = f.node(
        40, 14, 256, 124, "blue",
        [("Co-Author Browsers", "name"), ("Local CRDT · 0 ms apply", "sub"), ("Mobile offline op queue", "small")],
        icon="laptop", kind="card", icon_size=26,
    )

    # Top-right: Control Plane
    cp_x = 324
    cp_w = WIDTH - MARGIN - cp_x  # 564
    f.zone(
        cp_x, 0, cp_w, 148, "purple",
        "Control Plane (Session Routing & Access Control)",
        "Sticky document-to-gateway placement · Fencing epochs · Live ACL revocation",
        icon="settings_suggest", dashed=True,
    )
    coord = f.node(
        cp_x + 16, 58, 256, 74, "purple",
        [("Session Coordinator", "name"), ("Consistent doc_id lease", "sub")],
        icon="dns", kind="card", icon_size=26,
    )
    acl = f.node(
        cp_x + 292, 58, 256, 74, "purple",
        [("ACL & Auth Service", "name"), ("RBAC scopes · Revoke", "sub")],
        icon="shield", kind="card", icon_size=26,
    )

    # Middle Tier: Collaboration Gateways (title right-aligned over pres so left/mid wires stay unobstructed)
    f.zone(
        MARGIN, 194, INNER, 150, "teal",
        "Sticky Gateways",
        "Partitioned by doc_id",
        title_align="right",
    )
    pod_a = f.node(
        MARGIN + 14, 252, 244, 76, "teal",
        [("Gateway Pod A (doc_42)", "name"), ("WS fanout · Op buffer", "sub")],
        icon="bolt", kind="card", icon_size=24,
    )
    pod_b = f.node(
        MARGIN + 306, 252, 244, 76, "teal",
        [("Gateway Pod B (doc_99)", "name"), ("In-RAM CRDT merge", "sub")],
        icon="memory", kind="card", icon_size=24,
    )
    pres = f.node(
        MARGIN + 598, 252, 244, 76, "amber",
        [("Presence & Pub/Sub Bus", "name"), ("Cursors · Cross-AZ relay", "sub")],
        icon="notifications_active", kind="card", icon_size=24,
    )

    # Bottom Tier: Durable Operation Log & Snapshot Store (title centered over comp)
    f.zone(
        MARGIN, 386, INNER, 154, "blue",
        "Durable Log & Snapshots",
        "3-AZ op log · Compaction",
        title_align="center",
    )
    oplog = f.node(
        MARGIN + 14, 444, 244, 76, "amber",
        [("Append-Only Op Log", "name"), ("Keyed by doc_id · 3-AZ", "sub")],
        icon="table_rows", kind="card", icon_size=24,
    )
    comp = f.node(
        MARGIN + 306, 444, 244, 76, "green",
        [("Snapshot Compactor", "name"), ("Async fold every N ops", "sub")],
        icon="loop", kind="card", icon_size=24,
    )
    snap = f.node(
        MARGIN + 598, 444, 244, 76, "blue",
        [("Snapshot Object Store", "name"), ("Compressed CRDT state", "sub")],
        icon="inventory_2", kind="card", icon_size=24,
    )

    # Synchronous & primary wires (100% centered card-to-card, zero border collisions!)
    f.wire([cli.bottom(0), pod_a.top(0)], tone="blue", width=2.0, tail=True)
    f.label(cli.cx - 72, 168, "WS deltas + carets", tone="blue", cls="small")

    f.wire([cli.right(19), coord.left(0)], tone="purple", dash=True, width=1.7, tail=True)
    f.label(312, 76, "Route", tone="purple", cls="small")

    f.wire([coord.bottom(0), (coord.cx, 170), (pod_b.cx - 32, 170), pod_b.top(-32)],
           tone="purple", dash=True, width=1.7)
    f.label(362, 168, "Pod lease", tone="purple", cls="small")

    f.wire([acl.bottom(0), (acl.cx, 170), (pod_b.cx + 32, 170), pod_b.top(32)],
           tone="purple", dash=True, width=1.7)
    f.label(614, 168, "ACL revoke", tone="purple", cls="small")

    f.wire([pod_b.right(0), pres.left(0)], tone="amber", dash=True, width=1.8, tail=True)

    f.wire([pod_a.bottom(0), oplog.top(0)], tone="amber", width=2.0)
    f.label(pod_a.cx + 58, 365, "Persist op", tone="amber", cls="small")

    f.wire([oplog.right(0), comp.left(0)], tone="amber", dash=True, width=1.8)
    f.wire([comp.right(0), snap.left(0)], tone="green", dash=True, width=1.8)

    f.wire([snap.top(0), (snap.cx, 365), (pod_b.cx, 365), pod_b.bottom(0)],
           tone="teal", dash=True, width=1.8)
    f.label(502, 365, "Cold doc hydrate", tone="teal", cls="small")

    # Symmetrically centered numbered step badges (1-6, zero border collisions)
    step_badge(f, pod_a.cx, 166, 1, "blue")
    step_badge(f, seg_mid(pod_b.r, pres.x, head=True, tail=True), pod_b.cy, 2, "amber")
    step_badge(f, pod_a.cx, 365, 3, "amber")
    step_badge(f, seg_mid(oplog.r, comp.x, head=True), oplog.cy, 4, "amber")
    step_badge(f, seg_mid(comp.r, snap.x, head=True), comp.cy, 5, "green")
    step_badge(f, 646, 365, 6, "teal")

    return f.save([
        ("Solid wires trace the synchronous WS delta ingest and durable op-log append (steps 1, 3); dashed wires mark ephemeral presence (2), async compaction (4-5), and cold hydration (6).", "noteb"),
        "Pinning active document sessions to a sticky collaboration gateway minimizes fanout hops while keeping ephemeral presence out of durable storage.",
    ])


def ch26_crdt_convergence():
    f = Fig(
        "ch26_crdt_convergence",
        "Figure 26-3. Concurrent Edits Converging via Sequence CRDT Identifiers and Causal Broadcast.",
        494,
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
    za = f.zone(
        MARGIN, 112, lw, 208, "teal",
        "2a. Replica A (site_id = 1)",
        "Inserts 'B' after (1,1) while offline",
        icon="laptop",
    )
    f.node(MARGIN + 16, 170, lw - 32, 58, "green", [
        ("Local op1: Ins('B', after=(1,1))", "monob"),
        ("Assigned id = (3, 1) -> \"ABC\"", "small"),
    ], kind="card", r=10)
    f.node(MARGIN + 16, 244, lw - 32, 60, "amber", [
        ("Receive op2: id = (3, 2) 'X'", "monob"),
        ("Tie-break (3,2) > (3,1) -> \"AXBC\"", "small"),
    ], kind="card", r=10)

    zb = f.zone(
        rx, 112, lw, 208, "purple",
        "2b. Replica B (site_id = 2)",
        "Concurrently inserts 'X' after (1,1)",
        icon="laptop",
    )
    f.node(rx + 16, 170, lw - 32, 58, "amber", [
        ("Local op2: Ins('X', after=(1,1))", "monob"),
        ("Assigned id = (3, 2) -> \"AXC\"", "small"),
    ], kind="card", r=10)
    f.node(rx + 16, 244, lw - 32, 60, "green", [
        ("Receive op1: id = (3, 1) 'B'", "monob"),
        ("Tie-break (3,2) > (3,1) -> \"AXBC\"", "small"),
    ], kind="card", r=10)

    # Non-crossing causal broadcast wires in the 88px center corridor (x=416..504)
    f.wire([(MARGIN + lw, 198), (rx, 198)], tone="green", dash=True, width=1.9)
    f.label(460, 182, "op1 (3,1)", tone="green", cls="small")
    step_badge(f, seg_mid(MARGIN + lw, rx, head=True), 198, 1, "green")

    f.wire([(rx, 274), (MARGIN + lw, 274)], tone="amber", dash=True, width=1.9)
    f.label(460, 258, "op2 (3,2)", tone="amber", cls="small")
    step_badge(f, seg_mid(rx, MARGIN + lw, head=True), 274, 2, "amber")

    # Bottom Band: Converged State (48px below Middle Band for steps 3 & 4)
    conv = f.zone(
        MARGIN, 368, INNER, 118, "green",
        "3. Converged Sequence State on Both Replicas (Strong Eventual Consistency)",
        "Deterministic total order on (clock, site_id) guarantees identical \"AXBC\" regardless of arrival order",
        icon="play_arrow",
    )
    f.wire([(za.cx, za.b), (za.cx, conv.y)], tone="teal", width=1.9)
    step_badge(f, za.cx, seg_mid(za.b, conv.y, head=True), 3, "teal")
    f.wire([(zb.cx, zb.b), (zb.cx, conv.y)], tone="purple", width=1.9)
    step_badge(f, zb.cx, seg_mid(zb.b, conv.y, head=True), 4, "purple")

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
        c = f.cell(fx + idx * (cw + fgap), 424, cw, 38, tone, [(lbl, "monob")], kind=knd, r=8)
        if idx < len(final_cells) - 1:
            f.wire([c.right(0), (fx + (idx + 1) * (cw + fgap), c.cy)], tone="green", width=1.6)

    f.pill(WIDTH - MARGIN - 16, 380, "Commutative · Idempotent", tone="green", anchor="end")

    return f.save([
        ("Because sequence CRDT operations reference immutable anchor identifiers rather than volatile integer offsets, concurrent insertions never corrupt sibling positions (steps 1-2).", "noteb"),
        "Causal broadcast guarantees that every referenced parent anchor arrives before its dependent insertion, converging both replicas to identical order (steps 3-4).",
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
        548,
    )
    # Top-left: Physical Trading Firm Clients (centered over s1.cx = 131.5)
    firms = f.node(
        MARGIN, 18, 199, 92, "blue",
        [("Trading Firms", "name"), ("Co-located FIX / SBE", "sub"), ("Kernel-bypass TCP", "small")],
        icon="laptop", kind="card", icon_size=24,
    )

    # Top-right: Control Plane
    cp_x = 272
    cp_w = WIDTH - MARGIN - cp_x  # 616
    f.zone(
        cp_x, 0, cp_w, 148, "purple",
        "Control Plane (Risk Rules, Symbol Map & Market Surveillance)",
        "Margin limits · Fat-finger collars · Circuit breakers · Kill switch",
        icon="settings_suggest", dashed=True,
    )
    risk_ctrl = f.node(
        cp_x + 16, 58, 282, 74, "purple",
        [("Risk & Limit Manager", "name"), ("Credit caps · Price collars", "sub")],
        icon="shield", kind="card", icon_size=26,
    )
    surv = f.node(
        cp_x + 318, 58, 282, 74, "purple",
        [("Surveillance & Halts", "name"), ("Symbol routing · Kill switch", "sub")],
        icon="warning", kind="card", icon_size=26,
    )

    # Middle Tier: Deterministic Order Pipeline (title centered over s2/s3 gap, clear of all vertical wires)
    f.zone(
        MARGIN, 192, INNER, 156, "teal",
        "Matching Pipeline",
        "< 100 us p99 · Pinned",
        title_align="center",
    )
    st_w = 171
    st_gap = 48
    sx = [MARGIN + 14 + i * (st_w + st_gap) for i in range(4)]
    s1 = f.node(sx[0], 250, st_w, 80, "blue", [
        ("Order Gateway", "name"),
        ("Decode SBE · Auth", "sub"),
        ("Rate & session ID", "small"),
    ], layout="center", kind="card")
    s2 = f.node(sx[1], 250, st_w, 80, "amber", [
        ("Pre-Trade Risk", "name"),
        ("In-RAM limits", "sub"),
        ("Fat-finger check", "small"),
    ], layout="center", kind="card")
    s3 = f.node(sx[2], 250, st_w, 80, "purple", [
        ("Sequencer", "name"),
        ("Total seq_id", "sub"),
        ("Append journal", "small"),
    ], layout="center", kind="card")
    s4 = f.node(sx[3], 250, st_w, 80, "green", [
        ("Matching Core", "name"),
        ("Sharded by symbol", "sub"),
        ("Price-time FIFO", "small"),
    ], layout="center", kind="card")

    f.wire([s1.right(0), s2.left(0)], tone="blue", width=1.9)
    f.wire([s2.right(0), s3.left(0)], tone="amber", width=1.9)
    f.wire([s3.right(0), s4.left(0)], tone="purple", width=1.9)

    # Bottom Tier: Outputs, Standby Replay & Market Data (compact left header ends before o1.cx = 177)
    f.zone(
        MARGIN, 390, INNER, 150, "blue",
        "Outputs",
        "Fills · Replay · L2/L3",
    )
    o1 = f.node(MARGIN + 16, 448, 258, 72, "green", [
        ("Drop Copy & Clearing", "name"),
        ("Exec reports · T+1 DTCC", "sub"),
    ], icon="library_books", kind="card", icon_size=24)
    o2 = f.node(MARGIN + 298, 448, 258, 72, "amber", [
        ("Hot Standby Shards", "name"),
        ("Deterministic journal replay", "sub"),
    ], icon="loop", kind="card", icon_size=24)
    o3 = f.node(MARGIN + 580, 448, 260, 72, "teal", [
        ("Market Data Publisher", "name"),
        ("UDP multicast L2 / L3", "sub"),
    ], icon="lan", kind="card", icon_size=24)

    # Card-to-card orthogonal wires (100% centered exits & entries, zero border collisions!)
    f.wire([firms.bottom(0), s1.top(0)], tone="blue", width=2.0, tail=True)
    f.label(216, 152, "Orders / ExecReports", tone="blue", cls="small")

    f.wire([risk_ctrl.bottom(0), (risk_ctrl.cx, 168), (s2.cx, 168), s2.top(0)],
           tone="purple", dash=True, width=1.7)
    f.label(392, 155, "Risk limits", tone="purple", cls="small")

    f.wire([surv.bottom(0), (surv.cx, 168), (s4.cx, 168), s4.top(0)],
           tone="purple", dash=True, width=1.7)
    f.label(668, 168, "Halt / kill switch", tone="purple", cls="small")

    f.wire([s1.bottom(0), (s1.cx, 369), (o1.cx, 369), o1.top(0)], tone="green", width=1.8, tail=True)
    f.label(238, 369, "Fills & audit", tone="green", cls="small")

    f.wire([s3.bottom(0), (s3.cx, 369), (o2.cx, 369), o2.top(0)], tone="amber", dash=True, width=1.8)
    f.label(400, 369, "Seq stream", tone="amber", cls="small")

    f.wire([s4.bottom(0), (s4.cx, 369), (o3.cx, 369), o3.top(0)], tone="teal", width=2.0)
    f.label(684, 369, "Book deltas", tone="teal", cls="small")

    # Symmetrically centered numbered step badges (1-6, zero border collisions)
    step_badge(f, s1.cx, 151, 1, "blue")
    step_badge(f, seg_mid(s1.r, s2.x, head=True), s1.cy, 2, "blue")
    step_badge(f, seg_mid(s2.r, s3.x, head=True), s2.cy, 3, "amber")
    step_badge(f, seg_mid(s3.r, s4.x, head=True), s3.cy, 4, "purple")
    step_badge(f, (s4.cx + o3.cx) / 2, 369, 5, "teal")
    step_badge(f, (s3.cx + o2.cx) / 2, 369, 6, "amber")

    return f.save([
        ("Solid wires trace the < 100 us deterministic order-to-match-and-publish path (steps 1-5); dashed wires carry control-plane limits, kill switches, and standby replay (6).", "noteb"),
        "Assigning a strict total order in the sequencer before matching allows partitioned symbol engines to execute deterministically without cross-core locks.",
    ])


def ch27_lmax_pipeline():
    f = Fig(
        "ch27_lmax_pipeline",
        "Figure 27-3. Single-Threaded LMAX Ring-Buffer Matching Loop and Deterministic Replicated Standby.",
        492,
    )
    # Top Band: Primary LMAX Ring Buffer + Single-Threaded Matching Loop
    f.zone(
        MARGIN, 0, INNER, 260, "blue",
        "Primary Matching Shard (Pinned CPU Core · Zero Locks · Pre-Allocated Memory)",
        "Cache-line padded sequence counters avoid false sharing; zero heap allocations eliminate GC jitter",
        icon="developer_board",
    )

    # Ring Buffer visualization on left (6 slots: 366px total, right edge = 418)
    f.text(MARGIN + 20, 68, "Inbound Disruptor Ring Buffer (Power-of-2 Slots)", "name", "start", tone="blue")
    slot_w = 56
    slot_gap = 6
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
    ring_r = sx0 + 6 * slot_w + 5 * slot_gap  # 418

    # Cursor pills beneath slots
    f.pill(sx0 + 2 * (slot_w + slot_gap) + slot_w / 2, 148, "Match Cursor", tone="green", anchor="middle")
    f.pill(sx0 + 5 * (slot_w + slot_gap) + slot_w / 2, 148, "Prod Cursor", tone="amber", anchor="middle")

    # Key properties box under ring buffer
    f.node(MARGIN + 20, 182, 366, 62, "teal", [
        ("Mechanical Sympathy Guarantees", "name"),
        ("Single-writer seq · L1/L2 prefetch · Busy-spin", "sub"),
    ], icon="memory", kind="card", icon_size=22)

    # Right side: Single-Threaded Matching Loop (54px gap from Ring Buffer; 47px badged gaps inside)
    lx = 472
    lw = WIDTH - MARGIN - lx - 16  # 400
    f.zone(lx, 56, lw, 188, "green", "Single-Threaded Matching Loop", "No mutexes · No context switches", icon="play_arrow")
    l1 = f.node(lx + 12, 114, 94, 114, "blue", [("1. Poll", "name"), ("Read #103", "mono"), ("0 alloc", "small")], layout="center", kind="card")
    l2 = f.node(lx + 153, 114, 94, 114, "green", [("2. Match", "name"), ("L3 book", "mono"), ("FIFO fill", "small")], layout="center", kind="card")
    l3 = f.node(lx + 294, 114, 94, 114, "teal", [("3. Emit", "name"), ("Out ring", "mono"), ("L2 delta", "small")], layout="center", kind="card")
    f.wire([l1.right(0), l2.left(0)], tone="green", width=1.8)
    f.wire([l2.right(0), l3.left(0)], tone="green", width=1.8)

    # Wire from Ring Buffer to Loop (54px long) + badges 1, 2, 3
    f.wire([(ring_r, 110), (lx, 110)], tone="blue", width=1.9)
    step_badge(f, seg_mid(ring_r, lx, head=True), 110, 1, "blue")
    step_badge(f, seg_mid(l1.r, l2.x, head=True), l1.cy, 2, "green")
    step_badge(f, seg_mid(l2.r, l3.x, head=True), l2.cy, 3, "green")

    # Bottom Band: Deterministic Replicated Standby (52px below Primary for step 4; 48px gaps for 5 & 6)
    stb = f.zone(
        MARGIN, 312, INNER, 170, "amber",
        "Deterministic Replicated Standby (State Machine Replication)",
        "Replays the exact same sequenced input events on an isolated host for sub-50 ms failover",
        icon="loop", dashed=True,
    )
    b1 = f.node(MARGIN + 14, 374, 244, 86, "purple", [
        ("1. Sequenced Journal", "name"),
        ("Identical #101..#106", "mono"),
        ("Kernel-bypass multicast", "small"),
    ], icon="table_rows", kind="card", icon_size=22)
    b2 = f.node(MARGIN + 306, 374, 244, 86, "amber", [
        ("2. Standby Loop", "name"),
        ("Pure deterministic fn", "mono"),
        ("No wall-clock calls", "small"),
    ], icon="developer_board", kind="card", icon_size=22)
    b3 = f.node(MARGIN + 598, 374, 244, 86, "green", [
        ("3. Warm Shadow Book", "name"),
        ("Bit-identical state", "mono"),
        ("Outputs muted until cutover", "small"),
    ], icon="shield", kind="card", icon_size=22)

    f.wire([b1.right(0), b2.left(0)], tone="amber", width=1.9)
    f.wire([b2.right(0), b3.left(0)], tone="green", width=1.9)

    # Vertical replication wire from Primary to Standby (52px long) + badges 4, 5, 6
    f.wire([(175, 260), (175, stb.y)], tone="purple", dash=True, width=1.9)
    f.label(296, 288, "Ordered event stream (#101..#106)", tone="purple", cls="small")
    step_badge(f, 175, seg_mid(260, stb.y, head=True), 4, "purple")
    step_badge(f, seg_mid(b1.r, b2.x, head=True), b1.cy, 5, "amber")
    step_badge(f, seg_mid(b2.r, b3.x, head=True), b2.cy, 6, "green")

    return f.save([
        ("Running the order book on a single pinned CPU core (steps 1-3) eliminates lock contention and cache-line bouncing, sustaining over one million orders per second per shard.", "noteb"),
        "Because every state transition depends solely on the sequenced input stream (steps 4-6) and never on local wall-clock time or randomness, the standby replica stays bit-for-bit identical.",
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
        548,
    )
    # Top-left: Physical Visitor Browsers / SDKs (centered over c1.cx = 131.5)
    browsers = f.node(
        MARGIN, 18, 199, 92, "blue",
        [("Browsers & SDKs", "name"), ("100k+ clicks/s · LB", "sub"), ("POST /v1/clicks", "mono")],
        icon="laptop", kind="card", icon_size=24,
    )

    # Top-right: Control Plane
    cp_x = 272
    cp_w = WIDTH - MARGIN - cp_x  # 616
    f.zone(
        cp_x, 0, cp_w, 148, "purple",
        "Control Plane (Stream Orchestration, Checkpoints & Schema)",
        "Partition rebalancing · Chandy-Lamport barriers · Avro schema registry",
        icon="settings_suggest", dashed=True,
    )
    schema_ctrl = f.node(
        cp_x + 16, 58, 282, 74, "purple",
        [("Schema & Broker Ctrl", "name"), ("Topic partitions · ACLs", "sub")],
        icon="dns", kind="card", icon_size=26,
    )
    flink_ctrl = f.node(
        cp_x + 318, 58, 282, 74, "purple",
        [("Stream Job Manager", "name"), ("Checkpoints · Watermarks", "sub")],
        icon="tune", kind="card", icon_size=26,
    )

    # Middle Tier: Real-Time Streaming Path (title right-aligned over c4, clear of all incoming wires!)
    f.zone(
        MARGIN, 192, INNER, 156, "teal",
        "Speed Layer",
        "Real-time streaming path",
        title_align="right",
    )
    st_w = 171
    st_gap = 48
    sx = [MARGIN + 14 + i * (st_w + st_gap) for i in range(4)]
    c1 = f.node(sx[0], 250, st_w, 80, "blue", [
        ("Click Collectors", "name"),
        ("Validate · Enrich", "sub"),
        ("Fast 202 ACK", "small"),
    ], layout="center", kind="card")
    c2 = f.node(sx[1], 250, st_w, 80, "amber", [
        ("Event Log", "name"),
        ("Kafka · by ad_id", "sub"),
        ("3-AZ replication", "small"),
    ], layout="center", kind="card")
    c3 = f.node(sx[2], 250, st_w, 80, "teal", [
        ("Stream Engine", "name"),
        ("Dedup + Windows", "sub"),
        ("RocksDB state", "small"),
    ], layout="center", kind="card")
    c4 = f.node(sx[3], 250, st_w, 80, "green", [
        ("OLAP Store", "name"),
        ("Pinot / ClickHouse", "sub"),
        ("Live Top-K reads", "small"),
    ], layout="center", kind="card")

    f.wire([c1.right(0), c2.left(0)], tone="blue", width=1.9)
    f.wire([c2.right(0), c3.left(0)], tone="amber", width=1.9)
    f.wire([c3.right(0), c4.left(0)], tone="teal", width=1.9)

    # Bottom Tier: Raw Archive, Nightly Batch & Serving API (title centered over b2, clear of b1 & b3 wires!)
    f.zone(
        MARGIN, 390, INNER, 150, "blue",
        "Batch & Serving Tier",
        "Raw archive · Nightly recon",
        title_align="center",
    )
    b1 = f.node(MARGIN + 16, 448, 258, 72, "purple", [
        ("Raw Click Archive", "name"),
        ("Parquet on S3 · 73 TB/yr", "sub"),
    ], icon="inventory_2", kind="card", icon_size=24)
    b2 = f.node(MARGIN + 298, 448, 258, 72, "amber", [
        ("Nightly Batch Reconciler", "name"),
        ("Re-aggregates late clicks", "sub"),
    ], icon="loop", kind="card", icon_size=24)
    b3 = f.node(MARGIN + 580, 448, 260, 72, "green", [
        ("Counts API & Billing", "name"),
        ("Dashboards + final bills", "sub"),
    ], icon="table_rows", kind="card", icon_size=24)

    f.wire([b1.right(0), b2.left(0)], tone="purple", dash=True, width=1.8)
    f.wire([b2.right(0), b3.left(0)], tone="amber", dash=True, width=1.8)

    # Card-to-card orthogonal wires (100% centered exits & entries, zero border collisions!)
    f.wire([browsers.bottom(0), c1.top(0)], tone="blue", width=2.0)
    f.label(204, 152, "Click beacons", tone="blue", cls="small")

    f.wire([schema_ctrl.bottom(0), (schema_ctrl.cx, 168), (c2.cx, 168), c2.top(0)],
           tone="purple", dash=True, width=1.7)
    f.label(390, 155, "Schema", tone="purple", cls="small")

    f.wire([flink_ctrl.bottom(0), (flink_ctrl.cx, 168), (c3.cx, 168), c3.top(0)],
           tone="purple", dash=True, width=1.7)
    f.label(650, 155, "Checkpoints", tone="purple", cls="small")

    f.wire([c2.bottom(0), (c2.cx, 369), (b1.cx, 369), b1.top(0)], tone="purple", dash=True, width=1.8)
    f.label(426, 369, "Raw sink (Parquet)", tone="purple", cls="small")

    f.wire([c4.bottom(0), (c4.cx, 369), (b3.cx, 369), b3.top(0)], tone="green", width=2.0)
    f.label(686, 369, "Live counts", tone="green", cls="small")

    # Symmetrically centered numbered step badges (1-6, zero border collisions)
    step_badge(f, c1.cx, 151, 1, "blue")
    step_badge(f, seg_mid(c1.r, c2.x, head=True), c1.cy, 2, "blue")
    step_badge(f, seg_mid(c2.r, c3.x, head=True), c2.cy, 3, "amber")
    step_badge(f, seg_mid(c3.r, c4.x, head=True), c3.cy, 4, "teal")
    step_badge(f, (c2.cx + b1.cx) / 2, 369, 5, "purple")
    step_badge(f, (c4.cx + b3.cx) / 2, 369, 6, "green")

    return f.save([
        ("Solid wires trace the low-latency streaming aggregation path (steps 1-4, 6); dashed wires mark control-plane schemas/checkpoints, raw Parquet archiving (5), and nightly batch reconciliation.", "noteb"),
        "Partitioning the event log by ad_id colocalizes all clicks for a campaign on one stateful stream processor, avoiding costly distributed shuffles.",
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
    f.node(ax1 + 32, 114, 268, 42, "green", [
        ("On-Time (ev 12:00:12..58)", "monob"),
    ], layout="center", kind="card", r=8)
    f.node(ax1 + 320, 162, 210, 42, "amber", [
        ("Late Click (ev 12:00:55)", "monob"),
    ], layout="center", kind="mid", r=8)
    f.node(ax1 + 550, 206, 216, 42, "red", [
        ("Straggler (ev 12:00:40)", "monob"),
    ], layout="center", kind="mid", r=8)

    # Explanatory right-side annotations in empty timeline space
    f.pill(ax1 + 430, 125, "Included in initial emit", tone="green", anchor="start")
    f.pill(ax1 + 550, 173, "Updates window + retract", tone="amber", anchor="start")

    # Bottom Band: 3-Stage Window Lifecycle (48px badged horizontal gaps)
    f.zone(
        MARGIN, 290, INNER, 172, "teal",
        "Window State Lifecycle and Late-Event Routing Policy",
        "Separates fast provisional results from bounded in-memory corrections and unbounded archive recovery",
        icon="rule",
    )
    s1 = f.node(MARGIN + 14, 352, 244, 92, "green", [
        ("1. Watermark Trigger", "name"),
        ("W(t) >= 12:01:00", "monob"),
        ("Emit initial count to OLAP", "small"),
    ], icon="play_arrow", kind="card", icon_size=22)
    s2 = f.node(MARGIN + 306, 352, 244, 92, "amber", [
        ("2. Allowed Lateness", "name"),
        ("12:01 < W <= 12:01:20", "monob"),
        ("Retain RocksDB · Upsert", "small"),
    ], icon="hourglass_top", kind="card", icon_size=22)
    s3 = f.node(MARGIN + 598, 352, 244, 92, "red", [
        ("3. Side Output & Purge", "name"),
        ("W(t) > 12:01:20", "monob"),
        ("Free RAM · Route to batch", "small"),
    ], icon="warning", kind="mid", icon_size=22)

    f.wire([s1.right(0), s2.left(0)], tone="amber", width=1.9)
    f.wire([s2.right(0), s3.left(0)], tone="red", width=1.9)
    step_badge(f, seg_mid(s1.r, s2.x, head=True), s1.cy, 1, "amber")
    step_badge(f, seg_mid(s2.r, s3.x, head=True), s2.cy, 2, "red")

    return f.save([
        ("Watermarks formalize the latency-completeness trade-off: a longer watermark lag captures more out-of-order mobile clicks before emitting, at the cost of higher dashboard delay.", "noteb"),
        "Allowed lateness keeps window state in RocksDB for a bounded grace period to emit incremental retractions (step 1), after which stragglers route to a side output for batch reconciliation (step 2).",
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
