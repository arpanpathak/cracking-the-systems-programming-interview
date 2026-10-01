# Build the browser and print editions of the book.
#
#   make               art, figures, animations, HTML, and PDF
#   make serve         serve the HTML edition on http://localhost:3000
#   make lint          check every figure and animation for overflowing or colliding
#                      labels, and the chapter prose for banned phrases

MDBOOK ?= mdbook
PYTHON ?= python3
PDF := build/cracking-the-systems-programming-interview.pdf

.PHONY: all art figures hand-drawn diagram-figures animations lint-figures lint-animations lint-prose lint html pdf serve clean

all: art figures animations html pdf

## The chapter plates and the cover, from tools/art.py
art:
	$(PYTHON) tools/art.py

## Every figure: the hand-drawn ones and the Graphviz ones
figures: hand-drawn diagram-figures

## The figures written by tools/draw_chNN.py
hand-drawn:
	$(PYTHON) tools/handdrawn.py

## Every diagrams/*.dot rendered to src/figures/*.svg
diagram-figures:
	$(PYTHON) tools/figures.py

## The animated GIFs, written by tools/animations.py
animations:
	$(PYTHON) tools/animations.py
	$(PYTHON) tools/anim_markup.py

## Check every figure for a label that overflows or collides
lint-figures:
	$(PYTHON) tools/lint_figures.py

## Check every animation frame for a pointer label that lands on a sentence
lint-animations:
	$(PYTHON) tools/lint_animations.py

## Check the chapter prose for banned phrases and long sentences
lint-prose:
	$(PYTHON) tools/lint_prose.py src/*.md

## Every check
lint: lint-figures lint-animations
	$(PYTHON) tools/lint_prose.py src/*.md

## The browser edition, written to book/
html:
	$(MDBOOK) build

## The print edition
pdf:
	$(PYTHON) tools/build_pdf.py --out $(PDF)

serve:
	$(MDBOOK) serve --open

clean:
	rm -rf book build
