#!/usr/bin/env python3
"""Render `benchmarking-report.md` as a PDF.

    python3 benchmarking_examples/build_report_pdf.py

Markdown is rendered by Python-Markdown with Pygments for the code blocks, the
result is wrapped in one HTML document, and WeasyPrint paginates it using
`report.css`. Requires `markdown`, `pygments`, and `weasyprint`.
"""

from __future__ import annotations

import pathlib
import sys

import markdown
from pygments.formatters import HtmlFormatter
from weasyprint import CSS, HTML

HERE = pathlib.Path(__file__).resolve().parent
SOURCE = HERE / "benchmarking-report.md"
STYLESHEET = HERE / "report.css"
OUTPUT = HERE / "benchmarking-report.pdf"
TITLE = "A Comparative Study of LRU Cache Storage Strategies and Singly Linked List Deallocation"

EXTENSIONS = ["extra", "codehilite", "sane_lists"]
CONFIG = {"codehilite": {"guess_lang": False, "css_class": "highlight"}}

# The title block is written as ordinary Markdown paragraphs. These identifiers
# let the stylesheet centre them and distinguish them from body text.
TITLE_BLOCK = (
    ('<p><strong>Arpan Pathak</strong></p>', '<p id="title-author"><strong>Arpan Pathak</strong></p>'),
    ('<p>11 September 2026</p>', '<p id="title-date">11 September 2026</p>'),
    (
        '<p><strong>Keywords:</strong>',
        '<p id="title-keywords"><strong>Keywords:</strong>',
    ),
)


def build_document() -> str:
    """The whole report as one HTML document."""
    body = markdown.markdown(
        SOURCE.read_text(encoding="utf-8"), extensions=EXTENSIONS, extension_configs=CONFIG
    )

    for old, new in TITLE_BLOCK:
        body = body.replace(old, new, 1)

    style = HtmlFormatter(style="friendly").get_style_defs(".highlight")
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '<meta charset="utf-8">',
            f"<title>{TITLE}</title>",
            '<meta name="author" content="Arpan Pathak">',
            f"<style>{style}</style>",
            "</head>",
            "<body>",
            body,
            "</body>",
            "</html>",
        ]
    )


def main() -> int:
    if not SOURCE.exists():
        print(f"missing {SOURCE}", file=sys.stderr)
        return 1

    document = build_document()
    stylesheet = CSS(filename=str(STYLESHEET))
    rendered = HTML(string=document, base_url=str(HERE))
    page_count = len(rendered.render(stylesheets=[stylesheet]).pages)
    rendered.write_pdf(target=str(OUTPUT), stylesheets=[stylesheet])

    print(f"wrote {OUTPUT.name} ({page_count} pages)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
