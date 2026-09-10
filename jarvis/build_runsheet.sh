#!/usr/bin/env bash
# Render QUEST_RUNSHEET.md to a printable A4 PDF.
#
# pandoc for markdown → HTML, Chrome headless for HTML → PDF. Chrome rather
# than pandoc's own PDF path because that needs a LaTeX install, and this only
# needs a browser that is already on the machine.
#
#   ./build_runsheet.sh [output.pdf]
#
# Requires: pandoc (brew install pandoc) and Google Chrome.
set -euo pipefail

cd "$(dirname "$0")"
OUT="${1:-Elena-Hunt-Run-Sheet.pdf}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
[ -x "$CHROME" ] || { echo "Chrome not found at $CHROME" >&2; exit 1; }
command -v pandoc >/dev/null || { echo "pandoc not installed" >&2; exit 1; }

# -V pagetitle rather than --metadata title: the latter injects a second <h1>
# on top of the document's own masthead.
pandoc QUEST_RUNSHEET.md -f gfm -t html5 -s \
  -V pagetitle="V · E — Six Hundred Years Waiting" \
  -c "$PWD/runsheet.css" \
  -o "$TMP/runsheet.html"

"$CHROME" --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf="$OUT" "file://$TMP/runsheet.html" 2>/dev/null

echo "wrote $OUT"
