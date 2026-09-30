#!/usr/bin/env python3
"""Build the print edition as a PDF.

The order of the book comes from src/SUMMARY.md, the same file mdbook reads.
Each page is Markdown with `{{#include path[:start[:end]]}}` directives; they
are expanded here exactly as mdbook expands them, so every listing in the PDF is
the source file byte for byte. Python-Markdown and Pygments render the HTML, and
WeasyPrint paginates it with tools/print.css.

    python3 tools/build_pdf.py --out build/cracking-the-systems-programming-interview.pdf
"""

from __future__ import annotations

import argparse
import html
import pathlib
import re
import sys

import markdown
from pygments.formatters import HtmlFormatter
from weasyprint import CSS, HTML

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

TITLE = "Cracking the Systems Programming Interview"
SUBTITLE = "Rust from data structures to the kernel boundary"
AUTHOR = "Arpan Pathak"
REPOSITORY = "https://github.com/arpanpathak/cracking-the-systems-programming-interview"

EXTENSIONS = ["extra", "codehilite", "sane_lists", "toc", "md_in_html"]
CONFIG = {"codehilite": {"guess_lang": False, "css_class": "highlight"}}

SUMMARY_LINK = re.compile(r"^(?P<marker>\s*-\s+)?\[(?P<title>[^\]]+)\]\((?P<href>[^)]+)\)")
INCLUDE = re.compile(r"\{\{#include\s+(?P<path>[^:}\s]+)(?::(?P<start>\d*))?(?::(?P<end>\d*))?\s*\}\}")
CHAPTER_LINK = re.compile(r'href="(?P<path>[^"#:]*?)\.md(?:#(?P<fragment>[^"]*))?"')
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
FIRST_HEADING = re.compile(r'<h1[^>]*id="(?P<id>[^"]+)"')


class Page:
    """One row of the summary: a part divider, front or back matter, or a chapter."""

    def __init__(self, kind: str, title: str, path: pathlib.Path | None) -> None:
        self.kind = kind
        self.title = title
        self.path = path
        self.anchor = ""
        self.body = ""


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"\s+", "-", slug.strip())


def read_summary(path: pathlib.Path) -> list[Page]:
    pages: list[Page] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped == "# Summary" or stripped == "---":
            continue
        if stripped.startswith("#"):
            pages.append(Page("part", stripped.lstrip("#").strip(), None))
            continue
        entry = SUMMARY_LINK.match(line)
        if entry is None:
            continue
        kind = "chapter" if entry.group("marker") else "front"
        pages.append(Page(kind, entry.group("title").strip(), SRC / entry.group("href")))
    return pages


def expand_includes(source: str, base: pathlib.Path) -> str:
    """Replace each include directive with the named lines of the named file.

    mdbook numbers lines from 1, and `file:a:b` takes lines a through b, `file:a:`
    takes line a to the end, and `file::b` takes the first b lines.
    """

    def replace(match: re.Match) -> str:
        target = (base / match.group("path")).resolve()
        if not target.is_file():
            raise SystemExit("include not found: %s" % match.group("path"))
        lines = target.read_text(encoding="utf-8").split("\n")
        if lines and lines[-1] == "":
            lines.pop()
        start = int(match.group("start")) if match.group("start") else 1
        end = int(match.group("end")) if match.group("end") else len(lines)
        return "\n".join(lines[start - 1 : end])

    return INCLUDE.sub(replace, source)


def render_page(page: Page) -> None:
    assert page.path is not None
    if not page.path.is_file():
        raise SystemExit("missing page: %s" % page.path.relative_to(ROOT))
    source = HTML_COMMENT.sub("", page.path.read_text(encoding="utf-8"))
    source = expand_includes(source, page.path.parent)
    page.body = markdown.Markdown(
        extensions=EXTENSIONS, extension_configs=CONFIG, output_format="html5"
    ).convert(source)
    heading = FIRST_HEADING.search(page.body)
    page.anchor = heading.group("id") if heading else slugify(page.title)


