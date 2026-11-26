#!/usr/bin/env python3
"""Export the compiled mdBook to a publication-grade technical monograph PDF.

Features:
  1. Cover page (unnumbered)
  2. Title & Copyright / Colophon page (unnumbered)
  3. Printed Table of Contents with dotted leaders and exact page numbers (Roman numerals)
  4. Preface (Roman numerals, running header)
  5. Chapters 1..28 (Arabic numerals starting at 1, chapter running headers suppressed on
     each chapter's opening page via `@page :first`, compact natural pagination)
  6. Two-column Alphabetical Subject Index with exact verified page numbers extracted
     directly from the rendered chapter PDFs via Ghostscript `txtwrite`
  7. Detailed clickable Index (chapters, sections, subsections), clickable Subject Index
     page numbers, working cross-chapter links, and a nested PDF outline (PyMuPDF)
"""
import concurrent.futures
import html as html_lib
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote, urlparse

import fitz  # PyMuPDF: link rewriting and nested outline

# Placeholder URI scheme used inside generated HTML (Index, Subject Index). Chrome
# emits these as URI link annotations; the final pass rewrites them into internal
# GoTo links that jump to the exact page and heading position.
GOTO = "https://pdf-goto.invalid/"

ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = ROOT / "src"
BOOK_DIR = ROOT / "book"
OUT_PDF = ROOT / "Distributed-Systems-from-the-Ground-Up.pdf"
PDF_CSS = ROOT / "tools" / "pdf.css"  # Material Design 3 print styling, injected after theme/custom.css
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
GS = "/usr/local/bin/gs"

