#!/usr/bin/env bash
#
# regenerate-diagrams.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOC="$SCRIPT_DIR/technical-specifications.md"
OUT_DIR="$SCRIPT_DIR/technical-specifications-diagrams"

SCALE="${SCALE:-2}"
BACKGROUND="${BACKGROUND:-white}"

DIAGRAMS=(
  flowintel-technical-layered-architecture       # 2.1.1  Layered architecture
  flowintel-technical-class-identity             # 2.2.1a Class: identity and access
  flowintel-technical-class-case-management      # 2.2.1b Class: case management
  flowintel-technical-class-templating           # 2.2.1c Class: templating
  flowintel-technical-class-classification       # 2.2.1d Class: classification
  flowintel-technical-class-integrations         # 2.2.1e Class: integrations
  flowintel-technical-class-misp-objects         # 2.2.1f Class: MISP objects
  flowintel-technical-object-diagram             # 2.2.2  Object diagram
  flowintel-technical-component-diagram          # 2.2.3  Component diagram
  flowintel-technical-use-case-diagram           # 2.3.1  Use-case diagram
  flowintel-technical-sequence-generic-request   # 2.3.2  Sequence: generic request
  flowintel-technical-sequence-create-user       # 2.3.2  Sequence: create a user
  flowintel-technical-collaboration-create-user  # 2.3.3  Collaboration diagram
  flowintel-technical-statechart-task-status     # 2.3.4  Statechart: task status
  flowintel-technical-activity-workflow          # 2.3.5  Activity diagram
  flowintel-technical-conceptual-schema          # 3.1    Conceptual schema
  flowintel-technical-logical-schema             # 3.2    Logical schema
)

find_mmdc() {
  if [[ -n "${MMDC:-}" ]]; then echo "$MMDC"; return; fi
  if command -v mmdc >/dev/null 2>&1; then command -v mmdc; return; fi
  for cand in \
    "$SCRIPT_DIR/../node_modules/.bin/mmdc" \
    "$HOME/node_modules/.bin/mmdc"; do
    [[ -x "$cand" ]] && { echo "$cand"; return; }
  done
  echo ""  # not found
}
MMDC_BIN="$(find_mmdc)"
if [[ -z "$MMDC_BIN" ]]; then
  echo "ERROR: mmdc (Mermaid CLI) not found." >&2
  echo "  Install it with:  npm install -g @mermaid-js/mermaid-cli" >&2
  echo "  or point MMDC=/path/to/mmdc" >&2
  exit 1
fi

find_chrome() {
  if [[ -n "${PUPPETEER_EXECUTABLE_PATH:-}" ]]; then echo "$PUPPETEER_EXECUTABLE_PATH"; return; fi
  for c in google-chrome google-chrome-stable chromium chromium-browser; do
    command -v "$c" >/dev/null 2>&1 && { command -v "$c"; return; }
  done
  echo ""
}
CHROME_BIN="$(find_chrome)"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PUPPETEER_CFG="$TMP/puppeteer.json"
if [[ -n "$CHROME_BIN" ]]; then
  printf '{ "executablePath": "%s", "args": ["--no-sandbox", "--disable-gpu"] }\n' "$CHROME_BIN" > "$PUPPETEER_CFG"
else
  printf '{ "args": ["--no-sandbox", "--disable-gpu"] }\n' > "$PUPPETEER_CFG"
fi

# extract the mermaid blocks (in order) to .mmd files
python3 - "$DOC" "$TMP" "${DIAGRAMS[@]}" <<'PY'
import re, sys, pathlib
doc_path, tmp = sys.argv[1], sys.argv[2]
names = sys.argv[3:]
text = pathlib.Path(doc_path).read_text()
blocks = re.findall(r"```mermaid\n(.*?)```", text, re.S)
if len(blocks) != len(names):
    sys.exit(
        f"ERROR: found {len(blocks)} mermaid blocks but {len(names)} filenames "
        f"are configured.\nThe DIAGRAMS list in regenerate-diagrams.sh is out of "
        f"sync with the document. Update it to match the current diagrams."
    )
for block, name in zip(blocks, names):
    pathlib.Path(tmp, name + ".mmd").write_text(block)
print(f"Extracted {len(blocks)} mermaid blocks.")
PY

# render each block to its PNG
mkdir -p "$OUT_DIR"
echo "Rendering with: $MMDC_BIN"
[[ -n "$CHROME_BIN" ]] && echo "Browser:        $CHROME_BIN" || echo "Browser:        (mmdc bundled Chromium)"
echo "Output:         $OUT_DIR"
echo

for name in "${DIAGRAMS[@]}"; do
  "$MMDC_BIN" -i "$TMP/$name.mmd" -o "$OUT_DIR/$name.png" \
      -b "$BACKGROUND" -s "$SCALE" -p "$PUPPETEER_CFG" >/dev/null 2>"$TMP/$name.err" \
    && printf '  OK   %s.png\n' "$name" \
    || { printf '  FAIL %s.png\n' "$name"; tail -n 3 "$TMP/$name.err" >&2; exit 1; }
done

echo
echo "Done. Regenerated ${#DIAGRAMS[@]} diagrams."
