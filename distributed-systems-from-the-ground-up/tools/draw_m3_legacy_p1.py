#!/usr/bin/env python3
"""Generate Material Design 3 light+dark SVG figures for the 16 upgraded legacy
diagrams in Chapters 2, 3, and 4 of Distributed Systems from the Ground Up.

Standalone script (does not modify draw_m3_figures.py or draw_m3_part1.py).
All figures use figkit_m3 (WIDTH = 920, MARGIN = 32, INNER = 856) and emit both
src/figures/m3/<name>.svg and src/figures/m3/dark/<name>.svg.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from figkit_m3 import Fig, WIDTH, MARGIN

INNER = WIDTH - 2 * MARGIN  # 856px usable width


def step_badge(f, cx, cy, num, tone="blue", ring="paper"):
    """Draw a high-contrast circular step badge (1, 2, 3...) for light & dark modes."""
    f.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="11.5" class="{ring}"/>')
    f.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="9.5" class="a-{tone}"/>')
    f.add(f'<text x="{cx:.1f}" y="{cy + 3.7:.1f}" text-anchor="middle" class="badge paper">{num}</text>')


def path_legend(f, y, sync_text="Solid: Sync data path", async_text="Dashed: Async / control path"):
    """Draw a compact legend strip distinguishing solid vs dashed wires."""
    f.rect(MARGIN, y, INNER, 28, "c-gray", r=8)
    f.wire([(MARGIN + 18, y + 14), (MARGIN + 52, y + 14)], tone="blue", width=2.0)
    f.text(MARGIN + 60, y + 18, sync_text, "small", "start", tone="blue")
    mid = MARGIN + INNER / 2 + 12
    f.wire([(mid, y + 14), (mid + 34, y + 14)], tone="purple", dash=True, width=1.7)
    f.text(mid + 42, y + 18, async_text, "small", "start", tone="purple")


# =============================================================================
# CHAPTER 2: STORAGE NODE
# =============================================================================

def ch02_crash_points():
    f = Fig(
        "ch02_crash_points",
        "Figure 2-1. Four Crash Points During a Write and Their Restart Outcomes.",
        452,
    )

    # Top timeline zone
    f.zone(
        MARGIN, 0, INNER, 118, "blue",
        "Write Execution Pipeline and Interruption Points",
        "Crash 1..4 divide a single HTTP PUT into four deterministic recovery outcomes",
        icon="bolt",
    )

    # 4 pipeline stages aligned above the 4 outcome columns
    col_w = 202
    col_gap = 16
    xs = [MARGIN + i * (col_w + col_gap) for i in range(4)]

    stages = [
        ("Receive PUT", "Before WAL write", "gray"),
        ("WAL write()", "Mid-record bytes", "amber"),
        ("WAL fsync()", "Durable on NVMe", "teal"),
        ("HTTP 201/204", "Ack sent to client", "green"),
    ]
    stage_boxes = []
    for i, (t, s, tone) in enumerate(stages):
        bx = xs[i] + 14
        bw = col_w - 28
        b = f.node(bx, 54, bw, 50, tone, [(t, "name"), (s, "small")], layout="center", kind="card")
        stage_boxes.append(b)
    for i in range(3):
        f.wire([stage_boxes[i].right(0), stage_boxes[i + 1].left(0)], tone="wire", width=1.8)

    # Four outcome columns below
    outcomes = [
        (
            "1", "Before WAL Write", "gray",
            ("Disk", "Not written", "gray"),
            ("Client", "No HTTP reply", "amber"),
            ("On Restart", "Key absent", "gray"),
        ),
        (
            "2", "Mid-Record Write", "red",
            ("Disk", "Partial / torn bytes", "red"),
            ("Client", "No HTTP reply", "amber"),
            ("On Restart", "Truncated on scan", "teal"),
        ),
        (
            "3", "After fsync, Pre-Reply", "amber",
            ("Disk", "Complete record", "green"),
            ("Client", "No HTTP reply", "amber"),
            ("On Restart", "Key present", "green"),
        ),
        (
            "4", "After HTTP Reply", "green",
            ("Disk", "Complete record", "green"),
            ("Client", "201 / 204 ACK", "green"),
            ("On Restart", "Key present", "green"),
        ),
    ]

    card_y = 172
    card_h = 268
    for i, (num, title, tone, r1, r2, r3) in enumerate(outcomes):
        cx = xs[i] + col_w / 2
        # Drop wire from pipeline stage to outcome card (span 104..172 = 68px)
        f.wire([(cx, 104), (cx, card_y)], tone=tone, dash=True, width=1.8)
        step_badge(f, cx, (104 + card_y - 9) / 2, num, tone=tone)

        f.rect(xs[i], card_y, col_w, card_h, f"c-{tone}", r=14)
        f.text(cx, card_y + 26, title, "name", "middle", tone=tone, fit=(xs[i] + 8, xs[i] + col_w - 8))

        ry = card_y + 42
        for lbl, val, rtone in (r1, r2, r3):
            f.node(
                xs[i] + 12, ry, col_w - 24, 62, rtone,
                [(lbl, "small"), (val, "monob")],
                layout="center", kind="card", r=10, text_tone=rtone,
            )
            ry += 72

    return f.save([
        ("Crash points 1 and 2 leave no acknowledged write; any torn bytes from point 2 fail CRC32C validation and are truncated on startup.", "noteb"),
        "Crash point 3 leaves a durable record even though the client timed out; point 4 is the normal acknowledged path.",
    ])


def ch02_survives():
    f = Fig(
        "ch02_survives",
        "Figure 2-3. Durability Boundaries: Process Crash (SIGKILL) vs. Host Power Loss.",
        388,
    )

    col_w = 416
    gap = 24
    lx = MARGIN
    rx = MARGIN + col_w + gap

    # Left Zone: Process Crash (SIGKILL)
    f.zone(
        lx, 0, col_w, 326, "amber",
        "Process Crash (SIGKILL)",
        "OS kernel stays alive; only process address space is lost",
        icon="warning",
    )
    # Right Zone: Host Power Loss
    f.zone(
        rx, 0, col_w, 326, "red",
        "Host Power Loss",
        "All volatile DRAM is cleared; only flushed NVMe media survives",
        icon="bolt",
    )

    layers = [
        ("In-Process RAM", "BTreeMap, user buffers", "memory", "LOST", "red", "LOST", "red"),
        ("Kernel Page Cache", "Buffered write() pages", "layers", "SURVIVES", "green", "LOST", "red"),
        ("NVMe Disk (fsync)", "fsync-confirmed kv.log", "save", "SURVIVES", "green", "SURVIVES", "green"),
    ]

    ly = 62
    lh = 76
    lgap = 14
    for title, sub, ic, l_badge, l_tone, r_badge, r_tone in layers:
        # Left card
        f.node(lx + 16, ly, col_w - 32, lh, l_tone, [(title, "name"), (sub, "sub")], icon=ic, kind="card", icon_size=28)
        f.pill(lx + col_w - 28, ly + lh / 2 - 10, l_badge, tone=l_tone, anchor="end")

        # Right card
        f.node(rx + 16, ly, col_w - 32, lh, r_tone, [(title, "name"), (sub, "sub")], icon=ic, kind="card", icon_size=28)
        f.pill(rx + col_w - 28, ly + lh / 2 - 10, r_badge, tone=r_tone, anchor="end")

        ly += lh + lgap

    # Bottom summary strip
    f.node(
        MARGIN, 342, INNER, 40, "green",
        [("Durability boundary: only fsync()-confirmed WAL records survive both SIGKILL and power failure.", "body")],
        layout="center", kind="tonal", r=10, text_tone="green",
    )

    return f.save([
        ("A SIGKILL test alone cannot catch a missing fsync() because dirty pages in the kernel page cache survive process exit.", "noteb"),
        "True crash-consistent durability requires flushing through the kernel page cache onto non-volatile NVMe media with fsync().",
    ])


def ch02_sync_cost():
    f = Fig(
        "ch02_sync_cost",
        "Figure 2-4. Empirical NVMe Write Latency: Buffered write() vs. write() + fsync().",
        336,
    )

    f.zone(
        MARGIN, 0, INNER, 266, "blue",
        "Per-Record Append Latency on NVMe (Drawn to Scale)",
        "Comparing un-synced page-cache writes against durable fsync-confirmed appends",
        icon="timer",
    )

    # Chart geometry: x=228..846 (618px for 0..6.0 ms -> 103 px/ms)
    x0 = 228
    x1 = 846
    span = x1 - x0
    max_ms = 6.0

    # Gridlines & axis labels
    grid_top = 64
    grid_bot = 224
    for ms in range(7):
        gx = x0 + (ms / max_ms) * span
        f.rule(gx, grid_top, gx, grid_bot, tone="gray", width=1.1, dash="4 4" if ms > 0 else None)
        f.text(gx, grid_bot + 18, f"{ms} ms", "small", "middle")

    # Row 1: write() only (0.003 ms)
    r1_y = 84
    r1_h = 46
    f.text(x0 - 14, r1_y + 19, "write() only", "monob", "end", fit=(MARGIN + 12, x0 - 10))
    f.text(x0 - 14, r1_y + 36, "(page cache)", "small", "end", fit=(MARGIN + 12, x0 - 10))
    # True width is 0.31px; draw a 4px crisp sliver so it is visible
    f.rect(x0, r1_y, 4, r1_h, "a-teal", r=2)
    f.pill(x0 + 16, r1_y + 13, "0.003 ms · 366,991 rec/s (sliver to scale)", tone="teal", anchor="start")

    # Row 2: write() + fsync() (5.395 ms)
    r2_y = 156
    r2_h = 46
    f.text(x0 - 14, r2_y + 19, "write() + fsync()", "monob", "end", fit=(MARGIN + 12, x0 - 10))
    f.text(x0 - 14, r2_y + 36, "(NVMe flush)", "small", "end", fit=(MARGIN + 12, x0 - 10))
    bar_w = (5.395 / max_ms) * span  # 555.7px
    f.rect(x0, r2_y, bar_w, r2_h, "m-amber", r=8)
    f.rect(x0, r2_y, 8, r2_h, "a-amber", r=3)
    f.text(x0 + bar_w - 14, r2_y + 28, "5.395 ms · 185 rec/s", "monob", "end", tone="amber", fit=(x0 + 12, x0 + bar_w - 8))

    # Bottom KPI bar
    f.node(
        MARGIN, 282, INNER, 44, "amber",
        [("Cost of per-record durability: ~1,800x higher latency per fsync() — motivating group commit and batching.", "body")],
        layout="center", kind="tonal", r=10, text_tone="amber",
    )

    return f.save([
        ("Buffered write() returns in 3 microseconds after copying bytes into kernel RAM; fsync() waits 5.395 ms for the NVMe controller flush.", "noteb"),
        "Throughput drops from 366,991 records/s to 185 records/s when every single write pays a synchronous disk barrier.",
    ])


def ch02_two_machines():
    f = Fig(
        "ch02_two_machines",
        "Figure 2-6. Two-Host Crash Verification Topology (node-a vs. node-b).",
        412,
    )

    # Two host zones with a 132px network gap between them (362 + 132 + 362 = 856)
    zw = 362
    gap = 132
    lx = MARGIN
    rx = MARGIN + zw + gap  # 526

    f.zone(
        lx, 0, zw, 344, "blue",
        "node-a (Verifier Host)",
        "External client isolated from target crashes",
        icon="laptop",
    )
    f.zone(
        rx, 0, zw, 344, "teal",
        "node-b (Storage Host)",
        "Storage node subjected to SIGKILL + restart",
        icon="dns",
    )

    # Left cards inside node-a
    kvctl = f.node(
        lx + 18, 66, zw - 36, 86, "blue",
        [("kvctl", "monob"), ("HTTP PUT load & verifier", "sub")],
        icon="terminal", kind="card", icon_size=28,
    )
    acked = f.node(
        lx + 18, 224, zw - 36, 86, "green",
        [("acked.txt", "monob"), ("Local log of 201/204 keys", "sub")],
        icon="description", kind="card", icon_size=28,
    )
    # Wire 2: kvctl -> acked.txt (span 152..224 = 72px)
    f.wire([kvctl.bottom(0), acked.top(0)], tone="green", width=1.9)
    step_badge(f, kvctl.cx, (152 + 224 - 9) / 2, "2", tone="green", ring="c-blue")
    f.text(kvctl.cx + 18, 189, "Record ACKed key", "small", "start", tone="green", fit=(kvctl.cx + 16, lx + zw - 12))

    # Right cards inside node-b
    kvd = f.node(
        rx + 18, 66, zw - 36, 86, "teal",
        [("kvd", "monob"), ("Storage daemon under test", "sub")],
        icon="dns", kind="card", icon_size=28,
    )
    kvlog = f.node(
        rx + 18, 224, zw - 36, 86, "amber",
        [("kv.log", "monob"), ("fsync-confirmed WAL", "sub")],
        icon="save", kind="card", icon_size=28,
    )
    # Wire: kvd <-> kv.log (span 152..224 = 72px)
    f.wire([kvd.bottom(-54), kvlog.top(-54)], tone="amber", width=1.8)
    f.text(kvd.cx - 40, 189, "fsync / replay", "small", "start", tone="amber", fit=(kvd.cx - 42, rx + zw - 12))
    # Step 3 pill on kvd: SIGKILL & Restart
    step_badge(f, rx + zw - 28, 72, "3", tone="red", ring="c-teal")
    f.pill(rx + zw - 46, 62, "SIGKILL + restart", tone="red", anchor="end")

    # Cross-host wires across x=376..544 (168px span!)
    wx1 = kvctl.r
    wx2 = kvd.x
    # Wire 1: HTTP PUT traffic (top)
    y1 = kvctl.cy - 22
    f.wire([(wx1, y1), (wx2, y1)], tone="blue", width=2.0)
    step_badge(f, (wx1 + wx2 - 9) / 2, y1, "1", tone="blue")
    f.label((wx1 + wx2) / 2, y1 - 15, "HTTP PUT", tone="blue")

    # Wire 4: Verify GETs after restart (middle)
    y4 = kvctl.cy + 20
    f.wire([(wx1, y4), (wx2, y4)], tone="purple", dash=True, width=1.8)
    step_badge(f, (wx1 + wx2 - 9) / 2, y4, "4", tone="purple")
    f.label((wx1 + wx2) / 2, y4 + 22, "Verify GET", tone="purple")

    # Wire 5: 1,107 keys verified (lower)
    y5 = acked.cy
    f.wire([(kvlog.x, y5), (acked.r, y5)], tone="green", width=2.0)
    step_badge(f, (kvlog.x + acked.r + 9) / 2, y5, "5", tone="green")
    f.label((kvlog.x + acked.r) / 2, y5 - 15, "1,107 keys OK", tone="green")

    # Bottom summary strip
    f.node(
        MARGIN, 360, INNER, 42, "green",
        [("Result: all 1,107 keys recorded in acked.txt on node-a were read back intact after SIGKILL and restart on node-b.", "body")],
        layout="center", kind="tonal", r=10, text_tone="green",
    )

    return f.save([
        ("Running kvctl on a separate host guarantees that the verifier's ground-truth acked.txt survives when kvd is killed.", "noteb"),
        "Steps 1-2 stream PUTs and record acknowledgments; step 3 kills and restarts kvd; steps 4-5 verify all 1,107 keys.",
    ])


# =============================================================================
# CHAPTER 3: REPLICATION
# =============================================================================

def ch03_repl_state():
    f = Fig(
        "ch03_repl_state",
        "Figure 3-2. Replica Log Prefix: Committed & Visible (1..7) vs. Uncommitted Tail (8..9).",
        356,
    )

    f.zone(
        MARGIN, 0, INNER, 198, "blue",
        "Replica WAL Sequence (Records 1..9)",
        "Only the majority-committed prefix is applied to the readable key-value map",
        icon="view_week",
    )

    # 9 log cells spanning x=50..870 (820px): 9*84 + 8*8 = 756 + 64 = 820
    cw = 84
    cgap = 8
    cx0 = MARGIN + 18
    cy = 64
    ch = 72
    for idx in range(1, 10):
        x = cx0 + (idx - 1) * (cw + cgap)
        if idx <= 7:
            f.cell(x, cy, cw, ch, "green", [(f"#{idx}", "monob"), ("committed", "small")], kind="card", r=9, text_tone="green")
        else:
            f.cell(x, cy, cw, ch, "amber", [(f"#{idx}", "monob"), ("pending", "small")], kind="tonal", r=9, text_tone="amber")

    # Vertical dashed commit watermark between #7 and #8
    div_x = cx0 + 7 * cw + 6.5 * cgap
    f.rule(div_x, 54, div_x, 146, tone="green", width=2.0, dash="5 4")

    # Span brackets underneath
    c_start = cx0
    c_end = cx0 + 7 * cw + 6 * cgap
    u_start = cx0 + 7 * (cw + cgap)
    u_end = cx0 + 9 * cw + 8 * cgap

    f.rule(c_start, 158, c_end, 158, tone="green", width=1.8)
    f.rule(c_start, 153, c_start, 163, tone="green", width=1.8)
    f.rule(c_end, 153, c_end, 163, tone="green", width=1.8)
    f.text((c_start + c_end) / 2, 180, "Committed on majority (1..7) — applied to entries", "small", "middle", tone="green")

    f.rule(u_start, 158, u_end, 158, tone="amber", width=1.8)
    f.rule(u_start, 153, u_start, 163, tone="amber", width=1.8)
    f.rule(u_end, 153, u_end, 163, tone="amber", width=1.8)
    f.text((u_start + u_end) / 2, 180, "Uncommitted (8..9)", "small", "middle", tone="amber")

    # Bottom cards
    b_left = f.node(
        MARGIN, 250, 560, 92, "green",
        [("entries: BTreeMap (Visible to Reads)", "name"), ("Contains state of records 1..=7 · Served to get() and list()", "sub")],
        icon="table_rows", kind="card", icon_size=30,
    )
    b_right = f.node(
        MARGIN + 584, 250, 272, 92, "amber",
        [("Invisible Suffix", "name"), ("Records 8..9 await majority ACK", "sub")],
        icon="hourglass_top", kind="tonal", icon_size=28, text_tone="amber",
    )

    # Wires from brackets to bottom cards (span 198..250 = 52px)
    f.wire([((c_start + c_end) / 2, 198), ((c_start + c_end) / 2, b_left.y)], tone="green", width=2.0)
    f.wire([((u_start + u_end) / 2, 198), ((u_start + u_end) / 2, b_right.y)], tone="amber", dash=True, width=1.8)

    return f.save([
        ("Separating log persistence from commit visibility prevents clients from observing speculative writes that have not reached a majority.", "noteb"),
        "Records 8 and 9 remain safely buffered in the log until the leader's commit watermark advances past them.",
    ])


def ch03_repl_replica_struct():
    f = Fig(
        "ch03_repl_replica_struct",
        "Figure 3-3. On-Disk and In-Memory Data Structures Inside Replica.",
        448,
    )

    # Left Zone: On Disk (x=32..276, w=244)
    f.zone(
        MARGIN, 0, 244, 344, "amber",
        "On Disk",
        "Durable WAL storage",
        icon="save",
    )
    kvlog = f.node(
        MARGIN + 18, 66, 208, 108, "amber",
        [("kv.log", "monob"), ("Append-only WAL", "sub"), ("fsync on every append", "small")],
        icon="description", kind="card", icon_size=28,
    )
    f.node(
        MARGIN + 18, 210, 208, 112, "gray",
        [("Crash Recovery", "name"), ("Replayed from byte 0", "sub"), ("on Replica::open()", "small")],
        icon="shield", kind="tonal", icon_size=26,
    )

    # Right Zone: In Memory (x=384..888, w=504) -> 108px gap between zones!
    mx = 384
    mw = WIDTH - MARGIN - mx  # 504
    f.zone(
        mx, 0, mw, 344, "blue",
        "In Memory (struct Replica)",
        "Rebuilt from kv.log on open(); committed starts at 0",
        icon="memory",
    )

    records = f.node(
        mx + 18, 66, 224, 108, "blue",
        [("records: Vec<Record>", "monob"), ("Full sequence in RAM", "sub"), ("Indexed 1..=last_seq", "small")],
        icon="view_week", kind="card", icon_size=26,
    )
    committed = f.node(
        mx + 260, 66, 226, 108, "purple",
        [("committed: u64", "monob"), ("Starts at 0 -> n", "sub"), ("Majority watermark", "small")],
        icon="tune", kind="card", icon_size=26,
    )
    entries = f.node(
        mx + 18, 240, mw - 36, 86, "green",
        [("entries: BTreeMap<String, Vec<u8>>", "monob"), ("Applied state for records 1..=committed", "sub")],
        icon="table_rows", kind="card", icon_size=28,
    )

    # Wire 1: open() from kv.log -> records (span 258..402 = 144px)
    y1 = kvlog.cy - 22
    f.wire([(kvlog.r, y1), (records.x, y1)], tone="blue", width=2.0)
    step_badge(f, (kvlog.r + records.x - 9) / 2, y1, "1", tone="blue")
    f.label((kvlog.r + records.x) / 2, y1 - 15, "open()", tone="blue")

    # Wire 2: append() from records -> kv.log (span 402..258 = 144px)
    y2 = kvlog.cy + 22
    f.wire([(records.x, y2), (kvlog.r, y2)], tone="amber", width=2.0)
    step_badge(f, (records.x + kvlog.r + 9) / 2, y2, "2", tone="amber")
    f.label((records.x + kvlog.r) / 2, y2 + 23, "append()", tone="amber")

    # Wire 3: commit(n) from records -> entries (span 174..240 = 66px)
    f.wire([records.bottom(0), (records.cx, entries.y)], tone="green", width=2.0)
    step_badge(f, records.cx, (records.b + entries.y - 9) / 2, "3", tone="green", ring="c-blue")
    f.text(records.cx + 18, (records.b + entries.y) / 2 + 4, "commit(n)", "monob", "start", tone="green")

    # Dashed watermark wire from committed -> entries
    f.wire([committed.bottom(0), (committed.cx, entries.y)], tone="purple", dash=True, width=1.8)
    f.text(committed.cx + 12, (committed.b + entries.y) / 2 + 4, "watermark n", "small", "start", tone="purple")

    # Bottom Client Reads card (y=390..440, h=50) -> vertical span 326..390 = 64px
    client = f.node(
        mx + 18, 390, mw - 36, 50, "teal",
        [("Client Reads: get(key) / list()", "monob"), ("Reads entries exclusively", "small")],
        icon="laptop", kind="card", icon_size=26,
    )
    # Wire 4: entries -> client (span 326..390 = 64px)
    f.wire([entries.bottom(0), client.top(0)], tone="teal", width=2.0)
    step_badge(f, entries.cx, (entries.b + client.y - 9) / 2, "4", tone="teal")
    f.text(entries.cx + 18, (entries.b + client.y) / 2 + 4, "get() / list()", "monob", "start", tone="teal")

    return f.save([
        ("On startup, Replica::open() loads kv.log into records with committed = 0 so uncommitted entries are never exposed prematurely.", "noteb"),
        "Calling commit(n) replays records up to n into entries; get() and list() read entries exclusively.",
    ])


def ch03_repl_follower_flow():
    f = Fig(
        "ch03_repl_follower_flow",
        "Figure 3-4. Two-Check Validation Flow Inside Replica::handle_append.",
        406,
    )

    x_in = MARGIN
    x_c1 = x_in + 138 + 56       # 226
    x_c2 = x_c1 + 172 + 56       # 454
    x_ok = x_c2 + 172 + 56       # 682

    inp = f.node(
        x_in, 54, 138, 108, "blue",
        [("Append RPC", "name"), ("term, prev_seq", "mono"), ("batch, commit", "mono")],
        icon="lan", layout="center", kind="card", icon_size=24,
    )
    c1 = f.node(
        x_c1, 54, 172, 108, "purple",
        [("Check 1: Term", "name"), ("msg.term >=", "monob"), ("local_term ?", "monob")],
        icon="rule", layout="center", kind="card", icon_size=24,
    )
    c2 = f.node(
        x_c2, 54, 172, 108, "amber",
        [("Check 2: Prefix", "name"), ("prev_seq ==", "monob"), ("last_seq ?", "monob")],
        icon="call_split", layout="center", kind="card", icon_size=24,
    )
    app = f.node(
        x_ok, 54, 206, 108, "teal",
        [("Append Batch", "name"), ("Write + fsync kv.log", "sub"), ("Extend records Vec", "small")],
        icon="save", layout="center", kind="card", icon_size=24,
    )

    # Bottom row (y=244..338, vertical span 162..244 = 82px!)
    r1 = f.node(
        x_c1, 244, 172, 94, "red",
        [("Reject: Stale Term", "name"), ("appended = false", "monob"), ("Ignore outdated leader", "small")],
        layout="center", kind="tonal", text_tone="red",
    )
    r2 = f.node(
        x_c2, 244, 172, 94, "red",
        [("Reject: Log Gap", "name"), ("appended = false", "monob"), ("Leader backtracks", "small")],
        layout="center", kind="tonal", text_tone="red",
    )
    rep = f.node(
        x_ok, 244, 206, 94, "green",
        [("Commit & Reply", "name"), ("Advance commit watermark", "sub"), ("appended = true", "monob")],
        icon="play_arrow", layout="center", kind="card", icon_size=24, text_tone="green",
    )

    # Step 1: Input -> Check 1 (56px)
    f.wire([inp.right(0), c1.left(0)], tone="blue", width=2.0)
    step_badge(f, (inp.r + c1.x - 9) / 2, inp.cy, "1", tone="blue")

    # Step 2: Check 1 -> Check 2 (56px)
    f.wire([c1.right(0), c2.left(0)], tone="purple", width=2.0)
    step_badge(f, (c1.r + c2.x - 9) / 2, c1.cy, "2", tone="purple")
    f.text((c1.r + c2.x) / 2, c1.cy - 18, "Yes", "small", "middle", tone="purple")

    # Step 3: Check 2 -> Append Batch (56px)
    f.wire([c2.right(0), app.left(0)], tone="teal", width=2.0)
    step_badge(f, (c2.r + app.x - 9) / 2, c2.cy, "3", tone="teal")
    f.text((c2.r + app.x) / 2, c2.cy - 18, "Yes", "small", "middle", tone="teal")

    # Step 4: Append Batch -> Commit & Reply (82px)
    f.wire([app.bottom(0), rep.top(0)], tone="green", width=2.0)
    step_badge(f, app.cx, (app.b + rep.y - 9) / 2, "4", tone="green")

    # Reject wires (82px)
    f.wire([c1.bottom(0), r1.top(0)], tone="red", dash=True, width=1.8)
    f.label(c1.cx, (c1.b + r1.y) / 2 + 4, "No", tone="red")
    f.wire([c2.bottom(0), r2.top(0)], tone="red", dash=True, width=1.8)
    f.label(c2.cx, (c2.b + r2.y) / 2 + 4, "No", tone="red")

    # Bottom invariant strip
    f.node(
        MARGIN, 356, INNER, 40, "gray",
        [("Both checks must pass before the follower writes to kv.log or advances its commit watermark.", "body")],
        layout="center", kind="tonal", r=10,
    )

    return f.save([
        ("Check 1 fences off stale leaders with lower terms; Check 2 guarantees contiguous prefix matching before appending.", "noteb"),
        "Only when both checks succeed does handle_append persist the batch, advance committed, and reply appended=true.",
    ])


def ch03_repl_commit_rule():
    f = Fig(
        "ch03_repl_commit_rule",
        "Figure 3-6. Majority Commit Rule: Median Frontier Across Three Replicas.",
        396,
    )

    # Top Zone: 3 Replicas and their log frontiers (10, 7, 9)
    f.zone(
        MARGIN, 0, INNER, 196, "blue",
        "1. Replica Log Frontiers (Leader = 10, Follower A = 7, Follower B = 9)",
        "Each cell represents a durable log record; dashed line marks the highest sequence on a majority",
        icon="view_week",
    )

    replicas = [
        ("Leader", 10, "blue"),
        ("Follower A", 7, "teal"),
        ("Follower B", 9, "purple"),
    ]
    label_x = MARGIN + 18
    grid_x = MARGIN + 132
    cw = 62
    cgap = 6
    # 10*62 + 9*6 = 620 + 54 = 674 -> grid_x + 674 = 838 (fits inside 888 with 50px right margin!)

    for r_idx, (name, seq, tone) in enumerate(replicas):
        ry = 62 + r_idx * 42
        f.text(label_x, ry + 20, name, "name", "start", tone=tone, fit=(label_x, grid_x - 8))
        for i in range(1, 11):
            cx = grid_x + (i - 1) * (cw + cgap)
            if i <= seq:
                ctone = "green" if i <= 9 else "amber"
                f.cell(cx, ry, cw, 30, ctone, [(f"{i}", "monob")], kind="mid", r=6, text_tone=ctone)
            else:
                f.cell(cx, ry, cw, 30, "gray", [("·", "small")], kind="dashed", r=6)
        f.pill(grid_x + 10 * (cw + cgap) + 2, ry + 5, f"{seq}", tone=tone, anchor="start")

    # Majority watermark line after #9
    wm_x = grid_x + 9 * cw + 8.5 * cgap
    f.rule(wm_x, 54, wm_x, 188, tone="green", width=2.2, dash="5 4")

    # Bottom-left: Sort & Pick Median
    bl = f.zone(
        MARGIN, 218, 416, 168, "purple",
        "2. Sort Descending & Pick Median",
        "For N = 3 replicas, majority index is floor(3/2) = 1",
        icon="tune",
    )
    # Unsorted -> Sorted
    f.cell(MARGIN + 22, 290, 128, 62, "gray", [("Frontiers", "small"), ("[10, 7, 9]", "monob")], kind="card", r=10)
    f.wire([(MARGIN + 150, 321), (MARGIN + 196, 321)], tone="purple", width=2.0)
    # Sorted 3 cells
    sx = MARGIN + 200
    for idx, (val, t, k) in enumerate([("10", "gray", "card"), ("9", "green", "mid"), ("7", "gray", "card")]):
        f.cell(sx + idx * 72, 290, 64, 62, t, [(f"[{idx}]", "small"), (val, "monob")], kind=k, r=10, text_tone=t if idx == 1 else None)
    f.text(sx + 72 + 32, 372, "Median = 9", "badge", "middle", tone="green")

    # Bottom-right: Commit Outcome
    br_x = MARGIN + 440
    f.zone(
        br_x, 218, 416, 168, "green",
        "3. Advance Commit Watermark",
        "Safe to expose 1..9; record 10 waits for a second copy",
        icon="shield",
    )
    f.node(
        br_x + 18, 282, 182, 82, "green",
        [("Records 1..9", "monob"), ("Committed", "name"), ("On >= 2 of 3 nodes", "small")],
        layout="center", kind="card", text_tone="green",
    )
    f.node(
        br_x + 216, 282, 182, 82, "amber",
        [("Record 10", "monob"), ("Uncommitted", "name"), ("Leader only so far", "small")],
        layout="center", kind="tonal", text_tone="amber",
    )

    return f.save([
        ("Sorting the three replica frontiers [10, 7, 9] descending gives [10, 9, 7]; the median entry (9) is guaranteed durable on a majority.", "noteb"),
        "Record 10 exists only on the leader and remains uncommitted until at least one follower acknowledges it.",
    ])


def ch03_repl_leader_parts():
    f = Fig(
        "ch03_repl_leader_parts",
        "Figure 3-7. Internal Concurrency Architecture of a kvnode Leader.",
        456,
    )

    # Top row: Node::write -> propose -> split bus -> Follower Task A/B -> Follower 1/2
    w_node = f.node(
        MARGIN, 56, 152, 92, "blue",
        [("Node::write", "monob"), ("Acquires write turn", "sub"), ("Awaits commit", "small")],
        icon="laptop", layout="center", kind="card", icon_size=24,
    )
    propose = f.node(
        248, 56, 158, 92, "teal",
        [("Replica::propose", "monob"), ("Append + fsync", "sub"), ("Wake tasks", "small")],
        icon="save", layout="center", kind="card", icon_size=24,
    )

    # Follower tasks (x=492, w=162)
    task_a = f.node(
        492, 14, 162, 76, "purple",
        [("Follower Task A", "name"), ("Build Append RPC", "sub")],
        icon="loop", layout="center", kind="card", icon_size=22,
    )
    task_b = f.node(
        492, 114, 162, 76, "purple",
        [("Follower Task B", "name"), ("Build Append RPC", "sub")],
        icon="loop", layout="center", kind="card", icon_size=22,
    )

    # Remote followers (x=722, w=166)
    foll_a = f.node(
        722, 14, 166, 76, "gray",
        [("Follower 1 (gRPC)", "name"), ("Persist & ACK seq", "sub")],
        icon="dns", layout="center", kind="tonal", icon_size=22,
    )
    foll_b = f.node(
        722, 114, 166, 76, "gray",
        [("Follower 2 (gRPC)", "name"), ("Persist & ACK seq", "sub")],
        icon="dns", layout="center", kind="tonal", icon_size=22,
    )

    # Bottom row (y=282..374, h=92) -> vertical gap from task_b (b=190) is 92px!
    maj = f.node(
        492, 282, 396, 92, "amber",
        [("majority_sequence()", "monob"), ("Records ACKs -> computes median watermark", "sub")],
        icon="tune", kind="card", icon_size=28,
    )
    watch = f.node(
        248, 282, 174, 92, "green",
        [("committed watch", "monob"), ("Broadcasts new n", "sub"), ("tokio::sync::watch", "small")],
        icon="notifications_active", layout="center", kind="card", icon_size=24,
    )
    ack = f.node(
        MARGIN, 282, 152, 92, "green",
        [("HTTP 201 / 204", "monob"), ("Unblocks write()", "sub"), ("Durable on quorum", "small")],
        icon="play_arrow", layout="center", kind="tonal", icon_size=24, text_tone="green",
    )

    # Step 1: Node::write -> propose (span 184..248 = 64px)
    f.wire([w_node.right(0), propose.left(0)], tone="blue", width=2.0)
    step_badge(f, (w_node.r + propose.x - 9) / 2, w_node.cy, "1", tone="blue")

    # Step 2: propose -> symmetric split bus (trunk 406..464 = 58px -> split to task_a & task_b)
    bus_x = 464
    f.wire([propose.right(0), (bus_x, propose.cy)], tone="purple", head=False, width=2.0)
    f.wire([(bus_x, propose.cy), (bus_x, task_a.cy), task_a.left(0)], tone="purple", width=2.0)
    f.wire([(bus_x, propose.cy), (bus_x, task_b.cy), task_b.left(0)], tone="purple", width=2.0)
    step_badge(f, (propose.r + bus_x) / 2, propose.cy, "2", tone="purple")

    # Step 3: Follower tasks <-> Followers (span 654..722 = 68px)
    f.wire([task_a.right(0), foll_a.left(0)], tone="blue", width=2.0)
    f.wire([task_b.right(0), foll_b.left(0)], tone="blue", width=2.0)
    step_badge(f, (task_a.r + foll_a.x - 9) / 2, task_a.cy, "3", tone="blue")
    f.text((task_b.r + foll_b.x) / 2, task_b.cy - 12, "Append", "small", "middle", tone="blue")

    # Step 4: Followers/Tasks -> majority_sequence (vertical span 190..282 = 92px)
    f.wire([foll_b.bottom(0), (foll_b.cx, maj.y)], tone="amber", width=2.0)
    f.wire([task_b.bottom(0), (task_b.cx, maj.y)], tone="amber", dash=True, width=1.8)
    step_badge(f, foll_b.cx, (foll_b.b + maj.y - 9) / 2, "4", tone="amber")
    f.text(foll_b.cx - 18, (foll_b.b + maj.y) / 2 + 4, "ACK seq", "small", "end", tone="amber")

    # Step 5: majority_sequence -> committed watch (left span 492..422 = 70px)
    f.wire([maj.left(0), watch.right(0)], tone="green", width=2.0)
    step_badge(f, (maj.x + watch.r + 9) / 2, maj.cy, "5", tone="green")

    # Step 6: committed watch -> HTTP 201/204 (left span 248..184 = 64px)
    f.wire([watch.left(0), ack.right(0)], tone="green", width=2.0)
    step_badge(f, (watch.x + ack.r + 9) / 2, watch.cy, "6", tone="green")

    path_legend(f, 410, "Solid: Write & replication handoffs (1 -> 6)", "Dashed: Per-follower task status signal")

    return f.save([
        ("Each follower runs in its own async task so a slow or partitioned peer never stalls replication to the healthy majority.", "noteb"),
        "When majority_sequence() advances, the tokio::sync::watch channel wakes Node::write to return HTTP 201/204.",
    ])


# =============================================================================
# CHAPTER 4: LEADER ELECTION (RAFT)
# =============================================================================

def ch04_elect_disk_memory():
    f = Fig(
        "ch04_elect_disk_memory",
        "Figure 4-2. Durable On-Disk Files vs. Volatile In-Memory State of a Raft Member.",
        396,
    )

    # Left Zone: Disk (x=32..424, w=392); Gap=72px; Right Zone: RAM (x=496..888, w=392)
    zw = 392
    rx = MARGIN + zw + 72  # 496

    f.zone(
        MARGIN, 0, zw, 332, "amber",
        "Durable On-Disk State",
        "Persisted via fsync() before sending any RPC reply",
        icon="save",
    )
    f.node(
        MARGIN + 18, 66, zw - 36, 112, "amber",
        [("kv.log", "monob"), ("WAL records + term markers", "sub"), ("Truncated on divergent tails", "small")],
        icon="description", kind="card", icon_size=28,
    )
    f.node(
        MARGIN + 18, 198, zw - 36, 112, "red",
        [("state (meta file)", "monob"), ("current_term: u64", "mono"), ("voted_for: Option<NodeId>", "mono")],
        icon="lock", kind="card", icon_size=28,
    )

    f.zone(
        rx, 0, zw, 332, "blue",
        "Volatile In-Memory State (RAM)",
        "Reconstructed from disk on boot; lost on crash",
        icon="memory",
    )

    ram_items = [
        ("records", "Vec<Record>", "blue"),
        ("terms", "Vec<u64>", "purple"),
        ("entries", "BTreeMap", "green"),
        ("committed", "u64 (0 on boot)", "teal"),
        ("role", "Follower on boot", "amber"),
        ("leader", "Option<NodeId>", "gray"),
    ]
    cw = 172
    ch = 74
    for idx, (k, v, tone) in enumerate(ram_items):
        col = idx % 2
        row = idx // 2
        cx = rx + 18 + col * (cw + 12)
        cy = 66 + row * (ch + 12)
        f.cell(cx, cy, cw, ch, tone, [(k, "monob"), (v, "small")], kind="card", r=10, text_tone=tone)

    # Bridge wire across the 72px gap (x=424..496)
    f.wire([(MARGIN + zw, 166), (rx, 166)], tone="teal", width=2.2)
    f.label((MARGIN + zw + rx) / 2, 152, "Boot", tone="teal")
    f.label((MARGIN + zw + rx) / 2, 186, "replay", tone="teal")

    # Bottom invariant strip
    f.node(
        MARGIN, 348, INNER, 40, "red",
        [("Invariant: current_term and voted_for must hit disk before granting a vote, preventing split-brain after a crash.", "body")],
        layout="center", kind="tonal", r=10, text_tone="red",
    )

    return f.save([
        ("Only two files live on disk: kv.log for replicated records and state for the monotonic term and vote.", "noteb"),
        "All six in-memory fields (records, terms, entries, committed, role, leader) are rebuilt safely on restart.",
    ])


def ch04_elect_steps():
    f = Fig(
        "ch04_elect_steps",
        "Figure 4-3. Eight-Step Cold-Start Raft Election Across Three Members.",
        518,
    )

    # Column geometry: Step badge col (x=32..142, w=110), 3 member cols (w=236, gap=14 -> 3*236+2*14 = 736; 110+10+736 = 856)
    step_w = 110
    mw = 236
    mgap = 14
    mx = [MARGIN + step_w + 10 + i * (mw + mgap) for i in range(3)]

    # Header cards
    headers = [
        ("Member 1", "Timeout: 17 ticks", "blue"),
        ("Member 2", "Timeout: 14 ticks", "teal"),
        ("Member 3", "Timeout: 11 ticks", "purple"),
    ]
    f.cell(MARGIN, 0, step_w, 46, "gray", [("Step", "name")], kind="tonal", r=10)
    for i, (t, s, tone) in enumerate(headers):
        f.cell(mx[i], 0, mw, 46, tone, [(t, "name"), (s, "small")], kind="mid", r=10, text_tone=tone)

    rows = [
        ("1", "Boot T0", "gray", ("Follower · T0", "gray"), ("Follower · T0", "gray"), ("Follower · T0", "gray")),
        ("2", "Tick 11", "purple", ("Waiting (6 left)", "gray"), ("Waiting (3 left)", "gray"), ("Timeout -> Candidate T1", "purple")),
        ("3", "Self-Vote", "amber", ("Follower · T0", "gray"), ("Follower · T0", "gray"), ("fsync term=1, vote=3", "amber")),
        ("4", "ReqVote", "blue", ("<- RequestVote(T1, 0)", "blue"), ("<- RequestVote(T1, 0)", "blue"), ("Broadcast RequestVote", "blue")),
        ("5", "Grant", "teal", ("fsync T1,v=3 -> Grant", "teal"), ("fsync T1,v=3 -> Grant", "teal"), ("Collect 3 / 3 votes", "teal")),
        ("6", "Leader", "green", ("Follower · T1", "gray"), ("Follower · T1", "gray"), ("Promoted to Leader T1", "green")),
        ("7", "Marker #1", "green", ("Append & ACK #1", "green"), ("Append & ACK #1", "green"), ("Commit term-1 marker #1", "green")),
        ("8", "Write #2", "blue", ("Append & ACK #2", "blue"), ("Append & ACK #2", "blue"), ("Serve client write #2", "blue")),
    ]

    ry = 58
    rh = 46
    rgap = 10
    for num, label, st_tone, c1, c2, c3 in rows:
        # Step cell with circular badge
        f.rect(MARGIN, ry, step_w, rh, f"c-{st_tone}", r=9)
        step_badge(f, MARGIN + 20, ry + rh / 2, num, tone=st_tone, ring=f"c-{st_tone}")
        f.text(MARGIN + 38, ry + rh / 2 + 4, label, "small", "start", tone=st_tone, fit=(MARGIN + 36, MARGIN + step_w - 6))

        for i, (txt, ctone) in enumerate((c1, c2, c3)):
            kind = "card" if ctone != "gray" else "tonal"
            f.cell(mx[i], ry, mw, rh, ctone, [(txt, "small")], kind=kind, r=9, text_tone=ctone if ctone != "gray" else None)

        ry += rh + rgap

    return f.save([
        ("Randomized election timeouts (17, 14, 11 ticks) break symmetry so Member 3 starts term 1 alone without a split vote.", "noteb"),
        "Before serving client write #2, the new leader commits a term-1 marker (#1) to establish current-term commitment.",
    ])


def ch04_elect_vote_rule():
    f = Fig(
        "ch04_elect_vote_rule",
        "Figure 4-4. Raft Log-Freshness Voting Comparison Across Three Members.",
        412,
    )

    f.zone(
        MARGIN, 0, INNER, 198, "blue",
        "1. Compare Final Log Entry: (last_term, last_seq) Lexicographically",
        "Higher final term wins first; if final terms tie, longer sequence wins",
        icon="rule",
    )

    members = [
        ("Member 1", [("T1", 1), ("T1", 2), ("T1", 3), ("T1", 4)], "(T1, seq 4)", "blue"),
        ("Member 2", [("T1", 1), ("T1", 2), ("T1", 3), ("T2", 4), ("T2", 5)], "(T2, seq 5) · Freshest", "green"),
        ("Member 3", [("T1", 1), ("T1", 2), ("T1", 3)], "(T1, seq 3) · Stale", "amber"),
    ]
    gx = MARGIN + 128
    cw = 92
    cgap = 8
    for idx, (name, entries, badge, tone) in enumerate(members):
        ry = 62 + idx * 42
        f.text(MARGIN + 18, ry + 20, name, "name", "start", tone=tone)
        for j, (t, seq) in enumerate(entries):
            ctone = "green" if t == "T2" else "blue"
            f.cell(gx + j * (cw + cgap), ry, cw, 30, ctone, [(f"{t} : #{seq}", "monob")], kind="mid", r=6, text_tone=ctone)
        f.pill(gx + 5 * (cw + cgap) + 12, ry + 5, badge, tone=tone, anchor="start")

    # Bottom Zone: Vote Outcomes
    f.zone(
        MARGIN, 218, INNER, 184, "gray",
        "2. Peer Vote Outcomes Under Raft's Up-to-Date Log Rule",
        "A voter grants its vote only if the candidate's log is at least as fresh as its own",
        icon="handshake",
    )

    cards = [
        ("Candidate: Member 2", "(T2, 5) >= M1 and M3", "Peer votes: M1 + M3 (All)", "Wins election", "green"),
        ("Candidate: Member 1", "(T1, 4) >= M3, but < M2", "Peer votes: M3 only", "M2 denies (T2 > T1)", "amber"),
        ("Candidate: Member 3", "(T1, 3) < M1 and M2", "Peer votes: None", "M1 & M2 both deny", "red"),
    ]
    bw = 264
    bgap = 14
    bx0 = MARGIN + 18
    for i, (t, cmp_txt, votes, res, tone) in enumerate(cards):
        f.node(
            bx0 + i * (bw + bgap), 280, bw, 106, tone,
            [(t, "name"), (cmp_txt, "mono"), (votes, "sub"), (res, "badge")],
            layout="center", kind="card", text_tone=tone,
        )

    return f.save([
        ("Raft compares (last_term, last_seq) lexicographically: Member 2's term-2 entry beats both term-1 logs regardless of length.", "noteb"),
        "Member 1 beats Member 3 on sequence length (4 > 3) within term 1, while Member 3 receives zero peer votes.",
    ])


def ch04_elect_append_flow():
    f = Fig(
        "ch04_elect_append_flow",
        "Figure 4-6. Three-Check Decision Tree Inside Member::on_append.",
        426,
    )

    # 4 columns across 856px: w=178, gap=48 -> 4*178 + 3*48 = 712 + 144 = 856!
    w = 178
    gap = 48
    xs = [MARGIN + i * (w + gap) for i in range(4)]

    c1 = f.node(
        xs[0], 40, w, 114, "purple",
        [("1. Term Check", "name"), ("msg.term >=", "monob"), ("local_term ?", "monob"), ("Pass: reset timer", "small")],
        icon="rule", layout="center", kind="card", icon_size=22,
    )
    c2 = f.node(
        xs[1], 40, w, 114, "blue",
        [("2. Presence Check", "name"), ("log contains", "sub"), ("prev_seq ?", "monob")],
        icon="view_week", layout="center", kind="card", icon_size=22,
    )
    c3 = f.node(
        xs[2], 40, w, 114, "amber",
        [("3. Term Match", "name"), ("term[prev_seq] ==", "monob"), ("prev_term ?", "monob")],
        icon="call_split", layout="center", kind="card", icon_size=22,
    )
    ok = f.node(
        xs[3], 40, w, 290, "green",
        [("4. Member::store", "name"), ("Skip matching prefix", "sub"), ("Truncate conflicts", "sub"), ("Append + fsync", "sub"), ("Advance commit", "sub"), ("appended = true", "monob")],
        icon="save", layout="center", kind="card", icon_size=26, text_tone="green",
    )

    # Reject boxes below checks 1, 2, 3 (vertical span 154..236 = 82px)
    r1 = f.node(
        xs[0], 236, w, 94, "red",
        [("Reject: Stale Term", "name"), ("appended = false", "monob"), ("Timer unchanged", "small")],
        layout="center", kind="tonal", text_tone="red",
    )
    r2 = f.node(
        xs[1], 236, w, 94, "red",
        [("Reject: Too Short", "name"), ("appended = false", "monob"), ("Leader backtracks", "small")],
        layout="center", kind="tonal", text_tone="red",
    )
    r3 = f.node(
        xs[2], 236, w, 94, "red",
        [("Reject: Conflict", "name"), ("appended = false", "monob"), ("Leader backtracks", "small")],
        layout="center", kind="tonal", text_tone="red",
    )

    # Pass wires (horizontal, 48px)
    for src, dst, tone in ((c1, c2, "purple"), (c2, c3, "blue"), (c3, ok, "green")):
        f.wire([src.right(0), (dst.x, src.cy)], tone=tone, width=2.0)
        f.text((src.r + dst.x) / 2, src.cy - 10, "Yes", "small", "middle", tone=tone)

    # Reject wires (vertical, 82px)
    for src, dst in ((c1, r1), (c2, r2), (c3, r3)):
        f.wire([src.bottom(0), dst.top(0)], tone="red", dash=True, width=1.8)
        f.label(src.cx, (src.b + dst.y) / 2 + 4, "No", tone="red")

    # Bottom highlight strip
    f.node(
        MARGIN, 354, INNER, 52, "teal",
        [("Side effect of Check 1: recognizing a valid term resets the election timeout and records leader_id immediately,", "body"),
         ("even if Check 2 or Check 3 rejects due to a missing prefix or term mismatch.", "small")],
        layout="center", kind="tonal", r=10, text_tone="teal",
    )

    return f.save([
        ("Three sequential checks enforce the Raft Log Matching Property before mutating the follower's log.", "noteb"),
        "Check 1 also suppresses unnecessary elections while a lagging follower catches up via backtracking.",
    ])


def ch04_elect_store_example():
    f = Fig(
        "ch04_elect_store_example",
        "Figure 4-7. Divergent Tail Reconciliation Inside Member::store.",
        438,
    )

    f.zone(
        MARGIN, 0, INNER, 372, "blue",
        "Reconciling Divergent Follower Tail (d, e, x, y) Against Leader Batch (e, f, g, h)",
        "Idempotent skip of matching record #5, truncation of conflicting (x, y), and single batched append of (f, g, h)",
        icon="swap_horiz",
    )

    # Column layout: label col x=48..228, 5 sequence cols #4..#8 (w=112, gap=14 -> 5*112+4*14 = 616 -> 244..860)
    lx = MARGIN + 18
    gx = 244
    cw = 112
    cgap = 14

    # Sequence column headers
    for i, seq in enumerate((4, 5, 6, 7, 8)):
        cx = gx + i * (cw + cgap)
        f.text(cx + cw / 2, 74, f"Index #{seq}", "monob", "middle", tone="blue")

    # Row 1: Follower Before
    y1 = 86
    f.text(lx, y1 + 30, "Follower Before", "name", "start")
    f.text(lx, y1 + 48, "Divergent tail (x, y)", "small", "start", tone="red")
    r1_cells = [
        ("d", "prefix", "gray", "card"),
        ("e", "matches", "green", "card"),
        ("x", "conflict", "red", "mid"),
        ("y", "conflict", "red", "mid"),
        (None, None, None, None),
    ]
    for i, (val, sub, tone, kind) in enumerate(r1_cells):
        cx = gx + i * (cw + cgap)
        if val:
            f.cell(cx, y1, cw, 56, tone, [(val, "monob"), (sub, "small")], kind=kind, r=9, text_tone=tone if tone != "gray" else None)
        else:
            f.cell(cx, y1, cw, 56, "gray", [("empty", "small")], kind="dashed", r=9)

    # Row 2: Leader Batch (after #4)
    y2 = 162
    f.text(lx, y2 + 30, "Leader Batch", "name", "start", tone="blue")
    f.text(lx, y2 + 48, "Sent after prev #4", "small", "start")
    r2_cells = [
        ("prev #4", "anchor", "gray", "dashed"),
        ("e", "same", "green", "card"),
        ("f", "new", "blue", "mid"),
        ("g", "new", "blue", "mid"),
        ("h", "new", "blue", "mid"),
    ]
    for i, (val, sub, tone, kind) in enumerate(r2_cells):
        cx = gx + i * (cw + cgap)
        f.cell(cx, y2, cw, 56, tone, [(val, "monob"), (sub, "small")], kind=kind, r=9, text_tone=tone if tone != "gray" else None)

    # Action pills between Row 2 and Row 3 (y=234..266)
    f.pill(gx + 1 * (cw + cgap) + cw / 2, 236, "1. Skip #5", tone="teal", anchor="middle")
    f.pill(gx + 2 * (cw + cgap) + cw + cgap / 2, 236, "2. Truncate (x, y)", tone="red", anchor="middle")
    f.pill(gx + 4 * (cw + cgap) + cw / 2, 236, "3. Append (f,g,h)", tone="blue", anchor="middle")

    # Row 3: Follower After
    y3 = 278
    f.text(lx, y3 + 30, "Follower After", "name", "start", tone="green")
    f.text(lx, y3 + 48, "Matches leader log", "small", "start", tone="green")
    r3_cells = [
        ("d", "kept", "gray", "card"),
        ("e", "skipped", "teal", "card"),
        ("f", "appended", "blue", "card"),
        ("g", "appended", "blue", "card"),
        ("h", "appended", "blue", "card"),
    ]
    for i, (val, sub, tone, kind) in enumerate(r3_cells):
        cx = gx + i * (cw + cgap)
        f.cell(cx, y3, cw, 56, tone, [(val, "monob"), (sub, "small")], kind=kind, r=9, text_tone=tone if tone != "gray" else None)

    # Bottom summary strip
    f.node(
        MARGIN, 388, INNER, 42, "teal",
        [("All new records (f, g, h) are written and fsynced in a single batched append after truncating the conflicting suffix.", "body")],
        layout="center", kind="tonal", r=10, text_tone="teal",
    )

    return f.save([
        ("Skipping matching record #5 makes AppendEntries idempotent under network retries without rewriting valid disk prefixes.", "noteb"),
        "Only the divergent suffix (x, y) is truncated before appending (f, g, h) in one WAL write.",
    ])


def ch04_elect_node_loop():
    f = Fig(
        "ch04_elect_node_loop",
        "Figure 4-8. Asynchronous Event Loop Driving raft::Member in kvraft.",
        444,
    )

    # Left column (x=32, w=178): Clock Task + HTTP Handlers
    clock = f.node(
        MARGIN, 24, 178, 84, "purple",
        [("Clock Task", "name"), ("100 ms tick loop", "sub")],
        icon="timer", kind="card", icon_size=26,
    )
    http = f.node(
        MARGIN, 136, 178, 84, "blue",
        [("HTTP Handlers", "name"), ("Client PUT / GET", "sub")],
        icon="laptop", kind="card", icon_size=26,
    )

    # Center column (x=282, w=232): Mutex<raft::Member> -> 72px gap from left col!
    mtx = f.zone(
        282, 24, 232, 196, "teal",
        "Mutex<Member>",
        "Pure state machine",
        icon="lock",
    )
    f.node(
        298, 84, 200, 54, "teal",
        [("Step tick / write / reply", "small"), ("Produce Vec<Envelope>", "monob")],
        layout="center", kind="card", r=9,
    )
    f.pill(398, 152, "Drop Mutex before I/O", tone="amber", anchor="middle")
    f.text(398, 196, "Zero network waits inside lock", "small", "middle", tone="teal")

    # Right column (x=586, w=302): Concurrent gRPC Dispatch -> 72px gap from center!
    grpc = f.zone(
        586, 24, 302, 196, "amber",
        "Concurrent gRPC Dispatch",
        "Spawned tasks outside the Mutex",
        icon="lan",
    )
    f.node(
        604, 84, 266, 54, "amber",
        [("One task per Envelope", "name"), ("500 ms RPC timeout bound", "sub")],
        layout="center", kind="card", r=9,
    )
    f.pill(737, 152, "Parallel RequestVote / Append", tone="amber", anchor="middle")
    f.text(737, 196, "Slow peers cannot block the lock", "small", "middle", tone="amber")

    # Bottom row (y=292..378, h=86) -> 72px vertical gap from top row (b=220)!
    peers = f.node(
        586, 292, 302, 86, "gray",
        [("Peer Raft Nodes (gRPC)", "name"), ("Persist state & return replies", "sub")],
        icon="dns", kind="tonal", icon_size=28,
    )
    feed = f.node(
        282, 292, 232, 86, "green",
        [("Feed Replies Back", "name"), ("Lock Mutex & wake HTTP", "sub")],
        icon="loop", kind="card", icon_size=26,
    )

    # Return wire from feed -> HTTP Handlers (left span 282..210? Route up to http.bottom!)
    f.wire([feed.left(0), (http.cx, feed.cy), http.bottom(0)], tone="green", dash=True, width=1.8)
    f.label(http.cx, 262, "Wake HTTP", tone="green")

    # Numbered step wires 1..6 (EVERY span is exactly 72px!)
    # 1: Clock -> Mutex (x=210..282, y=66)
    f.wire([clock.right(0), (mtx.x, clock.cy)], tone="purple", width=2.0)
    step_badge(f, (clock.r + mtx.x - 9) / 2, clock.cy, "1", tone="purple")

    # 2: HTTP -> Mutex (x=210..282, y=178)
    f.wire([http.right(0), (mtx.x, http.cy)], tone="blue", width=2.0)
    step_badge(f, (http.r + mtx.x - 9) / 2, http.cy, "2", tone="blue")

    # 3: Mutex -> gRPC Dispatch (x=514..586, y=122)
    f.wire([mtx.right(0), grpc.left(0)], tone="amber", width=2.0)
    step_badge(f, (mtx.r + grpc.x - 9) / 2, mtx.cy, "3", tone="amber")
    f.text((mtx.r + grpc.x) / 2, mtx.cy - 18, "Envelopes", "small", "middle", tone="amber")

    # 4: gRPC Dispatch -> Peers (y=220..292, x=737)
    f.wire([grpc.bottom(0), peers.top(0)], tone="amber", width=2.0)
    step_badge(f, grpc.cx, (grpc.b + peers.y - 9) / 2, "4", tone="amber")
    f.text(grpc.cx + 18, (grpc.b + peers.y) / 2 + 4, "500 ms RPC", "small", "start", tone="amber")

    # 5: Peers -> Feed Replies (left-pointing x=586..514, y=335)
    f.wire([peers.left(0), feed.right(0)], tone="green", width=2.0)
    step_badge(f, (peers.x + feed.r + 9) / 2, peers.cy, "5", tone="green")
    f.text((peers.x + feed.r) / 2, peers.cy - 18, "Replies", "small", "middle", tone="green")

    # 6: Feed Replies -> Mutex (upward y=292..220, x=398)
    f.wire([feed.top(0), mtx.bottom(0)], tone="teal", width=2.0)
    step_badge(f, feed.cx, (feed.y + mtx.b + 9) / 2, "6", tone="teal")
    f.text(feed.cx + 18, (feed.y + mtx.b) / 2 + 4, "Apply reply", "small", "start", tone="teal")

    path_legend(f, 404, "Solid: Lock-free I/O handoff cycle (1 -> 6)", "Dashed: Watch notification to HTTP client")

    return f.save([
        ("raft::Member performs zero network I/O under the Mutex: it returns outbound Envelope messages and releases the lock immediately.", "noteb"),
        "Concurrent 500 ms-bounded gRPC tasks deliver envelopes to peers and feed replies back into the state machine.",
    ])


def ch04_elect_probe():
    f = Fig(
        "ch04_elect_probe",
        "Figure 4-9. Empirical 20-Second Continuous Write Probe Across Leader Failover.",
        396,
    )

    f.zone(
        MARGIN, 0, INNER, 282, "blue",
        "Continuous Client Write Timeline (0.0 s to 20.0 s)",
        "Three-node Raft shard sustaining write traffic through an abrupt leader SIGKILL",
        icon="timer",
    )

    # Timeline axis: x=76..856 (780px -> 39 px/s)
    x0 = 76
    x1 = 856
    px_per_s = (x1 - x0) / 20.0  # 39.0
    t_kill = x0 + 6.0 * px_per_s    # 310.0
    t_elec = x0 + 7.1 * px_per_s    # 352.9

    bar_y = 140
    bar_h = 64

    # Phase 1: Leader A active (0..6.0 s)
    f.rect(x0, bar_y, t_kill - x0, bar_h, "m-green", r=8)
    f.text((x0 + t_kill) / 2, bar_y + 28, "Leader A Active", "name", "middle", tone="green")
    f.text((x0 + t_kill) / 2, bar_y + 46, "Continuous PUTs", "small", "middle", tone="green")

    # Phase 2: Failover / Election pause (6.0..7.1 s)
    f.rect(t_kill, bar_y, t_elec - t_kill, bar_h, "m-amber", r=4)

    # Phase 3: New Leader B active (7.1..20.0 s)
    f.rect(t_elec, bar_y, x1 - t_elec, bar_h, "m-teal", r=8)
    f.text((t_elec + x1) / 2, bar_y + 28, "New Leader B Active", "name", "middle", tone="teal")
    f.text((t_elec + x1) / 2, bar_y + 46, "Writes resume seamlessly · 0 lost acknowledgments", "small", "middle", tone="teal")

    # Vertical markers & callout pills
    f.rule(t_kill, 84, t_kill, bar_y + bar_h + 18, tone="red", width=2.0, dash="5 4")
    f.pill(t_kill - 6, 68, "Leader killed (6.0 s)", tone="red", anchor="end")

    f.rule(t_elec, 84, t_elec, bar_y + bar_h + 18, tone="teal", width=2.0, dash="5 4")
    f.pill(t_elec + 6, 68, "New leader elected (7.1 s)", tone="teal", anchor="start")

    # Pause bracket above amber gap
    f.pill((t_kill + t_elec) / 2, 108, "1.05 s max pause", tone="amber", anchor="middle")

    # Time axis & ticks (0..20s every 2s)
    axis_y = bar_y + bar_h + 26
    f.rule(x0, axis_y, x1, axis_y, tone="gray", width=1.4)
    for sec in range(0, 21, 2):
        tx = x0 + sec * px_per_s
        f.rule(tx, axis_y - 4, tx, axis_y + 5, tone="gray", width=1.4)
        f.text(tx, axis_y + 22, f"{sec} s", "small", "middle")

    # Bottom 3 KPI cards (w=274, gap=17 -> 3*274 + 2*17 = 856)
    kpis = [
        ("Leader Killed", "t = 6.0 s (SIGKILL)", "red", "bolt"),
        ("Max Write Pause", "1.05 s (6.0 s -> 7.1 s)", "amber", "hourglass_top"),
        ("Verified Writes", "1,443 / 1,443 intact", "green", "shield"),
    ]
    kw = 274
    kgap = 17
    for i, (t, v, tone, ic) in enumerate(kpis):
        f.node(
            MARGIN + i * (kw + kgap), 300, kw, 84, tone,
            [(t, "sub"), (v, "monob")],
            icon=ic, kind="card", icon_size=28, text_tone=tone,
        )

    return f.save([
        ("When the leader is killed at 6.0 s, the remaining two nodes elect a replacement and resume writes by 7.1 s.", "noteb"),
        "All 1,443 acknowledged writes across the 20-second probe were verified present after failover with a 1.05 s maximum pause.",
    ])


ALL_FIGURES = [
    # Chapter 2
    ch02_crash_points,
    ch02_survives,
    ch02_sync_cost,
    ch02_two_machines,
    # Chapter 3
    ch03_repl_state,
    ch03_repl_replica_struct,
    ch03_repl_follower_flow,
    ch03_repl_commit_rule,
    ch03_repl_leader_parts,
    # Chapter 4
    ch04_elect_disk_memory,
    ch04_elect_steps,
    ch04_elect_vote_rule,
    ch04_elect_append_flow,
    ch04_elect_store_example,
    ch04_elect_node_loop,
    ch04_elect_probe,
]


def main():
    total_problems = 0
    for fn in ALL_FIGURES:
        total_problems += fn()
    print(f"Generated {len(ALL_FIGURES)} M3 figures ({len(ALL_FIGURES) * 2} SVGs) with {total_problems} fit warnings.")
    return 1 if total_problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
