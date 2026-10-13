#!/usr/bin/env python3
"""Checks that every named part of a program is complete on its own.

A chapter prints the lines between `// ANCHOR: name` and `// ANCHOR_END: name`.
A part that opens a brace, bracket or parenthesis and does not close it, or
closes one it did not open, reads as broken code on the page. This reports
every such part and exits with status 1 if it finds any.

    python3 tools/check_excerpts.py
"""
import pathlib
import re
import sys

CODE = pathlib.Path(__file__).resolve().parent.parent / "code"
PAIRS = ("{}", "()", "[]")


def bare(line):
    """The line without its comment, string literals and character literals."""
    line = re.sub(r'"(\\.|[^"\\])*"', '""', line)
    line = re.sub(r"`[^`]*`", "``", line)
    line = re.sub(r"'(\\.|[^'\\])'", "''", line)

    return re.sub(r"//.*", "", line)


def main():
    problems = 0
    sources = [p for ext in ("*.go", "*.rs") for p in CODE.rglob(ext) if "target" not in p.parts]

    for path in sorted(sources):
        lines = path.read_text().split("\n")
        starts = {}

        for number, line in enumerate(lines):
            if found := re.match(r"\s*// ANCHOR: (\S+)", line):
                starts[found.group(1)] = number
            elif found := re.match(r"\s*// ANCHOR_END: (\S+)", line):
                name = found.group(1)
                body = "\n".join(bare(l) for l in lines[starts[name] + 1:number] if "ANCHOR" not in l)

                for opening, closing in PAIRS:
                    balance = body.count(opening) - body.count(closing)

                    if balance:
                        problems += 1
                        print("%s: part %r has %+d unmatched %r" % (path.relative_to(CODE), name, balance, opening))

    print("%d part(s) with unmatched brackets" % problems)

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
