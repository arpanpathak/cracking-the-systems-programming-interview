#!/usr/bin/env python3
"""Measure every <text> element of every Material 3 SVG in real Google Chrome.

Reports any label that overflows its container box (`data-fit`) or overlaps
another text label under actual macOS SF Pro / SF Mono rendering.
"""
import html
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
M3_DIR = ROOT / "src" / "figures" / "m3"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"


def main():
    prefixes = sys.argv[1:]
    svgs = sorted(M3_DIR.glob("*.svg"))
    if prefixes:
        svgs = [p for p in svgs if any(p.name.startswith(pref) for pref in prefixes)]
    blocks = []
    for p in svgs:
        blocks.append(f'<div class="wrap" data-name="{html.escape(p.name)}">{p.read_text()}</div>')

    page = f"""<!doctype html><html><body style="margin:0;padding:0;background:#fff">
{''.join(blocks)}
<pre id="report"></pre>
<script>
const issues = [];
document.querySelectorAll('.wrap').forEach(wrap => {{
  const name = wrap.dataset.name;
  const svg = wrap.querySelector('svg');
  const srect = svg.getBoundingClientRect();
  const texts = [...svg.querySelectorAll('text')];
  const boxes = texts.map(t => t.getBoundingClientRect());
  texts.forEach((t, i) => {{
    if (t.hasAttribute('transform')) return;
    const b = boxes[i];
    const leftRel = b.left - srect.left;
    const rightRel = b.right - srect.left;
    const fitAttr = t.getAttribute('data-fit');
    const [lo, hi] = fitAttr ? fitAttr.split(',').map(Number) : [8, srect.width - 8];
    if (leftRel < lo - 1.5 || rightRel > hi + 1.5) {{
      issues.push(`${{name}}: OVERFLOW "${{t.textContent}}" [${{leftRel.toFixed(1)}}..${{rightRel.toFixed(1)}}] > fit [${{lo.toFixed(1)}}..${{hi.toFixed(1)}}]`);
    }}
    for (let j = i + 1; j < texts.length; j++) {{
      if (texts[j].hasAttribute('transform')) continue;
      const o = boxes[j];
      const dx = Math.min(b.right, o.right) - Math.max(b.left, o.left);
      const dy = Math.min(b.bottom, o.bottom) - Math.max(b.top, o.top);
      if (dx > 2.5 && dy > 4.0) {{
        issues.push(`${{name}}: OVERLAP "${{t.textContent}}" / "${{texts[j].textContent}}" (dx=${{dx.toFixed(1)}}, dy=${{dy.toFixed(1)}})`);
      }}
    }}
  }});
}});
document.getElementById('report').textContent = JSON.stringify(issues);
</script></body></html>"""

    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False) as tf:
        tf.write(page)
        html_path = Path(tf.name)

    try:
        proc = subprocess.run(
            [CHROME, "--headless=new", "--disable-gpu", "--dump-dom", f"file://{html_path}"],
            capture_output=True, text=True, check=True,
        )
        m = re.search(r'<pre id="report">(.*?)</pre>', proc.stdout, re.S)
        if not m:
            raise RuntimeError("No report block found in Chrome output")
        issues = json.loads(html.unescape(m.group(1)))
        for item in issues:
            print(item)
        print(f"Chrome browser audit: {len(svgs)} SVGs checked, {len(issues)} issues")
        if issues:
            raise SystemExit(1)
    finally:
        html_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
