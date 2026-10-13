# Build the browser edition of the book.
#
#   make               figures, animations, and HTML
#   make serve         serve the HTML edition on http://localhost:3000
#   make check         run the programs and compare their output with the chapters
#
# The figures need Python 3. The animations also need Pillow, NumPy, CairoSVG,
# and ffmpeg. Their output in src/figures/ is committed, so `mdbook build` and
# Python 3, which the build uses to tidy the listings, are enough to read the
# book.

MDBOOK ?= mdbook
PYTHON ?= python3

.PHONY: all art figures animations html serve check clean

all: art figures animations html

## The cover and the chapter plates, drawn by tools/art.py to src/art/*.svg
art:
	$(PYTHON) tools/art.py

## Every diagram, drawn by tools/draw_figures.py to src/figures/*.svg
figures:
	$(PYTHON) tools/draw_figures.py

## Every animation (GIF, MP4, and step list), then the <video> markup in the chapters
animations:
	$(PYTHON) tools/animations.py
	$(PYTHON) tools/anim_markup.py

## The browser edition, written to book/
html:
	$(MDBOOK) build

serve:
	$(MDBOOK) serve --open

## Every printed part of a program is complete, and every program
## still prints the output its chapter shows
check:
	$(PYTHON) tools/check_excerpts.py
	tools/check_outputs.sh

clean:
	rm -rf book
