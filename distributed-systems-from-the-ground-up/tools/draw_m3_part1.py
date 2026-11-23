#!/usr/bin/env python3
"""Generate spacious Material Design 3 light+dark SVG figures for Part I (Chapters 2-6).

Every figure prioritizes generous whitespace, concise labels, zero text overflow
in Chrome/Safari, and clean orthogonal routing (WIDTH = 920, MARGIN = 32).
"""
from figkit_m3 import Box, Fig, WIDTH, MARGIN

INNER = WIDTH - 2 * MARGIN  # 856px usable width


def badge_pos(a, b, tail=False):
    """Exact midpoint of visible arrow shaft between a and b (accounting for 9px arrowhead)."""
    if tail:
        return (a + b) / 2
    return (a + b - 9) / 2 if b > a else (a + b + 9) / 2


def step_badge(f, cx, cy, num, tone="blue", ring="paper"):
    """Draw a high-contrast circular step badge (1, 2, 3...) for light & dark modes."""
    f.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="12.0" class="{ring}"/>')
    f.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="9.5" class="a-{tone}"/>')
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
# CHAPTER 2: STORAGE NODE, WAL FORMAT, AND CRASH RECOVERY
# =============================================================================

def ch02_wal_format():
    f = Fig(
        "ch02_wal_format",
        "Figure 2-1. On-Disk Write-Ahead Log Frame Layout and MemTable Write Path.",
        452,
    )

    # Top Zone: On-disk WAL Frame Layout
    f.zone(
        MARGIN, 0, INNER, 198, "blue",
        "On-Disk WAL Record Frame Layout (Little-Endian Byte Order)",
        "Append-only file · Fixed 8-byte header frames variable-length checksummed payload",
        icon="description",
    )

    # 5 framed record fields spanning x=50..870 (820px total)
    fields = [
        ("len", "4 B · u32 LE", 126, "purple", "mid"),
        ("CRC32C", "4 B · checksum", 142, "amber", "mid"),
        ("op", "1 B · PUT/DEL", 132, "teal", "card"),
        ("key", "2 B len + key bytes", 204, "blue", "card"),
        ("val", "remaining val bytes", 200, "green", "card"),
    ]
    fx = MARGIN + 18
    fy = 66
    fh = 76
    fgap = 4
    for title, sub, fw, tone, kind in fields:
        f.cell(fx, fy, fw, fh, tone, [(title, "monob"), (sub, "small")], kind=kind, r=8)
        fx += fw + fgap

    # Span brackets underneath header vs. payload
    hdr_x1, hdr_x2 = MARGIN + 18, MARGIN + 18 + 126 + fgap + 142
    pay_x1, pay_x2 = hdr_x2 + fgap, WIDTH - MARGIN - 18
    f.rule(hdr_x1, 156, hdr_x2, 156, tone="purple", width=1.6)
    f.rule(hdr_x1, 151, hdr_x1, 161, tone="purple", width=1.6)
    f.rule(hdr_x2, 151, hdr_x2, 161, tone="purple", width=1.6)
    f.text((hdr_x1 + hdr_x2) / 2, 178, "Frame Header (8 bytes)", "small", "middle", tone="purple")

    f.rule(pay_x1, 156, pay_x2, 156, tone="blue", width=1.6)
    f.rule(pay_x1, 151, pay_x1, 161, tone="blue", width=1.6)
    f.rule(pay_x2, 151, pay_x2, 161, tone="blue", width=1.6)
    f.text((pay_x1 + pay_x2) / 2, 178, "Checksummed Payload (len bytes protected by CRC32C)", "small", "middle", tone="blue")

    # Bottom Zone: Synchronous Write Path
    f.zone(
        MARGIN, 222, INNER, 222, "teal",
        "Synchronous Write Path: WAL Durability Precedes MemTable Visibility",
        "A crash before fsync completes leaves both the log prefix and in-memory map clean",
        icon="save",
    )

    stages = [
        ("Encode Frame", "Serialize op, key, val", "Compute CRC32C", "blue", "code"),
        ("Append + fsync", "Sequential write()", "Flush to NVMe media", "amber", "save"),
        ("Mutate MemTable", "Update BTreeMap", "Advance sequence ID", "teal", "memory"),
        ("Acknowledge", "Return HTTP 200", "Write is durable", "green", "play_arrow"),
    ]
    sw = 168
    sgap = 48
    sx0 = MARGIN + 20
    boxes = []
    for i, (t, s1, s2, tone, ic) in enumerate(stages):
        sx = sx0 + i * (sw + sgap)
        b = f.node(
            sx, 286, sw, 114, tone,
            [(t, "name"), (s1, "sub"), (s2, "small")],
            icon=ic, layout="center", kind="card", icon_size=26,
        )
        boxes.append(b)
    badge_tones = ["blue", "amber", "teal"]
    for i in range(3):
        f.wire([boxes[i].right(0), boxes[i + 1].left(0)], tone=badge_tones[i], width=1.9)
        step_badge(f, badge_pos(boxes[i].r, boxes[i + 1].x), boxes[i].cy, str(i + 1), badge_tones[i], ring="c-teal")
    step_badge(f, boxes[3].r - 16, boxes[3].y + 16, "4", "green", ring="card")

    f.text(
        WIDTH / 2, 426,
        "Durability invariant: MemTable mutation and client acknowledgment occur only after fsync returns.",
        "small", "middle", tone="teal",
    )

    return f.save([
        ("Every record begins with an 8-byte header holding the payload length and CRC32C checksum so partial or corrupted tails are detected deterministically.", "noteb"),
        "Appending sequentially to the write-ahead log and flushing with fsync before updating the in-memory BTreeMap guarantees that acknowledged writes survive process crashes and power loss.",
    ])


