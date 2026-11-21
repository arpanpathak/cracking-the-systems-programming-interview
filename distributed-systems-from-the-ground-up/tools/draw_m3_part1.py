#!/usr/bin/env python3
"""Generate spacious Material Design 3 light+dark SVG figures for Part I (Chapters 2-6).

Every figure prioritizes generous whitespace, concise labels, zero text overflow
in Chrome/Safari, and clean orthogonal routing (WIDTH = 920, MARGIN = 32).
"""
from figkit_m3 import Box, Fig, WIDTH, MARGIN

INNER = WIDTH - 2 * MARGIN  # 856px usable width


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
        ("1. Encode Frame", "Serialize op, key, val", "Compute CRC32C", "blue", "code"),
        ("2. Append + fsync", "Sequential write()", "Flush to NVMe media", "amber", "save"),
        ("3. Mutate MemTable", "Update BTreeMap", "Advance sequence ID", "teal", "memory"),
        ("4. Acknowledge", "Return HTTP 200", "Write is durable", "green", "play_arrow"),
    ]
    sw = 184
    sgap = 26
    sx0 = MARGIN + 21
    boxes = []
    for i, (t, s1, s2, tone, ic) in enumerate(stages):
        sx = sx0 + i * (sw + sgap)
        b = f.node(
            sx, 286, sw, 114, tone,
            [(t, "name"), (s1, "sub"), (s2, "small")],
            icon=ic, layout="center", kind="card", icon_size=26,
        )
        boxes.append(b)
    for i in range(3):
        f.wire([boxes[i].right(0), boxes[i + 1].left(0)], tone="wire", width=1.8)

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
        466,
    )

    # Top Zone: Sequential WAL scan and torn-tail truncation
    f.zone(
        MARGIN, 0, INNER, 198, "amber",
        "1. Sequential Startup Scan and Torn-Tail Truncation",
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
        f.cell(fx, 64, fw, 74, tone, [(hdr, "monob"), (sub, "small")], kind=kind, r=9)
        if idx == 2:
            boundary_x = fx + fw + fgap / 2
            f.rule(boundary_x, 54, boundary_x, 152, tone="red", width=2.0, dash="5 4")
        fx += fw + fgap

    f.pill(MARGIN + 20, 158, "Valid prefix replayed (bytes 0..95)", tone="green", anchor="start")
    f.pill(WIDTH - MARGIN - 20, 158, "ftruncate(fd, 96) drops partial frame", tone="red", anchor="end")

    # Bottom-left Zone: MemTable Reconstruction
    lw = 416
    f.zone(
        MARGIN, 222, lw, 236, "blue",
        "2. BTreeMap MemTable Rebuild",
        "Deterministic replay restores live key state",
        icon="memory",
    )
    m1 = f.node(
        MARGIN + 18, 286, lw - 36, 68, "blue",
        [("Apply Frames 1..3 in Order", "name"), ("PUT u1 -> PUT u2 -> DEL u1", "mono")],
        icon="table_rows", kind="card", icon_size=26,
    )
    m2 = f.node(
        MARGIN + 18, 376, lw - 36, 66, "green",
        [("Recovered MemTable Ready", "name"), ("Live map: { u2 -> bob }", "mono")],
        icon="layers", kind="card", icon_size=26,
    )
    f.wire([m1.bottom(0), m2.top(0)], tone="blue", width=1.8)

    # Bottom-right Zone: Atomic Log Compaction
    rx = MARGIN + lw + 24
    rw = WIDTH - MARGIN - rx  # 416
    f.zone(
        rx, 222, rw, 236, "teal",
        "3. Atomic Snapshot and Compaction",
        "Eliminates obsolete overwrites and tombstones",
        icon="folder",
    )
    c1 = f.node(
        rx + 18, 286, rw - 36, 68, "teal",
        [("Write wal.compact.tmp", "name"), ("Live keys only + fsync(tmp)", "sub")],
        icon="save", kind="card", icon_size=26,
    )
    c2 = f.node(
        rx + 18, 376, rw - 36, 66, "purple",
        [("Atomic rename() + dir fsync", "name"), ("wal.compact.tmp -> wal.log", "mono")],
        icon="shield", kind="card", icon_size=26,
    )
    f.wire([c1.bottom(0), c2.top(0)], tone="teal", width=1.8)

    # Link valid scan down to MemTable rebuild
    f.wire([(MARGIN + lw / 2, 198), (MARGIN + lw / 2, 222)], tone="green", width=1.9)
    # Link recovered state to periodic compaction
    f.wire([(MARGIN + lw, 340), (rx, 340)], tone="teal", dash=True, width=1.7)

    return f.save([
        ("Crash recovery scans frames sequentially from offset zero, halting at the first truncated length or checksum mismatch and truncating the torn tail in place.", "noteb"),
        "Compaction bounds restart latency by writing live MemTable entries to a temporary file, calling fsync, and replacing the old log with an atomic rename followed by a directory fsync.",
    ])


# =============================================================================
# CHAPTER 3: LEADER-FOLLOWER REPLICATION AND FAULT MODES
# =============================================================================

def ch03_replication_flow():
    f = Fig(
        "ch03_replication_flow",
        "Figure 3-1. Leader-Follower Write Replication and Commit Index Advancement.",
        472,
    )

    # Left: Client card
    cli = f.node(
        MARGIN, 174, 166, 118, "blue",
        [("Client", "name"), ("PUT k=v", "mono"), ("Awaits ACK", "small")],
        icon="laptop", layout="center", kind="card", icon_size=28,
    )

    # Middle: Leader Zone
    lx = 246
    lw = 264
    f.zone(
        lx, 0, lw, 464, "amber",
        "Leader Node (Term 4)",
        "Quorum = 2 of 3 replicas",
        icon="dns",
    )
    l1 = f.node(
        lx + 16, 66, lw - 32, 92, "amber",
        [("1. Append Local WAL", "name"), ("Assign log idx = 42", "mono"), ("fsync to local disk", "small")],
        icon="save", kind="card", icon_size=24,
    )
    l2 = f.node(
        lx + 16, 194, lw - 32, 96, "teal",
        [("2. Replicate in Parallel", "name"), ("Send AppendEntries", "sub"), ("Wait for majority ACK", "small")],
        icon="swap_horiz", kind="card", icon_size=24,
    )
    l3 = f.node(
        lx + 16, 326, lw - 32, 118, "green",
        [("3. Commit & Apply", "name"), ("commitIndex = 42", "mono"), ("Apply to MemTable", "sub"), ("Reply 200 OK", "small")],
        icon="play_arrow", kind="card", icon_size=24,
    )
    f.wire([l1.bottom(0), l2.top(0)], tone="amber", width=1.8)
    f.wire([l2.bottom(0), l3.top(0)], tone="green", width=1.8)

    # Right: Follower Replicas Zone
    rx = 602
    rw = WIDTH - MARGIN - rx  # 286
    f.zone(
        rx, 0, rw, 464, "blue",
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

    # Orthogonal wires with generous clearance
    f.wire([cli.right(-22), (222, cli.cy - 22), (222, l1.cy), l1.left(0)], tone="blue", width=1.9)
    f.label(184, 116, "PUT(k, v)", tone="blue", cls="small")

    f.wire([l3.left(0), (222, l3.cy), (222, cli.cy + 26), cli.right(26)], tone="green", width=1.9)
    f.label(184, 386, "200 OK", tone="green", cls="small")

    # Leader <-> Follower A (parallel AppendEntries & ACK)
    f.wire([l2.right(-20), (546, l2.cy - 20), (546, fa.cy - 18), fa.left(-18)], tone="amber", width=1.9)
    f.label(556, 98, "Append(42)", tone="amber", cls="small")

    f.wire([fa.left(20), (566, fa.cy + 20), (566, l2.cy + 6), l2.right(6)], tone="green", width=1.9)
    f.label(556, 178, "ACK(42)", tone="green", cls="small")

    # Leader -> Follower B (async catch-up)
    f.wire([l2.right(28), (546, l2.cy + 28), (546, fb.cy), fb.left(0)], tone="gray", dash=True, width=1.6)
    f.label(556, 350, "Async RPC", tone="gray", cls="small")

    return f.save([
        ("The leader persists each write to its local write-ahead log first, then replicates AppendEntries in parallel to all followers.", "noteb"),
        "Once a majority of replicas acknowledge the entry, the leader advances its commit index, applies the mutation to the state machine, and replies to the client without waiting for the slowest follower.",
    ])


def ch03_quorum_failover():
    f = Fig(
        "ch03_quorum_failover",
        "Figure 3-2. Replication Fault Modes: Stale Follower Catch-Up and Split-Brain Risk.",
        468,
    )

    lw = 416
    # Left Panel: Stale Follower Catch-Up
    f.zone(
        MARGIN, 0, lw, 460, "teal",
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

    # Replication wire down
    f.wire([(MARGIN + lw / 2, 170), (MARGIN + lw / 2, 234)], tone="teal", width=1.9)
    f.label(MARGIN + lw / 2, 206, "AppendEntries(prev=40, [41..43])", tone="teal", cls="small", back_cls="c-teal")

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

    # Outcome card
    f.node(
        MARGIN + 18, 366, lw - 36, 76, "green",
        [("Converged After Suffix Replay", "name"), ("Follower syncs 41..43 and rejoins quorum", "sub")],
        icon="play_arrow", kind="card", icon_size=26,
    )

    # Right Panel: Split-Brain Risk
    rx = MARGIN + lw + 24
    rw = WIDTH - MARGIN - rx  # 416
    f.zone(
        rx, 0, rw, 460, "red",
        "Mode B: Partitioned Leader Split-Brain",
        "Why naive failover fails without consensus fencing",
        icon="warning",
    )

    f.rect(rx + 18, 62, rw - 36, 118, "card", r=12, lift=True)
    f.pill(rx + 32, 74, "MINORITY PARTITION (1 of 3)", tone="red", anchor="start")
    f.text(rx + 32, 118, "Isolated Old Leader A", "name", "start", tone="red")
    f.text(rx + 32, 140, "Unfenced leader still accepts PUT k=v1", "sub", "start")
    f.text(rx + 32, 160, "Divergent write is lost upon heal", "small", "start")

    f.rule(rx + 18, 202, rx + rw - 18, 202, tone="red", width=2.0, dash="8 5")
    f.label(rx + rw / 2, 206, "NETWORK PARTITION", tone="red", cls="badge", back_cls="c-red")

    f.rect(rx + 18, 224, rw - 36, 120, "card", r=12, lift=True)
    f.pill(rx + 32, 236, "MAJORITY PARTITION (2 of 3)", tone="green", anchor="start")
    f.text(rx + 32, 280, "Promoted Leader B + Follower C", "name", "start", tone="green")
    f.text(rx + 32, 302, "Commits PUT k=v2 independently", "sub", "start")
    f.text(rx + 32, 322, "Two concurrent writers violate safety", "small", "start")

    f.node(
        rx + 18, 366, rw - 36, 76, "purple",
        [("Motivation for Chapter 4 Consensus", "name"), ("Quorum elections + monotonic terms fence A", "sub")],
        icon="shield", kind="mid", icon_size=26,
    )

    return f.save([
        ("A lagging follower recovers safely by requesting the missing log suffix after its highest matching entry index.", "noteb"),
        "By contrast, a network partition can leave an isolated primary believing it is still the leader, requiring Raft terms and quorum voting to fence stale leaders.",
    ])


# =============================================================================
# CHAPTER 4: RAFT LEADER ELECTION AND LOG MATCHING
# =============================================================================

def ch04_raft_states():
    f = Fig(
        "ch04_raft_states",
        "Figure 4-1. Raft Server Role State Machine and Term Transitions.",
        452,
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
    cy = 148
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

    # 1. Startup -> Follower
    f.wire([start.bottom(0), (start.cx, cy)], tone="wire", width=1.8)

    # 2. Candidate split-vote self-loop (top lane y=42)
    f.wire([bc.top(-28), (bc.cx - 28, 42), (bc.cx + 28, 42), bc.top(28)], tone="amber", dash=True, width=1.6)
    f.label(bc.cx, 28, "Split vote: election timeout / term++", tone="amber", cls="small")

    # 3. Follower -> Candidate (upper channel y=104)
    f.wire([bf.top(64), (bf.cx + 64, 104), (bc.cx - 76, 104), bc.top(-76)], tone="amber", width=1.9)
    f.label(306, 94, "Election timeout / term++", tone="amber", cls="small")

    # 4. Candidate -> Leader (upper channel y=104)
    f.wire([bc.top(76), (bc.cx + 76, 104), (bl.cx - 64, 104), bl.top(-64)], tone="green", width=1.9)
    f.label(614, 94, "Wins majority votes", tone="green", cls="small")

    # 5. Candidate -> Follower (lower channel 1, y=366)
    f.wire([bc.bottom(-36), (bc.cx - 36, 366), (bf.cx + 52, 366), bf.bottom(52)], tone="blue", width=1.8)
    f.label(318, 382, "Valid leader or higher term", tone="blue", cls="small")

    # 6. Leader -> Follower (lower channel 2, y=418)
    f.wire([bl.bottom(0), (bl.cx, 418), (bf.cx - 48, 418), bf.bottom(-48)], tone="red", width=1.9)
    f.label(460, 434, "Discovers higher term (term' > currentTerm) -> step down", tone="red", cls="small")

    return f.save([
        ("Every Raft server begins as a Follower and transitions to Candidate only when an election timeout elapses without a valid leader heartbeat.", "noteb"),
        "Discovering a strictly higher term from any RPC request or response forces a Candidate or Leader to step down immediately, preserving the single-leader-per-term invariant.",
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
        486,
    )

    # Top-left: Client
    cli = f.node(
        MARGIN, 14, 240, 88, "blue",
        [("Application Client", "name"), ("PUT /v1/keys/u42", "mono")],
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

    # Middle: Stateless Routing Tier
    r_zone = f.zone(
        MARGIN, 158, INNER, 134, "teal",
        "Stateless Routing Tier (In-Memory Ring Map + Leader Hint Cache)",
        "Any router instance computes the target shard and routes directly to its active Raft Leader",
        icon="swap_horiz",
    )
    r1 = f.node(
        MARGIN + 18, 214, 244, 62, "teal",
        [("1. Hash Key", "name"), ("xxhash64(u42)", "mono")],
        icon="code", kind="card", icon_size=24,
    )
    r2 = f.node(
        MARGIN + 306, 214, 244, 62, "blue",
        [("2. Ring Lookup", "name"), ("Token -> Shard 02", "mono")],
        icon="loop", kind="card", icon_size=24,
    )
    r3 = f.node(
        MARGIN + 594, 214, 244, 62, "amber",
        [("3. Leader Hint", "name"), ("Shard 02 -> Node B", "mono")],
        icon="call_split", kind="card", icon_size=24,
    )
    f.wire([r1.right(0), r2.left(0)], tone="teal", width=1.8)
    f.wire([r2.right(0), r3.left(0)], tone="blue", width=1.8)

    # Bottom: Partitioned Multi-Raft Storage Tier
    f.zone(
        MARGIN, 330, INNER, 148, "blue",
        "Storage Tier: Partitioned 3-Node Raft Groups",
        "Direct leader RPC eliminates extra inter-node forwarding hops on the steady-state write path",
        icon="layers",
    )

    # Shard 01 box
    s1_x, sw = MARGIN + 18, 398
    f.rect(s1_x, 386, sw, 78, "card", r=11, lift=True)
    f.text(s1_x + 14, 407, "Shard 01  (Tokens 0x0000..0x7FFF)", "monob", "start", tone="blue")
    f.cell(s1_x + 14, 418, 132, 34, "amber", [("Node A (Leader)", "badge")], kind="mid", r=7)
    f.cell(s1_x + 156, 418, 108, 34, "gray", [("Node B (F)", "badge")], kind="tonal", r=7)
    f.cell(s1_x + 274, 418, 108, 34, "gray", [("Node C (F)", "badge")], kind="tonal", r=7)

    # Shard 02 box
    s2_x = s1_x + sw + 24
    f.rect(s2_x, 386, sw, 78, "card", r=11, lift=True)
    f.text(s2_x + 14, 407, "Shard 02  (Tokens 0x8000..0xFFFF)", "monob", "start", tone="green")
    f.cell(s2_x + 14, 418, 108, 34, "gray", [("Node A (F)", "badge")], kind="tonal", r=7)
    f.cell(s2_x + 132, 418, 134, 34, "green", [("Node B (Leader)", "badge")], kind="mid", r=7)
    f.cell(s2_x + 276, 418, 108, 34, "gray", [("Node C (F)", "badge")], kind="tonal", r=7)

    # Orthogonal wires
    f.wire([cli.bottom(0), (cli.cx, r_zone.y)], tone="blue", width=2.0)
    f.label(cli.cx + 64, 134, "HTTP PUT", tone="blue", cls="small")

    f.wire([cp2.bottom(0), (cp2.cx, r_zone.y)], tone="purple", dash=True, width=1.7)
    f.label(cp2.cx - 86, 144, "Epoch e=14 watch", tone="purple", cls="small")

    # Router r3 -> Shard 02 Leader Node B
    target_x = s2_x + 199
    f.wire([r3.bottom(0), (r3.cx, 310), (target_x, 310), (target_x, 386)], tone="green", width=2.0)
    f.label(576, 314, "gRPC PUT -> Node B", tone="green", cls="small")

    return f.save([
        ("Stateless routers decouple client connections from storage placement by caching the consistent hash ring and per-shard leader hints in memory.", "noteb"),
        "The control plane propagates topology epochs asynchronously; routers remain available during control-plane outages and learn leader changes directly from storage responses.",
    ])


def ch05_epoch_redirect():
    f = Fig(
        "ch05_epoch_redirect",
        "Figure 5-2. Stale Route Detection and NOT_LEADER Retry Protocol.",
        476,
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
        f.rule(cxs[i], 62, cxs[i], 464, tone="gray", width=1.4, dash="4 4")

    # Step 1: Client -> Router
    y1 = 104
    f.wire([(cxs[0], y1), (cxs[1], y1)], tone="blue", width=2.0)
    f.label((cxs[0] + cxs[1]) / 2, y1 - 10, "1. PUT /keys/u42", tone="blue", cls="small")

    # Step 2: Router -> Demoted Node 1
    y2 = 156
    f.wire([(cxs[1], y2), (cxs[2], y2)], tone="amber", width=2.0)
    f.label((cxs[1] + cxs[2]) / 2, y2 - 10, "2. Write(u42, term=4)", tone="amber", cls="small")

    # Step 3: Demoted Node 1 -> Router (NOT_LEADER)
    y3 = 210
    f.wire([(cxs[2], y3), (cxs[1], y3)], tone="red", dash=True, width=1.9)
    f.label((cxs[1] + cxs[2]) / 2, y3 - 10, "3. NOT_LEADER(N2, T5)", tone="red", cls="monob")

    # Step 4: Router updates cached leader map
    f.node(
        cxs[1] - 110, 240, 220, 52, "purple",
        [("4. Update Leader Cache", "name"), ("Shard 02 -> N2 (T5)", "mono")],
        layout="center", kind="mid", r=10,
    )

    # Step 5: Router -> New Leader Node 2 (transparent retry)
    y5 = 330
    f.wire([(cxs[1], y5), (cxs[3], y5)], tone="green", width=2.0)
    f.label((cxs[1] + cxs[3]) / 2, y5 - 10, "5. Transparent Retry: Write(u42, term=5)", tone="green", cls="small")

    # Step 6: Node 2 -> Router (Quorum ACK)
    y6 = 384
    f.wire([(cxs[3], y6), (cxs[1], y6)], tone="green", width=2.0)
    f.label((cxs[1] + cxs[3]) / 2, y6 - 10, "6. Quorum Commit OK (idx=88)", tone="green", cls="small")

    # Step 7: Router -> Client (single attempt)
    y7 = 438
    f.wire([(cxs[1], y7), (cxs[0], y7)], tone="blue", width=2.0)
    f.label((cxs[0] + cxs[1]) / 2, y7 - 10, "7. HTTP 200 OK", tone="blue", cls="small")

    return f.save([
        ("When a router forwards a write to a demoted leader, the node rejects the request with NOT_LEADER and includes the current Raft term and leader hint.", "noteb"),
        "The router updates its local leader table and retries transparently on the new leader within the same client request budget, hiding leadership failovers from callers.",
    ])


# =============================================================================
# CHAPTER 6: PIPELINED GROUP COMMIT AND AMORTIZATION
# =============================================================================

def ch06_group_commit():
    f = Fig(
        "ch06_group_commit",
        "Figure 6-1. Pipelined Group Commit Batching Over Single fdatasync.",
        460,
    )

    # Stage 1: Concurrent Worker Tasks
    x1, w1 = MARGIN, 200
    f.zone(x1, 0, w1, 366, "blue", "Worker Tasks", "Concurrent RPC handlers", icon="apps")
    wk1 = f.node(x1 + 14, 68, w1 - 28, 76, "blue", [("Worker 1", "name"), ("PUT k1 + tx1", "mono")], layout="center", kind="card")
    wk2 = f.node(x1 + 14, 166, w1 - 28, 76, "blue", [("Worker 2", "name"), ("PUT k2 + tx2", "mono")], layout="center", kind="card")
    wk3 = f.node(x1 + 14, 264, w1 - 28, 76, "blue", [("Worker N", "name"), ("PUT kN + txN", "mono")], layout="center", kind="card")

    # Stage 2: Bounded mpsc Channel
    x2, w2 = 266, 152
    f.zone(x2, 46, w2, 274, "teal", "mpsc", "Bounded queue", icon="view_week")
    q_items = [("Frame 1 (tx1)", "teal"), ("Frame 2 (tx2)", "teal"), ("Frame ...", "gray"), ("Frame N (txN)", "teal")]
    for idx, (lbl, tone) in enumerate(q_items):
        f.cell(x2 + 14, 108 + idx * 50, w2 - 28, 38, tone, [(lbl, "monob")], kind="card" if tone == "teal" else "tonal", r=7)

    # Stage 3: Single WAL Writer Task
    x3, w3 = 456, 226
    f.zone(x3, 0, w3, 366, "amber", "Single WAL Writer", "Serializes disk barrier", icon="engineering")
    s1 = f.node(x3 + 16, 68, w3 - 32, 76, "teal", [("1. Drain Batch", "name"), ("try_recv() up to N", "mono")], layout="center", kind="card")
    s2 = f.node(x3 + 16, 166, w3 - 32, 76, "amber", [("2. One writev()", "name"), ("Vectored I/O append", "sub")], layout="center", kind="card")
    s3 = f.node(x3 + 16, 264, w3 - 32, 76, "red", [("3. One fdatasync()", "name"), ("Single NVMe flush", "sub")], layout="center", kind="mid")
    f.wire([s1.bottom(0), s2.top(0)], tone="teal", width=1.8)
    f.wire([s2.bottom(0), s3.top(0)], tone="amber", width=1.8)

    # Stage 4: Disk & Fan-Out ACKs
    x4, w4 = 716, WIDTH - MARGIN - 716  # 172
    f.zone(x4, 0, w4, 366, "green", "Disk & ACK", "Batch completion", icon="save")
    d1 = f.node(
        x4 + 14, 84, w4 - 28, 100, "amber",
        [("NVMe WAL", "name"), ("N durable", "sub")],
        icon="save", layout="center", kind="card", icon_size=24,
    )
    d2 = f.node(
        x4 + 14, 224, w4 - 28, 114, "green",
        [("Fan-Out", "name"), ("N oneshot", "mono"), ("ACK all", "small")],
        icon="bolt", layout="center", kind="card", icon_size=24,
    )
    f.wire([d1.bottom(0), d2.top(0)], tone="green", width=1.8)

    # Connecting wires
    f.wire([wk1.right(0), (248, wk1.cy), (248, 127), (x2, 127)], tone="blue", width=1.7)
    f.wire([wk2.right(0), (x2, wk2.cy)], tone="blue", width=1.7)
    f.wire([wk3.right(0), (248, wk3.cy), (248, 277), (x2, 277)], tone="blue", width=1.7)

    f.wire([(x2 + w2, 183), (438, 183), (438, s1.cy), s1.left(0)], tone="teal", width=1.9)
    f.wire([s3.right(0), (699, s3.cy), (699, d1.cy), d1.left(0)], tone="red", width=1.9)

    # Bottom fan-out return bus from d2 back to Worker Tasks
    f.wire([d2.bottom(0), (d2.cx, 418), (x1 + w1 / 2, 418), (x1 + w1 / 2, 366)], tone="green", width=2.0)
    f.label(WIDTH / 2, 422, "Fan-out oneshot::Sender::send(Ok(seq)) wakes all N awaiting worker tasks", tone="green", cls="small")

    return f.save([
        ("Concurrent worker tasks submit encoded WAL frames and oneshot reply channels into a bounded mpsc queue drained by a single dedicated writer task.", "noteb"),
        "Issuing one vectored writev followed by one fdatasync amortizes disk durability across all N queued operations before fanning out completion acknowledgments.",
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
