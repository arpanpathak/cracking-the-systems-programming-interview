#!/usr/bin/env python3
"""Expands a chapter source into Markdown: numbers the listings and figures and writes the includes.

    gen.py <chapter number> <source> <out.md>

@code <file> <part> :: <caption>     one named part of a file under code/
@full <file>                         a complete file
@out <name>                          a recorded terminal session from transcripts/<name>.txt
@crab <mood> :: <text>               a note beside a crab
@steps <prefix> :: <caption>         a picture in numbered steps, src/figures/<prefix>-NN.svg
@sim <crate>                         a link to a simulation in the repository
"""
import hashlib
import html
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
BASE = "https://github.com/arpanpathak/cracking-the-systems-programming-interview/blob/prep-v2/distributed-systems-from-the-ground-up/"
FENCE = {".rs": "rust", ".proto": "protobuf", ".toml": "toml"}
chapter, source, out = sys.argv[1:4]
count, lines, seen = 0, [], set()


def listing(caption, path, part=None):
    global count
    count += 1
    caption = re.sub(r"`([^`]+)`", r"<code>\1</code>", caption)
    mascot = "crab-cute" if part is None else "crab-happy"
    fence = FENCE[pathlib.Path(path).suffix]

    return ('<p class="listing"><img class="mascot" src="art/%s.svg" alt=""><b>Listing %s.%d</b> %s. <a href="%scode/%s">%s</a></p>\n\n```%s\n{{#include ../code/%s%s}}\n```\n'
            % (mascot, chapter, count, caption, BASE, path, path, fence, path, ":" + part if part else ""))


for line in open(source).read().split("\n"):
    if line.startswith("@code "):
        head, caption = line[6:].split(" :: ")
        path, part = head.split()

        # The first part of a file is preceded by its imports.
        if path not in seen:
            seen.add(path)

            if part != "imports" and "ANCHOR: imports" in (HERE.parent.parent / "code" / path).read_text():
                lines.append(listing("The imports of `%s`" % path, path, "imports"))

        lines.append(listing(caption, path, part))
        continue

    if line.startswith("@full "):
        path = line[6:].strip()
        lines.append(listing("The complete `%s`" % path, path))
        continue

    if line.startswith("@out "):
        lines.append("```console\n%s\n```" % (HERE / "transcripts" / (line[5:].strip() + ".txt")).read_text().rstrip("\n"))
        continue

    if line.startswith("@sim "):
        crate = line[5:].strip()
        lines.append('<div class="simulation">\n\n**Simulation in the repository.** The program '
                     '[`code/%s`](%scode/%s/src/main.rs) simulates this design. To run it, clone the repository and type '
                     '`cargo run --release -p %s` in the `code` directory.\n\n</div>' % (crate, BASE, crate, crate))
        continue

    if line.startswith("@crab "):
        mood, body = line[6:].split(" :: ")
        lines.append('<div class="crab crab-%s">\n\n%s\n\n</div>' % (mood.strip(), body))
        continue

    lines.append(line)


def renumber(body):
    """Numbers the figures in the order they appear, and rewrites every reference to one."""
    labels = re.findall(r"<figcaption><b>Figure (%s\.[\w-]+)</b>" % chapter, body)
    new = {label: "%s.%d" % (chapter, k + 1) for k, label in enumerate(labels)}

    return re.sub(r"([Ff]igure) (%s\.[\w-]+)" % chapter, lambda m: m.group(1) + " " + new.get(m.group(2), m.group(2)), body)


def mark(content):
    """A short mark of a picture's contents. It is part of the picture's address, so a
    browser that holds an older copy fetches the new one."""
    return hashlib.md5(content.encode()).hexdigest()[:8]


def figures(body):
    """Writes `@figure name :: caption` as a figure with the picture's own description as its alternative text."""
    def one(found):
        name, caption = found.group(1), found.group(2)
        svg = (HERE.parent.parent / "src" / "figures" / (name + ".svg")).read_text()
        alt = re.search(r'aria-label="([^"]*)"', svg).group(1)

        width = int(re.search(r'<svg[^>]* width="(\d+)"', svg).group(1))
        kind = ' class="wide"' if width > 600 else ""

        return ('<figure%s>\n<img src="figures/%s.svg?v=%s" alt="%s">\n<figcaption><b>Figure %s.%s</b> %s</figcaption>\n</figure>'
                % (kind, name, mark(svg), alt, chapter, name, caption))

    def stepped(found):
        prefix, caption = found.group(1), found.group(2)
        frames = sorted((HERE.parent.parent / "src" / "figures").glob(prefix + "-[0-9][0-9].svg"))
        first = frames[0].read_text()
        alt = re.search(r'aria-label="([^"]*)"', first).group(1)
        version = mark("".join(frame.read_text() for frame in frames))

        return ('<figure class="steps" data-prefix="figures/%s" data-count="%d" data-version="%s">\n<img src="figures/%s-01.svg?v=%s" alt="%s">\n'
                '<figcaption><b>Figure %s.%s</b> %s Use Next and Back to move through the %d steps.</figcaption>\n</figure>'
                % (prefix, len(frames), version, prefix, version, alt, chapter, prefix, caption, len(frames)))

    body = re.sub(r"^@steps (\S+) :: (.*)$", stepped, body, flags=re.M)

    return re.sub(r"^@figure (\S+) :: (.*)$", one, body, flags=re.M)


plates = json.load(open(HERE.parent.parent / "src" / "art" / "plates.json"))
key = "ch%02d" % int(chapter)
plate = (HERE.parent.parent / "src" / "art" / (key + ".svg")).read_text()
opener = '<img class="plate" src="art/%s.svg?v=%s" alt="%s">\n\n' % (key, mark(plate), html.escape(plates[key], quote=True))

open(out, "w").write(opener + renumber(figures("\n".join(lines))))
print("%s: %d listings" % (out, count))