def ch02_crash_recovery():
    f = Fig(
        "ch02_crash_recovery",
        "Figure 2-2. Crash Recovery Replay, Torn-Tail Truncation, and Compaction.",
        536,
    )

    # Top Zone: Sequential WAL scan and torn-tail truncation
    f.zone(
        MARGIN, 0, INNER, 196, "amber",
        "Sequential Startup Scan and Torn-Tail Truncation",
        "Recovery reads from offset 0, checks each CRC32C, and stops at the first corrupt byte",
        icon="warning",
    )

    frames = [
        ("Frame 1 (seq 1)", "PUT u1=ada · CRC OK", 184, "green", "card"),
        ("Frame 2 (seq 2)", "PUT u2=bob · CRC OK", 184, "green", "card"),
        ("Frame 3 (seq 3)", "DEL u1 · CRC OK", 184, "green", "card"),
        ("Torn Tail (96..112)", "CRC mismatch / EOF", 212, "red", "mid"),
    ]
    fx = MARGIN + 20
    fgap = 16
    for idx, (hdr, sub, fw, tone, kind) in enumerate(frames):
        f.cell(fx, 62, fw, 74, tone, [(hdr, "monob"), (sub, "small")], kind=kind, r=9)
        if idx == 2:
            boundary_x = fx + fw + fgap / 2
            f.rule(boundary_x, 52, boundary_x, 150, tone="red", width=2.0, dash="5 4")
        fx += fw + fgap

    f.pill(MARGIN + 20, 156, "Valid prefix replayed (bytes 0..95)", tone="green", anchor="start")
    f.pill(WIDTH - MARGIN - 20, 156, "ftruncate(fd, 96) drops partial frame", tone="red", anchor="end")

    # Bottom-left Zone: MemTable Reconstruction (50px vertical gap, 52px horizontal gap)
    lw = 402
    f.zone(
        MARGIN, 246, lw, 280, "blue",
        "BTreeMap MemTable Rebuild",
        "Deterministic replay restores live key state",
        icon="memory",
    )
    m1 = f.node(
        MARGIN + 18, 308, lw - 36, 68, "blue",
        [("Apply Frames 1..3 in Order", "name"), ("PUT u1 -> PUT u2 -> DEL u1", "mono")],
        icon="table_rows", kind="card", icon_size=26,
    )
    m2 = f.node(
        MARGIN + 18, 428, lw - 36, 68, "green",
        [("Recovered MemTable Ready", "name"), ("Live map: { u2 -> bob }", "mono")],
        icon="layers", kind="card", icon_size=26,
    )
    f.wire([m1.bottom(0), m2.top(0)], tone="blue", width=1.9)
    step_badge(f, m1.cx, badge_pos(m1.b, m2.y), "2", "blue", ring="c-blue")

    # Bottom-right Zone: Atomic Log Compaction
    rx = MARGIN + lw + 52  # 486
    rw = WIDTH - MARGIN - rx  # 402
    f.zone(
        rx, 246, rw, 280, "teal",
        "Atomic Snapshot and Compaction",
        "Eliminates obsolete overwrites and tombstones",
        icon="folder",
    )
    c1 = f.node(
        rx + 18, 308, rw - 36, 68, "teal",
        [("Write wal.compact.tmp", "name"), ("Live keys only + fsync(tmp)", "sub")],
        icon="save", kind="card", icon_size=26,
    )
    c2 = f.node(
        rx + 18, 428, rw - 36, 68, "purple",
        [("Atomic rename() + dir fsync", "name"), ("wal.compact.tmp -> wal.log", "mono")],
        icon="shield", kind="card", icon_size=26,
    )
    f.wire([c1.bottom(0), c2.top(0)], tone="teal", width=1.9)
    step_badge(f, c1.cx, badge_pos(c1.b, c2.y), "4", "teal", ring="c-teal")

    # Step 1: Valid scan -> MemTable rebuild (50px vertical gap)
    f.wire([(MARGIN + lw / 2, 196), (MARGIN + lw / 2, 246)], tone="green", width=1.9)
    step_badge(f, MARGIN + lw / 2, badge_pos(196, 246), "1", "green")

    # Step 3: Recovered state -> Periodic compaction (52px horizontal gap)
    f.wire([(MARGIN + lw, 386), (rx, 386)], tone="teal", dash=True, width=1.8)
    step_badge(f, badge_pos(MARGIN + lw, rx), 386, "3", "teal")

    return f.save([
        ("Crash recovery scans frames sequentially from offset zero, truncating any torn tail before replaying the valid prefix (1) into the BTreeMap MemTable (2).", "noteb"),
        "Periodic compaction (3) bounds restart latency by writing live entries to a temporary file, calling fsync, and replacing the old log via atomic rename and directory fsync (4).",
    ])


# =============================================================================
# CHAPTER 3: LEADER-FOLLOWER REPLICATION AND FAULT MODES
# =============================================================================

def ch03_replication_flow():
    f = Fig(
        "ch03_replication_flow",
        "Figure 3-1. Leader-Follower Write Replication and Commit Index Advancement.",
        514,
    )

    # Left: Client card
    cli = f.node(
        MARGIN, 174, 166, 118, "blue",
        [("App / Edge Client", "name"), ("PUT k=v · L7 LB", "mono"), ("Awaits ACK", "small")],
        icon="laptop", layout="center", kind="card", icon_size=28,
    )

    # Middle: Leader Zone
    lx = 246
    lw = 264
    f.zone(
        lx, 0, lw, 466, "amber",
        "Leader Node (Term 4)",
        "Quorum = 2 of 3 replicas",
        icon="dns",
    )
    l1 = f.node(
        lx + 16, 60, lw - 32, 86, "amber",
        [("Append Local WAL", "name"), ("Assign log idx = 42", "mono"), ("fsync to local disk", "small")],
        icon="save", kind="card", icon_size=24,
    )
    l2 = f.node(
        lx + 16, 196, lw - 32, 92, "teal",
        [("Replicate in Parallel", "name"), ("Send AppendEntries", "sub"), ("Wait for majority ACK", "small")],
        icon="swap_horiz", kind="card", icon_size=24,
    )
    l3 = f.node(
        lx + 16, 338, lw - 32, 112, "green",
        [("Commit & Apply", "name"), ("commitIndex = 42", "mono"), ("Apply to MemTable", "sub"), ("Reply 200 OK", "small")],
        icon="play_arrow", kind="card", icon_size=24,
    )
    f.wire([l1.bottom(0), l2.top(0)], tone="amber", width=1.9)
    step_badge(f, l1.cx, badge_pos(l1.b, l2.y), "2", "amber", ring="c-amber")
    f.wire([l2.bottom(0), l3.top(0)], tone="green", width=1.9)
    step_badge(f, l2.cx, badge_pos(l2.b, l3.y), "4", "green", ring="c-amber")

    # Right: Follower Replicas Zone
    rx = 602
    rw = WIDTH - MARGIN - rx  # 286
    f.zone(
        rx, 0, rw, 466, "blue",
        "Follower Replicas",
        "Independent failure domains",
        icon="layers",
    )
    fa = f.node(
        rx + 16, 74, rw - 32, 116, "green",
        [("Follower A (Fast)", "name"), ("Append idx=42 + fsync", "mono"), ("ACK in 1.2 ms", "small")],
        icon="developer_board", kind="card", icon_size=26,
    )
    f.pill(rx + rw / 2, 206, "Majority reached (2 of 3)", tone="green", anchor="middle")

    fb = f.node(
        rx + 16, 268, rw - 32, 116, "gray",
        [("Follower B (Slow)", "name"), ("Network or disk delay", "sub"), ("Applies asynchronously", "small")],
        icon="hourglass_top", kind="tonal", icon_size=26,
    )
    f.pill(rx + rw / 2, 400, "Off write critical path", tone="gray", anchor="middle")

    # Orthogonal wires: Client <-> Leader
    f.wire([cli.right(-22), (222, cli.cy - 22), (222, l1.cy), l1.left(0)], tone="blue", width=1.9)
    f.label(162, 116, "PUT(k, v)", tone="blue", cls="small")
    step_badge(f, 222, (cli.cy - 22 + l1.cy) / 2, "1", "blue")

    f.wire([l3.left(0), (222, l3.cy), (222, cli.cy + 26), cli.right(26)], tone="green", width=1.9)
    f.label(162, 386, "200 OK", tone="green", cls="small")
    step_badge(f, 222, (l3.cy + cli.cy + 26) / 2, "5", "green")

    # Symmetric Split / Fan-Out: Leader l2 -> Follower A (sync quorum) & Follower B (async)
    # Exact horizontal midpoint between l2.r (494) and fa.x (618) is x_mid = 556 (62px each side)
    x_mid = (l2.r + fa.x) / 2  # 556.0
    f.wire([l2.right(0), (x_mid, l2.cy)], tone="amber", width=1.9, head=False)
    f.wire([(x_mid, l2.cy), (x_mid, fa.cy), fa.left(0)], tone="amber", width=1.9, tail=False)
    f.wire([(x_mid, l2.cy), (x_mid, fb.cy), fb.left(0)], tone="gray", dash=True, width=1.6)
    f.label(x_mid, 108, "Append / ACK", tone="amber", cls="small")
    step_badge(f, x_mid, (l2.cy + fa.cy) / 2, "3", "amber")
    f.label(x_mid, 352, "Async RPC", tone="gray", cls="small")

    path_legend(
        f, 478,
        "Solid: Sync quorum write path (1->5)",
        "Dashed: Async slow-follower replication",
    )

    return f.save([
        ("The leader persists each write to its local write-ahead log first (1-2), then replicates AppendEntries in parallel to all followers (3).", "noteb"),
        "Once a majority of replicas acknowledge the entry, the leader advances its commit index, applies the mutation to the state machine (4), and replies 200 OK (5) without waiting for the slowest follower.",
    ])


