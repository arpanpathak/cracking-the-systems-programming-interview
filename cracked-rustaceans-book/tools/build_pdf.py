#!/usr/bin/env python3
"""Build the printed edition as a PDF.

Reads `src/SUMMARY.md` for the order of the book, renders each chapter to HTML
with Python-Markdown and Pygments, assembles one document, and paginates it with
WeasyPrint. Chapter links of the form `chapter.md#anchor` become fragment links,
so that the stylesheet can resolve them to page numbers in the contents page and
in the index.

    python3 tools/build_pdf.py          # writes build/cracked-rustaceans.pdf
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
TITLE_LINES = ("Coding Interviews for", "Cracked Rustaceans")
TITLE = " ".join(TITLE_LINES)
SUBTITLE = "A Zero-Cost Abstraction Obsession Anatomy"
AUTHOR = "Arpan Pathak"

EXTENSIONS = ["extra", "codehilite", "sane_lists", "toc"]
CONFIG = {"codehilite": {"guess_lang": False, "css_class": "highlight"}}

SUMMARY_LINK = re.compile(
    r"^(?P<marker>\s*-\s+)?\[(?P<title>[^\]]+)\]\((?P<href>[^)]+)\)"
)
CHAPTER_LINK = re.compile(r'href="(?P<path>[^"#]*?)\.md(?:#(?P<fragment>[^"]*))?"')
REPO_LINK = re.compile(r'href="\.\./\.\./(rust-interview-lab/[^"]+)"')
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
FIRST_HEADING = re.compile(r'<h1[^>]*id="(?P<id>[^"]+)"')
H1 = re.compile(r"<h1(?P<attrs>[^>]*)>(?P<body>.*?)</h1>", re.DOTALL)
H2 = re.compile(r"<h2[^>]*>(?P<body>.*?)</h2>", re.DOTALL)
TAGS = re.compile(r"<[^>]+>")

CALLOUTS = (
    ("Time and Space Complexity", "callout-complexity"),
    ("Limitations", "callout-limitations"),
)


def plain(fragment: str) -> str:
    """The text of a small HTML fragment, with entities resolved."""
    return html.unescape(TAGS.sub("", fragment)).strip()


def decorate_chapter(body: str, title: str) -> str:
    """Add a chapter opener: a number badge, the title, and an 'In this chapter' box."""
    match = H1.search(body)
    numbered = re.match(r"\s*(\d+)\.\s+(.*)", title)
    if match is None or numbered is None:
        return body

    number, name = numbered.group(1), numbered.group(2)
    sections = [plain(item) for item in H2.findall(body)]
    listed = [s for s in sections if s not in {"Summary", "References"}]
    items = "".join("<li>%s</li>" % html.escape(s) for s in listed[:6])

    opener = (
        '<div class="chapter-opener">'
        '<p class="chapter-kicker">Chapter %s</p>'
        "<h1%s>%s</h1>"
        '<div class="in-this-chapter">'
        '<p class="box-title">In this chapter</p><ul>%s</ul>'
        "</div></div>"
    ) % (html.escape(number), match.group("attrs"), html.escape(name), items)

    return body[: match.start()] + opener + body[match.end() :]


def wrap_section(body: str, heading: str, klass: str) -> str:
    """Put one section inside a tinted callout box."""
    pattern = re.compile(
        r"(<h2[^>]*>\s*%s\s*</h2>)(.*?)(?=<h2|\Z)" % re.escape(heading),
        re.DOTALL,
    )
    return pattern.sub(
        lambda m: '<div class="callout %s">%s%s</div>' % (klass, m.group(1), m.group(2)),
        body,
        count=1,
    )


class Page:
    """One row of the summary: a part divider, a front-matter page, or a chapter."""

    def __init__(self, kind: str, title: str, path: pathlib.Path | None) -> None:
        self.kind = kind
        self.title = title
        self.path = path
        self.anchor = ""
        self.body = ""


def slugify(text: str) -> str:
    """The identifier that Markdown derives from a heading."""
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"\s+", "-", slug.strip())


def read_summary(path: pathlib.Path) -> list[Page]:
    """Read the summary into pages, in order."""
    pages: list[Page] = []

    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.strip() == "# Summary":
            continue

        if line.startswith("#"):
            pages.append(Page("part", line.lstrip("#").strip(), None))
            continue

        entry = SUMMARY_LINK.match(line)
        if entry is None:
            continue

        # A prefix chapter (front matter) is written without a list marker.
        kind = "chapter" if entry.group("marker") else "front"
        pages.append(Page(kind, entry.group("title").strip(), SRC / entry.group("href")))

    return pages


def render_page(page: Page) -> None:
    """Render one page's Markdown and record the identifier of its first heading."""
    assert page.path is not None

    if not page.path.is_file():
        raise SystemExit("missing chapter: %s" % page.path.relative_to(ROOT))

    source = HTML_COMMENT.sub("", page.path.read_text(encoding="utf-8"))
    page.body = markdown.Markdown(
        extensions=EXTENSIONS, extension_configs=CONFIG, output_format="html5"
    ).convert(source)

    if page.kind == "chapter":
        page.body = decorate_chapter(page.body, page.title)
        for heading, klass in CALLOUTS:
            page.body = wrap_section(page.body, heading, klass)

    heading = FIRST_HEADING.search(page.body)
    page.anchor = heading.group("id") if heading else slugify(page.title)


