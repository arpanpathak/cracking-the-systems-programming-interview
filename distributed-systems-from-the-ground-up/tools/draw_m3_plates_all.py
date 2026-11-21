#!/usr/bin/env python3
"""Bespoke abstract geometric SVG chapter plates for Chapters 2-6, 8-18, 20-28.

Each plate uses crisp, zero-blur Swiss-Modernist / Bauhaus geometry tailored to
the chapter's mathematical and architectural core, in paired Light and Night-Owl
Dark variants.
"""
import math
from draw_m3_plates import W, H, header_svg, swiss_lockup, arc_path


def _base(num, title, s1, s2, bg_key, grid_key, accent_key, eq_line, t, aria):
    p = header_svg(aria, t[bg_key], t[grid_key], t)
    p += swiss_lockup(num, title, s1, s2, t[accent_key], t)
    p += [
        f'  <line x1="44" y1="336" x2="296" y2="336" stroke="{t["hair"]}" stroke-width="1"/>',
        f'  <text x="44" y="358" class="mono" font-size="11" fill="{t["muted"]}">{eq_line}</text>',
    ]
    return p


def plate_ch02(t):
    p = _base("02", "Storage Node", "WRITE-AHEAD LOG", "CRC32C · CRASH RECOVERY",
              "bg_kv", "grid_kv", "blue", "WAL fsync -> MemTable -> ACK", t,
              "Chapter 2 abstract artwork: append-only sequential WAL segments with checksum seals and a torn-tail truncation line.")
    # Sequential append-only log segments + torn tail truncation
    y0 = 138
    segs = [
        (360, 104, t["blue"], t["blue_soft"], "REC 01 · CRC"),
        (476, 104, t["teal"], t["teal_soft"], "REC 02 · CRC"),
        (592, 104, t["blue"], t["blue_soft"], "REC 03 · CRC"),
        (708, 104, t["teal"], t["teal_soft"], "REC 04 · CRC"),
    ]
    for sx, sw, sc, sf, lbl in segs:
        p.append(f'  <rect x="{sx}" y="{y0}" width="{sw}" height="106" rx="8" fill="{sf}" stroke="{sc}" stroke-width="2"/>')
        p.append(f'  <rect x="{sx}" y="{y0}" width="{sw}" height="24" rx="8" fill="{sc}"/>')
        p.append(f'  <text x="{sx+sw/2:.1f}" y="{y0+16}" text-anchor="middle" class="mono" font-size="9.5" font-weight="700" fill="{t["surface"]}">{lbl}</text>')
        p.append(f'  <line x1="{sx+16}" y1="{y0+54}" x2="{sx+sw-16}" y2="{y0+54}" stroke="{sc}" stroke-width="2" opacity="0.6"/>')
        p.append(f'  <line x1="{sx+16}" y1="{y0+74}" x2="{sx+sw-34}" y2="{y0+74}" stroke="{sc}" stroke-width="2" opacity="0.4"/>')
    # Torn uncommitted tail block cut off by dashed red truncation line
    p.append(f'  <rect x="824" y="{y0}" width="84" height="106" rx="8" fill="{t["terra_soft"]}" stroke="{t["terra"]}" stroke-width="1.8" stroke-dasharray="5 4"/>')
    p.append(f'  <line x1="818" y1="96" x2="818" y2="286" stroke="{t["terra"]}" stroke-width="2.4" stroke-dasharray="7 5"/>')
    p.append(f'  <text x="866" y="{y0+58}" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["terra"]}">TORN</text>')
    p.append(f'  <text x="590" y="294" text-anchor="middle" class="mono" font-size="10.5" fill="{t["muted"]}">APPEND-ONLY DURABLE PREFIX  |  TRUNCATE ON REPLAY</text>')
    p.append("</svg>\n")
    return "\n".join(p)


def plate_ch03(t):
    p = _base("03", "Replication", "LEADER-FOLLOWER", "MAJORITY COMMIT INDEX",
              "bg_kv", "grid_kv", "teal", "commit_seq = median(match_idx)", t,
              "Chapter 3 abstract artwork: three parallel replica log tracks synchronized by a vertical majority commit watermark.")
    ys = [104, 196, 288]
    roles = [("LEADER", t["ochre"], t["ochre_soft"], 6), ("FOLLOWER A", t["blue"], t["blue_soft"], 5), ("FOLLOWER B", t["teal"], t["teal_soft"], 3)]
    for y, (lbl, sc, sf, cnt) in zip(ys, roles):
        p.append(f'  <text x="364" y="{y-10}" class="mono" font-size="10.5" font-weight="700" fill="{sc}">{lbl}</text>')
        for i in range(6):
            bx = 364 + i * 86
            filled = i < cnt
            fill = sf if filled else t["surface"]
            dash = "" if filled else ' stroke-dasharray="4 4"'
            p.append(f'  <rect x="{bx}" y="{y}" width="72" height="44" rx="7" fill="{fill}" stroke="{sc}" stroke-width="{2.0 if filled else 1.1}"{dash}/>')
            if filled:
                p.append(f'  <text x="{bx+36}" y="{y+26}" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="{sc}">#{40+i}</text>')
    # Majority commit watermark at index 5 (x=786)
    p.append(f'  <line x1="786" y1="74" x2="786" y2="354" stroke="{t["teal"]}" stroke-width="2.6"/>')
    p.append(f'  <text x="786" y="64" text-anchor="middle" class="mono" font-size="10.5" font-weight="700" fill="{t["teal"]}">COMMITTED (2 OF 3)</text>')
    p.append("</svg>\n")
    return "\n".join(p)