def ch03_quorum_failover():
    f = Fig(
        "ch03_quorum_failover",
        "Figure 3-2. Replication Fault Modes: Stale Follower Catch-Up and Split-Brain Risk.",
        498,
    )

    lw = 416
    # Left Panel: Stale Follower Catch-Up
    f.zone(
        MARGIN, 0, lw, 490, "teal",
        "Mode A: Stale Follower Catch-Up",
        "Missing log suffix replicated incrementally from Leader",
        icon="loop",
    )

    # Leader Log box
    f.rect(MARGIN + 18, 62, lw - 36, 108, "card", r=12, lift=True)
    f.text(MARGIN + 32, 86, "Leader WAL (nextIndex[F2] = 41)", "monob", "start", tone="amber")
    for i, (lbl, tone, kind) in enumerate([
        ("40: k=a", "green", "mid"),
        ("41: k=b", "amber", "mid"),
        ("42: k=c", "amber", "mid"),
        ("43: k=d", "amber", "mid"),
    ]):
        f.cell(MARGIN + 32 + i * 89, 102, 83, 52, tone, [(lbl, "monob")], kind=kind, r=7)

    # Step 1: Replication wire down (66px gap: 170..236)
    cx_l = MARGIN + lw / 2
    f.wire([(cx_l, 170), (cx_l, 236)], tone="teal", width=1.9)
    step_badge(f, cx_l, badge_pos(170, 236), "1", "teal", ring="c-teal")
    f.label(cx_l + 96, 203, "AppendEntries(41..43)", tone="teal", cls="small", back_cls="c-teal")

    # Follower Log box
    f.rect(MARGIN + 18, 236, lw - 36, 108, "card", r=12, lift=True)
    f.text(MARGIN + 32, 260, "Lagging Follower B (Prefix Matches Through 40)", "sub", "start", tone="teal")
    for i, (lbl, tone, kind) in enumerate([
        ("40: k=a", "green", "mid"),
        ("41: ?", "gray", "dashed"),
        ("42: ?", "gray", "dashed"),
        ("43: ?", "gray", "dashed"),
    ]):
        f.cell(MARGIN + 32 + i * 89, 276, 83, 52, tone, [(lbl, "monob")], kind=kind, r=7)

    # Step 2: Suffix replay -> Convergence (52px gap: 344..396)
    f.wire([(cx_l, 344), (cx_l, 396)], tone="green", width=1.9)
    step_badge(f, cx_l, badge_pos(344, 396), "2", "green", ring="c-teal")

    # Outcome card
    f.node(
        MARGIN + 18, 396, lw - 36, 76, "green",
        [("Converged After Suffix Replay", "name"), ("Follower syncs 41..43 and rejoins quorum", "sub")],
        icon="play_arrow", kind="card", icon_size=26,
    )

    # Right Panel: Split-Brain Risk
    rx = MARGIN + lw + 24
    rw = WIDTH - MARGIN - rx  # 416
    f.zone(
        rx, 0, rw, 490, "red",
        "Mode B: Partitioned Leader Split-Brain",
        "Why naive failover fails without consensus fencing",
        icon="warning",
    )

    f.rect(rx + 18, 62, rw - 36, 118, "card", r=12, lift=True)
    f.pill(rx + 32, 74, "MINORITY PARTITION (1 of 3)", tone="red", anchor="start")
    f.text(rx + 32, 118, "Isolated Old Leader A", "name", "start", tone="red")
    f.text(rx + 32, 140, "Unfenced leader still accepts PUT k=v1", "sub", "start")
    f.text(rx + 32, 160, "Divergent write is lost upon heal", "small", "start")

    f.rule(rx + 18, 206, rx + rw - 18, 206, tone="red", width=2.0, dash="8 5")
    f.label(rx + rw / 2, 210, "NETWORK PARTITION", tone="red", cls="badge", back_cls="c-red")

    f.rect(rx + 18, 232, rw - 36, 126, "card", r=12, lift=True)
    f.pill(rx + 32, 244, "MAJORITY PARTITION (2 of 3)", tone="green", anchor="start")
    f.text(rx + 32, 288, "Promoted Leader B + Follower C", "name", "start", tone="green")
    f.text(rx + 32, 310, "Commits PUT k=v2 independently", "sub", "start")
    f.text(rx + 32, 332, "Two concurrent writers violate safety", "small", "start")

    f.node(
        rx + 18, 396, rw - 36, 76, "purple",
        [("Motivation for Chapter 4 Consensus", "name"), ("Quorum elections + monotonic terms fence A", "sub")],
        icon="shield", kind="mid", icon_size=26,
    )

    return f.save([
        ("A lagging follower recovers safely by requesting the missing log suffix (1) after its highest matching entry index and rejoining the quorum (2).", "noteb"),
        "By contrast, a network partition can leave an isolated primary believing it is still the leader, requiring Raft terms and quorum voting to fence stale leaders.",
    ])