# Curated technical subject index: (Display Term, regex pattern)
INDEX_TERMS = [
    ("ACID transactions", r"\bACID\b"),
    ("Adaptive bitrate (ABR)", r"\b(?:ABR|adaptive bitrate)\b"),
    ("Ad-click aggregation", r"\bclick aggregation\b"),
    ("AIMD congestion control", r"\bAIMD\b"),
    ("Allowed lateness", r"\ballowed lateness\b"),
    ("AppendEntries RPC", r"\bAppendEntries\b"),
    ("Asynchronous barrier snapshots", r"\b(?:Chandy-Lamport|asynchronous barrier)\b"),
    ("Atomic swap / rename", r"\b(?:atomic rename|atomic swap)\b"),
    ("Availability zones (AZ)", r"\b(?:availability zone|multi-AZ)\b"),
    ("Backpressure", r"\bbackpressure\b"),
    ("Base-62 encoding", r"\bBase-?62\b"),
    ("Bit-rot scrubbing", r"\b(?:bit-?rot|scrubbing)\b"),
    ("Bloom filter", r"\bBloom filter"),
    ("BOLA / BBA bitrate control", r"\b(?:BOLA|BBA)\b"),
    ("Cache-aside pattern", r"\bcache-aside\b"),
    ("Cache stampede", r"\b(?:stampede|thundering herd)\b"),
    ("CAP / PACELC theorem", r"\b(?:PACELC|CAP theorem)\b"),
    ("Cardinality explosion", r"\bcardinality explosion\b"),
    ("Causal broadcast", r"\bcausal (?:broadcast|order|delivery)\b"),
    ("CDN Origin Shield", r"\bOrigin Shield\b"),
    ("Circuit breaker", r"\bcircuit breaker"),
    ("Clock drift and leap seconds", r"\b(?:clock drift|clock regression|leap second)\b"),
    ("CMAF (HLS and DASH)", r"\bCMAF\b"),
    ("CoDel load shedding", r"\bCoDel\b"),
    ("Commit index", r"\bcommit index\b"),
    ("Compaction", r"\bcompaction\b"),
    ("Compare-and-Swap (CAS)", r"\b(?:compare-and-swap|If-Match)\b"),
    ("Conflict-free Replicated Data Types (CRDT)", r"\bCRDTs?\b"),
    ("Consistent hashing", r"\bconsistent hash"),
    ("Content-defined chunking (CDC)", r"\b(?:content-defined chunking|FastCDC|Rabin)\b"),
    ("Control plane vs. data plane", r"\bcontrol plane\b"),
    ("Cooperative sticky rebalance", r"\bcooperative (?:sticky )?rebalanc"),
    ("CRC32C checksums", r"\bCRC32C\b"),
    ("Cursor pagination", r"\b(?:cursor pagination|keyset pagination)\b"),
    ("Dead-letter queue (DLQ)", r"\b(?:dead-letter|DLQ)\b"),
    ("Delta-of-delta compression", r"\bdelta-of-delta\b"),
    ("Deterministic matching engine", r"\bmatching engine\b"),
    ("Double-entry ledger", r"\bdouble-entry\b"),
    ("Election timeout", r"\belection timeout\b"),
    ("Erasure coding", r"\berasure cod"),
    ("Error budget", r"\berror budget\b"),
    ("Event-time watermarks", r"\bwatermark"),
    ("Eventual consistency", r"\beventual consistency\b"),
    ("Exponential backoff with jitter", r"\b(?:exponential backoff|jitter)\b"),
    ("Exponential frequency decay", r"\bexponential (?:frequency )?decay\b"),
    ("Failure domains", r"\bfailure domain"),
    ("Fencing tokens", r"\bfencing token"),
    ("FIX / SBE binary protocols", r"\b(?:FIX|SBE|OUCH)\b"),
    ("Flapping / hysteresis alerts", r"\bhysteresis\b"),
    ("fsync / fdatasync durability", r"\b(?:fsync|fdatasync)\b"),
    ("Galois Field GF(2^8)", r"\bGF\(2\^?8\)\b"),
    ("GCRA (Generic Cell Rate Algorithm)", r"\bGCRA\b"),
    ("Geohash boundary distortion", r"\bgeohash\b"),
    ("Gorilla time-series compression", r"\bGorilla\b"),
    ("Group commit", r"\bgroup commit\b"),
    ("H3 hexagonal spatial index", r"\bH3\b"),
    ("Hot-account sharding", r"\bhot[- ]account"),
    ("Hot-key mitigation", r"\bhot[- ]key"),
    ("Hybrid fan-out (push vs. pull)", r"\bhybrid fan-?out\b"),
    ("Hybrid Logical Clock (HLC)", r"\b(?:Hybrid Logical Clock|HLC)\b"),
    ("HyperLogLog", r"\bHyperLogLog\b"),
    ("Idempotency keys", r"\bidempotenc"),
    ("In-Sync Replicas (ISR)", r"\b(?:In-Sync Replica|ISR)\b"),
    ("Inverted label index", r"\binverted (?:label )?index\b"),
    ("Joint consensus reconfiguration", r"\bjoint consensus\b"),
    ("K-anonymity privacy gate", r"\bk-anonymity\b"),
    ("Leader election", r"\bleader election\b"),
    ("Lease-based claiming", r"\blease\b"),
    ("Limit order book (LOB)", r"\border book\b"),
    ("Linearizability", r"\blinearizab"),
    ("LMAX Disruptor ring buffer", r"\b(?:LMAX|Disruptor)\b"),
    ("Log Matching Property", r"\bLog Matching\b"),
    ("Long polling vs. WebSockets", r"\bWebSocket"),
    ("LRU and W-TinyLFU eviction", r"\b(?:W-TinyLFU|TinyLFU|\bLRU\b)"),
    ("Mechanical sympathy", r"\bmechanical sympathy\b"),
    ("MemTable", r"\bMemTable\b"),
    ("Mercator politeness frontier", r"\bMercator\b"),
    ("Merkle tree diffing", r"\bMerkle\b"),
    ("Monotonic term fencing", r"\bmonotonic term\b"),
    ("Multi-Raft sharding", r"\bMulti-Raft\b"),
    ("Multipart atomic upload", r"\bmultipart\b"),
    ("NOT_LEADER redirection", r"\bNOT_LEADER\b"),
    ("Operational Transformation (OT)", r"\bOperational Transformation\b"),
    ("PCI-DSS cardholder isolation", r"\bPCI-?DSS\b"),
    ("Prefix trie (top-K)", r"\b(?:prefix trie|trie)\b"),
    ("Price-time priority (FIFO)", r"\bprice-time priority\b"),
    ("Priority lane isolation", r"\bpriority lane"),
    ("Probabilistic early expiration (XFetch)", r"\b(?:XFetch|probabilistic early)\b"),
    ("Quorum intersection", r"\bquorum\b"),
    ("Quota leasing", r"\bquota leas"),
    ("Raft consensus", r"\bRaft\b"),
    ("ReadIndex linearizable reads", r"\bReadIndex\b"),
    ("Reconciliation pipeline (T+0..T+2)", r"\breconciliation\b"),
    ("Redlock critique", r"\bRedlock\b"),
    ("Reed-Solomon RS(6, 3)", r"\bReed-Solomon\b"),
    ("Request coalescing (Singleflight)", r"\b(?:singleflight|request coalescing)\b"),
    ("robots.txt crawl delay", r"\brobots\.txt\b"),
    ("Saga compensation", r"\b[Ss]aga\b"),
    ("Seat hold state machine", r"\bseat hold"),
    ("Sequence CRDT (RGA / YATA / Fugue)", r"\b(?:RGA|YATA|Fugue)\b"),
    ("Service Level Objectives (SLOs)", r"\bSLOs?\b"),
    ("SimHash near-duplicate detection", r"\bSimHash\b"),
    ("Sliding window rate limiting", r"\bsliding window\b"),
    ("Snowflake 64-bit IDs", r"\bSnowflake\b"),
    ("Spider-trap guards", r"\bspider[- ]trap"),
    ("Split-brain prevention", r"\bsplit-brain\b"),
    ("State machine replication", r"\bstate machine replication\b"),
    ("Surge pricing", r"\bsurge pricing\b"),
    ("Tail latency (p99)", r"\btail latency\b"),
    ("Timing wheels", r"\btiming wheel"),
    ("Token bucket", r"\btoken bucket\b"),
    ("Tombstones and garbage collection", r"\btombstone"),
    ("Torn-tail truncation", r"\btorn[- ]tail\b"),
    ("Transactional outbox", r"\btransactional outbox\b"),
    ("Transcoding DAG", r"\btranscod"),
    ("Two-phase commit", r"\btwo-phase commit\b"),
    ("Virtual nodes (vnodes)", r"\b(?:virtual node|vnode)"),
    ("Virtual waiting room", r"\bwaiting room\b"),
    ("Write-Ahead Log (WAL)", r"\b(?:Write-Ahead Log|\bWAL\b)"),
    ("Zero-copy sendfile", r"\bsendfile\b"),
]