def style_index(body: str) -> str:
    """Mark the links of the index page so the stylesheet prints page numbers."""
    return body.replace('<a href="#', '<a class="ixlink" href="#')


def rewrite_links(body: str, anchors: dict[str, str]) -> str:
    """Turn `chapter.md#anchor` links into fragment links."""

    def replace(match: re.Match) -> str:
        name = pathlib.Path(match.group("path")).name
        if name not in anchors:
            return match.group(0)
        return 'href="#%s"' % (match.group("fragment") or anchors[name])

    return CHAPTER_LINK.sub(replace, body)


def build_contents(pages: list[Page]) -> list[str]:
    """Build the contents page, one line per part and one per chapter."""
    lines = ['<div class="contents">', "<h1>Contents</h1>"]

    for page in pages:
        if page.kind == "part":
            lines.append('<p class="contents-part">%s</p>' % html.escape(page.title))
            lines.append(
                '<p class="contents-line">'
                '<a class="entry" href="#%s">Part page</a></p>' % slugify(page.title)
            )
            continue

        if page.path is not None and page.path.name.endswith("-title.md"):
            # The typeset title page is generated below and is not listed in its
            # own table of contents.
            continue

        style = "front-line" if page.kind == "front" else ""
        lines.append(
            '<p class="contents-line %s">'
            '<a class="entry" href="#%s">%s</a></p>'
            % (style, page.anchor, html.escape(page.title))
        )

    lines.append("</div>")
    return lines


def build_title_page() -> list[str]:
    """Build the typeset cover."""
    return [
        '<div class="cover">',
        '<div class="cover-band">'
        '<p class="cover-kicker">Rust · Systems Programming</p></div>',
        '<div class="cover-body">',
        '<p class="cover-title">%s</p>'
        % "<br>".join(html.escape(line) for line in TITLE_LINES),
        '<p class="cover-subtitle">%s</p>' % html.escape(SUBTITLE),
        '<hr class="cover-rule">',
        '<p class="cover-author">%s</p>' % html.escape(AUTHOR),
        "</div>",
        '<p class="cover-foot">rust-interview-lab</p>',
        "</div>",
    ]


def build_document(pages: list[Page]) -> str:
    """Assemble the whole book as one HTML document."""
    anchors = {page.path.name: page.anchor for page in pages if page.path is not None}

    parts: list[str] = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        "<title>%s: %s</title>" % (html.escape(TITLE), html.escape(SUBTITLE)),
        '<meta name="author" content="%s">' % html.escape(AUTHOR),
        '<meta name="description" content="%s">' % html.escape(SUBTITLE),
        "<style>%s</style>"
        % HtmlFormatter(style="friendly").get_style_defs(".highlight"),
        "</head>",
        "<body>",
    ]

    parts += build_title_page()
    parts += build_contents(pages)

    for page in pages:
        if page.path is not None and page.path.name.endswith("-title.md"):
            continue

        if page.kind == "part":
            parts.append(
                '<div class="part-divider" id="%s">'
                '<p class="part-title">%s</p></div>'
                % (slugify(page.title), html.escape(page.title))
            )
            continue

        body = rewrite_links(page.body, anchors)
        # A relative repository link is resolved against the book directory while
        # the chapter file sits one level deeper, so point it at the real file.
        body = REPO_LINK.sub(
            lambda match: 'href="file://%s"' % (ROOT.parent / match.group(1)), body
        )
        if page.path is not None and page.path.name == "index.md":
            body = style_index(body)

        parts.append(body)

    parts += ["</body>", "</html>"]
    return "\n".join(parts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--summary",
        type=pathlib.Path,
        default=SRC / "SUMMARY.md",
        help="the summary that defines the order and contents of the book",
    )
    parser.add_argument(
        "--out",
        type=pathlib.Path,
        default=ROOT / "build" / "cracked-rustaceans.pdf",
        help="path of the PDF to write",
    )
    arguments = parser.parse_args()

    pages = read_summary(arguments.summary)
    for page in pages:
        if page.path is not None:
            render_page(page)

    document = build_document(pages)
    stylesheet = CSS(filename=str(ROOT / "tools" / "print.css"))

    arguments.out.parent.mkdir(parents=True, exist_ok=True)
    rendered = HTML(string=document, base_url=str(ROOT))
    pages_count = len(rendered.render(stylesheets=[stylesheet]).pages)
    rendered.write_pdf(target=str(arguments.out), stylesheets=[stylesheet])

    print("wrote %s (%d pages)" % (arguments.out, pages_count))
    return 0


if __name__ == "__main__":
    sys.exit(main())