# =============================================================================
# CHAPTER 4: RAFT LEADER ELECTION AND LOG MATCHING
# =============================================================================

def ch04_raft_states():
    f = Fig(
        "ch04_raft_states",
        "Figure 4-1. Raft Server Role State Machine and Term Transitions.",
        474,
    )

    # Startup trigger card top-left
    start = f.node(
        MARGIN, 10, 178, 52, "gray",
        [("Node Boot", "name"), ("currentTerm = 0", "mono")],
        icon="play_arrow", kind="tonal", icon_size=22,
    )

    # Three spacious state cards across middle row
    cw = 248
    ch = 178
    cy = 158
    gap = 56
    x_f = MARGIN
    x_c = MARGIN + cw + gap        # 336
    x_l = MARGIN + 2 * (cw + gap)  # 640

    # Follower card
    f.rect(x_f, cy, cw, ch, "card", r=14, lift=True)
    f.tile(x_f + 16, cy + 16, "dns", "blue", 30)
    f.text(x_f + 56, cy + 36, "Follower", "head", "start", tone="blue")
    f.text(x_f + 18, cy + 72, "Passive RPC responder", "sub", "start")
    f.text(x_f + 18, cy + 94, "Grants at most 1 vote/term", "sub", "start")
    f.text(x_f + 18, cy + 116, "Heartbeat resets timer", "sub", "start")
    f.pill(x_f + 18, cy + 140, "Default safe role", tone="blue", anchor="start")
    bf = Box(x_f, cy, cw, ch)

    # Candidate card
    f.rect(x_c, cy, cw, ch, "card", r=14, lift=True)
    f.tile(x_c + 16, cy + 16, "pending", "amber", 30)
    f.text(x_c + 56, cy + 36, "Candidate", "head", "start", tone="amber")
    f.text(x_c + 18, cy + 72, "Increments currentTerm", "sub", "start")
    f.text(x_c + 18, cy + 94, "Votes for self immediately", "sub", "start")
    f.text(x_c + 18, cy + 116, "Broadcasts RequestVote", "sub", "start")
    f.pill(x_c + 18, cy + 140, "Transient election role", tone="amber", anchor="start")
    bc = Box(x_c, cy, cw, ch)

    # Leader card
    f.rect(x_l, cy, cw, ch, "card", r=14, lift=True)
    f.tile(x_l + 16, cy + 16, "shield", "green", 30)
    f.text(x_l + 56, cy + 36, "Leader", "head", "start", tone="green")
    f.text(x_l + 18, cy + 72, "Accepts client writes", "sub", "start")
    f.text(x_l + 18, cy + 94, "Replicates AppendEntries", "sub", "start")
    f.text(x_l + 18, cy + 116, "Sends periodic heartbeats", "sub", "start")
    f.pill(x_l + 18, cy + 140, "Unique per Raft term", tone="green", anchor="start")
    bl = Box(x_l, cy, cw, ch)

    # 1. Startup -> Follower (96px vertical drop)
    f.wire([start.bottom(0), (start.cx, cy)], tone="wire", width=1.9)
    step_badge(f, start.cx, badge_pos(start.b, cy), "1", "gray")

    # 2. Follower -> Candidate (upper channel y=110, 164px horizontal leg)
    f.wire([bf.top(64), (bf.cx + 64, 110), (bc.cx - 76, 110), bc.top(-76)], tone="amber", width=1.9)
    f.label((bf.cx + 64 + bc.cx - 76) / 2, 92, "Election timeout / term++", tone="amber", cls="small")
    step_badge(f, (bf.cx + 64 + bc.cx - 76) / 2, 110, "2", "amber")

    # 3. Candidate split-vote self-loop (top lane y=46, 56px horizontal leg)
    f.wire([bc.top(-28), (bc.cx - 28, 46), (bc.cx + 28, 46), bc.top(28)], tone="amber", dash=True, width=1.6)
    f.label(bc.cx, 26, "Split vote: timeout / term++", tone="amber", cls="small")
    step_badge(f, bc.cx, 46, "3", "amber")

    # 4. Candidate -> Leader (upper channel y=110, 164px horizontal leg)
    f.wire([bc.top(76), (bc.cx + 76, 110), (bl.cx - 64, 110), bl.top(-64)], tone="green", width=1.9)
    f.label((bc.cx + 76 + bl.cx - 64) / 2, 92, "Wins majority votes", tone="green", cls="small")
    step_badge(f, (bc.cx + 76 + bl.cx - 64) / 2, 110, "4", "green")

    # 5. Candidate -> Follower (lower channel 1, y=378, 216px horizontal leg)
    f.wire([bc.bottom(-36), (bc.cx - 36, 378), (bf.cx + 52, 378), bf.bottom(52)], tone="blue", width=1.9)
    f.label((bc.cx - 36 + bf.cx + 52) / 2, 400, "Valid leader or higher term", tone="blue", cls="small")
    step_badge(f, (bc.cx - 36 + bf.cx + 52) / 2, 378, "5", "blue")

    # 6. Leader -> Follower (lower channel 2, y=434, 656px horizontal leg)
    f.wire([bl.bottom(0), (bl.cx, 434), (bf.cx - 48, 434), bf.bottom(-48)], tone="red", width=1.9)
    f.label((bl.cx + bf.cx - 48) / 2, 456, "Discovers higher term (term' > currentTerm) -> step down", tone="red", cls="small")
    step_badge(f, (bl.cx + bf.cx - 48) / 2, 434, "6", "red")

    return f.save([
        ("Every Raft server begins as a Follower (1) and transitions to Candidate (2) only when an election timeout elapses; split votes retry in a new term (3) until a majority elects a Leader (4).", "noteb"),
        "Discovering a valid leader or strictly higher term forces a Candidate (5) or Leader (6) to step down immediately, preserving the single-leader-per-term invariant.",
    ])


