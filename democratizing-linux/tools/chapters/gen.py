#!/usr/bin/env python3
"""Expands a chapter source into Markdown: numbers the listings and writes the includes.

    gen.py <chapter number> <source> <out.md>

@pair <program> <anchor> :: <caption>     a Go listing, then a Rust listing
@full <program>                           the two complete programs
"""
import html
import json
import re
import sys

BASE = "https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/democratizing-linux/"
chapter, source, out = sys.argv[1:4]
count, lines, seen = 0, [], set()


def listing(caption, lang, path, anchor=None):
    global count
    count += 1
    part = ":" + anchor if anchor else ""
    fence = "go" if lang == "Go" else "rust"

    caption = re.sub(r"`([^`]+)`", r"<code>\1</code>", caption)

    mascot = "gopher" if lang == "Go" else ("crab-cute" if anchor is None else "crab-happy")

    return ('<p class="listing"><img class="mascot" src="art/' + mascot + '.svg" alt=""><b>Listing %s.%d</b> %s, in %s. <a href="%s%s">%s</a></p>\n\n```%s\n{{#include ../%s%s}}\n```\n'
            % (chapter, count, caption, lang, BASE, path, path, fence, path, part))


for line in open(source).read().split("\n"):
    if line.startswith("@pair "):
        head, caption = line[6:].split(" :: ")
        program, anchor = head.split()

        # The first part of a program is preceded by its imports.
        if program not in seen:
            seen.add(program)
            go, rust = "code/go/%s/main.go" % program, "code/rust/%s/src/main.rs" % program
            lines.append(listing("The imports of `%s`" % program, "Go", go, "imports"))

            if "ANCHOR: imports" in open(rust).read():
                lines.append(listing("The imports of `%s`" % program, "Rust", rust, "imports"))

        lines.append(listing(caption, "Go", "code/go/%s/main.go" % program, anchor))
        lines.append(listing(caption, "Rust", "code/rust/%s/src/main.rs" % program, anchor))
        continue

    if line.startswith("@crab "):
        mood, body = line[6:].split(" :: ")
        lines.append('<div class="crab crab-%s">\n\n%s\n\n</div>' % (mood.strip(), body))
        continue

    if line.startswith("@full "):
        program = line[6:].strip()
        lines.append(listing("The complete `%s`" % program, "Go", "code/go/%s/main.go" % program))
        lines.append(listing("The complete `%s`" % program, "Rust", "code/rust/%s/src/main.rs" % program))
        continue

    lines.append(line)

def renumber(body):
    """Numbers the figures in the order they appear, and rewrites every reference to one."""
    labels = re.findall(r"<figcaption><b>Figure (%s\.[\w-]+)</b>" % chapter, body)
    new = {label: "%s.%d" % (chapter, k + 1) for k, label in enumerate(labels)}

    return re.sub(r"([Ff]igure) (%s\.[\w-]+)" % chapter, lambda m: m.group(1) + " " + new.get(m.group(2), m.group(2)), body)


plates = json.load(open("src/art/plates.json"))
key = "ch%02d" % int(chapter)
opener = '<img class="plate" src="art/%s.svg" alt="%s">\n\n' % (key, html.escape(plates[key], quote=True))

open(out, "w").write(opener + renumber("\n".join(lines)))
print("%s: %d listings" % (out, count))
