#!/usr/bin/env python3
"""Stamp crisp, publication-grade page numbers onto generated book PDFs.

Skips page 1 (front cover) and optional copyright page, then draws a subtle
editorial hairline rule and centered page number in the bottom margin.
Supports optional Roman numerals for front matter so printed page numbers match
the Table of Contents to the exact digit.
"""
import sys
from pathlib import Path
import fitz


def to_roman(n: int) -> str:
    vals = [
        (1000, "m"), (900, "cm"), (500, "d"), (400, "cd"),
        (100, "c"), (90, "xc"), (50, "l"), (40, "xl"),
        (10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i"),
    ]
    out = []
    for v, s in vals:
        while n >= v:
            out.append(s)
            n -= v
    return "".join(out)


def stamp_pdf(pdf_path: Path, skip_first: int = 1, roman_end: int = 0, arabic_start_num: int = 2):
    doc = fitz.open(pdf_path)
    total = len(doc)
    ink = (0.337, 0.376, 0.439)   # #566070 slate
    rule = (0.847, 0.871, 0.910)  # #D8DEE8 hairline

    for idx in range(skip_first, total):
        page = doc[idx]
        w, h = page.rect.width, page.rect.height
        if roman_end > 0 and idx < roman_end:
            label = to_roman(idx - skip_first + 1)
        elif roman_end > 0:
            label = str(idx - roman_end + 1)
        else:
            label = str(idx - skip_first + arabic_start_num)

        # Subtle centered footer rule + crisp 9pt page number
        y_rule = h - 28
        margin = 44
        page.draw_line(
            fitz.Point(margin, y_rule),
            fitz.Point(w - margin, y_rule),
            color=rule,
            width=0.5,
        )
        tw = fitz.get_text_length(label, fontname="helv", fontsize=9.0)
        page.insert_text(
            fitz.Point((w - tw) / 2.0, h - 15),
            label,
            fontname="helv",
            fontsize=9.0,
            color=ink,
        )

    tmp = pdf_path.with_suffix(".stamped.pdf")
    doc.save(tmp, garbage=3, deflate=True)
    doc.close()
    tmp.replace(pdf_path)
    print(f"Stamped {total - skip_first} pages in {pdf_path.name} (total={total})")


if __name__ == "__main__":
    pdf = Path(sys.argv[1])
    skip = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    roman_end = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    arabic_start = int(sys.argv[4]) if len(sys.argv) > 4 else 2
    stamp_pdf(pdf, skip_first=skip, roman_end=roman_end, arabic_start_num=arabic_start)
