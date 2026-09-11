# Build both editions.

MDBOOK ?= mdbook
PYTHON ?= python3

.PHONY: all html pdf clean

all: html pdf

## The browser edition, written to book/
html:
	$(MDBOOK) build

## The printed edition, written to build/cracked-rustaceans.pdf
pdf:
	$(PYTHON) tools/build_pdf.py

clean:
	rm -rf book build
