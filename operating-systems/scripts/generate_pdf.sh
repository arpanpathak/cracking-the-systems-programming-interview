#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

echo "==> Building mdbook..."
mdbook build

echo "==> Pre-highlighting print.html for high-contrast print..."
node scripts/pre_highlight.js

echo "==> Generating PDF with Headless Chrome..."
CHROME_BIN="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
OUTPUT_PDF="$REPO_DIR/Operating-Systems-A-Hands-On-Approach.pdf"

"$CHROME_BIN" \
  --headless=new \
  --disable-gpu \
  --run-all-compositor-stages-before-draw \
  --no-pdf-header-footer \
  --print-background \
  --print-to-pdf="$OUTPUT_PDF" \
  "file://$REPO_DIR/book/print.html"

echo "==> Stamping page numbers..."
python3 scripts/stamp_page_numbers.py "$OUTPUT_PDF" 1 0 2

echo "==> Successfully generated $OUTPUT_PDF"
ls -lh "$OUTPUT_PDF"