def ch04_log_matching():
    f = Fig(
        "ch04_log_matching",
        "Figure 4-2. Raft Log Matching Property and Safety Across Term Boundaries.",
        476,
    )

    # Top Zone: Log Index Grid
    f.zone(
        MARGIN, 0, INNER, 302, "blue",
        "Replicated Log Index Grid Across Terms 1 to 3",
        "Identical (index, term) implies identical prefix · Leader truncates conflicting follower tails",
        icon="table_rows",
    )

    # Column geometry: row label x=48..200, 6 index cells x=208..868 (each 102w + 8 gap = 652)
    col_x0 = 212
    col_w = 100
    col_gap = 10
    for i in range(6):
        cx = col_x0 + i * (col_w + col_gap) + col_w / 2
        f.text(cx, 68, f"Index {i + 1}", "monob", "middle", tone="blue")

    rows = [
        ("Leader (T3)", "amber", [
            ("T1 · x=1", "green", "mid"),
            ("T1 · y=2", "green", "mid"),
            ("T2 · x=5", "green", "mid"),
            ("T3 · z=9", "amber", "mid"),
            ("T3 · x=7", "amber", "card"),
            ("(empty)", "gray", "dashed"),
        ]),
        ("Follower A (T3)", "teal", [
            ("T1 · x=1", "green", "mid"),
            ("T1 · y=2", "green", "mid"),
            ("T2 · x=5", "green", "mid"),
            ("T3 · z=9", "amber", "mid"),
            ("(pending)", "gray", "dashed"),
            ("(empty)", "gray", "dashed"),
        ]),
        ("Follower B (Old)", "red", [
            ("T1 · x=1", "green", "mid"),
            ("T1 · y=2", "green", "mid"),
            ("T2 · x=5", "green", "mid"),
            ("T2 · z=4", "red", "mid"),
            ("T2 · w=8", "red", "mid"),
            ("(truncate)", "red", "dashed"),
        ]),
    ]

    for r_idx, (r_lbl, r_tone, cells) in enumerate(rows):
        ry = 80 + r_idx * 58
        f.text(MARGIN + 18, ry + 29, r_lbl, "name", "start", tone=r_tone, fit=(MARGIN + 14, col_x0 - 8))
        for c_idx, (txt, tone, kind) in enumerate(cells):
            cx = col_x0 + c_idx * (col_w + col_gap)
            f.cell(cx, ry, col_w, 46, tone, [(txt, "monob")], kind=kind, r=8)

    # Vertical dashed line separating committed prefix (Idx 1..3) from uncommitted suffix
    commit_x = col_x0 + 3 * col_w + 2.5 * col_gap
    f.rule(commit_x, 74, commit_x, 254, tone="green", width=2.0, dash="5 4")

    # Legend pills inside bottom of zone
    f.pill(MARGIN + 18, 266, "Committed prefix (Idx 1..3)", tone="green", anchor="start")
    f.pill(commit_x, 266, "Current-term quorum (Idx 4, T3)", tone="amber", anchor="middle")
    f.pill(WIDTH - MARGIN - 18, 266, "Divergent T2 tail overwritten", tone="red", anchor="end")

    # Bottom two safety rule panels
    lw = 416
    rx = MARGIN + lw + 24
    rw = WIDTH - MARGIN - rx
    f.zone(
        MARGIN, 322, lw, 146, "teal",
        "1. Consistency Check and Truncation",
        "AppendEntries verifies (prevLogIndex, prevLogTerm)",
        icon="rule",
    )
    f.node(
        MARGIN + 18, 382, lw - 36, 70, "teal",
        [("Conflict Resolution on Follower B", "name"), ("Rejects prev=(4, T3) -> leader backs up to", "sub"), ("Index 3 and overwrites stale T2 entries", "small")],
        kind="card",
    )

    f.zone(
        rx, 322, rw, 146, "purple",
        "2. Current-Term Commit Rule",
        "Prevents overwriting old-term majority entries",
        icon="shield",
    )
    f.node(
        rx + 18, 382, rw - 36, 70, "purple",
        [("Commit Only Current-Term Entries", "name"), ("Index 4 (T3) replicates to 2 of 3 nodes,", "sub"), ("indirectly committing all preceding entries", "small")],
        kind="card",
    )

    return f.save([
        ("Raft enforces the Log Matching Property by checking both prevLogIndex and prevLogTerm on every AppendEntries RPC and overwriting any conflicting follower suffix.", "noteb"),
        "A new leader commits entries from earlier terms only indirectly by committing an entry from its own current term on a majority of servers.",
    ])


# =============================================================================
# CHAPTER 5: STATELESS ROUTING TIER AND EPOCH REDIRECTION
# =============================================================================

