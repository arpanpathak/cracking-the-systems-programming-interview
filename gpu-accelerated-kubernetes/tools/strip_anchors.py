#!/usr/bin/env python3
"""An mdBook preprocessor that removes anchor comments from printed listings.

The chapters print parts of each program by name: a source file marks a part
with `// ANCHOR: name` and `// ANCHOR_END: name`, and a chapter includes it
with `{{#include file:name}}`. mdBook removes those comment lines from a named
part but leaves them in a listing of the whole file. This preprocessor runs
after the includes are resolved and removes the lines that remain, along with
blank lines at the start and the end of a listing.

book.toml registers it as `[preprocessor.strip-anchors]`.
"""
import json
import re
import sys

ANCHOR = re.compile(r"^[ \t]*(//|#)[ \t]*ANCHOR(_END)?:.*\n", re.M)
# A named part often ends with the blank line that separates it from the next
# declaration. This matches such blank lines in front of a closing code fence.
TRAILING_BLANK = re.compile(r"\n(?:[ \t]*\n)+(```[ \t]*(?:\n|$))")
# The same for blank lines straight after an opening fence.
LEADING_BLANK = re.compile(r"(^```\w[^\n]*\n)(?:[ \t]*\n)+", re.M)


def strip(node):
    """Removes anchor lines from every chapter under `node`."""

    if isinstance(node, dict):
        if isinstance(node.get("content"), str):
            content = ANCHOR.sub("", node["content"])
            node["content"] = LEADING_BLANK.sub(r"\1", TRAILING_BLANK.sub(r"\n\1", content))

        for value in node.values():
            strip(value)
    elif isinstance(node, list):
        for value in node:
            strip(value)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "supports":
        sys.exit(0)

    _context, book = json.load(sys.stdin)
    strip(book)
    json.dump(book, sys.stdout)
