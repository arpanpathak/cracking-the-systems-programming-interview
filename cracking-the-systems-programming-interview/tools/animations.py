#!/usr/bin/env python3
"""Every animation in the book, written to src/figures/.

Each module below holds the animations for one or more chapters, drawn with
`motion`. `render` writes three files per animation: a GIF, an MP4 of the same
frames, and a JSON step list that the HTML book uses for its step buttons.

    python3 tools/animations.py              # every animation
    python3 tools/animations.py two-sum bfs  # some of them

After a render, `python3 tools/anim_markup.py` points the chapters at the new
videos. `make animations` runs both.
"""

import sys

import anim_async
import anim_ch01
import anim_ch02
import anim_ch03
import anim_ch04
import anim_ch05
import anim_ch06
import anim_ch09
import anim_ch09_ops
import anim_ch09_more
import anim_ch11
import anim_ch12
import anim_ch13
import anim_ch13_19
import anim_ch07
import anim_ch08
import anim_ch10
import anim_ch10_more
import anim_ch10_trace
import anim_ch15
import anim_ch17
import anim_ch18
import anim_http
import anim_kernel
import anim_sockets
from motion import OUT

MOTION = {}
for module in (anim_ch01, anim_ch02, anim_ch03, anim_ch04, anim_ch07, anim_ch05, anim_ch06, anim_ch09, anim_ch09_ops, anim_ch09_more, anim_ch11, anim_ch12, anim_ch13, anim_ch13_19, anim_ch08, anim_ch10, anim_ch10_more, anim_ch10_trace, anim_ch15, anim_ch17, anim_ch18,
               anim_sockets, anim_http, anim_async, anim_kernel):
    MOTION.update(module.BUILDERS)


def main(argv):
    names = argv or list(MOTION)
    unknown = [n for n in names if n not in MOTION]
    if unknown:
        print("unknown animation(s): %s" % ", ".join(unknown), file=sys.stderr)
        print("available: %s" % ", ".join(MOTION), file=sys.stderr)
        return 2
    for name in names:
        MOTION[name]()
        print("  %s" % name)
    print("wrote %d animations to %s" % (len(names), OUT.name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
