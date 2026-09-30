#!/usr/bin/env python3
"""Run every tools/draw_chNN.py so its figures are written to src/figures/.

The chapter scripts hold their layout as top-level code, so this driver runs
each one in turn from the book root, which is where their relative
`OUT = "src/figures/"` resolves.

    python3 tools/handdrawn.py           # every chapter
    python3 tools/handdrawn.py ch12      # one chapter
"""

from __future__ import annotations

import os
import pathlib
import runpy
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOOLS = ROOT / "tools"


def main(argv: list[str]) -> int:
    if argv:
        scripts = [TOOLS / ("draw_%s.py" % name) for name in argv]
        missing = [s for s in scripts if not s.exists()]
        if missing:
            print("no such script: %s" % ", ".join(str(m) for m in missing), file=sys.stderr)
            return 2
    else:
        scripts = sorted(TOOLS.glob("draw_ch*.py"))

    sys.path.insert(0, str(TOOLS))
    os.chdir(ROOT)
    for script in scripts:
        runpy.run_path(str(script), run_name="__main__")
        print("  %s" % script.name)
    print("ran %d chapter scripts" % len(scripts))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