def plate_ch04(t):
    p = _base("04", "Leader Election", "RAFT CONSENSUS", "MONOTONIC TERM FENCING",
              "bg_kv", "grid_kv", "ochre", "term(T+1) fences stale term(T)", t,
              "Chapter 4 abstract artwork: a rising staircase of monotonic Raft terms with a fencing barrier rejecting a stale leader.")
    # Rising term blocks
    terms = [(370, 246, 110, 74, "TERM 3", t["muted"], t["surface"], True),
             (506, 186, 128, 134, "TERM 4", t["blue"], t["blue_soft"], False),
             (660, 116, 146, 204, "TERM 5", t["ochre"], t["ochre_soft"], False)]
    for x, y, w, h, lbl, sc, sf, stale in terms:
        dash = ' stroke-dasharray="5 4"' if stale else ""
        p.append(f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{sf}" stroke="{sc}" stroke-width="2"{dash}/>')
        p.append(f'  <text x="{x+w/2:.1f}" y="{y+30}" text-anchor="middle" class="mono" font-size="11.5" font-weight="700" fill="{sc}">{lbl}</text>')
    # Fencing wall between Term 4 and Term 5
    p.append(f'  <line x1="646" y1="86" x2="646" y2="342" stroke="{t["terra"]}" stroke-width="2.6" stroke-dasharray="7 5"/>')
    p.append(f'  <text x="646" y="74" text-anchor="middle" class="mono" font-size="10.5" font-weight="700" fill="{t["terra"]}">TERM FENCE</text>')
    # Majority vote ring inside Term 5
    p.append(f'  <circle cx="733" cy="226" r="42" fill="{t["surface"]}" stroke="{t["ochre"]}" stroke-width="2.4"/>')
    p.append(f'  <circle cx="733" cy="226" r="14" fill="{t["teal"]}"/>')
    p.append(f'  <text x="733" y="292" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["ochre"]}">QUORUM ELECTED</text>')
    p.append("</svg>\n")
    return "\n".join(p)


def plate_ch05(t):
    p = _base("05", "Request Router", "STATELESS ROUTING", "EPOCH CACHE · O(LOG V)",
              "bg_kv", "grid_kv", "teal", "H(key) -> shard_id -> leader", t,
              "Chapter 5 abstract artwork: stateless router nodes dispatching hashed keys through a fan-out lattice to shard leaders.")
    # Left router circles -> right shard blocks
    r_ys = [126, 200, 274]
    s_ys = [84, 158, 232, 306]
    for ry in r_ys:
        for sy in s_ys:
            p.append(f'  <line x1="454" y1="{ry}" x2="700" y2="{sy}" stroke="{t["blue"]}" stroke-width="1.3" opacity="0.35"/>')
    p.append(f'  <line x1="454" y1="200" x2="700" y2="158" stroke="{t["teal"]}" stroke-width="3.2"/>')
    for idx, ry in enumerate(r_ys):
        p.append(f'  <circle cx="430" cy="{ry}" r="24" fill="{t["teal_soft"]}" stroke="{t["teal"]}" stroke-width="2.2"/>')
        p.append(f'  <text x="430" y="{ry+4}" text-anchor="middle" class="mono" font-size="10.5" font-weight="700" fill="{t["teal"]}">R{idx+1}</text>')
    for idx, sy in enumerate(s_ys):
        col = t["ochre"] if idx == 1 else t["blue"]
        bg = t["ochre_soft"] if idx == 1 else t["blue_soft"]
        p.append(f'  <rect x="700" y="{sy-22}" width="184" height="44" rx="9" fill="{bg}" stroke="{col}" stroke-width="2"/>')
        p.append(f'  <text x="792" y="{sy+4}" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="{col}">SHARD 0{idx+1} LEADER</text>')
    p.append("</svg>\n")
    return "\n".join(p)


def plate_ch06(t):
    p = _base("06", "Group Commit", "BATCHED WAL FSYNC", "AMORTIZED DISK BARRIER",
              "bg_kv", "grid_kv", "ochre", "N writes -> 1 fsync barrier", t,
              "Chapter 6 abstract artwork: multiple concurrent write threads converging into a single batched NVMe fsync barrier.")
    # 6 incoming threads merging into 1 batch bar -> 1 NVMe ring
    for i in range(6):
        y = 86 + i * 44
        col = t["blue"] if i % 2 == 0 else t["teal"]
        p.append(f'  <path d="M 366 {y} C 470 {y} 500 198 584 198" fill="none" stroke="{col}" stroke-width="2.4" opacity="0.82"/>')
        p.append(f'  <circle cx="366" cy="{y}" r="6.5" fill="{col}"/>')
    p.append(f'  <rect x="584" y="138" width="108" height="120" rx="12" fill="{t["ochre_soft"]}" stroke="{t["ochre"]}" stroke-width="2.4"/>')
    p.append(f'  <text x="638" y="192" text-anchor="middle" class="mono" font-size="12" font-weight="700" fill="{t["ochre"]}">BATCH</text>')
    p.append(f'  <text x="638" y="212" text-anchor="middle" class="mono" font-size="10" fill="{t["muted"]}">1 fsync()</text>')
    p.append(f'  <line x1="692" y1="198" x2="758" y2="198" stroke="{t["ochre"]}" stroke-width="3.2"/>')
    p.append(f'  <circle cx="826" cy="198" r="68" fill="{t["teal_soft"]}" stroke="{t["teal"]}" stroke-width="2.4"/>')
    p.append(f'  <circle cx="826" cy="198" r="34" fill="{t["surface"]}" stroke="{t["teal"]}" stroke-width="1.8"/>')
    p.append(f'  <text x="826" y="202" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="{t["teal"]}">NVMe</text>')
    p.append("</svg>\n")
    return "\n".join(p)


def plate_ch08(t):
    p = _base("08", "Unique ID Generator", "SNOWFLAKE 64-BIT", "TIME · NODE · SEQUENCE",
              "bg_rl", "grid_rl", "blue", "1b | 41b ts | 10b node | 12b seq", t,
              "Chapter 8 abstract artwork: a 64-bit Snowflake identifier segmented proportionally into sign, 41-bit timestamp, 10-bit worker, and 12-bit sequence fields.")
    # Exact proportional 64-bit layout bar (width = 544 -> 8.5px per bit)
    x0, y0, bh = 360, 148, 86
    fields = [
        (1, "0", t["muted"], t["surface"], "1b"),
        (41, "41-BIT TIMESTAMP (ms)", t["blue"], t["blue_soft"], "69 yr"),
        (10, "NODE", t["teal"], t["teal_soft"], "1024"),
        (12, "SEQ", t["ochre"], t["ochre_soft"], "4096/ms"),
    ]
    cx = x0
    for bits, lbl, sc, sf, sub in fields:
        w = bits * 8.4
        p.append(f'  <rect x="{cx:.1f}" y="{y0}" width="{w - 4:.1f}" height="{bh}" rx="8" fill="{sf}" stroke="{sc}" stroke-width="2"/>')
        if bits >= 10:
            p.append(f'  <text x="{cx + (w-4)/2:.1f}" y="{y0 + 38}" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="{sc}">{lbl}</text>')
            p.append(f'  <text x="{cx + (w-4)/2:.1f}" y="{y0 + 58}" text-anchor="middle" class="mono" font-size="10" fill="{t["muted"]}">{sub}</text>')
        cx += w
    # Monotonic rising step markers below
    for k in range(8):
        rx = 374 + k * 66
        ry = 286 - k * 5
        p.append(f'  <rect x="{rx}" y="{ry}" width="44" height="{308 - ry}" rx="4" fill="{t["teal"] if k % 2 else t["blue"]}" opacity="0.75"/>')
    p.append(f'  <text x="632" y="346" text-anchor="middle" class="mono" font-size="10.5" fill="{t["muted"]}">K-SORTED · ZERO CENTRAL COORDINATION · 4.09M ID/s/NODE</text>')
    p.append("</svg>\n")
    return "\n".join(p)


def plate_ch09(t):
    p = _base("09", "Distributed Cache", "MEMORY HIERARCHY", "W-TINYLFU · SINGLEFLIGHT",
              "bg_rl", "grid_rl", "teal", "Hit Ratio -> p99 < 1 ms", t,
              "Chapter 9 abstract artwork: nested logarithmic memory hierarchy frames from L1 RAM cache down to persistent disk storage.")
    # Nested concentric rounded memory tiers
    tiers = [
        (366, 66, 536, 268, t["blue_soft"], t["blue"], "BACKING DATABASE (10-50 ms)"),
        (414, 114, 440, 198, t["teal_soft"], t["teal"], "DISTRIBUTED CACHE FLEET (0.5-1 ms)"),
        (466, 166, 336, 122, t["ochre_soft"], t["ochre"], "L1 HOT-KEY NEAR CACHE (10 us)"),
    ]
    for x, y, w, h, sf, sc, lbl in tiers:
        p.append(f'  <rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{sf}" stroke="{sc}" stroke-width="2"/>')
        p.append(f'  <text x="{x + 18}" y="{y + 28}" class="mono" font-size="11" font-weight="700" fill="{sc}">{lbl}</text>')
    # Singleflight coalescing dot inside L1
    p.append(f'  <circle cx="634" cy="242" r="22" fill="{t["surface"]}" stroke="{t["teal"]}" stroke-width="2.4"/>')
    p.append(f'  <circle cx="634" cy="242" r="7" fill="{t["terra"]}"/>')
    p.append("</svg>\n")
    return "\n".join(p)


def plate_ch10(t):
    p = _base("10", "Distributed Lock", "LEASES & FENCING", "MONOTONIC TOKEN BARRIER",
              "bg_pay", "grid_pay", "terra", "Reject write if token < max_seen", t,
              "Chapter 10 abstract artwork: two monotonic fencing tokens approaching a storage gate, where the newer token passes and the stale paused token is blocked.")
    # Fencing barrier wall at x=694
    p.append(f'  <rect x="694" y="72" width="14" height="256" rx="7" fill="{t["blue"]}"/>')
    p.append(f'  <text x="701" y="58" text-anchor="middle" class="mono" font-size="10.5" font-weight="700" fill="{t["blue"]}">STORAGE FENCE</text>')
    # Token 34 (valid -> passes through to storage)
    p.append(f'  <rect x="378" y="114" width="144" height="58" rx="10" fill="{t["teal_soft"]}" stroke="{t["teal"]}" stroke-width="2.2"/>')
    p.append(f'  <text x="450" y="148" text-anchor="middle" class="mono" font-size="13" font-weight="700" fill="{t["teal"]}">TOKEN #34</text>')
    p.append(f'  <line x1="522" y1="143" x2="854" y2="143" stroke="{t["teal"]}" stroke-width="2.8"/>')
    p.append(f'  <circle cx="860" cy="143" r="14" fill="{t["teal"]}"/>')
    # Token 33 (GC paused -> blocked at fence)
    p.append(f'  <rect x="378" y="230" width="144" height="58" rx="10" fill="{t["terra_soft"]}" stroke="{t["terra"]}" stroke-width="2.2" stroke-dasharray="5 4"/>')
    p.append(f'  <text x="450" y="264" text-anchor="middle" class="mono" font-size="13" font-weight="700" fill="{t["terra"]}">TOKEN #33</text>')
    p.append(f'  <line x1="522" y1="259" x2="684" y2="259" stroke="{t["terra"]}" stroke-width="2.2" stroke-dasharray="6 4"/>')
    p.append(f'  <text x="802" y="264" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="{t["terra"]}">REJECTED (33 &lt; 34)</text>')
    p.append("</svg>\n")
    return "\n".join(p)


def plate_ch11(t):
    p = _base("11", "Message Queue", "PARTITIONED LOG", "CONSUMER GROUP OFFSETS",
              "bg_kv", "grid_kv", "blue", "offset_k -> at-least-once replay", t,
              "Chapter 11 abstract artwork: three parallel append-only log partitions with independent color-coded consumer group offset cursors.")
    for row, (lbl, col, bg, cur_a, cur_b) in enumerate([
        ("PART 0", t["blue"], t["blue_soft"], 5, 3),
        ("PART 1", t["teal"], t["teal_soft"], 4, 2),
        ("PART 2", t["indigo"], t["indigo_soft"], 6, 4),
    ]):
        y = 104 + row * 86
        p.append(f'  <text x="364" y="{y-8}" class="mono" font-size="10" font-weight="700" fill="{col}">{lbl}</text>')
        for i in range(7):
            bx = 364 + i * 74
            p.append(f'  <rect x="{bx}" y="{y}" width="64" height="44" rx="6" fill="{bg}" stroke="{col}" stroke-width="1.6"/>')
            p.append(f'  <text x="{bx+32}" y="{y+26}" text-anchor="middle" class="mono" font-size="10.5" fill="{col}">{i}</text>')
        # Cursor triangles for Group A (ochre) and Group B (terra)
        ax = 364 + cur_a * 74 + 32
        bx2 = 364 + cur_b * 74 + 32
        p.append(f'  <polygon points="{ax},{y-2} {ax-7},{y-13} {ax+7},{y-13}" fill="{t["ochre"]}"/>')
        p.append(f'  <polygon points="{bx2},{y+46} {bx2-7},{y+57} {bx2+7},{y+57}" fill="{t["terra"]}"/>')
    p.append("</svg>\n")
    return "\n".join(p)


def plate_ch12(t):
    p = _base("12", "Job Scheduler", "DELAYED EXECUTION", "TIME WHEEL · WORKER LEASES",
              "bg_rl", "grid_rl", "ochre", "claim(lease) -> heartbeat -> done", t,
              "Chapter 12 abstract artwork: a circular hashed timing wheel dispatching scheduled tasks into parallel worker lanes.")
    cx, cy = 516, 200
    p.append(f'  <circle cx="{cx}" cy="{cy}" r="118" fill="{t["ochre_soft"]}" stroke="{t["ochre"]}" stroke-width="2.4"/>')
    p.append(f'  <circle cx="{cx}" cy="{cy}" r="54" fill="{t["surface"]}" stroke="{t["teal"]}" stroke-width="2"/>')
    for k in range(12):
        ang = math.radians(k * 30)
        x0, y0 = cx + 54 * math.cos(ang), cy + 54 * math.sin(ang)
        x1, y1 = cx + 118 * math.cos(ang), cy + 118 * math.sin(ang)
        p.append(f'  <line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="{t["ochre"]}" stroke-width="1.4" opacity="0.7"/>')
    # Active radial hand pointing right into worker lanes
    p.append(f'  <line x1="{cx}" y1="{cy}" x2="{cx+116}" y2="{cy}" stroke="{t["terra"]}" stroke-width="3"/>')
    p.append(f'  <circle cx="{cx}" cy="{cy}" r="9" fill="{t["terra"]}"/>')
    for idx, (wy, lbl, col, bg) in enumerate([
        (114, "WORKER 01 · LEASE OK", t["teal"], t["teal_soft"]),
        (200, "WORKER 02 · EXEC", t["blue"], t["blue_soft"]),
        (286, "DLQ · RETRY EXHAUST", t["terra"], t["terra_soft"]),
    ]):
        p.append(f'  <line x1="634" y1="200" x2="704" y2="{wy}" stroke="{col}" stroke-width="2"/>')
        p.append(f'  <rect x="704" y="{wy-24}" width="194" height="48" rx="9" fill="{bg}" stroke="{col}" stroke-width="1.8"/>')
        p.append(f'  <text x="801" y="{wy+4}" text-anchor="middle" class="mono" font-size="10.5" font-weight="700" fill="{col}">{lbl}</text>')
    p.append("</svg>\n")
    return "\n".join(p)


def plate_ch13(t):
    p = _base("13", "Notification Service", "MULTI-CHANNEL FANOUT", "BACKOFF · CIRCUIT BREAKERS",
              "bg_rl", "grid_rl", "indigo", "P0 OTP -> isolated from P3 Promo", t,
              "Chapter 13 abstract artwork: priority-isolated notification channels fanning out with exponential retry spacing.")
    # Source hub -> 4 isolated channel pipes with exponential tick marks
    hx, hy = 414, 200
    p.append(f'  <circle cx="{hx}" cy="{hy}" r="36" fill="{t["indigo_soft"]}" stroke="{t["indigo"]}" stroke-width="2.4"/>')
    p.append(f'  <text x="{hx}" y="{hy+4}" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="{t["indigo"]}">HUB</text>')
    chans = [
        (92, "APNs / FCM", t["blue"], t["blue_soft"]),
        (164, "SMS · P0", t["teal"], t["teal_soft"]),
        (236, "EMAIL · P2", t["ochre"], t["ochre_soft"]),
        (308, "WEBHOOK", t["terra"], t["terra_soft"]),
    ]
    for cy0, lbl, sc, sf in chans:
        p.append(f'  <path d="M {hx+36} {hy} C 520 {hy} 530 {cy0} 600 {cy0}" fill="none" stroke="{sc}" stroke-width="2.2"/>')
        p.append(f'  <rect x="600" y="{cy0-20}" width="144" height="40" rx="8" fill="{sf}" stroke="{sc}" stroke-width="1.8"/>')
        p.append(f'  <text x="672" y="{cy0+4}" text-anchor="middle" class="mono" font-size="10.5" font-weight="700" fill="{sc}">{lbl}</text>')
        # Exponential backoff pulses on right (1, 2, 4, 8)
        for step in (12, 34, 72, 130):
            p.append(f'  <circle cx="{752+step}" cy="{cy0}" r="5.5" fill="{sc}" opacity="0.82"/>')
    p.append("</svg>\n")
    return "\n".join(p)


def plate_ch14(t):
    p = _base("14", "URL Shortener", "BASE-62 BIJECTION", "301/302 EDGE REDIRECTS",
              "bg_kv", "grid_kv", "blue", "62^7 = 3.52 trillion codes", t,
              "Chapter 14 abstract artwork: a long URL vector compressed through a geometric funnel into 7 Base-62 character cells.")
    # Wide long-URL bar compressing into 7 compact Base-62 tiles
    p.append(f'  <rect x="364" y="96" width="536" height="48" rx="9" fill="{t["blue_soft"]}" stroke="{t["blue"]}" stroke-width="1.8"/>')
    p.append(f'  <text x="632" y="125" text-anchor="middle" class="mono" font-size="12" fill="{t["blue"]}">https://example.org/docs/systems/design?ref=2026&amp;id=9812</text>')
    # Geometric compression trapezoid
    p.append(f'  <polygon points="396,144 868,144 748,224 516,224" fill="{t["teal_soft"]}" fill-opacity="0.65" stroke="{t["teal"]}" stroke-width="1.6"/>')
    p.append(f'  <text x="632" y="192" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="{t["teal"]}">BASE-62 ENCODE (64-BIT ID)</text>')
    chars = list("a9K4x7Q")
    for i, ch in enumerate(chars):
        bx = 446 + i * 54
        p.append(f'  <rect x="{bx}" y="242" width="44" height="54" rx="8" fill="{t["surface"]}" stroke="{t["blue"]}" stroke-width="2.2"/>')
        p.append(f'  <text x="{bx+22}" y="276" text-anchor="middle" class="mono" font-size="18" font-weight="700" fill="{t["blue"]}">{ch}</text>')
    p.append("</svg>\n")
    return "\n".join(p)


def plate_ch15(t):
    p = _base("15", "News Feed", "HYBRID FAN-OUT", "PUSH INBOX · CELEBRITY PULL",
              "bg_kv", "grid_kv", "teal", "Fan-out-on-Write + Pull Merge", t,
              "Chapter 15 abstract artwork: bifurcated graph comparing write-time fan-out mesh with read-time pull merge for high-degree hubs.")
    # Top: Fan-out-on-Write (1 author -> 5 follower caches)
    p.append(f'  <circle cx="412" cy="126" r="26" fill="{t["teal_soft"]}" stroke="{t["teal"]}" stroke-width="2.2"/>')
    p.append(f'  <text x="412" y="130" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["teal"]}">USER</text>')
    for i in range(4):
        fy = 76 + i * 34
        p.append(f'  <line x1="438" y1="126" x2="564" y2="{fy}" stroke="{t["teal"]}" stroke-width="1.8"/>')
        p.append(f'  <rect x="564" y="{fy-11}" width="110" height="22" rx="6" fill="{t["teal_soft"]}" stroke="{t["teal"]}" stroke-width="1.4"/>')
    # Bottom: Celebrity Pull Hub -> Merge-on-Read
    p.append(f'  <circle cx="412" cy="284" r="34" fill="{t["ochre_soft"]}" stroke="{t["ochre"]}" stroke-width="2.4"/>')
    p.append(f'  <text x="412" y="288" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["ochre"]}">10M+</text>')
    p.append(f'  <line x1="446" y1="284" x2="732" y2="206" stroke="{t["ochre"]}" stroke-width="2.2" stroke-dasharray="6 4"/>')
    p.append(f'  <line x1="674" y1="126" x2="732" y2="206" stroke="{t["teal"]}" stroke-width="2.2"/>')
    p.append(f'  <rect x="732" y="160" width="166" height="92" rx="12" fill="{t["blue_soft"]}" stroke="{t["blue"]}" stroke-width="2.2"/>')
    p.append(f'  <text x="815" y="200" text-anchor="middle" class="mono" font-size="11.5" font-weight="700" fill="{t["blue"]}">K-WAY MERGE</text>')
    p.append(f'  <text x="815" y="220" text-anchor="middle" class="mono" font-size="10" fill="{t["muted"]}">RANKED FEED</text>')
    p.append("</svg>\n")
    return "\n".join(p)


def plate_ch16(t):
    p = _base("16", "Object Store", "ERASURE CODING", "REED-SOLOMON · SCRUBBING",
              "bg_pay", "grid_pay", "blue", "RS(6, 3): 1.5x overhead, f=3", t,
              "Chapter 16 abstract artwork: a 6+3 Reed-Solomon erasure-coded object stripe showing reconstruction of a missing shard.")
    # 6 Data stripes (blue) + 3 Parity stripes (ochre), with D3 missing (terra dashed)
    for i in range(9):
        bx = 364 + i * 60
        is_parity = i >= 6
        missing = i == 2
        if missing:
            sc, sf, lbl = t["terra"], t["terra_soft"], "LOST"
            dash = ' stroke-dasharray="5 4"'
        elif is_parity:
            sc, sf, lbl = t["ochre"], t["ochre_soft"], f"P{i-5}"
            dash = ""
        else:
            sc, sf, lbl = t["blue"], t["blue_soft"], f"D{i+1}"
            dash = ""
        p.append(f'  <rect x="{bx}" y="110" width="48" height="162" rx="8" fill="{sf}" stroke="{sc}" stroke-width="2"{dash}/>')
        p.append(f'  <text x="{bx+24}" y="196" text-anchor="middle" class="mono" font-size="12" font-weight="700" fill="{sc}">{lbl}</text>')
    # Reconstruction arc from P1 back to LOST D3
    p.append(f'  <path d="M 748 272 Q 620 356 508 276" fill="none" stroke="{t["teal"]}" stroke-width="2.4"/>')
    p.append(f'  <text x="632" y="346" text-anchor="middle" class="mono" font-size="10.5" font-weight="700" fill="{t["teal"]}">ANY 6 OF 9 RECONSTRUCT OBJECT</text>')
    p.append("</svg>\n")
    return "\n".join(p)


def plate_ch17(t):
    p = _base("17", "Video Streaming", "ADAPTIVE BITRATE", "HLS / DASH · CDN EDGE",
              "bg_kv", "grid_kv", "indigo", "4s GOP segments · ABR ladder", t,
              "Chapter 17 abstract artwork: a multi-rung adaptive bitrate ladder switching dynamically across 4-second media segments.")
    rungs = [(92, "4K · 15 Mbps", t["indigo"]), (156, "1080p · 5 Mbps", t["blue"]), (220, "720p · 2.5 Mbps", t["teal"]), (284, "480p · 1 Mbps", t["ochre"])]
    chosen = [1, 1, 2, 3, 2, 1, 0]
    for r_idx, (ry, lbl, col) in enumerate(rungs):
        p.append(f'  <text x="364" y="{ry+4}" class="mono" font-size="10" font-weight="700" fill="{col}">{lbl}</text>')
        for seg in range(7):
            sx = 492 + seg * 58
            active = chosen[seg] == r_idx
            p.append(f'  <rect x="{sx}" y="{ry-16}" width="46" height="32" rx="6" fill="{col if active else t["surface"]}" fill-opacity="{0.88 if active else 0.7}" stroke="{col}" stroke-width="{2.2 if active else 1.1}"/>')
    # Path connecting chosen segments
    pts = " ".join(f"{492 + seg*58 + 23},{rungs[chosen[seg]][0]}" for seg in range(7))
    p.append(f'  <polyline points="{pts}" fill="none" stroke="{t["terra"]}" stroke-width="2.4"/>')
    p.append("</svg>\n")
    return "\n".join(p)


def plate_ch18(t):
    p = _base("18", "Real-Time Chat", "PERSISTENT SOCKETS", "PER-CHANNEL SEQUENCE LOG",
              "bg_rl", "grid_rl", "teal", "seq_id monotonic per channel", t,
              "Chapter 18 abstract artwork: bidirectional WebSocket edge nodes routing ordered message envelopes through a channel sequence bus.")
    # Left & Right gateway clusters linked through ordered central sequence bar
    for i, gy in enumerate([114, 200, 286]):
        p.append(f'  <circle cx="406" cy="{gy}" r="24" fill="{t["blue_soft"]}" stroke="{t["blue"]}" stroke-width="2"/>')
        p.append(f'  <line x1="430" y1="{gy}" x2="520" y2="200" stroke="{t["blue"]}" stroke-width="1.8"/>')
        p.append(f'  <circle cx="862" cy="{gy}" r="24" fill="{t["teal_soft"]}" stroke="{t["teal"]}" stroke-width="2"/>')
        p.append(f'  <line x1="748" y1="200" x2="838" y2="{gy}" stroke="{t["teal"]}" stroke-width="1.8"/>')
    p.append(f'  <rect x="520" y="154" width="228" height="92" rx="12" fill="{t["surface"]}" stroke="{t["teal"]}" stroke-width="2.2"/>')
    for k in range(4):
        bx = 538 + k * 50
        p.append(f'  <rect x="{bx}" y="176" width="40" height="48" rx="6" fill="{t["teal_soft"]}" stroke="{t["teal"]}" stroke-width="1.6"/>')
        p.append(f'  <text x="{bx+20}" y="205" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="{t["teal"]}">#{k+1}</text>')
    p.append(f'  <text x="634" y="280" text-anchor="middle" class="mono" font-size="10.5" fill="{t["muted"]}">WEBSOCKET PUSH + OFFLINE SYNC CURSOR</text>')
    p.append("</svg>\n")
    return "\n".join(p)


def plate_ch20(t):
    p = _base("20", "Ticket Booking", "INVENTORY HOLDS", "VIRTUAL QUEUE · CAS LOCKS",
              "bg_pay", "grid_pay", "ochre", "AVAILABLE -> HELD(TTL) -> SOLD", t,
              "Chapter 20 abstract artwork: an architectural stadium seat grid with available, lease-held, and sold cells gated by a virtual waiting room.")
    # 7x4 seat matrix showing Available (teal), Held with TTL (ochre), Sold (blue), Contended (terra)
    states = [
        [2, 2, 2, 1, 0, 0, 0],
        [2, 2, 1, 3, 1, 0, 0],
        [2, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
    ]
    pal = {0: (t["teal"], t["teal_soft"]), 1: (t["ochre"], t["ochre_soft"]), 2: (t["blue"], t["blue_soft"]), 3: (t["terra"], t["terra_soft"])}
    for r in range(4):
        for c in range(7):
            sc, sf = pal[states[r][c]]
            sx = 416 + c * 68
            sy = 96 + r * 58
            p.append(f'  <rect x="{sx}" y="{sy}" width="54" height="44" rx="8" fill="{sf}" stroke="{sc}" stroke-width="2"/>')
    p.append(f'  <text x="648" y="352" text-anchor="middle" class="mono" font-size="10.5" fill="{t["muted"]}">SOLD (BLUE)  ·  TTL HOLD (GOLD)  ·  AVAILABLE (TEAL)</text>')
    p.append("</svg>\n")
    return "\n".join(p)


def plate_ch21(t):
    p = _base("21", "Ride Hailing", "SPATIAL INDEXING", "H3 HEXAGONS · DISPATCH",
              "bg_rl", "grid_rl", "teal", "k-ring H3 lookup -> bipartite match", t,
              "Chapter 21 abstract artwork: a hexagonal H3 spatial grid radiating outward from a rider origin to nearby driver coordinates.")
    def hex_pts(cx0, cy0, rad):
        return " ".join(f"{cx0 + rad*math.cos(math.radians(60*k)):.1f},{cy0 + rad*math.sin(math.radians(60*k)):.1f}" for k in range(6))
    cx, cy, r = 634, 200, 44
    dx, dy = r * 1.5, r * math.sqrt(3)
    cells = [
        (0, 0, t["terra"], t["terra_soft"]),
        (1, -0.5, t["teal"], t["teal_soft"]), (1, 0.5, t["teal"], t["teal_soft"]),
        (-1, -0.5, t["teal"], t["teal_soft"]), (-1, 0.5, t["teal"], t["teal_soft"]),
        (0, -1, t["teal"], t["teal_soft"]), (0, 1, t["teal"], t["teal_soft"]),
        (2, 0, t["blue"], t["blue_soft"]), (-2, 0, t["blue"], t["blue_soft"]),
        (2, -1, t["blue"], t["blue_soft"]), (2, 1, t["blue"], t["blue_soft"]),
        (-2, -1, t["blue"], t["blue_soft"]), (-2, 1, t["blue"], t["blue_soft"]),
    ]
    for gx, gy, sc, sf in cells:
        hx, hy = cx + gx * dx, cy + gy * dy
        p.append(f'  <polygon points="{hex_pts(hx, hy, r - 3)}" fill="{sf}" stroke="{sc}" stroke-width="1.8"/>')
    p.append(f'  <circle cx="{cx}" cy="{cy}" r="9" fill="{t["terra"]}"/>')
    for dpos in [(cx + dx, cy - 0.5*dy), (cx - dx, cy + 0.5*dy), (cx + 2*dx, cy)]:
        p.append(f'  <circle cx="{dpos[0]:.1f}" cy="{dpos[1]:.1f}" r="7" fill="{t["blue"]}"/>')
    p.append("</svg>\n")
    return "\n".join(p)


def plate_ch22(t):
    p = _base("22", "Search Autocomplete", "PREFIX TRIE", "TOP-K CACHE · EDGE SERVING",
              "bg_kv", "grid_kv", "indigo", "O(|prefix|) -> precomputed top-K", t,
              "Chapter 22 abstract artwork: a branching geometric prefix trie highlighting the active hot prefix path and precomputed top-K leaf weights.")
    # Tree nodes (x, y, lbl, active)
    nodes = [
        (634, 86, "root", True),
        (514, 174, "s", False), (634, 174, "k", True), (754, 174, "r", False),
        (464, 266, "sq", False), (564, 266, "ka", True), (694, 266, "kv", True), (814, 266, "ra", False),
    ]
    edges = [(0, 1, False), (0, 2, True), (0, 3, False), (1, 4, False), (2, 5, True), (2, 6, True), (3, 7, False)]
    for a, b, act in edges:
        p.append(f'  <line x1="{nodes[a][0]}" y1="{nodes[a][1]}" x2="{nodes[b][0]}" y2="{nodes[b][1]}" stroke="{t["indigo"] if act else t["hair"]}" stroke-width="{2.6 if act else 1.5}"/>')
    for x, y, lbl, act in nodes:
        sc = t["indigo"] if act else t["muted"]
        sf = t["indigo_soft"] if act else t["surface"]
        p.append(f'  <circle cx="{x}" cy="{y}" r="24" fill="{sf}" stroke="{sc}" stroke-width="2"/>')
        p.append(f'  <text x="{x}" y="{y+4}" text-anchor="middle" class="mono" font-size="11.5" font-weight="700" fill="{sc}">{lbl}</text>')
    p.append(f'  <text x="634" y="340" text-anchor="middle" class="mono" font-size="10.5" fill="{t["muted"]}">TOP-K SNAPSHOT AT EVERY PREFIX NODE  ·  p99 &lt; 20 ms</text>')
    p.append("</svg>\n")
    return "\n".join(p)


def plate_ch23(t):
    p = _base("23", "Web Crawler", "POLITE FRONTIER", "PER-HOST QUEUES · BLOOM FILTER",
              "bg_kv", "grid_kv", "teal", "Frontier -> Fetch -> Dedup -> Parse", t,
              "Chapter 23 abstract artwork: a circular crawl-loop pipeline passing through politeness host queues and a Bloom-filter deduplication sieve.")
    cx, cy = 634, 200
    p.append(f'  <circle cx="{cx}" cy="{cy}" r="112" fill="none" stroke="{t["teal"]}" stroke-width="2.4" stroke-dasharray="8 5"/>')
    stages = [
        (cx, cy - 112, "FRONTIER", t["blue"], t["blue_soft"]),
        (cx + 150, cy, "FETCHER", t["teal"], t["teal_soft"]),
        (cx, cy + 112, "PARSER", t["ochre"], t["ochre_soft"]),
        (cx - 150, cy, "BLOOM DEDUP", t["indigo"], t["indigo_soft"]),
    ]
    for sx, sy, lbl, sc, sf in stages:
        p.append(f'  <rect x="{sx-66}" y="{sy-24}" width="132" height="48" rx="10" fill="{sf}" stroke="{sc}" stroke-width="2"/>')
        p.append(f'  <text x="{sx}" y="{sy+4}" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="{sc}">{lbl}</text>')
    p.append("</svg>\n")
    return "\n".join(p)


def plate_ch24(t):
    p = _base("24", "Metrics & Monitoring", "TIME-SERIES ENGINE", "GORILLA DELTA · ROLLUPS",
              "bg_rl", "grid_rl", "blue", "delta-of-delta + XOR float", t,
              "Chapter 24 abstract artwork: a crisp time-series signal waveform compressed into discrete downsampled retention rollups.")
    # Continuous raw series -> downsampled bar buckets
    pts = " ".join(f"{370 + i*12},{180 - 52*math.sin(i*0.42) - 18*math.cos(i*1.1):.1f}" for i in range(44))
    p.append(f'  <polyline points="{pts}" fill="none" stroke="{t["blue"]}" stroke-width="2.4"/>')
    for k in range(10):
        bx = 376 + k * 52
        bh = 36 + (k * 17) % 58
        p.append(f'  <rect x="{bx}" y="{320 - bh}" width="36" height="{bh}" rx="5" fill="{t["teal_soft"]}" stroke="{t["teal"]}" stroke-width="1.6"/>')
    p.append(f'  <line x1="364" y1="320" x2="896" y2="320" stroke="{t["ink"]}" stroke-width="1.4" opacity="0.4"/>')
    p.append("</svg>\n")
    return "\n".join(p)


def plate_ch25(t):
    p = _base("25", "File Synchronization", "DELTA CHUNKING", "CONTENT-ADDRESSED MERKLE",
              "bg_pay", "grid_pay", "teal", "Only mutated chunks cross WAN", t,
              "Chapter 25 abstract artwork: two mirrored device chunk trees linked by a single changed content-addressed block transfer.")
    # Left & Right 4-chunk stacks; only chunk 2 differs (ochre -> teal sync arrow)
    for side, sx, lbl in [(0, 412, "DEVICE A"), (1, 744, "DEVICE B")]:
        p.append(f'  <text x="{sx+62}" y="82" text-anchor="middle" class="mono" font-size="11" font-weight="700" fill="{t["muted"]}">{lbl}</text>')
        for k in range(4):
            cy0 = 100 + k * 58
            changed = k == 2
            sc = t["ochre"] if changed else t["blue"]
            sf = t["ochre_soft"] if changed else t["blue_soft"]
            p.append(f'  <rect x="{sx}" y="{cy0}" width="124" height="44" rx="8" fill="{sf}" stroke="{sc}" stroke-width="2"/>')
            p.append(f'  <text x="{sx+62}" y="{cy0+26}" text-anchor="middle" class="mono" font-size="10.5" font-weight="700" fill="{sc}">{"DELTA #3" if changed else f"SHA #{k+1}"}</text>')
    p.append(f'  <line x1="536" y1="238" x2="744" y2="238" stroke="{t["ochre"]}" stroke-width="3"/>')
    p.append(f'  <text x="640" y="226" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["ochre"]}">SYNC 1 CHUNK</text>')
    p.append("</svg>\n")
    return "\n".join(p)


def plate_ch26(t):
    p = _base("26", "Collaborative Editing", "CONVERGENT CRDT", "CAUSAL ORDER · SEC MERGE",
              "bg_kv", "grid_kv", "indigo", "A ⊔ B = B ⊔ A  (commutativity)", t,
              "Chapter 26 abstract artwork: a causal diamond DAG splitting concurrent edits into two branches and merging deterministically into one converged state.")
    # Causal diamond DAG
    pts = [(412, 200, "S0", t["blue"], t["blue_soft"]),
           (606, 108, "OP_A", t["teal"], t["teal_soft"]),
           (606, 292, "OP_B", t["ochre"], t["ochre_soft"]),
           (800, 200, "A ⊔ B", t["indigo"], t["indigo_soft"])]
    for a, b, col in [(0, 1, t["teal"]), (0, 2, t["ochre"]), (1, 3, t["teal"]), (2, 3, t["ochre"])]:
        p.append(f'  <line x1="{pts[a][0]}" y1="{pts[a][1]}" x2="{pts[b][0]}" y2="{pts[b][1]}" stroke="{col}" stroke-width="2.6"/>')
    for x, y, lbl, sc, sf in pts:
        p.append(f'  <circle cx="{x}" cy="{y}" r="34" fill="{sf}" stroke="{sc}" stroke-width="2.4"/>')
        p.append(f'  <text x="{x}" y="{y+5}" text-anchor="middle" class="mono" font-size="12" font-weight="700" fill="{sc}">{lbl}</text>')
    p.append("</svg>\n")
    return "\n".join(p)


def plate_ch27(t):
    p = _base("27", "Stock Exchange", "MATCHING ENGINE", "PRICE-TIME PRIORITY · LMAX",
              "bg_pay", "grid_pay", "ochre", "Single-thread deterministic ring", t,
              "Chapter 27 abstract artwork: opposing bid and ask limit-order-book depth stairs converging at the market spread.")
    # Left Bid Depth Stairs (teal) vs Right Ask Depth Stairs (terra) meeting at x=634
    for i in range(5):
        bw = 44 + i * 38
        y = 104 + i * 44
        p.append(f'  <rect x="{624 - bw}" y="{y}" width="{bw}" height="32" rx="5" fill="{t["teal_soft"]}" stroke="{t["teal"]}" stroke-width="1.8"/>')
        p.append(f'  <rect x="644" y="{y}" width="{bw}" height="32" rx="5" fill="{t["terra_soft"]}" stroke="{t["terra"]}" stroke-width="1.8"/>')
    p.append(f'  <line x1="634" y1="74" x2="634" y2="334" stroke="{t["ochre"]}" stroke-width="2.4" stroke-dasharray="6 4"/>')
    p.append(f'  <text x="634" y="64" text-anchor="middle" class="mono" font-size="10.5" font-weight="700" fill="{t["ochre"]}">MID SPREAD · FILL</text>')
    p.append("</svg>\n")
    return "\n".join(p)


def plate_ch28(t):
    p = _base("28", "Click Aggregation", "STREAMING WINDOWS", "EVENT-TIME WATERMARKS",
              "bg_rl", "grid_rl", "blue", "Event time + watermark + late side", t,
              "Chapter 28 abstract artwork: tumbling event-time aggregation windows swept by a watermark bar with late-arriving events routed to a reconciliation track.")
    # 3 Tumbling windows + advancing watermark + late event arc
    for i in range(3):
        wx = 380 + i * 168
        col = t["blue"] if i < 2 else t["teal"]
        bg = t["blue_soft"] if i < 2 else t["teal_soft"]
        p.append(f'  <rect x="{wx}" y="114" width="148" height="128" rx="10" fill="{bg}" stroke="{col}" stroke-width="2"/>')
        p.append(f'  <text x="{wx+74}" y="142" text-anchor="middle" class="mono" font-size="10.5" font-weight="700" fill="{col}">WINDOW T+{i}</text>')
        for d in range(5):
            p.append(f'  <circle cx="{wx + 24 + d*24}" cy="{174 + ((d*19)%38)}" r="5.5" fill="{col}"/>')
    # Watermark bar
    p.append(f'  <line x1="706" y1="78" x2="706" y2="316" stroke="{t["ochre"]}" stroke-width="2.6"/>')
    p.append(f'  <text x="706" y="68" text-anchor="middle" class="mono" font-size="10.5" font-weight="700" fill="{t["ochre"]}">WATERMARK</text>')
    # Late arrival side output
    p.append(f'  <path d="M 764 294 Q 610 330 462 248" fill="none" stroke="{t["terra"]}" stroke-width="2.2" stroke-dasharray="5 4"/>')
    p.append(f'  <circle cx="764" cy="294" r="7" fill="{t["terra"]}"/>')
    p.append(f'  <text x="832" y="298" text-anchor="middle" class="mono" font-size="10" font-weight="700" fill="{t["terra"]}">LATE EVENT</text>')
    p.append("</svg>\n")
    return "\n".join(p)


EXTRA_PLATES = {
    "ch02-plate.svg": plate_ch02, "ch03-plate.svg": plate_ch03, "ch04-plate.svg": plate_ch04,
    "ch05-plate.svg": plate_ch05, "ch06-plate.svg": plate_ch06, "ch08-plate.svg": plate_ch08,
    "ch09-plate.svg": plate_ch09, "ch10-plate.svg": plate_ch10, "ch11-plate.svg": plate_ch11,
    "ch12-plate.svg": plate_ch12, "ch13-plate.svg": plate_ch13, "ch14-plate.svg": plate_ch14,
    "ch15-plate.svg": plate_ch15, "ch16-plate.svg": plate_ch16, "ch17-plate.svg": plate_ch17,
    "ch18-plate.svg": plate_ch18, "ch20-plate.svg": plate_ch20, "ch21-plate.svg": plate_ch21,
    "ch22-plate.svg": plate_ch22, "ch23-plate.svg": plate_ch23, "ch24-plate.svg": plate_ch24,
    "ch25-plate.svg": plate_ch25, "ch26-plate.svg": plate_ch26, "ch27-plate.svg": plate_ch27,
    "ch28-plate.svg": plate_ch28,
}