def ch05_router_topology():
    f = Fig(
        "ch05_router_topology",
        "Figure 5-1. Stateless Routing Tier, Partition Map, and Leader Redirection.",
        538,
    )

    # Top-left: Entry Devices & Client
    cli = f.node(
        MARGIN, 14, 240, 88, "blue",
        [("Mobile / Web (L7 LB)", "name"), ("PUT /v1/keys/u42", "mono")],
        icon="laptop", kind="card", icon_size=28,
    )

    # Top-right: Control Plane
    cp_x = 324
    cp_w = WIDTH - MARGIN - cp_x  # 564
    f.zone(
        cp_x, 0, cp_w, 126, "purple",
        "Control Plane (Metadata & Epoch Authority)",
        "Authoritative hash ring · Monotonic cluster epoch (e = 14)",
        icon="settings_suggest", dashed=True,
    )
    cp1 = f.node(
        cp_x + 16, 56, 250, 56, "purple",
        [("Metadata Raft", "name"), ("Epoch 14 · Ring map", "sub")],
        icon="dns", kind="card", icon_size=24,
    )
    cp2 = f.node(
        cp_x + 298, 56, 250, 56, "purple",
        [("Epoch Watch Stream", "name"), ("Pushes ring updates", "sub")],
        icon="notifications_active", kind="card", icon_size=24,
    )
    f.wire([cp1.right(0), cp2.left(0)], tone="purple", width=1.8)

    # Middle: Stateless Routing Tier (56px gap below cli)
    r_zone = f.zone(
        MARGIN, 158, INNER, 134, "teal",
        "Stateless Routing Tier (In-Memory Ring Map + Leader Hint Cache)",
        "Any router instance computes the target shard and routes directly to its active Raft Leader",
        icon="swap_horiz",
    )
    r1 = f.node(
        50, 214, 234, 62, "teal",
        [("Hash Key", "name"), ("xxhash64(u42)", "mono")],
        icon="code", kind="card", icon_size=24,
    )
    r2 = f.node(
        334, 214, 234, 62, "blue",
        [("Ring Lookup", "name"), ("Token -> Shard 02", "mono")],
        icon="loop", kind="card", icon_size=24,
    )
    r3 = f.node(
        618, 214, 252, 62, "amber",
        [("Leader Hint", "name"), ("Shard 02 -> Node B", "mono")],
        icon="call_split", kind="card", icon_size=24,
    )
    f.wire([r1.right(0), r2.left(0)], tone="teal", width=1.9)
    step_badge(f, badge_pos(r1.r, r2.x), r1.cy, "2", "teal", ring="c-teal")
    f.wire([r2.right(0), r3.left(0)], tone="blue", width=1.9)
    step_badge(f, badge_pos(r2.r, r3.x), r2.cy, "3", "blue", ring="c-teal")

    # Bottom: Partitioned Multi-Raft Storage Tier (50px gap below r_zone; concise header leaves x >= 600 clear)
    f.zone(
        MARGIN, 342, INNER, 148, "blue",
        "Storage Tier: Partitioned 3-Node Raft Groups",
        "Direct leader RPC · Zero extra forwarding hops",
        icon="layers",
    )

    # Shard 01 box
    s1_x, sw = MARGIN + 18, 398
    f.rect(s1_x, 398, sw, 78, "card", r=11, lift=True)
    f.text(s1_x + 14, 419, "Shard 01  (Tokens 0x0000..0x7FFF)", "monob", "start", tone="blue")
    f.cell(s1_x + 14, 430, 132, 34, "amber", [("Node A (Leader)", "badge")], kind="mid", r=7)
    f.cell(s1_x + 156, 430, 108, 34, "gray", [("Node B (F)", "badge")], kind="tonal", r=7)
    f.cell(s1_x + 274, 430, 108, 34, "gray", [("Node C (F)", "badge")], kind="tonal", r=7)

    # Shard 02 box
    s2_x = s1_x + sw + 24
    f.rect(s2_x, 398, sw, 78, "card", r=11, lift=True)
    f.text(s2_x + 14, 419, "Shard 02  (Tokens 0x8000..0xFFFF)", "monob", "start", tone="green")
    f.cell(s2_x + 14, 430, 108, 34, "gray", [("Node A (F)", "badge")], kind="tonal", r=7)
    f.cell(s2_x + 132, 430, 134, 34, "green", [("Node B (Leader)", "badge")], kind="mid", r=7)
    f.cell(s2_x + 276, 430, 108, 34, "gray", [("Node C (F)", "badge")], kind="tonal", r=7)

    # Orthogonal wires (all badged gaps >= 50px)
    f.wire([cli.bottom(0), (cli.cx, r_zone.y)], tone="blue", width=2.0)
    f.label(cli.cx + 68, 131, "HTTP PUT", tone="blue", cls="small")
    step_badge(f, cli.cx, badge_pos(cli.b, r_zone.y), "1", "blue")

    f.wire([cp2.bottom(0), (cp2.cx, r_zone.y)], tone="purple", dash=True, width=1.7)
    f.label(cp2.cx - 86, 144, "Epoch e=14 watch", tone="purple", cls="small")

    # Router r3 -> Shard 02 Leader Node B (73px horizontal leg at exact gutter midpoint y=317)
    target_x = s2_x + 199
    y_gutter = (r_zone.b + 342) / 2  # 317.0
    f.wire([r3.bottom(0), (r3.cx, y_gutter), (target_x, y_gutter), (target_x, 398)], tone="green", width=2.0)
    f.label(588, y_gutter + 4, "gRPC PUT -> Node B", tone="green", cls="small")
    step_badge(f, (r3.cx + target_x) / 2, y_gutter, "4", "green")
    step_badge(f, s2_x + sw - 18, 414, "5", "green", ring="card")

    path_legend(
        f, 502,
        "Solid: Sync routing path (1 PUT -> 2-3 Lookup -> 4 gRPC -> 5 Quorum)",
        "Dashed: Async control-plane epoch watch",
    )

    return f.save([
        ("Stateless routers decouple client connections from storage placement by caching the consistent hash ring and per-shard leader hints in memory.", "noteb"),
        "The control plane propagates topology epochs asynchronously; routers remain available during control-plane outages and learn leader changes directly from storage responses.",
    ])


def ch05_epoch_redirect():
    f = Fig(
        "ch05_epoch_redirect",
        "Figure 5-2. Stale Route Detection and NOT_LEADER Retry Protocol.",
        498,
    )

    # 4 participant header cards across width (4*188 + 3*34 = 854)
    pw = 188
    pgap = 34
    px = [MARGIN + 1 + i * (pw + pgap) for i in range(4)]
    cxs = [x + pw / 2 for x in px]

    headers = [
        ("Client", "Idempotent PUT", "blue", "laptop"),
        ("Stateless Router", "Cache: N1 (T4)", "teal", "swap_horiz"),
        ("Node 1 (Old)", "Follower (T5)", "red", "warning"),
        ("Node 2 (Leader)", "Active (T5)", "green", "dns"),
    ]
    for i, (t, sub, tone, ic) in enumerate(headers):
        f.node(px[i], 0, pw, 62, tone, [(t, "name"), (sub, "mono")], icon=ic, kind="card", icon_size=24)
        f.rule(cxs[i], 62, cxs[i], 486, tone="gray", width=1.4, dash="4 4")

    # Step 1: Client -> Router
    y1 = 108
    bx1 = badge_pos(cxs[0], cxs[1])
    f.wire([(cxs[0], y1), (cxs[1], y1)], tone="blue", width=2.0)
    f.label(bx1, y1 - 16, "PUT /keys/u42", tone="blue", cls="small")
    step_badge(f, bx1, y1, "1", "blue")

    # Step 2: Router -> Demoted Node 1
    y2 = 164
    bx2 = badge_pos(cxs[1], cxs[2])
    f.wire([(cxs[1], y2), (cxs[2], y2)], tone="amber", width=2.0)
    f.label(bx2, y2 - 16, "Write(u42, term=4)", tone="amber", cls="small")
    step_badge(f, bx2, y2, "2", "amber")

    # Step 3: Demoted Node 1 -> Router (NOT_LEADER)
    y3 = 220
    bx3 = badge_pos(cxs[2], cxs[1])
    f.wire([(cxs[2], y3), (cxs[1], y3)], tone="red", dash=True, width=1.9)
    f.label(bx3, y3 - 16, "NOT_LEADER(N2, T5)", tone="red", cls="monob")
    step_badge(f, bx3, y3, "3", "red")

    # Step 4: Router updates cached leader map
    upd = f.node(
        cxs[1] - 110, 252, 220, 54, "purple",
        [("Update Leader Cache", "name"), ("Shard 02 -> N2 (T5)", "mono")],
        layout="center", kind="mid", r=10,
    )
    step_badge(f, upd.x, upd.cy, "4", "purple")

    # Step 5: Router -> New Leader Node 2 (transparent retry)
    y5 = 352
    bx5 = badge_pos(cxs[1], cxs[3])
    f.wire([(cxs[1], y5), (cxs[3], y5)], tone="green", width=2.0)
    f.label(bx5, y5 - 16, "Transparent Retry: Write(u42, term=5)", tone="green", cls="small")
    step_badge(f, bx5, y5, "5", "green")

    # Step 6: Node 2 -> Router (Quorum ACK)
    y6 = 408
    bx6 = badge_pos(cxs[3], cxs[1])
    f.wire([(cxs[3], y6), (cxs[1], y6)], tone="green", width=2.0)
    f.label(bx6, y6 - 16, "Quorum Commit OK (idx=88)", tone="green", cls="small")
    step_badge(f, bx6, y6, "6", "green")

    # Step 7: Router -> Client (single attempt)
    y7 = 464
    bx7 = badge_pos(cxs[1], cxs[0])
    f.wire([(cxs[1], y7), (cxs[0], y7)], tone="blue", width=2.0)
    f.label(bx7, y7 - 16, "HTTP 200 OK", tone="blue", cls="small")
    step_badge(f, bx7, y7, "7", "blue")

    return f.save([
        ("When a router forwards a write (1-2) to a demoted leader, the node rejects the request with NOT_LEADER and includes the current Raft term and leader hint (3).", "noteb"),
        "The router updates its local leader table (4) and retries transparently on the new leader (5-6) within the same client request budget (7), hiding leadership failovers from callers.",
    ])