def to_roman(n: int) -> str:
    vals = [(10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    out = []
    for v, s in vals:
        while n >= v:
            out.append(s)
            n -= v
    return "".join(out)


def parse_summary():
    """Return ordered list of (kind, title, html_name) from src/SUMMARY.md."""
    entries = []
    for line in (SRC_DIR / "SUMMARY.md").read_text(encoding="utf-8").splitlines():
        m_part = re.match(r"^#\s+(.+)$", line.strip())
        if m_part:
            title = m_part.group(1).strip()
            if title != "Summary":
                entries.append(("part", title, None))
            continue
        m_ch = re.match(r"^(?:[-*]\s+)?\[([^\]]+)\]\(([^)]+\.md)\)", line.strip())
        if m_ch:
            title, md_name = m_ch.group(1).strip(), m_ch.group(2).strip()
            html_name = md_name[:-3] + ".html"
            if html_name == "cover.html" and not (BOOK_DIR / "cover.html").exists():
                html_name = "index.html"
            entries.append(("chapter", title, html_name))
    return entries


def css_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"')


def prepare_html(html_path: Path, is_cover: bool, running_title: str, out_html: Path):
    html = html_path.read_text(encoding="utf-8")
    html = re.sub(r'<html([^>]*?)class="[^"]*"', r'<html\1class="light"', html, count=1)
    html = re.sub(r"const default_light_theme = .*?;", 'const default_light_theme = "light";', html)
    html = re.sub(r"const default_dark_theme = .*?;", 'const default_dark_theme = "light";', html)
    html = re.sub(r"const default_theme = .*?;", 'const default_theme = "light";', html)
    if is_cover:
        html = re.sub(r'<h1 id="cover">.*?</h1>', "", html, count=1, flags=re.S)
    html = re.sub(r"<script[^>]*>\s*//\s*Live reload.*?</script>", "", html, flags=re.S)
    html = re.sub(r'<script src="theme/code[^"]*\.js"></script>', "", html)

    if is_cover:
        page_css = (
            "@page{size:letter;margin:0.45in;background:#ffffff;}"
            "html,body{background:#ffffff!important;color:#1b1f27!important;}"
        )
    else:
        rt = css_escape(running_title)
        page_css = (
            "@page{"
            "size:letter;"
            "margin:0.62in 0.56in 0.62in 0.56in;"
            "background:#ffffff;"
            '@top-left{content:"Distributed Systems from the Ground Up";font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;font-size:7.6pt;color:#6c7686;border-bottom:0.5pt solid #e2e6ee;padding-bottom:4pt;margin-bottom:8pt;}'
            f'@top-right{{content:"{rt}";font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;font-size:7.6pt;color:#6c7686;border-bottom:0.5pt solid #e2e6ee;padding-bottom:4pt;margin-bottom:8pt;}}'
            "}"
            "@page :first{@top-left{content:none;border-bottom:none;}@top-right{content:none;border-bottom:none;}}"
            "html,body{background:#ffffff!important;color:#1b1f27!important;}"
            "@media print{pre,code,.content pre > code{break-inside:auto!important;page-break-inside:auto!important;}}"
        )

    if not is_cover:
        page_css += PDF_CSS.read_text(encoding="utf-8")
    html = html.replace("</head>", f"<style>{page_css}</style></head>", 1)
    out_html.write_text(html, encoding="utf-8")


def pdf_page_count(pdf_path: Path) -> int:
    out = subprocess.check_output(
        [GS, "-q", "-dNOSAFER", "-dNODISPLAY", "-c", f"({pdf_path}) (r) file runpdfbegin pdfpagecount = quit"],
        text=True,
    ).strip()
    return int(out)


def extract_pdf_pages_text(pdf_path: Path):
    """Return list of extracted page texts (0-indexed) using Ghostscript txtwrite per page."""
    with tempfile.TemporaryDirectory() as ptd:
        pdir = Path(ptd)
        subprocess.run(
            [GS, "-q", "-dNOPAUSE", "-dBATCH", "-sDEVICE=txtwrite", f"-sOutputFile={pdir}/p_%04d.txt", str(pdf_path)],
            check=True,
        )
        return [p.read_text(encoding="utf-8", errors="ignore") for p in sorted(pdir.glob("p_*.txt"))]


def render_html_to_pdf(html_path: Path, out_pdf: Path, profile_dir: Path):
    profile_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        CHROME,
        "--headless=new",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-crash-reporter",
        f"--user-data-dir={profile_dir}",
        "--no-pdf-header-footer",
        "--allow-file-access-from-files",
        f"--print-to-pdf={out_pdf}",
        f"file://{html_path.resolve()}",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if not out_pdf.exists() or out_pdf.stat().st_size < 1000:
        raise RuntimeError(f"Chrome failed on {html_path.name} (rc={proc.returncode}): {proc.stderr[-800:]}")


def parse_headings(html: str):
    """Return ordered [(level, anchor_id, plain_text)] for every h2/h3 section heading."""
    out = []
    for m in re.finditer(r'<h([23])\s+id="([^"]+)"[^>]*>(.*?)</h\1>', html, re.S):
        text = html_lib.unescape(re.sub(r"<[^>]+>", "", m.group(3)))
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            out.append((int(m.group(1)), m.group(2), text))
    return out


def collect_links(pdf_path: Path):
    """Return every link annotation in a rendered component PDF as [(page_offset, link_dict)]."""
    doc = fitz.open(str(pdf_path))
    try:
        return [(p.number, lk) for p in doc for lk in p.get_links()]
    finally:
        doc.close()


def collect_dests(pdf_path: Path):
    """Return {anchor_id: (page_offset, to_point)} for every named destination Chrome emitted."""
    doc = fitz.open(str(pdf_path))
    try:
        return {
            name: (d["page"], fitz.Point(d.get("to", (0, 0))))
            for name, d in doc.resolve_names().items()
            if d.get("page", -1) >= 0
        }
    finally:
        doc.close()


def render_chapter(idx: int, title: str, html_name: str, tmp_dir: Path):
    src_html = BOOK_DIR / html_name
    if not src_html.exists():
        raise FileNotFoundError(f"Missing compiled HTML: {src_html}")
    is_cover = html_name in ("cover.html", "index.html")
    tmp_html = BOOK_DIR / f"_pdf_tmp_{idx:02d}.html"
    tmp_pdf = tmp_dir / f"sec_{idx:02d}.pdf"
    profile_dir = tmp_dir / f"prof_{idx:02d}"
    running_title = title if title == "Preface" else f"Chapter {title}"
    prepare_html(src_html, is_cover, running_title, tmp_html)
    try:
        render_html_to_pdf(tmp_html, tmp_pdf, profile_dir)
        pages = pdf_page_count(tmp_pdf)
        page_texts = [] if is_cover or title == "Preface" else extract_pdf_pages_text(tmp_pdf)
        dests = collect_dests(tmp_pdf)
        headings = []
        if not is_cover:
            for level, anchor, text in parse_headings(src_html.read_text(encoding="utf-8")):
                if anchor in dests:
                    page_off, to = dests[anchor]
                    headings.append((level, anchor, text, page_off, to))
        return idx, title, tmp_pdf, pages, page_texts, headings, dests
    finally:
        tmp_html.unlink(missing_ok=True)


def build_title_copyright_html() -> str:
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><style>
@page { size: letter; margin: 0.75in 0.85in; background: #ffffff; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  color: #1b1f27; margin: 0; padding: 0;
  display: flex; flex-direction: column; justify-content: space-between; min-height: 9.4in;
}
.top-rule { width: 52px; height: 4px; background: #1a5fc4; border-radius: 2px; margin-bottom: 28px; }
.kicker { font-size: 9pt; letter-spacing: 0.14em; text-transform: uppercase; color: #1a5fc4; font-weight: 650; margin-bottom: 12px; }
h1 { font-size: 28pt; line-height: 1.15; font-weight: 750; margin: 0 0 12px 0; color: #111622; }
.subtitle { font-size: 13pt; line-height: 1.45; color: #465060; margin: 0 0 36px 0; max-width: 5.8in; }
.author { font-size: 14pt; font-weight: 650; color: #1b1f27; margin: 0 0 6px 0; }
.edition { font-size: 10pt; color: #566070; margin: 0; }
.colophon {
  border-top: 1px solid #dce0e7; padding-top: 18px; font-size: 8.6pt; line-height: 1.6; color: #465060;
}
.colophon p { margin: 0 0 8px 0; }
.colophon strong { color: #1b1f27; font-weight: 650; }
.mono { font-family: "SF Mono", Menlo, Consolas, monospace; font-size: 8.2pt; color: #1a5fc4; }
</style></head><body>
<div>
  <div class="top-rule"></div>
  <div class="kicker">Systems Architecture Monograph &middot; Six Parts &middot; Twenty-Eight Chapters</div>
  <h1>Distributed Systems<br>from the Ground Up</h1>
  <p class="subtitle">Consensus, Storage Engines, Traffic Control, and Fault-Tolerant Architecture</p>
  <p class="author">Arpan Pathak</p>
  <p class="edition">First Edition &middot; 2026</p>
</div>
<div class="colophon">
  <p><strong>Copyright &copy; 2026 Arpan Pathak.</strong></p>
  <p><strong>License:</strong> The text, architectural diagrams, and abstract chapter plates of this book are licensed under the <strong>Creative Commons Attribution 4.0 International License (CC BY 4.0)</strong>. You are free to read, share, redistribute, and cite this work with appropriate attribution. The accompanying Rust implementations and fault simulations are licensed under the <strong>MIT License</strong>.</p>
  <p><strong>Documentation and Visual Engineering Standards:</strong> Prose across all twenty-eight chapters is audited against ISO 24495-1 (Plain Language), ISO/IEC/IEEE 26514 (Systems and Software Engineering Documentation), ISO/IEC Directives Part 2, and ASD-STE100. All 85 architectural figures follow Material Design 3 visual semantics and are programmatically verified in headless Chromium for layout integrity.</p>
  <p><strong>Author Website &amp; Code:</strong> <span class="mono">https://arpanpathak.github.io</span> &middot; <span class="mono">https://github.com/arpanpathak</span></p>
  <p><strong>Suggested Citation:</strong> Pathak, A. (2026). <em>Distributed Systems from the Ground Up: Consensus, Storage Engines, Traffic Control, and Fault-Tolerant Architecture</em>. First Edition.</p>
</div>
</body></html>"""


def toc_row(cls: str, href: str, label_html: str, page_label) -> str:
    return (
        f'<a class="toc-row {cls}" href="{href}">'
        f'<span class="toc-title">{label_html}</span>'
        f'<span class="toc-dots"></span>'
        f'<span class="toc-page">{html_lib.escape(str(page_label))}</span>'
        f"</a>"
    )


def build_toc_html(entries, chapter_pages, preface_roman: str, index_page: int, headings) -> str:
    """Detailed, fully clickable Index: every part, chapter, section (h2), and subsection (h3)."""
    rows = [toc_row("toc-front", f"{GOTO}f/preface", "Preface", preface_roman)]
    for idx, (kind, title, html_name) in enumerate(entries):
        if kind == "chapter" and html_name in ("cover.html", "index.html", "about-this-book.html"):
            continue
        if kind == "part":
            rows.append(f'<div class="toc-part">{html_lib.escape(title)}</div>')
            continue
        start = chapter_pages[idx]
        m = re.match(r"^(\d+)\.\s+(.+)$", title)
        if m:
            label = f'<span class="ch-num">{m.group(1)}</span><span class="ch-name">{html_lib.escape(m.group(2))}</span>'
        else:
            label = html_lib.escape(title)
        rows.append(toc_row("toc-chapter", f"{GOTO}c/{idx}", label, start))
        for level, anchor, text, page_off, _to in headings.get(idx, []):
            cls = "toc-sec" if level == 2 else "toc-sub"
            rows.append(toc_row(cls, f"{GOTO}s/{idx}/{anchor}", html_lib.escape(text), start + page_off))

    rows.append(toc_row("toc-back", f"{GOTO}f/index", "Subject Index", index_page))

    body = "\n".join(rows)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><style>
@page {{
  size: letter;
  margin: 0.62in 0.62in 0.62in 0.62in;
  background: #ffffff;
  @top-left {{ content: "Distributed Systems from the Ground Up"; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 7.6pt; color: #6c7686; border-bottom: 0.5pt solid #e2e6ee; padding-bottom: 4pt; margin-bottom: 8pt; }}
  @top-right {{ content: "Index"; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 7.6pt; color: #6c7686; border-bottom: 0.5pt solid #e2e6ee; padding-bottom: 4pt; margin-bottom: 8pt; }}
}}
@page :first {{ @top-left {{ content: none; border-bottom: none; }} @top-right {{ content: none; border-bottom: none; }} }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  color: #1b1f27; margin: 0; padding: 0;
}}
.toc-kicker {{ font-size: 8.5pt; letter-spacing: 0.14em; text-transform: uppercase; color: #1a5fc4; font-weight: 650; margin-bottom: 4px; }}
h1 {{ font-size: 20pt; font-weight: 750; margin: 0 0 6px 0; padding-bottom: 8px; border-bottom: 1.5px solid #1a5fc4; color: #111622; }}
.toc-hint {{ font-size: 8pt; color: #6c7686; margin: 0 0 10px 0; }}
.toc-part {{
  margin: 14px 0 5px 0;
  padding: 4px 8px;
  background: #eef4fe;
  border-left: 3px solid #1a5fc4;
  border-radius: 3px;
  font-size: 9.4pt;
  font-weight: 700;
  color: #173d7a;
  break-after: avoid;
}}
.toc-row {{
  display: flex;
  align-items: baseline;
  padding: 0 2px;
  break-inside: avoid;
  color: inherit;
  text-decoration: none;
}}
.toc-chapter {{ font-size: 9.6pt; font-weight: 650; line-height: 1.5; margin-top: 7px; break-after: avoid; }}
.toc-sec {{ font-size: 8.6pt; line-height: 1.42; padding-left: 30px; color: #263042; }}
.toc-sub {{ font-size: 7.8pt; line-height: 1.36; padding-left: 50px; color: #566070; }}
.toc-front {{ font-size: 9.6pt; font-weight: 600; margin-bottom: 4px; }}
.toc-back {{ font-size: 9.6pt; font-weight: 700; margin-top: 14px; padding-top: 6px; border-top: 1px solid #dce0e7; }}
.toc-title {{ flex: 0 1 auto; display: inline-flex; align-items: baseline; gap: 8px; }}
.ch-num {{
  display: inline-block; width: 20px; text-align: right;
  font-family: "SF Mono", Menlo, Consolas, monospace;
  font-size: 8.6pt; font-weight: 650; color: #1a5fc4;
}}
.toc-dots {{
  flex: 1 1 auto;
  border-bottom: 1px dotted #c3ccd8;
  margin: 0 8px;
  min-width: 18px;
}}
.toc-page {{
  flex: 0 0 auto;
  font-family: "SF Mono", Menlo, Consolas, monospace;
  font-size: 8pt;
  color: #1a5fc4;
  min-width: 26px;
  text-align: right;
}}
</style></head><body>
<div class="toc-kicker">Chapters, Sections, and Subsections</div>
<h1>Index</h1>
<p class="toc-hint">Every entry and page number is a link. Select any line to jump to that section.</p>
{body}
</body></html>"""


def page_link(n: int) -> str:
    return f'<a class="idx-link" href="{GOTO}p/{n}">{n}</a>'


def compress_page_ranges(pages):
    """Format sorted unique page ints into clickable ranges (e.g. [4,5,6,18] -> '4-6, 18')."""
    if not pages:
        return ""
    pages = sorted(set(pages))
    # Cap overly frequent terms to their first 10 and last 2 distinct references
    if len(pages) > 14:
        pages = pages[:10] + pages[-2:]
    ranges = []
    start = prev = pages[0]
    for p in pages[1:]:
        if p == prev + 1:
            prev = p
        else:
            ranges.append(page_link(start) if start == prev else f"{page_link(start)}&ndash;{page_link(prev)}")
            start = prev = p
    ranges.append(page_link(start) if start == prev else f"{page_link(start)}&ndash;{page_link(prev)}")
    return ", ".join(ranges)


def build_index_html(term_pages) -> str:
    grouped = {}
    for term, pages in sorted(term_pages.items(), key=lambda kv: kv[0].lower()):
        if not pages:
            continue
        letter = term[0].upper()
        grouped.setdefault(letter, []).append((term, compress_page_ranges(pages)))

    blocks = []
    for letter in sorted(grouped.keys()):
        items = "\n".join(
            f'<div class="idx-item"><span class="idx-term">{html_lib.escape(t)}</span>, <span class="idx-pg">{p}</span></div>'
            for t, p in grouped[letter]
        )
        blocks.append(f'<div class="idx-group"><div class="idx-letter">{letter}</div>{items}</div>')

    content = "\n".join(blocks)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><style>
@page {{
  size: letter;
  margin: 0.62in 0.56in 0.62in 0.56in;
  background: #ffffff;
  @top-left {{ content: "Distributed Systems from the Ground Up"; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 7.6pt; color: #6c7686; border-bottom: 0.5pt solid #e2e6ee; padding-bottom: 4pt; margin-bottom: 8pt; }}
  @top-right {{ content: "Index"; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; font-size: 7.6pt; color: #6c7686; border-bottom: 0.5pt solid #e2e6ee; padding-bottom: 4pt; margin-bottom: 8pt; }}
}}
@page :first {{ @top-left {{ content: none; border-bottom: none; }} @top-right {{ content: none; border-bottom: none; }} }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  color: #1b1f27; margin: 0; padding: 0;
}}
.idx-kicker {{ font-size: 8.5pt; letter-spacing: 0.14em; text-transform: uppercase; color: #1a5fc4; font-weight: 650; margin-bottom: 4px; }}
h1 {{ font-size: 20pt; font-weight: 750; margin: 0 0 14px 0; padding-bottom: 8px; border-bottom: 1.5px solid #1a5fc4; color: #111622; }}
.idx-cols {{ column-count: 2; column-gap: 28px; column-rule: 0.5pt solid #e2e6ee; }}
.idx-group {{ margin-bottom: 10px; }}
.idx-letter {{
  font-size: 11pt; font-weight: 750; color: #1a5fc4;
  border-bottom: 0.8pt solid #dce0e7; padding-bottom: 2px; margin: 6px 0 4px 0;
  break-after: avoid;
}}
.idx-item {{ font-size: 8.4pt; line-height: 1.48; margin: 1.5px 0; padding-left: 10px; text-indent: -10px; break-inside: avoid; }}
.idx-term {{ color: #1b1f27; font-weight: 500; }}
.idx-link {{ color: #1a5fc4; text-decoration: none; }}
.idx-pg {{ font-family: "SF Mono", Menlo, Consolas, monospace; font-size: 7.8pt; color: #465060; }}
</style></head><body>
<div class="idx-kicker">Back Matter</div>
<h1>Subject Index</h1>
<div class="idx-cols">
{content}
</div>
</body></html>"""


def ps_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_footer_stamper_ps(front_numbered_start: int, body_start_pdf_page: int, total_pdf_pages: int) -> str:
    """Build PostScript EndPage hook that stamps Roman numerals on front matter and Arabic 1..N on body+index."""
    # Build lookup array of footer strings (1-indexed by PDF page number)
    labels = [""] * (total_pdf_pages + 1)
    roman_idx = 1
    for p in range(front_numbered_start, body_start_pdf_page):
        labels[p] = to_roman(roman_idx)
        roman_idx += 1
    arabic_idx = 1
    for p in range(body_start_pdf_page, total_pdf_pages + 1):
        labels[p] = str(arabic_idx)
        arabic_idx += 1

    arr_items = " ".join(f"({ps_escape(lbl)})" for lbl in labels[1:])
    return f"""/PageLabels [ {arr_items} ] def
<<
  /EndPage {{
    2 eq {{ pop false }} {{
      /PIdx exch def
      PIdx PageLabels length lt {{
        PageLabels PIdx get dup length 0 gt {{
          gsave
            /Helvetica findfont 8.2 scalefont setfont
            0.34 0.39 0.46 setrgbcolor
            dup stringwidth pop 2 div 306 exch sub 22 moveto
            show
          grestore
        }} {{ pop }} ifelse
      }} if
      true
    }} ifelse
  }}
>> setpagedevice
"""


def finalize_links_and_outline(stamped_pdf: Path, out_pdf: Path, components, resolve_key, html_to_target, outline):
    """Rewrite every link in the merged book into a working internal jump, and install the outline.

    components: [(first_pdf_page_1based, [(page_offset, link_dict)], dests_or_None)]
    resolve_key: maps a GOTO placeholder key (e.g. 's/12/anchor') to (page0, Point) or None
    html_to_target: maps (html basename, fragment) to (page0, Point) or None
    """
    doc = fitz.open(str(stamped_pdf))
    for page in doc:
        for lk in page.get_links():
            page.delete_link(lk)

    stats = {"internal": 0, "index": 0, "cross": 0, "external": 0, "dropped": 0}
    for first_page, links, _dests in components:
        base0 = first_page - 1
        for page_off, lk in links:
            page = doc[base0 + page_off]
            rect = lk["from"]
            target = None
            uri = lk.get("uri") or lk.get("file") or ""
            if lk["kind"] in (fitz.LINK_GOTO, fitz.LINK_NAMED) and lk.get("page", -1) >= 0:
                target = (base0 + lk["page"], fitz.Point(lk.get("to", (0, 0))))
                stats["internal"] += 1
            elif uri.startswith(GOTO):
                target = resolve_key(uri[len(GOTO):])
                stats["index" if target else "dropped"] += 1
            elif uri.startswith("file:") or (uri and "://" not in uri):
                parsed = urlparse(uri)
                target = html_to_target(Path(unquote(parsed.path)).name, unquote(parsed.fragment))
                if target is None:
                    stats["dropped"] += 1
                    continue
                stats["cross"] += 1
            elif uri:
                page.insert_link({"kind": fitz.LINK_URI, "from": rect, "uri": uri})
                stats["external"] += 1
                continue
            if target is not None:
                page.insert_link({"kind": fitz.LINK_GOTO, "from": rect, "page": target[0], "to": target[1], "zoom": 0})

    # Nested outline: levels may only grow by one step at a time
    toc, prev = [], 0
    for level, title, (page0, to) in outline:
        level = min(level, prev + 1)
        toc.append([level, title, page0 + 1, {"kind": fitz.LINK_GOTO, "page": page0, "to": to}])
        prev = level
    doc.set_toc(toc, collapse=2)
    doc.set_metadata({
        "title": "Distributed Systems from the Ground Up",
        "author": "Arpan Pathak",
        "subject": "Consensus, Storage Engines, Traffic Control, and Fault-Tolerant Architecture",
    })
    out_pdf.unlink(missing_ok=True)
    doc.save(str(out_pdf), garbage=3, deflate=True)
    doc.close()
    return stats, len(toc)


def main():
    entries = parse_summary()
    sections = [(i, t, h) for i, (k, t, h) in enumerate(entries) if k == "chapter"]
    print(f"Pass 1: Rendering {len(sections)} book sections via headless Chrome...")

    with tempfile.TemporaryDirectory() as td:
        tmp_dir = Path(td)
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
            futs = [ex.submit(render_chapter, i, t, h, tmp_dir) for i, t, h in sections]
            for fut in concurrent.futures.as_completed(futs):
                idx, title, pdf_path, pages, texts, headings, dests = fut.result()
                results[idx] = (title, pdf_path, pages, texts, headings, dests)
                print(f"  [{idx:02d}] {title:52s} -> {pages:2d} pages, {len(headings):3d} sections")

        headings_by_idx = {i: r[4] for i, r in results.items()}

        # Separate front matter (Cover, Preface) from main chapters (1..28)
        cover_idx = next(i for i, (k, t, h) in enumerate(entries) if k == "chapter" and h in ("cover.html", "index.html"))
        preface_idx = next(i for i, (k, t, h) in enumerate(entries) if k == "chapter" and h == "about-this-book.html")

        # Render Title & Copyright Page (1 page)
        title_html = tmp_dir / "title_copyright.html"
        title_pdf = tmp_dir / "title_copyright.pdf"
        title_html.write_text(build_title_copyright_html(), encoding="utf-8")
        render_html_to_pdf(title_html, title_pdf, tmp_dir / "prof_title")
        title_pages = pdf_page_count(title_pdf)

        # Assign exact Arabic page numbers to Chapters 1..28 (starting at 1!)
        chapter_arabic_start = {}
        arabic_cursor = 1
        term_pages = {term: [] for term, _ in INDEX_TERMS}
        compiled_terms = [(term, re.compile(pat, re.I)) for term, pat in INDEX_TERMS]

        for idx, (kind, title, html_name) in enumerate(entries):
            if kind != "chapter" or idx in (cover_idx, preface_idx):
                continue
            pages, page_texts = results[idx][2], results[idx][3]
            chapter_arabic_start[idx] = arabic_cursor
            for offset, txt in enumerate(page_texts):
                abs_arabic_page = arabic_cursor + offset
                for term, rx in compiled_terms:
                    if rx.search(txt):
                        term_pages[term].append(abs_arabic_page)
            arabic_cursor += pages

        index_arabic_start = arabic_cursor

        # Render Subject Index
        index_html = tmp_dir / "subject_index.html"
        index_pdf = tmp_dir / "subject_index.pdf"
        index_html.write_text(build_index_html(term_pages), encoding="utf-8")
        render_html_to_pdf(index_html, index_pdf, tmp_dir / "prof_index")
        index_pages = pdf_page_count(index_pdf)
        indexed_count = sum(1 for v in term_pages.values() if v)
        print(f"  [IX] Subject Index ({indexed_count} terms)                         -> {index_pages:2d} pages")

        # Render detailed Index (front matter); re-render until the Preface Roman numeral is stable
        toc_html = tmp_dir / "toc.html"
        toc_pdf = tmp_dir / "toc.pdf"
        preface_roman = "iii"
        for attempt in range(4):
            toc_html.write_text(
                build_toc_html(entries, chapter_arabic_start, preface_roman, index_arabic_start, headings_by_idx),
                encoding="utf-8",
            )
            render_html_to_pdf(toc_html, toc_pdf, tmp_dir / f"prof_toc{attempt}")
            toc_pages = pdf_page_count(toc_pdf)
            want = to_roman(toc_pages + 1)
            if want == preface_roman:
                break
            preface_roman = want
        total_sections = sum(len(v) for k, v in headings_by_idx.items() if k in chapter_arabic_start)
        print(f"  [TC] Index ({total_sections} sections and subsections)          -> {toc_pages:2d} pages")

        # Assemble final PDF order & compute exact PDF page indices
        cover_pdf, cover_pages = results[cover_idx][1], results[cover_idx][2]
        preface_pdf, preface_pages = results[preface_idx][1], results[preface_idx][2]

        pdf_list = [str(cover_pdf), str(title_pdf), str(toc_pdf), str(preface_pdf)]
        cover_pdf_page = 1
        title_pdf_page = cover_pdf_page + cover_pages
        toc_pdf_page = title_pdf_page + title_pages
        preface_pdf_page = toc_pdf_page + toc_pages
        body_start_pdf_page = preface_pdf_page + preface_pages

        components = [
            (cover_pdf_page, collect_links(cover_pdf), None),
            (title_pdf_page, collect_links(title_pdf), None),
            (toc_pdf_page, collect_links(toc_pdf), None),
            (preface_pdf_page, collect_links(preface_pdf), None),
        ]
        start_page = {cover_idx: cover_pdf_page, preface_idx: preface_pdf_page}
        cur = body_start_pdf_page
        for idx, (kind, title, html_name) in enumerate(entries):
            if kind != "chapter" or idx in (cover_idx, preface_idx):
                continue
            pdf_path, pages = results[idx][1], results[idx][2]
            start_page[idx] = cur
            pdf_list.append(str(pdf_path))
            components.append((cur, collect_links(pdf_path), results[idx][5]))
            cur += pages

        index_pdf_page = cur
        pdf_list.append(str(index_pdf))
        components.append((index_pdf_page, collect_links(index_pdf), None))
        total_pdf_pages = index_pdf_page + index_pages - 1

        TOP = fitz.Point(0, 792)

        def top_of(pdf_page_1based):
            return (pdf_page_1based - 1, TOP)

        def dest_of(idx, anchor):
            dests = results[idx][5]
            if anchor and anchor in dests:
                off, to = dests[anchor]
                return (start_page[idx] - 1 + off, to)
            return top_of(start_page[idx])

        def resolve_key(key):
            parts = key.strip("/").split("/", 2)
            try:
                if parts[0] == "f":
                    return top_of(preface_pdf_page if parts[1] == "preface" else index_pdf_page)
                if parts[0] == "c":
                    return dest_of(int(parts[1]), None)
                if parts[0] == "s":
                    return dest_of(int(parts[1]), unquote(parts[2]))
                if parts[0] == "p":
                    return top_of(body_start_pdf_page + int(parts[1]) - 1)
            except (IndexError, ValueError, KeyError):
                return None
            return None

        html_to_idx = {h: i for i, (k, t, h) in enumerate(entries) if k == "chapter"}

        def html_to_target(basename, fragment):
            if basename.startswith("_pdf_tmp_"):
                return None
            idx = html_to_idx.get(basename)
            if idx is None or idx not in start_page:
                return None
            return dest_of(idx, fragment)

        # Outline: front matter, parts > chapters > sections > subsections, back matter
        outline = [
            (1, "Cover", top_of(cover_pdf_page)),
            (1, "Title and Copyright", top_of(title_pdf_page)),
            (1, "Index", top_of(toc_pdf_page)),
            (1, "Preface", top_of(preface_pdf_page)),
        ]
        for idx, (kind, title, html_name) in enumerate(entries):
            if kind == "part":
                nxt = next((j for j in range(idx + 1, len(entries)) if j in chapter_arabic_start), None)
                if nxt is not None:
                    outline.append((1, title, top_of(start_page[nxt])))
            elif idx in chapter_arabic_start:
                outline.append((2, title, top_of(start_page[idx])))
                for level, anchor, text, _off, _to in headings_by_idx.get(idx, []):
                    outline.append((level + 1, text, dest_of(idx, anchor)))
        outline.append((1, "Subject Index", top_of(index_pdf_page)))

        footer_ps_path = tmp_dir / "footer_numbers.ps"
        footer_ps_path.write_text(
            build_footer_stamper_ps(toc_pdf_page, body_start_pdf_page, total_pdf_pages),
            encoding="utf-8",
        )

        merged_raw = tmp_dir / "merged_raw.pdf"
        merge_cmd = [
            GS,
            "-q",
            "-dBATCH",
            "-dNOPAUSE",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.6",
            "-dPDFSETTINGS=/prepress",
            "-dCompressPages=true",
            f"-sOutputFile={merged_raw}",
            *pdf_list,
        ]
        subprocess.run(merge_cmd, check=True)

        # Stamp Roman (front matter) and Arabic (body + index) page numbers
        stamped = tmp_dir / "stamped.pdf"
        stamp_cmd = [
            GS,
            "-q",
            "-dBATCH",
            "-dNOPAUSE",
            "-sDEVICE=pdfwrite",
            "-dCompatibilityLevel=1.6",
            "-dPDFSETTINGS=/prepress",
            "-dCompressPages=true",
            "-dFIXEDMEDIA",
            "-sPAPERSIZE=letter",
            f"-sOutputFile={stamped}",
            str(footer_ps_path),
            str(merged_raw),
        ]
        subprocess.run(stamp_cmd, check=True)

        stats, outline_count = finalize_links_and_outline(
            stamped, OUT_PDF, components, resolve_key, html_to_target, outline
        )
        final_pages = pdf_page_count(OUT_PDF)
        size_mb = OUT_PDF.stat().st_size / 1048576
        print(f"  Links: {stats}  |  Outline entries: {outline_count}")
        print(
            f"Wrote {OUT_PDF} ({size_mb:.2f} MB, {final_pages} pages total: "
            f"Cover + Copyright + {toc_pages}p Index + {preface_pages}p Preface + "
            f"{index_arabic_start - 1}p Chapters 1-28 + {index_pages}p Subject Index)"
        )


if __name__ == "__main__":
    main()
