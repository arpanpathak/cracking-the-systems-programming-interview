# Build the browser edition of the book.
#
#   make               art, figures, chapters and HTML
#   make pdf           the PDF edition, with the clickable Index and Subject Index
#   make serve         serve the HTML edition on http://localhost:3000
#   make check         check the printed parts of the programs, and run the simulations
#
# The art and the figures need Python 3. Their output in src/ is committed, so
# `mdbook build` and Python 3 are enough to read the book.

MDBOOK ?= mdbook
PYTHON ?= python3

.PHONY: all m3-plates m3-figures art figures legacy-chapters html pdf serve check clean

all: m3-plates m3-figures html

## Programmatic Material Design 3 SVG chapter plates, written to src/art/ch*-plate.svg
m3-plates:
	$(PYTHON) tools/draw_m3_plates.py

## Material Design 3 light+dark SVG diagrams, written to src/figures/m3/
m3-figures:
	$(PYTHON) tools/draw_m3_figures.py

## Legacy cover and chapter plates, drawn by tools/art.py to src/art/*.svg
art:
	$(PYTHON) tools/art.py

## Legacy diagrams, drawn by tools/draw_figures.py to src/figures/*.svg
figures:
	$(PYTHON) tools/draw_figures.py

## Legacy chapter generator (deprecated: src/*.md is now the direct source of truth)
legacy-chapters:
	tools/chapters/build.sh

## The browser edition, written to book/
html:
	$(MDBOOK) build

## The PDF edition, written to Distributed-Systems-from-the-Ground-Up.pdf.
## Needs Google Chrome, Ghostscript and PyMuPDF; takes about ten minutes.
pdf: html
	$(PYTHON) tools/build_pdf.py

serve:
	$(MDBOOK) serve --open

## Every printed part of a program is complete, the code passes clippy, and
## every simulation still prints the output its chapter shows
check:
	$(PYTHON) tools/check_excerpts.py
	cd code && cargo clippy -q --all-targets -- -D warnings
	tools/check_outputs.sh

clean:
	rm -rf book