# =============================================================================
# CHAPTER 6: PIPELINED GROUP COMMIT AND AMORTIZATION
# =============================================================================

def ch06_group_commit():
    f = Fig(
        "ch06_group_commit",
        "Figure 6-1. Pipelined Group Commit Batching Over Single fdatasync.",
        476,
    )

    # Stage 1: Concurrent Worker Tasks
    x1, w1 = MARGIN, 172  # 32..204
    f.zone(x1, 0, w1, 388, "blue", "Worker Tasks", "Concurrent RPCs", icon="apps")
    wk1 = f.node(x1 + 14, 66, w1 - 28, 66, "blue", [("Worker 1", "name"), ("PUT k1 + tx1", "mono")], layout="center", kind="card")
    wk2 = f.node(x1 + 14, 182, w1 - 28, 66, "blue", [("Worker 2", "name"), ("PUT k2 + tx2", "mono")], layout="center", kind="card")
    wk3 = f.node(x1 + 14, 298, w1 - 28, 66, "blue", [("Worker N", "name"), ("PUT kN + txN", "mono")], layout="center", kind="card")

    # Stage 2: Bounded mpsc Channel (64px gutter from Stage 1 -> exact midpoint x=236)
    x2, w2 = 268, 144  # 268..412
    f.zone(x2, 52, w2, 284, "teal", "mpsc", "Bounded queue", icon="view_week")
    q_items = [("Frame 1 (tx1)", "teal"), ("Frame 2 (tx2)", "teal"), ("Frame ...", "gray"), ("Frame N (txN)", "teal")]
    for idx, (lbl, tone) in enumerate(q_items):
        f.cell(x2 + 10, 114 + idx * 52, w2 - 20, 38, tone, [(lbl, "monob")], kind="card" if tone == "teal" else "tonal", r=7)

    # Stage 3: Single WAL Writer Task (56px gutter from Stage 2 -> exact midpoint x=440)
    x3, w3 = 468, 208  # 468..676
    f.zone(x3, 0, w3, 388, "amber", "Single WAL Writer", "Serializes disk barrier", icon="engineering")
    s1 = f.node(x3 + 16, 66, w3 - 32, 66, "teal", [("Drain Batch", "name"), ("try_recv() up to N", "mono")], layout="center", kind="card")
    s2 = f.node(x3 + 16, 182, w3 - 32, 66, "amber", [("One writev()", "name"), ("Vectored I/O append", "sub")], layout="center", kind="card")
    s3 = f.node(x3 + 16, 298, w3 - 32, 66, "red", [("One fdatasync()", "name"), ("Single NVMe flush", "sub")], layout="center", kind="mid")
    f.wire([s1.bottom(0), s2.top(0)], tone="teal", width=1.9)
    step_badge(f, s1.cx, badge_pos(s1.b, s2.y), "3", "teal", ring="c-amber")
    f.wire([s2.bottom(0), s3.top(0)], tone="amber", width=1.9)
    step_badge(f, s2.cx, badge_pos(s2.b, s3.y), "4", "amber", ring="c-amber")

    # Stage 4: Disk & Fan-Out ACKs (48px gutter from Stage 3 -> exact midpoint x=700)
    x4, w4 = 724, WIDTH - MARGIN - 724  # 164
    f.zone(x4, 0, w4, 388, "green", "Disk & ACK", "Batch completion", icon="save")
    d1 = f.node(
        x4 + 14, 76, w4 - 28, 96, "amber",
        [("NVMe WAL", "name"), ("N durable", "sub")],
        icon="save", layout="center", kind="card", icon_size=24,
    )
    d2 = f.node(
        x4 + 14, 248, w4 - 28, 110, "green",
        [("Fan-Out", "name"), ("N oneshot", "mono"), ("ACK all", "small")],
        icon="bolt", layout="center", kind="card", icon_size=24,
    )
    f.wire([d1.bottom(0), d2.top(0)], tone="green", width=1.9)
    step_badge(f, d1.cx, badge_pos(d1.b, d2.y), "6", "green", ring="c-green")

    # Step 1: Symmetric Fan-In from 3 Workers -> mpsc queue at exact midpoint x=236
    x_mid_12 = (x1 + w1 + x2) / 2  # 236.0
    f.wire([wk1.right(0), (x_mid_12, wk1.cy)], tone="blue", width=1.8, head=False)
    f.wire([wk2.right(0), (x_mid_12, wk2.cy)], tone="blue", width=1.8, head=False)
    f.wire([wk3.right(0), (x_mid_12, wk3.cy)], tone="blue", width=1.8, head=False)
    f.wire([(x_mid_12, wk1.cy), (x_mid_12, wk3.cy)], tone="blue", width=1.8, head=False)
    f.wire([(x_mid_12, wk2.cy), (x2, wk2.cy)], tone="blue", width=1.9)
    step_badge(f, x_mid_12, (wk1.cy + wk2.cy) / 2, "1", "blue")

    # Step 2: mpsc -> Single WAL Writer Drain Batch (exact midpoint x=440)
    x_mid_23 = (x2 + w2 + x3) / 2  # 440.0
    f.wire([(x2 + w2, 194), (x_mid_23, 194), (x_mid_23, s1.cy), s1.left(0)], tone="teal", width=1.9)
    step_badge(f, x_mid_23, (194 + s1.cy) / 2, "2", "teal")

    # Step 5: fdatasync -> NVMe WAL (exact midpoint x=700)
    x_mid_34 = (x3 + w3 + x4) / 2  # 700.0
    f.wire([s3.right(0), (x_mid_34, s3.cy), (x_mid_34, d1.cy), d1.left(0)], tone="red", width=1.9)
    step_badge(f, x_mid_34, (s3.cy + d1.cy) / 2, "5", "red")

    # Step 7: Bottom fan-out return bus from d2 back to Worker Tasks (52px vertical return leg)
    f.wire([d2.bottom(0), (d2.cx, 440), (x1 + w1 / 2, 440), (x1 + w1 / 2, 388)], tone="green", width=2.0)
    step_badge(f, x1 + w1 / 2, badge_pos(440, 388), "7", "green")
    f.label(WIDTH / 2 + 24, 444, "Fan-out oneshot::Sender::send(Ok(seq)) wakes all N awaiting worker tasks", tone="green", cls="small")

    return f.save([
        ("Concurrent worker tasks submit encoded WAL frames and oneshot reply channels into a bounded mpsc queue (1) drained by a single dedicated writer task (2).", "noteb"),
        "Issuing one vectored writev (3) followed by one fdatasync (4-5) amortizes disk durability across all N queued operations before fanning out completion acknowledgments (6-7).",
    ])


