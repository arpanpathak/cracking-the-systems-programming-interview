# Build the browser edition of the book.
#
#   make               art, figures, chapters and HTML
#   make serve         serve the HTML edition on http://localhost:3000
#   make check         check the printed parts of the programs, and run the simulations
#
# The art and the figures need Python 3. Their output in src/ is committed, so
# `mdbook build` and Python 3 are enough to read the book.

MDBOOK ?= mdbook
PYTHON ?= python3

.PHONY: all art figures chapters html serve check clean

all: art figures chapters html

## The cover and the chapter plates, drawn by tools/art.py to src/art/*.svg
art:
	$(PYTHON) tools/art.py

## Every diagram, drawn by tools/draw_figures.py to src/figures/*.svg
figures:
	$(PYTHON) tools/draw_figures.py

## The chapters, expanded from tools/chapters/*.txt to src/*.md
chapters:
	tools/chapters/build.sh

## The browser edition, written to book/
html:
	$(MDBOOK) build

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
