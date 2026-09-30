#!/usr/bin/env python3
"""Check every animation frame for a label that overflows or collides.

The still figures are checked by `tools/lint_figures.py`. The animations have the
same problem in different clothes: a pointer label that lands on the step line,
a counter row that runs off the frame, a caption that reaches into the note. This
runs each animation builder, captures its frames, and checks every frame with the
same rules.

It also runs each builder twice. An animation lays out its frames more than once
while the canvas height settles, so a builder that accumulates state in a closure
prints the second pass on top of the first. The two passes are compared frame by
frame, and any difference is reported.

    python3 tools/lint_animations.py             # every animation
    python3 tools/lint_animations.py kmp-search  # one of them
"""

from __future__ import annotations

import pathlib
import sys
import tempfile

import animlib  # noqa: F401  (sets the type scale before any frame is built)
import lint_figures
import animations
from svgkit import Animation

ROOT = pathlib.Path(__file__).resolve().parent.parent


def capture(builder):
    """Run one builder and return the `Figure` frames it would have saved."""
    frames = []
    original = Animation.save

    def spy(self, path, width=None, colors=None):
        frames.extend(self.frames)

    Animation.save = spy
    try:
        builder()
    finally:
        Animation.save = original
    return frames


def repeatable(builder):
    """Run a builder twice and report any frame that came out differently."""
    first, second = capture(builder), capture(builder)
    if len(first) != len(second):
        return ["the two runs made %d and %d frames" % (len(first), len(second))]
    problems = []
    for i, (a, b) in enumerate(zip(first, second)):
        if a.svg() != b.svg():
            problems.append("frame %d differs between two runs of the builder" % i)
    return problems


def main(argv):
    names = argv or list(animations.BUILDERS)
    unknown = [n for n in names if n not in animations.BUILDERS]
    if unknown:
        print("unknown animation(s): %s" % ", ".join(unknown), file=sys.stderr)
        return 2

    flagged = findings = 0
    with tempfile.TemporaryDirectory() as tmp:
        for name in names:
            problems = repeatable(animations.BUILDERS[name])
            for i, frame in enumerate(capture(animations.BUILDERS[name])):
                path = pathlib.Path(tmp) / ("%s-%02d.svg" % (name, i))
                frame.save(str(path))
                for problem in lint_figures.check(path):
                    problems.append("frame %d: %s" % (i, problem))
            if problems:
                flagged += 1
                findings += len(problems)
                print(name)
                for problem in sorted(set(problems)):
                    print("    %s" % problem)
    print("\n%d/%d animations flagged, %d findings" % (flagged, len(names), findings))
    return 1 if flagged else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