def ch06_throughput_latency():
    f = Fig(
        "ch06_throughput_latency",
        "Figure 6-2. Single-Sync vs. Group-Commit Amortization Trade-Off.",
        472,
    )

    # Top Formula Banner
    f.zone(
        MARGIN, 0, INNER, 86, "blue",
        "Amortization Model (NVMe fdatasync = 5.0 ms, Max Flush Timer = 2.0 ms)",
        "Amortized sync cost = T_fsync / N   |   Throughput scales near-linearly while flush timer bounds tail latency",
        icon="tune",
    )

    # Middle Bar-Band Comparison Panel
    f.zone(
        MARGIN, 108, INNER, 242, "teal",
        "Batch Size Comparison Under Steady Concurrent Write Load",
        "Comparing sustained write throughput, p99 write latency, and amortized sync cost per operation",
        icon="table_rows",
    )

    # Column headers
    c_batch = MARGIN + 18
    c_tput = 218
    c_lat = 548
    c_sync = 758
    f.text(c_batch, 170, "Batch Size", "badge", "start", tone="teal")
    f.text(c_tput, 170, "Sustained Throughput (writes/s)", "badge", "start", tone="teal")
    f.text(c_lat, 170, "p99 Latency (ms)", "badge", "start", tone="teal")
    f.text(c_sync, 170, "Sync / Write", "badge", "start", tone="teal")

    rows = [
        ("N = 1", "Single sync", 18, "200 ops/s", "red", 84, "5.1 ms", "blue", "5.00 ms"),
        ("N = 16", "Balanced", 118, "3,100 ops/s", "teal", 104, "6.2 ms", "green", "0.31 ms"),
        ("N = 64", "High batch", 206, "11,800 ops/s", "green", 122, "7.0 ms", "amber", "0.08 ms"),
    ]
    tput_track = 212
    lat_track = 132

    for idx, (n_lbl, n_sub, tw, t_txt, t_tone, lw_bar, l_txt, l_tone, s_txt) in enumerate(rows):
        ry = 184 + idx * 52
        f.rect(MARGIN + 14, ry, INNER - 28, 42, "card", r=8, lift=True)
        f.text(c_batch + 4, ry + 18, n_lbl, "monob", "start", tone=t_tone)
        f.text(c_batch + 4, ry + 34, n_sub, "small", "start")

        # Throughput bar + label
        f.rect(c_tput, ry + 13, tput_track, 16, "c-gray", r=5)
        f.rect(c_tput, ry + 13, tw, 16, f"a-{t_tone}", r=5)
        f.text(c_tput + tput_track + 10, ry + 26, t_txt, "monob", "start", tone=t_tone)

        # Latency bar + label
        f.rect(c_lat, ry + 13, lat_track, 16, "c-gray", r=5)
        f.rect(c_lat, ry + 13, lw_bar, 16, f"a-{l_tone}", r=5)
        f.text(c_lat + lat_track + 10, ry + 26, l_txt, "monob", "start", tone=l_tone)

        # Amortized sync per write
        f.text(c_sync + 4, ry + 26, s_txt, "monob", "start", tone=t_tone)

    # Bottom 3 Trade-Off Takeaway Cards (3 * 270 + 2 * 23 = 856)
    cw = 270
    cgap = 23
    cards = [
        ("N = 1: Sync Bound", "1 fdatasync per write", "Disk barrier caps IOPS", "red", "hourglass_top"),
        ("N = 16-64: Amortized", "1/N sync cost per write", "Near-linear throughput gain", "green", "bolt"),
        ("Flush Timer Bound", "Max 2 ms batch wait", "Protects low-load p99", "amber", "timer"),
    ]
    for i, (hdr, s1, s2, tone, ic) in enumerate(cards):
        cx = MARGIN + i * (cw + cgap)
        f.node(
            cx, 372, cw, 92, tone,
            [(hdr, "name"), (s1, "sub"), (s2, "small")],
            icon=ic, kind="card", icon_size=26,
        )

    return f.save([
        ("Group commit reduces the per-operation fdatasync cost by a factor of 1/N, lifting throughput from roughly 200 to over 11,000 durable writes per second on the same disk.", "noteb"),
        "Pairing a maximum batch size with a bounded flush timer prevents idle requests from stalling at low concurrency while preserving full amortization under saturation.",
    ])


ALL = [
    ch02_wal_format,
    ch02_crash_recovery,
    ch03_replication_flow,
    ch03_quorum_failover,
    ch04_raft_states,
    ch04_log_matching,
    ch05_router_topology,
    ch05_epoch_redirect,
    ch06_group_commit,
    ch06_throughput_latency,
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
