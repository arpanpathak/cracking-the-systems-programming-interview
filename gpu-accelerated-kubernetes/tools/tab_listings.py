#!/usr/bin/env python3
"""Put the Go and Rust versions of a listing in 1 tabbed box.

A Go listing (its caption and its code block) followed directly by a Rust
listing becomes:

    <div class="code-tabs">
    <div class="code-tab" data-lang="Go"> ... </div>
    <div class="code-tab" data-lang="Rust"> ... </div>
    </div>

Several Go listings in a row followed by several Rust listings form 1 box with
1 tab per language. theme/tabs.js adds the buttons. Running the script twice
changes nothing, because listings already inside a box are skipped.

    python3 tools/tab_listings.py src/*.md
"""

import re
import sys

CAPTION = re.compile(r'^<p class="listing">')
FENCE = re.compile(r"^```(\w*)")


def units(lines):
    """Split a chapter into items: ("listing", lang, lines) for a caption and its code block, ("text", None, [line])
    for everything else."""
    out, k = [], 0

    while k < len(lines):
        if CAPTION.match(lines[k]):
            j = k + 1

            while j < len(lines) and lines[j].strip() == "":
                j += 1

            fence = FENCE.match(lines[j]) if j < len(lines) else None

            if fence:
                end = j + 1

                while not lines[end].startswith("```"):
                    end += 1

                out.append(("listing", fence.group(1), lines[k:end + 1]))
                k = end + 1
                continue

        out.append(("text", None, [lines[k]]))
        k += 1

    return out


def panel(lang, items):
    body = []

    for item in items:
        body += [*item, ""]

    return [f'<div class="code-tab" data-lang="{lang}">', "", *body, "</div>"]


def wrap(text):
    if 'class="code-tabs"' in text:
        return text, 0

    items, out, boxes, k = units(text.split("\n")), [], 0, 0

    def run(start, lang):
        """The listings of `lang` from `start`, allowing blank lines between them, and the index after the run."""
        found, j, last = [], start, start

        while j < len(items):
            kind, item_lang, body = items[j]

            if kind == "listing" and item_lang == lang:
                found.append(body)
                j += 1
                last = j
            elif kind == "text" and body[0].strip() == "":
                j += 1
            else:
                break

        return found, last

    while k < len(items):
        go, after_go = run(k, "go")
        rust, after_rust = run(after_go, "rust") if go else ([], k)

        if go and rust:
            out += ["", '<div class="code-tabs">', "", *panel("Go", go), "", *panel("Rust", rust), "", "</div>", ""]
            boxes += 1
            k = after_rust
        else:
            out += items[k][2]
            k += 1

    return "\n".join(out), boxes


def main(paths):
    for path in paths:
        text = open(path).read()
        new, boxes = wrap(text)

        if new != text:
            open(path, "w").write(new)

        print(f"{path}: {boxes} tabbed listing(s)")


if __name__ == "__main__":
    main(sys.argv[1:])
