#!/usr/bin/env python3
"""Render every diagrams/*.dot to src/figures/*.svg with one house style.

The style block is injected after the opening brace of each graph, so a
diagram file states only its structure and whatever it overrides.

    python3 tools/figures.py
"""

from __future__ import annotations

import pathlib
import re
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = ROOT / "diagrams"
OUT = ROOT / "src" / "figures"

STYLE = """
  graph [fontname="Helvetica" fontsize=12 bgcolor="transparent" pad="0.2" nodesep="0.35" ranksep="0.45"];
  node  [fontname="Menlo" fontsize=11 shape=box style="rounded,filled" fillcolor="#eef3f7" color="#1d2733" penwidth=1.4 margin="0.12,0.06"];
  edge  [fontname="Helvetica" fontsize=10 color="#1d2733" penwidth=1.3 arrowsize=0.7];
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    count = 0
    for dot in sorted(SOURCE.glob("*.dot")):
        source = dot.read_text(encoding="utf-8")
        styled = re.sub(r"\{", "{" + STYLE, source, count=1)
        svg = subprocess.run(["dot", "-Tsvg"], input=styled.encode(), capture_output=True, check=True).stdout
        (OUT / dot.with_suffix(".svg").name).write_bytes(svg)
        count += 1
    print("rendered %d figures to %s" % (count, OUT.relative_to(ROOT)))


if __name__ == "__main__":
    main()