def rewrite_links(body: str, anchors: dict[str, str]) -> str:
    """Turn `chapter.md#anchor` links into in-document fragment links."""

    def replace(match: re.Match) -> str:
        name = pathlib.Path(match.group("path")).name + ".md"
        if name not in anchors:
            return match.group(0)
        return 'href="#%s"' % (match.group("fragment") or anchors[name])

    return CHAPTER_LINK.sub(replace, body)


def contents(pages: list[Page]) -> list[str]:
    lines = ['<nav class="contents">', "<h1 class=\"contents-title\">Contents</h1>"]
    number = 0
    for page in pages:
        if page.kind == "part":
            lines.append('<p class="toc-part"><a href="#%s">%s</a></p>' % (slugify(page.title), html.escape(page.title)))
        elif page.path is not None and page.path.name != "cover.md":
            style = "toc-front" if page.kind == "front" else "toc-chapter"
            title = html.escape(page.title)
            if page.kind == "chapter":
                number += 1
                title = '<span class="toc-number">%d</span>%s' % (number, title)
            lines.append('<p class="%s"><a href="#%s">%s</a></p>' % (style, page.anchor, title))
    lines.append("</nav>")
    return lines


def front_pages() -> list[str]:
    return [
        '<section class="cover-page"><img src="art/cover.png" alt="Cover"></section>',
        '<section class="title-page">',
        '<p class="title-main">%s</p>' % html.escape(TITLE),
        '<p class="title-sub">%s</p>' % html.escape(SUBTITLE),
        '<p class="title-author">%s</p>' % html.escape(AUTHOR),
        '<p class="title-repo"><a href="%s">%s</a></p>' % (REPOSITORY, REPOSITORY.removeprefix("https://")),
        "</section>",
    ]


def build_document(pages: list[Page]) -> str:
    anchors = {page.path.name: page.anchor for page in pages if page.path is not None}
    parts = [
        "<!doctype html>",
        '<html lang="en"><head><meta charset="utf-8">',
        "<title>%s</title>" % html.escape(TITLE),
        '<meta name="author" content="%s">' % html.escape(AUTHOR),
        '<meta name="description" content="%s">' % html.escape(SUBTITLE),
        "<style>%s</style>" % HtmlFormatter(style="friendly").get_style_defs(".highlight"),
        "</head><body>",
    ]
    parts += front_pages()
    parts += contents(pages)
    for page in pages:
        if page.kind == "part":
            label, _, name = page.title.partition(":")
            parts.append(
                '<section class="part-divider" id="%s"><p class="part-label">%s</p>'
                '<p class="part-name">%s</p></section>'
                % (slugify(page.title), html.escape(label.strip()), html.escape(name.strip()))
            )
            continue
        if page.path is not None and page.path.name == "cover.md":
            continue
        klass = "chapter" if page.kind == "chapter" else "front-matter"
        parts.append('<section class="%s">%s</section>' % (klass, rewrite_links(page.body, anchors)))
    parts += ["</body></html>"]
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=pathlib.Path,
                        default=ROOT / "build" / "cracking-the-systems-programming-interview.pdf")
    parser.add_argument("--html", type=pathlib.Path, help="also write the assembled HTML here")
    arguments = parser.parse_args()

    pages = read_summary(SRC / "SUMMARY.md")
    for page in pages:
        if page.path is not None:
            render_page(page)

    document = build_document(pages)
    if arguments.html:
        arguments.html.write_text(document, encoding="utf-8")

    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    stylesheet = CSS(filename=str(ROOT / "tools" / "print.css"))
    rendered = HTML(string=document, base_url=str(SRC) + "/").render(stylesheets=[stylesheet])
    rendered.write_pdf(target=str(arguments.out))
    print("wrote %s (%d pages)" % (arguments.out, len(rendered.pages)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
